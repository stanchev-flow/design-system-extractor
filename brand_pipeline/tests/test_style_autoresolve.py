#!/usr/bin/env python3
"""Pass-3 stage-2 AUTO-RESOLUTION tests (2026-07-17).

Before this landing the resolved style-library block only reached a generation
prompt when a caller (an opt-in bakeoff lane) resolved it by hand and passed
``style_directives=...``. This closes that gap: the DEFAULT generate path now
resolves the ALREADY-CHOSEN ``style_id`` through the style-library resolver and
injects ``render_style_directive_block`` output automatically, so presets shape
every generation. These tests pin the wiring at the two seams that carry it —
``_auto_style_directives`` (resolve + render, preset-gated, fail-open) and
``_resolve_style_directives`` (explicit-wins / opt-out precedence) — plus the
``build_prompt`` assembly that consumes the result:

  - PRESET-BACKED style on a real brand → a block with the [[PASS3-STYLE]]
    sentinel and a known preset signal is auto-resolved and injected;
  - EXPLICIT-WINS / OPT-OUT: a caller-supplied ``style_directives`` (including
    ``""`` = suppress) is honored verbatim and never overwritten by
    auto-resolution;
  - BYTE-IDENTITY: a style with NO preset (``dark-mode``) — and any non-library
    style id — yields a prompt byte-identical to the pre-wiring assembly
    (no block); proven against both the opt-out path and a bare pre-wiring call;
  - FAIL-OPEN: a resolver failure / missing library degrades to no block, no
    crash (monkeypatched to raise).

Purely additive to the existing pass-3 contract (test_pass3_prompt_injection.py);
those byte-identity tests must stay green — this file only ADDS to the suite.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

_BRAND_PIPELINE = Path(__file__).resolve().parent.parent
if str(_BRAND_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_BRAND_PIPELINE))

import generate_composition as gc  # noqa: E402
import style_resolver as sr        # noqa: E402

REPO = _BRAND_PIPELINE.parent
HUBSPOT = REPO / "runs" / "hubspot-v2" / "brand" / "brand.yaml"

PRESET_STYLE = "swiss"             # pilot preset, id shared with directives.yaml
NO_PRESET_STYLE = "dark-mode"      # the 1/51 library style with no preset
NON_LIBRARY_STYLE = "corporate-saas-clean"   # a base styles/<id>.md id, not a directive

# a signal that survives the real hubspot brand merge (font/color/space suppressed
# by measured facts, but the uncalibrated marker + signatures always render).
PRESET_SIGNAL = "authored defaults (uncalibrated)"


def _prompt(style_id: str, **kw) -> str:
    doc = gc.load_brand(HUBSPOT)
    seeds = gc.seed_patterns(doc, HUBSPOT)
    return gc.build_prompt("Brief.", HUBSPOT, style_id, seeds, **kw)


# ─────────────────────────── _auto_style_directives (resolve + render) ─────────────

class AutoResolveHelper(unittest.TestCase):
    def test_preset_backed_style_resolves_a_block(self):
        block = gc._auto_style_directives(PRESET_STYLE, HUBSPOT)
        self.assertIsNotNone(block)
        self.assertIn(sr.STYLE_BLOCK_BEGIN, block)
        self.assertIn(sr.STYLE_BLOCK_END, block)
        self.assertIn(PRESET_SIGNAL, block)
        self.assertIn("STYLE DIRECTIVE — Swiss / International", block)

    def test_no_preset_style_returns_none(self):
        self.assertIsNone(gc._auto_style_directives(NO_PRESET_STYLE, HUBSPOT))

    def test_non_library_style_returns_none(self):
        self.assertIsNone(gc._auto_style_directives(NON_LIBRARY_STYLE, HUBSPOT))

    def test_resolver_failure_degrades_to_none(self):
        with mock.patch.object(sr, "load_library",
                               side_effect=RuntimeError("boom")):
            self.assertIsNone(gc._auto_style_directives(PRESET_STYLE, HUBSPOT))

    def test_missing_library_degrades_to_none(self):
        # a resolve_all that raises (e.g. corrupt library) is caught fail-open too
        with mock.patch.object(sr, "resolve_all",
                               side_effect=sr.StyleResolutionError("drift")):
            self.assertIsNone(gc._auto_style_directives(PRESET_STYLE, HUBSPOT))


# ─────────────────────────── _resolve_style_directives (precedence) ────────────────

class ResolveDecision(unittest.TestCase):
    def test_explicit_empty_string_is_honored_opt_out(self):
        """"" means SUPPRESS — auto-resolution must not overwrite it."""
        self.assertEqual(
            gc._resolve_style_directives("", PRESET_STYLE, HUBSPOT), "")

    def test_explicit_caller_value_is_honored_verbatim(self):
        self.assertEqual(
            gc._resolve_style_directives("CALLER BLOCK", PRESET_STYLE, HUBSPOT),
            "CALLER BLOCK")

    def test_opt_out_never_touches_the_library(self):
        """An explicit value short-circuits before any resolver work."""
        with mock.patch.object(gc, "_auto_style_directives") as auto:
            gc._resolve_style_directives("", PRESET_STYLE, HUBSPOT)
            gc._resolve_style_directives("X", PRESET_STYLE, HUBSPOT)
            auto.assert_not_called()

    def test_none_auto_resolves_preset_style(self):
        block = gc._resolve_style_directives(None, PRESET_STYLE, HUBSPOT)
        self.assertIsNotNone(block)
        self.assertIn(sr.STYLE_BLOCK_BEGIN, block)
        self.assertIn(PRESET_SIGNAL, block)

    def test_none_no_preset_style_stays_none(self):
        self.assertIsNone(
            gc._resolve_style_directives(None, NO_PRESET_STYLE, HUBSPOT))

    def test_none_resolver_failure_stays_none(self):
        with mock.patch.object(sr, "load_library",
                               side_effect=RuntimeError("boom")):
            self.assertIsNone(
                gc._resolve_style_directives(None, PRESET_STYLE, HUBSPOT))


# ─────────────────────────── default-path prompt assembly (build_prompt) ───────────

class DefaultPathInjection(unittest.TestCase):
    """The auto-resolved block feeds build_prompt exactly like a caller-supplied
    one — proving the whole default seam assembles as intended."""

    def test_default_path_injects_preset_block(self):
        sd = gc._resolve_style_directives(None, PRESET_STYLE, HUBSPOT)
        p = _prompt(PRESET_STYLE, style_directives=sd)
        self.assertEqual(p.count(sr.STYLE_BLOCK_BEGIN), 1)
        self.assertEqual(p.count(sr.STYLE_BLOCK_END), 1)
        self.assertIn(PRESET_SIGNAL, p)
        # rides in the system prompt, after the seeds, before the user brief
        self.assertLess(p.index("## SEED constraints"), p.index(sr.STYLE_BLOCK_BEGIN))
        self.assertLess(p.index(sr.STYLE_BLOCK_BEGIN), p.index("# USER — brief"))

    def test_opt_out_injects_no_block(self):
        sd = gc._resolve_style_directives("", PRESET_STYLE, HUBSPOT)
        p = _prompt(PRESET_STYLE, style_directives=sd)
        self.assertNotIn(sr.STYLE_BLOCK_BEGIN, p)


class ByteIdentity(unittest.TestCase):
    """No-preset + non-library styles keep the prompt byte-identical to the
    pre-wiring assembly (fact-gated, additive)."""

    def _byte_identical_to_prewiring(self, style_id: str):
        # pre-wiring assembly: build_prompt with no style_directives at all
        base = _prompt(style_id)
        # auto path: whatever _resolve_style_directives returns for None
        sd_auto = gc._resolve_style_directives(None, style_id, HUBSPOT)
        p_auto = _prompt(style_id, style_directives=sd_auto)
        # opt-out path: caller explicitly suppresses
        sd_supp = gc._resolve_style_directives("", style_id, HUBSPOT)
        p_supp = _prompt(style_id, style_directives=sd_supp)
        self.assertEqual(p_auto, base)
        self.assertEqual(p_supp, base)
        self.assertNotIn(sr.STYLE_BLOCK_BEGIN, p_auto)

    def test_no_preset_style_byte_identical(self):
        self._byte_identical_to_prewiring(NO_PRESET_STYLE)

    def test_non_library_style_byte_identical(self):
        self._byte_identical_to_prewiring(NON_LIBRARY_STYLE)

    def test_resolver_failure_byte_identical(self):
        base = _prompt(PRESET_STYLE)
        with mock.patch.object(sr, "load_library",
                               side_effect=RuntimeError("boom")):
            sd = gc._resolve_style_directives(None, PRESET_STYLE, HUBSPOT)
        p = _prompt(PRESET_STYLE, style_directives=sd)
        self.assertEqual(p, base)
        self.assertNotIn(sr.STYLE_BLOCK_BEGIN, p)


if __name__ == "__main__":
    unittest.main(verbosity=2)
