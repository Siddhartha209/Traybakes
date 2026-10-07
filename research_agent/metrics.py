# research_agent/metrics.py

from tavily import TavilyClient
import os
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

from research_agent.llm import llm_json
from research_agent.json_utils import extract_json_object

tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

MAX_WORKERS = 4


def _generate_metrics_query(competitor_name: str, goal: str, llm) -> str:
    """Ask the LLM to produce a single focused Tavily query for metrics gathering."""
    prompt = f"""
You are a competitive intelligence researcher.

User goal:
{goal}

Competitor:
{competitor_name}

Write a single Tavily search query to gather business metrics about this competitor
relevant to the user's goal. The query should help uncover:
- social media presence
- target customers and distribution channels
- product categories
- market positioning

Return ONLY the query string — no explanation, no quotes, no markdown.
"""

    response = llm.invoke(prompt)
    query    = response.content.strip().strip('"').strip("'")

    if not query:
        goal_snippet = " ".join(goal.split()[:5])
        query = f"{competitor_name} {goal_snippet} market presence customers products"

    return query


def _gather_metrics_for_competitor(competitor, goal, text_llm):
    """Runs the full per-competitor pipeline (query -> search -> analysis).
    Isolated into its own function so it can be dispatched to a thread pool
    and so a single competitor's failure can't take down the others."""

    name = competitor if isinstance(competitor, str) else competitor["name"]

    query = _generate_metrics_query(name, goal, text_llm)

    result   = tavily.search(query=query, max_results=3)
    evidence = [
        {
            "title":   item.get("title"),
            "content": item.get("content"),
            "url":     item.get("url"),
        }
        for item in result.get("results", [])
    ]

    prompt = f"""
You are analysing a competitor in this market.

Goal context:
{goal}

Competitor:
{name}

Evidence:
{json.dumps(evidence)}

Return ONLY this JSON object, no explanation, no markdown fences:
{{
 "name": "",
 "instagram_present": true,
 "youtube_present": false,
 "linkedin_present": true,
 "market_positioning": "",
 "target_customers": [],
 "product_categories": [],
 "estimated_strengths": [],
 "estimated_weaknesses": []
}}
"""

    response = llm_json.invoke(prompt)
    return extract_json_object(response.content, node_name=f"metrics:{name}")


def metrics_node(state, llm):

    competitors  = state["competitors"][:8]
    goal         = state["goal"]
    metrics      = []
    failed_names = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        future_to_name = {}
        for competitor in competitors:
            name = competitor if isinstance(competitor, str) else competitor["name"]
            future = pool.submit(_gather_metrics_for_competitor, competitor, goal, llm)
            future_to_name[future] = name

        for future in as_completed(future_to_name):
            name = future_to_name[future]
            try:
                metrics.append(future.result())
            except Exception as e:

                failed_names.append(name)

    errors = state.get("errors", [])
    for name in failed_names:
        errors.append({"agent": "metrics", "competitor": name, "error": "metrics extraction failed"})

    return {**state, "metrics": metrics, "errors": errors}