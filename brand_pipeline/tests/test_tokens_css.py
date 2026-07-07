#!/usr/bin/env python3
"""Unit tests for the layer-1 token generator (brand_pipeline/tokens_css.py — SPEC §G.1).

Covers: required-set completeness on both live brands; flat layer-1 (Webflow-clean);
type-shape normalization (flat vs families+scale); the motion trio; button-family
optionality (WoodWave typographic CTA ⇒ `filled-button` disabled); the responsive
sizeRem ladder; hard-fail on a missing REQUIRED token (DECISIONS.md #2); manifest/css
determinism; aspectPalette optionality (DECISIONS.md #5); case mapping; px→rem chrome.

The synthetic fixture brand ("Ravine") deliberately uses values DISTINCT from WoodWave
so the provenance foreign-brand tests (test_token_provenance.py) can tell them apart.

Run:  ./venv/bin/python -m unittest brand_pipeline.tests.test_tokens_css
"""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

import yaml

_BRAND_PIPELINE = Path(__file__).resolve().parent.parent
if str(_BRAND_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_BRAND_PIPELINE))

import tokens_css as tc  # noqa: E402

_WOODWAVE = _BRAND_PIPELINE.parent / "runs" / "woodwave" / "brand" / "brand.yaml"
_HUBSPOT = _BRAND_PIPELINE.parent / "runs" / "hubspot" / "brand" / "brand.yaml"


def _tier(family, size, weight, leading, case, tracking):
    return {"family": family, "sizeRem": size, "weight": weight,
            "lineHeight": leading, "case": case, "letterSpacing": tracking}


# Synthetic multi-brand fixture — flat type shape (WoodWave-like structure,
# non-WoodWave values).
FIXTURE = {
    "brand": {"name": "Ravine"},
    "tokens": {
        "colors": {
            "text/on-primary": {"value": "#10141A"},
            "text/on-primary-muted": {"value": "#4A5568"},
            "text/on-inverse": {"value": "#F2F6FA"},
            "text/on-inverse-muted": {"value": "#B8C4D0"},
            "border/hairline-on-primary": {"value": "#D8DEE6"},
            "text/ghost-on-primary": {"value": "#E9EDF2"},
            "accent/primary": {"value": "#0F62FE"},
        },
        "surfaces": {
            "surface/primary": {"bg": "#FFFFFF", "schemeMode": "light",
                                "textPrimary": "text/on-primary"},
            "surface/panel": {"bg": "#EEF2F7", "schemeMode": "light",
                              "textPrimary": "text/on-primary"},
            "surface/inverse": {"bg": "#1B2530", "schemeMode": "dark",
                                "textPrimary": "text/on-inverse",
                                "textAccent": "accent/primary"},
            "surface/inverse-strong": {"bg": "#10141A", "schemeMode": "dark",
                                       "textPrimary": "text/on-inverse",
                                       "textAccent": "accent/primary"},
        },
        "type": {
            "display-hero": _tier("Fixture Serif",
                                  {"base": 5.5, "tablet": 4.5, "mobileL": 3.25,
                                   "mobile": 2.75},
                                  500, 1.02, "sentence", "-0.01em"),
            "h1": _tier("Fixture Serif", 3.5, 500, 1.05, "sentence", None),
            "h2": _tier("Fixture Serif", 2.75, 400, 1.1, "uppercase", "0.02em"),
            "h3": _tier("Fixture Sans", 1.5, 600, 1.2, "sentence", None),
            "body": _tier("Fixture Sans", 1.0625, 400, 1.55, "sentence", None),
            "eyebrow": _tier("Fixture Sans", 0.8125, 600, 1.1, "uppercase", "0.18em"),
            "control-text": _tier("Fixture Sans", 0.9375, 500, 1.0, "title", "0.05em"),
        },
        "spacing": {
            "section-y-major": {"value": "7.5rem"},
            "section-y-minor": {"value": "4.5rem"},
            "panel-padding": {"value": "2.25rem"},
            "eyebrow-to-heading": {"value": "1.5rem"},
            "radius-global": {"value": "0.375rem"},
        },
        "imagery": {"aspectPalette": {"landscape": {"value": "3/2"},
                                      "portrait": {"value": "4/5"}}},
    },
    "voice": {"motionSpec": {
        "durations": {"fast": "180ms", "base": "240ms", "slow": "420ms"},
        "easing": {"primary": "cubic-bezier(.2, .8, .2, 1)"},
        "scrollReveal": {"translateY": "12px"},
    }},
    "buttons": {"primary": {"bg": "#0F62FE", "fg": "#FFFFFF", "bgHover": "#0043CE",
                            "padding": "0.875rem 1.75rem", "radius": "0.375rem",
                            "weight": 600, "sizeRem": 1.0}},
    "navbar": {"measured": {"link": {"fontSize": 15, "fontWeight": 500},
                            "logo": {"width": 120, "height": 28}}},
    "footer": {"measured": {"link": {"fontSize": 14, "fontWeight": 400},
                            "linkHoverColor": "#9BB8E8"}},
}

# The SAME fixture expressed in the families+scale shape (HubSpot-like structure) —
# canonical roles must normalize to the same layer-1 namespace.
FIXTURE_SCALE = copy.deepcopy(FIXTURE)
FIXTURE_SCALE["tokens"]["type"] = {
    "families": {"display": {"value": "Fixture Serif"},
                 "body": {"value": "Fixture Sans"}},
    "scale": {
        "display-01": {"family": "display", "sizeRem": 5.5, "line": 1.02,
                       "weight": 500, "tracking": "-0.01em", "case": "sentence"},
        "h2": {"family": "display", "sizeRem": 2.75, "line": 1.1, "weight": 400,
               "tracking": "0.02em", "case": "uppercase"},
        "h3": {"family": "body", "sizeRem": 1.5, "line": 1.2, "weight": 600},
        "body-lg": {"family": "body", "sizeRem": 1.0625, "line": 1.55, "weight": 400},
        "eyebrow": {"family": "body", "sizeRem": 0.8125, "line": 1.1, "weight": 600,
                    "tracking": "0.18em", "case": "uppercase"},
        "button-md": {"family": "button", "sizeRem": 0.9375, "line": 1.0,
                      "weight": 500, "case": "title", "tracking": "0.05em"},
    },
}
# families+scale has no h1 tier by that name; type_role falls back through the display
# family — keep h1 satisfiable by the display pick (largest display entry).


def _load(path):
    return yaml.safe_load(path.read_text())


class RequiredSetTests(unittest.TestCase):
    def test_woodwave_required_complete(self):
        bundle = tc.build_page_tokens(_load(_WOODWAVE), brand_yaml_path=_WOODWAVE)
        self.assertFalse(bundle.missing)
        for tok in ("--color-text-on-primary", "--color-text-on-inverse",
                    "--surface-surface-panel", "--surface-surface-inverse-strong",
                    "--font-display-hero", "--size-display-hero", "--case-h2",
                    "--tracking-eyebrow", "--space-panel-padding", "--radius-global",
                    "--motion-fast", "--motion-base", "--motion-slow", "--motion-ease",
                    "--size-nav", "--chrome-link-hover"):
            self.assertIn(tok, bundle.index, tok)
        # WoodWave truths: hero display 500, section headings (h2) 400
        self.assertEqual(bundle.index.get("--weight-display-hero"), "500")
        self.assertEqual(bundle.index.get("--weight-h2"), "400")
        self.assertEqual(bundle.index.get("--case-h2"), "uppercase")
        self.assertEqual(bundle.index.get("--chrome-link-hover"), "#edd580")

    def test_hubspot_required_complete(self):
        bundle = tc.build_page_tokens(_load(_HUBSPOT), brand_yaml_path=_HUBSPOT)
        self.assertFalse(bundle.missing)
        self.assertIn("--button-bg", bundle.index)
        self.assertIn("--button-fg", bundle.index)
        self.assertEqual(bundle.index.get("--case-h2"), "none")

    def test_fixture_required_complete_both_shapes(self):
        flat = tc.build_page_tokens(FIXTURE)
        scale = tc.build_page_tokens(FIXTURE_SCALE)
        self.assertFalse(flat.missing)
        self.assertFalse(scale.missing)


class ShapeNormalizationTests(unittest.TestCase):
    def test_canonical_namespace_identical_across_shapes(self):
        flat = tc.build_page_tokens(FIXTURE).index
        scale = tc.build_page_tokens(FIXTURE_SCALE).index
        for tok in ("--font-display-hero", "--size-display-hero", "--case-eyebrow",
                    "--tracking-eyebrow", "--size-body", "--case-control-text"):
            self.assertIn(tok, flat, tok)
            self.assertIn(tok, scale, tok)
        self.assertEqual(flat["--size-eyebrow"], scale["--size-eyebrow"])
        self.assertEqual(flat["--tracking-eyebrow"], scale["--tracking-eyebrow"])
        self.assertEqual(flat["--case-eyebrow"], scale["--case-eyebrow"])

    def test_case_mapping(self):
        idx = tc.build_page_tokens(FIXTURE).index
        self.assertEqual(idx["--case-h2"], "uppercase")       # uppercase → uppercase
        self.assertEqual(idx["--case-h1"], "none")            # sentence → none
        self.assertEqual(idx["--case-control-text"], "capitalize")  # title → capitalize


class FlatLayerTests(unittest.TestCase):
    def test_layer1_values_webflow_clean(self):
        for doc in (_load(_WOODWAVE), _load(_HUBSPOT), FIXTURE):
            bundle = tc.build_page_tokens(doc)
            offenders = [k for k, v in bundle.index.items()
                         if "var(" in v or "calc(" in v or "clamp(" in v]
            self.assertEqual(offenders, [], offenders)

    def test_responsive_ladder(self):
        bundle = tc.build_page_tokens(FIXTURE)
        self.assertEqual(bundle.index["--size-display-hero"], "5.5rem")
        self.assertEqual(bundle.index["--size-display-hero@tablet"], "4.5rem")
        self.assertEqual(bundle.index["--size-display-hero@mobileL"], "3.25rem")
        self.assertIn("@media (max-width: 991px)", bundle.css)
        self.assertIn("--size-display-hero: 4.5rem;", bundle.css)
        # flat -base alias for structural calc ladders
        self.assertEqual(bundle.index["--size-display-hero-base"], "5.5rem")


class MotionButtonsAspectTests(unittest.TestCase):
    def test_motion_trio_and_shift(self):
        idx = tc.build_page_tokens(FIXTURE).index
        self.assertEqual(idx["--motion-fast"], "180ms")
        self.assertEqual(idx["--motion-base"], "240ms")
        self.assertEqual(idx["--motion-slow"], "420ms")
        self.assertEqual(idx["--motion-ease"], "cubic-bezier(.2, .8, .2, 1)")
        self.assertEqual(idx["--motion-shift"], "12px")

    def test_buttons_optional_family(self):
        ww = tc.build_page_tokens(_load(_WOODWAVE))
        self.assertIn("filled-button", ww.disabled_devices)
        self.assertNotIn("--button-bg", ww.index)
        fx = tc.build_page_tokens(FIXTURE)
        self.assertEqual(fx.index["--button-bg"], "#0F62FE")
        self.assertEqual(fx.index["--button-pad"], "0.875rem 1.75rem")
        self.assertEqual(fx.index["--button-weight"], "600")
        self.assertNotIn("filled-button", fx.disabled_devices)

    def test_aspect_palette_optional(self):
        hs = tc.build_page_tokens(_load(_HUBSPOT))
        self.assertIn("aspect-palette", hs.disabled_devices)  # DECISIONS.md #5
        fx = tc.build_page_tokens(FIXTURE)
        self.assertEqual(fx.index["--aspect-landscape"], "3/2")
        self.assertNotIn("aspect-palette", fx.disabled_devices)


class FailLoudTests(unittest.TestCase):
    def test_missing_required_color_raises_named(self):
        broken = copy.deepcopy(FIXTURE)
        del broken["tokens"]["colors"]["text/on-inverse"]
        with self.assertRaises(tc.TokenGenerationError) as cm:
            tc.build_page_tokens(broken)
        self.assertIn("tokens.colors.text/on-inverse", str(cm.exception))
        self.assertIn("Ravine", str(cm.exception))

    def test_missing_motion_raises_named(self):
        broken = copy.deepcopy(FIXTURE)
        del broken["voice"]["motionSpec"]["durations"]["base"]
        with self.assertRaises(tc.TokenGenerationError) as cm:
            tc.build_page_tokens(broken)
        self.assertIn("voice.motionSpec.durations.base", str(cm.exception))


class DeterminismChromeTests(unittest.TestCase):
    def test_css_deterministic_across_runs(self):
        a = tc.build_page_tokens(FIXTURE)
        b = tc.build_page_tokens(FIXTURE)
        self.assertEqual(a.css, b.css)  # header carries no timestamp
        self.assertEqual(a.index, b.index)

    def test_chrome_px_to_rem(self):
        idx = tc.build_page_tokens(FIXTURE).index
        self.assertEqual(idx["--size-nav"], "0.9375rem")
        self.assertEqual(idx["--chrome-foot-link-size"], "0.875rem")
        self.assertEqual(idx["--chrome-nav-logo-w"], "7.5rem")

    def test_style_tag_has_tokens_id(self):
        bundle = tc.build_page_tokens(FIXTURE)
        tag = tc.style_tag(bundle)
        self.assertTrue(tag.startswith('<style id="tokens">'))
        self.assertIn("generated design tokens (layer 1)", tag)


if __name__ == "__main__":
    unittest.main()
