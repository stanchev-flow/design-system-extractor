#!/usr/bin/env python3
"""Eval-matrix round runner — generate + gate + record the standing 12-brief corpus.

Protocol: evals/matrix/README.md. One ROUND = one full pass over all 12 briefs
(6 campaign types × 2 brands) at a named checkpoint:

  1. generate each brief through the REAL loop (generate_composition — shortlist
     → model → validate → prefilters → render → onbrand gate → bounded repair),
     style pin ``corporate-saas-clean``, ``force_off_grid=True`` (the proven
     generative-lane setup — the gallery runner's levers). The brief file is
     copied into the page dir as ``brief.md`` (conversion_audit's campaign
     binding + provenance).
  2. gate every page with the full post-render battery: slop @1440+@1180 ·
     interaction --strict · spacing --strict · signature --strict · voice
     --strict · section-rules (baseline mode) · conversion-structure (advisory;
     hardFloor gates).
  3. record results.json (machine) + results.md (human table) + round.md
     (context) + shots/ (full-page PNG per page + contact sheet).

Timing discipline (README §Timing): per brief ``generateSeconds`` (model +
repair loop) and per-gate ``gateSeconds`` are recorded separately — generation
deltas call out model/prompt changes, gate deltas call out battery growth.

Conversion-guidance flag: the BASELINE round runs with brief-time guidance OFF
(`inject_conversion_guidance=False`, the pipeline default) — the baseline
measures the un-guided pipeline; the conversion checker's advisory findings on
it quantify what the guidance is for. A later round may A/B the flag.

Resumable: a brief whose page dir already has a PASSING onbrand-report.json +
composition.json is skipped unless --force (the gallery runner's contract).

Usage (repo root):
  env -u PLAYWRIGHT_BROWSERS_PATH ./venv/bin/python tools/run_eval_matrix.py \\
      --label baseline [--only hubspot-v2/pricing] [--skip-gen] [--force] [--shots-only]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "brand_pipeline"))

import generate_composition as gc       # noqa: E402

MATRIX = REPO / "evals" / "matrix"
BRIEFS = MATRIX / "briefs"
STYLE = "corporate-saas-clean"
BRANDS = {
    "hubspot-v2": REPO / "runs" / "hubspot-v2" / "brand",
    "remote": REPO / "runs" / "remote" / "brand",
}
PY = str(REPO / "venv" / "bin" / "python")


def hero_layout_id(brand_yaml: Path) -> str | None:
    """The brand layout id the gate resolves surface context against (the
    gallery runner's resolver — first layout naming hero/page-header)."""
    import yaml
    doc = yaml.safe_load(brand_yaml.read_text()) or {}
    for layout in (doc.get("layouts") or []):
        lid = str((layout or {}).get("id") or "").lower()
        if "hero" in lid or "page-header" in lid:
            return layout.get("id")
    return None


def page_passed(page_dir: Path) -> bool:
    score = page_dir / "onbrand-report.json"
    if not (score.exists() and (page_dir / "composition.json").exists()):
        return False
    try:
        return bool(json.loads(score.read_text()).get("overall"))
    except (OSError, json.JSONDecodeError):
        return False


# ── the post-render battery ─────────────────────────────────────────────────────

def _env() -> dict:
    env = dict(os.environ)
    env.pop("PLAYWRIGHT_BROWSERS_PATH", None)  # repo playwright discipline
    return env


def _run(cmd: list[str], timeout: int = 420) -> tuple[int, str]:
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO,
                          env=_env(), timeout=timeout)
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def battery(page_dir: Path, brand_dir: Path) -> dict:
    """Full gate battery on one rendered page. Every gate is a subprocess with
    its own wall-clock; a gate's report artifacts land inside the page dir."""
    html = page_dir / "index.html"
    gates: dict[str, dict] = {}

    def record(name: str, cmd: list[str], ok_when_zero: bool = True,
               summary_rx: str | None = None):
        t0 = time.time()
        try:
            code, out = _run(cmd)
        except subprocess.TimeoutExpired:
            gates[name] = {"ok": False, "seconds": round(time.time() - t0, 1),
                           "summary": "TIMEOUT"}
            return
        tail = [l for l in out.strip().splitlines() if l.strip()][-3:]
        gates[name] = {"ok": (code == 0) if ok_when_zero else True,
                       "exit": code,
                       "seconds": round(time.time() - t0, 1),
                       "summary": " / ".join(tail)[-300:]}

    record("slop", ["node", str(REPO / "brand_pipeline" / "slop_audit.mjs"), str(html)])
    record("interaction", [PY, "-m", "brand_pipeline.interaction_audit", str(page_dir),
                           "--strict", "--out", str(page_dir / "interaction-audit")])
    record("spacing", [PY, "-m", "brand_pipeline.spacing_audit", str(page_dir),
                       "--brand", str(brand_dir), "--strict", "--no-shots",
                       "--out", str(page_dir / "spacing-audit")])
    record("signature", [PY, "-m", "brand_pipeline.signature_audit", str(page_dir),
                         "--brand", str(brand_dir), "--strict",
                         "--out", str(page_dir / "signature-audit")])
    record("voice", [PY, "-m", "brand_pipeline.voice_audit", str(page_dir),
                     "--brand", str(brand_dir), "--strict",
                     "--out", str(page_dir / "voice-audit")])
    # new gates (steals stage B): section-rules baseline mode records counts
    # (exit 0 by design — severity graduation is post-baseline law); conversion
    # gates hardFloor from birth, advisory rows report.
    record("section-rules", [PY, "-m", "brand_pipeline.section_rules_audit",
                             str(page_dir), "--brand", str(brand_dir),
                             "--out", str(page_dir / "section-rules-audit")])
    record("conversion", [PY, "-m", "brand_pipeline.conversion_audit", str(page_dir),
                          "--brand", str(brand_dir),
                          "--out", str(page_dir / "conversion-audit")])

    # structured counts from the two new gates' machine reports
    # (section-rules findings: verdict ∈ pass/fail/error/skip/delegated/override)
    sr_json = page_dir / "section-rules-audit" / "report.json"
    if sr_json.exists():
        rep = json.loads(sr_json.read_text())
        frows = [f for lane in (rep.get("lanes") or [])
                 for f in (lane.get("findings") or [])]
        failing = [f for f in frows if f.get("verdict") in ("fail", "error")]
        gates["section-rules"]["requiredFails"] = sum(
            1 for f in failing if f.get("severity") == "required")
        gates["section-rules"]["advisoryWarns"] = sum(
            1 for f in failing if f.get("severity") == "advisory")
    cv_json = page_dir / "conversion-audit" / "report.json"
    if cv_json.exists():
        rep = json.loads(cv_json.read_text())
        lane = (rep.get("lanes") or [{}])[0]
        rows = lane.get("rows") or []
        gates["conversion"]["warns"] = sum(1 for r in rows if not r.get("ok"))
        gates["conversion"]["hardFloor"] = sum(
            1 for f in (lane.get("hardFloor") or []) if not f.get("ok"))
        gates["conversion"]["campaign"] = lane.get("campaign")
    return gates


# ── shots ────────────────────────────────────────────────────────────────────────

def shoot_round(round_dir: Path, pages: list[tuple[str, str, Path]],
                viewport=(1440, 900)) -> None:
    from playwright.sync_api import sync_playwright
    shots = round_dir / "shots"
    shots.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": viewport[0], "height": viewport[1]})
        page.emulate_media(reduced_motion="reduce")
        for brand, campaign, page_dir in pages:
            html = page_dir / "index.html"
            if not html.exists():
                continue
            page.goto(html.resolve().as_uri(), wait_until="networkidle")
            page.wait_for_timeout(400)
            page.screenshot(path=str(shots / f"{brand}--{campaign}.png"), full_page=True)
            print(f"  shot shots/{brand}--{campaign}.png")
        browser.close()
    _contact_sheet(round_dir, pages)


def _contact_sheet(round_dir: Path, pages: list[tuple[str, str, Path]],
                   cols: int = 4, cell_w: int = 540) -> None:
    from PIL import Image, ImageDraw
    shots = round_dir / "shots"
    tiles = [(f"{b}--{c}", shots / f"{b}--{c}.png") for b, c, _ in pages
             if (shots / f"{b}--{c}.png").exists()]
    if not tiles:
        return
    label_h, pad = 30, 10
    cell_h = int(cell_w * 0.75)
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell_w + (cols + 1) * pad,
                              rows * (cell_h + label_h) + (rows + 1) * pad), "#1f1f1f")
    draw = ImageDraw.Draw(sheet)
    for i, (label, path) in enumerate(tiles):
        img = Image.open(path).convert("RGB")
        img = img.resize((cell_w, int(img.height * cell_w / img.width)))
        img = img.crop((0, 0, cell_w, min(cell_h, img.height)))
        r, c = divmod(i, cols)
        x = pad + c * (cell_w + pad)
        y = pad + r * (cell_h + label_h + pad)
        draw.text((x + 2, y + 6), label, fill="#f8f5ee")
        sheet.paste(img, (x, y + label_h))
    sheet.save(shots / "contact-sheet.png")
    print(f"  contact sheet -> {(shots / 'contact-sheet.png').relative_to(REPO)}")


# ── results tables ───────────────────────────────────────────────────────────────

GATE_ORDER = ["onbrand", "slop", "interaction", "spacing", "signature", "voice",
              "section-rules", "conversion"]


def render_results_md(results: dict) -> str:
    lines = [f"# Eval-matrix round — {results['round']}",
             "",
             f"Generated {results['generatedAt']} · style `{results['style']}` · "
             f"guidance flag OFF (baseline measures the un-guided pipeline) · "
             f"repo `{results['repo']}`",
             "",
             "| brand | campaign | gen s | attempts | " + " | ".join(GATE_ORDER)
             + " | SR req/adv | conv warns |",
             "|---|---|---|---|" + "---|" * len(GATE_ORDER) + "---|---|"]
    for row in results["pages"]:
        g = row["gates"]
        cells = []
        for name in GATE_ORDER:
            if name == "onbrand":
                cells.append("PASS" if row.get("ok") else "FAIL")
                continue
            e = g.get(name) or {}
            cells.append(("PASS" if e.get("ok") else "FAIL")
                         + (f" ({e['seconds']}s)" if e.get("seconds") else ""))
        sr = g.get("section-rules") or {}
        cv = g.get("conversion") or {}
        lines.append(
            f"| {row['brand']} | {row['campaign']} | {row['generateSeconds']} | "
            f"{row['attempts']} | " + " | ".join(cells)
            + f" | {sr.get('requiredFails', '?')}/{sr.get('advisoryWarns', '?')}"
            + f" | {cv.get('warns', '?')} |")
    lines += ["",
              "SR req/adv = section-rules failing required / advisory rows "
              "(baseline mode: reported, not gating). conv warns = advisory "
              "conversion-structure findings (hardFloor violations fail the "
              "gate column).", ""]
    tg = sum(r["generateSeconds"] for r in results["pages"])
    ta = sum(sum((e or {}).get("seconds", 0) for e in r["gates"].values())
             for r in results["pages"])
    lines.append(f"Totals: generation {tg:.0f}s across {len(results['pages'])} "
                 f"brief(s); battery {ta:.0f}s (post-render, off the "
                 "generation clock).")
    return "\n".join(lines) + "\n"


# ── driver ───────────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--label", default="baseline", help="round label")
    ap.add_argument("--date", default=date.today().isoformat())
    ap.add_argument("--only", default=None, help="run one cell: <brand>/<campaign>")
    ap.add_argument("--force", action="store_true", help="regenerate passing pages")
    ap.add_argument("--skip-gen", action="store_true",
                    help="battery + results only (pages must exist)")
    ap.add_argument("--shots-only", action="store_true")
    ap.add_argument("--max-repairs", type=int, default=3)
    args = ap.parse_args()

    round_dir = MATRIX / "runs" / f"{args.date}-{args.label}"
    round_dir.mkdir(parents=True, exist_ok=True)

    cells: list[tuple[str, str, Path, Path]] = []   # brand, campaign, brief, page_dir
    for brand, brand_dir in BRANDS.items():
        for brief in sorted((BRIEFS / brand).glob("*.md")):
            key = f"{brand}/{brief.stem}"
            if args.only and key != args.only:
                continue
            cells.append((brand, brief.stem, brief, round_dir / brand / brief.stem))
    if not cells:
        print("no matrix cells selected", file=sys.stderr)
        return 2

    if args.shots_only:
        shoot_round(round_dir, [(b, c, d) for b, c, _, d in cells])
        return 0

    git_rev = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True, cwd=REPO).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain"], capture_output=True,
                           text=True, cwd=REPO).stdout.strip().splitlines()

    results_path = round_dir / "results.json"
    results = {"round": f"{args.date}-{args.label}", "style": STYLE,
               "repo": f"{git_rev} (+{len(dirty)} dirty)",
               "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               "guidanceFlag": False, "pages": []}
    if results_path.exists():
        try:
            prior = json.loads(results_path.read_text())
            results["pages"] = [p for p in prior.get("pages", [])
                                if not any(p["brand"] == b and p["campaign"] == c
                                           for b, c, _, _ in cells)]
        except (OSError, json.JSONDecodeError):
            pass

    ok_all = True
    for brand, campaign, brief, page_dir in cells:
        brand_dir = BRANDS[brand]
        brand_yaml = brand_dir / "brand.yaml"
        row = {"brand": brand, "campaign": campaign,
               "generateSeconds": 0.0, "attempts": 0, "ok": False, "gates": {}}

        if args.skip_gen or (not args.force and page_passed(page_dir)):
            row["ok"] = page_passed(page_dir)
            prior_row = next((p for p in json.loads(results_path.read_text())
                              .get("pages", []) if p["brand"] == brand
                              and p["campaign"] == campaign),
                             {}) if results_path.exists() else {}
            row["generateSeconds"] = prior_row.get("generateSeconds", 0.0)
            row["attempts"] = prior_row.get("attempts", 0)
            print(f"[{brand}/{campaign}] generation skipped "
                  f"({'--skip-gen' if args.skip_gen else 'already gate-green'})")
        else:
            print(f"[{brand}/{campaign}] generating…")
            t0 = time.time()
            res = gc.generate_composition(
                brief.read_text(), brand_yaml, STYLE,
                out_dir=page_dir, brief_id=f"{brand}-{campaign}",
                max_repairs=args.max_repairs,
                layout=hero_layout_id(brand_yaml),
                force_off_grid=True,
                # BASELINE: guidance flag stays at the pipeline default (False).
                enforce_gates=False,             # isolated eval matrix — opts out of the flow gate
            )
            row["generateSeconds"] = round(time.time() - t0, 1)
            row["attempts"] = res.attempts
            row["ok"] = res.ok
            row["failures"] = res.failures[:6]
            print(f"[{brand}/{campaign}] {'PASS' if res.ok else 'FAIL'} "
                  f"after {res.attempts} attempt(s) in {row['generateSeconds']}s")

        # the brief rides beside the page (conversion binding + provenance)
        if (page_dir / "index.html").exists():
            (page_dir / "brief.md").write_text(brief.read_text())
            print(f"[{brand}/{campaign}] battery…")
            row["gates"] = battery(page_dir, brand_dir)
            fails = [n for n, e in row["gates"].items() if not e.get("ok")]
            print(f"[{brand}/{campaign}] battery: "
                  + ("all green" if not fails else f"FAIL {fails}"))
        else:
            ok_all = False
            print(f"[{brand}/{campaign}] no rendered page — battery skipped")

        ok_all &= row["ok"]
        results["pages"].append(row)
        results["pages"].sort(key=lambda r: (r["brand"], r["campaign"]))
        results_path.write_text(json.dumps(results, indent=2) + "\n")

    (round_dir / "results.md").write_text(render_results_md(results))
    print(f"\nresults: {round_dir / 'results.md'}")
    shoot_round(round_dir, [(b, c, d) for b, c, _, d in cells])
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
