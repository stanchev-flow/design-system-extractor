#!/usr/bin/env python3
"""Run the normal pipeline with only design-system synthesis swapped to additive crops."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import run_pipeline


PROJECT_DIR = Path(__file__).parent
RUNS_DIR = PROJECT_DIR / "runs"
DEFAULT_SCREENSHOTS_DIR = PROJECT_DIR / "screenshots" / "use for testing"
ADDITIVE_VIEWER_PATH = PROJECT_DIR / "viewer-additive.html"
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}

SECTION_GROUNDING_PROMPT_FILES = (
    "section-inventory-prompt.md",
    "section-grounding-prompt.md",
    "grounding-merge-prompt.md",
    "section-transition-prompt.md",
    "full-page-review-prompt.md",
)


def find_screenshot(name_or_path: str) -> Path:
    candidate = Path(name_or_path)
    if candidate.exists():
        return candidate.resolve()

    matches = sorted(
        path
        for path in DEFAULT_SCREENSHOTS_DIR.iterdir()
        if path.is_file()
        and path.stem == name_or_path
        and path.suffix.lower() in IMAGE_SUFFIXES
    )
    if not matches:
        raise FileNotFoundError(f"Could not find screenshot '{name_or_path}'.")
    if len(matches) > 1:
        raise ValueError(f"Multiple screenshots matched '{name_or_path}': {[p.name for p in matches]}")
    return matches[0].resolve()


def latest_normal_run_with_sections(screenshot_stem: str, exclude_version: str) -> str | None:
    versions = sorted(
        (
            path.name
            for path in RUNS_DIR.iterdir()
            if path.is_dir()
            and path.name.startswith("v")
            and path.name[1:].isdigit()
            and path.name != exclude_version
        ),
        reverse=True,
    )
    for version in versions:
        if (RUNS_DIR / version / screenshot_stem / "single" / "sections.json").exists():
            return version
    return None


def copy_section_grounding_prompts(version_dir: Path, source_version: str) -> None:
    source_dir = RUNS_DIR / source_version
    missing: list[str] = []
    for filename in SECTION_GROUNDING_PROMPT_FILES:
        source_path = source_dir / filename
        if source_path.exists():
            shutil.copy2(source_path, version_dir / filename)
        elif filename in {"section-inventory-prompt.md", "section-grounding-prompt.md", "grounding-merge-prompt.md"}:
            missing.append(str(source_path))
    if missing:
        raise FileNotFoundError(
            "Cannot run additive-crops through the normal section pipeline; missing prompt files: "
            + ", ".join(missing)
        )


def copy_clean_input_to_temp(screenshot_path: Path, temp_dir: Path) -> Path:
    copied_screenshot = temp_dir / screenshot_path.name
    shutil.copy2(screenshot_path, copied_screenshot)
    source_html = screenshot_path.with_suffix(".html")
    if source_html.exists():
        shutil.copy2(source_html, temp_dir / source_html.name)
    return copied_screenshot


def write_run_note(version_dir: Path, source_version: str) -> None:
    changes_path = version_dir / "changes.md"
    existing = changes_path.read_text().rstrip() if changes_path.exists() else f"# {version_dir.name} Changes"
    note = (
        f"- Ran the normal pipeline with `--design-system-strategy additive-crops`, "
        f"reusing normal section artifacts from `{source_version}` so only design-system synthesis differs."
    )
    if note not in existing:
        changes_path.write_text(existing + "\n" + note + "\n")


def generate_single_version_additive_viewer(version_dir: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="additive-viewer-runs-") as temp_root:
        temp_runs = Path(temp_root)
        os.symlink(version_dir.resolve(), temp_runs / version_dir.name)
        run_pipeline.generate_viewer(temp_runs, ADDITIVE_VIEWER_PATH)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run the normal screenshot-to-template pipeline, changing only the "
            "design-system synthesis step to additive crop integration."
        )
    )
    parser.add_argument("--version", default=None, help="Version label (default: auto-increment)")
    parser.add_argument("--screenshot", default="clean", help="Screenshot path or stem under screenshots/use for testing")
    parser.add_argument(
        "--reuse-analysis-from",
        default=None,
        help="Normal run version whose section artifacts should be reused. Defaults to latest run with matching sections.",
    )
    parser.add_argument("--provider", default=None, help="Optional analysis provider override")
    parser.add_argument("--model", default=None, help="Optional analysis model override")
    parser.add_argument("--reasoning-effort", default=None, help="Optional analysis reasoning override")
    parser.add_argument("--config", default=None, help="Optional config YAML")
    args = parser.parse_args()

    screenshot_path = find_screenshot(args.screenshot)
    version = args.version or run_pipeline.get_next_version()
    version_dir = RUNS_DIR / version
    version_dir.mkdir(parents=True, exist_ok=True)

    source_version = args.reuse_analysis_from or latest_normal_run_with_sections(screenshot_path.stem, version)
    if not source_version:
        raise FileNotFoundError(
            f"No prior normal pipeline sections found for `{screenshot_path.stem}`. "
            "Run the normal pipeline once first, or pass --reuse-analysis-from."
        )

    copy_section_grounding_prompts(version_dir, source_version)
    (version_dir / "display-name.txt").write_text(f"{version} additive-crops\n")
    if args.provider:
        (version_dir / "analysis-provider.txt").write_text(args.provider + "\n")
    if args.model:
        (version_dir / "analysis-model.txt").write_text(args.model + "\n")
    if args.reasoning_effort is not None:
        (version_dir / "analysis-reasoning-effort.txt").write_text(args.reasoning_effort + "\n")

    with tempfile.TemporaryDirectory(prefix="additive-clean-input-") as temp_root:
        temp_screenshot_dir = Path(temp_root)
        copy_clean_input_to_temp(screenshot_path, temp_screenshot_dir)
        run_pipeline.run_pipeline(
            version=version,
            screenshots_dir=temp_screenshot_dir,
            config_path=args.config,
            design_system_strategy="additive-crops",
            reuse_analysis_from=source_version,
        )

    write_run_note(version_dir, source_version)
    generate_single_version_additive_viewer(version_dir)
    print(f"Done. Normal-format additive viewer: {ADDITIVE_VIEWER_PATH}")
    print(f"Run output: {version_dir}")


if __name__ == "__main__":
    main()
