# img_gen/generator.py

import os
from google.genai import types

from .config import gemini_client, IMAGE_GEN_MODEL
from .selector import select_products_for_goal
from .prompt_builder import (
    build_image_prompt,
    refine_prompt_with_llm,
    build_gemini_contents
)
from .utils import (
    call_with_retry,
    save_generated_image,
    load_image_part
)

# Gemini's image_config only accepts a fixed set of aspect ratios, so each
# content type is mapped to the closest supported value. Keys are normalised
# to lowercase/stripped so lookups are tolerant of casing coming from the UI.
CONTENT_TYPE_ASPECT_RATIOS = {
    "instagram post": "1:1",
    "facebook post": "4:3",
    "poster": "3:4",
    "banner": "16:9",
    "a4 portrait": "3:4",
    "a4 landscape": "4:3",
    "a5 portrait": "3:4",
    "a5 landscape": "4:3",
    "none": "1:1",
}

DEFAULT_ASPECT_RATIO = "1:1"


def get_aspect_ratio_for_state(state) -> str:
    """Maps state.content_type (set by the UI/orchestrator) to a Gemini-
    supported aspect ratio string, falling back to a square image if the
    content type is missing or unrecognised."""
    content_type = (getattr(state, "content_type", None) or "").strip().lower()
    return CONTENT_TYPE_ASPECT_RATIOS.get(content_type, DEFAULT_ASPECT_RATIO)


def run_image_gen(state):
    try:
        # Select products automatically so the generated image reflects the
        # marketing goal without requiring manual product selection.
        product_selection = select_products_for_goal(state)
        state.logs.append(f"Selected products: {product_selection}")

        raw_prompt = build_image_prompt(state, product_selection)
        refined_prompt = refine_prompt_with_llm(raw_prompt)
        state.logs.append("Image prompt refined")


        contents, product_paths = build_gemini_contents(
            state,
            refined_prompt,
            product_selection
        )
        state.logs.append("Gemini multimodal payload created")

        aspect_ratio = get_aspect_ratio_for_state(state)
        state.logs.append(
            f"Using aspect ratio {aspect_ratio} for content type "
            f"'{getattr(state, 'content_type', None)}'"
        )

        response = call_with_retry(
            gemini_client.models.generate_content,
            _label="image_generation",
            model=IMAGE_GEN_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(aspect_ratio=aspect_ratio)
            )
        )
        state.logs.append("Gemini image generated")

        output_path, refusal_text = save_generated_image(response)

        if not output_path:
            reason = refusal_text or "no reason given by Gemini"
            raise Exception(f"Gemini returned no image data ({reason})")

        state.logs.append(f"Saved image: {output_path}")

        state.images = {
            "raw_prompt": raw_prompt,
            "refined_prompt": refined_prompt,
            "generated_output_path": output_path,
            "aspect_ratio": aspect_ratio,
            "style_reference": getattr(state, "style_reference_path", None),
            "product_references": product_paths,
            "product_selection": product_selection
        }

    except Exception as error:
        state.errors.append({
            "agent": "image_generator",
            "error": str(error)
        })

    return state


def apply_tweak(state, tweak_prompt: str):
    try:
        images = getattr(state, "images", {})
        current_image = images.get("generated_output_path")

        if not current_image:
            raise Exception("No generated image exists to edit")

        if not os.path.exists(current_image):
            raise Exception("Generated image file missing")

        contents = [
            f"""
Edit this existing generated image.

USER REQUEST:

{tweak_prompt}


Editing rules:

- Apply ONLY the requested change.
- Preserve the products exactly.
- Preserve packaging.
- Preserve lighting.
- Preserve camera angle.
- Preserve overall composition unless required.
- Keep the result photorealistic.
- Keep the Traybakes trade-catalogue photography style
  (bright, clean, not luxury/fine-dining styling).
""",
            load_image_part(current_image)
        ]

        aspect_ratio = images.get("aspect_ratio") or get_aspect_ratio_for_state(state)

        response = call_with_retry(
            gemini_client.models.generate_content,
            _label="image_tweak",
            model=IMAGE_GEN_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(aspect_ratio=aspect_ratio)
            )
        )

        output_path, refusal_text = save_generated_image(response)

        if not output_path:
            reason = refusal_text or "no reason given by Gemini"
            raise Exception(f"Gemini returned no image data for tweak ({reason})")

        state.images["generated_output_path"] = output_path
        state.images["aspect_ratio"] = aspect_ratio
        state.logs.append(f"Successfully applied tweak and saved to {output_path}")

    except Exception as error:
        state.errors.append({
            "agent": "image_tweak",
            "error": str(error)
        })

    return state