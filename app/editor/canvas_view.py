"""
Traybakes · AI Marketing Assistant
CanvasView — the QGraphicsView subclass used by the Editor page. Handles
the background grid, smart alignment guides, zoom (Ctrl+wheel), middle-
mouse panning, arrow-key nudging, delete/duplicate shortcuts, and
drag-and-drop image insertion.

Canvas-edge clipping: items are clipped to the canvas by being real Qt
children of ResizableCanvas (which has ItemClipsChildrenToShape set), not
by any painter/clip-rect trick here. That's why AddItemCommand/
DeleteItemCommand below need a reference to editor.canvas_item — it's the
parent items are attached to / detached from.
"""

from PySide6.QtCore import Qt, QPoint, QPointF, Signal
from PySide6.QtGui import QPainter, QPainterPath, QPen, QColor, QBrush, QPixmap
from PySide6.QtWidgets import QGraphicsView

from app.editor.canvas_items import ResizablePixmapItem
from app.editor.commands import AddItemCommand, DeleteItemCommand


class CanvasView(QGraphicsView):

    zoomChanged = Signal(int)

    def __init__(self, scene):
        super().__init__(scene)

        self.zoom = 100
        self.selected_item = None
        self.verticalGuides = []
        self.horizontalGuides = []

        self.setDragMode(QGraphicsView.NoDrag)

        self.zoom_level = 0

        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)

        self._pan = False
        self._pan_start = QPoint()

        self.setTransformationAnchor(
            QGraphicsView.AnchorUnderMouse
        )

        self.setResizeAnchor(
            QGraphicsView.AnchorUnderMouse
        )


    # -------------------------------------------------
    # FOREGROUND
    # -------------------------------------------------

    def drawForeground(self, painter, rect):
        scene = self.scene()

        if not scene:
            return

        if hasattr(scene, "canvas_rect"):

            painter.save()

            painter.setClipRect(scene.canvas_rect)

            super().drawForeground(
                painter,
                rect
            )

            painter.restore()

        else:
            super().drawForeground(
                painter,
                rect
            )


        # -------------------------
        # Smart guides
        # -------------------------

        painter.save()

        pen = QPen(QColor("#F28C28"))
        pen.setWidth(2)
        painter.setPen(pen)

        scene_rect = scene.sceneRect()

        for x in self.verticalGuides:
            painter.drawLine(
                x,
                scene_rect.top(),
                x,
                scene_rect.bottom()
            )

        for y in self.horizontalGuides:
            painter.drawLine(
                scene_rect.left(),
                y,
                scene_rect.right(),
                y
            )

        painter.restore()


        # -------------------------
        # Selection box + handles
        # -------------------------

        if self.selected_item:

            painter.save()

            rect = self.selected_item.sceneBoundingRect()

            pen = QPen(QColor("#F28C28"))
            pen.setWidth(1)

            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)

            painter.drawRect(rect)


            if isinstance(self.selected_item, ResizablePixmapItem):

                painter.setBrush(
                    QBrush(QColor("#F28C28"))
                )

                size = 12

                points = [
                    rect.topLeft(),
                    rect.topRight(),
                    rect.bottomLeft(),
                    rect.bottomRight()
                ]

                for point in points:
                    painter.drawRect(
                        point.x() - size/2,
                        point.y() - size/2,
                        size,
                        size
                    )

            painter.restore()


    # -------------------------------------------------
    # BACKGROUND
    # -------------------------------------------------

    def drawBackground(self, painter, rect):

        super().drawBackground(
            painter,
            rect
        )

        grid_size = 20

        painter.setPen(
            QPen(
                QColor(200,200,200),
                1
            )
        )


        left = int(rect.left()) - (
            int(rect.left()) % grid_size
        )

        top = int(rect.top()) - (
            int(rect.top()) % grid_size
        )


        x = left

        while x < rect.right():

            painter.drawLine(
                x,
                rect.top(),
                x,
                rect.bottom()
            )

            x += grid_size


        y = top

        while y < rect.bottom():

            painter.drawLine(
                rect.left(),
                y,
                rect.right(),
                y
            )

            y += grid_size

    def keyPressEvent(self, event):
        selected_items = self.scene().selectedItems()

        if not selected_items:
            super().keyPressEvent(event)
            return

        step = 10 if event.modifiers() & Qt.ShiftModifier else 1

        dx, dy = 0, 0

        if event.key() == Qt.Key_Left:
            dx = -step
        elif event.key() == Qt.Key_Right:
            dx = step
        elif event.key() == Qt.Key_Up:
            dy = -step
        elif event.key() == Qt.Key_Down:
            dy = step

        if dx != 0 or dy != 0:
            for item in selected_items:
                item.setPos(item.pos().x() + dx, item.pos().y() + dy)
            return

        # DELETE
        if event.key() == Qt.Key_Delete:

            editor = self.editor

            for item in selected_items:

                editor.undo_stack.push(
                    DeleteItemCommand(
                        self.scene(),
                        item
                    )
                )

            return

        # DUPLICATE (Ctrl + D)
        if event.key() == Qt.Key_D and event.modifiers() == Qt.ControlModifier:

            editor = self.editor
            new_items = []

            for item in selected_items:
                clone = ResizablePixmapItem(item.pixmap())
                clone.setPos(item.pos() + QPointF(10, 10))
                clone.undo_stack = getattr(item, "undo_stack", None)

                highest = max(i.zValue() for i in self.scene().items())
                clone.setZValue(highest + 1)

                editor.undo_stack.push(
                    AddItemCommand(
                        self.scene(),
                        clone,
                        editor.canvas_item
                    )
                )

                new_items.append(clone)

            # update selection
            for i in new_items:
                i.setSelected(True)

            return

        super().keyPressEvent(event)

    def wheelEvent(self, event):

        if event.angleDelta().y() > 0:
            self.zoom += 10
        else:
            self.zoom -= 10

        self.zoom = max(10, min(300, self.zoom))

        self.resetTransform()
        self.scale(self.zoom / 100, self.zoom / 100)

        self.zoomChanged.emit(self.zoom)