#!/usr/bin/env python3
"""render_hero_variants.py - contract-driven Tailwind/shadcn static renderer for the
WoodWave opening-bookend HERO, with a variance dial (A|B|C).

This is NOT render_section.py (left untouched) and NOT the Webflow assembler. It reads
the LIBRARY-AGNOSTIC brand.yaml v2.0 (tokens carry value+intent) plus the two universal
contracts (contracts/primitives.yaml + contracts/blocks.yaml), resolves the
`opening-bookend` layout, and emits a SELF-CONTAINED static `index.html` per variant:

  - render substrate = STATIC HTML + Tailwind (CDN) + an inline tailwind.config carrying
    the brand fonts/colors + shadcn-style markup/class conventions. EVERY color / type /
    spacing / radius comes from brand.yaml token VALUES (never Webflow names; the
    `targetMappings:` block is ignored entirely). Brand fonts load via Google Fonts.
  - a `:root` custom-property block mirrors the brand token values so the static file
    is on-brand without depending on Tailwind's runtime JIT (and so the on-brand gate,
    which reads the static text, can verify token presence).

Variance dial (same brand.yaml + same copy across all three; ONLY variance differs):

  A = SAFE      - on-brand floor: conservative display tier, sanctioned title-over-media
                  only (no media-over-media), strict adherence to ALL brand rules.
  B = BOLD      - sanctioned overlap (display-text-over-media + media-over-media per
                  compositionRules) + expressive type scale, honoring EVERY neverDo.
  C = WILDCARD  - B, plus it relaxes EXACTLY ONE named neverDo (`no-buttons`): the CTA
                  becomes a filled gold button instead of a typographic arrow link.
                  The relaxation is logged passively to runs/woodwave/brand/signals.log
                  as a one-off exception (promoted:false) and is NEVER written to
                  brand.yaml.

Usage:
  python3 render_hero_variants.py <brand.yaml> --variant A -o <outdir>
  python3 render_hero_variants.py <brand.yaml> --all -o <variants_root>   # a/, b/, c/
"""
from __future__ import annotations

import argparse
import html
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

# The STYLE layer of the two-layer model lives beside this renderer in brand_pipeline/.
# Insert this file's dir on sys.path so `import styles` works whether invoked as a
# script (python3 brand_pipeline/render_hero_variants.py ...) or imported as a module.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from styles import RenderContext, inactive_context, load_and_merge  # noqa: E402

# The single neverDo rule the WILDCARD variant (C) is allowed to relax.
WILDCARD_RELAXED_RULE = "no-buttons"

# Real, on-brand hero copy (NOT lorem). Title comes from the layout blockMapping; the
# voice lines are loaded from the BRAND'S OWN section-copy.yaml (sectionCopy block)
# beside brand.yaml — never a hardcoded literal (the old dict froze one brand's voice
# into the harness). Missing file/keys degrade to a wordmark-only nav + elided lines,
# matching the composer's degrade-to-empty copy policy. Hydrated by render_variant().
COPY = {"wordmark": "", "nav": [], "eyebrow": "", "subhead": "", "cta": ""}

# Hero photography candidate NAMES, from the brand's own authored section-copy.yaml
# (defaultArt values + layoutImages) — only files that actually exist under the brand
# dir are copied, so a brand without these simply renders the placeholder plate.
ASSET_SOURCES: list = []

# Hero/overlap art the markup binds — the brand's OWN defaultArt (hero + detail kinds);
# empty means "no art declared" and the collage degrades to unbound media plates.
ART: dict = {"hero": "", "overlap": ""}


def load_brand_copy(doc, brand_dir: Path) -> tuple[dict, list, dict]:
    """(copy dict, asset name seed, art dict) from <brand_dir>/section-copy.yaml;
    degrade-to-empty."""
    data = {}
    p = Path(brand_dir) / "section-copy.yaml"
    if p.exists():
        data = yaml.safe_load(p.read_text()) or {}
    sc = data.get("sectionCopy") or {}
    copy_block = {
        "wordmark": sc.get("wordmark") or (doc.get("brand") or {}).get("name") or "Brand",
        "nav": list(sc.get("nav") or []),
        "eyebrow": sc.get("eyebrow") or "",
        "subhead": sc.get("subhead") or "",
        "cta": sc.get("cta") or "",
    }
    art_src = data.get("defaultArt") or {}
    art = {
        "hero": (art_src.get("hero") or [""])[0],
        "overlap": (art_src.get("detail") or art_src.get("overlays") or [""])[0],
    }
    names: list[str] = []
    for kind_names in art_src.values():
        for n in (kind_names or []):
            if n not in names:
                names.append(n)
    for img_map in (data.get("layoutImages") or {}).values():
        for n in (img_map or {}).values():
            if n not in names:
                names.append(n)
    return copy_block, names, art


# ── loaders + token resolvers (library-agnostic; targetMappings ignored) ────────

def load_yaml(path: Path):
    return yaml.safe_load(Path(path).read_text())


def load_contracts(doc, brand_yaml: Path):
    base = Path(brand_yaml).parent
    refs = doc.get("contracts", {}) or {}
    prim = load_yaml((base / refs["primitives"]).resolve()) if refs.get("primitives") else {}
    blk = load_yaml((base / refs["blocks"]).resolve()) if refs.get("blocks") else {}
    return prim, blk


def color(doc, token, default=None):
    if not token:
        return default
    c = (doc["tokens"]["colors"] or {}).get(token)
    return c["value"] if c else (token if str(token).startswith("#") else default)


def type_role(doc, role):
    return (doc["tokens"]["type"] or {}).get(role, {}) or {}


def base_size(t):
    sz = t.get("sizeRem")
    if isinstance(sz, dict):
        return sz.get("base")
    return sz


def size_at(t, tier, default=None):
    sz = t.get("sizeRem")
    if isinstance(sz, dict):
        return sz.get(tier, default)
    return sz if sz is not None else default


def spacing(doc, role, default="0rem"):
    return (doc["tokens"]["spacing"] or {}).get(role, {}).get("value", default)


def surface_for_layout(doc, layout):
    """Resolve a layout's surface via its library-agnostic `surfaceIntent` role."""
    role = layout.get("surfaceIntent") or layout.get("surfaceRole")
    surfaces = doc["tokens"]["surfaces"] or {}
    if role and role in surfaces:
        return role, surfaces[role]
    first = next(iter(surfaces))
    return first, surfaces[first]


def layout_by_id(doc, lid):
    return next((l for l in doc.get("layouts", []) if l.get("id") == lid), None)


# Layout ids / archetypes that count as a HERO (opening bookend). The WILDCARD one-off
# neverDo relaxation is scoped to these ONLY (recipePolicy.magicTrick.wildcardScope).
HERO_LAYOUT_IDS = {"opening-bookend"}
HERO_ARCHETYPES = {"hero"}


def is_hero_layout(layout) -> bool:
    """Robustly decide whether a layout is a HERO (opening-bookend) section.

    POLICY: the WILDCARD variant's one-off neverDo relaxation is permitted on hero
    sections ONLY. Detection checks the layout id and archetype passed in: an explicit
    hero archetype, the canonical `opening-bookend` id, or an id/archetype that reads as
    a hero / opening-bookend. Any non-hero section must enforce ALL neverDo rules.
    """
    if not isinstance(layout, dict):
        return False
    lid = str(layout.get("id", "")).strip().lower()
    arch = str(layout.get("archetype", "")).strip().lower()
    if arch in HERO_ARCHETYPES or lid in HERO_LAYOUT_IDS:
        return True
    return "hero" in lid or "opening-bookend" in lid or "opening-bookend" in arch


def heading_text(layout, default="HEADING"):
    for m in layout.get("blockMapping", []) or []:
        usage = m.get("usage") or {}
        if usage.get("heading"):
            return usage["heading"]
    return default


def _esc(s):
    return html.escape(str(s if s is not None else ""))


# ── variance dial ──────────────────────────────────────────────────────────────

def variance_config(doc, variant: str, is_hero: bool = True) -> dict:
    """Return the per-variant rendering knobs, derived from brand.yaml token values.

    `is_hero` gates the WILDCARD variant (C): the one-off neverDo relaxation is allowed
    on HERO sections ONLY (recipePolicy.magicTrick.wildcardScope = hero-only). For any
    non-hero section, C falls back to bold-level variance and enforces ALL neverDo rules
    (no relaxation, no button).
    """
    v = variant.upper()
    disp = type_role(doc, "display-hero")
    base = base_size(disp) or 6            # 6rem
    tablet = size_at(disp, "tablet", 4.5)  # 4.5rem
    if v == "A":
        return {
            "key": "a", "name": "Safe",
            # conservative tier (the brand's tablet display value) - the on-brand floor
            "display_size": f"{tablet}rem",
            "title_overlap": "-1.25rem",   # minimal sanctioned display-text-over-media
            "media_over_media": False,
            "cta_kind": "link",
            "relax": None,
            "subtitle": "Low variance — the on-brand floor.",
        }
    if v == "B":
        return {
            "key": "b", "name": "Bold",
            # expressive type scale beyond the base tier (variance dial = high)
            "display_size": f"clamp({base}rem, 9cqw, {round(base * 1.25, 3)}rem)",
            "title_overlap": "-3.25rem",   # deeper title overlap
            "media_over_media": True,      # sanctioned media-over-media overlap
            "cta_kind": "link",
            "relax": None,
            "subtitle": "High variance — sanctioned overlap + expressive type.",
        }
    if v == "C":
        if not is_hero:
            # POLICY (recipePolicy.magicTrick.wildcardScope = hero-only): the WILDCARD
            # one-off neverDo relaxation is permitted on HERO sections ONLY. On any
            # non-hero section C must enforce EVERY neverDo, so it falls back to
            # bold-level variance — no relaxation, typographic link CTA (no button).
            return {
                "key": "c", "name": "Wildcard",
                "display_size": f"clamp({base}rem, 9cqw, {round(base * 1.25, 3)}rem)",
                "title_overlap": "-3.25rem",
                "media_over_media": True,
                "cta_kind": "link",
                "relax": None,
                "subtitle": "Max variance — non-hero: all neverDo enforced (no relaxation).",
            }
        return {
            "key": "c", "name": "Wildcard",
            "display_size": f"clamp({base}rem, 9cqw, {round(base * 1.25, 3)}rem)",
            "title_overlap": "-3.25rem",
            "media_over_media": True,
            "cta_kind": "button",          # relaxes no-buttons: a filled gold CTA
            "relax": WILDCARD_RELAXED_RULE,
            "subtitle": "Max variance — relaxes one neverDo (no-buttons).",
        }
    raise SystemExit(f"unknown variant '{variant}' (expected A|B|C)")


# ── CSS ─────────────────────────────────────────────────────────────────────────

def build_style_overrides_css(ctx: RenderContext) -> str:
    """STYLE layer applied OVER the brand base, in CSS source order so the structural
    rules win (the precedence engine, expressed in CSS).

    STYLE owns structure (shape, depth, type scale/leading/tracking, density,
    color-DEPLOYMENT, motion); BRAND owns hues + fonts (pulled from the merged slots).
    Hues/fonts here are the brand SLOT values; structure is from the style.

    CRITICAL: every length here is rem / cqw / % — NEVER a viewport unit. The display
    tier's documented intent (~12vw) is emitted as cqw against `container-name:frame`.
    """
    s = ctx.structure
    paper = ctx.paper
    ink = ctx.ink
    accent = ctx.accent
    fd = ctx.font_display
    fb = ctx.font_body
    fm = ctx.font_mono
    return f"""

/* ===================================================================== */
/* STYLE: {ctx.style_id} (structure) layered OVER brand (hues+fonts).     */
/* Brand slots: paper={paper} ink={ink} accent={accent}.                  */
/* Structure: radius={s.radius} flat={s.flat} centered={s.centered}.      */
/* ===================================================================== */
:root {{
  /* BRAND slots fill the style's named slots (brand wins on hue/font) */
  --bg: {paper};
  --text: {ink};
  --accent: {accent};
  --on-accent: {paper};
  /* STYLE structure (brand may NOT override these) */
  --radius: {s.radius};
  --display-size: {s.display_size_css()};
  --display-leading: {s.display_leading};
  --display-tracking: {s.display_tracking};
  --motion: {s.motion_ms}ms;
  --font-heading: '{fd}', Georgia, serif;
  --font-body: '{fb}', system-ui, sans-serif;
  --font-mono: {fm};
}}

/* Shape: 0 radius everywhere incl. images + buttons; flat (no shadow/border/mat).
   Clean 0 / none values (no !important) so the rules win on source order + specificity. */
.hv-media, .hv-figure img, .hv-cta-btn {{ border-radius: 0; box-shadow: none; }}

/* Density & rhythm: ASYMMETRIC, never centered-everything. Big empty left/right
   margins set against a dense left-anchored type column. */
.hv-section {{ padding: 3rem 12cqw 6rem 6cqw; }}
.hv-slot {{ align-items: flex-start; text-align: left; }}
.hv-foot {{ align-items: flex-start; text-align: left; margin-top: 4rem; }}
.hv-collage {{ margin: 0; max-width: 64cqw; }}

/* Type (load-bearing): genuine poster scale, tight leading, negative tracking, ink. */
.hv-title.is-display {{ font-family: var(--font-heading); font-size: var(--display-size);
  line-height: var(--display-leading); letter-spacing: var(--display-tracking);
  color: var(--text); text-align: left; max-width: 18ch; }}

/* Color deployment: near-monochrome ink-on-paper. The accent is COMMITTED to ONE
   highlight (the eyebrow slug) — never scattered across nav/links/buttons as garnish. */
.hv-logo, .hv-logo .glyph, .hv-navlinks a, .hv-navlinks .sep, .hv-nav-cta,
.hv-action, .hv-sub, .hv-cap {{ color: var(--text); }}
.hv-eyebrow {{ color: var(--accent); font-family: var(--font-mono); text-align: left;
  letter-spacing: 0.18em; }}

/* Motion: restrained + slow (page turning, not UI reacting). */
.hv-title.is-display, .hv-media, .hv-sub {{ transition: opacity var(--motion) ease,
  transform var(--motion) ease; }}
@media (prefers-reduced-motion: reduce) {{
  .hv-title.is-display, .hv-media, .hv-sub {{ transition: none; }}
}}
"""


def build_css(doc, layout, cfg, style_ctx: RenderContext | None = None) -> str:
    _, surf = surface_for_layout(doc, layout)
    bg = surf.get("bg")
    text = color(doc, surf.get("textPrimary"))
    accent = color(doc, surf.get("textAccent")) or text
    muted = color(doc, "text/on-inverse-muted") or text
    # on-accent ink: the brand's own token, else its base text ink (never a foreign hex).
    on_accent = color(doc, "text/on-primary") or text or "#000000"

    disp = type_role(doc, "display-hero")
    radius = spacing(doc, "radius-global", "0rem")
    pad = (doc["tokens"]["spacing"].get("section-padding-dark", {}) or {}).get("value") \
        or spacing(doc, "section-padding-light", "6.25rem")
    eyebrow_gap = spacing(doc, "eyebrow-to-heading", "1.5rem")

    heading_family = disp.get("family", "Playfair Display")
    body_family = type_role(doc, "control-text").get("family") \
        or type_role(doc, "body").get("family") or "Inter"

    off = (layout.get("overlapRules", {}) or {}).get("offsets", {}) or {}
    second_cross = str(off.get("secondMediaCrossesBottom", "~50%")).replace("~", "").strip()
    disp_tablet = size_at(disp, "tablet", 4.5)
    disp_mobile = size_at(disp, "mobile", 3)

    base_css = f""":root {{
  --bg: {bg};
  --text: {text};
  --accent: {accent};
  --muted: {muted};
  --on-accent: {on_accent};
  --radius: {radius};
  --display-size: {cfg['display_size']};
  --section-pad: {pad};
  --eyebrow-gap: {eyebrow_gap};
  --font-heading: '{heading_family}', Georgia, serif;
  --font-body: '{body_family}', system-ui, sans-serif;
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
img {{ display: block; max-width: 100%; }}
html {{ background: var(--bg); height: 100%; }}
/* iframe-safe container context: cq* length units resolve against this sized box.
   Studio renders this HTML inside an iframe where viewport-relative length units
   misbehave, so the top-level wrapper establishes an explicit sized container. */
body {{ background: var(--bg); color: var(--text); font-family: var(--font-body);
  -webkit-font-smoothing: antialiased; min-height: 100%;
  container-type: size; container-name: frame; }}

/* opening-bookend scaffold (archetype stack, surface mode Inverse), full-bleed */
.hv-section {{ background: var(--bg); color: var(--text);
  padding: 1.75rem 2.5rem var(--section-pad); min-height: 100cqh; }}

/* zero-chrome slash nav: wordmark + typographic links (neverDo:no-buttons honored in A/B) */
.hv-nav {{ display: flex; align-items: center; justify-content: space-between; gap: 2rem;
  margin-bottom: clamp(2rem, 6cqw, 5rem); }}
.hv-logo {{ display: inline-flex; align-items: center; gap: 0.5rem; font-family: var(--font-body);
  font-weight: 600; font-size: 0.875rem; letter-spacing: 0.08em; text-transform: uppercase;
  color: var(--accent); }}
.hv-logo .glyph {{ font-family: var(--font-heading); font-size: 1.1rem; }}
.hv-navlinks {{ display: flex; gap: 0.55rem; flex: 1; justify-content: center; }}
.hv-navlinks a {{ font-family: var(--font-body); font-size: 0.875rem; letter-spacing: 0.08em;
  text-transform: uppercase; text-decoration: none; color: var(--text); white-space: nowrap; }}
.hv-navlinks .sep {{ color: var(--text); opacity: 0.55; }}
.hv-nav-cta {{ font-family: var(--font-body); font-size: 0.875rem; letter-spacing: 0.08em;
  text-transform: uppercase; text-decoration: none; color: var(--accent); white-space: nowrap; }}

/* stack slot: centered display title over layered media (bookend centering is sanctioned) */
.hv-slot {{ display: flex; flex-direction: column; align-items: center; }}
.hv-eyebrow {{ font-family: var(--font-body); font-size: 0.6875rem; letter-spacing: 0.08em;
  text-transform: uppercase; color: var(--muted); text-align: center;
  margin-bottom: var(--eyebrow-gap); }}

/* Heading Style:display - the sanctioned display-text-over-media overlap */
.hv-title.is-display {{ font-family: var(--font-heading); font-weight: {disp.get('weight', 400)};
  font-size: var(--display-size); line-height: {disp.get('lineHeight', '1.05em')};
  letter-spacing: {disp.get('letterSpacing', '0rem')}; text-transform: uppercase;
  color: var(--accent); text-align: center; position: relative; z-index: 2;
  margin-bottom: {cfg['title_overlap']}; }}

/* media: hard-edged photography (radius 0, no shadow/border/mat) */
.hv-collage {{ position: relative; width: 100%; max-width: 80rem; margin: 0 auto; }}
.hv-media {{ display: block; width: 100%; border-radius: var(--radius); }}
.hv-media.is-hero {{ aspect-ratio: 1355 / 570; object-fit: cover; }}
.hv-media.is-overlap-abs {{ position: absolute; width: 34%; right: 4%; bottom: -{second_cross};
  aspect-ratio: 785 / 620; object-fit: cover; z-index: 1; }}
.hv-spacer {{ height: 22cqw; }}

/* A: portrait as a margin figure with an uppercase micro-caption (no media-over-media) */
.hv-figure {{ display: flex; align-items: flex-end; gap: 0.75rem; max-width: 80rem;
  margin: 2.5rem auto 0; justify-content: flex-end; }}
.hv-figure img {{ width: 26%; border-radius: var(--radius); aspect-ratio: 785 / 620;
  object-fit: cover; }}
.hv-cap {{ font-family: var(--font-body); font-size: 0.6875rem; letter-spacing: 0.08em;
  text-transform: uppercase; color: var(--muted); writing-mode: vertical-rl; }}

/* hero foot: subhead + CTA */
.hv-foot {{ display: flex; flex-direction: column; align-items: center; gap: 1.75rem;
  text-align: center; margin-top: 2.5rem; }}
.hv-sub {{ font-family: var(--font-body); font-size: 1rem; line-height: 1.55em;
  color: var(--muted); max-width: 42rem; }}
.hv-action {{ font-family: var(--font-body); font-size: 0.875rem; letter-spacing: 0.08em;
  text-transform: uppercase; text-decoration: none; color: var(--accent); }}

/* C only: filled gold CTA button - hard-edged (radius 0), no shadow/border.
   This is the WILDCARD one-off that relaxes neverDo:no-buttons. */
.hv-cta-btn {{ font-family: var(--font-body); font-size: 0.875rem; letter-spacing: 0.08em;
  text-transform: uppercase; cursor: pointer; background: var(--accent); color: var(--on-accent);
  border-radius: var(--radius); padding: 0.9rem 2rem; display: inline-flex; align-items: center;
  gap: 0.5rem; }}

@media (max-width: 991px) {{
  :root {{ --display-size: {disp_tablet}rem; }}
  .hv-navlinks {{ display: none; }}
}}
@media (max-width: 767px) {{
  :root {{ --display-size: {disp_mobile}rem; }}
  .hv-section {{ padding: 1.25rem 1.25rem 3rem; }}
  .hv-media.is-overlap-abs {{ width: 46%; right: 2%; bottom: -18%; }}
  .hv-spacer {{ height: 30cqw; }}
  .hv-figure img {{ width: 40%; }}
}}
"""
    # PRECEDENCE ENGINE (CSS-source-order): when a STYLE is active, append its structural
    # overrides AFTER the brand base so the load-bearing style rules win. Brand still
    # supplies the hues/fonts (via the slots), but structure is the style's to dictate.
    if style_ctx is not None and style_ctx.active:
        return base_css + build_style_overrides_css(style_ctx)
    return base_css


# ── HTML ─────────────────────────────────────────────────────────────────────────

def tailwind_config(doc, layout) -> str:
    """Inline tailwind.config carrying the brand fonts + colors (token VALUES only)."""
    _, surf = surface_for_layout(doc, layout)
    disp = type_role(doc, "display-hero")
    body_family = type_role(doc, "control-text").get("family") \
        or type_role(doc, "body").get("family") or "Inter"
    colors = {
        "cream": color(doc, "surface/primary"),
        "panel": color(doc, "surface/panel"),
        "inverse": color(doc, "surface/inverse"),
        "inverse-strong": color(doc, "surface/inverse-strong"),
        "accent": color(doc, "accent/highlight"),
        "ink": color(doc, "text/on-primary"),
        "ink-inverse": color(doc, "text/on-inverse"),
        "ink-muted": color(doc, "text/on-inverse-muted"),
    }
    cfg = {
        "theme": {
            "extend": {
                "colors": colors,
                "fontFamily": {
                    "heading": [disp.get("family", "Playfair Display"), "Georgia", "serif"],
                    "body": [body_family, "system-ui", "sans-serif"],
                },
                "borderRadius": {"brand": spacing(doc, "radius-global", "0rem")},
            }
        }
    }
    return "tailwind.config = " + json.dumps(cfg, indent=2) + ";"


def google_fonts_link() -> str:
    return ('<link rel="preconnect" href="https://fonts.googleapis.com">\n'
            '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
            '<link href="https://fonts.googleapis.com/css2?'
            'family=Playfair+Display:wght@400;500&family=Inter:wght@400;500;600&display=swap" '
            'rel="stylesheet">')


def build_html(doc, layout, cfg, style_ctx: RenderContext | None = None) -> str:
    name = doc["brand"]["name"]
    css = build_css(doc, layout, cfg, style_ctx)
    twcfg = tailwind_config(doc, layout)
    style_active = bool(style_ctx and style_ctx.active)
    # Deterministic markers so the on-brand gate can verify the active style's
    # structural intent against the rendered output (asymmetric grid, single accent).
    html_attr = f' data-style="{style_ctx.style_id}"' if style_active else ""
    section_cls = "hv-section is-editorial" if style_active else "hv-section"
    slot_cls = "hv-slot is-editorial" if style_active else "hv-slot"

    title = heading_text(layout, name.upper())
    parts = title.split(" ")
    line1, line2 = (parts[0], " ".join(parts[1:])) if len(parts) >= 2 else (title, "")

    nav = ' <span class="sep">/</span> '.join(
        f'<a href="#">{_esc(n)}</a>' for n in COPY["nav"])

    # media block: B/C = media-over-media (absolute overlap); A = margin figure.
    # Art binds the brand's OWN defaultArt (hydrated into ART); a brand with none
    # declared renders unbound media plates rather than another brand's photos.
    hero_img = (f'<img class="hv-media is-hero" src="assets/{_esc(ART["hero"])}"\n'
                f'         alt="Hero photograph">'
                if ART.get("hero") else '<div class="hv-media is-hero"></div>')
    overlap_img = (f'<img class="hv-media is-overlap-abs" src="assets/{_esc(ART["overlap"])}"\n'
                   f'         alt="Detail photograph">'
                   if ART.get("overlap") else '<div class="hv-media is-overlap-abs"></div>')
    figure_img = (f'<img src="assets/{_esc(ART["overlap"])}" alt="Detail photograph">'
                  if ART.get("overlap") else '<div class="hv-media"></div>')
    if cfg["media_over_media"]:
        media_block = f"""  <!-- media-over-media via absolute offsets: sanctioned overlap (compositionRules) -->
  <div class="hv-collage">
    {hero_img}
    {overlap_img}
  </div>
  <div class="hv-spacer"></div>"""
    else:
        media_block = f"""  <!-- hero photo only; sanctioned overlap limited to title-over-media -->
  <div class="hv-collage">
    {hero_img}
  </div>
  <!-- portrait kept as a margin figure with an uppercase micro-caption (no media-over-media) -->
  <figure class="hv-figure">
    <figcaption class="hv-cap">Plate 02 — Detail</figcaption>
    {figure_img}
  </figure>"""

    # CTA: A/B typographic arrow link; C filled gold button (relaxes no-buttons)
    if cfg["cta_kind"] == "button":
        cta_html = (f'      <button type="button" class="hv-cta-btn">'
                    f'{_esc(COPY["cta"])} &rarr;</button>')
        nav_cta = (f'    <button type="button" class="hv-cta-btn" '
                   f'style="padding:0.5rem 1.1rem">{_esc(COPY["cta"])}</button>')
    else:
        cta_html = f'      <a class="hv-action" href="#">{_esc(COPY["cta"])} &rarr;</a>'
        nav_cta = f'    <a class="hv-nav-cta" href="#">{_esc(COPY["cta"])}</a>'

    return f"""<!doctype html>
<html lang="en"{html_attr}>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_esc(name)} - opening-bookend - Variant {cfg['key'].upper()} ({cfg['name']})</title>
<!-- Tailwind (CDN) + inline brand config; shadcn-style markup. Token VALUES from brand.yaml. -->
<script src="https://cdn.tailwindcss.com"></script>
<script>
{twcfg}
</script>
{google_fonts_link()}
<style>
{css}
</style>
</head>
<body class="font-body bg-inverse text-ink-inverse antialiased">
<!-- opening-bookend (archetype stack), surface mode Inverse -->
<section class="{section_cls}">
  <!-- Logo wordmark + slash nav -->
  <nav class="hv-nav">
    <span class="hv-logo"><span class="glyph">&#9697;</span> {_esc(COPY['wordmark'])}</span>
    <span class="hv-navlinks">{nav}</span>
{nav_cta}
  </nav>

  <!-- Stack slot: eyebrow -> display title over layered photo collage -->
  <div class="{slot_cls}">
    <p class="hv-eyebrow">{_esc(COPY['eyebrow'])}</p>
    <!-- Heading Style:display - display-text-over-media (sanctioned overlap) -->
    <h1 class="hv-title is-display">{_esc(line1)}<br>{_esc(line2)}</h1>
{media_block}
    <div class="hv-foot">
      <p class="hv-sub">{_esc(COPY['subhead'])}</p>
{cta_html}
    </div>
  </div>
</section>
</body>
</html>
"""


# ── assets + signal log ──────────────────────────────────────────────────────────

def find_asset_source(brand_dir: Path, name: str) -> Path | None:
    """Locate a reusable brand asset by name under the brand's existing renders."""
    candidates = [
        brand_dir / "render" / "section-opening-bookend" / "assets" / name,
        brand_dir / "compose" / "signup-launch" / "assets" / name,
    ]
    for c in candidates:
        if c.exists():
            return c
    hits = sorted(brand_dir.glob(f"**/assets/{name}"))
    return hits[0] if hits else None


def copy_assets(brand_dir: Path, out_assets: Path) -> list[str]:
    out_assets.mkdir(parents=True, exist_ok=True)
    copied = []
    for name in ASSET_SOURCES:
        src = find_asset_source(brand_dir, name)
        if src:
            shutil.copy2(src, out_assets / name)
            copied.append(name)
    return copied


def log_one_off_exception(brand_dir: Path, rule_id: str, note: str, variant: str) -> bool:
    """Append a PASSIVE one-off-exception event to signals.log (never promoted)."""
    log_path = brand_dir / "signals.log"
    event = {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "type": "one-off-exception",
        "ruleId": rule_id,
        "scope": "one-off",
        "promoted": False,
        "note": note,
        "variant": variant,
    }
    # de-dupe: skip if an identical one-off-exception for this rule+variant already exists
    if log_path.exists():
        for line in log_path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                prev = json.loads(line)
            except Exception:
                continue
            if (prev.get("type") == "one-off-exception"
                    and prev.get("ruleId") == rule_id
                    and prev.get("variant") == variant):
                return False
    with log_path.open("a") as fh:
        fh.write(json.dumps(event) + "\n")
    return True


# ── orchestration ────────────────────────────────────────────────────────────────

def render_variant(doc, layout, brand_dir: Path, variant: str, out_dir: Path,
                   style_ctx: RenderContext | None = None) -> dict:
    hero = is_hero_layout(layout)
    cfg = variance_config(doc, variant, is_hero=hero)
    # POLICY GUARD (recipePolicy.magicTrick.wildcardScope = hero-only): the WILDCARD
    # one-off neverDo relaxation is permitted on HERO sections ONLY. This renderer is
    # hero-only by construction today, but assert it explicitly so any future non-hero
    # caller is blocked rather than silently relaxing a neverDo off-hero.
    assert not (cfg["relax"] and not hero), (
        f"wildcard neverDo relaxation requested for non-hero layout "
        f"'{layout.get('id')}' (archetype '{layout.get('archetype')}'): "
        "magicTrick.wildcardScope is hero-only")
    copy_block, asset_names, art = load_brand_copy(doc, brand_dir)
    COPY.update(copy_block)
    ASSET_SOURCES[:] = asset_names
    ART.update(art)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.html").write_text(build_html(doc, layout, cfg, style_ctx))
    copied = copy_assets(brand_dir, out_dir / "assets")
    logged = False
    if cfg["relax"]:
        logged = log_one_off_exception(
            brand_dir, cfg["relax"],
            note=("Variant C (WILDCARD) renders a filled accent CTA button instead of a "
                  "typographic arrow link — a one-off, bolder hero. Passive log only."),
            variant=variant.upper())
    return {
        "variant": variant.upper(), "name": cfg["name"], "relax": cfg["relax"],
        "logged": logged, "out": str(out_dir), "assets": copied,
        "style": style_ctx.style_id if (style_ctx and style_ctx.active) else None,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("brand_yaml", type=Path)
    ap.add_argument("--layout", default="opening-bookend", help="layout id to render")
    ap.add_argument("--variant", choices=list("ABCabc"), help="single variant to render")
    ap.add_argument("--all", action="store_true", help="render A, B, C into <out>/{a,b,c}")
    ap.add_argument(
        "--style", default=None,
        help="active STYLE id (e.g. radical-editorial). When omitted, the renderer's "
             "current behavior is preserved. When given, the style's STRUCTURE is layered "
             "over the brand's hues/fonts per the two-layer precedence rules.")
    ap.add_argument("-o", "--out", type=Path, required=True)
    args = ap.parse_args()

    doc = load_yaml(args.brand_yaml)
    load_contracts(doc, args.brand_yaml)  # validate/resolve contracts (referenced, not inlined)
    layout = layout_by_id(doc, args.layout)
    if layout is None:
        raise SystemExit(f"layout '{args.layout}' not found in {args.brand_yaml}")
    brand_dir = Path(args.brand_yaml).parent

    # Build the merged STYLE+BRAND render context (or an inactive one -> current behavior).
    if args.style:
        style_ctx = load_and_merge(args.style, doc)
        print(f"STYLE '{style_ctx.style_id}' active -> structure layered over brand "
              f"(paper={style_ctx.paper} ink={style_ctx.ink} accent={style_ctx.accent}; "
              f"display={style_ctx.structure.display_size_css()})")
        for n in style_ctx.notes:
            print(f"  note: {n}")
    else:
        style_ctx = inactive_context()

    variants = ["A", "B", "C"] if args.all else [args.variant.upper()] if args.variant else None
    if not variants:
        raise SystemExit("pass --variant A|B|C or --all")

    for v in variants:
        out = (args.out / v.lower()) if args.all else args.out
        res = render_variant(doc, layout, brand_dir, v, out, style_ctx)
        extra = ""
        if res["relax"]:
            extra = (f"  [relaxed neverDo:{res['relax']}; "
                     f"signals.log {'appended' if res['logged'] else 'already had entry'}]")
        if res["style"]:
            extra += f"  [style:{res['style']}]"
        print(f"Variant {res['variant']} ({res['name']}) -> {res['out']}/index.html"
              f" (assets: {', '.join(res['assets']) or 'none'}){extra}")


if __name__ == "__main__":
    main()
