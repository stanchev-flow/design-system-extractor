#!/usr/bin/env python3
"""run_pipeline_flow.py — ONE high-level entry point for the canonical, gated
brand pipeline.

A single intent runs the WHOLE ordered sequence and FAILS CLOSED at the first
gate it can't clear (never silently proceeds to generation):

    G1 extraction → G2 validation (C1–C28) → G3 harness → G4 replica (≥ bar)
    → G5 creative generation (only after G1–G4 pass)

The operator does NOT have to name the sub-steps. Either of these does all of it:

    # extract + build the harness + prove the replica for a fresh capture
    ./venv/bin/python run_pipeline_flow.py --brand woodwave-v2 \
        --capture screenshots/woodwave-v2

    # same spine for an already-extracted lane (verify/resume), no re-extract
    ./venv/bin/python run_pipeline_flow.py --brand woodwave-v2

    # free-text intent — resolves the brand + entry stage automatically
    ./venv/bin/python run_pipeline_flow.py --intent "build replica for woodwave-v2"
    ./venv/bin/python run_pipeline_flow.py --intent "extract brand hubspot-v2"

Add ``--generate --brief <brief.md>`` to also run creative page generation; it
runs ONLY when G1–G4 pass. Exit code is 0 only when every requested gate cleared;
a blocked/needs_iteration flow exits non-zero and writes an honest
``flow-report.json`` into the lane.

The replica quality bar defaults to 0.90 (``--replica-bar``); see
brand_pipeline/spec/pipeline-flow.md for the rationale.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_DIR / "brand_pipeline"))

import pipeline_flow as pf  # noqa: E402

# free-text intent → (entry stage, whether to generate). The brand is pulled out
# separately. Every intent still runs the full ordered spine from the entry
# stage; the mapping only picks where a lane is allowed to RESUME from.
_STAGE_ALIASES = {
    "extract": "G1", "extraction": "G1", "capture": "G1",
    "validate": "G2", "validation": "G2",
    "harness": "G3", "spec-book": "G3", "preview": "G3", "catalog": "G3",
    "replica": "G4", "fidelity": "G4", "rebuild": "G4",
    "generate": "G5", "generation": "G5", "compose": "G5", "page": "G5",
}


def parse_intent(text: str) -> tuple[str | None, str, bool]:
    """(brand, start_from, run_generation) from a free-text intent. Lenient: the
    brand is the last token that resolves to a runs/<brand>/brand lane, else the
    token after 'for'/'brand'."""
    words = re.findall(r"[\w./-]+", text.lower())
    run_generation = any(w in ("generate", "generation", "compose", "page")
                         for w in words)
    start_from = "G1"
    for w in words:
        if w in _STAGE_ALIASES:
            # 'build replica for X' should still run the full spine (harness
            # before replica), so replica/generate intents keep G1 entry unless
            # the operator explicitly resumes; we only advance for validate/harness.
            if _STAGE_ALIASES[w] in ("G1", "G2", "G3"):
                start_from = _STAGE_ALIASES[w]
            break
    brand = None
    # explicit 'for X' / 'brand X'
    for i, w in enumerate(words[:-1]):
        if w in ("for", "brand", "lane", "of"):
            cand = words[i + 1]
            if pf.brand_dir_for(cand).joinpath("brand.yaml").is_file() or \
                    (pf.RUNS_DIR / cand).is_dir():
                brand = cand
                break
    if brand is None:
        for w in reversed(words):
            if (pf.RUNS_DIR / w / "brand" / "brand.yaml").is_file():
                brand = w
                break
    return brand, start_from, run_generation


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--brand", help="brand key → runs/<brand>/brand")
    ap.add_argument("--intent", help="free-text intent, e.g. 'build replica for woodwave-v2'")
    ap.add_argument("--capture", type=Path,
                    help="capture dir for a fresh extraction (runs extraction first)")
    ap.add_argument("--from", dest="start_from", default="G1",
                    help="resume entry gate: G1/G2/G3/G4 (or extract/validate/harness/replica)")
    ap.add_argument("--replica-bar", type=float, default=pf.DEFAULT_REPLICA_BAR,
                    help=f"replica fidelity threshold (default {pf.DEFAULT_REPLICA_BAR})")
    ap.add_argument("--max-iterations", type=int, default=pf.DEFAULT_MAX_ITERATIONS,
                    help="G4 diagnose→repair→re-score budget")
    ap.add_argument("--source-shot", type=Path, default=None,
                    help="source full-page png for the replica (default: crops-manifest)")
    ap.add_argument("--studio-url", default=None,
                    help="base URL of a running Studio server for an HTTP-200 harness probe")
    ap.add_argument("--no-build-harness", action="store_true",
                    help="G3 only VERIFIES the harness files; never renders them")
    ap.add_argument("--no-replica-run", action="store_true",
                    help="G4 reads an existing replica-report.json instead of re-shooting")
    ap.add_argument("--trusted-replica-score", type=float, default=None,
                    help="verify a committed lane against a recorded/verified score "
                         "(no re-shoot) — records provenance 'trusted'")
    ap.add_argument("--generate", action="store_true",
                    help="also run G5 creative generation (only if G1–G4 pass)")
    ap.add_argument("--brief", type=Path, default=None, help="brief markdown for G5")
    ap.add_argument("--style", default="editorial-luxury", help="style id for G5")
    ap.add_argument("--allow-no-vision", action="store_true")
    ap.add_argument("--author-model", default="claude-opus-4-8",
                    help="configured model for the executable author stage")
    ap.add_argument("--author-timeout", type=float, default=300.0,
                    help="author provider timeout in seconds")
    ap.add_argument("--author-max-repairs", type=int, default=2,
                    help="bounded C1-C28 author repair attempts")
    ap.add_argument("--force-author", action="store_true",
                    help="re-author a complete lane without repeating evidence stages")
    ap.add_argument("--force-author-stage",
                    choices=("foundation", "copy-chrome", "patterns-recipes",
                             "media", "projections"),
                    help="re-run one author DAG stage and all descendants")
    ap.add_argument("--no-smoke", action="store_true",
                    help="skip the validator C11 composed-demo smoke check")
    return ap


def _norm_stage(s: str) -> str:
    s = (s or "G1").strip()
    if s.upper() in pf.GATE_ORDER:
        return s.upper()
    return _STAGE_ALIASES.get(s.lower(), "G1")


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    brand = args.brand
    start_from = _norm_stage(args.start_from)
    run_generation = args.generate

    if args.intent:
        i_brand, i_start, i_gen = parse_intent(args.intent)
        brand = brand or i_brand
        if args.start_from == "G1":
            start_from = i_start
        run_generation = run_generation or i_gen

    if not brand:
        raise SystemExit("provide --brand or an --intent naming a known lane")

    result = pf.run_flow(
        brand,
        replica_bar=args.replica_bar,
        capture=args.capture,
        start_from=start_from,
        run_generation=run_generation,
        brief=args.brief,
        style=args.style,
        max_iterations=args.max_iterations,
        source_shot=args.source_shot,
        studio_url=args.studio_url,
        build_harness=not args.no_build_harness,
        replica_run=not args.no_replica_run,
        trusted_replica_score=args.trusted_replica_score,
        allow_no_vision=args.allow_no_vision,
        smoke=not args.no_smoke,
        author_model=args.author_model,
        author_timeout=args.author_timeout,
        author_max_repairs=args.author_max_repairs,
        force_author=args.force_author,
        force_author_stage=args.force_author_stage,
    )

    print()
    print(f"flow status: {result.status.upper()}  "
          f"(generation {'ALLOWED' if result.generation_allowed else 'REFUSED'})")
    for g in result.gates:
        print(f"  {g.gate} {g.name:11s} {g.status.upper():15s} "
              + (g.reason[:100] if g.reason else ""))
    if result.report_path:
        print(f"flow report: {result.report_path}")
    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())
