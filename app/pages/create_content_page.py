import os

from PySide6.QtCore import Qt, Signal, QThread, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QTextEdit,
    QLineEdit, QFrame, QFileDialog, QPushButton, QInputDialog, QMessageBox,
    QDialog, QApplication
)

from app.styles import (
    make_divider,
    make_section_label,
    make_primary_btn,
    make_secondary_btn,
    TEXT_DARK,
    GREEN_TEXT,
    BORDER,
    BROWN_LIGHT,
    ORANGE,
    ORANGE_DARK,
)
from app.widgets.caption_card import CaptionCard
from app.widgets.output_preview import OutputPreview
from app.widgets.product_select import ProductMultiSelect
from app.workers.orchestrator_worker import OrchestratorWorker
from app.workers.image_tweak_worker import ImageTweakWorker
from app.backend import (
    BACKEND_AVAILABLE,
    BACKEND_IMPORT_ERROR,
    _campaign_db,
    record_selection,
    record_rating,
    record_caption_rating,
    record_caption_edit,
)


# ── Custom Visually Consistent Edit Window ──
class EditCaptionDialog(QDialog):
    """A highly polished edit modal that matches the Traybakes UI design language."""
    def __init__(self, initial_text, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Base Caption")
        self.setMinimumSize(460, 280)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: #FAFAFA;
                border: 1px solid {BORDER};
                border-radius: 8px;
            }}
        """)
        
        # Main Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)
        
        # Header / Title Label
        title_lbl = make_section_label("Refine Caption Content")
        layout.addWidget(title_lbl)
        
        # Styled Multi-line Text Field
        self.text_edit = QTextEdit()
        self.text_edit.setPlainText(initial_text)
        self.text_edit.setStyleSheet(f"""
            QTextEdit {{
                background-color: #FFFFFF;
                color: {TEXT_DARK};
                border: 1px solid {BORDER};
                border-radius: 6px;
                padding: 10px;
                font-size: 13px;
                line-height: 1.4;
            }}
            QTextEdit:focus {{
                border: 1px solid {ORANGE};
            }}
        """)
        layout.addWidget(self.text_edit)
        
        # Bottom Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.addStretch()
        
        # Cancel (Secondary style)
        self.cancel_btn = make_secondary_btn("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        # Save (Primary style)
        self.save_btn = make_primary_btn("Save Changes")
        self.save_btn.clicked.connect(self.accept)
        
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.save_btn)
        layout.addLayout(btn_layout)

    def get_text(self):
        return self.text_edit.toPlainText().strip()


# ── Custom Visually Consistent Export Choice Window ──
class ExportCaptionDialog(QDialog):
    """A highly polished choice modal that matches the Traybakes UI design language."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Export Option")
        self.setMinimumSize(420, 200)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: #FAFAFA;
                border: 1px solid {BORDER};
                border-radius: 8px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        
        # Header / Title
        title_lbl = make_section_label("Choose Export Action")
        layout.addWidget(title_lbl)
        
        # Friendly description
        desc_lbl = QLabel("How would you like to handle your finalized caption?")
        desc_lbl.setStyleSheet(f"color: {TEXT_DARK}; font-size: 13px; border: none;")
        desc_lbl.setWordWrap(True)
        layout.addWidget(desc_lbl)
        
        # Actions Layout
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        # Buttons styled to match rest of UI
        self.save_btn = make_primary_btn("Save as TXT")
        self.copy_btn = make_secondary_btn("Copy to Clipboard")
        self.cancel_btn = make_secondary_btn("Cancel")
        
        # Tie clicks to custom return results
        self.save_btn.clicked.connect(lambda: self.done(1))
        self.copy_btn.clicked.connect(lambda: self.done(2))
        self.cancel_btn.clicked.connect(lambda: self.done(0))
        
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.copy_btn)
        btn_layout.addWidget(self.save_btn)
        
        layout.addLayout(btn_layout)


class CreateContentPage(QWidget):
    # Emitted once a generation run completes successfully, carrying a dict
    # of {dashboard metric label: display value string} for DashboardPage.
    metrics_ready = Signal(dict)
    # Emitted alongside metrics_ready, carrying {"patterns": [...], "gaps":
    # [...], "opportunities": [...]} — the actual finding text, not just counts.
    research_findings_ready = Signal(dict)
    content_confirmed = Signal(str, str)
    AGENT_FRIENDLY_NAMES = {
        "research_agent": "market research",
        "image_generator": "image creation",
        "caption_generator": "caption writing",
        "knowledge_lookup": "checking past research",
        "planner": "planning",
        "dispatcher": "the generation process",
    }

    TONE_HINTS = {
        "None": "",
        "Professional": "Polished and business-like — good for trade buyers and formal announcements.",
        "Minimal": "Short and to the point — good for simple, clean captions.",
        "Warm": "Friendly and personal — like talking to a regular customer.",
    }
    def __init__(self, navigate_callback):
        super().__init__()
        self.navigate = navigate_callback
        self._worker = None
        self.last_state = None  # most recent AgentState returned by the orchestrator
        self.selected_caption = None
        self.last_goal = None   # Retain the last generated goal for regeneration
        self._gen_timer = QTimer(self)
        self._gen_timer.setInterval(1000)
        self._gen_timer.timeout.connect(self._tick_generating_timer)
        self._gen_seconds = 0
        self._gen_active_button = None
        self._gen_base_text = ""
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 20)
        root.setSpacing(0)

        title = QLabel("Create Marketing Content")
        title.setObjectName("pageTitle")
        root.addWidget(title)
        root.addSpacing(4)

        subtitle = QLabel("Describe what you need and the AI will generate on-brand copy instantly.")
        subtitle.setObjectName("pageSubtitle")
        root.addWidget(subtitle)
        root.addSpacing(16)
        root.addWidget(make_divider())
        root.addSpacing(18)

        # Two-column body for settings & image preview
        columns = QHBoxLayout()
        columns.setSpacing(24)

        # ── Left: settings ──
        left = QVBoxLayout()
        left.setSpacing(14)
        left.setContentsMargins(0, 0, 0, 0)

        left.addWidget(make_section_label("Content settings"))

        # Content type
        left.addWidget(QLabel("Content type"))
        self.content_type_combo = QComboBox()
        self.content_type_combo.addItems([
            "None", "Instagram Post", "Facebook Post", "Poster", "Banner"
            ,"A4 Portrait", "A4 Landscape", "A5 Portrait", "A5 Landscape"
        ])
        left.addWidget(self.content_type_combo)

        #Choose Products
        left.addWidget(QLabel("Choose Products"))
        self.product_select = ProductMultiSelect()
        left.addWidget(self.product_select)

        #Choose Product Type
        left.addWidget(QLabel("Choose Product Types"))
        self.product_type_combo = QComboBox()
        self.product_type_combo.addItems(["None", "Single Slice", "Sharing Slice", "Service Tray"])
        left.addWidget(self.product_type_combo)

        #Tone
        left.addWidget(QLabel("Tone"))
        self.tone_combo = QComboBox()
        self.tone_combo.addItems(["None", "Professional", "Minimal", "Warm"])
        self.tone_combo.currentTextChanged.connect(self._update_tone_hint)
        left.addWidget(self.tone_combo)

        self.tone_hint_label = QLabel("")
        self.tone_hint_label.setWordWrap(True)
        self.tone_hint_label.setStyleSheet(f"color: {BROWN_LIGHT}; font-size: 11px;")
        left.addWidget(self.tone_hint_label)
        self._update_tone_hint(self.tone_combo.currentText())

        # Description
        left.addWidget(QLabel("What would you like to create?"))
        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText(
            "e.g. Generate instagram campaign for our flapjack product"
        )
        self.desc_input.setFixedHeight(70)
        left.addWidget(self.desc_input)


        # Reference image upload
        left.addWidget(QLabel("Reference image"))
        self.image_path = None

        self.upload_btn = make_secondary_btn("📎   Upload Reference Image")
        self.upload_btn.clicked.connect(self._on_upload_clicked)
        left.addWidget(self.upload_btn)

        self.image_chip = QFrame()
        self.image_chip.setObjectName("card")
        chip_layout = QHBoxLayout(self.image_chip)
        chip_layout.setContentsMargins(12, 8, 8, 8)
        chip_layout.setSpacing(8)

        self.image_chip_label = QLabel("")
        self.image_chip_label.setWordWrap(True)
        self.image_chip_label.setStyleSheet(f"color: {TEXT_DARK}; font-size: 12px; border: none;")

        remove_btn = QPushButton("✕")
        remove_btn.setFixedSize(22, 22)
        remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        remove_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {BROWN_LIGHT};
                border: 1px solid {BORDER};
                border-radius: 11px;
                font-size: 11px;
                font-weight: 700;
                padding: 0px;
            }}
            QPushButton:hover {{
                background-color: #FBE7E0;
                color: {ORANGE_DARK};
                border-color: {ORANGE};
            }}
        """)
        remove_btn.clicked.connect(self._on_remove_image)

        chip_layout.addWidget(self.image_chip_label, 1)
        chip_layout.addWidget(remove_btn)
        self.image_chip.setVisible(False)
        left.addWidget(self.image_chip)
        left.addSpacing(4)  # Small visual cushion before the primary button

        self.generate_btn = make_primary_btn("✦   Generate Content", full_width=True)
        self.generate_btn.clicked.connect(self._on_generate_clicked)
        left.addWidget(self.generate_btn)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        self.status_label.setVisible(False)
        left.addWidget(self.status_label)

        if not BACKEND_AVAILABLE:
            self._show_status(
                f"Backend not found ({BACKEND_IMPORT_ERROR}). "
                f"UI will run, but Generate won't produce real output.",
                error=True,
            )

        left.addStretch()

        # ── Right: output ──
        right = QVBoxLayout()
        right.setSpacing(14)
        right.setContentsMargins(0, 0, 0, 0)

        right.addWidget(make_section_label("Generated output"))
        self.output_preview = OutputPreview(height=320)
        right.addWidget(self.output_preview)

        right.addWidget(make_divider())

        right.addWidget(make_section_label("Refine generated image"))
        self.tweak_input = QLineEdit()
        self.tweak_input.setPlaceholderText(
            "e.g. Increase brightness, remove object..."
        )
        right.addWidget(self.tweak_input)
        self.apply_tweak_btn = make_secondary_btn("Apply tweak")
        right.addWidget(self.apply_tweak_btn)

        self.apply_tweak_btn.clicked.connect(self.start_image_tweak)
        right.addStretch()

        # Wrap top half in fixed-ratio columns
        left_w = QWidget()
        left_w.setLayout(left)
        right_w = QWidget()
        right_w.setLayout(right)
        columns.addWidget(left_w, 1)
        columns.addWidget(right_w, 1)

        root.addLayout(columns)

        # ── Bottom Section: Captions spanning all across the bottom ──
        root.addSpacing(16)
        root.addWidget(make_divider())
        root.addSpacing(12)

        bottom_section = QVBoxLayout()
        bottom_section.setSpacing(12)

        # Header for bottom section
        bottom_header = QHBoxLayout()
        bottom_header.addWidget(make_section_label("Choose and Refine a Base Caption"))
        bottom_header.addStretch()
        bottom_section.addLayout(bottom_header)

        # Horizontal container layout to hold captions side-by-side
        captions_layout = QHBoxLayout()
        captions_layout.setSpacing(16)

        caption_placeholders = [
            "Generated caption 1 will appear here once you create content...",
            "Generated caption 2 will appear here once you create content...",
            "Generated caption 3 will appear here once you create content...",
        ]

        self.caption_cards = []

        for i, placeholder_text in enumerate(caption_placeholders):
            card = CaptionCard(
                i,
                placeholder_text,
                caption_id=None
            )
            card.clicked.connect(self._on_caption_selected)
            card.rating_changed.connect(self.handle_caption_rating)
            
            # Fix Background Issue: Make inner components transparent so card color handles backgrounds
            card.setStyleSheet(f"""
                CaptionCard {{
                    background-color: #FFFFFF;
                    border: 1px solid {BORDER};
                    border-radius: 8px;
                }}
                CaptionCard:hover {{
                    border-color: {ORANGE};
                }}
            """)
            if hasattr(card, "text_label") and card.text_label:
                # Force the actual text display label to inherit/be transparent
                card.text_label.setStyleSheet("background-color: transparent; border: none;")
            
            # Add to horizontal layout
            captions_layout.addWidget(card, 1)
            self.caption_cards.append(card)

        bottom_section.addLayout(captions_layout)

        # ── Caption Actions Bar (Regenerate, Edit, Confirm) ──
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(12)
        actions_layout.addStretch()

        self.regenerate_caption_btn = make_secondary_btn("🔄   Try Different Caption")
        self.edit_caption_btn = make_secondary_btn("✏️   Edit Caption")
        self.confirm_btn = make_primary_btn("✓   Confirm Content")

        self.regenerate_caption_btn.clicked.connect(self._on_regenerate_caption_clicked)
        self.edit_caption_btn.clicked.connect(self._on_edit_caption_clicked)
        self.confirm_btn.clicked.connect(self._on_confirm_clicked)

        actions_layout.addWidget(self.regenerate_caption_btn)
        actions_layout.addWidget(self.edit_caption_btn)
        actions_layout.addWidget(self.confirm_btn)

        bottom_section.addLayout(actions_layout)
        
        # Add the constructed bottom section container directly to the layout
        bottom_container = QWidget()
        bottom_container.setLayout(bottom_section)
        root.addWidget(bottom_container)

    def _on_upload_clicked(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select reference image",
            "",
            "Images (*.png *.jpg *.jpeg)",
        )
        if file_path:
            self.image_path = file_path
            filename = os.path.basename(file_path)
            self.image_chip_label.setText(f"📎   Uploaded {filename}")
            self.upload_btn.setVisible(False)
            self.image_chip.setVisible(True)

    def _on_remove_image(self):
        self.image_path = None
        self.image_chip_label.setText("")
        self.image_chip.setVisible(False)
        self.upload_btn.setVisible(True)

    def _update_tone_hint(self, tone_text: str):
        self.tone_hint_label.setText(self.TONE_HINTS.get(tone_text, ""))

    def _friendly_agent_name(self, agent: str) -> str:
        agent = (agent or "").split(".")[0]
        return self.AGENT_FRIENDLY_NAMES.get(agent, "part of the generation")

    def _start_generating_timer(self, button: QPushButton, base_text: str):
        self._gen_seconds = 0
        self._gen_active_button = button
        self._gen_base_text = base_text
        button.setText(f"{base_text} 0s")
        self._gen_timer.start()

    def _tick_generating_timer(self):
        self._gen_seconds += 1
        if self._gen_active_button is not None:
            self._gen_active_button.setText(
                f"{self._gen_base_text} {self._gen_seconds}s"
            )

    def _stop_generating_timer(self):
        self._gen_timer.stop()
        self._gen_active_button = None

    def _on_regenerate_finished_ui_reset(self, *args):
        """Connected to both finished_ok and finished_error for the
        regenerate flow — resets the button/timer regardless of outcome."""
        self._stop_generating_timer()
        self.regenerate_caption_btn.setText("🔄   Try Different Captions")
        self.regenerate_caption_btn.setEnabled(True)

    def _on_caption_selected(self, selected_card):
        """Ensure only the clicked caption card is marked as selected."""
        for card in self.caption_cards:
            card.set_selected(card is selected_card)

        self.selected_caption = selected_card.text_label.text()

        if self.last_state and self.last_state.campaign_id:
            record_selection(
                _campaign_db,
                self.last_state.campaign_id,
                self.selected_caption
            )

    # ── Caption Action Slots ──
    def _on_regenerate_caption_clicked(self):
        """
        Generate captions if none exist yet.
        Otherwise regenerate captions using the previous goal.
        """

        if not BACKEND_AVAILABLE:
            self._show_status("Backend not found. Cannot generate captions.", error=True)
            return

        if self._worker is not None and self._worker.isRunning():
            return

        # Use previous goal if available, otherwise create one
        goal = self.last_goal

        if not goal:
            description = self.desc_input.toPlainText().strip()
            if not description:
                # No blocking error — fall back to a sensible default so
                # a user who hasn't typed anything can still generate.
                description = "Generate promotional content for Traybakes."

            goal = self._build_goal_string(description)
            self.last_goal = goal

        content_type = self.content_type_combo.currentText().strip()
        tone = self.tone_combo.currentText().strip()

        # Lock button + start elapsed-time feedback
        self.regenerate_caption_btn.setEnabled(False)
        self._start_generating_timer(self.regenerate_caption_btn, "Generating…")

        self._show_status(
            "Generating new caption options...",
            error=False
        )

        # Reset caption cards
        for card in self.caption_cards:
            card.set_text("Generating…")
            card.set_selected(False)

        self.selected_caption = None

        # Run generation pipeline
        self._worker = OrchestratorWorker(
            goal,
            content_type=content_type,
            tone=tone,
            style_reference_path=self.image_path,
        )

        self._worker.finished_ok.connect(self._on_generation_success)
        self._worker.finished_ok.connect(self._on_regenerate_finished_ui_reset)

        self._worker.finished_error.connect(self._on_generation_error)
        self._worker.finished_error.connect(self._on_regenerate_finished_ui_reset)

        self._worker.start()

    def _on_edit_caption_clicked(self):
        # Find which card is currently selected
        selected_card = None
        for card in self.caption_cards:
            if card.is_selected():
                selected_card = card
                break

        if not selected_card:
            self._show_status("Warning: Please click on a caption card to select it first before editing.", error=True)
            return

        current_text = selected_card.text_label.text()

        # Initialize custom gorgeous dialog!
        dialog = EditCaptionDialog(current_text, self)
        if dialog.exec() == QDialog.Accepted:
            modified_text = dialog.get_text()
            if modified_text and modified_text != current_text:
                # 1. Update the UI card itself
                selected_card.set_text(modified_text)
                # 2. Update the tracking variable
                self.selected_caption = modified_text

                # 3. Synchronize with the DB if campaign state exists
                if self.last_state and self.last_state.campaign_id:
                    record_selection(
                        _campaign_db,
                        self.last_state.campaign_id,
                        modified_text
                    )
                    # 4. Capture the edit itself as a targeted feedback
                    # signal — which specific phrases were changed — so
                    # future generations can learn from it, rather than
                    # only recording the final selected text.
                    if selected_card.caption_id:
                        record_caption_edit(
                            _campaign_db,
                            self.last_state.campaign_id,
                            selected_card.caption_id,
                            current_text,
                            modified_text,
                        )
                self._show_status("Caption updated successfully.", error=False)

    def _on_confirm_clicked(self):

        if not self.last_state:
            self._show_status("Warning: Please generate your content before confirming.", error=True)
            return

        # 1. Capture selected caption
        chosen_caption = self.get_selected_caption()

        if not chosen_caption:
            self._show_status("Warning: Please click on a caption card to select it before confirming.", error=True)
            return

        # 2. Capture selected/generated image
        generated_images = getattr(
            self.last_state,
            "images",
            None
        ) or {}

        image_path = None
        if isinstance(generated_images, dict):
            image_path = generated_images.get(
                "generated_output_path"
            )

        # 3. Ask user how they want the caption exported via beautiful custom dialogue
        dialog = ExportCaptionDialog(self)
        choice = dialog.exec()

        if choice == 1:  # Save as TXT
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Caption",
                "caption.txt",
                "Text Files (*.txt)"
            )

            if not file_path:
                return

            if not file_path.endswith(".txt"):
                file_path += ".txt"

            with open(
                file_path,
                "w",
                encoding="utf-8"
            ) as file:
                file.write(chosen_caption)

            self._show_status("Caption successfully saved to file.", error=False)

        elif choice == 2:  # Copy to Clipboard
            clipboard = QApplication.clipboard()
            clipboard.setText(chosen_caption)
            self._show_status("Caption copied to clipboard!", error=False)

        elif choice == 0:  # Cancel
            return

        # 4. Handle data retention logic
        if BACKEND_AVAILABLE and self.last_state.campaign_id:
            record_selection(
                _campaign_db,
                self.last_state.campaign_id,
                chosen_caption
            )
            self._show_status(
                "Campaign content successfully confirmed and recorded.",
                error=False
            )
        else:
            print(
                f"""
                Content confirmed!

                Caption:
                {chosen_caption}

                Image:
                {image_path or 'No generated image found'}
                """
            )

        # 5. Move to editor page
        proceed = QMessageBox.question(
            self,
            "Content Saved",
            "Your content has been saved. Continue to the Editor to add "
            "text, resize, or export the image?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if proceed == QMessageBox.Yes:
            self.navigate("Editor")

    def set_caption_options(self, captions: list[str]):
        """Populate the three caption cards with generated text (called once
        the backend returns results) and clear any previous selection."""
        for card, caption_data in zip(self.caption_cards, captions):
            if isinstance(caption_data, dict):
                text = caption_data.get("caption", "")
                card.caption_id = caption_data.get("id")
            else:
                text = str(caption_data)
                card.caption_id = None
            card.set_text(text)
            card.set_rating(None)
            card.set_selected(False)
        self.selected_caption = None

    def get_selected_caption(self) -> str | None:
        for card in self.caption_cards:
            if card.is_selected():
                return card.text_label.text()
        return None

    def update_caption_cards(self, captions):
        """
        Updates placeholder CaptionCards with generated captions.
        """
        for i, caption_data in enumerate(captions):
            if i >= len(self.caption_cards):
                break
            card = self.caption_cards[i]
            card.caption_id = caption_data.get("id")
            card.set_text(caption_data.get("caption", ""))

    def handle_caption_rating(self, card, rating):
        if not self.last_state:
            return
        if not self.last_state.campaign_id:
            return
        if not card.caption_id:
            return
        record_caption_rating(
            _campaign_db,
            self.last_state.campaign_id,
            card.caption_id,
            card.text_label.text(),
            rating
        )

    def set_output_image(self, source):
        """Called once the backend/img_gen pipeline returns a real image
        asset. `source` can be a file path (str) or a QPixmap."""
        self.output_preview.set_image(source)

    def clear_output_image(self):
        self.output_preview.clear()

    # ── Backend integration ──

    def _build_goal_string(self, description: str) -> str:
            """Folds the content-type and tone selections into a single goal
            string, since run_orchestrator() takes one goal string."""
            parts = [description.strip()]
            
            content_type = self.content_type_combo.currentText()
            if content_type and content_type != "None":
                parts.append(f"Format: {content_type}.")
                
            products = self.product_select.selected_labels()
            if products:
                if len(products) == 1:
                    parts.append(f"Products to feature: {products[0]}.")
                else:
                    parts.append(f"Products to feature: {', '.join(products)}")
            
            # Add Product Type to the goal string if one is selected
            product_type = self.product_type_combo.currentText()
            if product_type and product_type != "None":
                parts.append(f"Product type: {product_type}.")
            
            return " ".join(p for p in parts if p)

    def _on_generate_clicked(self):
            if not BACKEND_AVAILABLE:
                self._show_status(
                    f"Backend not found ({BACKEND_IMPORT_ERROR}). Check the project folder layout.",
                    error=True,
                )
                return

            if self._worker is not None and self._worker.isRunning():
                return  # a generation is already in flight

            description = self.desc_input.toPlainText().strip()
            if not description:
                # No blocking error — fall back to a sensible default so a
                # user who only picked buttons (no free text) can still
                # generate content.
                description = "Generate promotional content for Traybakes."

            goal = self._build_goal_string(description)
            self.last_goal = goal
            content_type = self.content_type_combo.currentText().strip()
            tone = self.tone_combo.currentText().strip()

            # Lock the UI into a "working" state
            self.generate_btn.setEnabled(False)
            self._start_generating_timer(self.generate_btn, "Generating…")
            self._show_status("Running research → captions → image prompt…", error=False)
            self.output_preview.set_generating()
            for card in self.caption_cards:
                card.set_text("Generating…")
                card.set_selected(False)

            self._worker = OrchestratorWorker(
                goal,
                content_type=content_type,
                tone=tone,
                style_reference_path=self.image_path,
            )
            self._worker.finished_ok.connect(self._on_generation_success)
            self._worker.finished_error.connect(self._on_generation_error)
            self._worker.start()
        
    def _on_generation_success(self, state):
        self.last_state = state
        self.state = state
        self._stop_generating_timer()
        self.generate_btn.setEnabled(True)
        self.generate_btn.setText("Generate Content")

        # ── Captions: state.captions is a list of {"opportunity", "caption"} ──
        captions = getattr(state, "captions", None) or []

        while len(captions) < 3:
            captions.append("No caption was generated for this slot.")
        self.set_caption_options(captions[:3])

        # ── Image: img_gen currently only returns a prompt, not an asset ──
        images = getattr(state, "images", None) or {}

        generated_path = None
        prompt_text = None

        if isinstance(images, dict):
            generated_path = images.get("generated_output_path")
            prompt_text = images.get("refined_prompt") or images.get("raw_prompt")

        if generated_path:
            self.output_preview.set_image(generated_path)
        elif prompt_text:
            self.output_preview.set_prompt_preview(prompt_text)
        else:
            self.output_preview.clear()

        # ── Metrics: state.metrics is populated by orchestrator.py/dispatcher.py ──
        # ── Metrics: persist cumulative metrics ──
        metrics = getattr(state, "metrics", None) or {}
        sub_times = metrics.get("subsystem_times_sec", {}) or {}


        def get_sub_time(*keys):
            for key in keys:
                if key in sub_times:
                    return sub_times[key]
            return 0.0

        metric_event = {
            "planner_time": metrics.get(
                "planner_time_sec",
                0.0
            ),

            "research_time": get_sub_time(
                "research_agent",
                "research",
            ),

            "image_time": get_sub_time(
                "img_gen",
                "image_generator",
            ),

            "caption_time": get_sub_time(
                "caption_generation",
                "caption_generator",
            ),

            "end_to_end": metrics.get(
                "total_time_sec",
                0.0
            ),

            "cost": metrics.get(
                "total_cost",
                metrics.get(
                    "avg_cost_per_request",
                    0.0
                )
            ),

        }
        
        self.metrics_ready.emit(metric_event)
        insights = (getattr(state, "research", None) or {}).get("insights", {})
        research_event = {
            "patterns": [self._format_finding(p, "patterns")
                         for p in insights.get("patterns",[])],
            "gaps": [self._format_finding(g, "gaps")
                         for g in insights.get("gaps",[])],
            "opportunities": [self._format_finding(o, "opportunities")
                         for o in insights.get("opportunities",[])]
        }
        if research_event["patterns"] or research_event["gaps"] or research_event["opportunities"]:
            self.research_findings_ready.emit(research_event)

        # ── Surface any subsystem errors without blocking what succeeded ──
        errors = getattr(state, "errors", None) or []
        if errors:
            affected = sorted({
                self._friendly_agent_name(e.get("agent", "")) for e in errors
            })
            affected_text = ", ".join(affected)
            self._show_status(
                f"Your content was created, but we had trouble with "
                f"{affected_text}. You can still use what was generated, "
                f"or try again.",
                error=True
            )
        else:
            self._show_status("Content generated.", error=False)

    @staticmethod
    def _format_finding(item, kind: str) -> str:
        if isinstance(item, str):
            return item.strip()
        if not isinstance(item, dict):
            return str(item)

        name = item.get("name") or item.get("title")
        detail = item.get("description") or item.get("reason")

        if kind == "opportunities":
            headline = name or detail or "Opportunity"
            metric_bits = []
            for key in ("impact", "competition", "effort", "confidence"):
                val = item.get(key)
                if val is not None:
                    metric_bits.append(f"{key} {val}")
            score = item.get("score")
            if score is not None:
                try:
                    metric_bits.append(f"score {float(score):.2f}")
                except (TypeError, ValueError):
                    metric_bits.append(f"score {score}")

            pieces = [str(headline)]
            if detail and detail != headline:
                pieces.append(str(detail))
            text = " — ".join(pieces)
            if metric_bits:
                text = f"{text}   ({', '.join(metric_bits)})"
            return text if text.strip() else str(item)

        pieces = []
        if name:
            pieces.append(str(name))
        if detail and str(name or "").strip().lower() not in str(detail).strip().lower():
            pieces.append(str(detail))
        elif detail and not name:
            pieces.append(str(detail))
        text = " — ".join(pieces) if pieces else None
        return text if text else str(item)

    def _on_generation_error(self, message: str):
        self._stop_generating_timer()
        self.generate_btn.setEnabled(True)
        self.generate_btn.setText("Generate Content")
        self.output_preview.clear()
        self._show_status(f"Generation failed: {message}", error=True)

    def _show_status(self, text: str, error: bool = False):
        color = "#B3261E" if error else GREEN_TEXT
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"color: {color}; font-size: 12px; border: none;")
        self.status_label.setVisible(True)

    def start_image_tweak(self):
        prompt = self.tweak_input.text().strip()
        
        if not prompt:
            return
        if self.last_state is None:
            return

        self.output_preview.set_generating()
        self.apply_tweak_btn.setEnabled(False)

        self.tweak_thread = QThread()
        self.tweak_worker = ImageTweakWorker(self.last_state, prompt)
        self.tweak_worker.moveToThread(self.tweak_thread)
        self.tweak_thread.started.connect(self.tweak_worker.run)
        self.tweak_worker.finished.connect(self.tweak_finished)
        self.tweak_worker.error.connect(self.tweak_failed)
        self.tweak_thread.start()

    def tweak_finished(self, state):
        self.last_state = state
        self.state = state
        image_path = self.state.images.get("generated_output_path")

        if image_path:
            self.output_preview.set_image(image_path)

        self.tweak_input.clear()
        self.apply_tweak_btn.setEnabled(True)

        if hasattr(self, "tweak_thread") and self.tweak_thread:
            self.tweak_thread.quit()
            self.tweak_thread.wait()
            self.tweak_thread = None

    def tweak_failed(self, error):
        self.apply_tweak_btn.setEnabled(True)
        if hasattr(self, "tweak_thread") and self.tweak_thread:
            self.tweak_thread.quit()
            self.tweak_thread.wait()
            self.tweak_thread = None
            self.tweak_worker = None