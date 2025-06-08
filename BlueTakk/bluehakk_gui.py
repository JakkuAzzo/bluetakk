import sys
import os
import asyncio
import subprocess
from types import SimpleNamespace
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PyQt6.QtWidgets import (
        QApplication,
        QWidget,
        QVBoxLayout,
        QPushButton,
        QInputDialog,
        QMessageBox,
        QTabWidget,
        QTextEdit,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QComboBox,
        QTableWidget,
        QTableWidgetItem,
        QSplitter,
        QProgressBar,
        QColorDialog,
        QStyleFactory,
        QSplashScreen,
        QDialog,
        QDialogButtonBox,
    )
    from PyQt6.QtGui import QColor, QPalette, QPixmap
    from PyQt6.QtCore import Qt, QTimer

try:  # Import PyQt6 if available, otherwise provide minimal stubs
    from PyQt6.QtWidgets import (
        QApplication,
        QWidget,
        QVBoxLayout,
        QPushButton,
        QInputDialog,
        QMessageBox,
        QTabWidget,
        QTextEdit,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QComboBox,
        QTableWidget,
        QTableWidgetItem,
        QSplitter,
        QProgressBar,
        QColorDialog,
        QStyleFactory,
        QSplashScreen,
        QDialog,
        QDialogButtonBox,
    )
    from PyQt6.QtGui import QColor, QPalette, QPixmap
    from PyQt6.QtCore import Qt, QTimer
except Exception:  # pragma: no cover - fallback for headless test envs
    class _Signal:
        def connect(self, func):
            self._func = func

    class QApplication(object):  # type: ignore
        def __init__(self, *a, **k):
            pass
        @staticmethod
        def instance():
            return None
        def exec(self):
            return 0
        def setStyle(self, *a, **k):
            pass
        def setPalette(self, *a, **k):
            pass

    class QWidget(object):  # type: ignore
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

    class QTabWidget(object):  # type: ignore
        def __init__(self, *a, **k): pass
        def addTab(self, *a, **k): pass
    class QTextEdit(object):  # type: ignore
        def __init__(self, *a, **k): pass
        def setReadOnly(self, *a): pass
        def setPlainText(self, *a): pass
        def clear(self): pass
    class QLineEdit(object):  # type: ignore
        def __init__(self, *a, **k): pass
        def setPlaceholderText(self, *a): pass
        def text(self): return ""
        def clear(self): pass
    class QLabel(object):  # type: ignore
        def __init__(self, *a, **k): pass
    class QComboBox(object):  # type: ignore
        def __init__(self, *a, **k): pass
        def addItems(self, *a): pass
        def currentText(self): return ""
    class QProgressBar(object):
        def __init__(self, *a, **k): pass
        def setValue(self, *a): pass
        def setMaximum(self, *a): pass
        def setMinimum(self, *a): pass
        def show(self): pass
        def hide(self): pass
    class QColorDialog(object):
        @staticmethod
        def getColor(*a, **k): return None
    class QStyleFactory(object):
        @staticmethod
        def create(*a, **k): return None
    class QSplashScreen(object):
        def __init__(self, *a, **k): pass
        def showMessage(self, *a, **k): pass
        def show(self): pass
        def finish(self, *a): pass
    class QDialog(object):
        def __init__(self, *a, **k): pass
        def exec(self): return 0
    class QDialogButtonBox(object):
        def __init__(self, *a, **k): pass
    class QColor(object):
        def __init__(self, *a, **k): pass
    class QPalette(object):
        class ColorRole:
            Window = 0
            WindowText = 1
            Base = 2
            AlternateBase = 3
            ToolTipBase = 4
            ToolTipText = 5
            Text = 6
            Button = 7
            ButtonText = 8
            BrightText = 9
            Highlight = 10
            HighlightedText = 11
        def __init__(self, *a, **k): pass
        def setColor(self, *a, **k): pass
    class QPixmap(object):
        def __init__(self, *a, **k): pass
    class Qt:
        class AlignmentFlag:
            AlignCenter = 0
            AlignBottom = 0
        class GlobalColor:
            white = 0
    class QTimer(object):
        @staticmethod
        def singleShot(*a, **k): pass

import deepBle_discovery_tool as deep
import bleshellexploit
import replay_attack
from utility_scripts import check_bt_utilities as bt_util
from peripheral_simulator import DEVICE_PROFILES, start_simulator


class SessionWindow(QWidget):
    """Simple window representing a running shell session."""

    def __init__(self, address: str):
        super().__init__()
        self.address = address
        self.setWindowTitle(f"Session {address}")
        layout = QVBoxLayout()
        self.setLayout(layout)
        # Launch blueshell detached
        self.proc = subprocess.Popen(
            [sys.executable, "blueshell.py", "--device_address", address],
            start_new_session=True,
        )

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Bluehakk GUI")
        self.sessions = []
        self.tabs = QTabWidget()
        self.init_tabs()
        layout = QVBoxLayout()
        layout.addWidget(self.tabs)
        self.setLayout(layout)

    def init_tabs(self):
        self.tabs.addTab(self.scan_tab(), "Detailed Scan")
        self.tabs.addTab(self.vuln_tab(), "Vulnerability Test")
        self.tabs.addTab(self.stats_tab(), "Session Stats")
        self.tabs.addTab(self.vis_tab(), "Static Visualization")
        self.tabs.addTab(self.mitm_tab(), "MITM Proxy")
        self.tabs.addTab(self.sim_tab(), "Peripheral Simulator")
        self.tabs.addTab(self.shell_tab(), "Shell Session")
        self.tabs.addTab(self.replay_tab(), "Replay Attack Test")

    def scan_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        btn = QPushButton("Run Detailed Scan")
        self.scan_output = QTextEdit()
        self.scan_output.setReadOnly(True)
        btn.clicked.connect(self.run_scan)
        layout.addWidget(btn)
        layout.addWidget(self.scan_output)
        tab.setLayout(layout)
        return tab

    def run_scan(self):
        self.scan_output.clear()
        async def do_scan():
            import io, contextlib
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                await deep.run_detailed_scan()
            self.scan_output.setPlainText(buf.getvalue())
        asyncio.run(do_scan())

    def vuln_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        addr_input = QLineEdit()
        addr_input.setPlaceholderText("Device address")
        btn = QPushButton("Run Vulnerability Test")
        self.vuln_output = QTextEdit()
        self.vuln_output.setReadOnly(True)
        def run_vuln():
            address = addr_input.text().strip()
            if address:
                results = bleshellexploit.run_exploit(address)
                self.vuln_output.setPlainText(str(results))
        btn.clicked.connect(run_vuln)
        layout.addWidget(QLabel("Target Address:"))
        layout.addWidget(addr_input)
        layout.addWidget(btn)
        layout.addWidget(self.vuln_output)
        tab.setLayout(layout)
        return tab

    def stats_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        btn = QPushButton("Show Session Stats")
        self.stats_output = QTextEdit()
        self.stats_output.setReadOnly(True)
        def run_stats():
            subprocess.run([sys.executable, "bleak_stats.py"])
            self.stats_output.setPlainText("Session stats script executed. See generated charts.")
        btn.clicked.connect(run_stats)
        layout.addWidget(btn)
        layout.addWidget(self.stats_output)
        tab.setLayout(layout)
        return tab

    def vis_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        btn = QPushButton("Show Static Visualization")
        self.vis_output = QTextEdit()
        self.vis_output.setReadOnly(True)
        def run_vis():
            bt_util.visualize_results(live=False)
            self.vis_output.setPlainText("Static visualization generated. See chart window.")
        btn.clicked.connect(run_vis)
        layout.addWidget(btn)
        layout.addWidget(self.vis_output)
        tab.setLayout(layout)
        return tab

    def mitm_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        addr_input = QLineEdit()
        addr_input.setPlaceholderText("Device address")
        btn = QPushButton("Start MITM Proxy")
        self.mitm_output = QTextEdit()
        self.mitm_output.setReadOnly(True)
        def run_mitm():
            address = addr_input.text().strip()
            if not address:
                self.mitm_output.setPlainText("No address provided.")
                return
            if sys.platform.startswith('win'):
                subprocess.run([sys.executable, "win_mitm.py", address])
            elif sys.platform.startswith('darwin'):
                subprocess.run([sys.executable, "mac_mitm.py", address])
            else:
                self.mitm_output.setPlainText("MITM not supported on this OS")
        btn.clicked.connect(run_mitm)
        layout.addWidget(QLabel("Target Address:"))
        layout.addWidget(addr_input)
        layout.addWidget(btn)
        layout.addWidget(self.mitm_output)
        tab.setLayout(layout)
        return tab

    def sim_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        combo = QComboBox()
        combo.addItems(list(DEVICE_PROFILES.keys()))
        btn = QPushButton("Start Peripheral Simulator")
        self.sim_output = QTextEdit()
        self.sim_output.setReadOnly(True)
        def run_sim():
            device = combo.currentText()
            try:
                start_simulator(device)
                self.sim_output.setPlainText(f"Started simulator for {device}")
            except Exception as exc:
                self.sim_output.setPlainText(f"Error: {exc}")
        btn.clicked.connect(run_sim)
        layout.addWidget(QLabel("Device Profile:"))
        layout.addWidget(combo)
        layout.addWidget(btn)
        layout.addWidget(self.sim_output)
        tab.setLayout(layout)
        return tab

    def shell_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        addr_input = QLineEdit()
        addr_input.setPlaceholderText("Device address")
        btn = QPushButton("Start Shell Session")
        self.shell_output = QTextEdit()
        self.shell_output.setReadOnly(True)
        def run_shell():
            address = addr_input.text().strip()
            if address:
                win = SessionWindow(address)
                self.sessions.append(win)
                win.show()
                self.shell_output.setPlainText(f"Started shell session for {address}")
        btn.clicked.connect(run_shell)
        layout.addWidget(QLabel("Target Address:"))
        layout.addWidget(addr_input)
        layout.addWidget(btn)
        layout.addWidget(self.shell_output)
        tab.setLayout(layout)
        return tab

    def replay_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        addr_input = QLineEdit()
        addr_input.setPlaceholderText("Device address")
        btn = QPushButton("Run Replay Attack Test")
        self.replay_output = QTextEdit()
        self.replay_output.setReadOnly(True)
        def run_replay():
            address = addr_input.text().strip()
            if address:
                asyncio.run(replay_attack.automatic_replay_test(address))
                self.replay_output.setPlainText(f"Replay attack test run for {address}")
        btn.clicked.connect(run_replay)
        layout.addWidget(QLabel("Target Address:"))
        layout.addWidget(addr_input)
        layout.addWidget(btn)
        layout.addWidget(self.replay_output)
        tab.setLayout(layout)
        return tab

def ensure_venv_and_requirements():
    import sys
    import subprocess
    import os
    venv_dir = os.path.join(os.path.dirname(__file__), ".venv_auto")
    if not os.path.exists(venv_dir):
        print(f"Creating virtual environment at {venv_dir}...")
        subprocess.run([sys.executable, "-m", "venv", venv_dir], check=True)
    pip_path = os.path.join(venv_dir, "bin", "pip") if not sys.platform.startswith("win") else os.path.join(venv_dir, "Scripts", "pip.exe")
    if sys.platform == "darwin":
        req_file = "mac_requirements.txt"
    elif sys.platform.startswith("win"):
        req_file = "win_requirements.txt"
    else:
        req_file = "requirements.txt"
    req_path = os.path.join(os.path.dirname(__file__), req_file)
    if os.path.exists(pip_path) and os.path.exists(req_path):
        print(f"Installing requirements from {req_file} in {venv_dir}...")
        subprocess.run([pip_path, "install", "--force-reinstall", "-r", req_path], check=True)
    else:
        print(f"Could not find pip at {pip_path} or requirements at {req_path}.")

def main():
    app = QApplication(sys.argv)
    YES = getattr(QMessageBox, 'Yes', 0x00004000)
    NO = getattr(QMessageBox, 'No', 0x00010000)
    question = getattr(QMessageBox, 'question', None)
    if question is not None:
        choice = question(
            None,
            "Setup",
            "Do you want to (re)install requirements and update Bluetooth SIG references?",
            YES | NO,
            NO
        )
    else:
        choice = NO
    if choice == YES:
        ensure_venv_and_requirements()
        try:
            subprocess.run([sys.executable, "utility_scripts/update_bluetooth_sig_jsons.py"], check=True)
        except Exception as e:
            if hasattr(QMessageBox, 'warning'):
                QMessageBox.warning(None, "Reference Update", f"Failed to update references: {e}")
            else:
                print(f"Failed to update references: {e}")
    # Show splash and GUI immediately, then load references in the background
    app.setStyle(QStyleFactory.create("Fusion"))
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(30, 30, 40))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(220, 220, 220))
    palette.setColor(QPalette.ColorRole.Base, QColor(40, 40, 50))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(60, 60, 80))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 220))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(30, 30, 40))
    palette.setColor(QPalette.ColorRole.Text, QColor(220, 220, 220))
    palette.setColor(QPalette.ColorRole.Button, QColor(50, 50, 70))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(220, 220, 220))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(100, 100, 200))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    app.setPalette(palette)
    splash = QSplashScreen(QPixmap(400, 200))
    splash.showMessage("Loading Bluehakk GUI...", Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignBottom, Qt.GlobalColor.white)
    splash.show()
    def start_gui():
        window = MainWindow()
        window.show()
        splash.finish(window)
    QTimer.singleShot(200, start_gui)
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
