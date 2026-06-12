#!/usr/bin/env python3
"""Run an HTML/CSS-only live-site grounding pipeline."""

from __future__ import annotations

import argparse
import base64
import concurrent.futures
import json
import shutil
from datetime import datetime
from pathlib import Path

from run_pipeline import (
    PROJECT_DIR,
    RUNS_DIR,
    _build_viewer_html,
    generate_website_html,
    html_document_is_complete,
    image_to_data_uri,
    load_api_keys,
    log,
)
from screenshot_to_template.config import load_config
from screenshot_to_template.live_site import build_dom_outline, ensure_live_site_html_snapshot
from screenshot_to_template.models import get_provider
from screenshot_to_template.output import clean_markdown
from screenshot_to_template.source_colors import (
    extract_source_colors,
    render_source_color_report,
    write_source_color_artifacts,
)


LIVE_SOURCE_GROUNDING_PROMPT = """\
You are an expert UI layout analyst. Analyze a live marketing website using only its DOM outline and CSS source data, then write one grounded structural markdown document for the whole page.

Your job in this step is interpretation, not code transcription. Convert DOM and CSS evidence into human-readable layout observations that a frontend model can use.

## Core mental model

Assume the page is composed like this:

`.page canvas > section wrapper > container > content > large module > nested components`

Important distinctions:
- `section wrapper`: the outer band or zone that defines a section's visible width and surface
- `container`: the centered max-width region holding the main content
- `large module`: a full-container-width block inside a section that uses a different background from the section background and usually contains the section's main heading/content inside the module
- `nested components`: buttons, cards, pills, badges, inputs, icons, dividers, media frames, banners, marquees, nav items, and other non-text UI pieces that sit inside the section or inside a large module
- `internal divider`: a line or separator inside a section or component; do not confuse this with a section boundary

## Core rules

- Do not mention screenshots, image uncertainty, OCR, or visual guessing.
- Use only the provided live DOM outline and source CSS style report.
- Keep section order faithful to the actual page flow in the DOM outline.
- Interpret class names, selectors, utility tokens, CSS variables, and `calc(...)` expressions into plain-English meaning whenever possible.
- Do not copy raw DOM paths, selectors, utility-class strings, repeated node names, hashed class names, or custom-property identifiers into the grounding unless there is no better plain-English description.
- Do not output raw snippets like `div.relative.mx-auto.w-full.max-w-5xl`, `flex items-center justify-between`, `LogosMarquee_item__rRtnM`, or `var(--_typography---heading-sizes--h1)`.
- If the CSS implies a concrete rendered meaning, state that meaning directly. Example: say `centered max-width container` instead of utility classes, and say `horizontal split layout with spaced ends` instead of flex utility tokens.
- When typography or spacing is expressed through variables or `calc(...)`, resolve it into a real rendered value when the source report supports that. If the exact rendered value is still unclear, describe it semantically instead of copying the code expression.
- Never repeat opaque variable names, generated class names, or emoji-based custom property names in the final grounding.
- When you include explicit color, gradient, font-family, font-size, font-weight, line-height, or letter-spacing values, they must be supported by the source CSS style report.
- If an exact explicit value is not clearly supported, use semantic wording instead of invented precision.
- Focus on structure, layout behavior, component patterns, repeated modules, and text hierarchy.
- Use `None` only when a subsection genuinely has no visible evidence.
- Return only the markdown document.

## Output requirements

Follow this exact structure.

# Structural Analysis

## Section Inventory

- List the page sections in order as a numbered list with short descriptive labels.

## Section 1: [generic role]

### Section
- **Section role:** hero, navigation, logo band, feature grid, testimonial block, CTA, footer, or similar
- **Section width:** full-bleed, inset, mixed, or unclear
- **Section background:** describe the rendered background in plain language, using exact supported values only when they are genuinely useful
- **Boundary / transition cues:** describe whether the section appears hard-cut, softly transitioned, divider-led, background-continuous, or unclear

### Container
- **Container pattern:** centered max-width, full-width content, split wrapper, repeated narrow modules, or similar
- **Approximate width behavior:** describe the practical width behavior in human terms
- **Alignment model:** left-aligned, centered, edge-balanced, mixed, or unclear

### Content layout
- **Primary layout pattern:** single-column stack, centered stack, two-column split, alternating rows, card grid, marquee/list band, mixed, or similar
- **Hierarchy shape:** describe how headings, body text, media, and supporting modules are arranged
- **Spacing rhythm:** describe the spacing between major pieces in practical terms

### Nested components
- List only non-text components that are clearly supported by the DOM/CSS evidence.
- This includes large modules, nav bars, dropdowns, buttons, cards, banners, marquees, pills/badges, inputs, icons, dividers, media frames, and similar UI pieces.
- For each visible component, create a mini-heading such as `#### Navigation`, `#### Large module`, `#### Card`, `#### Button`, `#### Logo marquee`, or another accurate component name.
- Under each component heading, use:
  - **Role:** what the component does in the section
  - **Structure:** how it is arranged
  - **Surface / treatment:** background, border, divider, or elevation treatment in plain language
  - **Notes:** any especially important implementation-facing observations

### Primary text
- This section is only for headings, body copy, and text links.
- For each visible primary text treatment, create a mini-heading such as `#### Heading`, `#### Body copy`, or `#### Text link`.
- Under each text heading, use:
  - **Content:** the actual text when it is available and important
  - **Scale role:** H1, H2, H3, body, supporting, text link, footer/supporting, or unclear
  - **Typography:** describe the rendered typography in human terms, using exact supported values only when they are clearly meaningful
  - **Style notes:** any notable emphasis, casing, density, or rhythm

### Visual direction
- **Graphic / interface direction:** describe non-photographic visual treatments such as diagrams, product UI, logos, illustrations, icons, patterns, or decorative graphics
- **Surface / mood notes:** describe the overall compositional feel in implementation-friendly terms

### Ambiguities
- List anything that is genuinely difficult to infer from the DOM/CSS evidence alone, or `- None`.
"""


def get_previous_prompt(version_name: str, filename: str) -> str | None:
    version_dir = RUNS_DIR / version_name
    candidates = sorted(
        [
            path for path in RUNS_DIR.iterdir()
            if path.is_dir() and path.name != version_name and path.name.startswith("v")
        ],
        key=lambda item: item.name,
        reverse=True,
    )
    for candidate in candidates:
        prompt_path = candidate / filename
        if prompt_path.exists():
            return prompt_path.read_text().strip()
    return None


def ensure_version_files(version_name: str) -> Path:
    version_dir = RUNS_DIR / version_name
    version_dir.mkdir(parents=True, exist_ok=True)

    for filename in ("website-gen-prompt.md",):
        path = version_dir / filename
        if path.exists():
            continue
        previous = get_previous_prompt(version_name, filename)
        if previous:
            path.write_text(previous + "\n")

    prompt_path = version_dir / "live-source-grounding-prompt.md"
    if not prompt_path.exists():
        prompt_path.write_text(LIVE_SOURCE_GROUNDING_PROMPT + "\n")

    site_source_path = version_dir / "site-generation-source.txt"
    if not site_source_path.exists():
        site_source_path.write_text("grounding\n")

    learnings_path = version_dir / "learnings.md"
    if not learnings_path.exists():
        learnings_path.write_text(
            "# Live Source Learnings\n\n"
            "- This run uses live DOM and CSS only for grounding, without image analysis.\n"
        )

    return version_dir


def _load_live_source_version_payload(version_dir: Path) -> dict:
    manifest = json.loads((version_dir / "manifest.json").read_text())
    items = []
    for entry in manifest["screenshots"]:
        screenshot_file = version_dir / entry["screenshot"]
        single = entry["single"]
        structural_rel = single["structural_analysis"]
        design_rel = single.get("design_system", "")
        design_file = version_dir / design_rel if design_rel else None
        item = {
            "name": entry["name"],
            "screenshot_uri": image_to_data_uri(screenshot_file) if screenshot_file.exists() else "",
            "single": {
                "design_system": design_file.read_text() if design_file and design_file.exists() else "",
                "structural_analysis": (version_dir / structural_rel).read_text(),
                "claude_html": (version_dir / single["site_claude"]).read_text(),
                "gemini_html": (version_dir / single["site_gemini"]).read_text(),
                "gpt54_html": (version_dir / single["site_gpt54"]).read_text(),
                "ds_path": str(design_file.resolve()) if design_file and design_file.exists() else "",
                "structural_path": str((version_dir / structural_rel).resolve()),
            },
            "gpt54_direct_html": "<html><body><p>Not available for this pipeline.</p></body></html>",
        }
        items.append(item)

    return {
        "timestamp": manifest.get("timestamp", ""),
        "structural_analysis_prompt": (version_dir / "live-source-grounding-prompt.md").read_text(),
        "system_prompt": "",
        "website_prompt": (version_dir / "website-gen-prompt.md").read_text() if (version_dir / "website-gen-prompt.md").exists() else "",
        "grounding_sync_prompt": "",
        "site_style_sync_prompt": "",
        "screenshot_direct_prompt": "",
        "learnings": (version_dir / "learnings.md").read_text() if (version_dir / "learnings.md").exists() else "",
        "has_gpt54_direct": False,
        "items": items,
    }


def render_viewer(version_name: str, output_path: Path) -> None:
    live_source_dirs = sorted(
        [
            path for path in RUNS_DIR.iterdir()
            if path.is_dir()
            and path.name.startswith("v")
            and path.name.endswith("-live-source")
            and (path / "manifest.json").exists()
        ],
        key=lambda item: item.name,
    )
    if not live_source_dirs:
        raise FileNotFoundError("No live-source runs with manifest.json were found.")

    version_data = {
        path.name: _load_live_source_version_payload(path)
        for path in live_source_dirs
    }
    data_b64 = base64.b64encode(json.dumps(version_data).encode("utf-8")).decode("ascii")
    html = _build_viewer_html([path.name for path in live_source_dirs], data_b64)
    html = html.replace(
        "<title>Design System Pipeline Viewer</title>",
        "<title>Design System Pipeline Viewer - Live Source</title>",
        1,
    )
    html = html.replace(
        "let currentMdArtifact = 'design-system';",
        "let currentMdArtifact = 'grounding';",
        1,
    )
    html = html.replace(
        """function renderMdTabs() {
  return `<div class="cell-tab-group" role="tablist" aria-label="Markdown view selector">
    <button
      class="cell-tab"
      type="button"
      role="tab"
      aria-selected="false"
      data-tab="grounding"
      tabindex="-1"
      onclick="setMdArtifact('grounding')"
      onkeydown="handleMdTabKeydown(event)"
    >Grounding</button>
    <button
      class="cell-tab"
      type="button"
      role="tab"
      aria-selected="false"
      data-tab="design-system"
      tabindex="-1"
      onclick="setMdArtifact('design-system')"
      onkeydown="handleMdTabKeydown(event)"
    >Design system</button>
  </div>`;
}""",
        """function renderMdTabs() {
  return '';
}""",
        1,
    )
    html = html.replace("<span>Output Docs</span>", "<span>Grounding</span>")
    html = html.replace(">Screenshot</div>", ">Screenshot of Live Site</div>")
    output_path.write_text(html)


def generate_source_only_grounding(
    dom_outline: str,
    source_style_report: str,
    prompt_text: str,
    config_path: str | None,
) -> str:
    config = load_config(config_path)
    config.provider = "openai"
    config.model = "gpt-5.5"
    config.max_tokens = 16384
    provider = get_provider(config)
    prompt = (
        "## Live DOM Outline\n\n"
        f"{dom_outline}\n\n"
        "## Source CSS Styles\n\n"
        f"{source_style_report}"
    )
    result = provider.text_query(
        system_prompt=prompt_text,
        user_prompt=prompt,
        max_tokens=config.max_tokens,
    )
    return clean_markdown(result)


def generate_site_with_retry(
    generation_input: str,
    provider_name: str,
    output_path: Path,
    website_prompt: str,
) -> None:
    last_error: Exception | None = None
    for _ in range(2):
        try:
            html = generate_website_html(
                generation_input,
                provider_name,
                website_prompt=website_prompt,
                generation_label="grounding",
            )
            if not html_document_is_complete(html):
                raise ValueError("Generated HTML was incomplete or truncated")
            output_path.write_text(html)
            return
        except Exception as exc:  # pragma: no cover - model failures are run-specific
            last_error = exc
    output_path.write_text(f"<html><body><h1>Error</h1><p>{last_error}</p></body></html>")


def process_item(
    screenshot_path: Path,
    version_dir: Path,
    config_path: str | None,
    website_prompt: str,
    grounding_prompt: str,
) -> dict:
    name = screenshot_path.stem
    item_dir = version_dir / name
    single_dir = item_dir / "single"
    single_dir.mkdir(parents=True, exist_ok=True)

    url, source_html_path = ensure_live_site_html_snapshot(screenshot_path)

    dest_screenshot = item_dir / f"screenshot{screenshot_path.suffix}"
    shutil.copy2(screenshot_path, dest_screenshot)

    dest_source_html = single_dir / "source.html"
    shutil.copy2(source_html_path, dest_source_html)

    extracted_source_styles = extract_source_colors(dest_source_html)
    write_source_color_artifacts(single_dir, extracted_source_styles)
    source_style_report = render_source_color_report(extracted_source_styles)

    html_text = dest_source_html.read_text(errors="ignore")
    dom_outline = build_dom_outline(html_text, url=url)
    (single_dir / "dom-outline.md").write_text(dom_outline)

    grounding = generate_source_only_grounding(
        dom_outline=dom_outline,
        source_style_report=source_style_report,
        prompt_text=grounding_prompt,
        config_path=config_path,
    )
    structural_path = single_dir / "structural-analysis.md"
    structural_path.write_text(grounding.strip() + "\n")
    for obsolete_path in (
        single_dir / "structural-analysis.pre-source-sync.md",
        single_dir / "design-system.pre-color-sync.md",
        single_dir / "design-system.md",
    ):
        if obsolete_path.exists():
            obsolete_path.unlink()

    generation_input = grounding.strip() + "\n"
    (single_dir / "site-generation-input.md").write_text(generation_input)

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        futures = [
            pool.submit(
                generate_site_with_retry,
                generation_input,
                provider_name,
                single_dir / filename,
                website_prompt,
            )
            for provider_name, filename in (
                ("claude", "site-claude.html"),
                ("gemini", "site-gemini.html"),
                ("gpt54", "site-gpt54.html"),
            )
        ]
        for future in futures:
            future.result()

    return {
        "name": name,
        "screenshot": str(dest_screenshot.relative_to(version_dir)),
        "single": {
            "structural_analysis": str(structural_path.relative_to(version_dir)),
            "site_claude": str((single_dir / "site-claude.html").relative_to(version_dir)),
            "site_gemini": str((single_dir / "site-gemini.html").relative_to(version_dir)),
            "site_gpt54": str((single_dir / "site-gpt54.html").relative_to(version_dir)),
        },
        "site_gpt54_direct": "",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a DOM/CSS-only live-site pipeline")
    parser.add_argument("--version", required=True, help="Version label for the live-source run")
    parser.add_argument("--screenshots-dir", required=True, help="Directory containing screenshot inputs")
    parser.add_argument("--config", default=None, help="Optional config override")
    parser.add_argument("--viewer-output", default="viewer-live-site.html", help="Viewer output path")
    args = parser.parse_args()

    load_api_keys()

    version_dir = ensure_version_files(args.version)
    screenshots_dir = Path(args.screenshots_dir)
    screenshot_files = sorted(
        [
            path for path in screenshots_dir.iterdir()
            if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
        ]
    )
    if not screenshot_files:
        raise SystemExit(f"No screenshots found in {screenshots_dir}")

    grounding_prompt = (version_dir / "live-source-grounding-prompt.md").read_text().strip()
    website_prompt = (version_dir / "website-gen-prompt.md").read_text().strip() if (version_dir / "website-gen-prompt.md").exists() else ""

    manifest = {
        "version": args.version,
        "timestamp": datetime.now().isoformat(),
        "screenshots": [],
    }

    for screenshot_path in screenshot_files:
        log(f"[live-source] {screenshot_path.stem} — starting")
        entry = process_item(
            screenshot_path=screenshot_path,
            version_dir=version_dir,
            config_path=args.config,
            website_prompt=website_prompt,
            grounding_prompt=grounding_prompt,
        )
        manifest["screenshots"].append(entry)
        log(f"[live-source] {screenshot_path.stem} — complete")

    manifest["screenshots"].sort(key=lambda item: item["name"])
    (version_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    render_viewer(args.version, PROJECT_DIR / args.viewer_output)
    log(f"Live-source viewer updated: {PROJECT_DIR / args.viewer_output}")


if __name__ == "__main__":
    main()
