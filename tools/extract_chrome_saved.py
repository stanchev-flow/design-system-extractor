#!/usr/bin/env python3
"""Browser-based nav/footer extraction from a SAVED page (offline).

Runs the high-fidelity Playwright v2 extractor against a locally saved
"Save Page As, Complete" capture (an .html + a sibling `*_files/` asset dir) by
serving the folder over a short-lived localhost static server. Computed styles,
visibility filtering, and the div.footer-* fallback all work without network.

Usage (explicit file):
    ./venv/bin/python tools/extract_chrome_saved.py \
        --html "screenshots/hubspot/HubSpot/HubSpot ... Homepage.html" \
        --base-url https://www.hubspot.com \
        --out runs/hubspot/assets/source-chrome.v2.json

Usage (auto-detect a brand's saved page):
    ./venv/bin/python tools/extract_chrome_saved.py \
        --brand hubspot --base-url https://www.hubspot.com \
        --out runs/hubspot/assets/source-chrome.v2.json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR / "src"))

from screenshot_to_template.browser_chrome_extractor import (  # noqa: E402
    extract_chrome_from_saved_page,
    find_saved_page_for_brand,
    snapshot_chrome_reference_from_saved_page,
    write_chrome_contract_v2,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Saved-page nav/footer extraction (v2, offline)")
    parser.add_argument("--html", help="Path to saved .html (Save Page As, Complete)")
    parser.add_argument("--brand", help="Brand name to auto-detect a saved page for")
    parser.add_argument("--base-url", default=None, help="Real site origin for resolving relative hrefs")
    parser.add_argument("--out", required=True, help="Output JSON path (source-chrome.v2.json)")
    parser.add_argument(
        "--reference-out",
        default=None,
        help="Optional: also write a 1:1 nav/footer reference HTML (inlined computed "
        "styles). REFERENCE ONLY — never influences the JSON contract or brand.yaml.",
    )
    parser.add_argument("--timeout", type=int, default=30000, help="Navigation timeout (ms)")
    args = parser.parse_args()

    html_path: Path | None = Path(args.html) if args.html else None
    if html_path is None and args.brand:
        html_path = find_saved_page_for_brand(args.brand, project_dir=PROJECT_DIR)
        if html_path:
            print(f"[auto] detected saved page for '{args.brand}': {html_path}")
    if html_path is None:
        parser.error("provide --html or a --brand with a detectable saved page")

    contract = extract_chrome_from_saved_page(
        html_path, base_url=args.base_url, timeout_ms=args.timeout
    )
    out = write_chrome_contract_v2(Path(args.out), contract)
    nav = contract.get("nav") or {}
    footer = contract.get("footer") or {}
    legal = footer.get("legal") or {}
    print(f"Wrote {out}")
    print(f"  source: {contract.get('source_url')}")
    print(f"  nav: {len(nav.get('links') or [])} links, {len(nav.get('ctas') or [])} CTAs, logo={'yes' if nav.get('logo') else 'no'}")
    print(f"  footer: {len(footer.get('columns') or [])} columns, {len(footer.get('social') or [])} social, "
          f"{len(legal.get('links') or [])} legal links, newsletter={'yes' if footer.get('newsletter') else 'no'}")
    for ln in (nav.get("links") or []):
        print(f"    nav  · {ln['label']} → {ln.get('href')}")
    for cta in (nav.get("ctas") or []):
        print(f"    cta  · {cta['label']} → {cta.get('href')} (icon={cta.get('hasIcon')}, filled={cta.get('filled')})")
    for col in (footer.get("columns") or []):
        print(f"    col  · {col.get('heading') or '(links)'}: {len(col.get('links') or [])} links")
    for s in (footer.get("social") or []):
        print(f"    soc  · {s.get('network')} → {s.get('href')}")
    if legal.get("text"):
        print(f"    legal· {legal['text']}")
    if footer.get("newsletter"):
        nl = footer["newsletter"]
        print(f"    news · placeholder={nl.get('placeholder')!r} submit={nl.get('submitLabel')!r} action={nl.get('action')}")
    menus = sum(1 for p in (nav.get("primary") or []) if isinstance(p, dict) and p.get("menu"))
    print(f"  primary mega-menus: {menus}; nav.measured={'yes' if nav.get('measured') else 'no'}, "
          f"footer.measured={'yes' if footer.get('measured') else 'no'}")
    for p in (nav.get("primary") or []):
        if isinstance(p, dict) and p.get("menu"):
            m = p["menu"]
            print(f"    menu · {p.get('label')}: {len(m.get('columns') or [])} columns, "
                  f"{sum(len(c.get('links') or []) for c in (m.get('columns') or []))} links, "
                  f"{len(m.get('featured') or [])} featured")

    if args.reference_out:
        snapshot_chrome_reference_from_saved_page(html_path, args.reference_out, timeout_ms=args.timeout)


if __name__ == "__main__":
    main()
