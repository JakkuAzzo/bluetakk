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
