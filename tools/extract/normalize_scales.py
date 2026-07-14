#!/usr/bin/env python3
"""Derived-scale normalizer (pass1 2026-07) — the QUANTIZATION layer.

Derives, from a brand's EXISTING captured evidence, one quantized scale artifact
(`style-scale.v1`, default `<brand_dir>/style-scale.yaml`):

  type    — modular ratio + base size fit against the measured type ladder
  space   — base unit + step multiples + section rhythm from the measured spacing ladder
  radius  — corner modes grouped from the measured radius facts
  grid    — content max-width / gutter / card gap where measured (columns NOT invented)
  motion  — duration band from the measured motion spec

DUAL-ARTIFACT LAW: raw evidence and brand.yaml are NEVER touched — this layer is a
separate file, and every derived value records its provenance (which raw facts
produced it) and its fit error. When a brand genuinely does not follow a scale the
artifact says so honestly (`fitQuality.verdict: poor`, `followsScale: false`) —
the normalizer never forces a fit.

CONSUMPTION (brand_pipeline/style_scale.py): generative composers prefer derived
steps for NEW geometry where no measured fact binds; a measured fact ALWAYS wins,
and the replica lane never loads this artifact (byte-identical by construction).
Validator advisory C24 checks the artifact's internal consistency + fit honesty.

Deterministic by design: no timestamps — the artifact records the brand.yaml
sha256 prefix as its version anchor, so regeneration is diffable.

Usage:
  ./venv/bin/python tools/extract/normalize_scales.py runs/<brand>/brand [-o out.yaml]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]

# ── raw-fact harvesting ──────────────────────────────────────────────────────────

REM_PX = 16.0

# spacing tokens that are NOT rhythm facts (media tiers / measures / containment /
# aliases of other families) — classified out, recorded under `excluded` with the
# class so the artifact shows every raw input was considered, not dropped silently.
_SPACE_EXCLUDE = (
    (re.compile(r"-tier$"), "media-tier (mark size, not rhythm)"),
    (re.compile(r"-measure$"), "text measure (width family)"),
    (re.compile(r"^container-"), "containment (width family)"),
    (re.compile(r"^radius-"), "radius alias (corner family)"),
)


def _parse_px(value) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return None
    m = re.fullmatch(r"(-?[\d.]+)\s*(rem|px|em)", value.strip())
    if not m:
        return None
    n = float(m.group(1))
    return n * REM_PX if m.group(2) in ("rem", "em") else n


def _token_value(entry):
    return entry.get("value") if isinstance(entry, dict) else entry


def harvest(brand_dir: Path) -> dict:
    """Collect the raw measured inputs the scales are fitted against."""
    doc = yaml.safe_load((brand_dir / "brand.yaml").read_text())
    tokens = doc.get("tokens") or {}

    # type ladder: tokens.type sizeRem at the canonical (base) tier
    type_px: dict[str, float] = {}
    for name, spec in (tokens.get("type") or {}).items():
        if isinstance(spec, dict) and isinstance(spec.get("sizeRem"), dict):
            base = spec["sizeRem"].get("base")
            if isinstance(base, (int, float)):
                type_px[name] = float(base) * REM_PX
    # button label sizes are measured type facts too (sizeRem on the family spec)
    for fam, spec in (doc.get("buttons") or {}).items():
        if isinstance(spec, dict) and isinstance(spec.get("sizeRem"), (int, float)):
            type_px[f"buttons.{fam}"] = float(spec["sizeRem"]) * REM_PX

    # computed corroboration: rendered heading/body px from the capture
    corroboration: dict[str, float] = {}
    comp_path = brand_dir / "evidence" / "computed-styles.json"
    if comp_path.exists():
        comp = json.loads(comp_path.read_text())
        for rank, spec in (comp.get("headings") or {}).items():
            if not isinstance(spec, dict):
                continue  # unrendered rank captured as null
            px = _parse_px(str(spec.get("font-size", "")))
            if px:
                corroboration[rank] = px
        body_px = _parse_px(str((comp.get("body") or {}).get("font-size", "")))
        if body_px:
            corroboration["body"] = body_px

    # spacing ladder
    space_px: dict[str, float] = {}
    excluded: list[dict] = []
    for name, spec in (tokens.get("spacing") or {}).items():
        px = _parse_px(_token_value(spec))
        if px is None:
            excluded.append({"name": name, "class": "non-length (shorthand/expression)"})
            continue
        cls = next((why for rx, why in _SPACE_EXCLUDE if rx.search(name)), None)
        if cls:
            excluded.append({"name": name, "px": px, "class": cls})
        elif px > 200:
            excluded.append({"name": name, "px": px, "class": "width family (> rhythm ceiling)"})
        else:
            space_px[name] = px

    # the brand's OWN authored spacing custom properties from the evidence CSS
    # corpus (--*spacing*/--*space* lengths) — the same mined rungs the spacing
    # auditor sanctions. A brand that ships `--spacing-xs..2xl` has DECLARED its
    # scale; fitting without these misses the smallest rungs (found by the
    # scale_adherence gate: an 8px form seam read off-scale while the source's
    # own --spacing-sm is exactly 8px).
    css_path = brand_dir / "evidence" / "css-rules.json"
    if css_path.exists():
        try:
            css_rules = json.loads(css_path.read_text()).get("rules", [])
        except (json.JSONDecodeError, OSError):
            css_rules = []
        for rule in css_rules:
            decls = rule.get("decls") or ""
            if not isinstance(decls, str):
                continue
            for m in re.finditer(
                    r"(--[\w-]*(?:spacing|space)[\w-]*)\s*:\s*(-?[.\d]+)(px|rem)",
                    decls):
                px = float(m.group(2)) * (REM_PX if m.group(3) == "rem" else 1.0)
                if 0 < px <= 200:
                    space_px.setdefault(f"css:{m.group(1)}", px)

    # radius facts
    radius_px: dict[str, float] = {}
    radius_special: dict[str, str] = {}
    for name, spec in (tokens.get("radius") or {}).items():
        val = _token_value(spec)
        px = _parse_px(val)
        if px is not None:
            radius_px[name] = px
        elif isinstance(val, str):
            radius_special[name] = val.strip()

    # grid facts (only where measured)
    grid: dict[str, float] = {}
    for key, tok in (("contentMaxPx", "container-max"),
                     ("gutterPx", "column-to-column"),
                     ("cardGapPx", "grid-gap")):
        px = _parse_px(_token_value((tokens.get("spacing") or {}).get(tok)))
        if px is not None:
            grid[key] = px

    # motion durations from the measured motion spec
    durations: dict[str, float] = {}
    easing = None
    ms = ((doc.get("voice") or {}).get("motionSpec") or {})
    for name, val in (ms.get("durations") or {}).items():
        m = re.fullmatch(r"([\d.]+)\s*ms", str(val).strip())
        if m:
            durations[name] = float(m.group(1))
    if isinstance(ms.get("easing"), dict):
        easing = ms["easing"].get("primary")

    return {"doc": doc, "type_px": type_px, "corroboration": corroboration,
            "space_px": space_px, "space_excluded": excluded,
            "radius_px": radius_px, "radius_special": radius_special,
            "grid": grid, "durations": durations, "easing": easing}


# ── fitting ──────────────────────────────────────────────────────────────────────

# coarsest-first, PARSIMONY-selected: a denser ratio fits anything (1.067 steps
# land within 3.3% of every number — a vacuous quantization), so the fit takes
# the LARGEST ratio whose RMSE clears the bar, not the minimum-RMSE ratio.
_RATIOS = (1.618, 1.5, 1.414, 4 / 3, 1.25, 1.2, 1.125)
_RMSE_BAR = 0.025


def fit_type(type_px: dict[str, float], corroboration: dict[str, float]) -> dict:
    """Fit sizes = base * ratio^k (k integer) against the measured ladder.
    The fit is DESCRIPTIVE: fitQuality records how well the brand's real ladder
    follows the best modular scale — a poor fit is recorded, never forced."""
    sizes = sorted(set(type_px.values()))
    if not sizes:
        return {"followsScale": False, "note": "no measured type ladder"}
    body = min(sizes, key=lambda s: abs(s - 16.0))  # base anchor = the body-ish size

    def rate(ratio, base):
        errs = []
        for s in sizes:
            k = round(math.log(s / base, ratio))
            errs.append(abs(base * ratio ** k - s) / s)
        return math.sqrt(sum(e * e for e in errs) / len(errs)), max(errs)

    best = None       # min-RMSE fallback when nothing clears the bar
    chosen = None     # largest ratio clearing the bar (parsimony winner)
    for ratio in _RATIOS:
        for base in sorted({body, 16.0, 18.0}):
            rmse, worst = rate(ratio, base)
            cand = (round(rmse, 6), worst, ratio, base)
            if best is None or cand[0] < best[0]:
                best = cand
            if chosen is None and rmse <= _RMSE_BAR:
                chosen = cand
        if chosen:
            break
    rmse, worst, ratio, base = chosen or best
    verdict = "good" if rmse <= 0.02 else ("approximate" if rmse <= 0.05 else "poor")
    k_min = round(math.log(min(sizes) / base, ratio))
    k_max = round(math.log(max(sizes) / base, ratio))
    steps = [round(base * ratio ** k, 1) for k in range(k_min, k_max + 1)]
    fits = []
    for name, s in sorted(type_px.items(), key=lambda kv: (-kv[1], kv[0])):
        k = round(math.log(s / base, ratio))
        pred = base * ratio ** k
        fits.append({"name": name, "measuredPx": round(s, 1),
                     "stepPx": round(pred, 1), "k": k,
                     "errPct": round(abs(pred - s) / s * 100, 1),
                     "corroboratedBy": sorted(r for r, px in corroboration.items()
                                              if abs(px - s) < 0.75) or None})
    return {
        "basePx": round(base, 1), "ratio": round(ratio, 3),
        "followsScale": verdict != "poor",
        "fitQuality": {"rmse": round(rmse, 4),
                       "worstErrPct": round(worst * 100, 1),
                       "verdict": verdict},
        "stepsPx": steps,
        "fits": fits,
        "provenance": {
            "method": "parsimony modular-ratio fit: the COARSEST candidate ratio "
                      f"({' > '.join(str(round(r, 3)) for r in _RATIOS)}) whose "
                      f"RMSE clears {_RMSE_BAR} wins (a denser ratio fits anything "
                      "— vacuous quantization); min-RMSE fallback when none clears. "
                      "Inputs are the brand's measured type ladder (tokens.type "
                      "sizeRem at the canonical tier + button sizeRem), "
                      "corroborated against evidence/computed-styles.json "
                      "rendered px",
            "inputs": [{"name": n, "px": round(p, 1)}
                       for n, p in sorted(type_px.items())],
        },
    }


def fit_space(space_px: dict[str, float], excluded: list[dict]) -> dict:
    """Base unit + step multiples: the largest unit (8 preferred over 4) that
    carries ≥90% of the measured rhythm ladder; off-unit facts are recorded as
    outliers with their nearest step, never snapped."""
    vals = sorted(set(space_px.values()))
    if not vals:
        return {"followsScale": False, "note": "no measured spacing ladder"}
    choice = None
    for unit in (8.0, 4.0):
        on = [v for v in vals if abs(v / unit - round(v / unit)) < 0.51 / unit]
        coverage = len(on) / len(vals)
        if coverage >= 0.9:
            choice = (unit, on, coverage)
            break
        if choice is None or coverage > choice[2]:
            choice = (unit, on, coverage)
    unit, on, coverage = choice
    verdict = "good" if coverage >= 0.95 else ("approximate" if coverage >= 0.8 else "poor")
    steps = sorted({round(v) for v in on})
    outliers = [{"name": n, "px": p,
                 "nearestStepPx": round(round(p / unit) * unit),
                 "errPx": round(abs(p - round(p / unit) * unit), 1)}
                for n, p in sorted(space_px.items()) if round(p) not in steps]
    section = sorted({round(p) for n, p in space_px.items()
                      if n.startswith("section-")})
    return {
        "baseUnitPx": round(unit),
        "followsScale": verdict != "poor",
        "fitQuality": {"coverage": round(coverage, 3), "verdict": verdict},
        "stepsPx": steps,
        "multiples": [round(s / unit, 2) for s in steps],
        "sectionRhythmPx": section,
        "outliers": outliers,
        "excluded": sorted(excluded, key=lambda e: e["name"]),
        "provenance": {
            "method": "largest base unit (8 preferred, else 4) carrying ≥90% of "
                      "the measured rhythm ladder (tokens.spacing lengths ≤200px, "
                      "media tiers / measures / containment / radius aliases "
                      "classified out); steps are the measured multiples present, "
                      "never invented rungs",
            "inputs": [{"name": n, "px": round(p, 1)}
                       for n, p in sorted(space_px.items())],
        },
    }


def fit_radius(radius_px: dict[str, float], special: dict[str, str]) -> dict:
    modes: dict[float, list[str]] = {}
    for name, px in sorted(radius_px.items()):
        modes.setdefault(px, []).append(name)
    mode_list = [{"px": round(px, 1), "roles": sorted(roles)}
                 for px, roles in sorted(modes.items())]
    px_vals = sorted(modes)
    btn = radius_px.get("button")
    plate = radius_px.get("card") or radius_px.get("panel")
    if btn is not None and plate is not None and btn >= 24 and btn >= 2 * plate:
        policy = "pill-controls"
    elif len(px_vals) <= 1:
        policy = "uniform"
    else:
        policy = "tiered"
    return {"modes": mode_list, "policy": policy,
            "special": dict(sorted(special.items())) or None,
            "provenance": {"method": "tokens.radius grouped by value; policy is "
                                     "descriptive (pill-controls when the button "
                                     "radius dwarfs the plate radius)",
                           "inputs": [{"name": n, "px": round(p, 1)}
                                      for n, p in sorted(radius_px.items())]}}


def fit_motion(durations: dict[str, float], easing) -> dict:
    if not durations:
        return {"note": "no measured motion durations"}
    rungs = sorted(set(durations.values()))
    return {"rungsMs": [round(r) for r in rungs],
            "bandMs": {"min": round(rungs[0]), "max": round(rungs[-1])},
            "easing": easing,
            "provenance": {"method": "voice.motionSpec.durations (measured motion "
                                     "census) — the band is the measured envelope, "
                                     "no invented tiers",
                           "inputs": [{"name": n, "ms": round(v)}
                                      for n, v in sorted(durations.items())]}}


# ── artifact assembly ────────────────────────────────────────────────────────────

def normalize(brand_dir: Path) -> dict:
    raw = harvest(brand_dir)
    digest = hashlib.sha256((brand_dir / "brand.yaml").read_bytes()).hexdigest()[:12]
    grid = {k: round(v, 1) for k, v in raw["grid"].items()}
    art = {
        "schema": "style-scale.v1",
        "brand": brand_dir.parent.name if brand_dir.name == "brand" else brand_dir.name,
        "sourceDigest": f"sha256:{digest}",
        "inputs": {"brandYaml": "brand.yaml",
                   "computedStyles": "evidence/computed-styles.json",
                   "motionSpec": "voice.motionSpec"},
        "law": ("derived layer — raw evidence and brand.yaml stay untouched; a "
                "measured fact ALWAYS beats a derived step; the replica lane never "
                "consumes this file"),
        "type": fit_type(raw["type_px"], raw["corroboration"]),
        "space": fit_space(raw["space_px"], raw["space_excluded"]),
        "radius": fit_radius(raw["radius_px"], raw["radius_special"]),
        "grid": {**grid,
                 "columns": None,
                 "note": "columns omitted — not a measured fact for this brand "
                         "(the registration grid is pipeline structure); widths "
                         "carry their token provenance",
                 "provenance": {"contentMaxPx": "tokens.spacing.container-max",
                                "gutterPx": "tokens.spacing.column-to-column",
                                "cardGapPx": "tokens.spacing.grid-gap"}} if grid else None,
        "motion": fit_motion(raw["durations"], raw["easing"]),
    }
    return art


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("brand_dir", type=Path, help="runs/<brand>/brand directory")
    ap.add_argument("-o", "--out", type=Path, default=None,
                    help="output path (default <brand_dir>/style-scale.yaml)")
    args = ap.parse_args(argv)
    brand_dir = args.brand_dir.resolve()
    if not (brand_dir / "brand.yaml").exists():
        raise SystemExit(f"no brand.yaml under {brand_dir}")
    art = normalize(brand_dir)
    out = args.out or (brand_dir / "style-scale.yaml")
    out.write_text(yaml.safe_dump(art, sort_keys=False, allow_unicode=True,
                                  width=88))
    t, s = art["type"], art["space"]
    print(f"[normalize-scales] {out}")
    if t.get("basePx"):
        print(f"  type:  base {t['basePx']}px ratio {t['ratio']} "
              f"({t['fitQuality']['verdict']}, rmse {t['fitQuality']['rmse']})")
    if s.get("baseUnitPx"):
        print(f"  space: unit {s['baseUnitPx']}px, {len(s['stepsPx'])} steps, "
              f"section rhythm {s['sectionRhythmPx']} "
              f"({s['fitQuality']['verdict']}, coverage {s['fitQuality']['coverage']})")
    print(f"  radius policy: {art['radius'].get('policy')}; "
          f"motion band: {art['motion'].get('bandMs')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
