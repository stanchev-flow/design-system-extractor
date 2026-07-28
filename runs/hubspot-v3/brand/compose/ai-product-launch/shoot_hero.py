#!/usr/bin/env python3
"""Focused before/after hero capture for the ai-product-launch generated page.

Captures the hero band (the first overlay section) at 1440 and 375 into
runs/hubspot-v3/brand/fix-shots/ with a caller-supplied phase tag.

Usage (repo root):
  env -u PLAYWRIGHT_BROWSERS_PATH ./venv/bin/python \
      runs/hubspot-v3/brand/compose/ai-product-launch/shoot_hero.py before
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
FIX_SHOTS = REPO / "runs" / "hubspot-v3" / "brand" / "fix-shots"


def shoot(phase: str) -> None:
    from playwright.sync_api import sync_playwright

    FIX_SHOTS.mkdir(parents=True, exist_ok=True)
    uri = (HERE / "index.html").resolve().as_uri()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for w, h in ((1440, 900), (375, 812)):
            page = browser.new_page(viewport={"width": w, "height": h})
            page.emulate_media(reduced_motion="reduce")
            page.goto(uri, wait_until="networkidle")
            page.wait_for_timeout(400)
            hero = page.query_selector("section.cs-overlay-sec")
            box = hero.bounding_box() if hero else None
            out = FIX_SHOTS / f"gen-hero-{phase}@{w}.png"
            if box:
                page.screenshot(path=str(out), clip={
                    "x": 0, "y": 0, "width": w,
                    "height": min(box["y"] + box["height"] + 8, 20000)})
                print(f"  hero height @{w} = {round(box['height'], 1)}px "
                      f"(top {round(box['y'], 1)})")
            else:
                page.screenshot(path=str(out))
            print(f"  shot {out.relative_to(REPO)}")
            page.close()
        browser.close()


if __name__ == "__main__":
    shoot(sys.argv[1] if len(sys.argv) > 1 else "before")
