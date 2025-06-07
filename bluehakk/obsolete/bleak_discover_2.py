import asyncio
from bleak import BleakScanner, BleakClient

async def scan_single_device(address):
    print(f"Scanning for device with address {address}...")
    d = await BleakScanner(scanning_mode="active").find_device_by_address(
        device_identifier=address, timeout=10)
    print("Scan complete.")
    if not d:
        print(f"Device with address {address} not found.")
    return d

async def scan_devices():
    print("Scanning for nearby Bluetooth devices...")
    devices = await BleakScanner.discover()
    return devices

async def get_device_details(address):
    """
    Retrieve detailed service information from the Bluetooth device.
    """
    details = {}
    try:
        async with BleakClient(address) as client:
            services = await client.get_services()
            details["services"] = []
            for service in services:
                service_info = {
                    "name": service.description,
                    "uuid": service.uuid,
                    "characteristics": [char.uuid for char in service.characteristics]
                }
                details["services"].append(service_info)
    except Exception as e:
        print(f"Failed to get services for {address}: {e}")
    return details

async def get_shell_service_uuids(device_address):
    """
    Retrieve the UUIDs for the shell service by looking for a service whose description 
    contains 'shell' (case-insensitive). Returns a dict with keys:
    'shell_service_uuid', 'read_char_uuid', 'write_char_uuid'.
    """
    uuids = {}
    try:
        async with BleakClient(device_address) as client:
            services = await client.get_services()
            for service in services:
                if "shell" in service.description.lower():
                    uuids["shell_service_uuid"] = service.uuid
                    for char in service.characteristics:
                        if "read" in char.properties and "read_char_uuid" not in uuids:
                            uuids["read_char_uuid"] = char.uuid
                        if "write" in char.properties and "write_char_uuid" not in uuids:
                            uuids["write_char_uuid"] = char.uuid
                    break
    except Exception as e:
        print(f"Error obtaining shell service UUIDs for {device_address}: {e}")
    return uuids

async def main():
    devices = await BleakScanner.discover()
    if not devices:
        print("No devices found.")
        return
    print(f"\nFound devices: {len(devices)}")
    for idx, device in enumerate(devices, start=1):
        print(f"{idx}. {device.name} ({device.address})")
    # This main() is for testing purposes.
    
if __name__ == "__main__":
    asyncio.run(main())
