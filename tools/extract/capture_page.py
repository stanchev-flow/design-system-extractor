#!/usr/bin/env python3
"""capture_page.py — live capture of a source page into the Save-Page-As shape
the extraction tools consume (<name>.html + <name>_files/ + full-page screenshot).

Loads the URL in Playwright chromium, runs a scroll pass (lazy media +
IntersectionObserver reveals), dismisses a consent banner when one matches the
common patterns, downloads every linked stylesheet and every rendered image's
CHOSEN candidate (currentSrc) into <name>_files/, rewrites the DOM to reference
the local copies (so the JS-off measure stage resolves the real CSS offline),
saves the rendered DOM and a full-page PNG screenshot.

Usage:
    ./venv/bin/python tools/extract/capture_page.py \
        --url https://remote.com --out screenshots/remote-v2 --name remote-com
"""
from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

CONSENT_SELECTORS = (
    "#onetrust-accept-btn-handler",
    "button#truste-consent-button",
    "[data-testid='cookie-banner'] button",
    "button[aria-label*='ccept']",
)


def sanitize(url: str, idx: int, kind: str) -> str:
    name = Path(urlparse(url).path).name or f"{kind}-{idx}"
    name = re.sub(r"[^A-Za-z0-9._-]+", "-", name)[:120]
    if kind == "css" and not name.endswith(".css"):
        name += ".css"
    return f"{idx:03d}-{name}"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--url", required=True)
    ap.add_argument("--out", type=Path, required=True, help="capture dir to create")
    ap.add_argument("--name", default="page", help="basename for html/_files")
    ap.add_argument("--viewport", default="1440x900")
    ap.add_argument("--settle-ms", type=int, default=2500)
    args = ap.parse_args(argv)

    from playwright.sync_api import sync_playwright

    w, h = (int(x) for x in args.viewport.split("x"))
    out = args.out
    files_dir = out / f"{args.name}_files"
    files_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        ctx = browser.new_context(viewport={"width": w, "height": h},
                                  user_agent=UA, device_scale_factor=1)
        page = ctx.new_page()
        page.goto(args.url, wait_until="load", timeout=90000)
        page.wait_for_timeout(args.settle_ms)

        dismissed = False
        for sel in CONSENT_SELECTORS:
            try:
                el = page.locator(sel).first
                if el.is_visible(timeout=800):
                    el.click(timeout=1500)
                    page.wait_for_timeout(600)
                    dismissed = True
                    break
            except Exception:
                continue
        if not dismissed:
            try:
                el = page.get_by_role("button", name=re.compile(r"accept( all)?", re.I)).first
                if el.is_visible(timeout=1200):
                    el.click(timeout=1500)
                    page.wait_for_timeout(600)
            except Exception:
                pass

        # scroll pass: fire lazy loads + reveal animations, then settle at top
        page_h = page.evaluate("document.body.scrollHeight")
        y, step = 0, int(h * 0.75)
        while y < page_h:
            page.evaluate(f"window.scrollTo(0, {y})")
            page.wait_for_timeout(250)
            y += step
            page_h = page.evaluate("document.body.scrollHeight")
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(1000)
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(1200)

        # full-page screenshot FIRST — the DOM rewrite below points hrefs at
        # local paths that do not exist on the live origin (styles would drop).
        page.screenshot(path=str(out / f"{args.name}-fullpage.png"), full_page=True)
        dims = page.evaluate(
            "({w: document.documentElement.scrollWidth,"
            "  h: document.documentElement.scrollHeight})")

        sheets = page.evaluate(
            "[...document.querySelectorAll(\"link[rel~='stylesheet'][href]\")]"
            ".map(l => l.href)")
        images = page.evaluate(
            "[...document.images].map(i => i.currentSrc || i.src).filter(Boolean)")

        url_map: dict[str, str] = {}
        n_css = n_img = 0
        for i, u in enumerate(dict.fromkeys(sheets)):
            if not u.startswith("http"):
                continue
            try:
                r = ctx.request.get(u, timeout=30000)
                if r.ok:
                    fname = sanitize(u, i, "css")
                    (files_dir / fname).write_text(r.text())
                    url_map[u] = f"{files_dir.name}/{fname}"
                    n_css += 1
            except Exception as exc:
                print(f"  ! css fetch failed: {u[:90]} ({exc})", file=sys.stderr)
        for i, u in enumerate(dict.fromkeys(images)):
            if not u.startswith("http"):
                continue
            try:
                r = ctx.request.get(u, timeout=30000)
                if r.ok:
                    fname = sanitize(u, i, "img")
                    (files_dir / fname).write_bytes(r.body())
                    url_map[u] = f"{files_dir.name}/{fname}"
                    n_img += 1
            except Exception as exc:
                print(f"  ! img fetch failed: {u[:90]} ({exc})", file=sys.stderr)

        # rewrite the live DOM to the local copies, then serialize it
        page.evaluate(
            """(map) => {
                 for (const l of document.querySelectorAll("link[rel~='stylesheet'][href]")) {
                   const local = map[l.href];
                   if (local) { l.setAttribute('href', local);
                                l.removeAttribute('integrity');
                                l.removeAttribute('crossorigin'); }
                 }
                 for (const img of document.images) {
                   const key = img.currentSrc || img.src;
                   const local = map[key];
                   if (local) { img.setAttribute('src', local);
                                img.removeAttribute('srcset');
                                img.removeAttribute('sizes'); }
                 }
                 for (const s of document.querySelectorAll('picture > source')) s.remove();
               }""", url_map)
        html_text = page.evaluate("'<!DOCTYPE html>' + document.documentElement.outerHTML")
        (out / f"{args.name}.html").write_text(html_text)
        browser.close()

    print(f"capture: {out}")
    print(f"  html:       {args.name}.html ({len(html_text)} chars)")
    print(f"  css saved:  {n_css}")
    print(f"  imgs saved: {n_img}")
    print(f"  screenshot: {args.name}-fullpage.png (page {dims['w']}x{dims['h']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
