import sys
import asyncio
from bleak import BleakClient

async def reverse_shell(client: BleakClient):
    services = await client.get_services()
    print("\nConnected to device. Entering Bluetooth shell. Type 'help' for a list of commands, or 'exit' to quit.")
    while True:
        cmd = input("bluetooth> ").strip()
        if cmd.lower() in ("exit", "quit"):
            print("Exiting shell.")
            break
        elif cmd.lower() == "help":
            print("Available commands:")
            print("  ls                                      - List services and characteristics")
            print("  read <characteristic_uuid>              - Read value from a characteristic (hex encoded)")
            print("  write <characteristic_uuid> <data>        - Write hex data to a characteristic (e.g., A1B2C3)")
            print("  shutdown                                - Send shutdown command to the device")
            print("  volume up                               - Increase device volume")
            print("  volume down                             - Decrease device volume")
            print("  open app <app_identifier>               - Open an app on the device")
            print("  close app <app_identifier>              - Close an app on the device")
            print("  exit                                    - Exit shell")
        elif cmd.lower() == "ls":
            for service in services:
                print(f"\nService: {service.uuid} - {service.description}")
                for char in service.characteristics:
                    print(f"  Characteristic: {char.uuid} - {char.properties}")
        elif cmd.startswith("read "):
            parts = cmd.split()
            if len(parts) != 2:
                print("Usage: read <characteristic_uuid>")
                continue
            char_uuid = parts[1]
            try:
                value = await client.read_gatt_char(char_uuid)
                print(f"Value: {value.hex()}")
            except Exception as e:
                print(f"Error reading characteristic: {e}")
        elif cmd.startswith("write "):
            parts = cmd.split()
            if len(parts) < 3:
                print("Usage: write <characteristic_uuid> <data>")
                continue
            char_uuid = parts[1]
            data_str = "".join(parts[2:])
            try:
                data = bytes.fromhex(data_str)
                await client.write_gatt_char(char_uuid, data)
                print("Write successful.")
            except Exception as e:
                print(f"Error writing characteristic: {e}")
        elif cmd.lower() == "shutdown":
            print("Attempting to shutdown device...")
            char_uuid = "0000dead-beef-0000-0000-abcdefabcdef"  # placeholder UUID
            try:
                data = bytes.fromhex("01")  # placeholder payload
                await client.write_gatt_char(char_uuid, data)
                print("Shutdown command sent.")
            except Exception as e:
                print(f"Error sending shutdown command: {e}")
        elif cmd.lower() == "volume up":
            print("Attempting to increase volume...")
            char_uuid = "0000volu-0000-0000-0000-abcdefabcdef"  # placeholder UUID
            try:
                data = bytes.fromhex("01")
                await client.write_gatt_char(char_uuid, data)
                print("Volume increase command sent.")
            except Exception as e:
                print(f"Error sending volume up command: {e}")
        elif cmd.lower() == "volume down":
            print("Attempting to decrease volume...")
            char_uuid = "0000vold-0000-0000-0000-abcdefabcdef"  # placeholder UUID
            try:
                data = bytes.fromhex("01")
                await client.write_gatt_char(char_uuid, data)
                print("Volume decrease command sent.")
            except Exception as e:
                print(f"Error sending volume down command: {e}")
        elif cmd.lower().startswith("open app"):
            parts = cmd.split(maxsplit=2)
            if len(parts) != 3:
                print("Usage: open app <app_identifier>")
                continue
            app_id = parts[2]
            print(f"Attempting to open app '{app_id}'...")
            char_uuid = "0000appa-0000-0000-0000-abcdefabcdef"  # placeholder UUID
            try:
                data = app_id.encode()
                await client.write_gatt_char(char_uuid, data)
                print("Open app command sent.")
            except Exception as e:
                print(f"Error sending open app command: {e}")
        elif cmd.lower().startswith("close app"):
            parts = cmd.split(maxsplit=2)
            if len(parts) != 3:
                print("Usage: close app <app_identifier>")
                continue
            app_id = parts[2]
            print(f"Attempting to close app '{app_id}'...")
            char_uuid = "0000appc-0000-0000-0000-abcdefabcdef"  # placeholder UUID
            try:
                data = app_id.encode()
                await client.write_gatt_char(char_uuid, data)
                print("Close app command sent.")
            except Exception as e:
                print(f"Error sending close app command: {e}")
        else:
            print("Unknown command. Type 'help' for available commands.")

async def main():
    if len(sys.argv) < 2:
        print("Usage: python3 bleak_connect.py <device_address>")
        return

    device_address = sys.argv[1]
    print(f"Connecting to device at {device_address} with a max timeout of 60 seconds...")
    client = BleakClient(device_address)
    try:
        await client.connect(timeout=60)
        if client.is_connected:
            print("Connected to device.")
            await reverse_shell(client)
        else:
            print("Failed to connect to device.")
    except Exception as e:
        print(f"Connection error: {e}")
    finally:
        if client.is_connected:
            await client.disconnect()
            print("Disconnected from device.")

if __name__ == "__main__":
    asyncio.run(main())