#!/usr/bin/env python3
"""render_components_preview.py — a brand-styled COMPONENT PREVIEW GALLERY.

Reads a brand.yaml (the canonical, library-agnostic design language) plus the
universal contracts (contracts/{primitives,blocks}.yaml) and renders a single,
self-contained gallery page that shows EVERY primitive and block in the brand's
catalog as a real, on-brand rendered example.

For each catalog item the gallery renders a labeled card carrying:
  - the item NAME + an origin BADGE
      extracted -> solid badge
      designed  -> dashed-outline "synthesized" badge (and a "not used on page" note)
  - the item's universal intent (from the contract)
  - a FAITHFUL rendered example built from the brand's real token values and the
    contract's slot grammar (heading in the brand display font/size/case, eyebrow
    uppercase, image at the brand radius, ruled action rows, etc.)

Brand rules are honored visually: neverDo (radius 0, no shadows/borders, accent
only on dark surfaces, underline-only inputs, typographic actions) shapes every
example, and prohibition-as-signal items (button, pill, icon-button, card-on-cream)
are rendered as the typographic form the brand actually uses, with the prohibited
"synthesized / avoid" variant shown and clearly labeled.

For action / interactive elements (link, cta, button, icon-button, input, toggle,
checkbox) the card also renders a STATES matrix: a row of static swatches showing
default / hover / pressed / focus / disabled all at once (state styling applied
inline), plus a LIVE interactive instance wired with real CSS :hover / :active /
:focus / :disabled so the user can actually hover and press it inside the iframe.
Hover / pressed styling is derived from the brand tokens and motion dial.

IFRAME CONVENTION: the page is embedded in a Studio iframe, so it uses NO
vh/dvh/vw units anywhere. Layout sizing uses container-query units (cqw/cqh/cqi)
against an explicit `container-type: size; container-name: frame;` wrapper on a
full-height html/body.

Token resolution reuses the faithful helpers in tokens_css.py (imported, never
modified) so every value is the brand's real token.

Usage:
  python3 render_components_preview.py <brand.yaml> -o <outdir>
  # writes <outdir>/index.html
"""
from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path

import yaml

# Reuse the canonical, faithful token resolvers from tokens_css.py (the layer-1
# generator module; the resolvers moved there when render_section.py was retired,
# token-layer 2026-07). We import — never modify — that module. When run as
# `python brand_pipeline/render_components_preview.py ...` the script's own dir is
# on sys.path[0]; we also insert it explicitly to be robust to other launch dirs.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import tokens_css  # noqa: E402
from tokens_css import (  # noqa: E402
    base_size,
    color_value,
    font_stack,
    google_fonts_link,
    spacing_value,
    type_role,
)
# The SINGLE SOURCE OF TRUTH per-component renderers. The gallery AND the section
# composer (compose_section.py) both render catalog components through this module, so a
# change to a primitive renderer here is reflected in every composed section too.
import component_render as cr  # noqa: E402
import compose_section as cs  # noqa: E402  (shared self-hosted-font copy + @font-face emit)
import compose_page as cp  # noqa: E402  (chrome footer surface-role resolution)
import compose_from_composition as cfc  # noqa: E402  (Tier-3 demo hydration adapter)

# Gallery render context (RP-1): rebound per brand in main() via _bind_gallery_ctx —
# the canvas is the BRAND's primary surface, so is_dark/accent-legality come from the
# brand's own surface declaration, never from a hardcoded light-canvas assumption.
_GALLERY_CTX = cr.ComponentContext(surface_role="surface/primary", is_dark=False)


def _bind_gallery_ctx(doc) -> None:
    """RP-1: bind the module-level gallery context to the BRAND's primary surface
    (the same make_context the composers use), so specimen rendering decisions
    (accent-on-dark, hover legality) follow the brand's surface declaration."""
    global _GALLERY_CTX
    surfaces = (doc.get("tokens", {}) or {}).get("surfaces", {}) or {}
    role = "surface/primary" if "surface/primary" in surfaces else \
        (next(iter(surfaces)) if surfaces else "surface/primary")
    if surfaces:
        _GALLERY_CTX = cr.make_context(doc, role, surfaces[role])


def component_alias_css(doc) -> str:
    """RP-1: the specimen alias layer, GENERATED per surface via the SAME
    ``component_vars`` emitter production uses (no hand-pinned `--c-accent: var(--ink)`;
    a brand whose primary surface declares a legal accent keeps it). The default
    `:root` scope is the brand's primary surface — the gallery canvas — plus one scoped
    block per surface role for the surface-roles specimen tier (`[data-surface-frame]`),
    which makes AS-20 interaction re-scoping visually reviewable per surface."""
    surfaces = (doc.get("tokens", {}) or {}).get("surfaces", {}) or {}
    if not surfaces:
        return ""
    primary = "surface/primary" if "surface/primary" in surfaces else next(iter(surfaces))
    blocks = [cr.component_vars(
        doc, surfaces[primary], selector=":root",
        # show the display sample at h2 scale so it fits a specimen card
        display_size="var(--c-h2-size)", surface_role=primary)]
    for role, surf in surfaces.items():
        blocks.append(cr.component_vars(
            doc, surf, selector=f'[data-surface-frame="{esc(role)}"]',
            display_size="var(--c-h2-size)", surface_role=role))
    return "\n".join(blocks)


def esc(value) -> str:
    return html.escape(str(value if value is not None else ""))


# ── measured button families (remote-fix Phase C) ────────────────────────────────

def _fam_slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(name).lower()).strip("-") or "family"


def _is_text_button_family(fam: dict) -> bool:
    """A text-link family (e.g. a 'Learn more →' card link) has no fill/outline of its
    own — it demos through the arrow-link device, not the filled specimen class."""
    if str(fam.get("style") or "").lower().startswith("text"):
        return True
    return not fam.get("bg") and not fam.get("border")


def _button_families(doc) -> dict:
    """The brand's measured button families from brand.yaml `buttons`, in declaration
    order. Only real family dicts count — sibling markers (`renderHint`,
    `singleVariantConfirmed`) carry none of the family keys and are skipped."""
    fams = {}
    for name, fam in ((doc.get("buttons") or {})).items():
        if isinstance(fam, dict) and any(fam.get(k) for k in ("bg", "fg", "border", "style")):
            fams[name] = fam
    return fams


# layer-1 (tokens_css.build_page_tokens) emits --button[-<family>]-* custom properties
# for these families; the specimen CSS var()-references them so the values stay in the
# generated token block, exactly like every other specimen class.
_TOKENIZED_FAMILIES = ("primary", "secondary", "tertiary")


def button_family_css(doc) -> str:
    """Per-family specimen classes (`.btnf-<family>`) for a filled-CTA brand's measured
    button families. Families layer 1 tokenizes ride var() references; any additional
    measured filled family falls back to its own brand.yaml values (read at render time
    from the ACTIVE brand's file — never another brand's, never shared literals)."""
    fams = _button_families(doc)
    if not fams or cr.cta_shape(doc) != "filled":
        return ""
    out = []
    for name, fam in fams.items():
        if _is_text_button_family(fam):
            continue
        slug = _fam_slug(name)
        if name in _TOKENIZED_FAMILIES:
            p = "--button" if name == "primary" else f"--button-{name}"
            base = (f"background: var({p}-bg, transparent); "
                    f"color: var({p}-fg, var(--button-fg)); "
                    f"border: var({p}-border, 0); "
                    f"border-radius: var({p}-radius, var(--button-radius, 0)); "
                    f"padding: var({p}-pad, var(--button-pad, 0.7rem 1.4rem)); "
                    f"font-family: var({p}-font, var(--button-font, var(--font-body))); "
                    f"font-size: var({p}-size, var(--button-size, var(--control-size))); "
                    f"font-weight: var({p}-weight, var(--button-weight, 400));")
            hover = f"background: var({p}-bg-hover, var({p}-bg, transparent));"
            press = (f"background: var({p}-bg-pressed, "
                     f"var({p}-bg-hover, var({p}-bg, transparent)));")
        else:
            def _v(key, default):
                v = fam.get(key)
                return str(v) if v is not None else default
            size = f"{fam['sizeRem']}rem" if fam.get("sizeRem") else "var(--control-size)"
            base = (f"background: {_v('bg', 'transparent')}; "
                    f"color: {_v('fg', 'var(--ink)')}; "
                    f"border: {_v('border', '0')}; "
                    f"border-radius: {_v('radius', '0')}; "
                    f"padding: {_v('padding', '0.7rem 1.4rem')}; "
                    f"font-family: var(--font-body); font-size: {size}; "
                    f"font-weight: {_v('weight', '400')};")
            hover = f"background: {_v('bgHover', _v('bg', 'transparent'))};"
            press = f"background: {_v('bgPressed', _v('bgHover', _v('bg', 'transparent')))};"
            if fam.get("fgHover"):
                hover += f" color: {fam['fgHover']};"
        out.append(f".btnf-{slug} {{ {base} }}\n"
                   f".btnf-{slug}.is-hover, .btnf-{slug}.live:hover {{ {hover} }}\n"
                   f".btnf-{slug}.is-active, .btnf-{slug}.live:active {{ {press} }}")
    if not out:
        return ""
    return ("/* measured button families — values via layer-1 --button[-<family>]-* refs */\n"
            + "\n".join(out))


# Action / interactive primitives that receive a full state matrix + live instance.
ACTION_KINDS = {"link", "cta", "button", "icon-button", "input", "toggle", "checkbox"}


# ── token -> CSS variables ──────────────────────────────────────────────────────

def root_css(doc) -> tuple[str, set]:
    """Build the :root brand-token CSS block. Returns (css, google_font_proxies)."""
    def c(token, fallback="#000000"):
        return color_value(doc, token) or fallback

    disp = type_role(doc, "display-hero")
    h1 = type_role(doc, "h1")
    h2 = type_role(doc, "h2")
    h3 = type_role(doc, "h3")
    eyb = type_role(doc, "eyebrow")
    body = type_role(doc, "body")
    ctrl = type_role(doc, "control-text")
    counter = type_role(doc, "counter-display")

    heading_stack, p1 = font_stack(doc, "display-hero", "Georgia, serif")
    body_stack, p2 = font_stack(doc, "body", "system-ui, sans-serif")
    _eyb_stack, p3 = font_stack(doc, "eyebrow", "system-ui, sans-serif")
    _ctrl_stack, p4 = font_stack(doc, "control-text", "system-ui, sans-serif")
    proxies = p1 | p2 | p3 | p4

    radius = spacing_value(doc, "radius-global", "0rem")
    panel_pad = spacing_value(doc, "panel-padding", "1.75rem")
    eyebrow_gap = spacing_value(doc, "eyebrow-to-heading", "1.5rem")
    module_gap = spacing_value(doc, "module-gap-editorial", "7.5rem")

    # motion dial drives transition speed (low = slow/subtle)
    motion = (((doc.get("voice") or {}).get("dials") or {}).get("motion") or {}).get("value", "low")
    ease_ms = {"low": "180ms", "medium": "120ms", "high": "80ms"}.get(motion, "180ms")

    # Every surface/ink token below is REQUIRED by the layer-1 generator, which ran
    # (fail-loud) before this harness CSS is built — so no foreign-brand hex fallbacks
    # (the old '#FAF0E8'/'#edd580' WoodWave literals, CP-1/RP-1 shape) can ever fire.
    # accent/highlight is OPTIONAL: an accent-less brand renders its masthead in
    # inverse ink instead of inheriting another brand's gold.
    css = f""":root {{
  --surface-primary: {c('surface/primary')};
  --surface-panel: {c('surface/panel')};
  --surface-inverse: {c('surface/inverse')};
  --surface-inverse-strong: {c('surface/inverse-strong')};
  --accent: {c('accent/highlight', 'var(--ink-inverse)')};
  --ink: {c('text/on-primary')};
  --ink-muted: {c('text/on-primary-muted')};
  --ink-inverse: {c('text/on-inverse')};
  --ink-inverse-muted: {c('text/on-inverse-muted')};
  --ghost: {c('text/ghost-on-primary')};
  --hairline: {c('border/hairline-on-primary')};

  --font-heading: {heading_stack};
  --font-body: {body_stack};

  --display-size: {base_size(disp) or 6}rem;
  --h1-size: {base_size(h1) or 3.5}rem;
  --h2-size: {base_size(h2) or 2.25}rem;
  --h3-size: {base_size(h3) or 1.625}rem;
  --eyebrow-size: {base_size(eyb) or 0.6875}rem;
  --body-size: {base_size(body) or 0.875}rem;
  --control-size: {base_size(ctrl) or 0.875}rem;
  --counter-size: {base_size(counter) or 2}rem;
  --eyebrow-ls: {eyb.get('letterSpacing', '0em')};
  --control-ls: {ctrl.get('letterSpacing', '0em')};

  --radius: {radius};
  --panel-pad: {panel_pad};
  --eyebrow-gap: {eyebrow_gap};
  --module-gap: {module_gap};
  --ease: {ease_ms};
}}"""
    # brand-declared list/separator specimen glyph (footer.separator / navbar.separator);
    # the CSS fallback is a neutral en dash when the brand declares none.
    glyph = cr.footer_separator(doc) or cr.nav_separator(doc)
    if glyph:
        css = css[:-1] + f'  --specimen-list-marker: "{glyph}";\n}}'
    return css, proxies


# ── static (non-token) page + card + state CSS ──────────────────────────────────
# Harness chrome is deliberately NEUTRAL (flat, 1px ruled bars, no shadows): brand
# presentation (casing, tracking, accent placement, chrome surfaces) renders through
# the generated tokens — nav-fix 2026-07: no casing/separator/surface literals here.
BASE_CSS = """
/* provenance: preview-chrome — gallery harness styling (masthead, badges, tier headers,
   spec labels, state-matrix chrome); never brand output. Specimen content inside the
   frames renders through component_vars + COMPONENT_CSS from the generated tokens
   (SPEC §C.4 split). */
* { margin: 0; padding: 0; box-sizing: border-box; }
img { display: block; max-width: 100%; }

/* iframe-safe: cq* units resolve against this sized box. NO vh/dvh/vw anywhere. */
html { background: var(--surface-primary); height: 100%; }
html, body {
  background: var(--surface-primary);
  color: var(--ink);
  font-family: var(--font-body);
  -webkit-font-smoothing: antialiased;
}
body {
  min-height: 100%;
  container-type: size;
  container-name: frame;
  line-height: 1.5;
}

.page { width: 100%; max-width: 96rem; margin: 0 auto; padding: 4cqh 5cqw 8cqh; }

/* Masthead on the dark bookend surface (gold accent permitted here). */
.masthead {
  background: var(--surface-inverse);
  color: var(--ink-inverse);
  padding: 5cqh 5cqw;
  margin-bottom: 5cqh;
}
.masthead .eyebrow { color: var(--ink-inverse-muted); }
.masthead h1 {
  font-family: var(--font-heading);
  font-weight: 400;
  text-transform: var(--case-h1, none);
  font-size: var(--h1-size);
  line-height: 1.1em;
  color: var(--accent);
  margin: var(--eyebrow-gap) 0 1rem;
}
.masthead p { color: var(--ink-inverse-muted); max-width: 52rem; font-size: var(--body-size); }
.legend { display: flex; flex-wrap: wrap; gap: 1.5rem; margin-top: 2rem; }
.legend span { display: inline-flex; align-items: center; gap: 0.5rem;
  font-size: var(--eyebrow-size); letter-spacing: var(--eyebrow-ls);
  text-transform: var(--case-eyebrow, none); color: var(--ink-inverse-muted); }

/* Tier headers. */
.tier { margin: 6cqh 0 2.5cqh; }
.tier-num { font-family: var(--font-heading); font-size: var(--counter-size);
  color: var(--ink); line-height: 1; }
.tier-name { font-family: var(--font-heading); text-transform: var(--case-h2, none);
  font-size: var(--h2-size); line-height: 1.2em; color: var(--ink); margin-top: 0.25rem; }
.tier-sub { font-size: var(--eyebrow-size); letter-spacing: var(--eyebrow-ls);
  text-transform: var(--case-eyebrow, none); color: var(--ink-muted); margin-top: 0.75rem; }
.tier-rule { height: 1px; background: var(--hairline); margin-top: 1.25rem; }

/* Surface-roles specimen tier: each frame paints its own surface via the scoped
   per-surface alias block ([data-surface-frame] — see component_alias_css). */
.sw-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(16rem, 1fr));
  gap: 1px; background: var(--hairline); }
.sw-frame { background: var(--c-paper); color: var(--c-ink);
  padding: var(--panel-pad); display: flex; flex-direction: column;
  gap: 1rem; align-items: flex-start; min-height: 14rem; }
.sw-role { font-size: var(--eyebrow-size); letter-spacing: var(--eyebrow-ls);
  text-transform: var(--case-eyebrow, none); color: var(--c-ink-muted); }

/* Single-column long list. One item PER ROW, full page width, stacked top to
   bottom. No multi-column grid, no boxed card containers — rows are separated by
   a thin 1px hairline rule with generous vertical breathing room. Each row is a
   two-part flow: a left meta column (name + badge + tags + intent + notes) and a
   right example column; on narrow widths the example stacks beneath the meta. */
.list { display: flex; flex-direction: column; }
.cmp { display: grid; grid-template-columns: 19rem 1fr; column-gap: 3rem; row-gap: 1.25rem;
  align-items: start; padding: 2.75rem 0; border-top: 1px solid var(--hairline); }
.cmp:first-child { border-top: 0; padding-top: 1.5rem; }
.cmp-meta { display: flex; flex-direction: column; gap: 0.85rem; }
.cmp-head { display: flex; align-items: center; flex-wrap: wrap; gap: 0.6rem; }
.cmp-name { font-family: var(--font-heading); text-transform: var(--case-h2, none);
  font-size: var(--h3-size); line-height: 1.2em; color: var(--ink); }
.cmp-intent { font-size: var(--body-size); color: var(--ink-muted); line-height: 1.5em; }
/* NON-STRETCH stage alignment (AGENTS.md flex-column mechanic, remote-fix Phase C):
   flex-column children stretch by default, so content-hugging specimens (buttons,
   eyebrows, chips, arrow links) rendered edge-to-edge. The stage columns align
   flex-start and the container-ish specimens that genuinely need the full row
   (state matrices, ruled rows/lists, surface frames, chrome demos, composed-layout
   iframes, classless inline-styled wrappers) opt back in via align-self: stretch. */
.cmp-example { display: flex; flex-direction: column; align-items: flex-start;
  gap: 1.25rem; max-width: 52rem; }
.cmp-example > .cmp-stage { align-self: stretch; }

/* Badges / tags — square, no radius. */
.badge { font-family: var(--font-body); font-size: 0.625rem; letter-spacing: 0.1em;
  text-transform: var(--case-eyebrow, none); padding: 0.2rem 0.5rem; border-radius: 0; line-height: 1.2; }
.badge-extracted { background: var(--ink); color: var(--surface-primary); }
.badge-designed { background: transparent; color: var(--ink-muted);
  border: 1px dashed var(--ink-muted); }
.tag { font-family: var(--font-body); font-size: 0.625rem; letter-spacing: 0.1em;
  text-transform: var(--case-eyebrow, none); color: var(--ink-muted);
  border: 1px solid var(--hairline); padding: 0.2rem 0.5rem; }
.tag-never { border-style: dashed; color: var(--ink-muted); }

/* Example stage — no box, no border: the example sits openly in the row flow.
   align-items: flex-start = the non-stretch default; the stretch list below re-widens
   the specimens that are full-row containers by design. */
.cmp-stage { display: flex; flex-direction: column; gap: 1rem; align-items: flex-start; }
.cmp-stage > div:not([class]), .cmp-stage > .states, .cmp-stage > .ex-rows,
.cmp-stage > .ex-list, .cmp-stage > .ex-illus, .cmp-stage > .ex-spacer,
.cmp-stage > .surface-dark, .cmp-stage > .surface-darkest, .cmp-stage > .surface-panel,
.cmp-stage > .cmp-chrome-demo, .cmp-stage > .cmp-footer-demo,
.cmp-stage > .c-header, .cmp-stage > .c-form, .cmp-stage > .c-field,
.cmp-stage > .layout-frame, .cmp-stage > iframe { align-self: stretch; }
.cmp-note { font-size: var(--eyebrow-size); letter-spacing: 0.04em; line-height: 1.45em;
  color: var(--ink-muted); }
.cmp-note strong { color: var(--ink); font-weight: 600; }

/* Dark sub-surface for component examples the brand renders on its inverse bands
   (badge, banner, tooltip, code demos); the surface colors are the brand's own
   inverse tokens. */
.surface-dark { background: var(--surface-inverse); color: var(--ink-inverse);
  padding: 1.25rem; }
.surface-darkest { background: var(--surface-inverse-strong); color: var(--ink-inverse);
  padding: 1.25rem; }
.surface-panel { background: var(--surface-panel); color: var(--ink);
  padding: var(--panel-pad); }
/* chrome demos (navbar / logo / footer): the wrapper carries data-surface-frame for
   the RESOLVED brand chrome surface role (nav_surface_role / footer_surface_role) —
   the per-surface alias block scopes the --c-* vars, so a light-chrome brand demos
   light and a dark-chrome brand demos dark, each from its own evidence. */
.cmp-chrome-demo { background: var(--c-paper); color: var(--c-ink); padding: 1.25rem; }
.cmp-chrome-demo .cs-nav { display: flex; align-items: center;
  justify-content: space-between; gap: 2rem; }
.cmp-chrome-demo .cs-navlinks { display: flex; gap: 0.55rem; flex: 1;
  justify-content: center; flex-wrap: wrap; }
.cmp-chrome-demo .cs-navlinks .c-arrow-link {
  font-size: var(--size-nav, var(--c-control-size)); }
.cmp-chrome-demo .cs-navlinks .cs-sep { opacity: 0.55; }
/* footer demo: generous, scale-driven breathing room around the shared render_footer
   output; surface + ink come from the alias scope, never an assumed dark band. */
.cmp-footer-demo { background: var(--c-paper); color: var(--c-ink);
  --c-block-gap: 2.5rem; padding: 3rem 1.75rem; }

/* ── faithful example primitives ── */
.ex-display { font-family: var(--font-heading); font-weight: 400; text-transform: var(--case-h2, none);
  font-size: var(--h2-size); line-height: 1.2em; color: var(--ink); }
.ex-h3 { font-family: var(--font-heading); font-weight: 400; text-transform: var(--case-h3, var(--case-h2, none));
  font-size: var(--h3-size); line-height: 1.3em; color: var(--ink); }
.ex-sub { font-family: var(--font-heading); font-weight: 400; font-size: 1.125rem;
  line-height: 1.3em; color: var(--ink-muted); }
.ex-eyebrow { font-family: var(--font-body); font-size: var(--eyebrow-size);
  letter-spacing: var(--eyebrow-ls); text-transform: var(--case-eyebrow, none); color: var(--ink-muted); }
.ex-body { font-family: var(--font-body); font-size: var(--body-size); line-height: 1.55em;
  color: var(--ink-muted); max-width: 34ch; }
.ex-caption { font-family: var(--font-body); font-size: var(--eyebrow-size);
  letter-spacing: var(--eyebrow-ls); text-transform: var(--case-eyebrow, none); color: var(--ink-muted); }
.ex-label { font-family: var(--font-body); font-size: var(--control-size);
  letter-spacing: var(--control-ls); text-transform: var(--case-control-text, none); color: var(--ink); }

/* image / video / avatar / illustration: hard-edged rectangles, radius 0, no chrome. */
.ex-photo { background: var(--surface-inverse); color: var(--ink-inverse-muted);
  border-radius: 0; aspect-ratio: 4 / 3; width: 100%; display: flex; align-items: center;
  justify-content: center; font-family: var(--font-body); font-size: var(--eyebrow-size);
  letter-spacing: var(--eyebrow-ls); text-transform: var(--case-control-text, none); }
.ex-photo.is-portrait { aspect-ratio: 3 / 4; max-width: 9rem; }
.ex-photo.is-square { aspect-ratio: 1 / 1; max-width: 6rem; }
.ex-illus { background: var(--ghost); color: var(--ink-muted); aspect-ratio: 4/3;
  display: flex; align-items: center; justify-content: center; font-family: var(--font-heading);
  font-size: 2rem; text-transform: var(--case-h2, none); }
.ex-play { width: 0; height: 0; border-style: solid; border-width: 0.55rem 0 0.55rem 0.9rem;
  border-color: transparent transparent transparent var(--ink-inverse); }

/* logo wordmark. */
.ex-logo { font-family: var(--font-heading); text-transform: var(--case-control-text, none); letter-spacing: 0.06em;
  font-size: 1.25rem; color: var(--c-accent, var(--accent)); }

/* divider / ruled rows / list. */
.ex-rule { height: 1px; background: var(--hairline); width: 100%; }
.ex-rows { display: flex; flex-direction: column; }
.ex-row { position: relative; display: flex; align-items: center; justify-content: space-between;
  gap: 1rem; padding: 0.85rem 0; }
.ex-row + .ex-row::before, .ex-row::before { content: ""; position: absolute; left: 0; right: 0;
  top: 0; height: 1px; background: var(--hairline); }
.ex-list { display: flex; flex-direction: column; }
.ex-list .ex-li { position: relative; padding: 0.6rem 0 0.6rem 1.5rem;
  font-family: var(--font-body); font-size: var(--body-size); color: var(--ink); }
.ex-list .ex-li::before { content: ""; position: absolute; left: 0; right: 0; top: 0; height: 1px;
  background: var(--hairline); }
.ex-list .ex-li::after { content: var(--specimen-list-marker, "\2013"); position: absolute; left: 0; top: 0.6rem;
  color: var(--ink-muted); font-family: var(--font-heading); }

/* quote / stat / counter. */
.ex-quote { font-family: var(--font-heading); text-transform: var(--case-h2, none); font-weight: 400;
  font-size: 1.5rem; line-height: 1.25em; color: var(--ink); }
.ex-counter { font-family: var(--font-heading); font-size: var(--counter-size); line-height: 1;
  color: var(--ink); }

/* code. */
.ex-code { font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace; font-size: 0.8125rem;
  color: var(--ink-inverse); white-space: pre; line-height: 1.5; }

/* badge marker (gold, flat square, dark only). */
.ex-marker { display: inline-block; background: var(--accent); color: var(--surface-inverse-strong);
  font-family: var(--font-body); font-size: 0.625rem; letter-spacing: 0.1em; text-transform: var(--case-eyebrow, none);
  padding: 0.25rem 0.5rem; border-radius: 0; }

/* underline form controls — no box, no fill, radius 0. */
.ex-field { position: relative; display: flex; align-items: flex-end; justify-content: space-between;
  gap: 1rem; padding-bottom: 0.5rem; width: 100%; }
.ex-field::after { content: ""; position: absolute; left: 0; right: 0; bottom: 0; height: 1px;
  background: var(--hairline); }
.ex-input { flex: 1; border: 0; background: transparent; outline: none; color: var(--ink);
  font-family: var(--font-body); font-size: var(--body-size); padding: 0; }
.ex-input::placeholder { color: var(--ink-muted); }
.ex-select { display: inline-flex; align-items: center; gap: 0.5rem; position: relative;
  padding-bottom: 0.5rem; font-family: var(--font-body); font-size: var(--control-size);
  letter-spacing: var(--control-ls); text-transform: var(--case-control-text, none); color: var(--ink); }
.ex-select::after { content: ""; position: absolute; left: 0; right: 0; bottom: 0; height: 1px;
  background: var(--hairline); }

/* square slider. */
.ex-slider { position: relative; height: 1px; background: var(--hairline); width: 100%; margin: 1rem 0; }
.ex-slider .fill { position: absolute; left: 0; top: 0; height: 1px; width: 55%; background: var(--ink); }
.ex-slider .handle { position: absolute; left: 55%; top: -0.4rem; width: 0.8rem; height: 0.8rem;
  background: var(--ink); border-radius: 0; }

/* square progress. */
.ex-progress { position: relative; height: 0.4rem; border: 1px solid var(--hairline); width: 100%; }
.ex-progress .fill { position: absolute; left: 0; top: 0; bottom: 0; width: 62%; background: var(--ink); }

/* tooltip. */
.ex-tip { display: inline-block; background: var(--surface-inverse); color: var(--ink-inverse);
  padding: 0.4rem 0.6rem; border-radius: 0; font-family: var(--font-body); font-size: var(--eyebrow-size);
  letter-spacing: 0.04em; }

/* spacer visual. */
.ex-spacer { border-left: 1px solid var(--hairline); border-right: 1px solid var(--hairline);
  position: relative; height: 3rem; display: flex; align-items: center; justify-content: center; }
.ex-spacer span { font-family: var(--font-body); font-size: var(--eyebrow-size);
  letter-spacing: var(--eyebrow-ls); text-transform: var(--case-eyebrow, none); color: var(--ink-muted); }

/* ── typographic action (link / cta / icon-button remap) ── */
.act { font-family: var(--font-body); font-size: var(--control-size); letter-spacing: var(--control-ls);
  text-transform: var(--case-control-text, none); color: var(--ink); text-decoration: none; background: none; border: 0;
  cursor: pointer; display: inline-flex; align-items: center; gap: 0.5rem; padding: 0;
  transition: transform var(--ease) ease, opacity var(--ease) ease; }
.act .arrow { transition: transform var(--ease) ease; }
/* static state classes (so all five are visible at once) + live pseudo-classes */
.act.is-hover, .act.live:hover { text-decoration: underline; text-underline-offset: 0.25rem; }
.act.is-hover .arrow, .act.live:hover .arrow { transform: translateX(0.35rem); }
.act.is-active, .act.live:active { opacity: 0.6; transform: translateY(1px); }
.act.is-focus, .act.live:focus-visible { outline: 1px solid var(--ink); outline-offset: 0.3rem;
  text-decoration: none; }
.act.is-disabled, .act.live:disabled, .act.live[aria-disabled="true"] { opacity: 0.32;
  pointer-events: none; text-decoration: none; }

/* ── measured button FAMILIES (filled-CTA brands): one specimen class per family,
   values var()-chained into the layer-1 --button[-<family>]-* tokens (remote-fix
   Phase C: the single-variant render hid the measured secondary/tertiary/text
   families). inline-flex + stage flex-start = content-hugging by construction. */
.btnf { display: inline-flex; align-items: center; gap: 0.5rem; align-self: flex-start;
  text-decoration: none; cursor: pointer; line-height: 1.15; white-space: nowrap;
  transition: background var(--ease) ease, color var(--ease) ease,
    border-color var(--ease) ease; }
.btnf.is-focus, .btnf.live:focus-visible { outline: 2px solid currentColor;
  outline-offset: 2px; }
.btnf.is-disabled, .btnf.live:disabled { opacity: 0.38; pointer-events: none; }

/* avoid (synthesized) filled button / icon-button — what the brand does NOT use. */
.avoid-btn { font-family: var(--font-body); font-size: var(--control-size); letter-spacing: var(--control-ls);
  text-transform: var(--case-control-text, none); background: var(--surface-inverse); color: var(--ink-inverse); border: 0;
  border-radius: 0; padding: 0.7rem 1.2rem; cursor: pointer; opacity: 0.85; }
.avoid-iconbtn { width: 2.4rem; height: 2.4rem; display: inline-flex; align-items: center;
  justify-content: center; background: var(--surface-inverse); color: var(--ink-inverse); border: 0;
  border-radius: 0; cursor: pointer; }
.avoid-pill { display: inline-block; border: 1px solid var(--ink-muted); border-radius: 999px;
  padding: 0.25rem 0.8rem; font-family: var(--font-body); font-size: var(--eyebrow-size);
  letter-spacing: var(--eyebrow-ls); text-transform: var(--case-eyebrow, none); color: var(--ink-muted); }
.strike { position: relative; }
.strike::after { content: ""; position: absolute; left: -4%; right: -4%; top: 50%; height: 1px;
  background: var(--ink-muted); transform: rotate(-8deg); }

/* checkbox / radio / toggle — square, radius 0, hairline + flat dark fill.
   OFF/default is an EMPTY cream control with a 1px hairline outline (no fill, no
   glyph shown); ON is the flat dark fill. Knob/box are a fixed size so the state
   row stays aligned. */
.ex-check { display: inline-flex; align-items: center; gap: 0.6rem; cursor: pointer;
  font-family: var(--font-body); font-size: var(--body-size); color: var(--ink); }
/* OFF: empty cream box, hairline outline, no visible check. */
.ex-check .box { width: 1.15rem; height: 1.15rem; box-sizing: border-box;
  border: 1px solid var(--hairline); border-radius: 0; background: var(--surface-primary);
  display: inline-flex; align-items: center; justify-content: center; color: transparent;
  font-size: 0.8rem; line-height: 1; transition: background var(--ease) ease, border-color var(--ease) ease; }
/* ON: flat dark fill with a light check. */
.ex-check.is-on .box, .ex-check input:checked + .box { background: var(--ink);
  border-color: var(--ink); color: var(--surface-primary); }
.ex-check.is-hover .box, .ex-check:hover .box { border-color: var(--ink); }
.ex-check.is-focus .box, .ex-check input:focus-visible + .box { outline: 2px solid var(--ink);
  outline-offset: 2px; }
.ex-check.is-disabled, .ex-check.disabled { opacity: 0.3; pointer-events: none; }
.ex-check input { position: absolute; opacity: 0; width: 0; height: 0; }

.ex-switch { display: inline-flex; align-items: center; gap: 0.6rem; cursor: pointer;
  font-family: var(--font-body); font-size: var(--body-size); color: var(--ink); }
/* OFF/default: empty cream track + hairline outline, dark knob pushed LEFT — an
   obviously empty switch, never a solid block. */
.ex-switch .track { width: 2.8rem; height: 1.4rem; box-sizing: border-box;
  background: var(--surface-primary); border: 1px solid var(--hairline); border-radius: 0;
  position: relative; transition: background var(--ease) ease, border-color var(--ease) ease; }
.ex-switch .knob { position: absolute; top: 50%; transform: translateY(-50%); left: 2px;
  width: 1rem; height: 1rem; background: var(--ink); border-radius: 0;
  transition: left var(--ease) ease, background var(--ease) ease; }
/* ON: flat dark fill, knob pushed RIGHT (light knob for contrast on the dark track). */
.ex-switch.is-on .track, .ex-switch input:checked + .track { background: var(--surface-inverse);
  border-color: var(--surface-inverse); }
.ex-switch.is-on .knob, .ex-switch input:checked + .track .knob { left: calc(100% - 1rem - 2px);
  background: var(--ink-inverse); }
/* hover (off): subtle emphasis by darkening the outline. */
.ex-switch.is-hover .track, .ex-switch:hover .track { border-color: var(--ink); }
.ex-switch.is-focus .track, .ex-switch input:focus-visible + .track { outline: 2px solid var(--ink);
  outline-offset: 2px; }
.ex-switch.is-disabled, .ex-switch.disabled { opacity: 0.3; pointer-events: none; }
.ex-switch input { position: absolute; opacity: 0; width: 0; height: 0; }

/* underline field state demo */
.ex-field.is-hover::after, .ex-field.live:hover::after { background: var(--ink-muted); height: 1px; }
.ex-field.is-active::after, .ex-field.is-focus::after,
.ex-field.live:focus-within::after { background: var(--ink); height: 2px; }
.ex-field.is-disabled { opacity: 0.32; pointer-events: none; }

/* states matrix. */
.states { display: flex; flex-direction: column; gap: 1rem; }
.states-label { font-family: var(--font-body); font-size: 0.625rem; letter-spacing: 0.12em;
  text-transform: var(--case-eyebrow, none); color: var(--ink-muted); }
.state-row { display: grid; grid-template-columns: repeat(5, 1fr); gap: 1px;
  background: var(--hairline); border: 1px solid var(--hairline); }
.state-col { background: var(--surface-primary); padding: 1rem 0.75rem; display: flex;
  flex-direction: column; align-items: flex-start; gap: 0.75rem; min-height: 5rem;
  justify-content: space-between; }
.state-col .stg { display: flex; align-items: center; min-height: 2rem; }
.state-name { font-family: var(--font-body); font-size: 0.5625rem; letter-spacing: 0.12em;
  text-transform: var(--case-eyebrow, none); color: var(--ink-muted); }
.state-live { display: flex; align-items: center; gap: 1.5rem; flex-wrap: wrap;
  padding-top: 0.25rem; }
.state-live .hint { font-family: var(--font-body); font-size: 0.5625rem; letter-spacing: 0.12em;
  text-transform: var(--case-eyebrow, none); color: var(--ink-muted); }

/* ── Tier 3: extracted layouts (composed through ARCHETYPE_COMPOSERS) ──
   Each pattern row embeds the REAL composed section document (compose_section.
   build_document output) in an iframe: composed sections carry their own scoped
   surface/scaffold CSS, so the iframe keeps them faithful without any mockup. */
.cmp--layout .cmp-example { max-width: none; }
.layout-frame { display: block; width: 100%; height: 42rem; border: 1px solid var(--hairline);
  background: var(--surface-primary); }

/* masthead anchor nav to the tier sections (the page's in-page navigation). */
.toc { display: flex; flex-wrap: wrap; gap: 1.5rem; margin-top: 1.5rem; }
.toc a { color: var(--accent); font-family: var(--font-body); font-size: var(--eyebrow-size);
  letter-spacing: var(--eyebrow-ls); text-transform: var(--case-eyebrow, none); text-decoration: none; }
.toc a:hover { text-decoration: underline; text-underline-offset: 0.25rem; }

/* collapsed secondary group: standard-tier patterns, listed only (not composed). */
.std { margin-top: 3rem; }
.std summary { cursor: pointer; font-family: var(--font-body); font-size: var(--eyebrow-size);
  letter-spacing: var(--eyebrow-ls); text-transform: var(--case-eyebrow, none); color: var(--ink-muted);
  padding: 0.85rem 0; border-top: 1px solid var(--hairline); }
.std-row { display: grid; grid-template-columns: 19rem 1fr; column-gap: 3rem;
  padding: 0.85rem 0; border-top: 1px solid var(--hairline); align-items: baseline; }
.std-row .std-id { font-family: var(--font-heading); text-transform: var(--case-h3, var(--case-h2, none));
  font-size: 1rem; color: var(--ink); }
.std-row .std-meta { font-size: var(--eyebrow-size); letter-spacing: 0.04em;
  color: var(--ink-muted); line-height: 1.5em; }

/* On narrower frames the example stacks directly beneath the meta line. */
@media (max-width: 60rem) {
  .cmp { grid-template-columns: 1fr; column-gap: 0; }
  .std-row { grid-template-columns: 1fr; }
}
@media (max-width: 40rem) {
  .state-row { grid-template-columns: repeat(2, 1fr); }
}
"""


# ── per-primitive faithful example renderers ────────────────────────────────────

def _arrow(label, cls=""):
    return f'<a class="act {cls}" href="#" tabindex="-1">{esc(label)} <span class="arrow">&rarr;</span></a>'


def _state_matrix(swatch_fn, live_html, label="states · hover / press / focus inside the iframe"):
    """Static 5-state row (styling applied inline) + a live interactive instance."""
    states = [("default", ""), ("hover", "is-hover"), ("pressed", "is-active"),
              ("focus", "is-focus"), ("disabled", "is-disabled")]
    cols = "".join(
        f'<div class="state-col"><div class="stg">{swatch_fn(cls)}</div>'
        f'<div class="state-name">{name}</div></div>'
        for name, cls in states
    )
    return f"""<div class="states">
      <div class="states-label">{esc(label)}</div>
      <div class="state-row">{cols}</div>
      <div class="state-live"><span class="hint">live &rarr;</span>{live_html}</div>
    </div>"""


def render_heading(doc, key, item):
    # SSOT: rendered by the shared catalog renderer (also used by section composition).
    # Specimen text + caption are BRAND-derived (blocker 7): measured layout copy /
    # the brand's own display family, never another brand's gallery prose.
    h = cr.render_heading(doc, _GALLERY_CTX,
                          {"text": _specimen(doc)["headline"], "level": "display", "tag": "div"})
    return (h + f'<div class="ex-eyebrow">display / h1 / h2 / h3 &mdash; {esc(_brand_law(doc)["display"])}</div>')


def render_subheading(doc, key, item):
    law = _brand_law(doc)
    return (f'<div class="ex-display" style="font-size:var(--h3-size)">{esc(_specimen(doc)["headline"])}</div>'
            f'<div class="ex-sub">The supporting register &mdash; {esc(law["display"])} at h3 scale, muted.</div>')


def render_eyebrow(doc, key, item):
    # Specimen = the brand's declared eyebrow PREFIX device + its authored specimen
    # line (sectionCopy.specimenEyebrow), degrading to a numbered label built from
    # the brand's own nav vocabulary — never another brand's gallery prose.
    sc = cs.section_copy_view(doc)
    text = sc.get("specimenEyebrow") or f"01 \u2014 {_specimen(doc)['links'][0]}"
    return cr.render_eyebrow(doc, _GALLERY_CTX, {"text": cr.eyebrow_prefix(doc) + text})


def render_paragraph(doc, key, item):
    # SSOT: rendered by the shared catalog renderer (also used by section composition).
    return cr.render_paragraph(doc, _GALLERY_CTX, {
        "text": ("Set narrow, roughly a third of the container and offset from its media. "
                 "The brand body register with generous leading.")})


def render_label(doc, key, item):
    return f'<span class="ex-label">{esc(_specimen(doc)["links"][0])}</span>'


def render_caption(doc, key, item):
    return ('<div class="ex-photo" style="aspect-ratio:16/9">PHOTO</div>'
            f'<div class="ex-caption">Fig. 01 &mdash; {esc(_specimen(doc)["name"])} photography</div>')


def render_image(doc, key, item):
    law = _brand_law(doc)
    ph = "IMAGE — RADIUS 0" if law["square"] else "IMAGE"
    img = cr.render_image(doc, _GALLERY_CTX, {"placeholder": ph})
    return (img + f'<div class="ex-caption">Media {esc(law["radius_word"])} &mdash; no shadow, border or mat</div>')


def render_video(doc, key, item):
    law = _brand_law(doc)
    return ('<div class="ex-photo"><span class="ex-play" aria-hidden="true"></span></div>'
            f'<div class="ex-caption">Treated like image &mdash; {esc(law["radius_word"])}</div>')


def render_avatar(doc, key, item):
    law = _brand_law(doc)
    cap = ("Hard rectangle crop &mdash; round default overridden by no-radius"
           if law["square"] else "Crop at the brand radius")
    return (f'<div class="ex-photo is-square">PERSON</div>'
            f'<div class="ex-caption">{cap}</div>')


def render_illustration(doc, key, item):
    return ('<div class="ex-illus">&#9697;</div>'
            '<div class="ex-caption">Flat graphic in a muted brand tone &mdash; no gradients</div>')


def render_logo(doc, key, item):
    role = _nav_demo_role(doc)
    return (f'<div class="cmp-chrome-demo" data-surface-frame="{esc(role)}">'
            f'<span class="ex-logo">{esc(_specimen(doc)["name"])}</span></div>'
            '<div class="ex-caption">Wordmark &mdash; rendered on the brand chrome surface</div>')


def render_icon(doc, key, item):
    return ('<div style="display:flex;gap:1.25rem;font-family:var(--font-heading);'
            'font-size:1.5rem;color:var(--ink)"><span>&rarr;</span><span>&#8260;</span>'
            '<span>+</span><span>&#8599;</span></div>'
            '<div class="ex-caption">Thin monoline glyphs inheriting text color</div>')


def render_link(doc, key, item):
    # SSOT: the base arrow link comes from the shared catalog renderer (cta/link remap).
    base = cr.render_arrow_link(doc, _GALLERY_CTX, {"label": _specimen(doc)["cta"]})
    matrix = _state_matrix(
        lambda cls: _arrow(_SPEC_CTA, cls),
        '<a class="act live" href="#">' + _SPEC_CTA + ' <span class="arrow">&rarr;</span></a>'
        '<button class="act live" disabled>Sold Out <span class="arrow">&rarr;</span></button>',
    )
    return f'{base}{matrix}'


def render_cta(doc, key, item):
    # Law-first (blocker 7 + AS-27 family): the specimen mirrors the brand's resolved
    # cta-shape — a filled-primary brand shows its real catalog button, a typographic
    # brand its arrow link — instead of asserting one brand's "never a button" law.
    if _brand_law(doc)["cta"] == "filled":
        base = cr.render_button(doc, _GALLERY_CTX, {"label": "Subscribe"})
        return ('<div class="ex-caption">CTA role &mdash; realized by the brand\'s filled button</div>'
                f'{base}')
    base = cr.render_arrow_link(doc, _GALLERY_CTX, {"label": "Subscribe"})
    matrix = _state_matrix(
        lambda cls: _arrow("Subscribe", cls),
        '<a class="act live" href="#">Subscribe <span class="arrow">&rarr;</span></a>'
        '<button class="act live" disabled>Subscribe <span class="arrow">&rarr;</span></button>',
    )
    return ('<div class="ex-caption">CTA role &mdash; realized by the arrow link primitive, never a button</div>'
            f'{base}{matrix}')


def render_button(doc, key, item):
    """Law-first: a filled-CTA brand renders its FULL measured family matrix —
    every brand.yaml `buttons` family (primary / secondary / tertiary / text-link)
    with its own five-state row + live instance (remote-fix Phase C: the old
    single-variant render hid the measured secondary/tertiary/text families). A
    typographic brand keeps the observed-as-prohibition framing (arrow-link
    realization + struck filled button as the avoid variant)."""
    if _brand_law(doc)["cta"] == "filled":
        fams = _button_families(doc)
        rows: list[str] = []
        for name, fam in fams.items():
            if rows:
                rows.append('<div class="ex-rule"></div>')
            style_word = esc(fam.get("style") or "filled")
            if _is_text_button_family(fam):
                matrix = _state_matrix(
                    lambda cls: _arrow(_SPEC_CTA, cls),
                    '<a class="act live" href="#">' + esc(_SPEC_CTA)
                    + ' <span class="arrow">&rarr;</span></a>',
                    label=f"{name} · hover / press / focus inside the iframe")
                rows.append(f'<div class="ex-caption"><strong>{esc(name)}</strong> &mdash; '
                            f'{style_word}; demos through the arrow-link device</div>{matrix}')
                continue
            slug = _fam_slug(name)
            def _sw(cls, slug=slug):
                return (f'<a class="btnf btnf-{slug} {cls}" href="#" tabindex="-1">'
                        f'{esc(_SPEC_CTA)}</a>')
            live = (f'<a class="btnf btnf-{slug} live" href="#">{esc(_SPEC_CTA)}</a>'
                    f'<button class="btnf btnf-{slug} live" disabled>{esc(_SPEC_CTA)}</button>')
            rows.append(
                f'<div class="ex-caption"><strong>{esc(name)}</strong> &mdash; {style_word}; '
                'content-hugging (inline-flex, non-stretch stage)</div>'
                + _state_matrix(_sw, live,
                                label=f"{name} · hover / press / focus inside the iframe"))
        if rows:
            return "".join(rows)
        return ('<div class="ex-caption">Brand realization &mdash; the measured filled button:</div>'
                + cr.render_button(doc, _GALLERY_CTX, {"label": _SPEC_CTA}))
    matrix = _state_matrix(
        lambda cls: _arrow(_SPEC_CTA, cls),
        '<a class="act live" href="#">' + _SPEC_CTA + ' <span class="arrow">&rarr;</span></a>'
        '<button class="act live" disabled>' + _SPEC_CTA + ' <span class="arrow">&rarr;</span></button>',
    )
    return ('<div class="ex-caption">Brand realization &mdash; the arrow link the CTA remaps to:</div>'
            f'{matrix}'
            '<div class="ex-rule"></div>'
            '<div class="ex-caption">Synthesized / avoid &mdash; filled button, never used on page:</div>'
            '<div class="strike"><button class="avoid-btn" tabindex="-1">' + _SPEC_CTA + '</button></div>')


def render_icon_button(doc, key, item):
    matrix = _state_matrix(
        lambda cls: f'<a class="act {cls}" href="#" tabindex="-1" aria-label="Next"><span class="arrow">&rarr;</span></a>',
        '<a class="act live" href="#" aria-label="Next"><span class="arrow">&rarr;</span></a>'
        '<button class="act live" disabled aria-label="Next"><span class="arrow">&rarr;</span></button>',
    )
    if _brand_law(doc)["cta"] == "filled":
        # no measured icon-button in the catalog: show the typographic stand-in
        # without asserting a prohibition the brand doesn't carry.
        return ('<div class="ex-caption">No measured icon-button &mdash; typographic arrow stand-in:</div>'
                f'{matrix}')
    return ('<div class="ex-caption">Brand realization &mdash; remaps to a typographic arrow/slash link:</div>'
            f'{matrix}'
            '<div class="ex-rule"></div>'
            '<div class="ex-caption">Synthesized / avoid &mdash; filled icon button, never used:</div>'
            '<div class="strike"><button class="avoid-iconbtn" tabindex="-1" aria-label="avoid">&rarr;</button></div>')


def render_pill(doc, key, item):
    tag = _specimen(doc)["links"][0]
    use = ""
    prims = doc.get("primitives")
    if isinstance(prims, dict) and isinstance(prims.get(key), dict):
        use = str(prims[key].get("use", "")).lower()
    if use != "never":
        return (f'<div class="ex-caption">Label chip at the brand radius:</div>'
                f'<span class="avoid-pill">{esc(tag)}</span>')
    return ('<div class="ex-caption">Brand realization &mdash; a tag remaps to an eyebrow-register label:</div>'
            f'<span class="ex-eyebrow">{esc(tag)}</span>'
            '<div class="ex-rule"></div>'
            '<div class="ex-caption">Synthesized / avoid &mdash; rounded chip, never used:</div>'
            f'<div class="strike"><span class="avoid-pill">{esc(tag)}</span></div>')


def render_badge(doc, key, item):
    law = _brand_law(doc)
    shape = "square" if law["square"] else "brand-radius"
    return ('<div class="surface-dark"><span class="ex-marker">New</span></div>'
            f'<div class="ex-caption">Flat {shape} accent marker &mdash; accent-legal surfaces only</div>')


def render_input(doc, key, item):
    # Law-first (blocker 7): a boxed-field brand shows its REAL catalog input; the
    # underline specimen (and its "underline only" law prose) is the underline brands'.
    if cr.input_shape(doc) == "boxed":
        return ('<div class="ex-caption">Boxed field &mdash; brand input radius, border and fill</div>'
                + cr.render_input(doc, _GALLERY_CTX, {"placeholder": "Enter your email"}))
    def sw(cls):
        return (f'<span class="ex-field {cls}" style="min-width:9rem">'
                '<span class="ex-input">you@email.com</span></span>')
    live = ('<span class="ex-field live" style="min-width:11rem">'
            '<input class="ex-input" type="email" placeholder="Enter your email"></span>'
            '<span class="ex-field is-disabled" style="min-width:9rem">'
            '<input class="ex-input" type="email" value="locked@email.com" disabled></span>')
    return ('<div class="ex-caption">Underline only &mdash; no box or fill, inline text submit</div>'
            f'{_state_matrix(sw, live)}')


def render_textarea(doc, key, item):
    return ('<div class="ex-field" style="align-items:flex-start;min-height:3.5rem">'
            '<span class="ex-input">Multi-line entry&hellip;</span></div>'
            '<div class="ex-caption">Follows the brand\'s field grammar (same shape as the input)</div>')


def render_select(doc, key, item):
    return (f'<span class="ex-select">Select {esc(_specimen(doc)["links"][0].lower())} '
            '<span aria-hidden="true">&#9662;</span></span>'
            '<div class="ex-caption">Trigger in the brand control-text register; flat menu panel</div>')


def render_form_field(doc, key, item):
    return ('<span class="ex-eyebrow">Email address</span>'
            '<div class="ex-field"><span class="ex-input">you@email.com</span></div>'
            '<div class="ex-caption">Label in the brand eyebrow register above the brand field control</div>')


def render_checkbox(doc, key, item):
    def sw(cls):
        # default/hover/focus/disabled show the empty OFF box; pressed shows ON.
        on = "is-on" if cls == "is-active" else ""
        return f'<span class="ex-check {cls} {on}"><span class="box">&#10003;</span></span>'
    live = ('<label class="ex-check live"><input type="checkbox">'
            '<span class="box">&#10003;</span><span>Subscribe (toggle me)</span></label>'
            '<label class="ex-check disabled"><input type="checkbox" disabled>'
            '<span class="box">&#10003;</span><span>Locked</span></label>')
    return ('<div class="ex-caption">Empty field-surface box + 1px hairline when off; solid ink fill + inverse check on select</div>'
            f'{_state_matrix(sw, live)}')


def render_radio(doc, key, item):
    sp = _specimen(doc)
    a, b = sp["links"][0], (sp["links"][1] if len(sp["links"]) > 1 else "Other")
    law = _brand_law(doc)
    cap = ("Square selector (radius 0 overrides the round default)"
           if law["square"] else "Selector at the brand radius")
    return (f'<span class="ex-check radio is-on"><span class="box">&#9632;</span><span>{esc(a)}</span></span>'
            f'<span class="ex-check radio"><span class="box"></span><span>{esc(b)}</span></span>'
            f'<div class="ex-caption">{cap}</div>')


def render_toggle(doc, key, item):
    def sw(cls):
        # default/hover/focus/disabled show the empty OFF switch (knob left);
        # pressed shows the flat dark ON switch (knob right).
        on = "is-on" if cls == "is-active" else ""
        return (f'<span class="ex-switch {cls} {on}">'
                '<span class="track"><span class="knob"></span></span></span>')
    live = ('<label class="ex-switch live"><input type="checkbox">'
            '<span class="track"><span class="knob"></span></span><span>Updates (toggle me)</span></label>'
            '<label class="ex-switch disabled"><input type="checkbox" disabled>'
            '<span class="track"><span class="knob"></span></span><span>Locked</span></label>')
    return ('<div class="ex-caption">Sliding switch &mdash; empty track when off (knob left); '
            'solid ink fill when on (knob right)</div>'
            f'{_state_matrix(sw, live)}')


def render_slider(doc, key, item):
    return ('<div class="ex-slider"><span class="fill"></span><span class="handle"></span></div>'
            '<div class="ex-caption">1px track + flat handle &mdash; no decorative thumb</div>')


def render_file_upload(doc, key, item):
    return ('<span class="ex-select">Attach a file <span aria-hidden="true">&rarr;</span></span>'
            '<div class="ex-caption">Trigger in the brand control grammar &mdash; no dropzone box</div>')


def render_divider(doc, key, item):
    sp = _specimen(doc)
    a, b = sp["links"][0], (sp["links"][1] if len(sp["links"]) > 1 else "Other")
    return (f'<div class="ex-rows"><div class="ex-row"><span class="ex-label">{esc(a)}</span>'
            '<span class="ex-counter" style="font-size:1.25rem">01</span></div>'
            f'<div class="ex-row"><span class="ex-label">{esc(b)}</span>'
            '<span class="ex-counter" style="font-size:1.25rem">02</span></div></div>'
            '<div class="ex-caption">1px ruled action-row bar inside a panel &mdash; never a section seam</div>')


def render_quote(doc, key, item):
    sp = _specimen(doc)
    law = _brand_law(doc)
    return (f'<blockquote class="ex-quote">{esc(sp["headline"])}</blockquote>'
            f'<div class="ex-eyebrow">&mdash; {esc(sp["name"])}</div>'
            f'<div class="ex-caption">Display-register quote ({esc(law["display"])}), open on the canvas; '
            'attribution as margin eyebrow</div>')


def render_stat(doc, key, item):
    sp = _specimen(doc)
    label = sp["links"][2] if len(sp["links"]) > 2 else sp["links"][0]
    return (f'<div class="ex-counter">1 / 6</div><div class="ex-eyebrow">{esc(label)}</div>'
            '<div class="ex-caption">Display-register numeral + eyebrow-register label &mdash; open, never boxed</div>')


def render_rating(doc, key, item):
    return ('<div class="ex-counter" style="font-size:1.5rem">4.8 / 5</div>'
            '<div class="ex-caption">Fraction numeral &mdash; no colored star glyphs</div>')


def render_list(doc, key, item):
    rows = "".join(f'<div class="ex-li">{esc(t)}</div>' for t in _specimen(doc)["links"][:3])
    return (f'<div class="ex-list">{rows}</div>'
            '<div class="ex-caption">Rows separated by 1px ruled bars &mdash; brand marker, never decorative bullets</div>')


def render_code(doc, key, item):
    # specimen host derives from the BRAND name (was a hardcoded woodwave.io literal —
    # AS-06 shape: one brand's DNA rendered into every brand's gallery).
    host = ((doc.get("brand") or {}).get("name") or "brand").lower().replace(" ", "")
    return (f'<div class="surface-darkest"><pre class="ex-code">curl {esc(host)}.example/api\n'
            '  &gt; { "open": true }</pre></div>'
            '<div class="ex-caption">Monospace on near-black, radius 0 &mdash; off-brand, used rarely</div>')


def render_progress(doc, key, item):
    return ('<div class="ex-progress"><span class="fill"></span></div>'
            '<div class="ex-caption">Thin square 1px bar, solid fill &mdash; no rounding/gradient</div>')


def render_tooltip(doc, key, item):
    law = _brand_law(doc)
    return ('<span class="ex-tip">More detail</span>'
            f'<div class="ex-caption">Flat dark panel, no shadow; {esc(law["body"])} micro-text</div>')


def render_spacer(doc, key, item):
    return ('<div class="ex-spacer"><span>module-gap 7.5rem</span></div>'
            '<div class="ex-caption">Explicit structural gap from the editorial module-gap ladder</div>')


PRIMITIVE_RENDERERS = {
    "heading": render_heading, "subheading": render_subheading, "eyebrow": render_eyebrow,
    "paragraph": render_paragraph, "label": render_label, "caption": render_caption,
    "image": render_image, "video": render_video, "avatar": render_avatar,
    "illustration": render_illustration, "logo": render_logo, "icon": render_icon,
    "link": render_link, "cta": render_cta, "button": render_button,
    "icon-button": render_icon_button, "pill": render_pill, "badge": render_badge,
    "input": render_input, "textarea": render_textarea, "select": render_select,
    "form-field": render_form_field, "checkbox": render_checkbox, "radio": render_radio,
    "toggle": render_toggle, "slider": render_slider, "file-upload": render_file_upload,
    "divider": render_divider, "quote": render_quote, "stat": render_stat,
    "rating": render_rating, "list": render_list, "code": render_code,
    "progress": render_progress, "tooltip": render_tooltip, "spacer": render_spacer,
}


# ── per-block faithful example renderers ────────────────────────────────────────

def render_b_header(doc, key, item):
    # SSOT: the header block composes eyebrow + heading + arrow cta via the shared
    # renderer; copy is the BRAND's (measured headline + derived CTA), blocker 7.
    sp = _specimen(doc)
    return cr.render_header(doc, _GALLERY_CTX, {
        "eyebrow": cr.eyebrow_prefix(doc) + sp["links"][0], "heading": sp["headline"], "level": "display",
        "cta": sp["cta"]})


def _nav_demo_role(doc) -> str:
    """The surface ROLE the navbar/logo chrome demos render on. The brand's measured
    bar color resolves to one of its own roles (cr.nav_surface_role); a TRANSPARENT
    bar demos on the surface its measured link ink needs (light link ink → the bar
    sits over a dark band → the brand's inverse role), else the base canvas."""
    role = cr.nav_surface_role(doc)
    if role:
        return role
    surfaces = (doc.get("tokens") or {}).get("surfaces") or {}
    link = ((doc.get("navbar") or {}).get("measured") or {}).get("link") or {}
    rgba = cr._parse_color_rgba(link.get("color"))
    if rgba and sum(rgba[:3]) / 3 > 150 and "surface/inverse" in surfaces:
        return "surface/inverse"
    return "surface/primary" if "surface/primary" in surfaces \
        else next(iter(surfaces), "surface/primary")


def render_b_navbar(doc, key, item):
    # SSOT (nav-fix 2026-07): the navbar demo is the SHARED render_navbar on the
    # brand's RESOLVED chrome surface — the same builder + props derivation the
    # composed page uses. Separator/casing/CTA-shape all ride brand declarations;
    # nothing here assumes a dark bar, slash links, or a typographic cta.
    role = _nav_demo_role(doc)
    surfaces = (doc.get("tokens") or {}).get("surfaces") or {}
    ctx = cr.make_context(doc, role, surfaces.get(role) or {})
    props = dict(cs._navbar_props(doc))
    props.pop("logo", None)  # image logo files live beside the composed page, not here
    nav = cr.render_navbar(doc, ctx, props)
    return (f'<div class="cmp-chrome-demo" data-surface-frame="{esc(role)}">{nav}</div>'
            f'<div class="ex-caption">Bar on the brand&rsquo;s extracted chrome surface '
            f'({esc(role)}); links + cta in the brand&rsquo;s own registers</div>')


def render_b_footer(doc, key, item):
    # SSOT: the footer block is rendered by the SHARED catalog renderer
    # (component_render.render_footer) with the SAME content source the page composer
    # uses (component_render.footer_content) — ONE renderer + ONE content derivation for
    # both the gallery and the composed page. Content is the brand's own extracted
    # footer (sitemap/directory, TEXT social row, legal line); a brand with no footer
    # extracted gets an honest caption, never a fabricated social row. The demo surface
    # is the brand's MEASURED chrome-footer surface resolved to one of its own roles
    # (compose_page.footer_surface_role — nav-fix 2026-07: a light-chrome brand demos
    # light, never an assumed near-black band); the wrapper's data-surface-frame alias
    # block scopes the --c-* vars, and the sitemap centers + right-sizes itself via the
    # contained clamp in component_render.COMPONENT_CSS.
    if not (doc.get("footer") or {}):
        return ('<div class="ex-caption">No footer extracted for this brand &mdash; the '
                'composed page ends without a closing bookend (nothing is invented)</div>')
    role = cp.footer_surface_role(doc)
    surfaces = (doc.get("tokens") or {}).get("surfaces") or {}
    ctx = cr.make_context(doc, role, surfaces.get(role) or {})
    foot = cr.render_footer(doc, ctx, cr.footer_content(doc))
    return (f'<div class="cmp-footer-demo" data-surface-frame="{esc(role)}">{foot}</div>'
            '<div class="ex-caption">Closing bookend &mdash; the brand&rsquo;s extracted footer '
            '(sitemap, text social row + muted legal); shared <code>render_footer</code>, no boxes</div>')


def render_b_media_text(doc, key, item):
    sp = _specimen(doc)
    a, b = sp["links"][0], (sp["links"][1] if len(sp["links"]) > 1 else "Other")
    return ('<div style="display:grid;grid-template-columns:1fr 1fr;gap:0">'
            '<div class="ex-photo" style="aspect-ratio:auto">PHOTO</div>'
            f'<div class="surface-panel"><div class="ex-h3">{esc(sp["headline"])}</div>'
            '<div class="ex-rows" style="margin-top:0.75rem">'
            f'<div class="ex-row"><span class="ex-label">{esc(a)}</span>'
            f'{_arrow(sp["cta"])}</div>'
            f'<div class="ex-row"><span class="ex-label">{esc(b)}</span>'
            f'{_arrow(sp["cta"])}</div></div></div></div>'
            '<div class="ex-caption">Two flush halves, gap 0, hard cut; panel surface child of inverse</div>')


def render_b_content_block(doc, key, item):
    sp = _specimen(doc)
    return ('<div class="ex-photo" style="aspect-ratio:16/9">PHOTO</div>'
            f'<div class="ex-caption">Fig. 02 &mdash; {esc(sp["name"])}</div>'
            f'<div class="ex-h3" style="margin-top:0.5rem">{esc(sp["headline"])}</div>'
            '<p class="ex-body">Narrow offset body, roughly a third of the container.</p>'
            f'{_arrow("Read more")}')


def render_b_cta_block(doc, key, item):
    sp = _specimen(doc)
    action = (cr.render_button(doc, _GALLERY_CTX, {"label": sp["cta"]})
              if _brand_law(doc)["cta"] == "filled" else _arrow(sp["cta"]))
    return ('<div style="text-align:center;display:flex;flex-direction:column;align-items:center;gap:1rem">'
            f'<div class="ex-eyebrow">/ {esc(sp["links"][0])}</div>'
            f'<div class="ex-display">{esc(sp["headline"])}</div>'
            f'{action}</div>'
            '<div class="ex-caption">Narrow centered stack; action in the brand\'s resolved CTA shape</div>')


def render_b_form(doc, key, item):
    # SSOT: the form block composes the underline field + inline arrow submit via the
    # shared catalog renderer (the SAME render_form the section composer uses).
    form = cr.render_form(doc, _GALLERY_CTX, {
        "eyebrow": cr.eyebrow_prefix(doc) + "Newsletter", "placeholder": "Enter your email", "submit": "Subscribe"})
    return (form + '<div class="ex-caption">Field + inline submit in the brand\'s field/CTA grammar</div>')


def render_b_card(doc, key, item):
    return ('<div class="ex-caption"><strong>Card treatment follows the brand law.</strong></div>'
            '<div class="ex-photo" style="aspect-ratio:16/9">PHOTO</div>'
            f'<div class="ex-caption">Fig. 03 &mdash; {esc(_specimen(doc)["name"])}</div>'
            '<div class="ex-rule"></div>'
            '<div class="ex-caption">Bounded units appear only where the brand\'s surface rules allow.</div>')


def render_b_testimonial(doc, key, item):
    sp = _specimen(doc)
    law = _brand_law(doc)
    return (f'<blockquote class="ex-quote">{esc(sp["headline"])}</blockquote>'
            '<div style="display:flex;align-items:center;gap:0.75rem;margin-top:0.75rem">'
            '<div class="ex-photo is-square" style="max-width:3rem;margin:0">A</div>'
            f'<span class="ex-eyebrow">{esc(sp["name"])} &mdash; Customer</span></div>'
            f'<div class="ex-caption">Open {esc(law["display"])} quote; name/role as margin eyebrow</div>')


def render_b_stat_block(doc, key, item):
    sp = _specimen(doc)
    labels = (sp["links"] + ["Teams", "Regions"])[:3]
    cells = "".join(
        f'<div><div class="ex-counter">{n}</div><div class="ex-eyebrow">{esc(lb)}</div></div>'
        for n, lb in zip(("12", "40k", "6"), labels))
    return (f'<div style="display:flex;gap:2.5rem">{cells}</div>'
            '<div class="ex-caption">Row of display-register numerals + eyebrow labels; open, no boxes</div>')


def render_b_accordion(doc, key, item):
    sp = _specimen(doc)
    a, b = sp["links"][0], (sp["links"][1] if len(sp["links"]) > 1 else "Other")
    return ('<div class="ex-rows">'
            f'<div class="ex-row"><span class="ex-h3" style="font-size:1.125rem">{esc(a)}</span>'
            '<span style="font-family:var(--font-heading)">&#8260;</span></div>'
            f'<div class="ex-row"><span class="ex-h3" style="font-size:1.125rem">{esc(b)}</span>'
            '<span style="font-family:var(--font-heading)">&#8260;</span></div></div>'
            '<div class="ex-caption">Display-register triggers separated by 1px ruled bars</div>')


def render_b_accordion_item(doc, key, item):
    sp = _specimen(doc)
    law = _brand_law(doc)
    return ('<div class="ex-row" style="padding-top:0"><span class="ex-h3" style="font-size:1.125rem">'
            f'{esc(sp["links"][0])}</span><span style="font-family:var(--font-heading)">&#8260;</span></div>'
            '<p class="ex-body">Expanded body copy in the brand body register.</p>'
            f'<div class="ex-caption">Trigger + {esc(law["body"])} body; typographic indicator, never a chevron chip</div>')


def render_b_tabs(doc, key, item):
    links = (_specimen(doc)["links"] + ["More"])[:3]
    return ('<div style="display:flex;gap:1.5rem">'
            f'<span class="ex-label" style="border-bottom:2px solid var(--ink);padding-bottom:0.3rem">{esc(links[0])}</span>'
            f'<span class="ex-label" style="color:var(--ink-muted)">{esc(links[1])}</span>'
            f'<span class="ex-label" style="color:var(--ink-muted)">{esc(links[2])}</span></div>'
            '<div class="ex-caption">Typographic triggers, underline active state</div>')


def render_b_logo_bar(doc, key, item):
    return ('<div class="ex-eyebrow">In partnership with</div>'
            '<div style="display:flex;gap:1.75rem;margin-top:0.6rem;font-family:var(--font-heading);'
            'text-transform:var(--case-control-text, none);color:var(--ink)"><span>ARTC</span><span>FOLIO</span><span>KILN</span></div>'
            '<div class="ex-caption">Monochrome wordmarks in a flush row + eyebrow caption; no tiles</div>')


def render_b_feature_item(doc, key, item):
    sp = _specimen(doc)
    return ('<div style="font-family:var(--font-heading);font-size:1.5rem;color:var(--ink)">&#8599;</div>'
            f'<div class="ex-h3" style="margin-top:0.5rem">{esc(sp["links"][0])}</div>'
            '<p class="ex-body">Feature body copy in the brand register.</p>'
            f'{_arrow("Learn more")}'
            '<div class="ex-caption">Open grid cell &mdash; thin icon + heading + body + action; no box</div>')


def render_b_pricing_card(doc, key, item):
    sp = _specimen(doc)
    return ('<div class="ex-rows"><div class="ex-row" style="padding-top:0">'
            '<div><span class="ex-counter" style="font-size:1.5rem">01</span> '
            f'<span class="ex-eyebrow">{esc(sp["links"][0])}</span></div>'
            f'{_arrow(sp["cta"])}</div></div>'
            '<div class="ex-caption">Plan as a ruled action row (numeral + label + action)</div>')


def render_b_banner(doc, key, item):
    sp = _specimen(doc)
    return ('<div class="surface-dark" style="display:flex;align-items:center;justify-content:space-between;gap:1rem">'
            f'<span class="ex-label" style="color:var(--ink-inverse)">{esc(sp["headline"])}</span>'
            '<span style="display:flex;gap:1.25rem;align-items:center">'
            '<a class="act" href="#" style="color:var(--accent)">Details <span class="arrow">&rarr;</span></a>'
            '<span style="color:var(--ink-inverse-muted);font-family:var(--font-heading)">&times;</span></span></div>'
            '<div class="ex-caption">Slim strip on the brand chrome surface; text + link action; typographic dismiss</div>')


def render_b_modal(doc, key, item):
    law = _brand_law(doc)
    panel_word = "hard-edged square panel" if law["square"] else "panel at the brand radius"
    return ('<div style="background:rgba(0,0,0,0.55);padding:1.25rem">'
            '<div class="surface-panel"><div style="display:flex;justify-content:space-between;align-items:start">'
            '<div class="ex-h3">Before you go</div>'
            '<span style="font-family:var(--font-heading)">&times;</span></div>'
            f'<p class="ex-body" style="margin-top:0.5rem">A {panel_word} on a flat scrim.</p>'
            f'{_arrow("Got it")}</div></div>'
            '<div class="ex-caption">Panel per the brand radius law, no shadow; flat scrim; typographic close</div>')


def render_b_dropdown_menu(doc, key, item):
    links = (_specimen(doc)["links"] + ["More"])[:3]
    rows = "".join(f'<span class="ex-label" style="color:var(--ink-inverse)">{esc(x)}</span>' for x in links)
    return (f'{_arrow(links[0])}'
            f'<div class="surface-dark" style="margin-top:0.5rem;display:flex;flex-direction:column;gap:0.5rem">{rows}</div>'
            '<div class="ex-caption">Flat menu panel; typographic links and trigger</div>')


def render_b_breadcrumb(doc, key, item):
    links = (_specimen(doc)["links"] + ["More"])[:2]
    return (f'<div class="ex-eyebrow">Home <span style="opacity:.5">/</span> {esc(links[0])} '
            f'<span style="opacity:.5">/</span> {esc(links[1])}</div>'
            '<div class="ex-caption">Uppercase trail with the brand separator; muted</div>')


def render_b_pagination(doc, key, item):
    return ('<div style="display:flex;align-items:center;gap:1.5rem">'
            '<a class="act" href="#"><span class="arrow" style="transform:scaleX(-1)">&rarr;</span> Prev</a>'
            '<span class="ex-counter" style="font-size:1.25rem">1 / 6</span>'
            f'{_arrow("Next")}</div>'
            '<div class="ex-caption">Fraction counter + prev/next arrow links; no numbered chips</div>')


def render_b_table(doc, key, item):
    return ('<div class="ex-rows"><div class="ex-row" style="padding-top:0">'
            '<span class="ex-eyebrow">Day</span><span class="ex-eyebrow">Hours</span></div>'
            '<div class="ex-row"><span class="ex-body" style="max-width:none">Tue&ndash;Fri</span>'
            '<span class="ex-body" style="max-width:none">10&ndash;18</span></div>'
            '<div class="ex-row"><span class="ex-body" style="max-width:none">Sat&ndash;Sun</span>'
            '<span class="ex-body" style="max-width:none">09&ndash;20</span></div></div>'
            '<div class="ex-caption">Rows on 1px ruled bars; eyebrow column headers; no zebra/borders</div>')


def render_b_carousel(doc, key, item):
    return ('<div style="display:flex;gap:0.5rem"><div class="ex-photo" style="flex:1">01</div>'
            '<div class="ex-photo" style="flex:1;opacity:0.6">02</div></div>'
            '<div style="display:flex;align-items:center;justify-content:space-between;margin-top:0.5rem">'
            '<span class="ex-counter" style="font-size:1.25rem">1 / 6</span>'
            f'{_arrow("Next")}</div>'
            '<div class="ex-caption">Hard-edged image track + fraction counter + arrow controls; low motion</div>')


def render_b_steps(doc, key, item):
    return ('<div class="ex-rows">'
            '<div class="ex-row" style="padding-top:0"><span class="ex-counter" style="font-size:1.5rem">01</span>'
            '<span class="ex-h3" style="font-size:1.125rem;flex:1;margin-left:1rem">Book online</span></div>'
            '<div class="ex-row"><span class="ex-counter" style="font-size:1.5rem">02</span>'
            '<span class="ex-h3" style="font-size:1.125rem;flex:1;margin-left:1rem">Arrive & scan</span></div></div>'
            '<div class="ex-caption">Display-register numerals + heading-register labels on ruled bars; never boxed</div>')


def render_b_step_item(doc, key, item):
    return ('<div style="display:flex;gap:1rem;align-items:baseline">'
            '<span class="ex-counter" style="font-size:1.75rem">01</span>'
            '<div><div class="ex-h3" style="font-size:1.125rem">Book online</div>'
            '<p class="ex-body">Choose a date and time slot in advance.</p></div></div>'
            '<div class="ex-caption">Didone numeral + heading + Inter body; no circular badge</div>')


BLOCK_RENDERERS = {
    "header": render_b_header, "navbar": render_b_navbar, "footer": render_b_footer,
    "media-text": render_b_media_text, "content-block": render_b_content_block,
    "cta-block": render_b_cta_block, "form": render_b_form, "card": render_b_card,
    "testimonial": render_b_testimonial, "stat-block": render_b_stat_block,
    "accordion": render_b_accordion, "accordion-item": render_b_accordion_item,
    "tabs": render_b_tabs, "logo-bar": render_b_logo_bar, "feature-item": render_b_feature_item,
    "pricing-card": render_b_pricing_card, "banner": render_b_banner, "modal": render_b_modal,
    "dropdown-menu": render_b_dropdown_menu, "breadcrumb": render_b_breadcrumb,
    "pagination": render_b_pagination, "table": render_b_table, "carousel": render_b_carousel,
    "steps": render_b_steps, "step-item": render_b_step_item,
}


# ── generic fallback (token-faithful) for any catalog item without a renderer ────

def render_generic(doc, key, item, contract):
    intent = (contract or {}).get("intent", "")
    slots = (contract or {}).get("slots") or {}
    slot_names = ", ".join(slots.keys()) if isinstance(slots, dict) else ""
    parts = [f'<div class="ex-h3" style="font-size:1.125rem">{esc(key)}</div>']
    if intent:
        parts.append(f'<p class="ex-body">{esc(intent)}</p>')
    if slot_names:
        parts.append(f'<div class="ex-caption">slots: {esc(slot_names)}</div>')
    return "".join(parts)


# ── Tier 3: extracted layout patterns (project-tier layout-library.yaml) ─────────
# Each pattern is rendered through the REAL archetype composers: we find a brand.yaml
# layout that references the pattern (patternRef.id) and run it through
# compose_section.build_document — the same path the composed pages use — writing a
# standalone per-pattern document that the gallery embeds as an iframe row. No
# hand-built HTML mockups. compose_section.py is imported, never modified.

def load_layout_library(brand_yaml: Path) -> list[dict]:
    """Read the project-tier layout library sitting next to brand.yaml. Returns []
    when absent so brands without a library render the gallery unchanged."""
    lib = brand_yaml.parent / "layout-library.yaml"
    if not lib.exists():
        return []
    data = yaml.safe_load(lib.read_text()) or {}
    return data.get("patterns") or []


def layout_for_pattern(doc, pattern_id: str):
    """First brand.yaml layout whose explicit patternRef points at this pattern
    (canonical story order = first wins)."""
    for layout in doc.get("layouts", []) or []:
        ref = layout.get("patternRef") or {}
        if isinstance(ref, dict) and ref.get("id") == pattern_id:
            return layout
    return None


# ── Tier-3 DEMO copy hydration (remote-fix Phase C) ──────────────────────────────
# A brand WITHOUT an authored section-copy.yaml used to compose every pattern demo
# from empty copy (_SafeCopy), so each row degenerated to the wordmark + a bare
# arrow. The gallery now synthesizes STRUCTURAL demo content per pattern from the
# brand's OWN evidence — layout-library contentShape slots + the brand layout's
# slot roles/assets — and registers it through the SAME runtime copy surfaces the
# composition adapter uses (cs.LAYOUT_COPY). Demo text is brand-derived specimen
# prose (brand name / navbar cta / quoted literals the analyst embedded in slot
# roles); demo media binds the layout slots' real `assets:` files. Brands WITH
# authored copy are untouched (the authored layers win, this path never runs).

# quoted literal inside an analyst-authored slot role — REAL captured copy
# (e.g. a microlabel role carrying the observed caption in quotes).
_ROLE_QUOTE_RX = re.compile(r"[\u2018\u201c'\"]([^\u2019\u201d'\"]{4,90})[\u2019\u201d'\"]")


def _demo_hydration_active(doc) -> bool:
    """Full specimen-copy hydration only when the brand authored NO section-copy
    layers at all (the pre-authoring gallery state)."""
    return not cs.brand_section_copy(doc) and not cs.brand_layout_copy(doc)


def _layout_needs_asset_hydration(doc, layout) -> bool:
    """A brand layout WITHOUT a blockMapping renders zero slot fragments through
    the plain composer path (the composers then degrade to wordmark fallbacks),
    so its demo can only realize slot ``assets:`` bindings (logo strips, card/
    badge runs, placed media) and authored copy through the composition adapter.
    It takes the demo path when it declares slot assets OR the brand authored a
    layoutCopy entry for it. Layouts WITH a blockMapping render their full
    anatomy directly (e.g. WoodWave's) and never take the demo path. A v1
    ``componentMapping`` layout still hydrates: its mapping's Text props are the
    v1 schema's partial copy, and the adapter path is how its pattern demos
    rendered before the brand's copy layers were authored."""
    if not isinstance(layout, dict) or layout.get("blockMapping"):
        return False
    if any(isinstance(s, dict) and s.get("assets") for s in (layout.get("slots") or [])):
        return True
    return bool(cs.brand_layout_copy(doc).get(layout.get("id")))


def _demo_text(role_text: str, kind: str, sp: dict, use: str,
               authored: dict | None = None) -> str:
    """Text for one demo slot. Preference order: the brand's AUTHORED copy layer for
    this layout (section-copy.yaml — real site voice), then a quoted literal from the
    analyst's slot role (real captured copy), then register-appropriate structural
    prose derived from the ACTIVE brand (name / cta) — never another brand's voice.
    A brand that authored copy layers but no value for this register renders EMPTY
    copy (the device elides), matching the real section's anatomy."""
    authored = authored or {}
    keymap = {"eyebrow": ("eyebrow", "caption"), "heading": ("heading",),
              "body": ("body", "text", "subhead"), "cta": ("cta",)}
    for k in keymap.get(kind, ()):
        if authored.get(k):
            return str(authored[k])
    m = _ROLE_QUOTE_RX.search(role_text or "")
    if m:
        return m.group(1).strip()
    if authored:
        return ""  # authored voice exists; don't blend specimen prose into it
    if kind == "eyebrow":
        return f"{sp['name']} {use} specimen"
    if kind == "heading":
        return f"A {use} pattern in the {sp['name']} register"
    if kind == "body":
        return (f"Structural demo copy: the pattern's surfaces, registers and components are "
                f"{sp['name']}'s real extracted system; authored copy replaces this text once "
                "section-copy.yaml is extracted.")
    if kind == "cta":
        return sp["cta"]
    return f"{use} {kind} specimen"


def _demo_section_for_pattern(doc, pat, layout) -> dict:
    """Build a composition.v1-shaped demo SECTION for one pattern + its referencing
    brand layout, so the PROVEN composition adapter (compose_from_composition.
    composition_to_layout) does the slot→blockMapping/copy binding — logo walls,
    hero copy, split translators and placement all reuse the tested path. When the
    brand authored copy layers (section-copy.yaml), the layout's authored entry
    feeds every text slot so the demo carries the REAL site voice over the same
    asset-bound structure."""
    sp = _specimen(doc)
    pid = pat.get("id", "")
    use = str(pat.get("useCase") or "section")
    authored = dict(cs.brand_layout_copy(doc).get(layout.get("id")) or {})
    authored_items = authored.get("items") if isinstance(authored.get("items"), list) else None
    shape_slots = {s.get("name"): s for s in ((pat.get("contentShape") or {}).get("slots") or [])
                   if isinstance(s, dict) and s.get("name")}
    lay_slots = [s for s in (layout.get("slots") or []) if isinstance(s, dict)]

    def _asset_label(fname: str) -> str:
        """Human words from the brand's own asset filename (data cleanup, no restyle)."""
        stem = Path(str(fname)).stem
        for pref in ("avatar-", "card-", "img-", "photo-"):
            if stem.startswith(pref):
                stem = stem[len(pref):]
        return stem.replace("-", " ").replace("_", " ").strip() or stem

    slots: list[dict] = []
    seen: set = set()
    for ls in lay_slots:
        name = str(ls.get("name") or f"slot-{len(slots)}")
        seen.add(name)
        role = str(ls.get("role") or shape_slots.get(name, {}).get("role") or name)
        shape = shape_slots.get(name) or {}
        lower = f"{name} {role}".lower()
        # the adapter's _by_role matchers scan ROLE prose for semantic keywords —
        # lead with the slot NAME so "heading — section h2" hits the "heading" probe.
        entry: dict = {"name": name, "role": f"{name} — {role}" if role != name else name}
        for k in ("textLen", "sizeClass", "width", "z", "mediaAspect"):
            if shape.get(k):
                entry[k] = shape[k]
        assets = [str(a) for a in (ls.get("assets") or []) if a]
        is_media = (ls.get("type") == "media") or bool(shape.get("mediaAspect"))
        if (is_media or assets) and ("logo" in lower or len(assets) >= 6):
            entry["contract"] = "logo"
            entry["copy"] = list(assets)  # coerced to asset items by _sanitize_assets
        elif len(assets) >= 2:
            # a multi-asset slot is a repeatable MODULE run (cards / avatars): one
            # module per real asset, labeled from the brand's own filenames — or
            # from the authored per-module items when the counts line up.
            entry["contract"] = "card"
            entry["copy"] = [
                {"heading": ((authored_items[i].get("heading") or _asset_label(a))
                             if authored_items and i < len(authored_items)
                             else _asset_label(a)),
                 "text": ((authored_items[i].get("body") or "")
                          if authored_items and i < len(authored_items)
                          else _demo_text(role, "body", sp, use, authored)),
                 "asset": a, "alt": _asset_label(a)}
                for i, a in enumerate(assets)]
        elif is_media or assets:
            entry["contract"] = "image"
            if assets:
                entry["asset"] = {"src": assets[0], "alt": f"{sp['name']} {name}"}
        elif authored_items and any(k in lower for k in ("card", "module", "prop", "hub")) \
                and not any(k in lower for k in ("cta", "button", "link", "icon")):
            # an asset-less repeatable module slot with AUTHORED per-module items
            # (e.g. a product-card grid whose icons live in a sibling slot)
            entry["contract"] = "card"
            entry["copy"] = [{"heading": it.get("heading") or it.get("label") or "",
                              "text": it.get("body") or it.get("text") or "",
                              **({"link": it["cta"]} if it.get("cta") else {})}
                             for it in authored_items]
        elif any(k in lower for k in ("eyebrow", "microlabel", "caption", "label")):
            # single-key copy: a `text` twin here would echo into the translators'
            # lede/body fallbacks (a v1 header dict carries its lede under `text`).
            entry["contract"] = "eyebrow"
            entry["copy"] = {"eyebrow": _demo_text(role, "eyebrow", sp, use, authored)}
        elif any(k in lower for k in ("heading", "title", "display", "h1", "h2", "header")):
            entry["contract"] = "heading"
            entry["copy"] = {"heading": _demo_text(role, "heading", sp, use, authored)}
            # roles like "section header" miss _props_for's heading keywords
            # ("title"/"heading"), so the flow composer would drop the copy; a
            # `text` twin would echo into conversion-lede fallbacks instead,
            # so surface the keyword in the role text itself.
            if "heading" not in lower and "title" not in lower:
                entry["role"] += " heading"
        elif any(k in lower for k in ("action", "cta", "button", "pill")):
            entry["contract"] = "button"
            entry["copy"] = {"label": _demo_text(role, "cta", sp, use, authored) or sp["cta"]}
            slots.append(entry)
            # a role naming BOTH a primary and a secondary action gets two demo buttons
            if ("primary" in lower or "filled" in lower) and \
                    ("secondary" in lower or "outlined" in lower):
                slots.append({"name": f"{name}-secondary", "role": "secondary action",
                              "contract": "button",
                              "copy": {"label": authored.get("secondaryCta") or sp["cta"]}})
            continue
        elif any(k in lower for k in ("quote", "testimonial")):
            entry["contract"] = "testimonial"
            entry["copy"] = {"quote": authored.get("quote")
                             or _demo_text(role, "body", sp, use, authored),
                             "name": authored.get("caption") or sp["name"],
                             "role": "" if authored.get("caption") else f"{use} specimen"}
        elif any(k in lower for k in ("list", "accordion", "faq", "rows", "items")):
            # ruled-row / accordion runs read label(+text) module lists — authored
            # per-module items win over synthesized placeholders.
            if authored_items:
                entry["contract"] = "list"
                entry["copy"] = [{"label": it.get("heading") or it.get("label") or "",
                                  "title": it.get("heading") or it.get("label") or "",
                                  "text": it.get("body") or it.get("text") or ""}
                                 for it in authored_items]
            else:
                entry["contract"] = "list"
                entry["copy"] = [{"label": f"{use} item {i + 1}",
                                  "title": f"{use} item {i + 1}",
                                  "text": _demo_text(role, "body", sp, use, authored)}
                                 for i in range(3)]
        else:
            body_text = _demo_text(role, "body", sp, use, authored)
            entry["contract"] = "paragraph"
            entry["copy"] = {"text": body_text, "body": body_text}
        slots.append(entry)

    # contentShape-only slots the brand layout doesn't list (e.g. a z:back panel
    # background) still shape the section — the art-panel/layer classifiers read them.
    for name, shape in shape_slots.items():
        if name in seen:
            continue
        entry = {"name": name, "role": str(shape.get("role") or name)}
        for k in ("textLen", "sizeClass", "width", "z", "mediaAspect"):
            if shape.get(k):
                entry[k] = shape[k]
        if shape.get("mediaAspect") or shape.get("z") == "back":
            entry["contract"] = "image"
        else:
            entry["contract"] = "paragraph"
            entry["copy"] = {"text": _demo_text(str(shape.get("role") or ""), "body", sp,
                                                use, authored)}
        slots.append(entry)

    # pattern treatments pass through where they use the composition vocabulary
    # (extraction-side kinds outside it, e.g. `marquee`, are dropped; the adapter
    # only maps known kinds — composition.v1 treatment enum).
    known_kinds = {
        "ghost-word", "overlap", "stagger", "bleed", "marginal-caption", "text-on-media",
        "counter-rotate", "float-wrap", "inset", "straddle", "panel-on-media",
        "scrim-band", "framed", "type-behind-media", "mixed-face", "stepped-lines",
        "break-frame"}
    treatments = [dict(t) for t in (pat.get("specialTreatments") or [])
                  if isinstance(t, dict) and str(t.get("kind")) in known_kinds]

    return {
        "id": layout.get("id") or pid,
        "useCase": use,
        # the LAYOUT's archetype is renderer vocabulary (build_document dispatches on
        # it); the pattern's archetypeRef is extraction vocabulary (e.g. `grid`) and
        # only backstops layouts that don't declare one.
        "archetype": str(layout.get("archetype") or pat.get("archetypeRef") or "stack"),
        "surfaceIntent": str(pat.get("surfaceIntent") or "any"),
        "novelty": "reuse",
        "seededFrom": {"lib": "project", "id": pid},
        "slots": slots,
        "treatments": treatments,
    }


def compose_pattern_docs(doc, patterns, brand_yaml: Path, out_dir: Path) -> dict:
    """Compose every pattern that has a referencing layout into
    <out_dir>/layouts/<pattern-id>.html via the real archetype composers. Returns
    {pattern_id: {"href": relative-url} | {"error": str}}. Defensive per pattern:
    a composer failing (e.g. mid-edit by another process) degrades that ONE row.

    When the brand lacks authored section copy (no section-copy.yaml), each pattern
    demo is hydrated through the composition adapter with brand-derived specimen
    content (_demo_section_for_pattern) so the tier shows the pattern's REAL
    structure instead of the empty-copy wordmark degenerate. cs.LAYOUT_COPY is
    snapshot/patched/restored exactly like compose_from_composition.render_composition."""
    import copy as _copy
    layouts_dir = out_dir / "layouts"
    layouts_dir.mkdir(parents=True, exist_ok=True)
    style_ctx = cs.inactive_context()
    # One shared assets/ dir beside the per-pattern documents (they reference
    # 'assets/<file>' relatively, same convention as compose_section main()).
    cdoc = _copy.deepcopy(doc)
    cs.prepare_nav_logo(cdoc, brand_yaml.parent, layouts_dir / "assets")
    cs.copy_assets(brand_yaml.parent, layouts_dir / "assets")
    cs.copy_fonts(brand_yaml.parent, layouts_dir / "assets", cdoc)

    hydrate = _demo_hydration_active(cdoc)
    saved_layout_copy = cs.LAYOUT_COPY
    results = {}
    try:
        for pat in patterns:
            pid = pat.get("id", "")
            layout = layout_for_pattern(cdoc, pid)
            if layout is None:
                results[pid] = {"error": "no brand.yaml layout references this pattern "
                                         "(listed without a composed render)"}
                continue
            use_layout, demo = layout, False
            # Adapter-composed demo when (a) the brand has no authored copy at all
            # (full specimen hydration), or (b) this layout binds slot assets or
            # authored copy that only the adapter realizes (logo strips / card
            # runs / placed media / mapped copy) — authored layers ride the same
            # structure.
            if hydrate or _layout_needs_asset_hydration(cdoc, layout):
                try:
                    sec = _demo_section_for_pattern(cdoc, pat, layout)
                    comp = cfc._sanitize_assets({"sections": [sec]}, brand_yaml.parent)
                    adapted = cfc.composition_to_layout(comp["sections"][0])
                    composer_copy = adapted.pop("_composerCopy", {}) or {}
                    sect_copy = adapted.pop("_sectionCopy", None) or {}
                    authored = dict(cs.brand_layout_copy(cdoc).get(layout.get("id")) or {})
                    merged = {**sect_copy, **composer_copy, **authored}
                    if merged:
                        cs.LAYOUT_COPY = {**cs.LAYOUT_COPY, adapted["id"]: merged}
                    use_layout, demo = adapted, True
                except Exception:
                    use_layout, demo = layout, False  # demo synth never takes the tier down
            try:
                html_doc = cs.build_document(cdoc, use_layout, brand_yaml, style_ctx)
                (layouts_dir / f"{pid}.html").write_text(html_doc)
                results[pid] = {"href": f"layouts/{pid}.html", "layout": layout.get("id"),
                                **({"demo": True} if demo else {})}
            except Exception as exc:  # composer mid-edit / moving state: degrade this row only
                results[pid] = {"error": f"composer failed: {type(exc).__name__}: {exc}"}
    finally:
        cs.LAYOUT_COPY = saved_layout_copy
    return results


def _pattern_badge(pat):
    origin = (pat or {}).get("origin", "designed")
    if origin == "extracted":
        return '<span class="badge badge-extracted">extracted</span>'
    return '<span class="badge badge-designed">designed</span>'


def _pattern_note(pat):
    origin = (pat or {}).get("origin", "designed")
    prov = ", ".join(str(p) for p in (pat.get("provenance") or []))
    if origin == "extracted":
        body = f"Observed on the live page. Provenance: {esc(prov)}." if prov \
            else "Observed on the live page."
        return f'<div class="cmp-note"><strong>Extracted.</strong> {body}</div>'
    note = ((pat.get("designedFrom") or {}).get("note") or "").strip()
    lead = "<strong>Designed / synthesized.</strong>"
    if pat.get("source") == "field":
        lead = "<strong>Designed — ratified from a field proposal.</strong>"
    return f'<div class="cmp-note">{lead} {esc(note)}</div>' if note \
        else f'<div class="cmp-note">{lead}</div>'


def build_layout_card(pat, composed):
    pid = pat.get("id", "")
    origin = pat.get("origin", "designed")
    tags = []
    if pat.get("useCase"):
        tags.append(f'<span class="tag">use-case: {esc(pat["useCase"])}</span>')
    if pat.get("archetypeRef"):
        tags.append(f'<span class="tag">archetype: {esc(pat["archetypeRef"])}</span>')
    if pat.get("confidence"):
        tags.append(f'<span class="tag">confidence: {esc(pat["confidence"])}</span>')

    info = composed.get(pid) or {}
    if info.get("href"):
        stage = (f'<iframe class="layout-frame" src="{esc(info["href"])}" loading="lazy" '
                 f'title="{esc(pid)} — composed section"></iframe>'
                 f'<div class="ex-caption">Composed through the real archetype composer '
                 f'(brand layout: {esc(info.get("layout", ""))})</div>')
    else:
        stage = (f'<div class="cmp-note"><strong>Not composed.</strong> '
                 f'{esc(info.get("error", "unavailable"))}</div>')

    return f"""    <article class="cmp cmp--layout" data-origin="{esc(origin)}">
      <div class="cmp-meta">
        <div class="cmp-head">
          <span class="cmp-name">{esc(pid)}</span>
          {_pattern_badge(pat)}
          {"".join(tags)}
        </div>
        <div class="cmp-intent">{esc(pat.get("intent", ""))}</div>
        {_pattern_note(pat)}
      </div>
      <div class="cmp-example">
        <div class="cmp-stage">{stage}</div>
      </div>
    </article>"""


def load_standard_patterns() -> list[dict]:
    """Standard-tier (brand-agnostic) patterns from brand_pipeline/contracts/
    layout-patterns/*.yaml — listed as a collapsed secondary group, not composed."""
    lp_dir = Path(__file__).resolve().parent / "contracts" / "layout-patterns"
    if not lp_dir.is_dir():
        return []
    out = []
    for f in sorted(lp_dir.glob("*.yaml")):
        if f.name == "index.yaml":
            continue
        try:
            data = yaml.safe_load(f.read_text()) or {}
        except Exception:
            continue
        out.extend(data.get("patterns") or [])
    return out


def build_layouts_section(patterns, composed, standard):
    n_extracted = sum(1 for p in patterns if p.get("origin") == "extracted")
    n_designed = len(patterns) - n_extracted
    cards = "\n".join(build_layout_card(p, composed) for p in patterns)

    std_html = ""
    if standard:
        rows = "".join(
            f'<div class="std-row"><span class="std-id">{esc(p.get("id", ""))}</span>'
            f'<span class="std-meta">{esc(p.get("useCase", ""))} &middot; '
            f'{esc(p.get("archetypeRef", ""))} &mdash; {esc(p.get("intent", ""))}</span></div>'
            for p in standard)
        std_html = f"""
  <details class="std">
    <summary>Standard-tier library &mdash; {len(standard)} brand-agnostic patterns (contracts/layout-patterns/, listed only)</summary>
    {rows}
  </details>"""

    return f"""  <section class="tier" id="tier-layouts">
    <div class="tier-num">Tier 3</div>
    <div class="tier-name">Extracted Layouts</div>
    <div class="tier-sub">{len(patterns)} project-tier layout patterns &mdash; {n_extracted} extracted, {n_designed} designed &mdash; each composed through the real archetype composers</div>
    <div class="tier-rule"></div>
  </section>
  <div class="list">
{cards}
  </div>{std_html}"""


# ── card + page assembly ────────────────────────────────────────────────────────

def _origin_badge(item):
    origin = (item or {}).get("origin", "designed")
    if origin == "extracted":
        return '<span class="badge badge-extracted">extracted</span>'
    return '<span class="badge badge-designed">synthesized</span>'


def _designed_note(item):
    df = (item or {}).get("designedFrom") or {}
    note = df.get("note")
    if note:
        return f'<div class="cmp-note"><strong>Designed / not used on page.</strong> {esc(note)}</div>'
    return '<div class="cmp-note"><strong>Designed / not used on page.</strong></div>'


def _rules_note(item):
    rules = (item or {}).get("rules") or []
    if rules:
        return '<div class="cmp-note">' + " ".join(f"&bull; {esc(r)}" for r in rules) + '</div>'
    val = (item or {}).get("value")
    if val:
        return f'<div class="cmp-note">{esc(val)}</div>'
    return ""


def build_card(doc, key, item, contract, renderers):
    origin = (item or {}).get("origin", "designed")
    use = (item or {}).get("use")
    intent = (contract or {}).get("intent", "")

    renderer = renderers.get(key)
    stage = renderer(doc, key, item) if renderer else render_generic(doc, key, item, contract)

    tags = []
    if use:
        cls = "tag tag-never" if use == "never" else "tag"
        tags.append(f'<span class="{cls}">use: {esc(use)}</span>')
    if (item or {}).get("conflictsWith"):
        tags.append(f'<span class="tag tag-never">conflict</span>')
    if key in ACTION_KINDS:
        tags.append('<span class="tag">stateful</span>')
    tags_html = "".join(tags)

    note = _designed_note(item) if origin == "designed" else _rules_note(item)

    return f"""    <article class="cmp" data-origin="{esc(origin)}">
      <div class="cmp-meta">
        <div class="cmp-head">
          <span class="cmp-name">{esc(key)}</span>
          {_origin_badge(item)}
          {tags_html}
        </div>
        <div class="cmp-intent">{esc(intent)}</div>
        {note}
      </div>
      <div class="cmp-example">
        <div class="cmp-stage">{stage}</div>
      </div>
    </article>"""


def build_section(doc, num, name, sub, items, contracts, renderers, anchor=""):
    cards = "\n".join(
        build_card(doc, key, item, contracts.get(key, {}), renderers)
        for key, item in items.items()
    )
    id_attr = f' id="{esc(anchor)}"' if anchor else ""
    return f"""  <section class="tier"{id_attr}>
    <div class="tier-num">{esc(num)}</div>
    <div class="tier-name">{esc(name)}</div>
    <div class="tier-sub">{esc(sub)}</div>
    <div class="tier-rule"></div>
  </section>
  <div class="list">
{cards}
  </div>"""


def build_surfaces_section(doc) -> str:
    """Surface-roles specimen tier (SPEC §C.4 / AS-20): one frame PER surface role,
    each scoped to its own generated per-surface alias block (`[data-surface-frame]`),
    so accent legality + link-hover re-scoping are visually reviewable on every
    surface the brand declares — not just a single hardcoded light canvas."""
    surfaces = (doc.get("tokens", {}) or {}).get("surfaces", {}) or {}
    if not surfaces:
        return ""
    frames = []
    for role, surf in surfaces.items():
        ctx = cr.make_context(doc, role, surf)
        specimen = (
            cr.render_eyebrow(doc, ctx, {"text": "Specimen eyebrow"})
            + cr.render_heading(doc, ctx, {"text": role.split("/")[-1].replace("-", " ").title(),
                                           "level": "h3"})
            + cr.render_arrow_link(doc, ctx, {"label": "Hover interaction",
                                              "accent": ctx.is_dark}))
        frames.append(
            f'<div class="sw-frame" data-surface-frame="{esc(role)}">'
            f'<div class="sw-role">{esc(role)}{" · dark" if ctx.is_dark else ""}</div>'
            f'{specimen}</div>')
    return f"""
<section id="tier-surfaces">
  <div class="tier">
    <div class="tier-num">3</div>
    <div class="tier-name">Surface roles</div>
    <div class="tier-sub">per-surface alias scopes &mdash; accent + hover re-scoping (AS-20), live :hover inside each frame</div>
    <div class="tier-rule"></div>
  </div>
  <div class="sw-grid">{''.join(frames)}</div>
</section>"""


def build_page(doc, prim_items, prim_contracts, block_items, block_contracts, brand_dir=None,
               layout_patterns=None, composed=None, standard_patterns=None, tokens_html=""):
    root, proxies = root_css(doc)
    gf = google_fonts_link(proxies)
    face_css = cs.font_face_css(brand_dir, doc) if brand_dir else ""
    name = (doc.get("brand") or {}).get("name", "Brand")
    snapshot = (((doc.get("brand") or {}).get("snapshot") or {}).get("value") or "").strip()
    # rule chips are BRAND-DRIVEN (the first few neverDo ids, humanized) — these were
    # hardcoded WoodWave literals ("radius 0 · no shadows …") shown verbatim on EVERY
    # brand's gallery, directly contradicting e.g. HubSpot's rounded/filled system.
    _nd = [str(r.get("id", "")).replace("no-", "no ").replace("never-", "never ").replace("-", " ")
           for r in (doc.get("neverDo") or []) if isinstance(r, dict)]
    rule_chips = " · ".join(_nd[:4]) if _nd else "brand rules: see brand.yaml neverDo"

    n_actions = sum(1 for k in prim_items if k in ACTION_KINDS)

    prim_section = build_section(
        doc, "Tier 1", "Primitives",
        f"{len(prim_items)} atomic primitives &mdash; {n_actions} action elements carry an interactive state matrix",
        prim_items, prim_contracts, PRIMITIVE_RENDERERS, anchor="tier-primitives")
    block_section = build_section(
        doc, "Tier 2", "Blocks",
        f"{len(block_items)} composed clusters &mdash; faithful mini-renders honoring the brand's slot grammar",
        block_items, block_contracts, BLOCK_RENDERERS, anchor="tier-blocks")

    surfaces_section = build_surfaces_section(doc)

    layouts_section = ""
    toc_layouts = ""
    if layout_patterns:
        layouts_section = "\n" + build_layouts_section(
            layout_patterns, composed or {}, standard_patterns or [])
        toc_layouts = '<a href="#tier-layouts">Extracted layouts</a>'
    toc = (f'<nav class="toc"><a href="#tier-primitives">Primitives</a>'
           f'<a href="#tier-blocks">Blocks</a><a href="#tier-surfaces">Surfaces</a>'
           f'{toc_layouts}</nav>')

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(name)} — Component Preview Gallery</title>
{gf}
{tokens_html}
<style>
{face_css}
{root}
{component_alias_css(doc)}
{button_family_css(doc)}
{BASE_CSS}
{cr.COMPONENT_CSS}
{cr.structural_variant_css(doc, include_all=True)}
{cr.motion_vars_css(doc)}
{cr.link_hover_css(doc)}
</style>
</head>
<body>
<div class="page">
  <header class="masthead">
    <div class="eyebrow ex-eyebrow">{esc(cr.eyebrow_prefix(doc))}Component Preview Gallery</div>
    <h1>{esc(name)}</h1>
    <p>{esc(snapshot)}</p>
    <div class="legend">
      <span><span class="badge badge-extracted">extracted</span> observed on the live page</span>
      <span><span class="badge badge-designed">synthesized</span> designed, not used on page</span>
      <span>{esc(rule_chips)}</span>
    </div>
    {toc}
  </header>
{prim_section}
{block_section}
{surfaces_section}{layouts_section}
</div>
</body>
</html>
"""


def load_contract(brand_yaml: Path, doc, kind: str) -> dict:
    """Resolve and load a universal contract referenced by brand.yaml.contracts."""
    ref = ((doc.get("contracts") or {}).get(kind))
    if not ref:
        # convention fallback: brand_pipeline/contracts/<kind>.yaml
        ref = f"../../../brand_pipeline/contracts/{kind}.yaml"
    path = (brand_yaml.parent / ref).resolve()
    data = yaml.safe_load(path.read_text()) or {}
    return data.get(kind, {}) or {}


_SPEC_NAME = "Brand"
_SPEC_CTA = "Learn more"
_SPEC_LINKS = ["About", "Products", "Pricing", "Contact"]


def _specimen(doc):
    """Brand-driven specimen strings for the gallery (anti-ai-slop AS-06/AS-01 shape:
    these were hardcoded WoodWave literals — _SPEC_CTA, 'WoodWave' — rendered
    verbatim into EVERY brand's gallery, so HubSpot's preview read as WoodWave).

    remote-fix 2026-07 (blocker 7): also derives a display HEADLINE from the brand's
    own measured layout copy (`layouts[].blockMapping[].props.Text` on a heading
    slot) so specimen headings/quotes are the ACTIVE brand's captured copy, never
    another brand's gallery prose; brands without measured copy fall back to the
    brand name (a type specimen set in the brand's own wordmark string)."""
    name = (doc.get("brand") or {}).get("name") or "Brand"
    nav = doc.get("navbar") or {}
    primary = [p.get("label") for p in (nav.get("primary") or []) if isinstance(p, dict) and p.get("label")]
    # the action label comes from the SAME evidence ladder the composed nav uses
    # (navbar.ctas[] / links[].style filled marker / measured.cta — never keyword
    # guesses over another brand's commerce vocabulary), then sectionCopy.
    cta = cs._navbar_props(doc).get("cta")
    headline = None
    for lay in (doc.get("layouts") or []):
        for bm in (lay.get("blockMapping") or []) if isinstance(lay, dict) else []:
            if not isinstance(bm, dict):
                continue
            txt = str(((bm.get("props") or {}).get("Text")) or "").strip()
            if not txt:
                continue
            slot = str(bm.get("slot") or "").lower()
            comp = str(bm.get("component") or "").lower()
            if comp == "heading" or "heading" in slot or slot == "main":
                headline = txt
                break
        if headline:
            break
    # labels pass through AS AUTHORED (AS-39): casing is presentation and belongs to
    # the brand's case tokens in CSS, never a Python .title()/.upper() restyle.
    return {"name": name, "cta": cta or "Learn more",
            "links": [str(x) for x in (primary[:4] or ["About", "Products", "Pricing", "Contact"])],
            "headline": headline or name}


def _brand_law(doc):
    """Brand-derived caption FACTS for the gallery (blocker 7, remote-fix 2026-07):
    captions must describe the ACTIVE brand's law, so the prose is computed from the
    brand's own tokens (families, radius scale, cta/input shape) instead of shipping
    one brand's design-law sentences into every brand's preview."""
    disp = (type_role(doc, "display-hero") or {}).get("family") \
        or (type_role(doc, "h1") or {}).get("family") or "the display face"
    body = (type_role(doc, "body") or {}).get("family") or "the body face"
    radii = set()
    for k, s in ((doc.get("tokens", {}) or {}).get("spacing", {}) or {}).items():
        if "radius" in k and isinstance(s, dict):
            radii.add(str(s.get("value", "")).strip())
    for s in ((doc.get("tokens", {}) or {}).get("radius", {}) or {}).values():
        if isinstance(s, dict) and s.get("value"):
            radii.add(str(s.get("value")).strip())
    square = radii <= {"0", "0px", "0rem", ""}
    return {
        "display": disp, "body": body, "square": square,
        "radius_word": "hard-edged (radius 0)" if square else "at the brand radius",
        "cta": cr.cta_shape(doc),
    }


def main():
    ap = argparse.ArgumentParser(description="Render a brand-styled component preview gallery.")
    ap.add_argument("brand_yaml", type=Path, help="path to a brand.yaml")
    ap.add_argument("-o", "--out", type=Path, required=True,
                    help="output dir (writes <out>/index.html)")
    args = ap.parse_args()

    doc = yaml.safe_load(args.brand_yaml.read_text())
    # AS-34 (remote-fix blocker 7): attach the ACTIVE brand's on-disk image inventory so
    # every pattern/default art resolves from the brand's own files — without this the
    # preview tier fell back to another brand's legacy default art names.
    cs.attach_brand_copy(doc, args.brand_yaml.parent)
    cs.attach_asset_inventory(doc, args.brand_yaml.parent)
    _bind_gallery_ctx(doc)  # RP-1: gallery canvas = the BRAND's primary surface
    global _SPEC_NAME, _SPEC_CTA, _SPEC_LINKS
    _sp = _specimen(doc)
    _SPEC_NAME, _SPEC_CTA, _SPEC_LINKS = _sp["name"], _sp["cta"], _sp["links"]
    prim_contracts = load_contract(args.brand_yaml, doc, "primitives")
    block_contracts = load_contract(args.brand_yaml, doc, "blocks")

    prim_items = doc.get("primitives") or {}
    block_items = doc.get("blocks") or {}

    args.out.mkdir(parents=True, exist_ok=True)

    # layer-1 generated tokens block: the specimens' alias layer resolves against it
    # (same generator + fail-loud semantics as the composed pages).
    bundle = tokens_css.build_page_tokens(doc, None, brand_yaml_path=args.brand_yaml)
    tokens_css.write_manifest(args.out, bundle)

    # Tier 3: compose each project-tier layout pattern through the real archetype
    # composers into <out>/layouts/<pattern-id>.html (embedded as iframe rows).
    layout_patterns = load_layout_library(args.brand_yaml)
    composed = compose_pattern_docs(doc, layout_patterns, args.brand_yaml, args.out) \
        if layout_patterns else {}
    standard_patterns = load_standard_patterns() if layout_patterns else []

    page = build_page(doc, prim_items, prim_contracts, block_items, block_contracts,
                      brand_dir=args.brand_yaml.parent,
                      layout_patterns=layout_patterns, composed=composed,
                      standard_patterns=standard_patterns,
                      tokens_html=tokens_css.style_tag(bundle))

    out_file = args.out / "index.html"
    out_file.write_text(page)
    cs.copy_fonts(args.brand_yaml.parent, args.out / "assets", doc)

    n_actions = sum(1 for k in prim_items if k in ACTION_KINDS)
    print(f"Wrote {out_file}")
    print(f"  primitives: {len(prim_items)} (rendered)")
    print(f"  blocks:     {len(block_items)} (rendered)")
    print(f"  action elements with state matrices: {n_actions} "
          f"({', '.join(k for k in prim_items if k in ACTION_KINDS)})")
    if layout_patterns:
        ok = sum(1 for v in composed.values() if v.get("href"))
        print(f"  layout patterns: {len(layout_patterns)} listed, {ok} composed "
              f"through ARCHETYPE_COMPOSERS; {len(standard_patterns)} standard-tier listed")
        for pid, v in composed.items():
            if not v.get("href"):
                print(f"    ! {pid}: {v.get('error')}")


if __name__ == "__main__":
    main()
