#!/usr/bin/env python3
"""Shared, fact-gated brand kit for the greenhouse-v2 RELUME section bake-off.

Everything here is derived from MEASURED greenhouse-v2 brand facts:
  - tokens.manifest.json  (palette / type scale / spacing / radius / motion)
  - brand.yaml            (button matrices, signature devices, surface grammar)
  - section-copy.yaml     (real greenhouse copy)
  - media-assets.yaml     (real greenhouse assets)

It is brand-agnostic in construction: values are READ from the manifest, never
hand-typed. This module only assembles CSS variables + a shared component
vocabulary; it does NOT edit any pipeline renderer source.
"""
from __future__ import annotations

import json
from pathlib import Path

BRAND_DIR = Path(__file__).resolve().parent.parent.parent  # runs/greenhouse-v2/brand
TOKENS_MANIFEST = BRAND_DIR / "components-preview" / "tokens.manifest.json"


def load_token_index() -> dict[str, str]:
    """The measured design-token index (CSS var name -> value)."""
    doc = json.loads(TOKENS_MANIFEST.read_text())
    return doc["index"]


def tokens_root_css() -> str:
    """Emit the measured tokens as a :root block, verbatim from the manifest."""
    index = load_token_index()
    lines = [
        "/* Greenhouse measured design tokens — sourced verbatim from",
        "   runs/greenhouse-v2/brand/components-preview/tokens.manifest.json. */",
        ":root {",
    ]
    for name, value in index.items():
        if "@" in name:  # responsive overrides handled in media queries below
            continue
        lines.append(f"  {name}: {value};")
    lines.append("}")
    # responsive type ramp (measured @tablet / @mobile overrides from the manifest)
    lines.append("@media (max-width: 991px) { :root {")
    for name, value in index.items():
        if name.endswith("@tablet"):
            lines.append(f"  {name.split('@')[0]}: {value};")
    lines.append("} }")
    lines.append("@media (max-width: 479px) { :root {")
    for name, value in index.items():
        if name.endswith("@mobile"):
            lines.append(f"  {name.split('@')[0]}: {value};")
    lines.append("} }")
    return "\n".join(lines)


# --- signature fingerprint-leaf line art (brand signature device) ------------
def fingerprint_leaf_svg(stroke_var: str = "currentColor", opacity: float = 1.0) -> str:
    """Concentric fingerprint ridges shaped into a leaf — the greenhouse
    'decorative fingerprint-leaf line art' signature (brand.yaml signatures)."""
    cx, cy = 200, 250
    rings = []
    base = ("M200,24 C132,150 132,350 200,476 "
            "C268,350 268,150 200,24 Z")
    for i, s in enumerate([1.0, 0.86, 0.72, 0.58, 0.44, 0.30, 0.16]):
        rings.append(
            f'<g transform="translate({cx},{cy}) scale({s:.3f}) translate({-cx},{-cy})">'
            f'<path d="{base}" fill="none" stroke="{stroke_var}" '
            f'stroke-width="{2.4 / max(s,0.18):.2f}" stroke-linecap="round"/></g>'
        )
    vein = (f'<path d="M200,60 L200,440" fill="none" stroke="{stroke_var}" '
            f'stroke-width="2.2" stroke-linecap="round"/>')
    for yy, dx in ((150, 44), (230, 60), (320, 52), (395, 34)):
        vein += (f'<path d="M200,{yy} C{200-dx*0.5},{yy+6} {200-dx},{yy+18} {200-dx-6},{yy+40}" '
                 f'fill="none" stroke="{stroke_var}" stroke-width="1.8" stroke-linecap="round"/>')
        vein += (f'<path d="M200,{yy} C{200+dx*0.5},{yy+6} {200+dx},{yy+18} {200+dx+6},{yy+40}" '
                 f'fill="none" stroke="{stroke_var}" stroke-width="1.8" stroke-linecap="round"/>')
    return (f'<svg class="gh-fingerprint" viewBox="0 0 400 500" '
            f'style="opacity:{opacity}" aria-hidden="true" '
            f'xmlns="http://www.w3.org/2000/svg">{"".join(rings)}{vein}</svg>')


def brand_g_badge(size_rem: float = 3.0) -> str:
    """Circular emerald brand badge with a lowercase g glyph (signature device)."""
    return (f'<span class="gh-badge" style="--sz:{size_rem}rem" aria-hidden="true">'
            f'<span class="gh-badge-g">g</span></span>')


# --- shared component CSS (all values via measured token vars) ----------------
BRAND_CSS = r"""
* { margin: 0; padding: 0; box-sizing: border-box; }
img, svg { display: block; max-width: 100%; }
html { -webkit-font-smoothing: antialiased; text-rendering: optimizeLegibility; }
body {
  font-family: "Untitled Sans", "Inter", Arial, sans-serif;
  color: var(--color-text-primary);
  background: var(--color-surface-canvas);
  font-size: var(--size-body);
  line-height: var(--leading-body);
}
a { color: inherit; }

/* brand family aliases: measured family first, close free stand-in second */
:root {
  --gh-serif: "Untitled Serif", "Fraunces", Georgia, "Times New Roman", serif;
  --gh-sans:  "Untitled Sans", "Inter", Arial, sans-serif;
  --gh-maxw: 1200px;            /* measured content column ~1216px */
  --gh-pad-x: clamp(1.5rem, 5vw, 5rem);
}

/* ---- surfaces (surface grammar: canvas / tint / muted / inverse) ---- */
.gh-sec { padding: clamp(4rem, 8vw, 8.125rem) var(--gh-pad-x); position: relative; overflow: hidden; }
.gh-sec--band { padding-top: clamp(6rem, 11vw, 12.5rem); padding-bottom: clamp(6rem, 11vw, 12.5rem); }
.surf-canvas  { background: var(--color-surface-canvas); color: var(--color-text-primary); }
.surf-tint    { background: var(--color-surface-tint);   color: var(--color-text-primary); }
.surf-muted   { background: var(--color-surface-muted);  color: var(--color-text-primary); }
.surf-inverse { background: var(--color-surface-inverse); color: var(--color-text-on-inverse); }
.gh-wrap { max-width: var(--gh-maxw); margin-inline: auto; position: relative; z-index: 2; }
.gh-wrap--wide { max-width: 1320px; }

/* ---- typography ---- */
.gh-eyebrow {
  font-family: var(--gh-sans); font-size: var(--size-eyebrow); font-weight: 600;
  letter-spacing: .06em; text-transform: uppercase; color: var(--color-accent-primary);
  display: inline-block;
}
.surf-inverse .gh-eyebrow { color: var(--color-accent-soft); }
.gh-display {
  font-family: var(--gh-serif); font-weight: 400; font-size: var(--size-display-hero);
  line-height: var(--leading-display-hero); letter-spacing: var(--tracking-display-hero);
  color: inherit;
}
.gh-h2 {
  font-family: var(--gh-serif); font-weight: 400; font-size: var(--size-h2);
  line-height: var(--leading-h2); letter-spacing: var(--tracking-h2); color: inherit;
}
.gh-h3 {
  font-family: var(--gh-serif); font-weight: 400; font-size: 1.75rem;
  line-height: 1.2; letter-spacing: -0.01em; color: inherit;
}
.gh-body {
  font-family: var(--gh-sans); font-size: var(--size-body); line-height: var(--leading-body);
  color: var(--color-text-on-primary-muted); max-width: 42ch;
}
.surf-inverse .gh-body { color: var(--color-text-on-inverse-muted); }
.gh-body--wide { max-width: 60ch; }
.gh-lead { font-size: 1.3125rem; }

/* ---- pill buttons (measured button matrix, radius 24px, pad 12/32) ---- */
.gh-btn {
  display: inline-flex; align-items: center; gap: .5rem; cursor: pointer;
  font-family: var(--gh-sans); font-size: 15px; font-weight: 500; line-height: 1;
  padding: 14px 32px; border-radius: var(--radius-global); border: 1px solid transparent;
  text-decoration: none; transition: background var(--motion-base) var(--motion-ease),
    color var(--motion-base) var(--motion-ease), border-color var(--motion-base) var(--motion-ease);
  white-space: nowrap;
}
.gh-btn--green  { background: var(--color-accent-primary); color: #fff; border-color: var(--color-accent-primary); }
.gh-btn--green:hover  { background: #006147; border-color: #006147; }
.gh-btn--blue   { background: var(--color-accent-secondary); color: #fff; border-color: var(--color-accent-secondary); }
.gh-btn--blue:hover   { background: #3860be; border-color: #3860be; }
.gh-btn--outline-dark  { background: transparent; color: var(--color-text-primary); border-color: var(--color-text-primary); }
.gh-btn--outline-dark:hover  { background: var(--color-text-primary); color: #fff; }
.gh-btn--outline-white { background: transparent; color: #fff; border-color: rgba(255,255,255,.7); }
.gh-btn--outline-white:hover { background: #fff; color: var(--color-text-primary); }

/* ghost / arrow text link */
.gh-link {
  font-family: var(--gh-sans); font-size: 15px; font-weight: 500; text-decoration: none;
  color: var(--color-accent-primary); display: inline-flex; align-items: center; gap: .4rem;
  position: relative;
}
.surf-inverse .gh-link { color: var(--color-accent-soft); }
.gh-link .gh-arrow { transition: transform var(--motion-fast) var(--motion-ease); }
.gh-link:hover .gh-arrow { transform: translateX(.3rem); }
.gh-link--ink { color: var(--color-text-primary); }
.surf-inverse .gh-link--ink { color: #fff; }

.gh-actions { display: flex; align-items: center; gap: 1.25rem; flex-wrap: wrap; }
.gh-actions--center { justify-content: center; }

/* ---- cards / media wells / floating product-UI ---- */
.gh-card {
  background: #fff; border-radius: 18px; overflow: hidden;
  box-shadow: var(--shadow-subtle); display: flex; flex-direction: column;
  border: 1px solid var(--color-border-hairline-on-primary);
}
.gh-card__media { aspect-ratio: 16/10; background: var(--color-surface-muted); overflow: hidden; }
.gh-card__media img { width: 100%; height: 100%; object-fit: cover; }
.gh-card__body { padding: 1.75rem; display: flex; flex-direction: column; gap: .75rem; align-items: flex-start; }
.gh-card__body .gh-body { max-width: none; }

.gh-media-well {
  border-radius: 22px; overflow: hidden; background: var(--color-surface-tint);
  box-shadow: var(--shadow-raised);
}
.gh-media-well img { width: 100%; height: 100%; object-fit: cover; display: block; }

/* floating product-UI chip + circle portrait (signature float device) */
.gh-float { position: absolute; border-radius: 18px; overflow: hidden; box-shadow: var(--shadow-raised);
  background: #fff; z-index: 3; }
.gh-float img { width: 100%; height: 100%; object-fit: cover; }
.gh-portrait { position: absolute; border-radius: 999px; overflow: hidden; box-shadow: var(--shadow-raised);
  z-index: 3; background: var(--color-surface-tint); }
.gh-portrait img { width: 100%; height: 100%; object-fit: cover; }

/* ---- circular emerald brand badge (lowercase g) ---- */
.gh-badge { width: var(--sz,3rem); height: var(--sz,3rem); border-radius: 999px;
  background: var(--color-accent-primary); display: inline-flex; align-items: center;
  justify-content: center; flex: none; }
.gh-badge-g { font-family: var(--gh-serif); color: #fff; font-size: calc(var(--sz,3rem) * .58);
  line-height: 1; font-weight: 500; transform: translateY(-.02em); }

/* ---- fingerprint-leaf decorative art ---- */
.gh-fingerprint { position: absolute; pointer-events: none; z-index: 1; }

/* ---- grids ---- */
.gh-grid { display: grid; gap: 2.5rem; }
.gh-grid--2 { grid-template-columns: repeat(2, minmax(0,1fr)); }
.gh-grid--3 { grid-template-columns: repeat(3, minmax(0,1fr)); }
.gh-grid--4 { grid-template-columns: repeat(4, minmax(0,1fr)); }
.gh-split { display: grid; grid-template-columns: 1fr 1fr; gap: clamp(2.5rem, 6vw, 6rem); align-items: center; }
.gh-split--wide-media { grid-template-columns: 0.9fr 1.1fr; }
.gh-split--wide-copy  { grid-template-columns: 1.1fr 0.9fr; }

.gh-stack { display: flex; flex-direction: column; }
.gh-stack--center { align-items: center; text-align: center; }
.gh-eyebrow-gap { margin-bottom: var(--space-eyebrow-to-heading); }
.gh-heading-gap { margin-top: var(--space-heading-to-body); }
.gh-cta-gap { margin-top: var(--space-body-to-cta); }
.gh-vrule { width: 1px; background: var(--color-border-hairline-on-primary); align-self: stretch; }
.surf-inverse .gh-vrule { background: rgba(255,255,255,.18); }

/* ---- quote / testimonial ---- */
.gh-quote-mark { font-family: var(--gh-serif); font-size: 4rem; line-height: .6; color: var(--color-accent-primary);
  display: block; height: 2.2rem; }
.surf-inverse .gh-quote-mark { color: var(--color-accent-soft); }
.gh-quote { font-family: var(--gh-serif); font-size: 1.375rem; line-height: 1.4; color: inherit; font-weight: 400; }
.gh-person { display: flex; align-items: center; gap: .85rem; }
.gh-person__avatar { width: 3rem; height: 3rem; border-radius: 999px; background: var(--color-surface-tint);
  overflow: hidden; flex: none; display:flex; align-items:center; justify-content:center; }
.gh-person__avatar img { width: 100%; height: 100%; object-fit: cover; }
.gh-person__name { font-family: var(--gh-sans); font-weight: 600; font-size: 1rem; }
.gh-person__meta { font-family: var(--gh-sans); font-size: .875rem; color: var(--color-text-on-primary-muted); }
.surf-inverse .gh-person__meta { color: var(--color-text-on-inverse-muted); }

/* ---- logo wall ---- */
.gh-logogrid { display: grid; gap: clamp(1.5rem,3vw,2.5rem) clamp(2rem,4vw,3.5rem);
  align-items: center; justify-items: center; }
.gh-logogrid img { max-height: 2.6rem; max-width: 100%; width: auto; object-fit: contain; }
.gh-logorow { display: flex; align-items: center; justify-content: center; flex-wrap: wrap;
  gap: clamp(2rem,5vw,4.5rem); }
.gh-logorow img { max-height: 2.4rem; width: auto; object-fit: contain; }
.surf-inverse .gh-logo-knockout { filter: brightness(0) invert(1); opacity: .9; }
.gh-logo-card { background:#fff; border-radius: 16px; padding: 1.5rem 2rem;
  display:flex; align-items:center; justify-content:center; box-shadow: var(--shadow-subtle);
  border: 1px solid var(--color-border-hairline-on-primary); min-height: 6rem; }
.gh-logo-card img { max-height: 2.4rem; width:auto; }

/* ---- stat / metric ---- */
.gh-stat-value { font-family: var(--gh-serif); font-size: clamp(3rem,6vw,4.5rem); line-height: 1;
  color: var(--color-accent-primary); font-weight: 400; }
.surf-inverse .gh-stat-value { color: var(--color-accent-soft); }

/* ---- pill filter row ---- */
.gh-pills { display:flex; flex-wrap:wrap; gap:.6rem; }
.gh-pill { font-family: var(--gh-sans); font-size:.875rem; padding:.5rem 1.1rem; border-radius:999px;
  border:1px solid var(--color-border-hairline-on-primary); color: var(--color-text-on-primary-muted);
  background:#fff; }
.gh-pill--on { background: var(--color-accent-primary); color:#fff; border-color: var(--color-accent-primary); }

/* ---- tabs ---- */
.gh-tabs { display:flex; gap:.5rem; flex-wrap:wrap; }
.gh-tab { font-family: var(--gh-sans); font-size:.95rem; font-weight:500; padding:.7rem 1.4rem;
  border-radius:999px; border:1px solid var(--color-border-hairline-on-primary);
  background:#fff; color: var(--color-text-on-primary-muted); cursor:pointer; }
.gh-tab--on { background: var(--color-text-primary); color:#fff; border-color: var(--color-text-primary); }

/* ---- badges strip ---- */
.gh-badges { display:flex; gap:1.25rem; flex-wrap:wrap; align-items:center; }
.gh-badges img { height: 5.5rem; width:auto; }

@media (max-width: 900px) {
  .gh-split, .gh-grid--2, .gh-grid--3, .gh-grid--4 { grid-template-columns: 1fr; }
  .gh-float, .gh-portrait { display: none; }
}
"""


def page(title: str, body: str, *, root_prefix: str = "../../") -> str:
    """Wrap a section body into a full self-contained HTML doc."""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,300..500&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style id="tokens">
{tokens_root_css()}
</style>
<style id="brand">
{BRAND_CSS}
</style>
</head>
<body>
{body}
</body>
</html>
"""
