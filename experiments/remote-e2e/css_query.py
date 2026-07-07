#!/usr/bin/env python3
"""css_query.py — query the parsed Remote CSS rules for token measurement.

Usage: css_query.py <mode> [pattern]
  modes: sel <regex>   — rules whose selector matches regex (shows media + decls)
         decl <regex>  — rules whose declarations match regex
         hover         — every rule containing :hover in the selector
         colors        — hex/rgb() value census across all rules
         motion        — every transition/animation declaration
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROWS = json.loads((HERE / "css-rules.json").read_text())


def show(rows, limit=80):
    for r in rows[:limit]:
        media = f"  [{r['media']}]" if r["media"] else ""
        print(f"--- {r['file']}{media}\n{r['selector']}\n    {r['decls'][:600]}")
    if len(rows) > limit:
        print(f"... {len(rows) - limit} more")


def main():
    mode = sys.argv[1]
    if mode == "sel":
        pat = re.compile(sys.argv[2])
        show([r for r in ROWS if pat.search(r["selector"])])
    elif mode == "decl":
        pat = re.compile(sys.argv[2])
        show([r for r in ROWS if pat.search(r["decls"])])
    elif mode == "hover":
        show([r for r in ROWS if ":hover" in r["selector"]], limit=200)
    elif mode == "colors":
        c = Counter()
        for r in ROWS:
            for m in re.findall(r"#[0-9a-fA-F]{3,8}\b|rgba?\([^)]+\)", r["decls"]):
                c[m.lower()] += 1
        for val, n in c.most_common(60):
            print(f"{n:5d}  {val}")
    elif mode == "motion":
        rows = [r for r in ROWS
                if re.search(r"transition|animation", r["decls"]) and r["kind"] == "rule"]
        show(rows, limit=150)
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
