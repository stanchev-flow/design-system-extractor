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

  // Text from a visually-hidden / sr-only descendant (the only label many
  // icon/dropdown <button>s carry). visibleText() intentionally drops these,
  // so read them straight from textContent.
  const srOnlyText = (el) => {
    const sr = el.querySelector(
      ".visually-hidden, .sr-only, .screen-reader-text, [class*='visually-hidden' i], [class*='sr-only' i]"
    );
    return sr ? collapse(sr.textContent || "") : "";
  };

  // Robust label for nav clickables: visible text first, then aria-label, then
  // the nearest tab-title / nav-link text in the same item, then any
  // visually-hidden text. Generic — works for HubSpot's dropdown tabs (whose
  // only label is a sibling .global-nav-tab-title span or a sr-only span) and
  // for ordinary a[href]/button items elsewhere.
  const navLabel = (el) => {
    let t = collapse(visibleText(el));
    if (t) return t.slice(0, 120);
    const aria = collapse(el.getAttribute("aria-label") || "");
    if (aria) return aria.slice(0, 120);
    const item = el.closest(
      ".global-nav-tab, .cl-navLink, li, [class*='nav-item' i], [class*='nav-tab' i]"
    ) || el.parentElement;
    if (item) {
      const tt = item.querySelector(
        ".global-nav-tab-title, [class*='tab-title' i], .cl-navLink-link"
      );
      if (tt) {
        const x = collapse(visibleText(tt) || tt.textContent || "");
        if (x) return x.slice(0, 120);
      }
    }
    const sr = srOnlyText(el);
    if (sr) return sr.slice(0, 120);
    return "";
  };

  // Label that works even for HIDDEN nodes (mega-menu panels are display:none in
  // a saved "complete" capture). visibleText() returns "" for hidden subtrees, so
  // fall back to aria-label and then raw textContent. Used ONLY for submenu
  // harvesting where we deliberately read hidden content straight from the DOM.
  const anyLabel = (el) => {
    let t = collapse(visibleText(el));
    if (t) return t.slice(0, 120);
    const aria = collapse(el.getAttribute && el.getAttribute("aria-label") || "");
    if (aria) return aria.slice(0, 120);
    return collapse(el.textContent || "").slice(0, 120);
  };

  // ---- mega-menu / dropdown harvesting (brand-agnostic) -------------------
  // For a primary nav link, find its associated submenu panel and return its
  // sub-links grouped by sub-column heading plus any "featured" items. The panel
  // is present-but-hidden in the saved DOM, so we read it directly (no hover/JS):
  //   1) aria-controls (on the link or a toggle button in the same nav item) →
  //      document.getElementById(target)   [most robust, fully generic]
  //   2) a sibling container whose class/role looks like a submenu/flyout/dropdown
  // Returns null when there's no panel (e.g. a plain destination link).
  const MENU_CLS = /submenu|sub-menu|sub-nav|subnav|flyout|fly-out|dropdown|drop-down|mega|tab-dropdown|nav-panel|menu-panel/i;
  const harvestMenu = (linkEl) => {
    // Resolve the enclosing nav-item container. Start the search from the link's
    // PARENT so a wrapper-ish class on the link itself (e.g. a "*nav-tab*" tab
    // title) can't match the link and shadow the real container that holds the
    // dropdown toggle / submenu panel.
    const item =
      (linkEl.parentElement || linkEl).closest(
        "li, [class*='nav-item' i], [class*='nav-tab' i], [class*='has-dropdown' i], [class*='menu-item' i], [class*='navLink' i]"
      ) || linkEl.parentElement;

    let panel = null;
    let controls = linkEl.getAttribute("aria-controls") || "";
    if (!controls && item) {
      const tog = item.querySelector("[aria-controls]");
      if (tog) controls = tog.getAttribute("aria-controls") || "";
    }
    if (controls) {
      const byId = document.getElementById(controls);
      if (byId && !byId.contains(linkEl)) panel = byId;
    }
    if (!panel && item) {
      const cands = Array.from(item.querySelectorAll("*")).filter((e) => {
        if (e === linkEl || e.contains(linkEl)) return false;
        const cls = e.getAttribute("class") || "";
        const role = e.getAttribute("role") || "";
        return (MENU_CLS.test(cls) || role === "menu") &&
          e.querySelector("a[href]");
      });
      cands.sort(
        (a, b) =>
          b.querySelectorAll("a[href]").length - a.querySelectorAll("a[href]").length
      );
      if (cands.length) panel = cands[0];
    }
    if (!panel) return null;

    // featured / banner / promo links (kept separate from the columns)
    const featuredSet = new Set();
    const featured = [];
    const seenF = new Set();
    for (const fe of panel.querySelectorAll(
      "[class*='banner' i], [class*='featured' i], [class*='promo' i], [class*='highlight' i]"
    )) {
      for (const a of fe.querySelectorAll("a[href]")) {
        featuredSet.add(a);
        const t = anyLabel(a);
        if (!t) continue;
        const href = a.getAttribute("href") || "";
        const k = (t + "|" + href).toLowerCase();
        if (seenF.has(k)) continue;
        seenF.add(k);
        featured.push({ label: t, href: href });
      }
    }

    // columns: group links by nearest preceding LEAF heading.
    // A title-classed node INSIDE a link is that LINK's own label (menu-card
    // title), never a column heading — promoting card titles to headings shifted
    // every column off by one card (sysfix 2026-07).
    const heads0 = Array.from(
      panel.querySelectorAll("h1,h2,h3,h4,h5,h6,[class*='title' i],[class*='heading' i]")
    ).filter((h) => !h.closest("a[href]"));
    const heads = heads0.filter((h) => !heads0.some((o) => o !== h && h.contains(o)));
    const allLinks = Array.from(panel.querySelectorAll("a[href]")).filter(
      (a) => !featuredSet.has(a)
    );
    // A menu-card link labels itself by its own TITLE node when it carries one;
    // anyLabel() on the whole card concatenated title+description into one string
    // ("Global Payroll RunRun compliant payroll easily", sysfix 2026-07).
    const menuLinkLabel = (a) => {
      const t = a.querySelector(
        "h1,h2,h3,h4,h5,h6,[class*='title' i]:not([class*='subtitle' i]),[class*='label' i],strong,b"
      );
      const own = t ? anyLabel(t) : "";
      return own || anyLabel(a);
    };
    const columns = [];
    if (heads.length) {
      for (let i = 0; i < heads.length; i++) {
        const head = heads[i];
        const next = heads[i + 1] || null;
        const items = [];
        const seenL = new Set();
        for (const a of allLinks) {
          const pos = head.compareDocumentPosition(a);
          if (!(pos & Node.DOCUMENT_POSITION_FOLLOWING)) continue;
          if (next) {
            const p2 = next.compareDocumentPosition(a);
            if (!(p2 & Node.DOCUMENT_POSITION_PRECEDING)) continue;
          }
          const t = menuLinkLabel(a);
          if (!t) continue;
          const href = a.getAttribute("href") || "";
          const k = (t + "|" + href).toLowerCase();
          if (seenL.has(k)) continue;
          seenL.add(k);
          items.push({ label: t, href: href });
        }
        if (items.length) columns.push({ heading: anyLabel(head), links: items });
      }
    }
    if (!columns.length && allLinks.length) {
      const items = [];
      const seenL = new Set();
      for (const a of allLinks) {
        const t = menuLinkLabel(a);
        if (!t) continue;
        const href = a.getAttribute("href") || "";
        const k = (t + "|" + href).toLowerCase();
        if (seenL.has(k)) continue;
        seenL.add(k);
        items.push({ label: t, href: href });
      }
      if (items.length) columns.push({ heading: "", links: items });
    }
    if (!columns.length && !featured.length) return null;
    return { columns: columns.slice(0, 16), featured: featured.slice(0, 12) };
  };

  const px = (v) => {
    const n = parseFloat(v || "0");
    return Number.isFinite(n) ? Math.round(n) : 0;
  };

  // max-width inherited up the ancestor chain (content container width).
  // PX LITERALS ONLY (sysfix 2026-07): a percentage/vw max-width is relative to its
  // own container, not a content measure — parsing `max-width: 100%` as 100(px)
  // shipped a 100px chrome container. Implausibly narrow px caps (< 320) are
  // treated as local element constraints, not the page content measure.
  const maxWidthUp = (el) => {
    let n = el;
    while (n && n !== document.body && n !== document.documentElement) {
      const mw = getComputedStyle(n).maxWidth;
      if (mw && mw !== "none" && /px$/.test(mw)) {
        const v = px(mw);
        if (v >= 320) return v;
      }
      n = n.parentElement;
    }
    return 0;
  };

  // nearest common ancestor of two nodes (for locating a grid/flex container)
  const lca = (a, b) => {
    const anc = new Set();
    let n = a;
    while (n) { anc.add(n); n = n.parentElement; }
    let m = b;
    while (m) { if (anc.has(m)) return m; m = m.parentElement; }
    return null;
  };
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
    // third-party marks are NEVER the site logo (sysfix 2026-07): app/play-store
    // badges, review-platform award/rating chips (a footer full of G2 badges
    // outscored the real wordmark), payment marks.
    if (/app-?store|play-?store|google-?play|apps\.apple|play\.google|badge|award|rating|trustpilot|capterra|\bg2\b/.test(hay)) s -= 6;
    if (href === "/" || href === origin || href === origin + "/" || href === "") s += 3;
    // an OFFSITE store/marketplace destination is not the brand home link
    if (/^https?:\/\//.test(href) && href.indexOf(origin) !== 0) s -= 2;
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

  // Effective painted background: walk up until a non-transparent backgroundColor
  // (a transparent nav bar PAINTS as its ancestor's fill — capture that fact so the
  // generator never renders `rgba(0,0,0,0)` as if it were a surface, sysfix 2026-07).
  const effectiveBg = (el) => {
    let n = el;
    while (n && n !== document.documentElement) {
      const bg = getComputedStyle(n).backgroundColor;
      if (!transparent(bg)) return bg;
      n = n.parentElement;
    }
    const rootBg = getComputedStyle(document.documentElement).backgroundColor;
    return transparent(rootBg) ? "" : rootBg;
  };

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

  // Real measured `:hover` color for an element. Scans every accessible
  // stylesheet for rules whose selector contains `:hover` and sets `color`,
  // then keeps the LAST rule whose base selector (`:hover` stripped) matches
  // `el` in its actual DOM position (rough cascade order). Cross-origin sheets
  // throw on cssRules access and are skipped. Returns "" when no hover color
  // rule applies — NEVER fabricates one. Lets the generator derive link-hover
  // from each brand's genuine behavior instead of a hardcoded brand hue.
  // Resolve a declared color value to a concrete literal: follow a single
  // `var(--name[, fallback])` against the element's (inherited) custom props so
  // a hover rule like `color: var(--yellow)` becomes the real swatch. Returns ""
  // if it can't be resolved to a usable color (so the caller skips it).
  const resolveColor = (raw, el) => {
    let v = (raw || "").trim();
    if (!v) return "";
    const m = v.match(/^var\(\s*(--[\w-]+)\s*(?:,\s*([\s\S]+))?\)$/);
    if (m) {
      let resolved = "";
      try { resolved = (getComputedStyle(el).getPropertyValue(m[1]) || "").trim(); } catch (e) {}
      if (!resolved && m[2]) resolved = m[2].trim();
      v = resolved;
    }
    if (!v || v.indexOf("var(") >= 0) return "";  // unresolved → skip, don't store a var
    return v;
  };

  const hoverColor = (el) => {
    if (!el) return "";
    let found = "";
    let sheets;
    try { sheets = Array.from(document.styleSheets || []); } catch (e) { return ""; }
    for (const sheet of sheets) {
      let rules = null;
      try { rules = sheet.cssRules || sheet.rules; } catch (e) { continue; }
      if (!rules) continue;
      for (const rule of Array.from(rules)) {
        const sel = rule.selectorText;
        if (!sel || sel.indexOf(":hover") < 0) continue;
        const col = rule.style && rule.style.getPropertyValue("color");
        if (!col) continue;
        for (let part of sel.split(",")) {
          if (part.indexOf(":hover") < 0) continue;
          const base = part.replace(/:hover/g, "").trim();
          if (!base) continue;
          try {
            if (el.matches(base)) {
              const resolved = resolveColor(col, el);
              if (resolved) found = resolved;
            }
          } catch (e) { /* invalid selector */ }
        }
      }
    }
    return found;
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

    // Junk labels: icon-button aria text, skip-links, logo home links, toggles,
    // plus a11y / theme-appearance toggles (not real nav destinations).
    const JUNK = /\b(toggle|open menu|close menu|close|skip to|search form|home link|hamburger|menu button|open search|breadcrumb)\b/i;
    const A11Y_TOGGLE = /\b(high contrast|dark mode|light mode|appearance|theme|reduce motion|color scheme)\b/i;

    // candidate clickables that live INSIDE the header band (excludes dropdown
    // panels that render below the header on hover/focus).
    const inHeaderBand = (el) => {
      const r = el.getBoundingClientRect();
      return r.top >= hr.top - 6 && r.bottom <= hr.bottom + 6 && r.height > 0;
    };
    // Candidate clickables: real links/buttons PLUS dropdown-tab labels that are
    // only spans (HubSpot's Products/Solutions/Resources mega-menu tabs) and any
    // role=menuitem entries. Generic across sites.
    const clickables = Array.from(
      header.querySelectorAll("a[href], button, [class*='tab-title' i], [role='menuitem']")
    ).filter((el) => isVisible(el) && inHeaderBand(el));

    const navLinks = [];
    const ctas = [];
    const seen = new Set();

    for (const el of clickables) {
      if (logoAnchor && (el === logoAnchor || logoAnchor.contains(el) || el.contains(logoAnchor))) continue;
      const text = navLabel(el);
      if (!text) continue;
      if (text.length > 60) continue;
      if (JUNK.test(text)) continue;
      if (A11Y_TOGGLE.test(text)) continue;
      // icon-only control (search/hamburger): has svg/img but no real word text
      if (el.querySelector("svg, img") && !/[A-Za-z]{2,}/.test(text)) continue;
      const s = getComputedStyle(el);
      const href = el.tagName === "A" ? (el.getAttribute("href") || "") : "";
      // pill fill painted on a pseudo-element (sysfix 2026-07): buttons whose own
      // background is transparent but whose ::before/::after carries the fill are
      // still filled CTAs — read the pseudo layer before declaring "not a button".
      let bg = s.backgroundColor;
      if (transparent(bg)) {
        for (const pe of ["::before", "::after"]) {
          const ps = getComputedStyle(el, pe);
          if (ps.content !== "none" && !transparent(ps.backgroundColor)) { bg = ps.backgroundColor; break; }
        }
      }
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
          _el: el,
        });
      } else {
        navLinks.push({
          label: text,
          href: href,
          color: s.color,
          fontFamily: s.fontFamily,
          fontSize: px(s.fontSize),
          fontWeight: s.fontWeight,
          top: Math.round(el.getBoundingClientRect().top),
          _el: el,
        });
      }
    }

    // ---- two-tier split: a utility row sits ABOVE the primary bar. -----------
    // Cluster nav links by vertical position (rect.top) and split at the single
    // largest row gap; items above the gap are the utility tier. Generic — when
    // there's only one row, everything is primary and utility is empty.
    const tops = navLinks.map((l) => l.top).sort((a, b) => a - b);
    let splitTop = null;
    if (tops.length >= 2) {
      let maxGap = 0;
      for (let i = 1; i < tops.length; i++) {
        const g = tops[i] - tops[i - 1];
        if (g > maxGap) { maxGap = g; splitTop = tops[i]; }
      }
      if (maxGap < 16) splitTop = null; // single visual row
    }
    // strip internal-only fields (DOM ref + measurement helper) from output
    const clean = (l) => {
      const { top, _el, ...rest } = l;
      return rest;
    };
    for (const l of navLinks) {
      l.tier = splitTop !== null && l.top < splitTop ? "utility" : "primary";
    }

    // Attach captured mega-menu (columns + featured) to each PRIMARY tab that
    // owns a dropdown. Read straight from the (hidden) DOM panel — no hover.
    for (const l of navLinks) {
      if (l.tier !== "primary" || !l._el) continue;
      const menu = harvestMenu(l._el);
      if (menu) l.menu = menu;
    }

    // ---- measured computed styles (the real fidelity lever) ----------------
    // Structured numbers/strings (NOT raw CSS rules). Captured while the page is
    // live so the generator can render true proportions instead of guesses.
    const primEntries = navLinks.filter((l) => l.tier === "primary");
    const utilEntries = navLinks.filter((l) => l.tier === "utility");
    const fp = primEntries.length ? primEntries[0]._el : null;
    const fu = utilEntries.length ? utilEntries[0]._el : null;
    const fcta = ctas.length ? ctas[0]._el : null;
    // the primary-tab ROW container = common ancestor of first & last primary
    // links (so its gap is the inter-tab gap, not a within-tab gap).
    let linksBox = fp ? fp.parentElement : null;
    if (primEntries.length > 1) {
      const lastP = primEntries[primEntries.length - 1]._el;
      const box = lca(fp, lastP);
      if (box) linksBox = box;
    }

    const measured = {
      _provenance: "getComputedStyle (rendered px / CSS strings) from saved DOM",
      bar: {
        bg: hs.backgroundColor,
        // the PAINTED bar fill (ancestor fill when the bar itself is transparent)
        effectiveBg: effectiveBg(header),
        height: px(hs.height) || Math.round(hr.height),
        paddingTop: px(hs.paddingTop),
        paddingBottom: px(hs.paddingBottom),
        paddingLeft: px(hs.paddingLeft),
        paddingRight: px(hs.paddingRight),
      },
      utilityBarHeight: splitTop !== null ? Math.max(0, Math.round(splitTop - hr.top)) : 0,
      primaryBarHeight: splitTop !== null ? Math.max(0, Math.round(hr.bottom - splitTop)) : Math.round(hr.height),
      contentMaxWidth: linksBox ? maxWidthUp(linksBox) : 0,
    };
    if (logo) measured.logo = { width: logo.width || 0, height: logo.height || 0 };
    if (fp) {
      const s = getComputedStyle(fp);
      measured.link = {
        fontSize: px(s.fontSize),
        fontWeight: s.fontWeight,
        color: s.color,
        lineHeight: s.lineHeight,
      };
      const hc = hoverColor(fp);
      if (hc) measured.linkHoverColor = hc;
    }
    if (linksBox) {
      const s = getComputedStyle(linksBox);
      const g = s.columnGap && s.columnGap !== "normal" ? s.columnGap : s.gap;
      measured.linkGap = px(g || "0");
    }
    if (fu) {
      const s = getComputedStyle(fu);
      measured.utilityLink = { fontSize: px(s.fontSize), fontWeight: s.fontWeight, color: s.color };
    }
    if (fcta) {
      const s = getComputedStyle(fcta);
      // pseudo-element pill fill (same rule as the classifier above)
      let ctaBg = s.backgroundColor;
      if (transparent(ctaBg)) {
        for (const pe of ["::before", "::after"]) {
          const ps = getComputedStyle(fcta, pe);
          if (ps.content !== "none" && !transparent(ps.backgroundColor)) { ctaBg = ps.backgroundColor; break; }
        }
      }
      measured.cta = {
        bg: ctaBg,
        color: s.color,
        fontSize: px(s.fontSize),
        fontWeight: s.fontWeight,
        paddingTop: px(s.paddingTop),
        paddingBottom: px(s.paddingBottom),
        paddingLeft: px(s.paddingLeft),
        paddingRight: px(s.paddingRight),
        radius: px(s.borderTopLeftRadius),
      };
    }

    const utilityLinks = navLinks.filter((l) => l.tier === "utility").map(clean);
    const primaryLinks = navLinks.filter((l) => l.tier === "primary").map(clean);

    result.nav = {
      found: true,
      sticky: sticky,
      twoTier: utilityLinks.length > 0,
      bg: hs.backgroundColor,
      color: bodyStyle.color,
      height: px(hs.height) || Math.round(hr.height),
      logo: logo,
      // `links` keeps the full ordered list (back-compat); tiers carry the rows.
      links: navLinks.map(clean).slice(0, 16),
      utility: utilityLinks.slice(0, 10),
      primary: primaryLinks.slice(0, 12),
      ctas: ctas.map((c) => { const { _el, ...rest } = c; return rest; }).slice(0, 4),
      anyButtonHasIcon: ctas.some((c) => c.hasIcon),
      measured: measured,
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
    // Heading candidates INSIDE a link are link labels, not group headings
    // (same discipline as the mega-menu splitter, sysfix 2026-07).
    const headingEls = Array.from(
      footer.querySelectorAll("h2, h3, h4, h5, h6, [class*='title' i], [class*='heading' i]")
    ).filter(isVisible).filter((h) => !h.closest("a[href]"));

    const columns = [];
    const colHeads = [];  // headings that actually produced a linked column
    if (headingEls.length >= 2) {
      for (let i = 0; i < headingEls.length; i++) {
        const head = headingEls[i];
        const headLabel = label(head);
        // collect links that come after this heading but before the next heading.
        // WALK UP from the heading to the nearest ancestor that actually contains
        // links (sysfix 2026-07): accordion-style footers wrap the group title in
        // its own <button> — head.parentElement held zero links, so every heading
        // produced an empty column and the extraction fell back to heading-less
        // grid columns.
        const next = headingEls[i + 1] || null;
        let container = head.parentElement || footer;
        while (container && container !== footer && !container.querySelector("a[href]")) {
          container = container.parentElement;
        }
        container = container || footer;
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
        // no per-column cap: capture ALL links under each heading
        if (items.length) { columns.push({ heading: headLabel, links: items }); colHeads.push(head); }
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

    // ---- footer social / legal / newsletter (optional enrichments) -------
    // SOCIAL: icon links / rel=me / known social hosts. Network-typed so the
    // bridge can pick the right glyph without inventing one.
    const SOCIAL_NET = [
      [/facebook|fb\.com|fb\.me/i, "facebook"],
      [/twitter\.com|x\.com|\/x\/?$/i, "twitter"],
      [/linkedin/i, "linkedin"],
      [/youtube|youtu\.be/i, "youtube"],
      [/instagram|instagr\.am/i, "instagram"],
      [/tiktok/i, "tiktok"],
      [/github\.com/i, "github"],
      [/threads\.net/i, "threads"],
      [/pinterest/i, "pinterest"],
      [/glassdoor/i, "glassdoor"],
      [/discord/i, "discord"],
      [/twitch\.tv/i, "twitch"],
      [/reddit/i, "reddit"],
      [/medium\.com/i, "medium"],
      [/dribbble/i, "dribbble"],
      [/vimeo/i, "vimeo"],
      [/wa\.me|whatsapp/i, "whatsapp"],
      [/t\.me|telegram/i, "telegram"],
      [/mastodon/i, "mastodon"],
      [/spotify\.com/i, "spotify"],
    ];
    const socialNet = (s) => {
      for (const [re, name] of SOCIAL_NET) if (re.test(s || "")) return name;
      return "";
    };
    const social = [];
    const seenSocial = new Set();
    for (const a of Array.from(footer.querySelectorAll("a[href]")).filter(isVisible)) {
      const href = a.getAttribute("href") || "";
      if (!href || href.startsWith("#") || /^javascript:/i.test(href)) continue;
      const rel = a.getAttribute("rel") || "";
      const aria = (a.getAttribute("aria-label") || "") + " " + (a.getAttribute("title") || "");
      const cls = a.getAttribute("class") || "";
      const img = a.querySelector("img");
      const imgHay = img ? ((img.getAttribute("alt") || "") + " " + (img.currentSrc || img.src || "")) : "";
      const hay = href + " " + aria + " " + cls + " " + imgHay;
      const net = socialNet(hay);
      const isMe = /(^|\s)me(\s|$)/.test(rel);
      if (!net && !isMe) continue;
      const key = (net || href).toLowerCase();
      if (seenSocial.has(key)) continue;
      seenSocial.add(key);
      // kind: does THIS source link render an icon glyph (svg / small img with no
      // real word text) or visible text? Drives whether the generator may show an
      // icon — never inject icons the page didn't use. Generic across brands.
      const visTxt = collapse(visibleText(a));
      const iconChild = hasIconChild(a);
      const kind = (iconChild && !/[A-Za-z]{2,}/.test(visTxt)) ? "icon" : (visTxt ? "text" : "icon");
      social.push({ network: net || "link", kind: kind, href: href, label: collapse(label(a)) || collapse(aria) || net, _el: a });
    }
    const firstSocialEl = social.length ? social[0]._el : null;

    // LEGAL: copyright line (most specific element carrying © / "all rights
    // reserved") + legal nav links (privacy / terms / cookies / ...).
    const COPY = /©|\(c\)|copyright|all rights reserved/i;
    const LEGAL_LINK = /privacy|terms|cookie|legal|accessib|gdpr|ccpa|do not sell|trademark|compliance|imprint|disclaimer/i;
    let legalText = "";
    let legalTextEl = null;
    for (const el of Array.from(footer.querySelectorAll("p, span, div, small, li, address")).filter(isVisible)) {
      const t = collapse(el.textContent || "");
      if (t && COPY.test(t) && t.length <= 240) {
        if (!legalText || t.length < legalText.length) { legalText = t; legalTextEl = el; }
      }
    }
    const legalLinks = [];
    const seenLegal = new Set();
    let firstLegalLinkEl = null;
    const pushLegal = (a) => {
      const t = collapse(label(a)) || collapse(a.getAttribute("aria-label") || "");
      if (!t) return;
      const k = t.toLowerCase();
      if (seenLegal.has(k)) return;
      seenLegal.add(k);
      if (!firstLegalLinkEl) firstLegalLinkEl = a;
      legalLinks.push({ label: t, href: a.getAttribute("href") || "#" });
    };
    // 1) walk the real legal / copyright / sub-footer utility nav so we capture
    //    EVERY bottom-row link in document order — including ones whose label
    //    doesn't match the legal keyword regex (e.g. "Security"). Generic.
    const legalContainer = footer.querySelector(
      "[class*='copyright' i], [class*='legal' i], [class*='sub-footer' i], [class*='subfooter' i], [class*='footer-bottom' i], [class*='footer__bottom' i]"
    );
    if (legalContainer) {
      for (const a of Array.from(legalContainer.querySelectorAll("a[href]")).filter(isVisible)) {
        // skip logo / icon-only anchors (image with no real word label) so the
        // brand wordmark link doesn't masquerade as a legal entry.
        if (!collapse(label(a)) && a.querySelector("img, svg")) continue;
        pushLegal(a);
      }
    }
    // 2) plus any keyword-matched legal links elsewhere in the footer
    for (const a of Array.from(footer.querySelectorAll("a[href]")).filter(isVisible)) {
      const t = collapse(label(a));
      if (t && LEGAL_LINK.test(t)) pushLegal(a);
    }

    // NEWSLETTER: an email input + submit living in the footer.
    let newsletter = null;
    const emailInput = Array.from(footer.querySelectorAll("input")).find((i) => {
      if (!isVisible(i)) return false;
      const ty = (i.getAttribute("type") || "").toLowerCase();
      const nm = ((i.getAttribute("name") || "") + " " + (i.getAttribute("id") || "") + " " +
        (i.getAttribute("placeholder") || "") + " " + (i.getAttribute("aria-label") || "")).toLowerCase();
      return ty === "email" || (ty !== "checkbox" && ty !== "radio" && /e-?mail|newsletter|subscribe/.test(nm));
    });
    if (emailInput) {
      const form = emailInput.closest("form");
      const scope = form || footer;
      let submitLabel = "";
      const btn = scope.querySelector("button[type='submit'], input[type='submit'], input[type='button'], button");
      if (btn) submitLabel = collapse(btn.tagName === "INPUT" ? (btn.getAttribute("value") || "") : label(btn));
      let heading = "";
      if (form) {
        const h = form.querySelector("h2, h3, h4, h5, [class*='title' i], [class*='heading' i], label");
        if (h && isVisible(h)) heading = collapse(label(h));
      }
      newsletter = {
        present: true,
        heading: heading,
        placeholder: emailInput.getAttribute("placeholder") || "",
        emailName: emailInput.getAttribute("name") || "",
        action: form ? (form.getAttribute("action") || "") : "",
        method: form ? (form.getAttribute("method") || "").toLowerCase() : "",
        submitLabel: submitLabel || "Subscribe",
      };
    }

    // ---- measured computed styles (structured numbers/strings) -------------
    const fmeasured = {
      _provenance: "getComputedStyle (rendered px / CSS strings) from saved DOM",
      bg: fs.backgroundColor,
      color: fs.color,
      padding: {
        top: px(fs.paddingTop),
        bottom: px(fs.paddingBottom),
        left: px(fs.paddingLeft),
        right: px(fs.paddingRight),
      },
      contentMaxWidth: maxWidthUp(headingEls.length ? headingEls[0] : footer),
    };
    // column grid: locate the grid/flex container holding the columns (LCA of
    // first & last COLUMN-PRODUCING heading — decorative titles elsewhere in the
    // footer must not widen the scope) and read its real track/gap geometry.
    const gridHeads = colHeads.length >= 2 ? colHeads : headingEls;
    let colsContainer = null;
    if (gridHeads.length >= 2) {
      colsContainer = lca(gridHeads[0], gridHeads[gridHeads.length - 1]);
    }
    if (colsContainer) {
      const cs = getComputedStyle(colsContainer);
      // physical column WRAPPERS (sysfix 2026-07): direct children that hold the
      // headed groups — a flex/columns footer (no grid tracks) still reports its
      // real column count AND the per-wrapper group distribution (e.g. 8 groups
      // over 6 columns as [1,2,1,2,1,1]), so the generator reproduces the source
      // stacking instead of guessing.
      const kids = Array.from(colsContainer.children);
      const wrapperSizes = kids
        .map((ch) => gridHeads.filter((h) => ch.contains(h)).length)
        .filter((n) => n > 0);
      fmeasured.grid = {
        display: cs.display,
        templateColumns: cs.gridTemplateColumns && cs.gridTemplateColumns !== "none" ? cs.gridTemplateColumns : "",
        columnGap: px((cs.columnGap && cs.columnGap !== "normal") ? cs.columnGap : cs.gap),
        rowGap: px((cs.rowGap && cs.rowGap !== "normal") ? cs.rowGap : cs.gap),
        columnCount: columns.length,
        wrapperCount: wrapperSizes.length,
        wrapperSizes: wrapperSizes,
      };
    } else {
      fmeasured.grid = { display: "", templateColumns: "", columnGap: 0, rowGap: 0, columnCount: columns.length };
    }
    if (headingEls.length) {
      const s = getComputedStyle(headingEls[0]);
      fmeasured.heading = { fontSize: px(s.fontSize), fontWeight: s.fontWeight, lineHeight: s.lineHeight, color: s.color, fontFamily: s.fontFamily };
    }
    // first real column link (skip the logo anchor) for link typography
    let flinkEl = null;
    for (const a of Array.from(footer.querySelectorAll("a[href]")).filter(isVisible)) {
      if (!collapse(label(a))) continue;
      if (a.querySelector("svg, img")) continue;
      flinkEl = a;
      break;
    }
    if (flinkEl) {
      const s = getComputedStyle(flinkEl);
      fmeasured.link = { fontSize: px(s.fontSize), fontWeight: s.fontWeight, lineHeight: s.lineHeight, color: s.color };
      const fhc = hoverColor(flinkEl);
      if (fhc) fmeasured.linkHoverColor = fhc;
    }
    if (flogo) fmeasured.logo = { width: flogo.width || 0, height: flogo.height || 0 };
    if (firstSocialEl) {
      // Footer-level social STYLE + (for text socials) their typography. The
      // generator uses `kind` to decide icon-glyphs vs real text labels, so it
      // never fabricates icons the source didn't use.
      const iconEl = firstSocialEl.querySelector("svg, img");
      const isIcon = social.length ? social[0].kind === "icon" : !!iconEl;
      const sizedEl = iconEl || firstSocialEl;
      const ss = getComputedStyle(sizedEl);
      const as = getComputedStyle(firstSocialEl);
      fmeasured.social = {
        kind: isIcon ? "icon" : "text",
        size: iconEl ? (px(ss.width) || px(ss.height) || 0) : 0,
        fontSize: px(as.fontSize),
        fontWeight: as.fontWeight,
        color: as.color,
        letterSpacing: as.letterSpacing,
        textTransform: as.textTransform,
      };
    }
    if (legalContainer) {
      // Determine the bottom block's true horizontal alignment GEOMETRICALLY:
      // many footers center the copyright/legal row via a centering parent (auto
      // margins / flex), so the element's own text-align reads "start" even when
      // it's visually centered. Compare its left/right gaps inside the footer.
      const fr = footer.getBoundingClientRect();
      const lr = legalContainer.getBoundingClientRect();
      const leftGap = lr.left - fr.left;
      const rightGap = fr.right - lr.right;
      let align = getComputedStyle(legalContainer).textAlign || "start";
      if (lr.width > 8 && Math.abs(leftGap - rightGap) <= 48 && leftGap > 24) {
        align = "center";
      } else if (leftGap <= rightGap) {
        align = "start";
      } else {
        align = "end";
      }
      fmeasured.bottom = { textAlign: align };
    }
    // LEGAL ROW TYPOGRAPHY: the © / copyright micro-text + small legal links use
    // their OWN (typically tiny) type — NOT the large sitemap column-link size.
    // Measure straight from the real legal/copyright DOM node so the generator
    // never reuses fmeasured.link (the big column link) for the legal row.
    // Preference: copyright text node → first legal link → legal container.
    let legalMeasureEl = legalTextEl || firstLegalLinkEl || legalContainer;
    // If the chosen node is a wrapper, prefer a leaf text/anchor inside it so we
    // read the actual rendered micro-text size rather than an inherited default.
    if (legalMeasureEl === legalContainer && legalContainer) {
      const leaf = legalContainer.querySelector("a[href], span, small, p, li");
      if (leaf && isVisible(leaf)) legalMeasureEl = leaf;
    }
    if (legalMeasureEl) {
      const s = getComputedStyle(legalMeasureEl);
      fmeasured.legal = {
        fontSize: px(s.fontSize),
        fontWeight: s.fontWeight,
        lineHeight: s.lineHeight,
        color: s.color,
      };
    }

    const cleanSocial = social.map((x) => { const { _el, ...rest } = x; return rest; });

    result.footer = {
      found: true,
      bg: fs.backgroundColor,
      color: fs.color,
      logo: flogo,
      columns: columns.slice(0, 8),
      social: cleanSocial.slice(0, 12),
      legal: { text: legalText, links: legalLinks.slice(0, 12) },
      newsletter: newsletter,
      measured: fmeasured,
    };
  }

  return result;
};
"""


# ── 1:1 reference snapshot (separate artifact; NOT fed into the contract) ────
# Lifts the ACTUAL nav + footer DOM subtree and inlines its SCOPED computed
# styles so a faithful, self-contained reference renders offline in the Studio
# iframe. Studio-iframe safety: viewport units (vh/vw/dvh/vmin/vmax) are rewritten
# to container-query units and a container-type context is set; <img>/background
# images are inlined as data URIs. Hidden subtrees (e.g. closed mega-menu panels)
# are kept display:none but pruned to keep the file lean.
_SNAPSHOT_JS = r"""
async () => {
  const PROPS = [
    "display","position","top","right","bottom","left","z-index","box-sizing","float","clear",
    "width","height","min-width","min-height","max-width","max-height",
    "margin-top","margin-right","margin-bottom","margin-left",
    "padding-top","padding-right","padding-bottom","padding-left",
    "border-top-width","border-right-width","border-bottom-width","border-left-width",
    "border-top-style","border-right-style","border-bottom-style","border-left-style",
    "border-top-color","border-right-color","border-bottom-color","border-left-color",
    "border-top-left-radius","border-top-right-radius","border-bottom-left-radius","border-bottom-right-radius",
    "outline-width","outline-style","outline-color","box-shadow","opacity","visibility","overflow-x","overflow-y",
    "color","background-color","background-image","background-size","background-position","background-repeat","background-clip","background-origin",
    "font-family","font-size","font-weight","font-style","line-height","letter-spacing","word-spacing",
    "text-align","text-transform","text-decoration-line","text-decoration-color","white-space","text-overflow","text-indent","vertical-align",
    "flex-direction","flex-wrap","justify-content","align-items","align-content","align-self","gap","column-gap","row-gap","flex-grow","flex-shrink","flex-basis","order",
    "grid-template-columns","grid-template-rows","grid-column","grid-row","grid-auto-flow","grid-auto-columns","grid-auto-rows","place-items","place-content",
    "transform","transform-origin","transition","list-style-type","list-style-position","object-fit","object-position","fill","stroke","stroke-width","cursor","pointer-events"
  ];
  const isVisible = (el) => {
    const s = getComputedStyle(el);
    if (s.display === "none" || s.visibility === "hidden") return false;
    const r = el.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) return false;
    return el.offsetParent !== null || s.position === "fixed";
  };
  // header pick (mirror of the main extractor)
  const headerCandidates = [
    document.querySelector("header[role='banner']"),
    document.querySelector("header"),
    document.querySelector("[class*='navbar' i]"),
    document.querySelector("nav"),
  ].filter(Boolean);
  let header = null;
  for (const c of headerCandidates) {
    const r = c.getBoundingClientRect();
    if (isVisible(c) && r.top < 220 && r.height >= 32 && r.height < 240) { header = c; break; }
  }
  if (!header) header = headerCandidates[0] || null;
  // footer pick
  let footers = Array.from(document.querySelectorAll("footer")).filter(isVisible);
  if (!footers.length) {
    const cands = Array.from(document.querySelectorAll("[class*='footer' i]")).filter(isVisible);
    const outer = cands.filter((el) => !cands.some((o) => o !== el && o.contains(el)));
    outer.sort((a, b) =>
      a.getBoundingClientRect().top + window.scrollY - (b.getBoundingClientRect().top + window.scrollY));
    footers = outer.length ? [outer[outer.length - 1]] : [];
  }
  const footer = footers.length ? footers[footers.length - 1] : null;

  const cq = (v) => (v || "")
    .replace(/(-?[0-9.]+)dvh/g, "$1cqh").replace(/(-?[0-9.]+)dvw/g, "$1cqw")
    .replace(/(-?[0-9.]+)svh/g, "$1cqh").replace(/(-?[0-9.]+)svw/g, "$1cqw")
    .replace(/(-?[0-9.]+)lvh/g, "$1cqh").replace(/(-?[0-9.]+)lvw/g, "$1cqw")
    .replace(/(-?[0-9.]+)vh/g, "$1cqh").replace(/(-?[0-9.]+)vw/g, "$1cqw")
    .replace(/(-?[0-9.]+)vmin/g, "$1cqi").replace(/(-?[0-9.]+)vmax/g, "$1cqi");

  const toDataURI = async (url) => {
    try {
      const res = await fetch(url);
      const blob = await res.blob();
      return await new Promise((resolve) => {
        const fr = new FileReader();
        fr.onloadend = () => resolve(fr.result || "");
        fr.onerror = () => resolve("");
        fr.readAsDataURL(blob);
      });
    } catch (e) { return ""; }
  };

  const imgJobs = [];
  const inlineStyles = (orig, clone) => {
    if (orig.nodeType !== 1 || clone.nodeType !== 1) return;
    const cs = getComputedStyle(orig);
    let css = "";
    for (const p of PROPS) {
      const val = cs.getPropertyValue(p);
      if (val === "" || val == null) continue;
      css += p + ":" + cq(val) + ";";
    }
    clone.setAttribute("style", css);
    if (clone.hasAttribute("srcset")) clone.removeAttribute("srcset");
    if (cs.display === "none") { while (clone.firstChild) clone.removeChild(clone.firstChild); return; }
    if (clone.tagName === "IMG") {
      const src = orig.currentSrc || orig.src || "";
      if (src && !/^data:/i.test(src)) imgJobs.push({ clone, src, bg: false });
    }
    const bi = cs.backgroundImage;
    if (bi && bi !== "none" && /url\(/i.test(bi)) {
      const m = bi.match(/url\((["']?)(.*?)\1\)/i);
      if (m && m[2] && !/^data:/i.test(m[2])) imgJobs.push({ clone, src: m[2], bg: true });
    }
    const oc = orig.children, cc = clone.children;
    for (let i = 0; i < oc.length && i < cc.length; i++) inlineStyles(oc[i], cc[i]);
  };

  const snap = async (el) => {
    if (!el) return "";
    imgJobs.length = 0;
    const clone = el.cloneNode(true);
    inlineStyles(el, clone);
    for (const job of imgJobs) {
      const uri = await toDataURI(job.src);
      if (!uri) continue;
      if (job.bg) {
        const st = job.clone.getAttribute("style") || "";
        job.clone.setAttribute("style", st.replace(/background-image:[^;]*;/i, "background-image:url(" + uri + ");"));
      } else {
        job.clone.setAttribute("src", uri);
      }
    }
    return clone.outerHTML;
  };

  const navHtml = await snap(header);
  const footerHtml = await snap(footer);
  return {
    navHtml: navHtml,
    footerHtml: footerHtml,
    bodyBg: getComputedStyle(document.body).backgroundColor,
    pageWidth: Math.round(document.documentElement.clientWidth) || 1440,
  };
};
"""


def _reference_doc(brand: str, snap: dict[str, Any]) -> str:
    """Wrap the captured nav/footer subtrees in a self-contained reference doc."""
    body_bg = snap.get("bodyBg") or "#ffffff"
    nav_html = snap.get("navHtml") or ""
    footer_html = snap.get("footerHtml") or ""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>{brand} — nav/footer 1:1 reference (inlined computed styles)</title>
<meta name="robots" content="noindex" />
<style>
  /* Studio-iframe safety: container-query frame so any cq* units resolve; the
     captured subtrees carry their own inlined computed styles (viewport units
     already rewritten to cq units at capture time). */
  html, body {{ container-type: size; container-name: frame; margin: 0; background: {body_bg}; }}
  * {{ box-sizing: border-box; }}
  img {{ max-width: 100%; }}
  .ref-spacer {{ min-height: 24cqh; }}
</style>
</head>
<body>
{nav_html}
<div class="ref-spacer"></div>
{footer_html}
</body>
</html>
"""


def snapshot_chrome_reference_from_saved_page(
    html_path: str | Path,
    out_path: str | Path,
    *,
    timeout_ms: int = 30000,
    log=print,
) -> Path:
    """Capture a 1:1 nav/footer reference from a saved page (OFFLINE) → out_path.

    Serves the saved folder over localhost, lifts the live nav + footer subtrees,
    inlines their scoped computed styles + data-URI images, and writes a faithful
    self-contained reference HTML. This is a REFERENCE artifact ONLY — it does not
    touch source-chrome.v2.json or brand.yaml.
    """
    import http.server
    import socketserver
    import threading
    from urllib.parse import quote

    from playwright.sync_api import sync_playwright

    html_path = Path(html_path).resolve()
    if not html_path.exists():
        raise FileNotFoundError(f"saved page not found: {html_path}")
    serve_dir = html_path.parent

    class _Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(serve_dir), **kw)

        def log_message(self, *a):
            pass

    httpd = socketserver.TCPServer(("127.0.0.1", 0), _Handler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    local_url = f"http://127.0.0.1:{port}/{quote(html_path.name)}"
    log(f"[chrome-reference] serving {serve_dir} → {local_url}")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            try:
                page = browser.new_page(viewport={"width": 1440, "height": 1024})
                page.goto(local_url, wait_until="networkidle", timeout=timeout_ms)
                try:
                    page.wait_for_timeout(1000)
                except Exception:
                    pass
                snap = page.evaluate(_SNAPSHOT_JS)
            finally:
                browser.close()
    finally:
        httpd.shutdown()
        httpd.server_close()

    snap = snap or {}
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc = _reference_doc(html_path.parent.name or "reference", snap)
    out_path.write_text(doc, encoding="utf-8")
    log(
        f"[chrome-reference] wrote {out_path} "
        f"(nav {len(snap.get('navHtml') or '')} chars, footer {len(snap.get('footerHtml') or '')} chars)"
    )
    return out_path


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
    menus = sum(1 for p in (nav.get("primary") or []) if isinstance(p, dict) and p.get("menu"))
    log(
        f"[chrome-browser] nav links={len(nav.get('links') or [])} "
        f"ctas={len(nav.get('ctas') or [])} "
        f"primary_menus={menus} "
        f"nav_measured={'yes' if nav.get('measured') else 'no'} "
        f"footer columns={len(footer.get('columns') or [])} "
        f"social={len(footer.get('social') or [])} "
        f"legal_links={len((footer.get('legal') or {}).get('links') or [])} "
        f"footer_measured={'yes' if footer.get('measured') else 'no'} "
        f"newsletter={'yes' if footer.get('newsletter') else 'no'}"
    )
    return data


def _resolve_hrefs(data: dict[str, Any], base_url: str) -> None:
    """Resolve relative hrefs in a v2 contract against `base_url` (in place).

    "Save Page As, Complete" snapshots usually keep absolute hrefs, but some
    sites emit root-relative links (/products). Absolute hrefs are left as-is so
    we never rewrite real destinations; only relative ones are joined.
    """
    from urllib.parse import urljoin

    base = base_url.rstrip("/") + "/" if base_url else ""

    def fix(href: str | None) -> str:
        h = (href or "").strip()
        if not h or h.startswith("#") or h.startswith("javascript:") or h.startswith("mailto:") or h.startswith("tel:"):
            return h or ""
        if h.startswith("http://") or h.startswith("https://"):
            return h
        if h.startswith("//"):
            return "https:" + h
        if not base:
            return h
        return urljoin(base, h.lstrip("/"))

    nav = data.get("nav") if isinstance(data.get("nav"), dict) else {}
    if isinstance(nav.get("logo"), dict) and nav["logo"].get("href"):
        nav["logo"]["href"] = fix(nav["logo"].get("href"))
    for tier_key in ("links", "utility", "primary"):
        for ln in (nav.get(tier_key) or []):
            if isinstance(ln, dict):
                ln["href"] = fix(ln.get("href"))
                menu = ln.get("menu") if isinstance(ln.get("menu"), dict) else None
                if menu:
                    for col in (menu.get("columns") or []):
                        for sub in (col.get("links") or []):
                            if isinstance(sub, dict):
                                sub["href"] = fix(sub.get("href"))
                    for feat in (menu.get("featured") or []):
                        if isinstance(feat, dict):
                            feat["href"] = fix(feat.get("href"))
    for c in (nav.get("ctas") or []):
        if isinstance(c, dict):
            c["href"] = fix(c.get("href"))

    footer = data.get("footer") if isinstance(data.get("footer"), dict) else {}
    if isinstance(footer.get("logo"), dict) and footer["logo"].get("href"):
        footer["logo"]["href"] = fix(footer["logo"].get("href"))
    for col in (footer.get("columns") or []):
        for ln in (col.get("links") or []):
            if isinstance(ln, dict):
                ln["href"] = fix(ln.get("href"))
    for s in (footer.get("social") or []):
        if isinstance(s, dict):
            s["href"] = fix(s.get("href"))
    legal = footer.get("legal") if isinstance(footer.get("legal"), dict) else None
    if legal:
        for ln in (legal.get("links") or []):
            if isinstance(ln, dict):
                ln["href"] = fix(ln.get("href"))
    nl = footer.get("newsletter") if isinstance(footer.get("newsletter"), dict) else None
    if nl and nl.get("action"):
        nl["action"] = fix(nl.get("action"))


def _resolve_logo_srcs(
    data: dict[str, Any],
    html_text: str,
    local_origin: str,
    base_url: str | None,
) -> None:
    """Map localhost-served / relative logo srcs back to their REAL remote URL.

    A "Save Page As, Complete" capture localizes assets, so a logo referenced by a
    bare filename resolves to the throwaway 127.0.0.1 server during extraction. We
    recover the genuine asset URL from the saved page itself: take the dominant
    absolute asset directory in the markup (the site's real CDN host) and re-join
    the logo filename onto it. `data:` URIs and already-absolute remote srcs are
    left untouched (so inline-SVG / CDN logos elsewhere are unaffected). No
    fabrication — the host comes straight from the page's other asset URLs.
    """
    import re
    from collections import Counter

    asset_urls = re.findall(
        r"https?://[^\s\"'()<>]+/[^\s\"'()<>/]+\.(?:svg|png|webp|jpe?g|avif|gif)",
        html_text,
        re.I,
    )
    dirs = Counter(u.split("?")[0].split("#")[0].rsplit("/", 1)[0] + "/" for u in asset_urls)
    cdn_base = dirs.most_common(1)[0][0] if dirs else ""
    site_base = (base_url.rstrip("/") + "/") if base_url else ""

    def fix(src: str | None) -> str:
        s = (src or "").strip()
        if not s or s.startswith("data:"):
            return s or ""
        is_local = bool(local_origin) and s.startswith(local_origin)
        is_rel = not s.startswith(("http://", "https://", "//"))
        if not (is_local or is_rel):
            return s
        fname = s.split("?")[0].split("#")[0].rstrip("/").rsplit("/", 1)[-1]
        if not fname:
            return s
        if cdn_base:
            return cdn_base + fname
        if site_base:
            return site_base + fname
        return s

    for scope in ("nav", "footer"):
        node = data.get(scope)
        if isinstance(node, dict) and isinstance(node.get("logo"), dict) and node["logo"].get("src"):
            node["logo"]["src"] = fix(node["logo"]["src"])


def extract_chrome_from_saved_page(
    html_path: str | Path,
    *,
    base_url: str | None = None,
    timeout_ms: int = 30000,
    log=print,
) -> dict[str, Any]:
    """Run the v2 browser extractor against a locally saved page (OFFLINE).

    Expects a "Save Page As, Complete" capture: an .html file with a sibling
    `*_files/` asset directory. We serve the folder containing the .html over a
    short-lived localhost static server so the page's CSS/JS load and computed
    styles + visibility filtering + the div.footer-* fallback all work without
    network. `base_url` (the real site origin) is used only to resolve any
    relative hrefs back to their true destinations.
    """
    import http.server
    import socketserver
    import threading
    from urllib.parse import quote

    html_path = Path(html_path).resolve()
    if not html_path.exists():
        raise FileNotFoundError(f"saved page not found: {html_path}")
    serve_dir = html_path.parent

    class _Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(serve_dir), **kw)

        def log_message(self, *a):  # silence per-request logging
            pass

    httpd = socketserver.TCPServer(("127.0.0.1", 0), _Handler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    local_origin = f"http://127.0.0.1:{port}"
    local_url = f"{local_origin}/{quote(html_path.name)}"
    log(f"[chrome-saved] serving {serve_dir} → {local_url}")
    try:
        data = extract_chrome_with_browser(local_url, timeout_ms=timeout_ms, log=log)
    finally:
        httpd.shutdown()
        httpd.server_close()

    # Record the real source, not the throwaway localhost URL.
    data["source_url"] = base_url or f"file://{html_path}"
    data["saved_page"] = str(html_path)
    # Recover genuine logo asset URLs (localized captures resolve them to the
    # throwaway 127.0.0.1 server) from the saved markup's real asset host.
    try:
        _resolve_logo_srcs(data, html_path.read_text(encoding="utf-8", errors="ignore"), local_origin, base_url)
    except OSError:
        pass
    if base_url:
        _resolve_hrefs(data, base_url)
    return data


def find_saved_page_for_brand(
    brand: str,
    *,
    project_dir: str | Path | None = None,
) -> Path | None:
    """Locate a saved "Save Page As, Complete" capture for a brand, if any.

    Searches (in priority order):
      - screenshots/<brand>/saved/*.html
      - screenshots/<brand>/**/*.html   (with a sibling "*_files" asset dir)
      - runs/<brand>/**/source.html
    A complete capture has an .html plus a sibling `<name>_files/` directory;
    those are strongly preferred. Returns the path to the .html or None.
    """
    root = Path(project_dir).resolve() if project_dir else Path(__file__).resolve().parents[2]

    def has_assets_dir(p: Path) -> bool:
        sib = p.with_name(p.stem + "_files")
        return sib.is_dir()

    search_roots = [root / "screenshots" / brand, root / "runs" / brand]
    candidates: list[Path] = []
    for base in search_roots:
        if not base.exists():
            continue
        candidates.extend(sorted(base.rglob("*.html")))

    # Strongest: an .html with a sibling *_files dir.
    complete = [p for p in candidates if has_assets_dir(p)]
    if complete:
        # Prefer the largest (homepage tends to be biggest), stable tie-break.
        complete.sort(key=lambda p: (p.stat().st_size, str(p)), reverse=True)
        return complete[0]

    # Next: an explicit source.html under runs/<brand>.
    for p in candidates:
        if p.name.lower() == "source.html":
            return p

    # Fall back to any html under a "saved" folder.
    saved = [p for p in candidates if "saved" in {part.lower() for part in p.parts}]
    if saved:
        saved.sort(key=lambda p: (p.stat().st_size, str(p)), reverse=True)
        return saved[0]
    return None


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
