#!/usr/bin/env python3
"""Fixture-based unit tests for the editorial-harvest-2026-07 gate checks
(brand_pipeline/onbrand_check.py — composition invariants):

  - G8 occlusion contract (`_check_occlusion`): recompute from the stamped grid
    geometry, enforce the maxOcclusion budget + endsVisible + stamp agreement.
  - G9 band attribution (`_check_bands`): a banded section declares + scopes BOTH
    band surfaces with real inline tokens.
  - the layout library exposes the new treatment kinds and retrieves every
    harvested standard-tier pattern (none silently neverDo-filtered for WoodWave).

Run:  ./venv/bin/python -m unittest brand_pipeline.tests.test_harvest_checks
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

_BRAND_PIPELINE = Path(__file__).resolve().parent.parent
if str(_BRAND_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_BRAND_PIPELINE))

import onbrand_check as oc          # noqa: E402
import layout_library as ll         # noqa: E402

_WOODWAVE = _BRAND_PIPELINE.parent / "runs" / "woodwave" / "brand" / "brand.yaml"

HARVESTED = ["card-over-portrait-statement", "boundary-straddle-headline",
             "framed-inset-monument", "stepped-overlay-statement",
             "type-behind-media-masthead", "tucked-headline-panorama",
             "staggered-caption-columns-3", "seam-straddle-portrait"]


def _occluded_section(occlusion: float, cap: float, ends: bool,
                      horiz: float, vert: float) -> str:
    geom = ('{"headingCols":[1,13],"mediaCols":[5,10],'
            f'"horizFrac":{horiz},"vertFrac":{vert}}}')
    return (f'<section class="cs-section" data-occlusion="{occlusion:g}" '
            f'data-occlusion-max="{cap:g}" data-ends-visible="{str(ends).lower()}" '
            f"data-occlusion-geom='{geom}'></section>")


class OcclusionContractTest(unittest.TestCase):
    def test_within_budget_passes(self):
        ok, detail = oc._check_occlusion(_occluded_section(0.17, 0.4, True, 0.417, 0.4))
        self.assertTrue(ok, detail)

    def test_over_budget_fails(self):
        # recomputed 0.9 * 0.6 = 0.54 > light cap 0.25
        ok, detail = oc._check_occlusion(_occluded_section(0.54, 0.25, True, 0.9, 0.6))
        self.assertFalse(ok)
        self.assertIn("budget", detail)

    def test_ends_visible_violation_fails(self):
        ok, detail = oc._check_occlusion(_occluded_section(0.17, 0.4, False, 0.417, 0.4))
        self.assertFalse(ok)
        self.assertIn("endsVisible", detail)

    def test_stamp_geometry_disagreement_fails(self):
        # stamped 0.05 but geometry recomputes 0.417 * 0.4 = 0.167 -> mismatch flagged
        ok, detail = oc._check_occlusion(_occluded_section(0.05, 0.4, True, 0.417, 0.4))
        self.assertFalse(ok)
        self.assertIn("disagrees", detail)

    def test_no_occluded_headings_is_pass(self):
        ok, _ = oc._check_occlusion("<section class='cs-section'></section>")
        self.assertTrue(ok)


def _banded_section(*, both_scoped: bool = True, with_vars: bool = True) -> str:
    style = ('style="--c-paper: #3A2F23; --c-ink: #F3EBDD; background: #3A2F23; '
             'color: #F3EBDD"') if with_vars else 'style="padding: 0"'
    second = (f'<div class="cs-band" data-band-surface="surface/panel" {style}></div>'
              if both_scoped else '<div class="cs-band"></div>')
    return (f'<section class="cs-section" data-bands="surface/inverse,surface/panel" '
            f'data-band-split="0.5">'
            f'<div class="cs-band" data-band-surface="surface/inverse" {style}></div>'
            f'{second}</section>')


class BandAttributionTest(unittest.TestCase):
    def test_two_scoped_bands_pass(self):
        ok, detail = oc._check_bands(_banded_section())
        self.assertTrue(ok, detail)

    def test_missing_band_scope_fails(self):
        ok, detail = oc._check_bands(_banded_section(both_scoped=False))
        self.assertFalse(ok)

    def test_band_without_surface_vars_fails(self):
        ok, detail = oc._check_bands(_banded_section(with_vars=False))
        self.assertFalse(ok)
        self.assertIn("scoped surface vars", detail)

    def test_no_banded_sections_is_pass(self):
        ok, _ = oc._check_bands("<section class='cs-section'></section>")
        self.assertTrue(ok)


class HarvestLibraryTest(unittest.TestCase):
    def test_new_treatment_kinds_registered(self):
        for kind in ("straddle", "panel-on-media", "scrim-band", "framed",
                     "type-behind-media", "mixed-face", "stepped-lines", "break-frame"):
            self.assertIn(kind, ll.TREATMENT_KINDS)

    @unittest.skipUnless(_WOODWAVE.exists(), "WoodWave brand run not present")
    def test_harvested_patterns_retrievable_for_woodwave(self):
        """Every harvested pattern resolves AND survives the WoodWave neverDo filter
        (media-target straddles + sanctioned text treatments are not screened out)."""
        for uc in ("hero", "gallery", "about"):
            ctx = ll.resolve_library(uc, _WOODWAVE)
            surviving = {p.id for p in ctx.candidates
                         if not ll._violates_neverdo(p, ctx.brand_neverdo)}
            for pid in HARVESTED:
                p = ll.get({"lib": "standard", "id": pid}, _WOODWAVE)
                self.assertIsNotNone(p, pid)
                if p.use_case == uc:
                    self.assertIn(pid, surviving)


if __name__ == "__main__":
    unittest.main()
