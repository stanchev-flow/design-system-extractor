"""Apply role-mapped brand assets into generated pipeline HTML.

The pipeline emits asset *briefs* — placeholder <img>/<div> slots tagged with
`data-stt-asset-brief` describing the photo each slot wants. When a brand-asset
manifest is available (harvested + vision-classified + role-mapped from the
source site), this fills each slot with the brand's OWN asset, chosen to fit
the slot — instead of leaving placeholders or generating art.

This is the post-generation half of extraction Tier-1, callable both as a
pipeline step (`apply_brand_assets_file`) and standalone (tools CLI).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

BRIEF_TAG_RE = re.compile(r"<(img|div)\b[^>]*\bdata-stt-asset-brief\b[^>]*>", re.IGNORECASE)
SRC_RE = re.compile(r'\ssrc\s*=\s*"(.*?)"', re.IGNORECASE | re.DOTALL)
STYLE_RE = re.compile(r'\sstyle\s*=\s*"(.*?)"', re.IGNORECASE | re.DOTALL)
BRIEF_RE = re.compile(r'data-stt-asset-brief\s*=\s*"(.*?)"', re.IGNORECASE | re.DOTALL)

JUNK_LABEL = (
    "gradient", "blur", "transparent", "checker", "placeholder",
    "swatch", "mask", "noise", "scrim",
)
TYPE_PRIORITY = {"photo": 0, "background": 1, "illustration": 2}


def _area(a: dict) -> int:
    return (a.get("width") or 0) * (a.get("height") or 0)


def _best_src(a: dict) -> str:
    return a.get("displayUrl") or a.get("url") or ""


def build_photo_pool(assets_data: dict) -> list[dict]:
    """Real photographic assets suited to full-frame brief slots.

    Briefs request documentary photography, so prefer type=photo, then real
    backgrounds, then product illustrations; drop decorative/junk (gradients,
    transparency checkerboards, masks) and square avatar crops.
    """
    by_role = assets_data.get("byRole", {})
    pool: list[dict] = []
    for role in ("background", "content", "card/feature", "hero", "testimonial/avatar"):
        for a in by_role.get(role, []):
            if not a.get("url") or a.get("type") not in TYPE_PRIORITY:
                continue
            blob = (a.get("label", "") + " " + a.get("alt", "")).lower()
            if any(j in blob for j in JUNK_LABEL):
                continue
            asp = a.get("aspect")
            if asp and asp < 0.7:
                continue
            pool.append(a)
    seen, uniq = set(), []
    for a in sorted(pool, key=lambda x: (TYPE_PRIORITY[x["type"]], -_area(x))):
        if a["id"] not in seen:
            seen.add(a["id"])
            uniq.append(a)
    return uniq


def _role_for_brief(brief: str, tag: str) -> str:
    b = brief.lower() + " " + tag.lower()
    if "hero" in b:
        return "hero"
    if "scrim" in b or "cta" in b or "behind a dark" in b:
        return "cta"
    return "content"


def _set_src(tag: str, url: str) -> str:
    if SRC_RE.search(tag):
        return SRC_RE.sub(f' src="{url}"', tag, count=1)
    return re.sub(r"^<(img|div)\b", rf'<\1 src="{url}"', tag, count=1, flags=re.IGNORECASE)


def _set_bg(tag: str, url: str) -> str:
    decl = (
        f"background-image:url('{url}');background-size:cover;"
        "background-position:center;background-repeat:no-repeat;"
    )
    m = STYLE_RE.search(tag)
    if m:
        merged = (m.group(1).rstrip("; ") + ";" + decl) if m.group(1).strip() else decl
        return STYLE_RE.sub(f' style="{merged}"', tag, count=1)
    return re.sub(r"^<(img|div)\b", rf'<\1 style="{decl}"', tag, count=1, flags=re.IGNORECASE)


def inject_brand_assets(html: str, assets_data: dict) -> tuple[str, dict]:
    """Pure transform: fill brief slots from the manifest. Returns (html, payload)."""
    pool = build_photo_pool(assets_data)
    if not pool:
        return html, {"status": "no_brand_assets", "filled": 0, "slots": []}

    used: list[str] = []
    slots: list[dict] = []

    def next_asset() -> dict:
        for a in pool:
            if a["id"] not in used:
                return a
        return pool[len(used) % len(pool)]

    def replace(m: re.Match) -> str:
        tag = m.group(0)
        is_img = tag[1:4].lower() == "img"
        brief_m = BRIEF_RE.search(tag)
        brief = brief_m.group(1) if brief_m else ""
        role = _role_for_brief(brief, tag)
        asset = next_asset()
        used.append(asset["id"])
        url = _best_src(asset)
        slots.append(
            {
                "slot": len(slots) + 1,
                "carrier": "img" if is_img else "div",
                "role": role,
                "asset_id": asset["id"],
                "label": asset.get("label", ""),
                "type": asset.get("type", ""),
                "url": url,
            }
        )
        return _set_src(tag, url) if is_img else _set_bg(tag, url)

    new_html = BRIEF_TAG_RE.sub(replace, html)
    payload = {"status": "brand_assets_applied", "filled": len(slots), "slots": slots}
    return new_html, payload


def apply_brand_assets_file(
    html_path: Path, manifest_path: Path, out_path: Path | None = None
) -> dict:
    """Read HTML + manifest, inject assets, write result (in place unless out_path)."""
    html = Path(html_path).read_text(encoding="utf-8")
    assets_data = json.loads(Path(manifest_path).read_text())
    new_html, payload = inject_brand_assets(html, assets_data)
    target = Path(out_path) if out_path else Path(html_path)
    if payload["filled"]:
        target.write_text(new_html, encoding="utf-8")
    payload["manifest"] = str(manifest_path)
    payload["output"] = str(target)
    return payload
