# knowledge_lookup.py

from typing import Dict, Any, List
from pathlib import Path
import json
import re
import time


STALENESS_MAX_AGE_DAYS = 14.0

MIN_GOAL_SIMILARITY = 0.2

_STOPWORDS = {
    "the", "a", "an", "and", "or", "to", "of", "in", "for", "with", "our",
    "is", "are", "it", "its", "on", "at", "that", "this", "be", "as",
    "from", "we", "us",
}


def has_value(x):
    return x is not None and x != "" and x != [] and x != {}


def count_nested_evidence(competitors: List[dict]) -> int:
    total = 0
    for competitor in competitors:
        total += len(competitor.get("evidence", []))
    return total


def evaluate_competitor_quality(competitors: List[dict]) -> float:
    if not competitors:
        return 0.0

    score = 0.0

    if len(competitors) >= 3:
        score += 0.3
    elif len(competitors) == 2:
        score += 0.2
    else:
        score += 0.1

    reasoning_ok = sum(
        1 for competitor in competitors
        if has_value(competitor.get("reason"))
    )
    score += 0.2 * (reasoning_ok / len(competitors))

    evidence_count = count_nested_evidence(competitors)
    if evidence_count >= 10:
        score += 0.5
    elif evidence_count >= 5:
        score += 0.35
    elif evidence_count >= 2:
        score += 0.2
    else:
        score += 0.05

    return min(score, 1.0)


def evaluate_insights(insights: Dict[str, Any]) -> float:
    if not insights:
        return 0.0

    score = 0.0

    patterns = insights.get("patterns", [])
    gaps = insights.get("gaps", [])
    opportunities = insights.get("opportunities", [])

    score += 0.2 if patterns else 0
    score += 0.3 if gaps else 0
    score += 0.3 if opportunities else 0

    if len(patterns) >= 3:
        score += 0.05
    if len(gaps) >= 3:
        score += 0.05
    if len(opportunities) >= 3:
        score += 0.10

    return min(score, 1.0)


def evaluate_evidence_quality(evidence: List[dict]) -> float:
    if not evidence:
        return 0.0

    usable = sum(
        1 for item in evidence
        if item.get("url") and item.get("snippet")
    )

    ratio = usable / len(evidence)

    if ratio > 0.8:
        return 1.0
    if ratio > 0.5:
        return 0.7
    if ratio > 0.2:
        return 0.4
    return 0.1


def knowledge_sufficiency_check(raw: Dict[str, Any]) -> Dict[str, Any]:
    missing = []

    goal = raw.get("goal")
    competitors = raw.get("competitors", [])
    insights = raw.get("insights", {})
    evidence = raw.get("evidence", [])

    if not has_value(goal):
        missing.append("goal")
    if len(competitors) < 2:
        missing.append("competitors (need at least 2)")
    if len(evidence) < 3:
        missing.append("evidence (too sparse)")

    competitor_score = evaluate_competitor_quality(competitors)
    insight_score = evaluate_insights(insights)
    evidence_score = evaluate_evidence_quality(evidence)

    final_score = (
        competitor_score * 0.4 +
        insight_score * 0.4 +
        evidence_score * 0.2
    )

    sufficient = (
        not missing
        and final_score >= 0.55
        and bool(insights.get("gaps"))
        and bool(insights.get("opportunities"))
    )

    return {
        "sufficient": sufficient,
        "confidence": round(final_score, 3),
        "score_components": {
            "competitors": competitor_score,
            "insights": insight_score,
            "evidence": evidence_score,
        },
        "missing": missing,
        "reason": (
            "Sufficient structured knowledge"
            if sufficient
            else "Insufficient structured knowledge; research enrichment required"
        ),
    }


def _normalized_words(text):
    if not text:
        return set()

    words = re.findall(r"[a-zA-Z']+", text.lower())
    return {
        word for word in words
        if word not in _STOPWORDS and len(word) > 2
    }


# Jaccard similarity is used because it compares shared keywords without
# depending on sentence length or exact phrasing.
def _goal_similarity(goal_a, goal_b) -> float:
    words_a = _normalized_words(goal_a)
    words_b = _normalized_words(goal_b)

    if not words_a or not words_b:
        return 0.0

    intersection = words_a & words_b
    union = words_a | words_b

    return len(intersection) / len(union)

def _cache_age_days(cached_timestamp) -> float:
    if not cached_timestamp:
        return float("inf")

    return max((time.time() - cached_timestamp) / 86400.0, 0.0)


def run_knowledge_lookup(state):
    project_root = Path(__file__).resolve().parent
    filepath = project_root / "research_agent" / "clean_output.json"

    state.errors = getattr(state, "errors", [])
    state.logs = getattr(state, "logs", [])

    current_goal = getattr(state, "goal", None)

    if not filepath.exists():
        state.errors.append({
            "agent": "knowledge_lookup",
            "error": "No cache found — will run research_agent"
        })
        state.knowledge = {
            "sufficient": False,
            "cached_research": None
        }
        return state

    try:
        with filepath.open("r", encoding="utf-8") as file:
            cached = json.load(file)

        safe_research = {
            "goal": cached.get("goal"),
            "timestamp": cached.get("timestamp"),
            "competitors": cached.get("competitors", []),
            "evidence": cached.get("evidence", []),
            "insights": {
                "patterns": cached.get("insights", {}).get("patterns", []),
                "gaps": cached.get("insights", {}).get("gaps", []),
                "opportunities": cached.get("insights", {}).get("opportunities", [])
            },
            "actions": cached.get("actions", {})
        }

        cached_goal = safe_research["goal"]
        similarity = _goal_similarity(current_goal, cached_goal)
        goal_matches = similarity >= MIN_GOAL_SIMILARITY

        age_days = _cache_age_days(safe_research["timestamp"])
        is_stale = age_days > STALENESS_MAX_AGE_DAYS

        if not goal_matches:
            state.knowledge = {
                "sufficient": False,
                "confidence": 0.0,
                "reason": (
                    f"Cached research goal ('{cached_goal}') does not match "
                    f"current goal ('{current_goal}'); similarity={similarity:.2f}"
                ),
                "cached_research": safe_research,
            }
            state.logs.append(
                "Knowledge check: cache rejected — goal mismatch "
                f"(similarity={similarity:.2f})"
            )
            return state

        if is_stale:
            state.knowledge = {
                "sufficient": False,
                "confidence": 0.0,
                "reason": (
                    f"Cached research is {age_days:.1f} days old "
                    f"(limit {STALENESS_MAX_AGE_DAYS}); re-running research"
                ),
                "cached_research": safe_research,
            }
            state.logs.append(
                f"Knowledge check: cache rejected — stale ({age_days:.1f} days old)"
            )
            return state

        result = knowledge_sufficiency_check({
            "goal": current_goal,
            "competitors": safe_research["competitors"],
            "insights": safe_research["insights"],
            "evidence": safe_research["evidence"],
        })

        state.knowledge = {
            **result,
            "cached_research": safe_research,
        }

        state.logs.append(
            f"Knowledge check complete: sufficient={result['sufficient']} "
            f"confidence={result['confidence']}"
        )

    except Exception as error:
        state.errors.append({
            "agent": "knowledge_lookup",
            "error": str(error)
        })
        state.knowledge = {
            "sufficient": False,
            "cached_research": None
        }

    return state