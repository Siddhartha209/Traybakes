"""
Traybakes · AI Marketing Assistant
OutputPreview widget — displays generated marketing image output. Shows a
dashed empty state until an image is set. Clicking the image opens a
zoomed-in modal view (closeable via the 'X' or Escape).
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel

from app.styles import BORDER, CREAM_CARD, BROWN_LIGHT
from app.widgets.image_zoom_dialog import ImageZoomDialog


class OutputPreview(QFrame):
    """Displays generated marketing image output. Shows a dashed empty
    state until an image is set. Clicking the image opens a zoomed-in
    modal view (closeable via the 'X' or Escape)."""

    def __init__(self, height: int = 320):
        super().__init__()
        self._height = height
        self._pixmap: QPixmap | None = None
        self.setFixedHeight(height)
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self._apply_empty_style()

        self._layout = QVBoxLayout(self)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._layout.setSpacing(6)

        self.icon_label = QLabel("🖼")
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setStyleSheet("font-size: 28px; border: none; background: transparent;")

        self.empty_label = QLabel("Your generated content will appear here")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setWordWrap(True)
        self.empty_label.setStyleSheet(
            f"color: {BROWN_LIGHT}; font-size: 13px; border: none; background: transparent;"
        )

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("border: none; background: transparent;")
        self.image_label.hide()

        self._layout.addWidget(self.icon_label)
        self._layout.addWidget(self.empty_label)
        self._layout.addWidget(self.image_label)

    def _apply_empty_style(self):
        self.setStyleSheet(f"""
            QFrame {{
                border: 1.5px dashed {BORDER};
                border-radius: 10px;
                background: transparent;
            }}
        """)

    def _apply_filled_style(self):
        self.setStyleSheet(f"""
            QFrame {{
                border: 1.5px solid {BORDER};
                border-radius: 10px;
                background-color: {CREAM_CARD};
            }}
        """)

    def set_image(self, source):
        """Set the preview image. `source` may be a file path (str) or a QPixmap."""
        pixmap = source if isinstance(source, QPixmap) else QPixmap(source)
        if pixmap.isNull():
            return
        self._pixmap = pixmap
        self._render_scaled()
        self.icon_label.hide()
        self.empty_label.hide()
        self.image_label.show()
        self._apply_filled_style()
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Click to view full size")

    def clear(self):
        self._pixmap = None
        self.image_label.clear()
        self.image_label.hide()
        self.icon_label.setText("🖼")
        self.icon_label.show()
        self.empty_label.setText("Your generated content will appear here")
        self.empty_label.show()
        self._apply_empty_style()
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.setToolTip("")

    def set_generating(self):
        """Interim state shown while the orchestrator is running."""
        self._pixmap = None
        self.image_label.hide()
        self.icon_label.setText("⏳")
        self.icon_label.show()
        self.empty_label.setText("Generating…")
        self.empty_label.show()
        self._apply_empty_style()
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.setToolTip("")

    def set_prompt_preview(self, prompt_text: str):
        """img_gen currently only returns a text prompt, not an image asset.
        Show that prompt here as interim feedback until real image bytes
        are wired in — at that point, call set_image(path) instead."""
        self._pixmap = None
        self.image_label.hide()
        self.icon_label.setText("🖋")
        self.icon_label.show()
        trimmed = prompt_text.strip()
        if len(trimmed) > 400:
            trimmed = trimmed[:400].rstrip() + "…"
        self.empty_label.setText(f"No image yet — generated prompt:\n\n{trimmed}")
        self.empty_label.show()
        self._apply_empty_style()
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.setToolTip(prompt_text.strip())

    def has_image(self) -> bool:
        return self._pixmap is not None

    def _render_scaled(self):
        if self._pixmap is None:
            return
        scaled = self._pixmap.scaled(
            max(self.width() - 24, 10), self._height - 24,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.image_label.setPixmap(scaled)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._pixmap is not None:
            self._render_scaled()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._pixmap is not None:
            dialog = ImageZoomDialog(self._pixmap, self.window())
            dialog.exec()
        super().mousePressEvent(event)
