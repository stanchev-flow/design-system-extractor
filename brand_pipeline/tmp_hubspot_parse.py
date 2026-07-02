#!/usr/bin/env python3
"""One-off HubSpot saved-page parser (NOT part of the spine).

Extracts real design tokens (CSS custom properties, @font-face, font-family,
radius, shadow, color) from the locally saved "Save Page As, Complete" capture so
brand.yaml can be grounded in the actual HTML/CSS instead of the screenshot.

Usage: ./venv/bin/python brand_pipeline/tmp_hubspot_parse.py
"""
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path("screenshots/hubspot/HubSpot")
HTML = BASE / "HubSpot _ Software & Tools for your Business - Homepage.html"
FILES = BASE / "HubSpot _ Software & Tools for your Business - Homepage_files"


def read(p):
    return Path(p).read_text(encoding="utf-8", errors="ignore")


def css_vars(text):
    """Return dict of --custom-prop -> value (last wins)."""
    out = {}
    for m in re.finditer(r"(--[A-Za-z0-9_-]+)\s*:\s*([^;{}]+)", text):
        out[m.group(1)] = m.group(2).strip()
    return out


def font_faces(text):
    faces = []
    for m in re.finditer(r"@font-face\s*\{([^}]*)\}", text):
        block = m.group(1)
        fam = re.search(r"font-family\s*:\s*([^;]+)", block)
        wght = re.search(r"font-weight\s*:\s*([^;]+)", block)
        src = re.search(r"url\(([^)]+)\)", block)
        faces.append({
            "family": fam.group(1).strip().strip('"\'') if fam else None,
            "weight": wght.group(1).strip() if wght else None,
            "src": src.group(1).strip().strip('"\'') if src else None,
        })
    return faces


def font_families(text):
    c = Counter()
    for m in re.finditer(r"font-family\s*:\s*([^;}{]+)", text):
        c[m.group(1).strip()] += 1
    return c


def hex_colors(text):
    c = Counter()
    for m in re.finditer(r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b", text):
        c[m.group(0).lower()] += 1
    return c


def main():
    theme = read(FILES / "hubspot-theme.stable.css")
    html = read(HTML)

    print("=== THEME CSS @font-face ===")
    for f in font_faces(theme):
        print(f)
    print()

    print("=== HTML inline @font-face (head) ===")
    for f in font_faces(html):
        print(f)
    print()

    print("=== font-family declarations (theme, top 25) ===")
    for fam, n in font_families(theme).most_common(25):
        print(f"{n:5d}  {fam}")
    print()

    print("=== font-family declarations (html, top 25) ===")
    for fam, n in font_families(html).most_common(25):
        print(f"{n:5d}  {fam}")
    print()

    vars_theme = css_vars(theme)
    print(f"=== THEME CSS custom properties: {len(vars_theme)} total ===")
    groups = defaultdict(list)
    for k, v in vars_theme.items():
        key = k
        for tag in ("color", "border-radius", "radius", "shadow", "font", "space", "spacing", "elevation", "text", "fill", "bg", "background"):
            if tag in k:
                groups[tag].append((k, v))
                break
    for tag in ("color", "border-radius", "radius", "shadow", "font", "space", "spacing", "elevation", "fill", "bg", "background", "text"):
        items = groups.get(tag, [])
        if not items:
            continue
        print(f"\n--- group:{tag} ({len(items)}) ---")
        for k, v in items[:60]:
            print(f"  {k}: {v}")

    print("\n=== top hex colors in THEME css (top 40) ===")
    for hx, n in hex_colors(theme).most_common(40):
        print(f"{n:6d}  {hx}")

    print("\n=== top hex colors in HTML (top 30) ===")
    for hx, n in hex_colors(html).most_common(30):
        print(f"{n:6d}  {hx}")


if __name__ == "__main__":
    main()
