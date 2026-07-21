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
import re
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
  // an ASIDE region inside a mega panel: the secondary rail that hosts either a
  // compact link group or the promo/feature card (fid4 2026-07). Class-name
  // families only — generic surface roles, never one brand's module hash.
  const ASIDE_CLS = /secondary|aside|sidebar|side-rail|featured|promo|spotlight|highlight|extra/i;
  // a promo/feature CARD object inside a panel (media + title + optional CTA)
  const CARD_CLS = /card|entry|promo|feature|banner|tile|spotlight|teaser/i;
  // small glyph inside a link/control (icon, not content imagery)
  const ICON_MAX = 48;

  // Compact icon source for a link/control: inline <svg> markup, a small <img>
  // src, or a CSS mask-image / background-image URL (mask icons paint the
  // element's backgroundColor through the mask shape — capture that ink too).
  // Returns null when the element carries no icon — NEVER fabricates one.
  const iconSource = (el) => {
    const svg = el.querySelector("svg");
    if (svg) {
      const o = outer_or(svg);
      if (o) {
        const r = svg.getBoundingClientRect();
        return { kind: "svg", svg: o, size: Math.round(Math.max(r.width, r.height)) || 0 };
      }
    }
    const img = el.querySelector("img");
    if (img) {
      const r = img.getBoundingClientRect();
      const w = r.width || px(getComputedStyle(img).width);
      const h = r.height || px(getComputedStyle(img).height);
      if ((w || h) && w <= ICON_MAX + 16 && h <= ICON_MAX + 16) {
        return { kind: "img", src: img.currentSrc || img.src || "",
                 alt: img.getAttribute("alt") || "",
                 size: Math.round(Math.max(w, h)) || 0 };
      }
    }
    const nodes = [el].concat(Array.from(el.querySelectorAll("*")).slice(0, 12));
    for (const n of nodes) {
      const s = getComputedStyle(n);
      const candidates = [
        ["mask", s.maskImage || s.webkitMaskImage || ""],
        ["bg", s.backgroundImage || ""],
      ];
      for (const [kind, v] of candidates) {
        if (!v || v === "none") continue;
        const m = v.match(/url\((["']?)(.*?)\1\)/i);
        if (!m || !m[2] || /^data:|gradient/i.test(m[2])) continue;
        const r = n.getBoundingClientRect();
        const size = Math.round(Math.max(r.width, r.height, px(s.width), px(s.height)));
        if (size > ICON_MAX + 32) continue;   // content imagery, not a glyph
        return { kind: kind, src: m[2].replace(/\\(.)/g, "$1"), size: size || 0,
                 ink: kind === "mask" ? s.backgroundColor : "" };
      }
    }
    return null;
  };

  // The link's own short DESCRIPTION line (menu-card anatomy: icon + title +
  // description). A descendant whose class names a description/subtitle role, or
  // the second distinct text node after the title. Returns { text, open } —
  // `open` is whether the description renders EXPANDED at rest (some menus keep
  // a featured group's descriptions visible and reveal the rest on link hover
  // via a grid-template-rows transition). null when the link has none.
  const linkDescription = (a, titleText) => {
    const d = a.querySelector("[class*='desc' i], [class*='subtitle' i], [class*='caption' i], p, small");
    // rest-state visibility: the nearest wrapper animating grid-template-rows —
    // 0px = collapsed until hover; >0 or none = visible at rest.
    const restOpen = (node) => {
      let n = node;
      for (let i = 0; i < 4 && n && n !== a.parentElement; i++) {
        const s = getComputedStyle(n);
        const g = s.gridTemplateRows || "";
        if (g && g !== "none" && g !== "auto") return px(g) > 0;
        n = n.parentElement;
      }
      return true;
    };
    if (d) {
      const t = collapse(d.textContent || "").slice(0, 200);
      if (t && t !== titleText) return { text: t, open: restOpen(d) };
    }
    const whole = collapse(a.textContent || "");
    if (titleText && whole.length > titleText.length + 4 && whole.indexOf(titleText) === 0) {
      return { text: whole.slice(titleText.length).trim().slice(0, 200), open: true };
    }
    return null;
  };

  // Does this node (a heading/group inside a panel) live in the panel's ASIDE
  // region? Walk its ancestor chain up to the panel; any hop whose class names a
  // secondary/aside/featured role marks the aside rail.
  const inAsideRegion = (node, panel) => {
    let n = node;
    while (n && n !== panel) {
      const cls = n.getAttribute && (n.getAttribute("class") || "");
      // A vertical-TAB layout wrapper (e.g. `global-nav-sidebar cl-tabs`) matches
      // the `sidebar` token but is a tabbed CONTENT layout, not a secondary rail —
      // its panels are the MAIN region (fix 2026-07). Skip such a wrapper: the rail
      // is captured separately as menu.sidebarTabs.
      if (ASIDE_CLS.test(cls) &&
          !(n.querySelector && n.querySelector("[role='tablist'], [role='tab']"))) {
        return true;
      }
      n = n.parentElement;
    }
    return false;
  };

  // A menu-card's DESCRIPTION line often sits OUTSIDE the title anchor (a sibling
  // <p> in the card wrapper: title link + description paragraph). linkDescription
  // only reads inside the anchor, so also look at the nearest card/list-item
  // container for a description/subtitle node that isn't itself a link (generic
  // across "title link + sibling description" card grammars). fix 2026-07.
  const cardDescription = (a, titleText) => {
    const inA = linkDescription(a, titleText);
    if (inA) return inA;
    // Climb a few levels from the title link and, at each wrapper, look for a
    // description/subtitle node that is not itself a link. The NEAREST wrapper
    // holding this card's own copy wins (a `card-title` <h3> holds none; its
    // `card-text-wrapper` parent holds the sibling <p>). Bounded climb so we never
    // reach a neighbouring card. Generic across "title link + sibling desc" cards.
    let n = a.parentElement;
    for (let i = 0; i < 5 && n; i++) {
      if (n.tagName !== "A") {
        const d = n.querySelector("[class*='desc' i], [class*='subtitle' i], [class*='caption' i], p, small");
        if (d && !d.closest("a[href]")) {
          const t = collapse(d.textContent || "").slice(0, 200);
          if (t && t !== titleText && t.indexOf(titleText) !== 0) {
            return { text: t, open: true };
          }
        }
      }
      n = n.parentElement;
    }
    return null;
  };

  // Harvest the panel's PROMO/FEATURE CARD (the right-side object): a bounded
  // non-link container carrying media + a title (and usually a CTA). Facts only
  // — image src, title, body, CTA label/href — nothing invented. Returns
  // { fact, el } so the column splitter can EXCLUDE the card's own heads/links
  // from the link-group harvest (the card is its own object, not a column).
  const harvestPanelCard = (panel, featuredSet) => {
    const cands = Array.from(panel.querySelectorAll("article, div, a, section")).filter((e) => {
      const cls = e.getAttribute("class") || "";
      if (!CARD_CLS.test(cls)) return false;
      if (!e.querySelector("img, picture, [style*='background-image']")) return false;
      const t = collapse(e.textContent || "");
      return t.length >= 8;
    });
    // keep the OUTERMOST card container only
    const outer = cands.filter((e) => !cands.some((o) => o !== e && o.contains(e)));
    if (!outer.length) return null;
    const card = outer[0];
    const img = card.querySelector("img");
    const titleEl = card.querySelector("h1,h2,h3,h4,h5,h6,[class*='title' i],strong,b");
    const title = titleEl ? anyLabel(titleEl) : "";
    // CTA: an anchor with a short label, or a cta-classed NON-anchor node (card
    // anatomies often render the affordance as a span inside one wrapping link).
    let cta = null;
    let href = card.tagName === "A" ? (card.getAttribute("href") || "") : "";
    for (const a of card.querySelectorAll("a[href]")) {
      const t = anyLabel(a);
      if (!href) href = a.getAttribute("href") || "";
      if (t && t.length <= 40 && t !== title) { cta = { label: t, href: a.getAttribute("href") || "" }; break; }
    }
    if (!cta) {
      const ctaEl = card.querySelector("[class*='cta' i], [class*='action' i]");
      if (ctaEl) {
        const t = collapse(ctaEl.textContent || "").slice(0, 40);
        if (t && t !== title) cta = { label: t, href: href };
      }
    }
    // body: a desc/body node whose text is neither the title nor the CTA label —
    // whole-card text concatenates title+cta ("…guessLearn more") and is NOT copy.
    let body = "";
    for (const bodyEl of card.querySelectorAll("p, [class*='desc' i], [class*='body' i]")) {
      const t = collapse(bodyEl.textContent || "").slice(0, 240);
      if (t && t !== title && (!cta || t !== cta.label) && !(title && t.indexOf(title) === 0)) {
        body = t;
        break;
      }
    }
    const cs = getComputedStyle(card);
    return { el: card, fact: {
      title: title,
      body: body,
      cta: cta,
      href: href,
      image: img ? { src: img.currentSrc || img.src || "", alt: img.getAttribute("alt") || "" } : null,
      area: (panel.querySelector("[role='tablist'], [role='tab']") ? "main"
             : (inAsideRegion(card, panel) ? "aside" : "main")),
      surface: { bg: cs.backgroundColor, radius: px(cs.borderTopLeftRadius) },
    } };
  };
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

    // A tabbed mega layout renders a vertical RAIL (role=tablist) beside its tab
    // panels; the panels are the MAIN content region, so the `sidebar` aside token
    // must not fire inside such a panel (the rail is captured as sidebarTabs). fix
    // 2026-07 — brands whose panels have no tablist keep the full aside heuristic.
    const hasRail = !!panel.querySelector("[role='tablist'], [role='tab']");
    const areaOf = (node) => (!hasRail && inAsideRegion(node, panel)) ? "aside" : "main";

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
    // the panel's promo/feature card (right-side object); its heads/links never
    // join the column groups (fid4 2026-07).
    const cardHit = harvestPanelCard(panel, featuredSet);
    const card = cardHit ? cardHit.fact : null;
    const cardEl = cardHit ? cardHit.el : null;
    // A heading candidate that WRAPS its own link (e.g. `<h3 class=card-title><a>
    // …</a></h3>`) is that CARD's title, not a column heading — promoting it split
    // every card into its own one-item column (fix 2026-07). Real group headings
    // (e.g. `<h2 class=…-sublinks-title>Marketing</h2>`) carry no link.
    const heads0 = Array.from(
      panel.querySelectorAll("h1,h2,h3,h4,h5,h6,[class*='title' i],[class*='heading' i]")
    ).filter((h) => !h.closest("a[href]") && !h.querySelector("a[href]") &&
                    !(cardEl && cardEl.contains(h)));
    const heads = heads0.filter((h) => !heads0.some((o) => o !== h && h.contains(o)));
    const allLinks = Array.from(panel.querySelectorAll("a[href]")).filter(
      (a) => !featuredSet.has(a) && !(cardEl && cardEl.contains(a))
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
          // per-link ANATOMY facts (fid4 2026-07): icon + description are part of
          // the menu-card grammar; captured only when the DOM carries them.
          const item = { label: t, href: href };
          const desc = cardDescription(a, t);
          if (desc) { item.description = desc.text; if (!desc.open) item.descriptionOnHover = true; }
          const ic = iconSource(a);
          if (ic) item.icon = ic;
          items.push(item);
        }
        if (items.length) {
          const col = { heading: anyLabel(head), links: items };
          // AREA fact (fid4 2026-07): which panel region the group lives in —
          // 'main' columns vs the 'aside' secondary rail (compact links / promo).
          col.area = areaOf(head);
          columns.push(col);
        }
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
        const item = { label: t, href: href };
        const desc = cardDescription(a, t);
        if (desc) { item.description = desc.text; if (!desc.open) item.descriptionOnHover = true; }
        const ic = iconSource(a);
        if (ic) item.icon = ic;
        items.push(item);
      }
      if (items.length) columns.push({ heading: "", links: items, area: "main" });
    }
    // an aside whose heading produced NO links but whose region holds the card
    // (e.g. a "Case Studies" rail that is only the promo card) still records its
    // heading as the card's group title.
    if (card && !card.groupHeading) {
      for (const h of heads) {
        if (inAsideRegion(h, panel) && !columns.some((c) => c.heading === anyLabel(h))) {
          card.groupHeading = anyLabel(h);
          break;
        }
      }
    }
    if (!columns.length && !featured.length && !card) return null;
    const out = { columns: columns.slice(0, 16), featured: featured.slice(0, 12) };
    if (card) out.card = card;
    // SIDEBAR RAIL (fix 2026-07): a vertical category rail rendered as a tablist
    // inside the panel (e.g. "By Use Case / By Team Size / Why HubSpot?"). Captured
    // as ordered labels so the renderer can draw the left rail; brands without a
    // tablist rail get no key (byte-identical). Structure-from-DOM — the panels are
    // present-but-hidden, so this reads straight from markup, no hover.
    const railBtns = Array.from(panel.querySelectorAll("[role='tab']"));
    const railSeen = new Set();
    const sidebarTabs = [];
    for (const rb of railBtns) {
      const t = anyLabel(rb);
      const k = t.toLowerCase();
      if (!t || t.length > 40 || railSeen.has(k)) continue;
      railSeen.add(k);
      sidebarTabs.push(t);
    }
    if (sidebarTabs.length >= 2) out.sidebarTabs = sidebarTabs.slice(0, 8);
    return out;
  };

  // ---- mega-panel MOTION + GEOMETRY facts (computed styles; brand-agnostic) --
  // Transition/animation declarations are readable from computed styles even
  // while the panel is hidden — capture them as structured facts (durations/
  // easings/hidden-state transform) so the renderer can reproduce the open/close
  // choreography without guessing. Geometry (padding, aside split, border) reads
  // from the same computed styles; rect-dependent numbers stay 0 when hidden and
  // are re-measured in the OPEN state by the Playwright pass.
  const transitionFact = (el) => {
    if (!el) return null;
    const s = getComputedStyle(el);
    const t = s.transitionProperty && s.transitionProperty !== "all" ? {
      property: s.transitionProperty,
      duration: s.transitionDuration,
      easing: s.transitionTimingFunction,
      delay: s.transitionDelay,
    } : (s.transitionDuration && s.transitionDuration !== "0s" ? {
      property: s.transitionProperty || "all",
      duration: s.transitionDuration,
      easing: s.transitionTimingFunction,
      delay: s.transitionDelay,
    } : null);
    return t;
  };

  const harvestPanelFacts = (linkEl) => {
    let controls = linkEl.getAttribute("aria-controls") || "";
    if (!controls) {
      const item = (linkEl.parentElement || linkEl).closest(
        "li, [class*='nav-item' i], [class*='nav-tab' i], [class*='menu-item' i], [class*='navLink' i]");
      const tog = item && item.querySelector("[aria-controls]");
      if (tog) controls = tog.getAttribute("aria-controls") || "";
    }
    const panel = controls ? document.getElementById(controls) : null;
    if (!panel) return null;
    const ps = getComputedStyle(panel);
    const facts = {
      _provenance: "getComputedStyle on the (hidden) mega panel from saved DOM",
      surface: {
        bg: ps.backgroundColor,
        borderTop: ps.borderTopWidth !== "0px" ? (ps.borderTopWidth + " " + ps.borderTopColor) : "",
        radius: px(ps.borderTopLeftRadius),
        maxHeight: ps.maxHeight !== "none" ? ps.maxHeight : "",
      },
      hiddenState: { opacity: ps.opacity, transform: ps.transform !== "none" ? ps.transform : "" },
      motion: {},
    };
    const pt = transitionFact(panel);
    if (pt) facts.motion.panel = pt;
    // the first link + its description reveal + the group title define the
    // interaction family inside the panel.
    const link0 = panel.querySelector("a[href]");
    if (link0) {
      const lt = transitionFact(link0);
      if (lt) facts.motion.link = lt;
      const ls = getComputedStyle(link0);
      facts.link = {
        padding: ls.padding, radius: px(ls.borderTopLeftRadius),
        fontSize: px(ls.fontSize), fontWeight: ls.fontWeight, color: ls.color,
      };
      const hb = hoverBg(link0);
      if (hb) facts.link.hoverBg = hb;
      const desc = link0.querySelector("[class*='desc' i]");
      if (desc) {
        const dt = transitionFact(desc) || transitionFact(desc.firstElementChild);
        if (dt) facts.motion.description = dt;
      }
    }
    const title0 = Array.from(panel.querySelectorAll("h1,h2,h3,h4,h5,h6,span,[class*='title' i]"))
      .find((h) => !h.closest("a[href]") && collapse(h.textContent || ""));
    if (title0) {
      const ts = getComputedStyle(title0);
      facts.groupTitle = {
        fontSize: px(ts.fontSize), fontWeight: ts.fontWeight, color: ts.color,
        letterSpacing: ts.letterSpacing, textTransform: ts.textTransform,
        fontFamily: ts.fontFamily,
      };
    }
    // aside rail (secondary region): border split + width fraction come from CSS
    const aside = Array.from(panel.querySelectorAll("div, section")).find((e) =>
      ASIDE_CLS.test(e.getAttribute("class") || "") && e.parentElement &&
      e.parentElement !== panel && panel.contains(e) &&
      !CARD_CLS.test(e.getAttribute("class") || ""));
    if (aside) {
      const as = getComputedStyle(aside);
      facts.aside = {
        borderLeft: as.borderLeftWidth !== "0px" ? (as.borderLeftWidth + " " + as.borderLeftColor) : "",
        maxWidth: as.maxWidth !== "none" ? as.maxWidth : "",
        paddingLeft: px(as.paddingLeft),
      };
    }
    // chevron / caret rotation (the trigger's own affordance)
    const item = (linkEl.parentElement || linkEl).closest("li, [class*='nav-item' i], [class*='navLink' i]") || linkEl.parentElement;
    const chev = (item || linkEl).querySelector("svg, [class*='chevron' i], [class*='caret' i], [class*='arrow' i]");
    if (chev) {
      const ct = transitionFact(chev);
      if (ct) facts.motion.chevron = ct;
    }
    return facts;
  };

  // measured background-color a :hover rule would apply to el ("" when none) —
  // same stylesheet scan as hoverColor but for the surface wash.
  const hoverBg = (el) => {
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
        const col = rule.style && rule.style.getPropertyValue("background-color");
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
  const outer_or = (svg) => {
    let o = svg.outerHTML || "";
    // Resolve a shared-sprite <use href="#id"> reference into a STANDALONE svg: the
    // <symbol id> lives elsewhere in the document (a hidden sprite map), so a bare
    // <use> paints NOTHING once extracted. Inline the referenced symbol's viewBox +
    // children as a single-ink (currentColor) svg so it materializes as real glyph
    // artwork. Generic — social glyphs, carets, any sprite icon. fix 2026-07.
    try {
      const use = svg.querySelector("use");
      const ownArt = svg.querySelector("path,polygon,circle,rect,ellipse,line,polyline,g");
      if (use && !ownArt) {
        let ref = use.getAttribute("href") || use.getAttribute("xlink:href") || "";
        const hash = ref.indexOf("#");
        const sym = hash >= 0 ? document.getElementById(ref.slice(hash + 1)) : null;
        if (sym && /symbol/i.test(sym.tagName) && sym.innerHTML.trim()) {
          const vb = sym.getAttribute("viewBox") || svg.getAttribute("viewBox") || "0 0 24 24";
          o = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="' + vb +
              '" fill="currentColor">' + sym.innerHTML + '</svg>';
        }
      }
    } catch (e) { /* fall back to the raw outerHTML */ }
    return o.length <= 12000 ? o : "";
  };
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
      // A logo LINK wraps only its mark — never a bar-wide layout container that
      // also holds the primary nav tabs / CTAs. Generic guard (fix 2026-07):
      // class substrings like `-burger-logo-slide-left` make a full-width bar
      // wrapper match `[class*='logo']`; with no ancestor <a> the anchor would
      // become that container and the main loop's `logoAnchor.contains(el)` would
      // then swallow every real tab/CTA. Reject any candidate that itself holds
      // more than one link/button (a mark wrapper holds none).
      const a0 = el.closest("a");
      if (!a0) {
        const innerActionable = el.querySelectorAll("a[href], button").length;
        if (innerActionable > 1) continue;
      }
      const a = a0 || el;
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
          // measured box geometry (2026-07): without these the composer fell back
          // to a too-narrow generic chip and could not wire the button's real size.
          paddingTop: px(s.paddingTop),
          paddingBottom: px(s.paddingBottom),
          paddingLeft: px(s.paddingLeft),
          paddingRight: px(s.paddingRight),
          height: Math.round(el.getBoundingClientRect().height),
          fontSize: px(s.fontSize),
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

    // Attach captured mega-menu (columns + featured + aside card) to each PRIMARY
    // tab that owns a dropdown. Read straight from the (hidden) DOM panel — no hover.
    let megaPanelFacts = null;
    for (const l of navLinks) {
      if (l.tier !== "primary" || !l._el) continue;
      const menu = harvestMenu(l._el);
      if (menu) {
        l.menu = menu;
        // panel-level geometry/typography/motion facts (fid4 2026-07): the panel
        // grammar is shared across tabs — keep the FIRST tab's facts as the
        // family spec; per-tab structure lives on each l.menu.
        if (!megaPanelFacts) megaPanelFacts = harvestPanelFacts(l._el);
      }
    }

    // ---- bar AFFORDANCES (fid15 2026-07) --------------------------------------
    // trigger chevron: the small trailing glyph inside a dropdown trigger. Harvested
    // as artwork (inline svg) + geometry (size, gap to the label) + the OPEN-state
    // transform/motion — measured by flipping aria-expanded (CSS attribute selectors
    // respond without the site's JS; restored immediately).
    const triggerChevron = (el) => {
      const svgs = Array.from(el.querySelectorAll("svg")).filter(isVisible);
      if (!svgs.length) return null;
      // the chevron is the LAST small svg (a leading icon glyph would come first)
      const svg = svgs[svgs.length - 1];
      const r = svg.getBoundingClientRect();
      if (Math.max(r.width, r.height) > ICON_MAX) return null;
      const o = outer_or(svg);
      if (!o) return null;
      const fact = { kind: "svg", svg: o,
                     box: { w: Math.round(r.width), h: Math.round(r.height) } };
      // gap label→glyph: prefer the trigger's own flex gap; else geometry against
      // the last text-bearing sibling before the svg.
      const es = getComputedStyle(el);
      const g = es.columnGap && es.columnGap !== "normal" ? px(es.columnGap) : 0;
      if (g) fact.gap = g;
      else {
        let prev = svg.previousSibling, right = null;
        while (prev) {
          if (prev.nodeType === 1) { right = prev.getBoundingClientRect().right; break; }
          if (prev.nodeType === 3 && prev.textContent.trim()) {
            const range = document.createRange(); range.selectNodeContents(prev);
            const rr = range.getBoundingClientRect();
            if (rr.width) { right = rr.right; break; }
          }
          prev = prev.previousSibling;
        }
        if (right !== null) fact.gap = Math.max(0, Math.round(r.left - right));
      }
      const ss = getComputedStyle(svg);
      if (ss.transition && ss.transition !== "all 0s ease 0s") fact.transition = ss.transition;
      // OPEN-state transform: flip the trigger's aria-expanded and re-read.
      const had = el.getAttribute("aria-expanded");
      if (had !== null) {
        try {
          el.setAttribute("aria-expanded", "true");
          const ot = getComputedStyle(svg).transform;
          if (ot && ot !== "none" && ot !== ss.transform) fact.openTransform = ot;
        } finally { el.setAttribute("aria-expanded", had); }
      }
      return fact;
    };
    let triggerFacts = null;
    for (const l of navLinks) {
      if (!l.menu || !l._el) continue;
      // The chevron glyph lives on the tab's TOGGLE BUTTON, a sibling of the
      // title span (fix 2026-07) — search the tab item container, not just the
      // label span (which carries no svg), so menu-owning tabs harvest the caret.
      const trigEl = l._el.closest(
        "li, [class*='nav-tab' i], [class*='nav-item' i], [class*='navLink' i]") || l._el;
      const ch = triggerChevron(trigEl);
      if (ch) { if (!triggerFacts) triggerFacts = { chevron: ch }; l.hasChevron = true; }
    }

    // in-bar UTILITY controls: entries in the SAME row as the primary tabs but
    // OUTSIDE the primary list container (trailing cluster — account links,
    // locale switchers). Recognized structurally: the primary-list container is
    // the LCA of the menu-owning tabs (fallback: of all primary entries); a
    // same-row entry whose element sits outside that container and to its right
    // is a utility control, never a nav destination. Its anatomy is harvested:
    // leading glyph, dropdown-ness (aria-expanded w/o a mega panel), chevron.
    const menuTabs = navLinks.filter((l) => l.tier === "primary" && l.menu && l._el);
    const rowTabs = menuTabs.length >= 1 ? menuTabs
      : navLinks.filter((l) => l.tier === "primary" && l._el);
    let mainList = null;
    if (rowTabs.length >= 2) mainList = lca(rowTabs[0]._el, rowTabs[rowTabs.length - 1]._el);
    else if (rowTabs.length === 1) mainList = rowTabs[0]._el.parentElement;
    if (mainList) {
      const mr = mainList.getBoundingClientRect();
      for (const l of navLinks) {
        if (l.tier !== "primary" || !l._el || l.menu) continue;
        const r = l._el.getBoundingClientRect();
        if (mainList.contains(l._el) || r.left < mr.right - 4) continue;
        l.tier = "utility";
        l.bar = "trailing";
        const ic = iconSource(l._el);
        if (ic) l.icon = ic;
        const expandable = l._el.getAttribute("aria-expanded") !== null ||
                           l._el.getAttribute("aria-haspopup") !== null;
        l.kind = expandable ? "dropdown" : "link";
        const aria = l._el.getAttribute("aria-label") || "";
        if (aria) l.ariaLabel = aria;
        if (expandable) {
          const ch = triggerChevron(l._el);
          if (ch) l.chevron = ch;
          // collapsed presentation: the trigger's VISIBLE inline label (aria-label
          // is the accessible phrase; the bar shows only this short text, if any).
          const spans = Array.from(l._el.querySelectorAll("span")).filter(isVisible);
          const shown = spans.map((sp) => (sp.textContent || "").trim())
            .filter((t) => t && t.length <= 24);
          if (shown.length) l.collapsedLabel = shown[0];
        }
        // ROLE from the source's own semantics (web-platform conventions, not
        // content vocabulary): an href routed at an auth endpoint marks login;
        // an accessible name naming language/locale selection marks language.
        const hrefL = (l.href || "").toLowerCase();
        const ariaL = aria.toLowerCase();
        if (/sign-?in|log-?in|account/.test(hrefL)) l.role = "login";
        else if (/language|locale/.test(ariaL)) l.role = "language";
      }
    }

    // Utility-item DROPDOWN items: the collapsed submenu a locale/account/about
    // control opens. The panel is present-but-hidden in the saved DOM (portals on
    // open), so read the associated list straight from markup via aria-controls
    // (the control OR a toggle in its item points at the panel id). Structure only —
    // the open-state PAINT (w/h/bg) is not in a static snapshot, so the panel stays
    // notObserved (the author marks dropdownNotObserved). fix 2026-07.
    const utilDropdownItems = (el) => {
      let controls = el.getAttribute("aria-controls") || "";
      const item = (el.parentElement || el).closest(
        "li, [class*='nav-item' i], [class*='navLink' i], [class*='has-dropdown' i]");
      if (!controls && item) {
        const tog = item.querySelector("[aria-controls]");
        if (tog) controls = tog.getAttribute("aria-controls") || "";
      }
      const panel = controls ? document.getElementById(controls) : null;
      const scope = panel || (item && item.querySelector("ul, [role='menu'], [class*='submenu' i], [class*='dropdown' i]"));
      if (!scope || scope.contains(el) && scope === el) return [];
      const items = [];
      const seen = new Set();
      for (const a of scope.querySelectorAll("a[href]")) {
        const t = anyLabel(a);
        const href = a.getAttribute("href") || "";
        const k = (t + "|" + href).toLowerCase();
        if (!t || t.length > 60 || seen.has(k)) continue;
        seen.add(k);
        const it = { label: t, href: href };
        const lang = a.getAttribute("lang") || a.getAttribute("hreflang");
        if (lang) it.lang = lang;
        if ((a.getAttribute("aria-current") || "").trim()) it.current = true;
        items.push(it);
      }
      return items.slice(0, 24);
    };
    // Annotate EVERY utility-tier control with its anatomy (kind/role/icon/chevron/
    // collapsed label/dropdown items) — not only the reclassified trailing cluster.
    // The top-bar (leading) utility run carries the locale switcher + support links.
    for (const l of navLinks) {
      if (l.tier !== "utility" || !l._el) continue;
      if (!l.icon) { const ic = iconSource(l._el); if (ic) l.icon = ic; }
      const aria = l._el.getAttribute("aria-label") || "";
      if (aria && !l.ariaLabel) l.ariaLabel = aria;
      const expandable = l._el.getAttribute("aria-expanded") !== null ||
                         l._el.getAttribute("aria-haspopup") !== null ||
                         !!(l._el.closest("[class*='has-dropdown' i], [class*='hasSubNav' i]"));
      if (!l.kind) l.kind = expandable ? "dropdown" : "link";
      if (l.kind === "dropdown") {
        if (!l.chevron) { const ch = triggerChevron(
          l._el.closest("li, [class*='navLink' i], [class*='nav-item' i]") || l._el);
          if (ch) l.chevron = ch; }
        if (!l.collapsedLabel) {
          const spans = Array.from(l._el.querySelectorAll("span")).filter(isVisible);
          const shown = spans.map((sp) => (sp.textContent || "").trim())
            .filter((t) => t && t.length <= 24);
          if (shown.length) l.collapsedLabel = shown[0];
        }
        if (!l.dropdown || !(l.dropdown.items || []).length) {
          const items = utilDropdownItems(l._el);
          if (items.length) l.dropdown = { items: items, panelNotObserved: true };
        }
      }
      const hrefL = (l.href || "").toLowerCase();
      const ariaL = (aria + " " + (l.label || "")).toLowerCase();
      if (!l.role) {
        if (/sign-?in|log-?in|account/.test(hrefL)) l.role = "login";
        else if (/language|locale|english|español|deutsch|français|português/.test(ariaL)) l.role = "language";
        else if (/about/.test((l.label || "").toLowerCase())) l.role = "menu";
      }
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
    // shared mega-panel grammar facts (surface/motion/typography, fid4 2026-07)
    if (megaPanelFacts) measured.megaPanel = megaPanelFacts;
    // dropdown-trigger affordance family facts (chevron artwork/geometry/motion,
    // fid15 2026-07) — first menu-owning tab speaks for the family.
    if (triggerFacts) measured.trigger = triggerFacts;

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
      const entry = { network: net || "link", kind: kind, href: href, label: collapse(label(a)) || collapse(aria) || net, _el: a };
      // ICON SOURCE fact (fid4 2026-07): the actual glyph the page renders —
      // inline <svg> markup, an <img> src, or a CSS mask/background URL — plus
      // the container box (size/radius/fills). Captured only when present; the
      // curate step downloads/binds the real artwork from these facts.
      const ic = iconSource(a);
      if (ic) {
        const as = getComputedStyle(a);
        const box = a.getBoundingClientRect();
        entry.icon = ic;
        entry.box = {
          width: Math.round(box.width) || px(as.width),
          height: Math.round(box.height) || px(as.height),
          radius: px(as.borderTopLeftRadius),
          bg: as.backgroundColor,
        };
      }
      social.push(entry);
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

    // ---- BOTTOM BAR structure (fid4 2026-07, brand-agnostic) -----------------
    // The footer's closing region — copyright/disclaimer, store badges, divider
    // rule, policy-link row, social cluster — captured as STRUCTURED facts from
    // DOM geometry so the renderer reproduces the row composition instead of
    // guessing. Region = the common ancestor of the © text and the last policy/
    // social element, clamped to a direct child of the footer's inner stack.
    let bottomBar = null;
    {
      // region anchors: the © line + the social cluster are the two most reliable
      // BOTTOM landmarks (keyword-matched "legal" links can live up in the link
      // columns, which would balloon the LCA to the whole footer).
      const anchors = [legalTextEl, firstSocialEl].filter(Boolean);
      if (anchors.length < 2 && firstLegalLinkEl) anchors.push(firstLegalLinkEl);
      let region = null;
      if (anchors.length >= 2) {
        region = anchors.reduce((acc, el) => (acc ? lca(acc, el) : el), null);
      } else if (anchors.length === 1) {
        region = anchors[0].parentElement;
      }
      if (region === footer) {
        // prefer the © text's own top-level block so the region is the bottom
        // stack, not the whole footer
        let n = legalTextEl || firstLegalLinkEl;
        while (n && n.parentElement && n.parentElement !== footer) n = n.parentElement;
        if (n && n !== footer) region = n;
      }
      if (region && footer.contains(region)) {
        const rs = getComputedStyle(region);
        // divider: an <hr> or a 1–2px-tall painted rule among the region's
        // descendants (between rows). Color = its painted background/border.
        let divider = null;
        for (const el of Array.from(region.querySelectorAll("hr, div, span")).slice(0, 60)) {
          const s = getComputedStyle(el);
          const r = el.getBoundingClientRect();
          const painted = !transparent(s.backgroundColor) ? s.backgroundColor
            : (px(s.borderTopWidth) > 0 && !transparent(s.borderTopColor) ? s.borderTopColor : "");
          if (r.height >= 0.5 && r.height <= 2.5 && r.width >= 200 && painted) {
            divider = { present: true, color: painted,
                        opacity: parseFloat(s.opacity || "1") };
            break;
          }
        }
        // row composition: the region's direct children (skip the divider) in
        // order, each classified by what it CONTAINS — copyright/disclaimer
        // text, store badges, policy links, social icons. Alignment facts come
        // from each row's own computed flex layout.
        const rowKind = (el) => {
          const kinds = [];
          if (legalTextEl && el.contains(legalTextEl)) kinds.push("copyright");
          const badges = Array.from(el.querySelectorAll("a[href]")).filter((a) =>
            /app.?store|play\.google|apps\.apple|google.?play/i.test(
              (a.getAttribute("href") || "") + " " + (a.getAttribute("aria-label") || "") +
              " " + (a.getAttribute("class") || "")));
          if (badges.length) kinds.push("store-badges");
          if (firstLegalLinkEl && el.contains(firstLegalLinkEl)) kinds.push("policy-links");
          if (firstSocialEl && el.contains(firstSocialEl)) kinds.push("social");
          if (!kinds.length && collapse(el.textContent || "")) kinds.push("text");
          return kinds;
        };
        const rows = [];
        for (const ch of Array.from(region.children)) {
          const s = getComputedStyle(ch);
          const r = ch.getBoundingClientRect();
          if (ch.tagName === "HR" || (r.height <= 2.5 && r.width >= 200)) {
            rows.push({ kinds: ["divider"] });
            continue;
          }
          if (r.height < 1) continue;
          rows.push({
            kinds: rowKind(ch),
            display: s.display,
            direction: s.flexDirection || "",
            justify: s.justifyContent || "",
            align: s.alignItems || "",
            gap: px((s.columnGap && s.columnGap !== "normal") ? s.columnGap : s.gap),
          });
        }
        // DISCLAIMER small-print: a second text block near the © line that is
        // NOT the © line itself (legal fine print — captured verbatim).
        let disclaimer = "";
        if (legalTextEl && legalTextEl.parentElement) {
          for (const sib of Array.from(legalTextEl.parentElement.children)) {
            if (sib === legalTextEl) continue;
            const t = collapse(sib.textContent || "");
            if (t && t.length >= 40 && !COPY.test(t) && !sib.querySelector("a[href]")) {
              disclaimer = t.slice(0, 600);
              break;
            }
          }
        }
        // STORE BADGES: app/play-store links with their real badge imagery.
        const storeBadges = [];
        for (const a of Array.from(region.querySelectorAll("a[href]"))) {
          const hay = (a.getAttribute("href") || "") + " " + (a.getAttribute("aria-label") || "") +
            " " + (a.getAttribute("class") || "");
          if (!/app.?store|play\.google|apps\.apple|google.?play/i.test(hay)) continue;
          const img = a.querySelector("img");
          storeBadges.push({
            href: a.getAttribute("href") || "",
            label: collapse(a.getAttribute("aria-label") || label(a)).slice(0, 80),
            img: img ? { src: img.currentSrc || img.src || "", alt: img.getAttribute("alt") || "" } : null,
          });
        }
        // POLICY LINKS scoped to the region's own list (the visually-present
        // bottom row) — keyword-matched links living up in the columns stay in
        // legal.links but NOT here. Resolution: keyword-matched links INSIDE the
        // region vote for their closest ul/ol/nav list; the winning list's links
        // ship IN ORDER (so non-keyword members of the same row, e.g. "Imprint"
        // localizations, are kept); regions with no list fall back to the
        // keyword-matched region links themselves.
        const policyLinks = [];
        {
          const seenP = new Set();
          const inRegionLegal = Array.from(region.querySelectorAll("a[href]"))
            .filter((a) => isVisible(a) && !socialNet(a.getAttribute("href") || ""))
            .filter((a) => LEGAL_LINK.test(collapse(label(a)) || ""));
          const listVotes = new Map();
          for (const a of inRegionLegal) {
            const list = a.closest("ul, ol, nav");
            if (list && region.contains(list)) {
              listVotes.set(list, (listVotes.get(list) || 0) + 1);
            }
          }
          let bestList = null, bestVotes = 0;
          for (const [list, n] of listVotes) {
            if (n > bestVotes) { bestList = list; bestVotes = n; }
          }
          const pool = bestList
            ? Array.from(bestList.querySelectorAll("a[href]")).filter(isVisible)
            : inRegionLegal;
          for (const a of pool) {
            if (socialNet(a.getAttribute("href") || "")) continue;
            const t = collapse(label(a)) || collapse(a.getAttribute("aria-label") || "");
            if (!t) continue;
            const k = t.toLowerCase();
            if (seenP.has(k)) continue;
            seenP.add(k);
            policyLinks.push({ label: t, href: a.getAttribute("href") || "#" });
          }
        }
        // vertical breathing room above the bar (fid4): the measured distance from
        // the link-directory's bottom edge to the bottom region's top edge — part of
        // the footer's real height budget the generator must reproduce.
        let gapAbove = 0;
        {
          const regionTop = region.getBoundingClientRect().top;
          let colsBottom = 0;
          for (const h of headingEls) {
            const wrap = h.parentElement || h;
            const b = wrap.getBoundingClientRect().bottom;
            if (b < regionTop && b > colsBottom) colsBottom = b;
          }
          // fall back: the lowest link ABOVE the region
          if (!colsBottom) {
            for (const a of Array.from(footer.querySelectorAll("a[href]")).filter(isVisible)) {
              const b = a.getBoundingClientRect().bottom;
              if (b < regionTop && b > colsBottom) colsBottom = b;
            }
          }
          if (colsBottom) gapAbove = Math.max(0, Math.round(regionTop - colsBottom));
        }
        bottomBar = {
          _provenance: "DOM geometry + getComputedStyle over the footer's bottom region",
          divider: divider || { present: false },
          rows: rows.slice(0, 8),
          gap: px((rs.rowGap && rs.rowGap !== "normal") ? rs.rowGap : rs.gap),
          gapAbove: gapAbove,
          disclaimer: disclaimer,
          storeBadges: storeBadges.slice(0, 4),
          policyLinks: policyLinks.slice(0, 12),
        };
      }
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
      // WRAPPER GEOMETRY (fid4 2026-07): each physical wrapper's rect + WHICH
      // groups it stacks, clustered into visual tracks (x) and row bands (y) —
      // a wrapping 6-wrapper flex over 3 tracks renders as 2 row bands, and the
      // generator must reproduce that placement, not just the group count.
      const wrappers = [];
      for (const ch of kids) {
        const headsIn = gridHeads.filter((h) => ch.contains(h));
        if (!headsIn.length) continue;
        const r = ch.getBoundingClientRect();
        wrappers.push({
          groups: headsIn.map((h) => label(h)),
          x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width),
        });
      }
      // cluster x → track index, y → row index (tolerance: half a wrapper width / 40px)
      const xs = [];
      for (const w of wrappers.slice().sort((a, b) => a.x - b.x)) {
        if (!xs.length || Math.abs(w.x - xs[xs.length - 1]) > Math.max(40, w.w / 2)) xs.push(w.x);
      }
      const ys = [];
      for (const w of wrappers.slice().sort((a, b) => a.y - b.y)) {
        if (!ys.length || Math.abs(w.y - ys[ys.length - 1]) > 40) ys.push(w.y);
      }
      const nearest = (arr, v) => {
        let bi = 0;
        for (let i = 1; i < arr.length; i++) if (Math.abs(arr[i] - v) < Math.abs(arr[bi] - v)) bi = i;
        return bi;
      };
      for (const w of wrappers) {
        w.track = nearest(xs, w.x);
        w.row = nearest(ys, w.y);
      }
      fmeasured.grid = {
        display: cs.display,
        templateColumns: cs.gridTemplateColumns && cs.gridTemplateColumns !== "none" ? cs.gridTemplateColumns : "",
        columnGap: px((cs.columnGap && cs.columnGap !== "normal") ? cs.columnGap : cs.gap),
        rowGap: px((cs.rowGap && cs.rowGap !== "normal") ? cs.rowGap : cs.gap),
        columnCount: columns.length,
        wrapperCount: wrapperSizes.length,
        wrapperSizes: wrapperSizes,
        trackCount: xs.length,
        rowBandCount: ys.length,
        wrappers: wrappers,
      };
    } else {
      fmeasured.grid = { display: "", templateColumns: "", columnGap: 0, rowGap: 0, columnCount: columns.length };
    }
    if (headingEls.length) {
      const s = getComputedStyle(headingEls[0]);
      fmeasured.heading = { fontSize: px(s.fontSize), fontWeight: s.fontWeight, lineHeight: s.lineHeight, color: s.color, fontFamily: s.fontFamily,
        textTransform: s.textTransform, letterSpacing: s.letterSpacing };
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
      // VERTICAL RHYTHM (fid4 2026-07): the median top-to-top stride between
      // consecutive links in the same stack — the directory's real line rhythm
      // (line-height + list gap), so the generated column heights match the source.
      let list = flinkEl.parentElement;
      for (let i = 0; i < 4 && list; i++) {
        const anchors = Array.from(list.querySelectorAll("a[href]")).filter(isVisible);
        if (anchors.length >= 3) {
          const tops = anchors.map((a) => a.getBoundingClientRect().top)
            .sort((a, b) => a - b);
          const strides = [];
          for (let j = 1; j < tops.length; j++) {
            const d = tops[j] - tops[j - 1];
            if (d > 4 && d < 120) strides.push(d);
          }
          if (strides.length) {
            strides.sort((a, b) => a - b);
            fmeasured.link.rowStride =
              Math.round(strides[Math.floor(strides.length / 2)]);
          }
          break;
        }
        list = list.parentElement;
      }
    }
    // heading→first-link gap (the space under a column group heading)
    if (colHeads.length && fmeasured.heading) {
      const h0 = colHeads[0];
      const scope = h0.parentElement ? h0.parentElement : footer;
      const after = Array.from(scope.querySelectorAll("a[href]")).filter(isVisible)
        .map((a) => a.getBoundingClientRect().top)
        .filter((t) => t > h0.getBoundingClientRect().bottom - 1);
      if (after.length) {
        const gap = Math.round(Math.min(...after) - h0.getBoundingClientRect().bottom);
        if (gap >= 0 && gap < 80) fmeasured.heading.gapBelow = gap;
      }
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
      bottomBar: bottomBar,
      newsletter: newsletter,
      measured: fmeasured,
    };
  }

  return result;
};
"""


# ── OPEN-STATE mega-panel measurement (Playwright hover/click pass) ──────────
# The hidden-DOM harvest reads structure + declared transitions; THIS pass opens
# each panel for real and measures rendered geometry (panel rect/padding, the
# main/aside split, column boxes, the promo card box) plus a per-panel screenshot.
# Brand-agnostic: triggers are located by aria-controls (the same association the
# hidden harvest uses); sites without that association degrade to no open-state
# facts — never a guess.

_MEGA_TRIGGERS_JS = r"""
() => {
  const out = [];
  const seen = new Set();
  const header = document.querySelector("header[role='banner'], header, [class*='navbar' i], nav");
  if (!header) return out;
  for (const el of header.querySelectorAll("[aria-controls]")) {
    const id = el.getAttribute("aria-controls") || "";
    if (!id || seen.has(id)) continue;
    // trigger must be VISIBLE at this viewport (skips the mobile drawer's
    // hamburger duplicate, which is display:none at desktop width)
    const r = el.getBoundingClientRect();
    const s = getComputedStyle(el);
    if (r.width < 2 || r.height < 2 || s.display === "none" || s.visibility === "hidden") continue;
    const panel = document.getElementById(id);
    if (!panel || !panel.querySelector("a[href]")) continue;
    seen.add(id);
    const txt = (el.textContent || "").replace(/\s+/g, " ").trim().slice(0, 60);
    out.push({ label: txt, controls: id });
  }
  return out;
};
"""

_MEGA_OPEN_MEASURE_JS = r"""
(panelId) => {
  const px = (v) => { const n = parseFloat(v || "0"); return Number.isFinite(n) ? Math.round(n) : 0; };
  const panel = document.getElementById(panelId);
  if (!panel) return null;
  const s = getComputedStyle(panel);
  if (s.display === "none" || s.visibility === "hidden" || parseFloat(s.opacity || "1") < 0.5) {
    return { open: false };
  }
  const rect = (el) => { const r = el.getBoundingClientRect();
    return { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) }; };
  const pr = rect(panel);
  // a zero-size box is NOT an open panel (e.g. a mobile drawer forced visible
  // at desktop width still lays out to 0x0)
  if (pr.w < 40 || pr.h < 40) return { open: false };
  const ASIDE_CLS = /secondary|aside|sidebar|side-rail|featured|promo|spotlight|highlight|extra/i;
  const CARD_CLS = /card|entry|promo|feature|banner|tile|spotlight|teaser/i;
  // the content container: the deepest descendant that still spans >= 85% of the
  // panel and owns >= 2 children (padding read from it).
  let content = panel;
  for (let i = 0; i < 6; i++) {
    const kids = Array.from(content.children).filter((c) => c.getBoundingClientRect().height > 4);
    if (kids.length === 1 && kids[0].getBoundingClientRect().width >= pr.w * 0.85) {
      content = kids[0];
    } else break;
  }
  const cs = getComputedStyle(content);
  // aside region: a visible child (anywhere shallow) whose class names the rail
  let aside = null;
  for (const el of panel.querySelectorAll("div, section")) {
    const cls = el.getAttribute("class") || "";
    if (!ASIDE_CLS.test(cls) || CARD_CLS.test(cls)) continue;
    const r = el.getBoundingClientRect();
    if (r.width < 40 || r.height < 40) continue;
    aside = el;
    break;
  }
  // main-area GROUP boxes: elements owning a heading + links, direct structure
  const groups = [];
  for (const g of panel.querySelectorAll("div, section, li")) {
    const cls = g.getAttribute("class") || "";
    if (!/group|column|col\b/i.test(cls)) continue;
    if (groups.some((o) => o.el.contains(g))) continue;
    const anchors = Array.from(g.querySelectorAll("a[href]"));
    const r = g.getBoundingClientRect();
    if (!anchors.length || r.width < 40 || r.height < 20) continue;
    // how many LINK COLUMNS the group's grid renders (distinct link left-x)
    const lxs = [];
    for (const a of anchors) {
      const ar = a.getBoundingClientRect();
      if (ar.width < 8) continue;
      const x = Math.round(ar.x);
      if (!lxs.some((v) => Math.abs(v - x) < 24)) lxs.push(x);
    }
    groups.push({ el: g, rect: rect(g), links: anchors.length,
                  linkColumns: Math.max(1, lxs.length),
                  aside: !!(aside && aside.contains(g)) });
  }
  // promo card box
  let card = null;
  for (const c of panel.querySelectorAll("article, a, div")) {
    const cls = c.getAttribute("class") || "";
    if (!CARD_CLS.test(cls)) continue;
    if (!c.querySelector("img, picture")) continue;
    const r = c.getBoundingClientRect();
    if (r.width < 80 || r.height < 80) continue;
    card = rect(c);
    break;
  }
  const out = {
    open: true,
    panel: pr,
    padding: { top: px(cs.paddingTop), right: px(cs.paddingRight),
               bottom: px(cs.paddingBottom), left: px(cs.paddingLeft) },
    surface: { bg: getComputedStyle(panel).backgroundColor,
               radius: px(getComputedStyle(content).borderTopLeftRadius) },
    groups: groups.map((g) => ({ rect: g.rect, links: g.links,
                                 linkColumns: g.linkColumns, aside: g.aside })),
    card: card,
  };
  if (aside) {
    const ar = rect(aside);
    const as2 = getComputedStyle(aside);
    out.aside = { rect: ar, widthFraction: pr.w ? +(ar.w / pr.w).toFixed(3) : 0,
                  borderLeft: as2.borderLeftWidth !== "0px"
                    ? (as2.borderLeftWidth + " " + as2.borderLeftColor) : "" };
  }
  // main column split: distinct left x-positions of NON-aside groups
  const xs = [...new Set(out.groups.filter((g) => !g.aside).map((g) => g.rect.x))];
  out.mainColumnCount = xs.length;
  return out;
};
"""


# Force-open fallback for saved pages: the framework that toggles [hidden] /
# aria-expanded doesn't hydrate offline, so hover/click never expands the panel.
# Forcing = removing the DECLARED hidden state (hidden attr, display:none,
# visibility, opacity, transform) on the panel and any suppressing ancestors so
# the CSS-defined open layout paints. Geometry measured this way is the real
# stylesheet layout — nothing synthetic. Every touched node is tagged so the
# restore pass can undo it exactly.
_MEGA_FORCE_JS = r"""
(panelId) => {
  const px = (v) => { const n = parseFloat(v || "0"); return Number.isFinite(n) ? n : 0; };
  const panel = document.getElementById(panelId);
  if (!panel) return false;
  const force = (el) => {
    if (el.getAttribute("data-cx-forced") != null) return;
    el.setAttribute("data-cx-forced", el.hasAttribute("hidden") ? "h" : "");
    el.setAttribute("data-cx-style", el.getAttribute("style") || "");
    el.removeAttribute("hidden");
    const s = getComputedStyle(el);
    if (s.display === "none") el.style.display = "block";
    if (s.visibility === "hidden" || s.visibility === "collapse") el.style.visibility = "visible";
    if (parseFloat(s.opacity || "1") < 0.5) el.style.opacity = "1";
    if (s.transform && s.transform !== "none") el.style.transform = "none";
    if (s.maxHeight !== "none" && px(s.maxHeight) < 8) el.style.maxHeight = "none";
  };
  // ancestors that suppress paint must be forced too (deepest last)
  const chain = [panel];
  let anc = panel.parentElement;
  for (let i = 0; anc && anc !== document.body && i < 5; i++) {
    const s = getComputedStyle(anc);
    if (anc.hasAttribute("hidden") || s.display === "none" ||
        s.visibility === "hidden" || parseFloat(s.opacity || "1") < 0.5) {
      chain.push(anc);
    }
    anc = anc.parentElement;
  }
  chain.reverse().forEach(force);
  const trig = document.querySelector('[aria-controls="' + (window.CSS && CSS.escape ? CSS.escape(panelId) : panelId) + '"]');
  if (trig) {
    if (trig.getAttribute("data-cx-expanded") == null) {
      trig.setAttribute("data-cx-expanded", trig.getAttribute("aria-expanded") || "");
    }
    trig.setAttribute("aria-expanded", "true");
  }
  return true;
};
"""

_MEGA_RESTORE_JS = r"""
() => {
  for (const el of document.querySelectorAll("[data-cx-forced]")) {
    const wasHidden = (el.getAttribute("data-cx-forced") || "").indexOf("h") >= 0;
    const style = el.getAttribute("data-cx-style") || "";
    if (style) el.setAttribute("style", style); else el.removeAttribute("style");
    if (wasHidden) el.setAttribute("hidden", "");
    el.removeAttribute("data-cx-forced");
    el.removeAttribute("data-cx-style");
  }
  for (const t of document.querySelectorAll("[data-cx-expanded]")) {
    const prev = t.getAttribute("data-cx-expanded") || "";
    if (prev) t.setAttribute("aria-expanded", prev); else t.removeAttribute("aria-expanded");
    t.removeAttribute("data-cx-expanded");
  }
};
"""


def measure_open_meganav(
    page,
    *,
    shots_dir: Path | None = None,
    shot_prefix: str = "chrome-mega",
    log=print,
) -> list[dict[str, Any]]:
    """Open every aria-controls nav panel in turn (hover, then click, then a
    force-open DOM fallback for non-hydrating saved pages), measure the RENDERED
    open-state geometry, and screenshot the open panel (viewport clip spanning
    the bar + panel). Returns per-item facts:
    ``[{label, controls, open, forced?, panel, padding, groups, aside?, card?, shot?}]``.
    Sites with no aria-controls triggers return [] — degrade, never invent."""
    # evidence hygiene: hide fixed/sticky cookie-consent overlays so panel shots
    # capture the chrome, not the banner (display state only — no data change)
    try:
        page.evaluate(
            """() => {
  for (const el of document.querySelectorAll("[class*='cookie' i], [id*='cookie' i], [aria-label*='cookie' i]")) {
    const s = getComputedStyle(el);
    if (s.position === 'fixed' || s.position === 'sticky') el.style.display = 'none';
  }
}"""
        )
    except Exception:
        pass
    triggers = page.evaluate(_MEGA_TRIGGERS_JS) or []
    out: list[dict[str, Any]] = []
    for i, trig in enumerate(triggers):
        controls = trig.get("controls") or ""
        if not controls:
            continue
        sel = f'[aria-controls="{controls}"]'
        item: dict[str, Any] = {"label": trig.get("label") or "", "controls": controls}
        facts = None
        try:
            el = page.locator(sel).first
            el.hover(timeout=2500)
            page.wait_for_timeout(450)
            facts = page.evaluate(_MEGA_OPEN_MEASURE_JS, controls)
            if not (facts and facts.get("open")):
                el.click(timeout=2500)
                page.wait_for_timeout(450)
                facts = page.evaluate(_MEGA_OPEN_MEASURE_JS, controls)
        except Exception:
            facts = None  # interaction can't open it — fall through to force mode
        try:
            if not (facts and facts.get("open")):
                if page.evaluate(_MEGA_FORCE_JS, controls):
                    page.wait_for_timeout(150)
                    facts = page.evaluate(_MEGA_OPEN_MEASURE_JS, controls)
                    if facts and facts.get("open"):
                        item["forced"] = True
            if facts and facts.get("open"):
                item.update(facts)
                if shots_dir is not None:
                    shots_dir.mkdir(parents=True, exist_ok=True)
                    slug = re.sub(r"[^a-z0-9]+", "-", (item["label"] or f"item-{i}").lower()).strip("-") or f"item-{i}"
                    shot = shots_dir / f"{shot_prefix}-{i}-{slug}.png"
                    pr = facts["panel"]
                    vp = page.viewport_size or {"width": 1440, "height": 1024}
                    clip = {
                        "x": 0,
                        "y": 0,
                        "width": vp["width"],
                        "height": max(1, min(vp["height"], pr["y"] + pr["h"] + 24)),
                    }
                    page.screenshot(path=str(shot), clip=clip)
                    item["shot"] = shot.name
                log(f"[chrome-mega] '{item['label']}' open{' (forced)' if item.get('forced') else ''}: "
                    f"panel {facts['panel']['w']}x{facts['panel']['h']} "
                    f"groups={len(facts.get('groups') or [])} aside={'yes' if facts.get('aside') else 'no'} "
                    f"card={'yes' if facts.get('card') else 'no'}")
            else:
                item["open"] = False
                log(f"[chrome-mega] '{item['label']}': panel did not open (hover+click+force)")
        except Exception as exc:  # keep the extraction alive — this pass is additive
            item["open"] = False
            item["error"] = f"{type(exc).__name__}: {exc}"
            log(f"[chrome-mega] '{trig.get('label')}' failed: {item['error']}")
        finally:
            # undo any forcing + close before the next tab
            try:
                page.evaluate(_MEGA_RESTORE_JS)
                page.keyboard.press("Escape")
                page.mouse.move(4, 4)
                page.wait_for_timeout(200)
            except Exception:
                pass
        out.append(item)
    return out


# ── bar affordances LIVE pass (fid15 2026-07) ────────────────────────────────
# The saved snapshot renders the bar's rest state only: the utility banner may be
# dismissed at capture time, and dropdown PANELS that portal on open (locale
# menus) never exist in the static DOM. This pass runs against the live page,
# harvests the banner's full anatomy (message / cta link / close glyph) and each
# in-bar utility dropdown's OPEN state (items + panel presentation + motion), and
# screenshots the states. Additive: sites without these controls return {}.

_BANNER_HARVEST_JS = r"""
() => {
  const px = (v) => { const n = parseFloat(v); return isNaN(n) ? 0 : Math.round(n); };
  const isVisible = (el) => {
    const s = getComputedStyle(el);
    if (s.display === "none" || s.visibility === "hidden") return false;
    const r = el.getBoundingClientRect();
    return r.width > 1 && r.height > 1;
  };
  // BACKDROP-AWARE paint resolution (W1, stress-playbook 2026-07): a strip's own
  // backgroundColor may be semi-transparent — on the live page it composites over
  // its ancestors' paint (e.g. a dark page cover), and THAT composite is the color
  // the eye sees. Re-hosting the raw alpha value over a light page shifts the hue
  // and kills contrast. Walk up from the element alpha-compositing each ancestor's
  // backgroundColor until opaque (white page default), and record the result.
  const parseColor = (c) => {
    const m = /rgba?\(([^)]+)\)/.exec(c || "");
    if (!m) return null;
    const p = m[1].split(",").map((x) => parseFloat(x));
    if (p.length < 3 || p.some((x) => isNaN(x))) return null;
    return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 };
  };
  const effectiveBg = (el) => {
    let r = 0, g = 0, b = 0, a = 0;
    for (let node = el; node && a < 0.999; node = node.parentElement) {
      const c = parseColor(getComputedStyle(node).backgroundColor);
      if (!c || c.a <= 0) continue;
      const w = (1 - a) * c.a;              // paint UNDER the accumulated layers
      r += w * c.r; g += w * c.g; b += w * c.b; a += w;
    }
    if (a < 0.999) { const w = 1 - a; r += w * 255; g += w * 255; b += w * 255; }
    return `rgb(${Math.round(r)}, ${Math.round(g)}, ${Math.round(b)})`;
  };
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
  const headerTop = header ? header.getBoundingClientRect().top : 120;
  // the banner: a slim full-width strip ABOVE the header carrying a dismiss button
  const vw = window.innerWidth;
  let banner = null;
  for (const el of Array.from(document.body.querySelectorAll("div, section, aside"))) {
    if (!isVisible(el) || el.contains(header) || (header && header.contains(el))) continue;
    const r = el.getBoundingClientRect();
    if (r.top > headerTop - 4 || r.height < 18 || r.height > 96 || r.width < vw * 0.9) continue;
    if (!el.querySelector("button, [role='button']")) continue;
    if (!(el.textContent || "").trim()) continue;
    if (banner && banner.contains(el)) banner = el;  // innermost qualifying strip
    else if (!banner) banner = el;
  }
  if (!banner) return null;
  banner.setAttribute("data-affordance-banner", "1");
  const s = getComputedStyle(banner);
  const r = banner.getBoundingClientRect();
  const out = {
    observed: true,
    bg: s.backgroundColor, ink: s.color, height: Math.round(r.height),
    fontSize: px(s.fontSize),
  };
  // the composited screen-truth paint rides beside the raw declaration (W1); only
  // meaningful (and only recorded) when the raw value carries alpha.
  const rawBg = parseColor(s.backgroundColor);
  if (rawBg && rawBg.a < 0.999) out.bgEffective = effectiveBg(banner);
  // CTA link: an anchor inside the strip (label + href + text-decoration + arrow glyph)
  const a = Array.from(banner.querySelectorAll("a[href]")).filter(isVisible)[0];
  if (a) {
    const as = getComputedStyle(a);
    const cta = { label: (a.textContent || "").replace(/\s+/g, " ").trim(),
                  href: a.getAttribute("href") || "",
                  underline: (as.textDecorationLine || "").indexOf("underline") >= 0,
                  color: as.color, fontWeight: as.fontWeight };
    const svg = a.querySelector("svg");
    if (svg) {
      const o = svg.outerHTML || "";
      const sr = svg.getBoundingClientRect();
      if (o && o.length <= 12000)
        cta.arrow = { kind: "svg", svg: o,
                      box: { w: Math.round(sr.width), h: Math.round(sr.height) } };
    }
    out.cta = cta;
  }
  // close affordance: a small button whose accessible name or artwork dismisses
  const btns = Array.from(banner.querySelectorAll("button, [role='button']")).filter(isVisible);
  for (const b of btns) {
    if (a && (b.contains(a) || a.contains(b))) continue;
    const br = b.getBoundingClientRect();
    if (Math.max(br.width, br.height) > 64) continue;
    const close = { box: { w: Math.round(br.width), h: Math.round(br.height) } };
    const aria = b.getAttribute("aria-label") || "";
    if (aria) close.ariaLabel = aria;
    const svg = b.querySelector("svg");
    if (svg) {
      const o = svg.outerHTML || "";
      if (o && o.length <= 12000) { close.kind = "svg"; close.svg = o; }
    } else if ((b.textContent || "").trim()) {
      close.kind = "text"; close.glyphText = (b.textContent || "").trim().slice(0, 4);
    }
    out.close = close;
    break;
  }
  // message: the strip's text minus the cta label and close glyph text
  let msg = (banner.textContent || "").replace(/\s+/g, " ").trim();
  if (out.cta && out.cta.label) msg = msg.replace(out.cta.label, " ");
  if (out.close && out.close.glyphText) msg = msg.replace(out.close.glyphText, " ");
  out.text = msg.replace(/\s+/g, " ").trim();
  return out;
}
"""

_UTILITY_TRIGGERS_JS = r"""
() => {
  const isVisible = (el) => {
    const s = getComputedStyle(el);
    if (s.display === "none" || s.visibility === "hidden") return false;
    const r = el.getBoundingClientRect();
    return r.width > 1 && r.height > 1;
  };
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
  if (!header) return [];
  // in-bar dropdown triggers that DON'T own an aria-controls mega panel: these
  // are the utility dropdowns (locale switchers, account menus) whose panels
  // portal on open. Mega tabs (aria-controls -> panel with links) are excluded.
  const out = [];
  let i = 0;
  for (const b of Array.from(header.querySelectorAll("button[aria-expanded], [role='button'][aria-expanded]"))) {
    if (!isVisible(b)) continue;
    const controls = b.getAttribute("aria-controls");
    if (controls) {
      const panel = document.getElementById(controls);
      if (panel && panel.querySelectorAll("a[href]").length >= 3) continue;  // mega tab
    }
    b.setAttribute("data-affordance-utility", String(i));
    out.push({ index: i, ariaLabel: b.getAttribute("aria-label") || "",
               label: (b.textContent || "").replace(/\s+/g, " ").trim() });
    i += 1;
  }
  return out;
}
"""

_UTILITY_OPEN_MEASURE_JS = r"""
(idx) => {
  const px = (v) => { const n = parseFloat(v); return isNaN(n) ? 0 : Math.round(n); };
  const isVisible = (el) => {
    const s = getComputedStyle(el);
    if (s.display === "none" || s.visibility === "hidden" || parseFloat(s.opacity || "1") < 0.05) return false;
    const r = el.getBoundingClientRect();
    return r.width > 1 && r.height > 1;
  };
  const trig = document.querySelector(`[data-affordance-utility="${idx}"]`);
  if (!trig) return null;
  const tr = trig.getBoundingClientRect();
  // the opened panel: prefer aria-controls; else the nearest NEW list-bearing
  // surface below the trigger (role=menu/listbox, or a ul/div of links/options).
  let panel = null;
  const controls = trig.getAttribute("aria-controls");
  if (controls) {
    const p = document.getElementById(controls);
    if (p && isVisible(p)) panel = p;
  }
  if (!panel) {
    let best = null, bestDy = 1e9;
    for (const el of Array.from(document.querySelectorAll("[role='menu'], [role='listbox'], ul, [class*='menu' i], [class*='dropdown' i]"))) {
      if (!isVisible(el) || el.contains(trig)) continue;
      const r = el.getBoundingClientRect();
      if (r.top < tr.bottom - 6 || r.width < 80 || r.width > 520 || r.height < 40) continue;
      const items = el.querySelectorAll("a[href], [role='option'], [role='menuitem'], li, button");
      if (items.length < 2) continue;
      const dy = Math.abs(r.top - tr.bottom) + Math.abs(r.left - tr.left) * 0.25;
      if (dy < bestDy) { best = el; bestDy = dy; }
    }
    panel = best;
  }
  if (!panel) return { open: false };
  panel.setAttribute("data-affordance-utility-panel", "1");
  const pr = panel.getBoundingClientRect();
  const ps = getComputedStyle(panel);
  const out = {
    open: true,
    panel: { x: Math.round(pr.x), y: Math.round(pr.y),
             w: Math.round(pr.w || pr.width), h: Math.round(pr.height),
             bg: ps.backgroundColor, radius: px(ps.borderTopLeftRadius),
             shadow: ps.boxShadow && ps.boxShadow !== "none" ? ps.boxShadow : "",
             border: ps.borderTopWidth && px(ps.borderTopWidth) ?
                     `${ps.borderTopWidth} solid ${ps.borderTopColor}` : "",
             paddingY: px(ps.paddingTop) },
  };
  if (ps.transition && ps.transition !== "all 0s ease 0s") out.panel.transition = ps.transition;
  // items: label / href / hreflang / selected markers
  const seen = new Set();
  const items = [];
  for (const it of Array.from(panel.querySelectorAll("a[href], [role='option'], [role='menuitem'], button"))) {
    if (!isVisible(it)) continue;
    const label = (it.textContent || "").replace(/\s+/g, " ").trim();
    if (!label || label.length > 48 || seen.has(label)) continue;
    seen.add(label);
    const entry = { label: label };
    const href = it.getAttribute && it.getAttribute("href");
    if (href) entry.href = href;
    const hl = it.getAttribute && (it.getAttribute("hreflang") || it.getAttribute("lang"));
    if (hl) entry.lang = hl;
    if (it.getAttribute("aria-current") || it.getAttribute("aria-selected") === "true" ||
        /\b(current|selected|active)\b/i.test(it.className || "")) entry.current = true;
    items.push(entry);
    if (items.length >= 40) break;
  }
  out.items = items;
  // item presentation: measured from a NON-current row; the current/selected row's
  // own paint (often inverted) rides a separate fact.
  const rows = Array.from(panel.querySelectorAll("a[href], [role='option'], [role='menuitem'], button")).filter(isVisible);
  const isCurrent = (el) => !!(el.getAttribute("aria-current") ||
    el.getAttribute("aria-selected") === "true" || /\b(current|selected|active)\b/i.test(el.className || ""));
  const plain = rows.find((el) => !isCurrent(el)) || rows[0];
  if (plain) {
    const fs = getComputedStyle(plain);
    out.item = { fontSize: px(fs.fontSize), color: fs.color,
                 padding: `${px(fs.paddingTop)}px ${px(fs.paddingLeft)}px` };
    if (px(fs.borderTopLeftRadius)) out.item.radius = px(fs.borderTopLeftRadius);
  }
  const cur = rows.find(isCurrent);
  if (cur) {
    const cs = getComputedStyle(cur);
    if (cs.backgroundColor && cs.backgroundColor !== "rgba(0, 0, 0, 0)")
      out.currentItem = { bg: cs.backgroundColor, color: cs.color };
  }
  // trigger chevron OPEN transform (hydrated real state)
  const svgs = Array.from(trig.querySelectorAll("svg")).filter(isVisible);
  if (svgs.length) {
    const t = getComputedStyle(svgs[svgs.length - 1]).transform;
    if (t && t !== "none") out.chevronOpenTransform = t;
  }
  return out;
}
"""


def measure_bar_affordances(
    url: str,
    *,
    viewport: tuple[int, int] = (1440, 900),
    shots_dir: Path | None = None,
    shot_prefix: str = "chrome-bar",
    timeout_ms: int = 45000,
    log=print,
) -> dict[str, Any]:
    """LIVE bar-affordance capture: utility-banner anatomy + in-bar utility
    dropdown open states (locale menus etc.). Returns
    ``{banner?, utilityDropdowns: {<ariaLabel-or-label>: {...}}, shots: [...]}``;
    controls the page never shows come back absent (degrade, never invent)."""
    from playwright.sync_api import sync_playwright

    out: dict[str, Any] = {"utilityDropdowns": {}, "shots": []}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": viewport[0], "height": viewport[1]},
                                device_scale_factor=2)
        page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
        page.wait_for_timeout(2200)
        # consent overlays REMOVED (the BANNER strip is chrome we keep — consent is
        # not; hidden-only nodes get re-shown by consent scripts and their fixed
        # overlays intercept the dropdown clicks below)
        try:
            page.evaluate(
                """() => {
  for (const el of document.querySelectorAll("[class*='cookie' i], [id*='cookie' i], [aria-label*='cookie' i], [id*='consent' i], [class*='consent' i]")) {
    if (el.closest('header, nav')) continue;
    el.remove();
  }
}"""
            )
        except Exception:
            pass
        banner = None
        try:
            banner = page.evaluate(_BANNER_HARVEST_JS)
        except Exception as exc:
            log(f"[chrome-bar] banner harvest failed: {type(exc).__name__}: {exc}")
        if banner:
            out["banner"] = banner
            if shots_dir is not None:
                shots_dir.mkdir(parents=True, exist_ok=True)
                shot = shots_dir / f"{shot_prefix}-banner.png"
                try:
                    page.locator("[data-affordance-banner]").screenshot(
                        path=str(shot), animations="disabled")
                    out["shots"].append(shot.name)
                except Exception:
                    pass
            log(f"[chrome-bar] banner: text={banner.get('text', '')[:60]!r} "
                f"cta={'yes' if banner.get('cta') else 'no'} "
                f"close={'yes' if banner.get('close') else 'no'}")
        else:
            log("[chrome-bar] no utility banner rendered on the live page")
        triggers = []
        try:
            triggers = page.evaluate(_UTILITY_TRIGGERS_JS) or []
        except Exception as exc:
            log(f"[chrome-bar] trigger scan failed: {type(exc).__name__}: {exc}")
        for t in triggers:
            name = t.get("ariaLabel") or t.get("label") or f"utility-{t['index']}"
            sel = f'[data-affordance-utility="{t["index"]}"]'
            facts = None
            try:
                page.locator(sel).click(timeout=3000)
                page.wait_for_timeout(600)
                facts = page.evaluate(_UTILITY_OPEN_MEASURE_JS, t["index"])
            except Exception as exc:
                log(f"[chrome-bar] '{name}' open failed: {type(exc).__name__}: {exc}")
            if facts and facts.get("open"):
                out["utilityDropdowns"][name] = facts
                if shots_dir is not None:
                    shots_dir.mkdir(parents=True, exist_ok=True)
                    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:40] or "utility"
                    shot = shots_dir / f"{shot_prefix}-{slug}-open.png"
                    try:
                        pr = facts["panel"]
                        vp = page.viewport_size or {"width": viewport[0], "height": viewport[1]}
                        clip = {"x": 0, "y": 0, "width": vp["width"],
                                "height": max(1, min(vp["height"], pr["y"] + pr["h"] + 24))}
                        page.screenshot(path=str(shot), clip=clip)
                        out["shots"].append(shot.name)
                    except Exception:
                        pass
                log(f"[chrome-bar] '{name}' open: {len(facts.get('items') or [])} items, "
                    f"panel {facts['panel']['w']}x{facts['panel']['h']}")
            try:
                page.keyboard.press("Escape")
                page.mouse.move(4, 4)
                page.wait_for_timeout(250)
            except Exception:
                pass
        browser.close()
    return out


_BANNER_FRAGMENT_JS = r"""
() => {
  const px = (v) => { const n = parseFloat(v); return isNaN(n) ? 0 : Math.round(n); };
  const isVisible = (el) => {
    const s = getComputedStyle(el);
    if (s.display === "none" || s.visibility === "hidden") return false;
    const r = el.getBoundingClientRect();
    return r.width > 1 && r.height > 1;
  };
  const bs = getComputedStyle(document.body);
  const out = { observed: true, bg: bs.backgroundColor, ink: bs.color,
                fontSize: px(bs.fontSize) };
  const a = Array.from(document.querySelectorAll("a[href]")).filter(isVisible)
    .filter((x) => (x.textContent || "").trim())[0];
  if (a) {
    const as = getComputedStyle(a);
    const cta = { label: (a.textContent || "").replace(/\s+/g, " ").trim(),
                  href: a.getAttribute("href") || "",
                  underline: (as.textDecorationLine || "").indexOf("underline") >= 0,
                  color: as.color, fontWeight: as.fontWeight };
    // weight may ride a styled WRAPPER (rich-text bold span around the anchor)
    if (cta.fontWeight === "400" && a.parentElement) {
      const ps = getComputedStyle(a.parentElement);
      if (parseInt(ps.fontWeight, 10) > 400) cta.fontWeight = ps.fontWeight;
    }
    const svg = a.querySelector("svg");
    if (svg && svg.outerHTML && svg.outerHTML.length <= 12000) {
      const sr = svg.getBoundingClientRect();
      cta.arrow = { kind: "svg", svg: svg.outerHTML,
                    box: { w: Math.round(sr.width), h: Math.round(sr.height) } };
    }
    out.cta = cta;
  }
  // close affordance: dedicated close containers/buttons (fragment captures often
  // style the box while the glyph itself is injected at runtime by the host page)
  const closer = document.querySelector(
    "[id*='close' i], [class*='close' i], button[aria-label*='close' i], button[aria-label*='dismiss' i]");
  if (closer) {
    const cs = getComputedStyle(closer);
    const close = {};
    const w = px(cs.width), h = px(cs.height);
    if (w || h) close.box = { w: w, h: h };
    if (cs.strokeWidth && px(cs.strokeWidth)) close.strokeWidth = px(cs.strokeWidth);
    if (cs.color) close.ink = cs.color;
    const svg = closer.querySelector("svg");
    if (svg && svg.outerHTML && svg.outerHTML.length <= 12000) {
      close.kind = "svg"; close.svg = svg.outerHTML;
    } else {
      close.kind = "box-only";  // glyph injected at runtime — artwork not captured
    }
    out.close = close;
  } else {
    // no close ELEMENT in the static fragment (runtime-injected): the fragment's
    // own stylesheet still declares the close box — mine the close-named rules
    // for the measured box/stroke/ink facts. Artwork stays uncaptured (box-only).
    const close = {};
    let sheets = [];
    try { sheets = Array.from(document.styleSheets || []); } catch (e) {}
    for (const sheet of sheets) {
      let rules = null;
      try { rules = sheet.cssRules || sheet.rules; } catch (e) { continue; }
      for (const rule of Array.from(rules || [])) {
        const sel = rule.selectorText || "";
        if (!/close/i.test(sel) || !rule.style) continue;
        const w = px(rule.style.getPropertyValue("width"));
        const h = px(rule.style.getPropertyValue("height"));
        if (w && h && w <= 64 && h <= 64) close.box = { w: w, h: h };
        const sw = px(rule.style.getPropertyValue("stroke-width"));
        if (sw) close.strokeWidth = sw;
        const col = rule.style.getPropertyValue("color");
        if (col && close.box) close.ink = col;
      }
    }
    if (close.box) { close.kind = "box-only"; out.close = close; }
  }
  let msg = (document.body.innerText || "").replace(/\s+/g, " ").trim();
  if (out.cta && out.cta.label) msg = msg.replace(out.cta.label, " ");
  out.text = msg.replace(/\s+/g, " ").trim();
  return out;
}
"""


def harvest_banner_from_fragment(
    fragment_path: str | Path,
    *,
    timeout_ms: int = 20000,
    log=print,
) -> dict[str, Any] | None:
    """Measure a utility banner's anatomy from a SAVED banner fragment (a captured
    iframe/embed .html that renders the banner as its own document — how hosted
    promo-banner services save). Serves the fragment's folder locally and computed-
    measures message / cta link (label, href, underline, weight, arrow) / close box.
    Surface colors are the FRAGMENT's own; the caller decides whether the site's
    banner-slot surface facts (mined CSS) supersede them. None when the fragment
    shows no banner-ish content."""
    import http.server
    import socketserver
    import threading
    from urllib.parse import quote

    from playwright.sync_api import sync_playwright

    fragment_path = Path(fragment_path).resolve()
    if not fragment_path.exists():
        raise FileNotFoundError(f"banner fragment not found: {fragment_path}")
    serve_dir = fragment_path.parent

    class _Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(serve_dir), **kw)

        def log_message(self, *a):
            pass

    httpd = socketserver.TCPServer(("127.0.0.1", 0), _Handler)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 300})
            page.goto(f"http://127.0.0.1:{port}/{quote(fragment_path.name)}",
                      timeout=timeout_ms, wait_until="domcontentloaded")
            page.wait_for_timeout(600)
            facts = page.evaluate(_BANNER_FRAGMENT_JS)
            browser.close()
    finally:
        httpd.shutdown()
        httpd.server_close()
    if not (facts and (facts.get("text") or facts.get("cta"))):
        return None
    facts["fragment"] = str(fragment_path)
    log(f"[chrome-banner] fragment: text={str(facts.get('text'))[:60]!r} "
        f"cta={'yes' if facts.get('cta') else 'no'} close={'yes' if facts.get('close') else 'no'}")
    return facts


def merge_bar_affordances(contract: dict[str, Any], affordances: dict[str, Any]) -> None:
    """Fold the live bar-affordance facts into the saved-page contract IN PLACE:
    the banner anatomy lands at ``nav.banner`` and each dropdown's open state
    attaches onto its matching ``nav.utility[]`` entry (by aria-label/label).
    Facts the live page didn't show merge nothing — the saved capture stands."""
    if not isinstance(affordances, dict):
        return
    nav = contract.get("nav") if isinstance(contract.get("nav"), dict) else None
    if nav is None:
        return
    banner = affordances.get("banner")
    if isinstance(banner, dict) and banner.get("observed"):
        nav["banner"] = banner
    drops = affordances.get("utilityDropdowns") or {}
    if not isinstance(drops, dict):
        return
    entries = [l for l in (nav.get("utility") or []) if isinstance(l, dict)]
    for name, facts in drops.items():
        if not isinstance(facts, dict) or not facts.get("open"):
            continue
        key = str(name).strip().lower()
        target = None
        for l in entries:
            probes = {str(l.get("ariaLabel") or "").strip().lower(),
                      str(l.get("label") or "").strip().lower(),
                      str(l.get("collapsedLabel") or "").strip().lower()}
            if key and key in probes:
                target = l
                break
        if target is None and len(drops) == 1:
            # a single live dropdown with a single captured dropdown-kind entry
            # matches structurally even when labels differ (locale-templated text)
            cands = [l for l in entries if l.get("kind") == "dropdown"]
            if len(cands) == 1:
                target = cands[0]
        if target is None:
            continue
        dd = {"items": facts.get("items") or [], "panel": facts.get("panel") or {}}
        for key in ("item", "currentItem"):
            if facts.get(key):
                dd[key] = facts[key]
        target["dropdown"] = dd
        if facts.get("chevronOpenTransform"):
            ch = target.get("chevron") if isinstance(target.get("chevron"), dict) else None
            if ch is not None and not ch.get("openTransform"):
                ch["openTransform"] = facts["chevronOpenTransform"]
            # the bar's dropdown-trigger family shares ONE chevron glyph: when the
            # measured open transform came from an IDENTICAL svg (same artwork,
            # byte-equal markup), the family fact is the same measurement — backfill
            # measured.trigger.chevron.openTransform (svg-equality guarded; a bar
            # with distinct glyph families keeps them separate).
            trig_ch = (((nav.get("measured") or {}).get("trigger") or {}).get("chevron"))
            if isinstance(trig_ch, dict) and not trig_ch.get("openTransform") \
                    and isinstance(ch, dict) \
                    and str(trig_ch.get("svg") or "") == str(ch.get("svg") or ""):
                trig_ch["openTransform"] = facts["chevronOpenTransform"]


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
    mega_shots_dir: str | Path | None = None,
    log=print,
) -> dict[str, Any]:
    """Launch headless Chromium, run the page, and extract nav/footer with styles.

    When ``mega_shots_dir`` is given, an OPEN-STATE mega-panel pass runs after the
    static harvest: each aria-controls panel is opened (hover/click), its rendered
    geometry measured, and a per-panel screenshot written there. The measured
    open facts merge into ``nav.megaOpen`` (fid4 2026-07)."""
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
            data = data or {}
            if mega_shots_dir is not None and isinstance(data.get("nav"), dict):
                try:
                    mega = measure_open_meganav(
                        page, shots_dir=Path(mega_shots_dir), log=log)
                    if mega:
                        data["nav"]["megaOpen"] = mega
                except Exception as exc:  # additive pass — never sink the harvest
                    log(f"[chrome-mega] open-state pass failed: {type(exc).__name__}: {exc}")
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


def _localize_asset_srcs(data: dict[str, Any], local_origin: str, serve_dir: Path) -> None:
    """Rewrite localhost-served asset srcs (icons / card images / store badges)
    captured from a saved page back to their ON-DISK saved file (in place).

    A saved-page capture serves `remote-com_files/...` via the throwaway
    127.0.0.1 server, so computed `currentSrc` values point there. The saved file
    IS the evidence — record its real path (`savedFile`) so the curate step can
    copy the artwork into the brand's assets. Absolute remote URLs are left
    untouched (they are the source of record; curation may download them)."""
    from urllib.parse import unquote

    def fix(node: dict[str, Any], key: str = "src") -> None:
        s = str(node.get(key) or "")
        if not s or not local_origin or not s.startswith(local_origin):
            return
        rel = unquote(s[len(local_origin):].lstrip("/"))
        cand = (serve_dir / rel).resolve()
        if cand.is_file():
            node["savedFile"] = str(cand)
            node[key] = rel

    nav = data.get("nav") if isinstance(data.get("nav"), dict) else {}
    for tier_key in ("links", "utility", "primary"):
        for ln in (nav.get(tier_key) or []):
            if not isinstance(ln, dict):
                continue
            menu = ln.get("menu") if isinstance(ln.get("menu"), dict) else None
            if not menu:
                continue
            for col in (menu.get("columns") or []):
                for sub in (col.get("links") or []):
                    ic = sub.get("icon") if isinstance(sub, dict) else None
                    if isinstance(ic, dict) and ic.get("src"):
                        fix(ic)
            card = menu.get("card") if isinstance(menu.get("card"), dict) else None
            if card and isinstance(card.get("image"), dict):
                fix(card["image"])
    footer = data.get("footer") if isinstance(data.get("footer"), dict) else {}
    for s in (footer.get("social") or []):
        ic = s.get("icon") if isinstance(s, dict) else None
        if isinstance(ic, dict) and ic.get("src"):
            fix(ic)
    bb = footer.get("bottomBar") if isinstance(footer.get("bottomBar"), dict) else None
    if bb:
        for badge in (bb.get("storeBadges") or []):
            if isinstance(badge, dict) and isinstance(badge.get("img"), dict):
                fix(badge["img"])


def extract_chrome_from_saved_page(
    html_path: str | Path,
    *,
    base_url: str | None = None,
    timeout_ms: int = 30000,
    mega_shots_dir: str | Path | None = None,
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
        data = extract_chrome_with_browser(
            local_url, timeout_ms=timeout_ms, mega_shots_dir=mega_shots_dir, log=log)
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
    # Map localhost-served icon/card/badge srcs back to their on-disk saved files
    # (the curate step copies that artwork into the brand's assets — fid4 2026-07).
    _localize_asset_srcs(data, local_origin, serve_dir)
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
