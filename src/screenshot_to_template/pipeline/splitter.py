"""Image section detection using configurable vision models + Pillow cropping."""

import json
import re
import sys
from dataclasses import dataclass

from PIL import Image, ImageDraw, ImageFont
from ..config import AppConfig
from ..models.base import LLMProvider
from ..models.anthropic import AnthropicProvider
from ..models.google import GoogleProvider
from ..models.openai import OpenAIProvider
from .single_shot import encode_pil_image


CROP_OVERLAP_PX = 0
RULER_GUTTER_WIDTH = 220
RULER_MAJOR_STEP = 100
RULER_MINOR_STEP = 50
@dataclass
class SectionDetectionResult:
    inventory_response: str
    raw_response: str
    parsed_sections: list[dict]
    window_debug: list[dict]
    final_sections: list[dict]


def detect_sections_with_llm(
    image_path: str,
    provider: LLMProvider,
    config: AppConfig,
) -> SectionDetectionResult:
    """Use the LLM to identify section boundaries in the screenshot.

    Returns the raw section detection stages we still care about.
    """
    img = Image.open(image_path)
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    original_w, original_h = img.size
    ruler_img = add_vertical_ruler(img, y_offset=0)

    if config.verbose:
        print(
            f"Detecting sections (image: {original_w}x{original_h}, "
            f"sent as: {ruler_img.size[0]}x{ruler_img.size[1]} with ruler)...",
            file=sys.stderr,
        )

    prompt = (
        "Analyze this full-page website screenshot and explain the visually distinct sections "
        "from top to bottom. Do not provide coordinates."
    )

    image_b64 = encode_pil_image(ruler_img, config.max_image_dimension)
    detector = _make_section_detector(config)

    inventory = _query_section_model(
        detector=detector,
        image_b64=image_b64,
        system_prompt=config.section_inventory_prompt,
        user_prompt=prompt,
    )

    window_debug: list[dict] = []
    auto_chunk_count = _auto_chunk_count_for_height(original_h, config)
    use_chunked = (
        (config.chunked_section_detection and original_h >= config.section_detection_chunk_trigger_height)
        or auto_chunk_count > 1
    )
    if use_chunked:
        parsed_sections, raw, window_debug = _detect_sections_with_chunked_windows(
            img=img,
            detector=detector,
            inventory=inventory,
            config=config,
            chunk_count=auto_chunk_count or None,
        )
        if len(parsed_sections) < 3:
            boundary_prompt = (
                f"The image is {original_w}x{original_h} pixels. "
                f"Report all Y-coordinates in these ORIGINAL dimensions ({original_w}x{original_h}). "
                "The image includes a numbered ruler gutter on the left. Each visible ruler label is an "
                "original page y-coordinate in pixels. Use those ruler numbers as your coordinate reference "
                "instead of estimating from the screenshot alone. "
                "Use the following section inventory as semantic grounding, then identify safe physical "
                "section boundaries for the screenshot.\n\n"
                "Section inventory:\n"
                f"{inventory}"
            )
            raw = _detect_with_model(
                detector=detector,
                image_b64=image_b64,
                system_prompt=config.section_detection_prompt,
                user_prompt=boundary_prompt,
            )
            parsed_sections = _parse_section_json(raw, original_h, 1.0)
            window_debug.append(
                {
                    "fallback": "full-page-raw",
                    "reason": "chunked-boundaries-insufficient",
                }
            )
    else:
        boundary_prompt = (
            f"The image is {original_w}x{original_h} pixels. "
            f"Report all Y-coordinates in these ORIGINAL dimensions ({original_w}x{original_h}). "
            "The image includes a numbered ruler gutter on the left. Each visible ruler label is an "
            "original page y-coordinate in pixels. Use those ruler numbers as your coordinate reference "
            "instead of estimating from the screenshot alone. "
            "Use the following section inventory as semantic grounding, then identify safe physical "
            "section boundaries for the screenshot.\n\n"
            "Section inventory:\n"
            f"{inventory}"
        )
        raw = _detect_with_model(
            detector=detector,
            image_b64=image_b64,
            system_prompt=config.section_detection_prompt,
            user_prompt=boundary_prompt,
        )
        parsed_sections = _parse_section_json(raw, original_h, 1.0)

    # Parse JSON from LLM response
    if config.verbose:
        print(
            f"Section inventory response (first 500 chars): {inventory[:500]}",
            file=sys.stderr,
        )
        print(f"Section detection raw response (first 500 chars): {raw[:500]}", file=sys.stderr)
    final_sections = [section.copy() for section in parsed_sections]

    if config.verbose:
        print(
            "Section detection mode: raw-only final output",
            file=sys.stderr,
        )
        for s in final_sections:
            print(
                f"  Section: {s['label']} ({s['y_start']}–{s['y_end']}px)",
                file=sys.stderr,
            )

    return SectionDetectionResult(
        inventory_response=inventory,
        raw_response=raw,
        parsed_sections=parsed_sections,
        window_debug=window_debug,
        final_sections=final_sections,
    )


def build_detection_windows(
    image_height: int,
    chunk_height: int,
    overlap: int,
) -> list[dict]:
    """Split a tall page into overlapping vertical windows for section-boundary detection."""
    if image_height <= 0:
        return []
    if chunk_height <= 0 or chunk_height >= image_height:
        return [{"index": 1, "y_start": 0, "y_end": image_height}]

    step = max(1, chunk_height - max(0, overlap))
    windows: list[dict] = []
    start = 0
    index = 1
    while True:
        end = min(image_height, start + chunk_height)
        windows.append({"index": index, "y_start": start, "y_end": end})
        if end >= image_height:
            break
        start = max(0, end - overlap)
        index += 1
    return windows


def build_even_detection_windows(
    image_height: int,
    chunk_count: int,
    overlap: int,
) -> list[dict]:
    """Split an image into a small number of overlapping near-equal windows."""
    if image_height <= 0:
        return []
    if chunk_count <= 1:
        return [{"index": 1, "y_start": 0, "y_end": image_height}]

    chunk_height = max(1, (image_height + chunk_count - 1) // chunk_count)
    windows: list[dict] = []
    for index in range(chunk_count):
        start = max(0, index * chunk_height - (overlap if index > 0 else 0))
        end = min(image_height, (index + 1) * chunk_height + (overlap if index < chunk_count - 1 else 0))
        if windows and start < windows[-1]["y_start"]:
            start = windows[-1]["y_start"]
        windows.append({"index": index + 1, "y_start": start, "y_end": end})

    windows[0]["y_start"] = 0
    windows[-1]["y_end"] = image_height
    return windows


def _auto_chunk_count_for_height(image_height: int, config: AppConfig) -> int:
    if not config.auto_chunk_tall_section_detection:
        return 1
    if image_height >= config.auto_three_chunk_threshold_height:
        return 3
    if image_height >= config.auto_two_chunk_threshold_height:
        return 2
    return 1


def _detect_sections_with_chunked_windows(
    img: Image.Image,
    detector: LLMProvider,
    inventory: str,
    config: AppConfig,
    chunk_count: int | None = None,
) -> tuple[list[dict], str, list[dict]]:
    image_w, image_h = img.size
    if chunk_count and chunk_count > 1:
        windows = build_even_detection_windows(
            image_height=image_h,
            chunk_count=chunk_count,
            overlap=config.auto_chunk_overlap,
        )
    else:
        windows = build_detection_windows(
            image_height=image_h,
            chunk_height=config.section_detection_chunk_height,
            overlap=config.section_detection_chunk_overlap,
        )
    if len(windows) <= 1:
        return _fallback_sections(image_h), "", []

    all_boundaries: list[dict] = []
    debug_rows: list[dict] = []
    raw_parts: list[str] = []

    for window in windows:
        crop = img.crop((0, window["y_start"], image_w, window["y_end"]))
        ruled = add_vertical_ruler(
            crop,
            y_offset=window["y_start"],
            major_step=config.chunk_ruler_major_step,
            minor_step=config.chunk_ruler_minor_step,
        )
        crop_b64 = encode_pil_image(ruled, config.max_image_dimension)
        local_inventory = inventory
        if config.use_local_inventory_per_chunk:
            inventory_system_prompt = config.section_window_inventory_prompt
            inventory_user_prompt = (
                f"This window spans original page y={window['y_start']} to y={window['y_end']} "
                f"within a full page that is {image_w}x{image_h} pixels.\n\n"
                "Describe only the sections visible inside this window."
            )
            local_inventory = _query_section_model(
                detector=detector,
                image_b64=crop_b64,
                system_prompt=inventory_system_prompt,
                user_prompt=inventory_user_prompt,
            )
        system_prompt = config.section_window_detection_prompt
        user_prompt = (
            f"This window spans original page y={window['y_start']} to y={window['y_end']} "
            f"within a full page that is {image_w}x{image_h} pixels.\n\n"
            "Section inventory for this window:\n"
            f"{local_inventory}"
        )
        raw = _query_section_model(
            detector=detector,
            image_b64=crop_b64,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
        boundaries = _parse_window_boundary_json(
            raw,
            window["y_start"],
            window["y_end"],
        )
        all_boundaries.extend(boundaries)
        debug_rows.append(
            {
                "window_index": window["index"],
                "window_start": window["y_start"],
                "window_end": window["y_end"],
                "coordinate_origin": "top",
                "inventory_response": local_inventory.strip(),
                "raw_response": raw.strip(),
                "boundaries": boundaries,
            }
        )
        raw_parts.append(
            "\n".join(
                [
                    f"## Window {window['index']} ({window['y_start']}–{window['y_end']})",
                    raw.strip(),
                ]
            )
        )

    merged_boundaries = _merge_window_boundary_candidates(
        all_boundaries,
        tolerance=config.chunk_boundary_cluster_tolerance,
        image_height=image_h,
    )
    merged_boundaries = _collapse_duplicate_transition_boundaries(merged_boundaries, image_h)
    sections = _sections_from_boundary_candidates(merged_boundaries, image_h)
    sections = _merge_adjacent_same_label_sections(sections, image_h)
    return sections, "\n\n".join(raw_parts), debug_rows


def add_vertical_ruler(
    img: Image.Image,
    y_offset: int = 0,
    gutter_width: int = RULER_GUTTER_WIDTH,
    major_step: int = RULER_MAJOR_STEP,
    minor_step: int = RULER_MINOR_STEP,
) -> Image.Image:
    """Render a left-side ruler gutter whose labels match original page Y coordinates."""
    if img.mode != "RGB":
        img = img.convert("RGB")

    canvas = Image.new("RGB", (img.size[0] + gutter_width, img.size[1]), (247, 246, 240))
    canvas.paste(img, (gutter_width, 0))

    draw = ImageDraw.Draw(canvas)
    font = _load_ruler_font()
    divider_x = gutter_width - 1
    draw.line((divider_x, 0, divider_x, img.size[1]), fill=(90, 90, 90), width=2)

    for y in range(0, img.size[1] + 1, minor_step):
        actual_y = y_offset + y
        is_major = (actual_y % major_step) == 0
        tick_start = gutter_width - (138 if is_major else 82)
        tick_color = (120, 120, 120) if is_major else (175, 175, 175)
        draw.line((tick_start, y, gutter_width, y), fill=tick_color, width=3 if is_major else 1)

        if not is_major:
            continue

        label = str(actual_y)
        if hasattr(draw, "textbbox"):
            left, top, right, bottom = draw.textbbox((0, 0), label, font=font)
            text_w = right - left
            text_h = bottom - top
        else:
            text_w, text_h = draw.textsize(label, font=font)

        text_x = max(10, tick_start - text_w - 12)
        text_y = max(0, min(y - (text_h // 2), img.size[1] - text_h))
        draw.text((text_x, text_y), label, fill=(18, 18, 18), font=font)

    return canvas


def _load_ruler_font(size: int = 22) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for font_name in ("DejaVuSans-Bold.ttf", "Arial Bold.ttf", "Arial.ttf"):
        try:
            return ImageFont.truetype(font_name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _make_section_detector(config: AppConfig) -> LLMProvider:
    provider_name = config.section_detection_provider
    model_name = config.section_detection_model
    if provider_name == "openai":
        detector = OpenAIProvider(
            model_name,
            reasoning_effort=getattr(config, "section_detection_reasoning_effort", None),
        )
        detector.image_detail = "original"
        return detector
    if provider_name == "anthropic":
        return AnthropicProvider(
            model_name,
            reasoning_effort=getattr(config, "section_detection_reasoning_effort", None),
        )
    if provider_name == "google":
        return GoogleProvider(model_name)
    raise ValueError(f"Unsupported section detection provider: {provider_name}")


def _query_section_model(
    detector: LLMProvider,
    image_b64: str,
    system_prompt: str,
    user_prompt: str,
) -> str:
    """Call the configured section-detection model once and return raw text."""
    max_tokens = 4096
    if isinstance(detector, OpenAIProvider) and getattr(detector, "reasoning_effort", None):
        max_tokens = 12288
    if isinstance(detector, AnthropicProvider) and getattr(detector, "reasoning_effort", None):
        max_tokens = 12288
    return detector.analyze_image(
        image_b64=image_b64,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        max_tokens=max_tokens,
        json_mode=False,
    )


def _detect_with_model(
    detector: LLMProvider,
    image_b64: str,
    system_prompt: str,
    user_prompt: str,
    max_retries: int = 3,
) -> str:
    """Call the configured section detector, retrying when JSON is malformed."""
    for attempt in range(max_retries):
        raw = _query_section_model(detector, image_b64, system_prompt, user_prompt)
        # Validate JSON before returning
        try:
            data = json.loads(raw)
            if "sections" in data and len(data["sections"]) >= 3:
                return raw
        except json.JSONDecodeError:
            # Check if we can extract enough sections from truncated JSON
            section_matches = re.findall(
                r'\{\s*"label"\s*:\s*"[^"]+"\s*,\s*"y_start"\s*:\s*\d+\s*,\s*"y_end"\s*:\s*\d+\s*\}',
                raw,
            )
            if len(section_matches) >= 5:
                return raw  # Parser will extract individual sections
        if attempt < max_retries - 1:
            print(f"  Section detection retry {attempt + 2}/{max_retries}...", file=sys.stderr)

    return raw  # Return last attempt, parser will handle fallback


def _parse_section_json(
    raw: str, original_height: int, scale: float
) -> list[dict]:
    """Extract section JSON from LLM response, scaling coordinates back to original size."""
    text = raw.strip()

    # Remove markdown code fences if present
    if "```" in text:
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            text = match.group(1)

    data = None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON object in the text
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
            except json.JSONDecodeError:
                pass

    # If full JSON parse failed, try to extract individual section objects
    # from truncated JSON (model sometimes cuts off mid-response)
    if data is None or "sections" not in data:
        section_pattern = re.findall(
            r'\{\s*"label"\s*:\s*"([^"]+)"\s*,\s*"y_start"\s*:\s*(\d+)\s*,\s*"y_end"\s*:\s*(\d+)\s*\}',
            text,
        )
        if len(section_pattern) >= 3:
            data = {
                "sections": [
                    {"label": m[0], "y_start": int(m[1]), "y_end": int(m[2])}
                    for m in section_pattern
                ]
            }
        else:
            return _fallback_sections(original_height)

    if "sections" not in data:
        return _fallback_sections(original_height)

    # Scale coordinates back to original image size
    sections = []
    for s in data["sections"]:
        y_start = int(s["y_start"] / scale)
        y_end = int(s["y_end"] / scale)
        # Clamp to image bounds
        y_start = max(0, min(y_start, original_height))
        y_end = max(0, min(y_end, original_height))
        if y_end > y_start:
            sections.append({
                "label": s.get("label", "Section"),
                "y_start": y_start,
                "y_end": y_end,
            })

    return sections if sections else _fallback_sections(original_height)


def _parse_window_boundary_json(
    raw: str,
    window_start: int,
    window_end: int,
) -> list[dict]:
    text = raw.strip()
    if "```" in text:
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            text = match.group(1)

    data = None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
            except json.JSONDecodeError:
                data = None

    if not data:
        return []

    boundaries = []
    for item in data.get("boundaries", []):
        try:
            y = int(item["y"])
        except (KeyError, TypeError, ValueError):
            continue
        y = max(window_start + 1, min(y, window_end - 1))
        between = str(item.get("between", "")).strip()
        upper_label, lower_label = _split_boundary_between_label(between)
        boundaries.append(
            {
                "y": y,
                "between": between or f"{upper_label} -> {lower_label}",
                "upper_label": upper_label,
                "lower_label": lower_label,
                "confidence": str(item.get("confidence", "")).strip().lower() or "medium",
                "window_start": window_start,
                "window_end": window_end,
            }
        )
    return boundaries


def _split_boundary_between_label(value: str) -> tuple[str, str]:
    text = value.strip()
    if not text:
        return "Section", "Section"
    parts = re.split(r"\s*(?:->|→)\s*", text, maxsplit=1)
    if len(parts) == 2:
        upper = parts[0].strip() or "Section"
        lower = parts[1].strip() or "Section"
        return upper, lower
    return text, "Section"


def _merge_window_boundary_candidates(
    boundaries: list[dict],
    tolerance: int,
    image_height: int,
) -> list[dict]:
    if not boundaries:
        return []

    ordered = sorted(boundaries, key=lambda item: item["y"])
    clusters: list[list[dict]] = []
    for boundary in ordered:
        if not clusters or not _should_merge_boundary_candidate(boundary, clusters[-1], tolerance):
            clusters.append([boundary])
        else:
            clusters[-1].append(boundary)

    merged: list[dict] = []
    for cluster in clusters:
        ys = sorted(item["y"] for item in cluster)
        merged_y = ys[len(ys) // 2]
        upper_label = _majority_label(cluster, "upper_label")
        lower_label = _majority_label(cluster, "lower_label")
        merged.append(
            {
                "y": max(1, min(merged_y, image_height - 1)),
                "upper_label": upper_label,
                "lower_label": lower_label,
                "between": f"{upper_label} -> {lower_label}",
                "votes": len(cluster),
                "windows": sorted({(item["window_start"], item["window_end"]) for item in cluster}),
            }
        )

    return merged


def _should_merge_boundary_candidate(
    candidate: dict,
    cluster: list[dict],
    tolerance: int,
) -> bool:
    if abs(candidate["y"] - cluster[-1]["y"]) > tolerance:
        return False
    upper = candidate.get("upper_label", "").strip().lower()
    lower = candidate.get("lower_label", "").strip().lower()
    for existing in cluster:
        existing_upper = str(existing.get("upper_label", "")).strip().lower()
        existing_lower = str(existing.get("lower_label", "")).strip().lower()
        if upper == existing_upper and lower == existing_lower:
            return True
    return False


def _majority_label(cluster: list[dict], key: str) -> str:
    counts: dict[str, int] = {}
    for item in cluster:
        label = (item.get(key) or "Section").strip() or "Section"
        counts[label] = counts.get(label, 0) + 1
    return max(counts.items(), key=lambda pair: (pair[1], -len(pair[0])))[0]


def _sections_from_boundary_candidates(boundaries: list[dict], image_height: int) -> list[dict]:
    if not boundaries:
        return _fallback_sections(image_height)

    sections: list[dict] = []
    previous_y = 0
    for index, boundary in enumerate(boundaries):
        boundary_y = max(previous_y + 1, min(boundary["y"], image_height - 1))
        previous_boundary = boundaries[index - 1] if index > 0 else None
        next_boundary = boundary
        sections.append(
            {
                "label": _section_label_from_neighbor_boundaries(previous_boundary, next_boundary),
                "y_start": previous_y,
                "y_end": boundary_y,
            }
        )
        previous_y = boundary_y

    last_boundary = boundaries[-1]
    sections.append(
        {
            "label": _clean_boundary_label(last_boundary.get("lower_label")) or "Section",
            "y_start": previous_y,
            "y_end": image_height,
        }
    )
    return _normalize_sections(sections, image_height)


def _collapse_duplicate_transition_boundaries(boundaries: list[dict], image_height: int) -> list[dict]:
    if not boundaries:
        return []

    collapsed: list[dict] = [boundaries[0].copy()]
    for boundary in boundaries[1:]:
        previous = collapsed[-1]
        same_transition = (
            _canonical_section_label(previous.get("upper_label")) == _canonical_section_label(boundary.get("upper_label"))
            and _canonical_section_label(previous.get("lower_label")) == _canonical_section_label(boundary.get("lower_label"))
        )
        if same_transition:
            overlap = _window_overlap_interval(previous.get("windows", []), boundary.get("windows", []))
            if overlap is None:
                collapsed.append(boundary.copy())
                continue

            previous_distance = _distance_to_interval(previous["y"], overlap)
            boundary_distance = _distance_to_interval(boundary["y"], overlap)
            chosen = previous if previous_distance <= boundary_distance else boundary

            if previous_distance == 0 and boundary_distance == 0:
                merged_y = (previous["y"] + boundary["y"]) // 2
            else:
                merged_y = chosen["y"]

            chosen["y"] = max(1, min(merged_y, image_height - 1))
            chosen["votes"] = int(previous.get("votes", 1)) + int(boundary.get("votes", 1))
            chosen_windows = {tuple(window) for window in previous.get("windows", [])}
            chosen_windows.update(tuple(window) for window in boundary.get("windows", []))
            chosen["windows"] = sorted(chosen_windows)
            if chosen is boundary:
                collapsed[-1] = boundary.copy()
            continue
        collapsed.append(boundary.copy())
    return collapsed


def _window_overlap_interval(
    previous_windows: list[tuple[int, int]] | list[list[int]],
    current_windows: list[tuple[int, int]] | list[list[int]],
) -> tuple[int, int] | None:
    best_overlap: tuple[int, int] | None = None
    for previous_window in previous_windows:
        previous_start, previous_end = int(previous_window[0]), int(previous_window[1])
        for current_window in current_windows:
            current_start, current_end = int(current_window[0]), int(current_window[1])
            overlap_start = max(previous_start, current_start)
            overlap_end = min(previous_end, current_end)
            if overlap_end <= overlap_start:
                continue
            if best_overlap is None or (overlap_end - overlap_start) > (best_overlap[1] - best_overlap[0]):
                best_overlap = (overlap_start, overlap_end)
    return best_overlap


def _distance_to_interval(y: int, interval: tuple[int, int]) -> int:
    start, end = interval
    if y < start:
        return start - y
    if y > end:
        return y - end
    return 0


def _section_label_from_neighbor_boundaries(
    previous_boundary: dict | None,
    next_boundary: dict | None,
) -> str:
    if previous_boundary is None and next_boundary is None:
        return "Section"
    if previous_boundary is None:
        return _clean_boundary_label(next_boundary.get("upper_label")) or "Section"
    if next_boundary is None:
        return _clean_boundary_label(previous_boundary.get("lower_label")) or "Section"

    previous_lower = _clean_boundary_label(previous_boundary.get("lower_label"))
    next_upper = _clean_boundary_label(next_boundary.get("upper_label"))
    if not previous_lower:
        return next_upper or "Section"
    if not next_upper:
        return previous_lower
    if _canonical_section_label(previous_lower) == _canonical_section_label(next_upper):
        return previous_lower if len(previous_lower) >= len(next_upper) else next_upper
    return next_upper


def _clean_boundary_label(value: str | None) -> str:
    return (value or "").strip()


def _canonical_section_label(value: str | None) -> str:
    text = _clean_boundary_label(value).lower()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _merge_adjacent_same_label_sections(sections: list[dict], image_height: int) -> list[dict]:
    if len(sections) <= 1:
        return sections

    merged: list[dict] = [sections[0].copy()]
    for section in sections[1:]:
        previous = merged[-1]
        if _canonical_section_label(previous["label"]) == _canonical_section_label(section["label"]):
            previous["y_end"] = section["y_end"]
            continue
        merged.append(section.copy())
    return _normalize_sections(merged, image_height)


def _fallback_sections(height: int) -> list[dict]:
    """Fallback: split into roughly equal thirds."""
    third = height // 3
    return [
        {"label": "Top", "y_start": 0, "y_end": third},
        {"label": "Middle", "y_start": third, "y_end": third * 2},
        {"label": "Bottom", "y_start": third * 2, "y_end": height},
    ]


def _normalize_sections(sections: list[dict], image_height: int) -> list[dict]:
    """Sort, clamp, and force contiguous coverage from top to bottom."""
    cleaned = []
    for section in sections:
        label = (section.get("label") or "Section").strip() or "Section"
        y_start = max(0, min(int(section["y_start"]), image_height))
        y_end = max(0, min(int(section["y_end"]), image_height))
        if y_end > y_start:
            cleaned.append({"label": label, "y_start": y_start, "y_end": y_end})

    if not cleaned:
        return _fallback_sections(image_height)

    cleaned.sort(key=lambda s: (s["y_start"], s["y_end"]))

    normalized = [cleaned[0].copy()]
    for section in cleaned[1:]:
        prev = normalized[-1]
        if section["y_start"] <= prev["y_start"]:
            section["y_start"] = prev["y_start"] + 1
        if section["y_end"] <= section["y_start"]:
            continue
        normalized.append(section.copy())

    normalized[0]["y_start"] = 0
    normalized[-1]["y_end"] = image_height

    for index in range(len(normalized) - 1):
        current = normalized[index]
        next_section = normalized[index + 1]
        boundary = max(current["y_start"] + 1, min(current["y_end"], next_section["y_start"]))
        current["y_end"] = boundary
        next_section["y_start"] = boundary

    return [s for s in normalized if s["y_end"] > s["y_start"]]

def compute_crop_bounds(
    sections: list[dict], image_height: int, overlap_px: int = CROP_OVERLAP_PX
) -> list[dict]:
    """Return section-aligned crop bounds, optionally expanded by overlap."""
    bounds = []
    total = len(sections)

    for index, section in enumerate(sections):
        top_overlap = 0 if index == 0 else overlap_px
        bottom_overlap = 0 if index == total - 1 else overlap_px
        crop_y_start = max(0, section["y_start"] - top_overlap)
        crop_y_end = min(image_height, section["y_end"] + bottom_overlap)
        bounds.append(
            {
                "label": section["label"],
                "y_start": section["y_start"],
                "y_end": section["y_end"],
                "crop_y_start": crop_y_start,
                "crop_y_end": crop_y_end,
            }
        )

    return bounds


def crop_sections(
    image_path: str,
    sections: list[dict],
    overlap_px: int = CROP_OVERLAP_PX,
) -> list[tuple[Image.Image, str]]:
    """Crop the image into section-aligned slices. Returns list of (cropped_image, label)."""
    img = Image.open(image_path)
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    w, h = img.size
    crops = []
    crop_bounds = compute_crop_bounds(sections, h, overlap_px=overlap_px)
    for section, bounds in zip(sections, crop_bounds):
        cropped = img.crop((0, bounds["crop_y_start"], w, bounds["crop_y_end"]))
        crops.append((cropped, section["label"]))

    return crops
