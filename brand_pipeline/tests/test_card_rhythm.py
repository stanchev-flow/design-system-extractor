"""Card rhythm regressions (hubspot-v2 2026-07 shared-code batch).

Covers:
- the plate media-well seam never double-counts the module flex gap
  (`--cs-module-gap` subtraction — spacing spec `card.media-to-content` =
  `panel-padding` by construction);
- pinned PLAIN plates ride the ladder body-to-cta rung as their minimum seam
  (spacing spec `card.body-to-actions`), topping up their structural flex gap;
- `pattern_card_rhythm_css` renders a pattern's measured
  `deviceGeometry.cardActionGap` (flow + anatomy, pinned + unpinned);
- the spacing audit resolves `card.body-to-actions` through the pattern fact
  first, ladder rung second;
- `_cards_copy` passes an explicitly authored module heading through without
  demanding a per-card eyebrow;
- the card device's `slots.icon.placement: heading-row` folds mark + heading
  into one flex headrow at the icon slot's measured size;
- side-anchored conversion stacks ride the shared content spine (container law)
  instead of pinning to the section's padding edge.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import compose_section as cs                          # noqa: E402
import layout_library as ll                           # noqa: E402
from compose_from_composition import _cards_copy      # noqa: E402
import spacing_audit as sa                            # noqa: E402


def _pattern(grid_equalize=None, device_geometry=None):
    shape = {"slots": []}
    if grid_equalize is not None:
        shape["gridEqualize"] = grid_equalize
    if device_geometry is not None:
        shape["deviceGeometry"] = device_geometry
    return ll.Pattern(
        id="fx-cards", use_case="features", archetype_ref="cards",
        surface_intent="primary", intent="fixture", content_shape=shape,
        special_treatments=[], responsive={}, variant_knobs={},
        origin="extracted", confidence="high", scope="design-language",
        provenance=[], raw={"id": "fx-cards"})


_STRETCH_PINNED = {"heights": "stretch", "slack": "body", "actionPinned": True}


class PlateMediaSeamTest(unittest.TestCase):
    """The full-bleed well seam is panel-padding BY CONSTRUCTION: the flex gap
    participates in the seam, so the margin subtracts it (anatomy/quote stacks
    declare --cs-module-gap: 0rem and keep the exact pad)."""

    def test_module_gap_is_a_variable(self):
        self.assertIn("--cs-module-gap: 0.9rem", cs.SCAFFOLD_CARDS_CSS)
        self.assertIn(".cs-module--anatomy { --cs-module-gap: 0rem; gap: 0; }",
                      cs.SCAFFOLD_CARDS_CSS)
        self.assertIn(".cs-module--quote { --cs-module-gap: 0rem; gap: 0; }",
                      cs.SCAFFOLD_CARDS_CSS)

    def test_plate_media_seam_subtracts_the_gap(self):
        self.assertIn(
            "margin-block-start: calc(var(--c-plate-pad) - var(--cs-module-gap, 0rem));",
            cs.SCAFFOLD_CARD_PLATE_CSS)


class PinnedPlateMinSeamTest(unittest.TestCase):
    """Plain plates (no anatomy/quote ladder) with pinned actions top their flex
    gap up to the rung; ladder-less brands resolve the calc to zero (degrade)."""

    def test_pinned_plate_rides_the_rung(self):
        css = cs.pattern_equalize_css(_pattern(_STRETCH_PINNED), "#sec-3")
        self.assertIn(
            "#sec-3 .cs-module--plate:not(.cs-module--anatomy):not(.cs-module--quote)"
            " > :has(+ .c-arrow-link:last-child)", css)
        self.assertIn(
            "margin-bottom: calc(var(--space-body-to-cta,"
            " var(--cs-module-gap, 0.9rem)) - var(--cs-module-gap, 0.9rem));", css)

    def test_anatomy_min_seam_unchanged(self):
        css = cs.pattern_equalize_css(_pattern(_STRETCH_PINNED))
        self.assertIn(".cs-module--anatomy > :has(+ .c-arrow-link:last-child), "
                      ".cs-module--anatomy > :has(+ .c-button:last-child) {"
                      " margin-bottom: var(--space-body-to-cta, 0.9rem); }", css)

    def test_unpinned_emits_no_plate_min_seam(self):
        css = cs.pattern_equalize_css(
            _pattern({"heights": "stretch", "slack": "body", "actionPinned": False}))
        self.assertNotIn(".cs-module--plate:not(", css)


class CardActionGapTest(unittest.TestCase):
    """deviceGeometry.cardActionGap: the pattern's measured in-card body→action
    seam renders (and the audit expects) that register, not the section rung."""

    def test_flow_modules_top_up_their_gap(self):
        css = cs.pattern_card_rhythm_css(_pattern(device_geometry={"cardActionGap": "2rem"}))
        self.assertIn(".cs-module:not(.cs-module--anatomy):not(.cs-module--quote)"
                      " > :has(+ .c-arrow-link:last-child)", css)
        self.assertIn("margin-bottom: calc(2rem - var(--cs-module-gap, 0.9rem));", css)

    def test_anatomy_seam_moves_to_preceding_content(self):
        css = cs.pattern_card_rhythm_css(_pattern(device_geometry={"cardActionGap": "3rem"}))
        self.assertIn(".cs-module--anatomy > :has(+ .c-arrow-link:last-child)", css)
        self.assertIn("margin-bottom: 3rem;", css)

    def test_unpinned_anatomy_zeroes_the_ladder_link_margin(self):
        # without a pin, the base ladder puts body-to-cta on the link itself —
        # the measured seam must not stack on top of it.
        css = cs.pattern_card_rhythm_css(_pattern(device_geometry={"cardActionGap": "2rem"}))
        self.assertIn(".cs-module--anatomy > .c-arrow-link:last-child", css)
        self.assertIn("margin-block-start: 0;", css)

    def test_pinned_anatomy_keeps_the_auto_pin(self):
        # actionPinned patterns pin via margin-top:auto (equalize CSS) — the
        # rhythm block must NOT zero the link margin (that would unpin).
        css = cs.pattern_card_rhythm_css(
            _pattern(grid_equalize=_STRETCH_PINNED,
                     device_geometry={"cardActionGap": "3rem"}))
        self.assertNotIn("margin-block-start: 0;", css)

    def test_factless_and_junk_degrade_empty(self):
        self.assertEqual("", cs.pattern_card_rhythm_css(None))
        self.assertEqual("", cs.pattern_card_rhythm_css(_pattern()))
        self.assertEqual("", cs.pattern_card_rhythm_css(
            _pattern(device_geometry={"cardActionGap": "55vw"})))

    def test_audit_resolves_pattern_fact_first(self):
        rel = sa.RELATIONSHIPS["card.body-to-actions"]
        self.assertEqual(("@deviceGeometry.cardActionGap", "body-to-cta"), rel.steps)
        book = sa.FactBook()
        book.pattern_facts["fx-cards"] = {
            "deviceGeometry.cardActionGap": sa.Fact("fx.cardActionGap", 32.0, "pattern:fx")}
        book.steps["body-to-cta"] = sa.Fact("body-to-cta", 56.0, "ladder")
        steps = sa.resolve_steps("card.body-to-actions", "fx-cards", book)
        self.assertEqual([32.0, 56.0], [f.px for f in steps])
        # no pattern fact -> the ladder rung alone
        steps = sa.resolve_steps("card.body-to-actions", "other", book)
        self.assertEqual([56.0], [f.px for f in steps])


class HeadingPassthroughTest(unittest.TestCase):
    """An explicitly authored module heading survives without an eyebrow."""

    def test_authored_heading_rides_through(self):
        section = {"slots": [
            {"name": "cards", "role": "module run", "contract": "card",
             "copy": [{"heading": "Marketing Hub", "body": "Attract leads.",
                       "cta": "Learn more"}]},
        ]}
        card = _cards_copy(section)["cards"][0]
        self.assertEqual("Marketing Hub", card["heading"])
        self.assertNotIn("eyebrow", card)

    def test_caption_fold_unchanged_without_heading_key(self):
        section = {"slots": [
            {"name": "cards", "role": "module run", "contract": "card",
             "copy": [{"caption": "A caption", "body": "Body."}]},
        ]}
        card = _cards_copy(section)["cards"][0]
        self.assertNotIn("heading", card)
        self.assertEqual("A caption", card["caption"])


class HeadrowDeviceTest(unittest.TestCase):
    """slots.icon.placement: heading-row — mark + heading fold into one row."""

    def _doc(self, icon_slot):
        return {
            "brand": {"name": "Fixture"},
            "tokens": {"surfaces": {"surface/primary": {"bg": "#ffffff"}}},
            "blocks": {"card": {"slots": {
                "heading": {"use": "require", "register": "h5"},
                "icon": icon_slot,
            }}},
            "layouts": [],
            # media-treatment FACT: the glyph is a mark, never a media well
            "_assetTags": {"producticons-marketing-icon.webp": {
                "mediaTreatment": {"fit": "mark"}}},
        }

    def _render(self, icon_slot):
        doc = self._doc(icon_slot)
        layout = {"id": "fx", "archetype": "cards", "_edgeCut": None}
        surf = (doc["tokens"]["surfaces"])["surface/primary"]
        ctx = cs.cr.make_context(doc, "surface/primary", surf)
        cs.LAYOUT_COPY["fx"] = {
            "heading": "Grid", "cards": [
                {"heading": "Marketing Hub", "body": "Attract leads.",
                 "link": "Learn more",
                 "asset": "assets/producticons-marketing-icon.webp"}]}
        try:
            return cs.compose_features_cards(doc, layout, ctx, [], None)
        finally:
            cs.LAYOUT_COPY.pop("fx", None)

    def test_declared_headrow_folds_mark_and_heading(self):
        html = self._render({"use": "optional", "placement": "heading-row",
                             "size": "1.5rem"})
        self.assertIn('cs-module-headrow', html)
        self.assertIn("--cs-headrow-mark: 1.5rem", html)
        # the heading rides INSIDE the row, not after the figure
        row = html.split('cs-module-headrow')[1].split("</div>")[0]
        self.assertIn("Marketing Hub", row)

    def test_undeclared_keeps_stacked_mark_row(self):
        html = self._render({"use": "optional"})
        self.assertNotIn('cs-module-headrow', html)

    def test_headrow_css_present(self):
        self.assertIn(".cs-modules .cs-module-headrow { display: flex;",
                      cs.SCAFFOLD_CARD_PLATE_CSS)
        self.assertIn("height: var(--cs-headrow-mark, 1.5rem)",
                      cs.SCAFFOLD_CARD_PLATE_CSS)


class ConversionSideAnchorTest(unittest.TestCase):
    """Container law for side-anchored conversion stacks: the column grows to
    the shared content spine (still centered by the scaffold); the heading keeps
    the stack measure. The old flex-start pinned it to the padding edge."""

    def test_left_anchor_rides_the_spine(self):
        css = cs.layout_placement_css(
            "#sec-9", {}, resolved={"anchor": "left", "source": "pattern"})
        self.assertIn("#sec-9 .cs-conversion { align-items: flex-start; text-align: left;"
                      " max-width: var(--content-measure, 86rem); }", css)
        self.assertIn("#sec-9 .cs-conversion .c-heading {"
                      " max-width: var(--cs-stack-measure, 46rem); }", css)
        # the old rule pinned the whole column to the section's padding edge
        self.assertNotIn(".cs-conversion-sec { justify-content: flex-start; }", css)

    def test_right_anchor_mirrors(self):
        css = cs.layout_placement_css(
            "#sec-9", {}, resolved={"anchor": "right", "source": "pattern"})
        self.assertIn("align-items: flex-end; text-align: right;", css)
        self.assertIn("max-width: var(--content-measure, 86rem);", css)

    def test_centered_anchor_unchanged(self):
        css = cs.layout_placement_css(
            "#sec-9", {}, resolved={"anchor": "centered", "source": "pattern"})
        self.assertIn("#sec-9 .cs-conversion-sec { justify-content: center; }", css)


if __name__ == "__main__":
    unittest.main()
