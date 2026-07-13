#!/usr/bin/env python3
"""Fixture tests for the interaction-remediation pass (2026-07) — AS-57:

  1. NAV TRIGGERS (IC-NAV-01/02/04/08) — a menu-owning primary item with no real
     destination renders a native <button> disclosure trigger carrying
     aria-expanded + aria-controls; a captured real href keeps the link element
     (with the same state attributes); menu-less links and gallery bars are
     untouched. The UA button chrome is neutralised so the measured pill styles
     apply unchanged, and the fid15 chevron renders inside the trigger.
  2. STRUCTURAL SCRIPT (`interaction_script`) — guarded blocks emitted only for
     components present in the assembled markup: nav state/Escape, language
     dropdown Escape+refocus, banner dismiss, rail arrow-key scrolling.
  3. FAQ GROUPING (IC-ACC-01/07) — single-open is the family default (<details
     name>); an authored `exclusive: false` knob drops the name and stamps
     data-acc-multi="authored", which the static auditor recognises as a
     declared multi-open family (contract §acc Resolution notes).
  4. EDGE-CUT RAIL (IC-CAR-01) — the scroller is a focusable named region
     (tabindex/role/aria-roledescription/aria-label) with no invented chrome.
  5. FIELD MOCKS (IC-FORM-01/03) — render_input emits a real readonly control
     the wrapping label owns; the c-field-input CSS keeps the old span look.

Run:  ./venv/bin/python -m unittest brand_pipeline.tests.test_interaction_remediation
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

_BRAND_PIPELINE = Path(__file__).resolve().parent.parent
if str(_BRAND_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_BRAND_PIPELINE))

import component_render as cr       # noqa: E402
import compose_section as cs        # noqa: E402
import compose_page as cp           # noqa: E402
import interaction_audit as ia      # noqa: E402

FIXTURE_DOC = {
    "brand": {"name": "Fixture"},
    "tokens": {
        "colors": {"text/on-primary": {"value": "#111111"}},
        "surfaces": {
            "surface/primary": {"bg": "#ffffff", "textPrimary": "text/on-primary"},
        },
        "type": {"body": {"family": "Inter", "sizeRem": {"base": 1.0}}},
        "spacing": {},
    },
}

MENU = {"columns": [{"heading": "G", "links": [{"label": "x", "href": "/x"}]}]}


def _ctx(**kw):
    ctx = cr.make_context(FIXTURE_DOC, "surface/primary",
                          FIXTURE_DOC["tokens"]["surfaces"]["surface/primary"])
    for k, v in kw.items():
        setattr(ctx, k, v)
    return ctx


def _nav_doc(primary):
    doc = dict(FIXTURE_DOC)
    doc["navbar"] = {"primary": primary}
    return doc


# ── 1) nav triggers ────────────────────────────────────────────────────────────────

class NavTriggerTest(unittest.TestCase):
    def test_menu_owning_hrefless_trigger_is_a_button(self):
        doc = _nav_doc([{"label": "Products", "href": "", "menu": MENU}])
        html = cr.render_navbar(doc, _ctx(mega_nav=True), {"links": doc["navbar"]["primary"]})
        m = re.search(r'<button type="button" class="c-arrow-link cs-nav-trigger" '
                      r'aria-expanded="false" aria-controls="(cs-mega-\d+)"', html)
        self.assertIsNotNone(m, html)
        # the aria-controls target is the panel's real id
        self.assertIn(f'<div class="cs-mega" id="{m.group(1)}">', html)

    def test_real_href_trigger_stays_a_link_with_state(self):
        doc = _nav_doc([{"label": "Products", "href": "/products", "menu": MENU}])
        html = cr.render_navbar(doc, _ctx(mega_nav=True), {"links": doc["navbar"]["primary"]})
        self.assertNotIn("<button", html)
        self.assertIn('href="/products" aria-expanded="false" '
                      'aria-controls="cs-mega-1"', html)

    def test_menuless_link_carries_no_disclosure_state(self):
        doc = _nav_doc([{"label": "Pricing", "href": "/pricing"}])
        html = cr.render_navbar(doc, _ctx(mega_nav=True), {"links": doc["navbar"]["primary"]})
        self.assertNotIn("aria-expanded", html)
        self.assertNotIn("<button", html)

    def test_gallery_bar_without_mega_nav_keeps_bare_links(self):
        # the components-preview navbar demo has no page-level panels: no buttons,
        # no state attributes (the chevron resting anatomy is fid15's business).
        doc = _nav_doc([{"label": "Products", "href": "", "menu": MENU}])
        html = cr.render_navbar(doc, _ctx(), {"links": doc["navbar"]["primary"]})
        self.assertNotIn("<button", html)
        self.assertNotIn("aria-expanded", html)

    def test_trigger_chevron_renders_inside_the_button(self):
        doc = _nav_doc([{"label": "Products", "href": "", "menu": MENU}])
        doc["navbar"]["measured"] = {"trigger": {"chevron": {
            "kind": "svg", "asset": "assets/chev.svg", "box": {"w": 16, "h": 16},
            "_dataUri": "data:image/svg+xml;base64,QUFBQQ=="}}}
        html = cr.render_navbar(doc, _ctx(mega_nav=True), {"links": doc["navbar"]["primary"]})
        m = re.search(r"<button[^>]*>Products<span class=\"cs-nav-chev", html)
        self.assertIsNotNone(m, html)

    def test_mega_css_neutralises_ua_button_chrome(self):
        css = cr.nav_mega_css(_nav_doc([{"label": "P", "href": "", "menu": MENU}]))
        self.assertIn("button.cs-nav-trigger { -webkit-appearance: none;", css)
        # Escape's closed-state latch outranks :hover/:focus-within until unhover
        self.assertIn(".cs-nav-tab.cs-nav-tab--closed:hover .cs-mega", css)

    def test_panel_id_stays_off_gallery_fragments(self):
        self.assertIn('<div class="cs-mega">', cr._mega_panel_fragment(MENU))
        self.assertIn('<div class="cs-mega" id="x7">',
                      cr._mega_panel_fragment(MENU, "x7"))


# ── 2) the structural interaction script ────────────────────────────────────────────

class InteractionScriptTest(unittest.TestCase):
    def test_no_components_no_script(self):
        self.assertEqual("", cr.interaction_script("<main><p>plain page</p></main>"))

    def test_each_component_gates_its_own_block(self):
        cases = {
            "cs-nav-tab": ".cs-nav-tab",
            "cs-nav-lang": "details.cs-nav-lang[open]",
            "cs-utility-banner-close": ".cs-utility-banner-close",
            "cs-edgecut": ".cs-edgecut",
        }
        for signature, marker in cases.items():
            script = cr.interaction_script(f'<div class="{signature}"></div>')
            self.assertIn(marker, script, signature)
            for other_sig, other_marker in cases.items():
                if other_sig != signature:
                    self.assertNotIn(other_marker, script,
                                     f"{other_sig} leaked into {signature}")

    def test_nav_block_carries_state_and_escape(self):
        script = cr.interaction_script('<span class="cs-nav-tab"></span>')
        self.assertIn("setAttribute('aria-expanded'", script)
        self.assertIn("'Escape'", script)
        self.assertIn("cs-nav-tab--closed", script)

    def test_lang_block_closes_and_refocuses(self):
        script = cr.interaction_script('<details class="cs-nav-lang"></details>')
        self.assertIn("removeAttribute('open')", script)
        self.assertIn("s.focus()", script)

    def test_rail_block_scrolls_by_card_width(self):
        script = cr.interaction_script('<div class="cs-edgecut"></div>')
        self.assertIn("'ArrowRight'", script)
        self.assertIn("scrollBy", script)

    def test_composed_page_injects_the_script(self):
        # compose_page assembles banner + nav + sections into interaction_script.
        src = Path(cp.__file__).read_text()
        self.assertIn("cr.interaction_script(", src)
        self.assertIn("{ix_script}", src)


# ── 3) FAQ grouping (single-open default + authored multi-open) ─────────────────────

class FaqGroupingTest(unittest.TestCase):
    def _compose(self, stamp):
        layout = {"id": "faq-fx", "archetype": "stack"}
        if stamp is not None:
            layout["_faq"] = stamp
        saved = cs.LAYOUT_COPY
        cs.LAYOUT_COPY = {**cs.LAYOUT_COPY, "faq-fx": {
            "eyebrow": "FAQ", "heading": "Questions",
            "items": [("Q1", "A1"), ("Q2", "A2"), ("Q3", "A3")]}}
        try:
            return cs.compose_faq_accordion(FIXTURE_DOC, layout, _ctx(), [], None)
        finally:
            cs.LAYOUT_COPY = saved

    def test_unstamped_family_defaults_to_grouped_single_open(self):
        html = self._compose(None)
        self.assertEqual(3, html.count('name="faq-faq-fx"'))
        self.assertNotIn("data-acc-multi", html)

    def test_exclusive_true_stamp_keeps_the_group(self):
        html = self._compose({"exclusive": True})
        self.assertEqual(3, html.count('name="faq-faq-fx"'))

    def test_authored_multi_open_drops_name_and_declares_itself(self):
        html = self._compose({"exclusive": False})
        self.assertNotIn(" name=", html)
        self.assertIn('<div class="c-faq-list" data-acc-multi="authored">', html)

    def test_auditor_waives_declared_multi_open(self):
        html = self._compose({"exclusive": False})
        findings = ia.audit_static(html, "fx")
        acc01 = [f for f in findings if f.check == "IC-ACC-01"]
        self.assertTrue(acc01)
        self.assertTrue(all(f.status == "pass" for f in acc01),
                        [f.message for f in acc01])
        self.assertIn("declared multi-open", acc01[0].message)

    def test_auditor_still_fails_accidentally_ungrouped(self):
        html = self._compose(None).replace(' name="faq-faq-fx"', "")
        findings = ia.audit_static(html, "fx")
        acc01 = [f for f in findings if f.check == "IC-ACC-01"]
        self.assertTrue(any(f.status == "fail" for f in acc01))


# ── 4) edge-cut rail region ──────────────────────────────────────────────────────────

class EdgecutRegionTest(unittest.TestCase):
    def _compose(self, heading):
        layout = {"id": "rail-fx", "archetype": "cards", "_edgeCut": True}
        saved = cs.LAYOUT_COPY
        cs.LAYOUT_COPY = {**cs.LAYOUT_COPY, "rail-fx": {
            "eyebrow": "", "heading": heading,
            "modules": [{"heading": "M1", "text": "B1"}, {"heading": "M2", "text": "B2"}]}}
        try:
            return cs.compose_features_cards(FIXTURE_DOC, layout, _ctx(), [], None)
        finally:
            cs.LAYOUT_COPY = saved

    def test_rail_is_a_focusable_named_region(self):
        html = self._compose("Customer stories")
        self.assertIn('<div class="cs-edgecut" tabindex="0" role="region" '
                      'aria-roledescription="carousel" '
                      'aria-label="Customer stories">', html)

    def test_headingless_rail_gets_the_structural_fallback_name(self):
        html = self._compose("")
        self.assertIn('aria-label="Gallery"', html)

    def test_no_invented_prev_next_chrome(self):
        html = self._compose("Stories")
        self.assertNotIn("<button", html)


# ── 5) field mocks own a real control ───────────────────────────────────────────────

class FieldMockTest(unittest.TestCase):
    def test_render_input_emits_a_labelled_readonly_control(self):
        html = cr.render_input(FIXTURE_DOC, _ctx(), {"placeholder": "Work email"})
        self.assertIn('<label class="c-field">', html)
        self.assertIn('<input class="c-field-input" type="text" readonly '
                      'placeholder="Work email" aria-label="Work email" />', html)

    def test_field_input_css_keeps_the_span_look(self):
        # transparent, chromeless, body register — the old .c-field-text look.
        m = re.search(r"\.c-field-input \{([^}]+)\}", cr.COMPONENT_CSS)
        self.assertIsNotNone(m)
        for decl in ("background: transparent", "border: 0",
                     "font-family: var(--c-font-body)",
                     "color: var(--c-ink-muted)"):
            self.assertIn(decl, m.group(1))


if __name__ == "__main__":
    unittest.main()
