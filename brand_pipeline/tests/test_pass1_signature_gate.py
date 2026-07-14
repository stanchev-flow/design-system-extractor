#!/usr/bin/env python3
"""pass1 (2026-07) — signature_check + accent_budget gate tests
(brand_pipeline/signature_audit.py): every per-kind verifier FAILS on a
synthetic bad measurement and PASSES on a clean one, the specimen-lane scope
law, the C25 authorship advisory, and the shape of both brands' authored
signatures. NO Playwright — the browser census is exercised by the lane
battery; verifiers are pure functions over the measurement dict.

Run:  ./venv/bin/python -m unittest brand_pipeline.tests.test_pass1_signature_gate
"""
from __future__ import annotations

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

import signature_audit as sig_a                     # noqa: E402
from validate_brand_evidence import Report          # noqa: E402
import validate_brand_evidence as vbe               # noqa: E402


def _paint(rgb, roles, prop="ink", area=1000.0, label="el", sec="sec-0"):
    return {"rgb": list(rgb), "roles": list(roles), "prop": prop,
            "area": area, "label": label, "sec": sec}


def _measure(paints=(), buttons=(), type_probes=None, sections=(),
             page_area=1_000_000.0):
    return {"paints": list(paints), "buttons": list(buttons),
            "typeProbes": dict(type_probes or {}), "sections": list(sections),
            "pageArea": page_area, "hasSections": True}


ORANGE = (255, 91, 53)


class AccentScopeTest(unittest.TestCase):
    SIG = {"id": "accent-x", "kind": "accent-scope", "mode": "never",
           "check": {"colors": ["#ff5b35"],
                     "allowedRoles": ["action-primary", "arrow-link", "logo-mark"],
                     "forbiddenRoles": ["body-text", "heading"],
                     "maxPaintSharePct": 5.0}}

    def test_accent_on_heading_fails(self):
        m = _measure(paints=[_paint(ORANGE, ["heading"], label="h2")])
        rows = sig_a.check_accent_scope(self.SIG, m)
        bad = [r for r in rows if not r["ok"]]
        self.assertTrue(bad, "forbidden-role accent paint must fail")

    def test_accent_outside_allowed_roles_fails(self):
        m = _measure(paints=[_paint(ORANGE, ["card-surface"], prop="bg")])
        rows = sig_a.check_accent_scope(self.SIG, m)
        stray = next(r for r in rows if r["check"] == "scope(allowed)")
        self.assertFalse(stray["ok"])

    def test_accent_on_primary_action_passes(self):
        m = _measure(paints=[_paint(ORANGE, ["action-primary"], prop="bg",
                                    area=5000)])
        rows = sig_a.check_accent_scope(self.SIG, m)
        self.assertTrue(all(r["ok"] for r in rows))

    def test_budget_breach_fails(self):
        # bg paints count fully: 6% of the page painted accent > 5% budget
        m = _measure(paints=[_paint(ORANGE, ["action-primary"], prop="bg",
                                    area=60_000)],
                     page_area=1_000_000)
        rows = sig_a.check_accent_scope(self.SIG, m)
        budget = next(r for r in rows if r["check"] == "accent_budget")
        self.assertFalse(budget["ok"])
        self.assertGreater(budget["sharePct"], budget["budgetPct"])

    def test_near_family_tolerance_catches_shifted_hue(self):
        m = _measure(paints=[_paint((250, 96, 60), ["heading"])])  # ~Δ12 off
        rows = sig_a.check_accent_scope(self.SIG, m)
        forbidden = next(r for r in rows if r["check"] == "scope(forbidden)")
        self.assertFalse(forbidden["ok"])


class ShapeMotifTest(unittest.TestCase):
    def _btn(self, radius, height=48.0, label="btn"):
        return {"radiusPx": radius, "heightPx": height, "label": label}

    def test_radius_family_fails_off_radius(self):
        sig = {"kind": "shape-motif", "check": {"buttons": {"radiusPx": 8}}}
        rows = sig_a.check_shape_motif(sig, _measure(buttons=[self._btn(2.0)]))
        self.assertFalse(rows[0]["ok"])

    def test_radius_family_passes_at_declared(self):
        sig = {"kind": "shape-motif", "check": {"buttons": {"radiusPx": 8}}}
        rows = sig_a.check_shape_motif(sig, _measure(buttons=[self._btn(8.4)]))
        self.assertTrue(rows[0]["ok"])

    def test_pill_family_fails_square_button(self):
        sig = {"kind": "shape-motif", "check": {"buttons": {"pill": True}}}
        rows = sig_a.check_shape_motif(sig, _measure(buttons=[self._btn(6.0)]))
        self.assertFalse(rows[0]["ok"])

    def test_pill_family_passes_pills(self):
        sig = {"kind": "shape-motif", "check": {"buttons": {"pill": True}}}
        rows = sig_a.check_shape_motif(
            sig, _measure(buttons=[self._btn(24.0), self._btn(999.0)]))
        self.assertTrue(all(r["ok"] for r in rows))

    def test_never_pill_fails_a_pill(self):
        sig = {"kind": "shape-motif", "check": {"neverPill": True}}
        rows = sig_a.check_shape_motif(sig, _measure(buttons=[self._btn(24.0)]))
        self.assertFalse(rows[0]["ok"])

    def test_no_buttons_is_vacuous_pass(self):
        sig = {"kind": "shape-motif", "check": {"buttons": {"pill": True}}}
        rows = sig_a.check_shape_motif(sig, _measure())
        self.assertTrue(all(r["ok"] for r in rows))


class TypeTreatmentTest(unittest.TestCase):
    SIG = {"kind": "type-treatment",
           "check": {"probes": [
               {"on": "display", "familyIncludesAny": ["Lexend Deca"],
                "weightMax": 500}]}}

    def _probe(self, family, weight):
        return {"display": [{"family": family, "weight": weight, "label": "h1"}]}

    def test_off_family_fails(self):
        m = _measure(type_probes=self._probe("Georgia, serif", 400))
        rows = sig_a.check_type_treatment(self.SIG, m)
        self.assertFalse(rows[0]["ok"])

    def test_over_weight_fails(self):
        m = _measure(type_probes=self._probe("Lexend Deca, sans", 700))
        rows = sig_a.check_type_treatment(self.SIG, m)
        self.assertFalse(rows[0]["ok"])

    def test_on_family_within_weight_passes(self):
        m = _measure(type_probes=self._probe("'Lexend Deca', sans-serif", 500))
        rows = sig_a.check_type_treatment(self.SIG, m)
        self.assertTrue(rows[0]["ok"])

    def test_unrendered_rank_is_vacuous_pass(self):
        rows = sig_a.check_type_treatment(self.SIG, _measure())
        self.assertTrue(rows[0]["ok"])

    def test_boolean_on_key_still_probes(self):
        # YAML 1.1: an unquoted `on:` parses as boolean True — the auditor
        # accepts both spellings (caught live: every type probe vacuously
        # passed while the key was True).
        sig = {"kind": "type-treatment",
               "check": {"probes": [{True: "display",
                                     "familyIncludesAny": ["Lexend Deca"]}]}}
        m = _measure(type_probes=self._probe("Georgia, serif", 400))
        rows = sig_a.check_type_treatment(sig, m)
        self.assertEqual(rows[0]["check"], "type(display)")
        self.assertFalse(rows[0]["ok"])

    def test_malformed_probe_fails_never_vacuous(self):
        sig = {"kind": "type-treatment",
               "check": {"probes": [{"familyIncludesAny": ["Lexend Deca"]}]}}
        rows = sig_a.check_type_treatment(sig, _measure())
        self.assertFalse(rows[0]["ok"])
        self.assertIn("malformed", rows[0]["detail"])

    def test_both_brands_probe_keys_parse_as_strings(self):
        # the committed brand.yaml files must carry quoted "on" keys — the
        # exact authoring defect that made every probe skip
        for brand in ("hubspot-v2", "remote"):
            doc = yaml.safe_load(
                (_ROOT / "runs" / brand / "brand" / "brand.yaml").read_text())
            for s in (doc.get("signatures") or []):
                for probe in ((s.get("check") or {}).get("probes") or []):
                    self.assertIn("on", probe,
                                  f"{brand}/{s['id']}: probe key parsed as "
                                  f"{sorted(map(repr, probe))}")


class SurfaceHabitTest(unittest.TestCase):
    def _sec(self, rgb, lum, sec_id="sec-1", has_image=False):
        return {"id": sec_id, "layout": "x", "rgb": list(rgb),
                "luminance": lum, "hasImage": has_image}

    def test_unlicensed_dark_family_fails(self):
        sig = {"kind": "surface-habit",
               "check": {"darkAllowedColors": ["#0b3d3b"], "darkMaxLuminance": 0.25}}
        m = _measure(sections=[self._sec((20, 20, 60), 0.02)])  # navy, not teal
        rows = sig_a.check_surface_habit(sig, m)
        self.assertFalse(rows[0]["ok"])

    def test_licensed_dark_family_passes(self):
        sig = {"kind": "surface-habit",
               "check": {"darkAllowedColors": ["#0b3d3b"], "darkMaxLuminance": 0.25}}
        m = _measure(sections=[self._sec((11, 61, 59), 0.04)])
        rows = sig_a.check_surface_habit(sig, m)
        self.assertTrue(rows[0]["ok"])

    def test_light_canvas_cut_fails(self):
        sig = {"kind": "surface-habit", "check": {"sectionMinLuminance": 0.5}}
        m = _measure(sections=[self._sec((30, 30, 30), 0.01)])
        rows = sig_a.check_surface_habit(sig, m)
        self.assertFalse(rows[0]["ok"])

    def test_image_sections_exempt_from_light_canvas(self):
        sig = {"kind": "surface-habit", "check": {"sectionMinLuminance": 0.5}}
        m = _measure(sections=[self._sec((30, 30, 30), 0.01, has_image=True)])
        rows = sig_a.check_surface_habit(sig, m)
        self.assertTrue(rows[0]["ok"])


class SpecimenScopeTest(unittest.TestCase):
    """Page-level claims (accent scope, surface habits) are void on a spec book;
    element-level claims (shape, type) still bind. The scope sets encode that."""

    def test_specimen_kinds_are_element_level_only(self):
        self.assertEqual(sig_a.SPECIMEN_KINDS, {"shape-motif", "type-treatment"})
        self.assertIn("accent-scope", sig_a.KIND_CHECKS)
        self.assertNotIn("accent-scope", sig_a.SPECIMEN_KINDS)
        self.assertNotIn("surface-habit", sig_a.SPECIMEN_KINDS)


class AuthoredSignaturesTest(unittest.TestCase):
    """Both brands' committed signatures: 3-5 discipline, known kinds,
    machine-checkable form, evidence provenance per signature."""

    def _sigs(self, brand):
        doc = yaml.safe_load(
            (_ROOT / "runs" / brand / "brand" / "brand.yaml").read_text())
        return doc.get("signatures") or []

    def test_both_brands_authored_within_discipline(self):
        for brand in ("hubspot-v2", "remote"):
            sigs = self._sigs(brand)
            self.assertTrue(3 <= len(sigs) <= 5,
                            f"{brand}: {len(sigs)} signatures (want 3-5)")
            for s in sigs:
                self.assertIn(s["kind"], vbe._SIGNATURE_KINDS,
                              f"{brand}/{s.get('id')}")
                self.assertIn(s["mode"], ("always", "never"))
                self.assertTrue(s.get("check"), f"{brand}/{s['id']} no check")
                self.assertTrue(s.get("evidence"),
                                f"{brand}/{s['id']} no evidence provenance")

    def test_c25_clean_on_both_brands(self):
        for brand in ("hubspot-v2", "remote"):
            doc = yaml.safe_load(
                (_ROOT / "runs" / brand / "brand" / "brand.yaml").read_text())
            rep = Report(_ROOT / "runs" / brand / "brand")
            vbe._check_signatures(rep, doc)
            self.assertEqual([w for w in rep.warnings if w.startswith("C25")],
                             [], brand)


class C25AdvisoryTest(unittest.TestCase):
    def _warns(self, doc) -> list[str]:
        with tempfile.TemporaryDirectory() as td:
            rep = Report(Path(td))
            vbe._check_signatures(rep, doc)
            return [w for w in rep.warnings if w.startswith("C25")]

    def test_missing_block_warns(self):
        self.assertTrue(self._warns({}))

    def test_rule_dump_warns(self):
        sig = {"id": "x", "kind": "accent-scope", "mode": "never",
               "check": {"colors": ["#fff"]}, "evidence": ["e"]}
        doc = {"signatures": [dict(sig, id=f"s{i}") for i in range(8)]}
        self.assertTrue(any("3-5" in w for w in self._warns(doc)))

    def test_unknown_kind_and_missing_fields_warn(self):
        doc = {"signatures": [
            {"id": "a", "kind": "vibe", "mode": "always",
             "check": {"x": 1}, "evidence": ["e"]},
            {"id": "b", "kind": "accent-scope", "mode": "sometimes",
             "check": {"x": 1}, "evidence": ["e"]},
            {"id": "c", "kind": "accent-scope", "mode": "never",
             "evidence": ["e"]},
            {"id": "d", "kind": "accent-scope", "mode": "never",
             "check": {"x": 1}}]}
        warns = self._warns(doc)
        self.assertTrue(any("'a'" in w and "kind" in w for w in warns))
        self.assertTrue(any("'b'" in w and "mode" in w for w in warns))
        self.assertTrue(any("'c'" in w and "check" in w for w in warns))
        self.assertTrue(any("'d'" in w and "evidence" in w for w in warns))


if __name__ == "__main__":
    unittest.main()
