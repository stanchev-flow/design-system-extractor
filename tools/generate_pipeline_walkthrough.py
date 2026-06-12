#!/usr/bin/env python3
"""Generate a horizontal-scroll walkthrough page for one pipeline item."""

from __future__ import annotations

import argparse
import html
import json
import re
from collections import defaultdict
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
RUNS_DIR = PROJECT_DIR / "runs"


def read_text(path: Path) -> str:
    return path.read_text() if path.exists() else f"[Missing] {path}"


def rel(path: Path) -> str:
    return path.relative_to(PROJECT_DIR).as_posix()


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "section"


def wrap_artifact(anchor_id: str | None, inner: str) -> str:
    if anchor_id:
        return inner.replace('<section class="artifact">', f'<section id="{html.escape(anchor_id)}" class="artifact">', 1)
    return inner


def code_block(label: str, path: Path, language: str = "", anchor_id: str | None = None) -> str:
    content = html.escape(read_text(path))
    lang_class = f" language-{language}" if language else ""
    block = (
        '<section class="artifact">'
        f'<div class="artifact-meta"><span class="artifact-label">{html.escape(label)}</span>'
        f'<a href="{html.escape(rel(path))}" target="_blank">{html.escape(rel(path))}</a></div>'
        f'<pre><code class="{lang_class.strip()}">{content}</code></pre>'
        "</section>"
    )
    return wrap_artifact(anchor_id, block)


def optional_code_block(label: str, path: Path, language: str = "", anchor_id: str | None = None) -> str:
    return code_block(label, path, language, anchor_id=anchor_id) if path.exists() else ""


def image_block(label: str, path: Path, anchor_id: str | None = None) -> str:
    block = (
        '<section class="artifact">'
        f'<div class="artifact-meta"><span class="artifact-label">{html.escape(label)}</span>'
        f'<a href="{html.escape(rel(path))}" target="_blank">{html.escape(rel(path))}</a></div>'
        f'<img src="{html.escape(rel(path))}" alt="{html.escape(label)}" loading="lazy" />'
        "</section>"
    )
    return wrap_artifact(anchor_id, block)


def optional_image_block(label: str, path: Path, anchor_id: str | None = None) -> str:
    return image_block(label, path, anchor_id=anchor_id) if path.exists() else ""


def iframe_block(label: str, path: Path, anchor_id: str | None = None) -> str:
    block = (
        '<section class="artifact">'
        f'<div class="artifact-meta"><span class="artifact-label">{html.escape(label)}</span>'
        f'<a href="{html.escape(rel(path))}" target="_blank">{html.escape(rel(path))}</a></div>'
        f'<iframe src="{html.escape(rel(path))}" loading="lazy"></iframe>'
        "</section>"
    )
    return wrap_artifact(anchor_id, block)


def optional_iframe_block(label: str, path: Path, anchor_id: str | None = None) -> str:
    return iframe_block(label, path, anchor_id=anchor_id) if path.exists() else ""


def artifacts_stack(label: str, blocks: list[str], anchor_id: str | None = None) -> str:
    blocks = [block for block in blocks if block]
    if not blocks:
        return ""
    block = (
        '<section class="artifact">'
        f'<div class="artifact-meta"><span class="artifact-label">{html.escape(label)}</span></div>'
        f'<div class="artifact-stack">{"".join(blocks)}</div>'
        "</section>"
    )
    return wrap_artifact(anchor_id, block)


def paired_artifacts_stack(label: str, pairs: list[tuple[str, str]], anchor_id: str | None = None) -> str:
    block = (
        '<section class="artifact">'
        f'<div class="artifact-meta"><span class="artifact-label">{html.escape(label)}</span></div>'
        f'<div class="artifact-stack">{"".join(left + right for left, right in pairs)}</div>'
        "</section>"
    )
    return wrap_artifact(anchor_id, block)


def paired_artifact(label: str, left: str, right: str, anchor_id: str | None = None) -> str:
    if not left or not right:
        return left or right
    block = (
        '<section class="artifact artifact-pair-shell">'
        f'<div class="artifact-meta"><span class="artifact-label">{html.escape(label)}</span></div>'
        f'<div class="artifact-pair"><div class="artifact-pair-media">{left}</div><div class="artifact-pair-copy">{right}</div></div>'
        "</section>"
    )
    return wrap_artifact(anchor_id, block)


def inline_code_block(label: str, content: str, language: str = "", anchor_id: str | None = None) -> str:
    lang_class = f" language-{language}" if language else ""
    block = (
        '<section class="artifact">'
        f'<div class="artifact-meta"><span class="artifact-label">{html.escape(label)}</span></div>'
        f'<pre><code class="{lang_class.strip()}">{html.escape(content)}</code></pre>'
        "</section>"
    )
    return wrap_artifact(anchor_id, block)


def simple_link_list(label: str, paths: list[Path], anchor_id: str | None = None) -> str:
    paths = [path for path in paths if path.exists()]
    if not paths:
        return ""
    items = "".join(
        f'<li><a href="{html.escape(rel(path))}" target="_blank">{html.escape(path.name)}</a></li>'
        for path in paths
    )
    block = (
        '<section class="artifact">'
        f'<div class="artifact-meta"><span class="artifact-label">{html.escape(label)}</span></div>'
        f'<ul class="link-list">{items}</ul>'
        "</section>"
    )
    return wrap_artifact(anchor_id, block)


def kv_block(label: str, items: list[tuple[str, str]], anchor_id: str | None = None) -> str:
    rows = "".join(
        f"<tr><th>{html.escape(k)}</th><td>{html.escape(v)}</td></tr>"
        for k, v in items
    )
    block = (
        '<section class="artifact">'
        f'<div class="artifact-meta"><span class="artifact-label">{html.escape(label)}</span></div>'
        f'<table class="kv-table">{rows}</table>'
        "</section>"
    )
    return wrap_artifact(anchor_id, block)


def load_token_usage(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows: list[dict] = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def summarize_token_events(events: list[dict]) -> list[tuple[str, str]]:
    if not events:
        return [("Calls", "0"), ("Input tokens", "0"), ("Output tokens", "0")]
    total_input = sum(int((event.get("usage") or {}).get("input_tokens") or 0) for event in events)
    total_output = sum(int((event.get("usage") or {}).get("output_tokens") or 0) for event in events)
    return [
        ("Calls", str(len(events))),
        ("Input tokens", f"{total_input:,}"),
        ("Output tokens", f"{total_output:,}"),
    ]


def token_summary_block(label: str, events: list[dict], anchor_id: str | None = None) -> str:
    return kv_block(label, summarize_token_events(events), anchor_id=anchor_id)


def token_breakdown_block(label: str, events: list[dict], anchor_id: str | None = None) -> str:
    grouped: dict[str, dict[str, int]] = defaultdict(lambda: {"calls": 0, "input": 0, "output": 0})
    for event in events:
        step = str(event.get("step", "unknown"))
        usage = event.get("usage") or {}
        grouped[step]["calls"] += 1
        grouped[step]["input"] += int(usage.get("input_tokens") or 0)
        grouped[step]["output"] += int(usage.get("output_tokens") or 0)
    rows = "".join(
        f"<tr><th>{html.escape(step)}</th><td>{stats['calls']}</td><td>{stats['input']:,}</td><td>{stats['output']:,}</td></tr>"
        for step, stats in sorted(grouped.items())
    )
    block = (
        '<section class="artifact">'
        f'<div class="artifact-meta"><span class="artifact-label">{html.escape(label)}</span></div>'
        '<table class="kv-table"><thead><tr><th>Step</th><th>Calls</th><th>Input</th><th>Output</th></tr></thead>'
        f"<tbody>{rows}</tbody></table>"
        "</section>"
    )
    return wrap_artifact(anchor_id, block)


def review_summary_rows(path: Path) -> list[tuple[str, str]]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text())
    rows = [
        ("Weighted score", f"{payload.get('weighted_score', 0)} / 100"),
        ("Summary", str(payload.get("summary", ""))),
        ("Verdict", str(payload.get("verdict", ""))),
    ]
    scores = payload.get("scores")
    if isinstance(scores, dict):
        rows.append(("Scored dimensions", str(len(scores))))
    section_reviews = payload.get("section_reviews")
    if isinstance(section_reviews, list):
        rows.append(("Reviewed sections", str(len(section_reviews))))
    return rows


def infer_generation_source(version_dir: Path, single_dir: Path) -> str:
    source_path = version_dir / "site-generation-source.txt"
    if source_path.exists():
        return source_path.read_text().strip()
    if (single_dir / "design-system.yaml").exists() or (single_dir / "design-system.md").exists():
        return "design_system"
    return "grounding"


def asset_candidate_block(manifest_path: Path, candidate: dict, index: int) -> str:
    asset_rel = str(candidate.get("asset_path") or "")
    asset_path = manifest_path.parent / asset_rel if asset_rel else None
    label_seed = candidate.get("asset_brief") or candidate.get("section_heading") or candidate.get("label_hint") or f"Asset {index}"
    label = f"{index}. {str(label_seed)[:90]}"
    rows = [
        ("Status", str(candidate.get("status", ""))),
        ("Target", f"{candidate.get('target_kind', '')} {candidate.get('width', '')}x{candidate.get('height', '')}"),
        ("Aspect ratio", str(candidate.get("aspect_ratio", ""))),
        ("Image size", str(candidate.get("image_size", ""))),
        ("Section background", str(candidate.get("section_background", ""))),
        ("Fallback used", str(candidate.get("fallback_used", False))),
    ]
    preview = image_block("Generated PNG", asset_path) if asset_path and asset_path.exists() else kv_block("Generated PNG", [("Path", asset_rel or "Not generated")])
    prompt_blocks = [
        kv_block("Image prompt inputs", rows),
        inline_code_block("Final image prompt", str(candidate.get("prompt", "")), "markdown"),
    ]
    fallback_prompt = str(candidate.get("fallback_prompt", ""))
    if fallback_prompt:
        prompt_blocks.append(inline_code_block("Fallback image prompt", fallback_prompt, "markdown"))
    error = str(candidate.get("error", ""))
    if error:
        prompt_blocks.append(inline_code_block("Generation error", error, "text"))
    return paired_artifact(label, preview, artifacts_stack("Prompt trace", prompt_blocks))


def asset_manifest_block(label: str, manifest_path: Path) -> str:
    if not manifest_path.exists():
        return code_block(label, manifest_path, "json")
    payload = json.loads(manifest_path.read_text())
    candidates = payload.get("candidates") or []
    summary = [
        ("Status", str(payload.get("status", ""))),
        ("Model", str(payload.get("model", ""))),
        ("Generated count", str(payload.get("generated_count", 0))),
        ("Candidates", str(len(candidates))),
    ]
    blocks = [kv_block(f"{label} summary", summary), code_block(f"{label} manifest JSON", manifest_path, "json")]
    for index, candidate in enumerate(candidates, start=1):
        blocks.append(asset_candidate_block(manifest_path, candidate, index))
    return artifacts_stack(label, blocks)


def build_column(title: str, subtitle: str, sections: list[tuple[str, str]]) -> str:
    normalized_sections: list[tuple[str, str, str]] = []
    for label, block in sections:
        if not block:
            continue
        anchor_id = f"{slugify(title)}-{slugify(label)}"
        normalized_sections.append((label, anchor_id, block))

    nav = ""
    if len(normalized_sections) > 1:
        items = "".join(
            f'<li><a href="#{html.escape(anchor_id)}">{html.escape(label)}</a></li>'
            for label, anchor_id, _ in normalized_sections
        )
        nav = (
            '<aside class="step-nav">'
            '<div class="step-nav-title">Sections</div>'
            f'<ul class="step-nav-list">{items}</ul>'
            '</aside>'
        )

    content = "".join(
        wrap_artifact(anchor_id, block) for _, anchor_id, block in normalized_sections
    )

    return (
        f'<article class="step-column {html.escape(slugify(title))}">'
        f"<header><h2>{html.escape(title)}</h2><p>{html.escape(subtitle)}</p></header>"
        '<div class="step-body">'
        f"{nav}"
        f'<div class="step-content">{content}</div>'
        '</div>'
        "</article>"
    )


def build_html(version: str, item: str) -> str:
    version_dir = RUNS_DIR / version
    item_dir = version_dir / item
    single_dir = item_dir / "single"
    changes_md = version_dir / "changes.md"

    structural_prompt = version_dir / "structural-analysis-prompt.md"
    system_prompt = version_dir / "system-prompt.md"
    grounding_sync_prompt = version_dir / "grounding-sync-prompt.md"
    section_inventory_prompt = version_dir / "section-inventory-prompt.md"
    section_grounding_prompt = version_dir / "section-grounding-prompt.md"
    global_site_grounding_prompt = version_dir / "global-site-grounding-prompt.md"
    grounding_merge_prompt = version_dir / "grounding-merge-prompt.md"
    full_page_review_prompt = version_dir / "full-page-review-prompt.md"
    website_prompt = version_dir / "website-gen-prompt.md"
    site_validator_prompt = version_dir / "site-validator-prompt.md"
    site_review_prompt = version_dir / "site-review-prompt.md"
    color_sync_prompt = version_dir / "color-sync-prompt.md"
    surface_component_map_prompt = version_dir / "surface-component-map-prompt.md"
    surface_component_map_review_prompt = version_dir / "surface-component-map-review-prompt.md"
    design_system_conversion_review_prompt = version_dir / "design-system-conversion-review-prompt.md"
    design_system_review_prompt = version_dir / "design-system-review-prompt.md"
    site_style_sync_prompt = version_dir / "site-style-sync-prompt.md"
    providers = version_dir / "site-generation-providers.txt"
    skills = version_dir / "site-generation-skills.txt"
    generation_source = version_dir / "site-generation-source.txt"

    screenshot = next(item_dir.glob("screenshot.*"))
    source_colors_md = single_dir / "source-colors.md"
    source_colors_json = single_dir / "source-colors.json"
    section_inventory = single_dir / "section-inventory.md"
    section_detection_raw = single_dir / "section-detection-raw.txt"
    section_map = single_dir / "section-map.html"
    sections_json = single_dir / "sections.json"
    full_page_review_json = single_dir / "full-page-review.json"
    crops_dir = single_dir / "crops"
    section_groundings_dir = single_dir / "section-groundings"
    structural_pre = single_dir / "structural-analysis.pre-source-sync.md"
    structural_final = single_dir / "structural-analysis.md"
    global_site_grounding = single_dir / "global-site-grounding.yaml"
    layouts_artifact = single_dir / "layouts.yaml"
    surface_component_map_draft = single_dir / "surface-component-map-deterministic-draft.md"
    surface_component_map = single_dir / "surface-component-map.md"
    surface_component_map_review_md = single_dir / "surface-component-map-review.md"
    surface_component_map_review_json = single_dir / "surface-component-map-review.json"
    design_pre = single_dir / "design-system.pre-color-sync.md"
    design_pre_self_refine = single_dir / "design-system.pre-self-refine.md"
    design_pre_self_refine_conversion_review_md = single_dir / "design-system.pre-self-refine-conversion-review.md"
    design_pre_self_refine_conversion_review_json = single_dir / "design-system.pre-self-refine-conversion-review.json"
    design_final = single_dir / "design-system.yaml"
    if not design_final.exists():
        design_final = single_dir / "design-system.md"
    design_system_conversion_ledger = single_dir / "design-system-conversion-ledger.md"
    design_system_conversion_review_md = single_dir / "design-system-conversion-review.md"
    design_system_conversion_review_json = single_dir / "design-system-conversion-review.json"
    design_system_review_md = single_dir / "design-system-review.md"
    design_system_review_json = single_dir / "design-system-review.json"
    generation_input = single_dir / "site-generation-input.md"
    claude_html = single_dir / "site-claude.html"
    claude_post_html = single_dir / "site-claude.post-validator.html"
    gemini_html = single_dir / "site-gemini.html"
    gemini_post_html = single_dir / "site-gemini.post-validator.html"
    gpt_output_stem = "site-gpt55" if (single_dir / "site-gpt55.html").exists() else "site-gpt54"
    gpt54_html = single_dir / f"{gpt_output_stem}.html"
    gpt54_post_html = single_dir / f"{gpt_output_stem}.post-validator.html"
    claude_assets = single_dir / "site-claude.assets.json"
    gemini_assets = single_dir / "site-gemini.assets.json"
    gpt54_assets = single_dir / f"{gpt_output_stem}.assets.json"
    claude_viewport_units = single_dir / "site-claude.viewport-units.json"
    gemini_viewport_units = single_dir / "site-gemini.viewport-units.json"
    gpt54_viewport_units = single_dir / f"{gpt_output_stem}.viewport-units.json"
    gpt54_png = single_dir / f"{gpt_output_stem}.png"
    review_md = single_dir / f"{gpt_output_stem}-review.md"
    review_json = single_dir / f"{gpt_output_stem}-review.json"
    run_steps = single_dir / "run-steps.json"
    token_usage = load_token_usage(single_dir / "token-usage.jsonl")
    generation_source_value = infer_generation_source(version_dir, single_dir)

    section_detection_events = [event for event in token_usage if str(event.get("step")) == "section_detection"]
    section_grounding_events = [event for event in token_usage if str(event.get("step", "")).startswith("section_grounding_")]
    full_page_review_events = [event for event in token_usage if str(event.get("step")) == "full_page_review"]
    global_site_grounding_events = [event for event in token_usage if str(event.get("step")) == "global_site_grounding"]
    grounding_merge_events = [event for event in token_usage if str(event.get("step")) == "grounding_merge"]
    grounding_sync_events = [event for event in token_usage if str(event.get("step")) == "grounding_style_sync"]
    design_system_events = [event for event in token_usage if str(event.get("step")) == "design_system_synthesis"]
    surface_component_map_events = [
        event for event in token_usage
        if str(event.get("step", "")).startswith("surface_component_map")
    ]
    design_system_conversion_events = [
        event for event in token_usage
        if str(event.get("step", "")).startswith("design_system_conversion")
    ]
    design_system_review_events = [
        event for event in token_usage
        if str(event.get("step", "")).startswith("design_system_review")
    ]
    site_generation_events = [
        event for event in token_usage
        if str(event.get("step", "")).startswith("site_generation_")
    ]
    site_style_sync_events = [
        event for event in token_usage
        if str(event.get("step", "")).startswith("site_style_sync_")
    ]
    site_asset_events = [
        event for event in token_usage
        if str(event.get("step", "")).startswith("site_asset_generation_")
    ]
    site_validator_events = [
        event for event in token_usage
        if str(event.get("step", "")).startswith("site_validator_")
        and not str(event.get("step", "")).startswith("site_validator_style_sync_")
    ]
    site_validator_style_sync_events = [
        event for event in token_usage
        if str(event.get("step", "")).startswith("site_validator_style_sync_")
    ]
    site_review_events = [event for event in token_usage if str(event.get("step")) == "site_review"]

    review_summary = review_summary_rows(review_json)

    crop_paths = sorted(crops_dir.glob("*")) if crops_dir.exists() else []
    section_grounding_paths = sorted(section_groundings_dir.glob("*.md")) if section_groundings_dir.exists() else []
    use_splitter_flow = section_inventory.exists()

    columns: list[str] = []

    columns.append(
        build_column(
            "Step 1",
            "Original input and version settings. This stage establishes the raw screenshot and the model configuration that the pipeline will use before any analysis or transformation begins.",
            [
                (
                    "Run context",
                    kv_block(
                        "Run context",
                        [
                            ("Version", version),
                            ("Item", item),
                            ("Generation source", generation_source_value),
                            ("Providers", ", ".join(read_text(providers).splitlines())),
                            ("Site skills", ", ".join(read_text(skills).splitlines()) if skills.exists() else "none"),
                        ],
                    ),
                ),
                ("Input screenshot", image_block("Input screenshot", screenshot)),
                ("Run steps", code_block("Run steps", run_steps, "json")),
            ],
        )
    )

    columns.append(
        build_column(
            "Step 2",
            "Source style extraction. This stage pulls color, typography, and other style clues from the source implementation so later grounding can be corrected or enriched with more concrete values.",
            [
                ("Source color/style report", code_block("Source color/style report", source_colors_md, "markdown")),
                ("Source color/style JSON", code_block("Source color/style JSON", source_colors_json, "json")),
            ],
        )
    )

    if use_splitter_flow:
        crop_preview_blocks = [image_block(path.name, path) for path in crop_paths]
        section_grounding_sections: list[tuple[str, str]] = []
        for grounding_path in section_grounding_paths:
            stem = grounding_path.stem
            prefix = stem.split("-", 1)[0]
            matching_crop = next((path for path in crop_paths if path.name.startswith(f"{prefix}-")), None)
            matching_yaml = grounding_path.with_suffix(".yaml")
            left = image_block(matching_crop.name, matching_crop) if matching_crop else ""
            right = artifacts_stack(
                "Section grounding outputs",
                [
                    code_block(grounding_path.name, grounding_path, "markdown"),
                    optional_code_block(matching_yaml.name, matching_yaml, "yaml"),
                ],
            )
            label_source = matching_crop.stem if matching_crop else grounding_path.stem
            display_label = label_source.replace("-", " ")
            section_grounding_sections.append(
                (
                    display_label,
                    paired_artifact(display_label, left, right),
                )
            )

        columns.append(
            build_column(
                "Step 3",
                "Full-page section inventory. This stage looks at the entire screenshot at once and decides which top-level sections exist from top to bottom before any cropping happens.",
                [
                    ("Inventory screenshot input", image_block("Inventory screenshot input", screenshot)),
                    ("Section inventory prompt", code_block("Section inventory prompt", section_inventory_prompt, "markdown") if section_inventory_prompt.exists() else ""),
                    ("Inventory token usage", token_summary_block("Inventory token usage", section_detection_events)),
                    ("Inventory output", code_block("Inventory output", section_inventory, "markdown")),
                ],
            )
        )

        columns.append(
            build_column(
                "Step 4",
                "Section detection and crop mapping. This stage converts the inventory into concrete section boundaries, creates the crop list, and shows how the page is being divided for per-section analysis.",
                [
                    ("Detection token usage", token_summary_block("Detection token usage", section_detection_events)),
                    ("Section detection raw output", code_block("Section detection raw output", section_detection_raw, "text")),
                    ("Sections JSON", code_block("Sections JSON", sections_json, "json")),
                    ("Section map", optional_iframe_block("Section map", section_map)),
                    ("Detected section crops", artifacts_stack("Detected section crops", crop_preview_blocks) if crop_preview_blocks else ""),
                ],
            )
        )

        columns.append(
            build_column(
                "Step 5",
                "Parallel per-section grounding. Each detected section crop is analyzed independently so the model can capture local layout, styling, components, and typography with less interference from the rest of the page.",
                [
                    ("Section grounding prompt", code_block("Section grounding prompt", section_grounding_prompt, "markdown") if section_grounding_prompt.exists() else ""),
                    ("Grounding token summary", token_summary_block("Grounding token summary", section_grounding_events)),
                    ("Grounding token breakdown", token_breakdown_block("Grounding token breakdown", section_grounding_events)),
                    *section_grounding_sections,
                ],
            )
        )

        columns.append(
            build_column(
                "Step 6",
                "Pre-sync merged grounding. This stage stitches the individual section analyses back into one full-page grounding draft before any source-CSS correction is applied.",
                [
                    ("Review + merge token summary", token_summary_block("Review + merge token summary", full_page_review_events + global_site_grounding_events + grounding_merge_events)),
                    ("Grounding merge prompt", code_block("Grounding merge prompt", grounding_merge_prompt, "markdown") if grounding_merge_prompt.exists() else ""),
                    ("Full-page review prompt", code_block("Full-page review prompt", full_page_review_prompt, "markdown") if full_page_review_prompt.exists() else ""),
                    ("Full-page review JSON", code_block("Full-page review JSON", full_page_review_json, "json") if full_page_review_json.exists() else ""),
                    ("Global site grounding prompt", optional_code_block("Global site grounding prompt", global_site_grounding_prompt, "markdown")),
                    ("Global site grounding YAML", optional_code_block("Global site grounding YAML", global_site_grounding, "yaml")),
                    ("Pre-sync merged grounding", code_block("Pre-sync merged grounding", structural_pre, "markdown")),
                    ("Source layouts artifact", optional_code_block("Source layouts artifact", layouts_artifact, "yaml")),
                ],
            )
        )

        columns.append(
            build_column(
                "Step 7",
                "Grounding sync with source CSS. This stage refines the merged grounding using extracted source styles so colors, typography, and other implementation-visible details become more explicit and consistent.",
                [
                    ("Sync token usage", token_summary_block("Sync token usage", grounding_sync_events)),
                    ("Grounding sync prompt", code_block("Grounding sync prompt", grounding_sync_prompt, "markdown")),
                    ("Final structural grounding", code_block("Final structural grounding", structural_final, "markdown")),
                ],
            )
        )

        next_step_number = 8
    else:
        columns.append(
            build_column(
                "Step 3",
                "Grounding analysis before sync. In the single-shot path, this stage analyzes the screenshot directly without section crops and writes the first structural grounding draft.",
                [
                    ("Grounding screenshot input", image_block("Grounding screenshot input", screenshot)),
                    ("Grounding prompt", code_block("Grounding prompt", structural_prompt, "markdown")),
                    ("Grounding token usage", token_summary_block("Grounding token usage", grounding_sync_events)),
                    ("Pre-sync structural grounding", code_block("Pre-sync structural grounding", structural_pre, "markdown")),
                ],
            )
        )

        columns.append(
            build_column(
                "Step 4",
                "Grounding sync with source CSS. This stage enriches the single-shot grounding using extracted source styles so the final grounding has stronger color and typography detail.",
                [
                    ("Sync token usage", token_summary_block("Sync token usage", grounding_sync_events)),
                    ("Grounding sync prompt", code_block("Grounding sync prompt", grounding_sync_prompt, "markdown")),
                    ("Final structural grounding", code_block("Final structural grounding", structural_final, "markdown")),
                ],
            )
        )

        next_step_number = 5

    if surface_component_map.exists() or surface_component_map_draft.exists():
        columns.append(
            build_column(
                f"Step {next_step_number}",
                "Surface/component map. This stage normalizes the grounding into reusable host-surface and nested-component relationships before design-system conversion, preserving facts such as component color pairings, typography casing, and surface-specific exceptions.",
                [
                    ("Surface-component map prompt", optional_code_block("Surface-component map prompt", surface_component_map_prompt, "markdown")),
                    ("Surface-map token summary", token_summary_block("Surface-map token summary", surface_component_map_events)),
                    ("Deterministic draft", optional_code_block("Deterministic draft", surface_component_map_draft, "markdown")),
                    ("Final surface-component map", optional_code_block("Final surface-component map", surface_component_map, "markdown")),
                    ("Surface-map review prompt", optional_code_block("Surface-map review prompt", surface_component_map_review_prompt, "markdown") if surface_component_map_review_md.exists() or surface_component_map_review_json.exists() else ""),
                    ("Surface-map review summary", kv_block("Surface-map review summary", review_summary_rows(surface_component_map_review_json)) if surface_component_map_review_json.exists() else ""),
                    ("Surface-map review markdown", optional_code_block("Surface-map review markdown", surface_component_map_review_md, "markdown")),
                    ("Surface-map review JSON", optional_code_block("Surface-map review JSON", surface_component_map_review_json, "json")),
                ],
            )
        )
        next_step_number += 1

    if generation_source_value == "design_system":
        if design_pre_self_refine.exists():
            columns.append(
                build_column(
                    f"Step {next_step_number}",
                    "Initial design-system synthesis. This stage converts the grounding and surface/component map into the first schema-based design system draft before the self-refine repair loop.",
                    [
                        ("Design-system prompt", code_block("Design-system prompt", system_prompt, "markdown")),
                        ("Design-system token usage", token_summary_block("Design-system token usage", design_system_events)),
                        ("Design-system token breakdown", token_breakdown_block("Design-system token breakdown", design_system_events)),
                        ("Initial design system before self-refine", code_block("Initial design system before self-refine", design_pre_self_refine, "markdown")),
                    ],
                )
            )
            next_step_number += 1

            columns.append(
                build_column(
                    f"Step {next_step_number}",
                    "Self-refine repair and color sync. This stage reviews conversion loss in the initial draft, repairs the design system against that review, then applies source color/style sync to produce the final design system used downstream.",
                    [
                        ("Conversion-review prompt", optional_code_block("Conversion-review prompt", design_system_conversion_review_prompt, "markdown")),
                        ("Pre-self-refine conversion summary", kv_block("Pre-self-refine conversion summary", review_summary_rows(design_pre_self_refine_conversion_review_json)) if design_pre_self_refine_conversion_review_json.exists() else ""),
                        ("Pre-self-refine conversion markdown", optional_code_block("Pre-self-refine conversion markdown", design_pre_self_refine_conversion_review_md, "markdown")),
                        ("Pre-self-refine conversion JSON", optional_code_block("Pre-self-refine conversion JSON", design_pre_self_refine_conversion_review_json, "json")),
                        ("Color sync prompt", optional_code_block("Color sync prompt", color_sync_prompt, "markdown")),
                        ("Repaired design system before color sync", optional_code_block("Repaired design system before color sync", design_pre, "markdown")),
                        ("Final color-synced design system", code_block("Final color-synced design system", design_final, "markdown")),
                    ],
                )
            )
            next_step_number += 1
        else:
            columns.append(
                build_column(
                    f"Step {next_step_number}",
                    "Design-system synthesis. This stage converts the grounded page description into a reusable schema-based design system and then syncs explicit values back to the source CSS where possible.",
                    [
                        ("Design-system prompt", code_block("Design-system prompt", system_prompt, "markdown")),
                        ("Color sync prompt", optional_code_block("Color sync prompt", color_sync_prompt, "markdown")),
                        ("Design-system token usage", token_summary_block("Design-system token usage", design_system_events)),
                        ("Design-system token breakdown", token_breakdown_block("Design-system token breakdown", design_system_events)),
                        ("Conversion ledger", optional_code_block("Conversion ledger", design_system_conversion_ledger, "markdown")),
                        ("Pre-color-sync design system", code_block("Pre-color-sync design system", design_pre, "markdown")),
                        ("Final design system", code_block("Final design system", design_final, "markdown")),
                    ],
                )
            )
            next_step_number += 1

    if design_system_conversion_review_md.exists() or design_system_conversion_review_json.exists():
        columns.append(
            build_column(
                f"Step {next_step_number}",
                "Design-system conversion-loss review. This stage compares the surface/component map against the synthesized design system and scores whether the factual visual pairings survived the conversion into reusable schema language.",
                [
                    ("Conversion-review prompt", optional_code_block("Conversion-review prompt", design_system_conversion_review_prompt, "markdown")),
                    ("Conversion-review token usage", token_summary_block("Conversion-review token usage", design_system_conversion_events)),
                    ("Conversion-review summary", kv_block("Conversion-review summary", review_summary_rows(design_system_conversion_review_json)) if design_system_conversion_review_json.exists() else ""),
                    ("Conversion-review markdown", optional_code_block("Conversion-review markdown", design_system_conversion_review_md, "markdown")),
                    ("Conversion-review JSON", optional_code_block("Conversion-review JSON", design_system_conversion_review_json, "json")),
                ],
            )
        )
        next_step_number += 1

    if design_system_review_md.exists() or design_system_review_json.exists():
        columns.append(
            build_column(
                f"Step {next_step_number}",
                "Screenshot-based design-system review. This stage reviews the final design system section by section against the source screenshot and records score, weakest areas, and actionable learnings.",
                [
                    ("Design-system review prompt", optional_code_block("Design-system review prompt", design_system_review_prompt, "markdown")),
                    ("Design-system review token usage", token_summary_block("Design-system review token usage", design_system_review_events)),
                    ("Design-system review token breakdown", token_breakdown_block("Design-system review token breakdown", design_system_review_events)),
                    ("Design-system review summary", kv_block("Design-system review summary", review_summary_rows(design_system_review_json)) if design_system_review_json.exists() else ""),
                    ("Design-system review markdown", optional_code_block("Design-system review markdown", design_system_review_md, "markdown")),
                    ("Design-system review JSON", optional_code_block("Design-system review JSON", design_system_review_json, "json")),
                ],
            )
        )
        next_step_number += 1

    has_asset_artifacts = any(path.exists() for path in (claude_assets, gemini_assets, gpt54_assets)) or bool(site_asset_events)

    gen_step = f"Step {next_step_number}"
    next_step_number += 1
    outputs_step = f"Step {next_step_number}"
    next_step_number += 1
    asset_step = ""
    if has_asset_artifacts:
        asset_step = f"Step {next_step_number}"
        next_step_number += 1
    validator_step = f"Step {next_step_number}" if site_validator_prompt.exists() else ""
    if validator_step:
        next_step_number += 1
    review_step = f"Step {next_step_number}"

    columns.append(
        build_column(
            gen_step,
            "Generation input handed to all models. This is the final shared input that gets fanned out in parallel so Claude, Gemini, and GPT-5.5 all generate from the same source of truth.",
            [
                ("Website prompt", code_block("Website prompt", website_prompt, "markdown")),
                ("Site style sync prompt", optional_code_block("Site style sync prompt", site_style_sync_prompt, "markdown")),
                ("Site generation input", code_block("Site generation input", generation_input, "markdown")),
                (
                    "Parallel model fan-out",
                    kv_block(
                        "Parallel model fan-out",
                        [
                            ("Claude input", rel(generation_input)),
                            ("Gemini input", rel(generation_input)),
                            ("GPT-5.5 input", rel(generation_input)),
                        ],
                    ),
                ),
                ("Generation token summary", token_summary_block("Generation token summary", site_generation_events + site_style_sync_events)),
                ("Generation token breakdown", token_breakdown_block("Generation token breakdown", site_generation_events + site_style_sync_events)),
            ],
        )
    )

    outputs_subtitle = (
        "Parallel site outputs. These are the HTML results from each model after source-style sync and before the image asset replacement pass."
        if has_asset_artifacts
        else "Parallel site outputs. These are the HTML results from each model after source-style sync, with viewport-unit repair reports captured beside each file."
    )

    columns.append(
        build_column(
            outputs_step,
            outputs_subtitle,
            [
                ("Claude output", iframe_block("Claude output", claude_html)),
                ("Claude viewport-unit repair report", optional_code_block("Claude viewport-unit repair report", claude_viewport_units, "json")),
                ("Gemini output", iframe_block("Gemini output", gemini_html)),
                ("Gemini viewport-unit repair report", optional_code_block("Gemini viewport-unit repair report", gemini_viewport_units, "json")),
                ("GPT-5.5 output", iframe_block("GPT-5.5 output", gpt54_html)),
                ("GPT-5.5 viewport-unit repair report", optional_code_block("GPT-5.5 viewport-unit repair report", gpt54_viewport_units, "json")),
            ],
        )
    )

    if has_asset_artifacts:
        columns.append(
            build_column(
                asset_step,
                "Generated image asset pass. This stage scans each model's rendered HTML for meaningful image, SVG, and CSS-background targets, builds a placement-aware image prompt from the design system, generates PNG assets, and rewrites the HTML to use them.",
                [
                    ("Asset token summary", token_summary_block("Asset token summary", site_asset_events)),
                    ("Asset token breakdown", token_breakdown_block("Asset token breakdown", site_asset_events)),
                    ("Claude asset prompts and images", asset_manifest_block("Claude asset prompts and images", claude_assets) if claude_assets.exists() else ""),
                    ("Gemini asset prompts and images", asset_manifest_block("Gemini asset prompts and images", gemini_assets) if gemini_assets.exists() else ""),
                    ("GPT-5.5 asset prompts and images", asset_manifest_block("GPT-5.5 asset prompts and images", gpt54_assets) if gpt54_assets.exists() else ""),
                ],
            )
        )

    if validator_step:
        columns.append(
            build_column(
                validator_step,
                "Post-validator refinement. This stage checks each generated site against the design-system input, rewrites mismatches, and produces final HTML variants.",
                [
                    ("Site validator prompt", code_block("Site validator prompt", site_validator_prompt, "markdown")),
                    ("Validator token summary", token_summary_block("Validator token summary", site_validator_events + site_validator_style_sync_events)),
                    ("Validator token breakdown", token_breakdown_block("Validator token breakdown", site_validator_events + site_validator_style_sync_events)),
                    (
                        "Claude original vs post-validator",
                        paired_artifact(
                            "Claude original vs post-validator",
                            iframe_block("Claude original", claude_html),
                            iframe_block("Claude post-validator", claude_post_html),
                        ),
                    ),
                    (
                        "Gemini original vs post-validator",
                        paired_artifact(
                            "Gemini original vs post-validator",
                            iframe_block("Gemini original", gemini_html),
                            iframe_block("Gemini post-validator", gemini_post_html),
                        ),
                    ),
                    (
                        "GPT-5.5 original vs post-validator",
                        paired_artifact(
                            "GPT-5.5 original vs post-validator",
                            iframe_block("GPT-5.5 original", gpt54_html),
                            iframe_block("GPT-5.5 post-validator", gpt54_post_html),
                        ),
                    ),
                ],
            )
        )

    if gpt54_png.exists() or review_md.exists() or review_json.exists():
        columns.append(
            build_column(
                review_step,
                "Rendered-site review. This stage renders the final GPT-5.5 result, captures a screenshot, and scores how well the recovered output matches the intended grounded patterns and styling.",
                [
                    ("Rendered GPT-5.5 screenshot", optional_image_block("Rendered GPT-5.5 screenshot", gpt54_png)),
                    ("Review token usage", token_summary_block("Review token usage", site_review_events)),
                    ("Review prompt", optional_code_block("Review prompt", site_review_prompt, "markdown")),
                    ("Review summary", kv_block("Review summary", review_summary) if review_summary else ""),
                    ("Review markdown", optional_code_block("Review markdown", review_md, "markdown")),
                    ("Review JSON", optional_code_block("Review JSON", review_json, "json")),
                ],
            )
        )
    else:
        columns.append(
            build_column(
                review_step,
                f"Run summary and audit trail. This final column gathers the run status, token log, and version changelog so the walkthrough still closes with the actual {version} completion record when no rendered-site review screenshot was produced.",
                [
                    ("Run steps", code_block("Run steps", run_steps, "json")),
                    ("Token usage log", code_block("Token usage log", single_dir / "token-usage.jsonl", "json")),
                    ("Version changelog", optional_code_block("Version changelog", changes_md, "markdown")),
                ],
            )
        )

    title = f"{version.upper()} {item.capitalize()} Pipeline Walkthrough"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{html.escape(title)}</title>
  <style>
    :root {{
      --bg: #0f1115;
      --panel: #171a21;
      --panel-2: #1e2330;
      --border: #2a3140;
      --text: #eef2f7;
      --muted: #9ba7b7;
      --accent: #8bd3ff;
      --code: #10141b;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: linear-gradient(180deg, #0c0f14 0%, #11161d 100%);
      color: var(--text);
    }}
    .topbar {{
      position: sticky;
      top: 0;
      z-index: 10;
      padding: 14px 18px;
      border-bottom: 1px solid var(--border);
      background: rgba(15, 17, 21, 0.92);
      backdrop-filter: blur(10px);
    }}
    .topbar h1 {{
      margin: 0 0 6px;
      font-size: 18px;
    }}
    .topbar p {{
      margin: 0;
      color: var(--muted);
      font-size: 13px;
    }}
    .scroller {{
      display: flex;
      gap: 16px;
      overflow-x: auto;
      overflow-y: hidden;
      align-items: stretch;
      padding: 16px;
      height: calc(100vh - 74px);
      width: 100%;
    }}
    .step-column {{
      flex: 0 0 980px;
      max-width: 980px;
      height: calc(100vh - 106px);
      display: flex;
      flex-direction: column;
      overflow-y: auto;
      overflow-x: hidden;
      scroll-behavior: smooth;
      overscroll-behavior: contain;
      background: linear-gradient(180deg, var(--panel) 0%, var(--panel-2) 100%);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 16px;
      box-shadow: 0 20px 40px rgba(0,0,0,.28);
    }}
    .step-column.step-5 {{
      flex-basis: 1900px;
      max-width: 1900px;
    }}
    .step-column header {{
      margin-bottom: 16px;
      padding-bottom: 12px;
      border-bottom: 1px solid var(--border);
    }}
    .step-column h2 {{
      margin: 0 0 6px;
      font-size: 18px;
    }}
    .step-column p {{
      margin: 0;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.45;
    }}
    .step-body {{
      display: grid;
      grid-template-columns: 210px minmax(0, 1fr);
      gap: 16px;
      align-items: start;
    }}
    .step-nav {{
      position: sticky;
      top: 12px;
      align-self: start;
      border: 1px solid var(--border);
      border-radius: 12px;
      background: rgba(12, 15, 20, 0.72);
      padding: 12px;
    }}
    .step-nav-title {{
      font-size: 12px;
      font-weight: 700;
      color: var(--text);
      margin-bottom: 10px;
      letter-spacing: 0.02em;
      text-transform: uppercase;
    }}
    .step-nav-list {{
      margin: 0;
      padding: 0;
      list-style: none;
      display: grid;
      gap: 8px;
    }}
    .step-nav-list a {{
      color: var(--accent);
      text-decoration: none;
      font-size: 12px;
      line-height: 1.4;
      display: block;
      padding: 7px 9px;
      border-radius: 8px;
      border: 1px solid transparent;
      transition: background-color 120ms ease, border-color 120ms ease, color 120ms ease;
    }}
    .step-nav-list a:hover {{
      background: rgba(139, 211, 255, 0.08);
      border-color: rgba(139, 211, 255, 0.16);
    }}
    .step-nav-list a.active {{
      background: rgba(139, 211, 255, 0.14);
      border-color: rgba(139, 211, 255, 0.28);
      color: #dff4ff;
      font-weight: 600;
    }}
    .step-content {{
      min-width: 0;
      padding-right: 4px;
    }}
    .artifact {{
      margin-bottom: 16px;
      border: 1px solid var(--border);
      border-radius: 12px;
      overflow: hidden;
      background: rgba(12, 15, 20, 0.45);
    }}
    .artifact-stack {{
      display: grid;
      gap: 12px;
      padding: 12px;
    }}
    .artifact-pair {{
      display: grid;
      grid-template-columns: minmax(360px, 0.95fr) minmax(0, 1.15fr);
      gap: 12px;
      padding: 12px;
      align-items: start;
    }}
    .step-column.step-5 .artifact-pair {{
      grid-template-columns: minmax(500px, 0.55fr) minmax(1080px, 1.45fr);
    }}
    .artifact-pair-shell {{
      overflow: visible;
    }}
    .artifact-pair-media {{
      position: sticky;
      top: 12px;
      align-self: start;
    }}
    .artifact-stack .artifact {{
      margin-bottom: 0;
    }}
    .artifact-pair .artifact {{
      margin-bottom: 0;
    }}
    .artifact-meta {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: center;
      padding: 10px 12px;
      border-bottom: 1px solid var(--border);
      background: rgba(255,255,255,0.02);
      font-size: 12px;
    }}
    .artifact-label {{
      color: var(--text);
      font-weight: 600;
    }}
    .artifact a {{
      color: var(--accent);
      text-decoration: none;
      word-break: break-all;
    }}
    img {{
      display: block;
      width: 100%;
      height: auto;
      background: #fff;
    }}
    iframe {{
      display: block;
      width: 100%;
      height: 520px;
      border: 0;
      background: #fff;
    }}
    pre {{
      margin: 0;
      padding: 14px;
      background: var(--code);
      color: #d9e2ef;
      overflow: auto;
      font-size: 12px;
      line-height: 1.5;
      white-space: pre-wrap;
      word-break: break-word;
    }}
    .kv-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 12px;
    }}
    .kv-table th,
    .kv-table td {{
      padding: 10px 12px;
      border-top: 1px solid var(--border);
      vertical-align: top;
      text-align: left;
    }}
    .kv-table th {{
      width: 160px;
      color: var(--muted);
      font-weight: 600;
    }}
    .link-list {{
      margin: 0;
      padding: 12px 18px 16px 32px;
      font-size: 12px;
      line-height: 1.6;
    }}
    .link-list a {{
      color: var(--accent);
      text-decoration: none;
    }}
    @media (max-width: 1200px) {{
      .step-column {{
        flex-basis: 860px;
        max-width: 860px;
      }}
      .step-column.step-5 {{
        flex-basis: 1500px;
        max-width: 1500px;
      }}
      .step-body {{
        grid-template-columns: 180px minmax(0, 1fr);
      }}
      .step-column.step-5 .artifact-pair {{
        grid-template-columns: minmax(400px, 0.5fr) minmax(760px, 1.5fr);
      }}
    }}
    @media (max-width: 900px) {{
      .step-column {{
        flex-basis: 92vw;
        max-width: 92vw;
        height: calc(100vh - 106px);
      }}
      .step-body {{
        grid-template-columns: 1fr;
      }}
      .step-nav {{
        position: static;
      }}
      .artifact-pair {{
        grid-template-columns: 1fr;
      }}
    }}
  </style>
</head>
<body>
  <div class="topbar">
    <h1>{html.escape(title)}</h1>
    <p>Each column is one pipeline stage. Scroll right to follow the full process from raw screenshot through grounding, design-system synthesis, model generation, generated image assets, and review.</p>
  </div>
  <main class="scroller">
    {''.join(columns)}
  </main>
  <script>
    (() => {{
      const scroller = document.querySelector('.scroller');
      const columns = Array.from(document.querySelectorAll('.step-column'));
      for (const column of columns) {{
        const links = Array.from(column.querySelectorAll('.step-nav-list a'));
        if (!links.length) continue;

        const sections = links
          .map((link) => {{
            const id = (link.getAttribute('href') || '').slice(1);
            const node = id ? column.querySelector(`#${{CSS.escape(id)}}`) : null;
            return node ? {{ link, node }} : null;
          }})
          .filter(Boolean);

        const setActive = () => {{
          let active = sections[0] || null;
          const columnTop = column.getBoundingClientRect().top;
          for (const entry of sections) {{
            const rect = entry.node.getBoundingClientRect();
            if (rect.top - columnTop <= 120) {{
              active = entry;
            }}
          }}
          for (const entry of sections) {{
            entry.link.classList.toggle('active', entry === active);
          }}
        }};

        for (const entry of sections) {{
          entry.link.addEventListener('click', (event) => {{
            event.preventDefault();
            entry.node.scrollIntoView({{ behavior: 'smooth', block: 'start', inline: 'nearest' }});
          }});
        }}

        column.addEventListener('scroll', setActive, {{ passive: true }});
        window.addEventListener('resize', setActive);
        setActive();
      }}

      if (scroller) {{
        document.addEventListener('wheel', (event) => {{
          const target = event.target;
          if (!(target instanceof Element)) return;
          if (!target.closest('.scroller')) return;
          const absX = Math.abs(event.deltaX);
          const absY = Math.abs(event.deltaY);
          if (absX < 1) return;
          if (absY > absX) return;
          scroller.scrollLeft += event.deltaX;
          event.preventDefault();
        }}, {{ passive: false, capture: true }});
      }}
    }})();
  </script>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--item", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    output = Path(args.output)
    output.write_text(build_html(args.version, args.item))
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
