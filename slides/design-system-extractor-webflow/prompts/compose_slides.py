from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "images" / "raw"
OUT_DIR = ROOT / "images"
W, H = 2048, 1152

BLUE = "#146EF5"
BLACK = "#080808"
CHARCOAL = "#121212"
GRAY = "#545454"
MID_GRAY = "#8A8A8A"
LIGHT_GRAY = "#ECECEC"
WHITE = "#FFFFFF"

FONT_REGULAR = "/System/Library/Fonts/HelveticaNeue.ttc"
FONT_BOLD = "/Library/Fonts/Neue Helvetica Pro OT Family/HelveticaNeueLTPro-Bd.otf"
if not Path(FONT_BOLD).exists():
    FONT_BOLD = FONT_REGULAR


SLIDES: list[dict] = [
    {
        "layout": "standard",
        "kicker": "Project walkthrough",
        "title": "Design System Extractor",
        "claim": "We take a screenshot plus CSS variables and construct a text-based design system.",
        "bullets": [
            "Extract visible layout, type, color, imagery, and component behavior.",
            "Translate local visual evidence into reusable design-system rules.",
        ],
        "file": "slide-01-design-system-extractor.png",
    },
    {
        "layout": "cards4",
        "kicker": "Challenges",
        "title": "Why This Is Hard",
        "cards": [
            (
                "LLMs are not good designers",
                "They default to generic systems unless the inputs preserve taste.",
            ),
            (
                "Simple ingestion loses richness",
                "Naive CSS ingestion or screenshot replication misses design-system detail.",
            ),
            (
                "Neither source is enough alone",
                "Screenshots show expression. Website code supplies facts. Each misses context by itself.",
            ),
            (
                "Small design.md files only scratch the surface",
                "A website expresses brand through image, type, color, graphics, decoration, and interaction.",
            ),
        ],
        "file": "slide-02-challenges.png",
    },
    {
        "layout": "two_cards",
        "kicker": "Opportunity",
        "title": "Why This Matters For Webflow AI",
        "claim": "Richer external brand understanding can help differentiate Webflow's AI offering.",
        "cards": [
            (
                "Import richer brand systems",
                "Bring expressive design systems into Webflow from screenshots, source sites, and external references.",
            ),
            (
                "Build a design-taste engine",
                "Help net-new sites avoid slop and help existing brands explore launches, sub-brands, and new directions.",
            ),
        ],
        "file": "slide-03-opportunity.png",
    },
    {
        "layout": "standard",
        "kicker": "Pipeline principles",
        "title": "Preserve Evidence Before Generating",
        "claim": "The pipeline works by accumulating visual facts, then converting them through explicit contracts.",
        "bullets": [
            "Separate data gathering from synthesis.",
            "Preserve parent-child visual relationships.",
            "Use generation as the final consumer, not the source of truth.",
        ],
        "file": "slide-04-pipeline-principles.png",
    },
    {
        "layout": "standard",
        "kicker": "Actual pipeline",
        "title": "From Screenshot To Design System",
        "claim": "Each step narrows ambiguity before the next model sees the work.",
        "bullets": [
            "Screenshot + CSS variables",
            "Section crops + full-page context",
            "Grounding records + schema/YAML contracts",
            "Text-based design system + generated site/assets",
        ],
        "file": "slide-05-actual-pipeline.png",
    },
    {
        "layout": "standard",
        "kicker": "Data transformation",
        "title": "Why The Data Keeps Changing Shape",
        "claim": "Raw visual evidence is too local; final design-system rules are too abstract. The middle steps carry structure forward.",
        "bullets": [
            "Grounding captures facts without trying to be reusable yet.",
            "Schemas normalize those facts into comparable visual roles.",
            "Design-system synthesis turns roles into reusable Webflow-ready resources.",
        ],
        "file": "slide-06-data-transformations.png",
    },
    {
        "layout": "standard",
        "kicker": "Learning 1",
        "title": "Grounding First",
        "claim": "The first important step is pure data gathering: describe what is visible before deciding what it means.",
        "bullets": [
            "Mechanics beat vibes: spacing, type, surfaces, graphics, and edge behavior.",
            "GPT-5.5 thinking was a game changer for careful visual inspection.",
        ],
        "file": "slide-07-grounding-first.png",
    },
    {
        "layout": "standard",
        "kicker": "Learning 2",
        "title": "Crops Provide Fidelity",
        "claim": "Section crops give the model smaller context and higher local fidelity.",
        "bullets": [
            "They expose local surfaces, component recipes, type hierarchy, and image treatment.",
            "They reduce the chance that the model compresses everything into generic page-level summary.",
        ],
        "file": "slide-08-crops-provide-fidelity.png",
    },
    {
        "layout": "standard",
        "kicker": "Learning 3",
        "title": "Local And Global Context Both Matter",
        "claim": "Crops provide local grounding; the full-page screenshot preserves global surface rules.",
        "bullets": [
            "Full-page context captures section color rhythm and grouped background runs.",
            "It also helps with container sizing, section transitions, and page-level hierarchy.",
        ],
        "file": "slide-09-local-global-context.png",
    },
    {
        "layout": "standard",
        "kicker": "Learning 4",
        "title": "Flexible But Rigid Schema",
        "claim": "A schema that visually attributes elements into a stable structure improved downstream conversion.",
        "bullets": [
            "Flexible enough for many site styles.",
            "Rigid enough to keep surfaces, controls, media, text, dividers, and effects comparable.",
        ],
        "file": "slide-10-schema.png",
    },
    {
        "layout": "standard",
        "kicker": "Learning 5",
        "title": "Surface > Child Relationships",
        "claim": "A proper design system needs to know which components live on which surfaces.",
        "bullets": [
            "Flat tokens lose crucial context.",
            "YAML was a strong format for preserving nested host-surface and child-component facts.",
        ],
        "file": "slide-11-surface-child-relationships.png",
    },
    {
        "layout": "standard",
        "kicker": "Learning 6",
        "title": "Evals Gave Signal, Bugs Drove Gains",
        "claim": "Critique and repair loops helped measure quality, but the biggest gains came from digging into each failure.",
        "bullets": [
            "Evals identified where abstraction or fidelity broke.",
            "Core improvements came from fixing pipeline bugs and sharpening instructions.",
        ],
        "file": "slide-12-evals-and-bugs.png",
    },
    {
        "layout": "standard",
        "kicker": "Learning 7",
        "title": "Image References Beat Words",
        "claim": "Source image references plus gpt-image-2 captured creative direction much better than text description alone.",
        "bullets": [
            "References preserved visual style, composition, and media edge behavior.",
            "Text-only prompts were more likely to become generic placeholders.",
        ],
        "file": "slide-13-image-references.png",
    },
    {
        "layout": "standard",
        "kicker": "Next steps",
        "title": "Turn Experiments Into Resources",
        "claim": "Keep iterating, optimize the expensive parts, then build reusable design-system resources.",
        "bullets": [
            "Test more sites, improve schemas, and remove unnecessary steps.",
            "Optimize for speed and cost because thinking-model runs are expensive.",
            "Split extracted systems into resources that can power bespoke, good-looking site generation.",
        ],
        "file": "slide-14-next-steps.png",
    },
]


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REGULAR, size=size)


def text_width(draw: ImageDraw.ImageDraw, text: str, typeface: ImageFont.FreeTypeFont) -> int:
    box = draw.textbbox((0, 0), text, font=typeface)
    return box[2] - box[0]


def wrap_text(draw: ImageDraw.ImageDraw, text: str, typeface: ImageFont.FreeTypeFont, width: int) -> str:
    lines: list[str] = []
    current: list[str] = []
    for word in text.split():
        trial = " ".join(current + [word])
        if text_width(draw, trial, typeface) <= width or not current:
            current.append(word)
        else:
            lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))
    return "\n".join(lines)


def rounded_rect(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], radius: int, fill: str, outline: str | None = None, width: int = 1) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def bullet_list(draw: ImageDraw.ImageDraw, bullets: list[str], x: int, y: int, width: int, typeface: ImageFont.FreeTypeFont) -> int:
    for bullet in bullets:
        wrapped = wrap_text(draw, bullet, typeface, width - 38)
        draw.ellipse((x, y + 12, x + 11, y + 23), fill=BLUE)
        draw.text((x + 34, y), wrapped, fill=BLACK, font=typeface, spacing=8)
        y += (wrapped.count("\n") + 1) * 36 + 22
    return y


def draw_small_illustration(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], variant: int) -> None:
    x1, y1, x2, y2 = box
    rounded_rect(draw, box, 14, CHARCOAL, "#2A2A2A", 2)
    cx = (x1 + x2) // 2
    cy = (y1 + y2) // 2
    if variant == 0:
        for i in range(3):
            draw.rounded_rectangle((x1 + 32, y1 + 34 + i * 34, x2 - 32, y1 + 52 + i * 34), radius=5, fill="#393939")
        draw.rectangle((x1 + 32, y2 - 46, x1 + 96, y2 - 24), fill=BLUE)
    elif variant == 1:
        for i in range(5):
            draw.line((x1 + 35, y1 + 35 + i * 22, x2 - 35, y1 + 70 + i * 8), fill="#575757", width=2)
        draw.rectangle((cx - 18, cy - 18, cx + 18, cy + 18), fill=BLUE)
    elif variant == 2:
        draw.rectangle((x1 + 36, y1 + 36, cx - 12, y2 - 36), outline="#575757", width=3)
        draw.rectangle((cx + 12, y1 + 36, x2 - 36, y2 - 36), outline=BLUE, width=3)
        draw.line((cx - 12, cy, cx + 12, cy), fill=WHITE, width=3)
    else:
        for i in range(4):
            draw.rectangle((x1 + 38, y1 + 36 + i * 24, x2 - 38, y1 + 46 + i * 24), fill="#555555")
        draw.line((x1 + 38, y2 - 40, x2 - 38, y2 - 40), fill=BLUE, width=4)


def draw_standard(draw: ImageDraw.ImageDraw, spec: dict, index: int) -> None:
    panel_w = 870
    draw.rectangle((0, 0, panel_w, H), fill=WHITE)
    draw.rectangle((panel_w, 0, panel_w + 2, H), fill="#D7D7D7")
    draw.rectangle((96, 94, 188, 102), fill=BLUE)

    kicker_font = font(24, True)
    title_font = font(68, True)
    claim_font = font(33)
    bullet_font = font(25)
    footer_font = font(18, True)

    x = 96
    y = 130
    draw.text((x, y), spec["kicker"].upper(), fill=BLUE, font=kicker_font)
    y += 68
    title = wrap_text(draw, spec["title"], title_font, 650)
    draw.text((x, y), title, fill=BLACK, font=title_font, spacing=6)
    y += (title.count("\n") + 1) * 78 + 36
    claim = wrap_text(draw, spec["claim"], claim_font, 645)
    draw.text((x, y), claim, fill=BLACK, font=claim_font, spacing=10)
    y += (claim.count("\n") + 1) * 46 + 40
    draw.line((x, y, x + 600, y), fill=LIGHT_GRAY, width=2)
    y += 32
    bullet_list(draw, spec.get("bullets", []), x, y, 620, bullet_font)

    draw.text((x, H - 96), f"{index:02d} / {len(SLIDES):02d}", fill=BLACK, font=footer_font)
    draw.text((x + 132, H - 96), "Design System Extractor", fill=GRAY, font=footer_font)


def draw_cards4(draw: ImageDraw.ImageDraw, spec: dict, index: int) -> None:
    draw.rectangle((0, 0, W, H), fill=(8, 8, 8, 120))
    x = 96
    y = 84
    draw.rectangle((x, y, x + 92, y + 8), fill=BLUE)
    draw.text((x, y + 38), spec["kicker"].upper(), fill=BLUE, font=font(24, True))
    draw.text((x, y + 90), spec["title"], fill=WHITE, font=font(72, True))

    card_w = 900
    card_h = 330
    gap = 44
    start_y = 300
    for i, (heading, body) in enumerate(spec["cards"]):
        col = i % 2
        row = i // 2
        cx = 96 + col * (card_w + gap)
        cy = start_y + row * (card_h + gap)
        rounded_rect(draw, (cx, cy, cx + card_w, cy + card_h), 22, WHITE, "#DDDDDD", 2)
        draw_small_illustration(draw, (cx + 34, cy + 38, cx + 244, cy + 198), i)
        draw.text((cx + 282, cy + 44), wrap_text(draw, heading, font(39, True), 520), fill=BLACK, font=font(39, True), spacing=4)
        draw.text((cx + 282, cy + 142), wrap_text(draw, body, font(26), 510), fill=GRAY, font=font(26), spacing=8)

    draw.text((96, H - 76), f"{index:02d} / {len(SLIDES):02d}", fill=WHITE, font=font(18, True))
    draw.text((228, H - 76), "Design System Extractor", fill="#BEBEBE", font=font(18, True))


def draw_two_cards(draw: ImageDraw.ImageDraw, spec: dict, index: int) -> None:
    draw.rectangle((0, 0, W, H), fill=(8, 8, 8, 105))
    x = 96
    y = 84
    draw.rectangle((x, y, x + 92, y + 8), fill=BLUE)
    draw.text((x, y + 38), spec["kicker"].upper(), fill=BLUE, font=font(24, True))
    draw.text((x, y + 90), wrap_text(draw, spec["title"], font(70, True), 1040), fill=WHITE, font=font(70, True), spacing=6)
    draw.text((x, y + 260), wrap_text(draw, spec["claim"], font(31), 860), fill="#DCDCDC", font=font(31), spacing=8)

    card_w = 880
    card_h = 390
    start_y = 610
    for i, (heading, body) in enumerate(spec["cards"]):
        cx = 96 + i * (card_w + 80)
        cy = start_y
        rounded_rect(draw, (cx, cy, cx + card_w, cy + card_h), 24, WHITE, "#E2E2E2", 2)
        draw_small_illustration(draw, (cx + 40, cy + 48, cx + 270, cy + 250), i + 1)
        draw.text((cx + 310, cy + 58), wrap_text(draw, heading, font(43, True), 500), fill=BLACK, font=font(43, True), spacing=5)
        draw.text((cx + 310, cy + 178), wrap_text(draw, body, font(27), 500), fill=GRAY, font=font(27), spacing=8)

    draw.text((96, H - 76), f"{index:02d} / {len(SLIDES):02d}", fill=WHITE, font=font(18, True))
    draw.text((228, H - 76), "Design System Extractor", fill="#BEBEBE", font=font(18, True))


def compose_one(index: int, spec: dict) -> Path:
    raw_path = RAW_DIR / f"visual-{index:02d}.png"
    if not raw_path.exists():
        raise FileNotFoundError(raw_path)

    base = Image.open(raw_path).convert("RGB").resize((W, H), Image.Resampling.LANCZOS)
    # Darken the generated visual so it reads as background, not competing content.
    shade = Image.new("RGB", (W, H), BLACK)
    base = Image.blend(base, shade, 0.18)

    overlay = Image.new("RGBA", (W, H), (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)
    layout = spec.get("layout", "standard")
    if layout == "cards4":
        draw_cards4(draw, spec, index)
    elif layout == "two_cards":
        draw_two_cards(draw, spec, index)
    else:
        draw_standard(draw, spec, index)

    out = Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")
    out_path = OUT_DIR / spec["file"]
    out.save(out_path, quality=96)
    return out_path


def make_contact_sheet(paths: list[Path]) -> Path:
    thumb_w, thumb_h = 480, 270
    cols = 4
    rows = (len(paths) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * thumb_w + (cols + 1) * 24, rows * thumb_h + (rows + 1) * 24), "#EDEDED")
    for i, path in enumerate(paths):
        thumb = Image.open(path).convert("RGB")
        thumb.thumbnail((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        canvas = Image.new("RGB", (thumb_w, thumb_h), WHITE)
        canvas.paste(thumb, ((thumb_w - thumb.width) // 2, (thumb_h - thumb.height) // 2))
        col = i % cols
        row = i // cols
        sheet.paste(canvas, (24 + col * (thumb_w + 24), 24 + row * (thumb_h + 24)))
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
