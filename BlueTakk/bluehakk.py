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
    os_type = detect_os()
    current_os = {
        "windows": "nt",
        "mac": "osx",
        "linux": "posix",
        "ish": "posix",
    }.get(os_type)
    print(f"{os_type.capitalize()} detected." if current_os else "Unsupported OS.")
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
    cmd = [sys.executable, "blueshell.py", "--device_address", address]
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
    import platform
    venv_dir = os.path.join(os.path.dirname(__file__), ".venv_auto")
    if not os.path.exists(venv_dir):
        print(f"Creating virtual environment at {venv_dir}...")
        subprocess.run([sys.executable, "-m", "venv", venv_dir], check=True)
    pip_path = os.path.join(venv_dir, "bin", "pip") if not sys.platform.startswith("win") else os.path.join(venv_dir, "Scripts", "pip.exe")
    if sys.platform == "darwin":
        req_file = "mac_requirements.txt"
    elif sys.platform.startswith("win"):
        req_file = "win_requirements.txt"
    else:
        req_file = "requirements.txt"
    req_path = os.path.join(os.path.dirname(__file__), req_file)
    if os.path.exists(pip_path) and os.path.exists(req_path):
        print(f"Installing requirements from {req_file} in {venv_dir}...")
        subprocess.run([pip_path, "install", "--force-reinstall", "-r", req_path], check=True)
    else:
        print(f"Could not find pip at {pip_path} or requirements at {req_path}.")

async def main_menu():
    if not bt_util.check_and_setup():
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
            if current_os == 'nt':
                print("Launching Windows MITM Proxy...")
                target_address = input("Enter the target BLE device address: ").strip()
                subprocess.run(["python3", "win_mitm.py", target_address])
            elif current_os == 'osx':
                print("Launching Mac-in-the-Middle Proxy...")
                target_address = input("Enter the target BLE device address: ").strip()
                subprocess.run(["python3", "mac_mitm.py", target_address])
            else:
                print("Unsupported...")
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
                launch_shell_session(addr)
        elif option == "9":
            list_sessions()
        else:
            print("Invalid option. Please try again.")

if __name__ == "__main__":
    ensure_venv_and_requirements()
    current_os = get_current_device()
    bt_util.check_and_setup()
    asyncio.get_event_loop().run_until_complete(main_menu())
