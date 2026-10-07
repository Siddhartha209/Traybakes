"""
Traybakes · AI Marketing Assistant
Colour palette, global QSS stylesheet, and small style-helper widgets
(dividers, section labels, buttons, placeholders, metric cards).

Change colours or the stylesheet here and it propagates everywhere —
this is the single place to touch for a UI-wide look-and-feel change.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout, QSizePolicy


# ── Colour palette ─────────────────────────────────
BROWN_DARK   = "#2C1A0E"
BROWN_MID    = "#5C3D2E"
BROWN_LIGHT  = "#9A6548"
CREAM        = "#FFFBF7"
CREAM_CARD   = "#FFF8F0"
CREAM_INPUT  = "#FFFDF9"
BORDER       = "#E8D5C0"
ORANGE       = "#C4622D"
ORANGE_DARK  = "#A34E22"
TEXT_DARK    = "#2C1A0E"
TEXT_MID     = "#4A2E1A"
TEXT_LIGHT   = "#F5E6D3"
GREEN_BG     = "#EAF6EE"
GREEN_TEXT   = "#276B3A"
GREEN_BORDER = "#B6DFC2"


# ── Shared stylesheet ──────────────────────────────
APP_STYLE = f"""
QMainWindow, QWidget {{
    background-color: {CREAM};
    color: {TEXT_DARK};
    font-family: 'Segoe UI', 'DM Sans', sans-serif;
    font-size: 13px;
}}
 
/* ── Sidebar ── */
#sidebar {{
    background-color: {BROWN_DARK};
    min-width: 210px;
    max-width: 210px;
}}
 
#sidebar QLabel {{
    color: {TEXT_LIGHT};
}}
 
#sidebar QPushButton {{
    background-color: transparent;
    color: {TEXT_LIGHT};
    border: none;
    text-align: left;
    padding: 10px 16px;
    font-size: 13px;
    border-radius: 6px;
}}
 
#sidebar QPushButton:hover {{
    background-color: {BROWN_MID};
}}
 
#sidebar QPushButton[active="true"] {{
    background-color: {ORANGE};
    color: white;
    font-weight: 600;
}}
 
#sidebarDivider {{
    background-color: {BROWN_MID};
    max-height: 1px;
    min-height: 1px;
}}
 
/* ── Primary button ── */
QPushButton#primary {{
    background-color: {ORANGE};
    color: white;
    border: none;
    border-radius: 8px;
    padding: 8px 18px;
    font-weight: 600;
    font-size: 13px;
}}
 
QPushButton#primary:hover {{
    background-color: {ORANGE_DARK};
}}
 
QPushButton#primary:disabled {{
    background-color: #D9A98A;
}}
 
/* ── Secondary button ── */
QPushButton#secondary {{
    background-color: transparent;
    color: {ORANGE};
    border: 1.5px solid {ORANGE};
    border-radius: 8px;
    padding: 7px 16px;
    font-weight: 500;
}}
 
QPushButton#secondary:hover {{
    background-color: #FFF0E8;
}}
 
/* ── Inputs ── */
QTextEdit, QLineEdit {{
    border: 1px solid {BORDER};
    border-radius: 8px;
    background-color: {CREAM_INPUT};
    color: {TEXT_DARK};
    padding: 6px 10px;
    font-size: 13px;
}}
 
QTextEdit:focus, QLineEdit:focus {{
    border: 1.5px solid {ORANGE};
}}
 
QComboBox {{
    border: 1px solid {BORDER};
    border-radius: 8px;
    background-color: {CREAM_INPUT};
    color: {TEXT_DARK};
    padding: 5px 10px;
    font-size: 13px;
}}
 
QComboBox::drop-down {{
    border: none;
    padding-right: 10px;
}}
 
QComboBox QAbstractItemView {{
    background-color: {CREAM_INPUT};
    border: 1px solid {BORDER};
    selection-background-color: {ORANGE};
    selection-color: white;
}}
 
QCheckBox {{
    spacing: 8px;
    color: {TEXT_DARK};
}}
 
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1.5px solid {BORDER};
    border-radius: 4px;
    background: {CREAM_INPUT};
}}
 
QCheckBox::indicator:checked {{
    background-color: {ORANGE};
    border-color: {ORANGE};
}}
 
/* ── Cards ── */
QFrame#card {{
    background-color: {CREAM_CARD};
    border: 1px solid {BORDER};
    border-radius: 10px;
}}
 
QFrame#cardAccent {{
    background-color: {CREAM_CARD};
    border: 1px solid {BORDER};
    border-left: 4px solid {ORANGE};
    border-radius: 10px;
}}
 
QFrame#metricCard {{
    background-color: {CREAM_CARD};
    border: 1px solid {BORDER};
    border-radius: 12px;
}}

/* ── Caption option cards ── */
QFrame#captionCard {{
    background-color: {CREAM_CARD};
    border: 1.5px solid {BORDER};
    border-radius: 10px;
}}

QFrame#captionCard:hover {{
    border-color: {BROWN_LIGHT};
}}

QFrame#captionCard[selected="true"] {{
    background-color: #FFF0E8;
    border: 1.5px solid {ORANGE};
}}
 
/* ── Section labels ── */
QLabel#sectionLabel {{
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1px;
    color: {BROWN_LIGHT};
    text-transform: uppercase;
}}
 
QLabel#pageTitle {{
    font-size: 24px;
    font-weight: 700;
    color: {TEXT_DARK};
}}
 
QLabel#pageSubtitle {{
    font-size: 13px;
    color: {BROWN_LIGHT};
}}
 
/* ── Info banner ── */
QFrame#infoBanner {{
    background-color: #EEF6FF;
    border: 1px solid #B8D6F5;
    border-left: 4px solid #3A8BCD;
    border-radius: 8px;
}}
 
/* ── Badge ── */
QLabel#badge {{
    background-color: {GREEN_BG};
    color: {GREEN_TEXT};
    border: 1px solid {GREEN_BORDER};
    border-radius: 12px;
    padding: 3px 14px;
    font-size: 11px;
    font-weight: 600;
}}
 
/* ── History item ── */
QFrame#historyItem {{
    background-color: {CREAM_CARD};
    border: 1px solid {BORDER};
    border-radius: 8px;
}}
 
/* ── Divider ── */
QFrame#divider {{
    background-color: {BORDER};
    max-height: 1px;
    min-height: 1px;
}}
 
/* ── Scroll area ── */
QScrollArea {{
    border: none;
    background-color: transparent;
}}
 
QScrollBar:vertical {{
    width: 6px;
    background: transparent;
}}
 
QScrollBar::handle:vertical {{
    background: {BORDER};
    border-radius: 3px;
    min-height: 30px;
}}
 
/* ── Editor toolbar ── */
QFrame#editorToolbar {{
    background-color: {CREAM_CARD};
    border: none;
    border-bottom: 1px solid {BORDER};
}}
 
QLabel#editorTitle {{
    color: {TEXT_DARK};
    font-size: 14px;
    font-weight: 700;
}}
 
QFrame#toolbarDivider {{
    background-color: {BORDER};
    max-width: 1px;
    min-width: 1px;
}}
 
QPushButton#toolbarBtn {{
    background-color: transparent;
    color: {TEXT_MID};
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 13px;
    font-weight: 500;
}}
 
QPushButton#toolbarBtn:hover {{
    background-color: #FFF0E8;
    border-color: {BORDER};
    color: {ORANGE_DARK};
}}
 
QPushButton#toolbarBtn:pressed {{
    background-color: #FBE0D0;
}}
 
QPushButton#toolbarBtn:disabled {{
    color: #C9B8A8;
}}
 
QPushButton#toolbarBtnPrimary {{
    background-color: {ORANGE};
    color: white;
    border: none;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 13px;
    font-weight: 600;
}}
 
QPushButton#toolbarBtnPrimary:hover {{
    background-color: {ORANGE_DARK};
}}
 
QCheckBox#toolbarToggle {{
    spacing: 0px;
    padding: 6px 12px;
    border: 1px solid {BORDER};
    border-radius: 6px;
    background-color: {CREAM_INPUT};
    color: {TEXT_MID};
    font-weight: 600;
}}
 
QCheckBox#toolbarToggle::indicator {{
    width: 0px;
    height: 0px;
}}
 
QCheckBox#toolbarToggle:hover {{
    border-color: {BROWN_LIGHT};
}}
 
QCheckBox#toolbarToggle:checked {{
    background-color: {ORANGE};
    color: white;
    border-color: {ORANGE};
}}
 
QCheckBox#toolbarToggle:disabled {{
    color: #C9B8A8;
    background-color: {CREAM_CARD};
    border-color: {BORDER};
}}
 
QComboBox#toolbarCombo, QSpinBox#toolbarSpin {{
    border: 1px solid {BORDER};
    border-radius: 6px;
    background-color: {CREAM_INPUT};
    color: {TEXT_DARK};
    padding: 4px 8px;
    font-size: 12px;
}}
 
QComboBox#toolbarCombo:disabled, QSpinBox#toolbarSpin:disabled {{
    color: #C9B8A8;
    background-color: {CREAM_CARD};
}}
 
QPushButton#toolbarColorBtn {{
    background-color: {CREAM_INPUT};
    color: {TEXT_MID};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 13px;
    font-weight: 500;
}}
 
QPushButton#toolbarColorBtn:hover {{
    border-color: {ORANGE};
    color: {ORANGE_DARK};
}}
 
QPushButton#toolbarColorBtn:disabled {{
    color: #C9B8A8;
}}
 
/* ── Editor canvas + status bar ── */
QFrame#canvasWrapper {{
    background-color: #E8E2DA;
    border: none;
}}
 
QFrame#editorStatusBar {{
    background-color: {CREAM_CARD};
    border: none;
    border-top: 1px solid {BORDER};
}}
 
QLabel#statusReady {{
    color: {BROWN_LIGHT};
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.5px;
}}
 
QLabel#zoomChip {{
    background-color: {CREAM_INPUT};
    border: 1px solid {BORDER};
    border-radius: 10px;
    padding: 2px 10px;
    color: {TEXT_MID};
    font-size: 11px;
    font-weight: 600;
}}
"""


# ------------------------ Helper widgets -----------------------

def make_divider():
    d = QFrame()
    d.setObjectName("divider")
    d.setFixedHeight(1)
    return d


def make_section_label(text: str) -> QLabel:
    lbl = QLabel(text.upper())
    lbl.setObjectName("sectionLabel")
    return lbl


def make_primary_btn(text: str, full_width=False) -> QPushButton:
    btn = QPushButton(text)
    btn.setObjectName("primary")
    if full_width:
        btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        btn.setFixedHeight(38)
    return btn


def make_secondary_btn(text: str) -> QPushButton:
    btn = QPushButton(text)
    btn.setObjectName("secondary")
    return btn


def make_placeholder(text: str, icon: str = "", height: int = 200) -> QFrame:
    """Dashed placeholder box — mirrors Streamlit's empty state areas."""
    frame = QFrame()
    frame.setFixedHeight(height)
    frame.setStyleSheet(f"""
        QFrame {{
            border: 1.5px dashed {BORDER};
            border-radius: 10px;
            background: transparent;
        }}
    """)
    vbox = QVBoxLayout(frame)
    vbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
    vbox.setSpacing(6)
    if icon:
        icon_lbl = QLabel(icon)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet(f"font-size: 28px; border: none;")
        vbox.addWidget(icon_lbl)
    txt = QLabel(text)
    txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
    txt.setStyleSheet(f"color: {BROWN_LIGHT}; font-size: 13px; border: none;")
    vbox.addWidget(txt)
    return frame


def make_metric_card(label: str, value: str):
    """Compact metric card used on the dashboard grids.

    Returns (card, value_label) so callers can keep a reference to the
    value QLabel and update it later — the card widget alone doesn't let
    you reach back in and change the displayed number.
    """
    card = QFrame()
    card.setObjectName("metricCard")
    card.setMinimumWidth(150)
    card_layout = QVBoxLayout(card)
    card_layout.setContentsMargins(14, 12, 14, 12)
    card_layout.setSpacing(4)

    val_lbl = QLabel(value)
    val_lbl.setWordWrap(True)
    val_lbl.setStyleSheet(f"font-size: 19px; font-weight: 700; color: {TEXT_DARK};")

    lbl_lbl = QLabel(label)
    lbl_lbl.setWordWrap(True)
    lbl_lbl.setStyleSheet(f"font-size: 11px; color: {BROWN_LIGHT};")

    card_layout.addWidget(val_lbl)
    card_layout.addWidget(lbl_lbl)
    return card, val_lbl


# ------------------------------------------------- Editor toolbar helpers --------------------

def make_toolbar_btn(text: str, tooltip: str = "", primary: bool = False) -> QPushButton:
    """A compact icon+label button for the editor toolbar. Purely a visual
    wrapper around QPushButton — callers still connect .clicked as usual."""
    btn = QPushButton(text)
    btn.setObjectName("toolbarBtnPrimary" if primary else "toolbarBtn")
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    if tooltip:
        btn.setToolTip(tooltip)
    return btn


def make_toolbar_divider() -> QFrame:
    """A thin vertical rule used to visually group clusters of toolbar
    controls (File / History / Insert / Layer / Text)."""
    d = QFrame()
    d.setObjectName("toolbarDivider")
    d.setFixedWidth(1)
    d.setFixedHeight(24)
    return d