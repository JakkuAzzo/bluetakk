import os
import re
import yaml
import json
import asyncio
import subprocess
from bleak import BleakScanner, BleakClient

# Import centralized utilities
from utility_scripts import check_bt_utilities as bt_util
import bleak_stats
import matplotlib.pyplot as plt

# --- Custom YAML Loader to Preserve Hex Strings ---
class HexStringLoader(yaml.SafeLoader):
    pass

def hex_int_constructor(loader, node):
    value = loader.construct_scalar(node)
    if re.match(r'^0[xX][0-9a-fA-F]+$', value):
        return value
    try:
        return int(value)
    except ValueError:
        return value

HexStringLoader.add_constructor('tag:yaml.org,2002:int', hex_int_constructor)

# --- Basic Reference Loaders ---
def load_company_identifiers(json_path):
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
            lookup = {}
            # Assume each entry has keys: value, name, description, identifier, etc.
            for entry in data.get("company_identifiers", []):
                key = entry.get("value")  # keep as string (e.g. "0x004C")
                lookup[key] = {
                    "name": entry.get("name"),
                    "description": entry.get("description", "No description available"),
                    "identifier": entry.get("identifier", key)
                    # add any additional fields here.
                }
            return lookup
    except Exception as e:
        print(f"Error loading JSON from {json_path}: {e}")
        return {}

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
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
COMPANY_IDENTIFIERS_PATH = os.path.join(
    BASE_DIR,
    "bluetooth-sig-public-jsons",
    "assigned_numbers",
    "company_identifiers",
    "company_identifiers.json",
)
CLASS_OF_DEVICE_PATH = os.path.join(
    BASE_DIR,
    "bluetooth-sig-public-jsons",
    "assigned_numbers",
    "core",
    "class_of_device.json",
)
LOG_FILE_PATH = os.path.join(BASE_DIR, "bluetooth_sig_jsons.txt")

CHIPSET_LOOKUP = load_company_identifiers(COMPANY_IDENTIFIERS_PATH)
COD_DATA = load_class_of_device(CLASS_OF_DEVICE_PATH)
REFERENCE_DATA = load_all_references_from_log(LOG_FILE_PATH)

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
        if hex_key in CHIPSET_LOOKUP:
            info = CHIPSET_LOOKUP[hex_key]
            name = info.get("name", "Unknown")
            return f"{name} ({hex_key})"
    return "Unknown"

def decode_class_of_device(cod_value):
    try:
        val = int(cod_value, 0) if isinstance(cod_value, str) else int(cod_value)
    except Exception:
        return f"Class of Device: {cod_value}"
    major = (val >> 8) & 0x1F
    minor = (val >> 2) & 0x3F
    services = val >> 13
    major_entry = next(
        (d for d in COD_DATA.get("cod_device_class", []) if d.get("major") == major),
        None,
    )
    major_name = major_entry.get("name") if major_entry else "Unknown"
    minor_name = None
    if major_entry and major_entry.get("minor"):
        m = next((mi for mi in major_entry["minor"] if mi.get("value") == minor), None)
        if m:
            minor_name = m.get("name")
    service_names = [
        s["name"]
        for s in COD_DATA.get("cod_services", [])
        if services & (1 << s.get("bit", 0))
    ]
    svc_str = ", ".join(service_names) if service_names else "No services"
    return f"{major_name} / {minor_name or 'Unknown'}; Services: {svc_str}"

def generate_fingerprint(device):
    """Return a simple fingerprint string based on advertisement data."""
    ad = getattr(device, "advertisement_data", None)
    parts = []
    if ad:
        if ad.manufacturer_data:
            keys = "-".join(f"0x{int(k):04X}" for k in ad.manufacturer_data.keys())
            parts.append(f"MD:{keys}")
        if ad.service_uuids:
            uuids = "-".join(sorted(ad.service_uuids))
            parts.append(f"SV:{uuids}")
        if ad.tx_power is not None:
            parts.append(f"TX:{ad.tx_power}")
    if hasattr(device, "rssi") and device.rssi is not None:
        parts.append(f"RSSI:{device.rssi}")
    return "|".join(parts)

def format_uuid_forms(uuid_str):
    pattern = re.compile(r"^0000([0-9a-fA-F]{4})-0000-1000-8000-00805f9b34fb$")
    m = pattern.match(uuid_str.lower())
    if m:
        short = "0x" + m.group(1).upper()
        return f"{short} / {uuid_str}"
    return uuid_str

def format_manufacturer_data(manufacturer_data):
    output = ""
    for key, value in manufacturer_data.items():
        key_hex = f"0x{int(key):04X}"
        details = lookup_details(key_hex, category="company_identifiers")
        output += f"{key_hex} (raw: {value}) -> {details}\n"
    return output.strip()

def format_service_details(service):
    uuid_fmt = format_uuid_forms(str(service.uuid))
    return f"Service {uuid_fmt}: {lookup_details(service.uuid, 'service_uuids')}"

def format_characteristic_details(char, value):
    try:
        decoded = value.decode(errors="ignore")
    except Exception:
        decoded = "N/A"
    uuid_fmt = format_uuid_forms(str(char.uuid))
    details = lookup_details(char.uuid, 'characteristic_uuids')
    return f"Characteristic {uuid_fmt}: {decoded} (raw: {value.hex()})\n  {details}"

# --- Scan Functions ---
async def _quick_device(device):
    print(f"\nDevice: {device.name} - {device.address}")
    ad = getattr(device, "advertisement_data", None)
    manufacturer_data = ad.manufacturer_data if ad else {}
    if manufacturer_data:
        print("  Manufacturer data (raw):", manufacturer_data)
        for key, val in manufacturer_data.items():
            print(f"  Manufacturer key {key} as hex: 0x{key:04X} -> value: {val.hex()}")
        chipset = decode_manufacturer_data(manufacturer_data)
        print(f"  ↳ Detected Chipset: {chipset}")
    else:
        print("  ↳ Manufacturer data not available; chipset Unknown.")
    cod = None
    if ad and hasattr(ad, 'manufacturer_data'):
        cod = ad.manufacturer_data.get('class_of_device')
    if cod is None:
        cod = getattr(device, 'metadata', {}).get('class_of_device')
    if cod is not None:
        print(decode_class_of_device(cod))
    else:
        print("  ↳ Class of Device not available.")
    print(f"  ↳ Fingerprint: {generate_fingerprint(device)}")

async def run_quick_scan(timeout: float = 5.0):
    devices = await BleakScanner.discover(timeout=timeout)
    if not devices:
        print("No BLE devices found.")
        return
    print("\nRunning Quick Scan:")
    await asyncio.gather(*[_quick_device(d) for d in devices])

async def _detailed_device(device):
    print(f"\nDevice: {device.name} - {device.address}")
    if hasattr(device, 'advertisement_data') and device.advertisement_data:
        manufacturer_data = device.advertisement_data.manufacturer_data
        service_uuids = device.advertisement_data.service_uuids
    else:
        manufacturer_data = {}
        service_uuids = []
        print("Warning: advertisement_data not available for device", device.address)
    if manufacturer_data:
        print("  Manufacturer data (raw):", manufacturer_data)
        for key, val in manufacturer_data.items():
            hex_key = f"0x{key:04X}"
            print(f"  Manufacturer key {key} as hex: {hex_key} -> value: {val.hex()}")
            extra = lookup_details(key)
            if extra:
                print(f"    Extra Detail for {hex_key}: {extra}")
        chipset = decode_manufacturer_data(manufacturer_data)
        print(f"  ↳ Detected Chipset: {chipset}")
    else:
        print("  ↳ Manufacturer data not available; chipset Unknown.")
    if service_uuids:
        formatted = [format_uuid_forms(u) for u in service_uuids]
        print("  ↳ Services: ", formatted)
        for uuid in service_uuids:
            extra = lookup_details(uuid, category="service_uuids")
            if extra:
                print(f"    Service {format_uuid_forms(uuid)} Detail: {extra}")
    else:
        print("  ↳ No service UUIDs available.")
    cod = None
    if hasattr(device, 'advertisement_data') and device.advertisement_data:
        cod = device.advertisement_data.manufacturer_data.get('class_of_device')
    if cod is None and hasattr(device, 'metadata'):
        cod = device.metadata.get('class_of_device')
    if cod is not None:
        print(decode_class_of_device(cod))
    else:
        print("  ↳ Class of Device not available.")
    print(f"  ↳ Fingerprint: {generate_fingerprint(device)}")
    print("  Full device details:", device)

async def run_detailed_scan(timeout: float = 10.0):
    devices = await BleakScanner.discover(timeout=timeout)
    if not devices:
        print("No BLE devices found.")
        return
    print("\nRunning Detailed Scan:")
    await asyncio.gather(*[_detailed_device(d) for d in devices])

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
                        "rssi": device.rssi
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
    plt.close("all")

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
                ad = getattr(device, 'advertisement_data', None)
                tx_power = ad.tx_power if ad else None
                adv_interval = ad.advertisement_interval_ms if ad else None
                if tx_power is not None and rssi is not None:
                    distance_m = 10 ** ((tx_power - rssi) / 20)
                else:
                    distance_m = None
                manufacturer_data = ad.manufacturer_data if ad else {}
                detailed_list.append({
                    "address": device.address,
                    "name": device.name,
                    "rssi": rssi,
                    "tx_power": tx_power,
                    "advertisement_interval_ms": adv_interval,
                    "distance_m": distance_m,
                    "manufacturer_data": manufacturer_data
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
    plt.close('all')

async def read_all_characteristics(address):
    try:
        async with BleakClient(address) as client:
            for service in client.services:
                print(f"\nService {service.uuid}: {lookup_details(service.uuid, category='service_uuids')}")
                for char in service.characteristics:
                    try:
                        raw_val = await client.read_gatt_char(char.uuid)
                        decoded_val = raw_val.decode(errors="ignore")
                    except Exception as e:
                        decoded_val = f"Error: {e}"
                    print(f"  Characteristic {char.uuid}: {decoded_val} (raw: {raw_val.hex()})")
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
            REFERENCE_DATA = load_all_references_from_log(LOG_FILE_PATH)
            print("References updated.")
        elif choice == "2":
            asyncio.run(run_quick_scan(timeout=5.0))
        elif choice == "3":
            asyncio.run(run_detailed_scan(timeout=10.0))
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
