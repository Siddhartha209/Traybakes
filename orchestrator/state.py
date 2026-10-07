# orchestrator/state.py

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AgentState:
    goal: str
    content_type: str = ""
    tone: str = ""
    style_reference_path: Optional[str] = None
    knowledge: Optional[Dict[str, Any]] = None
    research: Optional[Dict[str, Any]] = None
    images: Optional[List[Any]] = None
    captions: Optional[List[Any]] = None

    errors: List[Dict[str, str]] = field(default_factory=list)

    logs: List[str] = field(default_factory=list)

    metrics: Dict[str, Any] = field(default_factory=dict)

    feedback_items: List[Dict[str, Any]] = field(default_factory=list)

    reference_captions: List[str] = field(default_factory=list)

    learned_avoid_phrases: List[str] = field(default_factory=list)

    campaign_id: Optional[int] = None

    def to_dict(self):
        return {
            "goal": self.goal,
            "content_type": self.content_type,
            "tone": self.tone,
            "style_reference_path": self.style_reference_path,
            "knowledge": self.knowledge,
            "research": self.research,
            "images": self.images,
            "captions": self.captions,
            "logs": self.logs,
            "errors": self.errors,
            "metrics": self.metrics,
            "reference_captions": self.reference_captions,
            "learned_avoid_phrases": self.learned_avoid_phrases,
            "feedback_items": self.feedback_items,
            "campaign_id": self.campaign_id,
        }