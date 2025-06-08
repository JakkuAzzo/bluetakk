import os
import json
import sys
import time
import asyncio
import subprocess
from datetime import datetime

try:
    from bleak import BleakScanner, BleakClient
except ImportError:
    BleakScanner = None
    BleakClient = None
try:
    import nest_asyncio
    nest_asyncio.apply()
except ImportError:
    pass
try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None
try:
    import pandas as pd
except ImportError:
    pd = None

# Import modules
import deepBle_discovery_tool as deep
import bleshellexploit  # BLE shell exploit module (vulnerability tests are defined here)
from utility_scripts import check_bt_utilities as bt_util
from utility_scripts.check_bt_utilities import detect_os
import bleak_stats  # BLE session statistics module
from peripheral_simulator import DEVICE_PROFILES, start_simulator

current_os = None
# Track shell sessions keyed by device address
active_sessions: dict[str, subprocess.Popen[bytes]] = {}

def choose_adapter():
    """Prompt the user to select a Bluetooth adapter or use auto-detect."""
    if os.environ.get("BLEAK_SELECTED_ADAPTER"):
        print(f"Using adapter {os.environ['BLEAK_SELECTED_ADAPTER']}")
        return
    adapter = input(
        "Enter adapter path to use (blank for auto detect): ").strip()
    if adapter:
        os.environ["BLEAK_SELECTED_ADAPTER"] = adapter
        print(f"Using adapter {adapter}")
    else:
        print("Auto-detecting adapter")

def get_current_device():
    """Determine the simplified OS string."""
    global current_os
    # Use sys.platform for robust OS detection
    plat = sys.platform
    if plat == "darwin":
        os_type = "mac"
    elif plat.startswith("win"):
        os_type = "windows"
    elif plat.startswith("linux") or plat == "linux" or plat == "linux2":
        os_type = "linux"
    elif plat == "ish":
        os_type = "ish"
    else:
        os_type = None
    os_map = {
        "windows": "nt",
        "mac": "osx",
        "linux": "posix",
        "ish": "posix",
    }
    current_os = os_map[os_type] if os_type in os_map else None
    if current_os and os_type:
        print(f"{str(os_type).capitalize()} detected.")
    else:
        print("Unsupported OS.")
    return current_os

def store_session_details(device, details):
    session_data = {
        "timestamp": datetime.now().isoformat(),
        "device_address": device.address,
        "device_name": device.name,
        "services": details.get("services", []),
    }
    sessions_dir = "sessions"
    os.makedirs(sessions_dir, exist_ok=True)
    filename = os.path.join(
        sessions_dir,
        f"session_{device.address}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    with open(filename, "w") as f:
        json.dump({"current_session_details": session_data}, f, indent=4)
    print(f"Session details saved to {filename}")

def launch_shell_session(address: str) -> None:
    """Launch blueshell in a detached subprocess and track it."""
    script = "blueshell.py"
    if not os.path.exists(script):
        raise FileNotFoundError(script)
    cmd = [sys.executable, script, "--device_address", address]
    proc = subprocess.Popen(cmd, start_new_session=True)
    active_sessions[address] = proc
    print(f"Started shell session for {address} (PID {proc.pid})")

def visualize_vuln_results(results):
    """
    Displays the vulnerability test results using a table.
    Expected results is a list of dictionaries with keys like:
       "device_name", "service_uuid", "char_uuid", "response", etc.
    """
    if not results:
        print("No vulnerability test results to display.")
        return
    if pd is None or plt is None:
        print("pandas or matplotlib is not available for visualization.")
        return
    # Create a DataFrame for nicer formatting.
    df = pd.DataFrame(results)
    # Reorder columns if present.
    cols_order = ["device_name", "service_uuid", "char_uuid", "response"]
    cols = [col for col in cols_order if col in df.columns]
    if cols:
        df = df[cols]
    # Create and show a matplotlib table.
    fig, ax = plt.subplots(figsize=(max(8, len(df.columns)*1.2), max(2, len(df)*0.5)))
    ax.axis('tight')
    ax.axis('off')
    table = ax.table(
        cellText=df.values.tolist(),
        colLabels=list(df.columns),
        cellLoc='center',
        loc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    plt.title("Vulnerability Test Results")
    plt.show()

def list_sessions():
    """Display active sessions and remove finished ones."""
    to_remove = []
    for addr, proc in active_sessions.items():
        running = proc.poll() is None
        status = "running" if running else "closed"
        print(f"{addr}: {status} (PID {proc.pid})")
        if not running:
            to_remove.append(addr)
    for addr in to_remove:
        active_sessions.pop(addr, None)

def ensure_venv_and_requirements():
    import sys
    import subprocess
    import os
    venv_dir = os.path.join(os.path.dirname(__file__), ".venv_auto")
    if not os.path.exists(venv_dir):
        print(f"Creating virtual environment at {venv_dir}...")
        subprocess.run([sys.executable, "-m", "venv", venv_dir], check=True)
    pip_path = os.path.join(venv_dir, "bin", "pip") if not sys.platform.startswith("win") else os.path.join(venv_dir, "Scripts", "pip.exe")
    # Use sys.platform for accurate OS detection
    if sys.platform == "darwin":
        req_file = "mac_requirements.txt"
    elif sys.platform.startswith("win"):
        req_file = "win_requirements.txt"
    elif sys.platform.startswith("linux") or sys.platform == "linux" or sys.platform == "linux2":
        req_file = "requirements.txt"
    else:
        req_file = "requirements.txt"
    req_path = os.path.join(os.path.dirname(__file__), req_file)
    if os.path.exists(pip_path) and os.path.exists(req_path):
        print(f"Installing requirements from {req_file} in {venv_dir}...")
        subprocess.run([pip_path, "install", "--force-reinstall", "-r", req_path], check=True)
    else:
        print(f"Could not find pip at {pip_path} or requirements at {req_path}.")

async def main_menu():
    # Check dependencies and auto-install if missing
    missing = bt_util.check_and_setup()
    if missing is False:
        # Try to auto-install missing utilities for macOS
        plat = sys.platform
        if plat == "darwin":
            print("Attempting to auto-install missing macOS utilities...")
            # Try to install the configuration profile if missing
            profile_path = os.path.join("utility_scripts", "BluetoothProfileForMac", "Bluetooth_macOS.mobileconfig")
            if not os.path.exists(profile_path):
                # Download or copy a default profile if possible
                try:
                    import urllib.request
                    url = "https://developer.apple.com/bug-reporting/profiles-and-logs/?name=bluetooth"  # Apple official page
                    print("Could not auto-download Bluetooth_macOS.mobileconfig.\nPlease download it manually from:")
                    print("  https://developer.apple.com/bug-reporting/profiles-and-logs/?name=bluetooth")
                    print(f"and place it at: {profile_path}\nContinuing, but BLE packet capture may not work until this is done.")
                except Exception as e:
                    print(f"Failed to provide download instructions: {e}")
            # Re-run dependency check
            if not bt_util.check_and_setup():
                print("Dependency check still failed. You may continue, but BLE packet capture may not work until you manually install the missing configuration profile.")
                # Optionally, continue instead of return
                # return
        else:
            print("Dependency check failed. Please install/configure the missing utilities and re-run the tool.")
            return
    choose_adapter()
    bt_util.run_os_monitoring()
    
    while True:
        print("\n--- Bluehakk CLI Menu ---")
        print("1. Detailed Scan (DeepBle)")
        print("2. Vulnerability Testing on a Device")
        print("3. Run session stats")
        print("4. Static visualization (Last capture)")
        print("5. MITM Proxy (Windows/Mac)")
        print("6. Exit")
        print("7. Start Peripheral Simulator")
        print("8. Launch Shell Session")
        print("9. List Active Sessions")
        option = input("Choose an option: ").strip()
        
        if option == "1":
            print("\nLaunching deepBle discovery tool (embedded in Bluehakk).")
            # deepBle_discovery_tool.py is assumed to handle its own live updates during scanning.
            deep.main_menu()
        elif option == "2":
            device_address = input("Enter target BLE device address for vulnerability testing: ").strip()
            print(f"Starting vulnerability tests on {device_address} using bleshellexploit...")
            # Use the vulnerability exploit routine from bleshellexploit.
            results = bleshellexploit.run_exploit(device_address)
            print("Vulnerability testing completed. Results:")
            for res in results:
                print(f"Service UUID: {res.get('service_uuid')}")
                print(f"Characteristic UUID: {res.get('char_uuid')}")
                print(f"Response: {res.get('response')}")
                print("-----------------------")
            # Visualize the test results using bleak_stats style visualization.
            visualize_vuln_results(results)
        elif option == "3":
            print("\nLaunching session stats (using bleak_stats.py)...")
            subprocess.run(["python3", "bleak_stats.py"])
        elif option == "4":
            print("Generating static visualization from last captured session...")
            bt_util.visualize_results(live=False)
        elif option == "5":
            target_address = input("Enter the target BLE device address: ").strip()
            script = "win_mitm.py" if current_os == 'nt' else "mac_mitm.py" if current_os == 'osx' else None
            if script is None:
                print("MITM proxy not supported on this OS.")
            else:
                print(f"Launching {'Windows' if current_os=='nt' else 'Mac'} MITM Proxy...")
                try:
                    subprocess.run(["python3", script, target_address], check=True)
                except FileNotFoundError:
                    print(f"{script} not found. Feature not installed.")
                except Exception as exc:
                    print(f"Failed to launch {script}: {exc}")
        elif option == "6":
            print("Exiting Bluehakk CLI.")
            break
        elif option == "7":
            items = list(DEVICE_PROFILES.keys())
            print("Available device profiles:")
            for i, name in enumerate(items, 1):
                print(f"{i}. {name}")
            choice = input("Select profile: ").strip()
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(items):
                    start_simulator(items[idx])
                else:
                    print("Invalid selection")
            except Exception as exc:
                print(f"Failed to start simulator: {exc}")
        elif option == "8":
            addr = input("Device address for shell session: ").strip()
            if addr:
                try:
                    launch_shell_session(addr)
                except FileNotFoundError:
                    print("blueshell.py not found. Unable to start session.")
                except Exception as exc:
                    print(f"Failed to launch shell: {exc}")
        elif option == "9":
            list_sessions()
        else:
            print("Invalid option. Please try again.")

if __name__ == "__main__":
    ensure_venv_and_requirements()
    current_os = get_current_device()
    bt_util.check_and_setup()
    asyncio.get_event_loop().run_until_complete(main_menu())
