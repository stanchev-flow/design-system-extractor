#!/usr/bin/env python3
"""Unit test for the Phase 1C seeding hook (brand_pipeline/generate_composition.py).

Verifies that ``seed_patterns`` runs the layout-library retrieval against the real
WoodWave brand.yaml and that the REVIVED ``layout_library.render_pattern_constraint``
produces a non-empty reuse-constraint seed block naming REAL pattern ids for at least the
hero + features use-cases.

Run:  ./venv/bin/python -m unittest brand_pipeline.tests.test_generate_composition_seeds
  or: ./venv/bin/python -m pytest brand_pipeline/tests/test_generate_composition_seeds.py
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

# Make brand_pipeline/*.py importable whether run via unittest discovery or pytest.
_BRAND_PIPELINE = Path(__file__).resolve().parent.parent
if str(_BRAND_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_BRAND_PIPELINE))

import generate_composition as gc          # noqa: E402
import layout_library as ll                # noqa: E402

REPO_ROOT = _BRAND_PIPELINE.parent
BRAND_YAML = REPO_ROOT / "runs" / "woodwave" / "brand" / "brand.yaml"


class SeedPatternsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = gc.load_brand(BRAND_YAML)
        cls.seeds = gc.seed_patterns(cls.doc, BRAND_YAML)

    def test_brand_yaml_exists(self):
        self.assertTrue(BRAND_YAML.exists(), f"missing brand.yaml at {BRAND_YAML}")

    def test_hero_and_features_use_cases_present(self):
        """The candidate use-cases derived from the brand's layouts include hero + features."""
        self.assertIn("hero", self.seeds.use_cases)
        self.assertIn("features", self.seeds.use_cases)

    def test_hero_and_features_resolved_to_real_patterns(self):
        """Retrieval resolved a reuse/adapt pattern for BOTH hero and features."""
        self.assertIn("hero", self.seeds.matches, "no hero pattern matched")
        self.assertIn("features", self.seeds.matches, "no features pattern matched")

        hero = self.seeds.matches["hero"]
        feat = self.seeds.matches["features"]

        for uc, res in (("hero", hero), ("features", feat)):
            self.assertIsNotNone(res.pattern, f"{uc} match returned no pattern")
            self.assertIn(res.match_kind, ("reuse", "adapt"),
                          f"{uc} should reuse/adapt, got {res.match_kind}")
            self.assertTrue(res.pattern.id, f"{uc} pattern has empty id")
            self.assertEqual(res.pattern.use_case, uc)

    def test_seed_block_non_empty_and_names_real_pattern_ids(self):
        """render_pattern_constraint produced a non-empty block naming the resolved ids."""
        block = self.seeds.block
        self.assertTrue(block.strip(), "seed block is empty")
        self.assertIn("Layout patterns to REUSE", block)

        hero_id = self.seeds.matches["hero"].pattern.id
        feat_id = self.seeds.matches["features"].pattern.id
        self.assertIn(hero_id, block, f"hero pattern id {hero_id!r} not named in seed block")
        self.assertIn(feat_id, block, f"features pattern id {feat_id!r} not named in seed block")

        # The ids must be REAL patterns resolvable in the standard OR project library.
        real_ids = {p.id for p in _all_patterns()}
        for pid in (hero_id, feat_id):
            self.assertIn(pid, real_ids, f"pattern id {pid!r} is not a real library pattern")

    def test_render_pattern_constraint_directly_on_matched_patterns(self):
        """Exercise the revived function directly on the matched Pattern objects."""
        patterns = [self.seeds.matches["hero"].pattern, self.seeds.matches["features"].pattern]
        block = ll.render_pattern_constraint(patterns)
        self.assertTrue(block.strip())
        for p in patterns:
            self.assertIn(p.id, block)
        # empty input -> empty output (documented contract)
        self.assertEqual(ll.render_pattern_constraint([]), "")


def _all_patterns():
    """Every pattern across the standard library + the WoodWave project library."""
    pats = list(ll.load_project_patterns(BRAND_YAML))
    for uc in ll.USE_CASES:
        pats += ll.load_standard_patterns(uc)
    return pats


if __name__ == "__main__":
    unittest.main(verbosity=2)
