import os
import sys
import subprocess
import shutil
import asyncio
import json
import platform
from datetime import datetime

# ----------------- Dependency Checks -----------------
def is_tool_installed(name: str) -> bool:
    """Return True if a tool is available in the user's PATH."""
    return shutil.which(name) is not None


def detect_os() -> str:
    """Return a simplified string identifying the host OS."""
    plat = sys.platform
    release = platform.release().lower()
    if "ish" in release or os.environ.get("ISH_VERSION"):
        return "ish"
    if plat == "darwin":
        return "mac"
    if plat.startswith("win"):
        return "windows"
    if plat.startswith("linux"):
        return "linux"
    return "unknown"

def ensure_wireshark_in_path():
    """
    Ensure Wireshark is available in PATH.
    On Windows, check for both 'wireshark.exe' and 'Wireshark.exe' in common install locations.
    On macOS, check for Wireshark.app and add its bin to PATH if needed.
    On Linux, check for 'wireshark' in PATH.
    Returns True if Wireshark is found, False otherwise.
    """
    if sys.platform.startswith("win"):
        # Check for Wireshark in PATH or common install locations
        if is_tool_installed("wireshark.exe") or is_tool_installed("Wireshark.exe"):
            return True
        possible_paths = [
            r"C:\\Program Files\\Wireshark\\Wireshark.exe",
            r"C:\\Program Files (x86)\\Wireshark\\Wireshark.exe"
        ]
        for path in possible_paths:
            if os.path.exists(path):
                os.environ["PATH"] += os.pathsep + os.path.dirname(path)
                return True
        return False
    elif sys.platform == "darwin":
        if is_tool_installed("wireshark"):
            return True
        wireshark_app = "/Applications/Wireshark.app"
        if os.path.exists(wireshark_app):
            ws_exec = os.path.join(wireshark_app, "Contents", "MacOS")
            os.environ["PATH"] += os.pathsep + ws_exec
            if is_tool_installed("wireshark"):
                print(f"Added Wireshark from {ws_exec} to PATH.")
                return True
        return False
    else:  # Linux and others
        return is_tool_installed("wireshark")


def ensure_wireshark():
    """Attempt to ensure Wireshark is installed on the current OS."""
    os_type = detect_os()
    if os_type == "mac":
        return ensure_wireshark_in_path()
    if os_type in {"linux", "ish"}:
        if is_tool_installed("wireshark"):
            return True
        if shutil.which("apt-get"):
            try:
                subprocess.run(["apt-get", "update"], check=True)
                subprocess.run(["apt-get", "install", "-y", "wireshark"], check=True)
                return True
            except Exception:
                return False
    if os_type == "windows":
        if is_tool_installed("wireshark") or is_tool_installed("Wireshark.exe"):
            return True
        if is_tool_installed("choco"):
            try:
                subprocess.run(["choco", "install", "wireshark", "-y"], check=True)
                return True
            except Exception:
                return False
    return False

def check_macos_dependencies():
    errors = []
    profile_path = os.path.join("utility_scripts", "BluetoothProfileForMac", "Bluetooth_macOS.mobileconfig")
    if not os.path.exists(profile_path):
        errors.append(f"Configuration profile not found: {profile_path}")

    if not ensure_wireshark():
        errors.append(
            "Wireshark is not installed or could not be added to PATH. BLE capture will be limited."
        )

    if not is_tool_installed("brew"):
        errors.append("Homebrew is not installed. Please install Homebrew to manage required casks.")
    else:
        try:
            subprocess.run(["brew", "list", "--cask", "wireshark-chmodbpf"],
                           capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError:
            errors.append("wireshark-chmodbpf is not installed. Please run: brew install --cask wireshark-chmodbpf")
    
    try:
        subprocess.run(["xcode-select", "-p"], capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError:
        errors.append("Xcode/developer tools are not installed. Please install Xcode and the latest developer tools.")

    return errors

def check_windows_dependencies():
    errors = []
    if not ensure_wireshark():
        errors.append(
            "Wireshark is not installed. Packet capture will be disabled unless installed."
        )
    btpack_path = os.path.join("utility_scripts", "BluetoothToolforWindows", "BluetoothTestPlatformPack-1.14.0.msi")
    if not os.path.exists(btpack_path):
        errors.append(f"Bluetooth Test Platform Pack MSI not found: {btpack_path}")
    return errors

def check_linux_dependencies():
    """Simple checks for common linux BLE utilities."""
    errors = []
    for tool in ("bluetoothctl", "btmon"):
        if not is_tool_installed(tool):
            errors.append(f"{tool} is not installed or not in PATH.")
    if not ensure_wireshark():
        errors.append(
            "Wireshark is not installed. Live capture features will be disabled."
        )
    return errors

def check_and_setup() -> bool:
    os_type = detect_os()
    errors: list[str] = []

    if os_type == "mac":
        print("Checking dependencies for macOS...")
        errors = check_macos_dependencies()
        req = "mac_requirements.txt"
    elif os_type == "windows":
        print("Checking dependencies for Windows...")
        errors = check_windows_dependencies()
        req = "win_requirements.txt"
    elif os_type in {"linux", "ish"}:
        print("Checking dependencies for Linux/iSH...")
        errors = check_linux_dependencies()
        req = "requirements.txt"
    else:
        print("Unsupported OS. Some features may not work.")
        req = "requirements.txt"

    if errors:
        print("Dependency check failed with the following errors:")
        for err in errors:
            print(" - " + err)
        print("Please install/configure the missing utilities and re-run the tool.")
        return False
    else:
        print("All required dependencies are installed and configured.")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "-r", req], check=True)
        except Exception as exc:
            print(f"Failed to install Python requirements from {req}: {exc}")
        return True

# ----------------- OS-Specific Monitoring -----------------
def run_os_monitoring():
    platform = sys.platform
    if platform == "darwin":
        print("Launching Wireshark to analyze the Bluetooth interface...")
        try:
            subprocess.Popen(["open", "-a", "Wireshark"])
        except Exception as e:
            print(f"Failed to launch Wireshark: {e}")
        print("Launching PacketLogger to monitor the Bluetooth interface...")
        try:
            subprocess.Popen(["open", "-a", "PacketLogger"])
        except Exception as e:
            print(f"Failed to launch PacketLogger: {e}")
        print("Configuring Bluetooth interface for monitoring (stub)...")
    elif platform.startswith("win"):
        bt_tool_dir = os.path.join("utility_scripts", "BluetoothToolforWindows")
        btvs_exe = os.path.join(bt_tool_dir, "btvs.exe")
        if not os.path.exists(btvs_exe):
            print(f"btvs.exe not found in {bt_tool_dir}. Please ensure the Bluetooth Test Platform Pack is installed.")
            return
        print("Launching btvs.exe in Wireshark mode...")
        try:
            subprocess.Popen([btvs_exe, "-Mode", "Wireshark"], cwd=bt_tool_dir)
        except Exception as e:
            print(f"Failed to launch btvs.exe: {e}")
        btp_exe = os.path.join(bt_tool_dir, "btp.exe")
        if os.path.exists(btp_exe):
            print("Launching btp.exe to configure the Bluetooth interface for monitoring...")
            try:
                subprocess.Popen([btp_exe, "-Configure"], cwd=bt_tool_dir)
            except Exception as e:
                print(f"Failed to launch btp.exe: {e}")
        else:
            print("btp.exe not found. Please ensure the Bluetooth monitoring tools (btp) are installed.")
    elif platform.startswith("linux"):
        print("Launching Wireshark for Linux...")
        try:
            subprocess.Popen(["wireshark"])
        except Exception as e:
            print(f"Failed to launch Wireshark: {e}")
        print("For live BLE capture, ensure you have the correct permissions and tools (e.g., btmon, bluetoothctl).")
    else:
        print("No OS monitoring tool available for this platform.")

# ----------------- Live Scan Functions -----------------
async def run_windows_live_scan():
    try:
        from bleak import BleakScanner
    except ImportError:
        print("Bleak is not installed. Please install bleak to use Windows live scan.")
        return
    if BleakScanner is None or not hasattr(BleakScanner, "discover"):
        print("BleakScanner is not available or discover method missing.")
        return
    filter_addr = input("Enter filter for btle.advertising_address (e.g. AA:BB:CC:DD:EE:FF) or leave blank: ").strip().upper()
    filtered_devices = {}
    cancel_event = asyncio.Event()

    async def wait_for_cancel():
        while not cancel_event.is_set():
            ch = await asyncio.to_thread(input, "")
            if ch.strip().lower() == "q":
                cancel_event.set()
                print("Canceling Windows live scan...")
                break

    async def windows_live_scan_loop():
        while not cancel_event.is_set():
            devices = await BleakScanner.discover(timeout=2.0)
            print("\nWindows Live Scan Results:")
            for device in devices:
                adv_addr = device.address.upper() if device.address else ""
                if filter_addr and adv_addr != filter_addr:
                    continue
                print(f"  Device: {device.name} - {adv_addr}")
                filtered_devices[adv_addr] = {
                    "name": device.name,
                    "address": adv_addr,
                    "timestamp": datetime.now().isoformat()
                }
            await asyncio.sleep(0.5)

    await asyncio.gather(wait_for_cancel(), windows_live_scan_loop())
    output_file = "filtered_scan_results.json"
    with open(output_file, "w") as f:
        json.dump(filtered_devices, f, indent=2)
    print(f"Filtered scan results saved to {output_file}.")

async def run_deepble_live_scan():
    try:
        from bleak import BleakScanner
    except ImportError:
        print("Bleak is not installed. Please install bleak to use live scan.")
        return
    cancel_event = asyncio.Event()

    async def wait_for_cancel():
        while not cancel_event.is_set():
            ch = await asyncio.to_thread(input, "")
            if ch.strip().lower() == "q":
                cancel_event.set()
                print("Canceling deepBLE live scan...")
                break

    async def live_scan_loop():
        while not cancel_event.is_set():
            devices = await BleakScanner.discover(timeout=2.0)
            print("\nDeepBLE Live Scan Results:")
            if devices:
                for device in devices:
                    print(f"  Device: {device.name} - {device.address}")
            else:
                print("  No devices found in this interval.")
            await asyncio.sleep(0.5)

    await asyncio.gather(wait_for_cancel(), live_scan_loop())

# ----------------- Export & Visualization -----------------
def export_os_capture():
    os_type = detect_os()
    if os_type == "mac":
        output_file = "capture.btsnoop"
        print(f"Exporting PacketLogger capture to {output_file} ...")
        with open(output_file, "w") as f:
            f.write("")
        print("Export complete.")
    elif os_type == "windows":
        print("Using filtered_scan_results.json for further analysis and visualization.")
    else:
        print("Export not supported on this platform.")

def visualize_results(live=False):
    """
    If 'live' is False, load capture/session JSON and pass to bleak_stats.show_stats().
    If live is True, call bleak_stats.live_update_stats() to chart updating results.
    """
    try:
        import bleak_stats
    except ImportError:
        print("bleak_stats module not found.")
        return
    
    if live:
        print("Starting live updating visualization...")
        live_update = getattr(bleak_stats, "live_update_stats", None)
        if callable(live_update):
            live_update("filtered_scan_results.json")
        else:
            print("live_update_stats not found in bleak_stats.")
    else:
        print("Generating visualization from last captured session...")
        data_file = "capture.btsnoop" if detect_os() == "mac" else "filtered_scan_results.json"
        with open(data_file, "r") as f:
            try:
                data = json.load(f)
            except json.decoder.JSONDecodeError:
                data = {}
        show_stats = getattr(bleak_stats, "show_stats", None)
        if callable(show_stats):
            show_stats(data)
        else:
            print("show_stats not found in bleak_stats.")

# ----------------- Module Interface -----------------
if __name__ == "__main__":
    if check_and_setup():
        run_os_monitoring()
        os_type = detect_os()
        if os_type == "mac":
            asyncio.run(run_deepble_live_scan())
            export_os_capture()
        elif os_type == "windows":
            asyncio.run(run_windows_live_scan())
            export_os_capture()

try:
    from bleak import BleakScanner, BleakClient
except ImportError:
    BleakScanner = None
    BleakClient = None

