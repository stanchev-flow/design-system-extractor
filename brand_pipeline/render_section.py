#!/usr/bin/env python3
"""render_section.py - extractor-side faithful render of ONE section, driven by brand.yaml.

This is NOT the Webflow assembler. It builds a standalone HTML/CSS preview whose
tokens (colors, type sizes, spacing, radius) are read from brand.yaml and whose
DOM is a FAITHFUL EQUIVALENT of the real AISB library components named in the
section's componentMapping (same slot structure, same surface mode, same
width/grid/overlap rules). Composites use absolute offsets inside the Stack slot
(SIGN-OFF #5). Goal: an on-brand result that will transfer to Webflow later.

GENERALIZATION (2026-06-15): the renderer is now data-driven and brand-agnostic.
It dispatches on `layout.renderKind` (falling back to `archetype`):

  - "collage"    -> legacy WoodWave composite hero (display-text-over-media +
                    media-over-media via absolute offsets). UNCHANGED from v1.
  - "hero-cta"   -> centered hero cluster (eyebrow -> heading -> body -> filled +
                    outline CTA pair) over a full-bleed photo with a soft scrim.
  - "cta-stack"  -> centered heading + button pair on an inverse band.
  - "feature-grid" -> header cluster + grid of rounded, shadowed feature cards.

Surfaces, fonts (with non-Google proxies), radius and copy are ALL read from
brand.yaml; nothing about WoodWave or HubSpot is hardcoded in the generic paths.

Usage:
  python3 render_section.py <brand.yaml> <layoutId> -o <outdir>
"""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

import yaml


# ── token resolvers (shared) ───────────────────────────────────────────────────

def color_value(doc, token):
    """Resolve a token ref (e.g. 'text/on-inverse' or 'accent/primary') to hex."""
    if not token:
        return None
    c = doc["tokens"]["colors"].get(token)
    return c["value"] if c else token


# A loadable Google-Fonts proxy by generic family, used when a type role carries
# no explicit renderProxy (e.g. the families+scale token shape). Brand-agnostic.
_PROXY_FOR_GENERIC = {"serif": "Source Serif 4", "sans-serif": "Lexend Deca"}


def _normalize_scale_entry(entry, families):
    """Map a `tokens.type.scale` entry (families+scale shape) onto the flat
    type-role shape the renderer consumes (family/sizeRem/lineHeight/weight/...)."""
    fam_key = entry.get("family")
    fam_node = families.get(fam_key) if isinstance(families, dict) else None
    fam = fam_node.get("value") if isinstance(fam_node, dict) else (fam_key or None)
    return {
        "family": fam,
        "sizeRem": entry.get("sizeRem"),
        "lineHeight": entry.get("line", entry.get("lineHeight")),
        "weight": entry.get("weight"),
        "letterSpacing": entry.get("tracking", entry.get("letterSpacing")),
        "case": entry.get("case"),
    }


def _pick_scale_entry(role, scale):
    """Pick a scale entry for a requested render role by family/keyword. Generic:
    no brand literals - matches on the family bucket and role keywords."""
    r = role.lower()
    items = list(scale.items())

    def fam(famkey):
        return [v for _, v in items if v.get("family") == famkey]

    if "eyebrow" in r:
        for k, v in items:
            if "eyebrow" in k or v.get("case") == "uppercase":
                return v
    if "display" in r or "hero" in r or r in ("h0", "h1"):
        disp = fam("display") or [v for _, v in items]
        return max(disp, key=lambda v: v.get("sizeRem") or 0)
    if "button" in r or "control" in r:
        btn = fam("button")
        if btn:
            return min(btn, key=lambda v: v.get("sizeRem") or 0)
    if "body" in r or "paragraph" in r:
        for k, v in items:
            if k.startswith("body") and k.endswith("-lg"):
                return v
        body = [v for k, v in items if k.startswith("body")]
        if body:
            return body[0]
    return scale.get(role)


def type_role(doc, role):
    """Resolve a type role. Supports the flat shape (role -> spec, WoodWave) AND the
    families+scale shape (tokens.type.{families,scale}, HubSpot). Brand-agnostic;
    the flat path returns the original node unchanged."""
    types = doc.get("tokens", {}).get("type", {})
    node = types.get(role)
    if isinstance(node, dict) and ("family" in node or "sizeRem" in node):
        return node
    scale = types.get("scale")
    if isinstance(scale, dict):
        entry = _pick_scale_entry(role, scale)
        if entry:
            return _normalize_scale_entry(entry, types.get("families") or {})
    return node if isinstance(node, dict) else {}


def spacing_value(doc, role, default="0rem"):
    s = doc["tokens"]["spacing"].get(role, {})
    return s.get("value", default)


def base_size(t):
    sz = t.get("sizeRem", {})
    if isinstance(sz, dict):
        return sz.get("base")
    return sz


def css_len(value, default):
    """Sanitize an approximate brand.yaml offset (e.g. '~-2.75rem') into valid CSS."""
    if value is None:
        return default
    v = str(value).replace("~", "").strip()
    return v or default


def resolve_surface(doc, layout):
    """Return (role, surface-dict). Prefers layout.surfaceRole; else matches the
    layout's surfaceMode.mode against tokens.surfaces[*].schemeMode."""
    surfaces = doc["tokens"]["surfaces"]
    role = layout.get("surfaceRole")
    if role and role in surfaces:
        return role, surfaces[role]
    mode = (layout.get("surfaceMode") or {}).get("mode")
    for r, s in surfaces.items():
        if s.get("schemeMode") == mode:
            return r, s
    # last-resort default
    first = next(iter(surfaces))
    return first, surfaces[first]


# Non-Google webfonts -> a close Google Fonts proxy that DOES load, so the preview
# reads on-brand. The canonical family name stays first in the CSS stack.
_PROXY_GF = {
    "Source Serif 4": "Source+Serif+4:opsz,wght@8..60,400;8..60,500;8..60,600",
    "Playfair Display": "Playfair+Display:wght@400;500",
    "Lexend Deca": "Lexend+Deca:wght@300;400;500;600;700",
    "Inter": "Inter:wght@400;500;600",
}
_SERIF_HINTS = ("serif", "playfair", "didone", "georgia")


def _generic_family(family, proxy):
    base = f"{family} {proxy}".lower()
    return "serif" if any(h in base for h in _SERIF_HINTS) else "sans-serif"


def font_stack(doc, role, fallback_family="sans-serif"):
    t = type_role(doc, role)
    fam = t.get("family")
    proxy = t.get("renderProxy")
    if not fam:
        return fallback_family, set()
    generic = _generic_family(fam, proxy or "")
    if not proxy:
        # No explicit renderProxy (families+scale shape): pick a loadable proxy so
        # the preview reads on-brand instead of silently falling back to a system font.
        proxy = _PROXY_FOR_GENERIC.get(generic)
    parts = [f"'{fam}'"]
    used = set()
    if proxy:
        parts.append(f"'{proxy}'")
        used.add(proxy)
    parts.append(generic)
    return ", ".join(parts), used


def google_fonts_link(proxies):
    families = [_PROXY_GF[p] for p in sorted(proxies) if p in _PROXY_GF]
    if not families:
        return ""
    q = "&".join(f"family={f}" for f in families)
    return ('<link rel="preconnect" href="https://fonts.googleapis.com">\n'
            '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
            f'<link href="https://fonts.googleapis.com/css2?{q}&display=swap" rel="stylesheet">')


def find_map(layout, *role_substrings):
    """First componentMapping entry whose role contains any of the substrings."""
    for m in layout.get("componentMapping", []):
        role = (m.get("role") or "").lower()
        if any(s in role for s in role_substrings):
            return m
    return None


def prop(m, key, default=""):
    if not m:
        return default
    return (m.get("props") or {}).get(key, default)


# ── legacy WoodWave collage (UNCHANGED behavior from v1) ────────────────────────

def build_css_collage(doc, layout):
    surf_role, surf = resolve_surface(doc, layout)
    bg = surf.get("bg")
    text = color_value(doc, surf["textPrimary"])
    accent = color_value(doc, surf["textAccent"]) if surf.get("textAccent") else text

    disp = type_role(doc, "display-hero")
    ctrl = type_role(doc, "control-text")
    radius = spacing_value(doc, "radius-global", "0rem")
    pad = doc["tokens"]["spacing"].get("section-padding-dark", {}).get("value") \
        or spacing_value(doc, "section-padding-default", "6.25rem")

    heading_font = disp.get("family", "serif")
    body_font = ctrl.get("family", "sans-serif")

    off = (layout.get("overlapRules", {}) or {}).get("offsets", {})
    disp_sizes = disp.get("sizeRem", {}) if isinstance(disp.get("sizeRem"), dict) else {}
    size_tablet = disp_sizes.get("tablet", 4.5)
    size_mobile = disp_sizes.get("mobile", 3)

    css = f""":root {{
  --bg: {bg};
  --text: {text};
  --accent: {accent};
  --font-heading: '{heading_font}', Georgia, serif;
  --font-body: '{body_font}', system-ui, sans-serif;
  --display-size: {base_size(disp)}rem;
  --display-lh: {disp.get('lineHeight','1.05em')};
  --display-ls: {disp.get('letterSpacing','0rem')};
  --ctrl-size: {base_size(ctrl)}rem;
  --ctrl-ls: {ctrl.get('letterSpacing','0.08em')};
  --radius: {radius};
  --section-pad: {pad};
  --eyebrow-ls: 0.08em;
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
html {{ background: var(--bg); height: 100%; }}
/* iframe-safe container context: cq* length units resolve against this sized box
   (Studio renders this HTML in an iframe where viewport-relative units misbehave). */
html, body {{ background: var(--bg); color: var(--text); font-family: var(--font-body); -webkit-font-smoothing: antialiased; }}
body {{ min-height: 100%; container-type: size; container-name: frame; }}

/* Section / Stack scaffold (full-bleed, surface mode = Inverse) */
.wd-section {{
  background: var(--bg);
  color: var(--text);
  padding: 1.75rem 2.5rem var(--section-pad);
  min-height: 100cqh;
}}

/* Nav row: Logo + slash nav (control-text) - zero chrome */
.wd-nav {{
  display: flex; align-items: center; justify-content: space-between;
  gap: 2rem; margin-bottom: clamp(2rem, 6cqw, 5.5rem);
}}
.wd-logo {{
  display: inline-flex; align-items: center; gap: 0.5rem;
  font-family: var(--font-body); font-weight: 600;
  font-size: var(--ctrl-size); letter-spacing: var(--ctrl-ls);
  text-transform: uppercase; color: var(--accent);
}}
.wd-logo .glyph {{ font-family: var(--font-heading); font-size: 1.1rem; }}
.wd-navlinks {{ display: flex; gap: 0.55rem; flex: 1; justify-content: center; }}
.wd-navlinks a, .wd-cta {{
  font-family: var(--font-body); font-size: var(--ctrl-size);
  letter-spacing: var(--ctrl-ls); text-transform: uppercase;
  text-decoration: none; color: var(--text); white-space: nowrap;
}}
.wd-navlinks .sep {{ color: var(--text); opacity: 0.55; }}
.wd-cta {{ color: var(--accent); }}

/* Stack slot: centered display title over layered media */
.wd-slot {{ display: flex; flex-direction: column; align-items: center; }}

/* Heading / Style: display - the only sanctioned text-over-media */
.wd-heading.is-display {{
  font-family: var(--font-heading);
  font-weight: {disp.get('weight',400)};
  font-size: var(--display-size);
  line-height: var(--display-lh);
  letter-spacing: var(--display-ls);
  text-transform: uppercase;
  color: var(--accent);
  text-align: center;
  position: relative; z-index: 2;
  margin-bottom: {css_len(off.get('titleOverMediaTop'), '-2.75rem')};
}}

/* media-over-media composite: absolute offsets inside the Stack slot (SIGN-OFF #5) */
.wd-collage {{ position: relative; width: 100%; max-width: 80rem; }}
.wd-media {{ display: block; width: 100%; border-radius: var(--radius);
  border: none; box-shadow: none; }}
.wd-media.is-hero {{ aspect-ratio: 1355 / 570; object-fit: cover; }}
.wd-media.is-overlap {{
  position: absolute;
  width: 34%;
  right: 4%;
  bottom: -28%;
  aspect-ratio: 785 / 620;
  object-fit: cover;
  z-index: 1;
}}
.wd-spacer {{ height: 22cqw; }}

@media (max-width: 991px) {{
  :root {{ --display-size: {size_tablet}rem; }}
  .wd-navlinks {{ display: none; }}
}}
@media (max-width: 767px) {{
  :root {{ --display-size: {size_mobile}rem; }}
  .wd-section {{ padding: 1.25rem 1.25rem 3rem; }}
  .wd-media.is-overlap {{ width: 46%; right: 2%; bottom: -18%; }}
  .wd-spacer {{ height: 30cqw; }}
}}
"""
    return css


def build_html_collage(doc, layout):
    css = build_css_collage(doc, layout)
    name = doc["brand"]["name"]
    title_text = "WOODWAVE GALLERY"
    for m in layout.get("componentMapping", []):
        if m.get("role") == "display title":
            title_text = m.get("props", {}).get("Text", title_text)
    parts = title_text.split(" ")
    if len(parts) >= 2:
        line1, line2 = parts[0], " ".join(parts[1:])
    else:
        line1, line2 = title_text, ""

    nav = ["About", "Gallery", "Exhibition", "Visit"]
    navhtml = ' <span class="sep">/</span> '.join(
        f'<a href="#">{html.escape(n)}</a>' for n in nav)

    body = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(name)} - {layout['id']} (brand.yaml render)</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;500&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
{css}
</style>
</head>
<body>
<!-- Section / Stack (componentId 185a3d3a-0806-d61b-7c06-c5fdd636b093), surface mode: Inverse -->
<section class="wd-section">
  <!-- Logo (1f142114) wordmark + slash nav (control-text) - neverDo:no-buttons honored -->
  <nav class="wd-nav">
    <span class="wd-logo"><span class="glyph">&#9697;</span> WoodWave</span>
    <span class="wd-navlinks">{navhtml}</span>
    <a class="wd-cta" href="#">Buy Tickets</a>
  </nav>

  <!-- Stack Slot: display title over layered photo collage -->
  <div class="wd-slot">
    <!-- Heading (b2fd0399) Style:display - display-text-over-media overlap -->
    <h1 class="wd-heading is-display">{html.escape(line1)}<br>{html.escape(line2)}</h1>

    <!-- media-over-media via absolute offsets (SIGN-OFF #5) -->
    <div class="wd-collage">
      <!-- Image (abb0f607) hero landscape, Radius:false -->
      <img class="wd-media is-hero" src="assets/hero-staircase.jpg"
           alt="Spiral wooden staircase shot from above">
      <!-- Image (abb0f607) overlap portrait, Radius:false, anchored center-right crossing bottom -->
      <img class="wd-media is-overlap" src="assets/overlap-vase.jpg"
           alt="Terracotta vase on a wooden ledge">
    </div>
    <div class="wd-spacer"></div>
  </div>
</section>
</body>
</html>
"""
    return body


# ── generic shared head/reset for the new data-driven kinds ─────────────────────

def _doc_head(doc, layout, title, proxies, extra_css):
    name = doc["brand"]["name"]
    gf = google_fonts_link(proxies)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(name)} - {title} (brand.yaml render)</title>
{gf}
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
img {{ display: block; max-width: 100%; }}
{extra_css}
</style>
</head>
<body>"""


def _shadow(doc, default="0 4px 8px rgba(0,0,0,0.08)"):
    for r in doc.get("compositionRules", []):
        if r.get("id") == "soft-elevation":
            return (r.get("value") or {}).get("shadow", default)
    return default


# ── hero-cta (centered hero over full-bleed photo, flat dark scrim, NO blur) ────

def _bg_media_slot(layout):
    """Find a full-bleed background media slot (by type + name/use-case keywords)."""
    slots = layout.get("slots") or []
    for s in slots:
        nm = ((s.get("name") or "") + " " + (s.get("useCase") or "")).lower()
        if s.get("type") == "media" and any(
                k in nm for k in ("background", "full-bleed", "photo", "image")):
            return s
    for s in slots:
        if s.get("type") == "media":
            return s
    return None


def _load_section_copy(doc, layout, brand_yaml):
    """Optional display copy from the brand's referenced section inventory
    (`indexes.sections`), matched by `layout.index`. Brand-agnostic and fully
    defensive: any miss returns {} so the renderer stays robust and brand.yaml-driven
    for everything else. Lets the hero show real source copy without inlining it."""
    if brand_yaml is None:
        return {}
    idx = layout.get("index")
    sec_ref = (doc.get("indexes") or {}).get("sections")
    if sec_ref is None or idx is None:
        return {}
    try:
        path = (Path(brand_yaml).parent / sec_ref).resolve()
        data = json.loads(path.read_text())
    except Exception:
        return {}
    sec = next((s for s in data.get("sections", []) if s.get("index") == idx), None)
    if not sec:
        return {}
    out = {}
    for slot in sec.get("slots", []) or []:
        for comp in slot.get("composites", []) or []:
            role = (comp.get("role") or "").lower()
            props = comp.get("props") or {}
            if role == "eyebrow" and props.get("text") and "eyebrow" not in out:
                out["eyebrow"] = props["text"]
            elif role == "heading" and props.get("heading") and "heading" not in out:
                out["heading"] = props["heading"]
            elif role in ("body", "paragraph") and props.get("text") and "body" not in out:
                out["body"] = props["text"]
    return out


def build_hero_cta(doc, layout, brand_yaml=None):
    _, surf = resolve_surface(doc, layout)
    accent = color_value(doc, surf.get("textAccent")) or "#ff4800"
    bg = surf.get("bg", "#000000")

    # Hero treatment is authoritative for the photo darkening: flat dark scrim, NO blur.
    hero_t = (doc.get("heroTreatment") or {}).get("value") or {}
    # Text sits over the photo, so it reads from the on-image color, not the surface ink.
    text = hero_t.get("textColor") or color_value(doc, "text/on-image") \
        or color_value(doc, surf.get("textPrimary")) or "#ffffff"

    # Buttons - FILLED primary + outline secondary, all read from brand.yaml `buttons`.
    btns = doc.get("buttons") or {}
    prim = btns.get("primary") or {}
    sec = btns.get("secondary") or {}
    btn_bg = prim.get("bg") or accent
    btn_fg = prim.get("fg") or color_value(doc, "action/primary-fg") or "#ffffff"
    btn_hover = prim.get("bgHover") or color_value(doc, "brand/primary-hover") or btn_bg
    btn_pad = prim.get("padding") or "0.75rem 1.5rem"
    sec_border = sec.get("border") or f"1px solid {accent}"

    # Background photo: layout.background.image -> media slot asset -> heroTreatment asset.
    bgblock = layout.get("background") or {}
    bg_slot = _bg_media_slot(layout) or {}
    asset = bgblock.get("image") or bg_slot.get("asset") or hero_t.get("asset")
    image = ("assets/" + Path(str(asset)).name) if asset else ""
    overlay = hero_t.get("overlay") or {}
    scrim = bgblock.get("scrim") or overlay.get("color") \
        or color_value(doc, "overlay/scrim") or "rgba(0,0,0,0.5)"
    blur_raw = bgblock.get("blur", hero_t.get("blur"))
    blur_on = bool(blur_raw) and str(blur_raw).strip().lower() not in ("none", "0", "0px", "")

    disp = type_role(doc, "display-hero")
    eyb = type_role(doc, "eyebrow")
    bod = type_role(doc, "body")
    ctl = type_role(doc, "control-text")
    heading_stack, p1 = font_stack(doc, "display-hero", "Georgia, serif")
    body_stack, p2 = font_stack(doc, "body", "system-ui, sans-serif")
    eyebrow_stack, p3 = font_stack(doc, "eyebrow", "system-ui, sans-serif")
    btn_stack, p4 = font_stack(doc, "control-text", "system-ui, sans-serif")
    proxies = p1 | p2 | p3 | p4

    rad_btn = prim.get("radius") or spacing_value(
        doc, "radius-button", spacing_value(doc, "radius-global", "0.5rem"))
    pad = spacing_value(doc, "section-y-default",
                        spacing_value(doc, "section-padding-default", "5rem"))
    gap_node = (layout.get("gridRules", {}) or {}).get("gap", {})
    gap = gap_node.get("value", "1.5rem") if isinstance(gap_node, dict) else "1.5rem"
    shadow = _shadow(doc)

    copy = _load_section_copy(doc, layout, brand_yaml)
    eyebrow_text = copy.get("eyebrow", "")
    heading_text = copy.get("heading") or "Heading"
    body_text = copy.get("body", "")
    p_label = (prim.get("mappedComponent") or {}).get("props", {}).get("Label") or "Get started"
    s_label = (sec.get("mappedComponent") or {}).get("props", {}).get("Label") or ""

    ds_raw = disp.get("sizeRem")
    disp_base = ds_raw.get("base") if isinstance(ds_raw, dict) else ds_raw
    disp_mobile = ds_raw.get("mobile") if isinstance(ds_raw, dict) else None

    bg_layer = (f"background: url('{html.escape(image)}') center/cover no-repeat;"
                if image else f"background: {bg};")
    blur_css = f"\n  filter: blur({blur_raw});" if blur_on else ""

    css = f""":root {{
  --bg: {bg};
  --text: {text};
  --accent: {accent};
  --btn-bg: {btn_bg};
  --btn-fg: {btn_fg};
  --btn-hover: {btn_hover};
  --font-heading: {heading_stack};
  --font-body: {body_stack};
  --font-eyebrow: {eyebrow_stack};
  --font-button: {btn_stack};
  --display-size: {disp_base or 4}rem;
  --radius-button: {rad_btn};
  --section-pad: {pad};
  --gap: {gap};
  --shadow: {shadow};
}}
/* iframe-safe container context: cq* length units resolve against this sized box
   (Studio renders this HTML in an iframe where viewport-relative units misbehave). */
html {{ background: var(--bg); height: 100%; }}
html, body {{ background: var(--bg); color: var(--text); font-family: var(--font-body); -webkit-font-smoothing: antialiased; }}
body {{ min-height: 100%; container-type: size; container-name: frame; }}

/* Section / Stack scaffold, surface mode On Image, full-bleed photo + flat dark scrim (NO blur) */
.hs-hero {{
  position: relative; min-height: 100cqh; overflow: hidden;
  display: flex; align-items: center; justify-content: center;
  padding: calc(var(--section-pad) + 3rem) 1.5rem var(--section-pad);
  background: var(--bg); color: var(--text);
}}
.hs-bg {{ position: absolute; inset: 0; z-index: 0; {bg_layer}{blur_css} }}
.hs-scrim {{ position: absolute; inset: 0; background: {scrim}; z-index: 0; }}

/* Stack Slot: centered hero cluster (~prose width) */
.hs-cluster {{
  position: relative; z-index: 1;
  display: flex; flex-direction: column; align-items: center; text-align: center;
  gap: var(--gap); max-width: 52rem;
}}
.hs-eyebrow {{
  font-family: var(--font-eyebrow); font-size: {base_size(eyb) or 0.8125}rem;
  font-weight: {eyb.get('weight', 600)};
  letter-spacing: {eyb.get('letterSpacing', '0.08em')};
  text-transform: uppercase; color: var(--text); opacity: 0.95;
}}
.hs-heading {{
  font-family: var(--font-heading);
  font-weight: {disp.get('weight', 500)};
  font-size: var(--display-size);
  line-height: {disp.get('lineHeight', '1.2')};
  /* sentence case - NO uppercase transform */
  color: var(--text); max-width: 20ch;
}}
.hs-body {{
  font-family: var(--font-body); font-weight: 400;
  font-size: {base_size(bod) or 1.125}rem;
  line-height: 1.5; color: var(--text); opacity: 0.92; max-width: 42rem;
}}

/* Button Group - FILLED primary + outline secondary, ROUNDED with soft shadow */
.hs-actions {{ display: flex; gap: 1rem; flex-wrap: wrap; justify-content: center; margin-top: 0.5rem; }}
.btn {{
  font-family: var(--font-button); font-weight: {ctl.get('weight', 600)};
  font-size: {base_size(ctl) or 0.9375}rem;
  border-radius: var(--radius-button);
  padding: {btn_pad}; text-decoration: none; cursor: pointer;
  display: inline-flex; align-items: center; line-height: 1.5;
  transition: background 200ms, transform 120ms;
}}
.btn-primary {{ background: var(--btn-bg); color: var(--btn-fg); border: none; box-shadow: var(--shadow); }}
.btn-primary:hover {{ background: var(--btn-hover); }}
.btn-secondary {{ background: transparent; color: var(--text); border: {sec_border}; }}

@media (max-width: 767px) {{
  :root {{ --display-size: {disp_mobile or 2.5}rem; }}
}}
"""

    head = _doc_head(doc, layout, layout["id"], proxies, css)
    scaffold = layout.get("scaffold", {}) or {}

    eyebrow_html = (f'    <p class="hs-eyebrow">{html.escape(eyebrow_text)}</p>\n'
                    if eyebrow_text else "")
    body_block = (f'    <p class="hs-body">{html.escape(body_text)}</p>\n'
                  if body_text else "")
    sec_block = (f'      <a class="btn btn-secondary" href="#">{html.escape(s_label)}</a>\n'
                 if s_label else "")

    return head + f"""
<!-- {html.escape(scaffold.get('component',''))} ({scaffold.get('componentId','')}), surface mode On Image: full-bleed photo + flat dark scrim, NO blur -->
<section class="hs-hero">
  <div class="hs-bg" aria-hidden="true"></div>
  <div class="hs-scrim" aria-hidden="true"></div>
  <!-- Stack Slot: centered hero cluster -->
  <div class="hs-cluster">
{eyebrow_html}    <!-- Heading: display tier, sentence case -->
    <h1 class="hs-heading">{html.escape(heading_text)}</h1>
{body_block}    <!-- Button Group: FILLED primary + outline secondary -->
    <div class="hs-actions">
      <a class="btn btn-primary" href="#">{html.escape(p_label)}</a>
{sec_block}    </div>
  </div>
</section>
</body>
</html>
"""


# ── cta-stack (centered heading + buttons on inverse band) ─────────────────────

def build_cta_stack(doc, layout):
    _, surf = resolve_surface(doc, layout)
    text = color_value(doc, surf.get("textPrimary"))
    accent = color_value(doc, surf.get("textAccent")) or "#ff4800"
    accent_text = color_value(doc, "text/on-accent") or "#ffffff"
    bg = surf.get("bg", "#000000")

    disp = type_role(doc, "display-hero")
    heading_stack, p1 = font_stack(doc, "display-hero", "Georgia, serif")
    btn_stack, p2 = font_stack(doc, "control-text", "system-ui, sans-serif")
    proxies = p1 | p2
    rad_btn = spacing_value(doc, "radius-button", "0.5rem")
    pad = spacing_value(doc, "section-padding-default", "5rem")
    shadow = _shadow(doc)
    ds = disp.get("sizeRem", {}) if isinstance(disp.get("sizeRem"), dict) else {}

    heading = find_map(layout, "heading", "title")
    primary = find_map(layout, "primary cta", "primary")
    secondary = find_map(layout, "secondary cta", "secondary")

    css = f""":root {{
  --bg: {bg}; --text: {text}; --accent: {accent}; --accent-text: {accent_text};
  --font-heading: {heading_stack}; --font-button: {btn_stack};
  --display-size: {ds.get('base', 3)}rem; --radius-button: {rad_btn};
  --section-pad: {pad}; --shadow: {shadow};
}}
/* iframe-safe container context: cq* length units resolve against this sized box
   (Studio renders this HTML in an iframe where viewport-relative units misbehave). */
html {{ background: var(--bg); height: 100%; }}
html, body {{ background: var(--bg); color: var(--text); font-family: var(--font-button); }}
body {{ min-height: 100%; container-type: size; container-name: frame; }}
.hs-cta {{ min-height: 70cqh; display:flex; align-items:center; justify-content:center;
  text-align:center; padding: var(--section-pad) 1.5rem; background: var(--bg); }}
.hs-cluster {{ display:flex; flex-direction:column; align-items:center; gap:1.5rem; max-width:48rem; }}
.hs-heading {{ font-family: var(--font-heading); font-weight: {disp.get('weight',500)};
  font-size: var(--display-size); line-height: {disp.get('lineHeight','1.2')}; color: var(--text); }}
.hs-actions {{ display:flex; gap:1rem; flex-wrap:wrap; justify-content:center; }}
.btn {{ font-family: var(--font-button); font-weight:600; border-radius: var(--radius-button);
  padding:0.75rem 1.5rem; text-decoration:none; display:inline-flex; align-items:center; }}
.btn-primary {{ background: var(--accent); color: var(--accent-text); border:none; box-shadow: var(--shadow); }}
.btn-secondary {{ background: transparent; color: var(--text); border:1px solid var(--text); }}
"""
    head = _doc_head(doc, layout, layout["id"], proxies, css)
    p_label = html.escape(prop(primary, "Label", "Get started"))
    s_label = html.escape(prop(secondary, "Label", "Learn more"))
    sec_block = (f'      <a class="btn btn-secondary" href="#">{s_label}</a>\n'
                 if secondary else "")
    return head + f"""
<section class="hs-cta">
  <div class="hs-cluster">
    <h2 class="hs-heading">{html.escape(prop(heading,"Text","Heading"))}</h2>
    <div class="hs-actions">
      <a class="btn btn-primary" href="#">{p_label}</a>
{sec_block}    </div>
  </div>
</section>
</body>
</html>
"""


# ── dispatcher ──────────────────────────────────────────────────────────────────

def build_document(doc, layout, brand_yaml=None):
    kind = layout.get("renderKind")
    if not kind:
        # infer: collage on media-over-media overlap, hero-cta on text-over-image
        # (full-bleed photo hero), else by archetype.
        types = (layout.get("overlapRules", {}) or {}).get("types", []) or []
        if "media-over-media" in types:
            kind = "collage"
        elif "text-over-image" in types or "text-over-photo" in types:
            kind = "hero-cta"
        elif layout.get("archetype") == "stack":
            kind = "cta-stack"
        else:
            kind = "collage"
    if kind == "hero-cta":
        return build_hero_cta(doc, layout, brand_yaml)
    builders = {
        "collage": build_html_collage,
        "cta-stack": build_cta_stack,
    }
    builder = builders.get(kind, build_html_collage)
    return builder(doc, layout)


# ── ADDITIVE (2026-06-16): composed-page section FRAGMENTS for the AD-2 composer ──
#
# compose_page.py selects + orders a brand's own sections for a brief, binds the
# brief copy into each section's typed slots, then renders ONE self-contained page
# by concatenating the fragments below in plan order. These fragments REUSE the
# token resolvers above (color_value/type_role/spacing_value/resolve_surface/...)
# so every value is the brand's real token, and each is a faithful equivalent of
# the section's library components (Section / Stack, Split, Eyebrow, Heading, Rich
# Text, Lead form). Everything is SCOPED to a section wrapper class so the fragments
# compose without colliding. The existing build_* document renderers are UNCHANGED.
#
# WoodWave neverDo are honored structurally: all actions are typographic <a> links
# (no <button>, no filled CTA), radius is 0 everywhere, no box-shadow / `border:`,
# rules are 1px background bars (never border-top/bottom hairlines), the conversion
# field is an unboxed underline element (not a boxed <input>), accent only on dark
# surfaces, and only brand-palette hexes + brand fonts are emitted.


def _esc(s):
    return html.escape(str(s if s is not None else ""))


def brand_fonts(doc):
    """(heading_family, body_family, eyebrow_family, proxies) for the composed page.
    Loads the brand's real families when they are known Google Fonts. Brand-agnostic."""
    heading = type_role(doc, "display-hero").get("family") or "Georgia"
    body = (type_role(doc, "body").get("family")
            or type_role(doc, "control-text").get("family") or "system-ui")
    eyebrow = type_role(doc, "eyebrow").get("family") or body
    proxies = {f for f in (heading, body, eyebrow) if f in _PROXY_GF}
    return heading, body, eyebrow, proxies


def page_tokens_css(doc, hero_layout):
    """Page-level :root brand tokens shared by every composed section (real values
    from brand.yaml). Carries the brand display family/size, body family, accent,
    radius and the hero surface so the page reads on-brand and token-presence holds."""
    _, surf = resolve_surface(doc, hero_layout)
    bg = surf.get("bg")
    text = color_value(doc, surf.get("textPrimary"))
    accent = color_value(doc, surf.get("textAccent")) or text
    disp = type_role(doc, "display-hero")
    heading, body, _eyb, _pr = brand_fonts(doc)
    radius = spacing_value(doc, "radius-global", "0rem")
    return f""":root {{
  --bg: {bg};
  --text: {text};
  --accent: {accent};
  --radius: {radius};
  --display-size: {base_size(disp) or 4}rem;
  --font-heading: '{heading}', Georgia, serif;
  --font-body: '{body}', system-ui, sans-serif;
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
img {{ display: block; max-width: 100%; }}
html {{ background: var(--bg); height: 100%; }}
/* iframe-safe container context for the composed page: every fragment's cq* length
   units resolve against this sized box (Studio renders the page in an iframe where
   viewport-relative units misbehave). */
html, body {{ background: var(--bg); color: var(--text); font-family: var(--font-body);
  -webkit-font-smoothing: antialiased; }}
body {{ min-height: 100%; container-type: size; container-name: frame; }}
"""


def _slash_nav(wordmark, primary_cta):
    """Brand wordmark + slash nav + a single typographic CTA (no buttons)."""
    links = ["About", "Product", "Pricing"]
    nav = ' <span class="cx-sep">/</span> '.join(
        f'<a href="#">{_esc(n)}</a>' for n in links)
    cta = (f'<a class="cx-nav-cta" href="#">{_esc(primary_cta)}</a>'
           if primary_cta else "")
    return f"""  <nav class="cx-nav">
    <span class="cx-logo"><span class="cx-glyph">&#9697;</span> {_esc(wordmark)}</span>
    <span class="cx-navlinks">{nav}</span>
    {cta}
  </nav>"""


# ── fragment 1: opening-bookend hero (inverse, display title over media collage) ──

def build_fragment_hero(doc, layout, b):
    _, surf = resolve_surface(doc, layout)
    bg = surf.get("bg")
    text = color_value(doc, surf.get("textPrimary"))
    accent = color_value(doc, surf.get("textAccent")) or text
    muted = color_value(doc, "text/on-inverse-muted") or text
    disp = type_role(doc, "display-hero")
    eyb = type_role(doc, "eyebrow")
    pad = (doc["tokens"]["spacing"].get("section-padding-dark", {}) or {}).get("value") \
        or spacing_value(doc, "section-padding-light", "6.25rem")
    off = (layout.get("overlapRules", {}) or {}).get("offsets", {}) or {}
    disp_sizes = disp.get("sizeRem", {}) if isinstance(disp.get("sizeRem"), dict) else {}
    media = b.get("media") or []
    hero_img = media[0] if media else ""
    overlap_img = media[1] if len(media) > 1 else (media[0] if media else "")

    css = f""".cx-hero {{ background: {bg}; color: {text};
  padding: 1.75rem 2.5rem {pad}; }}
.cx-nav {{ display:flex; align-items:center; justify-content:space-between; gap:2rem;
  margin-bottom: clamp(2rem,6cqw,4.5rem); }}
.cx-logo {{ display:inline-flex; align-items:center; gap:0.5rem; font-family: var(--font-body);
  font-weight:600; font-size:{base_size(type_role(doc,'control-text')) or 0.875}rem;
  letter-spacing:0.08em; text-transform:uppercase; color:{accent}; }}
.cx-glyph {{ font-family: var(--font-heading); font-size:1.1rem; }}
.cx-navlinks {{ display:flex; gap:0.55rem; flex:1; justify-content:center; }}
.cx-navlinks a, .cx-nav-cta {{ font-family: var(--font-body);
  font-size:{base_size(type_role(doc,'control-text')) or 0.875}rem; letter-spacing:0.08em;
  text-transform:uppercase; text-decoration:none; color:{text}; white-space:nowrap; }}
.cx-navlinks .cx-sep {{ color:{text}; opacity:0.55; }}
.cx-nav-cta {{ color:{accent}; }}
.cx-hero-eyebrow {{ font-family: var(--font-body); font-size:{base_size(eyb) or 0.6875}rem;
  letter-spacing:0.08em; text-transform:uppercase; color:{muted}; text-align:center;
  margin-bottom:1.5rem; }}
.cx-hero-title {{ font-family: var(--font-heading); font-weight:{disp.get('weight',400)};
  font-size: var(--display-size); line-height:{disp.get('lineHeight','1.05em')};
  letter-spacing:{disp.get('letterSpacing','0rem')}; text-transform:uppercase; color:{accent};
  text-align:center; position:relative; z-index:2;
  margin-bottom:{css_len(off.get('titleOverMediaTop'), '-2.75rem')}; }}
.cx-collage {{ position:relative; width:100%; max-width:80rem; margin:0 auto; }}
.cx-media {{ display:block; width:100%; border:none; box-shadow:none;
  border-radius: var(--radius); }}
.cx-media.is-hero {{ aspect-ratio: 1355 / 570; object-fit:cover; }}
.cx-media.is-overlap {{ position:absolute; width:34%; right:4%; bottom:-28%;
  aspect-ratio:785 / 620; object-fit:cover; z-index:1; }}
.cx-hero-spacer {{ height:22cqw; }}
.cx-hero-foot {{ display:flex; flex-direction:column; align-items:center; gap:1.5rem;
  text-align:center; }}
.cx-hero-sub {{ font-family: var(--font-body); font-size:1rem; line-height:1.55em;
  color:{muted}; max-width:42rem; }}
.cx-actions {{ display:flex; gap:1.75rem; flex-wrap:wrap; justify-content:center; }}
.cx-action {{ font-family: var(--font-body);
  font-size:{base_size(type_role(doc,'control-text')) or 0.875}rem; letter-spacing:0.08em;
  text-transform:uppercase; text-decoration:none; color:{text}; }}
.cx-action.is-primary {{ color:{accent}; }}
@media (max-width:991px) {{ .cx-hero {{ --display-size:{disp_sizes.get('tablet',4.5)}rem; }}
  .cx-navlinks {{ display:none; }} }}
@media (max-width:767px) {{ .cx-hero {{ --display-size:{disp_sizes.get('mobile',3)}rem; padding:1.25rem 1.25rem 3rem; }}
  .cx-media.is-overlap {{ width:46%; right:2%; bottom:-18%; }} .cx-hero-spacer {{ height:30cqw; }} }}
"""

    title = _esc(b.get("headline") or "")
    eyebrow = b.get("eyebrow")
    sub = b.get("subhead")
    prim = b.get("primary_cta")
    secd = b.get("secondary_cta")
    eyebrow_html = f'    <p class="cx-hero-eyebrow">{_esc(eyebrow)}</p>\n' if eyebrow else ""
    sub_html = f'      <p class="cx-hero-sub">{_esc(sub)}</p>\n' if sub else ""
    acts = []
    if prim:
        acts.append(f'<a class="cx-action is-primary" href="#">{_esc(prim)} &rarr;</a>')
    if secd:
        acts.append(f'<a class="cx-action" href="#">{_esc(secd)} &rarr;</a>')
    acts_html = (f'      <div class="cx-actions">{"".join(acts)}</div>\n' if acts else "")
    scaffold = layout.get("scaffold", {}) or {}

    htmlf = f"""<!-- {_esc(scaffold.get('component',''))} ({scaffold.get('componentId','')}) - surface mode Inverse: opening-bookend hero -->
<section class="cx-hero">
{_slash_nav(b.get('wordmark',''), prim)}
{eyebrow_html}  <!-- Heading Style:display - display-text-over-media (sanctioned overlap) -->
  <h1 class="cx-hero-title">{title}</h1>
  <!-- media-over-media via absolute offsets (SIGN-OFF #5), Radius:false -->
  <div class="cx-collage">
    <img class="cx-media is-hero" src="{_esc(hero_img)}" alt="WoodWave editorial photography">
    <img class="cx-media is-overlap" src="{_esc(overlap_img)}" alt="WoodWave detail photography">
  </div>
  <div class="cx-hero-spacer"></div>
  <div class="cx-hero-foot">
{sub_html}{acts_html}  </div>
</section>"""
    return {"css": css, "html": htmlf}


# ── fragment 2: editorial-collage value-prop modules (primary, ghost watermark) ──

def build_fragment_editorial(doc, layout, b):
    _, surf = resolve_surface(doc, layout)
    bg = surf.get("bg")
    text = color_value(doc, surf.get("textPrimary"))
    muted = color_value(doc, "text/on-primary-muted") or text
    ghost = color_value(doc, "text/ghost-on-primary") or "rgba(0,0,0,0.06)"
    h3 = type_role(doc, "h3")
    eyb = type_role(doc, "eyebrow")
    pad = spacing_value(doc, "section-padding-light", "6.875rem")
    gap_node = (layout.get("gridRules", {}) or {}).get("gap", {}) or {}
    gap = gap_node.get("value", "7.5rem") if isinstance(gap_node, dict) else "7.5rem"
    ghost_t = type_role(doc, "ghost-watermark")
    ghost_size = base_size(ghost_t) or 12

    css = f""".cx-edit {{ position:relative; overflow:hidden; background:{bg}; color:{text};
  padding:{pad} 2.5rem; }}
.cx-edit-ghost {{ position:absolute; top:6%; left:-2%; z-index:0; pointer-events:none;
  font-family: var(--font-heading); font-weight:400; text-transform:uppercase;
  line-height:1; color:{ghost}; font-size:clamp(6rem,18cqw,{ghost_size}rem); white-space:nowrap; }}
.cx-edit-inner {{ position:relative; z-index:1; max-width:72rem; margin:0 auto;
  display:flex; flex-direction:column; gap:{gap}; }}
.cx-module {{ display:flex; align-items:center; gap:3.5rem; }}
.cx-module.anchor-left {{ flex-direction:row; margin-right:18%; }}
.cx-module.anchor-right {{ flex-direction:row-reverse; margin-left:18%; }}
.cx-module-text {{ flex:0 0 34%; }}
.cx-module-media {{ flex:1; }}
.cx-module-media img {{ width:100%; border:none; box-shadow:none; border-radius: var(--radius);
  aspect-ratio:4 / 3; object-fit:cover; }}
.cx-cap {{ font-family: var(--font-body); font-size:{base_size(eyb) or 0.6875}rem;
  letter-spacing:0.08em; text-transform:uppercase; color:{muted}; margin-bottom:0.75rem; }}
.cx-mtitle {{ font-family: var(--font-heading); font-weight:{h3.get('weight',400)};
  font-size:{base_size(h3) or 1.625}rem; line-height:{h3.get('lineHeight','1.3em')};
  text-transform:uppercase; color:{text}; margin-bottom:1rem; }}
.cx-mbody {{ font-family: var(--font-body); font-size:{base_size(type_role(doc,'body')) or 0.875}rem;
  line-height:1.55em; color:{muted}; }}
@media (max-width:767px) {{ .cx-module, .cx-module.anchor-left, .cx-module.anchor-right {{
  flex-direction:column; margin:0; align-items:flex-start; gap:1.25rem; }}
  .cx-module-text {{ flex:1 1 auto; }} }}
"""

    vps = b.get("value_props") or []
    ghost_word = _esc(b.get("ghost") or (b.get("headline") or "").split(" ")[0])
    media = b.get("media") or []
    modules = []
    for i, vp in enumerate(vps):
        anchor = "anchor-left" if i % 2 == 0 else "anchor-right"
        img = media[i % len(media)] if media else ""
        modules.append(f"""    <div class="cx-module {anchor}">
      <div class="cx-module-text">
        <p class="cx-cap">/ {i + 1:02d}</p>
        <h3 class="cx-mtitle">{_esc(vp.get('title'))}</h3>
        <p class="cx-mbody">{_esc(vp.get('body'))}</p>
      </div>
      <div class="cx-module-media"><img src="{_esc(img)}" alt="{_esc(vp.get('title'))}"></div>
    </div>""")
    modules_html = "\n".join(modules)

    htmlf = f"""<!-- Section / Stack - surface mode base (Primary): editorial-collage value-prop modules -->
<section class="cx-edit">
  <div class="cx-edit-ghost" aria-hidden="true">{ghost_word}</div>
  <div class="cx-edit-inner">
{modules_html}
  </div>
</section>"""
    return {"css": css, "html": htmlf}


# ── fragment 3: info-band split (inverse + cream panel) carrying social proof ──

def build_fragment_band(doc, layout, b):
    _, surf = resolve_surface(doc, layout)
    bg = surf.get("bg")
    panel_bg = color_value(doc, "surface/panel") or "#F7EFE6"
    panel_text = color_value(doc, "text/on-primary") or "#1F1A14"
    panel_muted = color_value(doc, "text/on-primary-muted") or panel_text
    rule = color_value(doc, "border/hairline-on-primary") or "rgba(0,0,0,0.3)"
    h3 = type_role(doc, "h3")
    eyb = type_role(doc, "eyebrow")
    pad = spacing_value(doc, "section-padding-dark", "6.25rem")
    media = b.get("media") or []
    band_img = media[0] if media else ""
    sp = b.get("social_proof") or {}

    css = f""".cx-band {{ display:grid; grid-template-columns:1fr 1fr; background:{bg};
  align-items:stretch; }}
.cx-band-media {{ overflow:hidden; }}
.cx-band-media img {{ width:100%; height:100%; min-height:24rem; object-fit:cover;
  border:none; box-shadow:none; border-radius: var(--radius); }}
.cx-band-panel {{ background:{panel_bg}; color:{panel_text}; padding:{pad} 3rem;
  display:flex; flex-direction:column; justify-content:center; gap:1.5rem; }}
.cx-band-eyebrow {{ font-family: var(--font-body); font-size:{base_size(eyb) or 0.6875}rem;
  letter-spacing:0.08em; text-transform:uppercase; color:{panel_muted}; }}
.cx-band-title {{ font-family: var(--font-heading); font-weight:{h3.get('weight',400)};
  font-size:{base_size(h3) or 1.625}rem; line-height:{h3.get('lineHeight','1.3em')};
  text-transform:uppercase; color:{panel_text}; }}
.cx-band-quote {{ font-family: var(--font-heading); font-weight:400; font-size:1.5rem;
  line-height:1.4em; color:{panel_text}; }}
.cx-band-attr {{ font-family: var(--font-body); font-size:{base_size(eyb) or 0.6875}rem;
  letter-spacing:0.08em; text-transform:uppercase; color:{panel_muted}; }}
.cx-rows {{ display:flex; flex-direction:column; margin-top:0.5rem; }}
.cx-row {{ position:relative; display:flex; align-items:center; justify-content:space-between;
  gap:1rem; padding:1rem 0; }}
.cx-row-rule {{ position:absolute; left:0; right:0; top:0; height:1px; background:{rule}; }}
.cx-row a {{ font-family: var(--font-body);
  font-size:{base_size(type_role(doc,'control-text')) or 0.875}rem; letter-spacing:0.08em;
  text-transform:uppercase; text-decoration:none; color:{panel_text}; }}
@media (max-width:767px) {{ .cx-band {{ grid-template-columns:1fr; }}
  .cx-band-media img {{ min-height:16rem; }} .cx-band-panel {{ padding:3rem 1.5rem; }} }}
"""

    stat = sp.get("stat")
    quote = sp.get("quote")
    attr = sp.get("quote_attr")
    prim = b.get("primary_cta")
    secd = b.get("secondary_cta")
    rows = []
    if prim:
        rows.append(f'      <div class="cx-row"><span class="cx-row-rule"></span>'
                    f'<a href="#">{_esc(prim)}</a><a href="#">&rarr;</a></div>')
    if secd:
        rows.append(f'      <div class="cx-row"><span class="cx-row-rule"></span>'
                    f'<a href="#">{_esc(secd)}</a><a href="#">&rarr;</a></div>')
    rows_html = ("\n".join(rows))
    eyebrow_html = (f'    <p class="cx-band-eyebrow">{_esc(stat)}</p>\n' if stat else "")
    quote_html = (f'    <p class="cx-band-quote">&ldquo;{_esc(quote)}&rdquo;</p>\n' if quote else "")
    attr_html = (f'    <p class="cx-band-attr">{_esc(attr)}</p>\n' if attr else "")
    title_html = (f'    <h3 class="cx-band-title">{_esc(b.get("band_title"))}</h3>\n'
                  if b.get("band_title") else "")

    htmlf = f"""<!-- Section / Split / Content and media - surface mode Inverse: info-band social proof, cream panel child of inverse -->
<section class="cx-band">
  <!-- Image (flush hard-edged photo), Radius:false -->
  <div class="cx-band-media"><img src="{_esc(band_img)}" alt="WoodWave editorial photography"></div>
  <!-- cream panel (surface/panel) nested on inverse: title + quote + ruled action rows -->
  <div class="cx-band-panel">
{eyebrow_html}{title_html}{quote_html}{attr_html}    <div class="cx-rows">
{rows_html}
    </div>
  </div>
</section>"""
    return {"css": css, "html": htmlf}


# ── fragment 4: conversion-stack (primary, centered narrow, underline field) ──

def build_fragment_conversion(doc, layout, b):
    _, surf = resolve_surface(doc, layout)
    bg = surf.get("bg")
    text = color_value(doc, surf.get("textPrimary"))
    muted = color_value(doc, "text/on-primary-muted") or text
    rule = color_value(doc, "border/hairline-on-primary") or "rgba(0,0,0,0.3)"
    h2 = type_role(doc, "h2")
    eyb = type_role(doc, "eyebrow")
    pad = spacing_value(doc, "section-padding-light", "6.875rem")

    css = f""".cx-conv {{ background:{bg}; color:{text}; padding:{pad} 1.5rem;
  display:flex; justify-content:center; }}
.cx-conv-inner {{ width:50%; min-width:320px; max-width:36rem; display:flex; flex-direction:column;
  align-items:center; text-align:center; gap:1.5rem; }}
.cx-conv-eyebrow {{ font-family: var(--font-body); font-size:{base_size(eyb) or 0.6875}rem;
  letter-spacing:0.08em; text-transform:uppercase; color:{muted}; }}
.cx-conv-title {{ font-family: var(--font-heading); font-weight:{h2.get('weight',400)};
  font-size:{base_size(h2) or 2.25}rem; line-height:{h2.get('lineHeight','1.3em')};
  text-transform:uppercase; color:{text}; }}
.cx-field {{ position:relative; width:100%; display:flex; align-items:flex-end;
  justify-content:space-between; gap:1rem; padding-bottom:0.6rem; margin-top:0.5rem; }}
.cx-field-rule {{ position:absolute; left:0; right:0; bottom:0; height:1px; background:{rule}; }}
.cx-input {{ flex:1; font-family: var(--font-body);
  font-size:{base_size(type_role(doc,'body')) or 0.875}rem; color:{muted}; text-align:left;
  outline:none; border:none; background:transparent; min-height:1.4rem; }}
.cx-submit {{ font-family: var(--font-body);
  font-size:{base_size(type_role(doc,'control-text')) or 0.875}rem; letter-spacing:0.08em;
  text-transform:uppercase; text-decoration:none; color:{text}; white-space:nowrap; }}
.cx-conv-sub {{ font-family: var(--font-body); font-size:{base_size(type_role(doc,'control-text')) or 0.875}rem;
  letter-spacing:0.08em; text-transform:uppercase; text-decoration:none; color:{muted}; }}
"""

    eyebrow = b.get("conv_eyebrow") or b.get("eyebrow")
    title = b.get("conv_title") or b.get("headline")
    prim = b.get("primary_cta") or "Submit"
    secd = b.get("secondary_cta")
    placeholder = b.get("field_placeholder") or "you@company.com"
    eyebrow_html = (f'  <p class="cx-conv-eyebrow">{_esc(eyebrow)}</p>\n' if eyebrow else "")
    sub_html = (f'  <a class="cx-conv-sub" href="#">{_esc(secd)} &rarr;</a>\n' if secd else "")

    htmlf = f"""<!-- Section / Stack - surface mode base (Primary): conversion-stack, underline-only field, inline text submit -->
<section class="cx-conv">
  <div class="cx-conv-inner">
{eyebrow_html}    <!-- Eyebrow -> Heading (Tag h2) -->
    <h2 class="cx-conv-title">{_esc(title)}</h2>
    <!-- Form / Webflow / Lead (Style:underline) - unboxed underline field + inline text submit (neverDo:no-boxed-inputs) -->
    <div class="cx-field">
      <span class="cx-field-rule"></span>
      <span class="cx-input" role="textbox" contenteditable="true" aria-label="Email address">{_esc(placeholder)}</span>
      <a class="cx-submit" href="#">{_esc(prim)} &rarr;</a>
    </div>
{sub_html}  </div>
</section>"""
    return {"css": css, "html": htmlf}


def build_section_fragment(doc, layout, bindings, brand_yaml=None):
    """Dispatch a selected layout to its faithful composed-page fragment builder.
    Returns {"css", "html"}. Brand-agnostic: routes on archetype + form presence."""
    arch = (layout.get("archetype") or "").lower()
    lid = (layout.get("id") or "").lower()
    has_form = any("form" in ((m.get("component") or "").lower())
                   for m in layout.get("componentMapping", []))
    if has_form or "conversion" in lid:
        return build_fragment_conversion(doc, layout, bindings)
    if arch == "split" or "band" in lid:
        return build_fragment_band(doc, layout, bindings)
    if arch == "collage" or "collage" in lid or "editorial" in lid:
        return build_fragment_editorial(doc, layout, bindings)
    return build_fragment_hero(doc, layout, bindings)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("brand_yaml", type=Path)
    ap.add_argument("layout_id")
    ap.add_argument("-o", "--out", type=Path, required=True)
    args = ap.parse_args()

    doc = yaml.safe_load(args.brand_yaml.read_text())
    layout = next((l for l in doc["layouts"] if l["id"] == args.layout_id), None)
    if layout is None:
        raise SystemExit(f"layout '{args.layout_id}' not found in {args.brand_yaml}")

    args.out.mkdir(parents=True, exist_ok=True)
    html_doc = build_document(doc, layout, args.brand_yaml)
    (args.out / "index.html").write_text(html_doc)
    print(f"Wrote {args.out / 'index.html'} for layout '{args.layout_id}' "
          f"(renderKind={layout.get('renderKind') or 'inferred'}).")


if __name__ == "__main__":
    main()
