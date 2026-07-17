#!/usr/bin/env python3
"""style_resolver.py — PASS 3 stage 1: the style-library resolution engine.

Implements the 4-level cascade of ``contracts/style-library/resolution-model.md``
(sectionDefault → styleDirective → style×section override → brandOverride) WITH
the normative adaptations of ``contracts/style-library/INTEGRATION-PLAN.md`` §4:

  §4.1  TWO-CLASS INVARIANTS — a section invariant is either PHYSICS-class
        (delegates to an EXISTING gate id: AS-59, AS-01/AS-22, AS-32/AS-51,
        AS-40, AS-50/container-law — names, never reimplementations; stays hard
        in every lane) or GENRE-class (a genre-mean prior demoted to a SOFT
        default: advisory, brand evidence may override with provenance).
  §4.2  MERGED PRECEDENCE — the package's internal order (4 > 3 > 2 > 1) is
        preserved verbatim, but the WHOLE package stack sits BELOW the brand
        evidence stack: after the package cascade, brand measured/derived facts
        (style-scale.yaml, tokens.type families, radius modes, motion band,
        voice-facts casing) REPLACE directive values key-by-key, each
        replacement recorded as a ``dissents`` row. Genre-mean directive values
        never correct an extracted brand.
  §4.3  ALGORITHM REPAIRS — an explicit ``layout:`` at override/brand level
        WINS if it is in the section's ``layouts`` and REJECTS LOUDLY
        (StyleResolutionError) if not (never a silent degrade — the authored
        algorithm's step-5 recompute made override layout picks dead code);
        dangling layoutBias ids (``grid-aligned``, ``asymmetric``) resolve
        through a declared data-side translation map so the style's intent
        survives as discipline notes instead of silently no-op'ing; unknown
        ``$`` tags in list merges are ERRORS, not keys.
  §5    ZERO-SIGNAL AXES — ``motion: subtle`` (51/51 styles) and
        ``scaleRatio: 1.25`` (49/51) are filler, emitted UNSET; a genuinely
        differing ratio (newspaper 1.2, editorial-magazine 1.333) survives.
  §P    PRESET LAYER (2026-07-16) — ``styles/pilot-presets.yaml`` +
        ``styles/generated-presets.yaml`` load as ONE merged preset map keyed
        by style id (pilot wins on collision) and fold into every resolution
        as LEVEL-2 DEFAULTS: a preset slot fills only when the brand carries
        NO measured fact for it; every brand binding suppresses its preset
        slot(s), each suppression logged as a ``presetDissents`` row (brand
        wins, provenance named — same posture as the directive dissents).
        Presets carry REAL per-style values, so the §5 filler rule applies to
        DIRECTIVE values only — a preset scaleRatio of 1.25 is a deliberate
        authored default and survives (unless a measured brand ratio beats
        it). Preset values stay OUT of ``constraints`` (directive golden
        behavior unchanged) and are UNCALIBRATED authored priors: prompt
        guidance only, never a gate. A style with NO preset (dark-mode, the
        1/51 uncovered id) resolves and renders byte-identically to
        pre-preset behavior. Exemplars are STRIPPED at load — calibration-only
        per the preset files' policy; they must never reach a prompt.

Pure data-in/data-out: ``load_library()`` / ``load_brand_bundle()`` do the I/O,
``resolve()`` is deterministic over plain dicts, unit-testable with fixtures.
Nothing here renders, and nothing here outranks the gate battery — resolutions
SHAPE the generation prompt only (stage 2 wiring in generate_composition.py).
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from pathlib import Path

import yaml

_HERE = Path(__file__).resolve().parent
LIBRARY_DIR = _HERE / "contracts" / "style-library"

# ── §4.3: dangling layoutBias translation map (data-side, declared) ────────────────
# These two ids appear in 15/51 directives but are NOT layout primitives and are in
# no section's `layouts` — they are alignment/composition DISCIPLINES, not layouts.
# The map preserves their intent as prompt-guidance notes (INTEGRATION-PLAN §3.2/§4.3).
DANGLING_BIAS_TRANSLATION = {
    "grid-aligned": ("layout-grid + left-flush header discipline "
                     "(strict shared column lines, no centered header stack)"),
    "asymmetric": ("collage/interlock composition (offset masses, deliberate "
                   "imbalance — requiresOffGrid territory)"),
}

# ── §5: zero-signal axes (emitted UNSET unless genuinely differing) ─────────────────
ZERO_SIGNAL_MOTION = "subtle"          # 51/51 styles — filler, never a token (AS-47)
ZERO_SIGNAL_SCALE_RATIO = 1.25         # 49/51 styles — only 1.2 / 1.333 carry signal

# ── §4.1: the two-class invariant split ─────────────────────────────────────────────
# PHYSICS-class invariants delegate to the EXISTING gate law by id (the archetype
# physicsBindings pattern: names, not reimplementations). Everything not matched
# here is GENRE-class: a reasonable prior demoted to a soft default (advisory);
# brand evidence may override it with provenance (report OVERRIDE, never FAIL).
_PHYSICS_INVARIANTS = (
    # substring (lowercased) → delegated gate id(s)
    ("exactly one primary cta", "AS-59"),
    ("headline is the focal point", "AS-32/AS-51"),
    ("high contrast with neighbors", "AS-01"),
    ("one item open at a time", "AS-40"),
    ("equal optical weight", "AS-50/container-law"),
    ("equal tile treatment", "AS-50/container-law"),
)


def classify_invariant(text: str) -> tuple[str, str | None]:
    """→ ("physics", gate_id) for the delegated hard laws, ("genre", None) for
    everything else (soft default; INTEGRATION-PLAN §4.1)."""
    low = str(text or "").strip().lower()
    for needle, gate in _PHYSICS_INVARIANTS:
        if needle in low:
            return "physics", gate
    return "genre", None


# ── errors ──────────────────────────────────────────────────────────────────────────

class StyleResolutionError(ValueError):
    """A resolution that must FAIL CLOSED: unknown section/style, an unknown
    ``$`` merge tag, or an explicit layout pick outside the section's layout
    vocabulary (§4.3 — loud rejection, never silent degrade)."""


# ── merge semantics (resolution-model.md, with the unknown-tag repair) ──────────────

_LIST_TAGS = ("$replace", "$append", "$remove")


def _merge_list(base: list, patch: dict) -> list:
    """Apply ONE tagged list op. Unknown $-tags raise (§4.3: errors, not keys)."""
    unknown = [k for k in patch if k.startswith("$") and k not in _LIST_TAGS]
    if unknown:
        raise StyleResolutionError(f"unknown list-merge tag(s) {unknown} "
                                   f"(allowed: {list(_LIST_TAGS)})")
    out = list(base or [])
    if "$replace" in patch:
        out = list(patch["$replace"] or [])
    if "$append" in patch:
        out = out + [v for v in (patch["$append"] or [])]
    if "$remove" in patch:
        gone = set(map(_hashable, patch["$remove"] or []))
        out = [v for v in out if _hashable(v) not in gone]
    return out


def _hashable(v):
    return yaml.safe_dump(v, sort_keys=True) if isinstance(v, (dict, list)) else v


def merge_specs(base, patch):
    """The package's merge semantics (resolution-model.md):
    scalars replace · dicts deep-merge per key · lists are tagged
    ({$replace/$append/$remove}; a BARE array = $replace). Pure; returns a new
    object, never mutates the inputs."""
    if isinstance(patch, dict) and any(k in patch for k in _LIST_TAGS) \
            or (isinstance(patch, dict) and isinstance(base, list)
                and any(k.startswith("$") for k in patch)):
        return _merge_list(base if isinstance(base, list) else [], patch)
    if isinstance(base, dict) and isinstance(patch, dict):
        out = dict(base)
        for k, v in patch.items():
            if k.startswith("$"):
                raise StyleResolutionError(
                    f"unknown merge tag {k!r} against a mapping (tags are legal "
                    "only as list ops)")
            out[k] = merge_specs(base.get(k), v) if k in base else copy.deepcopy(v)
        return out
    # scalars and bare arrays: higher level replaces
    return copy.deepcopy(patch)


# ── library loading ────────────────────────────────────────────────────────────────

@dataclass
class StyleLibrary:
    sections: dict[str, dict]          # id → section entry (catalog.yaml)
    styles: dict[str, dict]            # id → directive (directives.yaml)
    overrides: dict[str, dict]         # style → section → patch (overrides.yaml)
    primitives: dict[str, dict]        # id → {desc, axis, good} (primitives.yaml)
    global_axes: dict[str, list]       # variations/axes.yaml `global`
    presets: dict[str, dict] = field(default_factory=dict)  # §P: id → preset entry
    source_dir: Path = field(default=LIBRARY_DIR)


def _read_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text()) or {}


# §P: preset files, in PRECEDENCE order — pilot loads first and WINS if an id
# ever appears in both (the pilot five are richer/hand-tuned).
_PRESET_FILES = ("pilot-presets.yaml", "generated-presets.yaml")


def _normalize_probe_keys(check):
    """YAML-1.1 coercion repair (same defect class as the catalog's bare
    on/off axis values, §1.1): the preset files write probes as
    ``{ on: display, ... }`` and YAML parses the bare ``on`` KEY as boolean
    True. Normalize back to the authored string key in memory; the files
    stay verbatim."""
    if isinstance(check, dict):
        return {("on" if k is True else k): _normalize_probe_keys(v)
                for k, v in check.items()}
    if isinstance(check, list):
        return [_normalize_probe_keys(v) for v in check]
    return check


def _load_presets(styles_dir: Path, directive_ids: set[str]) -> dict[str, dict]:
    """§P: one merged preset map keyed by style id. Missing files load as
    nothing (the layer degrades to directive-only). Every preset id must
    resolve into directives.yaml (fail closed on drift). Exemplars are
    STRIPPED at load — they are calibration-only per the preset files' own
    policy and must never travel toward a generation prompt."""
    merged: dict[str, dict] = {}
    for name in _PRESET_FILES:
        path = styles_dir / name
        if not path.exists():
            continue
        doc = _read_yaml(path)
        source = "pilot" if name.startswith("pilot") else "generated"
        for sid, entry in (doc.get("styles") or {}).items():
            sid = str(sid)
            if sid not in directive_ids:
                raise StyleResolutionError(
                    f"preset file {name} carries id {sid!r} which is not a "
                    "directives.yaml style — presets key into existing ids only")
            if sid in merged:              # pilot loaded first → pilot wins
                continue
            entry = entry or {}
            merged[sid] = {
                "preset": copy.deepcopy(entry.get("preset") or {}),
                "signatures": _normalize_probe_keys(
                    copy.deepcopy(entry.get("signatures") or [])),
                "neighbors": list(entry.get("neighbors") or []),
                "distinguishers": copy.deepcopy(entry.get("distinguishers") or {}),
                "source": source,
            }
    return merged


def load_library(lib_dir: Path | str = LIBRARY_DIR) -> StyleLibrary:
    """Load + validate the canonical package. Guards the import defects the plan
    documented: string-typed axis values (YAML-1.1 on/off coercion, §1.1) and the
    declared counts (21 sections / 51 styles / 17 primitives)."""
    lib_dir = Path(lib_dir)
    catalog = _read_yaml(lib_dir / "sections" / "catalog.yaml")
    directives = _read_yaml(lib_dir / "styles" / "directives.yaml")
    overrides = _read_yaml(lib_dir / "overrides" / "overrides.yaml")
    primitives = _read_yaml(lib_dir / "layouts" / "primitives.yaml")
    axes = _read_yaml(lib_dir / "variations" / "axes.yaml")

    sections = {str(s["id"]): s for s in (catalog.get("sections") or [])
                if isinstance(s, dict) and s.get("id")}
    styles = {str(k): v for k, v in (directives.get("styles") or {}).items()}
    prims = {str(k): v for k, v in (primitives.get("primitives") or {}).items()}

    # string-typed axis guard (import defect §1.1: bare on/off parsed as bool)
    for sid, sec in sections.items():
        for axis, values in (sec.get("variationAxes") or {}).items():
            for v in (values or []):
                if isinstance(v, bool):
                    raise StyleResolutionError(
                        f"section {sid!r} axis {axis!r} carries a BOOLEAN {v!r} — "
                        "the catalog's on/off axis values must stay strings "
                        "(YAML-1.1 coercion defect; quote them)")
    return StyleLibrary(
        sections=sections, styles=styles,
        overrides=overrides.get("overrides") or {},
        primitives=prims,
        global_axes=axes.get("global") or {},
        presets=_load_presets(lib_dir / "styles", set(styles)),
        source_dir=lib_dir,
    )


# ── §4.2: the brand bundle (brand-owned facts, loaded once) ─────────────────────────

@dataclass
class BrandBundle:
    """The brand evidence stack the resolver merges ABOVE the package cascade:
    brand.yaml doc + pass-1 artifacts (style-scale.yaml, voice-facts.yaml) +
    layout-library recipes. All optional — an empty bundle leaves the package
    resolution untouched (create-from-style posture)."""
    doc: dict = field(default_factory=dict)              # brand.yaml
    style_scale: dict | None = None                      # style-scale.v1
    voice_facts: dict | None = None                      # voice-facts.v1
    recipes: list[dict] = field(default_factory=list)    # layout-library recipes
    brand_dir: Path | None = None


def load_brand_bundle(brand_dir: Path | str) -> BrandBundle:
    """Load the brand's own facts for the §4.2 merge. Missing artifacts load as
    None/[] (fact-gated everywhere downstream)."""
    brand_dir = Path(brand_dir)
    doc: dict = {}
    by = brand_dir / "brand.yaml"
    if by.exists():
        doc = yaml.safe_load(by.read_text()) or {}

    scale = None
    sp = brand_dir / "style-scale.yaml"
    if sp.exists():
        try:
            art = yaml.safe_load(sp.read_text())
            if isinstance(art, dict) and art.get("schema") == "style-scale.v1":
                scale = art
        except Exception:
            scale = None

    voice = None
    vp = brand_dir / "voice-facts.yaml"
    if vp.exists():
        try:
            vf = yaml.safe_load(vp.read_text())
            if isinstance(vf, dict) and vf.get("schema") == "voice-facts.v1":
                voice = vf
        except Exception:
            voice = None

    recipes: list[dict] = []
    lp = brand_dir / "layout-library.yaml"
    if lp.exists():
        try:
            lib = yaml.safe_load(lp.read_text()) or {}
            recipes = [r for r in (lib.get("recipes") or []) if isinstance(r, dict)]
        except Exception:
            recipes = []
    return BrandBundle(doc=doc, style_scale=scale, voice_facts=voice,
                       recipes=recipes, brand_dir=brand_dir)


# ── directive projection (level 2) ──────────────────────────────────────────────────

# The directive keys that project into the section spec as `constraints`. `layoutBias`
# and `signatures` project separately; family/label are labels, not constraints.
_DIRECTIVE_CONSTRAINT_KEYS = (
    "density", "radius", "border", "shadow", "contrast", "accentUsage", "palette",
    "typeDisplay", "typeBody", "scaleRatio", "case", "tracking", "imagery", "motion",
)


def project_directive(directive: dict) -> dict:
    """Level-2 projection of one style directive: constraints (zero-signal axes
    dropped, §5), effective layoutBias (dangling ids translated to discipline
    notes, §4.3), and the style's signature moves."""
    directive = directive or {}
    constraints: dict = {}
    for key in _DIRECTIVE_CONSTRAINT_KEYS:
        if key not in directive:
            continue
        val = directive[key]
        if key == "motion" and val == ZERO_SIGNAL_MOTION:
            continue                       # filler on 51/51 — never a constraint
        if key == "scaleRatio" and val == ZERO_SIGNAL_SCALE_RATIO:
            continue                       # filler on 49/51 — pass-1 scale owns this
        constraints[key] = copy.deepcopy(val)

    bias: list[str] = []
    disciplines: list[str] = []
    for b in (directive.get("layoutBias") or []):
        b = str(b)
        if b in DANGLING_BIAS_TRANSLATION:
            disciplines.append(f"{b} → {DANGLING_BIAS_TRANSLATION[b]}")
        else:
            bias.append(b)
    return {
        "constraints": constraints,
        "layoutBias": bias,
        "layoutDisciplines": disciplines,
        "signatures": list(directive.get("signatures") or []),
        "label": directive.get("label"),
        "family": directive.get("family"),
    }


# ── §4.2: brand bindings (brand facts REPLACE directive values, with dissent) ───────

def _brand_type_families(doc: dict) -> dict[str, str]:
    """display/body families from tokens.type (measured facts)."""
    out: dict[str, str] = {}
    types = ((doc.get("tokens") or {}).get("type") or {})
    for role in ("display-hero", "h1"):
        fam = ((types.get(role) or {}).get("family"))
        if fam:
            out["display"] = str(fam)
            break
    fam = ((types.get("body") or {}).get("family"))
    if fam:
        out["body"] = str(fam)
    return out


def brand_bindings(bundle: BrandBundle) -> dict:
    """The §3.3 token-mapping rows the brand ACTUALLY carries, keyed by the
    directive constraint they outrank. Only measured/derived facts bind — an
    empty bundle binds nothing (create-from-style: the style speaks)."""
    if bundle is None:
        return {}
    out: dict[str, dict] = {}
    scale = bundle.style_scale or {}

    t = scale.get("type") or {}
    if t.get("followsScale") and t.get("ratio"):
        out["scaleRatio"] = {
            "value": t["ratio"], "basePx": t.get("basePx"),
            "provenance": "style-scale.yaml type (pass-1 derived over measured ladder)"}
    s = scale.get("space") or {}
    if s.get("followsScale") and s.get("stepsPx"):
        out["space"] = {
            "value": {"baseUnitPx": s.get("baseUnitPx"),
                      "stepsPx": list(s["stepsPx"]),
                      "sectionRhythmPx": list(s.get("sectionRhythmPx") or [])},
            "provenance": "style-scale.yaml space (pass-1 derived over measured ladder)"}
    r = scale.get("radius") or {}
    if r.get("modes"):
        out["radius"] = {
            "value": {"modes": copy.deepcopy(r["modes"]), "policy": r.get("policy")},
            "provenance": "style-scale.yaml radius (measured tokens.radius modes)"}
    m = scale.get("motion") or {}
    if m.get("bandMs"):
        out["motion"] = {
            "value": {"bandMs": dict(m["bandMs"]), "easing": m.get("easing")},
            "provenance": "style-scale.yaml motion (measured census band)"}

    fams = _brand_type_families(bundle.doc or {})
    if fams.get("display"):
        out["typeDisplay"] = {"value": fams["display"],
                              "provenance": "brand.yaml tokens.type (measured family)"}
    if fams.get("body"):
        out["typeBody"] = {"value": fams["body"],
                           "provenance": "brand.yaml tokens.type (measured family)"}

    casing = ((bundle.voice_facts or {}).get("casing") or {})
    rule = ((casing.get("headings") or {}).get("rule"))
    if rule:
        # directive `case` (upper/mixed) is a genre prior; the brand's measured
        # heading casing rule outranks it in extraction lanes.
        out["case"] = {"value": str(rule),
                       "provenance": "voice-facts.yaml casing.headings (measured corpus)"}

    sigs = [s for s in ((bundle.doc or {}).get("signatures") or []) if isinstance(s, dict)]
    if sigs:
        out["signatures"] = {
            "value": [{"id": s.get("id"), "kind": s.get("kind"),
                       "mode": s.get("mode"), "claim": s.get("claim")} for s in sigs],
            "provenance": "brand.yaml signatures (pass-1, evidence-cited)"}
    return out


# ── §P: preset precedence (presets are LEVEL-2 DEFAULTS under brand facts) ──────────

def _apply_preset_precedence(entry: dict, bindings: dict,
                             brand: BrandBundle | None) -> tuple[dict, list[dict]]:
    """Fold ONE style's preset under the brand evidence stack: a preset slot
    survives only where the brand carries NO measured fact; every measured
    fact SUPPRESSES its preset slot(s) and logs a dissent row (brand wins,
    provenance named — the §4.2 posture applied to the preset layer).

    Slot map (brand binding → preset slot beaten):
      typeDisplay → font.display · typeBody → font.body ·
      scaleRatio → type.scaleRatio (+ type.baseSizePx when the binding carries
      basePx) · space → space · radius → shape.radiusPx · motion → motion ·
      measured brand palette (brand.yaml tokens.colors/surfaces) → color.

    Signatures/imagery/layout/border/shadow stay preset — no brand binding
    carries a measured fact for them today, and the rendered block states
    that any measured brand fact beats them regardless."""
    preset = copy.deepcopy(entry.get("preset") or {})
    dissents: list[dict] = []

    def _suppress(slot: str, preset_value, bound: dict):
        dissents.append({"slot": slot, "preset": preset_value,
                         "brand": bound.get("value"),
                         "provenance": bound.get("provenance", ""),
                         "winner": "brand"})

    font = preset.get("font") or {}
    if "typeDisplay" in bindings and font.get("display"):
        _suppress("font.display", font.pop("display"), bindings["typeDisplay"])
    if "typeBody" in bindings and font.get("body"):
        _suppress("font.body", font.pop("body"), bindings["typeBody"])
    if not font and "font" in preset:
        del preset["font"]

    typ = preset.get("type") or {}
    if "scaleRatio" in bindings:
        if "scaleRatio" in typ:
            _suppress("type.scaleRatio", typ.pop("scaleRatio"), bindings["scaleRatio"])
        if bindings["scaleRatio"].get("basePx") and "baseSizePx" in typ:
            _suppress("type.baseSizePx", typ.pop("baseSizePx"),
                      {"value": bindings["scaleRatio"]["basePx"],
                       "provenance": bindings["scaleRatio"].get("provenance", "")})
    if not typ and "type" in preset:
        del preset["type"]

    if "space" in bindings and preset.get("space"):
        _suppress("space", preset.pop("space"), bindings["space"])

    shape = preset.get("shape") or {}
    if "radius" in bindings and shape.get("radiusPx"):
        _suppress("shape.radiusPx", shape.pop("radiusPx"), bindings["radius"])
    if not shape and "shape" in preset:
        del preset["shape"]

    if "motion" in bindings and preset.get("motion"):
        _suppress("motion", preset.pop("motion"), bindings["motion"])

    doc = (brand.doc if brand else {}) or {}
    tokens = doc.get("tokens") or {}
    if preset.get("color") and (tokens.get("colors") or tokens.get("surfaces")):
        _suppress("color", preset.pop("color"),
                  {"value": "brand-owned palette",
                   "provenance": "brand.yaml tokens.colors/surfaces (measured palette)"})

    return {
        "preset": preset,
        "signatures": copy.deepcopy(entry.get("signatures") or []),
        "neighbors": list(entry.get("neighbors") or []),
        "distinguishers": copy.deepcopy(entry.get("distinguishers") or {}),
        "source": entry.get("source"),
    }, dissents


# ── the resolver ────────────────────────────────────────────────────────────────────

def resolve(section_id: str, style_id: str, library: StyleLibrary,
            brand: BrandBundle | None = None) -> dict:
    """Resolve ONE (section, style[, brand]) into a merged section spec.

    Steps (resolution-model.md algorithm + INTEGRATION-PLAN §4 adaptations):
      1. spec = deepclone(sectionDefault)
      2. merge the projected style directive (constraints + bias rerank)
      3. merge overrides[style][section]                       (level 3)
      4. merge brand.overrides[section] from brand.yaml         (level 4)
      5. layout: an EXPLICIT `layout:` from steps 3/4 wins IF allowed, else
         REJECT loudly; otherwise first allowed layoutBias entry, else
         defaultLayout
      6. invariants classify into physics (gate-delegated) / genre (advisory)
      7. brand BINDINGS replace directive constraint values key-by-key
         (dissents recorded) — the §4.2 evidence-over-designed ratchet
      8. §P: the style's PRESET (if one exists) folds in as level-2 defaults
         UNDER the same bindings — measured facts suppress their preset slots
         (presetDissents recorded); a style with no preset emits NO preset
         keys at all (byte-identical to pre-preset resolutions)

    Raises StyleResolutionError on unknown ids, unknown $-tags, or an
    out-of-vocabulary explicit layout pick. Never mutates library/brand data.
    """
    if section_id not in library.sections:
        raise StyleResolutionError(f"unknown section {section_id!r}")
    if style_id not in library.styles:
        raise StyleResolutionError(f"unknown style {style_id!r}")

    section = copy.deepcopy(library.sections[section_id])
    proj = project_directive(library.styles[style_id])
    notes: list[str] = [f"dangling layoutBias translated: {d}"
                        for d in proj["layoutDisciplines"]]

    # 2. directive merge: constraints ride in whole; bias reranks (kept separate
    #    from the section body so `layouts` stays the section's vocabulary).
    spec: dict = {
        "slots": section.get("slots") or {},
        "variationAxes": section.get("variationAxes") or {},
        "rules": list(section.get("rules") or []),
        "constraints": proj["constraints"],
    }
    layout_bias = list(proj["layoutBias"])
    explicit_layout: str | None = None
    explicit_source: str | None = None

    # 3. style×section override (level 3)
    override = ((library.overrides.get(style_id) or {}).get(section_id) or {})
    if override:
        patch = {k: v for k, v in override.items() if k not in ("layout", "layoutBias")}
        spec = merge_specs(spec, patch)
        if "layoutBias" in override:
            layout_bias = list(override["layoutBias"] or [])
        if override.get("layout"):
            explicit_layout, explicit_source = str(override["layout"]), f"override {style_id}×{section_id}"

    # 4. brand override (level 4 — brand.yaml `overrides:` per token-schema shape)
    brand_over = (((brand.doc if brand else {}) or {}).get("overrides") or {}).get(section_id) or {}
    if brand_over:
        patch = {k: v for k, v in brand_over.items() if k not in ("layout", "layoutBias")}
        spec = merge_specs(spec, patch)
        if "layoutBias" in brand_over:
            layout_bias = list(brand_over["layoutBias"] or [])
        if brand_over.get("layout"):
            explicit_layout, explicit_source = str(brand_over["layout"]), "brand override"

    # 5. layout resolution (§4.3 semantics)
    allowed = [str(l) for l in (section.get("layouts") or [])]
    if explicit_layout is not None:
        if explicit_layout not in allowed:
            raise StyleResolutionError(
                f"{explicit_source} picks layout {explicit_layout!r} but section "
                f"{section_id!r} allows only {allowed} — rejecting loudly "
                "(never a silent degrade; extend the section's layouts or "
                "re-author the override)")
        layout = explicit_layout
        notes.append(f"layout {explicit_layout!r} set explicitly by {explicit_source}")
    else:
        layout = next((b for b in layout_bias if b in allowed), None) \
            or str(section.get("defaultLayout") or (allowed[0] if allowed else ""))
        ignored = [b for b in layout_bias if b not in allowed]
        if ignored:
            notes.append(f"layoutBias entries not in section layouts (rerank no-ops): {ignored}")

    # 6. two-class invariants (§4.1)
    invariants = []
    for inv in (section.get("invariants") or []):
        cls, gate = classify_invariant(inv)
        row = {"text": str(inv), "class": cls}
        if gate:
            row["gate"] = gate
        invariants.append(row)

    # 7. brand bindings (§4.2 — the whole package stack yields to brand evidence)
    bindings = brand_bindings(brand) if brand else {}
    dissents: list[dict] = []
    constraints = dict(spec.get("constraints") or {})
    for key in ("scaleRatio", "typeDisplay", "typeBody", "case", "radius", "motion"):
        if key not in bindings:
            continue
        bound = bindings[key]
        if key in constraints:
            dissents.append({
                "key": key,
                "directive": constraints[key],
                "brand": bound.get("value"),
                "provenance": bound.get("provenance", ""),
                "winner": "brand",
            })
        constraints[key] = copy.deepcopy(bound.get("value"))
    spec["constraints"] = constraints

    out = {
        "section": section_id,
        "style": style_id,
        "styleLabel": proj["label"],
        "layout": layout,
        "layouts": allowed,
        "layoutBias": layout_bias,
        "layoutDisciplines": proj["layoutDisciplines"],
        "slots": spec.get("slots") or {},
        "variationAxes": spec.get("variationAxes") or {},
        "rules": list(spec.get("rules") or []),
        "constraints": spec["constraints"],
        "invariants": invariants,
        "styleSignatures": proj["signatures"],
        "brandBindings": bindings,
        "dissents": dissents,
        "notes": notes,
    }

    # 8. §P: preset layer (level-2 defaults; keys absent when no preset exists,
    #    keeping no-preset styles byte-identical to pre-preset resolutions)
    if style_id in library.presets:
        preset_entry, preset_dissents = _apply_preset_precedence(
            library.presets[style_id], bindings, brand)
        out["stylePreset"] = preset_entry
        out["presetDissents"] = preset_dissents
    return out


def resolve_all(style_id: str, library: StyleLibrary,
                brand: BrandBundle | None = None,
                sections: list[str] | None = None) -> dict[str, dict]:
    """Resolve every requested section (default: all 21) for one style."""
    wanted = sections if sections is not None else list(library.sections.keys())
    return {sid: resolve(sid, style_id, library, brand) for sid in wanted}


# ── stage-2 rendering: the prompt guidance block ────────────────────────────────────

# §3.2 primitive → composition.v1 archetype hints (our 8 drawable archetypes).
_PRIMITIVE_ARCHETYPE_HINT = {
    "center-stack": 'archetype "stack" (centered header stack)',
    "split-left": 'archetype "split" (text left / media right)',
    "split-right": 'archetype "split" (media left / text right)',
    "full-bleed": 'archetype "stack-fullbleed" or a sanctioned overlay',
    "grid-2": 'archetype "cards" (columns: 2)',
    "grid-3": 'archetype "cards" (columns: 3)',
    "grid-4": 'archetype "cards" (columns: 4)',
    "bento": 'archetype "collage" (mixed-size tiles on one grid)',
    "list-rows": 'archetype "stack" of full-width rows (one idea per row)',
    "table": "the table block inside a stack section",
    "accordion": "the accordion block inside a stack section",
    "tabs": "the tabs block inside a stack section",
    "carousel": "the carousel block inside a stack section",
    "marquee": "a marquee strip device",
    "minimal": 'archetype "stack" (single element, maximal whitespace)',
}

STYLE_BLOCK_BEGIN = "[[PASS3-STYLE:BEGIN]]"
STYLE_BLOCK_END = "[[PASS3-STYLE:END]]"


def _fmt_value(v) -> str:
    """Compact, deterministic rendering of a constraint value for the prompt."""
    if isinstance(v, dict):
        if "modes" in v:                                 # radius binding
            modes = " · ".join(
                f"{m.get('px'):g}px({','.join(map(str, m.get('roles') or []))})"
                for m in (v.get("modes") or []))
            pol = f", policy {v['policy']}" if v.get("policy") else ""
            return f"{modes}{pol}"
        if "bandMs" in v:                                # motion binding
            band = v.get("bandMs") or {}
            eas = f", easing {v['easing']}" if v.get("easing") else ""
            return f"{band.get('min')}–{band.get('max')}ms band{eas}"
        if "stepsPx" in v:                               # space binding
            steps = ", ".join(f"{s:g}" for s in (v.get("stepsPx") or []))
            rhythm = ", ".join(f"{s:g}" for s in (v.get("sectionRhythmPx") or []))
            return (f"base {v.get('baseUnitPx')}px; steps(px): {steps}"
                    + (f"; section rhythm(px): {rhythm}" if rhythm else ""))
        return ", ".join(f"{k}={_fmt_value(val)}" for k, val in sorted(v.items()))
    if isinstance(v, list):
        return ", ".join(_fmt_value(x) for x in v)
    return str(v)


def _fmt_font_slot(f: dict) -> str:
    fam = f.get("family") or "?"
    weights = "/".join(str(w) for w in (f.get("weights") or []))
    bits = [f'"{fam}"']
    if weights:
        bits.append(f"w{weights}")
    gf = f.get("googleFont")
    if gf and gf != fam:
        bits.append(f"googleFont {gf}")
    out = " ".join(bits)
    if f.get("stack"):
        out += f" — stack: {f['stack']}"
    return out


def _preset_lines(res: dict) -> list[str]:
    """§P: the compact prompt-safe preset block for ONE resolved style. Empty
    for styles without a preset (byte-identity for the uncovered id). Purely
    additive guidance; every line renders only from slots that survived brand
    suppression. Exemplars never appear here (stripped at load;
    calibration-only)."""
    entry = res.get("stylePreset")
    if not entry:
        return []
    p = entry.get("preset") or {}
    lines = [
        "Style preset — authored defaults (uncalibrated) — any measured brand",
        "fact beats these. Expert-authored level-2 defaults, not measurements;",
        "check thresholds refine over time via the style-calibration workflow.",
    ]

    font = p.get("font") or {}
    font_bits = [f"{slot} {_fmt_font_slot(font[slot])}"
                 for slot in ("display", "body") if font.get(slot)]
    if font_bits:
        lines.append("  - font pairing: " + " · ".join(font_bits))

    typ = p.get("type") or {}
    if typ:
        bits = []
        if typ.get("baseSizePx") is not None:
            bits.append(f"base {typ['baseSizePx']}px")
        if typ.get("scaleRatio") is not None:
            bits.append(f"ratio {typ['scaleRatio']}")
        lh = typ.get("lineHeight") or {}
        if lh:
            bits.append("line-height " + " / ".join(
                f"{k} {lh[k]}" for k in ("display", "body") if k in lh))
        mc = typ.get("measureCh") or {}
        if mc:
            bits.append("measure " + " / ".join(
                f"{k} {mc[k]}ch" for k in ("body", "lead") if k in mc))
        tr = typ.get("tracking") or {}
        if tr:
            bits.append("tracking " + " / ".join(
                f"{k} {tr[k]}" for k in ("display", "body") if k in tr))
        if bits:
            lines.append("  - type: " + " · ".join(bits))

    color = p.get("color") or {}
    if color:
        role_bits = [f"{role} {v.get('oklch')} ({v.get('hex')})"
                     for role, v in color.items() if isinstance(v, dict)]
        lines.append("  - palette roles: " + " · ".join(role_bits))

    space = p.get("space") or {}
    if space:
        bits = []
        if space.get("basePx") is not None:
            bits.append(f"base {space['basePx']}px")
        if space.get("stepsPx"):
            bits.append("steps(px) " + ", ".join(str(s) for s in space["stepsPx"]))
        if space.get("sectionRhythmPx") is not None:
            bits.append(f"section rhythm {space['sectionRhythmPx']}px")
        lines.append("  - space: " + " · ".join(bits))

    shape = p.get("shape") or {}
    if shape:
        bits = []
        rad = shape.get("radiusPx") or {}
        if rad:
            bits.append("radius(px) " + " / ".join(
                f"{k} {rad[k]}" for k in ("button", "card", "input") if k in rad))
        if shape.get("borderWidthPx") is not None:
            bits.append(f"border {shape['borderWidthPx']}px")
        if shape.get("shadow") is not None:
            bits.append(f"shadow {shape['shadow']}")
        lines.append("  - shape: " + " · ".join(bits))

    layout = p.get("layout") or {}
    if layout:
        bits = []
        if layout.get("maxWidthPx") is not None:
            bits.append(f"max-width {layout['maxWidthPx']}")
        if layout.get("gutterPx") is not None:
            bits.append(f"gutter {layout['gutterPx']}px")
        if layout.get("columns") is not None:
            bits.append(f"columns {layout['columns']}")
        lines.append("  - layout: " + " · ".join(bits))

    motion = p.get("motion") or {}
    if motion:
        bits = []
        if motion.get("easing"):
            bits.append(f"easing {motion['easing']}")
        if motion.get("durationsMs"):
            bits.append("durations(ms) " + ", ".join(str(d) for d in motion["durationsMs"]))
        lines.append("  - motion: " + " · ".join(bits))

    imagery = p.get("imagery") or {}
    if imagery:
        bits = [f"{k} — {imagery[k]}"
                for k in ("subjects", "lighting", "backdrop", "treatment")
                if imagery.get(k)]
        if imagery.get("aspectHabits"):
            bits.append("aspects " + ", ".join(str(a) for a in imagery["aspectHabits"]))
        lines.append("  - imagery art direction: " + " · ".join(bits))

    sigs = entry.get("signatures") or []
    if sigs:
        lines.append("Style preset signatures (always/never guidance; "
                     "check thresholds UNCALIBRATED):")
        for g in sigs:
            check = g.get("check") or {}
            lines.append(
                f"  - [{g.get('mode')}] {g.get('id')} ({g.get('kind')}): "
                f"{g.get('claim')} [check: {_fmt_value(check)}]")

    pd = res.get("presetDissents") or []
    if pd:
        lines.append("Preset slots suppressed by measured brand facts (brand wins):")
        for d in pd:
            lines.append(f"  - {d['slot']}: authored default → brand fact "
                         f"{_fmt_value(d['brand'])} WINS ({d['provenance']})")
    return lines


def render_style_directive_block(style_id: str, resolutions: dict[str, dict],
                                 library: StyleLibrary) -> str:
    """Deterministic prompt block: the resolved style directive as LAYOUT
    GUIDANCE (stage 2). Composition-shaping prose only — brand facts/neverDo
    stay the harder law and are stated as such inside the block. Byte-stable
    for fixed inputs (section order = the caller's dict order)."""
    if not resolutions:
        return ""
    directive = library.styles.get(style_id) or {}
    label = directive.get("label") or style_id
    first = next(iter(resolutions.values()))
    con_lines = [f"  - {k}: {_fmt_value(first['constraints'][k])}"
                 for k in sorted(first.get("constraints") or {})]
    sig_lines = [f"  - {s}" for s in (directive.get("signatures") or [])]
    disc_lines = [f"  - {d}" for d in first.get("layoutDisciplines") or []]

    sec_lines = []
    for sid, res in resolutions.items():
        prim = str(res.get("layout") or "")
        desc = str(((library.primitives.get(prim) or {}).get("desc") or "")).strip()
        hint = _PRIMITIVE_ARCHETYPE_HINT.get(prim, "")
        extra = []
        rules = [r for r in res.get("rules") or []]
        if rules:
            extra.append("rules: " + "; ".join(str(r) for r in rules))
        genre = [i["text"] for i in res.get("invariants") or [] if i["class"] == "genre"]
        if genre:
            extra.append("soft defaults (brand evidence may override): "
                         + "; ".join(genre))
        if sid == "hero":
            # copy-first doctrine intact (INTEGRATION-PLAN stage D): the directive
            # only RERANKS an offered archetype shortlist; the copy plan still picks.
            extra.append("if HERO STRUCTURE CANDIDATES are offered above, prefer the "
                         "candidate whose skeleton is closest to this layout — the "
                         "copy plan still picks")
        sec_lines.append(
            f"- {sid}: layout `{prim}` — {desc}"
            + (f" Compose as {hint}." if hint else "")
            + (("\n    " + "\n    ".join(extra)) if extra else ""))

    dissent_lines = []
    for res in resolutions.values():
        for d in res.get("dissents") or []:
            line = (f"  - {d['key']}: directive said {_fmt_value(d['directive'])} → "
                    f"brand fact {_fmt_value(d['brand'])} WINS ({d['provenance']})")
            if line not in dissent_lines:
                dissent_lines.append(line)

    parts = [
        STYLE_BLOCK_BEGIN,
        f"## STYLE DIRECTIVE — {label} (style-library `{style_id}`, resolved per section)",
        "This run composes in a PICKED STYLE. The directive below RERANKS layout",
        "choices and sets compositional posture. It NEVER outranks brand facts,",
        "brand neverDo, or the gate battery: where a directive value conflicts",
        "with a measured brand fact, the brand fact wins (dissents listed below).",
        "",
        "Style constraints (compositional posture, brand tokens still paint):",
        *con_lines,
        "Style signature moves (make these READABLE in the composition):",
        *sig_lines,
    ]
    if disc_lines:
        parts += ["Layout disciplines (translated bias):", *disc_lines]
    preset_lines = _preset_lines(first)          # §P: empty for no-preset styles
    if preset_lines:
        parts += ["", *preset_lines]
    parts += [
        "",
        "Per-section layout guidance (the resolver's picks for this style):",
        *sec_lines,
        "",
        # bakeoff round-1 finding (2026-07-14): left-flush directive postures led
        # the model to ride reused patterns' own asymmetric alignment WITHOUT a
        # section-level declaration — the pattern stance then stamps left with no
        # counterweight and hard-fails the alignment-resolution gate. The contract
        # reminder is generic (any style, any brand): declare alignment explicitly.
        "Alignment contract (HARD — the alignment-resolution gate enforces it):",
        "  declare `alignment` EXPLICITLY on every section. An asymmetric anchor",
        '  ({"anchor":"left"|"right"}) MUST name a real slot as `counterweight`;',
        "  a section left undeclared inherits its reused pattern's own asymmetric",
        "  stance WITHOUT a counterweight and FAILS the gate. Where this style's",
        "  posture is flush-asymmetric, declare the anchor AND the counterweight",
        '  slot; where no balancing slot exists, declare {"anchor":"centered"}.',
    ]
    if dissent_lines:
        parts += ["", "Brand-evidence dissents (brand facts that beat the directive):",
                  *dissent_lines]
    parts.append(STYLE_BLOCK_END)
    return "\n".join(parts) + "\n"


# ── CLI: inspect a resolution ───────────────────────────────────────────────────────

def main() -> None:
    import argparse
    import json as _json
    ap = argparse.ArgumentParser(description="Resolve style-library (section × style"
                                             " [× brand]) specs — inspection CLI.")
    ap.add_argument("--style", required=True, help="style-library style id (e.g. swiss)")
    ap.add_argument("--section", default=None, help="one section id (default: all)")
    ap.add_argument("--brand", type=Path, default=None,
                    help="brand run dir (brand.yaml + pass-1 artifacts) for the §4.2 merge")
    ap.add_argument("--block", action="store_true",
                    help="print the stage-2 prompt guidance block instead of JSON")
    args = ap.parse_args()

    library = load_library()
    bundle = load_brand_bundle(args.brand) if args.brand else None
    sections = [args.section] if args.section else None
    resolutions = resolve_all(args.style, library, bundle, sections)
    if args.block:
        print(render_style_directive_block(args.style, resolutions, library))
    else:
        print(_json.dumps(resolutions, indent=2, default=str))


if __name__ == "__main__":
    main()
