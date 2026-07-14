#!/usr/bin/env python3
"""event-genlaunch screenshots: full page at 1440 plus per-section crops (hero, proof,
bento, agenda, quote, pricing, faq, form). Run from repo root:
env -u PLAYWRIGHT_BROWSERS_PATH ./venv/bin/python runs/remote/brand/shots/event_shoot.py"""
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[3].parent  # repo root
BRAND = ROOT / "runs" / "remote" / "brand"
SHOTS = BRAND / "shots"
PAGE = BRAND / "compose" / "event-genlaunch" / "index.html"

CROPS = [
    ("event-hero.png", "#sec-0"),
    ("event-proof.png", "#sec-1"),
    ("event-bento.png", "#sec-2"),
    ("event-agenda.png", "#sec-3"),
    ("event-quote.png", "#sec-4"),
    ("event-pricing.png", "#sec-5"),
    ("event-faq.png", "#sec-6"),
    ("event-form.png", "#sec-7"),
]


def settle(page) -> None:
    """Walk the page so the scroll-reveal observer fires for every section."""
    page.evaluate("""async () => {
      const step = window.innerHeight;
      for (let y = 0; y < document.body.scrollHeight; y += step) {
        window.scrollTo(0, y); await new Promise(r => setTimeout(r, 90)); }
      window.scrollTo(0, 0);
    }""")
    page.wait_for_timeout(600)


def main() -> None:
    SHOTS.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900},
                                device_scale_factor=1)
        page.goto(PAGE.as_uri(), wait_until="load", timeout=30000)
        settle(page)
        page.screenshot(path=str(SHOTS / "event-full-1440.png"), full_page=True)
        print("[event] event-full-1440.png")
        for crop_name, sel in CROPS:
            loc = page.locator(sel).first
            if not loc.count():
                print(f"[event] MISSING selector for {crop_name}: {sel}")
                continue
            loc.scroll_into_view_if_needed()
            page.wait_for_timeout(250)
            loc.screenshot(path=str(SHOTS / crop_name), timeout=15000)
            print(f"[event] {crop_name}")
        page.close()
        browser.close()


if __name__ == "__main__":
    main()
