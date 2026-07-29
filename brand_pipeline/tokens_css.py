#!/usr/bin/env python3
"""tokens_css.py — the LAYER-1 token generator + the canonical brand.yaml resolvers.

Three-layer indirection (experiments/token-layer-design/SPEC.md §A):

  LAYER 1  measured brand values — generated HERE from brand.yaml: flat, one var per
           measured fact (``--color-*``, ``--surface-*``, ``--font/-size/-weight/
           -leading/-case/-tracking-<tier>``, ``--space-*``, ``--radius-*``,
           ``--shadow-*``, ``--aspect-*``, ``--motion-*``, ``--button-*``,
           ``--chrome-*``). NO var()/calc() — every value is a resolved literal, so
           each maps 1:1 to a Webflow native variable.
  LAYER 2  semantic role aliases — the existing ``--c-*`` contract, emitted per surface
           scope by component_render.component_vars / compose_section.root_vars /
           compose_page.legacy_root_vars: every right-hand side is a var() reference
           into layer 1, never a Python-interpolated literal.
  LAYER 3  renderer usage — component/scaffold CSS references ONLY var(--c-*) etc.

Fallback policy (DECISIONS.md #2): a missing REQUIRED source key raises
``TokenGenerationError`` at generation time with the exact brand.yaml path to fix.
Missing OPTIONAL tokens disable their device (``TokensBundle.disabled_devices``) —
never substitute another brand's magnitude.

This module also hosts the canonical token RESOLVERS (``color_value``, ``type_role``,
``spacing_value``, ``base_size``, ``css_len``, ``font_stack``, ``google_fonts_link``,
``resolve_surface``) that previously lived in render_section.py (retired 2026-07-03 —
see brand_pipeline/quarantine/). All composers import them from here.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from screenshot_to_template.repo_paths import report_path

GENERATOR_VERSION = "1.0.0"

# ── canonical token resolvers (moved verbatim from render_section.py) ────────────

def color_value(doc, token):
    """Resolve a token ref (e.g. 'text/on-inverse' or 'accent/primary') to hex."""
    if not token:
        return None
    c = doc["tokens"]["colors"].get(token)
    return c["value"] if c else token


# A loadable Google-Fonts proxy by generic family, used when a type role carries
# no explicit renderProxy (e.g. the families+scale token shape). Brand-agnostic.
_PROXY_FOR_GENERIC = {"serif": "Source Serif 4", "sans-serif": "Lexend Deca"}


def _normalize_scale_entry(entry, families):
    """Map a `tokens.type.scale` entry (families+scale shape) onto the flat
    type-role shape the renderer consumes (family/sizeRem/lineHeight/weight/...)."""
    fam_key = entry.get("family")
    fam_node = families.get(fam_key) if isinstance(families, dict) else None
    fam = fam_node.get("value") if isinstance(fam_node, dict) else (fam_key or None)
    return {
        "family": fam,
        "sizeRem": entry.get("sizeRem"),
        "lineHeight": entry.get("line", entry.get("lineHeight")),
        "weight": entry.get("weight"),
        "letterSpacing": entry.get("tracking", entry.get("letterSpacing")),
        "case": entry.get("case"),
    }


def _pick_scale_entry(role, scale):
    """Pick a scale entry for a requested render role by family/keyword. Generic:
    no brand literals - matches on the family bucket and role keywords."""
    r = role.lower()
    items = list(scale.items())

    # Exact tier-name match is AUTHORITATIVE for register-specific roles: a hyphenated
    # role name ('display-hero', 'button-md', ...) is a request for that precise measured
    # tier, so when the brand's scale carries the key verbatim it wins over the keyword
    # heuristics below (which otherwise pick e.g. the LARGEST display-family tier — the
    # B11 bug where 'display-hero' resolved to a bigger sibling). Bare bucket roles
    # ('body', 'display', 'eyebrow') keep the heuristics, which deliberately choose the
    # reading/lead register rather than a same-named smaller tier.
    if "-" in r and isinstance(scale.get(role), dict):
        return scale[role]

    def fam(famkey):
        return [v for _, v in items if v.get("family") == famkey]

    if "eyebrow" in r:
        for k, v in items:
            if "eyebrow" in k:
                return v
        for k, v in items:
            # case-based fallback only among small tiers, so an uppercase display/h2
            # tier is never mistaken for the eyebrow register
            if v.get("case") == "uppercase" and (v.get("sizeRem") or 9) <= 1.25:
                return v
    if "display" in r or "hero" in r or r in ("h0", "h1"):
        disp = fam("display") or [v for _, v in items]
        return max(disp, key=lambda v: v.get("sizeRem") or 0)
    if "button" in r or "control" in r:
        btn = fam("button")
        if btn:
            return min(btn, key=lambda v: v.get("sizeRem") or 0)
    if "body" in r or "paragraph" in r:
        for k, v in items:
            if k.startswith("body") and k.endswith("-lg"):
                return v
        body = [v for k, v in items if k.startswith("body")]
        if body:
            return body[0]
    return scale.get(role)


def type_role(doc, role):
    """Resolve a type role. Supports the flat shape (role -> spec, WoodWave) AND the
    families+scale shape (tokens.type.{families,scale}, HubSpot). Brand-agnostic;
    the flat path returns the original node unchanged."""
    types = doc.get("tokens", {}).get("type", {})
    node = types.get(role)
    if isinstance(node, dict) and ("family" in node or "sizeRem" in node):
        return node
    scale = types.get("scale")
    if isinstance(scale, dict):
        entry = _pick_scale_entry(role, scale)
        if entry:
            return _normalize_scale_entry(entry, types.get("families") or {})
    return node if isinstance(node, dict) else {}


def spacing_value(doc, role, default="0rem"):
    s = doc["tokens"]["spacing"].get(role, {})
    return s.get("value", default)


def base_size(t):
    sz = t.get("sizeRem", {})
    if isinstance(sz, dict):
        return sz.get("base")
    return sz


def css_len(value, default):
    """Sanitize an approximate brand.yaml offset (e.g. '~-2.75rem') into valid CSS."""
    if value is None:
        return default
    v = str(value).replace("~", "").strip()
    return v or default


def resolve_surface(doc, layout):
    """Return (role, surface-dict). Prefers layout.surfaceRole; else matches the
    layout's surfaceMode.mode against tokens.surfaces[*].schemeMode."""
    surfaces = doc["tokens"]["surfaces"]
    role = layout.get("surfaceRole")
    if role and role in surfaces:
        return role, surfaces[role]
    mode = (layout.get("surfaceMode") or {}).get("mode")
    for r, s in surfaces.items():
        if s.get("schemeMode") == mode:
            return r, s
    # last-resort default
    first = next(iter(surfaces))
    return first, surfaces[first]


# Non-Google webfonts -> a close Google Fonts proxy that DOES load, so the preview
# reads on-brand. The canonical family name stays first in the CSS stack.
_PROXY_GF = {
    "Source Serif 4": "Source+Serif+4:opsz,wght@8..60,400;8..60,500;8..60,600",
    "Playfair Display": "Playfair+Display:wght@400;500",
    "Lexend Deca": "Lexend+Deca:wght@300;400;500;600;700",
    "Inter": "Inter:wght@400;500;600",
}
_SERIF_HINTS = ("serif", "playfair", "didone", "georgia")

# CSS generic font-family keywords. A declared family stack that already ends in one
# of these carries its OWN resolved generic — the substring serif-hint heuristic below
# must NOT be consulted (it false-positives on "sans-serif", which contains "serif").
_CSS_GENERICS = ("serif", "sans-serif", "monospace", "cursive", "fantasy",
                 "system-ui", "ui-serif", "ui-sans-serif", "ui-monospace",
                 "ui-rounded", "math", "emoji", "fangsong")


def _split_families(stack) -> list[str]:
    """Split a CSS font-family declaration into member tokens, respecting quotes.
    ``'"HubSpot Sans", sans-serif'`` (a declared stack) → ``['"HubSpot Sans"',
    'sans-serif']``; a bare ``Inter`` → ``['Inter']``."""
    out, buf, q = [], [], ""
    for ch in str(stack):
        if q:
            buf.append(ch)
            if ch == q:
                q = ""
        elif ch in "'\"":
            q = ch
            buf.append(ch)
        elif ch == ",":
            tok = "".join(buf).strip()
            if tok:
                out.append(tok)
            buf = []
        else:
            buf.append(ch)
    tok = "".join(buf).strip()
    if tok:
        out.append(tok)
    return out


def _unquote_family(tok: str) -> str:
    tok = str(tok).strip()
    if len(tok) >= 2 and tok[0] == tok[-1] and tok[0] in "'\"":
        return tok[1:-1].strip()
    return tok


def _generic_family(family, proxy):
    # A declared stack that ends in a CSS generic keyword IS its own truth — return it
    # verbatim (fixes the "sans-serif"→serif substring false-positive that mis-classed
    # a sans body/control family as serif and pulled a serif proxy in front of it).
    members = _split_families(family)
    if members and _unquote_family(members[-1]).lower() in _CSS_GENERICS:
        return _unquote_family(members[-1]).lower()
    base = f"{family} {proxy}".lower()
    return "serif" if any(h in base for h in _SERIF_HINTS) else "sans-serif"


def deliverable_families(doc, brand_dir=None) -> set[str]:
    """The families this brand can actually DELIVER as its own face.

    A face is deliverable when the brand REGISTERS it in ``selfHostedFonts`` with at
    least one face file — that registry is what makes compose_section emit the
    ``@font-face`` blocks and copy the files next to the render. When ``brand_dir`` is
    given the registry is additionally checked against disk (``assets/fonts/``), so a
    registry entry whose files were never captured is reported as what it is: a
    declaration, not a delivery.

    Brand-agnostic: nothing here knows any family name — it reads the brand's own
    declarations only."""
    hosted: set[str] = set()
    entries = doc.get("selfHostedFonts") if isinstance(doc, dict) else None
    fonts_dir = Path(brand_dir) / "assets" / "fonts" if brand_dir else None
    for entry in (entries or []):
        if not isinstance(entry, dict):
            continue
        fam = str(entry.get("family") or "").strip()
        if not fam:
            continue
        files = [str(x).strip() for f in (entry.get("faces") or [])
                 if isinstance(f, dict) for x in (f.get("files") or [])
                 if isinstance(x, str) and str(x).strip()]
        if not files:
            continue
        if fonts_dir is not None and not any((fonts_dir / n).exists() for n in files):
            continue
        hosted.add(fam)
    return hosted


def _stack_members(fam: str, hint: str = "") -> tuple[list[str], list[str], str]:
    """Split a declared family value into (member tokens without the trailing CSS
    generic, their unquoted names, the resolved generic keyword). ``hint`` is the
    role's authored proxy, which the generic classifier reads for bare family names
    that carry no generic keyword of their own."""
    generic = _generic_family(fam, hint or "")
    members = _split_families(fam)
    if members and _unquote_family(members[-1]).lower() in _CSS_GENERICS:
        members = members[:-1]
    return members, [_unquote_family(m) for m in members], generic


def _family_css(fam: str, render_proxy: str | None, *, self_hosted=(), proxy_for=None):
    """Build a CSS font-family value + the set of webfont proxies to load.

    The decision is driven by whether the declared face is DELIVERABLE, never by the
    syntax of the declaration. A declaration is only a claim; a face renders when the
    brand self-hosts it (``selfHostedFonts`` — @font-face + copied files) or when a
    loadable proxy is put in front of the declaration's own fallbacks.

    * a BARE single family name keeps the historical single-quoted emission plus its
      proxy (authored ``renderProxy``, else the generic's default), so it never
      degrades to a raw system face;
    * a declared MULTI-MEMBER stack is emitted with its members verbatim — they are
      already valid family tokens and must not be re-wrapped in another layer of
      quotes. When one of those members is self-hosted the stack DELIVERS its own
      face and no substitute is injected ahead of it. When none is, the primary family
      cannot render, so the proxy is the substitution actually doing the rendering and
      is inserted DIRECTLY AFTER the primary family — a declaration's own fallback
      members are usually locally installed faces, so a substitute appended behind
      them would never be reached.

    ``proxy_for`` (``substitution_map``) keeps one family's substitute identical across
    every role that declares it, so a family whose declarations disagree about their
    trailing generic cannot render as two different genres in one page.

    Returns ``(css_value, proxies_to_load)``. An undeliverable family for which no
    proxy exists returns no proxy at all: that is a real gap, and
    ``typography_delivery`` records it rather than letting it pass silently."""
    members, names, generic = _stack_members(fam, render_proxy or "")
    hosted = {str(f) for f in (self_hosted or ())}
    used: set[str] = set()
    is_stack = len(_split_families(fam)) > 1 or "'" in fam or '"' in fam
    if is_stack:
        parts = list(members)
        if hosted & set(names):
            # the stack delivers a brand face; an authored proxy stays a tail
            # fallback behind it rather than a substitution.
            if render_proxy and _unquote_family(render_proxy) not in names:
                parts.append(f"'{render_proxy}'")
                used.add(render_proxy)
        else:
            proxy = (render_proxy or (proxy_for or {}).get(names[0] if names else "")
                     or _PROXY_FOR_GENERIC.get(generic))
            if proxy and _unquote_family(proxy) not in names:
                parts.insert(1, f"'{proxy}'")
                used.add(proxy)
        parts.append(generic)
        return ", ".join(parts), used
    proxy = render_proxy or _PROXY_FOR_GENERIC.get(generic)
    parts = [f"'{fam}'"]
    if proxy and proxy != fam:
        parts.append(f"'{proxy}'")
        used.add(proxy)
    parts.append(generic)
    return ", ".join(parts), used


def font_stack(doc, role, fallback_family="sans-serif", *, self_hosted=None):
    t = type_role(doc, role)
    fam = t.get("family")
    if not fam:
        return fallback_family, set()
    hosted = deliverable_families(doc) if self_hosted is None else self_hosted
    return _family_css(fam, t.get("renderProxy"), self_hosted=hosted,
                       proxy_for=substitution_map(doc))


# ── typography DELIVERY facts ─────────────────────────────────────────────────────
# Every declared family resolves to exactly one of three outcomes, and each of them is
# RECORDED (tokens.manifest.json + a tokens-CSS disclosure comment). A declared face
# that renders as an unrecorded generic is the failure mode these facts close.
DELIVERY_SELF_HOSTED = "self-hosted"     # brand ships the files; @font-face is emitted
DELIVERY_PROXY = "proxy-substituted"     # a loadable stand-in renders in its place
DELIVERY_UNAVAILABLE = "unavailable"     # knowingly not delivered — a named gap


def declared_type_families(doc) -> dict[str, list[str]]:
    """Declared family value -> the type roles that request it (order-stable)."""
    out: dict[str, list[str]] = {}
    types = (doc or {}).get("tokens", {}).get("type", {}) or {}
    roles = list(_REQUIRED_TYPE_ROLES) + list(_OPTIONAL_TYPE_ROLES)
    scale = types.get("scale")
    native = scale if isinstance(scale, dict) else {
        k: v for k, v in types.items()
        if isinstance(v, dict) and ("family" in v or "sizeRem" in v)}
    roles += [k for k in (native or {}) if k not in roles]
    for role in roles:
        t = type_role(doc, role)
        fam = t.get("family") if isinstance(t, dict) else None
        if not fam:
            continue
        out.setdefault(str(fam), [])
        if role not in out[str(fam)]:
            out[str(fam)].append(role)
    return out


def substitution_map(doc) -> dict[str, str]:
    """Declared family name -> the ONE substitute that stands in for it brand-wide.

    Captures routinely declare the same family with inconsistent trailing generics
    across roles. Resolving the substitute per declaration would then render one brand
    family in two different genres on the same page, so the first declaration that
    resolves a substitute fixes it for that family. An authored ``renderProxy`` always
    wins for the role that carries it."""
    out: dict[str, str] = {}
    for fam, roles in declared_type_families(doc).items():
        authored = (type_role(doc, roles[0]) or {}).get("renderProxy")
        _members, names, generic = _stack_members(fam, authored or "")
        if not names or names[0] in out:
            continue
        proxy = authored or _PROXY_FOR_GENERIC.get(generic)
        if proxy:
            out[names[0]] = proxy
    return out


def typography_delivery(doc, brand_dir=None) -> list[dict]:
    """How every declared type family is ACTUALLY delivered — the fact that turns a
    silent generic fallback into a recorded outcome.

    One row per declared family value: the primary family, the roles that request it,
    whether the brand self-hosts it, the substitute that renders in its place, and the
    resulting ``status`` (``self-hosted`` / ``proxy-substituted`` / ``unavailable``).
    ``unavailable`` is not an error here — it is the honest record of a face this
    project cannot redistribute and has no stand-in for.

    The status is read off the stack this brand ACTUALLY emits, not recomputed beside
    it: a substitute counts only where it lands ahead of the declaration's own
    fallbacks, since a member behind a locally-installed face is never reached. The
    one thing this adds on top of the emitters' view is disk truth — pass ``brand_dir``
    and a family registered as self-hosted whose files were never captured is reported
    as the gap it is instead of the delivery it claims to be."""
    hosted = deliverable_families(doc, brand_dir)
    registered = deliverable_families(doc)
    substitutes = substitution_map(doc)
    rows: list[dict] = []
    for fam, roles in declared_type_families(doc).items():
        proxy_authored = (type_role(doc, roles[0]) or {}).get("renderProxy")
        _members, names, generic = _stack_members(fam, proxy_authored or "")
        primary = names[0] if names else ""
        emitted, used = _family_css(fam, proxy_authored, self_hosted=registered,
                                    proxy_for=substitutes)
        # the member immediately after the primary family is the only position a
        # substitute can render from; anything further back sits behind a fallback.
        out = _split_families(emitted)
        front = _unquote_family(out[1]) if len(out) > 1 else ""
        substitute = front if front in used and front in _PROXY_GF else ""
        # a declared family that is ITSELF a loadable webfont needs no stand-in: the
        # composer links the family the brand actually declared.
        loadable_itself = bool(primary) and primary in _PROXY_GF
        row = {
            "family": primary,
            "declared": fam,
            "roles": roles,
            "generic": generic,
            "selfHosted": bool(hosted & set(names)),
        }
        if row["selfHosted"]:
            row["status"] = DELIVERY_SELF_HOSTED
        elif loadable_itself:
            row["status"] = DELIVERY_PROXY
            row["proxy"] = primary
            row["proxySource"] = "declared"
        elif substitute:
            row["status"] = DELIVERY_PROXY
            row["proxy"] = substitute
            row["proxySource"] = ("declared" if substitute in names
                                  else "authored" if proxy_authored
                                  else "generic-default")
            if registered & set(names):
                row["note"] = ("registered in selfHostedFonts but no face file present "
                               "on disk, so the substitute is what renders")
        else:
            row["status"] = DELIVERY_UNAVAILABLE
            if registered & set(names):
                row["note"] = ("registered in selfHostedFonts but no face file present "
                               "on disk — no @font-face is emitted and the stack puts "
                               "no substitute ahead of its own fallbacks")
            elif proxy_authored or substitutes.get(primary):
                row["proxy"] = proxy_authored or substitutes.get(primary)
                row["note"] = ("a proxy is named but does not render: it is not a "
                               "loadable webfont, or it sits behind the declaration's "
                               "own fallbacks")
        rows.append(row)
    return sorted(rows, key=lambda r: (r["family"], r["declared"]))


def delivery_note(rows: list[dict]) -> str:
    """One-line disclosure for the tokens-CSS header. Empty when every declared family
    is self-hosted (nothing to disclose), so fully self-hosting brands stay
    byte-stable."""
    parts, seen = [], set()
    for r in rows:
        if r.get("status") == DELIVERY_SELF_HOSTED or r["family"] in seen:
            continue
        seen.add(r["family"])
        if r.get("status") == DELIVERY_PROXY and r.get("proxy") == r["family"]:
            parts.append(f"{r['family']} (loaded as a webfont, not self-hosted)")
        elif r.get("status") == DELIVERY_PROXY:
            parts.append(f"{r['family']} -> {r['proxy']} ({r.get('proxySource', 'proxy')})")
        elif r.get("note"):
            parts.append(f"{r['family']} -> UNAVAILABLE ({r['note']})")
        else:
            parts.append(f"{r['family']} -> UNAVAILABLE (no self-hosted face, no loadable proxy)")
    if not parts:
        return ""
    return ("/* typography delivery — declared families this brand does NOT self-host, "
            "and what renders instead: " + "; ".join(parts) + ". */")


def google_fonts_link(proxies):
    families = [_PROXY_GF[p] for p in sorted(proxies) if p in _PROXY_GF]
    if not families:
        return ""
    q = "&".join(f"family={f}" for f in families)
    return ('<link rel="preconnect" href="https://fonts.googleapis.com">\n'
            '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
            f'<link href="https://fonts.googleapis.com/css2?{q}&display=swap" rel="stylesheet">')


# ── layer-1 generation ────────────────────────────────────────────────────────────

class TokenGenerationError(ValueError):
    """A REQUIRED brand token is missing at generation time (DECISIONS.md #2).
    The message names the exact brand.yaml path(s) to fix — re-extract or author."""


@dataclass
class TokensBundle:
    css: str
    index: dict[str, str]
    missing: list[str]
    manifest: dict
    disabled_devices: list[str] = field(default_factory=list)
    typography_delivery: list[dict] = field(default_factory=list)


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(name).lower()).strip("-")


def color_var(token_ref: str) -> str:
    """Layer-2 helper: the layer-1 var() reference for a color token ref."""
    return f"var(--color-{_slug(token_ref)})"


def surface_var(role: str) -> str:
    """Layer-2 helper: the layer-1 var() reference for a surface role's bg."""
    return f"var(--surface-{_slug(role)})"


def _px_to_rem(px) -> str | None:
    try:
        return f"{round(float(px) / 16, 4):g}rem"
    except (TypeError, ValueError):
        return None


def _button_size_rem(b: dict) -> str | None:
    """Measured button font-size as a CSS length: prefer the authored ``sizeRem`` (rem),
    else the raw computed ``fontSize`` ("18px" → rem; an already-rem/other length passes
    through). Byte-stable for brands that only carry ``sizeRem``."""
    if b.get("sizeRem") is not None:
        return f"{b['sizeRem']}rem"
    fs = b.get("fontSize")
    if fs is None:
        return None
    s = str(fs).strip()
    if s.endswith("px"):
        return _px_to_rem(s[:-2].strip()) or s
    return s


# text-transform value per measured case: sentence/none render as `none` (initial),
# uppercase stays, title-case maps to capitalize. Always emitted for a resolved tier so
# `text-transform: var(--c-case-*)` never silently drops (CR-1 closure).
_CASE_CSS = {"uppercase": "uppercase", "title": "capitalize", "capitalize": "capitalize"}

# Canonical type roles the composers consume (component_vars/root_vars + footer/ghost
# devices). Required roles hard-fail when unresolvable; optional roles disable devices.
_REQUIRED_TYPE_ROLES = ("display-hero", "h1", "h2", "h3", "body", "eyebrow", "control-text")
_OPTIONAL_TYPE_ROLES = ("counter-display", "ghost-watermark", "footer-sitemap-link")

_REQUIRED_COLORS = ("text/on-primary", "text/on-primary-muted", "text/on-inverse",
                    "text/on-inverse-muted", "border/hairline-on-primary",
                    "text/ghost-on-primary")
_REQUIRED_SURFACES = ("surface/primary", "surface/panel", "surface/inverse",
                      "surface/inverse-strong")

_BP_MAX = (("tablet", "991px"), ("mobileL", "767px"), ("mobile", "479px"))


def _emit_type_tier(role_slug: str, t: dict, lines, bp_lines, index, self_hosted=(),
                    proxy_for=None):
    """Emit the full --font/-size/-weight/-leading/-case/-tracking set for ONE tier."""
    fam = t.get("family")
    if fam:
        stack, _ = _family_css(fam, t.get("renderProxy"), self_hosted=self_hosted,
                               proxy_for=proxy_for)
        lines.append(f"  --font-{role_slug}: {stack};")
        index[f"--font-{role_slug}"] = stack
    size = t.get("sizeRem")
    base = size.get("base") if isinstance(size, dict) else size
    if base is not None:
        lines.append(f"  --size-{role_slug}: {base}rem;")
        index[f"--size-{role_slug}"] = f"{base}rem"
        # flat, breakpoint-independent alias — for structural calc ladders (ghost-scale
        # multipliers) AND for layer-2 aliases that must keep the legacy fixed-size
        # behavior (component_vars sizes never re-resolved per breakpoint) byte-stable.
        lines.append(f"  --size-{role_slug}-base: {base}rem;")
        index[f"--size-{role_slug}-base"] = f"{base}rem"
        if isinstance(size, dict):
            for bp, _mx in _BP_MAX:
                if size.get(bp) is not None:
                    bp_lines[bp].append(f"    --size-{role_slug}: {size[bp]}rem;")
                    index[f"--size-{role_slug}@{bp}"] = f"{size[bp]}rem"
    if t.get("weight") is not None:
        lines.append(f"  --weight-{role_slug}: {t['weight']};")
        index[f"--weight-{role_slug}"] = str(t["weight"])
    if t.get("lineHeight") is not None:
        lines.append(f"  --leading-{role_slug}: {t['lineHeight']};")
        index[f"--leading-{role_slug}"] = str(t["lineHeight"])
    case_css = _CASE_CSS.get(str(t.get("case") or "").lower(), "none")
    lines.append(f"  --case-{role_slug}: {case_css};")
    index[f"--case-{role_slug}"] = case_css
    tracking = t.get("letterSpacing")
    tracking = str(tracking) if tracking not in (None, "") else "0em"
    lines.append(f"  --tracking-{role_slug}: {tracking};")
    index[f"--tracking-{role_slug}"] = tracking


def emit_layer1(doc: dict) -> tuple[list[str], dict[str, list[str]], dict, list, list]:
    """The shared layer-1 emission core (page tokens AND kit tokens use this).

    Returns (lines, bp_lines, index, missing, disabled_devices) where ``lines`` are
    ``:root``-body declarations, ``bp_lines`` the responsive ladder per breakpoint,
    ``index`` maps every emitted token to its resolved value, ``missing`` lists
    REQUIRED brand.yaml paths that failed to resolve, and ``disabled_devices`` names
    the devices whose OPTIONAL tokens are absent.

    Font delivery is judged from the brand's ``selfHostedFonts`` REGISTRY alone, with
    no disk access, because every other emitter of a font value (the legacy :root
    vars, the composer's webfont-link decision) judges it the same way from the same
    document — a stack that disagreed with the links beside it would name a face
    nothing loads. Whether the registered files are actually on disk is a separate,
    reported question: see ``typography_delivery``."""
    tokens = (doc or {}).get("tokens", {}) or {}
    lines: list[str] = []
    bp_lines: dict[str, list[str]] = {bp: [] for bp, _ in _BP_MAX}
    index: dict[str, str] = {}
    missing: list[str] = []
    disabled: list[str] = []
    # which declared faces this brand can actually deliver — the font stacks below are
    # gated on delivery, never on how the family value happens to be written.
    self_hosted = deliverable_families(doc)
    proxy_for = substitution_map(doc)

    # colors
    colors = tokens.get("colors") or {}
    for role, c in colors.items():
        val = c.get("value") if isinstance(c, dict) else c
        if val:
            lines.append(f"  --color-{_slug(role)}: {val};")
            index[f"--color-{_slug(role)}"] = str(val)
    for req in _REQUIRED_COLORS:
        if f"--color-{_slug(req)}" not in index:
            missing.append(f"tokens.colors.{req}")

    # surfaces (color bgs only; a DESCRIPTIVE bg like "image + dark scrim" is a media
    # surface, not a flat color — the composer substitutes an on-palette dark)
    surfaces = tokens.get("surfaces") or {}
    for role, sf in surfaces.items():
        bg = sf.get("bg") if isinstance(sf, dict) else None
        if bg and re.match(r"^(#|rgb|hsl)", str(bg).strip()):
            lines.append(f"  --surface-{_slug(role)}: {bg};")
            index[f"--surface-{_slug(role)}"] = str(bg)
    for req in _REQUIRED_SURFACES:
        if f"--surface-{_slug(req)}" not in index:
            missing.append(f"tokens.surfaces.{req}.bg")

    # type — canonical roles first (normalized through type_role, both shapes),
    # then any native tiers not already covered (kit completeness).
    emitted_tiers: set[str] = set()
    for role in _REQUIRED_TYPE_ROLES + _OPTIONAL_TYPE_ROLES:
        t = type_role(doc, role)
        slug = _slug(role)
        if not t or (not t.get("family") and base_size(t) is None):
            if role in _REQUIRED_TYPE_ROLES:
                missing.append(f"tokens.type.{role}")
            else:
                disabled.append({"counter-display": "counter-display",
                                 "ghost-watermark": "ghost-watermark",
                                 "footer-sitemap-link": "footer-display-links"}[role])
            continue
        _emit_type_tier(slug, t, lines, bp_lines, index, self_hosted, proxy_for)
        emitted_tiers.add(slug)
    types = tokens.get("type") or {}
    native = types.get("scale") if isinstance(types.get("scale"), dict) else {
        k: v for k, v in types.items()
        if isinstance(v, dict) and ("family" in v or "sizeRem" in v)}
    fams = types.get("families") or {}
    for tier, node in (native or {}).items():
        slug = _slug(tier)
        if slug in emitted_tiers:
            continue
        t = _normalize_scale_entry(node, fams) if "scale" in types else node
        _emit_type_tier(slug, t, lines, bp_lines, index, self_hosted, proxy_for)
        emitted_tiers.add(slug)

    # spacing
    spacing = tokens.get("spacing") or {}
    for role, sp in spacing.items():
        val = sp.get("value") if isinstance(sp, dict) else sp
        if val:
            lines.append(f"  --space-{_slug(role)}: {val};")
            index[f"--space-{_slug(role)}"] = str(val)
    if not any(k.startswith("--space-section-padding") or k.startswith("--space-section-y")
               for k in index):
        missing.append("tokens.spacing.section-padding-light|section-y-*")
    for req in ("eyebrow-to-heading", "panel-padding"):
        if f"--space-{req}" not in index:
            missing.append(f"tokens.spacing.{req}")

    # radius (normalized: --radius-global always; roles when measured)
    rg = spacing.get("radius-global")
    rg_val = rg.get("value") if isinstance(rg, dict) else rg
    radius_roles = tokens.get("radius") or {}
    if not rg_val and isinstance(radius_roles.get("global"), dict):
        rg_val = radius_roles["global"].get("value")
    if rg_val:
        lines.append(f"  --radius-global: {rg_val};")
        index["--radius-global"] = str(rg_val)
    else:
        missing.append("tokens.spacing.radius-global (or tokens.radius.global)")
    for role, node in radius_roles.items():
        val = node.get("value") if isinstance(node, dict) else node
        # `0` is a REAL measured fact (square family — e.g. media wells whose parent
        # plate does the rounding), not an absence: only None/"" skip emission.
        if val not in (None, "") and role != "global":
            lines.append(f"  --radius-{_slug(role)}: {val};")
            index[f"--radius-{_slug(role)}"] = str(val)

    # shadows (absent ⇒ not emitted: flat brands)
    shadows = tokens.get("shadow") or {}
    for level, node in shadows.items():
        val = node.get("value") if isinstance(node, dict) else node
        if val:
            lines.append(f"  --shadow-{_slug(level)}: {val};")
            index[f"--shadow-{_slug(level)}"] = str(val)
    if not shadows:
        disabled.append("shadows")

    # aspect palette (OPTIONAL per DECISIONS.md #5 — absence disables the device)
    palette = ((tokens.get("imagery") or {}) or {}).get("aspectPalette") or {}
    for name, a in palette.items():
        val = a.get("value") if isinstance(a, dict) else a
        if val:
            lines.append(f"  --aspect-{_slug(name)}: {val};")
            index[f"--aspect-{_slug(name)}"] = str(val)
    if not palette:
        disabled.append("aspect-palette")

    # motion (REQUIRED trio + easing; scrollReveal shift optional → fade-only reveal)
    ms = ((doc or {}).get("voice") or {}).get("motionSpec") or {}
    durations = ms.get("durations") or {}
    for k, tok in (("fast", "--motion-fast"), ("base", "--motion-base"),
                   ("slow", "--motion-slow")):
        if durations.get(k):
            lines.append(f"  {tok}: {durations[k]};")
            index[tok] = str(durations[k])
        else:
            missing.append(f"voice.motionSpec.durations.{k}")
    ease = (ms.get("easing") or {}).get("primary")
    if ease:
        lines.append(f"  --motion-ease: {ease};")
        index["--motion-ease"] = str(ease)
    else:
        missing.append("voice.motionSpec.easing.primary")
    shift = (ms.get("scrollReveal") or {}).get("translateY")
    if shift:
        lines.append(f"  --motion-shift: {shift};")
        index["--motion-shift"] = str(shift)

    # buttons (OPTIONAL family: absence ⇒ typographic-CTA structural variant)
    buttons = (doc or {}).get("buttons") or {}
    if isinstance(buttons.get("primary"), dict):
        for variant in ("primary", "secondary", "tertiary"):
            b = buttons.get(variant)
            if not isinstance(b, dict):
                continue
            prefix = "--button" if variant == "primary" else f"--button-{variant}"
            # full measured state surface (sysfix 2026-07): fgHover (label swap on
            # hover, e.g. outline→filled families), bgDisabled (measured disabled
            # fill) and the explicit control height are brand facts — dropping them
            # here silently downgraded every consumer to structural fallbacks.
            pairs = (("bg", "bg"), ("fg", "fg"), ("bgHover", "bg-hover"),
                     ("fgHover", "fg-hover"), ("bgPressed", "bg-pressed"),
                     ("bgDisabled", "bg-disabled"), ("fgDisabled", "fg-disabled"),
                     ("border", "border"),
                     ("padding", "pad"), ("radius", "radius"), ("weight", "weight"),
                     ("height", "height"))
            for src, suffix in pairs:
                if b.get(src) is not None:
                    lines.append(f"  {prefix}-{suffix}: {b[src]};")
                    index[f"{prefix}-{suffix}"] = str(b[src])
            # measured font WEIGHT: some captures carry it as ``weight`` (handled by the
            # pairs loop above), others as the raw computed ``fontWeight`` — bind either
            # so the button never silently falls back to the heading weight.
            if b.get("weight") is None and b.get("fontWeight") is not None:
                lines.append(f"  {prefix}-weight: {b['fontWeight']};")
                index[f"{prefix}-weight"] = str(b["fontWeight"])
            # measured font SIZE: ``sizeRem`` (rem) or the raw computed ``fontSize``
            # (e.g. "18px") — both are real button facts; without this the control-text
            # size (0.875rem) leaked onto a 18px measured CTA.
            _bsize = _button_size_rem(b)
            if _bsize is not None:
                lines.append(f"  {prefix}-size: {_bsize};")
                index[f"{prefix}-size"] = _bsize
            # measured font FAMILY (``font`` or the raw ``fontFamily``): absent ⇒ the
            # button rides the body sans family (correct for brands whose CTA uses the
            # body face). A declared family is composed via the shared stack builder.
            _bfont = b.get("font") or b.get("fontFamily")
            if _bfont:
                stack, _ = _family_css(_bfont, None, self_hosted=self_hosted,
                                       proxy_for=proxy_for)
                lines.append(f"  {prefix}-font: {stack};")
                index[f"{prefix}-font"] = stack
            # measured DARK-SURFACE variant (fix1 2026-07 item-10): a family's
            # `onInverse` facts emit under `<prefix>-oninverse-*`; consumed only
            # inside surface scopes that declare `controls: onInverse`
            # (component_render._button_oninverse_css). No facts ⇒ no vars.
            inv = b.get("onInverse")
            if isinstance(inv, dict):
                for src, suffix in pairs:
                    if inv.get(src) is not None:
                        lines.append(f"  {prefix}-oninverse-{suffix}: {inv[src]};")
                        index[f"{prefix}-oninverse-{suffix}"] = str(inv[src])
        for req in ("--button-bg", "--button-fg"):
            if req not in index:
                missing.append(f"buttons.primary.{'bg' if req.endswith('-bg') else 'fg'}")
    else:
        disabled.append("filled-button")

    # chrome (navbar/footer measured registers, px→rem)
    nav = ((doc or {}).get("navbar") or {}).get("measured") or {}
    nav_link = nav.get("link") or {}
    v = _px_to_rem(nav_link.get("fontSize"))
    if v:
        # measured nav register — single source; components read this, not control-text
        lines.append(f"  --size-nav: {v};")
        index["--size-nav"] = v
    if nav_link.get("fontWeight"):
        lines.append(f"  --chrome-nav-link-weight: {nav_link['fontWeight']};")
        index["--chrome-nav-link-weight"] = str(nav_link["fontWeight"])
    # measured nav-link hover WASH (pill/underlay interaction: hoverBg + hoverRadius) —
    # emitted only when extracted; component_render.nav_hover_css gates the CSS on these.
    if isinstance(nav_link.get("hoverBg"), str) and nav_link["hoverBg"].strip():
        lines.append(f"  --chrome-nav-link-hover-bg: {nav_link['hoverBg'].strip()};")
        index["--chrome-nav-link-hover-bg"] = nav_link["hoverBg"].strip()
    v = _px_to_rem(nav_link.get("hoverRadius"))
    if v:
        lines.append(f"  --chrome-nav-link-hover-radius: {v};")
        index["--chrome-nav-link-hover-radius"] = v
    logo = nav.get("logo") or {}
    for dim, suffix in (("width", "w"), ("height", "h")):
        v = _px_to_rem(logo.get(dim))
        if v:
            lines.append(f"  --chrome-nav-logo-{suffix}: {v};")
            index[f"--chrome-nav-logo-{suffix}"] = v
    foot = ((doc or {}).get("footer") or {}).get("measured") or {}
    foot_link = foot.get("link") or {}
    v = _px_to_rem(foot_link.get("fontSize"))
    if v:
        lines.append(f"  --chrome-foot-link-size: {v};")
        index["--chrome-foot-link-size"] = v
    if foot_link.get("fontWeight"):
        lines.append(f"  --chrome-foot-link-weight: {foot_link['fontWeight']};")
        index["--chrome-foot-link-weight"] = str(foot_link["fontWeight"])
    # measured link-hover color (AS-10/AS-20 interaction token: dark surfaces only —
    # the per-surface layer-2 scoping decides where it applies)
    hover = None
    for blk in ((doc or {}).get("footer"), (doc or {}).get("navbar")):
        c = ((blk or {}).get("measured") or {}).get("linkHoverColor")
        if isinstance(c, str) and c.strip():
            hover = c.strip()
            break
    if hover:
        lines.append(f"  --chrome-link-hover: {hover};")
        index["--chrome-link-hover"] = hover

    return lines, bp_lines, index, missing, disabled


def _media_blocks(bp_lines: dict[str, list[str]]) -> str:
    media = ""
    for bp, mx in _BP_MAX:
        if bp_lines[bp]:
            media += (f"\n@media (max-width: {mx}) {{\n  :root {{\n"
                      + "\n".join(bp_lines[bp]) + "\n  }\n}\n")
    return media


def build_page_tokens(doc: dict, style_ctx=None, *, brand_yaml_path=None) -> TokensBundle:
    """Generate the per-page layer-1 tokens block (SPEC §B.1/§B.2).

    Raises ``TokenGenerationError`` when any REQUIRED token is missing (fail-loud,
    DECISIONS.md #2). The css carries a deterministic manifest header (no timestamp,
    so regenerated pages stay byte-identical); the full manifest (with ``generated_at``
    + the resolved ``index``) is returned for ``write_manifest``."""
    brand_dir = Path(brand_yaml_path).parent if brand_yaml_path else None
    lines, bp_lines, index, missing, disabled = emit_layer1(doc)
    brand = ((doc or {}).get("brand") or {}).get("name", "Brand")
    if missing:
        raise TokenGenerationError(
            f"{brand}: required brand token(s) missing — re-extract or author: "
            + "; ".join(missing)
            + (f" (source: {report_path(brand_yaml_path)})" if brand_yaml_path else ""))
    sha = ""
    if brand_yaml_path and Path(brand_yaml_path).exists():
        sha = hashlib.sha256(Path(brand_yaml_path).read_bytes()).hexdigest()
    style_id = getattr(style_ctx, "style_id", "") if getattr(style_ctx, "active", False) else ""
    # style md hash (SPEC §F.4): a style edit flags composed pages as stale too.
    style_sha = ""
    style_src = getattr(getattr(style_ctx, "style", None), "source_path", "")
    if style_src and Path(style_src).exists():
        style_sha = hashlib.sha256(Path(style_src).read_bytes()).hexdigest()
    header = (f"/* {brand} — generated design tokens (layer 1). Source: brand.yaml"
              f" sha256={sha[:12] or 'unknown'}; generator tokens_css.py v{GENERATOR_VERSION};"
              f" style={style_id or 'none'}; tokens={len(index)};"
              f" disabledDevices={','.join(disabled) or 'none'}."
              f" Regenerate via the compose CLI — never hand-edit. */")
    delivery = typography_delivery(doc, brand_dir)
    note = delivery_note(delivery)
    css = (header + ("\n" + note if note else "")
           + "\n:root {\n" + "\n".join(lines) + "\n}\n" + _media_blocks(bp_lines))
    manifest = {
        "brand": brand,
        "brand_yaml_sha256": sha,
        "style_id": style_id,
        "style_md_sha256": style_sha,
        "generator_version": GENERATOR_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "token_count": len(index),
        "disabledDevices": disabled,
        "typographyDelivery": delivery,
        "index": index,
    }
    return TokensBundle(css=css, index=index, missing=missing,
                        manifest=manifest, disabled_devices=disabled,
                        typography_delivery=delivery)


def write_manifest(out_dir, bundle: TokensBundle) -> Path:
    """Write ``tokens.manifest.json`` beside a render (drift detection + the
    provenance checker's value index — SPEC §B.1/§F)."""
    p = Path(out_dir) / "tokens.manifest.json"
    p.write_text(json.dumps(bundle.manifest, indent=2) + "\n")
    return p


def style_tag(bundle: TokensBundle) -> str:
    """The tokens block as the FIRST <style> of a render (id='tokens' — the provenance
    scanner recognizes and skips it: layer 1 is the source of truth, not a violation)."""
    return f'<style id="tokens">\n{bundle.css}</style>'
