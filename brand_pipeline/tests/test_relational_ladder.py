#!/usr/bin/env python3
"""Fixture tests for the fid11 pass (2026-07) — AS-48 + AS-49:

  1. RELATIONAL SPACING LADDER — a brand that authored the pair trio
     (eyebrow-to-heading / heading-to-body / body-to-cta) renders header/anatomy
     stacks as NO-GAP columns with per-pair margins from ONE gated source
     (`relational_ladder_css`); `compose_flow` stamps each item's semantic row so
     flow seams key on content relationships; the block rhythm (`--c-block-gap`)
     and registration gutter (`--grid-gutter`) resolve from the brand's own
     block-to-block / column-to-column rungs. Ladder-less brands keep the uniform
     gap mechanic byte-identically (the degrade).
  2. HEADER-CONTEXT GRAMMAR — `layoutGrammar.headerContext` resolves as the
     brand-default alignment layer BENEATH explicit facts (section/pattern stay
     supreme) and ABOVE the style role default; chrome archetypes and
     grammar-less brands never consult it.

Run:  ./venv/bin/python -m unittest brand_pipeline.tests.test_relational_ladder
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

_BRAND_PIPELINE = Path(__file__).resolve().parent.parent
if str(_BRAND_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_BRAND_PIPELINE))

import compose_section as cs   # noqa: E402
import component_render as cr  # noqa: E402


def _ladder_doc(extra_spacing=None):
    spacing = {
        "eyebrow-to-heading": {"value": "0.75rem"},
        "heading-to-body": {"value": "1rem"},
        "body-to-cta": {"value": "2rem"},
    }
    spacing.update(extra_spacing or {})
    return {"brand": {"name": "Fixture"}, "tokens": {"spacing": spacing}}


def _grammar_doc():
    return {
        "brand": {"name": "Fixture"},
        "layoutGrammar": {"headerContext": {
            "splitColumn": {"anchor": "left", "counterweight": "media"},
            "standaloneStack": {"anchor": "centered"},
        }},
    }


# ── AS-48: the ladder stack mechanic ─────────────────────────────────────────────

class RelationalLadderCssTest(unittest.TestCase):
    """The gated no-gap mechanic ships if-and-only-if the brand authored the pair
    trio — uniform stack gap survives ONLY as the no-ladder degrade."""

    def test_ladder_doc_ships_no_gap_pair_mechanic(self):
        css = cs.relational_ladder_css(_ladder_doc())
        # every header/anatomy stack family becomes a no-gap column
        for sel in (".cs-faq", ".cs-foot", ".cs-hero-panel-content", ".cs-conversion",
                    ".cs-statement-text", ".cs-quote-text", ".cs-flow"):
            self.assertIn(sel, css)
        self.assertIn("gap: 0", css)
        # pair seams ride the authored rungs — bare token refs, no invented values
        self.assertIn("var(--space-heading-to-body)", css)
        self.assertIn("var(--space-body-to-cta)", css)
        self.assertIn("var(--space-eyebrow-to-heading)", css)
        # block rhythm degrades through the uniform gap when un-authored
        self.assertIn("var(--space-block-to-block, var(--c-block-gap))", css)

    def test_no_ladder_degrades_to_nothing(self):
        self.assertEqual("", cs.relational_ladder_css({}))
        self.assertEqual("", cs.relational_ladder_css({"tokens": {"spacing": {}}}))

    def test_partial_trio_degrades_to_nothing(self):
        doc = _ladder_doc()
        del doc["tokens"]["spacing"]["body-to-cta"]
        self.assertEqual("", cs.relational_ladder_css(doc))

    def test_no_literal_lengths_inside_the_gated_block(self):
        # the mechanic carries structure only: seams are token refs (structural
        # degrades live inside var() fallbacks); gap: 0 is not a rhythm value and
        # the mobile @media prelude is a structural breakpoint, not a seam.
        css = re.sub(r"/\*.*?\*/", "", cs.relational_ladder_css(_ladder_doc()),
                     flags=re.S)
        css = re.sub(r"@media[^{]*", "", css)
        lengths = [v for v in re.findall(r"(?<!\()\b\d+(?:\.\d+)?(?:px|rem|em|ch)\b",
                                         re.sub(r"var\([^)]*\)", "var()", css))]
        self.assertEqual([], lengths, css)

    def test_flow_items_carry_semantic_row_stamps(self):
        doc = _ladder_doc()
        ctx = cr.ComponentContext(surface_role="surface/primary", is_dark=False)
        rendered = [
            {"contract": "eyebrow", "html": "<p class='c-eyebrow'>K</p>", "role": "eyebrow"},
            {"contract": "heading", "html": "<h2 class='c-heading'>H</h2>", "role": "heading"},
            {"contract": "paragraph", "html": "<p class='c-paragraph'>B</p>", "role": "body"},
            {"contract": "button", "html": "<a class='c-button'>Go</a>", "role": "cta"},
        ]
        html = cs.compose_generic_flow(doc, {"id": "fx", "archetype": "flow"}, ctx,
                                       rendered, None)
        self.assertIn('data-row="eyebrow"', html)
        self.assertIn('data-row="heading"', html)
        self.assertIn('data-row="body"', html)
        self.assertIn('data-row="action"', html)

    def test_scaffold_constants_keep_the_uniform_gap_degrade(self):
        # the DEGRADE lives in the un-gated scaffolds: the flow/FAQ columns still
        # declare the uniform gap for ladder-less brands (the gated block overrides
        # it by order only when the trio is authored).
        self.assertIn("gap: var(--c-block-gap)", cs.SCAFFOLD_FLOW_CSS)
        self.assertIn("gap: var(--c-block-gap)", cs.SCAFFOLD_FAQ_CSS)

    def test_scaffold_css_appends_the_gated_block_for_ladder_brands(self):
        doc = _ladder_doc()
        doc["tokens"]["surfaces"] = {"surface/primary": {"bg": "#ffffff"}}
        layout = {"id": "fx", "archetype": "stack"}
        self.assertIn("RELATIONAL LADDER (AS-48)", cs.scaffold_css(doc, layout))
        bare = {"tokens": {"surfaces": {"surface/primary": {"bg": "#ffffff"}}}}
        self.assertNotIn("RELATIONAL LADDER", cs.scaffold_css(bare, layout))


class LadderRhythmTest(unittest.TestCase):
    """The uniform rhythm vars themselves resolve from the brand's rungs."""

    def test_block_gap_prefers_the_authored_row_rung(self):
        doc = _ladder_doc({"block-to-block": {"value": "4rem"}})
        self.assertEqual("4rem", cs.rhythm_for(doc, None, "surface/primary")["block_gap"])

    def test_block_gap_degrades_without_the_rung(self):
        self.assertEqual("2.5rem",
                         cs.rhythm_for(_ladder_doc(), None, "surface/primary")["block_gap"])

    def test_grid_gutter_rides_the_column_rung_chain(self):
        doc = {"brand": {"name": "Fixture"},
               "tokens": {"colors": {}, "spacing": {}, "surfaces": {}}}
        css = cs.root_vars(doc, {"bg": "#ffffff", "textPrimary": None},
                           display_size="4rem", title_overlap=None)
        self.assertIn("--grid-gutter: var(--space-column-to-column, 6rem)", css)

    def test_prose_measures_ride_the_body_measure_chain(self):
        self.assertIn("var(--c-measure, var(--space-body-measure, 34ch))",
                      cr.COMPONENT_CSS)
        self.assertIn("var(--space-body-measure, 62ch)", cs.SCAFFOLD_FLOW_CSS)
        self.assertIn("var(--space-body-measure, 56ch)", cs.SCAFFOLD_FAQ_CSS)
        self.assertIn("var(--space-header-measure, 52rem)",
                      cs.relational_ladder_css(_ladder_doc()))


# ── AS-49: the header-context grammar layer ─────────────────────────────────────

class _StyleStub:
    """Duck-typed style_ctx whose structure declares one alignment default."""
    class _Structure:
        def declares_alignment(self):
            return True

        def align_for(self, *keys):
            return {"anchor": "left"}
    active = True
    structure = _Structure()


class HeaderGrammarTest(unittest.TestCase):
    def test_standalone_contexts_resolve_centered(self):
        for arch in ("stack", "cards", "grid", "stack-fullbleed"):
            r = cs.resolve_alignment({"archetype": arch}, None, None, doc=_grammar_doc())
            self.assertEqual(("centered", "brand"), (r["anchor"], r["source"]), arch)

    def test_split_context_resolves_left_with_counterweight(self):
        r = cs.resolve_alignment({"archetype": "split"}, None, None, doc=_grammar_doc())
        self.assertEqual({"anchor": "left", "source": "brand",
                          "counterweight": "media"}, r)

    def test_chrome_and_uncorroborated_archetypes_never_consult_it(self):
        for arch in ("footer", "nav", "overlay", "banded", "collage"):
            self.assertIsNone(
                cs.resolve_alignment({"archetype": arch}, None, None,
                                     doc=_grammar_doc()), arch)

    def test_section_fact_outranks_the_grammar(self):
        r = cs.resolve_alignment({"archetype": "cards",
                                  "alignment": {"anchor": "left"}},
                                 None, None, doc=_grammar_doc())
        self.assertEqual(("left", "section"), (r["anchor"], r["source"]))

    def test_pattern_fact_outranks_the_grammar(self):
        pattern = SimpleNamespace(
            alignment={"anchor": "left", "counterweight": "cards"}, use_case="features")
        r = cs.resolve_alignment({"archetype": "cards"}, pattern, None,
                                 doc=_grammar_doc())
        self.assertEqual(("left", "pattern"), (r["anchor"], r["source"]))

    def test_grammar_outranks_the_style_layer(self):
        r = cs.resolve_alignment({"archetype": "cards"}, None, _StyleStub(),
                                 doc=_grammar_doc())
        self.assertEqual(("centered", "brand"), (r["anchor"], r["source"]))

    def test_grammarless_brand_falls_through_to_style(self):
        r = cs.resolve_alignment({"archetype": "cards"}, None, _StyleStub(),
                                 doc={"brand": {"name": "Fixture"}})
        self.assertEqual(("left", "style"), (r["anchor"], r["source"]))

    def test_out_of_enum_grammar_anchor_falls_through(self):
        doc = {"layoutGrammar": {"headerContext": {
            "standaloneStack": {"anchor": "sideways"}}}}
        self.assertIsNone(cs.resolve_alignment({"archetype": "stack"}, None, None,
                                               doc=doc))

    def test_brand_source_is_stamped(self):
        attrs = cs.align_stamp_attrs(
            cs.resolve_alignment({"archetype": "cards"}, None, None,
                                 doc=_grammar_doc()))
        self.assertIn('data-align="centered"', attrs)
        self.assertIn('data-align-source="brand"', attrs)


if __name__ == "__main__":
    unittest.main()
