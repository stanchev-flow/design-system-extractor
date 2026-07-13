#!/usr/bin/env python3
"""Fixture tests for the fid6 fidelity batch (workflow cards + partner section):

  - CARD REGISTER LADDER (`_cards_copy` + `compose_features_cards`): a module
    authoring its own eyebrow renders eyebrow→heading(h3)→body→cta as separate
    registers; modules without an eyebrow keep the caption fold byte-identical.
    The preview demo adapter (`_demo_section_for_pattern`) carries item eyebrows.
  - OBSERVED COLUMN TIERS (`_demo_section_for_pattern` grid + `layout_placement_css`):
    the pattern's recorded responsive column counts emit @container tier rules; the
    layout's measured grid gap rides --grid-gutter/--grid-gutter-row.
  - PLATE MEDIA BLEED (SCAFFOLD_CARD_PLATE_CSS): plated module media runs flush to
    the card's top/side edges, top corners rounded, mark media excluded.
  - FLOW HUG-COLLAPSE (`compose_generic_flow` + SCAFFOLD_FLOW_CSS): the 62ch prose
    measure clamps paragraph slots only; headings/eyebrows/actions hug content.
  - SCALED LOGO STRIP (`stamp_pattern_devices` `_logoScale` + the generic-flow
    strip): a logo slot with a measured container fraction renders the row at that
    scale with aspect-weighted marks; missing aspect coverage degrades to the
    structural strip.
  - WIDTH FIDELITY (compose_replica `_content_span` / `band_similarity`): the gate
    reports a content-span ratio that catches centered-stack width collapse.

Run:  ./venv/bin/python -m unittest brand_pipeline.tests.test_fid6_cards_partner
"""
from __future__ import annotations

import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_BRAND_PIPELINE = Path(__file__).resolve().parent.parent
if str(_BRAND_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_BRAND_PIPELINE))
_REPO = _BRAND_PIPELINE.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

import compose_from_composition as cfc  # noqa: E402
import compose_section as cs            # noqa: E402
import component_render as cr           # noqa: E402
import layout_library as ll             # noqa: E402
import render_components_preview as rp  # noqa: E402

FIXTURE_DOC = {
    "brand": {"name": "Fixture"},
    "tokens": {
        "colors": {
            "text/on-primary": {"value": "#111111"},
            "text/on-inverse": {"value": "#ffffff"},
        },
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


def _compose_cards(layout, cards, copy_extra=None, doc=None):
    saved = cs.LAYOUT_COPY
    try:
        cs.LAYOUT_COPY = {**cs.LAYOUT_COPY,
                          layout["id"]: {"eyebrow": "", "heading": "Grid",
                                         "cards": cards, **(copy_extra or {})}}
        return cs.compose_features_cards(doc or FIXTURE_DOC, layout, _ctx(), [], None)
    finally:
        cs.LAYOUT_COPY = saved


# ── card register ladder (eyebrow + heading anatomy) ───────────────────────────────

class CardsCopyEyebrowTest(unittest.TestCase):
    def _section(self, module):
        return {"id": "s", "archetype": "cards", "slots": [
            {"name": "heading", "role": "section heading",
             "copy": {"heading": "Grid"}},
            {"name": "cards", "role": "card modules", "contract": "card",
             "copy": [module]},
        ]}

    def test_authored_eyebrow_carries_separate_registers(self):
        cards = cfc._cards_copy(self._section(
            {"eyebrow": "MCP", "heading": "Deploy agents",
             "body": "Body.", "cta": "Learn more"}))["cards"]
        self.assertEqual(cards[0]["eyebrow"], "MCP")
        self.assertEqual(cards[0]["heading"], "Deploy agents")

    def test_no_eyebrow_keeps_caption_fold(self):
        cards = cfc._cards_copy(self._section(
            {"heading": "Deploy agents", "body": "Body."}))["cards"]
        self.assertNotIn("eyebrow", cards[0])
        # the caption fold is intact — it still drives the plain photo-card
        # render path byte-identically; the explicitly authored heading ALSO
        # passes through as a fact (hubspot-v2 2026-07) because only mark-media
        # feature cards consume it (anatomy or fit:mark), never caption cards.
        self.assertEqual(cards[0]["caption"], "Deploy agents")
        self.assertEqual(cards[0]["heading"], "Deploy agents")


class CardAnatomyRenderTest(unittest.TestCase):
    ANATOMY = [{"eyebrow": "MCP", "heading": "Deploy agents",
                "body": "Body copy.", "link": "Learn more", "asset": "photo-a.webp"}]
    LEGACY = [{"caption": "Deploy agents", "body": "Body copy.",
               "asset": "photo-a.webp"}]

    def test_anatomy_card_renders_register_ladder(self):
        html = _compose_cards({"id": "t"}, self.ANATOMY)
        card = html.split("</article>")[0]
        self.assertIn("cs-module--anatomy", card)
        self.assertIn("c-eyebrow", card)
        self.assertIn("c-heading--h3", card)
        self.assertNotIn("c-caption", card)
        # reading order: eyebrow → heading → body → arrow link
        self.assertLess(card.index("c-eyebrow"), card.index("c-heading--h3"))
        self.assertLess(card.index("c-heading--h3"), card.index("c-paragraph"))
        self.assertLess(card.index("c-paragraph"), card.index("c-arrow-link"))

    def test_legacy_card_keeps_caption_anatomy(self):
        html = _compose_cards({"id": "t"}, self.LEGACY)
        self.assertNotIn("cs-module--anatomy", html)
        self.assertNotIn("c-heading--h3", html)
        self.assertIn("c-caption", html)

    def test_anatomy_rhythm_rides_relational_ladder(self):
        css = cs.SCAFFOLD_CARDS_CSS
        # anatomy modules zero BOTH the flex gap and the seam variable so plate
        # padding math never double-counts a rhythm the ladder owns (2026-07).
        self.assertIn(".cs-module--anatomy { --cs-module-gap: 0rem; gap: 0; }", css)
        self.assertIn("--space-eyebrow-to-heading", css)
        self.assertIn("--space-heading-to-body", css)
        self.assertIn("--space-body-to-cta", css)

    def test_card_heading_rides_declared_register(self):
        # blocks.card slots.heading.register pins the card heading CLASS tier
        # (the measured sub-h3 card register); the TAG stays h3 for the outline.
        doc = {**FIXTURE_DOC, "blocks": {"card": {
            "origin": "extracted",
            "slots": {"heading": {"use": "require", "register": "h5"}}}}}
        html = _compose_cards({"id": "t"}, self.ANATOMY, doc=doc)
        self.assertIn("c-heading--h5", html)
        self.assertNotIn("c-heading--h3", html)
        self.assertIn("<h3", html)
        # bogus register values degrade to the h3 default
        doc["blocks"]["card"]["slots"]["heading"]["register"] = "jumbo"
        self.assertIn("c-heading--h3", _compose_cards({"id": "t"}, self.ANATOMY, doc=doc))

    def test_sub_h3_register_classes_ride_layer1_vars(self):
        self.assertEqual(cr._level_class("h5"), "c-heading--h5")
        self.assertEqual(cr._level_class("h4"), "c-heading--h4")
        css = cr.COMPONENT_CSS
        # fix1 2026-07: sub-h3 tiers gained the per-tier family channel
        # (--c-h5-font behind the display-family fallback) — same contract
        # as h3/h4; family-silent brands resolve identically to before.
        self.assertIn(".c-heading--h5 { font-size: var(--c-h5-size); "
                      "line-height: var(--leading-h5, 1.4em);\n"
                      "  font-family: var(--c-h5-font, var(--c-font-heading)); }",
                      css)
        h5doc = {**FIXTURE_DOC, "tokens": {**FIXTURE_DOC["tokens"],
                 "type": {**FIXTURE_DOC["tokens"]["type"],
                          "h5": {"family": "Inter", "sizeRem": {"base": 1.25}}}}}
        vars_css = cr.component_vars(
            h5doc, FIXTURE_DOC["tokens"]["surfaces"]["surface/primary"],
            surface_role="surface/primary")
        self.assertIn("--c-h5-size: var(--size-h5-base)", vars_css)
        # ladder-less brands keep the structural default
        vars_css = cr.component_vars(
            FIXTURE_DOC, FIXTURE_DOC["tokens"]["surfaces"]["surface/primary"],
            surface_role="surface/primary")
        self.assertIn("--c-h5-size: 1.25rem", vars_css)

    def test_content_measure_rides_brand_container_cap(self):
        # both root-vars twins resolve the shared measure from the brand's
        # measured container LAW first (container-span, fid10), then the measured
        # container-max cap (fid6), 86rem structural fallback.
        import compose_page as cp
        for block in (
                cs.root_vars(FIXTURE_DOC,
                             FIXTURE_DOC["tokens"]["surfaces"]["surface/primary"],
                             display_size="4rem", title_overlap="-2.75rem",
                             surface_role="surface/primary"),
                cp.legacy_root_vars(FIXTURE_DOC,
                                    FIXTURE_DOC["tokens"]["surfaces"]["surface/primary"],
                                    display_size="4rem")):
            self.assertIn("--content-measure: var(--space-container-span, "
                          "var(--space-container-max, 86rem))", block)

    def test_demo_adapter_passes_item_eyebrow(self):
        doc = {**FIXTURE_DOC,
               cs.BRAND_COPY_KEY: {"layout": {"sec": {"items": [
                   {"eyebrow": "MCP", "heading": "Deploy", "body": "B.",
                    "cta": "Go"},
                   {"eyebrow": "API", "heading": "Build", "body": "B2."},
               ]}}}}
        pat = {"id": "p", "useCase": "features",
               "contentShape": {"slots": [
                   {"name": "cards", "role": "card modules", "textLen": "long"}]}}
        layout = {"id": "sec", "archetype": "cards", "slots": [
            {"name": "cards", "role": "card modules",
             "assets": ["photo-a.webp", "photo-b.webp"]}]}
        sec = rp._demo_section_for_pattern(doc, pat, layout)
        mods = next(s for s in sec["slots"] if s.get("contract") == "card")["copy"]
        self.assertEqual([m.get("eyebrow") for m in mods], ["MCP", "API"])


# ── observed column tiers + measured gutter ────────────────────────────────────────

class ObservedColumnsTest(unittest.TestCase):
    def test_demo_grid_carries_gutter_and_tiers(self):
        doc = dict(FIXTURE_DOC)
        pat = {"id": "p", "useCase": "features",
               "responsive": {"columnsTiers": [
                   {"columns": 2, "maxViewportPx": 992, "source": "computed"}]},
               "contentShape": {"slots": []}}
        layout = {"id": "sec", "archetype": "cards",
                  "gridRules": {"columns": "repeat(3)", "gap": "2rem"},
                  "slots": []}
        sec = rp._demo_section_for_pattern(doc, pat, layout)
        self.assertEqual(sec["grid"]["columns"], 3)
        self.assertEqual(sec["grid"]["gutter"], "2rem")
        self.assertEqual(sec["grid"]["columnsTiers"][0]["columns"], 2)
        self.assertEqual(sec["grid"]["columnsTiers"][0]["maxViewportPx"], 992)

    def test_placement_emits_container_tier_rule(self):
        css = cs.layout_placement_css("#sec-5", {
            "_grid": {"columns": 3, "gutter": "2rem",
                      "columnsTiers": [{"columns": 2, "maxViewportPx": 992}]}})
        self.assertIn("--grid-cols: 3;", css)
        self.assertIn("--grid-gutter: 2rem;", css)
        self.assertIn("--grid-gutter-row: 2rem;", css)
        self.assertIn("@container frame (max-width: 992px)", css)
        self.assertIn("#sec-5 .cs-section { --grid-cols: 2; }", css)

    def test_placement_without_tiers_has_no_container_rule(self):
        css = cs.layout_placement_css("#sec-5", {"_grid": {"columns": 3}})
        self.assertNotIn("@container", css)

    def test_cols_grid_row_gap_rides_declared_gutter(self):
        # spacing remediation B6 (2026-07): the N-up card grid's COLUMN seam prefers
        # a declared section gutter, then the brand's card-grid rung
        # (--space-grid-gap), then the shared page gutter (degrade) — the row gap
        # keeps its fid6 declared-gutter chain.
        self.assertIn(".cs-modules--cols { column-gap: var(--grid-gutter-col,\n"
                      "  var(--space-grid-gap, var(--grid-gutter, 6rem)));\n"
                      "  row-gap: var(--grid-gutter-row,",
                      cs.SCAFFOLD_CARDS_CSS)


# ── plate media bleed ──────────────────────────────────────────────────────────────

class PlateMediaBleedTest(unittest.TestCase):
    def test_plate_media_bleeds_to_top_corners_only(self):
        css = cs.SCAFFOLD_CARD_PLATE_CSS
        self.assertIn("--c-plate-pad: var(--space-panel-padding,", css)
        rule = re.search(
            r"\.cs-module--plate > \.cs-module-media:first-child"
            r":not\(\.cs-module-media--mark\) \{([^}]*)\}", css)
        self.assertIsNotNone(rule)
        body = rule.group(1)
        self.assertIn("calc(-1 * var(--c-plate-pad))", body)
        self.assertIn("calc(100% + 2 * var(--c-plate-pad))", body)
        self.assertIn(
            "border-radius: var(--radius-card, 0) var(--radius-card, 0) 0 0", body)


# ── generic-flow hug collapse ──────────────────────────────────────────────────────

def _flow(rendered, layout=None):
    return cs.compose_generic_flow(FIXTURE_DOC, layout or {"id": "f"}, _ctx(),
                                   rendered, None)


class FlowHugCollapseTest(unittest.TestCase):
    def test_prose_clamp_only_on_paragraph_slots(self):
        html = _flow([
            {"contract": "eyebrow", "role": "eyebrow",
             "html": '<p class="c-eyebrow">LABEL</p>'},
            {"contract": "heading", "role": "section heading",
             "html": '<h2 class="c-heading">Heading copy</h2>'},
            {"contract": "paragraph", "role": "supporting paragraph",
             "html": '<p class="c-paragraph">Body.</p>'},
        ])
        self.assertEqual(html.count("cs-flow-item--prose"), 1)
        prose_div = next(l for l in html.splitlines() if "cs-flow-item--prose" in l)
        self.assertIn("c-paragraph", prose_div)
        heading_div = next(l for l in html.splitlines() if "c-heading" in l)
        self.assertNotIn("cs-flow-item--prose", heading_div)

    def test_flow_css_unclamps_non_prose_items(self):
        css = cs.SCAFFOLD_FLOW_CSS
        self.assertIn(".cs-flow-item { max-width: none; }", css)
        # fid11: the prose measure rides the brand's authored description-measure
        # rung when present; 62ch stays the structural degrade in the fallback.
        self.assertIn(".cs-flow-item--prose { max-width: var(--space-body-measure, 62ch); }",
                      css)


# ── scaled logo strip (measured row fraction + real asset aspects) ─────────────────

def _scale_pattern(slot):
    return ll.Pattern(
        id="scale-pattern", use_case="logos", archetype_ref="stack",
        surface_intent="any", intent="test", content_shape={"slots": [slot]},
        special_treatments=[], responsive={}, variant_knobs={},
        origin="extracted", confidence="high", scope="design-language",
        provenance=[])


def _strip_rendered(names, group="logos"):
    return [{"slot": "logo-strip", "contract": "logo", "role": "logo item",
             "group": group,
             "html": (f'<a class="c-logo c-logo--img">'
                      f'<img class="c-logo-img" src="assets/{n}"></a>')}
            for n in names]


class ScaledLogoStripTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.brand_dir = Path(self._tmp.name)
        (self.brand_dir / "assets").mkdir()
        from PIL import Image
        Image.new("RGB", (200, 100)).save(self.brand_dir / "assets" / "logo-a.png")
        Image.new("RGB", (100, 100)).save(self.brand_dir / "assets" / "logo-b.png")

    def tearDown(self):
        self._tmp.cleanup()

    def _stamp(self):
        layout = {"id": "sec"}
        pat = _scale_pattern({
            "name": "logos", "role": "colored partner logos",
            "mediaScale": {"of": "container", "fraction": 0.5},
            "assets": ["logo-a.png", "logo-b.png"]})
        with mock.patch.object(cs, "resolve_pattern", return_value=(pat, "ref")):
            cs.stamp_pattern_devices(FIXTURE_DOC, layout,
                                     self.brand_dir / "brand.yaml")
        return layout

    def test_stamp_measures_fraction_and_aspects(self):
        lay = self._stamp()
        # fid7: per-GROUP map keyed by slot name (an awards strip carries several
        # scaled mark rows — badges + ratings — so one stamp per slot group).
        self.assertEqual(lay["_logoScale"]["logos"]["fraction"], 0.5)
        self.assertEqual(lay["_logoScale"]["logos"]["aspects"],
                         {"logo-a.png": 2.0, "logo-b.png": 1.0})

    def test_scaled_strip_markup_with_aspect_weights(self):
        lay = self._stamp()
        html = _flow(_strip_rendered(["logo-a.png", "logo-b.png"]), lay)
        self.assertIn("cs-logo-strip--scaled", html)
        self.assertIn("--cs-strip-fraction: 0.5", html)
        self.assertIn('style="flex: 2 1 0"', html)
        self.assertIn('style="flex: 1 1 0"', html)

    def test_partial_aspect_coverage_degrades_to_plain_strip(self):
        lay = self._stamp()
        html = _flow(_strip_rendered(["logo-a.png", "logo-missing.png"]), lay)
        self.assertNotIn("cs-logo-strip--scaled", html)
        self.assertIn('<div class="cs-logo-strip">', html)

    def test_non_container_scale_does_not_stamp(self):
        layout = {"id": "sec"}
        pat = _scale_pattern({
            "name": "logos", "role": "colored partner logos",
            "mediaScale": {"of": "column", "fraction": 0.5},
            "assets": ["logo-a.png"]})
        with mock.patch.object(cs, "resolve_pattern", return_value=(pat, "ref")):
            cs.stamp_pattern_devices(FIXTURE_DOC, layout,
                                     self.brand_dir / "brand.yaml")
        self.assertNotIn("_logoScale", layout)

    def test_scaled_strip_css(self):
        css = cs.SCAFFOLD_FLOW_CSS
        self.assertIn(".cs-logo-strip--scaled { flex-wrap: nowrap; "
                      "width: calc(var(--cs-strip-fraction, 0.5) * 100%)", css)
        self.assertIn(".cs-logo-strip--scaled .c-logo-img { height: auto; "
                      "width: 100%; max-width: none; }", css)


# ── replica-gate width fidelity ────────────────────────────────────────────────────

class WidthFidelityTest(unittest.TestCase):
    @staticmethod
    def _band(content_frac: float, w: int = 400, h: int = 80):
        from PIL import Image, ImageDraw
        im = Image.new("RGB", (w, h), (238, 239, 240))
        d = ImageDraw.Draw(im)
        cw = int(w * content_frac)
        x0 = (w - cw) // 2
        d.rectangle([x0, 20, x0 + cw, h - 20], fill=(20, 30, 60))
        return im

    def test_content_span_detects_centered_block(self):
        sys.path.insert(0, str(_BRAND_PIPELINE))
        import compose_replica as crx
        span = crx._content_span(self._band(0.5))
        self.assertAlmostEqual(span, 0.5, delta=0.08)

    def test_band_similarity_reports_width_ratio(self):
        import compose_replica as crx
        m = crx.band_similarity(self._band(0.8), self._band(0.4))
        self.assertIn("widthFidelity", m)
        self.assertAlmostEqual(m["widthFidelity"], 0.5, delta=0.12)
        self.assertGreater(m["srcContentFrac"], m["replicaContentFrac"])


if __name__ == "__main__":
    unittest.main()


# ── fid7: width-collapse fixes (badge/rating rows + conversion stack measure) ──────

class MarkRowScaleTest(unittest.TestCase):
    """Badge/rating rows are mark rows WITHOUT 'logo' in their slot vocabulary — the
    per-group stamp must recognize them (name vocabulary or all-mark assets) and carry
    each row's measured fraction + gap so the flow renders every row at its span."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.brand_dir = Path(self._tmp.name)
        (self.brand_dir / "assets").mkdir()
        from PIL import Image
        for n, size in (("badge-a.png", (130, 150)), ("badge-b.png", (130, 150)),
                        ("rating-a.png", (154, 24)), ("rating-b.png", (212, 24))):
            Image.new("RGB", size).save(self.brand_dir / "assets" / n)

    def tearDown(self):
        self._tmp.cleanup()

    def _pattern(self, slots):
        return ll.Pattern(
            id="awards", use_case="logos", archetype_ref="stack",
            surface_intent="any", intent="test", content_shape={"slots": slots},
            special_treatments=[], responsive={}, variant_knobs={},
            origin="extracted", confidence="high", scope="design-language",
            provenance=[])

    def _stamp(self, slots):
        layout = {"id": "sec"}
        with mock.patch.object(cs, "resolve_pattern",
                               return_value=(self._pattern(slots), "ref")):
            cs.stamp_pattern_devices(FIXTURE_DOC, layout,
                                     self.brand_dir / "brand.yaml")
        return layout

    BADGES = {"name": "badges", "role": "award shield badges",
              "mediaScale": {"of": "container", "fraction": 0.94, "gap": "4rem"},
              "assets": ["badge-a.png", "badge-b.png"]}
    RATINGS = {"name": "ratings", "role": "review-platform rating chips",
               "mediaScale": {"of": "container", "fraction": 0.555, "gap": "2rem"},
               "assets": ["rating-a.png", "rating-b.png"]}

    def test_badge_and_rating_rows_stamp_per_group(self):
        lay = self._stamp([self.BADGES, self.RATINGS])
        scales = lay["_logoScale"]
        self.assertEqual(set(scales), {"badges", "ratings"})
        self.assertEqual(scales["badges"]["fraction"], 0.94)
        self.assertEqual(scales["badges"]["gap"], "4rem")
        self.assertAlmostEqual(scales["badges"]["aspects"]["badge-a.png"],
                               130 / 150, places=3)
        self.assertEqual(scales["ratings"]["gap"], "2rem")

    def test_mark_assets_qualify_slot_without_vocabulary(self):
        slot = {**self.BADGES, "name": "proof", "role": "third-party shields"}
        lay = self._stamp([slot])
        self.assertIn("proof", lay["_logoScale"])

    def test_non_mark_slot_never_stamps(self):
        slot = {"name": "gallery", "role": "photo run",
                "mediaScale": {"of": "container", "fraction": 0.9},
                "assets": ["photo-a.webp"]}
        lay = self._stamp([slot])
        self.assertNotIn("_logoScale", lay)

    def test_bogus_gap_is_dropped_from_stamp(self):
        slot = {**self.BADGES,
                "mediaScale": {"of": "container", "fraction": 0.94,
                               "gap": "expression(alert(1))"}}
        lay = self._stamp([slot])
        self.assertNotIn("gap", lay["_logoScale"]["badges"])

    def test_flow_renders_each_group_at_its_own_scale(self):
        lay = self._stamp([self.BADGES, self.RATINGS])
        rendered = (_strip_rendered(["badge-a.png", "badge-b.png"], group="badges")
                    + _strip_rendered(["rating-a.png", "rating-b.png"], group="ratings"))
        html = _flow(rendered, lay)
        self.assertEqual(html.count("cs-logo-strip--scaled"), 2)
        self.assertIn("--cs-strip-fraction: 0.94; --cs-strip-gap: 4rem;", html)
        self.assertIn("--cs-strip-fraction: 0.555; --cs-strip-gap: 2rem;", html)

    def test_scaled_strip_gap_rides_measured_var(self):
        # pattern's measured row gap → brand strip rung (B8) → uniform rhythm.
        self.assertIn("gap: var(--cs-strip-gap, var(--space-strip-gap, "
                      "var(--c-block-gap)));",
                      cs.SCAFFOLD_FLOW_CSS)


class StackMeasureTest(unittest.TestCase):
    """A centered-stack pattern's measured contentShape.stackMeasure sizes the
    conversion column (and un-clamps the supporting paragraph to span it); layouts
    without the fact keep the classic 46rem/40ch column byte-identically."""

    def _pattern(self, shape):
        return ll.Pattern(
            id="closing", use_case="cta", archetype_ref="stack",
            surface_intent="any", intent="test", content_shape=shape,
            special_treatments=[], responsive={}, variant_knobs={},
            origin="extracted", confidence="high", scope="design-language",
            provenance=[])

    def _stamp(self, shape):
        layout = {"id": "sec"}
        with mock.patch.object(cs, "resolve_pattern",
                               return_value=(self._pattern(shape), "ref")):
            cs.stamp_pattern_devices(FIXTURE_DOC, layout, Path("brand.yaml"))
        return layout

    def test_measured_stack_measure_stamps(self):
        lay = self._stamp({"slots": [], "stackMeasure": {"value": "54.375rem"}})
        self.assertEqual(lay["_stackMeasure"], "54.375rem")

    def test_malformed_measure_never_stamps(self):
        for bad in ("54.375", "calc(100% - 2rem)", "", None, {"px": 870}):
            lay = self._stamp({"slots": [], "stackMeasure": {"value": bad}})
            self.assertNotIn("_stackMeasure", lay, msg=repr(bad))

    def test_conversion_stack_rides_stamped_measure(self):
        html = cs.compose_conversion_stack(
            FIXTURE_DOC, {"id": "sec", "_stackMeasure": "54.375rem"}, _ctx(), [], None)
        self.assertIn('--cs-stack-measure: 54.375rem', html)
        self.assertIn('--c-cta-measure: 100%', html)

    def test_unstamped_conversion_keeps_classic_column(self):
        html = cs.compose_conversion_stack(FIXTURE_DOC, {"id": "sec"}, _ctx(), [], None)
        self.assertIn('<div class="cs-conversion">', html)
        self.assertNotIn("--cs-stack-measure", html)

    def test_conversion_css_rides_var_with_structural_default(self):
        self.assertIn("max-width: var(--cs-stack-measure, 46rem)",
                      cs.SCAFFOLD_CONVERSION_CSS)


class BandPaddingTest(unittest.TestCase):
    """A pattern's measured contentShape.bandPadding overrides the site-average
    section rhythm vars for THAT band only (inline custom properties); layouts
    without the fact keep the rhythm-var padding byte-identically."""

    def _stamp(self, shape):
        layout = {"id": "sec"}
        pat = ll.Pattern(
            id="closing", use_case="cta", archetype_ref="stack",
            surface_intent="any", intent="test", content_shape=shape,
            special_treatments=[], responsive={}, variant_knobs={},
            origin="extracted", confidence="high", scope="design-language",
            provenance=[])
        with mock.patch.object(cs, "resolve_pattern", return_value=(pat, "ref")):
            cs.stamp_pattern_devices(FIXTURE_DOC, layout, Path("brand.yaml"))
        return layout

    def test_measured_band_padding_stamps_valid_lengths_only(self):
        lay = self._stamp({"slots": [], "bandPadding":
                           {"top": "5rem", "bottom": "javascript:x"}})
        self.assertEqual(lay["_bandPadding"], {"top": "5rem"})
        self.assertNotIn("_bandPadding",
                         self._stamp({"slots": [], "bandPadding": {"top": "auto"}}))

    def test_conversion_section_rides_stamped_padding(self):
        html = cs.compose_conversion_stack(
            FIXTURE_DOC,
            {"id": "sec", "_bandPadding": {"top": "5rem", "bottom": "5rem"}},
            _ctx(), [], None)
        self.assertIn("--c-section-pad-top: 5rem;", html)
        self.assertIn("--c-section-pad-bottom: 5rem;", html)

    def test_unstamped_conversion_section_has_no_pad_style(self):
        html = cs.compose_conversion_stack(FIXTURE_DOC, {"id": "sec"}, _ctx(), [], None)
        self.assertNotIn("--c-section-pad-top", html)
