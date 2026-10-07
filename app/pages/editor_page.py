"""
Traybakes · AI Marketing Assistant
EditorPage — the canvas editor: toolbar (open/save/export, undo/redo,
insert image/text, layering controls, text style controls) wired to a
QGraphicsScene/QUndoStack, with .tray project save/open support.
"""

import os
import json
import zipfile
import shutil
import tempfile

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import (
    QFont, QPainter, QPen, QColor, QBrush, QImage, QUndoStack, QPixmap,
)
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QGraphicsScene, QFileDialog, QSpinBox, QCheckBox, QColorDialog,
    QFontComboBox, QSlider
)

from app.editor.canvas_view import CanvasView
from app.editor.canvas_items import ResizablePixmapItem, DraggableText, ResizableCanvas
from app.editor.commands import AddItemCommand, TextStyleCommand
from app.styles import make_toolbar_btn, make_toolbar_divider


class EditorPage(QWidget):
    def __init__(self):
        super().__init__()

        # ─────────────────────────────
        # State
        # ─────────────────────────────
        self.current_item = None
        self.undo_stack = QUndoStack(self)
        self.selected_color = QColor("black")

        # ─────────────────────────────
        # Scene
        # ─────────────────────────────
        self.scene = QGraphicsScene()
        self.scene.setSceneRect(-200, -200, 1600, 1200)
        self.scene.selectionChanged.connect(self.on_selection_changed)

        # ─────────────────────────────
        # Smart Guide
        # ─────────────────────────────
        # Smart guide lines
        guide_pen = QPen(QColor("#F28C28"))   # Traybakes orange
        guide_pen.setWidth(2)

        #self.v_guide = self.scene.addLine(0, 0, 0, 800, guide_pen)
        #self.h_guide = self.scene.addLine(0, 0, 1200, 0, guide_pen)

        # ─────────────────────────────
        # Layout
        # ─────────────────────────────
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ─────────────────────────────
        # Toolbar
        # ─────────────────────────────
        toolbar = QFrame()
        toolbar.setObjectName("editorToolbar")
        toolbar.setFixedHeight(56)

        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(18, 8, 18, 8)
        toolbar_layout.setSpacing(6)

        # Page title
        editor_title = QLabel("🪄  Editor")
        editor_title.setObjectName("editorTitle")
        toolbar_layout.addWidget(editor_title)
        toolbar_layout.addSpacing(14)
        toolbar_layout.addWidget(make_toolbar_divider())
        toolbar_layout.addSpacing(10)

        # -- File group: Open / Save / Export --
        self.open_btn = make_toolbar_btn("📂  Open", "Open a saved project (.tray)")
        self.open_btn.clicked.connect(self.open_project)
        toolbar_layout.addWidget(self.open_btn)

        self.save_btn = make_toolbar_btn("💾  Save", "Save this project (.tray)")
        self.save_btn.clicked.connect(self.save_project)
        toolbar_layout.addWidget(self.save_btn)

        self.export_btn = make_toolbar_btn("📤  Export", "Export the canvas as an image", primary=True)
        self.export_btn.clicked.connect(self.export_image)
        toolbar_layout.addWidget(self.export_btn)

        toolbar_layout.addSpacing(8)
        toolbar_layout.addWidget(make_toolbar_divider())
        toolbar_layout.addSpacing(8)

        # -- History group: Undo / Redo --
        self.undo_btn = make_toolbar_btn("↶  Undo", "Undo last action")
        self.undo_btn.clicked.connect(self.undo_stack.undo)
        toolbar_layout.addWidget(self.undo_btn)

        self.redo_btn = make_toolbar_btn("↷  Redo", "Redo last undone action")
        self.redo_btn.clicked.connect(self.undo_stack.redo)
        toolbar_layout.addWidget(self.redo_btn)

        toolbar_layout.addSpacing(8)
        toolbar_layout.addWidget(make_toolbar_divider())
        toolbar_layout.addSpacing(8)

        # -- Insert group: Image / Text --
        self.insert_image_btn = make_toolbar_btn("🖼  Image", "Insert an image onto the canvas")
        self.insert_image_btn.clicked.connect(self.insert_image)
        toolbar_layout.addWidget(self.insert_image_btn)

        self.insert_text_btn = make_toolbar_btn("🔤  Text", "Insert a text box onto the canvas")
        self.insert_text_btn.clicked.connect(self.insert_text)
        toolbar_layout.addWidget(self.insert_text_btn)

        toolbar_layout.addSpacing(8)
        toolbar_layout.addWidget(make_toolbar_divider())
        toolbar_layout.addSpacing(8)

        # -- Layer order group: Front / Forward / Backward / Back --
        self.front_btn = make_toolbar_btn("⤒", "Bring to front")
        self.front_btn.clicked.connect(self.bring_to_front)
        toolbar_layout.addWidget(self.front_btn)

        self.forward_btn = make_toolbar_btn("▲", "Bring forward")
        self.forward_btn.clicked.connect(self.bring_forward)
        toolbar_layout.addWidget(self.forward_btn)

        self.backward_btn = make_toolbar_btn("▼", "Send backward")
        self.backward_btn.clicked.connect(self.send_backward)
        toolbar_layout.addWidget(self.backward_btn)

        self.back_btn = make_toolbar_btn("⤓", "Send to back")
        self.back_btn.clicked.connect(self.send_to_back)
        toolbar_layout.addWidget(self.back_btn)

        toolbar_layout.addSpacing(8)
        toolbar_layout.addWidget(make_toolbar_divider())
        toolbar_layout.addSpacing(8)

        # -- Text formatting group: font / size / B / I / U / color --
        self.font_family = QFontComboBox()
        self.font_family.setObjectName("toolbarCombo")
        self.font_family.setFixedWidth(140)
        self.font_family.setToolTip("Font family (select a text box to enable)")
        self.font_family.currentFontChanged.connect(self.update_text_style)
        toolbar_layout.addWidget(self.font_family)

        self.font_size = QSpinBox()
        self.font_size.setObjectName("toolbarSpin")
        self.font_size.setRange(6, 200)
        self.font_size.setValue(16)
        # Increased width here from 58 to 80 to make room for digits and spin buttons
        self.font_size.setFixedWidth(80)
        self.font_size.setToolTip("Font size (select a text box to enable)")
        self.font_size.valueChanged.connect(self.update_text_style)
        self.font_size.setEnabled(False)
        toolbar_layout.addWidget(self.font_size)

        toolbar_layout.addSpacing(6)

        self.bold_btn = QCheckBox("B")
        self.bold_btn.setObjectName("toolbarToggle")
        self.bold_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.bold_btn.setToolTip("Bold")
        self.bold_btn.stateChanged.connect(self.update_text_style)
        self.bold_btn.setEnabled(False)
        toolbar_layout.addWidget(self.bold_btn)

        self.italic_btn = QCheckBox("I")
        self.italic_btn.setObjectName("toolbarToggle")
        self.italic_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.italic_btn.setToolTip("Italic")
        self.italic_btn.stateChanged.connect(self.update_text_style)
        self.italic_btn.setEnabled(False)
        toolbar_layout.addWidget(self.italic_btn)

        self.underline_btn = QCheckBox("U")
        self.underline_btn.setObjectName("toolbarToggle")
        self.underline_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.underline_btn.setToolTip("Underline")
        self.underline_btn.stateChanged.connect(self.update_text_style)
        self.underline_btn.setEnabled(False)
        toolbar_layout.addWidget(self.underline_btn)

        toolbar_layout.addSpacing(6)

        self.color_btn = QPushButton("🎨  Color")
        self.color_btn.setObjectName("toolbarColorBtn")
        self.color_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.color_btn.setToolTip("Text color (select a text box to enable)")
        self.color_btn.clicked.connect(self.pick_color)
        self.color_btn.setEnabled(False)
        toolbar_layout.addWidget(self.color_btn)

        toolbar_layout.addStretch()

        layout.addWidget(toolbar)

        # ─────────────────────────────
        # Canvas
        # ─────────────────────────────
        canvas_wrapper = QFrame()
        canvas_wrapper.setObjectName("canvasWrapper")
        canvas_wrapper_layout = QVBoxLayout(canvas_wrapper)
        canvas_wrapper_layout.setContentsMargins(0, 0, 0, 0)
        canvas_wrapper_layout.setSpacing(0)

        self.view = CanvasView(self.scene)
        self.view.editor = self
        self.view.zoomChanged.connect(self.sync_zoom_slider)
        self.view.setRenderHints(
            QPainter.Antialiasing |
            QPainter.SmoothPixmapTransform |
            QPainter.TextAntialiasing
        )

        self.view.setFrameShape(QFrame.NoFrame)
        self.view.setStyleSheet("border: none;")

        canvas_wrapper_layout.addWidget(self.view)
        layout.addWidget(canvas_wrapper, 1)

        # Page
        canvas_width = 1200
        canvas_height = 800
        if(hasattr(self,"last_state") and self.last_state and
           self.last_state.images.get("generated_output_path")):
            image_path = self.last_state.images.get("generated_output_path")
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                canvas_width = pixmap.width()
                canvas_height = pixmap.height()
        self.canvas_rect = QRectF(0,0,canvas_width, canvas_height)
        self.canvas_item = ResizableCanvas(
            self.canvas_rect,
            self
        )

        self.scene.addItem(
            self.canvas_item
        )
        self.scene.canvas_rect = self.canvas_rect
        # Shadow
        #shadow = self.scene.addRect(
            #QRectF(-5, -5, 1210, 810),
            #QPen(Qt.NoPen),
            #QBrush(QColor(0, 0, 0, 20))
        #)
        #shadow.setZValue(-1)

        # View setup
        self.view.setSceneRect(self.scene.sceneRect())
        self.view.centerOn(600, 400)

        self.view.setBackgroundBrush(QColor("#E5E5E5"))

        # ─────────────────────────────
        # Status bar
        # ─────────────────────────────
        status = QFrame()
        status.setObjectName("editorStatusBar")
        status.setFixedHeight(30)

        status_layout = QHBoxLayout(status)
        status_layout.setContentsMargins(18, 0, 18, 0)

        ready_label = QLabel("●  READY")
        ready_label.setObjectName("statusReady")
        status_layout.addWidget(ready_label)
        status_layout.addStretch()

        zoom_text = QLabel("Zoom")
        zoom_text.setObjectName("statusLabel")
        status_layout.addWidget(zoom_text)

        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setRange(10, 300)
        self.zoom_slider.setValue(100)
        self.zoom_slider.setFixedWidth(160)
        self.zoom_slider.valueChanged.connect(self.set_zoom)

        self.zoom_slider.setStyleSheet("""
        QSlider::groove:horizontal {
            height: 6px;
            background: #2B2B2B;
            border-radius: 3px;
        }

        QSlider::sub-page:horizontal {
            background: #F28C28;
            border-radius: 3px;
        }

        QSlider::handle:horizontal {
            background: white;
            width: 16px;
            margin: -5px 0;
            border-radius: 8px;
        }

        QSlider::handle:horizontal:hover {
            background: #FFD29A;
        }
        """)

        status_layout.addWidget(self.zoom_slider)

        self.zoom_label = QLabel("100%")
        self.zoom_label.setObjectName("zoomChip")
        status_layout.addWidget(self.zoom_label)

        layout.addWidget(status)

    def set_zoom(self, percent):
        self.view.zoom = percent
        self.view.resetTransform()
        self.view.scale(percent/100,percent/100)

        self.zoom_label.setText(f"{percent}%")

    def sync_zoom_slider(self, value):
        self.zoom_slider.blockSignals(True)
        self.zoom_slider.setValue(value)
        self.zoom_slider.blockSignals(False)

        self.zoom_label.setText(f"{value}%")

    # ─────────────────────────────
    # Insert image
    # ─────────────────────────────
    def insert_image(self):
        default_directory = os.path.join("img_gen", "outputs")
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Image",
            default_directory,
            "Images (*.png *.jpg *.jpeg *.bmp)"
        )

        if not file_path:
            return

        pixmap = QPixmap(file_path)

        if pixmap.isNull():
            return

        item = ResizablePixmapItem(pixmap)
        item.undo_stack = self.undo_stack
        item.image_path = file_path
        highest = max(i.zValue() for i in self.scene.items())
        item.setZValue(highest+1)

        canvas_center = self.canvas_rect.center()

        image_rect = item.boundingRect()

        item.setPos(
            canvas_center.x() - image_rect.width() / 2,
            canvas_center.y() - image_rect.height() / 2
        )

        self.undo_stack.push(AddItemCommand(self.scene, item, self.canvas_item))

    # ─────────────────────────────
    # Insert text
    # ─────────────────────────────
    def insert_text(self):
        item = DraggableText("New text")
        item.undo_stack = self.undo_stack
        center = self.view.mapToScene(
            self.view.viewport().rect().center()
        )
        item.setPos(center)
        highest = max(i.zValue() for i in self.scene.items())
        item.setZValue(highest + 1)
        self.undo_stack.push(AddItemCommand(self.scene, item, self.canvas_item))

    # ─────────────────────────────
    # Selection handler
    # ─────────────────────────────
    def on_selection_changed(self):
        if self.scene is None:
            return

        items = self.scene.selectedItems()

        self.current_item = items[0] if items else None

        self.view.selected_item = self.current_item
        self.view.viewport().update()

        is_text = isinstance(self.current_item, DraggableText)

        # Enable/disable toolbar
        self.font_family.setEnabled(is_text)
        self.font_size.setEnabled(is_text)
        self.bold_btn.setEnabled(is_text)
        self.italic_btn.setEnabled(is_text)
        self.underline_btn.setEnabled(is_text)
        self.color_btn.setEnabled(is_text)

        if not is_text:
            return

        # Prevent update_text_style() from firing while we populate the toolbar
        self.font_family.blockSignals(True)
        self.font_size.blockSignals(True)
        self.bold_btn.blockSignals(True)
        self.italic_btn.blockSignals(True)
        self.underline_btn.blockSignals(True)

        font = self.current_item.font()

        self.font_family.setCurrentFont(font)
        self.font_size.setValue(font.pointSize())
        self.bold_btn.setChecked(font.bold())
        self.italic_btn.setChecked(font.italic())
        self.underline_btn.setChecked(font.underline())

        self.font_family.blockSignals(False)
        self.font_size.blockSignals(False)
        self.bold_btn.blockSignals(False)
        self.italic_btn.blockSignals(False)
        self.underline_btn.blockSignals(False)

        self.selected_color = self.current_item.defaultTextColor()

    # ─────────────────────────────
    # Text formatting
    # ─────────────────────────────
    def update_text_style(self):

        if not isinstance(
            self.current_item,
            DraggableText
        ):
            return

        old_font = QFont(
            self.current_item.font()
        )

        old_color = (
            self.current_item.defaultTextColor()
        )

        new_font = QFont(old_font)
        new_font.setFamily(self.font_family.currentFont().family())

        new_font.setPointSize(
            self.font_size.value()
        )

        new_font.setBold(
            self.bold_btn.isChecked()
        )

        new_font.setItalic(
            self.italic_btn.isChecked()
        )

        new_font.setUnderline(
            self.underline_btn.isChecked()
        )

        new_color = self.selected_color

        self.undo_stack.push(
            TextStyleCommand(
                self.current_item,
                old_font,
                new_font,
                old_color,
                new_color
            )
        )

    # ─────────────────────────────
    # Color picker
    # ─────────────────────────────
    def pick_color(self):
        color = QColorDialog.getColor()

        if color.isValid():
            self.selected_color = color
            self.update_text_style()

    def bring_forward(self):
        if not self.current_item:
            return

        self.current_item.setZValue(
            self.current_item.zValue() + 1
        )
        self.normalize_layers()

    def send_backward(self):
        if not self.current_item:
            return

        self.current_item.setZValue(
            self.current_item.zValue() - 1)
        self.normalize_layers()

    def bring_to_front(self):
        if not self.current_item:
            return
        items = self.get_layer_items()
        highest = max(
            item.zValue()
            for item in self.scene.items()
        )

        self.current_item.setZValue(highest + 1)
        self.normalize_layers()

    def send_to_back(self):
        if not self.current_item:
            return

        lowest = min(
            item.zValue()
            for item in self.scene.items()
        )

        self.current_item.setZValue(0)
        self.normalize_layers()

    def get_layer_items(self):
        return [
            item for item in self.scene.items()
            if isinstance(item, (ResizablePixmapItem, DraggableText))
        ]

    def normalize_layers(self):

        items = self.get_layer_items()

        items.sort(key=lambda item: item.zValue())

        for index, item in enumerate(items, start=1):
            item.setZValue(index)

    def export_image(self):

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Image",
            "",
            "PNG Image (*.png);;JPEG Image (*.jpg)"
        )

        if not file_path:
            return

        image = QImage(
            self.canvas_rect.size().toSize(),
            QImage.Format_ARGB32
        )

        image.fill(Qt.white)

        painter = QPainter(image)

        self.scene.render(
            painter,
            QRectF(image.rect()),
            self.canvas_rect
        )

        painter.end()

        image.save(file_path)

    def save_project(self):

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Project",
            "",
            "Traybakes Project (*.tray)"
        )

        if not file_path:
            return

        if not file_path.endswith(".tray"):
            file_path += ".tray"

        temp_dir = tempfile.mkdtemp()

        assets_dir = os.path.join(
            temp_dir,
            "assets"
        )

        os.makedirs(assets_dir)

        project = {
            "canvas": {
                "width": self.canvas_rect.width(),
                "height": self.canvas_rect.height()
            },
            "items": []
        }

        image_index = 1

        for item in self.scene.items():

            if isinstance(item, ResizablePixmapItem):

                filename = f"image_{image_index}.png"

                asset_path = os.path.join(
                    assets_dir,
                    filename
                )

                item.pixmap().save(asset_path)

                project["items"].append({

                    "type": "image",

                    "path":
                        f"assets/{filename}",

                    "x": item.pos().x(),
                    "y": item.pos().y(),
                    "z": item.zValue()

                })

                image_index += 1

            elif isinstance(item, DraggableText):

                project["items"].append({

                    "type": "text",

                    "text": item.toPlainText(),

                    "x": item.pos().x(),
                    "y": item.pos().y(),

                    "z": item.zValue(),

                    "font_family": 
                        item.font().family(),

                    "font_size":
                        item.font().pointSize(),

                    "bold":
                        item.font().bold(),

                    "italic":
                        item.font().italic(),

                    "underline":
                        item.font().underline(),

                    "color":
                        item.defaultTextColor().name()
                })

        json_path = os.path.join(
            temp_dir,
            "project.json"
        )

        with open(json_path,"w", encoding="utf-8") as f:
            json.dump(
                project,
                f,
                indent=4,
                ensure_ascii=False
            )

        with zipfile.ZipFile(
            file_path,
            "w"
        ) as zip_file:

            for root, dirs, files in os.walk(temp_dir):

                for file in files:

                    full_path = os.path.join(
                        root,
                        file
                    )

                    relative = os.path.relpath(
                        full_path,
                        temp_dir
                    )

                    zip_file.write(
                        full_path,
                        relative
                    )

        shutil.rmtree(temp_dir)

    def open_project(self):

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Project",
            "",
            "Traybakes Project (*.tray)"
        )

        if not file_path:
            return

        temp_dir = tempfile.mkdtemp()
        with zipfile.ZipFile(file_path,"r") as zip_file:
            zip_file.extractall(temp_dir)

        json_path = os.path.join(
            temp_dir,
            "project.json"
        )
        with open(json_path,"r") as file:
            data=json.load(file)

        # Remove existing objects
        for item in self.scene.items():

            if isinstance(item, (ResizablePixmapItem, DraggableText)):
                self.scene.removeItem(item)

        # Rebuild objects

        for item_data in data["items"]:

            # -------------------------
            # IMAGE
            # -------------------------

            if item_data["type"] == "image":

                image_path = os.path.join(temp_dir, item_data["path"])
                pixmap = QPixmap(
                    image_path
                )

                if pixmap.isNull():
                    continue

                item = ResizablePixmapItem(pixmap)

                item.image_path = item_data["path"]

                item.undo_stack = self.undo_stack

                item.setPos(
                    item_data["x"],
                    item_data["y"]
                )

                item.setZValue(
                    item_data["z"]
                )

                item.setParentItem(self.canvas_item)

            # -------------------------
            # TEXT
            # -------------------------

            elif item_data["type"] == "text":

                item = DraggableText(item_data.get("text", ""))
                item.undo_stack = self.undo_stack

                item.setPos(
                    item_data["x"],
                    item_data["y"]
                )

                font = item.font()

                font.setFamily(item_data.get("font_family",
                    "Arial"))

                font.setPointSize(
                    item_data["font_size"]
                )

                font.setBold(
                    item_data["bold"]
                )

                font.setItalic(
                    item_data["italic"]
                )

                font.setUnderline(
                    item_data["underline"]
                )

                item.setFont(font)

                item.document().setDefaultFont(font)

                item.setDefaultTextColor(
                    QColor(
                        item_data["color"]
                    )
                )

                item.setZValue(
                    item_data["z"]
                )

                item.setParentItem(self.canvas_item)