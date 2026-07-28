#!/usr/bin/env python3
"""Regression tests: a failing gate must stay DIAGNOSABLE after the fact.

A real harness-quality failure was unrecoverable because the orchestrator clipped
the child process's output to 400 characters — the message was cut off immediately
after the header, so the actual issue list existed nowhere once the child exited.
A gate that shells out owns the child's diagnosis:

  * the child's COMPLETE combined output is written to a log beside the run's other
    logs (the record), and
  * the failure the operator reads carries a generous excerpt plus the log path
    (the readable console view), and
  * a build that dies is recorded as a BLOCKED gate rather than escaping the flow,
    so ``flow-report.json`` still describes what happened.

Run:  ./venv/bin/python -m unittest \
          brand_pipeline.tests.test_gate_failure_diagnostics
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

# A failure shaped like the one that was lost: a header followed by a long issue
# list. Every issue must survive. Generic wording — no lane or brand specifics.
N_ISSUES = 60
ISSUES = [f"check-{i:02d}: rendered substance below the bar in region {i:02d}"
          for i in range(N_ISSUES)]
FAILURE_TEXT = "harness quality failed:\n- " + "\n- ".join(ISSUES)


def _failing_module(dir_: Path, name: str) -> None:
    """A stand-in sibling CLI that fails the way a real quality gate fails."""
    (dir_ / f"{name}.py").write_text(
        "import sys\n"
        f"sys.stderr.write({FAILURE_TEXT!r})\n"
        "sys.exit(1)\n")


class ChildOutputPreservationTests(unittest.TestCase):
    def setUp(self):
        self._orig_here = pf._HERE

    def tearDown(self):
        pf._HERE = self._orig_here

    def test_full_child_output_is_written_to_a_log(self):
        with tempfile.TemporaryDirectory() as td:
            here = Path(td)
            pf._HERE = here
            _failing_module(here, "boom")
            with self.assertRaises(pf.ModuleCliError) as ctx:
                pf._run_module_cli("boom", [], log_dir=here)
            log = here / "boom.log"
            self.assertTrue(log.is_file(), "the child's output must be recorded")
            text = log.read_text()
        for issue in ISSUES:
            self.assertIn(issue, text, "every issue must survive in the log")
        self.assertEqual(ctx.exception.returncode, 1)
        self.assertEqual(ctx.exception.output.strip(), FAILURE_TEXT)

    def test_message_is_not_clipped_at_the_old_four_hundred_chars(self):
        """The exact regression: the message used to end inside the header."""
        self.assertGreaterEqual(pf.MODULE_CLI_EXCERPT_CHARS, 4000)
        with tempfile.TemporaryDirectory() as td:
            here = Path(td)
            pf._HERE = here
            _failing_module(here, "boom")
            with self.assertRaises(pf.ModuleCliError) as ctx:
                pf._run_module_cli("boom", [], log_dir=here)
        message = str(ctx.exception)
        self.assertGreater(len(message), 400)
        self.assertIn(ISSUES[0], message)
        self.assertIn(ISSUES[-1], message, "the tail of the issue list is readable")
        self.assertIn("boom.log", message, "the message points at the full record")

    def test_oversized_output_is_elided_in_the_message_but_whole_in_the_log(self):
        """The console view stays bounded; the record never is."""
        with tempfile.TemporaryDirectory() as td:
            here = Path(td)
            pf._HERE = here
            marker = "TAIL-MARKER-THAT-MUST-SURVIVE"
            (here / "huge.py").write_text(
                "import sys\n"
                f"sys.stderr.write('x' * {pf.MODULE_CLI_EXCERPT_CHARS * 2})\n"
                f"sys.stderr.write({marker!r})\n"
                "sys.exit(3)\n")
            with self.assertRaises(pf.ModuleCliError) as ctx:
                pf._run_module_cli("huge", [], log_dir=here)
            log_text = (here / "huge.log").read_text()
        self.assertIn(marker, log_text)
        self.assertNotIn(marker, str(ctx.exception))
        self.assertIn("elided", str(ctx.exception))
        self.assertIn(marker, ctx.exception.output)

    def test_unwritable_log_dir_still_raises_the_real_failure(self):
        """A log we cannot write must never mask the child's actual error."""
        with tempfile.TemporaryDirectory() as td:
            here = Path(td)
            pf._HERE = here
            _failing_module(here, "boom")
            blocked = here / "not-a-dir"
            blocked.write_text("this is a file, not a directory")
            with self.assertRaises(pf.ModuleCliError) as ctx:
                pf._run_module_cli("boom", [], log_dir=blocked)
        self.assertIsNone(ctx.exception.log_path)
        self.assertIn(ISSUES[0], str(ctx.exception))

    def test_log_dir_is_the_run_root_beside_the_other_logs(self):
        with tempfile.TemporaryDirectory() as td:
            run_root = Path(td)
            self.assertEqual(pf._flow_log_dir(run_root / "brand"), run_root)
            self.assertEqual(pf._flow_log_dir(run_root), run_root)


class G3FailureIsRecordedTests(unittest.TestCase):
    """A harness build that dies is a blocked gate with the full detail attached —
    not an exception that escapes before any report is written."""

    def setUp(self):
        self._orig_here = pf._HERE

    def tearDown(self):
        pf._HERE = self._orig_here

    def _lane(self, td: str) -> Path:
        brand_dir = Path(td) / "lane" / "brand"
        brand_dir.mkdir(parents=True)
        (brand_dir / "brand.yaml").write_text("brand:\n  name: Fixture\n")
        return brand_dir

    def test_g3_blocks_and_keeps_the_child_output(self):
        with tempfile.TemporaryDirectory() as td:
            here = Path(td) / "modules"
            here.mkdir()
            pf._HERE = here
            _failing_module(here, "render_components_preview")
            brand_dir = self._lane(td)
            gr = pf.gate_g3_harness(brand_dir)
            log = brand_dir.parent / "render_components_preview.log"
            self.assertTrue(log.is_file(), "the log lands beside the run's logs")
            log_text = log.read_text()
        self.assertFalse(gr.ok)
        self.assertEqual(gr.gate, "G3")
        self.assertEqual(gr.status, "blocked")
        self.assertEqual(gr.detail["failedModule"], "render_components_preview")
        self.assertEqual(gr.detail["exitCode"], 1)
        for issue in ISSUES:
            self.assertIn(issue, log_text)
            self.assertIn(issue, gr.detail["childOutput"])

    def test_flow_records_the_blocked_gate_instead_of_crashing(self):
        with tempfile.TemporaryDirectory() as td:
            here = Path(td) / "modules"
            here.mkdir()
            pf._HERE = here
            _failing_module(here, "render_components_preview")
            brand_dir = self._lane(td)
            orig = pf.brand_dir_for
            g1, g2 = pf.gate_g1_extraction, pf.gate_g2_validation
            try:
                pf.brand_dir_for = lambda _: brand_dir
                pf.gate_g1_extraction = lambda *a, **k: pf.GateResult(
                    "G1", pf.GATE_NAMES["G1"], True, "pass")
                pf.gate_g2_validation = lambda *a, **k: pf.GateResult(
                    "G2", pf.GATE_NAMES["G2"], True, "pass")
                res = pf.run_flow("__fixture__", start_from="G2")
            finally:
                pf.brand_dir_for = orig
                pf.gate_g1_extraction, pf.gate_g2_validation = g1, g2
            report = json.loads((brand_dir / pf.FLOW_REPORT_JSON).read_text())
            md = (brand_dir / pf.FLOW_REPORT_MD).read_text()
        self.assertEqual(res.blocked_gate, "G3")
        self.assertFalse(res.generation_allowed)
        g3 = next(g for g in report["gates"] if g["gate"] == "G3")
        # the JSON record is COMPLETE …
        for issue in ISSUES:
            self.assertIn(issue, g3["detail"]["childOutput"])
        # … and the markdown view says so rather than pretending it is the whole story
        self.assertIn(pf.FLOW_REPORT_JSON, md)


class ReportReadabilityTests(unittest.TestCase):
    def test_long_reason_is_whole_in_json_and_flagged_in_markdown(self):
        long_reason = "y" * (pf.REPORT_REASON_CHARS * 3)
        result = pf.FlowResult("fixture", Path("."), ok=False, status="blocked",
                               replica_bar=pf.DEFAULT_REPLICA_BAR)
        result.gates = [pf.GateResult("G3", pf.GATE_NAMES["G3"], False, "blocked",
                                      long_reason)]
        result.blocked_gate = "G3"
        with tempfile.TemporaryDirectory() as td:
            result.brand_dir = Path(td)
            pf.write_flow_report(result)
            data = json.loads((Path(td) / pf.FLOW_REPORT_JSON).read_text())
            md = (Path(td) / pf.FLOW_REPORT_MD).read_text()
        self.assertEqual(data["gates"][0]["reason"], long_reason)
        self.assertIn(pf.FLOW_REPORT_JSON, md)
        self.assertLess(len(md), len(long_reason))


if __name__ == "__main__":
    unittest.main()
