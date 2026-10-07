"""
Traybakes · AI Marketing Assistant
Backend bootstrap.

Walks upward from this file until it finds the folder that contains the
`orchestrator/` package (same pattern used on the backend: PROJECT_ROOT
anchored off __file__, then inserted into sys.path). This means the UI
can live anywhere in the project tree without hardcoding a path.
"""

import sys
from pathlib import Path


from orchestrator.campaign_store import (
    get_connection,
    record_selection,
    record_rating,
    record_caption_rating,
    record_caption_edit,
)

_campaign_db = get_connection()


def _bootstrap_project_root():
    here = Path(__file__).resolve().parent
    for candidate in [here, *here.parents]:
        marker = candidate / "orchestrator" / "orchestrator.py"
        if marker.exists():
            if str(candidate) not in sys.path:
                sys.path.insert(0, str(candidate))
            return candidate
    return None


PROJECT_ROOT = _bootstrap_project_root()

try:
    from orchestrator.orchestrator import run_orchestrator
    BACKEND_AVAILABLE = True
    BACKEND_IMPORT_ERROR = None
except Exception as _e: 
    run_orchestrator = None
    BACKEND_AVAILABLE = False
    BACKEND_IMPORT_ERROR = str(_e)