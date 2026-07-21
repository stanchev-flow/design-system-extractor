#!/usr/bin/env python3
"""Tests for the RESPONSIVE fact slice (hero + footer): the Phase-2 evidence extractor
(``responsive_facts.py``), the Phase-4 fact-gated CSS emitters
(``component_render.hero_responsive_css`` / ``footer_responsive_css``), and the
BYTE-STABILITY guarantee (a doc without a ``responsive`` block emits nothing).

Run:  ./venv/bin/python -m pytest brand_pipeline/tests/test_responsive_facts.py
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_BP = _REPO / "brand_pipeline"
if str(_BP) not in sys.path:
    sys.path.insert(0, str(_BP))

import component_render as cr  # noqa: E402
import responsive_facts as rf  # noqa: E402


# ── synthetic joined-evidence (hero + footer), no browser ─────────────────────────

def _synthetic_joined():
    return {
        "elements": [
            {"elementId": "section-00", "kind": "section", "visionRole": "hero",
             "domSelector": "#hero",
             "customProperties": {
                 "--page-header-height": [
                     {"media": "", "value": "calc(100dvh - var(--nav-h))"}],
                 "--nav-h": [
                     {"media": "", "value": "56px"},
                     {"media": "@media(width >= 1080px)", "value": "128px"}],
             },
             "cssRules": [
                 {"selector": ".page-header",
                  "decls": "height:var(--page-header-height);display:flex", "media": ""},
                 {"selector": ".page-header .heading",
                  "decls": "font-size:48px;line-height:55px", "media": ""},
                 {"selector": ".page-header .heading",
                  "decls": "font-size:80px;line-height:95px",
                  "media": "@media(width >= 600px)"},
             ],
             "computedLadder": {
                 "1440": {"headings": {"h1": {"font-size": "80px",
                                              "line-height": "95px"}}},
                 "375": {"headings": {"h1": {"font-size": "48px",
                                             "line-height": "55px"}}},
             }},
            {"elementId": "chrome-footer", "kind": "chrome", "visionRole": "footer",
             "domSelector": ".footer",
             "cssRules": [
                 {"selector": ".footer__col-left>ul",
                  "decls": "column-count:2;display:inline-block",
                  "media": "@media(width >= 900px)"},
                 {"selector": ".footer__nav", "decls": "display:flex;flex-direction:row",
                  "media": "@media(width >= 900px)"},
             ]},
        ]
    }


class ExtractorTests(unittest.TestCase):
    def setUp(self):
        self.sidecar = rf.build_sidecar(_synthetic_joined(),
                                        {"contentMaxWidth": 1080})

    def test_hero_height_rule_and_nav_offset(self):
        hero = self.sidecar["hero"]
        self.assertEqual(hero["heightRule"], "viewport-minus-nav")
        self.assertEqual(hero["navOffset"]["base"], "56px")
        self.assertEqual(hero["navOffset"]["wide"], "128px")
        self.assertEqual(hero["navOffset"]["wideMinWidth"], 1080)
        self.assertEqual(hero["provenance"]["origin"], "extracted")

    def test_hero_heading_ladder_shrinks(self):
        ladder = self.sidecar["hero"]["headingSizeLadder"]
        small = next(e for e in ladder if e.get("maxWidth"))
        large = next(e for e in ladder if e.get("minWidth"))
        self.assertEqual(small["fontSize"], "48px")
        self.assertEqual(small["lineHeight"], "55px")
        self.assertEqual(small["maxWidth"], 599)     # 600 breakpoint - 1
        self.assertEqual(large["fontSize"], "80px")
        self.assertEqual(large["minWidth"], 600)

    def test_footer_grid_and_maxwidth(self):
        foot = self.sidecar["footer"]
        self.assertEqual(foot["grid"]["breakpoint"], 900)
        self.assertEqual(foot["grid"]["columnsBelow"], 1)
        self.assertEqual(foot["grid"]["columnsAtOrAbove"], 2)  # column-count:2
        self.assertEqual(foot["maxWidth"], 1080)
        self.assertEqual(foot["provenance"]["origin"], "extracted")

    def test_no_facts_when_no_responsive_mechanic(self):
        # a hero with a fixed px height + no @media footer reflow → empty sidecar
        joined = {"elements": [
            {"elementId": "section-00", "kind": "section", "visionRole": "hero",
             "cssRules": [{"selector": ".h", "decls": "min-height:739px", "media": ""}],
             "computedLadder": {"1440": {"headings": {"h1": {"font-size": "80px"}}}}},
            {"elementId": "chrome-footer", "kind": "chrome",
             "cssRules": [{"selector": ".f", "decls": "display:flex", "media": ""}]},
        ]}
        self.assertEqual(rf.build_sidecar(joined, {}), {})


class EmitterGateTests(unittest.TestCase):
    """The Phase-4 emitters are FACT-GATED: no fact block → empty string (byte-stable)."""

    def test_hero_css_empty_without_block(self):
        self.assertEqual(cr.hero_responsive_css(None, "#sec-0"), "")
        self.assertEqual(cr.hero_responsive_css({}, "#sec-0"), "")

    def test_footer_css_empty_without_block(self):
        self.assertEqual(cr.footer_responsive_css({}, "#sec-9"), "")
        self.assertEqual(cr.footer_responsive_css({"footer": {}}, "#sec-9"), "")

    def test_hero_css_emits_viewport_height_and_shrink(self):
        block = {
            "heightRule": "viewport-minus-nav",
            "navOffset": {"base": "56px", "wide": "128px", "wideMinWidth": 1080},
            "headingSizeLadder": [
                {"maxWidth": 599, "fontSize": "48px", "lineHeight": "55px"},
                {"minWidth": 600, "fontSize": "80px", "lineHeight": "95px"}],
        }
        css = cr.hero_responsive_css(block, "#sec-0")
        self.assertIn("min-height: calc(100dvh - var(--c-hero-nav-offset", css)
        self.assertIn("--c-hero-nav-offset: 56px", css)
        self.assertIn("@media (min-width: 1080px)", css)
        self.assertIn("--c-hero-nav-offset: 128px", css)
        # heading shrink applies BELOW the breakpoint only (desktop left to the scale)
        self.assertIn("@media (max-width: 599px)", css)
        self.assertIn("font-size: 48px", css)
        self.assertIn("line-height: 55px", css)
        # scoped to the hero section id (no global bleed)
        self.assertTrue(all(line.startswith(("#sec-0", "@media", "/*"))
                            for line in css.strip().splitlines()))

    def test_footer_css_emits_reflow_and_purges_band_maxwidth(self):
        doc = {"footer": {"responsive": {
            "grid": {"breakpoint": 900, "columnsBelow": 1, "columnsAtOrAbove": 2},
            "maxWidth": 1080}}}
        css = cr.footer_responsive_css(doc, "#sec-9")
        # invented band cap purged → full-bleed; inner content capped at measured width
        self.assertIn("#sec-9 .c-footer { max-width: none", css)
        self.assertIn("--cf-cols-max: 1080px", css)
        # @media column reflow (stacked below the breakpoint)
        self.assertIn("@media (max-width: 899.98px)", css)
        self.assertIn("grid-template-columns: 1fr", css)

    def test_length_guard_rejects_non_length(self):
        # only whitelisted length literals cross the fact→CSS boundary
        self.assertIsNone(cr._resp_len("red; } evil {"))
        self.assertIsNone(cr._resp_len("url(x)"))
        self.assertEqual(cr._resp_len("48px"), "48px")
        self.assertEqual(cr._resp_len(128), "128px")


class ApplyMergeTests(unittest.TestCase):
    def test_apply_is_noop_without_sidecar(self):
        doc = {"layouts": [{"id": "h", "useCase": "hero"}], "footer": {}}
        import copy
        before = copy.deepcopy(doc)
        # a brand dir with no responsive-facts.yaml → doc unchanged (byte-stable)
        rf.apply_responsive_facts(doc, _REPO / "brand_pipeline")
        self.assertEqual(doc, before)


# ── real hubspot-v3 (skipped if joined-evidence absent) ───────────────────────────

class HubspotV3ExtractorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        p = _REPO / "runs" / "hubspot-v3" / "brand" / "evidence" / "joined-evidence.json"
        if not p.is_file():
            raise unittest.SkipTest("hubspot-v3 joined-evidence not present")
        cls.joined = json.loads(p.read_text())

    def test_real_hero_and_footer_facts(self):
        sidecar = rf.build_sidecar(self.joined, {"contentMaxWidth": 1080})
        self.assertEqual(sidecar["hero"]["heightRule"], "viewport-minus-nav")
        self.assertEqual(sidecar["footer"]["grid"]["breakpoint"], 900)
        self.assertEqual(sidecar["footer"]["grid"]["columnsAtOrAbove"], 2)
        # heading shrinks 80px → 48px (measured)
        small = next(e for e in sidecar["hero"]["headingSizeLadder"]
                     if e.get("maxWidth"))
        self.assertEqual(small["fontSize"], "48px")


if __name__ == "__main__":
    unittest.main()
