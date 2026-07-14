#!/usr/bin/env python3
"""fid14 verification shots (2026-07-09).

  fid14-grid-equalize-vs-source.png  composed workflow grid (cards with UNEQUAL
                                     natural content rendering EQUAL height, Learn-more
                                     links pinned to the card bottoms) stacked over the
                                     source grid (its own equalized 536px row)
  fid14-bento-pricing-equalize.png   event page: bento mosaic 3-cell row + pricing
                                     tier row after regen (equal heights, pinned
                                     actions per the brand grammar)

Run:  env -u PLAYWRIGHT_BROWSERS_PATH ./venv/bin/python runs/remote/brand/shots/fid14_shoot.py
"""
from pathlib import Path

from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
BRAND = HERE.parent
REPO = BRAND.parents[2]
COMPOSED = BRAND / "compose" / "index.html"
EVENT = BRAND / "compose" / "event-genlaunch" / "index.html"
SOURCE = REPO / "screenshots" / "remote-v2" / "remote-com.html"
TMP = HERE / "_fid14_tmp"
TMP.mkdir(exist_ok=True)


def _band_clip(page, selector, pad=20):
    box = page.locator(selector).first.bounding_box()
    return {"x": 0, "y": max(0, box["y"] - pad), "width": 1440,
            "height": box["height"] + 2 * pad}


def capture(pw):
    b = pw.chromium.launch()

    # composed workflow grid (unequal content, equalized render)
    page = b.new_page(viewport={"width": 1440, "height": 1200})
    page.goto(COMPOSED.as_uri(), wait_until="load")
    page.wait_for_timeout(600)
    sel = '[data-layout="workflow-cards"] .cs-modules'
    page.locator(sel).scroll_into_view_if_needed()
    page.wait_for_timeout(300)
    page.screenshot(path=str(TMP / "ours-grid.png"), clip=_band_clip(page, sel))
    heights = page.evaluate(
        """() => [...document.querySelectorAll('[data-layout="workflow-cards"] .cs-module')]
                 .map(c => Math.round(c.getBoundingClientRect().height))""")
    page.close()

    # event bento + pricing bands
    page = b.new_page(viewport={"width": 1440, "height": 1200})
    page.goto(EVENT.as_uri(), wait_until="load")
    page.wait_for_timeout(600)
    for name, s in (("bento", '[data-layout="event-bento"] .cs-bento'),
                    ("pricing", ".cs-tiers")):
        page.locator(s).first.scroll_into_view_if_needed()
        page.wait_for_timeout(300)
        page.screenshot(path=str(TMP / f"event-{name}.png"), clip=_band_clip(page, s))
    page.close()

    # source workflow grid (JS-off)
    ctx = b.new_context(viewport={"width": 1440, "height": 1200},
                        java_script_enabled=False)
    page = ctx.new_page()
    page.goto(SOURCE.as_uri(), wait_until="load", timeout=60000)
    page.wait_for_timeout(800)
    src_sel = '[class*="image-grid-card-module"][class*="__card"]'
    page.locator(src_sel).first.scroll_into_view_if_needed()
    page.wait_for_timeout(300)
    box = page.locator(src_sel).first.bounding_box()
    page.screenshot(path=str(TMP / "src-grid.png"),
                    clip={"x": 0, "y": max(0, box["y"] - 40), "width": 1440,
                          "height": box["height"] + 80})
    ctx.close()
    b.close()
    return heights


def _label(img, text):
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, img.width, 34], fill=(10, 16, 40))
    d.text((14, 9), text, fill=(255, 255, 255))
    return img


def stack(paths_labels, out, width=1440):
    imgs = []
    for p, lab in paths_labels:
        im = Image.open(p).convert("RGB")
        if im.width != width:
            im = im.resize((width, int(im.height * width / im.width)))
        imgs.append(_label(im, lab))
    total = sum(i.height for i in imgs) + 8 * (len(imgs) - 1)
    sheet = Image.new("RGB", (width, total), (225, 225, 225))
    y = 0
    for im in imgs:
        sheet.paste(im, (0, y))
        y += im.height + 8
    sheet.save(out)
    print("wrote", out)


if __name__ == "__main__":
    with sync_playwright() as pw:
        hts = capture(pw)
    stack([(TMP / "ours-grid.png",
            f"COMPOSED workflow grid — unequal content, EQUAL card heights {hts} "
            "+ pinned Learn-more links (gridEqualize: stretch/body/pinned)"),
           (TMP / "src-grid.png",
            "SOURCE (JS-off @1440) — its own equalized row (536px each; "
            "body flex-grow absorbs the slack)")],
          HERE / "fid14-grid-equalize-vs-source.png")
    stack([(TMP / "event-bento.png",
            "EVENT bento mosaic — 3-cell row equalized per the brand grammar"),
           (TMP / "event-pricing.png",
            "EVENT pricing tiers — 578px peers, buttons pinned at a constant "
            "bottom offset")],
          HERE / "fid14-bento-pricing-equalize.png")
