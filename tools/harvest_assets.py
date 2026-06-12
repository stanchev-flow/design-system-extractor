#!/usr/bin/env python3
"""Brand asset harvester + role-mapper.

Tier-1 of the extraction model (see the architecture canvas): clone the brand's
own assets and classify them so the page generator can RE-PLACE them in the
right slots — instead of generating cheap stand-ins.

Given a captured HTML snapshot (and the site's base URL) this:
  1. Harvests every asset reference: <img>/srcset, <picture>/<source>, <video>
     + poster, inline <svg>, and CSS url(...) backgrounds.
  2. Collapses responsive variants (`...-p-500.avif`) down to one logical asset.
  3. Classifies each by asset TYPE (icon / logo / photo / illustration /
     background / texture / video / animated) using filename, extension,
     dimensions and inline-svg geometry.
  4. Infers a placement ROLE (navigation / hero / logo-wall / card / footer /
     background / content) from the nearest DOM landmark + classes + alt text.
  5. Emits a machine-readable manifest (JSON) and a visual report (HTML).

Heuristic, no network needed for classification. A vision pass would later
refine type/role — the manifest schema already carries a `confidence` slot.

Usage:
    python tools/harvest_assets.py \\
        --html screenshots/hackathon-test/source/hatch.html \\
        --base-url https://www.usehatchapp.com \\
        --out screenshots/hackathon-test/source/assets
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from html import unescape
from pathlib import Path
from urllib.parse import urljoin

# ── reference extraction regexes ─────────────────────────────────────────────
IMG_TAG_RE = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
SOURCE_TAG_RE = re.compile(r"<source\b[^>]*>", re.IGNORECASE)
VIDEO_TAG_RE = re.compile(r"<video\b[^>]*>", re.IGNORECASE)
SVG_TAG_RE = re.compile(r"<svg\b[^>]*>.*?</svg>", re.IGNORECASE | re.DOTALL)
STYLE_BLOCK_RE = re.compile(r"<style[^>]*>(.*?)</style>", re.IGNORECASE | re.DOTALL)
CSS_URL_RE = re.compile(r"url\(\s*(['\"]?)([^'\")]+)\1\s*\)", re.IGNORECASE)
LANDMARK_RE = re.compile(
    r"<(nav|header|footer|section|main|aside|article)\b([^>]*)>", re.IGNORECASE
)

RASTER_EXTS = {"png", "jpg", "jpeg", "webp", "avif", "gif"}
VIDEO_EXTS = {"mp4", "webm", "mov", "m4v"}
ANIM_EXTS = {"lottie", "riv", "json"}

HINT_LOGO = ("logo", "wordmark", "brandmark")
HINT_BG = ("background", "bg-", "-bg", "gradient", "hero-bg", "backdrop")
HINT_TEXTURE = ("texture", "grain", "noise", "pattern", "dots", "mesh")
HINT_ICON = ("icon", "ico-", "-ico", "glyph", "chevron", "arrow", "check", "star")
HINT_AVATAR = ("avatar", "headshot", "portrait", "person", "team", "author")
HINT_LOGOWALL = ("clients", "logos", "trusted", "brands", "customers", "partner")


def get_attr(tag: str, name: str) -> str:
    m = re.search(rf"{name}\s*=\s*([\"'])(.*?)\1", tag, re.IGNORECASE | re.DOTALL)
    return unescape(m.group(2).strip()) if m else ""


def srcset_urls(srcset: str) -> list[str]:
    out = []
    for part in srcset.split(","):
        url = part.strip().split(" ")[0].strip()
        if url:
            out.append(url)
    return out


def to_abs(url: str, base: str) -> str:
    url = url.strip()
    if url.startswith("data:") or url.startswith("//"):
        return ("https:" + url) if url.startswith("//") else url
    if url.startswith("http"):
        return url
    return urljoin(base + "/", url)


def ext_of(url: str) -> str:
    m = re.search(r"\.([a-z0-9]{2,5})(?:\?|#|$)", url.split("/")[-1], re.IGNORECASE)
    return m.group(1).lower() if m else ""


RESP_SUFFIX_RE = re.compile(r"-p-\d+(?=\.[a-z0-9]+$)", re.IGNORECASE)


def logical_key(url: str) -> str:
    """Collapse responsive variants (foo-p-500.avif / foo-p-800.avif → foo)."""
    if url.startswith("data:"):
        return "data:" + hashlib.md5(url.encode()).hexdigest()[:10]
    base = url.split("?")[0].split("#")[0]
    base = RESP_SUFFIX_RE.sub("", base)
    return base


def landmarks(html: str) -> list[tuple[int, str, str]]:
    """(position, tag, class+aria+id signal string) for each landmark open tag."""
    out = []
    for m in LANDMARK_RE.finditer(html):
        attrs = m.group(2)
        sig = " ".join(
            [
                get_attr("<x " + attrs + ">", "class"),
                get_attr("<x " + attrs + ">", "aria-label"),
                get_attr("<x " + attrs + ">", "id"),
            ]
        ).lower()
        out.append((m.start(), m.group(1).lower(), sig))
    return out


def nearest_landmark(pos: int, lms: list[tuple[int, str, str]]) -> tuple[str, str]:
    tag, sig = "body", ""
    for p, t, s in lms:
        if p <= pos:
            tag, sig = t, s
        else:
            break
    return tag, sig


def classify_type(url: str, kind: str, name: str, ctx: str, dims: tuple | None) -> tuple[str, list[str]]:
    """Return (asset_type, signals)."""
    sig: list[str] = []
    low = (name + " " + ctx).lower()
    ext = "svg" if kind == "inline-svg" else ext_of(url)

    def has(hints):
        return any(h in low for h in hints)

    if kind == "inline-svg" or ext == "svg":
        if has(HINT_LOGO):
            sig.append("logo-hint")
            return "logo", sig
        if dims and max(dims) and max(dims) <= 64:
            sig.append("small-viewBox")
            return "icon", sig
        if has(HINT_ICON):
            sig.append("icon-hint")
            return "icon", sig
        return ("icon" if kind == "inline-svg" else "vector"), sig

    if ext in VIDEO_EXTS:
        return "video", ["video-ext"]
    if ext in ANIM_EXTS:
        return "animated", ["anim-ext"]

    if ext in RASTER_EXTS:
        if has(HINT_LOGO):
            return "logo", ["logo-hint"]
        if has(HINT_TEXTURE):
            return "texture", ["texture-hint"]
        if has(HINT_BG):
            return "background", ["bg-hint"]
        if has(HINT_AVATAR):
            return "avatar", ["avatar-hint"]
        if has(HINT_ICON):
            return "icon", ["icon-hint"]
        if ext == "gif":
            return "animated", ["gif"]
        # Default raster: a photo unless it's tiny (then icon).
        if dims and max(dims) and max(dims) <= 48:
            return "icon", ["tiny-raster"]
        return "photo", ["raster-default"]

    return "other", [f"ext:{ext or 'none'}"]


def infer_role(landmark: str, sig: str, alt: str, asset_type: str, name: str) -> tuple[str, list[str]]:
    s = (sig + " " + alt + " " + name).lower()
    reasons: list[str] = [f"landmark:{landmark}"]

    if landmark == "nav" or landmark == "header":
        if asset_type in ("logo",) or "logo" in s:
            return "navigation/logo", reasons + ["in-nav"]
        return "navigation", reasons + ["in-nav"]
    if landmark == "footer":
        return "footer", reasons + ["in-footer"]
    if any(h in s for h in HINT_LOGOWALL):
        return "logo-wall", reasons + ["logowall-hint"]
    if "hero" in s or landmark == "header":
        return "hero", reasons + ["hero-hint"]
    if asset_type == "background" or asset_type == "texture":
        return "background", reasons + ["bg-type"]
    if asset_type == "avatar" or "testimonial" in s or "review" in s:
        return "testimonial/avatar", reasons + ["avatar-ctx"]
    if "card" in s or "feature" in s:
        return "card/feature", reasons + ["card-hint"]
    if asset_type == "video":
        return "media/video", reasons + ["video"]
    return "content", reasons


def harvest(html: str, base: str) -> list[dict]:
    lms = landmarks(html)
    records: list[dict] = []

    def add(kind, url, pos, alt="", name="", dims=None, variants=None, inline_svg=None):
        landmark, sig = nearest_landmark(pos, lms)
        display_name = name or (url.split("/")[-1].split("?")[0] if url else kind)
        atype, tsig = classify_type(url or "", kind, display_name, sig + " " + alt, dims)
        role, rsig = infer_role(landmark, sig, alt, atype, display_name)
        records.append(
            {
                "kind": kind,
                "url": url,
                "name": display_name,
                "asset_type": atype,
                "role": role,
                "placement": {"landmark": landmark, "context": sig[:160]},
                "alt": alt[:160],
                "dims": list(dims) if dims else None,
                "variants": variants or [],
                "signals": tsig + rsig,
                "confidence": "heuristic",
                "inline_svg": inline_svg,
            }
        )

    # <img>
    for m in IMG_TAG_RE.finditer(html):
        tag = m.group(0)
        src = get_attr(tag, "src") or get_attr(tag, "data-src")
        srcset = get_attr(tag, "srcset") or get_attr(tag, "data-srcset")
        variants = [to_abs(u, base) for u in srcset_urls(srcset)] if srcset else []
        url = to_abs(src, base) if src else (variants[-1] if variants else "")
        if not url:
            continue
        w, h = get_attr(tag, "width"), get_attr(tag, "height")
        dims = (int(w), int(h)) if w.isdigit() and h.isdigit() else None
        add("img", url, m.start(), alt=get_attr(tag, "alt"), dims=dims, variants=variants)

    # <video> + poster
    for m in VIDEO_TAG_RE.finditer(html):
        tag = m.group(0)
        src = get_attr(tag, "src") or get_attr(tag, "data-src")
        poster = get_attr(tag, "poster")
        if src:
            add("video", to_abs(src, base), m.start(), alt=get_attr(tag, "aria-label"))
        if poster:
            add("img", to_abs(poster, base), m.start(), name=poster.split("/")[-1])

    # <source> (picture/video)
    for m in SOURCE_TAG_RE.finditer(html):
        tag = m.group(0)
        src = get_attr(tag, "src")
        srcset = get_attr(tag, "srcset")
        variants = [to_abs(u, base) for u in srcset_urls(srcset)] if srcset else []
        url = to_abs(src, base) if src else (variants[-1] if variants else "")
        if url:
            add("source", url, m.start(), variants=variants)

    # inline <svg>
    for m in SVG_TAG_RE.finditer(html):
        block = m.group(0)
        vb = get_attr(block, "viewBox")
        dims = None
        if vb:
            nums = re.findall(r"-?\d+\.?\d*", vb)
            if len(nums) == 4:
                dims = (float(nums[2]), float(nums[3]))
        cls = get_attr(block, "class")
        aria = get_attr(block, "aria-label")
        svg_markup = block if len(block) <= 6000 else None
        add(
            "inline-svg",
            "",
            m.start(),
            alt=aria,
            name=(cls or "inline-svg"),
            dims=dims,
            inline_svg=svg_markup,
        )

    # CSS url(...) in <style> blocks
    for sm in STYLE_BLOCK_RE.finditer(html):
        block, base_pos = sm.group(1), sm.start(1)
        for um in CSS_URL_RE.finditer(block):
            raw = um.group(2)
            if raw.startswith("data:image/svg"):
                add("css-bg", raw, base_pos + um.start(), name="inline-mask.svg")
            elif ext_of(raw) in RASTER_EXTS | VIDEO_EXTS:
                add("css-bg", to_abs(raw, base), base_pos + um.start(), name=raw.split("/")[-1])

    return records


def dedupe(records: list[dict]) -> list[dict]:
    by_key: dict[str, dict] = {}
    for r in records:
        key = logical_key(r["url"]) if r["url"] else hashlib.md5(
            (r.get("inline_svg") or r["name"]).encode()
        ).hexdigest()[:12]
        if key not in by_key:
            r["count"] = 1
            by_key[key] = r
        else:
            by_key[key]["count"] += 1
            # keep the variant list union
            if r.get("variants"):
                merged = set(by_key[key].get("variants") or []) | set(r["variants"])
                by_key[key]["variants"] = sorted(merged)
    return list(by_key.values())


def write_report(records: list[dict], out_html: Path, base: str) -> None:
    by_role: dict[str, list[dict]] = {}
    for r in records:
        by_role.setdefault(r["role"], []).append(r)
    type_counts = Counter(r["asset_type"] for r in records)
    role_counts = Counter(r["role"] for r in records)

    def thumb(r: dict) -> str:
        if r.get("inline_svg"):
            return f'<div class="svgwrap">{r["inline_svg"]}</div>'
        u = r["url"]
        if not u:
            return '<div class="ph">—</div>'
        if r["asset_type"] == "video":
            return f'<video class="thumb" src="{u}" muted preload="metadata"></video>'
        return f'<img class="thumb" loading="lazy" src="{u}" alt="">'

    cards = []
    for role in sorted(by_role, key=lambda k: -len(by_role[k])):
        items = by_role[role]
        cells = []
        for r in items:
            sigs = ", ".join(r["signals"][:4])
            cells.append(
                f"""<figure class="cell">
                  <div class="media">{thumb(r)}</div>
                  <figcaption>
                    <span class="type type-{r['asset_type']}">{r['asset_type']}</span>
                    <code class="name">{r['name'][:42]}</code>
                    <span class="meta">{r['placement']['landmark']} · {sigs}</span>
                  </figcaption>
                </figure>"""
            )
        cards.append(
            f"""<section class="role">
              <h2>{role} <span class="badge">{len(items)}</span></h2>
              <div class="grid">{''.join(cells)}</div>
            </section>"""
        )

    type_chips = " ".join(
        f'<span class="chip">{t} <b>{c}</b></span>' for t, c in type_counts.most_common()
    )
    role_chips = " ".join(
        f'<span class="chip">{t} <b>{c}</b></span>' for t, c in role_counts.most_common()
    )

    html = f"""<!doctype html><html><head><meta charset="utf-8">
<title>Brand asset map — {base}</title>
<style>
  :root {{ color-scheme: light; }}
  * {{ box-sizing: border-box; }}
  body {{ margin:0; font:14px/1.5 -apple-system,Inter,Segoe UI,sans-serif; color:#1c2a21; background:#f6f7f5; }}
  header {{ padding:28px 32px; border-bottom:1px solid #e2e6e1; background:#fff; }}
  h1 {{ margin:0 0 4px; font-size:20px; }}
  .sub {{ color:#5d6b61; font-size:13px; }}
  .chips {{ margin-top:14px; display:flex; flex-wrap:wrap; gap:6px; }}
  .chip {{ background:#eef1ed; border:1px solid #e2e6e1; border-radius:999px; padding:3px 10px; font-size:12px; color:#3a473e; }}
  .chip b {{ color:#1f8a5b; }}
  main {{ padding:24px 32px 60px; }}
  .role {{ margin-bottom:30px; }}
  .role h2 {{ font-size:13px; text-transform:uppercase; letter-spacing:.08em; color:#3a473e; display:flex; align-items:center; gap:8px; }}
  .badge {{ background:#1f8a5b; color:#fff; border-radius:999px; padding:1px 8px; font-size:11px; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(180px,1fr)); gap:14px; margin-top:12px; }}
  .cell {{ margin:0; background:#fff; border:1px solid #e2e6e1; border-radius:12px; overflow:hidden; }}
  .media {{ height:120px; display:grid; place-items:center; background:#fafbfa; border-bottom:1px solid #eef1ed; padding:10px; }}
  .thumb {{ max-width:100%; max-height:100px; object-fit:contain; }}
  .svgwrap {{ max-width:80px; max-height:80px; color:#1c2a21; }}
  .svgwrap svg {{ max-width:80px; max-height:80px; }}
  .ph {{ color:#b7c0b8; font-size:24px; }}
  figcaption {{ padding:10px; display:flex; flex-direction:column; gap:4px; }}
  .type {{ align-self:flex-start; font-size:11px; font-weight:600; padding:1px 7px; border-radius:6px; background:#eef1ed; color:#3a473e; }}
  .type-photo {{ background:#e7f0fb; color:#1f5fa8; }}
  .type-video {{ background:#fbe9e7; color:#b3402f; }}
  .type-icon {{ background:#eef1ed; color:#3a473e; }}
  .type-logo {{ background:#f3ecfb; color:#6b3fa0; }}
  .type-background, .type-texture {{ background:#fdf3e0; color:#9a6a14; }}
  .type-animated {{ background:#e7faf0; color:#1f8a5b; }}
  .name {{ font-size:11px; color:#1c2a21; word-break:break-all; }}
  .meta {{ font-size:11px; color:#7c8a80; }}
</style></head><body>
<header>
  <h1>Brand asset map</h1>
  <div class="sub">Source: {base} · {len(records)} logical assets harvested + role-mapped (heuristic)</div>
  <div class="chips"><b style="font-size:12px;color:#5d6b61">TYPE</b> {type_chips}</div>
  <div class="chips"><b style="font-size:12px;color:#5d6b61">ROLE</b> {role_chips}</div>
</header>
<main>{''.join(cards)}</main>
</body></html>"""
    out_html.write_text(html, encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description="Harvest + role-map brand assets from captured HTML.")
    ap.add_argument("--html", required=True, type=Path)
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()

    html = args.html.read_text(encoding="utf-8", errors="ignore")
    base = args.base_url.rstrip("/")

    records = dedupe(harvest(html, base))
    records.sort(key=lambda r: (r["role"], r["asset_type"], -r.get("count", 1)))

    args.out.mkdir(parents=True, exist_ok=True)
    manifest = {
        "source": base,
        "total_logical_assets": len(records),
        "by_type": dict(Counter(r["asset_type"] for r in records)),
        "by_role": dict(Counter(r["role"] for r in records)),
        "assets": records,
    }
    (args.out / "assets-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    write_report(records, args.out / "assets-report.html", base)

    print(f"Harvested {len(records)} logical assets")
    print("  by type:", manifest["by_type"])
    print("  by role:", manifest["by_role"])
    print(f"  manifest: {args.out / 'assets-manifest.json'}")
    print(f"  report:   {args.out / 'assets-report.html'}")


if __name__ == "__main__":
    main()
