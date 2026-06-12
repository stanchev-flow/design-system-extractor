from __future__ import annotations

import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "images" / "raw"
OUT_DIR = ROOT / "images"
W, H = 2048, 1152
BLUE = "#146EF5"
BLACK = "#080808"
GRAY = "#5A5A5A"
LIGHT_GRAY = "#F0F0F0"
WHITE = "#FFFFFF"

FONT_REGULAR = "/System/Library/Fonts/HelveticaNeue.ttc"
FONT_BOLD = "/Library/Fonts/Neue Helvetica Pro OT Family/HelveticaNeueLTPro-Bd.otf"
if not Path(FONT_BOLD).exists():
    FONT_BOLD = FONT_REGULAR


SLIDES = [
    {
        "title": "Screenshot-to-Template",
        "claim": "Turning visual evidence into reusable design-system contracts.",
        "kicker": "Project walkthrough",
        "note": "Screenshot → grounding → design system → generated site",
        "file": "slide-01-title-thesis.png",
    },
    {
        "title": "The Problem",
        "claim": "A screenshot is dense visual evidence, but it does not explain which rules should be reused.",
        "kicker": "Why this exists",
        "note": "The pipeline extracts mechanics instead of copying surface appearance.",
        "file": "slide-02-why-this-exists.png",
    },
    {
        "title": "Pipeline Overview",
        "claim": "The system is a chain of contracts, not one magic prompt.",
        "kicker": "How it works",
        "note": "Each artifact narrows ambiguity before the next model step.",
        "file": "slide-03-pipeline-overview.png",
    },
    {
        "title": "Versioned Runs",
        "claim": "Every experiment is reproducible because runs preserve prompts, outputs, manifests, and notes.",
        "kicker": "Operating model",
        "note": "runs/vNNN is the source of truth for what happened.",
        "file": "slide-04-versioned-runs.png",
    },
    {
        "title": "Crops Control Everything",
        "claim": "Bad section boundaries poison downstream grounding, tokens, and generated layouts.",
        "kicker": "Learning 1",
        "note": "Overlap-aware reconciliation fixed boundary drift on tall pages.",
        "file": "slide-05-crops-control-everything.png",
    },
    {
        "title": "Ground Mechanics",
        "claim": "The prompts had to turn vague mood into observable layout, typography, surface, and graphic mechanics.",
        "kicker": "Learning 2",
        "note": "Airy, premium, and technical become reusable implementation cues.",
        "file": "slide-06-ground-mechanics.png",
    },
    {
        "title": "Source Styles As Evidence",
        "claim": "Exact CSS values help only when they map to the right reusable visual role.",
        "kicker": "Learning 3",
        "note": "The source-style ledger separates raw values from generation-safe roles.",
        "file": "slide-07-source-styles-evidence.png",
    },
    {
        "title": "The Missing Middle",
        "claim": "Host-surface to child-component pairings preserve fidelity better than flat token lists.",
        "kicker": "Learning 4",
        "note": "Buttons, cards, badges, and dividers are bound to their parent surfaces.",
        "file": "slide-08-surface-relationships.png",
    },
    {
        "title": "Schema Plus Repair",
        "claim": "Structured extraction helps, but critique and repair loops won the conversion-fidelity test.",
        "kicker": "Learning 5",
        "note": "The strongest path combines schema-first synthesis with targeted repair.",
        "file": "slide-09-schema-plus-repair.png",
    },
    {
        "title": "Generated Assets",
        "claim": "Image slots became safer when prompts were slot-specific, reference-aware, and locally audited.",
        "kicker": "Last mile",
        "note": "gpt-image-2 assets are generated after HTML creates explicit asset briefs.",
        "file": "slide-10-generated-assets.png",
    },
    {
        "title": "The Viewer Is The Product",
        "claim": "The comparison viewer makes the pipeline inspectable enough to learn from each run.",
        "kicker": "Debugging surface",
        "note": "Source, grounding, design system, generated HTML, assets, and audits stay side by side.",
        "file": "slide-11-viewer-product.png",
    },
    {
        "title": "What To Remember",
        "claim": "The durable idea is evidence preservation through explicit intermediate contracts.",
        "kicker": "Takeaway",
        "note": "Version everything. Preserve relationships. Audit before generation drifts.",
        "file": "slide-12-takeaways.png",
    },
]


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REGULAR, size=size)


def wrap_text(draw: ImageDraw.ImageDraw, text: str, typeface: ImageFont.FreeTypeFont, width: int) -> str:
    words = text.split()
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        trial = " ".join(current + [word])
        if draw.textbbox((0, 0), trial, font=typeface)[2] <= width or not current:
            current.append(word)
        else:
            lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))
    return "\n".join(lines)


def compose_one(index: int, spec: dict[str, str]) -> Path:
    raw_path = RAW_DIR / f"visual-{index:02d}.png"
    if not raw_path.exists():
        raise FileNotFoundError(raw_path)

    img = Image.open(raw_path).convert("RGB").resize((W, H), Image.Resampling.LANCZOS)
    overlay = Image.new("RGBA", (W, H), (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)

    # Webflow-like clear black/white editorial field for exact text.
    panel_w = 840
    draw.rectangle((0, 0, panel_w, H), fill=(255, 255, 255, 255))
    draw.rectangle((panel_w, 0, panel_w + 2, H), fill=(8, 8, 8, 28))
    draw.rectangle((96, 96, 188, 104), fill=BLUE)

    kicker_font = font(25, bold=True)
    title_font = font(76, bold=True)
    claim_font = font(38)
    note_font = font(24)
    footer_font = font(20, bold=True)

    x = 96
    y = 132
    draw.text((x, y), spec["kicker"].upper(), fill=BLUE, font=kicker_font)
    y += 72
    title = wrap_text(draw, spec["title"], title_font, 650)
    draw.text((x, y), title, fill=BLACK, font=title_font, spacing=8)
    title_lines = title.count("\n") + 1
    y += title_lines * 86 + 44
    claim = wrap_text(draw, spec["claim"], claim_font, 640)
    draw.text((x, y), claim, fill=BLACK, font=claim_font, spacing=13)
    claim_lines = claim.count("\n") + 1
    y += claim_lines * 54 + 48
    draw.line((x, y, x + 560, y), fill=LIGHT_GRAY, width=2)
    y += 34
    note = wrap_text(draw, spec["note"], note_font, 560)
    draw.text((x, y), note, fill=GRAY, font=note_font, spacing=9)

    page = f"{index:02d} / {len(SLIDES):02d}"
    draw.text((x, H - 104), page, fill=BLACK, font=footer_font)
    draw.text((x + 132, H - 104), "Screenshot-to-Template", fill=GRAY, font=footer_font)

    out = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    out_path = OUT_DIR / spec["file"]
    out.save(out_path, quality=96)
    return out_path


def make_contact_sheet(paths: list[Path]) -> Path:
    thumbs = []
    for path in paths:
        thumb = Image.open(path).convert("RGB")
        thumb.thumbnail((480, 270), Image.Resampling.LANCZOS)
        canvas = Image.new("RGB", (480, 270), WHITE)
        canvas.paste(thumb, ((480 - thumb.width) // 2, (270 - thumb.height) // 2))
        thumbs.append(canvas)

    sheet = Image.new("RGB", (4 * 480 + 5 * 24, 3 * 270 + 4 * 24), "#F0F0F0")
    for i, thumb in enumerate(thumbs):
        col = i % 4
        row = i // 4
        sheet.paste(thumb, (24 + col * (480 + 24), 24 + row * (270 + 24)))
    out = OUT_DIR / "contact-sheet.png"
    sheet.save(out, quality=94)
    return out


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    paths = [compose_one(i, spec) for i, spec in enumerate(SLIDES, start=1)]
    make_contact_sheet(paths)
    for path in paths:
        print(path)


if __name__ == "__main__":
    main()
