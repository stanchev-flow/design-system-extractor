#!/usr/bin/env python3
"""Tests for the CSS-VARIABLE-FIRST type-scale extraction + heading-tier audit.

Covers:
  * tools/extract/type_scale.py — collecting ``--*font-size*`` custom properties,
    resolving ``var()`` alias chains + rem→px, evaluating ``@media`` responsive
    overrides, STRICT heading-tag binding (the mis-bind that collapsed the scale),
    namespace-scoped body/small/micro selection, and the computed-cluster fallback
    for brands with no font-size tokens.
  * brand_pipeline/css_fidelity.py — the heading-tier audit that diffs an authored
    scale against the CSS-var truth (catches the h2=18px collapse by construction).
  * the re-authored hubspot-v3 brand.yaml tier acceptance (h2 == 40px, not 18px).

Run:  ./venv/bin/python -m pytest brand_pipeline/tests/test_type_scale.py
"""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]


def _load(mod_name: str, rel: str):
    spec = importlib.util.spec_from_file_location(mod_name, _REPO / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


ts = _load("type_scale", "tools/extract/type_scale.py")
cf = _load("css_fidelity_mod", "brand_pipeline/css_fidelity.py")


# A synthetic design-system stylesheet in css-rules.json shape. It encodes the exact
# trap that collapsed the real scale: a bare-tag `h2` tier rule (40px) AND an instance
# override whose class merely CONTAINS a heading token (`.cta.-h2-on-mobile`, 18px).
def _mk_rules() -> list[dict]:
    root = ("--ds-font-size-h1:2.5rem;--ds-font-size-h2:2rem;--ds-font-size-h3:1.5rem;"
            "--ds-font-size-medium:1rem;--ds-font-size-small:0.875rem;"
            "--ds-font-size-micro:0.75rem;"
            "--ds-line-height-h1:1.15;--ds-line-height-h2:1.1;--ds-line-height-h3:1.42;"
            "--ds-font-weight-h1:600;--ds-font-weight-h2:600;--ds-font-weight-h3:500;"
            "--ds-font-family-heading:'Fancy Serif', serif;"
            "--ds-font-family:'Plain Sans', sans-serif;"
            "--ds-text-font-size:var(--ds-font-size-medium)")
    root_desktop = "--ds-font-size-h1:3rem;--ds-font-size-h2:2.5rem"
    return [
        {"kind": "rule", "media": "", "selector": ":root", "decls": root},
        # desktop overrides (mobile-first base + min-width bump)
        {"kind": "rule", "media": "@media(min-width:900px)", "selector": ":root",
         "decls": root_desktop},
        # semantic tier selectors (bare tag + sole utility class)
        {"kind": "rule", "media": "", "selector": "h1,.h1",
         "decls": "font-family:var(--ds-font-family-heading);font-size:var(--ds-font-size-h1);"
                  "line-height:var(--ds-line-height-h1);font-weight:var(--ds-font-weight-h1)"},
        {"kind": "rule", "media": "", "selector": "h2,.h2",
         "decls": "font-family:var(--ds-font-family-heading);font-size:var(--ds-font-size-h2);"
                  "line-height:var(--ds-line-height-h2);font-weight:var(--ds-font-weight-h2)"},
        {"kind": "rule", "media": "", "selector": "h3,.h3",
         "decls": "font-family:var(--ds-font-family);font-size:var(--ds-font-size-h3);"
                  "line-height:var(--ds-line-height-h3);font-weight:var(--ds-font-weight-h3)"},
        # the TRAP: a control mislabelled with a heading-ish class among others (18px).
        # A loose substring match would bind h2 -> 1.125rem here and collapse the scale.
        {"kind": "rule", "media": "", "selector": ".cta-button.-h2-on-mobile",
         "decls": "font-size:var(--ds-font-size-control)"},
        {"kind": "rule", "media": "", "selector": ":root",
         "decls": "--ds-font-size-control:1.125rem"},
        # body / small consumers
        {"kind": "rule", "media": "", "selector": "body,p",
         "decls": "font-family:var(--ds-font-family);font-size:var(--ds-text-font-size)"},
        {"kind": "rule", "media": "", "selector": ".caption",
         "decls": "font-size:var(--ds-font-size-small)"},
    ]


def _write_evidence(rules: list[dict], computed: dict | None = None) -> Path:
    d = Path(tempfile.mkdtemp())
    (d / "css-rules.json").write_text(json.dumps(
        {"schemaVersion": "css-mine.v1", "rules": rules}))
    if computed is not None:
        (d / "computed-styles.json").write_text(json.dumps(computed))
    return d


class TestCssVarExtraction(unittest.TestCase):
    def setUp(self):
        self.ev = _write_evidence(_mk_rules())
        self.doc = ts.extract(self.ev)
        self.roles = self.doc["canonicalRoles"]

    def test_method_is_css_var(self):
        self.assertEqual(self.doc["method"], "css-var")
        self.assertGreater(self.doc["fontSizeTokenCount"], 0)

    def test_heading_sizes_from_desktop_override(self):
        # canonical tier (1440) resolves the min-width:900 desktop values, not the
        # mobile-first base — h1=48, h2=40, h3=24.
        self.assertAlmostEqual(self.roles["h1"]["sizePx"], 48.0)
        self.assertAlmostEqual(self.roles["h2"]["sizePx"], 40.0)
        self.assertAlmostEqual(self.roles["h3"]["sizePx"], 24.0)

    def test_strict_heading_binding_ignores_instance_override(self):
        # the .cta-button.-h2-on-mobile (18px) must NOT capture the h2 tier.
        self.assertNotAlmostEqual(self.roles["h2"]["sizePx"], 18.0)
        self.assertEqual(self.roles["h2"]["token"], "--ds-font-size-h2")

    def test_responsive_ladder(self):
        # h2 shrinks below the 900px breakpoint (40 -> 32).
        self.assertTrue(self.roles["h2"]["responsive"])
        self.assertAlmostEqual(self.roles["h2"]["tiers"]["w375"]["px"], 32.0)
        self.assertFalse(self.roles["h3"]["responsive"])

    def test_family_serif_vs_sans(self):
        self.assertEqual(self.roles["h1"]["familyClass"], "serif")
        self.assertEqual(self.roles["h2"]["familyClass"], "serif")
        self.assertEqual(self.roles["h3"]["familyClass"], "sans")

    def test_line_height_and_weight_suffix_match(self):
        self.assertAlmostEqual(float(self.roles["h2"]["lineHeight"]), 1.1)
        self.assertEqual(self.roles["h1"]["weight"], 600)

    def test_body_and_small_namespace_scoped(self):
        self.assertAlmostEqual(self.roles["body"]["sizePx"], 16.0)
        self.assertAlmostEqual(self.roles["small"]["sizePx"], 14.0)
        self.assertAlmostEqual(self.roles["micro"]["sizePx"], 12.0)


class TestComputedClusterFallback(unittest.TestCase):
    def test_fallback_when_no_font_size_tokens(self):
        # a stylesheet with NO --*font-size* custom properties → cluster computed sizes
        rules = [{"kind": "rule", "media": "", "selector": "h1",
                  "decls": "color:#000"}]
        computed = {"headings": {
            "h1": {"font-size": "48px"}, "h2": {"font-size": "40px"},
            "h3": {"font-size": "24px"}}}
        ev = _write_evidence(rules, computed)
        doc = ts.extract(ev)
        self.assertEqual(doc["method"], "computed-cluster")
        sizes = sorted({t["sizePx"] for t in doc["tokens"]}, reverse=True)
        self.assertEqual(sizes, [48.0, 40.0, 24.0])


class TestHeadingTierAudit(unittest.TestCase):
    def setUp(self):
        self.truth = ts.extract(_write_evidence(_mk_rules()))

    def test_collapsed_scale_flagged(self):
        collapsed = {
            "h1": {"tiers": {"w1440": {"px": 80}}},
            "h2": {"sizeRem": {"base": 1.125}, "lineHeight": "1.56"},  # 18px
            "h3": {"sizeRem": {"base": 1}},  # 16px
        }
        divs = cf.heading_tier_divergences(collapsed, self.truth)
        h2 = [d for d in divs if d["element"] == "heading-h2"
              and d["property"] == "font-size"]
        self.assertTrue(h2, "collapsed h2 must be flagged")
        self.assertEqual(_norm := cf._norm(h2[0]["source"]), "40.0px")
        self.assertEqual(h2[0]["severity"], "high")

    def test_correct_scale_has_zero_divergences(self):
        correct = {
            "h1": {"sizeRem": {"base": 3}, "lineHeight": "1.15"},
            "h2": {"sizeRem": {"base": 2.5}, "lineHeight": "1.1"},
            "h3": {"sizeRem": {"base": 1.5}, "lineHeight": "1.42"},
            "body": {"sizeRem": {"base": 1}},
            "small": {"sizeRem": {"base": 0.875}},
            "micro": {"sizeRem": {"base": 0.75}},
        }
        divs = cf.heading_tier_divergences(correct, self.truth)
        sizes = [d for d in divs if d["property"] == "font-size"]
        self.assertEqual(sizes, [], f"unexpected size divergences: {sizes}")


class TestHubspotV3TierAcceptance(unittest.TestCase):
    """The re-authored v3 scale: h2 is the 40px section register, NOT the 18px CTA."""
    V3 = _REPO / "runs" / "hubspot-v3" / "brand" / "brand.yaml"

    def setUp(self):
        if not self.V3.is_file():
            self.skipTest("hubspot-v3 brand.yaml absent")
        import yaml
        self.type = (yaml.safe_load(self.V3.read_text())["tokens"]["type"])

    def _px(self, role):
        return cf._authored_tier_px(self.type[role])

    def test_h2_is_forty_not_eighteen(self):
        self.assertAlmostEqual(self._px("h2"), 40.0)
        self.assertNotAlmostEqual(self._px("h2"), 18.0)

    def test_full_ladder_descends(self):
        self.assertAlmostEqual(self._px("h1"), 48.0)
        self.assertAlmostEqual(self._px("h2"), 40.0)
        self.assertAlmostEqual(self._px("h3"), 24.0)
        self.assertAlmostEqual(self._px("h4"), 22.0)
        self.assertAlmostEqual(self._px("h5"), 18.0)
        self.assertAlmostEqual(self._px("h6"), 16.0)
        self.assertAlmostEqual(self._px("body"), 16.0)

    def test_heading_families(self):
        self.assertIn("Serif", self.type["h1"]["family"])
        self.assertIn("Serif", self.type["h2"]["family"])
        self.assertIn("Sans", self.type["h3"]["family"])

    def test_matches_css_var_truth(self):
        truth_p = self.V3.parent / "evidence" / "type-scale.json"
        if not truth_p.is_file():
            self.skipTest("type-scale.json absent")
        truth = json.loads(truth_p.read_text())
        divs = cf.heading_tier_divergences(self.type, truth)
        sizes = [d for d in divs if d["property"] == "font-size"]
        self.assertEqual(sizes, [], f"authored v3 diverges from css-var truth: {sizes}")


if __name__ == "__main__":
    unittest.main()
