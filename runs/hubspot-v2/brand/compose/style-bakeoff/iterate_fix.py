#!/usr/bin/env python3
"""Bakeoff iteration — composition-level repairs for gate failures (criteria budget:
max 2 iterations per page; every edit logged in changes.md).

All edits re-shape model-authored slots into the adapter's PROVEN vocabulary
(the shapes the passing hero-archetype gallery lanes use); no renderer/gate code
is touched:

  neumorphism (iteration 1):
    hero    — drop the full-bleed background + text-on-media (the directive says
              imagery:none; the art-panel device it triggered pads 64px vs the
              measured panel-padding 32px — renderer/audit mismatch logged as a
              follow-up); actions cta→button ×2 (string labels).
    sec-2   — add a stated-reason body paragraph (AS-11: stats are invisible to
              the audit's primary inventory — follow-up logged).
    close   — heading string copy → {"heading": ...} (the _text string-leak
              echoes it into eyebrow+body otherwise — follow-up logged);
              support role→body; actions cta→button ×2 (kills the invented
              signup form = AS-14 + container.width 992 wrong-step).
  swiss (iteration 2):
    sec-2   — one stat-block DICT slot → header + body paragraph + stat-block
              ARRAY (the adapter's stat branch consumes arrays only).
    sec-3   — split media slot binds a real brand asset (asset:null rendered an
              empty column = AS-12).
  editorial-magazine (iteration 2):
    sec-2   — archetype cards→stack + contract stat→stat-block + header/body
              (cards' module lookup never matches 'stat' → empty section).
    sec-4   — header copy key subheading→body (the cta copy fn binds body/text
              keys only → AS-11 heading-only).

Then re-renders each page from the saved composition (no model calls) and
re-runs the onbrand gate — the battery reruns separately.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
sys.path.insert(0, str(REPO / "brand_pipeline"))

import compose_from_composition as cfc  # noqa: E402
import generate_composition as gc       # noqa: E402

BRAND_DIR = REPO / "runs" / "hubspot-v2" / "brand"
BRAND_YAML = BRAND_DIR / "brand.yaml"
BASE_STYLE = "corporate-saas-clean"
PAGE = "product-launch"

SUPPORT_LINE = "Human approval on every action came standard through the beta."


def slot(name, role, contract, copy, **kw):
    base = {"name": name, "role": role, "contract": contract,
            "textLen": "short", "sizeClass": "body", "width": "hug", "z": "front",
            "copy": copy}
    base.update(kw)
    return base


def fix_neumorphism(comp: dict) -> None:
    hero = comp["sections"][0]
    hero["slots"] = [s for s in hero["slots"] if s["name"] != "background"]
    hero["treatments"] = [t for t in (hero.get("treatments") or [])
                          if t.get("kind") != "text-on-media"]
    hero["slots"] = [s for s in hero["slots"] if s["name"] != "actions"] + [
        slot("cta-primary", "primary action", "button", "Start with Breeze"),
        slot("cta-secondary", "secondary action", "button", "See how it works"),
    ]
    proof = comp["sections"][2]
    if not any(s.get("contract") == "paragraph" for s in proof["slots"]):
        proof["slots"].insert(1, slot("proof-support", "body", "paragraph",
                                      SUPPORT_LINE, textLen="medium"))
    close = comp["sections"][4]
    for s in close["slots"]:
        if s["name"] == "heading" and isinstance(s.get("copy"), str):
            s["copy"] = {"heading": s["copy"]}
        if s["name"] == "support":
            s["role"] = "body"
    close["slots"] = [s for s in close["slots"] if s["name"] != "actions"] + [
        slot("cta-primary", "primary action", "button", "Start with Breeze"),
        slot("cta-secondary", "secondary action", "button", "Get a demo"),
    ]


def fix_swiss(comp: dict) -> None:
    proof = comp["sections"][2]
    old = next(s for s in proof["slots"] if s["name"] == "stats")
    copy = old.get("copy") or {}
    heading = ((copy.get("header") or {}).get("heading")) or "Proof from the beta."
    stats = copy.get("stats") or []
    proof["slots"] = [
        slot("proof-header", "section-title", "header", {"heading": heading}),
        slot("proof-support", "body", "paragraph", SUPPORT_LINE, textLen="medium"),
        slot("stats", "metrics-band", "stat-block", stats),
    ]
    who = comp["sections"][3]
    for s in who["slots"]:
        if s.get("contract") == "image" and not s.get("asset"):
            s["asset"] = {"src": "016-case-20studies.webp",
                          "alt": "Customer case studies", "ratio": "landscape"}


def fix_editorial(comp: dict) -> None:
    proof = comp["sections"][2]
    proof["archetype"] = "stack"
    old = next(s for s in proof["slots"] if s.get("contract") in ("stat", "stat-block"))
    stats = old.get("copy") or []
    keep = [s for s in proof["slots"] if s is not old]
    proof["slots"] = [
        slot("proof-header", "section-title", "header",
             {"heading": "Believed before it left beta."}),
        slot("proof-support", "body", "paragraph", SUPPORT_LINE, textLen="medium"),
        slot("stats", "metrics-band", "stat-block", stats),
    ] + keep
    close = comp["sections"][4]
    for s in close["slots"]:
        c = s.get("copy")
        if s.get("contract") == "header" and isinstance(c, dict) and "subheading" in c:
            c["body"] = c.pop("subheading")


def hero_layout_id() -> str | None:
    import yaml
    doc = yaml.safe_load(BRAND_YAML.read_text()) or {}
    for layout in (doc.get("layouts") or []):
        lid = str((layout or {}).get("id") or "").lower()
        if "hero" in lid or "page-header" in lid:
            return layout.get("id")
    return None


def main() -> int:
    fixes = {"neumorphism": fix_neumorphism, "swiss": fix_swiss,
             "editorial-magazine": fix_editorial}
    only = sys.argv[1] if len(sys.argv) > 1 else None
    gate_layout = hero_layout_id()
    ok_all = True
    for style, fn in fixes.items():
        if only and style != only:
            continue
        lane = HERE.parent / f"style-bakeoff-{style}" / PAGE
        comp_path = lane / "composition.json"
        comp = json.loads(comp_path.read_text())
        fn(comp)
        comp_path.write_text(json.dumps(comp, indent=2) + "\n")
        cfc.render_composition(comp, BRAND_YAML, lane, style_id=BASE_STYLE,
                               brand_dir=BRAND_DIR)
        overall, failures, _ = gc.gate_composition(lane, BRAND_YAML, BASE_STYLE,
                                                   layout=gate_layout)
        print(f"[{style}] re-render gate: {'PASS' if overall else 'FAIL'}"
              + (f" {[c for c, _ in failures]}" if failures else ""))
        ok_all &= overall
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
