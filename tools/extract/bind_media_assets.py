#!/usr/bin/env python3
"""bind_media_assets.py — fold measured placements into the media-assets registry.

mine_asset_placements.py answers "which file rendered in which section" one page
at a time. This pass unions those per-page records into the brand-level evidence
file and writes the answer back onto the authored registry, so every consumer
(harness, replica, framework/codegen) can ask "where does this asset belong and
may I reuse it" instead of ranking candidates by aspect ratio.

Per registered logical asset (canonical file + variants[]) it sets:
    placements[]       measured page/section/zone rows (spec §2.2)
    compositionRoles   generic geometric roles derived from those rows
    reusePolicy        site-chrome | cross-page | page-specific | unplaced
    provenance.pages   capture pages the asset was observed on
    provenance.sections  canonical section slugs (the grounding/layout tokens)
    provenance.confidence  high once a measured placement exists

It also reports the two integrity gaps that silently corrupt generation:
UNPLACED registered assets (curated but never observed rendering — unproven, a
generator must not reach for them) and UNREGISTERED placed files (observed on
the page but missing from the registry — the extraction lost a real asset).

Usage:
    ./venv/bin/python tools/extract/bind_media_assets.py \
        --brand-dir runs/<brand>/brand [--registry media-assets.yaml] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import yaml

_HERE = Path(__file__).resolve().parent
_BP = _HERE.parent.parent / "brand_pipeline"
if str(_BP) not in sys.path:
    sys.path.insert(0, str(_BP))
import media_semantics as ms  # noqa: E402

SCHEMA = "asset-placements.v1"
# rendered areas within this ratio count as "comparable size" when deciding
# whether a band holds one lead media well or a row of equal siblings.
_SIBLING_AREA_RATIO = 2.5


def load_page_placements(brand_dir: Path) -> list[dict]:
    pages_dir = brand_dir / "evidence" / "pages"
    docs = []
    for path in sorted(pages_dir.glob("*/asset-placements.json")):
        try:
            docs.append(json.loads(path.read_text()))
        except Exception as exc:
            print(f"  [warn] unreadable {path}: {exc}")
    return docs


def merge_pages(docs: list[dict]) -> dict:
    """Per-page placement docs → one brand-level evidence artifact."""
    placements, rich, sections, unresolved = [], [], [], []
    for d in docs:
        page = str(d.get("page") or "")
        for p in d.get("placements") or []:
            row = dict(p)
            row.setdefault("page", page)
            placements.append(row)
        for r in d.get("richMedia") or []:
            row = dict(r)
            row["page"] = page
            rich.append(row)
        for s in d.get("sections") or []:
            sections.append({"page": page, **s})
        for u in d.get("unresolved") or []:
            unresolved.append({"page": page, **u})
    return {
        "schemaVersion": SCHEMA,
        "note": ("Brand-level union of per-page asset placements — the measured "
                 "answer to which curated file rendered in which section."),
        "pages": [str(d.get("page") or "") for d in docs],
        "sections": sections,
        "placements": placements,
        "richMedia": rich,
        "unresolved": unresolved,
    }


def sibling_counts(placements: list[dict]) -> dict[int, int]:
    """id(placement) → how many comparably sized assets share its band.

    A band holding six marks of the same size is a strip; one holding a single
    large well is a lead. Size comparability (not raw count) is what separates
    them, so a lead media well beside a small caption icon is not miscounted.
    """
    by_band: dict[tuple, list[dict]] = defaultdict(list)
    for p in placements:
        if p.get("zone") != "main" or p.get("hidden"):
            continue
        by_band[(p.get("page"), p.get("sectionSlug"), p.get("sectionIndex"))].append(p)
    out: dict[int, int] = {}
    for rows in by_band.values():
        for p in rows:
            area = _area(p)
            if not area:
                out[id(p)] = 1
                continue
            peers = [q for q in rows
                     if _area(q) and max(area, _area(q)) / min(area, _area(q))
                     <= _SIBLING_AREA_RATIO]
            out[id(p)] = len(peers)
    return out


def _area(p: dict) -> int:
    r = p.get("rendered") or {}
    return int(r.get("w") or 0) * int(r.get("h") or 0)


def registry_files(entry: dict) -> list[str]:
    files = [Path(str(entry.get("file") or "")).name]
    for v in entry.get("variants") or []:
        if isinstance(v, dict) and v.get("file"):
            files.append(Path(str(v["file"])).name)
    return [f for f in files if f]


def placement_row(p: dict, role: str) -> dict:
    return {
        "page": p.get("page"),
        "section": p.get("sectionSlug"),
        "zone": p.get("zone"),
        "role": role,
        "occurrences": p.get("occurrences", 1),
        "rendered": p.get("rendered"),
        "position": p.get("position"),
        "fractionOfSection": (p.get("fractionOfSection") or {}).get("w"),
        "visible": not p.get("hidden"),
        "alt": p.get("alt"),
    }


def _correct_unrefined_marks(entry: dict, roles: list[str]) -> None:
    """Measured proof-strip membership corrects an UNREFINED kind/rights guess.

    Draft kinds come from filename keywords, so a customer mark whose file never
    says "logo" arrives as a photograph owned by the brand — and a generator that
    trusts that will happily reuse someone else's trademark as decorative art.
    Only entries still carrying the draft's low-confidence guess are corrected;
    anything a human or the authoring pass refined is left alone.
    """
    if "proof-strip-mark" not in roles:
        return
    prov = entry.get("provenance") if isinstance(entry.get("provenance"), dict) else {}
    sem = entry.get("assetSemantics") if isinstance(entry.get("assetSemantics"), dict) else {}
    refined = bool(sem.get("subject")) or str(prov.get("confidence")) != "low"
    if refined or ms.kind_family(sem.get("kind")) in {"icon", "badge"}:
        return
    sem["kind"] = "logo-third-party"
    sem.setdefault("subtype", "client")
    entry["assetSemantics"] = sem
    entry["usageRights"] = "third-party-mark"
    entry["kindCorrectedBy"] = "measured-placement"


def bind(registry: dict, merged: dict) -> dict:
    """Write measured placements onto registry entries; return a summary."""
    entries = [a for a in (registry.get("assets") or []) if isinstance(a, dict)]
    placements = merged.get("placements") or []
    siblings = sibling_counts(placements)
    by_file: dict[str, list[dict]] = defaultdict(list)
    for p in placements:
        by_file[str(p.get("asset") or "")].append(p)

    rich_by_section: dict[tuple, list[dict]] = defaultdict(list)
    for r in merged.get("richMedia") or []:
        rich_by_section[(r.get("page"), r.get("sectionSlug"))].append(r)

    bound_files: set[str] = set()
    unplaced: list[str] = []
    for entry in entries:
        kind = (entry.get("assetSemantics") or {}).get("kind")
        rows, roles = [], []
        for fname in registry_files(entry):
            for p in by_file.get(fname, []):
                bound_files.add(fname)
                role = ms.derive_composition_role(kind, p,
                                                  siblings.get(id(p), 1))
                rows.append(placement_row(p, role))
                if role not in roles:
                    roles.append(role)
        rows.sort(key=lambda r: (str(r["page"]), str(r["section"] or "~"),
                                 str(r["zone"])))
        if rows:
            entry["placements"] = rows
            entry["compositionRoles"] = roles
        else:
            entry["placements"] = []
            unplaced.append(str(entry.get("id")))
        entry["reusePolicy"] = ms.derive_reuse_policy(rows)
        _correct_unrefined_marks(entry, roles)

        prov = entry.get("provenance")
        if not isinstance(prov, dict):
            prov = {}
            entry["provenance"] = prov
        prov["pages"] = sorted({r["page"] for r in rows if r.get("page")})
        prov["sections"] = sorted({r["section"] for r in rows if r.get("section")})
        prov.setdefault("source", "capture-files")
        prov["confidence"] = "high" if rows else "low"

        # An asset hidden in a band that also carries runtime media is that
        # media's still fallback — the only honest way to render the band
        # without the animation the capture could not keep.
        stand_in = []
        for r in rows:
            if r["visible"] or not r.get("section"):
                continue
            for rm in rich_by_section.get((r["page"], r["section"]), []):
                stand_in.append({"kind": rm.get("kind"), "ref": rm.get("ref")})
        if stand_in:
            entry["standsInFor"] = stand_in

    placed_files = {str(p.get("asset")) for p in placements}
    return {
        "entries": len(entries),
        "unplaced": unplaced,
        "unregistered": sorted(placed_files - bound_files),
    }


def seed_from_draft(registry: dict, draft: dict) -> tuple[int, int]:
    """Reconcile the registry against the curated draft; (added, refreshed).

    The registry is meant to be the SUPERSET of the curated library; when the
    authoring pass covers only part of it, every unregistered file becomes
    invisible to consumers even though it demonstrably renders on the page.
    Missing ids are appended in draft order.

    Existing entries keep their authored semantics (subject, kind, treatment),
    but variants[] is REFRESHED from the draft: content-hash dedupe is measured,
    not authored, and a registry authored against an earlier capture pass will
    be missing the sibling filenames a later page contributed — which is exactly
    how a rendering file ends up unregistered.
    """
    entries = registry.setdefault("assets", [])
    by_id = {str(a.get("id")): a for a in entries if isinstance(a, dict)}
    added = refreshed = 0
    for a in draft.get("assets") or []:
        if not isinstance(a, dict):
            continue
        aid = str(a.get("id"))
        prior = by_id.get(aid)
        if prior is None:
            entries.append(dict(a))
            by_id[aid] = entries[-1]
            added += 1
            continue
        draft_variants = a.get("variants") or []
        have = {str((v or {}).get("file")) for v in (prior.get("variants") or [])}
        new = [v for v in draft_variants if str(v.get("file")) not in have]
        if new:
            prior.setdefault("variants", []).extend(new)
            refreshed += 1
    return added, refreshed


# slot NAME hints → the measured composition roles that may fill them. Generic
# role words only: the same table has to read correctly for any brand's layout
# library, so no section, palette, or content vocabulary appears in it.
_SLOT_ROLE_HINTS: list[tuple[str, set[str]]] = [
    (r"logo|proof|marquee|partner|client|trust|badge|award",
     {"proof-strip-mark", "badge-cluster-mark"}),
    (r"icon|glyph", {"inline-spot-icon"}),
    (r"item|card|cell|tile|gallery|grid",
     {"card-media-well", "proof-strip-mark", "badge-cluster-mark"}),
    (r"media|art|image|visual|illustration|cluster|figure|hero|lead|photo|backdrop",
     {"section-lead-media", "full-bleed-backdrop", "card-media-well",
      "responsive-alternate"}),
]


# an explicit slot TYPE is authored intent and outranks any name reading.
_SLOT_TYPE_ROLES: dict[str, set[str]] = {
    "logo": {"proof-strip-mark", "badge-cluster-mark"},
    "icon": {"inline-spot-icon"},
    "media": {"section-lead-media", "full-bleed-backdrop", "card-media-well",
              "responsive-alternate"},
    "image": {"section-lead-media", "full-bleed-backdrop", "card-media-well",
              "responsive-alternate"},
}


def _pattern_sections(pattern: dict) -> list[str]:
    return [str(p) for p in (pattern.get("provenance") or []) if p]


def _slot_roles(slot: dict) -> set[str] | None:
    """Which measured roles may fill this slot, or None when it takes no media."""
    stype = str(slot.get("type") or "").strip().lower()
    if stype in _SLOT_TYPE_ROLES:
        return _SLOT_TYPE_ROLES[stype]
    if stype in {"content", "action", "text"}:
        # A repeatable card collection carries its own per-card art: the slot is
        # content-typed because the copy leads, but the media well is part of the
        # card anatomy, so it still takes measured card art.
        if re.search(r"media-well|card-media|card-list|card-collection|card-grid",
                     str(slot.get("role") or ""), re.IGNORECASE):
            return {"card-media-well"}
        return None
    name = str(slot.get("name") or "")
    for pat, roles in _SLOT_ROLE_HINTS:
        if re.search(pat, name, re.IGNORECASE):
            return roles
    return None


def _slot_containers(doc: dict):
    """(node, slots) for every media-bearing container in a brand doc.

    Both artifacts that carry slots — brand.yaml ``layouts[]`` and the layout
    library's ``patterns[].contentShape`` — are bound the same way, because a
    binding that lands in only one of them leaves the other lane still guessing.
    """
    for node in (doc.get("layouts") or []) + (doc.get("patterns") or []):
        if not isinstance(node, dict):
            continue
        if isinstance(node.get("slots"), list):
            yield node, node["slots"]
        shape = node.get("contentShape")
        if isinstance(shape, dict) and isinstance(shape.get("slots"), list):
            yield node, shape["slots"]


def _visual_order(row: dict) -> tuple:
    pos = row.get("position") or {}
    return (pos.get("y") if pos.get("y") is not None else 10 ** 6,
            pos.get("x") if pos.get("x") is not None else 10 ** 6)


def bind_layout_slots(lib: dict, registry: dict) -> dict:
    """Fill each media-bearing slot with the assets MEASURED in that band.

    A slot used to be filled at render time by ranking the whole library on
    role/aspect guesses, which is how a proof-row mark ends up in a hero well.
    Here the pattern's own provenance names its source section, and the registry
    knows which files rendered there, so the binding is a lookup rather than a
    judgement call. Slots with no measured asset stay empty on purpose — an
    honest gap beats a plausible-looking wrong image.
    """
    rows_by_section: dict[str, list[dict]] = defaultdict(list)
    for entry in registry.get("assets") or []:
        if not isinstance(entry, dict):
            continue
        fname = Path(str(entry.get("file") or "")).name
        for p in entry.get("placements") or []:
            if p.get("zone") != "main" or not p.get("section"):
                continue
            rows_by_section[str(p["section"])].append({**p, "file": fname})

    bound = empty = 0
    unbound_bands: list[str] = []
    for node, slots in _slot_containers(lib):
        # A pattern that recurs across bands describes ONE instance, so it binds
        # ONE band's art: pooling every occurrence stacks five sections' pictures
        # into a single slot, and the composers then draw a row of orphan media
        # with no copy to go with it. The first band with measured art is the
        # representative; the rest stay recorded in the registry's placements.
        rows: list[dict] = []
        for token in _pattern_sections(node):
            for slug, srows in rows_by_section.items():
                if slug == token or slug.startswith(f"{token}-"):
                    rows.extend(srows)
            if rows:
                break
        by_role: dict[str, list[dict]] = defaultdict(list)
        for r in rows:
            by_role[str(r.get("role"))].append(r)
        for group in by_role.values():
            group.sort(key=_visual_order)

        used: set[str] = set()
        for slot in slots:
            if not isinstance(slot, dict):
                continue
            roles = _slot_roles(slot)
            if roles is None:
                continue
            candidates: list[dict] = []
            filled: list[str] = []
            for role in sorted(roles):
                if role in used:
                    continue
                group = by_role.get(role, [])
                if group:
                    candidates.extend(group)
                    filled.append(role)
            # A responsive twin is the SAME picture in another format, kept hidden
            # at the measured viewport (and carrying its own role). Binding it
            # beside its visible original turns one image into a two-picture run,
            # so visible placements win across the whole slot; a slot whose only
            # evidence is the hidden twin still binds it, since that is the
            # picture the band shows.
            visible = [r for r in candidates if r.get("visible")]
            files = [r["file"] for r in (visible or candidates)]
            if files:
                used.update(filled)
            if files:
                slot["assets"] = files
                bound += 1
            else:
                slot.pop("assets", None)
                empty += 1
        leftover = sorted(set(by_role) - used)
        if leftover:
            unbound_bands.append(f"{node.get('id')} ({', '.join(leftover)})")
    return {"boundSlots": bound, "emptySlots": empty,
            "unboundBands": unbound_bands}


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--brand-dir", type=Path, required=True)
    ap.add_argument("--registry", default="media-assets.yaml",
                    help="registry filename inside the brand dir")
    ap.add_argument("--dry-run", action="store_true",
                    help="report the binding without writing the registry")
    ap.add_argument("--from-draft", default="media-assets-draft.yaml",
                    help="curated draft used to seed logical assets the registry "
                         "is missing ('' to disable)")
    ap.add_argument("--layout-library", default="layout-library.yaml",
                    help="layout library whose media slots get bound to the "
                         "measured placements ('' to skip)")
    ap.add_argument("--brand", default="brand.yaml",
                    help="brand doc whose layouts[].slots get the same binding "
                         "('' to skip)")
    return ap


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    brand_dir = args.brand_dir
    docs = load_page_placements(brand_dir)
    if not docs:
        raise SystemExit(
            f"no evidence/pages/*/asset-placements.json under {brand_dir} — run "
            "tools/extract/mine_asset_placements.py per capture page first")
    merged = merge_pages(docs)
    out_path = brand_dir / "evidence" / "asset-placements.json"
    out_path.write_text(json.dumps(merged, indent=1) + "\n")
    print(f"[done] merged placements: {len(merged['placements'])} rows across "
          f"{len(docs)} pages -> {out_path}")

    reg_path = brand_dir / args.registry
    if not reg_path.is_file():
        print(f"[skip] no {args.registry} to bind (evidence written)")
        return 0
    registry = yaml.safe_load(reg_path.read_text()) or {}
    draft_path = brand_dir / args.from_draft if args.from_draft else None
    if draft_path and draft_path.is_file():
        added, refreshed = seed_from_draft(
            registry, yaml.safe_load(draft_path.read_text()) or {})
        if added or refreshed:
            print(f"[seed] +{added} curated assets the registry was missing, "
                  f"{refreshed} entries gained variants (from {draft_path.name})")
    summary = bind(registry, merged)
    if not args.dry_run:
        reg_path.write_text(yaml.safe_dump(registry, sort_keys=False,
                                           allow_unicode=True, width=88))
    print(f"[done] bound {summary['entries']} registry entries "
          f"({'dry run' if args.dry_run else reg_path.name})")
    if summary["unplaced"]:
        print(f"  [gap] {len(summary['unplaced'])} registered assets never "
              f"observed rendering (reusePolicy: unplaced): "
              f"{', '.join(summary['unplaced'][:8])}"
              f"{' …' if len(summary['unplaced']) > 8 else ''}")
    if summary["unregistered"]:
        print(f"  [gap] {len(summary['unregistered'])} placed files missing from "
              f"the registry: {', '.join(summary['unregistered'][:6])}"
              f"{' …' if len(summary['unregistered']) > 6 else ''}")

    targets = [t for t in (args.layout_library, args.brand) if t]
    for target in targets:
        path = brand_dir / target
        if not path.is_file():
            continue
        doc = yaml.safe_load(path.read_text()) or {}
        slots = bind_layout_slots(doc, registry)
        if not args.dry_run:
            path.write_text(yaml.safe_dump(doc, sort_keys=False,
                                           allow_unicode=True, width=88))
        print(f"[done] slot binding: {slots['boundSlots']} media slots bound to "
              f"measured assets, {slots['emptySlots']} left empty -> {path.name}")
        if slots["unboundBands"]:
            print(f"  [gap] measured media with no slot to hold it: "
                  f"{'; '.join(slots['unboundBands'])} — the layout is missing a "
                  "media slot the source band actually has.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
