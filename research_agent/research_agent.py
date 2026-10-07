# research_agent/research_agent.py

import json
from pathlib import Path

from langgraph.graph import StateGraph, END
from research_agent.llm import llm
from research_agent.json_normaliser import normalise_json

from research_agent.discover import discover_node
from research_agent.collect import collect_node
from research_agent.patterns import patterns_node
from research_agent.gaps import gaps_node
from research_agent.ranking import ranking_node
from research_agent.report import report_node
from research_agent.metrics import metrics_node
from research_agent.trends import trends_node


def safe_node(name, fn, defaults):
    """
    Wrap a graph node so a failure inside it degrades gracefully instead
    of blowing up the whole run.

    Each node is wrapped individually: any exception is caught, logged
    into state["errors"], and the node returns the state with sensible
    empty defaults filled in for whatever keys it was supposed to
    produce. Every downstream node then just sees an empty list/dict for
    that piece and keeps going on partial data, instead of the whole
    graph dying.

    IMPORTANT: this used to be the only place a failure was recorded, and
    state["errors"] was never carried through into the final normalised
    research object — so a node silently defaulting to [] was
    indistinguishable, from the UI's perspective, from that node
    genuinely finding nothing. run_research_agent() below now attaches
    these errors to the final result under "meta.node_errors" so callers
    (the orchestrator, the dashboard) can tell the difference and surface
    it instead of showing a quietly empty section.
    """
    def wrapped(state):
        try:
            return fn(state)
        except Exception as e:
            errors = state.get("errors", [])
            errors.append({"agent": name, "error": str(e)})
            updated = {**state, "errors": errors}
            for key, default_value in defaults.items():
                updated.setdefault(key, default_value)
            return updated
    return wrapped


def build_graph():
    graph = StateGraph(dict)

    graph.add_node("discover", safe_node("discover", lambda s: discover_node(s, llm), {"competitors": []}))
    graph.add_node("collect",  safe_node("collect",  lambda s: collect_node(s, llm),  {"evidence": []}))
    graph.add_node("metrics",  safe_node("metrics",  lambda s: metrics_node(s, llm),  {"metrics": []}))
    graph.add_node("trends",   safe_node("trends",   lambda s: trends_node(s, llm),   {"market_trends": {}}))
    graph.add_node("patterns", safe_node("patterns", lambda s: patterns_node(s, llm), {"patterns": []}))
    graph.add_node("gaps",     safe_node("gaps",     lambda s: gaps_node(s, llm),     {"gaps": []}))
    graph.add_node("ranking",  safe_node("ranking",  lambda s: ranking_node(s, llm),  {"opportunities": []}))
    graph.add_node("report",   safe_node("report",   lambda s: report_node(s, llm),   {"report": {}}))

    graph.set_entry_point("discover")

    graph.add_edge("discover", "collect")
    graph.add_edge("collect",  "metrics")
    graph.add_edge("metrics",  "trends")
    graph.add_edge("trends",   "patterns")
    graph.add_edge("patterns", "gaps")
    graph.add_edge("gaps",     "ranking")
    graph.add_edge("ranking",  "report")
    graph.add_edge("report",   END)

    return graph.compile()


def run_research_agent(state):
    """
    Cache is OPTIONAL context only.
    Research graph ALWAYS runs.

    Every node inside the graph is wrapped with safe_node(), so a failure
    in, say, ranking no longer discards work already completed by
    discover/collect/metrics/trends/patterns/gaps. The try/except below
    is a last-resort safety net for things outside any single node's
    control (Tavily/network fully unreachable, a bug in the graph wiring
    itself, cache write failing) rather than the primary error-handling
    path.
    """

    try:
        cache_path = Path(__file__).resolve().parent / "clean_output.json"

        seed_context = None


        if cache_path.exists():
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    seed_context = json.load(f)

                state.logs.append("Loaded cached research as seed context")

            except Exception:
                seed_context = None

        graph = build_graph()

        raw_result = graph.invoke({
            "goal": state.goal,
            "seed": seed_context,   
            "errors": [],
        })

        node_errors = raw_result.get("errors", [])

        normalised = normalise_json({
            **raw_result,
            "goal": state.goal,
        })

        normalised["meta"] = {
            "node_errors": node_errors,
            "has_errors": bool(node_errors),
        }


        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(normalised, f, indent=2, ensure_ascii=False)

        state.research = normalised

        if node_errors:
            state.logs.append(
                f"Research agent completed with {len(node_errors)} node-level "
                f"error(s), partial data used: {node_errors}"
            )

            state.errors.extend([
                {"agent": f"research_agent.{e.get('agent', '?')}", "error": e.get("error", "")}
                for e in node_errors
            ])
        else:
            state.logs.append("Research agent completed successfully")

        state.logs.append("Research cache updated (non-blocking)")

    except Exception as e:
        state.errors.append({
            "agent": "research_agent",
            "error": str(e)
        })

        state.research = {
            "competitors": [],
            "insights": {
                "patterns": [],
                "gaps": [],
                "opportunities": []
            },
            "actions": {},
            "meta": {"node_errors": [], "has_errors": True},
        }

    return state