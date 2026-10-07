"""
Traybakes · AI Marketing Assistant
Canvas item classes used by the Editor page's QGraphicsScene:

- CanvasItem: mixin providing snap-to-guide logic shared by draggable items
- ResizablePixmapItem: an image on the canvas that can be moved and resized
  via corner handles
- DraggableImage: a simpler draggable/selectable image item (kept for
  parity with the original file; not used by EditorPage's own insert flow,
  which uses ResizablePixmapItem)
- DraggableText: an editable, draggable text item
"""

from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QFont, QPen, QColor, QBrush, QTextCursor
from PySide6.QtWidgets import QGraphicsPixmapItem, QGraphicsTextItem, QGraphicsItem, QGraphicsRectItem

from app.editor.commands import MoveItemCommand, ResizeItemCommand, TextEditCommand


# ------------- Canvas Item-----------------

class CanvasItem:
    SNAP_DISTANCE = 10

    def snap_position(self, pos):
        rect = self.scene().canvas_rect
        bounds = self.boundingRect()

        snap = self.SNAP_DISTANCE

        x = pos.x()
        y = pos.y()

        item_left = x
        item_right = x + bounds.width()

        item_top = y
        item_bottom = y + bounds.height()

        item_center_x = x + bounds.width()/2
        item_center_y = y + bounds.height()/2

        vertical_guides = []
        horizontal_guides = []

        # -------------------------
        # Page guides
        # -------------------------

        targets_x = [
            rect.left(),
            rect.center().x(),
            rect.right()
        ]

        targets_y = [
            rect.top(),
            rect.center().y(),
            rect.bottom()
        ]

        for target in targets_x:

            if abs(item_left-target) < snap:
                x = target
                vertical_guides.append(target)

            elif abs(item_right-target) < snap:
                x = target - bounds.width()
                vertical_guides.append(target)

            elif abs(item_center_x-target) < snap:
                x = target - bounds.width()/2
                vertical_guides.append(target)

        for target in targets_y:

            if abs(item_top-target) < snap:
                y = target
                horizontal_guides.append(target)

            elif abs(item_bottom-target) < snap:
                y = target - bounds.height()
                horizontal_guides.append(target)

            elif abs(item_center_y-target) < snap:
                y = target - bounds.height()/2
                horizontal_guides.append(target)

        # -------------------------
        # Object guides
        # -------------------------

        for other in self.scene().items():

            if other is self:
                continue

            if getattr(other, "is_canvas", False):
                continue

            if not hasattr(other, "boundingRect"):
                continue

            other_rect = other.sceneBoundingRect()

            other_x = [
                other_rect.left(),
                other_rect.center().x(),
                other_rect.right()
            ]

            other_y = [
                other_rect.top(),
                other_rect.center().y(),
                other_rect.bottom()
            ]

            for target in other_x:

                if abs(item_left-target) < snap:
                    x = target
                    vertical_guides.append(target)

                elif abs(item_right-target) < snap:
                    x = target - bounds.width()
                    vertical_guides.append(target)

            for target in other_y:

                if abs(item_top-target) < snap:
                    y = target
                    horizontal_guides.append(target)

                elif abs(item_bottom-target) < snap:
                    y = target - bounds.height()
                    horizontal_guides.append(target)


        self.show_guides(
            vertical_guides,
            horizontal_guides
            )

        return QPointF(x, y)

    def show_guides(self, vertical=None, horizontal=None):

        view = self.scene().views()[0]

        view.verticalGuides = vertical  # or []
        view.horizontalGuides = horizontal  # or []
        view.viewport().update()

    def hide_guides(self):

        view = self.scene().views()[0]

        view.verticalGuides = []
        view.horizontalGuides = []

        view.viewport().update()

# ---------------------------------------- Resizable Canvas-------------------
class ResizableCanvas(QGraphicsRectItem):

    HANDLE_SIZE = 12
    MIN_WIDTH = 200
    MIN_HEIGHT = 200
    EDGE = 6

    def __init__(self, rect, editor):
        super().__init__(rect)
        self.setFlag(QGraphicsItem.ItemClipsChildrenToShape, True)
        self.editor = editor
        self.resizing = False
        self.resize_right = False
        self.resize_bottom = False
        self.is_canvas = True

        self.setZValue(-100)

        self.setPen(
            QPen(QColor("#CCCCCC"))
        )

        self.setBrush(
            QBrush(QColor("white"))
        )

        self.setAcceptHoverEvents(True)

    def hoverMoveEvent(self, event):

        rect = self.rect()
        pos = event.pos()

        self.resize_right = abs(pos.x() - rect.right()) <= self.EDGE
        self.resize_bottom = abs(pos.y() - rect.bottom()) <= self.EDGE

        if self.resize_right and self.resize_bottom:
            self.setCursor(Qt.SizeFDiagCursor)
        elif self.resize_right:
            self.setCursor(Qt.SizeHorCursor)
        elif self.resize_bottom:
            self.setCursor(Qt.SizeVerCursor)
        else:
            self.setCursor(Qt.ArrowCursor)

        super().hoverMoveEvent(event)

    def mousePressEvent(self, event):

        if self.resize_right or self.resize_bottom:

            self.resizing = True
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):

        if not self.resizing:
            return

        rect = self.rect()

        width = rect.width()
        height = rect.height()

        if self.resize_right:
            width = max(self.MIN_WIDTH, event.pos().x())

        if self.resize_bottom:
            height = max(self.MIN_HEIGHT, event.pos().y())

        new_rect = QRectF(0, 0, width, height)

        self.setRect(new_rect)

        self.editor.canvas_rect = new_rect
        self.scene().canvas_rect = new_rect
        self.scene().setSceneRect(new_rect)

        self.scene().update()

    def mouseReleaseEvent(self, event):

        self.resizing = False
        self.resize_right = False
        self.resize_bottom = False

        super().mouseReleaseEvent(event)



# ------------------- Resizable Image -------------------------------

class ResizablePixmapItem(QGraphicsPixmapItem):
    MIN_SIZE = 30
    HANDLE_SIZE = 12  

    def __init__(self, pixmap, parent=None):
        self.original_pixmap = pixmap
        super().__init__(pixmap, parent)

        self.setFlags(
            QGraphicsItem.ItemIsMovable |
            QGraphicsItem.ItemIsSelectable |
            QGraphicsItem.ItemSendsGeometryChanges
        )
        self.image_path = None
        self.undo_stack = None
        self.old_position = None
        self.old_pixmap = None
        self.resizing = False
        self.resize_handle = None
        self.start_pos = None
        self.start_rect = None
        self.start_item_pos = None  

    def get_handle_at(self, pos):
        """Hit-test the four corner resize handles in local item coords.
        Returns a string like 'bottom-right' or None."""
        rect = self.boundingRect()
        s = self.HANDLE_SIZE
        handles = {
            "top-left": rect.topLeft(),
            "top-right": rect.topRight(),
            "bottom-left": rect.bottomLeft(),
            "bottom-right": rect.bottomRight(),
        }
        for name, point in handles.items():
            handle_rect = QRectF(point.x() - s / 2, point.y() - s / 2, s, s)
            if handle_rect.contains(pos):
                return name
        return None

    def mousePressEvent(self, event):
        handle = self.get_handle_at(event.pos()) if self.isSelected() else None
        if handle:
            self.resizing = True
            self.resize_handle = handle
            self.start_pos = event.scenePos()
            self.start_rect = self.boundingRect()
            self.start_item_pos = self.pos()
            self.old_pixmap = self.pixmap()
            self.setFlag(QGraphicsItem.ItemIsMovable, False)
            event.accept()
            return

        self.old_position = self.pos()

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not self.resizing:
            super().mouseMoveEvent(event)
            return
        diff = event.scenePos() - self.start_pos

        new_width = self.start_rect.width()
        new_height = self.start_rect.height()

        dx = 0
        dy = 0

        if "right" in self.resize_handle:
            new_width += diff.x()
        elif "left" in self.resize_handle:
            new_width -= diff.x()
            dx = diff.x()

        if "bottom" in self.resize_handle:
            new_height += diff.y()
        elif "top" in self.resize_handle:
            new_height -= diff.y()
            dy = diff.y()

        # Enforce minimum size limits
        if new_width < self.MIN_SIZE:
            new_width = self.MIN_SIZE
            if "left" in self.resize_handle:
                dx = self.start_rect.width() - self.MIN_SIZE

        if new_height < self.MIN_SIZE:
            new_height = self.MIN_SIZE
            if "top" in self.resize_handle:
                dy = self.start_rect.height() - self.MIN_SIZE

        # Scale Pixmap
        scaled = self.original_pixmap.scaled(
            int(new_width),
            int(new_height),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.setPixmap(scaled)

        if dx != 0 or dy != 0:
            self.setPos(self.start_item_pos.x() + dx, self.start_item_pos.y() + dy)

        if self.scene():
            self.scene().update()

    def mouseReleaseEvent(self, event):
        if self.resizing:
            if self.undo_stack and self.old_pixmap is not None:
                self.undo_stack.push(
                    ResizeItemCommand(
                        self,
                        self.old_pixmap,
                        self.pixmap(),
                        self.start_item_pos,
                        self.pos(),
                    )
                )
            self.resizing = False
            self.resize_handle = None
            self.setFlag(QGraphicsItem.ItemIsMovable, True)
            self.hide_guides()
            super().mouseReleaseEvent(event)
            return

        new_position = self.pos()

        if (
            self.undo_stack
            and self.old_position
            and self.old_position != new_position
        ):

            self.undo_stack.push(
                MoveItemCommand(
                    self,
                    self.old_position,
                    new_position
                )
            )

        self.resizing = False
        self.resize_handle = None

        self.hide_guides()

        super().mouseReleaseEvent(event)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            value = self.snap_position(value)
            views = self.scene().views()
            if views:
                views[0].viewport().update()
        return super().itemChange(change, value)

    def snap_position(self, pos):
        if not self.scene() or not hasattr(self.scene(), 'canvas_rect'):
            return pos

        rect = self.scene().canvas_rect
        snap_distance = 10

        x = pos.x()
        y = pos.y()
        bounds = self.boundingRect()

        item_left, item_right = x, x + bounds.width()
        item_top, item_bottom = y, y + bounds.height()
        item_center_x = x + bounds.width() / 2
        item_center_y = y + bounds.height() / 2

        vertical_guides = []
        horizontal_guides = []

        targets_x = [rect.left(), rect.center().x(), rect.right()]
        targets_y = [rect.top(), rect.center().y(), rect.bottom()]

        for target in targets_x:
            if abs(item_left - target) < snap_distance:
                x = target
                vertical_guides.append(target)
            elif abs(item_right - target) < snap_distance:
                x = target - bounds.width()
                vertical_guides.append(target)
            elif abs(item_center_x - target) < snap_distance:
                x = target - bounds.width() / 2
                vertical_guides.append(target)

        for target in targets_y:
            if abs(item_top - target) < snap_distance:
                y = target
                horizontal_guides.append(target)
            elif abs(item_bottom - target) < snap_distance:
                y = target - bounds.height()
                horizontal_guides.append(target)
            elif abs(item_center_y - target) < snap_distance:
                y = target - bounds.height() / 2
                horizontal_guides.append(target)

        for item in self.scene().items():
            if item == self or not isinstance(item, QGraphicsPixmapItem):
                continue

            other = item.sceneBoundingRect()
            if abs(item_left - other.right()) < snap_distance:
                x = other.right()
                vertical_guides.append(other.right())
            elif abs(item_right - other.left()) < snap_distance:
                x = other.left() - bounds.width()
                vertical_guides.append(other.left())
            elif abs(item_center_x - other.center().x()) < snap_distance:
                x = other.center().x() - bounds.width() / 2
                vertical_guides.append(other.center().x())

            if abs(item_top - other.bottom()) < snap_distance:
                y = other.bottom()
                horizontal_guides.append(other.bottom())
            elif abs(item_bottom - other.top()) < snap_distance:
                y = other.top() - bounds.height()
                horizontal_guides.append(other.top())
            elif abs(item_center_y - other.center().y()) < snap_distance:
                y = other.center().y() - bounds.height() / 2
                horizontal_guides.append(other.center().y())

        self.show_guides(vertical_guides, horizontal_guides)
        return QPointF(x, y)

    def show_guides(self, vertical, horizontal):
        if self.scene() and self.scene().views():
            view = self.scene().views()[0]
            view.verticalGuides = vertical
            view.horizontalGuides = horizontal
            view.viewport().update()

    def hide_guides(self):
        if self.scene() and self.scene().views():
            view = self.scene().views()[0]
            view.verticalGuides = []
            view.horizontalGuides = []
            view.viewport().update()


# ---------------------- Draggable Image ------------------------------------------------

class DraggableImage(QGraphicsPixmapItem, CanvasItem):
    def __init__(self, pixmap):
        super().__init__(pixmap)

        self.setFlags(
            QGraphicsPixmapItem.ItemIsMovable |
            QGraphicsPixmapItem.ItemIsSelectable |
            QGraphicsPixmapItem.ItemSendsGeometryChanges
        )

        self.setTransformationMode(Qt.SmoothTransformation)

        self.normal_pen = QPen(Qt.transparent)
        self.selected_pen = QPen(QColor(0, 120, 255), 2)

    def paint(self, painter, option, widget):
        super().paint(painter, option, widget)

        if not (self.isSelected() or self.resizing):
            return

        rect = self.rect()

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#F28C28"))

        painter.drawRect(
            QRectF(
                rect.right() - 10,
                rect.bottom() - 10,
                10,
                10,
            )
        )

    def mouseReleaseEvent(self, event):
        self.hide_guides()
        super().mouseReleaseEvent(event)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            return self.snap_position(value)

        return super().itemChange(change, value)


#-------------------------- Draggable Text-----------------------------------

class DraggableText(QGraphicsTextItem, CanvasItem):
    def __init__(self, text="Double click to edit"):
        # Explicitly initialize both parents due to Qt MRO limitations
        QGraphicsTextItem.__init__(self, text)
        CanvasItem.__init__(self)

        self.setFlags(
            QGraphicsTextItem.ItemIsMovable |
            QGraphicsTextItem.ItemIsSelectable |
            QGraphicsTextItem.ItemIsFocusable
        )

        self.setTextInteractionFlags(Qt.NoTextInteraction)
        self.undo_stack = None
        self.old_position = None
        self._text_before_edit = None

        font = QFont("Arial", 16)
        self.setFont(font)
        self.document().setDefaultFont(font)

    def mousePressEvent(self, event):
        self.old_position = self.pos()
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):

        self._text_before_edit = self.toPlainText()

        cursor = self.textCursor()
        cursor.select(QTextCursor.Document)

        fmt = cursor.charFormat()
        fmt.setFont(self.font())

        cursor.mergeCharFormat(fmt)
        self.setTextCursor(cursor)

        self.setTextInteractionFlags(Qt.TextEditorInteraction)
        self.setFocus()

        super().mouseDoubleClickEvent(event)

    def mouseReleaseEvent(self, event):
        new_position = self.pos()

        if (
            self.undo_stack
            and self.old_position
            and self.old_position != new_position
            and self.scene()
        ):
            self.undo_stack.push(
                MoveItemCommand(
                    self,
                    self.old_position,
                    new_position
                )
            )

        self.hide_guides()
        super().mouseReleaseEvent(event)

    def focusOutEvent(self, event):
        self.setTextInteractionFlags(Qt.NoTextInteraction)
        # REMOVED: self.clearFocus() to avoid recursion/redundancy

        new_text = self.toPlainText()
        old_text = self._text_before_edit
        if self.undo_stack and old_text is not None and old_text != new_text:
            self.undo_stack.push(TextEditCommand(self, old_text, new_text))
        self._text_before_edit = None

        super().focusOutEvent(event)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            return self.snap_position(value)

        return super().itemChange(change, value)
