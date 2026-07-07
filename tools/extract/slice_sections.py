#!/usr/bin/env python3
"""slice_sections.py — split a full-page capture screenshot into per-section crops.

The crops are the vision-grounding inputs (one model call per section). Section
boundaries come, in priority order, from:

  1. --rects section-rects.json   (measure_computed output) — rect y-ranges are
     scaled by screenshot-width / viewport-width; overlapping/adjacent rects are
     merged. NOTE: rects measured with JS disabled can drift from a live-site
     screenshot — eyeball the crops (crops-manifest.json lists y-ranges) before
     spending grounding calls.
  2. --boundaries y1,y2,...       explicit pixel cut lines (screenshot space).
  3. --slices N                   N equal slices with 12% overlap (last resort).

Writes crops + crops-manifest.json into --out-dir. Read-only over the screenshot.

Usage:
    ./venv/bin/python tools/extract/slice_sections.py --capture screenshots/<brand>/ \
        --rects runs/<brand>/brand/evidence/section-rects.json \
        --out-dir runs/<brand>/brand/evidence/crops/
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SCHEMA = "section-crops.v1"
SCREENSHOT_EXTS = (".webp", ".png", ".jpg", ".jpeg")


def find_screenshot(capture: Path) -> Path:
    shots = [p for p in capture.iterdir()
             if p.is_file() and p.suffix.lower() in SCREENSHOT_EXTS]
    if not shots:
        raise SystemExit(f"no screenshot ({'/'.join(SCREENSHOT_EXTS)}) in {capture}")
    return max(shots, key=lambda p: p.stat().st_size)


def _slug(text: str, fallback: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return (s[:48] or fallback).strip("-")


def spans_from_rects(rects_doc: dict, img_w: int, img_h: int,
                     min_height: int, tolerance: int = 12) -> list[dict]:
    """Scale rects into screenshot space, then resolve overlaps WITHOUT merging:
    adjacent page sections legitimately touch, so a rect fully inside the
    previous span is dropped (nested wrapper/duplicate) and a partial overlap is
    trimmed to start where the previous span ends. Sections stay one-crop-each."""
    viewport_w = ((rects_doc.get("viewport") or {}).get("w")) or img_w
    scale = img_w / viewport_w if viewport_w else 1.0
    raw = []
    for s in (rects_doc.get("chrome") or []):
        r = s.get("rect") or {}
        raw.append({"y0": r.get("y", 0) * scale, "y1": (r.get("y", 0) + r.get("h", 0)) * scale,
                    "label": s.get("name", "chrome"), "classes": s.get("classes", ""),
                    "heading": ""})
    for s in (rects_doc.get("sections") or []):
        r = s.get("rect") or {}
        raw.append({"y0": r.get("y", 0) * scale, "y1": (r.get("y", 0) + r.get("h", 0)) * scale,
                    "label": s.get("classes") or s.get("tag") or "section",
                    "classes": s.get("classes", ""), "heading": s.get("heading", "")})
    raw = [s for s in raw if (s["y1"] - s["y0"]) >= min_height]
    raw.sort(key=lambda s: (s["y0"], -(s["y1"] - s["y0"])))
    spans: list[dict] = []
    for s in raw:
        s = dict(s)
        if spans:
            prev = spans[-1]
            if s["y0"] < prev["y1"] - tolerance:
                if s["y1"] <= prev["y1"] + tolerance:
                    continue  # nested inside the previous span — duplicate coverage
                s["y0"] = prev["y1"]  # partial overlap — trim, don't merge
        if (s["y1"] - s["y0"]) < min_height:
            continue
        spans.append(s)
    for s in spans:
        s["y0"] = max(0.0, min(s["y0"], img_h))
        s["y1"] = max(0.0, min(s["y1"], img_h))
    return [s for s in spans if s["y1"] > s["y0"]]


def spans_from_boundaries(bounds: list[int], img_h: int) -> list[dict]:
    ys = sorted({0, img_h, *[max(0, min(int(b), img_h)) for b in bounds]})
    return [{"y0": a, "y1": b, "label": f"band-{i:02d}", "classes": "", "heading": ""}
            for i, (a, b) in enumerate(zip(ys, ys[1:])) if b - a > 8]


def spans_equal(n: int, img_h: int, overlap: float = 0.12) -> list[dict]:
    step = img_h / n
    pad = step * overlap
    out = []
    for i in range(n):
        y0 = max(0, i * step - pad)
        y1 = min(img_h, (i + 1) * step + pad)
        out.append({"y0": y0, "y1": y1, "label": f"slice-{i:02d}",
                    "classes": "", "heading": ""})
    return out


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--capture", type=Path, help="capture dir (largest webp/png wins)")
    ap.add_argument("--screenshot", type=Path, help="explicit full-page screenshot")
    ap.add_argument("--rects", type=Path, help="section-rects.json from measure_computed")
    ap.add_argument("--boundaries", help="explicit csv of y cut lines (screenshot px)")
    ap.add_argument("--slices", type=int, default=0, help="fallback: N equal slices")
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--pad", type=int, default=24, help="extra px above/below each crop")
    ap.add_argument("--min-height", type=int, default=140,
                    help="ignore rects shorter than this (post-scale px)")
    ap.add_argument("--overlap-tolerance", type=int, default=12,
                    help="rect overlap slack before trimming/dropping (px)")
    ap.add_argument("--max-crop-height", type=int, default=4200,
                    help="split crops taller than this")
    return ap


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    from PIL import Image  # local import: --help stays dependency-free
    shot = args.screenshot or (find_screenshot(args.capture) if args.capture else None)
    if shot is None:
        raise SystemExit("provide --capture <dir> or --screenshot <file>")
    img = Image.open(shot)
    img_w, img_h = img.size

    if args.rects and args.rects.is_file():
        rects_doc = json.loads(args.rects.read_text())
        spans = spans_from_rects(rects_doc, img_w, img_h, args.min_height,
                                 args.overlap_tolerance)
        mode = "rects"
    elif args.boundaries:
        spans = spans_from_boundaries(
            [int(x) for x in args.boundaries.split(",") if x.strip()], img_h)
        mode = "boundaries"
    elif args.slices:
        spans = spans_equal(args.slices, img_h)
        mode = "equal-slices"
    else:
        raise SystemExit("no boundary source: pass --rects, --boundaries or --slices N")
    if not spans:
        raise SystemExit(f"no usable section spans (mode={mode}) — check inputs")

    # split over-tall spans so every crop stays model-readable
    final: list[dict] = []
    for s in spans:
        height = s["y1"] - s["y0"]
        parts = max(1, int(height // args.max_crop_height) + (1 if height % args.max_crop_height else 0))
        step = height / parts
        for k in range(parts):
            final.append({**s, "y0": s["y0"] + k * step, "y1": s["y0"] + (k + 1) * step,
                          "label": s["label"] if parts == 1 else f"{s['label']}-part{k}"})

    args.out_dir.mkdir(parents=True, exist_ok=True)
    manifest = []
    for i, s in enumerate(final):
        y0 = int(max(0, s["y0"] - args.pad))
        y1 = int(min(img_h, s["y1"] + args.pad))
        crop = img.crop((0, y0, img_w, y1))
        name = f"section-{i:02d}-{_slug(s['label'], f'sec{i:02d}')}.png"
        crop_path = args.out_dir / name
        crop.save(crop_path)
        manifest.append({"file": name, "index": i, "yTop": y0, "yBottom": y1,
                         "classes": s.get("classes", ""), "heading": s.get("heading", ""),
                         "sourceLabel": s["label"]})
        print(f"  {name}  y {y0}-{y1}  ({y1 - y0}px)")
    (args.out_dir / "crops-manifest.json").write_text(json.dumps(
        {"schemaVersion": SCHEMA, "screenshot": str(shot),
         "imageSize": {"w": img_w, "h": img_h}, "mode": mode,
         "crops": manifest}, indent=1))
    print(f"[done] slice: {len(manifest)} crops ({mode}) -> {args.out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
