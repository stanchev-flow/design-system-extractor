"""Single-shot pipeline: send entire screenshot to LLM."""

import base64
import sys
from io import BytesIO
from pathlib import Path

from PIL import Image

from ..config import AppConfig
from ..models import get_provider


def encode_pil_image(img: Image.Image, max_dimension: int) -> str:
    """Resize a PIL image if needed and return base64-encoded PNG."""
    # Convert to RGB if necessary (handles RGBA, palette, etc.)
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    current = img
    # Resize if either dimension exceeds max
    w, h = current.size
    if w > max_dimension or h > max_dimension:
        ratio = min(max_dimension / w, max_dimension / h)
        new_size = (max(1, int(w * ratio)), max(1, int(h * ratio)))
        current = current.resize(new_size, Image.LANCZOS)

    max_bytes = 5 * 1024 * 1024
    while True:
        buffer = BytesIO()
        current.save(buffer, format="PNG", optimize=True)
        data = buffer.getvalue()
        if len(data) <= max_bytes:
            return base64.b64encode(data).decode("utf-8")
        w, h = current.size
        if w <= 512 and h <= 512:
            return base64.b64encode(data).decode("utf-8")
        current = current.resize(
            (max(1, int(w * 0.85)), max(1, int(h * 0.85))),
            Image.LANCZOS,
        )


def load_and_encode_image(image_path: str, max_dimension: int) -> str:
    """Load an image, resize if needed, and return base64-encoded PNG."""
    img = Image.open(image_path)
    return encode_pil_image(img, max_dimension)


def build_single_shot_views(
    image_path: str,
    max_dimension: int,
) -> list[tuple[str, str]]:
    """Build a full-page overview plus a few tall-page crops for extra detail."""
    img = Image.open(image_path)
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    w, h = img.size
    views: list[tuple[str, str]] = [
        ("full-page overview", encode_pil_image(img.copy(), max_dimension))
    ]

    # Tall screenshots lose too much detail when resized as a single image.
    if h <= max_dimension * 1.5:
        return views

    crop_height = min(h, max(int(h * 0.4), max_dimension))
    candidates = [
        ("top crop", 0),
        ("middle crop", max(0, (h - crop_height) // 2)),
        ("bottom crop", max(0, h - crop_height)),
    ]

    seen_starts: set[int] = set()
    for label, y_start in candidates:
        if y_start in seen_starts:
            continue
        seen_starts.add(y_start)
        crop = img.crop((0, y_start, w, min(h, y_start + crop_height)))
        views.append((label, encode_pil_image(crop, max_dimension)))

    return views


def run(image_path: str, config: AppConfig, output_dir: str | None = None) -> str:
    """Run a two-pass analysis on a screenshot."""
    provider = get_provider(config)

    if config.verbose:
        print(f"Using {config.provider}/{config.model}", file=sys.stderr)
        print(f"Loading image: {image_path}", file=sys.stderr)

    views = build_single_shot_views(image_path, config.max_image_dimension)
    image_b64 = views[0][1]
    additional_views = views[1:]
    view_descriptions = "\n".join(
        f"- View {i + 1}: {label}"
        for i, (label, _) in enumerate(views)
    )
    multi_view_note = (
        "You are receiving multiple views of the same webpage screenshot.\n"
        f"{view_descriptions}\n"
        "Use the overview for global structure and the crops for local detail. "
        "Treat them as the same page, not different pages.\n\n"
    )

    if config.verbose:
        print("Running structural analysis...", file=sys.stderr)

    structural_analysis = provider.analyze_image(
        image_b64=image_b64,
        system_prompt=config.structural_analysis_prompt,
        user_prompt=(
            f"{multi_view_note}"
            "Analyze this website screenshot and produce the structural analysis only. "
            "Do not produce the final design system."
        ),
        max_tokens=config.max_tokens,
        additional_images=additional_views,
    )

    if output_dir:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        with open(out / "structural-analysis.md", "w") as f:
            f.write(structural_analysis.rstrip())
            f.write("\n")

    if config.verbose:
        print("Synthesizing final design system...", file=sys.stderr)

    result = provider.analyze_image(
        image_b64=image_b64,
        system_prompt=config.system_prompt,
        user_prompt=(
            f"{multi_view_note}"
            "Use the structural analysis below as grounding, but verify it against the screenshot shown with this request. "
            "If the structural analysis conflicts with the screenshot, trust the screenshot. "
            "Now produce the final design system.\n\n"
            f"{structural_analysis}"
        ),
        max_tokens=config.max_tokens,
        additional_images=additional_views,
    )
    return result
