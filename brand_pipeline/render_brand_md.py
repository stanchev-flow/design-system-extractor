#!/usr/bin/env python3
"""render_brand_md.py - deterministic projection brand.yaml -> brand.md.

brand.yaml is canonical (see brand_pipeline/spec/brand-schema.md). brand.md is a
PURE rendered projection: this script adds no facts that are not derivable from
brand.yaml. Never hand-edit brand.md; edit brand.yaml and re-render.

(SIGN-OFF #1) `--check` re-renders and diffs against the committed brand.md. Drift
is reported as a WARNING and exits non-zero ONLY in --check mode so a human can
notice hand-edits; it is never wired into a build gate / CI.

Usage:
  python3 render_brand_md.py <brand.yaml> [-o brand.md]
  python3 render_brand_md.py <brand.yaml> --check
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.stderr.write("PyYAML required: pip install pyyaml\n")
    raise


def _val(node):
    """Unwrap a rule-envelope dict to its `value`, else return as-is."""
    if isinstance(node, dict) and "value" in node:
        return node["value"]
    return node


def _is_low(node) -> bool:
    return isinstance(node, dict) and node.get("confidence") in ("low", "medium")


_MEDIA_KW = ("image", "media", "photo", "logo", "icon", "video", "gallery",
             "wordmark", "avatar", "thumbnail", "illustration", "map")


def _slot_type(slot) -> str:
    """A slot's type: explicit `type` if present (HubSpot shape), else inferred
    from name/role/fill keywords (WoodWave shape). Brand-agnostic."""
    if slot.get("type"):
        return slot["type"]
    fill = slot.get("fill")
    blob = " ".join(str(x) for x in [
        slot.get("name", ""), slot.get("role", ""),
        " ".join(fill) if isinstance(fill, list) else "",
    ]).lower()
    return "media" if any(k in blob for k in _MEDIA_KW) else "content"


def _slot_use(slot) -> str:
    return slot.get("useCase") or slot.get("role") or slot.get("name") or ""


def _origin_badge(entry: dict) -> str:
    """`origin` of a primitive/block entry, annotated with its evidence handle:
    extracted -> provenance section ids; designed -> overridable flag. Pure
    projection of brand.yaml fields; adds no facts."""
    origin = entry.get("origin", "")
    if origin == "extracted":
        prov = entry.get("provenance") or []
        return f"extracted: {', '.join(prov)}" if prov else "extracted"
    if origin == "designed":
        return "designed, overridable" if entry.get("overridable") else "designed"
    return origin


def _origin_detail(entry: dict) -> str:
    """Fallback line when an entry carries no `rules`: surface the designed `note`
    or the prohibition `value`/conflictsWith so every item reads cleanly."""
    if entry.get("value"):
        bits = [str(entry["value"])]
        if entry.get("conflictsWith"):
            bits.append(f"(conflicts with {entry['conflictsWith']})")
        return " ".join(bits)
    df = entry.get("designedFrom") or {}
    return df.get("note", "") if isinstance(df, dict) else ""


def _origin_items(items) -> list[tuple[str, dict]]:
    """Named primitive/block entries from canonical maps or legacy id lists.

    The renderer remains a projection reader: accepting the legacy list does not
    rewrite it into canonical brand data, so validation can still reject it.
    """
    if isinstance(items, dict):
        return [(str(key), value) for key, value in items.items()
                if isinstance(value, dict)]
    if isinstance(items, list):
        return [
            (str(value.get("id") or value.get("name") or index), value)
            for index, value in enumerate(items) if isinstance(value, dict)
        ]
    raise TypeError("primitives/blocks must be a mapping or legacy list")


def _origin_summary(items) -> str:
    """`N extracted / M designed` counts for a primitives/blocks map."""
    entries = _origin_items(items)
    ex = sum(1 for _, v in entries if v.get("origin") == "extracted")
    de = sum(1 for _, v in entries if v.get("origin") == "designed")
    return f"{ex} extracted / {de} designed"


def _slot_component(slot, layout) -> str:
    """The contract(s) a slot maps to: the library-agnostic `blockMapping` entries
    (v0 schema) for this slot name, falling back to legacy `componentMapping` or a
    `mappedComponent` shape for older brand.yaml files."""
    mc = slot.get("mappedComponent")
    if isinstance(mc, dict) and mc.get("name"):
        return mc["name"]
    comps: list[str] = []
    for m in layout.get("blockMapping", []):
        if m.get("slot") == slot.get("name") and m.get("contract") \
                and m["contract"] not in comps:
            comps.append(m["contract"])
    if comps:
        return ", ".join(comps)
    for m in layout.get("componentMapping", []):  # legacy fallback
        if m.get("slot") == slot.get("name") and m.get("component") \
                and m["component"] not in comps:
            comps.append(m["component"])
    return ", ".join(comps)


def render(doc: dict, brand_dir=None) -> str:
    b = doc.get("brand", {})
    name = b.get("name", "Brand")
    src = b.get("sourceUrl", "")
    host = src.replace("https://", "").replace("http://", "").rstrip("/")
    ver = doc.get("version", "1.0")

    out: list[str] = []
    w = out.append

    w(f"# brand.md - {host}   <!-- rendered from brand.yaml v{ver} by "
      f"render_brand_md.py; DO NOT EDIT -->")
    w("")
    w("> Generated projection. Edit `brand.yaml` (canonical) and re-render; "
      "never hand-edit this file.")
    w("")

    # 1. Brand snapshot
    w("## 1. Brand snapshot")
    snap = _val(b.get("snapshot", "")).strip()
    w(f"{name} is {snap[0].lower() + snap[1:] if snap else ''}")
    w("")

    # 2. Surface grammar
    sg = doc.get("surfaceGrammar", {})
    surfaces = doc.get("tokens", {}).get("surfaces", {})
    w("## 2. Surface grammar")
    w(f"{len(sg.get('roles', []))} surface roles:")
    for role in sg.get("roles", []):
        s = surfaces.get(role, {})
        intent = s.get("intent") or s.get("schemeMode") or "?"
        w(f"- `{role}` - bg `{s.get('bg','?')}`, intent "
          f"`{intent}`, text `{s.get('textPrimary','?')}`"
          + (f", accent `{s['textAccent']}`" if s.get("textAccent") else ""))
    rhythm = _val(sg.get("pageRhythm", []))
    if rhythm:
        w("")
        w("Page rhythm: " + " -> ".join(rhythm) + ".")
    trans = _val(sg.get("transition", ""))
    if trans:
        if str(trans) == "hard-cut":
            w(f"Section transitions are **{trans}** - no gradients, fades, or divider "
              "rules at seams.")
        else:
            w(f"Section transitions are **{trans}**.")
    nesting = sg.get("nesting", [])
    if isinstance(nesting, str) and nesting.strip():
        w(f"Nesting: {nesting.strip()}.")
    elif isinstance(nesting, list):
        for nest in nesting:
            if isinstance(nest, dict):
                w(f"Nesting: `{nest.get('child', '?')}` allowed only inside "
                  + ", ".join(f"`{p}`" for p in nest.get("allowedParents", [])) + ".")
    w("")

    # 3. Color tokens (library-agnostic: semantic role + value)
    colors = doc.get("tokens", {}).get("colors", {})
    w("## 3. Color tokens (semantic role + value)")
    w("")
    w("| token | value | role |")
    w("|---|---|---|")
    for tok, c in colors.items():
        w(f"| `{tok}` | `{c.get('value','')}` | {c.get('role','')} |")
    w("")

    # 4. Typography roles
    types = doc.get("tokens", {}).get("type", {})
    w("## 4. Typography roles")
    w("")
    w("| role | family | size (base) | line-height | weight | case |")
    w("|---|---|---|---|---|---|")
    for role, t in types.items():
        size = t.get("sizeRem", {})
        size_s = size.get("base") if isinstance(size, dict) else size
        w(f"| {role} | {t.get('family','')} | {size_s}rem | "
          f"{t.get('lineHeight','')} | {t.get('weight','-')} | {t.get('case','')} |")
    w("")

    # 5. Spacing system (intent + value)
    spacing = doc.get("tokens", {}).get("spacing", {})
    w("## 5. Spacing system")
    for role, s in spacing.items():
        desc = f" - {s['role']}" if s.get("role") else ""
        w(f"- `{role}`: {s.get('value','')}{desc}")
    w("")

    # 6. Layout grammar (archetype + surface intent)
    w("## 6. Layout grammar")
    for lay in doc.get("layouts", []):
        surf = lay.get("surfaceIntent") or lay.get("surfaceMode", {}).get("mode", "?")
        slots = lay.get("slots", [])
        role = slots[0].get("role", "") if slots else ""
        w(f"- **{lay.get('archetype','').title()}** ({lay['id']}, {surf}): {role}.")
    w("")

    # 7. Slot -> contract mapping (library-agnostic)
    w("## 7. Slot mapping (slot -> primitive/block contract)")
    for lay in doc.get("layouts", []):
        w(f"### {lay['id']}")
        w("")
        w("| slot | role | contract |")
        w("|---|---|---|")
        mappings = lay.get("blockMapping", [])
        if mappings:
            for m in mappings:
                w(f"| {m.get('slot','')} | {m.get('role','')} | `{m.get('contract','')}` |")
        else:
            for slot in lay.get("slots", []):
                if isinstance(slot, dict):
                    w(f"| {slot.get('name','')} | {_slot_use(slot)} | "
                      f"`{_slot_component(slot, lay) or _slot_type(slot)}` |")
        w("")

    # 8. Composition mechanics
    w("## 8. Composition mechanics")
    for rule in doc.get("compositionRules", []):
        flag = " _(low confidence)_" if _is_low(rule) else ""
        w(f"- **{rule['id']}**: {rule.get('statement','')}{flag}")
    w("")

    # 9. Do (positive house style)
    w("## 9. Do")
    dos = doc.get("do", [])
    if dos:
        for r in dos:
            w(f"- {r.get('statement','')}")
    else:
        w("- None.")
    w("")

    # 10. Avoid (soft discouragements)
    w("## 10. Avoid")
    avoids = doc.get("avoid", [])
    if avoids:
        for r in avoids:
            w(f"- {r.get('statement','')}")
    else:
        w("- None.")
    w("")

    # 11. Never-do (hard prohibitions)
    w("## 11. Never-do")
    for nd in doc.get("neverDo", []):
        w(f"- {nd.get('statement','')}")
    w("")

    # 12. Primitive & block rules (THIS brand's overrides against the shared contracts)
    prims = doc.get("primitives", {}) or {}
    blks = doc.get("blocks", {}) or {}
    if prims or blks:
        w("## 12. Primitive & block rules")
        if prims:
            w("")
            w(f"**Primitives** ({_origin_summary(prims)})")
            for key, p in _origin_items(prims):
                bits = [_origin_badge(p)] if p.get("origin") else []
                if p.get("use"):
                    bits.append(f"use: {p['use']}")
                if p.get("variant") is not None:
                    bits.append(f"variant: {p['variant']}")
                if p.get("remapFrom"):
                    bits.append(f"remap of {p['remapFrom']}")
                refs = p.get("refs") or []
                if refs:
                    bits.append("refs: " + ", ".join(f"`{r}`" for r in refs))
                meta = f" ({'; '.join(bits)})" if bits else ""
                # When the entry references neverDo via `refs`, the binding IS the rule —
                # suppress the (redundant) rule prose so brand.md restates nothing.
                detail = "" if refs else ("; ".join(p.get("rules", []) or []) or _origin_detail(p))
                w(f"- `{key}`{meta}" + (f" - {detail}" if detail else ""))
        if blks:
            w("")
            w(f"**Blocks** ({_origin_summary(blks)})")
            for key, blk in _origin_items(blks):
                bits = [_origin_badge(blk)] if blk.get("origin") else []
                slot_bits = []
                for sname, sdef in (blk.get("slots", {}) or {}).items():
                    if isinstance(sdef, dict) and sdef.get("use"):
                        slot_bits.append(f"{sname}: {sdef['use']}")
                if slot_bits:
                    bits.append("slots — " + ", ".join(slot_bits))
                refs = blk.get("refs") or []
                if refs:
                    bits.append("refs: " + ", ".join(f"`{r}`" for r in refs))
                meta = f" ({'; '.join(bits)})" if bits else ""
                # `refs` supersedes rule prose (single source of truth = neverDo); slot
                # bindings above are kept.
                detail = "" if refs else ("; ".join(blk.get("rules", []) or []) or _origin_detail(blk))
                w(f"- `{key}`{meta}" + (f" - {detail}" if detail else ""))
        w("")

    # 13. Locked dials
    dials = doc.get("voice", {}).get("dials", {})
    w("## 13. Locked dials")
    for d in ("variance", "motion", "density"):
        if d in dials:
            flag = " _(low/medium confidence)_" if _is_low(dials[d]) else ""
            state = dials[d].get("state") if isinstance(dials[d], dict) else None
            state_s = f" _(state: {state})_" if state else ""
            w(f"- **{d.upper()}: {_val(dials[d])}**{flag}{state_s}")
    w("")

    # 13b. Motion spec (authored) — pure projection of voice.motionSpec. When the brand
    # carries a concrete motion spec, project its easing/durations/interactions so brand.md
    # documents the DEFINED motion (not just the inferred dial value).
    mspec = doc.get("voice", {}).get("motionSpec") or {}
    if mspec:
        w("## Motion (authored spec)")
        intensity = _val(dials.get("motion", {})) if dials else "low"
        st = mspec.get("state")
        w(f"Motion is an authored spec{f' (state: {st})' if st else ''}; intensity stays "
          f"`{intensity}` (calm/editorial) — no bounce, spring, overshoot, or snap.")
        w("")
        easing = (mspec.get("easing") or {}).get("primary")
        if easing:
            w(f"- Easing (primary): `{easing}`")
        dur = mspec.get("durations") or {}
        if dur:
            w("- Durations: " + ", ".join(f"{k} `{v}`" for k, v in dur.items()))
        # VALUES-ONLY projection: emit the authored motion VALUES (easing, durations,
        # link/scroll-reveal token + translateY). The behavioral essay for each interaction
        # and the forbidden bounce/spring/overshoot/snap list live in the base style's Motion
        # section (single source of truth) and are intentionally NOT restated here.
        link = mspec.get("link") or {}
        if link:
            w(f"- Link interaction: **{link.get('value','')}**")
        rev = mspec.get("scrollReveal") or {}
        if rev:
            ty = rev.get("translateY")
            w(f"- Scroll reveal: **{rev.get('value','')}**"
              + (f" (translateY {ty})" if ty else ""))
        if mspec.get("reducedMotion"):
            w(f"- prefers-reduced-motion: **{mspec['reducedMotion']}** "
              "(transitions/reveals disabled when the user requests reduced motion).")
        w("")

    # 14. Recipe policy
    rp = doc.get("recipePolicy", {})
    w("## 14. Recipe policy")
    for k, v in rp.items():
        w(f"- `{k}`: {_val(v)}")
    w("")

    # 15. Confidence flags
    flags: list[str] = []
    if _is_low(b.get("snapshot")):
        flags.append("brand snapshot")
    for d in ("variance", "motion", "density"):
        if d in dials and _is_low(dials[d]):
            cl = dials[d].get("changelog") or [{}]
            note = cl[-1].get("note", "") if cl else ""
            flags.append(f"{d.upper()} dial: {dials[d].get('confidence')} confidence"
                         + (f" - {note}" if note else ""))
    for rule in doc.get("compositionRules", []):
        if _is_low(rule):
            flags.append(f"{rule['id']}: {rule.get('confidence')} confidence")
    for lay in doc.get("layouts", []):
        if lay.get("confidence") in ("low", "medium"):
            flags.append(f"layout {lay['id']}: {lay['confidence']} confidence")
    w("## 15. Confidence flags")
    if flags:
        for f in flags:
            w(f"- {f}")
    else:
        w("- None.")
    w("")

    # 16. Section catalog (slot contracts)
    layouts = doc.get("layouts", [])
    if layouts:
        w("## 16. Section catalog (slot contracts)")
        w("")
        w("Each layout as an abstract contract: archetype, surface intent, use case, and "
          "the slots it exposes (slot -> type -> use case -> contract).")
        w("")
        for lay in layouts:
            surf = lay.get("surfaceIntent") or lay.get("surfaceMode", {}).get("mode", "?")
            arche = lay.get("archetype", "")
            w(f"### {lay['id']} - {arche} ({surf})")
            uc = lay.get("useCase")
            if uc:
                w("")
                w(uc)
            slots = lay.get("slots", [])
            if slots:
                w("")
                w("| slot | type | use case | contract |")
                w("|---|---|---|---|")
                for s in slots:
                    w(f"| {s.get('name','')} | {_slot_type(s)} | {_slot_use(s)} | "
                      f"`{_slot_component(s, lay)}` |")
            w("")

    # 17. Layout patterns (project library) — projection of the sibling layout-library.yaml
    # (brand-schema.md §4.4/§5.5). Reusable use-case patterns this project has learned; each
    # is the generalization a layouts[] instance links to via patternRef.
    _render_layout_patterns(w, brand_dir)

    # 18. Component recipes (brand-schema §4.4e / §9b, fix2 2026-07) — prose projection
    # of the brand's OWN recurring component anatomies so any generator consuming the
    # kit reads them as part of the brand's voice. Genre framing stays descriptive
    # per-brand (the recipe intent prose), never a shared taxonomy.
    _render_recipes(w, brand_dir)

    return "\n".join(out).rstrip() + "\n"


def _render_layout_patterns(w, brand_dir) -> None:
    if not brand_dir:
        return
    from pathlib import Path as _P
    lib = _P(brand_dir) / "layout-library.yaml"
    if not lib.exists():
        return
    data = yaml.safe_load(lib.read_text()) or {}
    pats = data.get("patterns") or []
    if not pats:
        return
    w("## 17. Layout patterns (project library)")
    w("")
    w("Reusable, use-case-keyed layout patterns extracted from this project (project tier — "
      "wins over the standard library on ties). Sizes are relationships/classes, never px.")
    w("")
    w("| pattern | use case | archetype | surface | special treatments | origin |")
    w("|---|---|---|---|---|---|")
    for p in pats:
        treatments = ", ".join(sorted({str(t.get("kind")) for t in
                                       (p.get("specialTreatments") or []) if t.get("kind")})) or "-"
        w(f"| `{p.get('id','')}` | {p.get('useCase','')} | {p.get('archetypeRef','')} | "
          f"{p.get('surfaceIntent','')} | {treatments} | {p.get('origin','')} |")
    w("")


def _render_recipes(w, brand_dir) -> None:
    """"Component recipes" section (brand-schema §9b): each recipe described in prose
    with its anatomy, variants + use cases, and the patterns bound to it. Recipe-less
    brands omit the section (recipes are brand data; there is no standard tier)."""
    if not brand_dir:
        return
    from pathlib import Path as _P
    lib = _P(brand_dir) / "layout-library.yaml"
    if not lib.exists():
        return
    recipes = (yaml.safe_load(lib.read_text()) or {}).get("recipes") or []
    recipes = [r for r in recipes if isinstance(r, dict) and r.get("id")]
    if not recipes:
        return
    w("## 18. Component recipes")
    w("")
    w("Recurring multi-slot anatomies this brand reuses across sections — recorded as "
      "first-class recipes in `layout-library.yaml` `recipes:` so generators compose "
      "them as units instead of re-deriving the parts.")
    w("")
    for r in recipes:
        w(f"### `{r.get('id')}` — {r.get('name') or r.get('id')}")
        w("")
        intent = " ".join(str(r.get("intent") or "").split())
        if intent:
            w(intent)
            w("")
        anatomy = [a for a in (r.get("anatomy") or []) if isinstance(a, dict)]
        if anatomy:
            w("Anatomy: " + " → ".join(
                f"**{a.get('slot','?')}**{'' if a.get('required', True) else ' (optional)'}"
                for a in anatomy) + ".")
            w("")
        for v in (r.get("variants") or []):
            if isinstance(v, dict) and v.get("id"):
                use = " ".join(str(v.get("useCase") or "").split())
                w(f"- **{v['id']}** — {use}" if use else f"- **{v['id']}**")
        used = [str(u) for u in (r.get("usedBy") or []) if u]
        if used:
            w("")
            w("Used by: " + ", ".join(f"`{u}`" for u in used) + ".")
        w("")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("brand_yaml", type=Path)
    ap.add_argument("-o", "--out", type=Path, default=None,
                    help="output path (default: brand.md next to brand.yaml)")
    ap.add_argument("--check", action="store_true",
                    help="re-render and diff against committed brand.md (WARNING only)")
    args = ap.parse_args()

    doc = yaml.safe_load(args.brand_yaml.read_text())
    rendered = render(doc, brand_dir=args.brand_yaml.parent)
    out = args.out or args.brand_yaml.with_name("brand.md")

    if args.check:
        current = out.read_text() if out.exists() else ""
        if current != rendered:
            sys.stderr.write(
                f"WARNING: {out} drifts from render_brand_md({args.brand_yaml}). "
                "Re-render to resolve. (Drift is a warning, not a build blocker.)\n")
            return 1
        print(f"OK: {out} matches render_brand_md({args.brand_yaml}).")
        return 0

    out.write_text(rendered)
    print(f"Wrote {out} ({len(rendered)} bytes) from {args.brand_yaml}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
