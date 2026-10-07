"""
Traybakes · AI Marketing Assistant
ImageZoomDialog — frameless overlay showing a large version of an image,
with an 'X' button in the top-right corner to close it (Escape also closes).
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent, QPixmap
from PySide6.QtWidgets import QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton

from app.styles import TEXT_LIGHT, ORANGE


class ImageZoomDialog(QDialog):
    """Frameless overlay showing a large version of an image with an
    'X' button in the top-right corner to close it. Escape also closes."""

    def __init__(self, pixmap: QPixmap, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setModal(True)
        self.setStyleSheet("background-color: rgba(20, 12, 6, 235);")

        screen = QApplication.primaryScreen().availableGeometry()
        max_w = int(screen.width() * 0.85)
        max_h = int(screen.height() * 0.85)
        self.resize(max_w, max_h)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 20, 20, 20)
        outer.setSpacing(10)

        close_row = QHBoxLayout()
        close_row.addStretch()
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(36, 36)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(255, 255, 255, 20);
                color: {TEXT_LIGHT};
                border: 1px solid rgba(255, 255, 255, 60);
                border-radius: 18px;
                font-size: 15px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background-color: {ORANGE};
                border-color: {ORANGE};
                color: white;
            }}
        """)
        close_btn.clicked.connect(self.close)
        close_row.addWidget(close_btn)
        outer.addLayout(close_row)

        img_label = QLabel()
        img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        img_label.setStyleSheet("border: none; background: transparent;")
        scaled = pixmap.scaled(
            max_w - 40, max_h - 90,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        img_label.setPixmap(scaled)
        outer.addWidget(img_label, 1)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)
