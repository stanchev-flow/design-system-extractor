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

Token resolution reuses the faithful helpers in render_section.py (imported, never
modified) so every value is the brand's real token.

Usage:
  python3 render_components_preview.py <brand.yaml> -o <outdir>
  # writes <outdir>/index.html
"""
from __future__ import annotations

import argparse
import html
import sys
from pathlib import Path

import yaml

# Reuse the canonical, faithful token resolvers from render_section.py (same
# package dir). We import — never modify — that module. When run as
# `python brand_pipeline/render_components_preview.py ...` the script's own dir is
# on sys.path[0]; we also insert it explicitly to be robust to other launch dirs.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_section import (  # noqa: E402
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

# Gallery render context: the gallery canvas is the light cream surface, so accent is
# pinned to ink in the alias block below (no accent on light — neverDo). is_dark=False.
_GALLERY_CTX = cr.ComponentContext(surface_role="surface/primary", is_dark=False)

# Map the shared `--c-*` component vars onto the gallery's own brand vars (defined in
# root_css), so the imported `c-*` classes read on-brand on the cream canvas.
COMPONENT_ALIAS_CSS = """:root {
  --c-paper: var(--surface-primary);
  --c-ink: var(--ink);
  --c-ink-muted: var(--ink-muted);
  --c-accent: var(--ink);            /* light canvas: action/heading ink, never accent */
  --c-font-heading: var(--font-heading);
  --c-font-body: var(--font-body);
  --c-display-size: var(--h2-size);  /* show the display sample at h2 scale to fit a card */
  --c-display-lh: 1.2em;
  --c-display-ls: 0;
  --c-display-weight: 400;
  --c-h2-size: var(--h2-size);
  --c-h3-size: var(--h3-size);
  --c-eyebrow-size: var(--eyebrow-size);
  --c-eyebrow-ls: var(--eyebrow-ls);
  --c-control-size: var(--control-size);
  --c-control-ls: var(--control-ls);
  --c-eyebrow-gap: var(--eyebrow-gap);
  --c-body-size: var(--body-size);
  --c-hairline: var(--hairline);
}"""


def esc(value) -> str:
    return html.escape(str(value if value is not None else ""))


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

    css = f""":root {{
  --surface-primary: {c('surface/primary', '#FAF0E8')};
  --surface-panel: {c('surface/panel', '#F7EFE6')};
  --surface-inverse: {c('surface/inverse', '#3A2F23')};
  --surface-inverse-strong: {c('surface/inverse-strong', '#1B150F')};
  --accent: {c('accent/highlight', '#edd580')};
  --ink: {c('text/on-primary', '#1F1A14')};
  --ink-muted: {c('text/on-primary-muted', '#4A4239')};
  --ink-inverse: {c('text/on-inverse', '#F5EDE2')};
  --ink-inverse-muted: {c('text/on-inverse-muted', '#C9BFB2')};
  --ghost: {c('text/ghost-on-primary', 'rgba(31,26,20,0.06)')};
  --hairline: {c('border/hairline-on-primary', 'rgba(31,26,20,0.30)')};

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
  --eyebrow-ls: {eyb.get('letterSpacing', '0.08em')};
  --control-ls: {ctrl.get('letterSpacing', '0.08em')};

  --radius: {radius};
  --panel-pad: {panel_pad};
  --eyebrow-gap: {eyebrow_gap};
  --module-gap: {module_gap};
  --ease: {ease_ms};
}}"""
    return css, proxies


# ── static (non-token) page + card + state CSS ──────────────────────────────────
# Brand neverDo is baked in: radius 0, no shadows/borders (separation is fill
# contrast + 1px ruled bars only), accent confined to .surface-dark contexts.
BASE_CSS = """
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
  text-transform: uppercase;
  font-size: var(--h1-size);
  line-height: 1.1em;
  color: var(--accent);
  margin: var(--eyebrow-gap) 0 1rem;
}
.masthead p { color: var(--ink-inverse-muted); max-width: 52rem; font-size: var(--body-size); }
.legend { display: flex; flex-wrap: wrap; gap: 1.5rem; margin-top: 2rem; }
.legend span { display: inline-flex; align-items: center; gap: 0.5rem;
  font-size: var(--eyebrow-size); letter-spacing: var(--eyebrow-ls);
  text-transform: uppercase; color: var(--ink-inverse-muted); }

/* Tier headers. */
.tier { margin: 6cqh 0 2.5cqh; }
.tier-num { font-family: var(--font-heading); font-size: var(--counter-size);
  color: var(--ink); line-height: 1; }
.tier-name { font-family: var(--font-heading); text-transform: uppercase;
  font-size: var(--h2-size); line-height: 1.2em; color: var(--ink); margin-top: 0.25rem; }
.tier-sub { font-size: var(--eyebrow-size); letter-spacing: var(--eyebrow-ls);
  text-transform: uppercase; color: var(--ink-muted); margin-top: 0.75rem; }
.tier-rule { height: 1px; background: var(--hairline); margin-top: 1.25rem; }

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
.cmp-name { font-family: var(--font-heading); text-transform: uppercase;
  font-size: var(--h3-size); line-height: 1.2em; color: var(--ink); }
.cmp-intent { font-size: var(--body-size); color: var(--ink-muted); line-height: 1.5em; }
.cmp-example { display: flex; flex-direction: column; gap: 1.25rem; max-width: 52rem; }

/* Badges / tags — square, no radius. */
.badge { font-family: var(--font-body); font-size: 0.625rem; letter-spacing: 0.1em;
  text-transform: uppercase; padding: 0.2rem 0.5rem; border-radius: 0; line-height: 1.2; }
.badge-extracted { background: var(--ink); color: var(--surface-primary); }
.badge-designed { background: transparent; color: var(--ink-muted);
  border: 1px dashed var(--ink-muted); }
.tag { font-family: var(--font-body); font-size: 0.625rem; letter-spacing: 0.1em;
  text-transform: uppercase; color: var(--ink-muted);
  border: 1px solid var(--hairline); padding: 0.2rem 0.5rem; }
.tag-never { border-style: dashed; color: var(--ink-muted); }

/* Example stage — no box, no border: the example sits openly in the row flow. */
.cmp-stage { display: flex; flex-direction: column; gap: 1rem; }
.cmp-note { font-size: var(--eyebrow-size); letter-spacing: 0.04em; line-height: 1.45em;
  color: var(--ink-muted); }
.cmp-note strong { color: var(--ink); font-weight: 600; }

/* Dark sub-surface used inside examples that the brand confines to dark bands
   (logo, badge, banner, navbar, footer, tooltip, code). Accent allowed here. */
.surface-dark { background: var(--surface-inverse); color: var(--ink-inverse);
  padding: 1.25rem; }
.surface-darkest { background: var(--surface-inverse-strong); color: var(--ink-inverse);
  padding: 1.25rem; }
.surface-panel { background: var(--surface-panel); color: var(--ink);
  padding: var(--panel-pad); }
/* footer demo: rescope the shared --c-* vars to the inverse tokens so the imported
   render_footer c-* classes read on-brand (light ink on the near-black footer band),
   and give the centered cluster generous, scale-driven breathing room. */
.cmp-footer-demo { --c-paper: var(--surface-inverse-strong); --c-ink: var(--ink-inverse);
  --c-ink-muted: var(--ink-inverse-muted); --c-accent: var(--accent);
  --c-block-gap: 2.5rem; padding: 3rem 1.75rem; }

/* ── faithful example primitives ── */
.ex-display { font-family: var(--font-heading); font-weight: 400; text-transform: uppercase;
  font-size: var(--h2-size); line-height: 1.2em; color: var(--ink); }
.ex-h3 { font-family: var(--font-heading); font-weight: 400; text-transform: uppercase;
  font-size: var(--h3-size); line-height: 1.3em; color: var(--ink); }
.ex-sub { font-family: var(--font-heading); font-weight: 400; font-size: 1.125rem;
  line-height: 1.3em; color: var(--ink-muted); }
.ex-eyebrow { font-family: var(--font-body); font-size: var(--eyebrow-size);
  letter-spacing: var(--eyebrow-ls); text-transform: uppercase; color: var(--ink-muted); }
.ex-body { font-family: var(--font-body); font-size: var(--body-size); line-height: 1.55em;
  color: var(--ink-muted); max-width: 34ch; }
.ex-caption { font-family: var(--font-body); font-size: var(--eyebrow-size);
  letter-spacing: var(--eyebrow-ls); text-transform: uppercase; color: var(--ink-muted); }
.ex-label { font-family: var(--font-body); font-size: var(--control-size);
  letter-spacing: var(--control-ls); text-transform: uppercase; color: var(--ink); }

/* image / video / avatar / illustration: hard-edged rectangles, radius 0, no chrome. */
.ex-photo { background: var(--surface-inverse); color: var(--ink-inverse-muted);
  border-radius: 0; aspect-ratio: 4 / 3; width: 100%; display: flex; align-items: center;
  justify-content: center; font-family: var(--font-body); font-size: var(--eyebrow-size);
  letter-spacing: var(--eyebrow-ls); text-transform: uppercase; }
.ex-photo.is-portrait { aspect-ratio: 3 / 4; max-width: 9rem; }
.ex-photo.is-square { aspect-ratio: 1 / 1; max-width: 6rem; }
.ex-illus { background: var(--ghost); color: var(--ink-muted); aspect-ratio: 4/3;
  display: flex; align-items: center; justify-content: center; font-family: var(--font-heading);
  font-size: 2rem; text-transform: uppercase; }
.ex-play { width: 0; height: 0; border-style: solid; border-width: 0.55rem 0 0.55rem 0.9rem;
  border-color: transparent transparent transparent var(--ink-inverse); }

/* logo wordmark. */
.ex-logo { font-family: var(--font-heading); text-transform: uppercase; letter-spacing: 0.06em;
  font-size: 1.25rem; color: var(--accent); }

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
.ex-list .ex-li::after { content: "/"; position: absolute; left: 0; top: 0.6rem;
  color: var(--ink-muted); font-family: var(--font-heading); }

/* quote / stat / counter. */
.ex-quote { font-family: var(--font-heading); text-transform: uppercase; font-weight: 400;
  font-size: 1.5rem; line-height: 1.25em; color: var(--ink); }
.ex-counter { font-family: var(--font-heading); font-size: var(--counter-size); line-height: 1;
  color: var(--ink); }

/* code. */
.ex-code { font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace; font-size: 0.8125rem;
  color: var(--ink-inverse); white-space: pre; line-height: 1.5; }

/* badge marker (gold, flat square, dark only). */
.ex-marker { display: inline-block; background: var(--accent); color: var(--surface-inverse-strong);
  font-family: var(--font-body); font-size: 0.625rem; letter-spacing: 0.1em; text-transform: uppercase;
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
  letter-spacing: var(--control-ls); text-transform: uppercase; color: var(--ink); }
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
  letter-spacing: var(--eyebrow-ls); text-transform: uppercase; color: var(--ink-muted); }

/* ── typographic action (link / cta / icon-button remap) ── */
.act { font-family: var(--font-body); font-size: var(--control-size); letter-spacing: var(--control-ls);
  text-transform: uppercase; color: var(--ink); text-decoration: none; background: none; border: 0;
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

/* avoid (synthesized) filled button / icon-button — what the brand does NOT use. */
.avoid-btn { font-family: var(--font-body); font-size: var(--control-size); letter-spacing: var(--control-ls);
  text-transform: uppercase; background: var(--surface-inverse); color: var(--ink-inverse); border: 0;
  border-radius: 0; padding: 0.7rem 1.2rem; cursor: pointer; opacity: 0.85; }
.avoid-iconbtn { width: 2.4rem; height: 2.4rem; display: inline-flex; align-items: center;
  justify-content: center; background: var(--surface-inverse); color: var(--ink-inverse); border: 0;
  border-radius: 0; cursor: pointer; }
.avoid-pill { display: inline-block; border: 1px solid var(--ink-muted); border-radius: 999px;
  padding: 0.25rem 0.8rem; font-family: var(--font-body); font-size: var(--eyebrow-size);
  letter-spacing: var(--eyebrow-ls); text-transform: uppercase; color: var(--ink-muted); }
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
  text-transform: uppercase; color: var(--ink-muted); }
.state-row { display: grid; grid-template-columns: repeat(5, 1fr); gap: 1px;
  background: var(--hairline); border: 1px solid var(--hairline); }
.state-col { background: var(--surface-primary); padding: 1rem 0.75rem; display: flex;
  flex-direction: column; align-items: flex-start; gap: 0.75rem; min-height: 5rem;
  justify-content: space-between; }
.state-col .stg { display: flex; align-items: center; min-height: 2rem; }
.state-name { font-family: var(--font-body); font-size: 0.5625rem; letter-spacing: 0.12em;
  text-transform: uppercase; color: var(--ink-muted); }
.state-live { display: flex; align-items: center; gap: 1.5rem; flex-wrap: wrap;
  padding-top: 0.25rem; }
.state-live .hint { font-family: var(--font-body); font-size: 0.5625rem; letter-spacing: 0.12em;
  text-transform: uppercase; color: var(--ink-muted); }

/* On narrower frames the example stacks directly beneath the meta line. */
@media (max-width: 60rem) {
  .cmp { grid-template-columns: 1fr; column-gap: 0; }
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
    h = cr.render_heading(doc, _GALLERY_CTX,
                          {"text": "Exhibitions On View", "level": "display", "tag": "div"})
    return (h + '<div class="ex-eyebrow">display / h1 / h2 / h3 &mdash; didone, uppercase</div>')


def render_subheading(doc, key, item):
    return ('<div class="ex-display" style="font-size:var(--h3-size)">A Living Archive</div>'
            '<div class="ex-sub">A smaller didone line, muted &mdash; never a generic sans sub-deck.</div>')


def render_eyebrow(doc, key, item):
    return cr.render_eyebrow(doc, _GALLERY_CTX, {"text": "/ 01 — On View"})


def render_paragraph(doc, key, item):
    # SSOT: rendered by the shared catalog renderer (also used by section composition).
    return cr.render_paragraph(doc, _GALLERY_CTX, {
        "text": ("Set narrow, roughly a third of the container and offset from its media. "
                 "Inter, sentence case, generous leading.")})


def render_label(doc, key, item):
    return '<span class="ex-label">Gallery Hours</span>'


def render_caption(doc, key, item):
    return ('<div class="ex-photo" style="aspect-ratio:16/9">PHOTO</div>'
            '<div class="ex-caption">Fig. 01 &mdash; Spiral staircase, 2026</div>')


def render_image(doc, key, item):
    img = cr.render_image(doc, _GALLERY_CTX, {"placeholder": "IMAGE — RADIUS 0"})
    return (img + '<div class="ex-caption">Hard-edged photography &mdash; no shadow, border or mat</div>')


def render_video(doc, key, item):
    return ('<div class="ex-photo"><span class="ex-play" aria-hidden="true"></span></div>'
            '<div class="ex-caption">Treated like image &mdash; hard-edged rectangle</div>')


def render_avatar(doc, key, item):
    return ('<div class="ex-photo is-square">PERSON</div>'
            '<div class="ex-caption">Hard rectangle crop &mdash; round default overridden by no-radius</div>')


def render_illustration(doc, key, item):
    return ('<div class="ex-illus">&#9697;</div>'
            '<div class="ex-caption">Flat ghost-tone graphic &mdash; no gradients</div>')


def render_logo(doc, key, item):
    return ('<div class="surface-dark"><span class="ex-logo">WoodWave</span></div>'
            '<div class="ex-caption">Wordmark &mdash; gold on dark, never on cream</div>')


def render_icon(doc, key, item):
    return ('<div style="display:flex;gap:1.25rem;font-family:var(--font-heading);'
            'font-size:1.5rem;color:var(--ink)"><span>&rarr;</span><span>&#8260;</span>'
            '<span>+</span><span>&#8599;</span></div>'
            '<div class="ex-caption">Thin monoline glyphs inheriting text color &mdash; no accent on light</div>')


def render_link(doc, key, item):
    # SSOT: the base arrow link comes from the shared catalog renderer (cta/link remap).
    base = cr.render_arrow_link(doc, _GALLERY_CTX, {"label": "Buy Tickets"})
    matrix = _state_matrix(
        lambda cls: _arrow("Buy Tickets", cls),
        '<a class="act live" href="#">Buy Tickets <span class="arrow">&rarr;</span></a>'
        '<button class="act live" disabled>Sold Out <span class="arrow">&rarr;</span></button>',
    )
    return f'{base}{matrix}'


def render_cta(doc, key, item):
    base = cr.render_arrow_link(doc, _GALLERY_CTX, {"label": "Subscribe"})
    matrix = _state_matrix(
        lambda cls: _arrow("Subscribe", cls),
        '<a class="act live" href="#">Subscribe <span class="arrow">&rarr;</span></a>'
        '<button class="act live" disabled>Subscribe <span class="arrow">&rarr;</span></button>',
    )
    return ('<div class="ex-caption">CTA role &mdash; realized by the arrow link primitive, never a button</div>'
            f'{base}{matrix}')


def render_button(doc, key, item):
    """Button is observed-as-prohibition: render the arrow link it remaps to (with
    states), and show the filled button as the synthesized / avoid variant."""
    matrix = _state_matrix(
        lambda cls: _arrow("Buy Tickets", cls),
        '<a class="act live" href="#">Buy Tickets <span class="arrow">&rarr;</span></a>'
        '<button class="act live" disabled>Buy Tickets <span class="arrow">&rarr;</span></button>',
    )
    return ('<div class="ex-caption">Brand realization &mdash; the arrow link the CTA remaps to:</div>'
            f'{matrix}'
            '<div class="ex-rule"></div>'
            '<div class="ex-caption">Synthesized / avoid &mdash; filled button, never used on page:</div>'
            '<div class="strike"><button class="avoid-btn" tabindex="-1">Buy Tickets</button></div>')


def render_icon_button(doc, key, item):
    matrix = _state_matrix(
        lambda cls: f'<a class="act {cls}" href="#" tabindex="-1" aria-label="Next"><span class="arrow">&rarr;</span></a>',
        '<a class="act live" href="#" aria-label="Next"><span class="arrow">&rarr;</span></a>'
        '<button class="act live" disabled aria-label="Next"><span class="arrow">&rarr;</span></button>',
    )
    return ('<div class="ex-caption">Brand realization &mdash; remaps to a typographic arrow/slash link:</div>'
            f'{matrix}'
            '<div class="ex-rule"></div>'
            '<div class="ex-caption">Synthesized / avoid &mdash; filled icon button, never used:</div>'
            '<div class="strike"><button class="avoid-iconbtn" tabindex="-1" aria-label="avoid">&rarr;</button></div>')


def render_pill(doc, key, item):
    return ('<div class="ex-caption">Brand realization &mdash; a tag remaps to an uppercase eyebrow label:</div>'
            '<span class="ex-eyebrow">Sculpture</span>'
            '<div class="ex-rule"></div>'
            '<div class="ex-caption">Synthesized / avoid &mdash; rounded chip, never used:</div>'
            '<div class="strike"><span class="avoid-pill">Sculpture</span></div>')


def render_badge(doc, key, item):
    return ('<div class="surface-dark"><span class="ex-marker">New</span></div>'
            '<div class="ex-caption">Flat square accent marker &mdash; gold on dark only, never rounded</div>')


def render_input(doc, key, item):
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
            '<span class="ex-input">Multi-line entry as a single underline rule&hellip;</span></div>'
            '<div class="ex-caption">No box/fill, matching the Lead-form input</div>')


def render_select(doc, key, item):
    return ('<span class="ex-select">Choose a tour <span aria-hidden="true">&#9662;</span></span>'
            '<div class="ex-caption">Underline trigger, uppercase control-text; flat square menu</div>')


def render_form_field(doc, key, item):
    return ('<span class="ex-eyebrow">Email address</span>'
            '<div class="ex-field"><span class="ex-input">you@email.com</span></div>'
            '<div class="ex-caption">Label as uppercase eyebrow; underline control; no boxed row</div>')


def render_checkbox(doc, key, item):
    def sw(cls):
        # default/hover/focus/disabled show the empty OFF box; pressed shows ON.
        on = "is-on" if cls == "is-active" else ""
        return f'<span class="ex-check {cls} {on}"><span class="box">&#10003;</span></span>'
    live = ('<label class="ex-check live"><input type="checkbox">'
            '<span class="box">&#10003;</span><span>Members (toggle me)</span></label>'
            '<label class="ex-check disabled"><input type="checkbox" disabled>'
            '<span class="box">&#10003;</span><span>Closed</span></label>')
    return ('<div class="ex-caption">Empty cream box + 1px hairline when off; flat dark fill + light check on select &mdash; radius 0</div>'
            f'{_state_matrix(sw, live)}')


def render_radio(doc, key, item):
    return ('<span class="ex-check radio is-on"><span class="box">&#9632;</span><span>Adult</span></span>'
            '<span class="ex-check radio"><span class="box"></span><span>Concession</span></span>'
            '<div class="ex-caption">Square selector (radius 0 overrides the round default)</div>')


def render_toggle(doc, key, item):
    def sw(cls):
        # default/hover/focus/disabled show the empty OFF switch (knob left);
        # pressed shows the flat dark ON switch (knob right).
        on = "is-on" if cls == "is-active" else ""
        return (f'<span class="ex-switch {cls} {on}">'
                '<span class="track"><span class="knob"></span></span></span>')
    live = ('<label class="ex-switch live"><input type="checkbox">'
            '<span class="track"><span class="knob"></span></span><span>Late hours (toggle me)</span></label>'
            '<label class="ex-switch disabled"><input type="checkbox" disabled>'
            '<span class="track"><span class="knob"></span></span><span>Locked</span></label>')
    return ('<div class="ex-caption">Square sliding switch &mdash; empty cream track when off (knob left); '
            'flat dark fill when on (knob right); no pill/rounding, radius 0</div>'
            f'{_state_matrix(sw, live)}')


def render_slider(doc, key, item):
    return ('<div class="ex-slider"><span class="fill"></span><span class="handle"></span></div>'
            '<div class="ex-caption">1px square track + square handle &mdash; no rounded thumb</div>')


def render_file_upload(doc, key, item):
    return ('<span class="ex-select">Attach a file <span aria-hidden="true">&rarr;</span></span>'
            '<div class="ex-caption">Underline-style trigger + uppercase control-text &mdash; no dropzone box</div>')


def render_divider(doc, key, item):
    return ('<div class="ex-rows"><div class="ex-row"><span class="ex-label">Adult</span>'
            '<span class="ex-counter" style="font-size:1.25rem">&pound;14</span></div>'
            '<div class="ex-row"><span class="ex-label">Concession</span>'
            '<span class="ex-counter" style="font-size:1.25rem">&pound;9</span></div></div>'
            '<div class="ex-caption">1px ruled action-row bar inside a panel &mdash; never a section seam</div>')


def render_quote(doc, key, item):
    return ('<blockquote class="ex-quote">A space that lets the work breathe.</blockquote>'
            '<div class="ex-eyebrow">&mdash; The Observer</div>'
            '<div class="ex-caption">Large didone, open on the canvas; attribution as margin eyebrow</div>')


def render_stat(doc, key, item):
    return ('<div class="ex-counter">1 / 6</div><div class="ex-eyebrow">Galleries open</div>'
            '<div class="ex-caption">Big didone numeral + uppercase eyebrow &mdash; open, never boxed</div>')


def render_rating(doc, key, item):
    return ('<div class="ex-counter" style="font-size:1.5rem">4.8 / 5</div>'
            '<div class="ex-caption">Fraction numeral &mdash; no colored stars on cream</div>')


def render_list(doc, key, item):
    items = ["Permanent collection", "Rotating exhibitions", "Members-only previews"]
    rows = "".join(f'<div class="ex-li">{esc(t)}</div>' for t in items)
    return (f'<div class="ex-list">{rows}</div>'
            '<div class="ex-caption">Rows separated by 1px ruled bars; slash marker, never decorative bullets</div>')


def render_code(doc, key, item):
    return ('<div class="surface-darkest"><pre class="ex-code">curl woodwave.io/api\n  &gt; { "open": true }</pre></div>'
            '<div class="ex-caption">Monospace on near-black, radius 0 &mdash; off-brand, used rarely</div>')


def render_progress(doc, key, item):
    return ('<div class="ex-progress"><span class="fill"></span></div>'
            '<div class="ex-caption">Thin square 1px bar, solid fill &mdash; no rounding/gradient</div>')


def render_tooltip(doc, key, item):
    return ('<span class="ex-tip">Opens at 10:00</span>'
            '<div class="ex-caption">Square dark panel, no shadow/radius, Inter micro-text</div>')


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
    # SSOT: the header block composes eyebrow + heading + arrow cta via the shared renderer.
    return cr.render_header(doc, _GALLERY_CTX, {
        "eyebrow": "/ Now Open", "heading": "Light & Timber", "level": "display",
        "cta": "Plan your visit"})


def render_b_navbar(doc, key, item):
    return ('<div class="surface-dark"><div style="display:flex;align-items:center;'
            'justify-content:space-between;gap:1.5rem">'
            '<span class="ex-logo" style="font-size:1rem">WoodWave</span>'
            '<span class="ex-label" style="color:var(--ink-inverse);font-size:var(--control-size)">'
            'About <span style="opacity:.5">/</span> Gallery <span style="opacity:.5">/</span> Visit</span>'
            '<a class="act" href="#" style="color:var(--accent)">Buy Tickets <span class="arrow">&rarr;</span></a>'
            '</div></div>'
            '<div class="ex-caption">Zero-chrome bar &mdash; no fill/border/button; slash typographic nav</div>')


def render_b_footer(doc, key, item):
    # SSOT: the footer block is rendered by the SHARED catalog renderer
    # (component_render.render_footer) — the SAME renderer the page composer uses — so
    # there is ONE footer renderer for both the gallery and the composed page. Rendered
    # on the brand's near-black strong surface (a footer/closing bookend is dark-only);
    # `.cmp-footer-demo` rescopes the shared --c-* vars to the inverse tokens so the
    # imported c-* classes read on-brand (light ink on dark), and the sitemap centers +
    # right-sizes itself via the contained clamp in component_render.COMPONENT_CSS.
    foot = cr.render_footer(doc, _GALLERY_CTX, {
        "sitemap": ["About", "Gallery", "Exhibition", "Visit", "Buy Tickets"],
        "social": ["Instagram", "Facebook", "Youtube", "Twitter"],
        "legal": "© 2026 WoodWave Gallery",
    })
    return (f'<div class="surface-darkest cmp-footer-demo">{foot}</div>'
            '<div class="ex-caption">Closing bookend &mdash; centered, right-sized oversized didone '
            'slash sitemap, text social row + muted legal; shared <code>render_footer</code>, no boxes</div>')


def render_b_media_text(doc, key, item):
    return ('<div style="display:grid;grid-template-columns:1fr 1fr;gap:0">'
            '<div class="ex-photo" style="aspect-ratio:auto">PHOTO</div>'
            '<div class="surface-panel"><div class="ex-h3">Ticket Prices</div>'
            '<div class="ex-rows" style="margin-top:0.75rem">'
            '<div class="ex-row"><span class="ex-label">Adult</span>'
            f'{_arrow("Buy")}</div>'
            '<div class="ex-row"><span class="ex-label">Concession</span>'
            f'{_arrow("Buy")}</div></div></div></div>'
            '<div class="ex-caption">Two flush halves, gap 0, hard cut; cream panel child of inverse</div>')


def render_b_content_block(doc, key, item):
    return ('<div class="ex-photo" style="aspect-ratio:16/9">PHOTO</div>'
            '<div class="ex-caption">Fig. 02 &mdash; Atrium</div>'
            '<div class="ex-h3" style="margin-top:0.5rem">A Living Archive</div>'
            '<p class="ex-body">Narrow offset body, ~1/3 container, set over the ghost watermark.</p>'
            f'{_arrow("Read more")}')


def render_b_cta_block(doc, key, item):
    return ('<div style="text-align:center;display:flex;flex-direction:column;align-items:center;gap:1rem">'
            '<div class="ex-eyebrow">/ Stay in touch</div>'
            '<div class="ex-display">Join the List</div>'
            f'{_arrow("Subscribe")}</div>'
            '<div class="ex-caption">Narrow centered stack; typographic arrow action, never a button</div>')


def render_b_form(doc, key, item):
    # SSOT: the form block composes the underline field + inline arrow submit via the
    # shared catalog renderer (the SAME render_form the section composer uses).
    form = cr.render_form(doc, _GALLERY_CTX, {
        "eyebrow": "/ Newsletter", "placeholder": "Enter your email", "submit": "Subscribe"})
    return (form + '<div class="ex-caption">Underline-only field + inline typographic submit; no boxed inputs</div>')


def render_b_card(doc, key, item):
    return ('<div class="ex-caption"><strong>No cards on cream.</strong> Light-canvas content is open '
            'editorial collage:</div>'
            '<div class="ex-photo" style="aspect-ratio:16/9">PHOTO</div>'
            '<div class="ex-caption">Fig. 03 &mdash; in the margin</div>'
            '<div class="ex-rule"></div>'
            '<div class="ex-caption">A bounded unit only ever appears as the cream panel inside a dark band.</div>')


def render_b_testimonial(doc, key, item):
    return ('<blockquote class="ex-quote">It rewired how I think about a gallery.</blockquote>'
            '<div style="display:flex;align-items:center;gap:0.75rem;margin-top:0.75rem">'
            '<div class="ex-photo is-square" style="max-width:3rem;margin:0">A</div>'
            '<span class="ex-eyebrow">Ada Mensah &mdash; Curator</span></div>'
            '<div class="ex-caption">Open didone quote; name/role as margin eyebrow; rectangle avatar</div>')


def render_b_stat_block(doc, key, item):
    return ('<div style="display:flex;gap:2.5rem">'
            '<div><div class="ex-counter">12</div><div class="ex-eyebrow">Galleries</div></div>'
            '<div><div class="ex-counter">40k</div><div class="ex-eyebrow">Visitors</div></div>'
            '<div><div class="ex-counter">6</div><div class="ex-eyebrow">Exhibitions</div></div></div>'
            '<div class="ex-caption">Row of big didone numerals + eyebrow labels; open, no boxes</div>')


def render_b_accordion(doc, key, item):
    return ('<div class="ex-rows">'
            '<div class="ex-row"><span class="ex-h3" style="font-size:1.125rem">Opening hours</span>'
            '<span style="font-family:var(--font-heading)">&#8260;</span></div>'
            '<div class="ex-row"><span class="ex-h3" style="font-size:1.125rem">Accessibility</span>'
            '<span style="font-family:var(--font-heading)">&#8260;</span></div></div>'
            '<div class="ex-caption">Didone triggers separated by 1px ruled bars; slash indicator</div>')


def render_b_accordion_item(doc, key, item):
    return ('<div class="ex-row" style="padding-top:0"><span class="ex-h3" style="font-size:1.125rem">'
            'Opening hours</span><span style="font-family:var(--font-heading)">&#8260;</span></div>'
            '<p class="ex-body">Tue&ndash;Sun, 10:00&ndash;18:00. Late opening Thursdays.</p>'
            '<div class="ex-caption">Didone trigger + Inter body; slash/arrow, never a chevron chip</div>')


def render_b_tabs(doc, key, item):
    return ('<div style="display:flex;gap:1.5rem">'
            '<span class="ex-label" style="border-bottom:2px solid var(--ink);padding-bottom:0.3rem">Overview</span>'
            '<span class="ex-label" style="color:var(--ink-muted)">Access</span>'
            '<span class="ex-label" style="color:var(--ink-muted)">Map</span></div>'
            '<div class="ex-caption">Uppercase typographic triggers, underline active state; never pill/boxed</div>')


def render_b_logo_bar(doc, key, item):
    return ('<div class="ex-eyebrow">In partnership with</div>'
            '<div style="display:flex;gap:1.75rem;margin-top:0.6rem;font-family:var(--font-heading);'
            'text-transform:uppercase;color:var(--ink)"><span>ARTC</span><span>FOLIO</span><span>KILN</span></div>'
            '<div class="ex-caption">Monochrome wordmarks in a flush row + eyebrow caption; no tiles</div>')


def render_b_feature_item(doc, key, item):
    return ('<div style="font-family:var(--font-heading);font-size:1.5rem;color:var(--ink)">&#8599;</div>'
            '<div class="ex-h3" style="margin-top:0.5rem">Self-guided tours</div>'
            '<p class="ex-body">Move at your own pace with margin captions throughout.</p>'
            f'{_arrow("Learn more")}'
            '<div class="ex-caption">Open grid cell &mdash; thin icon + didone heading + body + arrow; no box</div>')


def render_b_pricing_card(doc, key, item):
    return ('<div class="ex-rows"><div class="ex-row" style="padding-top:0">'
            '<div><span class="ex-counter" style="font-size:1.5rem">&pound;14</span> '
            '<span class="ex-eyebrow">Adult</span></div>'
            f'{_arrow("Buy")}</div></div>'
            '<div class="ex-caption">Plan as a ruled action row (numeral + label + arrow); never a boxed tile</div>')


def render_b_banner(doc, key, item):
    return ('<div class="surface-dark" style="display:flex;align-items:center;justify-content:space-between;gap:1rem">'
            '<span class="ex-label" style="color:var(--ink-inverse)">Late opening this Thursday</span>'
            '<span style="display:flex;gap:1.25rem;align-items:center">'
            '<a class="act" href="#" style="color:var(--accent)">Details <span class="arrow">&rarr;</span></a>'
            '<span style="color:var(--ink-inverse-muted);font-family:var(--font-heading)">&times;</span></span></div>'
            '<div class="ex-caption">Slim dark strip; uppercase text + arrow link; typographic dismiss</div>')


def render_b_modal(doc, key, item):
    return ('<div style="background:rgba(27,21,15,0.55);padding:1.25rem">'
            '<div class="surface-panel"><div style="display:flex;justify-content:space-between;align-items:start">'
            '<div class="ex-h3">Before you go</div>'
            '<span style="font-family:var(--font-heading)">&times;</span></div>'
            '<p class="ex-body" style="margin-top:0.5rem">A hard-edged square panel on a flat scrim.</p>'
            f'{_arrow("Got it")}</div></div>'
            '<div class="ex-caption">Square panel, radius 0, no shadow; flat scrim; typographic close</div>')


def render_b_dropdown_menu(doc, key, item):
    return (f'{_arrow("Visit")}'
            '<div class="surface-dark" style="margin-top:0.5rem;display:flex;flex-direction:column;gap:0.5rem">'
            '<span class="ex-label" style="color:var(--ink-inverse)">Hours</span>'
            '<span class="ex-label" style="color:var(--ink-inverse)">Getting here</span>'
            '<span class="ex-label" style="color:var(--ink-inverse)">Access</span></div>'
            '<div class="ex-caption">Flat square menu panel; uppercase links; slash/arrow trigger</div>')


def render_b_breadcrumb(doc, key, item):
    return ('<div class="ex-eyebrow">Home <span style="opacity:.5">/</span> Visit '
            '<span style="opacity:.5">/</span> Tickets</div>'
            '<div class="ex-caption">Uppercase Inter trail with the brand slash separator; muted</div>')


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
            '<div class="ex-caption">Big didone numerals + uppercase headings on ruled bars; never boxed</div>')


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


def build_section(doc, num, name, sub, items, contracts, renderers):
    cards = "\n".join(
        build_card(doc, key, item, contracts.get(key, {}), renderers)
        for key, item in items.items()
    )
    return f"""  <section class="tier">
    <div class="tier-num">{esc(num)}</div>
    <div class="tier-name">{esc(name)}</div>
    <div class="tier-sub">{esc(sub)}</div>
    <div class="tier-rule"></div>
  </section>
  <div class="list">
{cards}
  </div>"""


def build_page(doc, prim_items, prim_contracts, block_items, block_contracts, brand_dir=None):
    root, proxies = root_css(doc)
    gf = google_fonts_link(proxies)
    face_css = cs.font_face_css(brand_dir, doc) if brand_dir else ""
    name = (doc.get("brand") or {}).get("name", "Brand")
    snapshot = (((doc.get("brand") or {}).get("snapshot") or {}).get("value") or "").strip()

    n_actions = sum(1 for k in prim_items if k in ACTION_KINDS)

    prim_section = build_section(
        doc, "Tier 1", "Primitives",
        f"{len(prim_items)} atomic primitives &mdash; {n_actions} action elements carry an interactive state matrix",
        prim_items, prim_contracts, PRIMITIVE_RENDERERS)
    block_section = build_section(
        doc, "Tier 2", "Blocks",
        f"{len(block_items)} composed clusters &mdash; faithful mini-renders honoring the brand's slot grammar",
        block_items, block_contracts, BLOCK_RENDERERS)

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(name)} — Component Preview Gallery</title>
{gf}
<style>
{face_css}
{root}
{COMPONENT_ALIAS_CSS}
{BASE_CSS}
{cr.COMPONENT_CSS}
{cr.motion_vars_css(doc)}
{cr.link_hover_css(doc)}
</style>
</head>
<body>
<div class="page">
  <header class="masthead">
    <div class="eyebrow ex-eyebrow">/ Component Preview Gallery</div>
    <h1>{esc(name)}</h1>
    <p>{esc(snapshot)}</p>
    <div class="legend">
      <span><span class="badge badge-extracted">extracted</span> observed on the live page</span>
      <span><span class="badge badge-designed">synthesized</span> designed, not used on page</span>
      <span>radius 0 &middot; no shadows &middot; accent on dark only &middot; typographic actions</span>
    </div>
  </header>
{prim_section}
{block_section}
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


def main():
    ap = argparse.ArgumentParser(description="Render a brand-styled component preview gallery.")
    ap.add_argument("brand_yaml", type=Path, help="path to a brand.yaml")
    ap.add_argument("-o", "--out", type=Path, required=True,
                    help="output dir (writes <out>/index.html)")
    args = ap.parse_args()

    doc = yaml.safe_load(args.brand_yaml.read_text())
    prim_contracts = load_contract(args.brand_yaml, doc, "primitives")
    block_contracts = load_contract(args.brand_yaml, doc, "blocks")

    prim_items = doc.get("primitives") or {}
    block_items = doc.get("blocks") or {}

    page = build_page(doc, prim_items, prim_contracts, block_items, block_contracts,
                      brand_dir=args.brand_yaml.parent)

    args.out.mkdir(parents=True, exist_ok=True)
    out_file = args.out / "index.html"
    out_file.write_text(page)
    cs.copy_fonts(args.brand_yaml.parent, args.out / "assets", doc)

    n_actions = sum(1 for k in prim_items if k in ACTION_KINDS)
    print(f"Wrote {out_file}")
    print(f"  primitives: {len(prim_items)} (rendered)")
    print(f"  blocks:     {len(block_items)} (rendered)")
    print(f"  action elements with state matrices: {n_actions} "
          f"({', '.join(k for k in prim_items if k in ACTION_KINDS)})")


if __name__ == "__main__":
    main()
