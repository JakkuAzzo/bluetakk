# Bluehakk

Bluehakk is a versatile Bluetooth toolkit designed for scanning, vulnerability testing, session monitoring, and MITM proxying on Bluetooth Low Energy (BLE) devices. The project integrates several Python modules that utilize asynchronous programming, the Bleak library, and various system-specific utilities to provide both interactive CLI and live visualization features.

---

## Table of Contents

- [Features](#features)
- [Project Structure](#project-structure)
- [Installation &amp; Setup](#installation--setup)
- [Usage](#usage)
  - [Bluehakk CLI](#bluehakk-cli)
  - [DeepBle Discovery Tool](#deepble-discovery-tool)
  - [Vulnerability Testing](#vulnerability-testing)
  - [MITM Proxy](#mitm-proxy)
  - [BLE Shell Session](#ble-shell-session)
  - [Reference Update](#reference-update)
- [Dependencies &amp; Platform-Specific Setup](#dependencies--platform-specific-setup)
- [Contributing](#contributing)
- [License](#license)
- [Contact](#contact)

---

## Features

- **BLE Device Scanning:** Quickly discover nearby Bluetooth devices.
- **Deep Device Analysis:** Detailed scanning with manufacturer data decoding, service UUID mappings, and class-of-device information.
- **Vulnerability Testing:** Run tests and exploits on target devices to check for potential vulnerabilities.
- **Session Monitoring:** Record session data and generate statistical visualizations using matplotlib.
- **MITM Proxy:** Cross-platform (macOS and Windows) proxy that intercepts BLE traffic.
- **BLE Shell Session:** Establish command shell sessions on connected devices through BLE characteristics.
- **Reference Data Updates:** Automatically update JSON reference files from Bluetooth SIG YAML repositories.

---

## Project Structure

```
bluehack/
├── bluehakk.py                  # Main CLI entry point.
├── bleshellexploit.py           # Contains scanning, exploitation & vulnerability test functions.
├── blueshell.py                 # Implements a shell session on connected BLE devices.
├── bleak_stats.py               # Provides live and static visualization of BLE session statistics.
├── deepBle_discovery_tool.py    # Advanced BLE scanning and discovery tool.
├── mac_mitm.py                 # MITM proxy for macOS.
├── win_mitm.py                 # MITM proxy for Windows.
├── sessions/                    # Directory where session details are stored.
└── utility_scripts/             # Utility modules:
    ├── check_bt_utilities.py   # Dependency checks and platform-specific monitoring.
    └── update_bluetooth_sig_jsons.py  # Updates JSON reference files from Bluetooth SIG repository.
```

---

## Installation & Setup

1. **Clone the Repository and run bluehakk.py as it will handle everything:**

   ```bash
   git clone https://github.com/jakkuazzo/bluehack.git
   cd bluehack
   python3 bluehakk.py
   ```
2. **To manually Install Dependencies:**

   Bluehakk relies on Python 3.12+ and several libraries. Based on your platform, run:

   - **macOS:**

     ```bash
     pip install -r mac_requirements.txt
     ```
   - **Windows:**

     ```bash
     pip install -r win_requirements.txt
     ```
   - **Linux (posix):**

     ```bash
     pip install -r lin_requirements.txt
     ```
3. **Reference Data Update (Optional):**

   To manually download and convert Bluetooth SIG YAML files into JSON references, run:

   ```bash
   python utility_scripts/update_bluetooth_sig_jsons.py
   ```

   This script clones the Bluetooth SIG repository, converts necessary YAML files to JSON, logs the generated files, and cleans up the repository folder after conversion.

---

## Usage

### Bluehakk CLI

Run the main CLI application:

```bash
python bluehakk.py
```

The CLI offers the following options:

- **Detailed Scan (DeepBle):** Launches an embedded deep scan to list nearby BLE devices.
- **Vulnerability Testing:** Executes vulnerability tests on a target device using `bleshellexploit`.
- **Session Stats:** Displays a graphical summary of session details via `bleak_stats.py`.
- **Static Visualization:** Generates a visualization from the last captured session.
- **MITM Proxy:** Launches a MITM proxy; the script used varies based on your OS.
- **Exit:** Close the CLI.

### DeepBle Discovery Tool

Run the DeepBle Discovery Tool for advanced scanning and real-time device analysis:

```bash
python deepBle_discovery_tool.py
```

This tool includes options for quick scans, detailed scans, live scans (with cancellation on pressing 'q'), and updating reference data.

### Vulnerability Testing

The vulnerability testing mode (option 2 in the Bluehakk CLI) uses `bleshellexploit.py` to:

- Identify writable BLE characteristics.
- Attempt test commands and exploits (buffer overflow, input limits, etc.).
- Display results in a formatted matplotlib table.

### MITM Proxy

Depending on your OS, the project provides:

- **macOS:** Run the MITM proxy via:

  ```bash
  python mac_mitm.py <target_device_address>
  ```
- **Windows:** Run the MITM proxy via:

  ```bash
  python win_mitm.py <target_device_address>
  ```

The MITM proxies intercept BLE traffic, enabling read/write forwarding via custom delegates and GATT servers.

### BLE Shell Session

Establish a shell session with a connected BLE device using `blueshell.py`:

```bash
python blueshell.py --device_address <device_address> [--device_name <name>]
```

This opens an interactive shell that transfers commands to the BLE device using dedicated shell service UUIDs.

### Reference Update

To update the Bluetooth reference JSON files, run:

```bash
python utility_scripts/update_bluetooth_sig_jsons.py
```

This ensures that the latest manufacturer identifiers, service, and characteristic references are used during scans and decoding.

---

## Dependencies & Platform-Specific Setup

- **macOS:**

  - Requires Wireshark and PacketLogger.
  - The script `check_bt_utilities.py` automatically checks for Wireshark, verifies Homebrew installation, and attempts to install necessary casks.
- **Windows:**

  - Requires Wireshark and the Bluetooth Test Platform Pack (btvs.exe, btp.exe).
  - Dependency checks and configuration are performed in `check_bt_utilities.py`.

Ensure you install all required system utilities as prompted by the CLI if any dependencies are missing.

---

## Contributing

Contributions are welcome! To contribute:

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

## License

[Include your project License here.]

---

## Contact

For questions, bug reports, or feature requests, open an issue on the GitHub repository or contact [your-email@example.com].

---

Bluehakk leverages Python’s asyncio capabilities, the Bleak library for BLE communication, and matplotlib for visualization to serve as a powerful BLE diagnostic and exploitation tool across multiple platforms.
