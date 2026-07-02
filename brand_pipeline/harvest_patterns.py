#!/usr/bin/env python3
"""harvest_patterns.py - READ-ONLY feedstock miner for the layout-pattern library.

The other pipeline emits, per run, ``runs/*/single/layouts.yaml`` (schema
``source_layouts.v1``): an ordered list of sections, each with ``layout_nodes[]`` carrying
``role``, ``layout_signature``, ``pattern_candidate``, ``width_behavior``
(content_hugging / intrinsic_media / parent_stretched / full_width / fixed_size),
``placement`` and ``surface_role``; plus section-level ``pattern_candidates[]`` and
top-level ``global_layout_signatures[]`` / ``surface_relationships[]``. Those files are
explicitly ``do_not_use_as_design_system`` - source reconstruction only.

This script NEVER writes into ``contracts/`` or any brand. It scans every source
``layouts.yaml``, buckets the observed signatures BY USE-CASE (inferred from each section's
``role``), maps ``width_behavior`` -> content-shape width classes, clusters the recurring
signatures, and emits ONE candidate report so a human/agent can hand-bless the ~6-10
standard patterns in ``contracts/layout-patterns/*.yaml``. It is a SEEDING AID, not part of
generation.

Usage:
  python3 brand_pipeline/harvest_patterns.py [--runs-root runs] [-o <report.md>] [--json <report.json>]
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent

# ── use-case classification (section role -> canonical use-case) ─────────────────
# Ordered keyword rules; first match wins. Keys are the canonical use-cases the standard
# library is organized by. `None` (chrome/nav) sections are recorded separately, not seeded.
USE_CASE_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("hero",        ("hero", "opening", "masthead", "banner")),
    ("pricing",     ("pricing", "price", "plan", "tier", "ticket")),
    ("features",    ("feature", "benefit", "process", "step", "how_it_works", "capabilit",
                     "service", "value")),
    ("testimonial", ("testimonial", "quote", "review", "praise")),
    ("cta",         ("cta", "signup", "sign_up", "newsletter", "subscribe", "closing",
                     "call_to_action", "conversion", "contact", "demo", "get_started")),
    ("gallery",     ("gallery", "card", "article", "research", "portfolio", "grid",
                     "collection", "blog", "resource", "logo")),
    ("about",       ("about", "story", "mission", "intro", "info", "editorial",
                     "statement", "manifesto")),
    ("faq",         ("faq", "question", "accordion")),
    ("footer",      ("footer",)),
    ("logos",       ("logos", "partners", "clients", "brands", "trusted")),
]

CHROME_KEYS = ("navigation", "nav_", "navbar", "chrome", "header_global", "global_nav")

# width_behavior -> content-shape width class (how a slot sizes relative to its container).
WIDTH_CLASS = {
    "content_hugging": "hug",        # text/control sized to its content (short measure)
    "fixed_size": "fixed",
    "intrinsic_media": "media",      # media at its natural/intrinsic size
    "parent_stretched": "stretch",
    "full_width": "full-bleed",
}

# signature keywords that flag "special treatments" worth capturing as pattern devices.
TREATMENT_KEYWORDS = {
    "ghost-word": ("ghost", "watermark", "marquee", "oversized_display", "wordmark",
                   "identity_graphic", "oversized"),
    "overlap":    ("overlay", "over_media", "on_photo", "on_media", "straddle", "overlap"),
    "stagger":    ("stagger", "asymmetric", "offset", "rotated", "alternating"),
    "bleed":      ("full_bleed", "edge_to_edge", "fills_band", "bleed"),
    "marginal-caption": ("micro_caption", "margin", "leading_inline", "taxonomy"),
}


def classify_use_case(role: str) -> str | None:
    r = (role or "").lower()
    if any(k in r for k in CHROME_KEYS):
        return None
    for use_case, keys in USE_CASE_RULES:
        if any(k in r for k in keys):
            return use_case
    return "other"


def detect_treatments(text: str) -> set[str]:
    t = (text or "").lower()
    return {kind for kind, keys in TREATMENT_KEYWORDS.items() if any(k in t for k in keys)}


def iter_source_files(runs_root: Path):
    yield from sorted(runs_root.glob("*/**/single/layouts.yaml"))


def _project_of(path: Path) -> str:
    # runs/<version>/<project>/single/layouts.yaml  OR  runs/<project>/single/layouts.yaml
    parts = path.parts
    try:
        i = parts.index("single")
        return parts[i - 1]
    except ValueError:
        return path.parent.name


def harvest(runs_root: Path) -> dict:
    """Return an aggregate keyed by use-case with clustered signatures + content-shape hints."""
    agg: dict[str, dict] = defaultdict(lambda: {
        "sections": 0,
        "projects": set(),
        "pattern_candidates": Counter(),
        "layout_signatures": Counter(),
        "roles": Counter(),
        "text_width_classes": Counter(),
        "media_width_classes": Counter(),
        "media_placements": Counter(),
        "treatments": Counter(),
    })
    global_sigs: Counter = Counter()
    files = list(iter_source_files(runs_root))

    for f in files:
        try:
            data = yaml.safe_load(f.read_text())
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        project = _project_of(f)
        for gs in data.get("global_layout_signatures", []) or []:
            if isinstance(gs, dict) and gs.get("signature"):
                global_sigs[re.sub(r"\s+", " ", gs["signature"]).strip()] += 1

        for sec in data.get("sections", []) or []:
            if not isinstance(sec, dict):
                continue
            use_case = classify_use_case(sec.get("role", ""))
            if use_case is None:
                continue
            b = agg[use_case]
            b["sections"] += 1
            b["projects"].add(project)
            b["roles"][sec.get("role", "?")] += 1
            for pc in sec.get("pattern_candidates", []) or []:
                b["pattern_candidates"][str(pc)] += 1
            for node in sec.get("layout_nodes", []) or []:
                if not isinstance(node, dict):
                    continue
                sig = node.get("layout_signature")
                if sig:
                    b["layout_signatures"][str(sig)] += 1
                pc = node.get("pattern_candidate")
                if pc:
                    b["pattern_candidates"][str(pc)] += 1
                kind = (node.get("kind") or "").lower()
                wclass = WIDTH_CLASS.get(node.get("width_behavior", ""), node.get("width_behavior") or "?")
                is_media = kind in ("media", "graphic", "background", "image") \
                    or "media" in (node.get("role") or "").lower()
                if is_media:
                    b["media_width_classes"][wclass] += 1
                    if node.get("placement"):
                        b["media_placements"][str(node["placement"])] += 1
                elif kind in ("text", "group", "list", "container", "panel"):
                    b["text_width_classes"][wclass] += 1
                blob = " ".join(str(node.get(k, "")) for k in
                                ("layout_signature", "pattern_candidate", "role", "placement"))
                for tr in detect_treatments(blob):
                    b["treatments"][tr] += 1

    return {"use_cases": agg, "global_signatures": global_sigs, "files": [str(x) for x in files]}


def _top(counter: Counter, n: int = 8) -> list[tuple[str, int]]:
    return counter.most_common(n)


def render_report(result: dict, runs_root: Path) -> str:
    agg = result["use_cases"]
    lines: list[str] = []
    lines.append("# Layout-pattern harvest report (SEEDING AID - not a library)\n")
    lines.append(f"Scanned {len(result['files'])} source `layouts.yaml` files under "
                 f"`{runs_root}`.\n")
    lines.append("Buckets = candidate USE-CASES for `contracts/layout-patterns/<useCase>.yaml`. "
                 "Each bucket lists the recurring `pattern_candidate` / `layout_signature` "
                 "clusters, the content-shape width classes (text vs media), the placement "
                 "mix, and detected special treatments. Hand-bless the top clusters into "
                 "`origin: designed` standard patterns.\n")

    order = ["hero", "features", "pricing", "testimonial", "gallery", "cta", "about",
             "faq", "logos", "footer", "other"]
    for uc in order:
        if uc not in agg:
            continue
        b = agg[uc]
        lines.append(f"\n## {uc}  ({b['sections']} sections across "
                     f"{len(b['projects'])} projects)\n")
        lines.append(f"- **top pattern_candidates**: "
                     + ", ".join(f"`{p}`×{c}" for p, c in _top(b["pattern_candidates"])) + "\n")
        lines.append(f"- **top layout_signatures**: "
                     + ", ".join(f"`{p}`×{c}" for p, c in _top(b["layout_signatures"], 6)) + "\n")
        lines.append(f"- **text width classes**: "
                     + ", ".join(f"{k}×{v}" for k, v in _top(b["text_width_classes"])) + "\n")
        lines.append(f"- **media width classes**: "
                     + ", ".join(f"{k}×{v}" for k, v in _top(b["media_width_classes"])) + "\n")
        lines.append(f"- **media placements**: "
                     + ", ".join(f"{k}×{v}" for k, v in _top(b["media_placements"])) + "\n")
        lines.append(f"- **special treatments**: "
                     + (", ".join(f"{k}×{v}" for k, v in _top(b["treatments"])) or "none") + "\n")

    lines.append("\n## Cross-project global signatures\n")
    for sig, c in _top(result["global_signatures"], 20):
        lines.append(f"- `{sig}` ×{c}\n")
    return "".join(lines)


def _jsonable(result: dict) -> dict:
    out = {"files": result["files"],
           "global_signatures": dict(result["global_signatures"]),
           "use_cases": {}}
    for uc, b in result["use_cases"].items():
        out["use_cases"][uc] = {
            "sections": b["sections"],
            "projects": sorted(b["projects"]),
            "pattern_candidates": dict(b["pattern_candidates"]),
            "layout_signatures": dict(b["layout_signatures"]),
            "roles": dict(b["roles"]),
            "text_width_classes": dict(b["text_width_classes"]),
            "media_width_classes": dict(b["media_width_classes"]),
            "media_placements": dict(b["media_placements"]),
            "treatments": dict(b["treatments"]),
        }
    return out


def main():
    ap = argparse.ArgumentParser(description="Harvest layout-pattern seed candidates (read-only).")
    ap.add_argument("--runs-root", type=Path, default=REPO_ROOT / "runs")
    ap.add_argument("-o", "--out", type=Path, default=None, help="write markdown report here")
    ap.add_argument("--json", type=Path, default=None, help="also write the raw aggregate as JSON")
    args = ap.parse_args()

    result = harvest(args.runs_root)
    report = render_report(result, args.runs_root)
    if args.out:
        args.out.write_text(report)
        print(f"wrote {args.out}")
    else:
        print(report)
    if args.json:
        args.json.write_text(json.dumps(_jsonable(result), indent=2))
        print(f"wrote {args.json}")


if __name__ == "__main__":
    main()
