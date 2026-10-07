# img_gen/data.py

PRODUCTS = {
    "all_butter_flapjack": "Traditional all butter flapjack.",
    "all_butter_flapjack_with_chocolate": "Traditional flapjack topped with chocolate.",
    "biscuit_tiffin": "Chocolate biscuit tiffin traybake.",
    "caramel_shortcake": "Shortbread base with caramel and chocolate.",
    "cinder_road": "Rocky road style traybake with marshmallows.",
    "dark_chocolate_brownie": "Rich dark chocolate brownie.",
    "granola_bar": "Healthy granola snack bar.",
    "honeycomb_crunch": "Chocolate traybake with honeycomb pieces.",
    "indulgent_flapjack": "Premium luxury flapjack.",
    "paradise_flapjack": "Fruit and coconut flapjack.",
    "peppermint_crunch": "Chocolate peppermint traybake.",
    "rocky_road": "Classic rocky road traybake.",
    "salted_caramel_brownie": "Brownie with salted caramel.",
    "vegan_flapjack": "Plant based flapjack."
}

PRESENTATIONS = {
    "tray": "Large catering tray for sharing.",
    "sharing_slice": "Wrapped sharing slice.",
    "stacked_sharing": "Multiple wrapped sharing slices stacked together.",
    "single_slice": "One individually wrapped slice.",
    "single_box": "Box containing multiple individually wrapped slices."
}

BRAND_IDENTITY = """
Brand: Traybakes — a specialist wholesale bakery based at the Food
Technology Centre, Redhills, Penrith, Cumbria, England. Established
over 25 years, supplying independent cafes, coffee shops, delis,
garden centres, artisan bakeries, catering companies and national
food wholesalers across the UK.

Brand positioning (all four must come through visually):
1. Handmade in small batches — not mass-produced, not machine-perfect.
   Slightly irregular tops, real ingredient texture, hand-finished look.
2. Traditional British recipes — nostalgic, homemade character rather
   than modern patisserie design.
3. Fresh, not frozen — bright, appetising, "just baked" feel, despite
   a long ambient shelf life.
4. Trade-focused — sold to businesses, not styled as a retail treat.
   The audience is a wholesale buyer deciding if this will sell well
   in their venue, not an end consumer being tempted to snack.

Tone: reliable, honest, unpretentious British craft baking. NOT a
fine-dining or luxury-patisserie aesthetic — avoid dark moody
restaurant lighting, sauce drizzles/garnish plating, marble surfaces,
gold leaf, or anything that reads as precious or fussy.
"""
#CHANGE THIS
PHOTOGRAPHY_STYLE = """
Photography style (matches Traybakes' own catalogue and trade
advertising):
- Bright, even, clean studio lighting — no dramatic shadows or moody
  restaurant-style lighting.
- Background: pale wood plank surface OR clean white/light studio
  background. Simple and uncluttered.
- Products individually wrapped in clear plastic film with a bold,
  colour-blocked printed paper label band across the top (each
  flavour has its own solid brand colour), exactly as supplied in
  the product reference images — the wrap must stay clearly visible,
  not removed or replaced with bare product.
- When multiple products/flavours appear, arrange them in a neat
  diagonal row or fan layout, slightly overlapping, front-facing to
  camera — the way a trade range/catalogue shot is composed, not a
  scattered lifestyle flat-lay.
- Photograph products straight-on or at a slight angle, at the same
  scale and eye-line as the reference images, so packaging and labels
  stay fully legible.
- Sharp focus across the whole product, food-styling-quality but not
  over-retouched — texture (oats, chocolate, caramel, fruit pieces)
  should read as genuinely handmade.
- No people, no cutlery, no plates unless specifically requested.
"""
PHOTOGRAPHY_STYLE_WITH_REFERENCE = """
Photography style (a style reference image has been provided — follow
its background, lighting, composition, and mood; the notes below are
constraints that still apply on top of that, not a replacement for it):

- Follow the style reference image for: background/surface, lighting
  quality and direction, camera angle, composition, and overall mood.
  Do NOT default to a plain pale wood or white studio background —
  use what the reference image shows instead.
- Products individually wrapped in clear plastic film with a bold,
  colour-blocked printed paper label band across the top (each
  flavour has its own solid brand colour), exactly as supplied in
  the product reference images — the wrap must stay clearly visible,
  not removed or replaced with bare product.
- When multiple products/flavours appear, arrange them in a neat
  diagonal row or fan layout, slightly overlapping, front-facing to
  camera — the way a trade range/catalogue shot is composed, not a
  scattered lifestyle flat-lay.
- Photograph products straight-on or at a slight angle, at the same
  scale and eye-line as the reference images, so packaging and labels
  stay fully legible.
- Sharp focus across the whole product, food-styling-quality but not
  over-retouched — texture (oats, chocolate, caramel, fruit pieces)
  should read as genuinely handmade.
- No people, no cutlery, no plates unless specifically requested.
- Still avoid fine-dining/luxury-patisserie styling (no marble, gold
  leaf, sauce drizzles/garnish plating) even when matching the
  reference's mood.
"""

FORMAT_CONTEXT = {
    "tray":
        "This is a pre-cut catering/foodservice tray (~14 portions). "
        "Frame it as it would appear in a catering display or "
        "foodservice setting — practical, generous, ready to serve.",

    "sharing_slice":
        "This is a larger sharing-format slice for a café or deli "
        "display cabinet. Frame it as it would sit in a counter "
        "display, appetising at a slight distance.",

    "stacked_sharing":
        "These are multiple wrapped sharing slices. Show them "
        "stacked or fanned together as they'd be merchandised in a "
        "deli or café counter display.",

    "single_slice":
        "This is a single individually wrapped grab-and-go bar, the "
        "kind sold at a café or coffee shop counter. Frame it as "
        "counter/grab-and-go merchandising.",

    "single_box":
        "This is a box of individually wrapped slices, suited to "
        "garden centre or gift-style retail. Frame it as a retail "
        "shelf or gift display piece."
}