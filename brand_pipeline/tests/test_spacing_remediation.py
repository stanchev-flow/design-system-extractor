#!/usr/bin/env python3
"""Fixture tests for the spacing-remediation pass (2026-07) — AS-54/55/56 + B8:

  B1  ONE SEAM OWNER (AS-54) — no scaffold rule re-declares `gap` on a header
      cluster the relational ladder already owns (.cs-split-body .c-header
      doubled the eyebrow seam).
  B2  PINNED-SLOT MINIMUM SEAM (AS-55) — covered in test_fid14_grid_equalize;
      here: the quote-card variant pins its attribution with the same guard.
  B3  CONTAINER LAW (AS-56) — .cs-split-intro rides the ONE shared content
      container rule; no local width override survives.
  B4  SPLIT GUTTER — the panel split variant opens the brand's column rung
      between its halves; fact-less brands keep the flush cut (0 degrade).
  B5  LADDER REGISTRY — .cs-split-intro is in _LADDER_STACKS, and every
      `cs-*-intro` stack family the composer emits is either registered or on
      the documented exemption list (the loud guard for NEW families).
  B6  CARD-GRID RUNG — a declared section gutter emits --grid-gutter-col so the
      N-up card grid's column seam outranks the page split gutter.
  B7  RUNG ATTRIBUTION — acc-foot rides the block rhythm (not body→cta);
      interlock-foot rides the content-to-actions register (stack-lg).
  B8  FACT CAPTURE — the new generic spacing keys resolve in the spacing
      auditor, emit as --space-* vars, and the scaffolds consume each with a
      structural degrade; the remote brand carries the mined facts.

Run:  ./venv/bin/python -m unittest brand_pipeline.tests.test_spacing_remediation
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

_BRAND_PIPELINE = Path(__file__).resolve().parent.parent
if str(_BRAND_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_BRAND_PIPELINE))

import component_render as cr    # noqa: E402
import compose_section as cs     # noqa: E402
import layout_library as ll      # noqa: E402
import spacing_audit as sa       # noqa: E402

_REMOTE = _BRAND_PIPELINE.parent / "runs" / "remote" / "brand" / "brand.yaml"

FIXTURE_DOC = {
    "brand": {"name": "Fixture"},
    "tokens": {
        "colors": {"text/on-primary": {"value": "#111111"}},
        "surfaces": {
            "surface/primary": {"bg": "#ffffff", "textPrimary": "text/on-primary"},
        },
        "type": {"body": {"family": "Inter", "sizeRem": {"base": 1.0}}},
        "spacing": {},
    },
}


def _ctx():
    return cr.make_context(FIXTURE_DOC, "surface/primary",
                           FIXTURE_DOC["tokens"]["surfaces"]["surface/primary"])


def _rule_bodies(css: str, selector_fragment: str) -> list[str]:
    """All rule bodies whose selector list contains the fragment."""
    out = []
    for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", re.sub(r"/\*.*?\*/", "", css, flags=re.S)):
        if selector_fragment in m.group(1):
            out.append(m.group(2))
    return out


# ── B1: one mechanic owns the eyebrow→heading seam ──────────────────────────────────

class SingleSeamOwnerTest(unittest.TestCase):
    def test_split_body_header_declares_no_gap(self):
        bodies = _rule_bodies(cs.SCAFFOLD_SPLIT_CSS, ".cs-split-body .c-header")
        for body in bodies:
            self.assertNotRegex(body, r"(^|[^-])gap\s*:", body)

    def test_no_scaffold_re_gaps_a_ladder_owned_header_cluster(self):
        # AS-54 guard: `.c-header` inside any cs- scope must not re-declare gap in
        # the scaffold constants — the base .c-header + the ladder own that seam.
        for name in dir(cs):
            if not name.startswith("SCAFFOLD_") or not name.endswith("_CSS"):
                continue
            css = getattr(cs, name)
            if not isinstance(css, str):
                continue
            for body in _rule_bodies(css, " .c-header"):
                self.assertNotRegex(
                    body, r"(^|[^-])gap\s*:",
                    f"{name} re-declares gap on a .c-header cluster (AS-54)")


# ── B2: pinned attribution keeps the quote rung ─────────────────────────────────────

def _pattern(grid_equalize):
    return ll.Pattern(
        id="fx-grid", use_case="features", archetype_ref="grid",
        surface_intent="primary", intent="fixture",
        content_shape={"slots": [], "gridEqualize": grid_equalize},
        special_treatments=[], responsive={}, variant_knobs={},
        origin="extracted", confidence="high", scope="design-language",
        provenance=[], raw={"id": "fx-grid"})


class PinnedQuoteSeamTest(unittest.TestCase):
    def test_quote_attribution_pin_keeps_the_quote_rung(self):
        css = cs.pattern_equalize_css(
            _pattern({"heights": "stretch", "slack": "body", "actionPinned": True}))
        self.assertIn(".cs-module--quote > :has(+ .c-person:last-child) {"
                      " margin-bottom: var(--space-quote-to-attribution, 0.9rem); }",
                      css)


# ── B3: container law ────────────────────────────────────────────────────────────────

class ContainerLawTest(unittest.TestCase):
    def _shared_container_selectors(self) -> str:
        m = re.search(
            r"([^{}]+)\{[^{}]*max-width: var\(--content-measure, 86rem\); margin-inline: auto;",
            cs.SCAFFOLD_BASE_CSS)
        self.assertIsNotNone(m, "shared content container rule not found")
        return m.group(1)

    def test_split_intro_joined_the_shared_container(self):
        self.assertIn(".cs-split-intro", self._shared_container_selectors())

    def test_no_local_width_override_survives(self):
        # the intro's OWN box: no width re-declaration (child measure caps are fine)
        for m in re.finditer(r"([^{}]+)\{([^{}]*)\}",
                             re.sub(r"/\*.*?\*/", "", cs.SCAFFOLD_SPLIT_CSS, flags=re.S)):
            sels = [s.strip() for s in m.group(1).split(",")]
            if ".cs-split-intro" in sels:
                self.assertNotIn("max-width", m.group(2))

    def test_known_page_wrappers_stay_registered(self):
        # AS-56: the intro/grid wrappers that span the page column all ride the
        # ONE shared rule — removal is a loud failure here.
        sels = self._shared_container_selectors()
        for wrapper in (".cs-modules-intro", ".cs-modules", ".cs-interlock",
                        ".cs-statement-grid", ".cs-quote-grid", ".cs-collage-grid"):
            self.assertIn(wrapper, sels, f"{wrapper} escaped the container law")


# ── B4: the panel split's column gutter ──────────────────────────────────────────────

class PanelSplitGutterTest(unittest.TestCase):
    def _band(self, copy):
        layout = {"id": "band-fx", "archetype": "split"}
        saved = cs.LAYOUT_COPY
        cs.LAYOUT_COPY = {**cs.LAYOUT_COPY, "band-fx": copy}
        try:
            return cs.compose_info_band(FIXTURE_DOC, layout, _ctx(), [], None)
        finally:
            cs.LAYOUT_COPY = saved

    def test_panel_band_carries_the_variant_class(self):
        html = self._band({"eyebrow": "E", "heading": "H", "panelTitle": "Ledger",
                           "rows": [("A", "1"), ("B", "2")], "cta": "Go"})
        self.assertIn('<div class="cs-split cs-split--panel">', html)

    def test_classic_split_stays_flush(self):
        html = self._band({"eyebrow": "E", "heading": "H", "panelTitle": "",
                           "rows": [], "cta": "", "body": "Supporting."})
        self.assertIn('<div class="cs-split">', html)
        self.assertNotIn("cs-split--panel", html)

    def test_gutter_rides_the_column_rung_with_flush_degrade(self):
        self.assertIn(".cs-split--panel { column-gap: "
                      "var(--space-column-to-column, 0); }",
                      cs.SCAFFOLD_SPLIT_CSS)


# ── B5: the ladder registry + loud guard for new stack families ─────────────────────

class LadderRegistryTest(unittest.TestCase):
    # Stack-shaped wrappers that legitimately live OUTSIDE _LADDER_STACKS. Add an
    # entry ONLY with a reason: the family must own its seams some other way.
    EXEMPT = {
        # its seams are the ladder's own dedicated rules (margin-bottom rhythm +
        # the .c-header cluster pair margins); registering it would double them.
        "cs-modules-intro",
    }

    def test_split_intro_is_registered(self):
        self.assertIn(".cs-split-intro", cs._LADDER_STACKS)

    def test_ladder_css_owns_the_split_intro_seams(self):
        doc = {"brand": {"name": "Fixture"}, "tokens": {"spacing": {
            "eyebrow-to-heading": {"value": "0.75rem"},
            "heading-to-body": {"value": "1rem"},
            "body-to-cta": {"value": "2rem"}}}}
        css = cs.relational_ladder_css(doc)
        self.assertIn(".cs-split-intro", css)
        # the bare heading + body pair (no .c-header wrap) gets the rung
        self.assertIn(".cs-split-intro > .c-heading + .c-paragraph", css)

    def test_every_emitted_intro_family_is_registered_or_exempt(self):
        # THE LOUD GUARD: a new `cs-*-intro` stack family composed into markup
        # must join _LADDER_STACKS (or the documented exemption list above) —
        # otherwise its pair seams silently render 0px under ladder brands.
        src = Path(cs.__file__).read_text()
        emitted = set(re.findall(r'class="[^"]*\b(cs-[a-z-]+-intro)\b', src))
        registered = {s.lstrip(".") for s in cs._LADDER_STACKS}
        for family in sorted(emitted):
            self.assertTrue(
                family in registered or family in self.EXEMPT,
                f"NEW stack family .{family} is neither in _LADDER_STACKS nor "
                f"exempted with a reason (test_spacing_remediation.LadderRegistryTest)")


# ── B6: card grids get their own column rung ─────────────────────────────────────────

class CardGridRungTest(unittest.TestCase):
    def test_declared_gutter_drives_the_cols_var(self):
        css = cs.layout_placement_css("#sec-5", {"_grid": {"columns": 3, "gutter": "2rem"}})
        self.assertIn("--grid-gutter-col: 2rem;", css)

    def test_undeclared_gutter_emits_no_cols_var(self):
        css = cs.layout_placement_css("#sec-5", {"_grid": {"columns": 3}})
        self.assertNotIn("--grid-gutter-col", css)

    def test_cols_grid_prefers_the_card_grid_rung(self):
        # declared gutter → brand card-grid rung → page split gutter (degrade).
        self.assertIn("column-gap: var(--grid-gutter-col,\n"
                      "  var(--space-grid-gap, var(--grid-gutter, 6rem)))",
                      cs.SCAFFOLD_CARDS_CSS)


# ── B7: rung attribution ─────────────────────────────────────────────────────────────

class RungAttributionTest(unittest.TestCase):
    def test_acc_foot_rides_the_block_rhythm(self):
        self.assertIn(".cs-acc-foot { margin-top: var(--space-block-to-block,\n"
                      "    var(--space-body-to-cta, calc(3 * var(--baseline))));",
                      cs.SCAFFOLD_ACCORDION_CSS)

    def test_plain_split_foot_rides_the_content_to_actions_register(self):
        # AS-58: support/action foot clusters are incompatible with interlock and
        # degrade to the ordinary split, where the body→action seam remains explicit.
        self.assertNotIn(".cs-interlock-foot", cs.SCAFFOLD_INTERLOCK_CSS)
        self.assertIn(".cs-media-split-copy .c-paragraph + .c-arrow-link",
                      cs.SCAFFOLD_MEDIA_SPLIT_CSS)
        self.assertIn("var(--space-body-to-cta, var(--c-block-gap))",
                      cs.SCAFFOLD_MEDIA_SPLIT_CSS)


# ── B8: new fact keys — auditor resolution + scaffold consumption + brand capture ───

class FactCaptureTest(unittest.TestCase):
    NEW_KEYS = {
        "form.field-gap": "field-to-field",
        "form.label-to-input": "field-label-gap",
        "form.stack-gap": "form-stack",
        "list.item-inset": "list-item-inset",
        "card.mark-to-quote": "mark-to-quote",
        "card.body-to-author": "quote-to-attribution",
    }

    def test_auditor_resolves_the_new_relationships(self):
        for rel, fact in self.NEW_KEYS.items():
            self.assertIn(rel, sa.RELATIONSHIPS, rel)
            self.assertIn(fact, sa.RELATIONSHIPS[rel].steps, rel)
        # list stride + strip gap prefer the pattern stamp, then the brand fact
        self.assertEqual(("@list.itemGap", "list-item-gap"),
                         sa.RELATIONSHIPS["list.item-gap"].steps)
        self.assertEqual(("@strip.gaps", "strip-gap"),
                         sa.RELATIONSHIPS["strip.gap"].steps)

    def test_scaffolds_consume_each_fact_with_a_degrade(self):
        cases = [
            (cs.SCAFFOLD_SIGNUP_CSS, "var(--space-form-stack, calc(2 * var(--baseline)))"),
            (cs.SCAFFOLD_SIGNUP_CSS, "var(--space-field-to-field, calc(2 * var(--baseline)))"),
            (cs.SCAFFOLD_SIGNUP_CSS, "var(--space-field-label-gap, 0.5em)"),
            (cs.SCAFFOLD_FAQ_CSS, "var(--space-list-item-inset, 1.5rem)"),
            (cs.SCAFFOLD_FAQ_CSS, "var(--space-list-item-gap, 0)"),
            (cs.SCAFFOLD_CARDS_CSS, "var(--space-mark-to-quote, 0.9rem)"),
            (cs.SCAFFOLD_CARDS_CSS, "var(--space-quote-to-attribution, 0.9rem)"),
            (cs.SCAFFOLD_FLOW_CSS, "var(--space-strip-gap, var(--c-block-gap))"),
            (cr.COMPONENT_CSS, "var(--c-form-gap, var(--space-form-stack, 1.25rem))"),
        ]
        for css, needle in cases:
            self.assertIn(needle, css, needle)

    @unittest.skipUnless(_REMOTE.exists(), "remote brand not on disk")
    def test_remote_brand_carries_the_mined_facts(self):
        import yaml
        spacing = (yaml.safe_load(_REMOTE.read_text())["tokens"]["spacing"])
        for key in ("field-to-field", "field-label-gap", "form-stack",
                    "list-item-gap", "list-item-inset", "mark-to-quote",
                    "quote-to-attribution", "strip-gap"):
            node = spacing.get(key)
            self.assertIsInstance(node, dict, key)
            self.assertTrue(str(node.get("value") or "").strip(), key)
            self.assertEqual("mapped", node.get("status"), key)
            self.assertTrue(str(node.get("role") or "").strip(), key)


if __name__ == "__main__":
    unittest.main()
