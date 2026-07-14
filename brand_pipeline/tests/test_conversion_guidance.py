#!/usr/bin/env python3
"""Brief-time conversion-structure guidance (steal 3, prompt side) — the
``conversion_structure.render_guidance_block`` projection and its opt-in ride
through ``generate_composition.build_prompt(conversion_guidance=...)``.

Pins the injection contract the stage-B scope note demands:
  - DOUBLY fact-gated: no campaignType frontmatter -> None; unknown campaign ->
    None; and build_prompt WITHOUT the parameter is byte-identical to
    conversion_guidance=None (the hero_candidates pattern) — so the default
    pipeline (and the pass-3 injection architecture) is untouched.
  - The block rides in the USER prompt: after the brief body, before the
    OUTPUT CONTRACT, exactly once.
  - Every eval-matrix brief resolves its declared campaign and projects a
    complete guidance block (all constraint rows surface as bullets).

The conversion CHECKER (constraint interpreter over compositions/lanes) is
conversion_audit.py law, tested in test_conversion_structure.py — this file
deliberately tests none of it.

Run: ./venv/bin/python -m pytest brand_pipeline/tests/test_conversion_guidance.py -q
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

_BRAND_PIPELINE = Path(__file__).resolve().parent.parent
if str(_BRAND_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_BRAND_PIPELINE))

import conversion_structure as conv  # noqa: E402
import generate_composition as gc    # noqa: E402

REPO = _BRAND_PIPELINE.parent
MATRIX_BRIEFS = REPO / "evals" / "matrix" / "briefs"
HUBSPOT = REPO / "runs" / "hubspot-v2" / "brand" / "brand.yaml"


class GuidanceProjection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = conv.load_contracts()

    def test_no_frontmatter_projects_nothing(self):
        self.assertIsNone(conv.render_guidance_block("Build a launch page."))

    def test_unknown_campaign_projects_nothing(self):
        brief = "---\ncampaignType: interpretive-dance\n---\n# Brief\n"
        self.assertIsNone(conv.render_guidance_block(brief))

    def test_every_campaign_projects_all_constraint_rows(self):
        for c in self.doc["campaigns"]:
            brief = f"---\ncampaignType: {c['id']}\n---\n# Brief\n"
            block = conv.render_guidance_block(brief, self.doc)
            self.assertIsNotNone(block, c["id"])
            self.assertIn(f"(campaign: {c['id']})", block)
            self.assertIn(str(c["funnelStage"]), block)
            band = c["depthBand"]
            self.assertIn(f"{band['min']}-{band['max']} content sections", block)
            # one bullet per constraint row (every kind renders — none skipped)
            bullets = [l for l in block.splitlines() if l.startswith("- ")]
            fixed = 3 if c.get("formDepth") else 2   # stage/moment(/formDepth)
            self.assertEqual(len(bullets), fixed + len(c["constraints"]), c["id"])

    def test_matrix_briefs_all_resolve_and_project(self):
        briefs = sorted(MATRIX_BRIEFS.glob("*/*.md"))
        self.assertEqual(len(briefs), 12, "the 6x2 standing corpus")
        for b in briefs:
            text = b.read_text()
            cid = conv.resolve_campaign_id(text, self.doc)
            self.assertEqual(cid, b.stem, b)   # brief file named by campaign id
            block = conv.render_guidance_block(text, self.doc)
            self.assertIn(f"(campaign: {b.stem})", block)

    def test_advisory_framing_is_explicit(self):
        brief = "---\ncampaignType: pricing\n---\n# Brief\n"
        block = conv.render_guidance_block(brief, self.doc)
        self.assertIn("ADVISORY prior", block)
        self.assertIn("brand evidence outranks both", block)


class PromptInjection(unittest.TestCase):
    """build_prompt threading — byte-identity default, single-block opt-in."""

    @classmethod
    def setUpClass(cls):
        cls.doc = gc.load_brand(HUBSPOT)
        cls.seeds = gc.seed_patterns(cls.doc, HUBSPOT)
        cls.brief = (MATRIX_BRIEFS / "hubspot-v2" / "leadgen-gated-content.md").read_text()
        _, cls.body = __import__("archetype_library").parse_brief_frontmatter(cls.brief)

    def _prompt(self, **kw) -> str:
        return gc.build_prompt(self.body, HUBSPOT, "corporate-saas-clean",
                               self.seeds, **kw)

    def test_absent_parameter_is_byte_identical_to_none(self):
        self.assertEqual(self._prompt(), self._prompt(conversion_guidance=None))

    def test_block_rides_user_prompt_between_brief_and_contract(self):
        g = conv.render_guidance_block(self.brief)
        with_g = self._prompt(conversion_guidance=g)
        without = self._prompt()
        marker = "# CONVERSION STRUCTURE — "
        self.assertEqual(with_g.count(marker), 1)
        self.assertNotIn(marker, without)
        i_user = with_g.find("# USER — brief")
        i_block = with_g.find(marker)
        i_contract = with_g.find("# OUTPUT CONTRACT")
        self.assertTrue(0 < i_user < i_block < i_contract)
        # removing the injected block restores the un-guided prompt byte-exactly
        self.assertEqual(with_g.replace("\n" + g.strip() + "\n", "", 1), without)

    def test_generate_composition_flag_defaults_off(self):
        import inspect
        sig = inspect.signature(gc.generate_composition)
        param = sig.parameters["inject_conversion_guidance"]
        self.assertIs(param.default, False)


if __name__ == "__main__":
    unittest.main()
