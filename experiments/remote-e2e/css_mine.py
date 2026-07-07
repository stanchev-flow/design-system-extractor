#!/usr/bin/env python3
"""css_mine.py — Remote extraction harness (experiments/remote-e2e/).

Parses the captured Remote CSS files (minified) into (media, selector, declarations)
triples so tokens can be measured WITH their @media / :hover context — the HubSpot
extraction's B12 lesson (hover rules nested in @media were missed by top-level scans).

Read-only over screenshots/remote/**; writes JSON summaries into this folder.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
FILES_DIR = REPO / "screenshots" / "remote" / (
    "Remote — Global Employment Infrastructure _ EOR, Payroll & Compliance, "
    "Worldwide_files")

CSS_FILES = [
    "template_theme-overrides.min.css",
    "template_main.min.css",
    "template_theme-macros.min.css",
    "module_Remote_-_Header_V2.min.css",
    "module_Remote_-_Hero_V2.min.css",
    "module_Remote_-_Global_Footer.min.css",
    "module_Remote_-_Icon_Grid_-_Homepage.min.css",
    "module_Remote_-_Image_Grid.min.css",
    "module_Remote_-_Panel.min.css",
    "module_Remote_-_Social_Proof_-_Logos_Global.min.css",
    "module_Remote_-_Social_Proof_-_V3.min.css",
    "module_Remote_-_Social_Proof_List_-_G2_Badges_Global.min.css",
    "module_Remote_-_Testimonials_-_Homepage.min.css",
    "module_Remote_-_Accordion.min.css",
    "module_Remote_-_Banner_-_Homepage.min.css",
    "styles__ltr.css",
]


def strip_comments(css: str) -> str:
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def parse_rules(css: str, fname: str):
    """Tokenize a stylesheet into (media, selector, decls) rows. Handles one level
    of @media nesting (the capture has no deeper nesting); skips @font-face bodies
    into their own rows; ignores @keyframes contents (motion measured separately)."""
    rows = []
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
                # skip the whole keyframes block (balanced braces)
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
            # normal rule — find matching close brace
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


def main():
    all_rows = []
    for f in CSS_FILES:
        p = FILES_DIR / f
        if not p.exists():
            print(f"MISSING: {f}", file=sys.stderr)
            continue
        css = strip_comments(p.read_text(errors="replace"))
        rows = parse_rules(css, f)
        all_rows.extend(rows)
        print(f"{f}: {len(rows)} rules")
    out = HERE / "css-rules.json"
    out.write_text(json.dumps(all_rows, indent=1))
    print(f"total {len(all_rows)} rows -> {out.name}")


if __name__ == "__main__":
    main()
