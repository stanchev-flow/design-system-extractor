#!/usr/bin/env python3
"""remote-fix Remote before/after shooter: full page + hero + footer of the e2e BEFORE
run (runs/remote/brand/compose/signup-launch) and this batch's AFTER run
(signup-launch-fixed), plus a HubSpot regression-run top shot. Same Playwright setup
as shoot_parity.py."""
from pathlib import Path

from playwright.sync_api import sync_playwright

REPO = Path(__file__).resolve().parent.parent.parent
OUT = Path(__file__).resolve().parent / "shots"

PAGES = [
    ("remote-before", REPO / "runs/remote/brand/compose/signup-launch/index.html"),
    ("remote-after", REPO / "runs/remote/brand/compose/signup-launch-fixed/index.html"),
    ("hubspot-after", REPO / "runs/hubspot/brand/compose/signup-launch-remotefix-live/index.html"),
]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        page = b.new_page(viewport={"width": 1440, "height": 900},
                          device_scale_factor=2, reduced_motion="reduce")
        for tag, path in PAGES:
            page.goto(path.resolve().as_uri(), wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(700)
            page.screenshot(path=str(OUT / f"{tag}-full.png"), full_page=True)
            hero = page.locator("#sec-0").first
            if hero.count():
                hero.screenshot(path=str(OUT / f"{tag}-hero.png"))
            foot = page.locator('[data-layout="closing-bookend"]').first
            if foot.count():
                foot.screenshot(path=str(OUT / f"{tag}-footer.png"))
        b.close()
    print("remote/hubspot shots done ->", OUT)


if __name__ == "__main__":
    main()
