import os
import sys
import subprocess
import shutil
import asyncio
import json
from datetime import datetime
from bleak import BleakScanner

# ----------------- Dependency Checks -----------------
def is_tool_installed(name):
    """Check if a tool is in PATH."""
    return shutil.which(name) is not None

def ensure_wireshark_in_path():
    """
    Ensure Wireshark is available in PATH.
    If not, check if Wireshark.app exists in /Applications, and if found, add its executable folder to PATH.
    If not found, attempt to install it using Homebrew.
    Returns True if Wireshark is found/installed, False otherwise.
    """
    if is_tool_installed("wireshark"):
        return True

    wireshark_app = "/Applications/Wireshark.app"
    if os.path.exists(wireshark_app):
        ws_exec = os.path.join(wireshark_app, "Contents", "MacOS")
        os.environ["PATH"] += os.pathsep + ws_exec
        if is_tool_installed("wireshark"):
            print(f"Added Wireshark from {ws_exec} to PATH.")
            return True

    if is_tool_installed("brew"):
        try:
            print("Wireshark not found. Installing via Homebrew...")
            subprocess.run(["brew", "install", "--cask", "wireshark"], check=True)
            ws_exec = os.path.join(wireshark_app, "Contents", "MacOS")
            os.environ["PATH"] += os.pathsep + ws_exec
            if is_tool_installed("wireshark"):
                print("Wireshark successfully installed and added to PATH.")
                return True
        except subprocess.CalledProcessError as e:
            print(f"Error installing Wireshark via Homebrew: {e}")
            return False
    else:
        print("Homebrew is not installed; cannot auto-install Wireshark.")
    return False

def check_macos_dependencies():
    errors = []
    profile_path = os.path.join("utility_scripts", "BluetoothProfileForMac", "Bluetooth_macOS.mobileconfig")
    if not os.path.exists(profile_path):
        errors.append(f"Configuration profile not found: {profile_path}")

    if not ensure_wireshark_in_path():
        errors.append("Wireshark is not installed or could not be added to PATH.")

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
    if not (is_tool_installed("Wireshark.exe") or is_tool_installed("wireshark")):
        errors.append("Wireshark is not installed or not in your PATH. Please install Wireshark.")
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
    return errors

def check_and_setup():
    platform = sys.platform
    errors = []
    if platform == "darwin":
        print("Checking dependencies for macOS...")
        errors = check_macos_dependencies()
    elif platform.startswith("win"):
        print("Checking dependencies for Windows...")
        errors = check_windows_dependencies()
    elif platform.startswith("linux"):
        print("Checking dependencies for Linux/iSH...")
        errors = check_linux_dependencies()
    else:
        print("Unsupported OS. This module supports macOS, Windows and Linux.")
        return False

    if errors:
        print("Dependency check failed with the following errors:")
        for err in errors:
            print(" - " + err)
        print("Please install/configure the missing utilities and re-run the tool.")
        return False
    else:
        print("All required dependencies are installed and configured.")
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
        # Launch PacketLogger (typically located in /Applications/Utilities)
        print("Launching PacketLogger to monitor the Bluetooth interface...")
        try:
            subprocess.Popen(["open", "-a", "PacketLogger"])
        except Exception as e:
            print(f"Failed to launch PacketLogger: {e}")
        # (Stub) Configure Bluetooth interface for monitoring.
        print("Configuring Bluetooth interface for monitoring (stub)...")
        # For example, you might run a shell script or system command here.
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
        # Attempt to launch btp.exe to configure the Bluetooth interface.
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
        if is_tool_installed("btmon"):
            print("Launching btmon for Bluetooth monitoring...")
            try:
                subprocess.Popen(["btmon"])
            except Exception as e:
                print(f"Failed to launch btmon: {e}")
        else:
            print("btmon not found. Install bluez-utils for monitoring support.")
    else:
        print("No OS monitoring tool available for this platform.")

# ----------------- Live Scan Functions -----------------
async def run_windows_live_scan():
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
    print("\nStarting deepBLE live scan (press 'q' then Enter to cancel)...")
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
    platform = sys.platform
    if platform == "darwin":
        output_file = "capture.btsnoop"
        print(f"Exporting PacketLogger capture to {output_file} ...")
        with open(output_file, "w") as f:
            f.write("")
        print("Export complete.")
    elif platform.startswith("win"):
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
        bleak_stats.live_update_stats("filtered_scan_results.json")
    else:
        print("Generating visualization from last captured session...")
        data_file = "capture.btsnoop" if sys.platform == "darwin" else "filtered_scan_results.json"
        with open(data_file, "r") as f:
            try:
                data = json.load(f)
            except json.decoder.JSONDecodeError:
                data = {}
        bleak_stats.show_stats(data)

# ----------------- Module Interface -----------------
if __name__ == "__main__":
    if check_and_setup():
        run_os_monitoring()
        platform = sys.platform
        if platform == "darwin":
            asyncio.run(run_deepble_live_scan())
            export_os_capture()
        elif platform.startswith("win"):
            asyncio.run(run_windows_live_scan())
            export_os_capture()
        elif platform.startswith("linux"):
            asyncio.run(run_deepble_live_scan())
            export_os_capture()

