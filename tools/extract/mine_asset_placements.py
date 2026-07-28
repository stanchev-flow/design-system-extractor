#!/usr/bin/env python3
"""mine_asset_placements.py — where each curated asset ACTUALLY appears on a page.

The curation pass (curate_assets.py) answers "which files does this capture
ship"; the grounding pass answers "what kind of imagery does this section use".
Neither answers the question generation needs: WHICH FILE went in WHICH SECTION.
Without that join, downstream lanes fall back to ranking assets by role/aspect
guesswork and cheerfully drop a testimonial portrait into a hero.

This pass closes the join deterministically. It loads the saved capture in
headless Chromium (same JS-disabled default + viewport as measure_computed.py so
geometry lines up with section-rects.json), enumerates every rendered image
carrier — <img> (src/currentSrc/srcset), <picture><source>, CSS
background-image, and inline <svg> — and assigns each to the content section
whose measured band contains it, or to header/footer chrome.

Resolution back to the curated library is by capture-file basename against
assets-manifest.json entries[].source (inline SVGs match on the aria-label slug
curate_assets.py names them with). Carriers that resolve to nothing are reported
in unresolved[] rather than silently dropped — an unbindable image is evidence
that curation missed a file.

Output: <out> (default evidence/pages/<page>/asset-placements.json)
    placements[]  one row per (asset, section, carrier kind), with occurrence
                  count, rendered geometry, the fraction of the section band the
                  asset covers, alt text, and the section's class signature
    byAsset{}     asset file -> the sections/zones it appears in (reuse map:
                  one section = page-specific, many = system-wide chrome/spot art)

Usage:
    ./venv/bin/python tools/extract/mine_asset_placements.py \
        --capture screenshots/<brand>/<page> --brand-dir runs/<brand>/brand \
        --page <page> [--js] [--viewport 1440x900]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

SCHEMA = "asset-placements.v1"

# carriers too small to be design content: tracking pixels, spacer gifs.
MIN_RENDERED_PX = 12


def find_saved_html(capture: Path) -> Path:
    pages = sorted(capture.glob("*.htm*"), key=lambda p: p.stat().st_size, reverse=True)
    if not pages:
        raise SystemExit(f"no saved .html page found in {capture}")
    return pages[0]


JS = r"""
() => {
  // ── sections: MUST mirror measure_computed.py's selection so placement
  // sectionIndex values line up with section-rects.json / crops / grounding.
  const isContentSection = (el) => {
    if (el.closest('header, footer, nav')) return false;
    const s = getComputedStyle(el);
    if (s.display === 'none' || s.visibility === 'hidden' || s.opacity === '0') return false;
    if (el.closest('[aria-hidden="true"], [hidden]')) return false;
    return el.getBoundingClientRect().height >= 40;
  };
  let root = document.querySelector('main') || document.body;
  while (root.children.length === 1 && root.children[0].children.length) {
    root = root.children[0];
  }
  let candidates = Array.from(root.children).filter(isContentSection);
  if (candidates.length < 3) {
    const outermost = Array.from(document.querySelectorAll('section')).filter(
      (s) => !(s.parentElement && s.parentElement.closest('section')));
    const outermostContent = outermost.filter(isContentSection);
    if (outermostContent.length > candidates.length) candidates = outermostContent;
  }
  const sections = candidates.map((el, i) => {
    const r = el.getBoundingClientRect();
    const cls = String((el.className && el.className.baseVal !== undefined)
      ? el.className.baseVal : (el.className || ''));
    const h = el.querySelector('h1,h2,h3,h4,h5,h6');
    return { index: i, el, tag: el.tagName.toLowerCase(),
      classes: cls.slice(0, 130),
      heading: h ? (h.textContent || '').trim().slice(0, 120) : '',
      rect: { x: r.x, y: r.y + window.scrollY, w: r.width, h: r.height } };
  });

  const zoneOf = (el) => {
    if (el.closest('header, nav')) return 'header';
    if (el.closest('footer')) return 'footer';
    return 'main';
  };
  // containment first (a carrier nested in a section belongs to it regardless of
  // overflow); geometric fallback catches absolutely-positioned art.
  const sectionOf = (el, box) => {
    for (const s of sections) if (s.el.contains(el)) return s;
    const cy = box.y + box.h / 2;
    for (const s of sections) {
      if (cy >= s.rect.y && cy < s.rect.y + s.rect.h) return s;
    }
    return null;
  };
  const boxOf = (el) => {
    const r = el.getBoundingClientRect();
    return { x: Math.round(r.x), y: Math.round(r.y + window.scrollY),
             w: Math.round(r.width), h: Math.round(r.height) };
  };

  const out = [];
  const record = (el, kind, url, extra) => {
    const box = boxOf(el);
    const sec = sectionOf(el, box);
    out.push(Object.assign({
      kind, url: url || null, zone: zoneOf(el),
      sectionIndex: sec ? sec.index : null,
      sectionClasses: sec ? sec.classes : null,
      sectionHeading: sec ? sec.heading : null,
      sectionRect: sec ? sec.rect : null,
      rendered: box,
      hidden: (() => { const s = getComputedStyle(el);
        return s.display === 'none' || s.visibility === 'hidden' || s.opacity === '0'; })(),
      inLink: !!el.closest('a'),
      carrierClasses: String(el.className && el.className.baseVal !== undefined
        ? el.className.baseVal : (el.className || '')).slice(0, 120),
    }, extra || {}));
  };

  for (const img of document.querySelectorAll('img')) {
    const srcset = (img.getAttribute('srcset') || '').split(',')
      .map((s) => s.trim().split(/\s+/)[0]).filter(Boolean);
    let picture = [];
    const parent = img.parentElement;
    if (parent && parent.tagName === 'PICTURE') {
      picture = Array.from(parent.querySelectorAll('source')).flatMap(
        (s) => (s.getAttribute('srcset') || '').split(',')
          .map((x) => x.trim().split(/\s+/)[0]).filter(Boolean));
    }
    record(img, 'img', img.getAttribute('src'), {
      currentSrc: img.currentSrc || null,
      candidates: Array.from(new Set(srcset.concat(picture))).slice(0, 12),
      alt: (img.getAttribute('alt') || '').slice(0, 160),
      loading: img.getAttribute('loading') || null,
      natural: { w: img.naturalWidth || null, h: img.naturalHeight || null },
    });
  }

  for (const el of document.querySelectorAll('*')) {
    const bg = getComputedStyle(el).getPropertyValue('background-image');
    if (!bg || bg === 'none' || bg.indexOf('url(') === -1) continue;
    const urls = Array.from(bg.matchAll(/url\((['"]?)(.*?)\1\)/g))
      .map((m) => m[2]).filter((u) => u && !u.startsWith('data:'));
    for (const u of urls) record(el, 'background', u, { alt: '' });
  }

  for (const svg of document.querySelectorAll('svg')) {
    if (svg.closest('svg') !== svg) continue;            // nested defs
    if (!svg.querySelector('path, polygon, circle, rect')) continue;
    const t = svg.querySelector('title');
    record(svg, 'inline-svg', null, {
      label: (svg.getAttribute('aria-label') || (t ? t.textContent : '') || '').trim().slice(0, 80),
      alt: '',
    });
  }

  // RICH MEDIA: animation/video carriers are page content the curated file
  // library cannot hold (Lottie JSON + streamed video are fetched at runtime).
  // Recording them keeps the section's real visual treatment on the record —
  // otherwise a Lottie hero looks like an empty band with a hidden fallback img.
  const rich = [];
  const recordRich = (el, kind, ref) => {
    const box = boxOf(el);
    const sec = sectionOf(el, box);
    rich.push({ kind, ref: ref ? String(ref).slice(0, 200) : null,
      zone: zoneOf(el), sectionIndex: sec ? sec.index : null,
      sectionClasses: sec ? sec.classes : null,
      rendered: box,
      fallbackImgs: Array.from((el.parentElement || el).querySelectorAll('img'))
        .map((i) => i.currentSrc || i.getAttribute('src')).filter(Boolean).slice(0, 4) });
  };
  for (const el of document.querySelectorAll('[data-src], [data-animation-type], .lottie-animation, [data-is-ix2-target]')) {
    const ref = el.getAttribute('data-src') || '';
    if (!/\.(json|lottie)(\?|$)/i.test(ref)) continue;
    recordRich(el, 'lottie', ref);
  }
  for (const v of document.querySelectorAll('video')) {
    const src = v.getAttribute('src') ||
      (v.querySelector('source') ? v.querySelector('source').getAttribute('src') : '');
    recordRich(v, 'video', src);
  }

  return { sections: sections.map(({ el, ...s }) => s), carriers: out,
           richMedia: rich, docHeight: document.documentElement.scrollHeight };
}
"""


def measure(html_path: Path, viewport: tuple[int, int], js_enabled: bool) -> dict:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": viewport[0], "height": viewport[1]},
                                java_script_enabled=js_enabled)
        page.goto(html_path.resolve().as_uri(), wait_until="load", timeout=60000)
        page.wait_for_timeout(400)
        data = page.evaluate(JS)
        browser.close()
    return data


# ── resolution back to the curated library ────────────────────────────────────

def _basename(url: str) -> str:
    path = urlparse(unquote(str(url or ""))).path
    return Path(path).name


def _slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", str(text or "").lower()).strip("-")
    return re.sub(r"-{2,}", "-", s)


def build_resolver(manifest: dict) -> tuple[dict, dict]:
    """(capture-basename → curated dest, inline-svg-label-slug → curated dest)."""
    by_basename: dict[str, str] = {}
    by_label: dict[str, str] = {}
    for e in manifest.get("entries") or []:
        dest = str(e.get("dest") or "")
        src = str(e.get("source") or "")
        if str(e.get("origin")) == "inline-svg":
            hint = _slug(e.get("altHint") or "")
            if hint:
                by_label.setdefault(hint, dest)
            continue
        base = _basename(src)
        if base:
            by_basename.setdefault(base, dest)
            by_basename.setdefault(base.lower(), dest)
    return by_basename, by_label


def resolve_carrier(c: dict, by_basename: dict, by_label: dict) -> str | None:
    if c.get("kind") == "inline-svg":
        return by_label.get(_slug(c.get("label") or ""))
    urls = [c.get("currentSrc"), c.get("url")] + list(c.get("candidates") or [])
    for u in urls:
        if not u or str(u).startswith("data:"):
            continue
        base = _basename(u)
        hit = by_basename.get(base) or by_basename.get(base.lower())
        if hit:
            return hit
    return None


def fold_placements(carriers: list[dict], by_basename: dict, by_label: dict,
                    page: str) -> tuple[list[dict], list[dict]]:
    """Carriers → one placement row per (asset, section, zone, kind)."""
    rows: dict[tuple, dict] = {}
    unresolved: dict[str, dict] = {}
    for c in carriers:
        box = c.get("rendered") or {}
        w, h = int(box.get("w") or 0), int(box.get("h") or 0)
        asset = resolve_carrier(c, by_basename, by_label)
        if asset is None:
            u = str(c.get("currentSrc") or c.get("url") or
                    f"inline-svg:{c.get('label') or '?'}")
            if str(u).startswith("data:"):
                continue
            row = unresolved.setdefault(u, {"ref": u[:200], "kind": c.get("kind"),
                                            "count": 0, "maxRendered": 0})
            row["count"] += 1
            row["maxRendered"] = max(row["maxRendered"], w * h)
            continue
        # A curated file rendering at zero size is not noise — it is a RESPONSIVE
        # ALTERNATE (the mobile still behind a desktop animation, the desktop art
        # hidden at narrow widths). Dropping it loses the alternate binding, so
        # only VISIBLE sub-pixel carriers (tracking pixels) are discarded.
        if not c.get("hidden") and (w < MIN_RENDERED_PX or h < MIN_RENDERED_PX):
            continue
        key = (asset, c.get("zone"), c.get("sectionIndex"), c.get("kind"))
        row = rows.get(key)
        if row is None:
            sec_rect = c.get("sectionRect") or {}
            frac_w = round(w / sec_rect["w"], 3) if sec_rect.get("w") else None
            frac_h = round(h / sec_rect["h"], 3) if sec_rect.get("h") else None
            rows[key] = {
                "asset": asset, "page": page, "zone": c.get("zone"),
                "sectionIndex": c.get("sectionIndex"),
                "sectionClasses": c.get("sectionClasses"),
                "sectionHeading": c.get("sectionHeading"),
                "carrier": c.get("kind"), "occurrences": 1,
                "rendered": {"w": w, "h": h},
                # document-space origin: lets consumers restore the VISUAL order
                # of a row/grid of assets, which slot binding depends on.
                "position": {"x": box.get("x"), "y": box.get("y")},
                "fractionOfSection": {"w": frac_w, "h": frac_h},
                "natural": c.get("natural") or None,
                "alt": (c.get("alt") or "").strip() or None,
                "inLink": bool(c.get("inLink")),
                "hidden": bool(c.get("hidden")),
                "carrierClasses": c.get("carrierClasses") or None,
            }
        else:
            row["occurrences"] += 1
            if w * h > row["rendered"]["w"] * row["rendered"]["h"]:
                row["rendered"] = {"w": w, "h": h}
            row["hidden"] = row["hidden"] and bool(c.get("hidden"))
    out = sorted(rows.values(), key=lambda r: (r["zone"] != "main",
                                               r["sectionIndex"] if r["sectionIndex"]
                                               is not None else 10_000,
                                               -(r["rendered"]["w"] * r["rendered"]["h"])))
    return out, sorted(unresolved.values(), key=lambda r: -r["count"])


def fold_rich_media(rich: list[dict], by_basename: dict) -> list[dict]:
    """Animation/video carriers, with any curated still resolved as the fallback."""
    rows: dict[tuple, dict] = {}
    for r in rich:
        box = r.get("rendered") or {}
        if int(box.get("w") or 0) < MIN_RENDERED_PX:
            continue
        fallbacks = []
        for u in r.get("fallbackImgs") or []:
            base = _basename(u)
            hit = by_basename.get(base) or by_basename.get(base.lower())
            if hit and hit not in fallbacks:
                fallbacks.append(hit)
        key = (r.get("kind"), r.get("ref"), r.get("sectionIndex"), r.get("zone"))
        if key in rows:
            rows[key]["occurrences"] += 1
            continue
        rows[key] = {
            "kind": r.get("kind"), "ref": r.get("ref"), "zone": r.get("zone"),
            "sectionIndex": r.get("sectionIndex"),
            "sectionClasses": r.get("sectionClasses"),
            "rendered": {"w": box.get("w"), "h": box.get("h")},
            "occurrences": 1,
            "fallbackAssets": fallbacks,
            "note": ("runtime-fetched media not present in the capture; "
                     "fallbackAssets[] are the curated stills that stand in for it"),
        }
    return sorted(rows.values(), key=lambda r: (r["sectionIndex"] is None,
                                                r["sectionIndex"] or 0))


def build_section_slugs(crops_manifest: Path | None, page: str,
                        measured: list[dict]) -> dict[int, dict]:
    """measured section index → the CANONICAL section slug used downstream.

    The slice/ground stage renumbers bands (sub-threshold bands merge away, chrome
    bands get appended), so measured index N and crop index N are NOT the same
    section. Everything downstream — grounding filenames, layout provenance
    tokens — keys off the CROP slug, so placements must speak that language or
    the join silently misaligns by one band. Matched on (classes, heading), which
    both records carry verbatim.
    """
    if not crops_manifest or not crops_manifest.is_file():
        return {}
    crops = (json.loads(crops_manifest.read_text()).get("crops") or [])
    by_pair = {(str(c.get("classes") or ""), str(c.get("heading") or "")): c
               for c in crops}
    by_heading: dict[str, dict] = {}
    for c in crops:
        h = str(c.get("heading") or "")
        if h:
            by_heading.setdefault(h, c)
    out: dict[int, dict] = {}
    for s in measured:
        cls, head = str(s.get("classes") or ""), str(s.get("heading") or "")
        crop = by_pair.get((cls, head)) or by_heading.get(head)
        if crop is None:
            continue
        out[int(s["index"])] = {
            "sectionSlug": f"{page}-{Path(str(crop.get('file') or '')).stem}",
            "cropIndex": crop.get("index"),
        }
    return out


def apply_section_slugs(rows: list[dict], slugs: dict[int, dict]) -> None:
    for r in rows:
        idx = r.get("sectionIndex")
        hit = slugs.get(idx) if isinstance(idx, int) else None
        r["sectionSlug"] = hit["sectionSlug"] if hit else None
        r["cropIndex"] = hit["cropIndex"] if hit else None


def build_by_asset(placements: list[dict]) -> dict:
    """asset → the zones/sections it appears in (the reuse map)."""
    by: dict[str, dict] = {}
    for p in placements:
        row = by.setdefault(p["asset"], {"zones": [], "sections": [],
                                         "occurrences": 0, "visible": False})
        if p["zone"] not in row["zones"]:
            row["zones"].append(p["zone"])
        slug = p.get("sectionSlug")
        if slug and slug not in row["sections"]:
            row["sections"].append(slug)
        row["occurrences"] += p["occurrences"]
        row["visible"] = row["visible"] or not p["hidden"]
    for row in by.values():
        row["sections"].sort()
    return dict(sorted(by.items()))


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--capture", type=Path, required=True, help="capture dir")
    ap.add_argument("--brand-dir", type=Path, required=True,
                    help="runs/<brand>/brand (reads assets-manifest.json)")
    ap.add_argument("--page", help="page key (default: capture dir name)")
    ap.add_argument("--out", type=Path,
                    help="output path (default: "
                         "<brand-dir>/evidence/pages/<page>/asset-placements.json)")
    ap.add_argument("--crops-manifest", type=Path,
                    help="crops-manifest.json used to emit canonical section "
                         "slugs (default: <brand-dir>/evidence/pages/<page>/crops/)")
    ap.add_argument("--viewport", default="1440x900")
    ap.add_argument("--js", action="store_true",
                    help="run with JavaScript enabled (closer to live geometry)")
    return ap


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    page = args.page or args.capture.name
    html_path = find_saved_html(args.capture)
    w, _x, h = args.viewport.partition("x")
    viewport = (int(w), int(h or 900))

    manifest_path = args.brand_dir / "assets-manifest.json"
    if not manifest_path.is_file():
        raise SystemExit(f"no assets-manifest.json in {args.brand_dir} — run "
                         "curate_assets.py first")
    manifest = json.loads(manifest_path.read_text())
    by_basename, by_label = build_resolver(manifest)

    data = measure(html_path, viewport, args.js)
    placements, unresolved = fold_placements(data.get("carriers") or [],
                                             by_basename, by_label, page)
    rich_media = fold_rich_media(data.get("richMedia") or [], by_basename)
    crops_manifest = args.crops_manifest or (
        args.brand_dir / "evidence" / "pages" / page / "crops" / "crops-manifest.json")
    slugs = build_section_slugs(crops_manifest, page, data.get("sections") or [])
    apply_section_slugs(placements, slugs)
    apply_section_slugs(rich_media, slugs)
    for s in data.get("sections") or []:
        hit = slugs.get(int(s["index"]))
        s["sectionSlug"] = hit["sectionSlug"] if hit else None
        s["cropIndex"] = hit["cropIndex"] if hit else None
    out_path = args.out or (args.brand_dir / "evidence" / "pages" / page /
                            "asset-placements.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({
        "schemaVersion": SCHEMA,
        "page": page,
        "source": str(html_path),
        "viewport": {"w": viewport[0], "h": viewport[1]},
        "jsEnabled": bool(args.js),
        "sections": data.get("sections") or [],
        "placements": placements,
        "richMedia": rich_media,
        "byAsset": build_by_asset(placements),
        "unresolved": unresolved,
    }, indent=1) + "\n")
    bound = len({p["asset"] for p in placements})
    print(f"[done] placements: {len(placements)} rows / {bound} assets bound on "
          f"{page}, {len(rich_media)} rich-media carriers "
          f"({len(unresolved)} unresolved refs) -> {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
