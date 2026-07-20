#!/usr/bin/env python3
"""Regression tests for measure_computed.py section collection (hubspot-v2 2026-07).

The bug: mega-menu dropdown panels keep layout boxes while ``visibility:hidden``
(and footer link columns are <section>-shaped), so the outermost-<section>
fallback wrote chrome-nested/invisible rects into section-rects.json. Those
phantom bands shifted every replica band mapping (three 770px "sections" at the
nav's y, footer columns as trailing sections) and tanked the replica score.

Runs the measure JS against synthetic fixtures in headless Chromium; skipped
when Playwright/browser is unavailable.

Run:  ./venv/bin/python -m unittest brand_pipeline.tests.test_measure_section_filter
"""
from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]

spec = importlib.util.spec_from_file_location(
    "measure_computed", _REPO / "tools" / "extract" / "measure_computed.py")
mc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mc)


def _measure(html: str) -> dict:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # pragma: no cover
        raise unittest.SkipTest(f"playwright unavailable: {exc}")
    with tempfile.TemporaryDirectory() as td:
        page_p = Path(td) / "page.html"
        page_p.write_text(html)
        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch()
                page = browser.new_page(viewport={"width": 1440, "height": 900},
                                        java_script_enabled=False)
                page.goto(page_p.resolve().as_uri(), wait_until="domcontentloaded")
                facts = page.evaluate(mc.JS, {})
                browser.close()
                return facts
        except Exception as exc:  # pragma: no cover
            raise unittest.SkipTest(f"chromium unavailable: {exc}")


_STYLE = """
  body { margin: 0; }
  section { display: block; height: 400px; }
"""


class SectionFilterTests(unittest.TestCase):
    def test_hidden_main_children_are_not_sections(self):
        """Direct-children path: visibility:hidden / aria-hidden nodes drop."""
        facts = _measure(f"""<!doctype html><html><head><style>{_STYLE}</style></head>
        <body><main>
          <section class="s-one">one</section>
          <section class="s-two">two</section>
          <section class="s-three">three</section>
          <section class="phantom-dropdown" style="visibility:hidden">menu</section>
          <div aria-hidden="true"><section class="phantom-aria">x</section></div>
        </main></body></html>""")
        classes = [s["classes"] for s in facts["sections"]]
        self.assertEqual(len(classes), 3, classes)
        self.assertNotIn("phantom-dropdown", " ".join(classes))

    def test_outermost_fallback_excludes_chrome_and_hidden(self):
        """Fallback path (<3 main children): header/footer-nested and hidden
        <section> nodes are chrome, not content sections."""
        facts = _measure(f"""<!doctype html><html><head><style>{_STYLE}</style></head>
        <body>
          <header>
            <nav>bar</nav>
            <section class="nav-dropdown-a" style="visibility:hidden">panel</section>
            <section class="nav-dropdown-b" style="visibility:hidden">panel</section>
          </header>
          <main>
            <section class="hero">hero</section>
            <section class="content">content</section>
          </main>
          <footer>
            <section class="footer-col-1">links</section>
            <section class="footer-col-2">links</section>
          </footer>
        </body></html>""")
        classes = [s["classes"] for s in facts["sections"]]
        self.assertEqual(sorted(classes), ["content", "hero"], classes)

    def test_chrome_rects_still_measured(self):
        """The header/footer chrome bands themselves keep being measured."""
        facts = _measure(f"""<!doctype html><html><head><style>{_STYLE}</style></head>
        <body>
          <header style="height:120px">nav</header>
          <main>
            <section class="a">a</section>
            <section class="b">b</section>
            <section class="c">c</section>
          </main>
          <footer style="height:300px">foot</footer>
        </body></html>""")
        names = {c["name"] for c in facts["chromeRects"]}
        self.assertEqual(names, {"header", "footer"})


class ActionLabelEvidenceTests(unittest.TestCase):
    def _group(self, inner: str, attrs: str = "", width: int = 160) -> dict:
        facts = _measure(f"""<!doctype html><html><head><style>
        .btn {{ display:inline-block; box-sizing:border-box; width:{width}px;
                padding:8px 16px; font:500 14px Arial; }}
        .sr-only {{ position:absolute; width:1px; height:1px; overflow:hidden;
                    clip:rect(0,0,0,0); clip-path:inset(50%); }}
        </style></head><body><a class="btn" {attrs}>{inner}</a></body></html>""")
        return facts["actionGroups"][0]

    def test_visible_span_excludes_sr_only_suffix(self):
        row = self._group(
            '<span>Start now</span><span class="sr-only"> with the complete platform</span>')
        self.assertEqual(row["visibleLabel"], "Start now")
        self.assertEqual(row["accessibleName"], "Start now with the complete platform")
        self.assertTrue(row["labelFit"]["visibleFits"])
        self.assertTrue(row["labelFit"]["likelyHiddenTextConflation"])

    def test_long_aria_label_is_accessible_only(self):
        row = self._group("<span>Demo</span>",
                          'aria-label="Request a personalized product demonstration"')
        self.assertEqual(row["visibleLabel"], "Demo")
        self.assertEqual(row["accessibleName"],
                         "Request a personalized product demonstration")
        self.assertEqual(row["ariaLabel"],
                         "Request a personalized product demonstration")

    def test_hidden_descendants_are_excluded(self):
        row = self._group(
            '<span>Continue</span><span style="display:none"> display</span>'
            '<span style="visibility:hidden"> visibility</span>'
            '<span aria-hidden="true"> aria</span>')
        self.assertEqual(row["visibleLabel"], "Continue")
        self.assertIn("display", row["accessibleName"])

    def test_labelledby_sets_accessible_name(self):
        facts = _measure("""<!doctype html><html><body>
        <span id="short">Open</span><span id="detail">Open account settings</span>
        <button class="btn" aria-labelledby="detail"><span>Open</span></button>
        </body></html>""")
        row = facts["actionGroups"][0]
        self.assertEqual(row["visibleLabel"], "Open")
        self.assertEqual(row["accessibleName"], "Open account settings")
        self.assertEqual(row["labelledBy"], "detail")

    def test_width_sanity_flags_semantic_text_not_visible_text(self):
        row = self._group(
            '<span>Go</span><span class="sr-only"> to the detailed onboarding workflow</span>',
            width=72)
        self.assertTrue(row["labelFit"]["visibleFits"])
        self.assertGreater(row["labelFit"]["semanticEstimatedWidth"],
                           row["labelFit"]["hostWidth"])

    def test_hubspot_v3_control_geometry_fixture(self):
        row = self._group(
            '<span>Get a demo</span><span class="sr-only"> of HubSpot\'s premium software</span>',
            width=113)
        self.assertEqual(row["visibleLabel"], "Get a demo")
        self.assertEqual(row["accessibleName"],
                         "Get a demo of HubSpot's premium software")
        self.assertTrue(row["labelFit"]["visibleFits"])


if __name__ == "__main__":
    unittest.main()
