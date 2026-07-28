#!/usr/bin/env python3
"""project_sections_to_patterns.py — every grounded band becomes a harness pattern.

A harness is supposed to be the inventory of what the source pages are BUILT
FROM. When the authoring pass covers only a handful of bands (input caps, a
truncated evidence bundle, a model that summarized instead of enumerating), the
harness silently claims the site has six sections when the capture grounded
twenty-six, and every downstream lane rebuilds a site that is missing most of
its anatomy.

This pass is the census plus the deterministic repair:

  census        every grounded band per page, its role, and whether an authored
                layout/pattern actually claims it (via provenance)
  --author-missing
                project uncovered bands into brand.yaml layouts +
                layout-library.yaml patterns + section-copy.yaml, built from
                that band's OWN grounding (structure, columns, components,
                copy) and its measured asset placements
  --reconcile-copy
                repoint each existing layout's copy at the band its provenance
                names — authoring passes that merge two bands into one layout
                leave a section wearing another section's words

Nothing here invents content: a band contributes only what its grounding and
measured placements already say. Chrome bands (nav/footer) are skipped — they
are contracts, not sections.

Usage:
    ./venv/bin/python tools/extract/project_sections_to_patterns.py \
        --brand-dir runs/<brand>/brand [--author-missing] [--reconcile-copy]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

CHROME_ROLES = {"footer", "nav", "navbar", "header", "chrome"}


def _slug(text: str, limit: int = 60) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", str(text or "").lower()).strip("-")
    s = re.sub(r"-{2,}", "-", s)
    return s[:limit].strip("-")


def _camel(text: str) -> str:
    parts = [p for p in re.split(r"[^a-zA-Z0-9]+", str(text or "")) if p]
    if not parts:
        return "section"
    return parts[0].lower() + "".join(p.capitalize() for p in parts[1:])


def load_bands(brand_dir: Path) -> list[dict]:
    """Every grounded band across every captured page, in page/section order."""
    bands: list[dict] = []
    pages_dir = brand_dir / "evidence" / "pages"
    for page_dir in sorted(p for p in pages_dir.glob("*") if p.is_dir()):
        page = page_dir.name
        for gy in sorted((page_dir / "grounding").glob("*.yaml")):
            try:
                doc = yaml.safe_load(gy.read_text()) or {}
            except Exception as exc:
                print(f"  [warn] unreadable grounding {gy}: {exc}")
                continue
            slug = f"{page}-{gy.stem}"
            m = re.search(r"section-(\d+)", gy.stem)
            bands.append({
                "page": page, "slug": slug, "file": str(gy),
                "index": int(m.group(1)) if m else 999,
                "role": str(doc.get("sectionRole") or "section"),
                "grounding": doc,
            })
    bands.sort(key=lambda b: (b["page"], b["index"]))
    return bands


def coverage(bands: list[dict], doc: dict, lib: dict) -> None:
    """Stamp each band with the layout/pattern that claims it, if any."""
    claims: list[tuple[str, str]] = []
    for node in (doc.get("layouts") or []) + (lib.get("patterns") or []):
        if not isinstance(node, dict):
            continue
        for token in node.get("provenance") or []:
            claims.append((str(token), str(node.get("id"))))
    for band in bands:
        owners = sorted({nid for token, nid in claims
                         if band["slug"] == token or band["slug"].startswith(f"{token}-")})
        band["claimedBy"] = owners


def stamp_source_pages(bands: list[dict], doc: dict, lib: dict) -> bool:
    """Declare which captured PAGES each layout/pattern was extracted from.

    A multi-page brand is a union: without this the single-page lanes have to
    guess a section's page by parsing provenance strings, and a replica of one
    screenshot silently composes another page's sections. Page membership is a
    measured fact, so the artifacts carry it.
    """
    by_slug = {b["slug"]: b for b in bands}
    changed = False
    for node in (doc.get("layouts") or []) + (lib.get("patterns") or []):
        if not isinstance(node, dict):
            continue
        pages = sorted({by_slug[slug]["page"]
                        for token in (node.get("provenance") or [])
                        for slug in by_slug
                        if slug == str(token) or slug.startswith(f"{token}-")})
        if pages and node.get("sourcePages") != pages:
            node["sourcePages"] = pages
            changed = True
    return changed


def placements_for(brand_dir: Path) -> dict[str, list[dict]]:
    path = brand_dir / "evidence" / "asset-placements.json"
    if not path.is_file():
        return {}
    rows: dict[str, list[dict]] = {}
    for p in json.loads(path.read_text()).get("placements") or []:
        if p.get("zone") != "main" or not p.get("sectionSlug"):
            continue
        rows.setdefault(str(p["sectionSlug"]), []).append(p)
    return rows


# ── projection: grounding + placements → a layout/pattern skeleton ───────────────

# measured placement role → (slot name, slot type, slot role). Generic words
# only, so the projection reads the same for any brand.
_MEDIA_SLOTS: dict[str, tuple[str, str, str]] = {
    "proof-strip-mark": ("logoGrid", "logo", "logo-strip"),
    "badge-cluster-mark": ("badgeRow", "logo", "badge-strip"),
    "card-media-well": ("itemMedia", "image", "card-media-well"),
    "section-lead-media": ("media", "media", "section-lead-media"),
    "full-bleed-backdrop": ("backdrop", "media", "full-bleed-backdrop"),
    "inline-spot-icon": ("itemIcon", "image", "inline-spot-icon"),
    "responsive-alternate": ("media", "media", "section-lead-media"),
}


def _media_slots(rows: list[dict], asset_roles: dict[str, str]) -> list[dict]:
    by_slot: dict[str, dict] = {}
    for row in sorted(rows, key=lambda r: ((r.get("position") or {}).get("y", 0),
                                           (r.get("position") or {}).get("x", 0))):
        role = asset_roles.get(str(row.get("asset")))
        spec = _MEDIA_SLOTS.get(str(role))
        if not spec:
            continue
        name, stype, srole = spec
        slot = by_slot.setdefault(name, {"name": name, "role": srole,
                                         "type": stype, "assets": []})
        if row["asset"] not in slot["assets"]:
            slot["assets"].append(str(row["asset"]))
    return list(by_slot.values())


def _fold_card_media(text_slots: list[dict], media_slots: list[dict]) -> list[dict]:
    """Move per-card art ONTO the item-collection slot it decorates.

    A card's picture is part of the card, not a parallel row of pictures. Split
    across two slots the composers draw the copy and the art as separate bands —
    or drop the art entirely — because only a repeatable slot carrying both can
    pair the i-th asset with the i-th item. Returns the media slots that stay
    standalone.
    """
    items = next((s for s in text_slots if s.get("name") == "items"), None)
    if items is None:
        return media_slots
    rest = []
    for slot in media_slots:
        if slot.get("role") != "card-media-well":
            rest.append(slot)
            continue
        items["assets"] = list(slot.get("assets") or [])
        items["role"] = re.sub(r"-item-list$", "-card-list", items["role"])
    return rest


def _text_slots(grounding: dict) -> list[dict]:
    copy = grounding.get("copy") if isinstance(grounding.get("copy"), dict) else {}
    role = str(grounding.get("sectionRole") or "section")
    slots: list[dict] = []
    if copy.get("eyebrow"):
        slots.append({"name": "eyebrow", "role": "section-eyebrow", "type": "content"})
    if copy.get("heading"):
        slots.append({"name": "heading", "role": "section-heading", "type": "content",
                      "textLen": "long" if len(str(copy["heading"])) > 48 else "short"})
    if copy.get("subheading"):
        slots.append({"name": "subheading", "role": "section-subheading",
                      "type": "content"})
    if copy.get("body"):
        slots.append({"name": "body", "role": "section-body", "type": "content"})
    if copy.get("items"):
        slots.append({"name": "items", "role": f"{_slug(role)}-item-list",
                      "type": "content"})
    return slots


def _action_slots(grounding: dict) -> list[dict]:
    variants: list[str] = []
    for comp in grounding.get("components") or []:
        if not isinstance(comp, dict) or str(comp.get("kind")) != "button":
            continue
        v = str(comp.get("variant") or "primary")
        if v not in variants:
            variants.append(v)
    names = ["primaryAction", "secondaryAction", "tertiaryAction"]
    return [{"name": names[i], "role": f"{_slug(v)}-action", "type": "action"}
            for i, v in enumerate(variants[:len(names)])]


def _archetype(grounding: dict, media_slots: list[dict]) -> str:
    """A STRUCTURAL archetype name: column count, card-ness, and whether the band
    actually has media.

    The grounding's prose structure line belongs in `description`, not here —
    composers read anatomy words out of the archetype, so a name that says
    "media-card-right" when no asset was measured makes the composer draw an
    empty placeholder plate. The name claims only what the evidence supports.
    """
    layout = grounding.get("layout") if isinstance(grounding.get("layout"), dict) else {}
    columns = layout.get("columns")
    if isinstance(columns, int) and columns >= 2:
        base = f"{_NUM_WORDS.get(str(columns), str(columns))}-column"
    else:
        base = "single-column"
    has_cards = any(isinstance(c, dict) and str(c.get("kind")) == "card"
                    for c in (grounding.get("components") or []))
    parts = [base]
    if has_cards:
        parts.append("cards")
    if media_slots:
        parts.append("with-media")
    return "-".join(parts)


_NUM_WORDS = {"1": "one", "2": "two", "3": "three", "4": "four", "5": "five",
              "6": "six"}


def _layout_id(role: str, band: dict, taken: set[str]) -> str:
    """A readable, unique layout id: the ROLE, qualified by what makes this band
    different from the others playing the same role.

    Harness ids are read by humans, so the qualifier is the band's own structure
    ("features" + "three column cards"), falling back to the source page and
    finally the band index — never an opaque disambiguation suffix.
    """
    base = _camel(role)
    if base not in taken:
        return base
    layout = band["grounding"].get("layout")
    structure = str((layout or {}).get("structure") or "")
    words = [_NUM_WORDS.get(w, w) for w in re.split(r"[^a-zA-Z0-9]+", structure) if w]
    for n in (3, 4, 2):
        cand = _camel(f"{role} {' '.join(words[:n])}")
        if words and cand not in taken:
            return cand
    for cand in (_camel(f"{role} {band['page']}"),
                 f"{base}{band['index']:02d}"):
        if cand not in taken:
            return cand
    i = 2
    while f"{base}{i}" in taken:
        i += 1
    return f"{base}{i}"


def project_band(band: dict, rows: list[dict], asset_roles: dict[str, str],
                 taken: set[str]) -> tuple[dict, dict, dict]:
    """(layout, pattern, copy) projected from ONE grounded band."""
    g = band["grounding"]
    role = str(g.get("sectionRole") or "section")
    lid = _layout_id(role, band, taken)
    taken.add(lid)

    text = _text_slots(g)
    media = _media_slots(rows, asset_roles)
    media = _fold_card_media(text, media)
    slots = text + media + _action_slots(g)
    layout_block = g.get("layout") if isinstance(g.get("layout"), dict) else {}
    surfaces = g.get("surfaces") if isinstance(g.get("surfaces"), list) else []
    band_surface = next((s for s in surfaces
                         if isinstance(s, dict) and s.get("role") == "band"), None)
    surface_intent = "surface/inverse" if band_surface else "surface/primary"

    described = _archetype(g, media)
    layout = {
        "id": lid,
        "archetype": described,
        # the structural name is EXTRACTION vocabulary, not a renderer key: the ref
        # tells the composers this band binds its whole anatomy in slots, so a
        # media-less band never gets topped up with invented hero photography.
        "archetypeRef": described,
        "useCase": role,
        "patternRef": {"lib": "project", "id": lid},
        "slots": slots,
        # any slot carrying measured art needs the adapter to realize it — including
        # a content-typed card run whose art rides inside the cards.
        "requiresHydration": any(s.get("type") in {"image", "media", "logo", "icon"}
                                 or s.get("assets") for s in slots),
        "surfaceIntent": surface_intent,
        "origin": "extracted",
        "provenance": [band["slug"]],
    }
    pattern = {
        "id": lid,
        "origin": "extracted",
        "useCase": role,
        "archetypeRef": described,
        "surfaceIntent": surface_intent,
        "confidence": str(g.get("confidence") or "medium"),
        "provenance": [band["slug"]],
        "description": str(layout_block.get("structure") or f"{role} band"),
        "layout": {k: v for k, v in layout_block.items() if v is not None},
        "contentShape": {"slots": [dict(s) for s in slots], "assets": []},
    }
    return layout, pattern, band_copy(g)


def band_copy(grounding: dict) -> dict:
    """The band's own words, in the layoutCopy shape."""
    copy = grounding.get("copy") if isinstance(grounding.get("copy"), dict) else {}
    out: dict = {}
    for key in ("eyebrow", "heading", "subheading", "body"):
        if copy.get(key):
            out[key] = copy[key]
    items = copy.get("items")
    if isinstance(items, list) and items:
        rows = [{k: v for k, v in i.items() if v not in (None, "")}
                for i in items if isinstance(i, dict)]
        out["items"] = rows
    return out


def fit_copy_to_slots(payload: dict, layout: dict) -> dict:
    """Normalize a copy block against its layout's slots.

    Item rows keep ONE vocabulary (`heading`/`body`/`meta`) whatever the slot
    calls them — every composer and validator reads that shape, so a per-layout
    rename here would just move the mismatch downstream.
    """
    if not isinstance(payload, dict):
        return payload
    out = dict(payload)
    rows = [dict(i) for i in (out.get("items") or []) if isinstance(i, dict)]
    if not rows:
        out.pop("itemBodiesNotObserved", None)
        return out

    # Body-less rows are real: collapsed accordions and tab strips show only
    # their labels in a static capture. Record that as observation rather than
    # letting it read as copy the extractor dropped.
    bodied = [k for k in ("body", "quote") if any(r.get(k) for r in rows)]
    if not bodied:
        out["itemBodiesNotObserved"] = True
    else:
        out.pop("itemBodiesNotObserved", None)
        for row in rows:
            if not any(row.get(k) for k in bodied):
                row["bodyNotObserved"] = True
    out["items"] = rows
    return out


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--brand-dir", type=Path, required=True)
    ap.add_argument("--author-missing", action="store_true",
                    help="project uncovered bands into the brand artifacts")
    ap.add_argument("--reconcile-copy", action="store_true",
                    help="repoint every layout's copy at the band it claims")
    return ap


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    brand_dir = args.brand_dir
    doc = yaml.safe_load((brand_dir / "brand.yaml").read_text()) or {}
    lib = yaml.safe_load((brand_dir / "layout-library.yaml").read_text()) or {}
    copy_doc = yaml.safe_load((brand_dir / "section-copy.yaml").read_text()) or {}
    registry = yaml.safe_load((brand_dir / "media-assets.yaml").read_text()) or {}
    asset_roles: dict[str, str] = {}
    for a in registry.get("assets") or []:
        for p in (a or {}).get("placements") or []:
            fname = Path(str(a.get("file") or "")).name
            if fname and p.get("role"):
                asset_roles.setdefault(fname, str(p["role"]))

    bands = load_bands(brand_dir)
    coverage(bands, doc, lib)
    rows_by_section = placements_for(brand_dir)

    content = [b for b in bands if b["role"] not in CHROME_ROLES]
    uncovered = [b for b in content if not b["claimedBy"]]
    print(f"census: {len(bands)} grounded bands "
          f"({len(content)} content, {len(bands) - len(content)} chrome) across "
          f"{len({b['page'] for b in bands})} pages")
    for b in bands:
        mark = "chrome" if b["role"] in CHROME_ROLES else (
            ", ".join(b["claimedBy"]) if b["claimedBy"] else "UNCOVERED")
        print(f"  {b['slug'][:56]:58} role={b['role']:14} {mark}")
    print(f"coverage: {len(content) - len(uncovered)}/{len(content)} content bands "
          f"claimed by an authored layout")

    changed = False
    if args.author_missing and uncovered:
        taken = {str(l.get("id")) for l in (doc.get("layouts") or [])}
        taken |= {str(p.get("id")) for p in (lib.get("patterns") or [])}
        layout_copy = copy_doc.setdefault("layoutCopy", {})
        # A band that repeats across pages is ONE pattern with several sources,
        # not several patterns — a harness that lists the same CTA three times
        # is an inventory of pages, not of components.
        seen: dict[tuple, dict] = {}
        for band in uncovered:
            rows = rows_by_section.get(band["slug"], [])
            layout, pattern, bcopy = project_band(band, rows, asset_roles, taken)
            sig = (layout["useCase"],
                   (pattern.get("layout") or {}).get("columns"),
                   tuple(s["name"] for s in layout["slots"]))
            prior = seen.get(sig)
            if prior is not None:
                taken.discard(layout["id"])
                for node in (prior["layout"], prior["pattern"]):
                    node["provenance"].append(band["slug"])
                print(f"  [recur]  {prior['layout']['id']:16} += {band['slug']}")
                continue
            seen[sig] = {"layout": layout, "pattern": pattern}
            doc.setdefault("layouts", []).append(layout)
            lib.setdefault("patterns", []).append(pattern)
            if bcopy:
                layout_copy[layout["id"]] = bcopy
            print(f"  [author] {layout['id']:16} <- {band['slug']} "
                  f"({len(layout['slots'])} slots, {len(rows)} measured assets)")
        changed = True

    if args.reconcile_copy:
        by_slug = {b["slug"]: b for b in bands}
        layout_copy = copy_doc.setdefault("layoutCopy", {})
        for layout in doc.get("layouts") or []:
            tokens = [str(t) for t in (layout.get("provenance") or [])]
            band = next((by_slug[s] for t in tokens for s in by_slug
                         if s == t or s.startswith(f"{t}-")), None)
            if band is None:
                continue
            fresh = band_copy(band["grounding"])
            lid = str(layout.get("id"))
            existing = layout_copy.get(lid)
            if not fresh:
                continue
            # Only a HEADING MISMATCH proves the copy came from a different band.
            # Where the headings agree the authored block is the same section's
            # words, usually refined further than the raw grounding (per-item
            # keys, attribution), so replacing it would be a downgrade.
            if isinstance(existing, dict) and existing.get("heading") and \
                    str(existing["heading"]).strip() == str(fresh.get("heading") or "").strip():
                continue
            if existing == fresh:
                continue
            print(f"  [copy] {lid:16} <- {band['slug']} "
                  f"({'was another band’s words' if existing else 'was unauthored'})")
            layout_copy[lid] = fresh
            changed = True

    if stamp_source_pages(bands, doc, lib):
        changed = True

    if changed:
        layout_copy = copy_doc.setdefault("layoutCopy", {})
        for layout in doc.get("layouts") or []:
            lid = str(layout.get("id"))
            payload = layout_copy.get(lid)
            if isinstance(payload, dict):
                layout_copy[lid] = fit_copy_to_slots(payload, layout)
        # Copy blocks keyed to a layout that no longer exists are dead weight the
        # composers still load; drop them so layoutCopy tracks the inventory.
        layout_ids = {str(l.get("id")) for l in (doc.get("layouts") or [])}
        orphans = [k for k in (copy_doc.get("layoutCopy") or {}) if k not in layout_ids]
        for key in orphans:
            copy_doc["layoutCopy"].pop(key, None)
        if orphans:
            print(f"  [prune] dropped copy for {len(orphans)} layout(s) that no "
                  f"longer exist: {', '.join(sorted(orphans)[:6])}")
        (brand_dir / "brand.yaml").write_text(
            yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=88))
        (brand_dir / "layout-library.yaml").write_text(
            yaml.safe_dump(lib, sort_keys=False, allow_unicode=True, width=88))
        (brand_dir / "section-copy.yaml").write_text(
            yaml.safe_dump(copy_doc, sort_keys=False, allow_unicode=True, width=88))
        print("wrote brand.yaml, layout-library.yaml, section-copy.yaml")
    return 0


if __name__ == "__main__":
    sys.exit(main())
