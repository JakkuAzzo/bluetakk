import sys
import asyncio


if len(sys.argv) < 2:
    print("Usage: python3 bleak_connect_test.py <DEVICE_ADDRESS>")
    sys.exit(1)

address = sys.argv[1]

async def main():
    from bleak import BleakClient
    print(f"Attempting to connect to {address}...")
    try:
        async with BleakClient(address) as client:
            # ``is_connected`` is a boolean property, not a coroutine
            connected = client.is_connected
            print(f"Connected: {connected}")
            if connected:
                print("Services:")
                for service in await client.get_services():
                    print(service)
    except Exception as e:
        print(f"Failed to connect: {e}")

if __name__ == "__main__":
    asyncio.run(main())
