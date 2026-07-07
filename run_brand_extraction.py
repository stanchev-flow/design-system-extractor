#!/usr/bin/env python3
"""Brand extraction pipeline — capture → mine → measure → slice → vision-ground
→ curate → author → validate.

Turns a Save-Page-As capture of a source site (saved .html + *_files/ dir + a
full-page screenshot) into the evidence set a brand authoring pass needs, then
gates the authored brand data behind a fail-loud output contract:

    runs/<brand>/brand/
      evidence/dom-sections.json      DOM census (sections, buttons, chrome, eyebrows)
      evidence/css-rules.json         raw parsed rules (@media/:hover aware)
      evidence/css-facts.json         hover pairs + radius/font/color/tracking censuses
      evidence/computed-styles.json   JS-off computed styles (chrome, action families)
      evidence/section-rects.json     per-section bounding boxes
      evidence/crops/                 per-section screenshot crops (+ manifest)
      evidence/grounding/             per-section VISION grounding YAMLs
      assets/ + assets-manifest.json  curated capture assets (incl. inline-SVG logos)

The `author` stage is agent work, not a script: brand.yaml, section-copy.yaml,
layout-library.yaml and assets-tagged.json are hand-authored FROM the evidence
(per brand_pipeline/spec/ layout-analyst-skill.md, brand-schema.md,
section-copy-schema.md). `validate` then enforces the contract
(tools/extract/validate_brand_evidence.py) — the gaps that broke the Remote run
fail loud here instead of rendering as empty sections.

Each stage reads only upstream artifacts, so stages re-run independently:

    ./venv/bin/python run_brand_extraction.py --brand remote --capture screenshots/remote
    ./venv/bin/python run_brand_extraction.py --brand remote --stages slice,ground --force
    ./venv/bin/python run_brand_extraction.py --brand remote --stages validate
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
TOOLS_EXTRACT = PROJECT_DIR / "tools" / "extract"
RUNS_DIR = PROJECT_DIR / "runs"
SPEC_DIR = PROJECT_DIR / "brand_pipeline" / "spec"
sys.path.insert(0, str(TOOLS_EXTRACT))

ALL_STAGES = ("mine-dom", "mine-css", "measure", "slice", "ground", "curate",
              "author", "validate")


def parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Brand extraction pipeline (evidence-first, vision-grounded)")
    ap.add_argument("--brand", required=True, help="brand key -> runs/<brand>/brand/")
    ap.add_argument("--capture", type=Path,
                    help="capture dir (default: screenshots/<brand>/)")
    ap.add_argument("--stages", default="all",
                    help=f"csv of {','.join(ALL_STAGES)} or 'all'")
    ap.add_argument("--force", action="store_true",
                    help="re-run stages whose output exists")
    # measure
    ap.add_argument("--js", action="store_true",
                    help="measure: enable JavaScript (default off — static CSS)")
    ap.add_argument("--viewport", default="1440x900")
    ap.add_argument("--pick", action="append", default=[], metavar="NAME=SELECTOR",
                    help="measure: extra nodes to measure (repeatable)")
    # slice
    ap.add_argument("--slices", type=int, default=0,
                    help="slice: fallback N equal slices when rects are unusable")
    ap.add_argument("--boundaries", help="slice: explicit csv y cut lines")
    # ground
    ap.add_argument("--model", default="claude-opus-4-8")
    ap.add_argument("--reasoning-effort", default="medium")
    ap.add_argument("--limit", type=int, default=0,
                    help="ground: only the first N crops (smoke runs)")
    # curate
    ap.add_argument("--manifest", type=Path, help="curate: explicit curation.yaml")
    ap.add_argument("--min-bytes", type=int, default=800)
    # validate
    ap.add_argument("--allow-no-vision", action="store_true")
    ap.add_argument("--min-logo-assets", type=int, default=3)
    args = ap.parse_args(argv)

    stages = ALL_STAGES if args.stages == "all" else tuple(
        s.strip() for s in args.stages.split(","))
    for s in stages:
        if s not in ALL_STAGES:
            raise SystemExit(f"Unknown stage: {s} (valid: {ALL_STAGES})")
    args.stage_list = stages
    return args


def main(argv=None) -> int:
    args = parse_args(argv)
    capture = args.capture or (PROJECT_DIR / "screenshots" / args.brand)
    brand_dir = RUNS_DIR / args.brand / "brand"
    evidence = brand_dir / "evidence"
    crops_dir = evidence / "crops"
    grounding_dir = evidence / "grounding"

    print(f"Brand extraction: {args.brand}")
    print(f"Capture: {capture}")
    print(f"Output:  {brand_dir.relative_to(PROJECT_DIR)}")
    print()

    scripted = [s for s in args.stage_list if s not in ("author", "validate")]
    if scripted and not capture.is_dir():
        raise SystemExit(f"capture dir not found: {capture} — save the source page "
                         "(html + _files + full-page screenshot) there first")

    def should_run(stage: str, output: Path) -> bool:
        if stage not in args.stage_list:
            return False
        if output.exists() and not args.force:
            print(f"[skip] {stage}: {output.relative_to(PROJECT_DIR)} exists "
                  "(use --force to redo)")
            return False
        return True

    def run_stage(label: str, module_name: str, argv_tool: list[str]) -> None:
        import importlib
        mod = importlib.import_module(module_name)
        print(f"[run ] {label}: {module_name} {' '.join(argv_tool)}")
        rc = mod.main(argv_tool)
        if rc:
            raise SystemExit(f"stage {label} failed (exit {rc})")

    # 1) mine-dom — DOM census
    dom_out = evidence / "dom-sections.json"
    if should_run("mine-dom", dom_out):
        run_stage("mine-dom", "mine_dom",
                  ["--capture", str(capture), "--out", str(dom_out)])

    # 2) mine-css — stylesheet rules + derived facts
    css_out = evidence / "css-facts.json"
    if should_run("mine-css", css_out):
        run_stage("mine-css", "mine_css",
                  ["--capture", str(capture), "--out-dir", str(evidence)])

    # 3) measure — JS-off computed styles + section rects
    measured_out = evidence / "computed-styles.json"
    if should_run("measure", measured_out):
        tool_argv = ["--capture", str(capture), "--out-dir", str(evidence),
                     "--viewport", args.viewport]
        if args.js:
            tool_argv.append("--js")
        for p in args.pick:
            tool_argv += ["--pick", p]
        run_stage("measure", "measure_computed", tool_argv)

    # 4) slice — screenshot -> per-section crops
    crops_out = crops_dir / "crops-manifest.json"
    if should_run("slice", crops_out):
        tool_argv = ["--capture", str(capture), "--out-dir", str(crops_dir)]
        rects = evidence / "section-rects.json"
        if args.boundaries:
            tool_argv += ["--boundaries", args.boundaries]
        elif args.slices:
            tool_argv += ["--slices", str(args.slices)]
        elif rects.is_file():
            tool_argv += ["--rects", str(rects)]
        else:
            tool_argv += ["--slices", "10"]
            print("[warn] slice: no section-rects.json (run measure first?) — "
                  "falling back to 10 equal slices")
        run_stage("slice", "slice_sections", tool_argv)

    # 5) ground — per-crop vision grounding (needs ANTHROPIC_API_KEY)
    ground_out = grounding_dir / "grounding-run.json"
    if should_run("ground", ground_out):
        tool_argv = ["--crops-dir", str(crops_dir), "--out-dir", str(grounding_dir),
                     "--model", args.model,
                     "--reasoning-effort", args.reasoning_effort]
        if args.limit:
            tool_argv += ["--limit", str(args.limit)]
        if args.force:
            tool_argv.append("--force")
        run_stage("ground", "ground_sections_vision", tool_argv)

    # 6) curate — capture assets -> brand assets/ (+ inline-SVG logos)
    curated_out = brand_dir / "assets-manifest.json"
    if should_run("curate", curated_out):
        tool_argv = ["--capture", str(capture), "--brand-dir", str(brand_dir),
                     "--min-bytes", str(args.min_bytes)]
        if args.manifest:
            tool_argv += ["--manifest", str(args.manifest)]
        else:
            tool_argv.append("--auto")
        if args.force:
            tool_argv.append("--force")
        run_stage("curate", "curate_assets", tool_argv)

    # 7) author — agent work, not a script: report what exists vs what's owed
    if "author" in args.stage_list:
        print("[info] author: hand-authoring stage (extraction agent) — inputs are "
              "the evidence files above; specs:")
        for spec in ("layout-analyst-skill.md", "brand-schema.md",
                     "section-copy-schema.md", "extraction-grounding-prompt.md"):
            print(f"         - {(SPEC_DIR / spec).relative_to(PROJECT_DIR)}")
        owed = ["brand.yaml", "section-copy.yaml", "layout-library.yaml",
                "assets-tagged.json", "brand.md", "voice.md"]
        for name in owed:
            state = "present" if (brand_dir / name).exists() else "MISSING"
            print(f"         {name:24s} {state}")

    # 8) validate — fail-loud output contract
    if "validate" in args.stage_list:
        import validate_brand_evidence as vbe
        tool_argv = ["--brand-dir", str(brand_dir),
                     "--min-logo-assets", str(args.min_logo_assets)]
        if args.allow_no_vision:
            tool_argv.append("--allow-no-vision")
        print(f"[run ] validate: validate_brand_evidence {' '.join(tool_argv)}")
        rc = vbe.main(tool_argv)
        if rc:
            return rc

    print()
    print("Evidence artifacts:")
    if evidence.is_dir():
        for p in sorted(evidence.rglob("*")):
            if p.is_file():
                print(f"  {p.relative_to(PROJECT_DIR)} ({p.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
