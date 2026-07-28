#!/usr/bin/env python3
"""ai-product-launch lane driver — generate + gate a NEW Breeze AI product-launch
page for hubspot-v3 (the now-faithful harness).

Canonical composition path (generate_composition.generate_composition):
  wireframe planning -> composition.v1 -> deterministic render (compose_from_composition)
  -> onbrand --composition gate, with a bounded validate/repair loop.

Style: BASE_STYLE `corporate-saas-clean` is the renderable base the renderer + gate need;
the AUTO-RESOLVED best preset (`saas-product`) is resolved through the style-library
resolver (brand facts win; dissents captured) and injected as the [[PASS3-STYLE]] block —
the pass-3 bakeoff pattern also used by the hubspot-v2 customer-story lane.

Gates are ENFORCED (fail-closed flow); hubspot-v3 has cleared G1-G4 (flow-report.json
generationAllowed=true) so generation is ALLOWED.

MODEL-API CAUTION: the Anthropic path has hung for thousands of seconds in this env.
generate_composition writes wireframe.json / composition.json / generation-telemetry.json
incrementally, and this driver is meant to be run under an EXTERNAL bounded wall-clock
timeout (the caller kills it if it exceeds the bound). No output is faked.

Usage (repo root):
  env -u PLAYWRIGHT_BROWSERS_PATH ./venv/bin/python \
      runs/hubspot-v3/brand/compose/ai-product-launch/run_ai_product_launch.py \
      [--max-repairs N]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
from pathlib import Path


def _arm_watchdog(seconds: float, marker: Path) -> None:
    """Self-bounding wall-clock guard: if the process (incl. a hung Anthropic
    call) runs past `seconds`, write a marker and hard-exit. Artifacts are written
    incrementally by generate_composition, so partial progress is preserved."""
    def _kill():
        marker.write_text(json.dumps({
            "status": "wall_clock_timeout",
            "boundSeconds": seconds,
            "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "note": "generation exceeded the bounded wall clock; hard-exited. "
                    "Inspect generation-telemetry.json / composition.json for the "
                    "last completed attempt.",
        }, indent=2) + "\n")
        os._exit(124)
    t = threading.Timer(seconds, _kill)
    t.daemon = True
    t.start()

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
sys.path.insert(0, str(REPO / "brand_pipeline"))

import generate_composition as gc  # noqa: E402

BRAND_DIR = REPO / "runs" / "hubspot-v3" / "brand"
BRAND_YAML = BRAND_DIR / "brand.yaml"
BRIEF = HERE / "copy-brief.md"
PRESET_STYLE = "saas-product"          # auto-resolved best preset under brand facts
BASE_STYLE = "corporate-saas-clean"    # renderable base the renderer + gate consume
OUT_DIR = HERE                          # render index.html at the lane root


def hero_layout_id() -> str | None:
    import yaml
    doc = yaml.safe_load(BRAND_YAML.read_text()) or {}
    for layout in (doc.get("layouts") or []):
        lid = str((layout or {}).get("id") or "").lower()
        if "hero" in lid or "page-header" in lid:
            return layout.get("id")
    return None


def resolve_preset_block() -> str:
    """Auto-resolve the saas-product preset UNDER brand facts and capture the
    brand-wins dissents to disk (provable style provenance). Returns the resolved
    [[PASS3-STYLE]] directive block (identical to the pure auto path)."""
    block = gc._auto_style_directives(PRESET_STYLE, BRAND_YAML) or ""
    (HERE / "auto-preset-block.txt").write_text(block)
    # capture the per-section dissents (brand facts suppressing preset slots)
    dissents: dict = {"preset": PRESET_STYLE, "base": BASE_STYLE,
                      "directiveDissents": [], "presetDissents": []}
    try:
        import style_resolver as sr
        lib = sr.load_library()
        bundle = sr.load_brand_bundle(BRAND_DIR)
        res = sr.resolve_all(PRESET_STYLE, lib, bundle)
        seen_dir, seen_pre = set(), set()
        for _sid, r in (res.items() if isinstance(res, dict) else []):
            for d in (r.get("dissents") or []):
                key = json.dumps(d, sort_keys=True)
                if key not in seen_dir:
                    seen_dir.add(key)
                    dissents["directiveDissents"].append(d)
            for d in (r.get("presetDissents") or []):
                key = json.dumps(d, sort_keys=True, default=str)
                if key not in seen_pre:
                    seen_pre.add(key)
                    dissents["presetDissents"].append(d)
    except Exception as exc:  # never let provenance capture take down the run
        dissents["error"] = f"{type(exc).__name__}: {exc}"
    (HERE / "preset-resolution.json").write_text(json.dumps(dissents, indent=2) + "\n")
    return block


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--max-repairs", type=int, default=4,
                    help="generate_composition internal validate/repair budget")
    ap.add_argument("--timeout-s", type=float, default=1500.0,
                    help="hard wall-clock bound; the process force-exits past it")
    args = ap.parse_args()

    _arm_watchdog(args.timeout_s, HERE / "TIMEOUT.json")
    preset_block = resolve_preset_block()
    gate_layout = hero_layout_id()
    print(f"[ai-product-launch] base={BASE_STYLE} preset={PRESET_STYLE} "
          f"gate-layout={gate_layout} preset-block={len(preset_block)}chars "
          f"max_repairs={args.max_repairs} gates=ENFORCED")

    t0 = time.time()
    res = gc.generate_composition(
        BRIEF.read_text(), BRAND_YAML, BASE_STYLE,
        out_dir=OUT_DIR, brief_id="ai-product-launch",
        max_repairs=args.max_repairs,
        layout=gate_layout,
        force_off_grid=True,               # allow designed/archetype structures per section
        style_directives=preset_block,     # inject the auto-resolved saas-product preset
        enforce_gates=True,                # PROVE the fail-closed flow (v3 PASSES)
    )
    secs = round(time.time() - t0, 1)

    comp = res.composition or {}
    sections = [{"id": s.get("id"), "useCase": s.get("useCase"),
                 "archetype": s.get("archetype"),
                 "surfaceIntent": s.get("surfaceIntent"),
                 "novelty": s.get("novelty"),
                 "seededFrom": s.get("seededFrom"),
                 "structureProvenance": s.get("structureProvenance"),
                 "archetypeRef": s.get("archetypeRef")}
                for s in (comp.get("sections") or []) if isinstance(s, dict)]
    summary = {"ok": res.ok, "attempts": res.attempts, "seconds": secs,
               "failures": res.failures[:12], "schemaErrors": res.schema_errors[:6],
               "sections": sections,
               "preset": PRESET_STYLE, "baseStyle": BASE_STYLE}
    (HERE / "run-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(f"[ai-product-launch] {'PASS' if res.ok else 'FAIL'} after "
          f"{res.attempts} attempt(s) in {secs}s")
    for s in sections:
        print(f"    {s['id']:14s} {str(s['archetype']):8s} "
              f"{str(s['surfaceIntent']):12s} {s['structureProvenance']}")
    if not res.ok:
        print("failures:", res.failures[:12])
    return 0 if res.ok else 1


if __name__ == "__main__":
    sys.exit(main())
