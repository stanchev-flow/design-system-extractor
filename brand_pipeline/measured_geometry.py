#!/usr/bin/env python3
"""measured_geometry.py — deterministic per-component geometry enrichment.

The staged author (and its deterministic projection) name a pattern's slots and
roles but historically shipped many slots as *name/role only* — no measured band
padding, box-to-box rhythm, per-card register/width/gap, grid equalization, or
container-relative media scale. The v2 quality bar reached fidelity only because
those facts were hand-measured into ``layout-library.yaml`` over many correction
passes. This module makes that step REPRODUCIBLE and evidence-grounded: given a
lane's own fresh evidence (the per-section vision grounding YAMLs, the measured
``section-rects.json`` band census, and the CSS section-padding tokens), it fills
the measured geometry facts the composer already consumes
(``bandPadding`` / ``bandRhythm`` / ``deviceGeometry`` / ``gridEqualize`` /
``mediaScale`` / ``stackMeasure`` / ``actionGroup``) onto every extracted pattern
that is missing them.

Design rules (why this is safe to run on any lane):

* FILL-ABSENT-ONLY. A pattern that already carries a measured fact (the v2/remote
  baselines, hand-authored) is never overwritten — those lanes are byte-identical
  after enrichment. Only patterns missing a fact gain one, and only when the lane's
  own evidence supplies it.
* EVIDENCE-DERIVED, NOT SECTION-NAMED. Every value is computed from the pattern's
  own grounding / rect / token evidence (generic surface/register/rhythm rules),
  never from a hard-coded per-section constant or a section-specific token name.
* PAGE-QUALIFIED. A pattern is measured from the band its own ``provenance[]`` /
  ``sourcePages[]`` name, so a multi-page lane never reads one page's geometry onto
  another page's pattern. An ambiguous provenance token fills nothing.
* EXACTLY-NAMED. Hand-authored patterns carry a semantic role label in
  ``provenance[]`` rather than a band slug, and declare the band itself in their
  authoring notes instead; both channels resolve through the same exact match and
  refuse an ambiguous token. There is no nearest-slug fallback anywhere.
* DEGRADE QUIETLY. Missing/…malformed evidence for a field simply leaves that field
  absent (the composer's structural default is the honest degrade).

The enrichment is invoked by the patterns-recipes author stage (and can be run
standalone for a re-author). It returns a per-pattern diff summary for telemetry.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml
except Exception:  # pragma: no cover
    yaml = None
import json


# ── px → CSS length helpers ──────────────────────────────────────────────────────

def _rem(px: float, base: float = 16.0) -> str:
    """A pixel measure as a tidy rem string (the composer accepts rem/px/em)."""
    val = round(px / base, 4)
    # trim trailing zeros: 2.5rem not 2.5000rem, 5rem not 5.0rem
    txt = ("%f" % val).rstrip("0").rstrip(".")
    return f"{txt}rem"


def _num(v: Any) -> float | None:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f == f else None  # drop NaN


# ── section-heading register from a measured type size ───────────────────────────
# Generic type-tier mapping (no section names): the size a heading measured on maps
# to the brand's own role tier the composer draws. Reusable across any palette/site.
def register_for_size(px: float | None) -> str | None:
    if px is None:
        return None
    if px >= 64:
        return "display"
    if px >= 44:
        return "h1"
    if px >= 34:
        return "h2"
    if px >= 24:
        return "h3"
    if px >= 19:
        return "h4"
    return "h5"


# ── evidence loaders ──────────────────────────────────────────────────────────────
#
# BAND IDENTITY IS PAGE-QUALIFIED. A lane may capture several pages, and two pages
# routinely both have a ``section-01``. The rest of the pipeline already settled this:
# ``tools/extract/project_sections_to_patterns.load_bands`` names a band
# ``<page>-<grounding file stem>`` and stamps that same string into a pattern's
# ``provenance[]`` (plus the page set into ``sourcePages[]``). This module reads the
# evidence through that one convention instead of a bare section NUMBER, because a
# number-keyed index silently attributes one page's measured geometry to another
# page's pattern — a worse failure than filling nothing.

@dataclass(frozen=True)
class GroundedBand:
    """One grounded source band: its page-qualified slug, page, section index, doc."""
    slug: str
    page: str            # "" for a single-page lane (no evidence/pages/ tree)
    index: int | None    # the section ordinal WITHIN its page
    doc: dict


def _section_index(text: str) -> int | None:
    m = re.search(r"section-(\d+)", str(text))
    return int(m.group(1)) if m else None


def _page_names(brand_dir: Path) -> list[str]:
    """The captured page keys, longest first so a page name that prefixes another
    ("talent" vs "talent-sourcing") never claims the longer one's bands."""
    pdir = brand_dir / "evidence" / "pages"
    if not pdir.is_dir():
        return []
    return sorted((p.name for p in pdir.iterdir() if p.is_dir()),
                  key=len, reverse=True)


def _read_yaml(path: Path) -> dict | None:
    try:
        doc = yaml.safe_load(path.read_text())
    except Exception:
        return None
    return doc if isinstance(doc, dict) else {}


def _load_grounding(brand_dir: Path) -> dict[str, GroundedBand]:
    """{page-qualified band slug: :class:`GroundedBand`} for every grounded band.

    Reads BOTH evidence shapes a lane can ship:

    * ``evidence/pages/<page>/grounding/*.yaml`` — the per-page capture (complete),
      slug ``<page>-<stem>``, page known from the directory.
    * ``evidence/grounding/*.yaml`` — the lane-canonical bundle. On a single-page
      lane the stem IS the slug and the page is unknown (""); on a multi-page lane
      the merge already prefixes the page, so the stem is the same slug the per-page
      tree produced and the page is recovered from that prefix.

    Overlapping slugs are the same band written twice, so the per-page tree (the
    authoritative, unabridged capture) wins.
    """
    out: dict[str, GroundedBand] = {}
    brand_dir = Path(brand_dir)
    if yaml is None:
        return out
    pages = _page_names(brand_dir)
    for page in pages:
        gdir = brand_dir / "evidence" / "pages" / page / "grounding"
        if not gdir.is_dir():
            continue
        for f in sorted(gdir.glob("*.yaml")):
            doc = _read_yaml(f)
            if doc is None:
                continue
            slug = f"{page}-{f.stem}"
            out[slug] = GroundedBand(slug, page, _section_index(f.stem), doc)
    gdir = brand_dir / "evidence" / "grounding"
    if gdir.is_dir():
        for f in sorted(gdir.glob("*.yaml")):
            if f.stem in out:
                continue
            doc = _read_yaml(f)
            if doc is None:
                continue
            page = next((p for p in pages if f.stem.startswith(f"{p}-")), "")
            index = _section_index(f.stem[len(page) + 1:] if page else f.stem)
            out[f.stem] = GroundedBand(f.stem, page, index, doc)
    return out


def _load_section_rects(brand_dir: Path) -> dict[str, dict[int, dict]]:
    """{page: {section index: rect doc}} from the measured band censuses.

    The "" page holds the lane-canonical ``evidence/section-rects.json``. On a
    multi-page lane that file is ONE page's census promoted to canonical, so a band
    that knows its page must read its own page's file and never fall back to the
    canonical one — the fallback is exactly the cross-page mis-attribution this
    index exists to prevent.
    """
    brand_dir = Path(brand_dir)
    out: dict[str, dict[int, dict]] = {}

    def _read(path: Path) -> dict[int, dict]:
        rows: dict[int, dict] = {}
        try:
            data = json.loads(path.read_text())
        except Exception:
            return rows
        for s in data.get("sections") or []:
            if isinstance(s, dict) and "index" in s:
                try:
                    rows[int(s["index"])] = s
                except (TypeError, ValueError):
                    continue
        return rows

    canonical = brand_dir / "evidence" / "section-rects.json"
    if canonical.is_file():
        out[""] = _read(canonical)
    for page in _page_names(brand_dir):
        p = brand_dir / "evidence" / "pages" / page / "section-rects.json"
        if p.is_file():
            out[page] = _read(p)
    return out


# A band token as the pipeline writes it: the ordinal-qualified section name that
# ``load_bands`` builds slugs from and the projector stamps into ``provenance[]``.
_BAND_TOKEN = re.compile(r"\bsection-\d+\b")


def declared_band_tokens(pattern: dict) -> list[str]:
    """The band a HAND-AUTHORED pattern names in its own authoring notes, or [].

    A projector-authored pattern puts the band slug straight into ``provenance[]``. A
    hand-authored one puts a semantic ROLE label there instead — a name for what the
    band does ("hero", a logo wall, a closing call to action), not an identifier for
    which band it was. Those labels are not band keys and cannot become them: they
    match no slug, and the role vocabulary the grounding itself declares repeats across
    many bands, so resolving through role names would be ambiguous by construction.

    What such a pattern DOES declare is the band, in its changelog notes, using the
    same ordinal token the projector uses. That is an explicit author-written
    reference, so it serves as a second provenance channel. Notes that name more than
    one band are REFUSED rather than ordered into a guess: unlike ``provenance[]``,
    whose order means "first source", a note mentioning two bands carries no such
    contract, and picking one would attribute a band's geometry to a pattern that was
    not extracted from it.
    """
    tokens: set[str] = set()
    for entry in (pattern.get("changelog") or []):
        if isinstance(entry, dict):
            tokens.update(_BAND_TOKEN.findall(str(entry.get("note") or "")))
    return sorted(tokens) if len(tokens) == 1 else []


def _band_for_token(token: str, bands: dict[str, GroundedBand],
                    pages: set[str]) -> GroundedBand | None:
    """The single band a token names, or None when it names none or several.

    Matching follows ``project_sections_to_patterns.coverage``: a token names a band
    when it equals the band slug or is a slug prefix ending at a segment boundary.
    Matching is exact — there is no nearest-slug fallback, because a near miss would
    silently attribute one band's measured geometry to another, which is worse than
    resolving nothing at all.
    """
    hits = [b for b in bands.values()
            if b.slug == token or b.slug.startswith(f"{token}-")]
    if not hits and pages:
        # A bare token on a page-qualified lane: re-read it against the pages
        # the pattern already declares, rather than against every page.
        hits = [b for b in bands.values()
                for pg in pages
                if b.slug == f"{pg}-{token}"
                or b.slug.startswith(f"{pg}-{token}-")]
    if pages and len(hits) > 1:
        hits = [b for b in hits if b.page in pages] or hits
    return hits[0] if len(hits) == 1 else None


def resolve_pattern_band(pattern: dict,
                         bands: dict[str, GroundedBand]) -> GroundedBand | None:
    """The grounded band a pattern was extracted from, or None.

    ``provenance[]`` is read first, in order, so a pattern recurring across pages is
    measured from its FIRST source. A pattern whose provenance names no band falls
    back to the band its authoring notes declare (see :func:`declared_band_tokens`),
    which is how the hand-authored lanes name their source. Every channel resolves
    through the same exact matching and refuses an ambiguous token rather than
    guessing, so a pattern either gets the geometry of the band it came from or gets
    none.
    """
    pages = {str(p) for p in (pattern.get("sourcePages") or []) if p}
    for token in [str(t) for t in (pattern.get("provenance") or [])] \
            + declared_band_tokens(pattern):
        band = _band_for_token(token, bands, pages)
        if band is not None:
            return band
    return None


def _identity(text: str) -> str:
    """A band label reduced to the identity its artifact names it by.

    A band's crop is named ``section-<ordinal>-<slug of the band's own class list>``
    and the grounding YAML inherits that name, while the rect census records the same
    class list per row. This is therefore the one token that identifies a band in BOTH
    artifacts — but the two names are truncated at different lengths, so identities
    are compared with :func:`_same_band` rather than for equality.
    """
    return re.sub(r"[^a-z0-9]+", "-", str(text or "").lower()).strip("-")


def _same_band(a: str, b: str) -> bool:
    """Whether two band identities name the same band despite name truncation.

    Truncation only ever shortens, so the shorter identity must be a prefix of the
    longer one. This is not a similarity test: a differing character anywhere in the
    shared span is a different band, and callers additionally require the match to be
    unique before they use it.
    """
    return bool(a) and bool(b) and (a.startswith(b) or b.startswith(a))


def _band_identity(band: GroundedBand) -> str:
    """A band's identity as its own slug spells it (page prefix and ordinal removed)."""
    stem = band.slug[len(band.page) + 1:] if band.page else band.slug
    return _identity(re.sub(r"^section-\d+-?", "", stem))


def _rect_for_band(rects: dict[str, dict[int, dict]],
                   band: GroundedBand) -> dict:
    """The measured rect for a band, read from ITS OWN page's census.

    The band's ordinal is NOT trusted as a census index. A band's ordinal counts the
    chrome bands that were cropped with it (a page header is not one of the census's
    content sections), so on a lane whose header became its own crop every ordinal is
    shifted by one against the census, which measured each band against its neighbour.
    The indexed row is therefore accepted only when its own identity agrees with the
    band's, and otherwise the band is looked up BY identity. A band whose identity
    names no single row measures nothing: a neighbouring band's rect is a wrong
    answer, not a near one.
    """
    if band.index is None:
        return {}
    page_rects = rects.get(band.page, {})
    wanted = _band_identity(band)

    def _row_identity(row: dict) -> str:
        return _identity(row.get("classes") or row.get("tag") or "section")

    indexed = page_rects.get(band.index, {})
    if indexed and _same_band(_row_identity(indexed), wanted):
        return indexed
    named = [row for row in page_rects.values()
             if _same_band(_row_identity(row), wanted)]
    return named[0] if len(named) == 1 else {}


# ── the per-field derivations ──────────────────────────────────────────────────────

def _display_size(grounding: dict) -> float | None:
    """The measured size of the section's dominant heading (display > h1/h2 tiers).
    Reads the grounding typography census generically."""
    best = None
    for t in grounding.get("typography") or []:
        if not isinstance(t, dict):
            continue
        role = str(t.get("role") or "").lower()
        if role in ("display", "h1", "h2", "heading", "title"):
            sz = _num(t.get("approxSizePx"))
            if sz is not None and (best is None or sz > best):
                best = sz
    return best


def _card_heading_size(grounding: dict) -> float | None:
    for t in grounding.get("typography") or []:
        if isinstance(t, dict) and str(t.get("role") or "").lower() in ("h3", "h4"):
            return _num(t.get("approxSizePx"))
    return None


def _component(grounding: dict, kind: str) -> dict | None:
    for c in grounding.get("components") or []:
        if isinstance(c, dict) and str(c.get("kind") or "").lower() == kind:
            return c
    return None


def _has_card_grid(pattern: dict) -> bool:
    for s in ((pattern.get("contentShape") or {}).get("slots") or []):
        if isinstance(s, dict) and str(s.get("role") or "") in ("card-grid",):
            return True
    return bool(pattern.get("cardAnatomy")) and any(
        str(s.get("role") or "") == "card-grid"
        for s in ((pattern.get("contentShape") or {}).get("slots") or [])
        if isinstance(s, dict))


def _slot(pattern: dict, name: str) -> dict | None:
    for s in ((pattern.get("contentShape") or {}).get("slots") or []):
        if isinstance(s, dict) and s.get("name") == name:
            return s
    return None


# ── enrich one pattern ──────────────────────────────────────────────────────────────

# The measured-geometry facts this module can fill. The default set is the full
# vocabulary; a caller (or A/B calibration) can restrict it. Every fact is
# fill-absent-only regardless of the selection.
ALL_FIELDS = frozenset({
    "bandPadding", "bandRhythm", "headingRegister", "cardRegister",
    "columnGap", "cardActionGap", "gridEqualize", "mediaScale",
    "heroMediaAspect",
})

# The calibrated set APPLIED to a lane's shipped library. Every fact here is measured
# AND verified to improve or hold the replica-gate fidelity (the rebuild-as-proof
# score). ``headingRegister`` / ``cardRegister`` / ``cardActionGap`` / ``gridEqualize``
# are deliberately EXCLUDED from the shipped set: the enricher can still extract them
# (they belong to ``ALL_FIELDS`` and the extraction is proven by test), but the current
# composer OVER-RESPONDS to them (over-sized card headings, stretch-taller grids), so
# authoring them today lowers rebuild fidelity — a NAMED residual renderer gap, not a
# data gap. They move into ``FIDELITY_FIELDS`` once the composer's card-register /
# grid-equalize response is calibrated to the measured source proportions.
FIDELITY_FIELDS = frozenset({
    "bandPadding", "bandRhythm", "columnGap", "mediaScale", "heroMediaAspect",
})


def enrich_pattern(pattern: dict, grounding: dict, rect: dict,
                   fields: frozenset[str] = ALL_FIELDS) -> list[str]:
    """Fill absent measured geometry on ONE pattern from its own evidence. Returns a
    list of the fact keys added (for telemetry). Mutates ``pattern`` in place.

    ``fields`` restricts which measured facts may be filled (default: all)."""
    added: list[str] = []
    cs = pattern.setdefault("contentShape", {})
    if not isinstance(cs, dict):
        return added
    layout = grounding.get("layout") or {}

    # 1) MEASURED BAND PADDING — the band's own top/bottom breathing room. The
    #    grounding's measured pad (px) is authoritative for the band register.
    pad = layout.get("approxPaddingPx") if isinstance(layout.get("approxPaddingPx"), dict) else {}
    top, bot = _num(pad.get("top")), _num(pad.get("bottom"))
    if "bandPadding" in fields and "bandPadding" not in cs and (top is not None or bot is not None):
        bp: dict[str, str] = {}
        if top is not None:
            bp["top"] = _rem(top)
        if bot is not None:
            bp["bottom"] = _rem(bot)
        if bp:
            cs["bandPadding"] = bp
            added.append("bandPadding")

    # 2) MEASURED BAND RHYTHM — deterministic box-to-box seams the source shows.
    rs = grounding.get("relationalSpacingPx") if isinstance(grounding.get("relationalSpacingPx"), dict) else {}
    if "bandRhythm" in fields and "bandRhythm" not in cs and rs:
        rung: dict[str, str] = {}
        for k in ("eyebrowToHeading", "headingToBody", "bodyToCta"):
            v = _num(rs.get(k))
            if v is not None:
                rung[k] = _rem(v)
        if rung:
            cs["bandRhythm"] = rung
            added.append("bandRhythm")

    # 3) MEASURED DEVICE GEOMETRY — heading/card registers, column gap, in-card seam.
    geo = cs.setdefault("deviceGeometry", {}) if isinstance(cs.get("deviceGeometry"), dict) or "deviceGeometry" not in cs else cs["deviceGeometry"]
    if isinstance(geo, dict):
        if "headingRegister" in fields and "headingRegister" not in geo:
            reg = register_for_size(_display_size(grounding))
            if reg:
                geo["headingRegister"] = reg
                added.append("deviceGeometry.headingRegister")
        # feature-card sections whose cards ride their own register
        if "cardRegister" in fields and "cardRegister" not in geo and _has_card_grid(pattern):
            creg = register_for_size(_card_heading_size(grounding))
            if creg:
                geo["cardRegister"] = creg
                added.append("deviceGeometry.cardRegister")
        # measured column gap for multi-column bands
        if "columnGap" in fields and "columnGap" not in geo:
            gp = _num(layout.get("gapPx"))
            cols = _num(layout.get("columns"))
            if gp is not None and cols is not None and cols >= 2 and gp <= 96:
                geo["columnGap"] = _rem(gp)
                added.append("deviceGeometry.columnGap")
        # measured in-card action seam: a card grid's body→link seam. The card's own
        # register is tighter than the section body-to-cta rung; use the card box's
        # measured inner padding as the seam evidence when present.
        if "cardActionGap" in fields and "cardActionGap" not in geo and _has_card_grid(pattern):
            card = _component(grounding, "card") or {}
            szpad = str((card.get("sizing") or {}).get("approxPaddingPx") or "")
            mm = re.findall(r"\d+", szpad)
            if mm:
                # the card's vertical padding doubles as the measured top/bottom seam
                geo["cardActionGap"] = _rem(float(mm[0]))
                added.append("deviceGeometry.cardActionGap")
        if not geo:
            cs.pop("deviceGeometry", None)

    # 4) GRID EQUALIZE — a multi-card grid whose cards stretch to equal heights and
    #    pin their trailing action (the measured product-card morphology).
    if "gridEqualize" in fields and "gridEqualize" not in cs and _has_card_grid(pattern):
        card = _component(grounding, "card") or {}
        if str((card.get("sizing") or {}).get("widthBehavior") or "").lower() == "stretch" \
                and _num(card.get("countObserved")) and _num(card.get("countObserved")) > 1:
            link = _component(grounding, "link") or {}
            pinned = "arrow" in str(link.get("variant") or "").lower() \
                or "arrow" in str(link.get("anatomy") or "").lower()
            cs["gridEqualize"] = {"heights": "stretch", "slack": "body",
                                  "actionPinned": bool(pinned)}
            added.append("gridEqualize")

    # 5) MEASURED MEDIA SCALE — a split band's media column share (container-relative).
    #    Split ratio evidence → the media slot's measured fraction the strip renderer
    #    and the split media column consume.
    # 6) MEASURED HERO/OVERLAY CANVAS ASPECT — a full-bleed background-media slot whose
    #    band the source measured (section-rects w×h) records that exact aspect so the
    #    overlay canvas renders at the measured band height instead of snapping to a
    #    coarse enum class (``wide`` 21/9 under-draws a nearly-16/9 hero by ~150px).
    #    Fill-absent-only, and only when the slot currently rides a coarse full-bleed
    #    enum (wide/pano) or names no aspect — a slot with an explicit ratio is kept.
    if "heroMediaAspect" in fields:
        rw, rh = _num((rect.get("rect") or {}).get("w")), _num((rect.get("rect") or {}).get("h"))
        if rw and rh and rh > 0:
            for slot in ((cs.get("slots") or [])):
                if not isinstance(slot, dict):
                    continue
                role = f"{slot.get('name') or ''} {slot.get('role') or ''}".lower()
                if "background" not in role and "media" not in role:
                    continue
                # a true band-filling background: an explicit full-bleed width OR a
                # z:back layer (the sanctioned text-on-media hero background).
                full = str(slot.get("width") or "").lower() in ("full-bleed", "full")
                zback = str(slot.get("z") or "").lower() == "back"
                if not (full or zback or "background" in role):
                    continue
                cur = str(slot.get("mediaAspect") or "").lower()
                if cur and cur not in ("wide", "pano"):
                    continue  # explicit/measured aspect already present
                slot["mediaAspect"] = f"{int(round(rw))} / {int(round(rh))}"
                added.append(f"mediaAspect[{slot.get('name')}]")

    if "mediaScale" not in fields:
        return added
    split = str(layout.get("splitRatio") or "")
    frac = None
    m = re.match(r"\s*(\d+)\s*/\s*(\d+)\s*", split)
    if m:
        a, b = float(m.group(1)), float(m.group(2))
        if a + b > 0:
            frac = round(b / (a + b), 3)  # media is the RIGHT column (counterweight)
    for sname in ("illustration", "media", "logo-collage", "portrait", "card-carousel"):
        slot = _slot(pattern, sname)
        if not slot:
            continue
        ms = slot.get("mediaScale")
        if isinstance(ms, dict) and "fraction" in ms:
            continue  # already measured
        if frac is None:
            continue
        if not isinstance(ms, dict):
            ms = {}
        ms.setdefault("of", "container")
        ms["fraction"] = frac
        slot["mediaScale"] = ms
        added.append(f"mediaScale[{sname}].fraction")

    return added


def enrich_layout_library(doc: dict, brand_dir: Path,
                          fields: frozenset[str] = ALL_FIELDS) -> dict:
    """Fill absent measured geometry on every extracted pattern in a loaded
    ``layout-library.yaml`` doc, from the lane's own evidence. Returns a telemetry
    summary ``{pattern_id: [added fact keys]}``. Idempotent + fill-absent-only, so a
    fully-authored library is unchanged."""
    brand_dir = Path(brand_dir)
    bands = _load_grounding(brand_dir)
    rects = _load_section_rects(brand_dir)
    summary: dict[str, list[str]] = {}
    for pat in doc.get("patterns") or []:
        if not isinstance(pat, dict):
            continue
        if str(pat.get("origin") or "").lower() not in ("extracted", "", "creation"):
            continue  # designed-from-signals patterns are not measured
        band = resolve_pattern_band(pat, bands)
        if band is None:
            continue
        added = enrich_pattern(pat, band.doc, _rect_for_band(rects, band),
                               fields=fields)
        if added:
            summary[str(pat.get("id"))] = added
    return summary


def unresolved_patterns(doc: dict, brand_dir: Path) -> list[str]:
    """Ids of extracted patterns whose provenance names no single grounded band.

    A DETECTION aid, not a repair: an extracted pattern that resolves to nothing
    silently forfeits every measured fact, which is precisely the failure a bare
    section-number index used to hide on a page-qualified lane."""
    bands = _load_grounding(Path(brand_dir))
    out: list[str] = []
    for pat in doc.get("patterns") or []:
        if not isinstance(pat, dict):
            continue
        if str(pat.get("origin") or "").lower() not in ("extracted", "", "creation"):
            continue
        if resolve_pattern_band(pat, bands) is None:
            out.append(str(pat.get("id")))
    return out


# ── CLI: enrich a lane's layout-library in place ─────────────────────────────────

def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("layout_library", type=Path,
                    help="path to a lane's layout-library.yaml")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the diff summary without writing")
    ap.add_argument("--all-fields", action="store_true",
                    help="apply every extractable fact (default: the calibrated, "
                         "fidelity-verified FIDELITY_FIELDS subset)")
    args = ap.parse_args(argv)
    path = args.layout_library.resolve()
    brand_dir = path.parent
    doc = yaml.safe_load(path.read_text()) or {}
    fields = ALL_FIELDS if args.all_fields else FIDELITY_FIELDS
    summary = enrich_layout_library(doc, brand_dir, fields=fields)
    for pid, keys in summary.items():
        print(f"[measured-geometry] {pid}: +{', '.join(keys)}")
    if not summary:
        print("[measured-geometry] no facts added (already complete or no evidence)")
    orphans = unresolved_patterns(doc, brand_dir)
    if orphans:
        print(f"[measured-geometry] {len(orphans)} extracted pattern(s) resolve to no "
              f"grounded band (no measured facts available): {', '.join(orphans)}")
    if not args.dry_run:
        path.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True,
                                       width=100))
        print(f"[measured-geometry] wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
