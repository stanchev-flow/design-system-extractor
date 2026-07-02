#!/usr/bin/env python3
"""Live HubSpot extraction: DOM + computed CSS via Playwright (headless Chromium,
falling back to system Chrome channel). Pulls the precise numeric/string values a
screenshot cannot give: CSS custom-property tokens, computed button system
(primary filled / secondary / text CTA, incl. :hover from stylesheets), type
families + scale, section surfaces, radius/shadow, and real asset URLs + roles.

Writes one comprehensive JSON to the run's assets folder.

Usage:
  ./venv/bin/python tools/extract_hubspot_live.py \
      --url https://www.hubspot.com/ \
      --out runs/hubspot/assets/source-live.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

_EXTRACT_JS = r"""
() => {
  const collapse = (s) => (s || "").replace(/\s+/g, " ").trim();
  const px = (v) => Math.round(parseFloat(v || "0") * 100) / 100;
  const cs = (el) => getComputedStyle(el);
  const isVisible = (el) => {
    if (!el) return false;
    const s = cs(el);
    if (s.display === "none" || s.visibility === "hidden") return false;
    if (parseFloat(s.opacity || "1") === 0) return false;
    const r = el.getBoundingClientRect();
    return r.width > 1 && r.height > 1;
  };

  // ---- 1. CSS custom-property tokens on :root + body --------------------------
  const dumpVars = (el) => {
    const out = {};
    const s = cs(el);
    for (let i = 0; i < s.length; i++) {
      const name = s[i];
      if (name && name.startsWith("--")) {
        const v = s.getPropertyValue(name).trim();
        if (v) out[name] = v;
      }
    }
    return out;
  };
  const rootVars = dumpVars(document.documentElement);
  const bodyVars = dumpVars(document.body);

  // ---- 2. global type ---------------------------------------------------------
  const bodyStyle = cs(document.body);
  const typeRole = (sel) => {
    const el = document.querySelector(sel);
    if (!el || !isVisible(el)) return null;
    const s = cs(el);
    return {
      selector: sel,
      family: s.fontFamily,
      sizePx: px(s.fontSize),
      weight: s.fontWeight,
      lineHeight: s.lineHeight,
      letterSpacing: s.letterSpacing,
      textTransform: s.textTransform,
      color: s.color,
      sample: collapse(el.textContent).slice(0, 80),
    };
  };
  const type = {
    body: {
      family: bodyStyle.fontFamily, sizePx: px(bodyStyle.fontSize),
      color: bodyStyle.color, lineHeight: bodyStyle.lineHeight,
    },
    h1: typeRole("h1"),
    h2: typeRole("h2"),
    h3: typeRole("h3"),
    h4: typeRole("h4"),
  };

  // ---- 3. button system -------------------------------------------------------
  const transparent = (c) =>
    !c || c === "transparent" || c === "rgba(0, 0, 0, 0)" || c === "rgba(0,0,0,0)";
  const hasIcon = (el) => {
    const svg = el.querySelector("svg");
    if (svg && isVisible(svg)) return true;
    const img = el.querySelector("img");
    if (img) { const r = img.getBoundingClientRect(); if (r.width <= 40 && r.height <= 40) return true; }
    return false;
  };
  const btnSig = (b) =>
    [b.bg, b.color, b.borderColor, b.borderWidth, b.borderRadius, b.fontWeight, b.paddingY, b.paddingX, b.fontSizePx].join("|");

  const candidates = Array.from(document.querySelectorAll(
    "a, button, [role='button'], [class*='button' i], [class*='btn' i], [class*='cta' i]"
  )).filter(isVisible).filter((el) => {
    const t = collapse(el.textContent);
    return t.length > 0 && t.length < 40 && /[A-Za-z]{2,}/.test(t);
  });

  const variants = {};   // signature -> representative button
  const orderedButtons = [];
  for (const el of candidates) {
    const s = cs(el);
    const bg = s.backgroundColor;
    const borderW = px(s.borderTopWidth);
    const filled = !transparent(bg);
    const bordered = borderW > 0 && !transparent(s.borderTopColor);
    const cls = (el.getAttribute("class") || "");
    const looksButton = filled || bordered || /button|btn|cta/i.test(cls);
    if (!looksButton) continue;
    const r = el.getBoundingClientRect();
    const b = {
      label: collapse(el.textContent).slice(0, 40),
      tag: el.tagName.toLowerCase(),
      classes: cls.slice(0, 120),
      bg: bg,
      color: s.color,
      borderColor: bordered ? s.borderTopColor : "",
      borderWidth: bordered ? borderW : 0,
      borderRadius: s.borderTopLeftRadius,
      borderRadiusPx: px(s.borderTopLeftRadius),
      paddingY: s.paddingTop,
      paddingX: s.paddingLeft,
      fontFamily: s.fontFamily,
      fontSizePx: px(s.fontSize),
      fontWeight: s.fontWeight,
      textTransform: s.textTransform,
      boxShadow: s.boxShadow === "none" ? "" : s.boxShadow,
      hasIcon: hasIcon(el),
      filled: filled,
      bordered: bordered,
      top: Math.round(r.top + window.scrollY),
    };
    const sig = btnSig(b);
    if (!(sig in variants)) { variants[sig] = b; b.examples = [b.label]; }
    else if (variants[sig].examples.length < 6 && !variants[sig].examples.includes(b.label)) variants[sig].examples.push(b.label);
    orderedButtons.push(b);
  }
  const buttonVariants = Object.values(variants).sort((a, b) => a.top - b.top);

  // ---- 4. button :hover rules from accessible stylesheets ---------------------
  const hoverRules = [];
  try {
    for (const sheet of Array.from(document.styleSheets)) {
      let rules;
      try { rules = sheet.cssRules; } catch (e) { continue; }
      if (!rules) continue;
      for (const rule of Array.from(rules)) {
        const sel = rule.selectorText || "";
        if (!sel) continue;
        if (sel.includes(":hover") && /button|btn|cta/i.test(sel)) {
          const txt = (rule.style && rule.style.cssText) || "";
          if (/background|color|box-shadow|border/i.test(txt)) {
            hoverRules.push({ selector: sel.slice(0, 160), css: txt.slice(0, 240) });
          }
        }
      }
    }
  } catch (e) {}

  // ---- 5. surfaces: top-level sections backgrounds ----------------------------
  const surfaces = [];
  const main = document.querySelector("main") || document.body;
  const tops = Array.from(main.children).filter(isVisible);
  for (const el of tops.slice(0, 40)) {
    const s = cs(el);
    const r = el.getBoundingClientRect();
    surfaces.push({
      tag: el.tagName.toLowerCase(),
      classes: (el.getAttribute("class") || "").slice(0, 80),
      bg: s.backgroundColor,
      backgroundImage: (s.backgroundImage || "none").slice(0, 120),
      color: s.color,
      heightPx: Math.round(r.height),
      top: Math.round(r.top + window.scrollY),
    });
  }

  // ---- 6. cards: radius + shadow sample ---------------------------------------
  const cardSamples = [];
  const cardEls = Array.from(document.querySelectorAll(
    "[class*='card' i], [class*='Card' i]"
  )).filter(isVisible).slice(0, 12);
  for (const el of cardEls) {
    const s = cs(el);
    cardSamples.push({
      classes: (el.getAttribute("class") || "").slice(0, 80),
      bg: s.backgroundColor,
      borderRadius: s.borderTopLeftRadius,
      boxShadow: s.boxShadow === "none" ? "" : s.boxShadow.slice(0, 120),
      border: s.borderTopWidth + " " + s.borderTopStyle + " " + s.borderTopColor,
    });
  }

  // ---- 7. assets: imgs + svg logos + background images ------------------------
  const assets = [];
  const seenSrc = new Set();
  for (const img of Array.from(document.querySelectorAll("img")).filter(isVisible)) {
    const src = img.currentSrc || img.src || "";
    if (!src || seenSrc.has(src)) continue;
    seenSrc.add(src);
    const r = img.getBoundingClientRect();
    assets.push({
      kind: "img",
      src: src,
      alt: (img.getAttribute("alt") || "").slice(0, 120),
      width: Math.round(r.width),
      height: Math.round(r.height),
      top: Math.round(r.top + window.scrollY),
    });
  }
  // background-image assets
  for (const el of Array.from(document.querySelectorAll("*")).filter(isVisible).slice(0, 4000)) {
    const bi = cs(el).backgroundImage || "";
    const m = bi.match(/url\((["']?)(.*?)\1\)/i);
    if (!m) continue;
    let u = m[2].replace(/\\(.)/g, "$1");
    if (/^data:|gradient/i.test(u)) continue;
    if (!/\.(svg|png|webp|jpe?g|avif)(\?|#|$)/i.test(u)) continue;
    if (seenSrc.has(u)) continue;
    seenSrc.add(u);
    const r = el.getBoundingClientRect();
    assets.push({
      kind: "bg",
      src: u,
      alt: (el.getAttribute("aria-label") || "").slice(0, 120),
      width: Math.round(r.width),
      height: Math.round(r.height),
      top: Math.round(r.top + window.scrollY),
    });
  }

  // ---- 8. hero region: heading + bg image + scrim hints -----------------------
  const heroEl = tops[0] || null;
  let hero = null;
  if (heroEl) {
    const s = cs(heroEl);
    const h1 = heroEl.querySelector("h1");
    hero = {
      bg: s.backgroundColor,
      backgroundImage: (s.backgroundImage || "none").slice(0, 200),
      color: s.color,
      headingText: h1 ? collapse(h1.textContent).slice(0, 160) : "",
      headingColor: h1 ? cs(h1).color : "",
    };
  }

  return { rootVars, bodyVars, type, buttonVariants, orderedButtonCount: orderedButtons.length,
           hoverRules: hoverRules.slice(0, 30), surfaces, cardSamples, assets: assets.slice(0, 120), hero };
};
"""


def run(url: str, timeout_ms: int) -> dict:
    from playwright.sync_api import sync_playwright

    last_err = None
    with sync_playwright() as p:
        for launch_kwargs in ({}, {"channel": "chrome"}):
            try:
                tag = launch_kwargs.get("channel", "chromium")
                print(f"[live] launching {tag} for {url}")
                browser = p.chromium.launch(**launch_kwargs)
            except Exception as e:  # noqa: BLE001
                last_err = e
                print(f"[live] launch failed ({launch_kwargs}): {e}")
                continue
            try:
                page = browser.new_page(viewport={"width": 1440, "height": 1024},
                                        user_agent=("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                                                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                                                    "Chrome/124.0 Safari/537.36"))
                page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                try:
                    page.wait_for_load_state("networkidle", timeout=12000)
                except Exception:
                    pass
                # trigger lazy content + scroll the page so lazy imgs resolve
                for y in (0, 2000, 5000, 9000):
                    page.evaluate(f"window.scrollTo(0, {y})")
                    page.wait_for_timeout(400)
                page.evaluate("window.scrollTo(0, 0)")
                page.wait_for_timeout(600)
                data = page.evaluate(_EXTRACT_JS)
                data["source_url"] = url
                data["launch"] = tag
                return data
            finally:
                browser.close()
    raise SystemExit(f"all launch strategies failed: {last_err}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--timeout", type=int, default=45000)
    args = ap.parse_args()

    data = run(args.url, args.timeout)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    bv = data.get("buttonVariants") or []
    print(f"Wrote {args.out}")
    print(f"  root CSS vars: {len(data.get('rootVars') or {})}")
    print(f"  button variants: {len(bv)} (of {data.get('orderedButtonCount')} buttons)")
    for b in bv[:8]:
        print(f"    btn · '{b['label']}' bg={b['bg']} color={b['color']} "
              f"radius={b['borderRadius']} border={b['borderWidth']}px filled={b['filled']}")
    print(f"  hover rules: {len(data.get('hoverRules') or [])}")
    print(f"  surfaces: {len(data.get('surfaces') or [])}  assets: {len(data.get('assets') or [])}")


if __name__ == "__main__":
    main()
