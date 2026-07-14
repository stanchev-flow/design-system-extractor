#!/usr/bin/env python3
"""Hero archetype gallery runner — generate + gate + shoot one hero page per brief.

Generic over brand/style/lane (no brand names, archetype ids, or page types in code):
every structural decision comes from the briefs' frontmatter + the genre library
(spec/archetype-library.md). Per brief, in order:

  1. accumulate the DISTINCTNESS exclusion set: archetype ids already instantiated by
     earlier briefs in this lane (each hero must use a different skeleton), plus the
     brief's own frontmatter excludes;
  2. run the REAL generation loop (generate_composition.generate_composition —
     candidate shortlist -> model -> validate -> prefilters -> render -> onbrand gate
     -> bounded repair), with ``force_off_grid=True`` for the lane (the lane-level
     ablation lever; the brand's style pin is never edited);
  3. record the instantiated archetype + gate verdict in the lane summary.

Resumable: a brief whose page dir already has a PASSING onbrand-report.json +
composition.json is skipped unless --force.

Shots: --shots renders each hero page at 1440x900 with prefers-reduced-motion
(full-page PNG into <lane>/shots/) and assembles a labeled contact sheet.

Usage (repo root):
  env -u PLAYWRIGHT_BROWSERS_PATH ./venv/bin/python tools/run_hero_archetype_gallery.py \\
      --brand runs/hubspot-v2/brand --style corporate-saas-clean \\
      --lane runs/hubspot-v2/brand/compose/hero-archetypes [--only page] [--shots]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "brand_pipeline"))

import archetype_library as al          # noqa: E402
import generate_composition as gc       # noqa: E402


def brief_order(briefs_dir: Path, only: str | None) -> list[Path]:
    """Briefs run in the order an optional ``order.txt`` lists (one stem per line).
    When order.txt exists it is AUTHORITATIVE — the lane's declared roster — so
    plan/rationale documents living beside the briefs (e.g. a copy-first plan md,
    spec/archetype-library.md §3) are never mistaken for generation briefs. Without
    order.txt every .md runs alphabetically. --only filters to a single stem."""
    order_file = briefs_dir / "order.txt"
    briefs = {p.stem: p for p in briefs_dir.glob("*.md")}
    if order_file.exists():
        stems = [s.strip() for s in order_file.read_text().splitlines()
                 if s.strip() and not s.strip().startswith("#")]
        ordered = [briefs[s] for s in stems if s in briefs]
    else:
        ordered = [p for _, p in sorted(briefs.items())]
    if only:
        ordered = [p for p in ordered if p.stem == only]
    return ordered


def used_archetypes(lane: Path, skip_stem: str | None = None) -> list[str]:
    """Archetype ids already instantiated by OTHER page dirs in this lane (their
    persisted composition.json files) — the distinctness exclusion set."""
    used: list[str] = []
    for comp_path in sorted(lane.glob("*/composition.json")):
        if skip_stem and comp_path.parent.name == skip_stem:
            continue
        try:
            comp = json.loads(comp_path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        for sec in (comp.get("sections") or []):
            ref = str((sec or {}).get("archetypeRef") or "").strip()
            if ref and ref not in used:
                used.append(ref)
    return used


def used_hero_surfaces(lane: Path, skip_stem: str | None = None) -> list[str]:
    """surfaceIntent values already chosen by OTHER heroes in this lane — the
    gallery-variety consideration (soft preference in the prompt, never a hard
    exclusion: every choice must still be a licensed brand surface)."""
    used: list[str] = []
    for comp_path in sorted(lane.glob("*/composition.json")):
        if skip_stem and comp_path.parent.name == skip_stem:
            continue
        try:
            comp = json.loads(comp_path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        for sec in (comp.get("sections") or []):
            if (sec or {}).get("archetypeRef") or (sec or {}).get("useCase") == "hero":
                si = str(sec.get("surfaceIntent") or "").strip()
                if si:
                    used.append(si)
                break
    return used


def page_passed(page_dir: Path) -> bool:
    score = page_dir / "onbrand-report.json"
    if not (score.exists() and (page_dir / "composition.json").exists()):
        return False
    try:
        return bool(json.loads(score.read_text()).get("overall"))
    except (OSError, json.JSONDecodeError):
        return False


def hero_layout_id(brand_yaml: Path) -> str | None:
    """The brand layout id the gate resolves surface context against — the brand's own
    hero layout when one exists (generic: first layout whose id mentions hero /
    page-header)."""
    import yaml
    doc = yaml.safe_load(brand_yaml.read_text()) or {}
    for layout in (doc.get("layouts") or []):
        lid = str((layout or {}).get("id") or "").lower()
        if "hero" in lid or "page-header" in lid:
            return layout.get("id")
    return None


def shoot(lane: Path, pages: list[str], viewport=(1440, 900)) -> list[Path]:
    """Full-page shots at the canonical tier with prefers-reduced-motion, one per hero."""
    from playwright.sync_api import sync_playwright
    shots_dir = lane / "shots"
    shots_dir.mkdir(parents=True, exist_ok=True)
    out: list[Path] = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": viewport[0], "height": viewport[1]})
        page.emulate_media(reduced_motion="reduce")
        for stem in pages:
            index = lane / stem / "index.html"
            if not index.exists():
                continue
            page.goto(index.resolve().as_uri(), wait_until="networkidle")
            page.wait_for_timeout(400)
            shot = shots_dir / f"{stem}.png"
            page.screenshot(path=str(shot), full_page=True)
            out.append(shot)
            print(f"  shot {shot.relative_to(REPO)}")
        browser.close()
    return out


def contact_sheet(lane: Path, pages: list[str], cols: int = 2,
                  cell_w: int = 720) -> Path | None:
    """One labeled grid PNG combining every hero shot (top-cropped to a uniform cell
    so the sheet stays reviewable; the full-page originals live beside it)."""
    from PIL import Image, ImageDraw
    shots_dir = lane / "shots"
    tiles = [(s, shots_dir / f"{s}.png") for s in pages if (shots_dir / f"{s}.png").exists()]
    if not tiles:
        return None
    label_h, pad = 34, 12
    cell_h = int(cell_w * 0.72)
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell_w + (cols + 1) * pad,
                              rows * (cell_h + label_h) + (rows + 1) * pad), "#1f1f1f")
    draw = ImageDraw.Draw(sheet)
    for i, (stem, path) in enumerate(tiles):
        img = Image.open(path).convert("RGB")
        scale = cell_w / img.width
        img = img.resize((cell_w, int(img.height * scale)))
        img = img.crop((0, 0, cell_w, min(cell_h, img.height)))
        r, c = divmod(i, cols)
        x = pad + c * (cell_w + pad)
        y = pad + r * (cell_h + label_h + pad)
        draw.text((x + 2, y + 8), stem, fill="#f8f5ee")
        sheet.paste(img, (x, y + label_h))
    out = shots_dir / "contact-sheet.png"
    sheet.save(out)
    print(f"  contact sheet -> {out.relative_to(REPO)}")
    return out


def lane_index(lane: Path, pages: list[str]) -> Path:
    """A static lane index page (contact sheet + per-hero links). Lives at
    <lane>/index.html so the studio's compose-lane discovery lists the gallery."""
    summary = {}
    sp = lane / "gallery-summary.json"
    if sp.exists():
        try:
            summary = json.loads(sp.read_text()).get("pages", {})
        except (OSError, json.JSONDecodeError):
            pass
    cards = []
    for stem in pages:
        if not (lane / stem / "index.html").exists():
            continue
        meta = summary.get(stem, {})
        arts = ", ".join(meta.get("archetypes", [])) or "—"
        shot = f"shots/{stem}.png" if (lane / "shots" / f"{stem}.png").exists() else ""
        img = (f'<a href="{stem}/index.html"><img src="{shot}" alt="{stem} hero" '
               f'loading="lazy"></a>' if shot else "")
        cards.append(
            f'<figure>{img}<figcaption><a href="{stem}/index.html">{stem}</a>'
            f'<span>{arts}</span></figcaption></figure>')
    html = f"""<!doctype html><meta charset="utf-8">
<title>Hero archetype gallery</title>
<style>
  body {{ margin: 0; padding: 2.5rem; background: #1f1f1f; color: #f8f5ee;
         font: 300 16px/1.5 system-ui, sans-serif; }}
  h1 {{ font-weight: 500; }} p {{ color: #f8f5ee9e; max-width: 60ch; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
          gap: 1.5rem; margin-top: 2rem; }}
  figure {{ margin: 0; background: #2a2a2a; border-radius: 8px; overflow: hidden; }}
  img {{ display: block; width: 100%; aspect-ratio: 3/2; object-fit: cover;
        object-position: top; }}
  figcaption {{ display: flex; flex-direction: column; gap: 2px; padding: .75rem 1rem; }}
  a {{ color: #ffa581; text-decoration: none; }} a:hover {{ text-decoration: underline; }}
  figcaption span {{ color: #f8f5ee80; font-size: .8125rem; }}
</style>
<h1>Hero archetype gallery — structure varies, style is the brand's</h1>
<p>One hero per page type, each instantiating a DIFFERENT genre archetype
(spec/archetype-library.md) through this brand's extracted facts only.
Full contact sheet: <a href="shots/contact-sheet.png">shots/contact-sheet.png</a></p>
<div class="grid">{''.join(cards)}</div>
"""
    out = lane / "index.html"
    out.write_text(html)
    print(f"  lane index -> {out.relative_to(REPO)}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--brand", type=Path, required=True, help="brand run dir (holds brand.yaml)")
    ap.add_argument("--style", required=True, help="base style id")
    ap.add_argument("--lane", type=Path, required=True, help="gallery lane dir (holds briefs/)")
    ap.add_argument("--only", default=None, help="run a single brief stem")
    ap.add_argument("--force", action="store_true", help="regenerate even if page passed")
    ap.add_argument("--max-repairs", type=int, default=3)
    ap.add_argument("--shots", action="store_true", help="screenshots + contact sheet only")
    ap.add_argument("--rerender", action="store_true",
                    help="re-render + re-gate the SAVED compositions (no model calls) — "
                         "for shared-renderer fixes after generation")
    args = ap.parse_args()

    brand_yaml = (args.brand / "brand.yaml").resolve()
    lane: Path = args.lane.resolve()
    briefs = brief_order(lane / "briefs", args.only)
    if not briefs:
        print("no briefs found", file=sys.stderr)
        return 2
    stems = [b.stem for b in briefs]

    if args.shots:
        shots = shoot(lane, stems)
        contact_sheet(lane, stems)
        lane_index(lane, stems)
        return 0 if shots else 1

    if args.rerender:
        import compose_from_composition as cfc
        gate_layout = hero_layout_id(brand_yaml)
        ok_all = True
        for stem in stems:
            comp_path = lane / stem / "composition.json"
            if not comp_path.exists():
                print(f"[{stem}] no saved composition — skip")
                continue
            comp = json.loads(comp_path.read_text())
            cfc.render_composition(comp, brand_yaml, lane / stem, style_id=args.style,
                                   brand_dir=brand_yaml.parent)
            overall, failures, _ = gc.gate_composition(
                lane / stem, brand_yaml, args.style, layout=gate_layout)
            print(f"[{stem}] re-render gate: {'PASS' if overall else 'FAIL'}"
                  + (f" {[c for c, _ in failures]}" if failures else ""))
            ok_all &= overall
        return 0 if ok_all else 1

    gate_layout = hero_layout_id(brand_yaml)
    summary_path = lane / "gallery-summary.json"
    summary = {"lane": str(lane.relative_to(REPO)), "style": args.style,
               "forceOffGrid": True, "pages": {}}
    if summary_path.exists():
        try:
            summary.update(json.loads(summary_path.read_text()))
        except (OSError, json.JSONDecodeError):
            pass

    ok_all = True
    for brief in briefs:
        stem = brief.stem
        out_dir = lane / stem
        if not args.force and page_passed(out_dir):
            print(f"[{stem}] already gate-green — skip (--force to redo)")
            continue
        exclude = tuple(used_archetypes(lane, skip_stem=stem))
        used_surf = tuple(used_hero_surfaces(lane, skip_stem=stem))
        print(f"[{stem}] generating (exclude: {list(exclude) or 'none'}; "
              f"sibling surfaces: {list(used_surf) or 'none'})")
        t0 = time.time()
        res = gc.generate_composition(
            brief.read_text(), brand_yaml, args.style,
            out_dir=out_dir, brief_id=stem,
            max_repairs=args.max_repairs,
            layout=gate_layout,
            force_off_grid=True,                 # lane-level lever; style pin untouched
            exclude_archetypes=exclude,
            used_surfaces=used_surf,
        )
        refs = sorted({str(s.get("archetypeRef"))
                       for s in ((res.composition or {}).get("sections") or [])
                       if isinstance(s, dict) and s.get("archetypeRef")})
        summary["pages"][stem] = {
            "ok": res.ok, "attempts": res.attempts, "archetypes": refs,
            "seconds": round(time.time() - t0, 1),
            "failures": res.failures[:6],
        }
        summary_path.write_text(json.dumps(summary, indent=2) + "\n")
        print(f"[{stem}] {'PASS' if res.ok else 'FAIL'} after {res.attempts} attempt(s) "
              f"— archetypes: {refs}")
        ok_all &= res.ok

    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
