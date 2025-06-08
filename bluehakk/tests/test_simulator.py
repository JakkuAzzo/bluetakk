import asyncio
from types import SimpleNamespace
import pytest
import sys
import types
try:
    from PyQt6.QtWidgets import QApplication
except ImportError:
    QApplication = None

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
    def __init__(self, uuid):
        self.uuid = uuid
        self.properties = ["write"]

class DummyService:
    def __init__(self, uuid):
        self.uuid = uuid
        self.characteristics = [DummyCharacteristic("0000FFF1-0000-1000-8000-00805F9B34FB")]

class DummyClient:
    def __init__(self, address):
        self.address = address

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

    async def get_services(self):
        return [DummyService("0000FFF0-0000-1000-8000-00805F9B34FB")]

    async def write_gatt_char(self, uuid, data):
        pass

    async def read_gatt_char(self, uuid):
        return b"shell"


def test_quick_scan_detects_device(monkeypatch, capsys):
    monkeypatch.setattr(deep.BleakScanner, "discover", _fake_discover)
    asyncio.run(deep.run_quick_scan())
    out = capsys.readouterr().out
    assert "FakeSpeaker" in out


def test_exploit_device(monkeypatch):
    monkeypatch.setattr(ble, "BleakClient", DummyClient)
    res = asyncio.run(ble.run_scan_async("scan_specific", "AA:BB:CC:DD:EE:FF"))
    assert res and res[0]["response"] == "shell"


def test_gui_triggers_scan(monkeypatch):
    import os
    try:
        from PyQt6.QtWidgets import QApplication
    except ImportError:
        QApplication = None
        return  # Skip the test if PyQt6 is not available

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])

    called = False

    async def fake_scan():
        nonlocal called
        called = True

    monkeypatch.setattr(deep, "run_detailed_scan", fake_scan)

    window = bluehakk_gui.MainWindow()
    window.detailed_scan()
    assert called


def test_cli_vuln_path(monkeypatch, capsys):
    import sys
    from types import SimpleNamespace
    import bluehakk  # Ensure bluehakk is loaded in sys.modules
    bt_util_mock = SimpleNamespace(
        check_and_setup=lambda: True,
        run_os_monitoring=lambda: None,
        visualize_results=lambda live=False: None,
    )
    monkeypatch.setattr("bluehakk.bt_util", bt_util_mock)
    monkeypatch.setattr("bluehakk.subprocess", SimpleNamespace(run=lambda *a, **k: None))
    bluehakk_mod = sys.modules.get("bluehakk")
    if bluehakk_mod is not None:
        setattr(bluehakk_mod, "current_os", "posix")
        setattr(bluehakk_mod, "main_menu", lambda: None)
        bluehakk_mod.main_menu()
    monkeypatch.setattr(ble, "run_exploit", lambda addr: [{"service_uuid": "s", "char_uuid": "c", "response": "ok"}])
    monkeypatch.setattr(bluehakk, "visualize_vuln_results", lambda r: None)

    inputs = iter(["2", "AA:BB:CC:DD:EE:FF", "6"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    bluehakk_mod.current_os = "posix"
    asyncio.run(bluehakk_mod.main_menu())
    out = capsys.readouterr().out
    assert "Vulnerability testing completed" in out

    # Replace bluehakk.subprocess and bluehakk.current_os/main_menu accesses with mocks or patching as needed in your test setup.

