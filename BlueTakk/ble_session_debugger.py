import asyncio
import logging
import string

# Guess data type by content
def guess_data_type(value: bytes):
    try:
        text = value.decode("utf-8")
        if all(c in string.printable for c in text):
            return "string"
    except:
        pass
    if all(32 <= b <= 126 for b in value):
        return "ascii"
    return "binary"

def print_menu(writable, notifiable):
    print("\n--- BLE Debugger Menu ---")
    print("Writable Characteristics:")
    for i, char in enumerate(writable):
        print(f"  {i+1}. UUID: {char.uuid}  | Properties: {char.properties}")
    print("\nNotifiable Characteristics:")
    for i, char in enumerate(notifiable):
        print(f"  {i+1}. UUID: {char.uuid}  | Properties: {char.properties}")
    print("\nOptions:")
    print("A. Listen for notifications from a specific characteristic")
    print("B. Listen for all notifiable characteristics")
    print("C. Send pre-made test payloads to all or one")
    print("D. Send custom payload")
    print("M. Mimic device behavior (advertise services/characteristics)")
    print("E. Exit debugger")

def find_writable_characteristics(services):
    writable = []
    for service in services:
        for char in service.characteristics:
            if "write" in char.properties:
                writable.append(char)
    return writable

def find_notifiable_characteristics(services):
    notifiable = []
    for service in services:
        for char in service.characteristics:
            if "notify" in char.properties:
                notifiable.append(char)
    return notifiable

def handle_notification(sender, data):
    try:
        decoded_data = data.decode("utf-8")
        logging.info(f"Notification from {sender}: {decoded_data}")
    except Exception as e:
        logging.error(f"Error handling notification from {sender}: {e}")


async def debugger_loop(address: str):
    """Interactive BLE debugging session."""
    from bleak import BleakClient

    async with BleakClient(address) as client:
        if not client.is_connected:
            print("Failed to connect to device")
            return
        services = await client.get_services()
        writable = find_writable_characteristics(services)
        notifiable = find_notifiable_characteristics(services)

        while True:
            print_menu(writable, notifiable)
            choice = input("Select option: ").strip().upper()

            if choice == "A":
                idx = input("Index to listen: ").strip()
                if idx.isdigit() and 0 < int(idx) <= len(notifiable):
                    char = notifiable[int(idx) - 1]
                    await client.start_notify(char.uuid, handle_notification)
                    input("Listening...press Enter to stop")
                    await client.stop_notify(char.uuid)
            elif choice == "B":
                for char in notifiable:
                    await client.start_notify(char.uuid, handle_notification)
                input("Listening to all...press Enter to stop")
                for char in notifiable:
                    await client.stop_notify(char.uuid)
            elif choice == "C":
                payload = b"test"
                target = input("Send to all or index: ")
                if target.isdigit() and 0 < int(target) <= len(writable):
                    await client.write_gatt_char(writable[int(target)-1].uuid, payload)
                else:
                    for char in writable:
                        await client.write_gatt_char(char.uuid, payload)
            elif choice == "D":
                hex_str = input("Hex payload: ").strip()
                try:
                    data = bytes.fromhex(hex_str)
                except Exception:
                    print("Invalid hex string")
                    continue
                idx = input("Characteristic index: ")
                if idx.isdigit() and 0 < int(idx) <= len(writable):
                    await client.write_gatt_char(writable[int(idx)-1].uuid, data)
            elif choice == "M":
                print("Mimic mode not implemented")
            elif choice == "E":
                break


if __name__ == "__main__":  # pragma: no cover - manual use
    import sys
    if len(sys.argv) < 2:
        print("Usage: python ble_session_debugger.py <device_address>")
        sys.exit(1)
    asyncio.run(debugger_loop(sys.argv[1]))
