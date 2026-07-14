#!/usr/bin/env python3
"""Regression tests for the fix5 batch (2026-07) — the hero-archetypes gallery
review defects:

  D1  PANEL HEADER ALIGNMENT: an archetype's anatomy alignment CONTEXT
      (`splitColumn` / `standaloneStack`) now rides the instantiated section
      (`apply_archetype_skeleton` stamps `_headerContext`, composition_to_layout
      carries it), so `resolve_alignment` consults the brand's header-context
      grammar for renderer archetypes outside the arch→context map (overlay,
      banded, …) instead of falling through to the style default. The section
      anchor pack additionally EXEMPTS overlay-panel interiors — a panel is its
      own copy column and aligns as one unit.
      AUDIT GAP: `header.stack-coherence` (spacing_audit) — a header stack that
      paints MIXED stances (centered heading over a left kicker/body/actions)
      hard-fails; coherent stacks of any stance conform.

  D2/D3  CROPPED CHROME GLYPHS: the harvested hubspot-v2 glyph assets carried a
      hand-authored `viewBox="0 0 24 24"` under artwork drawn on the source
      sprite's 32x32 (and non-square) grids — every consumer (inline svg AND
      mask) clipped the artwork. Repaired from the SOURCE sprite's own symbol
      viewBoxes. TEST GAP closed here: a browser crop check asserts every chrome
      glyph's artwork bbox fits its declared viewBox AND the rendered projection
      fills the host box unclipped (fix4's nonzero-paint-box check could not see
      cropping).

  D4  CHEVRON SPIN: the open-state chevron flip must swap INSTANTLY in
      generation lanes (user directive). Both brands measured a real rotation
      tween, so the ruling is recorded as CURATION DATA on the chevron fact
      (`curation.motion.resolve: instant`, the workflow-header precedent);
      `nav_affordance_css(honor_curation=…)` honors it in generation lanes while
      the replica lane keeps the measured transition. The FACT-LESS degrade is
      the instant toggle too (AS-47: motion is measured or absent — the old
      degrade invented a rotation tween on the brand's motion tokens).

Run:  ./venv/bin/python -m unittest brand_pipeline.tests.test_fix5_gallery_defects
"""
from __future__ import annotations

import copy
import re
import sys
import tempfile
import unittest
from pathlib import Path

_BRAND_PIPELINE = Path(__file__).resolve().parent.parent
if str(_BRAND_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_BRAND_PIPELINE))

import archetype_library as al           # noqa: E402
import component_render as cr            # noqa: E402
import compose_from_composition as cfc   # noqa: E402
import compose_section as cs             # noqa: E402
import spacing_audit as sa               # noqa: E402

_PROJECT = _BRAND_PIPELINE.parent
_HS_BRAND = _PROJECT / "runs" / "hubspot-v2" / "brand"
_REMOTE_BRAND = _PROJECT / "runs" / "remote" / "brand"

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


# ── D1: archetype alignment context propagation ────────────────────────────────────


class HeaderContextStampTest(unittest.TestCase):
    def test_panel_archetype_stamps_split_column(self):
        sec = {"id": "hero", "archetype": "stack",
               "archetypeRef": "hero-product-canvas-panel",
               "slots": [{"name": "canvas", "contract": "image"},
                         {"name": "panel", "contract": "media-text"}]}
        doc = {"tokens": {"surfaces": {"surface/primary": {}}}}
        out, notes = al.apply_archetype_skeleton(sec, doc)
        if out.get("archetypeRef"):  # physics resolved for the fixture doc
            self.assertEqual(out.get("_headerContext"), "splitColumn")
            self.assertTrue(any("header context" in n for n in notes))

    def test_context_stamp_rides_from_library_data(self):
        art = al.find_archetype("hero-product-canvas-panel", None)
        self.assertIsNotNone(art)
        ctx = ((art.get("anatomy") or {}).get("alignment") or {}).get("context")
        self.assertEqual(ctx, "splitColumn")
        crest = al.find_archetype("hero-announcement-crest", None)
        self.assertEqual(((crest.get("anatomy") or {}).get("alignment") or {})
                         .get("context"), "standaloneStack")

    def test_layout_rides_header_context(self):
        sec = {"id": "s0", "archetype": "overlay", "useCase": "hero",
               "_headerContext": "splitColumn",
               "slots": [{"name": "canvas", "contract": "image",
                          "role": "canvas", "copy": {}}]}
        layout = cfc.composition_to_layout(cfc._sanitize_assets(
            {"sections": [sec]}, _HS_BRAND)["sections"][0]) \
            if _HS_BRAND.exists() else cfc.composition_to_layout(sec)
        self.assertEqual(layout.get("_headerContext"), "splitColumn")

    def test_overlay_with_split_context_resolves_brand_grammar(self):
        doc = {"layoutGrammar": {"headerContext": {
            "splitColumn": {"anchor": "left", "counterweight": "media"},
            "standaloneStack": {"anchor": "centered"},
        }}}
        resolved = cs.resolve_alignment(
            {"id": "s0", "archetype": "overlay", "_headerContext": "splitColumn"},
            None, None, doc)
        self.assertIsNotNone(resolved)
        self.assertEqual(resolved["anchor"], "left")
        self.assertEqual(resolved["source"], "brand")
        self.assertEqual(resolved["counterweight"], "media")

    def test_overlay_without_context_still_falls_through(self):
        # no stamp + overlay archetype ⇒ grammar yields None (unchanged chain)
        doc = {"layoutGrammar": {"headerContext": {
            "splitColumn": {"anchor": "left", "counterweight": "media"}}}}
        self.assertIsNone(cs.resolve_alignment(
            {"id": "s0", "archetype": "overlay"}, None, None, doc))


class AnchorPackReachesPanelTest(unittest.TestCase):
    """The section anchor pack must REACH overlay-panel interiors: the resolved
    anchor IS the grammar's answer for the panel's header stack (the anatomy
    stamps the context pre-resolution). An exemption would re-expose the style
    density default — the exact mixed-alignment defect."""

    def test_pack_owns_panel_heading(self):
        pack = cs._anchor_css("#sec-0", "left")
        self.assertIn(".c-heading--display { text-align: left;", pack)
        self.assertNotIn(":not(.cs-ov-panel", pack)
        self.assertIn(".cs-hero-actions { justify-content: flex-start; }", pack)

    def test_pack_still_anchors_section_stacks(self):
        pack = cs._anchor_css("#sec-0", "centered")
        self.assertIn(".cs-title", pack)
        self.assertIn("align-items: center", pack)


# ── D1 audit gap: header-stack coherence ───────────────────────────────────────────


_STACK_FIXTURE = """<!doctype html><html><head><style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  .cs-surface {{ width: 1440px; }}
  .cs-section {{ padding: 40px; }}
  .stack {{ display: flex; flex-direction: column; gap: 24px; width: 500px;
    margin-left: 120px; }}
  .c-heading {{ font-size: 40px; {heading_css} }}
  .c-paragraph {{ max-width: 30ch; }}
  .cs-hero-actions {{ display: flex; gap: 16px; {actions_css} }}
  .c-button {{ display: inline-flex; padding: 12px 24px; background: #f50;
    color: #fff; }}
  .row {{ display: flex; gap: 40px; }}
</style></head><body>
<div class="cs-surface" data-layout="fx" id="sec-0"><section class="cs-section">
  {body}
</section></div>
</body></html>
"""

_MIXED_STACK = """<div class="stack">
  <p class="c-eyebrow">MARKETING HUB</p>
  <h1 class="c-heading">Almost centered heading</h1>
  <p class="c-paragraph">Body copy stays on the left edge of the column here.</p>
  <div class="cs-hero-actions"><a class="c-button" href="#">Go</a>
    <a class="c-button" href="#">Free</a></div>
</div>"""

_CENTERED_STACK = """<div class="stack" style="align-items: center; text-align: center">
  <p class="c-eyebrow">MARKETING HUB</p>
  <h1 class="c-heading" style="text-align: center">Centered heading</h1>
  <p class="c-paragraph">Body copy centered under the heading, same stance.</p>
  <div class="cs-hero-actions" style="justify-content: center"><a class="c-button"
    href="#">Go</a><a class="c-button" href="#">Free</a></div>
</div>"""

_ROW_INTRO = """<div class="row">
  <h2 class="c-heading" style="width: 40%">Two column intro heading</h2>
  <p class="c-paragraph" style="margin-left: auto; width: 40%">Right-set body in
    the same row — a ROW device, not a stacked header.</p>
</div>"""


class StackCoherenceAuditTest(unittest.TestCase):
    def _cells(self, body: str, heading_css: str = "", actions_css: str = ""):
        from playwright.sync_api import sync_playwright
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "brand.yaml").write_text(
                "brand: {name: X}\ntokens: {spacing: {}}\n")
            (root / "layout-library.yaml").write_text("patterns: []\n")
            html = root / "lane.html"
            html.write_text(_STACK_FIXTURE.format(
                body=body, heading_css=heading_css, actions_css=actions_css))
            book = sa.load_brand_facts(root)
            with sync_playwright() as pw:
                raw = sa.measure_lane(pw, html, (1440, 900))
            cells = [m for m in raw.get("measurements", [])
                     if m.get("rel") == "header.stack-coherence"]
            return [sa.classify_measurement(c, book) for c in cells]

    def test_mixed_stack_fails_hard(self):
        # the defect mechanic: heading centered by a leaked rule, siblings left
        cells = self._cells(_MIXED_STACK,
                            heading_css="text-align: center; margin-inline: auto;"
                                        " max-width: 14ch;")
        self.assertEqual(len(cells), 1)
        self.assertEqual(cells[0]["severity"], "off-ladder")
        self.assertEqual(cells[0]["gate"], "hard")

    def test_coherent_left_stack_conforms(self):
        cells = self._cells(_MIXED_STACK)   # no centering CSS — everything left
        self.assertEqual(len(cells), 1)
        self.assertEqual(cells[0]["severity"], "conform")

    def test_coherent_centered_stack_conforms(self):
        cells = self._cells(_CENTERED_STACK)
        self.assertEqual(len(cells), 1)
        self.assertEqual(cells[0]["severity"], "conform")

    def test_side_by_side_row_is_not_a_stack(self):
        cells = self._cells(_ROW_INTRO)
        for c in cells:
            self.assertEqual(c["severity"], "conform", c)

    def test_relationship_registered_hard(self):
        rel = sa.RELATIONSHIPS["header.stack-coherence"]
        self.assertEqual(rel.family, "center")
        self.assertFalse(rel.advisory_only)


# ── D2/D3: glyph crop guard (asset containment + rendered projection) ──────────────


def _chrome_glyph_assets(brand_dir: Path) -> list[Path]:
    """Every svg asset a brand's chrome facts reference through the glyph
    channel (prepare_chrome_glyphs coverage: trigger/utility chevrons + icons,
    banner arrow/close, footer socials, textCta glyph)."""
    import yaml
    doc = yaml.safe_load((brand_dir / "brand.yaml").read_text())
    refs: list[str] = []

    def _icon(node):
        if isinstance(node, dict) and str(node.get("asset") or "").endswith(".svg"):
            refs.append(str(node["asset"]))

    nav = doc.get("navbar") or {}
    for u in nav.get("utility") or []:
        if isinstance(u, dict):
            _icon(u.get("icon"))
            _icon(u.get("chevron"))
    measured = nav.get("measured") if isinstance(nav.get("measured"), dict) else {}
    _icon(((measured.get("trigger") or {}).get("chevron"))
          if isinstance(measured.get("trigger"), dict) else None)
    banner = nav.get("utilityBanner") if isinstance(nav.get("utilityBanner"), dict) else {}
    _icon((banner.get("cta") or {}).get("arrow")
          if isinstance(banner.get("cta"), dict) else None)
    _icon(banner.get("close"))
    for s in (doc.get("footer") or {}).get("social") or []:
        if isinstance(s, dict):
            _icon(s.get("icon"))
    for spec in (doc.get("buttons") or {}).values():
        if isinstance(spec, dict):
            _icon(spec.get("glyph"))
    out = []
    for r in dict.fromkeys(refs):
        p = brand_dir / r
        if p.is_file():
            out.append(p)
    return out


class GlyphCropTest(unittest.TestCase):
    """The REAL crop check fix4 lacked: artwork must fit its viewBox and the
    rendered projection must fill the host box unclipped. Would have failed on
    the 15 hubspot-v2 glyphs whose 24x24 viewBox cropped 32-grid artwork."""

    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls._pw = sync_playwright().start()
        cls._browser = cls._pw.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls._browser.close()
        cls._pw.stop()

    def _assert_artwork_fits_viewbox(self, files: list[Path]):
        pg = self._browser.new_page()
        pg.set_content("<!doctype html><body></body>")
        bad = []
        for f in files:
            r = pg.evaluate(
                """(t) => {
                  document.body.innerHTML = t;
                  const svg = document.querySelector('svg');
                  if (!svg || !svg.viewBox || !svg.viewBox.baseVal.width) return null;
                  const vb = svg.viewBox.baseVal;
                  let bb; try { bb = svg.getBBox(); } catch (e) { return null; }
                  return {vb: [vb.x, vb.y, vb.width, vb.height],
                          bb: [bb.x, bb.y, bb.width, bb.height]};
                }""", f.read_text(errors="replace"))
            if not r:
                continue
            vx, vy, vw, vh = r["vb"]
            bx, by, bw, bh = r["bb"]
            # ≤5% spill is source-faithful bleed (e.g. linkedin's own symbol
            # clips a ~1px sliver); the defect mechanic cropped ≥25% per axis
            # (32-grid artwork under a 24 viewBox).
            tol = 0.05 * max(vw, vh)
            if (bx < vx - tol or by < vy - tol
                    or bx + bw > vx + vw + tol or by + bh > vy + vh + tol):
                bad.append((f.name, r))
        pg.close()
        self.assertFalse(bad, f"artwork exceeds its viewBox (cropped glyphs): {bad}")

    @unittest.skipUnless(_HS_BRAND.is_dir(), "hubspot-v2 brand dir absent")
    def test_hubspot_chrome_glyph_artwork_fits_viewbox(self):
        files = _chrome_glyph_assets(_HS_BRAND)
        self.assertGreaterEqual(len(files), 10)   # chevron+utility+socials at least
        self._assert_artwork_fits_viewbox(files)

    @unittest.skipUnless(_REMOTE_BRAND.is_dir(), "remote brand dir absent")
    def test_remote_chrome_glyph_artwork_fits_viewbox(self):
        files = _chrome_glyph_assets(_REMOTE_BRAND)
        self.assertGreaterEqual(len(files), 1)
        self._assert_artwork_fits_viewbox(files)

    def test_rendered_projection_fills_host_unclipped(self):
        # end-to-end: a 32-grid glyph through the REAL emission (chevron span +
        # footer social span) paints its full artwork inside the host box, with
        # no ancestor overflow clipping — in a tight line-height flex row like
        # the real nav/footer contexts.
        art = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" '
               'fill="currentColor"><path d="M2 2h28v28H2z"/></svg>')
        inline = cr.sanitize_inline_svg(art)
        self.assertIsNotNone(inline)
        chev = cr._nav_chev_span({"_inlineSvg": inline, "_dataUri": "data:x"})
        html = ("<!doctype html><html><head><style>" + cr.COMPONENT_CSS
                + ".cs-nav-chev { display: inline-block; width: 16px; height: 16px; }"
                + ".cs-nav-chev > svg { display: block; width: 100%; height: 100%; }"
                + "</style></head><body>"
                + '<nav style="display:flex; line-height:1; overflow:hidden;'
                + ' font-size:14px; height:40px; align-items:center">'
                + f'<a href="#">Products {chev}</a></nav>'
                + "</body></html>")
        pg = self._browser.new_page()
        pg.set_content(html)
        r = pg.evaluate("""() => {
          const svg = document.querySelector('.cs-nav-chev svg');
          const host = svg.closest('.cs-nav-chev');
          const hr = host.getBoundingClientRect();
          const ctm = svg.getScreenCTM();
          let bb; try { bb = svg.getBBox(); } catch (e) { return null; }
          const px = (x, y) => ({ x: ctm.a * x + ctm.c * y + ctm.e,
                                  y: ctm.b * x + ctm.d * y + ctm.f });
          const p0 = px(bb.x, bb.y), p1 = px(bb.x + bb.width, bb.y + bb.height);
          // clipping ancestors between svg and body must contain the artwork
          let clipped = false;
          for (let a = svg.parentElement; a && a !== document.body; a = a.parentElement) {
            const cs = getComputedStyle(a);
            if (!/(hidden|clip|scroll|auto)/.test(cs.overflow + cs.overflowX + cs.overflowY))
              continue;
            const ar = a.getBoundingClientRect();
            if (p0.x < ar.left - 0.5 || p0.y < ar.top - 0.5
                || p1.x > ar.right + 0.5 || p1.y > ar.bottom + 0.5) clipped = true;
          }
          return { host: {l: hr.left, t: hr.top, r: hr.right, b: hr.bottom},
                   art: {l: p0.x, t: p0.y, r: p1.x, b: p1.y}, clipped };
        }""")
        pg.close()
        self.assertIsNotNone(r)
        self.assertFalse(r["clipped"], r)
        # artwork projection sits inside the host box (nothing self-clips): the
        # 2..30 art square projects to ~1..15 in a 16px box
        self.assertGreaterEqual(r["art"]["l"], r["host"]["l"] - 0.5, r)
        self.assertGreaterEqual(r["art"]["t"], r["host"]["t"] - 0.5, r)
        self.assertLessEqual(r["art"]["r"], r["host"]["r"] + 0.5, r)
        self.assertLessEqual(r["art"]["b"], r["host"]["b"] + 0.5, r)
        # and it FILLS the box (a cropped 24-viewBox over 32-grid art would
        # project past the box instead; a too-small projection means shrink)
        self.assertGreater(r["art"]["r"] - r["art"]["l"], 12)

    def test_cropped_viewbox_is_detected(self):
        # the pre-repair mechanic reproduced: 32-grid artwork under a 24 viewBox
        # projects PAST the host box — the guard must see it.
        art = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
               'fill="currentColor"><path d="M2 2h28v28H2z"/></svg>')
        pg = self._browser.new_page()
        pg.set_content(
            "<!doctype html><body><span style='display:inline-block;width:16px;"
            "height:16px'>" + art.replace("<svg ", "<svg style='display:block;"
            "width:100%;height:100%' ") + "</span></body>")
        r = pg.evaluate("""() => {
          const svg = document.querySelector('svg');
          const hr = svg.parentElement.getBoundingClientRect();
          const ctm = svg.getScreenCTM();
          const bb = svg.getBBox();
          const x1 = ctm.a * (bb.x + bb.width) + ctm.e;
          return { artRight: x1, hostRight: hr.right };
        }""")
        pg.close()
        self.assertGreater(r["artRight"], r["hostRight"] + 2)


# ── D4: curated instant chevron swap ───────────────────────────────────────────────


def _chev_doc(*, transition="transform 0.3s", curation=None) -> dict:
    chev = {"kind": "svg", "asset": "assets/c.svg", "box": {"w": 16, "h": 16},
            "gap": 4, "_dataUri": "data:image/svg+xml;base64,QQ=="}
    if transition:
        chev["transition"] = transition
    if curation:
        chev["curation"] = curation
    return {**copy.deepcopy(FIXTURE_DOC), "navbar": {
        "primary": [{"label": "P", "menu": {"columns": [
            {"heading": "G", "links": [{"label": "x"}]}]}}],
        "measured": {"trigger": {"chevron": chev}}}}


class ChevronInstantSwapTest(unittest.TestCase):
    _CURATION = {"motion": {"resolve": "instant", "by": "user",
                            "ts": "2026-07-14T10:30:00Z", "reason": "fix5"}}

    def _transition_of(self, css: str) -> str:
        m = re.search(r"\.cs-nav-chev \{[^}]*transition: ([^;]+);", css)
        self.assertIsNotNone(m, css)
        return m.group(1).strip()

    def test_generation_lane_honors_curated_instant(self):
        css = cr.nav_affordance_css(_chev_doc(curation=self._CURATION))
        self.assertEqual(self._transition_of(css), "none")
        # the flip itself survives — only the tween is gone
        self.assertIn(".cs-nav-lang[open] .cs-nav-chev { transform:", css)

    def test_replica_lane_keeps_measured_tween(self):
        css = cr.nav_affordance_css(_chev_doc(curation=self._CURATION),
                                    honor_curation=False)
        self.assertEqual(self._transition_of(css), "transform 0.3s")

    def test_uncurated_measured_transition_untouched(self):
        css = cr.nav_affordance_css(_chev_doc())
        self.assertEqual(self._transition_of(css), "transform 0.3s")

    def test_factless_degrade_is_instant_not_invented(self):
        # AS-47: motion on a state-change glyph is measured or ABSENT — the old
        # degrade invented a rotation tween on the brand's motion tokens.
        css = cr.nav_affordance_css(_chev_doc(transition=None))
        self.assertEqual(self._transition_of(css), "none")
        self.assertNotIn("--c-motion-fast", css.split(".cs-nav-chev--mask")[0])

    def test_both_brands_author_the_curation(self):
        import yaml
        for brand_dir in (_HS_BRAND, _REMOTE_BRAND):
            if not brand_dir.is_dir():
                continue
            doc = yaml.safe_load((brand_dir / "brand.yaml").read_text())
            chev = (((doc.get("navbar") or {}).get("measured") or {})
                    .get("trigger") or {}).get("chevron") or {}
            cur = (chev.get("curation") or {}).get("motion") or {}
            self.assertEqual(str(cur.get("resolve")), "instant", brand_dir)
            self.assertTrue(chev.get("transition"), brand_dir)  # evidence intact


if __name__ == "__main__":
    unittest.main()
