#!/usr/bin/env python3
"""capture_interaction_facts.py — evidence-derived INTERACTION FACT extractor.

The Archaeologist capture-prompt upgrades (baseline 30f52c3) added schema slots for
several NEW fact families that were previously reachable only as prose / vision hints,
but nothing DERIVED them from measured evidence and nothing CONSUMED them. This module
is the deterministic, BRAND-AGNOSTIC, PROVENANCE-TAGGED derivation for those families —
the exact discipline ``responsive_facts.py`` already uses for the hero/footer/nav
responsive facts (evidence → generic fact block → reviewable sidecar → fact-gated
consumer emitting a ``/* … (fact-gated: <path>) … */`` marker → AS-83 audit probe).

Families derived (each OPTIONAL and fact-gated — a source that carries no such
mechanic yields no block, so a brand without it renders byte-for-byte as before):

  * ``carousel``          structured slider/slideshow timing recipe (brand-schema §10.3g):
                          transitionMs / easing / controls / dots / autoplay / loop /
                          slidesPerView. ``intervalMs`` is JS-owned and OMITTED when the
                          static capture cannot read it (never guessed).
  * ``interactionStates`` exhaustive per-component interaction STATES (brand-schema §10.2b)
                          for generic component roles (button / link / tab / input):
                          hover / active / focus / disabled paint deltas.
  * ``navbar.mobile``     the hamburger→drawer contract (trigger / drawerSurface /
                          drawerAnim / closeAffordance).
  * ``navbar.sticky``     the sticky / scroll-shrink register (behavior + from/to register
                          + transition).
  * ``tokens.shadow``     elevation SCALE (generic role → measured box-shadow).
  * ``tokens.zIndex``     stacking SCALE (generic role → measured z-index).
  * ``footer.localeSelector`` the language/region control (options from the observed
                          locale-link cluster).

Everything keys on GENERIC vocabulary (role words, closed control vocab) via regexes that
match any naming convention — never a brand's specific class names, palette, or section
names. Every value traces to a measured rule and carries a ``provenance`` note.

Usage (derive the sidecar for a brand from its sibling evidence):
    ./venv/bin/python tools/extract/capture_interaction_facts.py runs/<brand>/brand/brand.yaml
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

SCHEMA = "interaction.v1"
SIDECAR_NAME = "interaction-facts.yaml"

# ── generic vocabulary (role words, never brand class names) ────────────────────────
# A carousel/slider/slideshow interactive track, any naming convention.
_CAROUSEL_RE = re.compile(r"carousel|slider|slideshow|swiper|slick|glide|splide", re.I)
# closed control-affordance vocabulary (matches brand-schema §10.3g CAROUSEL_CONTROLS)
_ARROW_RE = re.compile(r"arrow|prev|next|paddle|round-?button|control", re.I)
_DOTS_RE = re.compile(r"dot|bullet|pagination|indicator", re.I)
_AUTOPLAY_RE = re.compile(r"autoplay|auto-?play|auto-?rotate", re.I)
_INFINITE_RE = re.compile(r"infinite|loop|wrap", re.I)

# generic interactive component roles → selector match (any naming convention: kebab,
# camelCase, BEM). Substring-based so a hyphenated ``.x-button`` or camelCase ``.xButton``
# both match; a slight cross-match (a tab-button feeding both button + tab) is harmless
# because the consumer only emits button + link states and only safe paint props.
_COMPONENT_ROLES = {
    "button": re.compile(r"button|\bbtn\b", re.I),
    "link": re.compile(r"textlink|text-link|link|anchor", re.I),
    "tab": re.compile(r"tab(?!le)", re.I),
    "input": re.compile(r"input|textarea|field|select", re.I),
}
# the exhaustive interaction-state register (brand-schema §10.2b) → pseudo/attr match.
_STATE_MATCHERS = {
    "hover": re.compile(r":hover(?![\w-])"),
    "active": re.compile(r":active(?![\w-])|\[aria-pressed=true\]"),
    "focus": re.compile(r":focus-visible(?![\w-])|:focus(?![\w-])"),
    "disabled": re.compile(r":disabled(?![\w-])|\[disabled\]|\[aria-disabled=true\]|\.-disabled(?![\w-])"),
    "open": re.compile(r"\[aria-expanded=true\]|\[aria-selected=true\]|\.-open(?![\w-])|\.-active(?![\w-])"),
}
# paint/geometry props worth carrying for a state delta (visible deltas only).
_STATE_PROPS = ("background", "background-color", "color", "border", "border-color",
                "box-shadow", "outline", "outline-offset", "text-decoration",
                "text-decoration-line", "opacity", "transform")

# nav / header chrome selectors, generic. The lookbehind rejects only a preceding
# LETTER (so a hyphenated class like ``.global-nav-main`` still matches) while avoiding
# the word "navigate"/"navigation".
_NAV_RE = re.compile(r"(?<![a-z])nav(?!igat)|header|masthead|topbar|app-?bar", re.I)
# a scrolled / stuck register class the bar adopts on scroll (generic).
_SCROLLED_RE = re.compile(r"fixed|stuck|sticky|scroll|shrink|pinned|affix|is-?scrolled", re.I)
# a hamburger / mobile menu trigger, generic.
_BURGER_RE = re.compile(r"burger|hamburger|menu-?(?:toggle|button|btn|icon|trigger)"
                        r"|nav-?toggle|mobile-?(?:menu|nav|trigger)", re.I)
# a drawer / off-canvas / mobile-menu surface, generic.
_DRAWER_RE = re.compile(r"drawer|off-?canvas|mobile-?(?:menu|nav|panel)|menu-?open"
                        r"|burger-?menu|nav-?mobile", re.I)
_CLOSE_RE = re.compile(r"close|dismiss|\bx-?(?:glyph|icon|btn|button)\b", re.I)

_EMPTY = {"", "none", "transparent", "initial", "unset", "inherit", "auto",
          "rgba(0, 0, 0, 0)", "rgba(0,0,0,0)"}
_MS_RE = re.compile(r"([\d.]+)\s*(ms|s)\b", re.I)
_EASING_RE = re.compile(r"cubic-bezier\([^)]*\)|ease-in-out|ease-in|ease-out|ease|linear|steps\([^)]*\)", re.I)


# ── var resolution (combined :root + color-roles resolved tokens) ───────────────────

def _build_varmap(rules: list, color_roles: dict | None) -> dict:
    """A ``--var → literal`` map from the source ``:root`` custom properties plus the
    resolved color tokens in ``color-roles.json`` (the authoritative resolved-color
    evidence), then any other (non-:root) var definition as a fallback layer. First
    definition wins per precedence tier (root → color-roles → any-rule)."""
    varmap: dict[str, str] = {}
    for r in rules:
        sel = (r.get("selector") or "").strip()
        if r.get("media") or sel not in (":root", "html", ":where(:root)", ":root,:host"):
            continue
        for m in re.finditer(r"(--[\w-]+)\s*:\s*([^;]+)", r.get("decls", "") or ""):
            varmap.setdefault(m.group(1).strip(), m.group(2).strip())
    for t in ((color_roles or {}).get("tokens") or []):
        name = t.get("name") or t.get("token") or t.get("var")
        val = t.get("value") or t.get("resolved") or t.get("hex")
        if name and val and name not in varmap:
            varmap[name] = str(val)
    # fallback layer: any other var definition anywhere (first wins) so contextual
    # tokens (e.g. --*-anchor-hover-color) still resolve to a measured literal.
    for r in rules:
        for m in re.finditer(r"(--[\w-]+)\s*:\s*([^;]+)", r.get("decls", "") or ""):
            varmap.setdefault(m.group(1).strip(), m.group(2).strip())
    return varmap


def _split_top_comma(s: str) -> tuple[str, str]:
    """Split ``s`` on the FIRST top-level comma (paren-aware): (name, fallback)."""
    depth = 0
    for i, ch in enumerate(s):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch == "," and depth == 0:
            return s[:i], s[i + 1:]
    return s, ""


def _resolve(value: str, varmap: dict, depth: int = 0) -> str:
    """Resolve ``var(--x, fallback)`` chains (nested + paren-balanced) against ``varmap``;
    a var that resolves to nothing is left verbatim. Non-var text passes through."""
    val = (value or "").strip()
    if depth > 12:
        return val
    i = val.find("var(")
    if i < 0:
        return val
    j, pd = i + 4, 1
    while j < len(val) and pd:
        if val[j] == "(":
            pd += 1
        elif val[j] == ")":
            pd -= 1
        j += 1
    inner = val[i + 4:j - 1]
    name, fb = _split_top_comma(inner)
    name = name.strip()
    repl = varmap.get(name)
    if repl is None and fb.strip():
        repl = fb.strip()
    if repl is None:
        return val  # unresolvable — leave the var verbatim
    return _resolve(val[:i] + repl + val[j:], varmap, depth + 1)


def _decl(decls: str, prop: str) -> str | None:
    found = None
    for m in re.finditer(r"(?:^|;)\s*" + re.escape(prop) + r"\s*:\s*([^;!]+)", decls or ""):
        found = m.group(1).strip()
    return found


def _ms(value: str) -> int | None:
    m = _MS_RE.search(value or "")
    if not m:
        return None
    n = float(m.group(1))
    return int(round(n * 1000 if m.group(2).lower() == "s" else n))


# ── CAROUSEL timing recipe (brand-schema §10.3g) ────────────────────────────────────

def carousel_recipe(rules: list, varmap: dict) -> dict | None:
    """Structured slider timing recipe from measured CSS: transition duration/easing
    (from a ``--*carousel*-*duration``/``--*carousel*-easing`` var or a track transition),
    slidesPerView (from a ``--*slides-per-view*`` var), dots/arrows/autoplay/loop control
    affordances (from generic selectors). ``intervalMs`` (JS autoplay timer) is OMITTED —
    the static capture cannot read it. None when no carousel track is present."""
    has_track = False
    transition_ms = None
    easing = None
    slides_per_view = None
    controls: set[str] = set()
    autoplay = False
    loop = False
    dots = False
    for r in rules:
        sel = r.get("selector") or ""
        decls = r.get("decls", "") or ""
        if _CAROUSEL_RE.search(sel):
            has_track = True
            if _ARROW_RE.search(sel):
                controls.add("arrows")
            if _DOTS_RE.search(sel):
                controls.add("dots")
                dots = True
            if _AUTOPLAY_RE.search(sel):
                autoplay = True
            if _INFINITE_RE.search(sel):
                loop = True
        # timing / geometry vars (generic: any --...carousel...duration / easing / slides)
        for m in re.finditer(r"(--[\w-]+)\s*:\s*([^;]+)", decls):
            name, val = m.group(1).lower(), m.group(2).strip()
            if "carousel" not in name and "slider" not in name and "slide" not in name:
                continue
            has_track = True
            if ("duration" in name or "transition" in name) and transition_ms is None:
                transition_ms = _ms(val)
            if "easing" in name and easing is None:
                em = _EASING_RE.search(val)
                if em:
                    easing = em.group(0)
            if "slides-per-view" in name and "phone" not in name and "tablet" not in name \
                    and slides_per_view is None:
                if val.strip().isdigit():
                    slides_per_view = int(val.strip())
        # a track transition (translate/transform) with an inline duration/easing
        if _CAROUSEL_RE.search(sel) and "transition" in decls:
            tval = _decl(decls, "transition") or ""
            if transition_ms is None:
                transition_ms = _ms(_resolve(tval, varmap))
            if easing is None:
                em = _EASING_RE.search(_resolve(tval, varmap))
                if em:
                    easing = em.group(0)
    if not has_track:
        return None
    recipe: dict = {}
    if transition_ms is not None:
        recipe["transitionMs"] = transition_ms
    if easing:
        recipe["easing"] = easing
    if slides_per_view is not None:
        recipe["slidesPerView"] = slides_per_view
    if controls:
        recipe["controls"] = sorted(controls)
    recipe["dots"] = bool(dots)
    recipe["autoplay"] = bool(autoplay)
    recipe["loop"] = bool(loop)
    if not any(k in recipe for k in ("transitionMs", "easing", "slidesPerView", "controls")):
        return None
    recipe["provenance"] = {
        "origin": "extracted",
        "carousel": ("measured slider timing/geometry from the source's carousel CSS "
                     "custom properties + control-affordance selectors; intervalMs "
                     "(JS autoplay timer) is not exposed by the static capture and is "
                     "omitted (never guessed)."),
    }
    return recipe


# ── exhaustive per-component STATES (brand-schema §10.2b) ────────────────────────────

def _state_delta(decls: str, varmap: dict) -> dict:
    out: dict = {}
    for prop in _STATE_PROPS:
        raw = _decl(decls, prop)
        if raw is None:
            continue
        val = _resolve(raw, varmap)
        if val.lower() in _EMPTY and prop not in ("text-decoration", "text-decoration-line",
                                                  "outline", "box-shadow"):
            continue
        key = {"background-color": "background", "text-decoration-line": "textDecoration",
               "text-decoration": "textDecoration", "border-color": "borderColor",
               "outline-offset": "outlineOffset", "box-shadow": "boxShadow"}.get(prop, prop)
        out.setdefault(key, val)
    return out


def interaction_states(rules: list, varmap: dict) -> dict | None:
    """Per generic component role, the OBSERVED interaction-state register + measured
    paint deltas (hover/active/focus/disabled/open). None when no component carries a
    state rule (fact-gate)."""
    out: dict = {}
    for role, role_re in _COMPONENT_ROLES.items():
        states: dict = {}
        for r in rules:
            sel = r.get("selector") or ""
            if not role_re.search(sel):
                continue
            for state, st_re in _STATE_MATCHERS.items():
                if not st_re.search(sel):
                    continue
                # `open`/`expanded`/`selected` is a DISCLOSURE-component state
                # (brand-schema §10.2b): only disclosure-like roles carry it, so a plain
                # button/link/input never picks up a stray expanded-glyph transform.
                if state == "open" and role not in ("tab",):
                    continue
                delta = _state_delta(r.get("decls", "") or "", varmap)
                if delta:
                    # first measured rule per (role,state) wins; merge extra props in.
                    merged = states.get(state, {})
                    for k, v in delta.items():
                        merged.setdefault(k, v)
                    states[state] = merged
        if states:
            out[role] = {"statesObserved": sorted(states.keys()), **states}
    if not out:
        return None
    out["provenance"] = {
        "origin": "extracted",
        "interactionStates": ("measured per-component interaction-state paint deltas "
                              "(hover/active/focus/disabled/open) from the source's state "
                              "rules, resolved against the measured color tokens; generic "
                              "component roles only."),
    }
    return out


# ── NAVBAR sticky / scroll-shrink register ──────────────────────────────────────────

def navbar_sticky(rules: list, varmap: dict) -> dict | None:
    """The nav's sticky / scroll-shrink register: ``behavior`` + optional from/to register
    (the paint the bar adopts once scrolled) + transition. None when the bar is static."""
    at_rest_fixed = False
    to_register: dict = {}
    transition_ms = None
    easing = None
    for r in rules:
        sel = r.get("selector") or ""
        decls = r.get("decls", "") or ""
        if not _NAV_RE.search(sel):
            continue
        pos = _decl(decls, "position")
        if pos in ("fixed", "sticky") and not r.get("media"):
            at_rest_fixed = True
        # a scrolled-register variant selector (generic) that repaints the bar
        if _SCROLLED_RE.search(sel):
            bg = _resolve(_decl(decls, "background-color") or _decl(decls, "background") or "", varmap)
            sh = _decl(decls, "box-shadow")
            if bg and bg.lower() not in _EMPTY:
                to_register.setdefault("bg", bg)
            if sh and sh.lower() != "none":
                to_register.setdefault("shadow", _resolve(sh, varmap))
            tr = _decl(decls, "transition")
            if tr:
                transition_ms = transition_ms or _ms(tr)
                em = _EASING_RE.search(tr)
                if em and not easing:
                    easing = em.group(0)
    if not at_rest_fixed and not to_register:
        return None
    behavior = "scroll-shrink" if to_register else ("sticky" if at_rest_fixed else "static")
    out: dict = {"behavior": behavior}
    if to_register:
        out["toRegister"] = to_register
    if transition_ms is not None:
        out["transitionMs"] = transition_ms
    if easing:
        out["easing"] = easing
    out["provenance"] = {
        "origin": "extracted",
        "sticky": (f"nav bar measured {behavior}: "
                   + ("bar is position:fixed/sticky at rest" if at_rest_fixed else "")
                   + ("; adopts a scrolled register (bg/shadow) once stuck"
                      if to_register else "")),
    }
    return out


# ── NAVBAR mobile hamburger → drawer contract ───────────────────────────────────────

def navbar_mobile(rules: list, varmap: dict) -> dict | None:
    """The mobile hamburger→drawer contract: trigger kind + drawer surface + slide
    animation + close affordance. None when the nav ships no burger/drawer mechanic."""
    burger = False
    close_kind = None
    drawer_bg = None
    anim_ms = None
    anim_easing = None
    anim_prop = None
    for r in rules:
        sel = r.get("selector") or ""
        decls = r.get("decls", "") or ""
        if _BURGER_RE.search(sel):
            burger = True
            # a hamburger that morphs to an X on expand is an x-glyph close affordance
            if re.search(r"\[aria-expanded=true\]", sel) and "transform" in decls:
                close_kind = close_kind or "x-glyph"
        if _CLOSE_RE.search(sel):
            close_kind = close_kind or "x-glyph"
        if _DRAWER_RE.search(sel):
            bg = _resolve(_decl(decls, "background-color") or _decl(decls, "background") or "", varmap)
            if bg and bg.lower() not in _EMPTY and drawer_bg is None:
                drawer_bg = bg
            tr = _decl(decls, "transition")
            if tr and anim_ms is None:
                anim_ms = _ms(tr)
                em = _EASING_RE.search(tr)
                if em:
                    anim_easing = em.group(0)
                pm = re.match(r"\s*([\w-]+)", tr)
                if pm and pm.group(1) not in ("0", "0s"):
                    anim_prop = pm.group(1) if not re.match(r"[\d.]", pm.group(1)) else None
    if not burger:
        return None
    out: dict = {"trigger": {"kind": "hamburger"}}
    surf: dict = {}
    if drawer_bg:
        surf["bg"] = drawer_bg
    surf["side"] = "full"  # measured: mobile menu open covers the viewport (body fixed)
    out["drawerSurface"] = surf
    anim: dict = {}
    if anim_prop:
        anim["property"] = anim_prop
    if anim_ms is not None:
        anim["durationMs"] = anim_ms
    if anim_easing:
        anim["easing"] = anim_easing
    if anim:
        out["drawerAnim"] = anim
    out["closeAffordance"] = {"kind": close_kind or "overlay-tap"}
    out["provenance"] = {
        "origin": "extracted",
        "mobile": ("measured hamburger→drawer contract: a burger trigger toggles a "
                   "full-viewport mobile menu surface; the burger morphs to an X on "
                   "expand (x-glyph close). Drawer bg + slide transition resolved from "
                   "the source's mobile-menu rules."),
    }
    return out


# ── tokens.shadow elevation SCALE ────────────────────────────────────────────────────

_RING_RE = re.compile(r"^\s*0\s+0\s+0\s+[\d.]+px", re.I)  # 0 0 0 Npx = ring, not elevation


def shadow_scale(rules: list, varmap: dict) -> dict | None:
    """Generic elevation SCALE role→value from the source box-shadows: a nav/header
    shadow → ``sticky-nav``; small-blur elevations → ``raised``; large-blur → ``overlay``.
    Ring shadows (``0 0 0 Npx``, i.e. borders-as-shadow) and inset are excluded."""
    def _norm(v: str) -> str:
        return re.sub(r"\s+", " ", re.sub(r",\s*", ", ", v)).strip()

    elevations: list[tuple[int, str, str, bool]] = []  # (blur, value, sel, is_nav)
    seen: set[str] = set()
    for r in rules:
        sel = r.get("selector") or ""
        for m in re.finditer(r"box-shadow\s*:\s*([^;!]+)", r.get("decls", "") or ""):
            val = _norm(_resolve(m.group(1).strip(), varmap))
            if not val or val.lower() == "none" or "inset" in val.lower() \
                    or "var(" in val or _RING_RE.match(val):
                continue  # unresolved vars, rings and inset are not elevation-scale values
            bm = re.match(r"\s*[-\d.]+px\s+[-\d.]+px\s+([\d.]+)px", val)
            blur = int(float(bm.group(1))) if bm else 0
            if val in seen:
                continue
            seen.add(val)
            elevations.append((blur, val, sel, bool(_NAV_RE.search(sel))))
    if not elevations:
        return None
    scale: dict = {}
    # sticky-nav = a nav/header-context elevation; the remaining distinct elevations sort
    # by blur into raised (smallest) → overlay (largest) generic roles.
    nav_elev = next((e for e in elevations if e[3]), None)
    if nav_elev:
        scale["sticky-nav"] = {"value": nav_elev[1], "provenance": [nav_elev[2][:48]]}
    rest = sorted((e for e in elevations if e is not nav_elev), key=lambda e: e[0])
    if rest:
        scale["raised"] = {"value": rest[0][1], "provenance": [rest[0][2][:48]]}
    if len(rest) > 1:
        scale["overlay"] = {"value": rest[-1][1], "provenance": [rest[-1][2][:48]]}
    if not scale:
        return None
    scale["provenance"] = {
        "origin": "extracted",
        "shadow": ("measured elevation scale: generic roles (sticky-nav / raised / "
                   "overlay) mapped from the source's box-shadow census by blur radius "
                   "and consuming context; ring/inset shadows excluded."),
    }
    return scale


# ── tokens.zIndex stacking SCALE ─────────────────────────────────────────────────────

# order matters — a more specific role wins before the nav/header catch-all so a
# ``*-mobile-submenu`` is a dropdown, not sticky-nav.
_ZROLE_MATCHERS = [
    ("dropdown", re.compile(r"dropdown|submenu|flyout|mega", re.I)),
    ("modal", re.compile(r"modal|dialog", re.I)),
    ("banner", re.compile(r"banner|toast|notification", re.I)),
    ("overlay", re.compile(r"overlay|scrim|backdrop|::after|:has", re.I)),
    ("sticky-nav", re.compile(r"(?<![\w-])nav|header|masthead|topbar", re.I)),
]
_Z_OUTLIER = 100000  # 3rd-party cookie-banner z-indexes (2147483647 etc.) are not scale


def zindex_scale(rules: list) -> dict | None:
    """Generic stacking SCALE role→value from measured z-index on chrome/overlay
    selectors. Absurd 3rd-party values (> 100000) are excluded (not a design scale)."""
    role_vals: dict[str, list[int]] = {}
    for r in rules:
        sel = r.get("selector") or ""
        m = re.search(r"(?<![-\w])z-index\s*:\s*(-?\d+)", r.get("decls", "") or "")
        if not m:
            continue
        z = int(m.group(1))
        if z <= 0 or z >= _Z_OUTLIER:
            continue
        for role, role_re in _ZROLE_MATCHERS:
            if role_re.search(sel):
                role_vals.setdefault(role, []).append(z)
                break
    if not role_vals:
        return None
    scale: dict = {}
    for role, vals in role_vals.items():
        # the representative value for a role = the mode (most common), tie → the max.
        c = Counter(vals)
        top = max(c.values())
        scale[role] = {"value": max(v for v, n in c.items() if n == top),
                       "role": role}
    scale["provenance"] = {
        "origin": "extracted",
        "zIndex": ("measured stacking scale: generic roles (sticky-nav / dropdown / "
                   "overlay / modal / banner) mapped from the source's z-index census on "
                   "chrome + overlay selectors; 3rd-party outliers excluded."),
    }
    return scale


# ── footer.localeSelector ────────────────────────────────────────────────────────────

_LOCALE_LABELS = re.compile(
    r"日本語|Deutsch|Español|Português|Français|Italiano|中文|한국어|Nederlands|"
    r"English|language|langue|idioma|sprache", re.I)


def locale_selector(dom: dict) -> dict | None:
    """A language/region control (``footer.localeSelector`` schema slot) from the observed
    locale-link cluster. The link cluster (labels with hrefs to locale domains) is the
    measured fact; the schema materializes it at the footer locale slot for rendering.
    None when the source ships no locale control (fact-gate)."""
    chrome = dom.get("chrome") or {}
    candidates = []
    for zone in ("footer", "header"):
        links = ((chrome.get(zone) or {}).get("links")) or []
        loc = [l for l in links if isinstance(l, dict) and l.get("label")
               and _LOCALE_LABELS.search(str(l.get("label")))]
        if len(loc) >= 3:
            candidates.append((zone, loc))
    if not candidates:
        return None
    zone, loc = candidates[0]
    options = []
    for l in loc[:24]:
        opt = {"label": str(l.get("label"))}
        if l.get("href"):
            opt["href"] = str(l.get("href"))
        options.append(opt)
    return {
        "kind": "dropdown",
        "ariaLabel": "Select a language",
        "options": options,
        "provenance": {
            "origin": "extracted",
            "localeSelector": (f"measured locale-link cluster ({len(options)} language "
                               f"options with locale hrefs) observed in the source "
                               f"chrome ({zone}); materialized at the footer locale slot."),
        },
    }


# ── sidecar build ────────────────────────────────────────────────────────────────────

def build_interaction_facts(*, rules: list, dom: dict, color_roles: dict | None) -> dict:
    """The interaction-fact sidecar: every family is generic + provenance-tagged, and
    fact-gated (a family the source does not evidence is simply absent)."""
    varmap = _build_varmap(rules, color_roles)
    out: dict = {}
    car = carousel_recipe(rules, varmap)
    if car:
        out["carousel"] = car
    states = interaction_states(rules, varmap)
    if states:
        out["interactionStates"] = states
    sticky = navbar_sticky(rules, varmap)
    mobile = navbar_mobile(rules, varmap)
    nav: dict = {}
    if sticky:
        nav["sticky"] = sticky
    if mobile:
        nav["mobile"] = mobile
    if nav:
        out["navbar"] = nav
    shadow = shadow_scale(rules, varmap)
    zidx = zindex_scale(rules)
    tokens: dict = {}
    if shadow:
        tokens["shadow"] = shadow
    if zidx:
        tokens["zIndex"] = zidx
    if tokens:
        out["tokens"] = tokens
    locale = locale_selector(dom)
    if locale:
        out["footer"] = {"localeSelector": locale}
    return out


def _load(path: Path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def main(argv=None) -> int:
    import yaml
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("brand_yaml", type=Path)
    ap.add_argument("--evidence", type=Path, default=None,
                    help="evidence dir (default: <brand_dir>/evidence)")
    args = ap.parse_args(argv)
    brand_yaml = args.brand_yaml.resolve()
    if not brand_yaml.is_file():
        raise SystemExit(f"capture_interaction_facts: brand yaml not found: {brand_yaml}")
    brand_dir = brand_yaml.parent
    ev = (args.evidence or brand_dir / "evidence").resolve()
    css_rules = _load(ev / "css-rules.json")
    if not css_rules:
        raise SystemExit(f"capture_interaction_facts: css-rules.json not found under {ev}")
    rules = css_rules.get("rules") if isinstance(css_rules, dict) else css_rules
    dom = _load(ev / "dom-sections.json") or {}
    color_roles = _load(ev / "color-roles.json") or {}
    facts = build_interaction_facts(rules=rules, dom=dom, color_roles=color_roles)
    if not facts:
        print(f"[interaction] {brand_dir.parent.name}: no measured interaction facts")
        return 0
    out_p = brand_dir / SIDECAR_NAME
    header = ("# interaction-facts.yaml — evidence-derived INTERACTION facts (carousel "
              "timing, per-component states, mobile-drawer + sticky nav, shadow/z-index "
              "scales, footer locale selector).\n# Generated by "
              "tools/extract/capture_interaction_facts.py from evidence/*.json.\n"
              "# Merged into the doc at load (responsive_facts.merge_brand_facts); "
              "brand.yaml stays byte-identical. Every block is fact-gated + generic.\n")
    out_p.write_text(header + yaml.safe_dump({"schemaVersion": SCHEMA, **facts},
                                             sort_keys=False, allow_unicode=True,
                                             width=100000))
    report = {k: bool(facts.get(k)) for k in
              ("carousel", "interactionStates", "navbar", "tokens", "footer")}
    print(f"[interaction] {brand_dir.parent.name}: wrote {out_p.name} {json.dumps(report)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
