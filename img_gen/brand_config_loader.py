"""
img_gen_config/brand_config_loader.py

Standalone loader for brand_config.json — decouples client-specific
brand/product/format data from source code, so the image-generation
pipeline can (in principle) be pointed at a different client's config
without editing img_gen/data.py or img_gen/prompt_builder.py directly.

WHY THIS FILE IS SEPARATE FROM img_gen/data.py
-----------------------------------------------
This is deliberately delivered as a standalone module rather than a
direct edit to your existing img_gen/data.py, because I don't have the
current contents of that file in this conversation (its exact field
names for PRODUCTS / PRESENTATIONS / BRAND_IDENTITY / PHOTOGRAPHY_STYLE
/ FORMAT_CONTEXT may not match the template structure in
brand_config.json exactly). Editing it blind risks breaking working
code. Instead, this gives you a working, tested loader you can wire in
yourself with minimal, controlled changes — see INTEGRATION NOTES below.

USAGE (standalone, works immediately)
--------------------------------------
    from img_gen_config.brand_config_loader import load_brand_config

    config = load_brand_config()
    print(config["brand_identity"]["name"])
    print(config["products"]["flapjacks"]["description"])

You can also point it at a different client's config file entirely:

    config = load_brand_config("clients/other_client_config.json")

This is the concrete mechanism that makes the generality claim in your
dissertation literal and demonstrable: swapping brand_config.json for
a different file, with no source code changes, changes which brand the
image generator writes prompts for.

INTEGRATION NOTES (for actually wiring this into img_gen)
------------------------------------------------------------
In img_gen/data.py, wherever you currently have hardcoded constants
like:

    PRODUCTS = { ... }
    PRESENTATIONS = { ... }
    BRAND_IDENTITY = { ... }
    PHOTOGRAPHY_STYLE = { ... }
    FORMAT_CONTEXT = { ... }

Replace the hardcoded dict bodies with:

    from img_gen_config.brand_config_loader import load_brand_config
    _config = load_brand_config()

    PRODUCTS = _config["products"]
    PRESENTATIONS = _config["presentations"]
    BRAND_IDENTITY = _config["brand_identity"]
    PHOTOGRAPHY_STYLE = _config["photography_style"]
    FORMAT_CONTEXT = _config["format_context"]

You will likely need to adjust the KEY NAMES inside brand_config.json
(or add a small mapping step here) to match whatever field names your
current PRODUCTS/PRESENTATIONS dicts actually use internally (e.g. if
your code expects PRODUCTS["flapjacks"]["name"] rather than
["display_name"], either rename the JSON keys to match, or add a thin
translation layer in this loader). This file is intentionally a
starting point, not a drop-in replacement — 15-30 minutes of alignment
against your real data.py is expected, not a bug in this script.

VALIDATION
----------
load_brand_config() does basic structural validation (checks the
required top-level sections exist) and raises a clear error if the
JSON is malformed or a section is missing, rather than failing silently
deep inside a prompt-building function later.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "brand_config.json"

REQUIRED_TOP_LEVEL_SECTIONS = [
    "brand_identity",
    "photography_style",
    "format_context",
    "products",
    "presentations",
]


class BrandConfigError(Exception):
    """Raised when a brand config file is missing, malformed, or incomplete."""


def load_brand_config(path: str | Path | None = None) -> dict[str, Any]:
    """
    Loads and validates a brand config JSON file.

    Args:
        path: Optional path to a config file. Defaults to
              brand_config.json sitting alongside this loader. Pass a
              different path to point the image-generation pipeline at
              a different client's brand/product data entirely, with
              zero source code changes elsewhere in img_gen.

    Returns:
        The parsed config dict.

    Raises:
        BrandConfigError: if the file is missing, not valid JSON, or
                           missing a required top-level section.
    """
    config_path = Path(path) if path is not None else DEFAULT_CONFIG_PATH

    if not config_path.exists():
        raise BrandConfigError(f"Brand config file not found: {config_path}")

    try:
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        raise BrandConfigError(f"Brand config file is not valid JSON ({config_path}): {e}") from e

    missing = [section for section in REQUIRED_TOP_LEVEL_SECTIONS if section not in config]
    if missing:
        raise BrandConfigError(
            f"Brand config file ({config_path}) is missing required section(s): {missing}"
        )

    return config


def get_product(config: dict[str, Any], product_key: str) -> dict[str, Any]:
    """Convenience accessor with a clearer error than a raw KeyError."""
    products = config.get("products", {})
    if product_key not in products:
        raise BrandConfigError(
            f"Unknown product '{product_key}'. Available: {sorted(products.keys())}"
        )
    return products[product_key]


def get_format_context(config: dict[str, Any], format_key: str) -> dict[str, Any]:
    """Convenience accessor for aspect-ratio/format info by content type,
    e.g. get_format_context(config, 'instagram_post')."""
    formats = config.get("format_context", {})
    normalized_key = format_key.strip().lower().replace(" ", "_")
    if normalized_key not in formats:
        raise BrandConfigError(
            f"Unknown format '{format_key}'. Available: {sorted(formats.keys())}"
        )
    return formats[normalized_key]


if __name__ == "__main__":
    config = load_brand_config()
    print(f"Loaded brand config for: {config['brand_identity']['name']}")
    print(f"Products defined: {list(config['products'].keys())}")
    print(f"Formats defined:  {list(config['format_context'].keys())}")
    print("\nConfig loaded and validated successfully.")