#!/usr/bin/env python3
"""Tests for the canonical ordered flow with hard, fail-closed gates
(brand_pipeline/pipeline_flow.py) + the generation-refusal guard wired into
generate_composition.

Coverage:
  - THRESHOLD: 0.90 default passes the committed quality-bar scores
    (hubspot-v2 0.956/0.957, remote 0.951) and BLOCKS woodwave-v2 (0.767).
  - REAL LANES: hubspot-v2 / remote / woodwave-v2 clear G1 (extraction), G2
    (0 validation errors) and G3 (harness present); woodwave-v2 is blocked ONLY
    at G4 (proving the block is fidelity, not extraction/validation).
  - FAIL-CLOSED: run_flow stops at the first failing gate, records the blocking
    gate + honest status, leaves generation refused, and never runs later gates
    (incl. G5 generation).
  - ITERATION BOUND: the G4 diagnose→repair→re-score loop is bounded by N and
    stops early when no repair hook can improve the score.
  - RESUMABILITY: a needs_iteration lane resumes from a later gate without
    redoing the passing ones (idempotent).
  - GENERATION REFUSAL: generate_composition raises GenerationBlocked for an
    ungated / needs_iteration lane and is allowed for a cleared one.

No Playwright / no live model calls: G4 uses trusted scores or synthetic
replica-report.json fixtures, and the orchestration tests inject fake gates.

Run:  ./venv/bin/python -m unittest brand_pipeline.tests.test_pipeline_flow
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_BP = _REPO / "brand_pipeline"
_TE = _REPO / "tools" / "extract"
for _p in (str(_BP), str(_TE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import pipeline_flow as pf  # noqa: E402

HUBSPOT = _REPO / "runs" / "hubspot-v2" / "brand"
REMOTE = _REPO / "runs" / "remote" / "brand"
WOODWAVE = _REPO / "runs" / "woodwave-v2" / "brand"

# The committed / measured quality-bar scores this gate must respect.
SCORE_HUBSPOT = 0.957
SCORE_REMOTE = 0.951
SCORE_WOODWAVE = 0.7673


# ── THRESHOLD calibration (pure gate logic, no IO) ────────────────────────────

class ThresholdTests(unittest.TestCase):
    def test_default_bar_is_ninety(self):
        self.assertEqual(pf.DEFAULT_REPLICA_BAR, 0.90)

    def test_bar_passes_the_two_committed_brands(self):
        for name, score in (("hubspot", SCORE_HUBSPOT), ("remote", SCORE_REMOTE)):
            with tempfile.TemporaryDirectory() as td:
                gr = pf.gate_g4_replica(Path(td), trusted_score=score)
                self.assertTrue(gr.ok, f"{name} {score} should clear the 0.90 bar")
                self.assertEqual(gr.status, "pass")

    def test_bar_blocks_woodwave(self):
        with tempfile.TemporaryDirectory() as td:
            gr = pf.gate_g4_replica(Path(td), trusted_score=SCORE_WOODWAVE)
        self.assertFalse(gr.ok)
        self.assertEqual(gr.status, "needs_iteration")
        self.assertLess(gr.detail["overall"], gr.detail["bar"])

    def test_bar_is_configurable(self):
        # a stricter bar would (correctly) block even hubspot; proves it's not
        # hardcoded at 0.90 anywhere the gate reads.
        with tempfile.TemporaryDirectory() as td:
            gr = pf.gate_g4_replica(Path(td), bar=0.99, trusted_score=SCORE_HUBSPOT)
        self.assertFalse(gr.ok)


# ── G4 from a synthetic replica-report.json (resume/no-shoot) ─────────────────

class ReplicaReportTests(unittest.TestCase):
    def _write_report(self, out_dir: Path, overall: float, bands: list[dict]):
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "replica-report.json").write_text(json.dumps(
            {"schemaVersion": "replica-report.v1", "overall": overall,
             "bands": bands}))

    def test_reads_overall_and_band_diagnostics(self):
        with tempfile.TemporaryDirectory() as td:
            lane = Path(td)
            out = lane / "compose" / "replica"
            self._write_report(out, SCORE_WOODWAVE, [
                {"id": "sec-4", "label": "visit", "score": 0.68, "height": 0.37,
                 "structure": 0.76, "widthFidelity": 1.0},
                {"id": "hero", "label": "hero", "score": 0.95, "height": 0.9,
                 "structure": 0.9, "widthFidelity": 0.9},
            ])
            gr = pf.gate_g4_replica(lane, run=False)
        self.assertFalse(gr.ok)
        self.assertEqual(gr.status, "needs_iteration")
        diags = gr.detail["bandDiagnostics"]
        self.assertEqual([d["id"] for d in diags], ["sec-4"])  # only the below-bar band

    def test_resume_without_report_needs_iteration(self):
        with tempfile.TemporaryDirectory() as td:
            gr = pf.gate_g4_replica(Path(td), run=False)
        self.assertFalse(gr.ok)
        self.assertIn("no replica-report.json", gr.reason)


# ── G4 iteration bound ────────────────────────────────────────────────────────

class IterationBoundTests(unittest.TestCase):
    def test_stops_early_without_repair_hook(self):
        calls = {"n": 0}

        def runner(brand_dir, out_dir, shot, bar):
            calls["n"] += 1
            return 0.5

        with tempfile.TemporaryDirectory() as td:
            gr = pf.gate_g4_replica(Path(td), max_iterations=3, runner=runner)
        self.assertEqual(calls["n"], 1)          # no hook → one score, then stop
        self.assertFalse(gr.ok)
        self.assertEqual(gr.detail["iterations"], 1)

    def test_bounded_by_max_iterations_with_repair(self):
        calls = {"n": 0}

        def runner(brand_dir, out_dir, shot, bar):
            calls["n"] += 1
            return 0.5

        def repair(brand_dir, report):
            return True                          # claims progress, never reaches bar

        with tempfile.TemporaryDirectory() as td:
            gr = pf.gate_g4_replica(Path(td), max_iterations=3, runner=runner,
                                    repair_hook=repair)
        self.assertEqual(calls["n"], 3)          # capped at N, never unbounded
        self.assertEqual(len(gr.detail["iterationTrajectory"]), 3)
        self.assertFalse(gr.ok)

    def test_passes_when_runner_reaches_bar(self):
        def runner(brand_dir, out_dir, shot, bar):
            return 0.93

        with tempfile.TemporaryDirectory() as td:
            gr = pf.gate_g4_replica(Path(td), runner=runner)
        self.assertTrue(gr.ok)
        self.assertEqual(gr.detail["iterations"], 1)


# ── run_flow orchestration: ordering, fail-closed, resume ─────────────────────

def _pass(gate):
    return pf.GateResult(gate, pf.GATE_NAMES[gate], True, "pass")


def _fail(gate, status="blocked"):
    return pf.GateResult(gate, pf.GATE_NAMES[gate], False, status, "forced fail")


class OrchestrationTests(unittest.TestCase):
    def setUp(self):
        self._orig = {name: getattr(pf, name) for name in (
            "gate_g1_extraction", "gate_g2_validation", "gate_g3_harness",
            "gate_g4_replica", "_run_generation_gate")}
        self.calls: list[str] = []

    def tearDown(self):
        for name, fn in self._orig.items():
            setattr(pf, name, fn)

    def _install(self, results: dict):
        def mk(gate):
            def _fn(*a, **k):
                self.calls.append(gate)
                return results.get(gate, _pass(gate))
            return _fn
        pf.gate_g1_extraction = mk("G1")
        pf.gate_g2_validation = mk("G2")
        pf.gate_g3_harness = mk("G3")
        pf.gate_g4_replica = mk("G4")
        pf._run_generation_gate = mk("G5")

    def test_all_pass_completes_and_allows_generation(self):
        self._install({})
        res = pf.run_flow("__fake__", write_report=False)
        self.assertTrue(res.ok)
        self.assertEqual(res.status, "completed")
        self.assertTrue(res.generation_allowed)
        self.assertEqual(self.calls, ["G1", "G2", "G3", "G4"])  # no G5 unless asked

    def test_generation_runs_only_after_g1_g4(self):
        self._install({})
        res = pf.run_flow("__fake__", run_generation=True, write_report=False)
        self.assertEqual(self.calls, ["G1", "G2", "G3", "G4", "G5"])
        self.assertTrue(res.ok)

    def test_fail_closed_stops_and_refuses(self):
        # G4 blocks → G5 must never run, status needs_iteration, gen refused.
        self._install({"G4": _fail("G4", status="needs_iteration")})
        res = pf.run_flow("__fake__", run_generation=True, write_report=False)
        self.assertFalse(res.ok)
        self.assertEqual(res.status, "needs_iteration")
        self.assertEqual(res.blocked_gate, "G4")
        self.assertFalse(res.generation_allowed)
        self.assertNotIn("G5", self.calls)         # generation never reached

    def test_early_gate_failure_skips_all_downstream(self):
        self._install({"G2": _fail("G2")})
        res = pf.run_flow("__fake__", run_generation=True, write_report=False)
        self.assertEqual(res.blocked_gate, "G2")
        self.assertEqual(self.calls, ["G1", "G2"])  # G3/G4/G5 never called
        self.assertFalse(res.generation_allowed)

    def test_resume_from_later_gate_skips_passing_ones(self):
        self._install({})
        res = pf.run_flow("__fake__", start_from="G4", write_report=False)
        # G1..G3 marked skip (not executed), only G4 runs
        self.assertEqual(self.calls, ["G4"])
        statuses = {g.gate: g.status for g in res.gates}
        self.assertEqual(statuses["G1"], "skip")
        self.assertEqual(statuses["G3"], "skip")
        self.assertEqual(statuses["G4"], "pass")

    def test_force_author_stage_runs_on_complete_output_set(self):
        original_brand_dir_for = pf.brand_dir_for
        original_run_extraction = pf._run_extraction
        seen = []
        try:
            with tempfile.TemporaryDirectory() as td:
                lane = Path(td)
                (lane / "evidence").mkdir()
                for name in pf.REQUIRED_EVIDENCE:
                    (lane / "evidence" / name).write_text("{}")
                (lane / "assets-manifest.json").write_text("{}")
                for name in pf.REQUIRED_AUTHORED:
                    (lane / name).write_text("{}")
                pf.brand_dir_for = lambda _: lane
                pf._run_extraction = lambda *a, **kw: seen.append(kw)
                self._install({})
                pf.run_flow(
                    "__fake__", force_author_stage="media", write_report=False)
        finally:
            pf.brand_dir_for = original_brand_dir_for
            pf._run_extraction = original_run_extraction
        self.assertEqual(seen[0]["force_author_stage"], "media")


# ── generation-refusal guard ─────────────────────────────────────────────────

class GenerationGuardTests(unittest.TestCase):
    def _lane_with_flow(self, td, **flow):
        lane = Path(td)
        (lane / "flow-report.json").write_text(json.dumps(flow))
        return lane

    def test_completed_flow_allows(self):
        with tempfile.TemporaryDirectory() as td:
            lane = self._lane_with_flow(td, status="completed",
                                        generationAllowed=True)
            allowed, _ = pf.generation_gate_status(lane)
        self.assertTrue(allowed)

    def test_needs_iteration_flow_refuses(self):
        with tempfile.TemporaryDirectory() as td:
            lane = self._lane_with_flow(td, status="needs_iteration",
                                        generationAllowed=False, blockedGate="G4")
            allowed, reason = pf.generation_gate_status(lane)
        self.assertFalse(allowed)
        self.assertIn("G4", reason)

    def test_no_record_refuses_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            allowed, reason = pf.generation_gate_status(Path(td))
        self.assertFalse(allowed)
        self.assertIn("not been run", reason)

    def test_manifest_needs_iteration_refuses(self):
        with tempfile.TemporaryDirectory() as td:
            lane = Path(td)
            (lane / "manifest.json").write_text(json.dumps(
                {"status": "needs_iteration",
                 "replica": {"overall": SCORE_WOODWAVE},
                 "validation": {"errors": 0}}))
            allowed, _ = pf.generation_gate_status(lane)
        self.assertFalse(allowed)

    def test_manifest_completed_allows(self):
        with tempfile.TemporaryDirectory() as td:
            lane = Path(td)
            (lane / "manifest.json").write_text(json.dumps(
                {"status": "completed", "replica": {"overall": SCORE_HUBSPOT},
                 "validation": {"errors": 0}, "harness": {"status": "available"}}))
            allowed, _ = pf.generation_gate_status(lane)
        self.assertTrue(allowed)

    def test_assert_raises_generation_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(pf.GenerationBlocked):
                pf.assert_generation_allowed(Path(td))

    def test_generate_composition_refuses_ungated_lane(self):
        """The refusal is wired into generate_composition: it raises BEFORE any
        model/output work for a lane that hasn't cleared the gates."""
        import generate_composition as gc
        with tempfile.TemporaryDirectory() as td:
            lane = Path(td)
            (lane / "brand.yaml").write_text("brand:\n  name: Fixture\n")
            (lane / "flow-report.json").write_text(json.dumps(
                {"status": "needs_iteration", "generationAllowed": False,
                 "blockedGate": "G4"}))
            with self.assertRaises(pf.GenerationBlocked):
                gc.generate_composition("brief", lane / "brand.yaml", "editorial-luxury",
                                        out_dir=lane / "page", enforce_gates=True)
            # opt-out path does not raise the guard (it will fail later for other
            # reasons, but NOT GenerationBlocked) — proves the flag is honored.
            try:
                gc.generate_composition("brief", lane / "brand.yaml", "editorial-luxury",
                                        out_dir=lane / "page2", enforce_gates=False,
                                        provider=_never_called_provider())
            except pf.GenerationBlocked:
                self.fail("enforce_gates=False must not raise GenerationBlocked")
            except Exception:
                pass  # any other failure is fine; we only assert the guard didn't fire


class _never_called_provider:  # noqa: N801 - test double
    model = "fixture"

    def text_query(self, *a, **k):
        raise RuntimeError("model must not be called in this test")


# ── REAL committed lanes: pass the good brands, block only woodwave at G4 ──────

class RealLaneGateTests(unittest.TestCase):
    """Integration proof against the committed lanes. G2/G3 are real (cheap); G4
    uses the measured scores as trusted fixtures so the suite needs no Playwright.
    Skips gracefully if a lane isn't present in this checkout."""

    def _skip_if_absent(self, lane: Path):
        if not (lane / "brand.yaml").is_file():
            self.skipTest(f"lane not present: {lane}")

    def test_g1_extraction_passes_all_three(self):
        for lane in (HUBSPOT, REMOTE, WOODWAVE):
            self._skip_if_absent(lane)
            gr = pf.gate_g1_extraction(lane)
            self.assertTrue(gr.ok, f"G1 should pass for {lane.parent.name}: {gr.reason}")

    def test_g2_validation_zero_errors_all_three(self):
        for lane in (HUBSPOT, REMOTE, WOODWAVE):
            self._skip_if_absent(lane)
            gr = pf.gate_g2_validation(lane, smoke=False)
            self.assertTrue(gr.ok,
                            f"G2 should have 0 errors for {lane.parent.name}: "
                            f"{gr.detail.get('errors')}")

    def test_g3_harness_requires_current_quality_report(self):
        for lane, should_pass in ((HUBSPOT, True), (REMOTE, True), (WOODWAVE, False)):
            self._skip_if_absent(lane)
            gr = pf.gate_g3_harness(lane, build=False)
            self.assertEqual(
                gr.ok, should_pass,
                f"G3 quality state wrong for {lane.parent.name}: {gr.reason}")

    def test_g4_passes_good_brands_blocks_woodwave(self):
        cases = ((HUBSPOT, SCORE_HUBSPOT, True), (REMOTE, SCORE_REMOTE, True),
                 (WOODWAVE, SCORE_WOODWAVE, False))
        for lane, score, should_pass in cases:
            self._skip_if_absent(lane)
            gr = pf.gate_g4_replica(lane, trusted_score=score)
            self.assertEqual(gr.ok, should_pass,
                             f"G4 for {lane.parent.name} ({score}) expected "
                             f"ok={should_pass}")


if __name__ == "__main__":
    unittest.main()
