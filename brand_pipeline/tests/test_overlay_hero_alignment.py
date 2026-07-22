#!/usr/bin/env python3
"""Regression tests for the overlay-hero alignment + height fix (2026-07).

The deferred hero-archetype defect: a composed full-bleed `overlay` hero
(`hero-product-canvas-panel` et al.) authored its copy slots with per-slot
``colStart`` and NO panel, so the shared renderer

  1. dropped every co-column text slot as an INDEPENDENT absolutely-positioned
     ``cs-ov-placed`` at the SAME ``top`` — eyebrow/heading/subheading PILED on
     top of each other (the user's "misaligned text"), while the CTA group
     centered separately (split alignment); and
  2. never consumed the measured hero-height fact on the generation path, so the
     bleed canvas fell back to the inflated ``min(90svh, 54rem)`` default (the
     user's "hero is too large") instead of the measured viewport-minus-nav band.

The fix groups co-column front slots into ONE flowing anchored stack (folding a
co-anchored CTA group in reading order), insets a full-bleed hero's left-edge
column to the content-container gutter, ships the stack CSS ONLY when a stack is
present (every stack-less page — incl. replicas — is byte-identical), and promotes
the geometry-neutral hero height mechanic + hero-scoped heading-shrink ladder into
generation so the composed hero fills the measured band.

Run:  ./venv/bin/python -m unittest brand_pipeline.tests.test_overlay_hero_alignment
"""
from __future__ import annotations

import re
import sys
import tempfile
import unittest
from pathlib import Path

_BRAND_PIPELINE = Path(__file__).resolve().parent.parent
if str(_BRAND_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_BRAND_PIPELINE))
_SRC = _BRAND_PIPELINE.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import compose_section as cs                 # noqa: E402
import compose_from_composition as cfc       # noqa: E402

_PROJECT = _BRAND_PIPELINE.parent
_LANE = _PROJECT / "runs" / "hubspot-v3" / "brand" / "compose" / "ai-product-launch"
_BRAND_YAML = _PROJECT / "runs" / "hubspot-v3" / "brand" / "brand.yaml"

_HERO_RE = re.compile(
    r'<section class="cs-section cs-overlay-sec[^"]*">.*?</section>', re.S)


class ScaffoldGating(unittest.TestCase):
    """The copy-stack CSS must NOT live in the shared overlay scaffold: it rides ONLY
    via the build_page gate, so a page with no grouped stack (every replica) is
    byte-identical."""

    def test_stack_css_is_separate_from_shared_overlay_scaffold(self):
        self.assertIn("cs-ov-placed--stack", cs.SCAFFOLD_OVERLAY_STACK_CSS)
        self.assertNotIn("cs-ov-placed--stack", cs.SCAFFOLD_OVERLAY_CSS)

    def test_stack_css_left_aligns_folded_actions(self):
        # a CTA row folded into the copy column aligns to the column edge, not centered
        self.assertIn(".cs-ov-placed--stack > .cs-ov-actions", cs.SCAFFOLD_OVERLAY_STACK_CSS)
        self.assertIn("justify-content: flex-start", cs.SCAFFOLD_OVERLAY_STACK_CSS)


@unittest.skipUnless(_BRAND_YAML.is_file() and (_LANE / "composition.json").is_file(),
                     "hubspot-v3 ai-product-launch composition fixture not present")
class GeneratedHeroRender(unittest.TestCase):
    """End-to-end: render the frozen composition deterministically and assert the hero
    is one coherent anchored stack at the measured height — no overlap, no oversize."""

    @classmethod
    def setUpClass(cls):
        import json
        comp = json.loads((_LANE / "composition.json").read_text())
        cls._tmp = tempfile.TemporaryDirectory()
        out = Path(cls._tmp.name) / "page"
        cfc.render_composition(comp, _BRAND_YAML, out, style_id="corporate-saas-clean")
        cls.html = (out / "index.html").read_text()
        m = _HERO_RE.search(cls.html)
        assert m, "hero <section> not found"
        cls.hero = m.group(0)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_copy_is_one_grouped_stack_not_piled_layers(self):
        # exactly one grouped copy stack, carrying eyebrow + display heading together
        self.assertEqual(self.hero.count('class="cs-ov-placed cs-ov-placed--stack"'), 1)
        stack = re.search(r'cs-ov-placed--stack"[^>]*>(.*?)</div>\s*(?=<div class="cs-ov-placed"|\s*</figure>)',
                          self.hero, re.S)
        self.assertIsNotNone(stack, "grouped stack body not found")
        body = stack.group(1)
        self.assertIn("c-eyebrow", body)
        self.assertIn("c-heading--display", body)
        # the co-anchored CTA group folded INTO the stack (not a separate centered row)
        self.assertIn("cs-ov-actions", body)
        self.assertNotIn("cs-ov-onmedia", self.hero)

    def test_no_two_placed_layers_share_the_same_anchor(self):
        # the overlap bug: multiple cs-ov-placed at the SAME left+top. After the fix each
        # placed container has a DISTINCT anchor (the copy stack vs the counterweight).
        anchors = re.findall(r'class="cs-ov-placed[^"]*" style="(left:[^;]*; top:[^;]*)',
                             self.hero)
        self.assertEqual(len(anchors), len(set(anchors)),
                         f"placed layers still share an anchor (overlap): {anchors}")

    def test_bleed_left_column_insets_to_content_container(self):
        # a full-bleed hero's left-edge copy column must NOT jam the viewport glass; it
        # insets to the shared content-container gutter (never a per-brand literal).
        self.assertIn("cs-ov--bleed", self.hero)
        self.assertRegex(self.hero,
                         r'cs-ov-placed--stack" style="left: max\(var\(--c-section-pad-x')

    def test_hero_height_derives_from_measured_fact_not_inflated_default(self):
        # the generation path now consumes the measured viewport-minus-nav height
        self.assertIn("responsive hero (fact-gated: layouts[].responsive)", self.html)
        self.assertIn("calc(100dvh - var(--c-hero-nav-offset, 0px))", self.html)
        # the hero-scoped heading shrink ladder rides too (mobile display shrink)
        self.assertRegex(self.html,
                         r"@media \(max-width: \d+px\) \{ #sec-0 :is\(h1, \.c-heading--display\)")

    def test_stack_css_rides_only_because_a_stack_is_present(self):
        self.assertIn("overlay copy stack (fact-gated", self.html)


if __name__ == "__main__":
    unittest.main()
