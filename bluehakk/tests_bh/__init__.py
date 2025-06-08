"""Test helpers for bluehakk."""

import sys
import types

sys.modules.setdefault("bluehakk_tests", sys.modules[__name__])

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
