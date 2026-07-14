#!/usr/bin/env python3
"""Golden tests for the composition-grammar CORE split (2026-07-14).

styles/composition-rules.md is three layers: YAML front-matter (on-disk registry),
the NORMATIVE CORE (the only prompt payload), and an extended edition below the
``COMPOSITION-CORE:END`` sentinel (rationale + device detail, never injected).
These tests pin the contract:

  - the extraction cuts BOTH non-core layers and degrades safely without them;
  - the core stays under budget (the split's whole point — the old assembly
    injected the entire 27KB file, ~7k tokens/prompt);
  - the core still carries the COMPLETE working vocabulary (every drawable
    archetype, every treatment kind, placement fields, tiers, anchors) — a core
    that sheds a law to meet budget is a regression, not an optimization;
  - the on-disk registry (front-matter) stays consistent with the code vocabularies;
  - build_prompt end-to-end injects the core and nothing below the sentinel.
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

_BRAND_PIPELINE = Path(__file__).resolve().parent.parent
if str(_BRAND_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_BRAND_PIPELINE))

import generate_composition as gc   # noqa: E402
import layout_library as ll         # noqa: E402
import styles as styles_mod         # noqa: E402
from compose_section import ARCHETYPE_COMPOSERS  # noqa: E402

REPO = _BRAND_PIPELINE.parent
HUBSPOT = REPO / "runs" / "hubspot-v2" / "brand" / "brand.yaml"

RAW = gc.COMPOSITION_RULES_PATH.read_text()
CORE = gc.grammar_core(RAW)
META, BODY = styles_mod.parse_front_matter(RAW)

# Budget: core measured ~9.7k chars at the split; ceiling leaves edit headroom while
# staying far under the old 27KB whole-file payload.
CORE_MAX_CHARS = 13_000
CORE_MAX_LINES = 190


class CoreExtraction(unittest.TestCase):
    def test_front_matter_is_cut(self):
        self.assertNotIn("schemaVersion: composition.v1", CORE)
        self.assertNotIn("palette_sources:", CORE)
        self.assertNotIn("off_grid_treatments_gated:", CORE)

    def test_sentinel_and_extended_edition_are_cut(self):
        self.assertNotIn(gc.GRAMMAR_CORE_SENTINEL, CORE)
        self.assertNotIn("Extended edition", CORE)
        # a phrase that lives ONLY in the extended edition's assembly chapter
        self.assertNotIn("## Assembly (how this file is composed at gen time)", CORE)

    def test_core_is_the_normative_core(self):
        self.assertTrue(CORE.startswith("# Composition rules (normative core)"))

    def test_budget(self):
        self.assertLessEqual(len(CORE), CORE_MAX_CHARS,
                             "core grew past budget — move detail to the extended edition")
        self.assertLessEqual(CORE.count("\n"), CORE_MAX_LINES)

    def test_degrades_without_markers(self):
        plain = "# Some grammar\n\nProse only, no front-matter, no sentinel.\n"
        self.assertEqual(gc.grammar_core(plain), plain.strip() + "\n")

    def test_degrades_with_front_matter_but_no_sentinel(self):
        text = "---\nid: x\n---\nBody line.\n"
        self.assertEqual(gc.grammar_core(text), "Body line.\n")


class CoreVocabularyComplete(unittest.TestCase):
    """The core may compress prose but may NOT shed working vocabulary."""

    def test_every_drawable_archetype_named(self):
        for a in META["archetypes"]:
            self.assertIn(a, CORE, f"archetype `{a}` missing from core")

    def test_every_treatment_kind_named(self):
        for kind in sorted(ll.TREATMENT_KINDS):
            self.assertIn(kind, CORE, f"treatment `{kind}` missing from core")

    def test_type_tiers_and_alignment_anchors(self):
        self.assertIn("colossal|hero|display|title|body|caption", CORE)
        for anchor in ("centered", "left", "right", "space-between", "edge-to-edge", "mixed"):
            self.assertIn(anchor, CORE)

    def test_placement_and_registration_fields(self):
        for field in ("colStart", "colSpan", "offsetCols", "offsetBaselines",
                      "alignTo", "registration", "toSlot", "depthCols", "depthBaselines",
                      "counterweight"):
            self.assertIn(field, CORE, f"placement field `{field}` missing from core")

    def test_width_classes_and_aspects(self):
        self.assertIn("hug|stretch|fixed|media|full-bleed|framed", CORE)
        for aspect in ("wide", "pano", "portrait", "square"):
            self.assertIn(aspect, CORE)

    def test_legality_machinery_present(self):
        for token in ("neverDo", "sanctioned: true", "maxOcclusion", "endsVisible",
                      "novelty: novel", "seededFrom", "zOrder"):
            self.assertIn(token, CORE, f"legality token `{token}` missing from core")


class RegistryConsistentWithCode(unittest.TestCase):
    """Front-matter is now an on-disk registry — keep it honest against the code."""

    def test_archetypes_match_schema_enum(self):
        schema = json.loads(gc.SCHEMA_PATH.read_text())
        enum = schema["$defs"]["archetype"]["enum"]
        self.assertEqual(list(META["archetypes"]), list(enum))

    def test_archetypes_are_drawable(self):
        for a in META["archetypes"]:
            self.assertIn(a, ARCHETYPE_COMPOSERS, f"registry archetype `{a}` not drawable")

    def test_legal_treatments_subset_of_kinds(self):
        self.assertTrue(set(META["treatments"]["legal"]) <= set(ll.TREATMENT_KINDS))

    def test_off_grid_gated_set_matches_code(self):
        gated = set(META["freedom_envelope"]["off_grid_treatments_gated"])
        self.assertEqual(gated, set(gc.OFF_GRID_TREATMENTS))


class PromptUsesCore(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        doc = gc.load_brand(HUBSPOT)
        seeds = gc.seed_patterns(doc, HUBSPOT)
        cls.prompt = gc.build_prompt("Brief.", HUBSPOT, "corporate-saas-clean", seeds)

    def test_core_injected(self):
        self.assertIn("# Composition rules (normative core)", self.prompt)

    def test_registry_and_extended_edition_not_injected(self):
        self.assertNotIn(gc.GRAMMAR_CORE_SENTINEL, self.prompt)
        self.assertNotIn("Extended edition", self.prompt)
        self.assertNotIn("palette_sources:", self.prompt)


if __name__ == "__main__":
    unittest.main()
