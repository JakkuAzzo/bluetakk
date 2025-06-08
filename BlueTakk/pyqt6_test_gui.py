import sys
try:
    from PyQt6.QtWidgets import QApplication, QLabel
except Exception:  # pragma: no cover - PyQt6 missing
    print("PyQt6 not installed")
    sys.exit(0)

app = QApplication(sys.argv)
label = QLabel('PyQt6 test: If you see this window, your GUI is working!')
label.resize(400, 100)
label.show()
sys.exit(app.exec())
