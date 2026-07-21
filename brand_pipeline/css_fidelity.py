#!/usr/bin/env python3
"""css_fidelity.py — Phase 1b COMPUTED-CSS PROPERTY-DIFF HARNESS (measurement only).

The SSIM replica gate (``compose_replica.py``) diffs SCREENSHOTS. It catches gross
layout drift but is nearly blind to per-property divergences: a button that lifts on
hover (``transform: translateY(-1px)``) the source never had, a hero rendered at a
fixed ``band`` px height instead of the source's ``calc(100dvh - navheight)``, a
mega-nav panel with no background, a footer whose columns never reflow while the
source has ``@media(>=900){column-count:2}``.

This harness surfaces those divergences by construction. For every matched component
(hero / nav / footer / buttons / cards / sections / headings) it compares OUR rendered
replica's COMPUTED styles to the SOURCE's — per property, across the 1920/1440/960/375
viewport ladder — and emits a RANKED divergence report.

Two evidence channels, symmetric on both sides:
  * STATIC properties (font-size, background, padding, border-radius, …) come from
    COMPUTED styles: ours measured live per viewport (reusing measure_computed's
    Playwright engine); the source's from Phase 1's ``joined-evidence.json``
    ``computedLadder`` (already measured on the real page).
  * BEHAVIORAL facts that a static computed snapshot cannot see (hover ``transform``,
    viewport-relative ``calc`` height, ``@media`` column reflow, panel backgrounds)
    come from BOUND CSS RULES: the source's from ``joined-evidence.json`` ``cssRules``;
    ours from an in-browser stylesheet scan bound to each probe element the same way.

This is a VERIFICATION / measurement tool. It renders OUR replica through the REAL
composer (``compose_replica.build_replica_page``, imported unmodified) into an isolated
sub-dir so the SSIM gate's artifacts are never touched, and it changes NOTHING in the
renderer / composer / author / replica gate. Divergences are the driver for later
phases (responsive schema, purge of un-grounded defaults); this tool only reports them.

Usage:
    env -u PLAYWRIGHT_BROWSERS_PATH ./venv/bin/python brand_pipeline/css_fidelity.py \
        runs/<brand>/brand/brand.yaml [-o runs/<brand>/brand/compose/replica] \
        [--viewports 1920,1440,960,375] [--skip-compose]

Emits ``<out>/css-diff.json`` + ``<out>/css-diff.md`` (ranked table).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

REPO_ROOT = _HERE.parent

SCHEMA = "css-diff.v1"

# viewport ladder: 1440 is primary (where source section rects + button samples live);
# 375/960/1920 surface RESPONSIVE divergences (footer columns, hero height, type ladder).
DEFAULT_VIEWPORTS = (1920, 1440, 960, 375)
PRIMARY_VIEWPORT = "1440"
_VP_HEIGHT = {1920: 1080, 1440: 900, 960: 720, 375: 812}

# ── curated, load-bearing property set (union read on OUR side per probe) ─────────
LAYOUT_PROPS = [
    "display", "height", "min-height", "width", "max-width", "padding", "margin",
    "grid-template-columns", "grid-template-rows", "column-count", "columns",
    "flex-direction", "align-items", "justify-content", "flex-wrap", "gap",
    "container-type",
]
MOTION_PROPS = ["transform", "transition"]
SURFACE_PROPS = ["background-color", "background-image", "border", "border-radius",
                 "box-shadow"]
TYPE_PROPS = ["font-size", "font-weight", "line-height", "letter-spacing",
              "text-transform", "color", "font-family"]
ALL_PROPS = LAYOUT_PROPS + MOTION_PROPS + SURFACE_PROPS + TYPE_PROPS

# severity per property (behavioral detectors override with their own severity)
SEVERITY_BY_PROP = {
    "transform": "high", "transition": "medium",
    "background-color": "high", "background-image": "high", "border": "medium",
    "box-shadow": "medium", "border-radius": "medium",
    "height": "high", "min-height": "high", "display": "high", "max-width": "high",
    "grid-template-columns": "high", "grid-template-rows": "medium",
    "column-count": "high", "columns": "high",
    "flex-direction": "medium", "align-items": "medium", "justify-content": "medium",
    "flex-wrap": "medium", "gap": "medium", "container-type": "medium",
    "padding": "medium", "margin": "low", "width": "medium",
    "font-size": "high", "font-weight": "medium", "line-height": "medium",
    "letter-spacing": "low", "text-transform": "medium", "color": "medium",
    "font-family": "low",
}
SEVERITY_WEIGHT = {"critical": 4, "high": 3, "medium": 2, "low": 1}

# values that read as "no value" for the invented-default / missing-fact classifier
_EMPTY_VALUES = {"", "none", "normal", "auto", "transparent", "rgba(0, 0, 0, 0)",
                 "rgba(0,0,0,0)", "0s", "0s ease 0s", "initial", "unset"}

_VP_UNIT_RE = re.compile(r"\b\d*\.?\d+(?:dvh|svh|lvh|vh|dvw|vw)\b")
_STATE_PSEUDO_RE = re.compile(
    r"::?(?:hover|focus-visible|focus-within|focus|active|visited|target|checked)\b")
_PSEUDO_RE = re.compile(r"::?[a-zA-Z][a-zA-Z-]*(?:\([^)]*\))?")
_LAYOUT_REFLOW_RE = re.compile(
    r"(column-count|columns\s*:|grid-template|grid-auto|flex-direction|flex-wrap"
    r"|display\s*:\s*(?:grid|flex|inline-flex|inline-block|none|block))")
# a mega-nav PANEL CONTAINER surface (the flyout/dropdown sheet), NOT its child parts
_PANEL_CONTAINER_RE = re.compile(
    r"flyout|dropdown|submenu|nav-tab-dropdown|nav-main-inner|burger-menu"
    r"|mega(?!-(?:card|link|item|rail|icon|title|body|cta|head|group|chev|desc"
    r"|aside|toggle|button|arrow|badge|img|image|list|main))", re.I)
_PANEL_PART_RE = re.compile(
    r"card|link|item|rail|icon|title|body|cta|head|group|chev|desc|aside|toggle"
    r"|button|arrow|badge|img|image|-list", re.I)


# ── value normalization ─────────────────────────────────────────────────────────

def _norm(value) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _norm_color(value: str) -> str:
    """rgb(a,b,c) ≡ rgba(a,b,c,1); lowercase + whitespace-collapsed."""
    v = _norm(value).lower()
    m = re.match(r"rgb\(\s*([\d.]+)[ ,]+([\d.]+)[ ,]+([\d.]+)\s*\)$", v)
    if m:
        return f"rgba({m.group(1)}, {m.group(2)}, {m.group(3)}, 1)"
    m = re.match(r"rgba\(\s*([\d.]+)[ ,]+([\d.]+)[ ,]+([\d.]+)[ ,/]+([\d.]+)\s*\)$", v)
    if m:
        return f"rgba({m.group(1)}, {m.group(2)}, {m.group(3)}, {m.group(4)})"
    return v


def _color_tuple(value: str):
    m = re.match(r"rgba?\(\s*([\d.]+)[ ,]+([\d.]+)[ ,]+([\d.]+)(?:[ ,/]+([\d.]+))?\s*\)$",
                 _norm(value).lower())
    if not m:
        return None
    a = float(m.group(4)) if m.group(4) is not None else 1.0
    return (float(m.group(1)), float(m.group(2)), float(m.group(3)), a)


def _values_equal(prop: str, ours: str, source: str) -> bool:
    if prop in ("background-color", "color", "border-color"):
        co, cs = _color_tuple(ours), _color_tuple(source)
        if co and cs:
            # tolerate imperceptible channel drift (255 vs 252), but a transparent-vs-
            # solid gap (alpha mismatch) is the "missing surface" bug — keep it.
            return (all(abs(a - b) <= 6 for a, b in zip(co[:3], cs[:3]))
                    and abs(co[3] - cs[3]) <= 0.1)
        return _norm_color(ours) == _norm_color(source)
    o, s = _norm(ours).lower(), _norm(source).lower()
    if o == s:
        return True
    # font-family: compare first declared family (stack order / quoting differs)
    if prop == "font-family":
        first = lambda v: v.split(",")[0].strip().strip("\"'")
        return first(o) == first(s)
    # single-length px values: tolerate sub-pixel rounding (95.2px ≡ 95px)
    mo = re.fullmatch(r"(-?[\d.]+)px", o)
    ms = re.fullmatch(r"(-?[\d.]+)px", s)
    if mo and ms:
        return abs(float(mo.group(1)) - float(ms.group(1))) <= 1.0
    return False


def _is_empty(value: str) -> bool:
    v = _norm(value).lower()
    return v in _EMPTY_VALUES or v == ""


def classify_cause(ours: str, source: str) -> str:
    """invented-default: ours paints something the source doesn't; missing-fact: the
    source carries a value we dropped; wrong-value: both present but different."""
    o_empty, s_empty = _is_empty(ours), _is_empty(source)
    if s_empty and not o_empty:
        return "invented-default"
    if o_empty and not s_empty:
        return "missing-fact"
    return "wrong-value"


# ── bound-rule helpers (shared by both sides) ─────────────────────────────────────

def _rule_pseudos(rule: dict) -> list[str]:
    pseudos = rule.get("pseudo")
    if pseudos:
        return [p.lstrip(":") for p in pseudos]
    return [p.lstrip(":") for p in _PSEUDO_RE.findall(rule.get("selector") or "")]


def _decl(decls: str, prop: str) -> str | None:
    """Last declaration of ``prop`` in a decl block (later wins within a rule)."""
    found = None
    for m in re.finditer(r"(?:^|;)\s*" + re.escape(prop) + r"\s*:\s*([^;]+)", decls or ""):
        found = m.group(1).strip()
    return found


def hover_transform(bound_rules: list[dict]) -> str:
    """The transform declared under a hover/focus state (motion the resting snapshot
    can't show). ``none`` when no state rule declares a transform."""
    for r in bound_rules:
        ps = _rule_pseudos(r)
        if any(p in ("hover", "focus", "focus-visible", "focus-within") for p in ps):
            t = _decl(r.get("decls", ""), "transform")
            if t and _norm(t).lower() != "none":
                return _norm(t)
    return "none"


def viewport_relative_height(bound_rules: list[dict],
                             custom_props: dict | None = None) -> str | None:
    """The height mechanic when it is VIEWPORT-RELATIVE (calc()/vh/dvh). ``None``
    when every height fact is a fixed length — the divergence the hero exposes."""
    for r in bound_rules:
        d = r.get("decls", "")
        for m in re.finditer(
                r"((?:min-|max-)?height|--[\w-]*height[\w-]*)\s*:\s*([^;]+)", d):
            val = m.group(2).strip()
            if _VP_UNIT_RE.search(val):
                return val
    for name, entries in (custom_props or {}).items():
        if "height" in name.lower():
            for e in entries:
                if _VP_UNIT_RE.search(e.get("value", "")):
                    return e["value"].strip()
    return None


def vp_height_signature(value: str) -> str:
    """Canonical MECHANIC of a viewport-relative height, so two independently authored
    design systems compare like-for-like (our generic ``var(--c-hero-nav-offset)`` vs the
    source's ``var(--global-nav-header-height)`` are the SAME mechanic; requiring
    byte-identical var names across two systems is not a fidelity signal). The mechanic
    stays meaningful: a bare ``100dvh`` and ``calc(100dvh - var(nav))`` still differ, so
    a hero that fills the viewport but DROPS the nav subtraction is still flagged."""
    v = _norm(value).lower()
    if re.search(r"calc\(\s*\d*\.?\d*(?:dvh|svh|lvh|vh)\s*-\s*var\(", v):
        return "viewport-minus-var"
    if re.search(r"calc\(\s*\d*\.?\d*(?:dvh|svh|lvh|vh)\s*-\s*\d", v):
        return "viewport-minus-length"
    if _VP_UNIT_RE.search(v):
        return "viewport"
    return v


def responsive_layout_rules(bound_rules: list[dict]) -> list[dict]:
    """@media rules that RE-FLOW layout (column-count/grid/flex/display). The count
    is the footer's responsiveness signal."""
    out = []
    for r in bound_rules:
        if r.get("media") and _LAYOUT_REFLOW_RE.search(r.get("decls", "")):
            out.append(r)
    return out


def panel_background_rules(bound_rules: list[dict]) -> list[dict]:
    """Rules painting a mega-nav PANEL CONTAINER surface (the flyout/dropdown sheet)
    with a non-empty background. Child parts (cards/links/items) and transient
    hover/focus washes are excluded — the divergence is the panel SHEET itself, which
    our render leaves transparent (``.cs-mega`` = ``rgba(0,0,0,0)``) while the source
    dropdown wrapper is solid."""
    out = []
    for r in bound_rules:
        sel = r.get("selector", "")
        if not _PANEL_CONTAINER_RE.search(sel):
            continue
        if _PANEL_PART_RE.search(sel) or _STATE_PSEUDO_RE.search(sel):
            continue
        bg = _decl(r.get("decls", ""), "background") or \
            _decl(r.get("decls", ""), "background-color")
        if bg and not _is_empty(bg):
            out.append(r)
    return out


# ── SOURCE side: bundles from joined-evidence.json ────────────────────────────────

def load_joined(brand_dir: Path) -> dict:
    p = brand_dir / "evidence" / "joined-evidence.json"
    if not p.is_file():
        raise SystemExit(f"css_fidelity: {p} missing — run Phase 1 join_evidence first")
    return json.loads(p.read_text())


def _by_id(doc: dict) -> dict:
    return {e["elementId"]: e for e in doc.get("elements", [])}


def _find_source_hero(els: dict) -> dict | None:
    for e in els.values():
        if e.get("kind") == "section" and e.get("visionRole") == "hero":
            return e
    return els.get("section-00")


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


def _source_props_for(el: dict) -> dict[str, dict]:
    """byViewport {vp: {prop: value}} extracted from the element's computedLadder.
    Shape depends on kind (headings carry a full per-tier type ladder; actions a
    single 1440 button matrix; sections/chrome a surface + rect)."""
    ladder = el.get("computedLadder") or {}
    kind = el.get("kind")
    by_vp: dict[str, dict] = {}
    if kind == "heading":
        for tier, rec in ladder.items():
            if isinstance(rec, dict):
                by_vp[tier] = {k: v for k, v in rec.items()
                               if k in TYPE_PROPS and v is not None}
    elif kind == "action":
        rec = (ladder.get(PRIMARY_VIEWPORT) or {}).get("measured") or {}
        by_vp[PRIMARY_VIEWPORT] = {k: v for k, v in rec.items()
                                   if k in ALL_PROPS and v is not None}
    elif kind == "chrome":
        for tier, rec in ladder.items():
            if not isinstance(rec, dict):
                continue
            surf = rec.get("surface") or {}
            vals = {k: v for k, v in surf.items() if k in ALL_PROPS and v is not None}
            if surf.get("_rect"):
                vals.setdefault("height", f"{round(surf['_rect'].get('h', 0))}px")
            if vals:
                by_vp[tier] = vals
    else:  # section — compare the OUTER band surface only (background-color).
        # max-width / padding live on the INNER content wrapper (containerFacts),
        # a different element than our probed outer <section>; comparing them would be
        # apples-to-oranges, so the outer-band diff is limited to the band surface.
        for tier, rec in ladder.items():
            if not isinstance(rec, dict):
                continue
            if rec.get("backgroundColor"):
                by_vp[tier] = {"background-color": rec["backgroundColor"]}
    return by_vp


def _source_bundle(el: dict, role: str) -> dict:
    return {
        "role": role,
        "key": el.get("elementId"),
        "selector": el.get("domSelector"),
        "classes": el.get("classes"),
        "byViewport": _source_props_for(el),
        "boundRules": el.get("cssRules") or [],
        "customProperties": el.get("customProperties") or {},
    }


def source_bundles(doc: dict, max_sections: int = 10) -> dict[str, dict]:
    els = _by_id(doc)
    bundles: dict[str, dict] = {}
    hero = _find_source_hero(els)
    if hero:
        bundles["hero"] = _source_bundle(hero, "hero")
    nav = els.get("chrome-header")
    if nav:
        bundles["nav"] = _source_bundle(nav, "nav")
    footer = els.get("chrome-footer")
    if footer:
        bundles["footer"] = _source_bundle(footer, "footer")
    btn = _find_source_hero_button(els)
    if btn:
        bundles["button-primary"] = _source_bundle(btn, "button-primary")
    for tag in ("h1", "h2"):
        h = els.get(f"heading-{tag}")
        if h and h.get("byViewport") is not None or (h and h.get("computedLadder")):
            bundles[f"heading-{tag}"] = _source_bundle(h, f"heading-{tag}")
    # content sections by index (skip 0 — covered by the hero role)
    for e in doc.get("elements", []):
        if e.get("kind") != "section":
            continue
        m = re.match(r"section-(\d+)", e.get("elementId") or "")
        if not m:
            continue
        idx = int(m.group(1))
        if idx == 0 or idx > max_sections:
            continue
        bundles[f"section-{idx}"] = _source_bundle(e, f"section-{idx}")
    return bundles


# ── HEADING-TIER AUDIT: authored type scale vs CSS-VARIABLE truth ─────────────────
# The SSIM gate and the per-property replica diff both compare RENDERED output; neither
# catches an authored type-scale that COLLAPSED at authoring time (h2 authored 18px when
# the source's --cl-font-size-h2 declares 40px) — because the collapsed token renders
# self-consistently. This audit closes that hole by construction: it diffs the authored
# brand.yaml heading tiers against the CSS-variable-first type-scale truth
# (evidence/type-scale.json, produced by tools/extract/type_scale.py). It is
# brand-agnostic — it reads whatever heading roles the truth carries.

_HEADING_TIER_ROLES = ("h1", "h2", "h3", "h4", "h5", "h6", "body")
_ROOT_PX = 16.0


def load_type_scale_truth(brand_dir: Path) -> dict | None:
    p = brand_dir / "evidence" / "type-scale.json"
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text())
    except (ValueError, OSError):
        return None


def _authored_type(brand_yaml: Path) -> dict:
    import yaml
    doc = yaml.safe_load(brand_yaml.read_text()) or {}
    return ((doc.get("tokens") or {}).get("type") or {})


def _authored_tier_px(node: dict) -> float | None:
    """The authored canonical (1440) font-size px of a flat type role: the w1440 tier
    stamp if present, else sizeRem.base × root."""
    if not isinstance(node, dict):
        return None
    tiers = node.get("tiers") if isinstance(node.get("tiers"), dict) else {}
    w1440 = tiers.get("w1440") or tiers.get(f"w{int(PRIMARY_VIEWPORT)}")
    if isinstance(w1440, dict) and w1440.get("px") is not None:
        try:
            return float(w1440["px"])
        except (TypeError, ValueError):
            pass
    size = node.get("sizeRem")
    base = size.get("base") if isinstance(size, dict) else size
    try:
        return round(float(base) * _ROOT_PX, 2) if base is not None else None
    except (TypeError, ValueError):
        return None


def _lh_ratio(value) -> float | None:
    """Normalize a line-height (unitless / '1.15em' / px vs a size) to a bare ratio."""
    if value is None:
        return None
    m = re.match(r"^\s*(-?\d*\.?\d+)\s*(em|)?\s*$", str(value))
    if m:
        return round(float(m.group(1)), 3)
    return None


def heading_tier_divergences(authored_type: dict, truth: dict) -> list[dict]:
    """Per-heading-tier divergences of the AUTHORED scale vs the CSS-variable truth.
    font-size divergence is HIGH (this is the collapse bug); line-height MEDIUM."""
    divs: list[dict] = []
    roles = (truth or {}).get("canonicalRoles") or {}
    for tag in _HEADING_TIER_ROLES:
        css = roles.get(tag)
        css_px = (css or {}).get("sizePx")
        if css_px is None:
            continue
        role = f"heading-{tag}"
        node = authored_type.get(tag)
        if not isinstance(node, dict):
            divs.append(_mk_div(role, "font-size", "(role absent)", f"{css_px}px",
                                PRIMARY_VIEWPORT, "high", "missing-fact",
                                kind="type-scale"))
            continue
        a_px = _authored_tier_px(node)
        if a_px is not None and abs(a_px - float(css_px)) > 1.5:
            divs.append(_mk_div(role, "font-size", f"{a_px}px", f"{css_px}px",
                                PRIMARY_VIEWPORT, "high", "wrong-value",
                                kind="type-scale"))
        a_lh = _lh_ratio(node.get("lineHeight"))
        c_lh = _lh_ratio((css or {}).get("lineHeight"))
        if a_lh is not None and c_lh is not None and abs(a_lh - c_lh) > 0.06:
            divs.append(_mk_div(role, "line-height", str(a_lh), str(c_lh),
                                PRIMARY_VIEWPORT, "medium", "wrong-value",
                                kind="type-scale"))
    return divs


# ── OUR side: compose the replica + measure computed styles per viewport ──────────

# Probes: role -> {selector, prefer descendant of, kind}. Selectors are OUR composer's
# generic classes/ids, matched by ROLE not by source class names.
def _our_probes(section_count: int) -> list[dict]:
    probes = [
        {"role": "nav", "selector": "#page-nav"},
        {"role": "footer", "selector": ".c-footer"},
        {"role": "hero", "selector": "#sec-0"},
        {"role": "button-primary",
         "selector": "#sec-0 .c-button:not(.c-button--navcta)"},
    ]
    # HEADING-TIER PROBES: every heading level, not just h1/h2 — so a collapsed or
    # mis-authored heading register (the h2=18px bug) surfaces at the rendered level.
    for tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
        probes.append({"role": f"heading-{tag}", "selector": tag})
    for i in range(1, section_count):
        probes.append({"role": f"section-{i}", "selector": f"#sec-{i}"})
    return probes


_MEASURE_JS = r"""
(args) => {
  const {probes, props} = args;
  const STATE = /::?(hover|focus-visible|focus-within|focus|active|visited|target|checked)\b/g;
  const splitList = (sel) => {
    const parts = []; let buf = '', depth = 0;
    for (const ch of sel) {
      if (ch === '(' || ch === '[') depth++;
      else if (ch === ')' || ch === ']') depth = Math.max(0, depth - 1);
      if (ch === ',' && depth === 0) { parts.push(buf.trim()); buf = ''; }
      else buf += ch;
    }
    if (buf.trim()) parts.push(buf.trim());
    return parts;
  };
  const baseOf = (part) => (part.replace(STATE, '').trim() || '*');
  // flatten every same-origin stylesheet rule, carrying its @media condition
  const flat = [];
  const walk = (rules, media) => {
    for (const r of rules) {
      if (r.type === CSSRule.STYLE_RULE) {
        flat.push({selector: r.selectorText || '', media: media || '',
                   decls: r.style ? r.style.cssText : ''});
      } else if (r.type === CSSRule.MEDIA_RULE) {
        const cond = '@media(' + r.conditionText + ')';
        walk(r.cssRules, media ? media + ' and ' + cond : cond);
      } else if (r.type === CSSRule.SUPPORTS_RULE) {
        walk(r.cssRules, media);
      }
    }
  };
  for (const sheet of document.styleSheets) {
    try { walk(sheet.cssRules, ''); } catch (e) { /* cross-origin font CDN */ }
  }
  const boundRulesFor = (el) => {
    const out = [];
    for (const r of flat) {
      if (!r.selector) continue;
      let matched = null, pseudos = [];
      for (const part of splitList(r.selector)) {
        const base = baseOf(part);
        let hit = false;
        try { hit = el.matches(base); } catch (e) {}
        if (!hit) { try { hit = !!el.querySelector(base); } catch (e) {} }
        if (hit) {
          matched = part;
          pseudos = (part.match(STATE) || []).map(p => p.replace(/:/g, ''));
          break;
        }
      }
      if (matched) out.push({selector: r.selector, media: r.media,
                             decls: r.decls, pseudo: pseudos});
      if (out.length > 500) break;
    }
    return out;
  };
  // the surface color that actually fills a band: many composers paint the band bg
  // on an INNER wrapper (sections/hero) or an ANCESTOR band (footer), not the probed
  // element — so resolve the effective band background to compare like-for-like with
  // the source, which measured the band element that carries the paint.
  const TRANSPARENT = new Set(['rgba(0, 0, 0, 0)', 'transparent', '']);
  const bandBackground = (el) => {
    const own = getComputedStyle(el).backgroundColor;
    if (!TRANSPARENT.has(own)) return own;
    const a = el.getBoundingClientRect();
    const elArea = Math.max(1, a.width * a.height);
    for (const k of el.querySelectorAll(':scope > *, :scope > * > *')) {
      const bg = getComputedStyle(k).backgroundColor;
      if (!TRANSPARENT.has(bg)) {
        const r = k.getBoundingClientRect();
        if (r.width * r.height >= 0.5 * elArea) return bg;
      }
    }
    let p = el.parentElement;
    while (p && p !== document.documentElement) {
      const bg = getComputedStyle(p).backgroundColor;
      if (!TRANSPARENT.has(bg)) return bg;
      p = p.parentElement;
    }
    return own;
  };
  const readProps = (el) => {
    const cs = getComputedStyle(el);
    const o = {};
    for (const p of props) o[p] = cs.getPropertyValue(p);
    o['background-color'] = bandBackground(el);
    const r = el.getBoundingClientRect();
    o.height = Math.round(r.height) + 'px';  // used height (rect) over 'auto'
    return o;
  };
  const result = {};
  for (const probe of probes) {
    let el = null;
    try { el = document.querySelector(probe.selector); } catch (e) {}
    if (!el) { result[probe.role] = {found: false}; continue; }
    const entry = result[probe.role] || {found: true, computed: null, boundRules: null,
                                         selector: probe.selector};
    entry.found = true;
    entry.computed = readProps(el);
    if (!entry.boundRules) entry.boundRules = boundRulesFor(el);  // rules are viewport-stable
    result[probe.role] = entry;
  }
  return result;
}
"""


def measure_our_replica(index_html: Path, probes: list[dict],
                        viewports: tuple[int, ...]) -> dict[str, dict]:
    """Load OUR composed replica and read the curated computed property set for each
    probe at each viewport, plus its bound CSS rules (one scan — rules are viewport-
    stable). Mirrors measure_computed's engine: headless Chromium, JS OFF (static
    CSS, symmetric with how the source ladder was measured)."""
    os.environ.pop("PLAYWRIGHT_BROWSERS_PATH", None)
    from playwright.sync_api import sync_playwright

    by_vp: dict[str, dict] = {}
    bound: dict[str, list] = {}
    found: dict[str, bool] = {}
    selectors: dict[str, str] = {}
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": viewports[0],
                                          "height": _VP_HEIGHT.get(viewports[0], 900)},
                                java_script_enabled=False)
        page.goto(index_html.resolve().as_uri(), wait_until="load", timeout=60000)
        for w in viewports:
            page.set_viewport_size({"width": w, "height": _VP_HEIGHT.get(w, 900)})
            page.wait_for_timeout(60)
            res = page.evaluate(_MEASURE_JS, {"probes": probes, "props": ALL_PROPS})
            for role, data in res.items():
                found[role] = found.get(role, False) or data.get("found", False)
                if not data.get("found"):
                    continue
                selectors.setdefault(role, data.get("selector"))
                by_vp.setdefault(role, {})[str(w)] = data.get("computed") or {}
                if role not in bound and data.get("boundRules") is not None:
                    bound[role] = data["boundRules"]
        browser.close()

    bundles: dict[str, dict] = {}
    for probe in probes:
        role = probe["role"]
        bundles[role] = {
            "role": role,
            "found": found.get(role, False),
            "selector": selectors.get(role, probe["selector"]),
            "byViewport": by_vp.get(role, {}),
            "boundRules": bound.get(role, []),
            "customProperties": {},
        }
    return bundles


def compose_our_replica(brand_yaml: Path, work_dir: Path) -> Path:
    """Compose OUR source-order replica through the REAL machinery (imported,
    unmodified) into an ISOLATED dir so the SSIM gate's compose/replica artifacts
    are never overwritten. Returns the composed index.html path."""
    import compose_replica as cr
    work_dir.mkdir(parents=True, exist_ok=True)
    built = cr.build_replica_page(brand_yaml, work_dir)
    if built.get("errors"):
        for lid, err in built["errors"].items():
            print(f"[css-diff] section compose note: {lid}: {err}")
    return work_dir / "index.html"


# ── diff a matched (ours, source) pair ────────────────────────────────────────────

def _mk_div(role, prop, ours, source, viewport, severity, cause, kind="property"):
    return {"element": role, "property": prop, "ours": _norm(ours),
            "source": _norm(source), "viewport": viewport, "severity": severity,
            "likelyCause": cause, "kind": kind}


def diff_pair(role: str, ours: dict, source: dict) -> list[dict]:
    """All per-property + behavioral divergences for one matched component."""
    divs: list[dict] = []
    if not ours or not ours.get("found"):
        divs.append(_mk_div(role, "*element*", "not-rendered", "present",
                            PRIMARY_VIEWPORT, "high", "missing-fact", kind="match"))
        return divs

    o_vp = ours.get("byViewport") or {}
    s_vp = source.get("byViewport") or {}
    # STATIC per-property diff on every viewport the SOURCE measured that property.
    for vp, s_props in s_vp.items():
        o_props = o_vp.get(vp) or o_vp.get(PRIMARY_VIEWPORT) or {}
        for prop, s_val in s_props.items():
            if prop not in o_props:
                continue
            o_val = o_props[prop]
            if _values_equal(prop, o_val, s_val):
                continue
            if prop == "height" and role in ("hero",) and _norm(o_val) != _norm(s_val):
                # height magnitude for the hero is reported by the height-rule detector
                continue
            divs.append(_mk_div(role, prop, o_val, s_val, vp,
                                SEVERITY_BY_PROP.get(prop, "medium"),
                                classify_cause(o_val, s_val)))

    o_rules = ours.get("boundRules") or []
    s_rules = source.get("boundRules") or []

    # BEHAVIORAL: hover transform (button family). Source hero button has no hover
    # transform; a composer default that lifts on hover is invented motion.
    if role.startswith("button"):
        o_t, s_t = hover_transform(o_rules), hover_transform(s_rules)
        if _norm(o_t).lower() != _norm(s_t).lower():
            divs.append(_mk_div(role, "transform:hover", o_t, s_t, "all",
                                "high", classify_cause(o_t, s_t), kind="behavior"))

    # BEHAVIORAL: hero height mechanic (viewport-relative calc vs fixed px band).
    if role == "hero":
        s_h = viewport_relative_height(s_rules, source.get("customProperties"))
        o_h = viewport_relative_height(o_rules, ours.get("customProperties"))
        if s_h and not o_h:
            fixed = (o_vp.get(PRIMARY_VIEWPORT) or {}).get("height", "fixed px")
            divs.append(_mk_div(role, "height-rule", f"{fixed} (fixed px)", s_h,
                                "all", "critical", "missing-fact", kind="behavior"))
        elif s_h and o_h and vp_height_signature(o_h) != vp_height_signature(s_h):
            # both viewport-relative but a DIFFERENT mechanic (e.g. bare 100dvh vs the
            # source's viewport-minus-nav) — still a real divergence.
            divs.append(_mk_div(role, "height-rule", o_h, s_h, "all",
                                "high", "wrong-value", kind="behavior"))

    # BEHAVIORAL: footer responsive column reflow (@media column-count / grid).
    if role == "footer":
        s_re = responsive_layout_rules(s_rules)
        o_re = responsive_layout_rules(o_rules)
        if s_re and not o_re:
            sample = "; ".join(sorted({r["media"] for r in s_re}))[:80]
            divs.append(_mk_div(
                role, "responsive-columns",
                "no @media layout reflow", f"{len(s_re)} @media reflow rules ({sample})",
                "all", "critical", "missing-fact", kind="behavior"))
        # cross-check via computed grid across the ladder (non-responsive columns)
        cols = {vp: (o_vp.get(vp) or {}).get("grid-template-columns")
                for vp in o_vp}
        distinct = {_norm(v) for v in cols.values() if v and _norm(v).lower() != "none"}
        if s_re and len(distinct) <= 1 and distinct:
            divs.append(_mk_div(
                role, "grid-template-columns", f"constant {next(iter(distinct))[:48]}",
                "source reflows across breakpoints", "all", "high",
                "missing-fact", kind="behavior"))

    # BEHAVIORAL: nav mega-panel backgrounds (source paints panels; ours omits them).
    if role == "nav":
        s_bg = panel_background_rules(s_rules)
        o_bg = panel_background_rules(o_rules)
        if s_bg and not o_bg:
            divs.append(_mk_div(
                role, "panel-background",
                "no mega-nav panel surfaces rendered",
                f"{len(s_bg)} panel background rules", "all", "critical",
                "missing-fact", kind="behavior"))
    return divs


# ── matching + ranking ────────────────────────────────────────────────────────────

def match_and_diff(our_bundles: dict, src_bundles: dict) -> tuple[list[dict], list[dict]]:
    """Pair OUR components to SOURCE components by ROLE (hero↔hero, nav↔chrome-header,
    footer↔chrome-footer, button family, headings, sections-by-index), then diff each
    pair. Returns (divergences, matchTable)."""
    divs: list[dict] = []
    matches: list[dict] = []
    for role, src in src_bundles.items():
        ours = our_bundles.get(role)
        matched = bool(ours and ours.get("found"))
        matches.append({
            "role": role, "sourceKey": src.get("key"),
            "sourceSelector": src.get("selector"),
            "ourSelector": (ours or {}).get("selector"),
            "matched": matched,
        })
        if ours is None:
            continue
        divs.extend(diff_pair(role, ours, src))
    return divs, matches


def rank(divs: list[dict]) -> list[dict]:
    """RANK by severity × frequency: frequency is how often a (role, property) pair
    diverges across the whole report (a divergence hitting every viewport, or a
    behavior source-count, outranks a one-off)."""
    freq: dict[tuple, int] = {}
    for d in divs:
        freq[(d["element"], d["property"])] = freq.get((d["element"], d["property"]), 0) + 1
    for d in divs:
        f = freq[(d["element"], d["property"])]
        w = SEVERITY_WEIGHT.get(d["severity"], 1)
        d["frequency"] = f
        d["rankScore"] = round(w * (1 + math.log2(f)), 3)
    # severity tier dominates (a lone critical must outrank a frequent medium), then
    # the severity×frequency score orders within the tier.
    order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    return sorted(divs, key=lambda d: (order.get(d["severity"], 9), -d["rankScore"],
                                       d["element"], d["property"]))


# ── acceptance: the 4 known hubspot-v3 divergences (found / not-found) ─────────────

def acceptance(divs: list[dict]) -> dict:
    def has(role, prop_sub, cause=None):
        for d in divs:
            if d["element"] == role and prop_sub in d["property"]:
                if cause is None or d["likelyCause"] == cause:
                    return d
        return None

    checks = {
        "button_hover_transform": has("button-primary", "transform:hover"),
        "hero_height_calc_vs_px": has("hero", "height-rule"),
        "nav_panel_background": has("nav", "panel-background"),
        "footer_responsive_columns": (has("footer", "responsive-columns")
                                      or has("footer", "grid-template-columns")),
    }
    return {k: {"found": v is not None, "divergence": v} for k, v in checks.items()}


# ── emit ────────────────────────────────────────────────────────────────────────

def build_docs(brand: str, divs: list[dict], matches: list[dict], acc: dict,
               meta: dict) -> tuple[dict, str]:
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for d in divs:
        counts[d["severity"]] = counts.get(d["severity"], 0) + 1
    doc = {
        "schemaVersion": SCHEMA,
        "brand": brand,
        "viewports": meta.get("viewports"),
        "primaryViewport": PRIMARY_VIEWPORT,
        "replicaIndex": meta.get("replicaIndex"),
        "joinedEvidence": meta.get("joinedEvidence"),
        "totalDivergences": len(divs),
        "severityCounts": counts,
        "acceptance": {k: v["found"] for k, v in acc.items()},
        "headingTierAudit": meta.get("headingTierAudit"),
        "matches": matches,
        "divergences": divs,
    }

    lines = [
        f"# Computed-CSS property-diff — {brand}", "",
        "Per-property divergence of OUR composed replica vs the SOURCE computed styles "
        "+ bound CSS rules, across the viewport ladder. Measurement only — no renderer / "
        "composer / author / SSIM-gate change.", "",
        f"- viewports: `{', '.join(str(v) for v in meta.get('viewports') or [])}` "
        f"(primary {PRIMARY_VIEWPORT})",
        f"- replica: `{meta.get('replicaIndex')}`",
        f"- source: `{meta.get('joinedEvidence')}`",
        f"- **{len(divs)} divergences** — critical {counts['critical']}, "
        f"high {counts['high']}, medium {counts['medium']}, low {counts['low']}", "",
        "## Known hubspot-v3 acceptance divergences", "",
    ]
    labels = {
        "button_hover_transform": "button `translateY(-1px)` hover-transform (source has none)",
        "hero_height_calc_vs_px": "hero height px vs source `calc(100dvh - navheight)`",
        "nav_panel_background": "mega-nav panel missing background",
        "footer_responsive_columns": "footer non-responsive grid vs source `@media` columns",
    }
    for key, label in labels.items():
        mark = "FOUND" if acc[key]["found"] else "NOT FOUND"
        lines.append(f"- [{mark}] {label}")
    # heading-tier audit (authored scale vs CSS-variable truth)
    hta = meta.get("headingTierAudit") or {}
    ht_divs = hta.get("divergences") or []
    lines += ["", "## Heading-tier audit (authored vs CSS-variable truth)", "",
              f"- truth: `{hta.get('source') or '—'}` (method `{hta.get('method') or '—'}`)",
              f"- **{len(ht_divs)} heading-tier divergence(s)** "
              f"— 0 means the authored ladder matches the source's declared font-size tokens"]
    if ht_divs:
        lines += ["", "| tier | property | authored | css-var | severity |",
                  "|---|---|---|---|---|"]
        for d in ht_divs:
            lines.append(f"| {d['element']} | `{d['property']}` | {_md(d['ours'])} | "
                         f"{_md(d['source'])} | {d['severity']} |")
    lines += ["", "## Ranked divergences", "",
              "| # | element | property | severity | cause | viewport | ours | source | rank |",
              "|---|---|---|---|---|---|---|---|---|"]
    for i, d in enumerate(divs[:60], 1):
        lines.append(
            f"| {i} | {d['element']} | `{d['property']}` | {d['severity']} | "
            f"{d['likelyCause']} | {d['viewport']} | {_md(d['ours'])} | "
            f"{_md(d['source'])} | {d['rankScore']} |")
    if len(divs) > 60:
        lines.append(f"\n_(+{len(divs) - 60} more in css-diff.json)_")
    lines += ["", "## Component match table", "",
              "| role | source | our selector | matched |", "|---|---|---|---|"]
    for m in matches:
        lines.append(f"| {m['role']} | `{m['sourceKey']}` | `{m['ourSelector'] or '—'}` | "
                     f"{'yes' if m['matched'] else 'NO'} |")
    lines.append("")
    return doc, "\n".join(lines)


def _md(value: str) -> str:
    v = _norm(value).replace("|", "\\|")
    return (v[:60] + "…") if len(v) > 61 else (v or "—")


# ── driver ────────────────────────────────────────────────────────────────────────

def run(brand_yaml: Path, out_dir: Path, viewports: tuple[int, ...],
        skip_compose: bool = False) -> dict:
    brand_dir = brand_yaml.parent
    doc = load_joined(brand_dir)
    src_bundles = source_bundles(doc)

    work_dir = out_dir / "_cssdiff"
    index_html = work_dir / "index.html"
    if not (skip_compose and index_html.is_file()):
        index_html = compose_our_replica(brand_yaml, work_dir)

    n_sections = sum(1 for e in doc.get("elements", []) if e.get("kind") == "section")
    probes = _our_probes(max(n_sections, 6))
    our_bundles = measure_our_replica(index_html, probes, viewports)

    divs, matches = match_and_diff(our_bundles, src_bundles)

    # HEADING-TIER AUDIT: authored brand.yaml scale vs the CSS-variable truth. These
    # divergences catch a collapsed/mis-authored type ladder that renders
    # self-consistently and would otherwise slip past both gates.
    truth = load_type_scale_truth(brand_dir)
    heading_tier_divs: list[dict] = []
    if truth:
        heading_tier_divs = heading_tier_divergences(_authored_type(brand_yaml), truth)
        divs.extend(heading_tier_divs)

    divs = rank(divs)
    acc = acceptance(divs)

    brand_name = brand_dir.parent.name
    meta = {
        "viewports": list(viewports),
        "replicaIndex": str(index_html),
        "joinedEvidence": str(brand_dir / "evidence" / "joined-evidence.json"),
    }
    meta["headingTierAudit"] = {
        "source": str(brand_dir / "evidence" / "type-scale.json") if truth else None,
        "method": (truth or {}).get("method"),
        "divergences": heading_tier_divs,
    }
    out_doc, md = build_docs(brand_name, divs, matches, acc, meta)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "css-diff.json").write_text(json.dumps(out_doc, indent=1) + "\n")
    (out_dir / "css-diff.md").write_text(md)
    return out_doc


def print_summary(doc: dict) -> None:
    print(f"[css-diff] {doc['brand']}: {doc['totalDivergences']} divergences "
          f"(critical {doc['severityCounts']['critical']}, "
          f"high {doc['severityCounts']['high']}, "
          f"medium {doc['severityCounts']['medium']}, "
          f"low {doc['severityCounts']['low']})")
    labels = {
        "button_hover_transform": "(a) button translateY(-1px) hover-transform",
        "hero_height_calc_vs_px": "(b) hero height px vs calc(100dvh-nav)",
        "nav_panel_background": "(c) mega-nav panel missing background",
        "footer_responsive_columns": "(d) footer non-responsive grid vs @media columns",
    }
    print("[css-diff] known-divergence acceptance:")
    for key, label in labels.items():
        mark = "FOUND    " if doc["acceptance"].get(key) else "NOT FOUND"
        print(f"    [{mark}] {label}")
    hta = doc.get("headingTierAudit") or {}
    ht_divs = hta.get("divergences") or []
    print(f"[css-diff] heading-tier audit (authored vs css-var): "
          f"{len(ht_divs)} divergence(s)")
    for d in ht_divs:
        print(f"    {d['severity']:<8} {d['element']}.{d['property']} "
              f"authored={_norm(d['ours'])!r} css-var={_norm(d['source'])!r}")
    print("[css-diff] top divergences:")
    for d in doc["divergences"][:8]:
        print(f"    {d['rankScore']:>5} {d['severity']:<8} {d['element']}."
              f"{d['property']} [{d['likelyCause']}] "
              f"ours={_norm(d['ours'])[:32]!r} src={_norm(d['source'])[:32]!r}")


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("brand_yaml", type=Path)
    ap.add_argument("-o", "--out", type=Path, default=None,
                    help="output dir (default: <brand_dir>/compose/replica)")
    ap.add_argument("--viewports", default=",".join(str(v) for v in DEFAULT_VIEWPORTS),
                    help="csv viewport widths (default 1920,1440,960,375)")
    ap.add_argument("--skip-compose", action="store_true",
                    help="reuse an already-composed _cssdiff/index.html if present")
    return ap


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    brand_yaml = args.brand_yaml.resolve()
    if not brand_yaml.is_file():
        raise SystemExit(f"css_fidelity: brand yaml not found: {brand_yaml}")
    out_dir = (args.out or (brand_yaml.parent / "compose" / "replica")).resolve()
    try:
        viewports = tuple(int(v) for v in args.viewports.split(",") if v.strip())
    except ValueError:
        raise SystemExit(f"css_fidelity: bad --viewports {args.viewports!r}")
    doc = run(brand_yaml, out_dir, viewports, skip_compose=args.skip_compose)
    print_summary(doc)
    print(f"[css-diff] wrote {out_dir / 'css-diff.json'} + css-diff.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
