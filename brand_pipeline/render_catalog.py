#!/usr/bin/env python3
"""render_catalog.py - a Studio CATALOG of a brand's extracted components and
sections, validated as ABSTRACT SLOT CONTRACTS, before any Webflow build.

Driven ENTIRELY by a brand.yaml (canonical design language). It is brand-agnostic:
nothing about WoodWave or HubSpot is hardcoded. Given any brand.yaml that follows
brand-schema.md, it emits:

  catalog/
    index.html     - self-contained, on-brand catalog page (brand tokens for
                     color + type; slot contents are NEUTRAL TYPED PLACEHOLDERS).
    catalog.json    - machine-readable contract.

It surfaces two things a human (or build agent) validates BEFORE binding copy/media:

  (1) COMPONENTS - every unique leaf/library component referenced across the
      layouts' componentMapping (e.g. Heading, Eyebrow, Image, Rich Text,
      Link / Secondary, Form), as a small on-brand gallery.

  (2) SECTIONS - every layout as an abstract SLOT CONTRACT: archetype NAME, its
      MODE / surface (labeled chip + reflected in the rendered surface color),
      the LAYOUT scaffold, and the SLOTS available - each rendered as a TYPED
      PLACEHOLDER by TYPE (content | media) with its use-case caption and the
      component it maps to. The point is to validate slot structure + types +
      surface + layout, INDEPENDENT of content.

Usage:
  python3 render_catalog.py <brand.yaml> -o <outdir>
  # default outdir is <brand.yaml dir>/catalog
"""
from __future__ import annotations

import argparse
import html
import json
from datetime import datetime, timezone
from pathlib import Path

import yaml


# ── token resolvers (copied from render_section.py, kept read-only there) ───────
# Copied intentionally so this script is self-contained and never edits the
# faithful section renderer. These mirror render_section.py's helpers.

def color_value(doc, token):
    """Resolve a color token ref (e.g. 'text/on-inverse') to a hex/rgba string."""
    if not token:
        return None
    c = doc.get("tokens", {}).get("colors", {}).get(token)
    return c["value"] if c else token


def type_role(doc, role):
    return doc.get("tokens", {}).get("type", {}).get(role, {})


def spacing_value(doc, role, default="0rem"):
    s = doc.get("tokens", {}).get("spacing", {}).get(role, {})
    return s.get("value", default)


def base_size(t):
    sz = t.get("sizeRem", {})
    if isinstance(sz, dict):
        return sz.get("base")
    return sz


def resolve_surface(doc, layout):
    """Return (role, surface-dict). Prefers layout.surfaceRole; else matches the
    layout's surfaceMode.mode against tokens.surfaces[*].schemeMode."""
    surfaces = doc.get("tokens", {}).get("surfaces", {})
    if not surfaces:
        return None, {}
    role = layout.get("surfaceRole")
    if role and role in surfaces:
        return role, surfaces[role]
    mode = (layout.get("surfaceMode") or {}).get("mode")
    for r, s in surfaces.items():
        if s.get("schemeMode") == mode:
            return r, s
    first = next(iter(surfaces))
    return first, surfaces[first]


# Non-Google webfonts -> a close Google Fonts proxy that DOES load.
_PROXY_GF = {
    "Source Serif 4": "Source+Serif+4:opsz,wght@8..60,400;8..60,500;8..60,600",
    "Playfair Display": "Playfair+Display:wght@400;500;600",
    "Lexend Deca": "Lexend+Deca:wght@300;400;500;600;700",
    "Inter": "Inter:wght@400;500;600",
}
_SERIF_HINTS = ("serif", "playfair", "didone", "georgia", "times")


def _generic_family(family, proxy):
    base = f"{family} {proxy}".lower()
    return "serif" if any(h in base for h in _SERIF_HINTS) else "sans-serif"


def font_stack(doc, role, fallback="sans-serif"):
    t = type_role(doc, role)
    fam = t.get("family")
    proxy = t.get("renderProxy")
    if not fam:
        return fallback, set()
    generic = _generic_family(fam, proxy or "")
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


# ── slot TYPE inference (small, transparent map) ────────────────────────────────
# A slot's TYPE is `media` or `content`. We look at the mapped component name
# FIRST (most reliable), then the semantic role. Both sources are checked against
# keyword sets. Anything we cannot classify is defaulted to `content` and flagged
# as AMBIGUOUS so a human can review.

MEDIA_KEYWORDS = [
    "image", "media", "photo", "photography", "picture", "logo",
    "wordmark", "avatar", "icon", "video", "gallery", "illustration",
    "graphic", "map", "thumbnail",
]
CONTENT_KEYWORDS = [
    "heading", "title", "eyebrow", "paragraph", "rich text", "richtext",
    "text", "link", "form", "button", "label", "action", "caption", "body",
    "cta", "quote", "stat", "counter", "list", "input", "field", "nav",
]

TYPE_INFERENCE_RULE = (
    "Check the mapped component name first, then the slot's semantic role, "
    "against a media keyword set and a content keyword set. media wins on a "
    "media-keyword hit (Image/Logo/photo/icon/...); otherwise content on a "
    "content-keyword hit (Heading/Eyebrow/Rich Text/Link/Form/...). Unmatched "
    "slots default to 'content' and are flagged ambiguous."
)


def _match(text, keywords):
    t = (text or "").lower()
    return any(k in t for k in keywords)


def infer_slot_type(role, component):
    """Return (type, ambiguous: bool). Component name is the stronger signal."""
    # component name first
    if _match(component, MEDIA_KEYWORDS):
        return "media", False
    if _match(component, CONTENT_KEYWORDS):
        return "content", False
    # then semantic role
    if _match(role, MEDIA_KEYWORDS):
        return "media", False
    if _match(role, CONTENT_KEYWORDS):
        return "content", False
    return "content", True


def derive_group(component_name):
    """Webflow library group = the segment before the first '/'. Leaf primitives
    (no '/') are grouped as 'Primitive'. Brand-agnostic, name-derived only."""
    name = (component_name or "").strip()
    if "/" in name:
        return name.split("/")[0].strip() or "Primitive"
    return "Primitive"


# ── origin catalog (Tier 1 primitives / Tier 2 blocks / Tier 3 scaffolds) ───────
# Surfaces the brand's FULL component vocabulary grouped by TIER, each item tagged
# with where it came from:
#   origin: extracted  → observed on the live page  (carries `provenance` section
#                         ids and any `conflictsWith` neverDo refs)
#   origin: designed    → synthesized brand-consistent from rules+tokens, NOT on the
#                         page (carries the `designedFrom.note` + `overridable: true`)
# Fully data-driven / brand-agnostic: reads whatever a brand.yaml carries and
# degrades gracefully (returns hasOrigin:false) when no `origin` fields are present.

# Tier map → which top-level brand.yaml section holds origin-tagged items.
ORIGIN_TIERS = [
    ("primitives", "Primitives", 1),
    ("blocks", "Blocks", 2),
    ("scaffolds", "Scaffolds", 3),
]


def _as_list(value):
    """Normalize a scalar | list | None into a clean list of strings."""
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(v) for v in value if v is not None and str(v).strip()]
    s = str(value).strip()
    return [s] if s else []


def _origin_item(name, spec):
    """One catalog row from a brand.yaml primitives/blocks/scaffolds entry.

    Returns None for malformed entries. Pulls the key supporting detail per origin:
    extracted → provenance + conflictsWith; designed → designedFrom.note + overridable.
    """
    if not isinstance(spec, dict):
        return None
    origin = spec.get("origin") or ""
    item = {
        "name": name,
        "origin": origin,
        "use": spec.get("use") or "",
        "variant": spec.get("variant") or "",
        "confidence": spec.get("confidence") or "",
        "provenance": [],
        "conflictsWith": [],
        "designedFrom": "",
        "overridable": bool(spec.get("overridable", False)),
    }
    if origin == "extracted":
        item["provenance"] = _as_list(spec.get("provenance"))
        item["conflictsWith"] = _as_list(spec.get("conflictsWith"))
    elif origin == "designed":
        df = spec.get("designedFrom")
        if isinstance(df, dict):
            item["designedFrom"] = df.get("note") or ""
        elif isinstance(df, str):
            item["designedFrom"] = df
    return item


def build_origin_catalog(doc):
    """Walk brand.yaml's primitives/blocks/scaffolds → tier-grouped origin catalog.

    Brand-agnostic + import-safe (used by both this CLI and studio_server.py). Only
    tiers that actually carry `origin` data are included; a brand.yaml with no origin
    fields yields {"hasOrigin": False, "tiers": []} so callers degrade gracefully.
    """
    tiers = []
    has_origin = False
    for key, label, tier_no in ORIGIN_TIERS:
        section = doc.get(key)
        if not isinstance(section, dict) or not section:
            continue
        items = []
        for name, spec in section.items():
            row = _origin_item(name, spec)
            if row is not None:
                items.append(row)
        if not any(it["origin"] for it in items):
            continue  # this tier has no origin tagging → skip (graceful)
        has_origin = True
        extracted = sum(1 for it in items if it["origin"] == "extracted")
        designed = sum(1 for it in items if it["origin"] == "designed")
        # extracted first, then designed, then anything else; alpha within a group.
        rank = {"extracted": 0, "designed": 1}
        items.sort(key=lambda it: (rank.get(it["origin"], 2), it["name"].lower()))
        tiers.append({
            "key": key,
            "label": label,
            "tier": tier_no,
            "extracted": extracted,
            "designed": designed,
            "total": len(items),
            "items": items,
        })
    return {"hasOrigin": has_origin, "tiers": tiers}


# ── catalog model ───────────────────────────────────────────────────────────────

def build_catalog_model(doc):
    """Walk brand.yaml -> the catalog data model (also serialized to catalog.json)."""
    layouts = doc.get("layouts", []) or []

    # (1) unique components across every layout's componentMapping
    components: dict[str, dict] = {}  # key: componentId or name
    ambiguous: list[dict] = []
    sections: list[dict] = []

    for layout in layouts:
        lid = layout.get("id", "section")
        archetype = layout.get("archetype", "")
        scaffold = (layout.get("scaffold") or {}).get("component", "")
        surf_role, surf = resolve_surface(doc, layout)
        mode = (layout.get("surfaceMode") or {}).get("mode") or surf_role or ""
        surf_bg = surf.get("bg", "#ffffff")
        surf_text = color_value(doc, surf.get("textPrimary")) or "#111111"
        surf_accent = color_value(doc, surf.get("textAccent")) if surf.get("textAccent") else None

        # broad structural-slot role map (layout.slots[].name -> role)
        slot_role_map = {
            (s.get("name") or ""): (s.get("role") or "")
            for s in (layout.get("slots") or [])
        }

        # Unified mapping list: prefer componentMapping (WoodWave shape); otherwise
        # derive mapping-like entries from slots[].mappedComponent (HubSpot shape).
        # Brand-agnostic: a layout that has componentMapping is untouched.
        raw_maps = layout.get("componentMapping")
        if raw_maps:
            maps = [dict(m) for m in raw_maps]
        else:
            maps = []
            for s in (layout.get("slots") or []):
                mc = s.get("mappedComponent") or {}
                maps.append({
                    "slot": s.get("name", ""),
                    "role": s.get("useCase") or s.get("name", ""),
                    "component": mc.get("name", ""),
                    "componentId": mc.get("componentId", ""),
                    "props": mc.get("props", {}),
                    "_explicitType": s.get("type"),
                })

        sect_slots = []
        for m in maps:
            role = m.get("role") or ""
            comp = m.get("component") or ""
            comp_id = m.get("componentId") or ""
            structural = m.get("slot") or ""
            explicit = m.get("_explicitType")
            if explicit in ("media", "content"):
                stype, amb = explicit, False
            else:
                stype, amb = infer_slot_type(role, comp)
            broad = slot_role_map.get(structural, "")
            use_case = broad if (broad and broad != role) else role

            sect_slots.append({
                "name": role or structural or "slot",
                "type": stype,
                "useCase": use_case or role,
                "mappedComponent": comp,
                "structuralSlot": structural,
            })

            if amb:
                ambiguous.append({
                    "section": lid, "slot": role or structural,
                    "component": comp, "defaultedTo": stype,
                })

            # accumulate unique component
            key = comp_id or comp
            if not comp:
                continue
            ctype, _ = infer_slot_type("", comp)
            entry = components.setdefault(key, {
                "name": comp,
                "componentId": comp_id,
                "group": derive_group(comp),
                "type": ctype,
                "usedInSlots": [],
            })
            usage = f"{lid} \u2192 {role}" if role else lid
            if usage not in entry["usedInSlots"]:
                entry["usedInSlots"].append(usage)

        sections.append({
            "name": f"{lid} / {archetype.title()}" if archetype else lid,
            "id": lid,
            "layoutArchetype": archetype,
            "scaffold": scaffold,
            "mode": mode,
            "surface": {
                "role": surf_role or "",
                "bg": surf_bg,
                "text": surf_text,
                "accent": surf_accent,
            },
            "slots": sect_slots,
        })

    component_list = sorted(
        components.values(),
        key=lambda c: (0 if c["type"] == "content" else 1, c["name"].lower()),
    )

    return {
        "brand": doc.get("brand", {}).get("name", "Brand"),
        "sourceUrl": doc.get("brand", {}).get("sourceUrl", ""),
        "generated": datetime.now(timezone.utc).isoformat(),
        "typeInference": {
            "rule": TYPE_INFERENCE_RULE,
            "mediaKeywords": MEDIA_KEYWORDS,
            "contentKeywords": CONTENT_KEYWORDS,
        },
        "ambiguousSlots": ambiguous,
        "components": component_list,
        "sections": sections,
        # FULL primitive/block/scaffold vocabulary grouped by tier, each tagged
        # extracted (provenance) vs designed (designedFrom + overridable).
        "originCatalog": build_origin_catalog(doc),
    }


# ── HTML rendering (on-brand chrome, neutral typed placeholders) ────────────────

def _component_specimen(doc, comp):
    """A small on-brand specimen for a component card, by its render archetype."""
    name = comp["name"]
    low = name.lower()
    heading_font, _ = font_stack(doc, "display-hero", "Georgia, serif")
    if not type_role(doc, "display-hero"):
        heading_font, _ = font_stack(doc, "h1", "Georgia, serif")
    body_font, _ = font_stack(doc, "body", "system-ui, sans-serif")
    eyebrow_font, _ = font_stack(doc, "eyebrow", "system-ui, sans-serif")

    if comp["type"] == "media":
        return ('<div class="cat-ph cat-ph-media cat-specimen-media">'
                '<span class="cat-ph-tag">MEDIA</span></div>')
    if "eyebrow" in low or "caption" in low:
        return (f'<div class="cat-specimen-text" style="font-family:{eyebrow_font};'
                'text-transform:uppercase;letter-spacing:0.14em;font-size:0.7rem;'
                'opacity:0.8">Eyebrow label</div>')
    if "heading" in low or "title" in low:
        return (f'<div class="cat-specimen-text" style="font-family:{heading_font};'
                'font-size:1.9rem;line-height:1.05;text-transform:uppercase">Aa</div>')
    if "rich text" in low or "paragraph" in low or low == "text" or "body" in low:
        return (f'<div class="cat-specimen-text" style="font-family:{body_font};'
                'font-size:0.78rem;line-height:1.5;opacity:0.85">'
                '<div class="cat-line" style="width:100%"></div>'
                '<div class="cat-line" style="width:88%"></div>'
                '<div class="cat-line" style="width:64%"></div></div>')
    if "link" in low:
        return (f'<div class="cat-specimen-text" style="font-family:{body_font};'
                'text-transform:uppercase;letter-spacing:0.08em;font-size:0.78rem;'
                'font-weight:600">View more &rarr;</div>')
    if "form" in low or "input" in low:
        return (f'<div class="cat-specimen-form" style="font-family:{body_font}">'
                '<span>Email address</span><span class="cat-submit">Submit &rarr;</span></div>')
    if "button" in low:
        return (f'<div class="cat-specimen-text" style="font-family:{body_font};'
                'text-transform:uppercase;letter-spacing:0.08em;font-size:0.78rem;'
                'font-weight:600">Action &rarr;</div>')
    return ('<div class="cat-ph cat-ph-content cat-specimen-media">'
            '<span class="cat-ph-tag">CONTENT</span></div>')


def _slot_placeholder(slot):
    """A neutral TYPED placeholder block for a slot contract."""
    is_media = slot["type"] == "media"
    klass = "cat-ph-media" if is_media else "cat-ph-content"
    tag = "MEDIA" if is_media else "CONTENT"
    name = html.escape(slot["name"])
    use = html.escape(slot["useCase"] or "")
    comp = html.escape(slot["mappedComponent"] or "")
    struct = html.escape(slot["structuralSlot"] or "")
    return f"""      <figure class="cat-slot">
        <div class="cat-ph {klass}">
          <span class="cat-ph-tag">{tag}</span>
        </div>
        <figcaption class="cat-slot-meta">
          <div class="cat-slot-name">{name} <span class="cat-type cat-type-{slot['type']}">{slot['type']}</span></div>
          <div class="cat-slot-use">{use}</div>
          <div class="cat-slot-comp">&rarr; {comp}{f' <span class="cat-struct">[{struct}]</span>' if struct else ''}</div>
        </figcaption>
      </figure>"""


def _origin_pill(origin):
    if origin == "extracted":
        return '<span class="cat-pill cat-pill-extracted" title="observed on the live page">extracted</span>'
    if origin == "designed":
        return ('<span class="cat-pill cat-pill-designed" '
                'title="synthesized brand-consistent, overridable">designed</span>')
    return f'<span class="cat-pill">{html.escape(origin or "?")}</span>'


def _origin_item_html(it):
    bits = []
    if it["origin"] == "extracted":
        prov = html.escape(", ".join(it["provenance"])) if it["provenance"] else "&mdash;"
        bits.append(f'<div class="cat-origin-detail">from: {prov}</div>')
        if it["conflictsWith"]:
            bits.append('<div class="cat-origin-conflict">&#9888; conflictsWith: '
                        f'{html.escape(", ".join(it["conflictsWith"]))}</div>')
    elif it["origin"] == "designed":
        note = it["designedFrom"] or "synthesized from brand rules + tokens"
        bits.append(f'<div class="cat-origin-detail">{html.escape(note)}</div>')
        if it["overridable"]:
            bits.append('<div class="cat-origin-over">overridable</div>')
    use = f' <span class="cat-origin-use">({html.escape(it["use"])})</span>' if it["use"] else ""
    variant = f' <span class="cat-origin-use">&middot; {html.escape(it["variant"])}</span>' if it["variant"] else ""
    return f"""      <div class="cat-origin-item">
        <div class="cat-origin-top">
          <div class="cat-origin-name">{html.escape(it["name"])}{variant}{use}</div>
          {_origin_pill(it["origin"])}
        </div>
{chr(10).join(bits)}
      </div>"""


def _origin_catalog_html(model):
    """Render the tier-grouped origin catalog section, or '' when absent."""
    oc = model.get("originCatalog") or {}
    tiers = oc.get("tiers") or []
    if not oc.get("hasOrigin") or not tiers:
        return ""
    blocks = []
    for t in tiers:
        items = "\n".join(_origin_item_html(it) for it in t["items"])
        blocks.append(f"""    <div class="cat-origin-tier">
      <div class="cat-origin-tierhead">Tier {t['tier']} &middot; {html.escape(t['label'])}
        <span class="cat-origin-counts">&mdash; {t['extracted']} extracted / {t['designed']} designed</span>
      </div>
      <div class="cat-origin-grid">
{items}
      </div>
    </div>""")
    legend = ('<div class="cat-origin-legend">'
              f'<span class="lg">{_origin_pill("extracted")} observed on the page</span>'
              f'<span class="lg">{_origin_pill("designed")} synthesized brand-consistent &middot; overridable</span>'
              '</div>')
    return f"""  <section>
    <h2 class="cat-h2">Catalog by tier &mdash; origin</h2>
    <p class="cat-lead">The brand's FULL component vocabulary grouped by tier. Each item is tagged
    <b>extracted</b> (observed on the live page, with its provenance section ids and any neverDo
    conflicts) or <b>designed</b> (synthesized brand-consistent from rules + tokens, not on the page,
    and overridable).</p>
    {legend}
{chr(10).join(blocks)}
  </section>

"""


def render_html(doc, model):
    brand = model["brand"]
    # gather font proxies actually used by the page
    proxies: set[str] = set()
    for role in ("display-hero", "h1", "h2", "body", "eyebrow"):
        _, p = font_stack(doc, role)
        proxies |= p
    gf = google_fonts_link(proxies)

    page_surfaces = doc.get("tokens", {}).get("surfaces", {})
    page_bg = "#f6f5f3"
    page_text = "#1c1a17"
    for cand in ("surface/primary", "surface/panel"):
        if cand in page_surfaces:
            page_bg = page_surfaces[cand].get("bg", page_bg)
            page_text = color_value(doc, page_surfaces[cand].get("textPrimary")) or page_text
            break

    heading_font, _ = font_stack(doc, "display-hero", "Georgia, serif")
    if not type_role(doc, "display-hero"):
        heading_font, _ = font_stack(doc, "h1", "Georgia, serif")
    body_font, _ = font_stack(doc, "body", "system-ui, sans-serif")
    radius = spacing_value(doc, "radius-global", "0px")

    # component cards
    comp_cards = []
    for c in model["components"]:
        specimen = _component_specimen(doc, c)
        used = ", ".join(c["usedInSlots"][:4])
        more = f" +{len(c['usedInSlots']) - 4}" if len(c["usedInSlots"]) > 4 else ""
        comp_cards.append(f"""    <article class="cat-comp">
      <div class="cat-comp-preview">{specimen}</div>
      <div class="cat-comp-meta">
        <div class="cat-comp-name">{html.escape(c['name'])}</div>
        <div class="cat-comp-chips">
          <span class="cat-chip">{html.escape(c['group'])}</span>
          <span class="cat-type cat-type-{c['type']}">{c['type']}</span>
        </div>
        <div class="cat-comp-used" title="{html.escape(', '.join(c['usedInSlots']))}">used in: {html.escape(used)}{more}</div>
      </div>
    </article>""")

    # section cards
    sect_cards = []
    for s in model["sections"]:
        surf = s["surface"]
        accent = surf.get("accent") or surf["text"]
        slots_html = "\n".join(_slot_placeholder(sl) for sl in s["slots"])
        sect_cards.append(f"""    <article class="cat-section">
      <header class="cat-section-head">
        <div>
          <div class="cat-section-name">{html.escape(s['name'])}</div>
          <div class="cat-section-sub">{html.escape(s['scaffold'])}</div>
        </div>
        <div class="cat-section-chips">
          <span class="cat-chip cat-chip-mode" style="--swatch:{surf['bg']}">mode: {html.escape(s['mode'])}</span>
          <span class="cat-chip">layout: {html.escape(s['layoutArchetype'] or 'n/a')}</span>
          <span class="cat-chip">{html.escape(surf['role'])}</span>
        </div>
      </header>
      <div class="cat-surface" style="background:{surf['bg']};color:{surf['text']};--accent:{accent}">
        <div class="cat-surface-label">surface {html.escape(surf['role'])} &middot; {html.escape(surf['bg'])}</div>
        <div class="cat-slots">
{slots_html}
        </div>
      </div>
    </article>""")

    # type-inference + ambiguous notes
    amb = model["ambiguousSlots"]
    if amb:
        amb_html = "<ul class='cat-amb-list'>" + "".join(
            f"<li>{html.escape(a['section'])} &middot; <b>{html.escape(a['slot'])}</b> "
            f"({html.escape(a['component'])}) &rarr; defaulted to {a['defaultedTo']}</li>"
            for a in amb) + "</ul>"
    else:
        amb_html = "<p class='cat-note-ok'>No ambiguous slots &mdash; every slot resolved cleanly via component or role keywords.</p>"

    css = f""":root {{
  --page-bg: {page_bg};
  --page-text: {page_text};
  --font-heading: {heading_font};
  --font-body: {body_font};
  --radius: {radius};
  --hair: color-mix(in srgb, var(--page-text) 16%, transparent);
  --hair-strong: color-mix(in srgb, var(--page-text) 30%, transparent);
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
html, body {{ background: var(--page-bg); color: var(--page-text);
  font-family: var(--font-body); -webkit-font-smoothing: antialiased; }}
.cat-wrap {{ max-width: 1180px; margin: 0 auto; padding: 3rem 2rem 5rem; }}
.cat-top {{ border-bottom: 1px solid var(--hair-strong); padding-bottom: 1.5rem; margin-bottom: 2.5rem; }}
.cat-kicker {{ text-transform: uppercase; letter-spacing: 0.18em; font-size: 0.7rem; opacity: 0.6; }}
.cat-title {{ font-family: var(--font-heading); font-size: 2.6rem; line-height: 1.05; margin-top: 0.5rem; }}
.cat-sub {{ margin-top: 0.65rem; font-size: 0.9rem; max-width: 60ch; opacity: 0.8; line-height: 1.5; }}
.cat-counts {{ display: flex; gap: 1.5rem; margin-top: 1.1rem; font-size: 0.8rem; }}
.cat-counts b {{ font-family: var(--font-heading); font-size: 1.4rem; display: block; }}

.cat-h2 {{ font-family: var(--font-heading); font-size: 1.5rem; text-transform: uppercase;
  letter-spacing: 0.02em; margin: 2.8rem 0 1.2rem; }}
.cat-lead {{ font-size: 0.85rem; opacity: 0.7; margin: -0.6rem 0 1.4rem; max-width: 66ch; line-height: 1.5; }}

/* components gallery */
.cat-comps {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 1rem; }}
.cat-comp {{ border: 1px solid var(--hair); background: color-mix(in srgb, var(--page-text) 3%, transparent);
  border-radius: var(--radius); overflow: hidden; display: flex; flex-direction: column; }}
.cat-comp-preview {{ height: 96px; display: grid; place-items: center; padding: 0.75rem;
  border-bottom: 1px solid var(--hair); background: color-mix(in srgb, var(--page-text) 4%, transparent); }}
.cat-comp-meta {{ padding: 0.7rem 0.8rem 0.85rem; }}
.cat-comp-name {{ font-weight: 600; font-size: 0.9rem; }}
.cat-comp-chips {{ display: flex; gap: 0.4rem; margin: 0.45rem 0; flex-wrap: wrap; }}
.cat-comp-used {{ font-size: 0.68rem; opacity: 0.6; line-height: 1.4; }}

.cat-chip {{ font-size: 0.66rem; text-transform: uppercase; letter-spacing: 0.06em;
  padding: 0.18rem 0.5rem; border: 1px solid var(--hair-strong); border-radius: 999px; white-space: nowrap; }}
.cat-chip-mode {{ display: inline-flex; align-items: center; gap: 0.4rem; }}
.cat-chip-mode::before {{ content: ""; width: 0.7rem; height: 0.7rem; border-radius: 50%;
  background: var(--swatch); border: 1px solid var(--hair-strong); display: inline-block; }}
.cat-type {{ font-size: 0.62rem; text-transform: uppercase; letter-spacing: 0.08em; font-weight: 700;
  padding: 0.16rem 0.45rem; border-radius: 999px; }}
.cat-type-content {{ background: #2563eb1f; color: #1d4ed8; }}
.cat-type-media {{ background: #c026631f; color: #be185d; }}

/* origin catalog (extracted vs designed) */
.cat-origin-tier {{ margin-bottom: 1.6rem; }}
.cat-origin-tierhead {{ display: flex; align-items: baseline; gap: 0.5rem; flex-wrap: wrap;
  font-family: var(--font-heading); font-size: 1.05rem; text-transform: uppercase;
  letter-spacing: 0.02em; margin: 0 0 0.7rem; }}
.cat-origin-counts {{ font-family: var(--font-body); font-size: 0.72rem; text-transform: none;
  letter-spacing: 0; opacity: 0.65; }}
.cat-origin-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 0.7rem; }}
.cat-origin-item {{ border: 1px solid var(--hair); border-radius: var(--radius);
  padding: 0.7rem 0.8rem; background: color-mix(in srgb, var(--page-text) 3%, transparent); }}
.cat-origin-top {{ display: flex; align-items: flex-start; justify-content: space-between; gap: 0.5rem; }}
.cat-origin-name {{ font-weight: 600; font-size: 0.86rem; }}
.cat-origin-use {{ font-size: 0.66rem; opacity: 0.55; }}
.cat-origin-detail {{ font-size: 0.68rem; opacity: 0.7; margin-top: 0.35rem; line-height: 1.45; }}
.cat-origin-conflict {{ font-size: 0.66rem; margin-top: 0.25rem; color: #b45309; }}
.cat-origin-over {{ font-size: 0.62rem; text-transform: uppercase; letter-spacing: 0.08em;
  opacity: 0.7; margin-top: 0.25rem; }}
.cat-pill {{ font-size: 0.62rem; text-transform: uppercase; letter-spacing: 0.08em; font-weight: 700;
  padding: 0.16rem 0.5rem; border-radius: 999px; white-space: nowrap; }}
.cat-pill-extracted {{ background: #16a34a26; color: #15803d; border: 1px solid #16a34a55; }}
.cat-pill-designed {{ background: transparent; color: #2563eb; border: 1px dashed #2563eb88; }}
.cat-origin-legend {{ display: flex; gap: 0.8rem; flex-wrap: wrap; align-items: center;
  font-size: 0.72rem; opacity: 0.75; margin: -0.4rem 0 1.2rem; }}
.cat-origin-legend span.lg {{ display: inline-flex; align-items: center; gap: 0.4rem; }}

.cat-specimen-text {{ text-align: center; }}
.cat-specimen-text .cat-line {{ height: 0.42rem; background: currentColor; opacity: 0.28; margin: 0.28rem auto; border-radius: 2px; }}
.cat-specimen-media {{ width: 80%; height: 66px; }}
.cat-specimen-form {{ display: flex; align-items: center; gap: 0.5rem; border-bottom: 1.5px solid currentColor;
  padding-bottom: 0.3rem; font-size: 0.75rem; opacity: 0.85; }}
.cat-specimen-form .cat-submit {{ margin-left: auto; text-transform: uppercase; letter-spacing: 0.08em; font-weight: 600; }}

/* typed placeholders (slots + media/content specimens) */
.cat-ph {{ position: relative; display: grid; place-items: center; border-radius: var(--radius);
  width: 100%; min-height: 70px; }}
.cat-ph-media {{ background:
    repeating-linear-gradient(45deg, color-mix(in srgb, currentColor 12%, transparent) 0 8px,
    transparent 8px 16px); border: 1.5px dashed color-mix(in srgb, currentColor 45%, transparent); }}
.cat-ph-content {{ background: color-mix(in srgb, currentColor 7%, transparent);
  border: 1.5px solid color-mix(in srgb, currentColor 30%, transparent); }}
.cat-ph-tag {{ font-size: 0.62rem; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase;
  opacity: 0.7; }}

/* sections */
.cat-section {{ border: 1px solid var(--hair); border-radius: var(--radius); overflow: hidden; margin-bottom: 1.6rem; }}
.cat-section-head {{ display: flex; align-items: flex-start; justify-content: space-between; gap: 1rem;
  flex-wrap: wrap; padding: 1rem 1.2rem; background: color-mix(in srgb, var(--page-text) 4%, transparent);
  border-bottom: 1px solid var(--hair); }}
.cat-section-name {{ font-family: var(--font-heading); font-size: 1.25rem; text-transform: uppercase; letter-spacing: 0.01em; }}
.cat-section-sub {{ font-size: 0.74rem; opacity: 0.6; margin-top: 0.2rem; }}
.cat-section-chips {{ display: flex; gap: 0.4rem; flex-wrap: wrap; align-items: center; }}
.cat-surface {{ padding: 1.6rem 1.4rem 1.8rem; position: relative; }}
.cat-surface-label {{ position: absolute; top: 0.55rem; right: 0.8rem; font-size: 0.6rem;
  text-transform: uppercase; letter-spacing: 0.1em; opacity: 0.5; font-family: var(--font-body); }}
.cat-slots {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 1rem; margin-top: 0.6rem; }}
.cat-slot {{ margin: 0; }}
.cat-slot .cat-ph {{ min-height: 84px; }}
.cat-slot-meta {{ margin-top: 0.55rem; }}
.cat-slot-name {{ font-weight: 600; font-size: 0.82rem; display: flex; gap: 0.4rem; align-items: center; flex-wrap: wrap; }}
.cat-slot-use {{ font-size: 0.72rem; opacity: 0.75; margin-top: 0.18rem; line-height: 1.4; }}
.cat-slot-comp {{ font-size: 0.68rem; opacity: 0.6; margin-top: 0.22rem; }}
.cat-struct {{ opacity: 0.55; }}

/* inference note */
.cat-note {{ border: 1px solid var(--hair); border-radius: var(--radius); padding: 1.1rem 1.2rem; margin-top: 1rem;
  background: color-mix(in srgb, var(--page-text) 3%, transparent); font-size: 0.8rem; line-height: 1.5; }}
.cat-note code {{ font-family: ui-monospace, Menlo, monospace; font-size: 0.74rem; }}
.cat-kw {{ display: flex; gap: 0.35rem; flex-wrap: wrap; margin-top: 0.5rem; }}
.cat-kw span {{ font-size: 0.64rem; padding: 0.12rem 0.4rem; border: 1px solid var(--hair); border-radius: 4px; opacity: 0.8; }}
.cat-amb-list {{ margin: 0.5rem 0 0 1.1rem; font-size: 0.78rem; }}
.cat-note-ok {{ margin-top: 0.5rem; opacity: 0.8; }}
"""

    n_comp = len(model["components"])
    n_sect = len(model["sections"])
    n_media = sum(1 for c in model["components"] if c["type"] == "media")
    n_content = n_comp - n_media

    media_kw = "".join(f"<span>{html.escape(k)}</span>" for k in MEDIA_KEYWORDS)
    content_kw = "".join(f"<span>{html.escape(k)}</span>" for k in CONTENT_KEYWORDS)

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(brand)} &mdash; Studio Catalog (slot contracts)</title>
{gf}
<style>
{css}
</style>
</head>
<body>
<div class="cat-wrap">
  <header class="cat-top">
    <div class="cat-kicker">Studio Catalog &middot; Slot Contracts</div>
    <h1 class="cat-title">{html.escape(brand)}</h1>
    <p class="cat-sub">Every unique component and section the brand extracted, validated as an
    abstract slot contract &mdash; rendered with the brand's real color &amp; type tokens, but with
    NEUTRAL typed placeholders instead of real copy or photos. Validate structure, types, surface
    and layout before any Webflow build.</p>
    <div class="cat-counts">
      <div><b>{n_comp}</b> components</div>
      <div><b>{n_sect}</b> sections</div>
      <div><b>{n_content}</b> content &middot; <b>{n_media}</b> media</div>
    </div>
  </header>

  <section>
    <h2 class="cat-h2">Components</h2>
    <p class="cat-lead">Unique leaf/library components referenced across all sections' component
    mappings. Each is shown as a small on-brand specimen with its library group and inferred type.</p>
    <div class="cat-comps">
{chr(10).join(comp_cards)}
    </div>
  </section>

{_origin_catalog_html(model)}  <section>
    <h2 class="cat-h2">Sections &mdash; Slot Contracts</h2>
    <p class="cat-lead">Each section is an abstract contract: archetype name, its mode/surface
    (chip + reflected surface color), its layout scaffold, and the typed slots it exposes.
    Slots are neutral CONTENT / MEDIA placeholders &mdash; structure over content.</p>
{chr(10).join(sect_cards)}
  </section>

  <section>
    <h2 class="cat-h2">Slot type inference</h2>
    <div class="cat-note">
      <div>{html.escape(TYPE_INFERENCE_RULE)}</div>
      <div style="margin-top:0.7rem"><code>media</code> keywords:</div>
      <div class="cat-kw">{media_kw}</div>
      <div style="margin-top:0.6rem"><code>content</code> keywords:</div>
      <div class="cat-kw">{content_kw}</div>
      <div style="margin-top:0.8rem"><b>Ambiguous slots</b></div>
      {amb_html}
    </div>
  </section>
</div>
</body>
</html>
"""


# ── cli ─────────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="Render a Studio slot-contract catalog from a brand.yaml")
    ap.add_argument("brand_yaml", type=Path)
    ap.add_argument("-o", "--out", type=Path, default=None,
                    help="output dir (default: <brand.yaml dir>/catalog)")
    args = ap.parse_args()

    doc = yaml.safe_load(args.brand_yaml.read_text())
    if not isinstance(doc, dict) or "layouts" not in doc:
        raise SystemExit(f"{args.brand_yaml} does not look like a brand.yaml (no 'layouts').")

    out = args.out or (args.brand_yaml.parent / "catalog")
    out.mkdir(parents=True, exist_ok=True)

    model = build_catalog_model(doc)
    (out / "catalog.json").write_text(json.dumps(model, indent=2), encoding="utf-8")
    (out / "index.html").write_text(render_html(doc, model), encoding="utf-8")

    print(f"Wrote {out / 'index.html'}")
    print(f"Wrote {out / 'catalog.json'}")
    print(f"  brand={model['brand']!r}  components={len(model['components'])}  "
          f"sections={len(model['sections'])}  ambiguous={len(model['ambiguousSlots'])}")


if __name__ == "__main__":
    main()
