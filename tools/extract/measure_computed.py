#!/usr/bin/env python3
"""measure_computed.py — brand-agnostic computed-style measurement of a capture.

Generalized from the (frozen) experiments/remote-e2e/measure_chrome.py: loads the
saved page in headless Chromium (JavaScript DISABLED by default — static CSS only,
mirroring the source_chrome.v2 offline approach), but measures GENERIC node sets
instead of one brand's selectors:

  chrome         header/nav/footer surfaces, a nav link, a footer link
  headings       first instance of each h1..h6 + a body paragraph + body/html
  actionGroups   every <a>/<button> with button-ish classes, grouped by class
                 signature — one representative per family measured with the full
                 button prop set + a width-behavior hint (rect vs parent width);
                 this is the button VARIANT-MATRIX evidence
  sections       visible direct children of <main> (or <body>) — rect + surface
                 color + first heading; written to section-rects.json for the
                 screenshot slicing stage
  picks          extra --pick name=selector nodes (site-specific additions
                 WITHOUT editing this script)
  tiers          CANONICAL-TIER LADDER (P1.1, additive): the same page re-measured
                 at four viewport tiers (default 1920/1440/960/375), each block
                 stamped with its tier — headings h1..h6 + p per tier, root/body
                 font sizes, CONTAINER WIDTH facts (declared max/min/% resolved
                 to used px per tier), and HEADING-EMPHASIS facts (<strong>/<b>
                 weight inside headings — the emphasis-inside-heading law).
                 The authored brand.yaml declares which tier its canonical values
                 refer to (meta.canonicalTier) and per-tier type ladders; the
                 validator gates them (C14). --tiers "" skips the ladder pass.

CAVEAT: with JS disabled the static layout's y-coordinates can diverge from a
live full-page screenshot (JS-injected content, lazy sections). slice_sections.py
scales rects by viewport ratio and supports explicit boundaries as a fallback —
verify the crops visually before grounding. Use --js for closer-to-live geometry
when the capture tolerates it.

Usage:
    ./venv/bin/python tools/extract/measure_computed.py --capture screenshots/<brand>/ \
        --out-dir runs/<brand>/brand/evidence/ [--js] [--pick heroPanel=.hero-mod] \
        [--tiers 1920,1440,960,375]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCHEMA = "computed-measure.v1"          # section-rects.json (shape unchanged)
STYLES_SCHEMA = "computed-measure.v2"   # computed-styles.json (v1 + additive tier keys)

# the canonical measurement ladder: desktop-xl / desktop / tablet / mobile.
# The AUTHORED ladder convention (brand.yaml sizeRem base/tablet/mobileL/mobile)
# maps onto these measured tiers; meta.canonicalTier names which one is canonical.
DEFAULT_TIERS = (1920, 1440, 960, 375)
_TIER_HEIGHT = {1920: 1080, 1440: 900, 960: 720, 375: 812}


def find_saved_html(capture: Path) -> Path:
    pages = sorted(capture.glob("*.htm*"), key=lambda p: p.stat().st_size, reverse=True)
    if not pages:
        raise SystemExit(f"no saved .html page found in {capture}")
    return pages[0]


JS = r"""
(picks) => {
  const BTN_PROPS = ['background-color','color','border','border-radius','padding',
    'font-family','font-size','font-weight','line-height','letter-spacing',
    'text-transform','display','width'];
  const TXT_PROPS = ['color','font-family','font-size','font-weight','line-height',
    'letter-spacing','text-transform'];
  const SURF_PROPS = ['background-color','color','padding','border-bottom','border-top',
    'position','max-width'];

  const pick = (el, props) => {
    if (!el) return null;
    const cs = getComputedStyle(el);
    const out = {};
    for (const p of props) out[p] = cs.getPropertyValue(p);
    const r = el.getBoundingClientRect();
    out._rect = { x: r.x, y: r.y, w: r.width, h: r.height };
    return out;
  };
  const q = (sel) => { try { return document.querySelector(sel); } catch (e) { return null; } };

  // Painted text and accessible names are different evidence channels. A common
  // CTA pattern appends an sr-only descriptive suffix inside the anchor; raw
  // textContent then looks like the visible label even though it cannot fit the
  // measured host. Keep the semantic name, but never let hidden text affect paint.
  const collapse = (value) => String(value || '').replace(/\s+/g, ' ').trim();
  const isHiddenTextContainer = (node, root) => {
    for (let el = node; el && el.nodeType === Node.ELEMENT_NODE; el = el.parentElement) {
      if (el.hidden || el.getAttribute('aria-hidden') === 'true') return true;
      const cls = String((el.className && el.className.baseVal !== undefined)
        ? el.className.baseVal : (el.className || ''));
      if (/(^|\s)(?:sr-only|visually-hidden|screen-reader-text|u-sr-only)(?:\s|$)/i.test(cls)) {
        return true;
      }
      const s = getComputedStyle(el);
      if (s.display === 'none' || s.visibility === 'hidden') return true;
      const clipped = (
        (s.clip && s.clip !== 'auto' && s.clip !== 'rect(auto, auto, auto, auto)')
        || (s.clipPath && s.clipPath !== 'none')
      );
      const r = el.getBoundingClientRect();
      if (clipped && r.width <= 1 && r.height <= 1) return true;
      if (el === root) break;
    }
    return false;
  };
  const visibleLabel = (el) => {
    const parts = [];
    const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) {
      const text = collapse(walker.currentNode.nodeValue);
      const parent = walker.currentNode.parentElement;
      if (text && parent && !isHiddenTextContainer(parent, el)) parts.push(text);
    }
    return collapse(parts.join(' '));
  };
  const accessibleLabel = (el) => {
    const ariaLabel = collapse(el.getAttribute('aria-label'));
    const labelledBy = collapse(el.getAttribute('aria-labelledby'));
    if (ariaLabel) return { accessibleName: ariaLabel, ariaLabel, labelledBy };
    if (labelledBy) {
      const name = collapse(labelledBy.split(/\s+/).map((id) => {
        const ref = document.getElementById(id);
        return ref ? ref.textContent : '';
      }).join(' '));
      if (name) return { accessibleName: name, ariaLabel: '', labelledBy };
    }
    return { accessibleName: collapse(el.textContent), ariaLabel: '', labelledBy };
  };
  const labelFit = (el, label, semanticText, measured) => {
    const cs = getComputedStyle(el);
    const canvas = document.createElement('canvas');
    const context = canvas.getContext('2d');
    context.font = `${cs.fontStyle} ${cs.fontWeight} ${cs.fontSize} ${cs.fontFamily}`;
    const textWidth = (text) => context.measureText(text || '').width;
    const pad = (parseFloat(cs.paddingLeft) || 0) + (parseFloat(cs.paddingRight) || 0);
    const host = measured && measured._rect ? measured._rect.w : el.getBoundingClientRect().width;
    const visibleEstimate = textWidth(label) + pad;
    const semanticEstimate = textWidth(semanticText) + pad;
    const tolerance = Math.max(4, host * 0.08);
    return {
      hostWidth: Math.round(host * 1000) / 1000,
      horizontalPadding: Math.round(pad * 1000) / 1000,
      visibleEstimatedWidth: Math.round(visibleEstimate * 1000) / 1000,
      semanticEstimatedWidth: Math.round(semanticEstimate * 1000) / 1000,
      visibleFits: visibleEstimate <= host + tolerance,
      likelyHiddenTextConflation: semanticEstimate > host + tolerance && visibleEstimate <= host + tolerance,
    };
  };

  // chrome
  const header = q('header') || q('[class*="header"]');
  const footer = (() => { const f = document.querySelectorAll('footer');
    if (f.length) return f[f.length - 1];
    return q('[class*="footer"]'); })();
  const navLink = header ? header.querySelector('nav a, a') : null;
  const footerLink = footer ? footer.querySelector('a') : null;

  // headings + body
  const headings = {};
  for (const tag of ['h1','h2','h3','h4','h5','h6','p']) {
    headings[tag] = pick(q(tag), TXT_PROPS);
  }

  // action groups (button variant-matrix evidence)
  const groups = {};
  const isButtonish = (el) => {
    if (el.tagName === 'BUTTON') return true;
    const cls = (el.className && el.className.baseVal !== undefined)
      ? el.className.baseVal : (el.className || '');
    return /button|btn(\b|-)|cta/i.test(String(cls));
  };
  for (const el of document.querySelectorAll('a, button, input[type="submit"]')) {
    if (!isButtonish(el)) continue;
    const cls = String((el.className && el.className.baseVal !== undefined)
      ? el.className.baseVal : (el.className || ''));
    const key = el.tagName.toLowerCase() + '.' + cls.split(/\s+/).sort().join('.');
    if (!groups[key]) {
      const measured = pick(el, BTN_PROPS);
      const visible = visibleLabel(el);
      const semanticText = collapse(el.textContent);
      const accessibility = accessibleLabel(el);
      let widthBehavior = null;
      if (measured && el.parentElement) {
        const pr = el.parentElement.getBoundingClientRect();
        if (pr.width > 0) {
          const ratio = measured._rect.w / pr.width;
          widthBehavior = ratio > 0.96 ? 'stretch' : (ratio < 0.85 ? 'hug' : 'near-full');
        }
      }
      groups[key] = { classes: cls.slice(0, 140), tag: el.tagName.toLowerCase(),
        count: 0, sample: visible.slice(0, 120), visibleLabel: visible.slice(0, 240),
        accessibleName: accessibility.accessibleName.slice(0, 500),
        ariaLabel: accessibility.ariaLabel.slice(0, 500),
        labelledBy: accessibility.labelledBy.slice(0, 240),
        semanticText: semanticText.slice(0, 500),
        labelFit: labelFit(el, visible, semanticText, measured),
        widthBehavior, measured };
    }
    groups[key].count += 1;
  }
  const actionGroups = Object.values(groups)
    .sort((a, b) => b.count - a.count).slice(0, 48);

  // sections: visible structural children of main (fallback body), piercing
  // single-child wrappers; when that yields too few, fall back to the OUTERMOST
  // <section> elements (saved pages often wrap all modules in one div).
  let root = q('main') || document.body;
  while (root.children.length === 1 && root.children[0].children.length) {
    root = root.children[0];
  }
  const describe = (el, idx) => {
    const r = el.getBoundingClientRect();
    const h = el.querySelector('h1,h2,h3,h4,h5,h6');
    const cls = String((el.className && el.className.baseVal !== undefined)
      ? el.className.baseVal : (el.className || ''));
    return { index: idx, tag: el.tagName.toLowerCase(),
      classes: cls.slice(0, 130), id: (el.id || '').slice(0, 60),
      rect: { x: r.x, y: r.y + window.scrollY, w: r.width, h: r.height },
      backgroundColor: getComputedStyle(el).getPropertyValue('background-color'),
      heading: h ? (h.textContent || '').trim().slice(0, 120) : '' };
  };
  // CONTENT sections only: chrome-nested nodes (mega-menu dropdown panels that
  // keep layout boxes while visibility:hidden, footer link columns) and
  // invisible nodes are NOT page sections — they polluted section-rects and
  // shifted every replica band mapping (hubspot-v2 2026-07).
  const isContentSection = (el) => {
    if (el.closest('header, footer, nav')) return false;
    const s = getComputedStyle(el);
    if (s.display === 'none' || s.visibility === 'hidden' || s.opacity === '0') return false;
    if (el.closest('[aria-hidden="true"], [hidden]')) return false;
    return el.getBoundingClientRect().height >= 40;
  };
  let candidates = Array.from(root.children).filter(isContentSection);
  if (candidates.length < 3) {
    const outermost = Array.from(document.querySelectorAll('section')).filter(
      (s) => !(s.parentElement && s.parentElement.closest('section')));
    const outermostContent = outermost.filter(isContentSection);
    if (outermostContent.length > candidates.length) candidates = outermostContent;
  }
  const sections = candidates.map((el, i) => describe(el, i));

  // header/footer participate as slices too (chrome crops for grounding).
  // Sticky/overlay wrappers can report near-document heights (100vh menus),
  // so chrome bands are CAPPED to plausible chrome heights.
  const chromeRects = [];
  const CHROME_CAP = { header: 600, footer: 2400 };
  for (const [name, el] of [['header', header], ['footer', footer]]) {
    if (!el) continue;
    const r = el.getBoundingClientRect();
    if (r.height < 24) continue;
    let y = r.y + window.scrollY;
    let hgt = Math.min(r.height, CHROME_CAP[name]);
    if (name === 'footer' && r.height > CHROME_CAP.footer) {
      y = y + r.height - CHROME_CAP.footer;  // keep the BOTTOM band for footers
    }
    chromeRects.push({ name, classes: String(el.className || '').slice(0, 130),
      cappedFrom: r.height > CHROME_CAP[name] ? r.height : null,
      rect: { x: r.x, y, w: r.width, h: hgt } });
  }

  const picked = {};
  for (const [name, sel] of Object.entries(picks || {})) {
    picked[name] = pick(q(sel), BTN_PROPS.concat(SURF_PROPS));
  }

  return {
    chrome: {
      header: pick(header, SURF_PROPS),
      footer: pick(footer, SURF_PROPS),
      navLink: pick(navLink, TXT_PROPS.concat(['padding','border-radius'])),
      footerLink: pick(footerLink, TXT_PROPS),
    },
    headings,
    body: pick(document.body, TXT_PROPS.concat(['background-color'])),
    htmlFont: pick(document.documentElement, ['font-size']),
    actionGroups,
    sections,
    chromeRects,
    docHeight: document.documentElement.scrollHeight,
  };
}
"""


# ── canonical-tier ladder measurement (P1.1) ─────────────────────────────────────
# One lean evaluation per tier viewport: type registers, container width facts and
# heading-emphasis facts, every block stamped with the tier it was measured at.
TIER_JS = r"""
(tier) => {
  const TXT_PROPS = ['color','font-family','font-size','font-weight','line-height',
    'letter-spacing','text-transform'];
  const pick = (el, props) => {
    if (!el) return null;
    const cs = getComputedStyle(el);
    const out = {};
    for (const p of props) out[p] = cs.getPropertyValue(p);
    const r = el.getBoundingClientRect();
    out._rect = { x: r.x, y: r.y + window.scrollY, w: r.width, h: r.height };
    out.tier = tier;
    return out;
  };
  const q = (sel) => { try { return document.querySelector(sel); } catch (e) { return null; } };

  // type registers per tier (h1..h6 coverage where evidenced + body paragraph)
  const headings = {};
  for (const tag of ['h1','h2','h3','h4','h5','h6','p']) {
    headings[tag] = pick(q(tag), TXT_PROPS);
  }

  // CONTAINER WIDTH FACTS: ancestors of the main content that declare a max-width,
  // plus the header/footer content wrappers — the declared %/max/min beside the
  // USED px at this tier (the resolution the authored container tokens cite).
  const containerFacts = [];
  const seen = new Set();
  const describe = (el, owner) => {
    if (!el || seen.has(el)) return;
    seen.add(el);
    const cs = getComputedStyle(el);
    if (cs.maxWidth === 'none' && owner === 'content') return;
    const r = el.getBoundingClientRect();
    if (r.width < 200) return;               // controls/chips are not containers
    const cls = String((el.className && el.className.baseVal !== undefined)
      ? el.className.baseVal : (el.className || ''));
    containerFacts.push({
      tier, owner,
      tag: el.tagName.toLowerCase(), classes: cls.slice(0, 110),
      cssMaxWidth: cs.maxWidth, cssMinWidth: cs.minWidth,
      usedWidthPx: Math.round(r.width * 100) / 100,
      viewportFraction: Math.round((r.width / window.innerWidth) * 1000) / 1000,
      paddingLeft: cs.paddingLeft, paddingRight: cs.paddingRight,
    });
  };
  const h1 = q('h1');
  let node = h1 ? h1.parentElement : null;
  while (node && node !== document.body && containerFacts.length < 6) {
    describe(node, 'content');
    node = node.parentElement;
  }
  const header = q('header') || q('[class*="header"]');
  const footers = document.querySelectorAll('footer');
  const footer = footers.length ? footers[footers.length - 1] : q('[class*="footer"]');
  for (const [owner, root] of [['header', header], ['footer', footer]]) {
    if (!root) continue;
    let best = null;
    for (const el of root.querySelectorAll('*')) {
      const cs = getComputedStyle(el);
      if (cs.maxWidth === 'none') continue;
      const r = el.getBoundingClientRect();
      if (r.width < 200) continue;
      if (!best || r.width > best.getBoundingClientRect().width) best = el;
      if (containerFacts.length > 24) break;
    }
    if (best) describe(best, owner);
    else describe(root, owner + '-root');
  }

  // HEADING-EMPHASIS FACTS: <strong>/<b> inside h1..h6 — is emphasis a weight
  // step, a family swap, or inert (the emphasis-inside-heading law)?
  const headingEmphasis = [];
  for (const tag of ['h1','h2','h3','h4','h5','h6']) {
    const hits = document.querySelectorAll(tag + ' strong, ' + tag + ' b');
    if (!hits.length) continue;
    const em = hits[0];
    const h = em.closest(tag);
    const hcs = h ? getComputedStyle(h) : null;
    const ecs = getComputedStyle(em);
    headingEmphasis.push({
      tier, tag, count: hits.length,
      headingWeight: hcs ? hcs.fontWeight : null,
      emphasisWeight: ecs.fontWeight,
      sameFamily: hcs ? (hcs.fontFamily === ecs.fontFamily) : null,
      emphasisFamily: ecs.fontFamily.split(',')[0].trim().slice(0, 60),
      sample: (em.textContent || '').trim().slice(0, 60),
    });
  }

  return {
    tier,
    viewport: { w: window.innerWidth, h: window.innerHeight },
    htmlFontSize: getComputedStyle(document.documentElement).fontSize,
    bodyFontSize: getComputedStyle(document.body).fontSize,
    headings, containerFacts, headingEmphasis,
  };
}
"""


def measure(html_path: Path, viewport: tuple[int, int], js_enabled: bool,
            picks: dict[str, str], tiers: tuple[int, ...] = ()) -> dict:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        page = b.new_page(viewport={"width": viewport[0], "height": viewport[1]},
                          java_script_enabled=js_enabled)
        page.goto(html_path.resolve().as_uri(), wait_until="load", timeout=60000)
        facts = page.evaluate(JS, picks)
        # tier ladder: SAME loaded page re-measured per viewport (JS-off static CSS
        # reflows deterministically on resize; media queries re-apply per tier).
        if tiers:
            tier_facts: dict[str, dict] = {}
            for w in tiers:
                page.set_viewport_size(
                    {"width": w, "height": _TIER_HEIGHT.get(w, 900)})
                page.wait_for_timeout(80)
                tier_facts[str(w)] = page.evaluate(TIER_JS, str(w))
            # restore the primary viewport so any later evaluation sees it
            page.set_viewport_size({"width": viewport[0], "height": viewport[1]})
            facts["tierViewports"] = list(tiers)
            facts["tiers"] = tier_facts
        b.close()
    return facts


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--capture", type=Path, help="capture dir (auto-discovers the saved .html)")
    ap.add_argument("--html", type=Path, help="explicit saved-page .html")
    ap.add_argument("--out-dir", type=Path, required=True,
                    help="dir for computed-styles.json + section-rects.json")
    ap.add_argument("--viewport", default="1440x900", help="WxH (default 1440x900)")
    ap.add_argument("--js", action="store_true",
                    help="enable JavaScript (default OFF — static CSS only)")
    ap.add_argument("--pick", action="append", default=[], metavar="NAME=SELECTOR",
                    help="extra node to measure (repeatable)")
    ap.add_argument("--tiers", default=",".join(str(t) for t in DEFAULT_TIERS),
                    help="csv viewport widths for the canonical-tier ladder "
                         f"(default {','.join(str(t) for t in DEFAULT_TIERS)}; "
                         "empty string skips the ladder pass)")
    return ap


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    html_path = args.html or (find_saved_html(args.capture) if args.capture else None)
    if html_path is None:
        raise SystemExit("provide --capture <dir> or --html <file>")
    try:
        w, h = (int(x) for x in args.viewport.lower().split("x"))
    except ValueError:
        raise SystemExit(f"bad --viewport {args.viewport!r} (expected WxH)")
    picks: dict[str, str] = {}
    for p in args.pick:
        name, _, sel = p.partition("=")
        if not name or not sel:
            raise SystemExit(f"bad --pick {p!r} (expected NAME=SELECTOR)")
        picks[name] = sel
    try:
        tiers = tuple(int(t) for t in args.tiers.split(",") if t.strip())
    except ValueError:
        raise SystemExit(f"bad --tiers {args.tiers!r} (expected csv widths)")

    facts = measure(html_path, (w, h), args.js, picks, tiers=tiers)
    sections = facts.pop("sections", [])
    chrome_rects = facts.pop("chromeRects", [])
    doc_height = facts.pop("docHeight", None)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    styles_path = args.out_dir / "computed-styles.json"
    rects_path = args.out_dir / "section-rects.json"
    styles_path.write_text(json.dumps(
        {"schemaVersion": STYLES_SCHEMA, "source": str(html_path),
         "viewport": {"w": w, "h": h}, "jsEnabled": args.js, **facts}, indent=1))
    rects_path.write_text(json.dumps(
        {"schemaVersion": SCHEMA, "source": str(html_path),
         "viewport": {"w": w, "h": h}, "jsEnabled": args.js,
         "docHeight": doc_height, "chrome": chrome_rects,
         "sections": sections}, indent=1))
    print(f"[done] measure: {len(facts.get('actionGroups') or [])} action families, "
          f"{len(sections)} section rects (doc {doc_height}px), "
          f"{len(facts.get('tiers') or {})} tier ladders -> "
          f"{styles_path.name} + {rects_path.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
