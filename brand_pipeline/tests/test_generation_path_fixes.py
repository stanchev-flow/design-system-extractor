#!/usr/bin/env python3
"""Regression tests for the v3 ai-product-launch GENERATION-PATH defect fixes (2026-07).

Each test pins one systemic generation-path fix so the defect cannot silently return:

  D1/D7 nav facts    — composition_to_doc merges the measured nav mega-panel surface
                       + mobile-collapse facts onto the composed doc (transparent
                       mega-nav / non-collapsing nav on generated pages).
  D2 tabs consumer   — a split declaring a `tabs`/`tab-panels` slot surfaces panels +
                       labels through _split_copy (real tab device, no flat degrade).
  D3 silent copy     — _split_copy no longer drops a distinct subheading / mis-binds a
                       testimonial attribution as the body; lint_declared_copy is a loud
                       detector for any declared copy string that never rendered.
  D5 type tier       — a non-hero section heading demotes to the section tier, never the
                       display/hero tier, via the section-heading-level default.
  D8 spacing crash   — spacing_audit.load_brand_facts tolerates a string `mediaScale`
                       (`cover`/`contain`) instead of crashing the whole spacing gate.
  wireframe/lint     — the tabbed testimonial counts as one complete testimonial with a
                       visual anchor; per-panel tab stats are NOT a flat stat band.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "brand_pipeline"))

import compose_from_composition as cfc  # noqa: E402
import composition_lint as cl  # noqa: E402
import section_wireframe as sw  # noqa: E402


def _split_section(slots, **over):
    sec = {"id": "sec", "useCase": "features", "archetype": "split", "slots": slots}
    sec.update(over)
    return sec


class SilentCopyDropFixes(unittest.TestCase):
    def test_distinct_subheading_is_captured_beside_body(self):
        sec = _split_section([
            {"name": "heading", "role": "heading", "contract": "heading",
             "copy": "One layer across the platform."},
            {"name": "subheading", "role": "subheading", "contract": "paragraph",
             "copy": "It already knows your customers."},
            {"name": "body", "role": "body", "contract": "paragraph",
             "copy": "Grounded in the data every hub already shares."},
        ])
        copy = cfc._split_copy(sec)
        self.assertEqual(copy["subheading"], "It already knows your customers.")
        self.assertEqual(copy["body"], "Grounded in the data every hub already shares.")
        self.assertNotEqual(copy["subheading"], copy["body"])

    def test_lone_lede_stays_the_body_not_a_subheading(self):
        # regression guard: a single lede slot must remain the BODY (fix6-era), never
        # get hijacked as a subheading and blanked out.
        sec = _split_section([
            {"name": "heading", "role": "heading", "contract": "heading", "copy": "H"},
            {"name": "subheading", "role": "hub-lede", "contract": "paragraph",
             "copy": "The single body claim."},
        ])
        copy = cfc._split_copy(sec)
        self.assertEqual(copy["body"], "The single body claim.")
        self.assertEqual(copy["subheading"], "")

    def test_testimonial_quote_and_attribution_bind_not_the_body(self):
        sec = _split_section([
            {"name": "portrait", "role": "media", "contract": "image",
             "asset": {"src": "p.png"}, "mediaAspect": "landscape"},
            {"name": "quote", "role": "quote", "contract": "quote",
             "copy": "We trained the agent like a new hire."},
            {"name": "attribution", "role": "attribution", "contract": "label",
             "copy": "Jane Roe, Director, Acme"},
        ], useCase="testimonial")
        copy = cfc._split_copy(sec)
        self.assertTrue(copy["hasQuote"])
        self.assertEqual(copy["quote"], "We trained the agent like a new hire.")
        self.assertEqual(copy["attribution"], "Jane Roe, Director, Acme")
        # the attribution must NOT shadow the quote as the body
        self.assertNotEqual(copy["body"], "Jane Roe, Director, Acme")

    def test_lint_declared_copy_flags_a_dropped_string(self):
        comp = {"sections": [{"id": "s", "slots": [
            {"name": "h", "contract": "heading", "copy": "Rendered heading"},
            {"name": "b", "contract": "paragraph", "copy": "This body was dropped"},
        ]}]}
        html = "<h2>Rendered heading</h2>"
        misses = cfc.lint_declared_copy(comp, html)
        keys = {(m["slot"], m["key"]) for m in misses}
        self.assertIn(("b", "copy"), keys)
        # the rendered string is NOT reported
        self.assertNotIn(("h", "copy"), keys)

    def test_lint_declared_copy_passes_when_all_render(self):
        comp = {"sections": [{"id": "s", "slots": [
            {"name": "h", "contract": "heading", "copy": "All present here"}]}]}
        html = "<h2>All present here</h2>"
        self.assertEqual(cfc.lint_declared_copy(comp, html), [])


class TabsConsumer(unittest.TestCase):
    def _tab_section(self):
        return _split_section([
            {"name": "panels", "role": "tab-panels", "contract": "tabs", "copy": [
                {"label": "Enterprise", "quote": "Q1", "name": "A", "role": "R1",
                 "media": "a.png", "stats": [{"value": "12", "label": "x"}]},
                {"label": "SMB", "quote": "Q2", "name": "B", "role": "R2",
                 "media": "b.png", "stats": [{"value": "59%", "label": "y"}]},
            ]}], useCase="testimonial", seededFrom={"lib": "project",
                                                    "id": "tabbed-testimonial-with-stats"})

    def test_split_copy_surfaces_panels_and_labels(self):
        copy = cfc._split_copy(self._tab_section())
        self.assertEqual(copy["tabs"], ["Enterprise", "SMB"])
        self.assertEqual(len(copy["panels"]), 2)
        self.assertEqual(copy["panels"][0]["quote"], "Q1")

    def test_single_panel_does_not_trigger_tab_device(self):
        sec = _split_section([
            {"name": "panels", "role": "tab-panels", "contract": "tabs",
             "copy": [{"label": "Only", "quote": "Q"}]}], useCase="testimonial")
        copy = cfc._split_copy(sec)
        self.assertEqual(copy["panels"], [])
        self.assertEqual(copy["tabs"], [])


class WireframeTabbedTestimonial(unittest.TestCase):
    def test_tabbed_testimonial_is_complete_with_visual_anchor(self):
        sec = _split_section([
            {"name": "panels", "role": "tab-panels", "contract": "tabs", "copy": [
                {"label": "Enterprise", "quote": "Q1", "name": "A",
                 "role": "Director, Acme", "media": "a.png"},
                {"label": "SMB", "quote": "Q2", "name": "B",
                 "role": "Owner, Beta", "media": "b.png"},
            ]}], useCase="testimonial")
        plan = sw._testimonial_plan(sec, registry=None, brand={})
        self.assertIsNotNone(plan)
        self.assertEqual(plan["componentContract"], "testimonial")
        self.assertTrue(plan["complete"])
        self.assertEqual(plan["assetStatus"], "bound")
        # the tabs slot is a substantive visual anchor (its case photos live in panels)
        self.assertTrue(sw._slot_has_visual(sec["slots"][0]))

    def test_tabbed_testimonial_visual_contract_in_lint(self):
        self.assertIn("tabs", cl._VISUAL_CONTRACTS)


class TypeTierDemotion(unittest.TestCase):
    def test_non_hero_display_heading_demotes_to_section_tier(self):
        import yaml
        brand_yaml = REPO / "runs" / "hubspot-v3" / "brand" / "brand.yaml"
        if not brand_yaml.is_file():
            self.skipTest("hubspot-v3 brand fixture not present")
        doc = yaml.safe_load(brand_yaml.read_text())
        section = {"id": "band", "useCase": "features", "archetype": "split",
                   "slots": [{"name": "heading", "role": "heading",
                              "contract": "heading", "sizeClass": "display",
                              "copy": "A section heading, not a hero monument."}]}
        _layout, merged, _sect = cfc.adapt_brand_section(section, doc)
        # the non-hero section heading demotes to the brand's measured section tier
        # (h2 for a ladder-bearing brand) — never the display/hero tier.
        self.assertNotEqual(str(merged.get("headingLevel") or "").lower(), "display")


class NavResponsiveChromeFacts(unittest.TestCase):
    def test_generation_doc_gets_nav_panel_collapse_and_promoted_headings(self):
        brand_yaml = REPO / "runs" / "hubspot-v3" / "brand" / "brand.yaml"
        if not brand_yaml.is_file():
            self.skipTest("hubspot-v3 brand fixture not present")
        comp = {"sections": [{"id": "hero", "useCase": "hero", "archetype": "stack",
                              "slots": [{"name": "heading", "role": "heading",
                                         "contract": "heading", "sizeClass": "display",
                                         "copy": "Hello"}]}]}
        doc, _order = cfc.composition_to_doc(comp, brand_yaml)
        resp = doc.get("responsive") or {}
        # nav mega-panel surface + mobile-collapse facts must be merged (D1/D7)...
        self.assertIn("nav", resp)
        self.assertTrue((resp["nav"].get("panelSurface") or {}).get("background"))
        self.assertIn("collapse", resp["nav"])
        # ...and heading line-heights are now PROMOTED into generation (fix2 2026-07):
        # AS-82 made line-height UNITLESS (a ratio, not a frozen-px box), removing the
        # AS-16 register-overlap risk, so the source's measured heading register crosses
        # into composed pages. (The hero family stays excluded — geometry-bearing.)
        self.assertIn("headings", resp)
        self.assertTrue((resp["headings"].get("lineHeights") or {}))


class AccordionCollapsedByDefault(unittest.TestCase):
    def test_faq_stamp_has_no_open_index_by_default(self):
        # the generation FAQ/disclosure device is native <details>: with no stamped
        # open index every row is CLOSED (no `open` attr) — collapsed-by-default, so
        # the accordion can never expand and push the page (D6). Native <details> also
        # never JS-mis-computes height.
        stamp = cfc._faq_stamp(None)
        self.assertNotIn("open", stamp)
        self.assertTrue(stamp["exclusive"])  # <details name> ⇒ single-open

    def test_faq_stamp_honours_authored_open_index(self):
        stamp = cfc._faq_stamp({"open": 0})
        self.assertEqual(stamp["open"], 0)


class IconSizingRoleGuard(unittest.TestCase):
    def test_spot_icon_coerced_to_mark_never_media_well(self):
        # AS-80: an icon/mark-kind asset requested for a card LEAD/media role is
        # coerced to `mark` (renders at mark/spot height in its icon role), never a
        # cover media-well — so a spot icon can never blow up into card hero media,
        # and card marks ride the card spot size, not the nav-mark size.
        import component_render as cr
        doc = {"_mediaAssetsKind": {"spark.svg": "spot-icon"},
               "_mediaAssetsFit": {"spark.svg": "cover"}}
        self.assertEqual(cr.asset_render_mode(doc, "spark.svg", "card-media"), "mark")
        # a real photograph keeps cover (a genuine card lead image)
        photo_doc = {"_mediaAssetsKind": {"agent.png": "photograph"},
                     "_mediaAssetsFit": {"agent.png": "cover"}}
        self.assertEqual(cr.asset_render_mode(photo_doc, "agent.png", "card-media"),
                         "cover")


class SpacingAuditMediaScaleCrash(unittest.TestCase):
    def test_string_media_scale_does_not_crash_load(self):
        import spacing_audit as sa
        brand_dir = REPO / "runs" / "hubspot-v3" / "brand"
        if not (brand_dir / "brand.yaml").is_file():
            self.skipTest("hubspot-v3 brand fixture not present")
        # the v3 layout-library declares slot.mediaScale as the string "cover"/"contain";
        # load_brand_facts must tolerate it instead of raising AttributeError.
        book = sa.load_brand_facts(brand_dir)
        self.assertIsNotNone(book)


class SectionRulesTabStatsNotAFlatBand(unittest.TestCase):
    def test_flat_stats_excludes_tab_panel_stats(self):
        try:
            from bs4 import BeautifulSoup
        except Exception:  # pragma: no cover - bs4 always present in this env
            self.skipTest("bs4 not available")
        import section_rules_audit as sra
        html = """
        <section id="a">
          <div class="cs-tabs">
            <div class="cs-tabpanel"><div class="c-stat"><span class="c-stat-value">12</span></div>
              <div class="c-stat"><span class="c-stat-value">5</span></div></div>
            <div class="cs-tabpanel" hidden><div class="c-stat"><span class="c-stat-value">59%</span></div>
              <div class="c-stat"><span class="c-stat-value">17%</span></div>
              <div class="c-stat"><span class="c-stat-value">7%</span></div></div>
          </div>
          <div class="c-stat"><span class="c-stat-value">99%</span></div>
        </section>"""
        node = BeautifulSoup(html, "html.parser").find("section")
        flat = sra._flat_stats(node)
        # 5 stats live inside tab panels; only the 1 flat stat counts as a band item
        self.assertEqual(len(flat), 1)


if __name__ == "__main__":
    unittest.main()
