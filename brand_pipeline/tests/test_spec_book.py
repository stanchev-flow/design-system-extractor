#!/usr/bin/env python3
"""Unit tests for the P1.2 spec-book chapters (render_components_preview.py Tier 0).

Covers, per chapter: renders purely from brand.yaml data with monospace key
citations; degrades to EMPTY (or an explicit not-observed panel) when the brand
lacks the axis — never invented values.

  - color:   family grouping from the brand's own `<family>/<name>` role prefixes;
  - type:    authored tier ladders (rem = px per breakpoint), measured tier stamps
             (tokens.type.<role>.tiers), singleTierConfirmed marker, canonical-tier
             note, families+scale shape normalization;
  - spacing: relational X-to-Y rungs only (never the section-y rhythm tokens),
             true-size gap bars, relationalLadder notObserved panel;
  - radius:  tokens.radius tiles with spacing.radius-global fallback;
  - motion:  duration/easing/signature-move ladders + live demo CSS from
             tokens.motion values verbatim; notObserved panel; absent ⇒ empty;
  - buttons × surfaces: one band per declared surface role, each carrying every
             button family's state row (filled brand) or the arrow-link device
             (typographic brand);
  - build_spec_book: assembles only non-empty chapters; empty brand ⇒ no tier.

Run:  ./venv/bin/python -m unittest brand_pipeline.tests.test_spec_book
"""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

_BRAND_PIPELINE = Path(__file__).resolve().parent.parent
if str(_BRAND_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_BRAND_PIPELINE))

import render_components_preview as rcp  # noqa: E402
from tests.test_tokens_css import FIXTURE, FIXTURE_SCALE  # noqa: E402

# Mined-shape motion block (tokens.motion, the C13 contract) — values distinct from
# any live brand.
_MOTION = {
    "durations": {
        "state": {"value": "150ms", "census": 4, "role": "state shifts"},
        "reveal": {"value": "300ms", "census": 2, "role": "panel reveals"},
        "expressive": {"value": "800ms", "census": 1, "role": "card reveals"},
    },
    "easings": [
        {"value": "cubic-bezier(0, 0, .2, 1)", "census": 3, "use": "enter"},
        {"value": "ease", "census": 2, "use": "default"},
    ],
    "signatureMoves": [
        {"name": "arrow-swap", "move": "icon exits right, re-enters left",
         "timing": "300ms enter / 250ms exit", "sourceSelectors": [".btn .icon"]},
    ],
    "reducedMotion": {"value": "declared", "role": "12 rules measured"},
    "provenance": [{"source": "computed", "detail": "fixture"}],
}


def _doc(**over):
    doc = copy.deepcopy(FIXTURE)
    doc.update(over)
    return doc


def _tokens(doc, key, value):
    doc["tokens"][key] = value
    return doc


class TestColorChapter(unittest.TestCase):
    def test_groups_by_role_prefix_families(self):
        html = rcp.spec_color_chapter(_doc())
        # FIXTURE colors live in text/, border/, accent/ families
        for fam in ("text", "border", "accent"):
            self.assertIn(f"tokens.colors.{fam}/*", html)
        self.assertIn("#10141A", html)          # hex label rendered
        self.assertIn("spec-chip", html)

    def test_empty_without_colors(self):
        doc = _doc()
        doc["tokens"]["colors"] = {}
        self.assertEqual(rcp.spec_color_chapter(doc), "")

    def test_valueless_entries_skip(self):
        doc = _doc()
        doc["tokens"]["colors"]["accent/valueless-probe"] = {"role": "no value carried"}
        html = rcp.spec_color_chapter(doc)
        self.assertNotIn("valueless-probe", html)


class TestTypeChapter(unittest.TestCase):
    def test_tier_ladder_rem_px_annotations(self):
        html = rcp.spec_type_chapter(_doc())
        # display-hero ladder: base 5.5rem = 88px … mobile 2.75rem = 44px
        self.assertIn("base 5.5rem = 88px", html)
        self.assertIn("mobile 2.75rem = 44px", html)
        self.assertIn("tokens.type.display-hero", html)

    def test_measured_tier_stamps_and_single_tier_marker(self):
        doc = _doc()
        doc["meta"] = {"canonicalTier": {"viewport": 1440, "label": "base"}}
        doc["tokens"]["type"]["h1"]["tiers"] = {
            "w1440": {"px": 56, "source": "computed"},
            "w375": {"px": 32, "source": "computed"},
        }
        doc["tokens"]["type"]["body"]["singleTierConfirmed"] = True
        html = rcp.spec_type_chapter(doc)
        self.assertIn("1440px→56px", html)
        self.assertIn("375px→32px", html)
        self.assertIn("(computed)", html)
        self.assertIn("singleTierConfirmed", html)
        self.assertIn("meta.canonicalTier", html)

    def test_marker_entries_skip(self):
        doc = _doc()
        doc["tokens"]["type"]["headingEmphasis"] = {
            "notObserved": True, "reason": "no strong/b in headings"}
        html = rcp.spec_type_chapter(doc)
        self.assertNotIn("headingEmphasis", html)

    def test_families_scale_shape_normalizes(self):
        html = rcp.spec_type_chapter(copy.deepcopy(FIXTURE_SCALE))
        self.assertIn("tokens.type.display-01", html)
        self.assertIn("base 5.5rem = 88px", html)

    def test_empty_without_type(self):
        doc = _doc()
        doc["tokens"]["type"] = {}
        self.assertEqual(rcp.spec_type_chapter(doc), "")


class TestSpacingChapter(unittest.TestCase):
    def test_relational_rungs_only(self):
        html = rcp.spec_spacing_chapter(_doc())
        self.assertIn("eyebrow-to-heading", html)
        self.assertIn("1.5rem = 24px", html)
        # rhythm tokens are NOT relational rungs
        self.assertNotIn("section-y-major", html)
        self.assertNotIn("radius-global", html)
        self.assertIn("spec-gap-demo", html)     # true-size bar rendered

    def test_mode_ladder_annotation(self):
        doc = _doc()
        doc["tokens"]["spacing"]["eyebrow-to-heading"]["modeLadder"] = {
            "base": "1.5rem", "mobile": "1rem"}
        html = rcp.spec_spacing_chapter(doc)
        self.assertIn("base 1.5rem = 24px", html)
        self.assertIn("mobile 1rem = 16px", html)

    def test_not_observed_panel(self):
        doc = _doc()
        doc["tokens"]["spacing"] = {
            "section-y-major": {"value": "7.5rem"},
            "relationalLadder": {"notObserved": True,
                                 "reason": "single flat section"},
        }
        html = rcp.spec_spacing_chapter(doc)
        self.assertIn("not observed", html)
        self.assertIn("single flat section", html)
        self.assertIn("tokens.spacing.relationalLadder", html)
        self.assertNotIn("spec-gap-demo", html)

    def test_empty_without_rungs_or_marker(self):
        doc = _doc()
        doc["tokens"]["spacing"] = {"section-y-major": {"value": "7.5rem"}}
        self.assertEqual(rcp.spec_spacing_chapter(doc), "")


class TestRadiusChapter(unittest.TestCase):
    def test_tokens_radius_tiles(self):
        doc = _tokens(_doc(), "radius", {
            "card": {"value": "0.75rem", "var": "--fx-radius-x3"},
            "button": {"value": "2.5rem"},
        })
        html = rcp.spec_radius_chapter(doc)
        self.assertIn("card — 0.75rem = 12px", html)
        self.assertIn("button — 2.5rem = 40px", html)
        self.assertIn("tokens.radius.card", html)
        self.assertIn("--fx-radius-x3", html)

    def test_radius_global_fallback(self):
        html = rcp.spec_radius_chapter(_doc())   # FIXTURE: spacing.radius-global only
        self.assertIn("global — 0.375rem = 6px", html)
        self.assertIn("tokens.spacing.radius-global", html)

    def test_empty_without_any_radius(self):
        doc = _doc()
        doc["tokens"]["spacing"].pop("radius-global")
        self.assertEqual(rcp.spec_radius_chapter(doc), "")


class TestMotionChapter(unittest.TestCase):
    def test_ladder_easings_moves_demos(self):
        doc = _tokens(_doc(), "motion", copy.deepcopy(_MOTION))
        html = rcp.spec_motion_chapter(doc)
        self.assertIn("duration ladder (3 tiers)", html)
        self.assertIn("150ms", html)
        self.assertIn("tokens.motion.durations", html)
        self.assertIn("cubic-bezier(0, 0, .2, 1)", html)
        self.assertIn("spec-ease-curve", html)   # SVG curve preview
        self.assertIn("arrow-swap", html)
        self.assertIn(".btn .icon", html)        # sourceSelectors citation
        self.assertIn("live timing demos", html)
        self.assertIn("durations.state", html)
        self.assertIn("pending (P2 renderer work)", html)
        self.assertIn("prefers-reduced-motion", html)

    def test_demo_css_carries_brand_values_verbatim(self):
        doc = _tokens(_doc(), "motion", copy.deepcopy(_MOTION))
        css = rcp.spec_motion_css(doc)
        self.assertIn("150ms", css)              # state tier
        self.assertIn("300ms", css)              # reveal tier
        self.assertIn("800ms", css)              # wash rides longest tier
        self.assertIn("cubic-bezier(0, 0, .2, 1)", css)

    def test_demo_timing_falls_back_positionally(self):
        # ladder without the conventional names: shortest/middle/longest picked
        motion = {"durations": {"a": {"value": "100ms"}, "b": {"value": "200ms"},
                                "c": {"value": "400ms"}}}
        t = rcp._demo_timing(motion)
        self.assertEqual(t["state"], ("a", "100ms"))
        self.assertEqual(t["wash"], ("c", "400ms"))
        self.assertEqual(t["ease"], "ease")      # easing-less ladder: browser default

    def test_not_observed_panel_and_no_css(self):
        doc = _tokens(_doc(), "motion",
                      {"notObserved": True, "reason": "static capture"})
        html = rcp.spec_motion_chapter(doc)
        self.assertIn("not observed", html)
        self.assertIn("static capture", html)
        self.assertEqual(rcp.spec_motion_css(doc), "")

    def test_absent_motion_empty(self):
        self.assertEqual(rcp.spec_motion_chapter(_doc()), "")
        self.assertEqual(rcp.spec_motion_css(_doc()), "")


class TestButtonsSurfacesChapter(unittest.TestCase):
    def test_every_surface_gets_every_family_row(self):
        html = rcp.spec_buttons_surfaces_chapter(_doc())
        # FIXTURE declares 4 surface roles; each band carries the primary family row
        self.assertEqual(html.count("spec-band-head"), 4)
        for role in FIXTURE["tokens"]["surfaces"]:
            self.assertIn(f"tokens.surfaces.{role}", html)
            self.assertIn(f'data-surface-frame="{role}"', html)
        self.assertEqual(html.count("buttons.primary ·"), 4)
        self.assertIn("btnf-primary", html)      # filled state row specimens
        self.assertIn("· dark", html)            # dark bands labeled

    def test_typographic_brand_rides_arrow_link(self):
        doc = _doc()
        doc.pop("buttons")
        doc["styleLaws"] = {"ctaShape": {"value": "text"}}
        html = rcp.spec_buttons_surfaces_chapter(doc)
        self.assertEqual(html.count("spec-band-head"), 4)
        self.assertNotIn("btnf-", html)

    def test_empty_without_surfaces(self):
        doc = _doc()
        doc["tokens"]["surfaces"] = {}
        self.assertEqual(rcp.spec_buttons_surfaces_chapter(doc), "")


class TestBuildSpecBook(unittest.TestCase):
    def test_assembles_present_chapters(self):
        doc = _tokens(_doc(), "motion", copy.deepcopy(_MOTION))
        html = rcp.build_spec_book(doc)
        self.assertIn('id="tier-specbook"', html)
        for anchor in ("spec-color", "spec-type", "spec-spacing", "spec-radius",
                       "spec-motion", "spec-buttons-surfaces"):
            self.assertIn(f'id="{anchor}"', html)

    def test_absent_axes_self_omit(self):
        doc = _tokens(_doc(), "motion", None)    # motion-less brand
        html = rcp.build_spec_book(doc)
        self.assertIn('id="spec-color"', html)
        self.assertNotIn('id="spec-motion"', html)

    def test_empty_brand_no_tier(self):
        self.assertEqual(
            rcp.build_spec_book({"brand": {"name": "X"}, "tokens": {}}), "")


if __name__ == "__main__":
    unittest.main()
