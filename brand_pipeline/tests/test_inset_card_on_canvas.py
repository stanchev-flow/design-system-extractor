#!/usr/bin/env python3
"""Regression tests for the INSET-CARD-ON-CANVAS card fidelity batch (2026-07).

The hubspot-v3 feature-card grid ("Growing a business is hard…") captured the
signature "white cards with 8–12px radius and hairline border on a warm canvas"
(surfaceGrammar.cardOn + a Container-scheme surface role) but the renderer dropped
it: plated cards painted the generic page-panel token (== the section canvas) with
NO border, the product glyph stacked ABOVE the title, and the captured header rule
never rendered. These tests pin the fact-gated fixes in ``compose_features_cards``
+ ``SCAFFOLD_CARD_PLATE_CSS``:

  - CARD SURFACE: a brand whose Container surface role is DISTINCT from the page
    panel re-points --c-card-plate-bg at that role's own surface var; a brand whose
    container role already IS the page panel (surface/panel) emits no override.
  - CARD OUTLINE: a container surface declaring a resting ``border`` fact draws a
    hairline via --c-card-plate-border; absent ⇒ ``border: none`` (byte-identical).
  - INLINE ICON: a card device ``slots.icon.placement: heading-row`` seats the glyph
    beside the title in one flex headrow; absent ⇒ the stacked mark row.
  - HEADER DIVIDER: a card device ``headerDivider`` rules a hairline between the
    icon+title header and the body; absent ⇒ no rule.

Run:  ./venv/bin/python -m unittest brand_pipeline.tests.test_inset_card_on_canvas
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

_BRAND_PIPELINE = Path(__file__).resolve().parent.parent
if str(_BRAND_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_BRAND_PIPELINE))

import compose_section as cs   # noqa: E402
import component_render as cr  # noqa: E402


def _doc(*, container_role="surface/white", container_border=True,
         icon_placement="heading-row", header_divider=True):
    """A minimal card brand: a warm page canvas + a distinct white Container surface,
    a card device carrying the inline-icon + header-divider grammar. Each fact is a
    keyword arg so a test can drop ONE and prove that sub-element degrades alone."""
    surfaces = {
        "surface/primary": {"bg": "#fcfcfa", "textPrimary": "text/on-primary"},
    }
    surf = {"bg": "#ffffff", "schemeMode": "Container", "textPrimary": "text/on-primary"}
    if container_border:
        surf["border"] = "hairline"
    surfaces[container_role] = surf
    card_dev: dict = {"origin": "extracted", "variants": ["icon-card"]}
    if header_divider:
        card_dev["headerDivider"] = "hairline"
    if icon_placement:
        card_dev["slots"] = {"icon": {"placement": icon_placement, "size": "1.5rem"}}
    return {
        "brand": {"name": "Fixture"},
        "blocks": {"card": card_dev},
        "tokens": {
            "colors": {
                "text/on-primary": {"value": "#1f1f1f"},
                "text/on-inverse": {"value": "#ffffff"},
            },
            "surfaces": surfaces,
            "type": {"body": {"family": "Inter", "sizeRem": {"base": 1.0}}},
            "spacing": {},
        },
        # tag the card glyph as a device-frame MARK so the feature-card anatomy
        # (mark row / heading-row) path is taken, not a media well.
        "_mediaAssetsFit": {"icon-a.svg": "mark"},
    }


CARDS = [
    {"heading": "Marketing Hub", "body": "Attract and convert the right leads.",
     "link": "Learn more", "asset": "icon-a.svg", "alt": "icon a"},
    {"heading": "Sales Hub", "body": "Generate quality leads and close deals.",
     "link": "Learn more", "asset": "icon-a.svg", "alt": "icon a"},
]


def _compose(doc, layout=None):
    layout = layout or {"id": "t", "archetype": "cards"}
    ctx = cr.make_context(doc, "surface/primary",
                          doc["tokens"]["surfaces"]["surface/primary"])
    saved = cs.LAYOUT_COPY
    try:
        cs.LAYOUT_COPY = {**cs.LAYOUT_COPY,
                          layout["id"]: {"eyebrow": "", "heading": "Grid",
                                         "cards": CARDS}}
        return cs.compose_features_cards(doc, layout, ctx, [], None)
    finally:
        cs.LAYOUT_COPY = saved


class CardPlateCssContractTest(unittest.TestCase):
    """The scaffold plate CSS resolves the fill + outline through fact-gated vars that
    default to the historical behavior (page-panel fill, no border)."""

    def test_plate_bg_rides_card_plate_var_with_panel_fallback(self):
        self.assertIn("background: var(--c-card-plate-bg, var(--c-panel));",
                      cs.SCAFFOLD_CARD_PLATE_CSS)

    def test_plate_border_rides_card_plate_var_defaulting_none(self):
        self.assertIn("border: var(--c-card-plate-border, none); }",
                      cs.SCAFFOLD_CARD_PLATE_CSS)

    def test_header_divider_rule_rides_plate_hairline(self):
        self.assertIn(".cs-modules .cs-module-divider { border: 0; height: 0;\n"
                      "  border-top: 1px solid var(--c-hairline); width: 100%; }",
                      cs.SCAFFOLD_CARD_PLATE_CSS)


class CardSurfaceOverrideTest(unittest.TestCase):
    def test_distinct_container_surface_repoints_plate_bg(self):
        html = _compose(_doc(container_role="surface/white"))
        self.assertIn("--c-card-plate-bg: var(--surface-surface-white)", html)

    def test_container_equal_to_page_panel_emits_no_bg_override(self):
        # a brand whose Container role IS the page panel (surface/panel drives
        # --c-panel already) must not emit a redundant override → byte-identical.
        html = _compose(_doc(container_role="surface/panel"))
        self.assertNotIn("--c-card-plate-bg:", html)
        # …and the plate still renders (the grid is plated on its container surface).
        self.assertIn("cs-module--plate", html)

    def test_border_fact_draws_hairline_outline(self):
        html = _compose(_doc(container_border=True))
        self.assertIn("--c-card-plate-border: 1px solid var(--c-panel-hairline)", html)

    def test_no_border_fact_leaves_plate_borderless(self):
        html = _compose(_doc(container_border=False))
        self.assertNotIn("--c-card-plate-border:", html)

    def test_explicit_css_border_value_rides_verbatim(self):
        doc = _doc()
        doc["tokens"]["surfaces"]["surface/white"]["border"] = "2px solid #abcdef"
        html = _compose(doc)
        self.assertIn("--c-card-plate-border: 2px solid #abcdef", html)


class CardInlineIconTest(unittest.TestCase):
    def test_heading_row_seats_icon_beside_title(self):
        html = _compose(_doc(icon_placement="heading-row"))
        self.assertIn("cs-module-headrow", html)
        card = html.split("</article>")[0]
        # icon figure precedes the heading inside the headrow
        self.assertLess(card.index("cs-module-media--mark"), card.index("c-heading--h3"))

    def test_no_placement_keeps_stacked_mark_row(self):
        html = _compose(_doc(icon_placement=None))
        self.assertNotIn("cs-module-headrow", html)
        # the glyph still renders as a mark figure, just stacked above the title
        self.assertIn("cs-module-media--mark", html)


class CardHeaderDividerTest(unittest.TestCase):
    def test_divider_renders_between_header_and_body(self):
        html = _compose(_doc(header_divider=True))
        self.assertEqual(html.count('class="cs-module-divider"'), len(CARDS))
        card = html.split("</article>")[0]
        self.assertLess(card.index("cs-module-headrow"), card.index("cs-module-divider"))
        self.assertLess(card.index("cs-module-divider"), card.index("c-paragraph"))

    def test_no_divider_fact_renders_no_rule(self):
        html = _compose(_doc(header_divider=False))
        self.assertNotIn("cs-module-divider", html)


if __name__ == "__main__":
    unittest.main()
