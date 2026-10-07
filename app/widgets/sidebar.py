"""
Traybakes · AI Marketing Assistant
Sidebar — left navigation panel. Add/remove/reorder pages by editing the
PAGES list below (each entry is (page name, icon) and must match a key
used when wiring pages into MainWindow.pages).
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QFrame, QLabel, QPushButton

from app.styles import ORANGE, BROWN_MID, TEXT_LIGHT, BROWN_LIGHT, TEXT_DARK


class Sidebar(QWidget):
    PAGES = [
        ("Create Content", "✦"),
        ("Dashboard",      "🏠"),
        ("Editor", "🪄"),
    ]

    DEFAULT_PAGE = "Create Content"

    def __init__(self, on_navigate):
        super().__init__()
        self.setObjectName("sidebar")
        self._buttons = []
        self._on_navigate = on_navigate
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Brand header
        header = QWidget()
        header.setObjectName("sidebar")
        h_layout = QVBoxLayout(header)
        h_layout.setContentsMargins(16, 20, 16, 12)
        h_layout.setSpacing(2)

        title = QLabel("Traybakes")
        title.setStyleSheet(f"background-color: transparent; color: {TEXT_LIGHT}; font-size: 17px; font-weight: 700;")

        subtitle = QLabel("AI Marketing Assistant")
        subtitle.setStyleSheet(f"background-color: transparent; color: {BROWN_LIGHT}; font-size: 11px;")

        h_layout.addWidget(title)
        h_layout.addWidget(subtitle)
        layout.addWidget(header)

        # Divider
        d = QFrame()
        d.setObjectName("sidebarDivider")
        d.setFixedHeight(1)
        layout.addWidget(d)
        layout.addSpacing(6)

        # Nav buttons
        for name, icon in self.PAGES:
            btn = QPushButton(f"  {icon}  {name}")
            btn.setObjectName("sidebar")
            btn.setFixedHeight(40)
            btn.setCheckable(False)
            btn.setProperty("active", False)
            btn.clicked.connect(lambda checked, n=name: self._navigate(n))
            layout.addWidget(btn)
            self._buttons.append((name, btn))

        layout.addSpacing(10)

        d2 = QFrame()
        d2.setObjectName("sidebarDivider")
        d2.setFixedHeight(1)
        layout.addWidget(d2)
        layout.addSpacing(10)
        layout.addStretch()

        self._set_active(self.DEFAULT_PAGE)

    def _navigate(self, name: str):
        self._set_active(name)
        self._on_navigate(name)

    def _set_active(self, name: str):
        for btn_name, btn in self._buttons:
            is_active = btn_name == name
            btn.setProperty("active", is_active)
            if is_active:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {ORANGE};
                        color: white;  /* High contrast against orange */
                        border: none;
                        text-align: left;
                        padding: 10px 16px;
                        font-size: 13px;
                        font-weight: 600;
                        border-radius: 6px;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: transparent;
                        color: {TEXT_DARK};  /* Use dark text color here! */
                        border: none;
                        text-align: left;
                        padding: 10px 16px;
                        font-size: 13px;
                        border-radius: 6px;
                    }}
                    QPushButton:hover {{
                        background-color: {BROWN_MID};
                    }}
                """)
