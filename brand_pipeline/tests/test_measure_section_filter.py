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


if __name__ == "__main__":
    unittest.main()
