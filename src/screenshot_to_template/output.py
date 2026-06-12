"""Markdown output cleaning, file writing, and saved artifact helpers."""

import base64
import re
from pathlib import Path

from PIL import Image


def image_to_data_uri(path: str | Path) -> str:
    """Convert a local image file into a data URI for embedding in HTML."""
    path = Path(path)
    suffix = path.suffix.lower()
    mime_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }
    mime = mime_map.get(suffix, "image/png")
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return f"data:{mime};base64,{b64}"


def clean_markdown(raw: str) -> str:
    """Strip common LLM artifacts from markdown output."""
    text = raw.strip()
    # Remove leading ```markdown fence
    if text.startswith("```markdown"):
        text = text[len("```markdown"):].strip()
    elif text.startswith("```md"):
        text = text[len("```md"):].strip()
    elif text.startswith("```"):
        text = text[3:].strip()
    # Remove trailing ``` fence
    if text.endswith("```"):
        text = text[:-3].strip()
    return text


def write_output(content: str, output_path: str) -> None:
    """Clean and write markdown content to file."""
    cleaned = clean_markdown(content)
    with open(output_path, "w") as f:
        f.write(cleaned)
        f.write("\n")


def save_ruler_gutter_preview(
    source_path: str | Path,
    output_path: str | Path,
    gutter_width: int = 220,
    width_scale: int = 4,
) -> None:
    """Save a widened preview of the ruler gutter so labels remain readable in viewers."""
    source_path = Path(source_path)
    output_path = Path(output_path)
    img = Image.open(source_path).convert("RGB")
    gutter = img.crop((0, 0, min(gutter_width, img.size[0]), img.size[1]))
    widened = gutter.resize((gutter.size[0] * max(1, width_scale), gutter.size[1]), Image.Resampling.LANCZOS)
    widened.save(output_path)


def generate_section_map(
    screenshot_path: str | Path,
    output_path: str | Path,
    sections: list[dict],
    crop_bounds: list[dict] | None = None,
) -> None:
    """Generate an HTML preview showing only the detected section boundaries."""
    screenshot_path = Path(screenshot_path)
    output_path = Path(output_path)
    if not sections:
        return

    img = Image.open(screenshot_path)
    img_w, img_h = img.size
    screenshot_uri = image_to_data_uri(screenshot_path)

    lines_html = []
    labels_html = []
    for section in sections:
        y_start = section["y_start"]
        y_end = section["y_end"]
        label = section["label"]
        lines_html.append(
            f'<div style="position:absolute;top:{y_start}px;left:0;right:0;height:2px;background:#ff3b30;z-index:3;"></div>'
        )
        labels_html.append(
            f'<div style="position:absolute;top:{y_start + 4}px;left:8px;z-index:4;background:rgba(255,59,48,0.88);color:#fff;font:bold 11px/1 monospace;padding:3px 6px;border-radius:2px;white-space:nowrap;">{label} ({y_start}\u2013{y_end}px)</div>'
        )
    lines_html.append(
        f'<div style="position:absolute;top:{sections[-1]["y_end"]}px;left:0;right:0;height:2px;background:#ff3b30;z-index:3;"></div>'
    )

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Section Map - {screenshot_path.stem}</title>
<style>
  body {{ margin: 0; background: #111; color: #fff; font-family: system-ui, sans-serif; }}
  .header {{ position: sticky; top: 0; z-index: 10; padding: 12px 16px; background: #1a1a1a; border-bottom: 1px solid #333; display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }}
  .header h1 {{ font-size: 14px; margin: 0; }}
  .header span {{ font-size: 12px; color: #888; }}
  .container {{ position: relative; display: inline-block; }}
  .container img {{ display: block; width: {img_w}px; height: {img_h}px; }}
</style>
</head>
<body>
<div class="header">
  <h1>Section Map: {screenshot_path.stem}</h1>
  <span>{len(sections)} sections detected · {img_w}×{img_h}px</span>
</div>
<div class="container">
  <img src="{screenshot_uri}" alt="{screenshot_path.stem}">
  {"".join(lines_html)}
  {"".join(labels_html)}
</div>
</body>
</html>"""

    with open(output_path, "w") as f:
        f.write(html)
