#!/usr/bin/env python3
"""Unit tests for the hubspot-fix batch (2026-07): the deterministic composer/adapter/
gate defects the HubSpot tokenized validation run isolated (AS-26..AS-31).

Covers:
  - radius-scale var()-chain resolution (N6): `var(--button-radius)` resolves through
    the page's own declarations before the scale judgment;
  - footer grammar selection (B6): display-links for a footer-tier brand, columns for
    a measured multi-column footer, display-links default otherwise;
  - style-aware cta-shape (B5): brand LAW beats the style default; the style's
    primaryAction soft-option default fills the gap for law-silent brands;
  - render_button dispatch (B5): a typographic brand cannot emit `.c-button`;
  - exact-role-first type-scale picking (B11): `display-hero` resolves to the brand's
    verbatim tier, not the largest display-family sibling;
  - display_source (B3): corporate-saas-clean rides the brand display tier; editorial
    styles keep the poster clamp;
  - adapter slot-faithfulness (N1/N2/B5): dict-src unwrapping, button-slot
    preservation, conversion-vs-flow stack routing, testimonial/logo/link/label
    normalization to registered renderers;
  - foreign-brand content check: another extracted brand's name in a content
    attribute fails; the active brand's own name passes.

Run:  ./venv/bin/python -m unittest brand_pipeline.tests.test_fix_batch
"""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

_BRAND_PIPELINE = Path(__file__).resolve().parent.parent
if str(_BRAND_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_BRAND_PIPELINE))

import component_render as cr  # noqa: E402
import compose_from_composition as cfc  # noqa: E402
import onbrand_check as oc  # noqa: E402
import styles  # noqa: E402
import tokens_css  # noqa: E402
from tests.test_tokens_css import FIXTURE  # noqa: E402


def _woodwavish():
    doc = copy.deepcopy(FIXTURE)
    doc["neverDo"] = [{"id": "no-boxed-inputs"}, {"id": "no-radius"}]
    doc["primitives"] = {"button": {"use": "never"}}
    doc.pop("buttons", None)
    return doc


class RadiusVarChain(unittest.TestCase):
    def test_resolves_single_hop(self):
        vm = {"--button-radius": "0.5rem"}
        self.assertEqual(oc._resolve_css_var_chain("var(--button-radius)", vm), "0.5rem")

    def test_resolves_nested_chain_and_fallback(self):
        vm = {"--c-button-radius": "var(--button-radius)", "--button-radius": "0.5rem"}
        self.assertEqual(oc._resolve_css_var_chain("var(--c-button-radius)", vm), "0.5rem")
        self.assertEqual(
            oc._resolve_css_var_chain("var(--missing, var(--button-radius))", vm), "0.5rem")

    def test_literal_and_dead_end_pass_through(self):
        self.assertEqual(oc._resolve_css_var_chain("0.25rem", {}), "0.25rem")
        self.assertEqual(oc._resolve_css_var_chain("var(--nope)", {}), "var(--nope)")

    def test_cycle_terminates(self):
        vm = {"--a": "var(--b)", "--b": "var(--a)"}
        out = oc._resolve_css_var_chain("var(--a)", vm)
        self.assertTrue(out.startswith("var("))  # judged as-is, never an infinite loop

    def test_radius_check_accepts_on_scale_chain(self):
        """End-to-end: a radius var whose chain lands on the brand scale passes."""
        doc = copy.deepcopy(FIXTURE)
        doc["tokens"]["radius"] = {"button": {"value": "0.5rem"}}
        facts = {
            "heading_family": "Fixture Serif", "off_palette": [], "allowed_hex": set(),
            "lorem": False, "missing_imgs": [], "local_imgs": ["assets/x.jpg"],
            "radius_vars": {"--c-button-radius": "var(--button-radius)"},
            "css_vars": {"--button-radius": "0.5rem"},
            "content_attr_texts": [], "webfont_delivered": True,
            "google_fonts": True, "self_hosted_fonts": False,
        }
        checks = oc.check_slop(doc, "<html></html>", {}, facts)
        row = next(c for c in checks if c[0].startswith("Rounding matches"))
        self.assertTrue(row[1], row[2])

    def test_radius_check_still_fails_true_off_scale(self):
        doc = copy.deepcopy(FIXTURE)
        doc["tokens"]["radius"] = {"button": {"value": "0.5rem"}}
        facts = {
            "heading_family": "Fixture Serif", "off_palette": [], "allowed_hex": set(),
            "lorem": False, "missing_imgs": [], "local_imgs": ["assets/x.jpg"],
            "radius_vars": {"--c-button-radius": "var(--button-radius)"},
            "css_vars": {"--button-radius": "7px"},   # resolves OFF the brand scale
            "content_attr_texts": [], "webfont_delivered": True,
            "google_fonts": True, "self_hosted_fonts": False,
        }
        checks = oc.check_slop(doc, "<html></html>", {}, facts)
        row = next(c for c in checks if c[0].startswith("Rounding matches"))
        self.assertFalse(row[1], row[2])


class FooterGrammar(unittest.TestCase):
    def test_footer_tier_selects_display_links(self):
        doc = copy.deepcopy(FIXTURE)
        doc["tokens"]["type"]["footer-sitemap-link"] = {"sizeRem": {"base": 2.5}}
        self.assertEqual(cr.footer_grammar(doc), "display-links")

    def test_measured_columns_select_columns(self):
        doc = copy.deepcopy(FIXTURE)
        doc["footer"] = {"columns": [{"links": [{"label": "Pricing", "href": "#"}]}]}
        self.assertEqual(cr.footer_grammar(doc), "columns")

    def test_measured_columns_outrank_compact_footer_link_tier(self):
        doc = copy.deepcopy(FIXTURE)
        doc["tokens"]["type"]["footer-sitemap-link"] = {"sizeRem": {"base": 0.75}}
        doc["footer"] = {"columns": [{"links": [{"label": "Pricing", "href": "#"}]}]}
        self.assertEqual(cr.footer_grammar(doc), "columns")

    def test_default_is_display_links(self):
        self.assertEqual(cr.footer_grammar(copy.deepcopy(FIXTURE)), "display-links")

    def test_render_footer_columns_grammar(self):
        doc = copy.deepcopy(FIXTURE)
        doc["footer"] = {"columns": [{"links": [{"label": "Pricing", "href": "/p"}]}]}
        ctx = cr.ComponentContext(surface_role="surface/inverse-strong", is_dark=True)
        html = cr.render_footer(doc, ctx, {
            "columns": doc["footer"]["columns"], "legal": "(c) Fixture"})
        self.assertIn("c-foot-cols", html)
        self.assertIn("c-foot-col-link", html)
        self.assertNotIn("c-foot-sitemap", html)


class StyleAwareCtaShape(unittest.TestCase):
    def test_brand_law_beats_style_default(self):
        # WoodWave-shaped brand under ANY style stays typographic (button use: never)
        self.assertEqual(cr.cta_shape(_woodwavish(), "filled"), "typographic")
        # a never-typographic-primary brand stays filled under a typographic style
        doc = copy.deepcopy(FIXTURE)
        doc["neverDo"] = [{"id": "never-typographic-primary"}]
        self.assertEqual(cr.cta_shape(doc, "typographic"), "filled")

    def test_style_default_fills_gap_for_law_silent_brand(self):
        doc = copy.deepcopy(FIXTURE)
        doc.pop("buttons", None)          # no measured family, no law
        doc.pop("primitives", None)
        self.assertEqual(cr.cta_shape(doc), "typographic")             # legacy default
        self.assertEqual(cr.cta_shape(doc, "filled"), "filled")        # style speaks

    def test_parsed_style_primary_action(self):
        for sid, expected in (("corporate-saas-clean", "filled"),
                              ("editorial-luxury", "filled"),
                              ("radical-editorial", "typographic")):
            st = styles.load_style(sid)
            self.assertEqual(st.structure.primary_action, expected, sid)

    def test_render_button_dispatch(self):
        ww = _woodwavish()
        ctx = cr.make_context(ww, "surface/primary", {})
        html = cr.render_button(ww, ctx, {"label": "Go"})
        self.assertIn("c-arrow-link", html)            # typographic downgrade
        self.assertNotIn("c-button", html)
        filled = copy.deepcopy(FIXTURE)
        filled["neverDo"] = [{"id": "never-typographic-primary"}]
        fctx = cr.make_context(filled, "surface/primary", {})
        fhtml = cr.render_button(filled, fctx, {"label": "Go"})
        self.assertIn('class="c-button"', fhtml)


class ExactRolePicker(unittest.TestCase):
    def test_hyphenated_role_is_authoritative(self):
        scale = {
            "display-hero": {"px": 64.8, "sizeRem": {"base": 4.05}, "family": "display"},
            "display-02": {"px": 120, "sizeRem": {"base": 7.5}, "family": "display"},
        }
        picked = tokens_css._pick_scale_entry("display-hero", scale)
        self.assertEqual(picked, scale["display-hero"])

    def test_bare_body_keeps_reading_register_heuristic(self):
        scale = {
            "body-lg": {"sizeRem": {"base": 1.125}, "family": "body"},
            "body-sm": {"sizeRem": {"base": 0.75}, "family": "body"},
            "body": {"sizeRem": {"base": 0.875}, "family": "body"},
        }
        picked = tokens_css._pick_scale_entry("body", scale)
        self.assertEqual(picked, scale["body-lg"])     # lead register, not the same-named tier


class DisplaySource(unittest.TestCase):
    def test_front_matter_parses(self):
        self.assertEqual(styles.load_style("corporate-saas-clean").structure.display_source,
                         "brand")
        self.assertEqual(styles.load_style("editorial-luxury").structure.display_source,
                         "poster")
        self.assertEqual(styles.load_style("radical-editorial").structure.display_source,
                         "poster")

    def test_page_display_size_honors_source(self):
        import compose_page as cp
        doc = copy.deepcopy(FIXTURE)

        class _Ctx:
            active = True

        ctx = _Ctx()
        ctx.structure = styles.load_style("corporate-saas-clean").structure
        brand_disp = cp.page_display_size(doc, ctx)
        self.assertNotIn("clamp", brand_disp)          # the brand tier, not the poster
        ctx2 = _Ctx()
        ctx2.structure = styles.load_style("radical-editorial").structure
        self.assertIn("clamp", cp.page_display_size(doc, ctx2))
        self.assertNotIn("clamp", cp.page_display_size(doc, None))  # unstyled = brand tier


class AdapterSlotFaithfulness(unittest.TestCase):
    def _section(self, **kw):
        base = {"id": "s", "archetype": "stack", "useCase": "cta", "slots": []}
        base.update(kw)
        return base

    def test_cta_mapping_preserves_buttons_and_drops_invented_form(self):
        sec = self._section(slots=[
            {"name": "header", "role": "section-header", "contract": "header",
             "copy": {"heading": "H", "text": "B"}},
            {"name": "primary", "role": "cta-primary", "contract": "button", "copy": "Start free"},
            {"name": "secondary", "role": "cta-secondary", "contract": "button", "copy": "See how"},
        ])
        mapping = cfc._cta_mapping(sec)
        contracts = [m["contract"] for m in mapping]
        self.assertEqual(contracts, ["header", "button", "button"])   # no invented form
        self.assertEqual(mapping[1]["usage"]["label"], "Start free")

    def test_cta_mapping_legacy_shape_unchanged(self):
        # a link/heading-only WoodWave conversion keeps the exact legacy mapping
        sec = self._section(slots=[
            {"name": "h", "role": "heading", "contract": "heading", "copy": "H"},
            {"name": "l1", "role": "primary", "contract": "link", "copy": "Go"},
        ])
        mapping = cfc._cta_mapping(sec)
        self.assertEqual([m["contract"] for m in mapping], ["header", "form"])
        self.assertEqual(mapping[1]["usage"], {"variant": "underline"})

    def test_stack_routing_variety(self):
        logos = cfc.composition_to_layout(self._section(
            id="logos", useCase="logos", slots=[
                {"name": "caption", "role": "logo-caption", "contract": "eyebrow", "copy": "Trusted"},
                {"name": "logos", "role": "logo-wall", "contract": "logo",
                 "copy": [{"alt": "DoorDash"}, {"alt": "eBay"}]},
            ]))
        self.assertEqual(logos["archetype"], "generic-flow")
        caps = [m for m in logos["blockMapping"] if m["contract"] == "caption"]
        self.assertEqual([c["usage"]["text"] for c in caps], ["DoorDash", "eBay"])

        testimonial = cfc.composition_to_layout(self._section(
            id="t", useCase="testimonial", slots=[
                {"name": "quote", "role": "testimonial", "contract": "testimonial",
                 "copy": {"quote": "Great.", "name": "Ops lead", "role": "Mid-market"}}]))
        self.assertEqual(testimonial["archetype"], "generic-flow")
        contracts = [m["contract"] for m in testimonial["blockMapping"]]
        self.assertEqual(contracts, ["paragraph", "caption"])   # quote + attribution

        cta = cfc.composition_to_layout(self._section(
            id="cta", useCase="cta", slots=[
                {"name": "header", "contract": "header", "copy": {"heading": "H"}},
                {"name": "primary", "role": "cta-primary", "contract": "button", "copy": "Go"}]))
        self.assertEqual(cta["archetype"], "stack")             # conversion stays a stack
        self.assertIn("button", [m["contract"] for m in cta["blockMapping"]])

        footer = cfc.composition_to_layout(self._section(
            id="footer", useCase="footer", slots=[
                {"name": "links", "role": "footer-nav", "contract": "link",
                 "copy": [{"text": "Pricing"}, {"text": "Contact"}]},
                {"name": "legal", "role": "legal", "contract": "label", "copy": "(c) X"}]))
        self.assertEqual(footer["archetype"], "generic-flow")
        kinds = [m["contract"] for m in footer["blockMapping"]]
        self.assertEqual(kinds, ["link", "link", "caption"])

    def test_cards_copy_unwraps_sanitized_asset_dict(self):
        sec = {"id": "features", "archetype": "cards", "useCase": "features", "slots": [
            {"name": "cards", "role": "feature-cards", "contract": "feature-item",
             "copy": [{"heading": "A", "text": "B",
                       "asset": {"src": "assets/icon.webp", "alt": "Icon"}}]}]}
        cards = cfc._cards_copy(sec)["cards"]
        self.assertEqual(cards[0]["asset"], "assets/icon.webp")   # a STRING, never a dict
        self.assertEqual(cards[0]["alt"], "Icon")


class MeasuredPairContrastExemption(unittest.TestCase):
    """fidelity-over-floor: the brand's MEASURED button pair is exempt from the generic
    text-contrast floor; the same colors in a NON-measured pairing still fail."""

    _HTML = """<html><body>
      <div id="sec-0" style="--c-paper:#ffffff; --c-ink:#1f1f1f;">
        <section class="cs-section">
          <a class="c-button" style="background:#ff4800;color:#ffffff;font-size:1rem">Start free</a>
        </section>
      </div></body></html>"""

    def test_measured_pair_exempt_and_reported(self):
        import readability
        ok, detail = readability.check_text_contrast(
            self._HTML, default_bg="#ffffff",
            measured_pairs=[("#ffffff", "#ff4800")])
        self.assertTrue(ok, detail)
        self.assertIn("MEASURED brand pair", detail)

    def test_non_measured_pair_still_fails(self):
        import readability
        ok, detail = readability.check_text_contrast(self._HTML, default_bg="#ffffff")
        self.assertFalse(ok, detail)


class ForeignBrandContent(unittest.TestCase):
    def _facts(self, alts):
        return {
            "heading_family": "Fixture Serif", "off_palette": [], "allowed_hex": set(),
            "lorem": False, "missing_imgs": [], "local_imgs": ["assets/x.jpg"],
            "radius_vars": {}, "css_vars": {}, "content_attr_texts": alts,
            "webfont_delivered": True, "google_fonts": True, "self_hosted_fonts": False,
        }

    def _row(self, doc, alts):
        checks = oc.check_slop(doc, "<html></html>", {}, self._facts(alts))
        return next(c for c in checks if c[0].startswith("No foreign-brand content"))

    def test_foreign_name_fails(self):
        doc = copy.deepcopy(FIXTURE)
        doc.setdefault("brand", {})["name"] = "HubSpot"
        row = self._row(doc, ["WoodWave editorial photography"])
        self.assertFalse(row[1], row[2])

    def test_own_name_passes(self):
        doc = copy.deepcopy(FIXTURE)
        doc.setdefault("brand", {})["name"] = "WoodWave Gallery"
        row = self._row(doc, ["WoodWave Gallery — hero staircase", "WoodWave detail"])
        self.assertTrue(row[1], row[2])


if __name__ == "__main__":
    unittest.main()
