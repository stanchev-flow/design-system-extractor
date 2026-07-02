#!/usr/bin/env python3
"""compose_from_composition.py — PHASE 2: the ``composition.v1`` → renderer adapter.

The hybrid generator (see brand_pipeline/spec/composition-schema.md §4.6 + the A/B
REPORT) has the AI emit a STRUCTURED ``composition.v1`` object — an ordered list of
sections, each = archetype + slots (primitive/block refs) + treatments + inline copy.
This module RE-EXPRESSES that object as the input the EXISTING deterministic renderer
already consumes (a ``brand.yaml layouts[]``-shaped dict fed to
``compose_page.build_page`` → ``compose_section`` → ``component_render``), per the 1:1
round-trip mapping table in composition-schema.md §4.6.3. It writes NOTHING to brand.yaml
and adds NO new render path — the composition is a *generator* for the existing contract.

Two public builders + a renderer/CLI:
  - ``composition_to_layout(section)``  → one ``layouts[]``-shaped dict (+ the copy dict the
    section's archetype composer reads). archetype→archetype key; slots→blockMapping with
    the slot's inline copy/asset folded into ``usage``; seededFrom→patternRef;
    surfaceIntent→a ``tokens.surfaces`` role; treatments→gridRules/overlapRules; knobs→
    variantKnobs. A ``novelty: novel`` section (or any archetype the renderer can't draw as
    a bespoke composer) routes to the ``generic-flow`` fallback composer so it degrades
    gracefully instead of erroring.
  - ``composition_to_doc(comp, brand_yaml_path)`` → the full page ``doc`` (reusing the
    brand's navbar/footer + tokens/type/motion), the section ORDER, and the copy overrides
    (``SECTION_COPY`` for the hero + per-id ``LAYOUT_COPY``) the composers read.
  - ``render_composition(...)`` + a CLI (``render_composition.py`` wraps it) render a
    composition file to a page dir via the UNMODIFIED ``compose_page.build_page`` — fonts +
    assets injected exactly like the other composed pages.

Inline copy is fed through the ``blockMapping``/``usage`` mechanism (consumed by the
fallback-safe ``compose_section.render_slots`` inline-copy path) for ``generic-flow``
sections, and through the composer copy dicts (``SECTION_COPY``/``LAYOUT_COPY``, the same
in-memory override mechanism ``experiments/woodwave-ab/gen_arm_a.py`` uses) for the bespoke
archetypes — so NO edit to the bespoke composers is required.
"""
from __future__ import annotations

import argparse
import copy as _copy
import json
import shutil
import sys
from pathlib import Path

import yaml

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import compose_page as cp          # noqa: E402
import compose_section as cs       # noqa: E402
from styles import inactive_context, load_and_merge  # noqa: E402


# composition.v1 surfaceIntent enum → the brand's tokens.surfaces role keys.
SURFACE_INTENT_MAP = {
    "any": "surface/primary",
    "primary": "surface/primary",
    "inverse": "surface/inverse",
    "inverse-strong": "surface/inverse-strong",
    "panel": "surface/panel",
}

# The renderer archetypes that HAVE a bespoke composer (compose_section.ARCHETYPE_COMPOSERS
# minus the generic fallback). A composition archetype outside this set — or any
# novelty:novel section — routes to `generic-flow`.
_BESPOKE_ARCHETYPES = ("stack", "collage", "split", "stack-fullbleed", "cards", "interlock",
                       "overlay", "banded")

_GENERIC_FLOW = "generic-flow"


# ── small copy helpers ────────────────────────────────────────────────────────────

def _slots(section: dict) -> list[dict]:
    return [s for s in (section.get("slots") or []) if isinstance(s, dict)]


def _by_role(slots: list[dict], *keywords: str) -> dict | None:
    for s in slots:
        role = (s.get("role") or "").lower()
        if any(k in role for k in keywords):
            return s
    return None


def _by_contract(slots: list[dict], *contracts: str) -> dict | None:
    for s in slots:
        if (s.get("contract") or "").lower() in contracts:
            return s
    return None


def _text(copyval, *keys: str) -> str | None:
    """Pull a display string from a slot's `copy` (string, or dict keyed by keys)."""
    if isinstance(copyval, str):
        return copyval or None
    if isinstance(copyval, dict):
        for k in keys:
            v = copyval.get(k)
            if isinstance(v, str) and v.strip():
                return v
    return None


def _slot_text(slot: dict | None, *keys: str) -> str | None:
    if not slot:
        return None
    return _text(slot.get("copy"), *keys)


def _repeatable_copy(slot: dict | None) -> list[dict]:
    """A repeatable slot carries a list of copy objects (e.g. 3 value_props → 3 modules)."""
    if not slot:
        return []
    c = slot.get("copy")
    if isinstance(c, list):
        return [x for x in c if isinstance(x, dict)]
    if isinstance(c, dict):
        return [c]
    return []


def _asset_src(slot: dict | None) -> str | None:
    if not slot:
        return None
    a = slot.get("asset")
    if isinstance(a, dict) and a.get("src"):
        return str(a["src"])
    return None


def _valid_asset_names(brand_dir: Path) -> set[str]:
    """Basenames of the real brand image assets: brand_dir + brand_dir/assets on disk,
    PLUS compose_section.ASSET_SOURCES — the canonical set copy_assets() copies into
    EVERY rendered page (they live deeper under the run, e.g. render/*/assets/, so a
    dir-only scan wrongly dropped declared srcs like hero-staircase.jpg that are in fact
    always present in the page's assets/)."""
    exts = (".jpg", ".jpeg", ".png", ".svg", ".webp", ".gif")
    names: set[str] = set(cs.ASSET_SOURCES)
    for d in (brand_dir, brand_dir / "assets"):
        if d.is_dir():
            names |= {p.name for p in d.iterdir() if p.suffix.lower() in exts}
    return names


def _sanitize_assets(comp: dict, brand_dir: Path) -> dict:
    """Normalize asset srcs so the rendered page passes the gate's asset-fidelity checks:
      - a VALID local basename (a real file under brand_dir[/assets]) is rewritten to the
        ``assets/<name>`` path the composer copies it to (a bare ``hero-staircase.jpg`` would
        otherwise resolve to the page root and read as "missing");
      - a hallucinated src (no matching file) is DROPPED so the renderer falls back to its
        brand photography defaults (compose_section.ASSET_SOURCES);
      - http(s)/data srcs are left untouched.
    Operates on a deep copy; the original composition (persisted for provenance) is unchanged."""
    valid = _valid_asset_names(brand_dir)

    def _norm(src):
        """Return a normalized src string, or None to drop it."""
        if not isinstance(src, str) or not src.strip():
            return None
        if src.startswith(("http://", "https://", "data:", "assets/")):
            return src
        name = Path(src).name
        return f"assets/{name}" if name in valid else None

    def _clean_asset(obj: dict) -> None:
        a = obj.get("asset")
        if isinstance(a, dict) and "src" in a:
            n = _norm(a.get("src"))
            if n is None:
                a.pop("src", None)
            else:
                a["src"] = n
        elif isinstance(a, str):
            n = _norm(a)
            obj["asset"] = {"src": n} if n else None

    out = _copy.deepcopy(comp)
    for sec in (out.get("sections") or []):
        if not isinstance(sec, dict):
            continue
        for slot in (sec.get("slots") or []):
            if not isinstance(slot, dict):
                continue
            _clean_asset(slot)
            c = slot.get("copy")
            if isinstance(c, list):
                for item in c:
                    if isinstance(item, dict):
                        _clean_asset(item)
    return out


# ── placement (grid/overlap contract §4.6.5) ────────────────────────────────────────

# slot-level placement fields (all OPTIONAL; composition.v1.schema.json §4.6.5).
_PLACEMENT_KEYS = ("colStart", "colSpan", "rowSpan", "offsetCols", "offsetBaselines",
                   "alignTo", "registration")

# mediaAspect class → real aspect-ratio CSS (None = keep the variant/intrinsic default).
ASPECT_CSS = {
    "portrait": "3 / 4",
    "square": "1 / 1",
    "wide": "21 / 9",
    "pano": "3 / 1",
    "landscape": None,
    "freeform": None,
}


def _slot_placement(slot: dict) -> dict:
    """The slot's declared placement fields (empty dict when it carries none)."""
    return {k: slot[k] for k in _PLACEMENT_KEYS if slot.get(k) is not None}


def _is_media_slot(slot: dict) -> bool:
    return (slot.get("contract") or "").lower() in ("image", "video") or any(
        k in (slot.get("role") or "").lower() for k in ("photo", "media", "image"))


def _media_layers(section: dict) -> list[dict] | None:
    """Classify a section's media slots into PLACED LAYERS for the layered hero composer
    (compose_stack_hero). Returns None when NO media slot carries placement vocabulary and
    there are <=2 media slots — the legacy hero path (measured default geometry) then
    renders byte-identical. Layer kinds:
      - background: z:back + width:full-bleed (or a 'background' role) — full-bleed layer
        behind the section text (sanctioned text-on-media; the composer adds a scrim).
      - overlay:    carries `registration` (or a slot-targeting alignTo) — registered to
        the base media's edge/corner, crossing by depthCols/depthBaselines, layered by z.
      - corner:     alignTo.corner against the SECTION frame (no slot / slot='section').
      - base:       the first remaining media slot (the collage's base image).
    """
    slots = [s for s in _slots(section) if _is_media_slot(s)]
    if not slots:
        return None
    placed = any(_slot_placement(s) for s in slots) or any(
        (s.get("mediaAspect") in ("wide", "pano")) for s in slots) or any(
        ((s.get("z") or "") == "back" and (s.get("width") or "") == "full-bleed")
        for s in slots) or len(slots) > 2
    if not placed:
        return None

    layers: list[dict] = []
    base_seen = False
    for s in slots:
        name = s.get("name") or s.get("role") or "media"
        role = (s.get("role") or name or "").lower()
        p = _slot_placement(s)
        align_to = p.get("alignTo") if isinstance(p.get("alignTo"), dict) else None
        registration = p.get("registration") if isinstance(p.get("registration"), dict) else None
        z = (s.get("z") or "").lower()
        full_bleed = (s.get("width") or "").lower() == "full-bleed"
        layer = {
            "name": name,
            "role": s.get("role") or name,
            "src": _asset_src(s),
            "alt": ((s.get("asset") or {}) or {}).get("alt") if isinstance(s.get("asset"), dict) else None,
            "aspect": ASPECT_CSS.get((s.get("mediaAspect") or "").lower()),
            "colStart": p.get("colStart"),
            "colSpan": p.get("colSpan"),
            "offsetCols": p.get("offsetCols"),
            "offsetBaselines": p.get("offsetBaselines"),
            "alignTo": align_to,
            "registration": registration,
            "z": z or None,
        }
        if (z == "back" and full_bleed) or "background" in role:
            layer["kind"] = "background"
        elif registration is not None:
            layer["kind"] = "overlay"
        elif align_to and align_to.get("corner") and \
                (not align_to.get("slot") or str(align_to.get("slot")).lower() == "section"):
            layer["kind"] = "corner"
        elif align_to and align_to.get("corner"):
            layer["kind"] = "overlay"          # corner-pinned to another slot, zero depth
        elif not base_seen:
            layer["kind"] = "base"
            base_seen = True
        else:
            layer["kind"] = "overlay"          # extra media w/o registration: default inset
        layers.append(layer)
    return layers


# ── usage folding: one composition slot → one blockMapping entry ────────────────────

def _slot_to_mapping(slot: dict) -> dict:
    """Map one composition slot → a blockMapping entry {slot, role, contract, usage},
    folding the slot's layout-class fields + inline copy/asset into `usage` so the shared
    render_slots inline-copy path can render it (generic-flow) and the gate fidelity/
    slot-resolution rows stay grounded."""
    usage: dict = {}
    for k in ("textLen", "sizeClass", "width", "mediaAspect", "z") + _PLACEMENT_KEYS:
        if slot.get(k) is not None:
            usage[k] = slot[k]
    aspect = ASPECT_CSS.get((slot.get("mediaAspect") or "").lower())
    if aspect and _is_media_slot(slot):
        usage["aspect"] = aspect               # honored by render_image as aspect-ratio
    copyval = slot.get("copy")
    if isinstance(copyval, str):
        usage["text"] = copyval
    elif isinstance(copyval, dict):
        # fold recognized copy fields directly so _inline_props can consume them
        for k in ("eyebrow", "heading", "subheading", "body", "text", "caption",
                  "label", "cta", "placeholder", "submit", "level"):
            if k in copyval:
                usage[k] = copyval[k]
    asset = slot.get("asset")
    if isinstance(asset, dict):
        if asset.get("src"):
            usage["src"] = asset["src"]
        if asset.get("alt"):
            usage["alt"] = asset["alt"]
    return {
        "slot": slot.get("name") or slot.get("role") or "main",
        "role": slot.get("role") or slot.get("name") or "",
        "contract": slot.get("contract") or "paragraph",
        "usage": usage,
    }


def _treatments_to_rules(section: dict) -> tuple[dict, dict]:
    """Translate composition treatments (+ slot z-order) → gridRules/overlapRules the
    retrieval query + resolve_pattern fallback read (composition-schema.md §4.6.3).
    NOTE: a declared §4.6.5 ``section.grid`` does NOT rewrite these retrieval-facing
    rules (12 registration columns ≠ 12 content columns; rewriting `columns` here would
    perturb pattern retrieval scoring) — it rides separately on ``layout['_grid']`` and
    re-scopes the section's --grid-cols/--grid-gutter vars at render time."""
    kinds = {(t.get("kind") or "").lower() for t in (section.get("treatments") or [])
             if isinstance(t, dict)}
    grid: dict = {"columns": 1, "source": "composition"}
    overlap: dict = {"types": [], "source": "composition"}
    if "stagger" in kinds:
        grid["stagger"] = True
    if kinds & {"overlap", "text-on-media", "ghost-word", "straddle", "panel-on-media",
                "scrim-band", "type-behind-media", "break-frame"}:
        grid["overlap"] = True
    media_names = {s.get("name") for s in _slots(section) if _is_media_slot(s)}
    types = []
    for t in (section.get("treatments") or []):
        if not isinstance(t, dict):
            continue
        k = (t.get("kind") or "").lower()
        if k == "overlap":
            types.append("media-over-media")
        elif k in ("text-on-media", "type-behind-media"):
            types.append("display-text-over-media")
        elif k == "ghost-word":
            types.append("text-over-ghost-watermark")
        elif k in ("panel-on-media", "scrim-band"):
            types.append("panel-over-media")
        elif k == "straddle":
            # a MEDIA-target straddle is the sanctioned media pair (media-over-seam when
            # it registers against the banded seam); a TEXT-target straddle is
            # text-on-media-family.
            reg = t.get("registration") or {}
            if t.get("target") in media_names:
                types.append("media-over-seam"
                             if str(reg.get("toSlot") or "").lower() == "seam"
                             else "media-over-media")
            else:
                types.append("display-text-over-media")
    if types:
        overlap["types"] = types
        overlap["zOrder"] = ["media", "text"]
    return grid, overlap


# ── per-archetype copy translators (→ the shape each bespoke composer reads) ───────

def _hero_section_copy(section: dict) -> dict:
    """SECTION_COPY overrides read by compose_stack_hero (eyebrow / subhead / cta / wordmark)."""
    slots = _slots(section)
    header = _by_role(slots, "title", "heading", "eyebrow") or _by_contract(slots, "header", "heading")
    # header-copy fallback ONLY for dict copy: _text passes a plain STRING through
    # regardless of keys, which leaked the display-title string into the eyebrow of any
    # hero that carried no eyebrow slot (visible once hero copy became per-section).
    hdr_copy = (header or {}).get("copy")
    eyebrow = _slot_text(_by_role(slots, "eyebrow"), "eyebrow", "text") \
        or (_text(hdr_copy, "eyebrow") if isinstance(hdr_copy, dict) else None)
    # 'support' added to the role vocabulary: the anchored-gallery run showed models
    # naturally emit role:"support" for the lede, which the old keyword set missed.
    subhead = _slot_text(_by_role(slots, "subhead", "lede", "sub", "body", "tagline",
                                  "support"),
                         "text", "body", "subheading")
    cta = _slot_text(_by_role(slots, "action", "cta", "link"), "label", "cta", "text")
    out = dict(cs.SECTION_COPY)
    if eyebrow:
        out["eyebrow"] = eyebrow
    if subhead:
        out["subhead"] = subhead
    if cta:
        out["cta"] = cta
    return out


def _hero_mapping(section: dict) -> list[dict]:
    """blockMapping for the hero stack: wordmark logo + display-title heading + the media
    slots. LEGACY shape (no placement vocabulary anywhere): exactly the hero/overlap pair
    compose_stack_hero's _pick expects — byte-identical to before. PLACED shape (any media
    slot carries §4.6.5 placement / >2 media): one entry PER media slot, each folding its
    placement into usage; the composer draws them from layout['_mediaLayers']."""
    slots = _slots(section)
    title = _by_role(slots, "title", "display") or _by_contract(slots, "header", "heading")
    heading = _slot_text(title, "heading", "text") or "Everything in one place"
    media = [s for s in slots if _is_media_slot(s)]
    mapping = [
        {"slot": "main", "role": "wordmark (nav)", "contract": "logo", "usage": {"variant": "inverse"}},
        {"slot": "main", "role": "display title", "contract": "heading",
         "usage": {"heading": heading, "level": "display"}},
    ]
    if _media_layers(section) is not None:
        for s in media:
            entry = _slot_to_mapping(s)
            entry["slot"] = "main"
            entry["role"] = f"placed media ({s.get('name') or s.get('role') or 'media'})"
            mapping.append(entry)
        return mapping
    hero_src = _asset_src(media[0]) if len(media) >= 1 else None
    over_src = _asset_src(media[1]) if len(media) >= 2 else None
    mapping.append({"slot": "main", "role": "hero photography", "contract": "image",
                    "usage": {"ratio": "landscape", "radius": "0",
                              **({"src": hero_src} if hero_src else {})}})
    mapping.append({"slot": "main", "role": "overlap photography", "contract": "image",
                    "usage": {"ratio": "portrait", "radius": "0",
                              **({"src": over_src} if over_src else {})}})
    return mapping


def _cta_copy(section: dict) -> dict:
    slots = _slots(section)
    header = _by_role(slots, "heading", "title") or _by_contract(slots, "header", "heading")
    form = _by_contract(slots, "form", "input") or _by_role(slots, "signup", "form", "field")
    formcopy = (form or {}).get("copy") if isinstance((form or {}).get("copy"), dict) else {}
    return {
        "eyebrow": _slot_text(_by_role(slots, "eyebrow"), "eyebrow", "text")
        or _text((header or {}).get("copy"), "eyebrow") or "Introducing",
        "heading": _slot_text(header, "heading", "text") or "Start today",
        "body": _slot_text(_by_role(slots, "body", "sub", "lede"), "text", "body")
        or _text((header or {}).get("copy"), "body") or "",
        "placeholder": (formcopy or {}).get("placeholder", "you@company.com"),
        "cta": (formcopy or {}).get("submit")
        or _slot_text(_by_role(slots, "action", "cta"), "label", "cta") or "Start free",
    }


def _cta_mapping() -> list[dict]:
    # a `form` contract routes compose_stack → compose_conversion_stack.
    return [
        {"slot": "main", "role": "heading", "contract": "header",
         "usage": {"level": "h2"}},
        {"slot": "main", "role": "newsletter form (underline only)", "contract": "form",
         "usage": {"variant": "underline"}},
    ]


def _cards_copy(section: dict) -> dict:
    """features `cards`: intro eyebrow/heading + N modules (each caption + body [+ link])."""
    slots = _slots(section)
    header = _by_role(slots, "section-title", "title", "heading") or _by_contract(slots, "header")
    module_slot = _by_role(slots, "module", "value-prop", "feature", "card", "prop")
    modules = _repeatable_copy(module_slot)
    if not modules:  # fall back: each non-intro slot is a module
        modules = [s.get("copy") for s in slots
                   if isinstance(s.get("copy"), dict) and s is not header]
        modules = [m for m in modules if m]
    cards = []
    for m in modules:
        cards.append({
            "caption": m.get("heading") or m.get("caption") or m.get("title") or "",
            "body": m.get("text") or m.get("body") or "",
            "link": m.get("link") or m.get("cta"),
            "asset": m.get("asset"),
            "aspect": m.get("aspect"),
        })
    return {
        "eyebrow": _slot_text(_by_role(slots, "eyebrow"), "eyebrow", "text")
        or _text((header or {}).get("copy"), "eyebrow"),
        "heading": _slot_text(header, "heading", "text") or "",
        "cards": cards,
    }


def _cards_mapping(section: dict) -> list[dict]:
    """blockMapping for a `cards` section. The composer builds modules from copy_for(), so
    this mapping is for traceability + gate fidelity/slot-resolution: expand the repeatable
    module slot into RENDERABLE caption+paragraph entries (feature-item has no shared
    renderer) so render_slots resolves every entry (0 unresolved) and mirrors the modules
    the composer draws."""
    slots = _slots(section)
    mapping: list[dict] = []
    for s in slots:
        contract = (s.get("contract") or "").lower()
        role = (s.get("role") or "").lower()
        modules = _repeatable_copy(s)
        if contract in ("feature-item", "card") or (len(modules) > 1):
            for i, m in enumerate(modules):
                cap = m.get("heading") or m.get("caption") or m.get("title") or ""
                body = m.get("text") or m.get("body") or ""
                mapping.append({"slot": "cards", "role": f"module caption {i + 1}",
                                "contract": "caption", "usage": {"text": cap, "case": "upper"}})
                if body:
                    mapping.append({"slot": "cards", "role": f"module body {i + 1}",
                                    "contract": "paragraph", "usage": {"text": body}})
        else:
            mapping.append(_slot_to_mapping(s))
    return mapping


def _module_copies(slots: list[dict]) -> list[dict]:
    """The list of module copy-objects from a section's repeatable slot (copy is a list) —
    e.g. the brief's three value_props. Empty when there is no repeatable module slot."""
    for s in slots:
        c = s.get("copy")
        if isinstance(c, list) and any(isinstance(x, dict) for x in c):
            return [x for x in c if isinstance(x, dict)]
    return []


def _weave_modules(modules: list[dict]) -> str:
    """Weave module copies into one editorial body sentence-run (the WoodWave move: no
    feature grid, so N modules melt into one flowing body) — surfaces ALL module copy so
    a collage/interlock features section never DROPS the brief's value_props."""
    parts = []
    for m in modules:
        h = (m.get("heading") or m.get("caption") or m.get("title") or "").strip()
        b = (m.get("text") or m.get("body") or "").strip()
        if h and b:
            parts.append(f"{h} \u2014 {b}")
        elif h or b:
            parts.append(h or b)
    return "  ".join(parts)


def _collage_copy(section: dict) -> dict:
    slots = _slots(section)
    header = _by_role(slots, "heading", "title") or _by_contract(slots, "header")
    body = _slot_text(_by_role(slots, "body", "paragraph", "lede"), "text", "body") or ""
    modules = _module_copies(slots)
    if not body and modules:                       # fold the value_props into the collage body
        body = _weave_modules(modules)
    return {
        "ghost": _slot_text(_by_role(slots, "ghost", "watermark"), "text") or "",
        "eyebrow": _slot_text(_by_role(slots, "eyebrow"), "eyebrow", "text")
        or _text((header or {}).get("copy"), "eyebrow") or "",
        "heading": _slot_text(header, "heading", "text") or "",
        "body": body,
        "caption": _slot_text(_by_role(slots, "caption"), "caption", "text") or "",
        "cta": _slot_text(_by_role(slots, "action", "cta", "link"), "label", "cta") or "",
    }


def _split_copy(section: dict) -> dict:
    """split → the split-family composers. compose_split dispatches a split section by
    patternRef to FOUR composers with different copy keys: compose_info_band
    (eyebrow/heading/panelTitle/rows/cta), compose_about_statement (+ ``body``),
    compose_curator_quote (+ ``quote``/``body``/``caption``) and compose_visit_band
    (``mapCaption``/``ticketsTitle``/``ticketsRows``/``ticketsCta``/``visitTitle``/…).
    This translator emits the COMPLETE key union so every route renders: any LLM
    composition seeding those patterns used to crash ``KeyError: 'body'`` because only
    the info-band keys were emitted (found + wrapper-patched by the showcase harness,
    experiments/woodwave-showcase/build_showcase.py — fix now upstreamed here). No copy
    is invented: every string comes from the section's own slots or stays empty."""
    slots = _slots(section)
    header = _by_role(slots, "heading", "title") or _by_contract(slots, "header")
    panel = _by_role(slots, "panel", "rows", "list", "prices")
    rows = []
    for m in _repeatable_copy(panel):
        label = m.get("label") or m.get("heading") or m.get("title") or ""
        val = m.get("value") or m.get("text") or ""
        if label:
            rows.append((label, val))
    if not rows:                                   # fold value_props modules into ruled rows
        for m in _module_copies(slots):
            label = m.get("heading") or m.get("label") or m.get("title") or ""
            val = m.get("text") or m.get("body") or m.get("value") or ""
            if label:
                rows.append((label, val))

    def first(*keys: str) -> str:
        """First non-empty string under any of `keys` across the section's slot copy."""
        for s in slots:
            v = _text(s.get("copy"), *keys)
            if v:
                return v
        return ""

    out = {
        "eyebrow": _slot_text(_by_role(slots, "eyebrow"), "eyebrow", "text")
        or _text((header or {}).get("copy"), "eyebrow") or "",
        "heading": _slot_text(header, "heading", "text") or "",
        "panelTitle": _slot_text(panel, "heading", "title") or "Details",
        "rows": rows,
        "cta": _slot_text(_by_role(slots, "action", "cta", "link"), "label", "cta") or "Learn more",
        "caption": _slot_text(_by_role(slots, "caption"), "caption", "text") or "",
    }
    # about-statement / curator-quote keys: surface the section's own slot copy.
    out["body"] = _slot_text(_by_role(slots, "body", "statement", "lede", "support",
                                      "attribution"), "text", "body") \
        or first("text", "body") or first("attribution")
    out["quote"] = _slot_text(_by_role(slots, "quote"), "quote", "text") \
        or first("quote") or out["heading"]
    # visit-band aliases (read only when the section routes to compose_visit_band).
    out["mapCaption"] = out["caption"]
    out["ticketsTitle"] = out["panelTitle"]
    out["ticketsRows"] = out["rows"]
    out["ticketsCta"] = out["cta"]
    out["visitTitle"] = out["panelTitle"]
    out["visitRows"] = out["rows"]
    out["visitCta"] = out["cta"]
    return out


def _gallery_copy(section: dict) -> dict:
    """stack-fullbleed → compose_gallery_showcase. Besides the band's utility copy
    (eyebrow/counter/caption), the translator now ALSO surfaces heading/body/cta: a
    hero routed through this archetype (e.g. `hero-centered-stack-on-media`) used to
    silently DROP its display heading, lede and actions (the #sec-1 dropped-heading
    symptom — the section declared center, rendered uncentered AND lost its heading).
    The composer renders these ONLY from the layout-layer copy, so legacy gallery
    sections (whose LAYOUT_COPY entries carry no heading) stay byte-identical."""
    slots = _slots(section)
    heading = _by_role(slots, "heading", "title") or _by_contract(slots, "header")
    out = {
        "eyebrow": _slot_text(_by_role(slots, "eyebrow"), "eyebrow", "text")
        or _text((heading or {}).get("copy"), "eyebrow") or "",
        "counter": _slot_text(_by_role(slots, "counter", "index"), "text") or "1/1",
        "caption": _slot_text(_by_role(slots, "caption"), "caption", "text") or "",
    }
    # only carry the display-copy keys when the section actually declares them, so they
    # never clobber a hero's sect_copy in the `{**sect_copy, **layout_copy[id]}` merge.
    for key, val in (
            ("heading", _slot_text(heading, "heading", "text")),
            ("body", _slot_text(_by_role(slots, "body", "lede", "support", "subhead"),
                                "text", "body")),
            ("cta", _slot_text(_by_role(slots, "action", "cta", "link"),
                               "label", "cta", "text"))):
        if val:
            out[key] = val
    return out


def _interlock_copy(section: dict) -> dict:
    slots = _slots(section)
    statement = _by_role(slots, "statement", "heading", "title")
    # caption: role keyword first, then slot NAME, then an eyebrow-role slot — the anchored
    # gallery showed models put the caption pin's copy under role "eyebrow", which the old
    # role-only lookup silently dropped (fixed here instead of a per-run assembly rename).
    caption = _by_role(slots, "caption") \
        or next((s for s in slots if str(s.get("name", "")).lower() == "caption"), None) \
        or _by_role(slots, "eyebrow")
    media = _by_contract(slots, "image", "video") or _by_role(slots, "media", "photo", "image")
    cap = _slot_text(caption, "caption", "text", "eyebrow") or ""
    modules = _module_copies(slots)
    if not cap and modules:                        # surface value_prop titles as a caption stack
        cap = "\n".join((m.get("heading") or m.get("title") or m.get("text") or "").strip()
                        for m in modules if (m.get("heading") or m.get("title") or m.get("text")))
    # support + cta: previously the interlock composer silently DROPPED these slots (the
    # ANCHORED-REPORT composer-gap #2); the translator now surfaces them and the composer
    # renders them in an interlock foot cluster.
    support = _slot_text(_by_role(slots, "support", "subhead", "lede", "body", "tagline"),
                         "text", "body", "subheading") or ""
    cta = _slot_text(_by_role(slots, "action", "cta", "link"), "label", "cta", "text") or ""
    aspect = None
    if isinstance(media, dict):
        aspect = ASPECT_CSS.get((media.get("mediaAspect") or "").lower())
    return {
        "caption": cap,
        "statement": _slot_text(statement, "heading", "text") or "",
        "asset": _asset_src(media),
        "support": support,
        "cta": cta,
        "mediaAspectCss": aspect,
    }


_COPY_TRANSLATORS = {
    "collage": _collage_copy,
    "split": _split_copy,
    "cards": _cards_copy,
    "stack-fullbleed": _gallery_copy,
    "interlock": _interlock_copy,
}


# ── overlay / banded (editorial-harvest-2026-07): raw-slot payload + mapping ────────

def _overlay_payload(section: dict) -> dict:
    """The raw slot/treatment payload compose_overlay / compose_banded consume
    (layout['_overlay']): normalized slots (copy + asset + placement + layout classes),
    the raw treatments, and the banded section's bands declaration. Nothing is invented —
    every value comes from the composition section itself."""
    slots = []
    for s in _slots(section):
        p = _slot_placement(s)
        slots.append({
            "name": s.get("name") or s.get("role") or "slot",
            "role": s.get("role") or "",
            "contract": (s.get("contract") or "").lower(),
            "z": (s.get("z") or "").lower() or None,
            "width": (s.get("width") or "").lower() or None,
            "sizeClass": (s.get("sizeClass") or "").lower() or None,
            "textLen": (s.get("textLen") or "").lower() or None,
            "mediaAspect": (s.get("mediaAspect") or "").lower() or None,
            "aspect": ASPECT_CSS.get((s.get("mediaAspect") or "").lower()),
            "media": _is_media_slot(s),
            "src": _asset_src(s),
            "alt": ((s.get("asset") or {}).get("alt")
                    if isinstance(s.get("asset"), dict) else None),
            "copy": s.get("copy"),
            **{k: p.get(k) for k in _PLACEMENT_KEYS},
        })
    return {
        "slots": slots,
        "treatments": [t for t in (section.get("treatments") or []) if isinstance(t, dict)],
        "bands": section.get("bands") if isinstance(section.get("bands"), dict) else None,
        "knobs": section.get("knobs") if isinstance(section.get("knobs"), dict) else {},
    }


def _overlay_mapping(section: dict) -> list[dict]:
    """blockMapping for overlay/banded sections — traceability + the gate's fidelity/
    slot-resolution rows. Every entry must resolve to a SHARED renderer (zero unresolved
    slots): media slots normalize to `image`, repeatable copy expands to caption+paragraph
    pairs, display-tier text to `heading`, the rest to caption/paragraph by sizeClass.
    Structural slots with no copy (the panel/rail shells) are drawn by the composer and
    carry no mapping entry."""
    mapping: list[dict] = []
    for s in _slots(section):
        if _is_media_slot(s):
            e = _slot_to_mapping(s)
            e["contract"] = "image"
            mapping.append(e)
            continue
        c = s.get("copy")
        if isinstance(c, list):
            for i, m in enumerate(_repeatable_copy(s)):
                cap = m.get("heading") or m.get("caption") or m.get("title") \
                    or m.get("label") or ""
                body = m.get("text") or m.get("body") or ""
                if cap:
                    mapping.append({"slot": s.get("name") or "overlay",
                                    "role": f"{s.get('role') or 'item'} {i + 1}",
                                    "contract": "caption",
                                    "usage": {"text": cap, "case": "upper"}})
                if body:
                    mapping.append({"slot": s.get("name") or "overlay",
                                    "role": f"{s.get('role') or 'item'} body {i + 1}",
                                    "contract": "paragraph", "usage": {"text": body}})
            continue
        if not c:
            continue                      # structural shell (panel/rail): composer-drawn
        e = _slot_to_mapping(s)
        contract = (e.get("contract") or "").lower()
        sc = (s.get("sizeClass") or "").lower()
        if contract in ("link", "cta"):
            e["contract"] = "link"
            e["usage"].setdefault("label", e["usage"].get("text")
                                  or e["usage"].get("cta") or "Learn more")
        elif sc in ("colossal", "hero", "display", "title"):
            e["contract"] = "heading"
            e["usage"].setdefault("heading", e["usage"].get("text")
                                  or e["usage"].get("heading") or "")
            e["usage"]["level"] = "display"
        elif sc == "caption" or (s.get("textLen") or "") in ("word", "short"):
            e["contract"] = "caption"
        else:
            e["contract"] = "paragraph"
        mapping.append(e)
    return mapping


# ── the public adapter ─────────────────────────────────────────────────────────────

def composition_to_layout(section: dict) -> dict:
    """Map ONE composition.v1 section → a brand.yaml layouts[]-shaped dict (round-trip
    §4.6.3). The section's copy dict (read by the archetype composer) is attached under the
    private key ``_composerCopy``; the hero also attaches ``_sectionCopy`` (SECTION_COPY
    overrides). Both are consumed by ``composition_to_doc`` and never written to disk."""
    sid = section.get("id") or section.get("useCase") or "section"
    archetype = (section.get("archetype") or "stack").lower()
    novelty = (section.get("novelty") or "reuse").lower()
    surface_intent = SURFACE_INTENT_MAP.get(
        (section.get("surfaceIntent") or "any").lower(), "surface/primary")

    # renderer archetype: per the schema, a `novelty:novel` section still RECOMPOSES WITHIN a
    # drawable archetype — so it renders via that archetype's bespoke composer (novelty only
    # flags promotion-eligibility, not a different render path). Only an archetype WITHOUT a
    # bespoke composer (none of the six today) degrades to the generic-flow safety net so it
    # still renders its exact slots instead of erroring.
    if archetype in _BESPOKE_ARCHETYPES:
        renderer_archetype = archetype
    else:
        renderer_archetype = _GENERIC_FLOW

    grid, overlap = _treatments_to_rules(section)
    layout: dict = {
        "id": sid,
        "archetype": renderer_archetype,
        "surfaceIntent": surface_intent,
        "gridRules": grid,
        "overlapRules": overlap,
    }
    # seededFrom → patternRef (drives resolve_pattern → pattern_treatment_css stagger/knobs).
    seeded = section.get("seededFrom")
    if isinstance(seeded, dict) and seeded.get("id"):
        layout["patternRef"] = {"lib": seeded.get("lib", "project"), "id": seeded["id"]}
    if isinstance(section.get("knobs"), dict):
        layout["variantKnobs"] = section["knobs"]

    # ── placement round-trip (§4.6.5; every field OPTIONAL) ──────────────────────
    # per-section alignment: first-class `alignment`, else the legacy knobs.align value.
    alignment = section.get("alignment")
    if not isinstance(alignment, dict):
        knob_align = str(((section.get("knobs") or {}).get("align")) or "").lower()
        if knob_align in ("center", "centered"):
            alignment = {"anchor": "centered"}
        elif knob_align in ("left", "right"):
            alignment = {"anchor": knob_align}
    if isinstance(alignment, dict) and alignment.get("anchor"):
        layout["alignment"] = {"anchor": str(alignment["anchor"]).lower(),
                               **({"counterweight": alignment["counterweight"]}
                                  if alignment.get("counterweight") else {})}
    # declared section grid (re-scopes --grid-cols/--grid-gutter at render time only).
    if isinstance(section.get("grid"), dict):
        layout["_grid"] = section["grid"]
    # per-slot placement (kept keyed by slot name for composers/scaffolds that read it).
    placement = {}
    for s in _slots(section):
        p = _slot_placement(s)
        if p:
            placement[s.get("name") or s.get("role") or "slot"] = p
    if placement:
        layout["_placement"] = placement
    # media layers for the layered hero composer (None = legacy measured geometry).
    layers = _media_layers(section) if archetype == "stack" else None
    if layers is not None:
        layout["_mediaLayers"] = layers
    # interlock media side: a float-wrap/inset treatment side (or knobs.mediaSide) is a
    # mirrorable contract lever → --c-float-side via compose_section.layout_placement_css.
    side = None
    for t in (section.get("treatments") or []):
        if isinstance(t, dict) and (t.get("kind") or "").lower() in ("float-wrap", "inset") \
                and t.get("side"):
            side = str(t["side"]).lower()
    side = side or str(((section.get("knobs") or {}).get("mediaSide")) or "").lower() or None
    if side in ("left", "right"):
        layout["_floatSide"] = side
    # composition provenance (advisory, stamped on the section wrapper via data-* if desired)
    layout["_composition"] = {"useCase": section.get("useCase"), "novelty": novelty,
                              "archetype": archetype}

    # blockMapping + composer copy. Disambiguate the `stack` archetype by useCase (it serves
    # both the hero bookend and the closing conversion CTA): a hero stack → the hero composer;
    # ANY other stack (cta/footer/…, with or without an explicit form) → the conversion stack.
    use_case = (section.get("useCase") or "").lower()
    is_hero = archetype == "stack" and use_case == "hero"
    is_conversion = archetype == "stack" and not is_hero

    if renderer_archetype == _GENERIC_FLOW:
        # expand repeatable list-copy slots (e.g. value_props) into caption+paragraph entries
        # so the generic-flow safety net never silently drops module copy.
        mapping = []
        for s in _slots(section):
            if isinstance(s.get("copy"), list):
                for i, m in enumerate(_repeatable_copy(s)):
                    cap = m.get("heading") or m.get("caption") or m.get("title") or ""
                    body = m.get("text") or m.get("body") or ""
                    if cap:
                        mapping.append({"slot": "flow", "role": f"module caption {i + 1}",
                                        "contract": "caption", "usage": {"text": cap, "case": "upper"}})
                    if body:
                        mapping.append({"slot": "flow", "role": f"module body {i + 1}",
                                        "contract": "paragraph", "usage": {"text": body}})
            else:
                mapping.append(_slot_to_mapping(s))
        layout["blockMapping"] = mapping
        layout["_composerCopy"] = {}
    elif is_hero:  # hero stack
        layout["blockMapping"] = _hero_mapping(section)
        layout["_composerCopy"] = {}
        layout["_sectionCopy"] = _hero_section_copy(section)
    elif is_conversion:  # conversion stack
        layout["blockMapping"] = _cta_mapping()
        layout["_composerCopy"] = _cta_copy(section)
    elif archetype in ("overlay", "banded"):
        # the layered/banded composers consume the RAW slot+treatment payload directly
        # (copy inline on each slot) — no fixed-key copy translator needed.
        layout["_overlay"] = _overlay_payload(section)
        layout["blockMapping"] = _overlay_mapping(section)
        layout["_composerCopy"] = {}
        if isinstance(section.get("bands"), dict):
            layout["_bands"] = section["bands"]
    else:  # collage / split / cards / stack-fullbleed / interlock
        layout["blockMapping"] = _cards_mapping(section) if archetype == "cards" \
            else [_slot_to_mapping(s) for s in _slots(section)]
        translator = _COPY_TRANSLATORS.get(archetype)
        layout["_composerCopy"] = translator(section) if translator else {}
    return layout


def composition_to_doc(comp: dict, brand_yaml_path: Path | str) -> tuple[dict, list[str]]:
    """Build the full page ``doc`` for a composition. Reuses the brand's navbar/footer +
    tokens/type/motion from brand.yaml; replaces ``layouts[]`` with the mapped sections and
    returns the section ORDER. The per-section copy overrides (SECTION_COPY for the hero +
    per-id LAYOUT_COPY) are stashed on the doc under ``_hybridCopy`` for the renderer to
    apply via the in-memory compose_section copy-dict override mechanism.

    Returns ``(doc, order)``.
    """
    doc = yaml.safe_load(Path(brand_yaml_path).read_text()) or {}
    sections = [s for s in (comp.get("sections") or []) if isinstance(s, dict)]
    if not sections:
        raise ValueError("composition has no sections")

    layouts: list[dict] = []
    order: list[str] = []
    layout_copy: dict = {}
    section_copy: dict | None = None
    accent_layout_id: str | None = None

    for sec in sections:
        layout = composition_to_layout(sec)
        composer_copy = layout.pop("_composerCopy", {})
        sect_copy = layout.pop("_sectionCopy", None)
        layouts.append(layout)
        order.append(layout["id"])
        if composer_copy:
            layout_copy[layout["id"]] = composer_copy
        if sect_copy is not None:
            # PER-SECTION hero copy (ANCHORED-REPORT composer-gap #1 fix): every hero
            # binds its own eyebrow/subhead/cta via LAYOUT_COPY[id] (compose_stack_hero
            # reads copy_for(layout)); the FIRST hero additionally seeds the page-global
            # SECTION_COPY base (nav wordmark/links + defaults for copyless sections).
            layout_copy[layout["id"]] = {**sect_copy, **layout_copy.get(layout["id"], {})}
        if sect_copy is not None and section_copy is None:
            section_copy = sect_copy
            accent_layout_id = layout["id"]  # the hero bookend keeps the single accent
        # first inverse/hero section becomes the accent bookend if no explicit hero copy
        if accent_layout_id is None and layout.get("surfaceIntent") in (
                "surface/inverse", "surface/inverse-strong"):
            accent_layout_id = layout["id"]

    doc["layouts"] = layouts
    doc["_hybridCopy"] = {
        "section_copy": section_copy or {},
        "layout_copy": layout_copy,
        "accent_layout_id": accent_layout_id or (order[0] if order else None),
    }
    return doc, order


# ── render a composition to a page dir (via the UNMODIFIED compose_page) ────────────

def render_composition(comp: dict, brand_yaml_path: Path | str, outdir: Path | str,
                       style_id: str | None = None,
                       brand_dir: Path | str | None = None) -> dict:
    """Render a composition to ``outdir/index.html`` via ``compose_page.build_page`` (the
    existing composer), injecting fonts + assets exactly like the other composed pages.

    Returns a small summary dict {out, order, unresolved, accent_layout}.
    """
    outdir = Path(outdir)
    brand_yaml_path = Path(brand_yaml_path)
    brand_dir = Path(brand_dir) if brand_dir else brand_yaml_path.parent

    # defensively drop hallucinated asset srcs so a bad filename can't fail asset fidelity
    # (renderer falls back to brand photography). Provenance copy below keeps the original.
    render_comp = _sanitize_assets(comp, brand_dir)
    doc, order = composition_to_doc(render_comp, brand_yaml_path)
    hybrid = doc.pop("_hybridCopy")

    style_ctx = load_and_merge(style_id, doc) if style_id else inactive_context()

    # In-memory copy-dict override (the gen_arm_a.py mechanism): the bespoke composers read
    # cs.SECTION_COPY / cs.LAYOUT_COPY by module reference, so patching binds the
    # composition's inline copy without editing the composers. Snapshot + restore so the
    # process stays clean across multiple renders.
    saved_section, saved_layout, saved_accent = (
        cs.SECTION_COPY, cs.LAYOUT_COPY, cp.ACCENT_LAYOUT)
    try:
        if hybrid["section_copy"]:
            cs.SECTION_COPY = {**cs.SECTION_COPY, **hybrid["section_copy"]}
        cs.LAYOUT_COPY = {**cs.LAYOUT_COPY, **hybrid["layout_copy"]}
        if hybrid["accent_layout_id"]:
            cp.ACCENT_LAYOUT = hybrid["accent_layout_id"]

        outdir.mkdir(parents=True, exist_ok=True)
        # resolve + copy the nav logo BEFORE building so the composed hero nav references the
        # local, offline-safe asset (in-memory doc mutation only; brand.yaml unchanged).
        cs.prepare_nav_logo(doc, brand_dir, outdir / "assets")
        html = cp.build_page(doc, brand_yaml_path, order, style_ctx)
        (outdir / "index.html").write_text(html)
        copied = cs.copy_assets(brand_dir, outdir / "assets")
        copied += _copy_declared_assets(render_comp, brand_dir, outdir / "assets")
        copied += cs.copy_fonts(brand_dir, outdir / "assets", doc)
    finally:
        cs.SECTION_COPY, cs.LAYOUT_COPY, cp.ACCENT_LAYOUT = (
            saved_section, saved_layout, saved_accent)

    # persist the composition JSON next to the render for provenance/round-trip.
    (outdir / "composition.json").write_text(json.dumps(comp, indent=2) + "\n")

    # unresolved-slot count (parity with compose_page.main()).
    import component_render as cr
    layouts = {l.get("id"): l for l in doc.get("layouts", [])}
    unresolved = 0
    for lid in order:
        layout = layouts[lid]
        ctx = cr.make_context(doc, *cs.resolve_surface_intent(doc, layout))
        unresolved += sum(1 for r in cs.render_slots(doc, layout, ctx)
                          if "unresolved slot" in r["html"])
    return {"out": str(outdir / "index.html"), "order": order, "unresolved": unresolved,
            "accent_layout": hybrid["accent_layout_id"], "assets": copied}


def _declared_asset_names(comp: dict) -> set[str]:
    """Basenames of every LOCAL asset the (sanitized) composition declares — the srcs
    _sanitize_assets already validated as real brand files (``assets/<name>``)."""
    names: set[str] = set()

    def _take(obj):
        a = obj.get("asset")
        src = a.get("src") if isinstance(a, dict) else None
        if isinstance(src, str) and src.startswith("assets/"):
            names.add(Path(src).name)

    for sec in (comp.get("sections") or []):
        if not isinstance(sec, dict):
            continue
        for slot in (sec.get("slots") or []):
            if not isinstance(slot, dict):
                continue
            _take(slot)
            c = slot.get("copy")
            if isinstance(c, list):
                for item in c:
                    if isinstance(item, dict):
                        _take(item)
    return names


def _copy_declared_assets(comp: dict, brand_dir: Path, out_assets: Path) -> list[str]:
    """Copy composition-declared brand assets that ``copy_assets`` (canonical
    ASSET_SOURCES only) does not cover — e.g. a composition referencing the real
    ``About-img-3.jpg``. Without this the gate's asset-presence rows read the file as
    missing (found + wrapper-patched by the showcase harness; upstreamed here)."""
    copied = []
    for name in sorted(_declared_asset_names(comp)):
        dest = out_assets / name
        if dest.exists():
            continue
        src = cs.find_asset_source(brand_dir, name)
        if src is None:  # brand_dir root/assets (the set _valid_asset_names scanned)
            for d in (brand_dir, brand_dir / "assets"):
                if (d / name).is_file():
                    src = d / name
                    break
        if src:
            out_assets.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            copied.append(name)
    return copied


def _load_composition(path: Path) -> dict:
    txt = Path(path).read_text()
    if str(path).endswith((".yaml", ".yml")):
        return yaml.safe_load(txt)
    return json.loads(txt)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Render a composition.v1 file to a page dir via the existing composer.")
    ap.add_argument("composition", type=Path, help="path to a composition.v1 JSON/YAML file")
    ap.add_argument("brand_yaml", type=Path, help="path to the canonical brand.yaml")
    ap.add_argument("-o", "--out", type=Path, required=True, help="output page dir")
    ap.add_argument("--style", default=None, help="active STYLE id (styles/<id>.md)")
    ap.add_argument("--brand-dir", type=Path, default=None,
                    help="brand asset dir (defaults to brand.yaml's parent)")
    args = ap.parse_args(argv)

    comp = _load_composition(args.composition)
    summary = render_composition(comp, args.brand_yaml, args.out, style_id=args.style,
                                 brand_dir=args.brand_dir)
    print(f"Rendered composition -> {summary['out']}"
          + (f"  [style:{args.style}]" if args.style else ""))
    print(f"  order: {' -> '.join(summary['order'])} -> closing-bookend")
    print(f"  accent layout (single accent bookend): {summary['accent_layout']}")
    print(f"  unresolved slots: {summary['unresolved']}")
    print(f"  assets: {', '.join(summary['assets']) or 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
