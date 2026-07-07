#!/usr/bin/env python3
"""tokens_drift.py — staleness / drift report for generated token artifacts (SPEC §F).

Standalone (taste_sync.py is contended by a live external worker — SPEC §F.2 names this
exact fallback): computes the CURRENT sha256 of ``runs/<brand>/brand/brand.yaml`` (+ the
per-style md hashes), then scans the known artifact roots for embedded manifests/hash
stamps that mismatch:

  - ``runs/<brand>/brand/kit/agent/tokens.css``       (header comment sha stamp)
  - any dir carrying ``tokens.manifest.json``          (composed pages, galleries)
  - any ``index.html`` embedding ``<style id="tokens">`` (header comment sha stamp)

Output: ``artifact | embedded | current | verdict`` — FRESH / STALE / UNSTAMPED —
printed, and appended to ``runs/<brand>/brand/signals.log`` as one INFO line.
**Exit 0 always** (SPEC §F.3): drift is a to-regenerate list, not a failure;
``taste_sync.py --export-if-changed`` remains the fix-action for the kit, the compose
CLI for pages.

Usage:
  python3 brand_pipeline/tokens_drift.py woodwave
  python3 brand_pipeline/tokens_drift.py runs/woodwave --roots experiments/woodwave-showcase
  python3 brand_pipeline/tokens_drift.py woodwave --no-log   (don't append to signals.log)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

_HDR_SHA_RE = re.compile(r"sha256=([0-9a-f]{6,64})")
_TOKENS_TAG_RE = re.compile(r'<style id="tokens">.*?sha256=([0-9a-f]{6,64})', re.S)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verdict(embedded: str, current: str) -> str:
    if not embedded:
        return "UNSTAMPED"
    # stamps may be truncated (the css header carries 12 hex chars)
    return "FRESH" if current.startswith(embedded) or embedded.startswith(current[:len(embedded)]) \
        else "STALE"


def _style_hashes(styles_dir: Path) -> dict[str, str]:
    return {p.stem: _sha(p) for p in sorted(styles_dir.glob("*.md"))} if styles_dir.is_dir() else {}


def scan_brand(brand_dir: Path, extra_roots: list[Path]) -> list[dict]:
    """Return one row dict per artifact: {artifact, embedded, current, verdict, kind}."""
    brand_yaml = brand_dir / "brand" / "brand.yaml"
    current = _sha(brand_yaml) if brand_yaml.exists() else ""
    style_hashes = _style_hashes(REPO_ROOT / "styles")
    rows: list[dict] = []

    def add(path: Path, embedded: str, kind: str, current_hash: str = None):
        cur = current if current_hash is None else current_hash
        rows.append({"artifact": str(path.relative_to(REPO_ROOT) if path.is_absolute()
                                      and str(path).startswith(str(REPO_ROOT)) else path),
                     "embedded": embedded[:12], "current": cur[:12],
                     "verdict": _verdict(embedded, cur), "kind": kind})

    # 1. kit tokens.css (header stamp; pre-token-layer kits carry no sha → UNSTAMPED)
    kit_css = brand_dir / "brand" / "kit" / "agent" / "tokens.css"
    if kit_css.exists():
        m = _HDR_SHA_RE.search(kit_css.read_text(errors="ignore")[:600])
        add(kit_css, m.group(1) if m else "", "kit-tokens-css")

    # 2+3. render dirs: tokens.manifest.json beside index.html, or an embedded
    # <style id="tokens"> stamp inside the html itself.
    roots = [brand_dir] + list(extra_roots)
    seen: set[Path] = set()
    for root in roots:
        if not root.exists():
            continue
        for mf in sorted(root.rglob("tokens.manifest.json")):
            d = mf.parent.resolve()
            if d in seen:
                continue
            seen.add(d)
            try:
                data = json.loads(mf.read_text())
            except Exception:
                add(mf, "", "manifest-unreadable")
                continue
            add(mf.parent / "index.html", data.get("brand_yaml_sha256", ""), "manifest")
            sid = data.get("style_id") or ""
            emb_style = data.get("style_md_sha256") or ""
            if sid and sid in style_hashes:
                add(mf.parent / f"[style:{sid}]", emb_style, "style-md",
                    current_hash=style_hashes[sid])
        for html in sorted(root.rglob("index.html")):
            d = html.parent.resolve()
            if d in seen:
                continue
            try:
                head = html.read_text(errors="ignore")[:4000]
            except Exception:
                continue
            if "<style" not in head:
                continue
            m = _TOKENS_TAG_RE.search(head)
            if m:
                seen.add(d)
                add(html, m.group(1), "embedded-tokens-block")
            elif "cs-section" in head or 'class="cs-surface"' in head:
                seen.add(d)
                add(html, "", "composed-page")  # composed but pre-token-layer → UNSTAMPED
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description="Token staleness report (non-blocking, exit 0).")
    ap.add_argument("brand", help="brand name under runs/ (e.g. woodwave) or a runs/<brand> path")
    ap.add_argument("--roots", nargs="*", default=[],
                    help="extra artifact roots to scan (e.g. experiments/woodwave-showcase)")
    ap.add_argument("--no-log", action="store_true", help="do not append to signals.log")
    args = ap.parse_args()

    brand_dir = Path(args.brand)
    if not brand_dir.exists():
        brand_dir = REPO_ROOT / "runs" / args.brand
    if not (brand_dir / "brand" / "brand.yaml").exists():
        print(f"tokens_drift: no brand.yaml under {brand_dir}/brand — nothing to check")
        return 0

    rows = scan_brand(brand_dir, [Path(r) if Path(r).is_absolute() else REPO_ROOT / r
                                  for r in args.roots])
    counts = {"FRESH": 0, "STALE": 0, "UNSTAMPED": 0}
    wa = max([len(str(r['artifact'])) for r in rows] + [8])
    print(f"{'artifact'.ljust(wa)} | embedded     | current      | verdict")
    print(f"{'-' * wa} | ------------ | ------------ | -------")
    for r in rows:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
        print(f"{str(r['artifact']).ljust(wa)} | {r['embedded'].ljust(12) or ' ' * 12} | "
              f"{r['current'].ljust(12)} | {r['verdict']}")
    summary = (f"tokens drift: {counts['FRESH']} fresh, {counts['STALE']} stale, "
               f"{counts['UNSTAMPED']} unstamped across {len(rows)} artifact(s)")
    print("\n" + summary)
    if counts["STALE"] or counts["UNSTAMPED"]:
        print("fix-action: regenerate via the compose CLI (pages) / "
              "taste_sync.py --export-if-changed (kit). Drift never gates (exit 0).")

    if not args.no_log:
        log = brand_dir / "brand" / "signals.log"
        stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with log.open("a") as fh:
            fh.write(f"[{stamp}] INFO tokens-drift: {summary}\n")
        print(f"appended INFO line -> {log}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
