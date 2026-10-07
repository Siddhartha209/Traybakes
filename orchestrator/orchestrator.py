from __future__ import annotations

import os
import time
from dotenv import load_dotenv

from caption_generation.caption_generation import run_caption_gen
from img_gen.generator import run_image_gen
from knowledge_lookup import run_knowledge_lookup
from orchestrator.campaign_store import (
    get_connection,
    get_similar_liked_captions,
    get_learned_edit_phrases,
    save_campaign_from_state,
)
from orchestrator.dispatcher import Dispatcher
from orchestrator.planner import Planner
from orchestrator.state import AgentState
from research_agent.research_agent import run_research_agent

load_dotenv()

_campaign_db = get_connection()

SUBSYSTEMS = {
    "knowledge_lookup": run_knowledge_lookup,
    "research_agent": run_research_agent,
    "image_generator": run_image_gen,
    "caption_generator": run_caption_gen,
}

GROQ_PRICING_PER_MILLION = {
    "openai/gpt-oss-120b": {"input": 0.15, "output": 0.60},
    "openai/gpt-oss-20b": {"input": 0.05, "output": 0.08},  
}

GEMINI_PRICING_PER_MILLION = {
    "gemini-2.5-flash": {"input": 0.075, "output": 0.30},
    "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
}

GEMINI_FLASH_IMAGE_COST_PER_IMAGE = 0.03

USD_TO_GBP_RATE = 0.79  

def _compute_cost_usd(entry: dict) -> float:
    model = entry.get("model", "")

    if entry.get("type") == "image":
        image_count = entry.get("image_count", 0) or entry.get("images", 0)
        if image_count:
            return float(image_count) * GEMINI_FLASH_IMAGE_COST_PER_IMAGE
        return 0.0

    pricing = GROQ_PRICING_PER_MILLION.get(model)
    if not pricing:
        return 0.0

    prompt_tokens = entry.get("prompt_tokens", 0) or 0
    completion_tokens = entry.get("completion_tokens", 0) or 0
    return (prompt_tokens / 1_000_000 * pricing["input"]) + (
        completion_tokens / 1_000_000 * pricing["output"]
    )


def _compute_cost_gbp(entry: dict) -> float:
    """Convert USD cost to GBP for display purposes."""
    return _compute_cost_usd(entry) * USD_TO_GBP_RATE


def _finalize_metrics(state: AgentState, planner_time: float, total_time: float) -> None:
    """Aggregates execution time, token usage, and research insights into state.metrics."""
    state.metrics["planner_time_sec"] = planner_time
    state.metrics["total_time_sec"] = total_time

    token_usage = state.metrics.get("token_usage", [])
    total_cost = sum(_compute_cost_gbp(e) for e in token_usage)
    total_tokens = sum(e.get("total_tokens", 0) or 0 for e in token_usage)
    num_requests = len(token_usage)

    state.metrics["total_cost"] = round(total_cost, 6)
    state.metrics["avg_cost_per_request"] = (
        round(total_cost / num_requests, 6) if num_requests else None
    )

    research = state.research or {}
    insights = research.get("insights", {})
    state.metrics["patterns_found"] = len(insights.get("patterns", []) or [])
    state.metrics["gaps_found"] = len(insights.get("gaps", []) or [])
    state.metrics["opportunities_found"] = len(insights.get("opportunities", []) or [])

    state.metrics.setdefault("subsystem_times_sec", {})
    state.metrics.setdefault("subsystems_selected", [])
    state.metrics.setdefault("plan_errors", 0)


def run_orchestrator(
    goal: str,
    content_type: str = "",
    tone: str = "",
    style_reference_path: str | None = None,
) -> AgentState:
    start_total = time.perf_counter()

    state = AgentState(
        goal=goal,
        content_type=content_type,
        tone=tone,
        style_reference_path=style_reference_path,
    )
    state.metrics["token_usage"] = []

    state.reference_captions = get_similar_liked_captions(
        _campaign_db, goal, top_k=3, content_type=content_type
    )
    if state.reference_captions:
        state.logs.append(
            f"Retrieved {len(state.reference_captions)} similar past-liked caption(s) for feedback loop"
        )

    state.learned_avoid_phrases = get_learned_edit_phrases(_campaign_db, top_k=10)
    if state.learned_avoid_phrases:
        state.logs.append(
            f"Loaded {len(state.learned_avoid_phrases)} learned avoid-phrase(s) from past edits"
        )

    planner = Planner()
    t0 = time.perf_counter()
    plan = planner.create_plan(state.goal)
    planner_time = time.perf_counter() - t0

    planner_usage = plan.pop("_usage", None)
    planner_model = plan.pop("_model", "openai/gpt-oss-120b")
    if planner_usage:
        state.metrics["token_usage"].append(
            {
                "agent": "planner",
                "model": planner_model,
                **planner_usage,
            }
        )

    state.logs.append(f"Plan created: {plan}")

    dispatcher = Dispatcher(SUBSYSTEMS)
    state = dispatcher.execute(plan, state)

    total_time = time.perf_counter() - start_total
    _finalize_metrics(state, planner_time, total_time)

    state.campaign_id = save_campaign_from_state(_campaign_db, state)
    return state