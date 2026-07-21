#!/usr/bin/env python3
"""Unit tests for brand_pipeline/compose_replica.py — the replica gate (P0.2).

Synthetic fixtures only (no brand data, no Playwright): source-order resolution
from pattern provenance (+ fail-loud on unmapped patterns), the Pillow-only band
similarity metric, and the evidence-driven renderer-gap detectors.

Run:  ./venv/bin/python -m unittest brand_pipeline.tests.test_compose_replica
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_BP = _REPO / "brand_pipeline"
if str(_BP) not in sys.path:
    sys.path.insert(0, str(_BP))

import compose_replica as cx  # noqa: E402


def _doc(layout_ids):
    return {"layouts": [{"id": i, "archetype": "stack",
                         "patternRef": {"id": f"pat-{i}"}} for i in layout_ids]
            + [{"id": "navbar", "archetype": "nav"},
               {"id": "footer", "archetype": "grid"}]}


class SourceOrderTests(unittest.TestCase):
    def test_orders_by_provenance_layout_position(self):
        doc = _doc(["hero", "logos", "cta"])
        # patterns deliberately shuffled: provenance restores source order
        patterns = [{"id": "pat-cta", "provenance": ["cta"]},
                    {"id": "pat-hero", "provenance": ["hero"]},
                    {"id": "pat-logos", "provenance": ["logos"]}]
        pairs = cx.source_order_sections(doc, patterns)
        self.assertEqual([l["id"] for l, _ in pairs], ["hero", "logos", "cta"])
        self.assertEqual([p["id"] for _, p in pairs],
                         ["pat-hero", "pat-logos", "pat-cta"])

    def test_falls_back_to_pattern_ref_backlink(self):
        doc = _doc(["hero"])
        patterns = [{"id": "pat-hero", "provenance": ["section-00"]}]  # opaque prov
        pairs = cx.source_order_sections(doc, patterns)
        self.assertEqual([l["id"] for l, _ in pairs], ["hero"])

    def test_unmapped_pattern_fails_loud(self):
        doc = _doc(["hero"])
        patterns = [{"id": "pat-ghost", "provenance": ["nowhere"]}]
        with self.assertRaises(SystemExit):
            cx.source_order_sections(doc, patterns)

    def test_chrome_layouts_never_become_sections(self):
        doc = _doc(["hero"])
        patterns = [{"id": "pat-hero", "provenance": ["hero"]}]
        pairs = cx.source_order_sections(doc, patterns)
        self.assertNotIn("navbar", [l["id"] for l, _ in pairs])

    def test_footer_crop_pattern_is_not_duplicated_as_section(self):
        doc = _doc(["hero", "sitemap-footer"])
        patterns = [{"id": "pat-hero", "provenance": ["hero"]},
                    {"id": "pat-footer", "provenance": ["section-10-footer"]}]
        pairs = cx.source_order_sections(doc, patterns)
        self.assertEqual([l["id"] for l, _ in pairs], ["hero"])


class BandSimilarityTests(unittest.TestCase):
    def _im(self, color, size=(200, 100)):
        from PIL import Image
        return Image.new("RGB", size, color)

    def test_identical_bands_score_one(self):
        a = self._im((240, 240, 240))
        m = cx.band_similarity(a, a.copy())
        self.assertAlmostEqual(m["score"], 1.0, places=3)
        self.assertAlmostEqual(m["height"], 1.0, places=3)

    def test_inverted_bands_score_low(self):
        a = self._im((255, 255, 255))
        b = self._im((0, 0, 0))
        m = cx.band_similarity(a, b)
        self.assertLess(m["score"], 0.25)

    def test_height_ratio_penalizes_size_drift(self):
        a = self._im((200, 200, 200), size=(200, 100))
        b = self._im((200, 200, 200), size=(200, 200))
        m = cx.band_similarity(a, b)
        self.assertAlmostEqual(m["height"], 0.5, places=3)
        self.assertGreater(m["structure"], 0.9)  # same flat surface


class KnownGapsTests(unittest.TestCase):
    def test_marquee_treatment_detected(self):
        pat = {"id": "logo-strip", "useCase": "logos",
               "specialTreatments": [{"kind": "marquee", "target": "logos"}]}
        gaps = cx._known_gaps({}, {"id": "logo-wall", "useCase": "logos"}, pat)
        self.assertTrue(any(g.startswith("marquee animation") for g in gaps))

    def test_accordion_open_state_detected(self):
        gaps = cx._known_gaps({}, {"id": "feature-accordion",
                                   "useCase": "accordion features"}, {"id": "p"})
        self.assertTrue(any("accordion open-state" in g for g in gaps))

    def test_plain_section_yields_no_gaps(self):
        gaps = cx._known_gaps({}, {"id": "about", "useCase": "about statement"},
                              {"id": "p", "useCase": "about"})
        self.assertEqual(gaps, [])


class ChromeGapsTests(unittest.TestCase):
    """_chrome_gaps honesty (hubspot-v2 2026-07): declared-absent banners and
    self-hosted fonts with PostScript-style (space-free) file stems must not
    surface as renderer gaps."""

    def test_utility_banner_not_observed_is_not_a_gap(self):
        import tempfile
        doc = {"navbar": {"utilityBanner": {
            "notObserved": True, "note": "source shows no banner"}}}
        with tempfile.TemporaryDirectory() as td:
            gaps = cx._chrome_gaps(doc, Path(td), "<html></html>")
        self.assertFalse(any(g["capability"] == "utility banner" for g in gaps))

    def test_utility_banner_observed_but_unrendered_is_a_gap(self):
        import tempfile
        doc = {"navbar": {"utilityBanner": {
            "observed": True, "text": "Big promo — act now"}}}
        with tempfile.TemporaryDirectory() as td:
            gaps = cx._chrome_gaps(doc, Path(td), "<html>no banner here</html>")
        self.assertTrue(any(g["capability"] == "utility banner" for g in gaps))

    def test_spaced_family_matches_spacefree_font_stem(self):
        import tempfile
        doc = {"tokens": {"type": {"display-hero": {"family": "HubSpot Serif"}}}}
        with tempfile.TemporaryDirectory() as td:
            fonts = Path(td) / "assets" / "fonts"
            fonts.mkdir(parents=True)
            (fonts / "HubSpotSerif-Book.woff2").write_bytes(b"\0")
            gaps = cx._chrome_gaps(doc, Path(td), "<html></html>")
        self.assertFalse(any("display font" in g["capability"] for g in gaps))

    def test_full_css_stack_matches_registered_font_file(self):
        import tempfile
        doc = {"tokens": {"type": {"display-hero": {
            "family": '"HubSpot Serif Page Header Human", "HubSpot Serif", serif'}}}}
        with tempfile.TemporaryDirectory() as td:
            fonts = Path(td) / "assets" / "fonts"
            fonts.mkdir(parents=True)
            (fonts / "HubSpotSerif-Medium.woff2").write_bytes(b"\0")
            gaps = cx._chrome_gaps(doc, Path(td), "<html></html>")
        self.assertFalse(any("display font" in g["capability"] for g in gaps))

    def test_missing_display_font_still_flagged(self):
        import tempfile
        doc = {"tokens": {"type": {"display-hero": {"family": "Proprietary Face"}}}}
        with tempfile.TemporaryDirectory() as td:
            gaps = cx._chrome_gaps(doc, Path(td), "<html></html>")
        self.assertTrue(any("display font" in g["capability"] for g in gaps))


class MultiViewportGateTests(unittest.TestCase):
    """Phase 5: the multi-viewport replica gate records per-viewport responsiveness
    numbers (no browser needed for the report shape / ladder constant)."""

    def test_ladder_constant_primary_first(self):
        self.assertEqual(cx.VIEWPORT_LADDER[0], 1440)
        self.assertIn(375, cx.VIEWPORT_LADDER)
        self.assertIn(960, cx.VIEWPORT_LADDER)
        self.assertIn(1920, cx.VIEWPORT_LADDER)

    def test_report_renders_per_viewport_section(self):
        import json
        import tempfile
        per_viewport = [
            {"viewport": 1440, "primary": True, "responsivenessHealth": 1.0,
             "overflowPx": 0, "bands": 12, "heroHeight": 800, "footerColumns": 5,
             "docHeight": 6000, "overflowEl": "", "screenshot": "replica-fullpage-1440.png"},
            {"viewport": 375, "primary": False, "responsivenessHealth": 0.5,
             "overflowPx": 389, "bands": 12, "heroHeight": 700, "footerColumns": 1,
             "docHeight": 9000, "overflowEl": "cs-nav-util",
             "screenshot": "replica-fullpage-375.png"},
        ]
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            cx.build_report(out, [], [], 0.911,
                            {"brand": "x", "sourceShot": "s.png", "sourceHeight": 1,
                             "replicaHeight": 1},
                            per_viewport)
            md = (out / "replica-report.md").read_text()
            doc = json.loads((out / "replica-report.json").read_text())
        self.assertIn("Multi-viewport replica gate", md)
        self.assertIn("responsiveness", md)
        self.assertIn("primary (fidelity)", md)
        self.assertIn("cs-nav-util", md)          # overflow culprit surfaced honestly
        self.assertEqual(len(doc["perViewport"]), 2)
        self.assertTrue(doc["perViewport"][0]["primary"])

    def test_report_omits_section_when_no_ladder(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            cx.build_report(out, [], [], 0.9,
                            {"brand": "x", "sourceShot": "s.png", "sourceHeight": 1,
                             "replicaHeight": 1})
            md = (out / "replica-report.md").read_text()
        self.assertNotIn("Multi-viewport replica gate", md)


if __name__ == "__main__":
    unittest.main()
