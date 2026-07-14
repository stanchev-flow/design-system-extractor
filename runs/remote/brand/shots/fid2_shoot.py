#!/usr/bin/env python3
"""fid2 punch-list screenshots: per-item bands from the rebuilt Remote replica +
chrome preview. Run from repo root: env -u PLAYWRIGHT_BROWSERS_PATH \
./venv/bin/python runs/remote/brand/shots/fid2_shoot.py"""
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[3].parent  # repo root
BRAND = ROOT / "runs" / "remote" / "brand"
SHOTS = BRAND / "shots"

REPLICA = BRAND / "compose" / "replica" / "index.html"
CHROME = BRAND / "chrome" / "index.html"

# (output name, selector) bands shot from the replica page
BANDS = [
    ("fid2-hero-png.png", "#sec-0"),                 # 1: transparent-PNG hero, no hatch
    ("fid2-marquee-fullbleed.png", "#sec-1"),        # 2: full-bleed measured marquee
    ("fid2-spacing-rhythm.png", "#sec-3"),           # 3: heading→body ladder rhythm
    ("fid2-accordion.png", "#sec-2"),                # 4: icons + circle-arrow + well
    ("fid2-banner-panel.png", "#sec-4"),             # 5: inset panel + art + h2
    ("fid2-cards-plates.png", "#sec-5"),             # 6: white card plates
    ("fid2-testimonials-person.png", "#sec-7"),      # 7: avatar + name/role rows
    ("fid2-footer-social.png", "#sec-10 .c-foot-bar, .c-foot-bar"),  # 8: bottom bar
    ("fid2-utility-banner.png", "#page-banner"),     # 9: measured neutral-900 banner
    ("fid2-nav-cta.png", "#page-nav"),               # 10a: measured neutral pill CTA
    ("fid2-badge-tier.png", "#sec-8"),               # follow-on: measured badge tier
]


def main() -> None:
    SHOTS.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900},
                                device_scale_factor=1)
        page.goto(REPLICA.as_uri(), wait_until="load", timeout=30000)
        # scroll pass so IO reveals fire, then settle
        page.evaluate("""async () => {
          const step = window.innerHeight;
          for (let y = 0; y < document.body.scrollHeight; y += step) {
            window.scrollTo(0, y); await new Promise(r => setTimeout(r, 90)); }
          window.scrollTo(0, 0);
        }""")
        page.wait_for_timeout(600)
        for name, sel in BANDS:
            loc = None
            for cand in sel.split(","):
                cand = cand.strip()
                if page.locator(cand).count():
                    loc = page.locator(cand).first
                    break
            if loc is None:
                print(f"[fid2] MISSING selector for {name}: {sel}")
                continue
            loc.scroll_into_view_if_needed()
            page.wait_for_timeout(250)
            loc.screenshot(path=str(SHOTS / name), timeout=15000)
            print(f"[fid2] {name}")
        # 10c: chrome mega-menu open-panel geometry (bounded card, not full-bleed)
        page.goto(CHROME.as_uri(), wait_until="load", timeout=30000)
        page.wait_for_timeout(400)
        tab = page.locator(".nav-tab.has-menu").first
        if tab.count():
            tab.hover()
            page.wait_for_timeout(350)
            page.screenshot(path=str(SHOTS / "fid2-mega-geometry.png"),
                            clip={"x": 0, "y": 0, "width": 1440, "height": 640})
            print("[fid2] fid2-mega-geometry.png")
        else:
            print("[fid2] chrome preview has no mega tab")
        browser.close()


if __name__ == "__main__":
    main()
