#!/usr/bin/env python3
"""Full-page shot of the new customer-story page + a side-by-side contact sheet
placing it next to HubSpot's real homepage (source) and the 0.957 replica.

Usage (repo root):
  env -u PLAYWRIGHT_BROWSERS_PATH ./venv/bin/python \
      runs/hubspot-v2/brand/compose/customer-story/shoot.py
"""
from __future__ import annotations

from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
SHOTS = HERE / "shots"
SOURCE = REPO / "screenshots" / "hubspot-v2" / "hubspot-fullpage.png"
REPLICA = REPO / "runs" / "hubspot-v2" / "brand" / "compose" / "replica" / "replica-fullpage.png"


def shoot_page() -> tuple[Path, Path]:
    from playwright.sync_api import sync_playwright
    SHOTS.mkdir(parents=True, exist_ok=True)
    out = SHOTS / "customer-story-fullpage.png"
    mobile_out = SHOTS / "customer-story-fullpage-375.png"
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.emulate_media(reduced_motion="reduce")
        page.goto((HERE / "index.html").resolve().as_uri(), wait_until="networkidle")
        page.wait_for_timeout(500)
        page.screenshot(path=str(out), full_page=True)
        mobile = browser.new_page(viewport={"width": 375, "height": 812})
        mobile.emulate_media(reduced_motion="reduce")
        mobile.goto((HERE / "index.html").resolve().as_uri(), wait_until="networkidle")
        mobile.wait_for_timeout(500)
        mobile.screenshot(path=str(mobile_out), full_page=True)
        browser.close()
    print(f"  shot {out.relative_to(REPO)}")
    print(f"  shot {mobile_out.relative_to(REPO)}")
    return out, mobile_out


def contact_sheet(page_shot: Path) -> Path:
    from PIL import Image, ImageDraw
    tiles = [("HubSpot.com — real homepage (source)", SOURCE),
             ("Replica of source (measured, 0.957)", REPLICA),
             ("NEW — customer-story page (generated)", page_shot)]
    tiles = [(lbl, p) for lbl, p in tiles if p.exists()]
    col_w, label_h, pad, crop_h = 460, 40, 16, 1600
    imgs = []
    for lbl, p in tiles:
        im = Image.open(p).convert("RGB")
        scale = col_w / im.width
        im = im.resize((col_w, int(im.height * scale)))
        im = im.crop((0, 0, col_w, min(crop_h, im.height)))
        imgs.append((lbl, im))
    sheet_h = max(im.height for _, im in imgs) + label_h + 2 * pad
    sheet_w = len(imgs) * col_w + (len(imgs) + 1) * pad
    sheet = Image.new("RGB", (sheet_w, sheet_h), "#1f1f1f")
    draw = ImageDraw.Draw(sheet)
    for i, (lbl, im) in enumerate(imgs):
        x = pad + i * (col_w + pad)
        draw.text((x + 2, 12), lbl, fill="#f8f5ee")
        sheet.paste(im, (x, label_h))
    out = SHOTS / "contact-sheet-vs-source.png"
    sheet.save(out)
    print(f"  contact sheet -> {out.relative_to(REPO)}")
    return out


if __name__ == "__main__":
    shot, _mobile = shoot_page()
    contact_sheet(shot)
