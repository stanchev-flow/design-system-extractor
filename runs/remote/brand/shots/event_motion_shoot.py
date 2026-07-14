#!/usr/bin/env python3
"""event-agenda-motion.png: MID-TWEEN capture of the agenda disclosure (AS-47 proof).
Clicks a closed agenda row and freezes the frame ~half-way through the brand's 200ms
::details-content height tween (marker mid-turn, panel partially open, the exclusive
set's previous row mid-collapse). Uses a clipped page screenshot (a locator shot would
auto-wait for the element to stop animating — exactly the frame we want to catch).
Run from repo root:
env -u PLAYWRIGHT_BROWSERS_PATH ./venv/bin/python runs/remote/brand/shots/event_motion_shoot.py"""
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[3].parent  # repo root
BRAND = ROOT / "runs" / "remote" / "brand"
SHOTS = BRAND / "shots"
PAGE = BRAND / "compose" / "event-genlaunch" / "index.html"


def _clip(page, sel):
    """VIEWPORT-relative clip (a plain page.screenshot images the viewport, so the
    clip must intersect it), clamped to the visible box of the element."""
    return page.evaluate("""(sel) => {
      const r = document.querySelector(sel).getBoundingClientRect();
      const x = Math.max(0, r.x), y = Math.max(0, r.y);
      return {x, y,
              width: Math.min(window.innerWidth, r.right) - x,
              height: Math.min(window.innerHeight, r.bottom) - y};
    }""", sel)


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900},
                                device_scale_factor=1)
        page.goto(PAGE.as_uri(), wait_until="load", timeout=30000)
        page.evaluate("""async () => {
          const step = window.innerHeight;
          for (let y = 0; y < document.body.scrollHeight; y += step) {
            window.scrollTo(0, y); await new Promise(r => setTimeout(r, 90)); }
        }""")
        page.locator("#sec-3").first.scroll_into_view_if_needed()
        page.wait_for_timeout(400)
        # click the SECOND row's summary (row 0 is composed open): the exclusive set
        # collapses row 0 while row 1 expands — both tweens run on --c-motion-base.
        page.locator("#sec-3 .c-faq-item .c-faq-q").nth(1).click()
        page.wait_for_timeout(90)  # ~mid-way through the brand's 200ms tween
        page.screenshot(path=str(SHOTS / "event-agenda-motion.png"),
                        clip=_clip(page, "#sec-3"), animations="allow")
        print("[event] event-agenda-motion.png (mid-tween)")
        # settled AFTER state for comparison (row 1 open, row 0 closed)
        page.wait_for_timeout(600)
        page.screenshot(path=str(SHOTS / "event-agenda-motion-settled.png"),
                        clip=_clip(page, "#sec-3"))
        print("[event] event-agenda-motion-settled.png")
        page.close()
        browser.close()


if __name__ == "__main__":
    main()
