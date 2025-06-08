"""Simple Bluetooth peripheral simulator using CoreBluetooth via PyObjC.

This module exposes fake BLE devices that Bluehakk can discover and
interact with. The implementation focuses on macOS where PyObjC can
interface with CoreBluetooth. Each simulated device advertises a set of
services and characteristics.
"""

import sys
import platform
from typing import TYPE_CHECKING, Optional

IS_MAC = sys.platform == "darwin"
IS_ISH = sys.platform == "ish"
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

if TYPE_CHECKING:  # pragma: no cover - type hints only
    from CoreBluetooth import (  # noqa: F401
        CBPeripheralManager,
        CBManagerStatePoweredOn,
        CBUUID,
        CBMutableCharacteristic,
        CBMutableService,
        CBAdvertisementDataLocalNameKey,
        CBAdvertisementDataServiceUUIDsKey,
    )

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


class LinuxPeripheralSimulator(CrossPlatformPeripheralSimulator):
    """Simulator that attempts to use BlueZ or aiobleserver on Linux."""

    def __init__(self, profile):
        super().__init__(profile)
        self._peripheral = None

    def start(self):
        try:
            from bluezero import adapter, peripheral  # type: ignore

            adapter_addr = list(adapter.Adapter.available())[0].address
            self._peripheral = peripheral.Peripheral(adapter_addr, local_name=self.name)

            for srv_id, svc in enumerate(self.services, start=1):
                self._peripheral.add_service(srv_id=srv_id, uuid=svc["uuid"], primary=True)
                for char_id, char in enumerate(svc.get("characteristics", []), start=1):
                    flags = []
                    props = char.get("properties", 0)
                    if props & CBCharacteristicPropertyRead:
                        flags.append("read")
                    if props & CBCharacteristicPropertyWrite:
                        flags.extend(["write", "write-without-response"])
                    self._peripheral.add_characteristic(
                        srv_id=srv_id,
                        chr_id=char_id,
                        uuid=char["uuid"],
                        value=[],
                        notifying=False,
                        flags=flags,
                    )

            self._peripheral.publish()
            self.running = True
            print(f"[Linux] Advertising '{self.name}' using BlueZ")
        except Exception:
            print(
                "[Linux] BlueZ/bluezero not available. Falling back to in-memory simulation."
            )
            super().start()

    def stop(self):
        if self._peripheral is not None:
            try:
                self._peripheral.unpublish()
            except Exception:
                pass
        super().stop()


class WindowsPeripheralSimulator(CrossPlatformPeripheralSimulator):
    """Simulator using WinRT advertisement APIs when available."""

    def __init__(self, profile):
        super().__init__(profile)
        self._publisher = None

    def start(self):
        try:
            from uuid import UUID
            from winsdk.windows.devices.bluetooth.advertisement import (
                BluetoothLEAdvertisement,
                BluetoothLEAdvertisementPublisher,
                BluetoothLEAdvertisementDataSection,
                BluetoothLEAdvertisementDataTypes,
            )
            from winsdk.windows.storage.streams import DataWriter

            adv = BluetoothLEAdvertisement()
            adv.local_name = self.name

            for svc in self.services:
                writer = DataWriter()
                writer.write_bytes(UUID(svc["uuid"]).bytes_le)
                section = BluetoothLEAdvertisementDataSection(
                    BluetoothLEAdvertisementDataTypes.uuid128_complete,
                    writer.detach_buffer(),
                )
                adv.data_sections.append(section)

            self._publisher = BluetoothLEAdvertisementPublisher(adv)
            self._publisher.start()
            self.running = True
            print(f"[Windows] Advertising '{self.name}' using WinRT")
        except Exception:
            print(
                "[Windows] WinRT BLE API not available. Falling back to in-memory simulation."
            )
            super().start()

    def stop(self):
        if self._publisher is not None:
            try:
                self._publisher.stop()
            except Exception:
                pass
        super().stop()

# placeholder constants so the module imports on non-mac platforms
CBCharacteristicPropertyRead = 0
CBCharacteristicPropertyWrite = 0
CBAttributePermissionsReadable = 0
CBAttributePermissionsWriteable = 0

def is_supported_platform():
    """Return True if the current platform is supported."""
    plat = sys.platform
    if (
        plat.startswith("win")
        or plat.startswith("linux")
        or plat == "darwin"
        or plat == "ish"
    ):
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
            self.peripheralManager = getattr(CoreBluetooth, "CBPeripheralManager").alloc().initWithDelegate_queue_options_(
                self, None, None
            )
            return self

        def peripheralManagerDidUpdateState_(self, manager):  # pragma: no cover
            if manager.state() == getattr(CoreBluetooth, "CBManagerStatePoweredOn"):
                self._setup()

        def _setup(self):  # pragma: no cover - requires macOS
            services = []
            for svc in self.profile["services"]:
                uuid = getattr(CoreBluetooth, "CBUUID").UUIDWithString_(svc["uuid"])
                chars = []
                for char in svc.get("characteristics", []):
                    c_uuid = getattr(CoreBluetooth, "CBUUID").UUIDWithString_(char["uuid"])
                    props = char.get(
                        "properties",
                        CBCharacteristicPropertyRead,
                    )
                    perms = char.get(
                        "permissions",
                        CBAttributePermissionsReadable,
                    )
                    c = getattr(CoreBluetooth, "CBMutableCharacteristic").alloc().initWithType_properties_value_permissions_(
                        c_uuid, props, None, perms
                    )
                    chars.append(c)
                service = getattr(CoreBluetooth, "CBMutableService").alloc().initWithType_primary_(
                    uuid, True
                )
                service.setCharacteristics_(chars)
                services.append(service)

            for service in services:
                self.peripheralManager.addService_(service)

            adv_data = {
                getattr(CoreBluetooth, "CBAdvertisementDataLocalNameKey"): self.profile["name"],
                getattr(CoreBluetooth, "CBAdvertisementDataServiceUUIDsKey"): [
                    getattr(CoreBluetooth, "CBUUID").UUIDWithString_(svc["uuid"])
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


def start_simulator(device_type: str = "speaker") -> Optional[CrossPlatformPeripheralSimulator]:
    """Start advertising the specified fake device profile."""
    if not is_supported_platform():
        raise RuntimeError(
            "This simulator is only supported on Windows, Linux, macOS and ish."
        )
    if device_type not in DEVICE_PROFILES:
        raise ValueError(f"Unknown device profile: {device_type}")

    profile = DEVICE_PROFILES[device_type]

    if IS_MAC or IS_ISH:
        if CoreBluetooth is None:
            raise RuntimeError(
                "CoreBluetooth not available. Simulator only works on macOS/iSH with PyObjC installed."
            )
        PeripheralDelegate.alloc().initWithProfile_(profile)
        print(
            f"[macOS] Starting CoreBluetooth simulator for profile: {device_type}"
        )
        AppHelper.runConsoleEventLoop(installInterrupt=True)
    elif IS_LINUX:
        print(f"[Linux] Starting simulator for profile: {device_type}")
        sim = LinuxPeripheralSimulator(profile)
        sim.start()
        return sim
    elif IS_WIN:
        print(f"[Windows] Starting simulator for profile: {device_type}")
        sim = WindowsPeripheralSimulator(profile)
        sim.start()
        return sim
    else:
        print("Unsupported platform for peripheral simulation.")
        return None


if __name__ == "__main__":  # pragma: no cover - manual use
    dt = sys.argv[1] if len(sys.argv) > 1 else "speaker"
    start_simulator(dt)
