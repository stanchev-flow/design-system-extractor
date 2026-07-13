#!/usr/bin/env python3
"""
Pipeline: Screenshot → Design System → Generated Websites

Runs the full pipeline on all test screenshots, saves versioned results,
and generates a self-contained viewer HTML.

Usage:
    python run_pipeline.py                  # auto-increment version
    python run_pipeline.py --version v003   # specific version
    python run_pipeline.py --screenshots-dir /path/to/screenshots
"""

import argparse
import base64
import concurrent.futures
import difflib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from io import BytesIO
from pathlib import Path

import yaml
from bs4 import BeautifulSoup, Tag
from PIL import Image

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from screenshot_to_template.config import load_config, AppConfig
from screenshot_to_template.models.google import GoogleProvider
from screenshot_to_template.models.anthropic import AnthropicProvider
from screenshot_to_template.models.openai import OpenAIProvider
from screenshot_to_template.models import get_provider
from screenshot_to_template.output import clean_markdown
from screenshot_to_template.pipeline.single_shot import load_and_encode_image, build_single_shot_views
from screenshot_to_template.pipeline.grounding_by_section import run as run_grounding_by_section
from screenshot_to_template.site_assets import ASSET_BRIEF_ATTRIBUTE, apply_generated_site_assets
from screenshot_to_template.brand_assets import apply_brand_assets_file
from screenshot_to_template.source_colors import (
    append_source_font_implementation,
    apply_document_color_replacements,
    extract_document_color_literals,
    extract_source_colors,
    find_non_source_document_colors,
    find_non_source_document_font_families,
    find_source_html_for_screenshot,
    render_source_color_report,
    suggest_nearest_source_color_replacements,
    write_source_color_artifacts,
)
from screenshot_to_template.source_style_ledger import (
    audit_document_styles,
    build_source_style_ledger,
    reconcile_document_styles,
    source_style_ledger_prompt_block,
    write_source_style_ledger_artifact,
    write_style_audit,
)
from screenshot_to_template.surface_contract import (
    build_surface_component_contract,
    contract_audit_passed,
    render_surface_component_contract_for_prompt,
    write_surface_component_contract_artifacts,
)
from screenshot_to_template.tracking import token_usage_context, update_step_status
from screenshot_to_template.framework_generator import (
    DEFAULT_FRAMEWORK_PROMPT_PATH,
    generate_framework_site,
    load_framework_prompt,
)


SCREENSHOTS_DIR = Path(__file__).parent / "screenshots" / "best" / "use for testing"
RUNS_DIR = Path(__file__).parent / "runs"
PROJECT_DIR = Path(__file__).parent
PROJECT_SKILLS_DIR = PROJECT_DIR / "skills"

WEBSITE_GEN_PROMPT = """\
You are an expert frontend developer. You will be given a text-based design system extracted from a website screenshot. Your job is to generate a complete, single-file HTML website that feels native to this design system.

Requirements:
- Output a SINGLE complete HTML file with all CSS inlined in a <style> tag
- If the design system includes YAML front matter tokens, treat those tokens as the normative source of truth and treat the markdown body as rationale and usage guidance
- Use the design system's structural system, layout grammar, surface families, typography system, shape/depth system, and component rules
- If the design system or grounding includes a "Source Font Implementation" section or source `@font-face` CSS, include that CSS in the generated page, but apply typography by the design-system role tokens first. Do not let one broad source font stack override role-specific font families, heading consistency rules, or text-size normalization in the design system.
- When source font files are provided, do not substitute Google Fonts or a generic font family for the primary typography
- Treat the design system as a reusable system, not as a screenshot reconstruction
- Create a realistic, professional-looking landing page with placeholder content that matches the described system
- The page should have a navigation bar, a footer, and enough content sections to reflect the described page rhythm and module density
- Prefer roughly 6-9 sections when the design system describes a long or highly sectional page
- Each section should feel like it belongs to the same system while still being a fresh composition
- Do not copy the source screenshot's exact section list, exact section order, or exact component positions. Use only recurring layout tendencies and surface grammar from the design system unless an explicit separate layouts artifact is intentionally supplied for source reconstruction.
- Vary section composition within the design system: reuse broad scaffolds such as centered intro stacks, two-column splits, wide rails, card rails, inset panels, and selector rows, but do not reproduce the original page as a one-to-one sequence.
- Preserve the dominant container behavior, spacing rhythm, alignment discipline, and layout tension from the design system
- Preserve recurring section-group behavior, long surface runs, and inset-panel patterns rather than collapsing everything into isolated generic sections
- Preserve grounded surface-run continuity: when adjacent modules are described as sharing one parent canvas, keep that parent canvas continuous and place contrasting, tinted, or neutral fills only on child modules that are explicitly described as inset/foreground. If the grounding or design system defines a full-width gray, tinted, dark, or otherwise distinct section reset, preserve that reset.
- For tonal gradients between a white/light canvas and a tinted run, start the gradient from the previous canvas color, usually white or near-white, before easing into the tint. Do not begin the gradient from a saturated tint when the source transition is described as white-to-tint.
- Use the component base recipes consistently
- When a component has contextual variants by surface family, only use the listed variants that fit the chosen surface
- Preserve compact icon-only/circular action recipes when the design system defines them. If a card, tile, carousel, nav, or footer pattern calls for a circle with an arrow/icon inside, render the circle control itself rather than replacing it with a loose arrow glyph or text-only link.
- Do not invent a stronger or brighter secondary button style than the primary on the same surface
- Only use secondary, ghost, tertiary, or text-button variants when they are explicitly defined in the design system
- If the design system says the button hierarchy is `single-primary-button pattern`, do not invent a filled secondary button; use either one primary CTA plus a text link, or the explicitly defined low-emphasis secondary treatment
- If the design system marks a secondary button as `derived`, keep it lower emphasis than the primary using ghost, low-opacity fill, subtle tonal fill, or dim border logic from the same surface family
- Preserve component sizing behavior. Foreground images, image placeholders, logos, icons, buttons, CTA pills, eyebrows, badges, tags, chips, text links, and compact metadata labels should size intrinsically or to an explicit bounded media frame; they should never become full-width just because their parent container is full-width.
- Implement content-hugging controls with CSS that defeats parent stretch, especially inside column flex stacks where `align-items: stretch` is the default. Use `display: inline-flex`, `width: max-content` or `fit-content`, `max-width: 100%`, `white-space: nowrap`, `flex: 0 0 auto`, plus `align-self` and `justify-self` that match the intended alignment. Do not rely on `inline-flex` and `width:auto` alone, because those can still stretch inside flex-column parents.
- If an older design system says `width:auto` in a `cssSizingHint` for a content-hugging button, eyebrow, badge, chip, pill, tag, CTA, or metadata label, treat that as incomplete legacy shorthand. Implement the control with `width: max-content` or `width: fit-content` plus explicit non-stretch alignment instead.
- Treat `width: 100%` on foreground images, logos, eyebrows, badges, tags, chips, text links, compact labels, or ordinary buttons as a mistake unless the element is filling a deliberately sized media frame that is itself the bounded object. Size the frame deliberately, then let the image fill that frame; do not let the image or compact text element span the entire card, column, or section by default.
- For content stacks that contain compact controls, either set the parent stack alignment to the intended non-stretch alignment (for example `align-items: flex-start` or `align-items: center`) or set explicit `align-self` on each compact control.
- Do not put one global `align-self:flex-start` on all compact labels or pills. A compact control inside a centered intro/CTA stack must center with that stack; a compact control inside a left-aligned stack may align start. Alignment is contextual even when sizing is shared.
- Do not use `display: block`, `width: 100%`, `justify-self: stretch`, parent `align-items: stretch`, or implicit flex-column stretch on pill-like buttons, eyebrows, badges, tags, chips, or compact metadata labels unless full-width sizing is explicitly grounded. If mobile wrapping is needed, wrap the text or the control group, not the individual pill width.
- Preserve recurring content stacks such as eyebrow + heading + paragraph + CTA when the design system says they are common
- Keep recurring card families distinct; do not mix many unrelated card background colors unless the design system explicitly supports that
- Treat rare or one-off motifs as optional accents, not mandatory patterns
- Do NOT invent extra component families, extra accent colors, or extra layout tricks that are not supported by the design system
- Make it responsive using CSS Grid/Flexbox
- Use CSS custom properties to reflect the surface tokens and component role tokens described in the design system
- Do not use JavaScript frameworks for app structure. JavaScript is allowed only for GSAP motion from active skills and small plain-JS glue code. Do not use shader, WebGL, Three.js, procedural canvas, or particle systems for generated imagery; create explicit visual placeholders for downstream image generation instead.
- The page should look polished and complete, not like a style guide
- Icons may be implemented as normal inline SVGs when they are simple UI/supporting icons
- For larger graphics, illustrations, decorative visuals, portraits, collages, or photo-like panels, do NOT use stock-photo URLs or final baked imagery; instead output blank image placeholders whose aspect ratio matches the intended layout/context
- Treat large empty visual regions in cards, panels, testimonial media columns, dark-card media headers, hero/background art zones, product/device mockups, certification/seal clusters, and decorative illustration wells as downstream image-generation candidates. Reserve their space with visible layout frames and include explicit placeholders rather than replacing them with flat color fills, CSS-only drawings, inline SVG illustrations, shader/canvas effects, or procedural gradients.
- Use `gpt-image-2` downstream asset generation for these visual regions by exposing them as placeholders with `data-stt-asset-brief`; the HTML generator should not attempt to render final bespoke artwork itself.
- For every non-icon visual placeholder, use an <img> element with a blank data URI or empty inline SVG placeholder source, size it correctly in the layout, keep an accessible plain-language `alt`, and include a `data-stt-asset-brief` attribute that describes what the final generated image should contain and how it should look in terms of subject matter, composition, and design-system style
- The `data-stt-asset-brief` should be concise but specific enough for downstream image generation, for example the content, mood, framing, material/texture, color treatment, and whether it should feel photographic, illustrative, diagrammatic, abstract, or collage-like
- Prefer `<img data-stt-asset-brief="...">` placeholders over CSS `background-image: url(...)` for major generated visuals unless the layout absolutely requires a background-image treatment
- IMPORTANT: Do NOT use viewport units (vh/svh/dvh/vw) anywhere — the output is rendered inside an iframe. Use container-query units (cqw/cqh/cqi) against a `container-type: size` ancestor; the root wrapper must set the container context.
- Keep the CSS concise — avoid overly verbose or redundant styles

Output ONLY the HTML code, no explanations or markdown fences.\
"""

SITE_GEN_MAX_TOKENS = 32768
CHROME_HEADLESS_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
ALLOWED_SITE_GENERATION_PROVIDERS = ("claude", "gpt55")
# Framework-first default: one framework build (Claude). Add gpt55 to site-generation-providers.txt if needed.
DEFAULT_SITE_GENERATION_PROVIDERS = ("claude",)
DISABLED_SITE_GENERATION_PROVIDERS = {"gemini"}
DEFAULT_SITE_GENERATION_SKILLS = ("motion-design-gsap",)
DISABLED_SITE_GENERATION_SKILLS = {"shader-effects", "abstract-three-webgl", "threejs", "three-js"}
SITE_MATCH_SCORE_WEIGHTS = {
    "color_token_fidelity": 0.20,
    "section_surface_patterns": 0.20,
    "layout_pattern_fidelity": 0.15,
    "component_recipe_fidelity": 0.20,
    "typography_pattern_fidelity": 0.15,
    "imagery_graphics_fidelity": 0.10,
}
SURFACE_COMPONENT_MAP_SCORE_WEIGHTS = {
    "surface_inventory": 0.18,
    "nested_element_pairings": 0.22,
    "critical_color_pairings": 0.24,
    "typography_and_casing": 0.12,
    "background_depth_graphics": 0.12,
    "actionability_and_constraints": 0.12,
}
DESIGN_SYSTEM_CONVERSION_SCORE_WEIGHTS = {
    "factual_pairing_preservation": 0.28,
    "surface_specificity": 0.20,
    "component_recipe_translation": 0.20,
    "typography_and_casing": 0.10,
    "constraints_and_exceptions": 0.10,
    "unsupported_overgeneralization": 0.12,
}
DESIGN_SYSTEM_REVIEW_MAX_WORKERS = 8

DEFAULT_COLOR_SYNC_PROMPT = """\
You are correcting color values in a design-system markdown file using source-of-truth CSS colors extracted from the original HTML plus screenshot grounding when provided.

Rules:
- Preserve the existing section order, headings, bullets, and non-color wording as closely as possible.
- Preserve local component-on-surface color pairings from the screenshot grounding. A component recipe on a specific host surface must not be remapped to a global accent just because that accent appears more often in source CSS.
- Use the source CSS color report as authoritative for exact hex, rgba, and gradient values when it contains a visually close match for the grounded color role.
- If the source CSS report does not contain a visually close match for a grounded component color, keep or restore the screenshot-grounded color value instead of forcing a distant source color.
- Preserve source-backed font-family, font-size, font-weight, line-height, letter-spacing, and downloaded font implementation details when they are present in the document or source report.
- Focus on correcting explicit color values, especially in `## Color Tokens`.
- If an exact explicit value in the markdown does not appear in the source report or screenshot grounding, replace it with a source value, a grounded screenshot value, or rewrite that wording so it no longer contains an unsupported explicit color value.
- Do not invent colors that appear in neither the source report nor the screenshot grounding.
- Return the full corrected markdown document.
"""

DEFAULT_GROUNDING_SYNC_PROMPT = """\
You are correcting a structural grounding markdown file using source-of-truth CSS styles extracted from the original HTML.

Rules:
- Preserve the exact document structure, section order, headings, bullets, and overall wording as closely as possible.
- The grounding file should remain a faithful text copy of the screenshot, not a rewritten design system.
- Use the source CSS style report as authoritative for exact color values and for exact typography values when the grounding mentions font family, font size, font weight, line height, or letter spacing.
- Replace approximate explicit color values with source-supported values whenever a clear match exists.
- Replace approximate typography values with source-supported values whenever a clear match exists.
- If the source report does not support an exact explicit value, prefer semantic wording over invented precision.
- Do not invent colors or typography values that do not appear in the source report.
- Return the full corrected grounding markdown document.
"""

DEFAULT_SURFACE_COMPONENT_MAP_PROMPT = """\
You are a design-system grounding compiler. Convert merged structural grounding plus detailed section grounding into a factual surface/component map.

Your output is an intermediate implementation reference, not a final design system. It must preserve local facts that are easy to lose during synthesis.

## Input

You may receive:
- merged structural grounding
- detailed per-section grounding
- source CSS style report

## Core Rules

- Base the map only on grounded evidence and source-supported values.
- Preserve exact or approximate visible values for surface backgrounds, heading text, body text, buttons, compact labels, cards, borders, shadows, dividers, gradients, imagery slots, and graphic accents.
- Treat surface/component pairing as the primary fact. A button color observed on one host surface must not become the default button color for a different host surface unless the grounding shows that pairing there too.
- Distinguish parent surfaces from child cards, panels, trays, buttons, labels, media frames, and nested UI.
- Do not invent section-specific token names. Use reusable generic surface names such as `primary`, `secondary`, `tertiary`, `inverse`, `inverseStrong`, `accentSurface`, `raisedLight`, or `insetDark` only when the role is justified.
- If a surface appears only once, still record its factual pairings, but mark `frequency: one-off`.
- If two similar colors serve different roles, keep them separate in the map and explain the role split.
- If two different components share a color but sit on different host surfaces, record them separately.
- Preserve typography casing facts. If headings or labels are all-caps/uppercase in the grounding, record `textTransform: uppercase`.
- Preserve heading color by host surface. Do not reduce a colored heading to a generic accent-span rule when the full heading is grounded in that color.
- Preserve body text color by host surface, including muted paragraph colors that differ from headings or accents.
- Preserve critical color pairings for host surface, heading text, body text, primary/secondary buttons, compact labels/eyebrows, cards, borders, shadows, and dividers.
- Use source CSS values when they are visually close to the grounded role. If the source report lacks a close match, keep the grounded screenshot value and mark it as `groundedApprox`.
- Do not choose globally common source colors over locally grounded component pairings.

## Output Format

Return markdown with this exact structure:

# Surface Component Map

## Surface Inventory

For each reusable or one-off host surface:

### [generic-surface-role]
- `frequency`: dominant | common | occasional | rare | one-off
- `observedBackgrounds`: [hex/rgb/gradient values or semantic values]
- `sourceBackedValues`: [values when available]
- `role`: [page canvas, section band, inset shell, card host, inverse run, etc.]
- `gradient`: [type, stops, focal area, softness, fade behavior, or `none observed`]
- `defaultHeading`: { color, typographyRole, textTransform, evidence }
- `accentedHeading`: { color, usage, evidence } or `none observed`
- `bodyText`: { color, mutedColor, evidence }
- `compactLabels`: [surface-specific eyebrow/badge/tag recipes with fill, text, border, textTransform, width behavior]
- `primaryButton`: { fill, text, border, shadow, widthBehavior, evidence } or `none observed`
- `secondaryButton`: { fill, text, border, shadow, widthBehavior, evidence } or `none observed`
- `cards`: [child card/panel recipes with fill, text, border, shadow, radius, separation mechanism]
- `dividersBordersShadows`: [values and where they apply]
- `imageGraphicSlots`: [raster/image/illustration/diagram direction and host relationship]
- `doNotGeneralize`: [pairings from this surface that must not be reused on other surfaces without evidence]

## Critical Color Pairings

List factual pairings as bullets in this form:
- `[host surface]` -> `[element role]`: background/fill `[value]`, text `[value]`, border/shadow `[value or none]`, evidence `[section/source reference]`

## Ambiguities

- [unclear or conflicting facts, including when source CSS and screenshot grounding disagree]
"""

DEFAULT_SITE_STYLE_SYNC_PROMPT = """\
You are correcting a generated single-file HTML document so its explicit visual values match the source-of-truth CSS styles and the provided markdown artifact.

Rules:
- Preserve the existing HTML structure, content, and layout as closely as possible.
- Focus on correcting explicit CSS values: colors, gradients, font-family, font-size, font-weight, line-height, and letter-spacing.
- Use the source CSS style report as authoritative for exact explicit values.
- If the provided markdown artifact includes an explicit exact value and that value is supported by the source CSS style report, prefer it.
- If the source CSS style report includes downloaded font assets or Source Font Implementation CSS, include those `@font-face` rules, but apply typography by the design-system role tokens first. Do not let one broad source font stack override role-specific font families, heading consistency rules, or text-size normalization in the design system.
- Do not invent new hex/rgb/rgba/hsl colors, gradients, or font-family stacks.
- Do not introduce approximate alpha variants or blended shades that are not supported by the source CSS style report.
- If an explicit visual value is unsupported, replace it with the closest supported explicit value from the design-system markdown or source CSS style report.
- Preserve grounded component width behavior while correcting visual values. For content-hugging buttons, CTA pills, eyebrows, badges, tags, chips, or compact metadata labels, do not leave sizing dependent on `width:auto` inside flex/grid stacks; use `width:max-content` or `fit-content`, `max-width:100%`, `flex:0 0 auto`, and explicit non-stretch alignment when needed.
- If the existing HTML or markdown uses `width:auto` as the only content-hugging sizing hint for compact controls, treat it as insufficient and upgrade it rather than preserving it literally.
- Keep the output as a single complete HTML document with inline CSS.
- Return ONLY the corrected HTML.
"""

DEFAULT_SITE_REVIEW_PROMPT = """\
You are evaluating how well a generated website screenshot expresses the stylistic patterns described in a grounding markdown file.

You will receive:
- A grounding markdown file describing the website's reusable stylistic patterns
- One image: a screenshot rendered from the generated HTML

Do NOT grade based on exact section-by-section layout matching or whether the page copied the original screenshot.
Do grade based on whether the generated page visibly expresses the grounding's design-system patterns.

## Scoring dimensions

Use a 0-10 score for each dimension:
- `color_token_fidelity`: whether the generated page appears to use the grounding's generic color roles and contrast relationships correctly
- `section_surface_patterns`: whether section backgrounds, section transitions, surface alternation, and wrapper/background behaviors match the grounding's patterns
- `layout_pattern_fidelity`: whether broad layout tendencies match the grounding, such as frequent left-vs-center alignment, density, container behavior, and common content organization patterns
- `component_recipe_fidelity`: whether recurring components like buttons, eyebrows, badges, chips, cards, tabs, dividers, nav, and footer visibly follow the grounding's component styling rules, including whether controls preserve grounded content-hugging, fixed-size, icon-only, or full-width sizing behavior
- `typography_pattern_fidelity`: whether heading/body/ui text hierarchy, casing, weight, spacing, and overall typographic character match the grounding
- `imagery_graphics_fidelity`: whether photography, illustrations, graphics, textures, and decorative motifs match the grounding's stylistic direction

## Rules

- Be strict. A pleasant page that misses the grounding's stylistic patterns should not score highly.
- Penalize full-card or full-column buttons, eyebrows, badges, tags, chips, or metadata labels when the grounding describes compact/content-hugging controls.
- Ignore business content, exact copy, and exact section order.
- Ignore whether the generated page copies the original screenshot layout.
- Penalize generic simplifications that flatten distinctive patterns called out in the grounding.
- Reward pages that feel stylistically faithful while still being fresh compositions.
- Keep notes concrete and implementation-oriented.
- Return JSON only, with no markdown fences.

Use this exact shape:

{
  "summary": "short overall summary",
  "scores": {
    "color_token_fidelity": {"score": 0, "notes": "short note"},
    "section_surface_patterns": {"score": 0, "notes": "short note"},
    "layout_pattern_fidelity": {"score": 0, "notes": "short note"},
    "component_recipe_fidelity": {"score": 0, "notes": "short note"},
    "typography_pattern_fidelity": {"score": 0, "notes": "short note"},
    "imagery_graphics_fidelity": {"score": 0, "notes": "short note"}
  },
  "strengths": ["bullet", "bullet"],
  "major_mismatches": ["bullet", "bullet"],
  "verdict": "short verdict"
}
"""

DEFAULT_DESIGN_SYSTEM_REVIEW_PROMPT = """\
You are one review agent in a parallel design-system audit.

You will receive:
- One original source screenshot
- One focused section from the final design-system markdown
- Optional YAML front matter from the same design-system markdown as shared token context

Your job is to score how well this focused design-system section emulates the screenshot's reusable visual system. Evaluate the markdown section itself, not a generated website and not exact page reconstruction.

## Scoring

Use a strict 0-10 score:
- 10: the section captures the screenshot's reusable patterns with precise, implementation-useful rules
- 7-9: strong fit with small omissions or mild overgeneralization
- 4-6: partially useful, but important screenshot patterns are missing, vague, or unsupported
- 1-3: mostly generic, misleading, or weakly grounded in the screenshot
- 0: absent or unrelated

## Rules

- Focus only on the named design-system section. Use the YAML context only when it helps interpret tokens referenced by that section.
- Compare against the screenshot directly.
- Do not reward vague design prose unless it would help a generator reproduce the screenshot's visual system.
- Penalize unsupported exact values, section-specific role names, palette-specific general rules, or rules that would fail on a different site.
- Reward generic reusable roles and mechanics that faithfully encode the screenshot, such as surface relationships, hierarchy, nesting, contrast, component sizing behavior, typography rhythm, and layout grammar.
- Keep findings concrete and implementation-oriented.
- Return JSON only, with no markdown fences.

Use this exact shape:

{
  "summary": "short focused summary",
  "score": 0,
  "confidence": 0,
  "accurate_patterns": ["bullet", "bullet"],
  "missing_or_weak_patterns": ["bullet", "bullet"],
  "overfit_or_unsupported_rules": ["bullet", "bullet"],
  "actionable_learnings": ["bullet", "bullet"],
  "verdict": "short verdict"
}
"""

DEFAULT_SURFACE_COMPONENT_MAP_REVIEW_PROMPT = """\
You are evaluating how well a surface-component map preserves factual visual relationships from a source website screenshot and its section grounding.

You will receive:
- One original source screenshot
- A compacted section-grounding reference
- One `surface-component-map.md`

Evaluate the map itself, not the final design system and not a generated website.

## Scoring

Use strict 0-10 scores for each dimension:
- `surface_inventory`: whether the map identifies the real host surfaces, section bands, inverse/light/tinted runs, gradients, and parent surfaces without collapsing unrelated surfaces.
- `nested_element_pairings`: whether the map preserves child elements on each host surface: headings, body text, buttons, compact labels, cards, panels, borders, dividers, shadows/glows, media/graphics.
- `critical_color_pairings`: whether the map captures accurate approximate/source-backed colors for host surface, heading text, body text, primary/secondary buttons, compact labels, cards, borders, dividers, and shadows.
- `typography_and_casing`: whether text roles include useful heading/body/label distinctions, casing, emphasis, and host-surface text-color behavior.
- `background_depth_graphics`: whether gradients, image/graphic slots, decorative motifs, shadows, glows, masks, and edge behavior are represented with enough implementation detail.
- `actionability_and_constraints`: whether the map is normalized enough for design-system synthesis, avoids noisy irrelevant evidence, and includes useful `doNotGeneralize` / ambiguity constraints.

## Rules

- Be strict. A noisy evidence dump with the right words but unclear role grouping should not score highly.
- Reward factual completeness and correct host-surface grouping more than polished prose.
- Penalize maps that collapse all evidence into one section, merge distinct surfaces, omit body/heading/button/card color relationships, or fail to separate parent surfaces from child cards/panels.
- Penalize page-specific names only when they prevent generic synthesis; section-local evidence labels are acceptable if the factual pairings remain clear.
- Ignore whether the map already has final token names. It is an intermediate grounding artifact.
- Return JSON only, with no markdown fences.

Use this exact shape:

{
  "summary": "short overall summary",
  "scores": {
    "surface_inventory": {"score": 0, "notes": "short note"},
    "nested_element_pairings": {"score": 0, "notes": "short note"},
    "critical_color_pairings": {"score": 0, "notes": "short note"},
    "typography_and_casing": {"score": 0, "notes": "short note"},
    "background_depth_graphics": {"score": 0, "notes": "short note"},
    "actionability_and_constraints": {"score": 0, "notes": "short note"}
  },
  "strengths": ["bullet", "bullet"],
  "major_mismatches": ["bullet", "bullet"],
  "actionable_learnings": ["bullet", "bullet"],
  "verdict": "short verdict"
}
"""

DEFAULT_DESIGN_SYSTEM_CONVERSION_REVIEW_PROMPT = """\
You are evaluating design-system conversion loss.

You will receive:
- One `surface-component-map.md`
- One `design-system.md`

No screenshot is available. Treat the surface-component map as the factual source of truth. Evaluate whether the design system preserved, translated, merged, distorted, omitted, or overgeneralized the map's factual host-surface and nested-component pairings.

## Scoring

Use strict 0-10 scores for each dimension:
- `factual_pairing_preservation`: whether the design system preserves critical pairings for host surface, heading text, body text, primary/secondary buttons, compact labels, cards/panels, borders, dividers, shadows, gradients, and image/graphic slots.
- `surface_specificity`: whether surface-specific recipes remain tied to their host surface roles instead of becoming generic global accent/default rules.
- `component_recipe_translation`: whether map facts become reusable implementation recipes, tokens, variants, or rules with enough detail to drive generation.
- `typography_and_casing`: whether heading/body/label hierarchy, host-specific text color, casing such as `textTransform: uppercase`, and emphasis rules are preserved.
- `constraints_and_exceptions`: whether `doNotGeneralize`, one-off/rare facts, ambiguity notes, and source-vs-grounded confidence boundaries are carried forward as useful constraints.
- `unsupported_overgeneralization`: whether the design system avoids inventing unsupported colors, surfaces, cards, buttons, section-specific token names, or broad rules that the map does not support.

## Rules

- Be strict. A polished design system that loses map-specific pairings should score poorly.
- Reward faithful translation into generic reusable roles, not verbatim copying.
- Penalize omitted factual pairings even if the design system looks internally consistent.
- Penalize merging distinct map surfaces when that would change component colors or contrast behavior.
- Penalize overgeneralizing a one-off pairing into a global default.
- Penalize section/content-specific token names, but do not penalize section-local evidence notes if they preserve the factual relationship.
- Do not ask for screenshot evidence. The map is the only factual reference for this review.
- Keep notes concrete enough to guide the next design-system synthesis prompt.
- Return JSON only, with no markdown fences.

Use this exact shape:

{
  "summary": "short overall summary",
  "scores": {
    "factual_pairing_preservation": {"score": 0, "notes": "short note"},
    "surface_specificity": {"score": 0, "notes": "short note"},
    "component_recipe_translation": {"score": 0, "notes": "short note"},
    "typography_and_casing": {"score": 0, "notes": "short note"},
    "constraints_and_exceptions": {"score": 0, "notes": "short note"},
    "unsupported_overgeneralization": {"score": 0, "notes": "short note"}
  },
  "preserved_pairings": ["bullet", "bullet"],
  "conversion_losses": ["bullet", "bullet"],
  "distortions_or_overgeneralizations": ["bullet", "bullet"],
  "actionable_learnings": ["bullet", "bullet"],
  "verdict": "short verdict"
}
"""

RUN_OUTPUT_LABEL_PATTERN = re.compile(r"\s+\((Full|Grounding|DS)\)$")


def get_next_version() -> str:
    """Determine the next version number based on existing runs."""
    if not RUNS_DIR.exists():
        return "v001"
    existing = sorted([
        d.name for d in RUNS_DIR.iterdir()
        if d.is_dir() and d.name.startswith("v") and d.name[1:].isdigit()
    ])
    if not existing:
        return "v001"
    last_num = int(existing[-1][1:])
    return f"v{last_num + 1:03d}"


def load_api_keys():
    """Load API keys from repo-local .env.local if not already set."""
    env_file = PROJECT_DIR / ".env.local"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip()
                    if key in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY"):
                        if not os.environ.get(key):
                            os.environ[key] = value
    if not os.environ.get("GOOGLE_API_KEY") and os.environ.get("GEMINI_API_KEY"):
        os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]


def generate_design_system(
    screenshot_path: str,
    config: AppConfig,
    mode: str = "single",
    system_prompt: str | None = None,
    output_dir: str | None = None,
) -> str:
    """Generate a design system from a screenshot using the active single pipeline."""
    if system_prompt:
        config = AppConfig(**{**vars(config), "system_prompt": system_prompt})
    if mode != "single":
        raise ValueError(f"Unsupported analysis mode: {mode}")
    from screenshot_to_template.pipeline.single_shot import run
    return run(screenshot_path, config, output_dir=output_dir)


def generate_structural_analysis(
    screenshot_path: str,
    config: AppConfig,
    output_dir: str | None = None,
) -> str:
    """Generate only the structural grounding markdown from a screenshot."""
    provider = get_provider(config)
    views = build_single_shot_views(screenshot_path, config.max_image_dimension)
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

    structural_analysis = provider.analyze_image(
        image_b64=image_b64,
        system_prompt=config.structural_analysis_prompt,
        user_prompt=(
            f"{multi_view_note}"
            "Analyze this website screenshot and produce the structural analysis only. "
            "Do not produce a design system."
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

    return structural_analysis


def load_prompt_file(path: Path) -> str:
    """Load a required prompt file."""
    if not path.exists():
        raise FileNotFoundError(f"Missing prompt file: {path}")
    return path.read_text().strip()


def load_optional_text_file(path: Path) -> str | None:
    """Load an optional text file, returning None when absent or empty."""
    if not path.exists():
        return None
    text = path.read_text().strip()
    return text or None


def write_resolved_text_file(path: Path, value: str | None) -> None:
    """Persist a resolved runtime setting so missing files cannot hide defaults."""
    text = (value or "").strip()
    if text:
        path.write_text(text + "\n")


def apply_version_model_overrides(config: AppConfig, version_dir: Path) -> None:
    """Apply version-local model overrides and persist the resolved runtime settings."""
    analysis_provider_override = load_optional_text_file(version_dir / "analysis-provider.txt")
    analysis_model_override = load_optional_text_file(version_dir / "analysis-model.txt")
    analysis_reasoning_override = load_optional_text_file(version_dir / "analysis-reasoning-effort.txt")
    section_detection_provider_override = load_optional_text_file(version_dir / "section-detection-provider.txt")
    section_detection_model_override = load_optional_text_file(version_dir / "section-detection-model.txt")
    section_detection_reasoning_override = load_optional_text_file(version_dir / "section-detection-reasoning-effort.txt")

    if analysis_provider_override:
        config.provider = analysis_provider_override
    if analysis_model_override:
        config.model = analysis_model_override
    if analysis_reasoning_override:
        config.reasoning_effort = analysis_reasoning_override

    if section_detection_provider_override:
        config.section_detection_provider = section_detection_provider_override
    if section_detection_model_override:
        config.section_detection_model = section_detection_model_override
    if section_detection_reasoning_override:
        config.section_detection_reasoning_effort = section_detection_reasoning_override

    write_resolved_text_file(version_dir / "analysis-provider.txt", config.provider)
    write_resolved_text_file(version_dir / "analysis-model.txt", config.model)
    write_resolved_text_file(version_dir / "analysis-reasoning-effort.txt", config.reasoning_effort)
    write_resolved_text_file(version_dir / "section-detection-provider.txt", config.section_detection_provider)
    write_resolved_text_file(version_dir / "section-detection-model.txt", config.section_detection_model)
    write_resolved_text_file(
        version_dir / "section-detection-reasoning-effort.txt",
        config.section_detection_reasoning_effort,
    )


def infer_manifest_from_version_dir(version_dir: Path) -> dict:
    """Reconstruct a manifest from run artifacts when one is missing."""
    screenshots: list[dict] = []
    for item_dir in sorted(p for p in version_dir.iterdir() if p.is_dir() and not p.name.startswith(".")):
        screenshot_path = next(iter(sorted(item_dir.glob("screenshot.*"))), None)
        single_dir = item_dir / "single"
        if screenshot_path is None or not single_dir.exists():
            continue

        structural_path = single_dir / "structural-analysis.md"
        design_path = design_system_artifact_path(single_dir)
        if not design_path.exists():
            design_path = structural_path
        direct_path = item_dir / "site-gpt55-direct.html"
        # Legacy v155 and earlier runs used gpt54 in filenames even after the slot moved to GPT-5.5.
        if not direct_path.exists():
            direct_path = item_dir / "site-gpt54-direct.html"
        gpt55_site_path = single_dir / "site-gpt55.html"
        if not gpt55_site_path.exists():
            gpt55_site_path = single_dir / "site-gpt54.html"
        claude_grounding_site_path = single_dir / "site-claude-grounding.html"
        gpt55_grounding_site_path = single_dir / "site-gpt55-grounding.html"
        grounding_generation_input_path = single_dir / "site-generation-input.grounding.md"
        screenshots.append(
            {
                "name": item_dir.name,
                "screenshot": str(screenshot_path.relative_to(version_dir)),
                "single": {
                    "structural_analysis": str(structural_path.relative_to(version_dir)) if structural_path.exists() else "",
                    "layouts": str((single_dir / "layouts.yaml").relative_to(version_dir)) if (single_dir / "layouts.yaml").exists() else "",
                    "design_system": str(design_path.relative_to(version_dir)) if design_path.exists() else "",
                    "site_generation_input": str((single_dir / "site-generation-input.md").relative_to(version_dir)),
                    "surface_component_contract": str((single_dir / "surface-component-contract.yaml").relative_to(version_dir)) if (single_dir / "surface-component-contract.yaml").exists() else "",
                    "surface_component_contract_audit": str((single_dir / "surface-component-contract-audit.md").relative_to(version_dir)) if (single_dir / "surface-component-contract-audit.md").exists() else "",
                    "source_style_ledger": str((single_dir / "source-style-ledger.yaml").relative_to(version_dir)) if (single_dir / "source-style-ledger.yaml").exists() else "",
                    "design_system_style_audit": str((single_dir / "design-system-style-audit.json").relative_to(version_dir)) if (single_dir / "design-system-style-audit.json").exists() else "",
                    "design_system_review": str((single_dir / "design-system-review.md").relative_to(version_dir)),
                    "design_system_conversion_review": str((single_dir / "design-system-conversion-review.md").relative_to(version_dir)),
                    "site_claude": str((single_dir / "site-claude.html").relative_to(version_dir)),
                    "site_gemini": str((single_dir / "site-gemini.html").relative_to(version_dir)),
                    "site_gpt55": str(gpt55_site_path.relative_to(version_dir)),
                    "site_claude_framework": str((single_dir / "site-claude-framework.html").relative_to(version_dir))
                    if (single_dir / "site-claude-framework.html").exists()
                    else "",
                    "site_gpt55_framework": str((single_dir / "site-gpt55-framework.html").relative_to(version_dir))
                    if (single_dir / "site-gpt55-framework.html").exists()
                    else "",
                    "site_generation_input_grounding": str(grounding_generation_input_path.relative_to(version_dir)) if grounding_generation_input_path.exists() else "",
                    "site_claude_grounding": str(claude_grounding_site_path.relative_to(version_dir)) if claude_grounding_site_path.exists() else "",
                    "site_gpt55_grounding": str(gpt55_grounding_site_path.relative_to(version_dir)) if gpt55_grounding_site_path.exists() else "",
                },
                "site_gpt55_direct": str(direct_path.relative_to(version_dir)) if direct_path.exists() else "",
            }
        )

    return {
        "version": version_dir.name,
        "timestamp": datetime.now().isoformat(),
        "screenshots": screenshots,
    }


def count_unfilled_asset_briefs(html_path: Path) -> int:
    """Count generated-site asset placeholders that have not been replaced."""
    if not html_path.exists():
        return 0
    soup = BeautifulSoup(html_path.read_text(errors="ignore"), "html.parser")
    count = 0
    for tag in soup.find_all(attrs={ASSET_BRIEF_ATTRIBUTE: True}):
        if not isinstance(tag, Tag):
            continue
        if (tag.name or "").lower() == "img":
            src = str(tag.get("src") or "").strip()
            if src and not src.startswith("data:"):
                continue
        count += 1
    return count


def write_disabled_site_asset_manifest(html_path: Path, placeholder_count: int) -> dict:
    """Record that asset generation was intentionally disabled for a generated site."""
    payload = {
        "status": "disabled",
        "html": str(html_path),
        "generated_count": 0,
        "unfilled_asset_brief_count": placeholder_count,
        "candidates": [],
    }
    html_path.with_suffix(".assets.json").write_text(json.dumps(payload, indent=2) + "\n")
    return payload


def backfill_generated_site_assets(version_dir: Path, config: AppConfig) -> dict:
    """Generate missing visual assets for an existing run without regenerating sites."""
    if not config.site_asset_generation_enabled:
        raise ValueError("Site asset generation is disabled. Use --site-assets or an assets-enabled config.")

    totals = {
        "sites_scanned": 0,
        "sites_with_placeholders": 0,
        "placeholders_before": 0,
        "generated_assets": 0,
        "errors": 0,
    }
    work_items: list[tuple[Path, Path, str, int, str]] = []
    for single_dir in sorted(version_dir.glob("*/single")):
        generation_input_path = single_dir / "site-generation-input.md"
        if not generation_input_path.exists():
            generation_input_path = single_dir / "site-generation-input.raw-design-system.md"
        generation_input = generation_input_path.read_text(errors="ignore") if generation_input_path.exists() else ""

        for html_path in sorted(single_dir.glob("site-*.html")):
            if html_path.name.endswith(".pre-style-sync.html"):
                continue
            totals["sites_scanned"] += 1
            placeholder_count = count_unfilled_asset_briefs(html_path)
            if placeholder_count <= 0:
                continue

            totals["sites_with_placeholders"] += 1
            totals["placeholders_before"] += placeholder_count
            work_items.append((single_dir, html_path, generation_input, placeholder_count, html_path.stem.replace("site-", "")))

    def generate_for_html(item: tuple[Path, Path, str, int, str]) -> tuple[int, int]:
        single_dir, html_path, generation_input, placeholder_count, provider_name = item
        log(f"  {single_dir.parent.name}/{html_path.name} — generating {placeholder_count} missing asset(s)")
        try:
            update_step_status(
                single_dir,
                f"site_asset_generation_{provider_name}",
                "in_progress",
                {"html": html_path.name, "placeholder_count": placeholder_count, "backfill": True},
            )
            with token_usage_context(single_dir, f"site_asset_generation_{provider_name}", {"html": html_path.name, "backfill": True}):
                payload = apply_generated_site_assets(
                    html_path=html_path,
                    design_system_markdown=generation_input,
                    config=config,
                    source_crops_dir=single_dir / "crops",
                )
            generated_count = int(payload.get("generated_count", 0) or 0)
            update_step_status(
                single_dir,
                f"site_asset_generation_{provider_name}",
                "completed",
                {
                    "html": html_path.name,
                    "placeholder_count": placeholder_count,
                    "generated_count": generated_count,
                    "status": payload.get("status", "unknown"),
                    "backfill": True,
                },
            )
            log(f"  {single_dir.parent.name}/{html_path.name} — generated {generated_count} asset(s)")
            return generated_count, 0
        except Exception as exc:
            update_step_status(
                single_dir,
                f"site_asset_generation_{provider_name}",
                "failed",
                {"html": html_path.name, "error": str(exc), "backfill": True},
            )
            log(f"  {single_dir.parent.name}/{html_path.name} — asset generation ERROR: {exc}")
            return 0, 1

    worker_count = max(1, int(getattr(config, "site_asset_generation_workers", 3) or 1))
    worker_count = min(worker_count, len(work_items)) if work_items else 1
    with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count) as executor:
        future_to_item = {executor.submit(generate_for_html, item): item for item in work_items}
        for future in concurrent.futures.as_completed(future_to_item):
            generated_count, error_count = future.result()
            totals["generated_assets"] += generated_count
            totals["errors"] += error_count

    (version_dir / "asset-backfill-summary.json").write_text(json.dumps(totals, indent=2) + "\n")
    return totals


def _inject_viewer_base_href(html_text: str, source_path: Path) -> str:
    """Make relative asset paths resolve correctly inside blob-backed viewer iframes."""
    if not html_text:
        return html_text
    if re.search(r"<base\b", html_text, flags=re.IGNORECASE):
        return html_text

    base_tag = f'<base href="{source_path.parent.resolve().as_uri()}/">'
    if re.search(r"<head\b[^>]*>", html_text, flags=re.IGNORECASE):
        return re.sub(
            r"(<head\b[^>]*>)",
            r"\1\n" + base_tag,
            html_text,
            count=1,
            flags=re.IGNORECASE,
        )
    if re.search(r"<html\b[^>]*>", html_text, flags=re.IGNORECASE):
        return re.sub(
            r"(<html\b[^>]*>)",
            r"\1\n<head>\n" + base_tag + "\n</head>",
            html_text,
            count=1,
            flags=re.IGNORECASE,
        )
    return "<head>\n" + base_tag + "\n</head>\n" + html_text


def load_section_agent_bundle(version_dir: Path) -> tuple[list[tuple[str, str]] | None, str | None]:
    """Load optional per-section agent prompts from a version folder."""
    agent_files = [
        ("section", version_dir / "section-agent-section-prompt.md"),
        ("container", version_dir / "section-agent-container-prompt.md"),
        ("components", version_dir / "section-agent-components-prompt.md"),
        ("text", version_dir / "section-agent-text-prompt.md"),
    ]
    existing_agents = [(name, path) for name, path in agent_files if path.exists()]
    if not existing_agents:
        return None, None

    missing = [str(path) for name, path in agent_files if not path.exists()]
    if missing:
        raise FileNotFoundError(
            "Multi-agent prompts are partially defined. Missing: " + ", ".join(missing)
        )

    merge_path = version_dir / "section-agent-merge-prompt.md"
    if not merge_path.exists():
        raise FileNotFoundError(f"Missing prompt file: {merge_path}")

    prompts = [(name, load_prompt_file(path)) for name, path in agent_files]
    return prompts, load_prompt_file(merge_path)


def load_section_grounding_bundle(version_dir: Path) -> dict | None:
    """Load optional section-grounding prompts for the single-shot path."""
    inventory_path = version_dir / "section-inventory-prompt.md"
    section_path = version_dir / "section-grounding-prompt.md"
    merge_path = version_dir / "grounding-merge-prompt.md"
    transition_path = version_dir / "section-transition-prompt.md"
    full_page_review_path = version_dir / "full-page-review-prompt.md"
    global_site_path = version_dir / "global-site-grounding-prompt.md"

    if not any(path.exists() for path in (inventory_path, section_path, merge_path, transition_path, full_page_review_path, global_site_path)):
        return None

    if not all(path.exists() for path in (inventory_path, section_path, merge_path)):
        missing = [str(path) for path in (inventory_path, section_path, merge_path) if not path.exists()]
        raise FileNotFoundError(
            "Section-grounding prompts are partially defined. Missing: " + ", ".join(missing)
        )

    section_agent_prompts, section_agent_merge_prompt = load_section_agent_bundle(version_dir)
    transition_prompt = transition_path.read_text().strip() if transition_path.exists() else None
    full_page_review_prompt = full_page_review_path.read_text().strip() if full_page_review_path.exists() else None
    global_site_prompt = global_site_path.read_text().strip() if global_site_path.exists() else None
    return {
        "inventory_prompt": load_prompt_file(inventory_path),
        "section_prompt": load_prompt_file(section_path),
        "merge_prompt": load_prompt_file(merge_path),
        "transition_prompt": transition_prompt,
        "full_page_review_prompt": full_page_review_prompt,
        "global_site_prompt": global_site_prompt,
        "section_agent_prompts": section_agent_prompts,
        "section_agent_merge_prompt": section_agent_merge_prompt,
        "include_full_page_context": transition_prompt is None,
    }


def load_site_generation_source(version_dir: Path) -> str:
    """Load which markdown artifact should drive site generation."""
    source_path = version_dir / "site-generation-source.txt"
    if not source_path.exists():
        return "design_system"
    source = source_path.read_text().strip().lower()
    if source not in {"design_system", "grounding"}:
        raise ValueError(
            f"Invalid site-generation source in {source_path}: {source!r}. "
            "Expected 'design_system' or 'grounding'."
        )
    return source


def parse_skill_list(text: str) -> list[str]:
    """Parse a version-scoped site-generation skill list."""
    skill_names: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].strip().lower()
        if not line:
            continue
        for item in re.split(r"[\s,]+", line):
            if item and item not in DISABLED_SITE_GENERATION_SKILLS:
                skill_names.append(item)

    ordered_unique: list[str] = []
    for skill_name in skill_names:
        if skill_name not in ordered_unique:
            ordered_unique.append(skill_name)
    return ordered_unique


def load_site_generation_skills(skill_names: list[str]) -> list[dict]:
    """Load project skill markdown files selected for site generation."""
    skills: list[dict] = []
    missing: list[str] = []

    for skill_name in skill_names:
        skill_path = PROJECT_SKILLS_DIR / skill_name / "SKILL.md"
        if not skill_path.exists():
            missing.append(skill_name)
            continue
        content = skill_path.read_text().strip()
        skills.append({
            "name": skill_name,
            "path": skill_path,
            "content": content,
        })

    if missing:
        raise FileNotFoundError(
            "Missing site generation skill(s): "
            + ", ".join(missing)
            + f". Expected each at {PROJECT_SKILLS_DIR}/<skill-name>/SKILL.md"
        )

    return skills


def build_site_generation_input(
    generation_markdown: str,
    generation_label: str,
    skills: list[dict],
) -> str:
    """Build the exact text bundle sent to website generation models."""
    normalized_label = generation_label.strip() or "design system"
    parts = [
        "# Site Generation Input",
        "",
        f"## Source {normalized_label.title()}",
        "",
        generation_markdown.strip(),
    ]

    if skills:
        parts.extend([
            "",
            "## Active Site Generation Skills",
            "",
            "Use these skills as additional implementation guidance. The source design-system tokens and grounded visual rules remain authoritative when a skill and the source artifact conflict.",
        ])
        for skill in skills:
            parts.extend([
                "",
                f"### {skill['name']}",
                "",
                skill["content"],
            ])

    return "\n".join(parts).rstrip() + "\n"


SITE_GENERATION_LEAK_PATTERNS = {
    "source_section_id": re.compile(r"\bsections?[_-]\d{1,2}(?:[_-][a-z0-9]+)*\b|\bsection_\d{1,2}(?:[_\. -][a-z0-9_-]+)*", re.IGNORECASE),
    "source_provenance_key": re.compile(
        r"\b(?:provenance|abstraction_source|detail_source|exact_values_source|normalized_site_ast|raw_section_grounding|css_style_report|derived_from|evidenceSections|run_order|source_order|page_sequence|section_sequence|patterns\.sections|surface_runs)\b",
        re.IGNORECASE,
    ),
    "source_layout_artifact": re.compile(r"\b(?:source_layouts|layouts\.yaml|source-specific section order)\b", re.IGNORECASE),
}


def strip_source_provenance_from_design_system(markdown: str) -> str:
    """Remove source-order/provenance breadcrumbs from a generated design-system artifact."""
    lines = markdown.splitlines()
    cleaned: list[str] = []
    skip_indent: int | None = None
    block_key = re.compile(
        r"^(\s*)(provenance|derived_from|evidenceSections|generated_from|run_order|source_order|page_sequence|section_sequence|surface_runs|sections)\s*:\s*(.*)$",
        re.IGNORECASE,
    )
    scalar_source = re.compile(r"^\s*source\s*:\s*(?:normalized_site_ast|section_grounding|source_layouts)\s*$", re.IGNORECASE)

    for raw_line in lines:
        line = raw_line.rstrip()
        stripped = line.strip()
        indent = len(line) - len(line.lstrip(" "))

        if skip_indent is not None:
            if not stripped:
                continue
            if indent > skip_indent or stripped.startswith("- "):
                continue
            skip_indent = None

        match = block_key.match(line)
        if match:
            value = match.group(3).strip()
            if not value or value in {"[]", "{}"}:
                skip_indent = len(match.group(1))
            continue
        if scalar_source.match(line):
            continue

        line = SITE_GENERATION_LEAK_PATTERNS["source_section_id"].sub("source_evidence", line)
        line = re.sub(r"\bsections?_\d{1,2}_to_\d{1,2}\b", "source_evidence_group", line, flags=re.IGNORECASE)
        cleaned.append(line)

    text = "\n".join(cleaned).strip()
    return text.rstrip() + "\n"


SITE_GENERATION_METADATA_BLOCKS_TO_STRIP = {
    "embedded_showcase_only",
}

SITE_GENERATION_SUBJECT_TERM_ALLOWLIST = {
    "app",
    "badge",
    "badges",
    "brand",
    "card",
    "cards",
    "content",
    "decorative",
    "demo",
    "diagram",
    "glyph",
    "glyphs",
    "interface",
    "interfaces",
    "label",
    "labels",
    "lettering",
    "logo",
    "media",
    "mockup",
    "only",
    "preview",
    "previews",
    "product",
    "showcase",
    "status",
    "text",
    "texture",
    "textures",
    "typography",
    "ui",
    "visual",
    "visualization",
    "visualizations",
}


def extract_embedded_showcase_subject_terms(markdown: str) -> set[str]:
    """Find likely source-subject terms hiding in embedded-showcase metadata names."""
    terms: set[str] = set()
    in_block = False
    block_indent = 0
    name_re = re.compile(r"^\s*-\s*name\s*:\s*['\"]?([^'\"\n#]+)")

    for line in markdown.splitlines():
        stripped = line.strip()
        indent = len(line) - len(line.lstrip(" "))
        if not in_block:
            if re.match(r"^embedded_showcase_only\s*:\s*$", stripped, flags=re.IGNORECASE):
                in_block = True
                block_indent = indent
            continue
        if stripped and indent <= block_indent and not stripped.startswith("- "):
            in_block = False
            continue
        match = name_re.match(line)
        if not match:
            continue
        raw_name = match.group(1)
        for token in re.findall(r"[a-z][a-z0-9]+", raw_name.lower()):
            if token not in SITE_GENERATION_SUBJECT_TERM_ALLOWLIST and len(token) > 3:
                terms.add(token)

    return terms


def rewrite_source_subject_terms_for_site_generation(line: str, subject_terms: set[str]) -> str:
    """Replace source-subject words in generation-facing prose with generic visual roles."""
    rewritten = line
    # These are visual mechanics when abstracted, but domain anchors when copied literally.
    rewritten = re.sub(r"\baudio\s+waveforms?\b", "abstract data visualizations", rewritten, flags=re.IGNORECASE)
    rewritten = re.sub(r"\bwaveform\s+controls?\b", "embedded visualization controls", rewritten, flags=re.IGNORECASE)
    rewritten = re.sub(r"\bwaveforms?\b", "abstract data visualizations", rewritten, flags=re.IGNORECASE)
    rewritten = re.sub(r"\baudio\b", "domain-specific media", rewritten, flags=re.IGNORECASE)

    for term in sorted(subject_terms, key=len, reverse=True):
        if term in {"audio", "waveform", "waveforms"}:
            continue
        rewritten = re.sub(rf"\b{re.escape(term)}\b", "domain-specific", rewritten, flags=re.IGNORECASE)
    return rewritten


def strip_source_subject_metadata_for_site_generation(markdown: str) -> str:
    """Remove source-subject helper metadata that can steer fresh site generation."""
    subject_terms = extract_embedded_showcase_subject_terms(markdown)
    lines: list[str] = []
    skip_block_indent: int | None = None
    in_do_not_generalize = False
    do_not_generalize_indent = 0
    content_warning_re = re.compile(
        r"\b(?:literal\s+business|business/product/industry|industry\s+copy|exact\s+brand|brand\s+mark|"
        r"wordmark|partner/customer|logo\s+names?|logo\s+letterforms|section\s+ordering|hidden\s+or\s+clipped\s+content)\b",
        re.IGNORECASE,
    )

    for raw_line in markdown.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        indent = len(line) - len(line.lstrip(" "))

        if skip_block_indent is not None:
            if not stripped:
                continue
            if indent > skip_block_indent or stripped.startswith("- "):
                continue
            skip_block_indent = None

        block_key_match = re.match(r"^([A-Za-z0-9_-]+)\s*:\s*$", stripped)
        if block_key_match and block_key_match.group(1).lower() in SITE_GENERATION_METADATA_BLOCKS_TO_STRIP:
            skip_block_indent = indent
            in_do_not_generalize = False
            continue

        if re.match(r"^do_not_generalize\s*:\s*$", stripped, flags=re.IGNORECASE):
            in_do_not_generalize = True
            do_not_generalize_indent = indent
            lines.append(line)
            continue
        if in_do_not_generalize and stripped and indent <= do_not_generalize_indent and not stripped.startswith("- "):
            in_do_not_generalize = False

        if in_do_not_generalize and stripped.startswith("- ") and content_warning_re.search(stripped):
            continue

        lines.append(rewrite_source_subject_terms_for_site_generation(line, subject_terms))

    return "\n".join(lines).strip() + "\n"


def source_section_label_patterns(output_dir: Path) -> dict[str, re.Pattern]:
    """Build conservative source-specific label detectors from sections.json."""
    sections_path = output_dir / "sections.json"
    if not sections_path.exists():
        return {}
    try:
        sections = json.loads(sections_path.read_text())
    except Exception:
        return {}

    generic_labels = {"navigation", "nav", "hero", "footer"}
    patterns: dict[str, re.Pattern] = {}
    for item in sections if isinstance(sections, list) else []:
        label = str(item.get("label", "")).strip()
        normalized = re.sub(r"\s+", " ", label.lower())
        if not normalized or normalized in generic_labels:
            continue
        words = re.findall(r"[a-z0-9]+", normalized)
        if len(words) < 2:
            continue
        phrase = r"\b" + r"[\W_]+".join(re.escape(word) for word in words) + r"\b"
        slug = r"\b" + re.escape("-".join(words)) + r"\b"
        patterns[normalized] = re.compile(f"(?:{phrase}|{slug})", re.IGNORECASE)
    return patterns


def strip_source_provenance_for_site_generation(markdown: str) -> str:
    """Remove source-order/provenance breadcrumbs before sending a design system to site generation."""
    text = strip_source_provenance_from_design_system(markdown).strip()
    text = strip_source_subject_metadata_for_site_generation(text).strip()
    text += (
        "\n\n## Fresh Composition Contract\n\n"
        "- Treat the design system above as an unordered library of reusable surfaces, components, imagery styles, and layout grammar.\n"
        "- Do not infer page order from the order of tokens, surfaces, components, patterns, or evidence in this artifact.\n"
        "- Build a fresh landing-page composition: navigation and footer may remain conventional bookends, but the body sections must be selected and ordered as a new composition.\n"
        "- Preserve reusable surface ownership, component recipes, typography, imagery style, and spacing rhythm without reconstructing the source page's section sequence.\n"
        "- If an artifact still contains a trace hint, treat it only as non-rendered metadata and do not use it for class names, section names, or page order.\n"
    )
    return text.rstrip() + "\n"


def audit_site_generation_freshness(text: str, output_dir: Path) -> dict:
    """Write and return a high-signal audit for source-order leaks in the generation bundle."""
    findings: dict[str, list[dict]] = {}
    audit_patterns = dict(SITE_GENERATION_LEAK_PATTERNS)
    audit_patterns.update({
        f"source_section_label:{label}": pattern
        for label, pattern in source_section_label_patterns(output_dir).items()
    })
    for name, pattern in audit_patterns.items():
        matches: list[dict] = []
        for match in pattern.finditer(text):
            start = max(0, match.start() - 80)
            end = min(len(text), match.end() + 80)
            matches.append({
                "match": match.group(0),
                "position": match.start(),
                "snippet": text[start:end].replace("\n", "\\n"),
            })
            if len(matches) >= 50:
                break
        findings[name] = matches

    high_risk_match_count = sum(len(matches) for matches in findings.values())
    payload = {
        "status": "passed" if high_risk_match_count == 0 else "failed",
        "high_risk_match_count": high_risk_match_count,
        "patterns": {name: len(matches) for name, matches in findings.items()},
        "findings": findings,
    }
    (output_dir / "site-generation-freshness-audit.json").write_text(json.dumps(payload, indent=2) + "\n")
    return payload


def compact_yaml_grounding_for_design_system(text: str, max_chars: int = 42000) -> str:
    """Compact large normalized/raw YAML grounding before final design-system synthesis."""
    stripped = (text or "").strip()
    if len(stripped) <= max_chars:
        return stripped

    priority = re.compile(
        r"(schema_version|^type:|^site:|^sections:|^global_observations:|"
        r"component_candidates:|section_pattern_candidates:|critical_pairings:|"
        r"do_not_generalize:|open_questions:|surface|background|color|typography|"
        r"spacing|radius|shadow|divider|button|link|card|panel|label|media|graphic|"
        r"image|gradient|pattern|widthBehavior|width_behavior|textTransform|confidence|derived_from)",
        flags=re.IGNORECASE | re.MULTILINE,
    )
    kept: list[str] = []
    current_chars = 0
    for raw_line in stripped.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            continue
        if priority.search(line) or line.startswith(("- id:", "  - id:", "    - id:", "- name:", "  - name:")):
            kept.append(line)
            current_chars += len(line) + 1
        if current_chars >= max_chars:
            break
    compacted = "\n".join(kept).strip()
    if len(compacted) < max_chars // 3:
        compacted = stripped[:max_chars].rstrip()
    return compacted[:max_chars].rstrip() + "\n# compacted_for_design_system_synthesis: see saved full artifacts for raw detail"


def synthesize_design_system_from_grounding(
    structural_analysis: str,
    config: AppConfig,
    source_color_report: str | None = None,
    source_style_ledger: str | None = None,
    section_grounding_markdown: str | None = None,
    surface_component_map: str | None = None,
    surface_component_contract: str | None = None,
    prior_review_guidance: str | None = None,
    prior_conversion_review_guidance: str | None = None,
    prior_design_system: str | None = None,
) -> str:
    """Generate the final design system from grounded text plus optional source CSS styles."""
    provider = get_provider(config)

    use_yaml_design_prompt = "design_system_yaml" in config.system_prompt or "Design-system YAML" in config.system_prompt
    structural_reference = (
        compact_yaml_grounding_for_design_system(structural_analysis)
        if use_yaml_design_prompt
        else structural_analysis
    )

    user_prompt = (
        "Use the structural analysis below as grounding and produce the final design system. "
        "Do not assume access to the screenshot. "
        "If detailed section grounding is also provided, use it to preserve local component-on-surface "
        "color pairings, typography casing, and other facts that may have been compressed during merge.\n\n"
        f"{structural_reference}"
    )
    if section_grounding_markdown and section_grounding_markdown.strip():
        section_reference = (
            compact_section_grounding_for_surface_map(section_grounding_markdown, max_chars=30000)
            if use_yaml_design_prompt
            else section_grounding_markdown.strip()
        )
        user_prompt += (
            "\n\n## Detailed Section Grounding Markdown\n\n"
            "This section-level grounding is a high-detail reference. Preserve factual component color pairings, "
            "heading/body color relationships, card/border/shadow recipes, and explicit text casing from it when "
            "the merged structural analysis is shorter or less specific.\n\n"
            f"{section_reference}"
        )
    if surface_component_map and surface_component_map.strip():
        user_prompt += (
            "\n\n## Surface Component Map\n\n"
            "This map is the most explicit reference for host-surface and nested-element color relationships. "
            "Preserve its pairings as normative component recipes and on-surface typography rules in YAML and markdown. "
            "Do not collapse a surface-specific button, label, card, heading, body, border, shadow, or divider pairing into "
            "a global accent if the map ties it to a specific host surface.\n\n"
            f"{surface_component_map.strip()}"
        )
    if surface_component_contract and surface_component_contract.strip():
        user_prompt += (
            "\n\n## Deterministic Surface Component Contract\n\n"
            "This audited contract is normative for host surface backgrounds, child fills, text colors by host, "
            "button/label/card/divider recipes, typography and casing, imagery creative direction, and do-not-generalize boundaries. "
            "Use the generic generation roles as reusable roles; do not infer source section order from this contract.\n\n"
            f"{surface_component_contract.strip()}"
        )
    if source_style_ledger and source_style_ledger.strip():
        user_prompt += (
            "\n\n## Source Style Ledger\n\n"
            "This ledger is the generation-facing source-style contract. Treat `palette.generation_palette` "
            "and typography roles as the exact source-backed values to prefer during synthesis. Grounding colors "
            "are visual observations; exact generated values should come from this ledger when a role-compatible "
            "value exists. Typography values from the ledger are evidence, not an override, when the active "
            "design-system prompt defines normalized type constraints for body text, subheads, controls, links, "
            "or semantic heading family/weight consistency.\n\n"
            f"{source_style_ledger.strip()}"
        )
    if source_color_report:
        user_prompt += (
            "\n\nSource-of-truth CSS styles from the original HTML are provided below. "
            "Use exact source colors, gradients, and typography values when they visually preserve the grounded role. "
            "When no visually close source value preserves a screenshot-grounded component-on-surface relationship, "
            "keep the grounded value or describe the relationship semantically instead of remapping it to a distant source token.\n\n"
            f"{source_color_report}"
        )
    if prior_review_guidance and prior_review_guidance.strip():
        user_prompt += (
            "\n\n## Prior Design-System Review Guidance\n\n"
            "The previous iteration was reviewed against the same screenshot. Address these concrete weak spots while staying grounded in the structural analysis, section grounding, surface/component map, and source CSS. "
            "Do not overfit to review wording by inventing unsupported components; improve specificity and correctness where the review identifies missing mechanics.\n\n"
            f"{prior_review_guidance.strip()}"
        )
    if prior_conversion_review_guidance and prior_conversion_review_guidance.strip():
        user_prompt += (
            "\n\n## Prior Surface-Map-To-Design-System Conversion Review Guidance\n\n"
            "The previous iteration was reviewed by comparing its design system directly to the surface/component map. "
            "Fix true conversion losses by preserving map-specific host surface pairings, nested component recipes, casing, constraints, and one-off boundaries. "
            "Do not satisfy this guidance by inventing unsupported surface roles or by copying section-specific labels into token names; translate exact map facts into generic reusable roles and variants.\n\n"
            f"{prior_conversion_review_guidance.strip()}"
        )
    if prior_design_system and prior_design_system.strip():
        user_prompt += (
            "\n\n## Previous Design System To Revise\n\n"
            "Use this previous design system as a seed. Preserve sections and recipes that the prior review scored well, but revise weak, sparse, overfit, or unsupported sections using the grounding, surface/component map, source CSS, and prior review guidance. "
            "Return a complete replacement design-system markdown document, not a patch.\n\n"
            f"{prior_design_system.strip()[:50000]}"
        )

    query_config = config
    if use_yaml_design_prompt and config.provider == "openai" and config.reasoning_effort:
        query_config = AppConfig(**{**vars(config), "reasoning_effort": None})
        provider = get_provider(query_config)

    return provider.text_query(
        system_prompt=config.system_prompt,
        user_prompt=user_prompt,
        max_tokens=max(query_config.max_tokens, 32768) if use_yaml_design_prompt else query_config.max_tokens,
    )


def _design_system_strategy_context(
    *,
    structural_analysis: str,
    source_color_report: str | None,
    source_style_ledger: str | None = None,
    section_grounding_markdown: str | None = None,
    surface_component_map: str | None = None,
    surface_component_contract: str | None = None,
    prior_review_guidance: str | None = None,
    prior_conversion_review_guidance: str | None = None,
    prior_design_system: str | None = None,
) -> str:
    """Build a shared context bundle for experimental design-system conversion strategies."""
    parts = [
        "## Merged Structural Grounding",
        structural_analysis.strip() or "No merged structural grounding provided.",
    ]
    if surface_component_map and surface_component_map.strip():
        parts.extend([
            "",
            "## Surface Component Map",
            "Treat this as the authoritative source for host-surface and nested-component facts.",
            surface_component_map.strip(),
        ])
    if surface_component_contract and surface_component_contract.strip():
        parts.extend([
            "",
            "## Deterministic Surface Component Contract",
            "Treat this audited contract as the authoritative source for host-surface and nested-component facts.",
            surface_component_contract.strip(),
        ])
    if source_style_ledger and source_style_ledger.strip():
        parts.extend([
            "",
            "## Source Style Ledger",
            "Treat this as the exact generation-facing source-style contract; use role-compatible values from `palette.generation_palette` before copying approximate grounding literals. Typography values are evidence, not an override, when the active design-system prompt defines normalized type constraints for body text, subheads, controls, links, or semantic heading family/weight consistency.",
            source_style_ledger.strip(),
        ])
    if section_grounding_markdown and section_grounding_markdown.strip():
        parts.extend([
            "",
            "## Detailed Section Grounding",
            "Use only to resolve ambiguity or restore detail missing from the map.",
            section_grounding_markdown.strip(),
        ])
    if source_color_report and source_color_report.strip():
        parts.extend([
            "",
            "## Source CSS Style Report",
            "Use exact source values only when they preserve the grounded/map role.",
            source_color_report.strip(),
        ])
    if prior_conversion_review_guidance and prior_conversion_review_guidance.strip():
        parts.extend([
            "",
            "## Prior Conversion Review Guidance",
            prior_conversion_review_guidance.strip(),
        ])
    if prior_review_guidance and prior_review_guidance.strip():
        parts.extend([
            "",
            "## Prior Screenshot-Based Design-System Review Guidance",
            prior_review_guidance.strip(),
        ])
    if prior_design_system and prior_design_system.strip():
        parts.extend([
            "",
            "## Prior Design System Seed",
            prior_design_system.strip()[:50000],
        ])
    return "\n\n".join(parts).rstrip()


def _write_strategy_artifact(output_dir: Path | None, filename: str, content: str) -> None:
    if not output_dir:
        return
    (output_dir / filename).write_text(content.strip() + "\n")


def _strategy_text_query(
    provider,
    *,
    system_prompt: str,
    user_prompt: str,
    config: AppConfig,
) -> str:
    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            return clean_markdown(provider.text_query(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=max(config.max_tokens, 16384),
            ))
        except Exception as exc:
            last_error = exc
            if attempt == 3:
                break
            time.sleep(8 * attempt)
    raise last_error or RuntimeError("strategy text query failed")


def _split_surface_map_chunks(surface_component_map: str, max_chunks: int = 4) -> list[str]:
    """Split the surface map into a few surface-oriented chunks for map/reduce conversion."""
    text = surface_component_map.strip()
    if not text:
        return []
    matches = list(re.finditer(r"^###\s+.+$", text, flags=re.MULTILINE))
    if not matches:
        return [text]

    sections: list[str] = []
    prefix = text[:matches[0].start()].strip()
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        section = text[match.start():end].strip()
        if section:
            sections.append(section)
    if not sections:
        return [text]

    groups: list[list[str]] = [[] for _ in range(min(max_chunks, len(sections)))]
    for index, section in enumerate(sections):
        groups[index % len(groups)].append(section)
    chunks = []
    for group in groups:
        chunk = "\n\n".join(([prefix] if prefix else []) + group).strip()
        if chunk:
            chunks.append(chunk)
    return chunks


ADDITIVE_CROP_INITIAL_PROMPT = """\
You are a design-system architect testing an additive extraction strategy inside an otherwise unchanged website-generation pipeline.

You will receive one cropped website section. Create the first complete design-system markdown document from this section alone.

Rules:
- Produce a complete markdown document with YAML front matter first.
- Use generic reusable token names and component variant names; never use section-specific, content-specific, or brand-specific token names.
- Exact source values may be mapped into generic roles, but the role names and rules must make sense for a completely different site.
- Treat this first section as provisional evidence. Do not claim a global default unless the crop itself makes that role unavoidable.
- Preserve host-surface/component pairings. A control, card, text, divider, or graphic recipe observed on one host surface must not become a default recipe for every surface.
- Capture non-stretch/content-hugging controls, casing, typography relationships, spacing rhythm, borders, radii, depth, graphics/media direction, and parent/child surface nesting when visible.
- Keep the document compact and implementation-oriented. Do not write a long walkthrough of the crop. The whole design system should stay under roughly 10,000 words.
- Include `## Additive Evidence Ledger` at the end and record the section number, label, bounds, crop path, observed surfaces, components, typography, layout, graphics/media, and uncertainties.
- The ledger should use one compact bullet group for this section, not repeated prose.
- Return only the design-system markdown.
"""


ADDITIVE_CROP_INTEGRATE_PROMPT = """\
You are a design-system architect testing an additive extraction strategy inside an otherwise unchanged website-generation pipeline.

You will receive:
1. The current cumulative design-system markdown from previous cropped sections.
2. One new cropped website section.

Return a complete replacement design-system markdown document integrating the new crop. Do not return a patch.

Rules:
- Preserve useful existing rules, but revise them when the new crop proves they are too broad, too narrow, or incorrectly generalized.
- Expand values and rules only when the new crop adds reusable evidence or a necessary surface-specific variant.
- Use generic reusable token names and component variant names; never use section-specific, content-specific, or brand-specific token names.
- Keep host-surface/component pairings local unless repeated evidence justifies promoting them to a default.
- If a relationship appears once, capture it as a generic conditional rule or one-off constraint, not a section-named token.
- Keep the cumulative document compact and implementation-oriented. Rewrite or consolidate earlier prose when needed; do not append a full new design-system-sized explanation for every section.
- The full replacement document should stay under roughly 10,000 words. Keep YAML concise, component recipes dense, and the ledger to one compact bullet group per processed section.
- Preserve and update `## Additive Evidence Ledger` so it remains cumulative and factual for every processed section.
- Return YAML front matter first, followed by the full markdown body.
"""


def _additive_crop_context(
    *,
    section: dict,
    index: int,
    total: int,
    crop_path: Path,
    sections: list[dict],
    source_color_report: str | None,
    previous_design_system: str | None,
) -> str:
    sequence = "\n".join(
        f"{idx}. {entry.get('label', f'Section {idx}')} "
        f"(y={entry.get('y_start', 'unknown')} to {entry.get('y_end', 'unknown')})"
        for idx, entry in enumerate(sections, start=1)
    )
    bounds = f"y={section.get('y_start', 'unknown')} to {section.get('y_end', 'unknown')}"
    prompt = (
        "## Current Section\n\n"
        f"- Section number: {index} of {total}\n"
        f"- Section label: {section.get('label', f'Section {index}')}\n"
        f"- Section bounds: {bounds}\n"
        f"- Crop artifact: {crop_path.name}\n\n"
        "## Full Section Sequence\n\n"
        f"{sequence}\n\n"
        "Analyze only the attached cropped section for new visual evidence. "
        "Use the sequence only for top-to-bottom placement."
    )
    if source_color_report and source_color_report.strip():
        prompt += (
            "\n\n## Source CSS Style Reference\n\n"
            "Use this reference only to ground exact colors, gradients, font families, and typography values when they match the crop. "
            "Do not let global source frequency override local surface/component pairings visible in the crop.\n\n"
            f"{source_color_report.strip()[:18000]}"
        )
    if previous_design_system and previous_design_system.strip():
        prompt += (
            "\n\n## Current Cumulative Design System\n\n"
            f"{previous_design_system.strip()}"
        )
    return prompt


def _find_section_crop(output_dir: Path, section_index: int) -> Path:
    crops_dir = output_dir / "crops"
    matches = sorted(crops_dir.glob(f"{section_index:02d}-*.png"))
    if not matches:
        raise FileNotFoundError(
            f"Missing section crop for section {section_index}: expected {crops_dir}/{section_index:02d}-*.png"
        )
    return matches[0]


def synthesize_design_system_additive_from_crops(
    *,
    config: AppConfig,
    source_color_report: str | None,
    output_dir: Path | None,
) -> str:
    """Build a design system by integrating normal-pipeline section crops one at a time."""
    if output_dir is None:
        raise ValueError("additive-crops strategy requires output_dir with normal section crops")
    sections_path = output_dir / "sections.json"
    if not sections_path.exists():
        raise FileNotFoundError("additive-crops strategy requires normal pipeline sections.json")
    sections = json.loads(sections_path.read_text())
    if not sections:
        raise ValueError("additive-crops strategy received no detected sections")

    provider = get_provider(config)
    steps_dir = output_dir / "additive-design-system-steps"
    steps_dir.mkdir(exist_ok=True)
    current_design_system = ""
    total = len(sections)

    for index, section in enumerate(sections, start=1):
        crop_path = _find_section_crop(output_dir, index)
        step_stem = crop_path.stem
        system_prompt = (
            ADDITIVE_CROP_INITIAL_PROMPT
            if not current_design_system
            else ADDITIVE_CROP_INTEGRATE_PROMPT
        )
        user_prompt = _additive_crop_context(
            section=section,
            index=index,
            total=total,
            crop_path=crop_path,
            sections=sections,
            source_color_report=source_color_report,
            previous_design_system=current_design_system or None,
        )
        cleaned = ""
        last_raw = ""
        for attempt in range(1, 3):
            attempt_config = config
            if attempt > 1 and config.provider == "openai" and config.reasoning_effort and not last_raw.strip():
                attempt_config = AppConfig(**{**vars(config), "reasoning_effort": None})
            attempt_provider = provider if attempt_config is config else get_provider(attempt_config)
            with token_usage_context(
                output_dir,
                f"design_system_additive_crop_{index:02d}",
                {
                    "section_label": section.get("label", f"Section {index}"),
                    "attempt": attempt,
                    "reasoning_effort": attempt_config.reasoning_effort,
                },
            ):
                raw = attempt_provider.analyze_image(
                    image_b64=load_and_encode_image(str(crop_path), attempt_config.max_image_dimension),
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    max_tokens=max(attempt_config.max_tokens, 24576),
                )
            last_raw = raw or ""
            (steps_dir / f"{step_stem}-raw-attempt-{attempt}.md").write_text(last_raw.rstrip() + "\n")
            cleaned = clean_markdown(last_raw)
            if len(cleaned.strip()) >= 300:
                break
            user_prompt += (
                "\n\n## Retry Instruction\n\n"
                "The previous attempt returned empty or malformed content. "
                "Return the complete cumulative design-system markdown now."
            )
        if len(cleaned.strip()) < 300:
            raise ValueError(f"Additive crop strategy returned empty output for section {index}")
        current_design_system = cleaned
        (steps_dir / f"{step_stem}-design-system.md").write_text(current_design_system.rstrip() + "\n")

    return current_design_system


def synthesize_design_system_with_strategy(
    *,
    structural_analysis: str,
    config: AppConfig,
    design_system_strategy: str,
    source_color_report: str | None = None,
    source_style_ledger: str | None = None,
    section_grounding_markdown: str | None = None,
    surface_component_map: str | None = None,
    surface_component_contract: str | None = None,
    prior_review_guidance: str | None = None,
    prior_conversion_review_guidance: str | None = None,
    prior_design_system: str | None = None,
    conversion_review_prompt: str | None = None,
    output_dir: Path | None = None,
) -> str:
    """Generate the final design system using an experimental conversion strategy."""
    strategy = (design_system_strategy or "one-shot").strip().lower()
    if strategy in {"default", "one-shot", "oneshot"}:
        return synthesize_design_system_from_grounding(
            structural_analysis=structural_analysis,
            config=config,
            source_color_report=source_color_report,
            source_style_ledger=source_style_ledger,
            section_grounding_markdown=section_grounding_markdown,
            surface_component_map=surface_component_map,
            surface_component_contract=surface_component_contract,
            prior_review_guidance=prior_review_guidance,
            prior_conversion_review_guidance=prior_conversion_review_guidance,
            prior_design_system=prior_design_system,
        )

    if strategy in {"additive-crops", "additive-sections"}:
        return synthesize_design_system_additive_from_crops(
            config=config,
            source_color_report=source_color_report,
            output_dir=output_dir,
        )

    provider = get_provider(config)
    context = _design_system_strategy_context(
        structural_analysis=structural_analysis,
        source_color_report=source_color_report,
        source_style_ledger=source_style_ledger,
        section_grounding_markdown=section_grounding_markdown,
        surface_component_map=surface_component_map,
        surface_component_contract=surface_component_contract,
        prior_review_guidance=prior_review_guidance,
        prior_conversion_review_guidance=prior_conversion_review_guidance,
        prior_design_system=prior_design_system,
    )
    final_instruction = (
        "Return a complete replacement design-system markdown document with YAML front matter first. "
        "Keep token names generic and reusable, but preserve factual host-surface pairings, component recipes, "
        "typography casing, gradients, dividers, shadows, one-off constraints, and doNotGeneralize boundaries from the map."
    )

    if strategy == "domain-agents":
        domains = [
            ("colors-surfaces", "Convert only color tokens, surface roles, on-surface heading/body text rules, gradients, and do-not-merge boundaries."),
            ("typography", "Convert only typography hierarchy, casing/textTransform, font/source style usage, heading/body/label roles, and surface-specific text behavior."),
            ("containers-layout", "Convert only containers, page rhythm, section shells, grouped runs, grids, split layouts, and parent/child surface nesting."),
            ("components-cards", "Convert only buttons, compact labels, badges, chips, cards, panels, links, controls, borders, dividers, shadows, and component surface mappings."),
            ("graphics-media", "Convert only imagery, graphics, decorative layers, masks, edge behavior, asset slots, and one-off visual constraints."),
        ]
        fragments: list[str] = []
        for slug, focus in domains:
            fragment = _strategy_text_query(
                provider,
                system_prompt=(
                    "You are a narrow design-system conversion agent. Work only in your assigned domain. "
                    "Preserve factual map evidence; do not write a full design system."
                ),
                user_prompt=(
                    f"Assigned domain: {focus}\n\n"
                    "Output a concise markdown fragment with exact tokens/rules this domain needs in the final design system. "
                    "Include `Must Preserve` and `Do Not Generalize` bullets when the map requires them.\n\n"
                    f"{context}"
                ),
                config=config,
            )
            _write_strategy_artifact(output_dir, f"design-system-domain-agent-{slug}.md", fragment)
            fragments.append(f"## {slug}\n\n{fragment}")
        merged = _strategy_text_query(
            provider,
            system_prompt=config.system_prompt,
            user_prompt=(
                "Merge these specialist conversion fragments into one coherent design system. "
                "Resolve conflicts by preserving the surface-component map facts over generic token cleanliness.\n\n"
                f"## Specialist Fragments\n\n{chr(10).join(fragments)}\n\n"
                f"## Original Context\n\n{context}\n\n{final_instruction}"
            ),
            config=config,
        )
        return merged

    if strategy == "schema-ledger":
        ledger = _strategy_text_query(
            provider,
            system_prompt=(
                "You are a schema-first extraction agent. Convert grounding/map text into a durable conversion ledger, "
                "not prose and not a final design system."
            ),
            user_prompt=(
                "Create a compact but complete conversion ledger with these sections: Surfaces, Critical Pairings, "
                "Components, Typography/Casing, Layout/Containers, Graphics/Media, Constraints/DoNotGeneralize, Ambiguities. "
                "Every row should include source role, exact/approx values, target generic role suggestion, and preserve/one-off status.\n\n"
                f"{context}"
            ),
            config=config,
        )
        _write_strategy_artifact(output_dir, "design-system-conversion-ledger.md", ledger)
        return _strategy_text_query(
            provider,
            system_prompt=config.system_prompt,
            user_prompt=(
                "Use the conversion ledger as the normative contract and render a full design-system markdown document. "
                "Do not drop ledger rows; place them in YAML components/tokens or explicit markdown constraints.\n\n"
                f"## Conversion Ledger\n\n{ledger}\n\n"
                f"## Reference Context\n\n{context}\n\n{final_instruction}"
            ),
            config=config,
        )

    if strategy == "surface-shards":
        chunks = _split_surface_map_chunks(surface_component_map or "", max_chunks=4)
        if not chunks:
            chunks = [surface_component_map or structural_analysis]
        fragments = []
        shared = (
            "Shared context: source styles and prior guidance are below. Convert only the provided surface-map shard "
            "into design-system fragment rules. Preserve exact pairings and constraints.\n\n"
        )
        shared_context = _design_system_strategy_context(
            structural_analysis=structural_analysis[:12000],
            source_color_report=source_color_report,
            section_grounding_markdown=None,
            surface_component_map=None,
            surface_component_contract=surface_component_contract,
            prior_review_guidance=prior_review_guidance,
            prior_conversion_review_guidance=prior_conversion_review_guidance,
            prior_design_system=None,
        )
        for index, chunk in enumerate(chunks, start=1):
            fragment = _strategy_text_query(
                provider,
                system_prompt=(
                    "You are a map/reduce surface-shard conversion agent. Convert only your shard into reusable design-system fragments."
                ),
                user_prompt=(
                    f"## Surface Map Shard {index}\n\n{chunk}\n\n"
                    f"{shared}{shared_context}"
                ),
                config=config,
            )
            _write_strategy_artifact(output_dir, f"design-system-surface-shard-{index}.md", fragment)
            fragments.append(f"## Shard {index}\n\n{fragment}")
        return _strategy_text_query(
            provider,
            system_prompt=config.system_prompt,
            user_prompt=(
                "Reduce these surface-shard fragments into one full design-system markdown document. "
                "If shards describe visually close but behaviorally different surfaces, keep them separate.\n\n"
                f"{chr(10).join(fragments)}\n\n"
                f"## Reference Context\n\n{context}\n\n{final_instruction}"
            ),
            config=config,
        )

    if strategy == "self-refine-repair":
        initial = synthesize_design_system_from_grounding(
            structural_analysis=structural_analysis,
            config=config,
            source_color_report=source_color_report,
            section_grounding_markdown=section_grounding_markdown,
            surface_component_map=surface_component_map,
            surface_component_contract=surface_component_contract,
            prior_review_guidance=prior_review_guidance,
            prior_conversion_review_guidance=prior_conversion_review_guidance,
            prior_design_system=prior_design_system,
        )
        initial = clean_markdown(initial)
        _write_strategy_artifact(output_dir, "design-system.pre-self-refine.md", initial)
        if conversion_review_prompt and output_dir:
            pre_review = evaluate_design_system_conversion_loss(
                surface_component_map=surface_component_map or "",
                design_system_markdown=initial,
                review_json_path=output_dir / "design-system.pre-self-refine-conversion-review.json",
                review_md_path=output_dir / "design-system.pre-self-refine-conversion-review.md",
                review_prompt=conversion_review_prompt,
                config=config,
                output_dir=output_dir,
            )
            review_text = design_system_conversion_review_to_markdown(pre_review)
        else:
            review_text = prior_conversion_review_guidance or ""
        repaired = _strategy_text_query(
            provider,
            system_prompt=config.system_prompt,
            user_prompt=(
                "Repair the design system using the conversion review. This is a targeted repair pass: preserve the original "
                "document structure where possible, patch missing YAML component recipes and markdown rules, and do not rewrite unrelated sections.\n\n"
                f"## Surface Component Map\n\n{surface_component_map or ''}\n\n"
                f"## Conversion Review\n\n{review_text}\n\n"
                f"## Design System To Repair\n\n{initial}\n\n{final_instruction}"
            ),
            config=config,
        )
        return repaired

    if strategy == "contract-render":
        contract = _strategy_text_query(
            provider,
            system_prompt=(
                "You are a design-system contract compiler. Produce a strict intermediate contract, not the final markdown."
            ),
            user_prompt=(
                "Compile a compact YAML-like contract with required keys: colors, typography, surfaces, components, cards, "
                "containers, graphics, dividers, constraints. Use generic names but include trace notes to map facts. "
                "Do not optimize for prose; optimize for lossless implementation requirements.\n\n"
                f"{context}"
            ),
            config=config,
        )
        _write_strategy_artifact(output_dir, "design-system-contract.md", contract)
        return _strategy_text_query(
            provider,
            system_prompt=config.system_prompt,
            user_prompt=(
                "Render this contract into the final design-system markdown. The contract is normative; do not simplify away "
                "surface-specific pairings, component variants, casing, dividers, graphics, or constraints.\n\n"
                f"## Design-System Contract\n\n{contract}\n\n"
                f"## Reference Context\n\n{context}\n\n{final_instruction}"
            ),
            config=config,
        )

    raise ValueError(f"Unknown design-system strategy: {design_system_strategy}")


def synthesize_surface_component_map(
    structural_analysis: str,
    config: AppConfig,
    surface_component_map_prompt: str,
    source_color_report: str | None = None,
    source_style_ledger: str | None = None,
    section_grounding_markdown: str | None = None,
    deterministic_surface_map: str | None = None,
    prior_surface_map_review_guidance: str | None = None,
    prior_surface_map: str | None = None,
) -> str:
    """Create an intermediate factual map of surfaces and nested component color recipes."""
    provider = get_provider(config)
    user_prompt = (
        "Compile a factual surface/component map from the grounding below. "
        "This map will be used before final design-system synthesis, so preserve implementation-critical local pairings.\n\n"
        "## Merged Structural Grounding\n\n"
        f"{structural_analysis.strip()}"
    )
    if section_grounding_markdown and section_grounding_markdown.strip():
        user_prompt += (
            "\n\n## Detailed Section Grounding Markdown\n\n"
            f"{section_grounding_markdown.strip()}"
        )
    if deterministic_surface_map and deterministic_surface_map.strip():
        user_prompt += (
            "\n\n## Deterministic Parsed Draft Surface Map\n\n"
            "Use this draft as a structured extraction aid, but correct taxonomy mistakes, remove repetition, "
            "and prefer the detailed section grounding whenever the draft conflicts with grounded evidence.\n\n"
            f"{deterministic_surface_map.strip()}"
        )
    if prior_surface_map_review_guidance and prior_surface_map_review_guidance.strip():
        user_prompt += (
            "\n\n## Prior Surface-Map Review Guidance\n\n"
            "The previous surface map was reviewed against the same screenshot. Address these concrete weak spots while staying grounded. "
            "Do not overfit to review wording by inventing unsupported surfaces or components; improve specificity, nesting, confidence, and normalization where the review identifies real gaps.\n\n"
            f"{prior_surface_map_review_guidance.strip()}"
        )
    if prior_surface_map and prior_surface_map.strip():
        user_prompt += (
            "\n\n## Previous Surface Map To Revise\n\n"
            "Use this previous map as a seed. Preserve sections and recipes the prior review scored well, but revise weak, missing, over-merged, over-split, noisy, or unsupported parts using the grounding and source CSS. "
            "Return a complete replacement surface-component map, not a patch.\n\n"
            f"{prior_surface_map.strip()[:50000]}"
        )
    if source_style_ledger and source_style_ledger.strip():
        user_prompt += (
            "\n\n## Source Style Ledger\n\n"
            "Use this source-style ledger as exact role-oriented evidence for colors, gradients, and typography. "
            "Only generalize values by reusable role family; do not turn section-specific observations into token names.\n\n"
            f"{source_style_ledger.strip()}"
        )
    if source_color_report and source_color_report.strip():
        user_prompt += (
            "\n\n## Source CSS Style Report\n\n"
            f"{source_color_report.strip()}"
        )

    return clean_markdown(provider.text_query(
        system_prompt=surface_component_map_prompt,
        user_prompt=user_prompt,
        max_tokens=max(config.max_tokens, 16384),
    ))


def sanitize_surface_component_map(surface_component_map: str) -> str:
    """Clean recurring taxonomy/provenance noise from synthesized surface maps."""
    cleaned_lines: list[str] = []
    font_family_pattern = re.compile(
        r"\b(?:PP\s+Right\s+Grotesk|Inter|Helvetica|Arial|Neue\s+Haas|Suisse|Graphik|Söhne|Sohne)\b",
        flags=re.IGNORECASE,
    )
    for raw_line in surface_component_map.splitlines():
        line = raw_line
        lower = line.lower()
        if "kind: cardpanel" in lower and re.search(
            r"same-surface|same surface|transparent|no separate fill|no distinct fill|low-confidence tonal shift",
            line,
            flags=re.IGNORECASE,
        ):
            line = re.sub(r"kind:\s*cardPanel", "kind: layout", line)
        if "kind: edgeDivider" in line and re.search(
            r"background line art|line art|mesh|ornament|motif|diagram|decorative background|background-blended",
            line,
            flags=re.IGNORECASE,
        ):
            line = re.sub(r"kind:\s*edgeDivider", "kind: graphicMedia", line)
        if "kind: graphicMedia" in line and re.search(
            r"decorative type|oversized word|slogan text|typographic slogan|display text|word art",
            line,
            flags=re.IGNORECASE,
        ):
            line = re.sub(r"kind:\s*graphicMedia", "kind: text", line)
        line = re.sub(r"\bCSS-close\b", "source-close", line, flags=re.IGNORECASE)
        line = re.sub(r"\bsource CSS\b", "source styles", line, flags=re.IGNORECASE)
        line = font_family_pattern.sub(lambda match: f"{match.group(0)}-like", line)
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines).rstrip() + "\n"


def synchronize_design_system_colors(
    design_system: str,
    source_color_report: str,
    config: AppConfig,
    color_sync_prompt: str | None = None,
    grounding_markdown: str | None = None,
) -> str:
    """Replace design-system color values using source CSS and grounding evidence."""
    provider = get_provider(config)
    input_is_yaml_design_system = _is_design_system_yaml_document(design_system)
    grounding_section = ""
    if grounding_markdown and grounding_markdown.strip():
        grounding_section = (
            "\n\n## Screenshot Grounding Markdown\n\n"
            "Use this grounding to preserve local component-on-surface color pairings. "
            "When source CSS colors do not contain a visually close match for a grounded component color, "
            "the grounded screenshot color may remain as the fallback value.\n\n"
            f"{grounding_markdown.strip()}"
        )
    result = provider.text_query(
        system_prompt=color_sync_prompt or DEFAULT_COLOR_SYNC_PROMPT,
        user_prompt=(
            "## Design System Markdown\n\n"
            f"{design_system}\n\n"
            "## Source CSS Color Report\n\n"
            f"{source_color_report}"
            f"{grounding_section}"
        ),
        max_tokens=max(config.max_tokens, 16384),
    )
    cleaned = clean_markdown(result)
    cleaned = re.sub(
        r"^(?:## Design System Markdown\s*)+",
        "",
        cleaned,
        flags=re.IGNORECASE,
    ).lstrip()
    cleaned = strip_echoed_source_style_report(cleaned)
    if input_is_yaml_design_system and not _is_design_system_yaml_document(cleaned):
        return design_system
    return cleaned


def _is_design_system_yaml_document(text: str) -> bool:
    """Return true when text is a parseable design-system YAML artifact."""
    stripped = text.strip()
    if not stripped:
        return False
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:ya?ml)?\s*", "", stripped, flags=re.IGNORECASE).strip()
        stripped = re.sub(r"\s*```$", "", stripped).strip()
    try:
        parsed = yaml.safe_load(stripped)
    except yaml.YAMLError:
        return False
    return isinstance(parsed, dict) and parsed.get("type") == "design_system"


def _parse_design_system_yaml_document(text: str) -> dict | None:
    """Parse a pure design-system YAML artifact."""
    stripped = text.strip()
    if not stripped:
        return None
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:ya?ml)?\s*", "", stripped, flags=re.IGNORECASE).strip()
        stripped = re.sub(r"\s*```$", "", stripped).strip()
    try:
        parsed = yaml.safe_load(stripped)
    except yaml.YAMLError:
        return None
    if isinstance(parsed, dict) and parsed.get("type") == "design_system":
        return parsed
    return None


def _has_yaml_front_matter(text: str) -> bool:
    stripped = text.lstrip()
    if not stripped.startswith("---\n"):
        return False
    return bool(re.search(r"\n---\s*(?:\n|$)", stripped[4:]))


def _scalar_summary(value) -> str:
    if value is None:
        return "`null`"
    if isinstance(value, bool):
        return "`true`" if value else "`false`"
    if isinstance(value, (int, float)):
        return f"`{value}`"
    text = str(value).strip()
    if not text:
        return "`\"\"`"
    if len(text) > 180:
        text = text[:177].rstrip() + "..."
    return f"`{text}`"


def _flatten_token_entries(value, prefix: str = "", limit: int = 80) -> list[str]:
    entries: list[str] = []
    if not isinstance(value, dict):
        return entries
    for key, child in value.items():
        name = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(child, dict):
            scalar_children = {k: v for k, v in child.items() if not isinstance(v, (dict, list))}
            if scalar_children:
                summary = ", ".join(
                    f"{k}: {str(v).strip()}" for k, v in list(scalar_children.items())[:5]
                )
                entries.append(f"- `{name}`: {summary}")
            entries.extend(_flatten_token_entries(child, name, limit=max(0, limit - len(entries))))
        elif isinstance(child, list):
            entries.append(f"- `{name}`: {len(child)} item(s)")
        else:
            entries.append(f"- `{name}`: {child}")
        if len(entries) >= limit:
            entries.append("- Additional token entries are preserved in the YAML front matter.")
            break
    return entries


def _append_mapping_summary(lines: list[str], mapping: dict, *, limit: int = 24) -> None:
    count = 0
    for key, value in mapping.items():
        if count >= limit:
            lines.append("- Additional entries are preserved in the YAML front matter.")
            return
        count += 1
        if isinstance(value, dict):
            summary_parts = []
            for field in (
                "value",
                "role",
                "kind",
                "fontFamily",
                "fontSize",
                "fontWeight",
                "lineHeight",
                "widthBehavior",
                "confidence",
            ):
                if field in value and value[field] not in (None, "", [], {}):
                    summary_parts.append(f"{field}: {value[field]}")
            if "text" in value and isinstance(value["text"], dict):
                text_summary = ", ".join(
                    f"{k}: {v}" for k, v in list(value["text"].items())[:3] if v not in (None, "")
                )
                if text_summary:
                    summary_parts.append(f"text: {text_summary}")
            if "variants" in value and isinstance(value["variants"], dict):
                summary_parts.append("variants: " + ", ".join(list(value["variants"].keys())[:6]))
            if not summary_parts:
                summary_parts = [f"{len(value)} nested field(s)"]
            lines.append(f"- `{key}`: " + "; ".join(str(part).strip() for part in summary_parts))
        elif isinstance(value, list):
            lines.append(f"- `{key}`: {len(value)} item(s)")
        else:
            lines.append(f"- `{key}`: {value}")


def _append_list_summary(lines: list[str], values, *, limit: int = 12) -> None:
    if not isinstance(values, list) or not values:
        lines.append("- None specified.")
        return
    for index, value in enumerate(values[:limit], start=1):
        if isinstance(value, dict):
            preferred = (
                value.get("rule")
                or value.get("description")
                or value.get("guidance")
                or value.get("name")
                or value.get("usage")
            )
            if preferred:
                lines.append(f"- {preferred}")
            else:
                compact = ", ".join(
                    f"{k}: {v}" for k, v in list(value.items())[:4] if not isinstance(v, (dict, list))
                )
                lines.append(f"- {compact or f'Nested rule {index}'}")
        else:
            lines.append(f"- {value}")
    if len(values) > limit:
        lines.append("- Additional entries are preserved in the YAML front matter.")


def _design_system_markdown_body(parsed: dict) -> str:
    metadata = parsed.get("metadata") if isinstance(parsed.get("metadata"), dict) else {}
    lines: list[str] = ["# Design System", "", "## Overview"]
    name = metadata.get("name") or parsed.get("name")
    description = metadata.get("description") or parsed.get("description")
    if name:
        lines.append(f"- Name: `{name}`")
    if description:
        lines.append(f"- {description}")
    if metadata.get("confidence"):
        lines.append(f"- Confidence: `{metadata.get('confidence')}`")
    if parsed.get("schema_version"):
        lines.append(f"- Schema: `{parsed.get('schema_version')}`")

    surfaces = parsed.get("surfaces")
    if isinstance(surfaces, dict) and surfaces:
        lines.extend(["", "## Surface System"])
        _append_mapping_summary(lines, surfaces, limit=28)

    tokens = parsed.get("tokens")
    if isinstance(tokens, dict) and tokens:
        lines.extend(["", "## Tokens"])
        for category, category_value in tokens.items():
            lines.extend(["", f"### {str(category).replace('_', ' ').title()}"])
            entries = _flatten_token_entries(category_value, str(category), limit=40)
            lines.extend(entries or ["- No explicit entries."])

    typography = parsed.get("typography")
    if isinstance(typography, dict) and typography:
        lines.extend(["", "## Typography"])
        _append_mapping_summary(lines, typography, limit=28)

    components = parsed.get("components")
    if isinstance(components, dict) and components:
        lines.extend(["", "## Components"])
        _append_mapping_summary(lines, components, limit=36)

    patterns = parsed.get("patterns")
    if isinstance(patterns, dict) and patterns:
        lines.extend(["", "## Patterns"])
        for category, values in patterns.items():
            lines.extend(["", f"### {str(category).replace('_', ' ').title()}"])
            _append_list_summary(lines, values, limit=12)

    imagery = parsed.get("imagery")
    if isinstance(imagery, dict) and imagery:
        lines.extend(["", "## Imagery"])
        for category, value in imagery.items():
            lines.extend(["", f"### {str(category).replace('_', ' ').title()}"])
            if isinstance(value, dict):
                for field in (
                    "observed",
                    "creativeDirection",
                    "density",
                    "simplicity",
                    "rendering",
                    "paletteRelationship",
                    "surfaceRelationship",
                    "edgeAndScale",
                    "subjectPolicy",
                ):
                    if field in value and value[field] not in (None, "", [], {}):
                        lines.append(f"- {field}: {_scalar_summary(value[field])}")
                if isinstance(value.get("avoid"), list) and value["avoid"]:
                    lines.append("- Avoid: " + "; ".join(str(item) for item in value["avoid"][:8]))
            else:
                lines.append(f"- {value}")

    rules = parsed.get("rules")
    if isinstance(rules, dict) and rules:
        lines.extend(["", "## Rules"])
        for category, values in rules.items():
            lines.extend(["", f"### {str(category).replace('_', ' ').title()}"])
            _append_list_summary(lines, values, limit=10)

    for key, title in (
        ("do_not_generalize", "Do Not Generalize"),
        ("embedded_showcase_only", "Embedded Showcase Only"),
        ("open_questions", "Open Questions"),
    ):
        values = parsed.get(key)
        if isinstance(values, list) and values:
            lines.extend(["", f"## {title}"])
            _append_list_summary(lines, values, limit=14)

    return "\n".join(lines).rstrip() + "\n"


def coerce_design_system_markdown_document(content: str) -> str:
    """Save design systems as Markdown with YAML front matter and categorized body."""
    stripped = content.strip()
    if _has_yaml_front_matter(stripped):
        return stripped.rstrip() + "\n"
    parsed = _parse_design_system_yaml_document(stripped)
    if not parsed:
        return stripped.rstrip() + "\n"
    yaml_block = yaml.safe_dump(parsed, sort_keys=False, allow_unicode=False, width=120).rstrip()
    return f"---\n{yaml_block}\n---\n\n{_design_system_markdown_body(parsed)}"


def design_system_artifact_path(mode_dir: Path) -> Path:
    """Return the canonical design-system artifact path for a mode directory."""
    yaml_path = mode_dir / "design-system.yaml"
    if yaml_path.exists():
        return yaml_path
    return mode_dir / "design-system.md"


def write_design_system_artifacts(mode_dir: Path, content: str) -> Path:
    """Write design-system content as Markdown with a machine-readable YAML header."""
    canonical_path = mode_dir / "design-system.md"
    canonical_path.write_text(coerce_design_system_markdown_document(content))
    legacy_yaml_path = mode_dir / "design-system.yaml"
    if legacy_yaml_path.exists():
        legacy_yaml_path.unlink()
    return canonical_path


def build_layouts_artifact(structural_analysis: str) -> str:
    """Extract source-specific layout definitions into a separate YAML artifact."""
    text = re.sub(r"^```(?:ya?ml)?\s*|\s*```$", "", structural_analysis.strip(), flags=re.IGNORECASE)
    if not text:
        return ""
    try:
        parsed = yaml.safe_load(text)
    except yaml.YAMLError:
        return ""
    if not isinstance(parsed, dict) or parsed.get("type") != "normalized_site_ast":
        return ""

    sections = []
    for section in parsed.get("sections") or []:
        if not isinstance(section, dict):
            continue
        layout_nodes = []
        for node in section.get("normalized_nodes") or []:
            if not isinstance(node, dict):
                continue
            relationships = node.get("relationships") if isinstance(node.get("relationships"), dict) else {}
            layout_signature = node.get("layout_signature") or ""
            placement = relationships.get("placement") or ""
            width_behavior = relationships.get("width_behavior") or ""
            kind = node.get("kind") or ""
            if not any((layout_signature, placement, width_behavior)) and kind not in {"container", "group", "grid", "card", "panel", "media", "graphic", "background"}:
                continue
            layout_nodes.append(
                {
                    "id": node.get("id") or "",
                    "kind": kind,
                    "role": node.get("role") or "",
                    "layout_signature": layout_signature,
                    "surface_role": node.get("surface_role") or "",
                    "width_behavior": width_behavior,
                    "placement": placement,
                    "component_candidate": node.get("component_candidate") or "",
                    "pattern_candidate": node.get("pattern_candidate") or "",
                    "provenance": node.get("provenance") or {},
                }
            )
        sections.append(
            {
                "id": section.get("id") or "",
                "section_index": ((section.get("source") or {}).get("section_index") if isinstance(section.get("source"), dict) else None),
                "role": section.get("role") or "",
                "bounds": ((section.get("source") or {}).get("bounds") if isinstance(section.get("source"), dict) else {}),
                "layout_nodes": layout_nodes,
                "pattern_candidates": section.get("pattern_candidates") or [],
            }
        )

    global_observations = parsed.get("global_observations") if isinstance(parsed.get("global_observations"), dict) else {}
    payload = {
        "schema_version": "source_layouts.v1",
        "type": "source_layouts",
        "source": "normalized_site_ast",
        "purpose": "Source-specific section order and component positioning. Keep this separate from reusable design-system patterns.",
        "sections": sections,
        "global_layout_signatures": global_observations.get("layout_signatures") or [],
        "surface_relationships": global_observations.get("surface_relationships") or [],
        "do_not_use_as_design_system": [
            "Do not copy this exact section list, section order, or one-off component positions into design-system tokens.",
            "Use design-system patterns for reusable generation; use this file only when exact source reconstruction is explicitly requested.",
        ],
    }
    return yaml.safe_dump(payload, sort_keys=False, allow_unicode=False)


def write_layouts_artifact(mode_dir: Path, structural_analysis: str) -> Path | None:
    layouts = build_layouts_artifact(structural_analysis)
    if not layouts.strip():
        return None
    path = mode_dir / "layouts.yaml"
    path.write_text(layouts)
    return path


def collect_section_grounding_markdown(output_dir: str | Path | None) -> str:
    """Read cached per-section grounding artifacts as a detailed synthesis/color-sync reference."""
    if not output_dir:
        return ""
    section_dir = Path(output_dir) / "section-groundings"
    if not section_dir.exists():
        return ""

    blocks: list[str] = []
    paths = sorted(section_dir.glob("*.yaml"))
    if not paths:
        paths = sorted(section_dir.glob("*.md"))
    for path in paths:
        text = path.read_text().strip()
        if not text:
            continue
        blocks.append(f"## {path.stem}\n\n{text}")
    return "\n\n---\n\n".join(blocks)


def compact_section_grounding_for_surface_map(section_grounding_markdown: str, max_chars: int = 28000) -> str:
    """Keep the surface/color/component facts needed by the intermediate map without sending every word."""
    if not section_grounding_markdown.strip():
        return ""

    keep_patterns = re.compile(
        r"(surface|background|gradient|color|colour|heading|display|body|paragraph|copy|"
        r"button|cta|eyebrow|badge|chip|tag|label|card|panel|tray|border|divider|shadow|"
        r"glow|image|graphic|component color|surface-specific|textTransform|uppercase|all-caps|"
        r"parent/child|host surface|nested)",
        flags=re.IGNORECASE,
    )
    blocks: list[str] = []
    current_heading = ""
    for raw_line in section_grounding_markdown.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            current_heading = stripped
            blocks.append(stripped)
            continue
        if keep_patterns.search(stripped):
            if current_heading and (not blocks or blocks[-1] != current_heading) and len(blocks) < 2:
                blocks.append(current_heading)
            blocks.append(line)

    compacted = "\n".join(blocks)
    if len(compacted) <= max_chars:
        return compacted

    # Keep top-to-bottom coverage. The review agent penalizes facts that are not
    # traceable to the compacted grounding, so preserve every section before
    # trimming within a section.
    lines = compacted.splitlines()
    if not lines:
        return compacted[:max_chars]

    groups: list[list[str]] = []
    current_group: list[str] = []
    for line in lines:
        if line.startswith("## ") and current_group:
            groups.append(current_group)
            current_group = [line]
        else:
            current_group.append(line)
    if current_group:
        groups.append(current_group)

    if len(groups) > 1:
        per_group_budget = max(400, max_chars // len(groups))
        selected_groups: list[str] = []
        for group in groups:
            group_selected: list[str] = []
            total = 0
            for line in group:
                # Keep headings intact; clip long evidence lines.
                line_budget = 180 if not line.startswith("#") else 260
                clipped = line if len(line) <= line_budget else line[: line_budget - 3].rstrip() + "..."
                if total + len(clipped) + 1 > per_group_budget:
                    break
                group_selected.append(clipped)
                total += len(clipped) + 1
            selected_groups.append("\n".join(group_selected))

        section_preserving = "\n".join(selected_groups)
        if len(section_preserving) <= max_chars:
            return section_preserving
        return section_preserving[:max_chars].rstrip() + "\n"

    # Fallback for unsectioned input: sample evenly through retained lines.
    budget_per_line = max(1, max_chars // max(len(lines), 1))
    selected: list[str] = []
    total = 0
    for line in lines:
        clipped = line if len(line) <= budget_per_line * 3 else line[: budget_per_line * 3].rstrip() + "..."
        if total + len(clipped) + 1 > max_chars:
            break
        selected.append(clipped)
        total += len(clipped) + 1
    return "\n".join(selected)


def build_surface_component_map_from_grounding(
    structural_analysis: str,
    section_grounding_markdown: str,
    source_color_report: str | None = None,
) -> str:
    """Create a deterministic intermediate map of surface/component facts from grounded markdown."""
    hex_pattern = re.compile(r"#(?:[0-9A-Fa-f]{3,8})\b|rgba?\([^)]*\)|linear-gradient\([^)]*\)|radial-gradient\([^)]*\)")

    def clean_fact(text: str, max_len: int = 360) -> str:
        text = re.sub(r"\s+", " ", text).strip()
        text = text.strip("- ")
        if len(text) > max_len:
            return text[: max_len - 3].rstrip() + "..."
        return text or "not explicit"

    def normalize_values(text: str) -> list[str]:
        values: list[str] = []
        for value in hex_pattern.findall(text or ""):
            normalized = value.upper() if value.startswith("#") else value
            if normalized not in values:
                values.append(normalized)
        return values

    def append_unique(items: list[str], item: str, max_len: int = 360) -> None:
        fact = clean_fact(item, max_len=max_len)
        if fact and fact != "not explicit" and fact not in items:
            items.append(fact)

    def parse_field_lines(lines_for_parse: list[str]) -> dict[str, list[str]]:
        fields: dict[str, list[str]] = {}
        current_key: str | None = None
        for raw_line in lines_for_parse:
            stripped = raw_line.strip()
            match = re.match(r"^-\s+\*\*([^:*]+):\*\*\s*(.*)$", stripped)
            if match:
                current_key = match.group(1).strip()
                fields.setdefault(current_key, [])
                append_unique(fields[current_key], match.group(2), max_len=520)
                continue
            if current_key and stripped and not stripped.startswith("#") and not re.match(r"^-\s+\*\*", stripped):
                append_unique(fields[current_key], stripped, max_len=520)
        return fields

    def first_field(fields: dict[str, list[str]], *keys: str) -> str:
        for key in keys:
            values = fields.get(key) or []
            if values:
                return values[0]
        return "not explicit"

    def join_field(fields: dict[str, list[str]], *keys: str, max_items: int = 2, max_len: int = 520) -> str:
        values: list[str] = []
        for key in keys:
            for value in fields.get(key) or []:
                append_unique(values, value, max_len=max_len)
        return "; ".join(values[:max_items]) if values else "none observed"

    def slugify(text: str, fallback: str) -> str:
        return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or fallback

    def component_kind(name: str, fields: dict[str, list[str]]) -> str:
        name_l = name.lower()
        if re.search(r"\b(divider|rule|separator|stroke|line)\b", name_l):
            return "edge-divider"
        if re.search(r"\b(logo|photo|image|graphic|illustration|media|mark|avatar|device|mockup|background|ornament|motif|ribbon|sash)\b", name_l):
            if not re.search(r"\b(button|cta|link|nav|navigation|tab|control)\b", name_l):
                return "graphic-media"
        if re.search(r"\b(button|cta|eyebrow|badge|chip|tag|pill|tab|selector|link|nav|status|label)\b", name_l):
            return "control"
        if re.search(r"\b(card|panel|tray|tile|quote|testimonial|pricing|table|accordion|faq)\b", name_l):
            return "card-panel"
        if re.search(r"\b(heading|display|title|headline|h1|h2)\b", name_l):
            return "heading-text"
        if re.search(r"\b(paragraph|supporting|body|copy|caption|legal|description)\b", name_l):
            return "body-text"
        if re.search(r"\b(stack|group|row|wrapper|container|layout|grid|cluster|column|cell|shell|item|block)\b", name_l):
            return "layout-content"
        surface_relationship = " ".join(fields.get("Surface relationship", [])).lower()
        fill = " ".join(fields.get("Background / fill", [])).lower()
        if re.search(r"\b(card|panel|tray|tile)\b", surface_relationship) and not re.search(r"\b(no fill|transparent|same-surface)\b", fill):
            return "card-panel"
        return "layout-content"

    def text_role_for_component(component: dict) -> str | None:
        name = component["name"].lower()
        typography = first_field(component["fields"], "Typography style")
        if typography == "not explicit" or re.search(r"^none\b|none observed|not readable UI text|logo art", typography, re.IGNORECASE):
            return None
        haystack = f"{name} {typography}".lower()
        if re.search(r"\b(mixed|contains|combines)\b", haystack) and re.search(r"\b(heading|body|paragraph|button|label|copy)\b", haystack):
            return "mixed-text-group"
        if re.search(r"\b(heading|display|headline|h1|h2|numeral|value|metric)\b", haystack) or re.search(r"\btitle\b", name):
            return "heading-text"
        if re.search(r"\b(paragraph|supporting|body|copy|description|legal|caption)\b", haystack):
            return "body-text"
        if re.search(r"\b(button|nav|link|label|eyebrow|badge|chip|tag|status|tab)\b", haystack):
            return "label-control-text"
        return "text"

    def parse_section_block(block: str, index: int) -> dict:
        block_lines = [line.rstrip() for line in block.splitlines()]
        wrapper_heading = next(
            (line.lstrip("# ").strip() for line in block_lines if line.startswith("## ")),
            f"section-{index:02d}",
        )
        section_title = next(
            (
                re.sub(r"^#+\s*", "", line).strip()
                for line in block_lines
                if re.match(r"^##\s+Section\b", line)
            ),
            wrapper_heading,
        )
        component_start = next(
            (line_index for line_index, line in enumerate(block_lines) if line.startswith("#### Component:")),
            len(block_lines),
        )
        top_lines = block_lines[:component_start]
        section_fields = parse_field_lines(top_lines)
        components: list[dict] = []
        component_indices = [
            line_index for line_index, line in enumerate(block_lines) if line.startswith("#### Component:")
        ]
        for offset, start in enumerate(component_indices):
            end = component_indices[offset + 1] if offset + 1 < len(component_indices) else len(block_lines)
            component_lines = block_lines[start:end]
            name = component_lines[0].split(":", 1)[1].strip() if ":" in component_lines[0] else "component"
            fields = parse_field_lines(component_lines[1:])
            components.append({
                "name": name,
                "slug": slugify(name, f"component-{offset + 1:02d}"),
                "kind": component_kind(name, fields),
                "fields": fields,
            })

        summary_index = next(
            (line_index for line_index, line in enumerate(block_lines) if line.startswith("### Section Reuse Summary")),
            len(block_lines),
        )
        summary_fields = parse_field_lines(block_lines[summary_index:])
        return {
            "section_title": section_title,
            "slug": slugify(wrapper_heading, f"section-{index:02d}"),
            "fields": section_fields,
            "components": components,
            "summary": summary_fields,
        }

    raw_blocks = re.split(r"\n\s*---\s*\n", section_grounding_markdown.strip()) if section_grounding_markdown.strip() else []
    sections = [parse_section_block(block, index) for index, block in enumerate(raw_blocks, start=1) if block.strip()]

    lines: list[str] = [
        "# Surface Component Map",
        "",
        "## Surface Inventory",
        "",
        "- This deterministic map normalizes the section grounding into host surfaces and their actual nested components.",
        "- Section-local names are evidence labels only; design-system synthesis must translate them into generic reusable surface roles.",
        "- Empty component categories mean no visible instance was grounded in that section.",
        "",
    ]
    critical: list[str] = []
    ambiguities: list[str] = []

    for section in sections:
        section_fields = section["fields"]
        summary_fields = section["summary"]
        components = section["components"]
        observed_backgrounds: list[str] = []
        child_surface_values: list[str] = []
        for source_text in [
            first_field(section_fields, "Background"),
        ]:
            for value in normalize_values(source_text):
                if value not in observed_backgrounds:
                    observed_backgrounds.append(value)
        for component in components:
            component_fields = component["fields"]
            for key in ("Background / fill", "Border / edge style", "Depth / elevation"):
                for value in normalize_values(join_field(component_fields, key, max_items=1)):
                    if value not in child_surface_values:
                        child_surface_values.append(value)

        control_components = [component for component in components if component["kind"] == "control"]
        card_components = [component for component in components if component["kind"] == "card-panel"]
        heading_components = [component for component in components if text_role_for_component(component) == "heading-text"]
        body_components = [component for component in components if text_role_for_component(component) == "body-text"]
        graphic_components = [component for component in components if component["kind"] == "graphic-media"]
        divider_components = [component for component in components if component["kind"] == "edge-divider"]
        layout_components = [component for component in components if component["kind"] == "layout-content"]
        text_role_components = [
            (component, text_role_for_component(component))
            for component in components
            if text_role_for_component(component)
        ]

        do_not_generalize: list[str] = []
        for key in ("Embedded or showcase-only UI", "Not-observed common components"):
            for value in summary_fields.get(key, []):
                append_unique(do_not_generalize, value, max_len=420)
        for component in components:
            haystack = f"{component['name']} {join_field(component['fields'], 'Typography style', 'Image / graphic creative direction', max_items=2)}"
            if re.search(r"\b(logo art|decorative|background layer|showcase|embedded|not page-copy|not readable UI text)\b", haystack, re.IGNORECASE):
                append_unique(do_not_generalize, f"{component['name']}: treat as {component['kind']}, not as a generic text/control recipe.", max_len=360)

        lines.extend([
            f"### {section['slug']}",
            f"- `sectionRole`: {clean_fact(section['section_title'])}",
            f"- `hostSurface`: background={first_field(section_fields, 'Background')}; edge={first_field(section_fields, 'Local edge / transition behavior')}; border={first_field(section_fields, 'Border style')}",
            f"- `observedHostValues`: {', '.join(observed_backgrounds[:12]) if observed_backgrounds else 'not explicit'}",
            f"- `childSurfaceValues`: {', '.join(child_surface_values[:16]) if child_surface_values else 'none observed'}",
            f"- `surfaceRelationshipSummary`: {join_field(section_fields, 'Surface relationships', max_items=2)}",
            f"- `spacingRhythm`: {join_field(section_fields, 'Spacing / density mechanics', 'Content rhythm', max_items=2)}",
            f"- `defaultHeadingRecipe`: {join_field(heading_components[0]['fields'], 'Typography style', max_items=1) if heading_components else 'none observed'}",
            f"- `defaultBodyRecipe`: {join_field(body_components[0]['fields'], 'Typography style', max_items=1) if body_components else 'none observed'}",
            f"- `sectionGraphics`: {join_field(section_fields, 'Decorative placement', max_items=1)}",
            f"- `edgesDepth`: {join_field(section_fields, 'Border style', 'Divider style', 'Local edge / transition behavior', max_items=3)}",
            f"- `doNotGeneralize`: {'; '.join(do_not_generalize[:4]) if do_not_generalize else 'none observed'}",
            "",
            "#### Canonical Host Child Matrix",
            f"- `host`: {clean_fact(first_field(section_fields, 'Background'), 420)}",
            f"- `headingTextChildren`: {', '.join(f'`{component['slug']}`' for component, role in text_role_components if role == 'heading-text') or 'none observed'}",
            f"- `bodyTextChildren`: {', '.join(f'`{component['slug']}`' for component, role in text_role_components if role == 'body-text') or 'none observed'}",
            f"- `mixedTextGroups`: {', '.join(f'`{component['slug']}`' for component, role in text_role_components if role == 'mixed-text-group') or 'none observed'}",
            f"- `labelControlTextChildren`: {', '.join(f'`{component['slug']}`' for component, role in text_role_components if role == 'label-control-text') or 'none observed'}",
            f"- `controls`: {', '.join(f'`{component['slug']}`' for component in control_components) if control_components else 'none observed'}",
            f"- `cardsPanels`: {', '.join(f'`{component['slug']}`' for component in card_components) if card_components else 'none observed'}",
            f"- `graphicsMedia`: {', '.join(f'`{component['slug']}`' for component in graphic_components) if graphic_components else 'none observed'}",
            f"- `dividersEdges`: {', '.join(f'`{component['slug']}`' for component in divider_components) if divider_components else clean_fact(join_field(section_fields, 'Divider style', 'Border style', max_items=2), 260)}",
            "",
            "#### Component Recipes",
        ])

        if not components:
            lines.append("- `none`: no nested components parsed.")
        for component in components:
            fields = component["fields"]
            lines.extend([
                f"- `{component['slug']}` ({component['kind']}):",
                f"  - `hostSurface`: {first_field(fields, 'Host surface')}",
                f"  - `fill`: {first_field(fields, 'Background / fill')}",
                f"  - `relationship`: {first_field(fields, 'Surface relationship')}",
                f"  - `textTypography`: {first_field(fields, 'Typography style')}",
                f"  - `borderEdge`: {first_field(fields, 'Border / edge style')}",
                f"  - `divider`: {first_field(fields, 'Divider style')}",
                f"  - `depth`: {first_field(fields, 'Depth / elevation')}",
                f"  - `sizing`: {first_field(fields, 'Width / sizing behavior')}",
                f"  - `graphicMedia`: {join_field(fields, 'Image / graphic creative direction', 'Graphic placement / edge behavior', max_items=2)}",
            ])
            text_values = normalize_values(first_field(fields, "Typography style"))
            fill_values = normalize_values(first_field(fields, "Background / fill"))
            host_values = normalize_values(first_field(fields, "Host surface"))
            border_values = normalize_values(first_field(fields, "Border / edge style"))
            if text_values or fill_values or host_values or border_values:
                critical.append(
                    f"- `{section['slug']}` / `{component['slug']}` ({component['kind']}): "
                    f"host={clean_fact(first_field(fields, 'Host surface'), 220)}; "
                    f"fill={clean_fact(first_field(fields, 'Background / fill'), 220)}; "
                    f"text={clean_fact(first_field(fields, 'Typography style'), 260)}; "
                    f"border={clean_fact(first_field(fields, 'Border / edge style'), 180)}"
                )
        lines.append("#### Component Kind Index")
        lines.append(f"- `layout-content`: {', '.join(f'`{component['slug']}`' for component in layout_components) if layout_components else 'none observed'}")
        lines.append(f"- `heading-text`: {', '.join(f'`{component['slug']}`' for component in heading_components) if heading_components else 'none observed'}")
        lines.append(f"- `body-text`: {', '.join(f'`{component['slug']}`' for component in body_components) if body_components else 'none observed'}")
        lines.append(f"- `control`: {', '.join(f'`{component['slug']}`' for component in control_components) if control_components else 'none observed'}")
        lines.append(f"- `card-panel`: {', '.join(f'`{component['slug']}`' for component in card_components) if card_components else 'none observed'}")
        lines.append(f"- `graphic-media`: {', '.join(f'`{component['slug']}`' for component in graphic_components) if graphic_components else 'none observed'}")
        lines.append(f"- `edge-divider`: {', '.join(f'`{component['slug']}`' for component in divider_components) if divider_components else 'none observed'}")

        for summary_key in ("Surface-specific recipes", "Component color relationships"):
            for value in summary_fields.get(summary_key, [])[:4]:
                critical.append(f"- `{section['slug']}` / `summary-{slugify(summary_key, 'summary')}`: {clean_fact(value, 520)}")

        if re.search(r"\b(unclear|low confidence|conflict|approx)\b", "\n".join(section_fields.get("Background", [])), re.IGNORECASE):
            ambiguities.append(f"{section['slug']}: host surface has approximate or ambiguous background evidence.")
        lines.append("")

    if not critical:
        structural_compact = compact_section_grounding_for_surface_map(structural_analysis, max_chars=12000)
        for line in structural_compact.splitlines():
            if hex_pattern.search(line) and re.search(r"(surface|heading|body|button|card|border|shadow)", line, re.IGNORECASE):
                critical.append(f"- `merged-grounding` -> `pairing`: {line.strip()}")

    lines.extend([
        "## Critical Color Pairings",
        "",
        *(critical[:160] or ["- No explicit critical color pairings extracted."]),
        "",
        "## Ambiguities",
        "",
    ])
    if source_color_report:
        lines.append("- Source CSS values should be used only when they visually preserve the grounded pairing above.")
    if ambiguities:
        lines.extend(f"- {item}" for item in ambiguities[:40])
    else:
        lines.append("- Ambiguities are inherited from the section-level grounding when lines above say `unclear`, `low confidence`, or `one-off`.")
    return "\n".join(lines).rstrip() + "\n"


def combine_grounding_references(
    structural_analysis: str,
    section_grounding_markdown: str | None = None,
) -> str:
    """Combine merged grounding and section-level grounding for downstream correction steps."""
    if not section_grounding_markdown or not section_grounding_markdown.strip():
        return structural_analysis
    return (
        f"{structural_analysis.strip()}\n\n"
        "## Detailed Section Grounding Reference\n\n"
        f"{section_grounding_markdown.strip()}"
    )


def strip_echoed_source_style_report(markdown: str) -> str:
    """Remove source CSS reference material if a sync model echoes it into output."""
    pattern = re.compile(
        r"(?ms)^## Source CSS (?:Color|Style) Report\s*\n\s*# Source CSS Styles\b.*\Z"
    )
    return pattern.sub("", markdown).rstrip()


def synchronize_grounding_styles(
    structural_analysis: str,
    source_style_report: str,
    config: AppConfig,
    grounding_sync_prompt: str | None = None,
    preferred_color_replacements: dict[str, str] | None = None,
) -> str:
    """Replace approximate grounding colors/typography using source CSS styles."""
    provider = get_provider(config)
    replacement_instructions = ""
    if preferred_color_replacements:
        replacement_lines = [
            "## Deterministic Explicit Color Replacements",
            "",
            "These explicit approximate colors were matched in code to the nearest source-backed colors using perceptual distance. Preserve these exact replacements unless the source style report makes them impossible.",
            "",
        ]
        for original, replacement in sorted(preferred_color_replacements.items()):
            replacement_lines.append(f"- `{original}` -> `{replacement}`")
        replacement_instructions = "\n".join(replacement_lines) + "\n\n"
    user_prompt = (
        replacement_instructions
        + 
        "## Structural Grounding Markdown\n\n"
        f"{structural_analysis}\n\n"
        "## Source CSS Style Report\n\n"
        f"{source_style_report}"
    )
    token_limits = [
        max(config.max_tokens, 16384),
        max(config.max_tokens, 24576),
        max(config.max_tokens, 32768),
    ]
    last_cleaned = ""
    for token_limit in dict.fromkeys(token_limits):
        result = provider.text_query(
            system_prompt=grounding_sync_prompt or DEFAULT_GROUNDING_SYNC_PROMPT,
            user_prompt=user_prompt,
            max_tokens=token_limit,
        )
        cleaned = clean_markdown(result)
        last_cleaned = cleaned
        if grounding_document_is_complete(cleaned):
            return cleaned
    raise ValueError(
        "Synced grounding was incomplete or truncated"
        + (f"; tail={last_cleaned[-200:]}" if last_cleaned else "")
    )


def enforce_source_color_literals(
    design_system: str,
    extracted_source_colors: dict,
    config: AppConfig,
    color_sync_prompt: str | None = None,
    grounding_markdown: str | None = None,
    source_style_ledger: dict | None = None,
    audit_path: Path | None = None,
    max_passes: int = 2,
) -> str:
    """Ensure design-system colors come from source HTML or grounded screenshot evidence."""
    synced = design_system
    previous_unsupported: list[str] | None = None
    source_color_report = render_source_color_report(extracted_source_colors)
    grounding_allowed = {
        literal.strip()
        for literal in extract_document_color_literals(grounding_markdown or "")
        if literal.strip()
    }
    ledger_audit = None
    if source_style_ledger:
        synced, ledger_audit = reconcile_document_styles(
            synced,
            extracted_source_colors,
            source_style_ledger,
            allowed_approximate_literals=grounding_allowed,
        )
        if audit_path:
            write_style_audit(audit_path, ledger_audit)
        remaining = ledger_audit.get("after", {}).get("unsupported_colors", [])
        if not remaining:
            return synced

    deterministic_replacements = {
        literal: replacement
        for literal, replacement in suggest_nearest_source_color_replacements(synced, extracted_source_colors).items()
        if literal not in grounding_allowed
    }
    if deterministic_replacements:
        candidate = apply_document_color_replacements(synced, deterministic_replacements)
        remaining = [
            literal
            for literal in find_non_source_document_colors(candidate, extracted_source_colors)
            if literal not in grounding_allowed
        ]
        if not remaining:
            return candidate
        if _is_design_system_yaml_document(candidate):
            synced = candidate

    for _ in range(max_passes):
        unsupported = [
            literal
            for literal in find_non_source_document_colors(synced, extracted_source_colors)
            if literal not in grounding_allowed
        ]
        if not unsupported:
            return synced
        if previous_unsupported == unsupported:
            break
        previous_unsupported = unsupported
        prior = synced
        synced = synchronize_design_system_colors(
            synced,
            source_color_report=source_color_report,
            config=config,
            color_sync_prompt=(
                (color_sync_prompt or DEFAULT_COLOR_SYNC_PROMPT)
                + "\n\nUnsupported explicit values currently present in the markdown:\n"
                + "\n".join(f"- `{value}`" for value in unsupported)
            ),
            grounding_markdown=grounding_markdown,
        )
        if _is_design_system_yaml_document(prior) and synced.strip() == prior.strip():
            replacements = suggest_nearest_source_color_replacements(prior, extracted_source_colors)
            replacements = {literal: replacement for literal, replacement in replacements.items() if literal in unsupported}
            candidate = apply_document_color_replacements(prior, replacements)
            if candidate.strip() != prior.strip() and _is_design_system_yaml_document(candidate):
                synced = candidate
        if synced.strip() == prior.strip():
            break

    if source_style_ledger and audit_path:
        final_audit = audit_document_styles(
            synced,
            extracted_source_colors,
            source_style_ledger,
            allowed_approximate_literals=grounding_allowed,
        )
        if isinstance(ledger_audit, dict):
            ledger_audit = {**ledger_audit, "final_after_model_fallback": final_audit}
            write_style_audit(audit_path, ledger_audit)
        else:
            write_style_audit(audit_path, final_audit)

    return synced


def enforce_source_grounding_styles(
    structural_analysis: str,
    extracted_source_styles: dict,
    config: AppConfig,
    grounding_sync_prompt: str | None = None,
    max_passes: int = 2,
) -> str:
    """Ensure explicit grounding colors come from source HTML and typography is synced when possible."""
    synced = structural_analysis
    previous_unsupported: list[str] | None = None
    source_style_report = render_source_color_report(extracted_source_styles)
    deterministic_color_replacements = suggest_nearest_source_color_replacements(
        synced,
        extracted_source_styles,
    )
    if deterministic_color_replacements:
        synced = apply_document_color_replacements(synced, deterministic_color_replacements)
    unsupported = find_non_source_document_colors(synced, extracted_source_styles)

    # Large grounding documents with many approximate literals are expensive to resync
    # and currently prone to long Anthropic stalls. In that case, keep the merged
    # grounding intact and let downstream generation continue.
    if len(unsupported) > 20:
        return synced

    for _ in range(max_passes):
        unsupported = find_non_source_document_colors(synced, extracted_source_styles)
        if not unsupported:
            return synced
        if previous_unsupported == unsupported:
            break
        previous_unsupported = unsupported
        prior = synced
        synced = synchronize_grounding_styles(
            synced,
            source_style_report=source_style_report,
            config=config,
            grounding_sync_prompt=(
                (grounding_sync_prompt or DEFAULT_GROUNDING_SYNC_PROMPT)
                + "\n\nUnsupported explicit color values currently present in the grounding:\n"
                + "\n".join(f"- `{value}`" for value in unsupported)
            ),
            preferred_color_replacements=deterministic_color_replacements,
        )
        if synced.strip() == prior.strip():
            break

    return synced


def synchronize_generated_site_styles(
    html: str,
    generation_markdown: str,
    source_style_report: str,
    config: AppConfig,
    site_style_sync_prompt: str | None = None,
) -> str:
    """Rewrite generated HTML so explicit visual values match source CSS styles."""
    provider = get_provider(config)
    result = provider.text_query(
        system_prompt=site_style_sync_prompt or DEFAULT_SITE_STYLE_SYNC_PROMPT,
        user_prompt=(
            "## Generated HTML\n\n"
            f"{html}\n\n"
            "## Source Markdown Artifact\n\n"
            f"{generation_markdown}\n\n"
            "## Source CSS Style Report\n\n"
            f"{source_style_report}"
        ),
        max_tokens=max(config.max_tokens, SITE_GEN_MAX_TOKENS),
    )
    result = result.strip()
    if result.startswith("```html"):
        result = result[7:]
    elif result.startswith("```"):
        result = result[3:]
    if result.endswith("```"):
        result = result[:-3]
    return result.strip()


def enforce_source_site_styles(
    html: str,
    generation_markdown: str,
    extracted_source_styles: dict,
    config: AppConfig,
    site_style_sync_prompt: str | None = None,
    source_style_ledger: dict | None = None,
    audit_before_path: Path | None = None,
    audit_after_path: Path | None = None,
    max_passes: int = 2,
) -> str:
    """Ensure generated site HTML uses only source-backed explicit colors and font families."""
    synced = html
    source_style_report = render_source_color_report(extracted_source_styles)
    allowed_approximate = {
        literal.strip()
        for literal in extract_document_color_literals(generation_markdown or "")
        if literal.strip()
    }

    if source_style_ledger:
        before_audit = audit_document_styles(
            synced,
            extracted_source_styles,
            source_style_ledger,
            allowed_approximate_literals=allowed_approximate,
        )
        if audit_before_path:
            write_style_audit(audit_before_path, before_audit)
        synced, deterministic_audit = reconcile_document_styles(
            synced,
            extracted_source_styles,
            source_style_ledger,
            allowed_approximate_literals=allowed_approximate,
        )
        after_det = deterministic_audit.get("after", {})
        if not after_det.get("unsupported_colors") and not after_det.get("unsupported_fonts"):
            if audit_after_path:
                write_style_audit(audit_after_path, deterministic_audit)
            return synced

    deterministic_replacements = suggest_nearest_source_color_replacements(synced, extracted_source_styles)
    if deterministic_replacements:
        candidate = apply_document_color_replacements(synced, deterministic_replacements)
        unsupported_colors = find_non_source_document_colors(candidate, extracted_source_styles)
        unsupported_fonts = find_non_source_document_font_families(candidate, extracted_source_styles)
        if not unsupported_colors and not unsupported_fonts:
            return candidate
        synced = candidate

    for _ in range(max_passes):
        unsupported_colors = find_non_source_document_colors(synced, extracted_source_styles)
        unsupported_fonts = find_non_source_document_font_families(synced, extracted_source_styles)
        if not unsupported_colors and not unsupported_fonts:
            return synced

        notes: list[str] = []
        if unsupported_colors:
            notes.append(
                "Unsupported explicit color values currently present in the HTML:\n"
                + "\n".join(f"- `{value}`" for value in unsupported_colors)
            )
        if unsupported_fonts:
            notes.append(
                "Unsupported explicit font-family values currently present in the HTML:\n"
                + "\n".join(f"- `{value}`" for value in unsupported_fonts)
            )

        synced = synchronize_generated_site_styles(
            synced,
            generation_markdown=generation_markdown,
            source_style_report=source_style_report,
            config=config,
            site_style_sync_prompt=(
                (site_style_sync_prompt or DEFAULT_SITE_STYLE_SYNC_PROMPT)
                + "\n\n"
                + "\n\n".join(notes)
            ),
        )

    if source_style_ledger and audit_after_path:
        write_style_audit(
            audit_after_path,
            audit_document_styles(
                synced,
                extracted_source_styles,
                source_style_ledger,
                allowed_approximate_literals=allowed_approximate,
            ),
        )

    return synced


VIEWPORT_LAYOUT_UNIT_RE = re.compile(
    r"(?P<full>(?P<prop>\b(?:min-|max-)?(?:height|width)\b)\s*:\s*(?P<value>[^;{}]*?"
    r"(?:\d*\.?\d+)(?:vh|dvh|svh|lvh|vw|vmin|vmax)\b[^;{}]*)(?P<semi>;?))",
    flags=re.IGNORECASE,
)

def repair_viewport_layout_units(html: str) -> tuple[str, dict]:
    """Replace viewport-relative layout sizing so generated sites do not create giant viewer sections."""
    replacements: list[dict] = []

    def replace_declaration(match: re.Match) -> str:
        prop = match.group("prop")
        value = match.group("value").strip()
        semi = match.group("semi") or ";"
        prop_lower = prop.lower()
        unit_match = re.search(
            r"(?P<number>\d*\.?\d+)(?P<unit>vh|dvh|svh|lvh|vw|vmin|vmax)\b",
            value,
            flags=re.IGNORECASE,
        )

        if "width" in prop_lower:
            repaired_value = re.sub(
                r"(\d*\.?\d+)vw\b",
                lambda unit_match: f"{unit_match.group(1)}%",
                value,
                flags=re.IGNORECASE,
            )
            repaired_value = re.sub(r"\b100(?:dvh|svh|lvh|vh|vmin|vmax)\b", "100%", repaired_value, flags=re.IGNORECASE)
            if re.search(r"(?:dvh|svh|lvh|vh|vmin|vmax)\b", repaired_value, flags=re.IGNORECASE):
                repaired_value = "100%"
        elif prop_lower == "min-height":
            amount = float(unit_match.group("number")) if unit_match else 60.0
            if amount >= 80:
                repaired_value = "clamp(560px, 50rem, 900px)"
            elif amount >= 60:
                repaired_value = "clamp(440px, 42rem, 760px)"
            else:
                repaired_value = "clamp(320px, 36rem, 560px)"
        elif prop_lower == "max-height":
            repaired_value = "900px"
        else:
            repaired_value = "clamp(320px, 48rem, 640px)"

        original = match.group("full")
        replacement = f"{prop}: {repaired_value}{semi}"
        replacements.append(
            {
                "property": prop,
                "original": original,
                "replacement": replacement,
            }
        )
        return replacement

    repaired = VIEWPORT_LAYOUT_UNIT_RE.sub(replace_declaration, html)
    remaining = sorted(set(re.findall(r"\d*\.?\d+(?:vh|dvh|svh|lvh|vw|vmin|vmax)\b", repaired, flags=re.IGNORECASE)))
    return repaired, {
        "status": "repaired" if replacements else "clean",
        "replacement_count": len(replacements),
        "replacements": replacements,
        "remaining_viewport_units": remaining,
    }


def repair_html_file_viewport_layout_units(html_path: Path) -> dict:
    """Repair a saved HTML file and persist a sidecar report."""
    html, report = repair_viewport_layout_units(html_path.read_text(errors="ignore"))
    html_path.write_text(html)
    html_path.with_suffix(".viewport-units.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def generate_website_html(
    generation_markdown: str,
    provider_name: str,
    website_prompt: str | None = None,
    generation_label: str = "design system",
) -> str:
    """Send the configured markdown artifact to an LLM and get back a complete HTML website."""
    prompt = website_prompt or WEBSITE_GEN_PROMPT
    intro = f"Here is the {generation_label} to implement:\n\n{generation_markdown}"
    if provider_name == "claude":
        provider = AnthropicProvider("claude-opus-4-8")
        result = provider.text_query(
            system_prompt=prompt,
            user_prompt=intro,
            max_tokens=SITE_GEN_MAX_TOKENS,
        )
    elif provider_name == "gemini":
        raise ValueError("Gemini site generation is disabled for future pipeline runs.")
    elif provider_name == "gpt55":
        provider = OpenAIProvider("gpt-5.5")
        result = provider.text_query(
            system_prompt=prompt,
            user_prompt=intro,
            max_tokens=SITE_GEN_MAX_TOKENS,
        )
    else:
        raise ValueError(f"Unknown provider: {provider_name}")

    result = result.strip()
    if result.startswith("```html"):
        result = result[7:]
    elif result.startswith("```"):
        result = result[3:]
    if result.endswith("```"):
        result = result[:-3]

    return result.strip()


def html_document_is_complete(html: str) -> bool:
    """Return True when an HTML string looks like a complete document."""
    lowered = html.lower()
    required_markers = ("<html", "</style>", "<body", "</body>", "</html>")
    return all(marker in lowered for marker in required_markers)


def grounding_document_is_complete(text: str) -> bool:
    """Return True when a grounding markdown string looks structurally complete."""
    required_markers = (
        "# Structural Analysis",
        "## Section Inventory",
        "## Cross-section Notes",
        "## Ambiguities",
    )
    if not all(marker in text for marker in required_markers):
        return False
    if not re.search(r"^## Section group \d+|^## Section \d+:", text, flags=re.MULTILINE):
        return False
    ambiguities_index = text.rfind("## Ambiguities")
    if ambiguities_index == -1:
        return False
    tail = text[ambiguities_index:].strip()
    return len(tail.splitlines()) >= 2


def parse_provider_list(text: str) -> list[str]:
    """Parse a version-scoped provider list."""
    providers: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].strip().lower()
        if not line:
            continue
        for item in re.split(r"[\s,]+", line):
            # Preserve old version folders/configs while normalizing new runs to the truthful key.
            if item == "gpt54":
                item = "gpt55"
            if item in DISABLED_SITE_GENERATION_PROVIDERS:
                continue
            if item:
                providers.append(item)

    allowed = set(ALLOWED_SITE_GENERATION_PROVIDERS)
    invalid = [provider for provider in providers if provider not in allowed]
    if invalid:
        raise ValueError(
            "Unsupported provider(s) in site-generation-providers.txt: "
            + ", ".join(sorted(set(invalid)))
        )

    ordered_unique: list[str] = []
    for provider in providers:
        if provider not in ordered_unique:
            ordered_unique.append(provider)
    return ordered_unique or ["gpt55"]


def extract_json_object(text: str) -> dict | None:
    """Extract the first JSON object from a model response."""
    stripped = text.strip()
    if not stripped:
        return None

    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped, flags=re.IGNORECASE)
        stripped = re.sub(r"\s*```$", "", stripped)

    try:
        payload = json.loads(stripped)
        return payload if isinstance(payload, dict) else None
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", stripped, flags=re.DOTALL)
    if not match:
        return None

    try:
        payload = json.loads(match.group(0))
        return payload if isinstance(payload, dict) else None
    except json.JSONDecodeError:
        return None


def normalize_site_review_payload(payload: dict, raw_response: str) -> dict:
    """Normalize a model-produced site review into a consistent saved shape."""
    raw_scores = payload.get("scores") if isinstance(payload.get("scores"), dict) else {}
    normalized_scores: dict[str, dict] = {}
    weighted_total = 0.0

    for key, weight in SITE_MATCH_SCORE_WEIGHTS.items():
        raw_entry = raw_scores.get(key) if isinstance(raw_scores, dict) else {}
        raw_score = raw_entry.get("score") if isinstance(raw_entry, dict) else 0
        try:
            score = max(0.0, min(10.0, float(raw_score)))
        except (TypeError, ValueError):
            score = 0.0
        notes = raw_entry.get("notes") if isinstance(raw_entry, dict) else ""
        normalized_scores[key] = {
            "score": round(score, 2),
            "weight": weight,
            "weighted_points": round(score * weight * 10, 2),
            "notes": str(notes or "").strip(),
        }
        weighted_total += score * weight * 10

    strengths = payload.get("strengths")
    if not isinstance(strengths, list):
        strengths = []
    mismatches = payload.get("major_mismatches")
    if not isinstance(mismatches, list):
        mismatches = []

    return {
        "summary": str(payload.get("summary", "")).strip(),
        "weighted_score": round(weighted_total, 2),
        "scores": normalized_scores,
        "strengths": [str(item).strip() for item in strengths if str(item).strip()],
        "major_mismatches": [str(item).strip() for item in mismatches if str(item).strip()],
        "verdict": str(payload.get("verdict", "")).strip(),
        "raw_response": raw_response.strip(),
    }


def normalize_weighted_review_payload(payload: dict, raw_response: str, weights: dict[str, float]) -> dict:
    """Normalize a weighted review JSON payload with named 0-10 score dimensions."""
    raw_scores = payload.get("scores") if isinstance(payload.get("scores"), dict) else {}
    normalized_scores: dict[str, dict] = {}
    weighted_total = 0.0

    for key, weight in weights.items():
        raw_entry = raw_scores.get(key) if isinstance(raw_scores, dict) else {}
        raw_score = raw_entry.get("score") if isinstance(raw_entry, dict) else 0
        try:
            score = max(0.0, min(10.0, float(raw_score)))
        except (TypeError, ValueError):
            score = 0.0
        notes = raw_entry.get("notes") if isinstance(raw_entry, dict) else ""
        normalized_scores[key] = {
            "score": round(score, 2),
            "weight": weight,
            "weighted_points": round(score * weight * 10, 2),
            "notes": str(notes or "").strip(),
        }
        weighted_total += score * weight * 10

    strengths = payload.get("strengths")
    if not isinstance(strengths, list):
        strengths = []
    mismatches = payload.get("major_mismatches")
    if not isinstance(mismatches, list):
        mismatches = []
    learnings = payload.get("actionable_learnings")
    if not isinstance(learnings, list):
        learnings = []

    return {
        "summary": str(payload.get("summary", "")).strip(),
        "weighted_score": round(weighted_total, 2),
        "scores": normalized_scores,
        "strengths": [str(item).strip() for item in strengths if str(item).strip()],
        "major_mismatches": [str(item).strip() for item in mismatches if str(item).strip()],
        "actionable_learnings": [str(item).strip() for item in learnings if str(item).strip()],
        "verdict": str(payload.get("verdict", "")).strip(),
        "raw_response": raw_response.strip(),
    }


def normalize_design_system_conversion_review_payload(payload: dict, raw_response: str) -> dict:
    """Normalize a design-system conversion-loss review payload."""
    normalized = normalize_weighted_review_payload(
        payload if isinstance(payload, dict) else {},
        raw_response,
        DESIGN_SYSTEM_CONVERSION_SCORE_WEIGHTS,
    )
    normalized["preserved_pairings"] = _normalize_string_list(
        payload.get("preserved_pairings") if isinstance(payload, dict) else []
    )
    normalized["conversion_losses"] = _normalize_string_list(
        payload.get("conversion_losses") if isinstance(payload, dict) else []
    )
    normalized["distortions_or_overgeneralizations"] = _normalize_string_list(
        payload.get("distortions_or_overgeneralizations") if isinstance(payload, dict) else []
    )
    return normalized


def review_payload_to_markdown(review: dict) -> str:
    """Render a saved site-match review as concise markdown."""
    lines = [
        "# Site Match Review",
        "",
        f"- Weighted score: **{review.get('weighted_score', 0):.2f} / 100**",
    ]

    summary = str(review.get("summary", "")).strip()
    if summary:
        lines.append(f"- Summary: {summary}")

    verdict = str(review.get("verdict", "")).strip()
    if verdict:
        lines.append(f"- Verdict: {verdict}")

    lines.extend(["", "## Dimension Scores", ""])
    for key, entry in review.get("scores", {}).items():
        label = key.replace("_", " ").title()
        lines.append(
            f"- **{label}:** {entry.get('score', 0):.2f}/10 "
            f"(weight {entry.get('weight', 0):.2f}, weighted points {entry.get('weighted_points', 0):.2f})"
        )
        notes = str(entry.get("notes", "")).strip()
        if notes:
            lines.append(f"  - {notes}")

    strengths = review.get("strengths") or []
    if strengths:
        lines.extend(["", "## Strengths", ""])
        for item in strengths:
            lines.append(f"- {item}")

    mismatches = review.get("major_mismatches") or []
    if mismatches:
        lines.extend(["", "## Major Mismatches", ""])
        for item in mismatches:
            lines.append(f"- {item}")

    return "\n".join(lines).rstrip() + "\n"


def surface_component_map_review_to_markdown(review: dict) -> str:
    """Render a saved surface-component-map review as concise markdown."""
    lines = [
        "# Surface Component Map Review",
        "",
        f"- Weighted score: **{review.get('weighted_score', 0):.2f} / 100**",
    ]
    summary = str(review.get("summary", "")).strip()
    if summary:
        lines.append(f"- Summary: {summary}")
    verdict = str(review.get("verdict", "")).strip()
    if verdict:
        lines.append(f"- Verdict: {verdict}")

    lines.extend(["", "## Dimension Scores", ""])
    for key, entry in review.get("scores", {}).items():
        label = key.replace("_", " ").title()
        lines.append(
            f"- **{label}:** {entry.get('score', 0):.2f}/10 "
            f"(weight {entry.get('weight', 0):.2f}, weighted points {entry.get('weighted_points', 0):.2f})"
        )
        notes = str(entry.get("notes", "")).strip()
        if notes:
            lines.append(f"  - {notes}")

    for heading, key in (
        ("Strengths", "strengths"),
        ("Major Mismatches", "major_mismatches"),
        ("Learnings", "actionable_learnings"),
    ):
        items = review.get(key) or []
        if items:
            lines.extend(["", f"## {heading}", ""])
            for item in items:
                lines.append(f"- {item}")

    return "\n".join(lines).rstrip() + "\n"


def design_system_conversion_review_to_markdown(review: dict) -> str:
    """Render a saved design-system conversion-loss review as concise markdown."""
    lines = [
        "# Design-System Conversion Loss Review",
        "",
        f"- Weighted score: **{review.get('weighted_score', 0):.2f} / 100**",
    ]
    summary = str(review.get("summary", "")).strip()
    if summary:
        lines.append(f"- Summary: {summary}")
    verdict = str(review.get("verdict", "")).strip()
    if verdict:
        lines.append(f"- Verdict: {verdict}")

    lines.extend(["", "## Dimension Scores", ""])
    for key, entry in review.get("scores", {}).items():
        label = key.replace("_", " ").title()
        lines.append(
            f"- **{label}:** {entry.get('score', 0):.2f}/10 "
            f"(weight {entry.get('weight', 0):.2f}, weighted points {entry.get('weighted_points', 0):.2f})"
        )
        notes = str(entry.get("notes", "")).strip()
        if notes:
            lines.append(f"  - {notes}")

    for heading, key in (
        ("Preserved Pairings", "preserved_pairings"),
        ("Conversion Losses", "conversion_losses"),
        ("Distortions Or Overgeneralizations", "distortions_or_overgeneralizations"),
        ("Learnings", "actionable_learnings"),
    ):
        items = review.get(key) or []
        if items:
            lines.extend(["", f"## {heading}", ""])
            for item in items:
                lines.append(f"- {item}")

    return "\n".join(lines).rstrip() + "\n"


def _clamp_score(value, default: float = 0.0) -> float:
    """Normalize a model score to the shared 0-10 scale."""
    try:
        return max(0.0, min(10.0, float(value)))
    except (TypeError, ValueError):
        return default


def _normalize_string_list(value) -> list[str]:
    """Return a clean list of non-empty strings from model output."""
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def slugify_review_section(value: str, existing: set[str] | None = None) -> str:
    """Create a stable section id for saved review payloads."""
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "section"
    if existing is None or slug not in existing:
        if existing is not None:
            existing.add(slug)
        return slug

    index = 2
    while f"{slug}-{index}" in existing:
        index += 1
    unique = f"{slug}-{index}"
    existing.add(unique)
    return unique


def split_design_system_review_sections(markdown: str) -> tuple[str, list[dict]]:
    """Split design-system markdown into focused leaf sections for parallel review."""
    text = markdown.strip()
    frontmatter = ""
    body = text
    frontmatter_match = re.match(r"\A---\s*\n(.*?)\n---\s*\n?", text, flags=re.DOTALL)
    if frontmatter_match:
        frontmatter = frontmatter_match.group(0).strip()
        body = text[frontmatter_match.end():].lstrip()

    lines = body.splitlines()
    heading_pattern = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
    headings: list[dict] = []
    for index, line in enumerate(lines):
        match = heading_pattern.match(line)
        if not match:
            continue
        title = match.group(2).strip()
        normalized_title = re.sub(r"\s+", " ", title).strip().lower()
        if normalized_title in {"source css color report", "source css styles", "source font implementation"}:
            break
        headings.append({
            "index": index,
            "level": len(match.group(1)),
            "title": title,
        })

    if not headings:
        return frontmatter, [
            {
                "id": "design-system",
                "heading": "Design system",
                "parent_heading": "",
                "level": 1,
                "content": body.strip(),
            }
        ] if body.strip() else []

    stop_line = len(lines)
    if headings:
        last_heading = headings[-1]
        last_heading_index = last_heading["index"]
        for index in range(last_heading_index + 1, len(lines)):
            match = heading_pattern.match(lines[index])
            if match:
                stop_line = index
                break

    parent_by_line: dict[int, str] = {}
    current_h2 = ""
    for heading in headings:
        if heading["level"] == 2:
            current_h2 = heading["title"]
        parent_by_line[heading["index"]] = current_h2

    # Review leaf sections: h3+ sections, plus h2 sections that do not contain
    # child h3 content before the next h2. This preserves focused agent scopes.
    candidate_indexes: list[int] = []
    for position, heading in enumerate(headings):
        next_same_or_higher = stop_line
        for later in headings[position + 1:]:
            if later["level"] <= heading["level"]:
                next_same_or_higher = later["index"]
                break
        has_child_h3 = any(
            later["level"] >= 3 and heading["index"] < later["index"] < next_same_or_higher
            for later in headings[position + 1:]
        )
        if heading["level"] == 3 or (heading["level"] == 2 and not has_child_h3):
            candidate_indexes.append(position)

    sections: list[dict] = []
    used_ids: set[str] = set()
    for position in candidate_indexes:
        heading = headings[position]
        end = stop_line
        for later in headings[position + 1:]:
            if later["level"] <= heading["level"]:
                end = later["index"]
                break
        content = "\n".join(lines[heading["index"]:end]).strip()
        if not content:
            continue
        parent = parent_by_line.get(heading["index"], "")
        if parent == heading["title"]:
            parent = ""
        display = f"{parent} / {heading['title']}" if parent else heading["title"]
        sections.append({
            "id": slugify_review_section(display, used_ids),
            "heading": heading["title"],
            "parent_heading": parent,
            "level": heading["level"],
            "content": content,
        })

    return frontmatter, sections


def normalize_design_system_section_review(
    section: dict,
    payload: dict,
    raw_response: str,
) -> dict:
    """Normalize one parallel design-system section review."""
    score = _clamp_score(payload.get("score") if isinstance(payload, dict) else 0)
    confidence = _clamp_score(payload.get("confidence") if isinstance(payload, dict) else 0) / 10
    return {
        "id": section.get("id", ""),
        "heading": section.get("heading", ""),
        "parent_heading": section.get("parent_heading", ""),
        "level": section.get("level", 0),
        "score": round(score, 2),
        "weighted_points": round(score * 10, 2),
        "confidence": round(confidence, 2),
        "summary": str(payload.get("summary", "") if isinstance(payload, dict) else "").strip(),
        "accurate_patterns": _normalize_string_list(payload.get("accurate_patterns") if isinstance(payload, dict) else []),
        "missing_or_weak_patterns": _normalize_string_list(payload.get("missing_or_weak_patterns") if isinstance(payload, dict) else []),
        "overfit_or_unsupported_rules": _normalize_string_list(payload.get("overfit_or_unsupported_rules") if isinstance(payload, dict) else []),
        "actionable_learnings": _normalize_string_list(payload.get("actionable_learnings") if isinstance(payload, dict) else []),
        "verdict": str(payload.get("verdict", "") if isinstance(payload, dict) else "").strip(),
        "raw_response": raw_response.strip(),
    }


def combine_design_system_review_sections(section_reviews: list[dict], raw_response: str = "") -> dict:
    """Combine parallel section reviews into one saved design-system review payload."""
    if section_reviews:
        weighted_score = sum(float(item.get("score", 0)) for item in section_reviews) / len(section_reviews) * 10
    else:
        weighted_score = 0.0

    sorted_reviews = sorted(section_reviews, key=lambda item: item.get("score", 0))
    weakest = [
        f"{item.get('heading', 'Section')}: {item.get('summary') or item.get('verdict') or 'No summary'}"
        for item in sorted_reviews[:3]
    ]
    strongest = [
        f"{item.get('heading', 'Section')}: {item.get('summary') or item.get('verdict') or 'No summary'}"
        for item in sorted(section_reviews, key=lambda item: item.get("score", 0), reverse=True)[:3]
    ]
    learnings: list[str] = []
    for item in sorted_reviews:
        for learning in item.get("actionable_learnings", []):
            if learning not in learnings:
                learnings.append(learning)
            if len(learnings) >= 8:
                break
        if len(learnings) >= 8:
            break

    summary = "No design-system sections were available for review."
    if section_reviews:
        summary = (
            f"Reviewed {len(section_reviews)} design-system section(s) against the source screenshot. "
            f"Weakest areas: {', '.join(item.get('heading', 'Section') for item in sorted_reviews[:3])}."
        )

    scores = {
        item.get("id", f"section-{index + 1}"): {
            "heading": item.get("heading", ""),
            "parent_heading": item.get("parent_heading", ""),
            "score": item.get("score", 0),
            "weighted_points": item.get("weighted_points", 0),
            "notes": item.get("summary", ""),
        }
        for index, item in enumerate(section_reviews)
    }

    return {
        "summary": summary,
        "weighted_score": round(weighted_score, 2),
        "scores": scores,
        "section_reviews": section_reviews,
        "strengths": strongest,
        "major_mismatches": weakest,
        "actionable_learnings": learnings,
        "verdict": "Design-system review complete." if section_reviews else "Review skipped.",
        "raw_response": raw_response.strip() or "\n\n".join(item.get("raw_response", "") for item in section_reviews).strip(),
    }


def design_system_review_payload_to_markdown(review: dict) -> str:
    """Render a saved design-system review as concise markdown."""
    lines = [
        "# Design System Review",
        "",
        f"- Weighted score: **{review.get('weighted_score', 0):.2f} / 100**",
    ]

    summary = str(review.get("summary", "")).strip()
    if summary:
        lines.append(f"- Summary: {summary}")

    verdict = str(review.get("verdict", "")).strip()
    if verdict:
        lines.append(f"- Verdict: {verdict}")

    section_reviews = review.get("section_reviews") or []
    if section_reviews:
        lines.extend(["", "## Section Scores", ""])
        for item in section_reviews:
            parent = str(item.get("parent_heading", "")).strip()
            heading = str(item.get("heading", "")).strip() or "Section"
            label = f"{parent} / {heading}" if parent else heading
            lines.append(f"- **{label}:** {item.get('score', 0):.2f}/10")
            summary = str(item.get("summary", "")).strip()
            if summary:
                lines.append(f"  - {summary}")

    learnings = review.get("actionable_learnings") or []
    if learnings:
        lines.extend(["", "## Learnings", ""])
        for item in learnings:
            lines.append(f"- {item}")

    mismatches = review.get("major_mismatches") or []
    if mismatches:
        lines.extend(["", "## Weakest Areas", ""])
        for item in mismatches:
            lines.append(f"- {item}")

    return "\n".join(lines).rstrip() + "\n"


def evaluate_design_system_section(
    reference_screenshot_path: Path,
    frontmatter: str,
    section: dict,
    review_prompt: str,
    config: AppConfig,
    *,
    max_image_dimension: int,
) -> dict:
    """Score one design-system markdown section against the original screenshot."""
    provider = get_provider(config)
    screenshot_b64 = load_and_encode_image(str(reference_screenshot_path), max_dimension=max_image_dimension)
    parent = section.get("parent_heading") or "None"
    response = provider.analyze_image(
        image_b64=screenshot_b64,
        system_prompt=review_prompt,
        user_prompt=(
            "Review the focused design-system section below against the source screenshot.\n\n"
            f"## Parent Section\n\n{parent}\n\n"
            f"## Focus Section\n\n{section.get('content', '')}\n\n"
            "## Shared YAML Front Matter\n\n"
            f"{frontmatter or 'No YAML front matter present.'}"
        ),
        max_tokens=4096,
    )
    payload = extract_json_object(response) or {}
    return normalize_design_system_section_review(section, payload, response)


def evaluate_design_system_match(
    reference_screenshot_path: Path,
    design_system_markdown: str,
    review_json_path: Path,
    review_md_path: Path,
    review_prompt: str,
    config: AppConfig,
    *,
    max_image_dimension: int,
    output_dir: Path | None = None,
) -> dict:
    """Run parallel section agents to score the final design system against the screenshot."""
    frontmatter, sections = split_design_system_review_sections(design_system_markdown)
    if not sections:
        normalized = combine_design_system_review_sections([])
        review_json_path.write_text(json.dumps(normalized, indent=2) + "\n")
        review_md_path.write_text(design_system_review_payload_to_markdown(normalized))
        return normalized

    max_workers = min(DESIGN_SYSTEM_REVIEW_MAX_WORKERS, len(sections))
    section_reviews: list[dict] = []

    def run_section_review(section: dict) -> dict:
        if output_dir:
            with token_usage_context(output_dir, f"design_system_review_{section['id']}", {"section": section["heading"]}):
                return evaluate_design_system_section(
                    reference_screenshot_path,
                    frontmatter,
                    section,
                    review_prompt,
                    config,
                    max_image_dimension=max_image_dimension,
                )
        return evaluate_design_system_section(
            reference_screenshot_path,
            frontmatter,
            section,
            review_prompt,
            config,
            max_image_dimension=max_image_dimension,
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(run_section_review, section): section
            for section in sections
        }
        for future in concurrent.futures.as_completed(futures):
            section = futures[future]
            try:
                section_reviews.append(future.result())
            except Exception as exc:
                section_reviews.append(normalize_design_system_section_review(
                    section,
                    {
                        "score": 0,
                        "confidence": 0,
                        "summary": f"Review failed: {exc}",
                        "missing_or_weak_patterns": [f"Review failed: {exc}"],
                        "verdict": "Review failed.",
                    },
                    "",
                ))

    order = {section["id"]: index for index, section in enumerate(sections)}
    section_reviews.sort(key=lambda item: order.get(item.get("id", ""), 9999))
    normalized = combine_design_system_review_sections(section_reviews)
    review_json_path.write_text(json.dumps(normalized, indent=2) + "\n")
    review_md_path.write_text(design_system_review_payload_to_markdown(normalized))
    return normalized


def evaluate_surface_component_map_match(
    reference_screenshot_path: Path,
    section_grounding_markdown: str,
    surface_component_map: str,
    review_json_path: Path,
    review_md_path: Path,
    review_prompt: str,
    config: AppConfig,
    *,
    max_image_dimension: int,
    output_dir: Path | None = None,
) -> dict:
    """Score the intermediate surface-component map against screenshot and grounding."""
    provider = get_provider(config)
    screenshot_b64 = load_and_encode_image(str(reference_screenshot_path), max_dimension=max_image_dimension)
    compact_grounding = compact_section_grounding_for_surface_map(section_grounding_markdown, max_chars=36000)

    def run_review(map_for_review: str) -> dict:
        response = provider.analyze_image(
            image_b64=screenshot_b64,
            system_prompt=review_prompt,
            user_prompt=(
                "Review the surface-component map against the source screenshot and section grounding.\n\n"
                "## Compacted Section Grounding Reference\n\n"
                f"{compact_grounding}\n\n"
                "## Surface Component Map\n\n"
                f"{map_for_review}"
            ),
            max_tokens=4096,
        )
        payload = extract_json_object(response) or {}
        return normalize_weighted_review_payload(
            payload,
            response,
            SURFACE_COMPONENT_MAP_SCORE_WEIGHTS,
        )

    if output_dir:
        with token_usage_context(output_dir, "surface_component_map_review"):
            normalized = run_review(surface_component_map)
    else:
        normalized = run_review(surface_component_map)

    if not str(normalized.get("raw_response", "")).strip() and float(normalized.get("weighted_score", 0) or 0) == 0:
        retry_map = surface_component_map
        if len(retry_map) > 30000:
            retry_map = retry_map[:30000].rstrip() + "\n\n[Surface map truncated for review retry after empty response.]\n"
        if output_dir:
            with token_usage_context(output_dir, "surface_component_map_review_retry"):
                normalized = run_review(retry_map)
        else:
            normalized = run_review(retry_map)

    review_json_path.write_text(json.dumps(normalized, indent=2) + "\n")
    review_md_path.write_text(surface_component_map_review_to_markdown(normalized))
    return normalized


def evaluate_design_system_conversion_loss(
    surface_component_map: str,
    design_system_markdown: str,
    review_json_path: Path,
    review_md_path: Path,
    review_prompt: str,
    config: AppConfig,
    *,
    output_dir: Path | None = None,
) -> dict:
    """Score how faithfully the design system translated the surface/component map."""
    provider = get_provider(config)

    def run_review(map_for_review: str, design_for_review: str) -> dict:
        response = provider.text_query(
            system_prompt=review_prompt,
            user_prompt=(
                "Review the design-system conversion against the surface-component map. "
                "The surface-component map is the factual source of truth; no screenshot is available.\n\n"
                "## Surface Component Map\n\n"
                f"{map_for_review}\n\n"
                "## Design System\n\n"
                f"{design_for_review}"
            ),
            max_tokens=4096,
        )
        payload = extract_json_object(response) or {}
        return normalize_design_system_conversion_review_payload(payload, response)

    if output_dir:
        with token_usage_context(output_dir, "design_system_conversion_review"):
            normalized = run_review(surface_component_map, design_system_markdown)
    else:
        normalized = run_review(surface_component_map, design_system_markdown)

    if not str(normalized.get("raw_response", "")).strip() and float(normalized.get("weighted_score", 0) or 0) == 0:
        retry_map = surface_component_map
        retry_design = design_system_markdown
        if len(retry_map) > 30000:
            retry_map = retry_map[:30000].rstrip() + "\n\n[Surface map truncated for review retry after empty response.]\n"
        if len(retry_design) > 30000:
            retry_design = retry_design[:30000].rstrip() + "\n\n[Design system truncated for review retry after empty response.]\n"
        if output_dir:
            with token_usage_context(output_dir, "design_system_conversion_review_retry"):
                normalized = run_review(retry_map, retry_design)
        else:
            normalized = run_review(retry_map, retry_design)

    review_json_path.write_text(json.dumps(normalized, indent=2) + "\n")
    review_md_path.write_text(design_system_conversion_review_to_markdown(normalized))
    return normalized


def render_html_to_screenshot(
    html_path: Path,
    output_path: Path,
    reference_screenshot_path: Path,
    *,
    virtual_time_budget_ms: int = 2500,
) -> None:
    """Render a single-file HTML page to a screenshot matching the reference size."""
    if not Path(CHROME_HEADLESS_PATH).exists():
        raise FileNotFoundError(f"Chrome not found at {CHROME_HEADLESS_PATH}")

    with Image.open(reference_screenshot_path) as img:
        width, height = img.size

    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        CHROME_HEADLESS_PATH,
        "--headless=new",
        "--disable-gpu",
        "--hide-scrollbars",
        "--allow-file-access-from-files",
        "--force-device-scale-factor=1",
        "--run-all-compositor-stages-before-draw",
        f"--virtual-time-budget={virtual_time_budget_ms}",
        f"--window-size={width},{height}",
        f"--screenshot={str(output_path)}",
        html_path.resolve().as_uri(),
    ]
    subprocess.run(command, check=True, capture_output=True, text=True)


def evaluate_site_match(
    reference_screenshot_path: Path,
    grounding_markdown: str,
    generated_html_path: Path,
    rendered_screenshot_path: Path,
    review_json_path: Path,
    review_md_path: Path,
    review_prompt: str,
    config: AppConfig,
    *,
    max_image_dimension: int,
) -> dict:
    """Render generated HTML and score its stylistic fidelity against grounding text."""
    render_html_to_screenshot(
        generated_html_path,
        rendered_screenshot_path,
        reference_screenshot_path,
    )

    provider = get_provider(config)
    candidate_b64 = load_and_encode_image(str(rendered_screenshot_path), max_dimension=max_image_dimension)
    response = provider.analyze_image(
        image_b64=candidate_b64,
        system_prompt=review_prompt,
        user_prompt=(
            "Evaluate whether the generated website screenshot expresses the stylistic patterns "
            "described in the grounding markdown below.\n\n"
            "## Grounding Markdown\n\n"
            f"{grounding_markdown}"
        ),
        max_tokens=4096,
    )
    payload = extract_json_object(response) or {}
    normalized = normalize_site_review_payload(payload, response)
    review_json_path.write_text(json.dumps(normalized, indent=2) + "\n")
    review_md_path.write_text(review_payload_to_markdown(normalized))
    return normalized


def image_to_data_uri(path: Path) -> str:
    """Convert an image file to a data URI for embedding in HTML."""
    suffix = path.suffix.lower()
    mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
    mime = mime_map.get(suffix, "image/png")
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return f"data:{mime};base64,{b64}"


def strip_run_output_label(display_name: str) -> str:
    """Remove any existing run-output suffix so regenerated labels do not stack."""
    return RUN_OUTPUT_LABEL_PATTERN.sub("", display_name).strip()


def classify_manifest_mode(version_dir: Path, mode_data: dict | None) -> str | None:
    """Classify a mode as full, grounding-only, or DS-only from real saved files."""
    if not isinstance(mode_data, dict):
        return None

    structural_rel = (mode_data.get("structural_analysis") or "").strip()
    design_system_rel = (mode_data.get("design_system") or "").strip()
    structural_path = version_dir / structural_rel if structural_rel else None
    design_system_path = version_dir / design_system_rel if design_system_rel else None
    has_structural = bool(structural_path and structural_path.exists() and structural_path.is_file())
    has_design_system = bool(design_system_path and design_system_path.exists() and design_system_path.is_file())

    if (
        has_structural
        and has_design_system
        and structural_path.resolve() != design_system_path.resolve()
    ):
        return "Full"
    if has_structural:
        return "Grounding"
    if has_design_system:
        return "DS"
    return None


def classify_manifest_entry(version_dir: Path, entry: dict) -> str | None:
    """Classify one screenshot entry, supporting both nested and legacy manifests."""
    mode_label = classify_manifest_mode(version_dir, entry.get("single"))
    if mode_label:
        return mode_label

    return classify_manifest_mode(version_dir, {
        "structural_analysis": entry.get("structural_analysis"),
        "design_system": entry.get("design_system"),
    })


def classify_manifest_version(version_dir: Path, entries: list[dict]) -> str | None:
    """Choose a single version label from its screenshot entries."""
    labels = {label for entry in entries if (label := classify_manifest_entry(version_dir, entry))}
    if "Full" in labels:
        return "Full"
    if "Grounding" in labels:
        return "Grounding"
    if "DS" in labels:
        return "DS"
    return None


def is_generated_site_html(site_path: Path | None) -> bool:
    """Return true when a saved site artifact looks like a real generated page."""
    if not site_path or not site_path.exists() or site_path.is_dir():
        return False
    try:
        html = site_path.read_text(errors="ignore").strip()
    except OSError:
        return False
    if not html:
        return False
    lowered = html.lower()
    return (
        "skipped for this run" not in lowered
        and "not available for this version" not in lowered
        and "not available for this mode" not in lowered
        and "<h1>error</h1>" not in lowered
        and "<body>error</body>" not in lowered
    )


def manifest_mode_has_generated_site(version_dir: Path, mode_data: dict | None) -> bool:
    """Detect modes that produced a real non-direct site artifact."""
    if not isinstance(mode_data, dict):
        return False

    for site_key in ("site_claude", "site_gemini", "site_gpt55", "site_gpt54", "site_claude_framework", "site_gpt55_framework"):
        site_rel = (mode_data.get(site_key) or "").strip()
        site_path = version_dir / site_rel if site_rel else None
        if is_generated_site_html(site_path):
            return True
    return False


def manifest_entry_has_generated_site(version_dir: Path, entry: dict) -> bool:
    """Detect design-system-based site output in nested or legacy manifest entries."""
    if manifest_mode_has_generated_site(version_dir, entry.get("single")):
        return True
    return manifest_mode_has_generated_site(version_dir, {
        "design_system": entry.get("design_system"),
        "site_claude": entry.get("site_claude"),
        "site_gemini": entry.get("site_gemini"),
        "site_gpt55": entry.get("site_gpt55") or entry.get("site_gpt54"),
    })


def _encode_viewer_payload(data: dict) -> str:
    """Base64-encode viewer payload JSON so embedded HTML cannot break scripts."""
    data_json = json.dumps(data)
    return base64.b64encode(data_json.encode("utf-8")).decode("ascii")


def _write_viewer_payload_script(path: Path, version: str, data: dict):
    encoded = _encode_viewer_payload(data)
    script = (
        "window.__VIEWER_VERSION_PAYLOADS__ = window.__VIEWER_VERSION_PAYLOADS__ || {};\n"
        f"window.__VIEWER_VERSION_PAYLOADS__[{json.dumps(version)}] = JSON.parse(atob({json.dumps(encoded)}));\n"
    )
    path.write_text(script)


def discover_viewer_versions(runs_dir: Path) -> list[str]:
    """Run dirs with viewer payloads: v### pipeline runs and Studio slug projects."""
    candidates: list[str] = []
    for d in runs_dir.iterdir():
        if not d.is_dir():
            continue
        if (d / "manifest.json").exists() or (d / "studio-project.json").exists():
            candidates.append(d.name)

    def sort_key(name: str) -> tuple:
        if name.startswith("v") and len(name) > 1:
            head = name[1:].split("-", 1)[0]
            if head.isdigit():
                suffix = name.split("-", 1)[1] if "-" in name[1:] else ""
                return (0, int(head), suffix)
        return (1, name)

    return sorted(candidates, key=sort_key, reverse=True)


def generate_viewer(runs_dir: Path, output_path: Path):
    """Generate a fast-loading viewer HTML with version data loaded on demand."""
    versions = discover_viewer_versions(runs_dir)

    if not versions:
        return

    # Build data for all versions into separate payload scripts. The latest payload
    # is also embedded in viewer.html so opening the file still shows content
    # immediately without needing a local server.
    payload_dir = output_path.parent / "viewer-data"
    payload_dir.mkdir(parents=True, exist_ok=True)
    version_index = {}
    initial_version = None
    initial_data_b64 = ""

    for version in versions:
        version_dir = runs_dir / version
        manifest_path = version_dir / "manifest.json"
        if manifest_path.exists():
            with open(manifest_path) as f:
                manifest = json.load(f)
            if manifest.get("screenshots") is None:
                # brand-lane style manifest (e.g. runs/<brand>/manifest.json with
                # status/stages keys) — not a pipeline run; nothing to embed.
                continue
        else:
            manifest = infer_manifest_from_version_dir(version_dir)
            if not manifest.get("screenshots"):
                continue

        structural_prompt_path = version_dir / "structural-analysis-prompt.md"
        structural_analysis_prompt = ""
        if structural_prompt_path.exists():
            with open(structural_prompt_path) as f:
                structural_analysis_prompt = f.read()

        # Load system prompt if saved
        prompt_path = version_dir / "system-prompt.md"
        system_prompt = ""
        if prompt_path.exists():
            with open(prompt_path) as f:
                system_prompt = f.read()

        website_prompt_path = version_dir / "website-gen-prompt.md"
        website_prompt = ""
        if website_prompt_path.exists():
            with open(website_prompt_path) as f:
                website_prompt = f.read()

        site_generation_skills = manifest.get("site_generation_skills")
        if not isinstance(site_generation_skills, list):
            site_generation_skills = []
        site_generation_skills_path = version_dir / "site-generation-skills.txt"
        if not site_generation_skills and site_generation_skills_path.exists():
            try:
                skill_names = parse_skill_list(site_generation_skills_path.read_text())
                site_generation_skills = [
                    {
                        "name": skill["name"],
                        "path": str(skill["path"].relative_to(PROJECT_DIR)),
                        "content": skill["content"],
                    }
                    for skill in load_site_generation_skills(skill_names)
                ]
            except Exception as exc:
                site_generation_skills = [{
                    "name": "skill-loading-error",
                    "path": str(site_generation_skills_path),
                    "content": f"Could not load site generation skills: {exc}",
                }]

        grounding_sync_prompt_path = version_dir / "grounding-sync-prompt.md"
        grounding_sync_prompt = ""
        if grounding_sync_prompt_path.exists():
            with open(grounding_sync_prompt_path) as f:
                grounding_sync_prompt = f.read()

        site_style_sync_prompt_path = version_dir / "site-style-sync-prompt.md"
        site_style_sync_prompt = ""
        if site_style_sync_prompt_path.exists():
            with open(site_style_sync_prompt_path) as f:
                site_style_sync_prompt = f.read()

        design_system_review_prompt_path = version_dir / "design-system-review-prompt.md"
        design_system_review_prompt = ""
        if design_system_review_prompt_path.exists():
            with open(design_system_review_prompt_path) as f:
                design_system_review_prompt = f.read()

        design_system_conversion_review_prompt_path = version_dir / "design-system-conversion-review-prompt.md"
        design_system_conversion_review_prompt = ""
        if design_system_conversion_review_prompt_path.exists():
            with open(design_system_conversion_review_prompt_path) as f:
                design_system_conversion_review_prompt = f.read()

        screenshot_direct_prompt_path = version_dir / "gpt55-screenshot-direct-prompt.md"
        if not screenshot_direct_prompt_path.exists():
            screenshot_direct_prompt_path = version_dir / "gpt54-screenshot-direct-prompt.md"
        screenshot_direct_prompt = ""
        if screenshot_direct_prompt_path.exists():
            with open(screenshot_direct_prompt_path) as f:
                screenshot_direct_prompt = f.read()

        learnings_path = version_dir / "learnings.md"
        learnings = ""
        if learnings_path.exists():
            with open(learnings_path) as f:
                learnings = f.read()

        display_name_path = version_dir / "display-name.txt"
        display_name = version
        if display_name_path.exists():
            display_name = display_name_path.read_text().strip() or version
        version_output_label = classify_manifest_version(version_dir, manifest.get("screenshots", []))
        if version_output_label:
            display_name = f"{strip_run_output_label(display_name)} ({version_output_label})"
        has_generated_site = any(
            manifest_entry_has_generated_site(version_dir, entry)
            for entry in manifest.get("screenshots", [])
        )

        items = []
        has_gpt55_direct = False
        has_framework_sites = False
        for entry in manifest["screenshots"]:
            name = entry["name"]

            # Read screenshot as data URI
            screenshot_file = version_dir / entry["screenshot"]
            screenshot_uri = image_to_data_uri(screenshot_file) if screenshot_file.exists() else ""

            def resolve_manifest_file(rel_path: str | None) -> Path | None:
                if not rel_path:
                    return None
                candidate = version_dir / rel_path
                if not candidate.exists() or candidate.is_dir():
                    return None
                return candidate

            def read_mode(mode_data):
                """Read design system + site HTML for the active pipeline output."""
                if isinstance(mode_data, dict):
                    ds_file = resolve_manifest_file(mode_data.get("design_system"))
                    claude_file = resolve_manifest_file(mode_data.get("site_claude"))
                    gemini_file = resolve_manifest_file(mode_data.get("site_gemini"))
                    gpt55_file = resolve_manifest_file(mode_data.get("site_gpt55") or mode_data.get("site_gpt54"))
                    claude_framework_file = resolve_manifest_file(mode_data.get("site_claude_framework"))
                    gpt55_framework_file = resolve_manifest_file(mode_data.get("site_gpt55_framework"))
                    claude_grounding_file = resolve_manifest_file(mode_data.get("site_claude_grounding"))
                    gpt55_grounding_file = resolve_manifest_file(mode_data.get("site_gpt55_grounding") or mode_data.get("site_gpt54_grounding"))
                    structural_file = resolve_manifest_file(mode_data.get("structural_analysis"))
                    generation_input_file = resolve_manifest_file(mode_data.get("site_generation_input"))
                    grounding_generation_input_file = resolve_manifest_file(mode_data.get("site_generation_input_grounding"))
                    surface_contract_file = resolve_manifest_file(mode_data.get("surface_component_contract"))
                    surface_contract_audit_file = resolve_manifest_file(mode_data.get("surface_component_contract_audit"))
                    source_style_ledger_file = resolve_manifest_file(mode_data.get("source_style_ledger"))
                    design_style_audit_file = resolve_manifest_file(mode_data.get("design_system_style_audit"))
                    design_review_file = resolve_manifest_file(mode_data.get("design_system_review"))
                    conversion_review_file = resolve_manifest_file(mode_data.get("design_system_conversion_review"))
                    if generation_input_file is None:
                        parent_file = ds_file or structural_file
                        candidate = parent_file.parent / "site-generation-input.md" if parent_file else None
                        if candidate and candidate.exists() and candidate.is_file():
                            generation_input_file = candidate
                    parent_file = ds_file or structural_file
                    candidate = parent_file.parent / "design-system-review.md" if parent_file else None
                    if candidate and candidate.exists() and candidate.is_file():
                        design_review_file = candidate
                    candidate = parent_file.parent / "design-system-conversion-review.md" if parent_file else None
                    if candidate and candidate.exists() and candidate.is_file():
                        conversion_review_file = candidate
                    candidate = parent_file.parent / "source-style-ledger.yaml" if parent_file else None
                    if candidate and candidate.exists() and candidate.is_file():
                        source_style_ledger_file = candidate
                    candidate = parent_file.parent / "surface-component-contract.yaml" if parent_file else None
                    if candidate and candidate.exists() and candidate.is_file():
                        surface_contract_file = candidate
                    candidate = parent_file.parent / "surface-component-contract-audit.md" if parent_file else None
                    if candidate and candidate.exists() and candidate.is_file():
                        surface_contract_audit_file = candidate
                    candidate = parent_file.parent / "design-system-style-audit.json" if parent_file else None
                    if candidate and candidate.exists() and candidate.is_file():
                        design_style_audit_file = candidate
                else:
                    return {
                        "design_system": "",
                        "structural_analysis": "",
                        "site_generation_input": "",
                        "surface_component_contract": "",
                        "surface_component_contract_audit": "",
                        "source_style_ledger": "",
                        "design_system_style_audit": "",
                        "design_system_review": "",
                        "design_system_conversion_review": "",
                        "claude_html": "",
                        "gemini_html": "",
                        "gpt55_html": "",
                        "claude_framework_html": "",
                        "gpt55_framework_html": "",
                        "claude_grounding_html": "",
                        "gpt55_grounding_html": "",
                        "ds_path": "",
                        "structural_path": "",
                        "site_generation_input_path": "",
                        "site_generation_input_grounding_path": "",
                        "surface_component_contract_path": "",
                        "surface_component_contract_audit_path": "",
                        "source_style_ledger_path": "",
                        "design_system_style_audit_path": "",
                        "design_system_review_path": "",
                        "design_system_conversion_review_path": "",
                    }
                return {
                    "design_system": ds_file.read_text() if ds_file else "Error loading",
                    "structural_analysis": structural_file.read_text() if structural_file else "",
                    "site_generation_input": generation_input_file.read_text() if generation_input_file else "",
                    "surface_component_contract": surface_contract_file.read_text() if surface_contract_file else "",
                    "surface_component_contract_audit": surface_contract_audit_file.read_text() if surface_contract_audit_file else "",
                    "source_style_ledger": source_style_ledger_file.read_text() if source_style_ledger_file else "",
                    "design_system_style_audit": design_style_audit_file.read_text() if design_style_audit_file else "",
                    "design_system_review": design_review_file.read_text() if design_review_file else "",
                    "design_system_conversion_review": conversion_review_file.read_text() if conversion_review_file else "",
                    "claude_html": _inject_viewer_base_href(claude_file.read_text(), claude_file) if claude_file else "<html><body>Error</body></html>",
                    "gemini_html": _inject_viewer_base_href(gemini_file.read_text(), gemini_file) if gemini_file else "<html><body>Error</body></html>",
                    "gpt55_html": _inject_viewer_base_href(gpt55_file.read_text(), gpt55_file) if gpt55_file else "<html><body><p>Not available for this mode.</p></body></html>",
                    "claude_framework_html": _inject_viewer_base_href(claude_framework_file.read_text(), claude_framework_file) if claude_framework_file else "",
                    "gpt55_framework_html": _inject_viewer_base_href(gpt55_framework_file.read_text(), gpt55_framework_file) if gpt55_framework_file else "",
                    "claude_grounding_html": _inject_viewer_base_href(claude_grounding_file.read_text(), claude_grounding_file) if claude_grounding_file else "",
                    "gpt55_grounding_html": _inject_viewer_base_href(gpt55_grounding_file.read_text(), gpt55_grounding_file) if gpt55_grounding_file else "",
                    "claude_url": claude_file.resolve().as_uri() if claude_file else "",
                    "gemini_url": gemini_file.resolve().as_uri() if gemini_file else "",
                    "gpt55_url": gpt55_file.resolve().as_uri() if gpt55_file else "",
                    "claude_framework_url": claude_framework_file.resolve().as_uri() if claude_framework_file else "",
                    "gpt55_framework_url": gpt55_framework_file.resolve().as_uri() if gpt55_framework_file else "",
                    "claude_grounding_url": claude_grounding_file.resolve().as_uri() if claude_grounding_file else "",
                    "gpt55_grounding_url": gpt55_grounding_file.resolve().as_uri() if gpt55_grounding_file else "",
                    "ds_path": str(ds_file.resolve()) if ds_file else "",
                    "structural_path": str(structural_file.resolve()) if structural_file else "",
                    "site_generation_input_path": str(generation_input_file.resolve()) if generation_input_file else "",
                    "site_generation_input_grounding_path": str(grounding_generation_input_file.resolve()) if grounding_generation_input_file else "",
                    "surface_component_contract_path": str(surface_contract_file.resolve()) if surface_contract_file else "",
                    "surface_component_contract_audit_path": str(surface_contract_audit_file.resolve()) if surface_contract_audit_file else "",
                    "source_style_ledger_path": str(source_style_ledger_file.resolve()) if source_style_ledger_file else "",
                    "design_system_style_audit_path": str(design_style_audit_file.resolve()) if design_style_audit_file else "",
                    "design_system_review_path": str(design_review_file.resolve()) if design_review_file else "",
                    "design_system_conversion_review_path": str(conversion_review_file.resolve()) if conversion_review_file else "",
                }

            # Support both old format (flat) and current nested format.
            if "single" in entry:
                single = read_mode(entry["single"])
            else:
                # Legacy v001 format
                ds_file = version_dir / entry["design_system"]
                claude_file = version_dir / entry["site_claude"]
                gemini_file = version_dir / entry["site_gemini"]
                single = {
                    "design_system": ds_file.read_text() if ds_file.exists() else "",
                    "structural_analysis": "",
                    "site_generation_input": "",
                    "surface_component_contract": "",
                    "surface_component_contract_audit": "",
                    "source_style_ledger": "",
                    "design_system_style_audit": "",
                    "design_system_review": "",
                    "design_system_conversion_review": "",
                    "claude_html": _inject_viewer_base_href(claude_file.read_text(), claude_file) if claude_file.exists() else "<html><body>Error</body></html>",
                    "gemini_html": _inject_viewer_base_href(gemini_file.read_text(), gemini_file) if gemini_file.exists() else "<html><body>Error</body></html>",
                    "gpt55_html": "<html><body><p>Not available for this mode.</p></body></html>",
                    "claude_grounding_html": "",
                    "gpt55_grounding_html": "",
                    "claude_url": claude_file.resolve().as_uri() if claude_file.exists() else "",
                    "gemini_url": gemini_file.resolve().as_uri() if gemini_file.exists() else "",
                    "gpt55_url": "",
                    "claude_grounding_url": "",
                    "gpt55_grounding_url": "",
                    "ds_path": str(ds_file.resolve()) if ds_file.exists() else "",
                    "structural_path": "",
                    "site_generation_input_path": "",
                    "site_generation_input_grounding_path": "",
                    "surface_component_contract_path": "",
                    "surface_component_contract_audit_path": "",
                    "source_style_ledger_path": "",
                    "design_system_style_audit_path": "",
                    "design_system_review_path": "",
                    "design_system_conversion_review_path": "",
                }

            gpt55_direct_html = "<html><body><p>Not available for this version.</p></body></html>"
            gpt55_direct_rel = entry.get("site_gpt55_direct") or entry.get("site_gpt54_direct")
            gpt55_direct_file = version_dir / gpt55_direct_rel if gpt55_direct_rel else None
            if gpt55_direct_file and gpt55_direct_file.exists():
                gpt55_direct_html = _inject_viewer_base_href(gpt55_direct_file.read_text(), gpt55_direct_file)
                gpt55_direct_url = gpt55_direct_file.resolve().as_uri()
                lowered_direct = gpt55_direct_html.lower()
                if (
                    "skipped for this run" not in lowered_direct
                    and "not available for this version" not in lowered_direct
                    and "<h1>error</h1>" not in lowered_direct
                ):
                    has_gpt55_direct = True

            if single.get("claude_framework_html") or single.get("gpt55_framework_html"):
                has_framework_sites = True

            items.append({
                "name": name,
                "screenshot_uri": screenshot_uri,
                "single": single,
                "gpt55_direct_html": gpt55_direct_html,
                "gpt55_direct_url": gpt55_direct_url if gpt55_direct_file and gpt55_direct_file.exists() else "",
            })

        version_data = {
            "display_name": display_name,
            "timestamp": manifest.get("timestamp", ""),
            "structural_analysis_prompt": structural_analysis_prompt,
            "system_prompt": system_prompt,
            "website_prompt": website_prompt,
            "site_generation_skills": site_generation_skills,
            "grounding_sync_prompt": grounding_sync_prompt,
            "site_style_sync_prompt": site_style_sync_prompt,
            "design_system_review_prompt": design_system_review_prompt,
            "design_system_conversion_review_prompt": design_system_conversion_review_prompt,
            "screenshot_direct_prompt": screenshot_direct_prompt,
            "learnings": learnings,
            "has_gpt55_direct": has_gpt55_direct,
            "has_framework_sites": has_framework_sites,
            "has_generated_site": has_generated_site,
            "items": items,
        }

        if initial_version is None:
            initial_version = version
            initial_data_b64 = _encode_viewer_payload(version_data)

        version_index[version] = {
            "display_name": display_name,
            "timestamp": manifest.get("timestamp", ""),
            "item_count": len(items),
            "has_generated_site": has_generated_site,
            "payload": f"viewer-data/{version}.js",
        }
        _write_viewer_payload_script(payload_dir / f"{version}.js", version, version_data)

    valid_versions = [version for version in versions if version in version_index]
    # The comparison viewer is now unified into the Studio project canvas
    # (/project/<version>), which renders the 3-lane layout + combined info
    # sidebar. viewer.html becomes a thin redirect so the URL keeps working and
    # there is a single source of truth. We still build _build_viewer_html data
    # payloads above for any external consumers, but ship a redirect stub here.
    initial_json = json.dumps(initial_version or "")
    html = (
        "<!doctype html><html><head><meta charset=\"utf-8\">"
        "<title>Redirecting to canvas…</title>"
        "<meta name=\"color-scheme\" content=\"dark light\">"
        "<style>body{font-family:system-ui,-apple-system,sans-serif;background:#0a0a0b;"
        "color:#e5e5e5;display:grid;place-items:center;height:100vh;margin:0}"
        "a{color:#34d399}</style>"
        "<script>(function(){var q=new URLSearchParams(location.search);"
        "var v=q.get('version')||q.get('v')||" + initial_json + ";"
        "var target=v?('/project/'+encodeURIComponent(v)):'/studio';"
        "location.replace(target);})();</script></head>"
        "<body><div>Opening the unified canvas… "
        "<a href=\"/studio\">open Studio</a></div></body></html>"
    )

    with open(output_path, "w") as f:
        f.write(html)


def _build_viewer_html(
    versions: list[str],
    data_b64: str | None = None,
    *,
    version_index: dict | None = None,
    initial_version: str | None = None,
    initial_data_b64: str = "",
) -> str:
    versions_json = json.dumps(versions)
    version_index_json = json.dumps(version_index or {})
    embedded_all_data_b64_json = json.dumps(data_b64 or "")
    initial_version_json = json.dumps(initial_version or "")
    initial_data_b64_json = json.dumps(initial_data_b64 or "")

    return f'''<!DOCTYPE html>
<html lang="en" class="dark">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Design System Pipeline Viewer</title>
<script src="https://cdn.tailwindcss.com"></script>
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<script>
tailwind.config = {{
  darkMode: 'class',
  theme: {{
    extend: {{
      fontFamily: {{ sans: ['Inter', 'system-ui', 'sans-serif'] }},
      colors: {{
        border: 'hsl(240 3.7% 15.9%)',
        input: 'hsl(240 3.7% 15.9%)',
        ring: 'hsl(240 4.9% 83.9%)',
        background: 'hsl(240 10% 3.9%)',
        foreground: 'hsl(0 0% 98%)',
        primary: {{ DEFAULT: 'hsl(0 0% 98%)', foreground: 'hsl(240 5.9% 10%)' }},
        secondary: {{ DEFAULT: 'hsl(240 3.7% 15.9%)', foreground: 'hsl(0 0% 98%)' }},
        muted: {{ DEFAULT: 'hsl(240 3.7% 15.9%)', foreground: 'hsl(240 5% 64.9%)' }},
        accent: {{ DEFAULT: 'hsl(240 3.7% 15.9%)', foreground: 'hsl(0 0% 98%)' }},
        card: {{ DEFAULT: 'hsl(240 10% 3.9%)', foreground: 'hsl(0 0% 98%)' }},
      }},
      borderRadius: {{ lg: '0.5rem', md: 'calc(0.5rem - 2px)', sm: 'calc(0.5rem - 4px)' }},
    }},
  }},
}}
</script>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: Inter, system-ui, sans-serif; background: hsl(240 10% 3.9%); color: hsl(0 0% 98%); min-height: 100vh; overflow-x: auto; padding-top: var(--chrome-h, 36px); }}

  /* Shared frost style for all sticky bars */
  .frost {{
    background: hsl(240 10% 2% / 0.92);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
  }}

  /* Top bar */
  .top-bar {{
    position: fixed; top: 0; left: 0; right: 0; z-index: 100;
    border-bottom: 1px solid hsl(240 3.7% 15.9%);
  }}
  .top-bar button {{
    flex: 0 0 auto;
    white-space: nowrap;
  }}
  .top-bar #jump-links button {{
    flex: 0 1 auto;
  }}

  /* Toggle group */
  .toggle-group {{
    display: inline-flex; flex: 0 0 auto; border-radius: 0.375rem; border: 1px solid hsl(240 3.7% 15.9%); overflow: hidden;
  }}
  .toggle-group button {{
    padding: 4px 12px; font-size: 12px; cursor: pointer; border: none;
    background: transparent; color: hsl(240 5% 64.9%); transition: all 0.15s;
    text-transform: capitalize;
    white-space: nowrap;
  }}
  .toggle-group button:not(:last-child) {{ border-right: 1px solid hsl(240 3.7% 15.9%); }}
  .toggle-group button.active {{
    background: hsl(0 0% 98%); color: hsl(240 5.9% 10%); font-weight: 500;
  }}
  .toggle-group button:not(.active):hover {{ background: hsl(240 3.7% 15.9%); color: hsl(0 0% 98%); }}
  #jump-links {{
    max-width: min(52vw, 56rem);
  }}
  #jump-links button {{
    max-width: 12rem;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }}

  .cell-tab-group {{
    display: inline-flex;
    align-items: center;
    flex: 0 0 auto;
    border-radius: 9999px;
    border: 1px solid hsl(240 3.7% 15.9%);
    overflow: hidden;
  }}
  .cell-tab {{
    padding: 3px 10px;
    font-size: 11px;
    font-weight: 500;
    cursor: pointer;
    border: none;
    background: transparent;
    color: hsl(240 5% 64.9%);
    transition: all 0.15s;
    white-space: nowrap;
  }}
  .cell-tab:not(:last-child) {{
    border-right: 1px solid hsl(240 3.7% 15.9%);
  }}
  .cell-tab:hover:not(.active):not(:disabled) {{
    background: hsl(240 3.7% 15.9%);
    color: hsl(0 0% 98%);
  }}
  .cell-tab.active {{
    background: hsl(0 0% 98%);
    color: hsl(240 5.9% 10%);
  }}
  .cell-tab:disabled {{
    cursor: not-allowed;
    opacity: 0.45;
  }}

  /* Output Docs tab strip — scroll horizontally inside the column instead of clipping */
  .md-tabs-scroll {{
    flex: 1 1 auto;
    min-width: 0;
    overflow-x: auto;
    overflow-y: hidden;
    scrollbar-width: thin;
    scrollbar-color: hsl(240 3.7% 25%) transparent;
    -webkit-overflow-scrolling: touch;
  }}
  .md-tabs-scroll::-webkit-scrollbar {{ height: 4px; }}
  .md-tabs-scroll::-webkit-scrollbar-thumb {{ background: hsl(240 3.7% 25%); border-radius: 9999px; }}
  .md-tabs-scroll::-webkit-scrollbar-track {{ background: transparent; }}

  /* Stateful toolbar toggles — fixed label, on/off via .active state */
  button.state-toggle {{
    display: inline-flex; align-items: center; gap: 6px;
  }}
  button.state-toggle::before {{
    content: ""; width: 6px; height: 6px; border-radius: 9999px;
    background: hsl(240 5% 45%); transition: all 0.15s;
  }}
  button.state-toggle.active {{
    background: hsl(160 84% 39% / 0.14) !important;
    border-color: hsl(160 84% 39% / 0.45) !important;
    color: hsl(152 76% 80%) !important;
  }}
  button.state-toggle.active::before {{
    background: hsl(152 70% 55%);
    box-shadow: 0 0 6px hsl(152 70% 55% / 0.8);
  }}

  /* Prompt panel */
  .prompt-panel, .learnings-panel, .structural-panel {{
    display: none;
    position: fixed;
    top: var(--top-bar-h, 0px);
    left: 0;
    right: 0;
    z-index: 95;
    border-bottom: 1px solid hsl(240 3.7% 15.9%);
    background: hsl(240 10% 2% / 0.96);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
  }}
  .prompt-panel.visible, .learnings-panel.visible, .structural-panel.visible {{ display: block; }}

  /* Grid */
  #content {{ width: max-content; min-width: 100%; }}
  .comparison-scroll {{ border-bottom: 1px solid hsl(240 3.7% 15.9%); }}
  .comparison-row {{
    display: grid;
    width: max-content;
  }}
  .cell {{ border-right: 1px solid hsl(240 3.7% 15.9%); position: relative; }}
  .cell:last-child {{ border-right: none; }}
  .cell-label {{
    position: sticky; top: var(--cell-label-top, 0px); z-index: 10;
    border-bottom: 1px solid hsl(240 3.7% 15.9%);
  }}
  .cell-label span {{
    flex: 0 0 auto;
    white-space: nowrap;
  }}
  .screenshot-cell img {{ width: 100%; height: auto; display: block; }}
  .design-system-cell .md-content {{ overflow-y: auto; }}

  /* Markdown */
  .md-content h1 {{ font-size: 18px; color: hsl(0 0% 98%); margin: 0 0 12px 0; font-weight: 600; }}
  .md-content h2 {{ font-size: 15px; color: hsl(217 91% 75%); margin: 16px 0 8px 0; border-bottom: 1px solid hsl(240 3.7% 15.9%); padding-bottom: 4px; font-weight: 600; }}
  .md-content h3 {{ font-size: 14px; color: hsl(240 5% 64.9%); margin: 12px 0 6px 0; font-weight: 500; }}
  .md-content h4 {{ font-size: 13px; color: hsl(240 5% 64.9%); margin: 10px 0 4px 0; font-weight: 500; }}
  .md-content p {{ margin: 6px 0; }}
  .md-content ul, .md-content ol {{ margin: 6px 0 6px 20px; }}
  .md-content li {{ margin: 3px 0; }}
  .md-content code {{ background: hsl(240 5% 12%); padding: 1px 5px; border-radius: 4px; font-size: 12px; color: hsl(191 97% 77%); }}
  .md-content strong {{ color: hsl(0 0% 93%); }}
  .md-content table {{ width: 100%; border-collapse: collapse; margin: 8px 0; font-size: 12px; }}
  .md-content th, .md-content td {{ text-align: left; padding: 4px 8px; border: 1px solid hsl(240 3.7% 15.9%); }}
  .md-content th {{ background: hsl(240 5% 12%); color: hsl(240 5% 64.9%); }}

  /* Iframes — use overflow:clip instead of hidden so sticky still works */
  .iframe-cell {{ overflow: clip; }}
  .iframe-cell iframe {{ border: none; background: #fff; width: 1400px; transform-origin: 0 0; }}

  /* Visual design-system column — single internal scroll, no nested scrollbars */
  .visual-cell {{ overflow: clip; }}
  .visual-cell iframe {{ border: none; background: hsl(240 10% 3.9%); width: 100%; display: block; }}
</style>
</head>
<body class="antialiased">

<!-- Top Bar -->
<div class="top-bar frost" id="top-bar">
  <div class="flex items-center gap-4 px-4 py-1.5">
    <h1 class="text-sm font-semibold tracking-tight whitespace-nowrap">Design System Pipeline Viewer</h1>
    <div class="flex items-center gap-3">
      <label for="version-select" class="text-xs text-muted-foreground">Version</label>
      <select id="version-select" class="h-7 min-w-[28rem] max-w-[40rem] rounded-md border border-input bg-secondary px-3 text-xs text-foreground cursor-pointer focus:outline-none focus:ring-1 focus:ring-ring"></select>
      <div class="toggle-group" id="view-toggle">
        <button data-view="outputs" class="active">Site Outputs</button>
        <button data-view="text-compare">Text Compare</button>
      </div>
      <button id="second-column-toggle" aria-pressed="true" class="state-toggle active h-7 rounded-md border border-input bg-secondary px-3 text-xs text-muted-foreground hover:bg-accent hover:text-foreground transition-colors cursor-pointer" title="Show or hide the Output Docs column">Col 2</button>
      <button id="visual-column-toggle" aria-pressed="false" class="state-toggle h-7 rounded-md border border-input bg-secondary px-3 text-xs text-muted-foreground hover:bg-accent hover:text-foreground transition-colors cursor-pointer" title="Render the extracted design system as a visual column next to the screenshot">Visual</button>
      <button id="prompt-toggle" aria-pressed="false" class="state-toggle h-7 rounded-md border border-input bg-secondary px-3 text-xs text-muted-foreground hover:bg-accent hover:text-foreground transition-colors cursor-pointer" title="Show or hide the prompts panel">Prompts</button>
      <button id="learnings-toggle" aria-pressed="false" class="state-toggle h-7 rounded-md border border-input bg-secondary px-3 text-xs text-muted-foreground hover:bg-accent hover:text-foreground transition-colors cursor-pointer" title="Show or hide the learnings panel">Learnings</button>
      <button id="structural-toggle" aria-pressed="false" class="state-toggle h-7 rounded-md border border-input bg-secondary px-3 text-xs text-muted-foreground hover:bg-accent hover:text-foreground transition-colors cursor-pointer" title="Show or hide the structural-analysis output panel">Structural</button>
      <a href="/studio" class="inline-flex items-center h-7 rounded-md border border-sky-500/30 bg-sky-500/10 px-3 text-xs text-sky-300 hover:bg-sky-500/20 transition-colors cursor-pointer no-underline" title="Open Design System Studio to add a new project (URL + screenshot) and run the full pipeline">Studio \u2197</a>
    </div>
    <div class="flex items-center gap-2 ml-auto">
      <span class="text-xs text-muted-foreground whitespace-nowrap">Screenshots:</span>
      <div class="toggle-group" id="jump-links"></div>
    </div>
    <span class="text-xs text-muted-foreground whitespace-nowrap" id="version-info"></span>
  </div>
</div>

<!-- Prompt Panel -->
<div class="prompt-panel" id="prompt-panel">
  <div class="px-4 py-4 max-h-96 overflow-y-auto"></div>
</div>

<!-- Learnings Panel -->
<div class="learnings-panel" id="learnings-panel">
  <div class="px-4 py-4 max-h-96 overflow-y-auto"></div>
</div>

<!-- Structural Analysis Output Panel -->
<div class="structural-panel" id="structural-panel">
  <div class="px-4 py-4 max-h-[32rem] overflow-y-auto"></div>
</div>

<!-- Content -->
<div id="content">
  <div class="flex items-center justify-center h-72 text-muted-foreground text-sm">Loading...</div>
</div>

<script>
const VERSION_ORDER = {versions_json};
const VERSION_META = {version_index_json};
const EMBEDDED_ALL_DATA_B64 = {embedded_all_data_b64_json};
const INITIAL_VERSION = {initial_version_json};
const INITIAL_DATA_B64 = {initial_data_b64_json};
const ALL_DATA = {{}};
window.__VIEWER_VERSION_PAYLOADS__ = window.__VIEWER_VERSION_PAYLOADS__ || {{}};

if (EMBEDDED_ALL_DATA_B64) {{
  Object.assign(ALL_DATA, JSON.parse(atob(EMBEDDED_ALL_DATA_B64)));
}}
if (INITIAL_VERSION && INITIAL_DATA_B64) {{
  ALL_DATA[INITIAL_VERSION] = JSON.parse(atob(INITIAL_DATA_B64));
}}

let currentVersion = null;
let currentView = 'outputs';
let currentMdArtifact = 'design-system';
let showSecondColumn = true;
let showVisualColumn = false;
const blobUrls = {{}};
const outputUrls = {{}};
const versionLoadPromises = {{}};

function mdToHtml(md) {{
  return marked.parse(md);
}}

function getVersionDisplayName(version) {{
  return ALL_DATA[version]?.display_name || VERSION_META[version]?.display_name || version;
}}

function hasGeneratedSite(version) {{
  return Boolean(
    ALL_DATA[version]?.has_generated_site ||
    VERSION_META[version]?.has_generated_site
  );
}}

function getVersionOptionLabel(version) {{
  return `${{hasGeneratedSite(version) ? '🖼️ ' : ''}}${{getVersionDisplayName(version)}}`;
}}

function getVersionItemCount(version) {{
  return ALL_DATA[version]?.items?.length ?? VERSION_META[version]?.item_count ?? 0;
}}

function getVersionTimestamp(version) {{
  return ALL_DATA[version]?.timestamp || VERSION_META[version]?.timestamp || '';
}}

function loadVersionPayload(version) {{
  if (ALL_DATA[version]) return Promise.resolve(ALL_DATA[version]);

  const payload = window.__VIEWER_VERSION_PAYLOADS__?.[version];
  if (payload) {{
    ALL_DATA[version] = payload;
    return Promise.resolve(payload);
  }}

  const payloadPath = VERSION_META[version]?.payload;
  if (!payloadPath) {{
    return Promise.reject(new Error(`No viewer payload is registered for ${{version}}.`));
  }}

  if (versionLoadPromises[version]) return versionLoadPromises[version];

  versionLoadPromises[version] = new Promise((resolve, reject) => {{
    const script = document.createElement('script');
    script.src = payloadPath;
    script.async = true;
    script.onload = () => {{
      const loaded = window.__VIEWER_VERSION_PAYLOADS__?.[version];
      if (!loaded) {{
        reject(new Error(`Viewer payload script loaded, but did not register ${{version}}.`));
        return;
      }}
      ALL_DATA[version] = loaded;
      resolve(loaded);
    }};
    script.onerror = () => reject(new Error(`Could not load ${{payloadPath}}.`));
    document.head.appendChild(script);
  }}).finally(() => {{
    delete versionLoadPromises[version];
  }});

  return versionLoadPromises[version];
}}

function getVersionsNeededForCurrentView(version) {{
  if (currentView !== 'text-compare') return [version];
  const compareVersions = getComparisonVersions(version);
  return showSecondColumn ? compareVersions : compareVersions.slice(1);
}}

function loadVersionsForCurrentView(version) {{
  const versions = Array.from(new Set([version, ...getVersionsNeededForCurrentView(version)]));
  return Promise.all(versions.map(loadVersionPayload));
}}

function createBlobUrl(html, key) {{
  if (blobUrls[key]) URL.revokeObjectURL(blobUrls[key]);
  const blob = new Blob([html], {{ type: 'text/html' }});
  const url = URL.createObjectURL(blob);
  blobUrls[key] = url;
  return url;
}}

function createOutputUrl(fileUrl, html, key) {{
  // Prefer a blob URL built from the embedded HTML: file:// iframes are blocked
  // when the viewer is served over http(s), and the HTML is already in the payload.
  // Fall back to the on-disk file URL only when no HTML was embedded.
  const url = html ? createBlobUrl(html, key) : fileUrl;
  outputUrls[key] = url;
  return url;
}}

function openInNewTab(key) {{
  if (outputUrls[key]) window.open(outputUrls[key], '_blank');
}}

function openActiveOutput(btn) {{
  openInNewTab(btn.dataset.outputKey || '');
}}

function syncGeneratedSiteOutputs() {{
  const useGroundingOutput = currentMdArtifact === 'grounding';
  document.querySelectorAll('.iframe-cell[data-default-src]').forEach(cell => {{
    const defaultSrc = cell.dataset.defaultSrc || '';
    const groundingSrc = cell.dataset.groundingSrc || '';
    const activeSrc = useGroundingOutput && groundingSrc ? groundingSrc : defaultSrc;
    const iframe = cell.querySelector('iframe');
    if (iframe && activeSrc && iframe.getAttribute('src') !== activeSrc) {{
      iframe.setAttribute('src', activeSrc);
    }}

    const openButton = cell.querySelector('.output-open-button');
    if (openButton) {{
      const defaultKey = cell.dataset.defaultOutputKey || '';
      const groundingKey = cell.dataset.groundingOutputKey || '';
      openButton.dataset.outputKey = useGroundingOutput && groundingKey ? groundingKey : defaultKey;
    }}

    const label = cell.querySelector('.provider-label');
    if (label) {{
      const defaultLabel = cell.dataset.defaultLabel || label.textContent;
      const groundingLabel = cell.dataset.groundingLabel || defaultLabel;
      label.textContent = useGroundingOutput && groundingSrc ? groundingLabel : defaultLabel;
    }}
  }});
}}

function revealInFinder(filePath, btn) {{
  navigator.clipboard.writeText(filePath).then(() => {{
    const orig = btn.textContent;
    btn.textContent = '\\u2713';
    setTimeout(() => btn.textContent = orig, 1500);
  }});
}}

function updateHeaderHeight() {{
  const bar = document.getElementById('top-bar');
  const panel = document.getElementById('prompt-panel');
  const learningsPanel = document.getElementById('learnings-panel');
  const structuralPanel = document.getElementById('structural-panel');
  if (bar) {{
    const barH = bar.offsetHeight;
    const panelH = panel && panel.classList.contains('visible') ? panel.offsetHeight : 0;
    if (learningsPanel) {{
      learningsPanel.style.top = (barH + panelH) + 'px';
    }}
    const learningsH = learningsPanel && learningsPanel.classList.contains('visible') ? learningsPanel.offsetHeight : 0;
    if (structuralPanel) {{
      structuralPanel.style.top = (barH + panelH + learningsH) + 'px';
    }}
    const structuralH = structuralPanel && structuralPanel.classList.contains('visible') ? structuralPanel.offsetHeight : 0;
    const chromeH = barH + panelH + learningsH + structuralH;
    document.documentElement.style.setProperty('--top-bar-h', barH + 'px');
    document.documentElement.style.setProperty('--chrome-h', chromeH + 'px');
    document.documentElement.style.setProperty('--header-h', chromeH + 'px');
    // Cell labels sit below fixed chrome + row heading (~52px)
    const rowHeading = document.querySelector('[id^="row-"]');
    const rowH = rowHeading ? rowHeading.offsetHeight : 52;
    document.documentElement.style.setProperty('--cell-label-top', (chromeH + rowH) + 'px');
  }}
}}

function getModeData(item) {{
  return item?.single || item || {{}};
}}

function setToggleState(id, on) {{
  const button = document.getElementById(id);
  if (!button) return;
  button.classList.toggle('active', on);
  button.setAttribute('aria-pressed', on ? 'true' : 'false');
}}

function updateSecondColumnToggleLabel() {{
  setToggleState('second-column-toggle', showSecondColumn);
}}

function updateVisualColumnToggleLabel() {{
  setToggleState('visual-column-toggle', showVisualColumn);
}}

function getComparisonVersions(version) {{
  const index = VERSION_ORDER.indexOf(version);
  if (index === -1) return VERSION_ORDER.slice(0, 4);
  return VERSION_ORDER.slice(index, index + 4);
}}

function findItemForVersion(version, itemName) {{
  const data = ALL_DATA[version];
  if (!data?.items) return null;
  return data.items.find(item => item.name === itemName) || null;
}}

function renderMdTabs() {{
  return `<div class="cell-tab-group" role="tablist" aria-label="Markdown view selector">
    <button
      class="cell-tab"
      type="button"
      role="tab"
      aria-selected="false"
      data-tab="grounding"
      tabindex="-1"
      onclick="setMdArtifact('grounding')"
      onkeydown="handleMdTabKeydown(event)"
    >Grounding</button>
    <button
      class="cell-tab"
      type="button"
      role="tab"
      aria-selected="false"
      data-tab="design-system"
      tabindex="-1"
      onclick="setMdArtifact('design-system')"
      onkeydown="handleMdTabKeydown(event)"
    >Design system</button>
    <button
      class="cell-tab"
      type="button"
      role="tab"
      aria-selected="false"
      data-tab="generation-input"
      tabindex="-1"
      onclick="setMdArtifact('generation-input')"
      onkeydown="handleMdTabKeydown(event)"
    >Generation input</button>
    <button
      class="cell-tab"
      type="button"
      role="tab"
      aria-selected="false"
      data-tab="ledger"
      tabindex="-1"
      onclick="setMdArtifact('ledger')"
      onkeydown="handleMdTabKeydown(event)"
    >Ledger</button>
    <button
      class="cell-tab"
      type="button"
      role="tab"
      aria-selected="false"
      data-tab="surface-contract"
      tabindex="-1"
      onclick="setMdArtifact('surface-contract')"
      onkeydown="handleMdTabKeydown(event)"
    >Contract</button>
    <button
      class="cell-tab"
      type="button"
      role="tab"
      aria-selected="false"
      data-tab="surface-contract-audit"
      tabindex="-1"
      onclick="setMdArtifact('surface-contract-audit')"
      onkeydown="handleMdTabKeydown(event)"
    >Contract audit</button>
    <button
      class="cell-tab"
      type="button"
      role="tab"
      aria-selected="false"
      data-tab="style-audit"
      tabindex="-1"
      onclick="setMdArtifact('style-audit')"
      onkeydown="handleMdTabKeydown(event)"
    >Style audit</button>
    <button
      class="cell-tab"
      type="button"
      role="tab"
      aria-selected="false"
      data-tab="review"
      tabindex="-1"
      onclick="setMdArtifact('review')"
      onkeydown="handleMdTabKeydown(event)"
    >Review</button>
    <button
      class="cell-tab"
      type="button"
      role="tab"
      aria-selected="false"
      data-tab="conversion-review"
      tabindex="-1"
      onclick="setMdArtifact('conversion-review')"
      onkeydown="handleMdTabKeydown(event)"
    >Conversion</button>
  </div>`;
}}

function syncMdArtifactControls() {{
  document.querySelectorAll('.cell-tab').forEach(button => {{
    const isActive = button.dataset.tab === currentMdArtifact;
    button.classList.toggle('active', isActive);
    button.setAttribute('aria-selected', isActive ? 'true' : 'false');
    button.tabIndex = isActive ? 0 : -1;
  }});

  document.querySelectorAll('.md-pane').forEach(pane => {{
    pane.hidden = pane.dataset.artifact !== currentMdArtifact;
  }});

  document.querySelectorAll('.md-column').forEach(column => {{
    const pathButton = column.querySelector('.md-path-button');
    if (!pathButton) return;

    const designPath = column.dataset.designPath || '';
    const groundingPath = column.dataset.groundingPath || '';
    const generationInputPath = column.dataset.generationInputPath || '';
    const ledgerPath = column.dataset.ledgerPath || '';
    const surfaceContractPath = column.dataset.surfaceContractPath || '';
    const surfaceContractAuditPath = column.dataset.surfaceContractAuditPath || '';
    const styleAuditPath = column.dataset.styleAuditPath || '';
    const reviewPath = column.dataset.reviewPath || '';
    const conversionReviewPath = column.dataset.conversionReviewPath || '';
    const activePath = currentMdArtifact === 'grounding'
      ? groundingPath
      : currentMdArtifact === 'generation-input'
        ? generationInputPath
      : currentMdArtifact === 'ledger'
        ? ledgerPath
      : currentMdArtifact === 'surface-contract'
        ? surfaceContractPath
      : currentMdArtifact === 'surface-contract-audit'
        ? surfaceContractAuditPath
      : currentMdArtifact === 'style-audit'
        ? styleAuditPath
        : currentMdArtifact === 'conversion-review'
          ? conversionReviewPath
        : currentMdArtifact === 'review'
          ? reviewPath
          : designPath;

    pathButton.hidden = !activePath;
    pathButton.dataset.path = activePath;
  }});
}}

function setMdArtifact(tab) {{
  currentMdArtifact = tab;
  syncMdArtifactControls();
  syncGeneratedSiteOutputs();
}}

function handleMdTabKeydown(event) {{
  const current = event.target.closest('.cell-tab');
  if (!current) return;

  const keys = ['ArrowLeft', 'ArrowRight', 'Home', 'End'];
  if (!keys.includes(event.key)) return;

  event.preventDefault();
  const buttons = Array.from(current.closest('.cell-tab-group')?.querySelectorAll('.cell-tab:not(:disabled)') || []);
  if (!buttons.length) return;

  let nextIndex = buttons.indexOf(current);
  if (event.key === 'ArrowRight') nextIndex = (nextIndex + 1) % buttons.length;
  if (event.key === 'ArrowLeft') nextIndex = (nextIndex - 1 + buttons.length) % buttons.length;
  if (event.key === 'Home') nextIndex = 0;
  if (event.key === 'End') nextIndex = buttons.length - 1;

  const next = buttons[nextIndex];
  next.focus();
  setMdArtifact(next.dataset.tab);
}}

function scrollToSection(name) {{
  const target = document.getElementById(`row-${{name}}`);
  if (!target) return;
  const chromeH = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--chrome-h')) || 0;
  const targetTop = window.scrollY + target.getBoundingClientRect().top - chromeH - 8;
  window.scrollTo({{ top: Math.max(0, targetTop), behavior: 'smooth' }});
}}

function renderOutputsView(version, data) {{
  let html = '';
  const hasDirect = !!data.has_gpt55_direct;
  const hasFramework = !!data.has_framework_sites;

  for (const item of data.items) {{
    const modeData = getModeData(item);
    const ds = modeData.design_system || '';
    const structural = modeData.structural_analysis || '';
    const generationInput = modeData.site_generation_input || '';
    const sourceLedger = modeData.source_style_ledger || '';
    const surfaceContract = modeData.surface_component_contract || '';
    const surfaceContractAudit = modeData.surface_component_contract_audit || '';
    const styleAudit = modeData.design_system_style_audit || '';
    const designReview = modeData.design_system_review || '';
    const conversionReview = modeData.design_system_conversion_review || '';
    const dsPath = modeData.ds_path || '';
    const structuralPath = modeData.structural_path || '';
    const generationInputPath = modeData.site_generation_input_path || '';
    const ledgerPath = modeData.source_style_ledger_path || '';
    const surfaceContractPath = modeData.surface_component_contract_path || '';
    const surfaceContractAuditPath = modeData.surface_component_contract_audit_path || '';
    const styleAuditPath = modeData.design_system_style_audit_path || '';
    const reviewPath = modeData.design_system_review_path || '';
    const conversionReviewPath = modeData.design_system_conversion_review_path || '';
    const claudeHtml = modeData.claude_html || '<html><body><p>Not available for this mode</p></body></html>';
    const gpt55Html = modeData.gpt55_html || '<html><body><p>Not available for this mode</p></body></html>';
    const claudeGroundingHtml = modeData.claude_grounding_html || '';
    const gpt55GroundingHtml = modeData.gpt55_grounding_html || '';
    const gpt55DirectHtml = item.gpt55_direct_html || '<html><body><p>Not available for this version.</p></body></html>';
    const claudeFrameworkHtml = modeData.claude_framework_html || '';
    const gpt55FrameworkHtml = modeData.gpt55_framework_html || '';
    const claudeFileUrl = modeData.claude_url || '';
    const gpt55FileUrl = modeData.gpt55_url || '';
    const claudeFrameworkFileUrl = modeData.claude_framework_url || '';
    const gpt55FrameworkFileUrl = modeData.gpt55_framework_url || '';
    const claudeGroundingFileUrl = modeData.claude_grounding_url || '';
    const gpt55GroundingFileUrl = modeData.gpt55_grounding_url || '';
    const gpt55DirectFileUrl = item.gpt55_direct_url || '';
    const claudeKey = `${{version}}-${{item.name}}-claude`;
    const gpt55Key = `${{version}}-${{item.name}}-gpt55`;
    const claudeGroundingKey = `${{version}}-${{item.name}}-claude-grounding`;
    const gpt55GroundingKey = `${{version}}-${{item.name}}-gpt55-grounding`;
    const gpt55DirectKey = `${{version}}-${{item.name}}-gpt55-direct`;
    const claudeFrameworkKey = `${{version}}-${{item.name}}-claude-framework`;
    const gpt55FrameworkKey = `${{version}}-${{item.name}}-gpt55-framework`;
    const claudeUrl = createOutputUrl(claudeFileUrl, claudeHtml, claudeKey);
    const gpt55Url = createOutputUrl(gpt55FileUrl, gpt55Html, gpt55Key);
    const claudeFrameworkUrl = (claudeFrameworkFileUrl || claudeFrameworkHtml) ? createOutputUrl(claudeFrameworkFileUrl, claudeFrameworkHtml, claudeFrameworkKey) : '';
    const gpt55FrameworkUrl = (gpt55FrameworkFileUrl || gpt55FrameworkHtml) ? createOutputUrl(gpt55FrameworkFileUrl, gpt55FrameworkHtml, gpt55FrameworkKey) : '';
    const claudeGroundingUrl = (claudeGroundingFileUrl || claudeGroundingHtml) ? createOutputUrl(claudeGroundingFileUrl, claudeGroundingHtml, claudeGroundingKey) : '';
    const gpt55GroundingUrl = (gpt55GroundingFileUrl || gpt55GroundingHtml) ? createOutputUrl(gpt55GroundingFileUrl, gpt55GroundingHtml, gpt55GroundingKey) : '';
    const gpt55DirectUrl = createOutputUrl(gpt55DirectFileUrl, gpt55DirectHtml, gpt55DirectKey);
    const frameworkColumnCount = hasFramework ? 2 : 0;
    const visibleColumns = 1 + (showVisualColumn ? 1 : 0) + (showSecondColumn ? 1 : 0) + 2 + frameworkColumnCount + (hasDirect ? 1 : 0);
    const visualCell = showVisualColumn ? `
          <div class="cell visual-cell">
            <div class="cell-label frost">
              <div class="flex items-center gap-2 px-4 py-2 text-xs font-medium text-muted-foreground">
                <span>Visual</span>
                <a class="ml-auto text-muted-foreground hover:text-foreground transition-colors text-sm" href="viewer-visual.html?run=${{encodeURIComponent(version)}}&item=${{encodeURIComponent(item.name)}}&variant=single" target="_blank" rel="noopener" title="Open the full visual viewer in a new tab">\\u2197</a>
              </div>
            </div>
            <iframe data-visual-src="viewer-visual.html?run=${{encodeURIComponent(version)}}&item=${{encodeURIComponent(item.name)}}&variant=single&embed=1" loading="lazy" title="Visual design system for ${{item.name}}"></iframe>
          </div>` : '';

    html += `
      <div class="frost px-4 py-1.5 border-b border-border" id="row-${{item.name}}" style="position:sticky; top:var(--header-h, 0px); z-index:50;">
        <h2 class="text-sm font-semibold tracking-tight capitalize">${{item.name}}</h2>
      </div>
      <div class="comparison-scroll">
        <div class="comparison-row" data-name="${{item.name}}" style="grid-template-columns: repeat(${{visibleColumns}}, minmax(320px, 550px));">
          <div class="cell screenshot-cell">
            <div class="cell-label frost">
              <div class="flex items-center gap-2 px-4 py-2 text-xs font-medium text-muted-foreground">Screenshot</div>
            </div>
            <img src="${{item.screenshot_uri}}" alt="${{item.name}}" loading="lazy">
          </div>
          ${{visualCell}}
          ${{showSecondColumn ? `<div class="cell design-system-cell md-column" data-design-path="${{dsPath.replace(/"/g, '&quot;')}}" data-grounding-path="${{structuralPath.replace(/"/g, '&quot;')}}" data-generation-input-path="${{generationInputPath.replace(/"/g, '&quot;')}}" data-ledger-path="${{ledgerPath.replace(/"/g, '&quot;')}}" data-surface-contract-path="${{surfaceContractPath.replace(/"/g, '&quot;')}}" data-surface-contract-audit-path="${{surfaceContractAuditPath.replace(/"/g, '&quot;')}}" data-style-audit-path="${{styleAuditPath.replace(/"/g, '&quot;')}}" data-review-path="${{reviewPath.replace(/"/g, '&quot;')}}" data-conversion-review-path="${{conversionReviewPath.replace(/"/g, '&quot;')}}">
            <div class="cell-label frost">
              <div class="flex items-center gap-3 px-4 py-2 text-xs font-medium text-muted-foreground">
                <span class="shrink-0">Output Docs</span>
                <div class="md-tabs-scroll">${{renderMdTabs()}}</div>
                ${{(dsPath || structuralPath || generationInputPath || ledgerPath || surfaceContractPath || surfaceContractAuditPath || styleAuditPath || reviewPath || conversionReviewPath) ? `<button class="md-path-button shrink-0 text-muted-foreground hover:text-foreground transition-colors cursor-pointer border-none bg-transparent text-sm" data-path="" hidden onclick="revealInFinder(this.dataset.path, this)" title="Copy file path">\\u2197</button>` : ''}}
              </div>
            </div>
            <div class="md-content px-4 py-3 text-xs leading-relaxed text-muted-foreground">
              <div class="md-pane" data-artifact="design-system">${{mdToHtml(ds || 'No design system markdown saved for this item.') }}</div>
              <div class="md-pane" data-artifact="grounding" hidden>${{mdToHtml(structural || 'No grounding markdown saved for this item.') }}</div>
              <div class="md-pane" data-artifact="generation-input" hidden>${{mdToHtml(generationInput || 'No site generation input saved for this item.') }}</div>
              <div class="md-pane" data-artifact="ledger" hidden>${{mdToHtml(sourceLedger || 'No source-style ledger saved for this item.') }}</div>
              <div class="md-pane" data-artifact="surface-contract" hidden><pre>${{(surfaceContract || 'No surface/component contract saved for this item.').replace(/</g, '&lt;')}}</pre></div>
              <div class="md-pane" data-artifact="surface-contract-audit" hidden>${{mdToHtml(surfaceContractAudit || 'No surface/component contract audit saved for this item.') }}</div>
              <div class="md-pane" data-artifact="style-audit" hidden><pre>${{(styleAudit || 'No design-system style audit saved for this item.').replace(/</g, '&lt;')}}</pre></div>
              <div class="md-pane" data-artifact="review" hidden>${{mdToHtml(designReview || 'No design-system review saved for this item.') }}</div>
              <div class="md-pane" data-artifact="conversion-review" hidden>${{mdToHtml(conversionReview || 'No design-system conversion review saved for this item.') }}</div>
            </div>
          </div>` : ''}}
          <div class="cell iframe-cell" data-default-src="${{gpt55Url}}" data-grounding-src="${{gpt55GroundingUrl}}" data-default-output-key="${{gpt55Key}}" data-grounding-output-key="${{gpt55GroundingUrl ? gpt55GroundingKey : ''}}" data-default-label="GPT-5.5" data-grounding-label="GPT-5.5 Grounding">
            <div class="cell-label frost">
              <div class="flex items-center gap-2 px-4 py-2 text-xs font-medium text-muted-foreground">
                <span class="provider-label inline-flex items-center rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-medium text-emerald-400 ring-1 ring-inset ring-emerald-500/20">GPT-5.5</span>
                <button class="output-open-button ml-auto text-muted-foreground hover:text-foreground transition-colors cursor-pointer border-none bg-transparent text-sm" data-output-key="${{gpt55Key}}" onclick="openActiveOutput(this)" title="Open in new tab">\\u2197</button>
              </div>
            </div>
            <iframe src="${{gpt55Url}}" loading="lazy"></iframe>
          </div>
          <div class="cell iframe-cell" data-default-src="${{claudeUrl}}" data-grounding-src="${{claudeGroundingUrl}}" data-default-output-key="${{claudeKey}}" data-grounding-output-key="${{claudeGroundingUrl ? claudeGroundingKey : ''}}" data-default-label="Claude Opus 4.8" data-grounding-label="Claude Grounding">
            <div class="cell-label frost">
              <div class="flex items-center gap-2 px-4 py-2 text-xs font-medium text-muted-foreground">
                <span class="provider-label inline-flex items-center rounded-full bg-violet-500/10 px-2 py-0.5 text-[10px] font-medium text-violet-400 ring-1 ring-inset ring-violet-500/20">Claude Opus 4.8</span>
                <button class="output-open-button ml-auto text-muted-foreground hover:text-foreground transition-colors cursor-pointer border-none bg-transparent text-sm" data-output-key="${{claudeKey}}" onclick="openActiveOutput(this)" title="Open in new tab">\\u2197</button>
              </div>
            </div>
            <iframe src="${{claudeUrl}}" loading="lazy"></iframe>
          </div>
          ${{hasFramework && gpt55FrameworkUrl ? `<div class="cell iframe-cell" data-default-src="${{gpt55FrameworkUrl}}" data-default-output-key="${{gpt55FrameworkKey}}" data-default-label="GPT-5.5 Framework">
            <div class="cell-label frost">
              <div class="flex items-center gap-2 px-4 py-2 text-xs font-medium text-muted-foreground">
                <span class="provider-label inline-flex items-center rounded-full bg-teal-500/10 px-2 py-0.5 text-[10px] font-medium text-teal-300 ring-1 ring-inset ring-teal-500/20">GPT-5.5 Framework</span>
                <button class="output-open-button ml-auto text-muted-foreground hover:text-foreground transition-colors cursor-pointer border-none bg-transparent text-sm" data-output-key="${{gpt55FrameworkKey}}" onclick="openActiveOutput(this)" title="Open in new tab">\\u2197</button>
              </div>
            </div>
            <iframe src="${{gpt55FrameworkUrl}}" loading="lazy"></iframe>
          </div>` : ''}}
          ${{hasFramework && claudeFrameworkUrl ? `<div class="cell iframe-cell" data-default-src="${{claudeFrameworkUrl}}" data-default-output-key="${{claudeFrameworkKey}}" data-default-label="Claude Framework">
            <div class="cell-label frost">
              <div class="flex items-center gap-2 px-4 py-2 text-xs font-medium text-muted-foreground">
                <span class="provider-label inline-flex items-center rounded-full bg-teal-500/10 px-2 py-0.5 text-[10px] font-medium text-teal-300 ring-1 ring-inset ring-teal-500/20">Claude Framework</span>
                <button class="output-open-button ml-auto text-muted-foreground hover:text-foreground transition-colors cursor-pointer border-none bg-transparent text-sm" data-output-key="${{claudeFrameworkKey}}" onclick="openActiveOutput(this)" title="Open in new tab">\\u2197</button>
              </div>
            </div>
            <iframe src="${{claudeFrameworkUrl}}" loading="lazy"></iframe>
          </div>` : ''}}
          ${{hasDirect ? `<div class="cell iframe-cell">
            <div class="cell-label frost">
              <div class="flex items-center gap-2 px-4 py-2 text-xs font-medium text-muted-foreground">
                <span class="inline-flex items-center rounded-full bg-amber-500/10 px-2 py-0.5 text-[10px] font-medium text-amber-400 ring-1 ring-inset ring-amber-500/20">GPT-5.5 Direct</span>
                <button class="ml-auto text-muted-foreground hover:text-foreground transition-colors cursor-pointer border-none bg-transparent text-sm" onclick="openInNewTab('${{gpt55DirectKey}}')" title="Open in new tab">\\u2197</button>
              </div>
            </div>
            <iframe src="${{gpt55DirectUrl}}" loading="lazy"></iframe>
          </div>` : ''}}
        </div>
      </div>`;
  }}

  return html;
}}

function renderTextCompareView(version, data) {{
  const compareVersions = getComparisonVersions(version);
  const compareVersionsToRender = showSecondColumn ? compareVersions : compareVersions.slice(1);
  let html = '';

  for (const item of data.items) {{
    let columns = `
      <div class="cell screenshot-cell">
        <div class="cell-label frost">
          <div class="flex items-center gap-2 px-4 py-2 text-xs font-medium text-muted-foreground">Screenshot</div>
        </div>
        <img src="${{item.screenshot_uri}}" alt="${{item.name}}" loading="lazy">
      </div>`;

    for (const compareVersion of compareVersionsToRender) {{
      const compareItem = findItemForVersion(compareVersion, item.name);
      const modeData = compareItem ? getModeData(compareItem) : {{}};
      const ds = modeData.design_system || '';
      const structural = modeData.structural_analysis || '';
      const generationInput = modeData.site_generation_input || '';
      const sourceLedger = modeData.source_style_ledger || '';
      const surfaceContract = modeData.surface_component_contract || '';
      const surfaceContractAudit = modeData.surface_component_contract_audit || '';
      const styleAudit = modeData.design_system_style_audit || '';
      const designReview = modeData.design_system_review || '';
      const conversionReview = modeData.design_system_conversion_review || '';
      const dsPath = modeData.ds_path || '';
      const structuralPath = modeData.structural_path || '';
      const generationInputPath = modeData.site_generation_input_path || '';
      const ledgerPath = modeData.source_style_ledger_path || '';
      const surfaceContractPath = modeData.surface_component_contract_path || '';
      const surfaceContractAuditPath = modeData.surface_component_contract_audit_path || '';
      const styleAuditPath = modeData.design_system_style_audit_path || '';
      const reviewPath = modeData.design_system_review_path || '';
      const conversionReviewPath = modeData.design_system_conversion_review_path || '';
      const isSelectedVersion = compareVersion === version;
      const versionLabel = getVersionDisplayName(compareVersion);
      const label = isSelectedVersion ? `${{versionLabel}} (current)` : versionLabel;

      columns += `
        <div class="cell design-system-cell md-column" data-design-path="${{dsPath.replace(/"/g, '&quot;')}}" data-grounding-path="${{structuralPath.replace(/"/g, '&quot;')}}" data-generation-input-path="${{generationInputPath.replace(/"/g, '&quot;')}}" data-ledger-path="${{ledgerPath.replace(/"/g, '&quot;')}}" data-surface-contract-path="${{surfaceContractPath.replace(/"/g, '&quot;')}}" data-surface-contract-audit-path="${{surfaceContractAuditPath.replace(/"/g, '&quot;')}}" data-style-audit-path="${{styleAuditPath.replace(/"/g, '&quot;')}}" data-review-path="${{reviewPath.replace(/"/g, '&quot;')}}" data-conversion-review-path="${{conversionReviewPath.replace(/"/g, '&quot;')}}">
          <div class="cell-label frost">
            <div class="flex items-center gap-3 px-4 py-2 text-xs font-medium text-muted-foreground">
              <span class="shrink-0 whitespace-nowrap uppercase tracking-wider">${{label}}</span>
              <div class="md-tabs-scroll">${{renderMdTabs()}}</div>
              ${{(dsPath || structuralPath || generationInputPath || ledgerPath || surfaceContractPath || surfaceContractAuditPath || styleAuditPath || reviewPath || conversionReviewPath) ? `<button class="md-path-button shrink-0 text-muted-foreground hover:text-foreground transition-colors cursor-pointer border-none bg-transparent text-sm" data-path="" hidden onclick="revealInFinder(this.dataset.path, this)" title="Copy file path">\\u2197</button>` : ''}}
            </div>
          </div>
          <div class="md-content px-4 py-3 text-xs leading-relaxed text-muted-foreground">
            <div class="md-pane" data-artifact="design-system">${{mdToHtml(ds || 'No design system markdown saved for this item in this version.') }}</div>
            <div class="md-pane" data-artifact="grounding" hidden>${{mdToHtml(structural || 'No grounding markdown saved for this item in this version.') }}</div>
            <div class="md-pane" data-artifact="generation-input" hidden>${{mdToHtml(generationInput || 'No site generation input saved for this item in this version.') }}</div>
            <div class="md-pane" data-artifact="ledger" hidden>${{mdToHtml(sourceLedger || 'No source-style ledger saved for this item in this version.') }}</div>
            <div class="md-pane" data-artifact="surface-contract" hidden><pre>${{(surfaceContract || 'No surface/component contract saved for this item in this version.').replace(/</g, '&lt;')}}</pre></div>
            <div class="md-pane" data-artifact="surface-contract-audit" hidden>${{mdToHtml(surfaceContractAudit || 'No surface/component contract audit saved for this item in this version.') }}</div>
            <div class="md-pane" data-artifact="style-audit" hidden><pre>${{(styleAudit || 'No design-system style audit saved for this item in this version.').replace(/</g, '&lt;')}}</pre></div>
            <div class="md-pane" data-artifact="review" hidden>${{mdToHtml(designReview || 'No design-system review saved for this item in this version.') }}</div>
            <div class="md-pane" data-artifact="conversion-review" hidden>${{mdToHtml(conversionReview || 'No design-system conversion review saved for this item in this version.') }}</div>
          </div>
        </div>`;
    }}

    html += `
      <div class="frost px-4 py-1.5 border-b border-border" id="row-${{item.name}}" style="position:sticky; top:var(--header-h, 0px); z-index:50;">
        <h2 class="text-sm font-semibold tracking-tight capitalize">${{item.name}}</h2>
      </div>
      <div class="comparison-scroll">
        <div class="comparison-row" data-name="${{item.name}}" style="grid-template-columns: repeat(${{1 + compareVersionsToRender.length}}, minmax(320px, 550px));">
          ${{columns}}
        </div>
      </div>`;
  }}

  return html;
}}

function sizeComparisonRows() {{
  document.querySelectorAll('.comparison-row').forEach(row => {{
    const img = row.querySelector('.screenshot-cell img');
    const mdColumns = row.querySelectorAll('.md-column');
    const iframeCells = row.querySelectorAll('.iframe-cell');
    const visualCells = row.querySelectorAll('.visual-cell');

    const applyHeights = () => {{
      const h = img.offsetHeight;
      if (h <= 0) return;

      mdColumns.forEach(column => {{
        const mdContent = column.querySelector('.md-content');
        const labelH = column.querySelector('.cell-label')?.offsetHeight || 0;
        if (mdContent) mdContent.style.maxHeight = (h - labelH) + 'px';
      }});

      iframeCells.forEach(cell => {{
        const colWidth = cell.clientWidth;
        const scale = colWidth / 1400;
        const iframe = cell.querySelector('iframe');
        if (iframe) {{
          iframe.style.transform = `scale(${{scale}})`;
          iframe.style.height = (h / scale) + 'px';
          cell.style.height = h + 'px';
        }}
      }});

      // Visual column: 1:1 iframe that fills the row height and owns the only
      // scrollbar (no nested md-content scroll). Lazy-load src on first sizing.
      visualCells.forEach(cell => {{
        const labelH = cell.querySelector('.cell-label')?.offsetHeight || 0;
        const iframe = cell.querySelector('iframe');
        if (!iframe) return;
        const src = iframe.getAttribute('data-visual-src');
        if (src && !iframe.getAttribute('src')) iframe.setAttribute('src', src);
        cell.style.height = h + 'px';
        iframe.style.height = (h - labelH) + 'px';
      }});
    }};

    if (img.complete && img.naturalHeight > 0) applyHeights();
    else img.addEventListener('load', applyHeights);
  }});
}}

function setupSectionObserver() {{
  if (window._sectionObserver) window._sectionObserver.disconnect();
  const headings = document.querySelectorAll('[id^="row-"]');
  window._sectionObserver = new IntersectionObserver((entries) => {{
    for (const entry of entries) {{
      if (entry.isIntersecting) {{
        const name = entry.target.id.replace('row-', '');
        document.querySelectorAll('#jump-links button').forEach(b => {{
          b.classList.toggle('active', b.dataset.section === name);
        }});
      }}
    }}
  }}, {{ rootMargin: '-10% 0px -80% 0px' }});
  headings.forEach(h => window._sectionObserver.observe(h));
}}

function loadVersion(version) {{
  const scrollY = (version === currentVersion) ? window.scrollY : 0;
  currentVersion = version;

  const itemCount = getVersionItemCount(version);
  const timestamp = getVersionTimestamp(version);
  document.getElementById('version-info').textContent =
    (timestamp || '') + (itemCount ? ' \\u00b7 ' + itemCount + ' screenshots' : '');

  if (!ALL_DATA[version]) {{
    document.getElementById('content').innerHTML =
      `<div class="flex items-center justify-center h-72 text-muted-foreground text-sm">Loading ${{getVersionDisplayName(version)}}...</div>`;
  }}

  loadVersionsForCurrentView(version)
    .then(() => {{
      if (currentVersion !== version) return;
      const data = ALL_DATA[version];
      if (!data) throw new Error(`No data loaded for ${{version}}.`);
      renderLoadedVersion(version, data, scrollY);
    }})
    .catch(error => {{
      if (currentVersion !== version) return;
      document.getElementById('content').innerHTML =
        `<div class="flex items-center justify-center h-72 text-red-300 text-sm">${{error.message}}</div>`;
    }});
}}

function renderLoadedVersion(version, data, scrollY) {{

  document.getElementById('version-info').textContent =
    (data.timestamp || '') + ' \\u00b7 ' + data.items.length + ' screenshots';

  // Prompt panel
  const panel = document.getElementById('prompt-panel').querySelector('div') || document.getElementById('prompt-panel');
  let promptHtml = '';
  if (data.structural_analysis_prompt) {{
    promptHtml += `<h3 class="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">Structural Analysis Prompt</h3>
      <pre class="bg-secondary/50 border border-border rounded-lg p-3 text-xs leading-relaxed text-muted-foreground whitespace-pre-wrap break-words mb-4">${{data.structural_analysis_prompt.replace(/</g, '&lt;')}}</pre>`;
  }}
  if (data.system_prompt) {{
    promptHtml += `<h3 class="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">Design System Extraction Prompt</h3>
      <pre class="bg-secondary/50 border border-border rounded-lg p-3 text-xs leading-relaxed text-muted-foreground whitespace-pre-wrap break-words mb-4">${{data.system_prompt.replace(/</g, '&lt;')}}</pre>`;
  }}
  if (data.grounding_sync_prompt) {{
    promptHtml += `<h3 class="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">Grounding Sync Prompt</h3>
      <pre class="bg-secondary/50 border border-border rounded-lg p-3 text-xs leading-relaxed text-muted-foreground whitespace-pre-wrap break-words mb-4">${{data.grounding_sync_prompt.replace(/</g, '&lt;')}}</pre>`;
  }}
  if (data.site_style_sync_prompt) {{
    promptHtml += `<h3 class="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">Site Style Sync Prompt</h3>
      <pre class="bg-secondary/50 border border-border rounded-lg p-3 text-xs leading-relaxed text-muted-foreground whitespace-pre-wrap break-words mb-4">${{data.site_style_sync_prompt.replace(/</g, '&lt;')}}</pre>`;
  }}
  if (data.design_system_review_prompt) {{
    promptHtml += `<h3 class="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">Design System Review Prompt</h3>
      <pre class="bg-secondary/50 border border-border rounded-lg p-3 text-xs leading-relaxed text-muted-foreground whitespace-pre-wrap break-words mb-4">${{data.design_system_review_prompt.replace(/</g, '&lt;')}}</pre>`;
  }}
  if (data.design_system_conversion_review_prompt) {{
    promptHtml += `<h3 class="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">Design System Conversion Review Prompt</h3>
      <pre class="bg-secondary/50 border border-border rounded-lg p-3 text-xs leading-relaxed text-muted-foreground whitespace-pre-wrap break-words mb-4">${{data.design_system_conversion_review_prompt.replace(/</g, '&lt;')}}</pre>`;
  }}
  if (data.website_prompt) {{
    promptHtml += `<h3 class="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">Website Generation Prompt</h3>
      <pre class="bg-secondary/50 border border-border rounded-lg p-3 text-xs leading-relaxed text-muted-foreground whitespace-pre-wrap break-words mb-4">${{data.website_prompt.replace(/</g, '&lt;')}}</pre>`;
  }}
  if (Array.isArray(data.site_generation_skills) && data.site_generation_skills.length) {{
    promptHtml += `<h3 class="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">Active Site Generation Skills</h3>`;
    for (const skill of data.site_generation_skills) {{
      const skillName = (skill.name || 'unnamed skill').replace(/</g, '&lt;');
      const skillPath = (skill.path || '').replace(/</g, '&lt;');
      const skillContent = (skill.content || '').replace(/</g, '&lt;');
      promptHtml += `<div class="mb-4">
        <div class="mb-1 flex items-center gap-2 text-xs text-muted-foreground">
          <span class="font-medium text-foreground">${{skillName}}</span>
          <span>${{skillPath}}</span>
        </div>
        <pre class="bg-secondary/50 border border-border rounded-lg p-3 text-xs leading-relaxed text-muted-foreground whitespace-pre-wrap break-words">${{skillContent}}</pre>
      </div>`;
    }}
  }}
  if (data.screenshot_direct_prompt) {{
    promptHtml += `<h3 class="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">GPT-5.5 Screenshot Direct Prompt</h3>
      <pre class="bg-secondary/50 border border-border rounded-lg p-3 text-xs leading-relaxed text-muted-foreground whitespace-pre-wrap break-words mb-4">${{data.screenshot_direct_prompt.replace(/</g, '&lt;')}}</pre>`;
  }}
  if (!promptHtml) promptHtml = '<p class="text-muted-foreground text-sm">No prompts saved for this version.</p>';
  panel.innerHTML = promptHtml;

  const learningsPanel = document.getElementById('learnings-panel').querySelector('div') || document.getElementById('learnings-panel');
  const learningsHtml = data.learnings
    ? `<div class="md-content text-xs leading-relaxed text-muted-foreground">${{mdToHtml(data.learnings)}}</div>`
    : '<p class="text-muted-foreground text-sm">No learnings saved for this version.</p>';
  learningsPanel.innerHTML = learningsHtml;

  const structuralPanel = document.getElementById('structural-panel').querySelector('div') || document.getElementById('structural-panel');
  const structuralSections = data.items.map(item => {{
    const modeData = getModeData(item);
    const structural = modeData.structural_analysis || '';
    const structuralPath = modeData.structural_path || '';
    const heading = item.name.charAt(0).toUpperCase() + item.name.slice(1);
    const copyBtn = structuralPath
      ? `<button class="ml-2 text-muted-foreground hover:text-foreground transition-colors cursor-pointer border-none bg-transparent text-sm" onclick="revealInFinder('${{structuralPath.replace(/'/g, "\\\\'")}}', this)" title="Copy file path">\\u2197</button>`
      : '';
    return `<section class="mb-5">
      <div class="flex items-center gap-2 mb-2">
        <h3 class="text-xs font-medium text-muted-foreground uppercase tracking-wider">${{heading}}</h3>
        ${{copyBtn}}
      </div>
      <pre class="bg-secondary/50 border border-border rounded-lg p-3 text-xs leading-relaxed text-muted-foreground whitespace-pre-wrap break-words">${{(structural || 'No structural analysis output saved for this item.').replace(/</g, '&lt;')}}</pre>
    </section>`;
  }}).join('');
  structuralPanel.innerHTML = structuralSections || '<p class="text-muted-foreground text-sm">No structural analysis output saved for this version.</p>';

  // Jump links
  const jumpHtml = data.items.map((item, i) =>
    `<button data-section="${{item.name}}" class="${{i === 0 ? 'active' : ''}}" onclick="scrollToSection('${{item.name}}')">${{item.name}}</button>`
  ).join('');
  document.getElementById('jump-links').innerHTML = jumpHtml;
  const contentHtml = currentView === 'text-compare'
    ? renderTextCompareView(version, data)
    : renderOutputsView(version, data);
  document.getElementById('content').innerHTML = contentHtml;

  requestAnimationFrame(() => {{
    updateHeaderHeight();
    syncMdArtifactControls();
    syncGeneratedSiteOutputs();
    sizeComparisonRows();

    if (scrollY > 0) window.scrollTo(0, scrollY);
    setupSectionObserver();
  }});
}}

// Init
const select = document.getElementById('version-select');
const versions = VERSION_ORDER;
for (const v of versions) {{
  const opt = document.createElement('option');
  opt.value = v; opt.textContent = getVersionOptionLabel(v);
  select.appendChild(opt);
}}
select.addEventListener('change', () => loadVersion(select.value));

document.getElementById('view-toggle').addEventListener('click', (e) => {{
  const btn = e.target.closest('button[data-view]');
  if (!btn || btn.classList.contains('active')) return;
  document.querySelectorAll('#view-toggle button').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  currentView = btn.dataset.view;
  loadVersion(select.value);
}});

document.getElementById('second-column-toggle').addEventListener('click', () => {{
  showSecondColumn = !showSecondColumn;
  updateSecondColumnToggleLabel();
  loadVersion(select.value);
}});

document.getElementById('visual-column-toggle').addEventListener('click', () => {{
  showVisualColumn = !showVisualColumn;
  updateVisualColumnToggleLabel();
  loadVersion(select.value);
}});

document.getElementById('prompt-toggle').addEventListener('click', () => {{
  const panel = document.getElementById('prompt-panel');
  const on = panel.classList.toggle('visible');
  setToggleState('prompt-toggle', on);
  updateHeaderHeight();
}});

document.getElementById('learnings-toggle').addEventListener('click', () => {{
  const panel = document.getElementById('learnings-panel');
  const on = panel.classList.toggle('visible');
  setToggleState('learnings-toggle', on);
  updateHeaderHeight();
}});

document.getElementById('structural-toggle').addEventListener('click', () => {{
  const panel = document.getElementById('structural-panel');
  const on = panel.classList.toggle('visible');
  setToggleState('structural-toggle', on);
  updateHeaderHeight();
}});

window.addEventListener('resize', () => {{
  updateHeaderHeight();
  sizeComparisonRows();
}});

updateSecondColumnToggleLabel();
updateVisualColumnToggleLabel();

function versionFromUrl() {{
  const params = new URLSearchParams(location.search);
  const requested = (params.get('version') || params.get('v') || '').trim();
  if (requested) return requested;
  const hash = (location.hash || '').replace(/^#/, '').trim();
  return hash || null;
}}

function resolveInitialVersion() {{
  const requested = versionFromUrl();
  if (requested && (versions.includes(requested) || VERSION_META[requested])) {{
    return requested;
  }}
  return versions[0] || null;
}}

function ensureVersionOption(version) {{
  if (!version || [...select.options].some(o => o.value === version)) return;
  if (!VERSION_META[version]) return;
  const opt = document.createElement('option');
  opt.value = version;
  opt.textContent = getVersionOptionLabel(version);
  select.appendChild(opt);
}}

const initialVersion = resolveInitialVersion();
if (initialVersion) {{
  ensureVersionOption(initialVersion);
  select.value = initialVersion;
  loadVersion(initialVersion);
}} else document.getElementById('content').innerHTML = '<div class="flex items-center justify-center h-72 text-muted-foreground text-sm">No runs found. Run python run_pipeline.py first.</div>';
</script>
</body>
</html>'''


def log(msg: str):
    """Print with immediate flush for background task visibility."""
    print(msg, flush=True)


def get_previous_version_dirs(current_version: str) -> list[Path]:
    """Return prior version directories in reverse lexical version order."""
    return sorted([
        d for d in RUNS_DIR.iterdir()
        if d.is_dir() and d.name.startswith("v") and d.name[1:].isdigit() and d.name != current_version
    ], key=lambda p: p.name, reverse=True)


def find_relevant_memory_files(version_dir: Path) -> list[Path]:
    """Return curated memory files worth including in version learnings."""
    candidates = [
        version_dir / "memory.md",
        PROJECT_DIR / "memory.md",
        Path.home() / ".codex" / "memory.md",
    ]
    return [path.resolve() for path in candidates if path.exists() and path.is_file()]


def ensure_version_learnings(version: str, version_dir: Path) -> None:
    """Create a learnings scaffold with prompt diffs when none exists."""
    version_dir = version_dir.resolve()
    runs_dir = RUNS_DIR.resolve()
    learnings_path = version_dir / "learnings.md"
    if learnings_path.exists():
        return

    previous_versions = get_previous_version_dirs(version)
    previous_version_dir = previous_versions[0] if previous_versions else None

    prompt_specs = [
        ("structural-analysis-prompt.md", "Structural Analysis Prompt"),
        ("system-prompt.md", "Design System Prompt"),
        ("grounding-sync-prompt.md", "Grounding Sync Prompt"),
        ("site-style-sync-prompt.md", "Site Style Sync Prompt"),
        ("website-gen-prompt.md", "Website Generation Prompt"),
        ("website-gen-framework-prompt.md", "Framework Generation Prompt"),
        ("section-inventory-prompt.md", "Section Inventory Prompt"),
        ("section-grounding-prompt.md", "Section Grounding Prompt"),
        ("grounding-merge-prompt.md", "Grounding Merge Prompt"),
        ("section-transition-prompt.md", "Section Transition Prompt"),
        ("full-page-review-prompt.md", "Full-page Review Prompt"),
        ("color-sync-prompt.md", "Color Sync Prompt"),
        ("design-system-review-prompt.md", "Design System Review Prompt"),
        ("site-generation-providers.txt", "Site Generation Providers"),
        ("site-generation-source.txt", "Site Generation Source"),
        ("site-generation-skills.txt", "Site Generation Skills"),
    ]

    lines: list[str] = [
        f"# {version} Learnings",
        "",
        "- Add observations about this run here.",
        "",
        "## Prompt Diffs",
        "",
    ]

    if previous_version_dir:
        lines.append(f"- Previous version used for comparison: `{previous_version_dir.name}`")
        lines.append("")
    else:
        lines.append("- No previous version was found, so prompt diffs could not be generated.")
        lines.append("")

    for filename, title in prompt_specs:
        current_path = version_dir / filename
        if not current_path.exists():
            continue

        previous_path = previous_version_dir / filename if previous_version_dir else None
        current_lines = current_path.read_text().splitlines()
        previous_lines = previous_path.read_text().splitlines() if previous_path and previous_path.exists() else []

        diff = "\n".join(difflib.unified_diff(
            previous_lines,
            current_lines,
            fromfile=str(previous_path.resolve().relative_to(runs_dir)) if previous_path and previous_path.exists() else f"(missing)/{filename}",
            tofile=str(current_path.resolve().relative_to(runs_dir)),
            lineterm="",
        ))

        lines.append(f"### {title}")
        lines.append("")
        if diff:
            lines.append("```diff")
            lines.append(diff)
            lines.append("```")
        else:
            lines.append("- No changes from the previous version.")
        lines.append("")

    memory_files = find_relevant_memory_files(version_dir)
    lines.append("## Memory Context")
    lines.append("")
    if memory_files:
        lines.append("- Curated memory files found for this workspace/version:")
        lines.append("")
        for memory_file in memory_files:
            lines.append(f"### `{memory_file}`")
            lines.append("")
            lines.append("```md")
            lines.append(memory_file.read_text().rstrip())
            lines.append("```")
            lines.append("")
    else:
        lines.append("- No curated repo/Codex memory file was found (`memory.md`).")
        lines.append("- Raw archived sessions and SQLite state were not included because they are not curated version memory.")
        lines.append("")

    learnings_path.write_text("\n".join(lines).rstrip() + "\n")


def design_system_is_usable(text: str) -> bool:
    """Return True when a saved design system should be used for site generation."""
    stripped = text.strip()
    return bool(stripped) and not stripped.startswith("# Error") and not stripped.startswith("# Skipped")


def site_output_needs_regeneration(path: Path) -> bool:
    """Return True when a site HTML file is missing or contains a known placeholder/error."""
    if not path.exists():
        return True

    text = path.read_text().strip()
    if not text:
        return True

    lowered = text.lower()
    failure_markers = (
        "<h1>error</h1>",
        "<h1>framework error</h1>",
        "did not complete for this run",
        "site generation was skipped for this run",
        "sectioned mode was skipped for this run",
        "direct screenshot-to-website generation was skipped for this run",
        "<body>error</body>",
    )
    if any(marker in lowered for marker in failure_markers):
        return True

    return not html_document_is_complete(text)


def design_system_review_needs_regeneration(path: Path) -> bool:
    """Return True when a design-system review artifact is missing or unusable."""
    if not path.exists():
        return True
    try:
        payload = json.loads(path.read_text())
    except json.JSONDecodeError:
        return True
    return (
        not isinstance(payload, dict)
        or "weighted_score" not in payload
        or "section_reviews" not in payload
        or not str(payload.get("raw_response", "")).strip()
        or str(payload.get("verdict", "")).strip().lower().startswith("review failed")
    )


def run_pipeline(
    version: str,
    screenshots_dir: Path,
    config_path: str | None = None,
    verbose: bool = True,
    single_only: bool = False,
    sites_only: bool = False,
    framework_sites: bool = False,
    vanilla_sites: bool = False,
    design_only: bool = False,
    surface_map_only: bool = False,
    skip_design_system_review: bool = False,
    run_reviews: bool | None = None,
    design_system_strategy: str = "one-shot",
    reuse_analysis_from: str | None = None,
    review_guidance_from: str | None = None,
    design_system_seed_from: str | None = None,
    design_system_best_seed_from: str | None = None,
    conversion_review_guidance_from: str | None = None,
    conversion_review_best_guidance_from: str | None = None,
    surface_map_review_guidance_from: str | None = None,
    surface_map_seed_from: str | None = None,
    surface_map_best_seed_from: str | None = None,
    surface_map_use_best_existing_from: str | None = None,
    surface_map_mode: str | None = None,
    reuse_section_groundings_from: str | None = None,
    assets_only: bool = False,
    site_assets_enabled: bool | None = None,
):
    """Run the current single-path pipeline on all screenshots in the directory."""
    load_api_keys()

    version_dir = RUNS_DIR / version
    version_dir.mkdir(parents=True, exist_ok=True)

    # Find all screenshots
    screenshot_files = sorted([
        f for f in screenshots_dir.iterdir()
        if f.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")
    ])

    if not screenshot_files:
        log(f"No screenshots found in {screenshots_dir}")
        sys.exit(1)

    log(f"Pipeline run: {version}")
    log(f"Screenshots: {len(screenshot_files)}")
    log(f"Output: {version_dir}")
    if single_only:
        log("--single-only is now a no-op because the pipeline only has one active mode.")
    print()

    # Config for design system extraction
    config = load_config(config_path)
    if surface_map_mode:
        config.surface_map_mode = surface_map_mode
    if site_assets_enabled is not None:
        config.site_asset_generation_enabled = site_assets_enabled
    if config.surface_map_mode not in {"auto", "model", "contract", "skip"}:
        raise ValueError(f"Unsupported surface-map-mode: {config.surface_map_mode}")
    config.verbose = False
    config.max_tokens = 16384
    reviews_enabled = config.run_reviews if run_reviews is None else bool(run_reviews)
    skip_design_system_review = skip_design_system_review or not reviews_enabled
    if vanilla_sites:
        config.vanilla_site_generation_enabled = True
    vanilla_site_generation_enabled = bool(getattr(config, "vanilla_site_generation_enabled", False))
    framework_generation_enabled = bool(
        getattr(config, "framework_generation_enabled", True) or framework_sites
    )
    skip_vanilla_html = bool(framework_sites and sites_only) or (
        framework_generation_enabled and not vanilla_site_generation_enabled
    )

    if assets_only:
        log(f"Backfilling generated site assets for: {version_dir}")
        totals = backfill_generated_site_assets(version_dir, config)
        log(
            "Asset backfill complete: "
            f"{totals['generated_assets']} generated asset(s), "
            f"{totals['placeholders_before']} placeholder(s), "
            f"{totals['errors']} error(s)."
        )
        generate_viewer(RUNS_DIR, PROJECT_DIR / "viewer.html")
        log("viewer.html regenerated")
        return

    apply_version_model_overrides(config, version_dir)

    # Load custom prompts from version folder if they exist, otherwise use defaults and save
    custom_structural_prompt_path = version_dir / "structural-analysis-prompt.md"
    custom_system_prompt_path = version_dir / "system-prompt.md"
    custom_website_prompt_path = version_dir / "website-gen-prompt.md"
    custom_framework_prompt_path = version_dir / "website-gen-framework-prompt.md"
    color_sync_prompt_path = version_dir / "color-sync-prompt.md"
    grounding_sync_prompt_path = version_dir / "grounding-sync-prompt.md"
    surface_component_map_prompt_path = version_dir / "surface-component-map-prompt.md"
    site_style_sync_prompt_path = version_dir / "site-style-sync-prompt.md"
    design_system_review_prompt_path = version_dir / "design-system-review-prompt.md"
    surface_component_map_review_prompt_path = version_dir / "surface-component-map-review-prompt.md"
    design_system_conversion_review_prompt_path = version_dir / "design-system-conversion-review-prompt.md"
    site_generation_providers_path = version_dir / "site-generation-providers.txt"
    site_generation_skills_path = version_dir / "site-generation-skills.txt"

    def find_previous_prompt(filename: str) -> str | None:
        """Find the prompt file from the most recent previous run."""
        previous_versions = get_previous_version_dirs(version)
        for prev_dir in previous_versions:
            prev_path = prev_dir / filename
            if prev_path.exists():
                return prev_path.read_text().strip()
        return None

    def ensure_prompt_appendix(prompt: str, marker: str, appendix: str) -> str:
        if marker in prompt:
            return prompt
        return prompt.rstrip() + "\n\n" + appendix.strip()

    if custom_structural_prompt_path.exists():
        custom_structural_prompt = custom_structural_prompt_path.read_text().strip()
        log("Using custom structural analysis prompt from version folder")
    else:
        prev = find_previous_prompt("structural-analysis-prompt.md")
        if prev:
            custom_structural_prompt = prev
            log("Copied structural analysis prompt from most recent previous run")
        else:
            custom_structural_prompt = config.structural_analysis_prompt
            log("Using default structural analysis prompt")
        with open(custom_structural_prompt_path, "w") as f:
            f.write(custom_structural_prompt + "\n")

    if custom_system_prompt_path.exists():
        custom_system_prompt = custom_system_prompt_path.read_text().strip()
        log("Using custom system prompt from version folder")
    else:
        prev = find_previous_prompt("system-prompt.md")
        if prev:
            custom_system_prompt = prev
            log("Copied system prompt from most recent previous run")
        else:
            custom_system_prompt = config.system_prompt
            log("Using default system prompt")
        with open(custom_system_prompt_path, "w") as f:
            f.write(custom_system_prompt + "\n")
    custom_system_prompt = ensure_prompt_appendix(
        custom_system_prompt,
        "## Layout Artifact Separation",
        """## Layout Artifact Separation

- Do not put the exact source section list, exact section order, or exact one-off component positions into the design system.
- Store exact source layouts separately in `layouts.yaml`; the design system should keep only reusable layout tendencies, broad scaffolds, surface runs, and special opening/closing surface grammar.
- If a source layout appears once, translate only its reusable mechanic into the design system and leave the source-specific arrangement to `layouts.yaml`.""",
    )
    custom_system_prompt_path.write_text(custom_system_prompt + "\n")

    if custom_website_prompt_path.exists():
        custom_website_prompt = custom_website_prompt_path.read_text().strip()
        log("Using custom website generation prompt from version folder")
    else:
        prev = find_previous_prompt("website-gen-prompt.md")
        if prev:
            custom_website_prompt = prev
            log("Copied website generation prompt from most recent previous run")
        else:
            custom_website_prompt = WEBSITE_GEN_PROMPT
            log("Using default website generation prompt")
        with open(custom_website_prompt_path, "w") as f:
            f.write(custom_website_prompt + "\n")
    custom_website_prompt = ensure_prompt_appendix(
        custom_website_prompt,
        "## Site Generation Layout Freshness",
        """## Site Generation Layout Freshness

- Do not copy the source screenshot's exact section list, exact section order, or exact component positions.
- Use broad layout tendencies and surface grammar from the design system, but make a fresh page composition unless a separate `layouts.yaml` artifact is explicitly provided and requested for source reconstruction.
- Keep grounded shared parent surface runs from turning into new full-width section resets; neutral, tinted, inverse, or contrasting fills should remain child/inset foreground modules only when that is what the design system says.
- Center compact eyebrows/pills inside centered intro or CTA stacks; do not apply a global `align-self:flex-start` to every compact label.
- Use defined circular icon-action variants as actual circles with centered arrows/icons, not loose arrow glyphs.
- Start white-to-tint transition gradients from the prior white/near-white canvas color before easing into the tint.
- Do not use shader, WebGL, Three.js, procedural canvas, or particle systems for bespoke generated imagery. Use explicit `data-stt-asset-brief` placeholders so downstream `gpt-image-2` asset generation can fill visual wells.""",
    )
    custom_website_prompt_path.write_text(custom_website_prompt + "\n")

    if custom_framework_prompt_path.exists():
        custom_framework_prompt = custom_framework_prompt_path.read_text().strip()
        log("Using custom framework generation prompt from version folder")
    else:
        prev = find_previous_prompt("website-gen-framework-prompt.md")
        if prev:
            custom_framework_prompt = prev
            log("Copied framework generation prompt from most recent previous run")
        elif DEFAULT_FRAMEWORK_PROMPT_PATH.exists():
            custom_framework_prompt = load_framework_prompt()
            log("Using default framework generation prompt")
        else:
            raise FileNotFoundError(f"Framework prompt missing: {DEFAULT_FRAMEWORK_PROMPT_PATH}")
        with open(custom_framework_prompt_path, "w") as f:
            f.write(custom_framework_prompt + "\n")

    if color_sync_prompt_path.exists():
        color_sync_prompt = color_sync_prompt_path.read_text().strip()
        log("Using custom color sync prompt from version folder")
    else:
        prev = find_previous_prompt("color-sync-prompt.md")
        if prev:
            color_sync_prompt = prev
            log("Copied color sync prompt from most recent previous run")
        else:
            color_sync_prompt = DEFAULT_COLOR_SYNC_PROMPT
            log("Using default color sync prompt")
        with open(color_sync_prompt_path, "w") as f:
            f.write(color_sync_prompt + "\n")

    if grounding_sync_prompt_path.exists():
        grounding_sync_prompt = grounding_sync_prompt_path.read_text().strip()
        log("Using custom grounding sync prompt from version folder")
    else:
        prev = find_previous_prompt("grounding-sync-prompt.md")
        if prev:
            grounding_sync_prompt = prev
            log("Copied grounding sync prompt from most recent previous run")
        else:
            grounding_sync_prompt = DEFAULT_GROUNDING_SYNC_PROMPT
            log("Using default grounding sync prompt")
        with open(grounding_sync_prompt_path, "w") as f:
            f.write(grounding_sync_prompt + "\n")

    if surface_component_map_prompt_path.exists():
        surface_component_map_prompt = surface_component_map_prompt_path.read_text().strip()
        log("Using custom surface component map prompt from version folder")
    else:
        prev = find_previous_prompt("surface-component-map-prompt.md")
        if prev:
            surface_component_map_prompt = prev
            log("Copied surface component map prompt from most recent previous run")
        else:
            surface_component_map_prompt = DEFAULT_SURFACE_COMPONENT_MAP_PROMPT
            log("Using default surface component map prompt")
        with open(surface_component_map_prompt_path, "w") as f:
            f.write(surface_component_map_prompt + "\n")

    if site_style_sync_prompt_path.exists():
        site_style_sync_prompt = site_style_sync_prompt_path.read_text().strip()
        log("Using custom site style sync prompt from version folder")
    else:
        prev = find_previous_prompt("site-style-sync-prompt.md")
        if prev:
            site_style_sync_prompt = prev
            log("Copied site style sync prompt from most recent previous run")
        else:
            site_style_sync_prompt = DEFAULT_SITE_STYLE_SYNC_PROMPT
            log("Using default site style sync prompt")
        with open(site_style_sync_prompt_path, "w") as f:
            f.write(site_style_sync_prompt + "\n")

    if design_system_review_prompt_path.exists():
        design_system_review_prompt = design_system_review_prompt_path.read_text().strip()
        log("Using custom design-system review prompt from version folder")
    else:
        prev = find_previous_prompt("design-system-review-prompt.md")
        if prev:
            design_system_review_prompt = prev
            log("Copied design-system review prompt from most recent previous run")
        else:
            design_system_review_prompt = DEFAULT_DESIGN_SYSTEM_REVIEW_PROMPT
            log("Using default design-system review prompt")
        with open(design_system_review_prompt_path, "w") as f:
            f.write(design_system_review_prompt + "\n")

    if surface_component_map_review_prompt_path.exists():
        surface_component_map_review_prompt = surface_component_map_review_prompt_path.read_text().strip()
        log("Using custom surface-component-map review prompt from version folder")
    else:
        prev = find_previous_prompt("surface-component-map-review-prompt.md")
        if prev:
            surface_component_map_review_prompt = prev
            log("Copied surface-component-map review prompt from most recent previous run")
        else:
            surface_component_map_review_prompt = DEFAULT_SURFACE_COMPONENT_MAP_REVIEW_PROMPT
            log("Using default surface-component-map review prompt")
        with open(surface_component_map_review_prompt_path, "w") as f:
            f.write(surface_component_map_review_prompt + "\n")

    if design_system_conversion_review_prompt_path.exists():
        design_system_conversion_review_prompt = design_system_conversion_review_prompt_path.read_text().strip()
        log("Using custom design-system conversion review prompt from version folder")
    else:
        prev = find_previous_prompt("design-system-conversion-review-prompt.md")
        if prev:
            design_system_conversion_review_prompt = prev
            log("Copied design-system conversion review prompt from most recent previous run")
        else:
            design_system_conversion_review_prompt = DEFAULT_DESIGN_SYSTEM_CONVERSION_REVIEW_PROMPT
            log("Using default design-system conversion review prompt")
        with open(design_system_conversion_review_prompt_path, "w") as f:
            f.write(design_system_conversion_review_prompt + "\n")

    if site_generation_providers_path.exists():
        site_generation_providers = parse_provider_list(site_generation_providers_path.read_text())
        log("Using custom site generation providers from version folder")
    else:
        site_generation_providers = list(DEFAULT_SITE_GENERATION_PROVIDERS)
        log("Using default site generation providers")
    with open(site_generation_providers_path, "w") as f:
        f.write("\n".join(site_generation_providers) + "\n")

    if site_generation_skills_path.exists():
        site_generation_skill_names = parse_skill_list(site_generation_skills_path.read_text())
        log("Using custom site generation skills from version folder")
    else:
        prev = find_previous_prompt("site-generation-skills.txt")
        if prev is not None:
            site_generation_skill_names = parse_skill_list(prev)
            log("Copied site generation skills from most recent previous run")
        else:
            site_generation_skill_names = list(DEFAULT_SITE_GENERATION_SKILLS)
            log("Using default site generation skills")
        with open(site_generation_skills_path, "w") as f:
            f.write("\n".join(site_generation_skill_names) + "\n")

    config.structural_analysis_prompt = custom_structural_prompt
    config.system_prompt = custom_system_prompt
    section_grounding_bundle = load_section_grounding_bundle(version_dir)
    if section_grounding_bundle and not reviews_enabled:
        section_grounding_bundle = dict(section_grounding_bundle)
        section_grounding_bundle["full_page_review_prompt"] = None
    site_generation_source = load_site_generation_source(version_dir)
    site_generation_skills = load_site_generation_skills(site_generation_skill_names)

    ensure_version_learnings(version, version_dir)

    log("Prompts ready")
    log(
        "Analysis model: "
        f"{config.provider}/{config.model}"
        + (f" (reasoning={config.reasoning_effort})" if config.reasoning_effort else "")
    )
    log(
        "Section detection model: "
        f"{config.section_detection_provider}/{config.section_detection_model}"
        + (
            f" (reasoning={config.section_detection_reasoning_effort})"
            if config.section_detection_reasoning_effort
            else ""
        )
    )
    if section_grounding_bundle:
        log("Single-shot will use section-by-section grounding before design-system synthesis")
    if design_only:
        log("Design-only mode: will generate design-system files, then skip site HTML generation")
    if surface_map_only:
        log("Surface-map-only mode: will generate surface-component maps, then stop")
    if reviews_enabled:
        log("Review model calls are enabled")
    else:
        log("Review model calls are disabled")
    if skip_design_system_review and reviews_enabled:
        log("Screenshot-based design-system review will be skipped")
    if design_system_strategy and design_system_strategy != "one-shot":
        log(f"Design-system conversion strategy: {design_system_strategy}")
    if reuse_analysis_from:
        log(f"Reusing grounding artifacts from: {reuse_analysis_from}")
    if review_guidance_from:
        log(f"Using prior review guidance from: {review_guidance_from}")
    if design_system_seed_from:
        log(f"Using prior design-system seed from: {design_system_seed_from}")
    if design_system_best_seed_from:
        log(f"Using best prior design-system seed from: {design_system_best_seed_from}")
    if conversion_review_guidance_from:
        log(f"Using prior design-system conversion review guidance from: {conversion_review_guidance_from}")
    if conversion_review_best_guidance_from:
        log(f"Using best prior design-system conversion review guidance from: {conversion_review_best_guidance_from}")
    if surface_map_review_guidance_from:
        log(f"Using prior surface-map review guidance from: {surface_map_review_guidance_from}")
    if surface_map_seed_from:
        log(f"Using prior surface-map seed from: {surface_map_seed_from}")
    if surface_map_best_seed_from:
        log(f"Using best prior surface-map seed from: {surface_map_best_seed_from}")
    if surface_map_use_best_existing_from:
        log(f"Using best existing prior surface-map output from: {surface_map_use_best_existing_from}")
    log(f"Surface-map mode: {config.surface_map_mode}")
    if reuse_section_groundings_from:
        log(f"Reusing cached section YAML groundings from: {reuse_section_groundings_from}")
    log(f"Generated sites will use: {'structural-analysis.md' if site_generation_source == 'grounding' else 'design-system artifact'}")
    log(f"Enabled site generators: {', '.join(site_generation_providers)}")
    if framework_generation_enabled:
        if skip_vanilla_html:
            log("Framework-first: React + Tailwind v4 + shadcn-style (vanilla one-shot HTML skipped)")
        else:
            log("Framework + vanilla HTML generation both enabled")
    elif not skip_vanilla_html:
        log("Vanilla one-shot HTML only (framework generation disabled)")
    log(f"Active site generation skills: {', '.join(site_generation_skill_names) if site_generation_skill_names else 'none'}")

    manifest = {
        "version": version,
        "timestamp": datetime.now().isoformat(),
        "site_generation_skills": [
            {
                "name": skill["name"],
                "path": str(skill["path"].relative_to(PROJECT_DIR)),
                "content": skill["content"],
            }
            for skill in site_generation_skills
        ],
        "screenshots": [],
    }

    def apply_brand_assets(html_path: Path, label: str) -> dict | None:
        """Fill asset-brief slots with the brand's own (harvested) assets, by role.

        Runs whenever a brand-asset manifest is configured, regardless of the AI
        image-generation toggle, so every generated page pulls real brand assets.
        """
        manifest_rel = (getattr(config, "brand_assets_manifest", "") or "").strip()
        if not manifest_rel:
            return None
        manifest_path = Path(manifest_rel)
        if not manifest_path.is_absolute():
            manifest_path = PROJECT_DIR / manifest_rel
        if not manifest_path.exists():
            log(f"  {label} — brand-asset manifest not found: {manifest_path}")
            return None
        try:
            result = apply_brand_assets_file(html_path, manifest_path)
            if result.get("filled"):
                log(f"  {label} — injected {result['filled']} brand asset(s) by role")
            else:
                log(f"  {label} — no brand assets injected ({result.get('status')})")
            return result
        except Exception as exc:
            log(f"  {label} — brand asset injection ERROR: {exc}")
            return None

    def apply_site_assets(html_path: Path, generation_input: str, label: str, step_name: str) -> dict | None:
        """Generate custom visual assets for a saved HTML page using the configured image model."""
        if not config.site_asset_generation_enabled:
            placeholder_count = count_unfilled_asset_briefs(html_path)
            payload: dict | None = None
            if placeholder_count:
                payload = write_disabled_site_asset_manifest(html_path, placeholder_count)
                log(f"  {label} — asset generation disabled; {placeholder_count} placeholder asset(s) remain")
            brand = apply_brand_assets(html_path, label)
            if brand:
                payload = {**(payload or {}), "brand_assets": brand}
            return payload
        try:
            with token_usage_context(html_path.parent, step_name, {"html": html_path.name}):
                payload = apply_generated_site_assets(
                    html_path=html_path,
                    design_system_markdown=generation_input,
                    config=config,
                    source_crops_dir=html_path.parent / "crops",
                )
            generated_count = payload.get("generated_count", 0)
            status = payload.get("status", "unknown")
            if status == "completed":
                log(f"  {label} — generated {generated_count} custom assets")
            elif status == "no_candidates":
                log(f"  {label} — no image candidates found")
            else:
                reason = payload.get("error") or status
                log(f"  {label} — asset generation skipped: {reason}")
            brand = apply_brand_assets(html_path, label)
            if brand:
                payload = {**(payload or {}), "brand_assets": brand}
            return payload
        except Exception as exc:
            log(f"  {label} — asset generation ERROR: {exc}")
            return None

    def gen_site(
        generation_input: str,
        provider_name: str,
        output_path: Path,
        label: str,
        extracted_source_styles: dict | None = None,
        source_style_ledger: dict | None = None,
        generation_label: str = "design system",
    ):
        """Generate a website HTML file from the configured markdown input."""
        last_error = None
        pre_sync_path = output_path.with_name(output_path.stem + ".pre-style-sync.html")
        for attempt in range(1, 3):
            try:
                with token_usage_context(output_path.parent, f"site_generation_{provider_name}", {"attempt": attempt}):
                    html = generate_website_html(
                        generation_input,
                        provider_name,
                        website_prompt=custom_website_prompt,
                        generation_label=generation_label,
                    )
                if not html_document_is_complete(html):
                    raise ValueError("Generated HTML was incomplete or truncated")
                if extracted_source_styles:
                    pre_sync_path.write_text(html)
                    html = enforce_source_site_styles(
                        html,
                        generation_markdown=generation_input,
                        extracted_source_styles=extracted_source_styles,
                        config=config,
                        site_style_sync_prompt=site_style_sync_prompt,
                        source_style_ledger=source_style_ledger,
                        audit_before_path=output_path.with_name(output_path.stem + "-style-audit.before.json"),
                        audit_after_path=output_path.with_name(output_path.stem + "-style-audit.after.json"),
                    )
                    if not html_document_is_complete(html):
                        raise ValueError("Synced HTML was incomplete or truncated")
                output_path.write_text(html)
                viewport_unit_report = repair_html_file_viewport_layout_units(output_path)
                if viewport_unit_report["replacement_count"]:
                    log(
                        f"  {label} — repaired "
                        f"{viewport_unit_report['replacement_count']} viewport layout unit(s)"
                    )
                apply_site_assets(
                    output_path,
                    generation_input,
                    f"{label} assets",
                    f"site_asset_generation_{provider_name}",
                )
                log(f"  {label} — done")
                return
            except Exception as e:
                last_error = e
                if attempt < 2:
                    log(f"  {label} — retrying after error: {e}")
                else:
                    log(f"  {label} — ERROR: {e}")
        if pre_sync_path.exists() and extracted_source_styles:
            try:
                html = pre_sync_path.read_text()
                if html_document_is_complete(html):
                    html = enforce_source_site_styles(
                        html,
                        generation_markdown=generation_input,
                        extracted_source_styles=extracted_source_styles,
                        config=config,
                        site_style_sync_prompt=site_style_sync_prompt,
                        source_style_ledger=source_style_ledger,
                        audit_before_path=output_path.with_name(output_path.stem + "-style-audit.before.json"),
                        audit_after_path=output_path.with_name(output_path.stem + "-style-audit.after.json"),
                    )
                    output_path.write_text(html)
                    viewport_unit_report = repair_html_file_viewport_layout_units(output_path)
                    if viewport_unit_report["replacement_count"]:
                        log(
                            f"  {label} — repaired "
                            f"{viewport_unit_report['replacement_count']} viewport layout unit(s)"
                        )
                    apply_site_assets(
                        output_path,
                        generation_input,
                        f"{label} assets",
                        f"site_asset_generation_{provider_name}",
                    )
                    log(f"  {label} — recovered from pre-style-sync HTML after error: {last_error}")
                    return
            except Exception as recovery_error:
                log(f"  {label} — pre-style-sync recovery failed: {recovery_error}")
        with open(output_path, "w") as f:
            f.write(f"<html><body><h1>Error</h1><p>{last_error}</p></body></html>")

    def resolve_brand_assets_manifest_path() -> Path | None:
        manifest_rel = (getattr(config, "brand_assets_manifest", "") or "").strip()
        if not manifest_rel:
            return None
        manifest_path = Path(manifest_rel)
        if not manifest_path.is_absolute():
            manifest_path = PROJECT_DIR / manifest_rel
        return manifest_path if manifest_path.exists() else None

    def resolve_source_chrome_path() -> Path | None:
        chrome_rel = (getattr(config, "source_chrome_contract", "") or "").strip()
        if chrome_rel:
            chrome_path = Path(chrome_rel)
            if not chrome_path.is_absolute():
                chrome_path = PROJECT_DIR / chrome_rel
            return chrome_path if chrome_path.exists() else None
        # Prefer the richer browser-extracted v2 contract over the static v1.
        assets = version_dir / "assets"
        for name in ("source-chrome.v2.json", "source-chrome.json"):
            candidate = assets / name
            if candidate.exists():
                return candidate
        return None

    def gen_framework_site(
        generation_input: str,
        provider_name: str,
        output_path: Path,
        label: str,
        generation_label: str = "design system",
    ):
        """Generate a framework-based site (React package → single-file HTML)."""
        last_error = None
        brand_manifest = resolve_brand_assets_manifest_path()
        chrome_path = resolve_source_chrome_path()
        if chrome_path:
            log(f"  {label} — using source chrome contract: {chrome_path.relative_to(PROJECT_DIR)}")
        for attempt in range(1, 3):
            try:
                with token_usage_context(
                    output_path.parent,
                    f"framework_site_generation_{provider_name}",
                    {"attempt": attempt},
                ):
                    generate_framework_site(
                        generation_markdown=generation_input,
                        provider_name=provider_name,
                        single_dir=output_path.parent,
                        output_html_path=output_path,
                        framework_prompt=custom_framework_prompt,
                        brand_assets_manifest=brand_manifest,
                        chrome_contract_path=chrome_path,
                        generation_label=generation_label,
                        log=log,
                    )
                apply_site_assets(
                    output_path,
                    generation_input,
                    f"{label} assets",
                    f"framework_site_asset_generation_{provider_name}",
                )
                brand = apply_brand_assets(output_path, label)
                if brand:
                    log(f"  {label} — brand assets applied to framework build")
                log(f"  {label} — framework build done")
                return
            except Exception as e:
                last_error = e
                if attempt < 2:
                    log(f"  {label} — framework retry after error: {e}")
                else:
                    log(f"  {label} — framework ERROR: {e}")
        with open(output_path, "w") as f:
            f.write(f"<html><body><h1>Framework Error</h1><p>{last_error}</p></body></html>")

    def write_site_skipped_output(output_path: Path, provider_label: str):
        """Write a placeholder when a generator is disabled for this run."""
        with open(output_path, "w") as f:
            f.write(
                "<html><body><p>"
                f"{provider_label} site generation was skipped for this run."
                "</p></body></html>"
            )

    def write_review_skipped_output(review_json_path: Path, review_md_path: Path, reason: str):
        """Write placeholder review artifacts when design-system review is unavailable."""
        payload = {
            "summary": reason,
            "weighted_score": 0,
            "scores": {},
            "section_reviews": [],
            "strengths": [],
            "major_mismatches": [],
            "actionable_learnings": [],
            "verdict": reason,
            "raw_response": reason,
        }
        review_json_path.write_text(json.dumps(payload, indent=2) + "\n")
        review_md_path.write_text(design_system_review_payload_to_markdown(payload))

    def write_surface_map_review_skipped_output(review_json_path: Path, review_md_path: Path, reason: str):
        payload = {
            "summary": reason,
            "weighted_score": 0,
            "scores": {},
            "strengths": [],
            "major_mismatches": [],
            "actionable_learnings": [],
            "verdict": reason,
            "raw_response": reason,
        }
        review_json_path.write_text(json.dumps(payload, indent=2) + "\n")
        review_md_path.write_text(surface_component_map_review_to_markdown(payload))

    def write_conversion_review_skipped_output(review_json_path: Path, review_md_path: Path, reason: str):
        payload = {
            "summary": reason,
            "weighted_score": 0,
            "scores": {},
            "preserved_pairings": [],
            "conversion_losses": [],
            "distortions_or_overgeneralizations": [],
            "actionable_learnings": [],
            "verdict": reason,
            "raw_response": reason,
        }
        review_json_path.write_text(json.dumps(payload, indent=2) + "\n")
        review_md_path.write_text(design_system_conversion_review_to_markdown(payload))

    def copy_reusable_analysis_artifacts(name: str, mode_dir: Path) -> bool:
        """Copy prior grounding artifacts into this run so design-only iterations can skip recropping/regrounding."""
        if not reuse_analysis_from:
            return False
        prior_mode_dir = RUNS_DIR / reuse_analysis_from / name / "single"
        if not prior_mode_dir.exists():
            log(f"  {name}/single — no reusable artifacts found in {prior_mode_dir}")
            return False

        copied = False
        for filename in (
            "structural-analysis.md",
            "structural-analysis.pre-source-sync.md",
            "section-inventory.md",
            "sections.json",
            "section-detection-raw.txt",
            "full-page-review.json",
            "section-map.html",
        ):
            src = prior_mode_dir / filename
            if src.exists():
                dest = mode_dir / filename
                if src.resolve() != dest.resolve():
                    shutil.copy2(src, dest)
                copied = True

        for dirname in ("section-groundings", "section-transitions", "crops"):
            src = prior_mode_dir / dirname
            dest = mode_dir / dirname
            if src.exists():
                if src.resolve() == dest.resolve():
                    copied = True
                    continue
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(src, dest)
                copied = True

        return copied

    def copy_reusable_section_grounding_artifacts(name: str, mode_dir: Path) -> bool:
        """Copy only cached section-level artifacts so global/merge/design steps can rerun."""
        if not reuse_section_groundings_from:
            return False
        prior_mode_dir = RUNS_DIR / reuse_section_groundings_from / name / "single"
        if not prior_mode_dir.exists():
            log(f"  {name}/single — no section-grounding cache found in {prior_mode_dir}")
            return False

        copied = False
        for dirname in ("section-groundings", "section-transitions"):
            src = prior_mode_dir / dirname
            dest = mode_dir / dirname
            if src.exists():
                if src.resolve() == dest.resolve():
                    copied = True
                    continue
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(src, dest)
                copied = True
        return copied

    def load_prior_review_guidance(name: str) -> str:
        if not review_guidance_from:
            return ""
        prior_review_path = RUNS_DIR / review_guidance_from / name / "single" / "design-system-review.md"
        if not prior_review_path.exists():
            return ""
        text = prior_review_path.read_text().strip()
        if not text:
            return ""
        return text[:24000]

    def load_prior_conversion_review_guidance(name: str) -> str:
        if conversion_review_best_guidance_from:
            best = find_best_prior_design_system(name, conversion_review_best_guidance_from)
            if best:
                text = best[2].read_text().strip()
                return text[:24000]
        if not conversion_review_guidance_from:
            return ""
        prior_review_path = RUNS_DIR / conversion_review_guidance_from / name / "single" / "design-system-conversion-review.md"
        if not prior_review_path.exists():
            return ""
        text = prior_review_path.read_text().strip()
        if not text:
            return ""
        return text[:24000]

    def load_prior_design_system_seed(name: str) -> str:
        if design_system_best_seed_from:
            best = find_best_prior_design_system(name, design_system_best_seed_from)
            if best:
                return best[1].read_text().strip()
        if not design_system_seed_from:
            return ""
        prior_design_dir = RUNS_DIR / design_system_seed_from / name / "single"
        prior_design_path = design_system_artifact_path(prior_design_dir)
        if not prior_design_path.exists():
            return ""
        return prior_design_path.read_text().strip()

    def load_prior_surface_map_review_guidance(name: str) -> str:
        if surface_map_best_seed_from:
            best = find_best_prior_surface_map(name, surface_map_best_seed_from)
            if best:
                review_text = best[2].read_text().strip()
                return review_text[:24000]
        if not surface_map_review_guidance_from:
            return ""
        prior_review_path = RUNS_DIR / surface_map_review_guidance_from / name / "single" / "surface-component-map-review.md"
        if not prior_review_path.exists():
            return ""
        text = prior_review_path.read_text().strip()
        if not text:
            return ""
        return text[:24000]

    def load_prior_surface_map_seed(name: str) -> str:
        if surface_map_best_seed_from:
            best = find_best_prior_surface_map(name, surface_map_best_seed_from)
            if best:
                return best[1].read_text().strip()
        if not surface_map_seed_from:
            return ""
        prior_map_path = RUNS_DIR / surface_map_seed_from / name / "single" / "surface-component-map.md"
        if not prior_map_path.exists():
            return ""
        return prior_map_path.read_text().strip()

    def expand_version_spec(spec: str) -> list[str]:
        versions: list[str] = []
        for part in spec.split(","):
            part = part.strip()
            if not part:
                continue
            if ":" in part:
                start, end = [item.strip() for item in part.split(":", 1)]
                try:
                    start_num = int(start.lstrip("v"))
                    end_num = int(end.lstrip("v"))
                except ValueError:
                    versions.extend([start, end])
                    continue
                step = 1 if end_num >= start_num else -1
                versions.extend(f"v{num:03d}" for num in range(start_num, end_num + step, step))
            else:
                versions.append(part)
        return list(dict.fromkeys(versions))

    def find_best_prior_surface_map(name: str, version_spec: str) -> tuple[str, Path, Path] | None:
        best: tuple[float, str, Path, Path] | None = None
        for prior_version in expand_version_spec(version_spec):
            prior_dir = RUNS_DIR / prior_version / name / "single"
            map_path = prior_dir / "surface-component-map.md"
            review_md_path = prior_dir / "surface-component-map-review.md"
            review_json_path = prior_dir / "surface-component-map-review.json"
            if not map_path.exists() or not review_md_path.exists() or not review_json_path.exists():
                continue
            try:
                score = float(json.loads(review_json_path.read_text()).get("weighted_score", 0) or 0)
            except (json.JSONDecodeError, ValueError, TypeError):
                continue
            if best is None or score > best[0]:
                best = (score, prior_version, map_path, review_md_path)
        if not best:
            return None
        return best[1], best[2], best[3]

    def find_existing_prior_surface_map(name: str, version_spec: str) -> tuple[str, Path, Path] | None:
        best = find_best_prior_surface_map(name, version_spec)
        if best:
            return best
        for prior_version in expand_version_spec(version_spec):
            map_path = RUNS_DIR / prior_version / name / "single" / "surface-component-map.md"
            if map_path.exists() and map_path.read_text().strip():
                return prior_version, map_path, map_path
        return None

    def find_best_prior_design_system(name: str, version_spec: str) -> tuple[str, Path, Path] | None:
        best: tuple[float, str, Path, Path] | None = None
        for prior_version in expand_version_spec(version_spec):
            prior_dir = RUNS_DIR / prior_version / name / "single"
            design_path = design_system_artifact_path(prior_dir)
            review_md_path = prior_dir / "design-system-conversion-review.md"
            review_json_path = prior_dir / "design-system-conversion-review.json"
            if not design_path.exists() or not review_md_path.exists() or not review_json_path.exists():
                continue
            try:
                payload = json.loads(review_json_path.read_text())
                score = float(payload.get("weighted_score", 0) or 0)
                raw_response = str(payload.get("raw_response", "")).strip()
            except (json.JSONDecodeError, ValueError, TypeError):
                continue
            if not raw_response or raw_response.lower().startswith("review failed"):
                continue
            if design_path.read_text().lstrip().startswith("# Error"):
                continue
            if best is None or score > best[0]:
                best = (score, prior_version, design_path, review_md_path)
        if not best:
            return None
        return best[1], best[2], best[3]

    def process_single_mode(name: str, screenshot_path: Path, mode_dir: Path):
        """Run the active single pipeline for one screenshot, then generate sites in parallel."""
        mode_dir.mkdir(exist_ok=True)
        tag = f"{name}/single"
        step_status = lambda step, status, meta=None: update_step_status(mode_dir, step, status, meta)

        try:
            output_dir = str(mode_dir)
            structural_path = mode_dir / "structural-analysis.md"
            design_artifact_path = design_system_artifact_path(mode_dir)
            surface_component_map = ""
            surface_component_reference = ""
            reused_analysis = copy_reusable_analysis_artifacts(name, mode_dir)
            reused_section_groundings = False if reused_analysis else copy_reusable_section_grounding_artifacts(name, mode_dir)
            if reused_analysis:
                step_status("reused_analysis_artifacts", "completed", {"from": reuse_analysis_from})
                log(f"  {tag} — reused grounding artifacts from {reuse_analysis_from}")
            elif reused_section_groundings:
                step_status("reused_section_groundings", "completed", {"from": reuse_section_groundings_from})
                log(f"  {tag} — reused section YAML groundings from {reuse_section_groundings_from}")
            source_style_report = None
            extracted_source_styles = None
            source_style_ledger_data = None
            source_style_ledger_block = None
            source_html_path = find_source_html_for_screenshot(screenshot_path)
            if source_html_path and source_html_path.exists():
                step_status("source_style_extraction", "in_progress")
                log(f"  {tag} — extracting source CSS styles...")
                extracted_source_styles = extract_source_colors(
                    source_html_path,
                    font_assets_dir=mode_dir / "source-fonts",
                )
                write_source_color_artifacts(mode_dir, extracted_source_styles)
                source_style_ledger_data = build_source_style_ledger(extracted_source_styles)
                write_source_style_ledger_artifact(mode_dir, source_style_ledger_data)
                source_style_ledger_block = source_style_ledger_prompt_block(source_style_ledger_data)
                source_style_report = render_source_color_report(extracted_source_styles)
                step_status("source_style_extraction", "completed")
            else:
                step_status("source_style_extraction", "skipped", {"reason": "no source html found"})

            if section_grounding_bundle:
                if reused_analysis and structural_path.exists():
                    structural_analysis = structural_path.read_text().strip()
                    step_status("section_grounding_pipeline", "skipped", {"reason": f"reused from {reuse_analysis_from}"})
                else:
                    step_status("section_grounding_pipeline", "in_progress")
                    log(f"  {tag} — grounding sections one at a time...")
                    with token_usage_context(mode_dir, "section_grounding_pipeline"):
                        structural_analysis = run_grounding_by_section(
                            image_path=str(screenshot_path),
                            config=config,
                            inventory_prompt=section_grounding_bundle["inventory_prompt"],
                            section_prompt=section_grounding_bundle["section_prompt"],
                            merge_prompt=section_grounding_bundle["merge_prompt"],
                            include_full_page_context=section_grounding_bundle["include_full_page_context"],
                            transition_prompt=section_grounding_bundle["transition_prompt"],
                            full_page_review_prompt=section_grounding_bundle["full_page_review_prompt"],
                            global_site_prompt=section_grounding_bundle["global_site_prompt"],
                            section_agent_prompts=section_grounding_bundle["section_agent_prompts"],
                            section_agent_merge_prompt=section_grounding_bundle["section_agent_merge_prompt"],
                            output_dir=output_dir,
                        )
                    step_status("section_grounding_pipeline", "completed")
                section_grounding_markdown = collect_section_grounding_markdown(output_dir)
                if source_style_report and extracted_source_styles:
                    with open(mode_dir / "structural-analysis.pre-source-sync.md", "w") as f:
                        f.write(structural_analysis.strip() + "\n")
                    step_status("grounding_style_sync", "in_progress")
                    log(f"  {tag} — syncing grounding colors and typography from source HTML...")
                    try:
                        with token_usage_context(mode_dir, "grounding_style_sync"):
                            structural_analysis = enforce_source_grounding_styles(
                                structural_analysis,
                                extracted_source_styles=extracted_source_styles,
                                config=config,
                                grounding_sync_prompt=grounding_sync_prompt,
                            )
                        if structural_analysis.strip():
                            with open(mode_dir / "structural-analysis.md", "w") as f:
                                f.write(structural_analysis.strip() + "\n")
                        step_status("grounding_style_sync", "completed")
                    except Exception as grounding_sync_error:
                        step_status("grounding_style_sync", "failed", {"error": str(grounding_sync_error)})
                        log(f"  {tag} — grounding sync skipped after error: {grounding_sync_error}")
                layouts_path = write_layouts_artifact(mode_dir, structural_analysis)
                if layouts_path:
                    step_status("layouts_artifact", "completed", {"path": layouts_path.name})
                if site_generation_source == "grounding":
                    ds_clean = ""
                    log(f"  {tag} — grounding done")
                else:
                    surface_component_map_path = mode_dir / "surface-component-map.md"
                    surface_component_contract_prompt = ""
                    surface_component_reference = ""
                    step_status("surface_component_map", "in_progress")
                    log(f"  {tag} — compiling deterministic surface/component contract...")
                    deterministic_surface_component_map = build_surface_component_map_from_grounding(
                        structural_analysis=structural_analysis,
                        section_grounding_markdown=section_grounding_markdown,
                        source_color_report=source_style_report,
                    )
                    (mode_dir / "surface-component-map-deterministic-draft.md").write_text(
                        deterministic_surface_component_map.strip() + "\n"
                    )
                    surface_component_contract = build_surface_component_contract(
                        section_grounding_markdown=section_grounding_markdown,
                        source_style_ledger=source_style_ledger_data,
                    )
                    write_surface_component_contract_artifacts(mode_dir, surface_component_contract)
                    surface_component_contract_prompt = render_surface_component_contract_for_prompt(surface_component_contract)
                    contract_passed = contract_audit_passed(surface_component_contract)
                    (mode_dir / "surface-component-contract.prompt.yaml").write_text(
                        surface_component_contract_prompt.strip() + "\n"
                    )
                    step_status(
                        "surface_component_contract",
                        "completed",
                        {
                            "passed": contract_passed,
                            "mode": config.surface_map_mode,
                        },
                    )

                    use_model_surface_map = config.surface_map_mode == "model" or (
                        config.surface_map_mode == "auto" and not contract_passed
                    )
                    use_contract_surface_map = config.surface_map_mode == "contract" or (
                        config.surface_map_mode == "auto" and contract_passed
                    )
                    if config.surface_map_mode == "skip":
                        log(f"  {tag} — skipping surface/component map reference by config")
                        step_status("surface_component_map", "skipped", {"reason": "surface-map-mode=skip"})
                        surface_component_map = ""
                        surface_component_reference = ""
                    elif use_contract_surface_map:
                        log(f"  {tag} — using deterministic surface/component contract for design-system synthesis")
                        surface_component_map = ""
                        surface_component_reference = surface_component_contract_prompt
                        step_status("surface_component_map", "completed", {"source": "contract", "contract_passed": contract_passed})
                    else:
                        if config.surface_map_mode == "auto":
                            log(f"  {tag} — contract audit did not pass; falling back to model surface/component map")
                        else:
                            log(f"  {tag} — compiling model surface/component map...")
                        best_existing = (
                            find_existing_prior_surface_map(name, surface_map_use_best_existing_from)
                            if surface_map_use_best_existing_from
                            else None
                        )
                        if best_existing:
                            log(f"  {tag} — using existing surface/component map from {best_existing[0]}")
                            surface_component_map = sanitize_surface_component_map(best_existing[1].read_text())
                        else:
                            try:
                                surface_component_map = synthesize_surface_component_map(
                                    structural_analysis=structural_analysis,
                                    config=config,
                                    surface_component_map_prompt=surface_component_map_prompt,
                                    source_color_report=source_style_report,
                                    source_style_ledger=source_style_ledger_block,
                                    section_grounding_markdown=section_grounding_markdown,
                                    deterministic_surface_map=deterministic_surface_component_map,
                                    prior_surface_map_review_guidance=load_prior_surface_map_review_guidance(name),
                                    prior_surface_map=load_prior_surface_map_seed(name),
                                )
                                if not surface_component_map.lstrip().startswith("# Surface Component Map"):
                                    raise ValueError("compiled surface map did not use expected heading")
                                surface_component_map = sanitize_surface_component_map(surface_component_map)
                            except Exception as surface_map_error:
                                log(f"  {tag} — surface/component map synthesis fell back to deterministic draft: {surface_map_error}")
                                surface_component_map = sanitize_surface_component_map(deterministic_surface_component_map)
                        if not surface_component_map.strip():
                            raise ValueError("Surface component map synthesis returned empty output")
                        surface_component_map_path.write_text(surface_component_map.strip() + "\n")
                        surface_component_reference = surface_component_map
                        step_status("surface_component_map", "completed", {"source": "model" if use_model_surface_map else "fallback"})
                    if surface_map_only:
                        review_json_path = mode_dir / "surface-component-map-review.json"
                        review_md_path = mode_dir / "surface-component-map-review.md"
                        review = None
                        if reviews_enabled and surface_component_reference.strip():
                            step_status("surface_component_map_review", "in_progress")
                            log(f"  {tag} — reviewing surface/component reference...")
                            review = evaluate_surface_component_map_match(
                                reference_screenshot_path=screenshot_path,
                                section_grounding_markdown=section_grounding_markdown,
                                surface_component_map=surface_component_reference,
                                review_json_path=review_json_path,
                                review_md_path=review_md_path,
                                review_prompt=surface_component_map_review_prompt,
                                config=config,
                                max_image_dimension=config.max_image_dimension,
                                output_dir=mode_dir,
                            )
                            step_status("surface_component_map_review", "completed", {"weighted_score": review.get("weighted_score")})
                            log(f"  {tag} — surface-map review score {review['weighted_score']:.2f}/100")
                        else:
                            reason = "reviews disabled" if not reviews_enabled else "no surface reference in skip mode"
                            step_status("surface_component_map_review", "skipped", {"reason": reason})
                            write_surface_map_review_skipped_output(
                                review_json_path,
                                review_md_path,
                                f"Surface-map review skipped: {reason}.",
                            )
                        for fname in (
                            "site-claude.html",
                            "site-gemini.html",
                            "site-gpt55.html",
                        ):
                            write_site_skipped_output(mode_dir / fname, fname.replace("site-", "").replace(".html", ""))
                        (mode_dir / "site-generation-input.md").write_text(
                            "# Surface Map Only\n\nSite generation was skipped for this run.\n"
                        )
                        (mode_dir / "design-system.md").write_text(
                            "# Surface Map Only\n\nDesign-system synthesis was skipped for this run.\n"
                        )
                        write_review_skipped_output(
                            mode_dir / "design-system-review.json",
                            mode_dir / "design-system-review.md",
                            "Design-system review skipped in surface-map-only mode.",
                        )
                        write_conversion_review_skipped_output(
                            mode_dir / "design-system-conversion-review.json",
                            mode_dir / "design-system-conversion-review.md",
                            "Design-system conversion review skipped in surface-map-only mode.",
                        )
                        step_status("run_complete", "completed", {
                            "surface_component_map_review_score": (review or {}).get("weighted_score")
                        })
                        log(f"  {tag} — surface-map-only complete")
                        return
                    log(f"  {tag} — grounding done, synthesizing design system...")
                    with token_usage_context(mode_dir, "design_system_synthesis"):
                        ds = synthesize_design_system_with_strategy(
                            structural_analysis=structural_analysis,
                            config=config,
                            design_system_strategy=design_system_strategy,
                            source_color_report=source_style_report,
                            source_style_ledger=source_style_ledger_block,
                            section_grounding_markdown=section_grounding_markdown,
                            surface_component_map=surface_component_map,
                            surface_component_contract=surface_component_reference if use_contract_surface_map else None,
                            prior_review_guidance=load_prior_review_guidance(name),
                            prior_conversion_review_guidance=load_prior_conversion_review_guidance(name),
                            prior_design_system=load_prior_design_system_seed(name),
                            conversion_review_prompt=design_system_conversion_review_prompt if reviews_enabled else None,
                            output_dir=mode_dir,
                        )
                    ds_clean = clean_markdown(ds)
                    if not ds_clean.strip():
                        raise ValueError("Design system synthesis returned empty output")
                    if source_style_report and extracted_source_styles:
                        with open(mode_dir / "design-system.pre-color-sync.md", "w") as f:
                            f.write(ds_clean + "\n")
                        with open(mode_dir / "design-system.pre-style-sync.md", "w") as f:
                            f.write(ds_clean + "\n")
                        log(f"  {tag} — syncing exact colors from source HTML...")
                        try:
                            synced = enforce_source_color_literals(
                                ds_clean,
                                extracted_source_colors=extracted_source_styles,
                                config=config,
                                color_sync_prompt=color_sync_prompt,
                                source_style_ledger=source_style_ledger_data,
                                audit_path=mode_dir / "design-system-style-audit.json",
                                grounding_markdown=combine_grounding_references(
                                    combine_grounding_references(
                                        structural_analysis,
                                        section_grounding_markdown,
                                    ),
                                    surface_component_reference or surface_component_map,
                                ),
                            )
                            if synced.strip():
                                ds_clean = synced
                        except Exception as color_sync_error:
                            log(f"  {tag} — color sync skipped after error: {color_sync_error}")
                        ds_clean = append_source_font_implementation(ds_clean, extracted_source_styles)

                    ds_clean = strip_source_provenance_from_design_system(ds_clean)
                    design_artifact_path = write_design_system_artifacts(mode_dir, ds_clean)
            else:
                section_grounding_markdown = ""
                if site_generation_source == "grounding":
                    step_status("grounding_single_shot", "in_progress")
                    log(f"  {tag} — extracting grounding...")
                    with token_usage_context(mode_dir, "grounding_single_shot"):
                        structural_analysis = generate_structural_analysis(
                            str(screenshot_path),
                            config,
                            output_dir=output_dir,
                        )
                    step_status("grounding_single_shot", "completed")
                    if source_style_report and extracted_source_styles:
                        with open(mode_dir / "structural-analysis.pre-source-sync.md", "w") as f:
                            f.write(structural_analysis.strip() + "\n")
                        step_status("grounding_style_sync", "in_progress")
                        log(f"  {tag} — syncing grounding colors and typography from source HTML...")
                        try:
                            with token_usage_context(mode_dir, "grounding_style_sync"):
                                structural_analysis = enforce_source_grounding_styles(
                                    structural_analysis,
                                    extracted_source_styles=extracted_source_styles,
                                    config=config,
                                    grounding_sync_prompt=grounding_sync_prompt,
                                )
                            if structural_analysis.strip():
                                with open(structural_path, "w") as f:
                                    f.write(structural_analysis.strip() + "\n")
                            step_status("grounding_style_sync", "completed")
                        except Exception as grounding_sync_error:
                            step_status("grounding_style_sync", "failed", {"error": str(grounding_sync_error)})
                            log(f"  {tag} — grounding sync skipped after error: {grounding_sync_error}")
                    ds_clean = ""
                else:
                    log(f"  {tag} — extracting design system...")
                    structural_analysis = structural_path.read_text().strip() if structural_path.exists() else ""
                    with token_usage_context(mode_dir, "design_system_synthesis"):
                        ds = generate_design_system(
                            str(screenshot_path),
                            config,
                            mode="single",
                            system_prompt=custom_system_prompt,
                            output_dir=output_dir,
                        )
                    ds_clean = clean_markdown(ds)
                    if not ds_clean.strip():
                        raise ValueError("Design system synthesis returned empty output")
                    if source_style_report and extracted_source_styles:
                        with open(mode_dir / "design-system.pre-color-sync.md", "w") as f:
                            f.write(ds_clean + "\n")
                        with open(mode_dir / "design-system.pre-style-sync.md", "w") as f:
                            f.write(ds_clean + "\n")
                        log(f"  {tag} — syncing exact colors from source HTML...")
                        try:
                            synced = enforce_source_color_literals(
                                ds_clean,
                                extracted_source_colors=extracted_source_styles,
                                config=config,
                                color_sync_prompt=color_sync_prompt,
                                source_style_ledger=source_style_ledger_data,
                                audit_path=mode_dir / "design-system-style-audit.json",
                                grounding_markdown=structural_analysis,
                            )
                            if synced.strip():
                                ds_clean = synced
                        except Exception as color_sync_error:
                            log(f"  {tag} — color sync skipped after error: {color_sync_error}")
                        ds_clean = append_source_font_implementation(ds_clean, extracted_source_styles)

                    ds_clean = strip_source_provenance_from_design_system(ds_clean)
                    design_artifact_path = write_design_system_artifacts(mode_dir, ds_clean)
            if site_generation_source == "grounding":
                site_generation_input = structural_path.read_text().strip() if structural_path.exists() else structural_analysis
                site_generation_label = "grounding"
                design_artifact_path = structural_path
                if extracted_source_styles:
                    site_generation_input = append_source_font_implementation(site_generation_input, extracted_source_styles)
            else:
                site_generation_input = ds_clean
                site_generation_label = "design system"
                design_artifact_path = design_artifact_path if "design_artifact_path" in locals() else design_system_artifact_path(mode_dir)
                (mode_dir / "site-generation-input.raw-design-system.md").write_text(
                    build_site_generation_input(
                        site_generation_input,
                        site_generation_label,
                        site_generation_skills,
                    ).strip() + "\n"
                )
                site_generation_input = strip_source_provenance_for_site_generation(site_generation_input)
            site_generation_input = build_site_generation_input(
                site_generation_input,
                site_generation_label,
                site_generation_skills,
            )
            freshness_audit = audit_site_generation_freshness(site_generation_input, mode_dir)
            if site_generation_label == "design system" and freshness_audit["high_risk_match_count"]:
                raise ValueError(
                    "Site generation input still contains source-order/provenance leaks; "
                    f"see {mode_dir / 'site-generation-freshness-audit.json'}"
                )
            site_generation_label = "site generation input"
            site_generation_input_path = mode_dir / "site-generation-input.md"
            with open(site_generation_input_path, "w") as f:
                f.write(site_generation_input.strip() + "\n")
            step_status("site_generation_input", "completed", {"label": site_generation_label})
            log(f"  {tag} — site generation input done, reviewing design system and generating sites...")

            provider_targets = (
                ("claude", "site-claude.html", "Claude"),
                ("gemini", "site-gemini.html", "Gemini"),
                ("gpt55", "site-gpt55.html", "GPT-5.5"),
            )
            framework_provider_targets = (
                ("claude", "site-claude-framework.html", "Claude Framework"),
                ("gpt55", "site-gpt55-framework.html", "GPT-5.5 Framework"),
            )
            enabled_providers = set(site_generation_providers)
            enabled_count = sum(1 for provider_name, _, _ in provider_targets if provider_name in enabled_providers)
            if framework_generation_enabled:
                enabled_count += sum(
                    1 for provider_name, _, _ in framework_provider_targets if provider_name in enabled_providers
                )
            review_json_path = mode_dir / "design-system-review.json"
            review_md_path = mode_dir / "design-system-review.md"
            conversion_review_json_path = mode_dir / "design-system-conversion-review.json"
            conversion_review_md_path = mode_dir / "design-system-conversion-review.md"
            design_review_input = design_artifact_path.read_text().strip() if design_artifact_path.exists() else ""

            def run_design_system_review():
                if skip_design_system_review:
                    step_status("design_system_review", "skipped", {"reason": "disabled for this run"})
                    write_review_skipped_output(
                        review_json_path,
                        review_md_path,
                        "Screenshot-based design-system review skipped for this run.",
                    )
                    return None
                if not design_system_is_usable(design_review_input):
                    step_status("design_system_review", "skipped", {"reason": "no usable design-system markdown"})
                    write_review_skipped_output(
                        review_json_path,
                        review_md_path,
                        "No usable design-system markdown was available for review.",
                    )
                    return None
                step_status("design_system_review", "in_progress")
                log(f"  {tag} — reviewing design-system sections against screenshot...")
                review = evaluate_design_system_match(
                    reference_screenshot_path=screenshot_path,
                    design_system_markdown=design_review_input,
                    review_json_path=review_json_path,
                    review_md_path=review_md_path,
                    review_prompt=design_system_review_prompt,
                    config=config,
                    max_image_dimension=config.max_image_dimension,
                    output_dir=mode_dir,
                )
                log(f"  {tag} — design-system review score {review['weighted_score']:.2f}/100")
                step_status("design_system_review", "completed", {"weighted_score": review.get("weighted_score")})
                return review

            def run_design_system_conversion_review():
                if not reviews_enabled:
                    step_status("design_system_conversion_review", "skipped", {"reason": "reviews disabled"})
                    write_conversion_review_skipped_output(
                        conversion_review_json_path,
                        conversion_review_md_path,
                        "Design-system conversion review skipped because review model calls are disabled.",
                    )
                    return None
                conversion_reference = surface_component_reference or surface_component_map
                if not conversion_reference.strip():
                    step_status("design_system_conversion_review", "skipped", {"reason": "no surface-component map or contract"})
                    write_conversion_review_skipped_output(
                        conversion_review_json_path,
                        conversion_review_md_path,
                        "No surface-component map or contract was available for conversion review.",
                    )
                    return None
                if not design_system_is_usable(design_review_input):
                    step_status("design_system_conversion_review", "skipped", {"reason": "no usable design-system markdown"})
                    write_conversion_review_skipped_output(
                        conversion_review_json_path,
                        conversion_review_md_path,
                        "No usable design-system markdown was available for conversion review.",
                    )
                    return None
                step_status("design_system_conversion_review", "in_progress")
                log(f"  {tag} — reviewing design-system conversion loss...")
                review = evaluate_design_system_conversion_loss(
                    surface_component_map=conversion_reference,
                    design_system_markdown=design_review_input,
                    review_json_path=conversion_review_json_path,
                    review_md_path=conversion_review_md_path,
                    review_prompt=design_system_conversion_review_prompt,
                    config=config,
                    output_dir=mode_dir,
                )
                log(f"  {tag} — conversion review score {review['weighted_score']:.2f}/100")
                step_status("design_system_conversion_review", "completed", {"weighted_score": review.get("weighted_score")})
                return review

            if design_only:
                review = run_design_system_review()
                conversion_review = run_design_system_conversion_review()
                for provider_name, filename, label in provider_targets:
                    write_site_skipped_output(mode_dir / filename, label)
                    step_status(f"site_generation_{provider_name}", "skipped", {"reason": "design-only mode"})
                if framework_generation_enabled:
                    for provider_name, filename, label in framework_provider_targets:
                        write_site_skipped_output(mode_dir / filename, label)
                        step_status(f"framework_site_generation_{provider_name}", "skipped", {"reason": "design-only mode"})
                step_status("run_complete", "completed", {
                    "design_system_review_score": (review or {}).get("weighted_score"),
                    "design_system_conversion_review_score": (conversion_review or {}).get("weighted_score"),
                })
                log(f"  {tag} — design-only complete")
                return

            max_workers = max(1, enabled_count + 2)
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
                futures: list[tuple[str, str, concurrent.futures.Future]] = []
                if not skip_vanilla_html:
                    for provider_name, filename, label in provider_targets:
                        output_path = mode_dir / filename
                        if provider_name in enabled_providers:
                            step_status(f"site_generation_{provider_name}", "in_progress")
                            futures.append((
                                "site",
                                provider_name,
                                pool.submit(
                                    gen_site,
                                    site_generation_input,
                                    provider_name,
                                    output_path,
                                    f"{tag}/{label}",
                                    extracted_source_styles,
                                    source_style_ledger_data,
                                    site_generation_label,
                                ),
                            ))
                        else:
                            write_site_skipped_output(output_path, label)
                if framework_generation_enabled:
                    for provider_name, filename, label in framework_provider_targets:
                        output_path = mode_dir / filename
                        if provider_name in enabled_providers:
                            step_status(f"framework_site_generation_{provider_name}", "in_progress")
                            futures.append((
                                "framework",
                                provider_name,
                                pool.submit(
                                    gen_framework_site,
                                    site_generation_input,
                                    provider_name,
                                    output_path,
                                    f"{tag}/{label}",
                                    site_generation_label,
                                ),
                            ))
                        else:
                            write_site_skipped_output(output_path, label)
                futures.append(("review", "design-system review", pool.submit(run_design_system_review)))
                futures.append(("conversion-review", "design-system conversion review", pool.submit(run_design_system_conversion_review)))

                for kind, name_for_status, future in futures:
                    try:
                        future.result()
                    except Exception as step_error:
                        if kind == "review":
                            step_status("design_system_review", "failed", {"error": str(step_error)})
                            log(f"  {tag} — design-system review skipped after error: {step_error}")
                            write_review_skipped_output(
                                review_json_path,
                                review_md_path,
                                f"Review failed: {step_error}",
                            )
                        elif kind == "conversion-review":
                            step_status("design_system_conversion_review", "failed", {"error": str(step_error)})
                            log(f"  {tag} — design-system conversion review skipped after error: {step_error}")
                            write_conversion_review_skipped_output(
                                conversion_review_json_path,
                                conversion_review_md_path,
                                f"Review failed: {step_error}",
                            )
                        else:
                            raise

                for provider_name, _, _ in provider_targets:
                    if provider_name in enabled_providers and not skip_vanilla_html:
                        step_status(f"site_generation_{provider_name}", "completed")
                if framework_generation_enabled:
                    for provider_name, _, _ in framework_provider_targets:
                        if provider_name in enabled_providers:
                            step_status(f"framework_site_generation_{provider_name}", "completed")

            step_status("run_complete", "completed")
            log(f"  {tag} — complete")
        except Exception as e:
            step_status("run_complete", "failed", {"error": str(e)})
            log(f"  {tag} — FAILED: {e}")
            # Write error placeholders so viewer doesn't break
            if site_generation_source != "grounding" and not design_system_artifact_path(mode_dir).exists():
                with open(mode_dir / "design-system.md", "w") as f:
                    f.write(f"# Error\n\nFailed to generate: {e}\n")
            for fname in (
                "site-claude.html",
                "site-gemini.html",
                "site-gpt55.html",
            ):
                if not (mode_dir / fname).exists():
                    with open(mode_dir / fname, "w") as f:
                        f.write(f"<html><body><h1>Error</h1><p>{e}</p></body></html>")
            review_json_path = mode_dir / "design-system-review.json"
            review_md_path = mode_dir / "design-system-review.md"
            if not review_json_path.exists():
                write_review_skipped_output(review_json_path, review_md_path, f"Review failed: {e}")
            conversion_review_json_path = mode_dir / "design-system-conversion-review.json"
            conversion_review_md_path = mode_dir / "design-system-conversion-review.md"
            if not conversion_review_json_path.exists():
                write_conversion_review_skipped_output(conversion_review_json_path, conversion_review_md_path, f"Review failed: {e}")

    def regenerate_existing_sites():
        """Rebuild site HTML from the configured saved markdown input."""
        source_label = "grounding" if site_generation_source == "grounding" else "design system"
        log(f"Sites-only mode: reusing existing {source_label} files")

        for i, screenshot_path in enumerate(screenshot_files):
            name = screenshot_path.stem
            item_dir = version_dir / name
            log(f"[{i+1}/{len(screenshot_files)}] {name} — checking saved generation inputs")

            mode_dir = item_dir / "single"
            ds_path = design_system_artifact_path(mode_dir)
            structural_path = mode_dir / "structural-analysis.md"

            if site_generation_source == "grounding":
                generation_input_path = structural_path
                generation_label = "grounding"
            else:
                generation_input_path = ds_path
                generation_label = "design system"

            if not generation_input_path.exists():
                log(f"  {name}/single — skipped (no {generation_label} input)")
                continue

            design_review_input = generation_input_path.read_text().strip()
            generation_input = design_review_input
            if not generation_input or generation_input.startswith("# Error") or generation_input.startswith("# Skipped"):
                log(f"  {name}/single — skipped ({generation_label} input is placeholder/error)")
                continue

            extracted_source_styles = None
            source_style_ledger_data = None
            source_html_path = find_source_html_for_screenshot(screenshot_path)
            if source_html_path and source_html_path.exists():
                extracted_source_styles = extract_source_colors(
                    source_html_path,
                    font_assets_dir=mode_dir / "source-fonts",
                )
                write_source_color_artifacts(mode_dir, extracted_source_styles)
                source_style_ledger_data = build_source_style_ledger(extracted_source_styles)
                write_source_style_ledger_artifact(mode_dir, source_style_ledger_data)
                generation_input = append_source_font_implementation(generation_input, extracted_source_styles)

            if generation_label == "design system":
                (mode_dir / "site-generation-input.raw-design-system.md").write_text(
                    build_site_generation_input(
                        generation_input,
                        generation_label,
                        site_generation_skills,
                    ).strip() + "\n"
                )
                generation_input = strip_source_provenance_for_site_generation(generation_input)
            generation_input = build_site_generation_input(
                generation_input,
                generation_label,
                site_generation_skills,
            )
            freshness_audit = audit_site_generation_freshness(generation_input, mode_dir)
            if generation_label == "design system" and freshness_audit["high_risk_match_count"]:
                raise ValueError(
                    "Site generation input still contains source-order/provenance leaks; "
                    f"see {mode_dir / 'site-generation-freshness-audit.json'}"
                )
            generation_label = "site generation input"
            site_generation_input_path = mode_dir / "site-generation-input.md"
            with open(site_generation_input_path, "w") as f:
                f.write(generation_input)

            enabled_providers = set(site_generation_providers)
            provider_targets = (
                ("claude", "site-claude.html", "Claude"),
                ("gemini", "site-gemini.html", "Gemini"),
                ("gpt55", "site-gpt55.html", "GPT-5.5"),
            )
            framework_provider_targets = (
                ("claude", "site-claude-framework.html", "Claude Framework"),
                ("gpt55", "site-gpt55-framework.html", "GPT-5.5 Framework"),
            )
            review_json_path = mode_dir / "design-system-review.json"
            review_md_path = mode_dir / "design-system-review.md"

            def run_existing_design_system_review():
                if skip_design_system_review:
                    write_review_skipped_output(
                        review_json_path,
                        review_md_path,
                        "Screenshot-based design-system review skipped because review model calls are disabled.",
                    )
                    return None
                if not design_system_review_needs_regeneration(review_json_path):
                    log(f"  {name}/single/design-system review — kept existing output")
                    return None
                log(f"  {name}/single/design-system review — reviewing sections against screenshot")
                review = evaluate_design_system_match(
                    reference_screenshot_path=screenshot_path,
                    design_system_markdown=design_review_input,
                    review_json_path=review_json_path,
                    review_md_path=review_md_path,
                    review_prompt=design_system_review_prompt,
                    config=config,
                    max_image_dimension=config.max_image_dimension,
                    output_dir=mode_dir,
                )
                log(f"  {name}/single/design-system review — score {review['weighted_score']:.2f}/100")
                return review

            def refresh_provider_site(provider_name: str, filename: str, label: str):
                output_path = mode_dir / filename
                if provider_name not in enabled_providers:
                    write_site_skipped_output(output_path, label)
                    log(f"  {name}/single/{label} — skipped by provider config")
                    return
                if not site_output_needs_regeneration(output_path):
                    viewport_unit_report = repair_html_file_viewport_layout_units(output_path)
                    if viewport_unit_report["replacement_count"]:
                        log(
                            f"  {name}/single/{label} — repaired "
                            f"{viewport_unit_report['replacement_count']} viewport layout unit(s)"
                        )
                    log(f"  {name}/single/{label} — kept existing output")
                else:
                    pre_sync_path = output_path.with_name(output_path.stem + ".pre-style-sync.html")
                    if pre_sync_path.exists() and extracted_source_styles:
                        html = pre_sync_path.read_text()
                        if html_document_is_complete(html):
                            html = enforce_source_site_styles(
                                html,
                                generation_markdown=generation_input,
                                extracted_source_styles=extracted_source_styles,
                                config=config,
                                site_style_sync_prompt=site_style_sync_prompt,
                                source_style_ledger=source_style_ledger_data,
                                audit_before_path=output_path.with_name(output_path.stem + "-style-audit.before.json"),
                                audit_after_path=output_path.with_name(output_path.stem + "-style-audit.after.json"),
                            )
                            output_path.write_text(html)
                            viewport_unit_report = repair_html_file_viewport_layout_units(output_path)
                            if viewport_unit_report["replacement_count"]:
                                log(
                                    f"  {name}/single/{label} — repaired "
                                    f"{viewport_unit_report['replacement_count']} viewport layout unit(s)"
                                )
                            apply_site_assets(
                                output_path,
                                generation_input,
                                f"{name}/single/{label} assets",
                                f"site_asset_generation_{provider_name}",
                            )
                            log(f"  {name}/single/{label} — recovered from pre-style-sync HTML")
                            return
                    gen_site(
                        generation_input,
                        provider_name,
                        output_path,
                        f"{name}/single/{label}",
                        extracted_source_styles,
                        source_style_ledger_data,
                        generation_label,
                    )

            def refresh_framework_site(provider_name: str, filename: str, label: str):
                output_path = mode_dir / filename
                if provider_name not in enabled_providers:
                    write_site_skipped_output(output_path, label)
                    log(f"  {name}/single/{label} — skipped by provider config")
                    return
                if not site_output_needs_regeneration(output_path):
                    log(f"  {name}/single/{label} — kept existing framework output")
                    return
                gen_framework_site(
                    generation_input,
                    provider_name,
                    output_path,
                    f"{name}/single/{label}",
                    generation_label,
                )

            worker_count = len(provider_targets) + 1
            if framework_generation_enabled:
                worker_count += len(framework_provider_targets)
            with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count) as pool:
                futures = [("review", pool.submit(run_existing_design_system_review))]
                if not skip_vanilla_html:
                    futures.extend(
                        (label, pool.submit(refresh_provider_site, provider_name, filename, label))
                        for provider_name, filename, label in provider_targets
                    )
                if framework_generation_enabled:
                    futures.extend(
                        (label, pool.submit(refresh_framework_site, provider_name, filename, label))
                        for provider_name, filename, label in framework_provider_targets
                    )
                for label, future in futures:
                    try:
                        future.result()
                    except Exception as review_error:
                        if label == "review":
                            log(f"  {name}/single/design-system review — skipped after error: {review_error}")
                            write_review_skipped_output(
                                review_json_path,
                                review_md_path,
                                f"Review failed: {review_error}",
                            )
                        else:
                            raise

            log(f"[{i+1}/{len(screenshot_files)}] {name} — site recovery done")

    def process_screenshot(i: int, screenshot_path: Path) -> dict:
        """Process one screenshot through the active single pipeline."""
        name = screenshot_path.stem
        item_dir = version_dir / name
        item_dir.mkdir(exist_ok=True)

        log(f"[{i+1}/{len(screenshot_files)}] {name} — starting")

        # Copy screenshot
        dest_screenshot = item_dir / f"screenshot{screenshot_path.suffix}"
        shutil.copy2(screenshot_path, dest_screenshot)

        single_dir = item_dir / "single"

        process_single_mode(name, screenshot_path, single_dir)

        log(f"[{i+1}/{len(screenshot_files)}] {name} — all done")

        return {
            "name": name,
            "screenshot": str(dest_screenshot.relative_to(version_dir)),
            "single": {
                "structural_analysis": str((single_dir / "structural-analysis.md").relative_to(version_dir)),
                "layouts": str((single_dir / "layouts.yaml").relative_to(version_dir)) if (single_dir / "layouts.yaml").exists() else "",
                "design_system": str(((single_dir / "structural-analysis.md") if site_generation_source == "grounding" else design_system_artifact_path(single_dir)).relative_to(version_dir)),
                "site_generation_input": str((single_dir / "site-generation-input.md").relative_to(version_dir)),
                "surface_component_contract": str((single_dir / "surface-component-contract.yaml").relative_to(version_dir)) if (single_dir / "surface-component-contract.yaml").exists() else "",
                "surface_component_contract_audit": str((single_dir / "surface-component-contract-audit.md").relative_to(version_dir)) if (single_dir / "surface-component-contract-audit.md").exists() else "",
                "source_style_ledger": str((single_dir / "source-style-ledger.yaml").relative_to(version_dir)) if (single_dir / "source-style-ledger.yaml").exists() else "",
                "design_system_style_audit": str((single_dir / "design-system-style-audit.json").relative_to(version_dir)) if (single_dir / "design-system-style-audit.json").exists() else "",
                "design_system_review": str((single_dir / "design-system-review.md").relative_to(version_dir)),
                "design_system_conversion_review": str((single_dir / "design-system-conversion-review.md").relative_to(version_dir)),
                "site_claude": str((single_dir / "site-claude.html").relative_to(version_dir)),
                "site_gemini": str((single_dir / "site-gemini.html").relative_to(version_dir)),
                "site_gpt55": str((single_dir / "site-gpt55.html").relative_to(version_dir)),
                "site_claude_framework": str((single_dir / "site-claude-framework.html").relative_to(version_dir))
                if (single_dir / "site-claude-framework.html").exists()
                else "",
                "site_gpt55_framework": str((single_dir / "site-gpt55-framework.html").relative_to(version_dir))
                if (single_dir / "site-gpt55-framework.html").exists()
                else "",
            },
        }

    if sites_only:
        regenerate_existing_sites()
        with open(version_dir / "manifest.json", "w") as f:
            json.dump(infer_manifest_from_version_dir(version_dir), f, indent=2)
        log("Generating viewer.html...")
        generate_viewer(RUNS_DIR, PROJECT_DIR / "viewer.html")
        log(f"Done! Site outputs refreshed in {version_dir}")
        return

    # Run screenshots in parallel as well as provider fan-out so independent items
    # do not block each other. Section grounding is heavier, so keep the worker
    # count conservative when that flow is enabled.
    screenshot_workers = min(
        len(screenshot_files),
        1 if (design_only and reuse_analysis_from and design_system_strategy != "one-shot")
        else (2 if (design_only and reuse_analysis_from) else (5 if (surface_map_only and reuse_analysis_from) else (2 if section_grounding_bundle else 5))),
    )
    with concurrent.futures.ThreadPoolExecutor(max_workers=screenshot_workers) as pool:
        futures = {
            pool.submit(process_screenshot, i, path): path
            for i, path in enumerate(screenshot_files)
        }
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            manifest["screenshots"].append(result)

    # Sort manifest by name for consistent ordering
    manifest["screenshots"].sort(key=lambda x: x["name"])

    # Save manifest
    with open(version_dir / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

    # Generate self-contained viewer with ALL versions embedded
    log("Generating viewer.html...")
    generate_viewer(RUNS_DIR, PROJECT_DIR / "viewer.html")

    log(f"Done! Results saved to {version_dir}")
    log(f"Open viewer.html in your browser to compare results.")


def main():
    parser = argparse.ArgumentParser(description="Run the screenshot-to-template pipeline")
    parser.add_argument("--version", default=None, help="Version label (default: auto-increment)")
    parser.add_argument("--screenshots-dir", default=None, help="Path to screenshots directory")
    parser.add_argument("--runs-dir", default=None, help="Path to runs output directory")
    parser.add_argument("--config", default=None, help="Optional YAML config override")
    parser.add_argument("--single-only", action="store_true", help="Deprecated no-op; the pipeline now runs only the single active mode")
    parser.add_argument("--sites-only", action="store_true", help="Regenerate site HTML from existing design-system markdown")
    parser.add_argument(
        "--framework-sites",
        action="store_true",
        help="Force framework site generation on (default when framework-generation-enabled in config)",
    )
    parser.add_argument(
        "--vanilla-sites",
        action="store_true",
        help="Also generate vanilla one-shot HTML (site-claude.html / site-gpt55.html) in addition to framework",
    )
    parser.add_argument("--assets-only", action="store_true", help="Generate missing site image assets for existing generated HTML")
    parser.add_argument("--design-only", action="store_true", help="Generate design-system artifacts, then skip site HTML generation")
    parser.add_argument("--surface-map-only", action="store_true", help="Generate surface-component maps, then skip design-system and site generation")
    asset_group = parser.add_mutually_exclusive_group()
    asset_group.add_argument("--site-assets", action="store_true", default=None, help="Enable generated site image assets, overriding config")
    asset_group.add_argument("--no-site-assets", action="store_false", dest="site_assets", help="Disable generated site image assets, overriding config")
    parser.add_argument("--run-reviews", action="store_true", default=None, help="Enable review model calls for full-page, surface-map, design-system, and conversion reviews")
    parser.add_argument("--skip-design-system-review", action="store_true", help="Skip screenshot-based design-system review when reviews are enabled")
    parser.add_argument(
        "--design-system-strategy",
        default="one-shot",
        choices=("one-shot", "additive-crops", "domain-agents", "schema-ledger", "surface-shards", "self-refine-repair", "contract-render"),
        help="Experimental strategy for converting grounding/surface maps into design-system markdown",
    )
    parser.add_argument("--reuse-analysis-from", default=None, help="Existing run version to reuse structural and section-grounding artifacts from")
    parser.add_argument("--review-guidance-from", default=None, help="Existing run version whose design-system reviews should guide the next synthesis")
    parser.add_argument("--design-system-seed-from", default=None, help="Existing run version whose design systems should be used as revision seeds")
    parser.add_argument("--design-system-best-seed-from", default=None, help="Comma/range version spec; for each site, seed from the prior design system with the highest conversion-review score")
    parser.add_argument("--conversion-review-guidance-from", default=None, help="Existing run version whose design-system conversion reviews should guide the next synthesis")
    parser.add_argument("--conversion-review-best-guidance-from", default=None, help="Comma/range version spec; for each site, use the conversion review from the highest-scoring prior design system")
    parser.add_argument("--surface-map-review-guidance-from", default=None, help="Existing run version whose surface-map reviews should guide the next synthesis")
    parser.add_argument("--surface-map-seed-from", default=None, help="Existing run version whose surface-component maps should be used as revision seeds")
    parser.add_argument("--surface-map-best-seed-from", default=None, help="Comma/range version spec; for each site, seed from the prior surface map with the highest review score")
    parser.add_argument("--surface-map-use-best-existing-from", default=None, help="Comma/range version spec; for each site, copy the prior surface map with the highest review score and review it")
    parser.add_argument("--surface-map-mode", choices=("auto", "model", "contract", "skip"), default=None, help="Surface/component intermediate mode: auto, model, contract, or skip")
    parser.add_argument("--reuse-section-groundings-from", default=None, help="Existing run version whose per-section YAML groundings should be reused while rerunning global/merge/design steps")
    args = parser.parse_args()

    global RUNS_DIR, SCREENSHOTS_DIR
    if args.runs_dir:
        RUNS_DIR = Path(args.runs_dir)
    if args.screenshots_dir:
        SCREENSHOTS_DIR = Path(args.screenshots_dir)

    version = args.version or get_next_version()
    run_pipeline(
        version,
        SCREENSHOTS_DIR,
        config_path=args.config,
        single_only=args.single_only,
        sites_only=args.sites_only,
        framework_sites=args.framework_sites,
        vanilla_sites=args.vanilla_sites,
        assets_only=args.assets_only,
        design_only=args.design_only,
        surface_map_only=args.surface_map_only,
        site_assets_enabled=args.site_assets,
        skip_design_system_review=args.skip_design_system_review,
        run_reviews=args.run_reviews,
        design_system_strategy=args.design_system_strategy,
        reuse_analysis_from=args.reuse_analysis_from,
        review_guidance_from=args.review_guidance_from,
        design_system_seed_from=args.design_system_seed_from,
        design_system_best_seed_from=args.design_system_best_seed_from,
        conversion_review_guidance_from=args.conversion_review_guidance_from,
        conversion_review_best_guidance_from=args.conversion_review_best_guidance_from,
        surface_map_review_guidance_from=args.surface_map_review_guidance_from,
        surface_map_seed_from=args.surface_map_seed_from,
        surface_map_best_seed_from=args.surface_map_best_seed_from,
        surface_map_use_best_existing_from=args.surface_map_use_best_existing_from,
        surface_map_mode=args.surface_map_mode,
        reuse_section_groundings_from=args.reuse_section_groundings_from,
    )


if __name__ == "__main__":
    main()
