#!/usr/bin/env python3
"""curate_assets.py — manifest-driven asset curation from a saved-page capture.

Generalized from the (frozen) experiments/remote-e2e/curate_assets.py, which was a
hardcoded (source, dest) tuple list for one brand. This version:

  --manifest curation.yaml   explicit curation: copy globs with sanitized dest
                             names + use-case tags, and an inline-SVG extraction
                             block (the Remote lesson: customer logo VECTORS often
                             live as inline <svg> in the DOM, not as files)
  --auto                     heuristic first pass: copies every raster/vector from
                             the capture's *_files dir with a sanitized kebab name
                             and a keyword tag guess, and extracts deduped inline
                             SVGs from logo-ish containers

Both modes write FLAT into <brand-dir>/assets/ (parity with existing brands) and
emit assets-manifest.json — the starting point the extraction agent refines into
the authored assets-tagged.json. Existing files are never overwritten unless
--force. Source capture stays untouched.

MEDIA SEMANTICS DRAFT (media semantics 2026-07, spec/media-assets-schema.md): the
same pass also emits media-assets-draft.yaml — stable logical-asset ids, content-
hash variant dedupe (identical bytes collapse into one entry's variants[]),
Pillow-measured stats (intrinsic geometry, alpha, dominant hue, luminance band,
busyness; gracefully skipped when Pillow is unavailable or a file cannot decode),
and a kind hint mapped from the existing TAG_GUESSES. The draft is AGENT-REFINED
into the authored media-assets.yaml (the same draft→authored convention as
assets-manifest → assets-tagged); --no-media-draft skips it.

Manifest shape (curation.yaml):
    copy:
      - { src: "hero-*.webp",  dest: hero-illustration.webp, tag: hero-illustration }
      - { src: "logo_*.webp",  tag: integration-logo }          # dest: sanitized src
    inlineSvg:
      containerClassRe: "social-proof|logo"    # containers to harvest <svg> from
      destPrefix: logo-inline                  # -> logo-inline-00.svg ...
      tag: logo-wall-logo

Usage:
    ./venv/bin/python tools/extract/curate_assets.py --capture screenshots/<brand>/ \
        --brand-dir runs/<brand>/brand --auto
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path
from urllib.parse import unquote

SCHEMA = "assets-curation.v1"

RASTER_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".avif", ".gif", ".svg"}
SKIP_NAME_RE = re.compile(r"sprite|favicon|pixel|tracking", re.I)
DEFAULT_SVG_CONTAINER_RE = r"logo|social-proof|customer|partner|client|brand|marquee"

# filename-keyword → use-case tag guesses (agent refines; generic roles only)
TAG_GUESSES = [
    (re.compile(r"logo|wordmark", re.I), "logo"),
    (re.compile(r"badge|award|leader|top-?\d+", re.I), "award-badge"),
    (re.compile(r"rating|review|stars?", re.I), "rating-badge"),
    (re.compile(r"avatar|profile|headshot|portrait", re.I), "testimonial-avatar"),
    (re.compile(r"icon", re.I), "feature-icon"),
    (re.compile(r"hero", re.I), "hero-illustration"),
    (re.compile(r"background|bg[-_]|noise|texture|gradient", re.I), "background-art"),
    (re.compile(r"card|panel|snippet|screenshot|ui[-_]", re.I), "product-graphic"),
]

# tag guess → media-assets.v1 kind HINT (media semantics 2026-07; the draft's
# initial reading, agent-corrected against the grounding evidence). Rights guess
# rides beside it: award/rating/store badges and third-party logo walls are
# someone else's marks (AS-67), everything else defaults to the brand's own art.
KIND_GUESSES = {
    "logo": ("logo-third-party", "third-party-mark"),
    "logo-wall-logo": ("logo-third-party", "third-party-mark"),
    "award-badge": ("badge-review-award", "third-party-mark"),
    "rating-badge": ("badge-review-award", "third-party-mark"),
    "testimonial-avatar": ("portrait", "own"),
    "feature-icon": ("spot-icon", "own"),
    "hero-illustration": ("illustration", "own"),
    "background-art": ("background-art", "own"),
    "product-graphic": ("product-ui-screenshot", "own"),
    "decorative": ("photograph", "own"),
}


def find_saved_html(capture: Path) -> Path | None:
    pages = sorted(capture.glob("*.htm*"), key=lambda p: p.stat().st_size, reverse=True)
    return pages[0] if pages else None


def find_files_dir(capture: Path, html_path: Path | None) -> Path | None:
    if html_path is not None:
        cand = html_path.with_name(html_path.stem + "_files")
        if cand.is_dir():
            return cand
    dirs = [d for d in capture.iterdir() if d.is_dir() and d.name.endswith("_files")]
    return dirs[0] if dirs else None


def sanitize(name: str) -> str:
    stem, dot, ext = unquote(name).rpartition(".")
    if not dot:
        stem, ext = name, ""
    stem = re.sub(r"@\d+x$", "", stem)
    stem = re.sub(r"[^a-zA-Z0-9]+", "-", stem).strip("-").lower()
    stem = re.sub(r"-{2,}", "-", stem) or "asset"
    return f"{stem}.{ext.lower()}" if ext else stem


def tag_guess(name: str) -> str:
    for rx, tag in TAG_GUESSES:
        if rx.search(name):
            return tag
    return "decorative"


def _copy(src: Path, dest: Path, force: bool, entries: list, origin: str, tag: str):
    if dest.exists() and not force:
        print(f"  [skip] {dest.name} exists")
    else:
        shutil.copy2(src, dest)
    entries.append({"dest": dest.name, "source": str(src), "origin": origin,
                    "bytes": dest.stat().st_size, "tagGuess": tag})


def curate_from_manifest(manifest: dict, files_dir: Path | None, html_path: Path | None,
                         out: Path, force: bool) -> list[dict]:
    entries: list[dict] = []
    for item in manifest.get("copy") or []:
        pattern = str(item.get("src") or "")
        if not pattern or files_dir is None:
            continue
        matches = sorted(files_dir.rglob(pattern))
        if not matches:
            print(f"  [warn] manifest src matched nothing: {pattern}")
            continue
        for m in matches:
            dest_name = str(item["dest"]) if item.get("dest") and len(matches) == 1 \
                else sanitize(m.name)
            _copy(m, out / dest_name, force, entries, "files",
                  str(item.get("tag") or tag_guess(dest_name)))
    svg_cfg = manifest.get("inlineSvg")
    if svg_cfg and html_path is not None:
        entries += extract_inline_svgs(
            html_path, out, force,
            container_re=str(svg_cfg.get("containerClassRe") or DEFAULT_SVG_CONTAINER_RE),
            dest_prefix=str(svg_cfg.get("destPrefix") or "logo-inline"),
            tag=str(svg_cfg.get("tag") or "logo-wall-logo"))
    return entries


def curate_auto(files_dir: Path | None, html_path: Path | None, out: Path,
                min_bytes: int, force: bool) -> list[dict]:
    entries: list[dict] = []
    if files_dir is not None:
        for p in sorted(files_dir.rglob("*")):
            if not p.is_file() or p.suffix.lower() not in RASTER_EXTS:
                continue
            if p.stat().st_size < min_bytes or SKIP_NAME_RE.search(p.name):
                continue
            dest_name = sanitize(p.name)
            _copy(p, out / dest_name, force, entries, "files", tag_guess(dest_name))
    if html_path is not None:
        entries += extract_inline_svgs(html_path, out, force,
                                       container_re=DEFAULT_SVG_CONTAINER_RE,
                                       dest_prefix="logo-inline", tag="logo-wall-logo")
    return entries


def extract_inline_svgs(html_path: Path, out: Path, force: bool, *,
                        container_re: str, dest_prefix: str, tag: str) -> list[dict]:
    """Harvest inline <svg> vectors from containers whose class matches
    ``container_re`` (logo walls ship as inline DOM vectors, not files). Dedupes
    by normalized markup hash (swiper/carousel duplicates collapse); skips
    sprite/def-only and trivially small svgs. Names carry an alt hint when the
    container exposes one (aria-label / img alt / title)."""
    from bs4 import BeautifulSoup  # local import: --help stays dependency-free
    soup = BeautifulSoup(html_path.read_text(errors="replace"), "html.parser")
    rx = re.compile(container_re, re.I)
    entries: list[dict] = []
    seen: set[str] = set()
    n = 0
    for container in soup.find_all(class_=rx):
        for svg in container.find_all("svg"):
            markup = str(svg)
            if len(markup) < 120:
                continue
            inner = re.sub(r"\s+", "", markup)
            if "<use" in inner and "<path" not in inner:
                continue  # sprite reference, not a drawable vector
            digest = hashlib.sha1(inner.encode()).hexdigest()
            if digest in seen:
                continue
            seen.add(digest)
            alt = (svg.get("aria-label") or "").strip()
            if not alt:
                t = svg.find("title")
                alt = t.get_text(strip=True) if t else ""
            slug = re.sub(r"[^a-z0-9]+", "-", alt.lower()).strip("-") if alt else ""
            dest_name = f"{dest_prefix}-{slug or f'{n:02d}'}.svg"
            dest = out / dest_name
            if dest.exists() and not force:
                print(f"  [skip] {dest.name} exists")
            else:
                dest.write_text(markup)
            entries.append({"dest": dest_name, "source": f"inline-svg:{digest[:10]}",
                            "origin": "inline-svg", "bytes": dest.stat().st_size,
                            "tagGuess": tag, "altHint": alt[:60]})
            n += 1
    print(f"  extracted {n} inline SVGs (deduped)")
    return entries


# ── media-assets draft emission (media semantics 2026-07) ───────────────────────────

def _asset_slug(name: str) -> str:
    stem = Path(unquote(name)).stem
    stem = re.sub(r"@\d+x$", "", stem)
    stem = re.sub(r"^\d+-", "", stem)           # curated numeric prefixes are not identity
    stem = re.sub(r"[^a-zA-Z0-9]+", "-", stem).strip("-").lower()
    return re.sub(r"-{2,}", "-", stem) or "asset"


def pillow_stats(path: Path) -> dict | None:
    """Deterministic per-file image stats via Pillow: intrinsic geometry, alpha
    presence, dominant hue (circular mean over saturated pixels), luminance band,
    saturation band, busyness (neighbor-difference proxy). Returns None when Pillow
    is unavailable or the file cannot decode (SVGs stay unmeasured) — the graceful
    skip the draft contract documents."""
    try:
        from PIL import Image
    except Exception:
        return None
    try:
        with Image.open(path) as im:
            w, h = im.size
            has_alpha = "A" in im.getbands()
            alpha_used = False
            if has_alpha:
                lo, _hi = im.getchannel("A").getextrema()
                alpha_used = lo < 250
            small = im.convert("RGB").resize((48, 48))
    except Exception:
        return None
    import math
    px = list(small.getdata())
    lum = [0.2126 * r + 0.7152 * g + 0.0722 * b for r, g, b in px]
    mean_lum = sum(lum) / len(lum)
    band = "dark" if mean_lum < 85 else ("mid" if mean_lum < 170 else "light")
    hsv = list(small.convert("HSV").getdata())
    sats = [s for _h, s, _v in hsv]
    mean_sat = sum(sats) / len(sats)
    sat_band = "muted" if mean_sat < 40 else ("moderate" if mean_sat < 120 else "vivid")
    hue_pts = [(math.cos(hh / 255 * 2 * math.pi), math.sin(hh / 255 * 2 * math.pi))
               for hh, s, v in hsv if s > 60 and v > 40]
    dominant_hue = None
    if len(hue_pts) >= len(hsv) * 0.05:
        cx = sum(p[0] for p in hue_pts) / len(hue_pts)
        cy = sum(p[1] for p in hue_pts) / len(hue_pts)
        dominant_hue = round((math.degrees(math.atan2(cy, cx)) % 360))
    # busyness: mean absolute neighbor delta on the 48px luma grid
    diffs = []
    for y in range(48):
        for x in range(47):
            diffs.append(abs(lum[y * 48 + x] - lum[y * 48 + x + 1]))
    for y in range(47):
        for x in range(48):
            diffs.append(abs(lum[y * 48 + x] - lum[(y + 1) * 48 + x]))
    mean_diff = sum(diffs) / len(diffs)
    busyness = "low" if mean_diff < 8 else ("medium" if mean_diff < 20 else "high")
    ratio = round(w / h, 4) if h else None
    orientation = None
    if ratio:
        orientation = "square" if 0.9 <= ratio <= 1.1 else (
            "landscape" if ratio > 1.1 else "portrait")
    return {
        "intrinsic": {"w": w, "h": h},
        "intrinsicAspect": ratio,
        "orientation": orientation,
        "alpha": bool(alpha_used),
        "stats": {"dominantHue": dominant_hue, "luminanceBand": band,
                  "busyness": busyness, "saturationBand": sat_band,
                  "source": "measured"},
    }


def build_media_draft(assets_dir: Path, entries: list[dict]) -> dict:
    """The media-assets.v1 DRAFT: one logical asset per curated file, content-hash
    dedupe folding byte-identical files into the largest entry's variants[]
    (relation: duplicate), Pillow stats where measurable, and TAG_GUESSES-derived
    kind/rights hints. status: draft — the Layout Analyst refines it into the
    authored media-assets.yaml (never ship the draft as the artifact)."""
    by_digest: dict[str, list[dict]] = {}
    for e in sorted(entries, key=lambda x: str(x.get("dest") or "")):
        name = str(e.get("dest") or "")
        p = assets_dir / name
        if not p.is_file():
            continue
        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        by_digest.setdefault(digest, []).append(e)

    drafts: list[dict] = []
    seen_ids: set[str] = set()
    for digest, group in sorted(by_digest.items(),
                                key=lambda kv: str(kv[1][0].get("dest"))):
        group = sorted(group, key=lambda e: (-int(e.get("bytes") or 0),
                                             str(e.get("dest"))))
        canon = group[0]
        name = str(canon["dest"])
        slug = _asset_slug(name)
        base, n = slug, 2
        while slug in seen_ids:
            slug, n = f"{base}-{n}", n + 1
        seen_ids.add(slug)
        tag = str(canon.get("tagGuess") or "decorative")
        kind, rights = KIND_GUESSES.get(tag, ("photograph", "own"))
        facts = pillow_stats(assets_dir / name) or {
            "intrinsic": None, "intrinsicAspect": None, "orientation": None,
            "alpha": None, "stats": None}
        facts["focalPoint"] = None      # null = UNKNOWN (spec §2) — never guessed
        facts["safeCrop"] = None
        facts["altHarvested"] = (str(canon.get("altHint")).strip()
                                 if canon.get("altHint") else None)
        entry = {
            "id": slug,
            "file": name,
            "assetSemantics": {"kind": kind, "subject": None},
            "facts": facts,
            "usageRights": rights,
            "treatmentDefaults": None,
            "compositionRoles": [],
            "provenance": {
                "source": ("inline-svg" if str(canon.get("origin")) == "inline-svg"
                           else "capture-files"),
                "sections": [], "confidence": "low"},
            "tagGuess": tag,
        }
        variants = [{"file": str(e["dest"]), "relation": "duplicate", "scale": None,
                     "note": "byte-identical to the canonical file (content-hash dedupe)"}
                    for e in group[1:]]
        if variants:
            entry["variants"] = variants
        drafts.append(entry)
    return {
        "schemaVersion": "media-assets.v1",
        "status": "draft",
        "note": ("DRAFT emitted by curate_assets.py (media semantics 2026-07) — "
                 "kind/rights are TAG-GUESS hints and subjects/provenance are "
                 "unrefined. The Layout Analyst refines this into the authored "
                 "media-assets.yaml (spec/media-assets-schema.md §8); never ship "
                 "the draft as the artifact."),
        "assets": drafts,
    }


def emit_media_draft(brand_dir: Path, entries: list[dict]) -> Path:
    import yaml
    draft = build_media_draft(brand_dir / "assets", entries)
    path = brand_dir / "media-assets-draft.yaml"
    path.write_text(yaml.safe_dump(draft, sort_keys=False, allow_unicode=True,
                                   width=88))
    measured = sum(1 for a in draft["assets"]
                   if (a.get("facts") or {}).get("stats"))
    print(f"[done] media draft: {len(draft['assets'])} logical assets "
          f"({measured} with measured stats) -> {path.name}")
    return path


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--capture", type=Path, help="capture dir (auto-discovers html + _files)")
    ap.add_argument("--html", type=Path, help="explicit saved-page .html")
    ap.add_argument("--files-dir", type=Path, help="explicit *_files assets dir")
    ap.add_argument("--brand-dir", type=Path, required=True,
                    help="runs/<brand>/brand (assets/ + assets-manifest.json go here)")
    ap.add_argument("--manifest", type=Path, help="curation.yaml (explicit copy list)")
    ap.add_argument("--auto", action="store_true", help="heuristic copy-everything pass")
    ap.add_argument("--min-bytes", type=int, default=800,
                    help="--auto: skip files smaller than this (default 800)")
    ap.add_argument("--force", action="store_true", help="overwrite existing curated files")
    ap.add_argument("--no-media-draft", action="store_true",
                    help="skip the media-assets-draft.yaml emission (media semantics)")
    return ap


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if not args.manifest and not args.auto:
        raise SystemExit("choose a mode: --manifest curation.yaml and/or --auto")
    html_path = args.html
    files_dir = args.files_dir
    if args.capture:
        html_path = html_path or find_saved_html(args.capture)
        files_dir = files_dir or find_files_dir(args.capture, html_path)

    out = args.brand_dir / "assets"
    out.mkdir(parents=True, exist_ok=True)

    entries: list[dict] = []
    if args.manifest:
        import yaml
        manifest = yaml.safe_load(args.manifest.read_text()) or {}
        entries += curate_from_manifest(manifest, files_dir, html_path, out, args.force)
    if args.auto:
        entries += curate_auto(files_dir, html_path, out, args.min_bytes, args.force)

    # dedupe by dest (manifest wins over auto)
    by_dest: dict[str, dict] = {}
    for e in entries:
        by_dest.setdefault(e["dest"], e)
    manifest_path = args.brand_dir / "assets-manifest.json"
    manifest_path.write_text(json.dumps(
        {"schemaVersion": SCHEMA,
         "note": ("Curated capture assets — starting point for the authored "
                  "assets-tagged.json (agent refines tags/labels; "
                  "tools/refine_assets_vision.py can vision-check them)."),
         "entries": sorted(by_dest.values(), key=lambda e: e["dest"])}, indent=1))
    print(f"[done] curate: {len(by_dest)} assets in {out} -> {manifest_path.name}")
    if not args.no_media_draft:
        emit_media_draft(args.brand_dir, sorted(by_dest.values(),
                                                key=lambda e: e["dest"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
