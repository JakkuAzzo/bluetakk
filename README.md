# bluetakk

bluetakk is a multi-folder Bluetooth Low Energy (BLE) toolkit for device scanning, vulnerability testing, session monitoring, and MITM proxying. The main, modernized and recommended version is in the `BlueTakk/` folder. See below for an overview of the three main project folders:

---

## BlueTakk (Main Program)

**BlueTakk/** is the primary, up-to-date toolkit. It provides:

- **CLI and GUI interfaces** (`bluehakk.py`, `bluehakk_gui.py`) for BLE scanning, vulnerability testing, session stats, and MITM attacks.
- **Deep scanning and device fingerprinting** with `deepBle_discovery_tool.py` and Bluetooth SIG reference data.
- **Vulnerability testing** via `bleshellexploit.py`.
- **Session statistics and visualization** with `bleak_stats.py` (matplotlib-based charts, JSON session logs).
- **MITM proxies** for macOS and Windows (`mac_mitm.py`, `win_mitm.py`).
- **BLE shell sessions** (`blueshell.py`) for interactive command execution on BLE devices.
- **Peripheral simulator** (`peripheral_simulator/`) for in-memory and CoreBluetooth-based BLE device simulation.
- **Utility scripts** for dependency checks, Bluetooth SIG data updates, and platform-specific setup.
- **Test suite** in `tests/` for core features and `setup_test_env.sh` for test environment setup.

### Quick Start

```bash
cd BlueTakk
pip install -r requirements.txt
python3 bluehakk.py
```

See `BlueTakk/README.md` for full details, usage, and development notes.

---

## bluehakk (Modernized, Standalone Copy)

**bluehakk/** is a modernized, mostly standalone copy of the toolkit, suitable for direct use or further development. It mirrors the structure and features of `BlueTakk/` and is kept in sync for testing and packaging purposes. Use this if you want a self-contained, ready-to-run version.

---

## bluehack (Legacy/Reference)

**bluehack/** contains the original, legacy version of the toolkit. It includes early scripts, proof-of-concept code, and historical reference implementations. The folder is preserved for reference and for users who want to see the evolution of the project. New development should use `BlueTakk/` or `bluehakk/` instead.

---

## Folder Overview

- `BlueTakk/` – Main, recommended toolkit (CLI, GUI, simulators, utilities, tests)
- `bluehakk/` – Modernized, standalone copy (mirrors BlueTakk)
- `bluehack/` – Legacy scripts and reference code

For more details, see the `README.md` in each folder.
