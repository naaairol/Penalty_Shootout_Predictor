import multiprocessing as mp
import sys
from PySide6.QtWidgets import QApplication
from interfaz import PenaltyVisionApp

if __name__ == "__main__":
    mp.freeze_support()
    app = QApplication(sys.argv)
    window = PenaltyVisionApp()
    window.show()
    sys.exit(app.exec())
