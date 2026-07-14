#!/usr/bin/env python3
"""Bakeoff shots + side-by-side contact sheet (checkpoint D deliverable).

Full-page 1440x900 shots with prefers-reduced-motion (the gallery-lane
convention) into each lane's shots/, then ONE labeled 3-across sheet at
runs/hubspot-v2/brand/compose/style-bakeoff-contact-sheet.png.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
STYLES = ("swiss", "editorial-magazine", "neumorphism")
PAGE = "product-launch"
SHEET = HERE.parent / "style-bakeoff-contact-sheet.png"


def shoot() -> dict[str, Path]:
    from playwright.sync_api import sync_playwright
    out: dict[str, Path] = {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.emulate_media(reduced_motion="reduce")
        for style in STYLES:
            index = HERE.parent / f"style-bakeoff-{style}" / PAGE / "index.html"
            if not index.exists():
                continue
            shots = HERE.parent / f"style-bakeoff-{style}" / "shots"
            shots.mkdir(parents=True, exist_ok=True)
            page.goto(index.resolve().as_uri(), wait_until="networkidle")
            page.wait_for_timeout(400)
            shot = shots / f"{PAGE}.png"
            page.screenshot(path=str(shot), full_page=True)
            out[style] = shot
            print(f"  shot {shot.relative_to(REPO)}")
        browser.close()
    return out


def sheet(shots: dict[str, Path], cell_w: int = 620) -> Path:
    from PIL import Image, ImageDraw
    label_h, pad = 40, 14
    tiles = []
    for style in STYLES:
        if style in shots:
            img = Image.open(shots[style]).convert("RGB")
            scale = cell_w / img.width
            tiles.append((style, img.resize((cell_w, int(img.height * scale)))))
    max_h = max(t.height for _, t in tiles)
    W = len(tiles) * cell_w + (len(tiles) + 1) * pad
    H = max_h + label_h + 2 * pad
    canvas = Image.new("RGB", (W, H), "#1f1f1f")
    draw = ImageDraw.Draw(canvas)
    for i, (style, img) in enumerate(tiles):
        x = pad + i * (cell_w + pad)
        draw.text((x + 2, pad + 6), f"style-library: {style}", fill="#f8f5ee")
        canvas.paste(img, (x, pad + label_h))
    canvas.save(SHEET)
    print(f"  contact sheet -> {SHEET.relative_to(REPO)}")
    return SHEET


if __name__ == "__main__":
    s = shoot()
    if not s:
        print("no pages to shoot", file=sys.stderr)
        sys.exit(1)
    sheet(s)
