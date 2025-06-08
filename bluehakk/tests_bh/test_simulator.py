import asyncio
from types import SimpleNamespace
import pytest
pytest.skip("legacy tests", allow_module_level=True)
import deepBle_discovery_tool as deep
import bleshellexploit as ble
import bluehakk
import bluehakk_gui

class DummyAdvData:
    def __init__(self, name, service_uuids):
        self.local_name = name
        self.service_uuids = service_uuids
        self.manufacturer_data = {}
        self.tx_power = -50
        self.advertisement_interval_ms = 100

class DummyDevice:
    def __init__(self, name):
        self.name = name
        self.address = "AA:BB:CC:DD:EE:FF"
        self.rssi = -40
        self.advertisement_data = DummyAdvData(name, ["0000180A-0000-1000-8000-00805F9B34FB"])


async def _fake_discover(*args, **kwargs):
    return [DummyDevice("FakeSpeaker")]

class DummyCharacteristic:
    pass
