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
* DEGRADE QUIETLY. Missing/…malformed evidence for a field simply leaves that field
  absent (the composer's structural default is the honest degrade).

The enrichment is invoked by the patterns-recipes author stage (and can be run
standalone for a re-author). It returns a per-pattern diff summary for telemetry.
"""
from __future__ import annotations

import glob
import re
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

def _load_grounding(brand_dir: Path) -> dict[int, dict]:
    """{section index: grounding doc} keyed off the ``section-NN-*.yaml`` filename."""
    out: dict[int, dict] = {}
    gdir = brand_dir / "evidence" / "grounding"
    if not gdir.is_dir() or yaml is None:
        return out
    for f in sorted(glob.glob(str(gdir / "section-*.yaml"))):
        m = re.search(r"section-(\d+)", Path(f).name)
        if not m:
            continue
        try:
            out[int(m.group(1))] = yaml.safe_load(Path(f).read_text()) or {}
        except Exception:
            continue
    return out


def _load_section_rects(brand_dir: Path) -> dict[int, dict]:
    """{section index: rect doc} from the measured band census."""
    p = brand_dir / "evidence" / "section-rects.json"
    if not p.is_file():
        return {}
    try:
        data = json.loads(p.read_text())
    except Exception:
        return {}
    out: dict[int, dict] = {}
    for s in data.get("sections") or []:
        if isinstance(s, dict) and "index" in s:
            out[int(s["index"])] = s
    return out


def _provenance_index(pattern: dict) -> int | None:
    """The source section index a pattern was extracted from (``provenance[0]`` like
    ``section-04``). Returns None when the pattern carries no section provenance."""
    for p in pattern.get("provenance") or []:
        m = re.search(r"section-(\d+)", str(p))
        if m:
            return int(m.group(1))
    return None


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
    grounding = _load_grounding(brand_dir)
    rects = _load_section_rects(brand_dir)
    summary: dict[str, list[str]] = {}
    for pat in doc.get("patterns") or []:
        if not isinstance(pat, dict):
            continue
        if str(pat.get("origin") or "").lower() not in ("extracted", "", "creation"):
            continue  # designed-from-signals patterns are not measured
        idx = _provenance_index(pat)
        if idx is None or idx not in grounding:
            continue
        added = enrich_pattern(pat, grounding[idx], rects.get(idx, {}), fields=fields)
        if added:
            summary[str(pat.get("id"))] = added
    return summary


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
    if not args.dry_run:
        path.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True,
                                       width=100))
        print(f"[measured-geometry] wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
