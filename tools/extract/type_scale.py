#!/usr/bin/env python3
"""type_scale.py — brand-agnostic, CSS-VARIABLE-FIRST type-scale extraction.

WHY THIS EXISTS (root-cause of the collapsed-scale bug):
    The old type-scale evidence came from ``measure_computed``'s ``q(tag)`` probe —
    the FIRST ``h1``/``h2``/… in the DOM — then the authoring path stamped a single
    ``singleTierConfirmed`` size per tag. When the first ``h2`` in source order is a
    hero CTA control (18px) rather than a section heading (40px), the whole scale
    collapses (h2=18, h3=16). A single measured instance is never authoritative for a
    tier ladder.

WHAT THIS DOES INSTEAD (systemic, brand-agnostic):
    Design systems declare their type scale in CSS CUSTOM PROPERTIES
    (``--*font-size*`` and friends). Those tokens ARE the ground-truth ladder. This
    module:

      1. collects every ``--*font-size*`` custom property, its value(s) (rem+px), and
         responsive redefinitions (``@media`` overrides + ``-small`` sibling tokens),
         resolving ``var()`` alias chains;
      2. finds the SELECTORS that consume each token as ``font-size: var(--…)`` and
         infers the html role each token feeds (heading tag h1..h6, body/text, control/
         button, display, …) from the consuming selector's key compound + the token's
         own name suffix;
      3. resolves the matching ``--*line-height-<suffix>*`` / ``--*font-weight-<suffix>*``
         / ``--*font-family*`` tokens for each tier, and classifies serif vs sans;
      4. resolves the USED value per viewport tier (1920/1440/960/375) by evaluating
         each definition's ``@media`` condition — mobile-first bases with desktop
         ``min-width`` overrides resolve correctly;
      5. emits a canonical tier ladder (display / h1..h6 / body / small / micro, or the
         source's own tier names) with size, responsive variant, line-height, weight and
         family per tier, each carrying provenance ``{source: css-var, …}``.

    Where a brand declares NO font-size custom properties, it FALLS BACK to clustering
    the computed font-sizes of ALL heading elements across the full DOM (never a single
    instance). The fallback is emitted with ``provenance.source = "computed-cluster"``.

This tool is READ-ONLY over the evidence; it writes only ``type-scale.json``. It does
not author brand.yaml and does not touch the harness. The re-authoring step consumes
its output.

Usage:
    ./venv/bin/python tools/extract/type_scale.py \
        --evidence runs/<brand>/brand/evidence/ \
        [--out runs/<brand>/brand/evidence/type-scale.json]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SCHEMA = "type-scale.v1"

# the canonical measurement ladder (desktop-xl / desktop / tablet / mobile), matching
# measure_computed + join_evidence. The 1440 tier is the authored-canonical viewport.
TIER_VIEWPORTS = (1920, 1440, 960, 375)
CANONICAL_TIER = 1440
ROOT_PX = 16.0  # rem base; overridden if the capture declares html { font-size }

_HEADING_TAGS = ("h1", "h2", "h3", "h4", "h5", "h6")

# tokens whose NAME contains one of these fragments read as serif families even before
# a proxy is known (keeps family classification brand-agnostic — no HubSpot literals).
_SERIF_HINTS = ("serif", "playfair", "georgia", "didone", "times", "garamond", "cambria")


# ── value helpers ─────────────────────────────────────────────────────────────────

_VAR_RE = re.compile(r"var\(\s*(--[\w-]+)\s*(?:,\s*([^)]*))?\)")
_LEN_RE = re.compile(r"^(-?\d*\.?\d+)(rem|em|px)?$")


def _to_px(value: str, root_px: float = ROOT_PX) -> float | None:
    """A bare length token → px. rem/em resolve against the root size; unitless numbers
    are treated as px only when they look like a font size (>= 6)."""
    if value is None:
        return None
    v = str(value).strip().lower()
    m = _LEN_RE.match(v)
    if not m:
        return None
    num = float(m.group(1))
    unit = m.group(2)
    if unit in ("rem", "em"):
        return round(num * root_px, 3)
    if unit == "px":
        return round(num, 3)
    # unitless
    return round(num, 3) if num >= 6 else None


def _rem_of(px: float | None, root_px: float = ROOT_PX) -> float | None:
    if px is None:
        return None
    return round(px / root_px, 4)


# ── @media condition evaluation (min/max width, both classic + range syntax) ───────

_MIN_RE = re.compile(r"(?:min-width\s*:\s*|width\s*>=\s*)(\d*\.?\d+)px", re.I)
_MAX_RE = re.compile(r"(?:max-width\s*:\s*|width\s*<=\s*)(\d*\.?\d+)px", re.I)
_MIN_GT_RE = re.compile(r"width\s*>\s*(\d*\.?\d+)px", re.I)
_MAX_LT_RE = re.compile(r"width\s*<\s*(\d*\.?\d+)px", re.I)


def media_applies(media: str, viewport_px: int) -> bool:
    """Whether an ``@media`` condition string applies at ``viewport_px``. Empty media
    (base rule) always applies. Only width features are evaluated; a media query that
    also carries a non-width feature (print, hover, …) is treated conservatively as
    NOT applying to the viewport-width ladder."""
    if not media:
        return True
    m = media.lower()
    # non-width media features we cannot resolve on a width ladder
    if any(tok in m for tok in ("print", "hover", "pointer", "orientation",
                                "prefers-", "resolution", "aspect-ratio")):
        return False
    ok = True
    for rx, cmp in ((_MIN_RE, lambda b: viewport_px >= b),
                    (_MIN_GT_RE, lambda b: viewport_px > b),
                    (_MAX_RE, lambda b: viewport_px <= b),
                    (_MAX_LT_RE, lambda b: viewport_px < b)):
        for mm in rx.finditer(m):
            ok = ok and cmp(float(mm.group(1)))
    return ok


# ── custom-property collection ─────────────────────────────────────────────────────

def _custom_prop_defs(rules: list[dict], name_substr: str) -> dict[str, list[dict]]:
    """All definitions of custom properties whose NAME contains ``name_substr``.
    Returns {varName: [{value, media, selector, order}]} in source order."""
    pat = re.compile(r"(--[\w-]*" + re.escape(name_substr) + r"[\w-]*)\s*:\s*([^;]+)")
    out: dict[str, list[dict]] = {}
    order = 0
    for r in rules:
        if r.get("kind") == "keyframes":
            continue
        decls = r.get("decls", "")
        for m in pat.finditer(decls):
            var, val = m.group(1), m.group(2).strip()
            out.setdefault(var, []).append({
                "value": val, "media": r.get("media", "") or "",
                "selector": r.get("selector", ""), "order": order})
            order += 1
    return out


def resolve_alias(value: str, pool: dict[str, list[dict]], viewport_px: int,
                  root_px: float, _seen: frozenset = frozenset()) -> str | None:
    """Resolve a token value that may be ``var(--other[, fallback])`` down to a literal
    length, chasing alias chains within the same pool at the given viewport."""
    if value is None:
        return None
    val = value.strip()
    m = _VAR_RE.match(val)
    if not m:
        return val
    ref, fallback = m.group(1), m.group(2)
    if ref in _seen:
        return fallback.strip() if fallback else None
    if ref in pool:
        resolved = value_at(pool[ref], pool, viewport_px, root_px, _seen | {ref})
        if resolved is not None:
            return resolved
    if fallback:
        return resolve_alias(fallback.strip(), pool, viewport_px, root_px, _seen | {ref})
    return None


def value_at(defs: list[dict], pool: dict[str, list[dict]], viewport_px: int,
             root_px: float, _seen: frozenset = frozenset()) -> str | None:
    """The USED raw value of a custom property at ``viewport_px``: the LAST definition
    (source order) whose media condition applies (CSS cascade for equal-specificity
    :root custom props)."""
    chosen = None
    for d in sorted(defs, key=lambda x: x["order"]):
        if media_applies(d["media"], viewport_px):
            chosen = d["value"]
    if chosen is None:
        return None
    return resolve_alias(chosen, pool, viewport_px, root_px, _seen)


# ── consumer discovery + role inference ─────────────────────────────────────────────

_COMBINATOR_RE = re.compile(r"[ >+~]")


def _key_compound(selector: str) -> str:
    depth, last = 0, 0
    for i, ch in enumerate(selector):
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth = max(0, depth - 1)
        elif depth == 0 and ch in " >+~":
            last = i + 1
    return selector[last:].strip()


def _split_list(selector: str) -> list[str]:
    parts, buf, depth = [], [], 0
    for ch in selector:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth = max(0, depth - 1)
        if ch == "," and depth == 0:
            parts.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
    if buf:
        parts.append("".join(buf).strip())
    return [p for p in parts if p]


_TAG_RE = re.compile(r"^([a-zA-Z][\w-]*)")
# a utility class that IS a heading-level alias and nothing else: .h2 / .cl-h2 /
# .heading-h2 (NOT .-h2-on-mobile, .wf-page-header_heading.cl-h1.-custom-*, …).
_HEADING_UTIL_RE = re.compile(r"^(?:cl-|c-|wf-)?h([1-6])$")


def _selector_heading_tag(selector: str) -> str | None:
    """The heading tag (h1..h6) a selector list DEFINES A TIER FOR — only when a
    selector-list part's KEY COMPOUND is the *semantic tier selector*: a bare heading
    element (``h2``, ``h2:not(.x)``) or a sole heading-level utility class (``.h2``,
    ``.cl-h2``). Instance overrides that merely CONTAIN a heading token among other
    classes (``.wf-page-header_heading.cl-h1.-custom-font-size-65``,
    ``.foo.-h2-on-mobile``) are NOT tier definitions — matching their substrings was the
    original mis-binding that collapsed the scale."""
    for part in _split_list(selector):
        kc = _key_compound(part)
        # bare tag: h2 or h2 followed only by pseudos (no classes/attrs)
        tm = _TAG_RE.match(kc)
        tag = tm.group(1).lower() if tm else None
        if tag in _HEADING_TAGS:
            rest = kc[len(tm.group(1)):]
            if not re.search(r"[.\[#]", rest):  # no extra class/attr/id qualifiers
                return tag
        # sole utility class: .cl-h2 with no other class/attr on the compound
        classes = re.findall(r"\.(-?[\w-]+)", kc)
        others = re.search(r"[\[#]", kc) or (tag and tag not in _HEADING_TAGS)
        if len(classes) == 1 and not others and not tag:
            um = _HEADING_UTIL_RE.match(classes[0].lstrip("-"))
            if um:
                return f"h{um.group(1)}"
    return None


def _role_from_var_name(var: str) -> str:
    """The tier id encoded in a font-size token name (the suffix after ``font-size-``).
    Brand-agnostic: it just strips the vendor prefix + the ``font-size`` marker."""
    m = re.search(r"font-size-?(.*)$", var)
    suffix = (m.group(1) if m else var).strip("-")
    return suffix or var.lstrip("-")


def find_consumers(rules: list[dict]) -> dict[str, list[dict]]:
    """{fontSizeVar: [{selector, media, headingTag, isButton, isText}]} for every rule
    that sets ``font-size: var(--…)``."""
    out: dict[str, list[dict]] = {}
    use_re = re.compile(r"font-size\s*:\s*var\(\s*(--[\w-]+)")
    for r in rules:
        if r.get("kind") == "keyframes":
            continue
        for m in use_re.finditer(r.get("decls", "")):
            var = m.group(1)
            sel = r.get("selector", "")
            out.setdefault(var, []).append({
                "selector": sel[:200], "media": r.get("media", "") or "",
                "headingTag": _selector_heading_tag(sel),
                "isButton": bool(re.search(r"button|btn(\b|-)|cta", sel, re.I)),
                "isText": bool(re.search(r"\b(body|p|paragraph|text|rich-text)\b",
                                         sel, re.I)),
                "isBodyElement": _selector_is_body(sel),
            })
    return out


def _selector_is_body(selector: str) -> bool:
    """A selector-list part whose key compound is the bare ``body`` or ``p`` element —
    the default reading register (never a ``.body-copy`` component class)."""
    for part in _split_list(selector):
        kc = _key_compound(part)
        tm = _TAG_RE.match(kc)
        tag = tm.group(1).lower() if tm else None
        if tag in ("body", "p"):
            rest = kc[len(tm.group(1)):]
            if not re.search(r"[.\[#]", rest):
                return True
    return False


# ── family / line-height / weight resolution per consuming rule ─────────────────────

def _family_for_selector(rules: list[dict], font_size_var: str,
                         family_pool: dict[str, list[dict]]) -> str | None:
    """The literal font-family a heading/text rule declares alongside its
    ``font-size: var(font_size_var)``. Resolves ``var()`` family aliases. Returns the
    first declared family name (stack head)."""
    fs_use = re.compile(r"font-size\s*:\s*var\(\s*" + re.escape(font_size_var) + r"\b")
    fam_decl = re.compile(r"font-family\s*:\s*([^;]+)")
    for r in rules:
        decls = r.get("decls", "")
        if not fs_use.search(decls):
            continue
        fm = fam_decl.search(decls)
        if not fm:
            continue
        raw = fm.group(1).strip()
        resolved = resolve_family(raw, family_pool)
        if resolved:
            return resolved
    return None


def resolve_family(raw: str, family_pool: dict[str, list[dict]],
                   _seen: frozenset = frozenset()) -> str | None:
    """First concrete family in a font-family value, chasing ``var()`` aliases."""
    raw = raw.strip()
    m = _VAR_RE.match(raw)
    if m:
        ref, fallback = m.group(1), m.group(2)
        if ref in family_pool and ref not in _seen:
            # prefer the BASE (no-media), NON-!important, non-attribute-scoped definition
            # so a locale/CJK override (`[lang] { --font: 'Zen Kaku' !important }`) never
            # masks the brand's default family.
            def rank(d):
                return (bool(d["media"]),
                        "!important" in d["value"].lower(),
                        bool(re.search(r"\[[^\]]+\]", d.get("selector", ""))),
                        d["order"])
            for d in sorted(family_pool[ref], key=rank):
                got = resolve_family(d["value"], family_pool, _seen | {ref})
                if got:
                    return got
        if fallback:
            return resolve_family(fallback, family_pool, _seen | {ref})
        return None
    # strip !important + quotes; take the first family in the stack
    raw = raw.replace("!important", "").strip()
    head = raw.split(",")[0].strip().strip("\"'")
    return head or None


def classify_family(family: str | None) -> str | None:
    if not family:
        return None
    return "serif" if any(h in family.lower() for h in _SERIF_HINTS) else "sans"


def _matching_prop_var(font_size_var: str, prop_pool: dict[str, list[dict]]) -> str | None:
    """The line-height / font-weight token whose suffix matches a font-size token's
    suffix (``--x-font-size-h2`` ↔ ``--x-line-height-h2``). Brand-agnostic suffix match."""
    suffix = _role_from_var_name(font_size_var)
    if not suffix:
        return None
    for var in prop_pool:
        if var.endswith("-" + suffix) or var.endswith(suffix):
            # avoid matching h1 to h1-small etc.: require exact suffix tail
            tail = re.sub(r".*?(line-height|font-weight)-?", "", var)
            if tail == suffix:
                return var
    return None


# ── ladder assembly ─────────────────────────────────────────────────────────────────

def build_tier(var: str, size_pool: dict, lh_pool: dict, weight_pool: dict,
               family_pool: dict, rules: list[dict], consumers: dict,
               root_px: float) -> dict:
    role = _role_from_var_name(var)
    # per-tier resolved px
    tiers: dict[str, dict] = {}
    for vp in TIER_VIEWPORTS:
        raw = value_at(size_pool[var], size_pool, vp, root_px)
        px = _to_px(raw, root_px) if raw else None
        if px is not None:
            tiers[f"w{vp}"] = {"px": px, "rem": _rem_of(px, root_px)}
    canonical_px = (tiers.get(f"w{CANONICAL_TIER}") or {}).get("px")
    # responsive variant: does the token change across the ladder?
    distinct = sorted({t["px"] for t in tiers.values()})
    responsive = len(distinct) > 1
    # line-height + weight (suffix-matched tokens, resolved at canonical tier)
    lh_var = _matching_prop_var(var, lh_pool)
    lh_val = value_at(lh_pool[lh_var], lh_pool, CANONICAL_TIER, root_px) if lh_var else None
    w_var = _matching_prop_var(var, weight_pool)
    w_val = value_at(weight_pool[w_var], weight_pool, CANONICAL_TIER, root_px) if w_var else None
    # family + serif/sans
    family = _family_for_selector(rules, var, family_pool)
    # consuming selectors + inferred html roles
    uses = consumers.get(var, [])
    heading_tags = sorted({u["headingTag"] for u in uses if u["headingTag"]})
    used_by_button = any(u["isButton"] for u in uses)
    used_by_text = any(u["isText"] for u in uses)
    used_by_body = any(u.get("isBodyElement") for u in uses)
    is_text_default = "text-font-size" in var
    html_roles = list(heading_tags)
    if used_by_button:
        html_roles.append("control")
    if used_by_text:
        html_roles.append("body")
    return {
        "token": var,
        "role": role,
        "sizePx": canonical_px,
        "sizeRem": _rem_of(canonical_px, root_px),
        "responsive": responsive,
        "tiers": tiers,
        "lineHeight": lh_val,
        "lineHeightToken": lh_var,
        "weight": _coerce_weight(w_val),
        "weightToken": w_var,
        "family": family,
        "familyClass": classify_family(family),
        "usedByHeadingTags": heading_tags,
        "usedByButton": used_by_button,
        "usedByText": used_by_text,
        "usedByBodyElement": used_by_body,
        "isTextDefault": is_text_default,
        "htmlRoles": html_roles,
        "consumerCount": len(uses),
        "consumers": [u["selector"] for u in uses[:8]],
        "provenance": {"source": "css-var",
                       "confirmedBy": ["computed"] if canonical_px else []},
    }


def _coerce_weight(val):
    if val is None:
        return None
    m = re.match(r"^\s*(\d{3})\s*$", str(val))
    return int(m.group(1)) if m else str(val).strip()


# ── computed-cluster fallback (no font-size tokens declared) ─────────────────────────

def cluster_from_computed(computed: dict) -> list[dict]:
    """Fallback ladder for brands WITHOUT font-size custom properties: cluster the
    computed font-sizes of every measured heading across the full tier ladder (never a
    single instance). Emits descending size clusters as anonymous tiers."""
    sizes: list[float] = []
    tiers = computed.get("tiers") or {}
    # prefer the canonical tier's per-tag headings; union across the ladder
    for tdata in tiers.values():
        for tag, rec in (tdata.get("headings") or {}).items():
            if isinstance(rec, dict) and rec.get("font-size"):
                px = _to_px(rec["font-size"])
                if px:
                    sizes.append(px)
    for tag, rec in (computed.get("headings") or {}).items():
        if isinstance(rec, dict) and rec.get("font-size"):
            px = _to_px(rec["font-size"])
            if px:
                sizes.append(px)
    if not sizes:
        return []
    sizes = sorted(set(round(s) for s in sizes), reverse=True)
    out = []
    for i, px in enumerate(sizes):
        out.append({
            "token": None, "role": f"cluster-{i}", "sizePx": float(px),
            "sizeRem": _rem_of(px), "responsive": False,
            "tiers": {f"w{CANONICAL_TIER}": {"px": float(px), "rem": _rem_of(px)}},
            "lineHeight": None, "weight": None, "family": None, "familyClass": None,
            "htmlRoles": [], "consumerCount": 0, "consumers": [],
            "provenance": {"source": "computed-cluster", "confirmedBy": ["computed"]},
        })
    return out


# ── canonical role mapping (tier ladder → brand.yaml roles) ──────────────────────────

def _vendor_prefix(var: str) -> str:
    """The design-system namespace prefix of a font-size token, i.e. everything up to
    and including ``font-size`` (``--cl-font-size-h1`` -> ``--cl-font-size``). Used to
    keep body/small/micro in the SAME token family as the headings, so tokens leaking in
    from unrelated third-party stylesheets (``--font-size-xl``) don't win."""
    m = re.match(r"(.*?font-size)", var or "")
    return m.group(1) if m else (var or "")


def canonical_ladder(tiers: list[dict]) -> dict:
    """Map the raw token tiers onto the canonical brand-role ladder
    (display/h1..h6/body/small/micro). Selection is generic + namespace-aware:
      * hN roles bind to the token whose SEMANTIC selector (bare ``hN`` / sole ``.cl-hN``)
        paints that heading tag; ties break by consumer count;
      * the dominant heading namespace prefix then scopes the text ladder so unrelated
        third-party size tokens can't win;
      * body binds to the bare ``body``/``p`` token, else the text-default token
        (``--*text-font-size*``), else the namespace's ``medium`` token;
      * small/micro/large bind to like-named tokens IN THE DOMINANT NAMESPACE;
      * display binds to the largest ``display*``-named token.
    Returns {roleName: tier-dict, ...} plus a ``definedButUnused`` list."""
    out: dict[str, dict] = {}
    for tag in _HEADING_TAGS:
        painted = [t for t in tiers if tag in t.get("usedByHeadingTags", []) and t.get("sizePx")]
        if painted:
            out[tag] = max(painted, key=lambda t: t.get("consumerCount", 0))

    # dominant namespace = the most common prefix among the bound headings
    prefixes = [_vendor_prefix(t["token"]) for t in out.values() if t.get("token")]
    dom = max(set(prefixes), key=prefixes.count) if prefixes else ""

    def by_name(name):
        cands = [t for t in tiers if t["role"] == name and t.get("sizePx")]
        in_ns = [t for t in cands if _vendor_prefix(t["token"]) == dom]
        pool = in_ns or cands
        return max(pool, key=lambda t: t.get("consumerCount", 0)) if pool else None

    # body: the DEFAULT reading register in the dominant namespace. Contextual text
    # tokens (--*text-font-size*) are excluded because components redefine them (button
    # text, small print), so they don't resolve to the base paragraph size. Prefer the
    # namespace's paragraph/medium role, ranked; fall back to any text-consumed token.
    ns_pref = dom[:5] if dom.startswith("--") else "--"
    in_ns = [t for t in tiers if t.get("token")
             and (_vendor_prefix(t["token"]) == dom or t["token"].startswith(ns_pref))]
    body = None
    for want in ("p-medium", "medium", "body", "base", "p", "p-base"):
        cands = [t for t in in_ns if t["role"] == want and t.get("sizePx")]
        if cands:
            body = max(cands, key=lambda t: t.get("consumerCount", 0))
            break
    if body is None:
        text_cands = [t for t in in_ns if t.get("usedByText") and t.get("sizePx")]
        body = max(text_cands, key=lambda t: t.get("consumerCount", 0)) if text_cands else None
    if body and body.get("sizePx"):
        out["body"] = body
    for name in ("small", "micro", "large"):
        t = by_name(name)
        if t:
            out[name] = t
    # display: largest display*-named token
    disp = [t for t in tiers if t["role"].startswith("display") and t.get("sizePx")]
    if disp:
        out["display"] = max(disp, key=lambda t: t["sizePx"])

    used_tokens = {id(t) for t in out.values()}
    unused = [t["token"] for t in tiers
              if id(t) not in used_tokens and t.get("consumerCount", 0) == 0 and t["token"]]
    return {"roles": out, "definedButUnused": unused, "dominantNamespace": dom}


# ── driver ────────────────────────────────────────────────────────────────────────

def extract(evidence_dir: Path) -> dict:
    css_doc = json.loads((evidence_dir / "css-rules.json").read_text())
    rules = css_doc.get("rules", [])
    computed_path = evidence_dir / "computed-styles.json"
    computed = json.loads(computed_path.read_text()) if computed_path.is_file() else {}

    # root font-size (px), if the capture declares one on html/:root
    root_px = ROOT_PX
    html_font = (computed.get("htmlFont") or {}).get("font-size")
    if html_font:
        px = _to_px(html_font)
        if px:
            root_px = px

    size_pool = _custom_prop_defs(rules, "font-size")
    lh_pool = _custom_prop_defs(rules, "line-height")
    weight_pool = _custom_prop_defs(rules, "font-weight")
    family_pool = _custom_prop_defs(rules, "font-family")
    consumers = find_consumers(rules)

    method = "css-var"
    tiers: list[dict] = []
    if size_pool:
        for var in size_pool:
            tiers.append(build_tier(var, size_pool, lh_pool, weight_pool,
                                    family_pool, rules, consumers, root_px))
        tiers.sort(key=lambda t: (t.get("sizePx") or 0), reverse=True)
    else:
        method = "computed-cluster"
        tiers = cluster_from_computed(computed)

    ladder = canonical_ladder(tiers) if method == "css-var" else {"roles": {}, "definedButUnused": []}

    # vision/instance confirmation: match each canonical role to a measured computed
    # instance where one exists (heading tag first-instance ladder from measure_computed)
    confirm = confirm_with_computed(ladder.get("roles", {}), computed)

    return {
        "schemaVersion": SCHEMA,
        "method": method,
        "rootPx": root_px,
        "tierViewports": list(TIER_VIEWPORTS),
        "canonicalTier": CANONICAL_TIER,
        "fontSizeTokenCount": len(size_pool),
        "tokens": tiers,
        "dominantNamespace": ladder.get("dominantNamespace", ""),
        "canonicalRoles": ladder.get("roles", {}),
        "definedButUnused": ladder.get("definedButUnused", []),
        "confirmation": confirm,
    }


def confirm_with_computed(roles: dict, computed: dict) -> dict:
    """For each canonical role, record whether a measured computed instance corroborates
    the CSS-var size (within 2px) and flag mismatches. Uses whatever heading instances
    measure_computed captured (still useful as a corroboration channel, not the source
    of truth)."""
    tiers = computed.get("tiers") or {}
    canon = tiers.get(str(CANONICAL_TIER)) or {}
    measured_headings = canon.get("headings") or computed.get("headings") or {}
    out: dict[str, dict] = {}
    for role, t in roles.items():
        rec = measured_headings.get(role) if isinstance(measured_headings, dict) else None
        measured_px = _to_px(rec.get("font-size")) if isinstance(rec, dict) and rec.get("font-size") else None
        css_px = t.get("sizePx")
        agrees = (measured_px is not None and css_px is not None
                  and abs(measured_px - css_px) <= 2)
        out[role] = {
            "cssVarPx": css_px,
            "measuredInstancePx": measured_px,
            "agrees": agrees,
            "note": ("measured first-instance corroborates css-var" if agrees
                     else "measured first-instance differs (single-instance not authoritative)"
                     if measured_px is not None else "no measured instance for this tag"),
        }
    return out


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--evidence", type=Path, required=True,
                    help="evidence dir with css-rules.json (+ computed-styles.json)")
    ap.add_argument("--out", type=Path, default=None,
                    help="output path (default <evidence>/type-scale.json)")
    return ap


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if not (args.evidence / "css-rules.json").is_file():
        raise SystemExit(f"type_scale: {args.evidence/'css-rules.json'} missing — run mine_css first")
    doc = extract(args.evidence)
    out = args.out or (args.evidence / "type-scale.json")
    out.write_text(json.dumps(doc, indent=1) + "\n")
    roles = doc["canonicalRoles"]
    print(f"[type-scale] method={doc['method']} tokens={doc['fontSizeTokenCount']} "
          f"canonical-roles={len(roles)} -> {out.name}")
    for role in ("display", "h1", "h2", "h3", "h4", "h5", "h6", "body", "small", "micro"):
        t = roles.get(role)
        if t:
            print(f"    {role:<8} {str(t.get('sizePx'))+'px':<7} lh={t.get('lineHeight')} "
                  f"w={t.get('weight')} fam={t.get('familyClass')} ({t.get('token')})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
