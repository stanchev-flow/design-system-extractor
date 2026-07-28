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


def default_assets_prefix(brand_dir: Path) -> str:
    """The URL the studio server already exposes this brand's assets/ under.

    Generated apps are served from inside the same runs/ tree, so a bare
    "/assets" prefix 404s everywhere except a dev server rooted at the brand
    dir; the repo-relative path is what actually resolves.
    """
    repo_root = Path(__file__).resolve().parent.parent
    try:
        rel = brand_dir.resolve().relative_to(repo_root)
    except ValueError:
        return "/assets"
    return "/" + str(rel).strip("/") + "/assets"


def from_brand_registry(brand_dir: Path, assets_prefix: str) -> dict:
    """Emit the bundle from a brand extraction's MEASURED media registry.

    The remote-manifest lane below can only describe an asset ("a logo, roughly
    square"), so its consumers have to rank candidates and hope. A brand
    extraction knows strictly more: bind_media_assets.py has already recorded
    which file rendered in which section, in what role, at what size. Carrying
    that through means a generated page can ask for "the assets in this band"
    and get exactly the ones the source used, in the source's visual order.
    """
    import yaml

    registry = yaml.safe_load((brand_dir / "media-assets.yaml").read_text()) or {}
    entries: list[dict] = []
    by_section: dict[str, list[str]] = defaultdict(list)
    by_role: dict[str, list[dict]] = defaultdict(list)
    for i, a in enumerate(registry.get("assets") or []):
        if not isinstance(a, dict):
            continue
        fname = str(a.get("file") or "")
        if not fname:
            continue
        facts = a.get("facts") if isinstance(a.get("facts"), dict) else {}
        intrinsic = facts.get("intrinsic") if isinstance(facts.get("intrinsic"), dict) else {}
        sem = a.get("assetSemantics") if isinstance(a.get("assetSemantics"), dict) else {}
        placements = [p for p in (a.get("placements") or []) if isinstance(p, dict)]
        aid = str(a.get("id") or f"a{i}")
        url = f"{assets_prefix.rstrip('/')}/{fname}"
        entry = {
            "id": aid,
            "file": fname,
            "type": str(sem.get("kind") or "other"),
            "role": (placements[0].get("role") if placements else "unplaced"),
            "label": str(sem.get("subject") or "")[:80],
            "alt": (facts.get("altHarvested")
                    or next((p.get("alt") for p in placements if p.get("alt")), "")
                    or ""),
            "url": url,
            "displayUrl": url,
            "inlineSvg": "",
            "iconOrIllustration": "na",
            "width": intrinsic.get("w"),
            "height": intrinsic.get("h"),
            "aspect": facts.get("intrinsicAspect"),
            "usageRights": a.get("usageRights"),
            "reusePolicy": a.get("reusePolicy"),
            "compositionRoles": a.get("compositionRoles") or [],
            "placements": [{"page": p.get("page"), "section": p.get("section"),
                            "zone": p.get("zone"), "role": p.get("role"),
                            "visible": p.get("visible")} for p in placements],
        }
        entries.append(entry)
        for p in placements:
            role = str(p.get("role") or "")
            if role and entry not in by_role[role]:
                by_role[role].append(entry)
            section = p.get("section")
            if section and aid not in by_section[str(section)]:
                by_section[str(section)].append(aid)
    # The brand's own WORDMARK is chrome the composer copies in separately, so it
    # is often absent from the curated media registry. Without the brand name the
    # only fallback a consumer has is the scaffold's literal "Brand" placeholder.
    brand_doc = yaml.safe_load((brand_dir / "brand.yaml").read_text()) or {}
    brand_block = brand_doc.get("brand") if isinstance(brand_doc.get("brand"), dict) else {}
    nav_logo = brand_dir / "assets" / "nav-logo.svg"
    return {
        "source": str(brand_dir),
        "note": ("Measured brand asset bundle: bySection is the authoritative "
                 "binding (what the source band actually used, in visual "
                 "order); byRole is for reuse in NEW compositions."),
        "brand": {
            "name": str(brand_block.get("name") or ""),
            "wordmarkUrl": (f"{assets_prefix.rstrip('/')}/{nav_logo.name}"
                            if nav_logo.is_file() else ""),
        },
        "assets": entries,
        "bySection": dict(by_section),
        "byRole": {k: v for k, v in sorted(by_role.items())},
        "counts": {role: len(items) for role, items in sorted(by_role.items())},
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", type=Path)
    ap.add_argument("--brand-dir", type=Path,
                    help="runs/<brand>/brand — emit from the MEASURED media "
                         "registry (media-assets.yaml + placements) instead")
    ap.add_argument("--assets-prefix",
                    help="--brand-dir: URL prefix the app serves assets/ under "
                         "(default: the brand dir's repo-relative path, which is "
                         "how the studio server exposes runs/**)")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--no-probe", action="store_true", help="skip pixel-dimension probing")
    args = ap.parse_args()

    if args.brand_dir:
        prefix = args.assets_prefix or default_assets_prefix(args.brand_dir)
        out_data = from_brand_registry(args.brand_dir, prefix)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(out_data, indent=2), encoding="utf-8")
        print(f"Wrote {len(out_data['assets'])} assets, "
              f"{len(out_data['bySection'])} bound sections → {args.out}")
        print("  roles:", out_data["counts"])
        return
    if not args.manifest:
        raise SystemExit("pass --manifest (remote lane) or --brand-dir (extraction lane)")

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
