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
    harvest_banner_from_fragment,
    measure_bar_affordances,
    merge_bar_affordances,
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
    parser.add_argument(
        "--mega-shots-dir",
        default=None,
        help="Optional: run the OPEN-STATE mega-panel pass (hover/click each "
        "aria-controls panel, measure rendered geometry into nav.megaOpen) and "
        "write per-panel screenshots into this directory.",
    )
    parser.add_argument(
        "--live-affordances",
        default=None,
        metavar="URL",
        help="Optional: run the LIVE bar-affordance pass against this URL (utility "
        "banner anatomy + in-bar utility dropdown open states — states a saved "
        "snapshot cannot show) and merge the facts into the contract.",
    )
    parser.add_argument(
        "--affordance-shots-dir",
        default=None,
        help="Where the live-affordance pass writes its state screenshots "
        "(default: alongside --mega-shots-dir, else no shots).",
    )
    parser.add_argument(
        "--banner-fragment",
        default=None,
        help="Optional: saved banner-embed fragment .html (hosted promo banners "
        "render as their own captured document). Its measured anatomy (message / "
        "cta / close) fills nav.banner when the live page shows no banner.",
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
        html_path, base_url=args.base_url, timeout_ms=args.timeout,
        mega_shots_dir=Path(args.mega_shots_dir) if args.mega_shots_dir else None,
    )
    if args.live_affordances:
        shots = args.affordance_shots_dir or args.mega_shots_dir
        affordances = measure_bar_affordances(
            args.live_affordances,
            shots_dir=Path(shots) if shots else None,
            timeout_ms=args.timeout,
        )
        merge_bar_affordances(contract, affordances)
    if args.banner_fragment and not (contract.get("nav") or {}).get("banner"):
        banner = harvest_banner_from_fragment(args.banner_fragment)
        if banner and isinstance(contract.get("nav"), dict):
            contract["nav"]["banner"] = banner
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
            aside_n = sum(1 for c in (m.get("columns") or []) if c.get("area") == "aside")
            desc_n = sum(1 for c in (m.get("columns") or [])
                         for l in (c.get("links") or []) if l.get("description"))
            icon_n = sum(1 for c in (m.get("columns") or [])
                         for l in (c.get("links") or []) if l.get("icon"))
            print(f"    menu · {p.get('label')}: {len(m.get('columns') or [])} columns "
                  f"({aside_n} aside), "
                  f"{sum(len(c.get('links') or []) for c in (m.get('columns') or []))} links "
                  f"({desc_n} w/desc, {icon_n} w/icon), "
                  f"{len(m.get('featured') or [])} featured, "
                  f"card={'yes' if m.get('card') else 'no'}")
    mega_open = [m for m in (nav.get("megaOpen") or []) if m.get("open")]
    if mega_open:
        print(f"  mega OPEN-state measured: {len(mega_open)} panel(s)")
        for m in mega_open:
            pr = m.get("panel") or {}
            print(f"    open · {m.get('label')}: {pr.get('w')}x{pr.get('h')} "
                  f"groups={len(m.get('groups') or [])} "
                  f"aside={'yes' if m.get('aside') else 'no'} "
                  f"card={'yes' if m.get('card') else 'no'} shot={m.get('shot') or '-'}")
    bb = footer.get("bottomBar") or {}
    if bb:
        print(f"  footer bottomBar: divider={'yes' if (bb.get('divider') or {}).get('present') else 'no'}, "
              f"rows={len(bb.get('rows') or [])}, policy={len(bb.get('policyLinks') or [])}, "
              f"badges={len(bb.get('storeBadges') or [])}, "
              f"disclaimer={'yes' if bb.get('disclaimer') else 'no'}")
    icon_soc = sum(1 for s in (footer.get("social") or []) if s.get("icon"))
    if footer.get("social"):
        print(f"  social icon sources captured: {icon_soc}/{len(footer.get('social') or [])}")

    if args.reference_out:
        snapshot_chrome_reference_from_saved_page(html_path, args.reference_out, timeout_ms=args.timeout)


if __name__ == "__main__":
    main()
