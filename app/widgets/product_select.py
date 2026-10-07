"""
Traybakes · AI Marketing Assistant
ProductMultiSelect — a button that opens a checklist menu of products.

Resolution order for the product list:
  1. Scan img_gen/products/ on disk (one subfolder = one product) — this
     is the source of truth, since it's what actually has reference
     images available.
  2. If that can't be resolved (backend not importable, folder missing),
     fall back to a hardcoded list matching the known product folders,
     so the menu still works and the app doesn't hard-depend on the
     backend just to show product names.

Zero selections means "don't mention specific products" — the caller
should treat an empty list as a no-op rather than adding empty text to
the goal.
"""

import os
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton, QMenu, QWidgetAction, QCheckBox
from app.styles import BORDER, ORANGE, TEXT_DARK
FALLBACK_PRODUCT_KEYS = [
    "all_butter_flapjack",
    "all_butter_flapjack_with_chocolate",
    "biscuit_tiffin",
    "caramel_shortcake",
    "cinder_road",
    "dark_chocolate_brownie",
    "granola_bar",
    "honeycomb_crunch",
    "indulgent_flapjack",
    "paradise_flapjack",
    "peppermint_crunch",
    "rocky_road",
    "salted_caramel_brownie",
    "vegan_flapjack",
]

PRODUCTS_DIR = None
try:
    from img_gen.config import PRODUCTS_DIR
except Exception:
    pass

PRODUCT_DESCRIPTIONS = {}
try:
    from img_gen.data import PRODUCTS as PRODUCT_DESCRIPTIONS
except Exception:
    pass


def discover_products() -> list[str]:
    """Returns sorted product keys — one per subfolder of PRODUCTS_DIR,
    falling back to FALLBACK_PRODUCT_KEYS if the folder can't be read."""
    if PRODUCTS_DIR and os.path.isdir(PRODUCTS_DIR):
        found = sorted(
            name for name in os.listdir(PRODUCTS_DIR)
            if os.path.isdir(os.path.join(PRODUCTS_DIR, name))
        )
        if found:
            return found

    return sorted(FALLBACK_PRODUCT_KEYS)


class ProductMultiSelect(QPushButton):
    def __init__(self, product_keys: list[str] | None = None, parent=None):
        super().__init__("Choose Product", parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._checkboxes: dict[str, QCheckBox] = {}
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {TEXT_DARK};
                border: 1px solid {BORDER};
                border-radius: 6px;
                padding: 6px 10px;
                text-align: left;
            }}
            QPushButton:hover {{
                border-color: {ORANGE};
            }}
            QPushButton::menu-indicator {{
                subcontrol-origin: padding;
                subcontrol-position: center right;
                right: 8px;
            }}
        """)
        if product_keys is None:
            product_keys = discover_products()

        menu = QMenu(self)

        for key in product_keys:
            label = key.replace("_", " ").title()

            checkbox = QCheckBox(label, menu)
            checkbox.setToolTip(PRODUCT_DESCRIPTIONS.get(key, label))
            checkbox.stateChanged.connect(self._update_label)

            action = QWidgetAction(menu)
            action.setDefaultWidget(checkbox)
            menu.addAction(action)

            self._checkboxes[key] = checkbox

        self.setMenu(menu)
        self.setEnabled(bool(product_keys))
        self._update_label()

    def _update_label(self):
        selected = self.selected_labels()
        if not selected:
            self.setText(" None")
        elif len(selected) == 1:
            self.setText(f"Product: {selected[0]}")
        else:
            self.setText(f"Products ({len(selected)} selected)")

    def selected_products(self) -> list[str]:
        """Raw folder-name keys, e.g. 'paradise_flapjack'."""
        return [key for key, cb in self._checkboxes.items() if cb.isChecked()]

    def selected_labels(self) -> list[str]:
        """Human-readable labels, e.g. 'Paradise Flapjack'."""
        return [key.replace("_", " ").title() for key in self.selected_products()]

    def clear_selection(self):
        for cb in self._checkboxes.values():
            cb.blockSignals(True)
            cb.setChecked(False)
            cb.blockSignals(False)
        self._update_label()