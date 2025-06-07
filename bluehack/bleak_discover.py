import asyncio
import json
import datetime
import time
import os
import sys
from bleak import BleakScanner, BleakClient

async def scan_devices():
    print("Scanning for nearby Bluetooth devices...")
    devices = await BleakScanner.discover()
    return devices

async def get_device_details(address):
    details = []
    try:
        async with BleakClient(address) as client:
            services = await client.get_services()
            for service in services:
                details.append({
                    "name": service.description,
                    "uuid": service.uuid,
                    "characteristics": [char.uuid for char in service.characteristics],
                    "handle": service.handle,
                })
    except Exception as e:
        print(f"Failed to get services for {address}: {e}")
    return details

async def continuous_scan(output, stop_event):
    while not stop_event.is_set():
        devices = await scan_devices()
        if not devices:
            print("No devices found in this scan iteration.")
        else:
            print("\nFound devices:")
            for idx, device in enumerate(devices, start=1):
                print(f"{idx}. {device.name} ({device.address})")
                details = await get_device_details(device.address)
                device_info = {
                    "name": device.name,
                    "address": device.address,
                    "details": details,
                }
                output.append(device_info)
                if details:
                    for service in details:
                        service_name = service.get("name", "Unknown")
                        service_uuid = service.get("uuid", "N/A")
                        characteristics = service.get("characteristics", [])
                        print(f"   - Service: {service_name}, UUID: {service_uuid}, Characteristics: {characteristics}, Handle: {service.get('handle', 'N/A')}")
                else:
                    print("   No additional services found.")
        # Wait a few seconds before the next scan cycle.
        await asyncio.sleep(5)

async def update_output_file_periodically(output, filename, stop_event):
    while not stop_event.is_set():
        try:
            with open(filename, "w") as f:
                json.dump(output, f, indent=4)
            print(f"Output updated to {filename}")
        except Exception as e:
            print(f"Error updating output to {filename}: {e}")
        # Update file every 5 seconds.
        await asyncio.sleep(5)

async def duration_timer(duration, stop_event):
    await asyncio.sleep(duration)
    print(f"Specified duration of {duration} seconds elapsed. Stopping scan.")
    stop_event.set()

async def listen_for_quit(stop_event):
    # Listen for user input in a thread so it doesn't block the event loop.
    while not stop_event.is_set():
        command = await asyncio.to_thread(input, "> ")
        if command.strip().lower() == 'q':
            print("Quit command received. Stopping scan.")
            stop_event.set()
            break
        else:
            print("Unrecognized command. To quit and save, type 'q'.")

async def main():
    output = []
    stop_event = asyncio.Event()

    # Determine duration (in seconds) from optional command-line argument.
    duration = None
    if len(sys.argv) > 1:
        try:
            duration = int(sys.argv[1])
            print(f"Scan will run for {duration} seconds.")
        except Exception as e:
            print(f"Invalid duration provided: {sys.argv[1]}, running until 'q' is pressed.")

    # Ensure recent_scan folder exists.
    recent_folder = os.path.join(os.getcwd(), "recent_scan")
    if not os.path.exists(recent_folder):
        os.makedirs(recent_folder)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(recent_folder, f"bleak_discover_{timestamp}.json")
    print(f"Output file will be: {filename}")

    # Start tasks for scanning, file updating, user input and optional duration timer.
    scan_task = asyncio.create_task(continuous_scan(output, stop_event))
    update_task = asyncio.create_task(update_output_file_periodically(output, filename, stop_event))
    listen_task = asyncio.create_task(listen_for_quit(stop_event))
    
    if duration:
        duration_task = asyncio.create_task(duration_timer(duration, stop_event))
        # Wait until duration expires or quit signal is received.
        await duration_task
    else:
        # Wait until quit signal is received.
        await listen_task

    # Make sure scanning stops.
    stop_event.set()
    await scan_task
    await update_task
    print(f"Final output saved to {filename}")

if __name__ == "__main__":
    asyncio.run(main())
    