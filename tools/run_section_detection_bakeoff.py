#!/usr/bin/env python3
"""Run the current section detector against multiple models and save comparison artifacts."""

import argparse
import json
import os
import re
from pathlib import Path

from PIL import Image

from screenshot_to_template.config import AppConfig
from screenshot_to_template.output import generate_section_map, save_ruler_gutter_preview
from screenshot_to_template.pipeline.splitter import (
    add_vertical_ruler,
    build_even_detection_windows,
    build_detection_windows,
    compute_crop_bounds,
    detect_sections_with_llm,
)
from screenshot_to_template.run_versions import allocate_section_separator_version, slugify


DEFAULT_MODELS = [
    ("openai", "gpt-5.5"),
    ("openai", "gpt-5"),
    ("openai", "gpt-4.1"),
    ("openai", "gpt-4o"),
    ("anthropic", "claude-sonnet-4-20250514"),
    ("google", "gemini-2.5-pro"),
    ("google", "gemini-2.5-flash"),
]


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def provider_available(provider: str) -> bool:
    if provider == "openai":
        return bool(os.environ.get("OPENAI_API_KEY"))
    if provider == "anthropic":
        return bool(os.environ.get("ANTHROPIC_API_KEY"))
    if provider == "google":
        return bool(os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY"))
    return False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("screenshot", help="Path to the screenshot image")
    parser.add_argument(
        "output_dir",
        nargs="?",
        default=None,
        help="Directory to write bakeoff artifacts into. If omitted, a new vNNN run folder is allocated.",
    )
    parser.add_argument(
        "--model",
        action="append",
        default=[],
        help="Model override in provider:model format, e.g. openai:gpt-5",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print progress to stderr via detector verbose mode",
    )
    parser.add_argument(
        "--title",
        default=None,
        help="Optional title to use when auto-allocating a vNNN bakeoff folder",
    )
    return parser.parse_args()


def parse_models(args: argparse.Namespace) -> list[tuple[str, str]]:
    if not args.model:
        return DEFAULT_MODELS

    parsed = []
    for entry in args.model:
        if ":" not in entry:
            raise SystemExit(f"Invalid --model value: {entry}. Use provider:model")
        provider, model = entry.split(":", 1)
        parsed.append((provider, model))
    return parsed


def main() -> None:
    args = parse_args()
    screenshot = Path(args.screenshot)
    if args.output_dir:
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        version_dir = None
    else:
        title = args.title or f"{screenshot.stem} section-detection bakeoff"
        version_dir = allocate_section_separator_version(
            title=title,
            slug=slugify(title),
            summary="Section-detection bakeoff run. Compare model outputs inside artifacts/.",
            screenshot=str(screenshot),
        )
        output_dir = version_dir / "artifacts"

    models = parse_models(args)
    image_height = Image.open(screenshot).size[1]
    summary = []

    for provider, model in models:
        label = f"{provider}-{slugify(model)}"
        model_dir = output_dir / label
        model_dir.mkdir(parents=True, exist_ok=True)

        row = {"provider": provider, "model": model}
        if not provider_available(provider):
            row["ok"] = False
            row["error"] = f"Missing API key for {provider}"
            summary.append(row)
            continue

        config = AppConfig(
            provider="openai",
            model="gpt-5.5",
            section_detection_provider=provider,
            section_detection_model=model,
            verbose=args.verbose,
        )

        try:
            detection = detect_sections_with_llm(str(screenshot), None, config)
            sections = detection.final_sections
            crop_bounds = compute_crop_bounds(sections, image_height)

            (model_dir / "section-inventory.md").write_text(detection.inventory_response + "\n")
            (model_dir / "raw.txt").write_text(detection.raw_response + "\n")
            (model_dir / "raw-sections.json").write_text(
                json.dumps(detection.parsed_sections, indent=2) + "\n"
            )
            (model_dir / "window-detection-debug.json").write_text(
                json.dumps(detection.window_debug, indent=2) + "\n"
            )
            (model_dir / "sections.json").write_text(json.dumps(sections, indent=2) + "\n")
            (model_dir / "crop-bounds.json").write_text(json.dumps(crop_bounds, indent=2) + "\n")
            source_img = Image.open(screenshot).convert("RGB")
            add_vertical_ruler(source_img).save(model_dir / "section-ruler.png")
            llm_inputs_dir = model_dir / "llm-inputs"
            llm_inputs_dir.mkdir(exist_ok=True)
            full_input_path = llm_inputs_dir / "01-full-page-inventory.png"
            add_vertical_ruler(source_img).save(full_input_path)
            save_ruler_gutter_preview(
                full_input_path,
                llm_inputs_dir / "01-full-page-inventory-gutter-preview.png",
            )
            llm_input_records = [
                {
                    "name": "01-full-page-inventory.png",
                    "purpose": ["full-page inventory"],
                    "window_start": 0,
                    "window_end": source_img.size[1],
                }
            ]
            windows_dir = model_dir / "windows"
            windows_dir.mkdir(exist_ok=True)
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
                window_path = windows_dir / f"{window['index']:02d}-{window['y_start']}-{window['y_end']}-ruler.png"
                ruled.save(window_path)
                save_ruler_gutter_preview(
                    window_path,
                    windows_dir / f"{window['index']:02d}-{window['y_start']}-{window['y_end']}-gutter-preview.png",
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
            (model_dir / "llm-inputs.json").write_text(json.dumps(llm_input_records, indent=2) + "\n")
            generate_section_map(
                screenshot_path=screenshot,
                output_path=model_dir / "section-map-raw.html",
                sections=detection.parsed_sections,
            )
            generate_section_map(
                screenshot_path=screenshot,
                output_path=model_dir / "section-map.html",
                sections=sections,
            )
            row["ok"] = True
            row["sections"] = sections
        except Exception as exc:  # noqa: BLE001
            row["ok"] = False
            row["error"] = str(exc)

        summary.append(row)

    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    if version_dir is not None:
        print(version_dir)


if __name__ == "__main__":
    main()
