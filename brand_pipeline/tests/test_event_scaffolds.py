#!/usr/bin/env python3
"""Fixture tests for the event-scaffolds batch (2026-07): the three NEW brand-
agnostic scaffolds (bento grid / pricing tiers / signup form) + the FAQ state
grammar and the poster-hero panel extensions.

Covers, per scaffold:
  - adapter validation (`_bento_stamp` / `_tiers_stamp` / `_form_fields_stamp` /
    `_faq_stamp`) — malformed knobs stamp nothing, valid knobs stamp exactly the
    vocabulary the composers read;
  - `composition_to_layout` wiring — the stamps ride the SHARED adaptation path
    (AS-46: every lane consumes them through adapt_brand_section);
  - composer output — pattern facts drive the markup (AS-44), every visible value
    rides brand-token var chains (AS-01/AS-02: sanctioned surface roles resolve
    through the token layer, unknown roles degrade);
  - conditional CSS shipping — pages without the stamps keep byte-identical CSS
    (AS-37 discipline), and existing composers render byte-identically without
    the new stamps.

Run:  ./venv/bin/python -m unittest brand_pipeline.tests.test_event_scaffolds
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

_BRAND_PIPELINE = Path(__file__).resolve().parent.parent
if str(_BRAND_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_BRAND_PIPELINE))
_REPO = _BRAND_PIPELINE.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

import compose_from_composition as cfc  # noqa: E402
import compose_section as cs            # noqa: E402
import component_render as cr           # noqa: E402

FIXTURE_DOC = {
    "brand": {"name": "Fixture"},
    "tokens": {
        "colors": {
            "text/on-primary": {"value": "#111111"},
            "text/on-inverse": {"value": "#ffffff"},
            "accent/warm-wash": {"value": "#fceef1"},
            "border/input": {"value": "#232325"},
        },
        "surfaces": {
            "surface/primary": {"bg": "#ffffff", "textPrimary": "text/on-primary"},
            "surface/accent": {"bg": "#511621", "schemeMode": "Inverse",
                               "textPrimary": "text/on-inverse",
                               "textAccent": "accent/warm-wash"},
        },
        "type": {"body": {"family": "Inter", "sizeRem": {"base": 1.0}}},
        "spacing": {},
    },
    # declared button families (top-level, the measured shape) ⇒ cta_shape resolves
    # "filled"; the secondary family exists so a declared ctaFamily survives the
    # family law instead of collapsing to primary.
    "buttons": {"primary": {"bg": "#0564ff", "height": "3rem"},
                "secondary": {"bg": "transparent", "border": "1px solid #232325"}},
}


def _ctx():
    return cr.make_context(FIXTURE_DOC, "surface/primary",
                           FIXTURE_DOC["tokens"]["surfaces"]["surface/primary"])


def _with_copy(layout, copy):
    """Register a LAYOUT_COPY entry for the layout id and return a restore fn."""
    saved = cs.LAYOUT_COPY
    cs.LAYOUT_COPY = {**cs.LAYOUT_COPY, layout["id"]: copy}
    return saved


# ── bento grid ───────────────────────────────────────────────────────────────────

class BentoStampTest(unittest.TestCase):
    def test_valid_knob_stamps_clamped_cells(self):
        stamp = cfc._bento_stamp({
            "cells": [{"span": 7, "rows": 2, "surface": "surface/accent", "lead": True},
                      {"span": 99}, {"span": 1}, {"rows": 9}, "junk"],
            "gap": "1rem", "collapseAt": 991})
        self.assertEqual(stamp["cells"][0],
                         {"span": 7, "rows": 2, "surface": "surface/accent", "lead": True})
        self.assertEqual(stamp["cells"][1], {"span": 12})   # clamped down
        self.assertEqual(stamp["cells"][2], {"span": 3})    # clamped up
        self.assertEqual(stamp["cells"][3], {"rows": 2})    # rows capped at 2
        self.assertEqual(stamp["cells"][4], {})             # junk cell -> no facts
        self.assertEqual(stamp["gap"], "1rem")
        self.assertEqual(stamp["collapseAt"], 991)

    def test_malformed_knob_stamps_nothing(self):
        self.assertIsNone(cfc._bento_stamp("bento"))
        self.assertIsNone(cfc._bento_stamp(7))

    def test_cards_section_with_bento_knob_routes_through_shared_path(self):
        section = {
            "id": "launch-bento", "archetype": "cards", "useCase": "features",
            "knobs": {"bento": {"cells": [{"span": 7}], "collapseAt": 991}},
            "slots": [
                {"name": "intro", "role": "section-title", "contract": "header",
                 "copy": {"heading": "One system", "eyebrow": "WHAT"}},
                {"name": "cells", "role": "module", "contract": "feature-item",
                 "copy": [{"eyebrow": "A", "heading": "Anchor", "text": "Body."}]},
            ],
        }
        layout = cfc.composition_to_layout(section)
        self.assertIsNotNone(layout.get("_bento"))
        self.assertEqual(layout["archetype"], "cards")
        # the shared adaptation path (AS-46) carries the same stamp.
        adapted, _copy, _sect = cfc.adapt_brand_section(section, dict(FIXTURE_DOC))
        self.assertEqual(adapted.get("_bento"), layout["_bento"])

    def test_malformed_bento_knob_keeps_module_grid(self):
        section = {"id": "x", "archetype": "cards", "knobs": {"bento": 3},
                   "slots": [{"name": "m", "role": "module", "contract": "feature-item",
                              "copy": [{"heading": "A", "text": "B"}]}]}
        layout = cfc.composition_to_layout(section)
        self.assertIsNone(layout.get("_bento"))


class BentoComposerTest(unittest.TestCase):
    LAYOUT = {"id": "launch-bento", "archetype": "cards",
              "surfaceIntent": "surface/primary",
              "_bento": {"cells": [
                  {"span": 7, "rows": 2, "lead": False},
                  {"span": 5, "surface": "surface/accent"},
                  {"span": 4, "surface": "surface/unknown"},
              ]}}
    CARDS = [
        {"eyebrow": "REMOTE AGENTS", "heading": "Deploy agents", "body": "Anchor body.",
         "link": "Save your seat"},
        {"eyebrow": "PAYROLL", "heading": "Catch errors", "body": "Support body."},
        {"eyebrow": "MCP", "heading": "Bring your own", "body": "Small body."},
    ]

    def _render(self):
        saved = _with_copy(self.LAYOUT, {"eyebrow": "WHAT", "heading": "One system",
                                         "cards": self.CARDS})
        try:
            return cs.compose_bento_grid(FIXTURE_DOC, self.LAYOUT, _ctx(), [], None)
        finally:
            cs.LAYOUT_COPY = saved

    def test_weights_ride_inline_vars(self):
        html = self._render()
        self.assertIn("--bn-span: 7", html)
        self.assertIn("--bn-rows: 2", html)
        self.assertIn("--bn-span: 5", html)

    def test_sanctioned_surface_resolves_through_token_layer(self):
        html = self._render()
        # the accent cell resolves the ROLE to token-layer var references (AS-02)
        self.assertIn("--bn-bg: var(--surface-surface-accent)", html)
        self.assertIn("--bn-ink: var(--color-text-on-inverse)", html)
        self.assertIn("--bn-accent: var(--color-accent-warm-wash)", html)
        # an UNDECLARED role stamps nothing — the cell keeps the panel default
        self.assertNotIn("surface-unknown", html)

    def test_cells_render_card_anatomy(self):
        html = self._render()
        self.assertEqual(html.count('<article class="cs-bento-cell'), 3)
        self.assertIn("REMOTE AGENTS", html)
        self.assertIn("Save your seat", html)

    def test_dispatcher_routes_stamped_layouts_only(self):
        # no stamp -> the module grid (byte-identical legacy path)
        plain = {"id": "p", "archetype": "cards", "surfaceIntent": "surface/primary"}
        saved = _with_copy(plain, {"eyebrow": "", "heading": "Grid",
                                   "cards": [{"caption": "A", "body": "B"}]})
        try:
            html = cs.compose_cards(FIXTURE_DOC, plain, _ctx(), [], None)
            expected = cs.compose_features_cards(FIXTURE_DOC, plain, _ctx(), [], None)
        finally:
            cs.LAYOUT_COPY = saved
        self.assertEqual(html, expected)
        self.assertNotIn("cs-bento", html)


# ── pricing tiers ────────────────────────────────────────────────────────────────

class TiersAdapterTest(unittest.TestCase):
    SECTION = {
        "id": "passes", "archetype": "cards", "useCase": "pricing",
        "knobs": {"tiers": {"emphasize": 1, "emphasisSurface": "surface/accent",
                            "collapseAt": 991}},
        "slots": [
            {"name": "intro", "role": "section-title", "contract": "header",
             "copy": {"heading": "The keynote is free.", "eyebrow": "PASSES",
                      "body": "Every pass includes the broadcast."}},
            {"name": "tiers", "role": "tier", "contract": "feature-item",
             "copy": [
                 {"name": "Virtual", "price": "Free",
                  "tagline": "The full launch.",
                  "features": ["Live keynote", "Recordings"],
                  "cta": "Save your seat"},
                 {"name": "Builder", "price": "$149",
                  "tagline": "For builders.",
                  "features": ["Everything in Virtual", "MCP lab"],
                  "cta": "Get the Builder pass", "ctaFamily": "secondary"},
             ]},
            {"name": "note", "role": "note", "contract": "caption",
             "copy": {"text": "Prices in USD."}},
        ],
    }

    def test_tiers_knob_swaps_translator_and_mapping(self):
        layout = cfc.composition_to_layout(self.SECTION)
        self.assertEqual(layout["_tiers"],
                         {"emphasize": 1, "emphasisSurface": "surface/accent",
                          "collapseAt": 991})
        copy = layout["_composerCopy"]
        self.assertEqual(len(copy["tiers"]), 2)
        self.assertEqual(copy["tiers"][0]["price"], "Free")
        self.assertEqual(copy["tiers"][1]["ctaFamily"], "secondary")
        self.assertEqual(copy["note"], "Prices in USD.")
        self.assertEqual(copy["subhead"], "Every pass includes the broadcast.")
        # the gate-facing mapping carries per-tier action entries
        contracts = [m["contract"] for m in layout["blockMapping"]]
        self.assertIn("button", contracts)


class TiersComposerTest(unittest.TestCase):
    LAYOUT = {"id": "passes", "archetype": "cards", "surfaceIntent": "surface/primary",
              "_tiers": {"emphasize": 1, "emphasisSurface": "surface/accent"}}
    TIERS = [
        {"name": "Virtual", "price": "Free", "priceMeta": "",
         "tagline": "The full launch.", "features": ["Keynote", "Recordings"],
         "cta": "Save your seat", "ctaFamily": ""},
        {"name": "Builder", "price": "$149", "priceMeta": "",
         "tagline": "For builders.", "features": ["MCP lab"],
         "cta": "Get the Builder pass", "ctaFamily": "secondary"},
    ]

    def _render(self, layout=None):
        layout = layout or self.LAYOUT
        saved = _with_copy(layout, {"eyebrow": "PASSES", "heading": "Free keynote",
                                    "note": "Prices in USD.", "tiers": self.TIERS})
        try:
            return cs.compose_pricing_tiers(FIXTURE_DOC, layout, _ctx(), [], None)
        finally:
            cs.LAYOUT_COPY = saved

    def test_emphasized_tier_paints_sanctioned_surface_head(self):
        html = self._render()
        # ONE emphasis device, once: the sanctioned surface head band exclusively —
        # the border ring is the ROLELESS degrade, never a second device on top.
        self.assertNotIn("cs-tier--emph", html)
        self.assertEqual(html.count("cs-tier-head--surface"), 1)
        self.assertIn("--bn-bg: var(--surface-surface-accent)", html)
        # the emphasis lands on tier index 1, not tier 0
        self.assertLess(html.index("Virtual"), html.index("cs-tier-head--surface"))

    def test_unknown_emphasis_surface_degrades_to_ring(self):
        layout = {**self.LAYOUT, "_tiers": {"emphasize": 0,
                                            "emphasisSurface": "surface/nope"}}
        html = self._render(layout)
        self.assertIn("cs-tier--emph", html)          # the ring class still lands
        self.assertNotIn("cs-tier-head--surface", html)
        self.assertNotIn("surface-nope", html)

    def test_anatomy_and_note(self):
        html = self._render()
        self.assertIn("cs-tier-price", html)
        self.assertIn("cs-tier-list", html)
        self.assertIn("Prices in USD.", html)
        # per-tier actions ride the measured button contract
        self.assertIn('class="c-button', html)
        self.assertIn("c-button--secondary", html)


# ── signup form ──────────────────────────────────────────────────────────────────

class FormFieldsStampTest(unittest.TestCase):
    SECTION = {
        "id": "signup", "archetype": "stack", "useCase": "signup",
        "slots": [
            {"name": "intro", "role": "heading", "contract": "header",
             "copy": {"heading": "Ready?", "body": "One registration gets you in."}},
            {"name": "form", "role": "signup", "contract": "form",
             "copy": {
                 "submit": "Save my seat",
                 "consent": "By registering, you agree.",
                 "success": "You're in.",
                 "meta": "Sept 17 · Virtual",
                 "fields": [
                     {"kind": "text", "label": "Full name", "span": "half",
                      "placeholder": "Alex Serra", "required": True,
                      "autocomplete": "name"},
                     {"kind": "email", "label": "Work email", "span": "half",
                      "helper": "Your pass lands here.", "required": True},
                     {"kind": "select", "label": "Company size",
                      "placeholder": "How many people?",
                      "options": ["1–10", "11–50"]},
                     {"kind": "radio-group", "label": "Pass",
                      "options": ["Virtual — free", "Builder — $149"],
                      "checkedIndex": 0,
                      "helper": "Paid passes continue to payment."},
                     {"kind": "checkbox", "label": "Product news from Remote"},
                     {"kind": "text"},                 # label-less -> dropped
                     {"kind": "martian", "label": "X"},  # unknown kind -> text
                 ]}},
        ],
    }

    def test_stamp_validates_fields_and_microcopy(self):
        stamp = cfc._form_fields_stamp(self.SECTION)
        self.assertEqual(len(stamp["fields"]), 6)      # the label-less one dropped
        self.assertEqual(stamp["fields"][0]["span"], "half")
        self.assertEqual(stamp["fields"][3]["checkedIndex"], 0)
        self.assertEqual(stamp["fields"][5]["kind"], "text")  # unknown coerced
        self.assertEqual(stamp["consent"], "By registering, you agree.")
        self.assertEqual(stamp["success"], "You're in.")
        self.assertEqual(stamp["meta"], "Sept 17 · Virtual")

    def test_fieldless_conversion_stamps_nothing(self):
        section = {"id": "cta", "archetype": "stack", "useCase": "cta",
                   "slots": [{"name": "form", "contract": "form",
                              "copy": {"placeholder": "you@co.com", "submit": "Go"}}]}
        self.assertIsNone(cfc._form_fields_stamp(section))
        layout = cfc.composition_to_layout(section)
        self.assertNotIn("_formFields", layout)

    def test_conversion_wiring_rides_shared_path(self):
        layout = cfc.composition_to_layout(self.SECTION)
        self.assertIsNotNone(layout.get("_formFields"))
        adapted, _c, _s = cfc.adapt_brand_section(self.SECTION, dict(FIXTURE_DOC))
        self.assertEqual(adapted.get("_formFields"), layout["_formFields"])


class SignupComposerTest(unittest.TestCase):
    def _layout(self, **extra):
        base = {
            "id": "signup", "archetype": "stack", "surfaceIntent": "surface/primary",
            "blockMapping": [{"slot": "main", "role": "heading", "contract": "header",
                              "usage": {"level": "h2"}}],
            "_formFields": {
                "fields": [
                    {"kind": "text", "label": "Full name", "span": "half",
                     "placeholder": "Alex Serra", "required": True},
                    {"kind": "email", "label": "Work email", "span": "half",
                     "helper": "Your pass lands here."},
                    {"kind": "select", "label": "Company size",
                     "placeholder": "How many people?", "options": ["1–10"]},
                    {"kind": "radio-group", "label": "Pass",
                     "options": ["Virtual — free", "Builder — $149"],
                     "checkedIndex": 0},
                    {"kind": "checkbox", "label": "Product news"},
                ],
                "consent": "By registering, you agree.",
                "success": "You're in.",
                "meta": "Sept 17 · Virtual",
            },
        }
        base.update(extra)
        return base

    def _render(self, layout=None):
        layout = layout or self._layout()
        saved = _with_copy(layout, {"eyebrow": "", "heading": "Ready?",
                                    "body": "One registration gets you in.",
                                    "cta": "Save my seat", "placeholder": ""})
        try:
            return cs.compose_conversion_stack(FIXTURE_DOC, layout, _ctx(), [], None)
        finally:
            cs.LAYOUT_COPY = saved

    def test_labels_bind_controls_accessibly(self):
        html = self._render()
        # every input/select id has a matching label[for]
        self.assertIn('for="signup-full-name"', html)
        self.assertIn('id="signup-full-name"', html)
        self.assertIn('for="signup-company-size"', html)
        self.assertIn("<legend", html)               # radio group announces itself
        self.assertIn('type="checkbox"', html)

    def test_field_facts_render(self):
        html = self._render()
        self.assertIn('placeholder="Alex Serra"', html)
        self.assertIn("Your pass lands here.", html)
        self.assertIn("disabled selected hidden", html)     # select prompt
        self.assertIn("checked", html)                      # radio default
        self.assertIn("By registering, you agree.", html)
        self.assertIn('aria-live="polite"', html)
        self.assertIn("Sept 17 · Virtual", html)

    def test_submit_rides_button_law(self):
        # fixture declares buttons.primary -> filled -> real <button class="c-button">
        html = self._render()
        self.assertIn('<button class="c-button" type="submit">Save my seat', html)
        # a typographic brand degrades the submit to the arrow-link register
        doc2 = {**FIXTURE_DOC,
                "tokens": {**FIXTURE_DOC["tokens"], "buttons": {}},
                "primitives": {"button": {"use": "never"}}}
        ctx2 = cr.make_context(doc2, "surface/primary",
                               doc2["tokens"]["surfaces"]["surface/primary"])
        layout = self._layout()
        saved = _with_copy(layout, {"eyebrow": "", "heading": "R", "body": "B.",
                                    "cta": "Save my seat", "placeholder": ""})
        try:
            html2 = cs.compose_conversion_stack(doc2, layout, ctx2, [], None)
        finally:
            cs.LAYOUT_COPY = saved
        self.assertIn("cs-signup-submit-link", html2)
        self.assertNotIn('class="c-button"', html2)

    def test_art_band_stamp_carries_signup(self):
        html = self._render(self._layout(_artSurface={}))
        self.assertIn("cs-conversion-sec--band", html)
        self.assertIn("cs-signup-sec", html)

    def test_no_stamp_keeps_legacy_conversion(self):
        layout = {"id": "cta", "archetype": "stack",
                  "surfaceIntent": "surface/primary", "blockMapping": []}
        saved = _with_copy(layout, {"eyebrow": "", "heading": "Start",
                                    "body": "", "cta": "Go",
                                    "placeholder": "you@co.com"})
        try:
            html = cs.compose_conversion_stack(FIXTURE_DOC, layout, _ctx(), [], None)
        finally:
            cs.LAYOUT_COPY = saved
        self.assertIn("c-form", html)               # the single-line newsletter device
        self.assertNotIn("cs-signup-grid", html)


# ── FAQ state grammar ────────────────────────────────────────────────────────────

class FaqScaffoldTest(unittest.TestCase):
    SECTION = {
        "id": "faq", "archetype": "stack", "useCase": "faq",
        "knobs": {"faq": {"open": 0, "hoverWash": "accent/warm-wash"}},
        "slots": [
            {"name": "intro", "role": "heading", "contract": "header",
             "copy": {"heading": "What to know", "eyebrow": "QUESTIONS"}},
            {"name": "items", "role": "faq", "contract": "faq-item",
             "copy": [{"question": "Is it free?", "answer": "Yes."},
                      {"question": "Refunds?", "answer": "Until Sept 10."}]},
        ],
    }

    def test_use_case_routes_to_faq_not_generic_flow(self):
        layout = cfc.composition_to_layout(self.SECTION)
        self.assertEqual(layout["archetype"], "stack")
        self.assertEqual(layout["_faq"], {"exclusive": True, "open": 0,
                                          "hoverWash": "accent/warm-wash"})
        self.assertEqual(layout["_composerCopy"]["items"],
                         [("Is it free?", "Yes."), ("Refunds?", "Until Sept 10.")])
        self.assertEqual(cs.scaffold_key(layout), "faq")

    def test_composer_exclusivity_open_state_and_wash(self):
        layout, copy, _ = cfc.adapt_brand_section(self.SECTION, dict(FIXTURE_DOC))
        saved = _with_copy(layout, copy)
        try:
            html = cs.compose_stack(FIXTURE_DOC, layout, _ctx(), [], None)
        finally:
            cs.LAYOUT_COPY = saved
        # AS-40: one platform-enforced exclusivity group, evidence-driven open item
        self.assertEqual(html.count('name="faq-faq"'), 2)
        self.assertEqual(html.count(" open>"), 1)
        self.assertLess(html.index(" open>"), html.index("Refunds?"))
        # the wash role resolved through the token layer onto the wrapper
        self.assertIn("cs-faq--stated", html)
        self.assertIn("--faq-hover-bg: var(--color-accent-warm-wash)", html)

    def test_active_surface_resolves_and_unknown_degrades(self):
        knob = {"open": 0, "activeSurface": "surface/accent"}
        layout, copy, _ = cfc.adapt_brand_section(
            {**self.SECTION, "knobs": {"faq": knob}}, dict(FIXTURE_DOC))
        saved = _with_copy(layout, copy)
        try:
            html = cs.compose_stack(FIXTURE_DOC, layout, _ctx(), [], None)
        finally:
            cs.LAYOUT_COPY = saved
        self.assertIn("--faq-active-bg: var(--surface-surface-accent)", html)
        self.assertIn("--faq-active-ink: var(--color-text-on-inverse)", html)
        # unknown role -> no stated variant at all
        layout2, copy2, _ = cfc.adapt_brand_section(
            {**self.SECTION, "knobs": {"faq": {"activeSurface": "surface/nope"}}},
            dict(FIXTURE_DOC))
        saved = _with_copy(layout2, copy2)
        try:
            html2 = cs.compose_stack(FIXTURE_DOC, layout2, _ctx(), [], None)
        finally:
            cs.LAYOUT_COPY = saved
        self.assertNotIn("cs-faq--stated", html2)


# ── poster hero panel extensions ─────────────────────────────────────────────────

class HeroPanelPosterTest(unittest.TestCase):
    def _render(self, panel, alignment=None):
        layout = {"id": "hero", "archetype": "stack",
                  "surfaceIntent": "surface/primary", "_artPanel": panel,
                  "_composition": {"useCase": "hero"}}
        if alignment:
            layout["alignment"] = alignment
        saved = _with_copy(layout, {"eyebrow": "REMOTE LAUNCH DAY",
                                    "heading": "Meet the agents",
                                    "subhead": "On September 17.",
                                    "cta": "Save your seat"})
        try:
            return cs.compose_stack_hero(FIXTURE_DOC, layout, _ctx(), [], None)
        finally:
            cs.LAYOUT_COPY = saved

    def test_poster_slots_render_when_authored(self):
        html = self._render({"asset": None, "eyebrow": True,
                             "meta": "Sept 17 · 16:00 UTC · Virtual"},
                            alignment={"anchor": "centered"})
        self.assertIn("REMOTE LAUNCH DAY", html)
        self.assertIn("cs-hero-panel-meta", html)
        self.assertIn("Sept 17 · 16:00 UTC · Virtual", html)
        self.assertIn("cs-hero-panel--center", html)

    def test_unauthored_panel_stays_byte_identical(self):
        html = self._render({"asset": None})
        self.assertNotIn("cs-eyebrow-wrap", html)
        self.assertNotIn("cs-hero-panel-meta", html)
        self.assertNotIn("cs-hero-panel--center", html)


# ── conditional CSS shipping + placement facts ───────────────────────────────────

class ScaffoldShippingTest(unittest.TestCase):
    def test_no_stamps_no_new_css(self):
        css = cs.device_scaffold_css([{"id": "a", "archetype": "cards"},
                                      {"id": "b", "archetype": "stack"}])
        for marker in ("cs-bento", "cs-tier", "cs-signup", "cs-faq--stated"):
            self.assertNotIn(marker, css)

    def test_stamps_ship_their_scaffold_only(self):
        css = cs.device_scaffold_css([{"_bento": {"cells": []}}])
        self.assertIn(".cs-bento", css)
        self.assertNotIn(".cs-tier", css)
        css = cs.device_scaffold_css([{"_tiers": {}}, {"_formFields": {"fields": []}}])
        self.assertIn(".cs-tiers", css)
        self.assertIn(".cs-signup-grid", css)
        css = cs.device_scaffold_css([{"_faq": {"hoverWash": "accent/warm-wash"}}])
        self.assertIn("cs-faq--stated", css)
        # a knob-less faq stamp ships NO state css (nothing to drive it)
        self.assertEqual("", cs.device_scaffold_css([{"_faq": {"exclusive": True}}]))

    def test_placement_css_emits_collapse_tiers_and_gap(self):
        css = cs.layout_placement_css("#sec-2", {
            "id": "bento", "_bento": {"cells": [], "gap": "1rem", "collapseAt": 991}})
        self.assertIn("--bn-gap: 1rem;", css)
        self.assertIn("@container frame (max-width: 991px)", css)
        self.assertIn("#sec-2 .cs-bento { grid-template-columns: 1fr; }", css)
        css = cs.layout_placement_css("#sec-5", {
            "id": "tiers", "_tiers": {"collapseAt": 767}})
        self.assertIn("#sec-5 .cs-tiers { grid-template-columns: 1fr; }", css)
        # no facts -> no rules (the structural floor lives in the scaffold)
        self.assertEqual("", cs.layout_placement_css("#sec-1", {"id": "x"}))


# ── shared disclosure motion (AS-47) ─────────────────────────────────────────────

def _motion_doc():
    d = dict(FIXTURE_DOC)
    d["voice"] = {"motionSpec": {"easing": {"primary": "cubic-bezier(0, 0, 0.2, 1)"},
                                 "durations": {"fast": "150ms", "base": "200ms",
                                               "slow": "400ms"}}}
    return d


class DisclosureMotionTest(unittest.TestCase):
    """AS-47 regression lock: a details-emitting scaffold on a motion-bearing brand
    MUST ship the shared disclosure-motion CSS (the event page's agenda/FAQ rendered
    static while the homepage accordion animated — two copies of one mechanic, one
    of them forgotten); a motion-less doc must ship NONE (instant-toggle degrade,
    never invented timing)."""
    FAQ_LAYOUT = {"id": "agenda", "archetype": "stack", "_faq": {"exclusive": True}}
    ACC_LAYOUT = {"id": "infra", "archetype": "split", "_accordion": {}}

    def test_faq_family_emits_full_motion_grammar(self):
        css = cs.disclosure_motion_css(_motion_doc(), [self.FAQ_LAYOUT])
        # panel height 0 -> auto on the platform slot, brand tiers only
        self.assertIn(".c-faq-item::details-content", css)
        self.assertIn("interpolate-size: allow-keywords", css)
        self.assertIn("block-size var(--c-motion-base) var(--c-ease)", css)
        # trigger wash + marker turn + state fade ride the aliases
        self.assertIn(".c-faq-q { transition: background-color var(--c-motion-fast)", css)
        self.assertIn(".c-faq-icon { transition: transform var(--c-motion-base)", css)
        # reduced-motion degrade
        self.assertIn("prefers-reduced-motion: reduce", css)

    def test_accordion_family_emits_same_mechanic(self):
        css = cs.disclosure_motion_css(_motion_doc(), [self.ACC_LAYOUT])
        self.assertIn(".c-acc-item::details-content", css)
        self.assertIn(".c-acc-chev { transition: transform var(--c-motion-base)", css)
        self.assertNotIn(".c-faq-item", css)

    def test_both_families_one_source(self):
        css = cs.disclosure_motion_css(_motion_doc(), [self.ACC_LAYOUT, self.FAQ_LAYOUT])
        self.assertIn(".c-acc-item::details-content", css)
        self.assertIn(".c-faq-item::details-content", css)

    def test_motionless_doc_degrades_to_nothing(self):
        # no captured motion language -> no motion CSS at all (never invented values)
        self.assertEqual("", cs.disclosure_motion_css(dict(FIXTURE_DOC),
                                                      [self.FAQ_LAYOUT, self.ACC_LAYOUT]))
        # a PARTIAL spec (easing without the duration trio) also degrades
        d = dict(FIXTURE_DOC)
        d["voice"] = {"motionSpec": {"easing": {"primary": "ease"}}}
        self.assertEqual("", cs.disclosure_motion_css(d, [self.FAQ_LAYOUT]))

    def test_no_disclosure_layouts_emit_nothing(self):
        self.assertEqual("", cs.disclosure_motion_css(
            _motion_doc(), [{"id": "cards", "archetype": "cards", "_bento": {}}]))

    def test_timing_rides_tokens_only(self):
        # every duration/easing in the block is a bare brand alias — zero literals
        css = cs.disclosure_motion_css(_motion_doc(), [self.FAQ_LAYOUT, self.ACC_LAYOUT])
        rules = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
        self.assertNotRegex(rules, r"\d+m?s\b")
        self.assertNotIn("cubic-bezier", rules)

    def test_scaffold_constants_carry_no_private_motion_fork(self):
        # the mechanic lives in ONE place: neither disclosure scaffold constant may
        # grow its own ::details-content/transition copy back (AS-46 spirit)
        for const in (cs.SCAFFOLD_ACCORDION_CSS, cs.SCAFFOLD_FAQ_CSS,
                      cs.SCAFFOLD_FAQ_STATE_CSS):
            self.assertNotIn("::details-content", const)
            self.assertNotIn("interpolate-size", const)


if __name__ == "__main__":
    unittest.main()
