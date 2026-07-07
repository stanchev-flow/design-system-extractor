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


if __name__ == "__main__":
    unittest.main()
