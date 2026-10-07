# img_gen/prompt_builder.py

import os

from .config import groq_client, IMAGE_PROMPT_MODEL
from .data import BRAND_IDENTITY, PHOTOGRAPHY_STYLE, FORMAT_CONTEXT, PHOTOGRAPHY_STYLE_WITH_REFERENCE
from .utils import call_with_retry, load_image_part, get_product_image


def build_image_prompt(state, product_selection=None):
    chosen_presentations = set()
    chosen_products_line = ""

    if product_selection and product_selection.get("products"):
        chosen_products_line = "Products/formats to feature:\n" + "\n".join(
            f"- {item['product'].replace('_', ' ').title()} "
            f"({item['presentation'].replace('_', ' ')})"
            for item in product_selection["products"]
        )

        chosen_presentations = {
            item["presentation"]
            for item in product_selection["products"]
        }

    format_notes = "\n".join(
        FORMAT_CONTEXT[p]
        for p in chosen_presentations
        if p in FORMAT_CONTEXT
    )

    has_style_reference = bool(
        getattr(state, "style_reference_path", None)
    )

    photography_style = PHOTOGRAPHY_STYLE
    if has_style_reference:
        photography_style = PHOTOGRAPHY_STYLE_WITH_REFERENCE

    return f"""
Create a trade/wholesale product photograph for Traybakes.

PRIMARY MARKETING GOAL:

{state.goal}

{chosen_products_line}

{format_notes}

{BRAND_IDENTITY}

{photography_style}

STYLE REFERENCE IMAGE:

A style image may be provided. When present, match its lighting,
camera angle, composition, background treatment, mood, and colour
palette as closely as possible — treat it as the visual target for
how the shot should look and feel. This includes staging: if the
reference shows a hand holding the product, a prop, or a particular
surface/setting, replicate that staging in the final image too.

Do NOT copy:

- the actual food/product items shown
- any packaging, branding, or text visible in it

The products themselves must always come from the product reference
images, not the style image but presented/staged the way the style
image shows


PRODUCT REFERENCE IMAGES:

Reference images show the exact products.

Preserve exactly:

- packaging and clear wrap
- printed label design and colour
- shape
- textures
- toppings
- colours
- proportions


FINAL IMAGE:

- Realistic, appetising food/product photography
- Trade catalogue / wholesale advertising style — NOT fine-dining
  or luxury patisserie styling
- Bright, clean, professional studio lighting unless the style
  reference image indicates otherwise
- Suitable for a trade buyer's website, price list, or social media
- No text overlays
"""


def refine_prompt_with_llm(raw_prompt):
    response = call_with_retry(
        groq_client.chat.completions.create,
        _label="prompt_refiner",
        model=IMAGE_PROMPT_MODEL,
        messages=[
            {
                "role": "system",
                "content": """
You are the in-house art director for Traybakes, a British trade/
wholesale bakery in Cumbria that supplies cafes, delis, garden
centres, caterers and wholesalers. Their photography is bright,
clean, handmade-looking trade catalogue style — NOT luxury
patisserie or fine-dining styling.

Transform the provided brief into a detailed image generation
prompt. Keep every brand and photography-style constraint from the
brief intact — do not soften, drop, or genericise them (in
particular: do not introduce "luxury", "fine dining", moody
lighting, marble, or garnish plating; do not remove the trade/
wholesale framing).

If the brief includes a STYLE REFERENCE IMAGE section instructing you
to match a reference image's background/lighting/composition, that
instruction takes priority over any default background or lighting
description elsewhere in the brief — do not reintroduce a pale wood
or plain studio background if the brief says to follow a reference
image instead.

Describe concretely:

- camera and lens feel
- lighting
- composition and layout of the products
- surface/background
- materials and textures
- atmosphere

Return ONLY the final prompt.
"""
            },
            {
                "role": "user",
                "content": raw_prompt
            }
        ],
        temperature=0.6,
        max_completion_tokens=500
    )

    return response.choices[0].message.content.strip()


def build_gemini_contents(state, prompt, product_selection):
    contents = []
    product_paths = []

    contents.append(prompt)

    style_path = getattr(state, "style_reference_path", None)
    print(f"[img_gen] style_path: {style_path!r}, exists: {style_path and os.path.exists(style_path)}")
    if style_path and os.path.exists(style_path):
        contents.append(
            """
STYLE REFERENCE IMAGE:

This image shows the target photographic style. Match it closely for:

- lighting quality and direction
- camera angle and framing
- composition and layout
- background/surface treatment
- overall mood and atmosphere
- colour palette and colour grading
- staging elements: if the reference shows a hand holding/presenting
  the product, a prop, a surface the product rests on, or any other
  human/staging interaction, replicate that same staging in the final
  image 
Lean strongly into this image's visual style — the final photograph
should feel like it was shot in the same session, same setup, same
lighting rig as this reference.

Do NOT copy from this reference:

- the specific food/product items shown
- any packaging, branding, or text visible in it

The Traybakes products must come from the PRODUCT REFERENCE IMAGES
below, not from this style image — but everything about how the shot
is lit, framed, and composed should follow this reference.
"""
        )
        contents.append(load_image_part(style_path))

    if product_selection:
        contents.append(
            """
PRODUCT REFERENCE IMAGES:

These images show the exact
products that must appear.

Maintain:

- exact product identity
- packaging
- shape
- toppings
- colours
- proportions
- branding

Do not redesign the products.
"""
        )

        for item in product_selection["products"]:
            path = get_product_image(
                item["product"],
                item["presentation"]
            )

            contents.append(
                f"""
PRODUCT REFERENCE:

Product:
{item["product"]}

Presentation:
{item["presentation"]}
"""
            )

            contents.append(load_image_part(path))

            product_paths.append({
                "product": item["product"],
                "presentation": item["presentation"],
                "path": path
            })

    return contents, product_paths