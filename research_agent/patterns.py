import json
import re

from research_agent.llm import llm_json
from research_agent.json_utils import extract_json_object

# Cap on how many evidence items / how much text per item gets dumped into
# the prompt
MAX_EVIDENCE_ITEMS = 15
MAX_SNIPPET_CHARS = 300

# Phrases the model uses when it pads out a category it has nothing real
# to say about, instead of just omitting it 
_PLACEHOLDER_MARKERS = (
    "none identified",
    "no data",
    "no visual data",
    "insufficient data",
    "not found",
    "not identified",
    "no explicit",
    "no evidence",
    "n/a",
    "unclear from",
)
MIN_DESCRIPTION_CHARS = 20
MIN_EVIDENCE_CHARS = 15


_GOAL_STOPWORDS = {
    "generate", "create", "develop", "produce", "provide", "conduct",
    "market", "marketing", "research", "analysis", "strategy", "product",
    "products", "for", "the", "and", "or", "with", "about", "into",
    "please", "this", "that", "some", "using",
}


def _goal_keywords(goal: str) -> set[str]:
    """
    Pulls the significant, product/niche-specific words out of the goal
    text itself (e.g. "salted", "caramel", "brownie" from "generate
    market research for salted caramel brownie product"). Entirely
    derived at runtime from whatever goal is passed in — nothing
    product-specific is hardcoded, so this works the same way regardless
    of what product the goal is actually about.
    """
    words = re.findall(r"[a-zA-Z']+", goal.lower())
    return {w for w in words if len(w) > 3 and w not in _GOAL_STOPWORDS}


def _is_off_goal(pattern: dict, goal_keywords: set[str]) -> bool:
    if not goal_keywords:

        return False
    text = f"{pattern.get('name', '')} {pattern.get('description', '')} {pattern.get('evidence', '')}".lower()
    return not any(kw in text for kw in goal_keywords)


def _is_incomplete(pattern: dict) -> bool:
    description = str(pattern.get("description", "")).strip()
    evidence = str(pattern.get("evidence", "")).strip()
    return len(description) < MIN_DESCRIPTION_CHARS or len(evidence) < MIN_EVIDENCE_CHARS


def _is_placeholder(pattern: dict) -> bool:
    text = f"{pattern.get('description', '')} {pattern.get('evidence', '')}".lower()
    return any(marker in text for marker in _PLACEHOLDER_MARKERS)


def _trim_evidence(evidence: list[dict]) -> list[dict]:
    trimmed = []
    for item in evidence[:MAX_EVIDENCE_ITEMS]:
        trimmed.append({
            "competitor": item.get("competitor"),
            "title": item.get("title"),
            "snippet": (item.get("snippet") or "")[:MAX_SNIPPET_CHARS],
        })
    return trimmed


def patterns_node(state, llm=None):

    evidence = _trim_evidence(state.get("evidence", []))
    goal = state["goal"]

    prompt = f"""
You are a market research analyst.

Goal:
{goal}

Use ONLY the evidence provided below. Do not use outside knowledge.

Evidence:

{json.dumps(evidence)}

Identify real, concrete patterns visible in this evidence that are
directly relevant to the goal above — things like recurring content
themes, posting patterns, visual styles, engagement tactics, or calls-to-
action are examples of the KIND of thing to look for, not a checklist you
must fill in.

Return between 0 and 3 patterns — however many the evidence actually
supports. It is normal and expected to return fewer than 3, or even 0, if
the evidence is thin.

STRICT RULES:
- Every pattern must explicitly reference the specific product, flavor,
  or niche named in the goal ("{goal}") — using that same term or a very
  close variant in the pattern's name or description. A pattern that
  only describes the broader industry/category in general (e.g. how
  bakeries in general use social media) with no direct connection to
  this specific product/niche does NOT satisfy this rule, even if it is
  true and well-evidenced. If the evidence only supports generic
  findings like this, prefer returning fewer patterns (or none) over
  padding with off-goal ones.
- Every pattern's "evidence" field must quote or closely paraphrase a
  specific detail from the Evidence list above (mention the competitor
  or title it came from).
- Do NOT include a pattern if you have nothing concrete to say about it.
- Do NOT write placeholder entries such as "None identified", "no data
  provided", "insufficient data", or similar. If there is nothing to
  report for a category, simply leave it out of the list entirely —
  never include an entry just to reach a certain count.

Return ONLY this JSON object, no explanation, no markdown fences:

{{
  "patterns": [
    {{
      "name": "",
      "description": "",
      "evidence": ""
    }}
  ]
}}
"""

    response = llm_json.invoke(prompt)
    data = extract_json_object(response.content, node_name="patterns")

    goal_keywords = _goal_keywords(goal)

    raw_patterns = data.get("patterns", [])
    filtered = [
        p for p in raw_patterns
        if not _is_placeholder(p)
        and not _is_incomplete(p)
        and not _is_off_goal(p, goal_keywords)
    ]

    dropped = len(raw_patterns) - len(filtered)
    if dropped:
        print(f"[patterns] Dropped {dropped} pattern(s) with placeholder, incomplete, or off-goal content")

    return {
        **state,
        "patterns": filtered
    }