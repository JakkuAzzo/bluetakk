# Bluehakk

Bluehakk is a collection of Bluetooth Low Energy (BLE) reconnaissance tools. It provides scanning utilities, vulnerability checks and MITM proof-of-concept scripts built around the [bleak](https://github.com/hbldh/bleak) library.

Recent updates add improved device fingerprinting heuristics along with optional curses and PyQt6 interfaces for navigating the toolkit.

## Installation

Bluehakk relies on Python 3.8+ and `bleak`.

```bash
pip install -r requirements.txt
```

For Windows and macOS, additional packages are listed in `win_requirements.txt` and `mac_requirements.txt`.

To update the Bluetooth‑SIG reference files used by the scanners:

```bash
python3 utility_scripts/update_bluetooth_sig_jsons.py
```

## Usage

The main entry point is `bluehakk.py` which provides a CLI for scanning and exploitation.

```bash
python3 bluehakk.py
```

From the menu you can launch quick or detailed scans, perform vulnerability tests, generate statistics and run MITM proxies (Windows or macOS).

Each script can also be run individually. A brief overview:

- `deepBle_discovery_tool.py` – scanning utilities that reference Bluetooth‑SIG data.
- `bleak_stats.py` – visualization of scanning sessions.
- `bleshellexploit.py` – proof-of-concept shell exploitation routines.
- `mac_mitm.py` and `win_mitm.py` – MITM proxies for their respective platforms.
- `utility_scripts/update_bluetooth_sig_jsons.py` – fetch and convert Bluetooth‑SIG references.
- `replay_attack.py` – automatic replay attack testing.
- `curses_ui.py` – simple curses-based menu interface.
- `bluehakk_gui.py` – PyQt6 GUI front end.

---

## Extended Usage & Features (from legacy bluehack)

- **Detailed Scan (DeepBle):** Launches an embedded deep scan to list nearby BLE devices.
- **Vulnerability Testing:** Executes vulnerability tests on a target device using `bleshellexploit`.
- **Session Stats:** Displays a graphical summary of session details via `bleak_stats.py`.
- **Static Visualization:** Generates a visualization from the last captured session.
- **MITM Proxy:** Launches a MITM proxy; the script used varies based on your OS.
- **BLE Shell Session:** Establish a shell session with a connected BLE device using `blueshell.py`.
- **Reference Data Update:** Update Bluetooth reference JSON files with `utility_scripts/update_bluetooth_sig_jsons.py`.

### Platform-Specific Setup
- **macOS:** Requires Wireshark and PacketLogger. The script `check_bt_utilities.py` checks for Wireshark, verifies Homebrew, and installs necessary casks.
- **Windows:** Requires Wireshark and the Bluetooth Test Platform Pack. Dependency checks and configuration are performed in `check_bt_utilities.py`.

### Contributing
1. Fork the repository.
2. Create a new feature branch:
   ```bash
   git checkout -b feature/my-new-feature
   ```
3. Commit your changes:
   ```bash
   git commit -am 'Add some feature'
   ```
4. Push to the branch:
   ```bash
   git push origin feature/my-new-feature
   ```
5. Submit a pull request.

---

## Contact
For questions, bug reports, or feature requests, open an issue on the GitHub repository or contact [your-email@example.com].

---

BlueTakk leverages Python’s asyncio capabilities, the Bleak library for BLE communication, and matplotlib for visualization to serve as a powerful BLE diagnostic and exploitation tool across multiple platforms.

## Development

The project contains experimental scripts and does not yet include full automation. Contributions are welcome via pull requests.


## Testing

A convenience script `setup_test_env.sh` helps create a virtual environment with just the packages needed to run the test suite.

```bash
./setup_test_env.sh
source .venv/bin/activate
pytest
```

