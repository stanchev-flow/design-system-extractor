"""fid13 (2026-07-09) — two user-driven mechanisms, locked by regression:

1. CURATION LAYER (brand-schema §4.4c): a curator's recorded resolution of a
   pattern-fact-vs-grammar dissent. Generation lanes resolve alignment THROUGH the
   ruling (`follow-grammar` retires the pattern's dissenting fact; the grammar wins
   and stamps source="curation"); the replica lane passes honor_curation=False and
   keeps the measured fact. Section-explicit stays supreme either way (AS-49 chain:
   section explicit > curation > pattern fact > grammar > style).

2. RADIUS FACTS (C19 + consumption): authored radii must ride the source's own
   ladder, `0` is a REAL square-family fact that must still emit its CSS var, and
   the geometry of a card media well belongs to the WELL/PLATE — never the bitmap.
"""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import compose_section as cs           # noqa: E402
import layout_library as ll            # noqa: E402
import tokens_css                      # noqa: E402


def _grammar_doc():
    return {
        "brand": {"name": "Fixture"},
        "layoutGrammar": {"headerContext": {
            "splitColumn": {"anchor": "left", "counterweight": "media"},
            "standaloneStack": {"anchor": "centered"},
        }},
    }


def _pattern(curation=None, anchor="left"):
    """A real ll.Pattern whose measured fact dissents (left) from the standalone
    grammar (centered) — optionally carrying a curation ruling."""
    raw = {"id": "fx-grid", "curation": curation} if curation else {"id": "fx-grid"}
    return ll.Pattern(
        id="fx-grid", use_case="features", archetype_ref="grid",
        surface_intent="primary", intent="fixture",
        content_shape={"alignment": {"value": anchor, "counterweight": "cards"}},
        special_treatments=[], responsive={}, variant_knobs={},
        origin="extracted", confidence="high", scope="design-language",
        provenance=[], raw=raw)


_FOLLOW = {"alignment": {"resolve": "follow-grammar", "by": "user",
                         "ts": "2026-07-09T19:25:00Z", "reason": "fixture ruling"}}


class CurationResolutionTest(unittest.TestCase):
    """§4.4c lane semantics on THE single resolution chain (resolve_alignment)."""

    def test_generation_lane_resolves_through_the_curation(self):
        r = cs.resolve_alignment({"archetype": "grid"}, _pattern(_FOLLOW),
                                 None, doc=_grammar_doc())
        self.assertEqual(("centered", "curation"), (r["anchor"], r["source"]))

    def test_replica_lane_keeps_the_measured_fact(self):
        r = cs.resolve_alignment({"archetype": "grid"}, _pattern(_FOLLOW),
                                 None, doc=_grammar_doc(), honor_curation=False)
        self.assertEqual(("left", "pattern"), (r["anchor"], r["source"]))

    def test_section_explicit_still_beats_the_curation(self):
        r = cs.resolve_alignment(
            {"archetype": "grid", "alignment": {"anchor": "right",
                                                "counterweight": "media"}},
            _pattern(_FOLLOW), None, doc=_grammar_doc())
        self.assertEqual(("right", "section"), (r["anchor"], r["source"]))

    def test_uncurated_pattern_fact_still_outranks_the_grammar(self):
        r = cs.resolve_alignment({"archetype": "grid"}, _pattern(),
                                 None, doc=_grammar_doc())
        self.assertEqual(("left", "pattern"), (r["anchor"], r["source"]))

    def test_curation_without_grammar_skips_the_retired_fact(self):
        # the curator rejected the fact; with no grammar rung the chain must NOT
        # silently revert to the rejected look — it falls to the style layer.
        class _Style:
            class _S:
                def declares_alignment(self):
                    return True

                def align_for(self, *k):
                    return {"anchor": "centered"}
            active, structure = True, _S()
        r = cs.resolve_alignment({"archetype": "grid"}, _pattern(_FOLLOW),
                                 _Style(), doc={"brand": {"name": "Fixture"}})
        self.assertEqual(("centered", "style"), (r["anchor"], r["source"]))

    def test_unknown_resolution_value_is_inert(self):
        cur = {"alignment": {"resolve": "keep-fact"}}
        r = cs.resolve_alignment({"archetype": "grid"}, _pattern(cur),
                                 None, doc=_grammar_doc())
        self.assertEqual(("left", "pattern"), (r["anchor"], r["source"]))

    def test_duck_typed_pattern_stubs_stay_supported(self):
        stub = SimpleNamespace(alignment={"anchor": "left",
                                          "counterweight": "cards"})
        r = cs.resolve_alignment({"archetype": "grid"}, stub, None,
                                 doc=_grammar_doc())
        self.assertEqual(("left", "pattern"), (r["anchor"], r["source"]))

    def test_pattern_curation_accessor(self):
        self.assertEqual("follow-grammar",
                         _pattern(_FOLLOW).curation_for("alignment")["resolve"])
        self.assertIsNone(_pattern().curation_for("alignment"))
        self.assertIsNone(_pattern(_FOLLOW).curation_for("radius"))


class RadiusFactConsumptionTest(unittest.TestCase):
    """fid13 radius corrections: `0` is a real emitted fact; well bitmaps never
    carry their own rounding; plates/wells ride the brand tokens (no literals)."""

    def test_zero_radius_role_still_emits_its_var(self):
        doc = {"brand": {"name": "Fixture"},
               "tokens": {"spacing": {"radius-global": {"value": "0.625rem"}},
                          "radius": {"card": {"value": "0.625rem"},
                                     "media": {"value": "0"}}}}
        lines, _bp, index, _missing, _disabled = tokens_css.emit_layer1(doc)
        self.assertEqual("0", index.get("--radius-media"))
        self.assertIn("  --radius-media: 0;", lines)

    def test_module_media_bitmap_never_rounds_itself(self):
        # the source's card images are square — the plate's own radius clips the
        # visible corners; the img must not ride the global --radius.
        src = cs.SCAFFOLD_MODULES_CSS if hasattr(cs, "SCAFFOLD_MODULES_CSS") else ""
        if ".cs-module-media .c-image" not in src:
            import inspect
            src = inspect.getsource(cs)
        rule = next(l for l in src.splitlines()
                    if ".cs-module-media .c-image" in l and "{" in l)
        self.assertIn("border-radius: 0", rule)

    def test_plate_and_well_ride_the_card_token(self):
        self.assertIn("border-radius: var(--radius-card, 0); padding:",
                      cs.SCAFFOLD_CARD_PLATE_CSS)
        self.assertIn("border-radius: var(--radius-card, 0) var(--radius-card, 0) 0 0",
                      cs.SCAFFOLD_CARD_PLATE_CSS)


if __name__ == "__main__":
    unittest.main()
