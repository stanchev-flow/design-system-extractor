#!/usr/bin/env python3
"""Turn the vision-refined asset manifest into a lean, role-grouped JSON that a
generated page can consume directly — now with real pixel dimensions so the
page can rank assets by how well they fit each slot.

This is the bridge for extraction Tier-1: the page generator no longer invents
placeholder art — it asks the resolver for "the logo wall" or "a hero media" and
gets the brand's own assets back, mapped by role and sized for the slot.

Usage:
    python tools/build_brand_assets.py \\
        --manifest screenshots/hackathon-test/source/assets/assets-manifest.vision.json \\
        --out handoff/v302-fieldnote/src/brand/brand-assets.json
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path

import requests
from PIL import Image


def pick_display_url(asset: dict) -> str:
    """Prefer a mid-size responsive variant (≈400–1000w) for display weight."""
    best = None
    for v in asset.get("variants") or []:
        m = re.search(r"-p-(\d+)\.", v)
        if m:
            w = int(m.group(1))
            if 400 <= w <= 1000 and (best is None or w > best[0]):
                best = (w, v)
    return best[1] if best else asset.get("url", "")


def probe_dims(url: str) -> tuple[int, int] | None:
    if not url or url.startswith("data:"):
        return None
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        with Image.open(BytesIO(r.content)) as im:
            return im.size  # (w, h)
    except Exception:  # noqa: BLE001
        return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--no-probe", action="store_true", help="skip pixel-dimension probing")
    args = ap.parse_args()

    manifest = json.loads(args.manifest.read_text())

    entries: list[dict] = []
    for i, a in enumerate(manifest["assets"]):
        url = a.get("url", "")
        inline = a.get("inline_svg")
        if not url and not inline:
            continue
        if url.startswith("data:") and not inline:
            continue
        clean_url = url if (url and not url.startswith("data:")) else ""
        entries.append(
            {
                "id": f"a{i}",
                "type": a.get("asset_type", "other"),
                "role": a.get("role", "content"),
                "label": a.get("label") or a.get("name", "")[:48],
                "alt": a.get("alt") or a.get("label") or "",
                "url": clean_url,
                "displayUrl": pick_display_url(a) if clean_url else "",
                "inlineSvg": inline if (inline and not clean_url) else "",
                "iconOrIllustration": a.get("icon_or_illustration", "na"),
                "width": None,
                "height": None,
                "aspect": None,
            }
        )

    # Probe real pixel dimensions in parallel (the signal slot-ranking needs).
    if not args.no_probe:
        targets = [e for e in entries if e["url"]]
        print(f"Probing pixel dimensions for {len(targets)} assets…")

        def fill(e: dict) -> None:
            dims = probe_dims(e["displayUrl"] or e["url"])
            if dims:
                w, h = dims
                e["width"], e["height"] = w, h
                e["aspect"] = round(w / h, 3) if h else None

        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(fill, targets))
        probed = sum(1 for e in targets if e["width"])
        print(f"  got dimensions for {probed}/{len(targets)}")

    by_role: dict[str, list[dict]] = defaultdict(list)
    for e in entries:
        by_role[e["role"]].append(e)

    out_data = {
        "source": manifest.get("source", ""),
        "byRole": by_role,
        "counts": {role: len(items) for role, items in sorted(by_role.items())},
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out_data, indent=2), encoding="utf-8")
    total = sum(len(v) for v in by_role.values())
    print(f"Wrote {total} renderable assets across {len(by_role)} roles → {args.out}")
    print("  counts:", out_data["counts"])


if __name__ == "__main__":
    main()
