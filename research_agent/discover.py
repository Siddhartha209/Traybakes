# research_agent/discover.py

from tavily import TavilyClient
import os
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor

from research_agent.llm import llm_json
from research_agent.json_utils import extract_json_object

tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


def _fallback_competitors_from_research(research: list) -> list[dict]:
    """
    Best-effort competitor list built directly from search result domains.

    Used only if the LLM extraction step fails to return parseable JSON
    (or returns an empty list), so a single bad LLM response degrades
    discovery instead of raising and killing the whole graph run.
    """
    seen = set()
    fallback = []

    for item in research:
        url = item.get("url", "")
        title = item.get("title", "")

        if not url:
            continue

        domain = re.sub(r"^https?://(www\.)?", "", url).split("/")[0]

        if domain in seen:
            continue
        seen.add(domain)

        fallback.append({
            "name": title or domain,
            "reason": "Fallback: derived from a search result domain because "
                      "competitor extraction failed to parse.",
        })

        if len(fallback) >= 5:
            break

    return fallback


def discover_node(state, llm):
    time.sleep(15)  
    goal = state["goal"]

    query_prompt = f"""
You are a competitive intelligence researcher.

User goal:
{goal}

Generate exactly 3 Tavily search queries to discover direct competitors relevant to this goal.

STRICT RULES:
- Every query MUST include the specific product, flavor, or niche term
  from the goal above (e.g. if the goal mentions "salted caramel
  brownie", every query must contain that exact term or a very close
  variant — do not generalize to just "bakery" or "brownies").
- Each query should target a different angle within that specific
  product/niche (e.g. direct product competitors, customer segment,
  trade directory, regional supply chain) — vary the angle, not the
  product specificity.
- Do not produce queries that would return results about the broader
  category only, with no connection to the specific goal.

Return ONLY this JSON object, no explanation, no markdown fences:
{{"queries": ["query 1", "query 2", "query 3"]}}
"""

    try:
        query_response = llm_json.invoke(query_prompt)
        query_data = extract_json_object(query_response.content, node_name="discover:queries")
        searches = query_data.get("queries", [])
        if not isinstance(searches, list) or len(searches) == 0:
            raise ValueError("Empty or invalid query list")
    except Exception as e:

        goal_snippet = " ".join(goal.split()[:8])
        searches = [
            f"{goal_snippet} competitors suppliers",
            f"{goal_snippet} industry leading companies",
            f"{goal_snippet} trade directory market overview",
        ]
    research = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        for result in pool.map(lambda q: tavily.search(query=q, max_results=3), searches):
            research.extend(result.get("results", []))

    prompt = f"""
You are a market research analyst.

Goal:
{goal}

From the search results below, extract REAL direct competitors most relevant to this goal.

Include only:
- Established companies that compete directly in this market
- Suppliers, manufacturers, or brands in the same space

Prioritize competitors whose products, pages, or descriptions connect
specifically to the goal above over competitors that only match the
broader industry category with no clear connection to the specific
product/niche in the goal.

Exclude:
- Bloggers, influencers, recipe sites
- News articles or aggregators
- Unrelated businesses

Return a maximum of 3 competitors ranked by relevance to the goal.

Return ONLY this JSON object, no explanation, no markdown fences:
{{
  "competitors": [
    {{
      "name": "",
      "reason": ""
    }}
  ]
}}

Research:
{json.dumps(research)}
"""

    try:
        response = llm_json.invoke(prompt)
        data = extract_json_object(response.content, node_name="discover")
        raw_competitors = data.get("competitors", [])

        if not raw_competitors:
            raise ValueError("LLM returned an empty competitors list")

    except Exception as e:
        raw_competitors = _fallback_competitors_from_research(research)

    competitors = []
    seen        = set()
    for item in raw_competitors[:8]:
        name = item.get("name") if isinstance(item, dict) else item
        if name and name not in seen:
            competitors.append(item)
            seen.add(name)

    return {
        **state,
        "competitors": competitors,
    }