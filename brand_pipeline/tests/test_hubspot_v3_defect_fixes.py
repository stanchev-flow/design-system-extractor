#!/usr/bin/env python3
"""Regression pins for the hubspot-v3 proof-section + bookend defect batch (2026-07).

Six user-reported defects, each fixed at the shared renderer/composition level
(fact-gated, brand-agnostic) and pinned here so it cannot silently return:

  D1 missing CTA      — a dual-cta actionGroup slot renders BOTH actions (filled
                        primary + outlined secondary), never just the lead CTA.
  D2 bookend surface  — the coarse `inverse` surface intent re-roles to the brand's
                        measured dark bookend surface (surfaceGrammar.bookend) so a
                        composed hero / closing CTA paints the measured teal, not the
                        neutral footer inverse.
  D4 duplicate copy   — a headrail/kicker slot binds the eyebrow register (not a
                        second body paragraph); AS-84 single-voice dedup drops any
                        text row whose visible copy repeats an earlier row.
  D5 badge sizing     — an award/mark row with a measured `mediaScale.item` box (no
                        container fraction, bare-px values) renders at that measured
                        box, not the structural logo height.
  D6 tab alignment    — a tabbed section's rail follows the section's resolved anchor
                        (left/right) instead of the hardcoded centered default.

The generated D2 pin renders the frozen composition deterministically; the replica
pins build the v3 source-order page. Both reuse the shipped composers (no fixtures).
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "brand_pipeline"))

import compose_from_composition as cfc  # noqa: E402
import compose_replica as crp  # noqa: E402

V3_BRAND = REPO / "runs" / "hubspot-v3" / "brand"
V3_BRAND_YAML = V3_BRAND / "brand.yaml"
V3_COMPOSITION = V3_BRAND / "compose" / "ai-product-launch" / "composition.json"

_PROOF_LINE = "Scale your business with HubSpot. The proof is in our customers"


@unittest.skipUnless(V3_BRAND_YAML.is_file(), "hubspot-v3 brand fixture required")
class ReplicaProofSectionFixes(unittest.TestCase):
    """D1 / D4 / D5 / D6 — all land on the replica (source-order) page."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.mkdtemp(prefix="v3-replica-")
        crp.build_replica_page(V3_BRAND_YAML, Path(cls._tmp))
        cls.html = (Path(cls._tmp) / "index.html").read_text()

    def _section(self, layout_id: str) -> str:
        """The HTML of the section whose wrapper declares data-layout=<layout_id>."""
        html = self.html
        start = html.find(f'data-layout="{layout_id}"')
        self.assertNotEqual(start, -1, f"section {layout_id} not rendered")
        nxt = html.find('<div id="sec-', start + 1)
        return html[start:nxt if nxt != -1 else len(html)]

    def test_d4_proof_line_renders_exactly_once(self):
        # the duplicated eyebrow-above + subhead-below slop: the measured body line
        # must appear ONCE across the whole page (it was emitted twice in one band).
        self.assertEqual(self.html.count(_PROOF_LINE), 1,
                         "proof body line must render exactly once (AS-84 dedup)")

    def test_d4_headrail_binds_eyebrow_not_second_body(self):
        band = self._section("headrail-two-col-header")
        self.assertIn("Case Studies", band)                 # eyebrow microlabel bound
        self.assertIn('class="c-eyebrow"', band)             # …in the eyebrow register
        self.assertEqual(band.count(_PROOF_LINE), 1)         # body once, not twice

    def test_d1_dual_cta_renders_both_actions(self):
        # the hero and the closing CTA each pair a filled primary + outlined secondary;
        # the "ghost" secondary was previously dropped on the replica path.
        hero = self._section("full-bleed-photo-hero")
        self.assertIn("Get a demo", hero)
        self.assertIn("Get started free", hero)
        cta = self._section("dark-band-cta")
        self.assertIn("Get a demo", cta)
        self.assertIn("Get started free", cta)
        self.assertIn("c-button--secondary", cta)

    def test_d5_award_badges_ride_measured_item_box(self):
        band = self._section("heading-left-award-badges-right")
        self.assertIn("cs-logo-strip--itembox", band)
        self.assertIn("--cs-strip-item-w: 96px", band)
        self.assertIn("--cs-strip-item-h: 132px", band)

    def test_d6_tab_rail_follows_left_anchor(self):
        # the tabbed testimonial's rail follows the section's left anchor instead of
        # the hardcoded centered default (arbitrary left-header + centered-tabs mix).
        tabs = self._section("tabbed-testimonial-with-stats")
        # the section wrapper id drives the per-section rule; find its #sec-N id.
        import re
        sid = re.search(r'id="(sec-\d+)"[^>]*data-layout="tabbed-testimonial', self.html)
        self.assertIsNotNone(sid)
        self.assertIn(f"#{sid.group(1)} .cs-tablist {{ justify-content: flex-start; }}",
                      self.html)


@unittest.skipUnless(V3_BRAND_YAML.is_file(), "hubspot-v3 brand fixture required")
class BookendSurfaceRemap(unittest.TestCase):
    """D2 — the coarse `inverse` intent re-roles to the measured dark bookend."""

    def _doc(self, bookend):
        surfaces = {"surface/primary": {"bg": "#fcfcfa"},
                    "surface/inverse": {"bg": "#1f1f1f"},
                    "surface/inverse-teal": {"bg": "#002b28"}}
        doc = {"tokens": {"surfaces": surfaces}, "layouts": []}
        if bookend:
            doc["surfaceGrammar"] = {"bookend": bookend}
        return doc

    def _closing_section(self):
        return {"id": "closing", "archetype": "stack", "surfaceIntent": "inverse",
                "slots": [{"name": "heading", "role": "display", "contract": "heading",
                           "copy": {"heading": "Grow with us."}}]}

    def test_inverse_remaps_to_declared_bookend(self):
        layout, _merged, _sect = cfc.adapt_brand_section(
            self._closing_section(), self._doc("surface/inverse-teal"))
        self.assertEqual(layout["surfaceIntent"], "surface/inverse-teal")

    def test_no_bookend_declared_stays_plain_inverse(self):
        layout, _merged, _sect = cfc.adapt_brand_section(
            self._closing_section(), self._doc(None))
        self.assertEqual(layout["surfaceIntent"], "surface/inverse")

    def test_bookend_equal_to_inverse_is_a_noop(self):
        layout, _merged, _sect = cfc.adapt_brand_section(
            self._closing_section(), self._doc("surface/inverse"))
        self.assertEqual(layout["surfaceIntent"], "surface/inverse")

    def test_v3_generated_bookends_paint_measured_teal(self):
        comp = json.loads(V3_COMPOSITION.read_text())
        with tempfile.TemporaryDirectory(prefix="v3-gen-") as tmp:
            cfc.render_composition(comp, V3_BRAND_YAML, tmp,
                                   style_id="corporate-saas-clean", brand_dir=V3_BRAND)
            html = (Path(tmp) / "index.html").read_text()
        # the composed hero (sec-0) + closing CTA both resolve to the teal bookend var.
        self.assertIn("--c-paper: var(--surface-surface-inverse-teal)", html)
        # …and the surface token carries the measured teal value.
        self.assertIn("--surface-surface-inverse-teal: #002b28", html)


if __name__ == "__main__":
    unittest.main()
