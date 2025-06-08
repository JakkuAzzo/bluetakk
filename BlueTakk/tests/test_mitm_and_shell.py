import asyncio
import sys
import types
from types import SimpleNamespace
import importlib

import blueshell
from peripheral_simulator import simulator as sim

def _ensure_bleak_exc():
    if "bleak.exc" not in sys.modules:
        exc_mod = types.ModuleType("bleak.exc")
        setattr(exc_mod, "BleakError", Exception)
        sys.modules["bleak.exc"] = exc_mod

def test_mac_mitm_import(monkeypatch):
    _ensure_bleak_exc()
    monkeypatch.setitem(sys.modules, "objc", types.ModuleType("objc"))
    import mac_mitm
    importlib.reload(mac_mitm)
    assert hasattr(mac_mitm, "MacMITMProxy")

def test_win_mitm_import(monkeypatch):
    _ensure_bleak_exc()
    monkeypatch.setitem(sys.modules, "winrt", types.ModuleType("winrt"))
    import win_mitm
    importlib.reload(win_mitm)
    assert hasattr(win_mitm, "WindowsMITMProxy")

# --- Blueshell UUID detection ---
async def _fake_get_shell_service_uuids(addr):
    return {}

class DummyChar:
    def __init__(self, uuid):
        self.uuid = uuid
        self.properties = ["read", "write"]

class DummyService:
    def __init__(self):
        self.uuid = "service"
        self.description = "Shell Service"
        self.characteristics = [DummyChar("char")]

class DummyClient:
    def __init__(self, address):
        self.address = address
        self.is_connected = True

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

    async def get_services(self):
        return [DummyService()]

# --- Tests ---

def test_get_shell_uuids_fallback(monkeypatch):
    monkeypatch.setattr(blueshell.bleak_discover_2, "get_shell_service_uuids", _fake_get_shell_service_uuids)
    monkeypatch.setattr(blueshell, "BleakClient", lambda addr: DummyClient(addr))
    uuids = asyncio.run(blueshell.get_shell_uuids("AA"))
    assert uuids["read_char_uuid"] == "char"


def test_start_simulator_paths(monkeypatch):
    monkeypatch.setattr(sim.sys, "platform", "win32", raising=False)
    monkeypatch.setattr(sim, "IS_WIN", True, raising=False)
    monkeypatch.setattr(sim, "IS_LINUX", False, raising=False)
    called = {}
    monkeypatch.setattr(sim, "WindowsPeripheralSimulator", lambda p: SimpleNamespace(start=lambda: called.setdefault("win", True)))
    sim.start_simulator("speaker")
    assert called.get("win")


