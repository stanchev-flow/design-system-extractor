#!/usr/bin/env python3
"""Remediation-pass verification shots (2026-07-10) — spacing + interaction fixes.

  remed-compare-band-width.png   stress pb-compare: the intro now obeys the 1216px
                                 container law (was 1360px) — annotated with the
                                 measured intro width
  remed-split-gutter.png         stress pb-compare closeup: media | ledger panel
                                 seam rides the brand's 48px column rung (was 0px
                                 flush) — annotated with the measured gutter
  remed-chapter-grid.png         stress pb-chapters: N-up card grid gutters ride
                                 the 32px card-grid rung (was 48px split rung) —
                                 annotated with the measured column gap
  remed-card-cta-seam.png        composed homepage workflow cards: the pinned
                                 arrow-link keeps the body→cta rung as a minimum
                                 box-to-box seam on the row's tallest card (was 0px)
  remed-nav-closeup.png          composed homepage top: banner + bar at rest, then
                                 Products hovered — triggers are real <button>s now;
                                 chevrons + measured pill styles intact (no UA
                                 button chrome)

Run:  env -u PLAYWRIGHT_BROWSERS_PATH ./venv/bin/python runs/remote/brand/shots/remed_shoot.py
"""
from pathlib import Path

from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
BRAND = HERE.parent
COMPOSED = BRAND / "compose" / "index.html"
STRESS = BRAND / "compose" / "stress-playbook" / "index.html"


def _label(png: Path, text: str) -> None:
    img = Image.open(png).convert("RGB")
    d = ImageDraw.Draw(img)
    pad, x, y = 6, 12, 10
    box = d.textbbox((x + pad, y + pad), text)
    d.rectangle((x, y, box[2] + pad, box[3] + pad), fill=(20, 20, 24))
    d.text((x + pad, y + pad), text, fill=(255, 255, 255))
    img.save(png)


def _clip(page, selector, pad=14, max_h=1000):
    box = page.locator(selector).first.bounding_box()
    return {"x": 0, "y": max(0, box["y"] - pad), "width": 1440,
            "height": min(max_h, box["height"] + 2 * pad)}


def capture(pw):
    b = pw.chromium.launch()

    # ── stress lane: compare band + chapter grid ─────────────────────────────
    page = b.new_page(viewport={"width": 1440, "height": 1000},
                      reduced_motion="reduce")
    page.goto(STRESS.as_uri(), wait_until="load")
    page.wait_for_timeout(500)

    intro_w = page.evaluate(
        "() => document.querySelector('#sec-5 .cs-split-intro').getBoundingClientRect().width")
    gutter = page.evaluate("""() => {
        const m = document.querySelector('#sec-5 .cs-split-media').getBoundingClientRect();
        const p = document.querySelector('#sec-5 .cs-panel').getBoundingClientRect();
        return p.left - m.right; }""")
    page.locator("#sec-5").scroll_into_view_if_needed()
    page.wait_for_timeout(250)
    shot = HERE / "remed-compare-band-width.png"
    page.screenshot(path=str(shot), clip=_clip(page, "#sec-5", max_h=980))
    _label(shot, f"pb-compare intro width: {intro_w:.0f}px (container law 1216) — was 1360")

    shot = HERE / "remed-split-gutter.png"
    page.screenshot(path=str(shot), clip=_clip(page, "#sec-5 .cs-split--panel", max_h=760))
    _label(shot, f"media->panel column gap: {gutter:.0f}px (column-to-column rung 48) — was 0")

    col_gap = page.evaluate("""() => {
        const mods = document.querySelectorAll('#sec-3 .cs-modules--cols > .cs-module');
        const a = mods[0].getBoundingClientRect(), b = mods[1].getBoundingClientRect();
        return b.left - a.right; }""")
    page.locator("#sec-3").scroll_into_view_if_needed()
    page.wait_for_timeout(250)
    shot = HERE / "remed-chapter-grid.png"
    page.screenshot(path=str(shot), clip=_clip(page, "#sec-3", max_h=980))
    _label(shot, f"chapter grid column gap: {col_gap:.0f}px (grid-gap rung 32) — was 48")
    page.close()

    # ── composed homepage: card CTA seam + nav closeup ───────────────────────
    page = b.new_page(viewport={"width": 1440, "height": 900},
                      reduced_motion="reduce")
    page.goto(COMPOSED.as_uri(), wait_until="load")
    page.wait_for_timeout(500)

    seam = page.evaluate("""() => {
        // the row's TALLEST anatomy card is where auto slack is 0 — the minimum seam.
        let worst = null;
        document.querySelectorAll('.cs-modules--cols .cs-module--anatomy').forEach(m => {
            const link = m.querySelector(':scope > .c-arrow-link:last-child');
            if (!link) return;
            const prev = link.previousElementSibling;
            if (!prev) return;
            const gap = link.getBoundingClientRect().top - prev.getBoundingClientRect().bottom;
            if (worst === null || gap < worst.gap)
                worst = {gap, y: m.getBoundingClientRect().top + scrollY};
        });
        return worst; }""")
    grid = page.locator(".cs-modules--cols").first
    grid.scroll_into_view_if_needed()
    page.wait_for_timeout(250)
    shot = HERE / "remed-card-cta-seam.png"
    page.screenshot(path=str(shot), clip=_clip(page, ".cs-modules--cols", max_h=900))
    _label(shot, f"tightest pinned CTA seam across cards: {seam['gap']:.1f}px "
                 f"(body-to-cta rung 32) — was 0 on the tallest card")

    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(250)
    nav_box = page.locator("nav.cs-nav").first.bounding_box()
    rest_h = nav_box["y"] + nav_box["height"] + 14
    page.screenshot(path=str(HERE / "_remed_nav_rest.png"),
                    clip={"x": 0, "y": 0, "width": 1440, "height": rest_h})
    page.locator(".cs-nav-tab .cs-nav-trigger").first.hover()
    page.wait_for_timeout(450)
    open_h = page.evaluate("""() => {
        const m = document.querySelector('.cs-nav-tab .cs-mega');
        const r = m.getBoundingClientRect();
        return Math.min(860, r.bottom + 16); }""")
    page.screenshot(path=str(HERE / "_remed_nav_open.png"),
                    clip={"x": 0, "y": 0, "width": 1440, "height": open_h})
    page.close()

    rest = Image.open(HERE / "_remed_nav_rest.png").convert("RGB")
    open_ = Image.open(HERE / "_remed_nav_open.png").convert("RGB")
    sheet = Image.new("RGB", (1440, rest.height + open_.height + 8), (225, 225, 225))
    sheet.paste(rest, (0, 0))
    sheet.paste(open_, (0, rest.height + 8))
    sheet.save(HERE / "remed-nav-closeup.png")
    _label(HERE / "remed-nav-closeup.png",
           "nav triggers are <button>s now — rest (top) vs Products hovered (bottom): "
           "chevrons + pill styles intact, no UA button chrome")
    (HERE / "_remed_nav_rest.png").unlink()
    (HERE / "_remed_nav_open.png").unlink()

    b.close()


if __name__ == "__main__":
    with sync_playwright() as pw:
        capture(pw)
    print("remed shots written to", HERE)
