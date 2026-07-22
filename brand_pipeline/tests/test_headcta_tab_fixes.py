#!/usr/bin/env python3
"""Regression tests for the hubspot-v3 header / CTA / tab fidelity fixes
(header-cta-tab-diagnostic.md D1/D3/D4). All three were captured-in-facts →
dropped-in-render (D1/D4) or a regression (D3); the fixes are fact-gated,
brand/palette-agnostic, and encoded in the renderer + audit — never brand values
or section/token names.

  D1 — dual-action register hierarchy (AS-59). The overlay action emitter reads the
       per-action register from the authored styleHint/variant/role (not `variant`
       alone) and COALESCES sibling action slots into one group so exactly one filled
       primary survives and every sibling takes its measured secondary register. The
       AS-59 audit gains a split-group advisory for adjacent single-action groups.

  D3 — tab-rail alignment is its OWN captured fact, independent of the section text
       anchor (reverts the D6 regression that coupled the tablist to the anchor). No
       captured fact ⇒ the centered scaffold default stands (nothing emitted); tab
       justification is never derived from resolved.anchor.

  D4 — headrail treatment-kind synonyms canonicalize so `dotted-leader-rule` stamps
       `_headRail`; a recipe-bound rail slot is sanctioned by its recipe binding; the
       captured device vocabulary (treatment kind + bound recipe/variant name) rides
       the rail prose so a prose-authored recipe still lights up pill/dotted/outlined.

Run:  ./venv/bin/python -m unittest brand_pipeline.tests.test_headcta_tab_fixes
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

_BRAND_PIPELINE = Path(__file__).resolve().parent.parent
if str(_BRAND_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_BRAND_PIPELINE))

import component_render as cr    # noqa: E402
import compose_section as cs     # noqa: E402
import layout_library as ll      # noqa: E402

FIXTURE_DOC = {
    "brand": {"name": "Fixture"},
    "tokens": {
        "colors": {"text/on-primary": {"value": "#111111"}},
        "surfaces": {"surface/primary": {"bg": "#ffffff",
                                         "textPrimary": "text/on-primary"}},
        "type": {"body": {"family": "Inter", "sizeRem": {"base": 1.0}}},
        "spacing": {},
    },
}

# a filled-CTA brand with a measured OUTLINE secondary family (palette-agnostic:
# the register is chosen by the family's declared `style`, never its hex).
BTN_DOC = {**FIXTURE_DOC, "buttons": {
    "primary": {"bg": "#ff4800", "fg": "#ffffff", "radius": "8px", "style": "filled"},
    "secondary": {"bg": "#ffffff", "fg": "#ff4800", "border": "2px solid #ff4800",
                  "style": "outline"},
}}


def _ctx(doc=FIXTURE_DOC):
    return cr.make_context(doc, "surface/primary",
                           doc["tokens"]["surfaces"]["surface/primary"])


def _pattern(**kw):
    base = dict(
        id="p", use_case="content", archetype_ref="band", surface_intent="primary",
        intent="", content_shape={"slots": []}, special_treatments=[], responsive={},
        variant_knobs={}, origin="extracted", confidence="high",
        scope="design-language", provenance=[])
    base.update(kw)
    return ll.Pattern(**base)


# ── D4: treatment-kind synonym canonicalization ──────────────────────────────────


class TreatmentKindCanonTest(unittest.TestCase):
    def test_headrail_synonyms_map_to_canonical(self):
        for syn in ("dotted-leader-rule", "dotted-leader", "leader-rule",
                    "header-rail", "head-rail", "headrail", "section-headrail",
                    "DOTTED-LEADER-RULE"):
            self.assertEqual(cs._canonical_treatment_kind(syn), "dotted-rule-rail",
                             syn)

    def test_canonical_token_passes_through(self):
        self.assertEqual(cs._canonical_treatment_kind("dotted-rule-rail"),
                         "dotted-rule-rail")

    def test_unknown_kind_lowercased_unchanged(self):
        self.assertEqual(cs._canonical_treatment_kind("Marquee"), "marquee")
        self.assertEqual(cs._canonical_treatment_kind(None), "")


# ── D4: the rail stamps + note-prose enrichment (fact-gated) ─────────────────────


class HeadrailStampTest(unittest.TestCase):
    def _stamp(self, treatment, slot):
        pat = _pattern(content_shape={"slots": [slot]}, special_treatments=[treatment])
        layout = {"id": "sec"}
        with mock.patch.object(cs, "resolve_pattern", return_value=(pat, "ref")):
            cs.stamp_pattern_devices(FIXTURE_DOC, layout,
                                     Path("/nonexistent/brand.yaml"))
        return layout

    def test_synonym_on_recipe_bound_slot_stamps_headrail(self):
        # the exact hubspot-v3 sec-6 shape: `dotted-leader-rule` (a synonym) on a
        # recipe-bound headrail slot with NO explicit `sanctioned` flag.
        layout = self._stamp(
            {"kind": "dotted-leader-rule", "target": "headrail"},
            {"name": "headrail", "role": "section-headrail",
             "recipeRef": {"recipe": "section-headrail", "variant": "outlined-pill"}})
        self.assertIsInstance(layout.get("_headRail"), dict)
        # the captured device vocabulary rides the prose so the shared helper's
        # measured-prose paths (pill / dotted / outlined) fire from real facts.
        note = (layout["_headRail"].get("note") or "").lower()
        self.assertIn("dotted-leader-rule", note)
        self.assertIn("outlined-pill", note)

    def test_recipe_binding_sanctions_even_without_flag(self):
        # non-recipe-bound, non-sanctioned treatment must NOT stamp (the sanctioned
        # guard is preserved for un-bound devices — no over-firing).
        layout = self._stamp(
            {"kind": "dotted-leader-rule", "target": "headrail"},
            {"name": "headrail", "role": "section-headrail"})
        self.assertIsNone(layout.get("_headRail"))

    def test_explicitly_sanctioned_synonym_stamps(self):
        layout = self._stamp(
            {"kind": "dotted-leader-rule", "target": "eyebrow", "sanctioned": True},
            {"name": "eyebrow", "role": "eyebrow"})
        self.assertIsInstance(layout.get("_headRail"), dict)

    def test_headrail_composite_renders_pill_dotted_outlined(self):
        # integration: the enriched prose drives the shared helper to the full
        # composite — an outlined pill kicker, a dotted leader rule, and a trailing
        # button in the measured OUTLINE register (family resolved from the brand's
        # own declared outline family, never a hex).
        rail = {"note": "section-headrail dotted-leader-rule section-headrail "
                        "outlined-pill", "assets": [], "role": "section-headrail"}
        html = cs._headrail_html(BTN_DOC, _ctx(BTN_DOC), rail,
                                 eyebrow_html='<p class="c-eyebrow">Case Studies</p>',
                                 cta_label="See all case studies",
                                 legacy_pill_wrap=True)
        self.assertIn("cs-headrail-pill", html)
        self.assertIn("cs-headrail-rule--dotted", html)
        self.assertIn("c-button--secondary", html)   # trailing = outline register
        self.assertIn("See all case studies", html)


# ── D3: tab-rail alignment is a captured fact, not the section anchor ─────────────


class TabAlignmentNormalizeTest(unittest.TestCase):
    def test_synonyms_normalize(self):
        for v in ("start", "left", "flex-start"):
            self.assertEqual(cs._normalize_tab_alignment(v), "start")
        for v in ("center", "centre"):
            self.assertEqual(cs._normalize_tab_alignment(v), "center")
        for v in ("end", "right", "flex-end"):
            self.assertEqual(cs._normalize_tab_alignment(v), "end")

    def test_absent_or_unknown_is_none(self):
        self.assertIsNone(cs._normalize_tab_alignment(None))
        self.assertIsNone(cs._normalize_tab_alignment(""))
        self.assertIsNone(cs._normalize_tab_alignment("justify"))


class TabRailPlacementTest(unittest.TestCase):
    SEL = "#sec-7"

    def test_no_fact_keeps_centered_default_regardless_of_anchor(self):
        # the D3/D6 regression: a `mixed` (or side) anchor used to force the rail to
        # flex-start. With no captured tabAlignment fact, NOTHING is emitted so the
        # centered scaffold default stands — for ANY section text anchor.
        for anchor in ("mixed", "left", "right", "centered"):
            css = cs.layout_placement_css(
                self.SEL, {"_tabs": {"target": "tab-row"}},
                {"anchor": anchor, "source": "section"})
            self.assertNotIn(".cs-tablist", css, f"anchor={anchor}")

    def test_captured_start_alignment_emits_flex_start(self):
        css = cs.layout_placement_css(
            self.SEL, {"_tabs": {"target": "tab-row", "tabAlignment": "start"}},
            {"anchor": "centered", "source": "section"})
        self.assertIn(f"{self.SEL} .cs-tablist {{ justify-content: flex-start; }}",
                      css)

    def test_captured_end_alignment_emits_flex_end(self):
        css = cs.layout_placement_css(
            self.SEL, {"_tabs": {"tabAlignment": "end"}}, None)
        self.assertIn("justify-content: flex-end", css)

    def test_captured_center_emits_nothing(self):
        # center IS the scaffold default — an explicit center fact is a no-op override.
        css = cs.layout_placement_css(
            self.SEL, {"_tabs": {"tabAlignment": "center"}}, None)
        self.assertNotIn(".cs-tablist", css)

    def test_non_tab_section_never_emits_tablist_rule(self):
        css = cs.layout_placement_css(self.SEL, {"id": "sec"},
                                      {"anchor": "left", "source": "section"})
        self.assertNotIn(".cs-tablist", css)


class TabAlignmentCaptureTest(unittest.TestCase):
    def test_tabs_treatment_captures_alignment_fact(self):
        pat = _pattern(special_treatments=[
            {"kind": "tabs", "target": "tab-row", "sanctioned": True,
             "tabAlignment": "center"}])
        layout = {"id": "sec"}
        with mock.patch.object(cs, "resolve_pattern", return_value=(pat, "ref")):
            cs.stamp_pattern_devices(FIXTURE_DOC, layout,
                                     Path("/nonexistent/brand.yaml"))
        self.assertEqual((layout.get("_tabs") or {}).get("tabAlignment"), "center")

    def test_tabs_without_alignment_fact_leaves_it_absent(self):
        pat = _pattern(special_treatments=[
            {"kind": "tabs", "target": "tab-row", "sanctioned": True}])
        layout = {"id": "sec"}
        with mock.patch.object(cs, "resolve_pattern", return_value=(pat, "ref")):
            cs.stamp_pattern_devices(FIXTURE_DOC, layout,
                                     Path("/nonexistent/brand.yaml"))
        self.assertNotIn("tabAlignment", layout.get("_tabs") or {})


# ── D1: action register hierarchy + sibling-slot coalescing (AS-59) ──────────────


class ActionRegisterTest(unittest.TestCase):
    def test_split_pair_filled_then_outlined_hint(self):
        seq = [({"label": "Get a demo", "styleHint": "filled"}, "actions"),
               ({"label": "Get started free", "styleHint": "outlined"},
                "secondary action")]
        self.assertEqual(cs._action_register_outlined(seq), [False, True])

    def test_secondary_role_word_demotes(self):
        seq = [({"label": "A"}, "primary action-group"),
               ({"label": "B"}, "secondary-action")]
        self.assertEqual(cs._action_register_outlined(seq), [False, True])

    def test_unhinted_pair_falls_back_to_first_primary(self):
        # list-authored pair with no distinguishing hint: the historical _i>0 law.
        seq = [({"label": "A"}, "actions"), ({"label": "B"}, "actions")]
        self.assertEqual(cs._action_register_outlined(seq), [False, True])

    def test_outlined_first_still_gives_the_filled_one_primary(self):
        seq = [({"label": "A", "styleHint": "outlined"}, "actions"),
               ({"label": "B", "styleHint": "filled"}, "actions")]
        self.assertEqual(cs._action_register_outlined(seq), [True, False])

    def test_all_secondary_group_promotes_nothing(self):
        # nothing invents a primary the source never painted.
        seq = [({"label": "A", "styleHint": "ghost"}, "actions"),
               ({"label": "B", "styleHint": "text"}, "actions")]
        self.assertEqual(cs._action_register_outlined(seq), [True, True])


class OverlayActionCoalesceTest(unittest.TestCase):
    def test_sibling_slots_coalesce_into_one_container(self):
        action_slots = [
            {"name": "actions", "role": "actions — action-group", "contract": "button",
             "copy": {"label": "Get a demo", "styleHint": "filled"}},
            {"name": "actions-secondary", "role": "secondary action",
             "contract": "button",
             "copy": {"label": "Get started free", "styleHint": "outlined"}},
        ]
        html = cs._ov_actions_html(BTN_DOC, _ctx(BTN_DOC), action_slots)
        # ONE container
        self.assertEqual(html.count("cs-ov-actions"), 1)
        # exactly one filled primary + one outlined secondary
        self.assertEqual(html.count("c-button--secondary"), 1)
        self.assertEqual(html.count('class="c-button"'), 1)   # the lone primary
        self.assertIn("Get a demo", html)
        self.assertIn("Get started free", html)

    def test_empty_slots_render_nothing(self):
        self.assertEqual(cs._ov_actions_html(BTN_DOC, _ctx(BTN_DOC), []), "")


class SlopAs59SplitGuardTest(unittest.TestCase):
    def test_split_group_advisory_present_and_advisory_only(self):
        src = (_BRAND_PIPELINE / "slop_audit.mjs").read_text()
        self.assertIn("auditSplitActionGroups", src)
        self.assertIn("adjacent single-action groups", src)
        # it pushes an ADVISORY (never the hard `out` exit flag)
        i = src.index("auditSplitActionGroups = (")
        body = src[i:i + 1200]
        self.assertIn("advisories.push", body)
        self.assertNotIn("out.push", body)


if __name__ == "__main__":
    unittest.main()
