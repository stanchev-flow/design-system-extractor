#!/usr/bin/env python3
"""Fixture-based unit tests for the STICKY COPY COLUMN device (fix1 2026-07, AS-83
driver — `patterns[].specialTreatments sticky-column`).

The source pins the copy column while the counterweight card grid scrolls (measured
`.…-sticky-sidebar { position:sticky; height:fit-content; top:calc(nav-height + offset) }`).
The device reuses the side-rail morphology (copy LEFT / grid RIGHT, which already owns
`position: sticky`) and supplies the MEASURED per-section pin. Everything is fact-gated:
a brand without the sanctioned treatment stamps nothing and ships byte-identical CSS.

Run:  ./venv/bin/python -m unittest brand_pipeline.tests.test_fix_sticky_column
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

_BRAND_PIPELINE = Path(__file__).resolve().parent.parent
if str(_BRAND_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_BRAND_PIPELINE))

import compose_section as cs  # noqa: E402


def _pattern(treatments):
    p = mock.Mock()
    p.special_treatments = treatments
    p.slots = []
    p.content_shape = {}
    p.archetype_ref = "split"
    return p


class StampStickyColumn(unittest.TestCase):
    def test_sanctioned_sticky_column_stamps_siderail_and_measured_pin(self):
        layout = {"id": "sticky-x", "useCase": "features"}
        treatment = {"kind": "sticky-column", "target": "heading", "sanctioned": True,
                     "offset": "2rem",
                     "navHeight": {"base": "56px", "wide": "76px", "wideMinWidth": 1080}}
        with mock.patch.object(cs, "resolve_pattern",
                               return_value=(_pattern([treatment]), "reuse")):
            cs.stamp_pattern_devices({"tokens": {}}, layout, None)
        # reuses the side-rail morphology (copy-left/grid-right, which owns position:sticky)
        self.assertTrue(layout.get("_sideRail"))
        sticky = layout.get("_stickyColumn")
        self.assertIsInstance(sticky, dict)
        self.assertEqual(sticky.get("offset"), "2rem")
        self.assertEqual(sticky.get("base"), "56px")
        self.assertEqual(sticky.get("wide"), "76px")
        self.assertEqual(sticky.get("wideMinWidth"), 1080)

    def test_unsanctioned_treatment_stamps_nothing(self):
        layout = {"id": "sticky-x"}
        treatment = {"kind": "sticky-column", "target": "heading"}  # not sanctioned
        with mock.patch.object(cs, "resolve_pattern",
                               return_value=(_pattern([treatment]), "reuse")):
            cs.stamp_pattern_devices({"tokens": {}}, layout, None)
        self.assertIsNone(layout.get("_stickyColumn"))
        self.assertIsNone(layout.get("_sideRail"))

    def test_measure_less_sticky_treatment_keeps_structural_pin(self):
        # a sanctioned sticky treatment with no measured navHeight still reuses the
        # side-rail (position:sticky) but supplies no measured top override.
        layout = {"id": "sticky-x"}
        with mock.patch.object(cs, "resolve_pattern",
                               return_value=(_pattern(
                                   [{"kind": "sticky-column", "sanctioned": True}]),
                                   "reuse")):
            cs.stamp_pattern_devices({"tokens": {}}, layout, None)
        self.assertTrue(layout.get("_sideRail"))
        self.assertEqual(cs.sticky_column_css(layout, "#sec-3"), "")


class StickyColumnCss(unittest.TestCase):
    def test_measured_top_ladder_and_fit_content(self):
        layout = {"_stickyColumn": {"offset": "2rem", "base": "56px",
                                    "wide": "76px", "wideMinWidth": 1080}}
        css = cs.sticky_column_css(layout, "#sec-3")
        self.assertIn("fact-gated: patterns[].specialTreatments sticky-column", css)
        self.assertIn("#sec-3 .cs-siderail-copy { height: fit-content; "
                      "top: calc(56px + 2rem); }", css)
        # the measured nav-height ladder promotes the pin at the wide breakpoint
        self.assertIn("@media (min-width: 1080px) { #sec-3 .cs-siderail-copy "
                      "{ top: calc(76px + 2rem); } }", css)

    def test_no_wide_tier_when_absent(self):
        layout = {"_stickyColumn": {"offset": "2rem", "base": "56px"}}
        css = cs.sticky_column_css(layout, "#sec-5")
        self.assertIn("top: calc(56px + 2rem)", css)
        self.assertNotIn("@media", css)

    def test_no_stamp_is_byte_identical_empty(self):
        # a brand/section without the fact emits nothing (v2/remote parity guard)
        self.assertEqual(cs.sticky_column_css({}, "#sec-1"), "")
        self.assertEqual(cs.sticky_column_css({"_stickyColumn": {}}, "#sec-1"), "")

    def test_sidebar_scaffold_owns_position_sticky(self):
        # the side-rail device is the consumer that satisfies the AS-83 probe —
        # the measured override only adds top/height, never the position itself.
        self.assertIn("position: sticky", cs.SCAFFOLD_SIDERAIL_CSS)


if __name__ == "__main__":
    unittest.main()
