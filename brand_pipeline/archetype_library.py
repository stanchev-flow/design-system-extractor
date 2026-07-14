#!/usr/bin/env python3
"""Genre archetype library — loader/selector for ``contracts/archetypes/*.yaml``.

The library is DATA (spec/archetype-library.md): genre structural vocabulary lives in
YAML, one file per genre (``heroes-saas`` today). This module is the ONLY code that
knows the ``hero-archetypes.v1`` schema, and it knows it GENERICALLY — no archetype id
is ever enumerated or branched on in code.

The law it serves (style-invariant / structure-variable / physics-hard):
  - selection: ``shortlist()`` filters a genre library by page type + task intents and
    emits 2-3 candidates for the composition prompt (``render_candidate_block``).
  - instantiation: ``apply_archetype_skeleton()`` normalizes a composition section
    against its chosen archetype BEFORE brand adaptation, so brand recipes/tokens win
    by construction (compose_from_composition.adapt_brand_section ordering).
  - physics: ``physics_checklist()`` + ``unresolved_bindings()`` expose the fact
    families that must bind; a family that cannot resolve against the active brand
    DEMOTES the section back to the brand's own evidenced hero recipe (fail closed).

Everything is fact-gated: a composition without ``archetypeRef`` passes through every
function unchanged, byte-identically.
"""
from __future__ import annotations

import copy
import re
from functools import lru_cache
from pathlib import Path

import yaml

_HERE = Path(__file__).resolve().parent
GENRE_DIR = _HERE / "contracts" / "archetypes"
SCHEMA_VERSION = "hero-archetypes.v1"

# bandHeight knob vocabulary (spec/archetype-library.md §6 / brand-schema §4.6.6):
# multipliers over the brand's own measured section-padding token — the knob scales
# the brand's rhythm, it never introduces a foreign length. ``viewport`` degrades to
# ``tall`` (composed pages never use viewport units — containment law).
BAND_HEIGHT_FACTORS = {"compact": 0.5, "standard": None, "tall": 1.35}
_BAND_HEIGHT_DEGRADE = {"viewport": "tall"}


# ── loading ─────────────────────────────────────────────────────────────────────────

@lru_cache(maxsize=8)
def load_genre(genre: str) -> dict:
    """Parse + shape-check one genre library. Raises FileNotFoundError/ValueError so a
    caller can fact-gate (``genre_available``) instead of crashing a lane."""
    path = GENRE_DIR / f"{genre}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"no genre library: {path}")
    doc = yaml.safe_load(path.read_text()) or {}
    if doc.get("schemaVersion") != SCHEMA_VERSION:
        raise ValueError(f"{path.name}: schemaVersion {doc.get('schemaVersion')!r} "
                         f"!= {SCHEMA_VERSION!r}")
    arts = doc.get("archetypes") or []
    ids = [a.get("id") for a in arts if isinstance(a, dict)]
    if len(ids) != len(set(ids)):
        raise ValueError(f"{path.name}: duplicate archetype ids")
    return doc


def genre_available(genre: str) -> bool:
    try:
        load_genre(genre)
        return True
    except (FileNotFoundError, ValueError):
        return False


def iter_genres() -> list[str]:
    if not GENRE_DIR.is_dir():
        return []
    return sorted(p.stem for p in GENRE_DIR.glob("*.yaml"))


def find_archetype(archetype_ref: str, genre: str | None = None) -> dict | None:
    """Resolve an archetype id across genre libraries (a specific genre first when
    given). Returns the archetype dict or None — never raises for an unknown id."""
    genres = [genre] if genre else iter_genres()
    for g in genres:
        try:
            doc = load_genre(g)
        except (FileNotFoundError, ValueError):
            continue
        for a in doc.get("archetypes") or []:
            if isinstance(a, dict) and a.get("id") == archetype_ref:
                return a
    return None


# ── brand resume (what the brand's OWN hero evidences) ───────────────────────────────

def brand_hero_structure(doc: dict) -> str:
    """The composition archetype family of the brand's evidenced hero layout
    (``layouts[]`` entry named/used as the hero), '' when the brand has none."""
    for layout in (doc.get("layouts") or []):
        if not isinstance(layout, dict):
            continue
        lid = str(layout.get("id") or "").lower()
        if lid == "hero" or "hero" in lid or "page-header" in lid:
            return str(layout.get("archetype") or "").lower()
    return ""


# ── selection ────────────────────────────────────────────────────────────────────────

def shortlist(genre_doc: dict, page_type: str, task_intents: list[str] | None = None,
              *, variance: str = "mid", brand_hero: str = "",
              off_grid: bool = True, k: int = 3,
              exclude: tuple[str, ...] = ()) -> list[dict]:
    """Rank the genre library for a brief: page-type affinity first, task-intent
    overlap second, variance dial third. Deterministic (stable sort over library
    order). ``off_grid=False`` excludes archetypes flagged ``requiresOffGrid`` (their
    anatomy needs off-grid geometry devices the style has locked)."""
    page_type = (page_type or "").strip().lower()
    intents = {str(t).strip().lower() for t in (task_intents or []) if str(t).strip()}
    out: list[tuple[float, int, dict]] = []
    for idx, a in enumerate(genre_doc.get("archetypes") or []):
        if not isinstance(a, dict) or a.get("id") in exclude:
            continue
        if not off_grid and a.get("requiresOffGrid"):
            continue
        uc = a.get("useCases") or {}
        pts = [str(p).lower() for p in (uc.get("pageTypes") or [])]
        if page_type and page_type not in pts:
            continue
        score = 0.0
        if page_type:
            # first-listed page type = the archetype's home turf
            score += 3.0 if pts and pts[0] == page_type else 2.0
        tis = {str(t).lower() for t in (uc.get("taskIntents") or [])}
        score += 1.5 * len(intents & tis)
        arch = str((a.get("structure") or {}).get("archetype") or "").lower()
        if brand_hero:
            if variance == "low" and arch == brand_hero:
                score += 1.0
            elif variance == "high" and arch != brand_hero:
                score += 1.0
        out.append((-score, idx, a))
    out.sort(key=lambda t: (t[0], t[1]))
    return [a for _, _, a in out[:k]]


def _slot_line(slot: dict) -> str:
    bits = [str(slot.get("slot") or "?")]
    meta = []
    if slot.get("required"):
        meta.append("required")
    for key in ("contract", "textLen", "sizeClass", "mediaAspect", "z"):
        if slot.get(key):
            meta.append(f"{key}:{slot[key]}")
    return bits[0] + (f"({', '.join(meta)})" if meta else "")


def render_candidate_block(candidates: list[dict]) -> str:
    """Prompt block for the composition generator — mirrors the voice of
    ``layout_library.render_pattern_constraint``. Empty list -> ''."""
    if not candidates:
        return ""
    out = ["## HERO STRUCTURE CANDIDATES (genre archetype library — pick EXACTLY ONE)",
           "",
           "The hero's structural skeleton may come from one of these genre archetypes "
           "(style-invariant / structure-variable / physics-hard). Choose ONE by the "
           "brief's task, record it on the hero section as `archetypeRef: \"<id>\"`, and "
           "instantiate it ENTIRELY through this brand's facts: tokens, surfaces, type "
           "tiers, spacing steps, actionGroup grammar, recipes. Where the brand has its "
           "own recipe for a slot role, the recipe's anatomy WINS (the archetype only "
           "places it). Physics is not relaxable: containment, measure caps, one primary "
           "per action group (AS-59), text-on-media contrast, heading-tier integrity. "
           "Alignment: prefer OMITTING `section.alignment` (the brand's header grammar "
           "resolves it); if you do declare an asymmetric anchor (left/right) you MUST "
           "name a real slot as `counterweight`. Keep ink/surface pairings to the "
           "brand's own surface roles — never repaint a slot's text color.", ""]
    for a in candidates:
        anatomy = a.get("anatomy") or {}
        slots = [s for s in (anatomy.get("slots") or []) if isinstance(s, dict)]
        geo = a.get("geometry") or {}
        knobs = ", ".join((a.get("variantKnobs") or {}).keys()) or "none"
        traps = "; ".join(str(t) for t in (a.get("slopTraps") or [])[:3])
        out.append(f"- **`{a.get('id')}`** — {str(a.get('intent') or '').strip()}")
        out.append(f"    - structure: archetype `{(a.get('structure') or {}).get('archetype')}`"
                   f", bandHeight `{geo.get('bandHeight')}`"
                   f", alignment context `{(anatomy.get('alignment') or {}).get('context')}`")
        out.append(f"    - slots (order matters): {'; '.join(_slot_line(s) for s in slots)}")
        out.append(f"    - tunable knobs: {knobs}")
        if traps:
            out.append(f"    - slop traps to avoid: {traps}")
    out.append("")
    out.append("Emit the chosen id as `archetypeRef` on the hero section. If NONE fits the "
               "brief, omit `archetypeRef` and compose the hero from the brand's own "
               "evidenced pattern instead.")
    out.append("")
    return "\n".join(out)


# ── physics bindings ────────────────────────────────────────────────────────────────

def physics_checklist(archetype: dict) -> list[str]:
    return [str(f) for f in (archetype.get("physicsBindings") or [])]


# Fact probes per binding family — GENERIC checks against the brand doc's standard
# fact families (brand-schema.md). A probe answers "can this family bind for this
# brand at all?"; the per-render verification lives in the gates. Families whose
# physics is drawn structurally by the composer (measure caps, grid equalization,
# control geometry) always bind — listed here as always-True so the checklist stays
# exhaustive and auditable.
_FAMILY_PROBES = {
    "containment": lambda d: bool(_spacing_keys(d, "container")) or bool(d.get("layouts")),
    "headingTier": lambda d: any("display" in k for k in _type_roles(d)),
    "headerContext": lambda d: bool((d.get("layoutGrammar") or {}).get("headerContext")),
    "relationalRhythm": lambda d: bool(((d.get("tokens") or {}).get("spacing") or {})),
    "actionGroup": lambda d: bool((d.get("layoutGrammar") or {}).get("actionGroup")),
    "surfaceContrast": lambda d: bool(((d.get("tokens") or {}).get("surfaces") or {})),
    "textOnMedia": lambda d: bool(d.get("heroTreatment")),
    "stackMeasure": lambda d: True,     # structural: composer draws measure caps
    "gridEqualize": lambda d: True,     # structural: grid scaffolds equalize (AS-44)
    "controlMeasure": lambda d: bool(d.get("buttons") or (d.get("tokens") or {}).get("type")),
    "assetFidelity": lambda d: True,    # render-time: asset sanitizer + gate rows
    "interaction": lambda d: True,      # render-time: interaction_audit gates it
    "motion": lambda d: True,           # render-time: interaction_audit gates it
}


def _spacing_keys(doc: dict, needle: str) -> list[str]:
    sp = ((doc.get("tokens") or {}).get("spacing") or {})
    return [k for k in sp if needle in str(k)]


def _type_roles(doc: dict) -> list[str]:
    return [str(k) for k in (((doc.get("tokens") or {}).get("type") or {}).keys())]


def unresolved_bindings(archetype: dict, doc: dict) -> list[str]:
    """The archetype's physics families that CANNOT bind for this brand (missing fact
    family). Non-empty => the section must demote to the brand's own hero recipe."""
    missing = []
    for fam in physics_checklist(archetype):
        probe = _FAMILY_PROBES.get(fam)
        if probe is None:
            missing.append(f"{fam} (unknown family)")
        elif not probe(doc):
            missing.append(fam)
    return missing


# ── instantiation-side skeleton application ─────────────────────────────────────────

def apply_archetype_skeleton(section: dict, doc: dict,
                             genre: str | None = None) -> tuple[dict, list[str]]:
    """Normalize ONE composition section against its chosen archetype BEFORE brand
    adaptation (compose_from_composition.adapt_brand_section calls this first, so the
    brand's recipes/tokens/ladder then overwrite anatomy where the brand has its own
    pattern — precedence "brand recipes win" falls out of the ordering).

    Returns ``(section, notes)``. A section WITHOUT ``archetypeRef`` is returned
    unchanged (the same object, untouched — byte-identical no-op for every existing
    lane). With a ref, a COPY is normalized:
      - unknown id / unresolvable physics binding -> the ref is stripped (fail closed:
        the section renders through the brand's own evidenced anatomy) + a note.
      - the archetype's structure.archetype corrects a mismatched section archetype.
      - variantKnob DEFAULTS fill absent knobs; ``knobs.bandHeight`` seeds from the
        archetype geometry (viewport degrades to tall — no viewport units).
    """
    ref = str(section.get("archetypeRef") or "").strip() if isinstance(section, dict) else ""
    if not ref:
        return section, []

    notes: list[str] = []
    sec = copy.deepcopy(section)
    art = find_archetype(ref, genre)
    if art is None:
        sec.pop("archetypeRef", None)
        notes.append(f"archetypeRef '{ref}' not found in any genre library — "
                     "demoted to the brand's evidenced hero anatomy")
        return sec, notes

    missing = unresolved_bindings(art, doc)
    if missing:
        sec.pop("archetypeRef", None)
        notes.append(f"archetypeRef '{ref}' demoted — physics families unresolved for "
                     f"this brand: {', '.join(missing)}")
        return sec, notes

    want_arch = str((art.get("structure") or {}).get("archetype") or "").lower()
    have_arch = str(sec.get("archetype") or "").lower()
    if want_arch and have_arch != want_arch:
        notes.append(f"archetype normalized {have_arch or '(absent)'} -> {want_arch} "
                     f"(structure of '{ref}')")
        sec["archetype"] = want_arch

    knobs = dict(sec.get("knobs") or {})
    for kname, kspec in (art.get("variantKnobs") or {}).items():
        if kname not in knobs and isinstance(kspec, dict) and kspec.get("default") is not None:
            knobs[kname] = kspec["default"]
    band = str((art.get("geometry") or {}).get("bandHeight") or "").strip().lower()
    if band and "bandHeight" not in knobs:
        knobs["bandHeight"] = _BAND_HEIGHT_DEGRADE.get(band, band)
    if knobs:
        sec["knobs"] = knobs

    # anatomy-declared ALIGNMENT CONTEXT (fix5 2026-07 — the panel-header defect): the
    # archetype states which header-context grammar rung its copy stack lives in
    # (`splitColumn` for a panel/copy column with a counterweight, `standaloneStack`
    # for a free-standing crest). Ride it through so resolve_alignment consults the
    # brand's OWN grammar for that context; without the stamp a renderer archetype
    # outside the arch→context map (overlay, banded, …) silently fell through to the
    # style-role default, which is how a splitColumn panel got a centered heading.
    anatomy_ctx = str(((art.get("anatomy") or {}).get("alignment") or {})
                      .get("context") or "").strip()
    if anatomy_ctx in ("splitColumn", "standaloneStack") and not sec.get("_headerContext"):
        sec["_headerContext"] = anatomy_ctx
        notes.append(f"header context '{anatomy_ctx}' stamped from the archetype "
                     "anatomy (brand header grammar resolves the stack anchor)")

    # anatomy-declared counterweight: an asymmetric anchor without a counterweight is
    # an alignment-resolution failure (AS-18/AS-49) the archetype already knows how to
    # balance — fill it from the anatomy when the section carries that slot.
    anatomy_cw = str(((art.get("anatomy") or {}).get("alignment") or {})
                     .get("counterweight") or "").strip()
    align = sec.get("alignment")
    if isinstance(align, dict) and str(align.get("anchor") or "").lower() in ("left", "right") \
            and not align.get("counterweight"):
        slots = [s for s in (sec.get("slots") or []) if isinstance(s, dict)]
        slot_names = {str(s.get("name") or "") for s in slots}
        cw = anatomy_cw if anatomy_cw in slot_names else next(
            (str(s.get("name")) for s in slots
             if str(s.get("contract") or "").lower() in ("image", "video", "form")),
            "")
        if cw:
            align["counterweight"] = cw
            notes.append(f"alignment counterweight '{cw}' filled from the archetype "
                         "anatomy (asymmetric anchors must balance — AS-18/AS-49)")
        else:
            # no mass exists to balance the empty half — drop the declaration and let
            # the brand's header grammar resolve the anchor (physics-hard).
            sec.pop("alignment", None)
            notes.append("asymmetric alignment without a possible counterweight "
                         "dropped — brand header grammar resolves the anchor")

    return sec, notes


def normalize_band_height(value) -> str:
    """Validate/degrade a bandHeight knob value to the implemented vocabulary
    ('' = unknown/standard: no CSS emitted)."""
    v = str(value or "").strip().lower()
    v = _BAND_HEIGHT_DEGRADE.get(v, v)
    return v if v in BAND_HEIGHT_FACTORS and BAND_HEIGHT_FACTORS[v] else ""


# ── brief frontmatter (pageType / taskIntents) ──────────────────────────────────────

_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def parse_brief_frontmatter(text: str) -> tuple[dict, str]:
    """Optional YAML frontmatter at the top of a brief md: ``pageType`` (str) +
    ``taskIntents`` (list) + ``genre`` (str). Returns ``(meta, body)``; briefs without
    frontmatter return ``({}, text)`` unchanged."""
    m = _FRONTMATTER_RE.match(text or "")
    if not m:
        return {}, text
    try:
        meta = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return {}, text
    if not isinstance(meta, dict):
        return {}, text
    return meta, text[m.end():]
