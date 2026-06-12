"""Browser-based nav/footer extraction using Playwright + computed styles.

Unlike the static-HTML heuristic (chrome_extractor.py), this launches a real
headless Chromium, lets the page's JS run, and reads COMPUTED styles + actual
visibility. That lets it:
  - keep only top-level VISIBLE nav items (drops hidden mega-menu leaves)
  - use visible text, not sr-only/aria labels ("Open menu for" noise gone)
  - capture real link colors, fonts, button fill/border/radius + whether
    buttons actually carry an icon (so we don't invent arrows)
  - resolve the real logo (inline SVG or <img> src)
  - group footer columns by their visible headings

Emits a richer `source_chrome.v2` contract consumed by chrome_codegen.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CHROME_SCHEMA_V2 = "source_chrome.v2"

# In-page extraction script. Returns a plain JSON-able object.
_EXTRACT_JS = r"""
() => {
  const collapse = (s) => (s || "").replace(/\s+/g, " ").trim();

  const isHidden = (el) => {
    if (!el) return true;
    const s = getComputedStyle(el);
    if (s.display === "none" || s.visibility === "hidden") return true;
    if (parseFloat(s.opacity || "1") === 0) return true;
    return false;
  };

  const isVisible = (el) => {
    if (isHidden(el)) return false;
    const r = el.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) return false;
    return el.offsetParent !== null || getComputedStyle(el).position === "fixed";
  };

  // Visible text only: skip sr-only / clipped / hidden descendants.
  const visibleText = (el) => {
    let out = "";
    for (const node of el.childNodes) {
      if (node.nodeType === 3) {
        out += node.textContent;
      } else if (node.nodeType === 1) {
        const s = getComputedStyle(node);
        if (s.display === "none" || s.visibility === "hidden") continue;
        if (parseFloat(s.opacity || "1") === 0) continue;
        const r = node.getBoundingClientRect();
        if (r.width <= 1 || r.height <= 1) continue;
        const clip = s.clip || "";
        if (s.position === "absolute" && (clip.indexOf("rect(0") === 0 || s.width === "1px")) continue;
        out += visibleText(node);
      }
    }
    return out;
  };

  const label = (el) => collapse(visibleText(el)).slice(0, 120);
  const px = (v) => Math.round(parseFloat(v || "0"));
  const origin = location.origin;
  const outer_or = (svg) => { const o = svg.outerHTML || ""; return o.length <= 12000 ? o : ""; };
  const SOCIAL = /facebook|twitter|linkedin|youtube|instagram|tiktok|github|x\.com|threads|glassdoor/i;

  // Resolved background-image URL (getComputedStyle returns it absolute + safely
  // percent-encoded, so we avoid the broken raw-CSS url(... \(1\) ...) form).
  const bgImageUrl = (el) => {
    const bi = getComputedStyle(el).backgroundImage || "";
    if (!bi || bi === "none") return "";
    const m = bi.match(/url\((["']?)(.*?)\1\)/i);
    if (!m) return "";
    let u = m[2].replace(/\\(.)/g, "$1");       // unescape CSS escapes
    if (/^data:|gradient/i.test(u)) return "";   // skip data-URIs / gradients
    if (!/\.(svg|png|webp|jpe?g|avif|gif)(\?|#|$)/i.test(u)) return "";
    return u;
  };

  // Score a logo candidate from a "haystack" (href + class/id/alt/aria + src).
  const logoScore = (href, hay, w, h, rect) => {
    let s = 0;
    hay = (hay || "").toLowerCase();
    if (/logo|wordmark|brandmark|brand\b/.test(hay)) s += 4;
    if (SOCIAL.test(hay)) s -= 6;
    if (href === "/" || href === origin || href === origin + "/" || href === "") s += 3;
    if (/\/(content|blog|topic|news|press|career|product|platform|resource|demo|pricing|sign)/.test(href)) s -= 3;
    if (w && h) { const ar = w / h; if (ar >= 1.6 && ar <= 9) s += 2; else if (ar < 1.1) s -= 1; }
    if (rect && rect.left < 240) s += 1;
    return s;
  };

  // Pick the best logo within a scope, looking at inline <svg>, <img>, AND
  // CSS background-image marks (Webflow-style a.nav-logo). Reject weak guesses.
  const pickLogo = (scope) => {
    let best = null, bestA = null, bestScore = -1e9;
    const consider = new Set();
    scope.querySelectorAll("a[href], [class*='logo' i], [class*='brand' i]").forEach((e) => consider.add(e));
    for (const el of consider) {
      if (!isVisible(el)) continue;
      const a = el.closest("a") || el;
      const href = (a.getAttribute && a.getAttribute("href")) || "";
      const baseHay = href + " " + (el.getAttribute("class") || "") + " " + (el.getAttribute("id") || "") +
        " " + (el.getAttribute("aria-label") || "") + " " + ((a.getAttribute && a.getAttribute("aria-label")) || "");
      const rect = a.getBoundingClientRect ? a.getBoundingClientRect() : el.getBoundingClientRect();
      const cands = [];

      const svg = el.querySelector("svg");
      if (svg && isVisible(svg)) {
        const w = px(getComputedStyle(svg).width), h = px(getComputedStyle(svg).height);
        cands.push({ score: logoScore(href, baseHay, w, h, rect) + 1, logo: {
          kind: "svg", href: href || "/", svg: outer_or(svg), alt: (a.getAttribute && a.getAttribute("aria-label")) || "", width: w, height: h } });
      }
      const img = el.querySelector("img");
      if (img && isVisible(img)) {
        const w = px(getComputedStyle(img).width), h = px(getComputedStyle(img).height);
        const src = img.currentSrc || img.src || "";
        cands.push({ score: logoScore(href, baseHay + " " + src, w, h, rect), logo: {
          kind: "img", href: href || "/", src: src, alt: img.getAttribute("alt") || "", width: w, height: h } });
      }
      const bg = bgImageUrl(el);
      if (bg) {
        const w = px(getComputedStyle(el).width), h = px(getComputedStyle(el).height);
        cands.push({ score: logoScore(href, baseHay + " " + bg, w, h, rect) + 1, logo: {
          kind: "img", href: href || "/", src: bg, alt: (el.getAttribute("aria-label") || "").trim(), width: w, height: h } });
      }

      for (const c of cands) {
        if (c.score > bestScore) { bestScore = c.score; best = c.logo; bestA = a; }
      }
    }
    if (bestScore < 1) return { logo: null, anchor: null };
    return { logo: best, anchor: bestA };
  };

  const transparent = (c) =>
    !c || c === "transparent" || c === "rgba(0, 0, 0, 0)" || c === "rgba(0,0,0,0)";

  const hasIconChild = (el) => {
    const svg = el.querySelector("svg");
    if (svg && isVisible(svg)) return true;
    const img = el.querySelector("img");
    if (img && isVisible(img)) {
      const r = img.getBoundingClientRect();
      if (r.width <= 40 && r.height <= 40) return true; // small icon, not a logo
    }
    // ::after content arrows are hard to read; skip.
    return false;
  };

  // ---- pick the primary header / nav -------------------------------------
  const headerCandidates = [
    document.querySelector("header[role='banner']"),
    document.querySelector("header"),
    document.querySelector("[class*='navbar' i]"),
    document.querySelector("nav"),
  ].filter(Boolean);
  let header = null;
  for (const c of headerCandidates) {
    const r = c.getBoundingClientRect();
    if (isVisible(c) && r.top < 220 && r.height >= 32 && r.height < 240) {
      header = c;
      break;
    }
  }
  if (!header) header = headerCandidates[0] || null;

  const result = { nav: { found: false }, footer: { found: false }, type: {} };

  // ---- global type ----
  const bodyStyle = getComputedStyle(document.body);
  const sampleLink = document.querySelector("a[href]");
  const h1 = document.querySelector("h1, h2");
  result.type = {
    bodyFont: bodyStyle.fontFamily,
    bodySize: px(bodyStyle.fontSize),
    bodyColor: bodyStyle.color,
    headingFont: h1 ? getComputedStyle(h1).fontFamily : bodyStyle.fontFamily,
    linkColor: sampleLink ? getComputedStyle(sampleLink).color : bodyStyle.color,
  };

  // ---- nav ----
  if (header) {
    const hs = getComputedStyle(header);
    const hr = header.getBoundingClientRect();
    const sticky = hs.position === "fixed" || hs.position === "sticky";

    // logo: score header img/svg anchors; prefer logo-named, root-href,
    // wordmark-aspect, left-most marks over promo/announcement imagery.
    const _navLogo = pickLogo(header);
    const logo = _navLogo.logo;
    const logoAnchor = _navLogo.anchor;

    // Junk labels: icon-button aria text, skip-links, logo home links, toggles.
    const JUNK = /\b(toggle|open menu|close menu|close|skip to|search form|home link|hamburger|menu button|open search|breadcrumb)\b/i;

    // candidate clickables that live INSIDE the header band (excludes dropdown
    // panels that render below the header on hover/focus).
    const inHeaderBand = (el) => {
      const r = el.getBoundingClientRect();
      return r.top >= hr.top - 6 && r.bottom <= hr.bottom + 6 && r.height > 0;
    };
    const clickables = Array.from(header.querySelectorAll("a[href], button"))
      .filter((el) => isVisible(el) && inHeaderBand(el));

    const navLinks = [];
    const ctas = [];
    const seen = new Set();

    for (const el of clickables) {
      if (logoAnchor && (el === logoAnchor || logoAnchor.contains(el) || el.contains(logoAnchor))) continue;
      const text = label(el);
      if (!text) continue;
      if (text.length > 60) continue;
      if (JUNK.test(text)) continue;
      // icon-only control (search/hamburger): has svg/img but no real word text
      if (el.querySelector("svg, img") && !/[A-Za-z]{2,}/.test(text)) continue;
      const s = getComputedStyle(el);
      const href = el.tagName === "A" ? (el.getAttribute("href") || "") : "";
      const bg = s.backgroundColor;
      const borderW = px(s.borderTopWidth) + px(s.borderBottomWidth) + px(s.borderLeftWidth) + px(s.borderRightWidth);
      const filled = !transparent(bg) && bg !== hs.backgroundColor;
      const bordered = borderW > 0 && !transparent(s.borderTopColor);
      const buttonish = el.tagName === "BUTTON" ? (filled || bordered) : (filled || bordered);
      const key = text.toLowerCase();
      if (seen.has(key)) continue;
      seen.add(key);

      if (buttonish) {
        ctas.push({
          label: text,
          href: href,
          bg: bg,
          color: s.color,
          borderColor: bordered ? s.borderTopColor : "",
          borderWidth: bordered ? px(s.borderTopWidth) : 0,
          borderRadius: px(s.borderTopLeftRadius),
          fontWeight: s.fontWeight,
          hasIcon: hasIconChild(el),
          filled: filled,
        });
      } else {
        navLinks.push({
          label: text,
          href: href,
          color: s.color,
          fontFamily: s.fontFamily,
          fontSize: px(s.fontSize),
          fontWeight: s.fontWeight,
        });
      }
    }

    result.nav = {
      found: true,
      sticky: sticky,
      bg: hs.backgroundColor,
      color: bodyStyle.color,
      height: px(hs.height) || Math.round(hr.height),
      logo: logo,
      links: navLinks.slice(0, 12),
      ctas: ctas.slice(0, 4),
      anyButtonHasIcon: ctas.some((c) => c.hasIcon),
    };
  }

  // ---- footer ----
  let footers = Array.from(document.querySelectorAll("footer")).filter(isVisible);
  if (!footers.length) {
    // Many templates (e.g. Webflow) use div.footer-* instead of a semantic
    // <footer>. Fall back to the outermost visible class*="footer" container
    // closest to the bottom of the document.
    const cands = Array.from(document.querySelectorAll("[class*='footer' i]")).filter(isVisible);
    const outer = cands.filter((el) => !cands.some((o) => o !== el && o.contains(el)));
    outer.sort(
      (a, b) =>
        a.getBoundingClientRect().top + window.scrollY -
        (b.getBoundingClientRect().top + window.scrollY)
    );
    footers = outer.length ? [outer[outer.length - 1]] : [];
  }
  const footer = footers.length ? footers[footers.length - 1] : null;
  if (footer) {
    const fs = getComputedStyle(footer);
    const flogo = pickLogo(footer).logo;

    // columns: group visible links by nearest preceding heading-ish element.
    const headingEls = Array.from(
      footer.querySelectorAll("h2, h3, h4, h5, h6, [class*='title' i], [class*='heading' i]")
    ).filter(isVisible);

    const columns = [];
    if (headingEls.length >= 2) {
      for (let i = 0; i < headingEls.length; i++) {
        const head = headingEls[i];
        const headLabel = label(head);
        // collect links that come after this heading but before the next heading
        const next = headingEls[i + 1] || null;
        const container = head.parentElement || footer;
        const links = Array.from(container.querySelectorAll("a[href]")).filter((a) => {
          if (!isVisible(a)) return false;
          const pos = head.compareDocumentPosition(a);
          const afterHead = !!(pos & Node.DOCUMENT_POSITION_FOLLOWING);
          if (!afterHead) return false;
          if (next) {
            const pos2 = next.compareDocumentPosition(a);
            const beforeNext = !!(pos2 & Node.DOCUMENT_POSITION_PRECEDING);
            if (!beforeNext) return false;
          }
          return true;
        });
        const items = [];
        const seenL = new Set();
        for (const a of links) {
          const t = label(a);
          if (!t) continue;
          const k = t.toLowerCase();
          if (seenL.has(k)) continue;
          seenL.add(k);
          items.push({ label: t, href: a.getAttribute("href") || "#", color: getComputedStyle(a).color });
        }
        if (items.length) columns.push({ heading: headLabel, links: items.slice(0, 12) });
      }
    }
    if (!columns.length) {
      const items = [];
      const seenL = new Set();
      for (const a of Array.from(footer.querySelectorAll("a[href]")).filter(isVisible)) {
        const t = label(a);
        if (!t) continue;
        const k = t.toLowerCase();
        if (seenL.has(k)) continue;
        seenL.add(k);
        items.push({ label: t, href: a.getAttribute("href") || "#", color: getComputedStyle(a).color });
      }
      const chunk = Math.max(4, Math.ceil(items.length / 4));
      for (let i = 0; i < items.length; i += chunk) {
        columns.push({ heading: "", links: items.slice(i, i + chunk) });
      }
    }

    result.footer = {
      found: true,
      bg: fs.backgroundColor,
      color: fs.color,
      logo: flogo,
      columns: columns.slice(0, 6),
    };
  }

  return result;
};
"""


def extract_chrome_with_browser(
    url: str,
    *,
    timeout_ms: int = 30000,
    log=print,
) -> dict[str, Any]:
    """Launch headless Chromium, run the page, and extract nav/footer with styles."""
    from playwright.sync_api import sync_playwright

    log(f"[chrome-browser] launching headless chromium for {url}")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page(viewport={"width": 1440, "height": 1024})
            page.goto(url, wait_until="networkidle", timeout=timeout_ms)
            try:
                page.wait_for_timeout(1200)
            except Exception:
                pass
            data = page.evaluate(_EXTRACT_JS)
        finally:
            browser.close()

    data = data or {}
    data["schema_version"] = CHROME_SCHEMA_V2
    data["source_url"] = url
    nav = data.get("nav") or {}
    footer = data.get("footer") or {}
    log(
        f"[chrome-browser] nav links={len(nav.get('links') or [])} "
        f"ctas={len(nav.get('ctas') or [])} "
        f"footer columns={len(footer.get('columns') or [])}"
    )
    return data


def write_chrome_contract_v2(path: Path, contract: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")
    return path


def load_chrome_contract_v2(path: Path | None) -> dict[str, Any] | None:
    if not path or not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if isinstance(data, dict) and data.get("schema_version") == CHROME_SCHEMA_V2:
        return data
    return None
