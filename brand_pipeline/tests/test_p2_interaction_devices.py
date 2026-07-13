#!/usr/bin/env python3
"""Fixture-based unit tests for the P2 interaction-device batch (anti-ai-slop.md
AS-40..AS-43 + the replica-gate punch list):

  - AS-42 seam-correct marquee (`compose_generic_flow` + SCAFFOLD_MARQUEE_CSS +
    `compose_page.MARQUEE_SCRIPT`): two IDENTICAL halves, translateX(-50%) loop,
    item-count fallback duration, reduced-motion pause; static row without the stamp.
  - AS-40 accordion open-state (`_compose_accordion_split` via `compose_info_band`):
    native single-open (<details name=…>), exactly one EVIDENCED open item, active
    inversion via the treatment's surface/hoverWash ROLES resolved to layer-1 vars,
    all-idle degrade without body evidence, classic panel without the stamp.
  - edge-cut carousel statics (`compose_features_cards`): cut-at-viewport track,
    card plates on brand vars, mark-height media, bound action row.
  - `stamp_pattern_devices`: sanctioned pattern treatments → private layout hints.
  - utility banner (`compose_page.build_page`): evidence-gated chrome, absent ⇒
    byte-identical page.
  - AS-41 reveal failsafe (REVEAL_SCRIPT: gate class + early-outs + timed fallback).
  - AS-43 disabled states are colors, never opacity (measured family CSS resets the
    harness dim; shared component CSS carries no opacity-disabled rule).

Run:  ./venv/bin/python -m unittest brand_pipeline.tests.test_p2_interaction_devices
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path
from unittest import mock

_BRAND_PIPELINE = Path(__file__).resolve().parent.parent
if str(_BRAND_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_BRAND_PIPELINE))

import compose_from_composition as cfc  # noqa: E402
import compose_page as cp            # noqa: E402
import compose_section as cs         # noqa: E402
import component_render as cr        # noqa: E402
import layout_library as ll          # noqa: E402
import render_components_preview as rp  # noqa: E402

_REMOTE = _BRAND_PIPELINE.parent / "runs" / "remote" / "brand" / "brand.yaml"


# ── shared minimal fixture (brand-agnostic; no run data) ───────────────────────────

FIXTURE_DOC = {
    "brand": {"name": "Fixture"},
    "tokens": {
        "colors": {
            "text/on-primary": {"value": "#111111"},
            "text/on-inverse": {"value": "#ffffff"},
            "accent/warm-wash": {"value": "#fceef1"},
        },
        "surfaces": {
            "surface/primary": {"bg": "#ffffff", "textPrimary": "text/on-primary"},
            "surface/accent": {"bg": "#511621", "textPrimary": "text/on-inverse"},
        },
        "type": {"body": {"family": "Inter", "sizeRem": {"base": 1.0}}},
        "spacing": {},
    },
}


def _ctx():
    return cr.make_context(FIXTURE_DOC, "surface/primary",
                           FIXTURE_DOC["tokens"]["surfaces"]["surface/primary"])


def _pattern(treatments: list[dict]) -> ll.Pattern:
    return ll.Pattern(
        id="test-pattern", use_case="features", archetype_ref="split",
        surface_intent="any", intent="test", content_shape={},
        special_treatments=treatments, responsive={}, variant_knobs={},
        origin="extracted", confidence="high", scope="design-language",
        provenance=[])


# ── stamp_pattern_devices ──────────────────────────────────────────────────────────

class StampPatternDevicesTest(unittest.TestCase):
    def _stamp(self, treatments, layout=None):
        layout = layout if layout is not None else {"id": "sec"}
        with mock.patch.object(cs, "resolve_pattern",
                               return_value=(_pattern(treatments), "ref")):
            cs.stamp_pattern_devices(FIXTURE_DOC, layout, Path("/tmp/x.yaml"))
        return layout

    def test_sanctioned_devices_stamp(self):
        lay = self._stamp([
            {"kind": "marquee", "target": "logos", "sanctioned": True},
            {"kind": "inset-emphasis", "target": "list", "sanctioned": True,
             "surfaceRole": "surface/accent", "hoverWash": "accent/warm-wash"},
            {"kind": "edge-cut", "target": "cards", "sanctioned": True},
        ])
        self.assertEqual(lay["_marquee"], {"target": "logos"})
        self.assertEqual(lay["_accordion"], {"surfaceRole": "surface/accent",
                                             "hoverWash": "accent/warm-wash",
                                             "affordance": None})
        self.assertTrue(lay["_edgeCut"])

    def test_unsanctioned_treatments_do_not_stamp(self):
        lay = self._stamp([{"kind": "marquee", "target": "logos"},
                           {"kind": "edge-cut", "target": "cards", "sanctioned": False}])
        self.assertNotIn("_marquee", lay)
        self.assertNotIn("_edgeCut", lay)

    def test_no_pattern_no_stamp(self):
        lay = {"id": "sec"}
        with mock.patch.object(cs, "resolve_pattern", return_value=(None, "none")):
            cs.stamp_pattern_devices(FIXTURE_DOC, lay, Path("/tmp/x.yaml"))
        self.assertEqual(lay, {"id": "sec"})

    def test_existing_hint_kept(self):
        lay = self._stamp([{"kind": "marquee", "target": "logos", "sanctioned": True}],
                          layout={"id": "sec", "_marquee": {"target": "authored"}})
        self.assertEqual(lay["_marquee"], {"target": "authored"})


# ── AS-42: seam-correct marquee ────────────────────────────────────────────────────

def _logo_rendered(n=3, group="logos"):
    return [{"slot": "logo-strip", "contract": "logo", "role": "logo item",
             "group": group, "html": f'<a class="c-logo c-logo--img">logo {i}</a>'}
            for i in range(n)]


class MarqueeDeviceTest(unittest.TestCase):
    def test_marquee_renders_two_identical_halves(self):
        layout = {"id": "wall", "_marquee": {"target": "logos"}, "_logoWall": True}
        html = cs.compose_generic_flow(FIXTURE_DOC, layout, _ctx(),
                                       _logo_rendered(3), None)
        halves = re.findall(r'<div class="cs-marquee-half"[^>]*>\n(.*?)\n\s*</div>',
                            html, re.S)
        self.assertEqual(len(halves), 2)
        self.assertEqual(halves[0].strip(), halves[1].strip())
        self.assertEqual(html.count('aria-hidden="true"'), 1)
        # item-count fallback duration (~2s of travel per mark)
        self.assertIn("--cs-marquee-duration: 6s", html)

    def test_no_stamp_keeps_static_row(self):
        layout = {"id": "wall", "_logoWall": True}
        html = cs.compose_generic_flow(FIXTURE_DOC, layout, _ctx(),
                                       _logo_rendered(3), None)
        self.assertNotIn("cs-marquee", html)
        self.assertIn("cs-logo-strip", html)

    def test_marquee_targets_declared_group_only(self):
        layout = {"id": "wall", "_marquee": {"target": "logos"}}
        rendered = _logo_rendered(3, "logos") + _logo_rendered(2, "badges")
        html = cs.compose_generic_flow(FIXTURE_DOC, layout, _ctx(), rendered, None)
        self.assertEqual(html.count("cs-marquee-track"), 1)
        # the non-target group keeps the static strip
        self.assertIn('<div class="cs-logo-strip">', html)

    def test_marquee_css_seam_math(self):
        css = cs.SCAFFOLD_MARQUEE_CSS
        self.assertIn("translateX(-50%)", css)
        self.assertIn("width: max-content", css)
        self.assertIn("prefers-reduced-motion: reduce", css)
        self.assertIn("animation: none", css)

    def test_marquee_script_pxs_constant(self):
        self.assertIn("scrollWidth / speed", cp.MARQUEE_SCRIPT)
        self.assertIn("cs-marquee-track", cp.MARQUEE_SCRIPT)


# ── AS-40: accordion open-state ────────────────────────────────────────────────────

def _acc_layout(**hint):
    return {"id": "features", "_accordion": hint or
            {"surfaceRole": "surface/accent", "hoverWash": "accent/warm-wash"}}


def _acc_copy(rows):
    return {"eyebrow": "How", "heading": "One system", "panelTitle": "", "cta": "",
            "body": "", "quote": "", "caption": "", "rows": rows}


def _compose_acc(layout, rows):
    saved = cs.LAYOUT_COPY
    try:
        cs.LAYOUT_COPY = {**cs.LAYOUT_COPY, layout["id"]: _acc_copy(rows)}
        return cs.compose_info_band(FIXTURE_DOC, layout, _ctx(), [], None)
    finally:
        cs.LAYOUT_COPY = saved


class AccordionDeviceTest(unittest.TestCase):
    ROWS = [("EOR", "Hire anyone, anywhere."), ("Payroll", ""), ("COR", "")]

    def test_single_open_native_group(self):
        html = _compose_acc(_acc_layout(), self.ROWS)
        items = re.findall(r"<details[^>]*>", html)
        self.assertEqual(len(items), 3)
        opens = [i for i in items if " open" in i]
        self.assertEqual(len(opens), 1, items)
        names = set(re.findall(r'name="([^"]+)"', " ".join(items)))
        self.assertEqual(len(names), 1)  # one exclusivity group (AS-40)

    def test_active_item_is_the_evidenced_one(self):
        rows = [("Idle", ""), ("Active", "body evidence"), ("Idle 2", "")]
        html = _compose_acc(_acc_layout(), rows)
        m = re.search(r"<details[^>]* open>.*?</details>", html, re.S)
        self.assertIsNotNone(m)
        self.assertIn("Active", m.group(0))
        self.assertIn("body evidence", m.group(0))

    def test_active_surface_vars_from_roles(self):
        html = _compose_acc(_acc_layout(), self.ROWS)
        self.assertIn("--acc-active-bg: var(--surface-surface-accent)", html)
        self.assertIn("--acc-active-ink: var(--color-text-on-inverse)", html)
        self.assertIn("--acc-hover-bg: var(--color-accent-warm-wash)", html)

    def test_unknown_roles_degrade_without_vars(self):
        html = _compose_acc(_acc_layout(surfaceRole="surface/nope",
                                        hoverWash="accent/nope"), self.ROWS)
        self.assertNotIn("--acc-active-bg", html)
        self.assertNotIn("--acc-hover-bg", html)
        self.assertIn("<details", html)  # the accordion structure still renders

    def test_no_body_evidence_all_idle(self):
        html = _compose_acc(_acc_layout(), [("A", ""), ("B", "")])
        self.assertNotIn(" open>", html)
        self.assertEqual(html.count("<details"), 2)

    def test_no_stamp_keeps_panel_branch(self):
        layout = {"id": "features"}
        saved = cs.LAYOUT_COPY
        try:
            cs.LAYOUT_COPY = {**cs.LAYOUT_COPY,
                              "features": _acc_copy(self.ROWS) | {"panelTitle": "T"}}
            html = cs.compose_info_band(FIXTURE_DOC, layout, _ctx(), [], None)
        finally:
            cs.LAYOUT_COPY = saved
        self.assertNotIn("c-acc-item", html)
        self.assertIn("cs-panel", html)

    def test_accordion_css_state_rides_vars(self):
        css = cs.SCAFFOLD_ACCORDION_CSS
        self.assertIn("--acc-active-bg", css)
        self.assertIn("--acc-hover-bg", css)
        self.assertIn("var(--radius-card, 0)", css)
        self.assertNotIn("#", re.sub(r"/\*.*?\*/", "", css, flags=re.S)
                         .replace("#sec", ""))  # no color literals

    def test_disclosure_animation_rides_motion_vars(self):
        # fid5, refactored to the SHARED source (AS-47): the disclosure animates
        # height 0 -> auto on ::details-content (the <details name=…>-compatible
        # equivalent of grid-rows 0fr->1fr), timed ONLY by the brand's motion
        # aliases; reduced-motion disables the transition. The accordion CONSTANT
        # carries no motion of its own — disclosure_motion_css emits it, gated on
        # the brand's motion facts.
        doc = dict(FIXTURE_DOC)
        doc["voice"] = {"motionSpec": {"easing": {"primary": "ease"},
                                       "durations": {"fast": "150ms", "base": "200ms",
                                                     "slow": "400ms"}}}
        css = cs.disclosure_motion_css(doc, [{"id": "sec", "_accordion": {}}])
        self.assertIn(".c-acc-item::details-content", css)
        self.assertIn("interpolate-size: allow-keywords", css)
        self.assertIn("block-size: 0", css)
        self.assertIn("block-size: auto", css)
        self.assertIn("block-size var(--c-motion-base) var(--c-ease)", css)
        self.assertIn("prefers-reduced-motion: reduce", css)
        # the grid-rows trick cannot run on <details> (rules only; comments may cite it)
        self.assertNotIn("0fr", re.sub(r"/\*.*?\*/", "", css, flags=re.S))
        # the constant itself stays motion-free (no second copy of the mechanic)
        self.assertNotIn("::details-content", cs.SCAFFOLD_ACCORDION_CSS)


# ── fid5: accordion per-item media swap ─────────────────────────────────────────────

def _acc_media_doc(inventory):
    d = dict(FIXTURE_DOC)
    d[cs.ASSET_INVENTORY_KEY] = list(inventory)
    return d


def _compose_acc_media(doc, layout, rows, media):
    saved = cs.LAYOUT_COPY
    try:
        cs.LAYOUT_COPY = {**cs.LAYOUT_COPY,
                          layout["id"]: _acc_copy(rows) | {"rowMedia": media}}
        return cs.compose_info_band(doc, layout, _ctx(), [], None)
    finally:
        cs.LAYOUT_COPY = saved


class AccordionMediaSwapTest(unittest.TestCase):
    ROWS = [("EOR", "Hire anyone, anywhere."), ("Payroll", ""), ("COR", "")]

    def test_media_stack_and_pairing_attrs(self):
        doc = _acc_media_doc(["panel-a.webp", "panel-c.webp"])
        layout = _acc_layout()
        html = _compose_acc_media(doc, layout, self.ROWS,
                                  ["panel-a.webp", "", "panel-c.webp"])
        # bound items carry the pairing attribute; the media-less one does not
        self.assertIn('data-acc-media="0"', html)
        self.assertNotIn('data-acc-media="1"', html)
        self.assertIn('data-acc-media="2"', html)
        # the stack renders over the honest well, one layer per bound item
        self.assertIn('class="cs-acc-media"', html)
        self.assertIn("cs-acc-well", html)
        self.assertIn('data-acc-i="0"', html)
        self.assertIn('src="assets/panel-a.webp"', html)
        self.assertIn('data-acc-i="2"', html)
        # the ACTIVE (evidenced open) item's layer is the server-rendered resting
        # state for no-:has browsers
        m = re.search(r'<img[^>]*data-acc-i="0"[^>]*>', html)
        self.assertIn("is-active", m.group(0))
        # composer stamps the bound indexes for the CSS generator
        self.assertEqual(layout["_accordion"]["mediaIdx"], [0, 2])

    def test_pairing_rules_generated_for_stamped_indexes(self):
        doc = _acc_media_doc(["panel-a.webp", "panel-c.webp"])
        layout = _acc_layout()
        _compose_acc_media(doc, layout, self.ROWS, ["panel-a.webp", "", "panel-c.webp"])
        css = cs.device_scaffold_css([layout])
        self.assertIn('.cs-acc-split:has(.c-acc-item[data-acc-media="0"][open]) '
                      '.cs-acc-media-item[data-acc-i="0"] { opacity: 1; }', css)
        self.assertIn('[data-acc-media="2"]', css)
        self.assertNotIn('[data-acc-media="1"]', css)

    def test_unbound_media_names_degrade_to_well(self):
        # names with no disk evidence render nothing (AS-34): no stack, no attrs,
        # no pairing rules — the honest well keeps the counterweight.
        doc = _acc_media_doc(["panel-a.webp"])
        layout = _acc_layout()
        html = _compose_acc_media(doc, layout, self.ROWS, ["ghost.webp", "", ""])
        self.assertNotIn("cs-acc-media-item", html)
        self.assertNotIn("data-acc-media", html)
        self.assertIn("cs-acc-well", html)
        self.assertNotIn("mediaIdx", layout["_accordion"])
        # no PAIRING rules generated (the static @supports/:has fallback text in the
        # scaffold constant is fine — only the per-index rules are conditional)
        self.assertNotIn('[data-acc-media="0"][open]', cs.device_scaffold_css([layout]))

    def test_no_row_media_keeps_single_path(self):
        doc = _acc_media_doc(["panel-a.webp"])
        layout = _acc_layout()
        html = _compose_acc_media(doc, layout, self.ROWS, [])
        self.assertNotIn("cs-acc-media-item", html)
        self.assertNotIn("data-acc-media", html)

    def test_media_swap_css_rides_motion_vars(self):
        css = cs.SCAFFOLD_ACCORDION_CSS
        # bare aliases (AS-47): unresolved vars invalidate the declaration for
        # motion-less docs — never an invented literal fallback.
        self.assertIn("opacity var(--c-motion-base) var(--c-ease)", css)
        self.assertIn("@supports not selector(:has(a))", css)

    def test_split_copy_carries_row_media(self):
        # the adapter folds items[].media beside rows/rowIcons (schema:
        # section-copy items[].media — the extraction agent authors the values).
        section = {"slots": [{"name": "list", "role": "accordion items",
                              "copy": [{"label": "EOR", "text": "b",
                                        "icon": "i.webp", "media": "m.webp"},
                                       {"label": "Payroll"}]}]}
        out = cfc._split_copy(section)
        self.assertEqual(out["rows"], [("EOR", "b"), ("Payroll", "")])
        self.assertEqual(out["rowIcons"], ["i.webp", ""])
        self.assertEqual(out["rowMedia"], ["m.webp", ""])


# ── fid5: full-bleed art-surface conversion band ────────────────────────────────────

def _conv_copy():
    return {"eyebrow": "", "heading": "Global employment is hard.", "body": "We built it.",
            "cta": "Book demo", "placeholder": "you@work.com", "quote": "", "caption": ""}


def _compose_conversion(doc, layout):
    saved = cs.LAYOUT_COPY
    try:
        cs.LAYOUT_COPY = {**cs.LAYOUT_COPY, layout["id"]: _conv_copy()}
        return cs.compose_conversion_stack(doc, layout, _ctx(), [], None)
    finally:
        cs.LAYOUT_COPY = saved


class ArtSurfaceBandTest(unittest.TestCase):
    def _stamp(self, treatments, layout=None):
        layout = layout if layout is not None else {"id": "sec"}
        with mock.patch.object(cs, "resolve_pattern",
                               return_value=(_pattern(treatments), "ref")):
            cs.stamp_pattern_devices(FIXTURE_DOC, layout, Path("/tmp/x.yaml"))
        return layout

    def test_sanctioned_background_art_surface_stamps(self):
        lay = self._stamp([{"kind": "art-surface", "target": "background",
                            "sanctioned": True,
                            "note": "noise family (band-noise.webp); full-bleed"}])
        self.assertEqual(lay["_artSurface"],
                         {"note": "noise family (band-noise.webp); full-bleed",
                          "asset": None})

    def test_non_background_art_surface_does_not_stamp(self):
        lay = self._stamp([{"kind": "art-surface", "target": "media",
                            "sanctioned": True}])
        self.assertNotIn("_artSurface", lay)

    def test_band_renders_treatment_named_art(self):
        doc = _acc_media_doc(["band-noise.webp"])
        layout = {"id": "close", "_artSurface":
                  {"note": "noise family (band-noise.webp)", "asset": None}}
        html = _compose_conversion(doc, layout)
        self.assertIn("cs-conversion-sec--band", html)
        self.assertIn('class="cs-conversion-band-art" src="assets/band-noise.webp"', html)

    def test_band_without_inventory_art_degrades_flat(self):
        layout = {"id": "close", "_artSurface": {"note": "no file named", "asset": None}}
        html = _compose_conversion(dict(FIXTURE_DOC), layout)
        self.assertIn("cs-conversion-sec--band", html)
        self.assertNotIn("cs-conversion-band-art", html)

    def test_no_stamp_keeps_classic_stack(self):
        layout = {"id": "close"}
        html = _compose_conversion(dict(FIXTURE_DOC), layout)
        self.assertNotIn("cs-conversion-sec--band", html)
        self.assertIn("cs-conversion-sec", html)

    def test_band_css_gated_in_scaffold(self):
        stamped = {"id": "close", "archetype": "stack",
                   "_artSurface": {"note": "", "asset": None},
                   "blockMapping": [{"contract": "button"}]}
        css = cs.scaffold_css(FIXTURE_DOC, stamped)
        self.assertIn(".cs-conversion-sec--band", css)
        unstamped = {k: v for k, v in stamped.items() if k != "_artSurface"}
        self.assertNotIn(".cs-conversion-sec--band",
                         cs.scaffold_css(FIXTURE_DOC, unstamped))


# ── edge-cut carousel statics ──────────────────────────────────────────────────────

def _cards_copy(cards):
    return {"eyebrow": "", "heading": "Voices", "cards": cards}


def _compose_cards(layout, cards, rendered=()):
    saved = cs.LAYOUT_COPY
    try:
        cs.LAYOUT_COPY = {**cs.LAYOUT_COPY, layout["id"]: _cards_copy(cards)}
        return cs.compose_features_cards(FIXTURE_DOC, layout, _ctx(),
                                         list(rendered), None)
    finally:
        cs.LAYOUT_COPY = saved


class EdgeCutDeviceTest(unittest.TestCase):
    CARDS = [{"caption": "Ada, VP", "body": "Quote one.", "asset": "logo-a.svg"},
             {"caption": "Lin, CFO", "body": "Quote two.", "asset": "photo-b.webp"}]

    def test_edgecut_track_and_plates(self):
        html = _compose_cards({"id": "t", "_edgeCut": True, "_grid": {"columns": 3}},
                              self.CARDS)
        self.assertIn('class="cs-edgecut"', html)
        self.assertIn("cs-modules--edgecut", html)
        self.assertEqual(html.count("cs-module--plate"), 2)
        self.assertIn("cs-modules-sec--edgecut", html)

    def test_edgecut_mark_media_and_reading_order(self):
        html = _compose_cards({"id": "t", "_edgeCut": True}, self.CARDS)
        # the mark asset renders at mark height without a photo aspect frame …
        self.assertIn("cs-module-media--mark", html)
        mark_card = html.split("</article>")[0]
        self.assertNotIn("aspect-ratio", mark_card)
        # … and the quote body ELEMENT leads the caption ELEMENT inside the plate
        # (class markers, not copy strings — the caption text also rides the img alt)
        self.assertLess(mark_card.index("c-paragraph"), mark_card.index("c-caption"))
        # the photo card keeps its aspect frame
        self.assertIn("aspect-ratio", html.split("</article>")[1])

    def test_default_cards_keep_caption_first(self):
        html = _compose_cards({"id": "t"}, self.CARDS)
        first = html.split("</article>")[0]
        self.assertLess(first.index("c-caption"), first.index("c-paragraph"))

    def test_no_stamp_keeps_contained_grid(self):
        html = _compose_cards({"id": "t"}, self.CARDS)
        self.assertNotIn("cs-edgecut", html)
        self.assertNotIn("cs-module--plate", html)
        self.assertNotIn("cs-module-media--mark", html)

    def test_bound_action_slot_renders_row(self):
        rendered = [{"contract": "button", "html": '<a class="btnf">Hear more</a>'}]
        html = _compose_cards({"id": "t", "_edgeCut": True}, self.CARDS, rendered)
        self.assertIn("cs-modules-actions", html)
        self.assertIn("Hear more", html)
        # and without a bound slot the row elides
        html2 = _compose_cards({"id": "t", "_edgeCut": True}, self.CARDS)
        self.assertNotIn("cs-modules-actions", html2)

    def test_edgecut_css_bleeds_and_uses_vars(self):
        css = cs.SCAFFOLD_EDGECUT_CSS
        self.assertIn("overflow-x: auto", css)
        self.assertIn("calc(-1 * var(--c-section-pad-x, 0rem))", css)
        self.assertIn("var(--c-panel)", css)
        self.assertIn("var(--radius-card, 0)", css)


# ── device CSS gating (AS-37 discipline) ───────────────────────────────────────────

class DeviceCssGatingTest(unittest.TestCase):
    def test_only_stamped_devices_ship(self):
        self.assertEqual(cs.device_scaffold_css([{"id": "a"}]), "")
        css = cs.device_scaffold_css([{"id": "a", "_marquee": {"target": "x"}}])
        self.assertIn("cs-marquee", css)
        self.assertNotIn("c-acc-item", css)
        self.assertNotIn("cs-edgecut", css)
        css = cs.device_scaffold_css([{"_accordion": {}}, {"_edgeCut": True}])
        self.assertIn("c-acc-item", css)
        self.assertIn("cs-edgecut", css)


# ── utility banner (evidence-gated chrome) ─────────────────────────────────────────

@unittest.skipUnless(_REMOTE.is_file(), "Remote run fixture not present")
class UtilityBannerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = cp.load_doc(_REMOTE)
        cls.order = [cls.doc["layouts"][0]["id"]]

    def _page(self, doc):
        from styles import inactive_context
        return cp.build_page(doc, _REMOTE, self.order, inactive_context())

    def test_declared_banner_renders_above_nav(self):
        import copy
        html = self._page(copy.deepcopy(self.doc))
        self.assertIn('id="page-banner"', html)
        self.assertLess(html.index('id="page-banner"'), html.index('id="page-nav"'))
        self.assertIn("cs-utility-banner-close", html)  # dismissible evidence
        self.assertIn("#page-banner", html)              # scoped surface vars + CSS

    def test_absent_banner_renders_nothing(self):
        import copy
        doc = copy.deepcopy(self.doc)
        doc["navbar"].pop("utilityBanner", None)
        html = self._page(doc)
        self.assertNotIn("page-banner", html)
        self.assertNotIn("cs-utility-banner", html)

    def test_unknown_surface_degrades_to_no_banner(self):
        import copy
        doc = copy.deepcopy(self.doc)
        doc["navbar"]["utilityBanner"]["surface"] = "surface/nope"
        # strip the measured-paint facts too (fid2 2026-07): with a measured bg the
        # banner legitimately renders on its own scoped literals regardless of the
        # (unknown) role — this test covers the role-only degrade path.
        doc["navbar"]["utilityBanner"].pop("bg", None)
        doc["navbar"]["utilityBanner"].pop("ink", None)
        html = self._page(doc)
        self.assertNotIn("page-banner", html)

    def test_measured_banner_paint_wins(self):
        # a banner carrying measured bg/ink facts renders them as scoped literals
        # (the :root chrome color no section surface role owns — fid2 2026-07).
        import copy
        doc = copy.deepcopy(self.doc)
        doc["navbar"]["utilityBanner"]["bg"] = "#141415"
        doc["navbar"]["utilityBanner"]["ink"] = "#ffffff"
        html = self._page(doc)
        self.assertIn('data-surface="chrome/utility-banner"', html)
        self.assertIn("--c-paper: #141415", html)

    def test_textless_banner_renders_nothing(self):
        import copy
        doc = copy.deepcopy(self.doc)
        doc["navbar"]["utilityBanner"].pop("text", None)
        html = self._page(doc)
        self.assertNotIn("page-banner", html)


# ── AS-41: reveal failsafe ─────────────────────────────────────────────────────────

class RevealFailsafeTest(unittest.TestCase):
    def test_reveal_script_carries_all_failsafes(self):
        s = cp.REVEAL_SCRIPT
        self.assertIn("prefers-reduced-motion", s)          # early-out (a)
        self.assertIn("'IntersectionObserver' in window", s)  # early-out (b)
        self.assertIn("cs-motion-ready", s)                 # hidden state gated on JS
        self.assertIn("setTimeout", s)                      # timed force-reveal (c)
        # the failsafe reveals the SAME node set the observer manages
        self.assertRegex(s, r"setTimeout[\s\S]*is-in")


# ── AS-43: disabled states are colors, never opacity ──────────────────────────────

class DisabledStateColorTest(unittest.TestCase):
    def test_measured_family_resets_harness_dim(self):
        # measured buttons live at brand.yaml top-level `buttons:`; a measured
        # primary set implies the filled cta-shape (component_render.cta_shape).
        doc = {"brand": {"name": "F"},
               "buttons": {"primary": {"bg": "#0000ff", "fg": "#ffffff",
                                       "bgDisabled": "#e4e4e4",
                                       "fgDisabled": "#8b8f93"}}}
        css = rp.button_family_css(doc)
        m = re.search(r"\.btnf-primary\.is-disabled[^{]*\{([^}]*)\}", css)
        self.assertIsNotNone(m, css)
        self.assertIn("opacity: 1", m.group(1))   # explicit harness-dim reset
        self.assertIn("disabled", m.group(1))     # color-token driven
        self.assertNotIn("opacity: 0", m.group(1))

    def test_shared_component_css_has_no_opacity_disabled_rule(self):
        # composed pages ride COMPONENT_CSS — disabled states there must never be
        # opacity ghosts (the preview harness's exhibit dim is preview-only).
        # Match RULES whose SELECTOR names a disabled state (comments stripped —
        # prose like "device disabled" in comment blocks is not a state rule).
        css = re.sub(r"/\*.*?\*/", "", cr.COMPONENT_CSS, flags=re.S)
        for sel, body in re.findall(r"([^{}]+)\{([^}]*)\}", css):
            if ":disabled" in sel or "is-disabled" in sel:
                self.assertNotIn("opacity", body, f"{sel.strip()} {{{body}}}")


if __name__ == "__main__":
    unittest.main()
