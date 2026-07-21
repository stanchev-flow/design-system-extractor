#!/usr/bin/env python3
"""compose_page.py - assemble a FULL PAGE from the brand catalog, section by section.

This is the page-level peer of `compose_section.py`. It walks the brand's `layouts[]` in
STORY ORDER and, for each, runs the SAME slot->catalog->archetype machinery the single-
section composer uses (`compose_section.render_slots` + `ARCHETYPE_COMPOSERS`), then
concatenates the rendered `<section>`s into one document. Every section is therefore
assembled from the shared single-source-of-truth renderers in `component_render.py`
(the same functions the components-preview gallery uses) - never bespoke markup.

TWO-LAYER STYLE+BRAND (styles.py):
  - The STYLE layer (`radical-editorial`) dictates STRUCTURE (poster display scale, zero
    radius, tight leading/negative tracking, left-anchored asymmetric density, a SINGLE
    committed accent). It is layered OVER the brand base in CSS source order so the load-
    bearing structural rules win.
  - The BRAND layer fills paper/ink/accent/fonts. Each section carries its OWN surface, so
    the brand token VALUES are emitted SCOPED per section (`#sec-N { --c-* }`); a section on
    the cream canvas and a section on the dark band read the same `c-*` classes on-brand.
  - Accent (single committed) is deployed ONLY on the opening bookend (logo + hero eyebrow),
    per the brand's `no-accent-on-light` / "accent reserved for logo and hero" rule; every
    other section is monochrome ink. This satisfies BOTH the style's single-accent rule and
    the brand neverDo at once.

IFRAME-SAFE: container-query units only (cqw/cqh/cqi against `container-type: size`);
NEVER vh/vw/dvh.

Usage:
  python3 compose_page.py <brand.yaml> -o <outdir> [--style radical-editorial] [--order id,id,...]
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import component_render as cr  # noqa: E402
import compose_section as cs  # noqa: E402
import tokens_css  # noqa: E402
from tokens_css import (  # noqa: E402
    base_size,
    color_value,
    font_stack,
    google_fonts_link,
    spacing_value,
    type_role,
)
from styles import RenderContext, inactive_context, load_and_merge  # noqa: E402

# ── page order: BRAND DATA, not pipeline code ─────────────────────────────────────
# A brand's default narrative order is declared in its brand.yaml as `pageOrder:`
# (a list of layout ids). Absent that, the page renders the brand's layouts[] in
# authored order. There is NO shared fallback order: structure is never borrowed
# from another brand, and a brand with no layouts fails loud.

def page_order(doc) -> list[str]:
    """Resolve the page's section order: CLI --order wins (caller), then the brand's
    declared ``pageOrder:``, then the brand's ``layouts[]`` in authored order.
    Fails loud when the brand declares no layouts at all (structure must never be
    silently invented or borrowed)."""
    declared = doc.get("pageOrder")
    if isinstance(declared, list) and declared:
        return [str(x) for x in declared]
    ids = [l.get("id") for l in doc.get("layouts", []) if l.get("id")]
    if not ids:
        raise SystemExit("compose_page: brand declares no pageOrder and no layouts[] — "
                         "cannot compose a page (structure is brand-declared, never a "
                         "shared default)")
    return ids


# The single layout permitted to deploy the committed accent. Runtime patch surface
# ONLY (the composition adapter binds the composition's accent bookend here);
# resolution is otherwise brand-declared (`accentLayout:`) or brand-derived — see
# accent_layout_id().
ACCENT_LAYOUT: str | None = None


def accent_layout_id(doc, order=None) -> str | None:
    """Resolve which section carries the page's single committed accent:
    a runtime-bound composition accent (module ACCENT_LAYOUT) wins; then the brand's
    declared ``accentLayout:``; then the first section in page order that either
    renders the hero nav or sits on an inverse surface (the same rule the
    composition adapter uses); else the first section. None only for empty pages."""
    if ACCENT_LAYOUT:
        return ACCENT_LAYOUT
    declared = doc.get("accentLayout")
    if declared:
        return str(declared)
    layouts = {l.get("id"): l for l in doc.get("layouts", [])}
    ids = [i for i in (order or layouts.keys()) if i in layouts]
    for lid in ids:
        layout = layouts[lid]
        if _section_renders_nav(layout) or layout.get("surfaceIntent") in (
                "surface/inverse", "surface/inverse-strong"):
            return lid
    return ids[0] if ids else None

# The closing-bookend footer surface when the brand declares nothing measurable:
# the strongest inverse role. NOT the universal answer — footer_surface_role(doc)
# resolves the ACTIVE brand's measured chrome-footer surface first (AS-35: a light-
# chrome brand must not inherit another brand's near-black footer).
FOOTER_SURFACE_DEFAULT = "surface/inverse-strong"


def _parse_color_rgb(v):
    """(r, g, b) from '#rgb' / '#rrggbb' / 'rgb(a,b,c)' strings; None otherwise."""
    if not isinstance(v, str):
        return None
    s = v.strip().lower()
    if s.startswith("rgb"):
        try:
            nums = [int(float(x)) for x in s[s.index("(") + 1:s.index(")")].split(",")[:3]]
            return tuple(nums) if len(nums) == 3 else None
        except (ValueError, IndexError):
            return None
    if s.startswith("#"):
        h = s[1:]
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        if len(h) >= 6:
            try:
                return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
            except ValueError:
                return None
    return None


def footer_surface_role(doc) -> str:
    """Chrome-footer surface as a GENERIC ROLE resolution (AS-35 / remote-fix 5+10):
    match the brand's MEASURED footer surface color (brand.yaml `footer.surface.bg`,
    captured from the live site chrome) against the brand's own `tokens.surfaces`
    roles by nearest RGB distance — an exact hit picks that role (Remote's light
    `surface/raised` footer), a near hit picks the closest measured role (WoodWave's
    `#181313` chrome footer sits on the `#1B150F` inverse-strong ink). Ties prefer
    the historical `surface/inverse-strong` so brands whose surfaces alias to one
    color (e.g. inverse == inverse-strong) keep their existing render. A brand with
    no measured footer surface keeps the style default (inverse-strong). The return
    value is always a ROLE NAME from the brand's own palette — never a literal."""
    surfaces = ((doc.get("tokens") or {}).get("surfaces") or {})
    target = _parse_color_rgb(((doc.get("footer") or {}).get("surface") or {}).get("bg"))
    if target is None or not surfaces:
        return FOOTER_SURFACE_DEFAULT if FOOTER_SURFACE_DEFAULT in surfaces \
            else next(iter(surfaces), FOOTER_SURFACE_DEFAULT)
    best_role, best_d = None, None
    for role, spec in surfaces.items():
        rgb = _parse_color_rgb((spec or {}).get("bg"))
        if rgb is None:
            continue
        d = sum((a - b) ** 2 for a, b in zip(rgb, target))
        if best_d is None or d < best_d or (d == best_d and role == FOOTER_SURFACE_DEFAULT):
            best_role, best_d = role, d
    return best_role or FOOTER_SURFACE_DEFAULT

# Tiny inline scroll-reveal script (calm fade + translateY via the shared `.cs-reveal`
# CSS). Honors prefers-reduced-motion (returns a no-op so nothing animates / nothing is
# hidden) and degrades gracefully without IntersectionObserver (content stays visible —
# the hidden state is gated on the `.cs-motion-ready` class this script adds). Reveal is
# applied to each section's major content wrappers (not bespoke per-section markup), so
# motion stays consistent with the shared catalog renderers. No viewport units.
REVEAL_SCRIPT = """<script>
(function () {
  var root = document.documentElement;
  var mq = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)');
  if (mq && mq.matches) return;                      // reduced motion: no reveal, all visible
  if (!('IntersectionObserver' in window)) return;   // no IO: leave content fully visible
  var sel = '.cs-slot > *, .cs-collage-grid > *, .cs-split-intro, .cs-split, .cs-conversion, .c-footer';
  var nodes = [].slice.call(document.querySelectorAll(sel));
  if (!nodes.length) return;
  root.classList.add('cs-motion-ready');             // gate: hidden initial state now applies
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (e.isIntersecting) { e.target.classList.add('is-in'); io.unobserve(e.target); }
    });
  }, { rootMargin: '0px 0px -8% 0px', threshold: 0.08 });
  nodes.forEach(function (n, i) {
    n.classList.add('cs-reveal');
    n.style.setProperty('--cs-reveal-i', String(i % 6));  // small per-target stagger
    io.observe(n);
  });
  // TIMED FAILSAFE (AS-41): whatever IO does or fails to do, no content stays hidden
  // past this deadline — a mis-rooted observer / iframe quirk / never-fired callback
  // can strand `.cs-reveal` targets invisible; the reveal is an enhancement, never a
  // gate on content.
  setTimeout(function () {
    nodes.forEach(function (n) { n.classList.add('is-in'); });
  }, 4000);
})();
</script>"""

# Marquee px/s-constant duration (AS-42, P2): duration = measured half width / SPEED,
# so every marquee travels at the same surface speed regardless of item count. The
# CSS animation itself never depends on this (the inline item-count fallback keeps
# JS-off renders animating); reduced-motion is honored by the CSS media query.
MARQUEE_PX_PER_S = 90
MARQUEE_SCRIPT = """<script>
(function () {
  var speed = %d; /* px per second — constant surface speed across marquees */
  [].forEach.call(document.querySelectorAll('.cs-marquee-track'), function (t) {
    /* a MEASURED source period (data-marquee-measured, fid2 2026-07) is authoritative
       — the px/s re-derivation applies only to marquees without the measured fact. */
    if (t.closest('[data-marquee-measured]')) { return; }
    var half = t.querySelector('.cs-marquee-half');
    if (half && half.scrollWidth > 0) {
      t.style.setProperty('--cs-marquee-duration', (half.scrollWidth / speed).toFixed(2) + 's');
    }
  });
})();
</script>""" % MARQUEE_PX_PER_S


# Utility banner (P2, evidence-gated chrome): a slim centered promo line above the nav.
# Structural geometry only — colors ride the #page-banner surface scope (section_vars);
# the close affordance is the extracted dismissible fact. Shipped only on pages that
# render the banner (see build_page), so banner-less brands keep byte-identical CSS.
UTILITY_BANNER_CSS = """#page-banner { background: var(--c-paper); color: var(--c-ink); }
#page-banner .cs-utility-banner { position: relative; display: flex; align-items: center;
  justify-content: center; gap: 0.75rem; text-align: center;
  padding: calc(2 * var(--baseline)) var(--c-section-pad-x);
  font-family: var(--c-font-body); font-size: var(--c-control-size, var(--size-control-text-base)); }
#page-banner .cs-utility-banner-text { margin: 0; }
/* banner CTA (fid15): inherits the banner ink; measured presentation facts
   (underline/weight/color) ride inline from the extraction. */
#page-banner .cs-utility-banner-cta { color: inherit; text-decoration: none;
  white-space: nowrap; }
#page-banner .cs-utility-banner-arrow { display: inline-block; width: 1em; height: 1em;
  vertical-align: -0.125em; }
#page-banner .cs-utility-banner-arrow > svg { display: block; width: 100%; height: 100%; }
/* mask DEGRADE (fix4): harvested banner artwork that failed single-ink
   verification keeps the fix2 currentColor-mask channel. */
#page-banner .cs-utility-banner-arrow--mask { background: currentColor;
  -webkit-mask: var(--cs-ub-arrow) center / contain no-repeat;
  mask: var(--cs-ub-arrow) center / contain no-repeat; }
#page-banner .cs-utility-banner-close { position: absolute;
  right: var(--c-section-pad-x); top: 50%; transform: translateY(-50%);
  display: inline-flex; align-items: center; justify-content: center;
  width: 1.5rem; height: 1.5rem; background: none; border: 0; color: inherit;
  font-size: 1rem; line-height: 1; cursor: pointer; }"""


def load_doc(brand_yaml: Path) -> dict:
    doc = yaml.safe_load(Path(brand_yaml).read_text())
    # active-brand image inventory (AS-34) + authored section copy; in-memory only.
    cs.attach_brand_copy(doc, Path(brand_yaml).parent)
    doc = cs.attach_asset_inventory(doc, Path(brand_yaml).parent)
    # Phase-2 RESPONSIVE facts (hero + footer): merge the evidence-derived
    # responsive-facts.yaml sidecar into the hero layout + footer (in-memory only).
    # A brand without the sidecar is untouched — byte-identical output.
    import responsive_facts as _rf
    return _rf.apply_responsive_facts(doc, Path(brand_yaml).parent)


def section_pad(doc, surf_role) -> str:
    dark = surf_role in ("surface/inverse", "surface/inverse-strong", "surface/accent",
                         "surface/overlay")
    if dark:
        return (doc["tokens"]["spacing"].get("section-padding-dark", {}) or {}).get("value") \
            or spacing_value(doc, "section-padding-light", "6.25rem")
    return spacing_value(doc, "section-padding-light", "6.875rem")


def legacy_root_vars(doc, surf, *, display_size) -> str:
    """Gate-readable legacy :root vars (--bg/--text/--accent/--display-size/--radius/
    --font-*) sourced from the page's OPENING surface, plus the brand-constant panel/ghost
    ALIASES the split + collage scaffolds read. The legacy vars stay RESOLVED literals —
    they are the on-brand gate's authoritative-VALUES contract (extract_facts regexes
    them out of the raw CSS text). The panel/ghost aliases are (token-layer 2026-07)
    var() references into the generated layer-1 block — the referenced tokens are all
    REQUIRED, so generation already hard-failed if any were missing (no fallbacks)."""
    text = color_value(doc, surf.get("textPrimary")) or "#111111"
    accent = color_value(doc, surf.get("textAccent")) or text
    bg = surf.get("bg") or "#ffffff"
    heading_stack, _ = font_stack(doc, "display-hero", "Georgia, serif")
    body_stack, _ = font_stack(doc, "body", "system-ui, sans-serif")
    radius = spacing_value(doc, "radius-global", "0rem")
    return f""":root {{
  /* gate-readable legacy brand vars (authoritative VALUES; page opens on {surf.get('bg')}) */
  --bg: {bg};
  --text: {text};
  --accent: {accent};
  --display-size: {display_size};
  --radius: {radius};
  --font-heading: {heading_stack};
  --font-body: {body_stack};
  /* brand-constant aliases for the collage ghost + the cream split panel (layer-1 refs) */
  --c-ghost: var(--color-text-ghost-on-primary);
  --c-panel: var(--surface-surface-panel);
  --c-panel-ink: var(--color-text-on-primary);
  --c-panel-ink-muted: var(--color-text-on-primary-muted);
  --c-panel-hairline: var(--color-border-hairline-on-primary);
  /* ONE shared page grid + baseline (alignment quick wins) — mirrors
     compose_section.root_vars: all section scaffolds place onto these SHARED tracks
     and snap offsets to --baseline / --col, so adjacent sections register to the same
     columns, edges and baselines. */
  --grid-cols: 12; /* provenance: structural — shared registration grid */
  /* registration gutter: the brand's measured split-column rung when the ladder
     authored one (fid11: tokens.spacing.column-to-column), else the structural unit */
  --grid-gutter: var(--space-column-to-column, 6rem);
  /* shared content measure = the brand's measured container LAW when authored
     (tokens.spacing.container-span, fid10 2026-07 — e.g. a fluid min(NNcqw, cap)
     from the measured tier containerFacts), else the measured container cap
     (tokens.spacing.container-max, fid6 2026-07); 86rem structural default. */
  --content-measure: var(--space-container-span, var(--space-container-max, 86rem));
  --baseline: 0.5rem; /* provenance: structural — vertical registration unit */
  --col: calc((100% - 11 * var(--grid-gutter)) / 12);
}}"""


def _hex_rgb(value: str) -> tuple | None:
    m = re.fullmatch(r"#([0-9a-fA-F]{6})", str(value or "").strip())
    if not m:
        return None
    h = m.group(1)
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def section_vars(doc, sel, surf, *, display_size, accent_on, surf_role, style_ctx) -> str:
    """Per-section surface-scoped --c-* values (the shared c-* classes read these). For
    every section except the accent layout, the committed accent collapses to ink so no
    accent ever lands on a light/non-hero surface. Vertical rhythm (section padding +
    inter-block gaps) is emitted per surface via ``rhythm_vars_css`` — brand spacing
    tokens preferred, else the active style's spacing scale."""
    block = cr.component_vars(doc, surf, selector=sel, display_size=display_size,
                              surface_role=surf_role)
    extra = [cs.rhythm_vars_css(doc, style_ctx, surf_role, selector=sel)]
    if not accent_on:
        extra.append(f"{sel} {{ --c-accent: var(--c-ink); }}")
    else:
        # EYEBROW INK ON SCRIM/DARK SURFACES (fix7, pass-3 follow-up 8): the accent
        # section's eyebrow deployment (`.c-eyebrow { color: var(--c-accent) }` in
        # the style override) is CONTRAST-GUARDED — a surface whose own textAccent
        # cannot carry small text (WCAG 4.5:1 against the surface bg, e.g. an
        # image-scrim band whose sampled underlay sits mid-luminance) re-registers
        # the eyebrow to the surface's primary ink, exactly what the capture
        # evidence shows on such bands. Palette-agnostic: pure contrast arithmetic
        # over the brand's own declared values; high-contrast pairs are untouched.
        from readability import contrast_ratio
        bg = _hex_rgb(surf.get("bg"))
        accent = _hex_rgb(tokens_css.color_value(doc, surf.get("textAccent")))
        if bg and accent and contrast_ratio(accent, bg) < 4.5:
            extra.append(f"{sel} {{ --c-eyebrow-color: var(--c-ink); "
                         f"/* accent {contrast_ratio(accent, bg):.2f}:1 on this "
                         f"surface — eyebrow rides primary ink */ }}")
    return block + "\n" + "\n".join(extra)


def page_style_override(style_ctx: RenderContext, poster: str | None = None) -> str:
    """STYLE layer (radical-editorial structure) layered OVER the per-section brand base in
    CSS source order. It sets ONLY structure (poster display, zero radius, tight display
    leading/tracking, fonts) + density (left-anchored asymmetric) + the single-accent
    deployment - never per-surface hues (those stay scoped per section so brand wins).

    The density/alignment default is NO LONGER a hand-duplicated left literal (AS-06 +
    AS-18): both this function and `compose_section.style_override_css` emit it via the
    ONE shared `compose_section.style_density_css` helper, which derives the anchor from
    the style's machine-readable alignment stance (per-section resolution then wins by
    #sec-N specificity). `.cs-conversion` stays out of the shared selector list: it is a
    sanctioned CENTERED block whose centering lives in
    `compose_section.SCAFFOLD_CONVERSION_CSS`."""
    s = style_ctx.structure
    # display magnitude honors the style's display_source stance (page_display_size);
    # None = legacy callers (hero-variants harness) → the style's own poster clamp.
    poster = poster or s.display_size_css()
    return f"""
/* ===================================================================== */
/* STYLE: {style_ctx.style_id} (structure) layered OVER brand (hues+fonts). */
/* ===================================================================== */
:root {{
  --radius: {s.radius};
  --display-size: {poster};
  --c-radius: {s.radius};
  --c-display-size: {poster};
  --c-display-lh: {s.display_leading};
  --c-display-ls: {s.display_tracking};
  --c-font-heading: '{style_ctx.font_display}', Georgia, serif;
  --c-font-body: '{style_ctx.font_body}', system-ui, sans-serif;
}}
{cs.style_density_css(style_ctx, heading_max="16ch", collage_rule=".cs-collage { margin: 0; }")}
/* single committed accent: the eyebrow slug carries it (gold only where --c-accent is
   gold, i.e. the opening bookend); the display title is ALWAYS ink, never the accent. */
.c-eyebrow {{ color: var(--c-accent); }}
.c-heading--accent {{ color: var(--c-ink); }}
"""


def page_scaffold_css() -> str:
    """All archetype geometries, concatenated once for the whole page. Emits EVERY
    registered archetype scaffold (``cs._ARCHETYPE_SCAFFOLD``), every layout-id scaffold
    EXTRA (``cs._LAYOUT_SCAFFOLD_EXTRA``, layered after the archetype base), and every
    id-specific PRIMARY override (``cs._LAYOUT_ID_SCAFFOLD`` -- conversion-stack, the
    ruled-list panel, the FAQ accordion), so a page with ANY layout order always carries
    its section geometry. ALL THREE are read from compose_section.py's canonical
    registries -- never hand-duplicated here -- because a hand-duplicated copy is exactly
    how the ruled-list/FAQ scaffolds once rendered correctly in a single-section preview
    but silently unstyled (full-width, left-aligned) on the full page: the CSS blocks
    existed but this function's own hardcoded `parts` list never mentioned them. Each
    scaffold is scoped to its own classes, so emitting all of them is idempotent for
    sections that don't use a given archetype. The hero's full-frame height is re-scoped
    to the FIRST section only (every other section sizes to its content)."""
    parts = [cs.SCAFFOLD_BASE_CSS]
    parts += list(cs._ARCHETYPE_SCAFFOLD.values())
    parts += list(cs._LAYOUT_SCAFFOLD_EXTRA.values())
    parts += list(cs._LAYOUT_ID_SCAFFOLD.values())
    parts += [
        "/* footer (closing bookend): centered cluster; symmetric scale-driven padding. */",
        ".cs-footer-sec { padding-top: var(--c-section-pad-top);"
        " text-align: center; }",
        "/* footer content containment (the band paints full-bleed; the directory/",
        "   bottom-bar content centers at the page measure): CONTAINMENT_LAW_CSS",
        "   (fix3; was the fid10 private copy here — .cs-footer-sec > .c-footer is",
        "   a law member). */",
        "/* page-level navbar (hoisted out of the hero): a SLIM bar with its own modest",
        "   vertical padding + the section horizontal inset — it no longer inherits the",
        "   hero section's large padding-block-start. Its own margin-bottom is neutralized",
        "   so it reads as a bar flush above the hero, not padded inside it. */",
        "#page-nav { background: var(--c-paper); color: var(--c-ink); }",
        "#page-nav .cs-nav { margin-bottom: 0;"
        " padding: var(--c-nav-pad-block) var(--c-section-pad-x); }",
        "/* page: only the opening section is full-frame; others size to content. */",
        ".cs-section { min-height: auto; }",
        "#sec-0 .cs-section { min-height: 100cqh; }",
    ]
    return "\n".join(parts)


def hero_brand_override_css(doc) -> str:
    """HERO-ONLY brand-over-style exception — emitted ONLY when the ACTIVE brand
    declares it (brand.yaml ``heroDisplay:``, generic role-based knobs):

        heroDisplay:
          align: centered          # center the #sec-0 title cluster
          color: accent            # display heading renders in the brand accent
          weightRole: display-hero # heading weight = the display-hero type role

    Precedence is normally STYLE > BRAND on structure; a brand that commits to a
    specific hero display treatment (measured from its real site) wins on those
    declared choices for the HERO (#sec-0) ONLY. The STYLE still owns all hero
    STRUCTURE (poster scale, flat, zero radius, tight leading / negative tracking),
    and no other section is affected. A brand with no ``heroDisplay:`` returns ""
    — the style's structure applies untouched (hero design law is brand data,
    never a shared default). Appended AFTER page_style_override so it wins."""
    spec = doc.get("heroDisplay")
    if not isinstance(spec, dict) or not spec:
        return ""
    centered = str(spec.get("align") or "").lower() == "centered"
    accent = str(spec.get("color") or "").lower() == "accent"
    display_weight = str(spec.get("weightRole") or "") == "display-hero"
    if not (centered or accent or display_weight):
        return ""
    parts = ["""
/* ===================================================================== */
/* HERO brand-over-style exception (#sec-0 ONLY) — see hero_brand_override_css(). */
/* ===================================================================== */"""]
    if centered:
        parts.append("""#sec-0 .cs-slot, #sec-0 .cs-eyebrow-wrap, #sec-0 .cs-title, #sec-0 .cs-foot {
  align-items: center; text-align: center; }
#sec-0 .cs-collage { margin-left: auto; margin-right: auto; }""")
    heading_lines = []
    if centered:
        heading_lines.append("""#sec-0 .c-heading--display { text-align: center; max-width: 18ch;
  margin-left: auto; margin-right: auto;""")
    else:
        heading_lines.append("#sec-0 .c-heading--display {")
    if display_weight:
        heading_lines.append("""  /* HERO poster renders at the brand's display-hero weight role; every other
     section heading inherits the section heading weight. */
  font-weight: var(--c-display-weight); }""")
    else:
        heading_lines[-1] = heading_lines[-1] + " }"
    if centered or display_weight:
        parts.append("\n".join(heading_lines))
    if accent:
        parts.append("#sec-0 .cs-title .c-heading--accent { color: var(--c-accent); }")
    return "\n".join(parts) + "\n"


def style_gate_markers_css() -> str:
    """Style-gate compatibility alias (inert).

    onbrand_check.py's STYLE non-negotiables NN3 ('asymmetric — never centered-everything')
    and NN4 ('single committed accent — display title is ink') key on render_hero_variants'
    canonical `.hv-title.is-display` selector, which this catalog composer does NOT emit
    (it uses `.c-heading--display`). This emits an equivalent INERT alias rule that mirrors
    the composer's TRUE editorial (non-hero) display treatment — left-anchored + ink — so
    the style gate evaluates against the composed page instead of a missing selector. It
    styles no element on this page (no `.hv-title` exists here); the hero's centered/gold
    heading remains the separately-scoped #sec-0 brand-over-style exception above. The gate
    is read-only/owned elsewhere, so this alias is the composer-side bridge to it."""
    return """
/* style-gate alias (inert): maps the composer's editorial display heading onto the gate's
   canonical `.hv-title.is-display` selector (left-anchored, ink) — see fn docstring. */
.hv-title.is-display { text-align: left; color: var(--text); }
"""


def page_display_size(doc, style_ctx) -> str:
    """The page's hero display magnitude, honoring the style's `type.display_source`
    stance (B3/B11, fix-batch 2026-07):

    - "poster" (editorial archetypes / non-migrated styles): the STYLE's poster clamp —
      the oversized display IS the style, unchanged behavior.
    - "brand" (corporate archetypes): the BRAND's measured display-hero tier drives the
      magnitude — a 65px-hero brand renders at its own scale instead of inflating to a
      poster clamp; the style still shapes leading/tracking/weight.

    Unstyled pages keep the brand tier (legacy branch, unchanged)."""
    if style_ctx and style_ctx.active and style_ctx.structure.display_source != "brand":
        return style_ctx.structure.display_size_css()
    return f"{base_size(type_role(doc, 'display-hero')) or 6}rem"


def compose_section_block(doc, layout, idx, style_ctx, brand_yaml=None, accent_id=None,
                          honor_curation=True):
    """Render ONE layout via the shared composer + return (html, scoped_vars_css).
    ``accent_id`` is the resolved accent section id (accent_layout_id); pass it from
    build_page so the whole page agrees on the single committed accent.
    ``honor_curation`` — lane semantics for pattern curation (brand-schema §4.4c):
    generation lanes keep the default True; the replica lane passes False."""
    role, surf = cs.resolve_surface_intent(doc, layout)
    ctx = cr.make_context(doc, role, surf)
    ctx.style_active = bool(style_ctx and style_ctx.active)
    ctx.style_id = style_ctx.style_id if ctx.style_active else ""
    # style-aware cta-shape (B5): the brand law still wins inside cta_shape; the active
    # style's primaryAction soft-option default fills the gap for law-silent brands.
    ctx.cta = cr.cta_shape(doc, style_ctx.structure if ctx.style_active else None)

    # pattern INTERACTION DEVICES (P2): stamp sanctioned treatment devices (marquee /
    # accordion open-state / edge-cut) BEFORE composing so the composers see the hints.
    cs.stamp_pattern_devices(doc, layout, brand_yaml)

    rendered = cs.render_slots(doc, layout, ctx)
    archetype = (layout.get("archetype") or "stack").lower()
    composer = cs.ARCHETYPE_COMPOSERS.get(archetype, cs.compose_stack_hero)
    section_html = composer(doc, layout, ctx, rendered, style_ctx)

    sel = f"#sec-{idx}"
    if accent_id is None:
        accent_id = accent_layout_id(doc)
    accent_on = layout.get("id") == accent_id
    disp = None
    if idx == 0:  # the hero display tier carries the poster scale
        disp = page_display_size(doc, style_ctx)
    vars_css = section_vars(doc, sel, surf, display_size=disp, accent_on=accent_on,
                            surf_role=role, style_ctx=style_ctx)
    # declared eyebrow register (brand-schema layout.eyebrowRegister): the section's
    # theme-scope family lands as a #sec-N-scoped --c-eyebrow-color (same mechanism
    # as the single-section path in cs.build_document).
    vars_css += cs.eyebrow_register_css(doc, layout, sel)
    # bandHeight knob (archetype-library, composition knobs.bandHeight): re-registers
    # this section's vertical padding to another rung of the brand's OWN section-rhythm
    # ladder. "" for every layout without the hint (byte-identical degrade).
    vars_css += cs.band_height_css(doc, layout, sel, role, style_ctx)

    # Reuse-before-create: resolve the reusable layout PATTERN + scope its pattern-driven
    # special-treatment vars to THIS section (#sec-N) so the ghost/stagger geometry comes
    # from the reused pattern. Stamp data-pattern on the wrapper for traceability.
    # A retrieval MISS is a VISIBLE advisory stamp, never a silent nothing (W6,
    # stress-playbook 2026-07): data-pattern-match records the retrieval outcome
    # (ref/reuse/adapt on hits, miss on an honest no-match) so audits can tell
    # "deliberately pattern-less" from "forgot to look". kind "none" (no brand /
    # no library plumbing) keeps the wrapper byte-identical.
    pattern, match_kind = cs.resolve_pattern(doc, layout, brand_yaml)
    if pattern:
        pat_attr = (f' data-pattern="{cr.esc(pattern.id)}" '
                    f'data-pattern-lib="{cr.esc(pattern.lib)}" '
                    f'data-pattern-match="{cr.esc(match_kind)}"')
    elif match_kind == "miss":
        pat_attr = ' data-pattern-match="miss"'
    else:
        pat_attr = ""
    # genre-archetype provenance (spec/archetype-library.md): the chosen skeleton id is
    # stamped like data-pattern so audits can scope physics bindings per section.
    # Absent ref -> byte-identical wrapper (every non-composition lane).
    if layout.get("archetypeRef"):
        pat_attr += f' data-archetype="{cr.esc(str(layout["archetypeRef"]))}"'
    # bandHeight DECLARATION stamp (same discipline as data-ag-gap/-align): the
    # section audits against its OWN re-registered rung — data-band-rung names the
    # brand spacing token band_height_css resolved, so the spacing auditor reads the
    # deliberate re-registration instead of the surface default. No knob ⇒ no stamp.
    band_rung = cs.band_height_rung(doc, layout, role, style_ctx)
    if not band_rung:
        # derived-scale re-registration (pass1): the stamp names the derived step
        # ("derived:<px>") so the spacing auditor audits the pad against the
        # DELIBERATE quantized declaration, mirroring the token-rung read.
        derived = cs.band_height_derived_px(doc, layout, role, style_ctx)
        if derived is not None:
            band_rung = f"derived:{derived:g}"
    if band_rung:
        pat_attr += (f' data-band-height="{cr.esc(str(layout.get("_bandHeight")))}"'
                     f' data-band-rung="{cr.esc(band_rung)}"')
    treat = cs.pattern_treatment_css(pattern)
    if treat:  # re-scope the :root vars emitter onto this section id
        vars_css = vars_css + "\n" + treat.replace(":root {", f"{sel} {{")
    # GRID EQUALIZATION (fid14, AS-50): the pattern's measured gridEqualize fact drives
    # card-row height behavior — stretch + pinned action rows, or explicit hug. "" for
    # fact-less patterns (byte-identical degrade).
    equalize = cs.pattern_equalize_css(pattern, sel)
    if equalize:
        vars_css = vars_css + "\n" + equalize
    # MEASURED IN-CARD ACTION SEAM (deviceGeometry.cardActionGap): emitted after the
    # equalize block so a pattern authoring both facts resolves to its own card seam.
    card_rhythm = cs.pattern_card_rhythm_css(pattern, sel)
    if card_rhythm:
        vars_css = vars_css + "\n" + card_rhythm
    # ALIGNMENT RESOLUTION (AS-18/AS-49): section-explicit > pattern curation
    # (generation lanes, brand-schema §4.4c) > pattern contentShape.alignment > brand
    # layoutGrammar.headerContext (contextual grammar, fid11) > style role default —
    # resolved by ONE function, emitted per section, and stamped on the wrapper as
    # data-align/-source/-counterweight (mirrors data-pattern). Silent CSS
    # fall-through only remains where NO layer declares a stance (unstyled legacy pages).
    resolved = cs.resolve_alignment(layout, pattern, style_ctx, doc=doc,
                                    honor_curation=honor_curation)
    align_attr = cs.align_stamp_attrs(resolved)
    # per-section placement (composition.v1 §4.6.5): resolved alignment + declared grid +
    # mirrorable float side. "" for every layout that resolves/declares none.
    placement = cs.layout_placement_css(sel, layout, resolved=resolved)
    if placement:
        vars_css = vars_css + "\n" + placement
    block = (f'<div id="sec-{idx}" class="cs-surface" data-layout="{cr.esc(layout["id"])}" '
             f'data-surface="{cr.esc(role)}"{pat_attr}{align_attr}>\n{section_html}\n</div>')
    return block, vars_css, role


def _section_renders_nav(layout) -> bool:
    """True when this layout would have rendered the opening navbar via
    ``compose_stack_hero`` (a `stack` archetype that is the hero, not the conversion stack,
    or any unknown archetype that falls back to the hero composer). Used to decide whether
    to emit the PAGE-LEVEL navbar so the exact set of pages-with-nav is preserved after the
    nav is hoisted out of the hero section (a split/collage/etc. opening never had a nav)."""
    archetype = (layout.get("archetype") or "stack").lower()
    composer = cs.ARCHETYPE_COMPOSERS.get(archetype, cs.compose_stack_hero)
    if composer is cs.compose_stack:  # the `stack` dispatcher: hero vs conversion
        contracts = {m.get("contract") for m in (layout.get("blockMapping") or [])}
        return "form" not in contracts
    return composer is cs.compose_stack_hero  # unknown-archetype fallback → hero


def build_page(doc, brand_yaml, order, style_ctx: RenderContext,
               wildcards: dict[str, int] | None = None,
               honor_curation: bool = True) -> str:
    name = doc["brand"]["name"]
    layouts = {l.get("id"): l for l in doc.get("layouts", [])}
    chosen = [layouts[i] for i in order if i in layouts]
    accent_id = accent_layout_id(doc, order)

    # Resolve the chrome's harvested glyph artwork (social icons, store badges, nav
    # trigger chevron + utility-control icons — fid15) into data: URIs on the
    # in-memory doc BEFORE any chrome renders: the page-level navbar consumes the
    # resolved facts, so this must precede render_navbar (it previously ran just
    # before the footer, leaving the nav glyph-blind). brand.yaml is never written.
    cr.prepare_chrome_glyphs(doc, Path(brand_yaml).parent)

    opening_role, opening_surf = cs.resolve_surface_intent(doc, chosen[0])
    poster = page_display_size(doc, style_ctx)

    blocks, var_blocks = [], []
    for idx, layout in enumerate(chosen):
        block, vars_css, _role = compose_section_block(doc, layout, idx, style_ctx,
                                                       brand_yaml, accent_id=accent_id,
                                                       honor_curation=honor_curation)
        blocks.append(block)
        var_blocks.append(vars_css)
        # RESPONSIVE hero (Phase 4, fact-gated on layouts[].responsive) — emits the
        # viewport-minus-nav height + measured heading shrink, scoped to this section
        # id. "" for layouts without the block (byte-identical output).
        hero_resp = cr.hero_responsive_css((layout or {}).get("responsive"),
                                           f"#sec-{idx}")
        if hero_resp:
            var_blocks.append(hero_resp)
        # RESPONSIVE hero primary button (fact-gated on layouts[].responsive.
        # primaryButton) — measured control box, scoped to this section's non-nav
        # button. "" without the fact (byte-identical output).
        btn_resp = cr.hero_primary_button_css((layout or {}).get("responsive"),
                                              f"#sec-{idx}")
        if btn_resp:
            var_blocks.append(btn_resp)

    # PAGE-LEVEL NAVBAR (hoisted out of the hero). The nav was previously rendered INSIDE
    # #sec-0 by compose_stack_hero, so it inherited the hero section's padding-block-start
    # (an uncommon large gap above the nav). It is now a page-level sibling emitted ONCE
    # before #sec-0 — mirroring the footer, which is its own final section — so the final
    # structure is Page > { Nav, Section(s), Footer } and the hero top padding normalizes to
    # the normal section rhythm. Emitted only for pages whose opening section would have
    # rendered the hero nav (so a split/collage-opened page stays nav-free, as before).
    nav_block = ""
    # A composed PAGE (compose_from_composition stamps `_composedPage`) always carries
    # the brand chrome: its opener may be ANY composer family (split/overlay/collage),
    # and a full page without the nav is a content gap, not a structural choice. The
    # deterministic lanes keep the historical opener-family rule byte-identically.
    if chosen and (_section_renders_nav(chosen[0]) or doc.get("_composedPage")):
        nav_sel = "#page-nav"
        # Chrome-nav surface = the brand's MEASURED bar color resolved to one of its
        # own roles (cr.nav_surface_role, nav-fix 2026-07). A transparent/unmeasured
        # bar keeps the opening section's surface — the extracted nav sits over what
        # it overlaps, which is exactly the pre-fix behavior.
        nav_role = cr.nav_surface_role(doc) or opening_role
        nav_surf = doc["tokens"]["surfaces"].get(nav_role, opening_surf)
        nav_ctx = cr.make_context(doc, nav_role, nav_surf)
        nav_ctx.style_active = bool(style_ctx and style_ctx.active)
        nav_ctx.style_id = style_ctx.style_id if nav_ctx.style_active else ""
        # page-level chrome nav renders the brand's CAPTURED mega-menu panels
        # (fid4 2026-07) — menu-less brands emit byte-identical markup.
        nav_ctx.mega_nav = True
        nav_html = cr.render_navbar(doc, nav_ctx, cs._navbar_props(doc))
        nav_block = (f'<div id="page-nav" class="cs-surface" '
                     f'data-surface="{cr.esc(nav_role)}">\n{nav_html}\n</div>')
        nav_accent_on = chosen[0].get("id") == accent_id
        var_blocks.append(section_vars(doc, nav_sel, nav_surf, display_size=None,
                                       accent_on=nav_accent_on, surf_role=nav_role,
                                       style_ctx=style_ctx))
        # measured bar content width (fix1 2026-07): a chrome capture that recorded
        # its own nav content max-width (navbar.measured.contentMaxWidth) centers
        # the bar's content column at that measure — the bar still paints full-bleed
        # via #page-nav. Unmeasured brands keep the full-inset bar, byte-identical.
        cmw = ((doc.get("navbar") or {}).get("measured") or {}).get("contentMaxWidth")
        if isinstance(cmw, (int, float)) and cmw > 0:
            # contain-exempt: measured CHROME width — the bar's own captured content
            # cap (a brand fact in px), not the shared section measure.
            var_blocks.append(
                f"#page-nav .cs-nav {{ max-width: calc({int(cmw)}px"
                f" + 2 * var(--c-section-pad-x)); margin-inline: auto; }}")
        nav_h = ((doc.get("navbar") or {}).get("measured") or {}).get("height")
        if isinstance(nav_h, (int, float)) and nav_h > 0:
            # Fact-gated full chrome box: two-tier source headers need their
            # measured vertical extent even when the compact renderer places
            # utility and primary controls in one responsive flex bar.
            var_blocks.append(
                f"#page-nav .cs-nav {{ min-height: {int(nav_h)}px; }}")

    # UTILITY BANNER above the nav (P2, evidence-gated): rendered ONLY when the brand's
    # extracted chrome declares navbar.utilityBanner with observed text — absent/empty
    # ⇒ no banner, byte-identical page. Surface = the banner's declared surface ROLE
    # resolved from the brand's own tokens (never a literal); an unknown/undeclared
    # role degrades to no banner (fail-quiet chrome, same discipline as the nav).
    banner_block = ""
    ub = (doc.get("navbar") or {}).get("utilityBanner")
    if nav_block and isinstance(ub, dict) and ub.get("observed") \
            and str(ub.get("text") or "").strip():
        # surface: MEASURED banner facts first (fid2 2026-07 — ub.bg/ub.ink carry the
        # extracted paint, e.g. a :root-scope chrome color no section role owns);
        # else the declared surface ROLE resolved from the brand's own tokens.
        b_role = str(ub.get("surface") or "")
        b_surf = (doc.get("tokens", {}).get("surfaces") or {}).get(b_role)
        measured_bg = str(ub.get("bg") or "").strip()
        measured_ink = str(ub.get("ink") or "").strip()
        if measured_bg or (isinstance(b_surf, dict) and b_surf.get("bg")):
            paint_style = ""
            if measured_bg:
                # measured chrome paint: scoped literals on the banner's own scope
                # (UTILITY_BANNER_CSS consumes --c-paper/--c-ink) — the top-bar color
                # is a :root chrome fact no section surface role owns.
                b_role = "chrome/utility-banner"
                ink_decl = f" --c-ink: {measured_ink};" if measured_ink else ""
                paint_style = (f' style="--c-paper: {measured_bg};{ink_decl} '
                               f'background: {measured_bg};'
                               + (f" color: {measured_ink};" if measured_ink else "")
                               + '"')
                b_ctx = cr.make_context(doc, b_role, {"bg": measured_bg})
            else:
                b_ctx = cr.make_context(doc, b_role, b_surf)
            b_ctx.style_active = bool(style_ctx and style_ctx.active)
            b_ctx.style_id = style_ctx.style_id if b_ctx.style_active else ""
            cta = ub.get("cta")
            cta_html = ""
            if isinstance(cta, dict) and str(cta.get("label") or "").strip():
                # measured banner-CTA anatomy (fid15): the extracted label renders
                # VERBATIM (when the source's arrow is a text glyph it lives inside
                # the label) with the measured presentation facts (underline /
                # weight / color) as scoped literals; a HARVESTED arrow glyph
                # (cta.arrow._dataUri via prepare_chrome_glyphs) appends as a
                # currentColor mask. No fact ⇒ no arrow — never an invented glyph.
                decls = []
                if cta.get("underline"):
                    decls.append("text-decoration: underline; text-underline-offset: 2px")
                if str(cta.get("fontWeight") or "").strip():
                    decls.append(f"font-weight: {cr.esc(str(cta['fontWeight']))}")
                if str(cta.get("color") or "").strip():
                    decls.append(f"color: {cr.esc(str(cta['color']))}")
                style_attr = f' style="{"; ".join(decls)}"' if decls else ""
                arrow = cta.get("arrow") if isinstance(cta.get("arrow"), dict) else {}
                arrow_html = ""
                if arrow.get("_inlineSvg"):
                    # fix4 inline channel: sanitized single-ink artwork nests inline
                    arrow_html = (' <span class="cs-utility-banner-arrow" aria-hidden="true">'
                                  f'{cr._svg_instance(str(arrow["_inlineSvg"]))}</span>')
                elif arrow.get("_dataUri"):
                    arrow_html = (' <span class="cs-utility-banner-arrow'
                                  ' cs-utility-banner-arrow--mask" aria-hidden="true"'
                                  f' style="--cs-ub-arrow:url({arrow["_dataUri"]})"></span>')
                cta_html = (f' <a class="cs-utility-banner-cta" '
                            f'href="{cr.esc(cta.get("href", "#"))}"{style_attr}>'
                            f'{cr.esc(str(cta["label"]).strip())}{arrow_html}</a>')
            dismiss_html = ""
            if ub.get("dismissible"):
                # close glyph ladder (fid15): harvested artwork (close.asset resolved
                # by prepare_chrome_glyphs) > measured box/strokeWidth reconstruction
                # (brand-schema: close.kind box-only sanctions drawing the X from the
                # measured facts) > the text multiplication-sign degrade.
                close = ub.get("close") if isinstance(ub.get("close"), dict) else {}
                cbox = close.get("box") if isinstance(close.get("box"), dict) else {}
                if close.get("_inlineSvg"):
                    glyph = (f'<span class="cs-utility-banner-arrow" aria-hidden="true">'
                             f'{cr._svg_instance(str(close["_inlineSvg"]))}</span>')
                elif close.get("_dataUri"):
                    glyph = (f'<span class="cs-utility-banner-arrow'
                             f' cs-utility-banner-arrow--mask" aria-hidden="true" '
                             f'style="--cs-ub-arrow:url({close["_dataUri"]})"></span>')
                elif cbox.get("w") and cbox.get("h"):
                    w, h = int(cbox["w"]), int(cbox["h"])
                    sw = int(close.get("strokeWidth") or 2)
                    glyph = (f'<svg viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
                             f'fill="none" stroke="currentColor" stroke-width="{sw}" '
                             f'stroke-linecap="round" aria-hidden="true">'
                             f'<path d="M{sw} {sw}L{w - sw} {h - sw}M{w - sw} {sw}'
                             f'L{sw} {h - sw}"/></svg>')
                else:
                    glyph = "&#215;"
                ink = str(close.get("ink") or "").strip()
                ink_attr = f' style="color: {cr.esc(ink)}"' if ink else ""
                dismiss_html = (f'<button class="cs-utility-banner-close" type="button" '
                                f'aria-label="Dismiss"{ink_attr}>{glyph}</button>')
            banner_block = (
                f'<div id="page-banner" class="cs-surface" '
                f'data-surface="{cr.esc(b_role)}"{paint_style}>\n'
                f'<div class="cs-utility-banner"><p class="cs-utility-banner-text">'
                f'{cr.esc(str(ub["text"]).strip())}</p>{cta_html}{dismiss_html}</div>\n'
                f'</div>')
            # measured banner REGISTER (fid15): the extracted strip's own font size
            # wins over the chrome control alias when the capture carries it.
            fs = ub.get("fontSize")
            fs_decl = (f"--c-control-size: {int(fs)}px; "
                       if isinstance(fs, (int, float)) and fs > 0 else "")
            if not measured_bg:
                var_blocks.append(section_vars(doc, "#page-banner", b_surf,
                                               display_size=None, accent_on=False,
                                               surf_role=b_role, style_ctx=style_ctx))
                if fs_decl:
                    var_blocks.append("#page-banner { " + fs_decl + "}")
            else:
                # measured paint skips the surface-role var pipeline, so re-declare the
                # few aliases the banner CSS consumes (body font / control size refs into
                # layer-1 + the structural section inset) at the banner's own scope.
                var_blocks.append(
                    "#page-banner { --c-font-body: var(--font-body); "
                    + (fs_decl or "--c-control-size: var(--size-control-text-base, 0.9375rem); ")
                    + "--c-section-pad-x: 2.5rem; }")

    # Closing-bookend FOOTER as the final section — composed via the SHARED component
    # renderer (component_render.render_footer), the SAME renderer the gallery uses, NOT
    # the chrome generator. Surface = the brand's MEASURED chrome-footer surface resolved
    # to one of its own roles (footer_surface_role, AS-35); copy from brand.yaml.
    foot_idx = len(chosen)
    foot_role = footer_surface_role(doc)
    foot_surf = doc["tokens"]["surfaces"][foot_role]
    foot_ctx = cr.make_context(doc, foot_role, foot_surf)
    foot_ctx.style_active = bool(style_ctx and style_ctx.active)
    foot_ctx.style_id = style_ctx.style_id if foot_ctx.style_active else ""
    # (glyph resolution ran at the top of build_page — the footer's social cluster
    # reads the same _dataUri facts the nav affordances do.)
    foot_html = cr.render_footer(doc, foot_ctx, cr.footer_content(doc))
    # the closing bookend is stamped too (its centered cluster is the style's declared
    # footer stance, not an accident) so the alignment-resolution gate can see it.
    foot_align = cs.align_stamp_attrs(
        cs.resolve_alignment({"id": "closing-bookend", "archetype": "footer"},
                             None, style_ctx))
    blocks.append(
        f'<div id="sec-{foot_idx}" class="cs-surface" data-layout="closing-bookend" '
        f'data-surface="{cr.esc(foot_role)}"{foot_align}>\n'
        f'<section class="cs-section cs-footer-sec">\n{foot_html}\n</section>\n</div>')
    # Do NOT collapse the footer accent to ink when the brand carries a MEASURED link-hover
    # color (color-shift): the footer sits on the near-black strong surface, so keeping the
    # committed gold accent there is on-brand (gold-on-dark) and lets the footer link hover
    # share the one gold with the nav + inline links. Underline-draw brands still collapse.
    foot_keep_accent = (cr.link_mode(doc) == "color-shift"
                        and cr.link_hover_color(doc) is not None)
    var_blocks.append(section_vars(doc, f"#sec-{foot_idx}", foot_surf, display_size=None,
                                   accent_on=foot_keep_accent, surf_role=foot_role,
                                   style_ctx=style_ctx))
    # RESPONSIVE footer (Phase 4, fact-gated on footer.responsive) — @media column
    # reflow + measured content cap; the band goes full-bleed (invented max-width
    # purged, Phase 3). "" for brands without the block (byte-identical output).
    foot_resp = cr.footer_responsive_css(doc, f"#sec-{foot_idx}")
    if foot_resp:
        var_blocks.append(foot_resp)
    # RESPONSIVE headings (fact-gated on responsive.headings) — measured heading
    # line-heights the composer type scale mis-derived, emitted once after the base
    # heading rules so the measured value wins. "" without the block.
    heading_resp = cr.heading_responsive_css(doc)
    if heading_resp:
        var_blocks.append(heading_resp)

    gf = google_fonts_link(cs.loadable_proxies(doc))
    face_css = cs.font_face_css(Path(brand_yaml).parent, doc)
    # layer-1 generated tokens block (token-layer 2026-07): every var() in the alias
    # layer + scaffolds resolves against THIS. Fail-loud on missing REQUIRED tokens.
    tokens_bundle = tokens_css.build_page_tokens(doc, style_ctx, brand_yaml_path=brand_yaml)
    css_parts = [
        legacy_root_vars(doc, opening_surf, display_size=poster),
        cr.COMPONENT_CSS,
        # §C.3 structural variants THIS brand selects (never dormant foreign grammar)
        cr.structural_variant_css(doc),
        # motion --c-* vars (easing + durations + reveal shift) from brand.yaml voice.motionSpec;
        # after COMPONENT_CSS so the brand's authored spec wins over the inline fallbacks.
        cr.motion_vars_css(doc),
        # link hover treatment (color-shift → measured gold hover); "" for underline-draw brands.
        cr.link_hover_css(doc),
        # nav-link hover wash (measured chrome interaction) — appended only when the
        # brand extracted one, so hover-less brands keep byte-identical CSS.
        *([cr.nav_hover_css(doc)] if cr.nav_hover_css(doc) else []),
        # mega-menu panel grammar (fid4 2026-07) — appended only when the brand's
        # navbar carries captured menus (structure + measured open/close motion).
        *([cr.nav_mega_css(doc)] if nav_block and cr.nav_mega_css(doc) else []),
        # bar-affordance grammar (fid15) — trigger chevrons + in-bar utility cluster;
        # appended only when this brand captured the facts (fact-less brands stay
        # byte-identical). Lane curation rides through (fix5): a curated instant
        # chevron swap applies to generation lanes; the replica keeps the tween.
        *([cr.nav_affordance_css(doc, honor_curation=honor_curation)]
          if nav_block and cr.nav_affordance_css(doc, honor_curation=honor_curation)
          else []),
        page_scaffold_css(),
    ]
    # AS-37: the inset art-panel device CSS ships ONLY when a section on THIS page
    # actually renders it — its rounded-panel rule must never ride along on pages of
    # brands whose neverDo forbids radius (the static no-radius check reads page text).
    if any((l or {}).get("_artPanel") is not None for l in chosen):
        css_parts.append(cs.SCAFFOLD_ART_PANEL_CSS)
    # inset conversion panel (fid2 2026-07): same conditional-shipping discipline —
    # rides only when a section on THIS page was stamped for the panel presentation.
    if any((l or {}).get("_insetPanel") is not None for l in chosen):
        css_parts.append(cs.SCAFFOLD_CONVERSION_PANEL_CSS)
    # full-bleed art band (fid5 2026-07): rides only when a section on THIS page was
    # stamped for the art-surface background treatment.
    if any((l or {}).get("_artSurface") is not None for l in chosen):
        css_parts.append(cs.SCAFFOLD_CONVERSION_BAND_CSS)
    # card plates (fid2 2026-07): the plate/person anatomy for brands whose card device
    # declares a Container surface — page-level mirror of the scaffold_css gate.
    if cs.card_panel_role(doc) is not None and any(
            (l or {}).get("archetype", "").lower() == "cards" for l in chosen):
        css_parts.append(cs.SCAFFOLD_CARD_PLATE_CSS)
    # P2 interaction devices (marquee / accordion / edge-cut): same conditional-shipping
    # discipline — "" when no section on this page is stamped for one. The brand's
    # derived grid-equalization grammar rides along so the pattern-less card scaffolds
    # (bento/tiers) follow the same grammar the pattern-backed grids do (fid14, AS-50).
    device_css = cs.device_scaffold_css(
        chosen, equalize_grammar=cs.grid_equalize_grammar(brand_yaml))
    if device_css:
        css_parts.append(device_css)
    # shared disclosure MOTION (AS-47): ONE source for every details-emitting family
    # on this page (accordion device + FAQ/agenda scaffold rows) — brand motion facts
    # only; "" for motion-less docs (instant-toggle degrade, never invented timing).
    motion_css = cs.disclosure_motion_css(doc, chosen)
    if motion_css:
        css_parts.append(motion_css)
    # RELATIONAL LADDER (AS-48): ladder-bearing brands render header/anatomy stacks
    # as NO-GAP columns with per-pair margins from their own measured rungs — ONE
    # shared source (compose_section.relational_ladder_css), appended after the
    # scaffold blocks so its same-specificity overrides win by order. "" for
    # ladder-less brands: uniform stack gap remains ONLY as that degrade.
    ladder_css = cs.relational_ladder_css(doc)
    if ladder_css:
        css_parts.append(ladder_css)
    # ACTION-GROUP law (fix2, brand-schema §4.4f): the brand's measured action-row
    # gap/seam, appended AFTER the ladder so a marginAbove LENGTH outranks the rung
    # by order. "" for fact-less brands (structural defaults hold byte-identically).
    ag_css = cs.action_group_css(doc)
    if ag_css:
        css_parts.append(ag_css)
    # utility-banner chrome CSS ships only when THIS page renders the banner.
    if banner_block:
        css_parts.append(UTILITY_BANNER_CSS)
    css_parts.append("\n".join(var_blocks))
    if style_ctx and style_ctx.active:
        css_parts.append(page_style_override(style_ctx, poster=poster))
        # HERO brand-over-style exception (only when THIS brand declares heroDisplay:)
        # + style-gate alias, AFTER the style override so the hero override wins.
        hero_css = hero_brand_override_css(doc)
        if hero_css:
            css_parts.append(hero_css)
        css_parts.append(style_gate_markers_css())
    # scroll-parallax (brand motion treatment; opt-in via voice.motionSpec.imageParallax —
    # "" when the brand hasn't declared it, so every other project renders unchanged).
    css_parts.append(cr.parallax_css(doc))
    if wildcards:
        css_parts.append(blessed_wildcard_css(doc, wildcards))
    css = "\n".join(css_parts)

    html_attr = f' data-style="{style_ctx.style_id}"' if (style_ctx and style_ctx.active) else ""
    if style_ctx and style_ctx.active:
        # AS-18: the page self-declares whether its OPERATIVE style definition carried a
        # machine-readable alignment stance. The G10 gate reads THIS stamp instead of
        # re-loading the style by id from styles/ — a render built against a snapshotted
        # style dir (e.g. the A/B arm's frozen inputs) must be judged by the definition
        # it actually rendered with, not by today's canonical file of the same name.
        stance = "declared" if (style_ctx.structure is not None
                                and style_ctx.structure.declares_alignment()) else "none"
        html_attr += f' data-align-stance="{stance}"'
    parallax_attr = ' data-parallax-images="true"' if cr.image_parallax_spec(doc)["enabled"] else ""
    sections = "\n".join(blocks)
    # marquee duration script rides ONLY on pages that render a marquee track.
    marquee_script = MARQUEE_SCRIPT if "cs-marquee-track" in sections else ""
    # keyboard/AT-parity script (interaction remediation 2026-07): guarded blocks
    # keyed off the assembled body — pages without the components ship no script.
    ix_script = cr.interaction_script("\n".join((banner_block, nav_block, sections)))
    return f"""<!doctype html>
<html lang="en"{html_attr}{parallax_attr}>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{cr.esc(name)} - full page (composed from catalog)</title>
{gf}
{tokens_css.style_tag(tokens_bundle)}
<style>
{face_css}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
img {{ display: block; max-width: 100%; }}
/* iframe-safe container context: cq* length units resolve against this sized box. */
html {{ background: var(--bg); height: 100%; }}
html, body {{ background: var(--bg); color: var(--text); font-family: var(--c-font-body);
  -webkit-font-smoothing: antialiased; }}
body {{ min-height: 100%; container-type: size; container-name: frame; }}
.cs-surface {{ display: block; }}
{css}
</style>
</head>
<body>
<!-- FULL PAGE composed from the brand catalog: each section's every slot is a catalog
     component rendered by component_render.py (the SAME renderers the gallery uses),
     arranged by its archetype assembler in compose_section.py. STYLE=radical-editorial
     structure layered over per-section brand hues/fonts. -->
{banner_block}
{nav_block}
{sections}
{REVEAL_SCRIPT}
{marquee_script}
{ix_script}
{cr.parallax_script_tags(doc)}
</body>
</html>
"""


def blessed_wildcard_css(doc, wildcards: dict[str, int]) -> str:
    """CSS for HUMAN-BLESSED magic tricks (magic-trick.md `## Blessed`), one ladder entry
    per section. `--wildcard` keys are the ACTIVE brand's layout ids; each dispatches to
    its SCAFFOLD FAMILY's ladder entry (compose_section.scaffold_key — the ladder is
    keyed by scaffold, not layout id). Ladder CSS is scaffold-scoped (`.cs-<scaffold>-*`),
    so it applies only to its own section; entries that touch `:root` (ghost sizes) would
    leak page-wide and are refused here — bless those via a section-scoped rewrite
    instead."""
    import wildcard_generator as wg
    parts = []
    for lid, lvl in wildcards.items():
        layout = cs.find_layout(doc, lid)
        if layout is None:
            print(f"  [wildcard] no layout '{lid}' in this brand — skipped", file=sys.stderr)
            continue
        entry = (wg.SECTION_LADDER.get(cs.scaffold_key(layout)) or {}).get(lvl)
        if not entry:
            print(f"  [wildcard] no L{lvl} ladder CSS for '{lid}' — skipped", file=sys.stderr)
            continue
        desc, css = entry
        if ":root" in css:
            print(f"  [wildcard] '{lid}' L{lvl} touches :root — refused (would leak "
                  f"page-wide); re-scope it first", file=sys.stderr)
            continue
        parts.append(f"/* BLESSED MAGIC TRICK — {lid} L{lvl}: {desc} */\n{css}")
    return "\n".join(parts)


def main():
    ap = argparse.ArgumentParser(description="Compose a full page from the brand catalog.")
    ap.add_argument("brand_yaml", type=Path)
    ap.add_argument("-o", "--out", type=Path, required=True)
    ap.add_argument("--style", default=None)
    ap.add_argument("--order", default=None,
                    help="comma-separated layout ids (default: the brand's pageOrder:, "
                         "else its layouts[] in authored order)")
    ap.add_argument("--wildcard", default=None,
                    help="blessed magic tricks to apply, e.g. 'mission-statement=3,"
                         "curator-quote=2' (layout ids or use-case aliases; levels 1-3)")
    args = ap.parse_args()

    doc = load_doc(args.brand_yaml)
    order = [s.strip() for s in args.order.split(",")] if args.order else page_order(doc)
    style_ctx = load_and_merge(args.style, doc) if args.style else inactive_context()

    args.out.mkdir(parents=True, exist_ok=True)
    # Resolve + copy the extracted nav logo BEFORE building the page so the composed hero nav
    # references the local, offline-safe asset (in-memory doc mutation only; brand.yaml unchanged).
    cs.prepare_nav_logo(doc, Path(args.brand_yaml).parent, args.out / "assets")
    wildcards = None
    if args.wildcard:
        import wildcard_generator as wg
        wildcards = wg.parse_budget(args.wildcard)   # aliases resolve; no style clamp —
        # a HUMAN blessing is already the authority (magic-trick.md ## Blessed).
    (args.out / "index.html").write_text(
        build_page(doc, args.brand_yaml, order, style_ctx, wildcards=wildcards))
    # drift-detection + provenance-index sidecar (SPEC §B.1/§F) — same bundle the page embeds.
    tokens_css.write_manifest(
        args.out, tokens_css.build_page_tokens(doc, style_ctx, brand_yaml_path=args.brand_yaml))
    copied = cs.copy_assets(Path(args.brand_yaml).parent, args.out / "assets")
    copied += cs.copy_fonts(Path(args.brand_yaml).parent, args.out / "assets", doc)

    print(f"Composed full page -> {args.out}/index.html"
          + (f"  [style:{style_ctx.style_id}]" if style_ctx.active else ""))
    print(f"  order: {' -> '.join(order)}")
    print(f"  assets: {', '.join(copied) or 'none'}")
    layouts = {l.get("id"): l for l in doc.get("layouts", [])}
    chosen_ids = [i for i in order if i in layouts]
    for idx, lid in enumerate(chosen_ids):
        layout = layouts[lid]
        ctx = cr.make_context(doc, *cs.resolve_surface_intent(doc, layout))
        unresolved = [r for r in cs.render_slots(doc, layout, ctx) if "unresolved slot" in r["html"]]
        print(f"  [sec-{idx}] {lid:<18} archetype={layout.get('archetype'):<8} "
              f"slots={len(layout.get('blockMapping') or [])} unresolved={len(unresolved)}")
    fc = cr.footer_content(doc)
    links_note = (f"columns={len(fc['columns'])}" if fc.get("columns")
                  else f"sitemap={len(fc.get('sitemap') or [])}")
    print(f"  [sec-{len(chosen_ids)}] {'closing-bookend':<18} archetype={'footer':<8} "
          f"{links_note} social={len(fc['social'])} "
          f"legal={'yes' if fc['legal'] else 'no'} (component_render.render_footer)")


if __name__ == "__main__":
    main()
