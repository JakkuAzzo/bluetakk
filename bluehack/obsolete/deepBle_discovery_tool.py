import os
import re
import json
import asyncio
import subprocess
from datetime import datetime

# --- Attempt to Import Optional Dependencies ---
try:
    import yaml
except ImportError:
    yaml = None
try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None
try:
    from bleak import BleakScanner, BleakClient  # type: ignore
except ImportError:
    class BleakScanner:
        @staticmethod
        async def discover(*args, **kwargs):
            return []
    class BleakClient:
        def __init__(self, *a, **k):
            self.services = []
        async def __aenter__(self): return self
        async def __aexit__(self, exc_type, exc, tb): pass
        async def get_services(self): return []
        async def read_gatt_char(self, uuid): return b""

# Import centralized utilities
from utility_scripts import check_bt_utilities as bt_util
import bleak_stats

# --- Custom YAML Loader to Preserve Hex Strings ---
def hex_int_constructor(loader, node):
    value = loader.construct_scalar(node)
    return value  # preserve as string

if yaml is not None and hasattr(yaml, "SafeLoader") and "HexStringLoader" not in globals():
    class HexStringLoader(yaml.SafeLoader):
        pass
    HexStringLoader.add_constructor('tag:yaml.org,2002:int', hex_int_constructor)
else:
    if "HexStringLoader" not in globals():
        class HexStringLoader(object):
            pass

# YAML safe_load guard

def load_yaml_file(path):
    if yaml is not None and hasattr(yaml, "safe_load"):
        with open(path) as f:
            return yaml.safe_load(f)
    return {}

# Matplotlib guards

def close_all_figures():
    if plt is not None and hasattr(plt, "get_fignums") and hasattr(plt, "close"):
        while plt.get_fignums():
            plt.close("all")

# bleak_stats guards
import inspect
async def guarded_live_update_stats_data(bleak_stats, live_scan_data):
    live_update = getattr(bleak_stats, "async_live_update_stats_data", None)
    if callable(live_update) and inspect.iscoroutinefunction(live_update):
        await live_update(live_scan_data)
    else:
        print("async_live_update_stats_data not found or not awaitable in bleak_stats.")

async def guarded_live_update_detailed_stats_data(bleak_stats, live_scan_data):
    detailed_update = getattr(bleak_stats, "async_live_update_detailed_stats_data", None)
    if callable(detailed_update) and inspect.iscoroutinefunction(detailed_update):
        await detailed_update(live_scan_data)
    else:
        print("async_live_update_detailed_stats_data not found or not awaitable in bleak_stats.")

# --- Device Detail Functions ---
async def get_device_details(address):
    details = []
    try:
        async with BleakClient(address) as client:
            services = await client.get_services()
            for service in services:
                service_info = {
                    "name": service.description,
                    "uuid": service.uuid,
                    "handle": service.handle,
                    "characteristics": []
                }
                for char in service.characteristics:
                    try:
                        raw_val = await client.read_gatt_char(char.uuid)
                        hex_val = raw_val.hex()
                        # Attempt to decode raw_val to a string (ignoring errors)
                        decoded = raw_val.decode(errors="ignore")
                    except Exception as e:
                        hex_val = "N/A"
                        decoded = f"Error reading value: {e}"
                    char_info = {
                        "uuid": char.uuid,
                        "properties": char.properties,
                        "value": hex_val,
                        "decoded": decoded,
                        "extra": lookup_details(char.uuid, category="characteristic_uuids")
                    }
                    service_info["characteristics"].append(char_info)
                # Look up extra detail for the service
                service_info["extra"] = lookup_details(service.uuid, category="service_uuids")
                details.append(service_info)
    except Exception as e:
        print(f"Failed to get services for {address}: {e}")
    return details

def save_scan_results(results, scan_type="scan"):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{scan_type}_{timestamp}.json"
    try:
        with open(filename, "w") as f:
            json.dump(results, f, indent=4)
        print(f"Scan results saved to {filename}")
    except Exception as e:
        print(f"Error saving scan results to {filename}: {e}")

# --- Basic Reference Loaders ---
def load_company_identifiers(folder_path='bluetooth-sig-public-jsons'):
    """
    Loads and aggregates JSON data from the Bluetooth SIG folder.
    This includes details from:
      - company_identifiers
      - profiled_and_services
      - service_discovery
      - uuids

    Returns a dictionary with keys for each folder. Each value is a dictionary
    mapping identifiers (e.g. "0x004C") to their detailed info.
    """

    folders = ['company_identifiers', 'profiled_and_services', 'service_discovery', 'uuids']
    aggregated_data = {folder: {} for folder in folders}
    
    if not os.path.exists(folder_path):
        print(f"Folder {folder_path} not found.")
        return aggregated_data

    for folder in folders:
        subfolder_path = os.path.join(folder_path, folder)
        if not os.path.exists(subfolder_path):
            print(f"Subfolder {subfolder_path} not found.")
            continue

        for filename in os.listdir(subfolder_path):
            if not filename.endswith('.json'):
                continue

            file_path = os.path.join(subfolder_path, filename)
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    # Data may be a dict or a list; merge accordingly.
                    if isinstance(data, dict):
                        for key, value in data.items():
                            aggregated_data[folder][key] = value
                    elif isinstance(data, list):
                        for item in data:
                            identifier = item.get('identifier')
                            if identifier:
                                aggregated_data[folder][identifier] = item
            except Exception as e:
                print(f"Error parsing {file_path}: {e}")

    return aggregated_data

def load_class_of_device(yaml_path):
    try:
        with open(yaml_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading Class of Device YAML from {yaml_path}: {e}")
        return {}

def load_all_references_from_log(log_filename="bluetooth_sig_jsons.txt"):
    refs = {}
    if not os.path.exists(log_filename):
        print(f"Log file {log_filename} not found.")
        return refs
    with open(log_filename, "r") as lf:
        for line in lf:
            json_path = line.strip()
            if not json_path or not json_path.endswith(".json"):
                continue
            try:
                with open(json_path, "r") as jf:
                    data = json.load(jf)
                    key = os.path.basename(json_path).replace(".json", "")
                    refs[key] = data
            except Exception as e:
                print(f"Error loading {json_path}: {e}")
    return refs

# --- Global Reference Data Loaded on Startup ---
COMPANY_IDENTIFIERS_PATH = "bluetooth-sig-public-jsons/assigned_numbers/company_identifiers/company_identifiers.json"
CLASS_OF_DEVICE_PATH = "bluetooth-sig-public-jsons/assigned_numbers/core/class_of_device.json"

CHIPSET_LOOKUP = load_company_identifiers(COMPANY_IDENTIFIERS_PATH)
COD_DATA = load_class_of_device(CLASS_OF_DEVICE_PATH)
REFERENCE_DATA = load_all_references_from_log()

print(f"Loaded {len(CHIPSET_LOOKUP)} company identifiers:")

def lookup_details(query, category=None):
    try:
        qnum = int(query) if isinstance(query, int) else int(query, 0)
    except Exception:
        return None
    for ref_name, data in REFERENCE_DATA.items():
        if category and category not in ref_name:
            continue
        items = data.get("values") if isinstance(data, dict) and "values" in data else data
        if not isinstance(items, list):
            continue
        for item in items:
            for field in ["opcode", "value", "propertyid", "uuid"]:
                if field in item:
                    try:
                        item_val = int(item[field], 0)
                        if item_val == qnum:
                            ident = item.get("identifier", item.get("name", ""))
                            desc = item.get("description", "")
                            return f"{ident} ({ref_name}): {desc}"
                    except Exception:
                        pass
    return None

def decode_manufacturer_data(manufacturer_data):
    for key in manufacturer_data.keys():
        hex_key = f"0x{key:04X}"
        print(f"Comparing manufacturer key {key} converted to {hex_key}")
        if hex_key in CHIPSET_LOOKUP:
            return f"{CHIPSET_LOOKUP[hex_key]} ({hex_key})"
    return "Unknown"

def decode_class_of_device(cod_value):
    return f"Class of Device: {cod_value}"

def format_manufacturer_data(manufacturer_data):
    output = ""
    for key, value in manufacturer_data.items():
        key_hex = f"0x{int(key):04X}"
        details = lookup_details(key_hex, category="company_identifiers")
        output += f"{key_hex} (raw: {value}) -> {details}\n"
    return output.strip()

def format_service_details(service):
    return f"Service {service.uuid}: {lookup_details(service.uuid, 'service_uuids')}"

def format_characteristic_details(char, value):
    try:
        decoded = value.decode(errors="ignore")
    except Exception:
        decoded = "N/A"
    details = lookup_details(char.uuid, 'characteristic_uuids')
    return f"Characteristic {char.uuid}: {decoded} (raw: {value.hex()})\n  {details}"

# --- Scan Functions ---
async def run_quick_scan():
    devices = await BleakScanner.discover()
    if not devices:
        print("No BLE devices found.")
        return
    print("\nRunning Quick Scan:")
    results = []
    for device in devices:
        device_info = {
            "name": device.name,
            "address": device.address,
            "rssi": device.rssi,
            "metadata": device.metadata,
            "manufacturer_data": {},
            "service_uuids": []
        }
        ad = getattr(device, "advertisement_data", None)
        if ad:
            device_info["manufacturer_data"] = ad.manufacturer_data
            # Optionally include service UUIDs
            device_info["service_uuids"] = ad.service_uuids
        else:
            device_info["manufacturer_data"] = device.metadata.get("manufacturer_data", {})
        results.append(device_info)
        print(f"\nDevice: {device.name} - {device.address}")
        if device_info["manufacturer_data"]:
            print("  Manufacturer data (raw):", device_info["manufacturer_data"])
        else:
            print("  Manufacturer data not available; chipset Unknown.")
        cod = device.metadata.get("class_of_device")
        if cod is not None:
            print(decode_class_of_device(cod))
        else:
            print("  Class of Device not available.")
    # Save results to a json file.
    save_scan_results(results, scan_type="quick_scan")

async def run_detailed_scan():
    devices = await BleakScanner.discover()
    if not devices:
        print("No BLE devices found.")
        return
    print("\nRunning Detailed Scan:")
    results = []
    for device in devices:
        device_info = {
            "name": device.name,
            "address": device.address,
            "rssi": device.rssi,
            "advertisement_data": {},
            "manufacturer_data": {},
            "service_uuids": [],
            "detailed_services": []  # New field for GATT services details.
        }
        ad = getattr(device, "advertisement_data", None)
        if ad:
            device_info["advertisement_data"] = {
                "tx_power": ad.tx_power,
                "service_uuids": ad.service_uuids,
                "manufacturer_data": ad.manufacturer_data
            }
            device_info["manufacturer_data"] = ad.manufacturer_data
            device_info["service_uuids"] = ad.service_uuids
        else:
            device_info["manufacturer_data"] = device.metadata.get("manufacturer_data", {})
        
        print(f"\nDevice: {device.name} - {device.address}")
        # Process Manufacturer Data
        if device_info["manufacturer_data"]:
            print("  Manufacturer data (raw):", device_info["manufacturer_data"])
            for key, val in device_info["manufacturer_data"].items():
                try:
                    hex_key = f"0x{int(key):04X}"
                except Exception:
                    hex_key = key
                detail = lookup_details(hex_key, category="company_identifiers")
                print(f"    {hex_key} -> {detail}")
        else:
            print("  Manufacturer data not available; chipset Unknown.")
        # Process Service UUIDs from advertisement
        if device_info["service_uuids"]:
            print("  Advertised Services:", device_info["service_uuids"])
            for uuid in device_info["service_uuids"]:
                extra = lookup_details(uuid, category="service_uuids")
                if extra:
                    print(f"    Service {uuid} Detail: {extra}")
        else:
            print("  No advertised service UUIDs available.")

        # Connect and get full GATT service details.
        details = await get_device_details(device.address)
        device_info["detailed_services"] = details
        if details:
            for service in details:
                print(f"  - Service: {service.get('name', 'Unknown')} (UUID: {service.get('uuid')}, Handle: {service.get('handle')})")
                if service.get("extra"):
                    print(f"       Extra: {service.get('extra')}")
                for char in service.get("characteristics", []):
                    print(f"      - Characteristic: {char.get('uuid')}, Value: {char.get('value')}, Decoded: {char.get('decoded')}")
                    if char.get("extra"):
                        print(f"           Extra: {char.get('extra')}")
        else:
            print("  No detailed services obtained.")
        
        # Append the enriched device info
        results.append(device_info)
    # Save results to a JSON file.
    save_scan_results(results, scan_type="detailed_scan")

# --- Live Scan Functions ---

async def run_live_scan():
    """
    Performs a basic live scan that opens a matplotlib window with two subplots.
    The scan is canceled when you press "q" in the GUI window or close the window.
    Now, discovered devices are remembered; only new devices are added, and existing devices update their RSSI.
    """
    print("\nStarting Live Scan. Press 'q' in the window to cancel.")
    # Initialize persistent dictionary for devices.
    live_scan_data = {"devices_found": 0, "devices": {}}
    live_chart_task = asyncio.create_task(bleak_stats.async_live_update_stats_data(live_scan_data))
    
    async def live_scan_loop():
        while plt.get_fignums():
            devices = await BleakScanner.discover(timeout=2.0)
            # Update persistent devices dict.
            for device in devices:
                addr = device.address
                # If device is new, add its data; otherwise update the RSSI.
                if addr not in live_scan_data["devices"]:
                    live_scan_data["devices"][addr] = {
                        "name": device.name,
                        "address": addr,
                        "rssi": device.rssi,
                        "tx_power": device.metadata.get("tx_power", None),
                        "advertisement_interval_ms": device.metadata.get("advertisement_interval_ms", None),
                        "manufacturer_data": device.metadata.get("manufacturer_data", {}),
                        "service_uuids": device.metadata.get("service_uuids", []),
                        "distance_m": None
                    }
                else:
                    live_scan_data["devices"][addr]["rssi"] = device.rssi
            live_scan_data["devices_found"] = len(live_scan_data["devices"])
            print(f"\nLive Scan: {len(devices)} devices detected this cycle, {live_scan_data['devices_found']} total new devices stored.")
            await asyncio.sleep(0.5)
    
    live_scan_loop_task = asyncio.create_task(live_scan_loop())
    await live_chart_task
    live_scan_loop_task.cancel()
    try:
        await live_scan_loop_task
    except asyncio.CancelledError:
        pass
    # Only use plt.get_fignums and plt.close if available
    if plt is not None and hasattr(plt, "get_fignums") and hasattr(plt, "close"):
        while plt.get_fignums():
            plt.close("all")  # type: ignore

async def run_detailed_live_scan():
    """
    Runs a detailed live scan and updates live_scan_data with discovered device info.
    The interactive GUI (from bleak_stats.async_live_update_detailed_stats_data) runs concurrently.
    Cancellation is handled via the GUI (press 'q' or close the window).
    """
    print("\nStarting Detailed Live Scan with Detailed Visualization. Close the window or press 'q' in it to cancel.")
    live_scan_data = {"devices": []}
    # Launch the interactive GUI with multiple chart pages.
    live_chart_task = asyncio.create_task(bleak_stats.async_live_update_detailed_stats_data(live_scan_data))
    
    async def detailed_live_scan_loop():
        while plt.get_fignums():
            devices = await BleakScanner.discover(timeout=2.0)
            detailed_list = []
            for device in devices:
                rssi = device.rssi
                tx_power = device.metadata.get("tx_power", None)
                adv_interval = device.metadata.get("advertisement_interval_ms", None)
                if tx_power is not None and rssi is not None:
                    distance_m = 10 ** ((tx_power - rssi) / 20)
                else:
                    distance_m = None
                detailed_list.append({
                    "address": device.address,
                    "name": device.name,
                    "rssi": rssi,
                    "tx_power": tx_power,
                    "advertisement_interval_ms": adv_interval,
                    "distance_m": distance_m,
                    "manufacturer_data": device.metadata.get("manufacturer_data", {})
                })
            live_scan_data["devices"] = detailed_list
            print(f"\nDetailed Live Scan: {len(detailed_list)} devices found.")
            await asyncio.sleep(0.5)
    
    live_scan_loop_task = asyncio.create_task(detailed_live_scan_loop())
    await live_chart_task
    live_scan_loop_task.cancel()
    try:
        await live_scan_loop_task
    except asyncio.CancelledError:
        pass
    if plt is not None and hasattr(plt, "close"):
        plt.close('all')  # type: ignore

async def read_all_characteristics(address):
    try:
        async with BleakClient(address) as client:
            for service in client.services:
                print(f"\nService {service.uuid}: {lookup_details(service.uuid, category='service_uuids')}")
                for char in service.characteristics:
                    raw_val = None
                    try:
                        raw_val = await client.read_gatt_char(char.uuid)
                        decoded_val = raw_val.decode(errors="ignore")
                    except Exception as e:
                        decoded_val = f"Error: {e}"
                    if raw_val is not None:
                        print(f"  Characteristic {char.uuid}: {decoded_val} (raw: {raw_val.hex()})")
                    else:
                        print(f"  Characteristic {char.uuid}: {decoded_val} (raw: None)")
                    print(f"    {lookup_details(char.uuid, category='characteristic_uuids')}")
    except Exception as e:
        print(f"Error connecting to {address}: {e}")

def print_device_details(device):
    # Device basic Info
    print(f"Device Name: {device.name}")
    print(f"Address: {device.address}")
    
    # Manufacturer Data
    if hasattr(device, 'advertisement_data') and device.advertisement_data:
        m_data = device.advertisement_data.manufacturer_data
        if m_data:
            print("\nManufacturer Data:")
            for key, value in m_data.items():
                # Format key as hex.
                key_hex = f"0x{int(key):04X}"
                detail = lookup_details(key_hex, category="company_identifiers")
                print(f"  Key: {key_hex} (raw: {value})  -> {detail}")
    else:
        print("No manufacturer data available.")
    
    # Services and Characteristics (if using BleakClient to connect)
    # Optionally, iterate over discovered services:
    # for service in device.services:
    #     print(f"\nService: {service.uuid} -> {lookup_details(service.uuid, category='service_uuids')}")
    #     for char in service.characteristics:
    #         try:
    #             val = await client.read_gatt_char(char.uuid)
    #             decoded = val.decode(errors="ignore")
    #         except Exception as e:
    #             decoded = "Error reading value"
    #         print(f"  Characteristic: {char.uuid}: {decoded} (raw: {val.hex()})")
    #         print(f"    Details: {lookup_details(char.uuid, category='characteristic_uuids')}")
    # Print additional fields
    print("\nAdditional Advertisement Data:")
    adv = device.advertisement_data
    if adv:
        print(f"  Tx Power: {adv.tx_power}")
        print(f"  Service UUIDs: {adv.service_uuids}")
        # etc.

# --- Menu ---
def main_menu():
    while True:
        print("\n--- deepBle Discovery Tool Menu ---")
        print("1. Update References")
        print("2. Run Quick Scan")
        print("3. Run Detailed Scan")
        print("4. Run Live Scan (Press 'q' to cancel)")
        print("5. Run Detailed Live Scan (Press 'q' to cancel)")
        print("6. Return to Main Menu")
        choice = input("Choose an option: ").strip()
        if choice == "1":
            global CHIPSET_LOOKUP, COD_DATA, REFERENCE_DATA
            if not os.path.exists("bluetooth-sig-public-jsons"):
                print("JSON reference folder not found. Running update utility...")
                try:
                    result = subprocess.run(["python", "utility_scripts/update_bluetooth_sig_jsons.py"],
                                              capture_output=True, text=True, check=True)
                    print(result.stdout)
                except subprocess.CalledProcessError as e:
                    print("Error running update utility:", e.stderr)
                    continue
            else:
                print("Using existing JSON reference files.")
            CHIPSET_LOOKUP = load_company_identifiers(COMPANY_IDENTIFIERS_PATH)
            COD_DATA = load_class_of_device(CLASS_OF_DEVICE_PATH)
            REFERENCE_DATA = load_all_references_from_log()
            print("References updated.")
        elif choice == "2":
            asyncio.run(run_quick_scan())
        elif choice == "3":
            asyncio.run(run_detailed_scan())
        elif choice == "4":
            asyncio.run(run_live_scan())
        elif choice == "5":
            asyncio.run(run_detailed_live_scan())
        elif choice == "6":
            print("Returning to main menu...")
            break
        else:
            print("Invalid option. Please try again.")

if __name__ == "__main__":
    main_menu()