#!/usr/bin/env python3
"""Apply role-mapped brand assets into generated v301 pipeline HTML (CLI).

Thin wrapper over `screenshot_to_template.brand_assets`, which is also folded
into `run_pipeline.py` as a post-generation step. Use this CLI to (re)apply
assets to an already-generated page out of band.

Usage:
    python tools/apply_assets_to_html.py \\
        --html runs/v301-mine/hatch-home/single/site-claude.html \\
        --assets handoff/v302-fieldnote/src/brand/brand-assets.json \\
        --out  runs/v301-mine/hatch-home/single/site-claude.assets-applied.html
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from screenshot_to_template.brand_assets import apply_brand_assets_file  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", required=True, type=Path)
    ap.add_argument("--assets", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()

    payload = apply_brand_assets_file(args.html, args.assets, out_path=args.out)
    print(f"Filled {payload['filled']} asset-brief slots → {payload['output']}")
    for slot in payload["slots"]:
        print(
            f"  slot {slot['slot']} ({slot['carrier']}/{slot['role']}) → "
            f"{slot['label'][:40]} [{slot['type']}]"
        )


if __name__ == "__main__":
    main()
