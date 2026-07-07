#!/usr/bin/env python3
"""compose_section.py - COMPOSE a section from the catalog, slot by slot.

A layout in brand.yaml describes structure as an ARCHETYPE + named SLOTS, and binds each
slot to catalog components via `blockMapping[]` (`{slot, role, contract, usage}`). This
module renders a section by, FOR EACH slot, resolving the bound primitive/block from the
catalog and rendering THAT component through the shared single-source-of-truth renderers
in `component_render.py` - the SAME functions the components-preview gallery uses. So a
section is ASSEMBLED from reusable catalog components, not hand-built bespoke markup:
editing a catalog primitive changes every composed section that uses it.

Pipeline:
  1. resolve the layout's surface (surfaceIntent) -> brand token VALUES (component_vars).
  2. for every blockMapping entry, resolve_renderer(contract) and render(doc, ctx, props),
     where props come from the entry's `usage` + the section's real copy. -> a dict of
     rendered fragments keyed by (slot, role).
  3. an ARCHETYPE handler arranges the rendered fragments into the scaffold (positions /
     grid / overlap), driven by brand tokens + the layout's grid/overlap rules.
  4. the STYLE layer (styles.py merge) is layered over the brand base in CSS source order
     so structural precedence still applies; default (no --style) behavior is unchanged.

Container-query units ONLY (cqw/cqh/cqi against a container-type:size context) - never
vh/vw/dvh (the render is shown in a Studio iframe).

Usage:
  python3 compose_section.py <brand.yaml> <layoutId> -o <outdir> [--style <id>]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import urllib.request
from pathlib import Path

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import component_render as cr  # noqa: E402
import tokens_css  # noqa: E402
from tokens_css import (  # noqa: E402
    _PROXY_GF,
    _slug,
    base_size,
    color_value,
    css_len,
    font_stack,
    google_fonts_link,
    spacing_value,
    type_role,
)
from styles import RenderContext, inactive_context, load_and_merge  # noqa: E402
import layout_library as ll  # noqa: E402


# ── section copy: BRAND DATA, not pipeline code ──────────────────────────────────
# A brand's real section copy lives in `<brand_dir>/section-copy.yaml`
# (`sectionCopy:` page-global base + `layoutCopy:` per-layout-id overrides) and is
# attached to the in-memory doc by the render entrypoints (attach_brand_copy), the
# same way the asset inventory travels. The module dicts below are EMPTY runtime
# patch surfaces: compose_from_composition / wildcard_generator / A-B harnesses
# still bind per-render copy by patching them, and a patched entry wins over the
# brand file. A brand with NO section-copy.yaml degrades to empty copy (wordmark-
# only nav, elided eyebrow/cta — the _SafeCopy behavior), never to another brand's.
SECTION_COPY: dict = {}

# private doc key carrying the ACTIVE brand's section-copy.yaml payload
# ({"section": {...}, "layout": {id: {...}}}); in-memory only, never written back.
BRAND_COPY_KEY = "_brandCopy"
SECTION_COPY_FILE = "section-copy.yaml"


def load_brand_copy(brand_dir: Path) -> dict:
    """Read `<brand_dir>/section-copy.yaml` into {"section", "layout", "layoutImages",
    "defaultArt", "wildcardCopy"} layers. Missing file (or malformed top level) → empty
    layers: copy and default art DEGRADE, they are never borrowed from another brand."""
    out = {"section": {}, "layout": {}, "layoutImages": {}, "defaultArt": {},
           "wildcardCopy": {}}
    p = Path(brand_dir) / SECTION_COPY_FILE
    if not p.is_file():
        return out
    try:
        data = yaml.safe_load(p.read_text()) or {}
    except Exception:
        return out
    if isinstance(data, dict):
        sec, lay = data.get("sectionCopy"), data.get("layoutCopy")
        if isinstance(sec, dict):
            out["section"] = sec
        if isinstance(lay, dict):
            out["layout"] = {k: v for k, v in lay.items() if isinstance(v, dict)}
        li, da = data.get("layoutImages"), data.get("defaultArt")
        if isinstance(li, dict):
            out["layoutImages"] = {k: v for k, v in li.items() if isinstance(v, dict)}
        if isinstance(da, dict):
            out["defaultArt"] = {k: [str(x) for x in v]
                                 for k, v in da.items() if isinstance(v, list)}
        wc = data.get("wildcardCopy")
        if isinstance(wc, dict):
            out["wildcardCopy"] = {k: v for k, v in wc.items() if isinstance(v, dict)}
    return out


def attach_brand_copy(doc: dict, brand_dir: Path) -> dict:
    """Attach the active brand's section-copy layers to the in-memory doc (under the
    private ``_brandCopy`` key). Idempotent; returns the doc for chaining."""
    if isinstance(doc, dict):
        doc[BRAND_COPY_KEY] = load_brand_copy(Path(brand_dir))
    return doc


def brand_section_copy(doc) -> dict:
    """The active brand's page-global copy base (empty when no section-copy.yaml)."""
    bc = doc.get(BRAND_COPY_KEY) if isinstance(doc, dict) else None
    return (bc or {}).get("section") or {}


def brand_layout_copy(doc) -> dict:
    """The active brand's per-layout-id copy overrides (empty when none declared)."""
    bc = doc.get(BRAND_COPY_KEY) if isinstance(doc, dict) else None
    return (bc or {}).get("layout") or {}


def brand_layout_images(doc) -> dict:
    """The active brand's per-layout photography map (section-copy.yaml
    ``layoutImages:``): layout id -> {role-substring: filename}. Empty when the
    brand declares none — sections then resolve generic default art or omit."""
    bc = doc.get(BRAND_COPY_KEY) if isinstance(doc, dict) else None
    return (bc or {}).get("layoutImages") or {}


def brand_default_art_names(doc, kind: str) -> list[str]:
    """The active brand's PREFERRED default-art filenames for a generic role kind
    (section-copy.yaml ``defaultArt:``). [] when undeclared — _brand_art then falls
    through to the generic keyword match over the brand's own inventory."""
    bc = doc.get(BRAND_COPY_KEY) if isinstance(doc, dict) else None
    return ((bc or {}).get("defaultArt") or {}).get(kind) or []


def brand_wildcard_copy(doc) -> dict:
    """The active brand's wildcard-candidate copy blocks (section-copy.yaml
    ``wildcardCopy:``): candidate id -> copy dict. Empty when undeclared — wildcard
    candidates that NEED copy are then omitted, never seeded from another brand."""
    bc = doc.get(BRAND_COPY_KEY) if isinstance(doc, dict) else None
    return (bc or {}).get("wildcardCopy") or {}

# ── brand asset inventory (AS-34: active-brand-only default art + recursive discovery) ─

IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".svg", ".webp", ".gif")

# private doc key carrying the ACTIVE brand's on-disk image inventory (attached by the
# render entrypoints via attach_asset_inventory; in-memory only, never written back).
ASSET_INVENTORY_KEY = "_assetInventory"


def brand_image_inventory(brand_dir: Path) -> list[str]:
    """Sorted unique basenames of the ACTIVE brand's real image assets — RECURSIVE
    (blocker-6: subdirectories such as ``assets/logos/`` used to be invisible, forcing
    extraction workers to flatten their curated trees). Scanned roots:
      - ``brand_dir`` itself, recursively (covers the WoodWave convention where the
        canonical files live under ``render/*/assets/`` — disk evidence replaces the old
        cross-brand ``ASSET_SOURCES`` name seed);
      - ``brand_dir.parent/assets`` top level (the run-root convention, e.g.
        runs/<brand>/assets/hero-full-bleed.webp) — top level only, because the run root
        also stores extraction dumps that must never count as curated brand assets.
    ``fonts/`` subtrees and the per-page composed ``NAV_LOGO_LOCAL`` are excluded."""
    brand_dir = Path(brand_dir)
    names: set[str] = set()
    if brand_dir.is_dir():
        for p in brand_dir.rglob("*"):
            if not p.is_file() or p.suffix.lower() not in IMAGE_EXTS:
                continue
            if "fonts" in p.parts or p.name == NAV_LOGO_LOCAL:
                continue
            names.add(p.name)
    parent_assets = brand_dir.parent / "assets"
    if parent_assets.is_dir():
        names |= {p.name for p in parent_assets.iterdir()
                  if p.is_file() and p.suffix.lower() in IMAGE_EXTS
                  and p.name != NAV_LOGO_LOCAL}
    return sorted(names)


def attach_asset_inventory(doc: dict, brand_dir: Path) -> dict:
    """Attach the active brand's image inventory to the in-memory doc (under the private
    ``_assetInventory`` key) so composers can resolve default/fallback art from the
    ACTIVE brand's own files (AS-34). Idempotent; returns the doc for chaining."""
    if isinstance(doc, dict):
        doc[ASSET_INVENTORY_KEY] = brand_image_inventory(Path(brand_dir))
    return doc


# default-art KIND → filename keywords, tried in order against the active brand's
# inventory. Keywords name generic asset ROLES (never a brand's own filenames): the
# resolver is a keyword match over the brand's OWN files, so every brand resolves
# its OWN art or nothing. A brand may pin exact preferences per kind via its
# section-copy.yaml ``defaultArt:`` (brand_default_art_names), checked first.
_DEFAULT_ART_KEYWORDS = {
    "hero": ("hero", "full-bleed", "cover"),
    "detail": ("overlap", "detail", "closeup", "texture"),
    "gallery": ("gallery", "interior", "showcase"),
    "portrait": ("portrait", "avatar", "curator"),
    "map": ("map",),
}


def brand_default_art(doc, kind: str = "hero") -> str | None:
    """The ACTIVE brand's default art for a generic role kind, as an ``assets/<name>``
    src — or None when the brand's inventory carries no match (callers must then OMIT
    the device, never borrow another brand's file: AS-34). A doc without an attached
    inventory (direct library callers / legacy harnesses) returns None for non-WoodWave
    shapes and the legacy WoodWave defaults only when those files are actually in the
    attached inventory — i.e. resolution is ALWAYS evidence-based."""
    inv = doc.get(ASSET_INVENTORY_KEY) if isinstance(doc, dict) else None
    if not inv:
        return None
    for kw in _DEFAULT_ART_KEYWORDS.get(kind, (kind,)):
        hit = next((n for n in inv if kw in n.lower()), None)
        if hit:
            return f"assets/{hit}"
    return None


def _brand_art(doc, kind: str, *preferred: str) -> str | None:
    """Evidence-checked default/fallback art (AS-34): the first *preferred* filename
    (the brand's own declared ``defaultArt:`` hints) that actually exists in the
    ACTIVE brand's inventory, else the first inventory file matching the generic
    *kind* keywords (brand_default_art), else None — the caller must then omit the
    device, NEVER borrow another brand's file. A doc with NO attached inventory
    resolves None too: art is only ever emitted on disk evidence."""
    inv = doc.get(ASSET_INVENTORY_KEY) if isinstance(doc, dict) else None
    if not inv:
        return None
    for name in preferred:
        if name in inv:
            return f"assets/{name}"
    return brand_default_art(doc, kind)

# Layout-specific REAL photography is BRAND DATA: each brand declares its own
# ``layoutImages:`` map in section-copy.yaml (layout id -> {role-substring: filename}),
# read via brand_layout_images(doc) in `_props_for` BEFORE the generic image fallback
# so each section shows its own real photo instead of reusing the hero's.

# Local, offline-safe filename the composed nav logo is copied to (referenced from the
# generated HTML as `assets/<NAV_LOGO_LOCAL>`).
NAV_LOGO_LOCAL = "nav-logo.svg"

# ── self-hosted brand DISPLAY fonts ──────────────────────────────────────────────
# A brand's real display face can be a NON-Google webfont. Instead of a Google-Fonts
# proxy, the brand self-hosts the files under `<brand_dir>/assets/fonts/` and
# DECLARES them in its brand.yaml `selfHostedFonts:` registry (see
# brand_self_hosted_fonts below). At compose time we (a) copy each face file into
# the page's `assets/` (offline-safe, exactly like the nav-logo copy) and (b) emit
# `@font-face` blocks so the display heading actually renders in it. Keyed by the
# brand.yaml `family` name; a brand whose display family is a Google font (or that
# registers nothing) is byte-unchanged (no @font-face, no copy).
#
# Each family self-hosts the REAL per-weight masters as SEPARATE `@font-face` blocks
# (one file pair per weight), so the browser picks the correct face for each
# requested font-weight. (An earlier version self-hosted only the Bold master and
# mapped every display weight onto it via a `font-weight: 400 700` range, which made
# every heading render Bold.) There is NO module-level registry: font registration
# is brand data, never shared pipeline state.

# The display type roles whose `family` we scan for a self-hosted face.
_DISPLAY_FONT_ROLES = ("display-hero", "h1", "h2", "h3", "counter-display",
                       "ghost-watermark", "footer-sitemap-link")

_FONT_FORMATS = {"woff2": "woff2", "woff": "woff", "ttf": "truetype", "otf": "opentype"}


def find_font_source(brand_dir: Path, name: str):
    """Resolve a self-hosted font file under the brand's stable assets/fonts/ dir."""
    p = brand_dir / "assets" / "fonts" / name
    return p if p.exists() else None


def brand_self_hosted_fonts(doc: dict) -> dict:
    """The ACTIVE brand's self-hosted font registry (schema-gap 8, remote-fix 2026-07):
    built ONLY from the brand.yaml ``selfHostedFonts`` entries — a brand registers its
    own faces declaratively; there is no shared module registry to inherit from.

    brand.yaml shape (additive, generic)::

        selfHostedFonts:
          - family: DisplayFace          # must match the type role's `family`
            faces:
              - weight: 400
                files: [DisplayFace-Regular.woff2, DisplayFace-Regular.ttf]
                # style: italic         # optional; normal when absent

    Files live under ``<brand_dir>/assets/fonts/``. A registered family whose files
    are ABSENT on disk simply emits no @font-face — the font stack then falls through
    to the brand's measured ``renderProxy``, so a registry entry can never break a
    render (registry present, commercial files not captured, proxy declared as the
    fallback)."""
    reg: dict = {}
    entries = doc.get("selfHostedFonts") if isinstance(doc, dict) else None
    for entry in (entries or []):
        if not isinstance(entry, dict):
            continue
        fam = str(entry.get("family") or "").strip()
        faces = []
        for f in (entry.get("faces") or []):
            if not isinstance(f, dict):
                continue
            files = [str(x).strip() for x in (f.get("files") or [])
                     if isinstance(x, str) and str(x).strip()]
            if not files:
                continue
            face = {"weight": f.get("weight", 400), "files": files}
            if f.get("style"):
                face["style"] = str(f["style"]).strip().lower()
            faces.append(face)
        if fam and faces:
            reg[fam] = {"faces": faces}
    return reg


def self_hosted_families(doc: dict) -> list[str]:
    """The brand display families that have a registered self-hosted font (order-stable)."""
    reg = brand_self_hosted_fonts(doc)
    fams, seen = [], set()
    for role in _DISPLAY_FONT_ROLES:
        fam = type_role(doc, role).get("family")
        if fam in reg and fam not in seen:
            seen.add(fam)
            fams.append(fam)
    return fams


def copy_fonts(brand_dir: Path, out_assets: Path, doc: dict) -> list[str]:
    """Copy every self-hosted display-font file into ``out_assets`` so the composed page's
    @font-face works offline (mirrors ``copy_assets`` / the nav-logo copy). Returns the
    list of copied filenames; empty (and a no-op) when the brand uses no self-hosted font."""
    out_assets.mkdir(parents=True, exist_ok=True)
    reg = brand_self_hosted_fonts(doc)
    copied = []
    for fam in self_hosted_families(doc):
        for face in reg[fam]["faces"]:
            for name in face["files"]:
                src = find_font_source(brand_dir, name)
                if src:
                    shutil.copy2(src, out_assets / name)
                    copied.append(name)
    return copied


def font_face_css(brand_dir: Path, doc: dict) -> str:
    """Emit the ``@font-face`` block(s) for the brand's self-hosted display face(s),
    referencing the copied ``assets/<file>`` relatively (woff2 preferred, ttf fallback).
    Returns "" when the brand carries no self-hosted font — or when the registered
    files are absent on disk (the font stack then resolves the measured renderProxy)."""
    reg = brand_self_hosted_fonts(doc)
    blocks = []
    for fam in self_hosted_families(doc):
        for face in reg[fam]["faces"]:
            srcs = []
            for name in face["files"]:
                if find_font_source(brand_dir, name):
                    ext = name.rsplit(".", 1)[-1].lower()
                    srcs.append(f"url('assets/{name}') format('{_FONT_FORMATS.get(ext, ext)}')")
            if not srcs:
                continue
            style = face.get("style") or "normal"
            blocks.append(
                f"@font-face {{ font-family: '{fam}'; src: {', '.join(srcs)}; "
                f"font-weight: {face['weight']}; font-style: {style}; font-display: swap; }}")
    if not blocks:
        return ""
    return ("/* self-hosted brand display face(s) — copied into assets/ for offline use */\n"
            + "\n".join(blocks))

# Per-layout copy overrides: runtime patch surface ONLY (see SECTION_COPY note).
# A brand's authored per-layout copy lives in `<brand_dir>/section-copy.yaml`
# under `layoutCopy:`; compositions and the wildcard generator register entries
# here at render time, and a registered entry replaces the brand-file entry for
# that layout id wholesale (the historical top-level-merge semantics).
LAYOUT_COPY: dict = {}


class _SafeCopy(dict):
    """Copy dict that resolves a MISSING key to '' instead of raising (AS-36 /
    remote-fix blocker-7: a pattern rendered for a brand whose copy dict lacks a
    composer's key — e.g. `panelTitle` on a split preview — crashed the whole tier).
    Composers keep their `copy["key"]` reads; an absent key renders as empty copy for
    that device, which the renderers already handle (empty heading/caption elide)."""

    def __missing__(self, key):
        return ""


def section_copy_view(doc) -> dict:
    """The page-global copy BASE the composers see: the active brand's authored
    ``sectionCopy`` (section-copy.yaml) with any runtime-patched module SECTION_COPY
    merged over it. _SafeCopy, so a key no layer declares degrades to ''."""
    return _SafeCopy({**brand_section_copy(doc), **SECTION_COPY})


def layout_copy_layer(layout, doc=None) -> dict:
    """The LAYOUT-layer copy for this section id. A runtime-registered module entry
    (composition adapter / wildcard generator) replaces the brand-file entry
    WHOLESALE — the same top-level semantics the old module dict had; otherwise the
    brand's authored layoutCopy entry applies."""
    lid = (layout or {}).get("id")
    if lid in LAYOUT_COPY:
        return LAYOUT_COPY[lid] or {}
    return brand_layout_copy(doc).get(lid) or {}


def copy_for(layout, doc=None) -> dict:
    """Merge the page-global copy base with this layout's copy layer (brand-file
    entry, or the runtime-registered entry when a composition/wildcard bound one)."""
    return _SafeCopy({**brand_section_copy(doc), **SECTION_COPY,
                      **layout_copy_layer(layout, doc)})


# ── helpers ──────────────────────────────────────────────────────────────────────

def load_doc(brand_yaml: Path) -> dict:
    doc = yaml.safe_load(Path(brand_yaml).read_text())
    # attach the ACTIVE brand's on-disk image inventory (AS-34) + authored section
    # copy so defaults resolve from the brand's own data — in-memory only.
    attach_brand_copy(doc, Path(brand_yaml).parent)
    return attach_asset_inventory(doc, Path(brand_yaml).parent)


def find_layout(doc, layout_id):
    return next((l for l in doc.get("layouts", []) if l.get("id") == layout_id), None)


# ── layout-pattern resolution (reuse-before-create; brand-schema.md §4.4, Appendix C) ──

def resolve_pattern(doc, layout, brand_yaml):
    """Resolve the reusable layout PATTERN a section is generated from. Prefers the layout's
    explicit ``patternRef`` (project/standard library); otherwise runs the retrieval matcher
    over the two-tier library (project-first, brand-neverDo-filtered). Returns
    ``(pattern|None, matchKind)`` where matchKind ∈ reuse|adapt|miss|ref. Defensive: any
    failure (no brand path, missing library) returns ``(None, "none")`` so composition falls
    back to the archetype default unchanged."""
    if not brand_yaml:
        return None, "none"
    try:
        ref = layout.get("patternRef")
        if isinstance(ref, dict) and ref.get("id"):
            p = ll.get(ref, Path(brand_yaml))
            if p is not None:
                return p, "ref"
        res = ll.match(ll.query_from_layout(layout, doc), Path(brand_yaml))
        return res.pattern, res.match_kind
    except Exception:
        return None, "none"


# amount-class -> concrete relative magnitude (resolved as container-query units, never px).
# The captured pattern's treatment ``amount.class`` drives the geometry, so the ghost word /
# stagger scale come FROM the reused pattern instead of a hardcoded literal.
#
# CS-2 (token-layer-2026-07): the ladder's rem ENDPOINTS are now calc-of-var products of
# the brand's MEASURED ghost tier (--size-ghost-watermark-base, layer 1) — the multipliers
# are the ladder's structural step ratios (computed against the pre-token ladder at
# WoodWave's 26.25rem tier so every existing render resolves byte-equal), the magnitude is
# the brand's. A brand with no ghost-watermark tier leaves the var unresolved -> font-size
# drops -> the device is disabled (never another brand's scale). cqw midpoints stay
# structural fluidity (SPEC §C.2). The flat -base alias keeps clamp endpoints breakpoint-
# independent (the responsive --size-ghost-watermark ladder is for direct consumers).
_GHOST_BASE = "var(--size-ghost-watermark-base)"
_GHOST_SIZE = {
    "light": f"clamp(calc({_GHOST_BASE} * 0.2286), 22cqw, calc({_GHOST_BASE} * 0.6857))",
    "medium": f"clamp(calc({_GHOST_BASE} * 0.3048), 30cqw, calc({_GHOST_BASE} * 0.9143))",
    "heavy": f"clamp(calc({_GHOST_BASE} * 0.381), 40cqw, calc({_GHOST_BASE} * 1.219))",
}
# ALIGNMENT: offsets are no longer free scalars — they snap to the SHARED units emitted on
# :root (--baseline / --col / --grid-gutter) so a staggered element lands on a shared line.
# The %-based stagger keeps its responsive magnitude but round()s the USED value to an
# exact --baseline multiple (registration without changing the rendered look).
_STAGGER_OFFSET = {
    "light": "round(nearest, 8%, var(--baseline))",
    "medium": "round(nearest, 18%, var(--baseline))",
    "heavy": "round(nearest, 33%, var(--baseline))",
}
# Block offset for the multi-module `cards` composer (margin-block-start): the harvested
# "~50px second-card offset" is now an exact --baseline multiple (old cqw values at the
# 1440 reference: 2.5cqw≈2.25rem→4 baselines, 4cqw≈3.6rem→7, 6.5cqw≈5.85rem→12).
_CARD_STAGGER = {
    "light": "calc(4 * var(--baseline))",
    "medium": "calc(7 * var(--baseline))",
    "heavy": "calc(12 * var(--baseline))",
}


def _span_for_ratio(ratio: float, *, measure_rem: float = 86.0, gutter_rem: float = 6.0,
                    cols: int = 12) -> int:
    """Nearest whole-column SPAN (on the shared grid at the nominal --content-measure /
    --grid-gutter) whose rendered width best matches ``ratio`` × container — how a %-based
    inset width snaps onto the shared column grid (e.g. 0.52 → span 7)."""
    col = (measure_rem - (cols - 1) * gutter_rem) / cols
    target = ratio * measure_rem
    return min(range(1, cols + 1), key=lambda s: abs((s * col + (s - 1) * gutter_rem) - target))


def _spans_for_tracks(tracks: str, *, cols: int = 12) -> list[int] | None:
    """Map an fr-ratio track list (e.g. "1.2fr 1fr") to whole-column spans on the shared
    grid that sum to ``cols`` (largest-remainder rounding, min 1 per track). Returns None
    when the string carries no parseable fr values."""
    import re as _re
    frs = [float(m) for m in _re.findall(r"(\d+(?:\.\d+)?)\s*fr", str(tracks))]
    if not frs:
        return None
    total = sum(frs)
    raw = [f / total * cols for f in frs]
    spans = [max(1, int(r)) for r in raw]
    rema = sorted(range(len(raw)), key=lambda i: raw[i] - int(raw[i]), reverse=True)
    i = 0
    while sum(spans) < cols:
        spans[rema[i % len(rema)]] += 1
        i += 1
    while sum(spans) > cols:
        j = max(range(len(spans)), key=lambda k: spans[k])
        spans[j] -= 1
    return spans


def _treatment(pattern, kind):
    for t in (pattern.special_treatments if pattern else []) or []:
        if t.get("kind") == kind:
            return t
    return None


def _knob_default(pattern, name):
    """Read a pattern variantKnob's ``default`` (None when the knob/pattern is absent)."""
    k = (pattern.variant_knobs or {}).get(name) if pattern else None
    return k.get("default") if isinstance(k, dict) else None


def pattern_treatment_css(pattern) -> str:
    """Emit the CSS custom properties the scaffold geometry reads for this pattern's SPECIAL
    TREATMENTS + tunable KNOBS so the reused pattern actually PARAMETERIZES the output:

      - ghost-word  -> --c-ghost-size            (watermark scale)
      - stagger     -> --c-stagger-offset (baseline-rounded %) +
                       --c-card-stagger (a --baseline multiple block offset)
      - columnRatio -> --c-span-a / --c-span-b   (whole-column spans on the SHARED grid;
                       the old private --c-column-ratio fr tracks are replaced by
                       registered spans) + --c-column-ratio kept for traceability
      - cardCount   -> --c-card-count            (module count, informational)
      - float-wrap / inset -> --c-float-side, --c-inset-width (a whole-column SPAN width),
                              --c-inset-margin / --c-inset-drop (--baseline multiples)

    ALIGNMENT: every offset/width is expressed in the SHARED page units (--baseline /
    --col / --grid-gutter emitted on :root) so pattern-driven geometry registers to the
    shared grid instead of floating on private scalars.
    Returns "" when the pattern carries none, so a section with no treatments/knobs is
    byte-unchanged. Kept neverDo-safe: only sizes/offsets/sides of existing devices — no
    radius/shadow/gradient introduced, cq/rem units only (never viewport units)."""
    if pattern is None:
        return ""
    decls: list[str] = []
    g = _treatment(pattern, "ghost-word")
    if g:
        amt = ((g.get("amount") or {}).get("class")) or "heavy"
        decls.append(f"--c-ghost-size: {_GHOST_SIZE.get(amt, _GHOST_SIZE['heavy'])};")
    s = _treatment(pattern, "stagger")
    if s:
        amt = ((s.get("amount") or {}).get("class")) or "medium"
        decls.append(f"--c-stagger-offset: {_STAGGER_OFFSET.get(amt, _STAGGER_OFFSET['medium'])};")
        decls.append(f"--c-card-stagger: {_CARD_STAGGER.get(amt, _CARD_STAGGER['medium'])};")
        # per-column registered placement (editorial-harvest-2026-07,
        # staggered-caption-columns-3): each entry pins a module to whole-column tracks
        # with a baseline-multiple drop; the scaffold's nth-child vars pick these up and
        # their var() defaults keep every perColumn-less render computed-value unchanged.
        for i, pc in enumerate((s.get("perColumn") or [])[:3], start=1):
            try:
                cs_, sp = int(pc.get("colStart")), int(pc.get("colSpan"))
                decls.append(f"--c-col-{i}: {cs_} / span {sp};")
            except (TypeError, ValueError):
                pass
            try:
                ro = int(pc.get("rowOffset"))
                decls.append(f"--c-drop-{i}: calc({3 * ro} * var(--baseline));")
            except (TypeError, ValueError):
                pass
    # multi-module knobs: the uneven column ratio maps to whole-column SPANS on the shared
    # grid ("1.2fr 1fr" -> 7/5) so the modules sit on registered tracks; the raw ratio is
    # kept as an inert traceability var (no scaffold reads it anymore).
    col = _knob_default(pattern, "columnRatio")
    if col:
        spans = _spans_for_tracks(col)
        if spans and len(spans) >= 2:
            decls.append(f"--c-span-a: {spans[0]};")
            decls.append(f"--c-span-b: {spans[1]};")
        decls.append(f"--c-column-ratio: {col};")
    cc = _knob_default(pattern, "cardCount")
    if cc is not None:
        decls.append(f"--c-card-count: {cc};")
    # float-wrap / inset (the interlock composer): side, inset width, headline drop + gutter.
    fw = _treatment(pattern, "float-wrap")
    inset = _treatment(pattern, "inset")
    if fw or inset:
        side = (fw or {}).get("side") or (inset or {}).get("side") \
            or _knob_default(pattern, "floatSide") or "right"
        side = "left" if str(side).lower() == "left" else "right"
        # the inset width SNAPS to a whole-column span of the shared grid (the % ratio's
        # nearest span at the nominal measure — e.g. 0.52 -> span 7), so the inset's inner
        # edge lands on a shared column line instead of an arbitrary % offset.
        try:
            ratio = float(((inset or {}).get("widthRel") or {}).get("ratio"))
        except (TypeError, ValueError):
            ratio = 0.52
        span = _span_for_ratio(ratio)
        width = (f"calc({span} * var(--col) + {span - 1} * var(--grid-gutter, 6rem))"
                 if span > 1 else "var(--col)")
        # the inset's gutter sits on the side FACING the wrapped copy; --baseline multiples
        # only (old cqw scalars at the 1440 reference: 0.4cqw≈1, 1.2cqw≈2, ~3rem≈6).
        _b = "var(--baseline)"
        margin = (f"calc(1 * {_b}) 0 calc(2 * {_b}) calc(6 * {_b})" if side == "right"
                  else f"calc(1 * {_b}) calc(6 * {_b}) calc(2 * {_b}) 0")
        decls.append(f"--c-float-side: {side};")
        decls.append(f"--c-inset-width: {width};")
        decls.append(f"--c-inset-margin: {margin};")
        decls.append(f"--c-inset-drop: clamp(calc(9 * {_b}), 12cqw, calc(22 * {_b}));")
    if not decls:
        return ""
    return ("/* pattern-driven special treatments + knobs (from the reused layout pattern) */\n"
            ":root { " + " ".join(decls) + " }")


def catalog_entry(doc, contract):
    """Resolve a contract key to its brand catalog entry (primitive or block)."""
    return (doc.get("primitives") or {}).get(contract) \
        or (doc.get("blocks") or {}).get(contract)


def resolve_surface_intent(doc, layout):
    """Resolve a layout's surface. v2 layouts name the surface via `surfaceIntent` (a
    token role); honor it first (legacy surfaceRole/surfaceMode fall through). Mirrors
    onbrand_check.resolve_surface so the composer and the gate agree on the surface."""
    surfaces = doc["tokens"]["surfaces"]
    role = layout.get("surfaceIntent") or layout.get("surfaceRole")
    if role and role in surfaces:
        return role, surfaces[role]
    mode = (layout.get("surfaceMode") or {}).get("mode")
    for r, s in surfaces.items():
        if s.get("schemeMode") == mode:
            return r, s
    first = next(iter(surfaces))
    return first, surfaces[first]


# Surface roles that read as "dark" (drive the dark vs light section-padding token).
DARK_SURFACES = ("surface/inverse", "surface/inverse-strong", "surface/accent", "surface/overlay")


def _brand_spacing(doc, key):
    """Read a brand.yaml spacing token VALUE (read-only); None when absent."""
    tok = ((doc.get("tokens", {}) or {}).get("spacing", {}) or {}).get(key)
    return (tok or {}).get("value") if isinstance(tok, dict) else None


def rhythm_for(doc, style_ctx, surf_role) -> dict:
    """Resolve the vertical-rhythm values for a surface, PREFERRING the brand's real
    spacing tokens (the source's measured rhythm) and falling back to the active style's
    spacing scale only where the brand is silent. Back-compatible: with no active style
    (default compose path) it still resolves from brand tokens + neutral fallbacks.

    Returns {pad_top, pad_bottom, block_gap, module_gap} — all rem strings, never
    viewport units. Section vertical padding is symmetric (top = bottom) unless the brand
    commits otherwise; the brand carries one section-padding token per surface tier."""
    s = style_ctx.structure if (style_ctx and style_ctx.active and style_ctx.structure) else None
    dark = surf_role in DARK_SURFACES
    # section vertical padding: prefer the brand's measured section-padding token.
    pad = (_brand_spacing(doc, "section-padding-dark") if dark else None) \
        or _brand_spacing(doc, "section-padding-light") \
        or (s.section_pad if s else "6.25rem")
    # inter-block gap: brand carries no generic block-gap token -> style scale (else neutral).
    block_gap = s.block_gap if s else "2.5rem"
    # module gap (between collage modules): prefer the brand's module-gap token.
    module_gap = _brand_spacing(doc, "module-gap-editorial") or (s.space("xl") if s else "6rem")
    return {"pad_top": pad, "pad_bottom": pad, "block_gap": block_gap, "module_gap": module_gap}


def rhythm_vars_css(doc, style_ctx, surf_role, selector=":root") -> str:
    """Emit the rhythm CSS custom properties for ``selector`` from ``rhythm_for``.
    These vars (read by the scaffold geometry) make section padding + inter-block gaps
    come from the spacing scale / brand tokens instead of ad-hoc literals.

    Also declares the two STRUCTURAL frame constants the scaffolds read —
    ``--c-section-pad-x`` (horizontal section inset) and ``--c-nav-pad-block`` (slim
    page-nav vertical padding). Declaring them here (custom properties are layer-2;
    the provenance scanner checks USED values, not ``--*`` declarations) lets the
    scaffold var() references drop their literal fallbacks (AS-24 discipline /
    remote-fix blocker-4: a `var(--c-section-pad, 6.25rem)` fallback read as a raw
    literal AND a cross-brand token collision for any brand without a 6.25rem token).
    Values are frame geometry (device structure), not brand rhythm tokens."""
    r = rhythm_for(doc, style_ctx, surf_role)
    return (f"{selector} {{ --c-section-pad-top: {r['pad_top']}; "
            f"--c-section-pad-bottom: {r['pad_bottom']}; --c-section-pad: {r['pad_bottom']}; "
            f"--c-block-gap: {r['block_gap']}; --c-module-gap: {r['module_gap']}; "
            f"--c-section-pad-x: 2.5rem; --c-nav-pad-block: 1.75rem; }}")


def loadable_proxies(doc):
    """Google-Fonts families to actually load: the brand's real display+body families
    when they are known Google Fonts (Playfair Display / Inter), else their proxy."""
    out = set()
    for role in ("display-hero", "body"):
        fam = type_role(doc, role).get("family")
        if fam in _PROXY_GF:
            out.add(fam)
        else:
            _, p = font_stack(doc, role)
            out |= p
    return out


def copy_assets(brand_dir: Path, out_assets: Path):
    out_assets.mkdir(parents=True, exist_ok=True)
    copied = []
    # brand-agnostic: any image under the ACTIVE brand's assets/ tree ships — checking
    # BOTH conventions (curated images at <brand_dir>/assets/, or at the run root
    # runs/<brand>/assets/). There is NO shared seed list: what ships is exactly what
    # the brand's own disk evidence carries.
    # RECURSIVE under the brand's own assets/ (blocker-6: curated subdirectories such as
    # assets/logos/ were invisible, forcing workers to flatten their trees) — flattened
    # to basenames on copy, first (sorted-path) occurrence wins; fonts/ ships via
    # copy_fonts, not here. The RUN-ROOT convention stays top-level only: that dir also
    # holds extraction dumps that are not curated brand assets.
    def _ship(img: Path):
        if img.is_file() and img.suffix.lower() in IMAGE_EXTS and img.name not in copied:
            shutil.copy2(img, out_assets / img.name)
            copied.append(img.name)

    brand_assets = brand_dir / "assets"
    if brand_assets.is_dir():
        for img in sorted(brand_assets.rglob("*")):
            if "fonts" not in img.relative_to(brand_assets).parts:
                _ship(img)
    parent_assets = brand_dir.parent / "assets"
    if parent_assets.is_dir():
        for img in sorted(parent_assets.glob("*")):
            _ship(img)
    return copied


# ── nav logo: resolve srcContract -> local, offline-safe asset (read-only wrt brand.yaml) ─

def _resolve_logo_src(brand_dir: Path, logo: dict):
    """Resolve a navbar logo's image URL. Inline `src` wins; else resolve `srcContract`
    of the form ``<relpath>#<dotted.key.path>`` by loading the referenced JSON (relative to
    the brand dir, e.g. runs/woodwave/assets/source-chrome.v2.json) and reading the dotted
    key (e.g. nav.logo.src). Defensive: any missing file/key/shape returns None so callers
    fall back to the text wordmark; never raises."""
    if not isinstance(logo, dict):
        return None
    if logo.get("src"):
        return logo["src"]
    contract = logo.get("srcContract")
    if not contract or "#" not in contract:
        return None
    relpath, dotted = contract.split("#", 1)
    ref = (brand_dir / relpath).resolve()
    try:
        data = json.loads(ref.read_text())
    except Exception:
        return None
    cur = data
    for key in dotted.split("."):
        if isinstance(cur, dict) and key in cur:
            cur = cur[key]
        else:
            return None
    return cur if isinstance(cur, str) and cur else None


def _copy_logo_file(brand_dir: Path, src: str, out_assets: Path):
    """Copy the resolved logo into ``out_assets/NAV_LOGO_LOCAL`` for offline-safe preview.
    Prefers a LOCAL copy of the extracted asset (runs/<brand>/assets/source_complete/... or
    elsewhere under the run) matched by the src's basename; falls back to downloading from
    the CDN URL only if no local copy exists. Returns the local filename or None (no crash)."""
    filename = src.split("/")[-1].split("?")[0] or NAV_LOGO_LOCAL
    run_dir = brand_dir.parent  # runs/<brand>/brand -> runs/<brand>
    candidates = [
        run_dir / "assets" / "source_complete" / filename,
        run_dir / "assets" / filename,
    ]
    candidates += sorted(run_dir.glob(f"**/{filename}"))
    out_assets.mkdir(parents=True, exist_ok=True)
    dest = out_assets / NAV_LOGO_LOCAL
    for c in candidates:
        if c.exists() and c.is_file():
            shutil.copy2(c, dest)
            return NAV_LOGO_LOCAL
    if src.startswith("http"):
        try:
            with urllib.request.urlopen(src, timeout=10) as r:  # noqa: S310 (known CDN asset)
                dest.write_bytes(r.read())
            return NAV_LOGO_LOCAL
        except Exception:
            return None
    return None


def prepare_nav_logo(doc: dict, brand_dir: Path, out_assets: Path):
    """Resolve doc.navbar.logo -> a LOCAL, offline-safe asset and record it on the IN-MEMORY
    doc as ``doc['navbar']['logo']['_composedSrc']`` (a relative ``assets/...`` path). brand.yaml
    is NOT written; this mutation is in-memory only. Defensive: any failure leaves
    `_composedSrc` unset so the composed nav gracefully falls back to the text wordmark."""
    nav = doc.get("navbar")
    if not isinstance(nav, dict):
        return None
    logo = nav.get("logo")
    if not isinstance(logo, dict):
        return None
    src = _resolve_logo_src(brand_dir, logo)
    if not src:
        return None
    local = _copy_logo_file(brand_dir, src, out_assets)
    if local:
        logo["_composedSrc"] = f"assets/{local}"
        return logo["_composedSrc"]
    return None


def _nav_action_split(nav: dict, primary: list[dict]) -> tuple[list[dict], dict | None]:
    """Split the extracted primary links into (links, trailing action) from EVIDENCE only
    (AS-39 — no content-keyword heuristics naming any brand's commerce vocabulary):

    1. an explicit ``navbar.ctas[]`` entry (the extractor saw a distinct action element);
    2. a ``navbar.links[]`` entry whose measured ``style`` marks it as a filled pill/button
       (the actions-slot control family), matched back into primary by label;
    3. ``navbar.measured.cta`` present — a distinct CTA element was measured in the bar,
       so the LAST primary item is that action.

    A brand whose evidence declares none of these keeps every primary item as a plain
    link — the action never materializes from vocabulary guesses."""
    ctas = [c for c in (nav.get("ctas") or []) if isinstance(c, dict) and c.get("label")]
    if ctas:
        cta = ctas[-1]
        return [p for p in primary if p.get("label") != cta.get("label")], cta
    styled = {(l.get("label") or ""): (l.get("style") or "")
              for l in (nav.get("links") or []) if isinstance(l, dict)}
    for p in reversed(primary):
        if "filled" in styled.get(p.get("label") or "", ""):
            return [q for q in primary if q is not p], p
    if primary and isinstance((nav.get("measured") or {}).get("cta"), dict):
        return primary[:-1], primary[-1]
    return primary, None


def _navbar_props(doc: dict) -> dict:
    """Build render_navbar props from the extracted ``doc['navbar']`` (logo image + primary
    links + trailing CTA). When no navbar was extracted the nav degrades to the BRAND'S OWN
    data: its authored sectionCopy wordmark/links/cta when present, else a wordmark-only
    nav built from the brand name — copy is never borrowed from another brand.

    The trailing action comes from the extraction evidence (``_nav_action_split``); the
    composition/sectionCopy cta only fills in when the extraction declares none."""
    sc = section_copy_view(doc)
    brand_name = (doc.get("brand") or {}).get("name") or ""
    nav = doc.get("navbar")
    if not isinstance(nav, dict):
        # wordmark-only degrade: links/cta render only when the BRAND declares them.
        return {"wordmark": sc.get("wordmark") or brand_name or "Brand",
                "links": sc.get("nav") or [],
                "cta": sc.get("cta") or None}
    logo = nav.get("logo") or {}
    primary = [p for p in (nav.get("primary") or []) if isinstance(p, dict) and p.get("label")]
    links, cta = _nav_action_split(nav, primary)

    props: dict = {
        "links": links or sc.get("nav") or [],
        "cta": cta["label"] if cta else (sc.get("cta") or None),
        "ctaHref": cta.get("href", "#") if cta else "#",
    }
    src = logo.get("_composedSrc")
    if src:
        props["logo"] = {
            "img": src,
            "href": logo.get("href", "#"),
            "alt": logo.get("alt") or (doc.get("brand") or {}).get("name") or "Brand",
            "width": logo.get("width"),
            "height": logo.get("height"),
        }
    else:
        props["wordmark"] = sc.get("wordmark") or brand_name or "Brand"
    return props


# ── slot resolution: blockMapping entry -> shared catalog renderer ───────────────

def _props_for(doc, layout, role, usage, ctx):
    """Build a shared-renderer props dict from a blockMapping entry's `usage` + the
    section's real copy. Role-keyword driven so it stays brand-agnostic."""
    r = (role or "").lower()
    usage = usage or {}
    sc = section_copy_view(doc)
    # alt text derives from the ACTIVE brand + the asset's own name — never a hardcoded
    # brand-named literal (fix-batch 2026-07: a brand-named alt literal was baked in
    # here and leaked verbatim into other brands' renders).
    brand_name = (doc.get("brand") or {}).get("name") or sc.get("wordmark") or "Brand"
    img_map = brand_layout_images(doc).get((layout or {}).get("id"))
    if img_map:
        for kw, fname in img_map.items():
            if kw in r:
                src = _brand_art(doc, "gallery", fname)
                if src:
                    return {"src": src, "variant": "hero",
                            "alt": f"{brand_name} — {Path(src).name.rsplit('.', 1)[0].replace('-', ' ')}"}
                break  # named art not in the ACTIVE brand's inventory → generic branches
    if "wordmark" in r or "nav" in r:
        # serves both render_logo (text) and render_navbar (wordmark/links/cta);
        # links/cta come from the BRAND's own copy and degrade to none.
        return {"text": brand_name, "wordmark": brand_name,
                "links": sc.get("nav") or [], "cta": sc.get("cta") or None}
    if "title" in r or "heading" in r:
        # serves both render_heading (text) and the header block (heading).
        # v1 layouts carry the REAL heading in props.Text — prefer it over any default.
        title = usage.get("Text") or usage.get("heading", "Heading")
        return {"text": title, "heading": title, "level": usage.get("level", "display"),
                "accent": ctx.is_dark, "splitTwoLines": True}
    if "hero" in r and ("photo" in r or "image" in r or "media" in r):
        return {"src": _brand_art(doc, "hero", *brand_default_art_names(doc, "hero")),
                "variant": "hero",
                "alt": f"{brand_name} editorial photography"}
    if "overlap" in r:
        return {"src": _brand_art(doc, "detail", *brand_default_art_names(doc, "detail")),
                "variant": "overlap", "absolute": True,
                "alt": f"{brand_name} detail photography"}
    if "eyebrow" in r:
        return {"text": usage.get("Text") or sc["eyebrow"]}
    if "action" in r or "cta" in r or "link" in r or "button" in r:
        return {"label": usage.get("Label")
                or (usage["label"] if "label" in usage else sc["cta"]),
                "accent": ctx.is_dark}
    # generic image / media fallback
    if "photo" in r or "image" in r or "media" in r:
        return {"src": _brand_art(doc, "hero", *brand_default_art_names(doc, "hero")),
                "variant": "hero",
                "alt": f"{brand_name} editorial photography"}
    return dict(usage)


# ── composition.v1 inline copy (fallback-safe) ──────────────────────────────────
# A composition.v1 slot binds INLINE copy from the brief; the adapter
# (compose_from_composition.py) folds that copy into the blockMapping entry's `usage`.
# These are the usage keys that signal inline copy the deterministic _props_for path does
# NOT already consume (it already reads usage.heading / usage.label). When one is present
# we build props directly from the inline copy so the generic-flow composer renders the
# composition's OWN copy; otherwise we fall back to _props_for unchanged — so the existing
# composed pages + A/B arms (whose usage never carries these keys) are byte-identical.
_INLINE_COPY_KEYS = ("text", "body", "caption", "eyebrow", "subheading",
                     "placeholder", "submit", "src", "alt")


def _has_inline_copy(usage) -> bool:
    return isinstance(usage, dict) and any(k in usage for k in _INLINE_COPY_KEYS)


def _inline_props(contract, role, usage, ctx):
    """Build shared-renderer props from a composition slot's inline copy (folded into
    `usage`). Returns None when the contract has no inline mapping (caller falls back to
    _props_for). Accent defaults to the surface (dark) but an explicit usage.accent wins so
    the adapter can keep the page's single committed accent."""
    u = usage or {}
    c = (contract or "").lower()
    accent = u.get("accent", ctx.is_dark)
    if c == "heading":
        text = u.get("text") or u.get("heading") or "Heading"
        return {"text": text, "heading": text, "level": u.get("level", "display"),
                "accent": accent, "splitTwoLines": u.get("splitTwoLines", False)}
    if c == "eyebrow":
        return {"text": u.get("text") or u.get("eyebrow") or ""}
    if c in ("paragraph", "subheading"):
        return {"text": u.get("text") or u.get("body") or u.get("subheading") or "",
                "measure": u.get("measure")}
    if c == "caption":
        return {"text": u.get("text") or u.get("caption") or ""}
    if c in ("link", "cta"):
        return {"label": u.get("label") or u.get("text") or u.get("cta") or "Learn more",
                "href": u.get("href", "#"), "accent": accent}
    if c == "button":
        # real action slot (B5): render_button dispatches on the brand's cta-shape
        # (filled button vs typographic downgrade); accent stays neutral by default.
        return {"label": u.get("label") or u.get("text") or u.get("cta") or "Get started",
                "href": u.get("href", "#"), "accent": u.get("accent", False)}
    if c == "image":
        return {"src": u.get("src"), "alt": u.get("alt", ""),
                "variant": u.get("variant", ""), "absolute": bool(u.get("absolute")),
                "aspect": u.get("aspect"),
                "placeholder": u.get("placeholder", "IMAGE / RADIUS 0")}
    if c == "logo":
        # IMAGE mode when the slot carries a disk-backed asset (AS-30: the payload is
        # unwrapped, never dropped — the old text-only branch discarded usage.src and
        # rendered SECTION_COPY's wordmark, five foreign-brand marks on a logo wall).
        if u.get("src") or u.get("img"):
            return {"src": u.get("src") or u.get("img"),
                    "alt": u.get("alt") or u.get("text") or "",
                    "variant": u.get("variant", "")}
        # inline copy carried no text: degrade to empty, never another brand's mark.
        return {"text": u.get("text") or ""}
    if c == "input":
        return {"placeholder": u.get("placeholder", "Your email"), "submit": u.get("submit")}
    if c == "header":
        return {"eyebrow": u.get("eyebrow"), "heading": u.get("heading", "Heading"),
                "level": u.get("level", "display"), "accent": accent, "cta": u.get("cta")}
    if c == "form":
        return {"eyebrow": u.get("eyebrow"), "heading": u.get("heading"),
                "placeholder": u.get("placeholder", "Your email"),
                "submit": u.get("submit") or u.get("cta") or "Subscribe"}
    return None


# v1-schema adapter (e.g. runs/hubspot, brand.yaml version "1.0"): v1 layouts carry
# `componentMapping` (real Webflow component names + props INCLUDING the section's real
# copy in Text/Label) instead of v2's `blockMapping` (contract keys). Normalize so the
# same composers serve both schemas — without this, a v1 brand's slots resolve empty and
# every composer falls back to its (WoodWave-flavored) default copy.
_V1_COMPONENT_CONTRACTS = {
    "heading": "header", "eyebrow": "eyebrow", "subheading": "paragraph",
    "paragraph": "paragraph", "rich text": "paragraph", "image": "image", "logo": "logo",
    "button / primary": "button", "button / secondary": "button", "button": "button",
    "link / primary": "link", "link / secondary": "link", "form / webflow / lead": "form",
}


def _effective_mappings(layout):
    """blockMapping (v2) verbatim, else componentMapping (v1) normalized to contracts."""
    bm = layout.get("blockMapping")
    if bm:
        return bm
    out = []
    for m in layout.get("componentMapping") or []:
        contract = _V1_COMPONENT_CONTRACTS.get(str(m.get("component") or "").lower())
        if not contract:
            continue
        out.append({"slot": m.get("slot"), "role": m.get("role"),
                    "contract": contract, "usage": dict(m.get("props") or {})})
    return out


def render_slots(doc, layout, ctx):
    """For every blockMapping entry, resolve the bound catalog component and render it
    through the shared renderer. Returns a list of {slot, role, contract, html}."""
    rendered = []
    for m in _effective_mappings(layout):
        contract = m.get("contract")
        renderer = cr.resolve_renderer(contract)
        entry = catalog_entry(doc, contract)
        usage = m.get("usage")
        props = None
        if _has_inline_copy(usage):
            props = _inline_props(contract, m.get("role"), usage, ctx)
        if props is None:
            props = _props_for(doc, layout, m.get("role"), usage, ctx)
        if renderer is None:
            # no shared renderer for this contract yet - record a typed gap, do not crash
            frag = f'<!-- unresolved slot: contract={contract} role={m.get("role")} -->'
        else:
            frag = renderer(doc, ctx, props)
        rendered.append({
            "slot": m.get("slot"), "role": m.get("role") or "", "contract": contract,
            "origin": (entry or {}).get("origin"), "html": frag,
        })
    return rendered


def _pick(rendered, *keywords):
    for r in rendered:
        role = r["role"].lower()
        if all(k in role for k in keywords) or any(k == r["contract"] for k in keywords):
            return r
    return None


# ── archetype: stack hero (opening-bookend) ──────────────────────────────────────

# z classes (composition.v1 §4.6.5) → concrete z-index INSIDE the layered hero collage.
# Ladder: back(0) < base media(1) < mid(2) < front(3) < display title(4) < corner(3, on
# the section frame). Matches the brand z-ladder (ghost → media → panels → text).
_Z_LAYER = {"back": 0, "mid": 2, "front": 3}

# default photography per layer kind (cycled for extra overlays) — generic role KINDS
# only; the concrete PREFERRED filenames are brand data (section-copy.yaml defaultArt:,
# via brand_default_art_names) resolved through _brand_art so they only apply when the
# file exists in the ACTIVE brand's inventory (AS-34); other brands resolve their OWN
# art (generic-kind keyword match) or render the srcless placeholder — never another
# brand's file.
_LAYER_KINDS = {"base": "hero", "background": "hero", "corner": "detail"}
_OVERLAY_KINDS = ["detail", "gallery", "gallery", "portrait"]


def _layer_fallback(doc, key: str) -> tuple:
    """(kind, preferred-names) for a named hero layer, from the brand's defaultArt."""
    kind = _LAYER_KINDS[key]
    return kind, brand_default_art_names(doc, kind)


def _overlay_fallback(doc, i: int) -> tuple:
    """(kind, preferred-names) for the i-th layered-hero overlay: the generic kind
    cycle + the brand's ordered ``defaultArt.overlays`` preference for that slot."""
    kind = _OVERLAY_KINDS[i % len(_OVERLAY_KINDS)]
    names = brand_default_art_names(doc, "overlays")
    preferred = [names[i % len(names)]] if names else []
    return kind, preferred


def _composer_art(doc, layout, kind: str) -> str | None:
    """Composer-level media fallback (media slot missing entirely): the brand's own
    ``layoutImages`` entry for THIS layout wins (its declared per-section photo),
    else its ``defaultArt`` preference for the generic *kind* — all evidence-checked
    via _brand_art; None (caller omits the device) when the brand carries no
    matching art."""
    li = brand_layout_images(doc).get((layout or {}).get("id")) or {}
    names = [v for v in li.values() if isinstance(v, str)]
    return _brand_art(doc, kind, *(names or brand_default_art_names(doc, kind)))


def _span_width_css(span, cols: int = 12) -> str:
    """A whole-column SPAN width on the shared registration grid (colSpan → real width):
    N columns + N-1 shared gutters, so both edges land on shared column lines."""
    try:
        s = max(1, min(int(span), cols))
    except (TypeError, ValueError):
        s = 4
    if s >= cols:
        return "100%"
    if s == 1:
        return "var(--col)"
    return f"calc({s} * var(--col) + {s - 1} * var(--grid-gutter, 6rem))"


def _overlay_style(layer: dict, idx: int) -> str:
    """Inline placement style for ONE registered overlay inside the layered collage.
    The declared registration (edge + depthCols/depthBaselines + z) resolves to grid-
    registered offsets — column-multiples across left/right edges, baseline-multiples
    across top/bottom — REPLACING the legacy magic % offsets wherever a registration is
    declared. Undeclared knobs keep the measured hero's baseline-rounded % defaults."""
    reg = layer.get("registration") or {}
    b = "var(--baseline)"
    colu = "(var(--col) + var(--grid-gutter, 6rem))"
    parts = [f"width: {_span_width_css(layer.get('colSpan') or 4)}"]

    def _num(v):
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    edge = str(reg.get("edge") or "bottom").lower()
    corner = str(((layer.get("alignTo") or {}) or {}).get("corner") or "").lower()
    if edge in ("left", "right"):
        d = _num(reg.get("depthCols"))
        depth = f"calc({d:g} * {colu})" if d is not None else f"round(nearest, 8%, {b})"
        parts.append(f"{edge}: calc(-1 * {depth})")
        ob = _num(layer.get("offsetBaselines"))
        parts.append(f"bottom: calc(-1 * {ob:g} * {b})" if ob is not None
                     else f"bottom: round(nearest, -18%, {b})")
    else:  # top | bottom (the measured hero's own overlap crosses the bottom edge)
        d = _num(reg.get("depthBaselines"))
        depth = f"calc({d:g} * {b})" if d is not None else f"round(nearest, 28%, {b})"
        parts.append(f"{edge if edge in ('top', 'bottom') else 'bottom'}: calc(-1 * {depth})")
        oc = _num(layer.get("offsetCols"))
        if oc is not None:
            parts.append(f"left: calc({oc:g} * {colu})")
        elif corner in ("tl", "bl") or (not corner and idx % 2 == 1):
            parts.append(f"left: round(nearest, 4%, {b})")
        else:
            parts.append(f"right: round(nearest, 4%, {b})")
    z = str(reg.get("z") or layer.get("z") or "front").lower()
    parts.append(f"z-index: {_Z_LAYER.get(z, 3)}")
    return "; ".join(parts)


def _layer_img(doc, ctx, layer: dict, *, variant: str, fallback) -> str:
    """One layered-hero image. `fallback` is a (kind, preferred-names) pair resolved
    through _brand_art — evidence-checked against the ACTIVE brand's inventory (AS-34);
    a brand with no matching art renders the srcless placeholder, never foreign art.
    Alt text derives from the ACTIVE brand's name (AS-29), never a brand literal."""
    kind, preferred = fallback
    src = layer.get("src") or _brand_art(doc, kind, *preferred)
    brand_name = (doc.get("brand") or {}).get("name") or "Brand"
    return cr.render_image(doc, ctx, {
        "src": src, "variant": variant, "aspect": layer.get("aspect"),
        "alt": layer.get("alt") or f"{brand_name} photography"})


def _stack_hero_layered(doc, ctx, layers: list[dict], *, eyebrow_html, title_html,
                        cta_html, subhead: str) -> str:
    """The PLACED hero body (grid/overlap contract): media layers classified by the
    adapter (compose_from_composition._media_layers) draw as a registered layer stack —
    an optional z:back full-bleed BACKGROUND behind the copy (sanctioned text-on-media;
    a flat surface-toned scrim keeps text contrast), a BASE collage image (colSpan-sized),
    registered OVERLAYS (edge + depth + z), and corner-pinned z:front media on the
    section frame. Every image is the shared c-image primitive; placement rides on
    per-instance inline styles resolved from the declared contract fields."""
    bg = next((l for l in layers if l["kind"] == "background"), None)
    base = next((l for l in layers if l["kind"] == "base"), None)
    overlays = [l for l in layers if l["kind"] == "overlay"]
    corners = [l for l in layers if l["kind"] == "corner"]

    bg_html = ""
    if bg is not None:
        img = _layer_img(doc, ctx, bg, variant="hero", fallback=_layer_fallback(doc, "background"))
        bg_html = (f'\n  <div class="cs-bg-layer" aria-hidden="true">{img}'
                   f'<div class="cs-bg-scrim"></div></div>')

    collage = ""
    if base is not None or overlays:
        base_img = _layer_img(doc, ctx, base, variant="hero",
                              fallback=_layer_fallback(doc, "base")) if base is not None else ""
        base_style = ""
        if base is not None and base.get("colSpan"):
            base_style = f' style="max-width: {_span_width_css(base["colSpan"])}"'
        ovs = "\n".join(
            f'      <div class="cs-ov" style="{_overlay_style(l, i)}">'
            f'{_layer_img(doc, ctx, l, variant="overlap", fallback=_overlay_fallback(doc, i))}</div>'
            for i, l in enumerate(overlays))
        collage = f"""    <div class="cs-collage cs-collage--layered"{base_style}>
      {base_img}
{ovs}
    </div>
    <div class="cs-spacer"></div>"""

    corner_html = ""
    for l in corners:
        c = str(((l.get("alignTo") or {}) or {}).get("corner") or "br").lower()
        x = "left" if c in ("tl", "bl") else "right"
        y = "top" if c in ("tl", "tr") else "bottom"
        img = _layer_img(doc, ctx, l, variant="overlap", fallback=_layer_fallback(doc, "corner"))
        corner_html += (f'\n  <div class="cs-corner-media" style="width: '
                        f'{_span_width_css(l.get("colSpan") or 3)}; '
                        f'{x}: var(--c-section-pad-x); '
                        f'{y}: calc(6 * var(--baseline)); z-index: 3">{img}</div>')

    return f"""<section class="cs-section cs-hero-layered">{bg_html}{corner_html}
  <div class="cs-slot">
    <div class="cs-eyebrow-wrap">{eyebrow_html}</div>
    <div class="cs-title">{title_html}</div>
{collage}
    <div class="cs-foot">
      <p class="cs-sub">{cr.esc(subhead)}</p>
      {cta_html}
    </div>
  </div>
</section>"""


def _hero_treatment_art(doc) -> str | None:
    """The brand's own MEASURED art-panel paint (brand.yaml `heroTreatment.value.asset`),
    as an ``assets/<name>`` src — only when the file actually exists in the ACTIVE
    brand's inventory (AS-34 disk evidence; a declared-but-absent file resolves None
    and the panel paints its plain surface instead)."""
    val = ((doc.get("heroTreatment") or {}).get("value") or {}) if isinstance(doc, dict) else {}
    name = val.get("asset")
    if not isinstance(name, str) or not name.strip():
        return None
    inv = doc.get(ASSET_INVENTORY_KEY) or []
    name = Path(name).name
    return f"assets/{name}" if name in inv else None


def _art_panel_permitted(style_ctx) -> bool:
    """STYLE-law gate for the inset art-panel device (AS-37 / remote-fix schema-gap 9):
    an ACTIVE style must declare `artPanel: inset` for the device to render (the
    hard-edged editorial styles say `none`, so a panel-averse style can never grow a
    rounded art panel). With no active style, the brand's own evidence (a declared
    art-panel treatment + a real asset) decides — brand grammar is not suppressed by
    a law nobody activated."""
    if not (style_ctx and getattr(style_ctx, "active", False)
            and getattr(style_ctx, "structure", None)):
        return True
    return (getattr(style_ctx.structure, "art_panel", None) or "none") == "inset"


def _stack_hero_art_panel(doc, ctx, layout, rendered, panel, *, title_html,
                          body_slot, cta_html, copy):
    """The INSET ART-PANEL hero body (schema-gap 9): the whole hero lives INSIDE one
    rounded panel painted with the brand's own art asset (noise/gradient/illustration
    fill — surface role, not photography): content column (title → body → actions)
    beside an optional media column. Geometry is generic; every measured value rides
    brand tokens (panel radius via --radius-panel → --radius chain, rhythm via the
    --c-* rhythm vars) and the art asset comes from the ACTIVE brand's inventory —
    never a literal, never another brand's file (AS-34)."""
    art = panel.get("asset") or _hero_treatment_art(doc)
    bg_style = f' style="background-image: url(\'{cr.esc(art)}\')"' if art else ""
    body_html = body_slot["html"] if body_slot else (
        f'<p class="cs-sub">{cr.esc(copy["subhead"])}</p>' if copy["subhead"] else "")
    media = next((r for r in rendered
                  if r.get("contract") == "image" and (r.get("html") or "").strip()), None)
    media_html = f'\n    <div class="cs-hero-panel-media">{media["html"]}</div>' \
        if media else ""
    mod = " cs-hero-panel--solo" if not media else ""
    return f"""<section class="cs-section cs-hero-panel-sec">
  <div class="cs-hero-panel{mod}"{bg_style}>
    <div class="cs-hero-panel-content">
      <div class="cs-title">{title_html}</div>
      {body_html}
      {cta_html}
    </div>{media_html}
  </div>
</section>"""


def compose_stack_hero(doc, layout, ctx, rendered, style_ctx):
    """Assemble the resolved catalog fragments into the opening-bookend stack scaffold:
    nav -> [eyebrow -> display title over media-over-media collage] -> subhead + cta.
    Positions/overlap come from the layout's grid/overlap rules; every visible piece is
    a catalog component rendered by component_render (no bespoke element markup here).
    COPY IS PER-SECTION (copy_for merges LAYOUT_COPY[this id] over the SECTION_COPY
    base) — the old page-global SECTION_COPY read meant the FIRST hero's copy won on
    every hero of a multi-hero page (ANCHORED-REPORT composer-gap #1).
    When the adapter classified PLACED media layers (layout['_mediaLayers'], §4.6.5),
    the media draws via the layered path; otherwise the measured default geometry is
    byte-identical."""
    copy = copy_for(layout, doc)
    title = _pick(rendered, "title") or _pick(rendered, "heading")

    # The navbar is NO LONGER rendered here: it used to live INSIDE this hero #section, so it
    # inherited the hero's padding-block-start (an uncommon large gap above the nav). It is
    # now hoisted to a PAGE-LEVEL sibling emitted once by compose_page.build_page BEFORE
    # #sec-0 (mirroring the footer), so the final structure is Page > { Nav, Section(s),
    # Footer } and the hero top padding normalizes to the normal section rhythm.
    # eyebrow / subhead / cta PREFER the layout's own resolved slots (v1 layouts carry
    # real copy in componentMapping props); copy_for is the fallback, not the default.
    eyebrow_slot = _pick(rendered, "eyebrow") or _pick(rendered, "tagline")
    body_slot = _pick(rendered, "supporting") or _pick(rendered, "paragraph")
    cta_slot = _pick(rendered, "cta") or _pick(rendered, "button") or _pick(rendered, "action")
    eyebrow_html = eyebrow_slot["html"] if eyebrow_slot else \
        cr.render_eyebrow(doc, ctx, {"text": copy["eyebrow"]})
    # brand-name fallback passes through AS AUTHORED (AS-39) — display casing is the
    # brand's case token on the heading register, never a Python .upper() restyle.
    title_html = title["html"] if title else cr.render_heading(doc, ctx, {
        "text": (doc.get("brand") or {}).get("name") or "Brand",
        "accent": ctx.is_dark, "splitTwoLines": True})
    # HERO ACTIONS are law-first (AS-27 extended to the hero path, remote-fix blocker-3):
    # real `button` contract slots render through render_button's cta-shape dispatch —
    # a `never-typographic-primary` brand gets its measured filled pill(s), a typographic
    # brand's dispatch downgrades the same slots to arrow links. Only with NO bound
    # action slot does the legacy copy-driven arrow link render (the WoodWave default:
    # the accent stays reserved for logo/eyebrow + display title, so the section carries
    # exactly ONE accent element — the composition single-accent invariant).
    action_frags = [r["html"] for r in rendered
                    if r.get("contract") == "button" and (r.get("html") or "").strip()]
    if action_frags:
        cta_html = f'<div class="cs-hero-actions">{"".join(action_frags)}</div>'
    elif cta_slot:
        cta_html = cta_slot["html"]
    else:
        cta_html = cr.render_arrow_link(doc, ctx, {"label": copy["cta"], "accent": False})

    panel = layout.get("_artPanel")
    if panel is not None and _art_panel_permitted(style_ctx):
        return _stack_hero_art_panel(doc, ctx, layout, rendered, panel,
                                     title_html=title_html, body_slot=body_slot,
                                     cta_html=cta_html, copy=copy)

    layers = layout.get("_mediaLayers")
    if layers:
        return _stack_hero_layered(doc, ctx, layers, eyebrow_html=eyebrow_html,
                                   title_html=title_html, cta_html=cta_html,
                                   subhead=copy["subhead"])

    hero_media = _pick(rendered, "hero", "photo") or _pick(rendered, "hero")
    overlap_media = _pick(rendered, "overlap")
    hero_html = hero_media["html"] if hero_media else ""
    overlap_html = overlap_media["html"] if overlap_media else ""

    collage = f"""    <div class="cs-collage">
      {hero_html}
      {overlap_html}
    </div>
    <div class="cs-spacer"></div>"""

    body = f"""<section class="cs-section">
  <div class="cs-slot">
    <div class="cs-eyebrow-wrap">{eyebrow_html}</div>
    <div class="cs-title">{title_html}</div>
{collage}
    <div class="cs-foot">
      {body_slot["html"] if body_slot else f'<p class="cs-sub">{cr.esc(copy["subhead"])}</p>'}
      {cta_html}
    </div>
  </div>
</section>"""
    return body


# ── archetype: editorial collage (about-run) ─────────────────────────────────────

def compose_editorial_collage(doc, layout, ctx, rendered, style_ctx):
    """Assemble the cream editorial-collage: an oversized ghost watermark behind a loose,
    left-anchored module of [eyebrow + display heading] + [hard-edged media w/ margin
    caption] + offset narrow paragraph + arrow link. z-order ghost -> media -> text.
    Every visible piece is a catalog component (header/image/caption/paragraph/link)."""
    copy = copy_for(layout, doc)
    media = _pick(rendered, "media") or _pick(rendered, "image")
    _brand_name = (doc.get("brand") or {}).get("name") or "Brand"
    media_html = media["html"] if media else cr.render_image(
        doc, ctx, {"src": _composer_art(doc, layout, "detail"),
                   "variant": "overlap",
                   "alt": f"{_brand_name} detail photography"})
    header_html = cr.render_header(doc, ctx, {
        "eyebrow": copy["eyebrow"], "heading": copy["heading"], "level": "display",
        "accent": ctx.is_dark, "splitTwoLines": False})
    caption_html = cr.render_caption(doc, ctx, {"text": copy["caption"]})
    body_html = cr.render_paragraph(doc, ctx, {"text": copy["body"], "measure": "34ch"})
    # GATE-COMPLIANT accent deployment (ANCHORED-REPORT composer-gap #3 fix): on a dark
    # surface the heading carries the section's ONE accent, so the arrow link stays
    # neutral ink — the old `accent: ctx.is_dark` on BOTH was a guaranteed double-accent
    # FAIL for every dark collage. Cream surfaces are byte-unchanged (both were False).
    cta_html = cr.render_arrow_link(doc, ctx, {"label": copy["cta"], "accent": False})
    ghost = cr.esc(copy["ghost"])
    return f"""<section class="cs-section cs-collage-sec">
  <div class="cs-collage-grid">
    <div class="cs-ghost" aria-hidden="true">{ghost}</div>
    <div class="cs-collage-head">{header_html}</div>
    <figure class="cs-collage-media">
      <div class="c-image-mask">{media_html}</div>
      {caption_html}
    </figure>
    <div class="cs-collage-body">
      {body_html}
      {cta_html}
    </div>
  </div>
</section>"""


# ── archetype: heritage timeline (collage variant — GHOST NUMERALS, not a word) ──

def compose_heritage_timeline(doc, layout, ctx, rendered, style_ctx):
    """Assemble the heritage/collection-timeline collage: reuses editorial-collage's
    ghost-watermark-behind-media grammar, but the watermark is a YEAR RANGE (numerals),
    and TWO dated captions mark specific acquisitions instead of one margin caption."""
    copy = copy_for(layout, doc)
    media = _pick(rendered, "heritage photography") or _pick(rendered, "media") or _pick(rendered, "image")
    _brand_name = (doc.get("brand") or {}).get("name") or "Brand"
    media_html = media["html"] if media else cr.render_image(
        doc, ctx, {"src": _composer_art(doc, layout, "gallery"),
                   "variant": "overlap",
                   "alt": f"{_brand_name} heritage photography"})
    header_html = cr.render_header(doc, ctx, {
        "eyebrow": copy["eyebrow"], "heading": copy["heading"], "level": "display",
        "accent": ctx.is_dark, "splitTwoLines": False})
    caption_html = cr.render_caption(doc, ctx, {"text": copy["caption"]})
    body_html = cr.render_paragraph(doc, ctx, {"text": copy["body"], "measure": "34ch"})
    ghost = cr.esc(copy["ghost"])
    return f"""<section class="cs-section cs-collage-sec cs-timeline-sec">
  <div class="cs-collage-grid">
    <div class="cs-ghost cs-ghost--numerals" aria-hidden="true">{ghost}</div>
    <div class="cs-collage-head">{header_html}</div>
    <figure class="cs-collage-media">
      <div class="c-image-mask">{media_html}</div>
      {caption_html}
    </figure>
    <div class="cs-collage-body">
      {body_html}
    </div>
  </div>
</section>"""


def _pattern_id(layout):
    """The layout's resolved patternRef id (the REUSABLE pattern identity), or None.
    Archetype dispatchers key off this FIRST — dispatching on the layout's own id alone
    is fragile: a NEW layout instance reusing an EXISTING pattern (the whole point of the
    pattern library) would silently fall through to the wrong composer, as happened when
    `exhibition-curator-quote` (patternRef curator-quote-portrait-collage) wasn't in the
    old id-only check list and crashed in compose_info_band instead."""
    ref = (layout or {}).get("patternRef")
    return ref.get("id") if isinstance(ref, dict) else None


def compose_collage(doc, layout, ctx, rendered, style_ctx):
    """`collage` archetype dispatcher: WoodWave has two collage-family sections — the
    editorial about-run (ghost WORD) and the heritage timeline (ghost NUMERALS).
    Disambiguate by patternRef FIRST (any layout reusing the timeline pattern), falling
    back to the legacy id check; default to editorial so about-run stays unchanged."""
    pid = _pattern_id(layout)
    if pid == "heritage-ghost-numerals-timeline" or (layout or {}).get("id") == "heritage-timeline":
        return compose_heritage_timeline(doc, layout, ctx, rendered, style_ctx)
    return compose_editorial_collage(doc, layout, ctx, rendered, style_ctx)


# ── archetype: split info-band (info-band) ───────────────────────────────────────

def compose_info_band(doc, layout, ctx, rendered, style_ctx):
    """Assemble the dark info-band split: a flush hard-edged photo half | a cream panel
    half (the only cream-on-dark surface) carrying a didone H3 title + 1px-ruled action
    rows + an arrow link. Two flush halves, gap 0, hard cut. The panel keeps cream/ink
    coloring regardless of the inverse parent (its own --c-* scope on .cs-panel)."""
    copy = copy_for(layout, doc)
    media = _pick(rendered, "photo") or _pick(rendered, "image") or _pick(rendered, "media")
    _brand_name = (doc.get("brand") or {}).get("name") or "Brand"
    media_html = media["html"] if media else cr.render_image(
        doc, ctx, {"src": _composer_art(doc, layout, "hero"),
                   "variant": "hero",
                   "alt": f"{_brand_name} editorial photography"})
    title_html = cr.render_heading(doc, ctx, {
        "text": copy["panelTitle"], "level": "h3"})
    rows = "".join(
        f'<div class="c-row"><span class="c-row-label">{cr.esc(lbl)}</span>'
        f'<span class="c-row-value">{cr.esc(val)}</span></div>'
        for lbl, val in copy.get("rows", []))
    cta_html = cr.render_arrow_link(doc, ctx, {"label": copy["cta"]})
    eyebrow_html = cr.render_eyebrow(doc, ctx, {"text": copy["eyebrow"]})
    # The dark info-band heading uses the brand's DIDONE DISPLAY tier (same family/scale
    # logic as the hero + collage headings), NOT a small h2 — on the dark inverse surface
    # it reads in paper/white (var(--c-ink) = text/on-inverse), accent reserved for the
    # hero. (Fix: the prior h2 looked undersized/off-style on the dark band.)
    band_heading = cr.render_heading(doc, ctx, {
        "text": copy["heading"], "level": "display", "accent": False})
    return f"""<section class="cs-section cs-split-sec">
  <div class="cs-split-intro">
    <div class="cs-eyebrow-wrap">{eyebrow_html}</div>
    {band_heading}
  </div>
  <div class="cs-split">
    <div class="cs-split-media"><div class="c-image-mask">{media_html}</div></div>
    <div class="cs-panel">
      <div class="cs-panel-title">{title_html}</div>
      <div class="c-rows">{rows}</div>
      <div class="cs-panel-foot">{cta_html}</div>
    </div>
  </div>
</section>"""


# ── archetype: mission statement (split variant — plain anchored, no ghost word) ─

def compose_about_statement(doc, layout, ctx, rendered, style_ctx):
    """Assemble the mission-statement: the PLAIN sibling of the editorial collage — an
    anchored text column (eyebrow -> display heading -> body -> arrow action) beside a
    single flush media panel. No ghost watermark; alternates anchor per the stagger rule."""
    copy = copy_for(layout, doc)
    media = _pick(rendered, "statement photography") or _pick(rendered, "media") or _pick(rendered, "image")
    _brand_name = (doc.get("brand") or {}).get("name") or "Brand"
    media_html = media["html"] if media else cr.render_image(
        doc, ctx, {"src": _composer_art(doc, layout, "gallery"),
                   "variant": "hero",
                   "alt": f"{_brand_name} gallery interior"})
    header_html = cr.render_header(doc, ctx, {
        "eyebrow": copy["eyebrow"], "heading": copy["heading"], "level": "display",
        "accent": ctx.is_dark, "splitTwoLines": False})
    body_html = cr.render_paragraph(doc, ctx, {"text": copy["body"], "measure": "50ch"})
    cta_html = cr.render_arrow_link(doc, ctx, {"label": copy["cta"], "accent": ctx.is_dark})
    return f"""<section class="cs-section cs-statement-sec">
  <div class="cs-statement-grid">
    <div class="cs-statement-text">
      {header_html}
      {body_html}
      {cta_html}
    </div>
    <div class="cs-statement-media"><div class="c-image-mask">{media_html}</div></div>
  </div>
</section>"""


# ── archetype: curator quote with portrait (split variant) ──────────────────────

def compose_curator_quote(doc, layout, ctx, rendered, style_ctx):
    """Assemble the curator-quote module: a heading-scale quote (didone serif, quotation
    marks kept) beside a hard-edged portrait, with a short name caption in the margin."""
    copy = copy_for(layout, doc)
    media = _pick(rendered, "curator portrait") or _pick(rendered, "media") or _pick(rendered, "image")
    # alt derives from the section's OWN attribution copy (never a hardcoded name).
    _who = copy["caption"] or (doc.get("brand") or {}).get("name") or "Portrait"
    media_html = media["html"] if media else cr.render_image(
        doc, ctx, {"src": _composer_art(doc, layout, "portrait"),
                   "variant": "overlap",
                   "alt": f"{_who}, curator"})
    eyebrow_html = cr.render_eyebrow(doc, ctx, {"text": copy["eyebrow"]})
    quote_html = cr.render_heading(doc, ctx, {
        "text": copy["quote"], "level": "display", "accent": False, "splitTwoLines": False})
    body_html = cr.render_paragraph(doc, ctx, {"text": copy["body"], "measure": "48ch"})
    caption_html = cr.render_caption(doc, ctx, {"text": copy["caption"]})
    return f"""<section class="cs-section cs-quote-sec">
  <div class="cs-quote-grid">
    <div class="cs-quote-text">
      <div class="cs-eyebrow-wrap">{eyebrow_html}</div>
      {quote_html}
      {body_html}
    </div>
    <figure class="cs-quote-media">
      <div class="c-image-mask">{media_html}</div>
      {caption_html}
    </figure>
  </div>
</section>"""


# ── archetype: visit band (split variant — TWO panels over a static map) ─────────

def compose_visit_band(doc, layout, ctx, rendered, style_ctx):
    """Assemble the fuller visit-info band: an intro heading over a static desaturated
    map graphic, overlapped by TWO cream panels (ticket prices + hours/address). Panels
    keep cream/ink coloring regardless of the inverse parent, same as info-band's panel."""
    copy = copy_for(layout, doc)
    media = _pick(rendered, "static map") or _pick(rendered, "media") or _pick(rendered, "image")
    # alt derives from the section's OWN map caption copy (never a hardcoded place name).
    media_html = media["html"] if media else cr.render_image(
        doc, ctx, {"src": _composer_art(doc, layout, "map"), "variant": "hero",
                   "alt": f"Map — {copy['mapCaption']}".rstrip(" —")})
    eyebrow_html = cr.render_eyebrow(doc, ctx, {"text": copy["eyebrow"]})
    band_heading = cr.render_heading(doc, ctx, {
        "text": copy["heading"], "level": "display", "accent": False})
    caption_html = cr.render_caption(doc, ctx, {"text": copy["mapCaption"]})

    tickets_title = cr.render_heading(doc, ctx, {"text": copy["ticketsTitle"], "level": "h3"})
    tickets_rows = "".join(
        f'<div class="c-row"><span class="c-row-label">{cr.esc(lbl)}</span>'
        f'<span class="c-row-value">{cr.esc(val)}</span></div>'
        for lbl, val in copy.get("ticketsRows", []))
    tickets_cta = cr.render_arrow_link(doc, ctx, {"label": copy["ticketsCta"]})

    visit_title = cr.render_heading(doc, ctx, {"text": copy["visitTitle"], "level": "h3"})
    visit_rows = "".join(
        f'<div class="c-row"><span class="c-row-label">{cr.esc(lbl)}</span></div>'
        for lbl, _val in copy.get("visitRows", []))
    visit_cta = cr.render_arrow_link(doc, ctx, {"label": copy["visitCta"]})

    return f"""<section class="cs-section cs-visit-sec">
  <div class="cs-split-intro">
    <div class="cs-eyebrow-wrap">{eyebrow_html}</div>
    {band_heading}
  </div>
  <div class="cs-visit-grid">
    <figure class="cs-visit-media">
      <div class="c-image-mask">{media_html}</div>
      {caption_html}
    </figure>
    <div class="cs-visit-panels">
      <div class="cs-panel">
        <div class="cs-panel-title">{tickets_title}</div>
        <div class="c-rows">{tickets_rows}</div>
        <div class="cs-panel-foot">{tickets_cta}</div>
      </div>
      <div class="cs-panel">
        <div class="cs-panel-title">{visit_title}</div>
        <div class="c-rows">{visit_rows}</div>
        <div class="cs-panel-foot">{visit_cta}</div>
      </div>
    </div>
  </div>
</section>"""


def compose_split(doc, layout, ctx, rendered, style_ctx):
    """`split` archetype dispatcher: WoodWave has four split-family sections — the dark
    info-band, the plain mission statement, the curator quote, and the fuller visit band.
    Disambiguate by patternRef FIRST (so ANY layout reusing an existing pattern routes
    correctly, e.g. exhibition-curator-quote reusing curator-quote-portrait-collage),
    falling back to the legacy id check; default to info-band so its render is unchanged."""
    pid = _pattern_id(layout)
    lid = (layout or {}).get("id")
    if pid == "about-anchored-statement" or lid == "mission-statement":
        return compose_about_statement(doc, layout, ctx, rendered, style_ctx)
    if pid == "curator-quote-portrait-collage" or lid == "curator-quote":
        return compose_curator_quote(doc, layout, ctx, rendered, style_ctx)
    if pid == "visit-dual-panel-map" or lid == "visit-band":
        return compose_visit_band(doc, layout, ctx, rendered, style_ctx)
    return compose_info_band(doc, layout, ctx, rendered, style_ctx)


# ── archetype: gallery showcase (stack-fullbleed — full-bleed photo, static counter) ─

def compose_gallery_showcase(doc, layout, ctx, rendered, style_ctx):
    """Assemble the gallery interior showcase: a single full-bleed photograph, no overlay
    text/controls, framed by a thin utility row (eyebrow far left, static counter far
    right) and a margin caption below. NOT a slider — the counter is a static label.

    #sec-1 dropped-heading fix (AS-18 companion): a hero routed through this archetype
    (e.g. `hero-centered-stack-on-media` -> stack-fullbleed) declares heading/body/cta
    copy that this composer used to silently DROP. When the LAYOUT-layer copy carries
    them (read from the layout layer directly, NOT the base-merged copy_for(), so
    legacy gallery bands stay byte-identical), a display header block renders above the
    photograph and an arrow link below the caption."""
    copy = copy_for(layout, doc)
    media = _pick(rendered, "interior photography") or _pick(rendered, "media") or _pick(rendered, "image")
    _brand_name = (doc.get("brand") or {}).get("name") or "Brand"
    media_html = media["html"] if media else cr.render_image(
        doc, ctx, {"src": _composer_art(doc, layout, "gallery"),
                   "variant": "hero",
                   "alt": f"{_brand_name} gallery interior"})
    eyebrow_html = cr.render_eyebrow(doc, ctx, {"text": copy["eyebrow"]})
    counter_html = cr.render_caption(doc, ctx, {"text": copy["counter"]})
    caption_html = cr.render_caption(doc, ctx, {"text": copy["caption"]})
    lc = layout_copy_layer(layout, doc)
    head = ""
    if lc.get("heading"):
        head_html = cr.render_header(doc, ctx, {
            "eyebrow": "", "heading": lc["heading"], "level": "display",
            "accent": ctx.is_dark})
        body_html = cr.render_paragraph(
            doc, ctx, {"text": lc["body"], "measure": "44ch"}) if lc.get("body") else ""
        head = f"""
  <div class="cs-gallery-head cs-slot">
    {head_html}
    {body_html}
  </div>"""
    cta = ""
    acts = [a for a in (lc.get("actions") or []) if isinstance(a, dict) and a.get("label")]
    if lc.get("heading") and acts:
        # real action slots (B5): the PRIMARY renders through render_button (filled for a
        # filled-CTA brand, typographic downgrade otherwise); companions stay arrow links.
        frags = [cr.render_button(doc, ctx, {"label": acts[0].get("label"),
                                             "href": acts[0].get("href", "#"),
                                             "accent": False})]
        frags += [cr.render_arrow_link(doc, ctx, {"label": a.get("label"),
                                                  "href": a.get("href", "#"),
                                                  "accent": False}) for a in acts[1:]]
        cta = f"""
  <div class="cs-gallery-cta cs-foot">{''.join(frags)}</div>"""
    elif lc.get("heading") and lc.get("cta"):
        cta_html = cr.render_arrow_link(doc, ctx, {"label": lc["cta"], "accent": False})
        cta = f"""
  <div class="cs-gallery-cta cs-foot">{cta_html}</div>"""
    return f"""<section class="cs-section cs-gallery-sec">
  <div class="cs-gallery-utility">
    <span class="cs-gallery-eyebrow">{eyebrow_html}</span>
    <span class="cs-gallery-counter">{counter_html}</span>
  </div>{head}
  <figure class="cs-gallery-media">
    <div class="c-image-mask">{media_html}</div>
  </figure>
  <div class="cs-gallery-caption">{caption_html}</div>{cta}
</section>"""


# ── archetype: conversion stack (conversion, narrow centered/anchored) ───────────

def compose_conversion_stack(doc, layout, ctx, rendered, style_ctx):
    """Assemble the cream conversion stack: a CENTERED narrow column (~50% container) — one
    of only two sanctioned centered stacks (with the hero) — of eyebrow -> full display-
    scale (H1) heading -> short body -> underline form (placeholder + inline arrow submit)
    spanning the full column width. No boxed inputs, no filled button.
    (Fix: level was hardcoded to the small h2 tier and the column was never actually
    centered — the pattern recorded `align: center` as intent but nothing implemented it,
    which is why the render came out small and left-anchored against the source reference.)

    ACTION SLOTS (B5, fix-batch 2026-07): when the section's mapping binds real `button`
    contracts (a filled-CTA brand's conversion grammar), the composer renders THOSE
    actions — via render_button's cta-shape dispatch — instead of inventing a signup
    form the composition never declared. A mapping with no button slots keeps the
    legacy copy-driven form path byte-identical (every existing WoodWave conversion)."""
    copy = copy_for(layout, doc)
    header_html = cr.render_header(doc, ctx, {
        "eyebrow": copy["eyebrow"], "heading": copy["heading"], "level": "display",
        "accent": ctx.is_dark})
    body_html = cr.render_paragraph(doc, ctx, {"text": copy["body"], "measure": "40ch"})
    action_frags = [r["html"] for r in rendered
                    if r.get("contract") == "button" and (r.get("html") or "").strip()]
    if action_frags:
        has_form_slot = any(r.get("contract") == "form" for r in rendered)
        form_html = cr.render_form(doc, ctx, {
            "placeholder": copy["placeholder"], "submit": copy["cta"]}) if has_form_slot else ""
        actions_html = f'\n    <div class="cs-conversion-actions">{"".join(action_frags)}</div>'
    else:
        form_html = cr.render_form(doc, ctx, {
            "placeholder": copy["placeholder"], "submit": copy["cta"]})
        actions_html = ""
    return f"""<section class="cs-section cs-conversion-sec">
  <div class="cs-conversion">
    {header_html}
    {body_html}{actions_html}
    {form_html}
  </div>
</section>"""


# ── archetype: cards (staggered caption cards — features-staggered-caption-cards) ──

def compose_features_cards(doc, layout, ctx, rendered, style_ctx):
    """Assemble the multi-module STAGGERED CAPTION CARDS section (Claude Design #04,
    harvested as `features-staggered-caption-cards`). Renders an optional eyebrow+heading
    intro, then N (2–3) repeating MODULES — each a module PHOTO + a tracked uppercase
    CAPTION + a short BODY (+ an optional typographic ARROW link, NEVER a pill/button) — on
    an uneven grid (grid-template-columns from the pattern's --c-column-ratio) with the even
    modules pushed down by --c-card-stagger (a cq block offset) so the columns never line
    up. Every visible piece is a catalog component rendered by component_render; the
    offset/ratio come from the reused pattern's treatment/knob CSS vars. Hard-edged: no
    radius/shadow, cq/rem units only, brand tokens + the style spacing scale for rhythm."""
    copy = copy_for(layout, doc)
    cards = copy.get("cards") or []
    # default assets + alternating aspect ratios: the pattern says "vary aspect between
    # cards"; the harvested 16/10 · 4/3 render as landscape/cover aspect-ratio boxes.
    # Defaults are EVIDENCE-CHECKED against the ACTIVE brand's inventory (AS-34): a
    # brand without matching art renders the srcless placeholder, never foreign art.
    _assets = [_brand_art(doc, "hero", *brand_default_art_names(doc, "hero")),
               _brand_art(doc, "detail", *brand_default_art_names(doc, "detail"))]
    _aspects = ["16 / 10", "4 / 3"]
    brand_name = (doc.get("brand") or {}).get("name") or "Brand"
    modules = []
    for i, card in enumerate(cards):
        # asset may be a bare name, an already-prefixed path, or a sanitized {src, alt}
        # dict (fix-batch 2026-07, N1-asset: interpolating the dict produced the literal
        # `assets/{'src': …}` path the fidelity gate flagged). Alt resolves from the
        # asset metadata, else the module caption + brand name — never a foreign-brand
        # literal baked into the composer.
        raw = card.get("asset")
        alt = card.get("alt")
        if isinstance(raw, dict):
            alt = alt or raw.get("alt")
            raw = raw.get("src")
        if raw:
            src = raw if str(raw).startswith(("assets/", "http://", "https://", "data:")) \
                else f"assets/{raw}"
        else:
            src = _assets[i % len(_assets)]
        if not alt:
            cap = (card.get("caption") or "").strip()
            alt = f"{brand_name} — {cap}" if cap else f"{brand_name} photography"
        aspect = card.get("aspect") or _aspects[i % len(_aspects)]
        img_html = cr.render_image(doc, ctx, {"src": src, "alt": alt})
        caption_html = cr.render_caption(doc, ctx, {"text": card.get("caption", "")})
        body_html = cr.render_paragraph(doc, ctx, {"text": card.get("body", ""), "measure": "44ch"})
        link_html = cr.render_arrow_link(doc, ctx, {"label": card["link"]}) if card.get("link") else ""
        modules.append(
            f'    <article class="cs-module">\n'
            f'      <figure class="cs-module-media" style="aspect-ratio: {cr.esc(aspect)};">{img_html}</figure>\n'
            f'      {caption_html}\n      {body_html}\n      {link_html}\n    </article>')
    intro = ""
    if copy.get("heading"):
        header_html = cr.render_header(doc, ctx, {
            "eyebrow": copy.get("eyebrow"), "heading": copy["heading"], "level": "display",
            "accent": ctx.is_dark, "splitTwoLines": False})
        intro = f'<div class="cs-modules-intro">{header_html}</div>\n  '
    return f"""<section class="cs-section cs-modules-sec">
  {intro}<div class="cs-modules">
{chr(10).join(modules)}
  </div>
</section>"""


# ── archetype: interlock (float-wrap statement + inset — editorial-interlocking-inset) ──

def compose_editorial_interlock(doc, layout, ctx, rendered, style_ctx):
    """Assemble the INTERLOCKING STATEMENT + INSET IMAGE section (Claude Design #11,
    harvested as `editorial-interlocking-inset`). A two-line tracked CAPTION pins the
    top-left, one landscape IMAGE floats into the upper-right (float side + width from the
    pattern's --c-float-side / --c-inset-width), and a long serif STATEMENT heading WRAPS
    around it — narrow beside the image, then full width beneath (the caption carries a big
    --c-inset-drop bottom margin so the headline's first lines sit level with the image).
    A float-wrap mechanism — DISTINCT from the ghost-word collage. Image + heading + caption
    are all catalog components (component_render); no radius/shadow, cq/rem units only."""
    copy = copy_for(layout, doc)
    raw = copy.get("asset")
    src = raw if str(raw or "").startswith("assets/") \
        else (f"assets/{raw}" if raw else _composer_art(doc, layout, "hero"))
    _brand_name = (doc.get("brand") or {}).get("name") or "Brand"
    img_html = cr.render_image(doc, ctx, {
        "src": src, "alt": copy.get("alt") or f"{_brand_name} photography",
        "aspect": copy.get("mediaAspectCss")})
    # two-line caption built on the c-caption primitive class (SSOT), <br> between lines.
    cap_lines = "<br>".join(cr.esc(ln) for ln in str(copy.get("caption", "")).split("\n") if ln.strip())
    statement_html = cr.render_heading(doc, ctx, {
        "text": copy.get("statement", ""), "level": "display", "tag": "h2"})
    # SUPPORT + CTA slots (ANCHORED-REPORT composer-gap #2 fix): the composer used to
    # silently DROP these; a composition that binds them now gets an interlock foot
    # cluster after the float clears. Read from the LAYOUT layer only (never the
    # page-global base, whose always-present `cta` would retro-add a CTA to every
    # existing interlock render) — so legacy sections stay byte-identical.
    lc = layout_copy_layer(layout, doc)
    support_html = cr.render_paragraph(doc, ctx, {"text": lc["support"], "measure": "44ch"}) \
        if lc.get("support") else ""
    cta_html = cr.render_arrow_link(doc, ctx, {"label": lc["cta"], "accent": False}) \
        if lc.get("cta") else ""
    foot = ""
    if support_html or cta_html:
        foot = f"""
    <div class="cs-interlock-foot">
      {support_html}
      {cta_html}
    </div>"""
    return f"""<section class="cs-section cs-interlock-sec">
  <div class="cs-interlock">
    <figure class="cs-interlock-media">{img_html}</figure>
    <p class="c-caption cs-interlock-caption">{cap_lines}</p>
    {statement_html}
    <div class="cs-interlock-clear"></div>{foot}
  </div>
</section>"""


# ── archetype: generic-flow (graceful fallback for a novel/unmapped archetype) ────

def compose_generic_flow(doc, layout, ctx, rendered, style_ctx):
    """Graceful fallback composer: render the section's resolved slot fragments in a sane
    left-anchored STACKED flow. Registered under ``generic-flow`` so a ``novelty: novel``
    composition section whose (renderer) archetype has no bespoke composer degrades
    gracefully — every slot still renders through the shared component_render primitives
    (so the output stays gate-safe: c-* vocabulary, no bespoke markup) — instead of the
    dispatch falling through to the hero and mis-rendering. Media slots flow full-measure;
    text slots stack with the block-gap rhythm. Hard-edged, cq/rem units only.

    LOGO-STRIP DEVICE (AS-33): mapping entries the adapter routed to the image device
    (slot="logo-strip", contract=logo, disk-backed src) group into ONE horizontal
    ``.cs-logo-strip`` row at the first entry's position; text-fallback logo items stay
    ordinary caption flow items. A ``_logoWall`` layout stamps the RESOLVED device on the
    section element (``data-logo-device="image|text|empty"``) so the gate can verify the
    section carries either real images or real text — never an empty frame."""
    parts: list[str | None] = []
    strip_items: list[str] = []
    strip_pos: int | None = None
    logo_text_items = 0
    for r in rendered:
        frag = r.get("html") or ""
        if not frag.strip() or "unresolved slot" in frag:
            continue
        role = (r.get("role") or "").lower()
        if r.get("slot") == "logo-strip" and r.get("contract") == "logo":
            if strip_pos is None:
                strip_pos = len(parts)
                parts.append(None)  # placeholder — replaced by the grouped strip below
            strip_items.append(f'      <div class="cs-logo-strip-item">{frag}</div>')
            continue
        if role == "logo item":
            logo_text_items += 1
        is_media = ("image" == r.get("contract")) or any(
            k in role for k in ("photo", "media", "image"))
        cls = "cs-flow-media" if is_media else "cs-flow-item"
        parts.append(f'    <div class="{cls}">{frag}</div>')
    if strip_pos is not None:
        parts[strip_pos] = ('    <div class="cs-logo-strip">\n'
                            + "\n".join(strip_items) + "\n    </div>")
    body = "\n".join(p for p in parts if p is not None) \
        or '    <!-- generic-flow: no renderable slots -->'
    device_attr = ""
    if layout.get("_logoWall"):
        mode = "image" if strip_items else ("text" if logo_text_items else "empty")
        device_attr = f' data-logo-device="{mode}"'
    return f"""<section class="cs-section cs-flow-sec"{device_attr}>
  <div class="cs-flow">
{body}
  </div>
</section>"""


# ── archetype: ruled-list panel (exhibition tickets/pricing + schedule/dates) ────

def compose_ruled_list_panel(doc, layout, ctx, rendered, style_ctx):
    """Assemble a centered eyebrow -> heading (+ optional intro line) -> flat list of
    ruled label/value rows -> optional arrow action. Reuses the SAME ruled-row primitive
    (.c-rows/.c-row, already shared/styled in COMPONENT_CSS) already extracted for the
    ticket/hours panels — shared by the exhibition TICKETS and SCHEDULE sections, promoted
    on a genuine miss (layout-library.yaml pricing-ruled-list-panel /
    schedule-ruled-list-panel): the standard library's card-based pricing patterns were
    rejected by the brand's own no-cards-on-cream neverDo during retrieval."""
    copy = copy_for(layout, doc)
    eyebrow_html = cr.render_eyebrow(doc, ctx, {"text": copy["eyebrow"]})
    heading_html = cr.render_heading(doc, ctx, {
        "text": copy["heading"], "level": "display", "accent": False})
    intro_html = cr.render_paragraph(doc, ctx, {"text": copy["intro"], "measure": "40ch"}) \
        if copy.get("intro") else ""
    rows = "".join(
        f'<div class="c-row"><span class="c-row-label">{cr.esc(lbl)}</span>'
        f'<span class="c-row-value">{cr.esc(val)}</span></div>'
        for lbl, val in copy.get("rows", []))
    cta_html = cr.render_arrow_link(doc, ctx, {"label": copy["cta"]}) if copy.get("cta") else ""
    return f"""<section class="cs-section cs-ruledlist-sec">
  <div class="cs-ruledlist">
    <div class="cs-eyebrow-wrap">{eyebrow_html}</div>
    {heading_html}
    {intro_html}
    <div class="c-rows">{rows}</div>
    {cta_html}
  </div>
</section>"""


# ── archetype: FAQ accordion (native <details>/<summary>, real interactivity) ────

def compose_faq_accordion(doc, layout, ctx, rendered, style_ctx):
    """Assemble a centered eyebrow -> heading -> stacked list of native disclosure rows
    (question as <summary>, answer revealed on toggle — real interactivity, zero JS).
    Promoted on a genuine miss (layout-library.yaml faq-accordion-list): no faq.yaml
    exists in the standard library at all. Rows separated by the brand's existing
    hairline device, never a card/box (no-cards-on-cream, no-shadows)."""
    copy = copy_for(layout, doc)
    eyebrow_html = cr.render_eyebrow(doc, ctx, {"text": copy["eyebrow"]})
    heading_html = cr.render_heading(doc, ctx, {
        "text": copy["heading"], "level": "display", "accent": False})
    items = "".join(
        f'<details class="c-faq-item"><summary class="c-faq-q">{cr.esc(q)}'
        f'<span class="c-faq-icon" aria-hidden="true">+</span></summary>'
        f'<p class="c-faq-a">{cr.esc(a)}</p></details>'
        for q, a in copy.get("items", []))
    return f"""<section class="cs-section cs-faq-sec">
  <div class="cs-faq">
    <div class="cs-eyebrow-wrap">{eyebrow_html}</div>
    {heading_html}
    <div class="c-faq-list">{items}</div>
  </div>
</section>"""


def compose_stack(doc, layout, ctx, rendered, style_ctx):
    """`stack` archetype dispatcher: WoodWave has the opening-bookend HERO, the narrow
    conversion stack, and (Held in Wood exhibition brief) the ruled-list panel + FAQ
    accordion. Disambiguate by patternRef FIRST (so ANY layout reusing an existing pattern
    routes correctly), falling back to the legacy id checks, then bound contracts (a
    `form` slot => the conversion stack); default to the hero so opening-bookend and every
    existing render stay unchanged."""
    pid = _pattern_id(layout)
    lid = (layout or {}).get("id")
    if pid in ("pricing-ruled-list-panel", "schedule-ruled-list-panel") \
            or lid in ("exhibition-tickets", "exhibition-schedule"):
        return compose_ruled_list_panel(doc, layout, ctx, rendered, style_ctx)
    if pid == "faq-accordion-list" or lid == "exhibition-faq":
        return compose_faq_accordion(doc, layout, ctx, rendered, style_ctx)
    # a composition-declared HERO routes to the hero composer BEFORE the bound-contract
    # checks (AS-27 hero extension): hero mappings now carry the section's REAL `button`
    # action slots, which must not re-route the hero into the conversion composer.
    if ((layout.get("_composition") or {}).get("useCase") or "").lower() == "hero":
        return compose_stack_hero(doc, layout, ctx, rendered, style_ctx)
    contracts = {m.get("contract") for m in (layout.get("blockMapping") or [])}
    # a bound `form` OR real `button` action slots => the conversion stack (B5: a
    # filled-CTA brand's closing CTA binds buttons, not an invented signup form).
    if "form" in contracts or "button" in contracts:
        return compose_conversion_stack(doc, layout, ctx, rendered, style_ctx)
    return compose_stack_hero(doc, layout, ctx, rendered, style_ctx)


# ── archetype: overlay (editorial-harvest-2026-07 — the layered positioning context) ──
# G1 panel-on-media · G2 straddle (z:front rides / z:back tucks) · G3 scrim-band ·
# G4 framed width class · G7 stepped-lines · G8 type-behind-media (occlusion contract).
# The adapter (compose_from_composition) attaches the raw composition slots + treatments
# under layout['_overlay']; every visible piece still renders through component_render.

# G8 occlusion budget per class (fraction of the occluded heading's GLYPH AREA the media
# may cover) — mirrored by onbrand_check._occlusion_checks; keep the two in sync.
OCCLUSION_CAP = {"light": 0.25, "medium": 0.40, "heavy": 0.55}
# scrim-band fill opacity per class (flat translucent wash of the section surface —
# NEVER a gradient). The medium default clears the body text-contrast floor on the
# WoodWave surfaces; light is legal only for display-tier content.
SCRIM_ALPHA = {"light": 0.35, "medium": 0.55, "heavy": 0.75}
# straddle/tuck depth per amount class, in --baseline multiples.
_TUCK_BASELINES = {"light": 2, "medium": 4, "heavy": 6}


def _rgba_css(hex_color, alpha: float) -> str:
    """A flat rgba() literal from a #rrggbb token value (readability.py can parse it,
    so the gate's text-contrast math stays deterministic over the scrim)."""
    m = re.fullmatch(r"#([0-9a-fA-F]{6})", str(hex_color or "").strip())
    if not m:
        return f"rgba(17, 17, 17, {alpha:g})"
    h = m.group(1)
    return f"rgba({int(h[0:2], 16)}, {int(h[2:4], 16)}, {int(h[4:6], 16)}, {alpha:g})"


def _ov_treatment(treatments, kind, target=None):
    for t in treatments or []:
        if (t.get("kind") or "").lower() != kind:
            continue
        if target is not None and t.get("target") != target:
            continue
        return t
    return None


def _ov_text(slot, *keys) -> str:
    """A display string from an overlay slot's inline copy (string or dict)."""
    c = (slot or {}).get("copy")
    if isinstance(c, str):
        return c
    if isinstance(c, dict):
        for k in keys or ("heading", "text", "body", "label", "caption", "quote", "eyebrow"):
            v = c.get(k)
            if isinstance(v, str) and v.strip():
                return v
    return ""


def _ov_left_css(col_start) -> str:
    """Left inset of a 1-based colStart on the shared registration grid."""
    try:
        cs_ = max(1, int(col_start))
    except (TypeError, ValueError):
        cs_ = 1
    if cs_ == 1:
        return "0"
    return f"calc({cs_ - 1} * (var(--col) + var(--grid-gutter, 6rem)))"


def _ov_rel_left(col_start, base_col=1) -> str:
    """Left inset of a 1-based colStart RELATIVE to a positioning context that itself
    starts at base_col (an inset canvas) — may be negative (a child reaching back over
    the canvas's left edge onto the page margin/rail)."""
    try:
        cs_ = max(1, int(col_start))
    except (TypeError, ValueError):
        cs_ = 1
    n = cs_ - max(1, int(base_col or 1))
    if n == 0:
        return "0"
    return f"calc({n} * (var(--col) + var(--grid-gutter, 6rem)))"


def _ov_render_text(doc, ctx, slot, *, heading_props=None):
    """Render ONE overlay text slot through the shared primitives (never bespoke markup),
    picked by role/contract/sizeClass. heading_props extends display-tier renders (e.g.
    stepped lines / mixed-face)."""
    role = (slot.get("role") or "").lower()
    contract = (slot.get("contract") or "").lower()
    sc = (slot.get("sizeClass") or "").lower()
    txt = _ov_text(slot)
    if contract in ("link", "cta") or "cta" in role or "action" in role \
            or (slot.get("name") or "") == "action":
        return cr.render_arrow_link(doc, ctx, {"label": txt or "Learn more", "accent": False})
    if "eyebrow" in role or "wordmark" in role:
        return cr.render_eyebrow(doc, ctx, {"text": txt})
    if sc in ("colossal", "hero", "display", "title"):
        props = {"text": txt or "Heading", "level": "display", "accent": False}
        props.update(heading_props or {})
        return cr.render_heading(doc, ctx, props)
    if sc == "caption" or "caption" in role or "meta" in role or "cue" in role \
            or "annotation" in role or "keyword" in role:
        return cr.render_caption(doc, ctx, {"text": txt})
    return cr.render_paragraph(doc, ctx, {"text": txt, "measure": "38ch"})


def _ov_media_html(doc, ctx, slot, *, variant="hero", art="hero"):
    # AS-34: the fallback preference comes from the ACTIVE brand's own declared
    # defaultArt (brand_default_art_names) resolved against its inventory
    # (_brand_art) — never a cross-brand literal src. ``art`` names the defaultArt
    # kind whose preferred filenames apply to this slot.
    kind = variant if variant in ("hero", "detail") else "hero"
    src = slot.get("src") or _brand_art(doc, kind, *brand_default_art_names(doc, art))
    if not src:
        return ""
    return cr.render_image(doc, ctx, {
        "src": src,
        "variant": variant, "aspect": slot.get("aspect"),
        "alt": slot.get("alt") or (slot.get("role") or "brand photography")})


def _ov_heading_lines(slot, stepped) -> list[str] | None:
    """stepped-lines (G7): the authored per-line breadown of the target's copy — an
    explicit multi-line string first, else a balanced word split into len(steps) lines."""
    if not stepped:
        return None
    txt = _ov_text(slot)
    if not txt:
        return None
    steps = stepped.get("steps") or [0, 1, 6]
    n = max(2, min(len(steps), 4))
    if "\n" in txt:
        lines = [ln.strip() for ln in txt.split("\n") if ln.strip()]
        return lines[:n] if len(lines) >= 2 else None
    words = txt.split()
    if len(words) < n:
        return None
    per = -(-len(words) // n)
    return [" ".join(words[i:i + per]) for i in range(0, len(words), per)][:n]


def _ov_mixed_face_props(slot, mixed) -> dict:
    """mixed-face (G5): copy carrying {lead, emphasis} renders per-span face contrast
    through render_heading's mixedFace path (falls back to weight/case contrast when the
    brand ships no alternate cut — never a synthesized italic)."""
    c = (slot or {}).get("copy")
    if not (mixed and isinstance(c, dict) and (c.get("lead") or c.get("emphasis"))):
        return {}
    return {"mixedFace": {"lead": c.get("lead") or "", "emphasis": c.get("emphasis") or ""}}


def _occlusion_geometry(heading_slot, media_slots, *, vert_frac, cols=12):
    """The G8 occlusion ESTIMATE from grid geometry: fraction of the heading's glyph area
    covered by the media stack (horizontal cover = the media's column span ∩ the heading's
    span; vertical cover = the declared tuck/pull fraction), plus first/last-letterform
    clearance (endsVisible). The composer stamps these INPUTS on the section
    (data-occlusion-geom) so the gate RECOMPUTES the estimate instead of trusting it."""
    h_start = int(heading_slot.get("colStart") or 1)
    h_span = int(heading_slot.get("colSpan") or cols)
    h_end = h_start + h_span
    covered_start, covered_end = None, None
    for m in media_slots:
        m_start = int(m.get("colStart") or 1)
        m_span = int(m.get("colSpan") or cols)
        s, e = max(h_start, m_start), min(h_end, m_start + m_span)
        if e > s:
            covered_start = s if covered_start is None else min(covered_start, s)
            covered_end = e if covered_end is None else max(covered_end, e)
    if covered_start is None:
        return {"occlusion": 0.0, "endsVisible": True, "horizFrac": 0.0,
                "vertFrac": round(vert_frac, 3), "headingCols": [h_start, h_end],
                "mediaCols": []}
    horiz_frac = (covered_end - covered_start) / h_span
    ends_visible = covered_start > h_start and covered_end < h_end
    if horiz_frac >= 0.999:
        # a full-width cover (the ref-7 tuck) hides the LOWER part of every glyph —
        # the word still reads while the tuck stays shallow (letterform tops clear).
        ends_visible = vert_frac <= 0.55
    return {"occlusion": round(horiz_frac * vert_frac, 3),
            "endsVisible": ends_visible, "horizFrac": round(horiz_frac, 3),
            "vertFrac": round(vert_frac, 3), "headingCols": [h_start, h_end],
            "mediaCols": [covered_start, covered_end]}


def _occlusion_attrs(geom, cap_class) -> str:
    """The data-* stamp for the G8 gate check (recomputable inputs + the declared cap)."""
    cap = OCCLUSION_CAP.get(str(cap_class or "medium").lower(), OCCLUSION_CAP["medium"])
    payload = json.dumps({
        "headingCols": geom["headingCols"], "mediaCols": geom["mediaCols"],
        "horizFrac": geom["horizFrac"], "vertFrac": geom["vertFrac"]},
        separators=(",", ":"))
    return (f' data-occlusion="{geom["occlusion"]:g}" data-occlusion-max="{cap:g}"'
            f' data-ends-visible="{str(geom["endsVisible"]).lower()}"'
            f" data-occlusion-geom='{payload}'")


def _overlay_type_behind_media(doc, layout, ctx, slots, treatments, tbm):
    """G8 type-behind-media masthead: REAL heading copy at full opacity on z:0, the
    portrait media stack ON TOP (z:2/3), flanking marginal captions mid-height. The
    media pull-up depth is CLAMPED so the computed occlusion honors the declared
    maxOcclusion budget, and endsVisible holds by grid construction (the media span
    stays strictly inside the heading span)."""
    by_name = {s["name"]: s for s in slots}
    heading = by_name.get(tbm.get("target")) or next(
        (s for s in slots if not s.get("media")
         and (s.get("sizeClass") or "") in ("colossal", "display", "hero")), None)
    media = [s for s in slots if s.get("media")]
    if heading is None or not media:
        return compose_generic_flow(doc, layout, ctx, [], None)
    over = tbm.get("over")
    over_names = over if isinstance(over, list) else ([over] if over else [])
    over_media = [by_name[n] for n in over_names if n in by_name] or media[:1]
    main = over_media[0]
    detail = next((s for s in media if s is not main), None)

    cap_class = ((tbm.get("maxOcclusion") or {}).get("class")) or "medium"
    cap = OCCLUSION_CAP.get(str(cap_class).lower(), OCCLUSION_CAP["medium"])
    # choose the pull depth: deepest vertical cover that keeps est. occlusion <= cap.
    h_span = int(heading.get("colSpan") or 12)
    m_span = min(int(main.get("colSpan") or 5), h_span)
    horiz = m_span / h_span
    vert = min(0.5, cap / max(horiz, 1e-6) * 0.85)   # 15% safety margin under the cap
    geom = _occlusion_geometry(heading, over_media, vert_frac=vert)

    eyebrow = next((s for s in slots if not s.get("media") and s is not heading
                    and "eyebrow" in (s.get("role") or "").lower()), None)
    captions = [s for s in slots if not s.get("media") and s is not heading
                and s is not eyebrow and "caption" in ((s.get("role") or "")
                                                       + (s.get("name") or "")).lower()]
    rest = [s for s in slots if not s.get("media")
            and s not in ([heading, eyebrow] + captions)]

    eyebrow_html = (f'<div class="cs-eyebrow-wrap">'
                    f'{cr.render_eyebrow(doc, ctx, {"text": _ov_text(eyebrow)})}</div>'
                    if eyebrow else "")
    heading_html = cr.render_heading(doc, ctx, {
        "text": _ov_text(heading) or "Heading", "level": "display", "accent": False,
        "splitTwoLines": True})
    main_html = _ov_media_html(doc, ctx, main, variant="overlap",
                               art="occlusion-main")
    detail_html = (f'<div class="cs-ov-detail" style="width: '
                   f'{_span_width_css(detail.get("colSpan") or 3)}">'
                   f'{_ov_media_html(doc, ctx, detail, variant="overlap", art="detail")}</div>'
                   if detail is not None else "")
    caption_html = ""
    for i, s in enumerate(captions[:2]):
        side = "right" if (i == 1 or "right" in ((s.get("role") or "")
                                                 + (s.get("name") or "")).lower()) else "left"
        caption_html += (f'\n    <div class="cs-ov-flank cs-ov-flank--{side}">'
                         f'{cr.render_caption(doc, ctx, {"text": _ov_text(s)})}</div>')
    rest_html = "".join(f'\n    <div class="cs-ov-foot-item">{_ov_render_text(doc, ctx, s)}</div>'
                        for s in rest if _ov_text(s))

    # --c-display-size is ALWAYS emitted per section (component_vars) — no literal
    # fallback (AS-24: a dormant `5rem` here was another brand's magnitude in disguise).
    pull = f"calc({vert:.3f} * 2.1 * var(--c-display-size))"
    return f"""<section class="cs-section cs-overlay-sec cs-ov-tbm-sec"{_occlusion_attrs(geom, cap_class)}>
  <div class="cs-ov-frame">
    {eyebrow_html}
    <div class="cs-ov-behind">{heading_html}</div>
    <div class="cs-ov-media-stack" style="width: {_span_width_css(main.get('colSpan') or 5)}; margin-inline-start: {_ov_left_css(main.get('colStart') or 5)}; margin-top: calc(-1 * {pull})">
      {main_html}
      {detail_html}
    </div>{caption_html}{rest_html}
  </div>
</section>"""


def compose_overlay(doc, layout, ctx, rendered, style_ctx):
    """`overlay` archetype (editorial-harvest-2026-07): ONE positioning context — an
    in-flow media CANVAS (full-bleed or `framed`) with grid-registered layers over it:
    a solid `panel-on-media`, `straddle` headings that ride over (z:front) or tuck under
    (z:back, G8 occlusion contract) a media edge, a flat translucent `scrim-band`, a
    sidebar rail, corner-registered captions/cues, `stepped-lines` statements. Slots +
    treatments arrive via layout['_overlay'] (the composition adapter); a layout without
    the payload degrades to the generic-flow safety net."""
    ov = layout.get("_overlay") or {}
    slots = ov.get("slots") or []
    if not slots:
        return compose_generic_flow(doc, layout, ctx, rendered, style_ctx)
    treatments = ov.get("treatments") or []
    by_name = {s["name"]: s for s in slots}

    tbm = _ov_treatment(treatments, "type-behind-media")
    if tbm:
        return _overlay_type_behind_media(doc, layout, ctx, slots, treatments, tbm)

    _role, surf = resolve_surface_intent(doc, layout)
    media = [s for s in slots if s.get("media")]
    claimed: set[str] = set()
    sec_mods, sec_attrs, frame_pre, canvas_children, frame_post = [], [], [], [], []

    # ── canvas: the framed target, else the z:back / full-bleed media, else the first ──
    framed_t = _ov_treatment(treatments, "framed")
    canvas = None
    if framed_t and framed_t.get("target") in by_name:
        canvas = by_name[framed_t["target"]]
    if canvas is None:
        canvas = next((s for s in media if s.get("z") == "back"
                       or (s.get("width") or "") in ("full-bleed", "framed")), None) \
            or (media[0] if media else None)
    canvas_style, canvas_cls = [], ["cs-ov-canvas"]
    is_framed = False
    canvas_col = 1     # the canvas's own column start: children position RELATIVE to it
    if canvas is not None:
        claimed.add(canvas["name"])
        if canvas.get("aspect"):
            canvas_style.append(f"aspect-ratio: {canvas['aspect']}")
        is_framed = framed_t is not None or (canvas.get("width") or "") == "framed"
        if is_framed:
            ratio = ((framed_t or {}).get("widthRel") or {}).get("ratio") or 0.86
            span = max(6, min(12, round(float(ratio) * 12)))
            canvas_cls.append("cs-ov-canvas--framed")
            if span < 12:
                canvas_style.append(f"width: {_span_width_css(span)}")
        else:
            bleed = _ov_treatment(treatments, "bleed", canvas["name"]) \
                or _ov_treatment(treatments, "bleed")
            if bleed or (canvas.get("width") or "") == "full-bleed":
                sec_mods.append("cs-ov--bleed")
        if int(canvas.get("colStart") or 1) > 1 and not is_framed:
            canvas_col = int(canvas["colStart"])
            canvas_style.append(f"margin-inline-start: {_ov_left_css(canvas_col)}")

    # ── panel-on-media (G1): a solid panel over the canvas carrying the free text stack ──
    panel_t = _ov_treatment(treatments, "panel-on-media")
    panel_html = ""
    if panel_t:
        panel_slot = by_name.get(panel_t.get("target"))
        if panel_slot is not None:
            claimed.add(panel_slot["name"])
        inner_names = []
        for s in slots:
            if s.get("media") or s["name"] in claimed:
                continue
            if s.get("colStart") is None and s.get("registration") is None:
                inner_names.append(s["name"])
        inner = "\n      ".join(
            f'<div class="cs-ov-panel-item">{_ov_render_text(doc, ctx, by_name[n])}</div>'
            for n in inner_names if _ov_text(by_name[n]))
        claimed.update(inner_names)
        dist = str(panel_t.get("distribute") or "start").lower()
        dist_css = {"start": "flex-start", "center": "center",
                    "space-between": "space-between"}.get(dist, "flex-start")
        p_start = (panel_slot or {}).get("colStart") or 4
        p_span = (panel_slot or {}).get("colSpan") or 6
        panel_html = (f'\n      <div class="cs-ov-panel" style="left: {_ov_rel_left(p_start, canvas_col)}; '
                      f'width: {_span_width_css(p_span)}; justify-content: {dist_css}">'
                      f'\n      {inner}\n      </div>')

    # ── sidebar rail: a stretch-width panel column + its name-prefixed child slots ──
    rail_html = ""
    rail = next((s for s in slots if not s.get("media") and s["name"] not in claimed
                 and "rail" in ((s.get("role") or "") + s["name"]).lower()), None)
    if rail is not None:
        claimed.add(rail["name"])
        kids = [s for s in slots if s["name"].startswith(rail["name"] + "-")]
        claimed.update(k["name"] for k in kids)
        kid_html = "\n        ".join(
            f'<div class="cs-ov-rail-item">{_ov_render_text(doc, ctx, k)}</div>'
            for k in kids if _ov_text(k))
        r_span = rail.get("colSpan") or 3
        rail_html = (f'\n      <div class="cs-ov-panel cs-ov-rail" style="left: '
                     f'{_ov_rel_left(rail.get("colStart") or 1, canvas_col)}; width: {_span_width_css(r_span)}">'
                     f'\n        {kid_html}\n      </div>')

    # ── scrim-band (G3): a FLAT translucent band across the canvas (never a gradient) ──
    scrim_html = ""
    scrim_t = _ov_treatment(treatments, "scrim-band")
    if scrim_t:
        target = by_name.get(scrim_t.get("target"))
        band = scrim_t.get("band") or {}
        alpha = SCRIM_ALPHA.get(str(((scrim_t.get("fill") or {}).get("opacityClass"))
                                    or "medium").lower(), SCRIM_ALPHA["medium"])
        fill = _rgba_css(surf.get("bg"), alpha)
        top = max(0.0, min(0.9, float(band.get("rowStart") or 0.55)))
        h = max(0.08, min(0.5, float(band.get("rowSpan") or 0.2)))
        items = ""
        if target is not None:
            claimed.add(target["name"])
            c = target.get("copy")
            entries = c if isinstance(c, list) else ([c] if c else [])
            for m in entries[:4]:
                if isinstance(m, dict):
                    kw = m.get("heading") or m.get("caption") or m.get("title") or m.get("label") or ""
                    sub = m.get("text") or m.get("body") or ""
                elif isinstance(m, str):
                    kw, sub = m, ""
                else:
                    continue
                items += (f'<div class="cs-ov-scrim-item">'
                          f'{cr.render_caption(doc, ctx, {"text": kw})}'
                          + (f'<p class="cs-sub">{cr.esc(sub)}</p>' if sub else "")
                          + "</div>")
        scrim_html = (f'\n      <div class="cs-ov-scrimband" style="top: '
                      f'round(nearest, {top:.0%}, var(--baseline)); min-height: {h:.0%}; '
                      f'background: {fill}">{items}</div>')

    # ── straddles (G2): z:front rides over an edge; z:back tucks under the canvas ──
    stepped_t = _ov_treatment(treatments, "stepped-lines")
    mixed_t = _ov_treatment(treatments, "mixed-face")
    tucked_html = ""
    for t in [t for t in treatments if (t.get("kind") or "").lower() == "straddle"]:
        target = by_name.get(t.get("target"))
        if target is None or target["name"] in claimed:
            continue
        reg = t.get("registration") or {}
        z = str(reg.get("z") or target.get("z") or "front").lower()
        claimed.add(target["name"])
        if z == "back":
            # tuck: heading drawn in flow BEFORE the canvas; the canvas rides over its
            # lower part by the registered depth (G8 occlusion params apply).
            depth_b = reg.get("depthBaselines")
            if depth_b is None:
                depth_b = _TUCK_BASELINES.get(
                    str(((t.get("amount") or {}).get("class")) or "medium").lower(), 4)
            depth_b = max(0, float(depth_b))
            # est. vertical cover: depth baselines over ~2.1 display-line-heights of glyphs
            vert = min(0.9, depth_b * 0.5 / (2.1 * 5.0))   # baselines→rem over ≈10.5rem
            geom = _occlusion_geometry(target, [canvas] if canvas else [],
                                       vert_frac=vert)
            sec_attrs.append(_occlusion_attrs(
                geom, ((t.get("maxOcclusion") or {}).get("class")) or "medium"))
            heading_html = _ov_render_text(doc, ctx, target,
                                           heading_props=_ov_mixed_face_props(target, mixed_t))
            # the heading's own row: support copy aligned to its top row on the right
            partner = next(
                (s for s in slots if not s.get("media") and s["name"] not in claimed
                 and isinstance(s.get("alignTo"), dict)
                 and s["alignTo"].get("slot") == target["name"]), None)
            partner_html = ""
            if partner is not None:
                claimed.add(partner["name"])
                partner_html = (f'\n      <div class="cs-ov-headrow-side" style="margin-inline-start: '
                                f'{_ov_left_css(partner.get("colStart") or 7)}; width: '
                                f'{_span_width_css(partner.get("colSpan") or 4)}">'
                                f'{_ov_render_text(doc, ctx, partner)}</div>')
            tucked_html = (f'\n    <div class="cs-ov-headrow cs-ov-headrow--tucked" '
                          f'style="--c-tuck-depth: calc({depth_b:g} * var(--baseline)); '
                          f'margin-inline-start: {_ov_left_css(target.get("colStart") or 1)}">'
                          f'\n      <div class="cs-ov-tucked" style="max-width: '
                          f'{_span_width_css(target.get("colSpan") or 6)}">{heading_html}</div>'
                          f'{partner_html}\n    </div>')
        else:
            # z:front: the heading rides over the crossed edge, registered to the seam /
            # the frame's bottom edge (the SAISEI monument) — sanctioned text-on-media.
            edge = str(reg.get("edge") or "left").lower()
            hp = _ov_mixed_face_props(target, mixed_t)
            lines = _ov_heading_lines(target, stepped_t if stepped_t
                                      and stepped_t.get("target") == target["name"] else None)
            if lines:
                hp["lines"] = lines
            heading_html = _ov_render_text(doc, ctx, target, heading_props=hp)
            pos = []
            to_slot = by_name.get(reg.get("toSlot"))
            if edge == "bottom":
                pos.append("bottom: calc(-0.5 * var(--baseline))")
            else:
                pos.append("top: calc(6 * var(--baseline))")
            if to_slot is not None and edge in ("left", "right"):
                seam_col = int(to_slot.get("colStart") or 1) + int(to_slot.get("colSpan") or 3)
                pos.append(f"left: {_ov_rel_left(seam_col, canvas_col)}")
            else:
                pos.append(f"left: {_ov_rel_left(target.get('colStart') or 1, canvas_col)}")
            cls = "cs-ov-straddle" + (" cs-ov-stepped" if lines else "")
            step_vars = ""
            if lines and stepped_t:
                steps = (stepped_t.get("steps") or [0, 1, 6])[:len(lines)]
                step_vars = "; ".join(
                    f"--c-step-{i + 1}: calc({s:g} * 0.5 * (var(--col) + var(--grid-gutter, 6rem)))"
                    for i, s in enumerate(steps))
                step_vars = "; " + step_vars
            canvas_children.append(
                f'\n      <div class="{cls}" style="{"; ".join(pos)}; max-width: '
                f'{_span_width_css(target.get("colSpan") or 8)}{step_vars}">{heading_html}</div>')

    # ── stepped-lines without a straddle (the full-bleed poster statement, ref 5) ──
    if stepped_t and stepped_t.get("target") in by_name \
            and stepped_t["target"] not in claimed:
        target = by_name[stepped_t["target"]]
        claimed.add(target["name"])
        lines = _ov_heading_lines(target, stepped_t)
        hp = _ov_mixed_face_props(target, mixed_t)
        if lines:
            hp["lines"] = lines
        heading_html = _ov_render_text(doc, ctx, target, heading_props=hp)
        steps = (stepped_t.get("steps") or [0, 1, 6])[:max(1, len(lines or [1]))]
        step_vars = "; ".join(
            f"--c-step-{i + 1}: calc({s:g} * 0.5 * (var(--col) + var(--grid-gutter, 6rem)))"
            for i, s in enumerate(steps))
        canvas_children.append(
            f'\n      <div class="cs-ov-straddle cs-ov-stepped" style="top: '
            f'calc(10 * var(--baseline)); left: {_ov_rel_left(target.get("colStart") or 1, canvas_col)}; '
            f'max-width: {_span_width_css(target.get("colSpan") or 8)}; {step_vars}">{heading_html}</div>')

    # ── break-frame (G6): corner-anchored DECORATION crossing the frame edge ──
    for t in [t for t in treatments if (t.get("kind") or "").lower() == "break-frame"]:
        target = by_name.get(t.get("target"))
        if target is None or not target.get("media") or target["name"] in claimed:
            continue
        claimed.add(target["name"])
        reg = t.get("registration") or {}
        corner = str(((target.get("alignTo") or {}) or {}).get("corner") or "tr").lower()
        x = "left" if corner in ("tl", "bl") else "right"
        y = "top" if corner in ("tl", "tr") else "bottom"
        db = float(reg.get("depthBaselines") or 4)
        img = _ov_media_html(doc, ctx, target, variant="overlap", art="detail")
        canvas_children.append(
            f'\n      <div class="cs-ov-breakframe" aria-hidden="true" data-decoration="true" '
            f'style="{x}: calc(-{db:g} * var(--baseline)); '
            f'{y}: calc(-{db:g} * var(--baseline)); '
            f'width: {_span_width_css(target.get("colSpan") or 2)}">{img}</div>')

    # ── remaining placed/corner slots: in-frame annotations, cues, corner support ──
    foot_items = []
    for s in slots:
        if s.get("media") or s["name"] in claimed:
            continue
        if not _ov_text(s):
            claimed.add(s["name"])
            continue
        align = s.get("alignTo") if isinstance(s.get("alignTo"), dict) else {}
        corner = str((align or {}).get("corner") or "").lower()
        frag = _ov_render_text(doc, ctx, s)
        if corner in ("br", "bl", "tr", "tl"):
            x = "left" if corner in ("tl", "bl") else "right"
            y = "top" if corner in ("tl", "tr") else "bottom"
            canvas_children.append(
                f'\n      <div class="cs-ov-corner cs-ov-corner--{corner}" style="'
                f'{x}: calc(4 * var(--baseline)); {y}: calc(4 * var(--baseline)); '
                f'max-width: {_span_width_css(s.get("colSpan") or 2)}">{frag}</div>')
        elif s.get("colStart") is not None:
            canvas_children.append(
                f'\n      <div class="cs-ov-placed" style="left: {_ov_rel_left(s.get("colStart"), canvas_col)}; '
                f'top: calc(6 * var(--baseline)); max-width: '
                f'{_span_width_css(s.get("colSpan") or 2)}">{frag}</div>')
        else:
            foot_items.append(f'\n    <div class="cs-ov-foot-item">{frag}</div>')
        claimed.add(s["name"])

    # sanctioned text-on-media over the raw canvas gets the flat surface scrim (the same
    # mitigation the layered hero applies) UNLESS a panel/scrim already carries the text.
    tom = _ov_treatment(treatments, "text-on-media")
    needs_scrim = bool(canvas_children) and not panel_html and not scrim_html and tom is not None
    scrim_wash = (f'\n      <div class="cs-ov-scrim" style="background: '
                  f'{_rgba_css(surf.get("bg"), 0.45)}" aria-hidden="true"></div>'
                  if needs_scrim else "")

    canvas_html = ""
    if canvas is not None:
        style_attr = f' style="{"; ".join(canvas_style)}"' if canvas_style else ""
        canvas_html = (f'\n    <figure class="{" ".join(canvas_cls)}"{style_attr}>'
                       f'\n      {_ov_media_html(doc, ctx, canvas)}{scrim_wash}'
                       f'{"".join(canvas_children)}{rail_html}{scrim_html}{panel_html}'
                       f'\n    </figure>')
    else:
        frame_post.extend(canvas_children)

    foot_html = f'\n    <div class="cs-ov-foot">{"".join(foot_items)}\n    </div>' \
        if foot_items else ""
    mods = (" " + " ".join(sec_mods)) if sec_mods else ""
    attrs = "".join(sec_attrs)
    return f"""<section class="cs-section cs-overlay-sec{mods}"{attrs}>
  <div class="cs-ov-frame">{tucked_html}{canvas_html}{"".join(frame_post)}{foot_html}
  </div>
</section>"""


# ── archetype: banded (G9 — dual-surface section with a hard horizontal seam) ─────

def compose_banded(doc, layout, ctx, rendered, style_ctx):
    """`banded` archetype (G9): TWO stacked full-width surface bands with a hard seam
    (a hard cut, never a gradient) — the 90°-rotation of the split's flush halves. A
    slot registered to the reserved name 'seam' STRADDLES the boundary (WoodWave's
    sanctioned media-over-seam pair) via an in-flow pull-up (negative registered
    margin), so content below flows naturally. Band surfaces are surface-attributed
    for the gate via data-band-surface."""
    ov = layout.get("_overlay") or {}
    slots = ov.get("slots") or []
    if not slots:
        return compose_generic_flow(doc, layout, ctx, rendered, style_ctx)
    treatments = ov.get("treatments") or []
    bands = ov.get("bands") or {}
    by_name = {s["name"]: s for s in slots}
    surfaces = bands.get("surfaces") or ["inverse", "panel"]
    split = float(bands.get("split") or 0.5)

    media = [s for s in slots if s.get("media")]
    photo = next((s for s in media if (s.get("width") or "") == "full-bleed"
                  or s.get("z") == "back"), None) or (media[0] if media else None)

    # the seam straddler: the straddle whose registration names the reserved 'seam'.
    straddler = None
    rise_b = 12.0
    for t in treatments:
        if (t.get("kind") or "").lower() != "straddle":
            continue
        reg = t.get("registration") or {}
        if str(reg.get("toSlot") or "").lower() == "seam":
            straddler = by_name.get(t.get("target"))
            rise_b = float(reg.get("depthBaselines") or 12)
            break
    if straddler is None:
        straddler = next((s for s in media if s is not photo), None)

    claimed = {s["name"] for s in (photo, straddler) if s is not None}
    caption = next((s for s in slots if not s.get("media") and s["name"] not in claimed
                    and "caption" in ((s.get("role") or "") + s["name"]).lower()), None)
    if caption is not None:
        claimed.add(caption["name"])
    rest = [s for s in slots if s["name"] not in claimed and not s.get("media")]

    # band surface tokens: resolve each band's role against the brand surfaces so the
    # bands carry REAL scoped values (the gate's band attribution + readability read them).
    surfs = doc.get("tokens", {}).get("surfaces", {}) or {}
    surf_map = {"any": "surface/primary", "primary": "surface/primary",
                "inverse": "surface/inverse", "inverse-strong": "surface/inverse-strong",
                "panel": "surface/panel"}
    def band_vars(role_word):
        role = surf_map.get(str(role_word).lower(), "surface/primary")
        s = surfs.get(role) or {}
        bg = s.get("bg") or "#ffffff"
        ink = color_value(doc, s.get("textPrimary")) or "#111111"
        # interaction tokens re-scope PER BAND SURFACE (AS-20, mirrors component_vars):
        # the measured accent hover is legal only on a dark/textAccent-bearing band;
        # a light band's hover resolves to its own ink (ink-shift).
        hover = (cr.link_hover_color(doc) if s.get("textAccent") else None) or ink
        return role, (f"--c-paper: {bg}; --c-ink: {ink}; --c-ink-muted: {ink}; "
                      f"--c-link-hover: {hover}; background: {bg}; color: {ink}")
    top_role, top_css = band_vars(surfaces[0])
    bot_role, bot_css = band_vars(surfaces[1] if len(surfaces) > 1 else "panel")

    photo_html = _ov_media_html(doc, ctx, photo) if photo is not None else ""
    # the on-photo caption renders on a small PANEL CHIP (sanctioned panel-over-media),
    # never bare text on the photograph (no-text-on-photos stays honored outside heroes).
    cap_html = ""
    if caption is not None and _ov_text(caption):
        chip_bg = _rgba_css((surfs.get(bot_role) or {}).get("bg"), 0.9)
        cap_html = (f'\n      <div class="cs-band-chip" style="background: {chip_bg}">'
                    f'{cr.render_caption(doc, ctx, {"text": _ov_text(caption)})}</div>')

    strad_html = ""
    if straddler is not None:
        span = straddler.get("colSpan") or 6
        start = straddler.get("colStart")
        inline = f"margin-inline-start: {_ov_left_css(start)};" if start and int(start) > 1 \
            else "margin-inline: auto;"
        if straddler.get("media"):
            inner = _ov_media_html(doc, ctx, straddler, variant="overlap",
                                   art="occlusion-main")
        else:
            inner = _ov_render_text(doc, ctx, straddler)
        strad_html = (f'\n    <div class="cs-band-straddler" style="width: {_span_width_css(span)}; '
                      f'{inline} --c-seam-rise: calc({rise_b:g} * var(--baseline))">'
                      f'{inner}</div>')

    rest_html = "".join(
        f'\n      <div class="cs-band-item" style="max-width: {_span_width_css(s.get("colSpan") or 8)};'
        + (f' margin-inline-start: {_ov_left_css(s.get("colStart"))}'
           if s.get("colStart") and int(s["colStart"]) > 1 else "")
        + f'">{_ov_render_text(doc, ctx, s)}</div>'
        for s in rest if _ov_text(s))

    split_pc = max(0.25, min(0.75, split))
    return f"""<section class="cs-section cs-banded-sec" data-bands="{cr.esc(top_role)},{cr.esc(bot_role)}" data-band-split="{split_pc:g}">
  <div class="cs-band cs-band--top" data-band-surface="{cr.esc(top_role)}" style="{top_css}">
    <figure class="cs-band-media">{photo_html}</figure>{cap_html}
  </div>
  <div class="cs-band cs-band--bottom" data-band-surface="{cr.esc(bot_role)}" style="{bot_css}">{strad_html}
    <div class="cs-band-body">{rest_html}
    </div>
  </div>
</section>"""


# Archetype dispatch: every WoodWave archetype now has a real assembler.
ARCHETYPE_COMPOSERS = {
    "stack": compose_stack,
    "collage": compose_collage,
    "split": compose_split,
    "stack-fullbleed": compose_gallery_showcase,
    "cards": compose_features_cards,
    "interlock": compose_editorial_interlock,
    # editorial-harvest-2026-07: the layered positioning context + the dual-surface seam.
    "overlay": compose_overlay,
    "banded": compose_banded,
    # graceful fallback for a novel/unmapped (renderer) archetype — see compose_generic_flow.
    "generic-flow": compose_generic_flow,
}


def scaffold_key(layout) -> str:
    """The SCAFFOLD FAMILY the archetype dispatch will assemble for this layout — the
    stable, brand-agnostic key space for scaffold-scoped machinery (the wildcard ladder
    keys on this, since its CSS targets `.cs-<scaffold>-*` classes, not layout ids).
    Mirrors compose_stack / compose_collage / compose_split exactly: patternRef id
    first, then legacy layout id, then bound contracts, then the archetype default."""
    archetype = ((layout or {}).get("archetype") or "stack").lower()
    pid = _pattern_id(layout)
    lid = (layout or {}).get("id")
    if archetype == "stack":
        if pid in ("pricing-ruled-list-panel", "schedule-ruled-list-panel") \
                or lid in ("exhibition-tickets", "exhibition-schedule"):
            return "ruled-list"
        if pid == "faq-accordion-list" or lid == "exhibition-faq":
            return "faq"
        if (((layout or {}).get("_composition") or {}).get("useCase") or "").lower() == "hero":
            return "hero"
        contracts = {m.get("contract") for m in ((layout or {}).get("blockMapping") or [])}
        if "form" in contracts or "button" in contracts:
            return "conversion"
        return "hero"
    if archetype == "collage":
        if pid == "heritage-ghost-numerals-timeline" or lid == "heritage-timeline":
            return "timeline"
        return "collage"
    if archetype == "split":
        if pid == "about-anchored-statement" or lid == "mission-statement":
            return "statement"
        if pid == "curator-quote-portrait-collage" or lid == "curator-quote":
            return "quote"
        if pid == "visit-dual-panel-map" or lid == "visit-band":
            return "visit"
        return "info-band"
    if archetype == "stack-fullbleed":
        return "gallery"
    return archetype


# ── scaffold CSS (archetype geometry; brand-token driven, cq-units only) ─────────

# Shared base scaffold (cs-section + nav). Cream/ink come from the surface-scoped --c-*.
# ALIGNMENT QUICK WINS: the base also carries (a) the ONE shared content container — every
# major section grid caps at the SAME var(--content-measure) and centers, so adjacent
# sections register to identical left/right edges (previously each scaffold re-declared
# its own `max-width: 86rem; margin: 0 auto`) — and (b) the shared 12-col registration
# grid every two-column scaffold places onto (repeat(var(--grid-cols)) tracks +
# var(--grid-gutter, 6rem)) instead of private fr-ratio tracks.
SCAFFOLD_BASE_CSS = """.cs-section { background: var(--c-paper); color: var(--c-ink);
  padding: var(--c-section-pad-top) var(--c-section-pad-x)
           var(--c-section-pad-bottom); }
.cs-nav { display: flex; align-items: center; justify-content: space-between; gap: 2rem;
  margin-bottom: clamp(2rem, 6cqw, 5rem); }
.cs-navlinks { display: flex; gap: 0.55rem; flex: 1; justify-content: center; }
/* nav links read the MEASURED nav register (--c-nav-size, single-sourced from
   brand.yaml navbar.measured.link), not the generic control-text size. */
.cs-navlinks .c-arrow-link { font-size: var(--c-nav-size, var(--c-control-size)); }
.cs-navlinks .cs-sep { opacity: 0.55; }
/* shared content container: ONE measure, identical section edges page-wide. */
.cs-collage-grid, .cs-statement-grid, .cs-quote-grid, .cs-visit-panels,
.cs-modules-intro, .cs-modules, .cs-interlock {
  max-width: var(--content-measure, 86rem); margin-inline: auto; }
/* shared 12-col registration grid (column-gap IS the shared gutter). */
.cs-collage-grid, .cs-statement-grid, .cs-quote-grid, .cs-modules {
  display: grid; grid-template-columns: repeat(var(--grid-cols, 12), minmax(0, 1fr));
  column-gap: var(--grid-gutter, 6rem); }"""

# stack hero (opening-bookend): centered display title over the media collage.
SCAFFOLD_HERO_CSS = """.cs-section { min-height: 100cqh; }
.cs-slot { display: flex; flex-direction: column; align-items: center; }
.cs-eyebrow-wrap { margin-bottom: var(--c-eyebrow-gap); text-align: center; }
.cs-title { position: relative; z-index: 2; text-align: center;
  margin-bottom: var(--c-title-overlap); }
.cs-collage { position: relative; width: 100%; max-width: 80rem; margin: 0 auto; }
/* ALIGNMENT: the overlap depth/offsets keep their measured % magnitudes but round() the
   USED value to an exact --baseline multiple, so the overlap registers to the shared
   baseline grid at any width instead of landing on an arbitrary fraction. */
.c-image--overlap.is-abs { position: absolute;
  width: round(nearest, 34%, var(--baseline));
  right: round(nearest, 4%, var(--baseline));
  bottom: round(nearest, -28%, var(--baseline)); z-index: 1; }
/* SPACER (anti-ai-slop.md AS-01/AS-03): reserves clearance below the collage for the
   overlap image's bleed (bottom:-28% of a 34%-wide, 785:620 image inside a 1355:570
   collage geometrically needs ~11.7% of the collage's OWN width, not a guessed round
   number). The clamp() UPPER BOUND (9.5rem) is what actually matters here: it caps
   growth once the collage hits its 80rem max-width, so the spacer stops scaling with
   the full, uncapped section width on wide viewports — the way the old bare `22cqw`
   (measured against `.cs-slot`, not the width-capped collage) kept growing forever. */
.cs-spacer { height: clamp(4rem, 12cqw, 9.5rem); }
.cs-foot { display: flex; flex-direction: column; align-items: center;
  gap: var(--c-block-gap); text-align: center; margin-top: var(--c-block-gap); }
/* subhead rides the brand body register one step up (1rem was body 0.875rem x 1.1429
   against the pre-token render — ratio is structure, magnitude is the brand's). */
.cs-sub { font-family: var(--c-font-body); font-size: calc(var(--c-body-size) * 1.1429);
  line-height: 1.55em; color: var(--c-ink-muted); max-width: 42rem; }
/* ── PLACED media layers (grid/overlap contract §4.6.5) ─────────────────────────
   Only sections whose composition declared placement get these classes; the legacy
   hero (.cs-collage without --layered) is byte-unchanged. z-ladder inside the layered
   collage: back overlays(0) < base media(1) < mid(2) < front(3) < display title(4);
   the corner-pinned media + background layer register to the SECTION frame. */
.cs-hero-layered { position: relative; overflow: hidden; }
.cs-hero-layered .cs-slot { position: relative; z-index: 2; }
.cs-hero-layered .cs-title { z-index: 4; }
.cs-collage--layered > .c-image, .cs-collage--layered > .c-image-ph {
  position: relative; z-index: 1; margin-inline: auto; }
.cs-ov { position: absolute; }
.cs-ov .c-image, .cs-ov .c-image-ph { width: 100%; }
/* z:back + width:full-bleed media = a true BACKGROUND layer behind the section copy —
   the SANCTIONED text-on-media treatment. The scrim is a flat surface-toned wash (the
   section's own --c-paper at high opacity) so text keeps AA contrast over the photo
   (gate: text-contrast); never a gradient (brand neverDo no-gradients). */
.cs-bg-layer { position: absolute; inset: 0; z-index: 0; }
.cs-bg-layer .c-image { width: 100%; height: 100%; object-fit: cover; }
.cs-bg-scrim { position: absolute; inset: 0;
  background: color-mix(in srgb, var(--c-paper) 72%, transparent); }
/* small z:front media pinned to a corner of the SECTION frame (alignTo.corner). */
.cs-corner-media { position: absolute; }
.cs-corner-media .c-image, .cs-corner-media .c-image-ph { width: 100%; }
/* HERO ACTIONS row (AS-27 hero extension): real bound action slots cluster on the
   brand's control rhythm; each child is the shared c-button / c-arrow-link primitive
   (filled vs typographic is render_button's law-first dispatch, not CSS). */
.cs-hero-actions { display: flex; flex-wrap: wrap; align-items: center;
  gap: var(--c-block-gap); justify-content: inherit; }
.cs-foot .cs-hero-actions { justify-content: center; }
@media (max-width: 991px) { .cs-navlinks { display: none; } }
@media (max-width: 767px) { .cs-section {
    /* provenance: structural — mobile floor insets (tap-safe minimum section padding on
       a narrow frame; device floor, not a brand rhythm token) */
    padding: clamp(1.25rem, 5cqw, 1.75rem)
    clamp(1.25rem, 5cqw, 1.75rem) clamp(1.5rem, 9cqw, 3rem); }
  .c-image--overlap.is-abs { width: round(nearest, 46%, var(--baseline));
    right: round(nearest, 2%, var(--baseline));
    bottom: round(nearest, -18%, var(--baseline)); }
  /* mobile overlap geometry (46% wide, bottom:-18%) needs ~7.6% of collage width */
  .cs-spacer { height: clamp(2.5rem, 8cqw, 5rem); }
}"""

# INSET ART-PANEL hero (AS-37: generic art-panel surface; style-gated). Emitted ONLY
# when the section actually renders the device (layout carries `_artPanel`), so pages
# without it — e.g. every no-radius brand render — stay literally free of this CSS
# (the neverDo.no-radius check reads the page text; an inert `border-radius:
# var(--radius-panel, ...)` rule would read as a rounded device on a sharp brand).
SCAFFOLD_ART_PANEL_CSS = """/* ── INSET ART-PANEL hero (AS-37) ─────────────────────
   The hero lives INSIDE one rounded panel painted with the brand's own art asset.
   Radius rides the brand token chain (panel tier, else the global radius); rhythm
   rides the shared --c-* vars; the art is a background FILL (surface, not an <img>). */
.cs-hero-panel-sec { display: flex; flex-direction: column; }
.cs-hero-panel { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  align-items: center; column-gap: var(--grid-gutter, 6rem); flex: 1;
  width: 100%; max-width: var(--content-measure, 86rem); margin-inline: auto;
  border-radius: var(--radius-panel, var(--radius));
  background-color: var(--c-panel-bg, var(--c-paper));
  background-size: cover; background-position: center top; overflow: hidden;
  padding: var(--c-module-gap, 6rem) var(--c-module-gap, 6rem); }
.cs-hero-panel--solo { grid-template-columns: minmax(0, 1fr); }
.cs-hero-panel-content { display: flex; flex-direction: column; align-items: flex-start;
  justify-content: center; gap: var(--c-block-gap); text-align: left; }
.cs-hero-panel-content .cs-title { margin-bottom: 0; text-align: inherit; }
.cs-hero-panel-media { align-self: stretch; display: flex; align-items: center; }
.cs-hero-panel-media .c-image, .cs-hero-panel-media .c-image-ph { width: 100%; }
@media (max-width: 767px) {
  .cs-hero-panel { grid-template-columns: minmax(0, 1fr); row-gap: var(--c-block-gap);
    /* provenance: structural — mobile floor inset inside the art panel (device floor) */
    padding: clamp(1.5rem, 6cqw, 2.5rem); } }"""

# collage (editorial about-run): oversized ghost watermark behind a DELIBERATELY
# asymmetric 2x2 module — headline top-left, offset body top-right, media bottom-left.
# (Fix: the prior layout left the display headline capped narrow on the left with the
# whole right half empty cream — an unintentional dead void. Now the body fills the
# top-right beside the headline and the ghost watermark fills the lower-right, so the
# asymmetry reads as intentional editorial negative space, not an empty void.)
SCAFFOLD_COLLAGE_CSS = """.cs-collage-sec { position: relative; overflow: hidden; }
.cs-ghost { position: absolute; right: -3cqw; top: 4%; z-index: 0;
  font-family: var(--c-font-heading);
  text-transform: var(--case-ghost-watermark, var(--c-case-heading));
  font-weight: var(--weight-ghost-watermark, var(--c-heading-weight));
  /* ghost scale: brand-measured tier magnitude x structural ladder ratios (CS-2);
     var unresolved (no ghost tier) => device disabled, never a foreign scale. */
  font-size: var(--c-ghost-size,
    clamp(calc(var(--size-ghost-watermark-base) * 0.381), 40cqw,
          calc(var(--size-ghost-watermark-base) * 1.219)));
  line-height: 0.9;
  color: var(--c-ghost);
  pointer-events: none; white-space: nowrap; }
/* SURFACE-AWARE ghost: the brand-constant --c-ghost is dark-ink-at-6% (cream tuned) —
   invisible dark-on-dark on an inverse collage. Scoped to inverse surfaces only, so
   every existing cream collage render is byte-unchanged; low-salience by construction
   (8% of the surface's own ink — gate: decoration-salience). */
[data-surface*="inverse"] .cs-ghost {
  color: color-mix(in srgb, var(--c-ink) 8%, transparent); }
/* placed onto the SHARED 12-col grid (tracks + gutter from SCAFFOLD_BASE_CSS): the old
   private 1.08fr/0.92fr ratio maps to a 6/6 span split (the nearest whole-column spans),
   so the head/media column and the body column register to shared page tracks. Row gap +
   body drop are exact --baseline multiples (3rem = 6, 3.5rem = 7). */
.cs-collage-grid { position: relative; z-index: 1;
  row-gap: calc(6 * var(--baseline)); align-items: start; }
.cs-collage-head { grid-column: 1 / span 6; grid-row: 1; max-width: none; }
/* the collage headline spans wider than the style's global display cap so it intrudes
   toward the right rather than stacking one word per line on the far left. */
.cs-collage-head .c-heading--display { max-width: 17ch; text-align: left; }
.cs-collage-media { grid-column: 1 / span 6; grid-row: 2; display: flex;
  flex-direction: column; gap: 0.75rem; margin: 0; align-self: end; }
.cs-collage-media .c-image { width: 100%; }
.cs-collage-body { grid-column: 7 / -1; grid-row: 1 / span 2; align-self: start;
  display: flex; flex-direction: column;
  gap: var(--c-block-gap); max-width: 38ch;
  padding-top: calc(7 * var(--baseline)); }
/* MID collapse (anti-ai-slop AS-16 multi-viewport lesson): between ~768-1280px the
   display heading overflows its 6-col track and paints OVER the body column (grid does
   not clip overflow) — collapse to a single column well before the mobile breakpoint. */
@media (max-width: 1280px) { .cs-collage-grid { grid-template-columns: 1fr; gap: 2.5rem; }
  .cs-collage-head { grid-column: 1; grid-row: 1; }
  .cs-collage-body { grid-column: 1; grid-row: 2; padding-top: 0; max-width: 46ch; }
  .cs-collage-media { grid-column: 1; grid-row: 3; align-self: start; } }
@media (max-width: 767px) { .cs-collage-grid { grid-template-columns: 1fr; gap: 2.5rem; }
  .cs-collage-head { grid-column: 1; grid-row: 1; }
  .cs-collage-body { grid-column: 1; grid-row: 2; padding-top: 0; max-width: none; }
  .cs-collage-media { grid-column: 1; grid-row: 3; align-self: start; }
  .cs-ghost { font-size: clamp(calc(var(--size-ghost-watermark-base) * 0.1905), 40cqw,
                calc(var(--size-ghost-watermark-base) * 0.4571));
    right: auto; left: -2cqw; } }"""

# split (info-band): two flush halves — photo | cream panel — gap 0, hard cut.
SCAFFOLD_SPLIT_CSS = """.cs-split-intro { max-width: 100%; margin-bottom: 3.5rem; }
.cs-split-intro .cs-eyebrow-wrap { margin-bottom: var(--c-eyebrow-gap); }
/* the band heading is the didone DISPLAY tier; give it room to breathe (the style's
   global 16ch display cap is too tight for this dark-band heading). */
.cs-split-intro .c-heading--display { max-width: 22ch; }
/* the split places onto 12 shared columns with a ZERO gutter (the flush hard cut is the
   band's character): each half spans 6, so its seam registers to the grid's center line. */
.cs-split { display: grid; grid-template-columns: repeat(var(--grid-cols, 12), minmax(0, 1fr));
  gap: 0; align-items: stretch; }
.cs-split-media { grid-column: 1 / span 6; display: flex; }
.cs-split > .cs-panel { grid-column: 7 / -1; }
.cs-split-media .c-image { width: 100%; height: 100%; object-fit: cover; }
/* CS-1 (token-layer-2026-07): the brand-color literals that used to sit in these var()
   fallbacks are GONE — the generated layer-1 block always defines the panel family
   (fail-loud at generation), so fallbacks were dead-or-DNA. */
.cs-panel { background: var(--c-panel); color: var(--c-panel-ink);
  padding: 2.75rem 2.5rem; display: flex; flex-direction: column;
  /* the panel keeps its own surface coloring regardless of the dark parent band.
     INTERACTION tokens re-scope with it (AS-20): the panel is a LIGHT surface, so the
     link hover resolves to the panel's own ink (ink-shift) — the parent dark section's
     measured accent hover (--c-link-hover) must never leak onto the light panel
     (the 'GET DIRECTIONS' gold-on-cream ~1.3:1 failure). */
  --c-ink: var(--c-panel-ink); --c-accent: var(--c-panel-ink);
  --c-link-hover: var(--c-panel-ink);
  --c-hairline: var(--c-panel-hairline); }
.cs-panel-title { margin-bottom: 1.25rem; }
.cs-panel-foot { margin-top: 1.5rem; display: flex; justify-content: flex-end; }
@media (max-width: 767px) { .cs-split { grid-template-columns: 1fr; }
  .cs-split-media, .cs-split > .cs-panel { grid-column: 1; }
  .cs-split-media .c-image { /* provenance: structural — mobile recrop: the stacked
    split half needs a bounded height (device geometry, not a brand ratio) */
    aspect-ratio: 4 / 3; } }"""

# conversion stack (newsletter): a centered narrow column with the underline form.
# ALIGNMENT-COHERENCE RULE (brand-schema.md §4.4 contentShape.alignment; CTA blocks only —
# NOT universal, see the schema note): once the heading is centered, sibling controls
# inherit the SAME MEASURE as the body text, not the full column width. `--c-cta-measure`
# is the single source both the paragraph and the form read, so they can never drift apart
# the way the form did before (it was stretched to the full 46rem column instead of this
# measure, reading visibly wider than the body above it against the source reference).
SCAFFOLD_CONVERSION_CSS = """.cs-conversion-sec { display: flex; justify-content: center; }
.cs-conversion { display: flex; flex-direction: column; align-items: center; text-align: center;
  gap: var(--c-block-gap); max-width: 46rem; width: 100%; --c-cta-measure: 40ch; }
.cs-conversion .c-paragraph { max-width: var(--c-cta-measure); }
.cs-conversion .c-form { margin: 0.75rem auto 0; max-width: var(--c-cta-measure); width: 100%; }
.cs-conversion .c-field { width: 100%; }
/* real action slots (B5): the bound button contracts render as a centered action row —
   present only when the composition binds `button` slots; the legacy form path never
   emits this element. Gap rides the section's own block-gap alias. */
.cs-conversion-actions { display: flex; flex-wrap: wrap; justify-content: center;
  align-items: center; gap: var(--c-block-gap); }
/* documented brand override (voice.md: "one of only two sanctioned centered stacks",
   the other being the hero #sec-0): beats the active style's generic
   `.c-heading--display { text-align:left; max-width:18ch }` default via higher
   selector specificity, scoped ONLY to this section — every other section keeps the
   style's asymmetric left-anchored default unchanged. */
.cs-conversion-sec .c-heading--display { text-align: center; max-width: 34ch; }
@media (max-width: 767px) { .cs-conversion { max-width: 100%; } }"""

# ruled-list panel (exhibition tickets/pricing + schedule/dates): a centered column,
# same ALIGNMENT-COHERENCE discipline as .cs-conversion above — heading, intro, rows and
# action all share ONE measure/center via --c-list-measure, so the rows list can never
# drift wider than the heading the way the conversion form once did (brand-schema.md
# §4.4 contentShape.alignment). Reuses .c-rows/.c-row verbatim (COMPONENT_CSS) — no new
# row markup, only the surrounding column geometry is new.
SCAFFOLD_RULEDLIST_CSS = """.cs-ruledlist-sec { display: flex; justify-content: center; }
.cs-ruledlist { display: flex; flex-direction: column; align-items: center; text-align: center;
  gap: var(--c-block-gap); max-width: 46rem; width: 100%; --c-list-measure: 34rem; }
.cs-ruledlist .c-paragraph { max-width: 40ch; }
.cs-ruledlist .c-rows { max-width: var(--c-list-measure); width: 100%; text-align: left; }
.cs-ruledlist-sec .c-heading--display { text-align: center; max-width: 34ch; }
@media (max-width: 767px) { .cs-ruledlist { max-width: 100%; } }"""

# FAQ accordion: centered eyebrow/heading (matches the ruled-list/conversion centered-
# stack convention), LEFT-aligned Q&A list for readability. Native <details>/<summary> —
# no boxed/card look (no-cards-on-cream, no-shadows): rows separated by the brand's
# existing hairline device only, the disclosure marker is a plain +/- glyph that rotates,
# never an icon sprite/chevron asset.
SCAFFOLD_FAQ_CSS = """.cs-faq-sec { display: flex; justify-content: center; }
.cs-faq { display: flex; flex-direction: column; align-items: center; text-align: center;
  gap: var(--c-block-gap); max-width: 52rem; width: 100%; }
.cs-faq-sec .c-heading--display { text-align: center; max-width: 34ch; }
.c-faq-list { width: 100%; text-align: left; }
.c-faq-item { position: relative; padding: 1.5rem 0; }
.c-faq-item::before { content: ""; position: absolute; left: 0; right: 0; top: 0; height: 1px;
  background: var(--c-hairline); }
.c-faq-item:last-child { padding-bottom: 0; }
.c-faq-q { font-family: var(--c-font-heading); font-size: var(--c-h3-size); color: var(--c-ink);
  cursor: pointer; list-style: none; display: flex; align-items: baseline;
  justify-content: space-between; gap: 1.5rem; }
.c-faq-q::-webkit-details-marker { display: none; }
/* disclosure glyph rides the question register: a fixed ratio of the brand's own h3
   question size (1.25rem was 1.625rem x 0.7692 against the pre-token render). */
.c-faq-icon { font-family: var(--c-font-body);
  font-size: calc(var(--c-h3-size) * 0.7692); color: var(--c-ink-muted);
  flex: 0 0 auto; transition: transform var(--c-motion-fast) var(--c-ease); }
.c-faq-item[open] .c-faq-icon { transform: rotate(45deg); }
.c-faq-a { font-family: var(--c-font-body); font-size: var(--c-body-size); line-height: 1.55em;
  color: var(--c-ink-muted); max-width: 56ch; margin-top: 0.85rem; }
@media (max-width: 767px) { .cs-faq { max-width: 100%; } .c-faq-q { font-size: var(--c-h3-size); } }"""

# heritage timeline (collage variant): reuses the collage grid; ghost numerals span WIDER
# (a year range reads wider than a single word) and sit lower so they don't collide with
# the heading, per the pattern's own `anchor: behind-media` + `amount.class: medium` overlap.
SCAFFOLD_TIMELINE_CSS = """.cs-timeline-sec .cs-ghost--numerals { top: auto; bottom: -6%;
  right: -1cqw;
  font-size: var(--c-ghost-size,
    clamp(calc(var(--size-ghost-watermark-base) * 0.3429), 32cqw,
          calc(var(--size-ghost-watermark-base) * 0.9905)));
  /* provenance: structural — numeral-pair tightening (glyph-overlap micro-tracking of
     the year-range device, not a brand tracking token) */
  letter-spacing: -0.01em; }
@media (max-width: 767px) { .cs-timeline-sec .cs-ghost--numerals { bottom: auto; top: 2%; } }"""

# mission statement (split variant): anchored text beside a single flush media panel, NO
# ghost word — the plain sibling of the collage grammar. Alternates side via variantKnob
# (mediaSide) through a data attribute the composer could set; default media-right.
SCAFFOLD_STATEMENT_CSS = """/* on the SHARED 12-col grid: the old private 0.9fr/1.1fr
   ratio maps to a 5/7 span split (nearest whole-column spans preserving the
   text-narrower-than-media asymmetry); tracks + gutter come from SCAFFOLD_BASE_CSS.
   AS-19: the spans are VAR-DRIVEN with the editorial-offset defaults — a centered
   resolved anchor re-scopes them symmetric (text 3/-3, media 4/-4) via
   layout_placement_css, so the 6/-1 offset only ever applies to a side anchor. */
.cs-statement-grid { align-items: center; }
.cs-statement-text { grid-column: var(--c-statement-text-col, 1 / span 5);
  display: flex; flex-direction: column;
  gap: var(--c-block-gap); max-width: 46ch; }
.cs-statement-media { grid-column: var(--c-statement-media-col, 6 / -1); }
/* CR-6: bare palette ref — no literal fallback. Palette-less brands keep the intrinsic
   ratio (the aspect device is disabled, never another brand's crop). */
.cs-statement-media .c-image { width: 100%; aspect-ratio: var(--c-aspect-landscape); object-fit: cover; }
@media (max-width: 767px) { .cs-statement-grid { grid-template-columns: 1fr; gap: 2.5rem; }
  .cs-statement-text, .cs-statement-media { grid-column: 1; } }"""

# curator quote with portrait (split variant): heading-scale quote beside a hard-edged
# portrait; caption sits in the margin beside the portrait (matches editorial-collage's
# marginal-caption device, applied to a portrait instead of a landscape module photo).
SCAFFOLD_QUOTE_CSS = """/* on the SHARED 12-col grid: the old private 1.2fr/0.8fr ratio
   maps to a 7/5 span split (an almost exact match — 1.48 vs 1.5 — on the shared tracks);
   tracks + gutter come from SCAFFOLD_BASE_CSS. AS-19: spans are VAR-DRIVEN with the
   editorial-offset defaults — a centered resolved anchor re-scopes them symmetric. */
.cs-quote-grid { align-items: center; }
.cs-quote-text { grid-column: var(--c-quote-text-col, 1 / span 7);
  display: flex; flex-direction: column;
  gap: var(--c-block-gap); }
.cs-quote-text .c-heading--display { max-width: 20ch; }
.cs-quote-media { grid-column: var(--c-quote-media-col, 8 / -1);
  display: flex; flex-direction: column; gap: 0.75rem; }
.cs-quote-media .c-image { width: 100%; aspect-ratio: var(--c-aspect-portrait); object-fit: cover; }
@media (max-width: 767px) { .cs-quote-grid { grid-template-columns: 1fr; gap: 2.5rem; }
  .cs-quote-text, .cs-quote-media { grid-column: 1; } }"""

# visit band (split variant): intro heading over a static map with TWO cream panels
# overlapping its lower edge (panel-over-media, the sanctioned overlap type).
SCAFFOLD_VISIT_CSS = """.cs-visit-grid { position: relative; }
.cs-visit-media .c-image { width: 100%; aspect-ratio: var(--c-aspect-band); object-fit: cover; }
/* the panel PAIR keeps its own tight two-track split (a component cluster, not a page
   grid — a 6/6 span on the shared gutter would blow its 1.5rem seam to 6rem), but its
   seam + inset snap to --baseline multiples (1.5rem = 3, 2.5rem = 5) and its container
   registers to the shared measure via the SCAFFOLD_BASE_CSS container rule. (The old
   `margin-top: -4.5rem` was dead — the later `margin: 0 auto` shorthand reset it —
   so it is dropped rather than silently resurrected here.) */
.cs-visit-panels { position: relative; z-index: 1; display: grid;
  grid-template-columns: 1fr 1fr; gap: calc(3 * var(--baseline));
  padding: 0 calc(5 * var(--baseline)); }
.cs-visit-panels .cs-panel { box-shadow: none; }
@media (max-width: 767px) { .cs-visit-panels { grid-template-columns: 1fr;
  margin-top: calc(3 * var(--baseline)); padding: 0 1.25rem; } }"""

# gallery showcase (stack-fullbleed): full-bleed photo, thin utility row (eyebrow far
# left / static counter far right), margin caption below. No slider controls.
SCAFFOLD_GALLERY_CSS = """.cs-gallery-sec { padding-left: 0; padding-right: 0; }
.cs-gallery-utility { display: flex; align-items: center; justify-content: space-between;
  padding: 0 2.5rem; margin-bottom: 1.25rem; }
.cs-gallery-media { margin: 0; }
.cs-gallery-media .c-image { width: 100%; aspect-ratio: var(--c-aspect-band); object-fit: cover; display: block; }
.cs-gallery-caption { padding: 1rem 2.5rem 0; }
/* optional display header/cta (hero-through-gallery-band; #sec-1 dropped-heading fix).
   .cs-slot/.cs-foot membership means the resolved anchor (AS-18) aligns them. */
.cs-gallery-head { display: flex; flex-direction: column; gap: 1rem;
  padding: 0 2.5rem; margin-bottom: 2rem; }
.cs-gallery-cta { display: flex; align-items: center;
  gap: var(--c-block-gap); padding: 1.25rem 2.5rem 0; }
@media (max-width: 767px) { .cs-gallery-utility, .cs-gallery-caption { padding-left: 1.25rem;
  padding-right: 1.25rem; } .cs-gallery-head, .cs-gallery-cta { padding-left: 1.25rem;
  padding-right: 1.25rem; }
  .cs-gallery-media .c-image { /* provenance: structural — mobile recrop of the
    full-bleed band device (tall crop so the band keeps presence on a narrow frame;
    device geometry, not a brand ratio) */
    aspect-ratio: 4 / 5; } }"""


# cards (staggered caption cards — features-staggered-caption-cards, Claude Design #04):
# modules on the SHARED 12-col grid (the old private --c-column-ratio 1.2fr/1fr tracks map
# to a 7/5 span split), with the EVEN modules pushed down by --c-card-stagger — now an
# exact --baseline multiple, so the stagger reads as a deliberate registered offset
# against the shared grid instead of a floating scalar. Hard-edged: no radius/shadow.
SCAFFOLD_CARDS_CSS = """.cs-modules-sec { position: relative; }
.cs-modules-intro { margin-bottom: clamp(2.5rem, 6cqw, 5rem); }
.cs-modules { row-gap: clamp(calc(4 * var(--baseline)), 5cqw,
  calc(7 * var(--baseline))); align-items: start; }
.cs-modules > .cs-module:nth-child(odd) { grid-column: 1 / span var(--c-span-a, 7); }
.cs-modules > .cs-module:nth-child(even) { grid-column: span var(--c-span-b, 5) / -1; }
.cs-module { display: flex; flex-direction: column; gap: 0.9rem; }
/* the second (even) module is staggered downward so the columns never line up — the drop
   is a whole number of baselines (registration, not a float). Chrome-less: NO
   background/border/radius/shadow — depth from the stagger + whitespace only (so this is
   an editorial module, not a prohibited cream card). */
.cs-modules > .cs-module:nth-child(even) {
  margin-block-start: var(--c-card-stagger, calc(7 * var(--baseline))); }
/* PER-COLUMN placement (editorial-harvest-2026-07, staggered-caption-columns-3): a
   pattern's stagger.perColumn entries set --c-col-N/--c-drop-N (whole-column tracks +
   baseline-multiple drops) via pattern_treatment_css; the var() DEFAULTS reproduce the
   odd/even geometry exactly, so every existing render is computed-value unchanged. */
.cs-modules > .cs-module:nth-child(1) {
  grid-column: var(--c-col-1, 1 / span var(--c-span-a, 7));
  margin-block-start: var(--c-drop-1, 0); }
.cs-modules > .cs-module:nth-child(2) {
  grid-column: var(--c-col-2, span var(--c-span-b, 5) / -1);
  margin-block-start: var(--c-drop-2, var(--c-card-stagger, calc(7 * var(--baseline)))); }
.cs-modules > .cs-module:nth-child(3) {
  grid-column: var(--c-col-3, 1 / span var(--c-span-a, 7));
  margin-block-start: var(--c-drop-3, 0); }
.cs-module-media { margin: 0; width: 100%; overflow: hidden; border-radius: 0; }
.cs-module-media .c-image { width: 100%; height: 100%; }
@media (max-width: 767px) { .cs-modules { grid-template-columns: 1fr; gap: 2.5rem; }
  .cs-modules > .cs-module:nth-child(odd), .cs-modules > .cs-module:nth-child(even) {
    grid-column: 1; margin-block-start: 0; } }"""

# interlock (float-wrap statement + inset image — editorial-interlocking-inset, Claude
# Design #11): the image FLOATS to one side (--c-float-side / --c-inset-width / --c-inset-
# margin) and the long statement heading WRAPS around it; the caption's big --c-inset-drop
# bottom margin drops the headline so its first lines sit level with the image. The display
# heading runs full measure at a CONTAINED editorial scale (not the poster hero scale) so a
# 100–160ch statement wraps convincingly. Hard-edged, cq/rem units only.
# The float mechanism is KEPT (grid cannot wrap running text around a block), but its
# geometry snaps to the shared units: the inset width is a whole-column SPAN of the shared
# grid (7 cols + 6 gutters ≈ the old 52%) and the margins/drop are --baseline multiples,
# so the inset's edge and the headline's first line register to shared lines.
SCAFFOLD_INTERLOCK_CSS = """.cs-interlock { position: relative; }
.cs-interlock-media { float: var(--c-float-side, right);
  width: var(--c-inset-width, calc(7 * var(--col) + 6 * var(--grid-gutter, 6rem)));
  margin: var(--c-inset-margin, calc(1 * var(--baseline)) 0
          calc(2 * var(--baseline)) calc(6 * var(--baseline)));
  /* aspect alias only (no literal fallback): brands without an aspectPalette let the
     media keep its natural ratio — device disabled, never a foreign crop. */
  aspect-ratio: var(--c-aspect-landscape); overflow: hidden; border-radius: 0; }
.cs-interlock-media .c-image { width: 100%; height: 100%; }
.cs-interlock-caption { display: block;
  margin-bottom: var(--c-inset-drop, clamp(calc(9 * var(--baseline)), 12cqw,
    calc(22 * var(--baseline)))); }
.cs-interlock .c-heading--display { max-width: none; text-align: left;
  /* interlock display de-scales from the brand's display tier (0.3333/0.6 of the
     measured base — ratios are structure, the rem magnitude is the brand's). */
  font-size: clamp(calc(var(--size-display-hero-base) * 0.3333), 4.4cqw,
                   calc(var(--size-display-hero-base) * 0.6));
  line-height: 1.06em; }
.cs-interlock-clear { clear: both; }
/* support/CTA foot cluster (rendered ONLY when the composition binds those slots —
   ANCHORED-REPORT composer-gap #2 fix; legacy interlock sections emit no foot). */
.cs-interlock-foot { display: flex; flex-direction: column; align-items: flex-start;
  gap: var(--c-block-gap); margin-top: var(--c-block-gap); }
@media (max-width: 767px) { .cs-interlock-media { float: none; width: 100%; margin: 0 0 1.75rem;
  /* provenance: structural — mobile recrop: the un-floated interlock media needs a
     bounded height (device geometry, not a brand ratio) */
  aspect-ratio: 3 / 2; } .cs-interlock-caption { margin-bottom: 1.25rem; } }"""


# overlay (editorial-harvest-2026-07): ONE positioning context — an in-flow media canvas
# (full-bleed / framed) with grid-registered ABSOLUTE layers over it (panel-on-media,
# straddles, scrim bands, rails, corner cues) and in-flow tucked headings before it.
# Hard-edged, flat fills only (no gradient/shadow/radius); offsets are --baseline /
# --col multiples so every layer registers to the shared grid.
SCAFFOLD_OVERLAY_CSS = """.cs-overlay-sec { position: relative; }
.cs-overlay-sec.cs-ov--bleed { padding-left: 0; padding-right: 0; }
.cs-ov-frame { position: relative; max-width: var(--content-measure, 86rem);
  margin-inline: auto; }
.cs-ov--bleed .cs-ov-frame { max-width: none; }
.cs-ov-canvas { position: relative; margin: 0; min-height: calc(48 * var(--baseline)); }
.cs-ov-canvas > .c-image, .cs-ov-canvas > .c-image-ph {
  width: 100%; height: 100%; min-height: inherit; object-fit: cover; }
/* framed (G4): page margins visible on ALL sides — the frame is an inset canvas other
   slots register against (never edge-to-edge, never a border). */
.cs-ov-canvas--framed { margin-inline: auto; }
/* flat surface-toned wash (sanctioned text-on-media mitigation; never a gradient). */
.cs-ov-scrim { position: absolute; inset: 0; z-index: 1; }
/* panel-on-media (G1): a SOLID panel floated over the canvas — the sanctioned
   panel-over-media pair. Own opaque surface scope (like the split's .cs-panel), so its
   text never composites against the photograph. Flat: no shadow, no radius. */
.cs-ov-panel { position: absolute; z-index: 3; top: 50%; transform: translateY(-50%);
  min-height: 62%; display: flex; flex-direction: column; gap: var(--c-block-gap);
  background: var(--c-panel); color: var(--c-panel-ink);
  /* light panel surface: interaction tokens re-scope with ink (AS-20) — no dark-surface
     accent hover leaking onto the light overlay panel. CS-1: literal fallbacks gone. */
  --c-ink: var(--c-panel-ink); --c-accent: var(--c-panel-ink);
  --c-ink-muted: var(--c-panel-ink);
  --c-link-hover: var(--c-panel-ink);
  --c-hairline: var(--c-panel-hairline);
  padding: calc(6 * var(--baseline)) calc(5 * var(--baseline)); }
/* panel display steps DOWN from the section's own display alias — --c-display-size is
   always emitted per section (component_vars), so no literal fallback (AS-24). */
.cs-ov-panel .c-heading--display { font-size: calc(0.62 * var(--c-display-size));
  max-width: 14ch; }
/* sidebar rail: the full-height panel column (ref 3) — space-between stack. */
.cs-ov-rail { top: 0; bottom: 0; transform: none; min-height: 0;
  justify-content: space-between; }
/* straddle (G2, z:front): a display heading riding over a crossed edge/seam. */
.cs-ov-straddle { position: absolute; z-index: 4; }
.cs-ov-straddle .c-heading--display { max-width: none; }
/* tuck (G2 z:back + G8 params): the heading row sits in flow BEFORE the canvas and the
   canvas rides OVER its lower part by the registered depth (media z above heading z). */
.cs-ov-headrow--tucked { display: flex; align-items: flex-start; gap: var(--grid-gutter, 6rem);
  position: relative; z-index: 0; margin-bottom: calc(-1 * var(--c-tuck-depth, calc(4 * var(--baseline)))); }
.cs-ov-headrow--tucked ~ .cs-ov-canvas { z-index: 2; }
.cs-ov-headrow-side { margin-inline-start: auto; }
/* scrim-band (G3): a FLAT translucent band across the canvas (fill set inline from the
   section surface + opacityClass — an rgba literal, never a gradient). */
.cs-ov-scrimband { position: absolute; left: 0; right: 0; z-index: 2; display: flex;
  gap: var(--grid-gutter, 6rem); align-items: center;
  padding: calc(3 * var(--baseline)) calc(4 * var(--baseline)); }
.cs-ov-scrim-item { display: flex; flex-direction: column; gap: calc(1 * var(--baseline)); }
.cs-ov-scrim-item .cs-sub { max-width: 24ch; }
/* corner-registered cues/support + in-frame annotations. */
.cs-ov-corner, .cs-ov-placed { position: absolute; z-index: 4; }
.cs-ov-corner--br, .cs-ov-corner--bl { text-align: right; }
/* break-frame (G6): corner-anchored DECORATION crossing the frame edge — area-capped,
   pointer-events none, never over text (decoration-salience applies). */
.cs-ov-breakframe { position: absolute; z-index: 4; pointer-events: none; }
.cs-overlay-sec:has(.cs-ov-breakframe) .cs-ov-frame { overflow: visible; }
/* stepped-lines (G7): per-line registered indents in half-column units. */
.cs-ov-stepped .c-heading-line:nth-child(1) { margin-inline-start: var(--c-step-1, 0); }
.cs-ov-stepped .c-heading-line:nth-child(2) { margin-inline-start: var(--c-step-2, 0); }
.cs-ov-stepped .c-heading-line:nth-child(3) { margin-inline-start: var(--c-step-3, 0); }
.cs-ov-stepped .c-heading-line:nth-child(4) { margin-inline-start: var(--c-step-4, 0); }
/* type-behind-media (G8): REAL heading at z:0, media stack above (media z 2, detail 3);
   the detail image registers to the main's bottom-right corner (media-over-media). */
.cs-ov-tbm-sec .cs-eyebrow-wrap { text-align: center; margin-bottom: calc(4 * var(--baseline)); }
.cs-ov-behind { position: relative; z-index: 0; text-align: center; }
.cs-ov-behind .c-heading--display { max-width: none; text-align: center;
  /* rides the section's display alias, always emitted per section — no literal fallback */
  font-size: calc(1.25 * var(--c-display-size)); line-height: 1.02em; }
.cs-ov-media-stack { position: relative; z-index: 2; }
.cs-ov-media-stack > .c-image, .cs-ov-media-stack > .c-image-ph { width: 100%; }
.cs-ov-detail { position: absolute; z-index: 3;
  right: calc(-3 * var(--baseline)); bottom: calc(-4 * var(--baseline)); }
.cs-ov-flank { position: absolute; top: 55%; z-index: 4; max-width: 16ch; }
.cs-ov-flank--left { left: 0; }
.cs-ov-flank--right { right: 0; text-align: right; }
/* foot cluster for unplaced support/cta slots. */
.cs-ov-foot { display: flex; flex-direction: column; align-items: flex-start;
  gap: var(--c-block-gap); margin-top: var(--c-block-gap); }
.cs-ov-foot-item { max-width: 46ch; }
@media (max-width: 767px) {
  .cs-ov-panel, .cs-ov-rail { position: static; transform: none; width: 100% !important;
    left: auto !important; min-height: 0; margin-top: var(--c-block-gap); }
  .cs-ov-straddle, .cs-ov-placed { position: static; max-width: none !important;
    margin: var(--c-block-gap) 0 0; }
  .cs-ov-corner { position: static; text-align: left; margin-top: var(--c-block-gap); }
  .cs-ov-headrow--tucked { flex-direction: column; gap: 1.25rem; margin-bottom: 0; }
  .cs-ov-scrimband { position: static; flex-direction: column; align-items: flex-start; }
  .cs-ov-media-stack { margin-top: 0 !important; margin-inline: auto !important; }
  .cs-ov-flank { position: static; max-width: none; margin-top: 1.25rem; }
  .cs-ov-detail { position: static; width: 60% !important; margin-top: 0.75rem; }
  .cs-ov-canvas { min-height: 0; } }"""

# banded (G9): TWO stacked full-width surface bands with a hard horizontal seam — the
# 90°-rotation of the split's flush halves. The straddler pulls up across the seam by a
# registered --baseline multiple (in flow, so following content clears it naturally).
SCAFFOLD_BANDED_CSS = """.cs-banded-sec { padding: 0; }
.cs-band { position: relative; }
.cs-band--top .cs-band-media { margin: 0; }
.cs-band--top .c-image, .cs-band--top .c-image-ph { width: 100%;
  height: calc(56 * var(--baseline)); object-fit: cover; display: block; }
/* the on-photo caption rides a small solid panel CHIP (sanctioned panel-over-media) —
   never bare text on the photograph. */
.cs-band-chip { position: absolute; top: calc(5 * var(--baseline));
  left: 50%; transform: translateX(-50%); z-index: 1;
  padding: calc(1 * var(--baseline)) calc(3 * var(--baseline)); }
.cs-band--bottom { padding: 0 var(--c-section-pad-x)
  var(--c-section-pad-bottom); }
.cs-band-straddler { position: relative; z-index: 2;
  margin-top: calc(-1 * var(--c-seam-rise, calc(12 * var(--baseline)))); }
.cs-band-straddler .c-image, .cs-band-straddler .c-image-ph { width: 100%; }
.cs-band-body { max-width: var(--content-measure, 86rem); margin-inline: auto;
  display: flex; flex-direction: column; gap: var(--c-block-gap);
  padding-top: var(--c-block-gap); }
@media (max-width: 767px) {
  .cs-band--top .c-image, .cs-band--top .c-image-ph { height: calc(36 * var(--baseline)); }
  .cs-band-straddler { width: 100% !important; margin-inline: 0 !important;
    --c-seam-rise: calc(6 * var(--baseline)); } }"""


# generic-flow (graceful fallback): a stacked column; text items follow the block-gap
# rhythm, media items run full measure. Hard-edged, cq/rem units only. Gaps use
# var()/clamp() so no bare off-scale rem token lands on a section selector (rhythm-clean).
# NB (AS-18): this scaffold NO LONGER hardcodes `align-items: flex-start` — the section's
# alignment is emitted by layout_placement_css from the RESOLVED anchor (section >
# pattern > style), never a silent left literal.
SCAFFOLD_FLOW_CSS = """.cs-flow { display: flex; flex-direction: column;
  gap: var(--c-block-gap); max-width: 72rem; }
.cs-flow-item { max-width: 62ch; }
.cs-flow-media { width: 100%; }
.cs-flow-media .c-image { width: 100%; height: auto; }
/* logo-strip device (AS-33): a HORIZONTAL row of partner/customer logo images —
   disk-backed extracted assets only (the adapter routes file-less entries to text
   captions instead). Gap rides the brand rhythm. Emphasis treatment (grayscale/…) is
   the STYLE layer's qualitative logoStrip flag (style_density_css), never hardcoded
   here. */
/* provenance: structural logo-strip-geometry — mark height/width caps are device frame
   geometry (same discipline as the nav-logo height cap); a brand chrome token
   (--c-logo-strip-h) wins over the structural default. */
.cs-logo-strip { display: flex; flex-direction: row; flex-wrap: wrap; align-items: center;
  gap: var(--c-block-gap); max-width: none; }
.cs-logo-strip-item { display: flex; align-items: center; }
.cs-logo-strip .c-logo--img { border: none; border-radius: 0; }
.cs-logo-strip .c-logo-img { height: var(--c-logo-strip-h, 2.25rem); width: auto;
  max-width: 10rem; object-fit: contain; }
@media (max-width: 767px) { .cs-flow { gap: clamp(1.25rem, 6cqw, 1.75rem); } }"""


_ARCHETYPE_SCAFFOLD = {
    "stack": SCAFFOLD_HERO_CSS,          # the hero stack; conversion stack uses its own block below
    "collage": SCAFFOLD_COLLAGE_CSS,
    "split": SCAFFOLD_SPLIT_CSS,
    "stack-fullbleed": SCAFFOLD_GALLERY_CSS,
    "cards": SCAFFOLD_CARDS_CSS,
    "interlock": SCAFFOLD_INTERLOCK_CSS,
    "overlay": SCAFFOLD_OVERLAY_CSS,
    "banded": SCAFFOLD_BANDED_CSS,
    "generic-flow": SCAFFOLD_FLOW_CSS,
}

# Layout-id overrides layered AFTER the archetype base (same dispatch discipline as the
# composer functions): a section sharing an archetype with another gets its OWN geometry
# on top of the shared base instead of a whole new archetype scaffold.
# Keyed by BOTH the resolved patternRef id (preferred — matches ANY layout instance
# reusing that pattern) and the legacy literal layout id (fallback for layouts with no
# patternRef). Looked up via `_scaffold_extra_for` below, never `.get(layout id)` alone —
# an id-only lookup here is exactly how `exhibition-curator-quote` got the composer's
# correct `.cs-quote-grid` markup but NONE of its matching CSS (only `curator-quote`, the
# original section's literal id, was ever a key).
# Id-specific PRIMARY scaffold overrides (selected INSTEAD of the archetype default,
# not layered after it like _LAYOUT_SCAFFOLD_EXTRA) -- keyed by patternRef id first, then
# literal layout id, mirroring the composer dispatch discipline (_pattern_id/_dispatch).
# BOTH scaffold_css() and compose_page.page_scaffold_css() consume this SAME dict, so
# adding a new id-specific scaffold only ever needs ONE registration, not two or three.
_LAYOUT_ID_SCAFFOLD = {
    # conversion-stack: kept here too (not JUST the "form" contract check below) so
    # page_scaffold_css() can bundle it from this ONE dict without also needing a
    # separate hardcoded reference -- that separate reference is what got dropped.
    "cta-underline-conversion-stack": SCAFFOLD_CONVERSION_CSS,
    "conversion-stack": SCAFFOLD_CONVERSION_CSS,
    "pricing-ruled-list-panel": SCAFFOLD_RULEDLIST_CSS,
    "schedule-ruled-list-panel": SCAFFOLD_RULEDLIST_CSS,
    "exhibition-tickets": SCAFFOLD_RULEDLIST_CSS,
    "exhibition-schedule": SCAFFOLD_RULEDLIST_CSS,
    "faq-accordion-list": SCAFFOLD_FAQ_CSS,
    "exhibition-faq": SCAFFOLD_FAQ_CSS,
}


def _primary_scaffold_for(layout):
    """The id-specific PRIMARY scaffold override for this layout (patternRef id first,
    then literal layout id), or None when no override applies (caller falls back to the
    archetype default)."""
    return _LAYOUT_ID_SCAFFOLD.get(_pattern_id(layout)) \
        or _LAYOUT_ID_SCAFFOLD.get((layout or {}).get("id"))


_LAYOUT_SCAFFOLD_EXTRA = {
    "heritage-timeline": SCAFFOLD_TIMELINE_CSS,
    "heritage-ghost-numerals-timeline": SCAFFOLD_TIMELINE_CSS,
    "mission-statement": SCAFFOLD_STATEMENT_CSS,
    "about-anchored-statement": SCAFFOLD_STATEMENT_CSS,
    "curator-quote": SCAFFOLD_QUOTE_CSS,
    "curator-quote-portrait-collage": SCAFFOLD_QUOTE_CSS,
    "visit-band": SCAFFOLD_VISIT_CSS,
    "visit-dual-panel-map": SCAFFOLD_VISIT_CSS,
}


def _scaffold_extra_for(layout):
    return _LAYOUT_SCAFFOLD_EXTRA.get(_pattern_id(layout)) \
        or _LAYOUT_SCAFFOLD_EXTRA.get((layout or {}).get("id"), "")


def _align_role_keys(layout, pattern=None) -> list[str]:
    """Candidate role keys for the STYLE-layer alignment lookup, most specific first:
    the section's composition useCase, the pattern's useCase, the `conversion`
    disambiguation for a form-bearing stack, then the renderer archetype(s)."""
    keys: list[str] = []
    comp = (layout or {}).get("_composition") or {}
    if comp.get("useCase"):
        keys.append(str(comp["useCase"]).lower())
    if pattern is not None and pattern.use_case:
        keys.append(str(pattern.use_case).lower())
    archetype = ((layout or {}).get("archetype") or "").lower()
    contracts = {m.get("contract") for m in ((layout or {}).get("blockMapping") or [])}
    if archetype == "stack":
        # the `stack` dispatcher serves BOTH the hero bookend and the conversion CTA
        keys.append("conversion" if "form" in contracts else "hero")
    if archetype:
        keys.append(archetype)
    if pattern is not None and pattern.archetype_ref:
        keys.append(str(pattern.archetype_ref).lower())
    return keys


def resolve_alignment(layout, pattern=None, style_ctx=None) -> dict | None:
    """THE single alignment resolution chain (anti-ai-slop.md AS-18):

        section-explicit ``alignment`` > pattern ``contentShape.alignment`` >
        style role default (StyleStructure.align_for)

    Never a silent CSS fall-through: every resolved stance carries its winning SOURCE
    ("section" | "pattern" | "style"), stamped on the section wrapper as
    ``data-align-source`` (mirrors data-pattern). Out-of-enum anchors warn loudly (via
    ``ll.normalize_anchor``) and fall through to the next layer EXPLICITLY. Returns
    ``{"anchor", "source", "counterweight"}`` or None only when NO layer declares a
    stance (e.g. an unstyled legacy render — behavior unchanged)."""
    layout = layout or {}
    # 1. section-explicit (composition.v1 §4.6.5 / a layouts[] instance's own field)
    sec = layout.get("alignment")
    if isinstance(sec, dict):
        anchor = ll.normalize_anchor(
            sec.get("anchor"), where=f"layout '{layout.get('id')}' alignment")
        if anchor:
            counterweight = sec.get("counterweight")
            # COUNTERWEIGHT INHERITANCE (AS-18): a section that declares only an
            # asymmetric ANCHOR (the common LLM `knobs.align: left` path) inherits the
            # counterweight DEVICE from the deepest layer declaring one for the SAME
            # anchor — pattern first, then style. The anchor's source stays "section";
            # only when no layer declares a device does the stamp stay bare (and the
            # G10 gate then fails the page: that IS counterweight-less asymmetry).
            if counterweight is None and anchor in ("left", "right"):
                pa = pattern.alignment if pattern is not None else None
                if pa and pa.get("anchor") == anchor and pa.get("counterweight"):
                    counterweight = pa["counterweight"]
                elif style_ctx is not None and getattr(style_ctx, "active", False) \
                        and style_ctx.structure is not None \
                        and style_ctx.structure.declares_alignment():
                    # scan ALL candidate role keys (not first-hit): we want the style's
                    # device for THIS anchor — e.g. a testimonial-in-interlock section
                    # declares left; `testimonial: centered` says nothing about a left
                    # device, `interlock: {left, inset-media}` is the match.
                    for key in _align_role_keys(layout, pattern):
                        sa = style_ctx.structure.align_for(key)
                        if sa and sa.get("anchor") == anchor and sa.get("counterweight"):
                            counterweight = sa["counterweight"]
                            break
            return {"anchor": anchor, "source": "section",
                    "counterweight": counterweight}
    # 2. pattern contentShape.alignment (brand-schema §4.4)
    if pattern is not None:
        pa = pattern.alignment
        if pa:
            return {"anchor": pa["anchor"], "source": "pattern",
                    "counterweight": pa.get("counterweight")}
    # 3. style role default (machine-readable alignment block, styles.py)
    if style_ctx is not None and getattr(style_ctx, "active", False) \
            and style_ctx.structure is not None \
            and style_ctx.structure.declares_alignment():
        sa = style_ctx.structure.align_for(*_align_role_keys(layout, pattern))
        if sa:
            return {"anchor": sa["anchor"], "source": "style",
                    "counterweight": sa.get("counterweight")}
    return None


def align_stamp_attrs(resolved) -> str:
    """The ``data-align`` / ``data-align-source`` (+ counterweight) wrapper attributes
    for a resolved alignment (mirrors how data-pattern is stamped). "" when unresolved."""
    if not resolved:
        return ""
    attrs = (f' data-align="{cr.esc(resolved["anchor"])}"'
             f' data-align-source="{cr.esc(resolved["source"])}"')
    if resolved.get("counterweight"):
        attrs += f' data-align-counterweight="{cr.esc(str(resolved["counterweight"]))}"'
    return attrs


# Anchor -> (flex align-items, text-align) for the stack/flow families.
_ANCHOR_FLEX = {
    "centered": ("center", "center"),
    "left": ("flex-start", "left"),
    "right": ("flex-end", "right"),
}


def _anchor_css(sel: str, anchor: str) -> str:
    """Anchor CSS covering EVERY archetype's markup (AS-18: a declared anchor used to
    no-op on gallery-band/flow/overlay/banded markup because only the stack-family
    selectors were targeted). Includes the anchor-derived media-span vars the
    statement/quote scaffolds read (AS-19: media placement derives from the RESOLVED
    anchor — a centered stance gets a symmetric span, the 6/-1 editorial offset applies
    only to a side anchor)."""
    _slots_sel = f"{sel} .cs-slot, {sel} .cs-eyebrow-wrap, {sel} .cs-title, {sel} .cs-foot"
    if anchor == "space-between":
        # utility rows / logo strips: distribute along the row (the previously-dropped
        # out-of-enum value). Flow markup becomes a wrapping space-between row.
        return (f"{sel} .cs-flow {{ flex-direction: row; flex-wrap: wrap; "
                f"justify-content: space-between; align-items: baseline; max-width: none; }}\n"
                f"{sel} .cs-flow-item {{ max-width: 40ch; }}\n"
                f"{sel} .cs-gallery-utility {{ justify-content: space-between; }}")
    if anchor == "edge-to-edge":
        # full-bleed bands: content runs the full measure; no re-anchoring of text.
        return (f"{sel} .cs-flow {{ max-width: none; }}\n"
                f"{sel} .cs-flow-media {{ width: 100%; }}")
    if anchor not in _ANCHOR_FLEX:  # "mixed": per-slot placement wins; nothing global
        return ""
    flex, text = _ANCHOR_FLEX[anchor]
    margin = {"centered": "auto", "left": "0 auto", "right": "auto 0"}[anchor]
    parts = [
        f"{_slots_sel} {{ align-items: {flex}; text-align: {text}; }}",
        f"{sel} .cs-collage {{ margin-inline: {margin}; }}",
        f"{sel} .c-heading--display {{ text-align: {text}; margin-inline: {margin}; }}",
        # generic-flow (the SCAFFOLD_FLOW_CSS hardcoded flex-start is DELETED — the
        # resolved value is emitted here instead; AS-18)
        f"{sel} .cs-flow {{ align-items: {flex}; text-align: {text}; }}",
        # gallery band (stack-fullbleed): intro header + caption honor the anchor
        f"{sel} .cs-gallery-intro {{ text-align: {text}; }}",
        f"{sel} .cs-gallery-caption {{ text-align: {text}; }}",
        # cards / interlock intros
        f"{sel} .cs-modules-intro {{ text-align: {text}; }}",
        # overlay: in-flow foot cluster + tucked headrow honor the anchor
        f"{sel} .cs-ov-foot {{ align-items: {flex}; text-align: {text}; }}",
        # banded: the bottom band's body column
        f"{sel} .cs-band-body {{ align-items: {flex}; text-align: {text}; }}",
    ]
    if anchor == "centered":
        parts += [
            # conversion/ruled-list stacks are centered by their own scaffold; a
            # centered anchor is consistent (no-op). Statement/quote splits collapse
            # to SYMMETRIC spans (AS-19: 'What we hold' media no longer sits 6/-1
            # under centered text) and the text column centers.
            f"{sel} {{ --c-statement-text-col: 3 / -3; --c-statement-media-col: 4 / -4;"
            f" --c-quote-text-col: 3 / -3; --c-quote-media-col: 4 / -4; }}",
            f"{sel} .cs-statement-text, {sel} .cs-quote-text {{ align-items: center;"
            f" text-align: center; margin-inline: auto; }}",
            f"{sel} .cs-statement-media, {sel} .cs-quote-media {{ justify-self: center; }}",
        ]
    elif anchor == "right":
        parts += [
            # mirrored editorial offset: text right, media left (still asymmetric —
            # the offset is legal because the anchor is a SIDE anchor).
            f"{sel} {{ --c-statement-text-col: 8 / -1; --c-statement-media-col: 1 / span 7;"
            f" --c-quote-text-col: 6 / -1; --c-quote-media-col: 1 / span 5; }}",
            f"{sel} .cs-conversion {{ align-items: flex-end; text-align: right; }}",
        ]
    elif anchor == "left":
        parts += [
            f"{sel} .cs-conversion {{ align-items: flex-start; text-align: left; }}",
            f"{sel} .cs-conversion-sec {{ justify-content: flex-start; }}",
        ]
    return "\n".join(parts)


def layout_placement_css(sel: str, layout, resolved=None) -> str:
    """Per-section PLACEMENT CSS (grid/overlap contract §4.6.5), scoped to ``sel``.
      - ``resolved`` alignment (from ``resolve_alignment``; falls back to the layout's
        own declared ``alignment`` for callers that don't resolve): the anchor CSS now
        covers EVERY archetype's markup — stack family, generic-flow, gallery band,
        cards, overlay, banded — instead of no-oping outside the stack family (AS-18),
        and derives the statement/quote media spans from the anchor (AS-19).
      - ``_grid`` {columns, gutter}: re-scopes the SECTION's --grid-cols/--grid-gutter/
        --col registration vars (the page-level shared grid is untouched).
      - ``_floatSide``: mirrors the interlock inset side (--c-float-side)."""
    if not layout and not resolved:
        return ""
    layout = layout or {}
    out: list[str] = []
    if resolved is None and isinstance(layout.get("alignment"), dict):
        anchor = ll.normalize_anchor(layout["alignment"].get("anchor"),
                                     where=f"layout '{layout.get('id')}' alignment")
        if anchor:
            resolved = {"anchor": anchor, "source": "section",
                        "counterweight": layout["alignment"].get("counterweight")}
    if resolved:
        css = _anchor_css(sel, resolved["anchor"])
        if css:
            out.append(f"/* alignment: {resolved['anchor']} (source: {resolved['source']}"
                       + (f", counterweight: {resolved['counterweight']}"
                          if resolved.get("counterweight") else "")
                       + ") — resolved, never fall-through (AS-18) */\n" + css)
    decls: list[str] = []
    g = layout.get("_grid") or {}
    if g.get("columns"):
        try:
            n = max(1, int(g["columns"]))
            decls.append(f"--grid-cols: {n};")
            decls.append(f"--col: calc((100% - {n - 1} * var(--grid-gutter, 6rem)) / {n});")
        except (TypeError, ValueError):
            pass
    gutter = str(g.get("gutter") or "").strip()
    if gutter and re.fullmatch(r"[\w.%()\s+*/-]+", gutter):
        decls.append(f"--grid-gutter: {gutter};")
    side = layout.get("_floatSide")
    if side in ("left", "right"):
        decls.append(f"--c-float-side: {side};")
    if decls:
        out.append(f"{sel} {{ {' '.join(decls)} }}")
    if not out:
        return ""
    return "/* per-section placement (composition.v1 §4.6.5) */\n" + "\n".join(out)


def scaffold_css(doc, layout, style_ctx=None) -> str:
    """Return the base scaffold + this layout's archetype geometry. Brand-token driven,
    container-query / rem units only (never viewport). Vertical rhythm (section padding +
    inter-block gaps) comes from ``rhythm_for`` — brand spacing tokens preferred, else the
    active style's spacing scale."""
    role, _surf = resolve_surface_intent(doc, layout)
    archetype = (layout.get("archetype") or "stack").lower()
    contracts = {m.get("contract") for m in (layout.get("blockMapping") or [])}
    primary = _primary_scaffold_for(layout)
    if primary:
        arch_css = primary
    elif archetype == "stack" and "form" in contracts:
        arch_css = SCAFFOLD_CONVERSION_CSS
    else:
        arch_css = _ARCHETYPE_SCAFFOLD.get(archetype, SCAFFOLD_HERO_CSS)
    extra = _scaffold_extra_for(layout)
    if extra:
        arch_css = arch_css + "\n" + extra
    # AS-37: the art-panel device CSS ships ONLY on sections that actually render it,
    # so no-radius brand pages never carry its rounded-panel rule (see the blob note).
    if (layout or {}).get("_artPanel") is not None:
        arch_css = arch_css + "\n" + SCAFFOLD_ART_PANEL_CSS
    return rhythm_vars_css(doc, style_ctx, role) + "\n" + SCAFFOLD_BASE_CSS + "\n" + arch_css


def root_vars(doc, surf, *, display_size, title_overlap, surface_role=None) -> str:
    """Emit the document :root for the single-section path. Carries the gate-readable
    legacy brand vars (`--bg/--text/--accent/--font-heading/--font-body/--display-size/
    --radius`) as RESOLVED literals — they are the gate's authoritative-VALUES contract
    (extract_facts regexes them) — plus the `--c-*` aliases, which (token-layer-2026-07)
    are var() references into the generated layer-1 block via component_vars, the SAME
    emitter the full-page path uses (the old hand-mirrored copy drifted by design).
    Panel/ghost brand-constant aliases + the shared grid/baseline units live here too."""
    text = color_value(doc, surf.get("textPrimary")) or "#111111"
    accent = color_value(doc, surf.get("textAccent")) or text
    bg = surf.get("bg") or "#ffffff"
    # v1 DESCRIPTIVE surface ("image + dark scrim") — substitute the darkest brand color
    # so the legacy --bg literal stays on-palette (anti-ai-slop.md AS-02 shape).
    if not re.match(r"^(#|rgb|hsl|var\()", str(bg).strip()):
        _cands = [str(c.get("value") if isinstance(c, dict) else c)
                  for c in ((doc.get("tokens", {}) or {}).get("colors", {}) or {}).values()]
        _hexes = [h for h in _cands if re.match(r"^#[0-9a-fA-F]{6}$", h or "")]
        bg = min(_hexes, key=lambda h: int(h[1:3], 16) + int(h[3:5], 16) + int(h[5:7], 16)) \
            if _hexes else "#141414"
    heading_stack, _ = font_stack(doc, "display-hero", "Georgia, serif")
    body_stack, _ = font_stack(doc, "body", "system-ui, sans-serif")
    radius = spacing_value(doc, "radius-global", "0rem")
    alias_block = cr.component_vars(doc, surf, selector=":root",
                                    display_size="var(--display-size)",
                                    title_overlap=title_overlap,
                                    surface_role=surface_role)
    return f""":root {{
  /* gate-readable legacy brand vars (authoritative token VALUES) */
  --bg: {bg};
  --text: {text};
  --accent: {accent};
  --display-size: {display_size};
  --radius: {radius};
  --font-heading: {heading_stack};
  --font-body: {body_stack};
  /* brand-constant aliases for the collage ghost + the cream split panel (layer-1 refs;
     all four tokens are REQUIRED — generation hard-failed already if any were missing) */
  --c-ghost: var(--color-text-ghost-on-primary);
  --c-panel: var(--surface-surface-panel);
  --c-panel-ink: var(--color-text-on-primary);
  --c-panel-hairline: var(--color-border-hairline-on-primary);
  /* ONE shared page grid + baseline (alignment quick wins): every archetype scaffold
     places onto THESE tracks instead of private per-section grids, and every offset
     scalar snaps to --baseline / one --col so staggered elements REGISTER to shared
     lines instead of floating. --col resolves its 100% against the element it is used
     on (the section's shared-measure container). */
  --grid-cols: 12; /* provenance: structural — shared registration grid */
  --grid-gutter: 6rem; /* provenance: structural — registration gutter unit */
  --content-measure: 86rem; /* provenance: structural — shared content measure */
  --baseline: 0.5rem; /* provenance: structural — vertical registration unit */
  --col: calc((100% - 11 * var(--grid-gutter, 6rem)) / 12);
}}
{alias_block}"""


def style_density_css(style_ctx: RenderContext, *, heading_max: str = "18ch",
                      collage_rule: str = ".cs-collage { margin: 0; max-width: 64cqw; }") -> str:
    """The style layer's page-wide DENSITY/alignment default — the SINGLE shared source
    for BOTH override twins (compose_section.style_override_css +
    compose_page.page_style_override; AS-06/AS-18). When the style declares a
    machine-readable alignment stance, its DEFAULT anchor is emitted here (per-section
    resolution then wins by #sec-N specificity); a non-migrated style keeps the legacy
    left literals — the old behavior, now explicitly the style's documented base."""
    s = style_ctx.structure
    default = s.alignment_default if s.declares_alignment() else None
    default = default if default in _ANCHOR_FLEX else ("left" if default is None else "left")
    flex, text = _ANCHOR_FLEX[default]
    margin = {"centered": "auto", "left": "0 auto", "right": "auto 0"}[default]
    heading_margin = f" margin-inline: {margin};" if default != "left" else ""
    src = "style alignment.default (AS-18)" if s.declares_alignment() \
        else "legacy density literal (style declares no alignment stance)"
    return f"""/* density default — {src}: anchor '{default}'. Per-section resolution
   (section > pattern > style role) is emitted per #sec-N and wins by specificity. */
.cs-slot, .cs-foot, .cs-eyebrow-wrap, .cs-title {{ align-items: {flex}; text-align: {text}; }}
{collage_rule}
.c-heading--display {{ text-align: {text}; max-width: {heading_max};{heading_margin} }}{logo_strip_treatment_css(style_ctx)}"""


def logo_strip_treatment_css(style_ctx: RenderContext) -> str:
    """The STYLE layer's qualitative ``logoStrip`` flag (AS-33), realized as the
    logo-strip device's emphasis treatment. ONE shared implementation (called from
    style_density_css so both override twins inherit it — AS-06). The style file names
    only the QUALITATIVE treatment (monochrome | reduced | plain); the concrete
    realization below is structural device behavior, identical for every brand, with
    motion riding the brand's own tokens. A style with no flag (non-migrated) emits
    nothing — marks render as shipped."""
    s = style_ctx.structure
    t = getattr(s, "logo_strip", "")
    if t == "monochrome":
        return """
/* logoStrip: monochrome — marks read as a quiet grayscale row; full color on hover.
   provenance: structural logo-strip-treatment — the qualitative flag's fixed
   realization (emphasis fractions are device behavior, not brand values). */
.cs-logo-strip .c-logo-img { filter: grayscale(1); opacity: 0.72;
  transition: filter var(--c-motion-fast) var(--c-ease),
              opacity var(--c-motion-fast) var(--c-ease); }
.cs-logo-strip .c-logo--img:hover .c-logo-img,
.cs-logo-strip .c-logo--img:focus-visible .c-logo-img { filter: none; opacity: 1; }"""
    if t == "reduced":
        return """
/* logoStrip: reduced — marks keep their own ink but sit back from the content.
   provenance: structural logo-strip-treatment — the qualitative flag's fixed
   realization (emphasis fractions are device behavior, not brand values). */
.cs-logo-strip .c-logo-img { opacity: 0.78;
  transition: opacity var(--c-motion-fast) var(--c-ease); }
.cs-logo-strip .c-logo--img:hover .c-logo-img,
.cs-logo-strip .c-logo--img:focus-visible .c-logo-img { opacity: 1; }"""
    return ""  # plain / style silent: marks as shipped, no treatment


def style_override_css(style_ctx: RenderContext) -> str:
    """STYLE layer layered OVER the brand base in CSS source order so the load-bearing
    structural rules win (precedence engine, expressed in CSS). Brand still supplies
    hues+fonts via the merged slots; the style dictates structure. cq-units only."""
    s = style_ctx.structure
    return f"""
/* ===================================================================== */
/* STYLE: {style_ctx.style_id} (structure) layered OVER brand (hues+fonts). */
/* ===================================================================== */
:root {{
  /* PER-SURFACE HUES ARE NOT SET HERE (anti-ai-slop AS-06/AS-01): this override once
     forced --c-paper/--c-ink/--c-accent to the brand's LIGHT slots at :root, clobbering
     a DARK section's own surface in single-section renders — visit-band painted its
     on-dark text colors onto the style's cream paper (1.30:1, caught by contrast_audit).
     The full-page override (compose_page.page_style_override) never set hues; parity
     restored. Surface hues come from root_vars/component_vars per section. */
  --c-radius: {s.radius};
  --c-display-size: {s.display_size_css() if s.display_source != "brand" else "var(--size-display-hero)"};
  --c-display-lh: {s.display_leading};
  --c-display-ls: {s.display_tracking};
  --c-font-heading: '{style_ctx.font_display}', Georgia, serif;
  --c-font-body: '{style_ctx.font_body}', system-ui, sans-serif;
}}
/* Vertical padding comes from the rhythm scale / brand tokens (symmetric top=bottom),
   not ad-hoc literals; horizontal stays the style's asymmetric cqw inset. The rhythm
   vars are guaranteed by rhythm_vars_css on every render path, so the references are
   fallback-free (AS-24 / remote-fix blocker-4: a literal fallback is unwrapped by the
   provenance scanner and collides cross-brand). */
.cs-section {{ padding: var(--c-section-pad-top) 12cqw
                        var(--c-section-pad-bottom) 6cqw; }}
{style_density_css(style_ctx)}
/* color deployment: single committed accent (the eyebrow slug); everything else ink. */
.c-heading--accent {{ color: var(--c-ink); }}
.c-eyebrow {{ color: var(--c-accent); }}
"""


# ── document assembly ─────────────────────────────────────────────────────────────

def build_document(doc, layout, brand_yaml, style_ctx: RenderContext) -> str:
    role, surf = resolve_surface_intent(doc, layout)
    ctx = cr.make_context(doc, role, surf)
    ctx.style_active = bool(style_ctx and style_ctx.active)
    ctx.style_id = style_ctx.style_id if ctx.style_active else ""
    # style-aware cta-shape (B5) — same resolution as the full-page path.
    ctx.cta = cr.cta_shape(doc, style_ctx.structure if ctx.style_active else None)

    rendered = render_slots(doc, layout, ctx)
    archetype = (layout.get("archetype") or "stack").lower()
    composer = ARCHETYPE_COMPOSERS.get(archetype, compose_stack_hero)
    section_html = composer(doc, layout, ctx, rendered, style_ctx)

    name = doc["brand"]["name"]
    gf = google_fonts_link(loadable_proxies(doc))
    disp_size = f"{base_size(type_role(doc, 'display-hero')) or 6}rem"
    overlap = (layout.get("overlapRules", {}) or {}).get("offsets", {}).get("titleOverMediaTop")
    # layer-1 generated tokens block (token-layer 2026-07): the measured brand values every
    # var() below resolves against. Fail-loud on missing REQUIRED tokens (DECISIONS.md #2).
    tokens_bundle = tokens_css.build_page_tokens(doc, style_ctx, brand_yaml_path=brand_yaml)
    vars_css = root_vars(doc, surf, display_size=disp_size, title_overlap=overlap,
                         surface_role=role)
    css = vars_css + "\n" + cr.COMPONENT_CSS + cr.structural_variant_css(doc) \
        + "\n" + cr.link_hover_css(doc) + cr.nav_hover_css(doc) \
        + "\n" + scaffold_css(doc, layout, style_ctx)
    if ctx.style_active:
        css += "\n" + style_override_css(style_ctx)
        # ACCENT COLLAPSE PARITY (anti-ai-slop.md AS-06 + AS-10): the full-page path
        # (compose_page.section_vars) collapses --c-accent to ink for every non-accent
        # section; this single-section path applied the style's gold accent at :root
        # UNCONDITIONALLY, so variant/preview renders showed the gold eyebrow on the
        # cream surface — a 1.3:1 contrast failure AND a no-accent-on-light violation
        # visible only in single-section renders, never on the full page. Collapse on
        # light (no-textAccent) surfaces; dark surfaces keep the sanctioned accent.
        if not surf.get("textAccent"):
            css += "\n:root { --c-accent: var(--c-ink); /* no-accent-on-light */ }"

    # Reuse-before-create: resolve the reusable layout PATTERN this section is generated from
    # and let its special treatments drive the geometry (pattern-driven, not reinvented).
    pattern, match_kind = resolve_pattern(doc, layout, brand_yaml)
    treat_css = pattern_treatment_css(pattern)
    if treat_css:
        css += "\n" + treat_css
    pat_attr = f' data-pattern="{cr.esc(pattern.id)}" data-pattern-lib="{cr.esc(pattern.lib)}"' \
        if pattern else ""
    pat_comment = (f"\n<!-- layout pattern REUSED ({match_kind}): {pattern.lib}:{pattern.id}"
                   f" — {cr.esc(pattern.intent)} -->" if pattern else "")

    # ALIGNMENT RESOLUTION (AS-18) — same chain as the full-page path: section-explicit >
    # pattern contentShape.alignment > style role default; emitted body-scoped and
    # stamped on <html> (single-section renders have no #sec-N wrapper).
    resolved_align = resolve_alignment(layout, pattern, style_ctx)
    align_attr = align_stamp_attrs(resolved_align)
    placement_css = layout_placement_css("body", layout, resolved=resolved_align)
    if placement_css:
        css += "\n" + placement_css

    face_css = font_face_css(Path(brand_yaml).parent, doc) if brand_yaml else ""
    parallax_css = cr.parallax_css(doc)  # "" unless the brand declared imageParallax

    html_attr = f' data-style="{style_ctx.style_id}"' if ctx.style_active else ""
    if ctx.style_active:
        # AS-18 stance self-declaration — mirrors compose_page.build_page: the G10 gate
        # judges stamps against the OPERATIVE style definition, stamped here, never by
        # re-loading today's styles/<id>.md (snapshot styles_dir renders differ).
        stance = "declared" if (style_ctx.structure is not None
                                and style_ctx.structure.declares_alignment()) else "none"
        html_attr += f' data-align-stance="{stance}"'
    parallax_attr = ' data-parallax-images="true"' if cr.image_parallax_spec(doc)["enabled"] else ""
    return f"""<!doctype html>
<html lang="en"{html_attr}{pat_attr}{align_attr}{parallax_attr}>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{cr.esc(name)} - {cr.esc(layout['id'])} (composed from catalog)</title>
{gf}
{tokens_css.style_tag(tokens_bundle)}
<style>
{face_css}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
img {{ display: block; max-width: 100%; }}
/* iframe-safe container context: cq* length units resolve against this sized box. */
html {{ background: var(--c-paper); height: 100%; }}
html, body {{ background: var(--c-paper); color: var(--c-ink); font-family: var(--c-font-body);
  -webkit-font-smoothing: antialiased; }}
body {{ min-height: 100%; container-type: size; container-name: frame; }}
{css}
{parallax_css}
</style>
</head>
<body>{pat_comment}
<!-- Section composed from the brand catalog: each slot is a catalog component rendered
     by component_render.py (the SAME renderers the components-preview gallery uses). -->
{section_html}
{cr.parallax_script_tags(doc)}
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser(description="Compose a section from the brand catalog.")
    ap.add_argument("brand_yaml", type=Path)
    ap.add_argument("layout_id")
    ap.add_argument("-o", "--out", type=Path, required=True)
    ap.add_argument("--style", default=None,
                    help="active STYLE id; layers the style's structure over brand hues/fonts.")
    args = ap.parse_args()

    doc = load_doc(args.brand_yaml)
    layout = find_layout(doc, args.layout_id)
    if layout is None:
        raise SystemExit(f"layout '{args.layout_id}' not found in {args.brand_yaml}")

    style_ctx = load_and_merge(args.style, doc) if args.style else inactive_context()

    args.out.mkdir(parents=True, exist_ok=True)
    # Resolve + copy the extracted nav logo BEFORE building the HTML so the composed nav can
    # reference the local, offline-safe asset (in-memory doc mutation only; brand.yaml unchanged).
    prepare_nav_logo(doc, Path(args.brand_yaml).parent, args.out / "assets")
    (args.out / "index.html").write_text(build_document(doc, layout, args.brand_yaml, style_ctx))
    # drift-detection + provenance-index sidecar (SPEC §B.1/§F) — same bundle the page embeds.
    tokens_css.write_manifest(
        args.out, tokens_css.build_page_tokens(doc, style_ctx, brand_yaml_path=args.brand_yaml))
    copied = copy_assets(Path(args.brand_yaml).parent, args.out / "assets")
    copied += copy_fonts(Path(args.brand_yaml).parent, args.out / "assets", doc)

    # report which slots resolved to which catalog component (the binding proof).
    ctx = cr.make_context(doc, *resolve_surface_intent(doc, layout))
    print(f"Composed '{layout['id']}' (archetype={layout.get('archetype')}) -> {args.out}/index.html")
    print(f"  assets: {', '.join(copied) or 'none'}"
          + (f"  [style:{style_ctx.style_id}]" if style_ctx.active else ""))
    pattern, match_kind = resolve_pattern(doc, layout, args.brand_yaml)
    if pattern:
        print(f"  layout pattern: REUSED ({match_kind}) [{pattern.lib}] {pattern.id}  "
              f"treatments={sorted(pattern.treatment_kinds())}")
    else:
        print("  layout pattern: none matched (archetype default)")
    print("  slot -> catalog component bindings:")
    for r in render_slots(doc, layout, ctx):
        renderer = cr.resolve_renderer(r["contract"])
        fn = getattr(renderer, "__name__", "UNRESOLVED")
        print(f"    [{r['slot']}] {r['role']:<26} contract={r['contract']:<10} "
              f"origin={r['origin'] or '?':<10} -> {fn}")


if __name__ == "__main__":
    main()
