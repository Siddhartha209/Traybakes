# research_agent/report.py


def report_node(state, llm):
    return {
        **state,
        "report": {
            "goal":          state["goal"],
            "competitors":   state.get("competitors", []),
            "metrics":       state.get("metrics", []),
            "trends":        state.get("market_trends", {}),   # was "trends" — key mismatch fixed
            "patterns":      state.get("patterns", []),
            "gaps":          state.get("gaps", []),
            "opportunities": state.get("opportunities", []),
        }
    }