import os
import sys

from dotenv import load_dotenv
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from config import APP_TITLE, DEBUG_MODE_ON, FONT_FAMILY, FONT_SIZE_BASE
from ui.main_window import CITICalculatorApp
from utils.logger import setup_logger


def main():
    load_dotenv()
    debug_mode = os.getenv("DEBUG", "False").lower() == "true"
    if debug_mode:
        print(DEBUG_MODE_ON)
    setup_logger(debug_mode)

    app = QApplication(sys.argv)
    app.setFont(QFont(FONT_FAMILY, FONT_SIZE_BASE))
    window = CITICalculatorApp()
    window.setWindowTitle(APP_TITLE)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
