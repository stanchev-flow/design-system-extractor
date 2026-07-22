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
            {"elementId": "chrome-header", "kind": "chrome", "visionRole": "nav",
             "domSelector": ".nav",
             "customProperties": {
                 "--container-01": [{"media": "", "value": "var(--light-container)"}],
                 "--light-container": [{"media": "", "value": "#ffffff"}]},
             "cssRules": [
                 {"selector": ".global-nav-main .global-nav-main-inner",
                  "decls": "background:var(--container-01);position:absolute", "media": ""},
                 {"selector": ".global-nav-tab-dropdown-content-wrapper .mega-card",
                  "decls": "background:#eee", "media": ""},
                 {"selector": ".global-nav-main-inner:hover",
                  "decls": "background:#f5f5f5", "media": "", "pseudo": [":hover"]},
             ]},
            {"elementId": "action-40", "kind": "action", "visionRole": "hero",
             "classes": "cl-button -primary -large",
             "computedLadder": {"1440": {"measured": {
                 "display": "block", "font-size": "18px", "line-height": "32px",
                 "border": "2px solid rgba(0, 0, 0, 0)", "padding": "16px 40px"}}},
             "cssRules": [
                 {"selector": ".cl-button", "decls": "background:var(--fill)", "media": ""},
                 {"selector": ".cl-button:hover,.cl-button:focus-visible",
                  "decls": "background:var(--hover);color:var(--ink)",
                  "media": "", "pseudo": [":hover"]},
             ]},
            {"elementId": "heading-h2", "kind": "heading",
             "computedLadder": {
                 "1440": {"line-height": "28px", "font-size": "18px"},
                 "375": {"line-height": "28px", "font-size": "18px"}}},
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


class GeneralizedExtractorTests(unittest.TestCase):
    """The generalized fact blocks: nav mega-panel surface, hero primary button
    geometry + brand-wide hover-transform purge, and heading line-heights."""

    def setUp(self):
        self.sidecar = rf.build_sidecar(_synthetic_joined(), {"contentMaxWidth": 1080})

    def test_nav_panel_surface_resolved(self):
        nav = self.sidecar["nav"]
        # the panel container paints var(--container-01) → resolved through the var
        # chain to the measured literal; child cards + hover washes are excluded.
        self.assertEqual(nav["panelSurface"]["background"], "#ffffff")
        self.assertEqual(nav["provenance"]["origin"], "extracted")

    def test_hero_primary_button_geometry(self):
        btn = self.sidecar["hero"]["primaryButton"]
        self.assertEqual(btn["fontSize"], "18px")
        self.assertEqual(btn["lineHeight"], "32px")
        self.assertEqual(btn["padding"], "16px 40px")
        # a transparent measured border is normalized colour-agnostically (no palette leak)
        self.assertEqual(btn["border"], "2px solid transparent")
        self.assertTrue(btn["motionPurge"]["hoverTransform"])

    def test_brand_wide_hover_transform_purge_flag(self):
        # the source button state rules swap bg/color only → purge the composer lift
        self.assertTrue(self.sidecar["buttons"]["purgeHoverTransform"])

    def test_hover_transform_kept_when_source_has_one(self):
        j = _synthetic_joined()
        for e in j["elements"]:
            if e["elementId"] == "action-40":
                e["cssRules"][1]["decls"] += ";transform:translateY(-2px)"
        sidecar = rf.build_sidecar(j, {})
        self.assertNotIn("buttons", sidecar)  # grounded hover transform → no purge
        self.assertNotIn("motionPurge", sidecar["hero"]["primaryButton"])

    def test_heading_line_heights(self):
        lhs = self.sidecar["headings"]["lineHeights"]
        self.assertEqual(lhs["h2"], "28px")


class GeneralizedEmitterTests(unittest.TestCase):
    """Fact-gated emitters for the generalized components (byte-stable without a block)."""

    def test_hero_primary_button_css_gated(self):
        self.assertEqual(cr.hero_primary_button_css(None, "#sec-0"), "")
        self.assertEqual(cr.hero_primary_button_css({}, "#sec-0"), "")
        self.assertEqual(cr.hero_primary_button_css({"primaryButton": {}}, "#sec-0"), "")

    def test_hero_primary_button_css_emits_measured_box(self):
        block = {"primaryButton": {"fontSize": "18px", "lineHeight": "32px",
                                   "padding": "16px 40px",
                                   "border": "2px solid transparent"}}
        css = cr.hero_primary_button_css(block, "#sec-0")
        self.assertIn("#sec-0 .c-button:not(.c-button--navcta)", css)
        self.assertIn("font-size: 18px", css)
        self.assertIn("line-height: 32px", css)
        self.assertIn("border: 2px solid transparent", css)

    def test_heading_css_gated_and_emits(self):
        self.assertEqual(cr.heading_responsive_css({}), "")
        self.assertEqual(cr.heading_responsive_css(
            {"responsive": {"headings": {}}}), "")
        css = cr.heading_responsive_css(
            {"responsive": {"headings": {"lineHeights": {"h2": "28px"}}}})
        self.assertIn(":is(h2, .c-heading--h2)", css)
        self.assertIn("line-height: 28px", css)

    def test_button_variant_purge_is_fact_gated(self):
        # without the fact the hover lift stays (byte-identical to the base variant)
        self.assertEqual(cr._button_variant_css({}), cr._BUTTON_VARIANT_CSS)
        self.assertIn("translateY(-1px)", cr._button_variant_css({}))
        # with the purge fact the un-grounded lift is dropped, bg/color swap kept
        purged = cr._button_variant_css(
            {"responsive": {"buttons": {"purgeHoverTransform": True}}})
        self.assertNotIn("translateY(-1px)", purged)
        self.assertIn(".c-button:hover", purged)
        self.assertIn("--c-button-bg-hover", purged)

    def test_nav_mega_panel_prefers_responsive_surface(self):
        # a doc whose measured megaPanel surface is transparent but carries a responsive
        # nav panel-surface fact paints the resolved colour on .cs-mega.
        doc = {
            "navbar": {"primary": [{"label": "Products",
                                    "menu": {"columns": [{"title": "A", "links": []}]}}],
                       "measured": {"megaPanel": {"surface": {"bg": "rgba(0, 0, 0, 0)"}}}},
            "responsive": {"nav": {"panelSurface": {"background": "#ffffff"}}},
        }
        css = cr.nav_mega_css(doc)
        self.assertIn(".cs-mega", css)
        self.assertIn("background: #ffffff", css)
        # without the responsive fact the transparent measured surface is unchanged
        doc.pop("responsive")
        css2 = cr.nav_mega_css(doc)
        self.assertIn("background: rgba(0, 0, 0, 0)", css2)


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


class NavCollapseExtractorTests(unittest.TestCase):
    """The nav mobile-collapse fact: a burger control hidden at/above a measured
    breakpoint + desktop rows that are mobile-first hidden and shown at/above it.
    Brand-agnostic across kebab (`.-mobile-only`) and camelCase (`menuToggle`) names."""

    def _kebab_nav(self):
        # HubSpot-shape: mobile-first rows (display:none at base, display:flex @>=1080),
        # a burger group shown at base and hidden at/above the breakpoint.
        return {
            "elementId": "chrome-header", "kind": "chrome", "visionRole": "nav",
            "cssRules": [
                {"selector": ".global-nav-top-bar", "decls": "display:none", "media": ""},
                {"selector": ".global-nav-top-bar",
                 "decls": "display:flex", "media": "@media(width >= 1080px)"},
                {"selector": ".global-nav-main-tab-list",
                 "decls": "display:none", "media": ""},
                {"selector": ".global-nav-main-tab-list",
                 "decls": "display:flex", "media": "@media(width >= 1080px)"},
                {"selector": ".global-nav-main .global-nav-main-group.-mobile-only",
                 "decls": "display:flex", "media": ""},
                {"selector": ".global-nav-header .global-nav-main .-mobile-only",
                 "decls": "display:none", "media": "@media(width >= 1080px)"},
                {"selector": ".global-nav-burger-btn", "decls": "display:block",
                 "media": ""},
            ]}

    def _camel_nav(self):
        # CSS-module (camelCase) shape at a different breakpoint — same mechanic.
        return {
            "elementId": "chrome-header", "kind": "chrome", "visionRole": "nav",
            "cssRules": [
                {"selector": ".mod__mainNav", "decls": "display:none", "media": ""},
                {"selector": ".mod__mainNav", "decls": "display:flex",
                 "media": "@media (min-width:1200px)"},
                {"selector": ".mod__menuToggle", "decls": "display:flex", "media": ""},
                {"selector": ".mod__menuToggle", "decls": "display:none",
                 "media": "@media (min-width:1200px)"},
                {"selector": ".mod__navMobileBar", "decls": "display:flex", "media": ""},
                {"selector": ".mod__navMobileBar", "decls": "display:none",
                 "media": "@media (min-width:1200px)"},
            ]}

    def test_kebab_collapse_breakpoint_and_burger(self):
        c = rf._nav_collapse_from_evidence(self._kebab_nav())
        self.assertEqual(c["breakpoint"], 1080)
        self.assertTrue(c["burger"])

    def test_camelcase_collapse_breakpoint_and_burger(self):
        c = rf._nav_collapse_from_evidence(self._camel_nav())
        self.assertEqual(c["breakpoint"], 1200)
        self.assertTrue(c["burger"])

    def test_nav_block_carries_collapse(self):
        block = rf.nav_responsive_from_evidence(self._kebab_nav())
        self.assertEqual(block["collapse"]["breakpoint"], 1080)
        self.assertIn("collapse", block["provenance"])

    def test_no_collapse_without_mechanic(self):
        # a nav with only a static bar (no mobile-first rows, no burger) → None
        nav = {"elementId": "chrome-header", "cssRules": [
            {"selector": ".nav", "decls": "display:flex", "media": ""},
            {"selector": ".nav-links", "decls": "display:flex", "media": ""}]}
        self.assertIsNone(rf._nav_collapse_from_evidence(nav))

    def test_real_brands_collapse(self):
        # the two captured sources (hubspot 1080, remote 1200) both carry the mechanic.
        for run, bp in (("hubspot-v3", 1080), ("hubspot-v2", 1080), ("remote", 1200)):
            p = (_REPO / "runs" / run / "brand" / "evidence" / "joined-evidence.json")
            if not p.is_file():
                continue
            joined = json.loads(p.read_text())
            nav = next((e for e in joined.get("elements", [])
                        if e.get("elementId") == "chrome-header"), None)
            c = rf._nav_collapse_from_evidence(nav)
            self.assertIsNotNone(c, f"{run} nav collapse not detected")
            self.assertEqual(c["breakpoint"], bp, f"{run} breakpoint")
            self.assertTrue(c["burger"], f"{run} burger")


class NavCollapseEmitterTests(unittest.TestCase):
    """nav_collapse_css: fact-gated, byte-stable without the block; emits a #page-nav
    scoped @media that hides the desktop rows + shows the burger below the breakpoint."""

    def test_gated_empty_without_fact(self):
        self.assertEqual(cr.nav_collapse_css({}), "")
        self.assertEqual(cr.nav_collapse_css({"responsive": {}}), "")
        self.assertEqual(cr.nav_collapse_css({"responsive": {"nav": {}}}), "")
        self.assertEqual(
            cr.nav_collapse_css({"responsive": {"nav": {"collapse": {}}}}), "")

    def test_emits_media_and_burger(self):
        css = cr.nav_collapse_css(
            {"responsive": {"nav": {"collapse": {"breakpoint": 1080}}}})
        self.assertIn("@media (max-width: 1079px)", css)
        self.assertIn("#page-nav .cs-nav-tier--utility { display: none; }", css)
        self.assertIn("#page-nav .cs-navlinks { display: none; }", css)
        self.assertIn("#page-nav .cs-nav-util { display: none; }", css)
        self.assertIn("#page-nav .cs-nav-actions { display: none; }", css)
        self.assertIn("#page-nav .cs-nav-burger { display: inline-flex; }", css)
        # burger hidden by default (desktop byte-identical) + drawer closed at rest
        self.assertIn("#page-nav .cs-nav-burger { display: none;", css)
        self.assertIn("#page-nav .cs-nav-drawer { display: none;", css)

    def test_breakpoint_rides_the_fact(self):
        css = cr.nav_collapse_css(
            {"responsive": {"nav": {"collapse": {"breakpoint": 1200}}}})
        self.assertIn("@media (max-width: 1199px)", css)
        self.assertNotIn("1079", css)


class NavCollapseRenderTests(unittest.TestCase):
    """render_navbar emits the burger + drawer ONLY when the mobileCollapse prop is
    present (fact-gated); a bar without it is byte-identical (no burger/drawer)."""

    def _doc(self):
        return {"brand": {"name": "Acme"}, "tokens": {"surfaces": {}}}

    def _ctx(self):
        return cr.make_context(self._doc(), "surface/primary", {})

    def test_no_burger_without_prop(self):
        html = cr.render_navbar(self._doc(), self._ctx(),
                                {"wordmark": "Acme", "links": ["A", "B"], "cta": "Go"})
        self.assertNotIn("cs-nav-burger", html)
        self.assertNotIn("cs-nav-drawer", html)

    def test_burger_and_drawer_with_prop(self):
        html = cr.render_navbar(self._doc(), self._ctx(), {
            "wordmark": "Acme", "links": [{"label": "Products", "href": "/p"}],
            "cta": "Go",
            "mobileCollapse": {"breakpoint": 1080, "burgerLabel": "Menu"}})
        self.assertIn('class="cs-nav-burger"', html)
        self.assertIn('aria-expanded="false"', html)
        self.assertIn('aria-controls="cs-nav-drawer"', html)
        self.assertIn('aria-label="Menu"', html)
        self.assertIn('id="cs-nav-drawer"', html)
        self.assertIn("hidden>", html)          # drawer closed at rest (adds no width)
        self.assertIn("Products", html)         # top-level link mirrored into the drawer

    def test_burger_byte_stability(self):
        # the ONLY delta between with/without the prop is the burger + drawer markup;
        # everything else (logo/links/cta) is byte-identical.
        base = {"wordmark": "Acme", "links": [{"label": "Products", "href": "/p"}],
                "cta": "Go"}
        without = cr.render_navbar(self._doc(), self._ctx(), dict(base))
        withp = cr.render_navbar(self._doc(), self._ctx(),
                                 {**base, "mobileCollapse": {"breakpoint": 1080}})
        # stripping the added burger + drawer from the with-prop markup recovers the
        # without-prop markup exactly (pure superset, nothing else changed).
        import re as _re
        stripped = _re.sub(r'<button type="button" class="cs-nav-burger".*?</button>',
                           "", withp, flags=_re.S)
        stripped = _re.sub(r'<div id="cs-nav-drawer".*?</div>', "", stripped,
                           flags=_re.S)
        self.assertEqual(stripped, without)


class NavbarPropsCollapseTests(unittest.TestCase):
    """_navbar_props surfaces the mobileCollapse prop from responsive.nav.collapse
    (fact-gated) with the captured mobile-burger label."""

    def test_props_gated_on_collapse_fact(self):
        import compose_section as cs
        doc = {"brand": {"name": "Acme"},
               "navbar": {"primary": [{"label": "P"}],
                          "utilityControls": [{"role": "mobile-burger",
                                               "label": "Open menu"}]},
               "responsive": {"nav": {"collapse": {"breakpoint": 1080}}}}
        props = cs._navbar_props(doc)
        self.assertEqual(props["mobileCollapse"]["breakpoint"], 1080)
        self.assertEqual(props["mobileCollapse"]["burgerLabel"], "Open menu")
        # no collapse fact → no prop (byte-identical bar)
        doc.pop("responsive")
        self.assertNotIn("mobileCollapse", cs._navbar_props(doc))

    def test_burger_label_defaults_to_menu(self):
        import compose_section as cs
        doc = {"brand": {"name": "Acme"}, "navbar": {"primary": [{"label": "P"}]},
               "responsive": {"nav": {"collapse": {"breakpoint": 1200}}}}
        props = cs._navbar_props(doc)
        self.assertEqual(props["mobileCollapse"]["burgerLabel"], "Menu")


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
