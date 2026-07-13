#!/usr/bin/env python3
"""Fixture tests for the fid15 pass (2026-07) — NAV BAR AFFORDANCES:

  1. GLYPH RESOLUTION — `prepare_chrome_glyphs` inlines the bar's harvested
     affordance artwork (dropdown-trigger chevron, utility-control icons +
     chevrons, utility-banner cta arrow / close glyph) as data: URIs on the
     IN-MEMORY doc; missing files degrade silently; brand.yaml is never written.
  2. MARKUP — `render_navbar` emits the trigger chevron on menu-owning primary
     links (gallery bars included — the chevron is resting anatomy, unlike the
     page-level hover panels) and the trailing utility cluster (icon links +
     <details> locale dropdowns). Fact-less brands emit byte-identical bars.
  3. CSS — `nav_affordance_css` carries the measured geometry/motion and is ""
     for brands without the facts (AS-37 conditional-shipping discipline).
  4. LANE PARITY (AS-46) — the composed page (compose_page.build_page, shared by
     the replica + catalog lanes) renders chevrons, the utility cluster, and the
     measured utility-banner CTA; stripping the facts removes the markup.

Run:  ./venv/bin/python -m unittest brand_pipeline.tests.test_nav_affordances
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

import component_render as cr  # noqa: E402
import compose_page as cp      # noqa: E402

_REMOTE = _BRAND_PIPELINE.parent / "runs" / "remote" / "brand" / "brand.yaml"

SVG = b'<svg xmlns="http://www.w3.org/2000/svg"><path d="M4 6L8 10L12 6"/></svg>'

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


def _ctx(doc=None, **kw):
    ctx = cr.make_context(doc or FIXTURE_DOC, "surface/primary",
                          (doc or FIXTURE_DOC)["tokens"]["surfaces"]["surface/primary"])
    for k, v in kw.items():
        setattr(ctx, k, v)
    return ctx


def _affordance_navbar(*, resolved=True, inline=True) -> dict:
    """A navbar carrying the full fid15 fact set; ``resolved=True`` stamps what
    prepare_chrome_glyphs would (markup tests without a disk pass): the data URI
    plus — fix4 — the sanitized inline markup. ``inline=False`` simulates
    artwork that failed single-ink verification (mask-degrade channel)."""
    uri = "data:image/svg+xml;base64,QUFBQQ=="
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" '
           'aria-hidden="true" focusable="false">'
           '<path d="M4 6L8 10L12 6" stroke="currentColor"/></svg>')
    nav = {
        "primary": [
            {"label": "Products", "href": "",
             "menu": {"columns": [{"heading": "G", "links": [{"label": "x"}]}]}},
            {"label": "Pricing", "href": "/pricing"},
        ],
        "measured": {"trigger": {"chevron": {
            "kind": "svg", "asset": "assets/chev.svg", "box": {"w": 16, "h": 16},
            "gap": 4, "transition": "transform 0.2s",
            "openTransform": "matrix(-1, 0, 0, -1, 0, 0)"}}},
        "utility": [
            {"label": "Login", "href": "/sign-in", "kind": "link", "role": "login",
             "icon": {"kind": "svg", "asset": "assets/login.svg", "size": 24}},
            {"label": "Select language — current: English", "href": "",
             "kind": "dropdown", "role": "language",
             "ariaLabel": "Select language — current: English",
             "icon": {"kind": "svg", "asset": "assets/lang.svg", "size": 24},
             "chevron": {"kind": "svg", "asset": "assets/chev.svg",
                         "box": {"w": 16, "h": 16}},
             "dropdown": {
                 "items": [{"label": "English", "href": "/", "lang": "en-us",
                            "current": True},
                           {"label": "Nederlands", "href": "/nl-nl",
                            "lang": "nl-nl"}],
                 "panel": {"w": 180, "h": 200, "bg": "#fff", "radius": 6,
                           "paddingY": 8},
                 "item": {"fontSize": 15, "padding": "10px 12px", "color": "#111"},
                 "currentItem": {"bg": "#141415", "color": "#fff"}}},
        ],
    }
    if resolved:
        for node in (nav["measured"]["trigger"]["chevron"],
                     nav["utility"][0]["icon"], nav["utility"][1]["icon"],
                     nav["utility"][1]["chevron"]):
            node["_dataUri"] = uri
            if inline:
                node["_inlineSvg"] = svg
    return nav


def _doc_with_nav(nav) -> dict:
    doc = copy.deepcopy(FIXTURE_DOC)
    doc["navbar"] = nav
    return doc


# ── 1) glyph resolution (prepare_chrome_glyphs) ────────────────────────────────────

class PrepareNavGlyphsTest(unittest.TestCase):
    def _brand_dir(self, td: Path) -> Path:
        (td / "assets").mkdir()
        for name in ("chev.svg", "login.svg", "lang.svg", "arrow.svg"):
            (td / "assets" / name).write_bytes(SVG)
        return td

    def test_affordance_assets_resolve_to_data_uris(self):
        with tempfile.TemporaryDirectory() as td:
            self._brand_dir(Path(td))
            doc = _doc_with_nav(_affordance_navbar(resolved=False))
            doc["navbar"]["utilityBanner"] = {
                "observed": True, "text": "hi", "dismissible": True,
                "cta": {"label": "Go", "href": "#",
                        "arrow": {"kind": "svg", "asset": "assets/arrow.svg"}},
                "close": {"kind": "svg", "asset": "assets/chev.svg",
                          "box": {"w": 16, "h": 16}}}
            n = cr.prepare_chrome_glyphs(doc, td)
        # trigger chevron + 2 utility icons + utility chevron + cta arrow + close
        self.assertEqual(n, 6)
        nav = doc["navbar"]
        for node in (nav["measured"]["trigger"]["chevron"],
                     nav["utility"][0]["icon"], nav["utility"][1]["icon"],
                     nav["utility"][1]["chevron"],
                     nav["utilityBanner"]["cta"]["arrow"],
                     nav["utilityBanner"]["close"]):
            self.assertTrue(str(node.get("_dataUri", "")).startswith(
                "data:image/svg+xml;base64,"), node)

    def test_missing_files_degrade_silently(self):
        with tempfile.TemporaryDirectory() as td:  # no assets/ tree at all
            doc = _doc_with_nav(_affordance_navbar(resolved=False))
            n = cr.prepare_chrome_glyphs(doc, td)
        self.assertEqual(n, 0)
        nav = doc["navbar"]
        self.assertNotIn("_dataUri", nav["measured"]["trigger"]["chevron"])
        self.assertNotIn("_dataUri", nav["utility"][0]["icon"])

    def test_namespaceless_dom_harvest_gains_xmlns_in_data_uri(self):
        # outerHTML of an inline <svg> legally omits xmlns; standalone (mask/img)
        # consumption is XML, where a namespace-less payload silently paints
        # NOTHING. The data URI must carry the injected declaration.
        import base64
        naked = b'<svg width="16" height="16" viewBox="0 0 16 16" fill="none">' \
                b'<path d="M4 6L8 10L12 6" stroke="currentColor"/></svg>'
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "assets").mkdir()
            (Path(td) / "assets" / "chev.svg").write_bytes(naked)
            nav = {"measured": {"trigger": {"chevron": {
                "kind": "svg", "asset": "assets/chev.svg",
                "box": {"w": 16, "h": 16}}}}}
            doc = _doc_with_nav(nav)
            self.assertEqual(cr.prepare_chrome_glyphs(doc, td), 1)
        uri = doc["navbar"]["measured"]["trigger"]["chevron"]["_dataUri"]
        payload = base64.b64decode(uri.split(",", 1)[1])
        self.assertIn(b'xmlns="http://www.w3.org/2000/svg"', payload)
        # already-namespaced artwork is left byte-identical
        self.assertEqual(cr._svg_with_namespace(SVG), SVG)

    def test_brand_yaml_on_disk_never_mutated(self):
        import yaml
        with tempfile.TemporaryDirectory() as td:
            self._brand_dir(Path(td))
            doc = _doc_with_nav(_affordance_navbar(resolved=False))
            by = Path(td) / "brand.yaml"
            by.write_text(yaml.safe_dump(doc, sort_keys=False))
            before = by.read_bytes()
            loaded = yaml.safe_load(by.read_text())
            cr.prepare_chrome_glyphs(loaded, td)
            cr.render_navbar(loaded, _ctx(loaded),
                             {"links": loaded["navbar"]["primary"]})
            after = by.read_bytes()
        self.assertEqual(before, after)
        self.assertIn("_dataUri", loaded["navbar"]["utility"][0]["icon"])  # in-memory only


# ── 2) navbar markup ────────────────────────────────────────────────────────────────

class NavbarAffordanceMarkupTest(unittest.TestCase):
    def test_menu_trigger_emits_chevron_inside_anchor(self):
        doc = _doc_with_nav(_affordance_navbar())
        html = cr.render_navbar(doc, _ctx(doc), {"links": doc["navbar"]["primary"]})
        m = re.search(r'<a class="c-arrow-link"[^>]*>Products(.*?)</a>', html)
        self.assertIsNotNone(m)
        # fix4 inline channel: the span nests the sanitized artwork; no mask class
        self.assertIn('class="cs-nav-chev"', m.group(1))
        self.assertNotIn("cs-nav-chev--mask", m.group(1))
        self.assertIn("<svg", m.group(1))
        self.assertIn('stroke="currentColor"', m.group(1))
        # the mask DEGRADE default still ships in the affordance CSS (gated
        # under .cs-nav-chev--mask, inert for inline spans)
        self.assertIn(".cs-nav-chev--mask", cr.nav_affordance_css(doc))
        # the plain destination carries no chevron
        m2 = re.search(r'<a class="c-arrow-link"[^>]*>Pricing(.*?)</a>', html)
        self.assertNotIn("cs-nav-chev", m2.group(1))

    def test_unverified_artwork_keeps_mask_degrade(self):
        # artwork that failed single-ink verification (_dataUri only, fix4):
        # the span rides the fix2 mask channel under the --mask modifier.
        doc = _doc_with_nav(_affordance_navbar(inline=False))
        html = cr.render_navbar(doc, _ctx(doc), {"links": doc["navbar"]["primary"]})
        m = re.search(r'<a class="c-arrow-link"[^>]*>Products(.*?)</a>', html)
        self.assertIn("cs-nav-chev cs-nav-chev--mask", m.group(1))
        self.assertNotIn("<svg", m.group(1))
        self.assertIn("--cs-nav-chev: url('data:image/svg+xml;base64,",
                      cr.nav_affordance_css(doc))

    def test_gallery_bar_carries_chevron_without_panels(self):
        # the chevron is resting bar anatomy — it renders in panel-free (gallery)
        # bars too; the mega panel itself stays page-level (ctx.mega_nav).
        doc = _doc_with_nav(_affordance_navbar())
        html = cr.render_navbar(doc, _ctx(doc), {"links": doc["navbar"]["primary"]})
        self.assertIn("cs-nav-chev", html)
        self.assertNotIn("cs-mega", html)
        html_page = cr.render_navbar(doc, _ctx(doc, mega_nav=True),
                                     {"links": doc["navbar"]["primary"]})
        self.assertIn("cs-nav-chev", html_page)
        self.assertIn("cs-mega", html_page)

    def test_utility_cluster_renders_icons_and_dropdown(self):
        doc = _doc_with_nav(_affordance_navbar())
        html = cr.render_navbar(doc, _ctx(doc), {"links": doc["navbar"]["primary"]})
        self.assertIn('class="cs-nav-util"', html)
        # login: inline icon artwork (fix4) + accessible text label + real href
        login = re.search(r'<a class="cs-nav-util-link" href="/sign-in">(.*?)</a>', html)
        self.assertIsNotNone(login)
        self.assertIn('class="cs-nav-util-icon"', login.group(1))
        self.assertIn("<svg", login.group(1))
        self.assertNotIn("cs-nav-util-icon--mask", login.group(1))
        self.assertIn("<span>Login</span>", login.group(1))
        # language: <details> dropdown, aria-labelled summary, current item marked
        self.assertIn('<details class="cs-nav-lang">', html)
        self.assertIn('aria-label="Select language — current: English"', html)
        self.assertIn('class="cs-nav-lang-menu"', html)
        self.assertIn('aria-current="true"', html)
        self.assertIn('hreflang="nl-nl"', html)
        # the dropdown summary carries its chevron
        summ = re.search(r"<summary.*?</summary>", html)
        self.assertIn("cs-nav-chev", summ.group(0))

    def test_unresolved_glyphs_degrade_to_text(self):
        # facts authored but artwork NOT resolved (no _dataUri): no icon/chevron
        # spans render; the accessible labels remain.
        doc = _doc_with_nav(_affordance_navbar(resolved=False))
        html = cr.render_navbar(doc, _ctx(doc), {"links": doc["navbar"]["primary"]})
        self.assertNotIn("cs-nav-chev", html)
        self.assertNotIn("cs-nav-util-icon", html)
        self.assertIn("<span>Login</span>", html)          # text link degrade
        self.assertIn('<details class="cs-nav-lang">', html)  # dropdown still works

    def test_factless_brand_renders_byte_identical_bar(self):
        doc = _doc_with_nav({"primary": [{"label": "About", "href": "/about"}]})
        html = cr.render_navbar(doc, _ctx(doc), {"links": doc["navbar"]["primary"]})
        for marker in ("cs-nav-chev", "cs-nav-util", "cs-nav-lang"):
            self.assertNotIn(marker, html)


# ── 3) affordance CSS gating ────────────────────────────────────────────────────────

class NavAffordanceCssTest(unittest.TestCase):
    def test_factless_doc_emits_nothing(self):
        self.assertEqual(cr.nav_affordance_css(FIXTURE_DOC), "")
        doc = _doc_with_nav({"primary": [{"label": "x"}]})
        self.assertEqual(cr.nav_affordance_css(doc), "")

    def test_measured_facts_ride_the_css(self):
        doc = _doc_with_nav(_affordance_navbar())
        css = cr.nav_affordance_css(doc)
        self.assertIn(".cs-nav-chev", css)
        self.assertIn("width: 16px; height: 16px", css)      # measured box
        self.assertIn("margin-left: 4px", css)               # measured gap
        self.assertIn("transform 0.2s", css)                 # measured motion
        self.assertIn("matrix(-1, 0, 0, -1, 0, 0)", css)     # measured open pose
        self.assertIn(".cs-nav-util", css)
        self.assertIn("background: #fff", css)               # measured panel bg
        self.assertIn("font-size: 15px", css)                # measured item register
        self.assertIn('.cs-nav-lang-item[aria-current] { background: #141415', css)

    def test_unresolved_chevron_keeps_utility_css_only(self):
        doc = _doc_with_nav(_affordance_navbar(resolved=False))
        css = cr.nav_affordance_css(doc)
        self.assertNotIn(".cs-nav-chev", css)   # artwork didn't resolve
        self.assertIn(".cs-nav-util", css)      # utility anatomy still declared


# ── 4) lane parity: the composed page (shared by replica + catalog lanes) ──────────

@unittest.skipUnless(_REMOTE.is_file(), "Remote run fixture not present")
class ComposedPageAffordancesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from styles import inactive_context
        cls.doc = cp.load_doc(_REMOTE)
        cls.order = [cls.doc["layouts"][0]["id"]]
        cls.html = cp.build_page(copy.deepcopy(cls.doc), _REMOTE, cls.order,
                                 inactive_context())

    def _nav_block(self, html: str) -> str:
        return html.split('id="page-nav"', 1)[1].split("</nav>", 1)[0]

    def test_page_nav_carries_chevrons_and_utility(self):
        nav = self._nav_block(self.html)
        self.assertIn("cs-nav-chev", nav)
        self.assertIn('class="cs-nav-util"', nav)
        self.assertIn('<details class="cs-nav-lang">', nav)
        self.assertIn(".cs-nav-chev", self.html)  # affordance CSS shipped

    def test_banner_cta_renders_measured_label_once(self):
        # the extracted label carries the source's own text arrow; the composer
        # must not append a second glyph (the old render_arrow_link path did).
        banner = self.html.split('id="page-banner"', 1)[1].split("</div>", 1)[0]
        self.assertIn("cs-utility-banner-cta", banner)
        self.assertIn("Take the quiz", banner)
        self.assertNotIn('class="c-arrow"', banner)
        self.assertIn("font-weight: 700", banner)      # measured presentation
        self.assertIn("text-decoration: underline", banner)

    def test_stripping_facts_removes_markup(self):
        from styles import inactive_context
        doc = copy.deepcopy(self.doc)
        doc["navbar"].pop("utility", None)
        (doc["navbar"].get("measured") or {}).pop("trigger", None)
        html = cp.build_page(doc, _REMOTE, self.order, inactive_context())
        nav = self._nav_block(html)
        self.assertNotIn("cs-nav-chev", nav)
        self.assertNotIn("cs-nav-util", nav)


if __name__ == "__main__":
    unittest.main()
