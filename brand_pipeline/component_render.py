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
    muted = _color_ref(doc, "text/on-inverse-muted" if surf.get("textAccent")
                       else "text/on-primary-muted") or text

    # the brand's single ruled-line hairline (underline fields + ruled action rows):
    # SURFACE-AWARE (a dark surface prefers a dedicated "-on-inverse" token; else falls
    # back to `muted`, which is already resolved per-surface above). Token EXISTENCE is
    # checked directly — color_value()'s pass-through-on-missing return is truthy (the
    # AS-02 invisible-hairline trap this block previously documented at length).
    _hairline_tok = "border/hairline-on-inverse" if surf.get("textAccent") else "border/hairline-on-primary"
    hairline = f"var(--color-{_slug(_hairline_tok)})" if _hairline_tok in colors else muted
    # PER-SURFACE link-hover (anti-ai-slop.md AS-10/AS-20): the measured hover color was
    # measured on a DARK surface — it applies ONLY on dark/textAccent-bearing surfaces
    # (incl. re-scoping panels/cards); every light surface hovers in its own ink.
    link_hover = ("var(--chrome-link-hover)"
                  if (surf.get("textAccent") and link_hover_color(doc)) else text)
    # BRAND LINK TOKENS win when carried (sysfix 2026-07): a brand with an authored
    # text/link(+hover) pair binds its typographic-action color per surface — idle
    # `--c-action-color` + hover `--c-link-hover` — from ITS OWN tokens (the on-inverse
    # twins on dark surfaces). Token-less brands keep the resolutions above unchanged.
    _link_tok, _link_hover_tok = (("text/link-on-inverse", "text/link-hover-on-inverse")
                                  if surf.get("textAccent")
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
  --c-h2-size: {_size_ref(doc, 'h2', 2.25)};
  --c-h3-size: {_size_ref(doc, 'h3', 1.625)};
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
  --c-title-overlap: {css_len(title_overlap, '-2.75rem')};{aspect_css}{btn_css}{input_css}{foot_css}
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
.c-heading--h2 { font-size: var(--c-h2-size); line-height: 1.3em; }
.c-heading--h3 { font-size: var(--c-h3-size); line-height: 1.3em; }
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
  color: var(--c-ink-muted); margin: 0; }

.c-image { display: block; width: 100%; border: none; box-shadow: none;
  border-radius: var(--radius); object-fit: cover;
  /* PLACEHOLDER BACKING (anti-ai-slop AS-23): every image slot carries a diagonal-hatch
     plate DERIVED FROM THE SURFACE'S OWN TOKENS (never a hardcoded hex at this level —
     AS-01). Visible while the photo loads, on a broken src, or wherever cover-fit leaves
     the frame unpainted; re-scopes per surface automatically because it reads --c-ink/
     --c-paper. PAPER-dominant mixes (the plate is the surface, gently lifted toward its ink):
     on a dark hero surface this resolves to a matching dark hatch pair, on a light
     canvas to a pale one. */
  background: repeating-linear-gradient(135deg,
    var(--c-paper) 0px,
    var(--c-paper) 13px,
    color-mix(in srgb, var(--c-paper) 93%, var(--c-ink)) 13px,
    color-mix(in srgb, var(--c-paper) 93%, var(--c-ink)) 26px); }
/* hero-collage occlusion geometry: this exact base/overlap crop PAIR is what makes the
   layered collage device read (the spacer clearance math + depth parallax derive from
   it — see .cs-spacer + parallax_css docstrings). Compositions that declare mediaAspect
   override it inline per §4.6.5; brands without the collage device never render these
   classes. */
.c-image--hero { /* provenance: structural — collage occlusion geometry */
  aspect-ratio: 1355 / 570; }
.c-image--overlap { /* provenance: structural — collage occlusion geometry */
  aspect-ratio: 785 / 620; }
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
  gap: 0.5rem; background: none; border: none; cursor: pointer; padding: 0; }
.c-arrow-link--accent { color: var(--c-accent); }
/* CHROME register pin (sysfix 2026-07): NAV links are chrome, not in-flow text
   actions — they read the surface ink (their measured --chrome-* registers own any
   deviation), never the page's typographic-action color (--c-action-color). */
.cs-navlinks .c-arrow-link { color: currentColor; }

.c-arrow { transition: transform var(--c-motion-fast) var(--c-ease); }
.c-arrow-link:hover .c-arrow { transform: translateX(0.35rem); }

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
  line-height: 1.55em; color: var(--c-ink-muted); max-width: var(--c-measure, 34ch); margin: 0; }

/* caption primitive: muted uppercase margin micro-text (never over media). */
.c-caption { font-family: var(--c-font-body); font-size: var(--c-eyebrow-size);
  letter-spacing: var(--c-eyebrow-ls); text-transform: var(--c-case-eyebrow);
  color: var(--c-ink-muted); margin: 0; }

/* form block + underline field: NO box, NO fill, NO border — the single 1px rule is a
   pseudo-element (height:1px+background), so it never reads as a boxed input or a section
   hairline (honors a no-boxed-inputs / no-section-hairlines neverDo). */
.c-form { display: flex; flex-direction: column; gap: var(--c-form-gap, 1.25rem); }
.c-field { position: relative; display: flex; align-items: flex-end; justify-content: space-between;
  gap: 1rem; padding-bottom: 0.5rem; }
.c-field::after { content: ""; position: absolute; left: 0; right: 0; bottom: 0; height: 1px;
  background: var(--c-hairline); }
.c-field-text { font-family: var(--c-font-body); font-size: var(--c-body-size);
  text-transform: var(--c-case-control); letter-spacing: var(--c-control-ls);
  color: var(--c-ink-muted); }

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
.c-foot-cols { display: flex; flex-wrap: wrap; justify-content: center; text-align: left;
  gap: var(--c-block-gap, 2.5rem) clamp(2rem, 5cqw, 4rem); max-width: 72rem; margin: 0 auto; }
.c-foot-col { display: flex; flex-direction: column; gap: 0.6em;
  flex: 1 1 10rem; min-width: 10rem; max-width: 16rem; }
.c-foot-col-link { font-family: var(--c-font-body);
  font-size: var(--c-foot-link-size, var(--c-control-size));
  font-weight: var(--c-foot-link-weight, var(--c-body-weight));
  color: var(--c-ink-muted); text-decoration: none; line-height: 1.6em; }
.c-foot-col-link:hover, .c-foot-col-link:focus-visible { color: var(--c-link-hover); }
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


def footer_grammar(doc) -> str:
    """Structural-variant flag `footer-grammar` → 'display-links' | 'columns'.

    Resolution mirrors input_shape/cta_shape: the brand's own extracted facts pick the
    grammar. A type-scale footer display tier (e.g. a measured footer-sitemap-link
    register) selects the oversized display-links device; an extracted multi-column
    footer (footer.columns) selects the measured directory. Brands carrying neither
    keep display-links — the legacy bookend default — so existing renders are stable."""
    types = (doc.get("tokens", {}) or {}).get("type", {}) or {}
    keys = set(types.keys()) if isinstance(types, dict) else set()
    scale = types.get("scale") if isinstance(types, dict) else None
    if isinstance(scale, dict):  # families+scale shape (flat role keys covered above)
        keys |= set(scale.keys())
    if any("footer" in str(k).lower() for k in keys):
        return "display-links"
    cols = (doc.get("footer") or {}).get("columns")
    if isinstance(cols, list) and cols:
        return "columns"
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
    if footer_grammar(doc) == "columns":
        return {"columns": foot.get("columns") or [], "social": social, "legal": legal}
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
    return {"sitemap": sitemap, "social": social, "legal": legal}


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
        canon = {"outlined": "outline", "ghosted": "ghost"}
        return {canon.get(w, w)
                for w in str(text or "").lower().replace("-", " ").split()}

    words = _norm(hint)
    if not words:
        return None
    for name, facts in _button_families(doc).items():
        if _norm(facts.get("style")) & words & {"outline", "ghost", "quiet", "neutral"}:
            return name
    return None


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


def structural_variant_css(doc, include_all: bool = False) -> str:
    """The §C.3 variant rules THIS brand's structural flags select (appended after
    COMPONENT_CSS by both composers). ``include_all=True`` is the gallery/harness mode:
    the gallery renders prohibited variants as labeled specimens, so it carries every
    variant's CSS regardless of the brand's flags."""
    parts = []
    if include_all or cta_shape(doc) == "filled":
        parts.append(_BUTTON_VARIANT_CSS)
        parts.append(_button_family_override_css(doc))
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
    return "".join(parts)


# ── per-component renderers (SINGLE SOURCE OF TRUTH) ─────────────────────────────

def _level_class(level):
    lv = str(level or "display").lower()
    if lv in ("display", "h0", "h1", "hero"):
        return "c-heading--display"
    if lv == "h2":
        return "c-heading--h2"
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
        parts = str(text).split(" ")
        if len(parts) >= 2:
            inner = f"{esc(parts[0])}<br>{esc(' '.join(parts[1:]))}"
    return f'<{tag} class="c-heading {_level_class(level)}{accent}">{inner}</{tag}>'


def render_eyebrow(doc, ctx: ComponentContext, props=None) -> str:
    props = props or {}
    return f'<p class="c-eyebrow">{esc(props.get("text", "Eyebrow"))}</p>'


def render_image(doc, ctx: ComponentContext, props=None) -> str:
    """image primitive. props: src, alt, variant (hero|overlap), absolute (bool),
    aspect (a declared CSS aspect-ratio value, e.g. "21 / 9" — the composition contract's
    mediaAspect resolved by the adapter; wins over the variant's intrinsic ratio).
    With no src it renders the gallery placeholder (radius 0, no chrome)."""
    props = props or {}
    variant = props.get("variant", "")
    mod = f" c-image--{variant}" if variant in ("hero", "overlap") else ""
    aspect = props.get("aspect")
    style = f' style="aspect-ratio: {esc(str(aspect))}"' if aspect else ""
    src = props.get("src")
    alt = esc(props.get("alt", ""))
    if not src:
        return f'<div class="c-image-ph{mod}"{style}>{esc(props.get("placeholder", "IMAGE / RADIUS 0"))}</div>'
    abs_cls = " is-abs" if props.get("absolute") else ""
    return f'<img class="c-image{mod}{abs_cls}"{style} src="{esc(src)}" alt="{alt}">'


def render_arrow_link(doc, ctx: ComponentContext, props=None) -> str:
    """link primitive == cta role (WoodWave remaps cta -> arrow link, never a button).
    props: label, href, accent. Always a typographic <a>, NEVER a <button>.
    An EXPLICITLY EMPTY label elides the device (sysfix 2026-07): a label-less action
    is no action — the adapter no longer invents "Learn more"-style fallback copy, so
    a copy-less slot must not render a bare floating arrow glyph. The "Learn more"
    default still applies only when the caller passes no label key at all (harness
    specimen shorthand)."""
    props = props or {}
    label = props.get("label", "Learn more")
    if not str(label or "").strip():
        return ""
    accent = " c-arrow-link--accent" if props.get("accent") else ""
    href = esc(props.get("href", "#"))
    return (f'<a class="c-arrow-link{accent}" href="{href}">{esc(label)} '
            f'<span class="c-arrow" aria-hidden="true">&rarr;</span></a>')


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
    return (f'<a class="c-button{fam_cls}" href="{href}" role="button">'
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
    return (f'<label class="c-field{boxed}"><span class="c-field-text">{placeholder}</span>'
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
    if columns:
        col_parts = []
        for col in columns:
            links = col.get("links") if isinstance(col, dict) else col
            items = "".join(
                f'<a class="c-foot-col-link" href="{esc(l.get("href") or "#")}">{esc(l.get("label") or "")}</a>'
                for l in (links or []) if isinstance(l, dict) and l.get("label"))
            if items:
                col_parts.append(f'<div class="c-foot-col">{items}</div>')
        if col_parts:
            parts.append(f'<nav class="c-foot-cols" aria-label="Sitemap">{"".join(col_parts)}</nav>')
    elif sitemap:
        links = f" {sep} ".join(
            f'<a class="c-foot-sitemap-link" href="{esc(it.get("href", "#"))}">{esc(it.get("label", it))}</a>'
            if isinstance(it, dict) else
            f'<a class="c-foot-sitemap-link" href="#">{esc(it)}</a>'
            for it in sitemap)
        parts.append(f'<nav class="c-foot-sitemap" aria-label="Sitemap">{links}</nav>')
    if social:
        links = f" {sep} ".join(
            f'<a class="c-foot-social-link" href="{esc(it.get("href", "#"))}">{esc(it.get("label", it))}</a>'
            if isinstance(it, dict) else
            f'<a class="c-foot-social-link" href="#">{esc(it)}</a>'
            for it in social)
        parts.append(f'<nav class="c-foot-social" aria-label="Social">{links}</nav>')
    if legal:
        parts.append(f'<p class="c-foot-legal">{esc(legal)}</p>')
    return f'<div class="c-footer">{"".join(parts)}</div>'


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

    def _link(n):
        if isinstance(n, dict):
            return (f'<a class="c-arrow-link" href="{esc(n.get("href", "#"))}" '
                    f'style="gap:0">{esc(n.get("label", ""))}</a>')
        return f'<a class="c-arrow-link" href="#" style="gap:0">{esc(n)}</a>'

    navlinks = sep.join(_link(n) for n in links)
    cta = ""
    if props.get("cta"):
        cta = render_button(doc, ctx, {
            "label": props["cta"], "href": props.get("ctaHref", "#"),
            "accent": props.get("ctaAccent", False)})
    return (f'<nav class="cs-nav">{logo}'
            f'<span class="cs-navlinks">{navlinks}</span>{cta}</nav>')


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
}


def resolve_renderer(contract: str):
    """Resolve a catalog contract key (from a layout's blockMapping) to its shared
    renderer. Returns None when no shared renderer exists yet (caller may fall back)."""
    return PRIMITIVE_RENDERERS.get(contract) or BLOCK_RENDERERS.get(contract)
