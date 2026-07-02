#!/usr/bin/env python3
"""
Image-crop pipeline: screenshot -> 3 section crops -> Services page HTML.

This runner is intentionally separate from run_pipeline.py. It still uses the
existing section detector and cropper, but it does not synthesize or send a
design-system markdown artifact to the site-generation model.

Usage:
    ./venv/bin/python run_image_pipeline.py
    ./venv/bin/python run_image_pipeline.py --version v001
    ./venv/bin/python run_image_pipeline.py --screenshots-dir "screenshots/use for testing"
    ./venv/bin/python run_image_pipeline.py --viewer-only
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).parent / "src"))

from screenshot_to_template.config import AppConfig, load_config
from screenshot_to_template.models import get_provider
from screenshot_to_template.output import generate_section_map
from screenshot_to_template.pipeline.single_shot import encode_pil_image
from screenshot_to_template.pipeline.splitter import (
    compute_crop_bounds,
    crop_sections,
    detect_sections_with_llm,
)
from screenshot_to_template.tracking import token_usage_context, update_step_status


PROJECT_DIR = Path(__file__).parent
RUNS_DIR = PROJECT_DIR / "runs"
IMAGE_RUNS_DIR = RUNS_DIR / "image"
VIEWER_IMAGE_PATH = PROJECT_DIR / "viewer-image.html"
DEFAULT_SITE_MAX_TOKENS = 32768
SCREENSHOT_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}

DEFAULT_IMAGE_SITE_PROMPT = """\
You are an expert frontend developer and visual design-system interpreter.

You will receive exactly three cropped sections from one source website screenshot. Infer the reusable design system directly from those image crops, then generate a new Services page that feels native to that system.

Critical rules:
- Do not ask for, reference, or depend on a text design-system markdown artifact.
- Use only the three section screenshots as visual evidence for the system.
- Treat the crops as examples of a reusable visual language, not sections to copy verbatim.
- Generate a complete Services page for a professional service business, with realistic service content, navigation, service offerings, proof, process, FAQ or CTA, and footer.
- Preserve the source system's typography character, spacing rhythm, surface relationships, component sizing, button/label recipes, card/panel behavior, image/graphic treatment, border/radius/depth logic, and page density.
- Keep compact controls such as buttons, badges, tags, chips, and eyebrows content-hugging unless a crop clearly shows a full-width control.
- Use CSS custom properties for inferred colors, surface roles, typography, spacing, radius, and component roles.
- Make the page responsive with CSS Grid/Flexbox.
- Output a single complete HTML file with all CSS in a <style> tag.
- Do not use external stock-photo URLs. For major imagery, use intentionally sized <img> placeholders with blank SVG/data URI sources and concise data-stt-asset-brief attributes that describe the needed visual.
- Icons may be simple inline SVG.
- Do not use JavaScript frameworks.
- Do NOT use viewport units (vh/svh/dvh/vw) anywhere — the output is rendered inside an iframe. Use container-query units (cqw/cqh/cqi) against a `container-type: size` ancestor; the root wrapper must set the container context.
- Return only the HTML code, no markdown fences or explanations.
"""


def load_api_keys() -> None:
    """Load API keys from repo-local .env.local when shell env is empty."""
    env_file = PROJECT_DIR / ".env.local"
    if not env_file.exists():
        return

    for line in env_file.read_text().splitlines():
        line = line.strip()
        if "=" not in line or line.startswith("#"):
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if key in {"GEMINI_API_KEY", "GOOGLE_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY"} and value:
            os.environ.setdefault(key, value)

    if not os.environ.get("GOOGLE_API_KEY") and os.environ.get("GEMINI_API_KEY"):
        os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]


def default_screenshots_dir() -> Path:
    candidates = [
        PROJECT_DIR / "screenshots" / "best" / "use for testing",
        PROJECT_DIR / "screenshots" / "use for testing",
        PROJECT_DIR / "screenshots" / "use for testing new",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def get_next_image_version() -> str:
    if not IMAGE_RUNS_DIR.exists():
        return "v001"
    existing = sorted(
        d.name
        for d in IMAGE_RUNS_DIR.iterdir()
        if d.is_dir() and re.fullmatch(r"v\d{3}", d.name)
    )
    if not existing:
        return "v001"
    return f"v{int(existing[-1][1:]) + 1:03d}"


def safe_slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "item"


def screenshot_name(path: Path) -> str:
    return safe_slug(path.stem)


def iter_screenshots(screenshots_dir: Path, max_items: int | None = None) -> list[Path]:
    if not screenshots_dir.exists():
        raise FileNotFoundError(f"Screenshots directory not found: {screenshots_dir}")
    paths = [
        path
        for path in sorted(screenshots_dir.iterdir())
        if path.is_file() and path.suffix.lower() in SCREENSHOT_EXTENSIONS
    ]
    if max_items is not None:
        return paths[:max_items]
    return paths


def image_to_data_uri(path: Path) -> str:
    mime = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }.get(path.suffix.lower(), "image/png")
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def strip_html_fence(text: str) -> str:
    result = text.strip()
    if result.startswith("```html"):
        result = result[7:]
    elif result.startswith("```"):
        result = result[3:]
    if result.endswith("```"):
        result = result[:-3]
    return result.strip()


def select_three_section_indices(crop_records: list[dict], explicit_indices: list[int] | None = None) -> list[int]:
    """Return zero-based crop indexes to send: hero, middle section, footer."""
    total = len(crop_records)
    if total <= 0:
        return []

    if explicit_indices:
        selected: list[int] = []
        for one_based in explicit_indices:
            index = one_based - 1
            if 0 <= index < total and index not in selected:
                selected.append(index)
            if len(selected) == 3:
                break
        if len(selected) != 3:
            raise ValueError(
                f"--crop-indices must resolve to exactly 3 distinct sections; got {len(selected)}"
            )
        return selected

    if total <= 3:
        return list(range(total))

    def label_at(index: int) -> str:
        return str(crop_records[index].get("label", "")).lower()

    hero_index = next(
        (index for index in range(total) if re.search(r"\b(hero|headline|masthead)\b", label_at(index))),
        None,
    )
    if hero_index is None:
        hero_index = 1 if total > 1 and re.search(r"\b(nav|header|menu)\b", label_at(0)) else 0

    footer_index = next(
        (index for index in range(total - 1, -1, -1) if re.search(r"\b(footer)\b", label_at(index))),
        total - 1,
    )

    available = [index for index in range(total) if index not in {hero_index, footer_index}]
    if not available:
        available = [index for index in range(total) if index != hero_index]
    target = (hero_index + footer_index) / 2 if footer_index != hero_index else total / 2
    center_index = min(available, key=lambda index: abs(index - target)) if available else hero_index

    selected = [hero_index, center_index, footer_index]
    deduped: list[int] = []
    for index in selected:
        if index not in deduped:
            deduped.append(index)
    for index in range(total):
        if len(deduped) >= 3:
            break
        if index not in deduped:
            deduped.append(index)
    return deduped[:3]


def build_services_generation_user_prompt(
    screenshot_path: Path,
    selected: list[dict],
) -> str:
    lines = [
        "Create a new Services page from the reusable visual system visible in the three section crops attached to this request.",
        "The selected crops are intentionally the source hero section, one center/body section, and the footer section.",
        "",
        "The image order is:",
    ]
    for item in selected:
        bounds = item["bounds"]
        lines.append(
            f"- Image {item['image_number']} ({item.get('selection_role', 'reference')}): section {item['section_number']} "
            f"({item['label']}), original y={bounds['y_start']} to {bounds['y_end']}."
        )
    lines.extend(
        [
            "",
            f"Source screenshot file name: {screenshot_path.name}",
            "",
            "Page goal:",
            "- Generate a Services page, not a generic landing page.",
            "- Invent credible service-business copy, but keep visual decisions grounded in the crops.",
            "- Include navigation, services overview, detailed service cards or modules, process/proof, a final CTA, and footer.",
            "- If the crop system is editorial, playful, futuristic, minimal, or formal, let that character shape the Services page.",
        ]
    )
    return "\n".join(lines)


def generate_services_page_from_crops(
    *,
    crop_paths: list[Path],
    selected: list[dict],
    screenshot_path: Path,
    config: AppConfig,
    output_dir: Path,
    system_prompt: str,
) -> tuple[str, str]:
    provider = get_provider(config)
    image_b64s = [
        encode_pil_image(Image.open(path).convert("RGB"), config.max_image_dimension)
        for path in crop_paths
    ]
    if not image_b64s:
        raise ValueError("No crop images were selected for site generation.")

    user_prompt = build_services_generation_user_prompt(screenshot_path, selected)
    prompt_artifact = (
        "# Services Image Generation Prompt\n\n"
        "## System Prompt\n\n"
        f"{system_prompt.strip()}\n\n"
        "## User Prompt\n\n"
        f"{user_prompt.strip()}\n"
    )
    (output_dir / "services-generation-prompt.md").write_text(prompt_artifact)

    response = provider.analyze_image(
        image_b64=image_b64s[0],
        additional_images=[
            (f"selected crop {index + 2}", image_b64)
            for index, image_b64 in enumerate(image_b64s[1:])
        ],
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        max_tokens=max(config.max_tokens, DEFAULT_SITE_MAX_TOKENS),
    )
    return strip_html_fence(response), prompt_artifact


def process_screenshot(
    *,
    screenshot_path: Path,
    item_dir: Path,
    config: AppConfig,
    crop_indices: list[int] | None,
    system_prompt: str,
) -> dict:
    item_dir.mkdir(parents=True, exist_ok=True)
    update_step_status(item_dir, "section_detection", "in_progress")

    copied_screenshot = item_dir / f"screenshot{screenshot_path.suffix.lower()}"
    shutil.copy2(screenshot_path, copied_screenshot)

    provider = get_provider(config)
    with token_usage_context(item_dir, "section_detection"):
        detection = detect_sections_with_llm(str(screenshot_path), provider, config)
    sections = detection.final_sections
    if not sections:
        raise ValueError("No sections detected.")
    update_step_status(item_dir, "section_detection", "completed", {"sections_detected": len(sections)})

    source_img = Image.open(screenshot_path).convert("RGB")
    crop_bounds = compute_crop_bounds(sections, source_img.size[1])
    crops = crop_sections(str(screenshot_path), sections)

    (item_dir / "section-inventory.md").write_text(detection.inventory_response.rstrip() + "\n")
    (item_dir / "section-detection-raw.txt").write_text(detection.raw_response.rstrip() + "\n")
    (item_dir / "sections.json").write_text(json.dumps(sections, indent=2) + "\n")
    (item_dir / "crop-bounds.json").write_text(json.dumps(crop_bounds, indent=2) + "\n")
    generate_section_map(
        screenshot_path=str(screenshot_path),
        output_path=item_dir / "section-map.html",
        sections=sections,
        crop_bounds=crop_bounds,
    )

    crops_dir = item_dir / "crops"
    crops_dir.mkdir(exist_ok=True)
    crop_records: list[dict] = []
    for index, ((crop_img, label), bounds) in enumerate(zip(crops, crop_bounds), start=1):
        crop_path = crops_dir / f"{index:02d}-{safe_slug(label)}.png"
        crop_img.save(crop_path)
        crop_records.append(
            {
                "index": index,
                "label": label,
                "path": str(crop_path.relative_to(item_dir)),
                "bounds": bounds,
            }
        )

    selected_indices = select_three_section_indices(crop_records, crop_indices)
    selected_records: list[dict] = []
    selected_crop_paths: list[Path] = []
    for image_number, crop_index in enumerate(selected_indices, start=1):
        record = crop_records[crop_index]
        role = ["hero", "center/body", "footer/bottom"][image_number - 1]
        selected = {
            **record,
            "image_number": image_number,
            "section_number": record["index"],
            "selection_role": role,
        }
        selected_records.append(selected)
        selected_crop_paths.append(item_dir / record["path"])

    (item_dir / "selected-crops.json").write_text(json.dumps(selected_records, indent=2) + "\n")

    update_step_status(item_dir, "services_site_generation", "in_progress")
    with token_usage_context(item_dir, "services_site_generation"):
        html, prompt_artifact = generate_services_page_from_crops(
            crop_paths=selected_crop_paths,
            selected=selected_records,
            screenshot_path=screenshot_path,
            config=config,
            output_dir=item_dir,
            system_prompt=system_prompt,
        )
    site_path = item_dir / "services-page.html"
    site_path.write_text(html.rstrip() + "\n")
    update_step_status(item_dir, "services_site_generation", "completed")
    update_step_status(item_dir, "run_complete", "completed")

    return {
        "name": screenshot_name(screenshot_path),
        "source_path": str(screenshot_path),
        "screenshot": str(copied_screenshot.relative_to(item_dir.parent)),
        "sections": str((item_dir / "sections.json").relative_to(item_dir.parent)),
        "section_map": str((item_dir / "section-map.html").relative_to(item_dir.parent)),
        "crops": [
            {**record, "path": str((item_dir / record["path"]).relative_to(item_dir.parent))}
            for record in crop_records
        ],
        "selected_crops": [
            {**record, "path": str((item_dir / record["path"]).relative_to(item_dir.parent))}
            for record in selected_records
        ],
        "prompt": str((item_dir / "services-generation-prompt.md").relative_to(item_dir.parent)),
        "site_html": str(site_path.relative_to(item_dir.parent)),
    }


def run_image_pipeline(
    *,
    version: str,
    screenshots_dir: Path,
    config_path: str | None,
    max_items: int | None,
    crop_indices: list[int] | None,
    provider_name: str | None,
    model_name: str | None,
    system_prompt_path: Path | None,
) -> None:
    load_api_keys()
    IMAGE_RUNS_DIR.mkdir(parents=True, exist_ok=True)
    version_dir = IMAGE_RUNS_DIR / version
    version_dir.mkdir(parents=True, exist_ok=True)

    config = load_config(config_path)
    if provider_name:
        provider_override = {**vars(config), "provider": provider_name}
        if not model_name:
            provider_override["model"] = ""
        config = AppConfig(**provider_override)
    if model_name:
        config = AppConfig(**{**vars(config), "model": model_name})

    system_prompt = DEFAULT_IMAGE_SITE_PROMPT
    if system_prompt_path:
        system_prompt = system_prompt_path.read_text().strip()
    (version_dir / "services-image-prompt.md").write_text(system_prompt.strip() + "\n")
    (version_dir / "display-name.txt").write_text(f"{version} (Image Crops -> Services)\n")

    screenshots = iter_screenshots(screenshots_dir, max_items=max_items)
    manifest = {
        "version": version,
        "timestamp": datetime.now().isoformat(),
        "pipeline": "image-crops-to-services-page",
        "screenshots_dir": str(screenshots_dir),
        "provider": config.provider,
        "model": config.model,
        "crop_selection": crop_indices or "hero-center-footer-bottom",
        "items": [],
    }

    changes_path = version_dir / "changes.md"
    changes_path.write_text(
        f"# {version} Image-Crop Services Pipeline\n\n"
        "- Initialized image-crop Services-page run folder.\n"
        f"- Source screenshots directory: `{screenshots_dir}`.\n"
        f"- Generation provider/model: `{config.provider}/{config.model}`.\n"
    )

    for screenshot_path in screenshots:
        name = screenshot_name(screenshot_path)
        print(f"[{version}] {name}: detecting sections, cropping, and generating Services page...")
        item_dir = version_dir / name
        try:
            item = process_screenshot(
                screenshot_path=screenshot_path,
                item_dir=item_dir,
                config=config,
                crop_indices=crop_indices,
                system_prompt=system_prompt,
            )
            manifest["items"].append(item)
            with changes_path.open("a") as f:
                selected = ", ".join(
                    f"{crop['selection_role']}={crop['section_number']}"
                    for crop in item["selected_crops"]
                )
                f.write(
                    f"- `{name}`: detected {len(item['crops'])} sections, "
                    f"sent crop sections {selected}, generated `services-page.html`.\n"
                )
        except Exception as exc:
            error_payload = {"name": name, "source_path": str(screenshot_path), "error": str(exc)}
            manifest["items"].append(error_payload)
            (item_dir / "error.txt").write_text(str(exc) + "\n")
            update_step_status(item_dir, "run_complete", "failed", {"error": str(exc)})
            with changes_path.open("a") as f:
                f.write(f"- `{name}`: failed with `{exc}`.\n")
            print(f"[{version}] {name}: failed: {exc}", file=sys.stderr)

    (version_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    with changes_path.open("a") as f:
        f.write("- Wrote `manifest.json` and regenerated `viewer-image.html`.\n")
    generate_image_viewer(IMAGE_RUNS_DIR, VIEWER_IMAGE_PATH)


def load_image_version_data(version_dir: Path) -> dict | None:
    manifest_path = version_dir / "manifest.json"
    if not manifest_path.exists():
        return None
    manifest = json.loads(manifest_path.read_text())
    items = []
    for entry in manifest.get("items", []):
        if entry.get("error"):
            items.append(entry)
            continue
        screenshot_path = version_dir / entry["screenshot"]
        site_path = version_dir / entry["site_html"]
        prompt_path = version_dir / entry["prompt"]
        selected_crops = []
        for crop in entry.get("selected_crops", []):
            crop_path = version_dir / crop["path"]
            image_number = int(crop.get("image_number") or 0)
            fallback_role = {1: "hero", 2: "center/body", 3: "footer/bottom"}.get(image_number, "reference")
            selected_crops.append(
                {
                    **crop,
                    "selection_role": crop.get("selection_role") or fallback_role,
                    "uri": image_to_data_uri(crop_path) if crop_path.exists() else "",
                }
            )
        items.append(
            {
                "name": entry.get("name", ""),
                "screenshot_uri": image_to_data_uri(screenshot_path) if screenshot_path.exists() else "",
                "site_html": site_path.read_text() if site_path.exists() else "<html><body><p>Missing site output.</p></body></html>",
                "site_url": site_path.resolve().as_uri() if site_path.exists() else "",
                "prompt": prompt_path.read_text() if prompt_path.exists() else "",
                "prompt_path": str(prompt_path.resolve()) if prompt_path.exists() else "",
                "section_map_url": (version_dir / entry["section_map"]).resolve().as_uri() if entry.get("section_map") else "",
                "selected_crops": selected_crops,
            }
        )

    display_name_path = version_dir / "display-name.txt"
    display_name = display_name_path.read_text().strip() if display_name_path.exists() else version_dir.name
    return {
        "display_name": display_name,
        "timestamp": manifest.get("timestamp", ""),
        "provider": manifest.get("provider", ""),
        "model": manifest.get("model", ""),
        "items": items,
    }


def encode_viewer_payload(data: dict) -> str:
    return base64.b64encode(json.dumps(data).encode("utf-8")).decode("ascii")


def generate_image_viewer(runs_dir: Path, output_path: Path) -> None:
    versions = sorted(
        [
            path.name
            for path in runs_dir.iterdir()
            if path.is_dir() and re.fullmatch(r"v\d{3}", path.name) and (path / "manifest.json").exists()
        ],
        reverse=True,
    ) if runs_dir.exists() else []

    data = {
        version: load_image_version_data(runs_dir / version)
        for version in versions
    }
    data = {version: payload for version, payload in data.items() if payload}
    output_path.write_text(build_image_viewer_html(list(data.keys()), encode_viewer_payload(data)))


def build_image_viewer_html(versions: list[str], data_b64: str) -> str:
    versions_json = json.dumps(versions)
    data_b64_json = json.dumps(data_b64)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Image-Crop Services Pipeline Viewer</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    background: #09090b;
    color: #f4f4f5;
    font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  }}
  .topbar {{
    position: sticky;
    top: 0;
    z-index: 20;
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 10px 14px;
    border-bottom: 1px solid #27272a;
    background: rgba(9, 9, 11, 0.94);
    backdrop-filter: blur(12px);
  }}
  h1 {{ margin: 0; font-size: 14px; font-weight: 650; white-space: nowrap; }}
  select, button {{
    height: 30px;
    border: 1px solid #3f3f46;
    border-radius: 6px;
    background: #18181b;
    color: #f4f4f5;
    font: inherit;
    font-size: 12px;
  }}
  select {{ min-width: 300px; padding: 0 10px; }}
  button {{ padding: 0 10px; cursor: pointer; }}
  button.active {{ background: #f4f4f5; color: #09090b; border-color: #f4f4f5; }}
  .meta {{ margin-left: auto; color: #a1a1aa; font-size: 12px; white-space: nowrap; }}
  .empty {{ padding: 80px 24px; color: #a1a1aa; text-align: center; }}
  .item-title {{
    position: sticky;
    top: 51px;
    z-index: 10;
    padding: 9px 14px;
    border-bottom: 1px solid #27272a;
    background: rgba(9, 9, 11, 0.92);
    backdrop-filter: blur(12px);
    font-size: 13px;
    font-weight: 650;
    text-transform: capitalize;
  }}
  .grid {{
    display: grid;
    grid-template-columns: minmax(280px, 460px) minmax(360px, 620px) minmax(640px, 1fr);
    min-width: 1280px;
    border-bottom: 1px solid #27272a;
  }}
  .cell {{ border-right: 1px solid #27272a; min-width: 0; }}
  .cell:last-child {{ border-right: 0; }}
  .label {{
    position: sticky;
    top: 86px;
    z-index: 8;
    display: flex;
    align-items: center;
    gap: 8px;
    min-height: 38px;
    padding: 8px 12px;
    border-bottom: 1px solid #27272a;
    background: rgba(9, 9, 11, 0.92);
    backdrop-filter: blur(12px);
    color: #a1a1aa;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.02em;
    text-transform: uppercase;
  }}
  .source-img {{ display: block; width: 100%; height: auto; }}
  .crops {{ display: grid; gap: 12px; padding: 12px; }}
  .crop-card {{
    overflow: hidden;
    border: 1px solid #27272a;
    border-radius: 8px;
    background: #111113;
  }}
  .crop-card img {{ display: block; width: 100%; height: auto; }}
  .crop-caption {{ padding: 7px 9px; color: #a1a1aa; font-size: 11px; }}
  iframe {{ display: block; width: 100%; min-height: 880px; border: 0; background: white; }}
  pre {{
    display: none;
    margin: 0;
    padding: 14px;
    max-height: 520px;
    overflow: auto;
    white-space: pre-wrap;
    color: #d4d4d8;
    background: #111113;
    font-size: 12px;
    line-height: 1.55;
  }}
  body.show-prompt pre {{ display: block; }}
  body.show-prompt iframe {{ min-height: 620px; }}
</style>
</head>
<body>
<div class="topbar">
  <h1>Image-Crop Services Pipeline Viewer</h1>
  <select id="version-select"></select>
  <button id="prompt-toggle" type="button">Show Prompt</button>
  <div class="meta" id="meta"></div>
</div>
<main id="content"></main>
<script>
const VERSION_ORDER = {versions_json};
const ALL_DATA = JSON.parse(atob({data_b64_json} || ""));
let currentVersion = VERSION_ORDER[0] || "";

function esc(value) {{
  return String(value ?? "").replace(/[&<>"']/g, char => ({{
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;"
  }}[char]));
}}

function renderVersionSelect() {{
  const select = document.getElementById("version-select");
  select.innerHTML = VERSION_ORDER.map(version => {{
    const data = ALL_DATA[version] || {{}};
    return `<option value="${{esc(version)}}">${{esc(data.display_name || version)}}</option>`;
  }}).join("");
  select.value = currentVersion;
  select.addEventListener("change", () => {{
    currentVersion = select.value;
    render();
  }});
}}

function render() {{
  const data = ALL_DATA[currentVersion];
  const content = document.getElementById("content");
  const meta = document.getElementById("meta");
  if (!data) {{
    content.innerHTML = '<div class="empty">No image-crop pipeline runs yet. Run <code>./venv/bin/python run_image_pipeline.py</code> to create one.</div>';
    meta.textContent = "";
    return;
  }}
  meta.textContent = `${{data.provider || ""}}/${{data.model || ""}} · ${{data.items?.length || 0}} item(s)`;
  content.innerHTML = (data.items || []).map(item => {{
    if (item.error) {{
      return `<section><div class="item-title">${{esc(item.name)}} failed</div><div class="empty">${{esc(item.error)}}</div></section>`;
    }}
    const crops = (item.selected_crops || []).map(crop => `
      <figure class="crop-card">
        <img src="${{crop.uri}}" alt="${{esc(crop.label)}} crop">
        <figcaption class="crop-caption">Image ${{crop.image_number}} · ${{esc(crop.selection_role || 'reference')}} · Section ${{crop.section_number}} · ${{esc(crop.label)}}</figcaption>
      </figure>
    `).join("");
    return `
      <section>
        <div class="item-title">${{esc(item.name)}}</div>
        <div class="grid">
          <div class="cell">
            <div class="label">Source Screenshot</div>
            <img class="source-img" src="${{item.screenshot_uri}}" alt="${{esc(item.name)}} source screenshot">
          </div>
          <div class="cell">
            <div class="label">Three Section Crops <button type="button" onclick="window.open('${{item.section_map_url}}', '_blank')">Map</button></div>
            <div class="crops">${{crops}}</div>
          </div>
          <div class="cell">
            <div class="label">Generated Services Page <button type="button" onclick="window.open('${{item.site_url}}', '_blank')">Open</button></div>
            <iframe src="${{item.site_url}}" loading="lazy"></iframe>
            <pre>${{esc(item.prompt || "")}}</pre>
          </div>
        </div>
      </section>
    `;
  }}).join("");
}}

document.getElementById("prompt-toggle").addEventListener("click", event => {{
  document.body.classList.toggle("show-prompt");
  event.currentTarget.classList.toggle("active", document.body.classList.contains("show-prompt"));
  event.currentTarget.textContent = document.body.classList.contains("show-prompt") ? "Hide Prompt" : "Show Prompt";
}});

renderVersionSelect();
render();
</script>
</body>
</html>
"""


def parse_crop_indices(value: str | None) -> list[int] | None:
    if not value:
        return None
    indices = []
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        indices.append(int(part))
    return indices


def main() -> None:
    parser = argparse.ArgumentParser(description="Run image-crop-to-Services-page pipeline")
    parser.add_argument("--version", default=None, help="Image run version label under runs/image (default: auto-increment)")
    parser.add_argument("--screenshots-dir", default=None, help="Path to screenshots directory")
    parser.add_argument("--config", default=None, help="Optional YAML config override")
    parser.add_argument("--max-items", type=int, default=None, help="Limit screenshots processed")
    parser.add_argument("--crop-indices", default=None, help="Manual comma-separated 1-based section crop indices to send instead of hero, center, footer; e.g. 1,4,8")
    parser.add_argument("--provider", default=None, choices=("anthropic", "google", "openai"), help="Override generation provider")
    parser.add_argument("--model", default=None, help="Override generation model")
    parser.add_argument("--system-prompt", default=None, help="Optional Services image-generation system prompt file")
    parser.add_argument("--viewer-only", action="store_true", help="Regenerate viewer-image.html without running models")
    args = parser.parse_args()

    if args.viewer_only:
        generate_image_viewer(IMAGE_RUNS_DIR, VIEWER_IMAGE_PATH)
        print(f"viewer-image regenerated at {VIEWER_IMAGE_PATH}")
        return

    run_image_pipeline(
        version=args.version or get_next_image_version(),
        screenshots_dir=Path(args.screenshots_dir) if args.screenshots_dir else default_screenshots_dir(),
        config_path=args.config,
        max_items=args.max_items,
        crop_indices=parse_crop_indices(args.crop_indices),
        provider_name=args.provider,
        model_name=args.model,
        system_prompt_path=Path(args.system_prompt) if args.system_prompt else None,
    )


if __name__ == "__main__":
    main()
