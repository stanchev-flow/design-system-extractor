#!/usr/bin/env python3
"""Evaluate v159+ YAML normalized AST and design-system quality."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from screenshot_to_template.config import AppConfig, load_config
from screenshot_to_template.models import get_provider
from screenshot_to_template.pipeline.single_shot import load_and_encode_image


AST_REVIEW_PROMPT = """\
You are a strict reviewer for the second step of a screenshot-to-design-system pipeline.

You receive a full-page screenshot and a normalized_site_ast YAML artifact generated from raw per-section YAML captures plus a global full-site pass.

Score only the normalized AST. Do not score the final generated website.

Criteria:
- schema_validity: valid YAML, required keys, all detected sections represented, provenance/traceability present.
- global_layer_awareness: captures full-site surface runs and grouped layers, such as nav+hero same background, adjacent sections sharing one wrapper, continuous gradients, and hard resets.
- normalization_quality: converts raw observations into comparable reusable roles/signatures instead of copying exact section walkthroughs.
- factual_visual_coverage: preserves major surfaces, typography hierarchy, component candidates, image/graphic roles, spacing rhythm, and critical pairings visible in the screenshot.
- abstraction_balance: keeps section-local facts traceable but does not overfit to exact content or exact list of section layouts.
- downstream_usefulness: gives the design-system step enough reliable token/component/pattern candidates and do-not-generalize constraints.

Return JSON only:
{
  "weighted_score": 0-100,
  "scores": {
    "schema_validity": 0-10,
    "global_layer_awareness": 0-10,
    "normalization_quality": 0-10,
    "factual_visual_coverage": 0-10,
    "abstraction_balance": 0-10,
    "downstream_usefulness": 0-10
  },
  "strengths": [],
  "weaknesses": [],
  "actionable_prompt_or_pipeline_changes": [],
  "verdict": ""
}
"""


DESIGN_REVIEW_PROMPT = """\
You are a strict reviewer for the final design-system YAML step of a screenshot-to-template pipeline.

You receive a full-page screenshot, the normalized AST YAML, and the final design_system_yaml artifact.

Score only the design system as a reusable implementation contract, not generated sites.

Criteria:
- schema_validity: valid YAML, required keys, parseable token/component/pattern/rule structure.
- visual_fidelity: tokens and rules match visible color, type, surfaces, depth, graphics, and overall creative direction.
- pattern_abstraction: captures reusable layout and composition patterns rather than the exact source section list and exact section layouts.
- component_contract: buttons, labels, cards, links, media, controls, and surface variants are explicit enough for generation.
- global_layer_translation: carries full-site layer/group awareness into surfaces, section-run patterns, and rules.
- generation_usefulness: practical enough for three different generators to create varied but on-system pages without copying the screenshot.

Return JSON only:
{
  "weighted_score": 0-100,
  "scores": {
    "schema_validity": 0-10,
    "visual_fidelity": 0-10,
    "pattern_abstraction": 0-10,
    "component_contract": 0-10,
    "global_layer_translation": 0-10,
    "generation_usefulness": 0-10
  },
  "strengths": [],
  "weaknesses": [],
  "actionable_prompt_or_pipeline_changes": [],
  "verdict": ""
}
"""


def strip_fence(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def parse_json_response(text: str) -> dict:
    cleaned = strip_fence(text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if match:
            return json.loads(match.group(0))
    raise ValueError("Reviewer did not return JSON")


def deterministic_yaml_summary(path: Path, expected_type: str) -> dict:
    text = path.read_text()
    try:
        data = yaml.safe_load(text)
        parse_ok = isinstance(data, dict)
    except Exception as exc:
        return {
            "parse_ok": False,
            "error": str(exc),
            "expected_type": expected_type,
            "actual_type": None,
            "section_count": 0,
        }
    return {
        "parse_ok": parse_ok,
        "expected_type": expected_type,
        "actual_type": data.get("type") if isinstance(data, dict) else None,
        "schema_version": data.get("schema_version") if isinstance(data, dict) else None,
        "section_count": len(data.get("sections", [])) if isinstance(data, dict) and isinstance(data.get("sections"), list) else 0,
        "top_level_keys": sorted(data.keys()) if isinstance(data, dict) else [],
    }


def weighted(scores: dict[str, float]) -> float:
    if not scores:
        return 0.0
    return round(sum(float(v) for v in scores.values()) / len(scores) * 10, 2)


def review_artifact(provider, screenshot_path: Path, system_prompt: str, user_prompt: str, max_image_dimension: int) -> dict:
    response = provider.analyze_image(
        image_b64=load_and_encode_image(str(screenshot_path), max_image_dimension),
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        max_tokens=4096,
    )
    payload = parse_json_response(response)
    if "weighted_score" not in payload:
        payload["weighted_score"] = weighted(payload.get("scores", {}))
    return payload


def evaluate_site(provider, version_dir: Path, entry: dict, max_image_dimension: int) -> dict:
    name = entry["name"]
    screenshot_path = version_dir / entry["screenshot"]
    single = version_dir / name / "single"
    ast_path = single / "structural-analysis.md"
    design_path = single / "design-system.yaml"
    if not design_path.exists():
        design_path = single / "design-system.md"
    global_path = single / "global-site-grounding.yaml"

    ast_text = ast_path.read_text()
    design_text = design_path.read_text()
    global_text = global_path.read_text() if global_path.exists() else ""

    ast_det = deterministic_yaml_summary(ast_path, "normalized_site_ast")
    design_det = deterministic_yaml_summary(design_path, "design_system")

    ast_prompt = (
        "## Deterministic YAML Check\n\n"
        f"{json.dumps(ast_det, indent=2)}\n\n"
        "## Global Full-Site Grounding YAML\n\n"
        f"{global_text[:16000]}\n\n"
        "## Normalized Site AST YAML\n\n"
        f"{ast_text[:48000]}"
    )
    design_prompt = (
        "## Deterministic YAML Check\n\n"
        f"{json.dumps(design_det, indent=2)}\n\n"
        "## Normalized Site AST YAML\n\n"
        f"{ast_text[:28000]}\n\n"
        "## Design System YAML\n\n"
        f"{design_text[:48000]}"
    )

    ast_review = review_artifact(provider, screenshot_path, AST_REVIEW_PROMPT, ast_prompt, max_image_dimension)
    design_review = review_artifact(provider, screenshot_path, DESIGN_REVIEW_PROMPT, design_prompt, max_image_dimension)

    return {
        "name": name,
        "ast_deterministic": ast_det,
        "design_deterministic": design_det,
        "normalized_ast_review": ast_review,
        "design_system_yaml_review": design_review,
    }


def render_markdown(version: str, results: list[dict]) -> str:
    lines = [f"# YAML Pipeline Quality Evaluation - {version}", ""]
    for result in results:
        ast = result["normalized_ast_review"]
        ds = result["design_system_yaml_review"]
        lines.append(f"## {result['name']}")
        lines.append(f"- Normalized AST score: **{ast.get('weighted_score')} / 100**")
        lines.append(f"- Design-system YAML score: **{ds.get('weighted_score')} / 100**")
        lines.append(f"- AST YAML parse/type: `{result['ast_deterministic'].get('parse_ok')}` / `{result['ast_deterministic'].get('actual_type')}`")
        lines.append(f"- Design YAML parse/type: `{result['design_deterministic'].get('parse_ok')}` / `{result['design_deterministic'].get('actual_type')}`")
        if ast.get("weaknesses"):
            lines.append("- AST weaknesses: " + "; ".join(map(str, ast["weaknesses"][:3])))
        if ds.get("weaknesses"):
            lines.append("- Design weaknesses: " + "; ".join(map(str, ds["weaknesses"][:3])))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--sites", default=None, help="Comma-separated site names to evaluate")
    parser.add_argument("--config", default=None)
    args = parser.parse_args()

    config = load_config(args.config)
    config.provider = "openai"
    config.model = "gpt-5.5"
    config.reasoning_effort = None
    provider = get_provider(config)

    version_dir = ROOT / "runs" / args.version
    manifest = json.loads((version_dir / "manifest.json").read_text())
    selected = {s.strip() for s in args.sites.split(",")} if args.sites else None
    entries = [entry for entry in manifest.get("screenshots", []) if selected is None or entry["name"] in selected]
    results = [evaluate_site(provider, version_dir, entry, config.max_image_dimension) for entry in entries]

    payload = {"version": args.version, "results": results}
    (version_dir / "yaml-quality-evaluation.json").write_text(json.dumps(payload, indent=2) + "\n")
    (version_dir / "yaml-quality-evaluation.md").write_text(render_markdown(args.version, results))
    print(render_markdown(args.version, results))


if __name__ == "__main__":
    main()
