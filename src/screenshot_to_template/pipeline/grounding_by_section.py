"""Section-by-section grounding pipeline for structural analysis."""

import concurrent.futures
import json
import re
import sys
from pathlib import Path

import yaml
from PIL import Image, ImageDraw

from ..config import AppConfig
from ..models import get_provider
from ..output import clean_markdown, generate_section_map
from ..tracking import token_usage_context, update_step_status
from .single_shot import build_single_shot_views, encode_pil_image
from .splitter import compute_crop_bounds, crop_sections, detect_sections_with_llm

TRANSITION_CONTEXT_PX = 100
BOUNDARY_STRIP_CONTEXT_PX = 140


def _safe_label_slug(label: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")
    return slug or "section"


def _find_cached_section_file(section_dir: Path, index: int, label: str) -> Path:
    exact = section_dir / f"{index:02d}-{_safe_label_slug(label)}.yaml"
    if exact.exists():
        return exact

    prefix_matches = sorted(section_dir.glob(f"{index:02d}-*.yaml"))
    if prefix_matches:
        return prefix_matches[0]

    legacy_exact = section_dir / f"{index:02d}-{_safe_label_slug(label)}.md"
    if legacy_exact.exists():
        return legacy_exact

    prefix_matches = sorted(section_dir.glob(f"{index:02d}-*.md"))
    if prefix_matches:
        return prefix_matches[0]

    return exact


def _build_section_sequence(sections: list[dict]) -> str:
    lines = []
    for index, section in enumerate(sections, start=1):
        lines.append(
            f"{index}. {section['label']} (y={section['y_start']} to y={section['y_end']})"
        )
    return "\n".join(lines)


def _encode_highlighted_full_page(
    image_path: str,
    bounds: dict,
    max_dimension: int,
) -> str:
    img = Image.open(image_path)
    if img.mode != "RGBA":
        img = img.convert("RGBA")

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rectangle((0, 0, img.size[0], img.size[1]), fill=(0, 0, 0, 110))
    draw.rectangle(
        (0, bounds["y_start"], img.size[0], bounds["y_end"]),
        fill=(0, 0, 0, 0),
    )

    composited = Image.alpha_composite(img, overlay)
    outline = ImageDraw.Draw(composited)
    outline.rectangle(
        (2, bounds["y_start"] + 2, img.size[0] - 3, bounds["y_end"] - 3),
        outline=(255, 76, 60, 255),
        width=8,
    )

    return encode_pil_image(composited.convert("RGB"), max_dimension)


def _build_boundary_strip(image, boundary_y: int, context_px: int = BOUNDARY_STRIP_CONTEXT_PX):
    top = max(0, boundary_y - context_px)
    bottom = min(image.size[1], boundary_y + context_px)
    return image.crop((0, top, image.size[0], bottom))


def _grounding_document_is_complete(text: str) -> bool:
    if _normalized_ast_document_is_complete(text):
        return True

    required_markers = (
        "# Structural Analysis",
        "## Section Inventory",
        "## Cross-section Notes",
        "## Ambiguities",
    )
    return all(marker in text for marker in required_markers)


def _normalized_ast_document_is_complete(text: str) -> bool:
    """Return True when the merge output is a normalized site AST YAML document."""
    stripped = re.sub(r"^```(?:yaml|yml)?\s*|\s*```$", "", text.strip(), flags=re.IGNORECASE)
    if not stripped:
        return False
    try:
        parsed = yaml.safe_load(stripped)
    except yaml.YAMLError:
        return False
    if not isinstance(parsed, dict):
        return False
    return (
        parsed.get("type") == "normalized_site_ast"
        and isinstance(parsed.get("sections"), list)
        and bool(parsed.get("sections"))
        and isinstance(parsed.get("global_observations"), dict)
        and isinstance(parsed.get("component_candidates"), list)
    )


def _build_fallback_grounding_document(
    inventory_response: str,
    sections: list[dict],
    section_results: list[dict],
) -> str:
    """Build a structurally complete grounding document when model merge retries fail."""
    lines: list[str] = [
        "# Structural Analysis",
        "",
        "## Section Inventory",
        "",
        clean_markdown(inventory_response).strip() or "- Section inventory unavailable.",
        "",
    ]

    for index, entry in enumerate(section_results, start=1):
        section = sections[index - 1] if index - 1 < len(sections) else {}
        label = entry.get("label") or section.get("label") or f"Section {index}"
        bounds = entry.get("bounds") or {}
        y_start = bounds.get("y_start", section.get("y_start", "unknown"))
        y_end = bounds.get("y_end", section.get("y_end", "unknown"))
        lines.extend([
            f"## Section {index}: {label}",
            "",
            f"- **Approximate boundaries:** y={y_start} to y={y_end}",
            "- **Generic role:** see grounded section observations below",
            "- **Evidence notes:** generated from cached per-section grounding because the final merge response was incomplete.",
            "",
            clean_markdown(entry.get("analysis", "")).strip() or "- No section analysis was available.",
            "",
        ])

    lines.extend([
        "## Cross-section Notes",
        "",
        "- The model merge step did not return a complete structural document after retries, so this fallback preserves the per-section grounding without additional synthesis.",
        "- Treat repeated patterns, surface relationships, and typography hierarchy as grounded in the individual section notes above.",
        "",
        "## Ambiguities",
        "",
        "- Cross-section synthesis may be less normalized than usual because the fallback document avoided inventing details after merge failure.",
    ])
    return "\n".join(lines).rstrip()


def _build_section_visual_inputs(
    image_path: str,
    img_crop,
    bounds: dict,
    max_dimension: int,
    include_full_page_context: bool,
) -> tuple[str, list[tuple[str, str]] | None, str]:
    image_b64 = encode_pil_image(img_crop, max_dimension)
    if include_full_page_context:
        full_page_views = build_single_shot_views(image_path, max_dimension)
        full_page_overview_b64 = full_page_views[0][1]
        highlighted_full_page_b64 = _encode_highlighted_full_page(
            image_path=image_path,
            bounds=bounds,
            max_dimension=max_dimension,
        )
        user_prompt = (
            "Analyze only the target section.\n"
            "Image 1 is the crop of the target section.\n"
            "Image 2 is the full-page overview for context.\n"
            "Image 3 is the full-page overview with the target section highlighted.\n"
            "Use the full-page views only for placement and immediate neighbor context.\n"
            "Do not use them to invent same-background groups or to make final transition decisions in this step.\n"
            "Keep this analysis focused on the target section itself."
        )
        additional_images = [
            ("full-page overview", full_page_overview_b64),
            ("highlighted target section", highlighted_full_page_b64),
        ]
    else:
        user_prompt = (
            "Analyze only the target section.\n"
            "Image 1 is the exact crop of the target section.\n"
            "Do not infer details from the rest of the page beyond the written section list and neighboring section labels provided in the prompt."
        )
        additional_images = None

    return image_b64, additional_images, user_prompt


def _extract_named_value(text: str, label: str) -> str | None:
    patterns = (
        re.compile(
            rf"^\s*(?:[-*]\s*)?\*\*{re.escape(label)}:\*\*\s*(.+?)\s*$",
            flags=re.MULTILINE,
        ),
        re.compile(
            rf"^\s*(?:[-*]\s*)?\*\*{re.escape(label)}\*\*:\s*(.+?)\s*$",
            flags=re.MULTILINE,
        ),
        re.compile(
            rf"^\s*(?:[-*]\s*)?{re.escape(label)}:\s*(.+?)\s*$",
            flags=re.MULTILINE,
        ),
    )
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            return match.group(1).strip()
    return None


def _extract_json_object(text: str) -> dict | None:
    text = text.strip()
    if not text:
        return None

    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        return None

    try:
        parsed = json.loads(match.group(0))
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        return None


def _replace_named_value(section_analysis: str, label: str, value: str) -> str:
    patterns = (
        re.compile(
            rf"^(?P<prefix>\s*(?:[-*]\s*)?\*\*{re.escape(label)}:\*\*\s*).+$",
            flags=re.MULTILINE,
        ),
        re.compile(
            rf"^(?P<prefix>\s*(?:[-*]\s*)?\*\*{re.escape(label)}\*\*:\s*).+$",
            flags=re.MULTILINE,
        ),
        re.compile(
            rf"^(?P<prefix>\s*(?:[-*]\s*)?{re.escape(label)}:\s*).+$",
            flags=re.MULTILINE,
        ),
    )
    for pattern in patterns:
        if pattern.search(section_analysis):
            return pattern.sub(rf"\g<prefix>{value}", section_analysis, count=1)

    section_heading = "### Section"
    if section_heading not in section_analysis:
        return section_analysis

    lines = section_analysis.splitlines()
    for index, line in enumerate(lines):
        if line.strip() == section_heading:
            insert_at = index + 1
            while insert_at < len(lines) and lines[insert_at].startswith("- **"):
                insert_at += 1
            lines.insert(insert_at, f"- **{label}:** {value}")
            return "\n".join(lines)

    return section_analysis


def _extract_transition_payload(text: str) -> dict[str, str]:
    if parsed := _extract_json_object(text):
        key_map = {
            "transition_from_previous_section": "Transition from previous section",
            "transition_to_next_section": "Transition to next section",
            "boundary_relationship_to_previous_section": "Boundary relationship to previous section",
            "boundary_relationship_to_next_section": "Boundary relationship to next section",
            "navigation_relationship_to_hero": "Navigation relationship to hero",
        }
        payload: dict[str, str] = {}
        for key, label in key_map.items():
            value = parsed.get(key)
            if isinstance(value, str) and value.strip():
                payload[label] = value.strip()
        if payload:
            return payload

    labels = (
        "Transition from previous section",
        "Transition to next section",
        "Boundary relationship to previous section",
        "Boundary relationship to next section",
        "Navigation relationship to hero",
    )
    return {
        label: value
        for label in labels
        if (value := _extract_named_value(text, label))
    }


def _apply_transition_override(section_analysis: str, transition_text: str) -> str:
    updated = section_analysis
    for label, value in _extract_transition_payload(transition_text).items():
        updated = _replace_named_value(updated, label, value)
    return updated


def _build_full_page_review_context(section_results: list[dict]) -> str:
    review_only_fields = (
        "Navigation relationship to hero",
        "Transition from previous section",
        "Transition to next section",
        "Background group",
        "Background graphic relationship",
        "Container width relationship",
        "Container width group",
    )
    blocks = []
    for index, entry in enumerate(section_results, start=1):
        sanitized_analysis = entry["analysis"]
        for label in review_only_fields:
            patterns = (
                re.compile(
                    rf"^\s*(?:[-*]\s*)?\*\*{re.escape(label)}:\*\*\s*.+$\n?",
                    flags=re.MULTILINE,
                ),
                re.compile(
                    rf"^\s*(?:[-*]\s*)?\*\*{re.escape(label)}\*\*:\s*.+$\n?",
                    flags=re.MULTILINE,
                ),
                re.compile(
                    rf"^\s*(?:[-*]\s*)?{re.escape(label)}:\s*.+$\n?",
                    flags=re.MULTILINE,
                ),
            )
            for pattern in patterns:
                sanitized_analysis = pattern.sub("", sanitized_analysis)
        sanitized_analysis = re.sub(r"\n{3,}", "\n\n", sanitized_analysis).strip()
        blocks.append(
            f"## Section {index}: {entry['label']}\n"
            f"- Bounds: y={entry['bounds']['y_start']} to y={entry['bounds']['y_end']}\n"
            f"{sanitized_analysis}"
        )
    return "\n\n---\n\n".join(blocks)


def _apply_full_page_review_to_analysis(section_analysis: str, review_entry: dict) -> str:
    updated = section_analysis

    mappings = {
        "transition_from_previous_section": "Transition from previous section",
        "transition_to_next_section": "Transition to next section",
        "navigation_relationship_to_hero": "Navigation relationship to hero",
        "background_graphic_relationship": "Background graphic relationship",
        "background_group_id": "Background group",
        "container_width_relationship": "Container width relationship",
        "container_width_group_id": "Container width group",
    }
    for key, label in mappings.items():
        value = review_entry.get(key)
        if isinstance(value, str) and value.strip():
            updated = _replace_named_value(updated, label, value.strip())

    return updated


def _compact_section_analysis_for_normalized_merge(text: str, max_chars: int = 5000) -> str:
    """Keep normalized-AST merge inputs complete enough without resending huge raw YAML."""
    stripped = text.strip()
    if len(stripped) <= max_chars:
        return stripped

    priority_patterns = re.compile(
        r"(schema_version|^type:|^source:|^section:|^tree:|^component_anatomy:|"
        r"observed_values:|consolidation_notes:|background|surface|color|typography|"
        r"spacing|radius|shadow|border|divider|button|link|card|panel|label|"
        r"media|graphic|image|pattern|gradient|width_behavior|implementation_assumption|"
        r"do_not_generalize|uncertainties)",
        flags=re.IGNORECASE | re.MULTILINE,
    )
    kept_lines: list[str] = []
    current_chars = 0
    for raw_line in stripped.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            continue
        if priority_patterns.search(line) or line.startswith(("  - id:", "    - id:", "      - id:")):
            kept_lines.append(line)
            current_chars += len(line) + 1
        if current_chars >= max_chars:
            break

    compacted = "\n".join(kept_lines).strip()
    if len(compacted) < max_chars // 3:
        compacted = stripped[:max_chars].rstrip()
    return (
        compacted[:max_chars].rstrip()
        + "\n# compacted_for_normalized_merge: full raw section YAML is saved in section-groundings/"
    )


def _extract_full_page_review_payload(text: str) -> dict | None:
    return _extract_json_object(text)


def _strip_code_fence(text: str) -> str:
    stripped = text.strip()
    stripped = re.sub(r"^```(?:yaml|yml|json)?\s*", "", stripped, flags=re.IGNORECASE)
    stripped = re.sub(r"\s*```$", "", stripped)
    return stripped.strip()


def _run_global_site_capture(
    *,
    provider,
    image_path: str,
    config: AppConfig,
    global_site_prompt: str,
    total: int,
    section_sequence: str,
    inventory_response: str,
    sections: list[dict],
    full_page_review_raw: str,
    output_dir: str | None,
) -> str:
    prompt = global_site_prompt.format(
        total_sections=total,
        section_sequence=section_sequence,
    )
    user_prompt = (
        "Analyze the full-page screenshot for global page-layer facts only. "
        "Do not re-describe every section. Focus on section groups that share one visual layer, "
        "continuous background runs, nav/hero surface continuity, full-page edge behavior, repeated global motifs, "
        "and any hard resets between groups.\n\n"
        "## Section Inventory\n\n"
        f"{clean_markdown(inventory_response)}\n\n"
        "## Final Detected Sections\n\n"
        f"{json.dumps(sections, indent=2)}\n\n"
        + (
            "## Full-Page Review Overrides\n\n"
            f"{full_page_review_raw}\n\n"
            if full_page_review_raw
            else ""
        )
    )
    full_page_views = build_single_shot_views(image_path, config.max_image_dimension)
    with token_usage_context(output_dir, "global_site_grounding", {"total_sections": total}):
        raw = provider.analyze_image(
            image_b64=full_page_views[0][1],
            system_prompt=prompt,
            user_prompt=user_prompt,
            max_tokens=min(max(config.max_tokens, 4096), 8192),
            additional_images=full_page_views[1:] if len(full_page_views) > 1 else None,
        )
    return _strip_code_fence(clean_markdown(raw))


def _run_section_agents(
    provider,
    image_b64: str,
    additional_images: list[tuple[str, str]] | None,
    user_prompt: str,
    section_prompt_values: dict,
    section_agent_prompts: list[tuple[str, str]],
    section_agent_merge_prompt: str,
    max_tokens: int,
    output_dir: Path | None,
    output_stem: str,
) -> str:
    agent_outputs: list[tuple[str, str]] = []

    for agent_name, agent_prompt in section_agent_prompts:
        prompt = agent_prompt.format(**section_prompt_values)
        result = provider.analyze_image(
            image_b64=image_b64,
            system_prompt=prompt,
            user_prompt=user_prompt,
            max_tokens=min(max_tokens, 1536),
            additional_images=additional_images,
        )
        cleaned = clean_markdown(result)
        agent_outputs.append((agent_name, cleaned))

        if output_dir:
            agent_dir = output_dir / output_stem
            agent_dir.mkdir(parents=True, exist_ok=True)
            with open(agent_dir / f"{agent_name}.md", "w") as f:
                f.write(cleaned)
                f.write("\n")

    merge_prompt = section_agent_merge_prompt.format(**section_prompt_values)
    merge_input = "\n\n---\n\n".join(
        f"## {agent_name.title()} Agent\n\n{text}"
        for agent_name, text in agent_outputs
    )
    merged = provider.text_query(
        system_prompt=merge_prompt,
        user_prompt=merge_input,
        max_tokens=min(max_tokens, 4096),
    )
    return clean_markdown(merged)


def run(
    image_path: str,
    config: AppConfig,
    inventory_prompt: str,
    section_prompt: str,
    merge_prompt: str,
    include_full_page_context: bool = True,
    transition_prompt: str | None = None,
    full_page_review_prompt: str | None = None,
    global_site_prompt: str | None = None,
    ignore_cache: bool = False,
    section_agent_prompts: list[tuple[str, str]] | None = None,
    section_agent_merge_prompt: str | None = None,
    output_dir: str | None = None,
) -> str:
    """Run full-page section inventory, per-section grounding, and merged grounding."""
    provider = get_provider(config)

    if config.verbose:
        print(f"Using {config.provider}/{config.model}", file=sys.stderr)
        print("Detecting sections for section-by-section grounding...", file=sys.stderr)

    detection_config = AppConfig(
        **{
            **vars(config),
            "section_inventory_prompt": inventory_prompt,
        }
    )
    if output_dir:
        update_step_status(output_dir, "section_detection", "in_progress")
    with token_usage_context(output_dir, "section_detection"):
        detection = detect_sections_with_llm(image_path, provider, detection_config)
    if output_dir:
        update_step_status(output_dir, "section_detection", "completed", {"sections_detected": len(detection.final_sections)})
    sections = detection.final_sections

    if not sections:
        raise ValueError("No sections were detected for grounding.")

    source_img = Image.open(image_path).convert("RGB")
    crop_bounds = compute_crop_bounds(sections, source_img.size[1])
    crops = crop_sections(image_path, sections)
    if transition_prompt:
        expanded_crop_bounds = compute_crop_bounds(
            sections,
            source_img.size[1],
            overlap_px=TRANSITION_CONTEXT_PX,
        )
        expanded_crops = crop_sections(
            image_path,
            sections,
            overlap_px=TRANSITION_CONTEXT_PX,
        )
    else:
        expanded_crop_bounds = [None] * len(crops)
        expanded_crops = [(None, label) for _, label in crops]
    total = len(crops)
    section_sequence = _build_section_sequence(sections)

    out: Path | None = None
    if output_dir:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        with open(out / "section-inventory.md", "w") as f:
            f.write(clean_markdown(detection.inventory_response))
            f.write("\n")
        with open(out / "section-detection-raw.txt", "w") as f:
            f.write(detection.raw_response.rstrip())
            f.write("\n")
        with open(out / "sections.json", "w") as f:
            json.dump(sections, f, indent=2)
        generate_section_map(
            screenshot_path=image_path,
            output_path=out / "section-map.html",
            sections=sections,
            crop_bounds=crop_bounds,
        )
        crops_dir = out / "crops"
        crops_dir.mkdir(exist_ok=True)
        for index, (img_crop, label) in enumerate(crops, start=1):
            img_crop.save(crops_dir / f"{index:02d}-{_safe_label_slug(label)}.png")
        if transition_prompt:
            with open(out / "expanded-crop-bounds.json", "w") as f:
                json.dump(expanded_crop_bounds, f, indent=2)
            expanded_crops_dir = out / "expanded-crops"
            expanded_crops_dir.mkdir(exist_ok=True)
            for index, (img_crop, label) in enumerate(expanded_crops, start=1):
                if img_crop is not None:
                    img_crop.save(expanded_crops_dir / f"{index:02d}-{_safe_label_slug(label)}.png")
            boundary_crops_dir = out / "boundary-crops"
            boundary_crops_dir.mkdir(exist_ok=True)
        else:
            boundary_crops_dir = None
    else:
        boundary_crops_dir = None

    section_results: list[dict] = []
    ordered_results: list[dict | None] = [None] * total
    pending_jobs: list[
        tuple[int, object, object, object | None, object | None, str, dict, dict, str, str, Path | None, Path | None]
    ] = []

    if out:
        section_dir = out / "section-groundings"
        section_dir.mkdir(exist_ok=True)
        transition_dir = out / "section-transitions"
        transition_dir.mkdir(exist_ok=True)
    else:
        section_dir = None
        transition_dir = None

    for index, ((img_crop, label), (expanded_crop, _expanded_label), bounds, expanded_bounds) in enumerate(
        zip(crops, expanded_crops, crop_bounds, expanded_crop_bounds),
        start=1,
    ):
        previous_label = sections[index - 2]["label"] if index > 1 else "N/A"
        next_label = sections[index]["label"] if index < total else "N/A"
        if transition_prompt:
            top_boundary_crop = _build_boundary_strip(source_img, bounds["y_start"]) if index > 1 else None
            bottom_boundary_crop = _build_boundary_strip(source_img, bounds["y_end"]) if index < total else None
        else:
            top_boundary_crop = None
            bottom_boundary_crop = None
        section_file = _find_cached_section_file(section_dir, index, label) if section_dir else None
        transition_file = (
            transition_dir / f"{index:02d}-{_safe_label_slug(label)}.md"
            if transition_dir
            else None
        )

        if boundary_crops_dir:
            boundary_stem = f"{index:02d}-{_safe_label_slug(label)}"
            if top_boundary_crop is not None:
                top_boundary_crop.save(boundary_crops_dir / f"{boundary_stem}-top.png")
            if bottom_boundary_crop is not None:
                bottom_boundary_crop.save(boundary_crops_dir / f"{boundary_stem}-bottom.png")

        if section_file and section_file.exists() and not ignore_cache:
            cleaned_result = clean_markdown(section_file.read_text())
            if cleaned_result:
                if config.verbose:
                    print(
                        f"Reusing cached grounding for section {index}/{total}: {label}...",
                        file=sys.stderr,
                    )
                ordered_results[index - 1] = {
                    "label": label,
                    "bounds": bounds,
                    "analysis": cleaned_result,
                }
                continue

        pending_jobs.append(
            (
                index,
                img_crop,
                expanded_crop,
                top_boundary_crop,
                bottom_boundary_crop,
                label,
                bounds,
                expanded_bounds,
                previous_label,
                next_label,
                section_file,
                transition_file,
            )
        )

    def process_section_job(
        job: tuple[int, object, object, object | None, object | None, str, dict, dict, str, str, Path | None, Path | None]
    ) -> tuple[int, dict]:
        index, img_crop, expanded_crop, top_boundary_crop, bottom_boundary_crop, label, bounds, expanded_bounds, previous_label, next_label, section_file, transition_file = job
        local_provider = get_provider(config)

        if config.verbose:
            print(f"Grounding section {index}/{total}: {label}...", file=sys.stderr)

        section_prompt_values = dict(
            section_num=index,
            total_sections=total,
            section_label=label,
            section_y_start=bounds["y_start"],
            section_y_end=bounds["y_end"],
            crop_y_start=bounds["crop_y_start"],
            crop_y_end=bounds["crop_y_end"],
            expanded_crop_y_start=expanded_bounds["crop_y_start"] if expanded_bounds else bounds["crop_y_start"],
            expanded_crop_y_end=expanded_bounds["crop_y_end"] if expanded_bounds else bounds["crop_y_end"],
            previous_section_label=previous_label,
            next_section_label=next_label,
            section_sequence=section_sequence,
        )
        image_b64, additional_images, user_prompt = _build_section_visual_inputs(
            image_path=image_path,
            img_crop=img_crop,
            bounds=bounds,
            max_dimension=config.max_image_dimension,
            include_full_page_context=include_full_page_context,
        )

        if section_agent_prompts and section_agent_merge_prompt:
            with token_usage_context(output_dir, f"section_grounding_{index:02d}", {"section_label": label}):
                cleaned_result = _run_section_agents(
                    provider=local_provider,
                    image_b64=image_b64,
                    additional_images=additional_images,
                    user_prompt=user_prompt,
                    section_prompt_values=section_prompt_values,
                    section_agent_prompts=section_agent_prompts,
                    section_agent_merge_prompt=section_agent_merge_prompt,
                    max_tokens=config.max_tokens,
                    output_dir=(out / "section-agent-groundings") if out else None,
                    output_stem=f"{index:02d}-{_safe_label_slug(label)}",
                )
        else:
            prompt = section_prompt.format(**section_prompt_values)
            with token_usage_context(output_dir, f"section_grounding_{index:02d}", {"section_label": label}):
                result = local_provider.analyze_image(
                    image_b64=image_b64,
                    system_prompt=prompt,
                    user_prompt=user_prompt,
                    max_tokens=config.max_tokens,
                    additional_images=additional_images,
                )
            cleaned_result = clean_markdown(result)

        if transition_prompt and expanded_crop is not None:
            transition_prompt_text = transition_prompt.format(**section_prompt_values)
            transition_additional_images = []
            if top_boundary_crop is not None:
                transition_additional_images.append(
                    ("top boundary strip", encode_pil_image(top_boundary_crop, config.max_image_dimension))
                )
            if bottom_boundary_crop is not None:
                transition_additional_images.append(
                    ("bottom boundary strip", encode_pil_image(bottom_boundary_crop, config.max_image_dimension))
                )
            with token_usage_context(output_dir, f"section_transition_{index:02d}", {"section_label": label}):
                transition_result = local_provider.analyze_image(
                    image_b64=encode_pil_image(expanded_crop, config.max_image_dimension),
                    system_prompt=transition_prompt_text,
                    user_prompt=(
                        "Analyze only the section boundaries.\n"
                        "Image 1 is the expanded crop for the target section.\n"
                        "Additional images, when present, are narrow boundary strips centered on the exact top and bottom cut lines.\n"
                        "Return only the requested transition fields."
                    ),
                    max_tokens=min(config.max_tokens, 768),
                    additional_images=transition_additional_images or None,
                )
            cleaned_transition = clean_markdown(transition_result)
            cleaned_result = _apply_transition_override(cleaned_result, cleaned_transition)
            if transition_file:
                with open(transition_file, "w") as f:
                    f.write(cleaned_transition)
                    f.write("\n")

        if section_file:
            section_file.write_text(cleaned_result.rstrip() + "\n")
            if section_file.suffix == ".yaml":
                legacy_md = section_file.with_suffix(".md")
                legacy_md.write_text(cleaned_result.rstrip() + "\n")

        return index - 1, {
            "label": label,
            "bounds": bounds,
            "analysis": cleaned_result,
        }

    if pending_jobs:
        section_workers = min(4, len(pending_jobs))
        with concurrent.futures.ThreadPoolExecutor(max_workers=section_workers) as pool:
            futures = [pool.submit(process_section_job, job) for job in pending_jobs]
            for future in concurrent.futures.as_completed(futures):
                result_index, result_payload = future.result()
                ordered_results[result_index] = result_payload

    section_results = [entry for entry in ordered_results if entry is not None]

    full_page_review_raw = ""
    full_page_review_payload: dict | None = None
    if full_page_review_prompt:
        if config.verbose:
            print("Running full-page review for transitions and grouped section backgrounds...", file=sys.stderr)
        if output_dir:
            update_step_status(output_dir, "full_page_review", "in_progress")

        review_prompt = full_page_review_prompt.format(
            total_sections=total,
            section_sequence=section_sequence,
        )
        review_context = _build_full_page_review_context(section_results)
        full_page_views = build_single_shot_views(image_path, config.max_image_dimension)
        with token_usage_context(output_dir, "full_page_review", {"total_sections": total}):
            review_result = provider.analyze_image(
                image_b64=full_page_views[0][1],
                system_prompt=review_prompt,
                user_prompt=(
                    "Use the full-page screenshot and the grounded per-section observations below to determine "
                    "the final from/to transitions for every section and which sections belong to the same background group.\n\n"
                    f"{review_context}"
                ),
                max_tokens=max(config.max_tokens, 4096),
            )
        full_page_review_raw = clean_markdown(review_result)
        full_page_review_payload = _extract_full_page_review_payload(full_page_review_raw)
        if output_dir:
            update_step_status(output_dir, "full_page_review", "completed")

        if out:
            with open(out / "full-page-review.json", "w") as f:
                f.write(full_page_review_raw)
                f.write("\n")

        if full_page_review_payload:
            review_sections = full_page_review_payload.get("sections", [])
            review_by_index = {
                entry.get("section_num"): entry
                for entry in review_sections
                if isinstance(entry, dict) and isinstance(entry.get("section_num"), int)
            }
            for index, entry in enumerate(section_results, start=1):
                review_entry = review_by_index.get(index)
                if not review_entry:
                    continue
                updated_analysis = _apply_full_page_review_to_analysis(entry["analysis"], review_entry)
                entry["analysis"] = updated_analysis
                ordered_results[index - 1]["analysis"] = updated_analysis

    global_site_grounding = ""
    if global_site_prompt:
        if config.verbose:
            print("Running global full-site YAML grounding...", file=sys.stderr)
        if output_dir:
            update_step_status(output_dir, "global_site_grounding", "in_progress")
        global_site_grounding = _run_global_site_capture(
            provider=provider,
            image_path=image_path,
            config=config,
            global_site_prompt=global_site_prompt,
            total=total,
            section_sequence=section_sequence,
            inventory_response=detection.inventory_response,
            sections=sections,
            full_page_review_raw=full_page_review_raw,
            output_dir=output_dir,
        )
        if out:
            (out / "global-site-grounding.yaml").write_text(global_site_grounding.rstrip() + "\n")
        if output_dir:
            update_step_status(output_dir, "global_site_grounding", "completed")

    if config.verbose:
        print("Merging section analyses into one grounding file...", file=sys.stderr)
    if output_dir:
        update_step_status(output_dir, "grounding_merge", "in_progress")

    use_normalized_yaml_merge = "normalized_site_ast" in merge_prompt
    section_groundings = "\n\n---\n\n".join(
        f"### Grounded Section {index}: {entry['label']}\n"
        f"- Bounds: y={entry['bounds']['y_start']} to y={entry['bounds']['y_end']}\n\n"
        f"{_compact_section_analysis_for_normalized_merge(entry['analysis']) if use_normalized_yaml_merge else entry['analysis']}"
        for index, entry in enumerate(section_results, start=1)
    )

    merge_user_prompt = (
        "Section inventory from the full-page pass:\n\n"
        f"{clean_markdown(detection.inventory_response)}\n\n"
        "Final detected sections:\n\n"
        f"{json.dumps(sections, indent=2)}\n\n"
        + (
            "Full-page review overrides:\n\n"
            f"{full_page_review_raw}\n\n"
            if full_page_review_raw
            else ""
        )
        + (
            "Global full-site YAML grounding:\n\n"
            f"{global_site_grounding}\n\n"
            if global_site_grounding
            else ""
        )
        + "Grounded section analyses:\n\n"
        f"{section_groundings}"
    )
    merge_token_limit = max(config.max_tokens, 12288)
    if use_normalized_yaml_merge:
        retry_instruction = (
            "The previous attempt was incomplete or too verbose. Return one complete, compact YAML document now. "
            "It must include `schema_version: normalized_site_ast.v1`, `type: normalized_site_ast`, every section in `sections`, "
            "`global_observations`, and `component_candidates`. Keep per-section `normalized_nodes` to the highest-signal "
            "layout/surface/component nodes so the document can finish within the token budget."
        )
    else:
        retry_instruction = (
            "The previous attempt was incomplete. Return the full structural analysis document, "
            "including every section, `## Cross-section Notes`, and `## Ambiguities`."
        )
    retry_prompt = f"{merge_user_prompt}\n\n{retry_instruction}"
    if config.provider == "openai":
        merge_attempts = [
            (merge_user_prompt, max(merge_token_limit, 32768)),
            (retry_prompt, max(merge_token_limit, 49152)),
            (retry_prompt, max(merge_token_limit, 65536)),
        ]
    else:
        merge_attempts = [
            (merge_user_prompt, max(merge_token_limit, 32768)),
            (retry_prompt, max(merge_token_limit, 49152)),
            (retry_prompt, max(merge_token_limit, 65536)),
        ]
    cleaned_merged = ""
    used_merge_fallback = False
    for attempt_index, (user_prompt, token_limit) in enumerate(merge_attempts, start=1):
        attempt_provider = provider
        if use_normalized_yaml_merge and config.provider == "openai" and config.reasoning_effort:
            attempt_config = AppConfig(**{**vars(config), "reasoning_effort": None})
            attempt_provider = get_provider(attempt_config)
        with token_usage_context(output_dir, "grounding_merge", {"attempt": attempt_index, "token_limit": token_limit}):
            merged = attempt_provider.text_query(
                system_prompt=merge_prompt,
                user_prompt=user_prompt,
                max_tokens=token_limit,
            )
        cleaned_merged = clean_markdown(merged)
        if _grounding_document_is_complete(cleaned_merged):
            break
        if config.verbose:
            print(
                f"Merged grounding file was incomplete on attempt {attempt_index}; retrying...",
                file=sys.stderr,
            )
    else:
        used_merge_fallback = True
        cleaned_merged = _build_fallback_grounding_document(
            inventory_response=detection.inventory_response,
            sections=sections,
            section_results=section_results,
        )
        if output_dir:
            update_step_status(output_dir, "grounding_merge", "fallback", {
                "reason": "model merge incomplete after retries",
            })

    if out:
        with open(out / "structural-analysis.md", "w") as f:
            f.write(cleaned_merged)
            f.write("\n")
    if output_dir:
        meta = {"fallback": True} if used_merge_fallback else None
        update_step_status(output_dir, "grounding_merge", "completed", meta)

    return cleaned_merged
