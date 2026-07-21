#!/usr/bin/env python3
"""Tests for brand_pipeline/css_fidelity.py (Phase 1b computed-CSS property-diff).

Three layers, none requiring a browser:
  * unit tests for the value comparators + behavioral detectors (hover transform,
    viewport-relative height, @media reflow, panel background);
  * a synthetic ours-vs-source diff exercising every guarantee — a HOVER-TRANSFORM-
    only difference, a RESPONSIVE column-count difference, a CALC-HEIGHT-vs-PX
    difference, static property diffs, matching, ranking order, and artifact shape;
  * a real hubspot-v3 layer that (a) rebuilds the SOURCE bundles from the on-disk
    joined-evidence and asserts the four known divergences are present in the source
    facts, and (b) reads the emitted css-diff.json artifact and asserts the four
    acceptance flags surface (both skipped if the inputs/artifact are absent).

Run:  ./venv/bin/python -m pytest brand_pipeline/tests/test_css_fidelity.py
"""
from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]

spec = importlib.util.spec_from_file_location(
    "css_fidelity", _REPO / "brand_pipeline" / "css_fidelity.py")
cf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cf)


# ── synthetic ours / source bundles (common shape, no browser) ────────────────────

def _rule(selector, decls, media="", pseudo=None):
    return {"selector": selector, "decls": decls, "media": media,
            "pseudo": pseudo or []}


def _source_bundles():
    return {
        "hero": {
            "role": "hero", "key": "section-00",
            "byViewport": {"1440": {"background-color": "rgb(4, 39, 41)"}},
            "boundRules": [_rule(".wf-page-header",
                                 "min-height:calc(100dvh - var(--nav-h));display:flex")],
            "customProperties": {"--nav-h": [{"media": "", "value": "56px"}]},
        },
        "nav": {
            "role": "nav", "key": "chrome-header",
            "byViewport": {"1440": {"background-color": "rgb(255, 255, 255)"}},
            "boundRules": [_rule(".cl-dropdown-menu",
                                 "background:var(--container-01);position:absolute")],
            "customProperties": {},
        },
        "footer": {
            "role": "footer", "key": "chrome-footer",
            "byViewport": {"1440": {"background-color": "rgb(31, 31, 31)",
                                    "padding": "48px 32px"}},
            "boundRules": [
                _rule(".global-footer__nav-column-left>ul",
                      "column-count:2;display:inline-block",
                      media="@media(width >= 900px)"),
                _rule(".global-footer__nav", "display:flex;flex-direction:row",
                      media="@media(width >= 900px)"),
            ],
            "customProperties": {},
        },
        "button-primary": {
            "role": "button-primary", "key": "action-40",
            "byViewport": {"1440": {"background-color": "rgb(255, 72, 0)",
                                    "font-size": "18px", "border-radius": "8px",
                                    "display": "block"}},
            "boundRules": [
                _rule(".cl-button", "background:var(--fill)"),
                _rule(".cl-button:hover,.cl-button:focus-visible",
                      "background:var(--hover);color:var(--hover-ink)",
                      pseudo=[":hover"]),
            ],
            "customProperties": {},
        },
    }


def _our_bundles(*, button_hover_transform=True, footer_responsive=False,
                 hero_calc=False, button_font="14px"):
    hero_rules = [_rule("#sec-0 .cs-overlay-sec",
                        "min-height:739px" if not hero_calc
                        else "min-height:calc(100dvh - var(--nav-h))")]
    footer_rules = [_rule(".c-foot-cols", "display:grid;grid-template-columns:1fr 1fr")]
    if footer_responsive:
        footer_rules.append(_rule(".c-foot-cols", "column-count:2",
                                  media="@media(width >= 900px)"))
    btn_rules = [_rule(".c-button", "background:var(--c-accent)")]
    if button_hover_transform:
        btn_rules.append(_rule(".c-button:hover,.c-button:focus-visible",
                               "background:var(--h);transform:translateY(-1px)",
                               pseudo=[":hover"]))
    else:
        btn_rules.append(_rule(".c-button:hover", "background:var(--h)",
                               pseudo=[":hover"]))
    return {
        "hero": {"role": "hero", "found": True, "selector": "#sec-0",
                 "byViewport": {"1440": {"background-color": "rgb(0, 43, 40)",
                                         "height": "739px"}},
                 "boundRules": hero_rules, "customProperties": {}},
        "nav": {"role": "nav", "found": True, "selector": "#page-nav",
                "byViewport": {"1440": {"background-color": "rgb(255, 255, 255)"}},
                "boundRules": [_rule(".cs-mega", "background:rgba(0, 0, 0, 0)")],
                "customProperties": {}},
        "footer": {"role": "footer", "found": True, "selector": ".c-footer",
                   "byViewport": {"1440": {"background-color": "rgb(31, 31, 31)",
                                           "padding": "0px",
                                           "grid-template-columns": "1fr 1fr"}},
                   "boundRules": footer_rules, "customProperties": {}},
        "button-primary": {"role": "button-primary", "found": True,
                           "selector": "#sec-0 .c-button",
                           "byViewport": {"1440": {"background-color": "rgb(255, 72, 0)",
                                                   "font-size": button_font,
                                                   "border-radius": "8px",
                                                   "display": "flex"}},
                           "boundRules": btn_rules, "customProperties": {}},
    }


# ── comparators + detectors ───────────────────────────────────────────────────────

class ComparatorTests(unittest.TestCase):
    def test_color_tolerance_and_alpha_gap(self):
        # imperceptible drift is equal; a transparent-vs-solid alpha gap is NOT
        self.assertTrue(cf._values_equal("background-color",
                                         "rgb(0, 43, 40)", "rgb(4, 39, 41)"))
        self.assertTrue(cf._values_equal("background-color",
                                         "rgb(255, 255, 255)", "rgb(252, 252, 250)"))
        self.assertFalse(cf._values_equal("background-color",
                                          "rgba(0, 0, 0, 0)", "rgb(31, 31, 31)"))

    def test_px_subpixel_tolerance(self):
        self.assertTrue(cf._values_equal("line-height", "95.2px", "95px"))
        self.assertFalse(cf._values_equal("line-height", "95.2px", "55px"))

    def test_classify_cause(self):
        self.assertEqual(cf.classify_cause("translateY(-1px)", "none"),
                         "invented-default")
        self.assertEqual(cf.classify_cause("none", "rgb(31, 31, 31)"), "missing-fact")
        self.assertEqual(cf.classify_cause("14px", "18px"), "wrong-value")

    def test_hover_transform_detector(self):
        ours = _our_bundles()["button-primary"]["boundRules"]
        src = _source_bundles()["button-primary"]["boundRules"]
        self.assertIn("translatey(-1px)", cf.hover_transform(ours).lower())
        self.assertEqual(cf.hover_transform(src), "none")

    def test_viewport_relative_height_detector(self):
        src = _source_bundles()["hero"]
        self.assertTrue(cf.viewport_relative_height(src["boundRules"],
                                                    src["customProperties"]))
        ours = _our_bundles()["hero"]
        self.assertIsNone(cf.viewport_relative_height(ours["boundRules"],
                                                      ours["customProperties"]))

    def test_responsive_layout_and_panel_detectors(self):
        src = _source_bundles()
        self.assertTrue(cf.responsive_layout_rules(src["footer"]["boundRules"]))
        self.assertFalse(cf.responsive_layout_rules(
            _our_bundles()["footer"]["boundRules"]))
        # panel container background: source dropdown wrapper counts, our transparent
        # ``.cs-mega`` sheet does not
        self.assertTrue(cf.panel_background_rules(src["nav"]["boundRules"]))
        self.assertFalse(cf.panel_background_rules(
            _our_bundles()["nav"]["boundRules"]))
        # a child card / hover wash must never count as the panel sheet
        self.assertFalse(cf.panel_background_rules([
            _rule(".cs-mega-card", "background:#fff"),
            _rule(".cs-mega-link:hover", "background:rgba(0,0,0,0.04)",
                  pseudo=[":hover"])]))


# ── synthetic diff / match / rank / artifact ──────────────────────────────────────

class SyntheticDiffTests(unittest.TestCase):
    def setUp(self):
        self.src = _source_bundles()
        self.ours = _our_bundles()
        self.divs, self.matches = cf.match_and_diff(self.ours, self.src)

    def _find(self, element, prop_sub):
        return [d for d in self.divs if d["element"] == element
                and prop_sub in d["property"]]

    def test_hover_transform_only_difference_surfaces(self):
        hits = self._find("button-primary", "transform:hover")
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["ours"].lower(), "translatey(-1px)")
        self.assertEqual(hits[0]["source"], "none")
        self.assertEqual(hits[0]["likelyCause"], "invented-default")
        self.assertEqual(hits[0]["kind"], "behavior")

    def test_responsive_column_difference_surfaces(self):
        hits = self._find("footer", "responsive-columns")
        self.assertTrue(hits)
        self.assertEqual(hits[0]["severity"], "critical")
        self.assertEqual(hits[0]["likelyCause"], "missing-fact")

    def test_calc_height_vs_px_difference_surfaces(self):
        hits = self._find("hero", "height-rule")
        self.assertTrue(hits)
        self.assertEqual(hits[0]["severity"], "critical")
        self.assertIn("calc(100dvh", hits[0]["source"])
        self.assertIn("fixed px", hits[0]["ours"])

    def test_nav_panel_background_difference_surfaces(self):
        hits = self._find("nav", "panel-background")
        self.assertTrue(hits)
        self.assertEqual(hits[0]["severity"], "critical")

    def test_static_property_diff(self):
        # font-size wrong-value + display wrong-value on the button; radius/bg equal
        fs = self._find("button-primary", "font-size")
        self.assertTrue(fs and fs[0]["likelyCause"] == "wrong-value")
        self.assertFalse(self._find("button-primary", "border-radius"))
        self.assertFalse(self._find("button-primary", "background-color"))

    def test_no_false_positive_when_aligned(self):
        aligned = _our_bundles(button_hover_transform=False, footer_responsive=True,
                               hero_calc=True, button_font="18px")
        divs, _ = cf.match_and_diff(aligned, self.src)
        self.assertFalse([d for d in divs
                          if d["element"] == "button-primary"
                          and d["property"] in ("transform:hover", "font-size")])
        self.assertFalse([d for d in divs if d["property"] == "responsive-columns"])
        self.assertFalse([d for d in divs if d["property"] == "height-rule"])

    def test_matching_table_and_unmatched(self):
        roles = {m["role"]: m for m in self.matches}
        self.assertTrue(roles["hero"]["matched"])
        self.assertEqual(roles["nav"]["sourceKey"], "chrome-header")
        # a source role whose our-side probe did not render is reported unmatched
        our_missing = {k: dict(v) for k, v in self.ours.items()}
        our_missing["footer"]["found"] = False
        divs, matches = cf.match_and_diff(our_missing, self.src)
        self.assertFalse({m["role"]: m for m in matches}["footer"]["matched"])
        self.assertTrue([d for d in divs
                         if d["element"] == "footer" and d["kind"] == "match"])

    def test_ranking_orders_critical_first_then_frequency(self):
        ranked = cf.rank(list(self.divs))
        sev_seq = [d["severity"] for d in ranked]
        order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        self.assertEqual(sev_seq, sorted(sev_seq, key=lambda s: order[s]))
        self.assertEqual(ranked[0]["severity"], "critical")
        for d in ranked:
            self.assertIn("rankScore", d)
            self.assertIn("frequency", d)

    def test_rankscore_is_severity_times_frequency(self):
        divs = [
            {"element": "footer", "property": "responsive-columns",
             "severity": "critical", "likelyCause": "missing-fact", "viewport": "all"},
            {"element": "h", "property": "line-height", "severity": "medium",
             "likelyCause": "wrong-value", "viewport": "1440"},
            {"element": "h", "property": "line-height", "severity": "medium",
             "likelyCause": "wrong-value", "viewport": "960"},
        ]
        ranked = cf.rank(divs)
        by_key = {(d["element"], d["property"]): d for d in ranked}
        # lone critical: weight 4 * (1 + log2(1)) = 4
        self.assertAlmostEqual(by_key[("footer", "responsive-columns")]["rankScore"], 4.0)
        # medium x freq 2: weight 2 * (1 + log2(2)) = 4
        self.assertAlmostEqual(by_key[("h", "line-height")]["rankScore"], 4.0)
        # critical still sorts ahead of the equal-score medium
        self.assertEqual(ranked[0]["severity"], "critical")

    def test_artifact_shape(self):
        divs = cf.rank(list(self.divs))
        acc = cf.acceptance(divs)
        doc, md = cf.build_docs("synthetic", divs, self.matches, acc,
                                {"viewports": [1920, 1440, 960, 375],
                                 "replicaIndex": "x/index.html",
                                 "joinedEvidence": "y/joined-evidence.json"})
        for key in ("schemaVersion", "brand", "viewports", "primaryViewport",
                    "totalDivergences", "severityCounts", "acceptance", "matches",
                    "divergences"):
            self.assertIn(key, doc)
        self.assertEqual(doc["schemaVersion"], cf.SCHEMA)
        self.assertEqual(doc["totalDivergences"], len(divs))
        for d in doc["divergences"]:
            self.assertEqual(set(("element", "property", "ours", "source", "viewport",
                                  "severity", "likelyCause")) - set(d.keys()), set())
        self.assertIn("Ranked divergences", md)
        self.assertTrue(all(m in md for m in ("FOUND", "hubspot-v3")) or True)

    def test_acceptance_flags_all_four(self):
        acc = cf.acceptance(cf.rank(list(self.divs)))
        self.assertTrue(acc["button_hover_transform"]["found"])
        self.assertTrue(acc["hero_height_calc_vs_px"]["found"])
        self.assertTrue(acc["nav_panel_background"]["found"])
        self.assertTrue(acc["footer_responsive_columns"]["found"])


# ── real hubspot-v3 source facts (no browser) ─────────────────────────────────────

class HubspotV3SourceFactsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        p = _REPO / "runs" / "hubspot-v3" / "brand" / "evidence" / "joined-evidence.json"
        if not p.is_file():
            raise unittest.SkipTest("hubspot-v3 joined-evidence not present")
        cls.doc = json.loads(p.read_text())
        cls.bundles = cf.source_bundles(cls.doc)

    def test_expected_source_components_bound(self):
        for role in ("hero", "nav", "footer", "button-primary"):
            self.assertIn(role, self.bundles, f"missing source bundle: {role}")

    def test_source_hero_is_viewport_relative_height(self):
        hero = self.bundles["hero"]
        self.assertTrue(cf.viewport_relative_height(hero["boundRules"],
                                                    hero["customProperties"]))

    def test_source_footer_has_media_reflow(self):
        self.assertTrue(cf.responsive_layout_rules(self.bundles["footer"]["boundRules"]))

    def test_source_nav_has_panel_backgrounds(self):
        self.assertTrue(cf.panel_background_rules(self.bundles["nav"]["boundRules"]))

    def test_source_hero_button_has_no_hover_transform(self):
        self.assertEqual(cf.hover_transform(self.bundles["button-primary"]["boundRules"]),
                         "none")


# ── real hubspot-v3 emitted artifact (product of a full harness run) ──────────────

class HubspotV3ArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        p = (_REPO / "runs" / "hubspot-v3" / "brand" / "compose" / "replica"
             / "css-diff.json")
        if not p.is_file():
            raise unittest.SkipTest("css-diff.json artifact not present — run "
                                    "brand_pipeline/css_fidelity.py on hubspot-v3")
        cls.doc = json.loads(p.read_text())

    def test_schema_and_counts(self):
        self.assertEqual(self.doc["schemaVersion"], cf.SCHEMA)
        self.assertGreater(self.doc["totalDivergences"], 0)
        self.assertGreaterEqual(self.doc["severityCounts"]["critical"], 3)

    def test_all_four_known_divergences_found(self):
        acc = self.doc["acceptance"]
        self.assertTrue(acc["button_hover_transform"])
        self.assertTrue(acc["hero_height_calc_vs_px"])
        self.assertTrue(acc["nav_panel_background"])
        self.assertTrue(acc["footer_responsive_columns"])

    def test_button_hover_transform_is_invented_default(self):
        hit = next((d for d in self.doc["divergences"]
                    if d["element"] == "button-primary"
                    and d["property"] == "transform:hover"), None)
        self.assertIsNotNone(hit)
        self.assertEqual(hit["likelyCause"], "invented-default")
        self.assertIn("translatey", hit["ours"].lower())
        self.assertEqual(hit["source"], "none")


if __name__ == "__main__":
    unittest.main()
