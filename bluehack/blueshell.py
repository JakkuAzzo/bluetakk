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
    try:
        uuids = await bleak_discover_2.get_shell_service_uuids(device_address)
        if uuids:
            return uuids
        else:
            print("No UUIDs returned by get_shell_service_uuids; using fallback values.")
    except Exception as e:
        print("Error in get_shell_service_uuids:", e)
    # Fallback placeholder UUIDs—update these as needed.
    return {
        "shell_service_uuid": "0000xxxx-0000-1000-8000-00805f9b34fb",
        "read_char_uuid":    "0000yyyy-0000-1000-8000-00805f9b34fb",
        "write_char_uuid":   "0000zzzz-0000-1000-8000-00805f9b34fb"
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
        if client.is_connected:
            print(f"Connected to {device_name}")
            await shell_session(client, READ_CHAR_UUID, WRITE_CHAR_UUID)
        else:
            print("Failed to connect.")
            
if __name__ == '__main__':
    asyncio.run(main())