#!/usr/bin/env python3
"""Regression tests for the split MARK-ROW batch (hubspot-v2 2026-07):

  - LOGO LIST EXPANSION (`composition_to_layout` bespoke branch): a split/collage
    section whose logo-contract slot carries list copy expands per-item (AS-33
    evidence routing, same as generic-flow) instead of folding to one empty entry.
  - BOUND MARK RUN (`compose_info_band`): a split whose media slot bound a run of
    marks renders that mark row in the media half — never invented editorial art;
    a measured `_logoScale` entry draws the aspect-weighted scaled row; award-badge
    filename families ride the brand's badge tier.
  - SLOT MEDIA-ASPECT FALLBACK (`_cards_copy`): a module slot's declared
    `mediaAspect` becomes the per-card aspect fallback (a module's own wins).
  - SVG ASPECTS (`_asset_aspects`): vector marks resolve width/height from their
    own viewBox (PIL cannot open SVGs).
  - EDGE-CUT FIT IS FACT-FIRST (`compose_features_cards`): a DECLARED `fit:
    contain` keeps the contained media WELL on the edge-cut track (mark anatomy
    only for declared `fit: mark` or the undeclared mark-filename compat path).

Run:  ./venv/bin/python -m unittest brand_pipeline.tests.test_split_mark_row
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_BRAND_PIPELINE = Path(__file__).resolve().parent.parent
if str(_BRAND_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_BRAND_PIPELINE))

import compose_from_composition as cfc  # noqa: E402
import compose_section as cs            # noqa: E402
import component_render as cr           # noqa: E402

FIXTURE_DOC = {
    "brand": {"name": "Fixture"},
    "tokens": {
        "colors": {
            "text/on-primary": {"value": "#111111"},
            "text/on-inverse": {"value": "#ffffff"},
        },
        "surfaces": {
            "surface/primary": {"bg": "#ffffff", "textPrimary": "text/on-primary"},
        },
        "type": {"body": {"family": "Inter", "sizeRem": {"base": 1.0}}},
        "spacing": {},
    },
}


def _ctx():
    return cr.make_context(FIXTURE_DOC, "surface/primary",
                           FIXTURE_DOC["tokens"]["surfaces"]["surface/primary"])


def _split_section(media_copy):
    return {
        "id": "band", "archetype": "split", "useCase": "banner",
        "slots": [
            {"name": "heading", "contract": "heading",
             "copy": {"heading": "Voted #1"}},
            {"name": "media", "contract": "logo", "copy": media_copy},
        ],
    }


# ── logo list expansion in the bespoke (split/collage) mapping ──────────────────────

class SplitLogoMappingTest(unittest.TestCase):
    ITEMS = [{"asset": {"src": "assets/048-badge-a.png"}, "alt": "badge a"},
             {"asset": {"src": "assets/049-badge-b.png"}, "alt": "badge b"}]

    def test_list_copy_logo_slot_expands_per_item(self):
        layout = cfc.composition_to_layout(_split_section(self.ITEMS))
        logos = [m for m in layout["blockMapping"] if m.get("contract") == "logo"]
        self.assertEqual(len(logos), 2)
        self.assertEqual(logos[0]["usage"]["src"], "assets/048-badge-a.png")
        # the source-slot group rides along (per-slot strip rows)
        self.assertEqual({m.get("group") for m in logos}, {"media"})

    def test_scalar_slots_keep_the_fold(self):
        layout = cfc.composition_to_layout(_split_section(self.ITEMS))
        heads = [m for m in layout["blockMapping"] if m.get("contract") == "heading"]
        self.assertEqual(len(heads), 1)

    def test_single_logo_slot_unchanged(self):
        sec = _split_section(None)
        sec["slots"][1]["asset"] = {"src": "assets/048-badge-a.png"}
        layout = cfc.composition_to_layout(sec)
        logos = [m for m in layout["blockMapping"] if m.get("contract") == "logo"]
        self.assertEqual(len(logos), 1)


# ── bound mark run in the info-band media half ──────────────────────────────────────

def _logo_frags():
    return [
        {"slot": "logo-strip", "role": "logo item", "contract": "logo",
         "group": "media",
         "html": '<a class="c-logo c-logo--img" href="#">'
                 '<img class="c-logo-img" src="assets/048-badge-a.png" alt="a"></a>'},
        {"slot": "logo-strip", "role": "logo item", "contract": "logo",
         "group": "media",
         "html": '<a class="c-logo c-logo--img" href="#">'
                 '<img class="c-logo-img" src="assets/049-badge-b.png" alt="b"></a>'},
    ]


def _info_band(layout, rendered):
    saved = cs.LAYOUT_COPY
    try:
        cs.LAYOUT_COPY = {**cs.LAYOUT_COPY,
                          layout["id"]: {"eyebrow": "", "heading": "Voted #1",
                                         "panelTitle": "", "rows": [], "cta": "",
                                         "body": "", "headingLevel": ""}}
        return cs.compose_info_band(FIXTURE_DOC, layout, _ctx(), rendered, None)
    finally:
        cs.LAYOUT_COPY = saved


class InfoBandMarkRowTest(unittest.TestCase):
    def test_bound_marks_render_no_invented_art(self):
        html = _info_band({"id": "band"}, _logo_frags())
        self.assertIn("cs-logo-strip", html)
        self.assertIn("assets/048-badge-a.png", html)
        # never the invented editorial-photography default over bound marks
        self.assertNotIn("editorial photography", html)
        # a flex strip, not an image frame
        self.assertNotIn("c-image-mask", html.split("cs-split-body")[0])

    def test_measured_scale_draws_weighted_row(self):
        layout = {"id": "band",
                  "_logoScale": {"media": {"fraction": 0.52, "gap": "0.75rem",
                                           "aspects": {"048-badge-a.png": 0.9,
                                                       "049-badge-b.png": 0.9}}}}
        html = _info_band(layout, _logo_frags())
        self.assertIn("cs-logo-strip--scaled", html)
        # container fraction doubles inside the 6-of-12-column media half (clamped)
        self.assertIn("--cs-strip-fraction: 1;", html)
        self.assertIn("--cs-strip-gap: 0.75rem;", html)
        self.assertIn("flex: 0.9 1 0", html)

    def test_partial_aspects_degrade_to_plain_row(self):
        layout = {"id": "band",
                  "_logoScale": {"media": {"fraction": 0.52,
                                           "aspects": {"048-badge-a.png": 0.9}}}}
        html = _info_band(layout, _logo_frags())
        self.assertNotIn("cs-logo-strip--scaled", html)
        self.assertIn("cs-logo-strip", html)

    def test_badge_tier_rides_the_brand_token(self):
        doc = {**FIXTURE_DOC,
               "tokens": {**FIXTURE_DOC["tokens"],
                          "spacing": {"badge-tier": {"value": "5.625rem"}}}}
        saved = cs.LAYOUT_COPY
        try:
            cs.LAYOUT_COPY = {**cs.LAYOUT_COPY,
                              "band": {"eyebrow": "", "heading": "Voted #1",
                                       "panelTitle": "", "rows": [], "cta": "",
                                       "body": "", "headingLevel": ""}}
            html = cs.compose_info_band(doc, {"id": "band"}, _ctx(),
                                        _logo_frags(), None)
        finally:
            cs.LAYOUT_COPY = saved
        self.assertIn("--c-logo-strip-h: var(--space-badge-tier)", html)

    def test_real_media_fragment_still_wins(self):
        rendered = _logo_frags() + [
            {"slot": "media", "role": "photo", "contract": "image",
             "html": '<img class="c-image" src="assets/photo.webp" alt="">'}]
        html = _info_band({"id": "band"}, rendered)
        self.assertIn("c-image-mask", html)
        self.assertIn("assets/photo.webp", html)


# ── slot mediaAspect → per-card fallback (`_cards_copy`) ────────────────────────────

class CardsSlotAspectTest(unittest.TestCase):
    def _section(self, slot_extra=None, item_extra=None):
        return {
            "id": "cards", "archetype": "cards", "useCase": "features",
            "slots": [{
                "name": "cards", "role": "3 agent cards", "contract": "card",
                **(slot_extra or {}),
                "copy": [{"heading": "One", "text": "Body.", **(item_extra or {})}],
            }],
        }

    def test_slot_media_aspect_is_card_fallback(self):
        copy = cfc._cards_copy(self._section({"mediaAspect": "square"}))
        self.assertEqual(copy["cards"][0]["aspect"], "1 / 1")

    def test_module_own_aspect_wins(self):
        copy = cfc._cards_copy(self._section({"mediaAspect": "square"},
                                             {"aspect": "4 / 3"}))
        self.assertEqual(copy["cards"][0]["aspect"], "4 / 3")

    def test_no_fact_keeps_none(self):
        copy = cfc._cards_copy(self._section())
        self.assertIsNone(copy["cards"][0]["aspect"])


# ── SVG aspects from viewBox (`_asset_aspects`) ─────────────────────────────────────

class SvgAspectTest(unittest.TestCase):
    def test_viewbox_ratio(self):
        with tempfile.TemporaryDirectory() as td:
            assets = Path(td) / "assets"
            assets.mkdir()
            (assets / "mark.svg").write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 50"/>')
            out = cs._asset_aspects(Path(td), ["mark.svg"])
        self.assertEqual(out.get("mark.svg"), 2.0)

    def test_width_height_fallback(self):
        with tempfile.TemporaryDirectory() as td:
            assets = Path(td) / "assets"
            assets.mkdir()
            (assets / "mark.svg").write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" width="30" height="60"/>')
            out = cs._asset_aspects(Path(td), ["mark.svg"])
        self.assertEqual(out.get("mark.svg"), 0.5)

    def test_unreadable_svg_absent(self):
        with tempfile.TemporaryDirectory() as td:
            assets = Path(td) / "assets"
            assets.mkdir()
            (assets / "mark.svg").write_text("<svg/>")
            out = cs._asset_aspects(Path(td), ["mark.svg"])
        self.assertNotIn("mark.svg", out)


# ── surface-declared secondary ink (`textSecondary`) ────────────────────────────────

class SurfaceTextSecondaryTest(unittest.TestCase):
    DOC = {
        "brand": {"name": "Fixture"},
        "tokens": {
            "colors": {
                "text/on-inverse": {"value": "#f8f5ee"},
                "text/on-inverse-muted": {"value": "rgba(255,255,255,0.62)"},
                "accent/x": {"value": "#ff4800"},
            },
            "surfaces": {},
            "type": {"body": {"family": "Inter", "sizeRem": {"base": 1.0}}},
        },
    }

    def test_declared_secondary_wins(self):
        surf = {"bg": "#55453e", "textPrimary": "text/on-inverse",
                "textSecondary": "text/on-inverse", "textAccent": "accent/x"}
        css = cr.component_vars(self.DOC, surf, surface_role="surface/photo")
        muted = css.split("--c-ink-muted:")[1].split(";")[0]
        self.assertIn("text-on-inverse", muted)
        self.assertNotIn("muted", muted)

    def test_absent_key_keeps_global_muted(self):
        surf = {"bg": "#55453e", "textPrimary": "text/on-inverse",
                "textAccent": "accent/x"}
        css = cr.component_vars(self.DOC, surf, surface_role="surface/photo")
        muted = css.split("--c-ink-muted:")[1].split(";")[0]
        self.assertIn("text-on-inverse-muted", muted)


# ── edge-cut media fit is fact-first ────────────────────────────────────────────────

class EdgeCutFactFirstTest(unittest.TestCase):
    def _compose(self, doc, cards):
        saved = cs.LAYOUT_COPY
        try:
            cs.LAYOUT_COPY = {**cs.LAYOUT_COPY,
                              "t": {"eyebrow": "", "heading": "Agents",
                                    "cards": cards}}
            return cs.compose_features_cards(doc, {"id": "t", "_edgeCut": True},
                                             _ctx(), [], None)
        finally:
            cs.LAYOUT_COPY = saved

    def test_declared_contain_keeps_media_well(self):
        doc = {**FIXTURE_DOC,
               "_assetTags": {"ui-shot.png": {"assetKind": "product-UI"}},
               "_mediaTreatmentRules": [{"assetKind": "product-UI",
                                         "role": "card-media", "fit": "contain"}]}
        html = self._compose(doc, [{"caption": "One", "body": "B.",
                                    "asset": "ui-shot.png", "aspect": "1 / 1"}])
        self.assertNotIn("cs-module-media--mark", html)
        self.assertIn("cs-module-media--contain", html)
        self.assertIn("aspect-ratio: 1 / 1", html)

    def test_declared_mark_keeps_mark_anatomy(self):
        doc = {**FIXTURE_DOC,
               "_assetTags": {"glyph.png": {"assetKind": "feature-icon"}},
               "_mediaTreatmentRules": [{"assetKind": "feature-icon",
                                         "role": "card-media", "fit": "mark"}]}
        html = self._compose(doc, [{"caption": "One", "body": "B.",
                                    "asset": "glyph.png"}])
        self.assertIn("cs-module-media--mark", html)

    def test_undeclared_mark_filename_compat(self):
        html = self._compose(FIXTURE_DOC, [{"caption": "One", "body": "B.",
                                            "asset": "logo-a.svg"}])
        self.assertIn("cs-module-media--mark", html)


if __name__ == "__main__":
    unittest.main()
