"""
Traybakes · AI Marketing Assistant
OrchestratorWorker — runs run_orchestrator(goal) off the UI thread. The
orchestrator makes live Groq/Tavily calls across several agents, so
calling it directly from a button handler would freeze the window until
it returns.
"""

from PySide6.QtCore import QThread, Signal

from app.backend import run_orchestrator


class OrchestratorWorker(QThread):
    """Runs run_orchestrator(goal) off the UI thread. The orchestrator makes
    live Groq/Tavily calls across several agents, so calling it directly
    from a button handler would freeze the window until it returns."""

    finished_ok = Signal(object)   
    finished_error = Signal(str)  

    def __init__(
        self,
        goal: str,
        content_type: str = "",
        tone: str = "",
        style_reference_path: str | None = None,
    ):
        super().__init__()
        self.goal = goal
        self.content_type = content_type
        self.tone = tone
        self.style_reference_path = style_reference_path

    def run(self):
        try:
            state = run_orchestrator(
                self.goal,
                content_type=self.content_type,
                tone=self.tone,
                style_reference_path=self.style_reference_path,
            )
            self.finished_ok.emit(state)
        except Exception as e:
            self.finished_error.emit(str(e))