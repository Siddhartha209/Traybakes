"""
Traybakes · AI Marketing Assistant
CaptionCard widget — a single selectable caption option with feedback
controls (thumbs up/thumbs down), used on the Create Content page.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton

from app.styles import BROWN_LIGHT, ORANGE, TEXT_DARK


class CaptionCard(QFrame):
    """A single selectable caption option with feedback controls."""

    clicked = Signal(object)
    rating_changed = Signal(object, int)


    def __init__(
        self,
        index: int,
        text: str = "",
        caption_id: str | None = None
    ):

        super().__init__()

        self.index = index
        self.caption_id = caption_id
        self._selected = False
        self._rating = None

        self.setObjectName("captionCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setProperty("selected", False)

        layout = QVBoxLayout(self)

        layout.setContentsMargins(
            14,
            12,
            14,
            12
        )

        layout.setSpacing(8)

        # -----------------------------
        # HEADER
        # -----------------------------

        header = QHBoxLayout()
        header.setSpacing(8)

        self.radio_dot = QLabel("○")

        self.radio_dot.setStyleSheet(
            f"color: {BROWN_LIGHT}; font-size: 14px; border: none;"
        )

        label = QLabel(
            f"Option {index + 1}"
        )

        label.setStyleSheet(
            f"color: {BROWN_LIGHT}; font-size: 11px; font-weight: 600; border: none;"
        )

        header.addWidget(
            self.radio_dot
        )

        header.addWidget(
            label
        )

        header.addStretch()

        layout.addLayout(header)

        # -----------------------------
        # CAPTION TEXT
        # -----------------------------

        self.text_label = QLabel(text)

        self.text_label.setWordWrap(True)

        self.text_label.setStyleSheet(
            f"color: {TEXT_DARK}; font-size: 13px; border: none;"
        )

        layout.addWidget(
            self.text_label
        )

        # -----------------------------
        # FEEDBACK BUTTONS
        # -----------------------------

        feedback_row = QHBoxLayout()

        feedback_row.addStretch()

        self.like_button = QPushButton(
            "👍 Use this"
        )

        self.dislike_button = QPushButton(
            "👎 Not this one"
        )

        for button in (
            self.like_button,
            self.dislike_button
        ):

            button.setFixedSize(
                100,
                28
            )

            button.setCursor(
                Qt.CursorShape.PointingHandCursor
            )

        self.like_button.clicked.connect(
            lambda: self.set_rating(1)
        )

        self.dislike_button.clicked.connect(
            lambda: self.set_rating(-1)
        )

        feedback_row.addWidget(
            self.like_button
        )

        feedback_row.addWidget(
            self.dislike_button
        )

        layout.addLayout(
            feedback_row
        )

    def set_text(
        self,
        text: str
    ):

        self.text_label.setText(text)

    def set_rating(
        self,
        rating: int
    ):

        self._rating = rating
        if rating is None:
            self._rating = None
            self.like_button.setText("👍 Use this")
            self.dislike_button.setText("👎 Not this one")
            return

        if rating == 1:

            self.like_button.setText(
                "👍 Using this ✓"
            )

            self.dislike_button.setText(
                "👎 Not this one"
            )

        else:

            self.like_button.setText(
                "👍 Use this"
            )

            self.dislike_button.setText(
                "👎 Not this one ✓"
            )

        self.rating_changed.emit(
            self,
            rating
        )

    def set_selected(
        self,
        selected: bool
    ):

        self._selected = selected

        self.setProperty(
            "selected",
            selected
        )

        self.radio_dot.setText(
            "●" if selected else "○"
        )

        self.radio_dot.setStyleSheet(
            f"color: {ORANGE if selected else BROWN_LIGHT}; "
            "font-size: 14px; "
            "font-weight: 700; "
            "border: none;"
        )

        self.style().unpolish(self)
        self.style().polish(self)

    def is_selected(self):

        return self._selected

    def mousePressEvent(
        self,
        event
    ):

        if event.button() == Qt.MouseButton.LeftButton:

            self.clicked.emit(
                self
            )

        super().mousePressEvent(event)
