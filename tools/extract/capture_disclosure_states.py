#!/usr/bin/env python3
"""capture_disclosure_states.py — per-item INTERACTION capture for disclosure
sections (accordion / tabs), brand-agnostic.

A disclosure section renders N trigger items where activating an item (a) reveals
that item's body copy and (b) often swaps a shared MEDIA region (the per-item
product-UI collage). A static capture only ever sees the initially-active item, so
its evidence carries one body and one media state — this tool activates EACH item
in turn (Playwright, live page or saved HTML) and harvests, per item:

  - the trigger label + the revealed body copy (verbatim),
  - the associated media region's rendered artwork (element screenshot, the same
    harvested-crop discipline as the chrome mega-panel pass),
  - a full-section screenshot of the active state (evidence crop for grounding).

DETECTION IS SEMANTIC, NEVER BRAND-NAMED: triggers are visible `[aria-expanded]`
buttons inside the section that anchors the --section-text heading; the media
region is the largest rendered img/svg/picture/video block inside the section but
OUTSIDE the trigger column. No class names, no content keywords.

Outputs (into --out-dir):
  disclosure-<slug>.json                     harvest manifest (items, boxes, files)
  disclosure-item-<i>-<label>.png            full-section active-state crop
  disclosure-media-<i>-<label>.png           the media region's artwork, per item

Usage:
    ./venv/bin/python tools/extract/capture_disclosure_states.py \
        --url https://example.com --section-text "Heading anchor text" \
        --out-dir runs/<brand>/brand/evidence/crops [--viewport 1440x900] [--scale 2]
"""
from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

_FIND_SECTION_JS = """
(anchor) => {
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let node = null;
  while (walker.nextNode()) {
    const t = (walker.currentNode.textContent || "").trim();
    if (t && t.includes(anchor)) { node = walker.currentNode.parentElement; break; }
  }
  if (!node) return null;
  let sec = node;
  while (sec && sec !== document.body) {
    if (sec.tagName === "SECTION") break;
    sec = sec.parentElement;
  }
  if (!sec || sec === document.body) {
    sec = node.closest("section, main > div, [class*='section' i]") || node.parentElement;
  }
  sec.setAttribute("data-disclosure-capture-root", "1");
  return true;
}
"""

_LIST_TRIGGERS_JS = """
() => {
  const root = document.querySelector("[data-disclosure-capture-root]");
  if (!root) return [];
  const vis = (el) => {
    const r = el.getBoundingClientRect();
    const s = getComputedStyle(el);
    return r.width > 1 && r.height > 1 && s.visibility !== "hidden" && s.display !== "none";
  };
  const trigs = Array.from(root.querySelectorAll("button[aria-expanded], [role='button'][aria-expanded]"))
    .filter(vis);
  return trigs.map((t, i) => {
    t.setAttribute("data-disclosure-trigger", String(i));
    return {
      index: i,
      label: (t.textContent || "").replace(/\\s+/g, " ").trim().slice(0, 120),
      expanded: t.getAttribute("aria-expanded") === "true",
      controls: t.getAttribute("aria-controls") || "",
    };
  });
}
"""

# body copy of the item's revealed region: prefer the aria-controls panel; its
# longest paragraph-ish text block is the body (trigger label text excluded).
_HARVEST_BODY_JS = """
(args) => {
  const [i] = args;
  const t = document.querySelector(`[data-disclosure-trigger="${i}"]`);
  if (!t) return null;
  const id = t.getAttribute("aria-controls");
  let panel = id ? document.getElementById(id) : null;
  if (!panel) {
    // fallback: next element sibling chain from the trigger's header wrapper
    let n = t.closest("h1,h2,h3,h4,div,header") || t;
    panel = n.nextElementSibling;
  }
  if (!panel) return null;
  const collapse = (s) => (s || "").replace(/\\s+/g, " ").trim();
  const paras = Array.from(panel.querySelectorAll("p"))
    .map((p) => collapse(p.textContent)).filter(Boolean);
  if (paras.length) return paras.join("\\n\\n").slice(0, 1200);
  const whole = collapse(panel.textContent);
  return whole ? whole.slice(0, 1200) : null;
}
"""

# the shared media region: the largest visible rendered-art block (img / svg /
# picture / video / canvas) inside the section but OUTSIDE any trigger's list
# column (an element containing every trigger). Marked for element-screenshot.
_MARK_MEDIA_JS = """
() => {
  const root = document.querySelector("[data-disclosure-capture-root]");
  if (!root) return null;
  const trigs = Array.from(root.querySelectorAll("[data-disclosure-trigger]"));
  if (!trigs.length) return null;
  let list = trigs[0];
  while (list && list !== root && !trigs.every((t) => list.contains(t))) {
    list = list.parentElement;
  }
  const vis = (el) => {
    const r = el.getBoundingClientRect();
    const s = getComputedStyle(el);
    return r.width > 40 && r.height > 40 && s.visibility !== "hidden" &&
           s.display !== "none" && parseFloat(s.opacity || "1") > 0.05;
  };
  let best = null, bestArea = 0;
  for (const el of Array.from(root.querySelectorAll("img, svg, picture, video, canvas"))) {
    if (list && list.contains(el)) continue;
    if (!vis(el)) continue;
    const r = el.getBoundingClientRect();
    const area = r.width * r.height;
    if (area > bestArea) { best = el; bestArea = area; }
  }
  if (!best) return null;
  // screenshot the media WRAPPER (the collage block may layer several siblings):
  // walk up while the parent stays media-dominated (not the whole split row).
  let target = best;
  for (let i = 0; i < 3 && target.parentElement && target.parentElement !== root; i++) {
    const p = target.parentElement;
    const pr = p.getBoundingClientRect();
    const tr = target.getBoundingClientRect();
    if (list && p.contains(list)) break;
    if (pr.width <= tr.width * 1.3 && pr.height <= tr.height * 1.35) target = p;
    else break;
  }
  document.querySelectorAll("[data-disclosure-media]").forEach((n) =>
    n.removeAttribute("data-disclosure-media"));
  target.setAttribute("data-disclosure-media", "1");
  const r = target.getBoundingClientRect();
  return { w: Math.round(r.width), h: Math.round(r.height) };
}
"""

_HIDE_OVERLAYS_JS = """
() => {
  const vw = window.innerWidth, vh = window.innerHeight;
  for (const el of Array.from(document.querySelectorAll("body *")).slice(0, 5000)) {
    const s = getComputedStyle(el);
    if (s.position !== "fixed" && s.position !== "sticky") continue;
    const t = (el.textContent || "").toLowerCase();
    const r = el.getBoundingClientRect();
    const kill = () => el.style.setProperty("display", "none", "important");
    // consent banners/backdrops, chat bubbles, and ANY translucent full-viewport wash
    if (/cookie|consent|privacy|gdpr/.test(t) && r.height > 24) { kill(); continue; }
    if (/chat|intercom|drift|zendesk|help|widget/.test(String(el.className || "")) && r.width < 480) { kill(); continue; }
    if (r.width >= vw * 0.9 && r.height >= vh * 0.9) {
      const bg = s.backgroundColor || "";
      const m = bg.match(/rgba?\\(([^)]+)\\)/);
      const a = m && m[1].split(",")[3] !== undefined ? parseFloat(m[1].split(",")[3]) : 1;
      if (m && a > 0.01 && a < 0.98) { kill(); continue; }  // dim backdrop
    }
    // page chrome bars overlap element screenshots (sticky nav composites on top
    // of the media crop) — the capture wants the SECTION's own pixels only.
    if (r.top <= 2 && r.width >= vw * 0.9 && r.height < vh * 0.4) kill();
  }
}
"""


def slug(s: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")
    return s[:48] or "item"


def main() -> int:
    ap = argparse.ArgumentParser(description="Per-item disclosure interaction capture")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--url", help="live page URL")
    src.add_argument("--html", type=Path, help="saved .html page")
    ap.add_argument("--section-text", required=True,
                    help="anchor text that identifies the disclosure section (its heading)")
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--prefix", default="disclosure",
                    help="output filename prefix (default: disclosure)")
    ap.add_argument("--viewport", default="1440x900")
    ap.add_argument("--scale", type=int, default=2, help="deviceScaleFactor for crisp art")
    ap.add_argument("--settle-ms", type=int, default=900,
                    help="wait after each activation (open animation + media swap)")
    ap.add_argument("--timeout", type=int, default=45000)
    args = ap.parse_args()

    from playwright.sync_api import sync_playwright

    w, h = (int(x) for x in args.viewport.split("x"))
    args.out_dir.mkdir(parents=True, exist_ok=True)
    manifest: dict = {"source": args.url or str(args.html), "sectionText": args.section_text,
                      "items": []}

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": w, "height": h},
                                device_scale_factor=args.scale)
        target = args.url or Path(args.html).resolve().as_uri()
        page.goto(target, timeout=args.timeout, wait_until="domcontentloaded")
        page.wait_for_timeout(1500)
        page.evaluate(_HIDE_OVERLAYS_JS)
        if not page.evaluate(_FIND_SECTION_JS, args.section_text):
            raise SystemExit(f"section anchor text not found: {args.section_text!r}")
        section = page.locator("[data-disclosure-capture-root]")
        section.scroll_into_view_if_needed()
        page.wait_for_timeout(600)
        triggers = page.evaluate(_LIST_TRIGGERS_JS)
        if not triggers:
            raise SystemExit("no [aria-expanded] triggers found in the section")
        print(f"  disclosure triggers: {len(triggers)}")
        for t in triggers:
            i = t["index"]
            name = slug(t["label"])
            trig = page.locator(f'[data-disclosure-trigger="{i}"]')
            if not t["expanded"]:
                try:
                    trig.click(timeout=4000)
                except Exception:
                    trig.evaluate("el => el.click()")
            page.wait_for_timeout(args.settle_ms)
            body = page.evaluate(_HARVEST_BODY_JS, [i])
            media_box = page.evaluate(_MARK_MEDIA_JS)
            section.scroll_into_view_if_needed()
            page.evaluate(_HIDE_OVERLAYS_JS)
            page.wait_for_timeout(250)
            sec_shot = args.out_dir / f"{args.prefix}-item-{i}-{name}.png"
            section.screenshot(path=str(sec_shot), animations="disabled")
            media_file = None
            if media_box:
                media_file = args.out_dir / f"{args.prefix}-media-{i}-{name}.png"
                page.locator("[data-disclosure-media]").screenshot(
                    path=str(media_file), animations="disabled")
            manifest["items"].append({
                "index": i, "label": t["label"], "body": body,
                "mediaBox": media_box,
                "sectionShot": sec_shot.name,
                "mediaShot": media_file.name if media_file else None,
            })
            print(f"  [{i}] {t['label'][:40]!r} body={'yes' if body else 'NO'} "
                  f"media={media_box or 'NO'}")
        browser.close()

    out = args.out_dir / f"{args.prefix}-{slug(args.section_text)}.json"
    out.write_text(json.dumps(manifest, indent=1, ensure_ascii=False) + "\n")
    print(f"[done] manifest -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
