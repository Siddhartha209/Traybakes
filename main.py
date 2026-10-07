"""
Traybakes · AI Marketing Assistant
Entry point. Run with: python main.py
"""

import sys

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPalette, QColor

from app.styles import APP_STYLE, CREAM, TEXT_DARK, CREAM_INPUT, ORANGE
from app.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(APP_STYLE)
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(CREAM))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(TEXT_DARK))
    palette.setColor(QPalette.ColorRole.Base, QColor(CREAM_INPUT))
    palette.setColor(QPalette.ColorRole.Text, QColor(TEXT_DARK))
    palette.setColor(QPalette.ColorRole.Button, QColor(ORANGE))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("white"))
    app.setPalette(palette)

    win = MainWindow()
    win.showMaximized()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
