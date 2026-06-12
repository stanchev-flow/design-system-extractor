#!/usr/bin/env python3
"""Generate brand_pipeline/inventory.md from the AISB Webflow library skill export.

Reads the skill's components.json + variables.json (real site inventory for
aisb-v2-test1) and renders a concise markdown inventory the build-plan
assembler prompt consumes as the authoritative "available inventory".

Usage:
    ./venv/bin/python brand_pipeline/generate_inventory.py \
        [--skill-dir PATH] [--out PATH]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

DEFAULT_SKILL_DIR = Path(
    "~/Webflow/campaigns-hackathon/.cursor/skills/webflow-library-aisb"
).expanduser()
DEFAULT_OUT = Path(__file__).resolve().parent / "inventory.md"

GROUP_ORDER = [
    "Layout",
    "Blocks/Text",
    "Blocks/CTA",
    "Blocks/Media",
    "Blocks/Content",
    "Utility",
    "FlowKit",
]

STYLE_GUIDE_ONLY = {"Style Guide", "Styles", "Utility / Classes", "UTL - Form placeholder"}


def fmt_prop(p: dict) -> str:
    name, ptype = p["name"], p["type"]
    if ptype == "boolean":
        t, f = p.get("trueLabel"), p.get("falseLabel")
        if t and f and (t, f) != ("Visible", "Hidden"):
            return f"{name}:boolean({t}/{f})"
        return f"{name}:boolean"
    if ptype == "textContent":
        d = p.get("default")
        if isinstance(d, str) and d and len(d) <= 24:
            return f'{name}:text("{d}")'
        return f"{name}:text"
    if ptype == "slot":
        return f"[slot {name}]"
    return f"{name}:{ptype}"


def fmt_component(c: dict) -> str:
    slots = [p["name"] for p in c["props"] if p["type"] == "slot"]
    props = [fmt_prop(p) for p in c["props"] if p["type"] != "slot"]
    bits = []
    if slots:
        bits.append("slots: " + ", ".join(f"`{s}`" for s in slots))
    if props:
        bits.append("props: " + "; ".join(props))
    detail = " — ".join(bits) if bits else "(no props)"
    return f"- **`{c['name']}`** — {detail}"


def fmt_value(v) -> str:
    if isinstance(v, dict) and "aliasOf" in v:
        return f"→ {v['aliasOf']}"
    if isinstance(v, dict) and v.get("type") == "custom":
        return f"custom: `{' '.join(str(v.get('value', '')).split())}`"
    return str(v)


def render_components(data: dict) -> list[str]:
    lines: list[str] = []
    comps = [c for c in data["components"] if c["name"] not in STYLE_GUIDE_ONLY]
    by_group: dict[str, list[dict]] = {}
    for c in comps:
        by_group.setdefault(c.get("group") or "(ungrouped)", []).append(c)

    lines.append(f"## Components ({len(comps)} usable, grouped)")
    lines.append("")
    lines.append(
        "Components with `[slot …]` are scaffolds: instantiate them first, then fill"
        " slots with other component instances (never raw elements). `variant` props"
        " take one of the component's predefined variant options."
    )
    for group in GROUP_ORDER + sorted(set(by_group) - set(GROUP_ORDER)):
        if group not in by_group:
            continue
        items = sorted(by_group[group], key=lambda c: c["name"])
        scaffolds = [c for c in items if c["hasSlot"]]
        leaves = [c for c in items if not c["hasSlot"]]
        lines.append("")
        lines.append(f"### {group} ({len(items)})")
        if scaffolds:
            lines.append("")
            lines.append("Scaffolds (have slots):")
            lines.extend(fmt_component(c) for c in scaffolds)
        if leaves:
            lines.append("")
            lines.append("Leaf components:")
            lines.extend(fmt_component(c) for c in leaves)
    return lines


def render_variables(data: dict) -> list[str]:
    lines: list[str] = []
    lines.append("## Variable collections (the token system)")
    lines.append("")
    lines.append(
        "Layering: **Brand colors** (no modes) holds raw brand values; **Color"
        " schemes** / **Card color schemes** alias into it per surface mode"
        " (Primary=base, Secondary, Accent Primary, Accent Secondary, Accent"
        " Tertiary, Inverse); components and styles consume the scheme roles."
        " Retargeting a brand = update Brand colors values + Typography fonts."
        " Reference variables by `Collection > Group/Name`; never raw hex/px when"
        " a variable exists."
    )
    for col in data["collections"]:
        modes = [m["name"] for m in col["modes"]]
        mode_str = f" — modes: base, {', '.join(modes)}" if modes else " — no modes"
        lines.append("")
        lines.append(f"### {col['name']} ({col['variableCount']} variables{mode_str})")
        lines.append("")
        for v in col["variables"]:
            val = fmt_value(v["baseValue"])
            extra = ""
            if modes and v.get("modeValues"):
                mvs = {m: fmt_value(mv) for m, mv in v["modeValues"].items()}
                # only show per-mode values when they differ from base
                diff = {m: mv for m, mv in mvs.items() if mv != val}
                if diff:
                    extra = " | " + "; ".join(f"{m}: {mv}" for m, mv in diff.items())
            lines.append(f"- `{v['name']}` ({v['type'].lower()}) = {val}{extra}")
    return lines


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skill-dir", type=Path, default=DEFAULT_SKILL_DIR)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    comps = json.loads((args.skill_dir / "components.json").read_text())
    vars_ = json.loads((args.skill_dir / "variables.json").read_text())

    lines: list[str] = []
    lines.append(f"# Webflow library inventory — {comps['siteName']} (real export)")
    lines.append("")
    lines.append(
        f"Site `{comps['siteId']}`. This is the REAL component + variable inventory"
        " of the target Webflow site. Compose pages ONLY from these components and"
        " variables; reference both by their exact names below."
    )
    lines.append("")
    lines.append("Operating rules:")
    lines.append(
        "1. Layout-first: every section starts from a `Section / *` scaffold (or"
        " `Layout / *` inside it); fill slots with component instances only."
    )
    lines.append(
        "2. Reuse-before-create: map needs onto existing components/variants/props;"
        " mint a new component only on a true miss, composed from these primitives."
    )
    lines.append(
        "3. Theme via Color schemes modes on styles (surface flips = scheme mode"
        " change), not new colors. Bind colors/sizes to variables, never raw hex."
    )
    lines.append(
        "4. Spacing/width/radius come from `Sizes`, `Width`, `Section padding`,"
        " `Grid gap` collections (mode-driven on styles)."
    )
    lines.append("")
    lines.extend(render_components(comps))
    lines.append("")
    lines.extend(render_variables(vars_))
    lines.append("")
    lines.append("## Class naming conventions (existing, reuse these)")
    lines.append("")
    lines.append(
        "- Utilities `property_value` (`padding-bottom_medium`, `max-width_xlarge`,"
        " `radius_none`, `text-color_inverse`); state combos `is-*` (`is-y-center`,"
        " `is-small`); scheme combos `on-*` (`on-inverse`, `on-accent-tertiary`);"
        " gap utilities `gap-small`; responsive `tablet-1-col`, `mobile-l-vertical`,"
        " `hide_mobile`; prefixes `ix_` (interactions), `nav_`, `form_`/`wf-form_`,"
        " `ratio_`/`image-ratio_`. Don't invent a parallel convention."
    )

    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {args.out} ({args.out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
