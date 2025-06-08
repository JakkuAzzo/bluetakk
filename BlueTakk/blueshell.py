import sys
import asyncio
import argparse
from bleak import BleakClient
import obsolete.bleak_discover_2 as bleak_discover_2  # Now provides get_shell_service_uuids()

def parse_arguments():
    parser = argparse.ArgumentParser(description="BLE Shell Session")
    parser.add_argument("--device_address", type=str, required=True,
                        help="Address of the connected device")
    parser.add_argument("--device_name", type=str, default="",
                        help="Name of the connected device")
    return parser.parse_args()

async def get_shell_uuids(device_address):
    """Detect the shell service UUIDs or return sensible defaults."""
    try:
        uuids = await bleak_discover_2.get_shell_service_uuids(device_address)
        if uuids:
            return uuids
    except Exception as e:
        print("Detection via bleak_discover_2 failed:", e)

    try:
        async with BleakClient(device_address) as client:
            services = await client.get_services()
            for service in services:
                desc = service.description.lower()
                if "shell" in desc or "cmd" in desc or service.uuid.startswith("0000ffe0"):
                    read_uuid = None
                    write_uuid = None
                    for char in service.characteristics:
                        if "read" in char.properties and not read_uuid:
                            read_uuid = char.uuid
                        if "write" in char.properties and not write_uuid:
                            write_uuid = char.uuid
                    if read_uuid and write_uuid:
                        return {
                            "shell_service_uuid": service.uuid,
                            "read_char_uuid": read_uuid,
                            "write_char_uuid": write_uuid,
                        }
    except Exception as exc:
        print("Fallback detection failed:", exc)

    return {
        "shell_service_uuid": "0000feed-0000-1000-8000-00805f9b34fb",
        "read_char_uuid": "0000fe01-0000-1000-8000-00805f9b34fb",
        "write_char_uuid": "0000fe02-0000-1000-8000-00805f9b34fb",
    }

async def shell_session(client: BleakClient, read_char_uuid, write_char_uuid):
    print("Connected. Starting BLE shell session. Type 'exit' to quit.")
    
    def notification_handler(sender, data):
        try:
            sys.stdout.write(data.decode())
            sys.stdout.flush()
        except Exception as e:
            print("Decode error:", e)
        
    await client.start_notify(read_char_uuid, notification_handler)
    
    while True:
        try:
            cmd = input("shell> ")
        except EOFError:
            break
        if cmd.lower() in ("exit", "quit"):
            break
        try:
            await client.write_gatt_char(write_char_uuid, (cmd + "\n").encode())
        except Exception as e:
            print("Write error:", e)
            break
    await client.stop_notify(read_char_uuid)
    
async def main():
    args = parse_arguments()
    device_address = args.device_address
    device_name = args.device_name
    print(f"Attempting to launch shell session on device {device_name} ({device_address})")
    
    uuids = await get_shell_uuids(device_address)
    SHELL_SERVICE_UUID = uuids.get("shell_service_uuid")
    READ_CHAR_UUID = uuids.get("read_char_uuid")
    WRITE_CHAR_UUID = uuids.get("write_char_uuid")
    
    if not (SHELL_SERVICE_UUID and READ_CHAR_UUID and WRITE_CHAR_UUID):
        print("Incomplete shell service UUIDs received.")
        return

    async with BleakClient(device_address) as client:
        if not client.is_connected:
            print("Failed to connect.")
            return
        print(f"Connected to {device_name}")
        await shell_session(client, READ_CHAR_UUID, WRITE_CHAR_UUID)
            
if __name__ == '__main__':
    asyncio.run(main())
