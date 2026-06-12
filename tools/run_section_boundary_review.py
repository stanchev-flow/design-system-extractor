#!/usr/bin/env python3
"""Ask independent vision models to review section-boundary quality."""

import argparse
import json
import os
from pathlib import Path

from PIL import Image, ImageDraw

from screenshot_to_template.models.anthropic import AnthropicProvider
from screenshot_to_template.models.google import GoogleProvider
from screenshot_to_template.pipeline.single_shot import load_and_encode_image


SYSTEM_PROMPT = """\
You are an independent reviewer evaluating section-boundary quality on a website screenshot.

You are not the model that generated the section boundaries.
Your job is to inspect the original screenshot and a second overlay image that draws proposed section boundary lines.

Focus on whether the lines fall in the correct vertical gaps between sections.

Rules:
- Judge only what is visually supported by the images.
- Pay special attention to cuts that appear to run through headings, cards, images, buttons, forms, or section backgrounds.
- Prefer concrete findings over vague praise.
- If a line seems slightly off but still inside a safe gap, say so.
- If a line appears to split a section or clip content, call it out clearly.
- Keep the response concise and complete.
"""

USER_PROMPT_TEMPLATE = """\
Review these proposed section boundaries for the attached website screenshot.

Image 1 is the original screenshot.
Image 2 is the same screenshot with proposed section-boundary lines drawn across it in red.

The proposed sections are:
{sections_json}

If available, the detector's text understanding of the sections was:
{inventory_text}

Write exactly these five short sections:
1. Overall verdict
2. Strongest correct boundaries
3. Problematic boundaries
4. Overall letter grade from A to F
5. One short recommendation

Keep the full response under 250 words.
"""


def load_shared_env() -> None:
    env_file = Path(__file__).resolve().parents[1] / ".env.local"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip()
                if key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY", "GEMINI_API_KEY"):
                    os.environ.setdefault(key, value)
    if not os.environ.get("GOOGLE_API_KEY") and os.environ.get("GEMINI_API_KEY"):
        os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]


def render_overlay(screenshot_path: Path, sections_path: Path, output_path: Path) -> None:
    img = Image.open(screenshot_path).convert("RGB")
    draw = ImageDraw.Draw(img)
    sections = json.loads(sections_path.read_text())

    for section in sections:
        y = int(section["y_start"])
        draw.line((0, y, img.width, y), fill=(255, 59, 48), width=4)
    last_end = int(sections[-1]["y_end"])
    draw.line((0, last_end, img.width, last_end), fill=(255, 59, 48), width=4)
    img.save(output_path)


def response_looks_incomplete(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return True
    required_markers = [
        "overall verdict",
        "strongest",
        "problematic",
        "grade",
        "recommendation",
    ]
    lower = stripped.lower()
    if not all(marker in lower for marker in required_markers):
        return True
    if stripped.endswith(("(", "-", "*", "•", ":")):
        return True
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("screenshot", help="Path to the original screenshot")
    parser.add_argument("artifacts_dir", help="Sectioned artifact directory to review")
    parser.add_argument("output_dir", help="Directory to save the review outputs")
    args = parser.parse_args()

    load_shared_env()

    screenshot_path = Path(args.screenshot)
    artifacts_dir = Path(args.artifacts_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    sections_path = artifacts_dir / "sections.json"
    inventory_path = artifacts_dir / "section-inventory.md"
    overlay_path = output_dir / "section-overlay.png"
    render_overlay(screenshot_path, sections_path, overlay_path)

    screenshot_b64 = load_and_encode_image(str(screenshot_path), max_dimension=4096)
    overlay_b64 = load_and_encode_image(str(overlay_path), max_dimension=4096)
    sections_json = sections_path.read_text().strip()
    inventory_text = inventory_path.read_text().strip() if inventory_path.exists() else "Unavailable."
    user_prompt = USER_PROMPT_TEMPLATE.format(
        sections_json=sections_json,
        inventory_text=inventory_text,
    )

    reviewers = [
        ("anthropic", "claude-sonnet-4-20250514", AnthropicProvider("claude-sonnet-4-20250514")),
        ("google", "gemini-3-pro-preview", GoogleProvider("gemini-3-pro-preview")),
    ]

    summary = []
    for provider_name, model_name, provider in reviewers:
        reviewer_dir = output_dir / f"{provider_name}-{model_name.replace('.', '-').replace('/', '-')}"
        reviewer_dir.mkdir(exist_ok=True)
        try:
            report = ""
            max_tokens = 8192 if provider_name == "google" else 1200
            prompts = [
                user_prompt,
                user_prompt + "\n\nBe brief. Do not exceed 250 words.",
            ]
            for prompt in prompts:
                report = provider.analyze_image(
                    image_b64=screenshot_b64,
                    system_prompt=SYSTEM_PROMPT,
                    user_prompt=prompt,
                    max_tokens=max_tokens,
                    additional_images=[("overlay", overlay_b64)],
                )
                if not response_looks_incomplete(report):
                    break
            (reviewer_dir / "report.md").write_text(report.strip() + "\n")
            summary.append(
                {
                    "provider": provider_name,
                    "model": model_name,
                    "ok": True,
                    "complete": not response_looks_incomplete(report),
                    "report_path": str((reviewer_dir / "report.md").relative_to(output_dir)),
                }
            )
        except Exception as exc:
            (reviewer_dir / "error.txt").write_text(f"{type(exc).__name__}: {exc}\n")
            summary.append(
                {
                    "provider": provider_name,
                    "model": model_name,
                    "ok": False,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")


if __name__ == "__main__":
    main()
