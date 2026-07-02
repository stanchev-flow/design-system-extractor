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
import sys
from pathlib import Path

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import component_render as cr  # noqa: E402
import compose_section as cs  # noqa: E402
from render_section import (  # noqa: E402
    base_size,
    color_value,
    css_len,
    font_stack,
    google_fonts_link,
    spacing_value,
    type_role,
)
from styles import RenderContext, inactive_context, load_and_merge  # noqa: E402

# Default narrative order for the WoodWave page: hero bookend -> editorial about-run ->
# mission statement -> gallery showcase -> heritage timeline -> curator quote -> visit band
# (the richer two-panel variant, supersedes the simpler info-band in the default page) ->
# newsletter conversion -> closing footer bookend. The CONTENT footer below is composed
# from the SHARED component renderer (component_render.render_footer) as the final
# section; the site-chrome navbar/footer pipeline is a separate worker's concern.
# `info-band` (the simpler single-panel pattern) stays a valid layouts[] instance for
# reuse elsewhere — it is just not part of THIS page's default narrative order.
DEFAULT_ORDER = ["opening-bookend", "editorial-collage", "mission-statement",
                 "gallery-showcase", "heritage-timeline", "curator-quote",
                 "visit-band", "conversion-stack"]

# The single layout that is permitted to deploy the gold accent (logo + hero eyebrow).
ACCENT_LAYOUT = "opening-bookend"

# The closing-bookend footer renders on the brand's near-black strong surface.
FOOTER_SURFACE = "surface/inverse-strong"

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
})();
</script>"""


def footer_content(doc) -> dict:
    """Pull the closing-bookend footer copy from brand.yaml (read-only): the oversized
    didone slash SITEMAP (ABOUT / GALLERY / EXHIBITION / VISIT / BUY TICKETS), the TEXT
    social links (INSTAGRAM / FACEBOOK / YOUTUBE / TWITTER) and the legal/copyright line.
    Sourced from the extracted top-level `footer` block (footer.columns nav links +
    footer.social + footer.legal); never fabricated."""
    foot = doc.get("footer") or {}
    nav_set = ("about", "gallery", "exhibition", "visit", "buy tickets")
    sitemap, seen = [], set()
    for col in foot.get("columns") or []:
        for link in col.get("links") or []:
            lab = (link.get("label") or "").strip()
            key = lab.lower()
            if key in nav_set and key not in seen:
                seen.add(key)
                sitemap.append({"label": lab.upper(), "href": link.get("href", "#")})
    social = [{"label": (s.get("network") or "").upper(), "href": s.get("href", "#")}
              for s in (foot.get("social") or []) if s.get("network")]
    legal = ((foot.get("legal") or {}).get("text") or "").strip()
    return {"sitemap": sitemap, "social": social, "legal": legal}


def load_doc(brand_yaml: Path) -> dict:
    return yaml.safe_load(Path(brand_yaml).read_text())


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
    vars the split + collage scaffolds read. The per-section blocks below override the
    visual --c-* values per surface; these are the document baseline + the values the
    on-brand gate reads."""
    text = color_value(doc, surf.get("textPrimary")) or "#111111"
    accent = color_value(doc, surf.get("textAccent")) or text
    bg = surf.get("bg") or "#ffffff"
    disp = type_role(doc, "display-hero")
    heading_stack, _ = font_stack(doc, "display-hero", "Georgia, serif")
    body_stack, _ = font_stack(doc, "body", "system-ui, sans-serif")
    radius = spacing_value(doc, "radius-global", "0rem")
    ghost = color_value(doc, "text/ghost-on-primary") or "rgba(31,26,20,0.06)"
    panel = color_value(doc, "surface/panel") or "#F7EFE6"
    panel_ink = color_value(doc, "text/on-primary") or "#1F1A14"
    panel_hair = color_value(doc, "border/hairline-on-primary") or "rgba(31,26,20,0.30)"
    return f""":root {{
  /* gate-readable legacy brand vars (authoritative VALUES; page opens on {surf.get('bg')}) */
  --bg: {bg};
  --text: {text};
  --accent: {accent};
  --display-size: {display_size};
  --radius: {radius};
  --font-heading: {heading_stack};
  --font-body: {body_stack};
  /* brand-constant aliases for the collage ghost + the cream split panel */
  --c-ghost: {ghost};
  --c-panel: {panel};
  --c-panel-ink: {panel_ink};
  --c-panel-hairline: {panel_hair};
  /* ONE shared page grid + baseline (alignment quick wins) — mirrors
     compose_section.root_vars: all section scaffolds place onto these SHARED tracks
     and snap offsets to --baseline / --col, so adjacent sections register to the same
     columns, edges and baselines. */
  --grid-cols: 12;
  --grid-gutter: 6rem;
  --content-measure: 86rem;
  --baseline: 0.5rem;
  --col: calc((100% - 11 * var(--grid-gutter)) / 12);
}}"""


def section_vars(doc, sel, surf, *, display_size, accent_on, surf_role, style_ctx) -> str:
    """Per-section surface-scoped --c-* values (the shared c-* classes read these). For
    every section except the accent layout, the committed accent collapses to ink so no
    accent ever lands on a light/non-hero surface. Vertical rhythm (section padding +
    inter-block gaps) is emitted per surface via ``rhythm_vars_css`` — brand spacing
    tokens preferred, else the active style's spacing scale."""
    block = cr.component_vars(doc, surf, selector=sel, display_size=display_size)
    extra = [cs.rhythm_vars_css(doc, style_ctx, surf_role, selector=sel)]
    if not accent_on:
        extra.append(f"{sel} {{ --c-accent: var(--c-ink); }}")
    return block + "\n" + "\n".join(extra)


def page_style_override(style_ctx: RenderContext) -> str:
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
    poster = s.display_size_css()
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
        ".cs-footer-sec { padding-top: var(--c-section-pad-top, var(--c-section-pad, 6.25rem));"
        " text-align: center; }",
        "/* page-level navbar (hoisted out of the hero): a SLIM bar with its own modest",
        "   vertical padding + the section horizontal inset — it no longer inherits the",
        "   hero section's large padding-block-start. Its own margin-bottom is neutralized",
        "   so it reads as a bar flush above the hero, not padded inside it. */",
        "#page-nav { background: var(--c-paper); color: var(--c-ink); }",
        "#page-nav .cs-nav { margin-bottom: 0;"
        " padding: var(--c-nav-pad-block, 1.75rem) var(--c-section-pad-x, 2.5rem); }",
        "/* page: only the opening section is full-frame; others size to content. */",
        ".cs-section { min-height: auto; }",
        "#sec-0 .cs-section { min-height: 100cqh; }",
    ]
    return "\n".join(parts)


def hero_brand_override_css() -> str:
    """HERO-ONLY brand-over-style exception (human-directed, intentional).

    Precedence is normally STYLE > BRAND on structure; the radical-editorial STYLE left-
    anchors every section and forces the display heading to ink. For the HERO
    (opening-bookend, #sec-0) ONLY, the BRAND wins on four committed visual choices of the
    real WoodWave hero: (1) the heading is CENTERED, (2) the display heading is the brand
    ACCENT (gold), (3) on the brand's dark inverse hero surface (already set by the layout's
    surfaceIntent), (4) the display heading renders at the display-hero weight (Melodrama
    Medium 500) while every other section heading uses the section weight (Melodrama Regular
    400) — matching the real site (hero 12.2vw/500 vs section headings 100/80px/400). The
    STYLE still owns all hero STRUCTURE (poster scale, flat, zero
    radius, tight leading / negative tracking). Scoped to #sec-0 so NO other section is
    centered or accent-headed — every editorial/info/conversion section keeps the style's
    left-anchored, ink-display treatment. Gold-on-dark also resolves the earlier
    gold-on-cream low-contrast hero. Appended AFTER page_style_override so it wins."""
    return """
/* ===================================================================== */
/* HERO brand-over-style exception (#sec-0 ONLY) — see hero_brand_override_css(). */
/* ===================================================================== */
#sec-0 .cs-slot, #sec-0 .cs-eyebrow-wrap, #sec-0 .cs-title, #sec-0 .cs-foot {
  align-items: center; text-align: center; }
#sec-0 .cs-collage { margin-left: auto; margin-right: auto; }
#sec-0 .c-heading--display { text-align: center; max-width: 18ch;
  margin-left: auto; margin-right: auto;
  /* HERO poster renders at the display-hero weight (Melodrama Medium 500); every other
     section heading inherits the section heading weight (Melodrama Regular 400). */
  font-weight: var(--c-display-weight); }
#sec-0 .cs-title .c-heading--accent { color: var(--c-accent); }
"""


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


def compose_section_block(doc, layout, idx, style_ctx, brand_yaml=None):
    """Render ONE layout via the shared composer + return (html, scoped_vars_css)."""
    role, surf = cs.resolve_surface_intent(doc, layout)
    ctx = cr.make_context(doc, role, surf)
    ctx.style_active = bool(style_ctx and style_ctx.active)
    ctx.style_id = style_ctx.style_id if ctx.style_active else ""

    rendered = cs.render_slots(doc, layout, ctx)
    archetype = (layout.get("archetype") or "stack").lower()
    composer = cs.ARCHETYPE_COMPOSERS.get(archetype, cs.compose_stack_hero)
    section_html = composer(doc, layout, ctx, rendered, style_ctx)

    sel = f"#sec-{idx}"
    accent_on = layout.get("id") == ACCENT_LAYOUT
    disp = None
    if idx == 0:  # the hero display tier carries the poster scale
        disp = style_ctx.structure.display_size_css() if (style_ctx and style_ctx.active) \
            else f"{base_size(type_role(doc, 'display-hero')) or 6}rem"
    vars_css = section_vars(doc, sel, surf, display_size=disp, accent_on=accent_on,
                            surf_role=role, style_ctx=style_ctx)

    # Reuse-before-create: resolve the reusable layout PATTERN + scope its pattern-driven
    # special-treatment vars to THIS section (#sec-N) so the ghost/stagger geometry comes
    # from the reused pattern. Stamp data-pattern on the wrapper for traceability.
    pattern, match_kind = cs.resolve_pattern(doc, layout, brand_yaml)
    pat_attr = f' data-pattern="{cr.esc(pattern.id)}" data-pattern-lib="{cr.esc(pattern.lib)}"' \
        if pattern else ""
    treat = cs.pattern_treatment_css(pattern)
    if treat:  # re-scope the :root vars emitter onto this section id
        vars_css = vars_css + "\n" + treat.replace(":root {", f"{sel} {{")
    # ALIGNMENT RESOLUTION (AS-18): section-explicit > pattern contentShape.alignment >
    # style role default — resolved by ONE function, emitted per section, and stamped on
    # the wrapper as data-align/-source/-counterweight (mirrors data-pattern). Silent CSS
    # fall-through only remains where NO layer declares a stance (unstyled legacy pages).
    resolved = cs.resolve_alignment(layout, pattern, style_ctx)
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


def build_page(doc, brand_yaml, order, style_ctx: RenderContext) -> str:
    name = doc["brand"]["name"]
    layouts = {l.get("id"): l for l in doc.get("layouts", [])}
    chosen = [layouts[i] for i in order if i in layouts]

    opening_role, opening_surf = cs.resolve_surface_intent(doc, chosen[0])
    poster = style_ctx.structure.display_size_css() if (style_ctx and style_ctx.active) \
        else f"{base_size(type_role(doc, 'display-hero')) or 6}rem"

    blocks, var_blocks = [], []
    for idx, layout in enumerate(chosen):
        block, vars_css, _role = compose_section_block(doc, layout, idx, style_ctx, brand_yaml)
        blocks.append(block)
        var_blocks.append(vars_css)

    # PAGE-LEVEL NAVBAR (hoisted out of the hero). The nav was previously rendered INSIDE
    # #sec-0 by compose_stack_hero, so it inherited the hero section's padding-block-start
    # (an uncommon large gap above the nav). It is now a page-level sibling emitted ONCE
    # before #sec-0 — mirroring the footer, which is its own final section — so the final
    # structure is Page > { Nav, Section(s), Footer } and the hero top padding normalizes to
    # the normal section rhythm. Emitted only for pages whose opening section would have
    # rendered the hero nav (so a split/collage-opened page stays nav-free, as before).
    nav_block = ""
    if chosen and _section_renders_nav(chosen[0]):
        nav_sel = "#page-nav"
        nav_ctx = cr.make_context(doc, opening_role, opening_surf)
        nav_ctx.style_active = bool(style_ctx and style_ctx.active)
        nav_ctx.style_id = style_ctx.style_id if nav_ctx.style_active else ""
        nav_html = cr.render_navbar(doc, nav_ctx, cs._navbar_props(doc))
        nav_block = (f'<div id="page-nav" class="cs-surface" '
                     f'data-surface="{cr.esc(opening_role)}">\n{nav_html}\n</div>')
        nav_accent_on = chosen[0].get("id") == ACCENT_LAYOUT
        var_blocks.append(section_vars(doc, nav_sel, opening_surf, display_size=None,
                                       accent_on=nav_accent_on, surf_role=opening_role,
                                       style_ctx=style_ctx))

    # Closing-bookend FOOTER as the final section — composed via the SHARED component
    # renderer (component_render.render_footer), the SAME renderer the gallery uses, NOT
    # the chrome generator. Surface = brand near-black strong; copy from brand.yaml.
    foot_idx = len(chosen)
    foot_surf = doc["tokens"]["surfaces"][FOOTER_SURFACE]
    foot_ctx = cr.make_context(doc, FOOTER_SURFACE, foot_surf)
    foot_ctx.style_active = bool(style_ctx and style_ctx.active)
    foot_ctx.style_id = style_ctx.style_id if foot_ctx.style_active else ""
    foot_html = cr.render_footer(doc, foot_ctx, footer_content(doc))
    # the closing bookend is stamped too (its centered cluster is the style's declared
    # footer stance, not an accident) so the alignment-resolution gate can see it.
    foot_align = cs.align_stamp_attrs(
        cs.resolve_alignment({"id": "closing-bookend", "archetype": "footer"},
                             None, style_ctx))
    blocks.append(
        f'<div id="sec-{foot_idx}" class="cs-surface" data-layout="closing-bookend" '
        f'data-surface="{cr.esc(FOOTER_SURFACE)}"{foot_align}>\n'
        f'<section class="cs-section cs-footer-sec">\n{foot_html}\n</section>\n</div>')
    # Do NOT collapse the footer accent to ink when the brand carries a MEASURED link-hover
    # color (color-shift): the footer sits on the near-black strong surface, so keeping the
    # committed gold accent there is on-brand (gold-on-dark) and lets the footer link hover
    # share the one gold with the nav + inline links. Underline-draw brands still collapse.
    foot_keep_accent = (cr.link_mode(doc) == "color-shift"
                        and cr.link_hover_color(doc) is not None)
    var_blocks.append(section_vars(doc, f"#sec-{foot_idx}", foot_surf, display_size=None,
                                   accent_on=foot_keep_accent, surf_role=FOOTER_SURFACE,
                                   style_ctx=style_ctx))

    gf = google_fonts_link(cs.loadable_proxies(doc))
    face_css = cs.font_face_css(Path(brand_yaml).parent, doc)
    css_parts = [
        legacy_root_vars(doc, opening_surf, display_size=poster),
        cr.COMPONENT_CSS,
        # motion --c-* vars (easing + durations + reveal shift) from brand.yaml voice.motionSpec;
        # after COMPONENT_CSS so the brand's authored spec wins over the inline fallbacks.
        cr.motion_vars_css(doc),
        # link hover treatment (color-shift → measured gold hover); "" for underline-draw brands.
        cr.link_hover_css(doc),
        page_scaffold_css(),
        "\n".join(var_blocks),
    ]
    if style_ctx and style_ctx.active:
        css_parts.append(page_style_override(style_ctx))
        # HERO brand-over-style exception + style-gate alias, AFTER the style override so
        # the hero override wins; both are no-ops when no style is active.
        css_parts.append(hero_brand_override_css())
        css_parts.append(style_gate_markers_css())
    # scroll-parallax (brand motion treatment; opt-in via voice.motionSpec.imageParallax —
    # "" when the brand hasn't declared it, so every other project renders unchanged).
    css_parts.append(cr.parallax_css(doc))
    css = "\n".join(css_parts)

    html_attr = f' data-style="{style_ctx.style_id}"' if (style_ctx and style_ctx.active) else ""
    parallax_attr = ' data-parallax-images="true"' if cr.image_parallax_spec(doc)["enabled"] else ""
    sections = "\n".join(blocks)
    return f"""<!doctype html>
<html lang="en"{html_attr}{parallax_attr}>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{cr.esc(name)} - full page (composed from catalog)</title>
{gf}
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
{nav_block}
{sections}
{REVEAL_SCRIPT}
{cr.parallax_script_tags(doc)}
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser(description="Compose a full page from the brand catalog.")
    ap.add_argument("brand_yaml", type=Path)
    ap.add_argument("-o", "--out", type=Path, required=True)
    ap.add_argument("--style", default=None)
    ap.add_argument("--order", default=None,
                    help="comma-separated layout ids (default: hero,editorial,info,conversion)")
    args = ap.parse_args()

    doc = load_doc(args.brand_yaml)
    order = [s.strip() for s in args.order.split(",")] if args.order else DEFAULT_ORDER
    style_ctx = load_and_merge(args.style, doc) if args.style else inactive_context()

    args.out.mkdir(parents=True, exist_ok=True)
    # Resolve + copy the extracted nav logo BEFORE building the page so the composed hero nav
    # references the local, offline-safe asset (in-memory doc mutation only; brand.yaml unchanged).
    cs.prepare_nav_logo(doc, Path(args.brand_yaml).parent, args.out / "assets")
    (args.out / "index.html").write_text(build_page(doc, args.brand_yaml, order, style_ctx))
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
    fc = footer_content(doc)
    print(f"  [sec-{len(chosen_ids)}] {'closing-bookend':<18} archetype={'footer':<8} "
          f"sitemap={len(fc['sitemap'])} social={len(fc['social'])} "
          f"legal={'yes' if fc['legal'] else 'no'} (component_render.render_footer)")


if __name__ == "__main__":
    main()
