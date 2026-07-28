#!/usr/bin/env python3
"""The framework generation lane obeys the same fail-closed gates as every other
page generation, and records honestly what it did.

The framework lane used to be the ONE generation path with no gate: it did model
work and wrote a React app without ever consulting the validator, the replica
score, or ``assert_generation_allowed``. Every recurring fidelity failure
(invented bands, wrong-slot assets, a blank page, literal ``\\uXXXX`` escapes in
rendered text) came out of that lane.

Coverage:
  - GATE: ``generate_framework_site`` refuses BEFORE any scaffold/model work for a
    lane that failed a gate, and the refusal names the gate (G3 harness / G4
    replica below bar) and why.
  - OVERRIDE: opt-in, default OFF, honoured via argument OR env var, and recorded
    rather than silent.
  - LANE RESOLUTION: the gate is found by walking up from the output dir, so a
    per-run lane script inherits it without knowing about it.
  - FROZEN INPUTS: the exact assembled payload + the prompt used are written into
    the run before the model call.
  - C12: literal ``\\uXXXX`` escapes in generated framework SOURCE are caught,
    while a built single-file bundle's legitimate vendor escapes are not.
  - HONEST MANIFEST: a gate failure cannot be recorded as a completed run, and
    the replica score comes from the measured report, never a stale manifest.

No model calls and no npm: the gate raises before any of that, and the payload
freeze is exercised directly.

Run:  ./venv/bin/python -m unittest brand_pipeline.tests.test_framework_lane_gating
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_REPO = Path(__file__).resolve().parents[2]
for _p in (str(_REPO / "brand_pipeline"), str(_REPO / "tools" / "extract"),
           str(_REPO / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import pipeline_flow as pf  # noqa: E402
import validate_brand_evidence as vbe  # noqa: E402
from screenshot_to_template import framework_generator as fg  # noqa: E402

SCORE_BELOW_BAR = 0.7437       # greenhouse-4's measured replica
SCORE_ABOVE_BAR = 0.956        # hubspot-v2's committed replica


def _lane(root: Path, **flow) -> Path:
    """A brand lane whose framework output dir hangs off it, like a real run."""
    lane = root / "brand"
    (lane / "framework" / "single").mkdir(parents=True, exist_ok=True)
    (lane / "brand.yaml").write_text("brand:\n  name: Fixture\n")
    if flow:
        (lane / "flow-report.json").write_text(json.dumps(flow))
    return lane


def _replica_report(lane: Path, overall: float) -> None:
    out = lane / "compose" / "replica"
    out.mkdir(parents=True, exist_ok=True)
    (out / "replica-report.json").write_text(json.dumps({"overall": overall}))


class _Rep:
    """Minimal stand-in for the validator's Report (errors only)."""

    def __init__(self) -> None:
        self.errors: list[tuple[str, str]] = []

    def error(self, check: str, message: str) -> None:
        self.errors.append((check, message))

    def warn(self, check: str, message: str) -> None:  # pragma: no cover
        pass


# ── the gate ──────────────────────────────────────────────────────────────────

class FrameworkGateTests(unittest.TestCase):
    def setUp(self) -> None:
        # the override must never leak in from the ambient environment
        self._env = mock.patch.dict(
            os.environ, {fg.FRAMEWORK_ALLOW_UNGATED_ENV: ""})
        self._env.start()
        self.addCleanup(self._env.stop)

    def test_refuses_lane_blocked_at_harness(self):
        with tempfile.TemporaryDirectory() as td:
            lane = _lane(Path(td), status="blocked", generationAllowed=False,
                         blockedGate="G3",
                         gates=[{"gate": "G3", "reason":
                                 "harness quality report failed"}])
            with self.assertRaises(pf.GenerationBlocked) as ctx:
                fg.assert_framework_generation_allowed(lane)
        message = str(ctx.exception)
        self.assertIn("G3", message)
        self.assertIn("harness", message)
        self.assertIn("harness quality report failed", message)

    def test_refuses_lane_below_replica_bar_and_names_the_score(self):
        with tempfile.TemporaryDirectory() as td:
            lane = _lane(Path(td))
            (lane / "manifest.json").write_text(json.dumps(
                {"status": "completed", "validation": {"errors": 0}}))
            _replica_report(lane, SCORE_BELOW_BAR)
            with self.assertRaises(pf.GenerationBlocked) as ctx:
                fg.assert_framework_generation_allowed(lane)
        message = str(ctx.exception)
        self.assertIn("G4", message)
        self.assertIn("replica", message)
        self.assertIn(str(SCORE_BELOW_BAR), message)

    def test_refuses_lane_with_no_gate_record_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            lane = _lane(Path(td))
            with self.assertRaises(pf.GenerationBlocked):
                fg.assert_framework_generation_allowed(lane)

    def test_allows_cleared_lane(self):
        with tempfile.TemporaryDirectory() as td:
            lane = _lane(Path(td), status="completed", generationAllowed=True)
            record = fg.assert_framework_generation_allowed(lane)
        self.assertTrue(record["allowed"])
        self.assertTrue(record["enforced"])
        self.assertFalse(record["override"])

    def test_refusal_names_the_documented_override(self):
        with tempfile.TemporaryDirectory() as td:
            lane = _lane(Path(td), status="needs_iteration",
                         generationAllowed=False, blockedGate="G4")
            with self.assertRaises(pf.GenerationBlocked) as ctx:
                fg.assert_framework_generation_allowed(lane)
        self.assertIn(fg.FRAMEWORK_ALLOW_UNGATED_ENV, str(ctx.exception))


class FrameworkOverrideTests(unittest.TestCase):
    def setUp(self) -> None:
        self._env = mock.patch.dict(
            os.environ, {fg.FRAMEWORK_ALLOW_UNGATED_ENV: ""})
        self._env.start()
        self.addCleanup(self._env.stop)

    def test_override_defaults_off(self):
        self.assertFalse(fg.framework_ungated_override())

    def test_override_argument_generates_and_records_the_refusal(self):
        logged: list[str] = []
        with tempfile.TemporaryDirectory() as td:
            lane = _lane(Path(td), status="needs_iteration",
                         generationAllowed=False, blockedGate="G4")
            record = fg.assert_framework_generation_allowed(
                lane, allow_ungated=True, log=logged.append)
        self.assertTrue(record["override"])
        self.assertFalse(record["allowed"])          # honest: still not cleared
        self.assertTrue(any("GATE OVERRIDDEN" in line for line in logged))

    def test_override_env_var(self):
        with tempfile.TemporaryDirectory() as td:
            lane = _lane(Path(td), status="blocked", generationAllowed=False,
                         blockedGate="G2")
            with mock.patch.dict(
                    os.environ, {fg.FRAMEWORK_ALLOW_UNGATED_ENV: "1"}):
                record = fg.assert_framework_generation_allowed(
                    lane, log=lambda *_: None)
        self.assertTrue(record["override"])

    def test_env_var_falsey_values_do_not_override(self):
        for value in ("", "0", "false", "no", "off"):
            with mock.patch.dict(
                    os.environ, {fg.FRAMEWORK_ALLOW_UNGATED_ENV: value}):
                self.assertFalse(fg.framework_ungated_override(), value)


class LaneResolutionTests(unittest.TestCase):
    """A per-run lane script passes only its output dir, so the gate has to be
    discoverable from there — otherwise the tracked gate ships ungated runs."""

    def test_resolves_lane_from_framework_output_dir(self):
        with tempfile.TemporaryDirectory() as td:
            lane = _lane(Path(td))
            found = fg.resolve_brand_lane_dir(lane / "framework" / "single")
        self.assertEqual(found, lane.resolve())

    def test_no_lane_above_output_dir(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "single"
            out.mkdir()
            self.assertIsNone(fg.resolve_brand_lane_dir(out))

    def test_generate_framework_site_refuses_before_any_work(self):
        """The refusal happens before the scaffold copy and before the model
        call — an ungated lane produces NO framework package at all."""
        with tempfile.TemporaryDirectory() as td:
            lane = _lane(Path(td), status="needs_iteration",
                         generationAllowed=False, blockedGate="G4")
            single = lane / "framework" / "single"
            with mock.patch.object(fg, "scaffold_framework_project") as scaffold, \
                    mock.patch.object(fg, "generate_framework_files") as model, \
                    mock.patch.dict(os.environ,
                                    {fg.FRAMEWORK_ALLOW_UNGATED_ENV: ""}):
                with self.assertRaises(pf.GenerationBlocked):
                    fg.generate_framework_site(
                        generation_markdown="# brand",
                        provider_name="claude",
                        single_dir=single,
                        output_html_path=single / "site.html",
                        framework_prompt="prompt",
                        log=lambda *_: None,
                    )
            scaffold.assert_not_called()
            model.assert_not_called()
            self.assertFalse((single / "framework-claude").exists())


# ── frozen generation payload + prompt snapshot ────────────────────────────────

class GenerationSnapshotTests(unittest.TestCase):
    def test_freeze_writes_payload_and_prompt(self):
        with tempfile.TemporaryDirectory() as td:
            paths = fg.freeze_generation_snapshot(
                Path(td),
                system_prompt="SYSTEM PROMPT BODY",
                user_prompt="## Measured chrome\n\nassembled payload",
                provider_name="claude",
                generation_label="brand.md tokens",
                prompt_path=Path("website-gen-framework-prompt.md"),
            )
            payload = Path(paths["payload"]).read_text()
            prompt = Path(paths["prompt"]).read_text()
            request = json.loads(Path(paths["request"]).read_text())
        self.assertIn("assembled payload", payload)
        self.assertIn("SYSTEM PROMPT BODY", prompt)
        self.assertEqual(request["provider"], "claude")
        self.assertEqual(request["payload"], fg.GENERATION_INPUT_FILENAME)

    def test_payload_frozen_before_the_model_call(self):
        """A generation that fails mid-call still leaves its inputs on disk —
        that is the whole point of freezing them."""
        with tempfile.TemporaryDirectory() as td:
            snapshot = Path(td) / "single"
            with mock.patch.object(
                    fg.AnthropicProvider, "__init__", return_value=None), \
                    mock.patch.object(fg.AnthropicProvider, "text_query",
                                      side_effect=RuntimeError("model down")):
                with self.assertRaises(RuntimeError):
                    fg.generate_framework_files(
                        "# brand facts", "claude", Path(td) / "pkg",
                        framework_prompt="PROMPT",
                        snapshot_dir=snapshot,
                    )
            frozen = (snapshot / fg.GENERATION_INPUT_FILENAME).read_text()
            prompt_frozen = (snapshot / fg.GENERATION_PROMPT_FILENAME).read_text()
        self.assertIn("# brand facts", frozen)
        self.assertEqual(prompt_frozen.strip(), "PROMPT")


# ── C12 escape hygiene over framework output ──────────────────────────────────

class C12FrameworkScopeTests(unittest.TestCase):
    def test_catches_literal_unicode_escape_in_generated_source(self):
        with tempfile.TemporaryDirectory() as td:
            lane = Path(td)
            src = lane / "framework" / "single" / "framework-claude" / "src"
            src.mkdir(parents=True)
            (src / "App.tsx").write_text(
                '<h1>the only platform you\\u2019ll need</h1>')
            rep = _Rep()
            vbe._check_escape_hygiene(rep, lane)
        self.assertEqual(len(rep.errors), 1)
        self.assertEqual(rep.errors[0][0], "C12")
        self.assertIn("App.tsx", rep.errors[0][1])
        self.assertIn("u2019", rep.errors[0][1])

    def test_ignores_vendor_escapes_in_dependencies_and_built_bundle(self):
        """A production React bundle carries dozens of legitimate \\uXXXX regex
        literals; scanning the built single-file page for them would report a
        run's worth of false positives."""
        with tempfile.TemporaryDirectory() as td:
            lane = Path(td)
            pkg = lane / "framework" / "single" / "framework-claude"
            (pkg / "src").mkdir(parents=True)
            (pkg / "src" / "App.tsx").write_text("<h1>clean copy — no escapes</h1>")
            (pkg / "node_modules" / "react").mkdir(parents=True)
            (pkg / "node_modules" / "react" / "index.js").write_text(
                r"var re=/[:A-Z_a-z\u00C0-\u00D6]/;")
            (lane / "framework" / "index.html").write_text(
                r'<html><script>var x=/\u0000|\uFFFD/g;</script></html>')
            rep = _Rep()
            vbe._check_escape_hygiene(rep, lane)
        self.assertEqual(rep.errors, [])

    def test_catches_double_escaped_entity_in_framework_page(self):
        with tempfile.TemporaryDirectory() as td:
            lane = Path(td)
            (lane / "framework").mkdir(parents=True)
            (lane / "framework" / "index.html").write_text(
                "<p>hiring &amp;mdash; done</p>")
            rep = _Rep()
            vbe._check_escape_hygiene(rep, lane)
        self.assertEqual(len(rep.errors), 1)
        self.assertIn("double-escaped", rep.errors[0][1])

    def test_framework_is_in_the_scanned_generated_dirs(self):
        self.assertIn("framework", vbe.GENERATED_ARTIFACT_DIRS)
        self.assertIn("components-preview", vbe.GENERATED_ARTIFACT_DIRS)


# ── honest manifest ───────────────────────────────────────────────────────────

class HonestManifestTests(unittest.TestCase):
    def _result(self, status: str, *, allowed: bool, gate: str | None,
                bar: float = pf.DEFAULT_REPLICA_BAR) -> pf.FlowResult:
        return pf.FlowResult("fixture", Path("."), ok=(status == "completed"),
                             status=status, replica_bar=bar,
                             blocked_gate=gate, generation_allowed=allowed)

    def test_gate_failure_cannot_claim_a_completed_run(self):
        with tempfile.TemporaryDirectory() as td:
            lane = Path(td)
            (lane / "manifest.json").write_text(json.dumps(
                {"status": "completed", "pipeline_run_completed": True}))
            result = self._result("needs_iteration", allowed=False, gate="G4")
            pf._update_manifest_status(lane, result)
            m = json.loads((lane / "manifest.json").read_text())
        self.assertEqual(m["status"], "needs_iteration")
        self.assertFalse(m["pipeline_run_completed"])
        self.assertFalse(m["generationAllowed"])
        self.assertEqual(m["blockedGate"], "G4")

    def test_cleared_run_records_completion(self):
        with tempfile.TemporaryDirectory() as td:
            lane = Path(td)
            (lane / "manifest.json").write_text(json.dumps({"status": "unknown"}))
            pf._update_manifest_status(
                lane, self._result("completed", allowed=True, gate=None))
            m = json.loads((lane / "manifest.json").read_text())
        self.assertEqual(m["status"], "completed")
        self.assertTrue(m["pipeline_run_completed"])

    def test_recorded_score_comes_from_the_measured_report(self):
        """One source of truth: the manifest is a cache of replica-report.json,
        so a hand-written better number is overwritten, not preserved."""
        with tempfile.TemporaryDirectory() as td:
            lane = Path(td)
            (lane / "manifest.json").write_text(json.dumps(
                {"status": "completed", "replica": {"overall": 0.8206,
                                                    "bar": 0.9}}))
            _replica_report(lane, SCORE_BELOW_BAR)
            pf._update_manifest_status(
                lane, self._result("needs_iteration", allowed=False, gate="G4"))
            m = json.loads((lane / "manifest.json").read_text())
        self.assertEqual(m["replica"]["overall"], SCORE_BELOW_BAR)
        self.assertEqual(m["replica"]["source"],
                         "compose/replica/replica-report.json")

    def test_stale_manifest_score_cannot_unblock_generation(self):
        """The exact greenhouse-4 shape: a manifest claiming 'completed' at 0.8206
        over a lane the replica report scores 0.7437."""
        with tempfile.TemporaryDirectory() as td:
            lane = Path(td)
            (lane / "manifest.json").write_text(json.dumps(
                {"status": "completed", "pipeline_run_completed": True,
                 "validation": {"c1_c28_errors": 0},
                 "replica": {"overall": 0.8206, "bar": 0.9}}))
            _replica_report(lane, SCORE_BELOW_BAR)
            detail = pf.generation_gate_detail(lane)
        self.assertFalse(detail["allowed"])
        self.assertEqual(detail["blockedGate"], "G4")
        self.assertEqual(detail["replica"], SCORE_BELOW_BAR)
        self.assertEqual(detail["recordedReplica"], 0.8206)
        self.assertIn("stale", detail["reason"])

    def test_manifest_validation_error_count_blocks_at_g2(self):
        with tempfile.TemporaryDirectory() as td:
            lane = Path(td)
            (lane / "manifest.json").write_text(json.dumps(
                {"status": "completed", "validation": {"c1_c28_errors": 3},
                 "replica": {"overall": SCORE_ABOVE_BAR}}))
            detail = pf.generation_gate_detail(lane)
        self.assertFalse(detail["allowed"])
        self.assertEqual(detail["blockedGate"], "G2")

    def test_flow_report_refusal_names_the_gate_and_its_reason(self):
        with tempfile.TemporaryDirectory() as td:
            lane = Path(td)
            (lane / "flow-report.json").write_text(json.dumps(
                {"status": "blocked", "generationAllowed": False,
                 "blockedGate": "G3",
                 "gates": [{"gate": "G3",
                            "reason": "harness quality report failed"}]}))
            detail = pf.generation_gate_detail(lane)
        self.assertFalse(detail["allowed"])
        self.assertEqual(detail["blockedGate"], "G3")
        self.assertEqual(detail["gateName"], "harness")
        self.assertIn("harness quality report failed", detail["reason"])


# ── the typecheck is part of the gate ─────────────────────────────────────────

class TypecheckEnabledTests(unittest.TestCase):
    def test_build_runs_the_typechecking_script(self):
        """`build` is `tsc -b && vite build`; `build:nocheck` skipped tsc and hid
        real defects in generated code."""
        with tempfile.TemporaryDirectory() as td:
            pkg = Path(td)
            (pkg / "node_modules").mkdir()
            (pkg / "dist").mkdir()
            (pkg / "dist" / "index.html").write_text("<html></html>")
            with mock.patch.object(fg.subprocess, "run") as run:
                run.return_value = mock.Mock(returncode=0, stdout="", stderr="")
                fg.build_framework_project(pkg, log=lambda *_: None)
            argv = run.call_args[0][0]
        self.assertEqual(argv, ["npm", "run", "build"])

    def test_scaffold_build_script_typechecks(self):
        scripts = json.loads(
            (_REPO / "handoff" / "scaffold" / "framework-site"
             / "package.json").read_text())["scripts"]
        self.assertIn("tsc -b", scripts["build"])

    def test_typecheck_failure_fails_the_lane(self):
        with tempfile.TemporaryDirectory() as td:
            pkg = Path(td)
            (pkg / "node_modules").mkdir()
            with mock.patch.object(fg.subprocess, "run") as run:
                run.return_value = mock.Mock(
                    returncode=2, stdout="src/App.tsx(12,7): error TS2322",
                    stderr="")
                with self.assertRaises(RuntimeError) as ctx:
                    fg.build_framework_project(pkg, log=lambda *_: None)
        self.assertIn("TS2322", str(ctx.exception))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
