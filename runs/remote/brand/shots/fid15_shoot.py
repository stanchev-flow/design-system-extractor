#!/usr/bin/env python3
"""fid15 verification shots (2026-07-10) — nav bar affordances.

  fid15-specbook-chrome.png        spec-book chrome demo bar: trigger chevrons on
                                   menu-owning tabs, Login person icon, language
                                   globe control — plus the language dropdown OPEN
                                   (portal panel, locale items, chevron flipped)
  fid15-composed-nav-closeup.png   composed homepage top: utility banner (text +
                                   arrow cta + close box) over the bar at rest,
                                   then Products hovered (chevron rotated 180°,
                                   mega panel entering)
  fid15-replica-nav-closeup.png    replica lane top band (same chrome facts,
                                   lane parity)

Run:  env -u PLAYWRIGHT_BROWSERS_PATH ./venv/bin/python runs/remote/brand/shots/fid15_shoot.py
"""
from pathlib import Path

from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
BRAND = HERE.parent
PREVIEW = BRAND / "components-preview" / "index.html"
COMPOSED = BRAND / "compose" / "index.html"
REPLICA = BRAND / "compose" / "replica" / "index.html"
TMP = HERE / "_fid15_tmp"
TMP.mkdir(exist_ok=True)


def _clip_to(page, selector, pad=16, min_h=90):
    box = page.locator(selector).first.bounding_box()
    return {"x": 0, "y": max(0, box["y"] - pad), "width": 1440,
            "height": max(min_h, box["height"] + 2 * pad)}


def capture(pw):
    b = pw.chromium.launch()

    # ── spec book: chrome demo bar, rest + language dropdown open ────────────
    page = b.new_page(viewport={"width": 1440, "height": 1100})
    page.goto(PREVIEW.as_uri(), wait_until="load")
    page.wait_for_timeout(600)
    bar = ".cmp-chrome-demo:has(nav.cs-nav)"
    page.locator(bar).first.scroll_into_view_if_needed()
    page.wait_for_timeout(300)
    page.screenshot(path=str(TMP / "spec-rest.png"), clip=_clip_to(page, bar))
    page.evaluate("document.querySelector('.cs-nav-lang').open = true")
    page.wait_for_timeout(350)
    clip = _clip_to(page, bar)
    clip["height"] += 300  # keep the portal panel in frame
    page.screenshot(path=str(TMP / "spec-lang-open.png"), clip=clip)
    page.close()

    # ── composed homepage: banner + bar at rest, then Products hovered ───────
    page = b.new_page(viewport={"width": 1440, "height": 900})
    page.goto(COMPOSED.as_uri(), wait_until="load")
    page.wait_for_timeout(600)
    nav_box = page.locator("nav.cs-nav").first.bounding_box()
    rest_h = nav_box["y"] + nav_box["height"] + 14
    page.screenshot(path=str(TMP / "composed-rest.png"),
                    clip={"x": 0, "y": 0, "width": 1440, "height": rest_h})
    page.hover(".cs-nav-tab >> text=Products")
    page.wait_for_timeout(500)
    page.screenshot(path=str(TMP / "composed-hover.png"),
                    clip={"x": 0, "y": 0, "width": 1440,
                          "height": min(620.0, rest_h + 460)})
    page.close()

    # ── replica lane: same top band ──────────────────────────────────────────
    page = b.new_page(viewport={"width": 1440, "height": 900})
    page.goto(REPLICA.as_uri(), wait_until="load")
    page.wait_for_timeout(600)
    nav_box = page.locator("nav.cs-nav").first.bounding_box()
    page.screenshot(path=str(TMP / "replica-rest.png"),
                    clip={"x": 0, "y": 0, "width": 1440,
                          "height": nav_box["y"] + nav_box["height"] + 14})
    page.close()
    b.close()


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
        capture(pw)
    stack([(TMP / "spec-rest.png",
            "SPEC BOOK chrome demo — trigger chevrons on menu tabs, Login person "
            "icon, EN globe control (harvested glyphs as currentColor masks)"),
           (TMP / "spec-lang-open.png",
            "language dropdown OPEN — chevron flipped (openTransform matrix(-1,0,0,-1)),"
            " measured panel paint + locale items from navbar.utility[].dropdown")],
          HERE / "fid15-specbook-chrome.png")
    stack([(TMP / "composed-rest.png",
            "COMPOSED homepage top — utility banner (text + 'Take the quiz' arrow "
            "cta + measured close box) over the bar: chevrons + Login + EN globe"),
           (TMP / "composed-hover.png",
            "Products hovered — trigger chevron rotated per measured motion, mega "
            "panel entering (same fact family, one hover)")],
          HERE / "fid15-composed-nav-closeup.png")
    stack([(TMP / "replica-rest.png",
            "REPLICA lane top — same banner + bar affordances (AS-46 lane parity: "
            "spec book / composed / replica / event all consume the facts)")],
          HERE / "fid15-replica-nav-closeup.png")
