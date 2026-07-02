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

Token resolution reuses the faithful helpers in render_section.py (imported, never
modified) so every value is the brand's real token.
"""
from __future__ import annotations

import html
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Reuse the canonical token resolvers from render_section.py (same package dir).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_section import (  # noqa: E402
    base_size,
    color_value,
    css_len,
    font_stack,
    spacing_value,
    type_role,
)


def esc(value) -> str:
    return html.escape(str(value if value is not None else ""))


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


def make_context(doc, surface_role, surf) -> ComponentContext:
    is_dark = surface_role in (
        "surface/inverse", "surface/inverse-strong", "surface/accent", "surface/overlay")
    # collect the google-font proxies the brand fonts need (so the caller can <link> them)
    proxies = set()
    for role in ("display-hero", "body", "eyebrow", "control-text"):
        _, p = font_stack(doc, role)
        proxies |= p
    return ComponentContext(surface_role=surface_role, is_dark=is_dark, proxies=proxies)


# ── shared per-surface CSS variables (token VALUES) ──────────────────────────────

def component_vars(doc, surf, *, selector=":root", display_size=None,
                   title_overlap="-2.75rem", eyebrow_gap=None) -> str:
    """Emit the `--c-*` custom properties for ONE surface from brand token values.

    The same `c-*` component classes read these vars, so a single class set renders
    on-brand on any surface just by re-declaring this block at the surface's scope."""
    text = color_value(doc, surf.get("textPrimary")) or "#111111"
    accent = color_value(doc, surf.get("textAccent")) or text
    bg = surf.get("bg") or "#ffffff"
    # v1 surfaces sometimes carry a DESCRIPTIVE string ("image + dark scrim") instead of a
    # color — written raw into CSS it's an invalid value the browser silently drops
    # (anti-ai-slop.md AS-02 shape). Guard: non-color strings fall back to a dark canvas
    # (descriptive surfaces in practice describe photo-over-scrim, i.e. dark).
    if not re.match(r"^(#|rgb|hsl|var\()", str(bg).strip()):
        bg = "#141414"
    muted = (color_value(doc, "text/on-inverse-muted")
             if surf.get("textAccent") else color_value(doc, "text/on-primary-muted")) or text

    disp = type_role(doc, "display-hero")
    h2 = type_role(doc, "h2")
    h3 = type_role(doc, "h3")
    eyb = type_role(doc, "eyebrow")
    ctl = type_role(doc, "control-text")
    body = type_role(doc, "body")
    heading_stack, _ = font_stack(doc, "display-hero", "Georgia, serif")
    body_stack, _ = font_stack(doc, "body", "system-ui, sans-serif")
    eyebrow_gap = eyebrow_gap or spacing_value(doc, "eyebrow-to-heading", "1.5rem")
    # the brand's single ruled-line hairline (underline fields + ruled action rows);
    # falls back to muted ink so the hairline is never invisible.
    # SURFACE-AWARE hairline (matches the `muted` pattern above): a dark surface
    # never falls back to the light-surface "-on-primary" hairline value, which was
    # a near-black rgba at 30% opacity — invisible ("dark on dark") on the dark
    # inverse bands (e.g. the schedule/visit ruled rows). Prefers a dedicated
    # "-on-inverse" token when the brand has extracted one; otherwise falls back to
    # `muted`, which IS already correctly resolved per-surface above.
    # color_value() passes an UNRESOLVED token name through as a literal string (by
    # design, for callers that pass a raw hex value instead of a token ref) -- so `or
    # muted` never fires for a genuinely-missing "-on-inverse" token (the string itself
    # is truthy), and the browser silently drops the whole `--c-hairline` custom property
    # (not a valid color), which is how the schedule/visit ruled-row dividers went fully
    # TRANSPARENT rather than merely wrong-colored. Check token EXISTENCE directly instead
    # of relying on color_value()'s return-value truthiness.
    _hairline_tok = "border/hairline-on-inverse" if surf.get("textAccent") else "border/hairline-on-primary"
    _colors = (doc.get("tokens", {}) or {}).get("colors", {}) or {}
    hairline = color_value(doc, _hairline_tok) if _hairline_tok in _colors else muted
    # PER-SURFACE link-hover (anti-ai-slop.md AS-10): the brand's measured hover color was
    # measured on a DARK surface (footer/nav) -- WoodWave's gold is a 1.3:1 contrast
    # failure against the cream surface, so it must NEVER apply unconditionally. Use the
    # measured accent hover ONLY on a dark/textAccent-bearing surface; every light surface
    # keeps its own (already-safe, high-contrast) ink color on hover -- no visible shift,
    # same principle as no-accent-on-light applied to the hover state, not just the rest state.
    link_hover = (link_hover_color(doc) if surf.get("textAccent") else None) or text
    ds = base_size(disp) or 4
    # imagery aspect palette (tokens.imagery.aspectPalette, anti-ai-slop.md AS-17):
    # the brand's MEASURED ratio variety, emitted as vars the scaffolds read (each with
    # its pre-palette hardcoded value as fallback, so palette-less brands are unchanged).
    _pal = ((doc.get("tokens", {}) or {}).get("imagery", {}) or {}).get("aspectPalette", {}) or {}
    aspect_css = "".join(
        f"\n  --c-aspect-{k}: {v.get('value')};" for k, v in _pal.items()
        if isinstance(v, dict) and v.get("value"))

    return f"""{selector} {{
  --c-paper: {bg};
  --c-ink: {text};
  --c-ink-muted: {muted};
  --c-accent: {accent};
  --c-hairline: {hairline};
  --c-link-hover: {link_hover};
  --c-font-heading: {heading_stack};
  --c-font-body: {body_stack};
  --c-display-size: {display_size or f'{ds}rem'};
  --c-display-lh: {disp.get('lineHeight', '1.05em')};
  --c-display-ls: {disp.get('letterSpacing', '0rem')};
  --c-display-weight: {disp.get('weight', 400)};
  --c-heading-weight: {h2.get('weight') or disp.get('weight', 400)};
  --c-h2-size: {base_size(h2) or 2.25}rem;
  --c-h3-size: {base_size(h3) or 1.625}rem;
  --c-body-size: {base_size(body) or 1}rem;
  --c-eyebrow-size: {base_size(eyb) or 0.6875}rem;
  --c-eyebrow-ls: {eyb.get('letterSpacing', '0.08em')};
  --c-control-size: {base_size(ctl) or 0.875}rem;
  --c-control-ls: {ctl.get('letterSpacing', '0.08em')};
  --c-eyebrow-gap: {eyebrow_gap};
  --c-title-overlap: {css_len(title_overlap, '-2.75rem')};{aspect_css}
}}"""


# ── motion vars (calm editorial) — sourced from brand.yaml voice.motionSpec ─────
# Defaults encode the authored WoodWave calm/editorial spec so the renderer always has
# concrete values even if the brand is silent; the brand's voice.motionSpec wins.
_MOTION_DEFAULTS = {
    "ease": "cubic-bezier(.22, 1, .36, 1)",
    "fast": "320ms", "base": "480ms", "slow": "620ms", "shift": "16px",
}


def motion_spec(doc) -> dict:
    """Resolve the brand's authored motion spec (brand.yaml ``voice.motionSpec``) to the
    concrete CSS values the shared motion rules read: primary easing, fast/base/slow
    durations, and the scroll-reveal translateY shift. Falls back to the calm-editorial
    defaults wherever the brand is silent (so the spec is library-agnostic + robust)."""
    ms = ((doc or {}).get("voice") or {}).get("motionSpec") or {}
    dur = ms.get("durations") or {}
    rev = ms.get("scrollReveal") or {}
    return {
        "ease": (ms.get("easing") or {}).get("primary") or _MOTION_DEFAULTS["ease"],
        "fast": dur.get("fast") or _MOTION_DEFAULTS["fast"],
        "base": dur.get("base") or _MOTION_DEFAULTS["base"],
        "slow": dur.get("slow") or _MOTION_DEFAULTS["slow"],
        "shift": rev.get("translateY") or _MOTION_DEFAULTS["shift"],
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
    """Emit the motion ``--c-*`` custom properties from the brand motion spec so the shared
    motion rules (underline draw-in, scroll reveal, arrow nudge) read the brand's authored
    easing + durations. Container-query-safe: only time/transform values, never viewport
    units. Mirrors the existing ``--c-*`` CSS-var pattern."""
    m = motion_spec(doc)
    return (f"{selector} {{ --c-ease: {m['ease']}; --c-motion-fast: {m['fast']}; "
            f"--c-motion-base: {m['base']}; --c-motion-slow: {m['slow']}; "
            f"--c-reveal-shift: {m['shift']}; }}")


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
  transition: color var(--c-motion-fast, 320ms) var(--c-ease, cubic-bezier(.22, 1, .36, 1)); }}
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
  text-transform: uppercase; font-weight: var(--c-heading-weight, var(--c-display-weight)); }
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
  letter-spacing: var(--c-eyebrow-ls); text-transform: uppercase; color: var(--c-ink-muted);
  margin: 0; }

.c-image { display: block; width: 100%; border: none; box-shadow: none;
  border-radius: var(--radius); object-fit: cover; }
.c-image--hero { aspect-ratio: 1355 / 570; }
.c-image--overlap { aspect-ratio: 785 / 620; }
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
  aspect-ratio: 4 / 3; font-family: var(--c-font-body); font-size: var(--c-eyebrow-size);
  letter-spacing: var(--c-eyebrow-ls); text-transform: uppercase; }

.c-arrow-link { font-family: var(--c-font-body); font-size: var(--c-control-size);
  letter-spacing: var(--c-control-ls); text-transform: uppercase; text-decoration: none;
  color: var(--c-action-color, currentColor); display: inline-flex; align-items: center;
  gap: 0.5rem; background: none; border: none; cursor: pointer; padding: 0; }
.c-arrow-link--accent { color: var(--c-accent); }
.c-arrow { transition: transform var(--c-motion-fast, 320ms) var(--c-ease, cubic-bezier(.22, 1, .36, 1)); }
.c-arrow-link:hover .c-arrow { transform: translateX(0.35rem); }

.c-logo { display: inline-flex; align-items: center; gap: 0.5rem; font-family: var(--c-font-body);
  font-weight: 600; font-size: var(--c-control-size); letter-spacing: 0.08em;
  text-transform: uppercase; color: var(--c-logo-color, var(--c-accent)); }
.c-logo .c-glyph { font-family: var(--c-font-heading); font-size: 1.1rem; }
/* image logo (composed nav): the extracted brand logo as a plain linked <img>, no chip,
   no border, no radius. Sized from the extracted 175x26 proportions (height-capped so it
   scales down gracefully); width:auto keeps the aspect ratio. The WoodWave source SVG is
   already the brand gold, so it reads on the dark hero surface with no filter needed. */
.c-logo--img { display: inline-flex; align-items: center; text-decoration: none;
  border: none; border-radius: 0; }
.c-logo-img { display: block; height: 1.625rem; width: auto; max-width: 12rem; }

/* header block: eyebrow -> heading (+ optional subhead/cta) typographic cluster */
.c-header { display: flex; flex-direction: column; gap: var(--c-eyebrow-gap); }

/* paragraph primitive: narrow offset body, Inter sentence case, generous leading. */
.c-paragraph { font-family: var(--c-font-body); font-size: var(--c-body-size);
  line-height: 1.55em; color: var(--c-ink-muted); max-width: var(--c-measure, 34ch); margin: 0; }

/* caption primitive: muted uppercase margin micro-text (never over media). */
.c-caption { font-family: var(--c-font-body); font-size: var(--c-eyebrow-size);
  letter-spacing: var(--c-eyebrow-ls); text-transform: uppercase; color: var(--c-ink-muted);
  margin: 0; }

/* form block + underline field: NO box, NO fill, NO border — the single 1px rule is a
   pseudo-element (height:1px+background), so it never reads as a boxed input or a section
   hairline (honors WoodWave no-boxed-inputs / no-section-hairlines). */
.c-form { display: flex; flex-direction: column; gap: var(--c-form-gap, 1.25rem); }
.c-field { position: relative; display: flex; align-items: flex-end; justify-content: space-between;
  gap: 1rem; padding-bottom: 0.5rem; }
.c-field::after { content: ""; position: absolute; left: 0; right: 0; bottom: 0; height: 1px;
  background: var(--c-hairline); }
.c-field-text { font-family: var(--c-font-body); font-size: var(--c-body-size);
  text-transform: uppercase; letter-spacing: var(--c-control-ls); color: var(--c-ink-muted); }

/* ruled action rows (the divider primitive): label left, value/action right, separated by a
   1px pseudo-rule INSIDE a panel only — never as a section seam. */
.c-rows { display: flex; flex-direction: column; }
.c-row { position: relative; display: flex; align-items: baseline; justify-content: space-between;
  gap: 1rem; padding: 0.85rem 0; }
.c-row::before { content: ""; position: absolute; left: 0; right: 0; top: 0; height: 1px;
  background: var(--c-hairline); }
.c-row-label { font-family: var(--c-font-body); font-size: var(--c-control-size);
  letter-spacing: var(--c-control-ls); text-transform: uppercase; color: var(--c-ink); }
.c-row-value { font-family: var(--c-font-heading); font-size: var(--c-h3-size); color: var(--c-ink); }

/* footer block (closing bookend): a CENTERED oversized didone slash sitemap + TEXT
   social links (slash-separated, no icons) + a centered muted legal line. Reuses the
   brand's typographic vocabulary — the sitemap is the heading (didone) treatment, the
   social row is the control-text slash-link treatment, legal is muted micro-text. No
   boxes, borders, shadows, or radius (honors WoodWave neverDo). cq/rem units only.
   The whole cluster is CENTERED (flex centering + centered nav rows + centered legal),
   and uses the rhythm scale's inter-block gap so its vertical spacing matches the page.
   The sitemap link is a CONTAINED oversized clamp: clearly larger than body editorial
   display, but right-sized for a footer context — never the gigantic ~80px it was. */
.c-footer { display: flex; flex-direction: column; align-items: center; text-align: center;
  gap: var(--c-block-gap, 2.5rem); }
.c-foot-sitemap { display: flex; flex-wrap: wrap; align-items: baseline; justify-content: center;
  gap: 0.4rem 1.5rem; max-width: 60rem; margin: 0 auto; }
.c-foot-sitemap-link { font-family: var(--c-font-heading); text-transform: uppercase;
  font-weight: var(--c-heading-weight, var(--c-display-weight));
  font-size: var(--c-footer-link-size, clamp(1.75rem, 3.5cqw, 3rem));
  line-height: 1.2em; color: var(--c-ink); text-decoration: none; }
.c-foot-sep { color: var(--c-ink-muted); font-family: var(--c-font-heading); }
.c-foot-social { display: flex; flex-wrap: wrap; align-items: center; justify-content: center;
  gap: 0.4rem 0.9rem; margin: 0 auto; }
.c-foot-social-link { font-family: var(--c-font-body); font-size: var(--c-control-size);
  letter-spacing: var(--c-control-ls); text-transform: uppercase; color: var(--c-ink-muted);
  text-decoration: none; }
.c-foot-social .c-foot-sep { font-family: var(--c-font-body); }
.c-foot-legal { font-family: var(--c-font-body); font-size: var(--c-eyebrow-size);
  letter-spacing: var(--c-eyebrow-ls); color: var(--c-ink-muted); margin: 0; }

/* ── MOTION (calm / editorial) ── authored brand spec (brand.yaml voice.motionSpec):
   expressive ease-out, durations ~320-620ms, NO bounce/spring/overshoot/snap. Easing +
   durations come from the brand's --c-* motion vars (component_render.motion_vars_css),
   each with an inline calm-editorial fallback so the rules still read if a caller omits
   them. Motion is time + transform only — no viewport units, no new color/shadow/radius. */

/* typographic links: an underline that DRAWS IN (scaleX 0->100%, origin left), NOT a
   color swap — consistent with WoodWave's typographic-link aesthetic. The rule is a 1px
   pseudo-element (height+background), never a border, so it adds no border/hairline. */
.c-arrow-link, .c-foot-sitemap-link, .c-foot-social-link { position: relative; }
.c-arrow-link::after, .c-foot-sitemap-link::after, .c-foot-social-link::after {
  content: ""; position: absolute; left: 0; right: 0; bottom: -0.08em; height: 1px;
  background: currentColor; transform: scaleX(0); transform-origin: left center;
  transition: transform var(--c-motion-base, 480ms) var(--c-ease, cubic-bezier(.22, 1, .36, 1)); }
.c-arrow-link:hover::after, .c-arrow-link:focus-visible::after,
.c-foot-sitemap-link:hover::after, .c-foot-sitemap-link:focus-visible::after,
.c-foot-social-link:hover::after, .c-foot-social-link:focus-visible::after {
  transform: scaleX(1); }

/* calm scroll reveal: opacity + small translateY (no scale pop, no rotation). The hidden
   initial state is GATED on `.cs-motion-ready` (added by the page's tiny IntersectionObserver
   script) so content is fully visible if JS/IO is unavailable; `.is-in` reveals it. */
.cs-motion-ready .cs-reveal {
  opacity: 0; transform: translateY(var(--c-reveal-shift, 16px));
  transition: opacity var(--c-motion-slow, 620ms) var(--c-ease, cubic-bezier(.22, 1, .36, 1)),
              transform var(--c-motion-slow, 620ms) var(--c-ease, cubic-bezier(.22, 1, .36, 1));
  transition-delay: calc(var(--cs-reveal-i, 0) * 60ms); will-change: opacity, transform; }
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
    props: label, href, accent. Always a typographic <a>, NEVER a <button>."""
    props = props or {}
    accent = " c-arrow-link--accent" if props.get("accent") else ""
    href = esc(props.get("href", "#"))
    return (f'<a class="c-arrow-link{accent}" href="{href}">{esc(props.get("label", "Learn more"))} '
            f'<span class="c-arrow" aria-hidden="true">&rarr;</span></a>')


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


def render_input(doc, ctx: ComponentContext, props=None) -> str:
    """input primitive (underline variant). Rendered as a typographic underline FIELD with
    an inline submit arrow-link — no boxed/filled <input>, matching the brand's Lead form.
    props: placeholder, submit (label)."""
    props = props or {}
    placeholder = esc(props.get("placeholder", "Your email"))
    submit = render_arrow_link(doc, ctx, {"label": props.get("submit", "Subscribe"),
                                          "accent": ctx.is_dark}) if props.get("submit") else ""
    return (f'<label class="c-field"><span class="c-field-text">{placeholder}</span>'
            f'{submit}</label>')


def render_form(doc, ctx: ComponentContext, props=None) -> str:
    """form block — composes an optional header + underline field(s) + inline submit, all
    from the catalog primitives. No boxed inputs, no filled button (typographic submit)."""
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
    typographic primitives: a CENTERED oversized didone slash SITEMAP, a TEXT social row
    (slash-separated, no icons), and a centered muted legal line. Pulled from brand.yaml
    (blocks.footer slot notes + the extracted top-level footer); never a boxed/chromed
    footer. props: sitemap[], social[], legal. Rendered on a dark/inverse surface."""
    props = props or {}
    sep = '<span class="c-foot-sep" aria-hidden="true">/</span>'
    sitemap = props.get("sitemap") or []
    social = props.get("social") or []
    legal = props.get("legal") or ""
    parts = []
    if sitemap:
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


def render_navbar(doc, ctx: ComponentContext, props=None) -> str:
    """navbar block - zero-chrome: logo + slash links + a single arrow-link cta (no
    fill/border/button). Composes the logo + arrow-link primitives.

    The logo is either the extracted IMAGE (when props["logo"] is a dict carrying an
    `img`/`src`, e.g. the composed nav) or the text wordmark (props["wordmark"]). Links may
    be plain strings OR {label, href} dicts (the extracted navbar.primary), so real hrefs
    survive; `.c-arrow-link` uppercases them, matching the brand's slash nav."""
    props = props or {}
    logo_props = props.get("logo")
    if isinstance(logo_props, dict):
        logo = render_logo(doc, ctx, logo_props)
    else:
        logo = render_logo(doc, ctx, {"text": props.get("wordmark", "Brand")})
    links = props.get("links") or []
    # vocabulary-prefixed separator class (cs-*) so the composition primitive-only
    # invariant sees only c-*/cs-* classes (was a bare `sep`, the sole non-vocab class).
    sep = ' <span class="cs-sep">/</span> '

    def _link(n):
        if isinstance(n, dict):
            return (f'<a class="c-arrow-link" href="{esc(n.get("href", "#"))}" '
                    f'style="gap:0">{esc(n.get("label", ""))}</a>')
        return f'<a class="c-arrow-link" href="#" style="gap:0">{esc(n)}</a>'

    navlinks = sep.join(_link(n) for n in links)
    cta = ""
    if props.get("cta"):
        # The nav CTA is a typographic INK arrow link (accent stays reserved for the
        # logo/eyebrow + the sanctioned hero display title), so a section carries a SINGLE
        # committed accent. A caller may opt back into an accent CTA via ctaAccent=True.
        cta = render_arrow_link(doc, ctx, {
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
    "paragraph": render_paragraph,
    "caption": render_caption,
    "input": render_input,
}

BLOCK_RENDERERS = {
    "header": render_header,
    "navbar": render_navbar,
    "form": render_form,
    "footer": render_footer,
}


def resolve_renderer(contract: str):
    """Resolve a catalog contract key (from a layout's blockMapping) to its shared
    renderer. Returns None when no shared renderer exists yet (caller may fall back)."""
    return PRIMITIVE_RENDERERS.get(contract) or BLOCK_RENDERERS.get(contract)
