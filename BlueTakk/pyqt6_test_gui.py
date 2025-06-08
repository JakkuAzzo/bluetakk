import sys
from PyQt6.QtWidgets import QApplication, QLabel

app = QApplication(sys.argv)
label = QLabel('PyQt6 test: If you see this window, your GUI is working!')
label.resize(400, 100)
label.show()
sys.exit(app.exec())
