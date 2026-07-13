"""fid14 (2026-07-09) — GRID EQUALIZATION facts + consumption (brand-schema §4.4d,
AS-50), locked by regression:

1. FACT: `contentShape.gridEqualize { heights: stretch|hug, slack, actionPinned }`
   parses through `Pattern.grid_equalize` (out-of-enum / absent -> None).
2. CONSUMPTION: `pattern_equalize_css` renders the fact — stretch rows + pinned
   trailing action rows (with the ladder's body->cta rung preserved as the pinned
   link's minimum seam), or an explicit hug; "" for fact-less patterns so fact-less
   brands stay byte-identical.
3. GRAMMAR: the pattern-less card scaffolds (bento mosaic / pricing tiers) follow
   the BRAND grammar derived from the observed facts (`grid_equalize_grammar`):
   all-hug releases their built-in equalization, no facts changes nothing.
4. AUTHORING: both of Remote's observed card-grid patterns carry the measured fact.
"""
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import compose_section as cs           # noqa: E402
import layout_library as ll            # noqa: E402

BRAND_DIR = Path(__file__).resolve().parents[2] / "runs" / "remote" / "brand"


def _pattern(grid_equalize=None, archetype="grid"):
    shape = {"slots": []}
    if grid_equalize is not None:
        shape["gridEqualize"] = grid_equalize
    return ll.Pattern(
        id="fx-grid", use_case="features", archetype_ref=archetype,
        surface_intent="primary", intent="fixture", content_shape=shape,
        special_treatments=[], responsive={}, variant_knobs={},
        origin="extracted", confidence="high", scope="design-language",
        provenance=[], raw={"id": "fx-grid"})


_STRETCH = {"heights": "stretch", "slack": "body", "actionPinned": True}


class GridEqualizeFactTest(unittest.TestCase):
    """§4.4d: the fact parses; junk degrades to None (never a guessed stance)."""

    def test_full_trio_parses(self):
        self.assertEqual({"heights": "stretch", "slack": "body", "actionPinned": True},
                         _pattern(_STRETCH).grid_equalize)

    def test_absent_and_out_of_enum_are_none(self):
        self.assertIsNone(_pattern().grid_equalize)
        self.assertIsNone(_pattern({"heights": "equalish"}).grid_equalize)
        self.assertIsNone(_pattern({"slack": "body"}).grid_equalize)

    def test_companion_defaults(self):
        fact = _pattern({"heights": "hug"}).grid_equalize
        self.assertEqual(("hug", "body", False),
                         (fact["heights"], fact["slack"], fact["actionPinned"]))


class PatternEqualizeCssTest(unittest.TestCase):
    """AS-50 consumption: stretch + pins, explicit hug, byte-identical degrade."""

    def test_stretch_fact_equalizes_and_pins(self):
        css = cs.pattern_equalize_css(_pattern(_STRETCH), "#sec-5")
        self.assertIn("#sec-5 .cs-modules { align-items: stretch; }", css)
        self.assertIn("#sec-5 .cs-module > .c-arrow-link:last-child", css)
        self.assertIn("margin-top: auto", css)

    def test_pinned_link_keeps_the_ladder_seam(self):
        # margin-top:auto replaces the pair margin; the tallest card of the row
        # (zero slack) must keep the body->cta rung as a minimum seam. Spacing
        # remediation B2 (2026-07): the seam lives on the PRECEDING content's
        # margin-bottom (real box-to-box distance `auto` cannot collapse) — the
        # old padding-block-start on the link moved the glyph but measured 0.
        css = cs.pattern_equalize_css(_pattern(_STRETCH))
        self.assertIn(".cs-module--anatomy > :has(+ .c-arrow-link:last-child), "
                      ".cs-module--anatomy > :has(+ .c-button:last-child) {"
                      " margin-bottom: var(--space-body-to-cta, 0.9rem); }", css)
        self.assertNotIn("padding-block-start", css)

    def test_unpinned_source_emits_no_pin(self):
        css = cs.pattern_equalize_css(
            _pattern({"heights": "stretch", "slack": "body", "actionPinned": False}))
        self.assertIn("align-items: stretch", css)
        self.assertNotIn("margin-top: auto", css)

    def test_hug_fact_is_equally_binding(self):
        css = cs.pattern_equalize_css(_pattern({"heights": "hug"}), "#sec-2")
        self.assertIn("#sec-2 .cs-modules { align-items: start; }", css)
        self.assertNotIn("margin-top: auto", css)

    def test_factless_degrade_is_empty(self):
        self.assertEqual("", cs.pattern_equalize_css(None))
        self.assertEqual("", cs.pattern_equalize_css(_pattern()))


def _tmp_brand(patterns) -> Path:
    d = Path(tempfile.mkdtemp())
    (d / "brand.yaml").write_text("brand:\n  name: Fixture\n")
    (d / "layout-library.yaml").write_text(yaml.safe_dump({"patterns": patterns}))
    return d / "brand.yaml"


class GrammarDerivationTest(unittest.TestCase):
    """grid_equalize_grammar: the brand layer the pattern-less scaffolds consume."""

    def test_observed_stretch_facts_derive_stretch(self):
        by = _tmp_brand([{"id": "a", "useCase": "features", "archetypeRef": "grid",
                          "contentShape": {"gridEqualize": _STRETCH}}])
        self.assertEqual("stretch", cs.grid_equalize_grammar(by))

    def test_all_hug_derives_hug(self):
        by = _tmp_brand([{"id": "a", "useCase": "features", "archetypeRef": "grid",
                          "contentShape": {"gridEqualize": {"heights": "hug"}}}])
        self.assertEqual("hug", cs.grid_equalize_grammar(by))

    def test_factless_brand_derives_nothing(self):
        by = _tmp_brand([{"id": "a", "useCase": "features", "archetypeRef": "grid",
                          "contentShape": {}}])
        self.assertIsNone(cs.grid_equalize_grammar(by))
        self.assertIsNone(cs.grid_equalize_grammar(None))


class ScaffoldGrammarTest(unittest.TestCase):
    """Bento cells + pricing tiers follow the SAME grammar (AS-50 uniform behavior)."""

    def test_builtin_scaffolds_ship_the_equalized_morphology(self):
        # stretch is the scaffolds' built-in construction: bento pins its trailing
        # rows, tiers declare row stretch + pinned buttons.
        self.assertIn(".cs-bento-cell .c-arrow-link { margin-top: auto; }",
                      cs.SCAFFOLD_BENTO_CSS)
        self.assertIn("align-items: stretch", cs.SCAFFOLD_TIERS_CSS)
        self.assertIn(".cs-tier > .c-button, .cs-tier > .c-arrow-link { margin-top: auto;",
                      cs.SCAFFOLD_TIERS_CSS)

    def test_hug_grammar_releases_both_scaffolds(self):
        css = cs.device_scaffold_css([{"_bento": {}}, {"_tiers": {}}],
                                     equalize_grammar="hug")
        self.assertIn(".cs-bento { align-items: start; }", css)
        self.assertIn(".cs-tiers { align-items: start; }", css)
        self.assertIn(".cs-bento-cell .c-arrow-link, .cs-bento-cell .c-person {"
                      " margin-top: 0; }", css)
        self.assertIn(".cs-tier > .c-button, .cs-tier > .c-arrow-link {"
                      " margin-top: 0; }", css)

    def test_factless_and_stretch_grammars_change_nothing(self):
        stamped = [{"_bento": {}}, {"_tiers": {}}]
        base = cs.device_scaffold_css(stamped)
        self.assertEqual(base, cs.device_scaffold_css(stamped, equalize_grammar=None))
        self.assertEqual(base, cs.device_scaffold_css(stamped,
                                                      equalize_grammar="stretch"))


class AuthoredFactsTest(unittest.TestCase):
    """Remote's two observed card grids carry the measured fact (fid14 authoring)."""

    def test_both_grid_patterns_record_stretch_with_pinned_actions(self):
        pats = {p.id: p for p in ll.load_project_patterns(BRAND_DIR / "brand.yaml")}
        for pid in ("features-card-grid-navy-media", "testimonial-card-row"):
            fact = pats[pid].grid_equalize
            self.assertIsNotNone(fact, pid)
            self.assertEqual("stretch", fact["heights"], pid)
            self.assertTrue(fact["actionPinned"], pid)


if __name__ == "__main__":
    unittest.main()
