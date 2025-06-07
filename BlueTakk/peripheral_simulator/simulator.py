"""Simple Bluetooth peripheral simulator using CoreBluetooth via PyObjC.

This module exposes fake BLE devices that Bluehakk can discover and
interact with. The implementation focuses on macOS where PyObjC can
interface with CoreBluetooth. Each simulated device advertises a set of
services and characteristics.
"""

import sys

try:
    from Foundation import NSObject
    import CoreBluetooth
    from PyObjCTools import AppHelper
except Exception:  # pragma: no cover - import failure on non-mac platforms
    CoreBluetooth = None  # type: ignore
    NSObject = object  # type: ignore
    class AppHelper:  # pragma: no cover - dummy fallback
        @staticmethod
        def runConsoleEventLoop(*a, **k):
            raise RuntimeError("CoreBluetooth not available")

    # placeholder constants so the module imports on non-mac platforms
    CBCharacteristicPropertyRead = 0
    CBCharacteristicPropertyWrite = 0
    CBAttributePermissionsReadable = 0
    CBAttributePermissionsWriteable = 0

if CoreBluetooth is not None:
    class PeripheralDelegate(NSObject):
        """Delegate that sets up services and starts advertising."""

        def initWithProfile_(self, profile):  # type: ignore[override]
            self = super().init()
            if self is None:
                return None
            self.profile = profile
            self.peripheralManager = CoreBluetooth.CBPeripheralManager.alloc().initWithDelegate_queue_options_(
                self, None, None
            )
            return self

        def peripheralManagerDidUpdateState_(self, manager):  # pragma: no cover
            if manager.state() == CoreBluetooth.CBManagerStatePoweredOn:
                self._setup()

        def _setup(self):  # pragma: no cover - requires macOS
            services = []
            for svc in self.profile["services"]:
                uuid = CoreBluetooth.CBUUID.UUIDWithString_(svc["uuid"])
                chars = []
                for char in svc.get("characteristics", []):
                    c_uuid = CoreBluetooth.CBUUID.UUIDWithString_(char["uuid"])
                    props = char.get(
                        "properties",
                        CBCharacteristicPropertyRead,
                    )
                    perms = char.get(
                        "permissions",
                        CBAttributePermissionsReadable,
                    )
                    c = CoreBluetooth.CBMutableCharacteristic.alloc().initWithType_properties_value_permissions_(
                        c_uuid, props, None, perms
                    )
                    chars.append(c)
                service = CoreBluetooth.CBMutableService.alloc().initWithType_primary_(
                    uuid, True
                )
                service.setCharacteristics_(chars)
                services.append(service)

            for service in services:
                self.peripheralManager.addService_(service)

            adv_data = {
                CoreBluetooth.CBAdvertisementDataLocalNameKey: self.profile["name"],
                CoreBluetooth.CBAdvertisementDataServiceUUIDsKey: [
                    CoreBluetooth.CBUUID.UUIDWithString_(svc["uuid"])
                    for svc in self.profile["services"]
                ],
            }
            self.peripheralManager.startAdvertising_(adv_data)


DEVICE_PROFILES = {
    "speaker": {
        "name": "FakeSpeaker",
        "services": [
            {"uuid": "0000180A-0000-1000-8000-00805F9B34FB"},
            {
                "uuid": "0000FFF0-0000-1000-8000-00805F9B34FB",
                "characteristics": [
                    {
                        "uuid": "0000FFF1-0000-1000-8000-00805F9B34FB",
                        "properties": CBCharacteristicPropertyRead
                        | CBCharacteristicPropertyWrite,
                        "permissions": CBAttributePermissionsReadable
                        | CBAttributePermissionsWriteable,
                    }
                ],
            },
        ],
    },
    "watch": {
        "name": "FakeWatch",
        "services": [
            {"uuid": "0000180F-0000-1000-8000-00805F9B34FB"},
            {"uuid": "00001805-0000-1000-8000-00805F9B34FB"},
        ],
    },
    "phone": {
        "name": "FakePhone",
        "services": [
            {"uuid": "00001812-0000-1000-8000-00805F9B34FB"},
            {"uuid": "00001108-0000-1000-8000-00805F9B34FB"},
        ],
    },
}


def start_simulator(device_type: str = "speaker") -> None:
    """Start advertising the specified fake device profile."""
    if CoreBluetooth is None:
        raise RuntimeError("CoreBluetooth not available. Simulator only works on macOS with PyObjC installed.")
    if device_type not in DEVICE_PROFILES:
        raise ValueError(f"Unknown device profile: {device_type}")

    profile = DEVICE_PROFILES[device_type]
    PeripheralDelegate.alloc().initWithProfile_(profile)
    AppHelper.runConsoleEventLoop(installInterrupt=True)


if __name__ == "__main__":  # pragma: no cover - manual use
    dt = sys.argv[1] if len(sys.argv) > 1 else "speaker"
    start_simulator(dt)
