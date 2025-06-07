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
