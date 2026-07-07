#!/usr/bin/env python3
"""mine_dom.py — brand-agnostic DOM census of a saved-page capture.

Generalized from the (frozen) experiments/remote-e2e/html_mine.py: same analysis
axes — section order + module classes, surface-scheme class census, eyebrow
candidates, nav + footer structure, button class families, inline-style color
census — but discovered from ANY Save-Page-As capture instead of a hardcoded
brand path, and emitted as ONE structured JSON document (`dom-mine.v1`) that the
grounding and validation stages consume.

Read-only over the capture. Writes only the --out file.

Usage:
    ./venv/bin/python tools/extract/mine_dom.py --capture screenshots/<brand>/ \
        --out runs/<brand>/brand/evidence/dom-sections.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

from bs4 import BeautifulSoup

SCHEMA = "dom-mine.v1"

# class-name hints that mark a page-level module/section wrapper
SECTION_RE = re.compile(
    r"module|section|hero|banner|footer|header|grid|accordion|panel|testimonial"
    r"|proof|logo|badge|partner|cta|pricing|faq|feature|carousel|swiper-container"
    r"|marquee|stats?\b", re.I)
BUTTONISH_RE = re.compile(r"button|btn\b|btn-|cta", re.I)
EYEBROWISH_RE = re.compile(r"label|lebel|eyebrow|kicker|overline|tagline|caption-top", re.I)
SOCIAL_RE = re.compile(r"linkedin|twitter|youtube|instagram|facebook|tiktok|x\.com", re.I)
LEGAL_RE = re.compile(r"©|&copy;|copyright", re.I)


# ── capture discovery (self-contained by design: tools stay independently runnable) ──

def find_saved_html(capture: Path) -> Path:
    pages = sorted(capture.glob("*.htm*"), key=lambda p: p.stat().st_size, reverse=True)
    if not pages:
        raise SystemExit(f"no saved .html page found in {capture}")
    return pages[0]


def _class_sig(el) -> str:
    return " ".join(el.get("class", []) or [])


def _first_heading(el) -> str:
    h = el.find(["h1", "h2", "h3", "h4", "h5", "h6"])
    return h.get_text(" ", strip=True)[:140] if h else ""


def _text_sample(el, n: int = 200) -> str:
    return re.sub(r"\s+", " ", el.get_text(" ", strip=True))[:n]


def mine(html_path: Path) -> dict:
    soup = BeautifulSoup(html_path.read_text(errors="replace"), "html.parser")
    body = soup.body or soup

    # 1. top-level structural children (page skeleton, document order)
    top_level = []
    for el in body.find_all(["header", "main", "footer", "section", "div", "nav"],
                            recursive=False):
        top_level.append({"tag": el.name, "classes": _class_sig(el)[:140],
                          "id": (el.get("id") or "")[:60]})

    # 2. module sections: descendants whose class matches the section hints,
    #    deduped by class signature (first occurrence wins document order).
    main = soup.find("main") or body
    sections, seen = [], set()
    for el in main.find_all(["section", "div"]):
        sig = _class_sig(el)
        if not sig or not SECTION_RE.search(sig):
            continue
        key = sig[:130]
        if key in seen:
            continue
        # skip wrappers that are just a child of an already-recorded section with
        # the identical heading (reduces nested-wrapper noise)
        seen.add(key)
        sections.append({
            "index": len(sections), "tag": el.name, "classes": key,
            "id": (el.get("id") or "")[:60],
            "heading": _first_heading(el),
            "textSample": _text_sample(el),
        })

    # 3. surface-scheme class census (e.g. `*-mode`, `color-scheme-*`, `theme-*`)
    mode_census: Counter = Counter()
    for el in soup.find_all(class_=re.compile(r"-mode\b|color-scheme|scheme-|theme-")):
        for c in el.get("class", []) or []:
            if re.search(r"-mode$|^color-scheme|^scheme-|^theme-", c):
                mode_census[c] += 1

    # 4. button class families (variant-matrix evidence)
    groups: dict[str, dict] = {}
    for el in soup.find_all(["a", "button"]):
        sig = _class_sig(el)
        if el.name != "button" and not BUTTONISH_RE.search(sig):
            continue
        key = f"{el.name}.{sig}"[:150]
        g = groups.setdefault(key, {"tag": el.name, "classes": sig[:140],
                                    "count": 0, "samples": []})
        g["count"] += 1
        txt = el.get_text(" ", strip=True)[:40]
        if txt and txt not in g["samples"] and len(g["samples"]) < 3:
            g["samples"].append(txt)
    button_census = sorted(groups.values(), key=lambda g: -g["count"])

    # 5. eyebrow candidates: class-hinted labels + short ALL-CAPS text runs
    eyebrows, eseen = [], set()
    for el in soup.find_all(True):
        sig = _class_sig(el)
        txt = el.get_text(" ", strip=True)
        if not txt or len(txt) > 60:
            continue
        class_hit = bool(EYEBROWISH_RE.search(sig))
        caps_hit = len(txt) >= 3 and txt == txt.upper() and any(ch.isalpha() for ch in txt)
        if not (class_hit or caps_hit):
            continue
        if el.name in ("script", "style") or BUTTONISH_RE.search(sig):
            continue
        key = (txt[:60], sig[:80])
        if key in eseen:
            continue
        eseen.add(key)
        eyebrows.append({"text": txt[:60], "classes": sig[:100],
                         "style": (el.get("style") or "")[:120],
                         "via": "class" if class_hit else "caps-text"})
        if len(eyebrows) >= 60:
            break

    # 6. chrome: header links/ctas + footer columns/social/legal
    chrome: dict = {"header": None, "footer": None}
    hdr = soup.find("header") or soup.find(class_=re.compile(r"\bheader\b", re.I))
    if hdr:
        links, ctas = [], []
        for a in hdr.find_all("a"):
            label = a.get_text(" ", strip=True)[:50]
            if not label:
                continue
            entry = {"label": label, "href": (a.get("href") or "")[:200],
                     "classes": _class_sig(a)[:100]}
            (ctas if BUTTONISH_RE.search(_class_sig(a)) else links).append(entry)
        chrome["header"] = {"classes": _class_sig(hdr)[:120],
                            "links": links[:24], "ctas": ctas[:8]}
    ftr = None
    footers = soup.find_all("footer") or soup.find_all(
        class_=re.compile(r"footer", re.I))
    if footers:
        ftr = footers[-1]
    if ftr is not None:
        columns = []
        for ul in ftr.find_all("ul"):
            lis = [li for li in ul.find_all("li") if li.find("a")]
            if len(lis) < 2:
                continue
            heading = ""
            # nearest preceding heading-ish sibling inside the column wrapper
            parent = ul.parent
            if parent is not None:
                head_el = parent.find(["h2", "h3", "h4", "h5", "h6", "p", "strong"])
                if head_el is not None and head_el.get_text(strip=True):
                    heading = head_el.get_text(" ", strip=True)[:60]
            columns.append({
                "heading": heading,
                "links": [{"label": li.find("a").get_text(" ", strip=True)[:60],
                           "href": (li.find("a").get("href") or "")[:200]}
                          for li in lis][:20]})
        social = []
        for a in ftr.find_all("a"):
            href = a.get("href") or ""
            if SOCIAL_RE.search(href):
                social.append({"href": href[:200],
                               "label": a.get_text(" ", strip=True)[:40],
                               "classes": _class_sig(a)[:100]})
        legal = ""
        for el in ftr.find_all(["p", "span", "div"]):
            t = el.get_text(" ", strip=True)
            if t and LEGAL_RE.search(t) and len(t) < 300:
                legal = t
                break
        chrome["footer"] = {"classes": _class_sig(ftr)[:120],
                            "columns": columns[:10], "social": social[:10],
                            "legalText": legal,
                            "totalLinks": len(ftr.find_all("a"))}

    # 7. inline style color census (surface evidence)
    style_census: Counter = Counter()
    for el in soup.find_all(style=True):
        for m in re.findall(r"(?:background(?:-color)?|color)\s*:\s*([^;]+)",
                            el["style"]):
            style_census[m.strip()[:50]] += 1

    return {
        "schemaVersion": SCHEMA,
        "source": str(html_path),
        "topLevel": top_level,
        "sections": sections,
        "modeCensus": dict(mode_census.most_common(40)),
        "buttonCensus": button_census[:40],
        "eyebrowCandidates": eyebrows,
        "chrome": chrome,
        "inlineStyleCensus": dict(style_census.most_common(50)),
    }


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--capture", type=Path, help="capture dir (auto-discovers the saved .html)")
    ap.add_argument("--html", type=Path, help="explicit saved-page .html (overrides --capture)")
    ap.add_argument("--out", type=Path, help="output JSON path (default: stdout summary only)")
    return ap


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if args.html:
        html_path = args.html
    elif args.capture:
        html_path = find_saved_html(args.capture)
    else:
        raise SystemExit("provide --capture <dir> or --html <file>")
    doc = mine(html_path)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(doc, indent=1))
        print(f"[done] dom-mine: {len(doc['sections'])} module sections, "
              f"{len(doc['buttonCensus'])} button families, "
              f"{len(doc['eyebrowCandidates'])} eyebrow candidates -> {args.out}")
    else:
        print(json.dumps({k: doc[k] for k in
                          ("schemaVersion", "source", "topLevel", "modeCensus")}, indent=1))
        print(f"(sections={len(doc['sections'])} buttons={len(doc['buttonCensus'])} "
              f"— pass --out to write the full document)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
