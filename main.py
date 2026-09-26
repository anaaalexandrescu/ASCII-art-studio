import sys
from PyQt6.QtWidgets import QApplication
from src.gui import MainWindow
from src.gui_widgets import STYLE_SHEET

def main():
    """
    punctul de intrare al aplicatiei
 
    creeaza obiectul QApplication, initializeaza si afiseaza fereastra
    principala MainWindow, apoi porneste event loop ul PyQt
    """
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLE_SHEET)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()