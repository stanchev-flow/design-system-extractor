#!/usr/bin/env python3
"""Regression tests for the fix2 batch (hubspot-v2 2026-07): the brand-owned
COMPONENT-RECIPE layer, the recipe-fact headrail, text-CTA SVG glyphs, measured
ACTION-GROUP layout facts (+ AS-60 and the spacing-audit relationships), and the
logo-strip measured ITEM BOX.

  - RECIPE layer (`layout_library`): recipes load from the brand's OWN
    layout-library.yaml `recipes:`; `resolve_recipe_ref` resolves a pattern's
    `recipeRef: {recipe, variant}`; dangling refs degrade to None.
  - HEADRAIL variants (`compose_section._headrail_html`): recipe variant facts
    (kicker shape/box/icon, rule style, trailing action) drive the device;
    recipe-less rails keep the fix1 prose-vocabulary behavior.
  - ARROW-LINK glyph (`component_render`): a brand-declared textCta glyph asset
    renders the SVG mask device; glyph-less brands keep the unicode arrow.
  - ACTION-GROUP facts (`compose_section`): brand law + per-pattern override CSS,
    declaration stamps (data-ag-*), and the fact-less byte-identical degrade.
  - SPACING AUDIT: `actions.item-gap` resolves the pattern override first, then
    the brand-level fact; fact-less brands classify unmapped.
  - LOGO ITEM BOX (`stamp_pattern_devices` + the strip composers): a measured
    `mediaScale.item` draws fixed contain-fit frames; item-less strips keep the
    aspect-weighted (or plain) row.

Run:  ./venv/bin/python -m unittest brand_pipeline.tests.test_fix2_recipes_actiongroups
"""
from __future__ import annotations

import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest import mock

_BRAND_PIPELINE = Path(__file__).resolve().parent.parent
if str(_BRAND_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_BRAND_PIPELINE))

import component_render as cr    # noqa: E402
import compose_section as cs     # noqa: E402
import layout_library as ll      # noqa: E402
import spacing_audit as sa       # noqa: E402

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


_LIB_YAML = textwrap.dedent("""\
    schemaVersion: layout-patterns.v1
    recipes:
      - id: section-headrail
        name: section headrail
        intent: the house section opener
        anatomy:
          - { slot: kicker, role: leading identity mark, required: true }
          - { slot: rule, role: leader rule, required: true }
          - { slot: trail, role: far-edge action, required: false }
        geometry: { railAlignment: content, railToHeading: 2rem, kickerGap: 1rem }
        variants:
          - id: icon-chip
            useCase: feature-band opener
            kicker: { shape: chip, size: 4.125rem, radius: 1rem, border: true,
                      surface: panel, label: false,
                      icon: { asset: mark.svg, size: 2rem } }
            rule: { style: dotted }
            trail: { present: true, family: outline-ink }
          - id: label-pill
            useCase: editorial opener
            kicker: { shape: pill, radius: 0.25rem, padding: 0.25rem 0.5rem,
                      surface: panel, label: true }
            rule: { style: dotted }
            trail: { present: true }
        usedBy: [rail-pattern]
        origin: extracted
    patterns:
      - id: rail-pattern
        useCase: features
        archetypeRef: cards
        surfaceIntent: primary
        intent: rail-opened cards
        recipeRef: { recipe: section-headrail, variant: icon-chip }
        contentShape: { slots: [] }
        origin: extracted
      - id: dangling-pattern
        useCase: features
        archetypeRef: cards
        surfaceIntent: primary
        intent: dangling ref
        recipeRef: { recipe: no-such-recipe }
        contentShape: { slots: [] }
        origin: extracted
    """)


class _LibDir:
    """Temp brand dir holding a layout-library.yaml (+ brand.yaml stub)."""

    def __enter__(self):
        self._td = tempfile.TemporaryDirectory()
        root = Path(self._td.name)
        (root / "layout-library.yaml").write_text(_LIB_YAML)
        (root / "brand.yaml").write_text("brand: {name: Fixture}\n")
        return root / "brand.yaml"

    def __exit__(self, *exc):
        self._td.cleanup()


# ── recipe layer: load + resolve + degrade ───────────────────────────────────────


class RecipeLayerTest(unittest.TestCase):
    def test_recipes_load_from_brand_library(self):
        with _LibDir() as brand_yaml:
            recipes = ll.load_recipes(brand_yaml)
        self.assertEqual([r.id for r in recipes], ["section-headrail"])
        rec = recipes[0]
        self.assertEqual(len(rec.variants), 2)
        self.assertEqual(rec.used_by, ["rail-pattern"])
        self.assertEqual(rec.geometry.get("railToHeading"), "2rem")

    def test_variant_resolution_and_fallback(self):
        with _LibDir() as brand_yaml:
            rec = ll.get_recipe("section-headrail", brand_yaml)
        self.assertEqual(rec.variant("label-pill").get("id"), "label-pill")
        # miss/None -> first variant; geometry-only recipes resolve {}
        self.assertEqual(rec.variant("nope").get("id"), "icon-chip")
        self.assertEqual(rec.variant(None).get("id"), "icon-chip")

    def test_resolve_recipe_ref_and_dangling_degrade(self):
        with _LibDir() as brand_yaml:
            pats = {p.id: p for p in ll.load_project_patterns(brand_yaml)}
            bound = ll.resolve_recipe_ref(pats["rail-pattern"], brand_yaml)
            dangling = ll.resolve_recipe_ref(pats["dangling-pattern"], brand_yaml)
        self.assertIsNotNone(bound)
        recipe, variant = bound
        self.assertEqual(recipe.id, "section-headrail")
        self.assertEqual(variant.get("id"), "icon-chip")
        self.assertIsNone(dangling)

    def test_recipeless_library_loads_empty(self):
        with tempfile.TemporaryDirectory() as td:
            by = Path(td) / "brand.yaml"
            by.write_text("brand: {name: X}\n")
            (Path(td) / "layout-library.yaml").write_text(
                "schemaVersion: layout-patterns.v1\npatterns: []\n")
            self.assertEqual(ll.load_recipes(by), [])


# ── headrail variants consume recipe facts ───────────────────────────────────────


class HeadrailVariantTest(unittest.TestCase):
    DOC = {**FIXTURE_DOC, cs.ASSET_INVENTORY_KEY: ["mark.svg"]}

    def _rail(self, variant, *, cta="Get started", geometry=None):
        rail = {"note": "", "assets": [], "role": "",
                "recipe": "section-headrail", "variant": variant,
                "variantId": str(variant.get("id") or ""),
                "geometry": geometry or {"railToHeading": "2rem", "kickerGap": "1rem"}}
        eyebrow = cr.render_eyebrow(self.DOC, _ctx(), {"text": "Agents"}) \
            if (variant.get("kicker") or {}).get("label") else ""
        return cs._headrail_html(self.DOC, _ctx(), rail, eyebrow_html=eyebrow,
                                 cta_label=cta, legacy_pill_wrap=False)

    def test_icon_chip_variant(self):
        html = self._rail({"id": "icon-chip",
                           "kicker": {"shape": "chip", "size": "4.125rem",
                                      "radius": "1rem", "border": True,
                                      "surface": "panel", "label": False,
                                      "icon": {"asset": "mark.svg", "size": "2rem"}},
                           "rule": {"style": "dotted"},
                           "trail": {"present": True, "family": "outline-ink"}})
        self.assertIn("cs-headrail-chip", html)
        self.assertIn("--cs-rail-chip-size: 4.125rem", html)
        self.assertIn("--cs-rail-chip-radius: 1rem", html)
        self.assertIn("--cs-rail-chip-icon: 2rem", html)
        self.assertIn('src="assets/mark.svg"', html)
        self.assertIn("cs-headrail-rule--dotted", html)
        self.assertIn("--cs-rail-gap-below: 2rem", html)
        self.assertIn("Get started", html)       # trailing action present

    def test_label_pill_variant(self):
        html = self._rail({"id": "label-pill",
                           "kicker": {"shape": "pill", "radius": "0.25rem",
                                      "padding": "0.25rem 0.5rem",
                                      "surface": "panel", "label": True},
                           "rule": {"style": "dotted"},
                           "trail": {"present": True}})
        self.assertIn("cs-headrail-pill", html)
        self.assertIn("--cs-rail-pill-radius: 0.25rem", html)
        self.assertIn("--cs-rail-pill-pad: 0.25rem 0.5rem", html)
        self.assertIn("Agents", html)            # the label rides the pill

    def test_trail_absent_variant_suppresses_action(self):
        html = self._rail({"id": "badge-with-icon",
                           "kicker": {"shape": "badge", "label": True},
                           "rule": {"style": "dotted"},
                           "trail": {"present": False}}, cta="Get started")
        self.assertNotIn("Get started", html)

    def test_recipeless_rail_keeps_fix1_behavior(self):
        rail = {"note": "pill + dotted rule", "assets": [], "role": "pill label"}
        html = cs._headrail_html(self.DOC, _ctx(), rail,
                                 eyebrow_html='<p class="c-eyebrow">Agents</p>',
                                 cta_label="Go", legacy_pill_wrap=True)
        self.assertIn("cs-headrail-pill", html)   # prose-vocabulary pill wrap
        self.assertIn("cs-headrail-rule--dotted", html)
        self.assertNotIn("--cs-rail-", html)      # no recipe vars invented


# ── arrow-link glyph: declared SVG mask + unicode degrade ────────────────────────


class ArrowGlyphTest(unittest.TestCase):
    def test_declared_glyph_renders_svg_mask(self):
        doc = {**FIXTURE_DOC,
               cs.ASSET_INVENTORY_KEY: ["icon-next.svg"],
               "buttons": {"textCta": {"style": "text-link-arrow",
                                       "glyph": {"asset": "icon-next.svg",
                                                 "size": "1rem"}}}}
        html = cr.render_arrow_link(doc, _ctx(), {"label": "Learn more"})
        self.assertIn("c-arrow--glyph", html)
        self.assertIn("icon-next.svg", html)
        self.assertNotIn("→", html)

    def test_prepared_glyph_renders_inline_svg(self):
        # fix4: prepare_chrome_glyphs sanitizes the harvested artwork and the
        # arrow link emits it INLINE (visible on file:// by construction — the
        # fix2 mask-invisibility class is retired); the data URI stays stamped
        # as the mask degrade for unverified artwork.
        with tempfile.TemporaryDirectory() as td:
            assets = Path(td) / "assets"
            assets.mkdir()
            (assets / "icon-next.svg").write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16">'
                '<path d="M0 8h16"/></svg>')
            doc = {**FIXTURE_DOC,
                   cs.ASSET_INVENTORY_KEY: ["icon-next.svg"],
                   "buttons": {"textCta": {"style": "text-link-arrow",
                                           "glyph": {"asset": "icon-next.svg",
                                                     "size": "1rem"}}}}
            n = cr.prepare_chrome_glyphs(doc, Path(td))
            html = cr.render_arrow_link(doc, _ctx(), {"label": "Learn more"})
        self.assertGreaterEqual(n, 1)
        self.assertIn("c-arrow--glyph", html)
        self.assertNotIn("c-arrow--mask", html)         # inline channel, not mask
        self.assertIn("<svg", html)
        self.assertIn('viewBox="0 0 16 16"', html)      # geometry survives
        self.assertIn('fill="currentColor"', html)      # ink rides the color chain
        self.assertNotIn("data:image/svg+xml", html)    # no dead mask URL emitted
        self.assertNotIn("url('assets/", html)

    def test_missing_asset_degrades_to_unicode(self):
        doc = {**FIXTURE_DOC,
               cs.ASSET_INVENTORY_KEY: [],
               "buttons": {"textCta": {"glyph": {"asset": "icon-next.svg"}}}}
        html = cr.render_arrow_link(doc, _ctx(), {"label": "Learn more"})
        self.assertNotIn("c-arrow--glyph", html)
        self.assertIn("&rarr;", html)

    def test_glyphless_brand_unchanged(self):
        html = cr.render_arrow_link(FIXTURE_DOC, _ctx(), {"label": "Learn more"})
        self.assertNotIn("c-arrow--glyph", html)
        self.assertIn("&rarr;", html)


# ── action-group facts: law, override, stamps, degrade ───────────────────────────


AG_DOC = {**FIXTURE_DOC,
          "layoutGrammar": {"actionGroup": {
              "gap": "1rem", "orientation": "row", "wrap": "wrap",
              "align": "start", "marginAbove": "ladder",
              "registers": ["primary", "secondary"]}}}


class ActionGroupFactsTest(unittest.TestCase):
    def test_brand_law_emits_gap(self):
        css = cs.action_group_css(AG_DOC)
        self.assertIn(".cs-hero-actions, .cs-modules-actions, .cs-conversion-actions "
                      "{ gap: 1rem; }", css)
        # `ladder` marginAbove rides the rung — no margin law emitted
        self.assertNotIn("margin-block-start", css)

    def test_margin_above_length_emits_seam(self):
        doc = {**FIXTURE_DOC,
               "layoutGrammar": {"actionGroup": {"gap": "1rem",
                                                 "marginAbove": "2.5rem"}}}
        self.assertIn("margin-block-start: 2.5rem", cs.action_group_css(doc))

    def test_factless_brand_emits_nothing(self):
        self.assertEqual(cs.action_group_css(FIXTURE_DOC), "")
        self.assertEqual(cs.ag_attrs(FIXTURE_DOC), "")

    def test_stamps_resolve_px(self):
        attrs = cs.ag_attrs(AG_DOC)
        self.assertIn('data-ag-gap="16"', attrs)
        self.assertIn('data-ag-align="start"', attrs)

    def test_pattern_override_wins_stamp(self):
        layout = {"_actionGroup": {"gap": "1.5rem"}}
        attrs = cs.ag_attrs(AG_DOC, layout)
        self.assertIn('data-ag-gap="24"', attrs)
        self.assertIn('data-ag-align="start"', attrs)   # brand fact rides along

    def test_placement_css_emits_pattern_override(self):
        css = cs.layout_placement_css("[data-sec=x]",
                                      {"_actionGroup": {"gap": "1.5rem"}})
        self.assertIn("[data-sec=x] .cs-conversion-actions", css)
        self.assertIn("gap: 1.5rem", css)

    def test_stamp_pattern_devices_stamps_override(self):
        pat = ll.Pattern(
            id="closing", use_case="cta", archetype_ref="stack",
            surface_intent="primary", intent="",
            content_shape={"slots": [],
                           "actionGroup": {"gap": "1.5rem", "align": "start",
                                           "marginAbove": "junk-not-a-length"}},
            special_treatments=[], responsive={}, variant_knobs={},
            origin="extracted", confidence="high", scope="design-language",
            provenance=[])
        layout = {"id": "sec"}
        with mock.patch.object(cs, "resolve_pattern", return_value=(pat, "ref")):
            cs.stamp_pattern_devices(AG_DOC, layout, Path("/nonexistent/brand.yaml"))
        self.assertEqual(layout.get("_actionGroup"),
                         {"gap": "1.5rem", "align": "start"})


class SpacingAuditActionRelTest(unittest.TestCase):
    def _brand_dir(self, td, *, brand_ag=True, pattern_ag=True):
        root = Path(td)
        ag = ("layoutGrammar:\n  actionGroup: { gap: 1rem }\n" if brand_ag else "")
        (root / "brand.yaml").write_text(
            "brand: {name: X}\ntokens: {spacing: {}}\n" + ag)
        pag = ("      actionGroup: { gap: 1.5rem }\n" if pattern_ag else "")
        (root / "layout-library.yaml").write_text(
            "patterns:\n"
            "  - id: closing\n"
            "    useCase: cta\n"
            "    contentShape:\n"
            "      slots: []\n" + pag)
        return root

    def test_steps_resolve_override_then_brand(self):
        with tempfile.TemporaryDirectory() as td:
            book = sa.load_brand_facts(self._brand_dir(td))
            facts = sa.resolve_steps("actions.item-gap", "closing", book)
        self.assertEqual([f.px for f in facts], [24.0, 16.0])

    def test_brand_fact_only(self):
        with tempfile.TemporaryDirectory() as td:
            book = sa.load_brand_facts(self._brand_dir(td, pattern_ag=False))
            facts = sa.resolve_steps("actions.item-gap", "closing", book)
        self.assertEqual([f.px for f in facts], [16.0])

    def test_factless_measures_unmapped(self):
        with tempfile.TemporaryDirectory() as td:
            book = sa.load_brand_facts(
                self._brand_dir(td, brand_ag=False, pattern_ag=False))
            verdict = sa.classify_measurement(
                {"rel": "actions.item-gap", "value": 40.0, "pattern": None,
                 "sec": "sec-1", "note": ""}, book)
        self.assertEqual(verdict["severity"], "unmapped")

    def test_alignment_is_center_family(self):
        with tempfile.TemporaryDirectory() as td:
            book = sa.load_brand_facts(self._brand_dir(td))
            ok = sa.classify_measurement(
                {"rel": "actions.alignment", "value": 0.0, "pattern": None,
                 "sec": "sec-1", "note": "stamped start"}, book)
            off = sa.classify_measurement(
                {"rel": "actions.alignment", "value": 22.0, "pattern": None,
                 "sec": "sec-1", "note": "stamped start"}, book)
        self.assertEqual(ok["severity"], "conform")
        self.assertEqual(off["severity"], "off-ladder")

    def test_audit_js_measures_action_groups(self):
        js = Path(sa.__file__).read_text()
        self.assertIn("actions.item-gap", js)
        self.assertIn("actions.alignment", js)
        self.assertIn("data-ag-align", js)

    def test_edgecut_card_gap_is_column_gap_fact(self):
        # fix2 gate alignment: an edge-cut track's measured `cardGap` IS the
        # module column gap in its device spelling — grid.column-gap resolves it.
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "brand.yaml").write_text(
                "brand: {name: X}\ntokens: {spacing: {}}\n")
            (root / "layout-library.yaml").write_text(
                "patterns:\n"
                "  - id: carousel\n"
                "    useCase: features\n"
                "    contentShape:\n"
                "      deviceGeometry: { cardGap: 17px, cardWidth: 306px }\n"
                "      slots: []\n")
            book = sa.load_brand_facts(root)
            facts = sa.resolve_steps("grid.column-gap", "carousel", book)
        self.assertEqual(facts[0].px, 17.0)

    def test_side_anchored_stack_audits_acting_column(self):
        # fid10 container law: the side anchor releases the stack BOX to the
        # content spine; the auditor measures the widest capped text child.
        js = Path(sa.__file__).read_text()
        self.assertIn("side-anchored: acting column = widest capped text child",
                      js)
        self.assertIn("'flex-start', 'start', 'left', 'flex-end', 'end', 'right'",
                      js)


class SlopAs60Test(unittest.TestCase):
    def test_as60_rule_present_and_declaration_driven(self):
        src = (Path(__file__).resolve().parent.parent / "slop_audit.mjs").read_text()
        self.assertIn("AS-60", src)
        self.assertIn("data-ag-gap", src)
        self.assertIn("data-ag-align", src)
        # anchoring contexts are the sanctioned exception
        self.assertIn('.cs-foot, [data-align="centered"], .cs-hero-panel--center',
                      src)
        # the audit loop scans the stamps, not a hardcoded brand list
        self.assertIn('[data-ag-gap], [data-ag-align]', src)


# ── logo strip: measured item box + degrade ──────────────────────────────────────


class LogoItemBoxTest(unittest.TestCase):
    def _stamp(self, media_scale):
        pat = ll.Pattern(
            id="logos", use_case="logos", archetype_ref="stack",
            surface_intent="primary", intent="",
            content_shape={"slots": [{"name": "logos",
                                      "role": "customer logo row",
                                      "mediaScale": media_scale,
                                      "assets": ["logo-a.svg"]}]},
            special_treatments=[], responsive={}, variant_knobs={},
            origin="extracted", confidence="high", scope="design-language",
            provenance=[])
        layout = {"id": "sec"}
        with mock.patch.object(cs, "resolve_pattern", return_value=(pat, "ref")):
            cs.stamp_pattern_devices(FIXTURE_DOC, layout,
                                     Path("/nonexistent/brand.yaml"))
        return layout.get("_logoScale") or {}

    def test_item_box_rides_the_stamp(self):
        scales = self._stamp({"of": "container", "fraction": 0.96, "gap": "69px",
                              "item": {"width": "153px", "height": "76px"}})
        self.assertEqual(scales.get("logos", {}).get("item"),
                         {"width": "153px", "height": "76px"})

    def test_malformed_item_drops(self):
        scales = self._stamp({"of": "container", "fraction": 0.9,
                              "item": {"width": "wide", "height": None}})
        self.assertNotIn("item", scales.get("logos", {}))

    def test_flow_strip_renders_itembox(self):
        layout = {"id": "sec",
                  "_logoScale": {"media": {"fraction": 0.96, "gap": "69px",
                                           "item": {"width": "153px",
                                                    "height": "76px"}}}}
        rendered = [{"slot": "logo-strip", "contract": "logo", "group": "media",
                     "html": '<a class="c-logo c-logo--img" href="#">'
                             '<img class="c-logo-img" src="assets/logo-a.svg" alt=""></a>'}]
        saved = cs.LAYOUT_COPY
        try:
            cs.LAYOUT_COPY = {**cs.LAYOUT_COPY,
                              "sec": {"eyebrow": "", "heading": "", "body": "",
                                      "cta": "", "items": []}}
            html = cs.compose_generic_flow(FIXTURE_DOC, layout, _ctx(),
                                           rendered, None)
        finally:
            cs.LAYOUT_COPY = saved
        self.assertIn("cs-logo-strip--itembox", html)
        self.assertIn("--cs-strip-item-w: 153px", html)
        self.assertIn("--cs-strip-item-h: 76px", html)
        self.assertIn("--cs-strip-gap: 69px", html)

    def test_itemless_scale_keeps_weighted_row(self):
        layout = {"id": "sec",
                  "_logoScale": {"media": {"fraction": 0.9, "gap": "2rem",
                                           "aspects": {"logo-a.svg": 2.0}}}}
        rendered = [{"slot": "logo-strip", "contract": "logo", "group": "media",
                     "html": '<a class="c-logo c-logo--img" href="#">'
                             '<img class="c-logo-img" src="assets/logo-a.svg" alt=""></a>'}]
        saved = cs.LAYOUT_COPY
        try:
            cs.LAYOUT_COPY = {**cs.LAYOUT_COPY,
                              "sec": {"eyebrow": "", "heading": "", "body": "",
                                      "cta": "", "items": []}}
            html = cs.compose_generic_flow(FIXTURE_DOC, layout, _ctx(),
                                           rendered, None)
        finally:
            cs.LAYOUT_COPY = saved
        self.assertIn("cs-logo-strip--scaled", html)
        self.assertNotIn("cs-logo-strip--itembox", html)

    def test_itembox_css_shipped(self):
        self.assertIn(".cs-logo-strip--itembox", cs.SCAFFOLD_FLOW_CSS)


if __name__ == "__main__":
    unittest.main()
