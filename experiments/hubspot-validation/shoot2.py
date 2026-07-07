#!/usr/bin/env python3
"""Per-section crops of the tokenized validation page (sec-0..sec-N)."""
from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
PAGE = REPO / "runs/hubspot/brand/compose/signup-launch-tokenized/index.html"
SHOTS = HERE / "shots"


def main() -> None:
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={"width": 1440, "height": 900})
        pg.goto(PAGE.as_uri())
        pg.wait_for_timeout(1200)
        n = pg.locator("section.cs-section").count()
        print("sections:", n)
        for i in range(n):
            sec = pg.locator("section.cs-section").nth(i)
            cls = sec.get_attribute("class")
            wrap = sec.evaluate("el => el.parentElement.id || ''")
            path = SHOTS / f"sec-{i}.png"
            try:
                sec.screenshot(path=str(path))
                print(i, cls, wrap, "->", path.name)
            except Exception as e:  # zero-height sections
                print(i, cls, wrap, "SKIP:", str(e)[:80])
        b.close()


if __name__ == "__main__":
    main()
