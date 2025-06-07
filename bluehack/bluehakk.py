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
import obsolete.deepBle_discovery_tool as deep
import bleshellexploit  # BLE shell exploit module (vulnerability tests are defined here)
from utility_scripts import check_bt_utilities as bt_util
import bleak_stats  # BLE session statistics module

import pandas as pd  # Used for vulnerability result visualization

os.name = ''

def get_current_device():
    if sys.platform.startswith('win'):
        os.name = 'nt'
        print("Windows detected.")
        return 'nt'
    elif sys.platform.startswith('darwin'):
        os.name = 'osx'
        print("Mac OS detected.")
        return 'osx'
    elif sys.platform.startswith('linux'):
        os.name = 'posix'
        print("Linux detected.")
        return 'posix'
    else:
        print("Unsupported OS.")
        return None

async def main_menu():
    if not bt_util.check_and_setup(os.name):
        return
    bt_util.run_os_monitoring(os.name)
    while True:
        print("\n--- Bluehakk CLI Menu ---")
        print("1. Detailed Scan (bleak_discover)")
        print("2. Vulnerability Testing (bleshellexploit)")
        print("3. Run session stats (bleak_stats.py)")
        print("4. MITM Proxy (Windows/Mac)")
        print("5. Exit")
        option = input("Choose an option: ").strip()
        
        if option == "1":
            print("Launching bleak_discover (scan for devices)...")
            subprocess.run(["python3", "bleak_discover.py"])
            print("bleak_discover completed, output saved to recent_scan folder.")
        elif option == "2":
            print("Launching BLE Shell Exploit...")
            subprocess.run(["python3", "bleshellexploit.py"])
            print("BLE Shell Exploit completed, output saved to recent_scan folder.")
        elif option == "3":
            print("\nLaunching session stats (using bleak_stats.py)...")
            subprocess.run(["python3", "bleak_stats.py"])
        elif option == "4":
            print("Launching MITM Proxy, leave blank or enter 'q', 'quit' or 'exit' to go back to menu...")
            if (os.name == 'nt'):
                print("Launching Windows MITM Proxy...")
                target_address = input("Enter the target BLE device address: ").strip()
                if not target_address:
                    print("No address provided. Exiting...")
                    continue
                elif target_address == 'q':
                    print("Exiting...")
                    continue
                elif target_address == 'quit':
                    print("Exiting...")
                    continue
                elif target_address == 'exit':
                    print("Exiting...")
                    continue
                else:
                    subprocess.run(["python3", "win_mitm.py", target_address])
            elif (os.name == 'osx'):
                print("Launching Mac-in-the-Middle Proxy...")
                target_address = input("Enter the target BLE device address: ").strip()
                if not target_address:
                    print("No address provided. Exiting...")
                    continue
                elif target_address == 'q':
                    print("Exiting...")
                    continue
                elif target_address == 'quit':
                    print("Exiting...")
                    continue
                elif target_address == 'exit':
                    print("Exiting...")
                    continue
                else:
                    subprocess.run(["python3", "mac_mitm.py", target_address])
            else:
                print("Unsupported...")
        elif option == "5":
            print("Exiting Bluehakk CLI.")
            break
        else:
            print("Invalid option. Please try again.")

if __name__ == "__main__":
    os.name = get_current_device()
    # Check if the required modules are installed
    if os.name == 'nt':
        subprocess.run(["pip", "install", "-r", "win_requirements.txt"])
    elif os.name == 'osx':
        subprocess.run(["pip", "install", "-r", "mac_requirements.txt"])
    elif os.name == 'posix':
        subprocess.run(["pip", "install", "-r", "lin_requirements.txt"])
    else:
        print("Unsupported OS. Some features may not work.")
        subprocess.run(["pip", "install", "-r", "requirements.txt"])
    # Update the Bluetooth SIG JSON files only if the folder doesn't exist
    if not os.path.isdir("bluetooth-sig-public-jsons"):
        print("Folder 'bluetooth-sig-public-jsons' not found. Updating Bluetooth SIG JSON files...")
        subprocess.run(["python3", "utility_scripts/update_bluetooth_sig_jsons.py"])
    else:
        print("Folder 'bluetooth-sig-public-jsons' found. Skipping update.")
    asyncio.get_event_loop().run_until_complete(main_menu())