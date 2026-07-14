#!/usr/bin/env python3
"""fid12: computed re-measurement of the SOURCE workflow-cards section header
alignment (JS-off saved capture @1440, the evidence-canonical setup) + the same
probe over every standalone-stack section header for a class-level sanity check.

Run from repo root:
env -u PLAYWRIGHT_BROWSERS_PATH ./venv/bin/python runs/remote/brand/shots/fid12_measure.py"""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[3].parent
CAPTURE = ROOT / "screenshots" / "remote-v2" / "remote-com.html"

PROBE = """() => {
  const out = [];
  const secs = [...document.querySelectorAll('section')];
  for (let i = 0; i < secs.length; i++) {
    const sec = secs[i];
    const r = sec.getBoundingClientRect();
    if (r.width < 600 || r.height < 120) continue;
    // the source's shared header module: .base-header header (fallback: first
    // h1/h2 wrapper inside the section)
    const h = sec.querySelector('header') ||
              sec.querySelector('h1,h2')?.parentElement;
    if (!h) continue;
    const hr = h.getBoundingClientRect();
    const cs = getComputedStyle(h);
    const heading = sec.querySelector('h1,h2');
    const hd = heading ? heading.getBoundingClientRect() : null;
    const leftGap = hr.left - r.left;
    const rightGap = r.right - hr.right;
    out.push({
      i, heading: (heading?.textContent || '').trim().slice(0, 60),
      secW: Math.round(r.width), hdrW: Math.round(hr.width),
      leftGap: Math.round(leftGap), rightGap: Math.round(rightGap),
      blockCentered: Math.abs(leftGap - rightGap) < 8,
      textAlign: cs.textAlign, alignItems: cs.alignItems,
      display: cs.display, marginInline: cs.marginLeft + '/' + cs.marginRight,
      headingLeftInHdr: hd ? Math.round(hd.left - hr.left) : null,
    });
  }
  return out;
}"""


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1440, "height": 900},
                                  java_script_enabled=False)
        page = ctx.new_page()
        page.goto(CAPTURE.as_uri(), wait_until="load", timeout=60000)
        page.wait_for_timeout(800)
        rows = page.evaluate(PROBE)
        for r in rows:
            print(json.dumps(r))
        browser.close()


if __name__ == "__main__":
    main()
