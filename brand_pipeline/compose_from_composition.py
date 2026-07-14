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
import re
import shutil
import sys
from pathlib import Path

import yaml

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import archetype_library as al     # noqa: E402  (genre skeleton normalization — fact-gated)
import compose_page as cp          # noqa: E402
import compose_section as cs       # noqa: E402
import style_scale                 # noqa: E402  (derived-scale consumption, pass1)
from styles import inactive_context, load_and_merge  # noqa: E402


# composition.v1 surfaceIntent canonical values → the brand's tokens.surfaces role
# keys. Non-canonical intents (copy-first surface selection, 2026-07-14) resolve as
# `surface/<intent>` and are honored ONLY when the brand declares that role
# (compose_section.resolve_surface_intent's existing role-membership check); a brand
# without the role keeps the historical degrade. The intent vocabulary therefore
# stays the brand's own surface roster, never an invented palette.
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
_BESPOKE_ARCHETYPES = ("stack", "collage", "split", "media-split", "stack-fullbleed",
                       "cards", "interlock", "overlay", "banded")

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


def _by_name(slots: list[dict], *names: str) -> dict | None:
    """Match on the slot's declared NAME (the archetype anatomy vocabulary — meta,
    kicker, subheading…). Role keywords stay the primary lookup; names are the
    archetype-section fallback, because a genre skeleton fixes slot NAMES while the
    model authors domain ROLE words (\"event-logistics\", \"promise\")."""
    for s in slots:
        if (s.get("name") or "").strip().lower() in names:
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
    """Basenames of the real brand image assets — DISK EVIDENCE from the ACTIVE brand's
    own tree only (AS-34): ``compose_section.brand_image_inventory`` scans brand_dir
    recursively (assets/ subdirectories included — blocker-6 — plus the deeper
    render/*/assets copies that the old ``ASSET_SOURCES`` module-constant seed papered
    over). The constant seed is GONE: it declared one brand's filenames valid for every
    brand, so a foreign composition's ``hero-staircase.jpg`` survived sanitization and
    shipped as a broken reference."""
    return set(cs.brand_image_inventory(brand_dir))


def _sanitize_assets(comp: dict, brand_dir: Path) -> dict:
    """Normalize asset srcs so the rendered page passes the gate's asset-fidelity checks:
      - a VALID local basename (a real file under the ACTIVE brand's tree) is rewritten to
        the ``assets/<name>`` path the composer copies it to (a bare ``logo-box.svg`` would
        otherwise resolve to the page root and read as "missing");
      - a hallucinated src (no matching file) is DROPPED so the renderer falls back to the
        ACTIVE brand's own default art (or omits the device) — never a foreign brand's;
      - http(s)/data srcs are left untouched;
      - a BARE-STRING item in a repeatable slot's copy list (AS-34, blocker-1: the
        live-generation shape ``copy: ["Anthropic", "logo-box.svg", …]``) is COERCED, not
        filtered: a string naming a real brand file becomes ``{"asset": {"src": …}}``
        (evidence routing then draws the real image); any other string becomes
        ``{"text": …}`` (the caption device). ``_repeatable_copy``'s dict filter then
        keeps every item instead of silently dropping the wall.
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

    def _coerce_item(item):
        """A bare-string copy-list item → a dict the downstream mapping keeps."""
        if not isinstance(item, str) or not item.strip():
            return item
        n = _norm(item.strip())
        return {"asset": {"src": n}} if n else {"text": item.strip()}

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
                slot["copy"] = [_coerce_item(item) for item in c]
                for item in slot["copy"]:
                    if isinstance(item, dict):
                        _clean_asset(item)
            elif isinstance(c, dict):
                # dict copy carrying repeatable sub-lists (a block contract's item
                # run, e.g. a logo-bar's marks — fix6): the same coerce/clean walk,
                # so nested asset refs normalize + register for copying like any
                # top-level list copy.
                for key, v in list(c.items()):
                    if isinstance(v, list):
                        c[key] = [_coerce_item(item) for item in v]
                        for item in c[key]:
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


# treatment kinds that declare the INSET ART-PANEL surface (schema-gap 9, AS-37):
# a rounded panel painted with a brand art asset, hosting the section's content/media.
_ART_PANEL_KINDS = {"panel-on-media", "inset-panel", "art-panel", "inset-rounded-panel-art"}


def _is_art_panel_bg_slot(slot: dict) -> bool:
    """A slot that IS the panel's paint (not content media): named/roled 'background'
    or 'panel', drawn at z:back or full-bleed width."""
    label = f"{slot.get('name') or ''} {slot.get('role') or ''}".lower()
    if not ("background" in label or "panel" in label):
        return False
    return (str(slot.get("z") or "").lower() == "back"
            or str(slot.get("width") or "").lower() == "full-bleed")


def _art_panel_payload(section: dict) -> dict | None:
    """Detect a section that declares the INSET ART-PANEL device (AS-37): either a
    sanctioned panel treatment (`panel-on-media` / `inset-panel` / `art-panel`) or a
    z:back/full-bleed background/panel slot. Returns {"asset": <declared src|None>} —
    the composer resolves a missing asset from the ACTIVE brand's own measured
    heroTreatment/inventory (never another brand's file), or paints the plain panel
    surface. None = no panel declared (every existing composition, byte-unchanged)."""
    def _is_panel_treatment(t) -> bool:
        # kind alone is not enough: `panel-on-media` targeting a TEXT slot is the
        # overlay grammar's text-chip (G1), not the art panel. The art panel is the
        # treatment whose target IS the section's background/panel surface.
        if not isinstance(t, dict) or t.get("sanctioned", True) is False:
            return False
        if (t.get("kind") or "").lower() not in _ART_PANEL_KINDS:
            return False
        target = str(t.get("target") or "").lower()
        return target in ("background", "panel", "section", "")

    treat = any(_is_panel_treatment(t) for t in (section.get("treatments") or []))
    bg = next((s for s in _slots(section) if _is_art_panel_bg_slot(s)), None)
    if not treat and bg is None:
        return None
    # A background slot claimed by a sanctioned TEXT-ON-MEDIA treatment is the
    # LAYERED full-bleed hero (copy directly on the photo — _media_layers),
    # not the inset art panel: without this, any brand whose hero is a true
    # photo band got hijacked into a rounded panel (hubspot-v2 2026-07). An
    # explicit panel treatment still wins (that IS the declared device).
    if not treat and bg is not None:
        bg_name = str(bg.get("name") or "").lower()
        for t in (section.get("treatments") or []):
            if not isinstance(t, dict) or t.get("sanctioned", True) is False:
                continue
            if (t.get("kind") or "").lower() != "text-on-media":
                continue
            target = str(t.get("target") or "").lower()
            if target in ("background", "panel", bg_name):
                return None
    payload: dict = {"asset": _asset_src(bg) if bg else None}
    # EVENT-POSTER slots (event-scaffolds 2026-07), each authored-only so every
    # existing panel hero keeps its exact payload shape semantics:
    #   - a bound EYEBROW slot flags the panel to render the eyebrow register (the
    #     text itself rides _hero_section_copy → copy['eyebrow'] as usual);
    #   - a META-role caption slot (the poster's date/place line) passes its text
    #     through for the caption register between body and actions.
    slots = _slots(section)
    if _slot_text(_by_role(slots, "eyebrow"), "eyebrow", "text"):
        payload["eyebrow"] = True
    meta = _slot_text(_by_role(slots, "meta", "details", "schedule", "when"),
                      "text", "caption", "label")
    if meta:
        payload["meta"] = meta
    return payload


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

def _logo_item_mapping(item: dict | str) -> dict | None:
    """Route ONE logo-wall entry (a list-copy item OR a whole logo slot) on DISK
    EVIDENCE (AS-33): an asset src that survived ``_sanitize_assets`` (rewritten to
    ``assets/<name>`` because the file exists in the brand dir) renders as a REAL
    logo image in the logo-strip device; an entry whose file does not exist on disk
    (src dropped by the sanitizer, or never declared) falls back to the uppercase
    text-caption device — a filename in a composition is NOT evidence, the file is.
    Alt text derives from the entry's own metadata (alt/label) or the asset filename,
    never a brand-named literal (AS-29). Returns None for an entry with neither a
    usable image nor any text (nothing is invented for it).

    A BARE STRING entry (AS-34, blocker-1) is accepted defensively as a text caption —
    the sanitizer normally coerces strings first (with disk-evidence routing for
    filename strings), but a direct caller must never crash or silently drop one."""
    if isinstance(item, str):
        item = {"text": item}
    if not isinstance(item, dict):
        return None
    a = item.get("asset")
    src = a.get("src") if isinstance(a, dict) else (a if isinstance(a, str) else None)
    label = (item.get("alt")
             or (a.get("alt") if isinstance(a, dict) else None)
             or item.get("text") or item.get("label") or "").strip()
    if isinstance(src, str) and src.startswith("assets/"):
        alt = label or Path(src).stem.replace("-", " ").replace("_", " ").strip()
        return {"slot": "logo-strip", "role": "logo item", "contract": "logo",
                "usage": {"src": src, "alt": alt, "variant": "strip"}}
    if label:
        return {"slot": "flow", "role": "logo item", "contract": "caption",
                "usage": {"text": label, "case": "upper"}}
    return None


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
        # (value/prefix/suffix/columns/rows: the stat + table contract vocabulary, W4)
        for k in ("eyebrow", "heading", "subheading", "body", "text", "caption",
                  "label", "cta", "placeholder", "submit", "level",
                  "family", "styleHint",
                  "value", "prefix", "suffix", "columns", "rows"):
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
    if section.get("archetypeRef"):
        # GENRE-SKELETON sections are SLOT-FAITHFUL end to end (fix6, the event-hero
        # copy-first rebuild): the anatomy fixes slot NAMES while models author domain
        # role words ("event-logistics", "promise"), so the archetype vocabulary rides
        # as a NAME/CONTRACT fallback — and a slot the composition does NOT author is
        # rendered EMPTY, never back-filled from the brand's homepage SECTION_COPY
        # (the ride-through that stamped the extraction's hero eyebrow/subhead onto
        # creative heroes).
        eyebrow = eyebrow \
            or _slot_text(_by_name(slots, "kicker", "meta", "eyebrow"), "text", "label") \
            or _slot_text(_by_contract(slots, "eyebrow", "label"), "text", "label")
        subhead = subhead \
            or _slot_text(_by_name(slots, "subheading", "support", "subhead", "promise"),
                          "text", "body", "subheading")
        out = dict(cs.SECTION_COPY)
        out["eyebrow"] = eyebrow or ""
        out["subhead"] = subhead or ""
        out["cta"] = cta or ""
        return out
    out = dict(cs.SECTION_COPY)
    if eyebrow:
        out["eyebrow"] = eyebrow
    if subhead:
        out["subhead"] = subhead
    if cta:
        out["cta"] = cta
    return out


def _hero_mapping(section: dict, art_panel: bool = False) -> list[dict]:
    """blockMapping for the hero stack: wordmark logo + display-title heading + the media
    slots + the section's REAL action slots. LEGACY shape (no placement vocabulary
    anywhere): the hero/overlap pair compose_stack_hero's _pick expects. PLACED shape
    (any media slot carries §4.6.5 placement / >2 media): one entry PER media slot, each
    folding its placement into usage; the composer draws them from layout['_mediaLayers'].

    SLOT-FAITHFUL MEDIA (AS-34, blocker-2): a hero/overlap image entry is emitted only
    for a media slot the composition actually BINDS. The old shape emitted BOTH entries
    unconditionally, so a one-media (or zero-media) hero inherited the other entry's
    renderer default — WoodWave placeholder art on another brand's page. A hero with no
    media slots at all keeps the legacy pair (both srcless): that is the deliberate
    "trust the brand's default art" shape every existing WoodWave composition renders,
    and the renderer default now resolves from the ACTIVE brand's own inventory.

    SLOT-FAITHFUL ACTIONS (AS-27 hero extension, blocker-3): real `button` contract
    slots map through — compose_stack_hero renders them via render_button's law-first
    cta-shape dispatch (a `never-typographic-primary` brand gets its filled pill; a
    typographic brand's dispatch downgrades to the arrow link, unchanged). Emitted only
    when button slots exist, so legacy compositions stay byte-identical.

    ACTION-GROUP COPY (archetype-gallery 2026-07): a hero that authors its actions as
    ONE group slot (`copy.cta` string or list — the natural generation shape) expands
    each label into a real button entry; the SECOND and later actions carry a
    'secondary'-treatment familyHint so render_button resolves the brand's own
    measured non-primary register (brands without one degrade to primary and AS-59
    arbitrates). Fires only when no `button` contract slots exist (slot-faithful
    precedence unchanged)."""
    slots = _slots(section)
    title = _by_role(slots, "title", "display") or _by_contract(slots, "header", "heading")
    heading = _slot_text(title, "heading", "text") or "Everything in one place"
    media = [s for s in slots if _is_media_slot(s)]
    if art_panel:
        # the panel's z:back/full-bleed paint slot is the PANEL SURFACE, not content
        # media — exclude it so it can't map as an <img> (the composer paints it as
        # the panel background fill instead).
        media = [s for s in media if not _is_art_panel_bg_slot(s)]
    mapping = [
        {"slot": "main", "role": "wordmark (nav)", "contract": "logo", "usage": {"variant": "inverse"}},
        {"slot": "main", "role": "display title", "contract": "heading",
         "usage": {"heading": heading, "level": "display"}},
    ]
    actions = []
    for i, b in enumerate(_button_slots(section)):
        items = b.get("copy") if isinstance(b.get("copy"), list) else None
        if items:
            # ONE actionGroup slot whose copy is a LIST of action objects (the natural
            # composition shape for an archetype actionGroup slot — fix6): each item is
            # a real action; non-primary items carry their declared treatment (or the
            # quiet-secondary hint) so render_button resolves the brand's own register.
            for j, item in enumerate(x for x in items if isinstance(x, dict)):
                label = _text(item, "label", "cta", "text")
                if not label:
                    continue
                usage = {"label": label, "accent": False}
                for k in ("family", "styleHint"):
                    if str(item.get(k) or "").strip():
                        usage[k] = item[k]
                if j > 0 and "family" not in usage and "styleHint" not in usage:
                    usage["styleHint"] = str(item.get("emphasis") or item.get("variant")
                                             or "secondary outlined quiet")
                actions.append({
                    "slot": "main",
                    "role": "cta-primary" if not actions else "cta-secondary",
                    "contract": "button", "usage": usage,
                })
            continue
        label = _slot_text(b, "label", "cta", "text") or "Get started"
        actions.append({
            "slot": "main",
            "role": b.get("role") or b.get("name") or ("cta-primary" if i == 0 else "cta-secondary"),
            "contract": "button",
            "usage": _button_usage(b, label),
        })
    if not actions:
        for i, label in enumerate(_group_cta_labels(section)):
            usage = {"label": label, "accent": False}
            if i > 0:
                usage["styleHint"] = "secondary outlined quiet"
            actions.append({
                "slot": "main",
                "role": "cta-primary" if i == 0 else "cta-secondary",
                "contract": "button", "usage": usage,
            })
    # SLOT-FAITHFUL ANATOMY DEVICES (fix6, archetype sections only). A genre skeleton
    # binds its WHOLE anatomy in slots; three device families the legacy hero mapping
    # never carried now map through — absent the ref the mapping is byte-identical:
    #   - logo-family slot (agenda/track/award rail): per-item mark entries + the
    #     rail's one caption line, drawn after the actions;
    #   - form slot (search-first / capture anatomy): the brand's form block, folded
    #     from the slot's field/submit/note copy;
    #   - link slot with list copy (quiet link rail): one arrow-link entry per item.
    if section.get("archetypeRef"):
        for s in slots:
            contract = (s.get("contract") or "").lower()
            sname = s.get("name") or "rail"
            if contract.startswith("logo"):
                c = s.get("copy") if isinstance(s.get("copy"), dict) else {}
                items = next((v for v in c.values()
                              if isinstance(v, list) and any(isinstance(x, dict) for x in v)), [])
                for item in items:
                    src = _asset_src(item) if isinstance(item, dict) else None
                    if not src:
                        continue
                    actions.append({
                        "slot": "main", "role": f"rail mark ({sname})",
                        "contract": "logo",
                        "usage": {"src": src, "alt": _text(item, "alt", "text") or ""}})
                cap = _text(c, "caption", "text")
                if cap:
                    actions.append({
                        "slot": "main", "role": f"rail caption ({sname})",
                        "contract": "caption", "usage": {"text": cap}})
            elif contract == "form":
                c = s.get("copy") if isinstance(s.get("copy"), dict) else {}
                fields = [f for f in (c.get("fields") or []) if isinstance(f, dict)]
                actions.append({
                    "slot": "main", "role": f"foot form ({sname})",
                    "contract": "form",
                    "usage": {"placeholder": _text(fields[0] if fields else c,
                                                   "placeholder", "label") or "Search",
                              "submit": _text(c, "submit", "cta") or "Submit"}})
                note = _text(c, "note")
                if note:
                    # the note is the form's STATED REASON (AS-14) — body register,
                    # drawn ABOVE the field by the composer, never a caption microlabel.
                    actions.append({"slot": "main", "role": f"foot form note ({sname})",
                                    "contract": "paragraph", "usage": {"text": note}})
            elif contract == "link" and isinstance(s.get("copy"), list):
                for item in s["copy"]:
                    label = _text(item, "label", "text") if isinstance(item, dict) \
                        else (item if isinstance(item, str) else None)
                    if label:
                        # quiet register (single-accent invariant): the rail is
                        # secondary wayfinding — never the page's committed accent.
                        # `text` rides along so the inline-copy props path (the one
                        # that honors accent:False) handles the entry.
                        actions.append({
                            "slot": "main", "role": f"rail link ({sname})",
                            "contract": "link",
                            "usage": {"label": label, "text": label,
                                      "accent": False}})
    if not art_panel and _media_layers(section) is not None:
        for s in media:
            entry = _slot_to_mapping(s)
            entry["slot"] = "main"
            entry["role"] = f"placed media ({s.get('name') or s.get('role') or 'media'})"
            mapping.append(entry)
        return mapping + actions
    if art_panel:
        # slot-faithful ONLY: the panel hero maps each bound content-media slot 1:1
        # and never invents the legacy hero/overlap pair.
        for s in media:
            entry = _slot_to_mapping(s)
            entry["slot"] = "main"
            entry["role"] = f"panel media ({s.get('name') or s.get('role') or 'media'})"
            mapping.append(entry)
        return mapping + actions
    # SLOT-FAITHFUL SKELETONS (spec/archetype-library.md): a hero instantiating a
    # genre archetype binds its whole anatomy in slots — a zero-media composition
    # means a text-forward band, never "trust the brand's default art" (the legacy
    # replica-shape below, which layers invented photography OVER the display title —
    # right for the extracted layered hero, wrong for a monument/value-forward stack).
    if not media and section.get("archetypeRef"):
        return mapping + actions
    hero_src = _asset_src(media[0]) if len(media) >= 1 else None
    over_src = _asset_src(media[1]) if len(media) >= 2 else None
    if len(media) >= 1 or not media:
        # legacy zero-media shape keeps BOTH srcless entries (brand default art);
        # a bound hero slot maps 1:1.
        mapping.append({"slot": "main", "role": "hero photography", "contract": "image",
                        "usage": {"ratio": "landscape", "radius": "0",
                                  **({"src": hero_src} if hero_src else {})}})
    if len(media) >= 2 or not media:
        mapping.append({"slot": "main", "role": "overlap photography", "contract": "image",
                        "usage": {"ratio": "portrait", "radius": "0",
                                  **({"src": over_src} if over_src else {})}})
    return mapping + actions


def _button_slots(section: dict) -> list[dict]:
    """The section's real `button` contract slots (B5: these used to be dropped)."""
    return [s for s in _slots(section) if (s.get("contract") or "").lower() == "button"]


def _group_cta_labels(section: dict) -> list[str]:
    """Action labels authored as ONE group slot: any non-button slot whose dict copy
    carries ``cta`` (string or list of strings). [] when the section binds none —
    every existing composition (which authors per-action `button` slots or none)
    is untouched."""
    for s in _slots(section):
        c = s.get("copy")
        if not isinstance(c, dict) or not c.get("cta"):
            continue
        v = c["cta"]
        if isinstance(v, str) and v.strip():
            return [v.strip()]
        if isinstance(v, list):
            labels = [str(x).strip() for x in v if isinstance(x, str) and str(x).strip()]
            if labels:
                return labels
    return []


def _button_usage(slot: dict, label: str) -> dict:
    """Button usage payload: the slot's declared treatment (family / styleHint)
    rides along (sysfix 2026-07: the split/conversion builders emitted bare
    label+accent, so a declared 'outlined' secondary lost its family and rendered
    as a second primary pill)."""
    usage = {"label": label, "accent": False}
    copy = slot.get("copy") if isinstance(slot.get("copy"), dict) else {}
    for k in ("family", "styleHint"):
        if str((copy or {}).get(k) or "").strip():
            usage[k] = copy[k]
    return usage


def _has_form_slot(section: dict) -> bool:
    return any((s.get("contract") or "").lower() in ("form", "input", "form-field")
               for s in _slots(section))


def _cta_copy(section: dict) -> dict:
    slots = _slots(section)
    header = _by_role(slots, "heading", "title") or _by_contract(slots, "header", "heading")
    form = _by_contract(slots, "form", "input") or _by_role(slots, "signup", "form", "field")
    formcopy = (form or {}).get("copy") if isinstance((form or {}).get("copy"), dict) else {}
    # body: a body-role slot first, then the header block's own body/text key (a v1
    # header copy dict carries the lede under `text` — dropping it left the CTA bare).
    body = _slot_text(_by_role(slots, "body", "sub", "lede"), "text", "body") \
        or _text((header or {}).get("copy"), "body", "text") or ""
    return {
        # NO invented eyebrow (sysfix 2026-07): a conversion that authored none renders
        # none — the render_header eyebrow slot is OPTIONAL and elides on empty; the
        # old "Introducing" default was fabricated copy on every button-only banner.
        "eyebrow": _slot_text(_by_role(slots, "eyebrow"), "eyebrow", "text")
        or _text((header or {}).get("copy"), "eyebrow") or "",
        "heading": _slot_text(header, "heading", "text") or "Start today",
        "body": body,
        "placeholder": (formcopy or {}).get("placeholder", "you@company.com"),
        "cta": (formcopy or {}).get("submit")
        or _slot_text(_by_role(slots, "action", "cta"), "label", "cta") or "Start free",
    }


def _cta_mapping(section: dict) -> list[dict]:
    """blockMapping for the conversion stack. SLOT-FAITHFUL (B5, fix-batch 2026-07):
    real `button` contract slots are PRESERVED (they render through render_button's
    cta-shape dispatch — the filled CTA a corporate brand's gate demands); the signup
    form entry is emitted only when the section binds a form slot OR binds no explicit
    action at all (the legacy shape every existing WoodWave conversion renders)."""
    mapping = [
        {"slot": "main", "role": "heading", "contract": "header",
         "usage": {"level": "h2"}},
    ]
    buttons = _button_slots(section)
    for i, b in enumerate(buttons):
        label = _slot_text(b, "label", "cta", "text") or "Get started"
        mapping.append({
            "slot": "main",
            "role": b.get("role") or b.get("name") or ("cta-primary" if i == 0 else "cta-secondary"),
            "contract": "button",
            "usage": _button_usage(b, label),
        })
    if _has_form_slot(section) or not buttons:
        mapping.append({"slot": "main", "role": "newsletter form (underline only)",
                        "contract": "form", "usage": {"variant": "underline"}})
    return mapping


def _cards_copy(section: dict) -> dict:
    """features `cards`: intro eyebrow/heading + N modules (each caption + body [+ link]).
    A TESTIMONIAL run under the cards archetype (the quote-card grid a testimonial
    pattern seeds) is the same module shape: quote→body, name (+ role)→caption."""
    slots = _slots(section)
    header = _by_role(slots, "section-title", "title", "heading") or _by_contract(slots, "header")
    module_slot = _by_role(slots, "module", "value-prop", "feature", "card", "prop") \
        or _by_contract(slots, "testimonial", "quote", "feature-item", "card")
    modules = _repeatable_copy(module_slot)
    # DECLARED slot mediaAspect (hubspot-v2 2026-07): a module slot whose pattern
    # recorded the card-media frame (e.g. `mediaAspect: square` measured from the
    # source's 1:1 product-UI wells) is honored as the per-card fallback — a module's
    # own `aspect:` still wins. Slots without the fact keep the composer default.
    slot_aspect = ASPECT_CSS.get(str((module_slot or {}).get("mediaAspect") or "").lower())
    if not modules:  # fall back: each non-intro slot is a module
        modules = [s.get("copy") for s in slots
                   if isinstance(s.get("copy"), dict) and s is not header]
        modules = [m for m in modules if m]
    cards = []
    for m in modules:
        # asset: the sanitizer normalizes a bare module asset name into {src, alt} —
        # unwrap to STRINGS here so the composer never string-interpolates a dict into
        # the src path (the `assets/{'src': …}` malformation, fix-batch 2026-07).
        asset = m.get("asset")
        alt = m.get("alt")
        if isinstance(asset, dict):
            alt = alt or asset.get("alt")
            asset = asset.get("src")
        name = (m.get("name") or "").strip()
        who = ", ".join(x for x in (name, (m.get("role") or "").strip()) if x)
        card = {
            "caption": m.get("heading") or m.get("caption") or m.get("title") or who,
            "body": m.get("text") or m.get("body") or m.get("quote") or "",
            "link": m.get("link") or m.get("cta"),
            "asset": asset,
            "alt": alt,
            "aspect": m.get("aspect") or slot_aspect,
        }
        # CARD EYEBROW anatomy (fid6 2026-07): a module authoring its OWN microlabel
        # carries eyebrow + heading as separate registers — the composer renders the
        # eyebrow→heading→body→cta ladder instead of folding the heading into the
        # caption tier. Modules without an eyebrow keep the caption fold unchanged.
        if str(m.get("eyebrow") or "").strip():
            card["eyebrow"] = str(m["eyebrow"]).strip()
            card["heading"] = m.get("heading") or m.get("title") or ""
        elif str(m.get("heading") or m.get("title") or "").strip():
            # an EXPLICITLY authored heading passes through as one (hubspot-v2
            # 2026-07): the composer's mark-media feature-card path renders it at
            # the card register ("the feature-card ladder is mark → heading → body
            # → link"); modules without media-treatment facts never read the key,
            # so caption-fold brands stay byte-identical.
            card["heading"] = str(m.get("heading") or m.get("title")).strip()
        # PERSON attribution (fid2 2026-07): a testimonial module carrying an avatar
        # asset and/or an authored name/role passes them through — the composer
        # renders the avatar + name/role person row instead of a bare caption line.
        avatar = m.get("avatar")
        if isinstance(avatar, dict):
            avatar = avatar.get("src")
        if avatar:
            card["avatar"] = avatar
        if name:
            card["name"] = name
        if str(m.get("personRole") or m.get("role") or "").strip():
            card["role"] = str(m.get("personRole") or m.get("role")).strip()
        cards.append(card)
    hdr_copy = (header or {}).get("copy")
    return {
        "eyebrow": _slot_text(_by_role(slots, "eyebrow"), "eyebrow", "text")
        or _text(hdr_copy, "eyebrow"),
        "heading": _slot_text(header, "heading", "text") or "",
        # intro SUBHEAD (event-scaffolds 2026-07): the module composers already
        # render layout-copy `subhead` under the intro header — the translator now
        # carries an authored body-role slot (or the header's own body key) through
        # instead of silently dropping it. Absent ⇒ "" ⇒ elides (unchanged pages).
        "subhead": _slot_text(_by_role(slots, "body", "sub", "lede"), "text", "body")
        or (_text(hdr_copy, "body", "text") if isinstance(hdr_copy, dict) else "") or "",
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


# ── event scaffolds (2026-07): bento / pricing-tiers / signup-form / faq vocabulary ──

def _bento_stamp(knob) -> dict | None:
    """Validate the composition's `knobs.bento` → the `_bento` stamp compose_bento_grid
    + layout_placement_css consume. Pattern-fact-driven knobs (AS-44 discipline —
    facts validated here once, structural defaults are the composer's degrade):
      cells:      [{span 3–12, rows 1–2, surface <sanctioned role str>, lead bool}]
                  index-aligned with the section's module copy;
      gap:        CSS length for the mosaic gap (e.g. the measured card-grid gutter);
      collapseAt: px tier where the mosaic folds to one column (the brand's own
                  measured collapse register).
    Returns None for a malformed knob (section renders as the plain module grid)."""
    if knob is True:
        return {"cells": []}
    if not isinstance(knob, dict):
        return None
    cells = []
    for c in (knob.get("cells") or []):
        c = c if isinstance(c, dict) else {}
        cell: dict = {}
        if isinstance(c.get("span"), (int, float)):
            cell["span"] = max(3, min(12, int(c["span"])))
        if isinstance(c.get("rows"), (int, float)):
            cell["rows"] = max(1, min(2, int(c["rows"])))
        if isinstance(c.get("start"), (int, float)):     # explicit track (e.g. a
            cell["start"] = max(1, min(12, int(c["start"])))  # centered solo cell)
        if str(c.get("surface") or "").strip():
            cell["surface"] = str(c["surface"]).strip()
        if c.get("lead"):
            cell["lead"] = True
        cells.append(cell)
    stamp: dict = {"cells": cells}
    if str(knob.get("gap") or "").strip():
        stamp["gap"] = str(knob["gap"]).strip()
    if isinstance(knob.get("collapseAt"), (int, float)):
        stamp["collapseAt"] = int(knob["collapseAt"])
    return stamp


def _tiers_stamp(knob) -> dict | None:
    """Validate `knobs.tiers` → the `_tiers` stamp compose_pricing_tiers consumes.
      emphasize:       index of the ONE emphasized tier;
      emphasisSurface: sanctioned surface ROLE its head band paints (resolved through
                       the token layer by the composer; unknown role degrades to the
                       border ring);
      gap / collapseAt: same knob semantics as the bento stamp."""
    if knob is True:
        return {}
    if not isinstance(knob, dict):
        return None
    stamp = {}
    if isinstance(knob.get("emphasize"), (int, float)):
        stamp["emphasize"] = int(knob["emphasize"])
    if str(knob.get("emphasisSurface") or "").strip():
        stamp["emphasisSurface"] = str(knob["emphasisSurface"]).strip()
    if str(knob.get("gap") or "").strip():
        stamp["gap"] = str(knob["gap"]).strip()
    if isinstance(knob.get("collapseAt"), (int, float)):
        stamp["collapseAt"] = int(knob["collapseAt"])
    return stamp


def _tiers_copy(section: dict) -> dict:
    """pricing `cards`: intro eyebrow/heading/subhead + N TIER modules — each name
    (caption register) / price + priceMeta / tagline / features[] / cta (+ ctaFamily)
    — + an optional trailing note caption. Everything authored; missing keys elide."""
    slots = _slots(section)
    header = _by_role(slots, "section-title", "title", "heading") or _by_contract(slots, "header")
    tier_slot = _by_role(slots, "tier", "plan", "module") \
        or _by_contract(slots, "tier", "feature-item", "card")
    tiers = []
    for m in _repeatable_copy(tier_slot):
        tiers.append({
            "name": m.get("name") or m.get("heading") or m.get("caption") or "",
            "price": m.get("price") or "",
            "priceMeta": m.get("priceMeta") or m.get("unit") or "",
            "tagline": m.get("tagline") or m.get("body") or m.get("text") or "",
            "features": [str(f).strip() for f in (m.get("features") or [])
                         if str(f).strip()],
            "cta": m.get("cta") or m.get("label") or "",
            "ctaFamily": m.get("ctaFamily") or m.get("family") or "",
        })
    hdr_copy = (header or {}).get("copy")
    return {
        "eyebrow": _slot_text(_by_role(slots, "eyebrow"), "eyebrow", "text")
        or _text(hdr_copy, "eyebrow") or "",
        "heading": _slot_text(header, "heading", "text") or "",
        "subhead": _slot_text(_by_role(slots, "body", "sub", "lede"), "text", "body")
        or (_text(hdr_copy, "body", "text") if isinstance(hdr_copy, dict) else "") or "",
        "note": _slot_text(_by_role(slots, "note", "fineprint", "footnote"),
                           "text", "caption") or "",
        "tiers": tiers,
    }


def _tiers_mapping(section: dict) -> list[dict]:
    """blockMapping for a pricing-tiers section (gate traceability + slot resolution,
    same discipline as _cards_mapping): header entry, then per tier its name caption,
    price heading, tagline paragraph, feature captions and button action."""
    slots = _slots(section)
    tier_slot = _by_role(slots, "tier", "plan", "module") \
        or _by_contract(slots, "tier", "feature-item", "card")
    mapping: list[dict] = [{"slot": "main", "role": "heading", "contract": "header",
                            "usage": {"level": "h2"}}]
    for i, m in enumerate(_repeatable_copy(tier_slot)):
        name = m.get("name") or m.get("heading") or m.get("caption") or f"tier {i + 1}"
        mapping.append({"slot": "tiers", "role": f"tier name {i + 1}",
                        "contract": "caption", "usage": {"text": name, "case": "upper"}})
        if m.get("price"):
            mapping.append({"slot": "tiers", "role": f"tier price {i + 1}",
                            "contract": "heading",
                            "usage": {"heading": str(m["price"]), "level": "h3"}})
        body = m.get("tagline") or m.get("body") or m.get("text") or ""
        if body:
            mapping.append({"slot": "tiers", "role": f"tier tagline {i + 1}",
                            "contract": "paragraph", "usage": {"text": body}})
        cta = m.get("cta") or m.get("label") or ""
        if cta:
            usage = {"label": cta, "accent": False}
            if str(m.get("ctaFamily") or m.get("family") or "").strip():
                usage["family"] = str(m.get("ctaFamily") or m.get("family")).strip()
            mapping.append({"slot": "tiers", "role": f"tier action {i + 1}",
                            "contract": "button", "usage": usage})
    return mapping


_FORM_FIELD_KINDS = {"text", "email", "tel", "select", "radio-group", "checkbox",
                     # W12 (stress-playbook 2026-07): a declared multiline field is a
                     # REAL vocabulary member — the old whitelist silently coerced it
                     # to a single-line text input.
                     "textarea"}


def _form_fields_stamp(section: dict) -> dict | None:
    """Validate a conversion section's multi-field FORM payload → the `_formFields`
    stamp _compose_signup_form consumes. The fields live on the form slot's copy
    (`fields: [...]`), microcopy beside them (consent / success / meta). Field keys:
    kind (vocabulary above; unknown → text), label (REQUIRED — an unlabeled control
    is dropped, never rendered bare), name, placeholder, helper, options[],
    checkedIndex, required, span (half|full), autocomplete. None ⇒ no multi-field
    payload (the classic single-line newsletter device renders unchanged)."""
    form = _by_contract(_slots(section), "form", "input") \
        or _by_role(_slots(section), "signup", "form")
    formcopy = (form or {}).get("copy")
    if not isinstance(formcopy, dict) or not isinstance(formcopy.get("fields"), list):
        return None
    fields = []
    for f in formcopy["fields"]:
        if not isinstance(f, dict) or not str(f.get("label") or "").strip():
            continue
        kind = str(f.get("kind") or "text").lower()
        field = {"kind": kind if kind in _FORM_FIELD_KINDS else "text",
                 "label": str(f["label"]).strip()}
        # `error` is authored VALIDATION MICROCOPY — carried as a data-error attr on
        # the control (static markup; no JS is invented to display it).
        for k in ("name", "placeholder", "helper", "autocomplete", "error"):
            if str(f.get(k) or "").strip():
                field[k] = str(f[k]).strip()
        if str(f.get("span") or "").lower() == "half":
            field["span"] = "half"
        if f.get("required"):
            field["required"] = True
        opts = [str(o).strip() for o in (f.get("options") or []) if str(o).strip()]
        if opts:
            field["options"] = opts
        if isinstance(f.get("checkedIndex"), (int, float)):
            field["checkedIndex"] = int(f["checkedIndex"])
        fields.append(field)
    if not fields:
        return None
    stamp: dict = {"fields": fields}
    for k in ("consent", "success", "meta"):
        if str(formcopy.get(k) or "").strip():
            stamp[k] = str(formcopy[k]).strip()
    # panel copy (fix6, form-split hero): the form's OWN header/submit/note ride the
    # stamp so the capture-panel composer can voice them. The conversion composer
    # reads none of these keys — every existing signup renders byte-identically.
    header = formcopy.get("header") if isinstance(formcopy.get("header"), dict) else {}
    for k, v in (("heading", _text(header, "heading", "text")
                  or _text(formcopy, "heading")),
                 ("submit", _text(formcopy, "submit", "cta")),
                 ("note", _text(formcopy, "note"))):
        if v:
            stamp[k] = v
    return stamp


def _faq_copy(section: dict) -> dict:
    """faq stack → compose_faq_accordion copy keys: eyebrow / heading / items
    [(question, answer)] from the section's repeatable item slot."""
    slots = _slots(section)
    header = _by_role(slots, "heading", "title") or _by_contract(slots, "header")
    item_slot = _by_role(slots, "faq", "question", "item") \
        or _by_contract(slots, "faq-item", "disclosure", "feature-item")
    items = []
    for m in _repeatable_copy(item_slot):
        q = str(m.get("question") or m.get("heading") or m.get("caption") or "").strip()
        a = str(m.get("answer") or m.get("text") or m.get("body") or "").strip()
        if q and a:
            items.append((q, a))
    hdr_copy = (header or {}).get("copy")
    return {
        "eyebrow": _slot_text(_by_role(slots, "eyebrow"), "eyebrow", "text")
        or _text(hdr_copy, "eyebrow") or "",
        "heading": _slot_text(header, "heading", "text") or "",
        # intro paragraph + closing action are OPTIONAL anatomy (the agenda shape);
        # absent keys elide in the composer (SafeCopy), so bare FAQs are unchanged.
        "intro": _slot_text(_by_role(slots, "body", "lede", "sub"), "text", "body")
        or (_text(hdr_copy, "body", "text") if isinstance(hdr_copy, dict) else "") or "",
        "cta": _slot_text(_by_role(slots, "action", "cta", "link"),
                          "label", "cta", "text") or "",
        "items": items,
    }


def _faq_mapping(section: dict) -> list[dict]:
    """blockMapping for a composed FAQ (gate traceability): header + one caption/
    paragraph pair per disclosure row."""
    slots = _slots(section)
    item_slot = _by_role(slots, "faq", "question", "item") \
        or _by_contract(slots, "faq-item", "disclosure", "feature-item")
    mapping: list[dict] = [{"slot": "main", "role": "heading", "contract": "header",
                            "usage": {"level": "h2"}}]
    for i, m in enumerate(_repeatable_copy(item_slot)):
        q = str(m.get("question") or m.get("heading") or m.get("caption") or "").strip()
        a = str(m.get("answer") or m.get("text") or m.get("body") or "").strip()
        if q:
            mapping.append({"slot": "faq", "role": f"question {i + 1}",
                            "contract": "caption", "usage": {"text": q}})
        if a:
            mapping.append({"slot": "faq", "role": f"answer {i + 1}",
                            "contract": "paragraph", "usage": {"text": a}})
    return mapping


def _faq_stamp(knob) -> dict:
    """Validate `knobs.faq` → the `_faq` stamp (AS-40 hardening knobs): exclusive
    (one open member at a time via <details name>) + open (the evidence-driven
    open-item index; absent = all closed, the degrade) + the state-grammar role
    refs (activeSurface / hoverWash — the accordion inset-emphasis vocabulary; the
    composer resolves them through the token layer, unknown roles degrade)."""
    stamp: dict = {"exclusive": True}
    if isinstance(knob, dict):
        if knob.get("exclusive") is False:
            stamp["exclusive"] = False
        if isinstance(knob.get("open"), (int, float)):
            stamp["open"] = int(knob["open"])
        for k in ("activeSurface", "hoverWash"):
            if str(knob.get(k) or "").strip():
                stamp[k] = str(knob[k]).strip()
    return stamp


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
    # contract fallback includes `heading` (archetype-gallery 2026-07): a heading
    # slot under a domain role name (e.g. role "hub-promise") is still THE heading —
    # role keywords first (unchanged), the declared contract as the honest fallback
    # (same lookup _hero_section_copy always used).
    header = _by_role(slots, "heading", "title") or _by_contract(slots, "header", "heading")
    panel = _by_role(slots, "panel", "rows", "list", "prices")
    rows = []
    row_icons: list[str] = []
    row_media: list[str] = []
    for m in _repeatable_copy(panel):
        label = m.get("label") or m.get("heading") or m.get("title") or ""
        val = m.get("value") or m.get("text") or ""
        if label:
            rows.append((label, val))
            row_icons.append(str(m.get("icon") or ""))
            # per-item MEDIA binding (fid5 2026-07): an item's own media asset rides
            # beside the rows so the accordion device can swap the counterweight
            # well to the ACTIVE item's asset; all-empty degrades to the slot media.
            row_media.append(str(m.get("media") or ""))
    if not rows:                                   # fold value_props modules into ruled rows
        for m in _module_copies(slots):
            label = m.get("heading") or m.get("label") or m.get("title") or ""
            val = m.get("text") or m.get("body") or m.get("value") or ""
            if label:
                rows.append((label, val))
                row_icons.append(str(m.get("icon") or ""))
                row_media.append(str(m.get("media") or ""))

    def first(*keys: str) -> str:
        """First non-empty string under any of `keys` across the section's DICT-shaped
        slot copy. Plain-string copy is EXCLUDED here (pass2 finding): `_text`'s str
        passthrough matches ANY key, so this last-resort scan used to leak whatever
        string slot came first into the body/quote lookups (the blog's eyebrow kicker
        rendered as the hero body paragraph). Role/contract lookups keep the str
        passthrough — a slot they match means its string."""
        for s in slots:
            if isinstance(s.get("copy"), dict):
                v = _text(s.get("copy"), *keys)
                if v:
                    return v
        return ""

    out = {
        # eyebrow: role keyword → the header's OWN dict eyebrow → the declared
        # eyebrow contract. The header fallback is dict-guarded (pass2 finding): a
        # plain-string heading copy used to echo THE HEADING into the eyebrow via the
        # str passthrough whenever the model's role words dodged the keyword table.
        "eyebrow": _slot_text(_by_role(slots, "eyebrow"), "eyebrow", "text")
        or (_text((header or {}).get("copy"), "eyebrow")
            if isinstance((header or {}).get("copy"), dict) else None)
        or _slot_text(_by_contract(slots, "eyebrow"), "eyebrow", "text") or "",
        # the section's own display heading (sysfix 2026-07: the key union was
        # missing it — out["heading"] below raised KeyError on quote-less splits)
        "heading": _slot_text(header, "heading", "text") or "",
        # NO invented panel title / cta (sysfix 2026-07): "Details" / "Learn more" were
        # fabricated copy on any split that authored neither; the split composers now
        # elide the empty panel-title/action devices instead.
        "panelTitle": _slot_text(panel, "heading", "title") or "",
        "rows": rows,
        # per-row ICONS (fid2 2026-07): authored item icons ride beside the rows so
        # the accordion device can render the brand's own product-family marks;
        # all-empty degrades to no icon column.
        "rowIcons": row_icons,
        # per-row MEDIA (fid5 2026-07): authored item media assets for the accordion
        # media-swap device; all-empty keeps the single slot-bound media path.
        "rowMedia": row_media,
        "cta": _slot_text(_by_role(slots, "action", "cta", "link"), "label", "cta") or "",
        "caption": _slot_text(_by_role(slots, "caption"), "caption", "text") or "",
        # AUTHORED HEADING REGISTER (W5, stress-playbook 2026-07): a header slot
        # declaring copy.level carries it through so the info-band's intro heading is
        # demotable — absent, the adapter's non-hero default (section tier) applies.
        "headingLevel": str((_text((header or {}).get("copy"), "level")
                             if isinstance((header or {}).get("copy"), dict) else "")
                            or "").strip().lower(),
    }
    # about-statement / curator-quote keys: surface the section's own slot copy.
    # Role keywords first (unchanged); the declared `paragraph` contract is the
    # honest fallback (same doctrine as the header lookup above — the model authors
    # domain role words like "hub-promise", but the contract IS the body claim).
    out["body"] = _slot_text(_by_role(slots, "body", "statement", "lede", "support",
                                      "attribution"), "text", "body") \
        or _slot_text(_by_contract(slots, "paragraph"), "text", "body") \
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
    # real `button` action slots (B5): surfaced as an ordered actions list so the
    # composer renders THEM (primary via render_button's cta-shape dispatch) instead of
    # downgrading every action to the single copy-driven arrow link. Emitted only when
    # button slots exist, so legacy sections (no `actions` key) stay byte-identical.
    buttons = _button_slots(section)
    if buttons:
        out["actions"] = [
            {"label": _slot_text(b, "label", "cta", "text") or "Get started"}
            for b in buttons]
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
    alt = ""
    if isinstance(media, dict):
        aspect = ASPECT_CSS.get((media.get("mediaAspect") or "").lower())
        # AUTHORED ALT (W9, stress-playbook 2026-07): the slot's own asset.alt rides
        # through — the composer used to fall straight to its brand-default alt,
        # overwriting the composition's authored description.
        a = media.get("asset")
        if isinstance(a, dict) and str(a.get("alt") or "").strip():
            alt = str(a["alt"]).strip()
    evidence = None
    knobs = section.get("knobs") if isinstance(section.get("knobs"), dict) else {}
    if knobs.get("interlockEvidence"):
        evidence = knobs["interlockEvidence"]
    return {
        "caption": cap,
        "statement": _slot_text(statement, "heading", "text") or "",
        "asset": _asset_src(media),
        "alt": alt,
        "support": support,
        "cta": cta,
        "mediaAspectCss": aspect,
        "mediaOrientation": ((media or {}).get("mediaAspect")
                             if isinstance(media, dict) else None),
        "interlockEvidence": evidence,
    }


_COPY_TRANSLATORS = {
    "collage": _collage_copy,
    "split": _split_copy,
    "cards": _cards_copy,
    "stack-fullbleed": _gallery_copy,
    "media-split": _interlock_copy,
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
    raw_intent = (section.get("surfaceIntent") or "any").strip().lower()
    surface_intent = SURFACE_INTENT_MAP.get(raw_intent) or f"surface/{raw_intent}"

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
    # ARCHETYPE-declared header context rides through first (fix5 2026-07): the
    # skeleton's anatomy states its own grammar rung (apply_archetype_skeleton
    # stamps it on the section) — an explicit structural fact, so it outranks the
    # split+table inference below. Without it an overlay/banded renderer archetype
    # mapped to NO grammar rung and the header stack fell to the style default.
    if section.get("_headerContext") in ("splitColumn", "standaloneStack"):
        layout["_headerContext"] = section["_headerContext"]
    # A split renderer may carry a HEADER ABOVE the split rather than inside either
    # column (comparison/info-band anatomy). Stamp the actual header context so the
    # shared alignment chain consults standaloneStack in the captured brand grammar.
    # Content below being two columns is not itself evidence for splitColumn alignment.
    elif archetype == "split" and (
            (section.get("useCase") or "").lower() in ("comparison", "table")
            or any((s.get("contract") or "").lower() == "table" for s in _slots(section))):
        layout["_headerContext"] = "standaloneStack"
    # seededFrom → patternRef (drives resolve_pattern → pattern_treatment_css stagger/knobs).
    seeded = section.get("seededFrom")
    if isinstance(seeded, dict) and seeded.get("id"):
        layout["patternRef"] = {"lib": seeded.get("lib", "project"), "id": seeded["id"]}
    if isinstance(section.get("knobs"), dict):
        layout["variantKnobs"] = section["knobs"]
    # genre-archetype provenance (spec/archetype-library.md): the chosen skeleton id
    # rides through so the wrapper stamp + audits can see it; the bandHeight knob
    # becomes a per-section rhythm hint (compose_section.band_height_css — a multiplier
    # over the brand's OWN section-padding token, never a foreign length). Both are
    # fact-gated: sections without the ref/knob keep the layout byte-identical.
    if section.get("archetypeRef"):
        layout["archetypeRef"] = str(section["archetypeRef"])
    band = al.normalize_band_height((section.get("knobs") or {}).get("bandHeight"))
    if band:
        layout["_bandHeight"] = band

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
    # INSET ART-PANEL hero detection (AS-37, schema-gap 9) — BEFORE the placed-media
    # classification: the panel's z:back/full-bleed background slot is the panel's
    # PAINT, not a text-on-media background layer, so a panel hero must not also
    # trigger the layered/scrim path off that same slot.
    use_case = (section.get("useCase") or "").lower()
    art_panel = _art_panel_payload(section) if use_case == "hero" else None
    layers = _media_layers(section) if (archetype == "stack" and art_panel is None) else None
    if layers is not None:
        layout["_mediaLayers"] = layers
        # the sanctioned text-on-media treatment may DECLARE the scrim wash class
        # over the z:back layer (scrim-band's fill.opacityClass vocabulary, plus
        # `none` for art whose contrast tint is baked into the photograph itself —
        # measured, not defaulted). Absent = the composer's flat default wash.
        # A MEASURED scrim paint (fix1 2026-07, hero-overlay punch item) may ride
        # `fill.color` instead: the brand's own captured overlay color (e.g. the
        # source's ::after gradient resolved to one flat rgba) — validated as a
        # color literal and painted verbatim by the layered-hero composer. Brands
        # without the fact keep the class ladder / default wash byte-identically.
        for t in (section.get("treatments") or []):
            if isinstance(t, dict) and t.get("sanctioned", True) is not False \
                    and (t.get("kind") or "").lower() == "text-on-media":
                fill = t.get("fill") if isinstance(t.get("fill"), dict) else {}
                color = str(fill.get("color") or "").strip()
                if re.fullmatch(r"(rgba?\([\d\s.,%]+\)|#[0-9a-fA-F]{3,8})", color):
                    layout["_bgScrimColor"] = color
                oc = str(fill.get("opacityClass") or "").lower()
                if oc in ("none", "light", "medium", "heavy"):
                    layout["_bgScrimClass"] = oc
                break
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

    # blockMapping + composer copy. Disambiguate the `stack` archetype by EVIDENCE
    # (fix-batch 2026-07, N2: the old rule forced EVERY non-hero stack into the
    # conversion composer, collapsing logos/testimonial/footer stacks into
    # near-identical invented signup forms):
    #   - useCase `hero` → the hero composer (unchanged);
    #   - a CONVERSION stack is one that declares a conversion useCase (cta/…) OR binds
    #     a form/input slot OR binds real button actions → the conversion composer;
    #   - any OTHER stack (logos / testimonial / footer / features-divider …) routes to
    #     the generic-flow composer with a slot-faithful mapping, so each source role
    #     keeps its own shape instead of inheriting the signup-form scaffold.
    # a hero is a STACK hero, or (AS-37) a SPLIT hero that declares the inset art-panel
    # device — the panel grid subsumes the split's two-column intent, so it routes to
    # the hero composer's panel variant instead of the info-band split.
    is_hero = use_case == "hero" and (
        archetype == "stack" or (archetype == "split" and art_panel is not None))
    _conversion_cases = {"cta", "conversion", "newsletter", "signup", "subscribe", "contact"}
    # a stack that binds a logo-contract slot is a logo-wall-role section even when it
    # also carries an action (e.g. a partner/badge strip closed by one pill): the
    # conversion scaffold would DROP the bound logo evidence (AS-33), so the logo
    # device outranks the button heuristic — generic-flow renders both.
    has_logo_slot = any((s.get("contract") or "").lower().startswith("logo")
                        for s in _slots(section))
    is_conversion = (archetype == "stack" and not is_hero and not has_logo_slot
                     and (use_case in _conversion_cases
                          or _has_form_slot(section) or bool(_button_slots(section))))
    # a composition-declared DISCLOSURE stack routes to the FAQ composer (event-
    # scaffolds 2026-07): the `faq` useCase is the declaration (same rule as the
    # hero), and a `knobs.faq` payload declares the same intent for disclosure
    # sections whose useCase is semantic (agenda / schedule / …).
    _knobs = section.get("knobs") if isinstance(section.get("knobs"), dict) else {}
    is_faq = archetype == "stack" and not is_hero and not is_conversion \
        and (use_case == "faq" or _knobs.get("faq") is not None)
    if archetype == "stack" and not is_hero and not is_conversion and not is_faq:
        renderer_archetype = _GENERIC_FLOW
        layout["archetype"] = _GENERIC_FLOW

    if renderer_archetype == _GENERIC_FLOW:
        # expand repeatable list-copy slots (e.g. value_props) into caption+paragraph entries
        # so the generic-flow safety net never silently drops module copy. Contract-aware
        # (fix-batch 2026-07): logo walls / utility link lists / testimonials / labels
        # normalize to REGISTERED shared renderers, never an unresolved-slot marker.
        # A section that binds ANY logo-contract slot is a logo-wall-role section: flag it
        # so the generic-flow composer stamps the resolved device (image strip / text
        # captions / empty) for the gate's logo-wall-integrity check (AS-33).
        if any((s.get("contract") or "").lower().startswith("logo")
               for s in _slots(section)):
            layout["_logoWall"] = True
        mapping = []
        for s in _slots(section):
            c_low = (s.get("contract") or "").lower()
            copyval = s.get("copy")
            if isinstance(copyval, list):
                items = _repeatable_copy(s)
                if c_low.startswith("logo"):
                    # logo wall (AS-33): per-item EVIDENCE routing — an entry whose
                    # asset file exists on disk (src survived _sanitize_assets) renders
                    # as a real logo image in the logo-strip device; an entry without a
                    # disk-backed file falls back to the uppercase text caption. Never
                    # a broken/invented image reference. Iterates the RAW list (AS-34,
                    # blocker-1): bare-string items route through the same mapping (the
                    # sanitizer coerces them with disk evidence first; an unsanitized
                    # string still lands as a caption) instead of being dict-filtered
                    # into an empty wall.
                    for it in (copyval if isinstance(copyval, list) else items):
                        entry = _logo_item_mapping(it)
                        if entry:
                            # source-slot GROUP rides along so the flow composer
                            # renders each authored slot (badges / ratings / logos)
                            # as its OWN strip row, never one merged strip.
                            entry["group"] = str(s.get("name") or "logo-strip")
                            mapping.append(entry)
                elif c_low in ("link", "cta"):
                    for it in items:
                        label = (it.get("label") or it.get("text") or "").strip()
                        if label:
                            mapping.append({"slot": "flow", "role": "utility link",
                                            "contract": "link",
                                            "usage": {"label": label,
                                                      "href": it.get("href", "#"),
                                                      "accent": False}})
                elif c_low in ("stat", "stat-block", "metric"):
                    # stat contract (W4): each metric routes to the REAL stat renderer
                    # (value at the brand's h2 register, label on the body register) —
                    # never the caption fold that rendered "170+" at eyebrow size.
                    # `group` rides the authored slot name so the flow composer bands
                    # consecutive stats into ONE row (same discipline as logo strips).
                    for i, m in enumerate(items):
                        value = str(m.get("value") or m.get("heading")
                                    or m.get("caption") or m.get("title") or "").strip()
                        label = str(m.get("label") or m.get("text")
                                    or m.get("body") or "").strip()
                        if not value:
                            continue
                        mapping.append({"slot": s.get("name") or "stats",
                                        "role": f"stat {i + 1}", "contract": "stat",
                                        "usage": {"value": value, "label": label},
                                        "group": str(s.get("name") or "stats")})
                elif c_low == "table":
                    # table contract (W4): the repeatable rows bind ONE semantic table
                    # (render_table handles {label, value} dict rows).
                    mapping.append({"slot": s.get("name") or "table",
                                    "role": s.get("role") or "table",
                                    "contract": "table",
                                    "usage": {"rows": items}})
                else:
                    for i, m in enumerate(items):
                        cap = m.get("heading") or m.get("caption") or m.get("title") or ""
                        body = m.get("text") or m.get("body") or ""
                        if cap:
                            mapping.append({"slot": "flow", "role": f"module caption {i + 1}",
                                            "contract": "caption", "usage": {"text": cap, "case": "upper"}})
                        if body:
                            mapping.append({"slot": "flow", "role": f"module body {i + 1}",
                                            "contract": "paragraph", "usage": {"text": body}})
            elif c_low in ("testimonial", "quote"):
                quote = _text(copyval, "quote", "text") \
                    or (copyval if isinstance(copyval, str) else "")
                if quote:
                    mapping.append({"slot": "flow", "role": "testimonial quote",
                                    "contract": "paragraph",
                                    "usage": {"text": quote, "measure": "44ch"}})
                if isinstance(copyval, dict):
                    attrib = " — ".join(x for x in (copyval.get("name"), copyval.get("role"))
                                        if isinstance(x, str) and x.strip())
                    if attrib:
                        mapping.append({"slot": "flow", "role": "attribution",
                                        "contract": "caption",
                                        "usage": {"text": attrib, "case": "upper"}})
            elif c_low == "logo":
                # SINGLE logo slot (the live-generation shape: one slot per mark, each
                # carrying its own asset payload). Same AS-33 evidence routing as the
                # list-copy wall above; an asset-less, text-less logo slot maps to
                # nothing rather than inheriting the brand-wordmark device (which is
                # a NAV device — five wordmark repeats on a logo wall was the leak).
                entry = _logo_item_mapping(s)
                if entry:
                    mapping.append(entry)
            elif c_low == "label":
                mapping.append({"slot": "flow", "role": s.get("role") or "label",
                                "contract": "caption",
                                "usage": {"text": _slot_text(s, "text", "label") or ""}})
            elif c_low == "subheading":
                e = _slot_to_mapping(s)
                e["contract"] = "paragraph"
                mapping.append(e)
            else:
                mapping.append(_slot_to_mapping(s))
        layout["blockMapping"] = mapping
        layout["_composerCopy"] = {}
    elif is_hero:  # hero stack (incl. the AS-37 inset art-panel split hero)
        if art_panel is not None:
            layout["_artPanel"] = art_panel
            # panel heroes render via the stack-hero composer + hero scaffold.
            layout["archetype"] = "stack"
        layout["blockMapping"] = _hero_mapping(section, art_panel=art_panel is not None)
        layout["_composerCopy"] = {}
        layout["_sectionCopy"] = _hero_section_copy(section)
    elif is_faq:  # composed FAQ accordion (event-scaffolds 2026-07)
        layout["blockMapping"] = _faq_mapping(section)
        layout["_composerCopy"] = _faq_copy(section)
        layout["_faq"] = _faq_stamp((section.get("knobs") or {}).get("faq"))
    elif is_conversion:  # conversion stack
        layout["blockMapping"] = _cta_mapping(section)
        layout["_composerCopy"] = _cta_copy(section)
        # multi-field SIGNUP FORM payload (event-scaffolds 2026-07): stamped only
        # when the form slot authors a validated `fields:` list — every existing
        # single-line conversion renders byte-identically without it.
        ff = _form_fields_stamp(section)
        if ff is not None:
            layout["_formFields"] = ff
    elif archetype in ("overlay", "banded"):
        # the layered/banded composers consume the RAW slot+treatment payload directly
        # (copy inline on each slot) — no fixed-key copy translator needed.
        layout["_overlay"] = _overlay_payload(section)
        layout["blockMapping"] = _overlay_mapping(section)
        layout["_composerCopy"] = {}
        if isinstance(section.get("bands"), dict):
            layout["_bands"] = section["bands"]
    else:  # collage / split / cards / stack-fullbleed / interlock
        if archetype == "cards":
            layout["blockMapping"] = _cards_mapping(section)
        else:
            # list-copy LOGO slots expand per-item (AS-33 evidence routing — the same
            # discipline as the generic-flow wall; hubspot-v2 2026-07): a split whose
            # media slot binds a RUN of marks (award badges, partner logos) used to
            # fold to one empty `logo` entry (usage folding drops list copy), so the
            # composer saw no media and invented editorial art over the bound marks.
            mapping = []
            for s in _slots(section):
                if (s.get("contract") or "").lower().startswith("logo") \
                        and isinstance(s.get("copy"), list):
                    for it in s["copy"]:
                        entry = _logo_item_mapping(it)
                        if entry:
                            entry["group"] = str(s.get("name") or "logo-strip")
                            mapping.append(entry)
                else:
                    mapping.append(_slot_to_mapping(s))
            layout["blockMapping"] = mapping
        translator = _COPY_TRANSLATORS.get(archetype)
        layout["_composerCopy"] = translator(section) if translator else {}
        # FORM-SPLIT hero (fix6, `hero-form-split` anatomy): a split HERO binding a
        # validated multi-field form slot stamps the same `_formFields` payload the
        # signup scaffold consumes, plus `_formSplit` (the copy column's proof points
        # + the declared form side) — compose_info_band routes the pair to the
        # capture-panel split. Splits without a fields-bearing form slot stamp
        # nothing and render byte-identically.
        if archetype == "split" and use_case == "hero":
            ff = _form_fields_stamp(section)
            if ff is not None:
                layout["_formFields"] = ff
                knobs = section.get("knobs") if isinstance(section.get("knobs"), dict) else {}
                points_slot = next(
                    (s for s in _slots(section)
                     if (s.get("contract") or "").lower() == "list"
                     and isinstance(s.get("copy"), list)), None)
                # items may be bare strings (raw composition) OR {"text": …} dicts
                # (the sanitizer's AS-34 coercion) — accept both.
                points = []
                for p in ((points_slot or {}).get("copy") or []):
                    txt = p if isinstance(p, str) else _text(p, "text", "label")
                    if str(txt or "").strip():
                        points.append(str(txt).strip())
                intro, support = "", []
                if points_slot is None:
                    # `content-block` support (pass2 finding): the hero-form-split
                    # anatomy DECLARES its support slot as content-block, but only
                    # `list` copy was consumed — a header+body support block was
                    # silently dropped, leaving the form with no stated reason
                    # (AS-14). Faithful to the block contract: its body strings are
                    # PARAGRAPHS (`support`; the ruled-points device stays the
                    # `list` contract's), its own heading rides as the copy
                    # column's lead-in line (`intro`).
                    cb = next(
                        (s for s in _slots(section)
                         if (s.get("contract") or "").lower() == "content-block"
                         and isinstance(s.get("copy"), dict)
                         and isinstance(s["copy"].get("body"), list)), None)
                    if cb is not None:
                        for p in cb["copy"]["body"]:
                            txt = p if isinstance(p, str) else _text(p, "text", "label")
                            if str(txt or "").strip():
                                support.append(str(txt).strip())
                        hdr = cb["copy"].get("header")
                        intro = str((_text(hdr, "heading", "text")
                                     if isinstance(hdr, dict) else "") or "").strip()
                layout["_formSplit"] = {
                    "points": points,
                    "side": str(knobs.get("formSide") or "").lower(),
                }
                if intro:
                    layout["_formSplit"]["intro"] = intro
                if support:
                    layout["_formSplit"]["support"] = support
        # event scaffolds (2026-07): validated cards-family knobs stamp the BENTO
        # mosaic / PRICING-TIER presentations (compose_cards dispatch). Malformed
        # knobs stamp nothing — the module grid renders unchanged.
        if archetype == "cards":
            knobs = section.get("knobs") if isinstance(section.get("knobs"), dict) else {}
            if knobs.get("bento") is not None:
                stamp = _bento_stamp(knobs["bento"])
                if stamp is not None:
                    layout["_bento"] = stamp
            if layout.get("_bento") is None and knobs.get("tiers") is not None:
                stamp = _tiers_stamp(knobs["tiers"])
                if stamp is not None:
                    layout["_tiers"] = stamp
                    layout["blockMapping"] = _tiers_mapping(section)
                    layout["_composerCopy"] = _tiers_copy(section)
    return layout


def adapt_brand_section(section: dict, doc: dict) -> tuple[dict, dict, dict | None]:
    """Adapt ONE (sanitized) composition section against the ACTIVE BRAND — the single
    shared lane path (fid10 2026-07). ``compose_replica`` and ``render_composition``
    previously post-processed ``composition_to_layout`` differently: the replica lane
    merged the brand's authored ``layoutCopy`` and rode the brand layout's declared
    ``eyebrowRegister`` onto the adapted layout, while the catalog lane did neither —
    so the composed-from-catalog page silently dropped authored headings/subheads
    (translators emit ``""`` for keys a composition never voices) and lost the
    per-section eyebrow color registers.

    Returns ``(layout, merged_copy, sect_copy)``:
      - ``layout``: ``composition_to_layout`` result; when the section id matches a
        brand layout, declarations the composition vocabulary doesn't model
        (``eyebrowRegister``) ride through.
      - ``merged_copy``: the LAYOUT_COPY entry — hero section copy, then translator
        copy, then the brand's AUTHORED layoutCopy for this id on top (the replica
        lane's proven precedence: authored voice heals lossy slot translations and
        translator fallbacks; a section id without an authored entry keeps the
        composition copy exactly as before).
      - ``sect_copy``: the hero SECTION_COPY payload (None on non-hero sections).

    ARCHETYPE SKELETON FIRST (spec/archetype-library.md §3.4): a section carrying
    ``archetypeRef`` is normalized against its genre archetype BEFORE the brand
    adaptation below — archetype family/knob defaults land first, then the brand's
    recipes/tokens/declarations overwrite anatomy wherever the brand has its own
    pattern, so "brand recipes win" is the ORDERING, not a special case. An unknown id
    or an unresolvable physics fact family strips the ref (fail closed — the section
    renders through the brand's own evidenced anatomy) and the demotion note rides
    ``layout['_archetypeNotes']``. Sections without the ref pass through untouched.
    """
    section, art_notes = al.apply_archetype_skeleton(section, doc)
    layout = composition_to_layout(section)
    if art_notes:
        layout["_archetypeNotes"] = art_notes
    composer_copy = layout.pop("_composerCopy", {}) or {}
    sect_copy = layout.pop("_sectionCopy", None)
    # STRUCTURE-VARIABLE mode (archetypeRef survived skeleton application): the
    # brand-layout id ride-throughs below (surface role, eyebrowRegister, authored
    # layoutCopy) exist to heal LOSSY REPLICA TRANSLATIONS of the brand's own
    # sections. An archetype-instantiated section is deliberately NOT the brand's
    # layout even when it shares an id (a generated hero is not the source hero) —
    # riding the source surface/copy onto it repaints the new skeleton with the old
    # section's identity (measured: the source's photo-hero surface under a bento
    # grid). Brand recipes/tokens still win — they bind during composition, not via
    # this id coincidence.
    creative = bool(layout.get("archetypeRef"))
    brand_layout = None if creative else next(
        (l for l in (doc.get("layouts") or [])
         if isinstance(l, dict) and l.get("id") == layout.get("id")), None)
    if brand_layout and brand_layout.get("eyebrowRegister"):
        layout.setdefault("eyebrowRegister", brand_layout["eyebrowRegister"])
    # the brand layout's DECLARED surface role rides through (same class of
    # declaration as eyebrowRegister: the composition enum is coarse — any/primary/
    # inverse/… — while the brand layout may name its real measured surface, e.g. an
    # accent-wash art band or a photo-hero role; hubspot-v2 2026-07). Only a role the
    # brand's tokens.surfaces actually carries wins (resolve_surface_intent contract).
    b_surf = str((brand_layout or {}).get("surfaceIntent") or "")
    if b_surf and b_surf in ((doc.get("tokens") or {}).get("surfaces") or {}):
        layout["surfaceIntent"] = b_surf
    # authored layoutCopy heals lossy REPLICA translations by id; a creative section
    # authors its OWN copy — the source section's voice must not overwrite it via the
    # same id coincidence (see the creative note above).
    authored = {} if creative else dict(cs.brand_layout_copy(doc).get(layout.get("id")) or {})
    merged = {**(sect_copy or {}), **composer_copy, **authored}
    # HEADING-LEVEL DEMOTION below the hero (W5, stress-playbook 2026-07): only the
    # hero rides the display tier — a NON-HERO section's heading/header slot that
    # declares no level demotes to the brand's measured section tier
    # (cs.section_heading_level: h2 for ladder-bearing brands, display for brands
    # without the fact — the historical degrade). An AUTHORED level (slot copy.level,
    # folded into usage upstream) always wins, so a composition can still declare a
    # display statement deliberately. Same rule for the split translator's
    # headingLevel (the info-band intro heading), keeping every lane on one law.
    if sect_copy is None:
        tier = cs.section_heading_level(doc)
        for m in (layout.get("blockMapping") or []):
            if not isinstance(m, dict):
                continue
            if (m.get("contract") or "").lower() not in ("heading", "header"):
                continue
            usage = m.get("usage")
            if isinstance(usage, dict) and not str(usage.get("level") or "").strip():
                usage["level"] = tier
        if not str(merged.get("headingLevel") or "").strip():
            merged["headingLevel"] = tier
    return layout, merged, sect_copy


def composition_to_doc(comp: dict, brand_yaml_path: Path | str) -> tuple[dict, list[str]]:
    """Build the full page ``doc`` for a composition. Reuses the brand's navbar/footer +
    tokens/type/motion from brand.yaml; replaces ``layouts[]`` with the mapped sections and
    returns the section ORDER. The per-section copy overrides (SECTION_COPY for the hero +
    per-id LAYOUT_COPY) are stashed on the doc under ``_hybridCopy`` for the renderer to
    apply via the in-memory compose_section copy-dict override mechanism.

    Returns ``(doc, order)``.
    """
    doc = yaml.safe_load(Path(brand_yaml_path).read_text()) or {}
    # active-brand image inventory (AS-34) + authored section copy; in-memory only.
    cs.attach_brand_copy(doc, Path(brand_yaml_path).parent)
    cs.attach_asset_inventory(doc, Path(brand_yaml_path).parent)
    # derived-scale consumption (pass1 2026-07, style-scale.v1): COMPOSED lanes may
    # prefer a derived step for NEW geometry where no measured fact binds (e.g. the
    # bandHeight knob with no measured rung in its direction). Loaded here — the
    # generative doc builder — and ONLY here: the replica assembler never reads the
    # artifact, so replica output is byte-identical whether or not it exists.
    doc["_styleScale"] = style_scale.load_style_scale(Path(brand_yaml_path).parent)
    sections = [s for s in (comp.get("sections") or []) if isinstance(s, dict)]
    if not sections:
        raise ValueError("composition has no sections")

    layouts: list[dict] = []
    order: list[str] = []
    layout_copy: dict = {}
    section_copy: dict | None = None
    accent_layout_id: str | None = None

    for sec in sections:
        # shared lane path (fid10 2026-07): the SAME brand-aware adaptation the
        # replica assembler uses — authored layoutCopy heals lossy translator copy,
        # brand-layout declarations (eyebrowRegister) ride through. PER-SECTION hero
        # copy (ANCHORED-REPORT composer-gap #1 fix): every hero binds its own
        # eyebrow/subhead/cta via LAYOUT_COPY[id] (compose_stack_hero reads
        # copy_for(layout)); the FIRST hero additionally seeds the page-global
        # SECTION_COPY base (nav wordmark/links + defaults for copyless sections).
        layout, merged, sect_copy = adapt_brand_section(sec, doc)
        layouts.append(layout)
        order.append(layout["id"])
        if merged:
            layout_copy[layout["id"]] = merged
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
    # A composition renders a whole standalone PAGE (archetype-gallery 2026-07): the
    # brand chrome (nav + banner) belongs on it whatever composer family opens it.
    # The replica/catalog lanes never set this hint, so their split/collage-opened
    # pages keep the historical nav-free shape byte-identically.
    doc["_composedPage"] = True
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
        # drift-detection + provenance-index sidecar (SPEC §B.1/§F): the index the
        # token-provenance gate reads. Same generator call the embedded block used.
        import tokens_css
        tokens_css.write_manifest(
            outdir, tokens_css.build_page_tokens(doc, style_ctx,
                                                 brand_yaml_path=brand_yaml_path))
        copied = cs.copy_assets(brand_dir, outdir / "assets")
        copied += _copy_declared_assets(render_comp, brand_dir, outdir / "assets")
        copied += cs.copy_fonts(brand_dir, outdir / "assets", doc)
    finally:
        cs.SECTION_COPY, cs.LAYOUT_COPY, cp.ACCENT_LAYOUT = (
            saved_section, saved_layout, saved_accent)

    # persist the composition JSON next to the render for provenance/round-trip.
    (outdir / "composition.json").write_text(json.dumps(comp, indent=2) + "\n")

    # unresolved-slot count (parity with compose_page.main() and the gate's
    # slot-resolution invariant, W11 stress-playbook 2026-07): count the markers in
    # the EMITTED page. The old side-render re-ran render_slots per layout, which
    # counted fragments the bespoke composers never place (e.g. a split's
    # feature-item rows drawn by the accordion device) — phantom "unresolved: 2"
    # while the shipped HTML carried zero markers.
    unresolved = html.count("<!-- unresolved slot")
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
            elif isinstance(c, dict):
                # dict copy carrying repeatable sub-lists (fix6, mirrors the
                # _sanitize_assets walk): nested item assets are declared files too.
                for v in c.values():
                    if isinstance(v, list):
                        for item in v:
                            if isinstance(item, dict):
                                _take(item)
    return names


def _copy_declared_assets(comp: dict, brand_dir: Path, out_assets: Path) -> list[str]:
    """Copy composition-declared brand assets that ``copy_assets`` (the brand's
    curated assets/ trees) does not cover — e.g. a composition referencing a real
    file that lives only under a render/*/assets snapshot of the SAME brand. Without
    this the gate's asset-presence rows read the file as missing (found +
    wrapper-patched by the showcase harness; upstreamed here). The search never
    leaves ``brand_dir`` — a declared name resolves from the ACTIVE brand's own
    tree or not at all."""
    copied = []
    for name in sorted(_declared_asset_names(comp)):
        dest = out_assets / name
        if dest.exists():
            continue
        hits = sorted(brand_dir.glob(f"**/assets/{name}"))
        src = hits[0] if hits else None
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
