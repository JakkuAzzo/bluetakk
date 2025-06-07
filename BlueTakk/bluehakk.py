import os
import json
import sys
import time
import asyncio
import subprocess
from datetime import datetime
from bleak import BleakScanner, BleakClient
import nest_asyncio
nest_asyncio.apply()
import matplotlib.pyplot as plt  # For live chart closing

# Import modules
import deepBle_discovery_tool as deep
import bleshellexploit  # BLE shell exploit module (vulnerability tests are defined here)
from utility_scripts import check_bt_utilities as bt_util
import bleak_stats  # BLE session statistics module
from peripheral_simulator import DEVICE_PROFILES, start_simulator

import pandas as pd  # Used for vulnerability result visualization

current_os = None

def get_current_device():
    global current_os
    if sys.platform.startswith('win'):
        current_os = 'nt'
        print("Windows detected.")
    elif sys.platform.startswith('darwin'):
        current_os = 'osx'
        print("Mac OS detected.")
    elif sys.platform.startswith('linux'):
        current_os = 'posix'
        print("Linux detected.")
    else:
        print("Unsupported OS.")
        current_os = None
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

def visualize_vuln_results(results):
    """
    Displays the vulnerability test results using a table.
    Expected results is a list of dictionaries with keys like:
       "device_name", "service_uuid", "char_uuid", "response", etc.
    """
    if not results:
        print("No vulnerability test results to display.")
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
    table = ax.table(cellText=df.values,
                     colLabels=df.columns,
                     cellLoc='center',
                     loc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    plt.title("Vulnerability Test Results")
    plt.show()

async def main_menu():
    if not bt_util.check_and_setup():
        return
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
        else:
            print("Invalid option. Please try again.")

if __name__ == "__main__":
    current_os = get_current_device()
    # Check if the required modules are installed
    if current_os == 'nt':
        subprocess.run(["pip", "install", "-r", "win_requirements.txt"])
    elif current_os == 'osx':
        subprocess.run(["pip", "install", "-r", "mac_requirements.txt"])
    elif current_os == 'posix':
        subprocess.run(["pip", "install", "-r", "requirements.txt"])
    else:
        print("Unsupported OS. Some features may not work.")
        subprocess.run(["pip", "install", "-r", "requirements.txt"])
    asyncio.get_event_loop().run_until_complete(main_menu())
