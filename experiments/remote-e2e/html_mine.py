#!/usr/bin/env python3
"""html_mine.py — DOM analysis of the captured Remote homepage.

Extracts: section order + module classes + surface-mode classes, eyebrow labels with
their inline/module colors, nav + footer structure, hero markup, and inline styles.
Read-only over screenshots/remote/**.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
HTML = REPO / "screenshots" / "remote" / (
    "Remote — Global Employment Infrastructure _ EOR, Payroll & Compliance, "
    "Worldwide.html")

soup = BeautifulSoup(HTML.read_text(errors="replace"), "html.parser")
mode = sys.argv[1] if len(sys.argv) > 1 else "sections"

if mode == "sections":
    # HubSpot CMS: top-level dnd/section wrappers
    body = soup.body
    print("=== top-level structural children of body ===")
    for el in body.find_all(["header", "main", "footer", "section", "div"], recursive=False):
        cls = " ".join(el.get("class", []))[:110]
        print(f"<{el.name}> class='{cls}' id='{el.get('id','')[:40]}'")
    main = soup.find("main") or body
    print("\n=== module sections inside main (depth-first, class contains 'module' or known names) ===")
    seen = []
    for el in main.find_all(["section", "div"]):
        cls = el.get("class", []) or []
        joined = " ".join(cls)
        if re.search(r"hero-module|main-banner|logo|iconGrid|imageGrid|accordion|panel|testimonial|social-proof|badges|footer-cta|partner", joined, re.I):
            top = joined[:130]
            if top not in seen:
                seen.append(top)
                print(f"<{el.name}> {top}")
    print("\n=== *-mode class census (surface scheme classes) ===")
    modes = {}
    for el in soup.find_all(class_=re.compile(r"-mode")):
        for c in el.get("class", []):
            if c.endswith("-mode"):
                modes[c] = modes.get(c, 0) + 1
    for k, v in sorted(modes.items(), key=lambda kv: -kv[1]):
        print(f"{v:4d}  {k}")

elif mode == "eyebrows":
    for el in soup.find_all(class_=re.compile(r"top-label|theme-label")):
        style = el.get("style", "")
        # find nearest ancestor w/ a -mode or color-relevant class
        anc = []
        p = el
        for _ in range(6):
            p = p.parent
            if p is None:
                break
            pc = " ".join(p.get("class", []) or [])
            if pc:
                anc.append(pc[:60])
        print(f"TEXT={el.get_text(strip=True)[:60]!r} style={style!r}")
        print(f"   ancestors: {' | '.join(anc[:4])}")

elif mode == "chrome":
    hdr = soup.find("header") or soup.find(class_=re.compile(r"theme-header"))
    print("=== header ===")
    if hdr:
        print(str(hdr)[:2000])
    print("\n=== footer top-level classes ===")
    ftr = soup.find("footer") or soup.find(class_=re.compile(r"footer-mod|global-footer"))
    if ftr:
        cols = ftr.find_all(class_=re.compile(r"menu|col"))
        print("footer tag:", ftr.name, " class:", " ".join(ftr.get("class", []))[:100])
        heads = [h.get_text(strip=True) for h in ftr.find_all(["h2", "h3", "h4", "h5", "h6", "strong"])][:30]
        print("column headings:", heads)
        links = ftr.find_all("a")
        print("total links:", len(links))
        social = [a.get("href") for a in links if re.search(r"linkedin|twitter|youtube|instagram|x\.com", a.get("href", ""))]
        print("social:", social[:8])

elif mode == "hero":
    hero = soup.find(class_=re.compile(r"hero-mod\b|hero-module"))
    print(str(hero)[:4000] if hero else "hero not found")

elif mode == "buttons":
    for el in soup.find_all("a", class_=re.compile(r"button|hs-button"))[:24]:
        cls = " ".join(el.get("class", []))
        print(f"{el.get_text(strip=True)[:40]!r:44s} class={cls[:100]}")

elif mode == "styleattr":
    from collections import Counter
    c = Counter()
    for el in soup.find_all(style=True):
        s = el["style"]
        for m in re.findall(r"(?:background(?:-color)?|color)\s*:\s*([^;]+)", s):
            c[m.strip()[:50]] += 1
    for k, v in c.most_common(40):
        print(f"{v:4d}  {k}")

elif mode == "sectionsfull":
    main = soup.find("main") or soup.body
    # HubSpot dnd rows: walk direct descendants w/ class containing 'dnd' or data attrs
    for el in main.find_all(True, recursive=False):
        print(f"<{el.name}> class='{' '.join(el.get('class', []))[:120]}'")
        for el2 in el.find_all(True, recursive=False):
            print(f"   <{el2.name}> class='{' '.join(el2.get('class', []))[:110]}'")
