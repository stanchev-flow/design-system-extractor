#!/usr/bin/env python3
"""fid13 verification shots (2026-07-09).

  fid13-workflow-header-lanes.png   composed lane header CENTERED (curation) stacked
                                    over the replica lane header LEFT (measured fact)
  fid13-cards-radius-vs-source.png  per-family radius truth: source vs ours after the
                                    fid13 correction (card 10px, well square-clipped,
                                    accordion 10px, hero panel 10px)

Run:  env -u PLAYWRIGHT_BROWSERS_PATH ./venv/bin/python runs/remote/brand/shots/fid13_shoot.py
"""
from pathlib import Path

from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
BRAND = HERE.parent
REPO = BRAND.parents[2]
COMPOSED = BRAND / "compose" / "index.html"
REPLICA = BRAND / "compose" / "replica" / "index.html"
SOURCE = REPO / "screenshots" / "remote-v2" / "remote-com.html"
TMP = HERE / "_fid13_tmp"
TMP.mkdir(exist_ok=True)


def _shoot(page, path, clip):
    page.screenshot(path=str(path), clip=clip)


def _clip_for(page, selector, *, pad=16, height=None):
    box = page.locator(selector).first.bounding_box()
    y = max(0, box["y"] - pad)
    h = height if height else box["height"] + 2 * pad
    return {"x": 0, "y": y, "width": 1440, "height": h}


def _element_clip(page, selector, pad=10):
    box = page.locator(selector).first.bounding_box()
    return {"x": max(0, box["x"] - pad), "y": max(0, box["y"] - pad),
            "width": box["width"] + 2 * pad, "height": box["height"] + 2 * pad}


def capture(pw):
    b = pw.chromium.launch()
    # composed + replica header bands
    for name, path in (("composed", COMPOSED), ("replica", REPLICA)):
        page = b.new_page(viewport={"width": 1440, "height": 900})
        page.goto(path.as_uri(), wait_until="load")
        page.wait_for_timeout(600)
        sel = '[data-layout="workflow-cards"]'
        page.locator(sel).scroll_into_view_if_needed()
        page.wait_for_timeout(300)
        _shoot(page, TMP / f"header-{name}.png",
               _clip_for(page, f"{sel} .cs-modules-intro", pad=28, height=220))
        if name == "composed":
            _shoot(page, TMP / "ours-card.png",
                   _element_clip(page, f"{sel} .cs-module"))
            page.locator('[data-layout="feature-accordion"]') \
                .scroll_into_view_if_needed()
            page.wait_for_timeout(300)
            _shoot(page, TMP / "ours-acc.png",
                   _element_clip(page, '[data-layout="feature-accordion"] .c-acc-item'))
            page.evaluate("window.scrollTo(0, 0)")
            page.wait_for_timeout(300)
            _shoot(page, TMP / "ours-hero.png",
                   _element_clip(page, ".cs-hero-panel", pad=14))
        page.close()
    # source families (JS-off)
    ctx = b.new_context(viewport={"width": 1440, "height": 900},
                        java_script_enabled=False)
    page = ctx.new_page()
    page.goto(SOURCE.as_uri(), wait_until="load", timeout=60000)
    page.wait_for_timeout(800)
    src = {
        "src-card": '[class*="image-grid-card-module"][class*="__card"]',
        "src-acc": '[class*="accordion-module"][class*="__surface"]',
        "src-hero": '[class*="hero-module"][class*="backgroundWrapper"]',
    }
    for name, sel in src.items():
        loc = page.locator(sel).first
        loc.scroll_into_view_if_needed()
        page.wait_for_timeout(200)
        _shoot(page, TMP / f"{name}.png", _element_clip(page, sel, pad=14))
    page.close()
    b.close()


def _fit(img, width):
    r = width / img.width
    return img.resize((width, int(img.height * r)))


def compose_headers():
    a = Image.open(TMP / "header-composed.png")
    c = Image.open(TMP / "header-replica.png")
    w = 1440
    pad, cap = 12, 34
    h = cap + a.height + pad + cap + c.height + pad
    out = Image.new("RGB", (w, h), "#101014")
    d = ImageDraw.Draw(out)
    y = 0
    for label, img in (("COMPOSED lane — curation follows grammar: header CENTERED "
                        "(data-align-source=curation)", a),
                       ("REPLICA lane — measured fact kept: header LEFT "
                        "(data-align-source=pattern)", c)):
        d.text((14, y + 9), label, fill="#9ae6b4")
        y += cap
        out.paste(img, (0, y))
        y += img.height + pad
    out.save(HERE / "fid13-workflow-header-lanes.png")


def compose_cards():
    cols = [("workflow card plate\nsource 10px | ours 10px, img 0",
             "src-card", "ours-card"),
            ("accordion active surface\nsource 10px | ours 10px",
             "src-acc", "ours-acc"),
            ("hero inset panel\nsource 10px | ours 10px (was 20px)",
             "src-hero", "ours-hero")]
    cw = 460
    cap = 46
    imgs = []
    for _, s, o in cols:
        si = _fit(Image.open(TMP / f"{s}.png"), cw)
        oi = _fit(Image.open(TMP / f"{o}.png"), cw)
        imgs.append((si, oi))
    row1 = max(i[0].height for i in imgs)
    row2 = max(i[1].height for i in imgs)
    pad = 12
    w = (cw + pad) * len(cols) + pad
    h = cap + 24 + row1 + 26 + row2 + pad
    out = Image.new("RGB", (w, h), "#101014")
    d = ImageDraw.Draw(out)
    x = pad
    for (label, _, _), (si, oi) in zip(cols, imgs):
        d.multiline_text((x + 4, 8), label, fill="#9ae6b4")
        d.text((x + 4, cap + 6), "SOURCE (JS-off @1440)", fill="#f6ad55")
        out.paste(si, (x, cap + 24))
        d.text((x + 4, cap + 24 + row1 + 6), "OURS (fid13)", fill="#63b3ed")
        out.paste(oi, (x, cap + 24 + row1 + 26))
        x += cw + pad
    out.save(HERE / "fid13-cards-radius-vs-source.png")


if __name__ == "__main__":
    with sync_playwright() as pw:
        capture(pw)
    compose_headers()
    compose_cards()
    for f in TMP.iterdir():
        f.unlink()
    TMP.rmdir()
    print("fid13 shots written:",
          [p.name for p in HERE.glob("fid13-*.png")])
