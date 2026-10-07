# research_agent/trends.py

from tavily import TavilyClient
import os
import json
from concurrent.futures import ThreadPoolExecutor

from research_agent.llm import llm_json
from research_agent.json_utils import extract_json_object

tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


def trends_node(state, llm):

    goal = state["goal"]

    # ----------------------------------------
    # Step 1: generate trend queries from goal
    # ----------------------------------------
    query_prompt = f"""
You are a market research assistant.

User goal:
{goal}

Generate exactly 3 Tavily search queries to find current market trends relevant to this goal.
Cover different angles such as:
- consumer demand shifts in the relevant product or service category
- growth or decline in relevant market segments
- emerging opportunities for suppliers or brands in this space

Return ONLY this JSON object, no explanation, no markdown fences:
{{"queries": ["query 1", "query 2", "query 3"]}}
"""

    try:
        query_response = llm_json.invoke(query_prompt)
        query_data = extract_json_object(query_response.content, node_name="trends:queries")
        searches = query_data.get("queries", [])
        if not isinstance(searches, list) or len(searches) == 0:
            raise ValueError("Empty or invalid query list")
    except Exception as e:
        goal_snippet = " ".join(goal.split()[:6])
        searches = [
            f"{goal_snippet} market trends 2026",
            f"{goal_snippet} consumer demand growth",
            f"{goal_snippet} industry emerging opportunities",
        ]


    # ----------------------------------------
    # Step 2: run the searches (independent —
    # parallelized rather than sequential)
    # ----------------------------------------
    evidence = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        for query, result in zip(
            searches,
            pool.map(lambda q: tavily.search(query=q, max_results=3), searches),
        ):
            for item in result.get("results", []):
                evidence.append({
                    "query":   query,
                    "title":   item.get("title"),
                    "content": item.get("content"),
                    "url":     item.get("url"),
                })

    # ----------------------------------------
    # Step 3: synthesise trends
    # ----------------------------------------
    prompt = f"""
You are a market analyst.

Goal:
{goal}

Research:
{json.dumps(evidence)}

Return ONLY this JSON object, no explanation, no markdown fences:
{{
 "market_trends": [
  {{
   "name": "",
   "description": "",
   "evidence": ""
  }}
 ],
 "growing_segments":       [],
 "declining_segments":     [],
 "emerging_opportunities": []
}}
"""

    default_trends = {
        "market_trends":          [],
        "growing_segments":       [],
        "declining_segments":     [],
        "emerging_opportunities": [],
    }

    try:
        response = llm_json.invoke(prompt)
        trends = extract_json_object(response.content, node_name="trends")
    except Exception as e:
        trends = default_trends

    return {**state, "market_trends": trends}