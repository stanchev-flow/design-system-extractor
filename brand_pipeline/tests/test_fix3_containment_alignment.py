#!/usr/bin/env python3
"""Regression tests for the fix3 batch (hubspot-v2 2026-07): the CONTAINMENT LAW
(one shared mechanism owns section max-width + centering), full alignment-axis
ownership for action groups, the painted-edge audit that catches box-level
centering, the split-panel carousel's rail-nav controls, the arrow-link content
hug (AS-61), and the hero stack MEASURE cap.

  - CONTAINMENT LAW (`compose_section.CONTAINMENT_LAW_CSS` / `CONTAINED_DEVICES`):
    every major section container spans (width: 100%), caps at the ONE shared
    measure and centers from a single rule; a source-lint fails any private
    `max-width: var(--content-measure)` / containment-pair declaration outside
    the law that is not `contain-exempt`-tagged.
  - AG ALIGNMENT OWNERSHIP (`action_group_css` / `layout_placement_css`): a
    declared `align` claims justify-content (brand law page-wide; pattern
    override per #sec-N); `crossAlign` claims align-items ONLY when authored.
  - AUDIT BLIND SPOT (`spacing_audit` / `slop_audit.mjs` AS-60): the
    actions.alignment cell measures the ITEMS' painted edges against the content
    column (widest sibling / parent content box) — the pre-fix hug-and-center
    mechanic must classify off-ladder, the fixed build conform.
  - RAIL-NAV CAROUSEL (`_compose_split_carousel`): treatment
    `controls: {placement: rail, size}` seats prev/next on the dot row; fact-less
    carousels keep the structural mid-edge paddles byte-identically.
  - ARROW-LINK HUG (`component_render` + AS-61): the text link's box hugs
    label + glyph in column flex stacks (width: fit-content).
  - HERO MEASURE (`_stack_hero_layered` + SCAFFOLD_HERO_CSS): a stamped
    stackMeasure caps .cs-title/.cs-foot at the measured column; fact-less
    heroes resolve the cap to `none`.

Run:  ./venv/bin/python -m unittest brand_pipeline.tests.test_fix3_containment_alignment
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

import component_render as cr    # noqa: E402
import compose_page as cp        # noqa: E402
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

AG_DOC = {**FIXTURE_DOC,
          "layoutGrammar": {"actionGroup": {
              "gap": "1rem", "align": "start", "marginAbove": "ladder"}}}


def _ctx():
    return cr.make_context(FIXTURE_DOC, "surface/primary",
                           FIXTURE_DOC["tokens"]["surfaces"]["surface/primary"])


# ── containment law: one shared mechanism ─────────────────────────────────────────


class ContainmentLawTest(unittest.TestCase):
    def test_law_rule_ships_in_base_scaffold(self):
        # the ONE rule: every member, spanning + capped + centered
        self.assertIn(cs.CONTAINMENT_LAW_CSS, cs.SCAFFOLD_BASE_CSS)
        m = re.search(r"([^{}]+)\{\s*width: 100%; max-width: "
                      r"var\(--content-measure, 86rem\); margin-inline: auto; \}",
                      cs.CONTAINMENT_LAW_CSS)
        self.assertIsNotNone(m, "law rule shape changed")
        sels = m.group(1)
        for member in cs.CONTAINED_DEVICES:
            self.assertIn(member, sels, f"{member} missing from the law rule")

    def test_width_100_is_load_bearing(self):
        # the nesting-safety property: auto margins never see free space inside
        # a narrower column, so hug-and-center (the fix3 leak) is impossible.
        self.assertIn("width: 100%", cs.CONTAINMENT_LAW_CSS)

    def test_bug_sites_are_members(self):
        for member in (".cs-modules-actions",   # the centering leak
                       ".cs-panelcar",          # the full-bleed slider
                       ".cs-footer-sec > .c-footer"):
            self.assertIn(member, cs.CONTAINED_DEVICES)

    def test_no_private_containment_survives_migration(self):
        # spot-check the migrated device blocks: their own rules no longer carry
        # the containment pair.
        for css_blob, sel in ((cs.SCAFFOLD_SPLIT_CSS, ".cs-split "),
                              (cs.SCAFFOLD_FLOW_CSS, ".cs-flow "),
                              (cs.SCAFFOLD_CONVERSION_PANEL_CSS, ".cs-conversion-panel ")):
            clean = re.sub(r"/\*.*?\*/", "", css_blob, flags=re.S)
            for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", clean):
                if sel.strip() in [s.strip() for s in m.group(1).split(",")]:
                    self.assertNotIn("max-width: var(--content-measure",
                                     m.group(2), f"{sel} kept a private copy")

    def _source_lint(self, path: Path) -> list[str]:
        """Every `max-width: var(--content-measure` declaration outside the law
        must be `contain-exempt`-tagged within the 6 lines above it."""
        lines = path.read_text().splitlines()
        law_span = set()
        for i, ln in enumerate(lines):
            if "CONTAINMENT_LAW_CSS = (" in ln:
                for j in range(i, min(i + 20, len(lines))):
                    law_span.add(j)
        offenders = []
        for i, ln in enumerate(lines):
            if "max-width: var(--content-measure" not in ln:
                continue
            if i in law_span or ln.strip().startswith("#"):
                continue
            window = "\n".join(lines[max(0, i - 6):i + 1])
            if "contain-exempt" not in window:
                offenders.append(f"{path.name}:{i + 1}: {ln.strip()[:90]}")
        return offenders

    def test_source_lint_no_untagged_containment(self):
        offenders = []
        for f in ("compose_section.py", "compose_page.py", "component_render.py"):
            offenders += self._source_lint(_BRAND_PIPELINE / f)
        self.assertEqual(offenders, [],
                         "untagged containment declarations outside the law:\n"
                         + "\n".join(offenders))

    def test_emitted_page_carries_exactly_one_law_rule(self):
        css = cp.page_scaffold_css()
        self.assertEqual(css.count("width: 100%; max-width: "
                                   "var(--content-measure, 86rem); "
                                   "margin-inline: auto; }"), 1)


# ── action-group law: full alignment-axis ownership ──────────────────────────────


class AGAlignmentOwnershipTest(unittest.TestCase):
    def test_align_fact_claims_justify_content(self):
        css = cs.action_group_css(AG_DOC)
        self.assertIn(".cs-hero-actions, .cs-modules-actions, .cs-conversion-actions"
                      " { justify-content: flex-start; }", css)

    def test_cross_axis_untouched_without_fact(self):
        # structural align-items: center stays scaffold-owned unless authored
        self.assertNotIn("align-items", cs.action_group_css(AG_DOC))

    def test_crossalign_fact_claims_align_items(self):
        doc = {**FIXTURE_DOC,
               "layoutGrammar": {"actionGroup": {"gap": "1rem",
                                                 "crossAlign": "stretch"}}}
        self.assertIn("align-items: stretch", cs.action_group_css(doc))

    def test_factless_brand_emits_nothing(self):
        self.assertEqual(cs.action_group_css(FIXTURE_DOC), "")

    def test_pattern_override_emits_scoped_alignment(self):
        css = cs.layout_placement_css(
            "#sec-3", {"_actionGroup": {"align": "end", "crossAlign": "center"}})
        self.assertIn("#sec-3 .cs-modules-actions", css)
        self.assertIn("justify-content: flex-end", css)
        self.assertIn("align-items: center", css)

    def test_stamp_pattern_devices_carries_crossalign(self):
        pat = ll.Pattern(
            id="p", use_case="cta", archetype_ref="stack",
            surface_intent="primary", intent="",
            content_shape={"slots": [],
                           "actionGroup": {"align": "start",
                                           "crossAlign": "center"}},
            special_treatments=[], responsive={}, variant_knobs={},
            origin="extracted", confidence="high", scope="design-language",
            provenance=[])
        layout = {"id": "sec"}
        with mock.patch.object(cs, "resolve_pattern", return_value=(pat, "ref")):
            cs.stamp_pattern_devices(AG_DOC, layout, Path("/nonexistent/brand.yaml"))
        self.assertEqual(layout.get("_actionGroup"),
                         {"align": "start", "crossAlign": "center"})

    def test_actions_row_no_longer_self_contains(self):
        # the leak mechanic is structurally impossible: the row is a containment-
        # law member (spans its column), never a private max-width + auto-margin
        # box that can hug and float.
        clean = re.sub(r"/\*.*?\*/", "", cs.SCAFFOLD_CARDS_CSS, flags=re.S)
        for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", clean):
            if ".cs-modules-actions" in [s.strip() for s in m.group(1).split(",")]:
                self.assertNotIn("margin-inline: auto", m.group(2))
                self.assertNotIn("max-width", m.group(2))


# ── the audit blind spot: painted edges vs the content column ────────────────────


_PREFIX_FIXTURE = """<!doctype html><html><head><style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  .cs-surface {{ width: 1440px; }}
  .cs-section {{ padding: 40px; }}
  .col {{ display: flex; flex-direction: column; width: 367px;
    margin-left: 140px; gap: 24px; }}
  .cs-modules-intro {{ max-width: 1080px; }}
  .cs-modules-actions {{ display: flex; flex-wrap: wrap; align-items: center;
    gap: 16px; {actions_css} justify-content: flex-start; }}
  .c-button {{ display: inline-flex; padding: 12px 24px; background: #f50;
    color: #fff; border-radius: 8px; }}
</style></head><body>
<div class="cs-surface" data-layout="product-grid" id="sec-0"><section class="cs-section">
  <div class="col">
    <div class="cs-modules-intro"><h2>Heading spans the copy column width here</h2></div>
    <div class="cs-modules-actions" data-ag-gap="16" data-ag-align="start">
      <a class="c-button" href="#">Get a demo</a>
      <a class="c-button" href="#">Get started free</a>
    </div>
  </div>
</section></div>
</body></html>
"""


class AuditCatchesCenteringTest(unittest.TestCase):
    """The actions.alignment cell must FAIL on the pre-fix mechanic (a group box
    hug-centered by its own max-width + auto margins inside a narrower column)
    and CONFORM on the containment-law build (the box spans the column)."""

    def _alignment_cell(self, actions_css: str):
        from playwright.sync_api import sync_playwright
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "brand.yaml").write_text(
                "brand: {name: X}\ntokens: {spacing: {}}\n"
                "layoutGrammar:\n  actionGroup: { gap: 1rem, align: start }\n")
            (root / "layout-library.yaml").write_text("patterns: []\n")
            html = root / "lane.html"
            html.write_text(_PREFIX_FIXTURE.format(actions_css=actions_css))
            book = sa.load_brand_facts(root)
            with sync_playwright() as pw:
                raw = sa.measure_lane(pw, html, (1440, 900))
            cells = [m for m in raw.get("measurements", raw if isinstance(raw, list) else [])
                     if m.get("rel") == "actions.alignment"]
            self.assertEqual(len(cells), 1, f"expected one alignment cell, got {cells}")
            return sa.classify_measurement(cells[0], book)

    def test_prefix_mechanic_fails_off_ladder(self):
        v = self._alignment_cell("max-width: 1080px; margin-inline: auto;")
        self.assertEqual(v["severity"], "off-ladder")

    def test_containment_law_build_conforms(self):
        v = self._alignment_cell("width: 100%; max-width: 1080px; margin-inline: auto;")
        self.assertEqual(v["severity"], "conform")

    def test_audit_js_measures_painted_edges(self):
        js = Path(sa.__file__).read_text()
        self.assertIn("painted edges vs column", js)
        self.assertIn("column = widest sibling", js)

    def test_hero_text_stacks_classify_as_measure_stacks(self):
        js = Path(sa.__file__).read_text()
        m = re.search(r"NARROW_STACKS = '([^']+)'", js)
        self.assertIsNotNone(m)
        for sel in (".cs-title", ".cs-foot", ".cs-conversion"):
            self.assertIn(sel, m.group(1))


class SlopAs60PaintedEdgeTest(unittest.TestCase):
    def test_as60_painted_edge_check_present(self):
        src = (_BRAND_PIPELINE / "slop_audit.mjs").read_text()
        self.assertIn("painted", src)
        self.assertIn("off its declared", src)
        # centering parents are a sanctioned anchor in BOTH auditors now
        self.assertIn('getComputedStyle(g.parentElement).alignItems === "center"', src)

    def test_as61_text_link_hug_present(self):
        src = (_BRAND_PIPELINE / "slop_audit.mjs").read_text()
        self.assertIn("AS-61", src)
        self.assertIn(".c-arrow-link", src)
        # nav hit-target boxes are excluded chrome geometry
        self.assertIn('a.closest(".cs-nav")', src)


# ── rail-nav carousel controls ────────────────────────────────────────────────────


def _carousel_pattern(controls=None):
    treatment = {"kind": "carousel", "target": "list", "sanctioned": True}
    if controls:
        treatment["controls"] = controls
    return ll.Pattern(
        id="car", use_case="features", archetype_ref="split",
        surface_intent="primary", intent="",
        content_shape={"slots": [
            {"name": "media", "role": "art",
             "mediaScale": {"of": "container", "fraction": 0.45}}]},
        special_treatments=[treatment], responsive={}, variant_knobs={},
        origin="extracted", confidence="high", scope="design-language",
        provenance=[])


_CAR_COPY = {"heading": "Platform", "eyebrow": "", "subhead": "",
             "body": "", "cta": "", "caption": ""}
_CAR_SLIDES = [{"heading": "One", "body": "Alpha"},
               {"heading": "Two", "body": "Beta"}]


class RailNavCarouselTest(unittest.TestCase):
    def _stamp(self, controls=None):
        layout = {"id": "sec"}
        pat = _carousel_pattern(controls)
        with mock.patch.object(cs, "resolve_pattern", return_value=(pat, "ref")):
            cs.stamp_pattern_devices(FIXTURE_DOC, layout,
                                     Path("/nonexistent/brand.yaml"))
        return layout

    def test_controls_fact_stamps(self):
        layout = self._stamp({"placement": "rail", "size": "3.5rem"})
        self.assertEqual(layout["_carousel"]["controls"],
                         {"placement": "rail", "size": "3.5rem"})
        self.assertEqual(layout["_carousel"]["mediaFraction"], 0.45)

    def test_rail_placement_renders_nav_row(self):
        layout = self._stamp({"placement": "rail", "size": "3.5rem"})
        html = cs._compose_split_carousel(FIXTURE_DOC, layout, _ctx(),
                                          _CAR_COPY, _CAR_SLIDES)
        self.assertIn("cs-panelcar--railnav", html)
        self.assertIn("--cs-panelcar-arrow-size: 3.5rem", html)
        nav = html.split('class="cs-panelcar-nav"')[1]
        # prev, dots, next all INSIDE the nav row, in rail order
        self.assertLess(nav.index("cs-panelcar-arrow--prev"),
                        nav.index("cs-panelcar-dots"))
        self.assertLess(nav.index("cs-panelcar-dots"),
                        nav.index("cs-panelcar-arrow--next"))

    def test_factless_carousel_keeps_structural_paddles(self):
        layout = self._stamp(None)
        html = cs._compose_split_carousel(FIXTURE_DOC, layout, _ctx(),
                                          _CAR_COPY, _CAR_SLIDES)
        self.assertNotIn("cs-panelcar--railnav", html)
        self.assertNotIn("cs-panelcar-nav", html)
        # arrows flank the panels as direct children (the fix1 markup)
        self.assertLess(html.index("cs-panelcar-arrow--prev"),
                        html.index("cs-panelcar-panels"))

    def test_carousel_is_contained(self):
        self.assertIn(".cs-panelcar", cs.CONTAINED_DEVICES)
        self.assertIn(".cs-panelcar--railnav .cs-panelcar-arrow { position: static;",
                      cs.SCAFFOLD_PANELCAR_CSS)


# ── arrow-link content hug ────────────────────────────────────────────────────────


class ArrowLinkHugTest(unittest.TestCase):
    def test_component_css_hugs_content(self):
        m = re.search(r"\.c-arrow-link \{[^}]+\}", cr.COMPONENT_CSS)
        self.assertIsNotNone(m)
        self.assertIn("width: fit-content", m.group(0))

    def test_hug_beats_column_flex_stretch_live(self):
        from playwright.sync_api import sync_playwright
        html = f"""<!doctype html><html><head><style>
          * {{ margin: 0; box-sizing: border-box; }}
          .card {{ display: flex; flex-direction: column; width: 600px; }}
          {re.search(r"[.]c-arrow-link [{][^}]+[}]", cr.COMPONENT_CSS).group(0)}
        </style></head><body>
          <div class="card"><a class="c-arrow-link" href="#">Learn more <span>→</span></a></div>
        </body></html>"""
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "hug.html"
            f.write_text(html)
            with sync_playwright() as pw:
                b = pw.chromium.launch()
                try:
                    page = b.new_page(viewport={"width": 900, "height": 300})
                    page.goto(f.resolve().as_uri())
                    got = page.evaluate(
                        """() => {
                          const a = document.querySelector('.c-arrow-link');
                          const r = a.getBoundingClientRect();
                          const rng = document.createRange();
                          rng.selectNodeContents(a);
                          return { box: r.width,
                                   ink: rng.getBoundingClientRect().width,
                                   card: a.parentElement.getBoundingClientRect().width };
                        }""")
                finally:
                    b.close()
        self.assertLess(got["box"], got["card"] / 2,
                        "link box did not hug (stretched in the column stack)")
        self.assertLessEqual(abs(got["box"] - got["ink"]), 4,
                             "underline box exceeds the label+glyph run")


# ── hero stack measure ────────────────────────────────────────────────────────────


class HeroMeasureTest(unittest.TestCase):
    _LAYERS = [{"kind": "background", "asset": "bg.webp"}]

    def _hero(self, stack_measure):
        return cs._stack_hero_layered(
            FIXTURE_DOC, _ctx(), self._LAYERS, eyebrow_html="<p>e</p>",
            title_html="<h1>T</h1>", cta_html="", subhead="s",
            stack_measure=stack_measure)

    def test_stamped_measure_rides_the_section_style(self):
        html = self._hero("49rem")
        self.assertIn("--cs-stack-measure: 49rem", html)

    def test_factless_hero_has_no_measure_var(self):
        self.assertNotIn("--cs-stack-measure", self._hero(None))

    def test_scaffold_caps_text_boxes_fallback_none(self):
        self.assertIn(".cs-title, .cs-foot { max-width: var(--cs-stack-measure, none); }",
                      cs.SCAFFOLD_HERO_CSS)

    def test_stack_measure_stamp_flows_from_pattern(self):
        pat = ll.Pattern(
            id="hero", use_case="hero", archetype_ref="stack",
            surface_intent="any", intent="",
            content_shape={"slots": [], "stackMeasure": {"value": "49rem"}},
            special_treatments=[], responsive={}, variant_knobs={},
            origin="extracted", confidence="high", scope="design-language",
            provenance=[])
        layout = {"id": "sec"}
        with mock.patch.object(cs, "resolve_pattern", return_value=(pat, "ref")):
            cs.stamp_pattern_devices(FIXTURE_DOC, layout,
                                     Path("/nonexistent/brand.yaml"))
        self.assertEqual(layout.get("_stackMeasure"), "49rem")


class HeroWrapParityTest(unittest.TestCase):
    """The shipped hubspot-v2 replica: heading wraps to the source's TWO lines at
    1440 AND at 1920 (the wide-screen leak). Skipped when the lane is absent."""

    _REPLICA = (_BRAND_PIPELINE.parent / "runs" / "hubspot-v2" / "brand"
                / "compose" / "replica" / "index.html")

    @unittest.skipUnless(_REPLICA.exists(), "hubspot-v2 replica not built")
    def test_hero_two_lines_at_1440_and_1920(self):
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            b = pw.chromium.launch()
            try:
                page = b.new_page(viewport={"width": 1440, "height": 950})
                page.goto(self._REPLICA.resolve().as_uri())
                page.wait_for_timeout(400)
                for w in (1440, 1920):
                    page.set_viewport_size({"width": w, "height": 950})
                    page.wait_for_timeout(250)
                    lines = page.evaluate(
                        """() => {
                          const h = document.querySelector('#sec-0 .cs-title .c-heading--display');
                          const r = h.getBoundingClientRect();
                          return Math.round(r.height / parseFloat(getComputedStyle(h).lineHeight));
                        }""")
                    self.assertEqual(lines, 2, f"hero heading lines @{w}px")
            finally:
                b.close()


if __name__ == "__main__":
    unittest.main()
