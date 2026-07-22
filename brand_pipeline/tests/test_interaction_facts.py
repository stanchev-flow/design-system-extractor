#!/usr/bin/env python3
"""Tests for the INTERACTION fact family end-to-end:

  1. capture  — tools/extract/capture_interaction_facts.build_interaction_facts derives the
     generic fact families from planted css-rules (brand-agnostic; no source class names).
  2. merge    — responsive_facts.merge_interaction_facts stashes them under the PRIVATE
     ``_interactionFacts`` namespace and is a strict NO-OP without the sidecar (byte-
     identical guarantee for brands that authored a same-named key but have no sidecar).
  3. consume  — each component_render emitter is fact-gated (fires with the fact, "" without)
     and writes its ``(fact-gated: <path>)`` marker.
  4. audit    — fact_consumption_audit reports each family CONSUMED when the marker is
     present and UNCONSUMED (loud) when the fact reached the doc but the marker is absent.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "brand_pipeline"))
sys.path.insert(0, str(REPO / "tools" / "extract"))

import responsive_facts as rf  # noqa: E402
import component_render as cr  # noqa: E402
import fact_consumption_audit as fca  # noqa: E402
import capture_interaction_facts as cif  # noqa: E402


# ── planted css-rules using a DIFFERENT naming convention than any real brand ────────
# (camelCase + a made-up prefix) so the derivation proves brand-agnostic matching.
_PLANTED_RULES = [
    {"selector": ":root", "media": "",
     "decls": "--fx-focus:#0a7; --fxSlider-duration:420ms; --fxSlider-easing:ease-out; "
              "--fxSlider-slides-per-view:2; --anchorHover:#123456"},
    # carousel/slider track + controls (generic role words)
    {"selector": ".fxSlider-track", "media": "", "decls": "transition: transform 420ms ease-out"},
    {"selector": ".fxSlider-arrowNext", "media": "", "decls": "display:flex"},
    {"selector": ".fxSlider-dots", "media": "", "decls": "display:flex"},
    {"selector": ".fxSlider.-infinite", "media": "", "decls": "overflow:visible"},
    {"selector": ".fxSlider-autoplayToggle", "media": "", "decls": "display:block"},
    # component states (button / link / input / tab)
    {"selector": ".fxButton:hover", "media": "", "decls": "background:#eee; color:#111"},
    {"selector": ".fxButton:active", "media": "", "decls": "background:#ddd"},
    {"selector": ".fxButton:focus-visible", "media": "", "decls": "outline:2px solid var(--fx-focus)"},
    {"selector": ".fxButton:disabled", "media": "", "decls": "color:#999"},
    {"selector": ".fxTextLink:hover", "media": "", "decls": "color:var(--anchorHover)"},
    {"selector": ".fxTabButton[aria-selected=true]", "media": "", "decls": "background:#f0f0f0"},
    {"selector": ".fxField:focus", "media": "", "decls": "outline:2px solid var(--fx-focus)"},
    # nav sticky / scroll-shrink
    {"selector": ".appHeader .appHeaderInner", "media": "",
     "decls": "position:fixed; top:0; width:100%"},
    {"selector": ".appHeader.isScrolled", "media": "",
     "decls": "background:#fff; box-shadow:0 2px 4px rgba(0,0,0,.1); transition: all 250ms ease"},
    # nav mobile hamburger → drawer
    {"selector": ".navMenuToggle", "media": "", "decls": "display:block"},
    {"selector": ".navMenuToggle[aria-expanded=true] .line", "media": "",
     "decls": "transform:rotate(45deg)"},
    {"selector": ".navMobileMenu", "media": "",
     "decls": "background:#fafafa; transition: transform 300ms ease-in-out"},
    # elevation + stacking
    {"selector": ".card", "media": "", "decls": "box-shadow:0 1px 3px rgba(0,0,0,.12)"},
    {"selector": ".flyoutPanel", "media": "", "decls": "box-shadow:0 12px 32px rgba(0,0,0,.3); z-index:200"},
    {"selector": ".appHeader", "media": "", "decls": "box-shadow:0 2px 4px rgba(0,0,0,.1); z-index:90"},
    {"selector": ".modalDialog", "media": "", "decls": "z-index:500"},
]

_PLANTED_DOM = {
    "chrome": {
        "footer": {"links": [
            {"label": "English", "href": "https://x.com"},
            {"label": "Deutsch", "href": "https://x.de"},
            {"label": "Français", "href": "https://x.fr"},
        ]},
        "header": {"links": []},
    }
}


class Capture(unittest.TestCase):
    def setUp(self):
        self.facts = cif.build_interaction_facts(
            rules=_PLANTED_RULES, dom=_PLANTED_DOM, color_roles={})

    def test_carousel_recipe(self):
        car = self.facts["carousel"]
        self.assertEqual(car["transitionMs"], 420)
        self.assertEqual(car["easing"], "ease-out")
        self.assertEqual(car["slidesPerView"], 2)
        self.assertIn("arrows", car["controls"])
        self.assertIn("dots", car["controls"])
        self.assertTrue(car["autoplay"])
        self.assertTrue(car["loop"])
        # intervalMs is JS-owned and must NEVER be synthesised
        self.assertNotIn("intervalMs", car)

    def test_states_generic_roles(self):
        st = self.facts["interactionStates"]
        self.assertIn("button", st)
        self.assertEqual(st["button"]["hover"]["background"], "#eee")
        self.assertIn("active", st["button"])
        self.assertIn("focus", st["button"])
        self.assertIn("disabled", st["button"])
        # a plain button never picks up a stray disclosure "open" state
        self.assertNotIn("open", st["button"])

    def test_var_resolution_nested_fallback(self):
        # var(--fx-focus) resolves to the :root literal
        self.assertEqual(self.facts["interactionStates"]["button"]["focus"]["outline"],
                         "2px solid #0a7")
        # a var with a nested fallback still resolves (link hover → --anchorHover literal)
        self.assertEqual(self.facts["interactionStates"]["link"]["hover"]["color"], "#123456")

    def test_navbar_sticky_and_mobile(self):
        st = self.facts["navbar"]["sticky"]
        self.assertEqual(st["behavior"], "scroll-shrink")
        self.assertEqual(st["toRegister"]["bg"], "#fff")
        self.assertEqual(st["transitionMs"], 250)
        mob = self.facts["navbar"]["mobile"]
        self.assertEqual(mob["trigger"]["kind"], "hamburger")
        self.assertEqual(mob["drawerSurface"]["bg"], "#fafafa")
        self.assertEqual(mob["drawerAnim"]["durationMs"], 300)
        self.assertEqual(mob["closeAffordance"]["kind"], "x-glyph")

    def test_shadow_and_zindex_scales(self):
        sh = self.facts["tokens"]["shadow"]
        self.assertEqual(sh["sticky-nav"]["value"], "0 2px 4px rgba(0, 0, 0, .1)")
        self.assertIn("raised", sh)
        self.assertIn("overlay", sh)
        zi = self.facts["tokens"]["zIndex"]
        self.assertEqual(zi["sticky-nav"]["value"], 90)
        self.assertEqual(zi["dropdown"]["value"], 200)
        self.assertEqual(zi["modal"]["value"], 500)

    def test_locale_selector(self):
        ls = self.facts["footer"]["localeSelector"]
        self.assertEqual(ls["kind"], "dropdown")
        self.assertEqual(len(ls["options"]), 3)

    def test_fact_gate_empty_source(self):
        # a source with no interactive mechanics yields no families (fact-gate)
        empty = cif.build_interaction_facts(
            rules=[{"selector": ".plain", "media": "", "decls": "color:#000"}],
            dom={}, color_roles={})
        self.assertEqual(empty, {})


# a minimal planted sidecar (post-capture) for merge/consume/audit tests.
_SIDECAR = {
    "schemaVersion": "interaction.v1",
    "carousel": {"transitionMs": 300, "easing": "ease", "controls": ["arrows", "dots"],
                 "dots": True, "autoplay": True, "loop": False,
                 "provenance": {"origin": "extracted"}},
    "interactionStates": {
        "button": {"statesObserved": ["focus", "active", "disabled"],
                   "focus": {"outline": "2px solid #2f7579", "outlineOffset": "2px"},
                   "active": {"background": "#fcead7", "color": "#1f1f1f"},
                   "disabled": {"color": "rgba(0, 0, 0, 0.2)"}},
        "provenance": {"origin": "extracted"}},
    "navbar": {
        "sticky": {"behavior": "scroll-shrink",
                   "toRegister": {"bg": "#ffffff", "shadow": "0 2px 4px rgba(33,51,67,.12)"},
                   "transitionMs": 300, "easing": "ease-in-out",
                   "provenance": {"origin": "extracted"}},
        "mobile": {"trigger": {"kind": "hamburger"},
                   "drawerSurface": {"bg": "#ffffff", "side": "full"},
                   "drawerAnim": {"durationMs": 300, "easing": "ease-in-out"},
                   "closeAffordance": {"kind": "x-glyph"},
                   "provenance": {"origin": "extracted"}}},
    "tokens": {
        "shadow": {"sticky-nav": {"value": "0 2px 4px rgba(33, 51, 67, .12)"},
                   "raised": {"value": "0 1px 24px rgba(33, 51, 67, .12)"},
                   "provenance": {"origin": "extracted"}},
        "zIndex": {"sticky-nav": {"value": 95, "role": "sticky-nav"},
                   "provenance": {"origin": "extracted"}}},
    "footer": {"localeSelector": {"kind": "dropdown", "ariaLabel": "Select a language",
                                  "options": [{"label": "English", "href": "https://x.com"},
                                              {"label": "Deutsch", "href": "https://x.de"}],
                                  "provenance": {"origin": "extracted"}}},
}


class MergeAndGate(unittest.TestCase):
    def setUp(self):
        self._orig = rf.load_interaction_facts

    def tearDown(self):
        rf.load_interaction_facts = self._orig

    def test_merge_populates_private_namespace(self):
        rf.load_interaction_facts = lambda _dir: dict(_SIDECAR)
        doc = {"navbar": {"sticky": False}, "tokens": {}, "footer": {}, "blocks": {}}
        rf.merge_interaction_facts(doc, "x", target="replica")
        self.assertIn("_interactionFacts", doc)
        self.assertIn("carousel", doc["_interactionFacts"])
        # canonical-path merge replaced the legacy bool sticky with the struct
        self.assertIsInstance(doc["navbar"]["sticky"], dict)

    def test_merge_no_sidecar_is_noop(self):
        rf.load_interaction_facts = lambda _dir: {}
        doc = {"navbar": {"sticky": False}, "tokens": {"shadow": {"x": 1}}}
        import copy
        before = copy.deepcopy(doc)
        rf.merge_interaction_facts(doc, "x", target="replica")
        self.assertEqual(doc, before)
        self.assertNotIn("_interactionFacts", doc)


def _merged_doc():
    doc = {"navbar": {}, "tokens": {}, "footer": {}, "blocks": {},
           "_interactionFacts": {k: v for k, v in _SIDECAR.items() if k != "schemaVersion"}}
    return doc


class Consume(unittest.TestCase):
    def test_every_emitter_fires_with_fact(self):
        doc = _merged_doc()
        self.assertIn("fact-gated: navbar.sticky", cr.navbar_sticky_css(doc))
        self.assertIn("fact-gated: navbar.mobile", cr.navbar_mobile_drawer_css(doc))
        self.assertIn("fact-gated: blocks.carousel.carousel", cr.carousel_timing_css(doc))
        self.assertIn("fact-gated: interactionStates", cr.interaction_states_css(doc))
        self.assertIn("fact-gated: tokens.shadow", cr.elevation_tokens_css(doc))
        self.assertIn("fact-gated: tokens.zIndex", cr.elevation_tokens_css(doc))
        self.assertIn("fact-gated: footer.localeSelector", cr.footer_locale_selector_html(doc))
        self.assertTrue(cr.navbar_sticky_script(doc))
        # sticky consumer emits the measured scrolled register (bg + shadow)
        self.assertIn("box-shadow: 0 2px 4px rgba(33,51,67,.12)", cr.navbar_sticky_css(doc))

    def test_every_emitter_empty_without_fact(self):
        doc = {"navbar": {}, "tokens": {}, "footer": {}, "blocks": {}}  # no _interactionFacts
        self.assertEqual(cr.navbar_sticky_css(doc), "")
        self.assertEqual(cr.navbar_mobile_drawer_css(doc), "")
        self.assertEqual(cr.carousel_timing_css(doc), "")
        self.assertEqual(cr.interaction_states_css(doc), "")
        self.assertEqual(cr.elevation_tokens_css(doc), "")
        self.assertEqual(cr.footer_locale_selector_html(doc), "")
        self.assertEqual(cr.navbar_sticky_script(doc), "")

    def test_no_fake_autoplay_timer(self):
        # the recipe declares autoplay:true but carries no intervalMs; the consumer must
        # not synthesise a JS timer (honest — the interval was not captured).
        doc = _merged_doc()
        out = cr.carousel_timing_css(doc)
        self.assertNotIn("setInterval", out)


class Audit(unittest.TestCase):
    def _findings(self, html):
        doc = _merged_doc()
        return {f.family: f for f in fca.audit_facts(
            sidecar={}, doc=doc, library={}, html=html, target="replica")}

    def test_all_families_consumed_when_markers_present(self):
        html = ("/* (fact-gated: navbar.sticky) */ /* (fact-gated: navbar.mobile) */ "
                "/* (fact-gated: blocks.carousel.carousel) */ /* (fact-gated: interactionStates) */ "
                "/* (fact-gated: tokens.shadow) */ /* (fact-gated: tokens.zIndex) */ "
                "<!-- (fact-gated: footer.localeSelector) -->")
        f = self._findings(html)
        for fam in ("interaction.carousel", "interaction.states", "interaction.navbar.mobile",
                    "interaction.navbar.sticky", "interaction.tokens.shadow",
                    "interaction.tokens.zIndex", "interaction.footer.localeSelector"):
            self.assertEqual(f[fam].status, fca.CONSUMED, fam)

    def test_unconsumed_is_loud(self):
        # captured facts but NO markers → every family is an UNCONSUMED (error) finding
        f = self._findings("<html>no markers here</html>")
        errs = [k for k, v in f.items() if k.startswith("interaction.") and v.is_error]
        self.assertEqual(len(errs), 7)


if __name__ == "__main__":
    unittest.main()
