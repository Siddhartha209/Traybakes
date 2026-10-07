# research_agent/json_utils.py


import json
import re


def clean_llm_text(text: str) -> str:
    """Strip markdown code fences that LLMs often wrap JSON responses in."""
    return (
        text
        .replace("```json", "")
        .replace("```", "")
        .strip()
    )


def repair_json(text: str) -> dict:
    """
    Best-effort JSON repair for common LLM output issues:
    - smart/curly quotes
    - single-quoted strings
    - trailing commas before } or ]
    """
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    text = re.sub(r"'([^']*)'", r'"\1"', text)
    text = re.sub(r",\s*([}\]])", r"\1", text)
    return json.loads(text)


def extract_json_object(raw_content: str, node_name: str = "node") -> dict:
    """
    Strip fences -> regex-extract the outermost {...} -> parse -> repair.

    This is the one JSON-recovery path every node should use. Raises
    ValueError (not a raw JSONDecodeError) if nothing recoverable is
    found, so callers/wrappers can catch a single predictable type.
    """
    content = clean_llm_text(raw_content)
    match = re.search(r"\{.*\}", content, re.DOTALL)

    if not match:
        raise ValueError(f"No JSON object found in {node_name} response:\n{raw_content}")

    candidate = match.group()

    try:
        return json.loads(candidate)
    except json.JSONDecodeError as e:
        try:
            return repair_json(candidate)
        except json.JSONDecodeError as e2:
            raise ValueError(
                f"Could not parse {node_name} JSON even after repair.\n"
                f"Error: {e2}\n"
                f"Raw content:\n{candidate}"
            ) from e2