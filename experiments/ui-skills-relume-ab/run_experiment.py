#!/usr/bin/env python3
"""Run the isolated Relume structure-only fallback controlled A/B."""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
BP = REPO / "brand_pipeline"
PY = REPO / "venv" / "bin" / "python"
BRAND_DIR = REPO / "runs" / "hubspot-v2" / "brand"
BRAND_YAML = BRAND_DIR / "brand.yaml"
BRIEF = HERE / "fixed-brief.md"
BASE_STYLE = "corporate-saas-clean"
MODEL = "claude-opus-4-8"
sys.path.insert(0, str(BP))

import generate_composition as gc  # noqa: E402
import relume_recipe_catalog as rrc  # noqa: E402

def hero_layout_id() -> str | None:
    import yaml
    doc = yaml.safe_load(BRAND_YAML.read_text()) or {}
    for layout in doc.get("layouts") or []:
        lid = str((layout or {}).get("id") or "").lower()
        if "hero" in lid or "page-header" in lid:
            return str(layout.get("id"))
    return None


def relume_fallback_guidance() -> tuple[str, list[str]]:
    guidance, selected = rrc.fallback_guidance(
        ["hero", "about", "features", "testimonial", "pricing", "cta"],
        higher_tier={
            "hero": "measured-brand-pattern",
            "about": "brand-style-archetype",
            "features": "brand-style-archetype",
            "testimonial": "measured-brand-pattern",
            "cta": "measured-brand-pattern",
        },
        ingredients_by_use_case={"pricing": ("plans", "cards", "actions")},
        top_k=3,
    )
    return guidance, selected.get("pricing", [])


def run_gate(cmd: list[object], log: Path) -> int:
    proc = subprocess.run([str(value) for value in cmd], cwd=REPO,
                          capture_output=True, text=True)
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(
        f"$ {' '.join(map(str, cmd))}\n\n--- stdout ---\n{proc.stdout}\n"
        f"--- stderr ---\n{proc.stderr}\n--- exit={proc.returncode} ---\n"
    )
    return proc.returncode


def run_battery(lane: Path) -> dict[str, int]:
    bat = lane / "battery"
    bat.mkdir(exist_ok=True)
    layout = hero_layout_id()
    rows = {
        "onbrand": run_gate(
            [PY, BP / "onbrand_check.py", BRAND_YAML, lane, "--layout", layout,
             "--style", BASE_STYLE, "--composition", "--report", "onbrand-report.md"],
            bat / "onbrand.log"),
        "slop": run_gate(["node", BP / "slop_audit.mjs", lane / "index.html"],
                         bat / "slop.log"),
        "interaction": run_gate(
            [PY, BP / "interaction_audit.py", lane, "--strict", "--out",
             bat / "interaction"], bat / "interaction.log"),
        "spacing": run_gate(
            [PY, BP / "spacing_audit.py", lane, "--brand", BRAND_DIR, "--strict",
             "--no-shots", "--out", bat / "spacing"], bat / "spacing.log"),
        "signature": run_gate(
            [PY, BP / "signature_audit.py", lane, "--brand", BRAND_DIR, "--strict",
             "--out", bat / "signature"], bat / "signature.log"),
        "voice": run_gate(
            [PY, "-m", "brand_pipeline.voice_audit", lane, "--brand", BRAND_DIR,
             "--strict", "--out", bat / "voice"], bat / "voice.log"),
        "section_rules": run_gate(
            [PY, BP / "section_rules_audit.py", lane, "--brand", BRAND_DIR,
             "--strict", "--out", bat / "section-rules"], bat / "section-rules.log"),
        "conversion": run_gate(
            [PY, BP / "conversion_audit.py", lane, "--brand", BRAND_DIR, "--strict",
             "--out", bat / "conversion"], bat / "conversion.log"),
    }
    import media_semantics as ms
    comp = json.loads((lane / "composition.json").read_text())
    hits = ms.lint_media_bindings(comp, ms.load_media_assets(BRAND_DIR))
    (bat / "media-binding.log").write_text(
        "\n".join(["PASS — 0 media-binding hits"] if not hits else
                  [f"FAIL {sid} [{rule}] {msg}" for sid, rule, msg in hits]) + "\n")
    rows["media_binding"] = 0 if not hits else 1
    (lane / "battery-summary.json").write_text(json.dumps(rows, indent=2) + "\n")
    return rows


def stamp_provenance(lane: Path, relume_ids: list[str], relume_enabled: bool) -> list[dict]:
    comp = json.loads((lane / "composition.json").read_text())
    rows = []
    for section in comp.get("sections") or []:
        use_case = str(section.get("useCase") or "")
        if section.get("seededFrom"):
            source = "measured-brand-pattern"
        elif section.get("structureProvenance"):
            source = section["structureProvenance"]
        elif section.get("archetypeRef"):
            source = "brand-style-archetype"
        else:
            source = "shared-archetype"
        rows.append({
            "sectionId": section.get("id"),
            "useCase": use_case,
            "structureProvenance": source,
            "seededFrom": section.get("seededFrom"),
            "archetype": section.get("archetype"),
            "archetypeRef": section.get("archetypeRef"),
            "relumeCandidateIds": relume_ids if source == "relume-fallback" else [],
            "structureRecipeId": section.get("structureRecipeId"),
            "stampMethod": "composition.v1 first-class provenance"
        })
    (lane / "structure-provenance.json").write_text(json.dumps(rows, indent=2) + "\n")
    return rows


def shoot() -> None:
    from PIL import Image, ImageDraw
    from playwright.sync_api import sync_playwright
    shots = HERE / "shots"
    shots.mkdir(exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for lane_name in ("lane-a", "lane-b"):
            if not (HERE / lane_name / "index.html").exists():
                continue
            for width, height, suffix in ((1440, 900, "desktop"), (375, 812, "mobile")):
                page = browser.new_page(viewport={"width": width, "height": height})
                page.emulate_media(reduced_motion="reduce")
                page.goto((HERE / lane_name / "index.html").as_uri(), wait_until="networkidle")
                page.wait_for_timeout(400)
                page.screenshot(path=str(shots / f"{lane_name}-{suffix}.png"), full_page=True)
                page.close()
        browser.close()
    for suffix, width in (("desktop", 620), ("mobile", 360)):
        images = []
        for label, lane_name in (("A — no Relume fallback", "lane-a"),
                                 ("B — pricing structure fallback", "lane-b")):
            shot = shots / f"{lane_name}-{suffix}.png"
            if shot.exists():
                image = Image.open(shot).convert("RGB")
                scale = width / image.width
                image = image.resize((width, int(image.height * scale)))
            else:
                image = Image.new("RGB", (width, 900), "#f1eee8")
                placeholder = ImageDraw.Draw(image)
                placeholder.text((28, 40), "NO RENDER", fill="#8c2f20")
                placeholder.text((28, 70), "Generation exhausted bounded repairs.",
                                 fill="#222222")
            images.append((label, image))
        crop_h = min(2400, max(image.height for _, image in images))
        sheet = Image.new("RGB", (2 * width + 48, crop_h + 48), "#202020")
        draw = ImageDraw.Draw(sheet)
        for index, (label, image) in enumerate(images):
            x = 16 + index * (width + 16)
            draw.text((x, 12), label, fill="#ffffff")
            sheet.paste(image.crop((0, 0, width, min(crop_h, image.height))), (x, 40))
        sheet.save(shots / f"contact-sheet-{suffix}.png")


def main() -> int:
    fallback, relume_ids = relume_fallback_guidance()
    (HERE / "lane-b-guidance.md").write_text(fallback)
    style_directive = gc._auto_style_directives("saas-product", BRAND_YAML) or ""
    outcomes = {}
    for lane_name, guidance, enabled in (
        ("lane-a", "", False),
        ("lane-b", None, True),
    ):
        lane = HERE / lane_name
        started = time.time()
        result = gc.generate_composition(
            BRIEF.read_text(), BRAND_YAML, BASE_STYLE,
            out_dir=lane, brief_id="ui-skills-relume-ab",
            model=MODEL, reasoning_effort="high", max_repairs=7, max_tokens=16000,
            layout=hero_layout_id(), force_off_grid=True,
            style_directives=style_directive,
            section_recipe_guidance=guidance,
            enable_relume_fallback=enabled,
            enforce_gates=True,
        )
        if not result.ok:
            outcomes[lane_name] = {
                "generationOk": False,
                "attempts": result.attempts,
                "seconds": round(time.time() - started, 1),
                "allGatesPass": False,
                "failures": result.failures,
                "provenance": [],
            }
            continue
        provenance = stamp_provenance(lane, relume_ids, enabled)
        battery = run_battery(lane)
        outcomes[lane_name] = {
            "generationOk": result.ok,
            "attempts": result.attempts,
            "seconds": round(time.time() - started, 1),
            "battery": battery,
            "allGatesPass": not any(battery.values()),
            "provenance": provenance,
        }
    if all(row["generationOk"] for row in outcomes.values()):
        shoot()
    (HERE / "results.json").write_text(json.dumps(outcomes, indent=2) + "\n")
    return 0 if all(row["allGatesPass"] for row in outcomes.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
