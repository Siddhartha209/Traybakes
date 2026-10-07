import os
import re
import time
import uuid
from collections import Counter
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

CAPTION_MODEL = "openai/gpt-oss-120b"
NUM_CAPTIONS = 3

MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 2

FALLBACK_ANGLES = [
    "Focus on product quality and craftsmanship",
    "Focus on reliability and trust for repeat business",
    "Focus on limited availability or seasonal urgency",
    "Focus on the story and people behind the product",
    "Focus on value and suitability for the buyer's own customers",
]

OPENING_MOVES = [
    "Open with a concrete, sensory description of the product itself (texture, ingredient, how it's made) — no scene-setting phrase first.",
    "Open with a specific scenario: a moment a wholesale buyer or café owner would actually be in (restocking, a client visit, a busy morning service).",
    "Open with a plain, blunt statement of fact or offer — short sentence, no adjectives in the first clause.",
    "Open with a direct question aimed at the buyer's own problem (margins, shelf life, customer demand) — not a rhetorical flourish.",
    "Open by naming a specific, concrete detail (batch size, delivery window, an ingredient) before anything else.",
]

BANNED_PHRASES = [
    "indulge in",
    "sweet life",
    "a testament to",
    "little luxury",
    "elevate your",
    "treat yourself",
    "discover a sweeter way",
    "pick-me-up",
    "irresistible treats",
]

SIMILARITY_THRESHOLD = 0.5

STOPWORDS = {
    "the", "a", "an", "and", "or", "to", "of", "in", "for", "with", "your",
    "our", "is", "are", "it", "its", "on", "at", "you", "that", "this",
    "be", "as", "from", "we", "us", "today", "try", "them",
}

TONE_GUIDANCE = {
    "professional": (
        "Tone for this batch: Professional. Write with a polished, "
        "business-appropriate register — confident and precise, "
        "minimal contractions, no slang or jokes. Still concrete and "
        "specific, never stiff or corporate-jargon-heavy."
    ),
    "minimal": (
        "Tone for this batch: Minimal. Keep sentences very short and "
        "spare. Cut every word that isn't doing work — no adjectives "
        "unless they carry real information. Prefer fragments over "
        "full sentences where it still reads clearly."
    ),
    "warm": (
        "Tone for this batch: Warm. Write like a friendly, familiar "
        "voice from someone who knows the buyer — approachable and "
        "personable, but still specific and business-relevant, never "
        "saccharine or generic-sweet."
    ),
}


def build_system_prompt(tone=None):
    banned = "\n".join(f'- "{p}"' for p in BANNED_PHRASES)

    tone_key = (tone or "").strip().lower()
    tone_block = TONE_GUIDANCE.get(tone_key, "")

    return f"""
You are writing social media captions for Traybakes, a UK handmade
cake and traybake company. The audience is wholesale buyers and
independent cafés deciding whether to stock or reorder — not
consumers buying a single treat for themselves.

Voice:
- Write like someone who actually bakes and ships this product, not a
  generic ad agency. Be specific and concrete rather than sweeping.
- Speak business-to-business: buyers care about consistency, shelf
  life, margins, and whether their own customers will reorder — not
  vague "luxury" or "indulgence" language.
- Short, plain sentences. Cut any sentence that could be copy-pasted
  onto a different bakery's product with no changes.
- One clear CTA. Relevant hashtags, not generic ones.
{"" if not tone_block else f"""
{tone_block}
"""}
Do NOT use any of these phrases or close variants of them — they read
as generic AI marketing copy:
{banned}

Do not open two different captions in a batch with the same sentence
structure or the same first few words. If you are given a list of
captions already written in this batch, your caption must be
clearly different from all of them in both opening line and structure.
"""


def build_user_prompt(state, opportunity=None, opening_move=None, prior_captions=None):
    research = state.research or {}
    insights = research.get("insights", {})
    actions = research.get("actions", {})

    patterns = [p.get("name", "") for p in insights.get("patterns", [])[:3]]
    gaps = [g.get("name", "") for g in insights.get("gaps", [])[:3]]
    themes = actions.get("recommended_content_themes", [])[:3]

    context_lines = []
    if patterns:
        context_lines.append(f"Competitor patterns to differentiate from: {patterns}")
    if gaps:
        context_lines.append(f"Market gaps to exploit: {gaps}")
    if themes:
        context_lines.append(f"Recommended content themes: {themes}")

    context = (
        "\n".join(context_lines)
        if context_lines
        else "No research context available — write from goal alone."
    )

    opp_block = ""
    if opportunity:
        if isinstance(opportunity, dict):
            opp_name = opportunity.get("name", str(opportunity))
            opp_reason = opportunity.get("reason", "")
            opp_block = f"\nFOCUS OPPORTUNITY: {opp_name}\nWhy it matters: {opp_reason}"
        else:
            opp_block = f"\nFOCUS OPPORTUNITY: {opportunity}"

    opening_block = (
        f"\nREQUIRED OPENING MOVE FOR THIS CAPTION: {opening_move}"
        if opening_move
        else ""
    )

    tone = (getattr(state, "tone", None) or "").strip()
    tone_reminder_block = (
        f"\nTONE REMINDER: Write this caption in a {tone.lower()} tone, "
        "consistent with the tone instructions in the system prompt."
        if tone and tone.lower() != "none"
        else ""
    )

    reference_block = ""
    reference_captions = getattr(state, "reference_captions", None) or []
    if reference_captions:
        examples = "\n".join(f'- "{c}"' for c in reference_captions[:3])
        reference_block = (
            "\n\nPast captions this user particularly liked for similar campaigns. "
            "Match the underlying tone (how direct/warm/formal it is), "
            "but do not copy its sentence structure, opening line, or specific phrasing:\n"
            f"{examples}"
        )

    avoid_block = ""
    learned_avoid = getattr(state, "learned_avoid_phrases", None) or []
    if learned_avoid:
        avoid_list = "\n".join(f'- "{p}"' for p in learned_avoid[:10])
        avoid_block = (
            "\n\nThe user has manually edited phrasing like this out of "
            "past captions — do not use these or close variants:\n"
            f"{avoid_list}"
        )

    batch_block = ""
    if prior_captions:
        existing = "\n".join(f'- "{c}"' for c in prior_captions)
        batch_block = (
            "\n\nCaptions already written for this same batch — your "
            "caption must be clearly different from each of these, "
            "especially in the opening sentence:\n"
            f"{existing}"
        )

    return f"""
CAMPAIGN GOAL:

{state.goal}


MARKET CONTEXT:

{context}


{opp_block}

{opening_block}

{tone_reminder_block}

{reference_block}

{avoid_block}

{batch_block}


Write a single caption based on the above.

Return ONLY the caption.
No explanation.
"""


def _build_caption_slots(opportunities):
    slots = list(opportunities[:NUM_CAPTIONS])
    fallback_index = 0
    while len(slots) < NUM_CAPTIONS:
        slots.append(FALLBACK_ANGLES[fallback_index % len(FALLBACK_ANGLES)])
        fallback_index += 1
    return slots


def _build_opening_moves(count):
    return [OPENING_MOVES[i % len(OPENING_MOVES)] for i in range(count)]


def _normalized_words(caption):
    words = re.findall(r"[a-zA-Z']+", caption.lower())
    return {w for w in words if w not in STOPWORDS and len(w) > 2}


def word_overlap_ratio(caption_a, caption_b):
    words_a = _normalized_words(caption_a)
    words_b = _normalized_words(caption_b)

    if not words_a or not words_b:
        return 0.0

    intersection = words_a & words_b
    union = words_a | words_b

    return len(intersection) / len(union)


def _too_similar_to_any(caption, prior_captions):
    return any(
        word_overlap_ratio(caption, prior) >= SIMILARITY_THRESHOLD
        for prior in prior_captions
    )


def generate_caption(system_prompt, user_prompt):
    response = client.chat.completions.create(
        model=CAPTION_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,
        max_completion_tokens=1024,
        reasoning_effort="low",
    )

    usage = getattr(response, "usage", None)
    usage_dict = {
        "prompt_tokens": getattr(usage, "prompt_tokens", 0) if usage else 0,
        "completion_tokens": getattr(usage, "completion_tokens", 0) if usage else 0,
        "total_tokens": getattr(usage, "total_tokens", 0) if usage else 0,
    }
    content = (response.choices[0].message.content or "").strip()
    if not content:
        raise ValueError("Model returned empty content (likely reasoning-token exhaustion)")

    return response.choices[0].message.content.strip(), usage_dict


def generate_caption_with_retry(system_prompt, user_prompt, max_retries=MAX_RETRIES):
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            return generate_caption(system_prompt, user_prompt)
        except Exception as e:
            last_error = e
            if attempt < max_retries:
                time.sleep(RETRY_BACKOFF_SECONDS * attempt)

    raise last_error


def run_caption_gen(state):
    try:
        tone = getattr(state, "tone", None)
        system = build_system_prompt(tone)
        opportunities = []

        if state.research and "insights" in state.research:
            opportunities = state.research["insights"].get("opportunities", [])

        slots = _build_caption_slots(opportunities)
        opening_moves = _build_opening_moves(len(slots))

        captions = []
        feedback_items = []
        failed_slots = []

        token_log = state.metrics.setdefault("token_usage", [])
        generated_texts = []

        for slot, opening_move in zip(slots, opening_moves):
            try:
                prompt = build_user_prompt(
                    state,
                    slot,
                    opening_move,
                    generated_texts,
                )

                caption, usage = generate_caption_with_retry(system, prompt)

                if _too_similar_to_any(caption, generated_texts):
                    retry_prompt = (
                        prompt
                        + "\n\nYour previous attempt for this slot was too "
                        "similar in wording and structure to another caption "
                        "in this batch. Write a genuinely different caption — "
                        "different opening sentence, different structure."
                    )

                    caption, retry_usage = generate_caption_with_retry(
                        system, retry_prompt
                    )

                    usage = dict(Counter(usage) + Counter(retry_usage))

                caption_id = uuid.uuid4().hex

                captions.append({
                    "id": caption_id,
                    "opportunity": slot,
                    "caption": caption,
                })

                feedback_items.append({
                    "id": caption_id,
                    "caption": caption,
                    "rating": None,
                })

                generated_texts.append(caption)

                token_log.append({
                    "agent": "caption_generator",
                    "model": CAPTION_MODEL,
                    **usage,
                })

            except Exception as e:
                print(f"[caption_generator] slot failed: {slot!r} — {e}")
                failed_slots.append(str(slot))

        state.captions = captions
        state.feedback_items = feedback_items

        if failed_slots:
            state.errors.append({
                "agent": "caption_generator",
                "error": f"{len(failed_slots)} of {NUM_CAPTIONS} caption(s) failed after retries",
                "failed_slots": failed_slots,
            })

        state.logs.append(
            f"Generated {len(captions)} caption(s)"
            + (f", {len(failed_slots)} failed" if failed_slots else "")
        )

    except Exception as e:
        state.errors.append({
            "agent": "caption_generator",
            "error": str(e),
        })

    return state