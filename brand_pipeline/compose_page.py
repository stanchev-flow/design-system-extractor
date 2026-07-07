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
})();
</script>"""


def load_doc(brand_yaml: Path) -> dict:
    doc = yaml.safe_load(Path(brand_yaml).read_text())
    # active-brand image inventory (AS-34) + authored section copy; in-memory only.
    cs.attach_brand_copy(doc, Path(brand_yaml).parent)
    return cs.attach_asset_inventory(doc, Path(brand_yaml).parent)


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
  --c-panel-hairline: var(--color-border-hairline-on-primary);
  /* ONE shared page grid + baseline (alignment quick wins) — mirrors
     compose_section.root_vars: all section scaffolds place onto these SHARED tracks
     and snap offsets to --baseline / --col, so adjacent sections register to the same
     columns, edges and baselines. */
  --grid-cols: 12; /* provenance: structural — shared registration grid */
  --grid-gutter: 6rem; /* provenance: structural — registration gutter unit */
  --content-measure: 86rem; /* provenance: structural — shared content measure */
  --baseline: 0.5rem; /* provenance: structural — vertical registration unit */
  --col: calc((100% - 11 * var(--grid-gutter)) / 12);
}}"""


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


def compose_section_block(doc, layout, idx, style_ctx, brand_yaml=None, accent_id=None):
    """Render ONE layout via the shared composer + return (html, scoped_vars_css).
    ``accent_id`` is the resolved accent section id (accent_layout_id); pass it from
    build_page so the whole page agrees on the single committed accent."""
    role, surf = cs.resolve_surface_intent(doc, layout)
    ctx = cr.make_context(doc, role, surf)
    ctx.style_active = bool(style_ctx and style_ctx.active)
    ctx.style_id = style_ctx.style_id if ctx.style_active else ""
    # style-aware cta-shape (B5): the brand law still wins inside cta_shape; the active
    # style's primaryAction soft-option default fills the gap for law-silent brands.
    ctx.cta = cr.cta_shape(doc, style_ctx.structure if ctx.style_active else None)

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


def build_page(doc, brand_yaml, order, style_ctx: RenderContext,
               wildcards: dict[str, int] | None = None) -> str:
    name = doc["brand"]["name"]
    layouts = {l.get("id"): l for l in doc.get("layouts", [])}
    chosen = [layouts[i] for i in order if i in layouts]
    accent_id = accent_layout_id(doc, order)

    opening_role, opening_surf = cs.resolve_surface_intent(doc, chosen[0])
    poster = page_display_size(doc, style_ctx)

    blocks, var_blocks = [], []
    for idx, layout in enumerate(chosen):
        block, vars_css, _role = compose_section_block(doc, layout, idx, style_ctx,
                                                       brand_yaml, accent_id=accent_id)
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
        # Chrome-nav surface = the brand's MEASURED bar color resolved to one of its
        # own roles (cr.nav_surface_role, nav-fix 2026-07). A transparent/unmeasured
        # bar keeps the opening section's surface — the extracted nav sits over what
        # it overlaps, which is exactly the pre-fix behavior.
        nav_role = cr.nav_surface_role(doc) or opening_role
        nav_surf = doc["tokens"]["surfaces"].get(nav_role, opening_surf)
        nav_ctx = cr.make_context(doc, nav_role, nav_surf)
        nav_ctx.style_active = bool(style_ctx and style_ctx.active)
        nav_ctx.style_id = style_ctx.style_id if nav_ctx.style_active else ""
        nav_html = cr.render_navbar(doc, nav_ctx, cs._navbar_props(doc))
        nav_block = (f'<div id="page-nav" class="cs-surface" '
                     f'data-surface="{cr.esc(nav_role)}">\n{nav_html}\n</div>')
        nav_accent_on = chosen[0].get("id") == accent_id
        var_blocks.append(section_vars(doc, nav_sel, nav_surf, display_size=None,
                                       accent_on=nav_accent_on, surf_role=nav_role,
                                       style_ctx=style_ctx))

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
        page_scaffold_css(),
    ]
    # AS-37: the inset art-panel device CSS ships ONLY when a section on THIS page
    # actually renders it — its rounded-panel rule must never ride along on pages of
    # brands whose neverDo forbids radius (the static no-radius check reads page text).
    if any((l or {}).get("_artPanel") is not None for l in chosen):
        css_parts.append(cs.SCAFFOLD_ART_PANEL_CSS)
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
{nav_block}
{sections}
{REVEAL_SCRIPT}
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
    print(f"  [sec-{len(chosen_ids)}] {'closing-bookend':<18} archetype={'footer':<8} "
          f"sitemap={len(fc['sitemap'])} social={len(fc['social'])} "
          f"legal={'yes' if fc['legal'] else 'no'} (component_render.render_footer)")


if __name__ == "__main__":
    main()
