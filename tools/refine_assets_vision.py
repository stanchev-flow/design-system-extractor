#!/usr/bin/env python3
"""Vision refinement pass for the harvested asset manifest.

The heuristic harvester (`harvest_assets.py`) is fast but blind — it guesses
type/role from filenames, extensions and DOM position. This pass actually
*looks* at each asset and corrects it:

  • rasters (incl. AVIF) are normalized to small PNGs and shown to Claude
  • inline SVGs / data-URI masks are sent as markup text
  • videos are left on their heuristic label (no still to inspect)

Claude returns, per asset: refined asset_type, placement role, an
icon-vs-illustration call, and a short human label. The merged manifest keeps
the original heuristic values plus a `changed` flag, and the report highlights
every correction so you can see what vision fixed.

Usage:
    python tools/refine_assets_vision.py \\
        --manifest screenshots/hackathon-test/source/assets/assets-manifest.json \\
        --model claude-opus-4-8 --limit 0 --batch 6
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
from io import BytesIO
from pathlib import Path
from urllib.parse import unquote

import requests
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

RASTER_EXTS = {"png", "jpg", "jpeg", "webp", "avif", "gif"}
TYPES = "icon | logo | photo | illustration | background | texture | avatar | video | animated | vector | other"
ROLES = "navigation | navigation/logo | hero | logo-wall | card/feature | testimonial/avatar | background | footer | content | media/video"

SYSTEM = (
    "You are a senior brand designer cataloguing a website's visual assets so an "
    "AI page builder can re-place them correctly. For each asset decide its true "
    "type and the role it plays on the page. Be decisive and consistent. "
    "Return ONLY a JSON array, no prose."
)

SCHEMA_HINT = (
    f'Each element: {{"index": <int>, "asset_type": "<{TYPES}>", '
    f'"role": "<{ROLES}>", "icon_or_illustration": "icon|illustration|na", '
    '"label": "<=4 word human label", "note": "<short why, optional>"}'
)


def load_env() -> None:
    env_file = ROOT / ".env.local"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def ext_of(url: str) -> str:
    m = re.search(r"\.([a-z0-9]{2,5})(?:\?|#|$)", url.split("/")[-1], re.IGNORECASE)
    return m.group(1).lower() if m else ""


def fetch_png_b64(url: str, max_px: int = 224) -> str | None:
    """Download any raster (incl. AVIF), flatten + downscale, return PNG base64."""
    try:
        r = requests.get(url, timeout=25)
        r.raise_for_status()
        im = Image.open(BytesIO(r.content))
        if getattr(im, "is_animated", False):
            im.seek(0)
        if im.mode in ("RGBA", "LA", "P"):
            im = im.convert("RGBA")
            bg = Image.new("RGB", im.size, (255, 255, 255))
            bg.paste(im, mask=im.split()[-1])
            im = bg
        else:
            im = im.convert("RGB")
        im.thumbnail((max_px, max_px))
        buf = BytesIO()
        im.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()
    except Exception as e:  # noqa: BLE001
        print(f"    ! image fetch failed ({url[:60]}…): {e}")
        return None


def svg_markup(asset: dict) -> str | None:
    if asset.get("inline_svg"):
        return asset["inline_svg"]
    url = asset.get("url", "")
    if url.startswith("data:image/svg"):
        body = url.split(",", 1)[-1]
        return unquote(body)[:4000]
    if ext_of(url) == "svg":
        try:
            return requests.get(url, timeout=20).text[:4000]
        except Exception:  # noqa: BLE001
            return None
    return None


def parse_json_array(text: str) -> list[dict]:
    m = re.search(r"\[.*\]", text, re.DOTALL)
    if not m:
        return []
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return []


def refine_image_batch(provider, batch: list[tuple[int, str]]) -> list[dict]:
    """batch: list of (asset_index, png_b64). Returns model classifications."""
    lines = [
        f"Classify these {len(batch)} brand assets (Image N = list position N).",
        f"Return a JSON array of {len(batch)} objects. {SCHEMA_HINT}",
        "Use index = the Image number (1-based).",
    ]
    imgs = [b64 for _, b64 in batch]
    out = provider.analyze_image(
        image_b64=imgs[0],
        system_prompt=SYSTEM,
        user_prompt="\n".join(lines),
        max_tokens=2048,
        additional_images=[(f"img{i}", b) for i, b in enumerate(imgs[1:], start=2)],
    )
    return parse_json_array(out)


def refine_text_batch(provider, batch: list[tuple[int, str, str]]) -> list[dict]:
    """batch: list of (local_index, name, svg_markup)."""
    blocks = []
    for i, (_, name, markup) in enumerate(batch, start=1):
        blocks.append(f"--- Asset {i} (name: {name}) ---\n{markup}")
    prompt = (
        f"Classify these {len(batch)} inline SVG / vector assets by inspecting their markup.\n"
        f"Return a JSON array of {len(batch)} objects (index = Asset number). {SCHEMA_HINT}\n\n"
        + "\n\n".join(blocks)
    )
    out = provider.text_query(system_prompt=SYSTEM, user_prompt=prompt, max_tokens=2048)
    return parse_json_array(out)


def apply_result(asset: dict, res: dict) -> None:
    asset["heuristic_type"] = asset["asset_type"]
    asset["heuristic_role"] = asset["role"]
    new_type = (res.get("asset_type") or "").strip() or asset["asset_type"]
    new_role = (res.get("role") or "").strip() or asset["role"]
    asset["asset_type"] = new_type
    asset["role"] = new_role
    asset["icon_or_illustration"] = res.get("icon_or_illustration", "na")
    asset["label"] = res.get("label", "")
    asset["vision_note"] = res.get("note", "")
    asset["confidence"] = "vision"
    asset["changed"] = (new_type != asset["heuristic_type"]) or (new_role != asset["heuristic_role"])


def write_report(manifest: dict, out_html: Path) -> None:
    assets = manifest["assets"]
    changed = [a for a in assets if a.get("changed")]
    by_role: dict[str, list[dict]] = {}
    for a in assets:
        by_role.setdefault(a["role"], []).append(a)

    def thumb(a: dict) -> str:
        if a.get("inline_svg"):
            return f'<div class="svgwrap">{a["inline_svg"]}</div>'
        u = a.get("url", "")
        if not u or u.startswith("data:"):
            return '<div class="ph">svg</div>'
        if a["asset_type"] == "video":
            return f'<video class="thumb" src="{u}" muted preload="metadata"></video>'
        return f'<img class="thumb" loading="lazy" src="{u}" alt="">'

    def cell(a: dict) -> str:
        badge = ""
        if a.get("changed"):
            badge = (
                f'<span class="chg">↻ {a.get("heuristic_type")}/{a.get("heuristic_role")} '
                f'→ {a["asset_type"]}/{a["role"]}</span>'
            )
        conf = "vision" if a.get("confidence") == "vision" else "heuristic"
        label = a.get("label") or a["name"][:40]
        return f"""<figure class="cell {('changed' if a.get('changed') else '')}">
          <div class="media">{thumb(a)}</div>
          <figcaption>
            <span class="type type-{a['asset_type']}">{a['asset_type']}</span>
            <span class="lab">{label}</span>
            <span class="conf conf-{conf}">{conf}</span>
            {badge}
          </figcaption>
        </figure>"""

    sections = []
    for role in sorted(by_role, key=lambda k: -len(by_role[k])):
        items = by_role[role]
        sections.append(
            f'<section class="role"><h2>{role} <span class="badge">{len(items)}</span></h2>'
            f'<div class="grid">{"".join(cell(a) for a in items)}</div></section>'
        )

    html = f"""<!doctype html><html><head><meta charset="utf-8">
<title>Brand asset map (vision-refined) — {manifest.get('source','')}</title>
<style>
  *{{box-sizing:border-box}}
  body{{margin:0;font:14px/1.5 -apple-system,Inter,Segoe UI,sans-serif;color:#1c2a21;background:#f6f7f5}}
  header{{padding:28px 32px;border-bottom:1px solid #e2e6e1;background:#fff}}
  h1{{margin:0 0 4px;font-size:20px}} .sub{{color:#5d6b61;font-size:13px}}
  .summary{{margin-top:12px;font-size:13px;color:#3a473e}}
  .summary b{{color:#1f8a5b}}
  main{{padding:24px 32px 60px}}
  .role{{margin-bottom:30px}}
  .role h2{{font-size:13px;text-transform:uppercase;letter-spacing:.08em;color:#3a473e;display:flex;gap:8px;align-items:center}}
  .badge{{background:#1f8a5b;color:#fff;border-radius:999px;padding:1px 8px;font-size:11px}}
  .grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:14px;margin-top:12px}}
  .cell{{margin:0;background:#fff;border:1px solid #e2e6e1;border-radius:12px;overflow:hidden}}
  .cell.changed{{border-color:#e0a000;box-shadow:inset 0 0 0 1px #f0c84a}}
  .media{{height:120px;display:grid;place-items:center;background:#fafbfa;border-bottom:1px solid #eef1ed;padding:10px}}
  .thumb{{max-width:100%;max-height:100px;object-fit:contain}}
  .svgwrap,.svgwrap svg{{max-width:80px;max-height:80px}} .ph{{color:#b7c0b8}}
  figcaption{{padding:10px;display:flex;flex-direction:column;gap:5px}}
  .type{{align-self:flex-start;font-size:11px;font-weight:600;padding:1px 7px;border-radius:6px;background:#eef1ed;color:#3a473e}}
  .type-photo{{background:#e7f0fb;color:#1f5fa8}} .type-video{{background:#fbe9e7;color:#b3402f}}
  .type-logo{{background:#f3ecfb;color:#6b3fa0}} .type-background,.type-texture{{background:#fdf3e0;color:#9a6a14}}
  .type-illustration{{background:#e7faf0;color:#1f8a5b}} .type-animated{{background:#e7faf0;color:#1f8a5b}}
  .lab{{font-size:12px;color:#1c2a21}}
  .conf{{align-self:flex-start;font-size:10px;padding:1px 6px;border-radius:5px}}
  .conf-vision{{background:#e7faf0;color:#1f8a5b}} .conf-heuristic{{background:#eef1ed;color:#7c8a80}}
  .chg{{font-size:10.5px;color:#8a5a00;background:#fff6e0;border:1px solid #f0d68a;border-radius:6px;padding:2px 6px}}
</style></head><body>
<header>
  <h1>Brand asset map — vision-refined</h1>
  <div class="sub">Source: {manifest.get('source','')} · {len(assets)} assets</div>
  <div class="summary"><b>{len(changed)}</b> of {len(assets)} corrected by the vision pass.
  Types now: {json.dumps(_count(assets,'asset_type'))} · Roles: {json.dumps(_count(assets,'role'))}</div>
</header>
<main>{''.join(sections)}</main>
</body></html>"""
    out_html.write_text(html, encoding="utf-8")


def _count(assets, key):
    from collections import Counter

    return dict(Counter(a[key] for a in assets).most_common())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True, type=Path)
    ap.add_argument("--model", default="claude-opus-4-8")
    ap.add_argument("--limit", type=int, default=0, help="max assets to refine (0 = all)")
    ap.add_argument("--batch", type=int, default=6)
    args = ap.parse_args()

    load_env()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY not found in environment / .env.local")

    from screenshot_to_template.models.anthropic import AnthropicProvider

    # Classification doesn't need extended thinking — disable for speed + cost.
    provider = AnthropicProvider(args.model, reasoning_effort="none")

    manifest = json.loads(args.manifest.read_text())
    assets = manifest["assets"]
    if args.limit:
        assets = assets[: args.limit]

    image_jobs: list[tuple[int, str]] = []  # (asset_idx, b64)
    text_jobs: list[tuple[int, str, str]] = []  # (asset_idx, name, markup)

    print(f"Preparing {len(assets)} assets…")
    for idx, a in enumerate(assets):
        url = a.get("url", "")
        if a["kind"] == "inline-svg" or url.startswith("data:image/svg") or ext_of(url) == "svg":
            markup = svg_markup(a)
            if markup:
                text_jobs.append((idx, a["name"], markup))
            continue
        if a["asset_type"] == "video" or ext_of(url) not in RASTER_EXTS:
            continue
        b64 = fetch_png_b64(url)
        if b64:
            image_jobs.append((idx, b64))

    print(f"  image jobs: {len(image_jobs)} · text jobs: {len(text_jobs)}")

    # ── image batches ──
    for start in range(0, len(image_jobs), args.batch):
        batch = image_jobs[start : start + args.batch]
        print(f"  vision batch {start // args.batch + 1} ({len(batch)} imgs)…")
        results = refine_image_batch(provider, batch)
        for res in results:
            try:
                pos = int(res.get("index", 0)) - 1
            except (TypeError, ValueError):
                continue
            if 0 <= pos < len(batch):
                apply_result(assets[batch[pos][0]], res)

    # ── text (svg) batches ──
    for start in range(0, len(text_jobs), args.batch):
        batch = text_jobs[start : start + args.batch]
        print(f"  svg batch {start // args.batch + 1} ({len(batch)})…")
        results = refine_text_batch(provider, batch)
        for res in results:
            try:
                pos = int(res.get("index", 0)) - 1
            except (TypeError, ValueError):
                continue
            if 0 <= pos < len(batch):
                apply_result(assets[batch[pos][0]], res)

    manifest["assets"] = assets
    manifest["by_type"] = _count(assets, "asset_type")
    manifest["by_role"] = _count(assets, "role")
    manifest["refined"] = True

    out_json = args.manifest.with_name("assets-manifest.vision.json")
    out_html = args.manifest.with_name("assets-report.vision.html")
    out_json.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    write_report(manifest, out_html)

    changed = sum(1 for a in assets if a.get("changed"))
    print(f"\nRefined {len(assets)} assets · {changed} corrected by vision")
    print("  by type:", manifest["by_type"])
    print("  by role:", manifest["by_role"])
    print(f"  manifest: {out_json}")
    print(f"  report:   {out_html}")


if __name__ == "__main__":
    main()
