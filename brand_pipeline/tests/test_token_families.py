#!/usr/bin/env python3
"""Tests for the CSS-VARIABLE-FIRST spacing / radius / color extraction + the
css_fidelity token-tier audits (the generalization of the proven type-scale pattern).

Covers:
  * tools/extract/token_families.py — collecting ``--*radius*`` / ``--*padding*`` /
    ``--*gap*`` / color custom properties, resolving ``var()`` alias chains + rem→px,
    THEME-AWARE color resolution (default/light wins over a later ``[data-theme=dark]``
    redefinition), STRICT component-name binding (a nested card-descendant selector must
    not capture the card radius — the radius analogue of the collapsed-scale mis-bind),
    generic role classification, and the computed-cluster fallback.
  * brand_pipeline/css_fidelity.py — the spacing / radius / color token-tier audits that
    diff authored brand.yaml tokens against the css-var truth (catch a drifted step /
    corner / surface color by construction).
  * the re-authored hubspot-v3 brand.yaml acceptance (section-4 surface == #fcded2,
    radius.card == 16px, and 0 token-tier divergences vs the on-disk truth).

Run:  ./venv/bin/python -m pytest brand_pipeline/tests/test_token_families.py
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


tf = _load("token_families", "tools/extract/token_families.py")
cf = _load("css_fidelity_tf", "brand_pipeline/css_fidelity.py")


def _write_evidence(rules, computed=None, facts=None, joined=None) -> Path:
    d = Path(tempfile.mkdtemp())
    (d / "css-rules.json").write_text(json.dumps({"schemaVersion": "css-mine.v1",
                                                  "rules": rules}))
    if computed is not None:
        (d / "computed-styles.json").write_text(json.dumps(computed))
    if facts is not None:
        (d / "css-facts.json").write_text(json.dumps(facts))
    if joined is not None:
        (d / "joined-evidence.json").write_text(json.dumps(joined))
    return d


def _rule(selector, decls, media=""):
    return {"kind": "rule", "media": media, "selector": selector, "decls": decls}


# ── RADIUS ───────────────────────────────────────────────────────────────────────

def _radius_rules():
    root = ("--ds-border-radius-small:4px;--ds-border-radius-medium:8px;"
            "--ds-border-radius-container:16px;--ds-border-radius-round:9999px;"
            "--ds-border-radius-input:4px;--ds-border-width-medium:1px;"
            "--ds-border-width-heavy:2px")
    return [
        _rule(":root", root),
        _rule(".ds-button", "border-radius:var(--ds-border-radius-medium)"),
        _rule(".ds-card", "border-radius:var(--ds-border-radius-container)"),
        _rule(".ds-input", "border-radius:var(--ds-border-radius-input)"),
        _rule(".ds-badge", "border-radius:var(--ds-border-radius-round)"),
        # the TRAP: a card DESCENDANT (a checkbox inside a card) uses the small radius.
        # a loose "contains card" match would bind the card radius to 4px; the strict
        # component-name binding must keep the card at its own 16px container radius.
        _rule(".ds-card .ds-checkbox:before",
              "border-radius:var(--ds-border-radius-small)"),
        # another decoy: a text-link whose class merely CONTAINS "card" mid-name.
        _rule(".global-nav-card-cta-text-link",
              "border-radius:var(--ds-border-radius-medium)"),
    ]


class TestRadiusCssVar(unittest.TestCase):
    def setUp(self):
        self.doc = tf.extract_radius(_write_evidence(_radius_rules()))
        self.roles = self.doc["canonicalRoles"]

    def test_method_and_count(self):
        self.assertEqual(self.doc["method"], "css-var")
        self.assertGreaterEqual(self.doc["radiusTokenCount"], 5)

    def test_control_input_card_pill(self):
        self.assertEqual(self.roles["control"]["px"], 8.0)
        self.assertEqual(self.roles["input"]["px"], 4.0)
        self.assertEqual(self.roles["card"]["px"], 16.0)
        self.assertTrue(tf._is_pill(self.roles["pill"]["px"]))

    def test_card_binding_ignores_descendant(self):
        # the card must NOT collapse to the 4px a nested checkbox descendant uses.
        self.assertEqual(self.roles["card"]["token"], "--ds-border-radius-container")
        self.assertNotEqual(self.roles["card"]["px"], 4.0)

    def test_border_widths_resolved(self):
        widths = {w["role"]: w["px"] for w in self.doc["borderWidths"]}
        self.assertEqual(widths.get("medium"), 1.0)
        self.assertEqual(widths.get("heavy"), 2.0)

    def test_computed_cluster_fallback(self):
        # no --*radius* tokens → cluster the border-radius census (corpus-wide).
        rules = [_rule(".x", "border-radius:6px")]
        facts = {"radiusCensus": {"6px": 5, "12px": 2, "50%": 3}}
        doc = tf.extract_radius(_write_evidence(rules, facts=facts))
        self.assertEqual(doc["method"], "computed-cluster")
        pxs = {t["px"] for t in doc["tokens"]}
        self.assertIn(12.0, pxs)
        self.assertTrue(any(tf._is_pill(t["px"]) for t in doc["tokens"]))


# ── SPACING ──────────────────────────────────────────────────────────────────────

def _spacing_rules():
    root = ("--csol-section-padding-top:0px;--csol-section-padding-bottom:0px;"
            "--csol-content-padding-true:1rem;--csol-content-padding-false:0;"
            "--ds-button-padding-small:0.5rem 1rem;"
            "--ds-button-padding-medium:0.75rem 1.5rem;"
            "--ds-button-padding-large:1rem 2.5rem")
    steps = ("--csol-section-padding-top:24px;--csol-section-padding-bottom:40px")
    return [
        _rule(":root", root),
        _rule(".csol-section.-padding-top-md", steps),
        _rule(".csol-section.-padding-bottom-lg", "--csol-section-padding-bottom:64px"),
        _rule(".ds-button.-small", "padding:var(--ds-button-padding-small)"),
        _rule(".ds-button", "padding:var(--ds-button-padding-medium)"),
        _rule(".ds-grid", "gap:1.5rem"),
        _rule(".ds-stack", "gap:1rem;padding-top:2rem"),
        _rule(".ds-wide", "gap:2.5rem"),
    ]


class TestSpacingCssVar(unittest.TestCase):
    def setUp(self):
        self.doc = tf.extract_spacing(_write_evidence(_spacing_rules()))

    def test_section_rhythm_steps(self):
        pxs = sorted(v["px"] for v in self.doc["sectionRhythm"].values())
        # 0 / 24 / 40 / 64 declared across the section padding tokens
        for want in (0.0, 24.0, 40.0, 64.0):
            self.assertIn(want, pxs)

    def test_control_padding_scale(self):
        cp = self.doc["controlPadding"]
        self.assertIn("button-small", cp)
        self.assertIn("button-medium", cp)
        self.assertAlmostEqual(cp["button-medium"]["blockPx"], 12.0)
        self.assertAlmostEqual(cp["button-medium"]["inlinePx"], 24.0)

    def test_step_ladder_is_corpus_cluster(self):
        ladder = {s["px"] for s in self.doc["stepScale"]}
        # gap/padding literals 16/24/32/40 (1/1.5/2/2.5rem) cluster in
        for want in (16.0, 24.0, 32.0, 40.0):
            self.assertIn(want, ladder)
        self.assertTrue(all(s["provenance"]["source"] == "computed-cluster"
                            for s in self.doc["stepScale"]))


# ── COLOR ────────────────────────────────────────────────────────────────────────

def _color_rules():
    # semantic role tokens aliasing a theme layer that carries the hex; the DARK block
    # is declared AFTER the light block (source order) — the light/default must win.
    light = (":root,[data-theme=light],.-light",
             "--c-color-background-01:var(--light-bg-01);"
             "--c-color-container-01:var(--light-container-01);"
             "--c-color-text-01:var(--light-text-01);"
             "--c-color-text-02:var(--light-text-02);"
             "--c-color-border-03:var(--light-border-03);"
             "--c-color-border-brand-01:var(--light-border-brand-01);"
             "--c-color-button-primary-fill-idle:var(--light-btn-idle);"
             "--c-color-button-primary-fill-hover:var(--light-btn-hover)")
    dark = ("[data-theme=dark],.-dark",
            "--c-color-background-01:var(--dark-bg-01);"
            "--c-color-container-01:var(--dark-container-01);"
            "--c-color-text-01:var(--dark-text-01)")
    prims = (":root",
             "--light-bg-01:#fcfcfa;--light-container-01:#ffffff;"
             "--light-text-01:#1f1f1f;--light-text-02:rgba(0,0,0,0.47);"
             "--light-border-03:rgba(0,0,0,0.11);--light-border-brand-01:#ff4800;"
             "--light-btn-idle:#ff4800;--light-btn-hover:#c93700;"
             "--dark-bg-01:#1f1f1f;--dark-container-01:#000000;--dark-text-01:#ffffff;"
             "--c-color-unused-01:#abcabc")
    return [
        _rule(*prims),
        _rule(*light),
        _rule(*dark),
        _rule("body", "background-color:var(--c-color-background-01)"),
        _rule(".card", "background-color:var(--c-color-container-01)"),
        _rule("body,p", "color:var(--c-color-text-01)"),
        _rule(".muted", "color:var(--c-color-text-02)"),
        _rule(".hairline", "border-color:var(--c-color-border-03)"),
        _rule(".badge", "border-color:var(--c-color-border-brand-01)"),
        _rule(".cta", "background-color:var(--c-color-button-primary-fill-idle)"),
        _rule(".cta:hover", "background-color:var(--c-color-button-primary-fill-hover)"),
    ]


def _joined_bands():
    def sec(i, bg):
        return {"elementId": f"section-{i:02d}", "kind": "section",
                "computedLadder": {"1440": {"backgroundColor": bg}}}
    return {"elements": [sec(0, "rgb(252, 252, 250)"), sec(1, "rgb(252, 252, 250)"),
                         sec(2, "rgb(252, 222, 210)")]}


class TestColorCssVar(unittest.TestCase):
    def setUp(self):
        ev = _write_evidence(_color_rules(), computed={"headings": {}},
                             joined=_joined_bands())
        self.doc = tf.extract_color(ev)
        self.roles = self.doc["canonicalRoles"]

    def test_theme_aware_light_wins(self):
        # container-01 resolves to the LIGHT #ffffff, never the later dark #000000.
        self.assertEqual(self.roles["surface"]["value"].lower(), "#ffffff")
        self.assertEqual(self.roles["background"]["value"].lower(), "#fcfcfa")

    def test_role_classification(self):
        self.assertEqual(self.roles["text"]["value"].lower(), "#1f1f1f")
        self.assertEqual(self.roles["accent"]["value"].lower(), "#ff4800")
        self.assertEqual(self.roles["accentHover"]["value"].lower(), "#c93700")
        self.assertEqual(self.roles["borderBrand"]["value"].lower(), "#ff4800")
        self.assertIn("border", self.roles)
        self.assertLess(self.roles["border"]["alpha"], 1.0)

    def test_defined_but_unused_flagged(self):
        self.assertIn("--c-color-unused-01", self.doc["definedButUnused"])

    def test_band_surfaces_capture_decorative_band(self):
        vals = {b["hex"] for b in self.doc["bandSurfaces"]}
        self.assertIn("#fcded2", vals)  # the decorative band no --*color* role declares
        band = next(b for b in self.doc["bandSurfaces"] if b["hex"] == "#fcded2")
        self.assertEqual(band["sections"], ["section-02"])

    def test_confirmation_agrees_on_background(self):
        self.assertTrue(self.doc["confirmation"]["background"]["agrees"])

    def test_computed_cluster_fallback(self):
        # no color custom properties → cluster measured band + heading colors.
        rules = [_rule(".x", "color:#000")]
        doc = tf.extract_color(_write_evidence(
            rules, computed={"headings": {"h1": {"color": "rgb(31,31,31)"}}},
            joined=_joined_bands()))
        self.assertEqual(doc["method"], "computed-cluster")
        self.assertTrue(doc["tokens"])


# ── css_fidelity token-tier audits ────────────────────────────────────────────────

class TestTokenTierAudits(unittest.TestCase):
    def test_radius_drift_flagged_and_clean(self):
        truth = {"canonicalRoles": {"control": {"px": 8}, "card": {"px": 16},
                                    "input": {"px": 4}}}
        drift = {"control": {"value": "8px"}, "card": {"value": "8px"},
                 "input": {"value": "4px"}}
        divs = cf.radius_tier_divergences(drift, {}, truth)
        card = [d for d in divs if d["element"] == "radius/card"]
        self.assertTrue(card, "card radius drift (8 vs 16) must be flagged")
        good = {"control": {"value": "8px"}, "card": {"value": "16px"},
                "input": {"value": "4px"}}
        self.assertEqual(cf.radius_tier_divergences(good, {}, truth), [])

    def test_spacing_offladder_flagged_and_clean(self):
        truth = {"sectionRhythm": {"md": {"px": 40}, "lg": {"px": 64}},
                 "stepScale": [{"px": 16}, {"px": 24}, {"px": 48}]}
        off = {"section-padding-light": {"value": "5rem"}}  # 80px, off-ladder
        divs = cf.spacing_tier_divergences(off, truth)
        self.assertTrue([d for d in divs if "section-padding-light" in d["element"]])
        on = {"section-padding-light": {"value": "4rem"}}  # 64px == lg
        self.assertEqual(cf.spacing_tier_divergences(on, truth), [])

    def test_color_band_surface_drift(self):
        truth = {"canonicalRoles": {"accent": {"value": "#ff4800"},
                                    "background": {"value": "#fcfcfa"}},
                 "bandSurfaces": [{"value": "#fcded2", "alpha": 1.0,
                                   "sections": ["section-04"]}]}
        # authored surfaces WITHOUT the band color → flagged; with it → clean.
        d = Path(tempfile.mkdtemp())
        (d / "brand.yaml").write_text(
            "tokens:\n  colors:\n    accent/primary:\n      value: '#ff4800'\n"
            "  surfaces:\n    surface/primary:\n      bg: '#fcfcfa'\n"
            "    surface/accent-soft:\n      bg: '#f9c9c0'\n")
        divs = cf.color_role_divergences(d / "brand.yaml", truth)
        self.assertTrue([x for x in divs if x["kind"] == "band-surface"])
        (d / "brand2.yaml").write_text(
            "tokens:\n  colors:\n    accent/primary:\n      value: '#ff4800'\n"
            "  surfaces:\n    surface/primary:\n      bg: '#fcfcfa'\n"
            "    surface/accent-soft:\n      bg: '#fcded2'\n")
        divs2 = cf.color_role_divergences(d / "brand2.yaml", truth)
        self.assertEqual([x for x in divs2 if x["kind"] == "band-surface"], [])

    def test_hex_color_tolerance(self):
        # the hex-aware comparator tolerates imperceptible drift (was a rgb-only bug).
        self.assertTrue(cf._color_close("#042729", "#002b28"))
        self.assertFalse(cf._color_close("#fcded2", "#f9c9c0"))

    def test_audit_severity_never_critical(self):
        # the css_fidelity critical==0 invariant must survive the new audits.
        truth_r = {"canonicalRoles": {"card": {"px": 16}}}
        for d in cf.radius_tier_divergences({"card": {"value": "8px"}}, {}, truth_r):
            self.assertNotEqual(d["severity"], "critical")


# ── re-authored hubspot-v3 acceptance ─────────────────────────────────────────────

class TestHubspotV3TokenAcceptance(unittest.TestCase):
    V3 = _REPO / "runs" / "hubspot-v3" / "brand"

    def setUp(self):
        if not (self.V3 / "brand.yaml").is_file():
            self.skipTest("hubspot-v3 brand.yaml absent")
        import yaml
        self.tokens = yaml.safe_load((self.V3 / "brand.yaml").read_text())["tokens"]

    def test_section4_surface_resolved(self):
        # section-4 soft-accent band was #f9c9c0 (drift); the source truth is #fcded2.
        self.assertEqual(self.tokens["surfaces"]["surface/accent-soft"]["bg"].lower(),
                         "#fcded2")
        self.assertEqual(self.tokens["colors"]["surface/accent-soft"]["value"].lower(),
                         "#fcded2")

    def test_radius_family_matches_truth(self):
        r = self.tokens.get("radius") or {}
        self.assertEqual(cf._px_of(r["control"]["value"]), 8.0)
        self.assertEqual(cf._px_of(r["card"]["value"]), 16.0)
        self.assertEqual(cf._px_of(r["input"]["value"]), 4.0)

    def test_section_padding_on_scale(self):
        self.assertEqual(cf._px_of(
            self.tokens["spacing"]["section-padding-light"]["value"]), 64.0)

    def test_zero_token_tier_divergences_vs_truth(self):
        for loader, authored in (
                (cf.load_spacing_truth,
                 lambda: cf.spacing_tier_divergences(
                     self.tokens["spacing"], cf.load_spacing_truth(self.V3))),
                (cf.load_radius_truth,
                 lambda: cf.radius_tier_divergences(
                     self.tokens.get("radius", {}), self.tokens["spacing"],
                     cf.load_radius_truth(self.V3))),
                (cf.load_color_truth,
                 lambda: cf.color_role_divergences(
                     self.V3 / "brand.yaml", cf.load_color_truth(self.V3)))):
            if loader(self.V3) is None:
                self.skipTest("token-family truth artifact absent — run token_families")
            self.assertEqual(authored(), [], "authored v3 diverges from css-var truth")


if __name__ == "__main__":
    unittest.main()
