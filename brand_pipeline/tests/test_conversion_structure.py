"""Enforcement tests for brand_pipeline/conversion_audit.py (stage B of the
quality steals; law: spec/conversion-structure.md, data:
contracts/conversion-structure.yaml).

Covers: the seven-kind constraint interpreter, composition-level family
resolution (familyMap + bySlots), render re-grounding through the section-rules
detector, depth/formDepth bands, the two hardFloor rows (gate from birth), and
fact-gated campaign binding.

Run: ./venv/bin/python -m pytest brand_pipeline/tests/test_conversion_structure.py -q
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

import conversion_audit as ca  # noqa: E402

REPO = HERE.parent
EVENT_LANE = REPO / "runs/remote/brand/compose/event-genlaunch"
MATRIX = REPO / "evals" / "matrix"

CONTRACTS = ca.load_contracts()


def seq(*family_sets) -> list[dict]:
    return [{"id": f"s{i}", "useCase": "", "families": set(fs)}
            for i, fs in enumerate(family_sets)]


def run_row(row: dict, *family_sets) -> tuple[bool, str]:
    return ca.interpret_constraint(row, seq(*family_sets))


class InterpreterKinds(unittest.TestCase):
    def test_opens(self):
        ok, _ = run_row({"kind": "opens", "family": "hero"}, {"hero"}, {"faq"})
        self.assertTrue(ok)
        ok, _ = run_row({"kind": "opens", "family": "hero"}, {"faq"}, {"hero"})
        self.assertFalse(ok)
        ok, detail = ca.interpret_constraint({"kind": "opens",
                                              "family": "hero"}, [])
        self.assertFalse(ok)
        self.assertIn("no content sections", detail)

    def test_closes_any_of(self):
        row = {"kind": "closes", "anyOf": ["cta-band", "capture-form"]}
        self.assertTrue(run_row(row, {"hero"}, {"capture-form"})[0])
        self.assertFalse(run_row(row, {"capture-form"}, {"faq"})[0])

    def test_present_band(self):
        row = {"kind": "present", "family": "capture-form", "min": 1, "max": 2}
        self.assertTrue(run_row(row, {"capture-form"}, {"faq"})[0])
        self.assertFalse(run_row(row, {"faq"})[0])
        self.assertFalse(run_row(row, {"capture-form"}, {"capture-form"},
                                 {"capture-form"})[0])

    def test_present_zero_budget(self):
        row = {"kind": "present", "family": "pricing-tiers", "min": 0, "max": 0}
        self.assertTrue(run_row(row, {"hero"})[0])
        self.assertFalse(run_row(row, {"pricing-tiers"})[0])

    def test_window(self):
        row = {"kind": "window", "family": "capture-form", "firstN": 3}
        self.assertTrue(run_row(row, {"hero"}, {"capture-form"}, {"faq"})[0])
        self.assertFalse(run_row(row, {"hero"}, {"faq"}, {"quote"},
                                 {"capture-form"})[0])
        ok, detail = run_row(row, {"hero"}, {"faq"})
        self.assertFalse(ok, "a window over an absent family is a miss")
        self.assertIn("no section binds", detail)

    def test_after_index(self):
        row = {"kind": "afterIndex", "family": "capture-form", "minIndex": 3}
        self.assertTrue(run_row(row, {"hero"}, {"faq"}, {"capture-form"})[0])
        self.assertFalse(run_row(row, {"hero"}, {"capture-form"})[0])
        self.assertTrue(run_row(row, {"hero"}, {"faq"})[0], "absent = vacuous")

    def test_before(self):
        row = {"kind": "before", "first": "pricing-tiers",
               "then": "capture-form"}
        self.assertTrue(run_row(row, {"pricing-tiers"}, {"capture-form"})[0])
        self.assertFalse(run_row(row, {"capture-form"}, {"pricing-tiers"})[0])
        self.assertTrue(run_row(row, {"pricing-tiers"}, {"faq"})[0],
                        "either side absent = vacuous")

    def test_adjacent(self):
        row = {"kind": "adjacent", "family": "capture-form",
               "toAnyOf": ["quote", "logo-strip"], "maxGap": 1}
        self.assertTrue(run_row(row, {"quote"}, {"capture-form"})[0])
        self.assertFalse(run_row(row, {"quote"}, {"hero"}, {"faq"},
                                 {"capture-form"})[0])
        ok, detail = run_row(row, {"hero"}, {"capture-form"})
        self.assertFalse(ok, "form present with no proof beat anywhere")
        self.assertIn("no", detail)
        self.assertTrue(run_row(row, {"hero"}, {"quote"})[0],
                        "no form = vacuous")


class CompositionFamilies(unittest.TestCase):
    def _families(self, sections):
        comp = {"schemaVersion": "composition.v1", "sections": sections}
        return ca.composition_families(comp, CONTRACTS)

    def test_family_map_projection(self):
        out = self._families([
            {"id": "a", "useCase": "hero", "slots": []},
            {"id": "b", "useCase": "logos", "slots": []},
            {"id": "c", "useCase": "testimonial", "slots": []},
            {"id": "d", "useCase": "pricing", "slots": []},
            {"id": "e", "useCase": "gallery", "slots": []}])
        self.assertEqual([sorted(s["families"]) for s in out],
                         [["hero"], ["logo-strip"], ["quote"],
                          ["pricing-tiers"], ["carousel"]])

    def test_by_slots_form_and_stats(self):
        out = self._families([
            {"id": "s", "useCase": "cta",
             "slots": [{"contract": "form"}]},
            {"id": "t", "useCase": "features",
             "slots": [{"contract": "stat"}, {"contract": "stat"}]},
            {"id": "u", "useCase": "features",
             "slots": [{"contract": "stat"}]}])
        self.assertEqual(sorted(out[0]["families"]),
                         ["capture-form", "cta-band"])
        self.assertEqual(sorted(out[1]["families"]),
                         ["feature-grid", "stat-band"])
        self.assertEqual(sorted(out[2]["families"]), ["feature-grid"],
                         "one stat slot is inline proof, not a band")

    def test_about_binds_grid_only_when_moduled(self):
        moduled = self._families([
            {"id": "a", "useCase": "about",
             "slots": [{"contract": "feature-item"},
                       {"contract": "feature-item"}]}])
        bare = self._families([
            {"id": "a", "useCase": "about",
             "slots": [{"contract": "paragraph"}]}])
        self.assertEqual(sorted(moduled[0]["families"]), ["feature-grid"])
        self.assertEqual(sorted(bare[0]["families"]), [])


def _campaign(cid: str) -> dict:
    c = ca.campaign_by_id(CONTRACTS, cid)
    assert c is not None
    return c


def _check(cid: str, families, form_fields=None) -> dict:
    return ca.check_conversion_structure(
        {"sections": []}, _campaign(cid), families=families,
        form_field_count=form_fields, contracts=CONTRACTS)


class HardFloors(unittest.TestCase):
    def test_capture_form_campaign_without_form_gates(self):
        res = _check("leadgen-gated-content",
                     seq({"hero"}, {"feature-grid"}, {"quote"}, {"cta-band"}))
        self.assertFalse(res["ok"])
        bad = [f for f in res["hardFloor"] if not f["ok"]]
        self.assertEqual(bad[0]["rule"], "hardFloor:conversion-moment")

    def test_capture_form_campaign_with_form_holds(self):
        res = _check("leadgen-gated-content",
                     seq({"hero"}, {"capture-form"}, {"feature-grid"},
                         {"cta-band"}))
        self.assertTrue(res["ok"])

    def test_pricing_form_before_tiers_gates(self):
        res = _check("pricing", seq({"hero"}, {"capture-form"},
                                    {"pricing-tiers"}, {"faq"}))
        self.assertFalse(res["ok"])
        bad = [f for f in res["hardFloor"] if not f["ok"]]
        self.assertEqual(bad[0]["rule"], "hardFloor:never-gate-the-price")

    def test_pricing_form_without_tiers_gates(self):
        res = _check("pricing", seq({"hero"}, {"capture-form"}, {"faq"}))
        self.assertFalse(res["ok"])

    def test_pricing_tiers_then_form_holds(self):
        res = _check("pricing", seq({"hero"}, {"pricing-tiers"}, {"faq"},
                                    {"capture-form"}))
        self.assertTrue(res["ok"])

    def test_cta_campaign_has_no_capture_floor(self):
        res = _check("product-launch",
                     seq({"hero"}, {"feature-grid"}, {"quote"}, {"cta-band"}))
        self.assertTrue(res["ok"])
        self.assertFalse([f for f in res["hardFloor"]
                          if f["rule"] == "hardFloor:conversion-moment"])


class AdvisoryRows(unittest.TestCase):
    def test_buried_form_warns_but_does_not_gate(self):
        """The stress-playbook shape: form present but at the page's end —
        required WINDOW rows warn, only hardFloor gates (advisory-first)."""
        families = seq({"hero"}, {"stat-band"}, {"feature-grid"},
                       {"feature-grid"}, {"cta-band"}, {"quote"},
                       {"logo-strip"}, {"faq"}, {"capture-form", "cta-band"})
        res = _check("leadgen-gated-content", families)
        self.assertTrue(res["ok"], "hardFloor holds: the form exists")
        window = [r for r in res["rows"] if r["kind"] == "window"]
        self.assertTrue(window and not window[0]["ok"])
        self.assertEqual(window[0]["severity"], "required")

    def test_depth_band_row(self):
        res = _check("leadgen-gated-content",
                     seq(*[{"hero"}] + [{"feature-grid"}] * 10
                         + [{"capture-form"}]))
        depth = [r for r in res["rows"] if r["kind"] == "depthBand"]
        self.assertFalse(depth[0]["ok"])
        res2 = _check("leadgen-gated-content",
                      seq({"hero"}, {"capture-form"}, {"feature-grid"},
                          {"cta-band"}))
        depth2 = [r for r in res2["rows"] if r["kind"] == "depthBand"]
        self.assertTrue(depth2[0]["ok"])

    def test_form_depth_band_rows(self):
        families = seq({"hero"}, {"capture-form"}, {"feature-grid"},
                       {"cta-band"})
        deep = _check("leadgen-gated-content", families, form_fields=7)
        row = [r for r in deep["rows"] if r["kind"] == "formDepth"][0]
        self.assertFalse(row["ok"], "7 fields breaks the 2-4 gated-content band")
        shallow = _check("leadgen-gated-content", families, form_fields=3)
        row2 = [r for r in shallow["rows"] if r["kind"] == "formDepth"][0]
        self.assertTrue(row2["ok"])
        unmeasured = _check("leadgen-gated-content", families)
        row3 = [r for r in unmeasured["rows"] if r["kind"] == "formDepth"][0]
        self.assertTrue(row3["ok"], "unmeasured form depth never warns")

    def test_every_row_carries_severity_and_why(self):
        res = _check("webinar-event",
                     seq({"hero"}, {"logo-strip"}, {"faq"}, {"capture-form"}))
        for r in res["rows"]:
            self.assertIn(r["severity"], ("advisory", "required"), r)
            self.assertIn("why", r)


class CampaignBinding(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_brief_frontmatter_binds(self):
        (self.tmp / "copy-brief.md").write_text(
            "---\npageType: event\ncampaignType: webinar-event\n---\n# Brief\n")
        self.assertEqual(ca.lane_campaign_id(self.tmp, {}), "webinar-event")

    def test_composition_brief_key_binds(self):
        comp = {"brief": {"id": "x", "campaignType": "pricing"}}
        self.assertEqual(ca.lane_campaign_id(self.tmp, comp), "pricing")

    def test_unbound_lane_returns_none(self):
        (self.tmp / "copy-brief.md").write_text("# No frontmatter\n")
        self.assertIsNone(ca.lane_campaign_id(self.tmp, {"brief": {"id": "x"}}))

    def test_audit_lane_skips_without_binding(self):
        (self.tmp / "composition.json").write_text(json.dumps(
            {"schemaVersion": "composition.v1", "sections": []}))
        entry = ca.audit_lane(self.tmp, CONTRACTS)
        self.assertIn("fact-gated skip", entry["note"])

    def test_audit_lane_rejects_unknown_campaign(self):
        (self.tmp / "composition.json").write_text(json.dumps(
            {"schemaVersion": "composition.v1", "sections": []}))
        entry = ca.audit_lane(self.tmp, CONTRACTS, "not-a-campaign")
        self.assertIn("unknown campaign", entry["error"])


@unittest.skipUnless(EVENT_LANE.exists(), "event lane not present")
class RealLaneRegrounding(unittest.TestCase):
    """The render re-ground on the real event lane: the closing signup binds
    capture-form + cta-band, the passes section binds pricing-tiers, and the
    full webinar-event grammar holds (hardFloor + required rows green)."""

    def test_rendered_families(self):
        fams = ca.rendered_families(EVENT_LANE, EVENT_LANE / "index.html")
        by_id = {s["id"]: s["families"] for s in fams}
        self.assertIn("capture-form", by_id["event-signup"])
        self.assertIn("cta-band", by_id["event-signup"])
        self.assertIn("pricing-tiers", by_id["event-passes"])
        self.assertIn("hero", by_id["event-hero"])
        self.assertNotIn("closing-bookend", by_id, "footer bookend is chrome")

    def test_event_lane_holds_webinar_grammar(self):
        entry = ca.audit_lane(EVENT_LANE, CONTRACTS, "webinar-event")
        self.assertEqual(entry.get("ground"), "rendered")
        self.assertTrue(entry["ok"], entry.get("hardFloor"))
        req_bad = [r for r in entry["rows"]
                   if r["severity"] == "required" and not r["ok"]]
        self.assertFalse(req_bad, req_bad)


@unittest.skipUnless(MATRIX.exists(), "matrix corpus not present")
class MatrixBriefBinding(unittest.TestCase):
    def test_every_matrix_brief_binds_a_real_campaign(self):
        import archetype_library as al
        for brand in ("hubspot-v2", "remote"):
            for path in sorted((MATRIX / "briefs" / brand).glob("*.md")):
                meta, _ = al.parse_brief_frontmatter(path.read_text())
                campaign = ca.campaign_by_id(CONTRACTS,
                                             str(meta.get("campaignType")))
                self.assertIsNotNone(campaign, path)


if __name__ == "__main__":
    unittest.main()
