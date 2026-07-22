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


# ── NAV panel surface fact ──────────────────────────────────────────────────────────
#
# The computed-CSS harness surfaces a CRITICAL missing-fact: the source mega-nav PANEL
# CONTAINER is painted a solid surface (its dropdown/flyout sheet), while our composed
# `.cs-mega` measures transparent (`navbar.measured.megaPanel.surface.bg` captured the
# transparent OUTER wrapper, not the painted inner panel). This derives the REAL panel
# surface color from the source's panel-container rules — the same GENERIC surface role
# the harness's `panel_background_rules` detector keys on — resolving any CSS-var chain
# against the element's measured customProperties. Generic key (`panelSurface`), never a
# section/content-specific name.

_PANEL_CONTAINER_RE = re.compile(
    r"flyout|dropdown|submenu|nav-tab-dropdown|nav-main-inner|burger-menu"
    r"|mega(?!-(?:card|link|item|rail|icon|title|body|cta|head|group|chev|desc"
    r"|aside|toggle|button|arrow|badge|img|image|list|main))", re.I)
_PANEL_PART_RE = re.compile(
    r"card|link|item|rail|icon|title|body|cta|head|group|chev|desc|aside|toggle"
    r"|button|arrow|badge|img|image|-list", re.I)
_STATE_PSEUDO_RE = re.compile(
    r"::?(?:hover|focus-visible|focus-within|focus|active|visited|target|checked)\b")
_EMPTY_BG = {"", "none", "transparent", "rgba(0, 0, 0, 0)", "rgba(0,0,0,0)",
             "initial", "unset", "inherit"}


def _resolve_var(value: str, custom: dict, depth: int = 0) -> str:
    """Resolve a ``var(--x)`` chain against measured customProperties (first
    non-@media entry wins), so a panel painted ``var(--container-01)`` collapses to
    its measured literal (e.g. ``#ffffff``). Non-var values pass through."""
    val = (value or "").strip()
    if depth > 6:
        return val
    m = re.fullmatch(r"var\(\s*(--[\w-]+)\s*(?:,[^)]*)?\)", val)
    if not m or m.group(1) not in (custom or {}):
        return val
    entries = custom[m.group(1)] or []
    base = next((e.get("value") for e in entries if not e.get("media")),
                entries[0].get("value") if entries else None)
    return _resolve_var(base or "", custom, depth + 1)


def _nav_panel_surface_from_evidence(nav: dict) -> tuple[dict, str, str] | None:
    """(panelSurface, source-selector, background-literal) for the nav mega-panel: the
    measured background of the source's panel CONTAINER sheet (dropdown/flyout/mega
    wrapper), resolved to a literal. None when the nav paints no solid panel container."""
    custom = nav.get("customProperties") or {}
    for r in nav.get("cssRules") or []:
        sel = r.get("selector") or ""
        if not _PANEL_CONTAINER_RE.search(sel):
            continue
        if _PANEL_PART_RE.search(sel) or _STATE_PSEUDO_RE.search(sel):
            continue
        bg = _decl(r.get("decls", ""), "background") \
            or _decl(r.get("decls", ""), "background-color")
        if not bg:
            continue
        resolved = _resolve_var(bg.split("!")[0].strip(), custom)
        if resolved.lower() in _EMPTY_BG:
            continue
        return ({"background": resolved}, sel, bg.strip())
    return None


# ── NAV responsive collapse fact ─────────────────────────────────────────────────
#
# The computed-CSS + multi-viewport harness surfaces a CRITICAL missing-fact: the
# source nav COLLAPSES to a mobile bar (logo + burger) below a measured breakpoint —
# the desktop utility row + primary link rail are MOBILE-FIRST hidden (`display:none`
# at base, `display:flex` only inside an `@media(width >= N)`), and a burger control
# (`.-mobile-only` / `*burger*`) shows below N (hidden at/above via `@media(width >= N)
# display:none`). Our composed nav never implemented this, so every narrow viewport
# overflowed (the utility + primary rows never left the bar). This derives the GENERIC,
# BRAND-AGNOSTIC collapse mechanic — the measured breakpoint + the presence of a burger
# control — so the renderer can hide the desktop rows and show the mobile bar below it.
# Generic keys (`breakpoint`, `burger`), never section/content-specific names.

# a mobile-only affordance: the burger button/group shown on narrow, hidden on desktop.
# Separators are optional so both kebab (`.-mobile-only`) and camelCase (`menuToggle`,
# `navMobileBar`) module class names match — the same mechanic, any naming convention.
_BURGER_RE = re.compile(
    r"burger|hamburger"
    r"|mobile[-_ ]?(?:only|menu|nav|bar|toggle|trigger|icon|drawer)"
    r"|menu[-_ ]?(?:toggle|trigger|button|btn|icon)"
    r"|nav[-_ ]?(?:toggle|mobile)", re.I)
# a desktop nav ROW that is mobile-first hidden and only shown at/above the breakpoint
# (the utility top-bar strip + the primary link/tab rail). Generic role words only,
# separators optional (kebab or camelCase module names).
_NAV_ROW_RE = re.compile(
    r"top[-_ ]?bar|tab[-_ ]?list|nav[-_ ]?links|nav[-_ ]?list|nav[-_ ]?main[-_ ]?tab"
    r"|main[-_ ]?nav|primary[-_ ]?nav|secondary[-_ ]?nav|desktop[-_ ]?(?:nav|panel|menu)"
    r"|utility(?:[-_ ]?(?:bar|row|nav))?|nav[-_ ]?menu[-_ ]?list", re.I)
_SHOW_DISPLAY_RE = re.compile(r"display\s*:\s*(flex|grid|block|inline-flex|table)", re.I)
_HIDE_DISPLAY_RE = re.compile(r"display\s*:\s*none\b", re.I)


def _min_width(media: str) -> int | None:
    return _media_min_width(media or "")


def _nav_collapse_from_evidence(nav: dict) -> dict | None:
    """Generic ``collapse`` fact for the nav: ``{breakpoint, burger}`` when the source
    declares a mobile-collapse mechanic — a burger control that hides at/above a
    breakpoint AND/OR desktop nav rows that are mobile-first hidden and only shown
    at/above it. None when no such mechanic is measured (fact-gate)."""
    rules = nav.get("cssRules") or []
    # base (non-@media) display state per selector — a row that is display:none at base
    # and display:flex inside a min-width @media is the mobile-first collapse signal.
    base_hidden: set[str] = set()
    burger_present = False
    for r in rules:
        if r.get("media") or _STATE_PSEUDO_RE.search(r.get("selector") or ""):
            continue
        sel = r.get("selector") or ""
        decls = r.get("decls", "")
        if _HIDE_DISPLAY_RE.search(decls):
            base_hidden.add(sel)
        if _BURGER_RE.search(sel) and _decl(decls, "display") \
                and not _HIDE_DISPLAY_RE.search(decls):
            burger_present = True

    burger_hide_bps: list[int] = []   # widths where the mobile-only burger hides
    row_show_bps: list[int] = []      # widths where a base-hidden desktop row shows
    for r in rules:
        media = r.get("media") or ""
        mw = _min_width(media)
        if not mw:
            continue
        sel = r.get("selector") or ""
        decls = r.get("decls", "")
        if _STATE_PSEUDO_RE.search(sel):
            continue
        if _BURGER_RE.search(sel) and _HIDE_DISPLAY_RE.search(decls):
            burger_hide_bps.append(mw)
        if _NAV_ROW_RE.search(sel) and _SHOW_DISPLAY_RE.search(decls) \
                and sel in base_hidden:
            row_show_bps.append(mw)

    # the collapse breakpoint: the definitive "desktop engages here" line. Prefer the
    # width where the mobile-only burger is hidden; else where the base-hidden desktop
    # rows turn visible. Among candidates take the most common (mode), tie → the widest.
    def _pick(bps: list[int]) -> int | None:
        if not bps:
            return None
        counts: dict[int, int] = {}
        for b in bps:
            counts[b] = counts.get(b, 0) + 1
        top = max(counts.values())
        return max(b for b, c in counts.items() if c == top)

    breakpoint = _pick(burger_hide_bps) or _pick(row_show_bps)
    # a genuine collapse needs both a breakpoint AND the rows that disappear below it;
    # a burger is the mobile trigger. Emit only when the mechanic is real (fact-gate):
    # a breakpoint from the row-show/burger-hide evidence, and at least one of a burger
    # control or a base-hidden desktop row that reappears at the breakpoint.
    if not breakpoint or not (burger_present or row_show_bps):
        return None
    return {"breakpoint": int(breakpoint),
            "burger": bool(burger_present),
            "_bpSource": "burger-hide" if burger_hide_bps else "row-show"}


def nav_responsive_from_evidence(nav: dict) -> dict | None:
    """Generic nav ``responsive`` fact: the mega-panel ``panelSurface`` (measured panel
    container background) + the mobile ``collapse`` mechanic (measured breakpoint +
    burger presence). None when the nav carries neither (fact-gate)."""
    if not isinstance(nav, dict):
        return None
    surf = _nav_panel_surface_from_evidence(nav)
    collapse = _nav_collapse_from_evidence(nav)
    if not surf and not collapse:
        return None
    out: dict = {"schema": SCHEMA}
    prov: dict = {"origin": "extracted",
                  "source": nav.get("elementId") or nav.get("domSelector")}
    if surf:
        panel, sel, bg = surf
        out["panelSurface"] = panel
        prov["panelSurface"] = (
            f"mega-nav panel container ({sel[:48]}) paints {bg[:32]}"
            f" → resolved {panel['background']}; our .cs-mega measured transparent")
    if collapse:
        bp_src = collapse.pop("_bpSource", "")
        out["collapse"] = collapse
        prov["collapse"] = (
            f"source nav rows are mobile-first (display:none at base, display:flex only "
            f"in @media(width >= {collapse['breakpoint']}px)); a burger control shows "
            f"below the breakpoint and hides at/above it. Below {collapse['breakpoint']}"
            f"px the desktop utility + primary rows collapse to a logo + burger mobile "
            f"bar (breakpoint from {bp_src or 'measured @media'}).")
    out["provenance"] = prov
    return out


# ── HERO primary-button fact (geometry + motion purge) ───────────────────────────────
#
# The harness flags the hero primary button on several static properties (font-size
# 14→18, line-height, border, width) AND an INVENTED hover ``transform: translateY(-1px)``
# the source never had. The geometry rows are missing measured facts; the transform is an
# un-grounded composer default (the provenance doctrine, extended to MOTION). This derives
# the measured button geometry and a motion-purge flag from the source primary button.

def _find_source_hero_button(els: dict) -> dict | None:
    prefer = None
    for e in els.values():
        if e.get("kind") != "action":
            continue
        cls = e.get("classes") or ""
        if e.get("visionRole") == "hero" and "-primary" in cls:
            return e
        if "-primary" in cls and "cl-button" in cls and prefer is None \
                and "nav" not in cls:
            prefer = e
    return prefer


def _button_has_hover_transform(btn: dict) -> bool:
    """True when the source button declares a real hover/focus transform (so ours is
    grounded); False when every state rule swaps bg/border/color only (our translateY
    lift is un-grounded and must be purged)."""
    for r in btn.get("cssRules") or []:
        ps = r.get("pseudo") or []
        sel = (r.get("selector") or "")
        is_state = any(p.strip(":") in ("hover", "focus", "focus-visible",
                                        "focus-within") for p in ps) \
            or _STATE_PSEUDO_RE.search(sel)
        if not is_state:
            continue
        t = _decl(r.get("decls", ""), "transform")
        if t and t.strip().lower() not in ("none", ""):
            return True
    return False


def hero_button_from_evidence(btn: dict) -> tuple[dict | None, bool]:
    """(primaryButton geometry block | None, purgeHoverTransform bool) from the source
    hero primary button's measured @1440 matrix + its bound state rules."""
    if not isinstance(btn, dict):
        return None, False
    rec = ((btn.get("computedLadder") or {}).get("1440") or {}).get("measured") or {}
    keep = {}
    fs = str(rec.get("font-size") or "").strip()
    lh = str(rec.get("line-height") or "").strip()
    disp = str(rec.get("display") or "").strip()
    border = str(rec.get("border") or "").strip()
    pad = str(rec.get("padding") or "").strip()
    if fs:
        keep["fontSize"] = fs
    if lh and lh.lower() != "normal":
        keep["lineHeight"] = lh
    if disp:
        keep["display"] = disp
    if pad:
        keep["padding"] = pad
    # a transparent measured border still RESERVES layout width — carry it as a
    # transparent border (generic, colour-agnostic) so the button's box matches.
    m = re.match(r"(\d*\.?\d+)px\s+(solid|dashed|dotted)\b", border)
    if m:
        from_alpha = re.search(r"rgba?\([^)]*,\s*0(?:\.0+)?\s*\)$", border)
        keep["border"] = (f"{m.group(1)}px {m.group(2)} transparent"
                          if from_alpha else border)
    purge = not _button_has_hover_transform(btn)
    if not keep and not purge:
        return None, False
    block = {"schema": SCHEMA}
    if keep:
        block.update(keep)
    if purge:
        block["motionPurge"] = {"hoverTransform": True}
    block["provenance"] = {
        "origin": "extracted",
        "source": btn.get("elementId"),
        "geometry": ("primary action measured @1440 (display/font-size/line-height/"
                     "border/padding) — the button box the composer left un-grounded"),
        "motionPurge": ("source hover/focus rules swap bg/border/color only, no "
                        "transform; composer translateY lift is un-grounded motion")
        if purge else None,
    }
    if block["provenance"].get("motionPurge") is None:
        block["provenance"].pop("motionPurge")
    return block, purge


# ── HEADING line-height fact ──────────────────────────────────────────────────────────
#
# The harness flags heading line-heights the composer's type scale mis-derives (h2
# 23.4px vs measured 28px). These are measured type facts, not scaffold ratios — carried
# per generic heading tag (h1/h2/…, not section/content names).

def heading_line_heights_from_evidence(els: dict) -> dict | None:
    out: dict = {}
    prov_src: list[str] = []
    for tag in ("h1", "h2", "h3"):
        h = els.get(f"heading-{tag}")
        if not isinstance(h, dict):
            continue
        ladder = h.get("computedLadder") or {}
        lhs = {str((rec or {}).get("line-height") or "").strip()
               for rec in ladder.values() if isinstance(rec, dict)}
        lhs = {v for v in lhs if v and v.lower() != "normal"}
        if len(lhs) == 1:  # a single measured line-height (stable across the ladder)
            out[tag] = next(iter(lhs))
            prov_src.append(f"heading-{tag}")
    if not out:
        return None
    return {
        "schema": SCHEMA,
        "lineHeights": out,
        "provenance": {
            "origin": "extracted",
            "source": ",".join(prov_src),
            "lineHeights": ("measured heading computedLadder line-heights (stable "
                            "across the viewport ladder) the composer type scale "
                            "mis-derived"),
        },
    }


# ── sidecar build + merge-at-load ──────────────────────────────────────────────────

SIDECAR_NAME = "responsive-facts.yaml"


def build_sidecar(joined: dict, footer_measured: dict | None = None) -> dict:
    """The responsive/measured-fact sidecar derived from joined-evidence, spanning the
    hero, footer, nav mega-panel, hero primary button, and heading line-heights. Empty
    dict when no component carries a measured fact the composer left un-grounded.

    Every block is GENERIC (reusable surface/typography/control roles, never a section-
    or content-specific name) and provenance-tagged; each emitter is fact-gated so a
    brand without a block renders byte-for-byte as before."""
    els = _by_id(joined)
    out: dict = {}
    hero_el = _find_source_hero(els)
    hero_block = hero_responsive_from_evidence(hero_el) if hero_el else None
    # hero primary-button geometry + hover-transform purge fold into the hero block
    # (its emitter is scoped to the hero section) plus a doc-level purge flag (the
    # button hover rule is brand-wide, so the purge is brand-wide when grounded).
    btn_el = _find_source_hero_button(els)
    btn_block, purge = hero_button_from_evidence(btn_el) if btn_el else (None, False)
    if btn_block:
        hero_block = hero_block or {"schema": SCHEMA,
                                    "provenance": {"origin": "extracted"}}
        hero_block["primaryButton"] = btn_block
    if hero_block:
        out["hero"] = hero_block
    if purge:
        out["buttons"] = {
            "schema": SCHEMA, "purgeHoverTransform": True,
            "provenance": {
                "origin": "extracted",
                "source": (btn_el or {}).get("elementId"),
                "purgeHoverTransform": (
                    "source button hover/focus rules declare no transform (bg/border/"
                    "color swap only); the composer translateY(-1px) lift is "
                    "un-grounded motion — purged brand-wide (provenance doctrine)"),
            },
        }
    footer_el = els.get("chrome-footer")
    footer_block = (footer_responsive_from_evidence(footer_el, footer_measured or {})
                    if footer_el else None)
    if footer_block:
        out["footer"] = footer_block
    nav_el = els.get("chrome-header")
    nav_block = nav_responsive_from_evidence(nav_el) if nav_el else None
    if nav_block:
        out["nav"] = nav_block
    heading_block = heading_line_heights_from_evidence(els)
    if heading_block:
        out["headings"] = heading_block
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
    # nav mega-panel surface, brand-wide button motion-purge, and heading line-heights
    # merge onto the doc under a single ``responsive`` namespace (in-memory only). Each
    # consumer is fact-gated; a brand without the sidecar leaves the doc untouched.
    resp = doc.get("responsive") if isinstance(doc.get("responsive"), dict) else {}
    for key in ("nav", "buttons", "headings"):
        block = sidecar.get(key)
        if isinstance(block, dict) and key not in resp:
            resp[key] = block
    if resp:
        doc.setdefault("responsive", resp)
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
    report = {k: bool(sidecar.get(k))
              for k in ("hero", "footer", "nav", "buttons", "headings")}
    print(f"[responsive] {brand_dir.parent.name}: wrote {out_p.name} {json.dumps(report)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
