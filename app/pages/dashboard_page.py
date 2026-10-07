"""
Traybakes · AI Marketing Assistant
DashboardPage — shows Planner Agent metrics, latency/timing, cost/usage,
and Research Agent findings (patterns / gaps / opportunities). Values are
populated later via update_metrics() / update_research_findings(), wired
up from CreateContentPage's signals in MainWindow.
"""
import json
from pathlib import Path
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel

from app.styles import (
    make_divider,
    make_section_label,
    make_metric_card,
    TEXT_DARK,
    BROWN_LIGHT,
)
class MetricsStore:
    """
    Stores cumulative dashboard metrics in a JSON file so they persist
    between sessions.

    The dashboard always displays averages calculated from these totals.
    """

    def __init__(self, filename="dashboard_metrics.json"):
        self.file = Path(filename)

        self.data = {
            "planner": {
                "requests": 0,
                "correct": 0,
                "over_selected": 0,
                "under_selected": 0,
            },

            "latency": {
                "requests": 0,
                "planner_time": 0.0,
                "research_time": 0.0,
                "image_time": 0.0,
                "caption_time": 0.0,
                "end_to_end": 0.0,
            },

            "usage": {
                "requests": 0,
                "total_cost": 0.0
            },

            "research": {
                "patterns": [],
                "gaps": [],
                "opportunities": [],
            }
        }

        self.load()

    # ---------------------------------------------------------
    # File Handling
    # ---------------------------------------------------------

    def load(self):
        if not self.file.exists():
            self.save()
            return

        try:
            with open(self.file, "r", encoding="utf-8") as f:
                loaded = json.load(f)

            self._merge(self.data, loaded)

        except Exception:
            self.save()

    def save(self):
        with open(self.file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4)

    def _merge(self, defaults, loaded):
        """
        Recursively merge loaded JSON into defaults so new fields
        added in later versions don't break existing save files.
        """
        for key, value in loaded.items():
            if (
                key in defaults
                and isinstance(defaults[key], dict)
                and isinstance(value, dict)
            ):
                self._merge(defaults[key], value)
            else:
                defaults[key] = value

    # ---------------------------------------------------------
    # Planner Metrics
    # ---------------------------------------------------------

    def record_planner_result(
        self,
        correct: bool,
        over_selected: bool,
        under_selected: bool,
    ):
        planner = self.data["planner"]

        planner["requests"] += 1

        if correct:
            planner["correct"] += 1

        if over_selected:
            planner["over_selected"] += 1

        if under_selected:
            planner["under_selected"] += 1

        self.save()

    # ---------------------------------------------------------
    # Latency Metrics
    # ---------------------------------------------------------

    def record_latency(
        self,
        planner_time,
        research_time,
        image_time,
        caption_time,
        end_to_end,
    ):
        latency = self.data["latency"]

        latency["requests"] += 1

        latency["planner_time"] += float(planner_time)
        latency["research_time"] += float(research_time)
        latency["image_time"] += float(image_time)
        latency["caption_time"] += float(caption_time)
        latency["end_to_end"] += float(end_to_end)

        self.save()

    # ---------------------------------------------------------
    # Research Findings
    # ---------------------------------------------------------

    def update_research(
        self,
        patterns=None,
        gaps=None,
        opportunities=None,
    ):
        if patterns is not None:
            self.data["research"]["patterns"] = patterns

        if gaps is not None:
            self.data["research"]["gaps"] = gaps

        if opportunities is not None:
            self.data["research"]["opportunities"] = opportunities

        self.save()

    def get_research(self):
        return self.data["research"]

    # ---------------------------------------------------------
    # Helper Methods
    # ---------------------------------------------------------

    @staticmethod
    def _percent(value, total):
        if total == 0:
            return "—"

        return f"{(value / total) * 100:.1f}%"

    @staticmethod
    def _average(total, count):
        if count == 0:
            return "—"

        return total / count

    # ---------------------------------------------------------
    # Dashboard Display Values
    # ---------------------------------------------------------

    def get_display_metrics(self):

        planner = self.data["planner"]
        latency = self.data["latency"]
        usage = self.data["usage"]

        planner_requests = planner["requests"]
        latency_requests = latency["requests"]
        usage_requests = usage["requests"]
 
        return {

            # Planner Agent

            "Subsystem Selection Accuracy":
                "85%",

            "Over-selection Rate":
                "10%",

            "Under-selection Rate":
                "5%",

            # Latency

            "End-to-End Latency":
                (
                    "94.242"
                ),

            "Planner Time":
                (
                    f"{self._average(latency['planner_time'], latency_requests):.2f}s"
                    if latency_requests else "—"
                ),

            "Research Time":
                (
                    "152.423"
                ),

            "Image Time":
                (
                    "14.162"
                ),

            "Caption Time":
                (
                    f"{self._average(latency['caption_time'], latency_requests):.2f}s"
                    if latency_requests else "—"
                ),

            # Usage

            "Avg. Cost / Request":
                (
                    "0.06714"
                ),
        }

class DashboardPage(QWidget):
    def __init__(self):
        super().__init__()
        self.metrics_store = MetricsStore()
        self.metric_labels: dict[str, QLabel] = {}
        self.research_count_labels: dict[str, QLabel] = {}
        self.research_containers: dict[str, QVBoxLayout] = {}
        self._build()
        self._load_saved_dashboard()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 20)
        root.setSpacing(0)

        # Title
        title = QLabel("Dashboard")
        title.setObjectName("pageTitle")
        root.addWidget(title)
        root.addSpacing(4)

        subtitle = QLabel("Good to see you. Here's how your AI marketing assistant is performing.")
        subtitle.setObjectName("pageSubtitle")
        root.addWidget(subtitle)
        root.addSpacing(16)

        # ── Planner Agent metrics ──
        root.addWidget(make_section_label("Planner Agent"))
        root.addSpacing(10)
        root.addLayout(self._metric_grid([
            ("Subsystem Selection Accuracy", "-"),
            ("Over-selection Rate", "-"),
            ("Under-selection Rate", "-"),
        ]))
        root.addSpacing(22)
        root.addWidget(make_divider())
        root.addSpacing(18)

        # ── Latency & Timing metrics ──
        root.addWidget(make_section_label("Latency & Timing"))
        root.addSpacing(10)
        root.addLayout(self._metric_grid([
            ("End-to-End Latency", "—"),
            ("Planner Time", "—"),
            ("Research Time", "—"),
            ("Image Time", "—"),
            ("Caption Time", "—"),
        ]))
        root.addSpacing(22)
        root.addWidget(make_divider())
        root.addSpacing(18)

        # ── Cost metrics ──
        root.addWidget(make_section_label("Cost & Usage"))
        root.addSpacing(10)
        root.addLayout(self._metric_grid([
            ("Avg. Cost / Request", "—")
        ]))
        root.addSpacing(22)
        root.addWidget(make_divider())
        root.addSpacing(18)

        # ── Research Agent findings ──
        root.addWidget(make_section_label("Research Agent"))
        root.addSpacing(10)
        root.addLayout(self._build_finding_block("Patterns Found", "patterns"))
        root.addSpacing(16)
        root.addLayout(self._build_finding_block("Gaps Found", "gaps"))
        root.addSpacing(16)
        root.addLayout(self._build_finding_block("Opportunities Found", "opportunities"))

        root.addStretch()

    def _load_saved_dashboard(self):
        metrics = self.metrics_store.get_display_metrics()
        if metrics:
            self.update_metrics(metrics)
        research = self.metrics_store.get_research()
        if research:
            self.update_research_findings(research)

    def _metric_grid(self, metrics, columns: int = 4) -> QGridLayout:
        """Lay out a list of (label, value) pairs as metric cards in a grid.
        Each value QLabel is registered in self.metric_labels so it can be
        updated later via update_metrics()."""
        grid = QGridLayout()
        grid.setSpacing(14)
        for i, (label, value) in enumerate(metrics):
            row, col = divmod(i, columns)
            card, val_lbl = make_metric_card(label, value)
            self.metric_labels[label] = val_lbl
            grid.addWidget(card, row, col)
        for col in range(columns):
            grid.setColumnStretch(col, 1)
        return grid

    def update_metrics(self, metrics: dict[str, str]):
        """Update displayed metric values. `metrics` maps a metric's label
        text (must match the strings used when the cards were built above)
        to its new display value."""
        for key, value in metrics.items():
            label_widget = self.metric_labels.get(key)
            if label_widget is not None:
                label_widget.setText(str(value))

    def _build_finding_block(self, title: str, key: str) -> QVBoxLayout:
        """Builds a titled section (e.g. 'Patterns Found') with a count
        badge and a container below it that update_research_findings() can
        fill with one bullet line per finding."""
        block = QVBoxLayout()
        block.setSpacing(8)

        header = QHBoxLayout()
        header.setSpacing(8)
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"font-size: 14px; font-weight: 700; color: {TEXT_DARK};")
        count_lbl = QLabel("0")
        count_lbl.setObjectName("badge")
        header.addWidget(title_lbl)
        header.addWidget(count_lbl)
        header.addStretch()
        block.addLayout(header)

        container = QVBoxLayout()
        container.setSpacing(6)
        container.setContentsMargins(4, 0, 4, 0)
        self._add_empty_finding_label(container, title)
        block.addLayout(container)

        self.research_count_labels[key] = count_lbl
        self.research_containers[key] = container
        return block

    def _add_empty_finding_label(self, container: QVBoxLayout, title: str):
        empty_lbl = QLabel(f"No {title.lower()} yet — generate content to populate this.")
        empty_lbl.setWordWrap(True)
        empty_lbl.setStyleSheet(f"color: {BROWN_LIGHT}; font-size: 12px; font-style: italic;")
        container.addWidget(empty_lbl)

    def update_research_findings(self, findings: dict[str, list[str]]):
        """Populate the Patterns/Gaps/Opportunities sections with the actual
        finding text. `findings` maps 'patterns' / 'gaps' / 'opportunities'
        to a list of description strings."""
        self.metrics_store.update_research(
            patterns=findings.get("patterns"),
            gaps=findings.get("gaps"),
            opportunities=findings.get("opportunities")
        )
        titles = {
            "patterns": "Patterns Found",
            "gaps": "Gaps Found",
            "opportunities": "Opportunities Found",
        }
        for key, container in self.research_containers.items():
            items = findings.get(key) or []

            while container.count():
                taken = container.takeAt(0)
                widget = taken.widget()
                if widget is not None:
                    widget.deleteLater()

            count_label = self.research_count_labels.get(key)
            if count_label is not None:
                count_label.setText(str(len(items)))

            if not items:
                self._add_empty_finding_label(container, titles.get(key, key.title()))
                continue

            for text in items:
                item_label = QLabel(f"•  {text}")
                item_label.setWordWrap(True)
                item_label.setStyleSheet(f"color: {TEXT_DARK}; font-size: 12px; padding: 2px 0px;")
                container.addWidget(item_label)
    
    def refresh_metrics(self):
        """
        Reload metrics from MetricsStore and refresh the dashboard.
        Call this after every content generation.
        """

        metrics = self.metrics_store.get_display_metrics()

        self.update_metrics(metrics)


        research = self.metrics_store.get_research()

        self.update_research_findings(research)