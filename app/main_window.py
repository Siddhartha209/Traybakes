"""
Traybakes · AI Marketing Assistant
MainWindow — the application shell: sidebar + stacked pages. To add a new
page, build the page widget, add it to self.pages with a name matching a
Sidebar.PAGES entry, and add it to self.stack.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QStackedWidget, QScrollArea

from app.styles import CREAM
from app.widgets.sidebar import Sidebar
from app.pages.dashboard_page import DashboardPage
from app.pages.create_content_page import CreateContentPage
from app.pages.editor_page import EditorPage


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Traybakes · AI Marketing")
        self.setMinimumSize(1100, 720)
        self.resize(1280, 800)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sidebar
        self.sidebar = Sidebar(self._navigate)
        main_layout.addWidget(self.sidebar)

        self.stack = QStackedWidget()

        self.dashboard_page = DashboardPage()
        self.create_content_page = CreateContentPage(self._navigate)
        self.editor_page = EditorPage()

        self.create_content_page.metrics_ready.connect(self._handle_metrics)
        self.create_content_page.research_findings_ready.connect(self._handle_research)

        self.pages = {
            "Dashboard":      self._scrolled(self.dashboard_page),
            "Create Content": self._scrolled(self.create_content_page),
            "Editor": self.editor_page,
        }
        for w in self.pages.values():
            self.stack.addWidget(w)

        main_layout.addWidget(self.stack, 1)

        self._navigate(Sidebar.DEFAULT_PAGE)

    def _scrolled(self, page: QWidget) -> QScrollArea:
        sa = QScrollArea()
        sa.setWidgetResizable(True)
        sa.setWidget(page)
        sa.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        sa.setStyleSheet(f"QScrollArea {{ border: none; background: {CREAM}; }}")
        return sa

    def _navigate(self, name: str):
        if name in self.pages:
            self.stack.setCurrentWidget(self.pages[name])
            self.sidebar._set_active(name)

    def _handle_metrics(self, event):

        self.dashboard_page.metrics_store.record_latency(
            planner_time=event["planner_time"],
            research_time=event["research_time"],
            image_time=event["image_time"],
            caption_time=event["caption_time"],
            end_to_end=event["end_to_end"],
        )
        self.dashboard_page.refresh_metrics()
    
    def _handle_research(self, findings):

        self.dashboard_page.metrics_store.update_research(
            patterns=findings.get("patterns", []),
            gaps=findings.get("gaps", []),
            opportunities=findings.get("opportunities", []),
        )

        self.dashboard_page.refresh_metrics()