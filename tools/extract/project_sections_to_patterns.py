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

# ── section surface derivation ────────────────────────────────────────────────────
#
# A section's `surfaceIntent` describes the band the SECTION paints from edge to
# edge. It is not a summary of every surface the crop contains: a section that
# holds one dark panel is still a light section with a dark panel in it.
#
# THE RULE (generic, palette-agnostic):
#
#   1. A section's own surface is its GROUND: the outermost surface the grounding
#      records as sitting on the page. Only a page-parented surface can be the
#      ground.
#   2. Any surface whose `parent` names another surface role is NESTED, and
#      therefore component-level — a panel, a card, a media well — however
#      strongly it contrasts with the section around it. A nested surface can
#      never set the section's surface intent; its contrast is carried by that
#      component's own surface variant.
#   3. When more than one surface is page-parented, `canvas` outranks `band`:
#      `canvas` is the role the grounding contract uses for a section's own
#      ground, so a `band` recorded beside a canvas is a full-bleed panel drawn
#      inside the section, not the section itself.
#   4. The section's intent then NAMES the role in the brand's own surface roster
#      whose recorded background is nearest the ground the section measured. The
#      roster is the brand's own measured vocabulary, so this picks a real
#      surface relationship rather than guessing one, and it works for any
#      palette because the only comparison is ground-to-ground within one brand.
#   5. When the roster offers nothing close enough to trust, the ground reads
#      INVERSE if its contrast polarity — the direction between its recorded
#      ground colour and the ink recorded on it — runs opposite to the polarity
#      most of the page's section grounds use, and PRIMARY otherwise. That makes
#      "inverse" mean "against this brand's prevailing ground", which holds for a
#      light-grounded brand and a dark-grounded one alike, with no absolute
#      lightness threshold and no reference to any particular palette.

# ordered by authority as a section ground; anything absent here is nested-only
_GROUND_ROLE_RANK = {"canvas": 0, "band": 1, "chrome-bar": 2, "inset-panel": 3}
_PAGE_PARENTS = {"", "page", "root", "document", "body", "none", "null", "viewport"}
_HEX_RE = re.compile(r"#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})\b")


def _rgb(note: str | None) -> tuple[int, int, int] | None:
    """The first hex triplet in a grounding/token colour note, as RGB."""
    m = _HEX_RE.search(str(note or ""))
    if not m:
        return None
    h = m.group(1)
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _ground_distance(a: str | None, b: str | None) -> float | None:
    """0.0 (identical) → 1.0 (opposite corners of the RGB cube), or None.

    A plain RGB distance is deliberate: the comparison is always between two
    grounds of the SAME brand, so it needs to rank candidates, not model
    perception. No hue, lightness, or palette assumption is baked in.
    """
    ca, cb = _rgb(a), _rgb(b)
    if ca is None or cb is None:
        return None
    return (sum((x - y) ** 2 for x, y in zip(ca, cb)) ** 0.5) / (255 * 3 ** 0.5)


# How near a roster ground must sit to the measured ground to be trusted as THE
# role that section uses, and how much nearer it must be than the authored role
# before a reconcile overwrites a human/model choice. Both are ratios of the RGB
# cube diagonal, so they carry no palette assumption.
GROUND_MATCH_TOLERANCE = 0.06
GROUND_MATCH_MARGIN = 0.10


def surface_roster(doc: dict) -> dict[str, str]:
    """{role: recorded background} for the brand's own measured surface roles.

    Alias roles (``canonicalAliasOf``) are dropped: they name the same measured
    ground as their canonical role, so keeping them would make the nearest-ground
    choice depend on dict order rather than on evidence.
    """
    surfaces = ((doc.get("tokens") or {}).get("surfaces") or {})
    out: dict[str, str] = {}
    for role, spec in surfaces.items():
        if not isinstance(spec, dict) or spec.get("canonicalAliasOf"):
            continue
        bg = spec.get("bg")
        if _rgb(bg) is not None:
            out[str(role)] = str(bg)
    return out


def nearest_surface_role(ground_bg: str | None,
                         roster: dict[str, str]) -> tuple[str | None, float]:
    """The roster role whose recorded ground is nearest ``ground_bg``.

    Ties break on roster order, which is the brand artifact's own ordering, so
    the choice is reproducible rather than dependent on iteration accidents.
    """
    best, best_d = None, 1.0
    for role, bg in roster.items():
        d = _ground_distance(ground_bg, bg)
        if d is not None and d < best_d:
            best, best_d = role, d
    return best, best_d


def _luminance(note: str | None) -> float | None:
    """sRGB relative luminance of the first colour in a grounding colour note.

    Grounding records plain hex, gradients (``gradient(#a -> #b)``) and
    image fills (``image-fill: <description>``). A gradient is read from its
    first stop; an image fill has no resolvable ground colour and returns None
    so callers fall back rather than guess.
    """
    m = _HEX_RE.search(str(note or ""))
    if not m:
        return None
    h = m.group(1)
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    def _lin(v: int) -> float:
        s = v / 255.0
        return s / 12.92 if s <= 0.04045 else ((s + 0.055) / 1.055) ** 2.4
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def _is_page_parented(surface: dict) -> bool:
    return str(surface.get("parent") or "").strip().lower() in _PAGE_PARENTS


def section_ground_surface(surfaces) -> dict | None:
    """The section's OWN surface — see THE RULE above (steps 1-3).

    Returns None when the grounding records no page-parented surface at all, in
    which case the section has no measured ground and callers keep the default.
    """
    if not isinstance(surfaces, list):
        return None
    ranked = [
        (_GROUND_ROLE_RANK[str(s.get("role") or "").strip().lower()], i, s)
        for i, s in enumerate(surfaces)
        if isinstance(s, dict)
        and str(s.get("role") or "").strip().lower() in _GROUND_ROLE_RANK
        and _is_page_parented(s)
    ]
    if not ranked:
        return None
    ranked.sort(key=lambda t: (t[0], t[1]))   # role authority, then reading order
    return ranked[0][2]


def surface_polarity(surface: dict | None, margin: float = 0.12) -> int | None:
    """Contrast DIRECTION of one surface: +1 light-ink-on-dark, -1 dark-ink-on-light.

    None when either colour is unresolvable (an image fill) or the two sit too
    close together to read a direction. Palette-agnostic by construction: it
    reports only which side of its own ground the ink sits on.
    """
    if not isinstance(surface, dict):
        return None
    bg = _luminance(surface.get("bgApprox"))
    ink = _luminance(surface.get("inkApprox"))
    if bg is None or ink is None or abs(ink - bg) < margin:
        return None
    return 1 if ink > bg else -1


def dominant_ground_polarity(bands: list[dict]) -> int | None:
    """The polarity most of this brand's SECTION grounds use — the page's ground.

    Derived from the brand's own evidence rather than assumed, so "inverse"
    means "against this brand's prevailing ground" whichever way that runs.
    Chrome bands are excluded: a page's opening and closing bookends routinely
    invert against the page and would skew the reading of the sections.
    """
    votes = [p for p in (
        surface_polarity(section_ground_surface(
            (b.get("grounding") or {}).get("surfaces")))
        for b in bands if str(b.get("role") or "") not in CHROME_ROLES
    ) if p is not None]
    if not votes:
        return None
    return 1 if sum(1 for v in votes if v > 0) * 2 > len(votes) else -1


# Surface roles that paint the band AGAINST the page's prevailing ground. The
# derivation resolves only this polarity, so a reconcile must leave any other
# authored intent (a muted or panelled ground on the prevailing polarity) alone
# rather than flattening a richer, non-contradicting reading.
INVERTING_INTENTS = {"surface/inverse", "surface/inverse-strong", "surface/accent",
                     "surface/overlay"}


def surface_intent_contradicts(authored: str | None, derived: str,
                               *, measured_bg: str | None = None,
                               roster: dict[str, str] | None = None) -> bool:
    """True when the authored intent disagrees with the section's MEASURED ground.

    Two disagreements count, and only these two, so a reconcile corrects real
    errors without flattening a richer authored reading the evidence does not
    contradict:

      POLARITY — the authored role paints against the brand's prevailing ground
      while the measured ground sits with it, or the reverse.
      GROUND DISTANCE — the derived role's recorded ground sits close to the one
      the section measured while the authored role's sits materially further
      away, meaning the band is painted on the wrong measured surface.
    """
    authored_role = str(authored or "").strip()
    inverts = authored_role in INVERTING_INTENTS
    if inverts != (derived in INVERTING_INTENTS):
        return True
    if not roster or not measured_bg or derived == authored_role:
        return False
    d_derived = _ground_distance(measured_bg, roster.get(derived))
    d_authored = _ground_distance(measured_bg, roster.get(authored_role))
    if d_derived is None or d_authored is None:
        return False
    return (d_derived <= GROUND_MATCH_TOLERANCE
            and d_authored - d_derived >= GROUND_MATCH_MARGIN)


def derive_surface_intent(surfaces, dominant: int | None = None,
                          roster: dict[str, str] | None = None) -> str:
    """The surface role the SECTION'S OWN ground uses — THE RULE, steps 4-5.

    With a brand surface roster, the intent NAMES the role whose recorded ground
    is nearest the ground this section measured. Without one (or with nothing
    close enough to trust) it degrades to the coarse polarity reading: a ground
    painting against the brand's prevailing ground is inverse, otherwise primary.
    """
    ground = section_ground_surface(surfaces)
    if ground is None:
        return "surface/primary"
    if roster:
        role, dist = nearest_surface_role(ground.get("bgApprox"), roster)
        if role and dist <= GROUND_MATCH_TOLERANCE:
            return role
    polarity = surface_polarity(ground)
    if polarity is None:
        role = str(ground.get("role") or "").strip().lower()
        return "surface/inverse" if role == "band" else "surface/primary"
    reference = dominant if dominant in (1, -1) else -1
    return "surface/inverse" if polarity != reference else "surface/primary"


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
                 taken: set[str], *,
                 ground_polarity: int | None = None,
                 roster: dict[str, str] | None = None) -> tuple[dict, dict, dict]:
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
    surface_intent = derive_surface_intent(surfaces, ground_polarity, roster)

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
    ap.add_argument("--reconcile-surfaces", action="store_true",
                    help="re-derive every extracted layout/pattern's surfaceIntent "
                         "from the band its provenance names (section ground, not "
                         "nested component surfaces)")
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

    ground_polarity = dominant_ground_polarity(bands)
    roster = surface_roster(doc)
    print(f"section grounds: prevailing contrast polarity "
          f"{'light-ink-on-dark' if ground_polarity == 1 else 'dark-ink-on-light'} "
          f"— a section inverts only against this; "
          f"{len(roster)} measured surface role(s) available to match grounds against")

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
            layout, pattern, bcopy = project_band(
                band, rows, asset_roles, taken,
                ground_polarity=ground_polarity, roster=roster)
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

    if args.reconcile_surfaces:
        by_slug = {b["slug"]: b for b in bands}
        for node in (doc.get("layouts") or []) + (lib.get("patterns") or []):
            if not isinstance(node, dict) or node.get("origin") != "extracted":
                continue
            tokens = [str(t) for t in (node.get("provenance") or [])]
            band = next((by_slug[s] for t in tokens for s in by_slug
                         if s == t or s.startswith(f"{t}-")), None)
            if band is None:
                continue
            surfaces = (band["grounding"] or {}).get("surfaces")
            fresh = derive_surface_intent(surfaces, ground_polarity, roster)
            ground = section_ground_surface(surfaces)
            if not surface_intent_contradicts(
                    node.get("surfaceIntent"), fresh,
                    measured_bg=(ground or {}).get("bgApprox"), roster=roster):
                continue
            print(f"  [surface] {str(node.get('id')):16} "
                  f"{node.get('surfaceIntent')} -> {fresh} "
                  f"(ground role={str((ground or {}).get('role'))}, "
                  f"parent={str((ground or {}).get('parent'))})")
            node["surfaceIntent"] = fresh
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
