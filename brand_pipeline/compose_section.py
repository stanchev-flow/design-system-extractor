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
import urllib.parse
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
ASSET_TAGS_KEY = "_assetTags"
MEDIA_TREATMENT_RULES_KEY = "_mediaTreatmentRules"


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
    ``_assetInventory`` key) plus captured asset-kind/media-treatment facts from
    ``assets-tagged.json``.  Facts stay in-memory and brand-local; malformed/missing
    metadata degrades to an empty registry. Idempotent; returns the doc for chaining."""
    if isinstance(doc, dict):
        doc[ASSET_INVENTORY_KEY] = brand_image_inventory(Path(brand_dir))
        tags: dict = {}
        rules: list = []
        tagged = Path(brand_dir) / "assets-tagged.json"
        try:
            payload = json.loads(tagged.read_text()) if tagged.is_file() else {}
        except Exception:
            payload = {}
        if isinstance(payload, dict):
            for asset in payload.get("assets") or []:
                if not isinstance(asset, dict):
                    continue
                name = Path(str(asset.get("filename") or "")).name
                if name:
                    tags[name] = {
                        "assetKind": asset.get("assetKind") or asset.get("useCase"),
                        "useCase": asset.get("useCase"),
                        **({"mediaTreatment": asset["mediaTreatment"]}
                           if isinstance(asset.get("mediaTreatment"), dict) else {}),
                    }
            rules = [r for r in (payload.get("mediaTreatmentRules") or [])
                     if isinstance(r, dict)]
        doc[ASSET_TAGS_KEY] = tags
        doc[MEDIA_TREATMENT_RULES_KEY] = rules
        attach_accent_devices(doc, brand_dir)
        # media-assets.v1 registry (media semantics 2026-07): per-asset
        # treatmentDefaults + logical-asset ids for the renderer/gates. Fact-gated:
        # brands without media-assets.yaml attach None and behave byte-identically.
        import media_semantics as _ms
        _ms.attach_media_assets(doc, brand_dir)
    return doc


ACCENT_GLYPHS_KEY = "_accentGlyphs"


def attach_accent_devices(doc: dict, brand_dir: Path) -> dict:
    """Resolve the brand's licensed accent-device GLYPH artwork (fix7 punch 3;
    brand-schema §4.11) into sanitized inline SVG on the in-memory doc — the same
    inline-SVG channel the chrome glyphs ride (fix4 sanitizer: currentColor,
    single-ink verified, never scripts/rasters). A device naming a file the brand's
    tree does not carry, or artwork the sanitizer refuses, resolves to NOTHING (the
    marked-list marker then degrades to the typographic dot — inventory law).
    Idempotent; brands without ``accentDevices`` attach an empty registry."""
    if not isinstance(doc, dict):
        return doc
    glyphs: dict[str, str] = {}
    for dev in (doc.get("accentDevices") or []):
        if not isinstance(dev, dict):
            continue
        kind = str(dev.get("kind") or "")
        asset = str(((dev.get("glyph") or {}) or {}).get("asset") or "").strip()
        if not asset or kind in glyphs:
            continue
        name = Path(asset).name
        hits = sorted(Path(brand_dir).rglob(name))
        src = next((h for h in hits if h.is_file() and "fonts" not in h.parts), None)
        if src is None:
            continue
        try:
            svg = cr.sanitize_inline_svg(src.read_text())
        except Exception:
            svg = None
        if svg:
            glyphs[kind] = svg
    doc[ACCENT_GLYPHS_KEY] = glyphs
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
    # inset-panel backdrop art (fid2 2026-07): the noise/texture/gradient family a
    # brand paints its rounded panel bands with (generic asset-role words only).
    "panel": ("noise", "texture", "gradient", "panel-art", "backdrop"),
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


# filename mentions inside a treatment's own prose (evidence, not invention): the
# art-surface note may name the exact art family file the capture shows.
_ART_FILE_RX = re.compile(r"[\w][\w.-]*\.(?:webp|png|jpe?g|avif|gif|svg)", re.I)


def _art_surface_src(doc, layout) -> str | None:
    """The band art for a section stamped ``_artSurface`` (fid5 2026-07): filenames
    the treatment itself names (explicit ``asset`` key, then any filename in its
    note prose) are preferred, then the brand's declared panel-art pins, then the
    generic noise/texture inventory match — all evidence-checked via _brand_art.
    None ⇒ the caller keeps the flat brand-surface fill (degrade, never invented)."""
    hint = layout.get("_artSurface")
    if not isinstance(hint, dict):
        return None
    named = []
    if hint.get("asset"):
        named.append(Path(str(hint["asset"])).name)
    named += _ART_FILE_RX.findall(str(hint.get("note") or ""))
    return _brand_art(doc, "panel", *named, *brand_default_art_names(doc, "panel"))

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
        stack = str(type_role(doc, role).get("family") or "")
        # Type roles carry a complete CSS stack while the registry is keyed by one
        # concrete face. Resolve every quoted/unquoted stack member in order so a
        # measured value such as `"Brand Display", "Brand Serif", serif` can bind
        # either captured family without requiring a non-CSS duplicate role value.
        for member in (part.strip().strip("\"'") for part in stack.split(",")):
            if member in reg and member not in seen:
                seen.add(member)
                fams.append(member)
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

def section_heading_level(doc) -> str:
    """The register NON-OPENING section headings ride (fid2 2026-07): a brand whose
    measured type ladder declares an h2 role under a canonical tier (the P1 extraction
    discipline) headlines its in-flow sections at that MEASURED h2 register — matching
    the source, where only the hero rides the display tier. Brands without the
    measured ladder keep the editorial display default (the historical behavior)."""
    meta = (doc or {}).get("meta") or {}
    type_roles = (((doc or {}).get("tokens") or {}).get("type")) or {}
    h2 = type_roles.get("h2")
    if isinstance(meta.get("canonicalTier"), dict) and isinstance(h2, dict) \
            and isinstance(h2.get("sizeRem"), dict):
        return "h2"
    return "display"


def load_doc(brand_yaml: Path) -> dict:
    doc = yaml.safe_load(Path(brand_yaml).read_text())
    # attach the ACTIVE brand's on-disk image inventory (AS-34) + authored section
    # copy so defaults resolve from the brand's own data — in-memory only.
    attach_brand_copy(doc, Path(brand_yaml).parent)
    return attach_asset_inventory(doc, Path(brand_yaml).parent)


# ── heading FIT-TO-MEASURE stepping (fix7 punch 5; AS-66) ─────────────────────────
# A display-rung heading placed in a SUB-MEASURE column steps DOWN the brand's own
# measured heading ladder until its projected line count fits the register cap
# (hero display: 3 lines — the archetype geometry's own 1–3 band; SR-HERO-01 is the
# detecting gate, this is the fix mechanic, same class as pass1's overlay-panel 0.6
# re-registration). Deterministic: a greedy word-wrap projection over the brand's
# measured tier sizes — never a browser call, never an invented size (every step is
# a measured rung, so scale_adherence holds by construction).

_FIT_LADDER = ("display", "h1", "h2")   # heading-register rungs, largest first
_FIT_CHAR_EM = 0.6                       # mean glyph advance (em) — calibrated on the
                                         # measured form-split wraps (5-line/4-line
                                         # cases @80px in a 500px column, stage B)


def _tier_px(doc, level: str) -> float | None:
    """The measured 1440-tier px size for a heading register (tiers.w1440.px first,
    sizeRem.base * 16 as the fallback). None when the brand never measured it."""
    role = "display-hero" if level == "display" else level
    spec = (((doc or {}).get("tokens") or {}).get("type") or {}).get(role)
    if not isinstance(spec, dict):
        return None
    tier = ((spec.get("tiers") or {}).get("w1440") or {})
    if isinstance(tier, dict) and isinstance(tier.get("px"), (int, float)):
        return float(tier["px"])
    sr = spec.get("sizeRem")
    base = sr.get("base") if isinstance(sr, dict) else sr
    return float(base) * 16.0 if isinstance(base, (int, float)) else None


def projected_line_count(text: str, font_px: float, measure_px: float,
                         char_em: float = _FIT_CHAR_EM) -> int:
    """Greedy word-wrap projection: words advance at ``len(word) * char_em * font``
    with a quarter-em space — the deterministic stand-in for the rendered break."""
    words = str(text or "").split()
    if not words or not font_px or not measure_px:
        return 1
    space = 0.25 * font_px
    lines, cur = 1, 0.0
    for w in words:
        wpx = len(w) * char_em * font_px
        if cur and cur + space + wpx > measure_px:
            lines += 1
            cur = wpx
        else:
            cur = (cur + space + wpx) if cur else wpx
    return lines


def heading_fit_level(doc, text: str, measure_px: float | None,
                      cap: int = 3) -> str:
    """The FIRST rung of the brand's measured heading ladder whose projected line
    count fits ``cap`` inside ``measure_px`` — 'display' when the display rung
    already fits (full-measure headings never step). Exhausting the ladder returns
    its last measured rung (the copy budget then carries the rest — SR-HERO-01)."""
    if not measure_px or not str(text or "").strip():
        return "display"
    fitted = "display"
    for level in _FIT_LADDER:
        px = _tier_px(doc, level)
        if px is None:
            continue
        fitted = level
        if projected_line_count(text, px, measure_px) <= cap:
            return level
    return fitted


def split_half_measure_px(doc, tracks: int = 6, of: int = 12) -> float | None:
    """The 1440-tier px width of a ``tracks``-of-``of`` split column under the
    brand's own container + column-gutter facts (the form-split copy column spans
    6 of 12 shared tracks with the column-to-column gutter between all of them).
    None when the brand declares no container width (no stepping — full measure)."""
    spacing = (((doc or {}).get("tokens") or {}).get("spacing")) or {}

    def _px(name):
        v = (spacing.get(name) or {}).get("value") if isinstance(spacing.get(name), dict) else None
        m = re.fullmatch(r"([\d.]+)\s*(rem|px|em)", str(v or "").strip())
        if not m:
            return None
        n = float(m.group(1))
        return n * 16.0 if m.group(2) in ("rem", "em") else n

    width = _px("container-max")
    if width is None:
        return None
    gutter = _px("column-to-column") or 32.0
    track = (width - (of - 1) * gutter) / of
    return max(0.0, tracks * track + (tracks - 1) * gutter)


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


# ── pattern INTERACTION DEVICES (P2 renderer capabilities, replica-gate punch list) ──
#
# A pattern's sanctioned specialTreatments can declare an INTERACTION DEVICE the static
# composers must draw (the capture shows its resting state; the treatment carries the
# evidence): a `marquee` logo track, an `inset-emphasis` accordion active state, an
# `edge-cut` carousel presentation. The treatments reference the brand's own token
# ROLES (surface/color roles), never literals — composers resolve them through the
# generated layer-1 vars, so a brand without the role degrades to the idle presentation.

def _token_var_slug(role) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(role or "").lower()).strip("-")


def stamp_pattern_devices(doc, layout, brand_yaml) -> None:
    """Stamp the resolved pattern's sanctioned interaction-device treatments onto the
    layout as private hints the archetype composers read (same private-key discipline
    as the adapter's ``_mediaLayers``/``_grid``). Idempotent; a layout already carrying
    a hint (e.g. set by a future composition adapter) keeps it. No pattern / no
    sanctioned device treatments ⇒ no stamp (all composers keep the static render)."""
    if not isinstance(layout, dict):
        return
    pattern, _kind = resolve_pattern(doc, layout, brand_yaml)
    if pattern is None:
        return
    for t in (pattern.special_treatments or []):
        if not isinstance(t, dict) or not t.get("sanctioned"):
            continue
        kind = str(t.get("kind") or "").lower()
        if kind == "marquee":
            hint: dict = {"target": t.get("target")}
            # MEASURED period (fid2 2026-07): the brand's marquee signature move may
            # carry the JS-computed duration serialized in the saved DOM
            # (measured.durationS) — the composed track then runs the source's real
            # period instead of the item-count approximation, and the page script
            # leaves it untouched.
            for m in (((doc.get("tokens") or {}).get("motion") or {})
                      .get("signatureMoves") or []):
                if not isinstance(m, dict):
                    continue
                probe = f"{m.get('name') or ''} {m.get('move') or ''}".lower()
                measured = m.get("measured") if isinstance(m.get("measured"), dict) else {}
                if ("marquee" in probe or "translatex(-50%)" in probe) \
                        and measured.get("durationS"):
                    try:
                        hint["durationS"] = float(measured["durationS"])
                    except (TypeError, ValueError):
                        pass
                    break
            layout.setdefault("_marquee", hint)
        elif kind == "inset-emphasis":
            layout.setdefault("_accordion", {
                "surfaceRole": t.get("surfaceRole"),
                "hoverWash": t.get("hoverWash"),
                # optional AFFORDANCE the evidence declares on the active item
                # (e.g. circle-arrow — the round go-affordance the capture shows).
                "affordance": t.get("affordance")})
        elif kind == "edge-cut":
            # measured rail CONTROLS (fix1 2026-07 item-8): a source rail that ships
            # visible round prev/next chrome declares it on the treatment
            # (`controls: {kind: round, pause: bool}`); the stamp stays truthy-True
            # for control-less rails (Remote parity — nothing invented there).
            if isinstance(t.get("controls"), dict):
                layout.setdefault("_edgeCut", {"controls": dict(t["controls"])})
            else:
                layout.setdefault("_edgeCut", True)
        elif kind == "carousel":
            # SPLIT-PANEL CAROUSEL statics (fix1 2026-07 item-6): a split section whose
            # sanctioned treatment declares a panel carousel over its list slot renders
            # the static-faithful device — slide 1 visible, siblings as hidden panels,
            # round prev/next + dot rail (consumed by compose_info_band). The media
            # slot's measured container fraction rides along (illustration column
            # share), same probe as the tabs device.
            hint = {"target": t.get("target")}
            for s in pattern.slots:
                if isinstance(s, dict) and str(s.get("name") or "") == "media":
                    ms = s.get("mediaScale") if isinstance(s.get("mediaScale"), dict) else {}
                    try:
                        f = float(ms.get("fraction"))
                        if 0 < f < 1:
                            hint["mediaFraction"] = f
                    except (TypeError, ValueError):
                        pass
                    break
            # measured CONTROL PLACEMENT (fix3, same treatment-fact discipline as
            # the edge-cut rail's `controls`): a source whose prev/next chrome sits
            # ON the dot rail below the slides (not floated mid-slide) declares
            # `controls: {placement: rail, size: <CSS length>}` — the device then
            # renders the bottom nav row at the captured control box. Fact-less
            # carousels keep the structural mid-edge paddles byte-identically.
            if isinstance(t.get("controls"), dict):
                hint["controls"] = dict(t["controls"])
            layout.setdefault("_carousel", hint)
        elif kind == "tabs":
            # TAB DEVICE (fix1 2026-07 item-9): a split section whose sanctioned
            # treatment declares a tab switcher composes the WAI-ARIA APG tab device
            # (tablist/tab/tabpanel; first tab active = the JS-off truth). Consumed by
            # compose_info_band from the section's authored panels. The media slot's
            # measured container fraction rides along (panel photo column share).
            hint = {"target": t.get("target"), "note": t.get("note")}
            # measured active-tab rule color (the committed-accent law collapses
            # --c-accent to ink on non-accent bands, so the captured underline
            # rides the treatment fact — never the page accent var).
            if t.get("activeUnderline"):
                hint["activeUnderline"] = str(t["activeUnderline"])
            for s in pattern.slots:
                if isinstance(s, dict) and str(s.get("name") or "") == "media":
                    ms = s.get("mediaScale") if isinstance(s.get("mediaScale"), dict) else {}
                    try:
                        f = float(ms.get("fraction"))
                        if 0 < f < 1:
                            hint["mediaFraction"] = f
                    except (TypeError, ValueError):
                        pass
                    break
            layout.setdefault("_tabs", hint)
        elif kind == "dotted-rule-rail":
            # SECTION HEADROW RAIL (fix1 2026-07 item-8): a leading chip/pill joined
            # by a horizontal rule to a trailing action at the far edge — the header
            # rail device. The stamp carries the target slot's OWN assets (a declared
            # icon chip; evidence-checked downstream) + the treatment prose (rule
            # style vocabulary). Consumed by the cards + generic-flow composers.
            # RECIPE FACTS (fix2 2026-07): when the pattern binds a brand recipe
            # (`recipeRef: {recipe, variant}` → layout-library.yaml `recipes:`,
            # brand-schema §4.4e) the resolved variant's measured facts ride the
            # stamp — kicker shape/size/radius/icon, rule style, trailing-action
            # presence, shared rail geometry. Recipe-less patterns keep the
            # prose-vocabulary stamp byte-identically.
            target = str(t.get("target") or "eyebrow")
            slot = next((s for s in pattern.slots if isinstance(s, dict)
                         and str(s.get("name") or "") == target), {})
            rail_stamp = {
                "note": t.get("note"),
                "assets": [str(a) for a in (slot.get("assets") or []) if a],
                "role": str(slot.get("role") or "")}
            resolved = ll.resolve_recipe_ref(pattern, brand_yaml) if brand_yaml else None
            if resolved is not None:
                recipe, variant = resolved
                rail_stamp["recipe"] = recipe.id
                rail_stamp["geometry"] = dict(recipe.geometry or {})
                rail_stamp["variant"] = {k: v for k, v in variant.items() if k != "id"}
                rail_stamp["variantId"] = str(variant.get("id") or "")
            layout.setdefault("_headRail", rail_stamp)
        elif kind == "panel-on-media":
            # INSET CONVERSION PANEL (fid2 2026-07): a conversion/banner pattern whose
            # sanctioned treatment declares the rounded panel-on-media band renders
            # its stack on a rounded inset panel (art from the brand's own panel-art
            # inventory; flat brand-surface fill is the degrade). Consumed only by
            # compose_conversion_stack — hero art-panels ride the adapter's _artPanel.
            layout.setdefault("_insetPanel", {"note": t.get("note")})
        elif kind == "art-surface" and \
                str(t.get("target") or "").lower() == "background":
            # FULL-BLEED ART BAND (fid5 2026-07): a section whose sanctioned treatment
            # declares its BACKGROUND is an art surface (e.g. a closing CTA on the
            # brand's noise-gradient band) renders the section box painted with the
            # brand's OWN art — filenames the treatment itself names (asset/note) are
            # preferred, evidence-checked against the inventory; flat brand-surface
            # fill is the degrade. Consumed by compose_conversion_stack.
            layout.setdefault("_artSurface", {"note": t.get("note"),
                                              "asset": t.get("asset")})
    # MARK-ROW SCALE facts (fid6 2026-07; fid7: per-GROUP map + mark-slot probe +
    # measured row gap): a mark-row slot whose pattern declares a measured
    # container-relative row scale (`mediaScale: {of: container, fraction: F, gap: L}`)
    # stamps `{fraction, gap?, aspects}` under its slot name so the generic-flow strip
    # renders EACH such row at its measured span (aspect-weighted marks, equal heights,
    # measured inter-mark gap). Mark rows are recognized by slot vocabulary
    # (logo/mark/badge/rating/award) OR by the slot's own assets all reading as marks
    # (the AS-33 filename discipline) — the badge/rating rows of an awards strip are
    # mark rows without "logo" anywhere in their name, which the fid6 probe missed and
    # left them collapsed at the structural height cap. No fraction fact / unreadable
    # assets ⇒ no stamp for that row (structural strip is the degrade).
    _scales: dict = {}
    for s in pattern.slots:
        if not isinstance(s, dict):
            continue
        ms = s.get("mediaScale") if isinstance(s.get("mediaScale"), dict) else {}
        if str(ms.get("of") or "").lower() != "container":
            continue
        probe = f"{s.get('name') or ''} {s.get('role') or ''}".lower()
        assets = [str(a) for a in (s.get("assets") or []) if a]
        marky = any(k in probe for k in ("logo", "mark", "badge", "rating", "award")) \
            or (bool(assets) and all(_is_mark_asset(a) for a in assets))
        if not marky:
            continue
        try:
            fraction = float(ms.get("fraction"))
        except (TypeError, ValueError):
            continue
        if not 0 < fraction <= 1:
            continue
        aspects = _asset_aspects(Path(brand_yaml).parent if brand_yaml else None, assets)
        entry: dict = {"fraction": fraction, "aspects": aspects}
        gap = str(ms.get("gap") or "").strip()
        if re.fullmatch(r"[\d.]+(?:rem|em|px)", gap):
            entry["gap"] = gap
        # MEASURED ITEM BOX (fix2 2026-07, brand-schema mediaScale.item): the strip's
        # uniform mark frame (width × height) measured on the capture — when present
        # the renderer draws fixed contain-fit boxes instead of distributing widths.
        item = ms.get("item") if isinstance(ms.get("item"), dict) else {}
        item_box = {k: str(item.get(k) or "").strip() for k in ("width", "height")}
        item_box = {k: v for k, v in item_box.items()
                    if re.fullmatch(r"[\d.]+(?:rem|em|px)", v)}
        if item_box:
            entry["item"] = item_box
        _scales[str(s.get("name") or "logos")] = entry
    if _scales:
        layout.setdefault("_logoScale", _scales)
    # MEASURED STACK MEASURE (fid7 2026-07): a centered-stack pattern whose contentShape
    # records the measured content-column cap (`stackMeasure: {value: <CSS length>}` —
    # JS-off computed geometry off the capture) stamps it so the conversion composer
    # sizes its column at the brand's real measure instead of the 46rem structural
    # default (whose 40ch prose measure collapsed a closing band to ~55% of the
    # source's content span). Malformed/missing values ⇒ no stamp (classic column).
    sm = (pattern.content_shape or {}).get("stackMeasure")
    if isinstance(sm, dict):
        v = str(sm.get("value") or "").strip()
        if re.fullmatch(r"[\d.]+(?:rem|em|px|ch)", v):
            layout.setdefault("_stackMeasure", v)
    # MEASURED BAND PADDING (fid7 2026-07): a pattern whose contentShape records the
    # band's own measured vertical padding (`bandPadding: {top, bottom}` — bookend
    # bands often breathe more than the brand's site-average section-padding token)
    # stamps it so the composer overrides the section rhythm vars for THIS band only.
    # Malformed lengths are dropped; nothing valid ⇒ no stamp (site rhythm holds).
    # GENRE-SKELETON sections excepted (spec/archetype-library.md, same discipline as
    # the alignment-layer skip): band GEOMETRY belongs to the archetype + the brand's
    # own spacing ladder (knobs.bandHeight re-registers on a measured rung); the donor
    # pattern's band padding is the SOURCE band's structural register, which must not
    # ride onto a different skeleton. Treatments/rhythm facts keep donating.
    bp = None if layout.get("archetypeRef") \
        else (pattern.content_shape or {}).get("bandPadding")
    if isinstance(bp, dict):
        pads = {k: str(bp.get(k) or "").strip() for k in ("top", "bottom")}
        pads = {k: v for k, v in pads.items()
                if re.fullmatch(r"[\d.]+(?:rem|em|px)", v)}
        if pads:
            layout.setdefault("_bandPadding", pads)
    # MEASURED BAND RHYTHM (fix1 2026-07 item-4): a pattern whose contentShape records
    # the band's OWN deterministic box-to-box seams (`bandRhythm: {eyebrowToHeading,
    # headingToBody, bodyToCta}`) stamps them so the band composer overrides the
    # site-wide relational-ladder rungs for THIS band only (bookend bands often run
    # tighter/looser than the working sections). Malformed lengths drop; nothing
    # valid ⇒ no stamp (the site ladder holds, byte-identical).
    br = (pattern.content_shape or {}).get("bandRhythm")
    if isinstance(br, dict):
        rungs = {k: str(br.get(k) or "").strip()
                 for k in ("eyebrowToHeading", "headingToBody", "bodyToCta")}
        rungs = {k: v for k, v in rungs.items()
                 if re.fullmatch(r"[\d.]+(?:rem|em|px)", v)}
        if rungs:
            layout.setdefault("_bandRhythm", rungs)
    # MEASURED ACTION-GROUP override (fix2 2026-07): a pattern whose contentShape
    # records its OWN multi-action row layout (`actionGroup: {gap, align,
    # marginAbove}` — e.g. a closing band whose CTA pair runs a wider gap than the
    # site default) stamps the partial override; the composer merges it over the
    # brand-level `layoutGrammar.actionGroup` facts. Malformed lengths drop;
    # nothing valid ⇒ no stamp (the brand default governs).
    ag = (pattern.content_shape or {}).get("actionGroup")
    if isinstance(ag, dict):
        over: dict = {}
        for k in ("gap", "marginAbove"):
            v = str(ag.get(k) or "").strip()
            if re.fullmatch(r"[\d.]+(?:rem|em|px)", v) or (k == "marginAbove" and v == "ladder"):
                over[k] = v
        if str(ag.get("align") or "").strip().lower() in ("start", "center", "end"):
            over["align"] = str(ag["align"]).strip().lower()
        # measured CROSS-AXIS placement (fix3): only a declared fact may move the
        # row off the structural align-items default — never hardcoded per section.
        if str(ag.get("crossAlign") or "").strip().lower() in ("start", "center",
                                                               "end", "stretch"):
            over["crossAlign"] = str(ag["crossAlign"]).strip().lower()
        if over:
            layout.setdefault("_actionGroup", over)
    # SIDE-RAIL CARD COUNTERWEIGHT (fix1 2026-07 item-7): a SPLIT-archetype pattern
    # whose alignment declares the CARD GRID as the copy rail's counterweight
    # (`archetypeRef: split` + `alignment: {value: left, counterweight: cards}`)
    # presents intro + actions as a left rail BESIDE the module grid (the split
    # morphology the source shows), instead of stacking intro above the grid.
    # The archetype requirement is load-bearing: a GRID pattern may also declare
    # counterweight:cards ("full-width grid balances the left header") yet keep
    # its header ABOVE the modules — only split anatomy owes the rail.
    # Fact-only: no split declaration ⇒ no stamp (grids render as today).
    _align = (pattern.content_shape or {}).get("alignment")
    if isinstance(_align, dict) \
            and str(getattr(pattern, "archetype_ref", "") or "").strip().lower() == "split" \
            and str(_align.get("counterweight") or "").strip().lower() == "cards" \
            and str(_align.get("value") or "").strip().lower() == "left":
        layout.setdefault("_sideRail", True)
    # SPLIT INTRO COLUMNS (fix1 2026-07 item-8): a pattern whose heading AND body
    # slots both declare `width: half` presents them side by side (heading LEFT /
    # supporting paragraph RIGHT) — the measured two-column intro morphology.
    # Geometry facts only; patterns with hug/full copy slots render as today.
    _slot_w = {str(s.get("name") or ""): str(s.get("width") or "")
               for s in pattern.slots if isinstance(s, dict)}
    if _slot_w.get("heading") == "half" and _slot_w.get("body") == "half":
        layout.setdefault("_introSplit", True)
    # MEASURED DEVICE GEOMETRY (fid9 2026-07): a pattern whose contentShape records
    # the band's JS-off computed geometry (`deviceGeometry`) stamps the validated
    # facts so the device composers draw the source's real proportions — column
    # split/gaps, header placement, media region aspect/alignment, list rhythm —
    # instead of the structural defaults (which under-drew a source band by ~200px).
    # Every field is optional and validated; nothing valid ⇒ no stamp (the
    # structural presentation is the degrade, byte-identical markup).
    geo = (pattern.content_shape or {}).get("deviceGeometry")
    if isinstance(geo, dict):
        g: dict = {}
        if str(geo.get("headerPlacement") or "").strip() == "list-column":
            g["headerInColumn"] = True
        if str(geo.get("columns") or "").strip() == "equal":
            g["equalColumns"] = True
        for k in ("columnGap", "rowGap", "contentSpan"):
            v = str(geo.get(k) or "").strip()
            if re.fullmatch(r"[\d.]+(?:rem|em|px)", v):
                g[k] = v
        med = geo.get("media") if isinstance(geo.get("media"), dict) else {}
        aspect = str(med.get("aspect") or "").strip()
        if re.fullmatch(r"\d+(?:\.\d+)?\s*/\s*\d+(?:\.\d+)?", aspect):
            g["mediaAspect"] = aspect
        if str(med.get("align") or "").strip() == "top":
            g["mediaTop"] = True
        # measured media FIT (fid10 2026-07): a source frame that letterboxes its
        # asset (`fit: contain` — e.g. a square media well holding a landscape
        # product-UI shot) records the fact; the split/accordion media column then
        # contains instead of cover-cropping to the asset's own aspect.
        if str(med.get("fit") or "").strip() == "contain":
            g["mediaContain"] = True
        lst = geo.get("list") if isinstance(geo.get("list"), dict) else {}
        for src_k, dst_k in (("triggerMinHeight", "triggerMinH"), ("itemGap", "itemGap")):
            v = str(lst.get(src_k) or "").strip()
            if re.fullmatch(r"[\d.]+(?:rem|em|px)", v):
                g[dst_k] = v
        # MEASURED CARD-HEADING REGISTER (fix1 2026-07 item-8): a pattern whose cards
        # ride a DIFFERENT measured type tier than the brand's global card device
        # (blocks.card slots.heading.register) records it here — e.g. an oversized
        # feature-card family beside a compact product-card family. The register
        # names a brand type ROLE tier; the tag stays h3 (document outline).
        reg = str(geo.get("cardRegister") or "").strip().lower()
        if reg in ("h2", "h3", "h4", "h5", "h6"):
            g["cardRegister"] = reg
        # MEASURED SECTION-HEADING REGISTER (fix1 2026-07): the tier THIS section's
        # heading measured on — when it differs from the brand's site-wide section
        # register (a compact statement strip, an up-tier showcase headline).
        h_reg = str(geo.get("headingRegister") or "").strip().lower()
        if h_reg in ("display", "h1", "h2", "h3", "h4", "h5", "h6"):
            g["headingRegister"] = h_reg
        # MEASURED RAIL CARD BOX (fix1 2026-07 item-8): an edge-cut track whose cards
        # measured their own width/gap (the clipped-card rhythm at the capture
        # viewport) rides them; length-validated, structural clamp is the degrade.
        for src_k, dst_k in (("cardWidth", "cardWidth"), ("cardGap", "cardGap")):
            v = str(geo.get(src_k) or "").strip()
            if re.fullmatch(r"[\d.]+(?:rem|em|px)", v):
                g[dst_k] = v
        if g:
            layout.setdefault("_accGeometry", g)


def _asset_aspects(brand_dir, names: list[str]) -> dict:
    """{basename: width/height} for each readable image among ``names`` under the
    brand's own asset conventions (brand assets/ tree, run-root assets/). Best-effort
    evidence measurement: unreadable/missing files are simply absent from the map
    (consumers require full coverage before scaling a row). Never raises."""
    out: dict[str, float] = {}
    if brand_dir is None:
        return out
    try:
        from PIL import Image
    except ImportError:
        return out
    roots = [Path(brand_dir) / "assets", Path(brand_dir).parent / "assets"]
    for raw in names:
        name = Path(raw).name
        if name in out:
            continue
        for root in roots:
            hits = sorted(root.rglob(name)) if root.is_dir() else []
            if not hits:
                continue
            if name.lower().endswith(".svg"):
                # vector marks (hubspot-v2 2026-07): PIL cannot open SVGs — the
                # intrinsic ratio comes from the file's own viewBox/width/height.
                try:
                    txt = hits[0].read_text(errors="ignore")
                    m = re.search(r'viewBox\s*=\s*"[\d.eE+-]+[ ,]+[\d.eE+-]+[ ,]+'
                                  r'([\d.eE+-]+)[ ,]+([\d.eE+-]+)"', txt)
                    if not m:
                        m = re.search(r'width\s*=\s*"([\d.]+)(?:px)?"\s+'
                                      r'height\s*=\s*"([\d.]+)(?:px)?"', txt)
                    if m and float(m.group(2)) > 0:
                        out[name] = round(float(m.group(1)) / float(m.group(2)), 4)
                except Exception:
                    pass
                break
            try:
                with Image.open(hits[0]) as im:
                    w, h = im.size
                if w > 0 and h > 0:
                    out[name] = round(w / h, 4)
            except Exception:
                pass
            break
    return out


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


def pattern_equalize_css(pattern, scope: str = "") -> str:
    """GRID EQUALIZATION consumption (fid14 2026-07, AS-50): render a card grid per the
    pattern's measured ``contentShape.gridEqualize`` fact (brand-schema §4.4d).

    ``stretch``: cards sharing a grid row equalize — explicit ``align-items: stretch``
    (the editorial stagger scaffold's ``align-items: start`` hug would otherwise leak
    into declared N-up grids), and when the source pins actions (``actionPinned``),
    trailing action rows take ``margin-top: auto`` so the slack the source absorbs in
    its flexing body region lands in the seam ABOVE the pinned row — the same visual
    morphology (content top-anchored, actions bottom-anchored) without demanding a
    wrapper the scaffold anatomy doesn't have. ``hug``: cards stay content-sized
    (explicit ``align-items: start``, no pins).

    Degrade: no pattern / no fact -> "" (fact-less brands are byte-identical)."""
    fact = getattr(pattern, "grid_equalize", None) if pattern is not None else None
    if not fact:
        return ""
    pfx = f"{scope} " if scope else ""
    if fact["heights"] == "stretch":
        rules = [f"/* grid equalization (pattern fact, AS-50): heights=stretch"
                 f" slack={fact['slack']} actionPinned={str(fact['actionPinned']).lower()} */",
                 f"{pfx}.cs-modules {{ align-items: stretch; }}"]
        if fact["actionPinned"]:
            rules.append(
                f"{pfx}.cs-module > .c-arrow-link:last-child, "
                f"{pfx}.cs-module > .c-button:last-child, "
                f"{pfx}.cs-module > .c-person:last-child {{ margin-top: auto; }}")
            # MINIMUM SEAM (spacing remediation B2 2026-07): margin-top:auto replaces
            # the ladder's body->cta pair margin, so in the row's TALLEST card (zero
            # slack) the pinned action sat flush against the body — the old fix padded
            # the link's own box, which moves the glyph but leaves the measured
            # box-to-box gap at 0. The seam now lives on the PRECEDING content's
            # margin-bottom: `auto` absorbs only slack beyond the ladder rung, and the
            # tallest card measures exactly the rung. Anatomy stacks only (gap:0 per
            # AS-48); plates keep their structural flex gap as the minimum.
            rules.append(
                f"{pfx}.cs-module--anatomy > :has(+ .c-arrow-link:last-child), "
                f"{pfx}.cs-module--anatomy > :has(+ .c-button:last-child) {{"
                f" margin-bottom: var(--space-body-to-cta, 0.9rem); }}")
            # PLAIN PLATES ride the same minimum (spacing spec: card.body-to-actions
            # maps to ladder body-to-cta for every card) — their structural flex gap
            # participates in the seam, so the margin tops it up to the rung
            # (ladder-less brands resolve to gap - gap = 0: byte-identical degrade).
            rules.append(
                f"{pfx}.cs-module--plate:not(.cs-module--anatomy):not(.cs-module--quote)"
                f" > :has(+ .c-arrow-link:last-child), "
                f"{pfx}.cs-module--plate:not(.cs-module--anatomy):not(.cs-module--quote)"
                f" > :has(+ .c-button:last-child) {{"
                f" margin-bottom: calc(var(--space-body-to-cta,"
                f" var(--cs-module-gap, 0.9rem)) - var(--cs-module-gap, 0.9rem)); }}")
            # quote modules pin their attribution row; the minimum seam is the
            # quote-card's own measured quote→attribution rung (B8).
            rules.append(
                f"{pfx}.cs-module--quote > :has(+ .c-person:last-child) {{"
                f" margin-bottom: var(--space-quote-to-attribution, 0.9rem); }}")
        return "\n".join(rules)
    return (f"/* grid equalization (pattern fact, AS-50): heights=hug — content-sized */\n"
            f"{pfx}.cs-modules {{ align-items: start; }}")


def pattern_card_rhythm_css(pattern, scope: str = "") -> str:
    """MEASURED IN-CARD ACTION SEAM (``contentShape.deviceGeometry.cardActionGap``,
    spacing spec ``card.body-to-actions``): a pattern that measured its card's own
    body→action register — a seam that does NOT ride the section-scale
    body-to-cta rung — stamps that seam on its module cards. Flow modules get the
    margin as a top-up over their structural flex gap; anatomy stacks (gap:0) get
    it on the preceding content's margin-bottom, mirroring the equalize min-seam
    mechanic so a PINNED action keeps its ``margin-top: auto`` pin (only slack
    beyond the measured seam is absorbed). Emitted AFTER pattern_equalize_css at
    both call sites, so a pattern authoring both facts resolves to its own
    measured card seam. Degrade: no pattern / no fact -> ""."""
    geo = ((getattr(pattern, "content_shape", None) or {}).get("deviceGeometry")
           if pattern is not None else None) or {}
    v = str(geo.get("cardActionGap") or "").strip()
    if not re.fullmatch(r"[\d.]+(?:rem|em|px)", v):
        return ""
    fact = getattr(pattern, "grid_equalize", None) or {}
    pinned = bool(fact.get("actionPinned"))
    pfx = f"{scope} " if scope else ""
    rules = [
        f"/* measured in-card action seam (pattern deviceGeometry.cardActionGap) */",
        # flow modules: the margin tops up the structural flex gap → net seam = {v}
        f"{pfx}.cs-module:not(.cs-module--anatomy):not(.cs-module--quote)"
        f" > :has(+ .c-arrow-link:last-child), "
        f"{pfx}.cs-module:not(.cs-module--anatomy):not(.cs-module--quote)"
        f" > :has(+ .c-button:last-child) {{"
        f" margin-bottom: calc({v} - var(--cs-module-gap, 0.9rem)); }}",
        f"{pfx}.cs-module--plate:not(.cs-module--anatomy):not(.cs-module--quote)"
        f" > :has(+ .c-arrow-link:last-child), "
        f"{pfx}.cs-module--plate:not(.cs-module--anatomy):not(.cs-module--quote)"
        f" > :has(+ .c-button:last-child) {{"
        f" margin-bottom: calc({v} - var(--cs-module-gap, 0.9rem)); }}",
        # anatomy stacks (gap:0): the seam is the preceding content's margin-bottom
        # (overrides the equalize rung min-seam — emitted later, same selector)
        f"{pfx}.cs-module--anatomy > :has(+ .c-arrow-link:last-child), "
        f"{pfx}.cs-module--anatomy > :has(+ .c-button:last-child) {{"
        f" margin-bottom: {v}; }}",
    ]
    if not pinned:
        # unpinned anatomy: the base ladder rule puts body-to-cta on the link's own
        # margin — zero it so the measured seam above doesn't stack with the rung.
        rules.append(
            f"{pfx}.cs-module--anatomy > .c-arrow-link:last-child, "
            f"{pfx}.cs-module--anatomy > .c-button:last-child {{"
            f" margin-block-start: 0; }}")
    return "\n".join(rules)


def grid_equalize_grammar(brand_yaml) -> str | None:
    """The BRAND's grid-equalization grammar, derived from the project library's
    measured ``gridEqualize`` facts — the layer the pattern-less generated scaffolds
    (bento mosaic, pricing tiers) consume, exactly like headerContext grammar backs
    pattern-less alignment. Returns ``"stretch"`` / ``"hug"`` when every observed
    card-grid fact agrees, ``"stretch"`` on a mixed corpus (equalization is the safer
    majority morphology and the per-pattern fact still wins where one exists), or
    ``None`` when no pattern records a stance (fact-less brands: scaffolds keep their
    built-in behavior unchanged)."""
    if not brand_yaml:
        return None
    try:
        facts = [p.grid_equalize for p in ll.load_project_patterns(Path(brand_yaml))]
        stances = {f["heights"] for f in facts if f}
    except Exception:
        return None
    if not stances:
        return None
    return "hug" if stances == {"hug"} else "stretch"


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


def eyebrow_register_css(doc, layout, sel: str) -> str:
    """Per-section eyebrow register (brand-schema `layout.eyebrowRegister`, sysfix
    2026-07): a layout may declare WHICH of the brand's own eyebrow color families
    its microlabel reads — the value names a `tokens.colors` ROLE (an accent family,
    the muted ink family, …). Emits a section-scoped `--c-eyebrow-color` pointing at
    the layer-1 var; undeclared layouts keep the surface default (the alias stays
    unset and `.c-eyebrow` falls back to its register for the render path). Declaring
    a role the brand does not carry fails loud — that is an evidence bug, and the C11
    smoke reports it as a compose failure."""
    role = str((layout or {}).get("eyebrowRegister") or "").strip()
    if not role:
        return ""
    colors = (doc.get("tokens", {}) or {}).get("colors", {}) or {}
    if role not in colors:
        raise KeyError(f"layout '{(layout or {}).get('id')}' declares "
                       f"eyebrowRegister '{role}' but tokens.colors carries no "
                       "such role")
    return (f"\n/* eyebrow register: the section's declared theme-scope family */\n"
            f"{sel} {{ --c-eyebrow-color: {tokens_css.color_var(role)}; }}")


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
    # inter-block gap: the brand's measured content-block ROW rhythm when the ladder
    # authored one (fid11: tokens.spacing.block-to-block — the source's own
    # header→content / content→content / content→actions rung), else the style
    # scale (else neutral) — the historical uniform look stays the degrade.
    block_gap = _brand_spacing(doc, "block-to-block") or (s.block_gap if s else "2.5rem")
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
    # MEASURED nav bar height (fid2 2026-07): when the brand extracted its chrome bar
    # height, the page-nav vertical padding derives from it — (barH − tallest control)/2
    # against the measured CTA height when present, floored at 0.5rem — instead of the
    # structural 1.75rem default (which inflated an 81px measured bar to 104px).
    nav_pad = "1.75rem"
    nb = (doc.get("navbar") or {}) if isinstance(doc, dict) else {}
    nm = nb.get("measured") or {}
    bar_h = ((nm.get("bar") or {}).get("height"))
    if isinstance(bar_h, (int, float)) and bar_h > 0:
        cta_h = ((nm.get("cta") or {}).get("height"))
        content_h = cta_h if isinstance(cta_h, (int, float)) and cta_h > 0 else 30
        nav_pad = f"{max((bar_h - content_h) / 2.0, 8) / 16.0:.4g}rem"
    # TWO-TIER bar (fix1 2026-07 item-12a): when the brand opted into the utility
    # tier AND measured both tier heights, the tiers' min-heights carry the FULL
    # measured bar geometry — the derived block padding (sized for a single bar)
    # would double-count it, so it collapses to 0. Single-bar brands unchanged.
    if isinstance(nb.get("utilityTier"), dict) \
            and isinstance(nm.get("utilityBarHeight"), (int, float)) \
            and isinstance(nm.get("primaryBarHeight"), (int, float)):
        nav_pad = "0rem"
    return (f"{selector} {{ --c-section-pad-top: {r['pad_top']}; "
            f"--c-section-pad-bottom: {r['pad_bottom']}; --c-section-pad: {r['pad_bottom']}; "
            f"--c-block-gap: {r['block_gap']}; --c-module-gap: {r['module_gap']}; "
            f"--c-section-pad-x: 2.5rem; --c-nav-pad-block: {nav_pad}; }}")


def band_height_rung(doc, layout, surf_role, style_ctx) -> str:
    """The brand spacing-token NAME the section's ``_bandHeight`` knob re-registers
    to: the NEAREST ``section-*`` rung BELOW the surface's resolved default pad
    (``compact``) or ABOVE it (``tall``). '' when the knob is absent/unknown, the
    default pad is unparsable, or no rung exists in the wanted direction (degrade =
    standard rhythm). Shared by ``band_height_css`` (the CSS emission) and the
    wrapper's ``data-band-rung`` declaration stamp (the spacing auditor's read)."""
    band = str((layout or {}).get("_bandHeight") or "").strip().lower()
    direction = {"compact": -1, "tall": 1}.get(band)
    if not direction:
        return ""

    def _px(val) -> float | None:
        m = re.fullmatch(r"([\d.]+)\s*(rem|px)", str(val or "").strip())
        if not m:
            return None
        n = float(m.group(1))
        return n * 16.0 if m.group(2) == "rem" else n

    base = _px(rhythm_for(doc, style_ctx, surf_role)["pad_top"])
    if base is None:
        return ""
    candidates = []
    for name, tok in (((doc.get("tokens") or {}).get("spacing") or {}) or {}).items():
        if not str(name).startswith("section"):
            continue
        px = _px((tok or {}).get("value") if isinstance(tok, dict) else None)
        if px is not None and px > 0:
            candidates.append((px, str(name)))
    picks = sorted((c for c in candidates if (c[0] - base) * direction > 0),
                   key=lambda c: abs(c[0] - base))
    return picks[0][1] if picks else ""


def band_height_derived_px(doc, layout, surf_role, style_ctx) -> float | None:
    """Derived-scale degrade for the bandHeight knob (pass1 2026-07,
    style-scale.v1 consumption): when the knob wants a direction the brand's OWN
    measured ladder has no rung for, a composed lane may ride the nearest DERIVED
    section-rhythm step instead of silently keeping standard rhythm. Fires only
    when ALL hold: a valid knob, NO measured rung in the direction (a measured
    fact always wins), and the page doc carries a loaded ``_styleScale`` with a
    non-poor space fit (composition_to_doc loads it; the replica assembler never
    does — byte-identical by construction). None ⇒ the historical '' degrade."""
    band = str((layout or {}).get("_bandHeight") or "").strip().lower()
    direction = {"compact": -1, "tall": 1}.get(band)
    if not direction:
        return None
    if band_height_rung(doc, layout, surf_role, style_ctx):
        return None  # measured rung binds — the derived step is never consulted
    import style_scale as _ss
    steps = _ss.section_rhythm_px(doc.get("_styleScale"))
    if not steps:
        return None
    m = re.fullmatch(r"([\d.]+)\s*(rem|px)",
                     str(rhythm_for(doc, style_ctx, surf_role)["pad_top"] or "").strip())
    if not m:
        return None
    base = float(m.group(1)) * (16.0 if m.group(2) == "rem" else 1.0)
    return _ss.nearest_step_px(steps, base, direction=direction)


def band_height_css(doc, layout, sel: str, surf_role, style_ctx) -> str:
    """Per-section bandHeight knob (spec/archetype-library.md; composition
    ``knobs.bandHeight`` → ``layout['_bandHeight']``): re-registers the section's
    vertical padding to the NEAREST rung of the brand's OWN section-rhythm token
    family (``section-padding-*`` / ``section-y-*``) BELOW the surface's resolved
    default pad (``compact``) or ABOVE it (``tall``). The knob never invents a
    length — it only re-points at a different rung of the measured ladder (emitted
    as a ``var(--space-…)`` layer-1 reference, so token provenance and the spacing
    audit both see the brand's own fact). Degrades: no rung in the wanted direction,
    an unparsable pad, or no ``_bandHeight`` hint -> '' (standard rhythm keeps).
    Emitted AFTER ``rhythm_vars_css`` for the same selector so source order wins."""
    band = str((layout or {}).get("_bandHeight") or "").strip().lower()
    rung = band_height_rung(doc, layout, surf_role, style_ctx)
    if not rung:
        # derived-scale degrade (pass1 2026-07): a composed lane with a loaded
        # style-scale prefers the nearest DERIVED section-rhythm step over the
        # silent standard-rhythm keep — quantized new geometry instead of an
        # unanswered knob. Measured rungs (above) always win; lanes without the
        # artifact keep the historical '' byte-identically.
        px = band_height_derived_px(doc, layout, surf_role, style_ctx)
        if px is None:
            return ""
        val = f"{px:g}px"
        return (f"\n/* bandHeight:{band} — no measured rung in this direction; "
                f"re-registered to the DERIVED section-rhythm step {val} "
                f"(style-scale.v1) */\n"
                f"{sel} {{ --c-section-pad-top: {val}; --c-section-pad-bottom: {val}; "
                f"--c-section-pad: {val}; }}")
    var = f"var(--space-{tokens_css._slug(rung)})"
    return (f"\n/* bandHeight:{band} — archetype band character re-registered to the "
            f"brand's own '{rung}' rung */\n"
            f"{sel} {{ --c-section-pad-top: {var}; --c-section-pad-bottom: {var}; "
            f"--c-section-pad: {var}; }}")


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
    out_assets.mkdir(parents=True, exist_ok=True)
    dest = out_assets / NAV_LOGO_LOCAL
    # DATA-URI logo (fix 2026-07): "Save Page As" captures often INLINE the logo as
    # `data:image/svg+xml;base64,…` (the real captured mark, not a placeholder).
    # Decode it to the local asset so the composed nav renders the true logo instead
    # of degrading to the text wordmark. Generic — any brand whose logo is inlined.
    if src.startswith("data:"):
        try:
            import base64 as _b64
            header, _, payload = src.partition(",")
            data = _b64.b64decode(payload) if ";base64" in header else \
                urllib.parse.unquote(payload).encode("utf-8")
            dest.write_bytes(data)
            return NAV_LOGO_LOCAL
        except Exception:
            return None
    filename = src.split("/")[-1].split("?")[0] or NAV_LOGO_LOCAL
    run_dir = brand_dir.parent  # runs/<brand>/brand -> runs/<brand>
    candidates = [
        run_dir / "assets" / "source_complete" / filename,
        run_dir / "assets" / filename,
    ]
    candidates += sorted(run_dir.glob(f"**/{filename}"))
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
        "ctaAriaLabel": (
            cta.get("ariaLabel") or cta.get("accessibleName")
            if cta else None
        ),
    }
    # ACTION GROUP (fix1 2026-07 item-12b): when the evidence declares MULTIPLE bar
    # actions (navbar.ctas[] length ≥ 2), every action rides along with its own
    # measured register facts — render_navbar draws the N-action run. Single-cta
    # brands never build this key (their bar markup stays byte-identical).
    all_ctas = [c for c in (nav.get("ctas") or [])
                if isinstance(c, dict) and c.get("label")]
    if len(all_ctas) >= 2:
        projected_lane = any(
            isinstance(layout, dict) and layout.get("requiresHydration") is True
            for layout in (doc.get("layouts") or []))
        families = doc.get("buttons") if isinstance(doc.get("buttons"), dict) else {}
        props["actions"] = [{
            "label": c["label"], "href": c.get("href", "#"),
            "ariaLabel": c.get("ariaLabel") or c.get("accessibleName"),
            "style": {
                "bg": c.get("bg") or (
                    (families.get(c.get("style")) or {}).get("bg") if projected_lane else None),
                "color": c.get("color") or (
                    (families.get(c.get("style")) or {}).get("fg") if projected_lane else None),
                "border": c.get("border") or (
                    (families.get(c.get("style")) or {}).get("border") if projected_lane else None),
                "radius": c.get("borderRadius") or (
                    (families.get(c.get("style")) or {}).get("radius") if projected_lane else None),
                "height": c.get("height") or (
                    (families.get(c.get("style")) or {}).get("height") if projected_lane else None),
                "padX": c.get("padX"),
                "fontSize": c.get("fontSize"),
            }} for c in all_ctas]
    # MEASURED chrome-CTA facts (fid2 2026-07): the extracted nav CTA's own computed
    # styles ride along so render_navbar draws the measured pill (e.g. a neutral
    # filled CTA distinct from the page's accent primary). Declared navbar.ctas[0]
    # facts win; navbar.measured.cta fills the geometry. Absent facts ⇒ no key, and
    # render_navbar keeps the law-first button dispatch (the degrade).
    c0 = next((c for c in (nav.get("ctas") or []) if isinstance(c, dict)), {})
    m_cta = (nav.get("measured") or {}).get("cta") or {}
    bg = c0.get("bg") or m_cta.get("bg")
    if bg:
        props["ctaStyle"] = {
            "bg": bg,
            "color": c0.get("color") or m_cta.get("color"),
            "radius": c0.get("borderRadius", m_cta.get("radius")),
            "height": m_cta.get("height"),
            "padX": m_cta.get("paddingLeft"),
            "fontSize": m_cta.get("fontSize"),
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
        # slot evidence prose rides along as a family hint (declared outline/quiet
        # treatments select the brand's matching measured family; else primary).
        return {"label": usage.get("Label")
                or (usage["label"] if "label" in usage else sc["cta"]),
                "accent": ctx.is_dark,
                "family": usage.get("family"),
                "familyHint": f"{role or ''} {usage.get('styleHint') or ''}".strip()}
    # generic image / media fallback
    if "photo" in r or "image" in r or "media" in r:
        # WRONG-ASSET GUARD (fid2 2026-07): a slot whose declared role is PRODUCT/UI
        # art (collage, ui, screenshot, diagram) must never fall back to the brand's
        # hero/background art — an unbound product-art slot degrades to NO src (the
        # composer's honest media well), not to a noise-gradient backdrop pretending
        # to be a product shot.
        if re.search(r"product|collage|\bui\b|screenshot|diagram|snippet", r):
            return {"src": None, "alt": ""}
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
                     "placeholder", "submit", "src", "alt",
                     # stat + table contract vocabulary (W4, stress-playbook 2026-07)
                     "value", "columns", "rows")


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
        # The slot's evidence prose (role + styleHint) rides along as a family hint
        # so a declared outline/quiet treatment selects the brand's matching family.
        return {"label": u.get("label") or u.get("text") or u.get("cta") or "Get started",
                "href": u.get("href", "#"), "accent": u.get("accent", False),
                "family": u.get("family"),
                "familyHint": f"{role or ''} {u.get('styleHint') or ''}".strip()}
    if c == "image":
        return {"src": u.get("src"), "alt": u.get("alt", ""),
                "variant": u.get("variant", ""), "absolute": bool(u.get("absolute")),
                "aspect": u.get("aspect"),
                # masked-media clip (media semantics 2026-07) — declared-only
                "mask": u.get("mask"),
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
    if c in ("stat", "stat-block", "metric"):
        # stat contract (W4): value + label at their REAL registers via render_stat —
        # heading/text keys accepted as authoring aliases (value/label win).
        return {"value": u.get("value") or u.get("heading") or u.get("text") or "",
                "label": u.get("label") or u.get("body") or u.get("caption") or "",
                "prefix": u.get("prefix"), "suffix": u.get("suffix")}
    if c == "table":
        # table contract (W4): caption/columns/rows straight through to render_table.
        return {"caption": u.get("caption") or u.get("heading") or "",
                "columns": u.get("columns"), "rows": u.get("rows")}
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
    # PATTERN-MEASURED HEADING REGISTER (fix1 2026-07, deviceGeometry.headingRegister —
    # stamped before render by stamp_pattern_devices): a section whose pattern measured
    # its heading on a DIFFERENT brand tier than the site-wide section register (e.g. a
    # proof strip's statement heading at the compact sans tier, or a showcase band a
    # tier up) rides its measured tier. Overrides the adapter's ladder default only for
    # heading/header contracts; stamp-less sections render byte-identically.
    _geo = layout.get("_accGeometry") if isinstance(layout.get("_accGeometry"), dict) else {}
    _head_reg = str(_geo.get("headingRegister") or "").strip().lower()
    for m in _effective_mappings(layout):
        contract = m.get("contract")
        renderer = cr.resolve_renderer(contract)
        entry = catalog_entry(doc, contract)
        usage = m.get("usage")
        if _head_reg and str(contract or "").lower() in ("heading", "header") \
                and isinstance(usage, dict):
            usage = {**usage, "level": _head_reg}
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
            "group": m.get("group"),
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
    props = {"src": src, "variant": variant, "aspect": layer.get("aspect"),
             "alt": layer.get("alt") or f"{brand_name} photography"}
    # masked-media (media semantics 2026-07): the layer clips inside a brand
    # accent-shape/logo silhouette. Declared-only; layers without a mask are
    # byte-identical.
    if layer.get("mask"):
        props["mask"] = layer["mask"]
    return cr.render_image(doc, ctx, props)


def _stack_hero_layered(doc, ctx, layers: list[dict], *, eyebrow_html, title_html,
                        cta_html, subhead: str, scrim_class: str | None = None,
                        scrim_color: str | None = None,
                        band_padding: dict | None = None,
                        band_rhythm: dict | None = None,
                        stack_measure: str | None = None) -> str:
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
        # the DECLARED text-on-media wash class (adapter `_bgScrimClass`): the brand's
        # own treatment fact decides the scrim — `none` means the contrast tint is
        # baked into the photograph (no wash div at all); light/medium/heavy ride the
        # shared SCRIM_ALPHA ladder as a paper-toned inline wash. Undeclared keeps the
        # flat default `.cs-bg-scrim` (existing brands byte-identical).
        # A MEASURED scrim paint (adapter `_bgScrimColor`, fix1 2026-07) outranks the
        # class ladder: the brand's own captured overlay color paints verbatim (the
        # source hero's flat contrast wash), never a paper-mix approximation.
        if scrim_color:
            scrim_div = (f'<div class="cs-bg-scrim" style="background: '
                         f'{cr.esc(scrim_color)}"></div>')
        elif scrim_class == "none":
            scrim_div = ""
        elif scrim_class in SCRIM_ALPHA:
            pct = round(SCRIM_ALPHA[scrim_class] * 100)
            scrim_div = ('<div class="cs-bg-scrim" style="background: color-mix('
                         f'in srgb, var(--c-paper) {pct}%, transparent)"></div>')
        else:
            scrim_div = '<div class="cs-bg-scrim"></div>'
        bg_html = (f'\n  <div class="cs-bg-layer" aria-hidden="true">{img}'
                   f'{scrim_div}</div>')

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

    # FLAT layered hero (fix1 2026-07, hero title-seam punch item): with NO collage
    # between title and foot there is nothing for the display title to overlap — the
    # collage overlap margin (--c-title-overlap, a NEGATIVE pull) would drag the foot
    # up through the authored heading→body rung. The modifier zeroes it so the seam
    # rides the section's own block rhythm; collage heroes keep the overlap
    # byte-identically.
    flat_cls = " cs-hero-layered--flat" if not collage else ""
    # MEASURED BAND PADDING (fix1 2026-07, stamped from contentShape.bandPadding —
    # same consumption discipline as the conversion/split composers): the hero band's
    # own measured vertical rhythm overrides the site-average section padding vars.
    # No stamp ⇒ no style attribute (site rhythm byte-identical).
    bp = band_padding if isinstance(band_padding, dict) else {}
    pad_decls = "".join(
        f" --c-section-pad-{k}: {cr.esc(bp[k])};" for k in ("top", "bottom") if bp.get(k))
    # MEASURED BAND RHYTHM (fix1 2026-07 item-4, stamped from contentShape.bandRhythm):
    # this band's OWN box-to-box seams override the site ladder as scoped vars —
    # eyebrow→heading rides the eyebrow gap, heading→body the title→foot seam, and
    # body→cta the foot's own internal gap (--cs-hero-foot-gap, a fallback-only var:
    # rhythm-less brands resolve it straight back to --c-block-gap, byte-identical).
    brh = band_rhythm if isinstance(band_rhythm, dict) else {}
    for key, var in (("eyebrowToHeading", "--c-eyebrow-gap"),
                     ("headingToBody", "--c-block-gap"),
                     ("bodyToCta", "--cs-hero-foot-gap")):
        if brh.get(key):
            pad_decls += f" {var}: {cr.esc(brh[key])};"
    # MEASURED HERO STACK MEASURE (fix3, stamped from contentShape.stackMeasure —
    # the same fact the conversion composers consume): the centered hero's TEXT
    # boxes cap at the source's own measured column, so the display heading wraps
    # where the source wraps at ANY viewport past the measure (the containment law
    # owns the section column; this is the narrower MEASURE vocabulary). No stamp
    # ⇒ no var ⇒ the scaffold cap resolves to `none`, byte-identical rendering.
    if isinstance(stack_measure, str) and stack_measure.strip():
        pad_decls += f" --cs-stack-measure: {cr.esc(stack_measure.strip())};"
    sec_style = f' style="{pad_decls.strip()}"' if pad_decls else ""
    return f"""<section class="cs-section cs-hero-layered{flat_cls}"{sec_style}>{bg_html}{corner_html}
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
    never a literal, never another brand's file (AS-34).

    EVENT-POSTER extensions (event-scaffolds 2026-07), each SLOT-GATED so every
    existing panel hero renders byte-identically:
      - an authored EYEBROW slot (panel['eyebrow'] flag from the adapter) renders the
        section eyebrow register above the title — unauthored panels keep none;
      - an authored META line (panel['meta'] — e.g. the date/place caption of a
        poster hero) renders in the caption register between body and actions;
      - a declared `alignment.anchor: centered` centers the panel's content column
        (the poster stance); side-anchored panels keep the editorial left column."""
    art = panel.get("asset") or _hero_treatment_art(doc)
    bg_style = f' style="background-image: url(\'{cr.esc(art)}\')"' if art else ""
    body_html = body_slot["html"] if body_slot else (
        f'<p class="cs-sub">{cr.esc(copy["subhead"])}</p>' if copy["subhead"] else "")
    media = next((r for r in rendered
                  if r.get("contract") == "image" and (r.get("html") or "").strip()), None)
    media_html = f'\n    <div class="cs-hero-panel-media">{media["html"]}</div>' \
        if media else ""
    mod = " cs-hero-panel--solo" if not media else ""
    if (((layout or {}).get("alignment") or {}).get("anchor") or "").lower() == "centered":
        mod += " cs-hero-panel--center"
    eyebrow_html = ""
    if panel.get("eyebrow") and str(copy["eyebrow"]).strip():
        eyebrow_html = ('\n      <div class="cs-eyebrow-wrap">'
                        + cr.render_eyebrow(doc, ctx, {"text": copy["eyebrow"]})
                        + "</div>")
    meta_html = ""
    if str(panel.get("meta") or "").strip():
        meta_html = ('\n      <p class="c-caption cs-hero-panel-meta">'
                     + cr.esc(str(panel["meta"]).strip()) + "</p>")
    return f"""<section class="cs-section cs-hero-panel-sec">
  <div class="cs-hero-panel{mod}"{bg_style}>
    <div class="cs-hero-panel-content">{eyebrow_html}
      <div class="cs-title">{title_html}</div>
      {body_html}{meta_html}
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
    # ANATOMY-DEVICE fragments (fix6: foot form / rail — placed by their own blocks
    # below) are excluded from these picks so a form's paragraph-register note can
    # never double-render as the hero body.
    core = [r for r in rendered
            if not str(r.get("role") or "").startswith(("foot form", "rail "))]
    eyebrow_slot = _pick(core, "eyebrow") or _pick(core, "tagline")
    body_slot = _pick(core, "supporting") or _pick(core, "paragraph")
    cta_slot = _pick(core, "cta") or _pick(core, "button") or _pick(core, "action")
    # EMPTY copy value = the section authored NO such slot (slot-faithful archetype
    # sections suppress the SECTION_COPY ride-through by passing "") — render nothing.
    # Legacy paths always carry non-empty defaults, so this is byte-identical there.
    eyebrow_html = eyebrow_slot["html"] if eyebrow_slot else (
        cr.render_eyebrow(doc, ctx, {"text": copy["eyebrow"]}) if copy["eyebrow"] else "")
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
        cta_html = (f'<div class="cs-hero-actions"{ag_attrs(doc, layout)}>'
                    f'{"".join(action_frags)}</div>')
    elif cta_slot:
        cta_html = cta_slot["html"]
    elif copy["cta"]:
        cta_html = cr.render_arrow_link(doc, ctx, {"label": copy["cta"], "accent": False})
    else:
        cta_html = ""

    # SLOT-FAITHFUL ANATOMY DEVICES (fix6, archetype sections only — the adapter maps
    # them exclusively for genre-skeleton heroes, so legacy heroes render
    # byte-identically):
    #   "rail mark"/"rail caption" — an agenda/track/award row after the actions,
    #     drawn through the existing logo-strip device + one caption line;
    #   "foot form" — a search-first/capture anatomy's form block at the foot;
    #   "rail link" — the quiet link row (popular/secondary destinations).
    rail_html = ""
    rail_marks = [r["html"] for r in rendered
                  if str(r.get("role") or "").startswith("rail mark")
                  and (r.get("html") or "").strip()]
    if rail_marks:
        rail_cap = next((r["html"] for r in rendered
                         if str(r.get("role") or "").startswith("rail caption")
                         and (r.get("html") or "").strip()), "")
        items = "".join(f'<div class="cs-logo-strip-item">{f}</div>' for f in rail_marks)
        rail_html = (f'<div class="cs-hero-rail"><div class="cs-logo-strip">{items}</div>'
                     f'{rail_cap}</div>')
    form_html = next((r["html"] for r in rendered
                      if str(r.get("role") or "").startswith("foot form (")
                      and (r.get("html") or "").strip()), "")
    if form_html:
        # the note ATTACHES to its control (fix7 punch 6): caption register BELOW
        # the field, capped to the control's width by the .cs-hero-form scope —
        # never a free-floating line between the lede and the control (the stated
        # reason AS-14 reads is the section's own body copy above).
        form_note = next((r["html"] for r in rendered
                          if str(r.get("role") or "").startswith("foot form note")
                          and (r.get("html") or "").strip()), "")
        form_html = f'<div class="cs-hero-form">{form_html}{form_note}</div>'
    link_frags = [r["html"] for r in rendered
                  if str(r.get("role") or "").startswith("rail link")
                  and (r.get("html") or "").strip()]
    links_html = (f'<div class="cs-hero-links">{"".join(link_frags)}</div>'
                  if link_frags else "")

    panel = layout.get("_artPanel")
    if panel is not None and _art_panel_permitted(style_ctx):
        return _stack_hero_art_panel(doc, ctx, layout, rendered, panel,
                                     title_html=title_html, body_slot=body_slot,
                                     cta_html=cta_html, copy=copy)

    layers = layout.get("_mediaLayers")
    if layers:
        return _stack_hero_layered(doc, ctx, layers, eyebrow_html=eyebrow_html,
                                   title_html=title_html, cta_html=cta_html,
                                   subhead=copy["subhead"],
                                   scrim_class=layout.get("_bgScrimClass"),
                                   scrim_color=layout.get("_bgScrimColor"),
                                   band_padding=layout.get("_bandPadding"),
                                   band_rhythm=layout.get("_bandRhythm"),
                                   stack_measure=layout.get("_stackMeasure"))

    hero_media = _pick(rendered, "hero", "photo") or _pick(rendered, "hero")
    overlap_media = _pick(rendered, "overlap")
    hero_html = hero_media["html"] if hero_media else ""
    overlap_html = overlap_media["html"] if overlap_media else ""

    collage = f"""    <div class="cs-collage">
      {hero_html}
      {overlap_html}
    </div>
    <div class="cs-spacer"></div>"""

    # STACKED archetype hero (spec/archetype-library.md): a genre-skeleton section
    # whose composition declares NO overlap device renders the plain stack — the
    # scaffold's measured title-over-collage pull is the SOURCE hero's layered fact,
    # not a genre default. Zero bound media also drops the empty collage frame.
    # Fact-gated on the ref: every existing lane keeps the classic shape byte-identically.
    sec_cls = "cs-section"
    if layout.get("archetypeRef") and not ((layout.get("overlapRules") or {}).get("types")):
        sec_cls = "cs-section cs-hero--stacked"
        if not hero_html.strip() and not overlap_html.strip():
            collage = ""

    sub_html = body_slot["html"] if body_slot else (
        f'<p class="cs-sub">{cr.esc(copy["subhead"])}</p>' if copy["subhead"] else "")
    body = f"""<section class="{sec_cls}">
  <div class="cs-slot">
    <div class="cs-eyebrow-wrap">{eyebrow_html}</div>
    <div class="cs-title">{title_html}</div>
{collage}
    <div class="cs-foot">
      {sub_html}
      {form_html}
      {cta_html}
      {links_html}
      {rail_html}
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
    # FORM-SPLIT hero (fix6): a split HERO whose composition bound a validated
    # multi-field form slot (`_formFields` stamped by the adapter) composes as the
    # capture split — copy column | real form panel — instead of the info-band
    # shapes below, which have no slot for a form and silently dropped it.
    if layout.get("_formFields") is not None:
        return _compose_form_split(doc, layout, ctx, rendered, copy)
    media = _pick(rendered, "photo") or _pick(rendered, "image") or _pick(rendered, "media")
    _brand_name = (doc.get("brand") or {}).get("name") or "Brand"
    # BOUND MARK RUN in the media half (AS-33/AS-34, hubspot-v2 2026-07): a split
    # whose media slot bound a run of marks (award badges / partner logos, expanded
    # per-item by the adapter) renders that mark row — never invented editorial art
    # over the section's own bound evidence. Award-badge filename families ride the
    # brand's measured badge tier when one is authored (same rule as the flow strip).
    logo_frags = [r["html"] for r in rendered
                  if (r.get("contract") or "").lower().startswith("logo")
                  and (r.get("html") or "").strip()]
    mark_row = media is None and bool(logo_frags)
    if mark_row:
        # MEASURED ROW SCALE first (fid6/fid7 vocabulary, same stamp as the flow
        # strip): a pattern that recorded the row's container fraction (+ gap) draws
        # ONE aspect-weighted, equal-height row. The fraction is container-relative;
        # the split's media half spans 6 of 12 columns, so the in-cell fraction
        # doubles (clamped to the cell). Requires aspect coverage for every mark.
        media_html = ""
        scales = layout.get("_logoScale") if isinstance(layout.get("_logoScale"), dict) else {}
        group = next((str(r.get("group") or "") for r in rendered
                      if (r.get("contract") or "").lower().startswith("logo")), "")
        scale = scales.get(group) if isinstance(scales.get(group), dict) else None
        # MEASURED ITEM BOX first (fix2 2026-07, mediaScale.item — same stamp
        # vocabulary as the flow strip): fixed contain-fit mark frames + measured
        # box gap when the pattern recorded them.
        _item_box = (scale or {}).get("item") if isinstance((scale or {}).get("item"), dict) else {}
        if _item_box.get("width") and _item_box.get("height") and logo_frags:
            gap_var = (f' --cs-strip-gap: {scale["gap"]};'
                       if scale.get("gap") else "")
            items = "\n".join(f'      <div class="cs-logo-strip-item">{f}</div>'
                              for f in logo_frags)
            media_html = (f'<div class="cs-logo-strip cs-logo-strip--itembox" '
                          f'style="--cs-strip-item-w: {cr.esc(_item_box["width"])}; '
                          f'--cs-strip-item-h: {cr.esc(_item_box["height"])};{gap_var}">\n'
                          f'{items}\n    </div>')
        elif scale and scale.get("fraction"):
            aspects = scale.get("aspects") if isinstance(scale.get("aspects"), dict) else {}
            srcs = [re.search(r'src="assets/([^"]+)"', f) for f in logo_frags]
            weights = [aspects.get(Path(m.group(1)).name) if m else None for m in srcs]
            if weights and all(w for w in weights):
                frac = min(1.0, float(scale["fraction"]) / 0.5)
                gap_var = (f' --cs-strip-gap: {scale["gap"]};'
                           if scale.get("gap") else "")
                items = "\n".join(
                    f'      <div class="cs-logo-strip-item" style="flex: {w:g} 1 0">{f}</div>'
                    for w, f in zip(weights, logo_frags))
                media_html = (f'<div class="cs-logo-strip cs-logo-strip--scaled" '
                              f'style="--cs-strip-fraction: {frac:g};{gap_var}">\n'
                              f'{items}\n    </div>')
        if not media_html:
            badge_style = ""
            _spacing = ((doc.get("tokens") or {}).get("spacing")) or {}
            if isinstance(_spacing.get("badge-tier"), dict) and all(
                    re.search(r"(badge|award|seal|leader|top-?\d+)", f, re.I)
                    for f in logo_frags):
                badge_style = ' style="--c-logo-strip-h: var(--space-badge-tier)"'
            items = "\n".join(f'      <div class="cs-logo-strip-item">{f}</div>'
                              for f in logo_frags)
            media_html = f'<div class="cs-logo-strip"{badge_style}>\n{items}\n    </div>'
    else:
        media_html = media["html"] if media else cr.render_image(
            doc, ctx, {"src": _composer_art(doc, layout, "hero"),
                       "variant": "hero",
                       "alt": f"{_brand_name} editorial photography"})
    # sysfix 2026-07: panel title / cta ELIDE when the section authored none — the
    # adapter no longer invents "Details"/"Learn more", so an empty string here must
    # not render an empty <h3>/bare arrow (fail-visible was wrong for OPTIONAL slots).
    title_html = ""
    if str(copy["panelTitle"]).strip():
        title_html = "<div class=\"cs-panel-title\">" + cr.render_heading(doc, ctx, {
            "text": copy["panelTitle"], "level": "h3"}) + "</div>"
    row_pairs = list(copy.get("rows", []))
    rows = cr.render_table(doc, ctx, {
        "rows": [{"label": lbl, "value": val} for lbl, val in row_pairs],
        "comparison": True,
    }) if row_pairs else ""
    # bound `button` contract slots (B5 parity with compose_stack_hero, sysfix
    # 2026-07: this route silently DROPPED them and rendered the copy-layer arrow
    # instead): real action slots compose as one horizontal .cs-hero-actions row
    # under the intro, in declared order; the legacy copy-driven arrow renders
    # only when NO bound action slot exists.
    action_frags = [r["html"] for r in rendered
                    if r.get("contract") == "button" and (r.get("html") or "").strip()]
    actions_html = ""
    cta_html = ""
    if action_frags:
        actions_html = (f'\n    <div class="cs-hero-actions"{ag_attrs(doc, layout)}>'
                        + "".join(action_frags) + "</div>")
    elif str(copy["cta"]).strip():
        cta_html = ('<div class="cs-panel-foot">'
                    + cr.render_arrow_link(doc, ctx, {"label": copy["cta"]}) + "</div>")
    eyebrow_html = cr.render_eyebrow(doc, ctx, {"text": copy["eyebrow"]})
    # supporting body (sysfix 2026-07): an authored info-band body used to be silently
    # DROPPED (copy["body"] was never read on this route); render it under the band
    # heading. Sections without one render byte-identically (the block elides).
    band_body = ""
    if str(copy["body"]).strip():
        band_body = "\n    " + cr.render_paragraph(
            doc, ctx, {"text": copy["body"], "measure": "50ch"})
        # QUOTE ATTRIBUTION (fix7, pass-3 follow-up 7): a testimonial-contract split
        # carries its name — role line as the caption under the quote copy (the same
        # person register the stack path renders); attribution-less splits elide.
        if str(copy.get("attribution") or "").strip():
            band_body += "\n    " + cr.render_caption(
                doc, ctx, {"text": copy["attribution"]})
    # SINGLE CASE-STUDY COUNTERWEIGHT.  A media-bearing card in a split is one
    # atomic component, not a text primitive plus an unrelated/default image.
    # The adapter stamps only a real bound asset, so this branch cannot invent a
    # painted half.  Existing split sections have no stamp and remain unchanged.
    case_card = layout.get("_caseCard") if isinstance(layout.get("_caseCard"), dict) else None
    if case_card is not None:
        is_landmark = str(((layout.get("_composition") or {}).get("useCase")
                           or "")).lower() == "hero"
        lead = cr.render_header(doc, ctx, {
            "eyebrow": copy["eyebrow"], "heading": copy["heading"], "level": "display",
            "accent": False, "landmark": is_landmark})
        support = (cr.render_paragraph(
            doc, ctx, {"text": copy["body"], "measure": "48ch"})
            if str(copy["body"]).strip() else "")
        case_eyebrow = (cr.render_eyebrow(doc, ctx, {"text": case_card.get("eyebrow")})
                         if str(case_card.get("eyebrow") or "").strip() else "")
        case_heading = (cr.render_heading(
            doc, ctx, {"text": case_card.get("heading"), "level": "h2", "tag": "h2"})
            if str(case_card.get("heading") or "").strip() else "")
        case_meta = (cr.render_caption(doc, ctx, {"text": case_card.get("meta")})
                     if str(case_card.get("meta") or "").strip() else "")
        case_body = (cr.render_paragraph(
            doc, ctx, {"text": case_card.get("body"), "measure": "40ch"})
            if str(case_card.get("body") or "").strip() else "")
        case_action = (cr.render_arrow_link(
            doc, ctx, {"label": case_card.get("cta"), "accent": False})
            if str(case_card.get("cta") or "").strip() else "")
        return f"""<section class="cs-section cs-split-sec cs-caselead-sec">
  <div class="cs-media-split cs-caselead">
    <div class="cs-media-split-copy cs-caselead-copy">
      {lead}{support}
    </div>
    <article class="cs-module cs-module--plate cs-module--anatomy cs-media-split-media cs-caselead-card">
      <figure class="cs-module-media" style="aspect-ratio: {cr.esc(case_card.get('aspect') or '16 / 10')};">{media_html}</figure>
      <div class="cs-caselead-card-copy">
        {case_eyebrow}{case_heading}{case_meta}{case_body}{case_action}
      </div>
    </article>
  </div>
</section>"""
    # ACCORDION OPEN-STATE (P2, replica-gate punch list): a split whose reused pattern
    # declares the sanctioned `inset-emphasis` list treatment composes its rows as a
    # native single-open accordion (<details name=…> — exclusive by the platform, no
    # JS) with the EVIDENCED item expanded: the first row carrying body copy opens and
    # inverts onto the treatment's declared surface ROLE (resolved through the brand's
    # own layer-1 vars). No row carries body copy ⇒ all-idle collapsed (the degrade);
    # no stamped device ⇒ the classic panel/split branches below render unchanged.
    # TAB DEVICE (fix1 2026-07 item-9, stamped from the pattern's sanctioned `tabs`
    # treatment): a split whose section copy preserves the switcher's panels verbatim
    # (layoutCopy `panels`, + `tabs` labels) composes the WAI-ARIA APG tab device —
    # tablist/tab/tabpanel with roving tabindex, first tab active (the JS-off truth),
    # arrow-key operation via the shared structural script. No panels ⇒ the branch
    # never fires (the classic split renders, byte-identical).
    tab_panels = [p for p in copy.get("panels") if isinstance(p, dict)] \
        if isinstance(copy.get("panels"), list) else []
    if tab_panels and isinstance(layout.get("_tabs"), dict):
        return _compose_tab_split(doc, layout, ctx, copy, tab_panels)
    # SPLIT-PANEL CAROUSEL statics (fix1 2026-07 item-6, stamped from the pattern's
    # sanctioned `carousel` treatment): the authored slide stacks (layoutCopy `items`,
    # heading+body+media each) compose as ONE split row — slide 1 visible (the JS-off
    # truth), siblings as hidden switchable panels — with the captured control rail
    # (round prev/next at the row edges, dot rail below, first dot active).
    car_slides = [s for s in copy.get("items")
                  if isinstance(s, dict) and str(s.get("heading") or "").strip()] \
        if isinstance(copy.get("items"), list) else []
    if car_slides and isinstance(layout.get("_carousel"), dict):
        return _compose_split_carousel(doc, layout, ctx, copy, car_slides)
    if row_pairs and isinstance(layout.get("_accordion"), dict):
        # honest media degrade (fid2 2026-07): the accordion's counterweight media
        # binds ONLY a slot-bound asset — never the page's default hero art (the
        # noise texture was riding in as the "product UI" panel). With no bound
        # asset the measured light media WELL renders empty (the well itself is the
        # evidence; its fill is the brand's own raised-surface var).
        if media is None or "c-image-ph" in (media_html or ""):
            # (a placeholder chip is a gallery device, not composed-page evidence)
            media_html = '<div class="cs-acc-well" aria-hidden="true"></div>'
        return _compose_accordion_split(doc, layout, ctx, copy, row_pairs,
                                        media_html, band_body, actions_html)
    # PANEL EVIDENCE gate (sysfix 2026-07, punch-list item 9 completion): the cream
    # panel is REAL only when the brand declared panel furniture — a title or ruled
    # rows. Without them the panel ELIDES (degrade-to-absent; the old markup shipped
    # an empty cream box once the invented "Details"/"Learn more" fillers were
    # removed) and the section composes as the classic media | text split instead:
    # the copy column takes the second half (grounding order: slots as declared),
    # heading on the section h2 register, actions/arrow riding the text column.
    if not (title_html or rows):
        tail = actions_html
        if not tail and str(copy["cta"]).strip():
            tail = "\n      " + cr.render_arrow_link(doc, ctx, {"label": copy["cta"]})
        # a HERO split's opening statement is the page LANDMARK even at the
        # measure-fit h2 register — the licensed punctuation-accent device
        # applies there exactly as on display-rank landmarks (fix7 punch 1).
        is_landmark = str(((layout.get("_composition") or {}).get("useCase")
                           or "")).lower() == "hero"
        header_html = cr.render_header(doc, ctx, {
            "eyebrow": copy["eyebrow"], "heading": copy["heading"], "level": "h2",
            "accent": False, "landmark": is_landmark})
        # MEASURED BAND GEOMETRY (fid10 2026-07, same stamp family as the accordion
        # device): a split pattern that recorded its media region (deviceGeometry.
        # media aspect/align/fit) draws the source's frame — e.g. a SQUARE media well
        # letterboxing a landscape product-UI shot — instead of cover-cropping at the
        # asset's own aspect; a recorded bandPadding overrides the site-average
        # section rhythm for THIS band only. No stamp ⇒ byte-identical markup.
        geo = layout.get("_accGeometry") if isinstance(layout.get("_accGeometry"), dict) else {}
        media_cls, media_vars = "", []
        if geo.get("mediaAspect"):
            media_cls += " cs-split-media--framed"
            media_vars.append(f"--cs-split-media-aspect: {cr.esc(str(geo['mediaAspect']))}")
        if geo.get("mediaTop"):
            media_cls += " cs-split-media--top"
        if geo.get("mediaContain"):
            media_cls += " cs-split-media--contain"
        media_style = f' style="{"; ".join(media_vars)};"' if media_vars else ""
        bp = layout.get("_bandPadding") if isinstance(layout.get("_bandPadding"), dict) else {}
        pad_decls = "".join(
            f" --c-section-pad-{k}: {cr.esc(bp[k])};" for k in ("top", "bottom") if bp.get(k))
        sec_style = f' style="{pad_decls.strip()}"' if pad_decls else ""
        # a mark row is a flex strip, not an image — no mask frame around it.
        media_cell = media_html if mark_row \
            else f'<div class="c-image-mask">{media_html}</div>'
        return f"""<section class="cs-section cs-split-sec"{sec_style}>
  <div class="cs-split">
    <div class="cs-split-media{media_cls}"{media_style}>{media_cell}</div>
    <div class="cs-split-body">
      {header_html}{band_body}{tail}
    </div>
  </div>
</section>"""
    # The dark info-band heading rides the brand's DISPLAY tier by default (same
    # family/scale logic as the hero + collage headings) — on the dark inverse surface
    # it reads in paper/white (var(--c-ink) = text/on-inverse), accent reserved for the
    # hero. DEMOTABLE (W5, stress-playbook 2026-07): an authored/adapter-supplied
    # `headingLevel` (slot copy.level via _split_copy, or the composition adapter's
    # below-the-hero section-tier default) wins — legacy pages whose copy layer carries
    # no headingLevel keep the display default byte-identically.
    band_heading = cr.render_heading(doc, ctx, {
        "text": copy["heading"],
        "level": (str(copy["headingLevel"]).strip().lower() or "display"),
        "accent": False,
        "landmark": str(((layout.get("_composition") or {}).get("useCase")
                         or "")).lower() == "hero"})
    return f"""<section class="cs-section cs-split-sec">
  <div class="cs-split-intro">
    <div class="cs-eyebrow-wrap">{eyebrow_html}</div>
    {band_heading}{band_body}{actions_html}
  </div>
  <div class="cs-split cs-split--panel">
    <div class="cs-split-media"><div class="c-image-mask">{media_html}</div></div>
    <div class="cs-panel">
      {title_html}
      <div class="c-rows c-rows--table">{rows}</div>
      {cta_html}
    </div>
  </div>
</section>"""


def _compose_form_split(doc, layout, ctx, rendered, copy):
    """FORM-SPLIT hero (fix6, `hero-form-split` anatomy): the copy column carries the
    hero ladder (eyebrow → display heading → support → proof points → stat) and the
    counterweight half is a REAL capture panel — the signup scaffold's field anatomy
    (`_signup_field_html`, same token chain as the boxed form variant), plated on the
    brand's Container surface when the grammar declares one (card_panel_role;
    panel-less brands keep the open form column, no invented plate). Every visible
    value is authored: fields/submit/heading/note ride the validated `_formFields`
    stamp, proof points ride `_formSplit` (the section's own list slot), the stat is
    the bound stat fragment. Composes ONLY when the adapter stamped a split hero's
    form slot — every other split renders byte-identically upstream."""
    ff = layout.get("_formFields") or {}
    fs = layout.get("_formSplit") if isinstance(layout.get("_formSplit"), dict) else {}
    uid = _token_var_slug(str(layout.get("id") or "form-split"))
    rows = "\n".join(_signup_field_html(doc, ctx, f, i, uid)
                     for i, f in enumerate(ff.get("fields") or []))
    submit = str(ff.get("submit") or copy["cta"] or "Submit").strip()
    if (ctx.cta or cr.cta_shape(doc)) == "filled":
        submit_html = f'<button class="c-button" type="submit">{cr.esc(submit)}</button>'
    else:
        submit_html = (f'<button class="c-arrow-link cs-signup-submit-link" '
                       f'type="submit">{cr.esc(submit)} <span class="c-arrow" '
                       f'aria-hidden="true">&rarr;</span></button>')
    title_html = ""
    if str(ff.get("heading") or "").strip():
        title_html = "\n      " + cr.render_heading(doc, ctx, {
            "text": ff["heading"], "level": "h3"})
    # the note is SENTENCE microcopy (scheduling/expectation line) — it rides the
    # signup consent register (sentence case), never the uppercase caption microlabel.
    note = str(ff.get("note") or "").strip()
    note_html = (f'\n      <p class="cs-signup-consent cs-form-split-note">'
                 f'{cr.esc(note)}</p>' if note else "")
    consent = str(ff.get("consent") or "").strip()
    consent_html = (f'\n      <p class="cs-signup-consent">{cr.esc(consent)}</p>'
                    if consent else "")
    plate_cls = " cs-signup-panel--plate" if card_panel_role(doc) is not None else ""
    panel_html = f"""<form class="cs-signup-panel cs-form-split-panel{plate_cls}" action="#" method="post">{title_html}
      <div class="cs-signup-grid">
{rows}
      </div>{consent_html}
      <div class="cs-signup-actions">{submit_html}</div>{note_html}
    </form>"""
    # HEADING FIT-TO-MEASURE (fix7 punch 5; AS-66): the display rung in this HALF-
    # MEASURE column steps DOWN the brand's measured heading ladder until the
    # projected line count fits the hero display cap (3) — the register keeps its
    # display CLASS (semantics + the SR-HERO-01 budget still bind) and re-registers
    # its SIZE to the stepped rung via the data-fit stamp, the same channel as
    # pass1's overlay-panel re-registration. Full-measure headings never step.
    fit_cap = 3
    fit_rung = heading_fit_level(doc, copy["heading"],
                                 split_half_measure_px(doc), cap=fit_cap)
    fit_attrs = f' data-fit-cap="{fit_cap}"'
    if fit_rung != "display":
        fit_attrs += f' data-fit-rung="{cr.esc(fit_rung)}"'
    # eyebrow + heading compose as ONE header block: render_header owns the
    # eyebrow→heading seam (the brand's relational-ladder token), so the split
    # column's flex gap never re-registers it.
    header_html = cr.render_header(doc, ctx, {
        "eyebrow": copy["eyebrow"], "heading": copy["heading"],
        "level": "display", "accent": False})
    # a content-block support slot (pass2): its OWN heading (`intro`) is the copy
    # column's lead-in when no separate body paragraph is authored, and its body
    # strings (`support`) compose as real paragraphs — the block contract's shape,
    # and the form's stated reason precedes the field (AS-14). The ruled-points
    # device below stays the `list` contract's presentation.
    # MARKED-LIST intent (fix7 punch 3): a composition that DECLARES list intent
    # (knobs.supportKind list/bullets, stamped on _formSplit by the adapter)
    # renders the parallel support items as the marked-list device — brand glyph
    # marker in the accent role, hanging indent, list-item-gap stride — never a
    # run of look-alike paragraphs (the silent knob drop AS-63 now fails loud).
    body_txt = str(copy["body"]).strip() or str(fs.get("intro") or "").strip()
    body_html = ("\n      " + cr.render_paragraph(doc, ctx, {"text": body_txt})) \
        if body_txt else ""
    support = [str(s).strip() for s in (fs.get("support") or []) if str(s).strip()]
    list_intent = str(fs.get("supportKind") or "").lower() in ("list", "bullets")
    if support and list_intent:
        body_html += "\n      " + cr.render_marked_list(doc, ctx, {"items": support})
    else:
        for s in support:
            body_html += "\n      " + cr.render_paragraph(doc, ctx, {"text": s})
    points = [str(p).strip() for p in (fs.get("points") or []) if str(p).strip()]
    points_html = ""
    if points:
        lis = "\n".join(f"        <li>{cr.esc(p)}</li>" for p in points)
        points_html = f'\n      <ul class="cs-form-split-points">\n{lis}\n      </ul>'
    stat = _pick(rendered, "stat")
    stat_html = ("\n      " + stat["html"]) \
        if stat and (stat.get("html") or "").strip() else ""
    flip = " cs-split--form-left" if str(fs.get("side") or "").lower() == "left" else ""
    intent_attr = ' data-list-intent="list"' if (support and list_intent) else ""
    return f"""<section class="cs-section cs-split-sec cs-form-split-sec">
  <div class="cs-split cs-split--form{flip}">
    <div class="cs-split-body"{fit_attrs}{intent_attr}>
      {header_html}{body_html}{points_html}{stat_html}
    </div>
    {panel_html}
  </div>
</section>"""


def _compose_accordion_split(doc, layout, ctx, copy, row_pairs, media_html,
                             band_body, actions_html):
    """The split's ACCORDION presentation (P2 device; see compose_info_band). List
    column first (the declared reading order for this device), media column as the
    counterweight. Exclusive-open rides the platform (<details name=…>); the active
    item's inversion resolves the treatment's surface/hoverWash ROLES to layer-1 vars
    scoped inline on the list — unknown/missing roles leave the vars unset and the
    CSS fallbacks keep the idle (non-inverted) presentation."""
    # keep the layout's OWN stamp dict (even when empty): the media-swap wiring
    # writes the bound indexes back onto it for device_scaffold_css to read.
    acc = layout.get("_accordion")
    acc = acc if isinstance(acc, dict) else {}
    layout["_accordion"] = acc
    group = f"acc-{_token_var_slug(layout.get('id') or 'section')}"
    scope_vars = []
    surf_role = str(acc.get("surfaceRole") or "")
    surf_spec = ((doc.get("tokens") or {}).get("surfaces") or {}).get(surf_role)
    if isinstance(surf_spec, dict) and surf_spec.get("bg"):
        scope_vars.append(f"--acc-active-bg: var(--surface-{_token_var_slug(surf_role)})")
        ink_role = str(surf_spec.get("textPrimary") or "")
        if ink_role:
            scope_vars.append(f"--acc-active-ink: var(--color-{_token_var_slug(ink_role)})")
    wash_role = str(acc.get("hoverWash") or "")
    if wash_role and wash_role in (((doc.get("tokens") or {}).get("colors")) or {}):
        scope_vars.append(f"--acc-hover-bg: var(--color-{_token_var_slug(wash_role)})")
    style_attr = f' style="{"; ".join(scope_vars)};"' if scope_vars else ""
    # the EVIDENCED active item: the first row whose authored copy carries a body
    # (the capture shows exactly one expanded item; rows without body copy are the
    # collapsed idle items). None carries one ⇒ no `open` anywhere (degrade).
    active_idx = next((i for i, (_l, v) in enumerate(row_pairs) if str(v).strip()), None)
    chev = ('<span class="c-acc-chev" aria-hidden="true"><svg viewBox="0 0 10 6" '
            'width="10" height="6" fill="none" stroke="currentColor" '
            'stroke-width="1.5"><path d="M1 1l4 4 4-4"/></svg></span>')
    # per-row ICONS (fid2 2026-07): authored item icons (the brand's own marks) render
    # as a leading icon tile on each trigger; rows without one keep the plain label.
    # Evidence-checked against the ACTIVE brand's inventory (AS-34) — a name that is
    # not the brand's own file renders nothing.
    inv = set(doc.get(ASSET_INVENTORY_KEY) or []) if isinstance(doc, dict) else set()
    row_icons = [str(x or "") for x in (copy.get("rowIcons") or [])]
    # PER-ITEM MEDIA SWAP (fid5 2026-07): items binding their own media asset
    # (section-copy items[].media, folded to rowMedia by the adapters) drive the
    # right-side well — the ACTIVE item's asset shows, swapping (crossfade on the
    # brand's motion aliases) when the open item changes. Evidence-checked against
    # the ACTIVE brand's inventory (AS-34); no item binding media ⇒ the single-media
    # path below stays untouched (bound slot asset, else the honest well).
    row_media = [str(x or "") for x in (copy.get("rowMedia") or [])]
    media_names = []
    for i in range(len(row_pairs)):
        nm = Path(row_media[i]).name if i < len(row_media) and row_media[i] else ""
        media_names.append(nm if nm and nm in inv else "")
    if any(media_names):
        layers = ['<div class="cs-acc-well" aria-hidden="true"></div>']
        for i, nm in enumerate(media_names):
            if not nm:
                continue
            fit = (" c-acc-media--contain"
                   if cr.asset_render_mode(doc, nm, "accordion-media") == "contain" else "")
            active_cls = " is-active" if i == active_idx else ""
            layers.append(
                f'<img class="cs-acc-media-item{fit}{active_cls}" data-acc-i="{i}" '
                f'src="assets/{cr.esc(nm)}" alt="" loading="lazy">')
        media_html = ('<div class="cs-acc-media">' + "".join(layers) + "</div>")
        # stamp the bound indexes so device_scaffold_css emits the matching
        # open-details -> media-layer pairing rules for THIS page (AS-37: the
        # generated CSS ships only where the device composed).
        acc["mediaIdx"] = [i for i, nm in enumerate(media_names) if nm]
    # ACTIVE-ITEM AFFORDANCE: the treatment may declare the capture's round
    # go-affordance on the expanded item (affordance: circle-arrow) — drawn with the
    # active panel's own ink/paper vars, never a literal.
    affordance = str(acc.get("affordance") or "").strip().lower()
    arrow = ""
    if affordance == "circle-arrow":
        arrow = ('\n        <span class="c-acc-go" aria-hidden="true">'
                 '<svg viewBox="0 0 14 14" width="14" height="14" fill="none" '
                 'stroke="currentColor" stroke-width="1.5">'
                 '<path d="M2 7h10M8 3l4 4-4 4"/></svg></span>')
    items = []
    for i, (label, val) in enumerate(row_pairs):
        is_open = " open" if i == active_idx else ""
        # media-pairing attribute: only items that BOUND media carry it (the
        # generated :has() rules match on it; media-less items pair nothing).
        media_attr = f' data-acc-media="{i}"' if (i < len(media_names)
                                                  and media_names[i]) else ""
        icon_html = ""
        icon_name = Path(row_icons[i]).name if i < len(row_icons) and row_icons[i] else ""
        if icon_name and icon_name in inv:
            icon_html = (f'<img class="c-acc-icon" src="assets/{cr.esc(icon_name)}" '
                         f'alt="" aria-hidden="true">')
        panel = ""
        if str(val).strip():
            panel = ('\n        <div class="c-acc-panel">'
                     + cr.render_paragraph(doc, ctx, {"text": val, "measure": "44ch"})
                     + (arrow if i == active_idx else "")
                     + "</div>")
        items.append(
            f'      <details class="c-acc-item" name="{group}"{media_attr}{is_open}>\n'
            f'        <summary class="c-acc-trigger">{icon_html}<span class="c-acc-label">'
            f'{cr.esc(label)}</span>{chev}</summary>{panel}\n'
            f'      </details>')
    header_html = cr.render_header(doc, ctx, {
        "eyebrow": copy["eyebrow"], "heading": copy["heading"], "level": "h2",
        "accent": False})
    # MEASURED BAND GEOMETRY (fid9 2026-07, stamped from contentShape.deviceGeometry):
    # the source band's own proportions override the structural split — equal columns
    # at the measured gutter, the header stack riding the LIST column's first row (so
    # the heading wraps at the column measure like the capture), square top-aligned
    # media region, and the measured list rhythm (trigger height + inter-item gap).
    # All var/class-gated: no stamp ⇒ the historical structural markup, byte-identical.
    geo = layout.get("_accGeometry") if isinstance(layout.get("_accGeometry"), dict) else {}
    split_vars = []
    for key, var in (("columnGap", "--cs-acc-colgap"), ("rowGap", "--cs-acc-rowgap"),
                     ("contentSpan", "--cs-acc-span"),
                     ("triggerMinH", "--cs-acc-trig-minh"), ("itemGap", "--cs-acc-itemgap"),
                     ("mediaAspect", "--cs-acc-media-aspect")):
        if geo.get(key):
            split_vars.append(f"{var}: {cr.esc(str(geo[key]))}")
    split_style = f' style="{"; ".join(split_vars)};"' if split_vars else ""
    equal_cls = " cs-acc-split--equal" if geo.get("equalColumns") else ""
    media_cls = " cs-split-media--top" if geo.get("mediaTop") else ""
    # MEASURED BAND PADDING (fid7 mechanism): this band's own vertical rhythm
    # overrides the site-average section padding vars when the pattern measured it.
    bp = layout.get("_bandPadding") if isinstance(layout.get("_bandPadding"), dict) else {}
    pad_decls = "".join(
        f" --c-section-pad-{k}: {cr.esc(bp[k])};" for k in ("top", "bottom") if bp.get(k))
    sec_style = f' style="{pad_decls.strip()}"' if pad_decls else ""
    intro = f"""<div class="cs-split-intro">
    {header_html}{band_body}{actions_html}
  </div>"""
    # SECTION ACTION SLOT (W8, stress-playbook 2026-07): a split-accordion section
    # that authors a cta (and binds no real button slot — those render in the intro's
    # actions row above) closes the LIST column with the brand's arrow link, riding
    # the split's left-anchored grammar. The old path silently DROPPED the declared
    # action — no render, no unresolved marker. Copy-less sections elide (no change).
    foot_html = ""
    if not actions_html and str(copy["cta"]).strip():
        foot_html = ('\n      <div class="cs-acc-foot">'
                     + cr.render_arrow_link(doc, ctx, {"label": copy["cta"]})
                     + "</div>")
    media_col = (f'<div class="cs-split-media{media_cls}">'
                 f'<div class="c-image-mask">{media_html}</div></div>')
    if geo.get("headerInColumn"):
        return f"""<section class="cs-section cs-split-sec cs-acc-sec"{sec_style}>
  <div class="cs-split cs-acc-split{equal_cls}"{split_style}>
    <div class="cs-acc-col cs-acc-col--lead">
      {intro}
      <div class="c-acc"{style_attr}>
{chr(10).join(items)}
      </div>{foot_html}
    </div>
    {media_col}
  </div>
</section>"""
    return f"""<section class="cs-section cs-split-sec cs-acc-sec"{sec_style}>
  {intro}
  <div class="cs-split cs-acc-split{equal_cls}"{split_style}>
    <div class="cs-acc-col">
      <div class="c-acc"{style_attr}>
{chr(10).join(items)}
      </div>{foot_html}
    </div>
    {media_col}
  </div>
</section>"""


def _compose_split_carousel(doc, layout, ctx, copy, slides):
    """SPLIT-PANEL CAROUSEL statics (fix1 2026-07 item-6; see compose_info_band).
    One panel per authored slide — copy column (h3 + body) LEFT, the slide's own
    bound illustration RIGHT — slide 1 rendered visible (the JS-off / static-capture
    truth), siblings as `hidden` switchable panels. Control rail per the captured
    anatomy: round prev/next buttons at the row edges (prev disabled on frame 1 —
    the capture shows it dimmed), a dot rail below with the first dot active.
    Everything chrome rides brand vars (hairline/ink/radius); slide media is
    evidence-checked against the ACTIVE brand's inventory (AS-34). The shared
    structural script (data-panelcar) makes the controls operable; JS-off keeps
    slide 1 — never an empty band."""
    inv = set(doc.get(ASSET_INVENTORY_KEY) or []) if isinstance(doc, dict) else set()
    # measured registers (deviceGeometry heading/cardRegister, fix1): the section
    # headline + the per-slide headings ride the tiers the pattern measured; the
    # ladder default / h3 hold for register-silent patterns.
    geo = layout.get("_accGeometry") if isinstance(layout.get("_accGeometry"), dict) else {}
    head_level = str(geo.get("headingRegister") or "") or section_heading_level(doc)
    slide_level = str(geo.get("cardRegister") or "") or "h3"
    header_html = ""
    if str(copy["heading"]).strip():
        header_html = cr.render_header(doc, ctx, {
            "eyebrow": copy["eyebrow"], "heading": copy["heading"],
            "level": head_level, "accent": False})
    sub = str(copy.get("subhead") or "").strip()
    sub_html = ("\n    " + cr.render_paragraph(doc, ctx, {"text": sub, "measure": "50ch"})
                if sub else "")
    n = len(slides)
    panels = []
    for i, s in enumerate(slides):
        head = cr.render_heading(doc, ctx, {
            "text": str(s.get("heading") or ""), "level": slide_level, "tag": "h3"})
        body_txt = str(s.get("body") or "").strip()
        body = ("\n          " + cr.render_paragraph(
            doc, ctx, {"text": body_txt, "measure": "44ch"})) if body_txt else ""
        nm = Path(str(s.get("media") or "")).name
        img = ""
        if nm and nm in inv:
            img = cr.render_image(doc, ctx, {
                "src": f"assets/{nm}", "mediaRole": "carousel-media",
                "alt": str(s.get("heading") or "")})
        media_col = (f'\n        <div class="cs-panelcar-media">'
                     f'<div class="c-image-mask">{img}</div></div>') if img else ""
        hidden = "" if i == 0 else " hidden"
        panels.append(
            f'      <div class="cs-panelcar-slide" role="group" '
            f'aria-roledescription="slide" aria-label="{i + 1} of {n}"'
            f' data-panelcar-i="{i}"{hidden}>\n'
            f'        <div class="cs-panelcar-grid">\n'
            f'        <div class="cs-panelcar-copy">{head}{body}</div>'
            f'{media_col}\n        </div>\n      </div>')
    chev_l = ('<svg viewBox="0 0 8 12" width="8" height="12" fill="none" '
              'stroke="currentColor" stroke-width="1.5" aria-hidden="true">'
              '<path d="M7 1L2 6l5 5"/></svg>')
    chev_r = ('<svg viewBox="0 0 8 12" width="8" height="12" fill="none" '
              'stroke="currentColor" stroke-width="1.5" aria-hidden="true">'
              '<path d="M1 1l5 5-5 5"/></svg>')
    dots = "".join(
        f'<button class="cs-panelcar-dot" type="button" data-panelcar-dot="{i}" '
        f'aria-label="Go to slide {i + 1}"'
        + (' aria-current="true"' if i == 0 else "") + "></button>"
        for i in range(n))
    label = str(copy["heading"]).strip() or "Carousel"
    bp = layout.get("_bandPadding") if isinstance(layout.get("_bandPadding"), dict) else {}
    pad_decls = "".join(
        f" --c-section-pad-{k}: {cr.esc(bp[k])};" for k in ("top", "bottom") if bp.get(k))
    sec_style = f' style="{pad_decls.strip()}"' if pad_decls else ""
    # measured illustration-column share (pattern mediaScale.fraction on the stamp).
    car_decls = []
    try:
        f = float((layout.get("_carousel") or {}).get("mediaFraction"))
        if 0 < f < 1:
            car_decls.append(f"--cs-panelcar-media-frac: {f:g}")
    except (TypeError, ValueError):
        pass
    # measured CONTROL PLACEMENT (fix3, treatment `controls` fact): `placement:
    # rail` seats prev/next ON the dot row — prev at the container's left edge,
    # next at its right, dots centered between (the captured bottom-rail chrome).
    # A declared control `size` rides along as the box var. Fact-less carousels
    # keep the structural mid-edge paddles and this branch emits nothing.
    controls = (layout.get("_carousel") or {}).get("controls")
    controls = controls if isinstance(controls, dict) else {}
    rail_nav = str(controls.get("placement") or "").strip().lower() == "rail"
    size = str(controls.get("size") or "").strip()
    if rail_nav and re.fullmatch(r"[\d.]+(?:rem|em|px)", size):
        car_decls.append(f"--cs-panelcar-arrow-size: {cr.esc(size)}")
    car_style = f' style="{"; ".join(car_decls)}"' if car_decls else ""
    if rail_nav:
        return f"""<section class="cs-section cs-panelcar-sec"{sec_style}>
  <div class="cs-split-intro">
    {header_html}{sub_html}
  </div>
  <div class="cs-panelcar cs-panelcar--railnav" data-panelcar{car_style} aria-roledescription="carousel" aria-label="{cr.esc(label)}">
    <div class="cs-panelcar-panels">
{chr(10).join(panels)}
    </div>
    <div class="cs-panelcar-nav">
      <button class="cs-panelcar-arrow cs-panelcar-arrow--prev" type="button" data-panelcar-prev aria-label="Previous slide" disabled>{chev_l}</button>
      <div class="cs-panelcar-dots">{dots}</div>
      <button class="cs-panelcar-arrow cs-panelcar-arrow--next" type="button" data-panelcar-next aria-label="Next slide">{chev_r}</button>
    </div>
  </div>
</section>"""
    return f"""<section class="cs-section cs-panelcar-sec"{sec_style}>
  <div class="cs-split-intro">
    {header_html}{sub_html}
  </div>
  <div class="cs-panelcar" data-panelcar{car_style} aria-roledescription="carousel" aria-label="{cr.esc(label)}">
    <button class="cs-panelcar-arrow cs-panelcar-arrow--prev" type="button" data-panelcar-prev aria-label="Previous slide" disabled>{chev_l}</button>
    <div class="cs-panelcar-panels">
{chr(10).join(panels)}
    </div>
    <button class="cs-panelcar-arrow cs-panelcar-arrow--next" type="button" data-panelcar-next aria-label="Next slide">{chev_r}</button>
    <div class="cs-panelcar-dots">{dots}</div>
  </div>
</section>"""


def _compose_tab_split(doc, layout, ctx, copy, panels):
    """TAB DEVICE (fix1 2026-07 item-9; see compose_info_band): WAI-ARIA APG tab
    semantics — a labelled `role=tablist` of native `role=tab` buttons (roving
    tabindex: selected tab is the only tab stop; ArrowLeft/Right + Home/End move
    selection via the shared structural script keyed on data-tabs), each controlling
    a `role=tabpanel` (tabindex=0 so the panel itself is reachable; non-active
    panels carry `hidden`). First tab active = the JS-off / static-capture truth.

    Panel anatomy per the captured evidence: a hairline-bordered card split — the
    panel's own case photo LEFT (inventory-checked, AS-34) / quote + bold name +
    role caption + arrow link RIGHT — closed by the stat pair on a vertical-rule
    row (the stat-rule treatment). Tab labels/quotes/stats are the section's OWN
    authored panels — nothing invented. Active-tab treatment (weight + accent
    underline) rides brand vars; the media fraction rides the pattern's measured
    mediaScale when recorded (--cs-tabs-media-frac)."""
    inv = set(doc.get(ASSET_INVENTORY_KEY) or []) if isinstance(doc, dict) else set()
    slug = _token_var_slug(layout.get("id") or "tabs")
    labels = [str(t) for t in (copy.get("tabs") or [])
              if isinstance(copy.get("tabs"), list) and str(t or "").strip()]
    if len(labels) != len(panels):   # authored labels win; panels' own headings degrade
        labels = [str(p.get("heading") or f"Tab {i + 1}") for i, p in enumerate(panels)]
    tabs_html = []
    panels_html = []
    for i, p in enumerate(panels):
        active = i == 0
        sel = "true" if active else "false"
        roving = "" if active else ' tabindex="-1"'
        tabs_html.append(
            f'      <button class="cs-tab" type="button" role="tab" '
            f'id="tab-{slug}-{i}" aria-selected="{sel}"{roving} '
            f'aria-controls="tabpanel-{slug}-{i}">{cr.esc(labels[i])}</button>')
        quote_txt = str(p.get("quote") or "").strip()
        quote = cr.render_paragraph(doc, ctx, {"text": quote_txt, "measure": "58ch"}) \
            if quote_txt else ""
        nm_txt, role_txt = str(p.get("name") or "").strip(), str(p.get("role") or "").strip()
        person = ""
        if nm_txt or role_txt:
            nm_html = f'<span class="c-person-name">{cr.esc(nm_txt)}</span>' if nm_txt else ""
            rl_html = f'<span class="c-person-role">{cr.esc(role_txt)}</span>' if role_txt else ""
            person = (f'\n          <div class="c-person">'
                      f'<span class="c-person-meta">{nm_html}{rl_html}</span></div>')
        cta_txt = str(p.get("cta") or "").strip()
        cta = ("\n          " + cr.render_arrow_link(doc, ctx, {"label": cta_txt})
               if cta_txt else "")
        img_nm = Path(str(p.get("media") or "")).name
        media = ""
        if img_nm and img_nm in inv:
            img = cr.render_image(doc, ctx, {
                "src": f"assets/{img_nm}", "mediaRole": "card-media",
                "alt": str(p.get("caption") or nm_txt or labels[i])})
            media = (f'\n        <div class="cs-tabcard-media">'
                     f'<div class="c-image-mask">{img}</div></div>')
        # stat pair spans the FULL card under photo+quote (captured anatomy),
        # centered cells split by the vertical hairline (the stat-rule treatment).
        stats = ""
        stat_items = [s for s in (p.get("stats") or []) if isinstance(s, dict)
                      and str(s.get("value") or "").strip()]
        if stat_items:
            cells = "".join(
                '<div class="cs-tabcard-stat">'
                + cr.render_stat(doc, ctx, {"value": str(s.get("value") or ""),
                                            "label": str(s.get("caption") or s.get("label") or "")})
                + "</div>" for s in stat_items)
            stats = f'\n        <div class="cs-tabcard-stats">{cells}</div>'
        hidden = "" if active else " hidden"
        panels_html.append(
            f'    <div class="cs-tabpanel" role="tabpanel" id="tabpanel-{slug}-{i}" '
            f'aria-labelledby="tab-{slug}-{i}" tabindex="0"{hidden}>\n'
            f'      <div class="cs-tabcard">{media}\n'
            f'        <div class="cs-tabcard-body">\n          {quote}{person}{cta}\n'
            f'        </div>{stats}\n      </div>\n    </div>')
    # measured media fraction (pattern mediaScale.fraction, carried on the stamp) —
    # the photo column's share of the card; the structural default otherwise.
    tab_decls = []
    try:
        f = float((layout.get("_tabs") or {}).get("mediaFraction"))
        if 0 < f < 1:
            tab_decls.append(f"--cs-tabs-media-frac: {f:g}")
    except (TypeError, ValueError):
        pass
    # measured active-tab rule color (treatment fact — the page's committed-accent
    # law collapses --c-accent to ink on this band, so the fact must ride scoped).
    au = (layout.get("_tabs") or {}).get("activeUnderline")
    if au:
        tab_decls.append(f"--cs-tab-active-rule: {cr.esc(str(au))}")
    frac_style = f' style="{"; ".join(tab_decls)}"' if tab_decls else ""
    list_label = str(copy["heading"]).strip() or "Case studies"
    bp = layout.get("_bandPadding") if isinstance(layout.get("_bandPadding"), dict) else {}
    pad_decls = "".join(
        f" --c-section-pad-{k}: {cr.esc(bp[k])};" for k in ("top", "bottom") if bp.get(k))
    sec_style = f' style="{pad_decls.strip()}"' if pad_decls else ""
    return f"""<section class="cs-section cs-tabs-sec"{sec_style}>
  <div class="cs-tabs" data-tabs{frac_style}>
    <div class="cs-tablist" role="tablist" aria-label="{cr.esc(list_label)}">
{chr(10).join(tabs_html)}
    </div>
{chr(10).join(panels_html)}
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

_FIELD_KINDS = ("text", "email", "tel", "select", "radio-group", "checkbox")


def _signup_field_html(doc, ctx, field: dict, idx: int, form_uid: str) -> str:
    """One signup-form field → accessible markup. Label text ALWAYS visible (a real
    <label>/<legend>, never placeholder-as-label); the control rides the brand's own
    boxed-input anatomy vars (--c-input-*/--color-border-input chain — same producers
    as the boxed variant of render_form). Kinds: text/email/tel (input), textarea
    (real multiline control, W12), select (native select + authored options),
    radio-group (fieldset+legend, one checked per authored default), checkbox
    (single opt-in row)."""
    kind = str(field.get("kind") or "text").lower()
    label = str(field.get("label") or "").strip()
    name = str(field.get("name") or "").strip() or re.sub(
        r"[^a-z0-9]+", "-", label.lower()).strip("-") or f"field-{idx}"
    helper = str(field.get("helper") or "").strip()
    span_cls = " cs-field--full" if str(field.get("span") or "").lower() != "half" else ""
    req = " required" if field.get("required") else ""
    # authored validation microcopy rides the control as data-error (static form:
    # native constraint validation runs; the authored string is carried, not invented UI).
    err = str(field.get("error") or "").strip()
    err_attr = f' data-error="{cr.esc(err)}"' if err else ""
    auto = (f' autocomplete="{cr.esc(str(field["autocomplete"]))}"'
            if field.get("autocomplete") else "")
    helper_html = (f'\n        <span class="cs-field-help">{cr.esc(helper)}</span>'
                   if helper else "")
    if kind == "radio-group":
        options = [str(o).strip() for o in (field.get("options") or []) if str(o).strip()]
        checked_i = field.get("checkedIndex")
        rows = "".join(
            f'\n        <label class="cs-choice"><input type="radio" name="{cr.esc(name)}" '
            f'value="{cr.esc(re.sub(r"[^a-z0-9]+", "-", o.lower()).strip("-"))}"'
            + (" checked" if isinstance(checked_i, int) and i == checked_i else "")
            + f'{req}><span class="cs-choice-label">{cr.esc(o)}</span></label>'
            for i, o in enumerate(options))
        return (f'      <fieldset class="cs-choice-group cs-field--full">\n'
                f'        <legend class="cs-field-label">{cr.esc(label)}</legend>'
                f'{rows}{helper_html}\n      </fieldset>')
    if kind == "checkbox":
        return (f'      <label class="cs-choice cs-choice--solo cs-field--full">'
                f'<input type="checkbox" name="{cr.esc(name)}"{req}>'
                f'<span class="cs-choice-label">{cr.esc(label)}</span></label>')
    fid = f"{form_uid}-{name}"
    if kind == "select":
        options = [str(o).strip() for o in (field.get("options") or []) if str(o).strip()]
        prompt = str(field.get("placeholder") or "").strip()
        opts = (f'\n          <option value="" disabled selected hidden>{cr.esc(prompt)}'
                f'</option>' if prompt else "")
        opts += "".join(
            f'\n          <option value="{cr.esc(re.sub(r"[^a-z0-9]+", "-", o.lower()).strip("-"))}">'
            f'{cr.esc(o)}</option>' for o in options)
        control = (f'<select class="cs-input cs-input--select" id="{cr.esc(fid)}" '
                   f'name="{cr.esc(name)}"{req}{err_attr}>{opts}\n        </select>')
    elif kind == "textarea":
        # REAL multiline control (W12, stress-playbook 2026-07): a declared textarea
        # renders <textarea> on the SAME brand input-anatomy chain as .cs-input
        # (border/radius/bg/focus tokens); rows is structural shape (~4 visible
        # lines), never a brand magnitude. The old whitelist coerced this kind to a
        # single-line <input type="text"> silently.
        ph = (f' placeholder="{cr.esc(str(field["placeholder"]))}"'
              if field.get("placeholder") else "")
        control = (f'<textarea class="cs-input cs-input--multiline" id="{cr.esc(fid)}" '
                   f'name="{cr.esc(name)}" rows="4"{ph}{auto}{req}{err_attr}></textarea>')
    else:
        itype = kind if kind in ("email", "tel") else "text"
        ph = (f' placeholder="{cr.esc(str(field["placeholder"]))}"'
              if field.get("placeholder") else "")
        control = (f'<input class="cs-input" id="{cr.esc(fid)}" type="{itype}" '
                   f'name="{cr.esc(name)}"{ph}{auto}{req}{err_attr}>')
    return (f'      <div class="cs-field{span_cls}">\n'
            f'        <label class="cs-field-label" for="{cr.esc(fid)}">{cr.esc(label)}'
            f'</label>\n        {control}{helper_html}\n      </div>')


def _compose_signup_form(doc, layout, ctx, rendered, style_ctx, *, copy,
                         header_html, body_html):
    """SIGNUP-FORM scaffold (event-scaffolds 2026-07) — the third new brand-agnostic
    scaffold: a real multi-field registration form (static markup, no backend) on the
    conversion stack's centered column. MECHANICS are generic (label-above boxed
    fields on a responsive half/full grid, radio/checkbox choice rows, consent line,
    one submit action, an aria-live success line for completeness of the static
    contract); every VISIBLE value resolves from brand facts:
      - field anatomy rides the SAME token chain as the boxed form variant
        (--c-input-radius/-border/-bg producers; border/input + focus-ring colors);
      - the submit is the measured button family via the c-button contract (cta-shape
        dispatch discipline — a typographic brand's form degrades its submit to the
        arrow-link register through the same law);
      - the panel (when the brand declares a Container surface, card_panel_role)
        plates the form on that surface; panel-less brands keep the open column.
    Field/label/microcopy come EXCLUSIVELY from the composition's validated
    `_formFields` stamp (AS-14: the intro copy states the exchange; AS-34: nothing
    invented here — an unauthored key simply doesn't render)."""
    ff = layout.get("_formFields") or {}
    fields = ff.get("fields") or []
    uid = re.sub(r"[^a-z0-9]+", "-", str(layout.get("id") or "signup").lower()).strip("-")
    rows = "\n".join(_signup_field_html(doc, ctx, f, i, uid)
                     for i, f in enumerate(fields))
    # consent is LEGAL SENTENCE microcopy — it rides the form's helper register
    # (sentence case), never the uppercase caption microlabel.
    consent = str(ff.get("consent") or "").strip()
    consent_html = (f'\n      <p class="cs-signup-consent">{cr.esc(consent)}</p>'
                    if consent else "")
    success = str(ff.get("success") or "").strip()
    success_html = (f'\n      <p class="cs-signup-success" aria-live="polite" hidden>'
                    f'{cr.esc(success)}</p>' if success else "")
    submit = str(copy["cta"]).strip() or "Submit"
    # the submit rides the measured button family CONTRACT: filled brands emit the
    # real <button class="c-button …"> (family class via the same slug discipline as
    # render_button); typographic brands keep the arrow-link register on a <button>
    # reset — law-first, never a hardcoded pill.
    if (ctx.cta or cr.cta_shape(doc)) == "filled":
        submit_html = (f'<button class="c-button" type="submit">{cr.esc(submit)}'
                       f'</button>')
    else:
        submit_html = (f'<button class="c-arrow-link cs-signup-submit-link" '
                       f'type="submit">{cr.esc(submit)} <span class="c-arrow" '
                       f'aria-hidden="true">&rarr;</span></button>')
    # meta line (e.g. the event's date/place restated at the point of decision) —
    # authored only; rides the caption register.
    meta = str(ff.get("meta") or "").strip()
    meta_html = (f'\n    <p class="c-caption cs-signup-meta">{cr.esc(meta)}</p>'
                 if meta else "")
    plate_cls = " cs-signup-panel--plate" if card_panel_role(doc) is not None else ""
    form_html = f"""<form class="cs-signup-panel{plate_cls}" action="#" method="post">
      <div class="cs-signup-grid">
{rows}
      </div>{consent_html}
      <div class="cs-signup-actions">{submit_html}</div>{success_html}
    </form>"""
    sm = layout.get("_stackMeasure")
    measure_style = (f' style="--cs-stack-measure: {cr.esc(str(sm))}; --c-cta-measure: 100%"'
                     if sm else "")
    bp = layout.get("_bandPadding") if isinstance(layout.get("_bandPadding"), dict) else {}
    pad_decls = "".join(
        f" --c-section-pad-{k}: {cr.esc(bp[k])};" for k in ("top", "bottom") if bp.get(k))
    sec_style = f' style="{pad_decls.strip()}"' if pad_decls else ""
    stack = f"""  <div class="cs-conversion cs-signup"{measure_style}>
    {header_html}
    {body_html}{meta_html}
    {form_html}
  </div>"""
    # the sanctioned full-bleed art band (fid5 grammar) carries the signup drama when
    # the composition stamped it; otherwise the flat conversion surface.
    if layout.get("_artSurface") is not None:
        art = _art_surface_src(doc, layout)
        art_html = (f'\n  <img class="cs-conversion-band-art" src="{cr.esc(art)}" '
                    f'alt="" aria-hidden="true">') if art else ""
        return f"""<section class="cs-section cs-conversion-sec cs-conversion-sec--band cs-signup-sec"{sec_style}>{art_html}
{stack}
</section>"""
    return f"""<section class="cs-section cs-conversion-sec cs-signup-sec"{sec_style}>
{stack}
</section>"""


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
    # register: the brand's measured section-heading tier (h2) when its type ladder
    # declares one (fid2 2026-07 — composed sections rode the display/H1 register,
    # oversizing every in-flow heading against the source); display is the degrade.
    header_html = cr.render_header(doc, ctx, {
        "eyebrow": copy["eyebrow"], "heading": copy["heading"],
        "level": section_heading_level(doc), "accent": ctx.is_dark})
    # sysfix 2026-07: a body-less conversion (e.g. a heading+pill inline banner) must
    # not render an empty <p> — the paragraph elides exactly like the header's
    # optional eyebrow slot does.
    body_html = cr.render_paragraph(doc, ctx, {"text": copy["body"], "measure": "40ch"}) \
        if str(copy["body"]).strip() else ""
    # SIGNUP-FORM scaffold (event-scaffolds 2026-07): a conversion whose composition
    # stamped validated multi-field form facts renders the registration form instead
    # of the single-line newsletter device. No stamp ⇒ every existing conversion
    # (underline form / button banner) renders byte-identically below.
    if layout.get("_formFields") is not None:
        return _compose_signup_form(doc, layout, ctx, rendered, style_ctx, copy=copy,
                                    header_html=header_html, body_html=body_html)
    action_frags = [r["html"] for r in rendered
                    if r.get("contract") == "button" and (r.get("html") or "").strip()]
    if action_frags:
        has_form_slot = any(r.get("contract") == "form" for r in rendered)
        form_html = cr.render_form(doc, ctx, {
            "placeholder": copy["placeholder"], "submit": copy["cta"]}) if has_form_slot else ""
        actions_html = (f'\n    <div class="cs-conversion-actions"{ag_attrs(doc, layout)}>'
                        f'{"".join(action_frags)}</div>')
    else:
        form_html = cr.render_form(doc, ctx, {
            "placeholder": copy["placeholder"], "submit": copy["cta"]})
        actions_html = ""
    # MEASURED STACK MEASURE (fid7 2026-07, stamped from the pattern's recorded
    # contentShape.stackMeasure — JS-off computed content-column cap): the centered
    # column rides the brand's real measure and the supporting paragraph spans it
    # (the measured geometry: body text fills the content column, no ch clamp).
    # Un-stamped layouts keep the classic 46rem column + 40ch prose measure
    # byte-identically (the structural degrade for brands without the fact).
    sm = layout.get("_stackMeasure")
    measure_style = (f' style="--cs-stack-measure: {cr.esc(str(sm))}; --c-cta-measure: 100%"'
                     if sm else "")
    stack = f"""  <div class="cs-conversion"{measure_style}>
    {header_html}
    {body_html}{actions_html}
    {form_html}
  </div>"""
    # MEASURED BAND PADDING (fid7 2026-07, stamped from contentShape.bandPadding):
    # this band's own measured vertical rhythm overrides the site-average section
    # padding vars (inline custom properties beat the per-section rhythm selector).
    # No stamp ⇒ no style attribute (site rhythm byte-identical).
    bp = layout.get("_bandPadding") if isinstance(layout.get("_bandPadding"), dict) else {}
    pad_decls = "".join(
        f" --c-section-pad-{k}: {cr.esc(bp[k])};" for k in ("top", "bottom") if bp.get(k))
    sec_style = f' style="{pad_decls.strip()}"' if pad_decls else ""
    # INSET PANEL presentation (fid2 2026-07, stamped from the pattern's sanctioned
    # panel-on-media treatment): the conversion stack sits on a rounded inset panel
    # painted with the brand's OWN panel-art (defaultArt `panel:` pin, else the
    # generic noise/texture inventory match). No art in the brand's inventory ⇒ the
    # panel still rounds on the surface's own tokens (flat fill degrade); no stamp
    # ⇒ the classic centered stack renders byte-identically.
    if layout.get("_insetPanel") is not None:
        art = _brand_art(doc, "panel", *brand_default_art_names(doc, "panel"))
        art_html = ""
        if art:
            art_html = (f'\n    <img class="cs-conversion-panel-art" src="{cr.esc(art)}" '
                        f'alt="" aria-hidden="true">')
        return f"""<section class="cs-section cs-conversion-sec cs-conversion-sec--panel"{sec_style}>
  <div class="cs-conversion-panel">{art_html}
{stack}
  </div>
</section>"""
    # FULL-BLEED ART BAND (fid5 2026-07, stamped from the pattern's sanctioned
    # `art-surface` background treatment): the whole SECTION box paints with the
    # brand's own band art (treatment-named file first — see _art_surface_src) behind
    # the stack, edge to edge — the closing-CTA-on-the-gradient-band grammar. No art
    # in the brand's inventory ⇒ the band class still applies on the flat surface
    # fill (degrade); no stamp ⇒ the classic centered stack renders byte-identically.
    if layout.get("_artSurface") is not None:
        art = _art_surface_src(doc, layout)
        art_html = ""
        if art:
            art_html = (f'\n  <img class="cs-conversion-band-art" src="{cr.esc(art)}" '
                        f'alt="" aria-hidden="true">')
        return f"""<section class="cs-section cs-conversion-sec cs-conversion-sec--band"{sec_style}>{art_html}
{stack}
</section>"""
    return f"""<section class="cs-section cs-conversion-sec"{sec_style}>
{stack}
</section>"""


# ── archetype: cards (staggered caption cards — features-staggered-caption-cards) ──

# MARK-vs-PHOTO asset classification (sysfix 2026-07): filename KIND vocabulary only
# (logo/badge/rating/icon families + any vector) — the same generic discipline as the
# AS-33 logo-strip device; never brand names or per-brand lists.
_MARK_FILE_RX = re.compile(
    r"(?:^|[-_./])(logos?|marks?|badges?|wordmarks?|glyphs?|stamps?|seals?|awards?|"
    r"ratings?|chips?|icons?)(?=$|[-_.\d])", re.I)


def _is_mark_asset(path) -> bool:
    """True when an asset file reads as a graphic MARK (logo/badge/rating/icon or any
    vector) — media that must render CONTAINED in its frame, never cover-cropped or
    stretched like a photograph."""
    name = Path(str(path or "")).name
    if not name:
        return False
    if name.lower().endswith(".svg"):
        return True
    return bool(_MARK_FILE_RX.search(Path(name).stem))


# ── SECTION HEADRAIL device (fix1 item-8 markup; fix2 recipe-fact consumption) ──

def _rail_spans_column(rail: dict) -> bool:
    """True when the rail's recipe facts pin it to the LOCAL column (a split/siderail
    copy column) instead of the section's content container — variant `span: column`
    wins over the recipe-level `geometry.railAlignment`."""
    variant = rail.get("variant") if isinstance(rail.get("variant"), dict) else {}
    span = str(variant.get("span") or "").lower()
    if span:
        return span == "column"
    geo = rail.get("geometry") if isinstance(rail.get("geometry"), dict) else {}
    return str(geo.get("railAlignment") or "").lower() == "column"


def _headrail_html(doc, ctx, rail: dict, *, eyebrow_html: str, cta_label: str,
                   legacy_pill_wrap: bool) -> str:
    """The section HEADRAIL device, shared by the cards + generic-flow composers:
    leading kicker (chip / pill / badge) — leader rule — trailing quiet action.

    RECIPE-BOUND rails (fix2, brand-schema §4.4e) render their variant's measured
    facts: kicker shape/box/radius/icon (emitted as inline --cs-rail-* vars the
    scaffold CSS consumes with structural defaults), rule style, trailing-action
    presence + family, and the measured rail->heading seam. Recipe-LESS rails keep
    the fix1 prose-vocabulary behavior byte-identically (chip when the slot binds
    an inventory asset; else the eyebrow, pill-wrapped only on the flow path when
    the prose says "pill"; rule dotted when the prose says so; trailing action
    whenever the section authors a cta)."""
    inv = set(doc.get(ASSET_INVENTORY_KEY) or []) if isinstance(doc, dict) else set()
    chip_asset = next((Path(a).name for a in (rail.get("assets") or [])
                       if Path(str(a)).name in inv), "")
    rail_prose = f"{rail.get('role') or ''} {rail.get('note') or ''}"
    variant = rail.get("variant") if isinstance(rail.get("variant"), dict) else {}
    kicker = variant.get("kicker") if isinstance(variant.get("kicker"), dict) else {}
    rule_v = variant.get("rule") if isinstance(variant.get("rule"), dict) else {}
    trail_v = variant.get("trail") if isinstance(variant.get("trail"), dict) else {}
    icon_v = kicker.get("icon") if isinstance(kicker.get("icon"), dict) else {}

    decls: list[str] = []

    def _decl(var: str, val) -> None:
        v = str(val or "").strip()
        if v:
            decls.append(f"--{var}: {cr.esc(v)}")

    # ── kicker ──
    shape = str(kicker.get("shape") or "").lower()
    icon_asset = Path(str(icon_v.get("asset") or "")).name
    if icon_asset and icon_asset not in inv:
        icon_asset = ""                      # inventory law: never bind a missing file
    icon_asset = icon_asset or chip_asset
    icon_img = (f'<img src="assets/{cr.esc(icon_asset)}" alt="" aria-hidden="true">'
                if icon_asset else "")
    if shape == "chip" and not kicker.get("label", False):
        # icon-only identity chip (measured box/radius/icon ride the vars)
        _decl("cs-rail-chip-size", kicker.get("size"))
        _decl("cs-rail-chip-radius", kicker.get("radius"))
        _decl("cs-rail-chip-icon", icon_v.get("size"))
        if kicker.get("border"):
            _decl("cs-rail-chip-border", "1px solid var(--c-hairline)")
        lead = f'<span class="cs-headrail-chip">{icon_img}</span>'
    elif shape in ("pill", "badge"):
        # labeled pill/badge kicker, optional leading icon inside the box
        _decl("cs-rail-pill-radius", kicker.get("radius"))
        _decl("cs-rail-pill-pad", kicker.get("padding"))
        _decl("cs-rail-pill-icon", icon_v.get("size"))
        pill_icon = icon_img if icon_v else ""
        lead = f'<span class="cs-headrail-pill">{pill_icon}{eyebrow_html}</span>'
    elif chip_asset:                          # legacy: slot binds an inventory mark
        lead = f'<span class="cs-headrail-chip">{icon_img}</span>'
    elif legacy_pill_wrap and "pill" in rail_prose.lower():
        lead = f'<span class="cs-headrail-pill">{eyebrow_html}</span>'
    else:
        lead = eyebrow_html
    if variant and str(kicker.get("surface") or "").lower() == "panel":
        # the kicker floats as a PANEL surface on the band (white plate on the
        # band's own paper — the same container role card plates paint)
        _decl("cs-rail-kicker-bg", "var(--c-panel, var(--c-paper))")

    # ── leader rule ──
    rule_style = str(rule_v.get("style") or "").lower()
    dotted = " cs-headrail-rule--dotted" if (
        rule_style == "dotted" or (not rule_style and "dotted" in rail_prose.lower())
    ) else ""
    rule_html = "" if rule_style == "none" else \
        f'<hr class="cs-headrail-rule{dotted}" aria-hidden="true">'

    # ── trailing action ──
    want_trail = trail_v.get("present") if isinstance(trail_v.get("present"), bool) \
        else bool(cta_label)
    trail = ""
    if want_trail and cta_label:
        trail = cr.render_button(doc, ctx, {
            "label": cta_label,
            "familyHint": str(trail_v.get("family") or "") or rail_prose})

    # ── shared geometry ──
    geo = rail.get("geometry") if isinstance(rail.get("geometry"), dict) else {}
    _decl("cs-rail-gap-below", geo.get("railToHeading"))
    _decl("cs-rail-item-gap", geo.get("kickerGap"))

    style_attr = f' style="{"; ".join(decls)}"' if decls else ""
    return (f'<div class="cs-headrail"{style_attr}>{lead}{rule_html}{trail}</div>')


def card_panel_role(doc) -> str | None:
    """The brand's declared CONTAINER surface role for card plates (fid2 2026-07):
    present only when the brand declares BOTH the card block device (blocks.card,
    usable) and a Container-scheme surface (the floating panel role its cards paint).
    None ⇒ the brand's cards are flat editorial modules (e.g. a no-cards neverDo
    brand) and the composers must not invent panels."""
    if not cr.block_device(doc, "card"):
        return None
    for role, spec in ((((doc or {}).get("tokens") or {}).get("surfaces")) or {}).items():
        if isinstance(spec, dict) and spec.get("bg") \
                and str(spec.get("schemeMode") or "").strip().lower() == "container":
            return role
    return None


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
    # default assets: EVIDENCE-CHECKED against the ACTIVE brand's inventory (AS-34) — a
    # brand without matching art renders the srcless placeholder, never foreign art.
    # UNIFORM default aspect (sysfix 2026-07): modules that declare no aspect all get
    # the SAME landscape frame — aspect VARIATION is pattern data (each authored card's
    # own `aspect:`, e.g. the staggered-caption pattern's 16/10 · 4/3 pair), never a
    # composer-invented alternation that leaves undeclared card rows ragged.
    _assets = [_brand_art(doc, "hero", *brand_default_art_names(doc, "hero")),
               _brand_art(doc, "detail", *brand_default_art_names(doc, "detail"))]
    _default_aspect = "16 / 10"
    brand_name = (doc.get("brand") or {}).get("name") or "Brand"
    # EDGE-CUT CAROUSEL STATICS (P2, replica-gate punch list): a cards section whose
    # reused pattern declares the sanctioned `edge-cut` treatment presents its modules
    # as the cut-at-viewport horizontal track — fixed-basis card plates on a native
    # overflow-x scroller that bleeds past the section's right padding, so the edge
    # card clips at the viewport (the carousel affordance the capture shows). Cards
    # ride the brand's own panel surface + card radius vars; mark media (company
    # logos) renders at mark height instead of a full media frame, and the quote
    # body leads the caption (card anatomy reading order). No treatment ⇒ the
    # contained grid renders unchanged.
    edgecut = bool(layout.get("_edgeCut"))
    # WHITE CARD PLATES (fid2 2026-07): a brand whose declared card device rides a
    # container-mode surface (blocks.card + a Container-scheme surface role) renders
    # its modules as REAL panels — bg/ink/radius from the brand's own panel vars —
    # in the contained grid too, not only on the edge-cut track. Brands without the
    # card device (or without a container surface) keep the flat editorial modules.
    plated = edgecut or card_panel_role(doc) is not None
    # CARD HEADING REGISTER (fid6 2026-07): the brand's card device may pin its heading
    # slot to a measured type register (blocks.card slots.heading.register — e.g. a
    # 20px h5-register card heading measured in the capture DOM). The register picks
    # the CLASS tier; the TAG stays h3 (document outline). h3 register = the default
    # for brands without the fact.
    _card_slots = (cr.block_device(doc, "card") or {}).get("slots") or {}
    _head_slot = _card_slots.get("heading") if isinstance(_card_slots, dict) else None
    _reg = str((_head_slot or {}).get("register") or "").strip().lower() \
        if isinstance(_head_slot, dict) else ""
    card_head_level = _reg if _reg in ("h2", "h3", "h4", "h5", "h6") else "h3"
    # PATTERN-MEASURED register override (fix1 2026-07 item-8, deviceGeometry.
    # cardRegister): THIS section's cards ride their own measured tier — e.g. an
    # oversized agent-card family (h3) beside the brand's compact product-card
    # device register (h5). The stamp also PROMOTES authored card headings out of
    # the caption fold on media cards (the heading is a measured fact here, not an
    # inference); stamp-less sections keep the device/caption behavior unchanged.
    _pat_geo = layout.get("_accGeometry") if isinstance(layout.get("_accGeometry"), dict) else {}
    pat_register = str(_pat_geo.get("cardRegister") or "").strip().lower()
    if pat_register:
        card_head_level = pat_register
    modules = []
    for i, card in enumerate(cards):
        fill = layout.get("_collectionFill") \
            if isinstance(layout.get("_collectionFill"), dict) else {}
        fill_items = fill.get("items") if isinstance(fill.get("items"), list) else []
        fill_item = fill_items[i] if i < len(fill_items) and isinstance(fill_items[i], dict) else {}
        try:
            grid_span = max(1, int(fill_item.get("span") or 1))
        except (TypeError, ValueError):
            grid_span = 1
        try:
            content_measure = float(fill_item.get("contentMeasureCh") or 0)
        except (TypeError, ValueError):
            content_measure = 0
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
        # QUOTE/TESTIMONIAL card detection (W7, stress-playbook 2026-07): a module
        # carrying person attribution (name/role/avatar) is a quote card — it NEVER
        # inherits the defaultArt backfill; only an EXPLICITLY bound asset renders.
        # Generic content-shape detection, no section names, no brand specifics.
        is_quote_card = bool(card.get("name") or card.get("avatar") or card.get("role"))
        if raw:
            src = raw if str(raw).startswith(("assets/", "http://", "https://", "data:")) \
                else f"assets/{raw}"
        elif is_quote_card:
            src = None            # text-first quote card: no media well at all
        else:
            src = _assets[i % len(_assets)]
        if not alt:
            cap = (card.get("caption") or "").strip()
            alt = f"{brand_name} — {cap}" if cap else f"{brand_name} photography"
        aspect = card.get("aspect") or _default_aspect
        # MEDIA TREATMENT FACT (fid16): card media resolves from the active brand's
        # assetKind + generic slot-role rules.  No filename vocabulary: transparent
        # illustrations/marks can contain, while screenshot/photo/product-UI card
        # media can cover the full well when the curator/evidence authorizes it.
        media_mode = cr.asset_render_mode(doc, src, "card-media") if src else "cover"
        contained_media = media_mode == "contain"
        # DECLARED mark row (fit: mark, hubspot-v2 2026-07): the module's art is a
        # glyph/icon that sits at MARK height above the card copy — the feature-card
        # anatomy — never a media well. Fact-only: no brand declares it, no change.
        mark_media = media_mode == "mark"
        # Edge-cut MARK anatomy is fact-first (hubspot-v2 2026-07): a DECLARED
        # `fit: mark` renders the glyph row; a DECLARED `fit: contain` keeps the
        # contained media WELL even on the track (the fit vocabulary distinguishes
        # them — a product-UI shot contained on its well margin is not a logo).
        # Legacy quote-card compositions may predate assets-tagged facts but still
        # declare an unmistakable mark asset: the filename compatibility path applies
        # ONLY when no media-treatment fact resolved (mode fell to the cover default).
        edgecut_mark = edgecut and (mark_media
                                    or (media_mode == "cover" and bool(src)
                                        and _is_mark_asset(src)))
        contain = " cs-module-media--contain" if contained_media else ""
        # only the QUOTE card goes media-less (W7); a non-quote module with no
        # resolvable art keeps the srcless placeholder chip exactly as before.
        img_html = "" if (is_quote_card and not src) \
            else cr.render_image(doc, ctx, {"src": src, "alt": alt,
                                            "mediaRole": "card-media"})
        # PERSON attribution row (fid2 2026-07): a module carrying an avatar and/or an
        # authored name/role renders the avatar + name/role cluster (the testimonial
        # card anatomy's divider + person row) INSTEAD of the bare caption line — the
        # caption was the same "Name, Role" string. Modules without person facts keep
        # the caption device unchanged.
        person_html = ""
        if card.get("avatar") or card.get("name"):
            av = str(card.get("avatar") or "").strip()
            av_src = ""
            if av:
                av_src = av if av.startswith(("assets/", "http://", "https://", "data:")) \
                    else f"assets/{av}"
            avatar_img = (f'<img class="c-person-avatar" src="{cr.esc(av_src)}" '
                          f'alt="{cr.esc(card.get("name") or "")}">') if av_src else ""
            nm = (f'<span class="c-person-name">{cr.esc(card["name"])}</span>'
                  if card.get("name") else "")
            rl = (f'<span class="c-person-role">{cr.esc(card["role"])}</span>'
                  if card.get("role") else "")
            meta = f'<span class="c-person-meta">{nm}{rl}</span>' if (nm or rl) else ""
            person_html = f'<div class="c-person">{avatar_img}{meta}</div>'
        caption_html = "" if person_html else \
            cr.render_caption(doc, ctx, {"text": card.get("caption", "")})
        # CARD EYEBROW + HEADING ANATOMY (fid6 2026-07): a module whose authored copy
        # carries its OWN eyebrow (the per-card microlabel the grounding confirms)
        # renders the full register ladder — eyebrow (c-eyebrow, the section's eyebrow
        # register) then the card heading at the brand's declared card register
        # (card_head_level above) — instead of folding the heading into the tracked
        # caption register (which dropped the eyebrow and demoted the heading).
        # Modules without a card eyebrow keep the caption anatomy byte-identical
        # (the staggered-caption editorial card).
        anatomy = bool(str(card.get("eyebrow") or "").strip()) \
            or bool(pat_register and str(card.get("heading") or "").strip())
        card_eyebrow_html = card_head_html = ""
        if anatomy or (mark_media and str(card.get("heading") or "").strip()):
            # (fit: mark modules carry their heading at the card register too — the
            # feature-card ladder is mark → heading → body → link; eyebrow optional.)
            if str(card.get("eyebrow") or "").strip():
                card_eyebrow_html = cr.render_eyebrow(doc, ctx, {"text": card["eyebrow"]})
            head_txt = str(card.get("heading") or card.get("caption") or "").strip()
            if head_txt:
                card_head_html = cr.render_heading(
                    doc, ctx, {"text": head_txt, "level": card_head_level, "tag": "h3"})
            caption_html = ""
            anatomy = True
        body_html = cr.render_paragraph(doc, ctx, {"text": card.get("body", ""), "measure": "44ch"})
        link_html = cr.render_arrow_link(doc, ctx, {"label": card["link"]}) if card.get("link") else ""
        _headrow = False
        if edgecut_mark:
            # card-plate anatomy: the company mark sits at MARK height (device frame
            # geometry, same discipline as the logo strip), quote leads, the person
            # row / caption (name/role) closes the card.
            figure = (f'      <figure class="cs-module-media cs-module-media--mark">'
                      f'{img_html}</figure>\n')
            inner = (f'{figure}      {body_html}\n      '
                     f'{person_html or caption_html}\n      {link_html}')
        elif mark_media:
            # FEATURE-CARD anatomy (declared fit: mark on a contained grid): mark row
            # at device height, then the register ladder (eyebrow? → heading → body →
            # link). The mark is a glyph fact, never a media well.
            figure = (f'      <figure class="cs-module-media cs-module-media--mark">'
                      f'{img_html}</figure>\n')
            # HEADING-ROW mark placement (hubspot-v2 2026-07, brand card device
            # `slots.icon.placement: heading-row`): the source's feature card seats
            # its glyph BESIDE the heading (one row), not above it — the declared
            # fact folds mark + heading into a flex headrow at the icon slot's
            # measured size. Devices without the fact keep the stacked mark row.
            _icon_slot = _card_slots.get("icon") if isinstance(_card_slots, dict) else None
            chosen_anatomy = str(layout.get("_collectionAnatomy") or "")
            _headrow = chosen_anatomy != "icon-top" and isinstance(_icon_slot, dict) \
                and str(_icon_slot.get("placement") or "").strip() == "heading-row" \
                and bool(card_head_html) and not card_eyebrow_html
            if _headrow:
                _sz = str(_icon_slot.get("size") or "").strip()
                _sz_style = (f' style="--cs-headrow-mark: {cr.esc(_sz)}"'
                             if re.fullmatch(r"[\d.]+(?:rem|em|px)", _sz) else "")
                inner = (f'      <div class="cs-module-headrow"{_sz_style}>\n'
                         f'  {figure}        {card_head_html}\n      </div>\n'
                         f'      {body_html}\n      '
                         f'{person_html}\n      {link_html}')
            else:
                lead = (f'{card_eyebrow_html}\n      {card_head_html}' if anatomy
                        else caption_html)
                inner = (f'{figure}      {lead}\n      {body_html}\n      '
                         f'{person_html}\n      {link_html}')
        else:
            # a media-less quote card composes text-first — no empty frame (W7).
            figure = (f'      <figure class="cs-module-media{contain}" '
                      f'style="aspect-ratio: {cr.esc(aspect)};">{img_html}</figure>\n'
                      if img_html else "")
            lead = (f'{card_eyebrow_html}\n      {card_head_html}' if anatomy
                    else caption_html)
            inner = (f'{figure}      {lead}\n      {body_html}\n      '
                     f'{person_html}\n      {link_html}')
        plate = " cs-module--plate" if plated else ""
        anatomy_cls = " cs-module--anatomy" if anatomy else ""
        quote_cls = " cs-module--quote" if is_quote_card else ""
        family_anatomy = str(layout.get("_collectionAnatomy") or (
            "icon-inline" if _headrow else "icon-top" if mark_media else "text-stack"))
        anatomy_attr = (f' data-internal-anatomy="{cr.esc(family_anatomy)}"'
                        if layout.get("_componentFit") else "")
        span_attr = ""
        if fill:
            span_style = f' style="--cs-grid-span: {grid_span}'
            if content_measure > 0:
                span_style += f"; --cs-span-content-measure: {content_measure:g}ch"
            span_style += '"'
            span_attr = f' data-grid-span="{grid_span}"{span_style}'
        modules.append(
            f'    <article class="cs-module{plate}{anatomy_cls}{quote_cls}"'
            f'{anatomy_attr}{span_attr}>\n'
            f'{inner}\n    </article>')
    # SECTION HEADROW RAIL (fix1 2026-07 item-8, stamped from the pattern's
    # sanctioned `dotted-rule-rail` treatment): leading chip (the rail slot's own
    # declared mark, inventory-checked) or eyebrow pill, a rule spanning to the far
    # edge, and the section's authored cta as the trailing action (family resolved
    # from the rail's own style prose). Renders ABOVE the intro; the eyebrow leaves
    # the intro header (it rides the rail instead). No stamp ⇒ no rail, and the
    # intro renders byte-identically. Recipe-bound rails (fix2) render their
    # variant's measured facts via the shared helper.
    rail = layout.get("_headRail") if isinstance(layout.get("_headRail"), dict) else None
    rail_html = ""
    rail_in_column = False
    if rail is not None:
        eyebrow_html = cr.render_eyebrow(doc, ctx, {"text": copy.get("eyebrow")}) \
            if str(copy.get("eyebrow") or "").strip() else ""
        rail_html = _headrail_html(doc, ctx, rail, eyebrow_html=eyebrow_html,
                                   cta_label=str(copy.get("cta") or "").strip(),
                                   legacy_pill_wrap=False) + "\n  "
        rail_in_column = _rail_spans_column(rail)
    intro = ""
    if copy.get("heading"):
        # section register: the measured h2 tier when the brand's ladder declares one
        # (fid2 2026-07); a pattern-measured headingRegister (deviceGeometry, fix1)
        # outranks it; an authored intro subhead renders under it (testimonial
        # band's "Join customers who trust…" line was silently dropped before).
        header_html = cr.render_header(doc, ctx, {
            "eyebrow": copy.get("eyebrow") if rail is None else "",
            "heading": copy["heading"],
            "level": (str(_pat_geo.get("headingRegister") or "")
                      or section_heading_level(doc)),
            "accent": ctx.is_dark, "splitTwoLines": False})
        own = layout_copy_layer(layout, doc)
        sub = str((own or {}).get("subhead") or "").strip()
        sub_html = cr.render_paragraph(doc, ctx, {"text": sub}) if sub else ""
        # SPLIT INTRO (fix1 2026-07 item-8, stamped from half-width heading+body
        # slots): heading column LEFT, supporting paragraph RIGHT — the measured
        # two-column intro. Stamp-less sections keep the stacked intro.
        if layout.get("_introSplit") and sub_html:
            intro = (f'<div class="cs-modules-intro cs-intro-split">'
                     f'{header_html}{sub_html}</div>\n  ')
        else:
            intro = f'<div class="cs-modules-intro">{header_html}{sub_html}</div>\n  '
    # DECLARED module grid (sysfix 2026-07): a section whose composition carries
    # §4.6.5 grid columns (adapter: brand gridRules.columns → layout['_grid']) flows
    # one module per track instead of the staggered 7/5 registration spans — the
    # brand's own N-up card grid, not the harvested editorial stagger.
    # MODULE-COLUMN COUNT (fix7): a `knobs.columns` declaration (_moduleCols) is the
    # CONTENT track count and outranks the registration-grid count — 12 registration
    # columns are not 12 card tracks (the swiss bakeoff's 4 cards letter-squeezed
    # into 1-of-12 tracks was exactly that leak).
    cols_cls = ""
    module_cols = None
    try:
        if int(layout.get("_moduleCols") or 0) >= 2:
            module_cols = int(layout["_moduleCols"])
            cols_cls = " cs-modules--cols"
        elif int((layout.get("_grid") or {}).get("columns") or 0) >= 2:
            cols_cls = " cs-modules--cols"
    except (TypeError, ValueError):
        pass
    # bound `button` contract slots (B5 parity with the split/hero routes, P2): a
    # cards section closed by a real action slot renders it as one action row under
    # the modules — the old path silently DROPPED it (the testimonial band's closing
    # pill never rendered). Present only when the section binds one; centered rides
    # the section's resolved alignment stamp ([data-align] scaffold rule).
    action_frags = [r["html"] for r in rendered
                    if r.get("contract") == "button" and (r.get("html") or "").strip()]
    actions_html = ""
    if action_frags:
        actions_html = (f'\n  <div class="cs-modules-actions"{ag_attrs(doc, layout)}>'
                        + "".join(action_frags) + "</div>")
    track_cls = f"cs-modules{cols_cls}" + (" cs-modules--edgecut" if edgecut else "")
    # measured rail card box (deviceGeometry cardWidth/cardGap via _accGeometry):
    # the clipped-card rhythm at the capture viewport; clamp default otherwise.
    card_decls = []
    if module_cols:
        # the knob's CONTENT track count re-scopes the module grid only — the
        # section keeps its registration --grid-cols for placed devices (fix7).
        card_decls.append(f"--grid-cols: {module_cols}")
    if edgecut and _pat_geo.get("cardWidth"):
        card_decls.append(f"--cs-edgecut-card-w: {cr.esc(_pat_geo['cardWidth'])}")
    if edgecut and _pat_geo.get("cardGap"):
        card_decls.append(f"--cs-edgecut-gap: {cr.esc(_pat_geo['cardGap'])}")
    fit = layout.get("_componentFit") if isinstance(layout.get("_componentFit"), dict) else {}
    fit_attrs = ""
    if fit:
        fill = layout.get("_collectionFill") \
            if isinstance(layout.get("_collectionFill"), dict) else {}
        counterweight = fill.get("balancingCounterweight") \
            if isinstance(fill.get("balancingCounterweight"), dict) else {}
        fit_attrs = (
            f' data-component-fit="collection"'
            f' data-fit-min-item="{cr.esc(fit.get("minItemWidth"))}"'
            f' data-fit-max-heading-lines="{cr.esc(fit.get("maxHeadingLines"))}"'
            f' data-fit-max-body-lines="{cr.esc(fit.get("maxBodyLines"))}"'
            f' data-fit-anatomy="{cr.esc(fit.get("internalAnatomy"))}"'
            f' data-fit-columns="{cr.esc(fit.get("chosenColumns"))}"'
            f' data-fill-strategy="{cr.esc(fill.get("strategy") or "")}"'
            f' data-fill-counterweight="'
            f'{cr.esc(counterweight.get("role") or counterweight.get("contract") or "")}"')
    track_style = f' style="{"; ".join(card_decls)}"' if card_decls else ""
    track = f"""<div class="{track_cls}"{track_style}{fit_attrs}>
{chr(10).join(modules)}
  </div>"""
    if edgecut:
        # interaction remediation (2026-07, IC-CAR-01): the edge-cut scroller is a
        # keyboard-operable region — focusable, named after the section's own
        # heading (structural "Gallery" fallback, never invented brand copy), with
        # ArrowLeft/ArrowRight handled by the shared interaction script. A rail whose
        # treatment MEASURED visible chrome (`controls` on the _edgeCut stamp, fix1
        # item-8) renders the captured round prev/next pair (wired by the same rail
        # script); control-less rails (Remote) ship no invented chrome — pixel
        # fidelity, resolution argued in interaction-contracts.md §Resolution notes.
        rail_name = str(copy.get("heading") or "").strip() or "Gallery"
        controls = (layout.get("_edgeCut") or {}).get("controls") \
            if isinstance(layout.get("_edgeCut"), dict) else None
        ctl_html = ""
        if isinstance(controls, dict):
            chev_l = ('<svg viewBox="0 0 8 12" width="8" height="12" fill="none" '
                      'stroke="currentColor" stroke-width="1.5" aria-hidden="true">'
                      '<path d="M7 1L2 6l5 5"/></svg>')
            chev_r = ('<svg viewBox="0 0 8 12" width="8" height="12" fill="none" '
                      'stroke="currentColor" stroke-width="1.5" aria-hidden="true">'
                      '<path d="M1 1l5 5-5 5"/></svg>')
            ctl_html = (
                f'<button class="cs-edgecut-arrow cs-edgecut-arrow--prev" type="button" '
                f'data-railbtn="prev" aria-label="Previous">{chev_l}</button>'
                f'<button class="cs-edgecut-arrow cs-edgecut-arrow--next" type="button" '
                f'data-railbtn="next" aria-label="Next">{chev_r}</button>')
            # measured autoplay toggle (`controls.pause`, fix1 item-8): the source rail
            # autoplays and parks a small round pause under the track — static-faithful
            # chrome (present in the source's JS-off DOM), wired as a pressed-state
            # toggle by the rail script. Rails without the fact ship nothing.
            if controls.get("pause"):
                pause_glyph = ('<svg viewBox="0 0 10 12" width="10" height="12" '
                               'fill="currentColor" aria-hidden="true">'
                               '<rect x="1" y="1" width="3" height="10" rx="0.75"/>'
                               '<rect x="6" y="1" width="3" height="10" rx="0.75"/></svg>')
                ctl_html += (
                    f'<div class="cs-edgecut-pauserow"><button class="cs-edgecut-pause" '
                    f'type="button" data-railbtn="pause" aria-pressed="false" '
                    f'aria-label="Pause carousel">{pause_glyph}</button></div>')
        track = (f'<div class="cs-edgecut-wrap">'
                 f'<div class="cs-edgecut" tabindex="0" role="region" '
                 f'aria-roledescription="carousel" aria-label="{cr.esc(rail_name)}">'
                 f'{track}</div>{ctl_html}</div>') if ctl_html else \
                (f'<div class="cs-edgecut" tabindex="0" role="region" '
                 f'aria-roledescription="carousel" aria-label="{cr.esc(rail_name)}">'
                 f'{track}</div>')
    edge_cls = " cs-modules-sec--edgecut" if edgecut else ""
    # SIDE-RAIL CARD COUNTERWEIGHT (fix1 2026-07 item-7, stamped from the pattern's
    # `alignment {value: left, counterweight: cards}` declaration): the copy rail
    # (intro + action pair) holds the LEFT column and the module grid rides beside
    # it as the counterweight — the measured split morphology — instead of stacking
    # intro above the grid with the actions dropped below it. Stamp-less sections
    # return the stacked section byte-identically.
    # measured band padding (fix1 2026-07, same consumption as the split family).
    bp = layout.get("_bandPadding") if isinstance(layout.get("_bandPadding"), dict) else {}
    pad_decls = "".join(
        f" --c-section-pad-{k}: {cr.esc(bp[k])};" for k in ("top", "bottom") if bp.get(k))
    sec_style = f' style="{pad_decls.strip()}"' if pad_decls else ""
    if layout.get("_sideRail") and intro:
        # a COLUMN-spanning rail (recipe `span: column` — the kicker+rule anatomy
        # lives inside the copy column in the source) opens the copy column; a
        # content-spanning rail keeps the section-level row above the split.
        col_rail, sec_rail = (rail_html, "") if rail_in_column else ("", rail_html)
        return f"""<section class="cs-section cs-modules-sec cs-modules-sec--siderail{edge_cls}"{sec_style}>
  {sec_rail}<div class="cs-siderail">
    <div class="cs-siderail-copy">
      {col_rail}{intro.rstrip()}{actions_html}
    </div>
    {track}
  </div>
</section>"""
    return f"""<section class="cs-section cs-modules-sec{edge_cls}"{sec_style}>
  {rail_html}{intro}{track}{actions_html}
</section>"""


# ── archetype: cards / BENTO GRID (event-scaffolds 2026-07 — weighted panel mosaic) ──

def _cell_surface_vars(doc, role: str) -> str:
    """Inline surface re-scope for ONE bento cell painted with a sanctioned surface
    ROLE (tokens.surfaces — the brand's own surface grammar). Resolves bg/ink/accent
    THROUGH the generated --color-*/--surface-* token layer (never literals here);
    an unknown/undeclared role returns "" so the cell keeps the panel default —
    surfaces are law, not suggestions (AS-02)."""
    surfaces = ((doc or {}).get("tokens") or {}).get("surfaces") or {}
    spec = surfaces.get(role)
    if not isinstance(spec, dict) or not spec.get("bg"):
        return ""
    slug = re.sub(r"[^a-z0-9]+", "-", str(role).lower()).strip("-")
    decls = [f"--bn-bg: var(--surface-{slug})"]
    for key, var in (("textPrimary", "--bn-ink"), ("textAccent", "--bn-accent")):
        ref = spec.get(key)
        if ref:
            cslug = re.sub(r"[^a-z0-9]+", "-", str(ref).lower()).strip("-")
            decls.append(f"{var}: var(--color-{cslug})")
    # inverse/accent cells re-scope the shared ink/eyebrow vars too, so every catalog
    # primitive inside the cell (paragraph/caption/eyebrow/link) reads the cell's own
    # contrast pair — the same rescoping discipline the section surfaces use.
    decls += ["--c-ink: var(--bn-ink, inherit)",
              "--c-ink-muted: var(--bn-ink, inherit)",
              "--c-eyebrow-color: var(--bn-accent, var(--bn-ink, inherit))"]
    return "; ".join(decls)


def compose_bento_grid(doc, layout, ctx, rendered, style_ctx):
    """Assemble the BENTO GRID (event-scaffolds 2026-07) — new brand-agnostic scaffold
    #1: ONE weighted mosaic of panel cells on a 12-track grid, an ANCHOR cell plus
    supports (varying spans/row-depths), each cell the brand's own card anatomy
    (eyebrow → heading at the measured card register → body → optional arrow link /
    person row) on a sanctioned panel surface. MECHANICS are generic:
      - cell WEIGHTS (span 3–12 / rows 1–2) come exclusively from the composition's
        validated `_bento` stamp (pattern-fact-driven knobs, AS-44 discipline — the
        no-fact degrade is the uniform equal-span grid);
      - a cell may declare a sanctioned surface ROLE (tokens.surfaces) — resolved
        through the token layer by _cell_surface_vars, never invented (AS-02);
      - a `lead: true` cell renders its body at the lead register (the oversized
        statement cell — e.g. a quote anchor);
      - responsive collapse rides the brand's own measured column tier (the stamp's
        collapseAt px, emitted as a container query by layout_placement_css; the
        structural floor collapses everything to one column).
    Every visible value is brand tokens: panel surface/radius/padding from the card
    device chain, rhythm from --c-* vars, gaps from the measured grid gutter."""
    copy = copy_for(layout, doc)
    cards = copy.get("cards") or []
    stamp = layout.get("_bento") or {}
    cells_meta = stamp.get("cells") or []
    _card_slots = (cr.block_device(doc, "card") or {}).get("slots") or {}
    _head_slot = _card_slots.get("heading") if isinstance(_card_slots, dict) else None
    _reg = str((_head_slot or {}).get("register") or "").strip().lower() \
        if isinstance(_head_slot, dict) else ""
    card_head_level = _reg if _reg in ("h2", "h3", "h4", "h5", "h6") else "h3"
    # DE-FACTO LEAD STAMP (fix7, stage-B follow-up): when NO cell declares
    # `lead: true`, a FIRST card whose authored anatomy strictly supersets the
    # (identical) anatomy every sibling shares IS the mosaic's lead — stamp it so
    # SR-GRID-01 reads the renderer's own declaration instead of re-inferring the
    # same superset from rendered anatomy. Mirrors the auditor's inference exactly.
    def _card_anatomy(card: dict) -> frozenset:
        pieces = set()
        if str(card.get("eyebrow") or "").strip():
            pieces.add("eyebrow")
        if str(card.get("heading") or ("" if card.get("name") else card.get("caption"))
               or "").strip():
            pieces.add("heading")
        if card.get("asset"):
            pieces.add("media")
        if str(card.get("body") or "").strip():
            pieces.add("body")
        if card.get("name"):
            pieces.add("person")
        if card.get("link"):
            pieces.add("link")
        return frozenset(pieces)

    defacto_lead = -1
    if cards and not any(isinstance(m, dict) and m.get("lead") for m in cells_meta) \
            and len(cards) >= 4:
        rest_sets = {_card_anatomy(c) for c in cards[1:]}
        if len(rest_sets) == 1 and _card_anatomy(cards[0]) > next(iter(rest_sets)):
            defacto_lead = 0
    cells = []
    for i, card in enumerate(cards):
        meta = cells_meta[i] if i < len(cells_meta) and isinstance(cells_meta[i], dict) else {}
        if i == defacto_lead:
            meta = {**meta, "lead": True}
        decls = []
        span = meta.get("span")
        start = meta.get("start")
        if isinstance(span, (int, float)) and isinstance(start, (int, float)):
            # explicit placement (e.g. ONE centered feature cell): full track ref.
            decls.append(f"--bn-col: {max(1, min(12, int(start)))} / span "
                         f"{max(3, min(12, int(span)))}")
        elif isinstance(span, (int, float)):
            decls.append(f"--bn-span: {max(3, min(12, int(span)))}")
        rows_n = meta.get("rows")
        if isinstance(rows_n, (int, float)) and int(rows_n) > 1:
            decls.append(f"--bn-rows: {min(2, int(rows_n))}")
        surface_decls = _cell_surface_vars(doc, str(meta.get("surface") or ""))
        if surface_decls:
            decls.append(surface_decls)
        style = f' style="{"; ".join(decls)}"' if decls else ""
        surf_cls = " cs-bento-cell--surface" if surface_decls else ""
        lead_cls = " cs-bento-cell--lead" if meta.get("lead") else ""
        eyebrow_html = cr.render_eyebrow(doc, ctx, {"text": card["eyebrow"]}) \
            if str(card.get("eyebrow") or "").strip() else ""
        # a person-attributed cell (quote anatomy) must not re-render the caption's
        # name/role fold as its heading — the person row below carries it.
        head_txt = str(card.get("heading")
                       or ("" if card.get("name") else card.get("caption"))
                       or "").strip()
        head_html = cr.render_heading(
            doc, ctx, {"text": head_txt, "level": card_head_level, "tag": "h3"}) \
            if head_txt else ""
        # optional MEDIA WELL (the anchor-cell anatomy): a cell binding a captured
        # asset leads with it — full-bleed to the cell's top edges via the same
        # negative-margin well the card plates use; AS-34: src must be authored
        # (inventory-validated upstream), never a composer default.
        media_html = ""
        raw = card.get("asset")
        alt = card.get("alt")
        if isinstance(raw, dict):
            alt = alt or raw.get("alt")
            raw = raw.get("src")
        if raw:
            src = raw if str(raw).startswith(("assets/", "http://", "https://", "data:")) \
                else f"assets/{raw}"
            aspect = card.get("aspect") or "16 / 10"
            media_html = (f'<figure class="cs-bento-media" '
                          f'style="aspect-ratio: {cr.esc(str(aspect))};">'
                          + cr.render_image(doc, ctx, {"src": src, "alt": alt or head_txt})
                          + "</figure>")
        body_html = cr.render_paragraph(doc, ctx, {"text": card.get("body", "")}) \
            if str(card.get("body") or "").strip() else ""
        link_html = cr.render_arrow_link(doc, ctx, {"label": card["link"]}) \
            if card.get("link") else ""
        # person row (same anatomy as the card plates — avatar optional, name/role
        # in the shared c-person register): a quote/host cell attributes itself.
        person_html = ""
        if card.get("name"):
            av = str(card.get("avatar") or "").strip()
            avatar_img = ""
            if av:
                av_src = av if av.startswith(("assets/", "http://", "https://", "data:")) \
                    else f"assets/{av}"
                avatar_img = (f'<img class="c-person-avatar" src="{cr.esc(av_src)}" '
                              f'alt="{cr.esc(card.get("name") or "")}">')
            nm = f'<span class="c-person-name">{cr.esc(card["name"])}</span>'
            rl = (f'<span class="c-person-role">{cr.esc(card["role"])}</span>'
                  if card.get("role") else "")
            person_html = (f'<div class="c-person">{avatar_img}<span class="c-person-meta">'
                           f'{nm}{rl}</span></div>')
        inner = "\n      ".join(x for x in (media_html, eyebrow_html, head_html,
                                            body_html, person_html, link_html) if x)
        cells.append(f'    <article class="cs-bento-cell{surf_cls}{lead_cls}"{style}>\n'
                     f'      {inner}\n    </article>')
    intro = ""
    if copy.get("heading"):
        header_html = cr.render_header(doc, ctx, {
            "eyebrow": copy.get("eyebrow"), "heading": copy["heading"],
            "level": section_heading_level(doc),
            "accent": ctx.is_dark, "splitTwoLines": False})
        own = layout_copy_layer(layout, doc)
        sub = str((own or {}).get("subhead") or "").strip()
        sub_html = cr.render_paragraph(doc, ctx, {"text": sub}) if sub else ""
        intro = f'<div class="cs-modules-intro">{header_html}{sub_html}</div>\n  '
    # bound `button` contract slots close the section as one action row (B5 parity
    # with the module-grid composer) — present only when the composition binds one.
    action_frags = [r["html"] for r in rendered
                    if r.get("contract") == "button" and (r.get("html") or "").strip()]
    actions_html = (f'\n  <div class="cs-modules-actions"{ag_attrs(doc, layout)}>'
                    + "".join(action_frags)
                    + "</div>") if action_frags else ""
    return f"""<section class="cs-section cs-bento-sec">
  {intro}<div class="cs-bento">
{chr(10).join(cells)}
  </div>{actions_html}
</section>"""


# ── archetype: cards / PRICING TIERS (event-scaffolds 2026-07 — emphasized tier row) ──

def compose_pricing_tiers(doc, layout, ctx, rendered, style_ctx):
    """Assemble PRICING TIERS (event-scaffolds 2026-07) — new brand-agnostic scaffold
    #2: N peer tier panels on one equal-track row (collapsing per the stamped tier),
    each tier = name (caption register) → price (display-family figure) + unit meta →
    tagline → hairline-ruled feature list → one action from the measured button
    family. ONE tier may be EMPHASIZED (the stamp's `emphasize` index) — emphasis is
    a sanctioned SURFACE relationship, never an invented badge (AS-44/AS-02):
      - a brand declaring an inverse/accent surface role in its grammar paints the
        emphasized tier's HEAD BAND with it (`emphasisSurface` in the stamp — role
        resolved through the token layer, same discipline as the bento cells);
      - brands without such a role degrade to the measured input/hairline border ring.
    Panel anatomy rides the brand's card device chain (panel surface + card radius +
    measured padding); prices ride the heading font stack + a contained structural
    clamp (register bound, not a brand magnitude)."""
    copy = copy_for(layout, doc)
    tiers = copy.get("tiers") or []
    stamp = layout.get("_tiers") or {}
    emph_i = stamp.get("emphasize")
    emph_surface_decls = _cell_surface_vars(doc, str(stamp.get("emphasisSurface") or ""))
    cols = []
    for i, tier in enumerate(tiers):
        emph = isinstance(emph_i, int) and i == emph_i
        name_html = (f'<p class="c-caption cs-tier-name">{cr.esc(tier.get("name") or "")}'
                     f'</p>') if str(tier.get("name") or "").strip() else ""
        price = str(tier.get("price") or "").strip()
        unit = str(tier.get("priceMeta") or "").strip()
        unit_html = f'<span class="cs-tier-unit">{cr.esc(unit)}</span>' if unit else ""
        price_html = (f'<div class="cs-tier-price">{cr.esc(price)}{unit_html}</div>'
                      if price else "")
        tag = str(tier.get("tagline") or "").strip()
        tag_html = f'<p class="cs-tier-tagline">{cr.esc(tag)}</p>' if tag else ""
        feats = [str(f).strip() for f in (tier.get("features") or []) if str(f).strip()]
        feats_html = ("\n        ".join(f'<li>{cr.esc(f)}</li>' for f in feats))
        list_html = (f'\n      <ul class="cs-tier-list">\n        {feats_html}\n      </ul>'
                     if feats else "")
        cta = str(tier.get("cta") or "").strip()
        cta_html = ""
        if cta:
            cta_html = "\n      " + cr.render_button(doc, ctx, {
                "label": cta, "family": tier.get("ctaFamily") or None})
        head_style = (f' style="{emph_surface_decls}"'
                      if emph and emph_surface_decls else "")
        head_cls = "cs-tier-head" + (
            " cs-tier-head--surface" if emph and emph_surface_decls else "")
        # ONE emphasis device, once: the surface head band when the brand's grammar
        # sanctions the role; the strong border ring ONLY as the roleless degrade.
        emph_cls = " cs-tier--emph" if emph and not emph_surface_decls else ""
        cols.append(f"""    <article class="cs-tier{emph_cls}">
      <header class="{head_cls}"{head_style}>
        {name_html}
        {price_html}
        {tag_html}
      </header>{list_html}{cta_html}
    </article>""")
    intro = ""
    if copy.get("heading"):
        header_html = cr.render_header(doc, ctx, {
            "eyebrow": copy.get("eyebrow"), "heading": copy["heading"],
            "level": section_heading_level(doc),
            "accent": ctx.is_dark, "splitTwoLines": False})
        own = layout_copy_layer(layout, doc)
        sub = str((own or {}).get("subhead") or "").strip()
        sub_html = cr.render_paragraph(doc, ctx, {"text": sub}) if sub else ""
        intro = f'<div class="cs-modules-intro">{header_html}{sub_html}</div>\n  '
    note = str(copy["note"]).strip()
    note_html = (f'\n  <p class="c-caption cs-tiers-note">{cr.esc(note)}</p>'
                 if note else "")
    return f"""<section class="cs-section cs-tiers-sec">
  {intro}<div class="cs-tiers">
{chr(10).join(cols)}
  </div>{note_html}
</section>"""


def compose_cards(doc, layout, ctx, rendered, style_ctx):
    """`cards` archetype dispatcher (event-scaffolds 2026-07): the BENTO mosaic and
    PRICING-TIER row are stamp-gated presentations of the cards family — a section
    stamped `_bento`/`_tiers` (validated composition knobs) routes to its scaffold;
    everything else renders the staggered/N-up module grid byte-identically."""
    if layout.get("_bento") is not None:
        return compose_bento_grid(doc, layout, ctx, rendered, style_ctx)
    if layout.get("_tiers") is not None:
        return compose_pricing_tiers(doc, layout, ctx, rendered, style_ctx)
    return compose_features_cards(doc, layout, ctx, rendered, style_ctx)


# ── archetype: media-split / evidence-qualified editorial interlock ───────────────

def compose_media_split(doc, layout, ctx, rendered, style_ctx):
    """Ordinary two-column media split: the complete copy stack is one child and
    landscape media is the other.  This is the safe degradation target for advanced
    editorial devices whose content-shape preconditions are not met."""
    copy = copy_for(layout, doc)
    lc = layout_copy_layer(layout, doc)
    raw = copy.get("asset")
    src = raw if str(raw or "").startswith("assets/") \
        else (f"assets/{raw}" if raw else _composer_art(doc, layout, "hero"))
    brand_name = (doc.get("brand") or {}).get("name") or "Brand"
    eyebrow = copy.get("caption") or lc.get("eyebrow") or ""
    title = copy.get("statement") or lc.get("title") or lc.get("heading") or ""
    support = lc.get("support") or copy.get("support") or ""
    cta = lc.get("cta") or copy.get("cta") or ""
    eyebrow_html = (f'<div class="cs-eyebrow-wrap"><p class="c-caption">'
                    f'{cr.esc(eyebrow)}</p></div>') if eyebrow else ""
    heading_html = cr.render_heading(
        doc, ctx, {"text": title,
                   "level": copy.get("headingLevel") or section_heading_level(doc),
                   "tag": "h2"}) if title else ""
    support_html = cr.render_paragraph(
        doc, ctx, {"text": support, "measure": "44ch"}) if support else ""
    cta_html = cr.render_arrow_link(
        doc, ctx, {"label": cta, "accent": False}) if cta else ""
    image_html = cr.render_image(doc, ctx, {
        "src": src, "alt": copy.get("alt") or f"{brand_name} media",
        "aspect": copy.get("mediaAspectCss"), "mediaRole": "split-media"})
    return f"""<section class="cs-section cs-media-split-sec">
  <div class="cs-media-split">
    <div class="cs-media-split-copy">
      {eyebrow_html}
      {heading_html}
      {support_html}
      {cta_html}
    </div>
    <figure class="cs-media-split-media">{image_html}</figure>
  </div>
</section>"""


def interlock_preconditions(copy: dict, layout_copy: dict) -> bool:
    """Advanced-device contract: explicit evidence, landscape media, the canonical
    caption+statement+media shape, and no unsupported support/action foot cluster."""
    evidence = copy.get("interlockEvidence") or copy.get("deviceEvidence")
    aspect = str(copy.get("mediaAspect") or copy.get("mediaAspectCss") or "").lower()
    landscape = (
        copy.get("mediaOrientation") == "landscape"
        or "landscape" in aspect
        or aspect in ("3 / 2", "4 / 3", "16 / 9")
    )
    shape = bool(copy.get("caption") and copy.get("statement") and copy.get("asset"))
    unsupported_foot = bool(layout_copy.get("support") or layout_copy.get("cta"))
    return bool(evidence and landscape and shape and not unsupported_foot)

def compose_editorial_interlock(doc, layout, ctx, rendered, style_ctx):
    """Assemble an evidence-qualified editorial statement + landscape inset.
    Content that lacks the explicit evidence/canonical shape contract degrades to
    ``compose_media_split``. The retained device uses a simple registered grid."""
    copy = copy_for(layout, doc)
    lc = layout_copy_layer(layout, doc)
    if not interlock_preconditions(copy, lc):
        return compose_media_split(doc, layout, ctx, rendered, style_ctx)
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
    return f"""<section class="cs-section cs-interlock-sec">
  <div class="cs-interlock">
    <figure class="cs-interlock-media">{img_html}</figure>
    <div class="cs-interlock-copy">
      <p class="c-caption cs-interlock-caption">{cap_lines}</p>
      {statement_html}
    </div>
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
    testimonial = layout.get("_testimonial") \
        if isinstance(layout.get("_testimonial"), dict) else None
    if testimonial is not None:
        quote_text = str(testimonial.get("quote") or "").strip()
        attribution = testimonial.get("attribution") \
            if isinstance(testimonial.get("attribution"), dict) else {}
        name = str(attribution.get("name") or "").strip()
        role = str(attribution.get("role") or "").strip()
        quote_html = cr.render_paragraph(
            doc, ctx, {"text": quote_text,
                       "measure": f'{int(testimonial.get("preferredMeasureCh") or 58)}ch'})
        person = (
            f'<div class="c-person"><span class="c-person-meta">'
            f'<span class="c-person-name">{cr.esc(name)}</span>'
            f'<span class="c-person-role">{cr.esc(role)}</span>'
            f'</span></div>')
        asset = str(testimonial.get("asset") or "").strip()
        media = ""
        if asset:
            src = asset if asset.startswith(("assets/", "http://", "https://", "data:")) \
                else f"assets/{asset}"
            image = cr.render_image(doc, ctx, {
                "src": src,
                "alt": f"{name}, {role}".strip(", "),
                "mediaRole": "card-media",
            })
            media = f'<figure class="cs-testimonial-media">{image}</figure>'
        anatomy = str(testimonial.get("internalAnatomy") or "quote-card")
        accent = (
            '<span class="cs-testimonial-mark" data-accent-device="testimonial-quote-mark" '
            'aria-hidden="true">“</span>'
            if testimonial.get("accentLicensed") else "")
        asset_state = "bound" if asset else "requested"
        return f"""<section class="cs-section cs-testimonial-sec" data-testimonial-intent="true">
  <div class="cs-flow">
    <article class="cs-testimonial cs-testimonial--{cr.esc(anatomy)}"
      data-component-contract="testimonial" data-testimonial-anatomy="{cr.esc(anatomy)}"
      data-testimonial-asset="{asset_state}" data-testimonial-max-empty="{cr.esc(testimonial.get("maxEmptySpaceRatio") or 0.68)}">
      {media}
      <div class="cs-testimonial-copy">
        {accent}<blockquote class="cs-testimonial-quote">{quote_html}</blockquote>
        {person}
      </div>
    </article>
  </div>
</section>"""
    parts: list[str | None] = []
    # SECTION HEADROW RAIL + SPLIT INTRO (fix1 2026-07 item-8; same stamps as the
    # cards composer): a flow section whose pattern declares the dotted-rule-rail
    # treatment folds its eyebrow into the rail row (leading pill — rule — trailing
    # authored cta), and half-width heading+body slots pair into one two-column
    # row. Consumed fragments leave the ordinary flow; stamp-less sections render
    # byte-identically (no rail, classic stacked flow).
    rail = layout.get("_headRail") if isinstance(layout.get("_headRail"), dict) else None
    consumed: set[int] = set()
    if rail is not None or layout.get("_introSplit"):
        flow_copy = copy_for(layout, doc)
        by_contract: dict[str, tuple[int, str]] = {}
        for idx, r in enumerate(rendered):
            frag = r.get("html") or ""
            if not frag.strip() or "unresolved slot" in frag:
                continue
            c = (r.get("contract") or "").lower()
            if c not in by_contract:
                by_contract[c] = (idx, frag)
        if rail is not None:
            # the flow's already-rendered eyebrow fragment rides the rail (and
            # leaves the ordinary flow); recipe variants restyle it via the
            # shared helper (fix2), prose-vocabulary rails keep fix1 behavior.
            # The eyebrow is consumed only when the kicker actually carries a
            # LABEL (pill/badge variants, or the chip-less legacy rail) — an
            # icon-only chip leaves the flow's eyebrow where it stands.
            inv = set(doc.get(ASSET_INVENTORY_KEY) or []) if isinstance(doc, dict) else set()
            has_chip = any(Path(str(a)).name in inv for a in (rail.get("assets") or []))
            kick_shape = str(((rail.get("variant") or {}).get("kicker") or {})
                             .get("shape") or "").lower() \
                if isinstance(rail.get("variant"), dict) else ""
            eyebrow_html = ""
            if "eyebrow" in by_contract and \
                    (kick_shape in ("pill", "badge") or not has_chip):
                eb_idx, eyebrow_html = by_contract["eyebrow"]
                consumed.add(eb_idx)
            parts.append("    " + _headrail_html(
                doc, ctx, rail, eyebrow_html=eyebrow_html,
                cta_label=str(flow_copy.get("cta") or "").strip(),
                legacy_pill_wrap=True))
        if layout.get("_introSplit") and "heading" in by_contract \
                and "paragraph" in by_contract:
            h_idx, h_frag = by_contract["heading"]
            p_idx, p_frag = by_contract["paragraph"]
            consumed |= {h_idx, p_idx}
            parts.append(f'    <div class="cs-intro-split">{h_frag}{p_frag}</div>')
    # PER-GROUP strips (sysfix 2026-07): logo entries carry the AUTHORED source-slot
    # name as `group` — each declared slot group (e.g. badges vs ratings) renders as
    # its OWN horizontal row at its first entry's position, in declared slot order.
    # The old single-strip fold merged every mark on the page into one row.
    strip_groups: dict[str, dict] = {}     # group -> {"pos": int, "items": [html]}
    # STAT BAND (W4, stress-playbook 2026-07): stat-contract entries group into ONE
    # horizontal band per authored slot (same per-group discipline as logo strips) —
    # metrics read as a row of value/label columns, not a vertical caption stack.
    stat_groups: dict[str, dict] = {}      # group -> {"pos": int, "items": [html]}
    logo_text_items = 0
    for r_idx, r in enumerate(rendered):
        if r_idx in consumed:              # folded into the headrail / split intro
            continue
        frag = r.get("html") or ""
        if not frag.strip() or "unresolved slot" in frag:
            continue
        role = (r.get("role") or "").lower()
        if r.get("slot") == "logo-strip" and r.get("contract") == "logo":
            group = str(r.get("group") or "logo-strip")
            g = strip_groups.get(group)
            if g is None:
                g = strip_groups[group] = {"pos": len(parts), "items": []}
                parts.append(None)  # placeholder — replaced by this group's strip below
            g["items"].append(f'      <div class="cs-logo-strip-item">{frag}</div>')
            continue
        if r.get("contract") in ("stat", "metric"):
            group = str(r.get("group") or r.get("slot") or "stats")
            g = stat_groups.get(group)
            if g is None:
                g = stat_groups[group] = {"pos": len(parts), "items": []}
                parts.append(None)  # placeholder — replaced by this group's band below
            g["items"].append(f'      <div class="cs-stat-band-item">{frag}</div>')
            continue
        if role == "logo item":
            logo_text_items += 1
        is_media = ("image" == r.get("contract")) or any(
            k in role for k in ("photo", "media", "image"))
        # HUG-COLLAPSE fix (fid6 2026-07): the prose measure (62ch) belongs to
        # PARAGRAPH slots only. It used to clamp EVERY flow item — computed at the
        # wrapper's inherited body size, so a centered section's h2 wrapped inside a
        # ~500px box and the whole stack read collapsed. Headings/eyebrows/actions
        # now hug their own content inside the full-width flow container ("hug"
        # applies to slots, never to the section container).
        if is_media:
            cls = "cs-flow-media"
        elif r.get("contract") == "paragraph":
            cls = "cs-flow-item cs-flow-item--prose"
        else:
            cls = "cs-flow-item"
        # SEMANTIC ROW STAMP (AS-48): the item's content relationship, from its
        # CONTRACT — the relational-ladder CSS keys pair seams (eyebrow->heading,
        # heading->body, body->action) on these, so a ladder-bearing brand's flow
        # renders per-pair rhythm instead of one flattened uniform gap. Unmapped
        # contracts (logo/image/form/caption rows) carry no stamp and ride the
        # block-to-block row rhythm. A HEADER block stamps as the heading row
        # (fix7, pass-3 follow-up 6): its lead-in sibling paragraph then rides the
        # heading→body rung instead of the 40px block stride the audit flagged.
        row = "media" if is_media else {
            "eyebrow": "eyebrow", "heading": "heading", "header": "heading",
            "paragraph": "body", "button": "action"}.get(r.get("contract") or "")
        row_attr = f' data-row="{row}"' if row else ""
        parts.append(f'    <div class="{cls}"{row_attr}>{frag}</div>')
    # MARQUEE DEVICE (P2, replica-gate punch list): a strip group whose reused pattern
    # declares the sanctioned `marquee` treatment renders the seam-correct track — TWO
    # IDENTICAL halves inside one max-content flex track, looped by a translateX(-50%)
    # keyframe, so the wrap point is mathematically invisible (AS-42). The px/s-constant
    # duration is set by the page script from the measured half width; the inline
    # fallback derives from the item count (~2s of travel per mark) so a JS-off render
    # still animates at approximately the same speed. Brands whose pattern declares no
    # marquee keep the static wrapping row (the degrade, byte-identical).
    mq = layout.get("_marquee") if isinstance(layout.get("_marquee"), dict) else None
    for group, g in strip_groups.items():
        is_marquee = bool(g["items"]) and mq is not None and (
            str(mq.get("target") or "") in (group, "") or len(strip_groups) == 1)
        if is_marquee:
            half = "\n".join(g["items"])
            # MEASURED period first (fid2 2026-07): the stamped durationS is the
            # source's own JS-computed loop period (serialized in the saved DOM);
            # `data-marquee-measured` tells the page script to leave it alone. The
            # item-count approximation stays the degrade for brands without the fact.
            measured_s = mq.get("durationS") if mq else None
            if measured_s:
                dur = f"{measured_s:g}"
                fixed_attr = ' data-marquee-measured="1"'
            else:
                dur = f"{max(6, 2 * len(g['items']))}"
                fixed_attr = ""
            parts[g["pos"]] = (
                f'    <div class="cs-logo-strip cs-marquee"{fixed_attr} '
                f'style="--cs-marquee-duration: {dur}s">\n'
                f'      <div class="cs-marquee-track">\n'
                f'      <div class="cs-marquee-half">\n{half}\n      </div>\n'
                f'      <div class="cs-marquee-half" aria-hidden="true">\n{half}\n'
                f'      </div>\n      </div>\n    </div>')
        else:
            # MEASURED ROW SCALE (fid6 2026-07; fid7: per-group map + measured gap):
            # a strip whose pattern recorded a container-relative row fraction for
            # THIS slot group (`_logoScale[group]`, e.g. a partner-proof row spanning
            # ~half the content width, or an awards strip's badge/rating rows at
            # their measured spans) renders the row at that scale: the row box is
            # `fraction * 100%` wide, each mark's flex weight is its real asset
            # aspect ratio (equal heights, row fills the measured span), and the
            # inter-mark gap rides the measured length when recorded. Requires
            # aspect coverage for EVERY item (evidence first); otherwise the
            # structural strip below is the degrade.
            scales = layout.get("_logoScale") if isinstance(layout.get("_logoScale"), dict) else {}
            scale = scales.get(group) if isinstance(scales.get(group), dict) else None
            # MEASURED ITEM BOX first (fix2 2026-07, mediaScale.item): the strip's
            # uniform mark frame measured on the capture — fixed contain-fit boxes
            # + the measured box gap reproduce the source row exactly (the
            # fraction-weighted route distributes widths, which UNDERSIZES marks
            # when the source draws uniform frames wider than the ink).
            item_box = (scale or {}).get("item") if isinstance((scale or {}).get("item"), dict) else {}
            if item_box.get("width") and item_box.get("height") and g["items"]:
                gap_var = (f' --cs-strip-gap: {scale["gap"]};'
                           if scale.get("gap") else "")
                parts[g["pos"]] = (
                    f'    <div class="cs-logo-strip cs-logo-strip--itembox" '
                    f'style="--cs-strip-item-w: {cr.esc(item_box["width"])}; '
                    f'--cs-strip-item-h: {cr.esc(item_box["height"])};{gap_var} '
                    f'flex-wrap: wrap; max-width: 100%;">\n'
                    + "\n".join(g["items"]) + "\n    </div>")
                continue
            if scale and scale.get("fraction") and g["items"]:
                aspects_map = scale.get("aspects") if isinstance(scale.get("aspects"), dict) else {}
                weights = []
                for item_html in g["items"]:
                    m = re.search(r'src="assets/([^"]+)"', item_html)
                    a = aspects_map.get(Path(m.group(1)).name) if m else None
                    weights.append(a)
                if weights and all(w for w in weights):
                    scaled = [
                        re.sub(r'class="cs-logo-strip-item"',
                               f'class="cs-logo-strip-item" style="flex: {w:g} 1 0"',
                               item_html, count=1)
                        for w, item_html in zip(weights, g["items"])]
                    gap_var = (f' --cs-strip-gap: {scale["gap"]};'
                               if scale.get("gap") else "")
                    parts[g["pos"]] = (
                        f'    <div class="cs-logo-strip cs-logo-strip--scaled" '
                        f'style="--cs-strip-fraction: {float(scale["fraction"]):g};{gap_var}">\n'
                        + "\n".join(scaled) + "\n    </div>")
                    continue
            # BADGE TIER (fid2 2026-07): a strip whose marks read as AWARD BADGES
            # (badge/award/seal filename families) renders at the brand's measured
            # badge tier (spacing token `badge-tier`) when one is authored — award
            # plaques are a taller mark class than wordmark logos. Brands without
            # the token (or non-badge strips) keep the structural logo height.
            badge_style = ""
            spacing = ((doc.get("tokens") or {}).get("spacing")) or {}
            if isinstance(spacing.get("badge-tier"), dict) and g["items"] and all(
                    re.search(r"(badge|award|seal|leader|top-?\d+)", i, re.I)
                    for i in g["items"]):
                badge_style = ' style="--c-logo-strip-h: var(--space-badge-tier)"'
            parts[g["pos"]] = (f'    <div class="cs-logo-strip"{badge_style}>\n'
                               + "\n".join(g["items"]) + "\n    </div>")
    # stat bands land at their first entry's position; the column count is the
    # authored item count (CSS collapses the grid on narrow frames).
    for group, g in stat_groups.items():
        if not g["items"]:
            continue
        parts[g["pos"]] = (
            f'    <div class="cs-stat-band" style="--cs-stat-cols: {len(g["items"])}">\n'
            + "\n".join(g["items"]) + "\n    </div>")
    any_strip_items = any(g["items"] for g in strip_groups.values())
    body = "\n".join(p for p in parts if p is not None) \
        or '    <!-- generic-flow: no renderable slots -->'
    device_attr = ""
    if layout.get("_logoWall"):
        mode = "image" if any_strip_items else ("text" if logo_text_items else "empty")
        device_attr = f' data-logo-device="{mode}"'
    # measured band padding (fix1 2026-07, same consumption as the split family):
    # the pattern's own vertical padding overrides the site rhythm for THIS band.
    bp = layout.get("_bandPadding") if isinstance(layout.get("_bandPadding"), dict) else {}
    pad_decls = "".join(
        f" --c-section-pad-{k}: {cr.esc(bp[k])};" for k in ("top", "bottom") if bp.get(k))
    sec_style = f' style="{pad_decls.strip()}"' if pad_decls else ""
    return f"""<section class="cs-section cs-flow-sec"{device_attr}{sec_style}>
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
    hairline device, never a card/box (no-cards-on-cream, no-shadows).

    `_faq` stamp (event-scaffolds 2026-07, composition knob — AS-40 hardening): a
    section stamped {exclusive: true} groups its rows into ONE platform-enforced
    exclusivity set (<details name=…> — one open member at a time, zero JS); an
    `open` index composes that member expanded (evidence-driven open state — the
    degrade stays all-closed). STATE GRAMMAR knobs name the brand's OWN token roles
    (the accordion inset-emphasis vocabulary): `activeSurface` inverts the open row
    to a sanctioned surface role, `hoverWash` tints idle hovered rows with a
    sanctioned color role — both resolved through the token layer here (never
    literals) and shipped only with the stamp (SCAFFOLD_FAQ_STATE_CSS gate).
    Un-stamped layouts render byte-identically, and the heading register rides the
    brand's measured section tier when the ladder declares one (the same
    section_heading_level law every other scaffold follows)."""
    copy = copy_for(layout, doc)
    stamp = layout.get("_faq") if isinstance(layout.get("_faq"), dict) else None
    eyebrow_html = cr.render_eyebrow(doc, ctx, {"text": copy["eyebrow"]})
    heading_html = cr.render_heading(doc, ctx, {
        "text": copy["heading"],
        "level": section_heading_level(doc) if stamp is not None else "display",
        "accent": False})
    uid = re.sub(r"[^a-z0-9]+", "-", str(layout.get("id") or "faq").lower()).strip("-")
    # single-open is the family DEFAULT (interaction remediation 2026-07, IC-ACC-01):
    # every FAQ group shares a <details name> so the platform enforces one open
    # member — un-stamped layouts included (the _faq_stamp default is exclusive:
    # true; the scaffold's own default now matches it). An AUTHORED multi-open
    # override (knobs.faq.exclusive: false) drops the name and declares itself via
    # data-acc-multi="authored" so the interaction audit can tell a deliberate
    # multi-open family from an accidentally ungrouped one.
    multi_authored = stamp is not None and stamp.get("exclusive") is False
    name_attr = "" if multi_authored else f' name="faq-{cr.esc(uid)}"'
    multi_attr = ' data-acc-multi="authored"' if multi_authored else ""
    open_i = (stamp or {}).get("open")
    # state-grammar roles → section-scoped vars (token-layer references, AS-02):
    # an unknown/undeclared role resolves to nothing and the row keeps its degrade.
    state_decls = []
    surfaces = ((doc or {}).get("tokens") or {}).get("surfaces") or {}
    active_role = str((stamp or {}).get("activeSurface") or "").strip()
    spec = surfaces.get(active_role)
    if isinstance(spec, dict) and spec.get("bg"):
        slug = re.sub(r"[^a-z0-9]+", "-", active_role.lower()).strip("-")
        state_decls.append(f"--faq-active-bg: var(--surface-{slug})")
        if spec.get("textPrimary"):
            ink = re.sub(r"[^a-z0-9]+", "-", str(spec["textPrimary"]).lower()).strip("-")
            state_decls.append(f"--faq-active-ink: var(--color-{ink})")
    wash_role = str((stamp or {}).get("hoverWash") or "").strip()
    if wash_role and tokens_css.color_value(doc, wash_role):
        wslug = re.sub(r"[^a-z0-9]+", "-", wash_role.lower()).strip("-")
        state_decls.append(f"--faq-hover-bg: var(--color-{wslug})")
    stated_cls = " cs-faq--stated" if state_decls else ""
    state_style = f' style="{"; ".join(state_decls)}"' if state_decls else ""
    items = "".join(
        f'<details class="c-faq-item"{name_attr}'
        + (" open" if isinstance(open_i, int) and i == open_i else "")
        + f'><summary class="c-faq-q">{cr.esc(q)}'
        f'<span class="c-faq-icon" aria-hidden="true">+</span></summary>'
        f'<p class="c-faq-a">{cr.esc(a)}</p></details>'
        for i, (q, a) in enumerate(copy.get("items", [])))
    # OPTIONAL anatomy (the agenda shape, event-scaffolds 2026-07): an authored
    # intro paragraph above the rows and/or one typographic closing action —
    # absent keys elide, so every bare FAQ renders byte-identically.
    intro_html = ('\n    ' + cr.render_paragraph(doc, ctx, {"text": copy["intro"]})
                  if str(copy["intro"]).strip() else "")
    cta_html = ('\n    ' + cr.render_arrow_link(doc, ctx, {"label": copy["cta"],
                                                           "accent": False})
                if str(copy["cta"]).strip() else "")
    return f"""<section class="cs-section cs-faq-sec">
  <div class="cs-faq{stated_cls}"{state_style}>
    <div class="cs-eyebrow-wrap">{eyebrow_html}</div>
    {heading_html}{intro_html}
    <div class="c-faq-list"{multi_attr}>{items}</div>{cta_html}
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
    # FAQ routes by pattern id, legacy layout id, the composition's declared
    # useCase, OR the adapter's `_faq` stamp (event-scaffolds 2026-07: a composed
    # disclosure section needs no patternRef — the declaration IS the route, same
    # discipline as the hero below; the stamp covers semantic useCases like agenda).
    if pid == "faq-accordion-list" or lid == "exhibition-faq" \
            or layout.get("_faq") is not None \
            or ((layout.get("_composition") or {}).get("useCase") or "").lower() == "faq":
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


def _ov_panel_copy_stack(doc, ctx, layout, copy: dict) -> str:
    """Render a panel slot's OWN copy dict (eyebrow / heading / text|body / cta) as
    panel items through the shared primitives. The cta value (string or list)
    renders as a real action row: first action through render_button's law-first
    cta-shape dispatch, later actions with a secondary-treatment hint so the brand's
    own measured non-primary register resolves (AS-59 one-primary)."""
    items = []
    if str(copy.get("eyebrow") or "").strip():
        items.append(cr.render_eyebrow(doc, ctx, {"text": copy["eyebrow"]}))
    if str(copy.get("heading") or "").strip():
        items.append(cr.render_heading(doc, ctx, {
            "text": copy["heading"], "level": "display", "accent": False}))
    body = copy.get("text") or copy.get("body") or copy.get("subheading") or ""
    if str(body).strip():
        items.append(cr.render_paragraph(doc, ctx, {"text": body, "measure": "38ch"}))
    ctas = copy.get("cta")
    labels = [ctas] if isinstance(ctas, str) and ctas.strip() else \
        [str(x) for x in ctas if isinstance(x, str) and str(x).strip()] \
        if isinstance(ctas, list) else []
    if labels:
        frags = []
        for i, label in enumerate(labels):
            props = {"label": label, "accent": False}
            if i > 0:
                props["familyHint"] = "secondary outlined quiet"
            frags.append(cr.render_button(doc, ctx, props))
        items.append(f'<div class="cs-hero-actions"{ag_attrs(doc, layout)}>'
                     + "".join(frags) + "</div>")
    return "\n      ".join(f'<div class="cs-ov-panel-item">{h}</div>' for h in items)


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
        # the panel shell DOUBLING as the text payload (archetype-gallery 2026-07): a
        # composition that authors the whole copy dict ON the panel slot (no sibling
        # text slots) renders that copy as the panel stack — the old shell-only read
        # drew an EMPTY panel over the canvas and silently dropped the authored
        # heading. Sibling-slot compositions are byte-identical (inner wins).
        if not inner and panel_slot is not None \
                and isinstance(panel_slot.get("copy"), dict):
            inner = _ov_panel_copy_stack(doc, ctx, layout, panel_slot["copy"])
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
    if tom is not None and canvas is not None and foot_items:
        canvas_children.append(
            '\n      <div class="cs-ov-onmedia">'
            + "".join(foot_items) + "\n      </div>")
        foot_items = []
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
    # cards family dispatcher (event-scaffolds 2026-07): routes `_bento`/`_tiers`
    # stamped sections to their scaffolds, everything else to the module grid.
    "cards": compose_cards,
    "media-split": compose_media_split,
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
        # composition-declared disclosure routes without a patternRef (event-
        # scaffolds 2026-07) — dispatch-parity with compose_stack's stamp route.
        if pid == "faq-accordion-list" or lid == "exhibition-faq" \
                or (layout or {}).get("_faq") is not None \
                or (((layout or {}).get("_composition") or {}).get("useCase") or "").lower() == "faq":
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
# ── CONTAINMENT LAW (fix3 2026-07): ONE mechanism owns section containment ───────
# CONTAINMENT means "this box IS (or spans) the section's content column": it fills
# its parent (width: 100%), caps at the ONE shared measure and centers. Every major
# section container inherits containment from THIS list — devices must never
# re-declare `max-width: var(--content-measure)` / `margin-inline: auto` ad hoc.
# That scatter is exactly how two real bugs shipped: a box that re-implements
# containment INSIDE an already-contained column (the action row in the side-rail
# copy column) resolves its auto margins before flex stretch, so it HUGS its
# content and floats centered instead of spanning the column; and a device that
# simply forgot the pair (the split-panel carousel) painted full-bleed while every
# neighbor capped. `width: 100%` is load-bearing: it removes the hug-and-center
# failure mode by construction (auto margins never see free space in a narrower
# parent), so nesting a contained device inside a contained column is always safe.
#
# CONTAINMENT is not MEASURE. Deliberately narrower caps — the conversion stack's
# --cs-stack-measure, prose `ch` clamps, the hero collage's 80rem art frame — are
# device-owned text/media measures and stay where they are. The few places that
# must touch the shared var outside this law (derived insets, anchor releases,
# bleed escapes) carry a `contain-exempt:` tag; test_fix3 lints both directions.
CONTAINED_DEVICES = (
    ".cs-collage-grid", ".cs-statement-grid", ".cs-quote-grid", ".cs-visit-panels",
    ".cs-modules-intro", ".cs-modules", ".cs-interlock", ".cs-split-intro",
    ".cs-media-split", ".cs-hero-panel", ".cs-split", ".cs-conversion-panel",
    ".cs-bento", ".cs-tiers", ".cs-modules-actions", ".cs-ov-frame",
    ".cs-band-body", ".cs-flow", ".cs-tabs", ".cs-siderail", ".cs-headrail",
    ".cs-panelcar", ".cs-footer-sec > .c-footer")

CONTAINMENT_LAW_CSS = (
    "/* ── CONTAINMENT LAW (fix3 2026-07): the ONE shared containment mechanism.\n"
    "   Every major section container spans its parent, caps at the shared content\n"
    "   measure and centers — identical section edges page-wide. Devices inherit\n"
    "   containment from this rule and never re-declare it ad hoc; releases\n"
    "   (edge-cut rails, overlay bleeds) and narrower MEASURE caps are the tagged\n"
    "   exceptions, not private copies of this pair. */\n"
    + ",\n".join(CONTAINED_DEVICES)
    + " {\n  width: 100%; max-width: var(--content-measure, 86rem);"
      " margin-inline: auto; }")

SCAFFOLD_BASE_CSS = """.cs-section { background: var(--c-paper); color: var(--c-ink);
  padding: var(--c-section-pad-top) var(--c-section-pad-x)
           var(--c-section-pad-bottom); }
.cs-nav { display: flex; align-items: center; justify-content: space-between; gap: 2rem;
  margin-bottom: clamp(2rem, 6cqw, 5rem); }
.cs-navlinks { display: flex; gap: 0.55rem; flex: 1; justify-content: center; }
/* TWO-TIER bar (fix1 2026-07 item-12a, navbar.utilityTier): thin utility strip over
   the primary bar — rules inert unless render_navbar stamped the opt-in markup;
   the tier vars are that brand's measured heights/register set inline. */
.cs-nav--twotier { flex-direction: column; align-items: stretch; gap: 0; }
.cs-nav-tier { display: flex; align-items: center; gap: 2rem; }
.cs-nav-tier--utility { justify-content: space-between;
  min-height: var(--cs-utier-h, 2.5rem); background: var(--cs-utier-bg, transparent);
  font-size: var(--cs-utier-size, 0.75rem); }
.cs-nav-tier--utility .cs-nav-util { display: inline-flex; align-items: center;
  gap: 1.5rem; }
.cs-nav-tier--primary { justify-content: space-between;
  min-height: var(--cs-ptier-h, auto); }
/* bar ACTION GROUP (fix1 item-12b): N measured-register actions at the bar end. */
.cs-nav-actions { display: inline-flex; align-items: center; gap: 0.75rem;
  flex: 0 0 auto; }
/* nav links read the MEASURED nav register (--c-nav-size, single-sourced from
   brand.yaml navbar.measured.link), not the generic control-text size. */
.cs-navlinks .c-arrow-link { font-size: var(--c-nav-size, var(--c-control-size)); }
.cs-navlinks .cs-sep { opacity: 0.55; }
/* shared 12-col registration grid (column-gap IS the shared gutter). */
.cs-collage-grid, .cs-statement-grid, .cs-quote-grid, .cs-modules {
  display: grid; grid-template-columns: repeat(var(--grid-cols, 12), minmax(0, 1fr));
  column-gap: var(--grid-gutter, 6rem); }""" + "\n" + CONTAINMENT_LAW_CSS

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
/* foot gap: --cs-hero-foot-gap is a FALLBACK-ONLY override slot (fix1 2026-07
   item-4, measured bandRhythm.bodyToCta) — rhythm-less brands resolve straight
   back to the block gap, byte-identical. */
.cs-foot { display: flex; flex-direction: column; align-items: center;
  gap: var(--cs-hero-foot-gap, var(--c-block-gap)); text-align: center;
  margin-top: var(--c-block-gap); }
/* MEASURED hero stack measure (fix3, --cs-stack-measure — a FALLBACK-ONLY slot set
   inline from the pattern's stackMeasure fact): the hero's TEXT boxes cap at the
   source's own measured column so the display heading wraps like the source at any
   viewport (the wide-screen one-line-heading leak). Measure, not containment: the
   section column stays law-owned; fact-less brands resolve to `none`,
   byte-identical. Actions inside .cs-foot hug regardless (no cap needed). */
.cs-title, .cs-foot { max-width: var(--cs-stack-measure, none); }
/* subhead rides the brand body register one step up (1rem was body 0.875rem x 1.1429
   against the pre-token render — ratio is structure, magnitude is the brand's). */
.cs-sub { font-family: var(--c-font-body); font-size: calc(var(--c-body-size) * 1.1429);
  line-height: 1.55em; color: var(--c-ink-muted);
  /* description measure rides the brand's authored ladder (fid11) when present */
  max-width: var(--space-body-measure, 42rem); }
/* ── PLACED media layers (grid/overlap contract §4.6.5) ─────────────────────────
   Only sections whose composition declared placement get these classes; the legacy
   hero (.cs-collage without --layered) is byte-unchanged. z-ladder inside the layered
   collage: back overlays(0) < base media(1) < mid(2) < front(3) < display title(4);
   the corner-pinned media + background layer register to the SECTION frame. */
.cs-hero-layered { position: relative; overflow: hidden; }
.cs-hero-layered .cs-slot { position: relative; z-index: 2; }
.cs-hero-layered .cs-title { z-index: 4; }
/* FLAT layered hero (fix1 2026-07): no collage between title and foot — the collage
   overlap margin has nothing to overlap, so the title-to-body seam rides the block
   rhythm instead of the negative pull. Collage heroes are untouched. */
.cs-hero-layered--flat .cs-title { margin-bottom: 0; }
/* STACKED archetype hero (genre skeleton without an overlap device): the title-to-
   media seam rides the block rhythm — no negative pull into the collage. */
.cs-hero--stacked .cs-title { margin-bottom: 0; }
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
/* HERO ACTIONS row (AS-27 hero extension): real bound action slots cluster as a
   HORIZONTAL wrapping pair; each child is the shared c-button / c-arrow-link
   primitive (filled vs typographic is render_button's law-first dispatch, not CSS).
   sysfix 2026-07: gap is CONTROL-scale (1em — an action pair sits on the control
   rhythm, not the section block rhythm; the old block-gap forced a wrap in the
   split-hero column) and alignment defaults to the reading edge — the old
   `justify-content: inherit` crossed axes (a flex-COLUMN parent's `center` means
   vertical centering, but inherited into this ROW it centered the pair). Centered
   contexts opt in explicitly (.cs-foot below / the conversion centered anchor). */
.cs-hero-actions { display: flex; flex-wrap: wrap; align-items: center;
  gap: 1em; justify-content: flex-start; }
.cs-foot .cs-hero-actions { justify-content: center; }
/* hero MARK RAIL (fix6): an archetype anatomy's agenda/track/award row after the
   actions — the shared logo-strip device + one caption line, following the foot's
   stance (centered foot centers the rail; anchored packs re-anchor like actions).
   The rail's marks are the BRAND'S OWN iconography (an agenda/track row), not a
   third-party proof wall — the style layer's logoStrip emphasis treatment
   (grayscale/reduced) does not apply inside the rail; marks render as shipped. */
.cs-hero-rail { display: flex; flex-direction: column;
  gap: var(--space-cluster-gap, var(--c-cluster-gap, 0.75rem)); }
.cs-foot .cs-hero-rail .cs-logo-strip { justify-content: center; }
.cs-hero-rail .c-caption { margin: 0; }
.cs-hero-rail .cs-logo-strip .c-logo-img { filter: none; opacity: 1; }
/* hero form + quiet link rail (fix6, archetype anatomy devices): the form block
   caps at the CTA/control measure inside the foot; the link rail is one wrapping
   row of arrow links at a quiet register. */
/* one mechanic owns the width: the foot column is already capped at the hero's
   measured stack measure, so the form fills it (no second competing cap). */
.cs-hero-form { width: 100%; display: flex; flex-direction: column;
  gap: var(--space-field-label-gap, 0.5em); }
.cs-hero-form .c-form { margin: 0; }
.cs-hero-form .c-paragraph { margin: 0; }
/* the form NOTE attaches to its control (fix7 punch 6/7): caption register BELOW the
   field, capped to the control's own width (the wrapper's), balanced wrap — a meta
   line inside an anchored stack honors the stack anchor, never a ragged floater.
   (.c-caption already carries text-wrap: balance in the component base.) */
.cs-hero-form .c-caption { margin: 0; max-width: 100%; align-self: stretch; }
.cs-hero-links { display: flex; flex-wrap: wrap; align-items: center;
  justify-content: center; column-gap: var(--c-cluster-gap, 1rem);
  row-gap: 0.5rem; }
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
  /* containment: CONTAINMENT_LAW_CSS (fix3) */
  border-radius: var(--radius-panel, var(--radius));
  background-color: var(--c-panel-bg, var(--c-paper));
  background-size: cover; background-position: center top; overflow: hidden;
  /* PANEL INSET = the brand's measured panel-padding fact (fix7, pass-3 follow-up
     4): the spacing law (hero.panel-inset) always expected it; the device padded
     the module-gap rhythm instead — first composed instantiation exposed the
     mismatch. Brands without the fact keep the module-gap degrade. */
  padding: var(--space-panel-padding, var(--c-module-gap, 6rem))
           var(--space-panel-padding, var(--c-module-gap, 6rem)); }
.cs-hero-panel--solo { grid-template-columns: minmax(0, 1fr); }
.cs-hero-panel-content { display: flex; flex-direction: column; align-items: flex-start;
  justify-content: center; gap: var(--c-block-gap); text-align: left; }
.cs-hero-panel-content .cs-title { margin-bottom: 0; text-align: inherit; }
/* poster stance (event-scaffolds 2026-07): a `centered` anchor centers the panel's
   content column; the display heading gets a contained poster measure so a long
   centered title wraps as a block instead of one viewport-wide line. */
.cs-hero-panel--center .cs-hero-panel-content { align-items: center; text-align: center; }
.cs-hero-panel--center .cs-hero-panel-content .c-heading--display { max-width: 18ch; }
.cs-hero-panel--center .cs-hero-panel-content .cs-sub { margin-inline: auto; }
.cs-hero-panel--center .cs-hero-actions { justify-content: center; }
.cs-hero-panel-meta { margin: 0; }
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
SCAFFOLD_SPLIT_CSS = """/* container width rides the shared content container
   (SCAFFOLD_BASE_CSS; spacing remediation B3 2026-07 — the old `max-width: 100%`
   here escaped the container law). */
.cs-split-intro { margin-bottom: 3.5rem; }
/* RELATIONAL-LADDER RHYTHM (fid2 2026-07): the heading→body seam rides the brand's
   measured ladder token everywhere — block-flow intros rendered the pair with NO
   gap while flex bodies used the generic block gap (different sections, different
   rhythm). Ladder-less brands fall back to the block gap (historical look). */
.cs-split-intro .c-header + .c-paragraph {
  margin-block-start: var(--space-heading-to-body, var(--c-block-gap, 1.5rem)); }
.cs-split-intro .cs-eyebrow-wrap { margin-bottom: var(--c-eyebrow-gap); }
/* the band heading is the didone DISPLAY tier; give it room to breathe (the style's
   global 16ch display cap is too tight for this dark-band heading). */
.cs-split-intro .c-heading--display { max-width: 22ch; }
/* the split places onto 12 shared columns with a ZERO gutter (the flush hard cut is the
   band's character): each half spans 6, so its seam registers to the grid's center line.
   Containment (max-width + centering): CONTAINMENT_LAW_CSS (fix3; was fid10 here). */
.cs-split { display: grid; grid-template-columns: repeat(var(--grid-cols, 12), minmax(0, 1fr));
  gap: 0; align-items: stretch; }
/* the PANEL variant opens the brand's split gutter between its halves (spacing
   remediation B4 2026-07): a brand that authored column-to-column gets the
   measured seam between media and ledger panel; fact-less brands keep the flush
   hard cut (the original band character — 0 is the degrade, not a new default). */
.cs-split--panel { column-gap: var(--space-column-to-column, 0); }
.cs-split-media { grid-column: 1 / span 6; display: flex; }
.cs-split > .cs-panel { grid-column: 7 / -1; }
/* panel-less split (media | text, sysfix 2026-07): when the brand declared no panel
   furniture, the copy column rides the grid's second half on the reading rhythm — a
   vertically-centered text stack, breathing room instead of the flush panel cut. */
.cs-split > .cs-split-body { grid-column: 8 / -1; display: flex;
  flex-direction: column; justify-content: center; align-items: flex-start;
  /* ladder rhythm (fid2 2026-07): heading→body seam = the measured ladder token;
     the action row below restores its own (larger) body→cta rung. */
  gap: var(--space-heading-to-body, var(--c-block-gap)); }
.cs-split-body > .cs-hero-actions, .cs-split-body > .c-arrow-link {
  margin-block-start: calc(var(--space-body-to-cta, var(--c-block-gap, 1.5rem))
    - var(--space-heading-to-body, var(--c-block-gap, 1.5rem))); }
/* ONE mechanic owns the eyebrow→heading seam (spacing remediation B1 2026-07):
   the base .c-header already carries the flex column + eyebrow gap, and the
   relational ladder converts that to owl margins — re-declaring the gap here
   at higher specificity re-added it ON TOP of the ladder margin (doubled seam).
   No local rule: base + ladder own it. */
.cs-split-body .c-paragraph { margin: 0; }
.cs-split-media .c-image { width: 100%; height: 100%; object-fit: cover; }
/* MEASURED MEDIA REGION (fid10 2026-07, deviceGeometry.media stamps — var/class-gated,
   structural presentation is the no-stamp degrade): a measured frame aspect fixes the
   region's shape; `fit: contain` letterboxes the asset inside it (the source's own
   object-fit) instead of cover-cropping; `align: top` pins the frame to the column top. */
.cs-split-media--top { align-items: flex-start; }
.cs-split-media--framed .c-image-mask { width: 100%;
  aspect-ratio: var(--cs-split-media-aspect, auto); }
.cs-split-media--framed .c-image { height: 100%; }
.cs-split-media--contain .c-image { object-fit: contain; }
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
/* FORM-SPLIT hero (fix6): copy column | capture panel. The copy column takes the
   reading half, the panel the counterweight half with the brand's column gutter
   between; formSide:left mirrors the pair. Field/panel anatomy is the signup
   scaffold's (SCAFFOLD_SIGNUP_CSS) — nothing new is styled here but placement. */
.cs-split--form { column-gap: var(--space-column-to-column, 2rem);
  align-items: center; }
/* adjacent halves: the brand's column-to-column token IS the visible gap
   (an empty registration column would re-register the seam off the ladder). */
.cs-split--form > .cs-split-body { grid-column: 1 / span 6; grid-row: 1; }
.cs-split--form > .cs-form-split-panel { grid-column: 7 / -1; grid-row: 1; }
.cs-split--form-left > .cs-split-body { grid-column: 7 / -1; }
.cs-split--form-left > .cs-form-split-panel { grid-column: 1 / span 6; }
.cs-form-split-points { list-style: none; margin: 0; padding: 0; width: 100%;
  max-width: var(--cs-stack-measure, 34rem);
  font-family: var(--c-font-body); font-size: var(--c-body-size, 1rem);
  line-height: 1.5; color: var(--c-ink); }
.cs-form-split-points li { padding: 0.65em 0;
  border-top: 1px solid var(--c-hairline); }
.cs-form-split-points li:last-child { border-bottom: 1px solid var(--c-hairline); }
.cs-form-split-note { margin: 0; }
/* HEADING FIT-TO-MEASURE (fix7 punch 5): a stepped display heading re-registers its
   SIZE to the stamped rung of the brand's own ladder — class/semantics/budget stay
   display (the pass1 overlay-panel channel); the leading is the display tier's own
   em-relative value so it scales with the step. Stamp-less columns are inert. */
[data-fit-rung="h1"] .c-heading--display { font-size: var(--c-h1-size); }
[data-fit-rung="h2"] .c-heading--display { font-size: var(--c-h2-size); }
/* STAT PAIR SEPARATION (fix7 punch 4): a stat device separates from the preceding
   block by >= 1.5x the column's sibling gap — the parent flex gap (heading-to-body
   rung) supplies 1x, this margin adds the other 0.5x, so the bound value+label pair
   reads as its OWN block instead of another list row. */
.cs-split-body > * + .c-stat { margin-block-start:
  calc(0.5 * var(--space-heading-to-body, var(--c-block-gap, 1.5rem))); }
@media (max-width: 767px) { .cs-split { grid-template-columns: 1fr; }
  .cs-split-media, .cs-split > .cs-panel, .cs-split > .cs-split-body { grid-column: 1; }
  .cs-split--form > .cs-split-body, .cs-split--form > .cs-form-split-panel {
    grid-column: 1; grid-row: auto; }
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
# INSET CONVERSION PANEL (fid2 2026-07; gated on the layout's _insetPanel stamp —
# AS-37): the rounded band the conversion stack sits on. Radius = the brand's own
# measured panel tier; the backdrop art (when the brand's inventory carries one)
# cover-paints the panel behind the stack.
SCAFFOLD_CONVERSION_PANEL_CSS = """.cs-conversion-panel { position: relative; overflow: hidden;
  border-radius: var(--radius-panel, var(--radius-card, 0));
  padding: clamp(3rem, 8cqw, 6.5rem) var(--c-section-pad-x);
  display: flex; justify-content: center;
  /* containment (spans + caps + centers): CONTAINMENT_LAW_CSS (fix3; was fid10 here) */ }
.cs-conversion-panel-art { position: absolute; inset: 0; width: 100%; height: 100%;
  object-fit: cover; border-radius: 0; }
.cs-conversion-panel .cs-conversion { position: relative; }"""

# FULL-BLEED ART BAND (fid5 2026-07; gated on the layout's _artSurface stamp — AS-37):
# the section's own box paints edge-to-edge with the brand's band art (no radius, no
# inset — the closing-band grammar), the stack rides above it. Art missing from the
# brand's inventory ⇒ only the positioning context ships (flat surface fill).
SCAFFOLD_CONVERSION_BAND_CSS = """.cs-conversion-sec--band { position: relative; overflow: hidden; }
.cs-conversion-band-art { position: absolute; inset: 0; width: 100%; height: 100%;
  object-fit: cover; z-index: 0; }
.cs-conversion-sec--band > .cs-conversion { position: relative; z-index: 1; }"""

SCAFFOLD_CONVERSION_CSS = """.cs-conversion-sec { display: flex; justify-content: center; }
.cs-conversion { display: flex; flex-direction: column; align-items: center; text-align: center;
  /* ladder rhythm (fid2 2026-07): same seam discipline as the split body. */
  gap: var(--space-heading-to-body, var(--c-block-gap));
  /* column cap = the pattern's measured stackMeasure when stamped (fid7 2026-07);
     46rem stays the structural default for brands without the fact. */
  max-width: var(--cs-stack-measure, 46rem); width: 100%; --c-cta-measure: 40ch; }
.cs-conversion > .cs-conversion-actions, .cs-conversion > .c-form {
  margin-block-start: calc(var(--space-body-to-cta, var(--c-block-gap, 1.5rem))
    - var(--space-heading-to-body, var(--c-block-gap, 1.5rem))); }
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

# ── BENTO GRID scaffold (event-scaffolds 2026-07; ships ONLY with a `_bento` stamp —
# AS-37 conditional-shipping discipline). MECHANICS generic: a 12-track dense mosaic
# whose cell weights ride per-cell --bn-span/--bn-rows (validated composition knobs,
# emitted inline by the composer); every VISIBLE value rides brand tokens — panel
# surface/ink/hairline chain, card radius, measured panel padding, baseline rhythm.
# CONTAINER LAW (AS-45): the mosaic spans the shared content measure and centers.
# Cell gap is a pattern-fact knob (--bn-gap, stamped per section); 1rem structural
# floor. Collapse tier = the stamp's collapseAt container query (layout_placement_css)
# + the structural mobile floor below.
SCAFFOLD_BENTO_CSS = """.cs-bento-sec { display: flex; flex-direction: column;
  gap: calc(6 * var(--baseline)); }
.cs-bento { display: grid; grid-template-columns: repeat(12, minmax(0, 1fr));
  grid-auto-flow: dense; gap: var(--bn-gap, 1rem);
  /* containment: CONTAINMENT_LAW_CSS (fix3; was AS-45 note here) */ }
.cs-bento-cell { grid-column: var(--bn-col, span var(--bn-span, 4));
  grid-row: span var(--bn-rows, 1);
  display: flex; flex-direction: column; gap: calc(1.5 * var(--baseline));
  background: var(--bn-bg, var(--c-panel)); color: var(--bn-ink, var(--c-panel-ink));
  --c-ink: var(--bn-ink, var(--c-panel-ink)); --c-ink-muted: var(--bn-ink, var(--c-panel-ink));
  --c-hairline: var(--c-panel-hairline);
  border-radius: var(--radius-card, 0);
  --c-plate-pad: var(--space-panel-padding, calc(4 * var(--baseline)));
  padding: var(--c-plate-pad); }
.cs-bento-cell .c-paragraph { max-width: none; }
.cs-bento-cell .c-heading { text-align: inherit; }
/* LEAD cell (stamped lead: true): its statement rides the measured h2 register —
   a register CHOICE from the brand's own ladder (the oversized quote/statement
   tier), never an invented magnitude. */
.cs-bento-cell--lead .c-paragraph { font-family: var(--c-font-heading);
  font-size: var(--c-h2-size); line-height: 1.3em; font-weight: var(--c-heading-weight, 500);
  color: var(--c-ink); }
/* person attribution inside a cell (same c-person anatomy as the card plates,
   scoped so panel-less brands get the row without the plate scaffold). */
.cs-bento-cell .c-person { display: flex; align-items: center; gap: 0.85rem;
  margin-top: auto; border-top: 1px solid var(--c-hairline);
  padding-top: calc(2 * var(--baseline)); }
.cs-bento-cell .c-person-meta { display: flex; flex-direction: column; gap: 0.15em; }
.cs-bento-cell .c-arrow-link { margin-top: auto; }
/* media well: bleeds to the cell's top + side edges (the card-plate well anatomy),
   top corners on the card radius; the image covers its measured frame. */
.cs-bento-media { margin: calc(-1 * var(--c-plate-pad)) calc(-1 * var(--c-plate-pad)) 0;
  overflow: hidden;
  border-radius: var(--radius-card, 0) var(--radius-card, 0) 0 0; }
.cs-bento-media .c-image { width: 100%; height: 100%; object-fit: cover;
  border-radius: 0; }
/* structural mobile floor: single column, natural row heights. */
@media (max-width: 767px) {
  .cs-bento { grid-template-columns: 1fr; }
  .cs-bento-cell { grid-column: auto; grid-row: auto; } }"""

# ── PRICING TIERS scaffold (event-scaffolds 2026-07; ships ONLY with a `_tiers`
# stamp). N peer panels on one equal-track row (--tier-cols, default 3; the stamp's
# collapseAt tier folds to one column via layout_placement_css + the structural
# floor). Emphasis is a sanctioned SURFACE/BORDER relationship: the emphasized
# tier's head band paints a declared surface role (inline --bn-bg/--bn-ink vars,
# same token-layer resolution as the bento cells) and/or the tier ring rides the
# brand's strong input-border token — never an invented badge. Price rides the
# heading stack at the measured h2 register.
SCAFFOLD_TIERS_CSS = """.cs-tiers-sec { display: flex; flex-direction: column;
  gap: calc(6 * var(--baseline)); }
.cs-tiers { display: grid; grid-template-columns: repeat(var(--tier-cols, 3), minmax(0, 1fr));
  gap: var(--bn-gap, 1rem); align-items: stretch;
  /* containment: CONTAINMENT_LAW_CSS (fix3) */ }
.cs-tier { display: flex; flex-direction: column; gap: calc(1.5 * var(--baseline));
  background: var(--c-panel); color: var(--c-panel-ink);
  --c-ink: var(--c-panel-ink); --c-ink-muted: var(--c-panel-ink);
  --c-hairline: var(--c-panel-hairline);
  border-radius: var(--radius-card, 0);
  --c-plate-pad: var(--space-panel-padding, calc(4 * var(--baseline)));
  padding: var(--c-plate-pad); }
.cs-tier--emph { border: 1px solid var(--c-input-border, var(--color-border-input, var(--c-panel-hairline))); }
.cs-tier-head { display: flex; flex-direction: column; gap: calc(1 * var(--baseline)); }
/* emphasized head band on a declared surface role: bleeds to the panel edges
   (the media-well negative-margin anatomy) and re-scopes its ink pair. */
.cs-tier-head--surface { background: var(--bn-bg, var(--c-panel));
  color: var(--bn-ink, var(--c-panel-ink));
  --c-ink: var(--bn-ink, var(--c-panel-ink)); --c-ink-muted: var(--bn-ink, var(--c-panel-ink));
  margin: calc(-1 * var(--c-plate-pad)) calc(-1 * var(--c-plate-pad)) 0;
  padding: var(--c-plate-pad);
  border-radius: var(--radius-card, 0) var(--radius-card, 0) 0 0; }
.cs-tier-name { margin: 0; }
.cs-tier-price { font-family: var(--c-font-heading); font-weight: var(--c-heading-weight, 500);
  font-size: var(--c-h2-size); line-height: 1.1em; color: var(--c-ink);
  display: flex; align-items: baseline; gap: 0.4em; flex-wrap: wrap; }
.cs-tier-unit { font-family: var(--c-font-body); font-weight: var(--c-body-weight, 400);
  font-size: var(--c-control-size); color: var(--c-ink-muted); }
.cs-tier-tagline { font-family: var(--c-font-body); font-size: var(--c-body-size);
  line-height: 1.5em; color: var(--c-ink); margin: 0; }
.cs-tier-list { list-style: none; margin: 0; padding: 0;
  display: flex; flex-direction: column; }
.cs-tier-list li { padding-block: calc(1.5 * var(--baseline));
  border-top: 1px solid var(--c-hairline);
  font-family: var(--c-font-body); font-size: var(--c-body-size);
  line-height: 1.45em; color: var(--c-ink); }
/* content-hugging action pinned to the panel foot (non-stretch alignment — a flex
   column stretches children by default, which fabricates full-width buttons). */
.cs-tier > .c-button, .cs-tier > .c-arrow-link { margin-top: auto; align-self: flex-start; }
.cs-tiers-note { text-align: center; margin: 0; }
@media (max-width: 767px) { .cs-tiers { grid-template-columns: 1fr; } }"""

# ── SIGNUP FORM scaffold (event-scaffolds 2026-07; ships ONLY with a `_formFields`
# stamp). Extends the conversion stack: intro (header/body/meta — the AS-14 exchange
# copy) above ONE form panel of label-above boxed fields on a responsive half/full
# grid. Field anatomy rides the SAME token chain as the boxed form variant
# (--c-input-radius/-border/-bg; the strong border/input color; control height from
# the measured button height); the focus ring's COLOR is the brand's declared
# focus-ring role (geometry is the measured focus-fact shape: 2px ring, 2px offset —
# ring params, not a brand magnitude; currentColor degrade). Choice controls ride
# accent-color from the measured button bg (no restyled fake radios).
SCAFFOLD_SIGNUP_CSS = """.cs-signup { --c-cta-measure: 100%; }
.cs-signup-meta { margin: 0; }
.cs-signup-panel { width: 100%; text-align: left;
  display: flex; flex-direction: column;
  /* form-stack fact (B8 2026-07): the brand's measured form-module stack rhythm;
     the structural 2-baseline gap is the fact-less degrade. */
  gap: var(--space-form-stack, calc(2 * var(--baseline))); }
/* brands declaring a Container surface plate the form on it (card_panel_role);
   panel-less brands keep the open column (class absent — no invented panel). */
.cs-signup-panel--plate { background: var(--c-panel); color: var(--c-panel-ink);
  --c-ink: var(--c-panel-ink); --c-ink-muted: var(--c-panel-ink);
  --c-hairline: var(--c-panel-hairline);
  border-radius: var(--radius-panel, var(--radius-card, 0));
  --c-plate-pad: var(--space-panel-padding, calc(4 * var(--baseline)));
  padding: calc(1.5 * var(--c-plate-pad)) var(--c-plate-pad); }
.cs-signup-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr));
  /* field-to-field fact (B8 2026-07): the form's measured field-grid rhythm rides
     both axes; the structural 2-baseline gap is the degrade. */
  gap: var(--space-field-to-field, calc(2 * var(--baseline)))
       var(--space-field-to-field, calc(2 * var(--baseline))); }
/* field-label-gap fact (B8 2026-07): the measured label→control seam; the
   structural 0.5em register-relative seam is the degrade. */
.cs-field { display: flex; flex-direction: column;
  gap: var(--space-field-label-gap, 0.5em); min-width: 0; }
.cs-field--full { grid-column: 1 / -1; }
.cs-field-label { font-family: var(--c-font-body); font-size: var(--c-control-size);
  font-weight: 500; color: var(--c-ink); text-align: left; }
.cs-field-help { font-family: var(--c-font-body);
  font-size: calc(var(--c-control-size) * 0.85); color: var(--c-ink-muted);
  line-height: 1.4em; }
.cs-input { width: 100%; min-height: var(--c-button-height, 3rem);
  padding: 0 0.9em; /* provenance: structural — em-relative field inset (shape, not
     magnitude), same discipline as .c-field--boxed */
  font-family: var(--c-font-body); font-size: var(--c-control-size); color: var(--c-ink);
  border: 1px solid var(--c-input-border, var(--color-border-input, var(--c-hairline)));
  border-radius: var(--c-input-radius, var(--radius-input, var(--radius)));
  background: var(--c-input-bg, transparent); }
.cs-input:focus-visible { outline: 2px solid var(--color-action-focus-ring, currentColor);
  outline-offset: 2px;
  border-color: var(--c-input-border-active, var(--color-border-input, var(--c-ink))); }
select.cs-input { appearance: auto; }
/* real multiline control (W12): same anatomy chain as .cs-input; the vertical inset
   mirrors the single-line optical centering (structural shape, not a magnitude) and
   only vertical resize is offered so the authored grid column holds. */
.cs-input--multiline { min-height: 0; height: auto; padding: 0.65em 0.9em;
  line-height: 1.5em; resize: vertical; }
.cs-choice-group { border: 0; margin: 0; padding: 0;
  display: flex; flex-direction: column; gap: 0.75em; }
.cs-choice-group legend { padding: 0; margin-bottom: 0.5em; }
.cs-choice { display: flex; align-items: center; gap: 0.6em; text-align: left;
  font-family: var(--c-font-body); font-size: var(--c-control-size); color: var(--c-ink); }
.cs-choice input { width: 1.05em; height: 1.05em; margin: 0; flex: 0 0 auto;
  accent-color: var(--c-button-bg, var(--c-accent)); }
.cs-choice input:focus-visible { outline: 2px solid var(--color-action-focus-ring, currentColor);
  outline-offset: 2px; }
.cs-choice-label { line-height: 1.4em; }
.cs-signup-consent { text-align: left; margin: 0; max-width: none;
  font-family: var(--c-font-body); font-size: calc(var(--c-control-size) * 0.85);
  line-height: 1.5em; color: var(--c-ink-muted); }
.cs-signup-actions { display: flex; }
.cs-signup-actions .c-button { cursor: pointer; }
.cs-signup-submit-link { background: none; border: 0; padding: 0; cursor: pointer;
  font: inherit; }
.cs-signup-success { font-family: var(--c-font-body); font-size: var(--c-control-size);
  color: var(--c-ink); margin: 0; }
@media (max-width: 639px) { .cs-signup-grid { grid-template-columns: 1fr; } }"""

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
/* list-item-inset + list-item-gap facts (B8 2026-07): the disclosure item's own
   trigger inset and the stride BETWEEN item boxes ride the brand's measured
   accordion rungs; the structural 1.5rem inset / flush stride are the degrades. */
.c-faq-item { position: relative; padding: var(--space-list-item-inset, 1.5rem) 0; }
.c-faq-item + .c-faq-item { margin-top: var(--space-list-item-gap, 0); }
.c-faq-item::before { content: ""; position: absolute; left: 0; right: 0; top: 0; height: 1px;
  background: var(--c-hairline); }
.c-faq-item:last-child { padding-bottom: 0; }
.c-faq-q { font-family: var(--c-font-heading); font-size: var(--c-h3-size); color: var(--c-ink);
  cursor: pointer; list-style: none; display: flex; align-items: baseline;
  justify-content: space-between; gap: 1.5rem; }
.c-faq-q::-webkit-details-marker { display: none; }
/* disclosure glyph rides the question register: a fixed ratio of the brand's own h3
   question size (1.25rem was 1.625rem x 0.7692 against the pre-token render).
   Marker/panel MOTION lives in the shared disclosure_motion_css block (AS-47). */
.c-faq-icon { font-family: var(--c-font-body);
  font-size: calc(var(--c-h3-size) * 0.7692); color: var(--c-ink-muted);
  flex: 0 0 auto; }
.c-faq-item[open] .c-faq-icon { transform: rotate(45deg); }
.c-faq-a { font-family: var(--c-font-body); font-size: var(--c-body-size); line-height: 1.55em;
  color: var(--c-ink-muted); max-width: var(--space-body-measure, 56ch); margin-top: 0.85rem; }
@media (max-width: 767px) { .cs-faq { max-width: 100%; } .c-faq-q { font-size: var(--c-h3-size); } }"""

# stamped disclosure STATE grammar (event-scaffolds 2026-07): the brand's own
# one-open emphasis on the FAQ scaffold's rows — open-item inversion to a sanctioned
# surface role and/or an idle hover wash from a sanctioned color role. Values ride
# the section vars compose_faq_accordion resolves through the token layer; this
# block ships ONLY when a page section stamps a state role (AS-37 discipline), so
# every existing FAQ page keeps byte-identical CSS. The stated variant gives rows
# an inline inset (the fill needs breathing room the bare hairline rows don't) on
# the brand's card radius — the inset-emphasis card the accordion grammar records.
SCAFFOLD_FAQ_STATE_CSS = """.cs-faq--stated .c-faq-item {
  padding-inline: calc(2 * var(--baseline));
  border-radius: var(--radius-card, 0); }
.cs-faq--stated .c-faq-item:not([open]):hover { background: var(--faq-hover-bg, transparent); }
.cs-faq--stated .c-faq-item[open] { background: var(--faq-active-bg, transparent);
  /* the open item's pop-out margin rides the same measured list stride (B8) so the
     stated variant cannot under-run the brand's item rhythm. */
  padding-block: var(--space-list-item-inset, 1.5rem);
  margin-block: var(--space-list-item-gap, 0.5rem);
  --c-ink: var(--faq-active-ink, inherit); --c-ink-muted: var(--faq-active-ink, inherit); }
.cs-faq--stated .c-faq-item[open]::before { display: none; }
.cs-faq--stated .c-faq-item[open] + .c-faq-item::before { display: none; }
.cs-faq--stated .c-faq-item:last-child {
  padding-bottom: var(--space-list-item-inset, 1.5rem); }
.cs-faq--stated .c-faq-a { color: var(--c-ink-muted); }"""

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
/* ladder rhythm (fid2 2026-07): intro heading→subhead seam = the measured token. */
.cs-modules-intro .c-header + .c-paragraph {
  margin-block-start: var(--space-heading-to-body, var(--c-block-gap, 1.5rem)); }
.cs-modules { row-gap: clamp(calc(4 * var(--baseline)), 5cqw,
  calc(7 * var(--baseline))); align-items: start; }
.cs-modules > .cs-module:nth-child(odd) { grid-column: 1 / span var(--c-span-a, 7); }
.cs-modules > .cs-module:nth-child(even) { grid-column: span var(--c-span-b, 5) / -1; }
.cs-module { --cs-module-gap: 0.9rem; display: flex; flex-direction: column;
  gap: var(--cs-module-gap); }
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
/* An explicitly classified mark stays a bounded glyph row even when this brand
   uses flat modules instead of Container card plates. */
.cs-modules .cs-module-media--mark { display: flex; align-items: center;
  justify-content: flex-start; height: 2.25rem; }
.cs-modules .cs-module-media--mark .c-image { width: auto; height: 100%;
  max-width: 12rem; object-fit: contain; }
/* geometry belongs to the WELL/PLATE, never the bitmap (fid13: the source's card
   images are square — the plate's own radius clips the visible corners; an image
   carrying the global radius rounds all four corners INSIDE the well). */
.cs-module-media .c-image { width: 100%; height: 100%; border-radius: 0; }
/* DECLARED module grid (sysfix 2026-07: brand gridRules.columns → _grid → --grid-cols):
   one module per track, no stagger — overrides the nth-child registration spans above
   for sections whose composition declares an N-up card grid. */
.cs-modules--cols > .cs-module, .cs-modules--cols > .cs-module:nth-child(odd),
.cs-modules--cols > .cs-module:nth-child(even), .cs-modules--cols > .cs-module:nth-child(1),
.cs-modules--cols > .cs-module:nth-child(2), .cs-modules--cols > .cs-module:nth-child(3) {
  grid-column: auto; margin-block-start: 0; }
/* WIREFRAME GRID FILL (AS-77): explicit per-item spans own occupancy after the
   component-fit solver selects tracks. Structural nth-child stagger rules above
   cannot override this plan. A spanning card may retain a readable internal
   measure while its painted plate fills the full row. */
.cs-modules--cols > .cs-module[data-grid-span] {
  grid-column: span var(--cs-grid-span, 1); }
.cs-modules--cols > .cs-module[data-grid-span]:not([data-grid-span="1"]) > * {
  max-width: var(--cs-span-content-measure, none); }
/* a declared-gutter N-up grid is UNIFORM: wrap rows ride the same measured gutter
   (fid6 2026-07 — --grid-gutter-row is emitted by layout_placement_css only when the
   section's evidence declares a grid gap; without it the editorial row rhythm holds).
   RUNG SELECTION (spacing remediation B6 2026-07): the card grid's column seam is the
   brand's own CARD-GRID rung (--space-grid-gap), not the page's split/registration
   gutter — a declared section gutter (--grid-gutter-col) still wins, and brands
   without a grid-gap fact keep riding the shared page gutter (the degrade). */
.cs-modules--cols { column-gap: var(--grid-gutter-col,
  var(--space-grid-gap, var(--grid-gutter, 6rem)));
  /* UNIFORM N-up grids wrap rows on the brand's card-grid rung too (fix7: a
     knob-declared column count carries no gutter declaration, and the editorial
     clamp is stagger-grid rhythm, not uniform-grid rhythm); the editorial clamp
     stays the degrade for brands without the token. */
  row-gap: var(--grid-gutter-row, var(--space-grid-gap,
  clamp(calc(4 * var(--baseline)), 5cqw, calc(7 * var(--baseline))))); }
/* CARD REGISTER LADDER rhythm (fid6 2026-07): a module carrying its own eyebrow +
   heading anatomy rides the brand's measured relational spacing ladder for its
   internal seams — eyebrow→heading, heading→body, body→cta — instead of the uniform
   structural flex gap. Fallbacks keep the old 0.9rem rhythm for ladder-less brands. */
.cs-module--anatomy { --cs-module-gap: 0rem; gap: 0; }
.cs-module--anatomy > * + * {
  margin-block-start: var(--space-heading-to-body, 0.9rem); }
.cs-module--anatomy > .c-eyebrow + .c-heading {
  margin-block-start: var(--space-eyebrow-to-heading, 0.9rem); }
.cs-module--anatomy > .c-arrow-link {
  margin-block-start: var(--space-body-to-cta, 0.9rem); }
/* QUOTE-CARD seams (spacing remediation B8 2026-07): a quote module (mark → quote
   body → attribution) rides the brand's measured quote-card rungs — mark→quote and
   quote→attribution — the same owl-margin mechanic as the anatomy ladder. The
   uniform 0.9rem flex rhythm survives as the fact-less degrade. */
.cs-module--quote { --cs-module-gap: 0rem; gap: 0; }
.cs-module--quote > * + * {
  margin-block-start: var(--space-mark-to-quote, 0.9rem); }
.cs-module--quote > * + .c-person {
  margin-block-start: var(--space-quote-to-attribution, 0.9rem); }
/* MARK media (sysfix 2026-07: logo/badge/rating/vector module media): contained inside
   the module frame — never cover-cropped/stretched; the same mark-geometry discipline
   as the logo-strip device (structural frame behavior, not a brand magnitude). */
.cs-module-media--contain { display: flex; align-items: center; justify-content: center; }
.cs-module-media--contain .c-image { width: 100%; height: 100%; object-fit: contain; }
/* bound action slots (P2 parity with the split/hero routes): one action row under the
   modules — present only when the section binds a real button slot; centered rides the
   section's resolved alignment stamp.
   fix3 (the action-row centering leak): the row's PRIVATE `max-width + margin-inline:
   auto` copy of containment is GONE — inside the side-rail copy column the auto
   margins resolved before flex stretch, so the row hugged its two buttons and floated
   centered (+21px off the column edge) while stamped data-ag-align="start". The row
   now inherits containment from CONTAINMENT_LAW_CSS (width:100% makes the auto
   margins inert in narrower columns); item placement inside the box belongs to
   justify-content — anchors and the action-group law own it, never box margins.
   align-items: center is CROSS-AXIS only (vertically centers unequal-height actions;
   the captured sources bear it — a brand whose evidence differs authors
   actionGroup.crossAlign, consumed by action_group_css). */
.cs-modules-actions { display: flex; flex-wrap: wrap; align-items: center;
  gap: var(--c-block-gap); margin-block-start: clamp(2rem, 5cqw, 3.5rem); }
[data-align="centered"] .cs-modules-actions { justify-content: center; }
@media (max-width: 767px) { .cs-modules { grid-template-columns: 1fr; gap: 2.5rem; }
  .cs-modules > .cs-module:nth-child(odd), .cs-modules > .cs-module:nth-child(even) {
    grid-column: 1; margin-block-start: 0; }
  .cs-modules--cols > .cs-module[data-grid-span] { grid-column: 1; }
  .cs-modules--cols > .cs-module[data-grid-span] > * { max-width: none; } }"""

# interlock (float-wrap statement + inset image — editorial-interlocking-inset, Claude
# Design #11): the image FLOATS to one side (--c-float-side / --c-inset-width / --c-inset-
# margin) and the long statement heading WRAPS around it; the caption's big --c-inset-drop
# bottom margin drops the headline so its first lines sit level with the image. The display
# heading runs full measure at a CONTAINED editorial scale (not the poster hero scale) so a
# Evidence-qualified editorial interlock.  Its adapter/composer preconditions exclude
# short/simple split content and unsupported foot clusters; retained instances use a
# registered 5/7 grid, not float/clear width arithmetic (AS-58).
SCAFFOLD_INTERLOCK_CSS = """.cs-interlock { position: relative; display: grid;
  grid-template-columns: minmax(0, 5fr) minmax(0, 7fr);
  gap: var(--grid-gutter); align-items: center; }
.cs-interlock-copy { min-width: 0; }
.cs-interlock-media { width: 100%;
  aspect-ratio: var(--c-aspect-landscape); overflow: hidden; border-radius: 0; }
.cs-interlock-media .c-image { width: 100%; height: 100%; }
.cs-interlock-caption { display: block;
  margin-bottom: var(--space-eyebrow-to-heading, var(--c-eyebrow-gap)); }
.cs-interlock .c-heading--display { max-width: none; text-align: left;
  /* interlock display de-scales from the brand's display tier (0.3333/0.6 of the
     measured base — ratios are structure, the rem magnitude is the brand's). */
  font-size: clamp(calc(var(--size-display-hero-base) * 0.3333), 4.4cqw,
                   calc(var(--size-display-hero-base) * 0.6));
  line-height: 1.06em; }
@media (max-width: 767px) {
  .cs-interlock { grid-template-columns: 1fr; }
  /* provenance: structural — mobile media recrop ratio (layout geometry, not a
     brand token; coincidentally equals Remote's landscape aspect) */
  .cs-interlock-media { aspect-ratio: 3 / 2; }
}"""


SCAFFOLD_MEDIA_SPLIT_CSS = """.cs-media-split { display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: var(--grid-gutter); align-items: center; }
.cs-media-split-copy { min-width: 0; display: flex; flex-direction: column; gap: 0; }
.cs-media-split-copy .cs-eyebrow-wrap {
  margin-bottom: var(--space-eyebrow-to-heading, var(--c-eyebrow-gap)); }
.cs-media-split-copy .c-heading + .c-paragraph {
  margin-top: var(--space-heading-to-body, var(--c-block-gap)); }
.cs-media-split-copy .c-paragraph + .c-arrow-link,
.cs-media-split-copy .c-heading + .c-arrow-link {
  margin-top: var(--space-body-to-cta, var(--c-block-gap)); }
.cs-media-split-media { min-width: 0; overflow: hidden;
  aspect-ratio: var(--c-aspect-landscape); }
.cs-media-split-media .c-image, .cs-media-split-media .c-image img {
  width: 100%; height: 100%; }
@media (max-width: 767px) { .cs-media-split { grid-template-columns: 1fr; } }"""


# overlay (editorial-harvest-2026-07): ONE positioning context — an in-flow media canvas
# (full-bleed / framed) with grid-registered ABSOLUTE layers over it (panel-on-media,
# straddles, scrim bands, rails, corner cues) and in-flow tucked headings before it.
# Hard-edged, flat fills only (no gradient/shadow/radius); offsets are --baseline /
# --col multiples so every layer registers to the shared grid.
SCAFFOLD_OVERLAY_CSS = """.cs-overlay-sec { position: relative; }
.cs-overlay-sec.cs-ov--bleed { padding-left: 0; padding-right: 0; }
.cs-ov-frame { position: relative;
  /* containment: CONTAINMENT_LAW_CSS (fix3) */ }
/* contain-exempt: overlay BLEED release — the declared edge-to-edge canvas escapes
   the shared measure by design (a release, not a private containment copy). */
.cs-ov--bleed .cs-ov-frame { max-width: none; }
.cs-ov-canvas { position: relative; margin: 0; min-height: calc(48 * var(--baseline)); }
.cs-ov-canvas > .c-image, .cs-ov-canvas > .c-image-ph {
  width: 100%; height: 100%; min-height: inherit; object-fit: cover; }
/* framed (G4): page margins visible on ALL sides — the frame is an inset canvas other
   slots register against (never edge-to-edge, never a border). */
.cs-ov-canvas--framed { margin-inline: auto; }
/* flat surface-toned wash (sanctioned text-on-media mitigation; never a gradient). */
.cs-ov-scrim { position: absolute; inset: 0; z-index: 1; }
.cs-ov-onmedia { position: absolute; inset: 0; z-index: 2; display: flex;
  flex-direction: column; align-items: center; justify-content: center;
  gap: var(--c-block-gap); padding: var(--c-section-pad); text-align: center; }
.cs-ov-onmedia .cs-ov-foot-item { max-width: 46rem; }
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
   always emitted per section (component_vars), so no literal fallback (AS-24).
   0.6 (pass1 2026-07, scale_adherence finding): the old 0.62 landed hubspot's panel
   heading at 49.6px — on NO ladder (measured h1 48 / derived step 52). 0.6 puts the
   stepped-down rank on the brand's own h1 rung for the evidenced display:h1 ratios
   (hubspot 80->48 = h1; remote 46->27.6 ~= h3 28) — quantized new geometry, audited
   per brand by the scale gate. */
.cs-ov-panel .c-heading--display { font-size: calc(0.6 * var(--c-display-size));
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
.cs-band-body { /* containment: CONTAINMENT_LAW_CSS (fix3) */
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
  gap: var(--c-block-gap);
  /* containment: CONTAINMENT_LAW_CSS (fix3; was fid10 here — note the old private
     copy carried a 72rem fallback literal; the law's shared 86rem fallback only
     binds when :root omits --content-measure, which no emitted page does). */ }
/* the prose measure clamps PARAGRAPH slots only (fid6 2026-07): headings, eyebrows
   and actions hug their own content — the old all-items 62ch clamp resolved at the
   wrapper's body size and collapsed centered stacks to a ~500px column. */
.cs-flow-item { max-width: none; }
.cs-flow-item--prose { max-width: var(--space-body-measure, 62ch); }
.cs-flow-media { width: 100%; }
.cs-flow-media .c-image { width: 100%; height: auto; }
/* TESTIMONIAL COMPONENT (AS-76): quote, attribution, and optional compatible
   media stay atomic. The photo-side variant uses the brand panel/hairline/type
   registers; no-photo fallback collapses to one intentional quote card and
   therefore reserves no dead media column. */
.cs-testimonial { width: 100%; display: grid;
  grid-template-columns: minmax(16rem, 0.56fr) minmax(0, 1fr);
  align-items: stretch; background: var(--c-panel, var(--c-paper));
  border: 1px solid var(--c-hairline); }
.cs-testimonial-copy { min-width: 0; display: flex; flex-direction: column;
  justify-content: center; padding: var(--space-panel-padding, 2rem); }
.cs-testimonial-media { min-width: 0; margin: 0; overflow: hidden; }
.cs-testimonial-media .c-image { width: 100%; height: 100%; min-height: 18rem;
  object-fit: cover; display: block; }
.cs-testimonial-quote { margin: 0; }
.cs-testimonial-quote .c-paragraph { font-family: var(--c-font-display);
  font-size: var(--type-h4-size, var(--c-heading-size));
  line-height: var(--type-h4-line-height, var(--c-heading-line)); color: var(--c-ink); }
.cs-testimonial-mark { color: var(--c-accent); font-family: var(--c-font-display);
  /* provenance: structural — decorative pull-quote glyph scale (a device size
     ceiling, not a brand type tier; coincidentally equals a Remote spacing rung) */
  font-size: clamp(2.5rem, 5cqw, 4rem); line-height: 0.8; margin-bottom: 1rem; }
.cs-testimonial .c-person { margin-top: var(--space-quote-to-attribution,
  var(--c-block-gap)); }
.cs-testimonial--quote-card { display: block; max-width: 58rem; }
@media (max-width: 767px) {
  .cs-testimonial { grid-template-columns: 1fr; }
  .cs-testimonial-media .c-image { min-height: 0; aspect-ratio: var(--c-aspect-landscape); }
  .cs-testimonial-copy { padding: var(--space-panel-padding, 1.5rem); }
}
/* logo-strip device (AS-33): a HORIZONTAL row of partner/customer logo images —
   disk-backed extracted assets only (the adapter routes file-less entries to text
   captions instead). Gap rides the brand rhythm. Emphasis treatment (grayscale/…) is
   the STYLE layer's qualitative logoStrip flag (style_density_css), never hardcoded
   here. */
/* provenance: structural logo-strip-geometry — mark height/width caps are device frame
   geometry (same discipline as the nav-logo height cap); a brand chrome token
   (--c-logo-strip-h) wins over the structural default. */
/* inter-mark seam (B8 2026-07): the brand's measured strip rung when authored;
   the uniform block rhythm stays as the fact-less degrade. */
.cs-logo-strip { display: flex; flex-direction: row; flex-wrap: wrap; align-items: center;
  gap: var(--space-strip-gap, var(--c-block-gap)); max-width: none; }
.cs-logo-strip-item { display: flex; align-items: center; }
.cs-logo-strip .c-logo--img { border: none; border-radius: 0; }
.cs-logo-strip .c-logo-img { height: var(--c-logo-strip-h, 2.25rem); width: auto;
  max-width: 10rem; object-fit: contain; }
/* MEASURED ROW SCALE (fid6 2026-07): the row spans the pattern's recorded fraction of
   its container; item flex weights are the marks' real aspect ratios (composer-stamped
   inline), so widths distribute aspect-proportionally and every mark lands the SAME
   height — the measured generous row, not height-capped chips. */
.cs-logo-strip--scaled { flex-wrap: nowrap; width: calc(var(--cs-strip-fraction, 0.5) * 100%);
  /* inter-mark gap = the pattern's measured row gap when recorded (fid7 2026-07),
     then the brand's strip rung (B8), then the uniform rhythm. */
  gap: var(--cs-strip-gap, var(--space-strip-gap, var(--c-block-gap))); }
.cs-logo-strip--scaled .cs-logo-strip-item { min-width: 0; }
.cs-logo-strip--scaled .c-logo--img { width: 100%; }
.cs-logo-strip--scaled .c-logo-img { height: auto; width: 100%; max-width: none; }
/* MEASURED ITEM BOX (fix2 2026-07, mediaScale.item): the strip's uniform mark frame
   as captured — fixed contain-fit boxes at the measured width × height, row hugs its
   own measured run (max-content) and centers in the parent stack; the measured box
   gap rides the same --cs-strip-gap chain the scaled row uses. */
.cs-logo-strip--itembox { flex-wrap: nowrap; width: max-content; max-width: 100%;
  gap: var(--cs-strip-gap, var(--space-strip-gap, var(--c-block-gap))); }
.cs-logo-strip--itembox .cs-logo-strip-item {
  flex: 0 0 var(--cs-strip-item-w); height: var(--cs-strip-item-h); }
.cs-logo-strip--itembox .c-logo--img { width: 100%; height: 100%; }
.cs-logo-strip--itembox .c-logo-img { height: 100%; width: 100%; max-width: none;
  object-fit: contain; }
/* stat band (W4): one horizontal row of stat columns — track count from the authored
   item count, gutter rides the brand's own column rung. Collapses to a 2-up (then
   1-up) grid on narrow frames instead of shrinking the value register. */
.cs-stat-band { display: grid; width: 100%;
  grid-template-columns: repeat(var(--cs-stat-cols, 4), minmax(0, 1fr));
  /* the stat band's column seam is the brand's COLUMN rhythm (spacing law
     stat.column-gap: column-to-column) — a section's registration-grid gutter is
     registration geometry, never this device's rhythm (fix7: the model-authored
     2rem gutter was overriding the brand's 80px rung). Gutter/structural values
     stay the degrade chain for brands without the token. */
  gap: var(--c-block-gap) var(--space-column-to-column, var(--grid-gutter, 3rem)); }
.cs-stat-band-item { min-width: 0; }
@media (max-width: 991px) { .cs-stat-band { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 539px) { .cs-stat-band { grid-template-columns: 1fr; } }
@media (max-width: 767px) { .cs-flow { gap: clamp(1.25rem, 6cqw, 1.75rem); } }"""


# ── INTERACTION-DEVICE scaffolds (P2). Shipped ONLY on pages/sections that render the
# device (AS-37 discipline — gated in scaffold_css / compose_page.build_page on the
# stamped layout hints, so dormant selectors never ride along on other brands' pages).

# Seam-correct marquee (AS-42): two IDENTICAL halves in one max-content flex track;
# the -50% keyframe endpoint lands exactly on the second half's start (each half
# carries a trailing inline gap so the seam spacing equals the inter-item gap). The
# duration var is px/s-constant when the page script measures the half width; the
# inline item-count fallback keeps JS-off renders animating. Reduced-motion pauses at
# the resting offset — the static row IS the animation's t=0 frame.
SCAFFOLD_MARQUEE_CSS = """.cs-marquee { display: block; overflow: hidden; max-width: none;
  /* pin the viewport box to its column (a flex item would otherwise size to the
     max-content track and overflow the page horizontally), then FULL-BLEED it
     (fid2 2026-07): the source marquee runs edge-to-edge, so the band takes the
     section CONTAINER's full inline size and re-centers over the padding via the
     classic 50%-50cqw shift (cq units only — no viewport units in composed CSS). */
  min-width: 0; align-self: stretch;
  width: 100cqw; margin-inline-start: calc(50% - 50cqw); }
.cs-marquee .cs-marquee-track { display: flex; width: max-content;
  animation: cs-marquee-scroll var(--cs-marquee-duration, 30s) linear infinite; }
.cs-marquee .cs-marquee-half { display: flex; flex-wrap: nowrap; align-items: center;
  gap: var(--c-block-gap); padding-inline-end: var(--c-block-gap); }
.cs-marquee .cs-marquee-half .cs-logo-strip-item { flex: none; }
@keyframes cs-marquee-scroll { from { transform: translateX(0); }
  to { transform: translateX(-50%); } }
@media (prefers-reduced-motion: reduce) {
  .cs-marquee .cs-marquee-track { animation: none; } }"""

# Accordion open-state (P2): native exclusive disclosure (<details name=…>, AS-40 —
# the platform enforces single-open; no JS). The ACTIVE item inverts onto the
# treatment's declared surface role via the --acc-* vars scoped inline on .c-acc;
# unset vars keep the idle presentation (transparent, inherited ink). State/chevron/
# panel-height MOTION is NOT in this constant: every details-based disclosure family
# shares ONE motion source (disclosure_motion_css, AS-47) so the FAQ scaffold can
# never fork a static copy of the same mechanic.
SCAFFOLD_ACCORDION_CSS = """.cs-acc-split .cs-acc-col { grid-column: 1 / span 6;
  display: flex; flex-direction: column; justify-content: center; }
.cs-acc-split .cs-split-media { grid-column: 8 / -1; }
/* the media column's mask must FILL its flex parent (fid5 2026-07): the well and
   the media-swap stack are absolutely-layered boxes with no intrinsic width, so a
   content-sized mask collapsed to 0px — the "empty right side" symptom. */
.cs-acc-split .cs-split-media .c-image-mask { flex: 1 1 auto; width: 100%; }
/* MEASURED BAND GEOMETRY (fid9 2026-07, contentShape.deviceGeometry): patterns that
   measured their band draw the source proportions — EQUAL columns at the measured
   gutter (the structural 6|5-of-12 split under-drew the media half), the header
   stack leading the list column (heading wraps at the column measure), a fixed-
   aspect top-aligned media region (a stretch-fill region tracked the list height
   instead of the source's square), and the measured list rhythm. Every rule is
   var/class-gated with the structural presentation as the no-stamp degrade. */
.cs-acc-split--equal { grid-template-columns: repeat(2, minmax(0, 1fr));
  column-gap: var(--cs-acc-colgap, var(--grid-gutter, 0px));
  max-width: var(--cs-acc-span, none); margin-inline: auto; }
.cs-acc-split--equal .cs-acc-col { grid-column: 1; }
.cs-acc-split--equal .cs-split-media { grid-column: 2; }
.cs-acc-col--lead { justify-content: flex-start; }
.cs-acc-col--lead > .cs-split-intro { margin-bottom: var(--cs-acc-rowgap, 3.5rem); }
.cs-split-media--top { align-items: flex-start; }
.cs-acc-split .cs-split-media--top .c-image-mask {
  aspect-ratio: var(--cs-acc-media-aspect, auto); height: auto; }
.c-acc-trigger { min-height: var(--cs-acc-trig-minh, auto); }
.c-acc-item + .c-acc-item { margin-top: var(--cs-acc-itemgap, 0); }
.c-acc { display: flex; flex-direction: column; width: 100%; }
.c-acc-item { border-bottom: 1px solid var(--c-hairline); }
.c-acc-trigger { display: flex; align-items: center; justify-content: space-between;
  gap: 1rem; padding: calc(3 * var(--baseline)) calc(3 * var(--baseline));
  cursor: pointer; list-style: none;
  /* family/weight/size ride the section-scoped brand vars — a bare <summary> would
     otherwise inherit the UA default (the var only resolves inside #sec-N scopes) */
  font-family: var(--c-font-body); font-weight: 500;
  font-size: var(--c-control-size, 1rem); }
.c-acc-trigger::-webkit-details-marker { display: none; }
.c-acc-chev { display: inline-flex; flex: none; }
.c-acc-item[open] > .c-acc-trigger .c-acc-chev { transform: rotate(180deg); }
.c-acc-item:not([open]):hover { background: var(--acc-hover-bg, transparent); }
.c-acc-item[open] { background: var(--acc-active-bg, transparent);
  color: var(--acc-active-ink, inherit); --c-ink: var(--acc-active-ink, inherit);
  border-radius: var(--radius-card, 0); border-color: transparent; }
@media (prefers-reduced-motion: reduce) {
  .cs-acc-media-item { transition: none; } }
.c-acc-panel { padding: 0 calc(3 * var(--baseline)) calc(3 * var(--baseline)); }
.c-acc-panel .c-paragraph { color: inherit; }
/* section action foot (W8): the split's declared cta closes the LIST column —
   left-anchored per the split grammar, never dropped. RUNG ATTRIBUTION (spacing
   remediation B7 2026-07): list→foot is a BLOCK-level row seam (the brand's
   content→ctasAfterContent rows all ride the one block rhythm rung), not the
   intra-stack body→cta rung; body→cta survives only as the degrade chain. */
.cs-acc-foot { margin-top: var(--space-block-to-block,
    var(--space-body-to-cta, calc(3 * var(--baseline))));
  align-self: flex-start; }
/* per-row icon tile (fid2 2026-07): the brand's own product-family mark leads the
   trigger; contained, never cropped. */
.c-acc-icon { width: 1.75rem; height: 1.75rem; object-fit: contain; flex: none;
  background: none; }
.c-acc-trigger .c-acc-label { flex: 1 1 auto; }
/* active-item go-affordance (treatment: affordance circle-arrow): a round chip on
   the active panel's own paper/ink — vars, never literals. */
.c-acc-go { display: inline-flex; align-items: center; justify-content: center;
  width: 2.5rem; height: 2.5rem; border-radius: 50%; margin-top: calc(2 * var(--baseline));
  background: var(--c-paper); color: var(--acc-active-bg, var(--c-ink)); }
.c-acc-panel .c-acc-go { margin-inline-start: 0; }
/* honest MEDIA WELL degrade (fid2 2026-07): the measured light well renders as the
   counterweight when no asset is bound — brand raised-surface var + card radius. */
.cs-acc-well { width: 100%; height: 100%; min-height: 24rem;
  background: var(--surface-surface-raised, var(--c-paper));
  border-radius: var(--radius-card, 0); }
/* PER-ITEM MEDIA SWAP (fid5 2026-07): items binding their own media (section-copy
   items[].media) stack as layers over the honest well; the ACTIVE item's layer shows
   (pairing rules generated per index by device_scaffold_css — :has() on the open
   details), crossfading on the brand's structural-collapse tier so the well swaps
   with the disclosure. Items without media leave no layer: opening one shows the
   bare well (the fid2 degrade). Browsers without :has() keep the server-rendered
   resting state (the @supports-gated .is-active fallback below). */
.cs-acc-media { position: relative; width: 100%; height: 100%; min-height: 24rem; }
.cs-acc-media .cs-acc-well { position: absolute; inset: 0; min-height: 0; }
.cs-acc-media-item { position: absolute; inset: 0; width: 100%; height: 100%;
  object-fit: cover; border-radius: var(--radius-card, 0); opacity: 0;
  /* crossfade rides the brand aliases BARE (AS-47): unresolved vars invalidate the
     declaration at computed-value time — motion-less brands swap instantly, never
     on an invented 200ms. */
  transition: opacity var(--c-motion-base) var(--c-ease); }
.cs-acc-media-item.c-acc-media--contain { object-fit: contain; }
@supports not selector(:has(a)) {
  .cs-acc-media-item.is-active { opacity: 1; } }
@media (max-width: 767px) {
  .cs-acc-split--equal { grid-template-columns: minmax(0, 1fr); }
  .cs-acc-split .cs-acc-col, .cs-acc-split .cs-split-media { grid-column: 1; } }"""

# Edge-cut carousel statics (P2): the module track becomes a native horizontal
# scroller whose right edge bleeds past the section padding to the viewport edge, so
# the last visible card CLIPS (the capture's carousel affordance). The left content
# edge stays registered to the shared measure. Cards take the plate anatomy (brand
# panel surface + card radius vars — no literals).
# card PLATE + PERSON-ROW anatomy (shared by the edge-cut track and — fid2 2026-07 —
# the contained card grid of any brand whose card device rides a Container surface;
# see card_panel_role). Values are the brand's own panel/radius vars, never literals.
SCAFFOLD_CARD_PLATE_CSS = """.cs-module--plate { background: var(--c-panel); color: var(--c-panel-ink);
  --c-ink: var(--c-panel-ink); --c-accent: var(--c-panel-ink);
  /* re-scope the MUTED ink to the panel too — body/caption text uses
     --c-ink-muted, not --c-ink; without this a plate that sits after an inverse
     section kept the surrounding (near-white) muted ink and rendered
     white-on-white on its own light panel (product-launch text-contrast, 2026-07).
     Matches the cs-panel / band-panel devices which already re-scope it. */
  --c-ink-muted: var(--c-panel-ink-muted, var(--c-panel-ink));
  --c-hairline: var(--c-panel-hairline);
  /* plate inset rides the brand's measured panel-padding token when authored
     (fid6 2026-07); the 4-baseline structural default is unchanged without it. */
  --c-plate-pad: var(--space-panel-padding, calc(4 * var(--baseline)));
  border-radius: var(--radius-card, 0); padding: var(--c-plate-pad); }
/* FULL-BLEED MEDIA WELL (fid6 2026-07): a plated module's leading media frame runs
   flush to the card's top + side edges (rounded top corners only — the classic card
   anatomy the capture shows: media well INSIDE the plate, bleeding to its edges);
   mark media (company logos on quote cards) keeps the inset mark row. */
.cs-module--plate > .cs-module-media:first-child:not(.cs-module-media--mark) {
  margin: calc(-1 * var(--c-plate-pad)) calc(-1 * var(--c-plate-pad)) 0;
  width: calc(100% + 2 * var(--c-plate-pad));
  border-radius: var(--radius-card, 0) var(--radius-card, 0) 0 0; }
.cs-module--plate > .cs-module-media:first-child:not(.cs-module-media--mark) + * {
  /* the seam is the plate pad BY CONSTRUCTION (the negative margin above swallowed
     the padding) — subtract the module's own flex gap so it never double-counts
     (anatomy/quote stacks run gap:0, plain plates 0.9rem; spacing audit
     card.media-to-content = panel-padding either way). */
  margin-block-start: calc(var(--c-plate-pad) - var(--cs-module-gap, 0rem)); }
.c-person { display: flex; align-items: center; gap: 0.85rem; margin-top: auto;
  border-top: 1px solid var(--c-hairline); padding-top: calc(2 * var(--baseline)); }
.c-person-avatar { width: var(--c-avatar-size, 3rem); height: var(--c-avatar-size, 3rem);
  border-radius: 50%; object-fit: cover; flex: 0 0 auto; }
.c-person-meta { display: flex; flex-direction: column; gap: 0.15em; min-width: 0; }
.c-person-name { font-family: var(--c-font-body);
  font-weight: var(--weight-control-text, var(--c-heading-weight));
  font-size: var(--c-control-size); color: var(--c-ink); }
.c-person-role { font-family: var(--c-font-body);
  font-size: calc(var(--c-control-size) * 0.9); color: var(--c-ink-muted); }
.cs-module--plate { display: flex; flex-direction: column; }
/* DECLARED mark row (fit: mark) on the contained grid — device-frame glyph height,
   same discipline as the edge-cut mark row (the edgecut scope keeps its own rule). */
.cs-modules .cs-module-media--mark { display: flex; align-items: center;
  justify-content: flex-start; height: 2.25rem; }
.cs-modules .cs-module-media--mark .c-image { width: auto; height: 100%;
  max-width: 12rem; object-fit: contain; }
/* HEADING-ROW mark placement (brand card device slots.icon.placement: heading-row):
   glyph seated BESIDE the heading in one flex row at the icon slot's measured size;
   the row itself rides the anatomy ladder like the stacked figure it replaces. */
.cs-modules .cs-module-headrow { display: flex; align-items: center; gap: 1rem; }
.cs-modules .cs-module-headrow .cs-module-media--mark,
.cs-modules--edgecut .cs-module-headrow .cs-module-media--mark {
  height: var(--cs-headrow-mark, 1.5rem); flex: 0 0 auto; width: auto; }
.cs-module-headrow .c-heading { margin: 0; flex: 1 1 auto; }"""

SCAFFOLD_EDGECUT_CSS = """.cs-edgecut { overflow-x: auto; scrollbar-width: none;
  margin-inline-end: calc(-1 * var(--c-section-pad-x, 0rem));
  /* contain-exempt: DERIVED inset — the released rail's left edge registers to the
     shared measure via this calc (containment math, not a private max-width copy) */
  padding-inline-start: max(0rem, calc((100% - var(--content-measure, 86rem)) / 2)); }
.cs-edgecut::-webkit-scrollbar { display: none; }
/* measured rail chrome (fix1 2026-07: `controls` fact on the edge-cut treatment) —
   round paper prev/next pair at the rail edges; ships only where the fact composed. */
.cs-edgecut-wrap { position: relative; }
.cs-edgecut-arrow { /* provenance: structural — round control geometry (999px pill cap)
  + neutral lift shadow; paddle paint itself rides brand panel/ink vars */
  position: absolute; top: 50%; transform: translateY(-50%);
  z-index: 2; width: 3rem; height: 3rem; border-radius: 999px; border: 0;
  background: var(--c-panel, var(--c-paper)); color: var(--c-panel-ink, var(--c-ink));
  box-shadow: 0 1px 4px rgb(0 0 0 / 0.12); display: inline-flex; align-items: center;
  justify-content: center; cursor: pointer; padding: 0; }
.cs-edgecut-arrow--prev { left: calc(1 * var(--baseline)); }
.cs-edgecut-arrow--next { right: calc(1 * var(--baseline)); }
.cs-edgecut-pauserow { display: flex; justify-content: center;
  margin-top: calc(3 * var(--baseline)); }
.cs-edgecut-pause { /* provenance: structural — round control geometry (999px pill cap) */
  width: 2.5rem; height: 2.5rem; border-radius: 999px;
  border: 1px solid var(--c-hairline); background: var(--c-paper);
  color: var(--c-ink); display: inline-flex; align-items: center;
  justify-content: center; cursor: pointer; padding: 0; }
.cs-modules--edgecut { display: flex; flex-wrap: nowrap; align-items: stretch;
  /* contain-exempt: edge-cut RELEASE — the track deliberately escapes the law's
     cap/centering (its left inset re-registers via the .cs-edgecut derived pad) */
  max-width: none; margin-inline: 0; column-gap: normal;
  gap: var(--cs-edgecut-gap, calc(4 * var(--baseline))); }
.cs-modules--edgecut > .cs-module, .cs-modules--edgecut > .cs-module:nth-child(odd),
.cs-modules--edgecut > .cs-module:nth-child(even) {
  /* measured card box (--cs-edgecut-card-w, deviceGeometry) or structural clamp */
  flex: 0 0 var(--cs-edgecut-card-w, clamp(20rem, 32cqw, 30rem));
  grid-column: auto; margin-block-start: 0; }
.cs-modules--edgecut .cs-module-media--mark { display: flex; align-items: center;
  justify-content: flex-start; height: 2.25rem; }
.cs-modules--edgecut .cs-module-media--mark .c-image { width: auto; height: 100%;
  max-width: 12rem; object-fit: contain; }
@media (max-width: 767px) {
  .cs-modules--edgecut { gap: 1.25rem; }
  .cs-modules--edgecut > .cs-module { flex-basis: min(86cqw, 24rem); } }
""" + SCAFFOLD_CARD_PLATE_CSS


SCAFFOLD_PANELCAR_CSS = """/* SPLIT-PANEL CAROUSEL statics (fix1 2026-07 item-6): slide 1 visible, siblings
   hidden; round prev/next at the row edges; dot rail below. All chrome rides brand
   vars (hairline/ink/control radius); ships only where the device composed. */
.cs-panelcar { position: relative; margin-top: calc(6 * var(--baseline)); }
.cs-panelcar-grid { display: grid; align-items: center;
  /* measured illustration share (--cs-panelcar-media-frac, pattern mediaScale)
     sizes the media column; the copy column takes the rest. Even split default. */
  grid-template-columns: minmax(0, 1fr)
    minmax(0, calc(var(--cs-panelcar-media-frac, 0.5) * 100%));
  column-gap: var(--grid-gutter, calc(4 * var(--baseline))); }
.cs-panelcar-slide[hidden] { display: none; }
.cs-panelcar-copy { display: flex; flex-direction: column;
  gap: var(--c-block-gap, calc(3 * var(--baseline))); }
.cs-panelcar-media .c-image-mask { width: 100%; }
.cs-panelcar-media img { width: 100%; height: auto; object-fit: contain; }
.cs-panelcar-arrow { /* provenance: structural — round control geometry (999px pill cap) */
  position: absolute; top: 50%; transform: translateY(-50%);
  z-index: 2; width: 3rem; height: 3rem; border-radius: 999px;
  border: 1px solid var(--c-hairline); background: var(--c-paper);
  color: var(--c-ink); display: inline-flex; align-items: center;
  justify-content: center; cursor: pointer; padding: 0; }
.cs-panelcar-arrow--prev { left: calc(-1 * var(--baseline)); }
.cs-panelcar-arrow--next { right: calc(-1 * var(--baseline)); }
.cs-panelcar-arrow[disabled] { opacity: 0.4; cursor: default; }
.cs-panelcar-dots { display: flex; justify-content: center;
  gap: calc(1.5 * var(--baseline)); margin-top: calc(5 * var(--baseline)); }
/* RAIL-NAV variant (fix3, treatment controls.placement: rail): prev/next sit ON the
   dot row below the slides — prev flush at the container's left edge, next at its
   right, dots centered between (the captured bottom-rail chrome; the floated
   mid-slide paddles collided with the copy column on contained sections). Control
   box rides the measured size fact (--cs-panelcar-arrow-size); rules are inert
   without the variant class — fact-less carousels keep the structural paddles. */
.cs-panelcar--railnav .cs-panelcar-nav { display: grid;
  grid-template-columns: auto 1fr auto; align-items: center;
  margin-top: calc(5 * var(--baseline)); }
.cs-panelcar--railnav .cs-panelcar-arrow { position: static; transform: none;
  width: var(--cs-panelcar-arrow-size, 3rem);
  height: var(--cs-panelcar-arrow-size, 3rem); }
.cs-panelcar--railnav .cs-panelcar-dots { margin-top: 0; }
.cs-panelcar-dot { /* provenance: structural — round dot geometry (999px pill cap) */
  width: 0.625rem; height: 0.625rem; border-radius: 999px;
  border: 0; padding: 0; cursor: pointer;
  background: color-mix(in srgb, var(--c-ink) 25%, transparent); }
.cs-panelcar-dot[aria-current="true"] { background: var(--c-ink); }
@media (max-width: 767px) {
  .cs-panelcar-grid { grid-template-columns: minmax(0, 1fr); row-gap: calc(3 * var(--baseline)); }
  .cs-panelcar-arrow { display: none; } }
"""

SCAFFOLD_TABS_CSS = """/* TAB DEVICE (fix1 2026-07 item-9): WAI-ARIA APG tablist over a bordered case
   card — photo column | quote column, stat pair on a vertical-rule row below.
   Active tab = weight + accent underline; hover = subtle wash (the captured
   states). Every value rides brand vars; ships only where the device composed. */
.cs-tabs { /* containment: CONTAINMENT_LAW_CSS (fix3) */ }
.cs-tablist { display: flex; justify-content: center; align-items: baseline;
  gap: calc(1 * var(--baseline)); margin-bottom: calc(4 * var(--baseline)); }
.cs-tab { background: none; border: 0; cursor: pointer;
  font-family: var(--c-font-body); font-size: var(--c-control-size, 0.875rem);
  font-weight: var(--weight-control-text, var(--weight-body)); color: var(--c-ink-muted, var(--c-ink));
  padding: calc(1 * var(--baseline)) calc(1.5 * var(--baseline));
  border-bottom: 2px solid transparent; }
.cs-tab:hover { background: color-mix(in srgb, var(--c-ink) 5%, transparent); }
.cs-tab[aria-selected="true"] { font-weight: var(--weight-h1); color: var(--c-ink);
  border-bottom-color: var(--cs-tab-active-rule, var(--c-accent)); }
.cs-tabpanel[hidden] { display: none; }
.cs-tabcard { border: 1px solid var(--c-hairline);
  border-radius: var(--radius-card, 0); background: var(--c-panel, var(--c-paper));
  padding: calc(4 * var(--baseline));
  display: grid; column-gap: calc(5 * var(--baseline));
  row-gap: calc(4 * var(--baseline));
  grid-template-columns: minmax(0, calc(var(--cs-tabs-media-frac, 0.45) * 100%)) minmax(0, 1fr); }
.cs-tabcard-media .c-image-mask { width: 100%; height: 100%; }
.cs-tabcard-media img { width: 100%; height: 100%; object-fit: cover;
  border-radius: var(--radius-media, var(--radius-small, 0)); }
.cs-tabcard-body { display: flex; flex-direction: column; justify-content: center;
  gap: calc(2 * var(--baseline)); }
.cs-tabcard-stats { grid-column: 1 / -1; display: grid;
  grid-template-columns: repeat(auto-fit, minmax(0, 1fr)); align-items: start; }
.cs-tabcard-stat { text-align: center;
  padding-inline: calc(3 * var(--baseline)); display: flex; flex-direction: column;
  align-items: center; gap: calc(0.5 * var(--baseline)); }
.cs-tabcard-stat + .cs-tabcard-stat { border-left: 1px solid var(--c-hairline); }
@media (max-width: 767px) {
  .cs-tabcard { grid-template-columns: minmax(0, 1fr); }
  .cs-tabcard-stats { grid-template-columns: minmax(0, 1fr); }
  .cs-tabcard-stat + .cs-tabcard-stat { border-left: 0;
    border-top: 1px solid var(--c-hairline); padding-top: calc(2 * var(--baseline)); } }
"""

SCAFFOLD_HEADRAIL_CSS = """/* SECTION HEADROW RAIL (fix1 2026-07 item-8): leading chip/pill — rule — trailing
   action; the split intro (heading LEFT / body RIGHT) rides the same stamp family.
   Rule style (dotted/solid) is the treatment's own vocabulary; chip is the brand's
   paper surface. Ships only where a pattern stamped the device.
   RECIPE FACTS (fix2): a recipe-bound rail stamps its variant's measured boxes as
   inline --cs-rail-* vars; every declaration below falls back to the fix1
   structural default, so recipe-less rails render byte-identically. The rail also
   obeys the shared container law (it previously escaped the measure and ran the
   full padded width while its intro capped — the fix2 overflow). */
.cs-headrail { display: flex; align-items: center;
  /* rail->heading seam measured ~24px on the captured header bands (crops
     section-05/07: pill bottom to heading top), not the 48px section default */
  gap: var(--cs-rail-item-gap, calc(3 * var(--baseline)));
  margin-bottom: var(--cs-rail-gap-below, calc(3 * var(--baseline)));
  /* column-flex parents anchor children left (content-hugging) — the rail must
     span the measure or its flex rule collapses to 0 width; the span itself
     (width + cap + centering) is CONTAINMENT_LAW_CSS (fix3) */
  align-self: stretch; }
.cs-headrail-rule { flex: 1 1 auto; border: 0;
  border-top: 1px solid var(--c-hairline); margin: 0; }
.cs-headrail-rule--dotted { border-top-style: dotted; }
.cs-headrail-chip { /* provenance: structural — round chip geometry (999px pill cap);
   recipe rails ride their measured box/radius/border via the --cs-rail-chip-* vars */
  display: inline-flex; align-items: center; justify-content: center;
  flex: none; width: var(--cs-rail-chip-size, 3rem);
  height: var(--cs-rail-chip-size, 3rem);
  border-radius: var(--cs-rail-chip-radius, 999px);
  border: var(--cs-rail-chip-border, 0);
  background: var(--cs-rail-kicker-bg, var(--c-paper)); }
.cs-headrail-chip img { width: var(--cs-rail-chip-icon, 1.5rem);
  height: var(--cs-rail-chip-icon, 1.5rem); object-fit: contain; }
/* bordered rail PILL (the leading label boxed in a hairline pill): the label
   renders as authored — the pill register is its own device, not the page
   eyebrow register (case/tracking tokens stay on bare eyebrows). */
.cs-headrail-pill { display: inline-flex; align-items: center; flex: none;
  gap: var(--cs-rail-pill-gap, calc(1 * var(--baseline)));
  border: 1px solid var(--c-hairline);
  border-radius: var(--cs-rail-pill-radius, var(--radius-small, 0));
  padding: var(--cs-rail-pill-pad,
           calc(0.5 * var(--baseline)) calc(1.25 * var(--baseline)));
  background: var(--cs-rail-kicker-bg, transparent); }
.cs-headrail-pill img { width: var(--cs-rail-pill-icon, 1rem);
  height: var(--cs-rail-pill-icon, 1rem); object-fit: contain; }
.cs-headrail-pill .c-eyebrow { margin: 0; text-transform: none;
  letter-spacing: normal; color: var(--c-ink); }
.cs-intro-split { display: grid; align-items: start;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  column-gap: var(--grid-gutter, calc(4 * var(--baseline)));
  margin-bottom: calc(6 * var(--baseline));
  align-self: stretch; width: 100%; }
/* a header-only section (rail + split intro and nothing after) must not carry the
   dangling seam — the band below completes the unit (padding-bottom-none bands). */
.cs-intro-split:last-child, .cs-headrail:last-child { margin-bottom: 0; }
.cs-intro-split .c-header, .cs-intro-split .c-heading { margin-bottom: 0; }
.cs-intro-split > .c-paragraph { justify-self: stretch; }
@media (max-width: 767px) {
  .cs-intro-split { grid-template-columns: minmax(0, 1fr);
    row-gap: calc(2 * var(--baseline)); } }
"""

SCAFFOLD_SIDERAIL_CSS = """/* SIDE-RAIL CARD COUNTERWEIGHT (fix1 2026-07 item-7): the copy rail (intro +
   actions) holds the LEFT column; the module grid is the counterweight beside it.
   Ships only where a pattern declares alignment.counterweight: cards. */
.cs-siderail { display: grid; align-items: start;
  grid-template-columns: minmax(0, 35fr) minmax(0, 65fr);
  column-gap: var(--grid-gutter, calc(4 * var(--baseline)));
  /* containment: CONTAINMENT_LAW_CSS (fix3; was the fix2 private copy here) */ }
.cs-siderail > .cs-siderail-copy { display: flex; flex-direction: column;
  gap: var(--c-block-gap, calc(3 * var(--baseline))); position: sticky;
  top: calc(4 * var(--baseline)); }
/* an IN-COLUMN headrail (recipe span: column, fix2): the column's flex gap already
   opens the seam — the rail's own margin tops it up (or pulls it back) so the
   TOTAL seam equals the recipe's measured railToHeading fact. */
.cs-siderail-copy > .cs-headrail { margin-bottom:
  calc(var(--cs-rail-gap-below, calc(3 * var(--baseline))) - var(--c-block-gap, 0rem)); }
.cs-siderail .cs-modules-intro { margin-bottom: 0; }
.cs-siderail .cs-modules-actions { margin-top: 0; justify-content: flex-start; }
.cs-siderail .cs-modules { margin-top: 0; }
@media (max-width: 1023px) {
  .cs-siderail { grid-template-columns: minmax(0, 1fr);
    row-gap: calc(4 * var(--baseline)); }
  .cs-siderail > .cs-siderail-copy { position: static; } }
"""

_ARCHETYPE_SCAFFOLD = {
    "stack": SCAFFOLD_HERO_CSS,          # the hero stack; conversion stack uses its own block below
    "collage": SCAFFOLD_COLLAGE_CSS,
    "split": SCAFFOLD_SPLIT_CSS,
    "stack-fullbleed": SCAFFOLD_GALLERY_CSS,
    "cards": SCAFFOLD_CARDS_CSS,
    "media-split": SCAFFOLD_MEDIA_SPLIT_CSS,
    # Interlock can safely degrade at render time, so its CSS bundle includes the
    # ordinary split target as part of the device contract.
    "interlock": SCAFFOLD_INTERLOCK_CSS + "\n" + SCAFFOLD_MEDIA_SPLIT_CSS,
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
    if archetype == "stack":
        # the `stack` dispatcher serves BOTH the hero bookend and the conversion CTA —
        # disambiguate through scaffold_key so this stays in lockstep with the composer
        # dispatch (sysfix 2026-07: a button-bound conversion resolved "hero" here
        # while compose_stack routed it to the conversion composer).
        keys.append("conversion" if scaffold_key(layout) == "conversion" else "hero")
    if archetype:
        keys.append(archetype)
    if pattern is not None and pattern.archetype_ref:
        keys.append(str(pattern.archetype_ref).lower())
    return keys


def _header_grammar_anchor(doc, layout) -> dict | None:
    """The brand's CONTEXTUAL header-alignment grammar (brand-schema §4.4b, AS-49):
    ``layoutGrammar.headerContext`` maps the section's LAYOUT CONTEXT — a column of a
    split row vs a header standing alone atop a stacked/grid section — to the brand's
    observed default anchor. Returns a resolved stance dict (source "brand") or None
    when the brand authored no grammar / no rung covers this context. Chrome
    archetypes (nav/footer) and uncorroborated contexts never consult it."""
    g = ((doc or {}).get("layoutGrammar") or {}).get("headerContext") \
        if isinstance(doc, dict) else None
    if not isinstance(g, dict) or not g:
        return None
    arch = ((layout or {}).get("archetype") or "stack").lower()
    explicit_context = str((layout or {}).get("_headerContext") or "")
    if explicit_context in ("splitColumn", "standaloneStack"):
        key = explicit_context
    elif arch in ("split", "media-split"):
        key = "splitColumn"
    elif arch in ("stack", "cards", "grid", "stack-fullbleed"):
        key = "standaloneStack"
    else:
        return None
    node = g.get(key)
    if not isinstance(node, dict):
        return None
    anchor = ll.normalize_anchor(node.get("anchor"),
                                 where=f"layoutGrammar.headerContext.{key}")
    if not anchor:
        return None
    return {"anchor": anchor, "source": "brand",
            "counterweight": node.get("counterweight")}


def resolve_alignment(layout, pattern=None, style_ctx=None, doc=None,
                      honor_curation=True) -> dict | None:
    """THE single alignment resolution chain (anti-ai-slop.md AS-18 + AS-49):

        section-explicit ``alignment`` > pattern ``curation`` (generation lanes) >
        pattern ``contentShape.alignment`` >
        brand ``layoutGrammar.headerContext`` (contextual grammar, fid11) >
        style role default (StyleStructure.align_for)

    ``honor_curation`` selects the lane semantics (brand-schema §4.4c): GENERATION
    lanes (composed catalog, event, wildcard, preview demos) pass True — a curated
    ``follow-grammar`` ruling retires the pattern's dissenting fact and hands the
    decision to the brand grammar. The REPLICA lane passes False: it rebuilds the
    source 1:1 and its gate scores against the source, so the measured pattern fact
    stays that lane's truth.

    Never a silent CSS fall-through: every resolved stance carries its winning SOURCE
    ("section" | "curation" | "pattern" | "brand" | "style"), stamped on the section
    wrapper as ``data-align-source`` (mirrors data-pattern). Out-of-enum anchors warn
    loudly (via ``ll.normalize_anchor``) and fall through to the next layer
    EXPLICITLY. Returns ``{"anchor", "source", "counterweight"}`` or None only when NO
    layer declares a stance (e.g. an unstyled legacy render — behavior unchanged)."""
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
    # 1.5 CURATION (brand-schema §4.4c): a curator's recorded resolution of a
    # pattern-fact-vs-grammar dissent (exactly what the C18 advisory surfaces).
    # `follow-grammar` RETIRES the pattern's dissenting fact for generation lanes:
    # the decision falls to the brand grammar (layer 2.5); if no grammar rung covers
    # this context the chain still skips the retired fact and lands on the style
    # layer — reverting silently to a look the curator rejected would be worse.
    curated_follow_grammar = False
    if honor_curation and pattern is not None:
        _cf = getattr(pattern, "curation_for", None)  # duck-typed pattern stubs lack it
        cur = _cf("alignment") if callable(_cf) else None
        if cur and str(cur.get("resolve")) == "follow-grammar":
            curated_follow_grammar = True
            ga = _header_grammar_anchor(doc, layout)
            if ga:
                return {**ga, "source": "curation"}
    # 2. pattern contentShape.alignment (brand-schema §4.4) — SKIPPED for genre-
    # archetype sections (spec/archetype-library.md): the seeded pattern's alignment
    # is a structural fact about the SOURCE's own section, and a section instantiating
    # a genre skeleton takes structure from the archetype + brand grammar, not from
    # the pattern it borrowed treatments from (style-invariant / structure-variable).
    # The pattern keeps donating treatments/knobs; only this structural layer yields.
    if pattern is not None and not curated_follow_grammar \
            and not layout.get("archetypeRef"):
        pa = pattern.alignment
        if pa:
            return {"anchor": pa["anchor"], "source": "pattern",
                    "counterweight": pa.get("counterweight")}
    # 2.5 brand HEADER-CONTEXT GRAMMAR (brand-schema §4.4b, AS-49): the brand's own
    # contextual default — beneath explicit facts (section/pattern stay supreme,
    # fid10's resolution unchanged above), above the style layer. Exactly what a
    # newly GENERATED section needs: a fact-less header inherits the brand's captured
    # alignment grammar instead of a scaffold-hardcoded or style-guessed anchor.
    ga = _header_grammar_anchor(doc, layout)
    if ga:
        return ga
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
        # out-of-enum value). Flow markup becomes a wrapping space-between row — so the
        # relational-ladder COLUMN mechanic (gap:0 + block-start margins, AS-48) must
        # not apply: restore the row gap and zero the stacked margins (per-#sec-N
        # specificity beats the page-level ladder rules).
        return (f"{sel} .cs-flow {{ flex-direction: row; flex-wrap: wrap; "
                f"justify-content: space-between; align-items: baseline; max-width: none; "
                f"gap: var(--c-block-gap); }}\n"
                f"{sel} .cs-flow > * + * {{ margin-block-start: 0; }}\n"
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
        # the pack REACHES overlay-panel interiors on purpose (fix5 2026-07, the
        # mixed-alignment header defect): the panel IS the section's header stack,
        # and this resolved anchor is the grammar's answer FOR that stack (the
        # archetype anatomy stamps its header context — splitColumn here — before
        # resolution). Exempting the panel just re-exposes the page-level style
        # density default (.c-heading--display center/auto), which is how a lone
        # centered heading sat over left siblings. One owner: this #sec-N pack.
        f"{sel} .c-heading--display {{ text-align: {text}; margin-inline: {margin}; }}",
        # generic-flow (the SCAFFOLD_FLOW_CSS hardcoded flex-start is DELETED — the
        # resolved value is emitted here instead; AS-18)
        f"{sel} .cs-flow {{ align-items: {flex}; text-align: {text}; }}",
        # action rows: wrapped lines follow the anchor too (the row itself is a
        # flex child, so align-items above places the ROW; this places its lines)
        f"{sel} .cs-hero-actions {{ justify-content: {flex}; }}",
        # the hero mark rail + quiet link rail (fix6) follow the action row's stance
        f"{sel} .cs-hero-rail .cs-logo-strip {{ justify-content: {flex}; }}",
        f"{sel} .cs-hero-links {{ justify-content: {flex}; }}",
        # gallery band (stack-fullbleed): intro header + caption honor the anchor
        f"{sel} .cs-gallery-intro {{ text-align: {text}; }}",
        f"{sel} .cs-gallery-caption {{ text-align: {text}; }}",
        # cards / interlock intros (+ their closing action row — AS-18: an anchor
        # never silently no-ops on an archetype's markup)
        f"{sel} .cs-modules-intro {{ text-align: {text}; }}",
        # info-band/comparison headers are structurally independent from the content
        # split beneath them; their adapter stamps standaloneStack so this selector
        # realizes the captured context grammar rather than inheriting split-column.
        f"{sel} .cs-split-intro {{ align-items: {flex}; text-align: {text}; }}",
        f"{sel} .cs-split-intro .cs-hero-actions {{ justify-content: {flex}; }}",
        f"{sel} .cs-modules-actions {{ justify-content: {flex}; }}",
        # overlay: in-flow foot cluster + tucked headrow honor the anchor
        f"{sel} .cs-ov-foot {{ align-items: {flex}; text-align: {text}; }}",
        # banded: the bottom band's body column
        f"{sel} .cs-band-body {{ align-items: {flex}; text-align: {text}; }}",
    ]
    if anchor == "centered":
        parts += [
            # conversion/ruled-list stacks are centered by their own scaffold, but a
            # resolved centered anchor ALSO declares it here (sysfix 2026-07): the
            # anchor must cover `.cs-conversion` markup even when a dispatch gap ships
            # a different scaffold (AS-18 — an anchor never silently no-ops on an
            # archetype's markup). Statement/quote splits collapse to SYMMETRIC spans
            # (AS-19: media no longer sits 6/-1 under centered text) and the text
            # column centers.
            f"{sel} .cs-conversion {{ align-items: center; text-align: center; }}",
            f"{sel} .cs-conversion-sec {{ justify-content: center; }}",
            # measure-capped intro header RUNS (fid11 header-measure, capped on the
            # intro's children — fid12) center as BLOCKS inside the full-measure intro
            f"{sel} .cs-modules-intro > * {{ margin-inline: auto; }}",
            f"{sel} .cs-split-intro > * {{ margin-inline: auto; }}",
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
            # container law (fid10): the side anchor re-anchors the stack INSIDE the
            # shared content spine — the column grows to the spine (still centered by
            # the scaffold) and the TEXT keeps the stack measure, so the section rides
            # the same container every other scaffold does. flex-end/flex-start makes
            # every child hug content, so only text elements need the measure cap.
            # contain-exempt: side-anchor RELEASE — the stack box grows from its
            # 46rem measure to the shared spine; the measure cap moves to the text.
            f"{sel} .cs-conversion {{ align-items: flex-end; text-align: right;"
            f" max-width: var(--content-measure, 86rem); }}",
            f"{sel} .cs-conversion .c-heading {{ max-width: var(--cs-stack-measure, 46rem); }}",
        ]
    elif anchor == "left":
        parts += [
            # container law (fid10): same spine discipline as `right` — the old
            # `justify-content: flex-start` pinned the 46rem column to the section's
            # PADDING edge (spacing-audit off-ladder centering: gutters 40px/664px
            # where the source anchors copy at the page container's edge).
            # contain-exempt: side-anchor RELEASE (mirror of `right` above).
            f"{sel} .cs-conversion {{ align-items: flex-start; text-align: left;"
            f" max-width: var(--content-measure, 86rem); }}",
            f"{sel} .cs-conversion .c-heading {{ max-width: var(--cs-stack-measure, 46rem); }}",
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
        # a DECLARED gutter also drives the module grid's wrap-row rhythm (fid6
        # 2026-07): uniform N-up card grids ride the same measured gap both axes.
        decls.append(f"--grid-gutter-row: {gutter};")
        # …and the card grid's own column rung (spacing remediation B6 2026-07):
        # .cs-modules--cols prefers the brand's grid-gap token over the page split
        # gutter, so a section-declared gutter must outrank the token too.
        decls.append(f"--grid-gutter-col: {gutter};")
    side = layout.get("_floatSide")
    if side in ("left", "right"):
        decls.append(f"--c-float-side: {side};")
    # stamped per-pattern action-group override (brand-schema §4.4f): THIS band's
    # measured row layout outranks the brand-default action-group law.
    ag = layout.get("_actionGroup") if isinstance(layout.get("_actionGroup"), dict) else {}
    if ag:
        ag_groups = ", ".join(f"{sel} {g}" for g in _AG_GROUPS)
        gap = str(ag.get("gap") or "").strip()
        if re.fullmatch(r"[\d.]+(?:rem|em|px)", gap):
            out.append(f"{ag_groups} {{ gap: {gap}; }}")
        ma = str(ag.get("marginAbove") or "").strip()
        if re.fullmatch(r"[\d.]+(?:rem|em|px)", ma):
            out.append(f"{ag_groups} {{ margin-block-start: {ma}; }}")
        # alignment ownership (fix3): a pattern-scoped align/crossAlign override
        # claims the placement properties at #sec-N specificity — over the brand
        # law AND over any context habit (same discipline as action_group_css).
        align = str(ag.get("align") or "").strip().lower()
        if align in _AG_JUSTIFY:
            out.append(f"{ag_groups} {{ justify-content: {_AG_JUSTIFY[align]}; }}")
        cross = str(ag.get("crossAlign") or "").strip().lower()
        if cross in ("start", "center", "end", "stretch"):
            flex = {"start": "flex-start", "end": "flex-end"}.get(cross, cross)
            out.append(f"{ag_groups} {{ align-items: {flex}; }}")
    # event scaffolds (2026-07): stamped bento/tier PATTERN FACTS → per-section vars.
    # The cell gap is a knob (validated CSS length), the collapse tier a px container
    # query below — the no-fact degrade is the scaffold's structural floor only.
    bn = layout.get("_bento") if isinstance(layout.get("_bento"), dict) else {}
    tr = layout.get("_tiers") if isinstance(layout.get("_tiers"), dict) else {}
    for stamp in (bn, tr):
        gap = str(stamp.get("gap") or "").strip()
        if gap and re.fullmatch(r"[\w.%()\s+*/-]+", gap):
            decls.append(f"--bn-gap: {gap};")
    if decls:
        out.append(f"{sel} {{ {' '.join(decls)} }}")
    for stamp, rules in ((bn, f"{sel} .cs-bento {{ grid-template-columns: 1fr; }} "
                              f"{sel} .cs-bento-cell {{ grid-column: auto; grid-row: auto; }}"),
                         (tr, f"{sel} .cs-tiers {{ grid-template-columns: 1fr; }}")):
        try:
            px = int(stamp.get("collapseAt"))
        except (TypeError, ValueError):
            continue
        out.append(f"@container frame (max-width: {px}px) {{ {rules} }}")
    # OBSERVED COLUMN TIERS (fid6 2026-07): the extracted pattern's measured
    # responsive column counts (recorded evidence, e.g. a 3-up grid the source
    # re-wraps to 2-up below its tablet register) re-scope --grid-cols through
    # container queries against the page frame — the canonical-tier count above
    # stays the default. Scoped `{sel} .cs-section` so the rule works in both the
    # full-page path (#sec-N wrapper) and the single-section path (sel=body, where
    # body itself is the queried container and cannot match inside @container).
    tiers = g.get("columnsTiers") if isinstance(g.get("columnsTiers"), list) else []
    for t in sorted((t for t in tiers if isinstance(t, dict)),
                    key=lambda t: -(t.get("maxViewportPx") or 0)):
        try:
            px = int(t["maxViewportPx"])
            n = max(1, int(t["columns"]))
        except (KeyError, TypeError, ValueError):
            continue
        out.append(f"@container frame (max-width: {px}px) {{ "
                   f"{sel} .cs-section {{ --grid-cols: {n}; }} }}")
    if not out:
        return ""
    return "/* per-section placement (composition.v1 §4.6.5) */\n" + "\n".join(out)


def scaffold_css(doc, layout, style_ctx=None, brand_yaml=None) -> str:
    """Return the base scaffold + this layout's archetype geometry. Brand-token driven,
    container-query / rem units only (never viewport). Vertical rhythm (section padding +
    inter-block gaps) comes from ``rhythm_for`` — brand spacing tokens preferred, else the
    active style's spacing scale. ``brand_yaml`` (optional) lets the device scaffolds
    consume brand-derived grammar (fid14 grid equalization); None keeps them built-in."""
    role, _surf = resolve_surface_intent(doc, layout)
    archetype = (layout.get("archetype") or "stack").lower()
    primary = _primary_scaffold_for(layout)
    if primary:
        arch_css = primary
    elif archetype == "stack" and scaffold_key(layout) == "faq":
        # composition-declared FAQ (event-scaffolds 2026-07): the useCase route has
        # no patternRef for the id registry to key on — dispatch parity with
        # compose_stack, same discipline as the conversion branch below.
        arch_css = SCAFFOLD_FAQ_CSS
    elif archetype == "stack" and scaffold_key(layout) == "conversion":
        # DISPATCH PARITY (sysfix 2026-07): scaffold_key mirrors compose_stack exactly
        # (patternRef/id, hero useCase, then form OR button contracts). The old
        # form-only check here shipped the HERO scaffold under a button-bound
        # conversion's `.cs-conversion` markup — correct markup, zero matching CSS,
        # so the centered narrow column never happened.
        arch_css = SCAFFOLD_CONVERSION_CSS
        # inset-panel presentation CSS rides ONLY stamped sections (AS-37 discipline).
        if layout.get("_insetPanel") is not None:
            arch_css = arch_css + "\n" + SCAFFOLD_CONVERSION_PANEL_CSS
        # full-bleed art band (fid5): same conditional-shipping discipline.
        if layout.get("_artSurface") is not None:
            arch_css = arch_css + "\n" + SCAFFOLD_CONVERSION_BAND_CSS
    else:
        arch_css = _ARCHETYPE_SCAFFOLD.get(archetype, SCAFFOLD_HERO_CSS)
    extra = _scaffold_extra_for(layout)
    if extra:
        arch_css = arch_css + "\n" + extra
    # AS-37: the art-panel device CSS ships ONLY on sections that actually render it,
    # so no-radius brand pages never carry its rounded-panel rule (see the blob note).
    if (layout or {}).get("_artPanel") is not None:
        arch_css = arch_css + "\n" + SCAFFOLD_ART_PANEL_CSS
    # P2 interaction devices: same conditional-shipping discipline as the art panel —
    # each device's CSS rides only with a layout stamped for it (stamp_pattern_devices).
    arch_css = arch_css + device_scaffold_css(
        [layout], equalize_grammar=grid_equalize_grammar(brand_yaml))
    # shared disclosure MOTION (AS-47): rides any details-emitting family on this
    # layout when the brand carries motion facts — one source for every lane.
    arch_css = arch_css + disclosure_motion_css(doc, [layout])
    # RELATIONAL LADDER (AS-48): the no-gap per-pair stack mechanic, appended AFTER
    # the archetype scaffolds so its same-specificity overrides win by order — ""
    # for ladder-less brands (uniform gap stays their degrade).
    arch_css = arch_css + relational_ladder_css(doc)
    # ACTION-GROUP law (fix2, brand-schema §4.4f): after the ladder so a measured
    # marginAbove LENGTH outranks the rung by order; "" for fact-less brands.
    _ag_css = action_group_css(doc)
    if _ag_css:
        arch_css = arch_css + "\n" + _ag_css
    # card PLATES on the contained grid (fid2 2026-07): the plate/person anatomy CSS
    # rides cards sections of brands whose card device declares a Container surface
    # (card_panel_role) — edge-cut sections already carry it via the device scaffold.
    if archetype == "cards" and layout.get("_edgeCut") is None \
            and card_panel_role(doc) is not None:
        arch_css = arch_css + "\n" + SCAFFOLD_CARD_PLATE_CSS
    return rhythm_vars_css(doc, style_ctx, role) + "\n" + SCAFFOLD_BASE_CSS + "\n" + arch_css


def device_scaffold_css(layouts, equalize_grammar: str | None = None) -> str:
    """The P2 interaction-device scaffolds needed by ANY of ``layouts`` (marquee /
    accordion open-state / edge-cut carousel), concatenated — "" when none is stamped,
    so pages without the devices ship byte-identical CSS (AS-37 discipline).
    ``is not None`` (not truthiness): an EMPTY hint dict is a valid stamp — a device
    treatment with no role refs still composes the device (idle presentation).

    ``equalize_grammar`` (fid14, AS-50): the brand's derived grid-equalization grammar
    (grid_equalize_grammar). The bento/tiers card scaffolds ship the equalized
    morphology by construction (row stretch + pinned action rows) — that already IS
    the ``stretch`` grammar; a brand whose observed card grids all HUG gets a release
    override so the generated scaffolds follow the same grammar the pattern-backed
    grids do. None (fact-less brand) keeps the built-in behavior byte-identical."""
    ls = [l for l in (layouts or []) if isinstance(l, dict)]
    parts = []
    if any(l.get("_marquee") is not None for l in ls):
        parts.append(SCAFFOLD_MARQUEE_CSS)
    # event scaffolds (2026-07): bento mosaic / pricing tiers / signup form / FAQ
    # state grammar ride the same stamp-gated shipping — pages without the stamps
    # keep byte-identical CSS.
    if any(l.get("_bento") is not None for l in ls):
        parts.append(SCAFFOLD_BENTO_CSS)
        if equalize_grammar == "hug":
            parts.append("/* brand grid grammar: hug — release the bento equalization"
                         " (AS-50) */\n.cs-bento { align-items: start; }\n"
                         ".cs-bento-cell .c-arrow-link, .cs-bento-cell .c-person {"
                         " margin-top: 0; }")
    if any(l.get("_tiers") is not None for l in ls):
        parts.append(SCAFFOLD_TIERS_CSS)
        if equalize_grammar == "hug":
            parts.append("/* brand grid grammar: hug — release the tier equalization"
                         " (AS-50) */\n.cs-tiers { align-items: start; }\n"
                         ".cs-tier > .c-button, .cs-tier > .c-arrow-link {"
                         " margin-top: 0; }")
    if any(l.get("_formFields") is not None for l in ls):
        parts.append(SCAFFOLD_SIGNUP_CSS)
    if any((l.get("_faq") or {}).get("activeSurface") or (l.get("_faq") or {}).get("hoverWash")
           for l in ls):
        parts.append(SCAFFOLD_FAQ_STATE_CSS)
    if any(l.get("_accordion") is not None for l in ls):
        parts.append(SCAFFOLD_ACCORDION_CSS)
        # per-item MEDIA-SWAP pairing rules (fid5 2026-07): one rule per bound item
        # index (composer-stamped _accordion.mediaIdx) — the open <details> drives
        # its own media layer via :has(), scoped structurally to any .cs-acc-split
        # instance. No bound media anywhere ⇒ no rules (byte-identical CSS).
        idxs = sorted({int(i) for l in ls
                       for i in ((l.get("_accordion") or {}).get("mediaIdx") or [])})
        if idxs:
            parts.append("\n".join(
                f'.cs-acc-split:has(.c-acc-item[data-acc-media="{i}"][open]) '
                f'.cs-acc-media-item[data-acc-i="{i}"] {{ opacity: 1; }}'
                for i in idxs))
    if any(l.get("_edgeCut") for l in ls):
        parts.append(SCAFFOLD_EDGECUT_CSS)
    # fix1 2026-07 devices: split-panel carousel / tab switcher / section headrow
    # rail (+ split intro) / side-rail card counterweight — same stamp-gated
    # shipping; brands without the pattern facts keep byte-identical CSS.
    if any(l.get("_carousel") is not None for l in ls):
        parts.append(SCAFFOLD_PANELCAR_CSS)
    if any(l.get("_tabs") is not None for l in ls):
        parts.append(SCAFFOLD_TABS_CSS)
    if any(l.get("_headRail") is not None or l.get("_introSplit") for l in ls):
        parts.append(SCAFFOLD_HEADRAIL_CSS)
    if any(l.get("_sideRail") for l in ls):
        parts.append(SCAFFOLD_SIDERAIL_CSS)
    return ("\n" + "\n".join(parts)) if parts else ""


def _disclosure_motion_block(item: str, trigger: str, marker: str) -> str:
    """One details-based disclosure family's motion rules, selector-parameterized —
    the ONE template both the accordion device and the FAQ scaffold ride (AS-46/47:
    no private forks of the same mechanic). Emitted ONLY by disclosure_motion_css,
    which gates on the brand's motion facts — every timing/easing value here is a
    BARE brand alias (no literal fallbacks: the block never ships without the facts).
    Panel height animates 0 -> auto on the platform's ::details-content slot — the
    <details name=…>-compatible equivalent of the grid-rows 0fr->1fr trick (closed
    details content is display-locked, so a grid-rows transition can never run on
    it). Browsers without ::details-content / interpolate-size keep the instant
    toggle; reduced-motion disables the panel tween."""
    return f"""/* ANIMATED DISCLOSURE (shared source, AS-47): state fade on the brand's fast tier,
   marker turn + panel height on the structural-collapse tier, brand primary curve. */
{item} {{ interpolate-size: allow-keywords;
  transition: background-color var(--c-motion-fast) var(--c-ease),
              color var(--c-motion-fast) var(--c-ease); }}
{trigger} {{ transition: background-color var(--c-motion-fast) var(--c-ease); }}
{marker} {{ transition: transform var(--c-motion-base) var(--c-ease); }}
{item}::details-content {{ display: block; block-size: 0; overflow-y: clip;
  transition: block-size var(--c-motion-base) var(--c-ease),
              content-visibility var(--c-motion-base) allow-discrete; }}
{item}[open]::details-content {{ block-size: auto; }}
@media (prefers-reduced-motion: reduce) {{
  {item}::details-content {{ transition: none; }} }}"""


def disclosure_motion_css(doc, layouts) -> str:
    """The shared disclosure-motion CSS for every details-emitting scaffold among
    ``layouts`` (accordion device rows, FAQ/agenda rows) — "" when none is present
    OR when the brand carries no captured motion language (AS-47: interactive state
    grammar ships WITH its captured motion wherever the mechanic renders; a brand
    with no motion facts degrades to the instant toggle, never to invented timing).
    The gate reads the brand's authored motion trio + easing (voice.motionSpec, the
    same REQUIRED facts the --c-motion-*/--c-ease aliases are generated from), so
    the bare alias references below always resolve when the block ships."""
    ls = [l for l in (layouts or []) if isinstance(l, dict)]
    if not ls:
        return ""
    spec = cr.motion_spec(doc)
    if not (spec.get("ease") and spec.get("fast") and spec.get("base")):
        return ""
    parts = []
    if any(l.get("_accordion") is not None for l in ls):
        parts.append(_disclosure_motion_block(
            ".c-acc-item", ".c-acc-trigger", ".c-acc-chev"))
    if any(((l.get("archetype") or "stack").lower() == "stack"
            and scaffold_key(l) == "faq") for l in ls):
        parts.append(_disclosure_motion_block(
            ".c-faq-item", ".c-faq-q", ".c-faq-icon"))
    return ("\n" + "\n".join(parts)) if parts else ""


def has_relational_ladder(doc) -> bool:
    """True when the brand authored the full relational PAIR trio (tokens.spacing
    eyebrow-to-heading + heading-to-body + body-to-cta, each with a value) — the gate
    for the no-gap stack mechanic (AS-48). The block/column rungs are optional riders:
    inside the gated block they degrade through var() chains, never re-gate it."""
    spacing = ((doc or {}).get("tokens") or {}).get("spacing") or {}
    def _has(key):
        node = spacing.get(key)
        return bool(node.get("value") if isinstance(node, dict) else node)
    return all(_has(k) for k in ("eyebrow-to-heading", "heading-to-body", "body-to-cta"))


# Header/anatomy stack containers the ladder mechanic converts: each is a flex COLUMN
# whose children form the label -> headline -> description -> action run (or a subset).
# Grid/card gutters and control rows are NOT here — those legitimately stay gap-based
# (riding their own measured row/column facts where captured).
# THIS TUPLE IS THE ONE REGISTRY (spacing remediation B5 2026-07): every scaffold
# that stacks label/headline/body/action content must be listed here (or carry its
# own explicit seam rules) — test_spacing_remediation.py guards the known families
# so a NEW stack scaffold fails loudly instead of silently shipping 0px seams.
# .cs-split-intro joined in B5: its bare heading+paragraph pairs rendered 0px
# (only the .c-header-wrapped variant had a seam rule).
_LADDER_STACKS = (".cs-faq", ".cs-foot", ".cs-hero-panel-content", ".cs-conversion",
                  ".cs-statement-text", ".cs-quote-text", ".cs-collage-body",
                  ".cs-gallery-head", ".cs-ruledlist", ".cs-split-intro")
# pair vocabulary (element-classed runs): what can open a seam on the left and what
# closes it on the right, per rung.
_LADDER_HEADS = (".c-header", ".c-heading", ".cs-title")
_LADDER_BODIES = (".c-paragraph", ".cs-sub")
_LADDER_ACTION_LEFTS = (".c-paragraph", ".cs-sub", ".c-caption", ".c-header",
                        ".c-heading", ".cs-title")
_LADDER_ACTIONS = (".cs-hero-actions", ".cs-conversion-actions", ".c-form",
                   ".cs-signup-panel", ".c-arrow-link", ".c-button")

# ── ACTION-GROUP facts (fix2 2026-07): measured multi-action row layout ──────────
_AG_GROUPS = (".cs-hero-actions", ".cs-modules-actions", ".cs-conversion-actions")


def action_group_facts(doc, layout=None) -> dict:
    """Resolve the brand's measured action-row layout facts (brand-schema §4.4f):
    brand-level `layoutGrammar.actionGroup` merged under the pattern's stamped
    `_actionGroup` override. Empty dict ⇒ no facts (structural defaults hold)."""
    brand = ((doc.get("layoutGrammar") or {}).get("actionGroup") or {})
    if not isinstance(brand, dict):
        brand = {}
    over = (layout or {}).get("_actionGroup") or {}
    merged = {**brand, **over}
    keys = ("gap", "align", "marginAbove", "crossAlign")
    return merged if any(merged.get(k) for k in keys) else {}


def _ag_px(value) -> float | None:
    """CSS length → px at the 16px root (rem/em action rows are root-relative)."""
    m = re.fullmatch(r"([\d.]+)(rem|em|px)", str(value or "").strip())
    if not m:
        return None
    n = float(m.group(1))
    return n * 16.0 if m.group(2) in ("rem", "em") else n


def ag_attrs(doc, layout=None) -> str:
    """Declaration stamps for one emitted action row: `data-ag-gap` (resolved px)
    + `data-ag-align`. AS-60 and the spacing auditor audit the rendered group
    against its OWN stamped declaration. No facts ⇒ no stamps (degrade)."""
    facts = action_group_facts(doc, layout)
    if not facts:
        return ""
    out = ""
    gap_px = _ag_px(facts.get("gap"))
    if gap_px is not None:
        out += f' data-ag-gap="{gap_px:g}"'
    align = str(facts.get("align") or "").strip().lower()
    if align in ("start", "center", "end"):
        out += f' data-ag-align="{align}"'
    return out


_AG_JUSTIFY = {"start": "flex-start", "center": "center", "end": "flex-end"}


def action_group_css(doc) -> str:
    """Brand-default action-row LAW (brand-schema §4.4f): the measured inter-action
    gap (+ the marginAbove seam when the fact is a length rather than `ladder`)
    emitted once per page over the scaffold's structural defaults.

    ALIGNMENT OWNERSHIP (fix3, the centering-leak fix): a declared `align` fact now
    claims the MAIN-AXIS placement property itself — `justify-content` on every
    emitted group — instead of trusting each scaffold's habit. Box-level centering
    (`margin-inline: auto` + max-width, the vector that actually displaced the
    stamped side-rail group) is not claimed here because the containment law
    already neutralized it structurally: contained groups span their column
    (width: 100%), so auto margins never see free space. Contexts that OWN their
    anchor (centered hero foot / panel / [data-align="centered"] / per-#sec-N
    anchors) keep winning by selector specificity — the schema's sanctioned
    exception, unchanged.

    CROSS-AXIS is evidence-gated: the scaffold's structural `align-items: center`
    (vertically centering unequal-height actions) holds unless the brand authored
    `crossAlign` (start|center|end|stretch) — only then does the law claim
    `align-items`. No facts ⇒ empty string (structural defaults hold
    byte-identically)."""
    facts = action_group_facts(doc)
    if not facts:
        return ""
    groups = ", ".join(_AG_GROUPS)
    parts = [f"/* ── ACTION-GROUP law (fix2): measured multi-action row facts ── */"]
    gap = str(facts.get("gap") or "").strip()
    if re.fullmatch(r"[\d.]+(?:rem|em|px)", gap):
        parts.append(f"{groups} {{ gap: {gap}; }}")
    ma = str(facts.get("marginAbove") or "").strip()
    if re.fullmatch(r"[\d.]+(?:rem|em|px)", ma):
        # a LENGTH seam overrides the ladder rung (source order: this block emits
        # after relational_ladder_css); `ladder` (or absence) rides the rung.
        parts.append(f"{groups} {{ margin-block-start: {ma}; }}")
    align = str(facts.get("align") or "").strip().lower()
    if align in _AG_JUSTIFY:
        parts.append(f"{groups} {{ justify-content: {_AG_JUSTIFY[align]}; }}")
    cross = str(facts.get("crossAlign") or "").strip().lower()
    if cross in ("start", "center", "end", "stretch"):
        flex = {"start": "flex-start", "end": "flex-end"}.get(cross, cross)
        parts.append(f"{groups} {{ align-items: {flex}; }}")
    return "\n".join(parts) if len(parts) > 1 else ""


def relational_ladder_css(doc) -> str:
    """The RELATIONAL-LADDER stack mechanic (AS-48), one shared source for every lane:
    when the brand authored the pair trio, header/anatomy stacks become NO-GAP columns
    and every seam is a per-pair margin riding the brand's own ladder tokens — the
    source mechanic itself (a flex column with no gap; each element carries its
    semantic margin). Uniform stack gap survives ONLY as the degrade for brands
    without ladder evidence (this function returns "" and nothing changes).

    Seam grammar (generic roles, never section-specific):
      eyebrow -> heading   --space-eyebrow-to-heading (the .cs-eyebrow-wrap's own
                           margin-bottom, --c-eyebrow-gap, already rides it)
      heading -> body      --space-heading-to-body (body meta captions ride it too)
      body    -> action    --space-body-to-cta
      block   -> block     --space-block-to-block (content-block row rhythm; degrades
                           to the uniform --c-block-gap when the rung is un-authored)
    The .cs-flow lane is contract-precise: compose_flow stamps each item's semantic
    row (data-row) so pair seams key on the CONTENT relationship, not markup order."""
    if not has_relational_ladder(doc):
        return ""
    block = "var(--space-block-to-block, var(--c-block-gap))"
    all_stacks = ", ".join(_LADDER_STACKS)
    seams = ", ".join(f"{c} > * + *" for c in _LADDER_STACKS)
    wrap_seams = ", ".join(f"{c} > .cs-eyebrow-wrap + *" for c in _LADDER_STACKS)
    head_body = ", ".join(f"{c} > {h} + {b}" for c in _LADDER_STACKS
                          for h in _LADDER_HEADS for b in _LADDER_BODIES)
    body_meta = ", ".join(f"{c} > {b} + .c-caption" for c in _LADDER_STACKS
                          for b in _LADDER_BODIES)
    body_action = ", ".join(f"{c} > {l} + {a}" for c in _LADDER_STACKS
                            for l in _LADDER_ACTION_LEFTS for a in _LADDER_ACTIONS)
    return f"""
/* ── RELATIONAL LADDER (AS-48): the brand's measured per-pair rhythm ─────────────
   Header/anatomy stacks are NO-GAP columns; every seam is a per-pair margin riding
   the authored ladder rungs (the source's own mechanic). Uniform gap is only the
   no-ladder degrade — it never renders when this block ships. */
{all_stacks} {{ gap: 0; }}
{seams} {{ margin-block-start: {block}; }}
/* label->headline: the eyebrow wrap's own margin-bottom (--c-eyebrow-gap == the
   authored rung) IS the seam — the follower opens none of its own. */
{wrap_seams} {{ margin-block-start: 0; }}
{head_body} {{ margin-block-start: var(--space-heading-to-body); }}
{body_meta} {{ margin-block-start: var(--space-heading-to-body); }}
{body_action} {{ margin-block-start: var(--space-body-to-cta); }}
/* the header CLUSTER itself (eyebrow -> heading -> optional typographic cta) */
.c-header {{ gap: 0; }}
.c-header > * + * {{ margin-block-start: var(--c-eyebrow-gap); }}
.c-header > * + .c-arrow-link {{ margin-block-start: var(--space-body-to-cta); }}
/* generic flow: contract-precise seams on the stamped semantic rows */
.cs-flow {{ gap: 0; }}
.cs-flow > * + * {{ margin-block-start: {block}; }}
/* the headrail's own margin-bottom IS its seam (recipe railToHeading fact or the
   structural default) — the follower opens none of its own (fix2; same discipline
   as the eyebrow-wrap rule above). */
.cs-flow > .cs-headrail + * {{ margin-block-start: 0; }}
.cs-flow > [data-row="eyebrow"] + * {{ margin-block-start: var(--space-eyebrow-to-heading); }}
.cs-flow > [data-row="heading"] + [data-row="body"] {{ margin-block-start: var(--space-heading-to-body); }}
.cs-flow > [data-row="body"] + [data-row="action"],
.cs-flow > [data-row="heading"] + [data-row="action"] {{ margin-block-start: var(--space-body-to-cta); }}
@media (max-width: 767px) {{ .cs-flow {{ gap: 0; }} }}
/* intro headers over module grids: the header->content seam is the brand's row
   rhythm. The bounded header measure caps the header RUN inside the intro (the
   source mechanic: a full-measure container whose header stack is measure-capped
   and rides the resolved anchor) — capping the .cs-modules-intro CONTAINER itself
   would fight the shared container centering (margin-inline: auto) and float a
   left-anchored header off the content edge (fid12). */
.cs-modules-intro {{ margin-bottom: {block}; }}
.cs-modules-intro > * {{ max-width: var(--space-header-measure, none); }}
.cs-modules-actions {{ margin-block-start: {block}; }}
.cs-faq {{ max-width: var(--space-header-measure, 52rem); }}"""


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
  --c-panel-ink-muted: var(--color-text-on-primary-muted);
  --c-panel-hairline: var(--color-border-hairline-on-primary);
  /* ONE shared page grid + baseline (alignment quick wins): every archetype scaffold
     places onto THESE tracks instead of private per-section grids, and every offset
     scalar snaps to --baseline / one --col so staggered elements REGISTER to shared
     lines instead of floating. --col resolves its 100% against the element it is used
     on (the section's shared-measure container). */
  --grid-cols: 12; /* provenance: structural — shared registration grid */
  /* registration gutter: the brand's measured split-column rung when the ladder
     authored one (fid11: tokens.spacing.column-to-column), else the structural unit */
  --grid-gutter: var(--space-column-to-column, 6rem);
  /* the shared content measure rides the brand's MEASURED container LAW when the
     spacing ladder authored one (fid10 2026-07: tokens.spacing.container-span — a
     fluid min(NNcqw, cap) expression from the tier containerFacts), else the measured
     container cap (fid6 2026-07: tokens.spacing.container-max — e.g. a 1216px
     measured content column was rendering at the 86rem structural default,
     inflating every section ~13% vs source); 86rem stays the ladder-less default. */
  --content-measure: var(--space-container-span, var(--space-container-max, 86rem));
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
/* color deployment: single committed accent (the eyebrow slug); everything else ink.
   A section's DECLARED eyebrow register (layout.eyebrowRegister) is brand evidence,
   so it wins over the style's generic deployment (brand hues beat style structure). */
.c-heading--accent {{ color: var(--c-ink); }}
.c-eyebrow {{ color: var(--c-eyebrow-color, var(--c-accent)); }}
"""


# ── document assembly ─────────────────────────────────────────────────────────────

def build_document(doc, layout, brand_yaml, style_ctx: RenderContext) -> str:
    role, surf = resolve_surface_intent(doc, layout)
    ctx = cr.make_context(doc, role, surf)
    ctx.style_active = bool(style_ctx and style_ctx.active)
    ctx.style_id = style_ctx.style_id if ctx.style_active else ""
    # style-aware cta-shape (B5) — same resolution as the full-page path.
    ctx.cta = cr.cta_shape(doc, style_ctx.structure if ctx.style_active else None)

    # pattern INTERACTION DEVICES (P2): stamp sanctioned treatment devices (marquee /
    # accordion open-state / edge-cut) BEFORE composing so the archetype composers
    # see the hints; the same resolve_pattern below keeps driving treatment CSS.
    stamp_pattern_devices(doc, layout, brand_yaml)

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
        + "\n" + scaffold_css(doc, layout, style_ctx, brand_yaml=brand_yaml) \
        + eyebrow_register_css(doc, layout, ":root")
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
    # GRID EQUALIZATION (fid14, AS-50): the pattern's measured gridEqualize fact drives
    # card-row height behavior in this single-section render too (bare selectors — no
    # #sec-N wrapper here). "" for fact-less patterns.
    equalize_css = pattern_equalize_css(pattern)
    if equalize_css:
        css += "\n" + equalize_css
    card_rhythm_css = pattern_card_rhythm_css(pattern)
    if card_rhythm_css:
        css += "\n" + card_rhythm_css
    # retrieval outcome is a visible stamp either way (W6): hits carry id+lib+kind,
    # an honest MISS carries the advisory attr + comment; kind "none" (no brand /
    # library plumbing) stays unstamped so legacy renders are byte-identical.
    if pattern:
        pat_attr = (f' data-pattern="{cr.esc(pattern.id)}" '
                    f'data-pattern-lib="{cr.esc(pattern.lib)}" '
                    f'data-pattern-match="{cr.esc(match_kind)}"')
        pat_comment = (f"\n<!-- layout pattern REUSED ({match_kind}): "
                       f"{pattern.lib}:{pattern.id} — {cr.esc(pattern.intent)} -->")
    elif match_kind == "miss":
        pat_attr = ' data-pattern-match="miss"'
        pat_comment = ("\n<!-- layout pattern: MISS — no library pattern matched this "
                       "section's use-case/shape; composed from the archetype default -->")
    else:
        pat_attr, pat_comment = "", ""

    # ALIGNMENT RESOLUTION (AS-18/AS-49) — same chain as the full-page path: section-
    # explicit > pattern contentShape.alignment > brand layoutGrammar.headerContext >
    # style role default; emitted body-scoped and stamped on <html> (single-section
    # renders have no #sec-N wrapper).
    resolved_align = resolve_alignment(layout, pattern, style_ctx, doc=doc)
    align_attr = align_stamp_attrs(resolved_align)
    placement_css = layout_placement_css("body", layout, resolved=resolved_align)
    if placement_css:
        css += "\n" + placement_css

    face_css = font_face_css(Path(brand_yaml).parent, doc) if brand_yaml else ""
    parallax_css = cr.parallax_css(doc)  # "" unless the brand declared imageParallax
    # Structural interaction blocks are signature-gated against the assembled section.
    # This includes the shared image loading/error lifecycle; image-less documents emit
    # no initializer, while cached and lazy `.c-image` assets share the same state law.
    ix_script = cr.interaction_script(section_html)

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
{ix_script}
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
