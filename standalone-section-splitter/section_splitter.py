#!/usr/bin/env python3
"""Standalone website screenshot section splitter.

This script is intentionally self-contained so it can be copied into another
repo without depending on the rest of this project.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


SECTION_INVENTORY_PROMPT = """\
You are analyzing a website screenshot and describing the visible sections from top to bottom.

Rules:
- Focus on visual section structure, not business content.
- Base conclusions on visible evidence only.
- Describe only the sections visible in the image you receive.
- Do not provide coordinates.
- Keep the list top-to-bottom and concise.
"""

SECTION_DETECTION_PROMPT = """\
You are analyzing a website screenshot to split it into full-width sections.

The image includes a ruler gutter on the left.
Each ruler label is the ORIGINAL page y-coordinate in pixels for that row.
Use those ruler numbers as your coordinate source of truth.

Rules:
- Base conclusions on visible evidence only.
- Never place a cut through visible content.
- Visible content includes headings, body text, buttons, cards, logos, images, illustrations, forms, dividers, and attached decorative graphics.
- A strong full-width background or surface change is a high-confidence section boundary signal.
- Large whitespace between the last content of one section and the first content of the next section is a strong section boundary signal.
- Hero graphics and decorative illustrations belong to the hero until they visibly end.
- Standalone logo strips, promo banners, and CTA bands count as real sections if they have their own visual block.
- Keep each section as one logical block.
- The first visible section in the image starts at the top of the image you were given.
- The last visible section in the image ends at the bottom of the image you were given.

Return only valid JSON in this exact format:
{
  "image_height": <total image height in pixels>,
  "sections": [
    {"label": "Navigation", "y_start": 0, "y_end": 80},
    {"label": "Hero", "y_start": 80, "y_end": 600}
  ]
}
"""

RULER_GUTTER_WIDTH = 220
RULER_MAJOR_STEP = 100
RULER_MINOR_STEP = 50


def load_shared_openai_api_key() -> str | None:
    existing = os.environ.get("OPENAI_API_KEY")
    if existing:
        return existing

    env_file = Path(__file__).resolve().parents[1] / ".env.local"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if "=" not in line or line.startswith("#"):
                continue
            key, _, value = line.partition("=")
            if key.strip() == "OPENAI_API_KEY" and value.strip():
                os.environ["OPENAI_API_KEY"] = value.strip()
                return os.environ["OPENAI_API_KEY"]
    return None


class VisionProvider(ABC):
    def __init__(self, model: str):
        self.model = model

    @abstractmethod
    def analyze_image(
        self,
        image_b64: str,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096,
    ) -> str:
        raise NotImplementedError


class OpenAIProvider(VisionProvider):
    def __init__(self, model: str = "gpt-5.5"):
        super().__init__(model)
        from openai import OpenAI

        api_key = load_shared_openai_api_key()
        if not api_key:
            raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY environment variable.")
        self.client = OpenAI(api_key=api_key)
        self.image_detail = "original"

    def analyze_image(
        self,
        image_b64: str,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096,
    ) -> str:
        content = [
            {"type": "text", "text": user_prompt},
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{image_b64}",
                    "detail": self.image_detail,
                },
            },
        ]
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content},
            ],
            max_completion_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""


class AnthropicProvider(VisionProvider):
    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        super().__init__(model)
        import anthropic

        self.client = anthropic.Anthropic(timeout=300.0, max_retries=2)

    def analyze_image(
        self,
        image_b64: str,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096,
    ) -> str:
        result = ""
        with self.client.messages.stream(
            model=self.model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": image_b64,
                            },
                        },
                    ],
                }
            ],
        ) as stream:
            for text in stream.text_stream:
                result += text
        return result


class GoogleProvider(VisionProvider):
    def __init__(self, model: str = "gemini-2.5-pro"):
        super().__init__(model)
        from google import genai
        from google.genai import types

        api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("Set GOOGLE_API_KEY or GEMINI_API_KEY.")
        self.genai = genai
        self.types = types
        self.client = genai.Client(api_key=api_key)

    def analyze_image(
        self,
        image_b64: str,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096,
    ) -> str:
        image_bytes = base64.b64decode(image_b64)
        response = self.client.models.generate_content(
            model=self.model,
            contents=[
                self.types.Content(
                    parts=[
                        self.types.Part.from_text(text=user_prompt),
                        self.types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
                    ]
                )
            ],
            config=self.types.GenerateContentConfig(
                system_instruction=system_prompt,
                max_output_tokens=max_tokens,
            ),
        )
        return response.text or ""


@dataclass
class SplitterConfig:
    provider: str = "openai"
    model: str = "gpt-5.5"
    max_tokens: int = 4096
    tall_page_threshold: int = 22000
    tall_page_chunk_count: int = 2
    tall_page_overlap: int = 4800
    save_inputs: bool = True
    save_crops: bool = True
    verbose: bool = False


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "section"


def canonical_label(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def make_provider(config: SplitterConfig) -> VisionProvider:
    if config.provider == "openai":
        return OpenAIProvider(config.model)
    if config.provider == "anthropic":
        return AnthropicProvider(config.model)
    if config.provider == "google":
        return GoogleProvider(config.model)
    raise ValueError(f"Unsupported provider: {config.provider}")


def encode_image(img: Image.Image) -> str:
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def load_image(path: str | Path) -> Image.Image:
    img = Image.open(path)
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    return img


def add_vertical_ruler(
    img: Image.Image,
    y_offset: int = 0,
    gutter_width: int = RULER_GUTTER_WIDTH,
    major_step: int = RULER_MAJOR_STEP,
    minor_step: int = RULER_MINOR_STEP,
) -> Image.Image:
    if img.mode != "RGB":
        img = img.convert("RGB")

    canvas = Image.new("RGB", (img.size[0] + gutter_width, img.size[1]), (247, 246, 240))
    canvas.paste(img, (gutter_width, 0))

    draw = ImageDraw.Draw(canvas)
    font = load_ruler_font()
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


def load_ruler_font(size: int = 22) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for font_name in ("DejaVuSans-Bold.ttf", "Arial Bold.ttf", "Arial.ttf"):
        try:
            return ImageFont.truetype(font_name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def save_gutter_preview(source_path: str | Path, output_path: str | Path) -> None:
    img = Image.open(source_path).convert("RGB")
    gutter = img.crop((0, 0, min(RULER_GUTTER_WIDTH, img.size[0]), img.size[1]))
    widened = gutter.resize((gutter.size[0] * 4, gutter.size[1]), Image.Resampling.LANCZOS)
    widened.save(output_path)


def build_even_detection_windows(image_height: int, chunk_count: int, overlap: int) -> list[dict]:
    if image_height <= 0:
        return []
    if chunk_count <= 1:
        return [{"index": 1, "y_start": 0, "y_end": image_height}]

    chunk_height = max(1, (image_height + chunk_count - 1) // chunk_count)
    windows: list[dict] = []
    for index in range(chunk_count):
        start = max(0, index * chunk_height - (overlap if index > 0 else 0))
        end = min(image_height, (index + 1) * chunk_height + (overlap if index < chunk_count - 1 else 0))
        windows.append({"index": index + 1, "y_start": start, "y_end": end})

    windows[0]["y_start"] = 0
    windows[-1]["y_end"] = image_height
    return windows


def query_sections(
    provider: VisionProvider,
    img: Image.Image,
    y_offset: int,
    config: SplitterConfig,
) -> tuple[str, str, list[dict], Image.Image]:
    ruled = add_vertical_ruler(img, y_offset=y_offset)
    image_b64 = encode_image(ruled)

    inventory = provider.analyze_image(
        image_b64=image_b64,
        system_prompt=SECTION_INVENTORY_PROMPT,
        user_prompt="Describe the visible sections from top to bottom. Do not provide coordinates.",
        max_tokens=config.max_tokens,
    )

    boundary_prompt = (
        f"This image spans original page y={y_offset} to y={y_offset + img.size[1]}.\n"
        "The left gutter is a ruler labeled in ORIGINAL page y-coordinates.\n"
        "Use the following section inventory as semantic grounding, then return section cuts in ORIGINAL page coordinates.\n\n"
        f"Section inventory:\n{inventory}"
    )
    raw = provider.analyze_image(
        image_b64=image_b64,
        system_prompt=SECTION_DETECTION_PROMPT,
        user_prompt=boundary_prompt,
        max_tokens=config.max_tokens,
    )
    sections = parse_section_json(raw, y_offset, y_offset + img.size[1])
    return inventory, raw, sections, ruled


def parse_section_json(raw: str, min_y: int, max_y: int) -> list[dict]:
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

    if not data or "sections" not in data:
        section_pattern = re.findall(
            r'\{\s*"label"\s*:\s*"([^"]+)"\s*,\s*"y_start"\s*:\s*(\d+)\s*,\s*"y_end"\s*:\s*(\d+)\s*\}',
            text,
        )
        if len(section_pattern) >= 2:
            data = {
                "sections": [
                    {"label": m[0], "y_start": int(m[1]), "y_end": int(m[2])}
                    for m in section_pattern
                ]
            }
        else:
            return [
                {"label": "Top", "y_start": min_y, "y_end": min_y + ((max_y - min_y) // 2)},
                {"label": "Bottom", "y_start": min_y + ((max_y - min_y) // 2), "y_end": max_y},
            ]

    sections = []
    for section in data["sections"]:
        y_start = max(min_y, min(int(section["y_start"]), max_y))
        y_end = max(min_y, min(int(section["y_end"]), max_y))
        if y_end > y_start:
            sections.append(
                {
                    "label": str(section.get("label", "Section")).strip() or "Section",
                    "y_start": y_start,
                    "y_end": y_end,
                }
            )

    return normalize_sections(sections, min_y=min_y, max_y=max_y)


def normalize_sections(sections: list[dict], min_y: int, max_y: int) -> list[dict]:
    if not sections:
        return []

    cleaned = []
    for section in sections:
        y_start = max(min_y, min(int(section["y_start"]), max_y))
        y_end = max(min_y, min(int(section["y_end"]), max_y))
        if y_end > y_start:
            cleaned.append(
                {
                    "label": (section.get("label") or "Section").strip() or "Section",
                    "y_start": y_start,
                    "y_end": y_end,
                }
            )
    if not cleaned:
        return []

    cleaned.sort(key=lambda item: (item["y_start"], item["y_end"]))
    cleaned[0]["y_start"] = min_y
    cleaned[-1]["y_end"] = max_y

    normalized = [cleaned[0].copy()]
    for section in cleaned[1:]:
        previous = normalized[-1]
        boundary = max(previous["y_start"] + 1, min(previous["y_end"], section["y_start"]))
        previous["y_end"] = boundary
        current = section.copy()
        current["y_start"] = boundary
        if current["y_end"] > current["y_start"]:
            normalized.append(current)
    normalized[-1]["y_end"] = max_y
    return normalized


def reconcile_window_sections(
    sections_by_window: list[dict],
    screenshot_height: int,
) -> tuple[list[dict], list[dict], dict]:
    overlap_start = max(item["window"]["y_start"] for item in sections_by_window)
    overlap_end = min(item["window"]["y_end"] for item in sections_by_window)

    candidates: list[dict] = []
    for window_result in sections_by_window:
        window = window_result["window"]
        for index, section in enumerate(window_result["sections"], start=1):
            candidates.append(
                {
                    "source_window": f"window-{window['index']}",
                    "source_window_start": window["y_start"],
                    "source_window_end": window["y_end"],
                    "label": section["label"],
                    "canonical_label": canonical_label(section["label"]),
                    "local_index": index,
                    "y_start": section["y_start"],
                    "y_end": section["y_end"],
                    "height": section["y_end"] - section["y_start"],
                    "status": "candidate",
                    "reasons": [],
                }
            )

    for candidate in candidates:
        intersects_overlap = candidate["y_start"] < overlap_end and candidate["y_end"] > overlap_start
        if not intersects_overlap:
            continue
        if (
            candidate["y_end"] == candidate["source_window_end"]
            and candidate["source_window_end"] == overlap_end
        ):
            candidate["status"] = "removed"
            candidate["reasons"].append("truncated-at-bottom-window-edge-in-overlap")
        elif (
            candidate["y_start"] == candidate["source_window_start"]
            and candidate["source_window_start"] == overlap_start
        ):
            candidate["status"] = "removed"
            candidate["reasons"].append("truncated-at-top-window-edge-in-overlap")

    active = [candidate for candidate in candidates if candidate["status"] == "candidate"]
    for index, current in enumerate(active):
        if current["status"] != "candidate":
            continue
        for other in active[index + 1:]:
            if other["status"] != "candidate":
                continue
            if current["canonical_label"] != other["canonical_label"]:
                continue
            overlap = min(current["y_end"], other["y_end"]) - max(current["y_start"], other["y_start"])
            if overlap <= 0:
                continue
            loser, winner = (current, other) if current["height"] < other["height"] else (other, current)
            loser["status"] = "removed"
            loser["reasons"].append(f"duplicate-of-{winner['source_window']}:{winner['label']}")

    kept = [candidate for candidate in candidates if candidate["status"] == "candidate"]
    removed = [candidate for candidate in candidates if candidate["status"] == "removed"]
    kept.sort(key=lambda item: item["y_start"])
    removed.sort(key=lambda item: (item["source_window"], item["y_start"]))

    summary = {
        "screenshot_height": screenshot_height,
        "overlap_start": overlap_start,
        "overlap_end": overlap_end,
        "candidate_count": len(candidates),
        "kept_count": len(kept),
        "removed_count": len(removed),
    }
    return kept, removed, summary


def image_to_data_uri(path: str | Path) -> str:
    path = Path(path)
    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    with open(path, "rb") as handle:
        payload = base64.b64encode(handle.read()).decode("utf-8")
    return f"data:{mime};base64,{payload}"


def generate_section_map(screenshot_path: str | Path, output_path: str | Path, sections: list[dict]) -> None:
    if not sections:
        return

    screenshot_path = Path(screenshot_path)
    output_path = Path(output_path)
    img = Image.open(screenshot_path)
    img_w, img_h = img.size
    screenshot_uri = image_to_data_uri(screenshot_path)

    lines = []
    labels = []
    for section in sections:
        y_start = section["y_start"]
        y_end = section["y_end"]
        label = section["label"]
        lines.append(
            f'<div style="position:absolute;top:{y_start}px;left:0;right:0;height:2px;background:#ff3b30;z-index:3;"></div>'
        )
        labels.append(
            f'<div style="position:absolute;top:{y_start + 4}px;left:8px;z-index:4;background:rgba(255,59,48,0.88);color:#fff;font:bold 11px/1 monospace;padding:3px 6px;border-radius:2px;white-space:nowrap;">{label} ({y_start}\u2013{y_end}px)</div>'
        )
    lines.append(
        f'<div style="position:absolute;top:{sections[-1]["y_end"]}px;left:0;right:0;height:2px;background:#ff3b30;z-index:3;"></div>'
    )

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Section Map</title>
<style>
body {{ margin: 0; background: #111; color: #fff; font-family: system-ui, sans-serif; }}
.header {{ position: sticky; top: 0; z-index: 10; padding: 12px 16px; background: #1a1a1a; border-bottom: 1px solid #333; }}
.container {{ position: relative; display: inline-block; }}
.container img {{ display: block; width: {img_w}px; height: {img_h}px; }}
</style>
</head>
<body>
<div class="header">{screenshot_path.name} · {len(sections)} sections · {img_w}×{img_h}</div>
<div class="container">
  <img src="{screenshot_uri}" alt="{screenshot_path.name}">
  {"".join(lines)}
  {"".join(labels)}
</div>
</body>
</html>"""
    output_path.write_text(html)


def save_crops(img: Image.Image, sections: list[dict], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for index, section in enumerate(sections, start=1):
        crop = img.crop((0, section["y_start"], img.size[0], section["y_end"]))
        crop.save(output_dir / f"{index:02d}-{slugify(section['label'])}.png")


def run_splitter(image_path: str | Path, output_dir: str | Path, config: SplitterConfig) -> Path:
    image_path = Path(image_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    provider = make_provider(config)
    img = load_image(image_path)
    width, height = img.size

    manifest: dict[str, object] = {
        "image": str(image_path),
        "size": {"width": width, "height": height},
        "provider": config.provider,
        "model": config.model,
    }

    if height < config.tall_page_threshold:
        inventory, raw, sections, ruled = query_sections(provider, img, 0, config)
        (output_dir / "section-inventory.md").write_text(inventory.rstrip() + "\n")
        (output_dir / "section-detection-raw.txt").write_text(raw.rstrip() + "\n")
        (output_dir / "sections.json").write_text(json.dumps(sections, indent=2) + "\n")
        if config.save_inputs:
            ruled_path = output_dir / "section-ruler.png"
            ruled.save(ruled_path)
            save_gutter_preview(ruled_path, output_dir / "section-ruler-gutter-preview.png")
        generate_section_map(image_path, output_dir / "section-map.html", sections)
        if config.save_crops:
            save_crops(img, sections, output_dir / "crops")
        manifest["mode"] = "single"
        manifest["sections"] = len(sections)
    else:
        manifest["mode"] = "tall-independent-windows"
        windows = build_even_detection_windows(height, config.tall_page_chunk_count, config.tall_page_overlap)
        manifest["windows"] = windows
        windows_dir = output_dir / "windows"
        windows_dir.mkdir(exist_ok=True)

        window_results = []
        for window in windows:
            crop = img.crop((0, window["y_start"], width, window["y_end"]))
            window_dir = windows_dir / f"window-{window['index']}-{window['y_start']}-{window['y_end']}"
            window_dir.mkdir(exist_ok=True)

            inventory, raw, sections, ruled = query_sections(provider, crop, window["y_start"], config)
            if config.save_inputs:
                source_path = window_dir / "input.png"
                crop.save(window_dir / "source.png")
                ruled.save(source_path)
                save_gutter_preview(source_path, window_dir / "gutter-preview.png")
            (window_dir / "section-inventory.md").write_text(inventory.rstrip() + "\n")
            (window_dir / "section-detection-raw.txt").write_text(raw.rstrip() + "\n")
            (window_dir / "sections.json").write_text(json.dumps(sections, indent=2) + "\n")
            generate_section_map(image_path, window_dir / "section-map.html", sections)
            window_results.append({"window": window, "sections": sections})

        kept, removed, summary = reconcile_window_sections(window_results, height)
        artifacts_dir = output_dir / "reconciled"
        artifacts_dir.mkdir(exist_ok=True)
        (artifacts_dir / "kept-sections.json").write_text(json.dumps(kept, indent=2) + "\n")
        (artifacts_dir / "removed-sections.json").write_text(json.dumps(removed, indent=2) + "\n")
        (artifacts_dir / "reconciliation-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        generate_section_map(image_path, artifacts_dir / "kept-section-map.html", kept)
        if config.save_crops:
            save_crops(img, kept, artifacts_dir / "kept-crops")
            save_crops(img, removed, artifacts_dir / "removed-crops")
        manifest["reconciled"] = summary

    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return output_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Standalone screenshot section splitter.")
    parser.add_argument("screenshot", help="Path to the screenshot image")
    parser.add_argument("-o", "--output-dir", default="splitter-output", help="Output directory")
    parser.add_argument(
        "--provider",
        choices=["openai", "anthropic", "google"],
        default="openai",
        help="Vision provider to use",
    )
    parser.add_argument("--model", default="gpt-5.5", help="Vision model name")
    parser.add_argument("--tall-page-threshold", type=int, default=22000, help="Height threshold for 2-window mode")
    parser.add_argument("--tall-page-overlap", type=int, default=4800, help="Overlap between the 2 tall-page windows")
    parser.add_argument("--max-tokens", type=int, default=4096, help="Max tokens per model call")
    parser.add_argument("--no-inputs", action="store_true", help="Do not save LLM input images")
    parser.add_argument("--no-crops", action="store_true", help="Do not save crops")
    parser.add_argument("-v", "--verbose", action="store_true", help="Print progress")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = SplitterConfig(
        provider=args.provider,
        model=args.model,
        max_tokens=args.max_tokens,
        tall_page_threshold=args.tall_page_threshold,
        tall_page_overlap=args.tall_page_overlap,
        save_inputs=not args.no_inputs,
        save_crops=not args.no_crops,
        verbose=args.verbose,
    )
    output_dir = run_splitter(args.screenshot, args.output_dir, config)
    print(output_dir)


if __name__ == "__main__":
    main()
