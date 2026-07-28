#!/usr/bin/env python3
"""Demonstration screenshots proving the NEW interaction facts render VISIBLY:
  * @375 mobile drawer OPEN (measured surface + slide) after tapping the burger,
  * @375 + @1440 sticky nav with the measured scrolled register (bg + shadow),
  * @1440 footer locale selector.
Writes into compose/replica/interaction-demo/. Run with the repo venv."""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
INDEX = HERE / "replica" / "index.html"
OUT = HERE / "replica" / "interaction-demo"
OUT.mkdir(parents=True, exist_ok=True)
url = INDEX.as_uri()


def shoot():
    with sync_playwright() as p:
        b = p.chromium.launch()
        # ── @375 mobile: default (drawer closed) then burger-open (drawer visible) ──
        pg = b.new_page(viewport={"width": 375, "height": 780})
        pg.goto(url, wait_until="networkidle")
        pg.wait_for_timeout(400)
        pg.screenshot(path=str(OUT / "m375-nav-closed.png"))
        burger = pg.query_selector("#page-nav .cs-nav-burger")
        if burger:
            burger.click()
            pg.wait_for_timeout(600)  # let the measured slide animation settle
            pg.screenshot(path=str(OUT / "m375-drawer-open.png"))
            print("drawer-open shot: burger toggled")
        else:
            print("WARN: no burger found @375")
        pg.close()

        # ── @1440 sticky: top (at-rest) vs scrolled (is-scrolled register paints) ──
        pg = b.new_page(viewport={"width": 1440, "height": 900})
        pg.goto(url, wait_until="networkidle")
        pg.wait_for_timeout(300)
        pg.screenshot(path=str(OUT / "d1440-nav-atrest.png"))
        pg.evaluate("window.scrollTo(0, 700)")
        pg.wait_for_timeout(500)
        scrolled = pg.evaluate("document.getElementById('page-nav')."
                               "classList.contains('is-scrolled')")
        # crop the sticky nav strip so the scrolled shadow/bg is unmistakable
        nav = pg.query_selector("#page-nav")
        if nav:
            nav.screenshot(path=str(OUT / "d1440-nav-scrolled.png"))
        print(f"sticky scrolled class active: {scrolled}")

        # ── @1440 footer locale selector (open the disclosure) ──
        loc = pg.query_selector("[data-locale-selector]")
        if loc:
            loc.evaluate("el => { el.open = true; el.scrollIntoView({block:'center'}); }")
            pg.wait_for_timeout(300)
            loc.screenshot(path=str(OUT / "d1440-footer-locale.png"))
            print("footer locale shot: disclosure opened")
        else:
            print("WARN: no locale selector found")
        pg.close()
        b.close()
    print(f"[demo] wrote screenshots -> {OUT}")


if __name__ == "__main__":
    sys.exit(shoot())
