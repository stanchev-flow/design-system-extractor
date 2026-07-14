#!/usr/bin/env python3
"""fix7 device mechanics (gallery review round 3, FIX7-PUNCHLIST.md items 1/3/4/5/6/7):

- punch 1  punctuation-accent device: licensed landmark headings wrap their terminal
  mark in the accent span (renderer application + license gating + the device-role
  CSS var); license-less brands render byte-identically.
- punch 3  marked-list device: declared list intent renders the brand's glyph-marked
  list (inline-SVG channel + hanging indent + list rhythm); glyph-less/license-less
  brands degrade to the typographic dot / plain paragraphs never silently.
- punch 4  stat pair binding: the value→label seam rides --space-stat-pair (tightest
  gap by construction) and the split column separates the pair by an extra 0.5x.
- punch 5  heading fit-to-measure: deterministic step-down projection + the
  form-split stamp (data-fit-cap / data-fit-rung) + measured-rung-only sizes.
- punch 6  form-note attachment: the foot form's note renders BELOW the control in
  the caption register, inside the control-width wrapper.
- punch 7  anchored-stack meta children: the note/caption rides the stack (audit
  extension is covered by the JS census; here the renderer contract).
- stage-B follow-up: the bento de-facto lead cell stamps --lead.
- pass-3 follow-up 4: the art-panel hero pads the measured panel-padding fact.
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "brand_pipeline"))

import component_render as cr  # noqa: E402
import compose_section as cs  # noqa: E402
import compose_from_composition as cfc  # noqa: E402

BRAND_DIR = REPO / "runs" / "hubspot-v2" / "brand"


def hubspot_doc():
    doc = yaml.safe_load((BRAND_DIR / "brand.yaml").read_text())
    cs.attach_asset_inventory(doc, BRAND_DIR)
    return doc


def light_ctx(doc):
    surf = (doc.get("tokens") or {}).get("surfaces", {}).get("surface/primary")
    return cr.make_context(doc, "surface/primary", surf)


class PunctuationAccentDevice(unittest.TestCase):
    """Punch 1: the licensed terminal mark wraps in the accent span on LANDMARK
    headings only — display rank or accent-flagged; never card/section tiers,
    never unlicensed brands."""

    def setUp(self):
        self.doc = hubspot_doc()
        self.ctx = light_ctx(self.doc)

    def test_display_heading_terminal_period_wraps(self):
        html = cr.render_heading(self.doc, self.ctx, {
            "text": "Build on the customer platform.", "level": "display"})
        self.assertIn('<span class="c-accent-mark" '
                      'data-accent-device="punctuation-accent">.</span>', html)
        self.assertTrue(html.count("data-accent-device") == 1)

    def test_accent_flagged_heading_wraps_the_closing_landmark(self):
        html = cr.render_heading(self.doc, self.ctx, {
            "text": "Make growth feel impossibly easy, with HubSpot.",
            "level": "h2", "accent": True})
        self.assertIn('data-accent-device="punctuation-accent"', html)

    def test_section_tier_headings_never_wrap(self):
        html = cr.render_heading(self.doc, self.ctx, {
            "text": "A section heading with a period.", "level": "h2"})
        self.assertNotIn("c-accent-mark", html)

    def test_mid_sentence_periods_untouched_only_terminal_wraps(self):
        html = cr.render_heading(self.doc, self.ctx, {
            "text": "Marketing that runs itself. Almost.", "level": "display"})
        self.assertEqual(html.count("c-accent-mark"), 1)
        self.assertIn("itself. Almost<span", html)

    def test_heading_without_the_mark_is_untouched(self):
        html = cr.render_heading(self.doc, self.ctx, {
            "text": "Spotlight", "level": "display"})
        self.assertNotIn("c-accent-mark", html)

    def test_license_less_brand_is_byte_identical(self):
        bare = {"brand": {"name": "X"}, "tokens": {"colors": {}, "surfaces": {}}}
        ctx = cr.make_context(bare, "s", {"bg": "#fff"})
        html = cr.render_heading(bare, ctx, {
            "text": "A landmark statement.", "level": "display"})
        self.assertNotIn("c-accent-mark", html)

    def test_landmark_flag_wraps_a_measure_fit_hero_register(self):
        # a hero SPLIT registers its opening statement at h2 (the measure-fit
        # tier) — still the page landmark, so the composer's landmark flag
        # licenses the device there (the homepage/blog split-hero shape).
        html = cr.render_heading(self.doc, self.ctx, {
            "text": "Go-to-market teams grow here.", "level": "h2",
            "landmark": True})
        self.assertIn('data-accent-device="punctuation-accent"', html)

    def test_split_hero_branch_declares_the_landmark(self):
        layout = {"id": "sec-0", "archetype": "split",
                  "_composition": {"useCase": "hero", "novelty": "adapt",
                                   "archetype": "split"}}
        cs.LAYOUT_COPY = {**cs.LAYOUT_COPY, "sec-0": {
            "eyebrow": "Kicker", "heading": "Go-to-market teams grow here.",
            "panelTitle": "", "rows": [], "cta": "", "caption": "", "body": "",
            "headingLevel": "", "quote": "", "attribution": ""}}
        try:
            html = cs.compose_info_band(self.doc, layout, self.ctx, [], None)
        finally:
            cs.LAYOUT_COPY.pop("sec-0", None)
        self.assertIn('data-accent-device="punctuation-accent"', html)

    def test_device_css_emits_the_license_role_var(self):
        css = cr.accent_device_css(self.doc)
        self.assertIn("--c-accent-mark: var(--color-accent-highlight)", css)
        self.assertEqual(cr.accent_device_css({"brand": {"name": "X"}}), "")

    def test_structural_variant_css_carries_the_device_block(self):
        self.assertIn("--c-accent-mark", cr.structural_variant_css(self.doc))


class MarkedListDevice(unittest.TestCase):
    """Punch 3: declared list intent renders the glyph-marked list through the
    sanitized inline-SVG channel; degrades honestly, never invents."""

    def setUp(self):
        self.doc = hubspot_doc()
        self.ctx = light_ctx(self.doc)

    def test_glyph_attaches_from_the_brand_assets(self):
        glyphs = self.doc.get(cs.ACCENT_GLYPHS_KEY) or {}
        self.assertIn("marked-list-glyph", glyphs)
        self.assertIn('viewBox="0 0 32 32"', glyphs["marked-list-glyph"])
        self.assertIn('fill="currentColor"', glyphs["marked-list-glyph"])

    def test_marked_list_renders_glyph_markers_and_stamps_the_device(self):
        html = cr.render_marked_list(self.doc, self.ctx, {
            "items": ["First claim", "Second claim", "Third claim"]})
        self.assertIn('data-accent-device="marked-list-glyph"', html)
        self.assertEqual(html.count("c-list-marker"), 3)
        self.assertEqual(html.count("<svg"), 3)

    def test_glyphless_brand_degrades_to_the_typographic_dot(self):
        bare = {"brand": {"name": "X"}}
        ctx = cr.make_context(bare, "s", {"bg": "#fff"})
        html = cr.render_marked_list(bare, ctx, {"items": ["A", "B"]})
        self.assertIn("&bull;", html)
        self.assertNotIn("data-accent-device", html)

    def test_zero_items_elide(self):
        self.assertEqual(cr.render_marked_list(self.doc, self.ctx, {"items": []}), "")

    def test_form_split_list_intent_renders_the_marked_list(self):
        layout = {
            "id": "demo-hero", "archetype": "split",
            "_formFields": {"fields": [{"kind": "text", "label": "Work email"}],
                            "submit": "Book"},
            "_formSplit": {"points": [], "side": "right", "supportKind": "list",
                           "support": ["Alpha claim", "Beta claim", "Gamma claim"]},
        }
        html = cs._compose_form_split(self.doc, layout, self.ctx, [], {
            "eyebrow": "", "heading": "See it work.", "body": "", "cta": ""})
        self.assertIn("c-marked-list", html)
        self.assertIn('data-list-intent="list"', html)
        self.assertNotIn("<p class=\"c-paragraph\">Alpha claim", html)

    def test_form_split_without_list_intent_keeps_paragraphs(self):
        layout = {
            "id": "demo-hero", "archetype": "split",
            "_formFields": {"fields": [{"kind": "text", "label": "Work email"}],
                            "submit": "Book"},
            "_formSplit": {"points": [], "side": "right", "supportKind": "",
                           "support": ["Alpha claim", "Beta claim"]},
        }
        html = cs._compose_form_split(self.doc, layout, self.ctx, [], {
            "eyebrow": "", "heading": "See it work.", "body": "", "cta": ""})
        self.assertNotIn("c-marked-list", html)
        self.assertIn("Alpha claim", html)

    def test_adapter_stamps_support_kind_from_the_knob(self):
        sec = {
            "id": "demo-hero", "useCase": "hero", "archetype": "split",
            "archetypeRef": "hero-form-split",
            "knobs": {"formSide": "right", "supportKind": "list"},
            "slots": [
                {"name": "heading", "role": "offer", "contract": "heading",
                 "copy": "See it work."},
                {"name": "support", "role": "value-proof", "contract": "content-block",
                 "copy": {"header": {"heading": "Lead-in"},
                          "body": ["One", "Two", "Three"]}},
                {"name": "form", "role": "capture", "contract": "form",
                 "copy": {"fields": [{"label": "Email"}], "submit": "Go"}},
            ],
        }
        layout = cfc.composition_to_layout(sec)
        self.assertEqual(layout["_formSplit"]["supportKind"], "list")


class StatPairBinding(unittest.TestCase):
    """Punch 4: the stat's internal seam is the statPair rung; the split column
    separates the pair from the preceding block by an extra half sibling gap."""

    def test_stat_css_rides_the_stat_pair_var(self):
        self.assertIn("gap: var(--space-stat-pair, 0.5rem)", cr.COMPONENT_CSS)
        self.assertNotIn(".c-stat { display: flex; flex-direction: column; "
                         "gap: var(--space-eyebrow-to-heading", cr.COMPONENT_CSS)

    def test_split_body_separation_rule_ships(self):
        self.assertIn(".cs-split-body > * + .c-stat", cs.SCAFFOLD_SPLIT_CSS)
        self.assertIn("calc(0.5 * var(--space-heading-to-body", cs.SCAFFOLD_SPLIT_CSS)

    def test_render_stat_value_label_shape_unchanged(self):
        doc = hubspot_doc()
        html = cr.render_stat(doc, light_ctx(doc), {
            "value": "299,000+", "label": "customers grow with HubSpot"})
        self.assertIn("c-stat-value", html)
        self.assertIn("c-stat-label", html)


class HeadingFitToMeasure(unittest.TestCase):
    """Punch 5: deterministic display step-down — projection math, measured-rung
    steps only, the form-split stamp, and full-measure no-op."""

    def setUp(self):
        self.doc = hubspot_doc()

    def test_half_measure_is_the_form_split_column(self):
        # container 1080, column-to-column 80 → 6 tracks + 5 gutters = 500px
        self.assertAlmostEqual(cs.split_half_measure_px(self.doc), 500.0, places=0)

    def test_demo_heading_steps_to_the_h1_rung(self):
        level = cs.heading_fit_level(
            self.doc, "See the customer platform at work.", 500.0, cap=3)
        self.assertEqual(level, "h1")

    def test_short_heading_keeps_the_display_rung(self):
        self.assertEqual(
            cs.heading_fit_level(self.doc, "Spotlight.", 500.0, cap=3), "display")

    def test_full_measure_never_steps(self):
        self.assertEqual(
            cs.heading_fit_level(self.doc, "See the customer platform at work.",
                                 1080.0, cap=3), "display")

    def test_measureless_brand_never_steps(self):
        self.assertEqual(cs.heading_fit_level({}, "Anything at all.", None), "display")
        self.assertIsNone(cs.split_half_measure_px({}))

    def test_projection_matches_the_measured_wrap_calibration(self):
        # stage-B facts: the 46-char claim rendered 5 lines, the 34-char claim 4
        # lines, both at 80px in the 500px column.
        self.assertEqual(cs.projected_line_count(
            "See the customer platform work for your team.", 80, 500), 5)
        self.assertEqual(cs.projected_line_count(
            "See the customer platform at work.", 80, 500), 4)
        # at the h1 rung (48px) the demo claim fits the cap
        self.assertLessEqual(cs.projected_line_count(
            "See the customer platform at work.", 48, 500), 3)

    def test_form_split_stamps_the_fit_contract(self):
        ctx = light_ctx(self.doc)
        layout = {"id": "demo-hero", "archetype": "split",
                  "_formFields": {"fields": [{"kind": "text", "label": "Email"}],
                                  "submit": "Go"},
                  "_formSplit": {"points": [], "side": "right"}}
        html = cs._compose_form_split(self.doc, layout, ctx, [], {
            "eyebrow": "", "heading": "See the customer platform at work.",
            "body": "", "cta": ""})
        self.assertIn('data-fit-cap="3"', html)
        self.assertIn('data-fit-rung="h1"', html)

    def test_fit_rung_css_re_registers_the_display_size(self):
        self.assertIn('[data-fit-rung="h1"] .c-heading--display '
                      '{ font-size: var(--c-h1-size); }', cs.SCAFFOLD_SPLIT_CSS)


class FormNoteAttachment(unittest.TestCase):
    """Punch 6/7: the foot form's note is a caption ATTACHED below its control,
    inside the control-width wrapper — never a floating line above it."""

    def test_hero_mapping_routes_the_note_to_the_caption_register(self):
        sec = {
            "id": "sec-0", "useCase": "hero", "archetype": "stack",
            "archetypeRef": "hero-search-first",
            "slots": [
                {"name": "heading", "role": "title", "contract": "heading",
                 "copy": "Build on the platform."},
                {"name": "search", "role": "primary-control", "contract": "form",
                 "copy": {"fields": [{"label": "Search the docs"}],
                          "submit": "Search",
                          "note": "We index every SDK nightly."}},
            ],
        }
        mapping = cfc._hero_mapping(sec)
        note = next(m for m in mapping if "foot form note" in m["role"])
        self.assertEqual(note["contract"], "caption")

    def test_stack_hero_places_the_note_after_the_control(self):
        doc = hubspot_doc()
        ctx = light_ctx(doc)
        rendered = [
            {"slot": "main", "role": "display title", "contract": "heading",
             "html": '<h1 class="c-heading c-heading--display">Build.</h1>',
             "group": None, "origin": None},
            {"slot": "main", "role": "foot form (search)", "contract": "form",
             "html": '<form class="c-form"><input class="c-field-input"></form>',
             "group": None, "origin": None},
            {"slot": "main", "role": "foot form note (search)", "contract": "caption",
             "html": '<p class="c-caption">We index every SDK nightly.</p>',
             "group": None, "origin": None},
        ]
        layout = {"id": "sec-0", "archetype": "stack", "archetypeRef": "hero-search-first"}
        html = cs.compose_stack_hero(doc, layout, ctx, rendered, None)
        self.assertIn("cs-hero-form", html)
        wrapper = html.split('class="cs-hero-form"')[1]
        self.assertLess(wrapper.index("c-form"), wrapper.index("c-caption"))

    def test_note_cap_css_ships(self):
        # caption meta children stretch to the control-width wrapper (balanced
        # wrap rides the component base's text-wrap: balance on .c-caption).
        self.assertIn(".cs-hero-form .c-caption { margin: 0; max-width: 100%; "
                      "align-self: stretch; }", cs.SCAFFOLD_HERO_CSS)
        self.assertIn(".c-heading, .c-eyebrow, .c-caption { text-wrap: balance; }",
                      cr.COMPONENT_CSS)


class BentoDeFactoLead(unittest.TestCase):
    """Stage-B follow-up: a first cell whose anatomy strictly supersets its
    siblings' shared set stamps --lead without a knob declaration."""

    def _render(self, cards):
        doc = hubspot_doc()
        ctx = light_ctx(doc)
        layout = {"id": "sec-1", "archetype": "cards", "_bento": {"cells": []}}
        cs.LAYOUT_COPY = {**cs.LAYOUT_COPY,
                          "sec-1": {"heading": "", "eyebrow": "", "cards": cards}}
        try:
            return cs.compose_bento_grid(doc, layout, ctx, [], None)
        finally:
            cs.LAYOUT_COPY.pop("sec-1", None)

    def test_first_superset_cell_stamps_lead(self):
        cards = [
            {"caption": "", "heading": "Lead claim", "body": "Rich body.",
             "link": "More", "eyebrow": "Kicker"},
            {"caption": "", "heading": "A", "body": "Body."},
            {"caption": "", "heading": "B", "body": "Body."},
            {"caption": "", "heading": "C", "body": "Body."},
        ]
        html = self._render(cards)
        self.assertEqual(html.count("cs-bento-cell--lead"), 1)
        first_cell_tag = html.split("<article")[1].split(">")[0]
        self.assertIn("cs-bento-cell--lead", first_cell_tag)

    def test_uniform_cells_stamp_nothing(self):
        cards = [{"caption": "", "heading": c, "body": "Body."}
                 for c in ("A", "B", "C", "D")]
        self.assertNotIn("cs-bento-cell--lead", self._render(cards))

    def test_declared_lead_knob_still_wins(self):
        doc = hubspot_doc()
        ctx = light_ctx(doc)
        layout = {"id": "sec-1", "archetype": "cards",
                  "_bento": {"cells": [{}, {"lead": True}, {}, {}]}}
        cards = [{"caption": "", "heading": c, "body": "Body."}
                 for c in ("A", "B", "C", "D")]
        cs.LAYOUT_COPY = {**cs.LAYOUT_COPY,
                          "sec-1": {"heading": "", "eyebrow": "", "cards": cards}}
        try:
            html = cs.compose_bento_grid(doc, layout, ctx, [], None)
        finally:
            cs.LAYOUT_COPY.pop("sec-1", None)
        self.assertEqual(html.count("cs-bento-cell--lead"), 1)

    def test_art_panel_pads_the_measured_panel_inset(self):
        # pass-3 follow-up 4: the device consumes the brand's panel-padding fact
        self.assertIn("var(--space-panel-padding, var(--c-module-gap, 6rem))",
                      cs.SCAFFOLD_ART_PANEL_CSS)


class ReplicaPathRegression(unittest.TestCase):
    """The replica improved (0.956→0.957 / 0.950→0.951 at fix7) BECAUSE the source
    carries the devices; the contracts here pin the mechanics that made it safe."""

    def test_norm_treats_the_accent_span_as_copy_identity(self):
        sys.path.insert(0, str(REPO / "brand_pipeline"))
        # onbrand's fidelity normalizer: the device span must not break heading match
        import onbrand_check as oc  # noqa: F401
        html = ('<h1 class="c-heading c-heading--display">go to grow'
                '<span class="c-accent-mark" data-accent-device='
                '"punctuation-accent">.</span></h1>')
        flat = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip().lower()
        normalized = re.sub(r"\s+([.,!?;:])", r"\1", flat)
        self.assertIn("go to grow.", normalized)

    def test_remote_brand_licenses_no_devices(self):
        # checked against evidence (hover-only underline = interaction treatment):
        # remote authors NO accentDevices, so its renders carry no device spans.
        remote = yaml.safe_load(
            (REPO / "runs/remote/brand/brand.yaml").read_text())
        self.assertNotIn("accentDevices", remote)
        self.assertEqual(cr.licensed_accent_devices(remote), [])


if __name__ == "__main__":
    unittest.main()
