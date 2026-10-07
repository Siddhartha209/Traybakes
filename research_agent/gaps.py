import json
import re

from research_agent.llm import llm_json
from research_agent.json_utils import extract_json_object

MAX_EVIDENCE_ITEMS = 12
MAX_SNIPPET_CHARS = 300


_ECHOED_STRUCTURE_MARKERS = (
    "already identified",
    '{"name"',
    "{'name'",
)


def _cites_patterns_instead_of_evidence(gap: dict) -> bool:
    text = str(gap.get("evidence", ""))
    lowered = text.lower()
    return any(marker.lower() in lowered for marker in _ECHOED_STRUCTURE_MARKERS)


def _trim_evidence(evidence: list[dict]) -> list[dict]:
    trimmed = []
    for item in evidence[:MAX_EVIDENCE_ITEMS]:
        trimmed.append({
            "competitor": item.get("competitor"),
            "title": item.get("title"),
            "snippet": (item.get("snippet") or "")[:MAX_SNIPPET_CHARS],
        })
    return trimmed


def gaps_node(state, llm=None):

    evidence = _trim_evidence(state.get("evidence", []))
    patterns = state.get("patterns", [])[:10]
    goal = state["goal"]

    prompt = f"""
You are a senior marketing strategist.

Goal:
{goal}

Patterns already identified (BACKGROUND CONTEXT ONLY — do not cite these as
evidence; they exist purely to help you avoid repeating findings already
made):

{json.dumps(patterns)}

Evidence (this is the ONLY thing you may cite in the "evidence" field
below):

{json.dumps(evidence)}

Identify up to 3 real opportunities competitors are NOT exploiting, grounded
strictly in the Evidence list above and directly relevant to the goal
above. Do not invent generic gaps that aren't supported by that evidence,
and do not include gaps that are only generic industry observations with
no clear connection to this specific goal.

Look for:

- content gaps
- audience gaps
- positioning gaps
- messaging gaps
- platform gaps
- trend gaps

Return between 0 and 3 gaps — however many the evidence actually supports.
It is normal to return fewer than 3 if the evidence doesn't support that
many distinct, well-grounded, goal-relevant gaps.

STRICT RULES:
- Every gap must relate specifically to the goal ("{goal}") — if a gap is
  only a generic bakery/industry observation with no clear connection to
  this specific goal, omit it rather than including it as padding.
- Every gap's "evidence" field must quote or closely paraphrase a specific
  detail from the Evidence list (name the competitor or title it came
  from). It must NOT reference or restate the Patterns list above, and
  must NOT contain the words "already identified" or any JSON-like
  fragment copied from the Patterns section.
- If the evidence does not clearly support a given gap, omit it rather
  than guessing.
- Write "description" and "reason" in full natural English.
- Return ONLY valid JSON, no explanation, no markdown fences
- All string values must use double quotes
- No trailing commas

{{
    "gaps": [
        {{
            "name": "",
            "description": "",
            "reason": "",
            "evidence": ""
        }}
    ]
}}
"""

    response = llm_json.invoke(prompt)
    data = extract_json_object(response.content, node_name="gaps")

    raw_gaps = data.get("gaps", [])
    filtered = [g for g in raw_gaps if not _cites_patterns_instead_of_evidence(g)]

    dropped = len(raw_gaps) - len(filtered)
    if dropped:
        print(f"[gaps] Dropped {dropped} gap(s) that cited patterns instead of raw evidence")

    return {
        **state,
        "gaps": filtered
    }