#!/usr/bin/env python3
"""Extract nav/footer chrome contract from a saved HTML snapshot."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR / "src"))

from screenshot_to_template.chrome_extractor import (  # noqa: E402
    extract_chrome_from_html,
    write_chrome_contract,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract source nav/footer chrome contract")
    parser.add_argument("--html", required=True, help="Path to HTML snapshot")
    parser.add_argument("--base-url", required=True, help="Site origin for resolving relative hrefs")
    parser.add_argument("--out", required=True, help="Output JSON path (source-chrome.json)")
    args = parser.parse_args()

    html = Path(args.html).read_text(encoding="utf-8", errors="ignore")
    contract = extract_chrome_from_html(html, args.base_url, source_url=args.base_url)
    out = write_chrome_contract(Path(args.out), contract)
    nav_links = len((contract.get("nav") or {}).get("links") or [])
    footer_cols = len((contract.get("footer") or {}).get("columns") or [])
    print(f"Wrote {out} (nav links={nav_links}, footer columns={footer_cols})")


if __name__ == "__main__":
    main()
