# img_gen/selector.py

import json

from .config import groq_client, PRODUCT_SELECTOR_MODEL, MAX_PRODUCT_IMAGES
from .data import PRODUCTS, PRESENTATIONS
from .exceptions import InvalidProductSelectionError
from .utils import call_with_retry, _fuzzy_match_key, get_product_image


def select_products_for_goal(state):
    product_catalogue = "\n".join(
        f"- {name}: {description}"
        for name, description in PRODUCTS.items()
    )

    presentation_catalogue = "\n".join(
        f"- {name}: {description}"
        for name, description in PRESENTATIONS.items()
    )

    prompt = f"""
You are selecting product reference images
for Traybakes, a UK trade/wholesale bakery
(cafes, delis, garden centres, caterers, wholesalers).

Marketing goal:

{state.goal}


Available products:

{product_catalogue}


Available presentations:

{presentation_catalogue}


Rules:

1. Select between 1 and {MAX_PRODUCT_IMAGES} references.

2. Only use products from the available list.

3. Only use presentation names from the available list.

4. Choose the most visually appropriate presentation for the
   trade buyer/context implied by the goal.

Guidelines:

- Catering, foodservice, events:
   Prefer tray.

- Cafe/deli counter display:
   Prefer sharing_slice or stacked_sharing.

- Garden centre, gift, retail shelf:
   Prefer single_box.

- Grab-and-go, coffee shop counter, individual snacking:
   Prefer single_slice.

- Product range / variety features:
   Choose multiple different products.

- Never select more than {MAX_PRODUCT_IMAGES} images.


Return ONLY valid JSON.


Example:

{{
    "products": [
        {{
            "product": "dark_chocolate_brownie",
            "presentation": "tray"
        }}
    ]
}}
"""

    response = call_with_retry(
        groq_client.chat.completions.create,
        _label="product_selector",
        model=PRODUCT_SELECTOR_MODEL,
        messages=[
            {
                "role": "system",
                "content": "Return only valid JSON. No explanation."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.2,
        response_format={
            "type": "json_object"
        }
    )

    try:
        selection = json.loads(
            response.choices[0].message.content
        )
    except Exception:
        raise InvalidProductSelectionError(
            "Groq returned invalid product JSON"
        )

    if "products" not in selection:
        raise InvalidProductSelectionError(
            "Missing products key"
        )

    selection["products"] = selection["products"][:MAX_PRODUCT_IMAGES]

    validated = []
    rejected = []

    for item in selection["products"]:
        raw_product = item.get("product")
        raw_presentation = item.get("presentation")

        product = (
            raw_product
            if raw_product in PRODUCTS
            else _fuzzy_match_key(raw_product, PRODUCTS.keys())
        )

        presentation = (
            raw_presentation
            if raw_presentation in PRESENTATIONS
            else _fuzzy_match_key(raw_presentation, PRESENTATIONS.keys())
        )

        if not product or not presentation:
            rejected.append({
                "raw_product": raw_product,
                "raw_presentation": raw_presentation,
                "reason": (
                    "no catalogue match for product"
                    if not product
                    else "no catalogue match for presentation"
                ),
            })
            continue

        try:

            get_product_image(product, presentation)
        except FileNotFoundError:
            rejected.append({
                "raw_product": raw_product,
                "raw_presentation": raw_presentation,
                "reason": (
                    f"no reference image on disk for "
                    f"{product}/{presentation}"
                ),
            })
            continue

        validated.append({
            "product": product,
            "presentation": presentation
        })

    if not validated:
        raise InvalidProductSelectionError(
            f"No valid products selected (rejected: {rejected})"
        )

    return {
        "products": validated,
        "rejected": rejected
    }