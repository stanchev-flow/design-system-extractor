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
    return 0


if __name__ == "__main__":
    sys.exit(main())
