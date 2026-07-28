#!/usr/bin/env python3
"""Regression tests: the harness gate artifact must be able to record a FAILURE.

``harness-quality.json`` is the gate's durable record of the harness's rendered
substance, and it used to be a structural pass. The writer ran only after the failure
check, and it asserted ``ok: true`` with all six checks hardcoded ``True``. Two things
followed:

  * a lane whose harness genuinely failed left an artifact reading ``ok=true`` beside
    a crashed flow, which is worse than no artifact — it actively misleads, and it did;
  * G3's ``quality.get("ok") is not True`` branch was unreachable for a real failure.
    It could only fire on a MISSING or stale file.

The contract these tests pin: the verdict is written BEFORE it is acted on, it carries
each check's own outcome plus the issues behind them, every one of the six checks is
individually reachable, and a failing verdict still fails the build.

Run:  ./venv/bin/python -m unittest \
          brand_pipeline.tests.test_harness_quality_record
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest import mock

_REPO = Path(__file__).resolve().parents[2]
_BP = _REPO / "brand_pipeline"
if str(_BP) not in sys.path:
    sys.path.insert(0, str(_BP))

import pipeline_flow as pf  # noqa: E402
import render_components_preview as rp  # noqa: E402
from artifact_digest import projection_input_digest  # noqa: E402

# A lane whose harness passes today, used to exercise the real writer end to end.
_LANE = _REPO / "runs" / "hubspot-v2" / "brand" / "brand.yaml"


class VerdictStructureTests(unittest.TestCase):
    """The verdict reports each check's OWN outcome, not a constant."""

    def test_a_clean_verdict_is_the_passing_report(self):
        quality = rp.HarnessQuality()
        self.assertTrue(quality.ok)
        self.assertEqual(quality.issues, [])
        self.assertEqual(quality.report("abc"), {
            "schemaVersion": "harness-quality.v1",
            "ok": True,
            "inputDigest": "abc",
            "checks": {name: True for name in rp.HARNESS_CHECKS},
            "issues": [],
        })

    def test_one_failing_check_leaves_the_other_five_true(self):
        quality = rp.HarnessQuality()
        quality.fail("tier2Substance", "a block has no real specimen renderer")
        report = quality.report("abc")
        self.assertFalse(report["ok"])
        self.assertFalse(report["checks"]["tier2Substance"])
        self.assertEqual(
            [name for name, ok in report["checks"].items() if ok],
            [name for name in rp.HARNESS_CHECKS if name != "tier2Substance"])
        self.assertEqual(report["issues"],
                         ["a block has no real specimen renderer"])

    def test_every_issue_survives_in_detection_order(self):
        quality = rp.HarnessQuality()
        quality.fail("richSnapshot", "first")
        quality.fail("controlGeometry", "second")
        quality.fail("richSnapshot", "third")
        self.assertEqual(quality.issues, ["first", "second", "third"])
        self.assertEqual(quality.checks()["richSnapshot"], False)
        self.assertEqual(quality.checks()["controlGeometry"], False)
        self.assertEqual(quality.checks()["tier2Substance"], True)

    def test_an_unknown_check_name_is_refused_rather_than_dropped(self):
        """A typo'd name would silently vanish from the artifact — the same class of
        bug as a hardcoded pass."""
        with self.assertRaises(KeyError):
            rp.HarnessQuality().fail("tier3Substance", "typo")

    def test_the_flat_issue_list_helper_still_answers(self):
        issues = rp.harness_quality_issues(
            {"brand": {"name": "Fixture", "snapshot": "short"}}, [], {},
            Path("."), "")
        self.assertIn("brand snapshot is missing or not a rich factual narrative",
                      issues)


class EveryCheckIsReachableTests(unittest.TestCase):
    """Each of the six checks must be able to report False for its own reason.

    This is the direct guard against the regression: while the artifact hardcoded six
    ``True``s, no check could ever be observed failing.
    """

    def _fail(self, doc: dict, patterns=(), composed=None, page: str = "") -> dict:
        return rp.harness_quality(doc, list(patterns), dict(composed or {}),
                                  Path("."), page).checks()

    def test_rich_snapshot_can_fail(self):
        checks = self._fail({"brand": {"name": "Fixture", "snapshot": "thin"}})
        self.assertFalse(checks["richSnapshot"])

    def test_public_copy_provenance_can_fail(self):
        checks = self._fail({"brand": {"name": "Fixture-v2", "snapshot": "x" * 200}})
        self.assertFalse(checks["publicCopyProvenance"])
        self.assertTrue(checks["richSnapshot"])

    def test_control_geometry_can_fail(self):
        checks = self._fail({
            "brand": {"name": "Fixture", "snapshot": "x" * 200},
            "buttons": {"primary": {
                "height": "400px",
                "sizes": {"md": {"fontSize": "16px", "padY": "8px"}},
            }},
        })
        self.assertFalse(checks["controlGeometry"])

    def test_designed_control_grammar_can_fail(self):
        checks = self._fail({"brand": {"name": "Fixture", "snapshot": "x" * 200}},
                            page="<html>no control radius here</html>")
        self.assertFalse(checks["designedControlGrammar"])

    def test_tier2_substance_can_fail(self):
        block = "measured-block-without-a-renderer"
        self.assertNotIn(block, rp.BLOCK_RENDERERS)
        checks = self._fail({
            "brand": {"name": "Fixture", "snapshot": "x" * 200},
            "blocks": {block: {"origin": "extracted", "archetype": "unmapped"}},
        })
        self.assertFalse(checks["tier2Substance"])

    def test_tier3_slots_assets_distinct_can_fail(self):
        checks = self._fail({"brand": {"name": "Fixture", "snapshot": "x" * 200}},
                            patterns=[{"id": "p1"}, {"id": "p2"}])
        self.assertFalse(checks["tier3SlotsAssetsDistinct"])

    def test_a_clean_doc_and_page_fails_nothing(self):
        checks = self._fail({"brand": {"name": "Fixture", "snapshot": "x" * 200}},
                            page="border-radius: var(--radius, 0)")
        self.assertEqual(checks, {name: True for name in rp.HARNESS_CHECKS})


@unittest.skipUnless(_LANE.is_file(), "harness lane fixture is absent")
class WrittenBeforeFailingTests(unittest.TestCase):
    """End to end through the real writer: the record lands even when the build dies."""

    def _run(self, out: Path, quality: rp.HarnessQuality | None = None):
        argv = ["render_components_preview", str(_LANE), "-o", str(out)]
        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(sys, "argv", argv))
            if quality is not None:
                stack.enter_context(mock.patch.object(
                    rp, "harness_quality", lambda *a, **k: quality))
            rp.main()

    def test_a_failing_verdict_is_recorded_and_still_fails_the_build(self):
        forced = rp.HarnessQuality()
        forced.fail("controlGeometry", "a control exceeds its measured tier")
        forced.fail("tier3SlotsAssetsDistinct", "a pattern rendered no anatomy")
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "harness"
            with self.assertRaises(RuntimeError) as ctx:
                self._run(out, forced)
            artifact = out / "harness-quality.json"
            self.assertTrue(artifact.is_file(),
                            "the failing verdict must be on disk, not only in the "
                            "exception that killed the process")
            data = json.loads(artifact.read_text())
            index_written = (out / "index.html").is_file()
        # the record says what happened …
        self.assertFalse(data["ok"])
        self.assertFalse(data["checks"]["controlGeometry"])
        self.assertFalse(data["checks"]["tier3SlotsAssetsDistinct"])
        self.assertTrue(data["checks"]["richSnapshot"])
        self.assertEqual(data["issues"], ["a control exceeds its measured tier",
                                          "a pattern rendered no anatomy"])
        self.assertEqual(data["inputDigest"],
                         projection_input_digest(_LANE.parent))
        # … and the build still failed, with the harness left unpublished
        self.assertIn("harness quality failed", str(ctx.exception))
        self.assertFalse(index_written)

    def test_a_passing_lane_still_writes_the_passing_form(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "harness"
            self._run(out)
            data = json.loads((out / "harness-quality.json").read_text())
            self.assertTrue((out / "index.html").is_file())
        self.assertEqual(data["schemaVersion"], "harness-quality.v1")
        self.assertIs(data["ok"], True)
        self.assertEqual(data["checks"], {name: True for name in rp.HARNESS_CHECKS})
        self.assertEqual(data["issues"], [])
        self.assertEqual(data["inputDigest"],
                         projection_input_digest(_LANE.parent))


class G3ReadsTheRecordedFailureTests(unittest.TestCase):
    """The branch that was unreachable: G3 blocking on a RECORDED failure rather than
    on a missing or stale file. ``pipeline_flow`` is exercised, not modified."""

    def _lane(self, td: str, ok: bool) -> Path:
        brand_dir = Path(td) / "lane" / "brand"
        preview = brand_dir.joinpath(*pf.HARNESS_PREVIEW)
        preview.parent.mkdir(parents=True)
        (brand_dir / "brand.yaml").write_text("brand:\n  name: Fixture\n")
        digest = projection_input_digest(brand_dir)
        preview.write_text(f'<html data-projection-input-digest="{digest}">ok</html>')
        quality = rp.HarnessQuality()
        if not ok:
            quality.fail("richSnapshot", "the snapshot is not a rich narrative")
        (preview.parent / "harness-quality.json").write_text(
            json.dumps(quality.report(digest), indent=2) + "\n")
        return brand_dir

    def test_a_recorded_failure_blocks_g3(self):
        with tempfile.TemporaryDirectory() as td:
            gr = pf.gate_g3_harness(self._lane(td, ok=False), build=False)
        self.assertFalse(gr.ok)
        self.assertEqual(gr.status, "blocked")
        self.assertIn("quality report failed", gr.reason)

    def test_a_recorded_pass_does_not_block_g3_on_quality(self):
        with tempfile.TemporaryDirectory() as td:
            gr = pf.gate_g3_harness(self._lane(td, ok=True), build=False)
        self.assertNotIn("quality report failed", gr.reason)


if __name__ == "__main__":
    unittest.main()
