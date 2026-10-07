# research_agent/collect.py

from tavily import TavilyClient
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

from research_agent.llm import llm_json
from research_agent.json_utils import extract_json_object

tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

MAX_WORKERS = 4


def _generate_competitor_queries(competitor_name: str, goal: str, llm) -> list[str]:
    """Ask the LLM to produce 3 targeted search queries for a single competitor."""
    prompt = f"""
You are a competitive intelligence researcher.

User goal:
{goal}

Competitor:
{competitor_name}

Generate exactly 3 Tavily search queries to gather evidence about this competitor
relevant to the user's goal. Cover different angles such as:
- their product range and positioning
- their target customers and distribution channels
- their social media or marketing presence
- their market share or trade positioning

Return ONLY this JSON object, no explanation, no markdown fences:
{{"queries": ["query 1", "query 2", "query 3"]}}
"""

    try:
        response = llm.invoke(prompt)
        data = extract_json_object(response.content, node_name="collect:queries")
        queries = data.get("queries", [])
        if isinstance(queries, list) and len(queries) > 0:
            return queries
    except Exception as e:
        print(f"[collect] query generation failed for {competitor_name}: {e}")

    goal_snippet = " ".join(goal.split()[:6])
    return [
        f"{competitor_name} {goal_snippet} products",
        f"{competitor_name} target customers distribution",
        f"{competitor_name} social media marketing",
    ]


def _collect_for_competitor(competitor, goal, llm):
    name = competitor if isinstance(competitor, str) else competitor["name"]
    queries = _generate_competitor_queries(name, goal, llm)
    
    items = []
    for query in queries:
        result = tavily.search(query=query, max_results=3)
        for item in result.get("results", []):
            url = item.get("url")
            if not url:
                continue
            items.append({
                "competitor": name,
                "query":      query,
                "title":      item.get("title"),
                "url":        url,
                "snippet":    item.get("content", "")[:1000],
            })
    return items


def collect_node(state, llm):

    evidence    = []
    competitors = state["competitors"][:8]
    goal        = state["goal"]
    seen_urls   = set()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = [
            pool.submit(_collect_for_competitor, competitor, goal, llm)
            for competitor in competitors
        ]

        for future in as_completed(futures):
            try:
                items = future.result()
            except Exception as e:
                continue

            for item in items:
                url = item["url"]
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                evidence.append(item)

    return {
        **state,
        "evidence": evidence,
    }