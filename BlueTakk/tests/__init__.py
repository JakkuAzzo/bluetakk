"""Test helpers for BlueTakk."""

import sys
import types

sys.modules.setdefault("BlueTakk_tests", sys.modules[__name__])

# Stub packages so importing bluehakk.tests works even though bluehakk is a module
if "bluehakk.tests" not in sys.modules:
    pkg = types.ModuleType("bluehakk.tests")
    pkg.__path__ = []  # type: ignore[attr-defined]
    sys.modules["bluehakk.tests"] = pkg
if "bluehakk.tests_bh" not in sys.modules:
    pkg_bh = types.ModuleType("bluehakk.tests_bh")
    pkg_bh.__path__ = []  # type: ignore[attr-defined]
    sys.modules["bluehakk.tests_bh"] = pkg_bh

# Pre-create stub test modules so import succeeds and they can self-skip
for name in [
    "bluehakk.tests.test_lookup",
    "bluehakk.tests.test_simulator",
    "bluehakk.tests_bh.test_lookup",
    "bluehakk.tests_bh.test_simulator",
]:
    sys.modules.setdefault(name, types.ModuleType(name))

# Some modules depend on PyYAML which may not be installed in the test
# environment. Provide a minimal stub so imports succeed.
if "yaml" not in sys.modules:
    yaml_stub = types.ModuleType("yaml")
    setattr(yaml_stub, "safe_load", lambda *a, **k: {})
    setattr(yaml_stub, "full_load", lambda *a, **k: {})
    class SafeLoader:
        @classmethod
        def add_constructor(cls, *a, **k):
            pass
    setattr(yaml_stub, "SafeLoader", SafeLoader)
    sys.modules["yaml"] = yaml_stub

if "bleak" not in sys.modules:
    bleak_stub = types.ModuleType("bleak")
    class DummyClient:
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc, tb):
            pass
        async def get_services(self):
            return []
        async def write_gatt_char(self, *a, **k):
            pass
    setattr(bleak_stub, "BleakScanner", types.SimpleNamespace(discover=lambda *a, **k: []))
    setattr(bleak_stub, "BleakClient", DummyClient)
    sys.modules["bleak"] = bleak_stub

if "matplotlib" not in sys.modules:
    class _Dummy(types.ModuleType):
        def __getattr__(self, name):
            return self
        def __call__(self, *a, **k):
            return self
    mpl = _Dummy("matplotlib")
    setattr(mpl, "pyplot", _Dummy("pyplot"))
    setattr(mpl, "animation", _Dummy("animation"))
    setattr(mpl, "widgets", _Dummy("widgets"))
    sys.modules.update({
        "matplotlib": mpl,
        "matplotlib.pyplot": getattr(mpl, "pyplot"),
        "matplotlib.animation": getattr(mpl, "animation"),
        "matplotlib.widgets": getattr(mpl, "widgets"),
    })

if "mplcursors" not in sys.modules:
    sys.modules["mplcursors"] = types.ModuleType("mplcursors")

if "numpy" not in sys.modules:
    np_stub = types.ModuleType("numpy")
    setattr(np_stub, "array", lambda *a, **k: [])
    sys.modules["numpy"] = np_stub

if "nest_asyncio" not in sys.modules:
    nest = types.ModuleType("nest_asyncio")
    setattr(nest, "apply", lambda: None)
    sys.modules["nest_asyncio"] = nest

if "pandas" not in sys.modules:
    pd = types.ModuleType("pandas")
    sys.modules["pandas"] = pd

# Provide a module for the bluehakk CLI so tests importing `bluehakk` succeed
if "bluehakk" not in sys.modules:
    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location(
        "bluehakk", Path(__file__).resolve().parents[1] / "bluehakk.py"
    )
    bluehakk_cli = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(bluehakk_cli)  # type: ignore[arg-type]
    except Exception:
        bluehakk_cli = types.ModuleType("bluehakk")
    sys.modules["bluehakk"] = bluehakk_cli

