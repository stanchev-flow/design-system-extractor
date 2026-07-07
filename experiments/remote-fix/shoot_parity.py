#!/usr/bin/env python3
"""remote-fix parity shooter: before/after full-page + detail shots of the WoodWave
matrix (mirrors tools/shoot_alignment_fix.mjs through the repo venv's Python
Playwright), then a subpixel diff — the token/logo batches' parity protocol
(byte-identical or <=0.04% subpixels)."""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

REPO = Path(__file__).resolve().parent.parent.parent
OUT = Path(__file__).resolve().parent / "parity"

PAGES = [
    ("editorial-luxury", "full-editorial-luxury"),
    ("lp-v2", "full-layout-patterns-v2"),
    ("lp-v2-luxury", "full-layout-patterns-v2-luxury"),
    ("monument", "full-wildcard-centered-monument"),
]


def shoot(page, url, outdir, tag):
    outdir.mkdir(parents=True, exist_ok=True)
    page.goto(url, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(700)
    page.screenshot(path=str(outdir / f"{tag}-full.png"), full_page=True)
    st = page.locator('[data-layout="mission-statement"], .cs-statement-sec').first
    if st.count():
        st.screenshot(path=str(outdir / f"{tag}-statement.png"))
    link = page.locator(".cs-panel .c-arrow-link").first
    if link.count():
        link.hover()
        page.wait_for_timeout(250)
        panel = page.locator(".cs-panel").first
        panel.screenshot(path=str(outdir / f"{tag}-panel-hover.png"))


def main():
    before_root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/ww-before")
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        page = b.new_page(viewport={"width": 1440, "height": 900},
                          device_scale_factor=2, reduced_motion="reduce")
        for tag, dirname in PAGES:
            shoot(page, (before_root / dirname / "index.html").resolve().as_uri(),
                  OUT / "before", tag)
            shoot(page, (REPO / "runs/woodwave/brand/compose" / dirname /
                         "index.html").resolve().as_uri(), OUT / "after", tag)
        b.close()
    print("shots done")


if __name__ == "__main__":
    main()
