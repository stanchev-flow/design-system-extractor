#!/usr/bin/env python3
"""mine_css.py — brand-agnostic CSS mining of a saved-page capture.

Generalized from the (frozen) experiments/remote-e2e/css_mine.py. Keeps that
harness's @media/:hover-aware rule parser (the HubSpot-extraction B12 lesson:
hover rules nested inside @media are missed by top-level scans) but DISCOVERS
stylesheets — every ``*.css`` under the capture's ``*_files`` dir plus inline
``<style>`` blocks in the saved HTML — instead of a hardcoded per-brand list.

Emits two documents:
  css-rules.json  raw (file, media, selector, decls) rows — the measurement corpus
  css-facts.json  derived censuses: hover pairs, radius/font/transition/color/
                  letter-spacing/text-transform counts, @media breakpoints —
                  chrome-presentation and motion evidence the grounding stage
                  cross-checks.

Read-only over the capture; writes only into --out-dir.

Usage:
    ./venv/bin/python tools/extract/mine_css.py --capture screenshots/<brand>/ \
        --out-dir runs/<brand>/brand/evidence/
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

SCHEMA = "css-mine.v1"


# ── capture discovery (self-contained by design) ────────────────────────────────

def find_saved_html(capture: Path) -> Path | None:
    pages = sorted(capture.glob("*.htm*"), key=lambda p: p.stat().st_size, reverse=True)
    return pages[0] if pages else None


def find_files_dir(capture: Path, html_path: Path | None) -> Path | None:
    if html_path is not None:
        cand = html_path.with_name(html_path.stem + "_files")
        if cand.is_dir():
            return cand
    dirs = [d for d in capture.iterdir() if d.is_dir() and d.name.endswith("_files")]
    return dirs[0] if dirs else None


# ── parser (kept from the remote-e2e harness — proven on minified captures) ─────

def strip_comments(css: str) -> str:
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def parse_rules(css: str, fname: str) -> list[dict]:
    """Tokenize a stylesheet into (media, selector, decls) rows. Handles one level
    of @media/@supports nesting; records @keyframes as their own rows (motion is
    summarized separately); skips nothing silently."""
    rows: list[dict] = []
    i, n = 0, len(css)
    media_stack: list[str] = []
    buf = ""
    while i < n:
        ch = css[i]
        if ch == "{":
            sel = buf.strip()
            buf = ""
            if sel.startswith("@media") or sel.startswith("@supports"):
                media_stack.append(sel)
                i += 1
                continue
            if sel.startswith("@keyframes") or sel.startswith("@-webkit-keyframes"):
                depth = 1
                j = i + 1
                while j < n and depth:
                    if css[j] == "{":
                        depth += 1
                    elif css[j] == "}":
                        depth -= 1
                    j += 1
                rows.append({"file": fname, "media": " && ".join(media_stack),
                             "selector": sel, "decls": css[i + 1:j - 1][:400],
                             "kind": "keyframes"})
                i = j
                continue
            j = css.find("}", i + 1)
            if j == -1:
                break
            decls = css[i + 1:j].strip()
            rows.append({"file": fname, "media": " && ".join(media_stack),
                         "selector": sel, "decls": decls, "kind": "rule"})
            i = j + 1
            continue
        if ch == "}":
            if media_stack:
                media_stack.pop()
            buf = ""
            i += 1
            continue
        buf += ch
        i += 1
    return rows


# ── derived facts ────────────────────────────────────────────────────────────────

_DECL_RE = re.compile(r"([a-z-]+)\s*:\s*([^;]+)", re.I)
_COLOR_RE = re.compile(r"#[0-9a-fA-F]{3,8}\b|rgba?\([^)]*\)")


def derive_facts(rows: list[dict]) -> dict:
    hover_rules = []
    radius, fonts, transitions, colors = Counter(), Counter(), Counter(), Counter()
    tracking, transform, weights = Counter(), Counter(), Counter()
    breakpoints: Counter = Counter()
    for r in rows:
        if r["kind"] != "rule":
            continue
        if r["media"]:
            breakpoints[r["media"][:80]] += 1
        decls = dict()
        for prop, val in _DECL_RE.findall(r["decls"]):
            decls[prop.lower()] = val.strip()
        if ":hover" in r["selector"] and any(
                p in decls for p in ("color", "background", "background-color",
                                     "border-color", "text-decoration", "box-shadow",
                                     "opacity", "transform")):
            hover_rules.append({"file": r["file"], "media": r["media"],
                                "selector": r["selector"][:160],
                                "decls": r["decls"][:300]})
        for prop, counter in (("border-radius", radius), ("font-family", fonts),
                              ("transition", transitions),
                              ("letter-spacing", tracking),
                              ("text-transform", transform),
                              ("font-weight", weights)):
            if prop in decls:
                counter[decls[prop][:80]] += 1
        for m in _COLOR_RE.findall(r["decls"]):
            colors[m.lower()[:40]] += 1
    return {
        "hoverRules": hover_rules[:400],
        "radiusCensus": dict(radius.most_common(30)),
        "fontFamilyCensus": dict(fonts.most_common(20)),
        "fontWeightCensus": dict(weights.most_common(15)),
        "transitionCensus": dict(transitions.most_common(30)),
        "letterSpacingCensus": dict(tracking.most_common(20)),
        "textTransformCensus": dict(transform.most_common(10)),
        "colorCensus": dict(colors.most_common(60)),
        "mediaBreakpoints": dict(breakpoints.most_common(30)),
    }


_STYLE_TAG_RE = re.compile(r"<style[^>]*>(.*?)</style>", re.S | re.I)


def collect_sources(files_dir: Path | None, html_path: Path | None) -> list[tuple[str, str]]:
    """(name, css-text) pairs: every *.css under files_dir (recursive, sorted)
    plus inline <style> blocks from the saved page."""
    out: list[tuple[str, str]] = []
    if files_dir is not None and files_dir.is_dir():
        for p in sorted(files_dir.rglob("*.css")):
            out.append((p.name, p.read_text(errors="replace")))
    if html_path is not None and html_path.is_file():
        html = html_path.read_text(errors="replace")
        for k, block in enumerate(_STYLE_TAG_RE.findall(html)):
            if block.strip():
                out.append((f"<inline-style-{k:02d}>", block))
    return out


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--capture", type=Path, help="capture dir (auto-discovers html + _files)")
    ap.add_argument("--html", type=Path, help="explicit saved-page .html")
    ap.add_argument("--files-dir", type=Path, help="explicit *_files assets dir")
    ap.add_argument("--out-dir", type=Path, required=True,
                    help="dir for css-rules.json + css-facts.json")
    return ap


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    html_path = args.html
    files_dir = args.files_dir
    if args.capture:
        html_path = html_path or find_saved_html(args.capture)
        files_dir = files_dir or find_files_dir(args.capture, html_path)
    if files_dir is None and html_path is None:
        raise SystemExit("provide --capture, or --files-dir / --html explicitly")

    sources = collect_sources(files_dir, html_path)
    if not sources:
        raise SystemExit(f"no stylesheets found (files-dir={files_dir}, html={html_path})")

    all_rows: list[dict] = []
    for name, css in sources:
        rows = parse_rules(strip_comments(css), name)
        all_rows.extend(rows)
        print(f"  {name}: {len(rows)} rules")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    rules_path = args.out_dir / "css-rules.json"
    facts_path = args.out_dir / "css-facts.json"
    rules_path.write_text(json.dumps(
        {"schemaVersion": SCHEMA, "sources": [n for n, _ in sources],
         "rules": all_rows}, indent=1))
    facts = derive_facts(all_rows)
    facts_path.write_text(json.dumps(
        {"schemaVersion": SCHEMA, **facts}, indent=1))
    print(f"[done] css-mine: {len(all_rows)} rules from {len(sources)} sheets -> "
          f"{rules_path.name}; {len(facts['hoverRules'])} hover rules -> {facts_path.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
