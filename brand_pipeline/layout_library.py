#!/usr/bin/env python3
"""layout_library.py - the reusable USE-CASE layout-pattern library + retrieval engine.

This is to LAYOUTS what ``styles.py`` is to visual structure: a pure loader / merge /
select engine over two stacked tiers (build order strict: STANDARD is the base, PROJECT
layers on top and wins on ties):

  1. STANDARD library (base) - ``contracts/layout-patterns/<useCase>.yaml`` (schema
     ``layout-patterns.v1``, brand-schema.md §4.4). Brand-AGNOSTIC, use-case-keyed recipes,
     ``origin: designed`` (blessed, overridable). Seeded from ``harvest_patterns.py``.
  2. PROJECT library (override) - ``runs/<brand>/brand/layout-library.yaml`` (same schema),
     the project's own extracted patterns (``origin: extracted``).

PRECEDENCE (Appendix C, parallel to styles.py Appendix B):
  - PROJECT patterns win on ties (``LIB_BIAS``): an equal-or-better project match always
    beats a standard one.
  - STANDARD supplies the base used when the project has no adequate match.
  - The brand's OWN ``neverDo`` is the only hard gate: a pattern whose special treatments
    would violate a ``neverDo`` is filtered out BEFORE scoring (reuse-before-create stays
    brand-safe).

Retrieval: ``match(query, ...)`` scores candidates (project-first) and returns
``reuse`` / ``adapt`` / ``miss`` so the caller reuses the closest pattern instead of
reinventing HTML/CSS. Writes nothing except the project library via ``promote`` (append/
reconcile), used by the Layout Analyst on a true miss.

CLI:
  python3 brand_pipeline/layout_library.py <useCase> <brand.yaml> [--demo]
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTRACTS_LP_DIR = REPO_ROOT / "brand_pipeline" / "contracts" / "layout-patterns"

# Canonical use-cases (must match the standard-library filenames + harvest buckets).
USE_CASES = ("hero", "features", "pricing", "testimonial", "gallery", "cta",
             "about", "faq", "logos", "footer")

# ── scoring weights + thresholds ────────────────────────────────────────────────
W_ARCHETYPE = 1.0
W_SLOTS = 2.0
W_SIZEREL = 1.0
W_TREATMENTS = 2.0
W_SURFACE = 0.5
LIB_BIAS = 0.75            # project tie-break (small vs slot/treatment weights: a clearly
                           # better standard match still wins; ties go to project).
REUSE_THRESHOLD = 4.5      # >= -> reuse the pattern as-is (bind brand tokens + copy)
ADAPT_THRESHOLD = 2.5      # [ADAPT, REUSE) -> nearest pattern + tune variantKnobs
                           # < ADAPT -> miss -> invent + promote to project library

TREATMENT_KINDS = ("ghost-word", "overlap", "stagger", "bleed", "marginal-caption",
                   "text-on-media", "counter-rotate", "float-wrap", "inset",
                   # editorial-harvest-2026-07 (P2 overlay family + G8/G9):
                   "straddle", "panel-on-media", "scrim-band", "framed", "type-behind-media",
                   # editorial-harvest-2026-07 (P3 typographic devices):
                   "mixed-face", "stepped-lines", "break-frame")

# ── alignment enum (AS-18: alignment resolution is explicit + source-stamped) ─────
# The canonical anchor vocabulary shared by the three resolution layers (section-
# explicit `alignment.anchor`, pattern `contentShape.alignment`, style role default).
# `space-between` was previously OUT of the enum and silently dropped
# (footer-compact-utility-bar declared it and rendered as accidental flex-start);
# it is now admitted. `center` normalizes to `centered`.
ALIGN_ANCHORS = ("centered", "left", "right", "space-between", "edge-to-edge", "mixed")


def normalize_anchor(value, *, where: str = "") -> str | None:
    """Normalize an alignment anchor to the canonical enum. Out-of-enum values are a
    LOUD warning (never a silent drop — AS-18) and resolve to None so the caller falls
    through to the next resolution layer explicitly."""
    if value is None:
        return None
    a = str(value).strip().lower()
    if a == "center":
        a = "centered"
    if a not in ALIGN_ANCHORS:
        print(f"[alignment] WARNING: out-of-enum anchor '{value}'"
              f"{' in ' + where if where else ''} — expected one of {ALIGN_ANCHORS}; "
              "value ignored (falls through to the next resolution layer)",
              file=sys.stderr)
        return None
    return a


# ── the pattern object ──────────────────────────────────────────────────────────

@dataclass
class Pattern:
    id: str
    use_case: str
    archetype_ref: str
    surface_intent: str
    intent: str
    content_shape: dict
    special_treatments: list[dict]
    responsive: dict
    variant_knobs: dict
    origin: str                       # extracted | designed
    confidence: str
    scope: str
    provenance: list[str]
    lib: str = ""                     # "project" | "standard" (set by the loader)
    raw: dict = field(default_factory=dict)

    # ── derived signature helpers (used by the matcher) ──
    @property
    def slots(self) -> list[dict]:
        return list((self.content_shape or {}).get("slots", []) or [])

    @property
    def alignment(self) -> dict | None:
        """The pattern's declared ``contentShape.alignment`` (brand-schema §4.4),
        normalized to ``{"anchor": <enum>, "counterweight": <slot|device|None>,
        "inheritance": <str|None>}``. Previously this block was NEVER parsed into the
        Pattern object (AS-18): only 2/27 standard patterns declared anything and even
        those declarations no-oped, while `footer-compact-utility-bar`'s
        ``space-between`` was silently dropped as out-of-enum. Accepts both the schema's
        ``value:`` spelling and the composer-side ``anchor:`` spelling. Returns None
        when the pattern declares no stance (resolution falls through to the style)."""
        a = (self.content_shape or {}).get("alignment")
        if not isinstance(a, dict):
            return None
        anchor = normalize_anchor(a.get("anchor", a.get("value")),
                                  where=f"pattern '{self.id}' contentShape.alignment")
        if anchor is None:
            return None
        return {"anchor": anchor,
                "counterweight": a.get("counterweight"),
                "inheritance": a.get("inheritance")}

    def treatment_kinds(self) -> set[str]:
        return {str(t.get("kind")) for t in (self.special_treatments or []) if t.get("kind")}

    def textlen_multiset(self) -> list[str]:
        return sorted(str(s.get("textLen", "none")) for s in self.slots
                      if str(s.get("textLen", "none")) != "none")

    def has_media(self) -> bool:
        return any(s.get("mediaAspect") or s.get("mediaScale")
                   or "media" in str(s.get("role", "")).lower()
                   or str(s.get("width")) == "media" for s in self.slots)

    def has_ghostword(self) -> bool:
        return "ghost-word" in self.treatment_kinds()


def _pattern_from_dict(d: dict, use_case: str, lib: str) -> Pattern:
    return Pattern(
        id=str(d.get("id")),
        use_case=str(d.get("useCase") or use_case),
        archetype_ref=str(d.get("archetypeRef") or "stack"),
        surface_intent=str(d.get("surfaceIntent") or "any"),
        intent=str(d.get("intent") or ""),
        content_shape=d.get("contentShape") or {},
        special_treatments=list(d.get("specialTreatments") or []),
        responsive=d.get("responsive") or {},
        variant_knobs=d.get("variantKnobs") or {},
        origin=str(d.get("origin") or ("designed" if lib == "standard" else "extracted")),
        confidence=str(d.get("confidence") or "medium"),
        scope=str(d.get("scope") or "design-language"),
        provenance=list(d.get("provenance") or []),
        lib=lib,
        raw=d,
    )


# ── loaders (base = standard, override = project) ───────────────────────────────

def load_standard_patterns(use_case: str, lp_dir: Path | None = None) -> list[Pattern]:
    """Load the STANDARD (brand-agnostic) patterns for a use-case. Missing file -> []."""
    base = Path(lp_dir) if lp_dir else CONTRACTS_LP_DIR
    path = base / f"{use_case}.yaml"
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text()) or {}
    return [_pattern_from_dict(p, use_case, "standard") for p in (data.get("patterns") or [])]


def _project_library_path(brand_yaml: Path) -> Path:
    return Path(brand_yaml).parent / "layout-library.yaml"


def load_project_patterns(brand_yaml: Path, use_case: str | None = None) -> list[Pattern]:
    """Load the PROJECT library beside ``brand.yaml``. Optionally filter to one use-case.
    Missing library -> [] (a project simply has no learned patterns yet)."""
    path = _project_library_path(brand_yaml)
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text()) or {}
    pats = [_pattern_from_dict(p, str(p.get("useCase") or ""), "project")
            for p in (data.get("patterns") or [])]
    return [p for p in pats if use_case is None or p.use_case == use_case]


# ── merged library context (project-first) ──────────────────────────────────────

@dataclass
class LibraryContext:
    use_case: str
    candidates: list[Pattern]         # PROJECT patterns first, then STANDARD
    brand_neverdo: list[str] = field(default_factory=list)


def brand_neverdo_ids(doc: dict) -> list[str]:
    return [str(r.get("id")) for r in (doc.get("neverDo") or []) if isinstance(r, dict) and r.get("id")]


def resolve_library(use_case: str, brand_yaml: Path, lp_dir: Path | None = None) -> LibraryContext:
    """Layer PROJECT patterns over STANDARD for a use-case (project-first ordering)."""
    doc = yaml.safe_load(Path(brand_yaml).read_text()) if Path(brand_yaml).exists() else {}
    project = load_project_patterns(brand_yaml, use_case)
    standard = load_standard_patterns(use_case, lp_dir)
    return LibraryContext(use_case=use_case, candidates=project + standard,
                          brand_neverdo=brand_neverdo_ids(doc or {}))


# ── neverDo hard filter (brand-safe reuse) ──────────────────────────────────────

def _violates_neverdo(pattern: Pattern, neverdo_ids: list[str]) -> str | None:
    """Return the offending neverDo id if this pattern's treatments would break a brand
    prohibition, else None. Only the clearly-encodable devices are checked here; the render
    gate (onbrand_check.py) remains the authoritative check. Unknown prohibitions never
    over-filter (fail open).

    SANCTIONED treatments are excluded from the screened set (mirrors
    generate_composition._section_to_pattern): a pattern whose text-on-media/straddle is
    explicitly blessed (e.g. the hero display-title-over-media exception) must stay
    retrievable for a brand carrying no-text-on-photos."""
    media_slots = {str(s.get("name")) for s in pattern.slots
                   if s.get("mediaAspect") or s.get("mediaScale")
                   or any(k in str(s.get("role", "")).lower()
                          for k in ("photo", "media", "image"))}
    kinds = set()
    for t in (pattern.special_treatments or []):
        k = str(t.get("kind") or "")
        if not k or t.get("sanctioned"):
            continue
        # a straddle whose target is a MEDIA slot (media-over-seam / media-over-media)
        # is not a text-on-photography device — don't screen it as one.
        if k == "straddle" and str(t.get("target")) in media_slots:
            continue
        kinds.add(k)
    blob = (pattern.intent + " " + " ".join(str(s.get("role", "")) for s in pattern.slots)
            + " " + " ".join(json.dumps(t) for t in pattern.special_treatments)).lower()
    for nd in neverdo_ids:
        n = nd.lower()
        # text overlaid on photography (incl. the text-meets-media straddle/occlusion kinds)
        if "text" in n and any(k in n for k in ("photo", "media", "image")):
            if kinds & {"text-on-media", "straddle", "type-behind-media"}:
                return nd
        # filled/pill buttons
        if "button" in n and ("button" in blob and "link" not in blob):
            return nd
        # cards on a light/cream canvas
        if "card" in n and "card" in blob and pattern.surface_intent in ("primary", "any"):
            return nd
        # gradients / tints
        if "gradient" in n and "gradient" in blob:
            return nd
        # boxed/filled inputs
        if ("boxed" in n or "input" in n) and ("boxed" in blob or "filled-input" in blob):
            return nd
    return None


# ── retrieval query + scoring ───────────────────────────────────────────────────

@dataclass
class Query:
    use_case: str
    textlens: list[str] = field(default_factory=list)   # observed text-length classes
    has_media: bool = False
    media_aspect: str = ""
    treatments: set[str] = field(default_factory=set)    # observed special-treatment kinds
    surface_intent: str = "any"
    archetype: str = ""


def _multiset_similarity(a: list[str], b: list[str]) -> float:
    """Bag overlap in [0,1]: 2·|intersection multiset| / (|a|+|b|). Both empty -> 1."""
    if not a and not b:
        return 1.0
    from collections import Counter
    ca, cb = Counter(a), Counter(b)
    inter = sum((ca & cb).values())
    return (2 * inter) / (len(a) + len(b)) if (a or b) else 1.0


def _jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b) if (a | b) else 1.0


def score_pattern(pattern: Pattern, query: Query) -> float:
    """Composite score (see Appendix C). Returns -inf when the use-case gate fails."""
    if pattern.use_case != query.use_case:
        return float("-inf")
    score = 0.0
    # archetype compatibility (unknown query archetype -> neutral 0.5)
    if query.archetype:
        score += W_ARCHETYPE * (1.0 if pattern.archetype_ref == query.archetype else 0.0)
    else:
        score += W_ARCHETYPE * 0.5
    # slot-shape similarity: text-length multiset overlap + media presence agreement
    tl = _multiset_similarity(pattern.textlen_multiset(), query.textlens)
    media_agree = 1.0 if pattern.has_media() == query.has_media else 0.0
    score += W_SLOTS * (0.7 * tl + 0.3 * media_agree)
    # size-relationship consistency: if the query carries a media aspect, reward a match;
    # else neutral. (Full sizeRel numeric matching is a future refinement.)
    if query.media_aspect:
        pat_aspects = {str(s.get("mediaAspect")) for s in pattern.slots if s.get("mediaAspect")}
        score += W_SIZEREL * (1.0 if query.media_aspect in pat_aspects else 0.4)
    else:
        score += W_SIZEREL * 0.5
    # special-treatment overlap (ghost-word / overlap / stagger / …)
    score += W_TREATMENTS * _jaccard(pattern.treatment_kinds(), query.treatments)
    # surface compatibility ("any" pattern fits everything)
    if pattern.surface_intent == "any" or not query.surface_intent or query.surface_intent == "any":
        score += W_SURFACE * 1.0
    else:
        score += W_SURFACE * (1.0 if pattern.surface_intent == query.surface_intent else 0.0)
    # project tie-break
    if pattern.lib == "project":
        score += LIB_BIAS
    return score


@dataclass
class MatchResult:
    pattern: Pattern | None
    lib: str
    score: float
    match_kind: str                   # reuse | adapt | miss
    ranked: list[tuple[Pattern, float]] = field(default_factory=list)
    filtered: list[tuple[str, str]] = field(default_factory=list)  # (patternId, neverDoId)


def match(query: Query, brand_yaml: Path, lp_dir: Path | None = None) -> MatchResult:
    """Score all candidates (project-first), hard-filter brand neverDo violations, and
    classify the best as reuse / adapt / miss."""
    ctx = resolve_library(query.use_case, brand_yaml, lp_dir)
    ranked: list[tuple[Pattern, float]] = []
    filtered: list[tuple[str, str]] = []
    for p in ctx.candidates:
        bad = _violates_neverdo(p, ctx.brand_neverdo)
        if bad:
            filtered.append((p.id, bad))
            continue
        s = score_pattern(p, query)
        if s != float("-inf"):
            ranked.append((p, s))
    # stable sort: higher score first; project before standard on equal score (LIB_BIAS
    # already nudges, this keeps ordering deterministic).
    ranked.sort(key=lambda ps: (ps[1], ps[0].lib == "project"), reverse=True)
    if not ranked:
        return MatchResult(None, "", float("-inf"), "miss", ranked, filtered)
    best, best_score = ranked[0]
    kind = "reuse" if best_score >= REUSE_THRESHOLD else \
           "adapt" if best_score >= ADAPT_THRESHOLD else "miss"
    return MatchResult(best if kind != "miss" else None, best.lib, best_score, kind,
                       ranked, filtered)


# ── query construction from a brand.yaml layout instance (generation wiring) ─────

_USECASE_KEYWORDS = {
    "hero": ("hero", "opening", "bookend", "masthead"),
    "pricing": ("pricing", "price", "plan", "ticket"),
    "features": ("feature", "benefit", "process", "step", "info-band", "info_band", "band"),
    "testimonial": ("testimonial", "quote", "review"),
    "cta": ("cta", "conversion", "signup", "newsletter", "subscribe", "closing"),
    "gallery": ("gallery", "card", "grid", "collage", "editorial"),
    "about": ("about", "story", "mission"),
    "faq": ("faq", "question", "accordion"),
    "logos": ("logos", "partners", "clients"),
    "footer": ("footer",),
}


def infer_use_case(layout: dict) -> str:
    blob = (str(layout.get("id", "")) + " "
            + " ".join(str(s.get("role", "")) for s in (layout.get("slots") or []))).lower()
    for uc, keys in _USECASE_KEYWORDS.items():
        if any(k in blob for k in keys):
            return uc
    return "hero"


def _textlen_for(role: str, contract: str) -> str:
    r = (role + " " + contract).lower()
    if any(k in r for k in ("eyebrow", "caption", "label", "overline")):
        return "short"
    if any(k in r for k in ("paragraph", "body", "lede", "rich")):
        return "long"
    if any(k in r for k in ("heading", "title", "header")):
        return "medium"
    if any(k in r for k in ("ghost", "watermark", "wordmark")):
        return "word"
    return "none"


def query_from_layout(layout: dict, doc: dict | None = None) -> Query:
    """Derive a retrieval Query from a brand.yaml layouts[] entry (its blockMapping shapes
    + grid/overlap rules). Used by the composer to look up a matching pattern."""
    mappings = layout.get("blockMapping") or []
    textlens = [tl for m in mappings
                if (tl := _textlen_for(str(m.get("role", "")), str(m.get("contract", "")))) != "none"]
    has_media = any("image" in str(m.get("contract", "")).lower()
                    or "media" in str(m.get("role", "")).lower() for m in mappings)
    grid = layout.get("gridRules") or {}
    overlap = layout.get("overlapRules") or {}
    treatments: set[str] = set()
    if grid.get("stagger"):
        treatments.add("stagger")
    if grid.get("overlap") or overlap.get("types"):
        treatments.add("overlap")
    blob = json.dumps(grid) + json.dumps(overlap)
    if "ghost" in blob.lower() or "watermark" in blob.lower():
        treatments.add("ghost-word")
    surf = str(layout.get("surfaceIntent") or "any")
    surf_short = surf.split("/")[-1] if "/" in surf else surf
    return Query(use_case=infer_use_case(layout), textlens=textlens, has_media=has_media,
                 treatments=treatments, surface_intent=surf_short,
                 archetype=str(layout.get("archetype") or ""))


# ── get by ref + promote (project-library write; append/reconcile) ──────────────

def get(pattern_ref: dict, brand_yaml: Path, lp_dir: Path | None = None) -> Pattern | None:
    """Resolve a layouts[].patternRef {lib, id} to its Pattern."""
    if not isinstance(pattern_ref, dict):
        return None
    lib = pattern_ref.get("lib")
    pid = pattern_ref.get("id")
    pools: list[Pattern] = []
    if lib == "project":
        pools = load_project_patterns(brand_yaml)
    elif lib == "standard":
        for uc in USE_CASES:
            pools += load_standard_patterns(uc, lp_dir)
    else:  # unknown lib -> search both
        pools = load_project_patterns(brand_yaml)
        for uc in USE_CASES:
            pools += load_standard_patterns(uc, lp_dir)
    return next((p for p in pools if p.id == pid), None)


def pattern_dict_from_section(section: dict, *, brief_id: str = "",
                              provenance: list[str] | None = None,
                              confidence: str = "medium") -> dict:
    """Convert a gate-green ``composition.v1`` SECTION into a ``layout-patterns.v1`` pattern
    dict ready for ``promote()`` (the PROMOTION LOOP — Part B). This is the inverse of
    ``generate_composition._section_to_pattern``: it lifts a one-off novel section that the
    on-brand gate blessed into a reusable, brand-agnostic project pattern so future runs can
    reuse/adapt it (novelty compounds into the library).

    Only the STRUCTURE is promoted — archetype, slot SHAPE (name/role/contract/textLen/
    sizeClass/width/mediaAspect/z; the inline copy + concrete asset srcs are dropped so the
    pattern stays content-agnostic), and the special treatments. ``origin`` is stamped
    ``extracted`` (a learned project pattern) and a synthetic id is derived when the section
    has none. Writes nothing — pair with ``promote()`` to persist."""
    use_case = str(section.get("useCase") or "")
    raw_id = str(section.get("id") or "").strip()
    pid = raw_id or f"{use_case or 'section'}-novel"
    if not pid.endswith("-promoted"):
        pid = f"{pid}-promoted"

    def _clean_slot(s: dict) -> dict:
        keep = ("name", "role", "contract", "textLen", "sizeClass", "width",
                "mediaAspect", "z")
        out = {k: s[k] for k in keep if k in s and s[k] is not None}
        # preserve a media slot's shape without a concrete src (content-agnostic).
        if isinstance(s.get("asset"), dict) and s["asset"].get("ratio"):
            out.setdefault("mediaAspect", s["asset"]["ratio"])
        return out

    slots = [_clean_slot(s) for s in (section.get("slots") or []) if isinstance(s, dict)]
    treatments = [dict(t) for t in (section.get("treatments") or []) if isinstance(t, dict)]
    prov = list(provenance or [])
    if brief_id:
        prov.append(f"promoted from composition.v1 section '{raw_id or pid}' (brief {brief_id})")
    return {
        "id": pid,
        "useCase": use_case,
        "archetypeRef": str(section.get("archetype") or "stack"),
        "surfaceIntent": str(section.get("surfaceIntent") or "any"),
        "intent": str(section.get("_intent") or section.get("rationale")
                      or f"promoted novel {use_case} pattern").strip(),
        "contentShape": {"slots": slots},
        "specialTreatments": treatments,
        "responsive": {},
        "variantKnobs": section.get("knobs") or {},
        "origin": "extracted",
        "confidence": confidence,
        "scope": "design-language",
        "provenance": prov,
    }


def promote(pattern_dict: dict, brand_yaml: Path) -> Path:
    """Append (or reconcile by id) a pattern into the project ``layout-library.yaml``.
    Used by the Layout Analyst on a true miss AND by the Part-B PROMOTION LOOP (a gate-green
    novel composition section, converted via ``pattern_dict_from_section``). Preserves
    existing patterns; on an id clash the incoming entry replaces the old one (the caller
    owns changelog discipline)."""
    path = _project_library_path(brand_yaml)
    data = yaml.safe_load(path.read_text()) if path.exists() else {}
    if not isinstance(data, dict):
        data = {}
    data.setdefault("schemaVersion", "layout-patterns.v1")
    pats = data.get("patterns") or []
    pats = [p for p in pats if p.get("id") != pattern_dict.get("id")]
    pats.append(pattern_dict)
    data["patterns"] = pats
    path.write_text(yaml.safe_dump(data, sort_keys=False, width=100))
    return path


def render_pattern_constraint(patterns: list[Pattern]) -> str:
    """Render a reuse-constraint markdown block for the SITE GENERATOR prompt. Injecting this
    tells the model to REUSE the resolved pattern (fill slots with brand copy/tokens, tune
    only the listed knobs) instead of reinventing section structure — the whole point of the
    library. Empty list -> ""."""
    if not patterns:
        return ""
    out = ["## Layout patterns to REUSE (do not reinvent section structure)",
           "",
           "For each section below, reuse the given pattern: keep its archetype, slot shape "
           "(text lengths, media aspect/scale), and special treatments; fill slots with the "
           "brand's real copy + tokens; tune ONLY the listed variant knobs. All sizes are "
           "relationships/classes — resolve them against the brand's type/spacing scale.", ""]
    for p in patterns:
        treatments = ", ".join(sorted(p.treatment_kinds())) or "none"
        knobs = ", ".join(p.variant_knobs.keys()) or "none"
        out.append(f"- **{p.use_case} → `{p.id}`** [{p.lib}] (archetype `{p.archetype_ref}`, "
                   f"surface `{p.surface_intent}`): {p.intent}")
        out.append(f"    - special treatments: {treatments}; tunable knobs: {knobs}")
    out.append("")
    return "\n".join(out)


# ── CLI ─────────────────────────────────────────────────────────────────────────

def _print_context(ctx: LibraryContext):
    print(f"use-case: {ctx.use_case}")
    print(f"brand neverDo: {', '.join(ctx.brand_neverdo) or '(none)'}")
    print(f"candidates ({len(ctx.candidates)}) — PROJECT first, then STANDARD:")
    for p in ctx.candidates:
        print(f"  [{p.lib:8}] {p.id:34} archetype={p.archetype_ref:8} "
              f"surface={p.surface_intent:14} treatments={sorted(p.treatment_kinds())}")


def _run_match(label: str, query: Query, brand_yaml: Path):
    res = match(query, brand_yaml)
    print(f"\n=== match: {label} ===")
    print(f"query: use_case={query.use_case} textlens={query.textlens} "
          f"has_media={query.has_media} treatments={sorted(query.treatments)}")
    if res.filtered:
        print("filtered (neverDo): " + ", ".join(f"{pid}!={nd}" for pid, nd in res.filtered))
    print(f"-> {res.match_kind.upper()} "
          + (f"[{res.lib}] {res.pattern.id} (score={res.score:.2f})" if res.pattern
             else f"(best score={res.score:.2f})"))
    for p, s in res.ranked[:5]:
        print(f"     {s:6.2f}  [{p.lib:8}] {p.id}")


def main():
    ap = argparse.ArgumentParser(description="Inspect the layout-pattern library + retrieval.")
    ap.add_argument("use_case", help="use-case to resolve (hero, pricing, …)")
    ap.add_argument("brand_yaml", type=Path)
    ap.add_argument("--demo", action="store_true",
                    help="run two canonical matches (ghostword hero vs plain centered hero)")
    args = ap.parse_args()

    ctx = resolve_library(args.use_case, args.brand_yaml)
    _print_context(ctx)

    if args.demo:
        _run_match(
            "ghostword staggered hero (short eyebrow + long body + landscape media)",
            Query(use_case="hero", textlens=["word", "short", "long"], has_media=True,
                  media_aspect="landscape", treatments={"ghost-word", "overlap", "stagger"},
                  surface_intent="inverse"),
            args.brand_yaml)
        _run_match(
            "plain centered hero (short heading, no ghost word)",
            Query(use_case="hero", textlens=["short", "medium"], has_media=False,
                  treatments=set(), surface_intent="any"),
            args.brand_yaml)
        _run_match(
            "text-on-photo hero (should be neverDo-filtered for a no-text-on-photos brand)",
            Query(use_case="hero", textlens=["medium"], has_media=True,
                  treatments={"text-on-media"}, surface_intent="any"),
            args.brand_yaml)


if __name__ == "__main__":
    main()
