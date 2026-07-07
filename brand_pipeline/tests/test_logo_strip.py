#!/usr/bin/env python3
"""Unit tests for the logo-strip device (AS-33, logo-strip 2026-07).

Covers:
  - adapter routing on DISK EVIDENCE, both composition shapes (one list-copy logo
    slot / one slot per mark): disk-backed asset -> logo-strip image entry; metadata
    without a file -> uppercase text caption; neither -> dropped (never a wordmark);
  - the sanitize->route pipeline end to end: a filename WITHOUT a file on disk is
    stripped by _sanitize_assets and falls back to the text device;
  - alt provenance: alts derive from the entry's own alt/label metadata (or the asset
    filename stem), never empty, never a foreign-brand literal;
  - _inline_props logo contract: a src-bearing usage renders IMAGE mode (payload
    unwrapped, AS-30), text mode unchanged;
  - compose_generic_flow: image entries group into ONE .cs-logo-strip row; the section
    stamps its resolved device (image | text | empty) when the layout is a logo wall;
  - gate logo-wall-integrity (G14): image device with on-disk srcs + alts passes;
    missing-on-disk src, empty alt, empty device, and text device without captions
    fail; pages without stamped logo walls pass vacuously;
  - styles: the three style files parse their qualitative logoStrip flags; the shared
    treatment helper emits per flag and stays silent for a silent style.

Run:  ./venv/bin/python -m unittest brand_pipeline.tests.test_logo_strip
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
import compose_section as cs  # noqa: E402
import onbrand_check as oc  # noqa: E402
import styles  # noqa: E402
from tests.test_tokens_css import FIXTURE  # noqa: E402


def _wall_section(slots):
    return {"id": "logos", "useCase": "logos", "archetype": "stack",
            "surfaceIntent": "primary", "slots": slots}


class AdapterRoutingListShape(unittest.TestCase):
    """ONE list-copy logo slot (the deterministic-replay shape)."""

    def test_disk_backed_items_route_to_image_device(self):
        sec = _wall_section([
            {"name": "logos", "role": "logo-wall", "contract": "logo",
             "copy": [{"alt": "DoorDash", "asset": {"src": "assets/doordash-logo.svg"}},
                      {"alt": "eBay", "asset": {"src": "assets/ebay-logo.svg"}}]}])
        layout = cfc.composition_to_layout(sec)
        self.assertEqual(layout["archetype"], "generic-flow")
        self.assertTrue(layout.get("_logoWall"))
        logos = [m for m in layout["blockMapping"] if m["contract"] == "logo"]
        self.assertEqual(len(logos), 2)
        for m in logos:
            self.assertEqual(m["slot"], "logo-strip")
            self.assertTrue(m["usage"]["src"].startswith("assets/"))
        self.assertEqual([m["usage"]["alt"] for m in logos], ["DoorDash", "eBay"])

    def test_fileless_items_route_to_text_captions(self):
        sec = _wall_section([
            {"name": "logos", "role": "logo-wall", "contract": "logo",
             "copy": [{"alt": "DoorDash"}, {"alt": "eBay"}]}])
        layout = cfc.composition_to_layout(sec)
        caps = [m for m in layout["blockMapping"] if m["contract"] == "caption"]
        self.assertEqual([c["usage"]["text"] for c in caps], ["DoorDash", "eBay"])
        self.assertEqual([c["usage"]["case"] for c in caps], ["upper", "upper"])
        self.assertFalse([m for m in layout["blockMapping"] if m["contract"] == "logo"])

    def test_mixed_wall_routes_per_entry(self):
        sec = _wall_section([
            {"name": "logos", "role": "logo-wall", "contract": "logo",
             "copy": [{"alt": "DoorDash", "asset": {"src": "assets/doordash-logo.svg"}},
                      {"alt": "Acme"}]}])
        layout = cfc.composition_to_layout(sec)
        kinds = [m["contract"] for m in layout["blockMapping"]]
        self.assertEqual(kinds, ["logo", "caption"])

    def test_entry_with_neither_maps_to_nothing(self):
        sec = _wall_section([
            {"name": "logos", "role": "logo-wall", "contract": "logo",
             "copy": [{}, {"alt": "eBay"}]}])
        layout = cfc.composition_to_layout(sec)
        self.assertEqual(len(layout["blockMapping"]), 1)  # the empty entry vanished


class AdapterRoutingSlotShape(unittest.TestCase):
    """One slot PER mark (the live-generation shape that leaked wordmarks)."""

    def _slots(self):
        return [
            {"name": "logo-1", "role": "logo", "contract": "logo",
             "asset": {"src": "assets/doordash-logo.svg", "alt": "DoorDash"}},
            {"name": "logo-2", "role": "logo", "contract": "logo",
             "asset": {"src": "assets/ebay-logo.svg", "alt": "eBay"}},
        ]

    def test_disk_backed_slots_route_to_image_device(self):
        layout = cfc.composition_to_layout(_wall_section(self._slots()))
        logos = [m for m in layout["blockMapping"] if m["contract"] == "logo"]
        self.assertEqual([m["usage"]["alt"] for m in logos], ["DoorDash", "eBay"])
        self.assertTrue(all(m["slot"] == "logo-strip" for m in logos))

    def test_srcless_slot_falls_back_to_alt_caption(self):
        slots = [{"name": "logo-1", "role": "logo", "contract": "logo",
                  "asset": {"alt": "DoorDash"}}]  # src stripped (file didn't exist)
        layout = cfc.composition_to_layout(_wall_section(slots))
        self.assertEqual([(m["contract"], m["usage"]["text"])
                          for m in layout["blockMapping"]],
                         [("caption", "DoorDash")])

    def test_slot_with_neither_never_becomes_a_wordmark(self):
        slots = [{"name": "logo-1", "role": "logo", "contract": "logo", "asset": None}]
        layout = cfc.composition_to_layout(_wall_section(slots))
        self.assertEqual(layout["blockMapping"], [])
        self.assertTrue(layout.get("_logoWall"))

    def test_alt_derives_from_filename_when_metadata_silent(self):
        slots = [{"name": "logo-1", "role": "logo", "contract": "logo",
                  "asset": {"src": "assets/youth-on-course.png"}}]
        layout = cfc.composition_to_layout(_wall_section(slots))
        self.assertEqual(layout["blockMapping"][0]["usage"]["alt"], "youth on course")


class SanitizeThenRoute(unittest.TestCase):
    """End to end through _sanitize_assets: the filename-without-a-file discipline."""

    def test_filename_without_file_is_text_filename_with_file_is_image(self):
        with tempfile.TemporaryDirectory() as td:
            brand_dir = Path(td)
            (brand_dir / "assets").mkdir()
            (brand_dir / "assets" / "real-logo.svg").write_text("<svg/>")
            comp = {"sections": [_wall_section([
                {"name": "logos", "role": "logo-wall", "contract": "logo",
                 "copy": [{"alt": "Real Co", "asset": "real-logo.svg"},
                          {"alt": "Ghost Co", "asset": "invented-logo.svg"}]}])]}
            clean = cfc._sanitize_assets(comp, brand_dir)
            layout = cfc.composition_to_layout(clean["sections"][0])
            entries = [(m["contract"], m["usage"].get("src"),
                        m["usage"].get("alt") or m["usage"].get("text"))
                       for m in layout["blockMapping"]]
            self.assertEqual(entries, [("logo", "assets/real-logo.svg", "Real Co"),
                                       ("caption", None, "Ghost Co")])


class InlinePropsLogo(unittest.TestCase):
    def test_src_bearing_usage_unwraps_to_image_mode(self):
        props = cs._inline_props("logo", "logo item",
                                 {"src": "assets/x.svg", "alt": "X"}, _ctx())
        self.assertEqual(props["src"], "assets/x.svg")
        self.assertEqual(props["alt"], "X")
        html = cr.render_logo(_doc(), _ctx(), props)
        self.assertIn('c-logo--img', html)
        self.assertIn('src="assets/x.svg"', html)
        self.assertIn('alt="X"', html)
        self.assertNotIn("c-glyph", html)  # never the wordmark device

    def test_text_mode_unchanged(self):
        props = cs._inline_props("logo", "wordmark", {"text": "Ravine"}, _ctx())
        self.assertEqual(props, {"text": "Ravine"})


def _doc():
    return copy.deepcopy(FIXTURE)


def _ctx():
    return cr.ComponentContext(surface_role="surface/primary", is_dark=False)


class GenericFlowStrip(unittest.TestCase):
    def _render(self, mapping, logo_wall=True):
        layout = {"id": "logos", "archetype": "generic-flow",
                  "blockMapping": mapping}
        if logo_wall:
            layout["_logoWall"] = True
        doc = _doc()
        rendered = cs.render_slots(doc, layout, _ctx())
        return cs.compose_generic_flow(doc, layout, _ctx(), rendered, None)

    def test_image_entries_group_into_one_strip(self):
        html = self._render([
            {"slot": "flow", "role": "caption", "contract": "eyebrow",
             "usage": {"text": "Trusted by teams"}},
            {"slot": "logo-strip", "role": "logo item", "contract": "logo",
             "usage": {"src": "assets/a.svg", "alt": "A"}},
            {"slot": "logo-strip", "role": "logo item", "contract": "logo",
             "usage": {"src": "assets/b.svg", "alt": "B"}},
        ])
        self.assertEqual(html.count('class="cs-logo-strip"'), 1)
        self.assertEqual(html.count("cs-logo-strip-item"), 2)
        self.assertIn('data-logo-device="image"', html)

    def test_text_fallback_stamps_text_device(self):
        html = self._render([
            {"slot": "flow", "role": "logo item", "contract": "caption",
             "usage": {"text": "DoorDash", "case": "upper"}}])
        self.assertIn('data-logo-device="text"', html)
        self.assertNotIn("cs-logo-strip", html)

    def test_empty_wall_stamps_empty(self):
        html = self._render([])
        self.assertIn('data-logo-device="empty"', html)

    def test_non_logo_sections_carry_no_stamp(self):
        html = self._render([
            {"slot": "flow", "role": "module caption 1", "contract": "caption",
             "usage": {"text": "Hello"}}], logo_wall=False)
        self.assertNotIn("data-logo-device", html)


class GateLogoWallIntegrity(unittest.TestCase):
    def _row(self, html, missing=()):
        return oc._check_logo_wall(html, {"missing_imgs": list(missing)})

    def _img_section(self, src="assets/a.svg", alt="A"):
        return (f'<section class="cs-section cs-flow-sec" data-logo-device="image">'
                f'<div class="cs-logo-strip"><div class="cs-logo-strip-item">'
                f'<a class="c-logo c-logo--img" href="#">'
                f'<img class="c-logo-img" src="{src}" alt="{alt}"></a>'
                f"</div></div></section>")

    def test_image_device_on_disk_passes(self):
        ok, detail = self._row(self._img_section())
        self.assertTrue(ok, detail)

    def test_missing_on_disk_src_fails(self):
        ok, detail = self._row(self._img_section(), missing=["assets/a.svg"])
        self.assertFalse(ok)
        self.assertIn("missing on disk", detail)

    def test_empty_alt_fails(self):
        ok, detail = self._row(self._img_section(alt=""))
        self.assertFalse(ok)
        self.assertIn("missing alt", detail)

    def test_empty_device_fails(self):
        ok, detail = self._row(
            '<section class="cs-section" data-logo-device="empty"></section>')
        self.assertFalse(ok)
        self.assertIn("neither", detail)

    def test_text_device_with_captions_passes_without_fails(self):
        good = ('<section data-logo-device="text">'
                '<p class="c-caption">DOORDASH</p></section>')
        bad = '<section data-logo-device="text"><p class="c-caption"> </p></section>'
        self.assertTrue(self._row(good)[0])
        self.assertFalse(self._row(bad)[0])

    def test_no_logo_walls_vacuous_pass(self):
        ok, detail = self._row("<section class='cs-section'></section>")
        self.assertTrue(ok)
        self.assertIn("no logo-wall sections", detail)

    def test_row_registered_as_composition_invariant(self):
        checks = oc.check_composition(
            _doc(), "<html></html>", {},
            {"missing_imgs": [], "css_vars": {}, "surface_bg": "#ffffff",
             "token_index": None})
        ids = [c[0] for c in checks]
        self.assertIn("logo-wall-integrity", ids)


class StyleLogoStripFlag(unittest.TestCase):
    def test_three_styles_parse_their_flags(self):
        self.assertEqual(styles.load_style("corporate-saas-clean").structure.logo_strip,
                         "monochrome")
        self.assertEqual(styles.load_style("editorial-luxury").structure.logo_strip,
                         "reduced")
        self.assertEqual(styles.load_style("radical-editorial").structure.logo_strip,
                         "plain")

    def test_treatment_emission_per_flag(self):
        class _Ctx:
            pass

        for flag, needle, absent in (
                ("monochrome", "grayscale(1)", None),
                ("reduced", "opacity: 0.78", "grayscale"),
                ("plain", None, ".cs-logo-strip"),
                ("", None, ".cs-logo-strip")):
            ctx = _Ctx()
            ctx.structure = styles.StyleStructure()
            ctx.structure.logo_strip = flag
            css = cs.logo_strip_treatment_css(ctx)
            if needle:
                self.assertIn(needle, css, flag)
            if absent:
                self.assertNotIn(absent, css, flag)

    def test_treatment_motion_rides_brand_tokens(self):
        class _Ctx:
            pass
        ctx = _Ctx()
        ctx.structure = styles.StyleStructure()
        ctx.structure.logo_strip = "monochrome"
        css = cs.logo_strip_treatment_css(ctx)
        self.assertIn("var(--c-motion-fast)", css)
        self.assertIn("var(--c-ease)", css)


if __name__ == "__main__":
    unittest.main()
