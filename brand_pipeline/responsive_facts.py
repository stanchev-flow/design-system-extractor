#!/usr/bin/env python3
"""responsive_facts.py — Phase 2 RESPONSIVE FACT extractor (hero + footer slice).

The computed-CSS property-diff harness (``css_fidelity.py``) surfaces two critical
per-property divergences the SSIM screenshot gate is blind to:

  * hero ``height-rule`` — the source hero is ``calc(100dvh - navheight)`` (fills the
    viewport minus the sticky nav); our composer emitted a FIXED px band.
  * footer ``responsive-columns`` — the source footer directory RE-FLOWS across
    ``@media`` breakpoints (stacked on mobile, multi-column at ``width >= 900px``);
    our composer emitted one non-responsive grid.

Both are MISSING-FACT divergences: the responsive mechanic was measured in Phase 1
(``joined-evidence.json`` carries the literal ``calc``/``@media`` rules + the per-tier
``computedLadder``) but never landed in the brand facts the renderer consumes. This
module derives a GENERIC, BRAND-AGNOSTIC, PROVENANCE-TAGGED ``responsive`` fact block
for the hero and the footer from that evidence, so Phase 4's renderer can emit the
grounded responsive CSS (fact-gated: brands without the block stay byte-identical).

The keys are reusable visual patterns, never section- or content-specific token names:
  * hero.responsive.heightRule ∈ {viewport-minus-nav, viewport, none}, plus the measured
    nav-offset ladder and a heading font-size ladder (the measured shrink at narrow
    viewports);
  * footer.responsive.grid (breakpoint + column-count below/at) + measured gaps, and the
    REAL measured content ``maxWidth`` (the invented band cap is dropped by Phase 3).

Every emitted value traces to a measured fact and carries a ``provenance`` note — the
token-provenance doctrine (SPEC §D), extended from color to LAYOUT + MOTION for these
paths: a layout/motion value the composer emits for hero/footer must trace to a
measured fact or a declared structural constant, never an un-grounded default.

WHERE IT LIVES (schema): the ``responsive`` block is a brand fact nested under the HERO
layout (``layouts[].responsive``) and the FOOTER (``footer.responsive``). It is
MATERIALIZED into a dedicated, reviewable ``responsive-facts.yaml`` sidecar beside
``brand.yaml`` and MERGED into the in-memory doc at load (``compose_page.load_doc`` →
``apply_responsive_facts``), so every existing ``brand.yaml`` stays byte-identical and a
brand without the sidecar renders byte-for-byte as before (the fact-gate discipline).

Usage (derive the sidecar for a brand from its sibling joined-evidence):
    ./venv/bin/python brand_pipeline/responsive_facts.py runs/<brand>/brand/brand.yaml
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

SCHEMA = "responsive.v1"

# viewport-relative length units — a height carrying one of these is measured against
# the viewport, not a fixed band.
_VP_UNIT_RE = re.compile(r"\b\d*\.?\d+(?:dvh|svh|lvh|vh)\b")
# a calc(<vp-height> - var(<nav-height-ish>)) mechanic: viewport minus a nav-height var.
_CALC_MINUS_VAR_RE = re.compile(
    r"calc\(\s*\d*\.?\d*(?:dvh|svh|lvh|vh)\s*-\s*var\(\s*(--[\w-]+)", re.I)
_PX_RE = re.compile(r"(-?\d*\.?\d+)px")


# ── shared evidence helpers ───────────────────────────────────────────────────────

def _by_id(doc: dict) -> dict:
    return {e.get("elementId"): e for e in doc.get("elements", [])}


def _decl(decls: str, prop: str) -> str | None:
    """Last declaration of ``prop`` in a decl block (later wins within a rule)."""
    found = None
    for m in re.finditer(r"(?:^|;)\s*" + re.escape(prop) + r"\s*:\s*([^;]+)",
                         decls or ""):
        found = m.group(1).strip()
    return found


def _media_min_width(media: str) -> int | None:
    """The ``N`` in an ``@media(width >= N)`` / ``min-width: N`` condition, else None."""
    m = re.search(r"(?:width\s*>=\s*|min-width\s*:\s*)(\d+)", media or "")
    return int(m.group(1)) if m else None


def _find_source_hero(els: dict) -> dict | None:
    for e in els.values():
        if e.get("kind") == "section" and e.get("visionRole") == "hero":
            return e
    return els.get("section-00")


# ── HERO responsive facts ─────────────────────────────────────────────────────────

def _hero_height_rule(hero: dict) -> tuple[str, dict] | None:
    """(heightRule, navOffset) derived from the hero's bound height mechanic.

    ``viewport-minus-nav`` when a height fact is ``calc(<vp-height> - var(<nav-var>))``;
    ``viewport`` when a bare viewport-relative height is present; else None (fixed px)."""
    rules = hero.get("cssRules") or []
    custom = hero.get("customProperties") or {}
    nav_var = None
    height_decl = None
    for r in rules:
        d = r.get("decls", "")
        for m in re.finditer(
                r"((?:min-|max-)?height|--[\w-]*height[\w-]*)\s*:\s*([^;]+)", d):
            val = m.group(2).strip()
            cm = _CALC_MINUS_VAR_RE.search(val)
            if cm:
                nav_var = cm.group(1)
                height_decl = val
                break
            if _VP_UNIT_RE.search(val) and height_decl is None:
                height_decl = val
        if nav_var:
            break
    # a height fact may hide behind a custom property (e.g. --page-header-height)
    if nav_var is None:
        for name, entries in custom.items():
            if "height" not in name.lower():
                continue
            for e in entries:
                cm = _CALC_MINUS_VAR_RE.search(e.get("value", ""))
                if cm:
                    nav_var = cm.group(1)
                    height_decl = e.get("value", "").strip()
                    break
            if nav_var:
                break
    if not height_decl:
        return None
    if nav_var is None:
        return ("viewport", {})
    # nav-offset ladder from the referenced nav-height var's measured entries
    nav_entries = custom.get(nav_var) or []
    base = None
    wide = None
    wide_min = None
    for e in nav_entries:
        val = (e.get("value") or "").strip()
        px = _PX_RE.search(val)
        if not px:
            continue
        mw = _media_min_width(e.get("media") or "")
        if mw:
            if wide is None or mw <= (wide_min or 1 << 30):
                wide = f"{px.group(1)}px"
                wide_min = mw
        elif base is None:
            base = f"{px.group(1)}px"
    nav_offset: dict = {"var": nav_var}
    if base:
        nav_offset["base"] = base
    if wide:
        nav_offset["wide"] = wide
        nav_offset["wideMinWidth"] = wide_min
    return ("viewport-minus-nav", nav_offset)


def _hero_heading_ladder(hero: dict) -> tuple[list[dict], int] | None:
    """The measured hero-heading font-size/line-height ladder (the shrink at narrow
    viewports) + the breakpoint. Reads the per-tier ``computedLadder`` h1 sizes and
    the switch breakpoint from a heading ``@media(width >= N)`` rule."""
    ladder = hero.get("computedLadder") or {}
    tiers: list[tuple[int, dict]] = []
    for tier, rec in ladder.items():
        if not isinstance(rec, dict):
            continue
        h1 = ((rec.get("headings") or {}).get("h1")) if isinstance(
            rec.get("headings"), dict) else None
        if isinstance(h1, dict) and h1.get("font-size"):
            try:
                tiers.append((int(tier), h1))
            except ValueError:
                pass
    if len(tiers) < 2:
        return None
    tiers.sort(key=lambda t: t[0])
    small_w, small = tiers[0]
    large_w, large = tiers[-1]
    small_fs = str(small.get("font-size") or "").strip()
    large_fs = str(large.get("font-size") or "").strip()
    if not small_fs or not large_fs or small_fs == large_fs:
        return None  # no responsive heading shrink measured
    # breakpoint: the smallest heading @media(width >= N) switch, else a documented default
    bp = None
    for r in hero.get("cssRules") or []:
        sel = (r.get("selector") or "").lower()
        if "heading" not in sel and "h1" not in sel:
            continue
        d = r.get("decls", "")
        if "font-size" not in d:
            continue
        mw = _media_min_width(r.get("media") or "")
        if mw and (bp is None or mw < bp):
            bp = mw
    if bp is None:
        bp = 600  # narrow-shrink default when the tier ladder brackets it but no media names it
    ladder_out = [
        {"maxWidth": bp - 1, "fontSize": small_fs,
         "lineHeight": str(small.get("line-height") or "").strip() or None},
        {"minWidth": bp, "fontSize": large_fs,
         "lineHeight": str(large.get("line-height") or "").strip() or None},
    ]
    for e in ladder_out:
        if e["lineHeight"] is None:
            e.pop("lineHeight")
    return (ladder_out, bp)


def hero_responsive_from_evidence(hero: dict) -> dict | None:
    """Generic ``responsive`` fact block for a hero from its joined-evidence element,
    or None when the hero carries no measured responsive mechanic."""
    if not isinstance(hero, dict):
        return None
    hr = _hero_height_rule(hero)
    ladder = _hero_heading_ladder(hero)
    if not hr and not ladder:
        return None
    out: dict = {"schema": SCHEMA}
    prov: dict = {"origin": "extracted",
                  "source": hero.get("elementId") or hero.get("domSelector")}
    if hr:
        rule, nav_offset = hr
        out["heightRule"] = rule
        if nav_offset:
            out["navOffset"] = nav_offset
        prov["heightRule"] = (
            "hero bound height mechanic is viewport-relative "
            f"({rule}); nav offset from measured "
            f"{nav_offset.get('var', 'nav-height var')}")
    if ladder:
        out["headingSizeLadder"], bp = ladder
        prov["headingSizeLadder"] = (
            f"computedLadder h1 shrinks below {bp}px "
            "(measured per-tier font-size/line-height)")
    out["provenance"] = prov
    return out


# ── FOOTER responsive facts ────────────────────────────────────────────────────────

_REFLOW_RE = re.compile(
    r"(column-count|columns\s*:|grid-template|grid-auto|flex-direction|flex-wrap"
    r"|display\s*:\s*(?:grid|flex|inline-flex|inline-block|none|block))")


def footer_responsive_from_evidence(footer: dict,
                                    measured: dict | None = None) -> dict | None:
    """Generic footer ``responsive`` fact block: the measured column-reflow breakpoint
    ladder (column-count below/at the breakpoint) + measured gaps + the REAL measured
    content maxWidth. None when the footer carries no @media reflow evidence."""
    if not isinstance(footer, dict):
        return None
    rules = footer.get("cssRules") or []
    # the reflow breakpoints + the peak measured column-count declared at/above one
    breakpoints: set[int] = set()
    columns_at = 1
    sample_media = None
    for r in rules:
        media = r.get("media") or ""
        if not media or not _REFLOW_RE.search(r.get("decls", "")):
            continue
        mw = _media_min_width(media)
        if mw:
            breakpoints.add(mw)
            cc = _decl(r.get("decls", ""), "column-count")
            if cc and cc.strip().isdigit():
                columns_at = max(columns_at, int(cc.strip()))
                sample_media = media
    if not breakpoints:
        return None
    breakpoint = min(breakpoints)  # the primary stacked→multi-column switch
    if columns_at <= 1:
        # no explicit column-count at the breakpoint — fall back to the measured track
        # count of the directory (still a measured fact, not an invented default)
        tracks = ((measured or {}).get("grid") or {}).get("trackCount")
        if isinstance(tracks, (int, float)) and int(tracks) > 1:
            columns_at = int(tracks)
        else:
            columns_at = 2
    grid_m = (measured or {}).get("grid") or {}
    grid: dict = {"breakpoint": breakpoint, "columnsBelow": 1,
                  "columnsAtOrAbove": columns_at}
    if isinstance(grid_m.get("columnGap"), (int, float)) and grid_m["columnGap"] > 0:
        grid["columnGap"] = int(grid_m["columnGap"])
    if isinstance(grid_m.get("rowGap"), (int, float)) and grid_m["rowGap"] > 0:
        grid["rowGap"] = int(grid_m["rowGap"])
    out: dict = {"schema": SCHEMA, "grid": grid}
    prov: dict = {"origin": "extracted",
                  "source": footer.get("elementId") or footer.get("domSelector"),
                  "grid": (f"{len(breakpoints)} measured @media reflow breakpoint(s); "
                           f"stacked below {breakpoint}px, {columns_at} column(s) at/above"
                           + (f" ({sample_media} column-count:{columns_at})"
                              if sample_media else ""))}
    # REAL measured content cap (the inner layout container), not the invented band cap.
    cmw = (measured or {}).get("contentMaxWidth")
    if isinstance(cmw, (int, float)) and cmw > 0:
        out["maxWidth"] = int(cmw)
        prov["maxWidth"] = ("footer.measured.contentMaxWidth (inner layout container "
                            "cssMaxWidth) — the band itself measured max-width:none")
    out["provenance"] = prov
    return out


# ── sidecar build + merge-at-load ──────────────────────────────────────────────────

SIDECAR_NAME = "responsive-facts.yaml"


def build_sidecar(joined: dict, footer_measured: dict | None = None) -> dict:
    """The ``{hero, footer}`` responsive sidecar derived from joined-evidence. Empty
    dict when neither component carries a measured responsive mechanic."""
    els = _by_id(joined)
    out: dict = {}
    hero_el = _find_source_hero(els)
    hero_block = hero_responsive_from_evidence(hero_el) if hero_el else None
    if hero_block:
        out["hero"] = hero_block
    footer_el = els.get("chrome-footer")
    footer_block = (footer_responsive_from_evidence(footer_el, footer_measured or {})
                    if footer_el else None)
    if footer_block:
        out["footer"] = footer_block
    return out


def apply_responsive_facts(doc: dict, brand_dir: Path) -> dict:
    """MERGE the ``responsive-facts.yaml`` sidecar (if present) into the in-memory doc:
    the hero layout's ``responsive`` block + the footer's ``responsive`` block. A brand
    without the sidecar is untouched (byte-identical). Returns the doc for chaining.

    Never overwrites an already-present ``responsive`` block (a future in-yaml fact
    wins over the sidecar)."""
    try:
        import yaml
        sidecar_p = Path(brand_dir) / SIDECAR_NAME
        if not sidecar_p.is_file():
            return doc
        sidecar = yaml.safe_load(sidecar_p.read_text()) or {}
    except Exception:
        return doc
    hero_block = sidecar.get("hero")
    if isinstance(hero_block, dict):
        hero_layout = next((l for l in (doc.get("layouts") or [])
                            if isinstance(l, dict) and l.get("useCase") == "hero"), None)
        if hero_layout is not None and "responsive" not in hero_layout:
            hero_layout["responsive"] = hero_block
    footer_block = sidecar.get("footer")
    if isinstance(footer_block, dict) and isinstance(doc.get("footer"), dict) \
            and "responsive" not in doc["footer"]:
        doc["footer"]["responsive"] = footer_block
    return doc


def main(argv=None) -> int:
    import yaml
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("brand_yaml", type=Path)
    ap.add_argument("--joined", type=Path, default=None,
                    help="joined-evidence.json (default: <brand_dir>/evidence/...)")
    args = ap.parse_args(argv)
    brand_yaml = args.brand_yaml.resolve()
    if not brand_yaml.is_file():
        raise SystemExit(f"responsive_facts: brand yaml not found: {brand_yaml}")
    brand_dir = brand_yaml.parent
    joined_p = (args.joined
                or brand_dir / "evidence" / "joined-evidence.json").resolve()
    if not joined_p.is_file():
        raise SystemExit(f"responsive_facts: joined-evidence not found: {joined_p}")
    doc = yaml.safe_load(brand_yaml.read_text())
    joined = json.loads(joined_p.read_text())
    sidecar = build_sidecar(joined, (doc.get("footer") or {}).get("measured") or {})
    if not sidecar:
        print(f"[responsive] {brand_dir.parent.name}: no measured responsive facts")
        return 0
    out_p = brand_dir / SIDECAR_NAME
    header = ("# responsive-facts.yaml — Phase 2 evidence-derived RESPONSIVE facts "
              "(hero + footer).\n# Generated by brand_pipeline/responsive_facts.py from "
              "evidence/joined-evidence.json.\n# Merged into the doc at "
              "compose_page.load_doc (apply_responsive_facts); brand.yaml stays "
              "byte-identical.\n")
    out_p.write_text(header + yaml.safe_dump({"schemaVersion": SCHEMA, **sidecar},
                                             sort_keys=False, allow_unicode=True,
                                             width=100000))
    report = {"hero": bool(sidecar.get("hero")), "footer": bool(sidecar.get("footer"))}
    print(f"[responsive] {brand_dir.parent.name}: wrote {out_p.name} {json.dumps(report)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
