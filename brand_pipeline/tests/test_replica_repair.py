#!/usr/bin/env python3
"""Unit tests for brand_pipeline/replica_repair.py — the G4 convergence repair
hook (spec/convergence-loop.md §2). All tests are deterministic: repair calls
are FAKES that mutate synthetic canon files; no LLM, no Playwright.

Run:  ./venv/bin/python -m unittest brand_pipeline.tests.test_replica_repair
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from brand_pipeline import replica_repair as rr  # noqa: E402


def _report(bands, punch):
    return {"schemaVersion": "replica-report.v1", "overall": 0.86,
            "bands": bands, "punchList": punch}


BANDS = [
    {"id": "sec-0", "label": "hero-band — Big heading", "score": 0.80},
    {"id": "sec-1", "label": "logo-row — Proof", "score": 0.96},
    {"id": "sec-2", "label": "cta-band — Closing", "score": 0.85},
]
PUNCH = [
    {"section": "hero-band", "capability": "composite hero art",
     "score": 0.80, "note": "layers an illustration with floating chips"},
    {"section": "cta-band", "capability": "content width diverges",
     "score": 0.85, "note": "content span 0.11 of band vs source 0.69"},
]


class ClassificationTests(unittest.TestCase):
    def test_renderer_capabilities(self):
        for cap in ("composite hero art", "carousel statics", "video static",
                    "accordion open-state", "marquee animation"):
            self.assertEqual(rr.classify_capability(cap), rr.GAP_RENDERER, cap)

    def test_authoring_capabilities(self):
        self.assertEqual(rr.classify_capability("content width diverges"),
                         rr.GAP_AUTHORING)
        self.assertEqual(rr.classify_capability("fidelity below threshold"),
                         rr.GAP_AUTHORING)

    def test_asset_capability(self):
        self.assertEqual(rr.classify_capability("display font (HubSpot Serif)"),
                         rr.GAP_ASSET)

    def test_evidence_from_note(self):
        self.assertEqual(
            rr.classify_capability("odd geometry",
                                   note="sample cannot physically fit in 113px"),
            rr.GAP_EVIDENCE)

    def test_unknown_defaults_to_authoring(self):
        self.assertEqual(rr.classify_capability("mystery-capability"),
                         rr.GAP_AUTHORING)


class BandCandidateTests(unittest.TestCase):
    def test_below_bar_only_and_worst_first(self):
        cands = rr.band_candidates(_report(BANDS, PUNCH), bar=0.90)
        sections = [c["section"] for c in cands]
        self.assertEqual(sections, ["hero-band", "cta-band"])  # 0.80 first
        self.assertNotIn("logo-row", sections)

    def test_band_without_punch_item_still_surfaces(self):
        bands = BANDS + [{"id": "sec-3", "label": "quiet-band — Silent",
                          "score": 0.70}]
        cands = rr.band_candidates(_report(bands, PUNCH), bar=0.90)
        quiet = [c for c in cands if c["section"] == "quiet-band"]
        self.assertEqual(len(quiet), 1)
        self.assertEqual(quiet[0]["gap"], rr.GAP_AUTHORING)
        self.assertEqual(cands[0]["section"], "quiet-band")  # worst first


class HookTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="replica-repair-")
        self.brand_dir = Path(self._tmp) / "brand"
        self.brand_dir.mkdir(parents=True)
        for name in rr.CANON_FILES:
            (self.brand_dir / name).write_text(f"original: {name}\n")

    def tearDown(self):
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _ledger(self):
        return json.loads((self.brand_dir / rr.LEDGER_NAME).read_text())

    def test_successful_round_snapshots_and_records(self):
        def fake_repair(brand_dir, cand):
            (brand_dir / "brand.yaml").write_text("repaired: true\n")
            return True
        hook = rr.make_repair_hook(fake_repair, bar=0.90)
        self.assertTrue(hook(self.brand_dir, _report(BANDS, PUNCH)))
        led = self._ledger()
        self.assertEqual(len(led["rounds"]), 1)
        self.assertEqual(led["rounds"][0]["bandsAttempted"], ["cta-band"])
        self.assertIsNone(led["rounds"][0]["overallAfter"])  # settled next call
        snap = self.brand_dir / rr.SNAPSHOT_DIR / "iter-001" / "brand.yaml"
        self.assertTrue(snap.is_file())
        self.assertIn("original", snap.read_text())  # pre-mutation state

    def test_renderer_only_returns_false_with_work_orders(self):
        renderer_punch = [PUNCH[0]]
        bands = [BANDS[0], BANDS[1]]
        hook = rr.make_repair_hook(lambda *_: True, bar=0.90)
        self.assertFalse(hook(self.brand_dir, _report(bands, renderer_punch)))
        led = self._ledger()
        self.assertEqual(len(led["rendererWorkOrders"]), 1)
        self.assertEqual(led["rendererWorkOrders"][0]["capability"],
                         "composite hero art")
        self.assertIn("renderer-capability", led["stopped"]["reason"])

    def test_no_progress_returns_false(self):
        hook = rr.make_repair_hook(lambda *_: False, bar=0.90)
        self.assertFalse(hook(self.brand_dir, _report(BANDS, PUNCH)))
        led = self._ledger()
        self.assertEqual(led["rounds"][0]["changed"], False)

    def test_ratchet_reverts_regressed_round(self):
        def fake_repair(brand_dir, cand):
            (brand_dir / "brand.yaml").write_text("mutated-by-round-1\n")
            return True
        hook = rr.make_repair_hook(fake_repair, bar=0.90)
        r1 = _report(BANDS, PUNCH)
        self.assertTrue(hook(self.brand_dir, r1))
        # round 1 mutated the canon
        self.assertIn("mutated", (self.brand_dir / "brand.yaml").read_text())
        # next invocation arrives with a LOWER overall → round 1 must revert
        r2 = dict(_report(BANDS, PUNCH));  r2["overall"] = 0.80
        hook(self.brand_dir, r2)
        led = self._ledger()
        self.assertTrue(led["rounds"][0]["reverted"])
        self.assertIn("cta-band", led["noSelfFix"])
        self.assertIn("original", (self.brand_dir / "brand.yaml").read_text())

    def test_improved_round_is_kept(self):
        def fake_repair(brand_dir, cand):
            (brand_dir / "brand.yaml").write_text("mutated-by-round-1\n")
            return True
        hook = rr.make_repair_hook(fake_repair, bar=0.90)
        self.assertTrue(hook(self.brand_dir, _report(BANDS, PUNCH)))
        r2 = dict(_report(BANDS, PUNCH));  r2["overall"] = 0.88  # improved
        hook(self.brand_dir, r2)
        led = self._ledger()
        self.assertNotIn("reverted", led["rounds"][0])
        self.assertEqual(led["rounds"][0]["overallAfter"], 0.88)
        self.assertIn("mutated", (self.brand_dir / "brand.yaml").read_text())

    def test_validator_failure_reverts_round_with_retry_budget(self):
        class FailingReport:
            errors = ["C4: synthetic failure"]
        def fake_repair(brand_dir, cand):
            (brand_dir / "brand.yaml").write_text("bad-mutation\n")
            return True
        hook = rr.make_repair_hook(fake_repair, bar=0.90,
                                   validator=lambda d: FailingReport())
        # first failure: reverted, but retry budget remains → True (re-score)
        self.assertTrue(hook(self.brand_dir, _report(BANDS, PUNCH)))
        led = self._ledger()
        self.assertTrue(led["rounds"][0]["reverted"])
        self.assertIn("validator", led["rounds"][0]["revertReason"])
        self.assertIn("original", (self.brand_dir / "brand.yaml").read_text())
        self.assertNotIn("cta-band", led["noSelfFix"])
        # second failure: attempt cap reached → quarantined, False
        self.assertFalse(hook(self.brand_dir, _report(BANDS, PUNCH)))
        led = self._ledger()
        self.assertIn("cta-band", led["noSelfFix"])
        self.assertIn("original", (self.brand_dir / "brand.yaml").read_text())

    def test_repair_exception_reverts_then_quarantines_at_cap(self):
        def exploding(brand_dir, cand):
            (brand_dir / "brand.yaml").write_text("partial-write\n")
            raise RuntimeError("boom")
        hook = rr.make_repair_hook(exploding, bar=0.90)
        # transient failure: reverted + one retry left → True
        self.assertTrue(hook(self.brand_dir, _report(BANDS, PUNCH)))
        led = self._ledger()
        self.assertTrue(led["rounds"][0]["reverted"])
        self.assertIn("original", (self.brand_dir / "brand.yaml").read_text())
        self.assertEqual(led["attempts"]["cta-band"], 1)
        # second explosion hits MAX_BAND_ATTEMPTS → quarantine, stop
        self.assertFalse(hook(self.brand_dir, _report(BANDS, PUNCH)))
        led = self._ledger()
        self.assertIn("cta-band", led["noSelfFix"])

    def test_demote_verdict_files_work_order_without_retry(self):
        calls = []
        def no_fix_repair(brand_dir, cand):
            calls.append(cand["section"])
            return "demote"
        hook = rr.make_repair_hook(no_fix_repair, bar=0.90)
        # cta-band demotes; hero-band is renderer already → nothing changed,
        # nothing fixable remains → False
        self.assertFalse(hook(self.brand_dir, _report(BANDS, PUNCH)))
        led = self._ledger()
        self.assertEqual(calls, ["cta-band"])
        self.assertIn("cta-band", led["noSelfFix"])
        demoted = [o for o in led["rendererWorkOrders"]
                   if o["section"] == "cta-band"]
        self.assertEqual(len(demoted), 1)
        self.assertIn("model verdict", demoted[0]["note"])
        self.assertNotIn("cta-band", led.get("attempts", {}))  # no retry burn

    def test_zero_delta_round_demotes_bands(self):
        def fake_repair(brand_dir, cand):
            (brand_dir / "brand.yaml").write_text("cosmetic-only\n")
            return True
        hook = rr.make_repair_hook(fake_repair, bar=0.90)
        self.assertTrue(hook(self.brand_dir, _report(BANDS, PUNCH)))
        # next invocation: identical overall → the applied change had no
        # render effect → band demotes to a work order, not a retry
        r2 = dict(_report(BANDS, PUNCH))  # same overall 0.86
        hook(self.brand_dir, r2)
        led = self._ledger()
        self.assertTrue(led["rounds"][0].get("demotedForNoEffect"))
        self.assertIn("cta-band", led["noSelfFix"])
        demoted = [o for o in led["rendererWorkOrders"]
                   if o["section"] == "cta-band"]
        self.assertEqual(len(demoted), 1)
        self.assertIn("no render effect", demoted[0]["note"])

    def test_no_self_fix_bands_are_skipped_next_round(self):
        calls = []
        def fake_repair(brand_dir, cand):
            calls.append(cand["section"])
            (brand_dir / "brand.yaml").write_text(f"try-{len(calls)}\n")
            return True
        hook = rr.make_repair_hook(fake_repair, bar=0.90)
        hook(self.brand_dir, _report(BANDS, PUNCH))          # round 1: cta-band
        r2 = dict(_report(BANDS, PUNCH));  r2["overall"] = 0.80  # regressed
        result = hook(self.brand_dir, r2)                    # reverts, retries others
        # cta-band is now noSelfFix; the only other candidate (hero-band) is
        # RENDERER — so nothing fixable remains and the loop stops.
        self.assertFalse(result)
        self.assertEqual(calls, ["cta-band"])


if __name__ == "__main__":
    unittest.main()
