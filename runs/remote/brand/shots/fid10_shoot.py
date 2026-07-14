#!/usr/bin/env python3
"""fid10 after-screenshots: the composed-from-catalog page (compose/index.html) full-page
at 1440 + 2760 (the widths the section-alignment defect was filed at) plus per-defect
section crops. Run from repo root: env -u PLAYWRIGHT_BROWSERS_PATH \
./venv/bin/python runs/remote/brand/shots/fid10_shoot.py"""
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[3].parent  # repo root
BRAND = ROOT / "runs" / "remote" / "brand"
SHOTS = BRAND / "shots"
COMPOSED = BRAND / "compose" / "index.html"

# (output name, selector) per-defect crops, shot at 1440
CROPS = [
    ("fid10-composed-hero-after.png", "#sec-0"),           # hero band full-width
    ("fid10-composed-accordion-after.png", "#sec-2"),      # accordion split geometry
    ("fid10-composed-infra-after.png", "#sec-3"),          # split media frame / measure
    ("fid10-composed-partner-after.png", "#sec-6"),        # partner centered full-measure
    ("fid10-composed-badges-after.png", "#sec-8"),         # badge rows centered
    ("fid10-composed-closing-after.png", "#sec-9"),        # closing stack measure
    ("fid10-composed-footer-after.png", ".cs-footer-sec"), # footer content width
]


def settle(page) -> None:
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
        for width, name in ((1440, "fid10-composed-after.png"),
                            (2760, "fid10-composed-2760-after.png")):
            page = browser.new_page(viewport={"width": width, "height": 900},
                                    device_scale_factor=1)
            page.goto(COMPOSED.as_uri(), wait_until="load", timeout=30000)
            settle(page)
            page.screenshot(path=str(SHOTS / name), full_page=True)
            print(f"[fid10] {name}")
            if width == 1440:
                for crop_name, sel in CROPS:
                    loc = page.locator(sel).first
                    if not loc.count():
                        print(f"[fid10] MISSING selector for {crop_name}: {sel}")
                        continue
                    loc.scroll_into_view_if_needed()
                    page.wait_for_timeout(250)
                    loc.screenshot(path=str(SHOTS / crop_name), timeout=15000)
                    print(f"[fid10] {crop_name}")
            page.close()
        browser.close()


if __name__ == "__main__":
    main()
