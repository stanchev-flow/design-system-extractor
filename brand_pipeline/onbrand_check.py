#!/usr/bin/env python3
"""onbrand_check.py - PASS/FAIL on-brand gate for a rendered section.

Three parts (per task spec):
  1. neverDo violations - parse neverDo from brand.yaml, statically verify the
     rendered HTML/CSS does not violate them.
  2. fidelity vs the source crop - structured checklist of layout / tokens /
     spacing matching the section crop. The script verifies the brand tokens are
     actually present in the render so the comparison is grounded, not vibes.
  3. slop checklist - generic-AI-look failure modes (default fonts, off-palette
     colors, lorem copy, missing brand assets, radius off the brand scale).

GENERALIZATION (2026-06-15): the gate is now brand-agnostic and data-driven.
  - The rendered layout is resolved from the render dir name (`section-<id>`),
    not hardcoded to WoodWave's `opening-bookend`.
  - `neverDo` checks run through a REGISTRY keyed by rule id that supports both
    WoodWave ids (no-radius, no-shadows, no-buttons, ...) AND HubSpot ids
    (no-hard-edges, no-flat-no-depth, no-typographic-only-cta, no-allcaps-display,
    no-serif-body, no-dark-editorial-canvas, ...). Unknown ids fall back to a
    keyword heuristic; if still unverifiable, they report as informational (a
    documented PASS) rather than a false fail.
  - Fidelity + slop are derived from the layout's resolved surface, tokens and
    componentMapping - no per-brand literals (espresso/gold/staircase) remain.

READABILITY (2026-07-01): two mechanical contrast checks joined the composition
invariant set (advisory by default, HARD under --composition) — `text-contrast`
(real text vs its EFFECTIVE background, i.e. the surface composited with any
decoration layer behind it; >=3.0 display-scale, >=4.5 body/small) and
`decoration-salience` (ghost-word/watermark layers must stay close to their
surface: composite-vs-surface contrast ratio <= 1.15). Both are computed
statically by readability.py; see its docstring for the model + thresholds.

TOKEN PROVENANCE (AS-24, 2026-07-03): `token-provenance` joined the same invariant
tier — every visual value in the emitted style blocks (minus the generated
`<style id="tokens">` layer-1 block) must trace to the active brand's token index
(tokens.manifest.json beside the render, else rebuilt from brand.yaml) or carry a
`/* provenance: structural */` allowlist comment. Colors/spacing/radius/type are
errors; duration/easing literals are WARNING severity per DECISIONS.md #3. A
literal matching ANOTHER brand's index is called out as a foreign-brand DNA leak.
Scanner lives in token_provenance.py; the layer-1 generator in tokens_css.py.

Writes onbrand-report.md next to the render and prints an overall verdict.

Usage:
  python3 onbrand_check.py <brand.yaml> <render_dir> [--report onbrand-report.md]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

import yaml

# Two-layer model: the STYLE loader lives beside this gate in brand_pipeline/.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from styles import load_style  # noqa: E402
# READABILITY + DECORATION-SALIENCE (2026-07-01): static contrast analysis for the
# `text-contrast` / `decoration-salience` composition invariants (see readability.py).
import readability  # noqa: E402
# TOKEN PROVENANCE (AS-24, token-layer-2026-07): the raw-literal scanner for the
# `token-provenance` composition invariant (see token_provenance.py + tokens_css.py).
import token_provenance  # noqa: E402

HEX_RE = re.compile(r"#[0-9a-fA-F]{6}")
_SERIF_HINTS = ("serif", "playfair", "didone", "georgia", "times")


def norm_hex(h):
    return h.lower()


# ── boxed-input signature detection (rule, not element) ─────────────────────────
# Phase 1B: `no-boxed-inputs` judges the RULE, not "does an <input> exist". A real,
# functional control (input/textarea/select, or the brand's `.c-field`/`.c-input`
# underline field) is COMPLIANT when it is underline-only (border-bottom / pseudo-element
# rule, radius 0, no fill, no full box) and only VIOLATES when it has a "boxed" look:
# a full `border:` shorthand on all sides, a non-transparent background fill, and/or a
# non-zero border-radius. Decorative pseudo-element underlines (`.c-field::after`) and
# state rules (:hover/:focus/::placeholder) are NOT the box and are skipped.

# input-like control selector: the bare element (input/textarea/select) or the brand's
# underline-field classes. `.c-field-text` (the label span) is handled/skipped by caller.
_CONTROL_SEL_RE = re.compile(
    r"(?:^|[\s,>+~])(?:input|textarea|select)\b|\.c-field\b|\.c-input\b|\.field\b")


def _border_shorthand_visible(val: str) -> bool:
    """True when a `border:` shorthand paints a visible full box (not none / 0-width)."""
    v = re.split(r"[;{}]", val, 1)[0].strip().lower()
    if not v or v in ("none", "inherit", "initial", "unset"):
        return False
    if "none" in v:  # e.g. "0 none" / "medium none"
        return False
    # a leading 0-width (0 / 0px / 0rem ...) means no visible box
    if re.match(r"0(px|rem|em)?(\s|$)", v):
        return False
    return True


def _decl_has_full_border(body: str) -> bool:
    # match `border:` but NOT `border-bottom:`/`border-top:`/`border-radius:`/`border-color:`
    m = re.search(r"(?<![-a-z])border\s*:\s*([^;{}]+)", body)
    return bool(m) and _border_shorthand_visible(m.group(1))


def _decl_has_fill(body: str) -> bool:
    for m in re.finditer(r"(?<![-a-z])background(?:-color)?\s*:\s*([^;{}]+)", body):
        val = m.group(1).strip().lower()
        first = val.split()[0] if val.split() else val
        if val in ("none", "transparent", "inherit", "initial", "unset") or first == "transparent":
            continue
        return True
    return False


def _decl_has_radius(body: str) -> bool:
    for m in re.finditer(r"border-radius\s*:\s*([^;{}]+)", body):
        val = m.group(1).strip()
        if val not in ("0", "0px", "0rem", "0em", "var(--radius)"):
            return True
    return False


def _detect_boxed_inputs(low: str) -> list:
    """Return a list of input-like controls that have a BOXED look (border/fill/radius).

    Empty list => every field is underline-only / unstyled => `no-boxed-inputs` PASSES.
    Conservative by design: only rules whose selector actually targets a control are
    inspected, decorative pseudo/state rules are skipped, and only a POSITIVE box signal
    (full border, non-transparent fill, or non-zero radius) counts as a violation."""
    offenders = []
    for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", low):
        sel = m.group(1).strip()
        body = m.group(2)
        if "::selection" in sel or not _CONTROL_SEL_RE.search(sel):
            continue
        # decorative underline / state rules are not the box itself
        if "::" in sel or ":hover" in sel or ":focus" in sel or ":active" in sel:
            continue
        if "c-field-text" in sel:  # the label span, not the field control
            continue
        sig = []
        if _decl_has_full_border(body):
            sig.append("border")
        if _decl_has_fill(body):
            sig.append("fill")
        if _decl_has_radius(body):
            sig.append("radius")
        if sig:
            offenders.append(f"{sel[:40]} [{'+'.join(sig)}]")
    # inline styles on real controls (e.g. <input style="border:1px solid #000;...">)
    for m in re.finditer(r"<(input|textarea|select)\b([^>]*)>", low):
        sm = re.search(r'style="([^"]*)"', m.group(2))
        if not sm:
            continue
        body = sm.group(1)
        sig = []
        if _decl_has_full_border(body):
            sig.append("border")
        if _decl_has_fill(body):
            sig.append("fill")
        if _decl_has_radius(body):
            sig.append("radius")
        if sig:
            offenders.append(f"<{m.group(1)} inline> [{'+'.join(sig)}]")
    return offenders


# ── load + layout resolution ────────────────────────────────────────────────────

def load(brand_yaml, render_dir):
    doc = yaml.safe_load(Path(brand_yaml).read_text())
    html = (Path(render_dir) / "index.html").read_text()
    return doc, html


def resolve_layout(doc, render_dir, layout_override=None):
    """Resolve the rendered layout.

    ADDITIVE (2026-06-29): an explicit ``layout_override`` (CLI ``--layout``) wins,
    so variant render dirs whose names do NOT encode the layout id (e.g. a/, b/, c/)
    can still resolve to the intended layout (opening-bookend). When absent, behavior
    is unchanged: the layout id is the render dir name minus the ``section-`` prefix.
    """
    if layout_override:
        for l in doc.get("layouts", []):
            if l.get("id") == layout_override:
                return l
        # explicit override that doesn't exist is a hard error (caller mistake)
        raise SystemExit(f"--layout '{layout_override}' not found in brand.yaml")
    name = Path(render_dir).name
    lid = name[len("section-"):] if name.startswith("section-") else name
    for l in doc.get("layouts", []):
        if l.get("id") == lid:
            return l
    # fall back: first layout
    return (doc.get("layouts") or [{}])[0]


def resolve_surface(doc, layout):
    surfaces = doc["tokens"]["surfaces"]
    # ADDITIVE (2026-06-29): the library-agnostic v2 schema names a layout's surface via
    # `surfaceIntent` (a token role) instead of legacy `surfaceRole`/`surfaceMode`. Honor
    # it first; older layouts (no surfaceIntent) fall through to the original resolution.
    role = layout.get("surfaceRole") or layout.get("surfaceIntent")
    if role and role in surfaces:
        return role, surfaces[role]
    mode = (layout.get("surfaceMode") or {}).get("mode")
    for r, s in surfaces.items():
        if s.get("schemeMode") == mode:
            return r, s
    first = next(iter(surfaces))
    return first, surfaces[first]


# ── component/block mapping normalizer (componentMapping OR blockMapping) ────────

def iter_mapping(layout):
    """Yield normalized mapping entries {role, component, props} for fidelity checks.

    ADDITIVE (2026-06-29): the v2 library-agnostic schema describes a layout's contents
    with `blockMapping` (slot/role/contract/usage) instead of the legacy
    `componentMapping` (role/component/props). When componentMapping is present it is
    used unchanged; otherwise blockMapping is normalized so the fidelity rows
    (heading copy / media / actions) stay grounded for the new schema too.
    """
    cm = layout.get("componentMapping")
    if cm:
        for m in cm:
            yield {"role": m.get("role") or "", "component": m.get("component") or "",
                   "props": m.get("props") or {}}
        return
    for m in layout.get("blockMapping") or []:
        contract = (m.get("contract") or "").strip()
        usage = m.get("usage") or {}
        props = {}
        if usage.get("heading"):
            props["Text"] = usage["heading"]
        elif usage.get("Text"):
            props["Text"] = usage["Text"]
        elif usage.get("label"):
            props["Label"] = usage["label"]
        yield {"role": m.get("role") or "", "component": contract.title(), "props": props}


def color_value(doc, token):
    if not token:
        return None
    c = doc["tokens"]["colors"].get(token)
    return c["value"] if c else token


# ── render fact extraction (computed once) ──────────────────────────────────────

def extract_facts(doc, html, layout, render_dir):
    low = html.lower()
    f = {}

    radii = re.findall(r"border-radius:\s*([^;]+);", low)
    f["radii"] = [r.strip() for r in radii]
    f["radius_vars"] = dict(re.findall(r"(--[a-z0-9-]*radius[a-z0-9-]*):\s*([^;]+);", low))
    # EVERY custom-property declaration (last one wins, mirroring the cascade for the
    # common same-specificity case) — the lookup table for var()-chain resolution
    # (fix-batch 2026-07, N6: `var(--button-radius)` must resolve to its 0.5rem layer-1
    # value BEFORE the radius-scale check judges it, not read as an off-scale literal).
    f["css_vars"] = dict(re.findall(r"(--[a-z0-9-]+)\s*:\s*([^;{}]+)", low))
    f["has_zero_radius_ui"] = bool(
        re.search(r"\.(btn|card|hs-|wd-media)[^{}]*\{[^}]*border-radius:\s*0(px|rem)?;", low))

    shadows = [s for s in re.findall(r"box-shadow:\s*([^;]+);", low) if s.strip() != "none"]
    borders = [b for b in re.findall(r"border:\s*([^;]+);", low) if b.strip() not in ("none", "0")]
    f["shadows"] = shadows
    f["borders"] = borders
    f["has_depth"] = bool(shadows or borders)

    # no-gradients counts gradient WASHES (color ramps). A `repeating-*` hard-stop stripe
    # is a flat texture plate, not a wash — the sanctioned AS-23 placeholder backing
    # (.c-image hatch from the surface's own tokens) must not trip a brand's no-gradients
    # neverDo, or every composed page fails the moment an image slot exists.
    f["gradients"] = re.findall(
        r"(?<!repeating-)(linear-gradient|radial-gradient|conic-gradient)\(", low)

    blur_m = re.search(r"filter:\s*blur\(([^)]*)\)", low)
    f["hero_blur"] = blur_m.group(1).strip() if blur_m else None
    f["has_hero_blur"] = bool(blur_m and blur_m.group(1).strip() not in ("0", "0px", "none", ""))
    f["has_button_el"] = "<button" in low
    # filled CTA = a primary button/cta selector that paints a background
    # ELEMENT-level check (anti-ai-slop.md AS-08 history): the shared stylesheet now
    # always carries the `.c-button` RULE; only an element actually USING the class is a
    # filled CTA on this page.
    f["has_filled_cta"] = bool(
        re.search(r'class="[^"]*\b(btn-primary|cta-primary|c-button)\b', low))
    f["has_outline_cta"] = bool(re.search(r"\.(btn-secondary|cta-secondary)", low))

    # display heading uppercase? find a heading-ish selector with uppercase transform
    # (exclude eyebrow/label selectors, where uppercase is sanctioned)
    f["display_uppercase"] = bool(re.search(
        r"\.(hs-heading|wd-heading|is-display|heading)[^{}]*\{[^}]*text-transform:\s*uppercase",
        low))

    fh = re.search(r"--font-heading:\s*'([^']+)'", html)
    fb = re.search(r"--font-body:\s*'([^']+)'", html)
    f["heading_family"] = fh.group(1) if fh else None
    f["body_family"] = fb.group(1) if fb else None
    f["body_is_serif"] = bool(f["body_family"] and
                              any(h in f["body_family"].lower() for h in _SERIF_HINTS))
    f["google_fonts"] = "fonts.googleapis.com" in low
    # Phase 1B: a webfont can be delivered by a CDN <link> OR by a self-hosted @font-face.
    # Both are equally on-brand; the gate must not privilege the CDN delivery mechanism.
    f["self_hosted_fonts"] = "@font-face" in low
    f["webfont_delivered"] = f["google_fonts"] or f["self_hosted_fonts"]

    f["abs_media"] = bool(re.search(r"\.(wd-media|hs-media)[^{}]*\{[^}]*position:\s*absolute", low))
    # card containers ACTUALLY APPLIED to an element (an attribute value), not just a CSS
    # selector rule (`.card { ... }`/`.hs-card { ... }` boilerplate is always emitted in the
    # shared stylesheet regardless of whether any element in THIS section uses it).
    f["has_card_class"] = bool(re.search(r'class="[^"]*\b(card|hs-card)\b', low))
    # accent-styled elements ACTUALLY APPLIED (same distinction: `.c-heading--accent { ... }`
    # is boilerplate; `class="... c-heading--accent"` on a real element is the violation).
    f["has_accent_class"] = bool(re.search(r'class="[^"]*--accent\b', low))
    f["inputs"] = len(re.findall(r"<input[^>]*>", low))
    # Phase 1B: boxed-input signature (the RULE), not the presence of an <input> element.
    f["boxed_inputs"] = _detect_boxed_inputs(low)
    f["hairlines"] = len(re.findall(r"border-(top|bottom):\s*[^;]*(solid|px)", low))
    f["lorem"] = "lorem" in low or "ipsum" in low
    f["centered_count"] = low.count("text-align: center")
    f["has_eyebrow"] = bool(re.search(r"\b(eyebrow)\b", low))

    # off-palette hexes
    allowed = set()
    for c in doc["tokens"]["colors"].values():
        for h in HEX_RE.findall(str(c.get("value", ""))):
            allowed.add(norm_hex(h))
    used = {norm_hex(h) for h in HEX_RE.findall(html)}
    f["allowed_hex"] = allowed
    f["off_palette"] = sorted(used - allowed)

    imgs = re.findall(r'src="([^"]+)"', html) + re.findall(r"url\('([^']+)'\)", html)
    local = [s for s in imgs if not s.startswith("http") and not s.startswith("data:")]
    f["local_imgs"] = local
    f["missing_imgs"] = [s for s in local if not (Path(render_dir) / s).exists()]

    # composer-authored content attributes (alt / aria-label / title) — scanned by the
    # foreign-brand-content slop check (fix-batch 2026-07: a hardcoded
    # `alt="WoodWave editorial photography"` shipped verbatim on another brand's page).
    f["content_attr_texts"] = re.findall(r'(?:alt|aria-label|title)="([^"]*)"', html,
                                         flags=re.I)

    role, surf = resolve_surface(doc, layout)
    f["surface_role"] = role
    f["surface_bg"] = surf.get("bg")
    f["surface_mode"] = (layout.get("surfaceMode") or {}).get("mode")
    # ADDITIVE (2026-06-29): the v2 schema has no per-layout surfaceMode; derive a dark/
    # light mode from the resolved surface role so surface-sensitive checks
    # (no-accent-on-light, no-cards-on-cream, ...) work on the library-agnostic schema.
    if not f["surface_mode"]:
        if role in ("surface/inverse", "surface/inverse-strong", "surface/accent",
                    "surface/overlay"):
            f["surface_mode"] = "Inverse"
        elif role:
            f["surface_mode"] = "Primary"
    _bg = str(surf.get("bg") or "")
    # a DESCRIPTIVE v1 surface value ("image + dark scrim") can never appear as a literal
    # CSS color — the composer substitutes an on-palette dark; requiring the literal here
    # made the check unpassable by design. Non-color surfaces are media surfaces: pass.
    if _bg and not re.match(r"^(#|rgb|hsl)", _bg.strip()):
        f["bg_in_css"] = True
    else:
        f["bg_in_css"] = bool(re.search(rf"--bg:\s*{re.escape(_bg)}", html, re.I)) if _bg else False

    # token-provenance (AS-24): the active render's layer-1 index — the values THIS
    # page was generated against (tokens.manifest.json beside the render). A missing
    # manifest marks a pre-token-layer render: the provenance check reports advisory
    # skip rather than retro-failing pages generated before the layer existed.
    f["token_index"] = token_provenance.load_manifest_index(render_dir)
    return f


# ── neverDo checker registry (brand-agnostic) ────────────────────────────────────

def _ck_no_radius(f, doc, layout, low):
    nonzero = [b for b in f["radii"] if b not in ("0", "0px", "0rem", "var(--radius)")]
    rv = f["radius_vars"].get("--radius")
    rv_ok = rv is not None and rv.strip() in ("0", "0px", "0rem")
    return (not nonzero and rv_ok,
            f"--radius={rv.strip() if rv else 'n/a'}; nonzero literal radii={nonzero or 'none'}")


def _ck_no_hard_edges(f, doc, layout, low):
    rounded = any(v.strip() not in ("0", "0px", "0rem") for v in f["radius_vars"].values()) \
        or any(b not in ("0", "0px", "0rem") for b in f["radii"])
    ok = rounded and not f["has_zero_radius_ui"]
    return (ok, f"rounded radius vars={list(f['radius_vars'].values()) or 'none'}; "
                f"zero-radius UI surface={f['has_zero_radius_ui']}")


def _ck_no_shadows(f, doc, layout, low):
    return (not f["shadows"] and not f["borders"],
            f"box-shadows={f['shadows'] or 'none'}; borders={f['borders'] or 'none'}")


def _ck_no_flat(f, doc, layout, low):
    return (f["has_depth"],
            f"depth present: shadows={f['shadows'] or 'none'}; borders={f['borders'] or 'none'}")


def _ck_no_gradients(f, doc, layout, low):
    return (not f["gradients"], f"gradient functions found={len(f['gradients'])}")


def _ck_no_buttons(f, doc, layout, low):
    ok = not f["has_button_el"] and not f["has_filled_cta"]
    return (ok, f"<button>={f['has_button_el']}; filled CTA bg={f['has_filled_cta']} "
                "(actions are typographic links)")


def _ck_typographic_only_cta(f, doc, layout, low):
    return (f["has_filled_cta"],
            f"filled primary CTA button present={f['has_filled_cta']}; outline secondary={f['has_outline_cta']}")


def _ck_no_allcaps_display(f, doc, layout, low):
    return (not f["display_uppercase"],
            f"display heading uppercased={f['display_uppercase']} (sentence case expected)")


def _ck_no_serif_body(f, doc, layout, low):
    return (not f["body_is_serif"], f"body font family={f['body_family']} (sans expected)")


_GENERIC_FAMILIES = ("serif", "sans-serif", "system-ui", "monospace", "cursive",
                     "fantasy", "ui-sans-serif", "ui-serif", "ui-monospace",
                     "arial", "helvetica", "times", "times new roman", "georgia")


def _ck_no_default_fonts(f, doc, layout, low):
    """Phase 1B: judge ON-BRAND OUTPUT, not the font DELIVERY mechanism.

    PASSES when heading font == brand display family AND body font == brand body family
    AND a webfont is actually delivered — by EITHER a `fonts.googleapis.com` <link> OR a
    self-hosted `@font-face` (the more robust offline path this pipeline prefers). Still
    FAILS when a display/body tier falls back to a default/system/generic family, which is
    the real intent of the rule."""
    bh = doc["tokens"]["type"].get("display-hero", {}).get("family")
    bb = doc["tokens"]["type"].get("control-text", {}).get("family") \
        or doc["tokens"]["type"].get("body", {}).get("family")
    hf = f["heading_family"]
    bf = f["body_family"]
    # a resolved family that is a generic/system keyword is a silent fallback => FAIL
    heading_generic = bool(hf) and hf.strip().lower() in _GENERIC_FAMILIES
    body_generic = bool(bf) and bf.strip().lower() in _GENERIC_FAMILIES
    families_ok = (hf == bh and bf == bb and not heading_generic and not body_generic)
    ok = families_ok and f["webfont_delivered"]
    return (ok, f"heading={hf} (brand {bh}); body={bf} (brand {bb}); "
                f"webfont delivered={f['webfont_delivered']} "
                f"(google-link={f['google_fonts']}, self-hosted @font-face={f['self_hosted_fonts']})")


def _ck_no_off_palette(f, doc, layout, low):
    return (not f["off_palette"],
            f"off-palette={f['off_palette'] or 'none'}; brand palette has {len(f['allowed_hex'])} hexes")


def _ck_no_boxed_inputs(f, doc, layout, low):
    """Phase 1B: judge the RULE (no BOXED look), not the ELEMENT (no <input>).

    A real, correctly underline-styled control (input/textarea/select or the brand's
    `.c-field`/`.c-input` field) PASSES; only a BOXED signature FAILS — a full `border:`
    on all sides, a non-transparent background fill, and/or a non-zero border-radius. The
    deterministic renderer's own underline `.c-field` (radius 0, no fill, pseudo-element
    hairline) and a from-scratch `<input>` styled `border:none;background:transparent`
    both pass; a genuinely boxed `<input>` fails."""
    boxed = f["boxed_inputs"]
    return (not boxed,
            f"boxed input-like controls (border/fill/radius)={boxed or 'none'}; "
            f"raw <input> count={f['inputs']} (underline-only fields are compliant)")


def _ck_no_section_hairlines(f, doc, layout, low):
    return (f["hairlines"] == 0, f"section hairlines={f['hairlines']}")


def _ck_no_cards_on_cream(f, doc, layout, low):
    # Violation ONLY when a card is ACTUALLY rendered on the cream (surface/primary) canvas
    # — a light-surface section with zero cards must PASS. (Fix: the prior `and` conflated
    # "is this section on cream" with "does it have a card", so every surface/primary
    # section failed unconditionally, even with no card present.)
    on_cream = f["surface_role"] == "surface/primary"
    violation = f["has_card_class"] and on_cream
    return (not violation,
            f"surface={f['surface_role']}; card containers={f['has_card_class']}")


def _ck_no_accent_on_light(f, doc, layout, low):
    # Violation ONLY when an accent-styled element is ACTUALLY rendered on a light surface —
    # a light-surface section with zero accent usage must PASS. (Fix: the prior check
    # required the section itself to BE dark, so every light-surface section failed
    # unconditionally, even with no accent color used.)
    light = f["surface_mode"] not in ("Inverse", "Accent Secondary", "Accent Primary")
    violation = light and f["has_accent_class"]
    return (not violation,
            f"section surface mode={f['surface_mode']}; accent-styled elements="
            f"{f['has_accent_class']} (accent sanctioned on dark only)")


def _ck_no_dark_editorial_canvas(f, doc, layout, low):
    sanctioned = f["surface_role"] in ("surface/overlay", "surface/inverse", "surface/accent")
    light = str(f["surface_bg"]).lower() in ("#fcfcfa", "#f8f5ee", "#ffffff")
    ok = sanctioned or light
    return (ok, f"surface={f['surface_role']} (bg {f['surface_bg']}); "
                "dark sanctioned for hero/cta/footer bookends")


def _ck_no_blur_hero(f, doc, layout, low):
    return (not f["has_hero_blur"],
            f"hero background blur filter present={f['has_hero_blur']} "
            f"(value={f['hero_blur'] or 'none'}; flat dark scrim only expected)")


def _ck_no_asymmetric_collage(f, doc, layout, low):
    return (not f["abs_media"],
            f"absolute-positioned overlapping media={f['abs_media']} (grid/split alignment expected)")


def _ck_no_text_on_photos(f, doc, layout, low):
    return (True, "captions live in the margin / display title over media is the sanctioned exception")


def _ck_no_centered_everything(f, doc, layout, low):
    """RECALIBRATED (AS-18): reads the DECLARED anchors (the data-align resolution
    stamps), not the old flex-start heuristic — an accidental left fall-through used to
    read as a PASS signal for asymmetry. A render with no stamps (legacy/unstyled) keeps
    the old sanctioned-centering PASS; a stamped render fails only when the page resolves
    centered nearly everywhere (the actual 'centered-everything' slop)."""
    stamps = re.findall(r'data-align="([^"]+)"', low)
    if not stamps:
        return (True, "no alignment stamps (legacy render) — centering sanctioned for "
                      "bookend / hero / cta stacks")
    centered = sum(1 for s in stamps if s == "centered")
    if len(stamps) >= 4 and centered / len(stamps) > 0.8:
        return (False, f"{centered}/{len(stamps)} sections RESOLVE centered (declared "
                       "anchors, AS-18) — page-wide centering violates prefer-asymmetry")
    return (True, f"declared anchors: {centered}/{len(stamps)} centered, "
                  f"{len(stamps) - centered} anchored/edge — asymmetry is intentional, "
                  "not a flex-start accident")


def _ck_no_missing_eyebrow(f, doc, layout, low):
    has = f["has_eyebrow"] or any("eyebrow" in (m.get("role") or "")
                                  for m in layout.get("componentMapping", []))
    return (has, f"eyebrow/header cluster present={has}")


CHECKERS = {
    # WoodWave (hard-edged editorial) ids
    "no-radius": _ck_no_radius,
    "no-shadows": _ck_no_shadows,
    "no-gradients": _ck_no_gradients,
    "no-buttons": _ck_no_buttons,
    "no-boxed-inputs": _ck_no_boxed_inputs,
    "no-default-fonts": _ck_no_default_fonts,
    "no-section-hairlines": _ck_no_section_hairlines,
    "no-cards-on-cream": _ck_no_cards_on_cream,
    "no-accent-on-light": _ck_no_accent_on_light,
    "no-text-on-photos": _ck_no_text_on_photos,
    "no-centered-everything": _ck_no_centered_everything,
    # HubSpot (rounded SaaS) ids - the near-inverse set
    "no-hard-edges": _ck_no_hard_edges,
    "no-flat-no-depth": _ck_no_flat,
    "no-typographic-only-cta": _ck_typographic_only_cta,
    "no-allcaps-display": _ck_no_allcaps_display,
    "no-serif-body": _ck_no_serif_body,
    "no-dark-editorial-canvas": _ck_no_dark_editorial_canvas,
    "no-asymmetric-collage": _ck_no_asymmetric_collage,
    "no-off-palette": _ck_no_off_palette,
    "no-missing-eyebrow-system": _ck_no_missing_eyebrow,
    # HubSpot `never-*` ids (statically verifiable variants of the above)
    "never-typographic-primary": _ck_typographic_only_cta,
    "never-zero-radius": _ck_no_hard_edges,
    "never-blur-hero": _ck_no_blur_hero,
    "no-hero-blur": _ck_no_blur_hero,
}

# keyword fallback for unknown ids
_KEYWORD_CHECKS = [
    (("radius", "rounded", "hard edge", "hard-edge"), None),  # ambiguous direction -> info
    (("shadow",), None),
    (("gradient",), _ck_no_gradients),
    (("button", "cta"), None),
    (("font", "serif", "sans"), None),
    (("off-palette", "off palette", "palette"), _ck_no_off_palette),
]


def check_neverdo(doc, html, layout, facts, allow=None):
    """Run every neverDo[] rule. ``allow`` is a set of rule ids declared as EXPECTED
    one-off exceptions (CLI ``--allow``): each still runs and reports its TRUE PASS/FAIL,
    but a failure on an allowed rule is flagged ``allowed`` so the report can keep OVERALL
    from flipping to FAIL on a declared exception."""
    allow = allow or set()
    low = html.lower()
    results = []
    for nd in doc.get("neverDo", []):
        rid = nd["id"]
        stmt = nd.get("statement", "")
        fn = CHECKERS.get(rid)
        if fn is not None:
            passed, detail = fn(facts, doc, layout, low)
        else:
            passed, detail = True, "informational: not statically checkable - confirmed by manual visual review"
            for kws, kfn in _KEYWORD_CHECKS:
                if any(k in rid or k in stmt.lower() for k in kws) and kfn is not None:
                    passed, detail = kfn(facts, doc, layout, low)
                    break
        results.append((rid, stmt, passed, detail, rid in allow))
    return results


# ── fidelity (data-driven from layout + tokens) ─────────────────────────────────

def _authored_display_headings(render_dir) -> list[str]:
    """Display-tier heading copy authored by the render's own composition.json
    (creative-mode source of truth). [] when no composition exists / none authored."""
    try:
        comp = json.loads((Path(render_dir) / "composition.json").read_text())
    except (OSError, ValueError, TypeError):
        return []
    out = []
    for sec in (comp.get("sections") or []):
        if not isinstance(sec, dict):
            continue
        for slot in (sec.get("slots") or []):
            if not isinstance(slot, dict):
                continue
            contract = str(slot.get("contract") or "").lower()
            size = str(slot.get("sizeClass") or "").lower()
            if contract == "heading" or size in ("display", "colossal", "hero"):
                c = slot.get("copy")
                txt = c if isinstance(c, str) else \
                    (c.get("heading") or c.get("text") or "") if isinstance(c, dict) else ""
                if str(txt).strip():
                    out.append(str(txt).strip())
    return out


def check_fidelity(doc, html, layout, facts, render_dir=None):
    checks = []
    role, surf = resolve_surface(doc, layout)
    disp = doc["tokens"]["type"].get("display-hero", {})
    disp_family = disp.get("family")
    disp_size = (disp.get("sizeRem", {}) or {}).get("base") if isinstance(disp.get("sizeRem"), dict) else disp.get("sizeRem")

    def has(pat):
        return re.search(pat, html, re.IGNORECASE) is not None

    # CREATIVE-MODE SCOPE (spec/archetype-library.md §3.4): a render whose sections
    # instantiate a genre archetype (``data-archetype`` wrapper stamp) deliberately
    # varies STRUCTURE — and may legitimately vary section surface and copy — while
    # style stays brand-bound. The two SOURCE-IDENTITY cells below therefore re-scope
    # to the law they exist to protect, instead of silently failing on (or being
    # silently skipped for) novel skeletons:
    #   - surface: every rendered section must sit on one of the brand's OWN surface
    #     roles (the data-surface stamps resolve into tokens.surfaces) — not
    #     necessarily the SOURCE layout's surface;
    #   - heading: authored display-tier copy must exist — the SOURCE heading string
    #     is n/a (creative pages author their own voice-true copy).
    # Renders without the stamp (replica + every deterministic lane) keep the original
    # cells byte-identically.
    # fix7 (pass-3 follow-up 9): EVERY generated composition.v1 render takes the
    # creative scope, stamp or no stamp — a pattern-reuse-only composed page authors
    # its own surfaces too, and the old id-coincidence path (a composition section
    # named `hero` binding the SOURCE hero's surface expectations) demanded the
    # source hero surface on pages that never claimed to mirror it. Replicas write
    # replica-composition.v1 and keep the source-identity cells byte-identically.
    creative = 'data-archetype="' in html \
        or _generated_composition(render_dir) is not None

    if creative:
        surf_roles = set(((doc.get("tokens") or {}).get("surfaces") or {}).keys())
        stamped = re.findall(r'data-surface="([^"]+)"', html)
        off_role = sorted({s for s in stamped if s not in surf_roles})
        checks.append(("Surface = a brand surface role (creative-mode scope)",
                       bool(stamped) and not off_role,
                       f"{len(stamped)} section(s) on brand roles; off-role: "
                       f"{off_role or 'none'} — source-surface identity re-scoped for "
                       "archetype-instantiated skeletons"))
    else:
        checks.append((f"Surface = brand {role} ({surf.get('bg')})", facts["bg_in_css"],
                       f"section renders on the brand surface bg {surf.get('bg')}"))

    if disp_family:
        checks.append((f"Display family present ({disp_family})",
                       facts["heading_family"] == disp_family and bool(disp_size and has(r"--display-size:")),
                       f"source display tier is {disp_family} ~{disp_size}rem"))

    entries = list(iter_mapping(layout))

    # heading copy: the render's AUTHORED composition copy in creative mode (the
    # composition.json beside the render is the source of truth — the brand layout's
    # mapping may carry no heading role at all, which used to silently skip this
    # cell while a composer dropped the heading); the SOURCE snippet otherwise.
    def _norm(s):
        # tag-stripping injects a space where an inline device span sits (the fix7
        # punctuation-accent wraps a heading's terminal mark) — whitespace before
        # punctuation is never copy identity, so it normalizes away.
        flat = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s)).strip().lower()
        return re.sub(r"\s+([.,!?;:])", r"\1", flat)

    if creative:
        # every authored display-tier heading must actually RENDER (a composer that
        # drops one is a content failure this cell exists to catch). The heading's
        # TIER/registration is the sibling gate's law (slop AS-32/AS-51 via the
        # headingTier physics family), so no tag-level assertion here.
        authored = _authored_display_headings(render_dir) if render_dir else []
        norm_html = _norm(html)
        missing = [h for h in authored if _norm(h)[:48] not in norm_html]
        checks.append(("Authored display heading present (creative-mode scope)",
                       bool(authored) and not missing,
                       "source-copy identity re-scoped: the composition's own display "
                       f"copy must render — authored {len(authored)}, "
                       f"missing: {[m[:36] for m in missing] or 'none'}"))
    else:
        heading_map = next((m for m in entries
                            if "heading" in (m.get("role") or "")
                            or "title" in (m.get("role") or "")), None)
        if heading_map:
            snippet = (heading_map.get("props", {}).get("Text", "") or "")[:24]
            # tag/whitespace-normalized so split titles (WOODWAVE<br>GALLERY) match
            checks.append(("Heading copy from source present",
                           bool(snippet) and _norm(snippet) in _norm(html),
                           f"source heading begins '{snippet}...'"))

    # accent token surfaced
    accent_tok = surf.get("textAccent")
    if accent_tok:
        av = color_value(doc, accent_tok)
        if creative:
            # creative-mode scope: the opening surface (and so the ``--accent`` root
            # var) is the composition's choice — the brand accent must still be
            # DEPLOYED somewhere on the page (buttons/eyebrow/accent device).
            checks.append((f"Brand accent surfaced ({av})", bool(av) and has(re.escape(av)),
                           f"brand accent {av} deployed in the render "
                           "(root-var identity re-scoped for creative mode)"))
        else:
            checks.append((f"Brand accent surfaced ({av})", has(rf"--accent:\s*{re.escape(av)}"),
                           f"brand accent {av} present in the render"))

    # expected action / media count from the normalized mapping
    n_actions = sum(1 for m in entries
                    if any(k in (m.get("role") or "") for k in ("cta", "button", "primary", "secondary")))
    if n_actions:
        present = (html.lower().count('class="btn') + html.lower().count('c-button')
                   + html.lower().count('c-arrow-link')) >= min(n_actions, 1)
        checks.append((f"Action buttons present (expect {n_actions})", present,
                       f"mapping declares {n_actions} action(s)"))

    n_media = sum(1 for m in entries
                  if (m.get("component") or "") in ("Image",) or "media" in (m.get("role") or "")
                  or "photo" in (m.get("role") or ""))
    if n_media:
        media_ct = html.lower().count("wd-media") + html.count("_source") + len(facts["local_imgs"])
        checks.append((f"Brand media present (expect ~{n_media})", media_ct >= 1,
                       f"componentMapping declares {n_media} media element(s)"))

    checks.append(("Brand assets present (not placeholder)",
                   bool(facts["local_imgs"]) and not facts["missing_imgs"],
                   f"{len(facts['local_imgs'])} local asset(s), missing={facts['missing_imgs'] or 'none'}"))
    return checks


# ── slop checklist (brand-agnostic) ──────────────────────────────────────────────

def _resolve_css_var_chain(value: str, var_map: dict, max_depth: int = 8) -> str:
    """Resolve a `var(--name[, fallback])` chain to its ultimate value using the page's
    OWN custom-property declarations (fix-batch 2026-07, N6). Non-var values pass
    through unchanged; an undeclared name resolves through its fallback (recursively);
    a dead-end/cyclic chain returns the deepest reachable expression (judged as-is)."""
    seen: set[str] = set()
    v = str(value).strip()
    for _ in range(max_depth):
        m = re.fullmatch(r"var\(\s*(--[a-z0-9-]+)\s*(?:,\s*(.+?)\s*)?\)", v, re.I)
        if not m:
            return v
        name, fallback = m.group(1).lower(), m.group(2)
        if name in seen:
            return v
        seen.add(name)
        nxt = var_map.get(name)
        if nxt is None:
            if fallback is None:
                return v
            v = fallback.strip()
        else:
            v = str(nxt).strip()
    return v


_BRAND_NAMES_CACHE: list[str] | None = None


def _known_brand_names() -> list[str]:
    """Names of every extracted brand in the local runs/ corpus (runs/*/brand/brand.yaml).
    The comparison corpus for the foreign-brand-content check — same corpus idea as the
    provenance scanner's foreign-brand VALUE attribution. Cached per process."""
    global _BRAND_NAMES_CACHE
    if _BRAND_NAMES_CACHE is None:
        names = []
        runs = Path(__file__).resolve().parent.parent / "runs"
        if runs.is_dir():
            for by in sorted(runs.glob("*/brand/brand.yaml")):
                try:
                    d = yaml.safe_load(by.read_text()) or {}
                except Exception:
                    continue
                n = ((d.get("brand") or {}).get("name") or "").strip()
                if n and n not in names:
                    names.append(n)
        _BRAND_NAMES_CACHE = names
    return _BRAND_NAMES_CACHE


_BRAND_ASSET_CORPUS_CACHE: dict | None = None
_IMG_EXT_RE = re.compile(r"\.(png|jpe?g|webp|avif|gif|svg)$", re.I)


def _brand_asset_corpus() -> dict:
    """Per-brand image-asset basename inventories for the foreign-brand ASSET check
    (remote-fix 2026-07, AS-34). For each extracted brand: every image basename under
    ``runs/<b>/brand/**`` EXCLUDING ``compose/`` output dirs, plus the top-level
    ``runs/<b>/assets``. ``compose/`` is excluded on purpose: it is the pipeline's own
    composed-page output lane — a foreign file copied there by a buggy run must never
    launder itself into the brand's inventory (self-whitelisting), while the older
    render/variants lanes hold canonical single-section asset copies (WoodWave's
    hero art lives only there). Keyed by lowercase brand name; cached per process."""
    global _BRAND_ASSET_CORPUS_CACHE
    if _BRAND_ASSET_CORPUS_CACHE is None:
        corpus = {}
        runs = Path(__file__).resolve().parent.parent / "runs"
        if runs.is_dir():
            for by in sorted(runs.glob("*/brand/brand.yaml")):
                try:
                    d = yaml.safe_load(by.read_text()) or {}
                except Exception:
                    continue
                name = ((d.get("brand") or {}).get("name") or "").strip().lower()
                if not name:
                    continue
                names = set()
                brand_dir = by.parent
                for p in brand_dir.rglob("*"):
                    if not (p.is_file() and _IMG_EXT_RE.search(p.name)):
                        continue
                    if "compose" in p.relative_to(brand_dir).parts:
                        continue
                    names.add(p.name)
                parent_assets = brand_dir.parent / "assets"
                if parent_assets.is_dir():
                    for p in parent_assets.iterdir():
                        if p.is_file() and _IMG_EXT_RE.search(p.name):
                            names.add(p.name)
                corpus.setdefault(name, set()).update(names)
        _BRAND_ASSET_CORPUS_CACHE = corpus
    return _BRAND_ASSET_CORPUS_CACHE


def check_slop(doc, html, layout, facts):
    checks = []
    fam = facts["heading_family"]
    checks.append(("No default/system display font",
                   bool(fam and fam not in ("Arial", "Helvetica", "sans-serif", "Times", "serif")),
                   f"display font={fam or 'MISSING'}"))

    checks.append(("No off-palette hex colors", not facts["off_palette"],
                   f"off-palette={facts['off_palette'] or 'none'}; brand palette has {len(facts['allowed_hex'])} hexes"))

    checks.append(("No lorem/placeholder copy", not facts["lorem"],
                   "real brand copy from the source inventory"))

    checks.append(("All brand image assets present", not facts["missing_imgs"],
                   f"local images={len(facts['local_imgs'])}; missing={facts['missing_imgs'] or 'none'}"))

    # rounding consistent with the brand radius scale. var()-chain-AWARE (fix-batch
    # 2026-07, N6): a radius alias that REFERENCES another custom property (e.g.
    # `--c-button-radius: var(--button-radius)` → layer-1 `--button-radius: 0.5rem`)
    # is resolved through the page's own declarations before being judged — an alias
    # chain into an on-scale token is the token architecture working, not off-scale.
    brand_radii = set()
    for k, s in doc["tokens"]["spacing"].items():
        if "radius" in k:
            brand_radii.add(str(s.get("value", "")).strip())
    # radius can live in a dedicated tokens.radius scale (rounded systems); include it.
    for s in (doc.get("tokens", {}).get("radius", {}) or {}).values():
        if isinstance(s, dict) and s.get("value"):
            brand_radii.add(str(s.get("value")).strip())
    var_map = facts.get("css_vars") or {}
    # measured chrome interaction radii (--chrome-*, e.g. the nav-link hover wash pill)
    # are EXTRACTED evidence straight from the layer-1 manifest, not composer-invented
    # rounding — the token-provenance invariant (AS-24) already vouches for them, so
    # they are exempt from the design radius SCALE the way 0 is (nav-fix 2026-07).
    var_vals = [v.strip() for k, v in facts["radius_vars"].items()
                if not k.startswith("--chrome-")]
    resolved = [_resolve_css_var_chain(v, var_map) for v in var_vals]

    def _rem(v):
        """px/rem length → float rem for VALUE comparison (a measured 40px chrome
        radius IS the brand's 2.5rem step; unit spelling is not a scale violation)."""
        m = re.fullmatch(r"([\d.]+)(px|rem)", str(v).strip())
        if not m:
            return None
        return float(m.group(1)) / (16.0 if m.group(2) == "px" else 1.0)
    brand_rems = {r for r in (_rem(b) for b in brand_radii) if r is not None}

    def _on_scale(res):
        if res in brand_radii or res in ("0", "0px", "0rem"):
            return True
        r = _rem(res)
        return r is not None and any(abs(r - b) < 1e-6 for b in brand_rems)
    bad = [f"{orig} -> {res}" if orig != res else orig
           for orig, res in zip(var_vals, resolved) if not _on_scale(res)]
    checks.append(("Rounding matches brand radius scale", not bad,
                   f"radius vars={var_vals or 'none'}; brand scale={sorted(brand_radii) or 'none'}; off-scale={bad or 'none'}"))

    # foreign-brand content literals (fix-batch 2026-07): composer-authored content
    # attributes (alt/aria-label/title) must never carry ANOTHER extracted brand's name —
    # that is composer DNA leaking between brands (the content-attribute twin of the
    # provenance scanner's foreign-brand VALUE callout). Names come from the local
    # runs/*/brand corpus; the active brand's own name (under any label) is exempt.
    active_name = ((doc.get("brand") or {}).get("name") or "").strip().lower()
    foreign_hits = []
    for other in _known_brand_names():
        ol = other.lower()
        if active_name and (ol in active_name or active_name in ol):
            continue  # the active brand under any label
        toks = [other] + ([other.split()[0]] if len(other.split()[0]) >= 4 else [])
        pat = re.compile("|".join(re.escape(t) for t in toks), re.I)
        hits = [t for t in facts.get("content_attr_texts", []) if pat.search(t)]
        if hits:
            foreign_hits.append(f"'{other}' in {hits[:2]}")
    checks.append(("No foreign-brand content literals (alt/aria/title)", not foreign_hits,
                   f"foreign brand names in content attributes={foreign_hits or 'none'}"))

    # foreign-brand ASSET references (remote-fix 2026-07, AS-34): every locally
    # referenced image must trace to the ACTIVE brand's own asset inventory. A name
    # that is absent from the active brand but IS another extracted brand's asset is
    # composer/adapter DNA leaking between brands (the file-level twin of the content-
    # literal check above — e.g. WoodWave hero art shipped as a fallback on Remote).
    # Names the active brand owns are exempt even if a sibling shares the same name.
    corpus = _brand_asset_corpus()
    own = corpus.get(active_name, set()) if active_name else set()
    if not own:  # brand label variants (e.g. "WoodWave Gallery" vs dir name)
        for bname, names in corpus.items():
            if active_name and (bname in active_name or active_name in bname):
                own = own | names
    foreign_assets = []
    for ref in facts.get("local_imgs", []):
        base = ref.split("?")[0].rstrip("/").split("/")[-1]
        if not base or base in own:
            continue
        owners = [b for b, names in corpus.items()
                  if base in names
                  and not (active_name and (b in active_name or active_name in b))]
        if owners:
            foreign_assets.append(f"{base} (owned by {'/'.join(sorted(owners))})")
    checks.append(("No foreign-brand asset references", not foreign_assets,
                   f"foreign-owned image refs={foreign_assets or 'none'}"))

    # Phase 1B: a self-hosted @font-face is a webfont too — don't count it as slop.
    checks.append(("Webfonts loaded (no silent system fallback)", facts["webfont_delivered"],
                   f"webfont delivered={facts['webfont_delivered']} "
                   f"(google-link={facts['google_fonts']}, self-hosted @font-face={facts['self_hosted_fonts']})"))
    return checks


# ── composition invariants (Phase 1B: AI-authored composition.v1 drift) ─────────
# These target drift that a from-scratch / AI author can introduce and that the visual
# neverDo checks don't catch (a smuggled second accent, bespoke non-vocabulary markup,
# arbitrary spacing, malformed composition metadata, unresolved slots). They are GATED:
# advisory WARN by default (so the existing deterministic pages never regress) and HARD
# (they gate OVERALL) only under the explicit ``--composition`` opt-in. Auto-detection via
# a present ``data-pattern`` attribute is deliberately NOT used to flip them hard, because
# the existing composed WoodWave pages already carry ``data-pattern`` and must stay PASS.

# vocabulary prefixes the deterministic renderer emits (component_render `c-*` SSOT +
# the composer's structural/state helpers). A class outside these is bespoke markup.
_VOCAB_PREFIXES = ("c-", "cs-", "is-", "has-", "hv-", "sr-", "u-")


def check_composition(doc, html, layout, facts):
    """Return [(id, label, passed, detail)] for the composition.v1 drift invariants."""
    low = html.lower()
    checks = []

    # 1. single-accent — accent appears at most once (brand neverDo `no-accent-*`).
    accent_hits = re.findall(r'class="[^"]*--accent\b', low)
    n_accent = len(accent_hits)
    checks.append(("single-accent", "Single accent element/role (accent used once)",
                   n_accent <= 1,
                   f"accent-role elements applied={n_accent} (<=1 expected per brand no-accent-* rule)"))

    # 2. primitive-only usage — every element carries a c-* SSOT class from the render
    #    vocabulary; a class outside the vocabulary flags bespoke smuggled markup.
    classes = set()
    for cm in re.findall(r'class="([^"]*)"', html):
        classes.update(cm.split())
    bespoke = sorted(c for c in classes
                     if c and not any(c.startswith(p) for p in _VOCAB_PREFIXES))
    more = f" (+{len(bespoke) - 8} more)" if len(bespoke) > 8 else ""
    checks.append(("primitive-only", "All elements use the c-* SSOT vocabulary (no bespoke markup)",
                   not bespoke, f"non-vocabulary classes={bespoke[:8] or 'none'}{more}"))

    # 3. rhythm adherence — section gaps/padding resolve to a step of the brand spacing
    #    scale (a var()/clamp() is scale-driven; a bare rem/px off the scale is arbitrary).
    scale = set()
    for _k, s in (doc.get("tokens", {}).get("spacing", {}) or {}).items():
        v = str((s or {}).get("value", "")).strip()
        if v:
            scale.add(v)
    off_rhythm = []
    # scan comment-free CSS: the selector-side capture ([^{}]+ back to the previous
    # brace) otherwise swallows preceding comment PROSE, and any comment mentioning
    # "section" turned an unrelated rule into a section-rhythm candidate.
    low_nc = re.sub(r"/\*.*?\*/", " ", low, flags=re.S)
    for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", low_nc):
        sel = m.group(1).strip()
        if not re.search(r"(?:^|[\s,>+~])section\b|\.cs-sec|\.cs-section|\[data-pattern|\[data-composition", sel):
            continue
        for prop in ("gap", "row-gap", "padding", "padding-top", "padding-bottom"):
            for dm in re.finditer(rf"(?<![-a-z]){prop}\s*:\s*([^;{{}}]+)", m.group(2)):
                for tok in dm.group(1).strip().split():
                    if re.fullmatch(r"\d*\.?\d+(px|rem|em)", tok) \
                            and tok not in scale and tok not in ("0", "0px", "0rem"):
                        off_rhythm.append(f"{sel[:24]}:{prop}={tok}")
    off_rhythm = sorted(set(off_rhythm))
    more = f" (+{len(off_rhythm) - 6} more)" if len(off_rhythm) > 6 else ""
    checks.append(("rhythm", "Section gaps/padding resolve to the brand spacing scale",
                   not off_rhythm,
                   f"off-scale section spacing={off_rhythm[:6] or 'none'}{more}; "
                   f"brand scale={sorted(scale) or 'none'}"))

    # 4. data-composition round-trip — when present, the metadata must be well-formed
    #    (Phase 1B: shape/coherence only; full JSON round-trip is Phase 4).
    comp_attrs = re.findall(r'data-(?:composition|pattern)="([^"]*)"', html)
    incoherent = []
    for v in comp_attrs:
        vs = v.strip()
        if not vs:
            incoherent.append("(empty)")
        elif vs[0] in "{[":
            try:
                json.loads(vs)
            except Exception:
                incoherent.append(vs[:40])
        elif not re.fullmatch(r"[a-z0-9][a-z0-9._-]*", vs, re.I):
            incoherent.append(vs[:40])
    checks.append(("data-composition", "data-composition/pattern metadata is well-formed",
                   not incoherent,
                   f"attrs present={len(comp_attrs)}; incoherent={incoherent or 'none'}"))

    # 5. slot-resolution completeness — zero `<!-- unresolved slot -->` comments.
    unresolved = low.count("unresolved slot")
    checks.append(("slot-resolution", "Zero unresolved slots",
                   unresolved == 0, f"unresolved-slot markers={unresolved}"))

    # 6+7. READABILITY + DECORATION-SALIENCE (2026-07-01) — mechanical contrast checks
    #    that catch "decorative layer brighter than the text" slop (the v4 ghost-hero
    #    failure: a near-cream WOODWAVE watermark on the dark hero surface loud enough
    #    to drown the gold heading, which nothing in the gate measured until now).
    #    Both are computed STATICALLY from the emitted CSS custom properties + class
    #    structure by readability.py (DOM-lite + CSS-cascade-lite + var resolution);
    #    elements that cannot be confidently resolved are SKIPPED, never failed. Same
    #    tier as the other composition invariants: advisory WARN by default, HARD under
    #    --composition.
    try:
        analysis = readability.analyze(html, default_bg=facts.get("surface_bg"))
        # fidelity-over-floor (fix-batch 2026-07): the brand's own MEASURED component
        # pairs (buttons.primary/secondary fg-on-bg from brand.yaml) are exempt from the
        # generic WCAG-ish floor — this invariant targets AI drift, and a provenance-
        # verified measured pair is brand truth (real brands ship sub-AA primaries).
        # Any non-measured low-contrast pairing still fails.
        measured_pairs = []
        for fam in ("primary", "secondary"):
            b = ((doc.get("buttons") or {}).get(fam) or {})
            fg = b.get("fg") or b.get("label") or b.get("color")
            bg = b.get("bg") or b.get("background")
            if fg and bg:
                measured_pairs.append((str(fg), str(bg)))
        # same doctrine for the brand's authored LINK token on its own authored
        # LIGHT surface roles: a provenance-verified text/link color on a
        # provenance-verified canvas is brand truth (real sites ship their one
        # link blue on every light band they own). Dark surfaces are excluded —
        # they carry their own -on-inverse twins. Any non-authored pairing
        # (wrong hue, wrong surface) still fails the floor.
        _link = ((doc.get("tokens") or {}).get("colors") or {}).get("text/link")
        _link_val = _link.get("value") if isinstance(_link, dict) else _link
        if _link_val:
            for surf in (((doc.get("tokens") or {}).get("surfaces") or {}).values()):
                if isinstance(surf, dict) and not surf.get("textAccent") and surf.get("bg"):
                    measured_pairs.append((str(_link_val), str(surf["bg"])))
        # (the fid15 measured-pair exemption for the CHROME banner is gone — W1,
        # stress-playbook 2026-07: the illegible pairing wasn't brand truth, it was a
        # capture artifact — a translucent declaration stored WITHOUT its live
        # backdrop. The extractor/bridge now resolve backdrop-aware paint
        # (utilityBanner.bg is the composited screen-truth color, bgRaw keeps the
        # declaration), so the banner passes the same floor as everything else and a
        # future mis-extracted chrome color fails LOUDLY instead of being exempted.)
        tc_pass, tc_detail = readability.check_text_contrast(
            html, analysis=analysis, measured_pairs=measured_pairs)
        ds_pass, ds_detail = readability.check_decoration_salience(html, analysis=analysis)
    except Exception as exc:  # static analysis must never crash the gate
        analysis = None
        tc_pass, tc_detail = True, f"static analysis unavailable ({type(exc).__name__}: {exc})"
        ds_pass, ds_detail = True, tc_detail
    checks.append(("text-contrast",
                   "Real text clears WCAG-ish contrast vs its effective background "
                   f"(display >= {readability.TEXT_CONTRAST_DISPLAY_MIN}, "
                   f"body >= {readability.TEXT_CONTRAST_BODY_MIN})",
                   tc_pass, tc_detail))
    checks.append(("decoration-salience",
                   "Decoration layers (ghost/watermark) stay close to their surface "
                   f"(composite-vs-surface ratio <= {readability.DECOR_SALIENCE_MAX_RATIO})",
                   ds_pass, ds_detail))

    # 8. OCCLUSION CONTRACT (G8, editorial-harvest-2026-07) — type-behind-media and any
    #    z:back straddle render REAL heading copy partially behind media. Legal ONLY when
    #    (i) the occluded glyph-area fraction stays within the declared maxOcclusion
    #    budget (light≈0.25 / medium≈0.40 / heavy≈0.55) and (ii) the word's first/last
    #    letterforms stay clear (endsVisible). The composer stamps the RAW grid geometry
    #    (data-occlusion-geom) alongside its estimate; the gate RECOMPUTES the estimate
    #    from that geometry rather than trusting the stamp. Over budget => the section
    #    must reclassify the word as a ghost-word (decorative) + carry a readable heading.
    occ_pass, occ_detail = _check_occlusion(html)
    checks.append(("occlusion",
                   "Occluded headings (type-behind-media / z:back straddle) honor "
                   "maxOcclusion + endsVisible (G8 contract)",
                   occ_pass, occ_detail))

    # 9. BAND ATTRIBUTION (G9) — a 'banded' dual-surface section must declare its two
    #    band surfaces and scope each band's tokens (data-band-surface + inline surface
    #    vars), so surface-dependent checks + readability attribute content to the band
    #    it sits on (straddlers to both) instead of the section's single surface.
    band_pass, band_detail = _check_bands(html)
    checks.append(("band-attribution",
                   "Banded sections declare + scope both band surfaces (seam contract)",
                   band_pass, band_detail))

    # 10. ALIGNMENT RESOLUTION (G10, AS-18) — on a style that declares an alignment
    #     stance, every section wrapper must carry the resolution stamp
    #     (data-align + data-align-source): a missing stamp IS the silent CSS
    #     fall-through this batch outlawed. An asymmetric (left/right) anchor must name
    #     its counterweight device; out-of-enum anchors fail.
    al_pass, al_detail = _check_alignment_resolution(html)
    checks.append(("alignment-resolution",
                   "Every section's alignment is resolved + source-stamped "
                   "(section|curation|pattern|brand|style); asymmetric anchors "
                   "carry a counterweight",
                   al_pass, al_detail))

    # 11. MEDIA REGISTRATION (G11, AS-19) — a section that RESOLVES centered must place
    #     its statement/quote media on a symmetric span: the 6/-1 editorial offset under
    #     centered text was the 'What we hold' misregistration.
    mr_pass, mr_detail = _check_media_registration(html)
    checks.append(("media-registration",
                   "Resolved-centered sections place split media symmetrically "
                   "(offset spans require a side anchor / counterweight)",
                   mr_pass, mr_detail))

    # 12. INTERACTION CONTRAST (AS-20) — statically-resolvable :hover colors, resolved
    #     in the element's OWN token scope, must clear contrast vs the element's OWN
    #     surface (card/panel bg, not the section bg). Gold-on-cream fails mechanically;
    #     the measured dark-footer gold hover passes untouched.
    try:
        ic_pass, ic_detail = readability.check_link_hover_contrast(
            html, default_bg=facts.get("surface_bg"), analysis=analysis)
    except Exception as exc:  # static analysis must never crash the gate
        ic_pass, ic_detail = True, f"hover analysis unavailable ({type(exc).__name__}: {exc})"
    checks.append(("interaction-contrast",
                   "Hover/interaction colors re-scope per surface mode and clear "
                   "contrast vs their OWN surface (incl. cards/panels)",
                   ic_pass, ic_detail))

    # 13. TOKEN PROVENANCE (AS-24, token-layer-2026-07) — every visual value in the
    #     emitted style blocks (minus the generated <style id="tokens"> block) must
    #     trace to the ACTIVE brand's token index or a `/* provenance: structural */`
    #     allowlist comment. A literal that matches ANOTHER brand's index gets the
    #     foreign-brand callout (the DNA-leak smoking gun). Duration/easing literals
    #     are WARNING severity (DECISIONS.md #3): carried in the detail, never
    #     flipping the row.
    tp_pass, tp_detail = _check_token_provenance(doc, html, facts)
    checks.append(("token-provenance",
                   "All emitted visual values trace to the brand token index "
                   "(raw literals need a structural allowlist comment)",
                   tp_pass, tp_detail))

    # 14. LOGO-WALL INTEGRITY (G14, AS-33) — a logo-wall-role section renders REAL
    #     disk-backed logo images (non-empty, metadata-derived alts) or the declared
    #     text-caption fallback; an empty logo frame, a broken/missing logo src, or an
    #     alt-less mark fails. Vacuous pass on pages with no stamped logo walls.
    lw_pass, lw_detail = _check_logo_wall(html, facts)
    checks.append(("logo-wall-integrity",
                   "Logo walls carry disk-backed logo images or text captions "
                   "(never empty frames, broken srcs, or alt-less marks)",
                   lw_pass, lw_detail))

    return checks


# ── archetype physics bindings (spec/archetype-library.md §3.4 / PHASE2 §3) ─────────
# A composition section that instantiated a genre archetype (``archetypeRef`` +
# the rendered ``data-archetype`` stamp) carries a physics CHECKLIST — the fact
# families that must bind. This check maps each family to the checks that verify it:
# families verified INSIDE this gate consult those rows' outcomes; families verified
# by a SIBLING gate are reported as delegated (the lane runner enforces those gates'
# exit codes — spacing_audit for the measured-ladder families, slop_audit for the
# AS action-group/grid rules, interaction_audit for device contracts). No new physics
# is invented here: the bindings list only selects which existing checks are MANDATORY
# for that section. Fact-gated: no composition.json / no archetypeRef -> no rows.
_PHYSICS_INTERNAL = {           # family -> composition-invariant row ids (inv)
    "headerContext": ("alignment-resolution",),
    "relationalRhythm": ("rhythm",),
    "surfaceContrast": ("text-contrast",),
    "textOnMedia": ("text-contrast", "occlusion"),
    "interaction": ("interaction-contrast",),
}
_PHYSICS_FIDELITY = {           # family -> fidelity row label prefixes (fid)
    "assetFidelity": ("All brand image assets present", "Brand assets present"),
}
_PHYSICS_DELEGATED = {          # family -> the sibling gate that owns it
    "containment": "spacing_audit (container law)",
    "stackMeasure": "spacing_audit (measure cells)",
    "headingTier": "slop_audit (AS-32/AS-51)",
    "actionGroup": "slop_audit (AS-59/AS-60/AS-61)",
    "gridEqualize": "slop_audit (AS-44/AS-50)",
    "controlMeasure": "slop_audit (AS-26) + interaction_audit",
    "motion": "interaction_audit (reduced-motion posture)",
}


def check_archetype_physics(render_dir, html, inv, fid):
    """Return extra composition-invariant rows for archetype-instantiated sections.
    ``inv``/``fid`` are the already-computed rows this maps onto."""
    comp_path = Path(render_dir) / "composition.json"
    if not comp_path.exists():
        return []
    try:
        comp = json.loads(comp_path.read_text())
    except (OSError, json.JSONDecodeError):
        return []
    sections = [s for s in (comp.get("sections") or [])
                if isinstance(s, dict) and s.get("archetypeRef")]
    if not sections:
        return []

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import archetype_library as al  # noqa: E402  (data loader — no archetype ids in code)

    inv_by_id = {rid: bool(p) for rid, _label, p, _d in (inv or [])}
    fid_rows = [(label, bool(p)) for label, p, _d in (fid or [])]
    rows = []
    for sec in sections:
        ref = str(sec.get("archetypeRef"))
        sid = str(sec.get("id") or sec.get("useCase") or "section")
        rid = f"archetype-physics:{sid}"
        stamped = f'data-archetype="{ref}"' in html
        if not stamped:
            rows.append((rid, f"Archetype physics bindings ({ref})", True,
                         "demoted at adaptation (fail-closed fallback to the brand's "
                         "own hero anatomy) — no bindings to verify"))
            continue
        art = al.find_archetype(ref)
        if art is None:
            rows.append((rid, f"Archetype physics bindings ({ref})", False,
                         "rendered section stamps an archetype no genre library "
                         "carries — skeleton unverifiable"))
            continue
        bits, ok = [], True
        for fam in al.physics_checklist(art):
            if fam in _PHYSICS_INTERNAL:
                ids = _PHYSICS_INTERNAL[fam]
                passed = all(inv_by_id.get(i, True) for i in ids)
                ok &= passed
                bits.append(f"{fam}:{'ok' if passed else 'FAIL'}"
                            f"({','.join(ids)})")
            elif fam in _PHYSICS_FIDELITY:
                prefixes = _PHYSICS_FIDELITY[fam]
                passed = all(p for label, p in fid_rows
                             if any(label.startswith(x) for x in prefixes))
                ok &= passed
                bits.append(f"{fam}:{'ok' if passed else 'FAIL'}(fidelity)")
            else:
                bits.append(f"{fam}:delegated[{_PHYSICS_DELEGATED.get(fam, 'lane gates')}]")
        rows.append((rid, f"Archetype physics bindings ({ref})", ok, "; ".join(bits)))
    return rows


def _generated_composition(render_dir) -> dict | None:
    """The render's own composition.json when it is a GENERATED composition.v1
    (the replica assembler's replica-composition.v1 and composition-less lanes
    return None — those lanes keep every source-identity cell byte-identically)."""
    if not render_dir:
        return None
    try:
        comp = json.loads((Path(render_dir) / "composition.json").read_text())
    except (OSError, ValueError, TypeError):
        return None
    if isinstance(comp, dict) and comp.get("schemaVersion") == "composition.v1":
        return comp
    return None


def check_composition_lints(render_dir):
    """Composition-lint rows (fix7 AS-63/AS-65 — brand_pipeline/composition_lint.py):
    knob-consumption (every declared knob has a consumer and a renderable value)
    + sibling-slot content redundancy. HARD under --composition like every other
    composition invariant; [] for lanes without a generated composition."""
    comp = _generated_composition(render_dir)
    if comp is None:
        return []
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import composition_lint  # noqa: E402
    hits = composition_lint.lint_composition(comp)
    rows = []
    for rule in ("knob-consumption", "content-redundancy"):
        mine = [(sid, msg) for sid, r, msg in hits if r == rule]
        label = ("Every declared knob has a consumer (AS-63)"
                 if rule == "knob-consumption" else
                 "No sibling-slot content redundancy (AS-65)")
        detail = "; ".join(f"{sid}: {msg}" for sid, msg in mine[:4]) \
            or "composition lints clean"
        rows.append((rule, label, not mine, detail))
    return rows


def check_media_bindings(render_dir, comp=None):
    """Media-binding rows (media semantics 2026-07 — brand_pipeline/
    media_semantics.py, spec/media-assets-schema.md §6/§7): every media-bearing slot
    resolves an asset or carries an explicit noCompatibleAsset {reason} (no silent
    drops — this repo's #1 recurring defect class), declared refs resolve into the
    brand's media-assets.v1 registry, placeholder recipes are licensed, and
    third-party marks obey AS-67. DOUBLY fact-gated: [] for lanes without a
    generated composition AND for brands without media-assets.yaml (pre-media
    lanes/brands never retro-fail)."""
    comp = comp if comp is not None else _generated_composition(render_dir)
    if comp is None:
        return []
    ref = str(((comp.get("brand") or {}) or {}).get("ref") or "")
    if not ref:
        return []
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import media_semantics as ms  # noqa: E402
    registry = ms.load_media_assets(Path(ref).parent)
    if registry is None:
        return []
    hits = ms.lint_media_bindings(comp, registry)
    rows = []
    for rule, label in (("media-binding",
                         "Every media slot resolves or declares its gap"),
                        ("mark-legality",
                         "Third-party marks in factual proof contexts only (AS-67)")):
        mine = [(sid, msg) for sid, r, msg in hits if r == rule]
        detail = "; ".join(f"{sid}: {msg}" for sid, msg in mine[:4]) \
            or "media bindings clean"
        rows.append((rule, label, not mine, detail))
    return rows


_RUNS_ROOT = Path(__file__).resolve().parent.parent / "runs"


def _check_token_provenance(doc, html, facts):
    """(passed, detail) for the token-provenance invariant.

    Scans ONLY manifest-carrying renders: tokens.manifest.json is the proof the page
    was generated through the layer-1 path, and its index holds the exact values the
    page was generated against. Pre-token-layer renders (no manifest) skip advisory —
    retro-failing them would regress every regate baseline without a defect."""
    try:
        index = facts.get("token_index")
        if not index:
            return True, ("no tokens.manifest.json beside render (pre-token-layer "
                          "page) — advisory skip; regenerate to enable the scan")
        brand = ((doc.get("brand") or {}).get("name")) or "brand"
        foreign = token_provenance.foreign_brand_indexes(_RUNS_ROOT, brand)
        res = token_provenance.check_token_provenance(
            html, index, brand=brand, foreign_indexes=foreign)
        return res["passed"], res["detail"]
    except Exception as exc:  # static scan must never crash the gate
        return True, f"provenance scan unavailable ({type(exc).__name__}: {exc})"


# ── G14 logo-wall integrity (AS-33) ──────────────────────────────────────────────────

def _check_logo_wall(html, facts):
    """(passed, detail) for the logo-wall-integrity invariant (AS-33).

    The generic-flow composer stamps every logo-wall-role section with its RESOLVED
    device (``data-logo-device="image|text|empty"``). The contract this verifies:
      - ``image``: the section carries >=1 real ``.c-logo-img`` whose src is non-empty
        AND present on disk (cross-referenced against facts['missing_imgs'], the
        gate's own disk scan) AND whose alt is non-empty (metadata-derived, AS-29);
      - ``text``: the section carries >=1 non-empty caption/eyebrow text (the declared
        text-caption fallback device);
      - ``empty``: always a failure — a logo wall with neither usable images nor text
        is an empty frame (the AS-11 shape, scoped to this device).
    Pages with no stamped logo-wall sections pass vacuously (pre-device renders never
    retro-fail)."""
    problems = []
    missing = set(facts.get("missing_imgs") or [])
    stamped = 0
    for seg in re.split(r"(?=<section\b)", html):
        m = re.match(r'<section\b[^>]*\bdata-logo-device="([^"]+)"', seg)
        if not m:
            continue
        stamped += 1
        mode = m.group(1)
        body = seg.split("</section>")[0]
        imgs = re.findall(r'<img\b[^>]*class="[^"]*c-logo-img[^"]*"[^>]*>', body)
        if mode == "empty":
            problems.append("logo-wall section rendered neither logo images nor text")
        elif mode == "image":
            if not imgs:
                problems.append("image-device logo wall carries no .c-logo-img")
            for tag in imgs:
                src = (re.search(r'\bsrc="([^"]*)"', tag) or [None, ""])[1]
                alt = (re.search(r'\balt="([^"]*)"', tag) or [None, ""])[1]
                if not (src or "").strip():
                    problems.append("logo image with empty src")
                elif src in missing:
                    problems.append(f"logo src missing on disk: {src}")
                if not (alt or "").strip():
                    problems.append(f"logo image missing alt (src={src or '?'})")
        elif mode == "text":
            caps = re.findall(r'<p\b[^>]*class="[^"]*c-(?:caption|eyebrow)[^"]*"[^>]*>'
                              r"([^<]*)</p>", body)
            if not any(c.strip() for c in caps):
                problems.append("text-device logo wall carries no caption text")
        else:
            problems.append(f"unknown logo device stamp '{mode}'")
    if stamped == 0:
        return True, "no logo-wall sections on this page"
    more = f" (+{len(problems) - 6} more)" if len(problems) > 6 else ""
    return (not problems,
            f"logo-wall sections={stamped}; problems={problems[:6] or 'none'}{more}")


# ── G10 alignment resolution (AS-18) ─────────────────────────────────────────────────

_SEC_WRAPPER_RE = re.compile(r'<div\b[^>]*\bid="sec-\d+"[^>]*>')
_ATTR_RE = re.compile(r'([a-zA-Z-]+)="([^"]*)"')
_ALIGN_ENUM = ("centered", "left", "right", "space-between", "edge-to-edge", "mixed")


def _style_declares_alignment(html) -> bool:
    """True when the render's OPERATIVE style declared a machine-readable alignment
    stance. Style-less renders (or an unloadable style) never gate on stamps.

    Preferred source: the composer's own `data-align-stance` stamp on <html> (AS-18 —
    a page rendered against a snapshotted styles_dir must be judged by the definition
    it rendered with; re-loading today's styles/<id>.md by name would demand stamps the
    operative style never declared). Legacy pages without the stamp fall back to
    loading the style by id."""
    m = re.search(r'<html\b[^>]*\bdata-align-stance="([^"]+)"', html)
    if m:
        return m.group(1) == "declared"
    m = re.search(r'<html\b[^>]*\bdata-style="([^"]+)"', html)
    if not m:
        return False
    try:
        style = load_style(m.group(1))
    except Exception:
        return False
    st = getattr(style, "structure", None)
    return bool(st is not None and getattr(st, "declares_alignment", lambda: False)())


def _check_alignment_resolution(html):
    """(passed, detail) for G10. Wrappers = the page's #sec-N surface divs, or the <html>
    tag on a single-section render (which stamps there)."""
    if not _style_declares_alignment(html):
        return True, ("active style declares no alignment stance (or no style) — "
                      "resolution stamps not required")
    wrappers = _SEC_WRAPPER_RE.findall(html)
    if not wrappers:
        m = re.search(r"<html\b[^>]*>", html)
        wrappers = [m.group(0)] if m else []
    if not wrappers:
        return True, "no section wrappers found"
    problems = []
    stamped = 0
    for tag in wrappers:
        attrs = dict(_ATTR_RE.findall(tag))
        ident = attrs.get("id") or attrs.get("data-layout") or "html"
        anchor = attrs.get("data-align")
        source = attrs.get("data-align-source")
        if not anchor or not source:
            problems.append(f"{ident}: MISSING data-align/-source (silent fall-through)")
            continue
        stamped += 1
        if anchor not in _ALIGN_ENUM:
            problems.append(f"{ident}: out-of-enum anchor '{anchor}'")
        # the full legitimate source chain (compose_section.resolve_alignment):
        # section > curation > pattern > brand grammar > style role default.
        if source not in ("section", "curation", "pattern", "brand", "style"):
            problems.append(f"{ident}: unknown align source '{source}'")
        if anchor in ("left", "right") and not attrs.get("data-align-counterweight"):
            problems.append(f"{ident}: asymmetric anchor '{anchor}' declares NO "
                            "counterweight device")
    if problems:
        more = f" (+{len(problems) - 5} more)" if len(problems) > 5 else ""
        return False, ("; ".join(problems[:5]) + more)
    return True, (f"{stamped}/{len(wrappers)} sections resolved + source-stamped; "
                  "asymmetric anchors all carry counterweights")


# ── G11 media registration (AS-19) ───────────────────────────────────────────────────

_MEDIA_COL_VAR_RE = re.compile(
    r"--c-(?:statement|quote)-media-col\s*:\s*([^;}]+)")
_SPAN_SYM_RE = re.compile(r"^\s*(\d+)\s*/\s*-\s*(\d+)\s*$")


def _split_sections(html):
    """Yield (ident, chunk) per #sec-N wrapper (chunk = wrapper to next wrapper), or the
    whole document as one chunk for single-section renders."""
    marks = [(m.start(), m.group(0)) for m in _SEC_WRAPPER_RE.finditer(html)]
    if not marks:
        yield "document", html
        return
    for i, (pos, tag) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(html)
        ident = (re.search(r'id="(sec-\d+)"', tag) or [None, "?"])[1]
        yield ident, html[pos:end]


def _check_media_registration(html):
    """(passed, detail): every RESOLVED-CENTERED section whose markup carries a
    statement/quote media slot must scope a SYMMETRIC media span (`n / -n`, tolerance
    |start-end| <= 1) — the scaffold's editorial-offset fallback (6/-1) under centered
    text is the AS-19 misregistration."""
    problems = []
    centered_media = 0
    for ident, chunk in _split_sections(html):
        head = chunk[:chunk.find(">") + 1]
        centered = 'data-align="centered"' in head or (
            ident == "document" and re.search(
                r'<html\b[^>]*data-align="centered"', html))
        if not centered:
            continue
        if "cs-statement-media" not in chunk and "cs-quote-media" not in chunk:
            continue
        centered_media += 1
        # the symmetric span is scoped per-section (#sec-N { --c-*-media-col: 4 / -4 })
        sel = ident if ident != "document" else ""
        scoped = re.findall(rf"#{sel}[^{{}}]*{{[^}}]*}}", html) if sel else [html]
        vals = []
        for block in scoped:
            vals += _MEDIA_COL_VAR_RE.findall(block)
        if not vals:
            problems.append(f"{ident}: centered section leaves media on the scaffold's "
                            "editorial-offset span (no symmetric --c-*-media-col scoped)")
            continue
        for v in vals:
            m = _SPAN_SYM_RE.match(v.strip())
            if not m or abs(int(m.group(1)) - int(m.group(2))) > 1:
                problems.append(f"{ident}: centered section places media on "
                                f"asymmetric span '{v.strip()}'")
    if problems:
        return False, "; ".join(problems[:5])
    if not centered_media:
        return True, "no resolved-centered statement/quote media in this render"
    return True, (f"{centered_media} centered section(s) place media on symmetric "
                  "anchor-derived spans")


# G8 occlusion budget per class — MUST mirror compose_section.OCCLUSION_CAP.
_OCCLUSION_CAPS = {"light": 0.25, "medium": 0.40, "heavy": 0.55}


def _check_occlusion(html):
    """(passed, detail) for the G8 occlusion contract. Reads every section carrying an
    occlusion stamp, recomputes the estimate from the stamped grid geometry
    (horizFrac x vertFrac), and enforces budget + endsVisible + stamp/geometry agreement."""
    tags = re.findall(r"<section\b[^>]*data-occlusion=[^>]*>", html)
    if not tags:
        return True, "no occluded headings (type-behind-media / z:back straddle) in this render"

    problems, rows = [], []
    for tag in tags:
        def attr(name, _tag=tag):
            m = re.search(rf'{name}="([^"]*)"', _tag) or re.search(rf"{name}='([^']*)'", _tag)
            return m.group(1) if m else None

        try:
            stamped = float(attr("data-occlusion"))
            cap = float(attr("data-occlusion-max"))
        except (TypeError, ValueError):
            problems.append("malformed occlusion stamp (data-occlusion/-max not numeric)")
            continue
        ends = (attr("data-ends-visible") or "").lower() == "true"
        est = stamped
        geom_raw = attr("data-occlusion-geom")
        if geom_raw:
            try:
                g = json.loads(geom_raw)
                est = round(float(g["horizFrac"]) * float(g["vertFrac"]), 3)
            except Exception:
                problems.append("unparseable data-occlusion-geom (gate cannot recompute)")
        else:
            problems.append("missing data-occlusion-geom (gate cannot recompute)")
        if abs(est - stamped) > 0.02:
            problems.append(f"stamped occlusion {stamped:g} disagrees with recomputed {est:g}")
        if est > cap + 1e-9:
            problems.append(f"occlusion {est:g} over the {cap:g} budget -> reclassify the "
                            "word as ghost-word (decorative) + carry a readable heading")
        if not ends:
            problems.append("endsVisible violated (first/last letterforms must stay clear)")
        rows.append(f"occlusion={est:g} (cap {cap:g}, endsVisible={ends})")

    if problems:
        shown = "; ".join(problems[:4])
        more = f" (+{len(problems) - 4} more)" if len(problems) > 4 else ""
        return False, f"{len(tags)} occluded heading(s): {shown}{more}"
    return True, f"{len(tags)} occluded heading(s) within contract: {'; '.join(rows)}"


def _check_bands(html):
    """(passed, detail) for the G9 banded dual-surface contract: each data-bands section
    carries exactly TWO data-band-surface bands matching its declaration, each with its
    own scoped surface vars (inline background + --c-ink re-scope)."""
    secs = re.findall(r'<section\b[^>]*data-bands="([^"]*)"[^>]*>', html)
    if not secs:
        return True, "no banded (dual-surface) sections in this render"
    band_attrs = re.findall(r'data-band-surface="([^"]*)"', html)
    problems = []
    declared = [r.strip() for v in secs for r in v.split(",") if r.strip()]
    if len(band_attrs) != 2 * len(secs):
        problems.append(f"{len(secs)} banded section(s) but {len(band_attrs)} scoped bands "
                        "(expected exactly 2 per section)")
    missing = [r for r in declared if r not in band_attrs]
    if missing:
        problems.append(f"declared band surfaces not scoped on any band: {missing}")
    # each band must scope its own tokens (inline background + ink re-scope)
    for m in re.finditer(r'<div\b[^>]*data-band-surface="[^"]*"[^>]*>', html):
        tag = m.group(0)
        style = (re.search(r'style="([^"]*)"', tag) or [None, ""])[1]
        if "background" not in style or "--c-ink" not in style:
            problems.append("a band lacks scoped surface vars (background + --c-ink)")
            break
    if problems:
        return False, "; ".join(problems)
    return True, (f"{len(secs)} banded section(s), {len(band_attrs)} scoped bands "
                  f"({', '.join(declared)})")


# ── STYLE definition (the active style layer's brand-overridable core rules) ─────

_VIEWPORT_UNIT_RE = re.compile(r"\b\d*\.?\d+(vw|vh|dvw|dvh|svw|svh|lvw|lvh)\b", re.I)


def _effective_display_size(html: str) -> str | None:
    """Return the desktop-effective ``--display-size`` value.

    Prefers the declaration inside the appended STYLE override block (the unconditional
    ``:root`` that wins at desktop over the brand base + the max-width media queries);
    otherwise falls back to the last unconditional declaration."""
    marker = html.find("STYLE:")
    region = html[marker:] if marker != -1 else html
    m = list(re.finditer(r"--display-size:\s*([^;]+);", region))
    if m:
        return m[-1].group(1).strip()
    m = list(re.finditer(r"--display-size:\s*([^;]+);", html))
    return m[-1].group(1).strip() if m else None


def _display_reaches_poster(value: str | None, min_rem: float, min_cqw: float):
    """True when the display tier reaches genuine poster scale (rem floor or cqw)."""
    if not value:
        return False, "no --display-size found"
    rems = [float(x) for x in re.findall(r"(\d+(?:\.\d+)?)\s*rem", value)]
    cqws = [float(x) for x in re.findall(r"(\d+(?:\.\d+)?)\s*cqw", value)]
    rem_ok = any(r >= min_rem for r in rems)
    cqw_ok = any(c >= min_cqw for c in cqws)
    return (rem_ok or cqw_ok,
            f"display-size={value} -> rems={rems or 'none'} (floor {min_rem}), "
            f"cqw={cqws or 'none'} (intent ~{min_cqw}); poster={'yes' if (rem_ok or cqw_ok) else 'NO'}")


def _brand_display_rem(doc):
    """The brand's measured display-hero base size in rem (None when unmeasured).
    Mirrors tokens_css.type_role's two shapes: flat role node OR families+scale."""
    types = (doc.get("tokens", {}) or {}).get("type", {}) or {}
    node = types.get("display-hero")
    if not isinstance(node, dict):
        scale = types.get("scale")
        node = scale.get("display-hero") if isinstance(scale, dict) else None
    if not isinstance(node, dict):
        return None
    sz = node.get("sizeRem")
    if isinstance(sz, dict):
        sz = sz.get("base")
    if sz is None and node.get("px"):
        try:
            sz = round(float(node["px"]) / 16, 4)
        except (TypeError, ValueError):
            sz = None
    try:
        return float(sz) if sz is not None else None
    except (TypeError, ValueError):
        return None


def _display_rides_brand_tier(value: str | None, tier_rem):
    """display_source='brand' judgment (B3/B11): the effective display magnitude must
    BE the brand's measured display-hero tier — a var() reference to the layer-1 tier
    token, or the tier's rem value verbatim — never an inflated poster clamp."""
    if not value:
        return False, "no --display-size found"
    if "--size-display-hero" in value:
        return True, f"display-size={value} — rides the brand display-hero tier token"
    rems = [float(x) for x in re.findall(r"(\d+(?:\.\d+)?)\s*rem", value)]
    if tier_rem is None:
        return False, (f"display-size={value}; brand display-hero tier UNMEASURED — "
                       f"cannot verify brand-sourced display")
    ok = any(abs(r - float(tier_rem)) < 0.03 for r in rems)
    return ok, (f"display-size={value} -> rems={rems or 'none'} vs brand display-hero "
                f"tier {tier_rem}rem (style display_source=brand); "
                f"{'matches' if ok else 'DOES NOT match'}")


def detect_brand_overrides(html, doc, style=None):
    """Detect the style rules the BRAND intentionally overrides in this render.

    Style Invariants/rules are brand-overridable DEFAULTS (not absolute floors): where the
    brand explicitly commits to a value that contradicts a style rule, the brand wins and
    the gate must BLESS the deviation as an INTENTIONAL OVERRIDE, not fail it.

    Two families of override are detected:

    (A) HERO (#sec-0) brand-over-style exception emitted by
        ``compose_page.hero_brand_override_css``: scoped to #sec-0 the brand commits to a
        CENTERED, accent display heading on its dark hero surface, overriding the style's
        left-anchored / ink-display defaults for that one section. Detected from grounded
        signals — (a) the composer's clearly-marked, #sec-0-scoped override CSS block
        (``hero_marker``, the primary signal), and/or (b) corroborating brand.yaml rules
        that sanction centering on the bookend/hero/conversion (do/avoid/blocks prose) — so
        an unrelated stray `text-align: center` is NOT mistaken for a sanctioned override.

    (B) SOFT-OPTION choices (tier-2): a brand commits a soft-option value (via a token or
        primitive binding) that differs from the ACTIVE style's declared default. Only
        blessed when the active ``style`` actually declares that option as SOFT — so a
        property that is an Invariant in the active style (e.g. radical-editorial's radius)
        never yields a spurious soft-option override row.

    Returns {override_key: human note} for each detected, brand-sanctioned override.
    """
    low = html.lower()
    overrides: dict[str, str] = {}

    # ── (A) hero #sec-0 brand-over-style exception ───────────────────────────────────
    hero_marker = "brand-over-style exception" in low and "#sec-0" in low
    hero_centered = bool(re.search(r"#sec-0[^{}]*\{[^}]*text-align:\s*center", low))
    hero_accent_heading = bool(re.search(
        r"#sec-0[^{}]*\.c-heading--accent[^{}]*\{[^}]*color:\s*var\(--c-accent\)", low))

    # brand.yaml corroboration: a do/avoid/block rule that sanctions centering on the
    # bookend/hero/conversion stack (so the deviation is backed by the BRAND, not invented).
    def _rule_texts():
        for key in ("do", "avoid"):
            for r in doc.get(key, []) or []:
                yield str(r.get("statement", ""))
        for b in (doc.get("blocks", {}) or {}).values():
            for r in (b.get("rules", []) or []):
                yield str(r)
    brand_sanctions_centered = any(
        ("center" in t.lower() and any(k in t.lower() for k in ("bookend", "hero", "conversion")))
        for t in _rule_texts())

    if (hero_marker or hero_centered) and (hero_marker or brand_sanctions_centered):
        overrides["centered"] = (
            "hero #sec-0 centered display heading — documented brand-over-style override "
            "(compose_page.hero_brand_override_css), corroborated by brand rules sanctioning "
            "centering on the bookend/hero; scoped to #sec-0 only")
    if hero_marker or hero_accent_heading:
        overrides["accent_display"] = (
            "hero #sec-0 accent display heading — documented brand-over-style override "
            "(brand commits the single accent to the hero display title on its dark surface); "
            "scoped to #sec-0 only")

    # ── (B) soft-option overrides (only for options the ACTIVE style declares SOFT) ───
    soft = getattr(style, "soft_options", {}) or {}

    if "radius" in soft:
        nd_ids = {nd.get("id") for nd in doc.get("neverDo", []) or []}
        rg = ((doc.get("tokens", {}) or {}).get("spacing", {}) or {}).get("radius-global", {})
        rg_val = str((rg or {}).get("value", "")).strip()
        if "no-radius" in nd_ids or rg_val in ("0", "0px", "0rem"):
            overrides["radius"] = (
                f"brand commits sharp corners (radius-global '{rg_val or '0'}'"
                + (" + neverDo.no-radius" if "no-radius" in nd_ids else "")
                + f") — soft-option 'radius' override of the style default "
                  f"'{soft['radius'].get('default')}'")

    if "primary-action" in soft:
        prims = doc.get("primitives", {}) or {}
        button_never = (prims.get("button", {}) or {}).get("use") == "never"
        link_remaps_cta = (prims.get("link", {}) or {}).get("remapFrom") == "cta"
        if button_never or link_remaps_cta:
            sig = "; ".join(s for s, ok in
                            (("button use: never", button_never),
                             ("link remapFrom: cta", link_remaps_cta)) if ok)
            overrides["primary-action"] = (
                f"brand remaps the CTA role to a typographic link ({sig}) — soft-option "
                f"'primary-action' override of the style default "
                f"'{soft['primary-action'].get('default')}'")

    return overrides


def check_style(doc, html, layout, facts, style):
    """Report the active STYLE's core rules against the render — OVERRIDE-AWARE.

    Style ``style_rules`` are the style's load-bearing DEFAULTS, but they are
    brand-overridable: this gate NEVER hard-fails OVERALL on a style rule. Each row is
    reported as one of:
      - PASS     — the render satisfies the style default.
      - OVERRIDE — the render deviates, but a documented brand override sanctions it
                   (e.g. the hero #sec-0 exception). Logged as an intentional override.
      - WARN     — the render deviates with no backing brand override (advisory only).
    Brand ``neverDo`` violations are handled separately and remain hard FAILs.

    Driven by the style's structural fields (so it generalizes to any style spec), and
    labeled with the spec's own ``style_rules`` wording where available."""
    low = html.lower()
    s = style.structure
    rules = style.style_rules
    soft = getattr(style, "soft_options", {}) or {}
    overrides = detect_brand_overrides(html, doc, style)
    checks = []  # (label, status, detail) with status in {PASS, OVERRIDE, WARN}

    def label(i, fallback):
        return rules[i] if i < len(rules) else fallback

    def add(lbl, passed, detail, override_key=None):
        if passed:
            checks.append((lbl, "PASS", detail))
        elif override_key and override_key in overrides:
            checks.append((lbl, "OVERRIDE",
                           f"{detail} — INTENTIONAL BRAND OVERRIDE: {overrides[override_key]}"))
        else:
            checks.append((lbl, "WARN",
                           f"{detail} — style default not met; no backing brand override (advisory)"))

    # Rule 1 — display magnitude, display_source-aware (B3/B11, fix-batch 2026-07):
    # 'poster' styles must reach genuine poster scale (unchanged); a 'brand'-sourced
    # style (corporate archetypes) must ride the brand's own measured display-hero tier
    # instead — inflating a 65px-hero brand to a poster clamp is the FAILURE there.
    if getattr(s, "display_source", "poster") == "brand":
        passed, detail = _display_rides_brand_tier(
            _effective_display_size(html), _brand_display_rem(doc))
        add("[INVARIANT] Display rides the brand's measured display tier", passed, detail)
    else:
        passed, detail = _display_reaches_poster(
            _effective_display_size(html), s.min_display_rem, s.display_vw)
        add("[INVARIANT] " + label(0, "Display reaches poster scale"), passed, detail)

    # Rule 2 — flat throughout: no cards, no shadows (depth from scale/whitespace only) (INVARIANT)
    flat_ok = (not facts["shadows"]) and (not facts["borders"]) and (not facts["has_card_class"])
    add("[INVARIANT] " + label(1, "Flat — no cards/shadows"), flat_ok,
        f"shadows={facts['shadows'] or 'none'}; borders={facts['borders'] or 'none'}; "
        f"card containers={facts['has_card_class']}")

    # Rule 2b — radius: TIER-AWARE. When the active style declares `radius` as a SOFT option
    # (e.g. editorial-luxury's ~10px luxury softness) the brand CHOOSES the value; the row
    # passes when the render is internally consistent with the brand's committed choice
    # (WoodWave commits sharp corners via radius-global 0 + neverDo.no-radius, so the render
    # is zero → PASS, blessed as the 'radius' soft-option override). When radius is an
    # INVARIANT of the style (e.g. radical-editorial: 0 everywhere) the original zero-radius
    # assertion applies.
    nonzero_radii = [r for r in facts["radii"] if r not in ("0", "0px", "0rem", "var(--radius)")]
    rv = facts["radius_vars"].get("--radius", "")
    render_zero = (not nonzero_radii) and rv.strip() in ("0", "0px", "0rem", "")
    radius_detail = (f"--radius={rv.strip() or 'n/a'}; nonzero literal radii={nonzero_radii or 'none'}; "
                     f"style radius default={s.radius}")
    if "radius" in soft:
        # brand chose the radius; render must honor a self-consistent value. WoodWave → 0.
        add("[SOFT] Radius matches brand choice", render_zero, radius_detail,
            override_key="radius")
    else:
        radius_ok = (s.radius in ("0", "0px", "0rem")) and render_zero
        add("[INVARIANT] Zero border-radius (sharp corners)", radius_ok, radius_detail)

    # Rule 3 — asymmetric whitespace grid, never centered-everything (brand-overridable;
    # the hero #sec-0 centered exception is a sanctioned override)
    asym_markers = bool(re.search(r"data-style=", html, re.I)) and \
        bool(re.search(r"align-items:\s*flex-start", low)) and \
        bool(re.search(r"\.hv-title\.is-display\s*\{[^}]*text-align:\s*left", low))
    add("[INVARIANT] " + label(2, "Asymmetric — not centered-everything"), asym_markers,
        f"data-style+flex-start+left-aligned display present={asym_markers} "
        f"(centered text-align count={facts['centered_count']})",
        override_key="centered")

    # Rule 4 — single committed accent / ink display (brand-overridable; the hero #sec-0
    # accent-gold display heading is a sanctioned override)
    title_is_ink = bool(re.search(
        r"\.hv-title\.is-display\s*\{[^}]*color:\s*var\(--text\)", low))
    single_accent = (not facts["off_palette"]) and title_is_ink
    add("[INVARIANT] Single committed accent (no second accent)", single_accent,
        f"off-palette hues={facts['off_palette'] or 'none'}; "
        f"display headline is ink (not accent)={title_is_ink}",
        override_key="accent_display")

    # Iframe convention — container-query units only, never viewport units. This is a
    # render-substrate invariant, not a style default, so it is reported PASS/WARN only.
    vp = sorted({m.group(0) for m in _VIEWPORT_UNIT_RE.finditer(html)})
    add("Container-query units only (0 viewport units)", not vp,
        f"viewport-unit matches={vp or 'none'}")

    # Explicit override ledger: surface every detected brand-over-style override as its own
    # blessed row so the report shows the hero exception as an intentional override.
    for key, note in overrides.items():
        checks.append((f"Brand-over-style override blessed — {key}", "OVERRIDE", note))
    return checks


# ── report ───────────────────────────────────────────────────────────────────────

def render_report(doc, layout, nd, fid, slop, render_dir, allow=None, style=None,
                  style_checks=None, inv=None, composition_mode=False):
    allow = allow or set()
    inv = inv or []
    # A failure on a DECLARED (--allow) rule does not count against the neverDo verdict.
    nd_pass = all(p or allowed for _, _, p, _, allowed in nd)
    nd_true_pass = all(p for _, _, p, _, _ in nd)
    declared_fails = [rid for rid, _, p, _, allowed in nd if (not p) and allowed]
    fid_pass = all(p for _, p, _ in fid)
    slop_pass = all(p for _, p, _ in slop)
    # Composition invariants gate OVERALL only under --composition; otherwise advisory.
    inv_true_pass = all(p for _, _, p, _ in inv)
    inv_pass = inv_true_pass if composition_mode else True
    # STYLE rows are advisory: brand-overridable defaults that are blessed when a brand
    # override sanctions a deviation, and at worst WARN. They NEVER hard-fail OVERALL — only
    # the brand neverDo (+ fidelity/slop) layers gate the build. The brand's own neverDo is
    # the single hard, non-overridable layer.
    style_rows = style_checks or []
    style_overrides = [lbl for lbl, st, _ in style_rows if st == "OVERRIDE"]
    style_warns = [lbl for lbl, st, _ in style_rows if st == "WARN"]
    style_clean = not style_warns  # PASS/OVERRIDE only
    overall = nd_pass and fid_pass and slop_pass and inv_pass

    name = doc.get("brand", {}).get("name", "Brand")
    lid = layout.get("id", "section")

    L = []
    w = L.append
    w(f"# On-brand report - {lid} ({name})")
    w("")
    w(f"**OVERALL: {'PASS' if overall else 'FAIL'}**")
    w("")
    if declared_fails:
        w(f"> Declared one-off exception(s) via `--allow`: "
          + ", ".join(f"`{r}`" for r in declared_fails)
          + ". These rules genuinely FAIL below but are EXPECTED for this variant, so they "
            "do NOT flip OVERALL. (neverDo true-pass without exceptions: "
          + ("PASS" if nd_true_pass else "FAIL") + ".)")
        w("")
    w("Generated by `brand_pipeline/onbrand_check.py` (brand-agnostic, data-driven) "
      f"against `{Path(render_dir).name}/index.html`, driven by `brand.yaml`.")
    w("")
    w("## Method")
    w("")
    w("- **neverDo:** every `neverDo[]` rule in `brand.yaml` is dispatched through a "
      "brand-agnostic checker registry (supports both hard-edged editorial id families "
      "and rounded-SaaS id families) and statically verified against the rendered "
      "HTML/CSS. Unknown ids fall back to a keyword heuristic, else report as "
      "informational rather than a false fail.")
    w("- **Fidelity:** structured checklist derived from the rendered layout's resolved "
      "surface, tokens and componentMapping (no per-brand literals). Each row asserts a "
      "token/layout fact from the source crop is actually present in the render. Visual "
      "confirmation was done by screenshotting the render with headless Chromium and "
      "comparing it beside the source crop in `assets/`.")
    w("- **Slop checklist:** generic-AI-look failure modes (default fonts, off-palette "
      "hex, lorem copy, missing assets, rounding off the brand radius scale, missing webfonts).")
    w("")

    w(f"## 1. neverDo violations - {'PASS' if nd_pass else 'FAIL'}")
    w("")
    w("| rule | result | detail |")
    w("|---|---|---|")
    for rid, stmt, passed, detail, allowed in nd:
        if not passed and allowed:
            verdict = "FAIL (declared one-off exception)"
        else:
            verdict = "PASS" if passed else "FAIL"
        w(f"| `{rid}` | {verdict} | {detail} |")
    w("")

    w(f"## 2. Fidelity vs source - {'PASS' if fid_pass else 'FAIL'}")
    w("")
    w("| check | result | source fact |")
    w("|---|---|---|")
    for label, passed, note in fid:
        w(f"| {label} | {'PASS' if passed else 'FAIL'} | {note} |")
    w("")

    w(f"## 3. Slop checklist - {'PASS' if slop_pass else 'FAIL'}")
    w("")
    w("| check | result | detail |")
    w("|---|---|---|")
    for label, passed, note in slop:
        w(f"| {label} | {'PASS' if passed else 'FAIL'} | {note} |")
    w("")

    if style is not None and style_checks is not None:
        verdict = "PASS" if style_clean else "PASS (advisory warnings)"
        w(f"## 4. Style definition — `{style.id}` — {verdict} (advisory, never gates OVERALL)")
        w("")
        w(f"The active STYLE layer (`{style.source_path}`) supplies STRUCTURE + DEFAULTS; the "
          "brand supplies hues + fonts AND wins on any value it explicitly sets. These are the "
          "style's core `Style definition` rules — brand-overridable defaults, NOT absolute "
          "non-negotiables. A deviation backed by a documented brand override (e.g. the hero "
          "`#sec-0` centered / accent-gold exception) is reported as an INTENTIONAL OVERRIDE "
          "(blessed, logged); a deviation with no backing override is an advisory WARN. Style "
          "rows never flip OVERALL — only the brand `neverDo` layer is hard.")
        w("")
        if style_overrides:
            w("> Intentional brand-over-style override(s) blessed: "
              + ", ".join(f"`{r}`" for r in style_overrides) + ".")
            w("")
        w("| style rule | result | detail |")
        w("|---|---|---|")
        for label, status, note in style_checks:
            w(f"| {label} | {status} | {note} |")
        w("")

    if inv:
        mode = "HARD (gates OVERALL)" if composition_mode else "advisory (WARN, never gates)"
        sect_verdict = ("PASS" if inv_true_pass else ("FAIL" if composition_mode else "advisory warnings"))
        w(f"## 5. Composition invariants — {mode} — {sect_verdict}")
        w("")
        w("AI-authored `composition.v1` drift checks (single-accent, primitive-only "
          "vocabulary, spacing rhythm, `data-composition` well-formedness, slot resolution) "
          "plus the static READABILITY checks (`text-contrast`: real text vs its effective "
          "background including any decoration layer behind it; `decoration-salience`: "
          "ghost-word/watermark layers must stay close to their surface). "
          "These catch drift the visual `neverDo` checks can't see. By default they are "
          "ADVISORY (a failure reports as `WARN` and never flips OVERALL); pass `--composition` "
          "to make them HARD for AI-composed pages. The existing deterministic pages are gated "
          "WITHOUT `--composition`, so these rows never regress them.")
        w("")
        w("| invariant | result | detail |")
        w("|---|---|---|")
        for rid, label, passed, detail in inv:
            verdict = ("PASS" if passed else ("FAIL" if composition_mode else "WARN"))
            w(f"| `{rid}` — {label} | {verdict} | {detail} |")
        w("")

    w("## How to view")
    w(f"- Open `{Path(render_dir).name}/index.html` in any browser (it loads the brand "
      "fonts from Google Fonts and the source crop in `assets/`).")
    w("- A captured preview of the render is at `assets/_preview-render.png`; the source "
      "crop it was compared against is `assets/_source-*-crop.*`.")
    w(f"- Re-generate: `python3 brand_pipeline/compose_section.py <brand.yaml> {lid} -o {render_dir}`.")
    layout_flag = f" --layout {lid}" if Path(render_dir).name != f"section-{lid}" else ""
    w(f"- Re-run this gate: `python3 brand_pipeline/onbrand_check.py <brand.yaml> {render_dir}{layout_flag}`.")
    w("")
    return "\n".join(L).rstrip() + "\n", overall


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("brand_yaml", type=Path)
    ap.add_argument("render_dir", type=Path)
    ap.add_argument("--report", default="onbrand-report.md")
    ap.add_argument(
        "--layout", default=None,
        help="explicit layout id to resolve against (overrides the render-dir-name "
             "heuristic; required when the render dir name does not encode the layout id, "
             "e.g. variant dirs a/b/c).")
    ap.add_argument(
        "--allow", action="append", default=[], metavar="RULE_ID",
        help="declare a neverDo rule id as an EXPECTED one-off exception (repeatable). The "
             "rule still runs and reports its true PASS/FAIL, but a failure on an --allow'd "
             "rule does NOT flip OVERALL to FAIL and is labeled a declared one-off exception.")
    ap.add_argument(
        "--style", default=None,
        help="active STYLE id (e.g. radical-editorial). When given, the style's "
             "`Style definition` core rules are ALSO reported against the render as "
             "brand-overridable defaults: PASS, OVERRIDE (a documented brand override blesses "
             "a deviation, e.g. the hero #sec-0 exception), or WARN (advisory). Style rows are "
             "ADVISORY and never flip OVERALL — only the brand neverDo/fidelity/slop layers gate. "
             "If omitted, only the brand neverDo/fidelity/slop checks run (current behavior).")
    ap.add_argument(
        "--composition", action="store_true",
        help="treat this render as AI-authored `composition.v1` output: the composition "
             "invariants (single-accent, primitive-only vocabulary, spacing rhythm, "
             "data-composition well-formedness, slot resolution) become HARD and gate OVERALL. "
             "When omitted, those invariants still run but are ADVISORY (WARN) and never flip "
             "OVERALL (the deterministic pages are gated this way, so they never regress).")
    args = ap.parse_args()

    allow = set(args.allow or [])
    doc, html = load(args.brand_yaml, args.render_dir)
    layout = resolve_layout(doc, args.render_dir, layout_override=args.layout)
    facts = extract_facts(doc, html, layout, args.render_dir)
    nd = check_neverdo(doc, html, layout, facts, allow=allow)
    fid = check_fidelity(doc, html, layout, facts, render_dir=args.render_dir)
    slop = check_slop(doc, html, layout, facts)

    inv = check_composition(doc, html, layout, facts)
    # archetype physics bindings (spec/archetype-library.md): extra HARD rows for
    # sections that instantiated a genre archetype; [] for every other render.
    inv += check_archetype_physics(args.render_dir, html, inv, fid)
    # composition lints (fix7 AS-63/AS-65): knob-consumption + sibling-slot content
    # redundancy on the render's own composition.json; [] for composition-less lanes.
    inv += check_composition_lints(args.render_dir)
    # media-binding rows (media semantics 2026-07, AS-67): every media slot resolves
    # or declares its gap + third-party-mark legality. DOUBLY fact-gated ([] without
    # a generated composition AND without the brand's media-assets.yaml).
    inv += check_media_bindings(args.render_dir)

    style = style_checks = None
    if args.style:
        style = load_style(args.style)
        style_checks = check_style(doc, html, layout, facts, style)

    report, overall = render_report(doc, layout, nd, fid, slop, args.render_dir,
                                    allow=allow, style=style, style_checks=style_checks,
                                    inv=inv, composition_mode=args.composition)

    out = args.render_dir / args.report
    out.write_text(report)
    print(f"Wrote {out}")

    # ── machine-readable JSON scorecard (for the future test/ranking harness) ──────
    scorecard = {
        "layout": layout.get("id", "section"),
        "brand": doc.get("brand", {}).get("name", "Brand"),
        "composition_mode": bool(args.composition),
        "neverDo": {rid: bool(passed) for rid, _stmt, passed, _detail, _allowed in nd},
        "neverDo_allowed": sorted(allow),
        "fidelity": {
            "pass": all(p for _, p, _ in fid),
            "checks": {label: bool(p) for label, p, _ in fid},
        },
        "slop": {
            "pass": all(p for _, p, _ in slop),
            "checks": {label: bool(p) for label, p, _ in slop},
        },
        "invariants": {
            "mode": "hard" if args.composition else "advisory",
            "pass": all(p for _, _, p, _ in inv),
            "checks": {rid: bool(p) for rid, _label, p, _detail in inv},
            # measured values (contrast ratios / luminance deltas) for the readability
            # invariants, so the scorecard carries the numbers, not just the verdicts.
            "details": {rid: detail for rid, _label, _p, detail in inv
                        if rid in ("text-contrast", "decoration-salience")},
        },
        "overall": bool(overall),
    }
    json_name = re.sub(r"\.md$", "", str(args.report)) + ".json" \
        if str(args.report).endswith(".md") else str(args.report) + ".json"
    json_out = args.render_dir / json_name
    json_out.write_text(json.dumps(scorecard, indent=2) + "\n")
    print(f"Wrote {json_out}")
    # itemized top-line: the brand neverDo set (HARD) + the active style's core rules (ADVISORY)
    print("neverDo (hard):")
    for rid, _stmt, passed, _detail, allowed in nd:
        tag = "PASS" if passed else ("FAIL (declared one-off)" if allowed else "FAIL")
        print(f"  [{tag}] {rid}")
    if style_checks is not None:
        print(f"style definition ({style.id}, advisory — never gates OVERALL):")
        for label, status, _note in style_checks:
            print(f"  [{status}] {label}")
    inv_mode = "HARD" if args.composition else "advisory"
    print(f"composition invariants ({inv_mode}):")
    for rid, _label, passed, _detail in inv:
        tag = "PASS" if passed else ("FAIL" if args.composition else "WARN")
        print(f"  [{tag}] {rid}")
    print(f"OVERALL: {'PASS' if overall else 'FAIL'}")
    return 0 if overall else 2


if __name__ == "__main__":
    raise SystemExit(main())
