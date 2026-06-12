"""Sectioned pipeline: split screenshot into sections, analyze each, merge."""

import base64
import json
import re
import sys
from io import BytesIO
from pathlib import Path

from PIL import Image

from ..config import AppConfig
from ..models import get_provider
from ..output import generate_section_map, save_ruler_gutter_preview
from .single_shot import load_and_encode_image
from .splitter import (
    add_vertical_ruler,
    build_even_detection_windows,
    build_detection_windows,
    compute_crop_bounds,
    crop_sections,
    detect_sections_with_llm,
)


def _safe_label_slug(label: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")
    return slug or "section"


def encode_pil_image(img: Image.Image, max_dimension: int = 2048) -> str:
    """Encode a PIL Image to base64 PNG, resizing if needed."""
    w, h = img.size
    if w > max_dimension or h > max_dimension:
        ratio = min(max_dimension / w, max_dimension / h)
        img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def run(image_path: str, config: AppConfig, output_dir: str | None = None) -> str:
    """Run staged analysis: structural pass, per-section evidence, then synthesis."""
    provider = get_provider(config)

    if config.verbose:
        print(f"Using {config.provider}/{config.model}", file=sys.stderr)

    # Load full image early (reused in step 1 and step 3)
    full_image_b64 = load_and_encode_image(image_path, config.max_image_dimension)

    # Step 1: Ground the run with a structural analysis of the full page.
    if config.verbose:
        print("Running structural analysis...", file=sys.stderr)

    structural_analysis = provider.analyze_image(
        image_b64=full_image_b64,
        system_prompt=config.structural_analysis_prompt,
        user_prompt=(
            "Analyze this website screenshot and produce the structural analysis only. "
            "Do not produce the final design system."
        ),
        max_tokens=config.max_tokens,
    )

    if output_dir:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        with open(out / "structural-analysis.md", "w") as f:
            f.write(structural_analysis.rstrip())
            f.write("\n")

    # Step 2: Detect sections, crop, and analyze each with an evidence-focused prompt.
    detection = detect_sections_with_llm(image_path, provider, config)
    sections = detection.final_sections

    if config.verbose:
        print(f"Detected {len(sections)} sections", file=sys.stderr)

    crops = crop_sections(image_path, sections)
    total = len(crops)

    # Save section data and crop images if output_dir is provided
    if output_dir:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        crop_bounds = compute_crop_bounds(sections, Image.open(image_path).size[1])
        source_img = Image.open(image_path).convert("RGB")
        with open(out / "section-inventory.md", "w") as f:
            f.write(detection.inventory_response.rstrip())
            f.write("\n")
        with open(out / "section-detection-raw.txt", "w") as f:
            f.write(detection.raw_response.rstrip())
            f.write("\n")
        with open(out / "raw-sections.json", "w") as f:
            json.dump(detection.parsed_sections, f, indent=2)
        with open(out / "window-detection-debug.json", "w") as f:
            json.dump(detection.window_debug, f, indent=2)
        with open(out / "sections.json", "w") as f:
            json.dump(sections, f, indent=2)
        with open(out / "crop-bounds.json", "w") as f:
            json.dump(crop_bounds, f, indent=2)
        full_page_ruled = add_vertical_ruler(source_img)
        full_page_ruled.save(out / "section-ruler.png")
        llm_inputs_dir = out / "llm-inputs"
        llm_inputs_dir.mkdir(exist_ok=True)
        llm_input_records = [
            {
                "name": "01-full-page-inventory.png",
                "purpose": ["full-page inventory"],
                "window_start": 0,
                "window_end": source_img.size[1],
            }
        ]
        full_page_ruled.save(llm_inputs_dir / "01-full-page-inventory.png")
        window_dir = out / "windows"
        window_dir.mkdir(exist_ok=True)
        auto_chunk_count = 1
        if config.auto_chunk_tall_section_detection:
            if source_img.size[1] >= config.auto_three_chunk_threshold_height:
                auto_chunk_count = 3
            elif source_img.size[1] >= config.auto_two_chunk_threshold_height:
                auto_chunk_count = 2
        if auto_chunk_count > 1:
            windows = build_even_detection_windows(
                image_height=source_img.size[1],
                chunk_count=auto_chunk_count,
                overlap=config.auto_chunk_overlap,
            )
        else:
            windows = build_detection_windows(
                image_height=source_img.size[1],
                chunk_height=config.section_detection_chunk_height,
                overlap=config.section_detection_chunk_overlap,
            )
        for window in windows:
            crop = source_img.crop((0, window["y_start"], source_img.size[0], window["y_end"]))
            ruled = add_vertical_ruler(
                crop,
                y_offset=window["y_start"],
                major_step=config.chunk_ruler_major_step,
                minor_step=config.chunk_ruler_minor_step,
            )
            window_path = window_dir / f"{window['index']:02d}-{window['y_start']}-{window['y_end']}-ruler.png"
            ruled.save(window_path)
            save_ruler_gutter_preview(
                window_path,
                window_dir / f"{window['index']:02d}-{window['y_start']}-{window['y_end']}-gutter-preview.png",
            )
            input_name = (
                f"{window['index'] + 1:02d}-window-{window['index']}-"
                f"{window['y_start']}-{window['y_end']}-input.png"
            )
            input_path = llm_inputs_dir / input_name
            ruled.save(input_path)
            save_ruler_gutter_preview(
                input_path,
                llm_inputs_dir / input_name.replace("-input.png", "-gutter-preview.png"),
            )
            llm_input_records.append(
                {
                    "name": input_name,
                    "purpose": (
                        ["window inventory", "window boundary"]
                        if config.use_local_inventory_per_chunk
                        else ["window boundary"]
                    ),
                    "window_index": window["index"],
                    "window_start": window["y_start"],
                    "window_end": window["y_end"],
                }
            )
        with open(out / "llm-inputs.json", "w") as f:
            json.dump(llm_input_records, f, indent=2)
        crops_dir = out / "crops"
        crops_dir.mkdir(exist_ok=True)
        for i, (img_crop, label) in enumerate(crops):
            safe_label = _safe_label_slug(label)
            img_crop.save(crops_dir / f"{i + 1:02d}-{safe_label}.png")
        generate_section_map(
            screenshot_path=image_path,
            output_path=out / "section-map-raw.html",
            sections=detection.parsed_sections,
        )
        generate_section_map(
            screenshot_path=image_path,
            output_path=out / "section-map.html",
            sections=sections,
            crop_bounds=crop_bounds,
        )

    section_results = []

    for i, (img_crop, label) in enumerate(crops):
        if config.verbose:
            print(
                f"Analyzing section {i + 1}/{total}: {label}...", file=sys.stderr
            )

        b64 = encode_pil_image(img_crop, config.max_image_dimension)

        prompt = config.section_analysis_prompt.format(
            section_num=i + 1,
            total_sections=total,
            section_label=label,
        )

        result = provider.analyze_image(
            image_b64=b64,
            system_prompt=prompt,
            user_prompt=(
                "Analyze this cropped website section and produce the section evidence only. "
                "Do not produce the final design system."
            ),
            max_tokens=config.max_tokens,
        )
        section_results.append((label, result))

    # Step 3: Synthesize the final design system from the structural pass, crops, and full page.
    if config.verbose:
        print("Synthesizing final design system...", file=sys.stderr)

    merge_input = "\n\n---\n\n".join(
        f"### Section {i + 1}: {label}\n\n{text}"
        for i, (label, text) in enumerate(section_results)
    )

    merge_prompt = config.merge_prompt.format(
        structural_analysis=structural_analysis,
        sections=merge_input,
    )

    # Combine synthesis instructions with the final output format prompt.
    combined_system_prompt = (
        f"{merge_prompt}\n\n"
        f"---\n\n"
        f"Use the following prompt as your guide for the final output structure and level of detail:\n\n"
        f"{config.system_prompt}"
    )

    merged = provider.analyze_image(
        image_b64=full_image_b64,
        system_prompt=combined_system_prompt,
        user_prompt=(
            "Here is the full website screenshot again for verification. "
            "Synthesize one definitive design system grounded in the structural analysis and section evidence."
        ),
        max_tokens=config.max_tokens,
    )

    return merged
