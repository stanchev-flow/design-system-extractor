#!/usr/bin/env python3
"""Fixture-based unit tests for the READABILITY + DECORATION-SALIENCE gate checks
(brand_pipeline/readability.py — wired into onbrand_check.py's composition invariants).

Covers the contrast math, the rgba-over-surface compositing, and the three canonical
fixtures from the task spec:
  - bright ghost on the dark surface        -> decoration-salience FAIL
  - 8%-opacity ink ghost on cream           -> decoration-salience PASS
  - gold #edd580 heading on #3d3728-ish dark -> text-contrast PASS
plus the motivating v4 case (cream ink at opacity .08 on the dark hero) and a
low-contrast body-text failure.

Run:  ./venv/bin/python -m unittest brand_pipeline.tests.test_readability_checks
  or: ./venv/bin/python -m pytest brand_pipeline/tests/test_readability_checks.py
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

_BRAND_PIPELINE = Path(__file__).resolve().parent.parent
if str(_BRAND_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_BRAND_PIPELINE))

import readability as rd  # noqa: E402


def _page(section_css: str, section_html: str, *, paper: str, ink: str,
          extra_root: str = "") -> str:
    """Minimal page mimicking the composer-emitted structure: :root vars, a #sec-0 var
    scope, the shared .cs-section/.cs-ghost rules, and one section of markup."""
    return f"""<!doctype html><html lang="en"><head><style>
:root {{ --bg: {paper}; --text: {ink}; --c-ghost: rgba(31, 26, 20, 0.06); {extra_root} }}
html, body {{ background: var(--bg); color: var(--text); }}
.cs-section {{ background: var(--c-paper); color: var(--c-ink); }}
.cs-ghost {{ position: absolute; z-index: 0; color: var(--c-ghost, rgba(31,26,20,0.06)); }}
.c-heading--display {{ font-size: clamp(8rem, 11cqw, 14.4rem); color: var(--c-ink); }}
.c-heading--accent {{ color: var(--c-accent); }}
.c-paragraph {{ font-size: 0.875rem; color: var(--c-ink-muted); }}
#sec-0 {{ --c-paper: {paper}; --c-ink: {ink}; --c-ink-muted: var(--c-ink); --c-accent: var(--c-ink); }}
{section_css}
</style></head><body>
<div id="sec-0" class="cs-surface" data-layout="hero-v4" data-surface="surface/inverse">
<section class="cs-section">{section_html}</section>
</div></body></html>"""


class ContrastMathTest(unittest.TestCase):
    def test_white_on_black_is_21(self):
        self.assertAlmostEqual(rd.contrast_ratio((255, 255, 255), (0, 0, 0)), 21.0, places=1)

    def test_same_color_is_1(self):
        self.assertAlmostEqual(rd.contrast_ratio((58, 47, 35), (58, 47, 35)), 1.0, places=6)

    def test_symmetry(self):
        a, b = (237, 213, 128), (58, 47, 35)
        self.assertAlmostEqual(rd.contrast_ratio(a, b), rd.contrast_ratio(b, a), places=9)

    def test_gold_on_woodwave_dark_clears_display_floor(self):
        # gold #edd580 heading on the #3d3728-ish dark hero surface ~= 8.1 (>= 3.0)
        ratio = rd.contrast_ratio((0xED, 0xD5, 0x80), (0x3D, 0x37, 0x28))
        self.assertGreater(ratio, rd.TEXT_CONTRAST_DISPLAY_MIN)
        self.assertAlmostEqual(ratio, 8.13, places=1)

    def test_composite_alpha_blend(self):
        # 50% white over black = mid gray, channel-exact source-over
        self.assertEqual(rd.composite((255, 255, 255, 0.5), (0, 0, 0)), (127.5, 127.5, 127.5))

    def test_composite_opaque_and_transparent(self):
        self.assertEqual(rd.composite((10, 20, 30, 1.0), (200, 200, 200)), (10, 20, 30))
        self.assertEqual(rd.composite((10, 20, 30, 0.0), (200, 200, 200)), (200, 200, 200))

    def test_parse_color_forms(self):
        self.assertEqual(rd.parse_color("#3A2F23"), (58, 47, 35, 1.0))
        self.assertEqual(rd.parse_color("rgba(31, 26, 20, 0.06)"), (31, 26, 20, 0.06))
        self.assertEqual(rd.parse_color("#fff"), (255, 255, 255, 1.0))
        self.assertIsNone(rd.parse_color("var(--c-ink)"))
        self.assertIsNone(rd.parse_color("currentcolor"))


class DecorationSalienceTest(unittest.TestCase):
    def test_bright_ghost_on_dark_fails(self):
        """A loud cream watermark on the dark surface must FAIL the salience ceiling."""
        html = _page(
            "#sec-0 .cs-ghost { color: rgba(245, 237, 226, 0.6); }",
            '<div class="cs-ghost" aria-hidden="true">WOODWAVE</div>'
            '<h1 class="c-heading--display">WOODWAVE GALLERY</h1>',
            paper="#3A2F23", ink="#F5EDE2")
        passed, detail = rd.check_decoration_salience(html)
        self.assertFalse(passed, detail)
        self.assertIn("ratio", detail)

    def test_v4_motivating_case_cream_ink_at_8pct_opacity_on_dark_fails(self):
        """The actual v4 emission: ghost color = var(--c-ink) (cream) + opacity 0.08 on
        the dark hero surface -> measured ratio ~1.256 > ceiling."""
        html = _page(
            '[data-layout^="hero-"] .cs-ghost { color: var(--c-ink); opacity: 0.08; }',
            '<div class="cs-ghost" aria-hidden="true">WOODWAVE</div>',
            paper="#3A2F23", ink="#F5EDE2")
        analysis = rd.analyze(html)
        self.assertEqual(len(analysis["decorations"]), 1)
        row = analysis["decorations"][0]
        self.assertAlmostEqual(row["ratio"], 1.256, places=2)
        self.assertFalse(row["passed"])

    def test_8pct_ink_ghost_on_cream_passes(self):
        """The sanctioned treatment: near-ink watermark at 8% alpha on the cream
        surface (~1.17) stays under the ceiling."""
        html = _page(
            "#sec-0 .cs-ghost { color: rgba(31, 26, 20, 0.08); }",
            '<div class="cs-ghost" aria-hidden="true">About</div>',
            paper="#FAF0E8", ink="#1F1A14")
        passed, detail = rd.check_decoration_salience(html)
        self.assertTrue(passed, detail)

    def test_known_good_6pct_ink_ghost_on_cream_passes(self):
        """The deterministic composer default (rgba ink 0.06 via --c-ghost) = 1.124."""
        html = _page(
            "", '<div class="cs-ghost" aria-hidden="true">About</div>',
            paper="#FAF0E8", ink="#1F1A14")
        analysis = rd.analyze(html)
        self.assertEqual(len(analysis["decorations"]), 1)
        row = analysis["decorations"][0]
        self.assertAlmostEqual(row["ratio"], 1.124, places=2)
        self.assertTrue(row["passed"])

    def test_empty_ghost_slot_is_ignored(self):
        html = _page("", '<div class="cs-ghost" aria-hidden="true"></div>',
                     paper="#FAF0E8", ink="#1F1A14")
        passed, detail = rd.check_decoration_salience(html)
        self.assertTrue(passed)
        self.assertIn("no decoration layers", detail)


class TextContrastTest(unittest.TestCase):
    def test_gold_heading_on_dark_passes(self):
        """Gold #edd580 display heading on the ~#3d3728 dark surface -> PASS (>= 3.0)."""
        html = _page(
            "#sec-0 { --c-accent: #edd580; }",
            '<h1 class="c-heading--display c-heading--accent">WOODWAVE GALLERY</h1>',
            paper="#3D3728", ink="#F5EDE2")
        analysis = rd.analyze(html)
        passed, detail = rd.check_text_contrast(html, analysis=analysis)
        self.assertTrue(passed, detail)
        row = next(r for r in analysis["text"] if "c-heading" in r["desc"])
        self.assertEqual(row["tier"], "display")
        self.assertGreater(row["ratio"], rd.TEXT_CONTRAST_DISPLAY_MIN)

    def test_low_contrast_body_text_fails(self):
        """Muted brownish body copy on the dark surface (~1.7) must FAIL (< 4.5)."""
        html = _page(
            "#sec-0 { --c-ink-muted: #5A5248; }",
            '<p class="c-paragraph">An evolving exhibition of woodgrain and light.</p>',
            paper="#3A2F23", ink="#F5EDE2")
        passed, detail = rd.check_text_contrast(html)
        self.assertFalse(passed, detail)
        self.assertIn("c-paragraph", detail)

    def test_text_over_bright_ghost_measures_against_composited_background(self):
        """A decoration layer behind the text brightens the EFFECTIVE background: the
        brand's muted cream text passes cleanly on the bare dark surface but must FAIL
        once a loud cream ghost (60% alpha) is composited behind it."""
        section = ('<div class="cs-ghost" aria-hidden="true">WOODWAVE</div>'
                   '<p class="c-paragraph">An evolving exhibition of woodgrain.</p>')
        # without the ghost: muted #C9BFB2 on #3A2F23 ~ 7.2 -> PASS
        html_plain = _page("#sec-0 { --c-ink-muted: #C9BFB2; }",
                           section.replace('<div class="cs-ghost" aria-hidden="true">'
                                           'WOODWAVE</div>', ""),
                           paper="#3A2F23", ink="#F5EDE2")
        self.assertTrue(rd.check_text_contrast(html_plain)[0])
        # with the bright ghost behind it: effective bg jumps, contrast collapses -> FAIL
        html_ghost = _page(
            "#sec-0 { --c-ink-muted: #C9BFB2; } "
            "#sec-0 .cs-ghost { color: rgba(245, 237, 226, 0.6); }",
            section, paper="#3A2F23", ink="#F5EDE2")
        passed, detail = rd.check_text_contrast(html_ghost)
        self.assertFalse(passed, detail)

    def test_aria_hidden_and_decoration_text_excluded(self):
        """The ghost itself (and any aria-hidden ornament) is never a text-contrast row."""
        html = _page(
            "", '<div class="cs-ghost" aria-hidden="true">WOODWAVE</div>'
                '<span aria-hidden="true">&rarr;</span>',
            paper="#3A2F23", ink="#F5EDE2")
        analysis = rd.analyze(html)
        self.assertEqual(analysis["text"], [])

    def test_unresolvable_elements_skip_not_fail(self):
        """Colors the static pass can't resolve are SKIPPED (conservative), not failed."""
        html = _page(
            ".mystery { color: color-mix(in srgb, red, blue); }",
            '<p class="mystery">Unresolvable paint</p>',
            paper="#FAF0E8", ink="#1F1A14")
        analysis = rd.analyze(html)
        passed, _ = rd.check_text_contrast(html, analysis=analysis)
        self.assertTrue(passed)
        self.assertEqual(analysis["skipped"], 1)


class CascadeResolutionTest(unittest.TestCase):
    def test_panel_rescopes_ink_vars(self):
        """The cream panel re-scopes --c-ink inside a dark band (compose_section's
        .cs-panel), so panel text must be measured against the PANEL, not the band."""
        html = _page(
            ".cs-panel { background: #F7EFE6; --c-ink: #1F1A14; } "
            ".c-heading--h3 { font-size: 1.625rem; color: var(--c-ink); }",
            '<div class="cs-panel"><h2 class="c-heading--h3">Ticket prices</h2></div>',
            paper="#3A2F23", ink="#F5EDE2")
        analysis = rd.analyze(html)
        row = next(r for r in analysis["text"] if "c-heading--h3" in r["desc"])
        self.assertEqual(row["bg"], "#f7efe6")   # the panel, not the dark band
        self.assertEqual(row["color"], "#1f1a14")
        self.assertTrue(row["passed"])

    def test_shim_specificity_beats_base_rule(self):
        """[data-layout^=hero-] .cs-ghost (0,2,0) must beat .cs-ghost (0,1,0)."""
        html = _page(
            '[data-layout^="hero-"] .cs-ghost { color: rgba(245, 237, 226, 0.9); }',
            '<div class="cs-ghost" aria-hidden="true">WOODWAVE</div>',
            paper="#3A2F23", ink="#F5EDE2")
        row = rd.analyze(html)["decorations"][0]
        self.assertFalse(row["passed"])  # 90% cream on dark is way over the ceiling
        self.assertGreater(row["ratio"], 5.0)


if __name__ == "__main__":
    unittest.main()
