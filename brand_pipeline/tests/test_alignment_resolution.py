#!/usr/bin/env python3
"""Fixture-based unit tests for the AS-18/19/20 batch (anti-ai-slop.md):

  - AS-18 alignment resolution chain (`compose_section.resolve_alignment`):
    section-explicit > pattern contentShape.alignment > style role default, with the
    winning source stamped (`align_stamp_attrs`) and out-of-enum anchors warned +
    dropped (never silently kept).
  - G10 `alignment-resolution` gate (`onbrand_check._check_alignment_resolution`):
    stamp-less sections on a stance-declaring style FAIL; asymmetric anchors without a
    counterweight FAIL.
  - AS-19 media registration: a resolved-centered anchor derives SYMMETRIC
    statement/quote media spans; G11 (`_check_media_registration`) fails the
    editorial-offset span under centered text.
  - AS-20 interaction contrast (`readability.check_link_hover_contrast`): hover colors
    resolve in the element's OWN token scope and measure against its OWN surface —
    gold-on-cream fails, gold-on-dark passes, a panel that re-scopes --c-link-hover
    passes.
  - recalibrated `no-centered-everything`: reads declared anchors, not flex-start.

Run:  ./venv/bin/python -m unittest brand_pipeline.tests.test_alignment_resolution
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

_BRAND_PIPELINE = Path(__file__).resolve().parent.parent
if str(_BRAND_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_BRAND_PIPELINE))

import yaml                          # noqa: E402

import compose_section as cs         # noqa: E402
import layout_library as ll          # noqa: E402
import onbrand_check as oc           # noqa: E402
import readability as rd             # noqa: E402
import styles                        # noqa: E402

_WOODWAVE = _BRAND_PIPELINE.parent / "runs" / "woodwave" / "brand" / "brand.yaml"


def _pattern(alignment: dict | None, *, use_case="about", archetype="split") -> ll.Pattern:
    content_shape = {"alignment": alignment} if alignment else {}
    return ll.Pattern(
        id="test-pattern", use_case=use_case, archetype_ref=archetype,
        surface_intent="any", intent="test", content_shape=content_shape,
        special_treatments=[], responsive={}, variant_knobs={}, origin="designed",
        confidence="high", scope="design-language", provenance=[])


def _style_ctx():
    doc = yaml.safe_load(_WOODWAVE.read_text())
    return styles.load_and_merge("editorial-luxury", doc)


class ResolutionChainTest(unittest.TestCase):
    def test_section_explicit_wins(self):
        lay = {"id": "x", "archetype": "split", "alignment": {"anchor": "centered"}}
        r = cs.resolve_alignment(lay, _pattern({"value": "left", "counterweight": "media"}),
                                 _style_ctx())
        self.assertEqual(r["anchor"], "centered")
        self.assertEqual(r["source"], "section")

    def test_pattern_beats_style(self):
        lay = {"id": "x", "archetype": "split"}
        r = cs.resolve_alignment(lay, _pattern({"value": "left", "counterweight": "media"}),
                                 _style_ctx())
        self.assertEqual((r["anchor"], r["source"], r["counterweight"]),
                         ("left", "pattern", "media"))

    def test_style_role_default_is_last(self):
        # editorial-luxury: cta role -> centered
        lay = {"id": "x", "archetype": "stack",
               "blockMapping": [{"contract": "form"}]}  # -> conversion role
        r = cs.resolve_alignment(lay, None, _style_ctx())
        self.assertEqual((r["anchor"], r["source"]), ("centered", "style"))

    def test_no_layer_declares_returns_none(self):
        r = cs.resolve_alignment({"id": "x", "archetype": "split"}, None,
                                 styles.inactive_context())
        self.assertIsNone(r)

    def test_out_of_enum_anchor_warns_and_falls_through(self):
        lay = {"id": "x", "archetype": "split",
               "alignment": {"anchor": "diagonal"}}  # nonsense -> next layer
        r = cs.resolve_alignment(lay, _pattern({"value": "left", "counterweight": "media"}),
                                 _style_ctx())
        self.assertEqual(r["source"], "pattern")

    def test_center_normalizes_to_centered(self):
        self.assertEqual(ll.normalize_anchor("center"), "centered")
        self.assertEqual(ll.normalize_anchor("space-between"), "space-between")
        self.assertIsNone(ll.normalize_anchor("diagonal"))

    def test_stamp_attrs(self):
        attrs = cs.align_stamp_attrs(
            {"anchor": "left", "source": "pattern", "counterweight": "media"})
        self.assertIn('data-align="left"', attrs)
        self.assertIn('data-align-source="pattern"', attrs)
        self.assertIn('data-align-counterweight="media"', attrs)
        self.assertEqual(cs.align_stamp_attrs(None), "")


class AnchorCssTest(unittest.TestCase):
    def test_centered_derives_symmetric_media_spans(self):
        css = cs._anchor_css("#sec-3", "centered")
        self.assertIn("--c-statement-media-col: 4 / -4", css)
        self.assertIn("--c-quote-media-col: 4 / -4", css)
        self.assertIn("align-items: center", css)

    def test_left_keeps_editorial_offset(self):
        css = cs._anchor_css("#sec-3", "left")
        self.assertNotIn("--c-statement-media-col", css)  # scaffold default (6/-1) rules
        self.assertIn("align-items: flex-start", css)

    def test_space_between_covers_flow_and_utility(self):
        css = cs._anchor_css("#sec-3", "space-between")
        self.assertIn("justify-content: space-between", css)

    def test_placement_css_stamps_resolution_source(self):
        out = cs.layout_placement_css(
            "#sec-1", {"id": "x"},
            resolved={"anchor": "centered", "source": "style", "counterweight": None})
        self.assertIn("source: style", out)


def _page(sections: str, *, style: str = ' data-style="editorial-luxury"',
          css: str = "") -> str:
    return (f"<html{style}><head><style>{css}</style></head>"
            f"<body>{sections}</body></html>")


class AlignmentResolutionGateTest(unittest.TestCase):
    def test_stamped_page_passes(self):
        html = _page(
            '<div id="sec-0" class="cs-surface" data-align="centered" '
            'data-align-source="pattern"></div>'
            '<div id="sec-1" class="cs-surface" data-align="left" '
            'data-align-source="style" data-align-counterweight="media"></div>')
        ok, detail = oc._check_alignment_resolution(html)
        self.assertTrue(ok, detail)

    def test_missing_stamp_on_stance_style_fails(self):
        html = _page('<div id="sec-0" class="cs-surface"></div>')
        ok, detail = oc._check_alignment_resolution(html)
        self.assertFalse(ok)
        self.assertIn("fall-through", detail)

    def test_asymmetric_without_counterweight_fails(self):
        html = _page('<div id="sec-0" class="cs-surface" data-align="left" '
                     'data-align-source="pattern"></div>')
        ok, detail = oc._check_alignment_resolution(html)
        self.assertFalse(ok)
        self.assertIn("counterweight", detail)

    def test_styleless_render_not_gated(self):
        html = _page('<div id="sec-0" class="cs-surface"></div>', style="")
        ok, _ = oc._check_alignment_resolution(html)
        self.assertTrue(ok)


class MediaRegistrationGateTest(unittest.TestCase):
    def test_centered_with_symmetric_span_passes(self):
        html = _page(
            '<div id="sec-2" class="cs-surface" data-align="centered" '
            'data-align-source="section">'
            '<div class="cs-statement-media"></div></div>',
            css="#sec-2 { --c-statement-media-col: 4 / -4; }")
        ok, detail = oc._check_media_registration(html)
        self.assertTrue(ok, detail)

    def test_centered_without_scoped_span_fails(self):
        html = _page(
            '<div id="sec-2" class="cs-surface" data-align="centered" '
            'data-align-source="section">'
            '<div class="cs-statement-media"></div></div>')
        ok, detail = oc._check_media_registration(html)
        self.assertFalse(ok)
        self.assertIn("editorial-offset", detail)

    def test_centered_with_asymmetric_span_fails(self):
        html = _page(
            '<div id="sec-2" class="cs-surface" data-align="centered" '
            'data-align-source="section">'
            '<div class="cs-quote-media"></div></div>',
            css="#sec-2 { --c-quote-media-col: 6 / -1; }")
        ok, detail = oc._check_media_registration(html)
        self.assertFalse(ok)
        self.assertIn("asymmetric", detail)

    def test_left_section_with_offset_is_legal(self):
        html = _page(
            '<div id="sec-2" class="cs-surface" data-align="left" '
            'data-align-source="pattern" data-align-counterweight="media">'
            '<div class="cs-statement-media"></div></div>')
        ok, _ = oc._check_media_registration(html)
        self.assertTrue(ok)


def _hover_page(panel_extra: str = "") -> str:
    """A dark section (gold measured hover) containing a cream panel card with an
    arrow link — the AS-20 leak fixture."""
    return f"""<html><head><style>
:root {{ --c-link-hover: var(--c-ink); }}
.sec {{ background: #3d3728; color: #f3ebdd; --c-ink: #f3ebdd; --c-link-hover: #edd580; }}
.cs-panel {{ background: #f7efe6; color: #1f1a14; --c-ink: #1f1a14; {panel_extra} }}
.c-arrow-link {{ font-size: 0.875rem; }}
.c-arrow-link:hover, .c-arrow-link:focus-visible {{ color: var(--c-link-hover); }}
</style></head><body>
<div id="sec-0" class="cs-surface sec"><a class="c-arrow-link">Plan a visit</a>
  <div class="cs-panel"><a class="c-arrow-link">GET DIRECTIONS</a></div>
</div></body></html>"""


class LinkHoverContrastTest(unittest.TestCase):
    def test_gold_hover_leaking_onto_cream_panel_fails(self):
        ok, detail = rd.check_link_hover_contrast(_hover_page())
        self.assertFalse(ok)
        self.assertIn("GET DIRECTIONS"[:8].lower(), detail.lower())

    def test_panel_rescope_passes_and_dark_gold_survives(self):
        # the AS-20 fix: the panel re-scopes --c-link-hover to its own ink
        ok, detail = rd.check_link_hover_contrast(
            _hover_page(panel_extra="--c-link-hover: #1f1a14;"))
        self.assertTrue(ok, detail)
        # the dark-surface link resolves the measured gold and PASSES vs the dark bg
        a = rd.analyze(_hover_page(panel_extra="--c-link-hover: #1f1a14;"))
        dark_rows = [r for r in a["links"] if "edd580" in r["hover_color"].lower()
                     or r["hover_color"].lower() == "#edd580"]
        self.assertTrue(dark_rows and all(r["passed"] for r in dark_rows),
                        f"dark gold hover must survive: {a['links']}")

    def test_no_hover_rules_is_pass(self):
        ok, _ = rd.check_link_hover_contrast(
            "<html><head><style>.a{color:#000}</style></head>"
            "<body><a class='a'>hi</a></body></html>")
        self.assertTrue(ok)


class NoCenteredEverythingRecalibrationTest(unittest.TestCase):
    FACTS = None  # the check ignores facts/doc/layout for the stamp path

    def test_unstamped_render_keeps_legacy_pass(self):
        ok, _ = oc._ck_no_centered_everything({}, {}, {}, "<div></div>")
        self.assertTrue(ok)

    def test_declared_variety_passes(self):
        low = ('<div data-align="centered"></div><div data-align="left"></div>'
               '<div data-align="left"></div><div data-align="edge-to-edge"></div>'
               '<div data-align="centered"></div>')
        ok, detail = oc._ck_no_centered_everything({}, {}, {}, low)
        self.assertTrue(ok, detail)
        self.assertIn("declared anchors", detail)

    def test_page_wide_centering_fails(self):
        low = '<div data-align="centered"></div>' * 5
        ok, detail = oc._ck_no_centered_everything({}, {}, {}, low)
        self.assertFalse(ok)
        self.assertIn("RESOLVE centered", detail)


if __name__ == "__main__":
    unittest.main()
