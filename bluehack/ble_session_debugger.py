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
        decoded = data.decode("utf-8")
    except:
        decoded = data
    print(f"\n[Notification] {sender}: {decoded}")

async def ensure_connected(client):
    if not client.is_connected:
        print("Reconnecting to target...")
        try:
            await client.connect()
            print("Reconnected.")
        except Exception as e:
            print(f"Reconnection failed: {e}")
            return False
    return True

async def mimic_device_behavior(services):
    print("\n[!] Mimic Mode Activated")
    print("This would normally configure your adapter to advertise the same services/characteristics...")
    print("Detected services:")
    for service in services:
        print(f"  Service: {service.uuid}")
        for char in service.characteristics:
            print(f"    Characteristic: {char.uuid} | Properties: {char.properties}")
    print("(NOTE: This is a placeholder for future peripheral emulation)")

async def start_debugger(client, services):
    writable_chars = find_writable_characteristics(services)
    notifiable_chars = find_notifiable_characteristics(services)
    test_payloads = [b"ping", b"\x00\xff", b"A"*10, b"A"*20, b"{\"fake_attendance\":true}"]

    while True:
        print_menu(writable_chars, notifiable_chars)
        choice = input("Choose an option: ").strip().lower()

        if choice == "a":
            if not await ensure_connected(client):
                continue
            idx = int(input("Select characteristic index to listen to: ")) - 1
            char = notifiable_chars[idx]
            await client.start_notify(char.uuid, handle_notification)
            print(f"Listening to {char.uuid}... Press Enter to stop.")
            try:
                while True:
                    await asyncio.sleep(0.5)
                    if input("Press Enter to stop listening... (leave blank to continue): ") == "":
                        continue
                    break
            finally:
                await client.stop_notify(char.uuid)

        elif choice == "b":
            if not await ensure_connected(client):
                continue
            for char in notifiable_chars:
                await client.start_notify(char.uuid, handle_notification)
            print("Listening to all notifiable characteristics... Press Enter to stop.")
            try:
                while True:
                    await asyncio.sleep(0.5)
                    if input("Press Enter to stop listening... (leave blank to continue): ") == "":
                        continue
                    break
            finally:
                for char in notifiable_chars:
                    await client.stop_notify(char.uuid)

        elif choice == "c":
            if not await ensure_connected(client):
                continue
            all_or_one = input("Send to (a)ll or (o)ne? ").strip().lower()
            if all_or_one == "a":
                for char in writable_chars:
                    for payload in test_payloads:
                        try:
                            await client.write_gatt_char(char.uuid, payload)
                            print(f"Sent to {char.uuid}: {payload}")
                        except Exception as e:
                            print(f"Failed to write to {char.uuid}: {e}")
            else:
                idx = int(input("Select characteristic index to send to: ")) - 1
                char = writable_chars[idx]
                for payload in test_payloads:
                    try:
                        await client.write_gatt_char(char.uuid, payload)
                        print(f"Sent to {char.uuid}: {payload}")
                    except Exception as e:
                        print(f"Failed to write to {char.uuid}: {e}")

        elif choice == "d":
            if not await ensure_connected(client):
                continue
            raw = input("Enter custom payload (string or hex like 0xDEADBEEF): ")
            if raw.startswith("0x"):
                payload = bytes.fromhex(raw[2:])
            else:
                payload = raw.encode("utf-8")
            all_or_one = input("Send to (a)ll or (o)ne? ").strip().lower()
            if all_or_one == "a":
                for char in writable_chars:
                    try:
                        await client.write_gatt_char(char.uuid, payload)
                        print(f"Sent to {char.uuid}: {payload}")
                    except Exception as e:
                        print(f"Failed to write to {char.uuid}: {e}")
            else:
                idx = int(input("Select characteristic index to send to: ")) - 1
                char = writable_chars[idx]
                try:
                    await client.write_gatt_char(char.uuid, payload)
                    print(f"Sent to {char.uuid}: {payload}")
                except Exception as e:
                    print(f"Failed to write to {char.uuid}: {e}")

        elif choice == "m":
            await mimic_device_behavior(services)

        elif choice == "e":
            print("Exiting BLE debugger...")
            break

        else:
            print("Invalid choice. Try again.")
