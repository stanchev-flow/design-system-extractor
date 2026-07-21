#!/usr/bin/env python3
"""token_families.py — brand-agnostic, CSS-VARIABLE-FIRST extraction of the SPACING,
RADIUS and COLOR token families (the sibling of ``type_scale.py``).

WHY THIS EXISTS (same root-cause as the collapsed type-scale):
    A single measured instance is never authoritative for a token ladder. The type
    scale proved that design systems declare their scales in CSS CUSTOM PROPERTIES and
    that reading those tokens (with ``var()`` alias/calc/rem resolution, ``@media``
    variants, and consuming-selector binding) reproduces the true, protected scale from
    the vars alone. This module generalizes that machinery to the remaining families.

WHAT THIS DOES (systemic, brand-agnostic — it drives off "a custom property consumed as
<property> by a role selector", never off vendor var names):

  RADIUS  collects every ``--*radius*`` (and ``--*border-width*``) custom property,
          resolves it to px, binds it to a control/card/input/pill role via the
          selectors that consume it as ``border-radius`` (or by its own name suffix), and
          emits a canonical radius scale. Falls back to clustering the computed
          ``border-radius`` census (css-facts) across the whole corpus.

  SPACING reads the source's DECLARED rhythm/padding tokens (section vertical rhythm,
          content padding, control padding) as css-var scales, and clusters the DECLARED
          gap/padding LITERALS across the full stylesheet corpus into a generic step
          ladder where no single named scale token exists (the improved
          computed-cluster fallback — corpus-wide, never a single instance).

  COLOR   collects every custom property that RESOLVES to a color literal (chasing
          ``var()`` alias chains THEME-AWARE — the default/light theme wins over a later
          ``[data-theme=dark]``/``.-dark`` redefinition), binds each token to a generic
          role group (surface / text / border / icon / accent) via the paint property
          that consumes it, and emits canonical generic color roles
          (background / surface / surfaceInverse / text / textMuted / textOnInverse /
          border / borderStrong / borderBrand / accent / accentHover / accentText) plus
          the full palette and the measured section band surfaces (so a decorative
          module band surface is captured as a generic pattern, not a section-specific
          variable). Falls back to clustering measured colors when no color tokens exist.

Each emitted token carries provenance ``{source: css-var, sourceVariable, confirmedBy}``
or ``{source: computed-cluster, confirmedBy}``. This tool is READ-ONLY over the evidence;
it writes only ``spacing-scale.json`` / ``radius-scale.json`` / ``color-roles.json``. It
does not author brand.yaml and does not touch the harness.

Usage:
    ./venv/bin/python tools/extract/token_families.py \
        --evidence runs/<brand>/brand/evidence/ [--family all|spacing|radius|color]
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path

# ── reuse the proven type_scale machinery (var collection / alias+rem resolution /
#    @media evaluation / selector parsing) so the two readers stay in lock-step ──────
_TS_PATH = Path(__file__).resolve().parent / "type_scale.py"
_spec = importlib.util.spec_from_file_location("type_scale_shared", _TS_PATH)
ts = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ts)

_custom_prop_defs = ts._custom_prop_defs
resolve_alias = ts.resolve_alias
value_at = ts.value_at
media_applies = ts.media_applies
_to_px = ts._to_px
_rem_of = ts._rem_of
_split_list = ts._split_list
_key_compound = ts._key_compound
_VAR_RE = ts._VAR_RE
TIER_VIEWPORTS = ts.TIER_VIEWPORTS
CANONICAL_TIER = ts.CANONICAL_TIER
ROOT_PX = ts.ROOT_PX

SPACING_SCHEMA = "spacing-scale.v1"
RADIUS_SCHEMA = "radius-scale.v1"
COLOR_SCHEMA = "color-roles.v1"


# ── generic, brand-agnostic selector-context classification ─────────────────────────

_CTX_PATTERNS = {
    "button": re.compile(r"button|\bbtn(\b|-)|\bcta\b", re.I),
    "input": re.compile(r"\binput\b|\bfield\b|\bselect\b|textarea|form-control|search", re.I),
    "card": re.compile(r"\bcard\b|\bpanel\b|\btile\b|container|\bbox\b", re.I),
    "badge": re.compile(r"\bbadge\b|\btag\b|\bchip\b|\bpill\b|\blabel\b", re.I),
    "section": re.compile(r"section|\bband\b|\bhero\b|wrapper|module|-block", re.I),
    "nav": re.compile(r"\bnav\b|header|\bmenu\b", re.I),
    "footer": re.compile(r"footer", re.I),
    "heading": re.compile(r"heading|title|\bh[1-6]\b|\.h[1-6]\b", re.I),
    "divider": re.compile(r"divider|separator|\bhr\b|rule", re.I),
}


def _selector_contexts(selector: str) -> set[str]:
    out = set()
    for name, pat in _CTX_PATTERNS.items():
        if pat.search(selector or ""):
            out.add(name)
    return out


def _selector_key_contexts(selector: str) -> set[str]:
    """Role contexts detected on the KEY COMPOUND (the styled element itself) of each
    selector-list part — the strict binding that ignores a descendant/ancestor role
    leaking in from a compound selector (``.cl-card .cl-badge`` binds to badge, not card).
    Mirrors type_scale's key-compound heading binding that fixed the collapsed scale."""
    out = set()
    for part in _split_list(selector or ""):
        out |= _selector_contexts(_key_compound(part))
    return out


# role → the keyword tails that mark a class as THAT component's own name. A class is a
# component-name match only when a class/element token ENDS with the keyword
# (``cl-card`` → card; but ``global-nav-card-cta-text-link`` → text-link, NOT card), so a
# role word buried mid-name in an unrelated component never mis-binds.
_COMPONENT_TAILS = {
    "button": ("button", "btn", "cta"),
    "card": ("card", "panel", "tile"),
    "input": ("input", "field", "select", "textarea"),
    "badge": ("badge", "tag", "chip", "pill"),
    "section": ("section", "band", "hero"),
    "nav": ("nav", "navbar", "header", "menu"),
    "footer": ("footer",),
    "heading": ("heading", "title", "h1", "h2", "h3", "h4", "h5", "h6"),
    "divider": ("divider", "separator", "hr", "rule"),
}
_CLASS_TOKEN_RE = re.compile(r"[.]?(-?[A-Za-z][\w-]*)")


def _selector_component_contexts(selector: str) -> set[str]:
    """Role contexts where the KEY COMPOUND carries a class/element that IS that
    component's own name (a class token ending in the role keyword). This is the
    strongest, still-brand-agnostic binding for a component surface (card / button /
    input / badge), used to pick control/card/input radius over incidental matches."""
    out = set()
    for part in _split_list(selector or ""):
        kc = _key_compound(part).lower()
        tokens = _CLASS_TOKEN_RE.findall(kc)
        for role, tails in _COMPONENT_TAILS.items():
            for tok in tokens:
                segs = tok.split("-")
                if tok in tails or (segs and segs[-1] in tails):
                    out.add(role)
                    break
    return out


def find_prop_consumers(rules: list[dict], prop_names: tuple[str, ...]) -> dict[str, list[dict]]:
    """{var: [{selector, media, prop, contexts}]} for every rule that sets one of
    ``prop_names`` to ``var(--…)``. Brand-agnostic: bound by the PROPERTY consumed and
    the consuming selector's role context, never by the var name."""
    out: dict[str, list[dict]] = {}
    prop_alt = "|".join(re.escape(p) for p in prop_names)
    use_re = re.compile(r"(" + prop_alt + r")\s*:\s*[^;]*?var\(\s*(--[\w-]+)")
    for r in rules:
        if r.get("kind") == "keyframes":
            continue
        sel = r.get("selector", "")
        for m in use_re.finditer(r.get("decls", "")):
            prop, var = m.group(1).lower(), m.group(2)
            out.setdefault(var, []).append({
                "selector": sel[:200], "media": r.get("media", "") or "",
                "prop": prop, "contexts": sorted(_selector_contexts(sel)),
                "keyContexts": sorted(_selector_key_contexts(sel)),
                "componentContexts": sorted(_selector_component_contexts(sel))})
    return out


def _var_suffix(var: str, marker: str) -> str:
    """The role id encoded after a family marker in a token name, brand-agnostic:
    ``--cl-border-radius-small`` + ``radius`` -> ``small``. A token that IS the bare
    family base (marker at the tail, no suffix) reads as ``base``."""
    m = re.search(marker + r"-?(.*)$", var)
    suffix = (m.group(1) if m else var).strip("-")
    return suffix or "base"


# ══════════════════════════════════════════════════════════════════════════════════
# RADIUS
# ══════════════════════════════════════════════════════════════════════════════════

def extract_radius(evidence_dir: Path) -> dict:
    css_doc = json.loads((evidence_dir / "css-rules.json").read_text())
    rules = css_doc.get("rules", [])
    facts_path = evidence_dir / "css-facts.json"
    facts = json.loads(facts_path.read_text()) if facts_path.is_file() else {}

    radius_pool = _custom_prop_defs(rules, "radius")
    width_pool = _custom_prop_defs(rules, "border-width")
    consumers = find_prop_consumers(rules, ("border-radius",))
    width_consumers = find_prop_consumers(rules, ("border-width", "border"))

    method = "css-var"
    tokens: list[dict] = []
    if radius_pool:
        for var in radius_pool:
            raw = value_at(radius_pool[var], radius_pool, CANONICAL_TIER, ROOT_PX)
            px = _px_or_special(raw)
            uses = consumers.get(var, [])
            ctxs = sorted({c for u in uses for c in u["contexts"]})
            key_ctxs = sorted({c for u in uses for c in u["keyContexts"]})
            comp_ctxs = sorted({c for u in uses for c in u["componentContexts"]})
            tokens.append({
                "token": var, "role": _var_suffix(var, "radius"),
                "px": px, "raw": raw,
                "usedByContexts": ctxs, "usedByKeyContexts": key_ctxs,
                "usedByComponentContexts": comp_ctxs,
                "consumerCount": len(uses),
                "consumers": [u["selector"] for u in uses[:6]],
                "provenance": {"source": "css-var", "sourceVariable": var,
                               "confirmedBy": ["computed"] if uses else []},
            })
        tokens.sort(key=lambda t: (t["px"] if isinstance(t["px"], (int, float)) else 1e9))
    else:
        method = "computed-cluster"
        tokens = _radius_from_census(facts)

    widths: list[dict] = []
    for var in width_pool:
        raw = value_at(width_pool[var], width_pool, CANONICAL_TIER, ROOT_PX)
        px = _to_px(raw, ROOT_PX) if raw else None
        uses = width_consumers.get(var, [])
        widths.append({
            "token": var, "role": _var_suffix(var, "border-width"),
            "px": px, "raw": raw, "consumerCount": len(uses),
            "provenance": {"source": "css-var", "sourceVariable": var,
                           "confirmedBy": ["computed"] if uses else []},
        })
    widths.sort(key=lambda t: (t["px"] or 0))

    roles = _radius_roles(tokens) if method == "css-var" else _radius_roles(tokens)
    unused = [t["token"] for t in tokens if t.get("consumerCount", 0) == 0 and t["token"]]
    return {
        "schemaVersion": RADIUS_SCHEMA, "method": method,
        "canonicalTier": CANONICAL_TIER,
        "radiusTokenCount": len(radius_pool),
        "tokens": tokens, "borderWidths": widths,
        "canonicalRoles": roles, "definedButUnused": unused,
        "census": facts.get("radiusCensus", {}),
    }


def _px_or_special(raw: str | None):
    """Radius px, keeping the pill sentinel (9999px / 50% / 100%) recognisable."""
    if raw is None:
        return None
    v = str(raw).strip().lower()
    if v in ("50%", "100%") or v.endswith("%"):
        return v
    px = _to_px(v, ROOT_PX)
    return px


def _is_pill(px) -> bool:
    if isinstance(px, str):
        return px.endswith("%")
    return isinstance(px, (int, float)) and px >= 999


def _radius_roles(tokens: list[dict]) -> dict:
    """Map the raw radius tokens onto canonical generic roles (control / input / card /
    pill / small / medium / large). Selection is by consuming CONTEXT first, then by the
    token's own name suffix, then by magnitude."""
    def numeric(t):
        return t["px"] if isinstance(t["px"], (int, float)) else None

    def by_context(ctx):
        # binding strength: a class that IS the component's own name (componentContexts)
        # beats any key-compound match, which beats a loose whole-selector match — so
        # ``.cl-card`` wins the card radius over ``.global-nav-card-cta-text-link``.
        def pool(field):
            return [t for t in tokens if ctx in t.get(field, [])
                    and numeric(t) is not None and not _is_pill(t["px"])]
        cands = (pool("usedByComponentContexts") or pool("usedByKeyContexts")
                 or pool("usedByContexts"))
        return max(cands, key=lambda t: t["consumerCount"]) if cands else None

    def by_name(*names):
        for n in names:
            cands = [t for t in tokens if t["role"] == n and numeric(t) is not None]
            if cands:
                return max(cands, key=lambda t: t["consumerCount"])
        return None

    out: dict[str, dict] = {}
    control = by_context("button") or by_name("medium")
    if control:
        out["control"] = control
    inp = by_context("input") or by_name("input")
    if inp:
        out["input"] = inp
    card = by_context("card") or by_name("container", "container-medium", "large")
    if card:
        out["card"] = card
    pill = next((t for t in tokens if _is_pill(t["px"])), None) or by_name("round", "pill", "full")
    if pill:
        out["pill"] = pill
    for name in ("small", "medium", "large"):
        t = by_name(name)
        if t:
            out[name] = t
    return out


def _radius_from_census(facts: dict) -> list[dict]:
    """Fallback: cluster the DECLARED ``border-radius`` literals (css-facts census,
    corpus-wide) into descending radius tokens. Never a single instance."""
    census = facts.get("radiusCensus", {}) or {}
    seen: dict[float, int] = {}
    special: dict[str, int] = {}
    for raw, count in census.items():
        v = str(raw).strip().lower()
        if "var(" in v or " " in v:  # skip shorthands + var indirections in the fallback
            continue
        if v.endswith("%"):
            special[v] = special.get(v, 0) + count
            continue
        px = _to_px(v, ROOT_PX)
        if px is not None:
            seen[round(px, 1)] = seen.get(round(px, 1), 0) + count
    out = []
    for px in sorted(seen, reverse=True):
        out.append({
            "token": None, "role": f"cluster-{px}", "px": px, "raw": f"{px}px",
            "usedByContexts": [], "consumerCount": seen[px],
            "consumers": [],
            "provenance": {"source": "computed-cluster", "confirmedBy": ["computed"]},
        })
    for v, count in sorted(special.items(), key=lambda kv: -kv[1]):
        out.append({
            "token": None, "role": "pill", "px": v, "raw": v,
            "usedByContexts": [], "consumerCount": count, "consumers": [],
            "provenance": {"source": "computed-cluster", "confirmedBy": ["computed"]},
        })
    return out


# ══════════════════════════════════════════════════════════════════════════════════
# SPACING
# ══════════════════════════════════════════════════════════════════════════════════

_LEN_LITERAL_RE = re.compile(r"^-?\d*\.?\d+(rem|em|px)$")


def extract_spacing(evidence_dir: Path) -> dict:
    css_doc = json.loads((evidence_dir / "css-rules.json").read_text())
    rules = css_doc.get("rules", [])

    pad_pool = _custom_prop_defs(rules, "padding")
    gap_pool = _custom_prop_defs(rules, "gap")
    space_pool = _custom_prop_defs(rules, "space")  # --*space* / --*spacing*
    pool_all = {**pad_pool, **gap_pool, **space_pool}

    pad_consumers = find_prop_consumers(rules, ("padding", "padding-top", "padding-bottom",
                                               "padding-block", "padding-inline"))
    gap_consumers = find_prop_consumers(rules, ("gap", "row-gap", "column-gap"))

    # SECTION VERTICAL RHYTHM: padding tokens whose name marks a section/band vertical
    # step (top/bottom), collected as a css-var scale of distinct px steps.
    section_rhythm = _spacing_named_steps(
        pool_all, lambda v: bool(re.search(r"section.*padding|padding.*(top|bottom)", v))
        and "content" not in v and "button" not in v and "carousel" not in v)

    # CONTENT PADDING: the inner content inset scale.
    content_padding = _spacing_named_steps(
        pool_all, lambda v: "content-padding" in v)

    # CONTROL PADDING: padding tokens consumed by a button/control context (or named so).
    control_padding = _control_padding(pool_all, pad_consumers)

    # GENERIC STEP LADDER: cluster the DECLARED gap/padding LITERALS across the whole
    # corpus into a rem-based step scale (the improved computed-cluster fallback — no
    # single named spacing scale token exists in most systems).
    step_scale = _spacing_step_ladder(rules)

    # NAMED GAPS: gap tokens with a clear column/row gutter role.
    named_gaps = _named_gaps(gap_pool, gap_consumers)

    unused = [v for v in pool_all
              if not (pad_consumers.get(v) or gap_consumers.get(v))]
    return {
        "schemaVersion": SPACING_SCHEMA,
        "method": "css-var+computed-cluster",
        "canonicalTier": CANONICAL_TIER,
        "paddingTokenCount": len(pad_pool),
        "gapTokenCount": len(gap_pool),
        "sectionRhythm": section_rhythm,
        "contentPadding": content_padding,
        "controlPadding": control_padding,
        "namedGaps": named_gaps,
        "stepScale": step_scale,
        "definedButUnused": unused[:40],
    }


def _spacing_named_steps(pool: dict, name_pred) -> dict:
    """Distinct px steps declared by the tokens whose name matches ``name_pred``,
    labelled none/xs/s/md/lg/xl by ascending magnitude — a css-var rhythm scale."""
    values: dict[float, list[str]] = {}
    for var, defs in pool.items():
        if not name_pred(var.lower()):
            continue
        for d in defs:
            raw = resolve_alias(d["value"], pool, CANONICAL_TIER, ROOT_PX)
            px = _to_px(raw, ROOT_PX) if raw else None
            if px is None and raw is not None and str(raw).strip() in ("0", "0px"):
                px = 0.0
            if px is not None:
                values.setdefault(round(px, 1), []).append(var)
    steps = sorted(values)
    labels = _rhythm_labels(len(steps))
    out = {}
    for label, px in zip(labels, steps):
        out[label] = {
            "px": px, "rem": _rem_of(px, ROOT_PX),
            "tokens": sorted(set(values[px]))[:4],
            "provenance": {"source": "css-var", "confirmedBy": ["computed"]},
        }
    return out


def _rhythm_labels(n: int) -> list[str]:
    base = ["none", "xs", "s", "md", "lg", "xl", "2xl", "3xl", "4xl"]
    if n <= len(base):
        return base[:n]
    return [f"step-{i}" for i in range(n)]


_CONTROL_PAD_RE = re.compile(r"(button|card)[\w-]*padding|padding[\w-]*(button|card)", re.I)


def _control_padding(pool: dict, pad_consumers: dict) -> dict:
    """Control padding scale: the button/card padding tokens (named ``*button*padding*``
    / ``*card*padding*``), keyed by their size suffix (small/medium/large/base/card).
    Restricted to the primary control families so incidental carousel-control / nav
    close-button padding tokens do not pollute the scale."""
    out = {}
    for var, defs in pool.items():
        low = var.lower()
        if not _CONTROL_PAD_RE.search(low):
            continue
        raw = value_at(defs, pool, CANONICAL_TIER, ROOT_PX)
        if raw is None or "var(" in str(raw):
            continue
        family = "card" if "card" in low else "button"
        size = None
        for s in ("small", "medium", "large", "x-large", "xlarge"):
            if s in low:
                size = s
                break
        key = f"{family}-{size}" if size else (family if family == "card" else "button-base")
        uses = pad_consumers.get(var, [])
        parts = str(raw).split()
        block = _to_px(parts[0], ROOT_PX) if parts else None
        inline = _to_px(parts[1], ROOT_PX) if len(parts) > 1 else block
        out[key] = {
            "raw": str(raw).strip(), "blockPx": block, "inlinePx": inline,
            "token": var, "consumerCount": len(uses),
            "provenance": {"source": "css-var", "sourceVariable": var,
                           "confirmedBy": ["computed"] if uses else []},
        }
    return out


def _named_gaps(gap_pool: dict, gap_consumers: dict) -> dict:
    out = {}
    for var, defs in gap_pool.items():
        raw = value_at(defs, gap_pool, CANONICAL_TIER, ROOT_PX)
        px = _to_px(raw, ROOT_PX) if raw and "var(" not in str(raw) else None
        uses = gap_consumers.get(var, [])
        if px is None:
            continue
        out[_var_suffix(var.lower(), "gap") or var] = {
            "px": px, "rem": _rem_of(px, ROOT_PX), "token": var,
            "usedByContexts": sorted({c for u in uses for c in u["contexts"]}),
            "consumerCount": len(uses),
            "provenance": {"source": "css-var", "sourceVariable": var,
                           "confirmedBy": ["computed"] if uses else []},
        }
    return out


def _spacing_step_ladder(rules: list[dict]) -> list[dict]:
    """Cluster the DECLARED ``gap`` / axis ``padding`` LITERAL lengths across the whole
    stylesheet corpus into an ascending step ladder. Corpus-wide (never a single
    instance); emitted with ``provenance.source = computed-cluster``."""
    counts: dict[float, int] = {}
    prop_re = re.compile(
        r"(?:^|;)\s*(gap|row-gap|column-gap|padding-top|padding-bottom|padding-block|"
        r"padding-inline|margin-top|margin-bottom)\s*:\s*([^;]+)")
    for r in rules:
        if r.get("kind") == "keyframes":
            continue
        for m in prop_re.finditer(r.get("decls", "")):
            for tok in m.group(2).strip().split():
                tok = tok.strip().lower()
                if not _LEN_LITERAL_RE.match(tok):
                    continue
                px = _to_px(tok, ROOT_PX)
                if px is not None and px > 0:
                    counts[round(px, 1)] = counts.get(round(px, 1), 0) + 1
    ladder = []
    for px in sorted(counts):
        ladder.append({
            "px": px, "rem": _rem_of(px, ROOT_PX), "count": counts[px],
            "provenance": {"source": "computed-cluster", "confirmedBy": ["computed"]},
        })
    return ladder


# ══════════════════════════════════════════════════════════════════════════════════
# COLOR
# ══════════════════════════════════════════════════════════════════════════════════

_COLOR_LIT_RE = re.compile(
    r"^\s*(#[0-9a-fA-F]{3,8}|rgba?\([^)]*\)|hsla?\([^)]*\))\s*$")
_DARK_SCOPE_RE = re.compile(
    r"theme=dark|\bdata-background=dark\b|(?:^|[ .])-?dark\b|\.-dark\b|\bnight\b", re.I)
_INVERSE_HINT_RE = re.compile(r"inverse|on-color|on-dark|footer", re.I)

_PAINT_PROPS = ("color", "background-color", "background", "border-color", "border",
                "border-top-color", "border-bottom-color", "outline-color",
                "fill", "stroke")


def _is_dark_scope(selector: str) -> bool:
    return bool(_DARK_SCOPE_RE.search(selector or ""))


def _color_value_at(defs: list[dict], pool: dict, vp: int, root_px: float,
                    seen: frozenset = frozenset()):
    """THEME-AWARE used value: among the definitions that apply at ``vp``, the
    default/light-scoped ones win over a later ``[data-theme=dark]``/``.-dark``
    redefinition; within the winning theme the LAST source-order def wins (cascade)."""
    applic = [d for d in defs if media_applies(d["media"], vp)]
    if not applic:
        return None
    light = [d for d in applic if not _is_dark_scope(d["selector"])]
    cand = light or applic
    chosen = sorted(cand, key=lambda d: d["order"])[-1]["value"]
    return _resolve_color(chosen, pool, vp, root_px, seen)


def _resolve_color(value, pool: dict, vp: int, root_px: float,
                   seen: frozenset = frozenset()):
    if value is None:
        return None
    val = str(value).strip()
    m = _VAR_RE.match(val)
    if not m:
        return val
    ref, fallback = m.group(1), m.group(2)
    if ref in seen:
        return fallback.strip() if fallback else None
    if ref in pool:
        r = _color_value_at(pool[ref], pool, vp, root_px, seen | {ref})
        if r is not None:
            return r
    if fallback:
        return _resolve_color(fallback.strip(), pool, vp, root_px, seen | {ref})
    return None


def _is_color_literal(value) -> bool:
    return value is not None and bool(_COLOR_LIT_RE.match(str(value)))


def _rgb_tuple(value: str):
    v = str(value).strip().lower()
    m = re.match(r"#([0-9a-f]{3})$", v)
    if m:
        h = m.group(1)
        return tuple(int(c * 2, 16) for c in h) + (1.0,)
    m = re.match(r"#([0-9a-f]{6})$", v)
    if m:
        h = m.group(1)
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 1.0)
    m = re.match(r"#([0-9a-f]{8})$", v)
    if m:
        h = m.group(1)
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), int(h[6:8], 16) / 255)
    m = re.match(r"rgba?\(\s*([\d.]+)[ ,]+([\d.]+)[ ,]+([\d.]+)(?:[ ,/]+([\d.]+))?\s*\)$", v)
    if m:
        a = float(m.group(4)) if m.group(4) is not None else 1.0
        return (float(m.group(1)), float(m.group(2)), float(m.group(3)), a)
    return None


def _luminance(value: str):
    t = _rgb_tuple(value)
    if not t:
        return None
    r, g, b, _a = t
    return round(0.2126 * r + 0.7152 * g + 0.0722 * b, 2)


def _alpha(value: str):
    t = _rgb_tuple(value)
    return t[3] if t else None


def _saturation(value: str):
    t = _rgb_tuple(value)
    if not t:
        return None
    r, g, b, _a = t
    mx, mn = max(r, g, b), min(r, g, b)
    if mx == 0:
        return 0.0
    return round((mx - mn) / mx, 3)


def _paint_group(prop: str) -> str:
    if prop == "color":
        return "text"
    if prop in ("background", "background-color"):
        return "surface"
    if "border" in prop or prop == "outline-color":
        return "border"
    if prop in ("fill", "stroke"):
        return "icon"
    return "other"


def extract_color(evidence_dir: Path) -> dict:
    css_doc = json.loads((evidence_dir / "css-rules.json").read_text())
    rules = css_doc.get("rules", [])
    computed_path = evidence_dir / "computed-styles.json"
    computed = json.loads(computed_path.read_text()) if computed_path.is_file() else {}
    joined_path = evidence_dir / "joined-evidence.json"
    joined = json.loads(joined_path.read_text()) if joined_path.is_file() else {}

    pool = _custom_prop_defs(rules, "")  # ALL custom properties (alias chains)
    paint_consumers = find_prop_consumers(rules, _PAINT_PROPS)
    # tokens referenced by OTHER custom properties (indirect usage, e.g. component tokens)
    referenced = _referenced_tokens(pool)

    method = "css-var"
    tokens: list[dict] = []
    for var, defs in pool.items():
        resolved = _color_value_at(defs, pool, CANONICAL_TIER, ROOT_PX)
        if not _is_color_literal(resolved):
            continue
        uses = paint_consumers.get(var, [])
        groups = sorted({_paint_group(u["prop"]) for u in uses})
        ctxs = sorted({c for u in uses for c in u["contexts"]})
        ref_count = referenced.get(var, 0)
        tokens.append({
            "token": var, "role": _var_suffix(var, "color"),
            "value": str(resolved).strip(),
            "luminance": _luminance(resolved), "alpha": _alpha(resolved),
            "saturation": _saturation(resolved),
            "paintGroups": groups, "usedByContexts": ctxs,
            "consumerCount": len(uses), "referencedByTokens": ref_count,
            "consumers": [u["selector"] for u in uses[:6]],
            "provenance": {
                "source": "css-var", "sourceVariable": var,
                "confirmedBy": ["computed"] if (uses or ref_count) else []},
        })

    if not tokens:
        method = "computed-cluster"
        tokens = _color_from_computed(computed, joined)

    roles = _color_roles(tokens) if method == "css-var" else {}
    band_surfaces = _band_surfaces(joined, computed)
    confirm = _confirm_colors(roles, computed, joined)
    unused = [t["token"] for t in tokens
              if t.get("consumerCount", 0) == 0 and t.get("referencedByTokens", 0) == 0
              and t["token"]]
    return {
        "schemaVersion": COLOR_SCHEMA, "method": method,
        "canonicalTier": CANONICAL_TIER,
        "colorTokenCount": len(tokens),
        "tokens": tokens,
        "canonicalRoles": roles,
        "bandSurfaces": band_surfaces,
        "definedButUnused": unused,
        "confirmation": confirm,
    }


def _referenced_tokens(pool: dict) -> dict[str, int]:
    counts: dict[str, int] = {}
    for defs in pool.values():
        for d in defs:
            for m in _VAR_RE.finditer(d["value"]):
                counts[m.group(1)] = counts.get(m.group(1), 0) + 1
    return counts


def _color_roles(tokens: list[dict]) -> dict:
    """Map the color palette onto canonical GENERIC roles (background / surface /
    surfaceMuted / surfaceInverse / text / textMuted / textOnInverse / border /
    borderStrong / borderBrand / accent / accentHover / accentText). Selection drives off
    the paint group each token is CONSUMED as + its measured value (luminance / alpha /
    saturation) + generic name hints — never a section- or content-specific var name."""
    def opaque(t):
        return (t.get("alpha") or 1.0) >= 0.95

    surfaces = [t for t in tokens if "surface" in t["paintGroups"]]
    texts = [t for t in tokens if "text" in t["paintGroups"]]
    borders = [t for t in tokens if "border" in t["paintGroups"]]

    def name_has(t, *frags):
        low = t["token"].lower()
        return any(f in low for f in frags)

    def top(cands, key):
        return max(cands, key=key) if cands else None

    out: dict[str, dict] = {}

    # ACCENT — the saturated brand color (consumed as a fill/background OR named
    # brand/accent/primary-fill), the highest-chroma non-neutral. Resolved first so it can
    # be excluded from the neutral surface/text picks.
    accent_cands = [t for t in tokens
                    if (t.get("saturation") or 0) >= 0.35 and opaque(t)
                    and (name_has(t, "brand", "accent", "primary-fill", "button-primary")
                         or "surface" in t["paintGroups"] or "border" in t["paintGroups"])]
    accent = top(accent_cands, lambda t: (name_has(t, "primary-fill", "brand"),
                                          t["consumerCount"] + t["referencedByTokens"]))
    if accent:
        out["accent"] = accent
        hover = top([t for t in tokens if name_has(t, "hover", "pressed")
                     and (t.get("saturation") or 0) >= 0.25 and opaque(t)],
                    lambda t: t["consumerCount"] + t["referencedByTokens"])
        if hover:
            out["accentHover"] = hover
    accent_txt = top([t for t in texts if name_has(t, "brand", "accent")],
                     lambda t: t["consumerCount"])
    if accent_txt:
        out["accentText"] = accent_txt

    accent_ids = {id(v) for v in out.values()}

    # SURFACES — neutrals (low saturation) painted as backgrounds.
    neutral_surfaces = [t for t in surfaces if (t.get("saturation") or 0) < 0.3
                        and id(t) not in accent_ids and t.get("luminance") is not None]
    light_surf = [t for t in neutral_surfaces if opaque(t) and t["luminance"] >= 128]
    dark_surf = [t for t in neutral_surfaces if opaque(t) and t["luminance"] < 128]
    # background = the lightest broadly-consumed page canvas (name background/canvas hint
    # wins ties); surface = the pure container (near-white / highest luminance).
    bg = top(light_surf, lambda t: (name_has(t, "background", "canvas", "page"),
                                    t["consumerCount"] + t["referencedByTokens"]))
    if bg:
        out["background"] = bg
    # surface = the pure container; prefer a semantic ``*color*container*`` token over an
    # equivalent component alias, then the highest-luminance / most-consumed.
    surface = top(light_surf, lambda t: (name_has(t, "container"),
                                         name_has(t, "surface", "card"),
                                         t["luminance"],
                                         t["consumerCount"] + t["referencedByTokens"]))
    if surface and (not bg or surface["token"] != bg["token"]):
        out["surface"] = surface
    bg_val = (bg or {}).get("value")
    surf_val = (surface or {}).get("value")
    muted = top([t for t in light_surf if t["value"] not in (bg_val, surf_val)],
                lambda t: (name_has(t, "background-02", "container-02", "muted", "subtle"),
                           t["consumerCount"]))
    if muted:
        out["surfaceMuted"] = muted
    inverse = top(dark_surf, lambda t: (name_has(t, "inverse", "footer"),
                                        -t["luminance"], t["consumerCount"]))
    if inverse:
        out["surfaceInverse"] = inverse

    # TEXT — default ink (darkest opaque), muted (alpha<1 or name secondary/02), on-inverse
    # (light ink or name on-color/inverse).
    dark_text = [t for t in texts if t.get("luminance") is not None and t["luminance"] < 128]
    light_text = [t for t in texts if t.get("luminance") is not None and t["luminance"] >= 160]
    ink = top([t for t in dark_text if opaque(t)],
              lambda t: (name_has(t, "text-01", "primary", "01"), t["consumerCount"], -t["luminance"]))
    if not ink:
        ink = top(dark_text, lambda t: t["consumerCount"])
    if ink:
        out["text"] = ink
    # muted ink is a NEUTRAL de-emphasised text (translucent black / grey) — a saturated
    # brand/hover ink is never the muted register, so exclude high-chroma candidates.
    tmuted = top([t for t in texts if id(t) != id(ink)
                  and (t.get("saturation") or 0) < 0.3
                  and ((t.get("alpha") or 1) < 0.95 or name_has(t, "secondary", "muted", "-02"))
                  and (t.get("luminance") or 255) < 170],
                 lambda t: (name_has(t, "secondary", "muted"), t["consumerCount"]))
    if tmuted:
        out["textMuted"] = tmuted
    on_inv = top([t for t in light_text if opaque(t) or name_has(t, "on-color", "inverse")],
                 lambda t: (name_has(t, "on-color", "inverse", "on-dark"), t["consumerCount"]))
    if on_inv:
        out["textOnInverse"] = on_inv

    # BORDERS — subtle (alpha<1 / low-contrast), strong (opaque neutral), brand (saturated).
    subtle = top([t for t in borders if (t.get("alpha") or 1) < 0.9
                  and (t.get("saturation") or 0) < 0.3],
                 lambda t: (name_has(t, "border", "divider", "hairline"), t["consumerCount"]))
    if subtle:
        out["border"] = subtle
    strong = top([t for t in borders if opaque(t) and (t.get("saturation") or 0) < 0.3
                  and id(t) != id(subtle)],
                 lambda t: (name_has(t, "border", "divider"), t["consumerCount"]))
    if strong:
        out["borderStrong"] = strong
    brand_border = top([t for t in borders if (t.get("saturation") or 0) >= 0.35],
                       lambda t: (name_has(t, "brand"), t["consumerCount"]))
    if brand_border:
        out["borderBrand"] = brand_border
    return out


def _band_surfaces(joined: dict, computed: dict) -> list[dict]:
    """Distinct MEASURED section band background colors across the full page (from the
    source's joined-evidence section ladder). This captures decorative/module band
    surfaces (which are NOT part of the semantic --*color* palette) as a GENERIC pattern
    keyed by the sections that use them — never a section-specific token name."""
    by_color: dict[str, list[str]] = {}
    for e in (joined.get("elements") or []):
        if e.get("kind") != "section":
            continue
        ladder = e.get("computedLadder") or {}
        rec = ladder.get(str(CANONICAL_TIER)) or {}
        bg = rec.get("backgroundColor") if isinstance(rec, dict) else None
        if bg:
            by_color.setdefault(_norm_color_key(bg), []).append(e.get("elementId"))
    out = []
    for color, sections in sorted(by_color.items(), key=lambda kv: -len(kv[1])):
        out.append({
            "value": color, "hex": _to_hex(color),
            "sections": sorted(sections), "count": len(sections),
            "luminance": _luminance(color), "saturation": _saturation(color),
            "provenance": {"source": "computed", "confirmedBy": ["computed"]},
        })
    return out


def _norm_color_key(value: str) -> str:
    t = _rgb_tuple(value)
    if not t:
        return str(value).strip().lower()
    r, g, b, a = t
    if a >= 0.999:
        return f"#{int(round(r)):02x}{int(round(g)):02x}{int(round(b)):02x}"
    return f"rgba({int(round(r))}, {int(round(g))}, {int(round(b))}, {round(a, 4)})"


def _to_hex(value: str):
    t = _rgb_tuple(value)
    if not t or t[3] < 0.999:
        return None
    r, g, b, _a = t
    return f"#{int(round(r)):02x}{int(round(g)):02x}{int(round(b)):02x}"


def _color_from_computed(computed: dict, joined: dict) -> list[dict]:
    """Fallback for systems with NO color custom properties: cluster measured colors
    (section backgrounds + heading/body ink) across the full DOM."""
    out = []
    seen = set()
    for b in _band_surfaces(joined, computed):
        key = b["value"]
        if key in seen:
            continue
        seen.add(key)
        out.append({
            "token": None, "role": f"band-{key}", "value": key,
            "luminance": b["luminance"], "alpha": _alpha(key),
            "saturation": b["saturation"], "paintGroups": ["surface"],
            "usedByContexts": ["section"], "consumerCount": b["count"],
            "referencedByTokens": 0, "consumers": [],
            "provenance": {"source": "computed-cluster", "confirmedBy": ["computed"]},
        })
    headings = computed.get("headings") or {}
    for tag, rec in headings.items():
        if isinstance(rec, dict) and rec.get("color"):
            key = _norm_color_key(rec["color"])
            if key in seen:
                continue
            seen.add(key)
            out.append({
                "token": None, "role": f"ink-{tag}", "value": key,
                "luminance": _luminance(key), "alpha": _alpha(key),
                "saturation": _saturation(key), "paintGroups": ["text"],
                "usedByContexts": ["heading"], "consumerCount": 1,
                "referencedByTokens": 0, "consumers": [],
                "provenance": {"source": "computed-cluster", "confirmedBy": ["computed"]},
            })
    return out


def _confirm_colors(roles: dict, computed: dict, joined: dict) -> dict:
    """Corroborate each canonical color role against a MEASURED instance where one
    exists (background = the most common section band; text = measured heading ink;
    accent = measured primary action fill). Flags conflicts like the type-scale did."""
    out: dict[str, dict] = {}
    bands = _band_surfaces(joined, computed)
    common_band = bands[0]["value"] if bands else None
    heading_ink = None
    for tag in ("h2", "h3", "h1", "p"):
        rec = (computed.get("headings") or {}).get(tag)
        if isinstance(rec, dict) and rec.get("color"):
            heading_ink = _norm_color_key(rec["color"])
            break
    measured = {"background": common_band, "surface": None, "text": heading_ink}
    for role, t in roles.items():
        m = measured.get(role)
        css = t.get("value")
        agrees = None
        if m and css:
            cm, cs = _rgb_tuple(m), _rgb_tuple(css)
            if cm and cs:
                agrees = all(abs(a - b) <= 8 for a, b in zip(cm[:3], cs[:3]))
        out[role] = {
            "cssVarValue": css, "measuredInstance": m, "agrees": agrees,
            "note": ("measured instance corroborates css-var" if agrees
                     else "measured instance differs" if agrees is False
                     else "no measured instance to corroborate"),
        }
    return out


# ── driver ─────────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--evidence", type=Path, required=True,
                    help="evidence dir with css-rules.json (+ css-facts / computed / joined)")
    ap.add_argument("--family", choices=("all", "spacing", "radius", "color"),
                    default="all")
    ap.add_argument("--out-dir", type=Path, default=None,
                    help="output dir (default = evidence dir)")
    return ap


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    ev = args.evidence
    if not (ev / "css-rules.json").is_file():
        raise SystemExit(f"token_families: {ev/'css-rules.json'} missing — run mine_css first")
    out_dir = args.out_dir or ev
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.family in ("all", "radius"):
        doc = extract_radius(ev)
        (out_dir / "radius-scale.json").write_text(json.dumps(doc, indent=1) + "\n")
        roles = doc["canonicalRoles"]
        print(f"[radius] method={doc['method']} tokens={doc['radiusTokenCount']} "
              f"roles={len(roles)} -> radius-scale.json")
        for r in ("control", "input", "card", "pill", "small", "medium", "large"):
            t = roles.get(r)
            if t:
                print(f"    {r:<8} {t['raw']:<8} ({t.get('token')})")

    if args.family in ("all", "spacing"):
        doc = extract_spacing(ev)
        (out_dir / "spacing-scale.json").write_text(json.dumps(doc, indent=1) + "\n")
        print(f"[spacing] section-rhythm={list(doc['sectionRhythm'])} "
              f"control={list(doc['controlPadding'])} "
              f"step-ladder={[s['px'] for s in doc['stepScale']]} -> spacing-scale.json")

    if args.family in ("all", "color"):
        doc = extract_color(ev)
        (out_dir / "color-roles.json").write_text(json.dumps(doc, indent=1) + "\n")
        roles = doc["canonicalRoles"]
        print(f"[color] method={doc['method']} tokens={doc['colorTokenCount']} "
              f"roles={len(roles)} bands={len(doc['bandSurfaces'])} -> color-roles.json")
        for r in ("background", "surface", "surfaceInverse", "text", "textMuted",
                  "textOnInverse", "border", "borderStrong", "borderBrand",
                  "accent", "accentHover"):
            t = roles.get(r)
            if t:
                print(f"    {r:<14} {t['value']:<28} ({t.get('token')})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
