# img_gen/utils.py

import os
import re
import time
import uuid
from google.genai import types

from .config import (
    PRODUCTS_DIR,
    OUTPUTS_DIR,
    MIN_MATCH_SCORE,
    MAX_RETRIES,
    RETRY_BACKOFF_SECONDS
)


def call_with_retry(
    fn,
    *args,
    _label="external_call",
    _max_retries=MAX_RETRIES,
    _backoff_seconds=RETRY_BACKOFF_SECONDS,
    **kwargs
):
    last_error = None

    for attempt in range(1, _max_retries + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as error:
            last_error = error

            if attempt < _max_retries:
                time.sleep(_backoff_seconds * attempt)

    raise last_error


def _normalise_words(text: str) -> set:
    if not text:
        return set()

    text = text.lower().replace("_", " ")
    return set(word for word in re.split(r"[^a-z0-9]+", text) if word)


def _fuzzy_match_key(candidate: str, valid_keys, min_score: float = MIN_MATCH_SCORE):
    candidate_words = _normalise_words(candidate)

    if not candidate_words:
        return None

    best_key, best_score = None, 0.0

    for key in valid_keys:
        key_words = _normalise_words(key)

        if not key_words:
            continue

        overlap = len(candidate_words & key_words)
        score = overlap / len(candidate_words)

        if score > best_score:
            best_key = key
            best_score = score

    return best_key if best_score >= min_score else None


def load_image_part(path: str):
    extension = os.path.splitext(path)[1].lower()
    mime = "image/png"

    if extension in [".jpg", ".jpeg"]:
        mime = "image/jpeg"
    elif extension == ".webp":
        mime = "image/webp"

    with open(path, "rb") as file:
        image_bytes = file.read()

    return types.Part.from_bytes(
        data=image_bytes,
        mime_type=mime
    )


def get_product_image(product: str, presentation: str):
    path = os.path.join(
        PRODUCTS_DIR,
        product,
        f"{presentation}.jpg"
    )

    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Missing product image: {path}"
        )

    return path


def save_generated_image(response):
    refusal_text_parts = []

    for candidate in response.candidates:
        for part in candidate.content.parts:
            if part.inline_data:
                image = part.as_image()
                filename = f"{uuid.uuid4()}.png"
                output_path = os.path.join(
                    OUTPUTS_DIR,
                    filename
                )
                image.save(output_path)

                return output_path, None

            elif getattr(part, "text", None):
                refusal_text_parts.append(part.text)

    refusal_text = " ".join(refusal_text_parts).strip() or None
    return None, refusal_text