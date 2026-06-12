#!/usr/bin/env python3
"""Separate, browser-based nav/footer extraction run.

Launches headless Chromium against a live URL and writes a rich
`source-chrome.v2.json` (computed styles, visible top-level nav, real button
styling, logo, footer columns) for framework generation to consume.

Usage:
    ./venv/bin/python tools/extract_chrome_browser.py \
        --url https://www.greenhouse.com/ \
        --out runs/greenhouse/assets/source-chrome.v2.json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR / "src"))

from screenshot_to_template.browser_chrome_extractor import (  # noqa: E402
    extract_chrome_with_browser,
    write_chrome_contract_v2,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Browser-based nav/footer extraction")
    parser.add_argument("--url", required=True, help="Live URL to extract chrome from")
    parser.add_argument("--out", required=True, help="Output JSON path (source-chrome.v2.json)")
    parser.add_argument("--timeout", type=int, default=30000, help="Navigation timeout (ms)")
    args = parser.parse_args()

    contract = extract_chrome_with_browser(args.url, timeout_ms=args.timeout)
    out = write_chrome_contract_v2(Path(args.out), contract)
    nav = contract.get("nav") or {}
    footer = contract.get("footer") or {}
    print(f"Wrote {out}")
    print(f"  nav: {len(nav.get('links') or [])} links, {len(nav.get('ctas') or [])} CTAs, logo={'yes' if nav.get('logo') else 'no'}")
    print(f"  footer: {len(footer.get('columns') or [])} columns")
    for ln in (nav.get("links") or []):
        print(f"    nav · {ln['label']}")
    for cta in (nav.get("ctas") or []):
        print(f"    cta · {cta['label']} (icon={cta['hasIcon']}, filled={cta['filled']})")


if __name__ == "__main__":
    main()
