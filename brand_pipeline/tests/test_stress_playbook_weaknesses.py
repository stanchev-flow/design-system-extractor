#!/usr/bin/env python3
"""Regression locks for the stress-playbook weakness batch (W1–W12, 2026-07).

The stress-test page (runs/remote/brand/compose/stress-playbook) deliberately
exercised rare contract/composer/gate paths and documented 12 weaknesses in its
REPORT.md. Each fix here is SYSTEM-LEVEL and palette-agnostic; these tests pin the
behavior so a weakness cannot silently return:

  W1  banner backdrop-aware paint     — bridge prefers the composited bgEffective,
                                        keeps the raw alpha declaration as bgRaw
  W3  AS-23 art exemption             — slop_audit's AS-23 skips the renderer's
                                        deliberate `.c-image--art` no-hatch contract
  W4  stat + table renderers          — real registers (value on the h2 chain, ruled
                                        semantic table), registered contracts, banding
  W5  heading demotion below the hero — level-less non-hero headings ride the brand's
                                        measured section tier; authored level wins
                                        (AS-51)
  W6  pattern retrieval               — declared useCase wins, no hero default,
                                        retrieval outcome is a visible stamp
  W7  quote-card phantom media        — person-attributed cards never inherit the
                                        defaultArt backfill (AS-52)
  W8  split-accordion action slot     — the authored cta renders as the list-column
                                        foot, never silently dropped (AS-53)
  W9  interlock authored alt          — the slot's own asset.alt rides through
  W12 real textarea                   — the declared multiline field renders a
                                        <textarea> on the brand input anatomy chain

(W2 is a provenance-comment fix verified by the token-provenance gate; W10 resolved
into W4 — no layout-library entry is fabricated; W11 is locked via the emitted-html
marker-count parity assert below.)

Run:  ./venv/bin/python -m unittest brand_pipeline.tests.test_stress_playbook_weaknesses
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

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

# a brand whose measured ladder carries the canonical h2 tier (section_heading_level
# resolves "h2"); the fixture above deliberately lacks it (resolves "display").
LADDER_DOC = {
    **FIXTURE_DOC,
    "meta": {"canonicalTier": {"h2": "2.5rem"}},
    "tokens": {
        **FIXTURE_DOC["tokens"],
        "type": {"body": {"family": "Inter", "sizeRem": {"base": 1.0}},
                 "h2": {"family": "Inter", "sizeRem": {"base": 2.5}}},
    },
}


def _ctx(doc=None):
    d = doc or FIXTURE_DOC
    return cr.make_context(d, "surface/primary", d["tokens"]["surfaces"]["surface/primary"])


# ── W4: stat + table renderers ───────────────────────────────────────────────────

class StatRendererTest(unittest.TestCase):
    def test_value_and_label_ride_their_registers(self):
        html = cr.render_stat(FIXTURE_DOC, _ctx(), {"value": "170+", "label": "Countries"})
        self.assertIn('class="c-stat"', html)
        self.assertIn('<span class="c-stat-value">170+</span>', html)
        self.assertIn('<span class="c-stat-label">Countries</span>', html)

    def test_prefix_suffix_wrap_the_value(self):
        html = cr.render_stat(FIXTURE_DOC, _ctx(),
                              {"value": "99.9", "prefix": "~", "suffix": "%"})
        self.assertIn("~99.9%", html)

    def test_valueless_stat_elides(self):
        self.assertEqual("", cr.render_stat(FIXTURE_DOC, _ctx(), {"label": "orphan"}))

    def test_contract_registration_and_alias(self):
        self.assertIs(cr.PRIMITIVE_RENDERERS.get("stat"), cr.render_stat)
        self.assertIs(cr.PRIMITIVE_RENDERERS.get("metric"), cr.render_stat)

    def test_value_register_is_the_h2_chain_not_eyebrow(self):
        # the weakness: values fell through the caption fold at eyebrow size.
        rule = cr.COMPONENT_CSS[cr.COMPONENT_CSS.index(".c-stat-value"):]
        rule = rule[:rule.index("}")]
        self.assertIn("var(--c-stat-size, var(--c-h2-size))", rule)
        self.assertNotIn("eyebrow", rule)


class TableRendererTest(unittest.TestCase):
    ROWS = [["Coverage", "185 countries", "12 countries"],
            ["Payroll", "Included", "Add-on"]]

    def test_semantic_table_with_caption_columns_rows(self):
        html = cr.render_table(FIXTURE_DOC, _ctx(), {
            "caption": "Compare plans", "columns": ["", "Us", "Them"],
            "rows": self.ROWS})
        self.assertIn('<table class="c-table">', html)
        self.assertIn("<caption>Compare plans</caption>", html)
        self.assertIn('<th scope="col">Us</th>', html)
        self.assertIn('<th scope="row">Coverage</th>', html)
        self.assertIn("<td>185 countries</td>", html)

    def test_dict_rows_render_label_value(self):
        html = cr.render_table(FIXTURE_DOC, _ctx(), {
            "rows": [{"label": "Setup", "value": "Same day"}]})
        self.assertIn('<th scope="row">Setup</th>', html)
        self.assertIn("<td>Same day</td>", html)

    def test_rowless_table_elides(self):
        self.assertEqual("", cr.render_table(FIXTURE_DOC, _ctx(), {"caption": "x"}))
        self.assertEqual("", cr.render_table(FIXTURE_DOC, _ctx(), {"rows": [[""], []]}))

    def test_block_registration(self):
        self.assertIs(cr.BLOCK_RENDERERS.get("table"), cr.render_table)


class StatAdapterAndBandingTest(unittest.TestCase):
    def test_repeatable_stat_slot_expands_to_stat_contract(self):
        layout = cfc.composition_to_layout({
            "id": "s", "useCase": "stats", "archetype": "stack", "slots": [
                {"name": "metrics", "role": "stat band", "contract": "stat",
                 "copy": [{"value": "170+", "label": "Countries"},
                          {"value": "99.9%", "label": "Uptime"}]}]})
        stats = [m for m in (layout.get("blockMapping") or [])
                 if m.get("contract") == "stat"]
        self.assertEqual(2, len(stats))
        self.assertEqual("170+", stats[0]["usage"]["value"])
        self.assertEqual("Countries", stats[0]["usage"]["label"])
        # banding key: consecutive stats group under the authored slot name —
        # and the old failure shape (caption fold at eyebrow size) is gone.
        self.assertEqual("metrics", stats[0]["group"])
        self.assertFalse([m for m in layout["blockMapping"]
                          if m.get("contract") == "caption"])

    def test_inline_props_route_stat_and_table(self):
        p = cs._inline_props("stat", "stat 1", {"value": "24", "label": "Hours"}, _ctx())
        self.assertEqual({"value": "24", "label": "Hours",
                          "prefix": None, "suffix": None}, p)
        p = cs._inline_props("table", "compare", {"rows": [["a", "b"]]}, _ctx())
        self.assertEqual([["a", "b"]], p["rows"])

    def test_generic_flow_bands_consecutive_stats(self):
        layout = {"id": "stats-sec", "archetype": "flow", "blockMapping": [
            {"slot": "metrics", "role": "stat 1", "contract": "stat",
             "usage": {"value": "170+", "label": "Countries"}, "group": "metrics"},
            {"slot": "metrics", "role": "stat 2", "contract": "stat",
             "usage": {"value": "99.9%", "label": "Uptime"}, "group": "metrics"},
            {"slot": "metrics", "role": "stat 3", "contract": "stat",
             "usage": {"value": "24h", "label": "Support"}, "group": "metrics"},
        ]}
        rendered = cs.render_slots(FIXTURE_DOC, layout, _ctx())
        html = cs.compose_generic_flow(FIXTURE_DOC, layout, _ctx(), rendered, None)
        self.assertIn('class="cs-stat-band"', html)
        self.assertIn("--cs-stat-cols: 3", html)
        self.assertEqual(3, html.count("cs-stat-band-item"))
        # one band, not three stacked flow children
        self.assertEqual(1, html.count('class="cs-stat-band"'))

    def test_stat_band_css_ships_in_flow_scaffold(self):
        self.assertIn(".cs-stat-band", cs.SCAFFOLD_FLOW_CSS)
        self.assertIn("repeat(var(--cs-stat-cols, 4)", cs.SCAFFOLD_FLOW_CSS)


# ── W5 / AS-51: heading-level demotion below the hero ────────────────────────────

class HeadingDemotionTest(unittest.TestCase):
    def _section(self, level=None):
        copy = {"heading": "Numbers that matter"}
        if level:
            copy["level"] = level
        return {"id": "nn", "useCase": "stats", "archetype": "stack",
                "slots": [{"name": "head", "role": "heading",
                           "contract": "heading", "copy": copy}]}

    def test_levelless_non_hero_heading_demotes_to_measured_tier(self):
        layout, merged, sect_copy = cfc.adapt_brand_section(self._section(), LADDER_DOC)
        self.assertIsNone(sect_copy)
        m = next(m for m in layout["blockMapping"]
                 if (m.get("contract") or "") == "heading")
        self.assertEqual("h2", m["usage"]["level"])
        self.assertEqual("h2", merged.get("headingLevel"))

    def test_authored_level_always_wins(self):
        layout, _, _ = cfc.adapt_brand_section(self._section(level="display"),
                                               LADDER_DOC)
        m = next(m for m in layout["blockMapping"]
                 if (m.get("contract") or "") == "heading")
        self.assertEqual("display", m["usage"]["level"])

    def test_ladderless_brand_keeps_the_display_degrade(self):
        layout, _, _ = cfc.adapt_brand_section(self._section(), FIXTURE_DOC)
        m = next(m for m in layout["blockMapping"]
                 if (m.get("contract") or "") == "heading")
        self.assertEqual("display", m["usage"]["level"])

    def test_hero_section_is_never_demoted(self):
        hero = {"id": "hero", "useCase": "hero", "archetype": "stack",
                "slots": [{"name": "head", "role": "hero heading",
                           "contract": "heading", "copy": {"heading": "Big"}}]}
        layout, _, sect_copy = cfc.adapt_brand_section(hero, LADDER_DOC)
        self.assertIsNotNone(sect_copy)  # hero carries SECTION_COPY
        for m in layout["blockMapping"]:
            if (m.get("contract") or "") == "heading":
                self.assertNotEqual("h2", str((m.get("usage") or {}).get("level")))

    def _band(self, doc, copy):
        # panel furniture (rows) routes compose_info_band down the BAND-HEADING
        # branch (panel-less copy delegates to the classic h2 split instead).
        saved = cs.LAYOUT_COPY
        try:
            cs.LAYOUT_COPY = {**cs.LAYOUT_COPY, "band": {
                "eyebrow": "", "panelTitle": "Panel",
                "rows": [("Label", "Value")], "cta": "", **copy}}
            return cs.compose_info_band(doc, {"id": "band"}, _ctx(doc), [], None)
        finally:
            cs.LAYOUT_COPY = saved

    def test_info_band_heading_honors_heading_level(self):
        html = self._band(LADDER_DOC, {"heading": "Band head", "headingLevel": "h2"})
        self.assertIn("c-heading--h2", html)
        self.assertNotIn("c-heading--display", html)

    def test_info_band_without_heading_level_keeps_display(self):
        html = self._band(FIXTURE_DOC, {"heading": "Band head"})
        self.assertIn("c-heading--display", html)


# ── W6: pattern retrieval — declared useCase, no hero default, visible outcome ───

class InferUseCaseTest(unittest.TestCase):
    def test_declared_canonical_use_case_wins(self):
        layout = {"id": "x", "_composition": {"useCase": "faq"}, "slots": []}
        self.assertEqual("faq", ll.infer_use_case(layout))

    def test_declared_semantic_use_case_maps_via_keywords(self):
        layout = {"id": "x", "_composition": {"useCase": "process"}, "slots": []}
        self.assertEqual("features", ll.infer_use_case(layout))

    def test_declared_unknown_use_case_is_no_bucket(self):
        layout = {"id": "x", "_composition": {"useCase": "stats"}, "slots": []}
        self.assertEqual("", ll.infer_use_case(layout))

    def test_keyword_fallback_still_works(self):
        self.assertEqual("hero", ll.infer_use_case({"id": "opening-hero", "slots": []}))

    def test_unknown_layout_no_longer_defaults_to_hero(self):
        # the W6 failure: "pb-statement"/"pb-compare" bucketed as hero and got
        # hero-inset-noise-panel stamped.
        self.assertEqual("", ll.infer_use_case({"id": "pb-statement", "slots": []}))

    def test_no_bucket_query_is_an_honest_miss(self):
        res = ll.match(ll.Query(use_case=""), Path("/nonexistent/brand.yaml"))
        self.assertEqual("miss", res.match_kind)
        self.assertIsNone(res.pattern)


class RetrievalStampTest(unittest.TestCase):
    def test_miss_is_a_visible_advisory_stamp(self):
        # single-section path: a no-bucket layout renders with the miss stamp,
        # never a silent nothing (and never a hero pattern).
        remote = _REPO / "runs" / "remote" / "brand" / "brand.yaml"
        if not remote.exists():
            self.skipTest("remote brand fixture not present")
        layout = {"id": "pb-statement", "archetype": "stack",
                  "_composition": {"useCase": "statement"}, "blockMapping": []}
        doc = cs.load_doc(remote)
        pattern, kind = cs.resolve_pattern(doc, layout, remote)
        self.assertIsNone(pattern)
        self.assertEqual("miss", kind)


# ── W7 / AS-52: no phantom media in quote cards ──────────────────────────────────

class QuoteCardMediaTest(unittest.TestCase):
    def _compose(self, cards):
        saved = cs.LAYOUT_COPY
        try:
            cs.LAYOUT_COPY = {**cs.LAYOUT_COPY,
                              "q": {"eyebrow": "", "heading": "Stories",
                                    "cards": cards}}
            return cs.compose_features_cards(FIXTURE_DOC, {"id": "q"}, _ctx(), [], None)
        finally:
            cs.LAYOUT_COPY = saved

    def test_assetless_quote_card_renders_no_media(self):
        html = self._compose([{"body": "Great product.", "name": "Ana P.",
                               "role": "COO"}])
        card = html.split("</article>")[0]
        self.assertIn("cs-module--quote", card)
        self.assertNotIn("<figure", card)
        self.assertNotIn("c-image", card)
        self.assertIn("c-person", card)  # the attribution row still renders

    def test_explicitly_bound_asset_still_renders(self):
        html = self._compose([{"body": "Great.", "name": "Ana P.",
                               "asset": "portrait.webp"}])
        card = html.split("</article>")[0]
        self.assertIn("<figure", card)
        self.assertIn("assets/portrait.webp", card)

    def test_non_quote_cards_keep_the_backfill(self):
        html = self._compose([{"caption": "Editorial", "body": "Body."}])
        card = html.split("</article>")[0]
        self.assertNotIn("cs-module--quote", card)
        # the asset-less FIXTURE brand backfills the srcless placeholder chip —
        # the pre-W7 behavior for non-quote modules, byte-identical.
        self.assertIn("<figure", card)
        self.assertIn("c-image-ph", card)


# ── W8 / AS-53: the split-accordion renders the section action slot ──────────────

class AccordionActionSlotTest(unittest.TestCase):
    def _copy(self, cta=""):
        return cs._SafeCopy({"eyebrow": "HOW IT WORKS", "heading": "Process",
                             "cta": cta, "rowIcons": [], "rowMedia": []})

    def test_authored_cta_renders_as_list_column_foot(self):
        html = cs._compose_accordion_split(
            FIXTURE_DOC, {"id": "proc"}, _ctx(), self._copy("See the full process"),
            [("Step one", "Details.")], "<img>", "", "")
        self.assertIn("cs-acc-foot", html)
        self.assertIn("See the full process", html)
        self.assertIn("c-arrow-link", html)
        # the foot closes the LIST column, before the media column
        self.assertLess(html.index("cs-acc-foot"), html.index("cs-split-media"))

    def test_ctaless_section_renders_no_foot(self):
        html = cs._compose_accordion_split(
            FIXTURE_DOC, {"id": "proc"}, _ctx(), self._copy(""),
            [("Step one", "Details.")], "<img>", "", "")
        self.assertNotIn("cs-acc-foot", html)

    def test_bound_button_slots_suppress_the_copy_foot(self):
        # real action slots render in the intro's actions row — the copy-layer cta
        # must not duplicate below the list.
        html = cs._compose_accordion_split(
            FIXTURE_DOC, {"id": "proc"}, _ctx(), self._copy("Dup risk"),
            [("Step one", "Details.")], "<img>", "",
            '\n    <div class="cs-hero-actions"><a>Real action</a></div>')
        self.assertNotIn("cs-acc-foot", html)

    def test_foot_css_ships_in_the_accordion_scaffold(self):
        self.assertIn(".cs-acc-foot", cs.SCAFFOLD_ACCORDION_CSS)


# ── W9: interlock honors authored alt ────────────────────────────────────────────

class InterlockAltTest(unittest.TestCase):
    def test_authored_alt_rides_through(self):
        copy = cfc._interlock_copy({"id": "st", "slots": [
            {"name": "statement", "role": "statement",
             "contract": "heading", "copy": {"heading": "One platform."}},
            {"name": "media", "role": "supporting media", "contract": "image",
             "asset": {"src": "photo.webp", "alt": "Team collaborating in Lisbon"}},
        ]})
        self.assertEqual("Team collaborating in Lisbon", copy["alt"])

    def test_absent_alt_stays_empty_for_the_brand_default(self):
        copy = cfc._interlock_copy({"id": "st", "slots": [
            {"name": "media", "role": "supporting media", "contract": "image",
             "asset": {"src": "photo.webp"}},
        ]})
        self.assertEqual("", copy["alt"])


# ── W12: real textarea on the brand input anatomy ────────────────────────────────

class TextareaFieldTest(unittest.TestCase):
    def test_textarea_kind_renders_a_real_textarea(self):
        html = cs._signup_field_html(FIXTURE_DOC, _ctx(), {
            "kind": "textarea", "label": "Anything else?", "name": "notes",
            "placeholder": "Tell us more", "span": "full"}, 0, "f1")
        self.assertIn("<textarea", html)
        self.assertIn('class="cs-input cs-input--multiline"', html)
        self.assertIn('rows="4"', html)
        self.assertIn('placeholder="Tell us more"', html)
        self.assertNotIn("<input", html)
        # accessible label still binds
        self.assertIn('for="f1-notes"', html)

    def test_textarea_is_a_recognized_composition_kind(self):
        self.assertIn("textarea", cfc._FORM_FIELD_KINDS)

    def test_multiline_css_ships_with_the_form_scaffold(self):
        self.assertIn(".cs-input--multiline", cs.SCAFFOLD_SIGNUP_CSS)
        self.assertIn("resize: vertical", cs.SCAFFOLD_SIGNUP_CSS)


# ── W1: banner backdrop-aware paint at the bridge ────────────────────────────────

class BannerBackdropTest(unittest.TestCase):
    def _bridge(self):
        sys.path.insert(0, str(_REPO / "tools"))
        import bridge_chrome_to_brand as bridge
        return bridge

    def _nav(self, banner):
        return {"bg": "#fff", "color": "#111", "height": 64, "utility": [],
                "primary": [], "links": [], "ctas": [], "banner": banner}

    def test_effective_paint_wins_and_raw_declaration_is_kept(self):
        bridge = self._bridge()
        out = bridge._merge_navbar(None, self._nav({
            "observed": True, "text": "Promo", "ink": "rgb(255, 255, 255)",
            "bg": "rgba(51, 79, 111, 0.5)", "bgEffective": "rgb(36, 50, 66)"}))
        ub = out["utilityBanner"]
        self.assertEqual("rgb(36, 50, 66)", ub["bg"])
        self.assertEqual("rgba(51, 79, 111, 0.5)", ub["bgRaw"])

    def test_capture_without_effective_keeps_old_behavior(self):
        bridge = self._bridge()
        out = bridge._merge_navbar(None, self._nav({
            "observed": True, "text": "Promo", "ink": "rgb(255, 255, 255)",
            "bg": "rgb(20, 20, 21)"}))
        ub = out["utilityBanner"]
        self.assertEqual("rgb(20, 20, 21)", ub["bg"])
        self.assertNotIn("bgRaw", ub)

    def test_remote_banner_fact_is_opaque_and_legible(self):
        # evidence lock: the active brand's banner fact is the composited
        # screen-truth paint and clears the WCAG floor against its own ink.
        remote = _REPO / "runs" / "remote" / "brand" / "brand.yaml"
        if not remote.exists():
            self.skipTest("remote brand fixture not present")
        import readability as R
        import yaml
        doc = yaml.safe_load(remote.read_text())
        ub = ((doc.get("navbar") or {}).get("utilityBanner") or {})
        bg = R.parse_color(str(ub.get("bg")))
        ink = R.parse_color(str(ub.get("ink")))
        self.assertIsNotNone(bg)
        self.assertGreaterEqual(bg[3], 0.999, "banner bg must be opaque (W1)")
        self.assertGreaterEqual(R.contrast_ratio(ink[:3], bg[:3]), 4.5)

    def test_extractor_measures_the_composited_paint(self):
        # the harvest JS records bgEffective beside the raw declaration whenever
        # the strip's own backgroundColor carries alpha.
        src = (_REPO / "src" / "screenshot_to_template"
               / "browser_chrome_extractor.py").read_text()
        js = src[src.index("_BANNER_HARVEST_JS"):src.index("_UTILITY_TRIGGERS_JS")]
        self.assertIn("bgEffective", js)
        self.assertIn("effectiveBg", js)


# ── W3: the slop audit honors the art-image contract ─────────────────────────────

class SlopAuditArtExemptionTest(unittest.TestCase):
    def test_as23_skips_art_tagged_images(self):
        src = (_BRAND_PIPELINE / "slop_audit.mjs").read_text()
        block = src[src.index("AS-23"):]
        block = block[:block.index("AS-13")]
        self.assertIn(".c-image--art", block)
        self.assertIn(".c-acc-media--contain", block)
        # the exemption is a `continue` BEFORE the hatch probe emits the flag
        exempt = block.index('im.matches(".c-image--art')
        self.assertIn("continue", block[exempt:exempt + 120])
        self.assertLess(exempt, block.index("out.push"))


# ── W11: the parity counter reads the EMITTED page ───────────────────────────────

class UnresolvedCounterTest(unittest.TestCase):
    def test_counter_counts_markers_in_emitted_html(self):
        src = (_BRAND_PIPELINE / "compose_from_composition.py").read_text()
        fn = src[src.index("def render_composition"):]
        self.assertIn('unresolved = html.count("<!-- unresolved slot")', fn)
        # the phantom source — a side re-render of slots per layout — is gone
        self.assertNotIn("sum(1 for", fn[:fn.index("return")])


if __name__ == "__main__":
    unittest.main()
