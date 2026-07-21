#!/usr/bin/env python3
"""component_render.py - the SINGLE SOURCE OF TRUTH for per-catalog-component rendering.

A brand's `primitives:`/`blocks:` catalog (in brand.yaml) is the vocabulary every
section is built from. This module owns ONE renderer per catalog component (heading,
eyebrow, image, arrow-link [cta/link], logo; the header/navbar blocks). BOTH callers
import these:

  - render_components_preview.py (the gallery) - shows EACH catalog item on its own.
  - compose_section.py (the composer) - assembles a SECTION by, for each layout slot,
    resolving the bound catalog component and rendering THAT component here.

Because both callers render through the same functions, editing a primitive here changes
EVERY composed section AND the gallery card at once - the catalog is truly the source,
sections are not bespoke markup.

CONTRACT (slot -> component binding):
  A layout's `blockMapping[]` entry is `{slot, role, contract, usage}`. `contract` names
  a catalog key (e.g. "header", "image", "link"). `resolve_renderer(contract)` returns the
  shared renderer; `usage` (+ section copy) becomes the renderer's `props`.

Every renderer takes (doc, ctx, props) and returns an HTML string built from shared
`c-*` classes. The shared stylesheet is emitted ONCE by `component_css()`; per-surface
token values are emitted by `component_vars()` so the SAME classes read on-brand on a
dark hero band or a cream gallery canvas. Units are container-query / rem only - never
viewport units (the render is shown in a Studio iframe).

Token resolution reuses the faithful helpers in tokens_css.py (imported, never
modified) so every value is the brand's real token.
"""
from __future__ import annotations

import html
import itertools
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Reuse the canonical token resolvers from tokens_css.py (same package dir) — the
# layer-1 generator module is the resolver SSOT (render_section.py retired 2026-07-03).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from tokens_css import (  # noqa: E402
    _slug,
    base_size,
    color_value,
    css_len,
    font_stack,
    spacing_value,
    type_role,
)


def esc(value) -> str:
    return html.escape(str(value if value is not None else ""))


def _px(value) -> str:
    """A CSS length from a measured fact: bare numbers gain px; CSS strings pass."""
    s = str(value if value is not None else "").strip()
    return f"{s}px" if re.fullmatch(r"-?\d+(\.\d+)?", s) else esc(s)


# ── layer-2 alias helpers: emit var() references INTO layer 1 (SPEC §A/§B) ───────
# Every --c-* right-hand side should be a var(--<layer1>) reference, never a Python-
# interpolated literal — the generated tokens block (tokens_css.build_page_tokens) is
# the single place brand VALUES appear.

def _color_ref(doc, token_ref):
    """var(--color-<slug>) when token_ref names a real brand color token; a raw value
    passes through unchanged (legacy callers hand hexes in); None when absent."""
    if not token_ref:
        return None
    colors = (doc.get("tokens", {}) or {}).get("colors", {}) or {}
    if token_ref in colors:
        return f"var(--color-{_slug(token_ref)})"
    return color_value(doc, token_ref)


def _font_ref(doc, role, fallback_family):
    """var(--font-<tier>) when the tier resolves; else the legacy literal stack."""
    if type_role(doc, role).get("family"):
        return f"var(--font-{_slug(role)})"
    return font_stack(doc, role, fallback_family)[0]


def _size_ref(doc, role, default_rem):
    """var(--size-<tier>-base) when the tier carries a measured size; else the legacy
    default. The -base alias is breakpoint-flat, preserving the legacy fixed-size
    behavior of these aliases (the responsive ladder lives in layer 1 for consumers
    that opt in via --size-<tier>)."""
    if base_size(type_role(doc, role)) is not None:
        return f"var(--size-{_slug(role)}-base)"
    return f"{default_rem}rem"


# ── render context (resolved brand values for ONE surface, + optional style) ─────

@dataclass
class ComponentContext:
    """Resolved, surface-scoped brand values handed to every shared renderer.

    The renderers themselves stay token-driven (they emit `c-*` classes that read the
    CSS custom properties produced by `component_vars`); this context only carries the
    facts a renderer needs to make structural decisions (e.g. accent only on dark)."""
    surface_role: str
    is_dark: bool
    proxies: set = field(default_factory=set)
    style_active: bool = False
    style_id: str = ""
    # resolved cta-shape flag ('filled'|'typographic'), cached so render-time action
    # dispatch (render_button) never re-derives it per fragment. Set by make_context
    # from the brand law; a style-aware caller (compose_page/compose_section) may
    # refine it with the active style's soft-option default via cta_shape(doc, style).
    cta: str = ""
    # chrome-nav mode (fid4 2026-07): the PAGE-LEVEL chrome nav renders the brand's
    # captured mega-menu panels (hover/focus dropdowns). Set by compose_page only —
    # gallery/preview navbars stay panel-free (their callers never set it).
    mega_nav: bool = False


def make_context(doc, surface_role, surf) -> ComponentContext:
    is_dark = surface_role in (
        "surface/inverse", "surface/inverse-strong", "surface/accent", "surface/overlay")
    # collect the google-font proxies the brand fonts need (so the caller can <link> them)
    proxies = set()
    for role in ("display-hero", "body", "eyebrow", "control-text"):
        _, p = font_stack(doc, role)
        proxies |= p
    return ComponentContext(surface_role=surface_role, is_dark=is_dark, proxies=proxies,
                            cta=cta_shape(doc))


# ── shared per-surface CSS variables (token VALUES) ──────────────────────────────

def _tier_ref(doc, role, attr, default):
    """var(--<attr-prefix>-<tier>) when the tier carries the measured attr in layer 1;
    else the legacy structural default (token-incomplete brands keep today's render)."""
    t = type_role(doc, role)
    slug = _slug(role)
    if attr == "leading":
        return f"var(--leading-{slug})" if t.get("lineHeight") is not None else default
    if attr == "weight":
        return f"var(--weight-{slug})" if t.get("weight") is not None else default
    if attr == "tracking":
        # layer 1 ALWAYS emits --tracking-<tier> for a resolved tier (0em default)
        return f"var(--tracking-{slug})" if t else default
    if attr == "case":
        return f"var(--case-{slug})" if t else default
    raise ValueError(attr)


def component_vars(doc, surf, *, selector=":root", display_size=None,
                   title_overlap="-2.75rem", eyebrow_gap=None, surface_role=None) -> str:
    """Emit the `--c-*` custom properties for ONE surface — layer 2 of the token
    contract (token-layer-2026-07): every right-hand side is a var() REFERENCE into the
    generated layer-1 block (tokens_css.build_page_tokens), never a Python-interpolated
    literal, so the brand VALUES live in exactly one place. The same `c-*` component
    classes read these vars, so a single class set renders on-brand on any surface just
    by re-declaring this block at the surface's scope."""
    colors = (doc.get("tokens", {}) or {}).get("colors", {}) or {}
    text = _color_ref(doc, surf.get("textPrimary")) or "var(--color-text-on-primary)"
    accent = _color_ref(doc, surf.get("textAccent")) or text
    bg = surf.get("bg") or "#ffffff"
    # DARK-SURFACE TEST from the raw bg luminance — NOT `surf.get("textAccent")`.
    # textAccent merely NAMES the accent color role and is present on light and dark
    # surfaces alike (v2/remote stamp it on 3 dark surfaces; a mis-authored brand can
    # stamp it on all 7). Using it as a dark proxy made every light section inherit the
    # INVERSE muted ink / inverse hairline / dark link-hover — white-on-white muted
    # text on light panels (product-launch text-contrast, 2026-07). A non-hex bg
    # (descriptive "image + dark scrim") resolves to the darkest brand color → dark.
    _raw_bg = str(surf.get("bg") or "#ffffff").strip()
    _m = re.match(r"^#([0-9a-fA-F]{6})$", _raw_bg)
    is_dark_surface = (sum(int(_m.group(1)[i:i+2], 16) for i in (0, 2, 4)) < 384
                       if _m else not re.match(r"^(rgb|hsl|var\()", _raw_bg))
    if re.match(r"^(#|rgb|hsl)", str(bg).strip()) and surface_role:
        bg = f"var(--surface-{_slug(surface_role)})"
    elif not re.match(r"^(#|rgb|hsl|var\()", str(bg).strip()):
        # v1 DESCRIPTIVE surface ("image + dark scrim") — not a color (anti-ai-slop.md
        # AS-02 shape). Substitute the darkest brand color (min luminance) BY TOKEN REF,
        # so the media-surface canvas stays on-palette and traceable.
        _hexes = [(k, str(c.get("value") if isinstance(c, dict) else c))
                  for k, c in colors.items()]
        _hexes = [(k, h) for k, h in _hexes if re.match(r"^#[0-9a-fA-F]{6}$", h or "")]
        if _hexes:
            tok, _ = min(_hexes, key=lambda kv: int(kv[1][1:3], 16)
                         + int(kv[1][3:5], 16) + int(kv[1][5:7], 16))
            bg = f"var(--color-{_slug(tok)})"
        else:
            bg = "var(--color-text-on-primary)"  # fail-visible: required token, never absent
    # SECONDARY ink is surface-declarable (hubspot-v2 2026-07, schema `textSecondary`):
    # a photographic band whose measured sub/eyebrow ink is FULL-strength (the art
    # carries the contrast; no 62% register exists on that surface) declares it —
    # surfaces without the key keep the global muted-role resolution unchanged.
    muted = _color_ref(doc, surf.get("textSecondary")) \
        or _color_ref(doc, "text/on-inverse-muted" if is_dark_surface
                      else "text/on-primary-muted") or text

    # the brand's single ruled-line hairline (underline fields + ruled action rows):
    # SURFACE-AWARE (a dark surface prefers a dedicated "-on-inverse" token; else falls
    # back to `muted`, which is already resolved per-surface above). Token EXISTENCE is
    # checked directly — color_value()'s pass-through-on-missing return is truthy (the
    # AS-02 invisible-hairline trap this block previously documented at length).
    _hairline_tok = "border/hairline-on-inverse" if is_dark_surface else "border/hairline-on-primary"
    hairline = f"var(--color-{_slug(_hairline_tok)})" if _hairline_tok in colors else muted
    # PER-SURFACE link-hover (anti-ai-slop.md AS-10/AS-20): the measured hover color was
    # measured on a DARK surface — it applies ONLY on dark/textAccent-bearing surfaces
    # (incl. re-scoping panels/cards); every light surface hovers in its own ink.
    link_hover = ("var(--chrome-link-hover)"
                  if (is_dark_surface and link_hover_color(doc)) else text)
    # BRAND LINK TOKENS win when carried (sysfix 2026-07): a brand with an authored
    # text/link(+hover) pair binds its typographic-action color per surface — idle
    # `--c-action-color` + hover `--c-link-hover` — from ITS OWN tokens (the on-inverse
    # twins on dark surfaces). Token-less brands keep the resolutions above unchanged.
    _link_tok, _link_hover_tok = (("text/link-on-inverse", "text/link-hover-on-inverse")
                                  if is_dark_surface
                                  else ("text/link", "text/link-hover"))
    action_color = (f"var(--color-{_slug(_link_tok)})"
                    if _link_tok in colors else None)
    if _link_hover_tok in colors:
        link_hover = f"var(--color-{_slug(_link_hover_tok)})"
    action_css = f"\n  --c-action-color: {action_color};" if action_color else ""
    eyebrow_gap = eyebrow_gap or (
        "var(--space-eyebrow-to-heading)"
        if "eyebrow-to-heading" in ((doc.get("tokens", {}) or {}).get("spacing", {}) or {})
        else "1.5rem")
    # imagery aspect palette (tokens.imagery.aspectPalette, anti-ai-slop.md AS-17):
    # OPTIONAL (DECISIONS.md #5) — absence emits nothing and the media devices fall back
    # to intrinsic ratios (aspect-ratio drops unresolved: device disabled, never another
    # brand's ratio).
    _pal = ((doc.get("tokens", {}) or {}).get("imagery", {}) or {}).get("aspectPalette", {}) or {}
    aspect_css = "".join(
        f"\n  --c-aspect-{_slug(k)}: var(--aspect-{_slug(k)});" for k, v in _pal.items()
        if isinstance(v, dict) and v.get("value"))
    # buttons (CR-2): alias the measured button family for brands that carry it; absent
    # (typographic-CTA brands) nothing is emitted and `.c-button` falls back to its
    # var()-chained control-tier shape. Names are surface-relationship generic.
    btn_css = ""
    if isinstance((doc.get("buttons") or {}).get("primary"), dict):
        b = doc["buttons"]["primary"]
        _btn = {"bg": "--button-bg", "fg": "--button-fg", "bgHover": "--button-bg-hover",
                "fgHover": "--button-fg-hover", "border": "--button-border",
                "padding": "--button-pad", "radius": "--button-radius",
                "weight": "--button-weight", "height": "--button-height"}
        parts = [f"\n  --c-button-{suffix.removeprefix('--button-')}: var({suffix});"
                 for src, suffix in _btn.items() if b.get(src) is not None]
        if b.get("sizeRem") is not None:
            parts.append("\n  --c-button-size: var(--button-size);")
        if b.get("font"):
            parts.append("\n  --c-button-font: var(--button-font);")
        btn_css = "".join(parts)

    # inputs (N5/B10, fix-batch 2026-07): alias the measured input tokens for BOXED-input
    # brands so `.c-field--boxed` renders the brand's own input radius instead of silently
    # falling back to the global --radius (HubSpot: 0.25rem input vs 1rem card). Emitted
    # only when the boxed variant is active (never dormant foreign grammar) and only for
    # tokens the brand actually carries — everything stays a var() reference into layer 1.
    input_css = ""
    if input_shape(doc) == "boxed":
        radius_roles = (doc.get("tokens", {}) or {}).get("radius") or {}
        _inp = radius_roles.get("input")
        if isinstance(_inp, dict) and _inp.get("value"):
            input_css = "\n  --c-input-radius: var(--radius-input);"

    # footer link register (B6/N3, fix-batch 2026-07): a COLUMNS-grammar footer reads the
    # brand's measured chrome footer-link size; display-links brands keep their sitemap
    # tier device (the alias stays unresolved there so the device's structural clamp
    # applies — resolving it to WoodWave's measured 80px would regress the bookend batch).
    foot_css = ""
    if footer_grammar(doc) == "columns":
        _foot_link = ((doc.get("footer") or {}).get("measured") or {}).get("link") or {}
        if _foot_link.get("fontSize"):
            foot_css += "\n  --c-foot-link-size: var(--chrome-foot-link-size);"
        if _foot_link.get("fontWeight"):
            foot_css += "\n  --c-foot-link-weight: var(--chrome-foot-link-weight);"

    # measured nav register (single source with tokens.css --size-nav; kit gap:
    # 18px measured vs 0.875rem control-text double truth). Falls back to control size.
    nav_px = (((doc.get("navbar") or {}).get("measured") or {}).get("link") or {}).get("fontSize")
    nav_size = f"{round(nav_px / 16, 4)}rem" if nav_px else "var(--c-control-size)"

    # PER-TIER heading families + dedicated stat tier (fix1 2026-07): a brand whose
    # measured sub-heads ride a DIFFERENT family than the display register (e.g. serif
    # display over sans h3–h6) emits --c-hN-font per tier that declares one; the
    # heading classes read var(--c-hN-font, var(--c-font-heading)), so family-silent
    # tiers keep the display family byte-identically. Same gate for a measured
    # stat-display tier (--c-stat-size/--c-stat-font feed the .c-stat-value chain).
    tier_css = ""
    for _t in ("h1", "h2", "h3", "h4", "h5", "h6"):
        if type_role(doc, _t).get("family"):
            tier_css += f"\n  --c-{_t}-font: var(--font-{_t});"
    _stat = type_role(doc, "stat-display")
    if _stat:
        if base_size(_stat) is not None:
            tier_css += "\n  --c-stat-size: var(--size-stat-display-base);"
        if _stat.get("family"):
            tier_css += "\n  --c-stat-font: var(--font-stat-display);"
    return f"""{selector} {{
  --c-paper: {bg};
  --c-ink: {text};
  --c-ink-muted: {muted};
  --c-accent: {accent};
  --c-hairline: {hairline};
  --c-link-hover: {link_hover};{action_css}
  --c-font-heading: {_font_ref(doc, 'display-hero', 'Georgia, serif')};
  --c-font-body: {_font_ref(doc, 'body', 'system-ui, sans-serif')};
  --c-display-size: {display_size or _size_ref(doc, 'display-hero', 4)};
  --c-display-lh: {_tier_ref(doc, 'display-hero', 'leading', '1.05em')};
  --c-display-ls: {_tier_ref(doc, 'display-hero', 'tracking', '0rem')};
  --c-display-weight: {_tier_ref(doc, 'display-hero', 'weight', '400')};
  --c-heading-weight: {_tier_ref(doc, 'h2', 'weight', _tier_ref(doc, 'display-hero', 'weight', '400'))};
  --c-h1-size: {_size_ref(doc, 'h1', 3)};
  --c-h2-size: {_size_ref(doc, 'h2', 2.25)};
  --c-h3-size: {_size_ref(doc, 'h3', 1.625)};
  --c-h4-size: {_size_ref(doc, 'h4', 1.375)};
  --c-h5-size: {_size_ref(doc, 'h5', 1.25)};
  --c-h6-size: {_size_ref(doc, 'h6', 1.125)};
  --c-body-size: {_size_ref(doc, 'body', 1)};
  --c-body-weight: {_tier_ref(doc, 'body', 'weight', '400')};
  --c-eyebrow-size: {_size_ref(doc, 'eyebrow', 0.6875)};
  --c-eyebrow-ls: {_tier_ref(doc, 'eyebrow', 'tracking', '0em')};
  --c-control-size: {_size_ref(doc, 'control-text', 0.875)};
  --c-control-ls: {_tier_ref(doc, 'control-text', 'tracking', '0em')};
  --c-nav-size: {nav_size};
  --c-case-heading: {_tier_ref(doc, 'h2', 'case', 'none')};
  --c-case-eyebrow: {_tier_ref(doc, 'eyebrow', 'case', 'none')};
  --c-case-control: {_tier_ref(doc, 'control-text', 'case', 'none')};
  --c-eyebrow-gap: {eyebrow_gap};
  --c-title-overlap: {css_len(title_overlap, '-2.75rem')};{aspect_css}{btn_css}{input_css}{foot_css}{tier_css}
}}"""


# ── motion vars — sourced from brand.yaml voice.motionSpec ──────────────────────
# CR-3 (token-layer-2026-07): the old _MOTION_DEFAULTS dict (WoodWave's authored
# 320/480/620ms + cubic-bezier(.22,1,.36,1) as universal fallbacks) is DELETED —
# the motion trio + easing are REQUIRED tokens; a brand with no motionSpec fails loud
# at tokens generation (tokens_css.build_page_tokens), never inherits another brand's
# tempo. motion_spec() now reports the brand's values verbatim (None where silent) for
# the few non-CSS consumers (parallax gating reads only imageParallax).


def motion_spec(doc) -> dict:
    """The brand's authored motion spec (brand.yaml ``voice.motionSpec``) verbatim:
    primary easing, fast/base/slow durations, scroll-reveal translateY shift. Values are
    None where the brand is silent — REQUIRED keys are enforced at tokens-generation
    time (fail-loud), not silently defaulted here."""
    ms = ((doc or {}).get("voice") or {}).get("motionSpec") or {}
    dur = ms.get("durations") or {}
    rev = ms.get("scrollReveal") or {}
    return {
        "ease": (ms.get("easing") or {}).get("primary"),
        "fast": dur.get("fast"),
        "base": dur.get("base"),
        "slow": dur.get("slow"),
        "shift": rev.get("translateY"),
    }


def image_parallax_spec(doc) -> dict:
    """Resolve the brand's authored `voice.motionSpec.imageParallax` (a brand-level MOTION
    TREATMENT, not a per-pattern specialTreatment — it applies to every non-hero module
    image on the page, the same way `do[]`/`neverDo[]` apply globally). Returns
    `{enabled, amount}`; `enabled=False` (the default) when the brand is silent, so a brand
    that never declared this treatment renders byte-identical to before — this is opt-in,
    not a global default for every project. `amount` is a class (light|medium|heavy),
    resolved to a concrete yPercent range only at the JS layer (never px in the spec)."""
    ms = ((doc or {}).get("voice") or {}).get("motionSpec") or {}
    p = ms.get("imageParallax") or {}
    return {"enabled": bool(p.get("enabled")), "amount": p.get("amount") or "light"}


def motion_vars_css(doc, selector=":root") -> str:
    """Emit the motion ``--c-*`` aliases as var() references into the generated layer-1
    block (``--motion-*``, tokens_css) so the shared motion rules (underline draw-in,
    scroll reveal, arrow nudge) read the brand's authored easing + durations from ONE
    source. ``--c-reveal-shift`` is aliased only when the brand declares scrollReveal
    (OPTIONAL token: absent ⇒ the reveal is fade-only, never another brand's shift)."""
    shift = " --c-reveal-shift: var(--motion-shift);" if motion_spec(doc)["shift"] else ""
    return (f"{selector} {{ --c-ease: var(--motion-ease); "
            f"--c-motion-fast: var(--motion-fast); "
            f"--c-motion-base: var(--motion-base); "
            f"--c-motion-slow: var(--motion-slow);{shift} }}")


# ── link hover treatment (extracted measured hover color, gated by motion mode) ──────
#
# The brand's link interaction has TWO modes (voice.motionSpec.link.mode):
#   - "underline-draw" (DEFAULT): the animated underline that draws in (scaleX 0→100%),
#     baked into COMPONENT_CSS. Brands like HubSpot keep this — untouched.
#   - "color-shift": the link swaps to the brand's MEASURED link-hover color on hover
#     (WoodWave nav/footer links go gold #edd580). This reads the extracted
#     `footer.measured.linkHoverColor` (or `navbar.measured.linkHoverColor`) that was
#     already persisted but previously dropped by the renderer.
# The gate is opt-in per brand, so every other brand renders byte-identical.

def link_hover_color(doc) -> str | None:
    """The brand's EXTRACTED measured link-hover color (footer preferred, then navbar).
    Returns None when the brand carries no measured hover color."""
    for blk in ((doc or {}).get("footer"), (doc or {}).get("navbar")):
        measured = (blk or {}).get("measured") or {}
        c = measured.get("linkHoverColor")
        if isinstance(c, str) and c.strip():
            return c.strip()
    return None


def link_mode(doc) -> str:
    """Resolve the brand's link interaction mode: ``color-shift`` or ``underline-draw``
    (the default). Reads ``voice.motionSpec.link.mode`` first; falls back to interpreting
    the legacy ``link.value`` string so a brand that only carries the descriptive value
    still resolves sensibly."""
    link = (((doc or {}).get("voice") or {}).get("motionSpec") or {}).get("link") or {}
    mode = str(link.get("mode") or "").strip().lower()
    if mode in ("color-shift", "underline-draw"):
        return mode
    val = str(link.get("value") or "").lower()
    if "color" in val:
        return "color-shift"
    return "underline-draw"


def link_hover_css(doc) -> str:
    """Emit the color-shift link-hover CSS (``--c-link-hover`` + ``:hover{color:…}`` on the
    typographic link primitives), GATED on ``voice.motionSpec.link.mode == color-shift``.

    Returns "" for underline-draw brands so their output is byte-identical (they keep the
    COMPONENT_CSS underline draw-in). For color-shift brands the underline pseudo-element is
    disabled (``content: none``) so the interaction is a clean single color swap.

    anti-ai-slop.md AS-01/AS-10: the `:root` value here is a SAFE FALLBACK (`var(--c-ink)`
    -- no visible color shift), NOT the brand's measured accent hover color. That measured
    color (WoodWave: `#edd580` gold, measured against the DARK footer/nav) has a 1.3:1
    contrast ratio against the CREAM surface -- a WCAG failure (needs >=4.5:1 for text,
    >=3:1 minimum for UI) that also breaks the brand's own `no-accent-on-light` rule; it
    only ever showed up on `:hover`, invisible to a static neverDo check of the resting
    HTML. The REAL per-surface value (gold on dark, ink on light) is set by
    `component_vars`/`root_vars` -- those emit `--c-link-hover` scoped to EACH surface,
    which wins over this `:root` fallback by selector specificity regardless of source
    order. Never re-introduce a single unconditional accent hover here."""
    if link_mode(doc) != "color-shift":
        return ""
    return f"""
/* link hover (color-shift mode) -- SAFE default here; the real per-surface value (accent
   on dark, ink on light) is set by component_vars/root_vars (anti-ai-slop.md AS-10). */
:root {{ --c-link-hover: var(--c-ink); }}
.c-arrow-link, .c-foot-sitemap-link, .c-foot-social-link {{
  transition: color var(--c-motion-fast) var(--c-ease); }}
.c-arrow-link:hover, .c-arrow-link:focus-visible,
.c-foot-sitemap-link:hover, .c-foot-sitemap-link:focus-visible,
.c-foot-social-link:hover, .c-foot-social-link:focus-visible {{ color: var(--c-link-hover); }}
/* color-shift REPLACES the underline draw-in for these links (no double signal). */
.c-arrow-link::after, .c-foot-sitemap-link::after, .c-foot-social-link::after {{ content: none; }}
"""


# ── RESPONSIVE render (Phase 4, hero + footer slice) ────────────────────────────────
#
# The composer's default hero band is a FIXED px height and its footer directory a
# NON-responsive grid — two missing-fact divergences the computed-CSS property-diff
# harness (css_fidelity.py) surfaces. These two emitters consume the Phase-2
# ``responsive`` fact block (layouts[].responsive / footer.responsive, merged from the
# responsive-facts.yaml sidecar at load) and emit the grounded responsive CSS.
#
# FACT-GATED + BYTE-STABLE: each returns "" when the fact block is absent, so every
# brand/component without a ``responsive`` block renders byte-for-byte as before. The
# rules are SCOPED to the hero/footer section id, so no other component is touched.
# Every value traces to a measured fact (provenance rides in the sidecar) — the
# token-provenance doctrine extended from color to layout + motion for these paths.

def _resp_len(value) -> str | None:
    """A whitelisted CSS length token (``48px`` / ``55px`` / ``128px``) from a fact,
    or None. Guards the fact→CSS boundary so only measured length literals emit."""
    if isinstance(value, (int, float)):
        return f"{int(value)}px" if float(value).is_integer() else f"{value}px"
    m = re.fullmatch(r"\s*(-?\d*\.?\d+)(px|rem|em|dvh|svh|vh|%)\s*", str(value or ""))
    return f"{m.group(1)}{m.group(2)}" if m else None


def hero_responsive_css(responsive, sec_sel: str) -> str:
    """Grounded responsive CSS for a hero section from its ``responsive`` fact block:

      * ``heightRule: viewport-minus-nav`` → the hero media canvas fills the viewport
        minus the measured nav offset (``calc(100dvh - <nav>)``, dvh like the source),
        flex-centering its on-media content (already the .cs-ov-onmedia default);
      * ``headingSizeLadder`` → the measured heading font-size/line-height SHRINK below
        the measured breakpoint (desktop rung is left to the brand's own type scale, so
        wide-viewport output stays byte-identical).

    Returns "" when the block is absent/none (fact-gate)."""
    if not isinstance(responsive, dict):
        return ""
    parts: list[str] = []
    rule = responsive.get("heightRule")
    if rule in ("viewport-minus-nav", "viewport"):
        nav = responsive.get("navOffset") or {}
        base = _resp_len(nav.get("base")) or "0px"
        wide = _resp_len(nav.get("wide"))
        wide_min = nav.get("wideMinWidth")
        if rule == "viewport-minus-nav":
            parts.append(f"{sec_sel} {{ --c-hero-nav-offset: {base}; }}")
            if wide and isinstance(wide_min, (int, float)):
                parts.append(f"@media (min-width: {int(wide_min)}px) {{ "
                             f"{sec_sel} {{ --c-hero-nav-offset: {wide}; }} }}")
            expr = "calc(100dvh - var(--c-hero-nav-offset, 0px))"
        else:
            expr = "100dvh"
        # A viewport-height hero is FULL-BLEED (like the source header): the inner
        # .cs-section drops its padding so the band is exactly the viewport-height
        # (border-box) and spans edge-to-edge; the frame releases the shared measure so
        # the media canvas covers the full width at every viewport. The on-media overlay
        # (inset:0, justify-center) keeps its own padding, centering the heading/CTAs.
        parts.append(f"{sec_sel} .cs-section {{ min-height: {expr}; "
                     "padding-block: 0; padding-inline: 0; }")
        parts.append(f"{sec_sel} .cs-ov-frame {{ max-width: none; }}")
        # The canvas is a DEFINITE viewport-height box (height, not just min-height) so
        # the covering photo has a height to fill; its AUTHORED aspect-ratio (set inline)
        # is neutralized (`auto !important` beats the inline value) so it can't drive the
        # width to height × ratio and overflow. The image COVERS the full-bleed box.
        parts.append(f"{sec_sel} .cs-ov-canvas {{ min-height: {expr}; height: {expr}; "
                     "aspect-ratio: auto !important; }")
        parts.append(f"{sec_sel} .cs-ov-canvas > .c-image, "
                     f"{sec_sel} .cs-ov-canvas > .c-image-ph "
                     f"{{ aspect-ratio: auto !important; width: 100%; height: 100%; "
                     "object-fit: cover; }")
    ladder = responsive.get("headingSizeLadder")
    if isinstance(ladder, list):
        small = next((e for e in ladder if isinstance(e, dict) and e.get("maxWidth")),
                     None)
        if small:
            fs = _resp_len(small.get("fontSize"))
            lh = _resp_len(small.get("lineHeight"))
            decls = []
            if fs:
                decls.append(f"font-size: {fs}")
            if lh:
                decls.append(f"line-height: {lh}")
            if decls:
                parts.append(
                    f"@media (max-width: {int(small['maxWidth'])}px) {{ "
                    f"{sec_sel} :is(h1, .c-heading--display) {{ {'; '.join(decls)}; }} }}")
    if not parts:
        return ""
    head = ("/* responsive hero (fact-gated: layouts[].responsive) — viewport-minus-nav "
            "height + measured heading shrink; provenance in responsive-facts.yaml. */")
    return head + "\n" + "\n".join(parts) + "\n"


def footer_responsive_css(doc, sec_sel: str) -> str:
    """Grounded responsive CSS for the closing-bookend footer from
    ``footer.responsive``:

      * ``grid`` → the directory RE-FLOWS at the measured breakpoint (stacked to one
        column below it, the composer's multi-column layout at/above), matching the
        source's ``@media`` column reflow;
      * ``maxWidth`` → the inner content caps at the REAL measured content width and the
        band paints FULL-BLEED (the invented band max-width cap is purged — Phase 3).

    Returns "" when the block is absent (fact-gate)."""
    resp = (doc.get("footer") or {}).get("responsive") if isinstance(doc, dict) else None
    if not isinstance(resp, dict):
        return ""
    parts: list[str] = []
    # Phase 3 purge + measured cap: un-cap the band (source band max-width:none); cap the
    # inner content wrappers at the measured contentMaxWidth via --cf-cols-max (cols /
    # bottom-bar / centered-stack all read it) so the visible content width is unchanged.
    cmw = _resp_len((resp.get("maxWidth")))
    band_decls = ["max-width: none"]
    if cmw:
        band_decls.append(f"--cf-cols-max: {cmw}")
    parts.append(f"{sec_sel} .c-footer {{ {'; '.join(band_decls)}; }}")
    grid = resp.get("grid") or {}
    bp = grid.get("breakpoint")
    below = grid.get("columnsBelow", 1)
    if isinstance(bp, (int, float)) and int(below) <= 1:
        # stacked → multi-column reflow: below the breakpoint the directory is one
        # column (the source's mobile stack); at/above it keeps the composer's grid.
        parts.append(
            f"@media (max-width: {float(bp) - 0.02:g}px) {{ "
            f"{sec_sel} .c-foot-cols {{ grid-template-columns: 1fr; }} }}")
    head = ("/* responsive footer (fact-gated: footer.responsive) — @media column reflow "
            "+ measured content cap; band full-bleed (invented max-width purged). */")
    return head + "\n" + "\n".join(parts) + "\n"


def hero_primary_button_css(responsive, sec_sel: str) -> str:
    """Grounded geometry for the hero PRIMARY button from ``responsive.primaryButton``
    (measured @1440): font-size / line-height / border / padding the composer left
    un-grounded (14px vs the source's 18px, no reserved border box). Scoped to the hero
    section's non-nav button so no other control is touched. "" without the block."""
    if not isinstance(responsive, dict):
        return ""
    btn = responsive.get("primaryButton")
    if not isinstance(btn, dict):
        return ""
    decls: list[str] = []
    fs = _resp_len(btn.get("fontSize"))
    lh = _resp_len(btn.get("lineHeight"))
    if fs:
        decls.append(f"font-size: {fs}")
    if lh:
        decls.append(f"line-height: {lh}")
    pad = str(btn.get("padding") or "").strip()
    if re.fullmatch(r"(?:-?\d*\.?\d+(?:px|rem|em)\s*){1,4}", pad or ""):
        decls.append(f"padding: {pad}")
    border = str(btn.get("border") or "").strip()
    # accept a measured border shorthand (width style colour) — colour is normalized to
    # transparent upstream, so no palette leaks; the border only RESERVES the box width.
    if re.fullmatch(r"\d*\.?\d+px\s+(?:solid|dashed|dotted)\s+[\w#().,%\s-]+", border):
        decls.append(f"border: {border}")
    if not decls:
        return ""
    sel = f"{sec_sel} .c-button:not(.c-button--navcta)"
    head = ("/* responsive hero primary button (fact-gated: layouts[].responsive."
            "primaryButton) — measured control box (font-size/line-height/border/"
            "padding); the composer left it at the small control tier. */")
    return f"{head}\n{sel} {{ {'; '.join(decls)}; }}\n"


def heading_responsive_css(doc) -> str:
    """Grounded heading line-heights from ``responsive.headings.lineHeights`` (measured
    per generic heading tag). The composer type scale mis-derives some heading
    line-heights (h2 23.4px vs the measured 28px); this pins the measured value on the
    generic heading role. "" without the block (fact-gate; v2/remote unchanged)."""
    resp = ((doc or {}).get("responsive") or {}).get("headings") \
        if isinstance(doc, dict) else None
    if not isinstance(resp, dict):
        return ""
    lhs = resp.get("lineHeights") if isinstance(resp.get("lineHeights"), dict) else {}
    parts: list[str] = []
    for tag in ("h1", "h2", "h3", "h4"):
        lh = _resp_len(lhs.get(tag))
        if lh:
            parts.append(f":is({tag}, .c-heading--{tag}) {{ line-height: {lh}; }}")
    if not parts:
        return ""
    head = ("/* responsive headings (fact-gated: responsive.headings.lineHeights) — "
            "measured heading line-heights the composer type scale mis-derived. */")
    return head + "\n" + "\n".join(parts) + "\n"


# ── scroll-parallax motion treatment (brand-level; voice.motionSpec.imageParallax) ──
#
# SINGLE SOURCE OF TRUTH for both build_page (compose_page.py) and build_document
# (compose_section.py) — a hand-duplicated copy per builder is exactly how the
# `.cs-conversion` centering bug happened (see compose_page.page_style_override's
# docstring). Both callers import this module as `cr` and call these three functions;
# neither builder re-declares its own copy.
#
# TWO MOTION KINDS, one brand-level toggle (`voice.motionSpec.imageParallax`):
#   1. MASK-PAN — a single image inside an `overflow:hidden` wrapper (the module images:
#      collage/split/statement/quote/visit/gallery media) pans vertically within its own
#      frame as the page scrolls. Requires the image to be scaled up (oversized) so the
#      pan never reveals empty space at the mask's edge.
#   2. DEPTH (differential-rate) — an OVERLAPPING PAIR of images (the hero's media-over-
#      media collage: `.c-image--hero` + `.c-image--overlap`, scoped to `.cs-collage` so
#      it never catches the SAME variant classes reused elsewhere for plain module photos)
#      move at DIFFERENT rates during scroll, so the overlap visibly deepens/shifts rather
#      than staying static — the motion counterpart of the `overlap` special treatment
#      already captured structurally in layout-patterns.v1 (brand-schema.md §4.4). This is
#      the reusable MOTION RULE for editorial/collage-style sites with overlapping media:
#      wherever a pattern records `specialTreatments: [{kind: overlap, pair: [...]}]`
#      between two MEDIA slots, the depth-parallax rule applies by default when the brand
#      has imageParallax enabled — never on text-over-media overlaps (the hero title over
#      its photo stays static; only the two PHOTOS get differential rates).
#
# Amount classes resolve to a base yPercent unit (never px — container/breakpoint safe):
_PARALLAX_AMOUNT_YPCT = {"light": 6, "medium": 10, "heavy": 16}

# The CANONICAL mask-pan wrapper (`.c-image-mask`, component_render.py COMPONENT_CSS) wraps
# ONLY an <img> — never a sibling caption — so the scale/translate below can never bleed
# into caption text sharing the same figure/div (a real bug: a caption sitting beside the
# image in the SAME overflow:hidden box got visually overlapped by the scaled/panning
# image). One wrapper class used everywhere replaces the earlier per-section wrapper-class
# list, so the CSS oversize rule and the JS query selector share a single source of truth.


def parallax_css(doc) -> str:
    """CSS for the scroll-parallax treatment. Returns "" when the brand hasn't declared
    `voice.motionSpec.imageParallax` (opt-in; every other brand/project renders unchanged).
    The oversize scale applies ONLY to `.c-image-mask` images — NEVER to the hero's
    `.cs-collage` overlap pair, whose exact aspect-ratio/crop is load-bearing for the
    overlap composition; the depth treatment moves those via translate only, no scale."""
    spec = image_parallax_spec(doc)
    if not spec["enabled"]:
        return ""
    return """
/* scroll-parallax (brand motion treatment; voice.motionSpec.imageParallax) */
[data-parallax-images] .c-image-mask .c-image { transform: scale(1.12); will-change: transform; }
@media (prefers-reduced-motion: reduce) {
  [data-parallax-images] .c-image-mask .c-image { transform: none !important; }
}
"""


PARALLAX_SCRIPT = """<script src="https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/gsap.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/ScrollTrigger.min.js"></script>
<script>
(function () {
  var mq = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)');
  if (mq && mq.matches) return;                 // reduced motion: no parallax, all static
  if (!window.gsap || !window.ScrollTrigger) return;
  gsap.registerPlugin(ScrollTrigger);
  var AMT = __AMOUNT_YPCT__;                    // base yPercent unit (brand amount class)

  // 1) MASK-PAN — one image per `.c-image-mask` wrapper, pans within its own frame. The
  // wrapper (not the image) is the ScrollTrigger trigger AND the clip boundary, so the
  // caption sitting outside the mask (a sibling in the parent figure) is never touched.
  document.querySelectorAll('.c-image-mask').forEach(function (wrap) {
    var img = wrap.querySelector('.c-image');
    if (!img) return;
    gsap.fromTo(img, { yPercent: -AMT }, { yPercent: AMT, ease: 'none',
      scrollTrigger: { trigger: wrap, start: 'top bottom', end: 'bottom top', scrub: 0.5 } });
  });

  // 2) DEPTH — the hero's overlapping media pair moves at DIFFERENT rates (motion
  // counterpart of the `overlap` special treatment; scoped to `.cs-collage` so it never
  // catches a plain module photo that happens to reuse the same variant class).
  var heroCollage = document.querySelector('.cs-collage');
  if (heroCollage) {
    var base = heroCollage.querySelector('.c-image--hero');
    var front = heroCollage.querySelector('.c-image--overlap');
    if (base) gsap.fromTo(base, { yPercent: -AMT * 0.4 }, { yPercent: AMT * 0.4, ease: 'none',
      scrollTrigger: { trigger: heroCollage, start: 'top bottom', end: 'bottom top', scrub: 0.5 } });
    if (front) gsap.fromTo(front, { yPercent: -AMT * 1.2 }, { yPercent: AMT * 1.2, ease: 'none',
      scrollTrigger: { trigger: heroCollage, start: 'top bottom', end: 'bottom top', scrub: 0.5 } });
  }
})();
</script>"""


def parallax_script_tags(doc) -> str:
    """GSAP CDN + init script, or "" when the brand hasn't declared imageParallax."""
    spec = image_parallax_spec(doc)
    if not spec["enabled"]:
        return ""
    amt = _PARALLAX_AMOUNT_YPCT.get(spec["amount"], _PARALLAX_AMOUNT_YPCT["light"])
    return PARALLAX_SCRIPT.replace("__AMOUNT_YPCT__", str(amt))


# The shared component stylesheet. NEVER uses viewport units. Separation is fill
# contrast + container-query / rem geometry only; radius is the brand radius var; no
# shadows, borders, gradients, or hairline section rules (honors WoodWave neverDo).
COMPONENT_CSS = """
/* ── shared catalog components (single source of truth) ── */
/* text-wrap defaults (anti-ai-slop.md AS-15): headings/eyebrows/captions balance their
   line breaks (no orphaned last word on a display heading); paragraphs use balanced
   wrapping too — engines cap balance at ~6 lines, so long body copy is unaffected while
   short paragraphs stop orphaning. */
.c-heading, .c-eyebrow, .c-caption { text-wrap: balance; }
p { text-wrap-style: balance; }
.c-heading { font-family: var(--c-font-heading); color: var(--c-ink); margin: 0;
  /* case comes from the brand's own heading register (CR-1): uppercase is a MEASURED
     brand fact (--case-h2 via --c-case-heading), never a shared-CSS assumption. */
  text-transform: var(--c-case-heading);
  font-weight: var(--c-heading-weight, var(--c-display-weight)); }
.c-heading--display { font-size: var(--c-display-size); line-height: var(--c-display-lh);
  letter-spacing: var(--c-display-ls); }
/* h1 SECTION register (fix1 2026-07): a pattern-measured headingRegister may name
   the brand's h1 tier for one band (an up-tier showcase headline below the hero);
   "display"/"h0"/"hero" levels keep the display class — nothing re-mapped. */
.c-heading--h1 { font-size: var(--c-h1-size); line-height: var(--leading-h1, 1.15em);
  font-family: var(--c-h1-font, var(--c-font-heading)); }
.c-heading--h2 { font-size: var(--c-h2-size); line-height: 1.3em;
  font-family: var(--c-h2-font, var(--c-font-heading)); }
.c-heading--h3 { font-size: var(--c-h3-size); line-height: 1.3em;
  /* per-tier family (fix1 2026-07): a tier that MEASURES its own family (e.g. sans
     sub-heads under a serif display) rides it; family-silent tiers fall back to the
     display family — byte-identical for brands without per-tier declarations. */
  font-family: var(--c-h3-font, var(--c-font-heading)); }
/* sub-h3 registers (fid6 2026-07): module/card headings whose brand declares a
   deeper register (blocks.card slots.heading.register) ride the tier's OWN measured
   size + leading vars from layer 1; structural fallbacks keep ladder-less brands. */
.c-heading--h4 { font-size: var(--c-h4-size); line-height: var(--leading-h4, 1.3em);
  font-family: var(--c-h4-font, var(--c-font-heading)); }
.c-heading--h5 { font-size: var(--c-h5-size); line-height: var(--leading-h5, 1.4em);
  font-family: var(--c-h5-font, var(--c-font-heading)); }
.c-heading--h6 { font-size: var(--c-h6-size); line-height: var(--leading-h6, 1.4em);
  font-family: var(--c-h6-font, var(--c-font-heading)); }
.c-heading--accent { color: var(--c-accent); }
/* stepped-lines (G7): each authored line is a block; the scaffold sets the per-line
   registered indent via --c-step-N (half-column multiples of the shared grid). */
.c-heading-line { display: block; }
/* mixed-face (G5): face contrast INSIDE one heading. Default is weight contrast (safe
   for brands with no italic cut — never a synthesized italic); a brand shipping a real
   italic sets --c-alt-style: italic. */
.c-heading-alt { font-style: var(--c-alt-style, normal);
  font-weight: var(--c-alt-weight, 500); }

.c-eyebrow { font-family: var(--c-font-body); font-size: var(--c-eyebrow-size);
  letter-spacing: var(--c-eyebrow-ls); text-transform: var(--c-case-eyebrow);
  /* a section's declared eyebrow register (layout.eyebrowRegister → section-scoped
     --c-eyebrow-color) wins; undeclared sections keep the muted-ink default. */
  color: var(--c-eyebrow-color, var(--c-ink-muted)); margin: 0; }

.c-image { display: block; width: 100%; border: none; box-shadow: none;
  border-radius: var(--radius); object-fit: cover;
  /* PLACEHOLDER BACKING (anti-ai-slop AS-23): unresolved/loading and error states carry
     a diagonal-hatch plate DERIVED FROM THE SURFACE'S OWN TOKENS (never a hardcoded hex
     at this level — AS-01). A successful load is stamped data-load-state="loaded" by
     interaction_script and removes this backing completely, so transparent pixels reveal
     the real parent surface. Error deliberately has no override and retains this fallback.
     PAPER-dominant mixes (the plate is the surface, gently lifted toward its ink):
     on a dark hero surface this resolves to a matching dark hatch pair, on a light
     canvas to a pale one. */
  background: repeating-linear-gradient(135deg,
    var(--c-paper) 0px,
    var(--c-paper) 13px,
    color-mix(in srgb, var(--c-paper) 93%, var(--c-ink)) 13px,
    color-mix(in srgb, var(--c-paper) 93%, var(--c-ink)) 26px); }
/* Image load-state contract: attribute ABSENT = unresolved/loading; loaded = real asset
   painted and NO backing; error = hatch fallback (inherits .c-image above). Do not use
   src presence as load truth — cached and lazy images are reconciled by the shared JS. */
.c-image[data-load-state="loaded"] { background: none; }
/* hero-collage occlusion geometry: this exact base/overlap crop PAIR is what makes the
   layered collage device read (the spacer clearance math + depth parallax derive from
   it — see .cs-spacer + parallax_css docstrings). Compositions that declare mediaAspect
   override it inline per §4.6.5; brands without the collage device never render these
   classes. */
.c-image--hero { /* provenance: structural — collage occlusion geometry */
  aspect-ratio: 1355 / 570; }
.c-image--overlap { /* provenance: structural — collage occlusion geometry */
  aspect-ratio: 785 / 620; }
/* transparent-PNG-safe ART mode (fid2 2026-07): non-photographic art (illustrations,
   product-UI graphics, marks) renders CONTAINED at its natural aspect on a clean field.
   `background: none` remains the JS-disabled fallback: media facts authorize this mode,
   never filename/brand inference. With JS, all successful images converge on the same
   loaded/no-backing state. `aspect-ratio: auto` releases the collage variants'
   photographic crop geometry; a DECLARED mediaAspect (inline style) still wins. */
.c-image--art { object-fit: contain; background: none; aspect-ratio: auto; }
/* the CANONICAL mask-pan wrapper — wraps ONLY the <img>, never a sibling caption, so the
   scroll-parallax scale/translate (parallax_css/parallax_script_tags) can never bleed into
   caption text sitting beside it in the same figure/div. Structural, always present
   (harmless when parallax is disabled: overflow:hidden around an unscaled, untransformed
   image is visually a no-op — a plain wrapper). See brand-schema.md §4.4.1. */
.c-image-mask { display: block; overflow: hidden; }
/* placeholder used by the gallery when no real asset is bound (keeps the gallery
   self-contained); composed sections always bind a real image src. */
.c-image-ph { display: flex; align-items: center; justify-content: center;
  background: var(--c-ink); color: var(--c-paper); border-radius: var(--radius);
  /* provenance: structural — placeholder plate geometry (gallery/unbound slots only;
     composed sections always bind a real src, and declared aspects win inline) */
  aspect-ratio: 4 / 3; font-family: var(--c-font-body); font-size: var(--c-eyebrow-size);
  letter-spacing: var(--c-eyebrow-ls); text-transform: var(--c-case-control); }

.c-arrow-link { font-family: var(--c-font-body); font-size: var(--c-control-size);
  letter-spacing: var(--c-control-ls); text-transform: var(--c-case-control);
  text-decoration: none;
  color: var(--c-action-color, currentColor); display: inline-flex; align-items: center;
  gap: 0.5rem; background: none; border: none; cursor: pointer; padding: 0;
  /* CONTENT HUG (fix3, AS-61): the link's box — and therefore its underline ink
     (the ::after spans the box) — hugs label + glyph in EVERY placement. Inside
     column flex stacks (card footers, tab-card bodies) flex items are blockified
     and STRETCH by default, so `inline-flex` alone painted the hover underline to
     the card's far edge; `fit-content` beats the stretch (stretch only applies to
     auto widths) and is a no-op in rows and inline contexts. This is the hug end
     of the containment-vs-measure-vs-hug discipline: a typographic action owns no
     column, so its box never spans one. */
  width: fit-content; }
.c-arrow-link--accent { color: var(--c-accent); }
/* CHROME register pin (sysfix 2026-07): NAV links are chrome, not in-flow text
   actions — they read the surface ink (their measured --chrome-* registers own any
   deviation), never the page's typographic-action color (--c-action-color). */
.cs-navlinks .c-arrow-link { color: currentColor; }
/* MEASURED nav-CTA pill (fid2 2026-07): scoped consumption vars set inline by
   render_navbar from the brand's extracted chrome-CTA facts — the nav CTA renders its
   OWN measured surface (e.g. a neutral filled pill), never the page accent default.
   Rule is inert for brands without the facts (the class never renders). */
.c-button.c-button--navcta { /* provenance: structural chrome-CTA fallbacks — the
     var() values are the brand's measured navcta facts set inline by render_navbar;
     the literals are inert defaults behind them (pill idiom / white-on-fill ink) */
  background: var(--navcta-bg); color: var(--navcta-ink, #fff);
  /* border channel (fix1 2026-07 item-12b): an outlined secondary register in the
     bar's action group draws its measured stroke; the none default keeps every
     existing single-cta brand's computed style identical. */
  border: var(--navcta-border, none); border-radius: var(--navcta-radius, 999px);
  height: var(--navcta-height, auto);
  /* pad-y default (2026-07): a measured-facts-less CTA had `0` vertical padding
     and relied on height:auto, collapsing to a too-narrow text-height chip.
     A 0.5rem vertical floor gives a real button box; measured padY overrides it. */
  padding: var(--navcta-pad-y, 0.5rem) var(--navcta-pad-x, 1.25rem);
  font-size: var(--navcta-size, var(--c-control-size));
  display: inline-flex; align-items: center; }
.c-button.c-button--navcta:hover, .c-button.c-button--navcta:focus-visible {
  /* keep the CTA's own ink on hover — the generic .c-button:hover otherwise sets
     color to --c-paper (white on a white nav), turning an unfilled orange-ink CTA
     white-on-white on hover (2026-07). */
  background: var(--navcta-bg); color: var(--navcta-ink, #fff); filter: brightness(1.06); }

.c-arrow { transition: transform var(--c-motion-fast) var(--c-ease); }
.c-arrow-link:hover .c-arrow { transform: translateX(0.35rem); }
/* MEASURED text-CTA glyph (fix2, buttons.<family>.glyph; fix4 inline channel):
   the brand's harvested SVG arrow as sanitized INLINE markup — fill rides
   currentColor, so ink follows the link's own color chain; box from the measured
   fact (inline var). The nested svg fills the box (default xMidYMid meet ≙ the
   old mask's `center / contain`). Inert for glyph-less brands (never renders). */
.c-arrow--glyph { display: inline-block; flex: none;
  width: var(--c-arrow-glyph-size, 1em); height: var(--c-arrow-glyph-size, 1em); }
.c-arrow--glyph > svg { display: block; width: 100%; height: 100%; }
/* mask DEGRADE (fix4): artwork that failed single-ink verification keeps the fix2
   currentColor-mask channel — never a silent recolor of multi-color art. */
.c-arrow--mask { background-color: currentColor;
  -webkit-mask: var(--c-arrow-glyph) center / contain no-repeat;
  mask: var(--c-arrow-glyph) center / contain no-repeat; }

/* wordmark logo (harness/wordmark brands; navs with an extracted image logo use
   .c-logo--img): the TEXT-LOGO device renders in the brand's own control register —
   weight from the heading register, tracking/case from control-text (CR-4). */
.c-logo { display: inline-flex; align-items: center; gap: 0.5rem; font-family: var(--c-font-body);
  font-weight: var(--c-logo-weight, var(--c-heading-weight));
  font-size: var(--c-control-size);
  letter-spacing: var(--c-logo-ls, var(--c-control-ls));
  text-transform: var(--c-logo-case, var(--c-case-control));
  color: var(--c-logo-color, var(--c-accent)); }
.c-logo .c-glyph { font-family: var(--c-font-heading);
  font-size: calc(var(--c-control-size) * 1.25); }
/* image logo (composed nav): the extracted brand logo as a plain linked <img>, no chip,
   no border, no radius. Height-capped from the extracted logo proportions (so it scales
   down gracefully); width:auto keeps the aspect ratio. An extracted logo file already
   carries its own brand color, so it reads on the brand's chrome surface with no filter. */
.c-logo--img { display: inline-flex; align-items: center; text-decoration: none;
  border: none; border-radius: 0; }
.c-logo-img { display: block; height: var(--chrome-nav-logo-h, 1.625rem);
  width: auto; max-width: 12rem; }

/* header block: eyebrow -> heading (+ optional subhead/cta) typographic cluster */
.c-header { display: flex; flex-direction: column; gap: var(--c-eyebrow-gap); }

/* paragraph primitive: narrow offset body in the brand body register, generous leading.
   font-weight rides the brand's measured body tier (N1, fix-batch 2026-07): a brand
   whose body register is light (300) must not silently render at the UA's 400. */
.c-paragraph { font-family: var(--c-font-body); font-size: var(--c-body-size);
  font-weight: var(--c-body-weight);
  line-height: 1.55em; color: var(--c-ink-muted);
  /* measure chain (fid11): explicit slot measure > the brand's authored description
     measure (tokens.spacing.body-measure) > the structural 34ch default */
  max-width: var(--c-measure, var(--space-body-measure, 34ch)); margin: 0; }

/* caption primitive: muted uppercase margin micro-text (never over media). */
.c-caption { font-family: var(--c-font-body); font-size: var(--c-eyebrow-size);
  letter-spacing: var(--c-eyebrow-ls); text-transform: var(--c-case-eyebrow);
  color: var(--c-ink-muted); margin: 0; }

/* form block + underline field: NO box, NO fill, NO border — the single 1px rule is a
   pseudo-element (height:1px+background), so it never reads as a boxed input or a section
   hairline (honors a no-boxed-inputs / no-section-hairlines neverDo). */
.c-form { display: flex; flex-direction: column;
  /* form-stack fact (B8 2026-07): the brand's measured form-module stack rhythm
     wins; the structural 1.25rem stays as the fact-less degrade. */
  gap: var(--c-form-gap, var(--space-form-stack, 1.25rem)); }
.c-field { position: relative; display: flex; align-items: flex-end; justify-content: space-between;
  gap: 1rem; padding-bottom: 0.5rem; }
.c-field::after { content: ""; position: absolute; left: 0; right: 0; bottom: 0; height: 1px;
  background: var(--c-hairline); }
.c-field-text { font-family: var(--c-font-body); font-size: var(--c-body-size);
  text-transform: var(--c-case-control); letter-spacing: var(--c-control-ls);
  color: var(--c-ink-muted); }
/* the field's REAL control (interaction remediation 2026-07, IC-FORM-01/03): a
   readonly input the wrapping label programmatically owns — visually identical to
   the old .c-field-text span (same register, transparent, chromeless), so field
   mocks and composed conversion forms keep their exact look while becoming
   associated form controls. */
.c-field-input { appearance: none; -webkit-appearance: none; flex: 1 1 0;
  width: 0; min-width: 0; margin: 0; padding: 0; border: 0; background: transparent;
  font-family: var(--c-font-body); font-size: var(--c-body-size);
  text-transform: var(--c-case-control); letter-spacing: var(--c-control-ls);
  color: var(--c-ink-muted); }
.c-field-input::placeholder { color: var(--c-ink-muted); opacity: 1; }

/* ruled action rows (the divider primitive): label left, value/action right, separated by a
   1px pseudo-rule INSIDE a panel only — never as a section seam. */
.c-rows { display: flex; flex-direction: column; }
.c-row { position: relative; display: flex; align-items: baseline; justify-content: space-between;
  gap: 1rem; padding: 0.85rem 0; }
.c-row::before { content: ""; position: absolute; left: 0; right: 0; top: 0; height: 1px;
  background: var(--c-hairline); }
.c-row-label { font-family: var(--c-font-body); font-size: var(--c-control-size);
  letter-spacing: var(--c-control-ls); text-transform: var(--c-case-control);
  color: var(--c-ink); }
.c-row-value { font-family: var(--c-font-heading); font-size: var(--c-h3-size); color: var(--c-ink); }

/* stat primitive (contracts/primitives.yaml `stat`, W4): a big metric VALUE on the
   brand's own heading register + a muted supporting LABEL on the body register.
   The value rides the measured h2 tier by default (--c-stat-size override wins when a
   brand ever measures a dedicated stat tier) — display stays reserved for the hero.
   STAT PAIR BINDING (fix7 punch 4): the value→label seam is the statPair rung — the
   TIGHTEST gap in any block the stat sits in (a brand-authored `stat-pair` spacing
   token wins; the 0.5rem structural default already satisfies the <= 0.5x-sibling-gap
   law everywhere). The old eyebrow-to-heading ride-along re-registered the pair to a
   24px header seam, collapsing the value/label hierarchy against its siblings. */
.c-stat { display: flex; flex-direction: column; gap: var(--space-stat-pair, 0.5rem); }
.c-stat-value { font-family: var(--c-stat-font, var(--c-font-heading)); color: var(--c-ink);
  text-transform: var(--c-case-heading);
  font-weight: var(--c-heading-weight, var(--c-display-weight));
  font-size: var(--c-stat-size, var(--c-h2-size)); line-height: 1.1em; }
.c-stat-label { font-family: var(--c-font-body); font-size: var(--c-body-size);
  font-weight: var(--c-body-weight); line-height: 1.5em; color: var(--c-ink-muted);
  max-width: var(--space-body-measure, 34ch); }

/* marked list (fix7 punch 3 — the checklist device): content-block items rendered as
   a REAL list when the composition declares list intent. Hanging indent by grid
   construction (marker track + text track); item stride rides the brand's own
   list-item-gap rung. The MARKER is the brand's licensed glyph in the accent role
   (inline-SVG channel) where an accentDevices marked-list-glyph license exists —
   license-less brands keep the typographic dot at ink (semantic, never invented). */
.c-marked-list { list-style: none; margin: 0; padding: 0; display: flex;
  flex-direction: column; gap: var(--space-list-item-gap, 0.75rem);
  font-family: var(--c-font-body); font-size: var(--c-body-size);
  font-weight: var(--c-body-weight); line-height: 1.5em; color: var(--c-ink);
  max-width: var(--c-measure, 62ch); }
.c-marked-list > li { display: grid;
  grid-template-columns: var(--c-list-marker-size, 1em) minmax(0, 1fr);
  column-gap: 0.6em; align-items: start; }
.c-list-marker { display: inline-flex; width: var(--c-list-marker-size, 1em);
  height: var(--c-list-marker-size, 1em); margin-top: 0.22em;
  color: var(--c-accent-mark, var(--c-ink)); }
.c-list-marker svg { width: 100%; height: 100%; display: block; }

/* punctuation-accent device (fix7 punch 1): a landmark heading's licensed terminal
   mark in the device's own accent role — scheme-stable (--c-accent-mark is emitted
   from the LICENSE's role token, never the surface accent, so a light-surface hero
   paints the same mark the brand's landmarks evidence). */
.c-accent-mark { color: var(--c-accent-mark, var(--c-accent)); }

/* table block (contracts/blocks.yaml `table`, W4): semantic tabular data on the same
   ruled-row discipline as .c-rows — 1px hairline per row, label register for column
   heads, body register for cells. No boxes/zebra fills: rules only, brand vars only. */
.c-table-wrap { width: 100%; overflow-x: auto; }
.c-table { width: 100%; border-collapse: collapse; text-align: left; }
.c-table caption { text-align: left; padding-bottom: 0.85rem;
  font-family: var(--c-font-body); font-size: var(--c-eyebrow-size);
  letter-spacing: var(--c-eyebrow-ls); text-transform: var(--c-case-eyebrow);
  color: var(--c-ink-muted); }
.c-table th, .c-table td { padding: 0.85rem 1rem 0.85rem 0; vertical-align: top;
  border-top: 1px solid var(--c-hairline); }
.c-table thead th { font-family: var(--c-font-body); font-size: var(--c-control-size);
  font-weight: 500; letter-spacing: var(--c-control-ls); text-transform: var(--c-case-control);
  color: var(--c-ink); border-top: 0; }
.c-table tbody th { font-family: var(--c-font-body); font-size: var(--c-control-size);
  font-weight: 500; letter-spacing: var(--c-control-ls); text-transform: var(--c-case-control);
  color: var(--c-ink); }
.c-table td { font-family: var(--c-font-body); font-size: var(--c-body-size);
  font-weight: var(--c-body-weight); line-height: 1.5em; color: var(--c-ink-muted); }
/* comparison anatomy: one fixed/minmax label track gives every value the same start
   edge; the row owns the separator so it cannot jump between cells.  Labels stay on
   the compact control/body-small register, values use the section-heading register. */
.c-table--comparison { table-layout: fixed; }
.c-table--comparison col.c-table-label-col { width: 9rem; }
.c-table--comparison tbody tr { border-top: 1px solid var(--c-hairline); }
.c-table--comparison th, .c-table--comparison td { border-top: 0; }
.c-table--comparison tbody th { padding-right: var(--space-heading-to-body, 1rem); }
.c-table--comparison td { font-family: var(--c-font-body);
  font-size: var(--c-body-size); font-weight: var(--c-body-weight);
  line-height: 1.5em; color: var(--c-ink); }
@media (max-width: 767px) {
  .c-table--comparison, .c-table--comparison tbody,
  .c-table--comparison tr, .c-table--comparison th,
  .c-table--comparison td { display: block; width: 100%; }
  .c-table--comparison colgroup { display: none; }
  .c-table--comparison tbody th { padding-bottom: 0;
    padding-right: 0; }
  .c-table--comparison td { padding-top: var(--space-heading-to-body, 1rem);
    padding-right: 0; }
}

/* footer block (closing bookend): a CENTERED cluster of sitemap + TEXT social links
   (slash-separated, no icons) + a centered muted legal line, reusing the brand's
   typographic vocabulary. No boxes, borders, shadows, or radius. cq/rem units only.
   The SITEMAP REGISTER is a per-brand GRAMMAR (fix-batch 2026-07, B6): the oversized
   didone slash-sitemap vs the measured multi-column directory live in
   footer_grammar_css() and are emitted per brand — neither leaks into the other. */
.c-footer { display: flex; flex-direction: column; align-items: center; text-align: center;
  gap: var(--c-block-gap, 2.5rem); }
.c-foot-sep { color: var(--c-ink-muted); font-family: var(--c-font-heading); }
.c-foot-social { display: flex; flex-wrap: wrap; align-items: center; justify-content: center;
  gap: 0.4rem 0.9rem; margin: 0 auto; }
.c-foot-social-link { font-family: var(--c-font-body); font-size: var(--c-control-size);
  letter-spacing: var(--c-control-ls); text-transform: var(--c-case-control);
  color: var(--c-ink-muted); text-decoration: none; }
.c-foot-social .c-foot-sep { font-family: var(--c-font-body); }
.c-foot-legal { font-family: var(--c-font-body); font-size: var(--c-eyebrow-size);
  letter-spacing: var(--c-eyebrow-ls); color: var(--c-ink-muted); margin: 0; }

/* ── MOTION ── authored brand spec (brand.yaml voice.motionSpec): easing + durations
   come ONLY from the brand's --c-* motion aliases (component_render.motion_vars_css →
   generated layer-1 --motion-*). CR-3: fallback literals are GONE — a missing motion
   spec fails loud at tokens generation, it never inherits another brand's tempo.
   Motion is time + transform only — no viewport units, no new color/shadow/radius. */

/* typographic links: an underline that DRAWS IN (scaleX 0->100%, origin left), NOT a
   color swap — consistent with the typographic-link aesthetic. The rule is a 1px
   pseudo-element (height+background), never a border, so it adds no border/hairline. */
.c-arrow-link, .c-foot-sitemap-link, .c-foot-social-link { position: relative; }
.c-arrow-link::after, .c-foot-sitemap-link::after, .c-foot-social-link::after {
  content: ""; position: absolute; left: 0; right: 0; bottom: -0.08em; height: 1px;
  background: currentColor; transform: scaleX(0); transform-origin: left center;
  transition: transform var(--c-motion-base) var(--c-ease); }
.c-arrow-link:hover::after, .c-arrow-link:focus-visible::after,
.c-foot-sitemap-link:hover::after, .c-foot-sitemap-link:focus-visible::after,
.c-foot-social-link:hover::after, .c-foot-social-link:focus-visible::after {
  transform: scaleX(1); }

/* calm scroll reveal: opacity + small translateY (no scale pop, no rotation). The hidden
   initial state is GATED on `.cs-motion-ready` (added by the page's tiny IntersectionObserver
   script) so content is fully visible if JS/IO is unavailable; `.is-in` reveals it.
   The translateY shift is the brand's OPTIONAL scrollReveal token: absent, the 0px
   fallback makes the reveal fade-only (device disabled, never a foreign shift). The
   stagger step derives from the brand's own fast duration (0.1875 × fast — e.g. an
   authored 320ms fast → a 60ms step), so reveal tempo scales with brand tempo. */
.cs-motion-ready .cs-reveal {
  opacity: 0; transform: translateY(var(--c-reveal-shift, 0px));
  transition: opacity var(--c-motion-slow) var(--c-ease),
              transform var(--c-motion-slow) var(--c-ease);
  transition-delay: calc(var(--cs-reveal-i, 0) * var(--c-motion-fast) * 0.1875);
  will-change: opacity, transform; }
.cs-motion-ready .cs-reveal.is-in { opacity: 1; transform: none; }

/* respect prefers-reduced-motion: reduce — neutralize all transitions/reveals + the arrow
   nudge, and force revealed content fully visible. */
@media (prefers-reduced-motion: reduce) {
  .c-arrow,
  .c-arrow-link::after, .c-foot-sitemap-link::after, .c-foot-social-link::after,
  .cs-motion-ready .cs-reveal { transition: none !important; animation: none !important; }
  .c-arrow-link:hover .c-arrow { transform: none !important; }
  .cs-reveal, .cs-motion-ready .cs-reveal { opacity: 1 !important; transform: none !important; }
}
"""


# ── structural-variant CSS (SPEC §C.3) — emitted PER BRAND FLAG, never dormant ────
# A brand that never uses a variant carries NO rule for it: the neverDo static checks
# judge the RULE TEXT deliberately (dormant grammar is how DNA leaks, AS-22/AS-24), so
# a no-buttons/no-boxed-inputs brand's page must not ship .c-button/.c-field--boxed CSS.

# button primitive: FILLED action for brands that require it. Fully token-driven (CR-2):
# shape/weight/tracking/padding come from the brand's MEASURED buttons.primary.* via the
# --c-button-* aliases (component_vars emits them only when the brand carries a button
# family). The control tier is the var-chained fallback SHAPE for harness specimens.
_BUTTON_VARIANT_CSS = """
.c-button { display: inline-flex; align-items: center; justify-content: center;
  background: var(--c-button-bg, var(--c-accent));
  color: var(--c-button-fg, var(--c-button-ink, var(--c-paper)));
  font-family: var(--c-button-font, var(--c-font-body));
  font-size: var(--c-button-size, var(--c-control-size));
  font-weight: var(--c-button-weight, var(--c-heading-weight));
  letter-spacing: var(--c-button-ls, var(--c-control-ls));
  text-decoration: none;
  /* measured control height (sysfix 2026-07): brands measuring an explicit pill
     height get it verbatim; the inline-flex centering keeps the label vertical-
     centered when the measured padding is horizontal-only (e.g. "0 1.5rem"). */
  height: var(--c-button-height, auto);
  padding: var(--c-button-pad, 0.8em 1.6em); /* provenance: structural — em-relative
     control inset fallback (shape, not magnitude: scales with the button's own size) */
  border-radius: var(--c-button-radius, var(--radius)); border: none;
  transition: background var(--c-motion-fast) var(--c-ease),
              color var(--c-motion-fast) var(--c-ease),
              transform var(--c-motion-fast) var(--c-ease); }
/* hover = the brand's MEASURED bg swap (--c-button-bg-hover) + measured label swap
   (--c-button-fg-hover, e.g. an outline family filling on hover); the old universal
   brightness-filter was a motion-language assumption (one brand's hover mechanic). */
.c-button:hover, .c-button:focus-visible {
  background: var(--c-button-bg-hover, var(--c-button-bg, var(--c-accent)));
  color: var(--c-button-fg-hover, var(--c-button-fg, var(--c-button-ink, var(--c-paper))));
  transform: translateY(-1px); }
"""

# CARD variant (structural flag: the brand DECLARES a usable `blocks.card` device) —
# a bounded content unit on the brand's PANEL surface role, radius from the brand's
# own card/global radius tokens, optional INSET media well on the brand's inverse
# surface (blocks.card.slots.media). Every magnitude is a brand token reference;
# layout mechanics (column stack, media-well geometry) are structural. Brands without
# a card device (or with `use: never`) ship NONE of this rule text (AS-22/AS-24).
_CARD_VARIANT_CSS = """
.c-card { display: flex; flex-direction: column; align-items: stretch; overflow: hidden;
  background: var(--c-card-bg, var(--surface-panel, var(--c-paper)));
  border-radius: var(--c-card-radius, var(--radius-card, var(--radius, 0))); }
/* inset media well (blocks.card.slots.media): an INVERSE-surface inset frame; art is
   contained, never cover-cropped (product shots/marks keep their geometry). */
.c-card-media { display: flex; align-items: center; justify-content: center;
  background: var(--c-card-media-bg, var(--surface-inverse, var(--c-ink)));
  border-radius: var(--c-card-media-radius, var(--radius-media, 0)); overflow: hidden; }
.c-card-media .c-image, .c-card-media .c-image-ph { width: 100%; height: 100%;
  border-radius: 0; object-fit: contain; }
.c-card-body { display: flex; flex-direction: column; align-items: flex-start;
  gap: 0.75rem; padding: var(--c-card-pad, var(--panel-pad, 1.75rem)); }
.c-card-body .c-heading { max-width: none; }
.c-card-body .c-paragraph { max-width: none; }
"""

# CONTENT-BLOCK variant (structural flag: a usable `blocks.content-block` device) —
# the brand's eyebrow → heading → body → actions stack. Rhythm rides the shared
# --c-* aliases; the action row is the same non-stretch flex-row discipline as the
# hero/conversion action clusters (AGENTS.md flex-column mechanic).
_CONTENT_BLOCK_VARIANT_CSS = """
.c-content-block { display: flex; flex-direction: column; align-items: flex-start;
  gap: var(--c-eyebrow-gap, 1.5rem); }
.c-content-block .c-actions { display: flex; flex-wrap: wrap; align-items: center;
  gap: 0.75rem 1rem; margin-top: 0.5rem; }
"""

# BOXED input variant (structural flag `input-shape: boxed`) — for brands whose forms
# are contained fields, not typographic underlines. Kind is the flag; radius/border/
# fill magnitudes are the brand's own tokens. 1px border THICKNESS is structural.
_BOXED_FIELD_VARIANT_CSS = """
.c-field--boxed { align-items: center;
  padding: 0.6em 0.9em; /* provenance: structural — em-relative field inset (shape,
     not magnitude: scales with the field's own type size) */
  border: 1px solid var(--c-input-border, var(--c-hairline));
  border-radius: var(--c-input-radius, var(--radius));
  background: var(--c-input-bg, transparent); }
.c-field--boxed::after { display: none; }
"""

# footer sitemap GRAMMARS (fix-batch 2026-07, B6): the bookend batch's oversized didone
# slash-sitemap was ALWAYS-ON component CSS, so its display register leaked into brands
# whose footer is a measured multi-column directory. Each grammar is now a structural
# variant emitted per brand flag (footer_grammar), same discipline as button/boxed-field.
_FOOT_DISPLAY_LINKS_CSS = """
/* display-links footer grammar: CENTERED oversized didone slash sitemap — for brands
   whose type scale carries a footer display tier. The link is a CONTAINED oversized
   clamp: clearly larger than body editorial display, right-sized for a footer. */
.c-foot-sitemap { display: flex; flex-wrap: wrap; align-items: baseline; justify-content: center;
  gap: 0.4rem 1.5rem; max-width: 60rem; margin: 0 auto; }
.c-foot-sitemap-link { font-family: var(--c-font-heading);
  text-transform: var(--c-foot-link-case, var(--c-case-heading));
  font-weight: var(--c-foot-link-weight, var(--c-heading-weight, var(--c-display-weight)));
  /* provenance: structural — this device's contained floor/ceiling (the sanctioned
     footer scale from the bookend batch), a register bound rather than a brand
     magnitude; the brand's own footer tier feeds --c-foot-link-size when resolved. */
  font-size: var(--c-foot-link-size, clamp(1.75rem, 3.5cqw, 3rem));
  line-height: 1.2em; color: var(--c-ink); text-decoration: none; }
"""

_FOOT_COLUMNS_CSS = """
/* columns footer grammar: a measured multi-column link directory — for brands whose
   extracted footer is a dense sitemap of small links, not a display device. Register
   (size/weight) rides the brand's measured chrome tokens via --c-foot-link-size;
   layout mechanics (wrap/gaps/measure) are structural. */
/* GRID sitemap (2026-07): flex-wrap staggered the columns into ragged rows
   (5+1) with misaligned left edges. A grid keeps every column on a shared track
   so wrapped rows stay column-aligned, like the real directory footer. */
.c-foot-cols { display: grid; justify-content: center; text-align: left;
  grid-template-columns: repeat(auto-fit, minmax(9rem, 1fr));
  gap: var(--c-block-gap, 2.5rem) clamp(2rem, 5cqw, 4rem); max-width: 72rem; margin: 0 auto; }
.c-foot-col { display: flex; flex-direction: column;
  gap: var(--cf-link-gap, 0.6em); min-width: 0; }
.c-foot-col-link { font-family: var(--c-font-body);
  font-size: var(--c-foot-link-size, var(--c-control-size));
  font-weight: var(--c-foot-link-weight, var(--c-body-weight));
  color: var(--c-ink-muted); text-decoration: none; line-height: 1.6em; }
.c-foot-col-link:hover, .c-foot-col-link:focus-visible { color: var(--c-link-hover); }
/* measured directory HIERARCHY (fid4 2026-07): group headings in the brand's
   extracted register (--cf-head-* vars, muted defaults); a .c-foot-cell is one MAJOR
   column stacking its captured groups (footer.measured.grid.wrapperSizes). */
.c-foot-col-head { font-family: var(--c-font-body);
  font-size: var(--cf-head-size, var(--c-foot-link-size, var(--c-control-size)));
  font-weight: var(--cf-head-weight, 500); color: var(--cf-head-ink, var(--c-ink-muted));
  text-transform: var(--cf-head-case, none); letter-spacing: var(--cf-head-ls, normal);
  margin-bottom: 0.25em; }
/* continuation column: an invisible heading-row spacer so its first link aligns
   with the headed columns' first links (shared link-start baseline). */
.c-foot-col-head--spacer { visibility: hidden; }
.c-foot-cell { display: flex; flex-direction: column;
  gap: var(--cf-cell-gap, 2rem);
  flex: 1 1 9rem; min-width: 9rem; max-width: 16rem; }
.c-foot-cell .c-foot-col { flex: 0 0 auto; min-width: 0; max-width: none; }
/* measured directory geometry (inline --cf-col-gap/--cf-cols-max when extracted)
   so the captured track count fits at full width exactly as the source. */
.c-foot-cols { column-gap: var(--cf-col-gap, clamp(2rem, 5cqw, 4rem));
  max-width: var(--cf-cols-max, 72rem); }
/* BOTTOM BAR (fid2 2026-07): legal line + policy links + social cluster on one row,
   per the measured bottom-bar grammar. Social stays TEXT links (no invented glyphs). */
.c-foot-bar { display: flex; flex-wrap: wrap; align-items: center; justify-content: center;
  gap: 0.75rem 1.5rem; max-width: 72rem; margin: 0 auto; }
.c-foot-bar .c-foot-legal { margin: 0; flex: 1 1 24rem; text-align: left; }
.c-foot-policy { display: inline-flex; flex-wrap: wrap; gap: 0.4rem 1.1rem; }
.c-foot-policy-link { font-family: var(--c-font-body);
  font-size: calc(var(--c-foot-link-size, var(--c-control-size)) * 0.9);
  color: var(--c-ink-muted); text-decoration: none; }
.c-foot-policy-link:hover, .c-foot-policy-link:focus-visible { color: var(--c-link-hover); }
.c-foot-bar .c-foot-social { display: inline-flex; gap: 0.75rem; }
/* MEASURED bottom-bar structure (fid4 2026-07, footer.bottomBar): copyright +
   small-print disclaimer left with the store-badge column right; the extracted
   divider; policy links centered beside the social cluster. */
.c-foot-bb { max-width: var(--cf-cols-max, 72rem); margin: 0 auto; display: flex;
  flex-direction: column; gap: var(--cf-bb-gap, 1.25rem); text-align: left;
  /* measured directory→bar breathing room (gapAbove) MINUS the container gap the
     footer already contributes — never negative, silent brands add nothing */
  margin-top: max(0px, calc(var(--cf-bb-above, 0px) - var(--c-block-gap, 2.5rem))); }
.c-foot-bb-row1 { display: flex; align-items: flex-end; gap: 1.5rem; }
.c-foot-bb-left { flex: 1 1 auto; min-width: 0; display: flex; flex-direction: column;
  gap: 0.5rem; }
.c-foot-bb .c-foot-legal { margin: 0; text-align: left; }
.c-foot-disclaimer { margin: 0; font-family: var(--c-font-body);
  font-size: calc(var(--c-foot-link-size, var(--c-control-size)) * 0.86);
  color: var(--c-ink-muted); line-height: 1.5; max-width: 64rem; }
.c-foot-badges { display: flex; flex-direction: column; gap: 0.5rem;
  align-items: flex-end; flex: 0 0 auto; }
.c-foot-badges img { display: block; height: 40px; width: auto; }
.c-foot-divider { border: 0; height: 1px; margin: 0; width: 100%;
  background: var(--c-hairline, currentColor); }
.c-foot-bb-row2 { display: flex; align-items: center; gap: 2rem; }
.c-foot-bb-row2 .c-foot-policy { margin: 0 auto; }
.c-foot-glyphs { display: inline-flex; align-items: center; gap: 1.25rem; flex: 0 0 auto; }
.c-foot-glyph { display: inline-flex; align-items: center; justify-content: center;
  text-decoration: none; }
.c-foot-glyph > span { display: block; }
/* fix4 inline channel: the sanitized <svg> paints its own currentColor shapes;
   the measured icon ink rides the same --cfg-ink var the mask consumed. */
.c-foot-glyph-svg { color: var(--cfg-ink, currentColor); }
.c-foot-glyph-svg > svg { display: block; width: 100%; height: 100%; }
/* mask DEGRADE (fix2 channel) for artwork that failed single-ink verification */
.c-foot-glyph-mask { background: var(--cfg-ink, currentColor);
  -webkit-mask: var(--cfg-mask) center / contain no-repeat;
  mask: var(--cfg-mask) center / contain no-repeat; }
/* CENTERED-STACK bottom bar (fix1 2026-07, footer.bottomBar.anatomy=centered-stack):
   social glyph row flanked by same-row hairline rules, then the wordmark, the legal
   line, and the policy row — all centered. --cf-rule = the measured divider color. */
.c-foot-cstack { max-width: var(--cf-cols-max, 72rem); margin: 0 auto; display: flex;
  flex-direction: column; align-items: center; gap: var(--cf-bb-gap, 1.5rem);
  text-align: center;
  /* the footer root is a centering column — the stack must span the directory
     measure or the flanking hairlines collapse to slivers */
  align-self: stretch; width: 100%;
  margin-top: max(0px, calc(var(--cf-bb-above, 0px) - var(--c-block-gap, 2.5rem))); }
.c-foot-cstack-social { display: flex; align-items: center; gap: 2.5rem;
  align-self: stretch; }
.c-foot-cstack-social::before, .c-foot-cstack-social::after { content: "";
  flex: 1 1 auto; height: 1px; background: var(--cf-rule, var(--c-hairline)); }
.c-foot-wordmark { display: block; height: 28px; width: auto; }
/* wordmark recolor: the brand's own logo art masked over the footer ink (the
   captured bottom stack draws the same mark in the light ink, not its own fill) */
span.c-foot-wordmark { background: currentColor;
  -webkit-mask: var(--cfw-mask) center / contain no-repeat;
  mask: var(--cfw-mask) center / contain no-repeat; }
.c-foot-cstack .c-foot-legal { margin: 0; text-align: center; }
.c-foot-cstack .c-foot-policy { justify-content: center; gap: 0.4rem 0; }
.c-foot-cstack .c-foot-policy-link { text-decoration: underline;
  text-underline-offset: 3px; padding: 0 1.1rem; }
.c-foot-cstack .c-foot-policy-link + .c-foot-policy-link {
  border-left: 1px solid var(--cf-rule, var(--c-hairline)); }
"""


# ── chrome PRESENTATION devices (nav-fix 2026-07) ────────────────────────────────
# Casing, separators, and chrome surfaces are BRAND EVIDENCE, never shared-code
# defaults (AS-38 class): the bootstrap brand's slash-separated tracked-caps dark
# nav was baked in here and leaked into every brand's chrome. Each device now reads
# a brand.yaml declaration and degrades to a NEUTRAL default (no separator glyph,
# no case transform, chrome surface from the brand's own roles).


def nav_separator(doc) -> str:
    """The brand's declared decorative inter-link nav separator glyph
    (``navbar.separator``). '' when the brand declares none — links are separated by
    spacing alone, never by an inherited glyph."""
    sep = ((doc or {}).get("navbar") or {}).get("separator")
    return str(sep).strip() if isinstance(sep, str) and sep.strip() else ""


def footer_separator(doc) -> str:
    """The brand's declared footer sitemap/social separator glyph
    (``footer.separator``). Same degrade-to-none rule as nav_separator."""
    sep = ((doc or {}).get("footer") or {}).get("separator")
    return str(sep).strip() if isinstance(sep, str) and sep.strip() else ""


def eyebrow_prefix(doc) -> str:
    """The eyebrow register's decorative text prefix (``tokens.type.eyebrow.prefix``,
    e.g. a slash device). Consumed by SPECIMEN/preview surfaces; composed section copy
    authors its own prefixes. '' when undeclared."""
    pre = (type_role(doc, "eyebrow") or {}).get("prefix")
    return str(pre) if isinstance(pre, str) and pre.strip() else ""


# The chrome-nav surface when nothing is measurable AND the caller supplies no
# context: the brand's base canvas (a bar of the page's own paper) — never an
# inverse band by default.
NAV_SURFACE_DEFAULT = "surface/primary"


def _parse_color_rgba(v):
    """(r, g, b, a) from '#rgb'/'#rrggbb'/'rgb()'/'rgba()' strings; None otherwise."""
    if not isinstance(v, str):
        return None
    s = v.strip().lower()
    if s.startswith("rgb"):
        try:
            parts = [float(x) for x in s[s.index("(") + 1:s.index(")")].split(",")]
        except (ValueError, IndexError):
            return None
        if len(parts) == 3:
            return (int(parts[0]), int(parts[1]), int(parts[2]), 1.0)
        if len(parts) == 4:
            return (int(parts[0]), int(parts[1]), int(parts[2]), parts[3])
        return None
    if s.startswith("#"):
        h = s[1:]
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        if len(h) >= 6:
            try:
                return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) + (1.0,)
            except ValueError:
                return None
    return None


def nav_surface_role(doc) -> str | None:
    """Chrome-NAV surface as a role resolution (same discipline as
    footer_surface_role / AS-35): match the brand's MEASURED nav bar color
    (``navbar.surface.bg``) against the brand's own ``tokens.surfaces`` roles by
    nearest RGB distance and return that ROLE NAME.

    Returns None when the measured bar is TRANSPARENT or absent — the extracted nav
    sits over whatever it overlaps, so the caller keeps its contextual surface (the
    composed page uses the opening section's surface, exactly the pre-fix behavior)."""
    surfaces = ((doc.get("tokens") or {}).get("surfaces") or {})
    rgba = _parse_color_rgba(((doc.get("navbar") or {}).get("surface") or {}).get("bg"))
    if rgba is None or rgba[3] < 0.5 or not surfaces:
        return None
    target = rgba[:3]
    best_role, best_d = None, None
    for role, spec in surfaces.items():
        rgb = _parse_color_rgba((spec or {}).get("bg"))
        if rgb is None:
            continue
        d = sum((a - b) ** 2 for a, b in zip(rgb[:3], target))
        if best_d is None or d < best_d:
            best_role, best_d = role, d
    return best_role


def nav_hover_css(doc) -> str:
    """Nav-link hover WASH (pill/underlay) — emitted ONLY when the brand's extraction
    measured one (``navbar.measured.link.hoverBg``, optional ``hoverRadius``); every
    other brand renders byte-identical. The wash is padding+negative-margin so the
    resting nav geometry is unchanged; color/radius ride the layer-1 chrome tokens
    (tokens_css emits --chrome-nav-link-hover-*), never a literal here."""
    link = (((doc or {}).get("navbar") or {}).get("measured") or {}).get("link") or {}
    if not (isinstance(link.get("hoverBg"), str) and link["hoverBg"].strip()):
        return ""
    # border-radius rides the layer-1 token and is emitted ONLY when the brand measured
    # a hoverRadius — no literal fallback (AS-24 token-provenance: a `999px` guess has
    # no provenance in any brand's manifest).
    radius = ("  border-radius: var(--chrome-nav-link-hover-radius);\n"
              if link.get("hoverRadius") not in (None, "") else "")
    return f"""
/* nav-link hover wash (measured chrome interaction — navbar.measured.link.hoverBg). */
.cs-navlinks .c-arrow-link {{ padding: 0.35em 0.8em; margin: -0.35em -0.8em;
{radius}  transition: background-color var(--c-motion-fast) var(--c-ease); }}
.cs-navlinks .c-arrow-link:hover, .cs-navlinks .c-arrow-link:focus-visible {{
  background: var(--chrome-nav-link-hover-bg); }}
"""


# ── chrome MEGA-MENU panels (fid4 2026-07) ──────────────────────────────────────
# The composed page-level nav renders the brand's CAPTURED mega-menu structure
# (column groups + per-link icon/description anatomy + the right-side promo card)
# with the MEASURED open/close motion. Everything below is evidence-gated: brands
# whose navbar.primary carries no `menu` emit no markup and no CSS (byte-identical
# pages); descriptions/icons/cards render only when captured.

def _nav_menus(doc) -> list[dict]:
    """The primary links that own a captured mega-menu."""
    nav = (doc or {}).get("navbar") or {}
    out = []
    for p in nav.get("primary") or []:
        menu = p.get("menu") if isinstance(p, dict) else None
        if isinstance(menu, dict) and (menu.get("columns") or menu.get("card")):
            out.append(p)
    return out


_DATA_URI_MIMES = {".svg": "image/svg+xml", ".png": "image/png", ".webp": "image/webp",
                   ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif"}


def _svg_with_namespace(data: bytes) -> bytes:
    """Inline-DOM svg markup (outerHTML harvests) legally omits xmlns inside HTML,
    but a STANDALONE payload (data: URI, mask/img resource) is XML — without the
    namespace the parser rejects it and the glyph silently paints nothing. Inject
    the missing declaration(s); artwork bytes are otherwise untouched."""
    i = data.find(b"<svg")
    j = data.find(b">", i) if i != -1 else -1
    if i == -1 or j == -1:
        return data
    if b"xmlns=" not in data[i:j]:
        data = data[:i + 4] + b' xmlns="http://www.w3.org/2000/svg"' + data[i + 4:]
    if b"xlink:" in data and b"xmlns:xlink=" not in data:
        i = data.find(b"<svg")
        data = (data[:i + 4] + b' xmlns:xlink="http://www.w3.org/1999/xlink"'
                + data[i + 4:])
    return data


def _asset_data_uri(brand_dir, asset, *, svg_only: bool = False) -> str | None:
    """data: URI for a brand asset path (best-effort; unreadable/unknown ⇒ None).
    ``svg_only`` restricts to SVG payloads (CSS mask glyphs need vector artwork)."""
    import base64

    p = Path(brand_dir) / str(asset)
    mime = _DATA_URI_MIMES.get(p.suffix.lower())
    if mime is None:
        return None
    try:
        data = p.read_bytes()
    except OSError:
        return None
    if mime == "image/svg+xml":
        if b"<svg" not in data[:300]:
            return None
        data = _svg_with_namespace(data)
    if svg_only and mime != "image/svg+xml":
        return None
    return f"data:{mime};base64," + base64.b64encode(data).decode("ascii")


# ── inline-SVG glyph channel (fix4 2026-07) ──────────────────────────────────────
# The SINGLE-COLOR glyph channel renders sanitized INLINE <svg> markup (technique
# parity with source sites, styleable icons for kit consumers) instead of the fix2
# data-URI currentColor masks. The mask stays as the DEGRADE channel for artwork
# that cannot be verified single-ink (multi-color / <style>-driven / gradient /
# raster payloads) — never silently recolored.

_SVG_INK_NEUTRAL = {"", "none", "transparent", "currentcolor", "inherit",
                    "context-fill", "context-stroke"}
# markers whose presence makes single-ink verification (or safe inlining) impossible
_SVG_UNVERIFIABLE = ("<style", "<lineargradient", "<radialgradient", "<pattern",
                     "<image", "<filter", "<animate", "<set ", "<set>")
_SVG_GID_TOKEN = "__GID__"
_svg_gid_counter = itertools.count(1)


def _svg_ink_value(raw: str) -> str | None:
    """Normalize one fill/stroke value: None for ink-neutral values, the lowered
    concrete color otherwise. `var(--x, fallback)` resolves to its fallback;
    a var() WITHOUT a fallback is unverifiable (returned as-is to poison the set)."""
    v = re.sub(r"\s+", "", str(raw or "")).lower()
    if v in _SVG_INK_NEUTRAL:
        return None
    m = re.fullmatch(r"var\([\w-]+,(.+)\)", v)
    if m:
        v = m.group(1)
    return v


def sanitize_inline_svg(text: str) -> str | None:
    """Sanitize harvested SVG artwork for INLINE emission (fix4). Returns the
    cleaned markup, or None when the payload cannot be safely inlined as a
    single-ink glyph (caller keeps the mask/image channel):

    - strips <script>/<foreignObject>, on* event attributes, comments, and
      EXTERNAL references (href/url() that do not target an internal #id);
    - refuses payloads whose ink cannot be verified (<style>, gradients,
      patterns, rasters, filters, animation elements, var() without fallback);
    - verifies the artwork is genuinely SINGLE-INK (≤1 distinct concrete
      fill/stroke color) and only then normalizes those paints to currentColor
      — multi-color artwork returns None, never a silent recolor;
    - root hygiene: xmlns guaranteed, viewBox required (synthesized from
      numeric width/height when absent), width/height/class/style/
      preserveAspectRatio/overflow dropped (CSS owns the box; default
      xMidYMid meet ≙ the mask channel's `center / contain`),
      `aria-hidden="true" focusable="false"` stamped;
    - internal ids: unreferenced ids are DROPPED; referenced ids are rewritten
      to a __GID__ token that `_svg_instance` uniquifies per emission, so the
      same glyph inlined N times (nav chevrons) cannot collide."""
    if not text or "<svg" not in text:
        return None
    s = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    s = re.sub(r"<\?xml[^>]*\?>\s*|<!DOCTYPE[^>]*>\s*", "", s)
    s = re.sub(r"<(script|foreignObject)[\s\S]*?</\1\s*>", "", s, flags=re.I)
    s = re.sub(r"<(?:script|foreignObject)[^>]*/>", "", s, flags=re.I)
    low = s.lower()
    if "<script" in low or "<foreignobject" in low:
        return None
    if any(t in low for t in _SVG_UNVERIFIABLE):
        return None
    # external references: any href/url() not targeting an internal #id
    s = re.sub(r"\s(?:xlink:)?href=\"(?!#)[^\"]*\"", "", s)
    if re.search(r"url\(\s*['\"]?(?!['\"]?#)", s):
        return None
    s = re.sub(r"\son[a-z]+=\"[^\"]*\"", "", s, flags=re.I)

    # ── single-ink verification (attributes + inline style declarations) ──
    inks = set()
    unverifiable = False
    for m in re.finditer(r"\b(?:fill|stroke)=\"([^\"]*)\"", s):
        v = _svg_ink_value(m.group(1))
        if v is not None:
            inks.add(v)
            if v.startswith("var("):
                unverifiable = True
    for m in re.finditer(r"\bstyle=\"([^\"]*)\"", s):
        for d in re.finditer(r"(?:^|;)\s*(fill|stroke)\s*:\s*([^;]+)", m.group(1)):
            v = _svg_ink_value(d.group(2))
            if v is not None:
                inks.add(v)
                if v.startswith("var("):
                    unverifiable = True
    if unverifiable or len(inks) > 1:
        return None

    # ── root tag hygiene ──
    i = s.find("<svg")
    j = s.find(">", i)
    if i == -1 or j == -1:
        return None
    root = s[i:j + (0 if s[j - 1] == "/" else 0)]
    root_tag = s[i:j]
    dims = {}
    for m in re.finditer(r"\b(width|height)=\"([\d.]+)(?:px)?\"", root_tag):
        dims[m.group(1)] = m.group(2)
    has_viewbox = re.search(r"\bviewBox=\"[^\"]+\"", root_tag) is not None
    root_tag = re.sub(
        r"\s(?:width|height|class|style|preserveAspectRatio|overflow|version"
        r"|baseProfile|xml:space|x|y|id|role|focusable|aria-[\w-]+)=\"[^\"]*\"",
        "", root_tag)
    if not has_viewbox:
        if not (dims.get("width") and dims.get("height")):
            return None
        root_tag += f' viewBox="0 0 {dims["width"]} {dims["height"]}"'
    root_tag += ' aria-hidden="true" focusable="false"'
    s = root_tag + s[j:]
    del root
    if "xmlns=" not in s[:s.find(">")]:
        s = s[:4] + ' xmlns="http://www.w3.org/2000/svg"' + s[4:]

    # ── inner presentation hygiene: foreign class names are dead references ──
    body_at = s.find(">") + 1
    s = s[:body_at] + re.sub(r"\sclass=\"[^\"]*\"", "", s[body_at:])

    # ── id discipline: drop unreferenced ids; tokenize referenced ones ──
    for gid in set(re.findall(r"\bid=\"([^\"]+)\"", s)):
        esc_gid = re.escape(gid)
        if re.search(rf"(?:url\(\s*['\"]?#{esc_gid}['\"]?\s*\)|href=\"#{esc_gid}\")", s):
            s = re.sub(rf"\bid=\"{esc_gid}\"", f'id="{_SVG_GID_TOKEN}{gid}"', s)
            s = re.sub(rf"url\(\s*(['\"]?)#{esc_gid}\1\s*\)",
                       f"url(#{_SVG_GID_TOKEN}{gid})", s)
            s = s.replace(f'href="#{gid}"', f'href="#{_SVG_GID_TOKEN}{gid}"')
        else:
            s = re.sub(rf"\s?\bid=\"{esc_gid}\"", "", s)

    # ── normalize the verified single ink to currentColor ──
    def _norm_attr(m):
        return (m.group(0) if _svg_ink_value(m.group(2)) is None
                else f'{m.group(1)}="currentColor"')
    s = re.sub(r"\b(fill|stroke)=\"([^\"]*)\"", _norm_attr, s)

    def _norm_style(m):
        decls = re.sub(
            r"(^|;)(\s*)(fill|stroke)(\s*:\s*)([^;]+)",
            lambda d: (d.group(0) if _svg_ink_value(d.group(5)) is None
                       else f"{d.group(1)}{d.group(2)}{d.group(3)}{d.group(4)}currentColor"),
            m.group(1))
        return f'style="{decls}"'
    s = re.sub(r"\bstyle=\"([^\"]*)\"", _norm_style, s)
    # a default-black glyph (no paint attr anywhere) painted opaque through the
    # mask; inline parity needs the explicit currentColor inheritance root.
    if not inks and not re.search(r"\b(?:fill|stroke)=", s):
        s = s[:s.find(">")] + ' fill="currentColor"' + s[s.find(">"):]
    return s.strip()


def _svg_instance(markup: str) -> str:
    """Per-emission instance of a sanitized glyph: uniquifies the __GID__ id
    namespace so the same artwork inlined N times on one page cannot collide.
    Token-less markup (the common case — unreferenced ids are dropped at
    sanitize time) passes through untouched."""
    if _SVG_GID_TOKEN in markup:
        return markup.replace(_SVG_GID_TOKEN, f"ig{next(_svg_gid_counter)}-")
    return markup


def prepare_chrome_glyphs(doc, brand_dir) -> int:
    """Resolve the chrome's HARVESTED icon-artwork assets into inline data: URIs on
    the IN-MEMORY doc: social glyphs (footer.social[].icon.asset -> icon['_dataUri'];
    CSS mask-image is a CORS fetch that file:// composed pages cannot satisfy), the
    bottom bar's store badges (footer.bottomBar.storeBadges[].img.asset ->
    img['_dataUri']; previews render from the brand dir without shipping an assets/
    tree, so path-relative img refs there would 404 — fid9), and the BAR AFFORDANCE
    glyphs (fid15): navbar.utility[] icons + chevrons, the dropdown-trigger family
    chevron (navbar.measured.trigger.chevron), and the utility banner's cta arrow /
    close glyph. Same discipline as prepare_nav_logo (brand.yaml is never written).
    Returns the number of assets resolved; missing files resolve to none (renderers
    degrade to accessible text / the raw asset path, never invented artwork).

    fix4: SVG glyph nodes ALSO stamp `_inlineSvg` — the sanitized single-ink
    markup (sanitize_inline_svg) that renderers now emit INLINE in place of the
    mask. Artwork that fails single-ink verification stamps only `_dataUri` and
    stays on the mask channel (the noted degrade, never a silent recolor)."""
    n = 0
    brand_dir = Path(brand_dir)

    def _resolve(node, *, svg_only: bool = True) -> int:
        if not (isinstance(node, dict) and node.get("asset")):
            return 0
        uri = _asset_data_uri(brand_dir, node["asset"], svg_only=svg_only)
        if uri:
            node["_dataUri"] = uri
            if svg_only:
                try:
                    raw = (brand_dir / str(node["asset"])).read_text(errors="replace")
                except OSError:
                    raw = ""
                inline = sanitize_inline_svg(raw)
                if inline:
                    node["_inlineSvg"] = inline
            return 1
        return 0

    foot = ((doc or {}).get("footer") or {})
    for s in foot.get("social") or []:
        n += _resolve(s.get("icon") if isinstance(s, dict) else None)
    bb = foot.get("bottomBar") if isinstance(foot.get("bottomBar"), dict) else {}
    for b in bb.get("storeBadges") or []:
        n += _resolve(b.get("img") if isinstance(b, dict) else None, svg_only=False)
    # FOOTER WORDMARK (fix1 2026-07 item-11): the centered-stack bottom anatomy
    # draws the brand's own logo asset recolored to the footer ink via CSS mask
    # (the captured footer wordmark is the same art in the light ink) — resolve
    # the artwork + its intrinsic aspect so the mask box can size itself.
    lg = foot.get("logo") if isinstance(foot.get("logo"), dict) else None
    if lg and lg.get("src"):
        src = str(lg["src"])
        rel = src if (brand_dir / src).exists() else f"assets/{src}"
        uri = _asset_data_uri(brand_dir, rel, svg_only=True)
        if uri:
            lg["_dataUri"] = uri
            n += 1
            try:
                svg_text = (brand_dir / rel).read_text(errors="replace")
                m = re.search(r'viewBox="[\d.\s-]*?([\d.]+)\s+([\d.]+)"', svg_text)
                if m and float(m.group(2)) > 0:
                    lg["_aspect"] = round(float(m.group(1)) / float(m.group(2)), 4)
            except OSError:
                pass
    # footer WORDMARK (fix1 2026-07 item-11): the extracted footer.logo artwork inlines
    # the same way (the centered-stack bottom bar renders it as an <img>); a bare
    # filename is also tried under assets/ (extraction wrote `src: <name>.svg`).
    logo = foot.get("logo") if isinstance(foot.get("logo"), dict) else None
    raw_logo = str((logo or {}).get("asset") or (logo or {}).get("src") or "")
    if logo is not None and raw_logo:
        for cand in ((raw_logo,) if "/" in raw_logo else (raw_logo, f"assets/{raw_logo}")):
            uri = _asset_data_uri(brand_dir, cand, svg_only=False)
            if uri:
                logo["_dataUri"] = uri
                n += 1
                break
    nav = ((doc or {}).get("navbar") or {})
    for u in nav.get("utility") or []:
        if not isinstance(u, dict):
            continue
        n += _resolve(u.get("icon"))
        n += _resolve(u.get("chevron"))
    m_trig = (nav.get("measured") or {}).get("trigger") \
        if isinstance(nav.get("measured"), dict) else None
    if isinstance(m_trig, dict):
        n += _resolve(m_trig.get("chevron"))
    ub = nav.get("utilityBanner") if isinstance(nav.get("utilityBanner"), dict) else {}
    if isinstance(ub.get("cta"), dict):
        n += _resolve(ub["cta"].get("arrow"))
    n += _resolve(ub.get("close") if isinstance(ub.get("close"), dict) else None)
    # text-CTA trailing glyph (fix2, brand-schema §10.2; fix4 inline channel): the
    # arrow-link's harvested SVG resolves through the same discipline as every
    # chrome glyph above — sanitized inline markup first, data-URI mask degrade.
    for spec in ((doc or {}).get("buttons") or {}).values():
        if isinstance(spec, dict) and isinstance(spec.get("glyph"), dict):
            g = spec["glyph"]
            if g.get("asset") and not g.get("_dataUri"):
                rel = f"assets/{Path(str(g['asset'])).name}"
                uri = _asset_data_uri(brand_dir, rel)
                if uri:
                    g["_dataUri"] = uri
                    n += 1
                    try:
                        raw = (brand_dir / rel).read_text(errors="replace")
                    except OSError:
                        raw = ""
                    inline = sanitize_inline_svg(raw)
                    if inline:
                        g["_inlineSvg"] = inline
    return n


def _mega_first(value, default: str) -> str:
    """First comma-separated CSS list item (transition shorthands measure per-property)."""
    s = str(value or "").strip()
    return (s.split(",")[0].strip() or default) if s else default


def nav_mega_css(doc) -> str:
    """Mega-panel CSS for the composed chrome nav — emitted ONLY when this brand's
    navbar carries captured mega-menus. Geometry/motion/typography are the brand's
    own MEASURED chrome facts (navbar.measured.megaPanel + megaOpen), inlined as
    scoped literals (chrome paint, same discipline as the utility banner)."""
    if not _nav_menus(doc):
        return ""
    nav = (doc or {}).get("navbar") or {}
    facts = (nav.get("measured") or {}).get("megaPanel") or {}
    motion = facts.get("motion") if isinstance(facts.get("motion"), dict) else {}
    panel_m = motion.get("panel") if isinstance(motion.get("panel"), dict) else {}
    dur = _mega_first(panel_m.get("duration"), "0.2s")
    ease = _mega_first(panel_m.get("easing"), "ease")
    desc_m = motion.get("description") if isinstance(motion.get("description"), dict) else {}
    desc_dur = _mega_first(desc_m.get("duration"), "0.25s")
    surface = facts.get("surface") if isinstance(facts.get("surface"), dict) else {}
    bg = str(surface.get("bg") or "").strip() or "var(--c-paper)"
    # RESPONSIVE fact override (fact-gated: responsive.nav.panelSurface): the measured
    # megaPanel.surface.bg often captures the transparent OUTER wrapper, not the painted
    # panel sheet (the computed-CSS harness flags this as a CRITICAL missing surface). A
    # derived panel-surface fact carries the REAL resolved container colour; prefer it
    # when the measured surface reads transparent. "" of the block ⇒ unchanged (v2/remote).
    _resp_nav = ((doc or {}).get("responsive") or {}).get("nav") \
        if isinstance(doc, dict) else None
    if isinstance(_resp_nav, dict):
        _panel_bg = str(((_resp_nav.get("panelSurface") or {}).get("background")
                         or "")).strip()
        _bg_norm = re.sub(r"\s+", "", bg).lower()
        if _panel_bg and _bg_norm in ("rgba(0,0,0,0)", "transparent", "none", ""):
            bg = _panel_bg
    border_top = str(surface.get("borderTop") or "").strip()
    border_css = (f"border-top: 1px solid {border_top.split(' ', 1)[1]};"
                  if " " in border_top else "border-top: 1px solid var(--c-hairline);")
    hidden = facts.get("hiddenState") if isinstance(facts.get("hiddenState"), dict) else {}
    shift = 8
    m = re.search(r"matrix\([^)]*,\s*(-?\d+(?:\.\d+)?)\)\s*$", str(hidden.get("transform") or ""))
    if m:
        try:
            shift = max(0, int(round(float(m.group(1)))))
        except ValueError:
            pass
    link = facts.get("link") if isinstance(facts.get("link"), dict) else {}
    link_pad = str(link.get("padding") or "0.5em")
    link_radius = link.get("radius") if isinstance(link.get("radius"), (int, float)) else 4
    hover_bg = str(link.get("hoverBg") or "").strip() or "rgba(0,0,0,0.04)"
    gt = facts.get("groupTitle") if isinstance(facts.get("groupTitle"), dict) else {}
    gt_size = gt.get("fontSize") if isinstance(gt.get("fontSize"), (int, float)) else 13
    gt_color = str(gt.get("color") or "").strip() or "var(--c-ink-muted)"
    gt_tt = str(gt.get("textTransform") or "none")
    gt_ls = str(gt.get("letterSpacing") or "normal")
    gt_fw = str(gt.get("fontWeight") or "500")
    aside = facts.get("aside") if isinstance(facts.get("aside"), dict) else {}
    aside_border = str(aside.get("borderLeft") or "").strip()
    aside_border_css = (f"border-left: 1px solid {aside_border.split(' ', 1)[1]};"
                        if " " in aside_border else "border-left: 1px solid var(--c-hairline);")
    # aside width fraction from the OPEN-state measurement (mean of tabs that carry one)
    fracs = [float((mo.get("aside") or {}).get("widthFraction") or 0)
             for mo in (nav.get("megaOpen") or []) if isinstance(mo, dict)]
    fracs = [f for f in fracs if 0.1 <= f <= 0.6]
    aside_pct = round(sum(fracs) / len(fracs) * 100, 1) if fracs else 24.0
    # per-group link columns from the same measurement (mode)
    cols = [int(g.get("linkColumns") or 0)
            for mo in (nav.get("megaOpen") or []) if isinstance(mo, dict)
            for g in (mo.get("groups") or []) if not g.get("aside")]
    cols = [c for c in cols if c > 0]
    link_cols = max(set(cols), key=cols.count) if cols else 2
    return f"""
/* chrome mega-menu panels (measured: navbar.measured.megaPanel + navbar.megaOpen).
   Full-bleed band under the sticky bar; opacity/translate open motion; menu-card
   link anatomy (icon + title + hover-revealed description); aside rail + promo card. */
#page-nav {{ position: relative; z-index: 40; }}
.cs-nav-tab {{ display: inline; }}
.cs-mega {{
  /* provenance: structural navbar.measured.megaPanel — measured chrome paint (panel
     edge + elevation), inlined like the utility banner; not composer-invented */
  position: absolute; left: 0; right: 0; top: 100%;
  background: {bg}; {border_css}
  border-bottom: 1px solid rgba(0,0,0,0.08);
  box-shadow: 0 18px 40px rgba(0,0,0,0.10);
  visibility: hidden; opacity: 0; transform: translateY({shift}px);
  transition: opacity {dur} {ease}, transform {dur} {ease}, visibility {dur} {ease};
  z-index: 30; text-align: left;
}}
.cs-nav-tab:hover .cs-mega, .cs-nav-tab:focus-within .cs-mega {{
  visibility: visible; opacity: 1; transform: none; }}
/* provenance: structural — disclosure-trigger parity (interaction remediation
   2026-07, IC-NAV-01/02/08). The menu-owning trigger is a real <button>; this
   neutralises the residual UA button chrome so it inherits the measured pill
   styles exactly (values identical to .c-arrow-link's own — safe at any
   specificity). Escape/click stamp .cs-nav-tab--closed, which outranks the
   :hover/:focus-within open rules until the pointer leaves. */
button.cs-nav-trigger {{ -webkit-appearance: none; appearance: none;
  background: none; border: 0; }}
.cs-nav-tab.cs-nav-tab--closed:hover .cs-mega,
.cs-nav-tab.cs-nav-tab--closed:focus-within .cs-mega {{
  visibility: hidden; opacity: 0; transform: translateY({shift}px); }}
.cs-mega-inner {{ max-width: 76rem; margin: 0 auto;
  padding: 2rem var(--c-section-pad-x, 2.5rem) 2.5rem;
  display: flex; gap: 2.5rem; align-items: stretch; }}
/* left CATEGORY RAIL (menu.sidebarTabs) — a vertical tab list beside the column
   groups; inert for brands whose menu carries no rail (no element emitted). */
.cs-mega-rail {{ flex: 0 0 15rem; max-width: 15rem;
  /* provenance: structural — mega-menu category-rail separator hairline (chrome
     device geometry, not a brand color role) */
  border-right: 1px solid rgba(0,0,0,0.08); padding-right: 1.25rem; }}
.cs-mega-rail ul {{ list-style: none; margin: 0; padding: 0;
  display: flex; flex-direction: column; gap: 0.25rem; }}
.cs-mega-rail-item {{ display: flex; align-items: center;
  justify-content: space-between; gap: 0.5rem;
  padding: 0.5rem 0.6rem; border-radius: 8px; font-family: var(--c-font-body);
  /* provenance: structural — mega-menu utility-list item size (nav chrome density,
     not a brand type tier) */
  font-size: 14px; font-weight: 500; color: {gt_color}; }}
/* provenance: structural — mega-menu active-item hover wash (chrome state tint) */
.cs-mega-rail-item--active {{ background: rgba(0,0,0,0.05); }}
.cs-mega-rail-chev {{ opacity: 0.5; }}
.cs-mega-main {{ flex: 1 1 auto; min-width: 0; display: flex;
  flex-direction: column; gap: 1.5rem; }}
.cs-mega-group ul {{ list-style: none; margin: 0; padding: 0;
  display: grid; grid-template-columns: repeat({link_cols}, minmax(0, 1fr));
  gap: 0.3rem 1.25rem; }}
.cs-mega-aside {{ flex: 0 0 {aside_pct}%; max-width: {aside_pct}%; {aside_border_css}
  padding-left: 1.25rem; display: flex; flex-direction: column; gap: 1.25rem; }}
.cs-mega-aside .cs-mega-group ul {{ display: flex; flex-direction: column; gap: 0.2rem; }}
.cs-mega-head {{ /* provenance: structural navbar.measured.megaPanel.groupTitle —
     measured chrome register (size/weight/tracking straight from capture) */
  display: block; margin: 0 0 0.6rem; font-family: var(--c-font-body);
  font-size: {gt_size}px; font-weight: {gt_fw}; color: {gt_color};
  text-transform: {gt_tt}; letter-spacing: {gt_ls}; }}
.cs-mega-link {{ /* provenance: structural navbar.measured.megaPanel.link —
     measured link-row geometry (inset/radius from capture) */
  display: flex; align-items: flex-start; gap: 10px;
  padding: {link_pad}; border-radius: {link_radius}px; text-decoration: none;
  transition: background-color var(--c-motion-fast, 0.15s) var(--c-ease, ease); }}
.cs-mega-link:hover, .cs-mega-link:focus-visible {{
  /* provenance: structural navbar.measured.megaPanel.link.hoverBg (measured wash) */
  background: {hover_bg}; }}
.cs-mega-link-icon {{ flex: 0 0 auto; display: inline-flex; margin-top: 1px; }}
.cs-mega-link-icon img {{ width: 20px; height: 20px; display: block; }}
.cs-mega-link-title {{ /* provenance: structural chrome control register (measured) */
  display: block; font-family: var(--c-font-body);
  font-size: var(--c-control-size); font-weight: 500; color: var(--c-ink);
  line-height: 1.35; }}
.cs-mega-link-desc {{ /* provenance: structural navbar.measured.megaPanel.motion.description
     — the hover-reveal duration is the capture's own measured value (falls back to the
     structural 0.25s only when the brand measured none), same discipline as the panel
     motion above; not a token because chrome motion is a measured chrome fact */
  display: grid; grid-template-rows: 1fr;
  transition: grid-template-rows {desc_dur} {ease}; }}
.cs-mega-link-desc > span {{ overflow: hidden; font-family: var(--c-font-body);
  font-size: calc(var(--c-control-size) * 0.875); color: var(--c-ink-muted);
  line-height: 1.4; }}
.cs-mega-link.cs-desc-hover .cs-mega-link-desc {{ grid-template-rows: 0fr; }}
.cs-mega-link.cs-desc-hover:hover .cs-mega-link-desc,
.cs-mega-link.cs-desc-hover:focus-visible .cs-mega-link-desc {{ grid-template-rows: 1fr; }}
.cs-mega-card {{ /* provenance: structural navbar.measured.megaPanel promo card —
     measured chrome paint (white promo plate, capture radius/elevation) */
  display: block; background: #fff; border-radius: 10px; overflow: hidden;
  box-shadow: 0 1px 2px rgba(0,0,0,0.06); text-decoration: none; }}
.cs-mega-card img {{ display: block; width: 100%; height: auto; }}
.cs-mega-card-title {{ /* provenance: structural chrome control register (measured) */
  margin: 0; padding: 12px 14px 4px; font-family: var(--c-font-body);
  font-size: var(--c-control-size); font-weight: 500; color: var(--c-ink);
  line-height: 1.35; }}
.cs-mega-card-body {{ margin: 0; padding: 0 14px; font-family: var(--c-font-body);
  font-size: calc(var(--c-control-size) * 0.875); color: var(--c-ink-muted); }}
.cs-mega-card-cta {{ /* provenance: structural chrome control register (measured) */
  display: block; padding: 8px 14px 14px; font-family: var(--c-font-body);
  font-size: calc(var(--c-control-size) * 0.875); font-weight: 500;
  color: var(--c-link-hover, var(--c-ink)); }}
@media (prefers-reduced-motion: reduce) {{
  .cs-mega, .cs-mega-link, .cs-mega-link-desc {{ transition: none !important; }}
}}
"""


def _mega_panel_fragment(menu: dict, panel_id: str = "") -> str:
    """The composed nav's mega-panel HTML for one primary tab (captured columns →
    main groups + aside rail + promo card). Icons/descriptions render only when
    captured; icon artwork binds by asset ref (composed pages ship assets/).
    ``panel_id`` (interaction remediation 2026-07) is the disclosure target id the
    trigger's aria-controls points at — "" keeps the id off (gallery demos)."""
    def link_html(l: dict) -> str:
        icon = l.get("icon") if isinstance(l.get("icon"), dict) else {}
        icon_html = ""
        if icon.get("asset"):
            icon_html = (f'<span class="cs-mega-link-icon"><img src="{esc(str(icon["asset"]))}" '
                         f'alt="" aria-hidden="true" /></span>')
        desc = str(l.get("description") or "")
        desc_html = (f'<span class="cs-mega-link-desc"><span>{esc(desc)}</span></span>'
                     if desc else "")
        hover_cls = " cs-desc-hover" if l.get("descriptionOnHover") else ""
        return (f'<li><a class="cs-mega-link{hover_cls}" href="{esc(l.get("href") or "#")}">'
                f'{icon_html}<span><span class="cs-mega-link-title">{esc(l.get("label") or "")}</span>'
                f'{desc_html}</span></a></li>')

    def group_html(col: dict) -> str:
        head = str(col.get("heading") or "")
        head_html = f'<h4 class="cs-mega-head">{esc(head)}</h4>' if head else ""
        items = "".join(link_html(l) for l in (col.get("links") or []) if isinstance(l, dict))
        return f'<div class="cs-mega-group">{head_html}<ul>{items}</ul></div>'

    columns = [c for c in (menu.get("columns") or []) if isinstance(c, dict)]
    main = [c for c in columns if (c.get("area") or "main") != "aside"]
    aside_cols = [c for c in columns if (c.get("area") or "main") == "aside"]
    card = menu.get("card") if isinstance(menu.get("card"), dict) else None
    card_html = ""
    if card and (card.get("title") or card.get("image")):
        img = card.get("image") if isinstance(card.get("image"), dict) else {}
        img_html = (f'<img src="{esc(str(img["asset"]))}" alt="{esc(img.get("alt") or "")}" />'
                    if img.get("asset") else "")
        head = str(card.get("groupHeading") or "")
        head_html = f'<h4 class="cs-mega-head">{esc(head)}</h4>' if head else ""
        cta = card.get("cta") if isinstance(card.get("cta"), dict) else None
        cta_html = (f'<span class="cs-mega-card-cta">{esc(cta["label"])} &rarr;</span>'
                    if cta and cta.get("label") else "")
        body = str(card.get("body") or "")
        body_html = f'<p class="cs-mega-card-body">{esc(body)}</p>' if body else ""
        card_html = (f'<div class="cs-mega-aside-card">{head_html}'
                     f'<a class="cs-mega-card" href="{esc(card.get("href") or "#")}">'
                     f'{img_html}<p class="cs-mega-card-title">{esc(card.get("title") or "")}</p>'
                     f'{body_html}{cta_html}</a></div>')
    aside_html = ""
    if aside_cols or card_html:
        aside_html = ('<div class="cs-mega-aside">'
                      + "".join(group_html(c) for c in aside_cols)
                      + card_html + "</div>")
    id_attr = f' id="{esc(panel_id)}"' if panel_id else ""
    # LEFT CATEGORY RAIL (fid4-rail 2026-07): a tabbed mega layout renders a vertical
    # category rail beside its column groups (menu.sidebarTabs — captured structurally
    # from the hidden DOM). The first entry reads as the active tab. Fact-gated:
    # brands whose menu carries no rail emit byte-identical markup (no rail element).
    rail = [str(t).strip() for t in (menu.get("sidebarTabs") or []) if str(t).strip()]
    rail_html = ""
    if rail:
        items = "".join(
            f'<li class="cs-mega-rail-item{" cs-mega-rail-item--active" if i == 0 else ""}">'
            f'<span class="cs-mega-rail-label">{esc(t)}</span>'
            f'<span class="cs-mega-rail-chev" aria-hidden="true">&rsaquo;</span></li>'
            for i, t in enumerate(rail))
        rail_html = f'<nav class="cs-mega-rail" aria-label="Categories"><ul>{items}</ul></nav>'
    return (f'<div class="cs-mega"{id_attr}><div class="cs-mega-inner">'
            f'{rail_html}'
            f'<div class="cs-mega-main">{"".join(group_html(c) for c in main)}</div>'
            f'{aside_html}</div></div>')


def _nav_trigger_chevron(doc) -> dict | None:
    """The dropdown-trigger family chevron fact (navbar.measured.trigger.chevron,
    fid15) with resolved artwork — None when the brand captured none."""
    nav = (doc or {}).get("navbar") or {}
    trig = (nav.get("measured") or {}).get("trigger") \
        if isinstance(nav.get("measured"), dict) else None
    ch = (trig or {}).get("chevron") if isinstance(trig, dict) else None
    return ch if isinstance(ch, dict) and ch.get("_dataUri") else None


def _nav_utility(doc) -> list[dict]:
    """The bar's captured in-bar utility controls (navbar.utility[], fid15)."""
    nav = (doc or {}).get("navbar") or {}
    return [u for u in (nav.get("utility") or [])
            if isinstance(u, dict) and (u.get("label") or u.get("ariaLabel"))]


def _nav_chevron_uri(doc) -> str:
    """The bar's shared chevron-artwork data URI (the trigger-family fact first,
    else the first utility control that harvested one) — "" when none resolved."""
    ch = _nav_trigger_chevron(doc)
    if ch:
        return str(ch.get("_dataUri") or "")
    for u in _nav_utility(doc):
        c = u.get("chevron") if isinstance(u.get("chevron"), dict) else None
        if isinstance(c, dict) and c.get("_dataUri"):
            return str(c["_dataUri"])
    return ""


def _nav_chev_span(chev, shared_uri: str = "") -> str:
    """Chevron <span> for a RESOLVED chevron fact ('' when the artwork didn't
    resolve — degrade is no glyph, never an invented caret). fix4: sanitized
    single-ink artwork nests INLINE <svg> in the span (each instance id-safe via
    _svg_instance); unverified artwork keeps the fix2 mask channel, where the
    bar's SHARED artwork rides the .cs-nav-chev--mask class default
    (nav_affordance_css) and an inline var override is emitted only for a span
    whose glyph differs from it."""
    if isinstance(chev, dict) and chev.get("_inlineSvg"):
        return (f'<span class="cs-nav-chev" aria-hidden="true">'
                f'{_svg_instance(str(chev["_inlineSvg"]))}</span>')
    uri = str(chev.get("_dataUri") or "") if isinstance(chev, dict) else ""
    if not uri:
        return ""
    override = (f" style=\"--cs-nav-chev:url('{uri}')\""
                if uri != shared_uri else "")
    return f'<span class="cs-nav-chev cs-nav-chev--mask" aria-hidden="true"{override}></span>'


def _nav_utility_fragment(doc, items: list[dict] | None = None) -> str:
    """The bar's trailing UTILITY cluster (navbar.utility[], fid15): icon links
    (login etc.) and icon dropdowns (locale switchers) rendered from CAPTURED
    facts. Resting bar anatomy — it renders wherever the shared bar renders
    (composed page-level nav AND the gallery/spec-book bar demo), unlike the
    hover mega panels which stay page-level (ctx.mega_nav).

    Glyph artwork binds ONLY via prepare_chrome_glyphs data URIs (CSS masks
    riding currentColor); a control whose glyph did not resolve degrades to its
    accessible TEXT label — never invented artwork. Dropdowns are <details>
    panels (open state works without JS; Enter/Space toggles natively —
    keyboard-accessible by construction). Brands without the facts get ""
    (byte-identical bars).

    ``items`` (fix1 2026-07 item-12a): an explicit control subset — the two-tier
    bar splits the captured utility run into leading/trailing clusters and renders
    each through this same device. None keeps the whole captured run (the
    single-bar grammar, byte-identical for existing brands)."""
    utility = _nav_utility(doc) if items is None else items
    if not utility:
        return ""
    shared_chev = _nav_chevron_uri(doc)
    fam_chev = _nav_trigger_chevron(doc)  # family caret for dropdowns without their own
    frags = []
    for u in utility:
        label = str(u.get("label") or u.get("ariaLabel") or "").strip()
        icon = u.get("icon") if isinstance(u.get("icon"), dict) else {}
        icon_uri = str(icon.get("_dataUri") or "")
        if icon.get("_inlineSvg"):
            # fix4 inline channel: sanitized single-ink artwork nests in the span
            icon_html = (f'<span class="cs-nav-util-icon" aria-hidden="true">'
                         f'{_svg_instance(str(icon["_inlineSvg"]))}</span>')
        else:
            icon_html = (f'<span class="cs-nav-util-icon cs-nav-util-icon--mask" '
                         f'aria-hidden="true" '
                         f"style=\"--cs-util-icon:url('{icon_uri}')\"></span>"
                         if icon_uri else "")
        dd = u.get("dropdown") if isinstance(u.get("dropdown"), dict) else None
        items = [i for i in ((dd or {}).get("items") or [])
                 if isinstance(i, dict) and str(i.get("label") or "").strip()]
        if str(u.get("kind") or "") == "dropdown" and items:
            ch = u.get("chevron") if isinstance(u.get("chevron"), dict) else None
            chev_html = (_nav_chev_span(ch, shared_chev)
                         or _nav_chev_span(fam_chev, shared_chev))
            # collapsed presentation: the captured collapsed label when the source
            # shows one; icon-only otherwise (the accessible name rides aria-label);
            # NO resolved glyph at all ⇒ the text label is the degrade.
            shown = str(u.get("collapsedLabel") or "").strip()
            shown_html = (f'<span class="cs-nav-util-label">{esc(shown)}</span>'
                          if shown else
                          ("" if icon_html
                           else f'<span class="cs-nav-util-label">{esc(label)}</span>'))
            items_html = "".join(
                f'<li><a class="cs-nav-lang-item" href="{esc(i.get("href") or "#")}"'
                + (f' hreflang="{esc(str(i["lang"]))}"' if i.get("lang") else "")
                + (' aria-current="true"' if i.get("current") else "")
                + f'>{esc(str(i["label"]))}</a></li>'
                for i in items)
            frags.append(
                f'<details class="cs-nav-lang">'
                f'<summary class="cs-nav-util-link" aria-label="{esc(label)}">'
                f'{icon_html}{shown_html}{chev_html}</summary>'
                f'<ul class="cs-nav-lang-menu">{items_html}</ul></details>')
        else:
            frags.append(
                f'<a class="cs-nav-util-link" href="{esc(u.get("href") or "#")}">'
                f'{icon_html}<span>{esc(label)}</span></a>')
    return f'<span class="cs-nav-util">{"".join(frags)}</span>'


def nav_affordance_css(doc, honor_curation: bool = True) -> str:
    """Bar-affordance CSS (fid15) — emitted ONLY when this brand captured the facts:
    the dropdown-trigger chevron (harvested glyph as a currentColor mask, measured
    box/gap, open rotation riding the measured motion) and the in-bar utility
    cluster (icon links + icon dropdowns with the measured panel/item paint).
    Fact-less brands get "" and keep byte-identical pages.

    ``honor_curation`` — lane semantics (brand-schema §4.4c, the workflow-header
    precedent applied to chrome motion): a curator's recorded ruling on the
    chevron fact (``chevron.curation.motion.resolve: instant``, fix5 2026-07)
    replaces the measured open-rotation TWEEN with an instant transform swap in
    GENERATION lanes. The replica lane passes False and keeps the measured
    transition — it rebuilds the source 1:1 and stays evidence-faithful."""
    utility = _nav_utility(doc)
    # chevron GEOMETRY facts: the trigger-family fact first; a brand whose only
    # captured chevron rides a utility control still gets the shared rule.
    chev = _nav_trigger_chevron(doc) \
        or next((u["chevron"] for u in utility
                 if isinstance(u.get("chevron"), dict)
                 and u["chevron"].get("_dataUri")), None)
    if not (chev or utility):
        return ""
    nav = (doc or {}).get("navbar") or {}
    parts = ["\n/* bar affordances (fid15): navbar.measured.trigger.chevron +"
             " navbar.utility — measured chrome facts, inlined like the mega panel */"]
    if chev:
        box = chev.get("box") if isinstance(chev.get("box"), dict) else {}
        w = int(box.get("w") or 14)
        h = int(box.get("h") or 14)
        gap = chev.get("gap")
        gap_px = f"{int(gap)}px" if isinstance(gap, (int, float)) else "0.25em"
        # measured transition wins; the fact-less degrade is the INSTANT swap —
        # motion on a state-change glyph must be measured or absent (AS-47:
        # "degrades to the instant toggle, never to an invented 200ms"; the old
        # degrade invented a rotation tween on the brand's motion tokens).
        trans = _mega_first(chev.get("transition"), "none")
        # curated instant swap (fix5 2026-07): the user's ruling on the OPEN flip
        # ("no spin — swap direction instantly") rides the fact as curation data;
        # generation lanes honor it, the replica keeps the measured tween.
        cur = (chev.get("curation") or {}).get("motion") \
            if isinstance(chev.get("curation"), dict) else None
        if honor_curation and isinstance(cur, dict) \
                and str(cur.get("resolve") or "").lower() == "instant":
            trans = "none"
        open_tf = str(chev.get("openTransform") or "rotate(180deg)")
        # fix4 inline channel: box/motion stay on the class; the artwork is the
        # span's nested sanitized <svg> (currentColor ink). The mask channel is
        # the DEGRADE (.cs-nav-chev--mask) for unverified artwork — its shared
        # trigger data URI stays the class default; a control whose glyph
        # differs overrides the var inline on its own span.
        uri = _nav_chevron_uri(doc)
        parts.append(f""".cs-nav-chev {{
  display: inline-block; width: {w}px; height: {h}px; margin-left: {gap_px};
  vertical-align: -0.125em; flex: 0 0 auto;
  transition: {trans};
}}
.cs-nav-chev > svg {{ display: block; width: 100%; height: 100%; }}
.cs-nav-chev--mask {{
  --cs-nav-chev: url('{uri}');
  background: currentColor;
  -webkit-mask: var(--cs-nav-chev) center / contain no-repeat;
  mask: var(--cs-nav-chev) center / contain no-repeat;
}}
.cs-nav-tab:hover .cs-nav-chev, .cs-nav-tab:focus-within .cs-nav-chev,
.cs-nav-lang[open] .cs-nav-chev {{ transform: {open_tf}; }}
.cs-nav-tab.cs-nav-tab--closed:hover .cs-nav-chev,
.cs-nav-tab.cs-nav-tab--closed:focus-within .cs-nav-chev {{ transform: none; }}
@media (prefers-reduced-motion: reduce) {{ .cs-nav-chev {{ transition: none; }} }}""")
    if utility:
        dd = next((u.get("dropdown") for u in utility
                   if isinstance(u.get("dropdown"), dict)), None) or {}
        panel = dd.get("panel") if isinstance(dd.get("panel"), dict) else {}
        item = dd.get("item") if isinstance(dd.get("item"), dict) else {}
        cur = dd.get("currentItem") if isinstance(dd.get("currentItem"), dict) else {}
        p_bg = str(panel.get("bg") or "var(--c-paper)")
        p_border = str(panel.get("border") or "1px solid var(--c-hairline)")
        p_radius = int(panel.get("radius") or 6)
        p_pad = int(panel.get("paddingY") or 8)
        p_minw = max(150, min(int(panel.get("w") or 180), 320))
        i_fs = int(item.get("fontSize") or 15)
        i_pad = str(item.get("padding") or "10px 12px")
        i_radius = int(item.get("radius") or 2)
        i_color = str(item.get("color") or "inherit")
        cur_bg = str(cur.get("bg") or "var(--c-ink)")
        cur_ink = str(cur.get("color") or "var(--c-paper)")
        # measured utility-link register (bar tier link styles) when extracted
        util_reg = (nav.get("measured") or {}).get("utilityLink") \
            if isinstance(nav.get("measured"), dict) else None
        util_fs = f"{int(util_reg['fontSize'])}px" \
            if isinstance(util_reg, dict) and util_reg.get("fontSize") \
            else "var(--c-nav-size, var(--c-control-size))"
        # invented hover washes are DNA leaks (AS-24); the wash ships only measured.
        item_hover = str(item.get("hoverBg") or "").strip()
        hover_rule = (
            f"\n.cs-nav-lang-item:hover, .cs-nav-lang-item:focus-visible {{"
            f" /* provenance: structural navbar.utility[].dropdown.item.hoverBg */"
            f" background: {item_hover}; }}") if item_hover else ""
        parts.append(f""".cs-nav-util {{ display: inline-flex; align-items: center; gap: 1.1rem; }}
.cs-nav-util-link {{
  /* provenance: structural navbar.measured.utilityLink — the bar's measured
     utility-tier link register (fontSize), inlined like the mega panel */
  display: inline-flex; align-items: center; gap: 0.5em;
  font-family: var(--c-font-body); font-size: {util_fs};
  color: inherit; text-decoration: none;
  cursor: pointer; white-space: nowrap; list-style: none;
}}
.cs-nav-util-link::-webkit-details-marker {{ display: none; }}
.cs-nav-util-icon {{
  display: inline-block; width: 1.35em; height: 1.35em; flex: 0 0 auto;
}}
.cs-nav-util-icon > svg {{ display: block; width: 100%; height: 100%; }}
.cs-nav-util-icon--mask {{
  background: currentColor;
  -webkit-mask: var(--cs-util-icon) center / contain no-repeat;
  mask: var(--cs-util-icon) center / contain no-repeat;
}}
.cs-nav-lang {{ position: relative; display: inline-block; }}
.cs-nav-lang-menu {{
  /* provenance: structural navbar.utility[].dropdown.panel — measured open-state
     paint (portal panel; a saved snapshot cannot show it, captured live) */
  position: absolute; right: 0; top: calc(100% + 8px); z-index: 60;
  margin: 0; padding: {p_pad}px; list-style: none;
  min-width: {p_minw}px; max-height: 60vh; overflow-y: auto;
  background: {p_bg}; border: {p_border}; border-radius: {p_radius}px;
  box-shadow: 0 12px 32px rgba(0,0,0,0.12); text-align: left;
}}
.cs-nav-lang-item {{
  /* provenance: structural navbar.utility[].dropdown.item — measured open-state
     item register (fontSize/padding/radius, captured live) */
  display: block; padding: {i_pad}; font-size: {i_fs}px; color: {i_color};
  border-radius: {i_radius}px; white-space: nowrap; text-decoration: none;
}}{hover_rule}
.cs-nav-lang-item[aria-current] {{ background: {cur_bg}; color: {cur_ink}; }}
@media (max-width: 991px) {{ .cs-nav-util {{ display: none; }} }}""")
    return "\n".join(parts)


# ── interaction parity script (interaction remediation 2026-07) ──────────────────
# provenance: structural — keyboard/AT parity for the chrome's hover- and
# native-element-driven disclosures (interaction-contracts.md). Four guarded
# blocks, each emitted ONLY when its component signature exists in the page
# markup; a page with none of them ships no script at all. Brand-agnostic by
# construction: no copy, no colors, no measured values — only state wiring.
# The CSS-only paths (hover panels, native <details>) keep working with JS off;
# this layer adds aria-expanded truth, Escape dismissal with focus restore
# (WCAG 1.4.13), banner dismissal, and rail arrow-key scrolling.

_IX_NAV_JS = """
  /* mega-menu triggers (IC-NAV-01/02/07/08): aria-expanded mirrors the CSS
     hover/focus-within open state; click toggles; Escape closes and returns
     focus to the trigger. .cs-nav-tab--closed suppresses the CSS open rules
     until the pointer leaves, so dismissal wins over :hover. */
  document.querySelectorAll('.cs-nav-tab').forEach(function (tab) {
    var trig = tab.querySelector('.cs-nav-trigger');
    var panel = tab.querySelector('.cs-mega');
    if (!trig || !panel) return;
    var CLOSED = 'cs-nav-tab--closed';
    var set = function (open) {
      trig.setAttribute('aria-expanded', open ? 'true' : 'false');
    };
    var shut = function (refocus) {
      tab.classList.add(CLOSED); set(false);
      if (refocus) trig.focus();
    };
    tab.addEventListener('mouseenter', function () {
      tab.classList.remove(CLOSED); set(true);
    });
    tab.addEventListener('mouseleave', function () {
      tab.classList.remove(CLOSED);
      set(tab.contains(document.activeElement));
    });
    tab.addEventListener('focusin', function () {
      if (!tab.classList.contains(CLOSED)) set(true);
    });
    tab.addEventListener('focusout', function (e) {
      if (!tab.contains(e.relatedTarget)) { tab.classList.remove(CLOSED); set(false); }
    });
    trig.addEventListener('click', function (e) {
      if (trig.tagName === 'BUTTON') e.preventDefault();
      if (trig.getAttribute('aria-expanded') === 'true') shut(false);
      else { tab.classList.remove(CLOSED); set(true); }
    });
    tab.addEventListener('keydown', function (e) {
      if (e.key !== 'Escape' || tab.classList.contains(CLOSED)) return;
      shut(true); e.stopPropagation();
    });
  });"""

_IX_LANG_JS = """
  /* utility dropdowns (IC-LANG-06): Escape closes any open <details> switcher
     and restores focus to its summary when focus was inside it. */
  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape') return;
    document.querySelectorAll('details.cs-nav-lang[open]').forEach(function (d) {
      var inside = d.contains(document.activeElement);
      d.removeAttribute('open');
      var s = d.querySelector('summary');
      if (inside && s) s.focus();
    });
  });"""

_IX_BANNER_JS = """
  /* utility banner (IC-BAN-04): the extracted dismissible fact — click/Enter
     hides the strip (no persistence; the capture declares none). */
  document.querySelectorAll('.cs-utility-banner-close').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var strip = btn.closest('#page-banner') || btn.closest('.cs-utility-banner');
      if (strip) strip.style.display = 'none';
    });
  });"""

_IX_RAIL_JS = """
  /* edge-cut rails (IC-CAR-01/05): explicit ArrowLeft/ArrowRight scrolling on
     the focusable scroller, one card-width per press (cross-browser parity —
     native scroll-container arrow keys are Chromium-only). Measured rail chrome
     (data-railbtn prev/next, fix1 2026-07) drives the same one-card step. */
  document.querySelectorAll('.cs-edgecut').forEach(function (rail) {
    var step = function () {
      var card = rail.querySelector('.cs-module');
      return card ? card.getBoundingClientRect().width : rail.clientWidth / 2;
    };
    rail.addEventListener('keydown', function (e) {
      if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
      if (e.target !== rail) return;
      rail.scrollBy({ left: e.key === 'ArrowRight' ? step() : -step() });
      e.preventDefault();
    });
    var wrap = rail.parentElement;
    if (wrap && wrap.classList.contains('cs-edgecut-wrap')) {
      wrap.querySelectorAll('[data-railbtn]').forEach(function (btn) {
        var kind = btn.getAttribute('data-railbtn');
        if (kind === 'pause') {
          /* measured autoplay toggle: the static replica has no motion to stop,
             so the control only reflects pressed state (source-anatomy chrome). */
          btn.addEventListener('click', function () {
            btn.setAttribute('aria-pressed',
              btn.getAttribute('aria-pressed') === 'true' ? 'false' : 'true');
          });
          return;
        }
        btn.addEventListener('click', function () {
          var dir = kind === 'next' ? 1 : -1;
          rail.scrollBy({ left: dir * step() });
        });
      });
    }
  });"""

_IX_TABS_JS = """
  /* TAB DEVICE (fix1 2026-07, IC-TAB contract): WAI-ARIA APG tabs — click selects;
     roving tabindex; ArrowLeft/ArrowRight (wrap) + Home/End move focus AND
     selection (selection follows focus). Panels toggle via [hidden]. */
  document.querySelectorAll('[data-tabs]').forEach(function (root) {
    var tabs = Array.prototype.slice.call(root.querySelectorAll('[role="tab"]'));
    if (!tabs.length) return;
    var select = function (tab) {
      tabs.forEach(function (t) {
        var on = t === tab;
        t.setAttribute('aria-selected', on ? 'true' : 'false');
        if (on) { t.removeAttribute('tabindex'); } else { t.setAttribute('tabindex', '-1'); }
        var panel = document.getElementById(t.getAttribute('aria-controls') || '');
        if (panel) { panel.hidden = !on; }
      });
    };
    tabs.forEach(function (tab, i) {
      tab.addEventListener('click', function () { select(tab); });
      tab.addEventListener('keydown', function (e) {
        var to = null;
        if (e.key === 'ArrowRight') to = tabs[(i + 1) % tabs.length];
        else if (e.key === 'ArrowLeft') to = tabs[(i - 1 + tabs.length) % tabs.length];
        else if (e.key === 'Home') to = tabs[0];
        else if (e.key === 'End') to = tabs[tabs.length - 1];
        if (!to) return;
        e.preventDefault();
        to.focus(); select(to);
      });
    });
  });"""

_IX_PANELCAR_JS = """
  /* SPLIT-PANEL CAROUSEL (fix1 2026-07, IC-CAR contract): prev/next + dot
     controls switch the visible slide panel ([hidden] toggles); the active dot
     carries aria-current; prev/next disable at the ends (the captured states). */
  document.querySelectorAll('[data-panelcar]').forEach(function (root) {
    var slides = Array.prototype.slice.call(root.querySelectorAll('[data-panelcar-i]'));
    var dots = Array.prototype.slice.call(root.querySelectorAll('[data-panelcar-dot]'));
    var prev = root.querySelector('[data-panelcar-prev]');
    var next = root.querySelector('[data-panelcar-next]');
    if (!slides.length) return;
    var current = 0;
    var show = function (i) {
      current = Math.max(0, Math.min(slides.length - 1, i));
      slides.forEach(function (s, j) { s.hidden = j !== current; });
      dots.forEach(function (d, j) {
        if (j === current) { d.setAttribute('aria-current', 'true'); }
        else { d.removeAttribute('aria-current'); }
      });
      if (prev) prev.disabled = current === 0;
      if (next) next.disabled = current === slides.length - 1;
    };
    if (prev) prev.addEventListener('click', function () { show(current - 1); });
    if (next) next.addEventListener('click', function () { show(current + 1); });
    dots.forEach(function (d, j) {
      d.addEventListener('click', function () { show(j); });
    });
  });"""

_IX_IMAGE_JS = """
  /* Image placeholder lifecycle (AS-23): attribute absent = unresolved/loading,
     loaded = remove the hatch completely, error = retain the hatch fallback.
     Listeners are attached before the complete/naturalWidth reconciliation so both
     lazy future loads and cache-complete images are handled without inline handlers. */
  document.querySelectorAll('img.c-image').forEach(function (img) {
    var set = function (state) { img.setAttribute('data-load-state', state); };
    var loaded = function () { set('loaded'); };
    var failed = function () { set('error'); };
    img.addEventListener('load', loaded);
    img.addEventListener('error', failed);
    if (img.complete) {
      if (img.naturalWidth > 0) loaded();
      else failed();
    }
  });"""


def interaction_script(markup: str) -> str:
    """The page's keyboard/AT-parity <script> — assembled from the guarded blocks
    whose component signatures appear in ``markup`` (the fully assembled body).
    Pages with none of the components get "" (no script tag at all)."""
    blocks = []
    if "cs-nav-tab" in markup:
        blocks.append(_IX_NAV_JS)
    if "cs-nav-lang" in markup:
        blocks.append(_IX_LANG_JS)
    if "cs-utility-banner-close" in markup:
        blocks.append(_IX_BANNER_JS)
    if "cs-edgecut" in markup:
        blocks.append(_IX_RAIL_JS)
    if "data-tabs" in markup:
        blocks.append(_IX_TABS_JS)
    if "data-panelcar" in markup:
        blocks.append(_IX_PANELCAR_JS)
    if '<img class="c-image' in markup:
        blocks.append(_IX_IMAGE_JS)
    if not blocks:
        return ""
    return ("<script>\n(function () {" + "".join(blocks) + "\n})();\n</script>")


def footer_grammar(doc) -> str:
    """Structural-variant flag `footer-grammar` → 'display-links' | 'columns'.

    Resolution mirrors input_shape/cta_shape: the brand's own extracted facts pick the
    grammar. A type-scale footer display tier (e.g. a measured footer-sitemap-link
    register) selects the oversized display-links device; an extracted multi-column
    footer (footer.columns) selects the measured directory. Brands carrying neither
    keep display-links — the legacy bookend default — so existing renders are stable."""
    # Explicit measured directory anatomy outranks a typography role whose name
    # happens to contain "footer". A compact ``footer-sitemap-link`` token
    # describes links inside a column directory; it is not evidence for the
    # oversized display-links variant.
    cols = (doc.get("footer") or {}).get("columns")
    if isinstance(cols, list) and cols:
        return "columns"
    types = (doc.get("tokens", {}) or {}).get("type", {}) or {}
    keys = set(types.keys()) if isinstance(types, dict) else set()
    scale = types.get("scale") if isinstance(types, dict) else None
    if isinstance(scale, dict):  # families+scale shape (flat role keys covered above)
        keys |= set(scale.keys())
    if any("footer" in str(k).lower() for k in keys):
        return "display-links"
    return "display-links"


def footer_content(doc) -> dict:
    """Pull the closing-bookend footer copy from brand.yaml (read-only), shaped by the
    brand's footer GRAMMAR (footer_grammar, fix-batch 2026-07 B6):

    - display-links: the oversized slash SITEMAP — the brand's primary-nav destinations
      (navbar.primary labels + nav cta), each resolved against footer.columns for its
      real href. The nav-destination set comes from the brand's own extracted navbar —
      never a hardcoded label list (the old literal tuple was one brand's nav frozen
      into the scaffold).
    - columns: the extracted footer.columns passed through verbatim (the measured
      multi-column directory brands keep their real sitemap).

    Social (TEXT links) + the legal line come from footer.social / footer.legal in both
    grammars; never fabricated. Lives here (not compose_page) so the components-preview
    gallery shares the SAME content source as the composed page without an import cycle.

    CASING IS CSS-ONLY (nav-fix 2026-07): labels pass through as extracted (a network
    slug is capitalized — data cleanup, not styling); any uppercase presentation comes
    from the brand's OWN case tokens on the link classes, never a Python transform."""
    foot = doc.get("footer") or {}
    social = [{"label": (s.get("label") or (s.get("network") or "").capitalize()),
               "href": s.get("href", "#")}
              for s in (foot.get("social") or []) if s.get("network") or s.get("label")]
    legal = ((foot.get("legal") or {}).get("text") or "").strip()
    # policy links (fid2 2026-07): the extracted footer.legal.links pass through for
    # the bottom bar (Security/Privacy/Terms …) — real hrefs, never fabricated.
    legal_links = [l for l in ((foot.get("legal") or {}).get("links") or [])
                   if isinstance(l, dict) and l.get("label")]
    if footer_grammar(doc) == "columns":
        out = {"columns": foot.get("columns") or [], "social": social, "legal": legal,
               "legalLinks": legal_links}
        # fid4 2026-07: the measured directory HIERARCHY + bottom-bar structure ride
        # along when the extraction carries them (all optional — brands without the
        # facts keep the flat directory + legacy one-row bar, byte-identical).
        measured = foot.get("measured") or {}
        sizes = [int(s) for s in ((measured.get("grid") or {}).get("wrapperSizes") or [])
                 if isinstance(s, (int, float)) and int(s) > 0]
        if sizes and sum(sizes) == len(out["columns"]):
            out["cells"] = sizes          # groups-per-major-column, source order
            grid = measured.get("grid") or {}
            if isinstance(grid.get("columnGap"), (int, float)):
                out["colGap"] = int(grid["columnGap"])
            if isinstance(grid.get("rowGap"), (int, float)):
                out["cellGap"] = int(grid["rowGap"])
            if isinstance(measured.get("contentMaxWidth"), (int, float)):
                out["colsMax"] = int(measured["contentMaxWidth"])
        # measured link ROW RHYTHM: stride between consecutive directory links minus
        # the line box = the real list gap (so column heights match the source).
        link_m = measured.get("link") if isinstance(measured.get("link"), dict) else {}
        stride = link_m.get("rowStride")
        lh = str(link_m.get("lineHeight") or "").replace("px", "").strip()
        if isinstance(stride, (int, float)) and stride > 0:
            try:
                out["linkGap"] = max(0, int(stride) - int(round(float(lh or 0))))
            except ValueError:
                pass
        if isinstance(measured.get("heading"), dict):
            out["headingStyle"] = measured["heading"]
        if isinstance(foot.get("bottomBar"), dict):
            out["bottomBar"] = foot["bottomBar"]
            if isinstance(foot["bottomBar"].get("gap"), (int, float)):
                out["bbGap"] = int(foot["bottomBar"]["gap"])
            if isinstance(foot["bottomBar"].get("gapAbove"), (int, float)):
                out["bbAbove"] = int(foot["bottomBar"]["gapAbove"])
            # the CENTERED-STACK anatomy (fix1 2026-07 item-11) draws the brand's
            # wordmark between social row and legal line — ride the resolved logo
            # along only when that anatomy is authored (other bars ignore it).
            if (str(foot["bottomBar"].get("anatomy") or "").strip().lower()
                    == "centered-stack" and isinstance(foot.get("logo"), dict)):
                out["footLogo"] = foot["logo"]
        # footer WORDMARK (fix1 2026-07 item-11): rides along when the artwork
        # resolved (prepare_chrome_glyphs stamped _dataUri) — the centered-stack
        # bottom bar renders it between the social row and the legal line.
        logo = foot.get("logo") if isinstance(foot.get("logo"), dict) else None
        if logo and logo.get("_dataUri"):
            out["logo"] = logo
        # the glyph cluster binds ONLY when every social link resolved a HARVESTED
        # SVG (prepare_chrome_glyphs stamped _dataUri) — a partial set degrades to
        # the accessible text row (never a mixed or invented mark).
        raw_social = [s for s in (foot.get("social") or []) if isinstance(s, dict)]
        glyphs = [s for s in raw_social
                  if isinstance(s.get("icon"), dict) and s["icon"].get("_dataUri")]
        if glyphs and len(glyphs) == len(raw_social):
            out["socialGlyphs"] = glyphs
        return out
    nav = doc.get("navbar") or {}
    nav_labels = [(l.get("label") or "").strip() for l in (nav.get("primary") or [])
                  if isinstance(l, dict)]
    cta_label = ((nav.get("cta") or {}).get("label") or "").strip()
    if cta_label:
        nav_labels.append(cta_label)
    nav_set = {l.lower() for l in nav_labels if l}
    sitemap, seen = [], set()
    for col in foot.get("columns") or []:
        for link in col.get("links") or []:
            lab = (link.get("label") or "").strip()
            key = lab.lower()
            if key in nav_set and key not in seen:
                seen.add(key)
                # label as-extracted; the display-links register's case rides the
                # brand's own case token (--c-foot-link-case / --c-case-heading).
                sitemap.append({"label": lab, "href": link.get("href", "#")})
    return {"sitemap": sitemap, "social": social, "legal": legal,
            "legalLinks": legal_links}


def block_device(doc, key: str) -> dict | None:
    """The brand's declared ``blocks.<key>`` evidence dict when the device is USABLE
    (declared, not ``notObserved``, ``use`` != never); None otherwise. The §C.3 gate
    for block-level structural variants (card / content-block): their CSS and
    renderers never ship dormant grammar for brands that don't carry the device."""
    blk = ((doc or {}).get("blocks") or {}).get(key)
    if not isinstance(blk, dict) or blk.get("notObserved"):
        return None
    if str(blk.get("use") or "").strip().lower() == "never":
        return None
    return blk


_BTN_FAMILY_VAR_KEYS = (
    ("bg", "--c-button-bg", "bg"),
    ("fg", "--c-button-fg", "fg"),
    ("bgHover", "--c-button-bg-hover", "bg-hover"),
    ("fgHover", "--c-button-fg-hover", "fg-hover"),
    ("padding", "--c-button-pad", "pad"),
    ("radius", "--c-button-radius", "radius"),
    ("weight", "--c-button-weight", "weight"),
    ("height", "--c-button-height", "height"),
)


def _button_families(doc) -> dict:
    """The brand's declared non-text button families beyond primary (fact dicts only)."""
    fams = {}
    for name, facts in ((doc or {}).get("buttons") or {}).items():
        if name == "primary" or not isinstance(facts, dict):
            continue
        style = str(facts.get("style") or "").lower()
        if "text" in style:            # text-link families ride the arrow-link device
            continue
        if facts.get("bg") or facts.get("border") or facts.get("fg"):
            fams[name] = facts
    return fams


def button_family_for_style(doc, hint: str) -> str | None:
    """Resolve a declared secondary button FAMILY from style prose: a slot role /
    evidence styleHint naming an outline/ghost (or other declared style word)
    treatment selects the brand family whose measured ``style`` fact matches.
    Palette-agnostic — the match is between the slot's declared treatment and the
    brand's OWN declared family styles; no family name is ever assumed."""
    def _norm(text: str) -> set[str]:
        canon = {"outlined": "outline", "ghosted": "ghost", "solid": "filled"}
        return {canon.get(w, w)
                for w in str(text or "").lower().replace("-", " ").split()}

    words = _norm(hint)
    if not words:
        return None
    # a DUAL-action description ("filled primary pill + outlined secondary pill")
    # names both treatments — it cannot select ONE family; the caller splits the
    # pair and hints each button separately (sysfix 2026-07: the whole-role hint
    # made the FIRST/primary button take the outline family).
    if "filled" in words and words & {"outline", "ghost", "quiet"}:
        return None
    # BEST-OVERLAP match (fix1 2026-07 item-3/8): among families whose declared
    # style carries a treatment word the hint names, the family sharing the MOST
    # style words wins — e.g. an "ink-outlined" hint selects an `outline-ink`
    # family over a plain `outline` one. Declared order breaks ties (the
    # historical first-match behavior for equally-specific families).
    best, best_score = None, 0
    for name, facts in _button_families(doc).items():
        style_words = _norm(facts.get("style"))
        if not style_words & words & {"outline", "ghost", "quiet", "neutral"}:
            continue
        score = len(style_words & words)
        if score > best_score:
            best, best_score = name, score
    if best:
        return best
    # FAMILY-NAME fallback (AS-59, archetype-gallery 2026-07): a hint naming one of
    # the brand's OWN declared families selects it — the common composition role
    # vocabulary (`secondary-action`, `cta-secondary`, `action-tertiary`) resolves
    # through the brand's family list, never an assumed register. Brands without a
    # family of that name degrade to primary exactly as before.
    for name in _button_families(doc):
        if _norm(name) & words:
            return name
    return None


def _accessible_name_for_label(doc, label: str, family: str | None = None) -> str:
    """Resolve a longer measured accessible name without changing painted copy."""
    buttons = (doc or {}).get("buttons") or {}
    candidates = []
    if family and isinstance(buttons.get(family), dict):
        candidates.append(buttons[family])
    if family is None and isinstance(buttons.get("primary"), dict):
        candidates.append(buttons["primary"])
    candidates.extend(
        facts for name, facts in buttons.items()
        if isinstance(facts, dict) and facts not in candidates
    )
    normalized = " ".join(str(label or "").split())
    for facts in candidates:
        visible = " ".join(str(facts.get("visibleLabel") or "").split())
        if visible and visible == normalized:
            return str(
                facts.get("ariaLabel") or facts.get("accessibleName") or ""
            ).strip()
    return ""


def _button_family_override_css(doc) -> str:
    """Per-family `.c-button--<family>` override rules for the brand's declared extra
    button families: every declaration re-points the shared `--c-button-*` consumption
    vars at that family's OWN Layer-1 tokens (only keys the family measured emit).
    An outline family also gets its measured border (the base rule is border: none)."""
    rules = []
    for name, facts in sorted(_button_families(doc).items()):
        sel = f".c-button--{_slug(name)}"
        decls = [f"{var}: var(--button-{_slug(name)}-{suffix});"
                 for key, var, suffix in _BTN_FAMILY_VAR_KEYS if facts.get(key)]
        if facts.get("border"):
            decls.append(f"border: var(--button-{_slug(name)}-border);")
        if decls:
            rules.append(sel + " { " + " ".join(decls) + " }")
    return ("\n" + "\n".join(rules) + "\n") if rules else ""


def _button_oninverse_css(doc) -> str:
    """Surface-scoped DARK-VARIANT button rules (fix1 2026-07 item-10). Emitted only
    when BOTH facts exist: a surface role declaring ``controls: onInverse``
    (tokens.surfaces — the brand says "this dark band swaps its control family
    variants") AND a non-primary button family carrying measured ``onInverse``
    facts (buttons.<family>.onInverse — emitted as ``--button-<family>-oninverse-*``
    by tokens_css). Each rule re-points the family's consumption vars INSIDE that
    surface's ``[data-surface]`` scope. Brands declaring neither fact emit zero
    bytes (Remote parity)."""
    surfaces = ((doc or {}).get("tokens") or {}).get("surfaces") or {}
    scoped_roles = [role for role, spec in surfaces.items()
                    if isinstance(spec, dict)
                    and str(spec.get("controls") or "").strip() == "onInverse"]
    if not scoped_roles:
        return ""
    rules = []
    for name, facts in sorted(_button_families(doc).items()):
        inv = facts.get("onInverse")
        if not isinstance(inv, dict):
            continue
        decls = [f"{var}: var(--button-{_slug(name)}-oninverse-{suffix});"
                 for key, var, suffix in _BTN_FAMILY_VAR_KEYS if inv.get(key)]
        if inv.get("border"):
            decls.append(f"border: var(--button-{_slug(name)}-oninverse-border);")
        if not decls:
            continue
        # LIGHT-PANEL opt-out: a solid light panel floated INSIDE the dark band
        # (.cs-ov-panel — its own opaque surface scope) keeps the family's light-
        # surface variant; the dark re-scope applies to controls on the band itself.
        sels = ", ".join(
            f'[data-surface="{esc(role)}"] .c-button--{_slug(name)}'
            f':not(.cs-ov-panel .c-button--{_slug(name)})'
            for role in scoped_roles)
        rules.append(sels + " { " + " ".join(decls) + " }")
    return ("\n" + "\n".join(rules) + "\n") if rules else ""


def _button_variant_css(doc) -> str:
    """``_BUTTON_VARIANT_CSS`` with the un-grounded hover LIFT purged when the brand's
    measured buttons carry no hover transform (fact-gated: responsive.buttons.
    purgeHoverTransform, provenance doctrine extended to MOTION). A brand without the
    fact keeps the line — byte-identical output (v2/remote unchanged)."""
    resp = ((doc or {}).get("responsive") or {}).get("buttons") \
        if isinstance(doc, dict) else None
    if isinstance(resp, dict) and resp.get("purgeHoverTransform"):
        # drop the trailing hover ``transform: translateY(-1px)`` (the composer default
        # the source never had); the measured bg/color swap stays.
        return _BUTTON_VARIANT_CSS.replace("\n  transform: translateY(-1px); }",
                                           " }")
    return _BUTTON_VARIANT_CSS


def structural_variant_css(doc, include_all: bool = False) -> str:
    """The §C.3 variant rules THIS brand's structural flags select (appended after
    COMPONENT_CSS by both composers). ``include_all=True`` is the gallery/harness mode:
    the gallery renders prohibited variants as labeled specimens, so it carries every
    variant's CSS regardless of the brand's flags."""
    parts = []
    if include_all or cta_shape(doc) == "filled":
        parts.append(_button_variant_css(doc))
        parts.append(_button_family_override_css(doc))
        parts.append(_button_oninverse_css(doc))
    if include_all or input_shape(doc) == "boxed":
        parts.append(_BOXED_FIELD_VARIANT_CSS)
    # block-device variants (sysfix 2026-07): gated on the brand DECLARING the device.
    if include_all or block_device(doc, "card"):
        parts.append(_CARD_VARIANT_CSS)
    if include_all or block_device(doc, "content-block"):
        parts.append(_CONTENT_BLOCK_VARIANT_CSS)
    grammar = footer_grammar(doc)
    if include_all or grammar == "display-links":
        parts.append(_FOOT_DISPLAY_LINKS_CSS)
    if include_all or grammar == "columns":
        parts.append(_FOOT_COLUMNS_CSS)
    # licensed accent devices (fix7): the device-role var block ships only where the
    # brand declares the license (accent_device_css itself is fact-gated).
    parts.append(accent_device_css(doc))
    return "".join(parts)


# ── licensed ACCENT DEVICES (fix7 2026-07; brand-schema §4.11) ────────────────────
# The brand's small recognizable accent moves as MACHINE-APPLICABLE licenses
# (brand.yaml `accentDevices:`): device kind + the token role that paints it +
# licensed contexts with optional floor/ceiling counts. Everything here is
# fact-gated — a brand without the block renders byte-identically, and no kind,
# mark, or glyph name is ever invented in code.

_ACCENT_DEVICE_KINDS = ("punctuation-accent", "marked-list-glyph",
                        "underline-accent", "accent-word")


def licensed_accent_devices(doc) -> list[dict]:
    """The brand's declared accentDevices entries (known kinds only), verbatim."""
    out = []
    for d in ((doc or {}).get("accentDevices") or []):
        if isinstance(d, dict) and str(d.get("kind") or "") in _ACCENT_DEVICE_KINDS:
            out.append(d)
    return out


def accent_device(doc, kind: str) -> dict | None:
    """The first licensed device of ``kind`` (None = the brand licenses none)."""
    for d in licensed_accent_devices(doc):
        if d.get("kind") == kind:
            return d
    return None


def accent_device_css(doc) -> str:
    """License-gated device vars: ``--c-accent-mark`` resolves the DEVICE's own
    token role (scheme-stable — the mark paints the same family on any surface,
    exactly what the landmark evidence shows), and the marker box rides the
    licensed glyph size. "" for license-less brands (the .c-accent-mark /
    .c-marked-list base rules then fall back to ink and never fire visually)."""
    devices = licensed_accent_devices(doc)
    if not devices:
        return ""
    decls = []
    role = next((str(d.get("role") or "") for d in devices if d.get("role")), "")
    if role:
        decls.append(f"--c-accent-mark: var(--color-{_slug(role)});")
    ml = accent_device(doc, "marked-list-glyph") or {}
    size = str(((ml.get("glyph") or {}) or {}).get("size") or "").strip()
    if re.fullmatch(r"[\d.]+(?:rem|em|px)", size):
        decls.append(f"--c-list-marker-size: {size};")
    if not decls:
        return ""
    return ("\n/* licensed accent devices (fix7): the device role's own token paints "
            "the mark */\n:root { " + " ".join(decls) + " }")


def _wrap_terminal_mark(inner: str, mark: str) -> str:
    """Wrap a rendered heading's TERMINAL licensed mark in the accent span (one
    per heading — the renderer applies the device at most once, which IS the
    per-heading ceiling). ``inner`` is already-escaped markup; only a bare
    trailing mark is wrapped (line/emphasis-span shapes end in a tag and skip)."""
    m = esc(mark)
    if not m or not inner.endswith(m) or inner.endswith("</span>" + m):
        return inner
    return (inner[: -len(m)]
            + f'<span class="c-accent-mark" data-accent-device="punctuation-accent">'
              f'{m}</span>')


def render_marked_list(doc, ctx: ComponentContext, props=None) -> str:
    """marked-list device (fix7 punch 3): ``props: items, measure``. Items render as
    a semantic <ul> with a hanging marker column. The marker is the brand's licensed
    marked-list glyph (sanitized inline SVG stashed on the doc by
    compose_section.attach_accent_devices) in the device's accent role; brands
    without the license keep a typographic dot at ink. Zero items elide."""
    props = props or {}
    items = [str(x).strip() for x in (props.get("items") or []) if str(x).strip()]
    if not items:
        return ""
    glyphs = (doc or {}).get("_accentGlyphs") if isinstance(doc, dict) else None
    svg = (glyphs or {}).get("marked-list-glyph") or ""
    licensed = bool(svg) and accent_device(doc, "marked-list-glyph") is not None

    def _marker() -> str:
        if licensed:
            return (f'<span class="c-list-marker" aria-hidden="true">'
                    f"{_svg_instance(svg)}</span>")
        return '<span class="c-list-marker" aria-hidden="true">&bull;</span>'

    lis = "\n".join(f"        <li>{_marker()}<span>{esc(t)}</span></li>" for t in items)
    device_attr = ' data-accent-device="marked-list-glyph"' if licensed else ""
    style = f' style="--c-measure:{esc(props["measure"])}"' if props.get("measure") else ""
    return f'<ul class="c-marked-list"{device_attr}{style}>\n{lis}\n      </ul>'


# ── per-component renderers (SINGLE SOURCE OF TRUTH) ─────────────────────────────

def _level_class(level):
    lv = str(level or "display").lower()
    if lv in ("display", "h0", "hero"):
        return "c-heading--display"
    # h1 is its own SECTION register (fix1 2026-07: pattern-measured headingRegister
    # tiers); no composer passed "h1" before, so legacy pages are unaffected.
    if lv in ("h1", "h2"):
        return f"c-heading--{lv}"
    if lv in ("h4", "h5", "h6"):
        return f"c-heading--{lv}"
    return "c-heading--h3"


def render_heading(doc, ctx: ComponentContext, props=None) -> str:
    """heading primitive (and the header block's heading slot). props: text, level,
    tag, accent. Splits a two-word display title onto two lines (the WoodWave bookend).
    editorial-harvest-2026-07 (P3, SSOT — never bespoke markup in a composer):
      - lines: [str, …]        stepped-lines (G7): each authored line renders as a block
                               `.c-heading-line` span; the scaffold applies per-line
                               registered indents (--c-step-N).
      - mixedFace: {lead, emphasis}   mixed-face (G5): the emphasis span renders as
                               `.c-heading-alt` — face contrast comes from --c-alt-style /
                               --c-alt-weight (weight contrast by default; a brand with a
                               real italic cut sets --c-alt-style: italic — NEVER a
                               synthesized italic)."""
    props = props or {}
    text = props.get("text", "Heading")
    level = props.get("level", "display")
    tag = props.get("tag") or ("h1" if _level_class(level) == "c-heading--display" else "h2")
    accent = " c-heading--accent" if props.get("accent") else ""
    inner = esc(text)
    lines = props.get("lines")
    mixed = props.get("mixedFace")
    if isinstance(lines, (list, tuple)) and len(lines) >= 2:
        inner = "".join(f'<span class="c-heading-line">{esc(str(ln))}</span>' for ln in lines)
    elif isinstance(mixed, dict) and (mixed.get("lead") or mixed.get("emphasis")):
        lead = esc(mixed.get("lead") or "")
        emph = esc(mixed.get("emphasis") or "")
        inner = (lead + (" " if lead and emph else "")
                 + (f'<em class="c-heading-alt">{emph}</em>' if emph else "")).strip()
    elif props.get("splitTwoLines"):
        # the WoodWave bookend device is a TWO-WORD display title split — a longer
        # sentence heading must never be broken after its first word (fid2 2026-07:
        # "The<br>world's best teams…" shipped a bogus break + a needlessly narrow
        # column on every sentence-cased section heading routed with the flag on).
        parts = str(text).split(" ")
        if len(parts) == 2:
            inner = f"{esc(parts[0])}<br>{esc(parts[1])}"
    # PUNCTUATION-ACCENT device (fix7 punch 1): when the brand LICENSES the device
    # and this heading is a LANDMARK — the display rank, an accent-flagged landmark
    # heading (the closing-band shape), or a composer-declared `landmark` (a hero
    # split registers its opening statement at a measure-fit tier, but it is still
    # the page's landmark heading) — a terminal mark matching the license wraps in
    # the device span. Extracted-but-never-applied was the defect: the signature
    # said landmark serif headings may close with the accent period, and no
    # renderer ever painted it. Fact-gated: license-less brands are byte-identical.
    dev = accent_device(doc, "punctuation-accent")
    if dev is not None and (
            _level_class(level) == "c-heading--display" or props.get("accent")
            or props.get("landmark")):
        inner = _wrap_terminal_mark(inner, str(dev.get("mark") or "").strip())
    return f'<{tag} class="c-heading {_level_class(level)}{accent}">{inner}</{tag}>'


def render_eyebrow(doc, ctx: ComponentContext, props=None) -> str:
    props = props or {}
    return f'<p class="c-eyebrow">{esc(props.get("text", "Eyebrow"))}</p>'


# Media treatment is an EXPLICIT asset-kind + slot-role fact.  The active brand's
# assets-tagged.json is attached under ``_assetTags`` / ``_mediaTreatmentRules`` by
# compose_section.attach_asset_inventory.  No basename vocabulary lives here: a file
# renamed from "illustration.webp" to "asset-17.webp" must render identically when its
# facts are unchanged, and a misleading filename must never change its crop.
def asset_render_mode(doc, src, role: str = "") -> str:
    """Return ``cover`` | ``contain`` | ``mark`` from captured media-treatment facts.

    Resolution: the media-assets.v1 registry's per-asset ``treatmentDefaults.fit``
    (media semantics 2026-07 — attached as ``_mediaAssetsFit`` by
    ``compose_section.attach_asset_inventory``; brands without the artifact attach
    an empty map); then an asset's explicit ``mediaTreatment.fit``; then the first
    generic ``mediaTreatmentRules`` entry matching its ``assetKind`` and the
    requested slot role; finally ``cover`` (the safe photographic/full-bleed
    default).  Filename words and brand names are deliberately ignored.  ``mark``
    (hubspot-v2 2026-07) declares a device-frame glyph row — icon/logo art that
    renders at mark height inside its module, never as a media well.
    """
    name = Path(str(src or "")).name
    if not name:
        return "cover"
    # ASSET-KIND ↔ SLOT-ROLE ELIGIBILITY (media semantics 2026-07, AS-80): an
    # ICON/MARK-family kind (spot-icon/ui-glyph/social-icon/logo mark) is NEVER
    # blown up to fill a media well — whatever fit resolves below, a cover/contain
    # (or unset⇒cover) resolution is coerced to `mark` so a content-scale glyph
    # can never render as a card's lead/hero/full-bleed image. Fact-gated on the
    # asset's captured kind; image-family kinds pass through byte-identically. The
    # registry kind drives ONLY this coercion — the mediaTreatmentRules below still
    # match on the assets-tagged `assetKind` vocabulary exactly as before.
    import media_semantics as _ms
    kind_map = (doc or {}).get("_mediaAssetsKind") if isinstance(doc, dict) else None
    reg_kind = str(kind_map.get(name) or "").strip().lower() \
        if isinstance(kind_map, dict) else ""
    ms_fit = (doc or {}).get("_mediaAssetsFit") if isinstance(doc, dict) else None
    if isinstance(ms_fit, dict):
        fit = str(ms_fit.get(name) or "").strip().lower()
        if fit in ("cover", "contain", "mark"):
            return _ms.eligible_render_mode(reg_kind, fit) or fit
    tags = (doc or {}).get("_assetTags") if isinstance(doc, dict) else None
    fact = tags.get(name) if isinstance(tags, dict) else None
    if isinstance(fact, dict):
        kind = str(fact.get("assetKind") or fact.get("useCase") or "").strip().lower()
        eff_kind = reg_kind or kind
        direct = fact.get("mediaTreatment")
        fit = str((direct or {}).get("fit") or "").strip().lower() \
            if isinstance(direct, dict) else ""
        if fit in ("cover", "contain", "mark"):
            return _ms.eligible_render_mode(eff_kind, fit) or fit
        wanted_role = str(role or "").strip().lower()
        rules = (doc or {}).get("_mediaTreatmentRules") or []
        for rule in rules:
            if not isinstance(rule, dict):
                continue
            rule_kind = str(rule.get("assetKind") or "").strip().lower()
            rule_role = str(rule.get("role") or "*").strip().lower()
            if rule_kind != kind or rule_role not in ("*", wanted_role):
                continue
            fit = str(rule.get("fit") or "").strip().lower()
            if fit in ("cover", "contain", "mark"):
                return _ms.eligible_render_mode(eff_kind, fit) or fit
    # NO fit fact resolved: keep the historical `cover` default byte-identically
    # for EVERY kind (icons included). The coercion above only rewrites an EXPLICIT
    # media-well fit authored on an icon/mark asset — it must never rewrite this
    # unset default, so brands whose icon/mark assets legitimately fall to the
    # cover default (held baselines) stay byte-identical; the AS-80 gate row is the
    # arm that flags an icon left to blow up here.
    return "cover"


def render_image(doc, ctx: ComponentContext, props=None) -> str:
    """image primitive. props: src, alt, variant (hero|overlap), absolute (bool),
    aspect (a declared CSS aspect-ratio value, e.g. "21 / 9" — the composition contract's
    mediaAspect resolved by the adapter; wins over the variant's intrinsic ratio),
    contain (force contain-mode; otherwise derived from the asset-kind + media-role
    treatment facts), mediaRole (generic slot role such as card-media).
    With no src it renders the gallery placeholder (radius 0, no chrome)."""
    props = props or {}
    variant = props.get("variant", "")
    mod = f" c-image--{variant}" if variant in ("hero", "overlap") else ""
    aspect = props.get("aspect")
    style_parts = [f"aspect-ratio: {aspect}"] if aspect else []
    # masked-media clip (media semantics 2026-07, spec/media-assets-schema.md §3):
    # the image clips inside a brand accent-shape/logo silhouette. Declared-only —
    # mask-less images keep the exact historical markup.
    mask = props.get("mask")
    if mask:
        style_parts.append(
            f"-webkit-mask-image: url('{mask}'); mask-image: url('{mask}'); "
            "-webkit-mask-size: contain; mask-size: contain; "
            "-webkit-mask-repeat: no-repeat; mask-repeat: no-repeat; "
            "-webkit-mask-position: center; mask-position: center")
    style = f' style="{esc("; ".join(style_parts))}"' if style_parts else ""
    src = props.get("src")
    alt = esc(props.get("alt", ""))
    if not src:
        return f'<div class="c-image-ph{mod}"{style}>{esc(props.get("placeholder", "IMAGE / RADIUS 0"))}</div>'
    # transparent-PNG-safe ART mode (fid2 2026-07): non-photographic art contains at
    # natural aspect on a clean field; a DECLARED mediaAspect (inline style) still wins.
    if props.get("contain") or (props.get("contain") is None
                                and asset_render_mode(doc, src, props.get("mediaRole", ""))
                                == "contain"):
        mod += " c-image--art"
    abs_cls = " is-abs" if props.get("absolute") else ""
    return f'<img class="c-image{mod}{abs_cls}"{style} src="{esc(src)}" alt="{alt}">'


def textcta_glyph(doc) -> dict | None:
    """The brand's MEASURED text-CTA trailing glyph (buttons.<family>.glyph, fix2,
    brand-schema §10.2): the first text-link family carrying a harvested glyph
    asset that exists in the brand's asset inventory. None -> the Unicode arrow
    degrade (byte-identical for glyph-less brands). The inventory check rides the
    same `_assetInventory` law every other asset binding obeys — a fact naming a
    missing file must not emit a dead mask URL."""
    inv = (doc or {}).get("_assetInventory")
    for spec in ((doc or {}).get("buttons") or {}).values():
        if not isinstance(spec, dict):
            continue
        if "text" not in str(spec.get("style") or "").lower():
            continue
        g = spec.get("glyph")
        if isinstance(g, dict) and g.get("asset"):
            name = Path(str(g["asset"])).name
            if inv is not None and name not in set(inv):
                continue
            return {"asset": name, "size": str(g.get("size") or "1em"),
                    "uri": str(g.get("_dataUri") or ""),
                    "inline": str(g.get("_inlineSvg") or "")}
    return None


def render_arrow_link(doc, ctx: ComponentContext, props=None) -> str:
    """link primitive == cta role (WoodWave remaps cta -> arrow link, never a button).
    props: label, href, accent. Always a typographic <a>, NEVER a <button>.
    An EXPLICITLY EMPTY label elides the device (sysfix 2026-07): a label-less action
    is no action — the adapter no longer invents "Learn more"-style fallback copy, so
    a copy-less slot must not render a bare floating arrow glyph. The "Learn more"
    default still applies only when the caller passes no label key at all (harness
    specimen shorthand).
    GLYPH fact (fix2; fix4 inline channel): a brand whose text-CTA family declares
    a harvested SVG glyph renders it as sanitized INLINE <svg> markup (technique
    parity with source sites — fill rides currentColor, so ink follows the link's
    own color chain); artwork that failed single-ink verification keeps the fix2
    currentColor MASK degrade (`c-arrow--mask`). The `.c-arrow` class stays on the
    same host span either way, so the hover nudge and reduced-motion rules apply
    unchanged. No fact -> Unicode, byte-identical."""
    props = props or {}
    label = props.get("label", "Learn more")
    if not str(label or "").strip():
        return ""
    accent = " c-arrow-link--accent" if props.get("accent") else ""
    href = esc(props.get("href", "#"))
    g = textcta_glyph(doc)
    if g and g.get("inline"):
        arrow = (f'<span class="c-arrow c-arrow--glyph" aria-hidden="true" '
                 f'style="--c-arrow-glyph-size: {esc(g["size"])}">'
                 f'{_svg_instance(g["inline"])}</span>')
    elif g:
        # mask degrade (multi-color / unverified artwork): data-URI first
        # (prepare_chrome_glyphs resolves it: CSS masks are CORS fetches file://
        # pages cannot satisfy); asset path is the served degrade.
        src = g["uri"] or f"assets/{g['asset']}"
        arrow = (f'<span class="c-arrow c-arrow--glyph c-arrow--mask" aria-hidden="true" '
                 f'style="--c-arrow-glyph: url(\'{esc(src)}\');'
                 f' --c-arrow-glyph-size: {esc(g["size"])}"></span>')
    else:
        arrow = '<span class="c-arrow" aria-hidden="true">&rarr;</span>'
    accessible = str(
        props.get("ariaLabel") or props.get("accessibleName")
        or _accessible_name_for_label(doc, label)
    ).strip()
    aria = f' aria-label="{esc(accessible)}"' if accessible and accessible != label else ""
    return f'<a class="c-arrow-link{accent}" href="{href}"{aria}>{esc(label)} {arrow}</a>'


def render_button(doc, ctx: ComponentContext, props=None) -> str:
    """button primitive — a FILLED action (bg accent, readable label, brand radius).
    The counterpart of render_arrow_link for brands whose grammar REQUIRES filled
    buttons (e.g. HubSpot: neverDo.never-typographic-primary). DISPATCH IS THE
    DISCIPLINE (B5, fix-batch 2026-07): when the resolved cta-shape is typographic
    (ctx.cta, cached style-aware by the composer), a `button` contract DOWNGRADES to
    the typographic arrow link — a WoodWave-style brand literally cannot emit
    `.c-button` through the catalog, and a filled-CTA brand's `button` slots stop
    being dropped. props: label, href, accent (arrow-link path only)."""
    props = props or {}
    shape = ctx.cta or cta_shape(doc)
    if shape != "filled":
        return render_arrow_link(doc, ctx, {
            "label": props.get("label", "Get started"),
            "href": props.get("href", "#"),
            "accent": props.get("accent", False)})
    # FAMILY dispatch (sysfix 2026-07): an explicit declared family wins; else a
    # style HINT from the slot's evidence prose (e.g. "outlined pill") resolves to
    # the brand family whose measured `style` fact matches. Unknown → primary.
    family = props.get("family")
    if family not in _button_families(doc):
        family = button_family_for_style(doc, props.get("familyHint", ""))
    fam_cls = f" c-button--{_slug(family)}" if family else ""
    href = esc(props.get("href", "#"))
    accessible = str(
        props.get("ariaLabel") or props.get("accessibleName")
        or _accessible_name_for_label(doc, props.get("label", "Get started"), family)
    ).strip()
    aria = f' aria-label="{esc(accessible)}"' if accessible else ""
    return (f'<a class="c-button{fam_cls}" href="{href}" role="button"{aria}>'
            f'{esc(props.get("label", "Get started"))}</a>')


def render_logo(doc, ctx: ComponentContext, props=None) -> str:
    """logo primitive. TWO modes, gated on whether an image prop is passed:

    - IMAGE mode (props carries `img` or `src`): emit the extracted brand logo as
      `<a href><img src alt width height></a>`. Used by the composed nav, which feeds the
      resolved extracted logo. Kept accessible: alt falls back to the brand name when the
      extracted alt is empty. No border/radius/chip (honors WoodWave neverDo).
    - TEXT mode (no image prop): the original glyph + wordmark span, UNCHANGED. Used by any
      caller that passes no image (e.g. a text-wordmark card / a brand with no logo image),
      so those renders stay byte-identical.
    """
    props = props or {}
    img = props.get("img") or props.get("src")
    if img:
        brand_name = ((doc or {}).get("brand") or {}).get("name") or "Brand"
        alt = props.get("alt") or props.get("text") or brand_name
        href = esc(props.get("href", "#"))
        dims = ""
        if props.get("width"):
            dims += f' width="{esc(props["width"])}"'
        if props.get("height"):
            dims += f' height="{esc(props["height"])}"'
        return (f'<a class="c-logo c-logo--img" href="{href}">'
                f'<img class="c-logo-img" src="{esc(img)}" alt="{esc(alt)}"{dims}></a>')
    return (f'<span class="c-logo"><span class="c-glyph" aria-hidden="true">&#9697;</span> '
            f'{esc(props.get("text", "Brand"))}</span>')


def render_header(doc, ctx: ComponentContext, props=None) -> str:
    """header block - composes eyebrow + heading (+ optional cta) from the primitives
    above, so the block IS its slot components, not a parallel implementation."""
    props = props or {}
    parts = []
    if props.get("eyebrow"):
        parts.append(render_eyebrow(doc, ctx, {"text": props["eyebrow"]}))
    parts.append(render_heading(doc, ctx, {
        "text": props.get("heading", "Heading"),
        "level": props.get("level", "display"),
        "accent": props.get("accent"),
        "landmark": props.get("landmark"),
        "splitTwoLines": props.get("splitTwoLines"),
    }))
    if props.get("cta"):
        parts.append(render_arrow_link(doc, ctx, {
            "label": props["cta"], "accent": props.get("ctaAccent")}))
    return f'<div class="c-header">{"".join(parts)}</div>'


def render_paragraph(doc, ctx: ComponentContext, props=None) -> str:
    """paragraph primitive. props: text, measure (CSS max-width for the narrow column)."""
    props = props or {}
    style = f' style="--c-measure:{esc(props["measure"])}"' if props.get("measure") else ""
    return f'<p class="c-paragraph"{style}>{esc(props.get("text", ""))}</p>'


def render_caption(doc, ctx: ComponentContext, props=None) -> str:
    """caption primitive — margin micro-caption beside media, never over a photo."""
    props = props or {}
    return f'<p class="c-caption">{esc(props.get("text", ""))}</p>'


def render_stat(doc, ctx: ComponentContext, props=None) -> str:
    """stat primitive (contracts/primitives.yaml `stat`, alias `metric` — W4): one big
    metric VALUE + a muted supporting LABEL. The value rides the brand's measured h2
    register (via .c-stat-value's --c-stat-size/--c-h2-size chain), NEVER the eyebrow
    tier the generic caption fold produced, and never the display tier (reserved for
    the hero). props: value, label, prefix, suffix. An empty value elides the device
    (a value-less stat is no stat — nothing is invented)."""
    props = props or {}
    value = str(props.get("value") or "").strip()
    if not value:
        return ""
    prefix = str(props.get("prefix") or "").strip()
    suffix = str(props.get("suffix") or "").strip()
    label = str(props.get("label") or "").strip()
    label_html = f'<span class="c-stat-label">{esc(label)}</span>' if label else ""
    return (f'<div class="c-stat"><span class="c-stat-value">'
            f'{esc(prefix)}{esc(value)}{esc(suffix)}</span>{label_html}</div>')


def render_table(doc, ctx: ComponentContext, props=None) -> str:
    """table block (contracts/blocks.yaml `table` — W4): semantic tabular data —
    optional caption, header columns, ruled data rows (the .c-rows hairline
    discipline as a real <table>). props:
      caption: str (optional)
      columns: [str, …] (header cells; optional)
      rows: [[cell, …], …]  — each row a list of cells; the FIRST cell renders as the
            row header (<th scope="row"> on the label register). A row may also be a
            {label, value} dict (the comparison-rows shape) or a bare string.
    Rows with no cells are dropped; zero renderable rows elides the block."""
    props = props or {}
    rows_in = props.get("rows") or []
    rows: list[list[str]] = []
    for r in rows_in:
        if isinstance(r, dict):
            cells = [str(r.get("label") or "").strip(),
                     str(r.get("value") or r.get("text") or "").strip()]
        elif isinstance(r, (list, tuple)):
            cells = [str(c or "").strip() for c in r]
        else:
            cells = [str(r or "").strip()]
        cells = [c for c in cells if c] or []
        if cells:
            rows.append(cells)
    if not rows:
        return ""
    caption = str(props.get("caption") or "").strip()
    caption_html = f"<caption>{esc(caption)}</caption>" if caption else ""
    columns = [str(c or "").strip() for c in (props.get("columns") or []) if str(c or "").strip()]
    head_html = ""
    if columns:
        head_html = ("<thead><tr>"
                     + "".join(f'<th scope="col">{esc(c)}</th>' for c in columns)
                     + "</tr></thead>")
    body_rows = []
    for cells in rows:
        first, rest = cells[0], cells[1:]
        tds = "".join(f"<td>{esc(c)}</td>" for c in rest)
        body_rows.append(f'<tr><th scope="row">{esc(first)}</th>{tds}</tr>')
    comparison = bool(props.get("comparison")) or (
        not columns and all(len(cells) == 2 for cells in rows))
    table_cls = "c-table c-table--comparison" if comparison else "c-table"
    colgroup = ('<colgroup><col class="c-table-label-col"><col '
                'class="c-table-value-col"></colgroup>') if comparison else ""
    return (f'<div class="c-table-wrap"><table class="{table_cls}">{colgroup}'
            f'{caption_html}{head_html}<tbody>{"".join(body_rows)}</tbody></table></div>')


def input_shape(doc) -> str:
    """Structural-variant flag `input-shape` → 'underline' | 'boxed' (SPEC §C.3).

    Resolution: brand structure LAW first — `neverDo.no-boxed-inputs` forces the
    underline archetype; a brand that declares an input radius/background token
    (tokens.radius input entry or spacing radius-input) selects the boxed variant.
    Default stays underline (the current archetype) so token-less brands render
    unchanged. The variant *kind* is the flag; every magnitude the boxed variant
    consumes (--c-input-radius/-border/-bg) is a brand token."""
    nd = {d.get("id") for d in (doc.get("neverDo") or []) if isinstance(d, dict)}
    if "no-boxed-inputs" in nd:
        return "underline"
    tokens = (doc.get("tokens", {}) or {})
    radius = tokens.get("radius") or {}
    if isinstance(radius, dict) and any("input" in str(k).lower() for k in radius):
        return "boxed"
    if "radius-input" in (tokens.get("spacing") or {}):
        return "boxed"
    return "underline"


def _style_primary_action(style) -> str:
    """Duck-typed reader for the active style's `primaryAction` soft-option default
    ('filled'|'typographic'). Accepts the parsed style object (attr on it or on its
    .structure) or a bare string; '' when the style is silent/absent."""
    if isinstance(style, str):
        v = style.strip().lower()
        return v if v in ("filled", "typographic") else ""
    for obj in (style, getattr(style, "structure", None)):
        v = getattr(obj, "primary_action", "") if obj is not None else ""
        if v:
            v = str(v).strip().lower()
            if v in ("filled", "typographic"):
                return v
    return ""


def cta_shape(doc, style=None) -> str:
    """Structural-variant flag `cta-shape` → 'filled' | 'typographic' (SPEC §C.3;
    'outline' reserved until a brand carries it). Resolution order (B5 composer half,
    fix-batch 2026-07):
      1. brand structure LAW — `neverDo.never-typographic-primary` /
         buttons.renderHint.useFilledButton force filled; `primitives.button.use:
         never` forces typographic (WoodWave stays typographic under ANY style);
      2. the active STYLE's `primaryAction` soft-option default (front-matter) — a
         corporate archetype declares filled primaries, editorial archetypes declare
         typographic links;
      3. a measured buttons.primary token set implies filled;
      4. typographic (the legacy archetype default).
    The actual renderer choice flows through render_button's dispatch on this flag —
    a typographic brand cannot emit `.c-button` through the catalog."""
    nd = {d.get("id") for d in (doc.get("neverDo") or []) if isinstance(d, dict)}
    if "never-typographic-primary" in nd:
        return "filled"
    btns = (doc.get("tokens", {}) or {}).get("buttons") or doc.get("buttons") or {}
    if isinstance(btns, dict):
        if (btns.get("renderHint") or {}).get("useFilledButton"):
            return "filled"
    prims = doc.get("primitives")
    if isinstance(prims, dict):
        b = prims.get("button")
        if isinstance(b, dict) and str(b.get("use", "")).lower() == "never":
            return "typographic"
    style_default = _style_primary_action(style)
    if style_default:
        return style_default
    if isinstance(btns, dict) and btns.get("primary"):
        return "filled"
    return "typographic"


def render_input(doc, ctx: ComponentContext, props=None) -> str:
    """input primitive. TWO structural variants selected by ``input_shape(doc)``
    (SPEC §C.3): the underline FIELD (typographic, single 1px rule) or the BOXED
    field (border + brand input radius/background). props: placeholder, submit."""
    props = props or {}
    placeholder = esc(props.get("placeholder", "Your email"))
    submit = ""
    if props.get("submit"):
        # the inline submit follows the brand's resolved cta-shape (B5): a filled-CTA
        # brand's form action is its filled button, not a typographic downgrade.
        if (ctx.cta or cta_shape(doc)) == "filled":
            submit = render_button(doc, ctx, {"label": props.get("submit", "Subscribe")})
        else:
            submit = render_arrow_link(doc, ctx, {"label": props.get("submit", "Subscribe"),
                                                  "accent": ctx.is_dark})
    boxed = " c-field--boxed" if input_shape(doc) == "boxed" else ""
    # the field carries a REAL readonly control (interaction remediation 2026-07,
    # IC-FORM-01/03): the wrapping label owns it programmatically; the visible text
    # stays the placeholder, styled identically to the old display-only span.
    return (f'<label class="c-field{boxed}"><input class="c-field-input" type="text" '
            f'readonly placeholder="{placeholder}" aria-label="{placeholder}" />'
            f'{submit}</label>')


def render_form(doc, ctx: ComponentContext, props=None) -> str:
    """form block — composes an optional header + field(s) + inline submit from the
    catalog primitives. The field's underline/boxed KIND follows the brand's
    `input_shape` structural flag (SPEC §C.3); submit stays typographic."""
    props = props or {}
    parts = []
    if props.get("heading"):
        parts.append(render_header(doc, ctx, {
            "eyebrow": props.get("eyebrow"), "heading": props["heading"],
            "level": props.get("level", "h2"), "accent": props.get("accent")}))
    elif props.get("eyebrow"):
        parts.append(render_eyebrow(doc, ctx, {"text": props["eyebrow"]}))
    if props.get("note"):
        parts.append(render_paragraph(doc, ctx, {"text": props["note"]}))
    parts.append(render_input(doc, ctx, {
        "placeholder": props.get("placeholder", "Your email"),
        "submit": props.get("submit", "Subscribe")}))
    return f'<div class="c-form">{"".join(parts)}</div>'


def render_footer(doc, ctx: ComponentContext, props=None) -> str:
    """footer block (closing bookend). Composes the brand's footer slots from the shared
    typographic primitives: an oversized display SITEMAP (display-links grammar) or the
    extracted multi-column directory (columns grammar), a TEXT social row (no icons),
    and a centered muted legal line. Pulled from brand.yaml (blocks.footer slot notes +
    the extracted top-level footer); never a boxed/chromed footer. Sitemap/social rows
    are joined by the brand's DECLARED ``footer.separator`` glyph — brands without one
    get spacing only (nav-fix 2026-07: the glyph was a shared-code literal). props:
    sitemap[] OR columns[] ([{title, links: [{label, href}]}]), plus social[], legal.
    Surface comes from the caller (footer_surface_role), not assumed dark."""
    props = props or {}
    glyph = footer_separator(doc)
    sep = (f'<span class="c-foot-sep" aria-hidden="true">{esc(glyph)}</span>'
           if glyph else "")
    sitemap = props.get("sitemap") or []
    columns = props.get("columns") or []
    social = props.get("social") or []
    legal = props.get("legal") or ""
    parts = []
    # measured GROUP-HEADING register (fid4 2026-07): the directory headings render in
    # the brand's extracted heading facts via scoped vars; brands without measured
    # facts read the muted defaults baked into .c-foot-col-head.
    root_style = ""
    hs = props.get("headingStyle") or {}
    if isinstance(hs, dict) and hs:
        decls = []
        if hs.get("color"):
            decls.append(f"--cf-head-ink: {esc(str(hs['color']))}")
        if isinstance(hs.get("fontSize"), (int, float)):
            decls.append(f"--cf-head-size: {int(hs['fontSize'])}px")
        if hs.get("fontWeight"):
            decls.append(f"--cf-head-weight: {esc(str(hs['fontWeight']))}")
        if hs.get("textTransform"):
            decls.append(f"--cf-head-case: {esc(str(hs['textTransform']))}")
        if hs.get("letterSpacing"):
            decls.append(f"--cf-head-ls: {esc(str(hs['letterSpacing']))}")
        if isinstance(props.get("colGap"), int):
            decls.append(f"--cf-col-gap: {props['colGap']}px")
        if isinstance(props.get("cellGap"), int):
            decls.append(f"--cf-cell-gap: {props['cellGap']}px")
        if isinstance(props.get("colsMax"), int):
            decls.append(f"--cf-cols-max: {props['colsMax']}px")
        if isinstance(props.get("linkGap"), int):
            decls.append(f"--cf-link-gap: {props['linkGap']}px")
        if isinstance(props.get("bbGap"), int):
            decls.append(f"--cf-bb-gap: {props['bbGap']}px")
        if isinstance(props.get("bbAbove"), int):
            decls.append(f"--cf-bb-above: {props['bbAbove']}px")
        if decls:
            root_style = f' style="{"; ".join(decls)}"'
    if columns:
        def _group_html(col) -> str:
            links = col.get("links") if isinstance(col, dict) else col
            items = "".join(
                f'<a class="c-foot-col-link" href="{esc(l.get("href") or "#")}">{esc(l.get("label") or "")}</a>'
                for l in (links or []) if isinstance(l, dict) and l.get("label"))
            if not items:
                return ""
            head = (col.get("heading") or col.get("title") or "") if isinstance(col, dict) else ""
            if str(head).strip():
                head_html = f'<span class="c-foot-col-head">{esc(str(head))}</span>'
            elif _has_headed_col:
                # CONTINUATION column (a headed group's link list overflowing into a
                # second, headingless column): reserve the heading-row height so its
                # first link shares the link-start baseline with the headed columns —
                # otherwise it floats to y=0 above the others. aria-hidden spacer;
                # only when sibling columns ARE headed (fact-gated, byte-stable for
                # footers with no headed columns). fix 2026-07.
                head_html = ('<span class="c-foot-col-head c-foot-col-head--spacer" '
                             'aria-hidden="true">&nbsp;</span>')
            else:
                head_html = ""
            return f'<div class="c-foot-col">{head_html}{items}</div>'

        _has_headed_col = any(
            str((c.get("heading") or c.get("title") or "")).strip()
            for c in columns if isinstance(c, dict))
        groups = [_group_html(c) for c in columns]
        groups = [g for g in groups if g]
        cells = props.get("cells") or []
        if cells and sum(cells) == len(groups):
            # measured column→group hierarchy: each MAJOR column (cell) stacks its
            # captured groups in source order (e.g. two related groups sharing a track).
            cell_parts, i = [], 0
            for n in cells:
                cell_parts.append(f'<div class="c-foot-cell">{"".join(groups[i:i + n])}</div>')
                i += n
            parts.append(f'<nav class="c-foot-cols" aria-label="Sitemap">{"".join(cell_parts)}</nav>')
        elif groups:
            parts.append(f'<nav class="c-foot-cols" aria-label="Sitemap">{"".join(groups)}</nav>')
    elif sitemap:
        links = f" {sep} ".join(
            f'<a class="c-foot-sitemap-link" href="{esc(it.get("href", "#"))}">{esc(it.get("label", it))}</a>'
            if isinstance(it, dict) else
            f'<a class="c-foot-sitemap-link" href="#">{esc(it)}</a>'
            for it in sitemap)
        parts.append(f'<nav class="c-foot-sitemap" aria-label="Sitemap">{links}</nav>')
    # SOCIAL cluster: the brand's HARVESTED glyph artwork when every network resolved
    # an SVG (footer_content.socialGlyphs, fid4 2026-07; fix4 inline channel) — the
    # sanitized single-ink artwork nests INLINE in the link's measured box (ink rides
    # --cfg-ink through currentColor); unverified artwork keeps the fix2 mask degrade.
    # Otherwise the accessible TEXT row (icon artwork renders only from the brand's
    # own harvested assets, never invented).
    glyphs = props.get("socialGlyphs") or []
    social_html = ""
    if glyphs:
        items = []
        for s in glyphs:
            ic = s.get("icon") or {}
            box = s.get("box") or {}
            size = int(ic.get("size") or 20)
            ink = str(ic.get("ink") or "").strip() or "currentColor"
            w = int(box.get("width") or 0) or size * 2
            h = int(box.get("height") or 0) or w
            radius = box.get("radius")
            box_decls = [f"width:{w}px", f"height:{h}px"]
            if isinstance(radius, (int, float)) and radius > 0:
                box_decls.append(f"border-radius:{int(radius)}px")
            bg = _parse_color_rgba(box.get("bg"))
            if bg and bg[3] > 0.05:
                box_decls.append(f"background:{box.get('bg')}")
            net = str(s.get("network") or "link")
            if ic.get("_inlineSvg"):
                span_style = f"width:{size}px; height:{size}px; --cfg-ink:{esc(ink)}"
                inner = (f'<span class="c-foot-glyph-svg" style="{span_style}" '
                         f'aria-hidden="true">{_svg_instance(str(ic["_inlineSvg"]))}</span>')
            else:
                span_style = (f"width:{size}px; height:{size}px; --cfg-ink:{esc(ink)}; "
                              f"--cfg-mask:url('{ic.get('_dataUri')}')")
                inner = (f'<span class="c-foot-glyph-mask" style="{span_style}" '
                         f'aria-hidden="true"></span>')
            items.append(
                f'<a class="c-foot-glyph" style="{"; ".join(box_decls)}" '
                f'href="{esc(s.get("href") or "#")}" aria-label="{esc(net)}">'
                f'{inner}</a>')
        social_html = f'<nav class="c-foot-glyphs" aria-label="Social">{"".join(items)}</nav>'
    elif social:
        links = f" {sep} ".join(
            f'<a class="c-foot-social-link" href="{esc(it.get("href", "#"))}">{esc(it.get("label", it))}</a>'
            if isinstance(it, dict) else
            f'<a class="c-foot-social-link" href="#">{esc(it)}</a>'
            for it in social)
        social_html = f'<nav class="c-foot-social" aria-label="Social">{links}</nav>'
    legal_html = f'<p class="c-foot-legal">{esc(legal)}</p>' if legal else ""
    bb = props.get("bottomBar") if isinstance(props.get("bottomBar"), dict) else None
    if bb and str(bb.get("anatomy") or "").strip().lower() == "centered-stack":
        # CENTERED-STACK bottom bar (fix1 2026-07 item-11, footer.bottomBar.anatomy):
        # the measured column stack — social glyph row flanked by hairline rules on
        # the SAME row, then the brand wordmark, then the centered legal line, then
        # the policy-link row (hairline-separated). Everything centered; each row
        # renders only when its fact exists. Brands without the anatomy fact keep
        # the inline row1/row2 grammar below byte-identically.
        rows = []
        div = bb.get("divider") if isinstance(bb.get("divider"), dict) else {}
        rule_style = ""
        if div.get("present") and div.get("color"):
            rule_style = f' style="--cf-rule: {esc(str(div["color"]))}"'
        if social_html:
            rows.append(f'<div class="c-foot-cstack-social">{social_html}</div>')
        logo = props.get("footLogo") if isinstance(props.get("footLogo"), dict) else None
        if logo and logo.get("_dataUri"):
            # the wordmark redraws in the footer INK (the captured bottom stack shows
            # the same logo art in the light ink) — CSS mask over currentColor, sized
            # by the SVG's intrinsic aspect; artwork without a parsed viewBox degrades
            # to the raw <img> (its own fill) rather than a guessed recolor.
            aspect = logo.get("_aspect")
            lh = logo.get("height")
            h_px = int(lh) if isinstance(lh, (int, float)) and lh > 0 else 28
            if isinstance(aspect, (int, float)) and aspect > 0:
                rows.append(
                    f'<span class="c-foot-wordmark" role="img" '
                    f'aria-label="{esc(str(logo.get("alt") or ""))}" '
                    f'style="--cfw-mask:url(\'{logo["_dataUri"]}\'); '
                    f'height:{h_px}px; width:{int(round(h_px * aspect))}px"></span>')
            else:
                rows.append(
                    f'<img class="c-foot-wordmark" src="{esc(str(logo["_dataUri"]))}" '
                    f'alt="{esc(str(logo.get("alt") or ""))}" style="height:{h_px}px" />')
        if legal_html:
            rows.append(legal_html)
        pol_links = [l for l in (bb.get("policyLinks") or [])
                     if isinstance(l, dict) and l.get("label")]
        if pol_links:
            items = "".join(
                f'<a class="c-foot-policy-link" href="{esc(l.get("href") or "#")}">{esc(l["label"])}</a>'
                for l in pol_links)
            rows.append(f'<nav class="c-foot-policy" aria-label="Legal">{items}</nav>')
        parts.append(f'<div class="c-foot-cstack"{rule_style}>{"".join(rows)}</div>')
        return f'<div class="c-footer c-footer--cstack"{root_style}>{"".join(parts)}</div>'
    if bb:
        # MEASURED bottom-bar structure (fid4 2026-07, footer.bottomBar): row 1 =
        # copyright + small-print disclaimer (left stack) with the store-badge column
        # right; a full-width divider in the extracted color; row 2 = the bottom bar's
        # OWN policy links (centered) + the social cluster at the row end — the
        # captured row composition, not the legacy one-row bar.
        left = [legal_html]
        if str(bb.get("disclaimer") or "").strip():
            left.append(f'<p class="c-foot-disclaimer">{esc(str(bb["disclaimer"]))}</p>')
        badges = ""
        badge_items = []
        for b in bb.get("storeBadges") or []:
            img = b.get("img") if isinstance(b, dict) else None
            if isinstance(img, dict) and img.get("asset"):
                # inlined data: URI when prepare_chrome_glyphs resolved the artwork
                # (fid9: previews don't ship an assets/ tree, so the path-relative
                # ref would 404 there); the raw asset path stays the degrade for
                # lanes that DO ship assets beside the page.
                src = str(img.get("_dataUri") or img["asset"])
                badge_items.append(
                    f'<a href="{esc(b.get("href") or "#")}">'
                    f'<img src="{esc(src)}" alt="{esc(img.get("alt") or "")}" /></a>')
        if badge_items:
            badges = f'<div class="c-foot-badges">{"".join(badge_items)}</div>'
        row1 = (f'<div class="c-foot-bb-row1"><div class="c-foot-bb-left">'
                f'{"".join(p for p in left if p)}</div>{badges}</div>')
        div = bb.get("divider") if isinstance(bb.get("divider"), dict) else {}
        div_style = ""
        if div.get("color"):
            op = div.get("opacity")
            op_css = f"; opacity:{op}" if isinstance(op, (int, float)) and 0 < op < 1 else ""
            div_style = f' style="background:{esc(str(div["color"]))}{op_css}"'
        divider = f'<hr class="c-foot-divider"{div_style} />' if div.get("present") else ""
        policy = ""
        pol_links = [l for l in (bb.get("policyLinks") or [])
                     if isinstance(l, dict) and l.get("label")]
        if pol_links:
            items = "".join(
                f'<a class="c-foot-policy-link" href="{esc(l.get("href") or "#")}">{esc(l["label"])}</a>'
                for l in pol_links)
            policy = f'<nav class="c-foot-policy" aria-label="Legal">{items}</nav>'
        row2 = (f'<div class="c-foot-bb-row2">{policy}{social_html}</div>'
                if policy or social_html else "")
        parts.append(f'<div class="c-foot-bb">{row1}{divider}{row2}</div>')
        return f'<div class="c-footer"{root_style}>{"".join(parts)}</div>'
    # policy links (the extracted footer.legal.links — Security/Privacy/Terms …)
    # ride the bottom bar as small muted links, per the measured bottom-bar grammar.
    legal_links = props.get("legalLinks") or []
    legal_links_html = ""
    if legal_links:
        items = "".join(
            f'<a class="c-foot-policy-link" href="{esc(l.get("href") or "#")}">{esc(l.get("label") or "")}</a>'
            for l in legal_links if isinstance(l, dict) and l.get("label"))
        if items:
            legal_links_html = f'<nav class="c-foot-policy" aria-label="Legal">{items}</nav>'
    # BOTTOM BAR (fid2 2026-07, evidence: the extracted footer's bottom bar carries the
    # legal line + policy links + the social cluster on ONE row): when a legal line and
    # social links coexist they compose as one `.c-foot-bar` row — accessible TEXT links
    # for social (icon artwork renders only from the brand's own tagged assets; none
    # captured ⇒ text, never invented glyphs). Brands with only one of the two keep the
    # stacked rows unchanged.
    if social_html and (legal_html or legal_links_html):
        parts.append(f'<div class="c-foot-bar">{legal_html}{legal_links_html}{social_html}</div>')
    else:
        if social_html:
            parts.append(social_html)
        if legal_links_html:
            parts.append(legal_links_html)
        if legal_html:
            parts.append(legal_html)
    return f'<div class="c-footer"{root_style}>{"".join(parts)}</div>'


def _render_action_row(doc, ctx: ComponentContext, actions) -> str:
    """A `.c-actions` row from a list of action props ({label, href, kind?}) — each
    action dispatches through render_button's law-first cta-shape (a filled brand gets
    its pill, a typographic brand the arrow link); `kind: "link"` forces the
    typographic arrow device (e.g. a card's measured text-link action). Label-less
    entries elide (render_arrow_link's empty-label rule). "" when nothing renders."""
    frags = []
    for a in actions or []:
        if isinstance(a, str):
            a = {"label": a}
        if not isinstance(a, dict) or not str(a.get("label") or "").strip():
            continue
        renderer = render_arrow_link if str(a.get("kind") or "").lower() == "link" \
            else render_button
        frags.append(renderer(doc, ctx, {"label": a["label"],
                                         "href": a.get("href", "#"),
                                         "accent": a.get("accent", False)}))
    frags = [f for f in frags if f]
    return f'<div class="c-actions">{"".join(frags)}</div>' if frags else ""


def render_content_block(doc, ctx: ComponentContext, props=None) -> str:
    """content-block block — the brand's eyebrow → heading → body → actions stack
    (blocks.content-block slot grammar), composed ENTIRELY from the shared primitives
    (sysfix 2026-07: this contract had no shared renderer — composed sections emitted
    an unresolved-slot comment and the gallery a photo stub). Only slots the caller
    passes render (optional slots elide; nothing is invented): props: eyebrow,
    heading, level (default h2), body, actions [{label, href, kind?}] or cta str."""
    props = props or {}
    parts = []
    if props.get("eyebrow"):
        parts.append(render_eyebrow(doc, ctx, {"text": props["eyebrow"]}))
    parts.append(render_heading(doc, ctx, {
        "text": props.get("heading", "Heading"), "level": props.get("level", "h2"),
        "accent": props.get("accent")}))
    if props.get("body"):
        parts.append(render_paragraph(doc, ctx, {"text": props["body"],
                                                 "measure": props.get("measure", "52ch")}))
    actions = props.get("actions") or ([{"label": props["cta"]}] if props.get("cta") else [])
    row = _render_action_row(doc, ctx, actions)
    if row:
        parts.append(row)
    return f'<div class="c-content-block">{"".join(parts)}</div>'


def render_card(doc, ctx: ComponentContext, props=None) -> str:
    """card block — a bounded content unit per the brand's ``blocks.card`` anatomy
    (sysfix 2026-07: previously renderer-less). Slot grammar (media? → eyebrow? →
    heading → body? → action?) follows blocks.card.slots; the INSET media well renders
    only when the caller binds media AND the brand's card anatomy declares a media
    slot (a media-less card grammar can't inherit one). The action defaults to the
    typographic arrow link (kind: "link") — the measured card-action grammar — unless
    the caller passes kind: "button". props: media {src, alt, aspect} | True (srcless
    well), eyebrow, heading, level (default h3), body, action {label, href, kind?} or
    cta str."""
    props = props or {}
    parts = []
    card_slots = (block_device(doc, "card") or {}).get("slots") or {}
    media = props.get("media")
    if media and ("media" in card_slots or not card_slots):
        mprops = dict(media) if isinstance(media, dict) else {}
        mprops.setdefault("placeholder", "MEDIA")
        aspect = mprops.pop("aspectRatio", None) or mprops.get("aspect")
        style = f' style="aspect-ratio: {esc(str(aspect))}"' if aspect else ""
        mprops.pop("aspect", None)
        parts.append(f'<div class="c-card-media"{style}>'
                     f'{render_image(doc, ctx, mprops)}</div>')
    body_parts = []
    if props.get("eyebrow"):
        body_parts.append(render_eyebrow(doc, ctx, {"text": props["eyebrow"]}))
    body_parts.append(render_heading(doc, ctx, {
        "text": props.get("heading", "Heading"), "level": props.get("level", "h3")}))
    if props.get("body"):
        body_parts.append(render_paragraph(doc, ctx, {"text": props["body"],
                                                      "measure": props.get("measure", "44ch")}))
    action = props.get("action") or ({"label": props["cta"]} if props.get("cta") else None)
    if action:
        if isinstance(action, str):
            action = {"label": action}
        action.setdefault("kind", "link")
        row = _render_action_row(doc, ctx, [action])
        if row:
            body_parts.append(row)
    parts.append(f'<div class="c-card-body">{"".join(body_parts)}</div>')
    return f'<article class="c-card">{"".join(parts)}</article>'


def render_navbar(doc, ctx: ComponentContext, props=None) -> str:
    """navbar block - zero-chrome: logo + links + a single trailing cta. Composes the
    logo + action primitives.

    The logo is either the extracted IMAGE (when props["logo"] is a dict carrying an
    `img`/`src`, e.g. the composed nav) or the text wordmark (props["wordmark"]). Links
    may be plain strings OR {label, href} dicts (the extracted navbar.primary), so real
    hrefs survive. PRESENTATION IS BRAND EVIDENCE (nav-fix 2026-07): the inter-link
    separator glyph is the brand's declared ``navbar.separator`` (none → spacing only);
    link casing rides the brand's case token on `.c-arrow-link`; the CTA dispatches
    through render_button's law-first cta-shape (a filled-primary brand gets its pill,
    a typographic brand keeps the ink arrow link — accent stays reserved unless the
    caller opts in via ctaAccent=True)."""
    props = props or {}
    logo_props = props.get("logo")
    if isinstance(logo_props, dict):
        logo = render_logo(doc, ctx, logo_props)
    else:
        logo = render_logo(doc, ctx, {"text": props.get("wordmark", "Brand")})
    links = props.get("links") or []
    # vocabulary-prefixed separator class (cs-*) so the composition primitive-only
    # invariant sees only c-*/cs-* classes; emitted only for a DECLARED brand glyph.
    glyph = nav_separator(doc)
    sep = f' <span class="cs-sep">{esc(glyph)}</span> ' if glyph else " "
    # dropdown-trigger chevron (fid15): the family fact renders on EVERY menu-owning
    # trigger — bar anatomy visible at rest, so the gallery bar demo carries it too
    # (unlike the hover panels, which stay page-level). Unresolved artwork ⇒ "".
    # The shared artwork rides the .cs-nav-chev class default (no per-span override).
    trig_chev = _nav_chev_span(_nav_trigger_chevron(doc), _nav_chevron_uri(doc))

    def _link(n, idx=0):
        if isinstance(n, dict):
            menu = n.get("menu")
            has_menu = isinstance(menu, dict) and (menu.get("columns") or menu.get("card"))
            chev = trig_chev if has_menu else ""
            # chrome mega-menu (fid4 2026-07): the page-level nav (ctx.mega_nav) wraps a
            # primary item that OWNS a captured menu in a hover/focus tab carrying the
            # measured panel. Gallery navbars and menu-less brands emit the bare link.
            if has_menu and getattr(ctx, "mega_nav", False):
                # interaction remediation (2026-07, IC-NAV-01/02/04): a menu-owning
                # trigger whose capture carries no real destination is a disclosure
                # control, not a link — render the APG-shaped <button> (aria-expanded
                # + aria-controls; interaction_script drives state/Escape; the CSS
                # hover path still works with JS off). A captured REAL href keeps the
                # link element (its panel opens on hover/focus-within) but still
                # carries the disclosure state attributes.
                panel_id = f"cs-mega-{idx + 1}"
                href = str(n.get("href") or "").strip()
                state = f'aria-expanded="false" aria-controls="{panel_id}"'
                if href in ("", "#"):
                    trigger = (f'<button type="button" class="c-arrow-link cs-nav-trigger" '
                               f'{state} style="gap:0">{esc(n.get("label", ""))}{chev}</button>')
                else:
                    trigger = (f'<a class="c-arrow-link cs-nav-trigger" href="{esc(href)}" '
                               f'{state} style="gap:0">{esc(n.get("label", ""))}{chev}</a>')
                return (f'<span class="cs-nav-tab">{trigger}'
                        f'{_mega_panel_fragment(menu, panel_id)}</span>')
            return (f'<a class="c-arrow-link" href="{esc(n.get("href", "#"))}" '
                    f'style="gap:0">{esc(n.get("label", ""))}{chev}</a>')
        return f'<a class="c-arrow-link" href="#" style="gap:0">{esc(n)}</a>'

    navlinks = sep.join(_link(n, i) for i, n in enumerate(links))

    def _measured_action(label: str, href: str, facts: dict,
                         accessible_name: str = "") -> str:
        """One bar action drawn from its own MEASURED register facts via the scoped
        navcta consumption vars (the fid2 device, extended fix1 item-12b with the
        border channel so an outlined secondary register renders its captured
        stroke — the var defaults keep existing single-cta brands byte-identical)."""
        decls = [f"--navcta-bg: {esc(str(facts['bg']))}"]
        # SAFE INK: when the measured fg wasn't captured, never fall back to the
        # CSS `#fff` default — a white/light-bg CTA (an unfilled "Get started free")
        # then rendered white-on-white at idle AND on hover. Derive the ink from the
        # bg luminance: dark fill → white, light/transparent fill → the brand accent
        # (the conventional text/outline-CTA ink). (product-launch nav CTAs, 2026-07)
        ink = facts.get("color")
        if not ink:
            _bg = str(facts.get("bg") or "").strip().lower()
            _rgb = re.search(r"(\d+)\D+(\d+)\D+(\d+)", _bg)
            _hex = re.match(r"^#([0-9a-f]{6})$", _bg)
            if _rgb:
                _dark = sum(int(_rgb.group(i)) for i in (1, 2, 3)) < 384
            elif _hex:
                _dark = sum(int(_hex.group(1)[i:i+2], 16) for i in (0, 2, 4)) < 384
            else:
                _dark = not _bg.startswith(("#fff", "rgb(255", "white", "transparent"))
            ink = "#ffffff" if _dark else "var(--c-accent)"
        decls.append(f"--navcta-ink: {esc(str(ink))}")
        if facts.get("border"):
            decls.append(f"--navcta-border: {esc(str(facts['border']))}")
        if facts.get("radius") is not None:
            decls.append(f"--navcta-radius: {_px(facts['radius'])}")
        if facts.get("height"):
            decls.append(f"--navcta-height: {_px(facts['height'])}")
        if facts.get("padX") is not None:
            decls.append(f"--navcta-pad-x: {_px(facts['padX'])}")
        if facts.get("fontSize"):
            decls.append(f"--navcta-size: {_px(facts['fontSize'])}")
        aria = (f' aria-label="{esc(accessible_name)}"'
                if accessible_name and accessible_name != label else "")
        return (f'<a class="c-button c-button--navcta" role="button"{aria} '
                f'style="{"; ".join(decls)}" href="{esc(href or "#")}">'
                f'{esc(label)}</a>')

    # in-bar utility cluster (fid15): captured trailing controls (login link,
    # locale dropdown) between the primary links and the CTA — "" for brands
    # whose extraction carries none.
    utility = _nav_utility_fragment(doc)
    cta = ""
    actions = [a for a in (props.get("actions") or [])
               if isinstance(a, dict) and str(a.get("label") or "").strip()]
    if actions:
        # ACTION GROUP (fix1 2026-07 item-12b): the bar's captured N-action run —
        # every action renders its own measured register (feeds AS-59: one primary,
        # the rest the brand's secondary/ghost/link registers). Brands whose
        # evidence declares a single cta never build this list (degrade below).
        frags = []
        for a in actions:
            st = a.get("style") if isinstance(a.get("style"), dict) else {}
            if st.get("bg"):
                frags.append(_measured_action(str(a["label"]),
                                              str(a.get("href") or "#"), st,
                                              str(a.get("ariaLabel")
                                                  or a.get("accessibleName") or "")))
            else:
                frags.append(render_button(doc, ctx, {
                    "label": a["label"], "href": a.get("href", "#"),
                    "ariaLabel": a.get("ariaLabel") or a.get("accessibleName"),
                    "accent": False}))
        cta = f'<span class="cs-nav-actions">{"".join(frags)}</span>'
    elif props.get("cta"):
        # MEASURED chrome-CTA facts win (fid2 2026-07): when the extraction carries the
        # nav CTA's own computed styles (navbar.ctas[0] + navbar.measured.cta — e.g. a
        # neutral filled pill distinct from the page's accent primary), the nav renders
        # THOSE facts via scoped vars instead of dispatching into the button-primary
        # family. Brands without measured chrome-CTA facts keep the law-first dispatch.
        facts = props.get("ctaStyle") if isinstance(props.get("ctaStyle"), dict) else {}
        if facts.get("bg"):
            decls = [f"--navcta-bg: {esc(str(facts['bg']))}"]
            if facts.get("color"):
                decls.append(f"--navcta-ink: {esc(str(facts['color']))}")
            if facts.get("radius") is not None:
                decls.append(f"--navcta-radius: {_px(facts['radius'])}")
            if facts.get("height"):
                decls.append(f"--navcta-height: {_px(facts['height'])}")
            if facts.get("padX") is not None:
                decls.append(f"--navcta-pad-x: {_px(facts['padX'])}")
            if facts.get("fontSize"):
                decls.append(f"--navcta-size: {_px(facts['fontSize'])}")
            accessible = str(props.get("ctaAriaLabel") or "").strip()
            aria = (f' aria-label="{esc(accessible)}"'
                    if accessible and accessible != str(props["cta"]) else "")
            cta = (f'<a class="c-button c-button--navcta" role="button"{aria} '
                   f'style="{"; ".join(decls)}" href="{esc(props.get("ctaHref", "#"))}">'
                   f'{esc(props["cta"])}</a>')
        else:
            cta = render_button(doc, ctx, {
                "label": props["cta"], "href": props.get("ctaHref", "#"),
                "ariaLabel": props.get("ctaAriaLabel"),
                "accent": props.get("ctaAccent", False)})
    # TWO-TIER bar (fix1 2026-07 item-12a/c): gated on the EXPLICIT opt-in
    # `navbar.utilityTier` contract — never on `twoTier` alone (a brand can
    # declare twoTier with a measured utilityBarHeight of 0; its bar stays
    # single-tier byte-identically). The captured utility run splits into the
    # leading cluster (source order) and the trailing cluster (the contract's
    # `trailing` placement labels, in declared order) — both render through the
    # same fid15 utility device. The primary tier keeps the logo + links + action
    # markup EXACTLY as the single bar (mega bindings/triggers unchanged).
    nav = (doc or {}).get("navbar") or {}
    tier = nav.get("utilityTier") if isinstance(nav.get("utilityTier"), dict) else None
    if tier:
        trailing_labels = [str(t).strip().lower() for t in (tier.get("trailing") or [])]
        every = _nav_utility(doc)
        trail_items = sorted(
            [u for u in every
             if str(u.get("label") or "").strip().lower() in trailing_labels],
            key=lambda u: trailing_labels.index(str(u.get("label") or "").strip().lower()))
        lead_items = [u for u in every if u not in trail_items]
        lead = _nav_utility_fragment(doc, lead_items)
        trail = _nav_utility_fragment(doc, trail_items)
        decls = []
        if isinstance(tier.get("height"), (int, float)) and tier["height"] > 0:
            decls.append(f"--cs-utier-h: {int(tier['height'])}px")
        if tier.get("bg"):
            decls.append(f"--cs-utier-bg: {esc(str(tier['bg']))}")
        if isinstance(tier.get("fontSize"), (int, float)) and tier["fontSize"] > 0:
            decls.append(f"--cs-utier-size: {int(tier['fontSize'])}px")
        ph = (nav.get("measured") or {}).get("primaryBarHeight") \
            if isinstance(nav.get("measured"), dict) else None
        if isinstance(ph, (int, float)) and ph > 0:
            decls.append(f"--cs-ptier-h: {int(ph)}px")
        style = f' style="{"; ".join(decls)}"' if decls else ""
        return (f'<nav class="cs-nav cs-nav--twotier"{style}>'
                f'<div class="cs-nav-tier cs-nav-tier--utility">{lead}{trail}</div>'
                f'<div class="cs-nav-tier cs-nav-tier--primary">{logo}'
                f'<span class="cs-navlinks">{navlinks}</span>{cta}</div></nav>')
    return (f'<nav class="cs-nav">{logo}'
            f'<span class="cs-navlinks">{navlinks}</span>{utility}{cta}</nav>')


# ── registry: catalog contract -> shared renderer ───────────────────────────────

PRIMITIVE_RENDERERS = {
    "heading": render_heading,
    "eyebrow": render_eyebrow,
    "image": render_image,
    "link": render_arrow_link,
    "cta": render_arrow_link,
    "logo": render_logo,
    "button": render_button,
    "paragraph": render_paragraph,
    "caption": render_caption,
    "input": render_input,
    # W4 (stress-playbook 2026-07): the `stat` contract existed in primitives.yaml
    # with no renderer — values fell through the generic caption fold and rendered
    # at the eyebrow register. `metric` is the contract's declared alias.
    "stat": render_stat,
    "metric": render_stat,
}

BLOCK_RENDERERS = {
    "header": render_header,
    "navbar": render_navbar,
    "form": render_form,
    "footer": render_footer,
    # sysfix 2026-07: real card / content-block anatomy renderers (previously the
    # composed path emitted an unresolved-slot comment for these contracts).
    "card": render_card,
    "content-block": render_content_block,
    # W4 (stress-playbook 2026-07): blocks.yaml declared `table` with no renderer —
    # comparison content had to be faked through panel label/value rows.
    "table": render_table,
}


def resolve_renderer(contract: str):
    """Resolve a catalog contract key (from a layout's blockMapping) to its shared
    renderer. Returns None when no shared renderer exists yet (caller may fall back)."""
    return PRIMITIVE_RENDERERS.get(contract) or BLOCK_RENDERERS.get(contract)
