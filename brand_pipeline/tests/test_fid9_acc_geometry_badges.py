#!/usr/bin/env python3
"""Fixture tests for the fid9 pass (2026-07):

  1. MEASURED ACCORDION BAND GEOMETRY — `contentShape.deviceGeometry` facts stamp as
     the `_accGeometry` layout hint (validated fields only) and the accordion device
     consumes them: equal split columns at the measured gutter/span, header stack
     riding the LIST column's first row, fixed-aspect top-aligned media region,
     measured list rhythm (trigger min-height + inter-item gap), band padding
     override. No stamp ⇒ the historical structural markup (degrade).
  2. STORE-BADGE RESOLUTION — `prepare_chrome_glyphs` inlines the footer bottom
     bar's store-badge artwork as data: URIs (previews ship no assets/ tree) and
     `render_footer` prefers the inlined URI over the raw asset path.

Run:  ./venv/bin/python -m unittest brand_pipeline.tests.test_fid9_acc_geometry_badges
"""
from __future__ import annotations

import base64
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_BRAND_PIPELINE = Path(__file__).resolve().parent.parent
if str(_BRAND_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_BRAND_PIPELINE))

import compose_section as cs   # noqa: E402
import component_render as cr  # noqa: E402
import layout_library as ll    # noqa: E402


FIXTURE_DOC = {
    "brand": {"name": "Fixture"},
    "tokens": {
        "colors": {
            "text/on-primary": {"value": "#111111"},
            "text/on-inverse": {"value": "#ffffff"},
            "accent/warm-wash": {"value": "#fceef1"},
        },
        "surfaces": {
            "surface/primary": {"bg": "#ffffff", "textPrimary": "text/on-primary"},
            "surface/accent": {"bg": "#511621", "textPrimary": "text/on-inverse"},
        },
        "type": {"body": {"family": "Inter", "sizeRem": {"base": 1.0}}},
        "spacing": {},
    },
}

GEOMETRY = {
    "source": "computed",
    "headerPlacement": "list-column",
    "columns": "equal",
    "contentSpan": "73rem",
    "columnGap": "6.3125rem",
    "rowGap": "4rem",
    "media": {"aspect": "1 / 1", "align": "top"},
    "list": {"triggerMinHeight": "5rem", "itemGap": "1rem"},
}


def _ctx():
    return cr.make_context(FIXTURE_DOC, "surface/primary",
                           FIXTURE_DOC["tokens"]["surfaces"]["surface/primary"])


def _pattern(content_shape: dict) -> ll.Pattern:
    return ll.Pattern(
        id="test-pattern", use_case="features", archetype_ref="split",
        surface_intent="any", intent="test", content_shape=content_shape,
        special_treatments=[], responsive={}, variant_knobs={},
        origin="extracted", confidence="high", scope="design-language",
        provenance=[])


def _stamp(content_shape: dict) -> dict:
    layout = {"id": "sec"}
    with mock.patch.object(cs, "resolve_pattern",
                           return_value=(_pattern(content_shape), "ref")):
        cs.stamp_pattern_devices(FIXTURE_DOC, layout, Path("/tmp/x.yaml"))
    return layout


def _compose_acc(layout, rows):
    saved = cs.LAYOUT_COPY
    try:
        cs.LAYOUT_COPY = {**cs.LAYOUT_COPY, layout["id"]: {
            "eyebrow": "How", "heading": "One system", "panelTitle": "", "cta": "",
            "body": "", "quote": "", "caption": "", "rows": rows}}
        return cs.compose_info_band(FIXTURE_DOC, layout, _ctx(), [], None)
    finally:
        cs.LAYOUT_COPY = saved


ROWS = [("EOR", "Hire anyone, anywhere."), ("Payroll", ""), ("COR", "")]


# ── deviceGeometry stamp ─────────────────────────────────────────────────────────────

class GeometryStampTest(unittest.TestCase):
    def test_valid_geometry_stamps_all_fields(self):
        lay = _stamp({"deviceGeometry": GEOMETRY})
        self.assertEqual(lay["_accGeometry"], {
            "headerInColumn": True, "equalColumns": True, "contentSpan": "73rem",
            "columnGap": "6.3125rem", "rowGap": "4rem",
            "mediaAspect": "1 / 1", "mediaTop": True,
            "triggerMinH": "5rem", "itemGap": "1rem"})

    def test_malformed_fields_are_dropped(self):
        lay = _stamp({"deviceGeometry": {
            "headerPlacement": "everywhere",          # unknown enum
            "columns": "equal",                        # valid
            "contentSpan": "wide",                     # not a CSS length
            "columnGap": "6.3125rem",                  # valid
            "rowGap": "calc(1rem + 2px)",              # not a plain length
            "media": {"aspect": "square", "align": "center"},   # invalid both
            "list": {"triggerMinHeight": "5rem", "itemGap": "big"},
        }})
        self.assertEqual(lay["_accGeometry"], {
            "equalColumns": True, "columnGap": "6.3125rem", "triggerMinH": "5rem"})

    def test_all_invalid_or_absent_means_no_stamp(self):
        self.assertNotIn("_accGeometry",
                         _stamp({"deviceGeometry": {"columns": "golden-ratio"}}))
        self.assertNotIn("_accGeometry", _stamp({}))


# ── accordion device consumption ─────────────────────────────────────────────────────

def _geo_layout(**over):
    geo = {"headerInColumn": True, "equalColumns": True, "contentSpan": "73rem",
           "columnGap": "6.3125rem", "rowGap": "4rem", "mediaAspect": "1 / 1",
           "mediaTop": True, "triggerMinH": "5rem", "itemGap": "1rem"} | over
    return {"id": "features",
            "_accordion": {"surfaceRole": "surface/accent",
                           "hoverWash": "accent/warm-wash"},
            "_accGeometry": geo}


class GeometryConsumptionTest(unittest.TestCase):
    def test_geometry_vars_and_classes_render(self):
        html = _compose_acc(_geo_layout(), ROWS)
        self.assertIn("cs-acc-split--equal", html)
        self.assertIn("cs-split-media--top", html)
        for decl in ("--cs-acc-colgap: 6.3125rem", "--cs-acc-rowgap: 4rem",
                     "--cs-acc-span: 73rem", "--cs-acc-trig-minh: 5rem",
                     "--cs-acc-itemgap: 1rem", "--cs-acc-media-aspect: 1 / 1"):
            self.assertIn(decl, html)

    def test_header_rides_the_list_column(self):
        html = _compose_acc(_geo_layout(), ROWS)
        self.assertIn("cs-acc-col--lead", html)
        col = re.search(r'<div class="cs-acc-col cs-acc-col--lead">.*?<div class="c-acc"',
                        html, re.S)
        self.assertIsNotNone(col)
        self.assertIn("cs-split-intro", col.group(0))  # intro INSIDE the column
        # no second intro outside the split
        self.assertEqual(html.count("cs-split-intro"), 1)

    def test_band_padding_overrides_section_rhythm(self):
        layout = _geo_layout()
        layout["_bandPadding"] = {"top": "4rem", "bottom": "4rem"}
        html = _compose_acc(layout, ROWS)
        m = re.search(r'<section[^>]*class="cs-section cs-split-sec cs-acc-sec"[^>]*>',
                      html)
        self.assertIn("--c-section-pad-top: 4rem", m.group(0))
        self.assertIn("--c-section-pad-bottom: 4rem", m.group(0))

    def test_no_geometry_keeps_structural_markup(self):
        html = _compose_acc({"id": "features",
                             "_accordion": {"surfaceRole": "surface/accent",
                                            "hoverWash": "accent/warm-wash"}}, ROWS)
        for marker in ("cs-acc-split--equal", "cs-acc-col--lead", "cs-split-media--top",
                       "--cs-acc-", "--c-section-pad-"):
            self.assertNotIn(marker, html)
        # intro precedes the split wrapper (historical top-level placement)
        self.assertLess(html.index("cs-split-intro"), html.index("cs-acc-split"))

    def test_geometry_css_is_var_gated(self):
        css = cs.SCAFFOLD_ACCORDION_CSS
        self.assertIn("max-width: var(--cs-acc-span, none)", css)
        self.assertIn("column-gap: var(--cs-acc-colgap", css)
        self.assertIn("aspect-ratio: var(--cs-acc-media-aspect, auto)", css)
        self.assertIn("min-height: var(--cs-acc-trig-minh, auto)", css)
        self.assertIn("margin-top: var(--cs-acc-itemgap, 0)", css)
        self.assertIn("margin-bottom: var(--cs-acc-rowgap, 3.5rem)", css)


# ── store-badge data-URI resolution ─────────────────────────────────────────────────

SVG = b'<svg xmlns="http://www.w3.org/2000/svg"><rect width="9" height="9"/></svg>'
PNG_1PX = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
    "YPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==")


def _badge_doc(*assets):
    return {"footer": {"bottomBar": {"storeBadges": [
        {"href": "#", "img": {"alt": f"badge {i}", "asset": a}}
        for i, a in enumerate(assets)]}}}


class StoreBadgeResolutionTest(unittest.TestCase):
    def test_badges_inline_svg_and_raster(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "assets").mkdir()
            (Path(td) / "assets" / "store.svg").write_bytes(SVG)
            (Path(td) / "assets" / "play.png").write_bytes(PNG_1PX)
            doc = _badge_doc("assets/store.svg", "assets/play.png")
            n = cr.prepare_chrome_glyphs(doc, td)
        self.assertEqual(n, 2)
        badges = doc["footer"]["bottomBar"]["storeBadges"]
        self.assertTrue(badges[0]["img"]["_dataUri"].startswith(
            "data:image/svg+xml;base64,"))
        self.assertTrue(badges[1]["img"]["_dataUri"].startswith(
            "data:image/png;base64,"))

    def test_missing_file_degrades_to_raw_path(self):
        with tempfile.TemporaryDirectory() as td:
            doc = _badge_doc("assets/ghost.svg")
            n = cr.prepare_chrome_glyphs(doc, td)
        self.assertEqual(n, 0)
        img = doc["footer"]["bottomBar"]["storeBadges"][0]["img"]
        self.assertNotIn("_dataUri", img)
        html = cr.render_footer(FIXTURE_DOC, _ctx(),
                                {"bottomBar": doc["footer"]["bottomBar"]})
        self.assertIn('src="assets/ghost.svg"', html)

    def test_footer_prefers_inlined_uri(self):
        bb = {"storeBadges": [{"href": "#", "img": {
            "alt": "App Store", "asset": "assets/store.svg",
            "_dataUri": "data:image/svg+xml;base64,AAAA"}}]}
        html = cr.render_footer(FIXTURE_DOC, _ctx(), {"bottomBar": bb})
        self.assertIn('src="data:image/svg+xml;base64,AAAA"', html)
        self.assertNotIn('src="assets/store.svg"', html)

    def test_social_glyphs_stay_svg_only(self):
        # CSS-mask glyphs must remain vector artwork: a raster social icon does
        # not inline (the renderer's text-link degrade covers it).
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "icon.png").write_bytes(PNG_1PX)
            doc = {"footer": {"social": [
                {"network": "x", "icon": {"asset": "icon.png"}}]}}
            n = cr.prepare_chrome_glyphs(doc, td)
        self.assertEqual(n, 0)
        self.assertNotIn("_dataUri", doc["footer"]["social"][0]["icon"])


if __name__ == "__main__":
    unittest.main()
