"""Simple Bluetooth peripheral simulator using CoreBluetooth via PyObjC.

This module exposes fake BLE devices that Bluehakk can discover and
interact with. The implementation focuses on macOS where PyObjC can
interface with CoreBluetooth. Each simulated device advertises a set of
services and characteristics.
"""

import sys
import platform

IS_MAC = sys.platform == "darwin"
IS_WIN = sys.platform.startswith("win")
IS_LINUX = sys.platform.startswith("linux")

try:
    from Foundation import NSObject
    import CoreBluetooth
    from PyObjCTools import AppHelper
except ImportError:
    Foundation = None
    CoreBluetooth = None
    NSObject = object
    class AppHelper:
        @staticmethod
        def runConsoleEventLoop(*a, **k):
            print("Peripheral simulation is only available on macOS with CoreBluetooth.")
            return

# --- Cross-platform Peripheral Simulator ---
class CrossPlatformPeripheralSimulator:
    """A simple in-memory BLE peripheral simulator for Windows/Linux."""
    def __init__(self, profile):
        self.profile = profile
        self.running = False
        self.services = profile.get("services", [])
        self.name = profile.get("name", "SimPeripheral")

    def start(self):
        self.running = True
        print(f"[SIM] Peripheral '{self.name}' started with services: {self.services}")
        print("[SIM] (Note: This is an in-memory simulation. No real BLE advertising is performed.)")

    def stop(self):
        self.running = False
        print(f"[SIM] Peripheral '{self.name}' stopped.")

# placeholder constants so the module imports on non-mac platforms
CBCharacteristicPropertyRead = 0
CBCharacteristicPropertyWrite = 0
CBAttributePermissionsReadable = 0
CBAttributePermissionsWriteable = 0

def is_supported_platform():
    plat = sys.platform
    if plat.startswith("win") or plat.startswith("linux") or plat == "darwin":
        return True
    return False

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
    if not is_supported_platform():
        raise RuntimeError("This simulator is only supported on Windows, Linux, and macOS.")
    if CoreBluetooth is None:
        raise RuntimeError("CoreBluetooth not available. Simulator only works on macOS with PyObjC installed.")
    if device_type not in DEVICE_PROFILES:
        raise ValueError(f"Unknown device profile: {device_type}")

    profile = DEVICE_PROFILES[device_type]
    if IS_MAC:
        PeripheralDelegate.alloc().initWithProfile_(profile)
        print(f"[macOS] Starting CoreBluetooth simulator for profile: {device_type}")
        AppHelper.runConsoleEventLoop(installInterrupt=True)
    elif IS_WIN or IS_LINUX:
        print(f"[SIM] Starting cross-platform in-memory simulator for profile: {device_type}")
        sim = CrossPlatformPeripheralSimulator(profile)
        sim.start()
        return sim
    else:
        print("Unsupported platform for peripheral simulation.")
        return


if __name__ == "__main__":  # pragma: no cover - manual use
    dt = sys.argv[1] if len(sys.argv) > 1 else "speaker"
    start_simulator(dt)
