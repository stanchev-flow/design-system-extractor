#!/usr/bin/env python3
"""Claude-distillation Phase B — brand-essence lead in build_prompt.

The one-line identity anchor (`brand.snapshot`) now LEADS the composition system
prompt so the model composes toward the brand's look first
(runs/claude-distillation/INTEGRATION-PROPOSAL.md §3 #1). Pins:

  - present: a brand carrying a snapshot gets a `## Brand essence` block ABOVE
    the composition grammar and the brand-facts block, with the real snapshot
    text inside;
  - framing-only: the block states it never outranks neverDo / the gate battery
    (risk R4 mitigation);
  - fact-gated byte-identity: a brand with NO snapshot gets NO block and a prompt
    byte-identical to the pre-essence assembly (proven structurally — strip the
    block and the two prompts match).
"""
from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

_BRAND_PIPELINE = Path(__file__).resolve().parent.parent
if str(_BRAND_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_BRAND_PIPELINE))

import generate_composition as gc  # noqa: E402

REPO = _BRAND_PIPELINE.parent
HUBSPOT = REPO / "runs" / "hubspot-v2" / "brand" / "brand.yaml"

ESSENCE_HEADER = "## Brand essence (rebuild the look from THIS first)"


def _prompt(brand_yaml: Path, **kw) -> str:
    doc = gc.load_brand(brand_yaml)
    seeds = gc.seed_patterns(doc, brand_yaml)
    return gc.build_prompt("Brief.", brand_yaml, "corporate-saas-clean", seeds, **kw)


class EssenceHelper(unittest.TestCase):
    def test_unwraps_envelope_and_collapses_whitespace(self):
        doc = {"brand": {"snapshot": {"value": "  warm\n  editorial system  "}}}
        self.assertEqual(gc._brand_essence(doc), "warm editorial system")

    def test_absent_snapshot_returns_empty(self):
        self.assertEqual(gc._brand_essence({"brand": {"name": "x"}}), "")
        self.assertEqual(gc._brand_essence({}), "")


class EssenceLeadsPrompt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prompt = _prompt(HUBSPOT)

    def test_block_present_with_real_snapshot_text(self):
        self.assertEqual(self.prompt.count(ESSENCE_HEADER), 1)
        snap = gc._brand_essence(gc.load_brand(HUBSPOT))
        # the first ~60 chars of the real snapshot ride inside the block
        self.assertIn(snap[:60], self.prompt)

    def test_essence_leads_grammar_and_brand_facts(self):
        i = self.prompt.index(ESSENCE_HEADER)
        self.assertLess(i, self.prompt.index("## Composition grammar"))
        self.assertLess(i, self.prompt.index("## Brand facts"))

    def test_block_is_framing_not_a_constraint(self):
        i = self.prompt.index(ESSENCE_HEADER)
        block = self.prompt[i:self.prompt.index("## Composition grammar")]
        self.assertIn("never outranks brand neverDo", block)


class FactGatedByteIdentity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.td = tempfile.mkdtemp(prefix="essence-gate-")
        src = HUBSPOT.parent
        cls.with_dir = Path(cls.td) / "with-snapshot"
        cls.without_dir = Path(cls.td) / "without-snapshot"
        for dst in (cls.with_dir, cls.without_dir):
            shutil.copytree(src, dst)
        doc = yaml.safe_load((cls.without_dir / "brand.yaml").read_text())
        doc["brand"].pop("snapshot", None)
        (cls.without_dir / "brand.yaml").write_text(yaml.safe_dump(doc, sort_keys=False))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.td, ignore_errors=True)

    def test_no_block_when_snapshot_absent(self):
        self.assertNotIn(ESSENCE_HEADER, _prompt(self.without_dir / "brand.yaml"))

    def test_injection_is_purely_additive(self):
        p_with = _prompt(self.with_dir / "brand.yaml")
        p_without = _prompt(self.without_dir / "brand.yaml")
        i = p_with.index(ESSENCE_HEADER)
        essence = gc._brand_essence(gc.load_brand(self.with_dir / "brand.yaml"))
        block = (f"{ESSENCE_HEADER}\n{essence}\n"
                 "This frames the target identity; it never outranks brand neverDo or "
                 "the gate battery.\n\n")
        self.assertIn(block, p_with)
        # removing exactly the injected span reproduces the snapshot-absent assembly
        stripped = p_with.replace(block, "", 1)
        normalized = p_without.replace(str(self.without_dir), str(self.with_dir))
        self.assertEqual(stripped, normalized)


if __name__ == "__main__":
    unittest.main(verbosity=2)
