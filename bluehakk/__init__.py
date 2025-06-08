"""bluehakk package exposing CLI from bluehakk.py."""

from importlib.util import spec_from_file_location, module_from_spec
from pathlib import Path

# Load the CLI script as a submodule so tests can access its symbols
_cli_path = Path(__file__).with_name("bluehakk.py")
spec = spec_from_file_location("bluehakk.cli", _cli_path)
cli = module_from_spec(spec)
try:
    spec.loader.exec_module(cli)  # type: ignore[arg-type]
except Exception:
    # When optional deps like bleak are missing, skip loading CLI details.
    cli = None

# Re-export public attributes from the CLI script
if cli is not None:
    for name in dir(cli):
        if not name.startswith("_"):
            globals()[name] = getattr(cli, name)

if "bt_util" not in globals():
    import types
    bt_util = types.SimpleNamespace()

__path__ = [str(Path(__file__).parent)]
