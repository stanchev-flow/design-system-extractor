#!/usr/bin/env python3
"""page_lane_brief.py — the measured section inventory for ONE captured page.

A multi-page brand's `brand.yaml` is a union: every page's sections live in one
layouts[] list. Handed that union, a generator has no way to know which bands
belong to the page it is rebuilding, so it composes a plausible SaaS outline
instead of the measured one (the invented stats band / testimonial wall).

Each layout declares the pages it was extracted from (`sourcePages`, stamped by
project_sections_to_patterns.py), so the lane is a filter, not a guess. This
module renders that lane as markdown facts a generation prompt can carry:
section order, the band's own copy, and the asset files measured in it.

Usage:
    ./venv/bin/python tools/page_lane_brief.py --brand-dir runs/<brand>/brand \
        --page home
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import yaml

CHROME_USE_CASES = {"navbar", "footer", "nav", "header", "chrome"}


def _section_index(token: str) -> int:
    """``home-section-03-div`` → 3; unknown → sentinel so order stays stable."""
    m = re.search(r"-section-(\d+)", str(token or "").lower())
    return int(m.group(1)) if m else 10_000


def lane_layouts(doc: dict, page: str) -> list[dict]:
    """The page's non-chrome layouts, in the order the source page shows them."""
    page = str(page or "").strip().lower()
    rows = []
    for layout in doc.get("layouts") or []:
        if not isinstance(layout, dict):
            continue
        if str(layout.get("useCase") or "").lower() in CHROME_USE_CASES:
            continue
        pages = {str(p).strip().lower() for p in (layout.get("sourcePages") or [])}
        if page not in pages:
            continue
        prov = [str(p) for p in (layout.get("provenance") or []) if str(p).startswith(page)]
        rows.append((min((_section_index(p) for p in prov), default=10_000), layout))
    rows.sort(key=lambda r: r[0])
    return [layout for _, layout in rows]


def _copy_lines(payload: dict) -> list[str]:
    out = []
    for key in ("eyebrow", "heading", "subheading", "body"):
        if payload.get(key):
            out.append(f"    {key}: {str(payload[key]).strip()}")
    items = payload.get("items")
    if isinstance(items, list) and items:
        out.append(f"    items ({len(items)}):")
        for item in items:
            if not isinstance(item, dict):
                continue
            head = str(item.get("heading") or item.get("label") or "").strip()
            body = str(item.get("body") or item.get("text") or "").strip()
            out.append(f"      - {head}" + (f" — {body}" if body else ""))
    return out


def asset_ids_by_file(brand_dir: Path) -> dict[str, str]:
    """filename → registry id, the key the framework's `assetById` takes.

    Slots bind FILES (that is what the page rendered) while the framework asset
    API is keyed by logical id, so the brief has to carry the translation or the
    generator looks up a filename, gets nothing back, and drops the image.
    """
    path = brand_dir / "media-assets.yaml"
    if not path.is_file():
        return {}
    registry = yaml.safe_load(path.read_text()) or {}
    out: dict[str, str] = {}
    for entry in registry.get("assets") or []:
        if not isinstance(entry, dict) or not entry.get("id"):
            continue
        for key in ("file", *(entry.get("variants") or [])):
            name = Path(str(entry.get(key) if key == "file" else key)).name
            if name:
                out.setdefault(name, str(entry["id"]))
    return out


def build_brief(brand_dir: Path, page: str) -> str:
    doc = yaml.safe_load((brand_dir / "brand.yaml").read_text()) or {}
    copy_path = brand_dir / "section-copy.yaml"
    copy_doc = (yaml.safe_load(copy_path.read_text()) or {}) if copy_path.is_file() else {}
    layout_copy = copy_doc.get("layoutCopy") or {}
    ids = asset_ids_by_file(brand_dir)

    layouts = lane_layouts(doc, page)
    if not layouts:
        return ""
    lines = [
        f"## Measured section inventory for the `{page}` page",
        "",
        f"This page has EXACTLY these {len(layouts)} body sections, in this order. "
        "Compose these and nothing else — no stats band, testimonial wall, pricing "
        "table, or FAQ unless it is listed here. Every heading, item, and image "
        "below was measured off the capture.",
        "",
    ]
    for i, layout in enumerate(layouts):
        lid = str(layout.get("id"))
        lines.append(f"{i + 1}. **{lid}** — useCase `{layout.get('useCase')}`, "
                     f"archetype `{layout.get('archetype')}`, "
                     f"surface `{layout.get('surfaceIntent')}`")
        band = next((str(p) for p in (layout.get("provenance") or [])
                     if str(p).lower().startswith(page)), "")
        if band:
            lines.append(f"    source band: sectionAssets(\"{band}\")")
        payload = layout_copy.get(lid)
        if isinstance(payload, dict):
            lines.extend(_copy_lines(payload))
        registers = [
            f"{slot.get('name')}={slot.get('sizeClass') or slot.get('textLen')}"
            for slot in (layout.get("slots") or [])
            if isinstance(slot, dict) and (slot.get("sizeClass") or slot.get("textLen"))
        ]
        if registers:
            lines.append(f"    measured type registers: {', '.join(registers)}")
        for slot in layout.get("slots") or []:
            if not isinstance(slot, dict) or not slot.get("assets"):
                continue
            files = [str(a) for a in slot["assets"]]
            lines.append(f"    {slot.get('name')} ({slot.get('role')}) — "
                         f"{len(files)} image(s) this section MUST render:")
            for f in files:
                lines.append(f"      assetById(\"{f}\")")
    lines.append("")
    lines.append("Every `assetById(...)` line above is an image the source section "
                 "shows: render it as an `<img>` with `bestSrc(...)` and the asset's "
                 "`alt`. A section that measured art and ships without it is a "
                 "regression, and a section's whole band can also be read in visual "
                 "order via `sectionAssets(\"<source band>\")`. Never reach for an "
                 "asset this inventory does not name for that section.")
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--brand-dir", type=Path, required=True)
    ap.add_argument("--page", required=True)
    return ap


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    brief = build_brief(args.brand_dir, args.page)
    if not brief:
        print(f"page_lane_brief: no layouts declare sourcePages: [{args.page}]")
        return 1
    print(brief)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
