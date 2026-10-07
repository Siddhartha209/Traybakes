from __future__ import annotations

import json
import os
import re
import time
from typing import Dict, Optional
from groq import Groq

VALID_SUBSYSTEMS = {
    "knowledge_lookup",
    "research_agent",
    "image_generator",
    "caption_generator",
}

SYSTEM_PROMPT = """
You are an AI Orchestrator for a social media marketing system for
Traybakes, a UK handmade cake and traybake company selling to wholesale
buyers and independent cafés.

You do NOT execute tasks. You ONLY decide which subsystems are needed
to satisfy the user's goal.

Available subsystems:

- knowledge_lookup: Checks what is already known/cached before doing
  new work. Cheap. The system will always run this regardless of your
  answer, so you do not need to justify including it — but you may
  include it if it is genuinely central to the goal (e.g. the user is
  explicitly asking "what do we already know about X").

- research_agent: Gathers NEW external information — competitor
  activity, market trends, content gaps, audience patterns. Choose this
  when the goal requires information the system does not already have,
  e.g. "see what competitors are posting", "find content gaps",
  "what's trending for wholesale bakeries right now". Do NOT choose this
  if the goal only asks for output (a caption, an image) using
  information that's already known or doesn't depend on fresh research.

- image_generator: Generates new visual/image assets. Choose this only
  when the goal explicitly needs a new image, graphic, or visual asset
  produced. Do NOT choose this for a goal that is purely about text
  (captions, copy, messaging) with no visual component mentioned.

- caption_generator: Writes social media captions/copy. Choose this
  when the goal asks for written content — a caption, post copy, or
  similar. Do NOT choose this if the goal is purely research or purely
  image generation with no caption requested.

Rules:
- Only choose what the goal actually requires. Adding an unnecessary
  subsystem wastes real time and money — under-select rather than
  over-select when a goal is ambiguous about one subsystem but clear
  about others.
- Do not choose research_agent "just in case" — only when the goal
  depends on information not already available.
- Always give a short, concrete reason tied to the actual goal text,
  not a generic justification.

Examples:

Goal: "Write a caption for our new honeycomb crunch traybake."
{
  "required_subsystems": [
    {"name": "caption_generator", "reason": "goal explicitly asks for a caption"}
  ]
}

Goal: "Find out what other bakeries are posting about corporate gifting this month."
{
  "required_subsystems": [
    {"name": "research_agent", "reason": "goal needs current competitor activity, not something already known"}
  ]
}

Goal: "Launch a full campaign for our new rocky road bar — new product shot and captions."
{
  "required_subsystems": [
    {"name": "research_agent", "reason": "new product launch benefits from current market/competitor context"},
    {"name": "image_generator", "reason": "goal explicitly asks for a new product shot"},
    {"name": "caption_generator", "reason": "goal explicitly asks for captions"}
  ]
}

Goal: "What do we already know about our flapjack customers?"
{
  "required_subsystems": [
    {"name": "knowledge_lookup", "reason": "goal is explicitly asking what is already known, not requesting new output"}
  ]
}

Return ONLY valid JSON in this exact shape, no other text:
{
  "required_subsystems": [
    {
      "name": "subsystem_name",
      "reason": "short explanation"
    }
  ]
}
"""

_FULL_FALLBACK = {
    "required_subsystems": [
        {"name": "knowledge_lookup", "reason": "fallback: planner unavailable"},
        {"name": "research_agent", "reason": "fallback: planner unavailable"},
        {"name": "image_generator", "reason": "fallback: planner unavailable"},
        {"name": "caption_generator", "reason": "fallback: planner unavailable"},
    ]
}

PLANNER_MODEL = "openai/gpt-oss-120b"
MAX_PLANNER_RETRIES = 2
RETRY_BACKOFF_SECONDS = 1.0


def _usage_to_dict(response) -> Optional[Dict[str, int]]:
    usage = getattr(response, "usage", None)
    if not usage:
        return None
    return {
        "prompt_tokens": getattr(usage, "prompt_tokens", 0) or 0,
        "completion_tokens": getattr(usage, "completion_tokens", 0) or 0,
        "total_tokens": getattr(usage, "total_tokens", 0) or 0,
    }


class Planner:
    def __init__(self, api_key: Optional[str] = None):
        key = api_key or os.getenv("GROQ_API_KEY")
        self.client = Groq(api_key=key) if key else None

    def extract_json(self, text: str) -> Optional[dict]:
        try:
            return json.loads(text)
        except Exception:
            pass

        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except Exception:
                return None

        return None

    def _has_valid_shape(self, parsed: dict) -> bool:
        if not isinstance(parsed, dict):
            return False

        items = parsed.get("required_subsystems")
        if not isinstance(items, list) or len(items) == 0:
            return False

        for item in items:
            if not isinstance(item, dict):
                return False
            if not isinstance(item.get("name"), str):
                return False

        return True

    def _repair_plan(self, plan: dict) -> dict:
        repaired = []
        seen = set()

        for item in plan.get("required_subsystems", []):
            raw_name = item.get("name", "")
            reason = item.get("reason", "")

            parts = [p.strip() for p in re.split(r"[|/,]", raw_name)]

            for part in parts:
                if part in VALID_SUBSYSTEMS and part not in seen:
                    repaired.append({"name": part, "reason": reason})
                    seen.add(part)

        if "knowledge_lookup" not in seen:
            repaired.insert(
                0,
                {
                    "name": "knowledge_lookup",
                    "reason": "always required for cache check",
                },
            )

        return {"required_subsystems": repaired}

    def _call_groq(self, goal: str):
        if not self.client:
            raise RuntimeError("Groq API key not configured")

        return self.client.chat.completions.create(
            model=PLANNER_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": goal},
            ],
            temperature=0.2,
            max_tokens=400,
        )

    def create_plan(self, goal: str) -> dict:
        last_error = None
        last_raw_content = None

        for attempt in range(1, MAX_PLANNER_RETRIES + 1):
            try:
                response = self._call_groq(goal)
            except Exception as e:
                last_error = f"Planner API call failed: {e}"
                if attempt < MAX_PLANNER_RETRIES:
                    time.sleep(RETRY_BACKOFF_SECONDS * attempt)
                continue

            usage_dict = _usage_to_dict(response)
            content = response.choices[0].message.content
            last_raw_content = content

            parsed = self.extract_json(content)

            if not parsed or not self._has_valid_shape(parsed):
                last_error = (
                    "JSON parse failed" if not parsed else "JSON had unexpected shape"
                )
                if attempt < MAX_PLANNER_RETRIES:
                    time.sleep(RETRY_BACKOFF_SECONDS * attempt)
                continue

            result = self._repair_plan(parsed)
            result["_usage"] = usage_dict
            result["_model"] = PLANNER_MODEL
            return result

        return {
            **_FULL_FALLBACK,
            "error": last_error,
            "raw": last_raw_content,
            "_usage": None,
            "_model": PLANNER_MODEL,
        }