#!/usr/bin/env python3
"""Run section-by-section structural grounding for one or more screenshots."""

import argparse
import difflib
import json
import os
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from screenshot_to_template.config import load_config
from screenshot_to_template.models.google import GoogleProvider
from screenshot_to_template.output import clean_markdown
from screenshot_to_template.pipeline.grounding_by_section import run as run_grounding_by_section
from screenshot_to_template.pipeline.single_shot import build_single_shot_views


PROJECT_DIR = Path(__file__).parent
RUNS_DIR = PROJECT_DIR / "runs"
SCREENSHOTS_DIR = PROJECT_DIR / "screenshots" / "best" / "use for testing"
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


def get_next_version() -> str:
    """Determine the next version number based on existing runs."""
    if not RUNS_DIR.exists():
        return "v001"
    existing = sorted(
        d.name
        for d in RUNS_DIR.iterdir()
        if d.is_dir() and d.name.startswith("v") and d.name[1:].isdigit()
    )
    if not existing:
        return "v001"
    return f"v{int(existing[-1][1:]) + 1:03d}"


def load_api_keys() -> None:
    """Load API keys from repo-local .env.local if not already set."""
    env_file = PROJECT_DIR / ".env.local"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip()
                    if key in (
                        "GEMINI_API_KEY",
                        "GOOGLE_API_KEY",
                        "ANTHROPIC_API_KEY",
                        "OPENAI_API_KEY",
                    ) and not os.environ.get(key):
                        os.environ[key] = value
    if not os.environ.get("GOOGLE_API_KEY") and os.environ.get("GEMINI_API_KEY"):
        os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]


def list_screenshots() -> list[Path]:
    """Return all test screenshots in a stable order."""
    return sorted(
        path
        for path in SCREENSHOTS_DIR.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    )


def find_screenshot(name_or_path: str) -> Path:
    """Resolve a screenshot by path or stem name."""
    candidate = Path(name_or_path)
    if candidate.exists():
        return candidate.resolve()

    matches = sorted(
        path
        for path in SCREENSHOTS_DIR.iterdir()
        if path.is_file() and path.stem == name_or_path and path.suffix.lower() in IMAGE_SUFFIXES
    )
    if not matches:
        raise FileNotFoundError(f"Could not find screenshot '{name_or_path}'.")
    if len(matches) > 1:
        raise ValueError(
            f"Multiple screenshots matched '{name_or_path}': {[p.name for p in matches]}"
        )
    return matches[0].resolve()


def load_prompt(path: Path) -> str:
    """Load a prompt file."""
    if not path.exists():
        raise FileNotFoundError(f"Missing prompt file: {path}")
    return path.read_text().strip()


def load_section_agent_bundle(version_dir: Path) -> tuple[list[tuple[str, str]] | None, str | None]:
    """Load optional multi-agent section prompts for a version."""
    agent_files = [
        ("section", version_dir / "section-agent-section-prompt.md"),
        ("container", version_dir / "section-agent-container-prompt.md"),
        ("components", version_dir / "section-agent-components-prompt.md"),
        ("text", version_dir / "section-agent-text-prompt.md"),
    ]
    existing_agents = [(name, path) for name, path in agent_files if path.exists()]
    if not existing_agents:
        return None, None

    missing = [str(path) for name, path in agent_files if not path.exists()]
    if missing:
        raise FileNotFoundError(
            "Multi-agent prompts are partially defined. Missing: " + ", ".join(missing)
        )

    merge_path = version_dir / "section-agent-merge-prompt.md"
    if not merge_path.exists():
        raise FileNotFoundError(f"Missing prompt file: {merge_path}")

    prompts = [(name, load_prompt(path)) for name, path in agent_files]
    return prompts, load_prompt(merge_path)


def ensure_placeholder_outputs(base_dir: Path) -> dict[str, str]:
    """Ensure viewer-compatible placeholder files exist for a grounding-only run."""
    base_dir.mkdir(parents=True, exist_ok=True)

    design_system_path = base_dir / "design-system.md"
    if not design_system_path.exists():
        design_system_path.write_text(
            "# Grounding-Only Run\n\n"
            "This run generated section-by-section structural grounding only.\n"
            "No design system or websites were produced in this mode.\n"
        )

    claude_path = base_dir / "site-claude.html"
    if not claude_path.exists():
        claude_path.write_text(
            "<!DOCTYPE html><html><head><meta charset=\"UTF-8\"><title>Not generated</title></head>"
            "<body><p>This was a grounding-only run. No Claude site was generated.</p></body></html>"
        )

    gemini_path = base_dir / "site-gemini.html"
    if not gemini_path.exists():
        gemini_path.write_text(
            "<!DOCTYPE html><html><head><meta charset=\"UTF-8\"><title>Not generated</title></head>"
            "<body><p>This was a grounding-only run. No Gemini site was generated.</p></body></html>"
        )

    return {
        "design_system": str(design_system_path),
        "site_claude": str(claude_path),
        "site_gemini": str(gemini_path),
    }


def update_manifest_for_grounding_run(
    version_dir: Path,
    screenshot_path: Path,
    grounding_output_dir: Path,
) -> None:
    """Create or update a minimal manifest so the viewer can include this version."""
    manifest_path = version_dir / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
    else:
        manifest = {
            "version": version_dir.name,
            "timestamp": "",
            "screenshots": [],
        }

    screenshot_dir = version_dir / screenshot_path.stem
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    screenshot_copy_path = screenshot_dir / f"screenshot{screenshot_path.suffix.lower()}"
    if not screenshot_copy_path.exists():
        shutil.copy2(screenshot_path, screenshot_copy_path)

    single_placeholders = ensure_placeholder_outputs(screenshot_dir / "single")
    sectioned_placeholders = ensure_placeholder_outputs(screenshot_dir / "sectioned")

    entry = {
        "name": screenshot_path.stem,
        "screenshot": str(screenshot_copy_path.relative_to(version_dir)),
        "single": {
            "structural_analysis": str((grounding_output_dir / "structural-analysis.md").relative_to(version_dir)),
            "design_system": str(Path(single_placeholders["design_system"]).relative_to(version_dir)),
            "site_claude": str(Path(single_placeholders["site_claude"]).relative_to(version_dir)),
            "site_gemini": str(Path(single_placeholders["site_gemini"]).relative_to(version_dir)),
        },
        "sectioned": {
            "structural_analysis": "",
            "design_system": str(Path(sectioned_placeholders["design_system"]).relative_to(version_dir)),
            "site_claude": str(Path(sectioned_placeholders["site_claude"]).relative_to(version_dir)),
            "site_gemini": str(Path(sectioned_placeholders["site_gemini"]).relative_to(version_dir)),
        },
    }

    screenshots = manifest.get("screenshots", [])
    updated = False
    for index, existing in enumerate(screenshots):
        if existing.get("name") == screenshot_path.stem:
            screenshots[index] = entry
            updated = True
            break
    if not updated:
        screenshots.append(entry)

    manifest["version"] = version_dir.name
    manifest["timestamp"] = datetime.now().isoformat()
    manifest["screenshots"] = sorted(screenshots, key=lambda item: item["name"])
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")


def regenerate_viewer() -> None:
    """Refresh the shared viewer HTML."""
    from run_pipeline import generate_viewer

    generate_viewer(RUNS_DIR, PROJECT_DIR / "viewer.html")


def normalize_markdown_for_diff(text: str) -> str:
    """Compact markdown so diffs focus on content rather than spacing noise."""
    cleaned = clean_markdown(text)
    lines = [line.rstrip() for line in cleaned.splitlines()]

    compacted: list[str] = []
    previous_blank = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if not previous_blank:
                compacted.append("")
            previous_blank = True
            continue
        compacted.append(stripped)
        previous_blank = False

    return "\n".join(compacted).strip() + "\n"


def write_diff(
    old_path: Path,
    new_path: Path,
    output_dir: Path,
    compare_version: str,
) -> Path:
    """Write normalized comparison artifacts for two grounding files."""
    old_text = old_path.read_text() if old_path.exists() else ""
    new_text = new_path.read_text() if new_path.exists() else ""

    normalized_old = normalize_markdown_for_diff(old_text)
    normalized_new = normalize_markdown_for_diff(new_text)

    normalized_old_path = output_dir / f"structural-analysis-{compare_version}-normalized.md"
    normalized_new_path = output_dir / "structural-analysis-normalized.md"
    normalized_old_path.write_text(normalized_old)
    normalized_new_path.write_text(normalized_new)

    diff_lines = difflib.unified_diff(
        normalized_old.splitlines(keepends=True),
        normalized_new.splitlines(keepends=True),
        fromfile=str(old_path),
        tofile=str(new_path),
    )
    diff_path = output_dir / f"compare-{compare_version}.diff"
    diff_path.write_text("".join(diff_lines))
    return diff_path


def find_compare_grounding_path(compare_version: str, screenshot_stem: str) -> Path | None:
    """Find the best available prior grounding file for comparison."""
    candidates = [
        RUNS_DIR / compare_version / screenshot_stem / "grounding-by-section" / "structural-analysis.md",
        RUNS_DIR / compare_version / screenshot_stem / "single" / "structural-analysis.md",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def audit_diff_with_gemini(
    screenshot_path: Path,
    previous_grounding_path: Path,
    new_grounding_path: Path,
    diff_path: Path,
    audit_prompt: str,
    output_path: Path,
) -> None:
    """Use Gemini to audit grounding changes against the screenshot."""
    provider = GoogleProvider("gemini-3.1-pro-preview")
    views = build_single_shot_views(str(screenshot_path), 2048)
    overview_b64 = views[0][1]
    additional_views = views[1:]

    user_prompt = (
        f"Previous grounding ({previous_grounding_path.name}):\n\n"
        f"{previous_grounding_path.read_text()}\n\n"
        f"New grounding ({new_grounding_path.name}):\n\n"
        f"{new_grounding_path.read_text()}\n\n"
        f"Unified diff ({diff_path.name}):\n\n"
        f"{diff_path.read_text()}"
    )
    result = provider.analyze_image(
        image_b64=overview_b64,
        system_prompt=audit_prompt,
        user_prompt=user_prompt,
        max_tokens=12288,
        additional_images=additional_views,
    )
    output_path.write_text(clean_markdown(result) + "\n")


def write_audit_summary(version_dir: Path, audit_paths: list[tuple[str, Path]]) -> None:
    """Combine per-screenshot audits into one version-level summary file."""
    lines = ["# Gemini Audit Summary", ""]
    if not audit_paths:
        lines.append("No Gemini audits were generated.")
    else:
        for name, path in audit_paths:
            lines.append(f"## {name}")
            lines.append("")
            lines.append(path.read_text().strip())
            lines.append("")
    (version_dir / "grounding-audit-summary.md").write_text("\n".join(lines).rstrip() + "\n")


def ensure_targets(args) -> list[Path]:
    """Resolve the target screenshots for this run."""
    if args.all:
        return list_screenshots()
    return [find_screenshot(args.screenshot)]


def process_screenshot(
    screenshot_path: Path,
    version_dir: Path,
    compare_version: str,
    config,
    inventory_prompt: str,
    section_prompt: str,
    merge_prompt: str,
    include_full_page_context: bool,
    ignore_cache: bool,
    section_agent_prompts: list[tuple[str, str]] | None,
    section_agent_merge_prompt: str | None,
) -> tuple[Path, Path | None]:
    """Generate one grounding artifact and its diff."""
    output_dir = version_dir / screenshot_path.stem / "grounding-by-section"
    output_dir.mkdir(parents=True, exist_ok=True)

    run_grounding_by_section(
        image_path=str(screenshot_path),
        config=config,
        inventory_prompt=inventory_prompt,
        section_prompt=section_prompt,
        merge_prompt=merge_prompt,
        include_full_page_context=include_full_page_context,
        ignore_cache=ignore_cache,
        section_agent_prompts=section_agent_prompts,
        section_agent_merge_prompt=section_agent_merge_prompt,
        output_dir=str(output_dir),
    )

    new_grounding_path = output_dir / "structural-analysis.md"
    update_manifest_for_grounding_run(version_dir, screenshot_path, output_dir)

    compare_path = find_compare_grounding_path(compare_version, screenshot_path.stem)
    diff_path = None
    if compare_path:
        diff_path = write_diff(compare_path, new_grounding_path, output_dir, compare_version)

    return new_grounding_path, diff_path


def process_screenshot_with_retries(
    screenshot_path: Path,
    version_dir: Path,
    compare_version: str,
    config,
    inventory_prompt: str,
    section_prompt: str,
    merge_prompt: str,
    include_full_page_context: bool,
    ignore_cache: bool,
    section_agent_prompts: list[tuple[str, str]] | None,
    section_agent_merge_prompt: str | None,
    max_attempts: int = 6,
) -> tuple[Path, Path | None]:
    """Process one screenshot with resume-friendly retries."""
    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            if config.verbose and attempt > 1:
                print(
                    f"Retrying {screenshot_path.stem} (attempt {attempt}/{max_attempts})...",
                    file=sys.stderr,
                )
            return process_screenshot(
                screenshot_path=screenshot_path,
                version_dir=version_dir,
                compare_version=compare_version,
                config=config,
                inventory_prompt=inventory_prompt,
                section_prompt=section_prompt,
                merge_prompt=merge_prompt,
                include_full_page_context=include_full_page_context,
                ignore_cache=ignore_cache,
                section_agent_prompts=section_agent_prompts,
                section_agent_merge_prompt=section_agent_merge_prompt,
            )
        except Exception as exc:
            last_error = exc
            if attempt >= max_attempts:
                break
            time.sleep(min(45, 8 * attempt))
    assert last_error is not None
    raise last_error


def run_audit_with_retries(
    screenshot_path: Path,
    previous_grounding_path: Path,
    new_grounding_path: Path,
    diff_path: Path,
    audit_prompt: str,
    output_path: Path,
    verbose: bool,
    max_attempts: int = 5,
) -> None:
    """Run the Gemini audit with retries."""
    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            if verbose and attempt > 1:
                print(
                    f"Retrying Gemini audit for {screenshot_path.stem} (attempt {attempt}/{max_attempts})...",
                    file=sys.stderr,
                )
            audit_diff_with_gemini(
                screenshot_path=screenshot_path,
                previous_grounding_path=previous_grounding_path,
                new_grounding_path=new_grounding_path,
                diff_path=diff_path,
                audit_prompt=audit_prompt,
                output_path=output_path,
            )
            return
        except Exception as exc:
            last_error = exc
            if attempt >= max_attempts:
                break
            time.sleep(min(45, 8 * attempt))
    assert last_error is not None
    raise last_error


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate structural grounding by analyzing one detected section at a time."
    )
    parser.add_argument("--version", default=get_next_version(), help="Version folder under runs/")
    parser.add_argument("--screenshot", help="Screenshot stem or full path")
    parser.add_argument("--all", action="store_true", help="Run against all test screenshots")
    parser.add_argument(
        "--compare-version",
        default="v013",
        help="Existing version to diff against after generating the new grounding file",
    )
    parser.add_argument("--config", help="Optional YAML config override")
    parser.add_argument(
        "--crop-only",
        action="store_true",
        help="Ground each section using only its crop rather than additional full-page visual context",
    )
    parser.add_argument(
        "--audit",
        action="store_true",
        help="Use Gemini to audit each diff against the screenshot and save markdown reports",
    )
    parser.add_argument(
        "--ignore-cache",
        action="store_true",
        help="Ignore any existing cached section-grounding files for this version and rerun section analysis",
    )
    parser.add_argument("--verbose", action="store_true", help="Print progress to stderr")
    args = parser.parse_args()

    if not args.all and not args.screenshot:
        parser.error("Provide --screenshot or use --all.")

    load_api_keys()

    version_dir = RUNS_DIR / args.version
    version_dir.mkdir(parents=True, exist_ok=True)
    inventory_prompt = load_prompt(version_dir / "section-inventory-prompt.md")
    section_prompt = load_prompt(version_dir / "section-grounding-prompt.md")
    merge_prompt = load_prompt(version_dir / "grounding-merge-prompt.md")
    section_agent_prompts, section_agent_merge_prompt = load_section_agent_bundle(version_dir)
    audit_prompt = ""
    audit_prompt_path = version_dir / "grounding-audit-prompt.md"
    if args.audit and audit_prompt_path.exists():
        audit_prompt = load_prompt(audit_prompt_path)

    config = load_config(args.config)
    config.verbose = args.verbose
    targets = ensure_targets(args)

    audit_outputs: list[tuple[str, Path]] = []

    for screenshot_path in targets:
        if args.verbose:
            print(f"=== Processing {screenshot_path.stem} ===", file=sys.stderr)

        new_grounding_path, diff_path = process_screenshot_with_retries(
            screenshot_path=screenshot_path,
            version_dir=version_dir,
            compare_version=args.compare_version,
            config=config,
            inventory_prompt=inventory_prompt,
            section_prompt=section_prompt,
            merge_prompt=merge_prompt,
            include_full_page_context=not args.crop_only,
            ignore_cache=args.ignore_cache,
            section_agent_prompts=section_agent_prompts,
            section_agent_merge_prompt=section_agent_merge_prompt,
        )

        print(f"Generated grounding file: {new_grounding_path}")
        if diff_path:
            print(f"Comparison diff: {diff_path}")
        else:
            print(
                "No comparison file found for: "
                f"{args.compare_version}/{screenshot_path.stem}"
            )

        if args.audit and audit_prompt and diff_path:
            compare_path = find_compare_grounding_path(args.compare_version, screenshot_path.stem)
            if not compare_path:
                raise FileNotFoundError(
                    f"No comparison grounding file found for {args.compare_version}/{screenshot_path.stem}"
                )
            audit_path = new_grounding_path.parent / f"grounding-audit-{args.compare_version}-gemini.md"
            if args.verbose:
                print(f"Auditing {screenshot_path.stem} with Gemini...", file=sys.stderr)
            run_audit_with_retries(
                screenshot_path=screenshot_path,
                previous_grounding_path=compare_path,
                new_grounding_path=new_grounding_path,
                diff_path=diff_path,
                audit_prompt=audit_prompt,
                output_path=audit_path,
                verbose=args.verbose,
            )
            audit_outputs.append((screenshot_path.stem, audit_path))
            print(f"Gemini audit: {audit_path}")

    if args.audit:
        write_audit_summary(version_dir, audit_outputs)
        print(f"Gemini audit summary: {version_dir / 'grounding-audit-summary.md'}")

    regenerate_viewer()
    print(f"Updated viewer: {PROJECT_DIR / 'viewer.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
