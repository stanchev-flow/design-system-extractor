#!/usr/bin/env python3
"""styles.py - the STYLE layer of the two-layer site-generation model.

TWO STACKED LAYERS (build order is strict: STYLE is the base, BRAND layers on top):

  1. STYLE layer (base) - supplies STRUCTURE + DEFAULTS: shape, depth, type scale/leading/
     tracking, density, color-DEPLOYMENT (not hues), motion, structural devices.
     Brand-agnostic. NEVER hardcodes a hue or font family - it references named brand
     SLOTS (paper, ink, accent, font-display, font-body, font-mono). Authored as a
     markdown spec in ``styles/<id>.md`` (legacy ``styles/style-<id>.md`` also accepted).

     The machine-consumed values live in a structured YAML FRONT-MATTER block (id, layer,
     owns[], never_sets[], composes_with[]; plus type/motion/radius/shape/spacing structure
     and, optionally, slots/invariants/soft_options/style_rules/failure_modes). This is the
     AUTHORITATIVE parsed source (deterministic, mirroring how ``brand.yaml`` is consumed).
     The markdown PROSE BODY stays as authored design guidance the generating LLM reads. The
     parser is FRONT-MATTER-FIRST with a PROSE-REGEX FALLBACK: any field absent from the
     front-matter is still derived from the prose body exactly as before, so a non-migrated
     style file (or a single un-migrated field) loads unchanged.

  2. BRAND layer (on top) - the extracted brand (runs/<brand>/brand/brand.yaml +
     brand.md) fills the style's named slots and may override any value it explicitly
     sets - including the style's "Style definition" core rules.

PRECEDENCE (enforced in ``merge``):
  - BRAND wins on any value it explicitly sets (colors, fonts, tokens, AND any style
    core rule the brand explicitly contradicts). The documented example is the WoodWave
    hero (#sec-0) centered, accent-gold display heading overriding the style's
    left-anchored / ink-display defaults (see compose_page.hero_brand_override_css).
  - STYLE supplies structure + defaults for everything the brand leaves unset (layout
    structure, shape, depth model, type scale, density, motion). It is the base the
    brand layers on top of, NOT an absolute floor.
  - There are NO absolute style non-negotiables. The only hard, non-overridable layer is
    the brand's OWN ``neverDo`` rules (enforced by onbrand_check.py).

This module is library-agnostic: styles live in ``styles/`` and brand stays in
``runs/<brand>/``. It writes nothing - it is a pure loader/merge engine consumed by the
renderer (render_hero_variants.py / render_section.py) and the on-brand gate
(onbrand_check.py).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from layout_library import normalize_anchor

# Repo-root-relative default location for authored style specs.
REPO_ROOT = Path(__file__).resolve().parent.parent
STYLES_DIR = REPO_ROOT / "styles"

# Documented brand-slot fallbacks (used ONLY when brand.md is silent on a slot).
# NEVER invent a second accent: when the brand carries no accent we fall back to ink
# (monochrome), we do NOT synthesize a new hue.
SLOT_FALLBACKS = {
    "paper": "#FCFCFA",   # near-white / off-white
    "ink": "#111111",     # near-black
    "font_display": "Georgia, 'Times New Roman', serif",
    "font_body": "system-ui, -apple-system, sans-serif",
    "font_mono": "ui-monospace, SFMono-Regular, Menlo, monospace",
}


# ── style structure (the part brand can NEVER change) ────────────────────────────

@dataclass
class StyleStructure:
    """Structural defaults supplied by the STYLE layer (the base; the brand may override
    any of these where it explicitly commits to a different value)."""
    radius: str = "0"                       # corner radius everywhere
    flat: bool = True                       # zero shadow / elevation / depth-gradient
    centered: bool = False                  # asymmetric, not centered-everything
    min_display_rem: float = 9.0            # poster-scale floor at desktop
    display_vw: float = 12.0                # documented intent (~12vw) -> rendered as cqw
    display_max_rem: float = 16.0           # upper clamp bound for the display tier
    display_leading: float = 0.94           # tight display leading (~0.92-1.0)
    display_tracking: str = "-0.02em"       # negative tracking on display
    motion_min_ms: int = 500                # restrained/slow motion floor
    motion_ms: int = 600                    # applied transition duration
    single_accent: bool = True              # one committed accent, never scattered

    # ── vertical rhythm / spacing scale (the style owns it; brand spacing tokens win) ──
    # A single named spacing scale (rem steps) so section padding + inter-block gaps are
    # deliberate, not ad-hoc. Defaults encode radical-editorial's documented scale so the
    # renderer always has concrete values even if the spec prose drifts. ``*_slot`` names
    # which scale step each structural gap defaults to (resolved via ``space()``).
    space_scale: dict = field(default_factory=lambda: {
        "3xs": "0.5rem", "2xs": "0.75rem", "xs": "1rem", "sm": "1.5rem",
        "md": "2.5rem", "lg": "4rem", "xl": "6rem", "2xl": "9rem",
    })
    section_pad_slot: str = "2xl"           # section vertical padding (top = bottom)
    block_gap_slot: str = "md"              # inter-block gap within a section
    cluster_gap_slot: str = "2xs"           # tight cluster gap (eyebrow→heading, …)

    # ── alignment stance (AS-18: explicit, source-stamped alignment resolution) ──
    # Machine-readable role/archetype -> anchor map parsed from the style front-matter's
    # ``alignment:`` block. ``alignment_default`` is the style's page-wide default anchor;
    # ``alignment_roles`` maps a section-role/useCase/archetype key (hero, cta,
    # conversion, collage, split, band, footer, …) to {"anchor": <enum>,
    # "counterweight": <named device|None>}. Both empty for a non-migrated style file —
    # the style then DECLARES NO STANCE and the composer keeps the legacy behavior
    # (never a silent stance invented on the style's behalf).
    alignment_default: str | None = None
    alignment_roles: dict = field(default_factory=dict)

    def declares_alignment(self) -> bool:
        """True when this style carries a machine-readable alignment stance."""
        return bool(self.alignment_default or self.alignment_roles)

    def align_for(self, *keys: str) -> dict | None:
        """Resolve the style-layer alignment for a section: the first role key that the
        style's ``alignment.roles`` map declares wins; otherwise the style default.
        Returns {"anchor", "counterweight", "role"} or None (style declares no stance)."""
        for key in keys:
            if not key:
                continue
            entry = self.alignment_roles.get(str(key).lower())
            if entry:
                return {"anchor": entry["anchor"],
                        "counterweight": entry.get("counterweight"), "role": str(key).lower()}
        if self.alignment_default:
            return {"anchor": self.alignment_default, "counterweight": None,
                    "role": "default"}
        return None

    def space(self, slot: str, fallback: str = "2.5rem") -> str:
        """Resolve a named scale step (or a literal rem already on the scale) to a value."""
        return self.space_scale.get(slot, fallback)

    @property
    def section_pad(self) -> str:
        return self.space(self.section_pad_slot, "9rem")

    @property
    def block_gap(self) -> str:
        return self.space(self.block_gap_slot, "2.5rem")

    @property
    def cluster_gap(self) -> str:
        return self.space(self.cluster_gap_slot, "0.75rem")

    def display_size_css(self) -> str:
        """Poster-scale display size as a container-query clamp.

        CRITICAL: the rendered iframe uses container-query units ONLY. The spec text
        documents intent as ``~12vw``; here we translate vw -> cqw so the rendered HTML
        never emits a viewport unit.
        """
        lo = _fmt_rem(self.min_display_rem)
        hi = _fmt_rem(self.display_max_rem)
        return f"clamp({lo}, {_fmt_num(self.display_vw)}cqw, {hi})"


def _fmt_num(n: float) -> str:
    return str(int(n)) if float(n).is_integer() else str(n)


def _fmt_rem(n: float) -> str:
    return f"{_fmt_num(n)}rem"


# ── style spec (parsed from styles/<id>.md) ──────────────────────────────────────

@dataclass
class Style:
    id: str
    layer: str
    owns: list[str]
    never_sets: list[str]
    slots: dict[str, str]                       # slot name -> documented fallback note
    style_rules: list[str]                      # the style's core rules (brand-overridable defaults)
    failure_modes: list[str]
    structure: StyleStructure
    # ── two-layer tier model (parsed from `## Invariants` / `## Soft options`) ──
    # invariants: tier-1 load-bearing style identity (advisory-STRONG; gate WARNs, never
    #   hard-fails, when broken with no documented brand override).
    # soft_options: tier-2 brand-choosable options, keyed by option-id ->
    #   {"allowed": <raw allowed-values string>, "default": <default value>}. A brand
    #   commits a choice via a token/primitive binding; the gate blesses it as an OVERRIDE.
    # Both default to empty so a style file WITHOUT these blocks loads with unchanged
    # behavior (back-compatible).
    invariants: list[str] = field(default_factory=list)
    soft_options: dict[str, dict] = field(default_factory=dict)
    # ── capability flag: off-grid generative EXPANSION (Part B) ──
    # offGridExpansion (front-matter boolean) is the style-level CAPABILITY GATE that decides
    # whether the composition generator may EXPAND beyond the captured/seeded layout set:
    #   TRUE  -> unlock the freedom-envelope off-grid treatments (stagger / overlap / bleed /
    #            float-wrap / counter-rotate) on non-hero sections AND allow novelty:"novel".
    #   FALSE -> the model may only reuse/adapt captured patterns; no novel sections and no
    #            off-grid treatments (enforced by generate_composition.offgrid_prefilter +
    #            the repair loop). The sanctioned hero bookend keeps its overlap/text-on-media
    #            regardless of the flag (it is style identity, not expansion).
    # Editorial styles (radical-editorial, editorial-luxury) set TRUE; clean/corporate
    # (corporate-saas-clean) sets FALSE. Absent -> False (conservative: no expansion).
    off_grid_expansion: bool = False
    title: str = ""
    raw_md: str = ""
    source_path: str = ""


def parse_front_matter(md: str) -> tuple[dict, str]:
    """Split a leading ``---`` YAML front-matter block from the markdown body."""
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", md, re.DOTALL)
    if not m:
        return {}, md
    meta = yaml.safe_load(m.group(1)) or {}
    return meta, m.group(2)


def _section(body: str, heading_re: str) -> str:
    """Return the text of the first markdown section whose heading matches."""
    m = re.search(rf"^#{{1,6}}\s*{heading_re}.*?$\n(.*?)(?=^#{{1,6}}\s|\Z)",
                  body, re.MULTILINE | re.DOTALL)
    return m.group(1).strip() if m else ""


def _bullets(text: str) -> list[str]:
    return [re.sub(r"\s+", " ", ln.strip()[1:].strip())
            for ln in text.splitlines() if ln.strip().startswith("- ")]


def _numbered(text: str) -> list[str]:
    return [re.sub(r"\s+", " ", re.sub(r"^\d+\.\s*", "", ln.strip()))
            for ln in text.splitlines() if re.match(r"^\d+\.\s", ln.strip())]


def _parse_slots(body: str) -> dict[str, str]:
    sec = _section(body, r"Brand slots")
    slots: dict[str, str] = {}
    for ln in sec.splitlines():
        m = re.match(r"-\s*`([a-z-]+)`\s*[—-]\s*(.*)", ln.strip())
        if m:
            slots[m.group(1)] = m.group(2).strip()
    return slots


def _parse_invariants(body: str) -> list[str]:
    """Parse the numbered ``## Invariants`` list (tier-1 style identity). Back-compatible:
    a style file with no Invariants block returns [] (behavior unchanged)."""
    return _numbered(_section(body, r"Invariants"))


# ``- `option-id`: [allowed, values] | default: `value` — optional trailing prose``
# (the separator before ``default:`` may be ``|`` or an em/en/hyphen dash; back-ticks
# around the id/default are optional). The default is captured as a SINGLE value token so
# any trailing rationale prose (which may itself contain back-ticked identifiers) is
# ignored.
_SOFT_OPT_RE = re.compile(
    r"-\s*`?([a-z0-9][a-z0-9-]*)`?\s*:\s*\[([^\]]*)\]\s*(?:\||—|–|-)\s*"
    r"default\s*:\s*`?([a-z0-9][a-z0-9./%-]*)`?",
    re.I)


def _parse_soft_options(body: str) -> dict[str, dict]:
    """Parse the ``## Soft options`` bullet list into ``{id: {allowed, default}}``.

    Each bullet is ``- `id`: [allowed values] | default: `value` — optional prose``. The
    default is stored as a single value token; trailing rationale prose is ignored. A
    style file with no Soft options block returns {} (behavior unchanged)."""
    sec = _section(body, r"Soft options")
    out: dict[str, dict] = {}
    for ln in sec.splitlines():
        m = _SOFT_OPT_RE.match(ln.strip())
        if not m:
            continue
        oid = m.group(1).strip()
        allowed = re.sub(r"\s+", " ", m.group(2).strip())
        default = m.group(3).strip()
        out[oid] = {"allowed": allowed, "default": default}
    return out


def _coerce_bool(value) -> bool | None:
    """Coerce a front-matter scalar to a bool. Returns None when unrecognized so the
    caller can apply the documented default rather than mis-reading a stray value."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        v = value.strip().lower()
        if v in ("true", "yes", "on", "1"):
            return True
        if v in ("false", "no", "off", "0"):
            return False
    return None


def _parse_off_grid_expansion(meta: dict) -> bool:
    """Read the ``offGridExpansion`` capability flag from the style front-matter.

    Front-matter-first + tolerant: honors a top-level ``offGridExpansion`` (the documented
    key), the snake_case ``off_grid_expansion`` alias, or a nested
    ``capabilities: { offGridExpansion: <bool> }`` block. Anything absent/unrecognized ->
    False (conservative: a style that does not opt in gets NO generative expansion, so a
    non-migrated style file keeps the safe reuse-only behavior)."""
    caps = meta.get("capabilities") or {}
    for src in (meta, caps if isinstance(caps, dict) else {}):
        for key in ("offGridExpansion", "off_grid_expansion", "off-grid-expansion"):
            if key in src:
                coerced = _coerce_bool(src[key])
                if coerced is not None:
                    return coerced
    return False


def _parse_structure(body: str, meta: dict | None = None) -> StyleStructure:
    """Derive structural numbers, FRONT-MATTER-FIRST with a PROSE-REGEX fallback.

    For each structural field the parser prefers a value in the YAML front-matter
    (``meta``) when present, and otherwise falls back to the existing regex-over-prose
    extraction (which itself falls back to the ``StyleStructure`` defaults). This keeps a
    style file that has NOT been migrated — or a single field not yet in front-matter —
    loading exactly as before, while a migrated field is read deterministically from the
    structured block (mirroring how ``brand.yaml`` is consumed). The recognized
    front-matter keys are:

        type:    {display_min_rem, display_vw, display_max_rem, display_leading,
                  display_tracking}
        motion:  {min_ms, base_ms}
        radius:  <css length>            # structural corner-radius default
        shape:   {flat, centered, single_accent}
        spacing: {scale: {step: rem}, section_pad_slot, block_gap_slot, cluster_gap_slot}
    """
    meta = meta or {}
    type_fm = meta.get("type") or {}
    motion_fm = meta.get("motion") or {}
    shape_fm = meta.get("shape") or {}
    spacing_fm = meta.get("spacing") or {}

    s = StyleStructure()
    type_sec = _section(body, r"Type")

    # display poster floor + upper clamp bound.
    # front-matter: exact final values (no re-derivation, so a migrated style reproduces
    # its parsed numbers byte-for-byte). prose fallback: "AT LEAST 9rem / ~12vw" + derived max.
    if "display_min_rem" in type_fm:
        s.min_display_rem = float(type_fm["display_min_rem"])
        if "display_vw" in type_fm:
            s.display_vw = float(type_fm["display_vw"])
        s.display_max_rem = float(type_fm["display_max_rem"]) if "display_max_rem" in type_fm \
            else round(max(s.min_display_rem * 1.8, s.min_display_rem + 6), 2)
    else:
        m = re.search(r"(\d+(?:\.\d+)?)\s*rem\s*/\s*~?\s*(\d+(?:\.\d+)?)\s*vw", type_sec, re.I)
        if m:
            s.min_display_rem = float(m.group(1))
            s.display_vw = float(m.group(2))
            s.display_max_rem = round(max(s.min_display_rem * 1.8, s.min_display_rem + 6), 2)

    # display leading: front-matter exact value, else prose range "~0.92-1.0" (bias tight).
    if "display_leading" in type_fm:
        s.display_leading = float(type_fm["display_leading"])
    else:
        m = re.search(r"leading[^0-9]*(\d?\.\d+)\s*-\s*(\d?\.?\d+)", type_sec, re.I)
        if m:
            lo, hi = float(m.group(1)), float(m.group(2))
            s.display_leading = round(lo + (hi - lo) * 0.2, 3)  # bias tight

    # negative tracking: front-matter exact value, else prose "~-0.02em".
    if "display_tracking" in type_fm:
        s.display_tracking = str(type_fm["display_tracking"])
    else:
        m = re.search(r"tracking[^-]*(-\d?\.\d+em)", type_sec, re.I)
        if m:
            s.display_tracking = m.group(1)

    # motion: front-matter {min_ms, base_ms} exact, else prose range "~320–620ms" (low
    # end = floor, midpoint = applied duration) OR a single "(500ms+)" floor.
    if "min_ms" in motion_fm or "base_ms" in motion_fm:
        if "min_ms" in motion_fm:
            s.motion_min_ms = int(motion_fm["min_ms"])
        if "base_ms" in motion_fm:
            s.motion_ms = int(motion_fm["base_ms"])
    else:
        motion_sec = _section(body, r"Motion")
        mr = re.search(r"(\d+)\s*(?:ms)?\s*[–—-]\s*(\d+)\s*ms", motion_sec)
        if mr:
            lo, hi = int(mr.group(1)), int(mr.group(2))
            s.motion_min_ms = lo
            s.motion_ms = round((lo + hi) / 2)
        else:
            m = re.search(r"(\d+)\s*ms", motion_sec)
            if m:
                s.motion_min_ms = int(m.group(1))
                s.motion_ms = max(s.motion_min_ms + 100, s.motion_min_ms)

    # shape/depth/density confirmations. front-matter carries the structural corner-radius
    # default + flat/centered/single-accent booleans; else confirm from prose (the
    # StyleStructure defaults already encode these). NB: the soft-option radius resolution
    # in ``load_style`` still runs on top of this (so the two-layer soft-radius model is
    # preserved regardless of source).
    if "radius" in meta:
        s.radius = str(meta["radius"])
    else:
        shape_sec = _section(body, r"Shape").lower()
        if "0px radius" in shape_sec or "corners sharp" in shape_sec:
            s.radius = "0"
    if "flat" in shape_fm:
        s.flat = bool(shape_fm["flat"])
    else:
        depth_sec = _section(body, r"Depth").lower()
        if "completely flat" in depth_sec or "zero shadow" in depth_sec:
            s.flat = True
    if "centered" in shape_fm:
        s.centered = bool(shape_fm["centered"])
    else:
        density_sec = _section(body, r"Density").lower()
        if "do not center everything" in density_sec or "asymmetric" in density_sec:
            s.centered = False
    if "single_accent" in shape_fm:
        s.single_accent = bool(shape_fm["single_accent"])

    # spacing scale + rhythm slot assignments. front-matter block preferred; else parse the
    # `#### Vertical rhythm & spacing scale` subsection (that heading terminates the Density
    # capture, so parse it directly; fall back to Density text for legacy specs that inlined it).
    if spacing_fm.get("scale") or any(
            spacing_fm.get(k) for k in ("section_pad_slot", "block_gap_slot", "cluster_gap_slot")):
        _apply_spacing_fm(spacing_fm, s)
    else:
        _parse_spacing(_section(body, r"Vertical rhythm") or _section(body, r"Density"), s)

    # alignment stance (AS-18): front-matter ONLY (no prose fallback — a stance must be
    # machine-explicit or absent). Shape:
    #   alignment:
    #     default: left|centered|…
    #     roles: { hero: centered, collage: {anchor: left, counterweight: ghost}, … }
    _apply_alignment_fm(meta.get("alignment"), s)
    return s


def _apply_alignment_fm(align_fm, s: StyleStructure) -> None:
    """Parse the front-matter ``alignment:`` block onto ``s`` in place. Role values may
    be a bare anchor string or ``{anchor, counterweight}``. Out-of-enum anchors warn
    loudly (via ``normalize_anchor``) and are dropped, never silently mis-read."""
    if not isinstance(align_fm, dict):
        return
    default = normalize_anchor(align_fm.get("default"), where="style alignment.default")
    if default:
        s.alignment_default = default
    roles = align_fm.get("roles")
    if not isinstance(roles, dict):
        return
    for key, val in roles.items():
        if isinstance(val, dict):
            anchor = normalize_anchor(val.get("anchor", val.get("value")),
                                      where=f"style alignment.roles.{key}")
            counterweight = val.get("counterweight")
        else:
            anchor = normalize_anchor(val, where=f"style alignment.roles.{key}")
            counterweight = None
        if anchor:
            s.alignment_roles[str(key).lower()] = {
                "anchor": anchor, "counterweight": counterweight}


def _apply_spacing_fm(spacing_fm: dict, s: StyleStructure) -> None:
    """Apply a front-matter ``spacing:`` block in place onto ``s`` (scale + rhythm slots).
    Only slot names that resolve against the active scale are honored (mirrors the prose
    parser's guard), so a stray slot never yields an unresolvable rhythm value."""
    scale = spacing_fm.get("scale")
    if scale:
        s.space_scale = {str(step): str(val) for step, val in scale.items()}
    for key, attr in (("section_pad_slot", "section_pad_slot"),
                      ("block_gap_slot", "block_gap_slot"),
                      ("cluster_gap_slot", "cluster_gap_slot")):
        slot = spacing_fm.get(key)
        if slot and str(slot) in s.space_scale:
            setattr(s, attr, str(slot))


def _parse_spacing(density_sec: str, s: StyleStructure) -> None:
    """Parse the vertical-rhythm / spacing scale from the rhythm subsection text, in
    place onto ``s``. Tolerant + back-compatible: a spec with no scale keeps the
    StyleStructure defaults (which already encode the documented scale), so older style
    files load unchanged.

    Expected (markdown) shape inside Density & rhythm:
        Spacing scale (rem):
        - `md` — 2.5rem
        Rhythm slots …:
        - section padding (top & bottom): `2xl` …
        - inter-block gap …: `md`.
        - tight cluster gap …: `2xs`–`xs`.
    """
    if not density_sec:
        return
    scale = {step: val for step, val in re.findall(
        r"-\s*`([0-9a-z]+)`\s*[—–-]\s*([0-9.]+rem)", density_sec)}
    if scale:
        s.space_scale = scale

    def _slot(label_re: str):
        m = re.search(rf"{label_re}[^\n]*?`([0-9a-z]+)`", density_sec, re.I)
        return m.group(1) if m and m.group(1) in s.space_scale else None

    sec = _slot(r"section padding")
    blk = _slot(r"inter-block gap")
    clu = _slot(r"(?:tight )?cluster gap")
    if sec:
        s.section_pad_slot = sec
    if blk:
        s.block_gap_slot = blk
    if clu:
        s.cluster_gap_slot = clu


def load_style(style_id: str, styles_dir: Path | None = None) -> Style:
    """Load + parse ``styles/<id>.md`` (legacy ``styles/style-<id>.md`` also accepted)."""
    base = Path(styles_dir) if styles_dir else STYLES_DIR
    # Preferred current convention: styles/<id>.md. Fall back to the legacy
    # styles/style-<id>.md name so older style files still resolve.
    path = base / f"{style_id}.md"
    if not path.exists():
        legacy = base / f"style-{style_id}.md"
        path = legacy if legacy.exists() else path
    if not path.exists():
        raise FileNotFoundError(
            f"style '{style_id}' not found (looked for {base}/{style_id}.md "
            f"and {base}/style-{style_id}.md)")
    md = path.read_text()
    meta, body = parse_front_matter(md)
    sid = str(meta.get("id") or style_id)
    title_m = re.search(r"^#\s+(.*)$", body, re.MULTILINE)
    # Every machine-consumed field below is FRONT-MATTER-FIRST with a PROSE fallback: when
    # the front-matter carries the key it is authoritative (deterministic, like brand.yaml);
    # otherwise the existing regex-over-prose extraction runs, so a non-migrated style file —
    # or a single field absent from front-matter — loads exactly as before. The prose body
    # stays authored as design guidance.
    #
    # The core rules live under "## Style definition"; stay tolerant of the legacy
    # "## ⚡ Non-negotiable …" heading so a style file that lags the rename still loads.
    rules = list(meta["style_rules"]) if meta.get("style_rules") is not None \
        else _numbered(_section(body, r"(?:Style definition|.*Non-negotiable)"))
    fm = list(meta["failure_modes"]) if meta.get("failure_modes") is not None \
        else _bullets(_section(body, r"Failure modes"))
    invariants = list(meta["invariants"]) if meta.get("invariants") is not None \
        else _parse_invariants(body)
    soft_options = dict(meta["soft_options"]) if meta.get("soft_options") is not None \
        else _parse_soft_options(body)
    slots = dict(meta["slots"]) if meta.get("slots") is not None else _parse_slots(body)
    # off-grid EXPANSION capability flag (Part B). Front-matter-first, tolerant of a few
    # documented spellings; a `capabilities:` block is also honored so the flag can live
    # beside future capability toggles. Absent -> False (no expansion; conservative).
    off_grid = _parse_off_grid_expansion(meta)
    structure = _parse_structure(body, meta)
    # Soft-radius fix: when the style declares `radius` as a SOFT option, the structural
    # default radius is that option's default (e.g. editorial-luxury's ~10px luxury
    # softness), NOT the StyleStructure hard-zero fallback. This fixes the bug where a
    # soft-radius style silently defaulted to 0. Only the intent-shaped values ("0"/px/rem)
    # are honored; the brand's `radius-global` token still wins in `merge()`.
    radius_opt = (soft_options.get("radius") or {}).get("default")
    if radius_opt:
        rv = _extract_radius_value(radius_opt)
        if rv:
            structure.radius = rv
    return Style(
        id=sid,
        layer=str(meta.get("layer", "style")),
        owns=list(meta.get("owns", []) or []),
        never_sets=list(meta.get("never_sets", []) or []),
        slots=slots,
        style_rules=rules,
        failure_modes=fm,
        structure=structure,
        invariants=invariants,
        soft_options=soft_options,
        off_grid_expansion=off_grid,
        title=title_m.group(1).strip() if title_m else sid,
        raw_md=md,
        source_path=str(path),
    )


def _extract_radius_value(text: str) -> str | None:
    """Pull a concrete radius value from a soft-option default (e.g. `10px`, `0`, `0.5rem`,
    `pill`). Returns a CSS length or None when nothing usable is present."""
    t = text.strip().lower()
    if t in ("pill", "full", "999px"):
        return "999px"
    m = re.search(r"(\d+(?:\.\d+)?)\s*(px|rem)?", t)
    if not m:
        return None
    num = m.group(1)
    if float(num) == 0:
        return "0"
    return f"{num}{m.group(2) or 'px'}"


# ── brand slot extraction (brand.yaml tokens -> style slots) ─────────────────────

def _color_value(doc: dict, token: str | None) -> str | None:
    if not token:
        return None
    colors = (doc.get("tokens", {}) or {}).get("colors", {}) or {}
    c = colors.get(token)
    if isinstance(c, dict):
        return c.get("value")
    return token if str(token).startswith("#") else None


def _page_surface(doc: dict):
    """Resolve the brand's default PAGE surface (the 'paper' source).

    Prefers ``surface/primary``; otherwise the first declared surface. Returns
    (role, surface_dict)."""
    surfaces = (doc.get("tokens", {}) or {}).get("surfaces", {}) or {}
    if not surfaces:
        return None, {}
    if "surface/primary" in surfaces:
        return "surface/primary", surfaces["surface/primary"]
    role = next(iter(surfaces))
    return role, surfaces[role]


def brand_slots(doc: dict) -> dict:
    """Map brand.yaml tokens -> the style's named brand slots.

    paper  <- the default page surface bg (surface/primary bg).
    ink    <- that surface's primary text token value (text/on-primary).
    accent <- the brand's single accent (accent/* color), else ink (monochrome; we never
              invent a second accent).
    font-display <- tokens.type.display-hero.family.
    font-body    <- tokens.type.body.family (or control-text).
    font-mono    <- brand carries no mono -> documented neutral mono fallback.

    Each slot records ``*_from_brand`` so the renderer/gate know whether the value came
    from the brand or from the style's documented fallback.
    """
    out: dict = {}
    colors = (doc.get("tokens", {}) or {}).get("colors", {}) or {}
    types = (doc.get("tokens", {}) or {}).get("type", {}) or {}

    role, surf = _page_surface(doc)

    # paper
    paper = surf.get("bg") if surf else None
    out["paper"] = paper or SLOT_FALLBACKS["paper"]
    out["paper_from_brand"] = bool(paper)
    out["paper_role"] = role

    # ink
    ink = _color_value(doc, (surf or {}).get("textPrimary")) or _color_value(doc, "text/on-primary")
    out["ink"] = ink or SLOT_FALLBACKS["ink"]
    out["ink_from_brand"] = bool(ink)

    # accent (single, committed). Prefer an explicit accent/* token.
    accent_tok = next((k for k in colors if k.startswith("accent/")), None)
    accent = _color_value(doc, accent_tok)
    out["accent"] = accent or out["ink"]
    out["accent_from_brand"] = bool(accent)
    out["accent_token"] = accent_tok

    # fonts
    disp = (types.get("display-hero") or {}).get("family")
    body = (types.get("body") or {}).get("family") or (types.get("control-text") or {}).get("family")
    out["font_display"] = disp or SLOT_FALLBACKS["font_display"]
    out["font_display_from_brand"] = bool(disp)
    out["font_body"] = body or SLOT_FALLBACKS["font_body"]
    out["font_body_from_brand"] = bool(body)
    out["font_mono"] = SLOT_FALLBACKS["font_mono"]  # brand silent -> fallback
    out["font_mono_from_brand"] = False
    return out


# ── merge: STYLE structure + BRAND slot values -> render context ─────────────────

@dataclass
class RenderContext:
    """The merged STYLE+BRAND context handed to the renderer/gate."""
    active: bool
    style_id: str = ""
    slots: dict = field(default_factory=dict)
    structure: StyleStructure | None = None
    style: Style | None = None
    notes: list[str] = field(default_factory=list)

    # convenience accessors (brand slot values)
    @property
    def paper(self):
        return self.slots.get("paper")

    @property
    def ink(self):
        return self.slots.get("ink")

    @property
    def accent(self):
        return self.slots.get("accent")

    @property
    def font_display(self):
        return self.slots.get("font_display")

    @property
    def font_body(self):
        return self.slots.get("font_body")

    @property
    def font_mono(self):
        return self.slots.get("font_mono")

    @property
    def off_grid_expansion(self) -> bool:
        """The active style's off-grid EXPANSION capability flag (see Style.off_grid_expansion).
        Inactive context (no style) -> False (no expansion)."""
        return bool(self.style.off_grid_expansion) if self.style else False


def merge(style: Style, doc: dict) -> RenderContext:
    """Layer BRAND on top of STYLE per the precedence rules.

    The style supplies STRUCTURE + DEFAULTS as the base; the brand layers on top and wins
    on any value it explicitly sets. The named brand SLOTS are filled from brand.yaml token
    values; where the brand is silent on a slot, the style's documented fallback is used.
    The style's core rules (``style_rules``) ride along as brand-overridable defaults and
    are reported downstream by the on-brand gate (which blesses documented brand overrides
    such as the hero #sec-0 exception rather than failing on them); only the brand's OWN
    ``neverDo`` rules are hard.
    """
    slots = brand_slots(doc)
    notes: list[str] = []
    for k in ("paper", "ink", "accent", "font_display", "font_body", "font_mono"):
        if not slots.get(f"{k}_from_brand"):
            notes.append(f"slot '{k}' silent in brand -> style fallback '{slots.get(k)}'")
    if not slots.get("accent_from_brand"):
        notes.append("brand carries no accent token -> accent falls back to ink "
                     "(monochrome; never invents a second accent)")

    # ── Soft-option merge: when the brand documents a soft-option choice, patch the merged
    # structure so the composer renders the brand's committed value (not the style default).
    # Copy the structure first so we never mutate the shared Style.structure (the gate loads
    # the style separately and must keep seeing the un-merged style default).
    from copy import deepcopy
    structure = deepcopy(style.structure)
    # radius: the brand's `tokens.spacing.radius-global` VALUE wins over the style's
    # soft-radius default (fixes the editorial-luxury soft-radius gap AND keeps a no-radius
    # brand's sharp corners). Only patched when the brand actually declares the token.
    radius_global = ((doc.get("tokens", {}) or {}).get("spacing", {}) or {}).get("radius-global")
    brand_radius = radius_global.get("value") if isinstance(radius_global, dict) else None
    if brand_radius is not None:
        notes.append(f"soft-option 'radius': brand radius-global '{brand_radius}' overrides "
                     f"style default '{style.structure.radius}'")
        structure.radius = str(brand_radius).strip()

    return RenderContext(
        active=True,
        style_id=style.id,
        slots=slots,
        structure=structure,   # STYLE owns structure; brand patches only documented soft options
        style=style,
        notes=notes,
    )


def load_and_merge(style_id: str, doc: dict, styles_dir: Path | None = None) -> RenderContext:
    return merge(load_style(style_id, styles_dir), doc)


def inactive_context() -> RenderContext:
    """No style selected -> current behavior preserved."""
    return RenderContext(active=False)


if __name__ == "__main__":
    import argparse
    import json

    ap = argparse.ArgumentParser(description="inspect a merged STYLE+BRAND context")
    ap.add_argument("style_id")
    ap.add_argument("brand_yaml", type=Path)
    args = ap.parse_args()
    doc = yaml.safe_load(args.brand_yaml.read_text())
    ctx = load_and_merge(args.style_id, doc)
    print(json.dumps({
        "style_id": ctx.style_id,
        "slots": {k: v for k, v in ctx.slots.items()},
        "structure": ctx.structure.__dict__,
        "display_size_css": ctx.structure.display_size_css(),
        "style_rules": ctx.style.style_rules,
        "invariants": ctx.style.invariants,
        "soft_options": ctx.style.soft_options,
        "offGridExpansion": ctx.off_grid_expansion,
        "notes": ctx.notes,
    }, indent=2))
