#!/usr/bin/env python3
"""fid11 verification shots (relational spacing ladder + header-context grammar).

Emits into runs/remote/brand/shots/:
  fid11-header-split.png       composed accordion section — split-context header (left)
  fid11-header-stack.png       composed partner-proof section — standalone header (centered)
  fid11-spacing-seams.png      hero panel stack with MEASURED seam overlays vs the
                               brand's authored ladder rungs (12/16/32/64px @1440)
  fid11-event-full.png         regenerated event page, full @1440
  fid11-event-pricing.png      event pricing — generated standalone header (brand grammar)
  fid11-event-faq.png          event FAQ — generated standalone header (brand grammar)

Run from repo root:
env -u PLAYWRIGHT_BROWSERS_PATH ./venv/bin/python runs/remote/brand/shots/fid11_shoot.py"""
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[3].parent
BRAND = ROOT / "runs" / "remote" / "brand"
SHOTS = BRAND / "shots"
HOME = BRAND / "compose" / "index.html"
EVENT = BRAND / "compose" / "event-genlaunch" / "index.html"

# overlay: draw a labeled bracket for each vertical seam between two elements
SEAM_JS = """(pairs) => {
  const box = document.createElement('div');
  box.style.cssText = 'position:absolute;inset:0;pointer-events:none;z-index:9999;';
  document.body.appendChild(box);
  const out = [];
  for (const [aSel, bSel, label] of pairs) {
    const a = document.querySelector(aSel), b = document.querySelector(bSel);
    if (!a || !b) { out.push([label, null]); continue; }
    const ra = a.getBoundingClientRect(), rb = b.getBoundingClientRect();
    const top = ra.bottom + window.scrollY, gap = rb.top - ra.bottom;
    const x = Math.max(ra.left, rb.left) + window.scrollX + 6;
    const m = document.createElement('div');
    m.style.cssText = `position:absolute;left:${x}px;top:${top}px;height:${gap}px;` +
      'width:26px;border:2px solid #d92f2f;border-right:none;box-sizing:border-box;' +
      'background:rgba(217,47,47,.12);';
    const t = document.createElement('div');
    t.style.cssText = `position:absolute;left:${x + 32}px;top:${top + gap / 2}px;` +
      'transform:translateY(-50%);font:600 12px monospace;color:#d92f2f;' +
      'background:#fff;padding:1px 6px;white-space:nowrap;border:1px solid #d92f2f;' +
      'z-index:10000;';
    t.textContent = `${label}: ${gap.toFixed(1)}px`;
    box.appendChild(m); box.appendChild(t);
    out.push([label, Math.round(gap * 10) / 10]);
  }
  return out;
}"""


def settle(page) -> None:
    page.evaluate("""async () => {
      const step = window.innerHeight;
      for (let y = 0; y < document.body.scrollHeight; y += step) {
        window.scrollTo(0, y); await new Promise(r => setTimeout(r, 90)); }
      window.scrollTo(0, 0);
    }""")
    page.wait_for_timeout(600)


def shoot(page, sel, name) -> None:
    loc = page.locator(sel).first
    if not loc.count():
        print(f"[fid11] MISSING {sel} for {name}")
        return
    loc.scroll_into_view_if_needed()
    page.wait_for_timeout(250)
    loc.screenshot(path=str(SHOTS / name), timeout=15000)
    print(f"[fid11] {name}")


def main() -> None:
    SHOTS.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900},
                                device_scale_factor=1)

        # ── composed homepage: one header per context ───────────────────────
        page.goto(HOME.as_uri(), wait_until="load", timeout=30000)
        settle(page)
        shoot(page, "#sec-2", "fid11-header-split.png")       # accordion split: left
        shoot(page, "#sec-6", "fid11-header-stack.png")       # partner row: centered
        # seam overlays vs the authored rungs: hero carries heading->body->cta;
        # the accordion header carries eyebrow->heading; modules carry block rhythm.
        seams = page.evaluate(SEAM_JS, [
            ["#sec-0 .c-heading", "#sec-0 .cs-sub", "heading->body (16px rung)"],
            ["#sec-0 .cs-sub", "#sec-0 .cs-hero-actions", "body->cta (32px rung)"],
            ["#sec-2 .c-header .c-eyebrow", "#sec-2 .c-header .c-heading",
             "eyebrow->heading (12px rung)"],
            ["#sec-5 .cs-modules-intro", "#sec-5 .cs-modules",
             "block->block (64px rung)"],
        ])
        print("[fid11] seams:", seams)

        def clip_shot(sel, name, pad=40):
            loc = page.locator(sel).first
            loc.scroll_into_view_if_needed()
            page.wait_for_timeout(250)
            bb = loc.bounding_box()
            page.screenshot(path=str(SHOTS / name),
                            clip={"x": max(bb["x"] - pad, 0),
                                  "y": max(bb["y"] - pad, 0),
                                  "width": bb["width"] + 2 * pad + 160,
                                  "height": bb["height"] + 2 * pad})
            print(f"[fid11] {name}")

        clip_shot("#sec-0 .cs-hero-panel-content", "fid11-spacing-seams.png")
        clip_shot("#sec-2 .c-header", "fid11-spacing-seams-eyebrow.png")

        # ── event page: full + the two generated standalone headers ────────
        page.goto(EVENT.as_uri(), wait_until="load", timeout=30000)
        settle(page)
        page.screenshot(path=str(SHOTS / "fid11-event-full.png"), full_page=True)
        print("[fid11] fid11-event-full.png")
        shoot(page, "#sec-5", "fid11-event-pricing.png")
        shoot(page, "#sec-6", "fid11-event-faq.png")
        # stamp check for the report
        stamps = page.evaluate("""() =>
          [...document.querySelectorAll('[data-align-source]')].map(s =>
            `${s.id}: ${s.dataset.align}/${s.dataset.alignSource}`)""")
        print("[fid11] event align stamps:", stamps)

        page.close()
        browser.close()


if __name__ == "__main__":
    main()
