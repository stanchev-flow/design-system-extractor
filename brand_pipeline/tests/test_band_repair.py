#!/usr/bin/env python3
"""Unit tests for brand_pipeline/band_repair.py — the LLM band-repair adapter
(spec/convergence-loop.md §7.3). All model calls are FAKES.

Run:  ./venv/bin/python -m unittest brand_pipeline.tests.test_band_repair
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

_REPO = Path(__file__).resolve().parents[2]
for p in (str(_REPO), str(_REPO / "brand_pipeline")):
    if p not in sys.path:
        sys.path.insert(0, p)

from brand_pipeline import band_repair as br  # noqa: E402
from author_brand import AuthorBlocked  # noqa: E402

SNAPSHOT = ("A synthetic fixture brand used only in unit tests; its visual "
            "system pairs a neutral ink palette with a single accent and a "
            "serif display voice over a humanist body face across all bands.")

BRAND = {
    "brand": {"name": "Fixture", "snapshot": {"value": SNAPSHOT}},
    "tokens": {"colors": {"text/default": {"value": "#101828"}}},
    "blocks": {"header": {"origin": "extracted"}},
    "layouts": [
        {"id": "hero-band", "archetype": "stack", "useCase": "hero",
         "patternRef": {"lib": "project", "id": "hero-band"},
         "slots": [{"name": "heading", "type": "content", "width": "half"}]},
        {"id": "cta-band", "archetype": "stack", "useCase": "cta",
         "patternRef": {"lib": "project", "id": "cta-band"},
         "slots": [{"name": "heading", "type": "content", "width": "hug"}]},
    ],
}
LIBRARY = {"schemaVersion": "layout-patterns.v1",
           "patterns": [{"id": "hero-band", "useCase": "hero",
                         "origin": "designed"},
                        {"id": "cta-band", "useCase": "cta",
                         "origin": "designed"}]}
COPY = {"sectionCopy": {"wordmark": "Fixture"},
        "layoutCopy": {"cta-band": {"heading": "Closing headline"}}}

CANDIDATE = {"section": "cta-band", "capability": "content width diverges",
             "gap": "authoring", "score": 0.85,
             "note": "content span 0.11 of band vs source 0.69"}


def _valid_patch_response():
    fixed = dict(BRAND["layouts"][1])
    fixed["slots"] = [{"name": "heading", "type": "content", "width": "full"}]
    return json.dumps({"patches": [{
        "file": "brand.yaml", "op": "replace", "path": "/layouts/1",
        "value": fixed,
    }]})


class BandRepairTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="band-repair-")
        self.brand_dir = Path(self._tmp) / "brand"
        self.brand_dir.mkdir(parents=True)
        (self.brand_dir / "brand.yaml").write_text(yaml.safe_dump(BRAND))
        (self.brand_dir / "layout-library.yaml").write_text(
            yaml.safe_dump(LIBRARY))
        (self.brand_dir / "section-copy.yaml").write_text(yaml.safe_dump(COPY))

    def tearDown(self):
        shutil.rmtree(self._tmp, ignore_errors=True)

    # ── resolution ───────────────────────────────────────────────────────────

    def test_resolve_band_joins_layout_pattern_copy(self):
        resolved = br.resolve_band(self.brand_dir, "cta-band")
        self.assertEqual(resolved["index"], 1)
        self.assertEqual(resolved["patternId"], "cta-band")
        self.assertEqual(resolved["pattern"]["useCase"], "cta")
        self.assertEqual(resolved["layoutCopy"]["heading"], "Closing headline")

    def test_resolve_unknown_section_is_none(self):
        self.assertIsNone(br.resolve_band(self.brand_dir, "phantom-band"))

    # ── bundle discipline ────────────────────────────────────────────────────

    def test_bundle_never_carries_the_score(self):
        resolved = br.resolve_band(self.brand_dir, "cta-band")
        bundle = br.build_band_bundle(self.brand_dir, CANDIDATE, resolved)
        flat = json.dumps(bundle)
        self.assertNotIn("0.85", flat)
        self.assertNotIn("score", flat.lower())
        self.assertIn("content span 0.11", flat)  # the diff note IS evidence

    # ── repair_call behavior ─────────────────────────────────────────────────

    def test_valid_patch_applies_and_returns_true(self):
        calls = []
        def fake_caller(system, user):
            calls.append((system, user))
            return _valid_patch_response()
        rc = br.make_llm_repair_call(caller=fake_caller)
        self.assertTrue(rc(self.brand_dir, dict(CANDIDATE)))
        doc = yaml.safe_load((self.brand_dir / "brand.yaml").read_text())
        self.assertEqual(doc["layouts"][1]["slots"][0]["width"], "full")
        # fence text reached the model; score never did
        self.assertIn("/layouts", calls[0][0])
        self.assertNotIn("0.85", calls[0][1])

    def test_out_of_fence_patch_raises_authorblocked(self):
        def rogue_caller(system, user):
            return json.dumps({"patches": [{
                "file": "brand.yaml", "op": "merge", "path": "/tokens",
                "value": {"colors": {"text/default": {"value": "#ff0000"}}}}]})
        rc = br.make_llm_repair_call(caller=rogue_caller)
        with self.assertRaises(AuthorBlocked):
            rc(self.brand_dir, dict(CANDIDATE))
        doc = yaml.safe_load((self.brand_dir / "brand.yaml").read_text())
        self.assertEqual(doc["tokens"]["colors"]["text/default"]["value"],
                         "#101828")  # untouched

    def test_non_authoring_gaps_skip_the_model(self):
        calls = []
        rc = br.make_llm_repair_call(
            caller=lambda s, u: calls.append(1) or _valid_patch_response())
        for gap in ("evidence", "asset", "renderer"):
            cand = dict(CANDIDATE); cand["gap"] = gap
            self.assertFalse(rc(self.brand_dir, cand))
        self.assertEqual(calls, [])

    def test_unjoinable_section_returns_false_without_call(self):
        calls = []
        rc = br.make_llm_repair_call(
            caller=lambda s, u: calls.append(1) or _valid_patch_response())
        cand = dict(CANDIDATE); cand["section"] = "phantom-band"
        self.assertFalse(rc(self.brand_dir, cand))
        self.assertEqual(calls, [])

    def test_no_authoring_fix_verdict_returns_demote(self):
        def honest_caller(system, user):
            # the system prompt must offer the legal no-fix escape
            self.assertIn("noAuthoringFix", system)
            return json.dumps({"patches": [], "noAuthoringFix": True,
                               "reason": "gap is renderer behavior"})
        telemetry = []
        rc = br.make_llm_repair_call(caller=honest_caller, telemetry=telemetry)
        self.assertEqual(rc(self.brand_dir, dict(CANDIDATE)), "demote")
        self.assertTrue(telemetry[0]["noAuthoringFix"])
        # canon untouched
        doc = yaml.safe_load((self.brand_dir / "brand.yaml").read_text())
        self.assertEqual(doc["layouts"][1]["slots"][0]["width"], "hug")

    def test_telemetry_records_the_round(self):
        telemetry = []
        rc = br.make_llm_repair_call(caller=lambda s, u: _valid_patch_response(),
                                     telemetry=telemetry)
        rc(self.brand_dir, dict(CANDIDATE))
        self.assertEqual(len(telemetry), 1)
        self.assertEqual(telemetry[0]["section"], "cta-band")
        self.assertIn("brand.yaml", telemetry[0]["applied"])


class ConvergeWiringTests(unittest.TestCase):
    def _args(self, **over):
        import argparse
        ns = argparse.Namespace(
            converge=False, converge_bands_per_round=None,
            author_model="claude-opus-4-8", author_timeout=300.0,
            replica_bar=0.90)
        for k, v in over.items():
            setattr(ns, k, v)
        return ns

    def test_no_flag_means_no_hook(self):
        sys.path.insert(0, str(_REPO))
        import run_pipeline_flow as rpf
        self.assertIsNone(rpf.build_converge_hook(self._args()))

    def test_flag_builds_a_hook(self):
        import run_pipeline_flow as rpf
        hook = rpf.build_converge_hook(self._args(converge=True))
        self.assertTrue(callable(hook))


if __name__ == "__main__":
    unittest.main()
