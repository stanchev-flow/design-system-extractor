#!/usr/bin/env python3
"""Claude-distillation Phase A — brand.md projections in render_brand_md.py.

Two SAFE-NOW projections pinned here (proposal runs/claude-distillation/
INTEGRATION-PROPOSAL.md §3 #2/#4):

  A1. "Signature moves — the rules that carry the look": a PURE projection of
      brand.yaml `signatures:` (both the structured dict shape and the legacy
      plain-string shape), never a parallel 5-rules structure. Fact-gated: a
      brand with no signatures omits the section.
  A2. "Provenance & confidence ledger": the four honest buckets (sampled /
      assumed / substitute / needs-licensing). CRUCIAL: every bucket annotates
      assets we STILL render — the substitute/needs-licensing framing is a flag,
      never a replacement (rejects Claude's substitution posture).
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import yaml

_BRAND_PIPELINE = Path(__file__).resolve().parent.parent
if str(_BRAND_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_BRAND_PIPELINE))

import render_brand_md as rbm  # noqa: E402


def _section(md: str, header_prefix: str) -> str:
    lines = md.splitlines()
    start = next(i for i, ln in enumerate(lines) if ln.startswith(header_prefix))
    end = next((i for i in range(start + 1, len(lines))
                if lines[i].startswith("## ")), len(lines))
    return "\n".join(lines[start:end])


class SignatureMovesProjection(unittest.TestCase):
    def test_structured_signatures_project_as_tagged_imperatives(self):
        doc = {
            "brand": {"name": "Fixture", "snapshot": {"value": "a fixture brand."}},
            "signatures": [
                {"id": "accent-scope", "kind": "accent-scope", "mode": "never",
                 "claim": "The accent ink is a control color, never a surface fill."},
                {"id": "serif-display", "kind": "type-treatment", "mode": "always",
                 "claim": "Serif display over sans body."},
            ],
        }
        md = rbm.render(doc)
        sec = _section(md, "## Signature moves")
        self.assertIn("- [never] The accent ink is a control color", sec)
        self.assertIn("_(accent-scope)_", sec)
        self.assertIn("- [always] Serif display over sans body. _(type-treatment)_", sec)

    def test_legacy_string_signatures_project_verbatim(self):
        doc = {
            "brand": {"name": "Fixture", "snapshot": {"value": "a fixture brand."}},
            "signatures": [
                "orange period accent closing display headlines",
                "warm cream-on-dark bookend bands",
            ],
        }
        sec = _section(rbm.render(doc), "## Signature moves")
        self.assertIn("- orange period accent closing display headlines", sec)
        self.assertIn("- warm cream-on-dark bookend bands", sec)
        # no [always]/[never] tag and no kind suffix for the bare-string shape
        self.assertNotIn("[always]", sec)
        self.assertNotIn("_(", sec)

    def test_section_omitted_when_no_signatures(self):
        doc = {"brand": {"name": "Fixture", "snapshot": {"value": "a fixture brand."}}}
        self.assertNotIn("## Signature moves", rbm.render(doc))

    def test_empty_claim_dicts_are_skipped(self):
        doc = {
            "brand": {"name": "Fixture", "snapshot": {"value": "a fixture brand."}},
            "signatures": [{"id": "x", "kind": "shape-motif", "mode": "always"}],
        }
        self.assertNotIn("## Signature moves", rbm.render(doc))


class ProvenanceLedger(unittest.TestCase):
    def _doc(self):
        return {
            "brand": {"name": "Fixture", "snapshot": {"value": "a fixture brand."}},
            "tokens": {
                "colors": {"a": {"value": "#000"}, "b": {"value": "#fff"}},
                "type": {
                    "display": {"family": "RealSerif", "renderProxy": "Georgia",
                                "weight": 500},
                    "body": {"family": "RealSans", "weight": 400},
                },
                "spacing": {"gap": {"value": "1rem"}},
            },
            "primitives": {
                "label": {"origin": "designed", "overridable": True},
                "heading": {"origin": "extracted"},
            },
        }

    def test_ledger_replaces_confidence_flags_and_states_render_framing(self):
        md = rbm.render(self._doc())
        self.assertIn("## 15. Provenance & confidence ledger", md)
        self.assertNotIn("## 15. Confidence flags", md)
        sec = _section(md, "## 15.")
        # the anti-substitution framing is the whole point of the reframe
        self.assertIn("every asset and value below is **rendered**".lower(),
                      sec.lower())
        self.assertIn("never a replacement", sec.lower())

    def test_four_buckets_present(self):
        sec = _section(rbm.render(self._doc()), "## 15.")
        self.assertIn("**Sampled", sec)
        self.assertIn("**Assumed", sec)
        self.assertIn("**Substitute", sec)
        self.assertIn("**Needs-licensing", sec)

    def test_substitute_bucket_names_real_family_and_proxy_fallback(self):
        sec = _section(rbm.render(self._doc()), "## 15.")
        self.assertIn("render `RealSerif`", sec)
        self.assertIn("proxy `Georgia` is the loaded fallback only", sec)

    def test_designed_entries_summarized_not_dumped(self):
        sec = _section(rbm.render(self._doc()), "## 15.")
        self.assertIn("1 primitive(s): designed contract defaults", sec)

    def test_no_proxy_brand_says_every_role_renders_real_family(self):
        doc = self._doc()
        doc["tokens"]["type"]["display"].pop("renderProxy")
        sec = _section(rbm.render(doc), "## 15.")
        self.assertIn("None — every type role renders its real family.", sec)

    def test_needs_licensing_reads_media_assets_third_party_and_own_logos(self):
        with tempfile.TemporaryDirectory() as td:
            brand_dir = Path(td)
            (brand_dir / "media-assets.yaml").write_text(yaml.safe_dump({
                "schemaVersion": "media-assets.v1",
                "assets": [
                    {"id": "mark-a", "usageRights": "third-party-mark",
                     "assetSemantics": {"kind": "logo-third-party"}},
                    {"id": "own-logo", "usageRights": "own",
                     "assetSemantics": {"kind": "logo-own"}},
                    {"id": "photo", "usageRights": "own",
                     "assetSemantics": {"kind": "photograph"}},
                ],
            }))
            sec = _section(rbm.render(self._doc(), brand_dir=brand_dir), "## 15.")
        self.assertIn("1 third-party mark(s)", sec)
        self.assertIn("1 own logo mark(s)", sec)
        self.assertIn("never auto-substituted", sec)

    def test_needs_licensing_none_flagged_without_media_assets(self):
        sec = _section(rbm.render(self._doc()), "## 15.")
        self.assertIn("None flagged.", sec)


class RealBrandProjection(unittest.TestCase):
    """Smoke-render the committed reference brands so the projection can't crash
    on a real brand.yaml shape (string signatures, no proxy, third-party marks)."""

    REPO = _BRAND_PIPELINE.parent

    def test_hubspot_v3_projects_both_new_sections(self):
        bd = self.REPO / "runs" / "hubspot-v3" / "brand"
        if not (bd / "brand.yaml").exists():
            self.skipTest("hubspot-v3 brand.yaml absent")
        doc = yaml.safe_load((bd / "brand.yaml").read_text())
        md = rbm.render(doc, brand_dir=bd)
        self.assertIn("## Signature moves — the rules that carry the look", md)
        self.assertIn("## 15. Provenance & confidence ledger", md)
        self.assertIn("third-party mark(s)", _section(md, "## 15."))


if __name__ == "__main__":
    unittest.main(verbosity=2)
