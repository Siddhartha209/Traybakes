"""
Traybakes · AI Marketing Assistant
Editor undo/redo commands (QUndoCommand subclasses) used by the canvas
editor: text styling, add/delete/move/resize of canvas items, and plain
text edits.
"""

from PySide6.QtGui import QUndoCommand, QTextCharFormat, QTextCursor
from PySide6.QtCore import QRectF 


class TextStyleCommand(QUndoCommand):

    def __init__(
        self,
        item,
        old_font,
        new_font,
        old_color,
        new_color
    ):

        super().__init__("Text Style")

        self.item = item

        self.old_font = old_font
        self.new_font = new_font

        self.old_color = old_color
        self.new_color = new_color

    def apply_style(self, font, color):

        self.item.setFont(font)

        self.item.setDefaultTextColor(color)

        cursor = self.item.textCursor()

        cursor.select(
            QTextCursor.Document
        )

        fmt = QTextCharFormat()

        fmt.setFont(font)

        fmt.setForeground(color)

        cursor.mergeCharFormat(fmt)

        self.item.setTextCursor(cursor)

    def undo(self):

        self.apply_style(
            self.old_font,
            self.old_color
        )

    def redo(self):

        self.apply_style(
            self.new_font,
            self.new_color
        )


# ------------------Add/Delete Commands ------------------------
class AddItemCommand(QUndoCommand):

    def __init__(self, scene, item, canvas_item):
        super().__init__("Add Item")

        self.scene = scene
        self.item = item
        self.canvas_item = canvas_item

    def undo(self):
        self.scene.removeItem(self.item)

    def redo(self):
        self.item.setParentItem(self.canvas_item)


class DeleteItemCommand(QUndoCommand):

    def __init__(self, scene, item):
        super().__init__("Delete Item")

        self.scene = scene
        self.item = item
        self.parent = item.parentItem()

    def undo(self):
        if self.parent:
            self.item.setParentItem(self.parent)
        else:
            self.scene.addItem(self.item)

    def redo(self):
        self.item.setParentItem(None)
        self.scene.removeItem(self.item)

class MoveItemCommand(QUndoCommand):

    def __init__(
        self,
        item,
        old_pos,
        new_pos
    ):

        super().__init__("Move Item")

        self.item = item
        self.old_pos = old_pos
        self.new_pos = new_pos

    def undo(self):

        self.item.setPos(
            self.old_pos
        )

    def redo(self):

        self.item.setPos(
            self.new_pos
        )


class ResizeItemCommand(QUndoCommand):
    """Undoes/redoes both the pixmap (size) AND the position of a resized
    image. Position matters too because dragging a top/left handle shifts
    item.pos() as well as its size — restoring only the pixmap on undo
    would leave the item in the wrong place."""

    def __init__(
        self,
        item,
        old_pixmap,
        new_pixmap,
        old_pos,
        new_pos,
    ):

        super().__init__("Resize Image")

        self.item = item
        self.old_pixmap = old_pixmap
        self.new_pixmap = new_pixmap
        self.old_pos = old_pos
        self.new_pos = new_pos

    def undo(self):

        self.item.setPixmap(
            self.old_pixmap
        )
        self.item.setPos(self.old_pos)

    def redo(self):

        self.item.setPixmap(
            self.new_pixmap
        )
        self.item.setPos(self.new_pos)


class TextEditCommand(QUndoCommand):
    """Tracks a change to a DraggableText's plain-text content, pushed once
    editing finishes (on focus-out) rather than per keystroke."""

    def __init__(self, item, old_text, new_text):
        super().__init__("Edit Text")
        self.item = item
        self.old_text = old_text
        self.new_text = new_text

    def undo(self):
        self.item.setPlainText(self.old_text)

    def redo(self):
        self.item.setPlainText(self.new_text)
