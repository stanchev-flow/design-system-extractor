#!/usr/bin/env python3
"""Unit tests for tools/extract/mine_motion.py — the per-selector motion audit.

Synthetic CSS-rule rows only (no real brand data). Covers the shorthand parsers
(multi-property transitions, var()-driven timings, animation keyword soup),
custom-property resolution, and the audit assembly (censuses + keyframes).

Run:  ./venv/bin/python -m unittest brand_pipeline.tests.test_mine_motion
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_TOOLS_EXTRACT = _REPO / "tools" / "extract"
if str(_TOOLS_EXTRACT) not in sys.path:
    sys.path.insert(0, str(_TOOLS_EXTRACT))

import mine_motion as mm  # noqa: E402


class TransitionParserTests(unittest.TestCase):
    def test_simple_shorthand(self):
        out = mm.parse_transition_value("color .15s")
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["property"], "color")
        self.assertEqual(out[0]["duration"], ".15s")
        self.assertIsNone(out[0]["easing"])

    def test_multi_property_with_easing_and_delay(self):
        out = mm.parse_transition_value(
            "opacity .3s ease-out .1s, transform .3s cubic-bezier(.16, 1, .3, 1)")
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0]["property"], "opacity")
        self.assertEqual(out[0]["duration"], ".3s")
        self.assertEqual(out[0]["easing"], "ease-out")
        self.assertEqual(out[0]["delay"], ".1s")
        # the bezier's internal commas must not split the list
        self.assertEqual(out[1]["property"], "transform")
        self.assertEqual(out[1]["easing"], "cubic-bezier(.16, 1, .3, 1)")

    def test_var_driven_duration_and_easing(self):
        out = mm.parse_transition_value(
            "transform var(--btn-duration-hover-in) var(--btn-easing-enter)")
        self.assertEqual(out[0]["property"], "transform")
        self.assertEqual(out[0]["duration"], "var(--btn-duration-hover-in)")
        self.assertEqual(out[0]["easing"], "var(--btn-easing-enter)")

    def test_modern_linear_stop_list_easing(self):
        # the modern `linear(0, 0.02 2.2%, …)` spring syntax is an easing, and its
        # internal commas/spaces must not split or truncate the entry
        out = mm.parse_transition_value(
            "transform 0.75s linear(0,0.006,0.023 2.2%,0.096 4.8%,1 )")
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["property"], "transform")
        self.assertEqual(out[0]["duration"], "0.75s")
        self.assertEqual(out[0]["easing"], "linear(0,0.006,0.023 2.2%,0.096 4.8%,1 )")


class AnimationParserTests(unittest.TestCase):
    def test_name_duration_keywords(self):
        out = mm.parse_animation_value("marquee-scroll 30s linear infinite")
        self.assertEqual(out[0]["name"], "marquee-scroll")
        self.assertEqual(out[0]["duration"], "30s")
        self.assertEqual(out[0]["easing"], "linear")
        self.assertIn("infinite", out[0]["extras"])

    def test_duration_then_delay(self):
        out = mm.parse_animation_value("pop .4s ease .2s both")
        self.assertEqual(out[0]["duration"], ".4s")
        self.assertEqual(out[0]["delay"], ".2s")
        self.assertIn("both", out[0]["extras"])


class VarResolutionTests(unittest.TestCase):
    VARS = {"--d-in": ".3s", "--ease-enter": "cubic-bezier(0, 0, .2, 1)",
            "--alias": "var(--d-in)"}

    def test_resolves_direct_and_chained(self):
        self.assertEqual(mm.resolve_var("var(--d-in)", self.VARS), ".3s")
        self.assertEqual(mm.resolve_var("var(--alias)", self.VARS), ".3s")

    def test_fallback_used_when_unknown(self):
        self.assertEqual(mm.resolve_var("var(--nope, .2s)", self.VARS), ".2s")

    def test_unknown_without_fallback_stays_symbolic(self):
        self.assertEqual(mm.resolve_var("var(--nope)", self.VARS), "var(--nope)")


class BuildAuditTests(unittest.TestCase):
    ROWS = [
        {"file": "a.css", "media": "", "kind": "rule", "selector": ":root",
         "decls": "--d-in:.3s;--ease-enter:cubic-bezier(0, 0, .2, 1)"},
        {"file": "a.css", "media": "", "kind": "rule", "selector": ".btn",
         "decls": "color:#000;transition:transform var(--d-in) var(--ease-enter)"},
        {"file": "a.css", "media": "", "kind": "rule", "selector": ".card",
         "decls": "transition:opacity .2s ease"},
        {"file": "a.css", "media": "", "kind": "rule", "selector": ".strip",
         "decls": "animation:scroll 30s linear infinite"},
        {"file": "a.css", "media": "", "kind": "keyframes",
         "selector": "@keyframes scroll", "decls": "to{transform:translateX(-50%)}"},
    ]

    def test_audit_shape_and_censuses(self):
        audit = mm.build_audit({"rules": self.ROWS})
        self.assertEqual(audit["schemaVersion"], mm.SCHEMA)
        self.assertEqual(len(audit["transitions"]), 2)
        self.assertEqual(len(audit["animations"]), 1)
        self.assertEqual([k["name"] for k in audit["keyframes"]], ["scroll"])
        # var()-driven duration resolves into the census (.3s -> 300ms)
        self.assertIn("300ms", audit["durationCensus"])
        self.assertIn("200ms", audit["durationCensus"])
        self.assertIn("30000ms", audit["durationCensus"])
        self.assertIn("cubic-bezier(0, 0, .2, 1)", audit["easingCensus"])
        self.assertIn("linear", audit["easingCensus"])
        self.assertIn("--d-in", audit["motionVars"])
        self.assertEqual(audit["jsTimingNotes"], [])


if __name__ == "__main__":
    unittest.main()
