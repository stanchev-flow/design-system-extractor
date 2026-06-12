#!/usr/bin/env python3
"""Run a plain section-understanding bakeoff across multiple vision models."""

import argparse
import json
import os
from pathlib import Path

from screenshot_to_template.models.anthropic import AnthropicProvider
from screenshot_to_template.models.google import GoogleProvider
from screenshot_to_template.models.openai import OpenAIProvider
from screenshot_to_template.pipeline.single_shot import load_and_encode_image


SYSTEM_PROMPT = (
    "You are analyzing a website screenshot. "
    "Explain the visually distinct sections that exist on the page from top to bottom. "
    "Do not estimate coordinates or cropping bounds. "
    "Just describe what sections appear to exist and why each feels like its own section."
)

USER_PROMPT = (
    "Look at this single full-page website screenshot and list the sections you think the page contains, "
    "from top to bottom. For each section, give:\n"
    "1. a short label\n"
    "2. one or two sentences explaining what is visible in that section\n"
    "3. one sentence explaining why it appears to be a separate section\n\n"
    "Keep this focused on the visible layout and content blocks. "
    "Do not mention pixel coordinates or crop lines."
)


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


def grade_output(text: str) -> tuple[str, list[str]]:
    lower = text.lower()
    checks = [
        ("navigation", any(word in lower for word in ("navigation", "nav", "header"))),
        ("hero", "hero" in lower),
        ("logo/client section", any(word in lower for word in ("logo", "logos", "client", "partner"))),
        ("mid-page feature/product sections", any(word in lower for word in ("feature", "features", "product", "products", "platform", "solution", "solutions"))),
        ("cta/footer ending", any(word in lower for word in ("cta", "call to action", "footer"))),
    ]
    score = sum(1 for _, ok in checks if ok)
    if score == 5:
        grade = "A"
    elif score == 4:
        grade = "B"
    elif score == 3:
        grade = "C"
    else:
        grade = "D"
    notes = [f"{label}: {'yes' if ok else 'no'}" for label, ok in checks]
    return grade, notes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("screenshot", help="Path to the screenshot to analyze")
    parser.add_argument("output_dir", help="Directory to save raw outputs and summary")
    args = parser.parse_args()

    load_shared_env()

    screenshot_path = Path(args.screenshot)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    image_b64 = load_and_encode_image(str(screenshot_path), max_dimension=4096)

    models = [
        ("openai", "gpt-5.5", OpenAIProvider("gpt-5.5")),
        ("anthropic", "claude-sonnet-4-20250514", AnthropicProvider("claude-sonnet-4-20250514")),
        ("google", "gemini-3-pro-preview", GoogleProvider("gemini-3-pro-preview")),
    ]

    summary = []
    for provider_name, model_name, provider in models:
        model_dir = output_dir / f"{provider_name}-{model_name.replace('.', '-').replace('/', '-')}"
        model_dir.mkdir(exist_ok=True)
        try:
            raw = provider.analyze_image(
                image_b64=image_b64,
                system_prompt=SYSTEM_PROMPT,
                user_prompt=USER_PROMPT,
                max_tokens=4096,
            )
            grade, notes = grade_output(raw)
            (model_dir / "raw.md").write_text(raw.strip() + "\n")
            (model_dir / "grade.json").write_text(
                json.dumps(
                    {
                        "provider": provider_name,
                        "model": model_name,
                        "grade": grade,
                        "check_notes": notes,
                    },
                    indent=2,
                )
                + "\n"
            )
            summary.append(
                {
                    "provider": provider_name,
                    "model": model_name,
                    "ok": True,
                    "grade": grade,
                    "check_notes": notes,
                    "raw_path": str((model_dir / "raw.md").relative_to(output_dir)),
                }
            )
        except Exception as exc:
            (model_dir / "error.txt").write_text(f"{type(exc).__name__}: {exc}\n")
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
