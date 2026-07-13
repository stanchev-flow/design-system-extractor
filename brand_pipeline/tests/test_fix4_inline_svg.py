#!/usr/bin/env python3
"""Regression tests for the fix4 batch (2026-07): the single-color glyph channel
renders SANITIZED INLINE <svg> markup instead of data-URI currentColor masks
(technique parity with source sites; styleable icons for kit consumers). The
mask stays as the DEGRADE channel for artwork that cannot be verified
single-ink — never a silent recolor.

  - SANITIZER (`component_render.sanitize_inline_svg`): strips script /
    foreignObject / on* handlers / comments / external references; guarantees
    xmlns + viewBox (synthesized from numeric width/height); drops root
    width/height/class/style/preserveAspectRatio/overflow (CSS owns the box;
    default xMidYMid meet ≙ the mask channel's `center / contain`); stamps
    `aria-hidden="true" focusable="false"`; drops unreferenced ids and
    tokenizes referenced ones for per-instance dedupe (`_svg_instance`);
    verifies SINGLE-INK before normalizing paints to currentColor — multi-color
    artwork returns None and keeps the mask/image channel.
  - PREPARE (`prepare_chrome_glyphs`): SVG glyph nodes stamp `_inlineSvg`
    alongside `_dataUri`; unverifiable artwork stamps only `_dataUri`.
  - EMISSION: arrow-link / nav chevrons / utility icons / footer socials nest
    the sanitized svg in the SAME host span (same classes, so hover nudge /
    chevron rotation / motion contracts ride unchanged); mask paint is gated
    under `--mask` modifier classes that only the degrade channel emits.
  - VISIBILITY (retired file:// mask-invisibility guard, inverted): the inline
    element paints a nonzero box on a file:// page.

Run:  ./venv/bin/python -m unittest brand_pipeline.tests.test_fix4_inline_svg
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

import component_render as cr    # noqa: E402
import compose_page as cp        # noqa: E402

FIXTURE_DOC = {
    "brand": {"name": "Fixture"},
    "tokens": {
        "colors": {"text/on-primary": {"value": "#111111"}},
        "surfaces": {
            "surface/primary": {"bg": "#ffffff", "textPrimary": "text/on-primary"},
        },
        "type": {"body": {"family": "Inter", "sizeRem": {"base": 1.0}}},
    },
}


def _ctx(doc=None):
    d = doc or FIXTURE_DOC
    return cr.make_context(d, "surface/primary", d["tokens"]["surfaces"]["surface/primary"])


# ── 1) sanitizer: hygiene ─────────────────────────────────────────────────────────


class SanitizeHygieneTest(unittest.TestCase):
    def test_script_and_foreignobject_stripped(self):
        out = cr.sanitize_inline_svg(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16">'
            '<script>alert(1)</script>'
            '<foreignObject><body xmlns="http://www.w3.org/1999/xhtml">x</body>'
            '</foreignObject><path d="M0 0h16v16"/></svg>')
        self.assertIsNotNone(out)
        self.assertNotIn("<script", out)
        self.assertNotIn("foreignObject", out)
        self.assertIn("<path", out)

    def test_event_attributes_stripped(self):
        out = cr.sanitize_inline_svg(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16">'
            '<path onclick="steal()" onmouseover="x()" d="M0 0h16"/></svg>')
        self.assertNotIn("onclick", out)
        self.assertNotIn("onmouseover", out)

    def test_external_href_dropped_and_external_url_refused(self):
        out = cr.sanitize_inline_svg(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16">'
            '<a href="https://evil.example"><path d="M0 0h16"/></a></svg>')
        self.assertIsNotNone(out)
        self.assertNotIn("evil.example", out)
        self.assertIsNone(cr.sanitize_inline_svg(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16">'
            '<path clip-path="url(https://evil.example/c.svg#c)" d="M0 0h16"/></svg>'))

    def test_comments_and_prolog_stripped(self):
        out = cr.sanitize_inline_svg(
            '<?xml version="1.0"?><!-- Generator: Adobe Illustrator -->'
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16">'
            '<path d="M0 0h16"/></svg>')
        self.assertNotIn("<!--", out)
        self.assertNotIn("<?xml", out)

    def test_xmlns_injected_when_missing_preserved_when_present(self):
        out = cr.sanitize_inline_svg('<svg viewBox="0 0 16 16"><path d="M0 0h16"/></svg>')
        self.assertIn('xmlns="http://www.w3.org/2000/svg"', out)
        out2 = cr.sanitize_inline_svg(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16">'
            '<path d="M0 0h16"/></svg>')
        self.assertEqual(out2.count("xmlns="), 1)

    def test_viewbox_preserved_or_synthesized_or_refused(self):
        out = cr.sanitize_inline_svg(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
            'width="32" height="32"><path d="M0 0h24"/></svg>')
        self.assertIn('viewBox="0 0 24 24"', out)
        synth = cr.sanitize_inline_svg(
            '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="10">'
            '<path d="M0 0h20"/></svg>')
        self.assertIn('viewBox="0 0 20 10"', synth)
        self.assertIsNone(cr.sanitize_inline_svg(
            '<svg xmlns="http://www.w3.org/2000/svg"><path d="M0 0h16"/></svg>'))

    def test_root_presentation_attrs_dropped(self):
        out = cr.sanitize_inline_svg(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 14 14" '
            'preserveAspectRatio="none" width="100%" height="100%" '
            'overflow="visible" style="display: block;" class="foreign-scss__x">'
            '<path d="M0 0h14"/></svg>')
        root = out.split(">", 1)[0]
        for attr in ("width=", "height=", "preserveAspectRatio=", "overflow=",
                     "style=", "class="):
            self.assertNotIn(attr, root)

    def test_decorative_aria_stamped(self):
        out = cr.sanitize_inline_svg(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" '
            'aria-hidden="true"><path d="M0 0h16"/></svg>')
        self.assertEqual(out.count('aria-hidden="true"'), 1)
        self.assertIn('focusable="false"', out)

    def test_inner_foreign_classes_dropped(self):
        out = cr.sanitize_inline_svg(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16">'
            '<path class="module-scss__glyph" d="M0 0h16"/></svg>')
        self.assertNotIn("class=", out.split(">", 1)[1])


# ── 2) sanitizer: single-ink verification + normalization ──────────────────────────


class SanitizeInkTest(unittest.TestCase):
    def test_single_concrete_fill_normalizes_to_currentcolor(self):
        out = cr.sanitize_inline_svg(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16">'
            '<path fill="#383A3D" d="M0 0h16"/><path fill="#383a3d" d="M0 8h16"/></svg>')
        self.assertIsNotNone(out)
        self.assertNotIn("#383A3D", out)
        self.assertEqual(out.count('fill="currentColor"'), 2)

    def test_var_with_fallback_resolves_and_normalizes(self):
        out = cr.sanitize_inline_svg(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 13 13" fill="none">'
            '<path d="M0 0h13" fill="var(--fill-0, #383A3D)"/></svg>')
        self.assertIsNotNone(out)
        self.assertIn('fill="currentColor"', out)
        self.assertIn('fill="none"', out)       # neutral values survive untouched

    def test_var_without_fallback_is_unverifiable(self):
        self.assertIsNone(cr.sanitize_inline_svg(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16">'
            '<path fill="var(--fill-0)" d="M0 0h16"/></svg>'))

    def test_multi_color_refused(self):
        self.assertIsNone(cr.sanitize_inline_svg(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16">'
            '<path fill="#ff0000" d="M0 0h16"/><path fill="#0000ff" d="M0 8h16"/></svg>'))

    def test_stroke_only_glyph_normalizes(self):
        out = cr.sanitize_inline_svg(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="none">'
            '<path d="M4 6L8 10L12 6" stroke="#1d1d1f" stroke-width="1.5"/></svg>')
        self.assertIn('stroke="currentColor"', out)
        self.assertIn('stroke-width="1.5"', out)

    def test_default_black_glyph_gains_root_currentcolor(self):
        out = cr.sanitize_inline_svg(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16">'
            '<path d="M0 0h16v16H0z"/></svg>')
        self.assertIn('fill="currentColor"', out.split(">", 1)[0])

    def test_unverifiable_payloads_refused(self):
        for body in ('<style>.a{fill:red}</style><path class="a" d="M0 0h16"/>',
                     '<linearGradient id="g"/><path fill="url(#g)" d="M0 0h16"/>',
                     '<image href="#x"/>'):
            self.assertIsNone(cr.sanitize_inline_svg(
                f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16">{body}</svg>'),
                msg=body)

    def test_style_decl_fill_normalizes(self):
        out = cr.sanitize_inline_svg(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16">'
            '<path style="fill: #292929; opacity: 0.9" d="M0 0h16"/></svg>')
        self.assertIn("fill: currentColor", out)
        self.assertIn("opacity: 0.9", out)


# ── 3) sanitizer: id discipline + per-instance dedupe ─────────────────────────────


class SanitizeIdTest(unittest.TestCase):
    def test_unreferenced_ids_dropped(self):
        out = cr.sanitize_inline_svg(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 14 14">'
            '<path id="Vector" fill="#383a3d" d="M0 0h14"/></svg>')
        self.assertNotIn('id="', out)

    def test_referenced_ids_tokenized_and_instances_dedupe(self):
        out = cr.sanitize_inline_svg(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16">'
            '<clipPath id="clip0"><rect width="16" height="16"/></clipPath>'
            '<g clip-path="url(#clip0)"><path fill="#111" d="M0 0h16"/></g></svg>')
        self.assertIn(cr._SVG_GID_TOKEN, out)
        a, b = cr._svg_instance(out), cr._svg_instance(out)
        ids_a = re.findall(r'id="([^"]+)"', a)
        ids_b = re.findall(r'id="([^"]+)"', b)
        self.assertEqual(len(ids_a), 1)
        self.assertNotEqual(ids_a, ids_b)               # N inlines cannot collide
        self.assertIn(f'url(#{ids_a[0]})', a)           # internal ref follows its id
        self.assertNotIn(cr._SVG_GID_TOKEN, a)

    def test_tokenless_markup_passes_through(self):
        svg = '<svg viewBox="0 0 16 16"><path d="M0 0h16"/></svg>'
        self.assertIs(cr._svg_instance(svg), svg)


# ── 4) prepare stamps + emission channels ─────────────────────────────────────────


CLEAN_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16">'
             '<path fill="#292929" d="M0 0h16v16H0z"/></svg>')
MULTI_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16">'
             '<path fill="#e00" d="M0 0h16"/><path fill="#00e" d="M0 8h16"/></svg>')


class PrepareStampsTest(unittest.TestCase):
    def _prep(self, svg_text: str) -> dict:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "assets").mkdir()
            (root / "assets" / "g.svg").write_text(svg_text)
            doc = {"footer": {"social": [
                {"network": "x", "icon": {"asset": "assets/g.svg"}}]}}
            cr.prepare_chrome_glyphs(doc, root)
            return doc["footer"]["social"][0]["icon"]

    def test_single_ink_svg_stamps_inline_and_datauri(self):
        icon = self._prep(CLEAN_SVG)
        self.assertIn("_dataUri", icon)
        self.assertIn("_inlineSvg", icon)
        self.assertIn('fill="currentColor"', icon["_inlineSvg"])

    def test_multi_color_svg_stamps_datauri_only(self):
        icon = self._prep(MULTI_SVG)
        self.assertIn("_dataUri", icon)
        self.assertNotIn("_inlineSvg", icon)


class SocialGlyphChannelTest(unittest.TestCase):
    def _footer_html(self, icon_extra: dict) -> str:
        glyphs = [{"network": "youtube", "href": "#",
                   "icon": {"asset": "assets/g.svg", "size": 20,
                            "ink": "rgb(41,41,41)", **icon_extra},
                   "box": {"width": 40, "height": 40}}]
        return cr.render_footer(FIXTURE_DOC, _ctx(), {"socialGlyphs": glyphs})

    def test_inline_channel_nests_svg(self):
        html = self._footer_html(
            {"_inlineSvg": cr.sanitize_inline_svg(CLEAN_SVG), "_dataUri": "data:x"})
        self.assertIn("c-foot-glyph-svg", html)
        self.assertIn("<svg", html)
        self.assertIn("--cfg-ink:rgb(41,41,41)", html)   # measured ink still rides
        self.assertNotIn("c-foot-glyph-mask", html)
        self.assertNotIn("--cfg-mask", html)

    def test_mask_degrade_without_inline(self):
        html = self._footer_html({"_dataUri": "data:image/svg+xml;base64,QQ=="})
        self.assertIn("c-foot-glyph-mask", html)
        self.assertIn("--cfg-mask", html)
        self.assertNotIn("<svg", html.split("c-foot-glyphs", 1)[1].split("</nav>", 1)[0])

    def test_component_css_carries_both_channels(self):
        self.assertIn(".c-arrow--glyph > svg", cr.COMPONENT_CSS)
        self.assertIn(".c-arrow--mask", cr.COMPONENT_CSS)
        # the directory-footer grammar block carries the social channels
        self.assertIn(".c-foot-glyph-svg > svg", cr._FOOT_COLUMNS_CSS)
        self.assertIn(".c-foot-glyph-mask", cr._FOOT_COLUMNS_CSS)

    def test_banner_css_carries_both_channels(self):
        css = cp.UTILITY_BANNER_CSS if hasattr(cp, "UTILITY_BANNER_CSS") else \
            Path(cp.__file__).read_text()
        self.assertIn(".cs-utility-banner-arrow > svg", css)
        self.assertIn(".cs-utility-banner-arrow--mask", css)


# ── 5) motion contracts ride the same hooks ────────────────────────────────────────


class MotionContractTest(unittest.TestCase):
    def test_arrow_nudge_targets_host_class(self):
        # the nudge rides .c-arrow (the host span) — channel-independent
        self.assertIn(".c-arrow-link:hover .c-arrow { transform: translateX",
                      cr.COMPONENT_CSS)

    def test_chevron_rotation_targets_host_class(self):
        doc = {**FIXTURE_DOC, "navbar": {
            "primary": [{"label": "P", "menu": {"columns": [
                {"heading": "G", "links": [{"label": "x"}]}]}}],
            "measured": {"trigger": {"chevron": {
                "asset": "assets/c.svg", "box": {"w": 16, "h": 16},
                "_dataUri": "data:image/svg+xml;base64,QQ==",
                "_inlineSvg": cr.sanitize_inline_svg(CLEAN_SVG)}}}}}
        css = cr.nav_affordance_css(doc)
        self.assertIn(".cs-nav-lang[open] .cs-nav-chev { transform:", css)
        self.assertIn("prefers-reduced-motion", css)
        self.assertIn(".cs-nav-chev > svg", css)
        self.assertIn(".cs-nav-chev--mask", css)


# ── 6) the retired mask-invisibility guard, inverted: inline paints on file:// ─────


class InlineVisibilityTest(unittest.TestCase):
    def test_inline_glyph_paints_nonzero_box_on_file_page(self):
        from playwright.sync_api import sync_playwright
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "assets").mkdir()
            (root / "assets" / "icon-next.svg").write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" '
                'fill="currentColor"><path d="M2 15h24M18 5l10 10-10 10" '
                'stroke="currentColor" stroke-width="3" fill="none"/></svg>')
            doc = {**FIXTURE_DOC,
                   "_assetInventory": ["icon-next.svg"],
                   "buttons": {"textCta": {"style": "text-link-arrow",
                                           "glyph": {"asset": "icon-next.svg",
                                                     "size": "1rem"}}}}
            cr.prepare_chrome_glyphs(doc, root)
            link = cr.render_arrow_link(doc, _ctx(), {"label": "Learn more"})
            page_path = root / "page.html"
            page_path.write_text(
                "<!doctype html><html><head><style>"
                + cr.COMPONENT_CSS +
                "</style></head><body>" + link + "</body></html>")
            with sync_playwright() as pw:
                b = pw.chromium.launch()
                pg = b.new_page()
                pg.goto(page_path.resolve().as_uri())
                box = pg.evaluate(
                    "() => {const s = document.querySelector('.c-arrow--glyph svg');"
                    " const r = s.getBoundingClientRect();"
                    " return {w: r.width, h: r.height,"
                    "  visible: getComputedStyle(s).display !== 'none'}; }")
                b.close()
        self.assertTrue(box["visible"])
        self.assertGreater(box["w"], 4)     # nonzero paint box — visible without
        self.assertGreater(box["h"], 4)     # any network/CORS fetch (file:// safe)


if __name__ == "__main__":
    unittest.main()
