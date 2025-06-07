import sys
import asyncio
import subprocess
from types import SimpleNamespace

try:  # Import PyQt6 if available, otherwise provide minimal stubs
    from PyQt6.QtWidgets import (
        QApplication,
        QWidget,
        QVBoxLayout,
        QPushButton,
        QInputDialog,
        QMessageBox,
    )
except Exception:  # pragma: no cover - fallback for headless test envs
    class _Signal:
        def connect(self, func):
            self._func = func

    class QApplication:  # type: ignore
        def __init__(self, *a, **k):
            pass

        @staticmethod
        def instance():
            return None

        def exec(self):
            return 0

    class QWidget:  # type: ignore
        def __init__(self, *a, **k):
            pass

        def setWindowTitle(self, *a):
            pass

        def setLayout(self, *a):
            pass

        def show(self):
            pass

    class QVBoxLayout:  # type: ignore
        def __init__(self):
            pass

        def addWidget(self, *a):
            pass

    class QPushButton:  # type: ignore
        def __init__(self, *a):
            self.clicked = SimpleNamespace(connect=lambda f: None)

    class QInputDialog:  # type: ignore
        @staticmethod
        def getText(*a, **k):
            return "", False

        @staticmethod
        def getItem(*a, **k):
            return "", False

    class QMessageBox:  # type: ignore
        @staticmethod
        def information(*a, **k):
            pass

        @staticmethod
        def warning(*a, **k):
            pass

import deepBle_discovery_tool as deep
import bleshellexploit
import replay_attack
from utility_scripts import check_bt_utilities as bt_util
from peripheral_simulator import DEVICE_PROFILES, start_simulator

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Bluehakk GUI")
        layout = QVBoxLayout()

        btn_scan = QPushButton("Detailed Scan")
        btn_scan.clicked.connect(self.detailed_scan)
        layout.addWidget(btn_scan)

        btn_vuln = QPushButton("Vulnerability Test")
        btn_vuln.clicked.connect(self.vuln_test)
        layout.addWidget(btn_vuln)

        btn_stats = QPushButton("Session Stats")
        btn_stats.clicked.connect(self.session_stats)
        layout.addWidget(btn_stats)

        btn_vis = QPushButton("Static Visualization")
        btn_vis.clicked.connect(self.static_vis)
        layout.addWidget(btn_vis)

        btn_mitm = QPushButton("MITM Proxy")
        btn_mitm.clicked.connect(self.mitm_proxy)
        layout.addWidget(btn_mitm)

        btn_sim = QPushButton("Start Peripheral Simulator")
        btn_sim.clicked.connect(self.start_simulator)
        layout.addWidget(btn_sim)

        btn_replay = QPushButton("Replay Attack Test")
        btn_replay.clicked.connect(self.replay_test)
        layout.addWidget(btn_replay)

        self.setLayout(layout)

    def detailed_scan(self):
        asyncio.run(deep.run_detailed_scan())

    def vuln_test(self):
        address, ok = QInputDialog.getText(self, "Target", "Device address:")
        if ok and address:
            results = bleshellexploit.run_exploit(address)
            QMessageBox.information(self, "Results", str(results))

    def session_stats(self):
        subprocess.run([sys.executable, "bleak_stats.py"])

    def static_vis(self):
        bt_util.visualize_results(live=False)

    def mitm_proxy(self):
        address, ok = QInputDialog.getText(self, "Target", "Device address:")
        if not ok or not address:
            return
        if sys.platform.startswith('win'):
            subprocess.run([sys.executable, "win_mitm.py", address])
        elif sys.platform.startswith('darwin'):
            subprocess.run([sys.executable, "mac_mitm.py", address])
        else:
            QMessageBox.information(self, "Info", "MITM not supported on this OS")

    def start_simulator(self):
        items = list(DEVICE_PROFILES.keys())
        device, ok = QInputDialog.getItem(
            self,
            "Device Type",
            "Choose profile:",
            items,
            0,
            False,
        )
        if ok and device:
            try:
                start_simulator(device)
            except Exception as exc:  # pragma: no cover - runtime only
                QMessageBox.warning(self, "Error", str(exc))

    def replay_test(self):
        address, ok = QInputDialog.getText(self, "Target", "Device address:")
        if ok and address:
            asyncio.run(replay_attack.automatic_replay_test(address))


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
