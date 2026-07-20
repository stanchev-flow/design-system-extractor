#!/usr/bin/env python3
"""Unit tests for the remote-fix batch (2026-07): the 7 pipeline blockers + 3 schema
gaps the Remote E2E run isolated (AS-34..AS-37 family).

Covers:
  - bare-string logo items (blocker 1): the adapter coerces/keeps them, image names
    resolve against the brand inventory, captions survive;
  - brand-owned default art (blocker 2): _brand_art resolves ONLY from the ACTIVE
    brand's attached inventory (exact-name parity first, generic keywords second,
    None third — never a cross-brand literal);
  - foreign-brand asset gate (blocker 2, AS-34): a referenced image owned by a
    SIBLING brand fails slop; the active brand's own files pass;
  - law-first hero CTAs (blocker 3, AS-27 extension): bound button slots render
    through the cta-shape dispatch in compose_stack_hero; no bound slot keeps the
    legacy arrow;
  - structural scaffold pads (blocker 4, AS-24): rhythm_vars_css emits the
    structural pad custom properties, scaffold CSS carries no literal var() fallback;
  - brand-selectable chrome footer surface (blockers 5+10, AS-35): measured footer
    bg resolves to the brand's own nearest surface role; silent brands keep the
    default;
  - recursive asset discovery (blocker 6): subdirectory assets are inventoried and
    copied;
  - preview-tier safety (blocker 7, AS-36): copy_for tolerates missing keys; the
    specimen headline derives from the brand's measured layout copy;
  - self-hosted font registry (schema-gap 8): brand.yaml `selfHostedFonts` entries
    register faces; absent files emit no @font-face (renderProxy fallback);
  - inset art-panel (schema-gap 9, AS-37): style-law gating + panel render with the
    brand's own treatment art.

Run:  ./venv/bin/python -m unittest brand_pipeline.tests.test_remote_fix
"""
from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path

_BRAND_PIPELINE = Path(__file__).resolve().parent.parent
if str(_BRAND_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_BRAND_PIPELINE))

import component_render as cr  # noqa: E402
import compose_from_composition as cfc  # noqa: E402
import compose_page as cp  # noqa: E402
import compose_section as cs  # noqa: E402
import onbrand_check as oc  # noqa: E402
import styles  # noqa: E402
from tests.test_tokens_css import FIXTURE  # noqa: E402


def _slop_facts(**over):
    f = {
        "heading_family": "Fixture Serif", "off_palette": [], "allowed_hex": set(),
        "lorem": False, "missing_imgs": [], "local_imgs": ["assets/x.jpg"],
        "radius_vars": {}, "css_vars": {}, "content_attr_texts": [],
        "webfont_delivered": True, "google_fonts": True, "self_hosted_fonts": False,
    }
    f.update(over)
    return f


def _slop_row(doc, prefix, facts):
    checks = oc.check_slop(doc, "<html></html>", {}, facts)
    return next(c for c in checks if c[0].startswith(prefix))


class BareStringLogoItems(unittest.TestCase):
    """Blocker 1: bare-string repeatable logo items survive the adapter."""

    def test_logo_item_mapping_accepts_bare_string(self):
        m = cfc._logo_item_mapping("Anthropic")
        self.assertEqual(m["usage"].get("text"), "Anthropic")

    def test_logo_wall_keeps_string_items(self):
        sec = {"id": "logos", "archetype": "stack", "useCase": "logos", "slots": [
            {"name": "wall", "role": "logo-wall", "contract": "logo",
             "copy": ["DoorDash", {"alt": "eBay"}]}]}
        layout = cfc.composition_to_layout(sec)
        texts = [m["usage"].get("text") for m in layout["blockMapping"]
                 if m["contract"] == "caption"]
        self.assertEqual(texts, ["DoorDash", "eBay"])


class BrandOwnedDefaultArt(unittest.TestCase):
    """Blocker 2 composer half: fallback art is evidence-checked per brand."""

    def _doc(self, inventory):
        doc = copy.deepcopy(FIXTURE)
        doc[cs.ASSET_INVENTORY_KEY] = inventory
        return doc

    def test_exact_name_parity(self):
        doc = self._doc(["hero-staircase.jpg", "overlap-vase.jpg"])
        self.assertEqual(cs._brand_art(doc, "hero", "hero-staircase.jpg"),
                         "assets/hero-staircase.jpg")

    def test_keyword_fallback_resolves_own_art(self):
        doc = self._doc(["hero-globe-illustration.webp", "logo-a.svg"])
        self.assertEqual(cs._brand_art(doc, "hero", "hero-staircase.jpg"),
                         "assets/hero-globe-illustration.webp")

    def test_no_match_omits_never_borrows(self):
        doc = self._doc(["logo-a.svg"])
        self.assertIsNone(cs._brand_art(doc, "hero", "hero-staircase.jpg"))

    def test_empty_inventory_omits(self):
        # attached-but-empty (a real brand dir with no images) must NOT fall back
        # to another brand's default name.
        doc = self._doc([])
        self.assertIsNone(cs._brand_art(doc, "hero", "hero-staircase.jpg"))


class ForeignAssetGate(unittest.TestCase):
    """Blocker 2 gate half (AS-34): sibling-owned image refs FAIL slop."""

    def test_foreign_owned_ref_fails(self):
        doc = copy.deepcopy(FIXTURE)
        doc.setdefault("brand", {})["name"] = "Remote"
        row = _slop_row(doc, "No foreign-brand asset",
                        _slop_facts(local_imgs=["assets/hero-staircase.jpg"]))
        self.assertFalse(row[1], row[2])
        self.assertIn("hero-staircase.jpg", row[2])

    def test_own_asset_passes(self):
        doc = copy.deepcopy(FIXTURE)
        doc.setdefault("brand", {})["name"] = "WoodWave Gallery"
        row = _slop_row(doc, "No foreign-brand asset",
                        _slop_facts(local_imgs=["assets/hero-staircase.jpg"]))
        self.assertTrue(row[1], row[2])

    def test_unowned_generic_name_passes(self):
        doc = copy.deepcopy(FIXTURE)
        doc.setdefault("brand", {})["name"] = "Remote"
        row = _slop_row(doc, "No foreign-brand asset",
                        _slop_facts(local_imgs=["assets/some-new-shot.webp"]))
        self.assertTrue(row[1], row[2])


class LawFirstHeroCta(unittest.TestCase):
    """Blocker 3: hero action slots ride render_button's cta-shape dispatch."""

    def _hero(self, doc, rendered):
        ctx = cr.make_context(doc, "surface/primary", {})
        layout = {"id": "hero", "archetype": "stack", "useCase": "hero"}
        return cs.compose_stack_hero(doc, layout, ctx, rendered, cs.inactive_context())

    def test_bound_button_slot_renders_in_actions_wrap(self):
        doc = copy.deepcopy(FIXTURE)
        doc["neverDo"] = [{"id": "never-typographic-primary"}]
        ctx = cr.make_context(doc, "surface/primary", {})
        btn_html = cr.render_button(doc, ctx, {"label": "Start free"})
        html = self._hero(doc, [
            {"role": "title", "contract": "heading", "html": "<h1>H</h1>"},
            {"role": "cta-primary", "contract": "button", "html": btn_html},
        ])
        self.assertIn("cs-hero-actions", html)
        self.assertIn('class="c-button"', html)

    def test_typographic_brand_hero_action_downgrades(self):
        doc = copy.deepcopy(FIXTURE)
        doc["primitives"] = {"button": {"use": "never"}}
        doc.pop("buttons", None)
        ctx = cr.make_context(doc, "surface/primary", {})
        btn_html = cr.render_button(doc, ctx, {"label": "Start free"})
        html = self._hero(doc, [
            {"role": "cta-primary", "contract": "button", "html": btn_html}])
        self.assertIn("cs-hero-actions", html)
        self.assertIn("c-arrow-link", html)
        self.assertNotIn('class="c-button"', html)

    def test_no_bound_action_keeps_legacy_arrow(self):
        # legacy path (no actions wrap) still renders the arrow device when the
        # brand actually authored cta copy for the section.
        doc = copy.deepcopy(FIXTURE)
        doc["_brandCopy"] = {"section": {"cta": "Explore"}}
        html = self._hero(doc, [])
        self.assertNotIn("cs-hero-actions", html)
        self.assertIn("c-arrow-link", html)

    def test_no_authored_cta_elides_bare_arrow(self):
        # sysfix 2026-07: no bound action AND no authored cta copy must not leave
        # a label-less "→" artifact (triage items 7/9 — invented action devices).
        html = self._hero(copy.deepcopy(FIXTURE), [])
        self.assertNotIn("cs-hero-actions", html)
        self.assertNotIn("c-arrow-link", html)


class StructuralScaffoldPads(unittest.TestCase):
    """Blocker 4 (AS-24): no literal fallback in scaffold var() references."""

    def test_rhythm_vars_emit_structural_pads(self):
        css = cs.rhythm_vars_css(copy.deepcopy(FIXTURE), None, "surface/primary")
        self.assertIn("--c-section-pad-x:", css)
        self.assertIn("--c-nav-pad-block:", css)
        self.assertIn("--c-section-pad-top:", css)
        self.assertIn("--c-block-gap:", css)

    def test_scaffolds_have_no_scanner_visible_literal_fallbacks(self):
        """AS-24 (scanner-faithful): spacing-prop declarations inside SECTION-scoped
        selectors must carry no literal var() fallback — that is exactly the class
        the provenance gate unwraps and flags (the remote-e2e 6.25rem blocker)."""
        import re
        import token_provenance as tp
        offenders = []
        blobs = [cs.SCAFFOLD_BASE_CSS, cs.SCAFFOLD_BANDED_CSS, cs.SCAFFOLD_HERO_CSS,
                 getattr(cs, "SCAFFOLD_CONVERSION_CSS", "")]
        for blob in blobs:
            stripped = tp._COMMENT_RE.sub(lambda m: " " * len(m.group(0)), blob)
            for sel, _s, b0, b1 in tp._iter_rules(stripped, 0, len(stripped)):
                for dm in tp._DECL_RE.finditer(stripped[b0:b1]):
                    prop = dm.group(1).lower()
                    if prop.startswith("--") or prop not in tp._SPACING_PROPS:
                        continue
                    if not tp._SECTION_SEL_RE.search(sel):
                        continue
                    for m in re.finditer(r"var\(--[a-z0-9-]+\s*,\s*([^()]+)\)",
                                         dm.group(2)):
                        if re.search(r"\d+(\.\d+)?(rem|px|em|ch)", m.group(1)):
                            offenders.append(f"{sel.strip()[:40]} {prop}: {m.group(0)}")
        self.assertEqual(offenders, [])


class FooterSurfaceRole(unittest.TestCase):
    """Blockers 5+10 (AS-35): chrome footer surface is a per-brand role resolution."""

    def _doc(self, footer_bg=None, surfaces=None):
        doc = copy.deepcopy(FIXTURE)
        if surfaces is not None:
            doc["tokens"]["surfaces"] = surfaces
        if footer_bg is not None:
            doc["footer"] = {"surface": {"bg": footer_bg}}
        return doc

    def test_light_measured_footer_picks_light_role(self):
        doc = self._doc("#f6f5f9", {
            "surface/primary": {"bg": "#ffffff"},
            "surface/raised": {"bg": "#f6f5f9"},
            "surface/inverse-strong": {"bg": "#0f1d3d"},
        })
        self.assertEqual(cp.footer_surface_role(doc), "surface/raised")

    def test_near_black_measured_footer_keeps_inverse_strong(self):
        doc = self._doc("#181313", {
            "surface/primary": {"bg": "#faf0e8"},
            "surface/inverse-strong": {"bg": "#1b150f"},
        })
        self.assertEqual(cp.footer_surface_role(doc), "surface/inverse-strong")

    def test_silent_brand_keeps_default(self):
        doc = self._doc(None, {
            "surface/primary": {"bg": "#faf0e8"},
            "surface/inverse-strong": {"bg": "#1b150f"},
        })
        self.assertEqual(cp.footer_surface_role(doc), cp.FOOTER_SURFACE_DEFAULT)


class RecursiveAssetDiscovery(unittest.TestCase):
    """Blocker 6: subdirectory assets are inventoried and copied."""

    def test_inventory_and_copy_include_subdirs(self):
        with tempfile.TemporaryDirectory() as td:
            brand = Path(td) / "brand"
            (brand / "assets" / "logos").mkdir(parents=True)
            (brand / "assets" / "logos" / "logo-acme.svg").write_text("<svg/>")
            (brand / "assets" / "hero.webp").write_bytes(b"x")
            (brand / "assets" / "fonts").mkdir()
            (brand / "assets" / "fonts" / "face.woff2").write_bytes(b"x")
            inv = cs.brand_image_inventory(brand)
            self.assertIn("logo-acme.svg", inv)
            self.assertIn("hero.webp", inv)
            self.assertNotIn("face.woff2", inv)   # fonts are not image assets
            out = Path(td) / "out-assets"
            cs.copy_assets(brand, out)
            self.assertTrue((out / "logo-acme.svg").exists())
            self.assertTrue((out / "hero.webp").exists())


class PreviewTierSafety(unittest.TestCase):
    """Blocker 7 (AS-36): missing copy keys render empty; specimens derive per brand."""

    def test_copy_for_tolerates_missing_keys(self):
        c = cs.copy_for({"id": "no-such-layout"})
        self.assertEqual(c["panelTitle"], c.get("no-such-key", ""))
        self.assertEqual(c["definitely-not-a-key"], "")

    def test_specimen_headline_derives_from_measured_copy(self):
        import render_components_preview as rcp
        doc = copy.deepcopy(FIXTURE)
        doc["brand"] = {"name": "Acme"}
        doc["layouts"] = [{"id": "hero", "blockMapping": [
            {"slot": "heading", "component": "Heading",
             "props": {"Text": "Measured brand headline"}}]}]
        self.assertEqual(rcp._specimen(doc)["headline"], "Measured brand headline")
        doc["layouts"] = []
        self.assertEqual(rcp._specimen(doc)["headline"], "Acme")


class SelfHostedFontRegistry(unittest.TestCase):
    """Schema-gap 8: brand.yaml selfHostedFonts registers faces declaratively."""

    def _doc(self):
        doc = copy.deepcopy(FIXTURE)
        doc["tokens"]["type"]["display-hero"] = {
            "family": "Bossa", "renderProxy": "Lexend Deca", "sizeRem": {"base": 2.875}}
        doc["selfHostedFonts"] = [
            {"family": "Bossa", "faces": [
                {"weight": 400, "files": ["Bossa-Regular.woff2"]}]}]
        return doc

    def test_registry_merges_brand_entries(self):
        reg = cs.brand_self_hosted_fonts(self._doc())
        self.assertIn("Bossa", reg)
        # contamination fix: the registry is built ONLY from the brand's own
        # declarations — no module-level legacy entries from another brand.
        self.assertEqual(set(reg), {"Bossa"})
        self.assertEqual(reg["Bossa"]["faces"][0]["files"], ["Bossa-Regular.woff2"])

    def test_family_detected_for_display_role(self):
        self.assertIn("Bossa", cs.self_hosted_families(self._doc()))

    def test_registered_faces_resolve_from_full_css_stack(self):
        doc = self._doc()
        doc["tokens"]["type"]["display-hero"]["family"] = (
            '"Bossa", "Fallback Serif", serif')
        self.assertEqual(cs.self_hosted_families(doc), ["Bossa"])

    def test_absent_files_emit_no_font_face(self):
        with tempfile.TemporaryDirectory() as td:
            css = cs.font_face_css(Path(td), self._doc())
            self.assertEqual(css, "")            # registry present, files absent

    def test_present_files_emit_font_face(self):
        with tempfile.TemporaryDirectory() as td:
            fonts = Path(td) / "assets" / "fonts"
            fonts.mkdir(parents=True)
            (fonts / "Bossa-Regular.woff2").write_bytes(b"x")
            css = cs.font_face_css(Path(td), self._doc())
            self.assertIn("font-family: 'Bossa'", css)
            self.assertIn("format('woff2')", css)


class InsetArtPanel(unittest.TestCase):
    """Schema-gap 9 (AS-37): style-gated inset art panel with brand-owned paint."""

    def test_style_flag_parses(self):
        self.assertEqual(styles.load_style("corporate-saas-clean").structure.art_panel,
                         "inset")
        self.assertEqual(styles.load_style("editorial-luxury").structure.art_panel,
                         "none")

    def test_permission_gating(self):
        class _Ctx:
            active = True
            structure = None
        ctx = _Ctx()
        ctx.structure = styles.load_style("corporate-saas-clean").structure
        self.assertTrue(cs._art_panel_permitted(ctx))
        ctx2 = _Ctx()
        ctx2.structure = styles.load_style("radical-editorial").structure
        self.assertFalse(cs._art_panel_permitted(ctx2))
        self.assertTrue(cs._art_panel_permitted(cs.inactive_context()))

    def test_panel_hero_renders_with_brand_treatment_art(self):
        doc = copy.deepcopy(FIXTURE)
        doc["neverDo"] = [{"id": "never-typographic-primary"}]
        doc["heroTreatment"] = {"value": {"asset": "bg-noise.webp"}}
        doc[cs.ASSET_INVENTORY_KEY] = ["bg-noise.webp"]
        ctx = cr.make_context(doc, "surface/primary", {})
        layout = {"id": "hero", "archetype": "stack", "useCase": "hero",
                  "_artPanel": {}}
        html = cs.compose_stack_hero(doc, layout, ctx, [
            {"role": "title", "contract": "heading", "html": "<h1>H</h1>"}],
            cs.inactive_context())
        self.assertIn("cs-hero-panel", html)
        self.assertIn("assets/bg-noise.webp", html)

    def test_declared_but_absent_art_paints_plain_panel(self):
        doc = copy.deepcopy(FIXTURE)
        doc["heroTreatment"] = {"value": {"asset": "bg-noise.webp"}}
        doc[cs.ASSET_INVENTORY_KEY] = []
        ctx = cr.make_context(doc, "surface/primary", {})
        layout = {"id": "hero", "archetype": "stack", "useCase": "hero",
                  "_artPanel": {}}
        html = cs.compose_stack_hero(doc, layout, ctx, [], cs.inactive_context())
        self.assertIn("cs-hero-panel", html)
        self.assertNotIn("background-image", html)


if __name__ == "__main__":
    unittest.main()
