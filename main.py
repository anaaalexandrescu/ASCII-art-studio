import sys
from PyQt6.QtWidgets import QApplication
from src.gui import MainWindow
from src.gui_widgets import STYLE_SHEET

def main():
    """
    the application's entry point

    creates the QApplication object, initializes and shows the main
    MainWindow window, then starts the PyQt event loop
    """
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLE_SHEET)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()