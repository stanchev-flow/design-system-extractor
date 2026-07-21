#!/usr/bin/env python3
"""Tests for tools/extract/join_evidence.py (Phase 1 responsive-fidelity JOIN).

The join binds CSS rules (incl. @media + pseudo-state) to each measured element
via selector matching against the SAVED DOM, preserves ``calc()``/``var()``
expressions literally with their resolved custom-property chains, carries the
multi-viewport computed ladder, and attaches the owning section's vision role.

Two layers:
  * synthetic in-memory capture (no browser) exercising every join guarantee;
  * a real hubspot-v3 acceptance fixture asserting the hero ``calc(100dvh - ...)``
    height rule, the footer grid ``@media`` reflow, and the mega-nav
    @media/state/background rules are all captured (skipped if evidence absent).

Run:  ./venv/bin/python -m pytest brand_pipeline/tests/test_join_evidence.py
"""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]

spec = importlib.util.spec_from_file_location(
    "join_evidence", _REPO / "tools" / "extract" / "join_evidence.py")
je = importlib.util.module_from_spec(spec)
spec.loader.exec_module(je)


# ── synthetic capture builder ────────────────────────────────────────────────

_HTML = """<!doctype html><html><body>
  <header class="site-nav" id="nav">
    <nav><a class="nav-link" href="#">Home</a></nav>
    <button class="menu-toggle">Menu</button>
  </header>
  <main>
    <section class="hero-band" id="hero">
      <div class="hero-inner">
        <h1 class="hero-title">Hi</h1>
        <a class="btn btn-primary" href="#">Go</a>
      </div>
    </section>
    <section class="feature-band" id="feat">
      <div class="cards"><div class="card">c</div></div>
    </section>
  </main>
  <footer class="site-footer">
    <div class="footer-grid"><ul class="footer-col"><li><a>x</a></li></ul></div>
  </footer>
</body></html>"""

_CSS_RULES = [
    {"file": "a.css", "media": "", "selector": ":root", "decls": "--nav-h:56px", "kind": "rule"},
    {"file": "a.css", "media": "@media(width >= 1080px)", "selector": ":root",
     "decls": "--nav-h:128px", "kind": "rule"},
    {"file": "a.css", "media": "", "selector": ".hero-band",
     "decls": "min-height:calc(100dvh - var(--nav-h));background:#042729", "kind": "rule"},
    {"file": "a.css", "media": "@media(width >= 900px)", "selector": ".footer-grid",
     "decls": "display:grid;grid-template-columns:repeat(4,1fr)", "kind": "rule"},
    {"file": "a.css", "media": "", "selector": ".nav-link:hover", "decls": "color:red", "kind": "rule"},
    {"file": "a.css", "media": "@media(width >= 1080px)", "selector": ".site-nav",
     "decls": "background:#ffffff", "kind": "rule"},
    {"file": "a.css", "media": "", "selector": ".btn-primary", "decls": "background:#ff5500", "kind": "rule"},
    {"file": "a.css", "media": "", "selector": "p", "decls": "margin:0", "kind": "rule"},
]


def _tier_headings(px):
    return {"headings": {"h1": {"font-size": f"{px}px", "_rect": {"x": 0, "y": 0, "w": 10, "h": px}}}}


_COMPUTED = {
    "schemaVersion": "computed-measure.v2",
    "viewport": {"w": 1440, "h": 900},
    "chrome": {
        "header": {"background-color": "rgb(255, 255, 255)", "_rect": {"x": 0, "y": 0, "w": 1440, "h": 80}},
        "footer": {"background-color": "rgb(31, 31, 31)", "_rect": {"x": 0, "y": 900, "w": 1440, "h": 300}},
    },
    "headings": {"h1": {"font-size": "40px", "_rect": {"x": 0, "y": 0, "w": 10, "h": 40}}},
    "actionGroups": [
        {"classes": "btn btn-primary", "tag": "a", "widthBehavior": "hug",
         "visibleLabel": "Go", "labelFit": {}, "measured": {"background-color": "rgb(255,85,0)"}},
        {"classes": "", "tag": "button", "widthBehavior": None, "visibleLabel": "",
         "labelFit": {}, "measured": {}},
    ],
    "tiers": {
        "1920": {**_tier_headings(48),
                 "containerFacts": [{"owner": "content", "tag": "div", "classes": "hero-inner",
                                     "usedWidthPx": 1080, "cssMaxWidth": "1080px"}]},
        "1440": {**_tier_headings(40),
                 "containerFacts": [{"owner": "content", "tag": "div", "classes": "hero-inner",
                                     "usedWidthPx": 1000, "cssMaxWidth": "1080px"}]},
        "960": {**_tier_headings(32), "containerFacts": []},
        "375": {**_tier_headings(24), "containerFacts": []},
    },
}

_SECTION_RECTS = {
    "schemaVersion": "computed-measure.v1",
    "source": "page.html",
    "chrome": [{"name": "header", "classes": "site-nav"},
               {"name": "footer", "classes": "site-footer"}],
    "sections": [
        {"index": 0, "tag": "section", "classes": "hero-band", "id": "hero",
         "rect": {"x": 0, "y": 80, "w": 1440, "h": 700}, "backgroundColor": "rgb(4, 39, 41)",
         "heading": "Hi"},
        {"index": 1, "tag": "section", "classes": "feature-band", "id": "feat",
         "rect": {"x": 0, "y": 780, "w": 1440, "h": 120}, "backgroundColor": "rgb(255, 255, 255)",
         "heading": ""},
    ],
}

_GROUNDING = {
    "section-00-hero-band.yaml": "schemaVersion: section-grounding.v1\nsectionRole: hero\n"
                                 "_source:\n  domClasses: hero-band\n",
    "section-01-feature-band.yaml": "schemaVersion: section-grounding.v1\nsectionRole: features\n"
                                    "_source:\n  domClasses: feature-band\n",
    "section-02-nav.yaml": "schemaVersion: section-grounding.v1\nsectionRole: navbar\n"
                           "_source:\n  domClasses: site-nav\n",
    "section-10-footer.yaml": "schemaVersion: section-grounding.v1\nsectionRole: footer\n"
                              "_source:\n  domClasses: site-footer\n",
}


def _build_capture(tmp: Path) -> tuple[Path, Path]:
    ev = tmp / "evidence"
    (ev / "grounding").mkdir(parents=True)
    (ev / "css-rules.json").write_text(json.dumps({"rules": _CSS_RULES}))
    (ev / "computed-styles.json").write_text(json.dumps(_COMPUTED))
    (ev / "section-rects.json").write_text(json.dumps(_SECTION_RECTS))
    for name, body in _GROUNDING.items():
        (ev / "grounding" / name).write_text(body)
    html = tmp / "page.html"
    html.write_text(_HTML)
    return ev, html


class SelectorParsingTests(unittest.TestCase):
    def test_split_selector_list_respects_parens(self):
        parts = je.split_selector_list(".a:not(.x,.y), .b > .c , div[data-a=b]")
        self.assertEqual(parts, [".a:not(.x,.y)", ".b > .c", "div[data-a=b]"])

    def test_key_compound_is_rightmost(self):
        key = je.parse_key_compound(".global-footer__nav-column > ul")
        self.assertEqual(key["tag"], "ul")
        self.assertEqual(key["classes"], frozenset())  # ancestor class is not the key

    def test_key_compound_strips_pseudo_but_records_it(self):
        key = je.parse_key_compound(".nav-link:hover")
        self.assertEqual(key["classes"], frozenset({"nav-link"}))
        self.assertIn(":hover", key["pseudos"])

    def test_selector_tokens_include_inside_functional_pseudos(self):
        classes, _ = je.selector_tokens("body:has(.global-nav-main)::after")
        self.assertIn("global-nav-main", classes)


class SyntheticJoinTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        ev, html = _build_capture(Path(self._tmp.name))
        self.doc = je.join(ev, html=html)
        self.els = {e["elementId"]: e for e in self.doc["elements"]}

    def tearDown(self):
        self._tmp.cleanup()

    def _rules(self, element_id):
        return self.els[element_id]["cssRules"]

    def test_media_and_hover_rules_bind_to_right_element(self):
        # :hover state rule (on a nav descendant) binds to the nav/header record
        nav = self.els["chrome-header"]
        hover = [r for r in nav["cssRules"] if ":hover" in r["pseudo"]]
        self.assertTrue(hover, "nav must carry the .nav-link:hover rule")
        self.assertTrue(any(r["selector"] == ".nav-link:hover" for r in hover))
        # @media rule on the nav itself binds too
        media = [r for r in nav["cssRules"] if r["media"] and "background" in r["decls"]]
        self.assertTrue(media, "nav must carry its @media background rule")
        # the footer grid @media rule binds to the footer, not the hero
        footer_media = [r for r in self._rules("chrome-footer")
                        if r["media"] and "grid" in r["decls"]]
        self.assertTrue(footer_media)
        hero_grid = [r for r in self._rules("section-00") if "grid-template-columns" in r["decls"]]
        self.assertFalse(hero_grid, "footer-only grid rule must not leak into the hero")

    def test_calc_var_expression_preserved_literally(self):
        hero = self.els["section-00"]
        calc = [r for r in hero["cssRules"] if "calc(100dvh - var(--nav-h))" in r["decls"]]
        self.assertTrue(calc, "literal calc()/var() expression must be preserved verbatim")
        # the referenced custom property is resolved with its per-@media literals
        nav_h = hero["customProperties"].get("--nav-h")
        self.assertIsNotNone(nav_h)
        values = {(e["media"], e["value"]) for e in nav_h}
        self.assertIn(("", "56px"), values)
        self.assertIn(("@media(width >= 1080px)", "128px"), values)

    def test_multi_viewport_ladder_captured(self):
        # heading carries a genuine 4-tier ladder with distinct sizes
        ladder = self.els["heading-h1"]["computedLadder"]
        self.assertEqual(set(ladder.keys()), {"1920", "1440", "960", "375"})
        sizes = {t: ladder[t]["font-size"] for t in ladder}
        self.assertEqual(sizes, {"1920": "48px", "1440": "40px", "960": "32px", "375": "24px"})
        # the hero section ladder is multi-viewport too (container width reflow)
        hero_ladder = self.els["section-00"]["computedLadder"]
        self.assertIsNotNone(hero_ladder["1920"])
        self.assertIsNotNone(hero_ladder["375"])
        self.assertEqual(hero_ladder["1440"]["rect"]["w"], 1440)

    def test_vision_role_attached_to_element_and_owning_section(self):
        self.assertEqual(self.els["section-00"]["visionRole"], "hero")
        self.assertEqual(self.els["section-01"]["visionRole"], "features")
        self.assertEqual(self.els["chrome-footer"]["visionRole"], "footer")
        self.assertEqual(self.els["chrome-header"]["visionRole"], "navbar")
        # heading + action inherit the owning section's (hero) vision role
        self.assertEqual(self.els["heading-h1"]["visionRole"], "hero")
        self.assertEqual(self.els["action-00"]["visionRole"], "hero")

    def test_coverage_report_shape(self):
        cov = self.doc["coverage"]
        self.assertEqual(set(cov.keys()),
                         {"totalElements", "withGoverningRule", "missingRule", "coveragePct"})
        self.assertEqual(cov["totalElements"], len(self.doc["elements"]))
        self.assertLessEqual(cov["withGoverningRule"], cov["totalElements"])
        self.assertIsInstance(cov["missingRule"], list)
        for m in cov["missingRule"]:
            self.assertEqual(set(m.keys()), {"elementId", "kind", "classes", "reason"})
        # the classless cookie button cannot be located -> reported missing with reason
        missing_ids = {m["elementId"] for m in cov["missingRule"]}
        self.assertIn("action-01", missing_ids)

    def test_rule_scopes_recorded(self):
        hero = self.els["section-00"]
        self.assertIn("self", hero["cssRuleScopes"])
        # hero owns the .hero-band rule as a self match
        self.assertTrue(any(r["scope"] == "self" and r["selector"] == ".hero-band"
                            for r in hero["cssRules"]))

    def test_provenance_and_schema(self):
        self.assertEqual(self.doc["schemaVersion"], "joined-evidence.v1")
        self.assertEqual(self.doc["primaryTier"], "1440")
        prov = self.els["section-00"]["provenance"]
        self.assertTrue(prov["domLocated"])
        self.assertEqual(prov["cssRules"], "css-rules.json")


class HubspotV3AcceptanceTests(unittest.TestCase):
    """Real hubspot-v3 evidence: the three responsive-fidelity acceptance facts."""

    @classmethod
    def setUpClass(cls):
        ev = _REPO / "runs" / "hubspot-v3" / "brand" / "evidence"
        if not (ev / "css-rules.json").is_file():
            raise unittest.SkipTest("hubspot-v3 evidence not present")
        try:
            cls.doc = je.join(ev, project_root=_REPO)
        except SystemExit as exc:  # html source unresolved
            raise unittest.SkipTest(f"hubspot-v3 capture unavailable: {exc}")
        cls.checks = je.acceptance_report(cls.doc)
        cls.els = {e["elementId"]: e for e in cls.doc["elements"]}

    def test_hero_contains_literal_calc_viewport_height(self):
        hero = self.els["section-00"]
        self.assertEqual(hero["visionRole"], "hero")
        calc = [r for r in hero["cssRules"]
                if "calc(100dvh - var(--global-nav-header-height))" in r["decls"]]
        self.assertTrue(calc, "hero must carry the literal calc(100dvh - var(--global-nav-header-height))")
        self.assertTrue(self.checks["hero_viewport_height_rule"]["pass"])
        # the nav-header-height var resolves to its 56px + 128px @media literals
        chain = hero["customProperties"].get("--global-nav-header-height", [])
        vals = {e["value"] for e in chain}
        self.assertIn("56px", vals)
        self.assertIn("128px", vals)

    def test_footer_contains_grid_media_breakpoint_rules(self):
        footer = self.els["chrome-footer"]
        media_layout = [r for r in footer["cssRules"]
                        if r["media"] and "footer" in r["selector"].lower()
                        and any(k in r["decls"] for k in ("grid", "flex", "column", "display"))]
        self.assertTrue(media_layout, "footer must carry its @media column/grid reflow rules")
        self.assertTrue(self.checks["footer_grid_media_rules"]["pass"])

    def test_nav_carries_media_state_and_background_rules(self):
        nav = self.els["chrome-header"]
        self.assertTrue(any(r["media"] for r in nav["cssRules"]))
        self.assertTrue(any(r["pseudo"] for r in nav["cssRules"]))
        self.assertTrue(any("background" in r["decls"] for r in nav["cssRules"]))
        # includes an actual global-nav background rule (not only descendant buttons)
        self.assertTrue(any("global-nav" in r["selector"] and "background" in r["decls"]
                            for r in nav["cssRules"]))
        self.assertTrue(self.checks["nav_media_state_background_rules"]["pass"])

    def test_coverage_is_reported_and_high(self):
        cov = self.doc["coverage"]
        self.assertGreaterEqual(cov["coveragePct"], 90.0)
        self.assertEqual(cov["totalElements"], len(self.doc["elements"]))


if __name__ == "__main__":
    unittest.main()
