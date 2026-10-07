import json
from copy import deepcopy
from collections import defaultdict


def deduplicate_list(items, key_fields):
    """Remove duplicates based on selected key fields."""
    seen = set()
    cleaned = []

    for item in items:
        key = tuple(item.get(k) for k in key_fields)
        if key not in seen:
            seen.add(key)
            cleaned.append(item)

    return cleaned


def clean_and_group_evidence(evidence_list):
    """
    Group evidence by competitor and attach URLs/snippets under each.
    Removes duplication and flattens structure for reporting.
    """

    grouped = defaultdict(lambda: {
        "name": None,
        "reason": None,
        "evidence": []
    })

    for e in evidence_list:
        comp = e.get("competitor", {}) or {}

        name = comp.get("name") if isinstance(comp, dict) else e.get("competitor")
        reason = comp.get("reason") if isinstance(comp, dict) else None

        if not name:
            continue

        if grouped[name]["name"] is None:
            grouped[name]["name"] = name
            grouped[name]["reason"] = reason

        grouped[name]["evidence"].append({
            "query": e.get("query"),
            "title": e.get("title"),
            "url": e.get("url"),
            "snippet": e.get("snippet")
        })

    return list(grouped.values())


def link_opportunities_to_gaps(gaps, opportunities):
    """
    Try to connect opportunities back to gaps using name matching.
    (simple heuristic version)
    """

    gap_map = {g["name"]: g for g in gaps}

    linked = []

    for opp in opportunities:
        linked_opp = deepcopy(opp)

        for gap_name in gap_map:
            if gap_name.lower() in opp.get("name", "").lower():
                linked_opp["source_gap"] = gap_name
                break

        linked.append(linked_opp)

    return linked


def normalise_json(raw):
    """
    Convert messy research JSON into clean orchestrator-ready format.
    """

    output = {}

    # ------------------------
    # CORE ENTITIES
    # ------------------------
    output["goal"] = raw.get("goal")

    # ------------------------
    # COMPETITORS (light dedupe only)
    # ------------------------
    raw_competitors = deduplicate_list(
        raw.get("competitors", []),
        key_fields=["name"]
    )

    # ------------------------
    # EVIDENCE → GROUPED INTO COMPETITORS
    # ------------------------
    evidence_grouped = clean_and_group_evidence(raw.get("evidence", []))

    # merge evidence into competitor objects
    competitor_map = {c["name"]: c for c in raw_competitors}

    for comp in evidence_grouped:
        name = comp["name"]

        if name in competitor_map:
            # attach evidence
            competitor_map[name]["evidence"] = comp["evidence"]
        else:
            # fallback if competitor wasn't pre-listed
            competitor_map[name] = comp

    output["competitors"] = list(competitor_map.values())

    # ------------------------
    # INSIGHTS LAYER
    # ------------------------
    patterns = raw.get("patterns", [])
    gaps = raw.get("gaps", [])
    opportunities = raw.get("opportunities", [])

    output["insights"] = {
        "patterns": deduplicate_list(patterns, ["name"]),
        "gaps": deduplicate_list(gaps, ["name"]),
        "opportunities": link_opportunities_to_gaps(gaps, opportunities)
    }

    # ------------------------
    # ACTION LAYER
    # ------------------------
    top_opps = sorted(
        output["insights"]["opportunities"],
        key=lambda x: x.get("score", 0),
        reverse=True
    )[:5]

    output["actions"] = {
        "recommended_angles": [
            o["name"] for o in top_opps
        ],
        "recommended_content_themes": list({
            o["name"].split(" - ")[0] for o in top_opps
        }),
        "highest_priority_opportunity": top_opps[0] if top_opps else None
    }

    return output