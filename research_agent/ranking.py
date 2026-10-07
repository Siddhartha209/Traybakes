import json

from research_agent.llm import llm_json
from research_agent.json_utils import extract_json_object


def ranking_node(state, llm=None):
    gaps = state.get('gaps', [])

    if not gaps:
        return {**state, "opportunities": []}

    prompt = f"""
You are a senior growth strategist.

Goal:
{state['goal']}

Opportunities (derived from real gaps found in this run's research):

{json.dumps(gaps, indent=2)}

For each opportunity, rate the following using the rubrics below. Be
disciplined about applying the rubric bands consistently across all
opportunities — do not default to similar scores for everything.

- impact (1-10): how much this could grow brownie-specific revenue or
  awareness if executed well.
    1-3 = marginal, affects a tiny niche audience
    4-6 = moderate, meaningful for one channel or segment
    7-10 = major, could materially shift brand positioning or reach

- competition (1-10): how saturated this space already is among the
  competitors researched in this run.
    1-3 = virtually no competitors doing this
    4-6 = some competitors doing this, inconsistently
    7-10 = most competitors already doing this well

- effort (1-10): implementation cost for a small handmade bakery with
  limited staff and budget.
    1-3 = a single social post or caption tweak
    4-6 = a short campaign or content series
    7-10 = requires new capability (photography, new channel, new process)

- confidence (1-10): how confident you are in this rating given the
  evidence available in this run's research (not how good the opportunity
  is — a strong opportunity backed by thin evidence should still get a
  lower confidence).
    1-3 = little supporting evidence, largely inferred
    4-6 = some supporting evidence
    7-10 = strongly supported by multiple pieces of evidence

Do not add opportunities that are not in the list above. Do not calculate
a score — that is handled separately.

IMPORTANT RULES:
- Return ONLY the JSON object below, no explanation, no markdown fences
- All string values must use double quotes
- No trailing commas
- Write "reason" in full natural English (contractions like "it's" are
  fine) — do not distort grammar to avoid apostrophes
- All numeric values must be plain numbers, not strings

{{
    "opportunities": [
        {{
            "name": "",
            "impact": 0,
            "competition": 0,
            "effort": 0,
            "confidence": 0,
            "reason": ""
        }}
    ]
}}
"""

    response = llm_json.invoke(prompt)
    data = extract_json_object(response.content, node_name="ranking")

    opportunities = data.get("opportunities", [])

    for opp in opportunities:
        try:
            impact = float(opp.get("impact", 0))
            confidence = float(opp.get("confidence", 0))
            competition = float(opp.get("competition", 0))
            effort = float(opp.get("effort", 0))
        except (TypeError, ValueError):
            opp["score"] = 0.0
            continue

        denominator = competition + effort
        opp["score"] = round((impact * confidence) / denominator, 2) if denominator else 0.0

    opportunities = sorted(opportunities, key=lambda x: x.get("score", 0.0), reverse=True)

    return {
        **state,
        "opportunities": opportunities
    }