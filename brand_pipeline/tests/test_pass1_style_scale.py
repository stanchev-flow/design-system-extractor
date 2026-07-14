#!/usr/bin/env python3
"""pass1 (2026-07) — derived-scale layer tests: the normalizer's fit honesty
(tools/extract/normalize_scales.py), the consumption law (brand_pipeline/
style_scale.py + compose_section band degrade), the scale_adherence gate's
classification (spacing_audit.classify_scale + the generative-lane marker), and
the C24 validator advisory. NO Playwright — browser payloads are exercised by
the lane battery.

Run:  ./venv/bin/python -m unittest brand_pipeline.tests.test_pass1_style_scale
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

_BRAND_PIPELINE = Path(__file__).resolve().parent.parent
_ROOT = _BRAND_PIPELINE.parent
for p in (str(_BRAND_PIPELINE), str(_ROOT / "tools" / "extract")):
    if p not in sys.path:
        sys.path.insert(0, p)

import normalize_scales as ns          # noqa: E402
import spacing_audit as sa             # noqa: E402
import style_scale as ss               # noqa: E402
import compose_section as cs           # noqa: E402
from validate_brand_evidence import Report  # noqa: E402
import validate_brand_evidence as vbe  # noqa: E402


# ───────────────────────────── normalizer fit honesty ─────────────────────────────

class FitTypeTest(unittest.TestCase):
    def test_clean_modular_ladder_fits_its_ratio(self):
        # exact 1.25 ladder on base 16 — parsimony must land 1.25, not a denser
        # ratio that also fits (vacuous quantization).
        ladder = {"h3": 20.0, "h2": 25.0, "h1": 31.3, "display": 39.1, "body": 16.0}
        fit = ns.fit_type(ladder, {})
        self.assertEqual(fit["ratio"], 1.25)
        self.assertEqual(fit["basePx"], 16.0)
        self.assertTrue(fit["followsScale"])
        self.assertIn(fit["fitQuality"]["verdict"], ("good", "approximate"))

    def test_scaleless_ladder_recorded_honestly(self):
        # sizes off every candidate grid: nothing clears the parsimony RMSE bar,
        # so the min-RMSE fallback is recorded — and the ledger must SAY so
        # (rmse above the bar, verdict not 'good'). A scaleless brand's numbers
        # are never forced into a clean-looking fit.
        ladder = {"a": 16.0, "b": 21.0, "c": 23.0, "d": 37.0, "e": 55.0}
        fit = ns.fit_type(ladder, {})
        self.assertGreater(fit["fitQuality"]["rmse"], ns._RMSE_BAR)
        self.assertNotEqual(fit["fitQuality"]["verdict"], "good")
        # every recorded per-size fit keeps its true error, never snapped to 0
        worst = max(f["errPct"] for f in fit["fits"])
        self.assertAlmostEqual(worst, fit["fitQuality"]["worstErrPct"], delta=0.2)

    def test_steps_are_self_consistent(self):
        fit = ns.fit_type({"h2": 25.0, "h1": 31.3, "body": 16.0}, {})
        base, ratio = fit["basePx"], fit["ratio"]
        for s in fit["stepsPx"]:
            import math
            k = round(math.log(s / base, ratio))
            self.assertAlmostEqual(s, round(base * ratio ** k, 1), delta=0.1)

    def test_empty_ladder_degrades(self):
        self.assertFalse(ns.fit_type({}, {}).get("followsScale"))


class FitSpaceTest(unittest.TestCase):
    def test_eight_grid_wins_with_full_coverage(self):
        vals = {"a": 8.0, "b": 16.0, "c": 24.0, "d": 32.0, "e": 64.0, "f": 96.0}
        fit = ns.fit_space(vals, [])
        self.assertEqual(fit["baseUnitPx"], 8)
        self.assertTrue(fit["followsScale"])
        self.assertEqual(fit["fitQuality"]["verdict"], "good")
        self.assertEqual(fit["stepsPx"], [8, 16, 24, 32, 64, 96])

    def test_prime_ladder_is_poor_and_honest(self):
        vals = {"a": 7.0, "b": 13.0, "c": 29.0, "d": 41.0, "e": 53.0}
        fit = ns.fit_space(vals, [])
        self.assertFalse(fit["followsScale"])
        self.assertEqual(fit["fitQuality"]["verdict"], "poor")

    def test_outliers_recorded_never_snapped(self):
        vals = {"a": 8.0, "b": 16.0, "c": 24.0, "d": 32.0, "e": 40.0,
                "f": 48.0, "g": 56.0, "h": 64.0, "i": 72.0, "j": 80.0,
                "odd": 18.0}
        fit = ns.fit_space(vals, [])
        self.assertNotIn(18, fit["stepsPx"])
        odd = [o for o in fit["outliers"] if o["name"] == "odd"]
        self.assertEqual(len(odd), 1)
        self.assertEqual(odd[0]["nearestStepPx"], 16)

    def test_section_rhythm_is_subset_of_named_section_inputs(self):
        vals = {"section-pad": 96.0, "section-gap": 64.0, "block": 32.0}
        fit = ns.fit_space(vals, [])
        self.assertEqual(fit["sectionRhythmPx"], [64, 96])


class RealArtifactsTest(unittest.TestCase):
    """The committed artifacts for both brands parse, carry provenance for every
    derived block, and agree with their own honesty ledger."""

    def _load(self, brand):
        p = _ROOT / "runs" / brand / "brand" / "style-scale.yaml"
        self.assertTrue(p.exists(), f"{p} missing — run normalize_scales.py")
        return yaml.safe_load(p.read_text())

    def test_both_brands_artifacts_consistent(self):
        for brand in ("hubspot-v2", "remote"):
            art = self._load(brand)
            self.assertEqual(art["schema"], "style-scale.v1")
            for block in ("type", "space", "radius", "motion"):
                self.assertIn("provenance", art[block] or {},
                              f"{brand}.{block} lacks provenance")
            space = art["space"]
            unit = space["baseUnitPx"]
            for s in space["stepsPx"]:
                self.assertAlmostEqual(s % unit, 0, delta=0.02 * unit,
                                       msg=f"{brand} step {s} off unit {unit}")
            for r in space["sectionRhythmPx"]:
                self.assertIn(r, space["stepsPx"])


# ───────────────────────────── consumption law ────────────────────────────────────

def _fake_scale(space_steps=(8, 16, 24, 32, 64, 96, 128), rhythm=(64, 96, 128),
                type_steps=(16, 20, 25, 31.3), follows=True):
    return {"schema": "style-scale.v1",
            "type": {"followsScale": follows, "stepsPx": list(type_steps),
                     "basePx": 16, "ratio": 1.25},
            "space": {"followsScale": follows, "baseUnitPx": 8,
                      "stepsPx": list(space_steps),
                      "sectionRhythmPx": list(rhythm)}}


class StyleScaleModuleTest(unittest.TestCase):
    def test_loader_rejects_absent_and_alien_schema(self):
        with tempfile.TemporaryDirectory() as td:
            self.assertIsNone(ss.load_style_scale(Path(td)))
            (Path(td) / "style-scale.yaml").write_text("schema: other.v9\n")
            self.assertIsNone(ss.load_style_scale(Path(td)))
        self.assertIsNone(ss.load_style_scale(None))

    def test_poor_fit_is_not_consumed(self):
        scale = _fake_scale(follows=False)
        self.assertEqual(ss.space_steps_px(scale), [])
        self.assertEqual(ss.type_steps_px(scale), [])
        self.assertEqual(ss.section_rhythm_px(scale), [])

    def test_nearest_step_directional(self):
        steps = [64.0, 96.0, 128.0]
        self.assertEqual(ss.nearest_step_px(steps, 80, direction=1), 96.0)
        self.assertEqual(ss.nearest_step_px(steps, 80, direction=-1), 64.0)
        self.assertEqual(ss.nearest_step_px(steps, 130, direction=1), None)
        self.assertEqual(ss.nearest_step_px(steps, 80), 64.0)


class BandHeightDerivedTest(unittest.TestCase):
    """The bandHeight knob's derived degrade: fires ONLY when no measured rung
    binds AND the doc carries a usable scale; measured facts always win; docs
    without the artifact keep the historical '' byte-identically."""

    def _doc(self, with_scale=True, with_rung=False):
        doc = {"meta": {"canonicalTier": 1440},
               "tokens": {"spacing": {
                   "section-pad": {"value": "5rem", "role": "section rhythm"}}}}
        if with_rung:
            # a measured rung ABOVE the resolved pad — the tall direction binds
            doc["tokens"]["spacing"]["section-pad-tall"] = {
                "value": "8rem", "role": "section rhythm"}
        if with_scale:
            doc["_styleScale"] = _fake_scale()
        return doc

    def _layout(self):
        return {"_bandHeight": "tall"}

    def test_no_scale_keeps_historical_empty_css(self):
        doc = self._doc(with_scale=False)
        self.assertEqual(
            cs.band_height_rung(doc, self._layout(), "surface/primary", {}), "")
        self.assertEqual(
            cs.band_height_css(doc, self._layout(), "#s", "surface/primary", {}),
            "")

    def test_scale_fills_the_unanswered_knob(self):
        doc = self._doc(with_scale=True)
        self.assertEqual(
            cs.band_height_rung(doc, self._layout(), "surface/primary", {}), "")
        px = cs.band_height_derived_px(doc, self._layout(), "surface/primary", {})
        self.assertIsNotNone(px)
        # the CONTRACT: nearest derived rhythm step strictly beyond the resolved
        # standard pad in the knob's direction (fixture rhythm 6.25rem=100px →
        # tall lands on the 128 step of the fake scale)
        import re as _re
        m = _re.fullmatch(r"([\d.]+)rem",
                          cs.rhythm_for(doc, {}, "surface/primary")["pad_top"])
        base = float(m.group(1)) * 16.0
        self.assertEqual(px, ss.nearest_step_px(
            ss.section_rhythm_px(doc["_styleScale"]), base, direction=1))
        css = cs.band_height_css(doc, self._layout(), "#s", "surface/primary", {})
        self.assertIn(f"{px:g}px", css)
        self.assertIn("DERIVED", css)

    def test_measured_rung_always_wins(self):
        doc = self._doc(with_scale=True, with_rung=True)
        self.assertEqual(
            cs.band_height_rung(doc, self._layout(), "surface/primary", {}),
            "section-pad-tall")
        self.assertIsNone(
            cs.band_height_derived_px(doc, self._layout(), "surface/primary", {}))
        css = cs.band_height_css(doc, self._layout(), "#s", "surface/primary", {})
        self.assertIn("rung", css)
        self.assertNotIn("DERIVED", css)


class ReplicaNeverLoadsScaleTest(unittest.TestCase):
    """Byte-identity pin: the replica assembler has NO code path that reads
    style-scale.yaml — grep-level proof, stronger than a render diff because it
    holds for every brand, not one fixture."""

    def test_compose_replica_source_never_references_artifact(self):
        src = (_BRAND_PIPELINE / "compose_replica.py").read_text()
        self.assertNotIn("style_scale", src)
        self.assertNotIn("style-scale", src)
        self.assertNotIn("_styleScale", src)

    def test_generative_builder_is_the_only_loader(self):
        src = (_BRAND_PIPELINE / "compose_from_composition.py").read_text()
        self.assertIn("load_style_scale", src)


# ───────────────────────────── scale_adherence gate ────────────────────────────────

class GenerativeLaneMarkerTest(unittest.TestCase):
    def test_composition_v1_marks_generative(self):
        with tempfile.TemporaryDirectory() as td:
            lane = Path(td)
            (lane / "composition.json").write_text(
                json.dumps({"schemaVersion": "composition.v1"}))
            self.assertTrue(sa._is_generative_lane(lane))

    def test_replica_composition_exempt(self):
        with tempfile.TemporaryDirectory() as td:
            lane = Path(td)
            (lane / "composition.json").write_text(
                json.dumps({"schemaVersion": "replica-composition.v1"}))
            self.assertFalse(sa._is_generative_lane(lane))

    def test_briefed_legacy_composition_is_generative(self):
        # event-genlaunch shape: replica-composition.v1 schema BUT briefed —
        # a novel generated page, not the assembler's source-order rebuild
        with tempfile.TemporaryDirectory() as td:
            lane = Path(td)
            (lane / "composition.json").write_text(
                json.dumps({"schemaVersion": "replica-composition.v1",
                            "brief": "launch-day event page"}))
            self.assertTrue(sa._is_generative_lane(lane))

    def test_markerless_lane_exempt(self):
        with tempfile.TemporaryDirectory() as td:
            self.assertFalse(sa._is_generative_lane(Path(td)))


class ClassifyScaleTest(unittest.TestCase):
    SCALE = _fake_scale()

    def test_synthetic_off_scale_type_fails(self):
        # 49.6px: not a measured fact (48 nearest) and not a derived step —
        # the exact real finding the gate caught on the product hero.
        samples = [{"px": 49.6, "cls": "c-heading--display", "sec": "sec-0",
                    "layout": "hero"}]
        out = sa.classify_scale(samples, [], [16.0, 48.0], self.SCALE)
        self.assertEqual(out["hardFails"], 1)
        self.assertEqual(out["cells"][0]["verdict"], "off-scale")

    def test_measured_fact_always_wins(self):
        samples = [{"px": 48.0, "cls": "c-heading", "sec": "sec-0", "layout": "x"}]
        out = sa.classify_scale(samples, [], [48.0], self.SCALE)
        self.assertEqual(out["cells"][0]["verdict"], "measured")
        self.assertEqual(out["hardFails"], 0)

    def test_derived_step_passes_novel_geometry(self):
        samples = [{"px": 25.0, "cls": "c-heading", "sec": "sec-1", "layout": "x"}]
        out = sa.classify_scale(samples, [], [16.0], self.SCALE)
        self.assertEqual(out["cells"][0]["verdict"], "on-scale")

    def test_unmapped_space_rides_space_steps(self):
        space = [{"rel": "stack.gap", "severity": "unmapped", "measured": 24.0,
                  "sec": "sec-2", "layout": "x"},
                 {"rel": "stack.gap", "severity": "unmapped", "measured": 27.0,
                  "sec": "sec-2", "layout": "x"}]
        out = sa.classify_scale([], space, [], self.SCALE)
        verdicts = [c["verdict"] for c in out["cells"]]
        self.assertEqual(verdicts, ["on-scale", "off-scale"])

    def test_chrome_space_rels_excluded(self):
        space = [{"rel": "footer.pad-top", "severity": "unmapped",
                  "measured": 27.0, "sec": None, "layout": None}]
        out = sa.classify_scale([], space, [], self.SCALE)
        self.assertEqual(out["cells"], [])

    def test_mapped_space_never_double_audited(self):
        space = [{"rel": "stack.gap", "severity": "conform", "measured": 27.0,
                  "sec": "sec-2", "layout": "x"}]
        out = sa.classify_scale([], space, [], self.SCALE)
        self.assertEqual(out["cells"], [])


class DerivedBandRungAuditTest(unittest.TestCase):
    """A composed page stamping data-band-rung="derived:<px>" audits its pad
    against that deliberate declaration (same hard gate as a token rung)."""

    def _classify(self, band_rung, measured):
        with tempfile.TemporaryDirectory() as td:
            brand = Path(td) / "brand"
            (brand / "evidence").mkdir(parents=True)
            (brand / "brand.yaml").write_text(
                "meta: {canonicalTier: 1440}\n"
                "tokens:\n  spacing:\n    section-pad: {value: 5rem}\n")
            (brand / "evidence" / "css-rules.json").write_text('{"rules": []}')
            book = sa.load_brand_facts(brand, viewport_w=1440)
        meas = {"rel": "section.pad-top", "value": measured, "sec": "sec-0",
                "layout": "hero", "pattern": None, "a": "a", "b": "b",
                "rect": None, "note": "", "kind": "gap", "bandRung": band_rung}
        return sa.classify_measurement(meas, book)

    def test_derived_stamp_conforms_at_step(self):
        out = self._classify("derived:96", 96.0)
        self.assertEqual(out["severity"], "conform")

    def test_derived_stamp_fails_off_step(self):
        out = self._classify("derived:96", 80.0)
        self.assertIn(out["severity"], ("wrong-step", "off-ladder", "drift"))


# ───────────────────────────── C24 validator advisory ──────────────────────────────

class C24AdvisoryTest(unittest.TestCase):
    def _run(self, artifact: dict | None) -> list[str]:
        with tempfile.TemporaryDirectory() as td:
            brand = Path(td)
            (brand / "brand.yaml").write_text("meta: {canonicalTier: 1440}\n")
            if artifact is not None:
                import hashlib
                artifact.setdefault("sourceDigest", "sha256:" + hashlib.sha256(
                    (brand / "brand.yaml").read_bytes()).hexdigest()[:12])
                (brand / "style-scale.yaml").write_text(
                    yaml.safe_dump(artifact, sort_keys=False))
            rep = Report(brand)
            vbe._check_style_scale(rep, brand)
            return [w for w in rep.warnings if w.startswith("C24")]

    def test_consistent_artifact_passes(self):
        art = {"schema": "style-scale.v1",
               "type": {"basePx": 16, "ratio": 1.25, "followsScale": True,
                        "stepsPx": [16, 20, 25],
                        "fitQuality": {"rmse": 0.01, "worstErrPct": 1.0},
                        "fits": [{"errPct": 1.0}]},
               "space": {"baseUnitPx": 8, "followsScale": True,
                         "stepsPx": [8, 16, 96], "sectionRhythmPx": [96],
                         "fitQuality": {"coverage": 1.0}}}
        self.assertEqual(self._run(art), [])

    def test_off_base_steps_warn(self):
        art = {"schema": "style-scale.v1",
               "space": {"baseUnitPx": 8, "followsScale": True,
                         "stepsPx": [8, 18], "sectionRhythmPx": [],
                         "fitQuality": {"coverage": 1.0}}}
        self.assertTrue(any("not multiples" in w for w in self._run(art)))

    def test_stray_rhythm_warns(self):
        art = {"schema": "style-scale.v1",
               "space": {"baseUnitPx": 8, "followsScale": True,
                         "stepsPx": [8, 16], "sectionRhythmPx": [96],
                         "fitQuality": {"coverage": 1.0}}}
        self.assertTrue(any("sectionRhythmPx" in w for w in self._run(art)))

    def test_poor_fit_claiming_scale_warns(self):
        art = {"schema": "style-scale.v1",
               "type": {"basePx": 16, "ratio": 1.25, "followsScale": True,
                        "stepsPx": [16],
                        "fitQuality": {"rmse": 0.09, "worstErrPct": 9.0},
                        "fits": [{"errPct": 9.0}]}}
        self.assertTrue(any("rmse" in w for w in self._run(art)))

    def test_stale_digest_warns(self):
        art = {"schema": "style-scale.v1", "sourceDigest": "sha256:deadbeef0000"}
        self.assertTrue(any("STALE" in w for w in self._run(art)))

    def test_absent_artifact_is_a_note_not_warning(self):
        self.assertEqual(self._run(None), [])


if __name__ == "__main__":
    unittest.main()
