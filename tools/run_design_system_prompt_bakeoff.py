#!/usr/bin/env python3
"""Run prompt-strategy bakeoffs using a fixed grounding source."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from run_pipeline import (  # noqa: E402
    DEFAULT_SITE_REVIEW_PROMPT,
    PROJECT_DIR,
    RUNS_DIR,
    SITE_GEN_MAX_TOKENS,
    SITE_MATCH_SCORE_WEIGHTS,
    evaluate_site_match,
    generate_viewer,
    generate_website_html,
    html_document_is_complete,
    load_api_keys,
    enforce_source_color_literals,
    enforce_source_site_styles,
    synthesize_design_system_from_grounding,
)
from screenshot_to_template.config import AppConfig  # noqa: E402
from screenshot_to_template.output import clean_markdown  # noqa: E402
from screenshot_to_template.source_colors import (  # noqa: E402
    extract_source_colors,
    find_source_html_for_screenshot,
    render_source_color_report,
    write_source_color_artifacts,
)


@dataclass
class StrategySpec:
    version: str
    title: str
    system_prompt: str
    website_prompt: str
    review_prompt: str = DEFAULT_SITE_REVIEW_PROMPT
    site_generation_source: str = "design_system"
    providers: tuple[str, ...] = ("gpt54",)


BASE_SYSTEM_PROMPT = """\
You are an expert UI/UX designer and design system architect. You will receive a grounded structural analysis of a website screenshot and may also receive a source-of-truth CSS style report from the matching HTML.

Your job is to translate the grounding into a reusable design-system markdown document.

Primary goal:
- capture transferable aesthetic and stylistic rules
- avoid reconstructing the original page section by section
- avoid naming industries, products, services, brands, or content themes

Core constraints:
- Do not describe the exact layouts of specific sections.
- Do describe recurring patterns across sections using frequency labels: `dominant`, `frequent`, `occasional`, `rare`.
- When describing patterns, use generic categories like `Layout`, `Sections`, `Content`, `Colors`, `Photography`, `Components`, `Typography`, `Spacing`, `Depth`.
- Use generic token naming. The most common page background should be `--background-primary`. Its inverse should be `--background-inverse`. The most common accent should be `--background-accent` when it exists. Create secondary variants only when clearly necessary.
- Use matching generic token names for foreground and components, such as `--foreground-primary`, `--foreground-inverse`, `--button-primary`, `--button-inverse`, `--card-primary`, `--eyebrow-primary`.
- Outside the `Color Tokens` section, do not use explicit hex colors when describing patterns. Refer to token names instead.
- Do not mention industry, business category, product domain, or literal content topics anywhere in the output.
- Component descriptions should focus on reusable component objects: buttons, eyebrows, cards, tabs, nav items, dividers, pills, inputs, footer groups, etc.
- Section/category descriptions should focus on recurring stylistic patterns, not on exact section structure.
- If a source CSS style report is present, every explicit color literal or explicit exact typography value must come from that report.

Frequency usage:
- `dominant`: the default system behavior seen across most of the page
- `frequent`: clearly recurring but not the default everywhere
- `occasional`: appears more than once but is secondary
- `rare`: appears once or almost once and should not be mistaken for a system rule

Output requirements:
- Use bullet lists, not long prose paragraphs.
- Keep the output organized under straightforward design-system categories.
{strategy_constraints}

Use this exact structure:

# Design System: [Short aesthetic title]

- [1 sentence on the overall aesthetic direction without mentioning industry/content.]

## Colors

### Color Behavior
- **Overall palette behavior:** ...
- **Accent usage pattern:** ...
- **Section background pattern:** ...
- **Contrast pattern:** ...

### Color Tokens
- Define generic tokens only.
- Organize them by background/surface first, then foreground/component roles.
- Example pattern:
  - `--background-primary`
  - `--foreground-primary`
  - `--foreground-primary-muted`
  - `--button-primary`
  - `--button-primary-foreground`
  - `--card-primary`
  - `--card-primary-foreground`
- Add `secondary` variants only when needed.

## Sections
- Describe recurring section wrapper and background behavior.
- Describe section-to-section transition patterns.
- Describe how often sections share the same surface family versus alternate.
- Describe these as pattern frequencies, not as exact page walkthroughs.

## Layout
- Describe recurring container-width behavior.
- Describe recurring alignment behavior.
- Describe recurring content arrangement patterns across sections.
- Do not name or reconstruct exact sections.

## Content
- Describe recurring heading + subhead + eyebrow alignment patterns across sections.
- Describe common versus rare content density patterns.
- Describe how text and non-text content tend to be paired.

## Typography
- Describe heading, body, and UI text styles.
- If exact values are used, they must come from source CSS styles when available.

## Photography
- Describe recurring photography/image direction patterns.
- Describe recurring background-graphic or foreground-graphic patterns.

## Components
- For each recurring component, describe styling using reusable traits only.
- Cover buttons, cards, eyebrows, pills/tags, tabs, dividers, nav items, inputs, footer groups, and other clearly recurring UI objects.
- Use token names instead of explicit color names when describing how components sit on surfaces.

## Spacing
- Describe large-scale section spacing, mid-scale component spacing, and tight inline spacing patterns.

## Depth
- Describe border, radius, shadow, and elevation behavior.
"""


BASE_WEBSITE_PROMPT = """\
You are an expert frontend developer. You will receive a design-system markdown file extracted from a website screenshot. Generate a complete, single-file HTML landing page that expresses the design system faithfully while remaining a fresh composition.

Rules:
- Output a SINGLE complete HTML file with all CSS inlined in a `<style>` tag.
- Build a fresh page. Do NOT try to copy the original screenshot's exact section layouts or section order.
- Use the design system's dominant and frequent patterns as the primary guide.
- Rare patterns may be used sparingly as accents.
- Focus on expressing the same color-token logic, section surface behavior, typography, imagery direction, component styling, spacing, and depth.
- Reuse the described component recipes consistently.
- Keep the page professional and complete.
- Use CSS custom properties for the generic tokens.
- Do not invent extra accent colors, extra font stacks, or extra component families that are not supported by the design system.
- Make it responsive with CSS Grid/Flexbox.
- Do not use JavaScript frameworks.
- Do not use viewport-height sizing for sections or containers.
- Keep the CSS concise.
{strategy_constraints}

Output ONLY the HTML code, with no markdown fences or explanation.
"""


def strategy_a_prompts() -> tuple[str, str]:
    system = BASE_SYSTEM_PROMPT.format(
        strategy_constraints=(
            "- In each major category, explicitly call out what is `dominant`, `frequent`, `occasional`, and `rare`.\n"
            "- Prefer concise bullets that sound like transferable design-system notes."
        )
    )
    website = BASE_WEBSITE_PROMPT.format(
        strategy_constraints=(
            "- Prefer the dominant patterns first, then layer in 1-2 frequent patterns and at most 1 rare accent pattern."
        )
    )
    return system, website


def strategy_b_prompts() -> tuple[str, str]:
    system = BASE_SYSTEM_PROMPT.format(
        strategy_constraints=(
            "- In `Sections`, `Layout`, `Content`, and `Components`, use explicit bullets labeled `Dominant patterns`, `Frequent patterns`, `Occasional patterns`, and `Rare patterns`.\n"
            "- Keep the analysis more pattern-matrix-like and less descriptive."
        )
    )
    website = BASE_WEBSITE_PROMPT.format(
        strategy_constraints=(
            "- Treat the `dominant` bullets as required behavior.\n"
            "- Treat `frequent` bullets as likely recurring moves across the page."
        )
    )
    return system, website


def strategy_c_prompts() -> tuple[str, str]:
    system = BASE_SYSTEM_PROMPT.format(
        strategy_constraints=(
            "- Make `Sections` especially strong on wrapper/background rhythm and section transition patterns.\n"
            "- Make `Content` especially strong on alignment and text-block positioning patterns.\n"
            "- Keep component detail moderate."
        )
    )
    website = BASE_WEBSITE_PROMPT.format(
        strategy_constraints=(
            "- Give extra priority to section surface rhythm, alignment patterns, and overall atmospheric consistency."
        )
    )
    return system, website


def strategy_d_prompts() -> tuple[str, str]:
    system = BASE_SYSTEM_PROMPT.format(
        strategy_constraints=(
            "- Make `Components` the most detailed category in the document.\n"
            "- For each component, separate base styling from contextual variants on `--background-primary`, `--background-inverse`, or `--background-accent` when applicable.\n"
            "- Keep section/layout descriptions shorter and more abstract."
        )
    )
    website = BASE_WEBSITE_PROMPT.format(
        strategy_constraints=(
            "- Make the page feel fresh by varying layout composition, but keep component styling very faithful to the design system."
        )
    )
    return system, website


def strategy_e_prompts() -> tuple[str, str]:
    system = BASE_SYSTEM_PROMPT.format(
        strategy_constraints=(
            "- Make `Photography` and `Colors` unusually thorough so aesthetic mood is captured as a reusable system.\n"
            "- In `Layout`, describe broad tendencies only and avoid any hint of section reconstruction."
        )
    )
    website = BASE_WEBSITE_PROMPT.format(
        strategy_constraints=(
            "- Prioritize overall aesthetic mood, token logic, and photography/graphic direction over structural similarity."
        )
    )
    return system, website


def iteration_1_prompts() -> tuple[str, str]:
    system = BASE_SYSTEM_PROMPT.format(
        strategy_constraints=(
            "- Start from the section/layout emphasis strategy: preserve strong `Sections`, `Layout`, and `Content` pattern bullets.\n"
            "- For every major category, write in a stricter design-system voice with short, implementation-friendly bullets.\n"
            "- Explicitly avoid section names and avoid inferred semantics."
        )
    )
    website = BASE_WEBSITE_PROMPT.format(
        strategy_constraints=(
            "- The generated page should feel like a different composition built from the same system, not a remix of the same screenshot.\n"
            "- Preserve broad section/background rhythm and alignment tendencies especially carefully."
        )
    )
    return system, website


def iteration_2_prompts() -> tuple[str, str]:
    system = BASE_SYSTEM_PROMPT.format(
        strategy_constraints=(
            "- Start from the section/layout emphasis strategy.\n"
            "- In `Colors`, require a clean generic hierarchy: `primary`, `secondary`, `accent`, `inverse`, and optional secondary variants only when justified.\n"
            "- In `Sections`, emphasize frequent background/transition tendencies across the page."
        )
    )
    website = BASE_WEBSITE_PROMPT.format(
        strategy_constraints=(
            "- Treat generic token hierarchy as the source of truth for all surfaces and components."
        )
    )
    return system, website


def iteration_3_prompts() -> tuple[str, str]:
    system = BASE_SYSTEM_PROMPT.format(
        strategy_constraints=(
            "- Start from the section/layout emphasis strategy.\n"
            "- In `Content`, explicitly describe whether eyebrow + heading + subhead stacks are usually left-aligned, centered, balanced in split layouts, or otherwise.\n"
            "- In `Layout`, describe frequent container and text-pairing tendencies with more precision."
        )
    )
    website = BASE_WEBSITE_PROMPT.format(
        strategy_constraints=(
            "- Recreate alignment tendencies and text-block behavior faithfully, while still avoiding exact section copying."
        )
    )
    return system, website


def iteration_4_prompts() -> tuple[str, str]:
    system = BASE_SYSTEM_PROMPT.format(
        strategy_constraints=(
            "- Start from the section/layout emphasis strategy.\n"
            "- In `Components`, require clear descriptions of radius, padding feel, border/shadow treatment, and how components sit on `--background-primary` versus `--background-inverse`.\n"
            "- Keep all component descriptions free of industry/content references."
        )
    )
    website = BASE_WEBSITE_PROMPT.format(
        strategy_constraints=(
            "- Recreate the component system very faithfully and let page composition vary more than component styling."
        )
    )
    return system, website


def iteration_5_prompts() -> tuple[str, str]:
    system = BASE_SYSTEM_PROMPT.format(
        strategy_constraints=(
            "- Start from the section/layout emphasis strategy.\n"
            "- Make the document slightly more conservative: only include patterns that are visually supported, and mark weaker evidence as `rare` instead of upgrading it.\n"
            "- Favor a clean, generic design-system schema over clever naming."
        )
    )
    website = BASE_WEBSITE_PROMPT.format(
        strategy_constraints=(
            "- Prefer a calm, consistent application of dominant/frequent patterns rather than squeezing in every rare pattern."
        )
    )
    return system, website


def iteration_6_prompts() -> tuple[str, str]:
    system = BASE_SYSTEM_PROMPT.format(
        strategy_constraints=(
            "- Start from the section/layout emphasis strategy.\n"
            "- In `Sections`, explicitly distinguish dominant surface families from occasional alternates and call out how transitions typically happen.\n"
            "- In `Colors`, keep token usage strict so surface descriptions consistently map back to the same generic roles."
        )
    )
    website = BASE_WEBSITE_PROMPT.format(
        strategy_constraints=(
            "- Preserve section-surface rhythm and token discipline more strongly than any one layout choice."
        )
    )
    return system, website


def iteration_7_prompts() -> tuple[str, str]:
    system = BASE_SYSTEM_PROMPT.format(
        strategy_constraints=(
            "- Start from the section/layout emphasis strategy.\n"
            "- In `Components`, describe reusable object styling with clear notes on radius, stroke weight, fill treatment, and contrast on `--background-primary` versus `--background-inverse`.\n"
            "- In `Content`, keep alignment notes concise so the document stays system-first."
        )
    )
    website = BASE_WEBSITE_PROMPT.format(
        strategy_constraints=(
            "- Keep the composition fresh, but make repeated components feel unmistakably from the same system across the page."
        )
    )
    return system, website


def iteration_8_prompts() -> tuple[str, str]:
    system = BASE_SYSTEM_PROMPT.format(
        strategy_constraints=(
            "- Start from the section/layout emphasis strategy.\n"
            "- Bias toward high-confidence aesthetic patterns only: promote something to `frequent` only when it visibly recurs, otherwise keep it `occasional` or `rare`.\n"
            "- Keep every category compact, generic, and implementation-friendly."
        )
    )
    website = BASE_WEBSITE_PROMPT.format(
        strategy_constraints=(
            "- Build a coherent page from the strongest system signals first and let weaker signals appear only sparingly."
        )
    )
    return system, website


def build_specs() -> dict[str, StrategySpec]:
    specs: dict[str, StrategySpec] = {}
    prompt_builders = {
        "v037": ("Strategy A - Frequency-first taxonomy", strategy_a_prompts),
        "v038": ("Strategy B - Pattern matrix", strategy_b_prompts),
        "v039": ("Strategy C - Section/layout emphasis", strategy_c_prompts),
        "v040": ("Strategy D - Component-led extraction", strategy_d_prompts),
        "v041": ("Strategy E - Mood/colors emphasis", strategy_e_prompts),
        "v042": ("Iteration 1 - Stricter generic system voice", iteration_1_prompts),
        "v043": ("Iteration 2 - Cleaner token hierarchy", iteration_2_prompts),
        "v044": ("Iteration 3 - Stronger content alignment patterns", iteration_3_prompts),
        "v045": ("Iteration 4 - Stronger component variants", iteration_4_prompts),
        "v046": ("Iteration 5 - Conservative evidence filter", iteration_5_prompts),
        "v047": ("Iteration 6 - Stronger section surface rhythm", iteration_6_prompts),
        "v048": ("Iteration 7 - Stronger reusable components", iteration_7_prompts),
        "v049": ("Iteration 8 - Higher confidence pattern filter", iteration_8_prompts),
    }
    for version, (title, builder) in prompt_builders.items():
        system_prompt, website_prompt = builder()
        specs[version] = StrategySpec(
            version=version,
            title=title,
            system_prompt=system_prompt,
            website_prompt=website_prompt,
        )
    return specs


def write_version_prompt_files(version_dir: Path, spec: StrategySpec) -> None:
    version_dir.mkdir(parents=True, exist_ok=True)
    (version_dir / "system-prompt.md").write_text(spec.system_prompt.rstrip() + "\n")
    (version_dir / "website-gen-prompt.md").write_text(spec.website_prompt.rstrip() + "\n")
    (version_dir / "site-review-prompt.md").write_text(spec.review_prompt.rstrip() + "\n")
    (version_dir / "site-generation-source.txt").write_text(spec.site_generation_source + "\n")
    (version_dir / "site-generation-providers.txt").write_text("\n".join(spec.providers) + "\n")
    (version_dir / "learnings.md").write_text(
        f"# {spec.version} Learnings\n\n"
        f"- Strategy: {spec.title}\n"
        "- Goal: improve grounding-to-design-system translation using generic tokens and pattern-first extraction.\n"
    )


def write_placeholder_site(path: Path, label: str) -> None:
    path.write_text(
        "<html><body><p>"
        f"{label} site generation was skipped for this prompt bakeoff."
        "</p></body></html>\n"
    )


def run_version(
    spec: StrategySpec,
    *,
    source_version: str,
    screenshots_dir: Path,
) -> dict:
    version_dir = RUNS_DIR / spec.version
    write_version_prompt_files(version_dir, spec)

    config = AppConfig(provider="openai", model="gpt-5.5")
    config.max_tokens = 16384
    config.system_prompt = spec.system_prompt

    screenshot_files = sorted(
        path for path in screenshots_dir.iterdir()
        if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
    )
    manifest = {
        "version": spec.version,
        "timestamp": datetime.now().isoformat(),
        "screenshots": [],
    }

    for screenshot_path in screenshot_files:
        name = screenshot_path.stem
        item_dir = version_dir / name
        item_dir.mkdir(parents=True, exist_ok=True)
        dest_screenshot = item_dir / f"screenshot{screenshot_path.suffix}"
        shutil.copy2(screenshot_path, dest_screenshot)

        single_dir = item_dir / "single"
        single_dir.mkdir(exist_ok=True)

        source_structural = RUNS_DIR / source_version / name / "single" / "structural-analysis.md"
        if not source_structural.exists():
            raise FileNotFoundError(f"Missing source grounding: {source_structural}")
        structural_analysis = source_structural.read_text().strip()
        (single_dir / "structural-analysis.md").write_text(structural_analysis + "\n")

        source_html_path = find_source_html_for_screenshot(screenshot_path)
        extracted_source_styles = None
        source_style_report = None
        if source_html_path and source_html_path.exists():
            extracted_source_styles = extract_source_colors(source_html_path)
            write_source_color_artifacts(single_dir, extracted_source_styles)
            source_style_report = render_source_color_report(extracted_source_styles)

        ds = synthesize_design_system_from_grounding(
            structural_analysis=structural_analysis,
            config=config,
            source_color_report=source_style_report,
        )
        ds_clean = clean_markdown(ds)
        if extracted_source_styles:
            (single_dir / "design-system.pre-color-sync.md").write_text(ds_clean + "\n")
            ds_clean = enforce_source_color_literals(
                ds_clean,
                extracted_source_colors=extracted_source_styles,
                config=config,
            )
        (single_dir / "design-system.md").write_text(ds_clean + "\n")
        (single_dir / "site-generation-input.md").write_text(ds_clean + "\n")

        html = generate_website_html(
            ds_clean,
            "gpt54",
            website_prompt=spec.website_prompt,
            generation_label="design system",
        )
        if not html_document_is_complete(html):
            raise ValueError(f"{spec.version}/{name}: generated HTML incomplete")
        if extracted_source_styles:
            html = enforce_source_site_styles(
                html,
                generation_markdown=ds_clean,
                extracted_source_styles=extracted_source_styles,
                config=config,
            )
            if not html_document_is_complete(html):
                raise ValueError(f"{spec.version}/{name}: synced HTML incomplete")

        (single_dir / "site-gpt54.html").write_text(html + "\n")
        write_placeholder_site(single_dir / "site-claude.html", "Claude")
        write_placeholder_site(single_dir / "site-gemini.html", "Gemini")

        evaluate_site_match(
            reference_screenshot_path=screenshot_path,
            grounding_markdown=structural_analysis,
            generated_html_path=single_dir / "site-gpt54.html",
            rendered_screenshot_path=single_dir / "site-gpt54.png",
            review_json_path=single_dir / "site-gpt54-review.json",
            review_md_path=single_dir / "site-gpt54-review.md",
            review_prompt=spec.review_prompt,
            max_image_dimension=2048,
        )

        manifest["screenshots"].append(
            {
                "name": name,
                "screenshot": str(dest_screenshot.relative_to(version_dir)),
                "single": {
                    "structural_analysis": str((single_dir / "structural-analysis.md").relative_to(version_dir)),
                    "design_system": str((single_dir / "design-system.md").relative_to(version_dir)),
                    "site_claude": str((single_dir / "site-claude.html").relative_to(version_dir)),
                    "site_gemini": str((single_dir / "site-gemini.html").relative_to(version_dir)),
                    "site_gpt54": str((single_dir / "site-gpt54.html").relative_to(version_dir)),
                },
            }
        )

    manifest["screenshots"].sort(key=lambda item: item["name"])
    (version_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Run design-system prompt bakeoff versions using a fixed grounding source.")
    parser.add_argument("--source-version", required=True, help="Version to copy structural-analysis.md from")
    parser.add_argument("--screenshots-dir", required=True, help="Directory containing screenshot/html pairs")
    parser.add_argument("--versions", nargs="+", required=True, help="Versions to run, e.g. v037 v038")
    args = parser.parse_args()

    load_api_keys()
    screenshots_dir = Path(args.screenshots_dir)
    specs = build_specs()
    for version in args.versions:
        spec = specs.get(version)
        if spec is None:
            raise ValueError(f"Unknown version spec: {version}")
        print(f"Running {version}: {spec.title}")
        run_version(spec, source_version=args.source_version, screenshots_dir=screenshots_dir)

    generate_viewer(RUNS_DIR, PROJECT_DIR / "viewer.html")
    print("viewer regenerated")


if __name__ == "__main__":
    main()
