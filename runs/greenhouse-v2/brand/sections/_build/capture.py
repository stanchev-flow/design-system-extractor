#!/usr/bin/env python3
"""Capture @1440 screenshots of every generated section + per-type contact
sheets + the gallery. Read-only screenshotting; edits no pipeline source."""
from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent.parent      # runs/.../sections
SHOTS = OUT / "shots"
MANIFEST = json.loads((OUT / "_build" / "manifest.json").read_text())


def _prep(page):
    # let webfonts + lazy media settle
    try:
        page.wait_for_load_state("networkidle", timeout=8000)
    except Exception:
        pass
    try:
        page.evaluate("document.fonts && document.fonts.ready")
    except Exception:
        pass
    page.wait_for_timeout(700)


def _scroll_through(page):
    """Force nested iframes (and their fonts/media) to load, then return to top."""
    total = page.evaluate("document.body.scrollHeight")
    y = 0
    while y < total:
        page.evaluate(f"window.scrollTo(0,{y})")
        page.wait_for_timeout(220)
        y += 700
    page.evaluate("window.scrollTo(0,0)")
    page.wait_for_timeout(1400)


def main():
    SHOTS.mkdir(parents=True, exist_ok=True)
    per_type = {}
    for m in MANIFEST:
        per_type.setdefault(m["type"], []).append(m)

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        # ---- per-section @1440 ----
        # small viewport height so a full_page shot equals the section's real
        # content height (no white viewport padding under short bands).
        page = browser.new_page(viewport={"width": 1440, "height": 200},
                                device_scale_factor=1)
        for m in MANIFEST:
            url = (OUT / m["path"]).as_uri()
            page.goto(url)
            _prep(page)
            out = SHOTS / f"{m['type']}-v{m['v']}.png"
            page.screenshot(path=str(out), full_page=True)
            print("shot", out.name)
        page.close()
        browser.close()


if __name__ == "__main__":
    main()
