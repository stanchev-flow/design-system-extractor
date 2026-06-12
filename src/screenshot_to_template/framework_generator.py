"""Framework-based site generation: React + Tailwind v4 + shadcn-style components.

Scaffolds a per-run Vite package from handoff/scaffold/framework-site, syncs
tokens from the design-system YAML front matter, asks an LLM for App.tsx (and
optional CSS), builds with vite-plugin-singlefile, and copies dist/index.html
into the pipeline's single/ folder for viewer embedding.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import yaml

from .browser_chrome_extractor import load_chrome_contract_v2
from .chrome_codegen import write_chrome_components
from .chrome_extractor import load_chrome_contract, summarize_chrome_contract
from .models.anthropic import AnthropicProvider
from .models.openai import OpenAIProvider

PROJECT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_SCAFFOLD_DIR = PROJECT_DIR / "handoff" / "scaffold" / "framework-site"
DEFAULT_FRAMEWORK_PROMPT_PATH = PROJECT_DIR / "website-gen-framework-prompt.md"
FRAMEWORK_GEN_MAX_TOKENS = 32768

SCAFFOLD_SKIP = {"node_modules", "dist", ".git", "tsconfig.tsbuildinfo"}


def load_framework_prompt(prompt_path: Path | None = None) -> str:
    path = prompt_path or DEFAULT_FRAMEWORK_PROMPT_PATH
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    raise FileNotFoundError(f"Framework generation prompt not found: {path}")


def parse_design_system_front_matter(markdown: str) -> dict[str, Any]:
    """Extract YAML front matter from design-system or site-generation-input markdown."""
    for match in re.finditer(r"(?:^|\n)---\s*\n(.*?)\n---", markdown, flags=re.DOTALL):
        try:
            payload = yaml.safe_load(match.group(1))
        except yaml.YAMLError:
            continue
        if isinstance(payload, dict) and payload.get("schema_version"):
            return payload

    # Fence-less fallback: site-generation-input.md embeds the design-system
    # YAML directly under a markdown heading (no --- fences). Parse from the
    # `schema_version:` line up to the next top-level markdown heading.
    lines = markdown.splitlines()
    start = next(
        (i for i, line in enumerate(lines) if line.startswith("schema_version:")),
        None,
    )
    if start is not None:
        end = next(
            (i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")),
            len(lines),
        )
        try:
            payload = yaml.safe_load("\n".join(lines[start:end]))
        except yaml.YAMLError:
            payload = None
        if isinstance(payload, dict) and payload.get("schema_version"):
            return payload
    return {}


def _token_color(value: str | None, fallback: str) -> str:
    if not value or not str(value).strip():
        return fallback
    return str(value).strip().strip("'\"")


def _is_design_system_yaml_v1(front_matter: dict[str, Any]) -> bool:
    return front_matter.get("schema_version") == "design_system_yaml.v1"


_TYPOGRAPHY_ROLE_ALIASES = {
    "display_heading": ("display_heading", "displayHero", "display"),
    "eyebrow": ("eyebrow", "label", "kicker", "labelSans"),
}


def _typography_role(front_matter: dict[str, Any], role: str) -> dict[str, Any]:
    typography = front_matter.get("typography")
    if not isinstance(typography, dict):
        return {}
    for key in _TYPOGRAPHY_ROLE_ALIASES.get(role, (role,)):
        node = typography.get(key)
        if isinstance(node, dict):
            return node
    return {}


def _typo_field(front_matter: dict[str, Any], role: str, field: str, default: str) -> str:
    return str(_typography_role(front_matter, role).get(field) or default)


def build_v1_theme_block(front_matter: dict[str, Any]) -> str:
    """Tailwind v4 @theme block aligned with design_system_yaml.v1 token names."""
    tokens = front_matter.get("tokens") if isinstance(front_matter.get("tokens"), dict) else {}
    color = tokens.get("color") if isinstance(tokens.get("color"), dict) else {}
    surface = color.get("surface") if isinstance(color.get("surface"), dict) else {}
    text = color.get("text") if isinstance(color.get("text"), dict) else {}
    border = color.get("border") if isinstance(color.get("border"), dict) else {}
    accent = color.get("accent") if isinstance(color.get("accent"), dict) else {}
    graphic = color.get("graphic") if isinstance(color.get("graphic"), dict) else {}
    radius = tokens.get("radius") if isinstance(tokens.get("radius"), dict) else {}
    shadow = tokens.get("shadow") if isinstance(tokens.get("shadow"), dict) else {}

    floating = "#FFFFFF"
    surfaces = front_matter.get("surfaces")
    if isinstance(surfaces, dict):
        card = surfaces.get("floating_card")
        if isinstance(card, dict) and card.get("value"):
            floating = _token_color(card.get("value"), floating)

    shadow_val = _token_color(
        shadow.get("floatingCard"),
        "0 8px 24px rgba(20,40,30,0.12)",
    )

    def first(*values: Any) -> str | None:
        """First non-empty candidate — tolerates vocabulary drift between
        extracted design systems (e.g. text.onPrimary vs text.primary)."""
        for v in values:
            if v and str(v).strip():
                return str(v)
        return None

    return f"""@theme {{
  --color-surface-primary: {_token_color(surface.get("primary"), "#FFFFFF")};
  --color-surface-secondary: {_token_color(first(surface.get("secondary"), surface.get("panel")), "#f5f7f6")};
  --color-surface-inverse: {_token_color(surface.get("inverse"), "#0f281b")};
  --color-surface-inverseSoft: {_token_color(first(surface.get("inverseSoft"), surface.get("inverseStrong"), surface.get("inverse")), "#16201a")};
  --color-surface-control: {_token_color(first(surface.get("control"), surface.get("panel"), surface.get("primary")), "#FFFFFF")};

  --color-text-primary: {_token_color(first(text.get("primary"), text.get("onPrimary")), "#1c2a21")};
  --color-text-muted: {_token_color(first(text.get("muted"), text.get("onPrimaryMuted")), "#5b665d")};
  --color-text-onInverse: {_token_color(text.get("onInverse"), "#f4f6f3")};
  --color-text-onInverseMuted: {_token_color(text.get("onInverseMuted"), "#9ab7b2")};
  --color-text-onSecondary: {_token_color(first(text.get("onSecondary"), text.get("onPrimary"), text.get("primary")), "#1c2a21")};
  --color-text-accent: {_token_color(first(text.get("accent"), accent.get("primary"), accent.get("highlight")), "#1e7a4d")};

  --color-border-onPrimary: {_token_color(first(border.get("onPrimary"), border.get("hairlineOnPrimary")), "#1c2a21")};
  --color-border-onInverse: {_token_color(border.get("onInverse"), "rgba(255,255,255,0.16)")};
  --color-border-divider: {_token_color(first(border.get("divider"), border.get("hairlineOnPanel"), border.get("hairlineOnPrimary")), "#e3e2dc")};

  --color-accent-primary: {_token_color(first(accent.get("primary"), accent.get("highlight"), text.get("accent")), "#1e7a4d")};
  --color-accent-onAccent: {_token_color(first(accent.get("onAccent"), text.get("onPrimary")), "#ffffff")};
  --color-accent-secondary: {_token_color(first(accent.get("secondary"), surface.get("inverse")), "#2b4539")};
  --color-accent-onSecondary: {_token_color(first(accent.get("onSecondary"), text.get("onInverse")), "#ffffff")};
  --color-accent-soft: {_token_color(first(accent.get("soft"), surface.get("panel"), surface.get("secondary")), "#d7e2dd")};

  --color-graphic-tintChip: {_token_color(first(graphic.get("tintChip"), accent.get("highlight"), accent.get("soft")), "#a9d6c4")};
  --color-graphic-lineMotif: {_token_color(first(graphic.get("lineMotif"), surface.get("inverse")), "#234a38")};

  --color-floating-card: {floating};

  --font-serif: Georgia, 'Times New Roman', serif;
  --font-sans: ui-sans-serif, system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;

  --text-display: {_typo_field(front_matter, "display_heading", "fontSize", "60px")};
  --text-display--line-height: {_typo_field(front_matter, "display_heading", "lineHeight", "1.05")};
  --text-display--letter-spacing: {_typo_field(front_matter, "display_heading", "letterSpacing", "-0.01em")};
  --text-h1: {_typo_field(front_matter, "h1", "fontSize", "56px")};
  --text-h1--line-height: {_typo_field(front_matter, "h1", "lineHeight", "1.1")};
  --text-h1--letter-spacing: {_typo_field(front_matter, "h1", "letterSpacing", "-0.01em")};
  --text-h2: {_typo_field(front_matter, "h2", "fontSize", "40px")};
  --text-h2--line-height: {_typo_field(front_matter, "h2", "lineHeight", "1.15")};
  --text-h2--letter-spacing: {_typo_field(front_matter, "h2", "letterSpacing", "-0.005em")};
  --text-h3: {_typo_field(front_matter, "h3", "fontSize", "24px")};
  --text-h3--line-height: {_typo_field(front_matter, "h3", "lineHeight", "1.2")};
  --text-body: {_typo_field(front_matter, "body", "fontSize", "16px")};
  --text-body--line-height: {_typo_field(front_matter, "body", "lineHeight", "1.55")};
  --text-control: {_typo_field(front_matter, "control", "fontSize", "16px")};
  --text-control--line-height: {_typo_field(front_matter, "control", "lineHeight", "1")};
  --text-eyebrow: {_typo_field(front_matter, "eyebrow", "fontSize", "14px")};
  --text-eyebrow--line-height: {_typo_field(front_matter, "eyebrow", "lineHeight", "1.3")};
  --text-eyebrow--letter-spacing: {_typo_field(front_matter, "eyebrow", "letterSpacing", "0.01em")};
  --text-legal: {_typo_field(front_matter, "legal", "fontSize", "14px")};
  --text-legal--line-height: {_typo_field(front_matter, "legal", "lineHeight", "1.4")};

  --radius-pill: {_token_color(radius.get("pill"), "999px")};
  --radius-media: {_token_color(radius.get("media"), "8px")};
  --radius-chip: {_token_color(radius.get("chip"), "6px")};
  --radius-input: {_token_color(radius.get("input"), "4px")};
  --radius-panel: {_token_color(radius.get("media"), "8px")};

  --shadow-floating: {shadow_val};

  /* aliases for scaffold ui components (Hatch-era token names) */
  --color-surface-soft: var(--color-accent-soft);
  --color-border-hairline: var(--color-border-divider);
  --color-accent: var(--color-accent-primary);
  --color-accent-foreground: var(--color-accent-onAccent);
  --color-accent-highlight: var(--color-accent-soft);
  --color-text-accent-on-inverse: var(--color-text-onInverseMuted);
  --shadow-card: var(--shadow-floating);

  /* kebab-case aliases used by generated chrome components */
  --color-text-on-inverse: var(--color-text-onInverse);
  --color-text-on-inverse-muted: var(--color-text-onInverseMuted);
  --color-border-on-inverse: var(--color-border-onInverse);
}}"""


def _extract_scaffold_css_tail(scaffold_css: str) -> str:
    """Return scaffold CSS after the @theme block (base + component layers)."""
    match = re.search(r"@theme\s*\{[^}]*\}", scaffold_css, flags=re.DOTALL)
    if not match:
        return ""
    return scaffold_css[match.end() :].strip()


def merge_scaffold_index_css_layers(
    index_css_path: Path,
    *,
    scaffold_dir: Path | None = None,
) -> bool:
    """Re-append scaffold @layer rules when the LLM replaced index.css with @theme only."""
    if not index_css_path.exists():
        return False
    css = index_css_path.read_text(encoding="utf-8")
    if "@layer components" in css and ".btn[data-variant=" in css:
        return False

    source = (scaffold_dir or DEFAULT_SCAFFOLD_DIR) / "src" / "index.css"
    if not source.exists():
        return False
    tail = _extract_scaffold_css_tail(source.read_text(encoding="utf-8"))
    if not tail:
        return False

    if "@import" not in css:
        css = '@import "tailwindcss";\n\n' + css
    patched = css.rstrip() + "\n\n" + tail + "\n"
    index_css_path.write_text(patched, encoding="utf-8")
    return True


def summarize_brand_assets_manifest(manifest_path: Path | None) -> str:
    if not manifest_path or not manifest_path.exists():
        return ""
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return ""
    by_role = data.get("byRole") if isinstance(data.get("byRole"), dict) else {}
    counts = {role: len(items) for role, items in by_role.items() if isinstance(items, list) and items}
    if not counts:
        return ""
    lines = [f"- source: {data.get('source', 'pipeline')}"]
    for role, count in sorted(counts.items(), key=lambda x: (-x[1], x[0])):
        lines.append(f"- {role}: {count} asset(s)")
    return (
        "Brand assets manifest (use @/brand/assets — heroMedia, avatars, logoWall, bestSrc):\n"
        + "\n".join(lines)
    )


def design_system_to_dtcg_tokens(front_matter: dict[str, Any]) -> dict[str, Any]:
    """Map design_system_yaml.v1 tokens into a DTCG tokens.json shape."""
    tokens = front_matter.get("tokens") if isinstance(front_matter.get("tokens"), dict) else {}
    color = tokens.get("color") if isinstance(tokens.get("color"), dict) else {}
    surface = color.get("surface") if isinstance(color.get("surface"), dict) else {}
    text = color.get("text") if isinstance(color.get("text"), dict) else {}
    border = color.get("border") if isinstance(color.get("border"), dict) else {}
    accent = color.get("accent") if isinstance(color.get("accent"), dict) else {}
    graphic = color.get("graphic") if isinstance(color.get("graphic"), dict) else {}
    radius = tokens.get("radius") if isinstance(tokens.get("radius"), dict) else {}
    shadow = tokens.get("shadow") if isinstance(tokens.get("shadow"), dict) else {}
    spacing = tokens.get("spacing") if isinstance(tokens.get("spacing"), dict) else {}
    roles = spacing.get("roles") if isinstance(spacing.get("roles"), dict) else {}
    typography = tokens.get("typography") if isinstance(tokens.get("typography"), dict) else {}
    families = typography.get("families") if isinstance(typography.get("families"), dict) else {}

    heading_font = families.get("heading") or "Instrument Sans"
    body_font = families.get("body") or heading_font
    if isinstance(heading_font, list):
        heading_font = heading_font[0] if heading_font else "Instrument Sans"
    if isinstance(body_font, list):
        body_font = body_font[0] if body_font else heading_font

    meta_name = ""
    metadata = front_matter.get("metadata")
    if isinstance(metadata, dict):
        meta_name = str(metadata.get("name") or "")

    return {
        "$description": f"Design tokens synced from pipeline extraction{f' ({meta_name})' if meta_name else ''}.",
        "color": {
            "$type": "color",
            "surface": {
                "primary": {"$value": _token_color(surface.get("primary"), "#ffffff")},
                "secondary": {"$value": _token_color(surface.get("secondary"), "#f5f7f6")},
                "inverse": {"$value": _token_color(surface.get("inverse"), "#0f281b")},
                "soft": {
                    "$value": _token_color(
                        surface.get("soft")
                        or surface.get("inverseSoft")
                        or surface.get("accentSoftPanel"),
                        "#d7e2dd",
                    )
                },
                "media": {
                    "$value": _token_color(surface.get("media") or surface.get("mediaDark"), "#20211f")
                },
            },
            "text": {
                "primary": {"$value": _token_color(text.get("primary"), "#212d3a")},
                "muted": {"$value": _token_color(text.get("muted"), "#5b665d")},
                "on-inverse": {"$value": _token_color(text.get("onInverse"), "#f4f6f3")},
                "on-inverse-muted": {"$value": _token_color(text.get("onInverseMuted"), "#9ab7b2")},
                "on-media": {"$value": _token_color(text.get("onMedia"), "#ffffff")},
                "accent-on-inverse": {
                    "$value": _token_color(text.get("accentOnInverse"), "#9ab7b2")
                },
            },
            "border": {
                "hairline": {
                    "$value": _token_color(
                        border.get("hairline") or border.get("divider") or border.get("onPrimary"),
                        "#e3e2dc",
                    )
                },
                "on-inverse": {"$value": _token_color(border.get("onInverse"), "rgba(255,255,255,0.16)")},
                "field": {"$value": _token_color(border.get("field"), "#d9ddd6")},
            },
            "accent": {
                "primary": {"$value": _token_color(accent.get("primary"), "#0f281b")},
                "on-accent": {"$value": _token_color(accent.get("onAccent"), "#ffffff")},
                "secondary": {"$value": _token_color(accent.get("secondary"), "#2b4539")},
                "highlight-on-dark": {
                    "$value": _token_color(accent.get("highlightOnDark"), "#9ab7b2")
                },
            },
            "graphic": {
                "star-rating": {"$value": _token_color(graphic.get("starRating"), "#faae7a")},
                "logo-muted": {"$value": _token_color(graphic.get("logoMuted"), "#959494")},
                "tint-chip": {"$value": _token_color(graphic.get("tintChip"), "#a9d6c4")},
                "line-motif": {"$value": _token_color(graphic.get("lineMotif"), "#234a38")},
            },
        },
        "font": {
            "$type": "fontFamily",
            "heading": {"$value": [str(heading_font), "Georgia", "sans-serif"]},
            "body": {"$value": [str(body_font), "Georgia", "sans-serif"]},
        },
        "radius": {
            "$type": "dimension",
            "sm": {"$value": _token_color(radius.get("sm"), "8px")},
            "md": {"$value": _token_color(radius.get("md"), "12px")},
            "lg": {"$value": _token_color(radius.get("lg"), "16px")},
            "panel": {"$value": _token_color(radius.get("panel"), "20px")},
            "pill": {"$value": _token_color(radius.get("pill"), "999px")},
        },
        "shadow": {
            "$type": "shadow",
            "floating-card": {
                "$value": _token_color(shadow.get("floatingCard"), "0 8px 24px rgba(20,30,24,0.12)")
            },
        },
        "space": {
            "$type": "dimension",
            "section-y": {"$value": _token_color(roles.get("sectionPaddingY"), "96px")},
            "section-y-tight": {"$value": _token_color(roles.get("sectionPaddingYTight"), "64px")},
        },
    }


def sync_index_css_theme_from_design_system(
    index_css_path: Path,
    design_system_markdown: str,
) -> None:
    """Patch @theme in index.css from design-system YAML (v1-aware)."""
    if not index_css_path.exists():
        return
    front_matter = parse_design_system_front_matter(design_system_markdown)
    if _is_design_system_yaml_v1(front_matter):
        theme_block = build_v1_theme_block(front_matter)
    else:
        sync_index_css_theme(index_css_path, design_system_to_dtcg_tokens(front_matter))
        return
    css = index_css_path.read_text(encoding="utf-8")
    patched, count = re.subn(r"@theme\s*\{[^}]*\}", theme_block, css, count=1, flags=re.DOTALL)
    if count:
        index_css_path.write_text(patched, encoding="utf-8")


def sync_index_css_theme(index_css_path: Path, dtcg: dict[str, Any]) -> None:
    """Patch the @theme block in index.css from synced DTCG tokens (legacy Hatch shape)."""
    if not index_css_path.exists():
        return

    color = dtcg.get("color", {})
    surface = color.get("surface", {})
    text = color.get("text", {})
    border = color.get("border", {})
    accent = color.get("accent", {})
    graphic = color.get("graphic", {})
    font = dtcg.get("font", {})
    radius = dtcg.get("radius", {})
    shadow = dtcg.get("shadow", {})
    space = dtcg.get("space", {})

    def val(group: dict, key: str, default: str) -> str:
        node = group.get(key, {})
        if isinstance(node, dict):
            return str(node.get("$value", default))
        return default

    heading = val(font, "heading", "Instrument Sans, Georgia, sans-serif")
    body = val(font, "body", heading)
    if isinstance(font.get("heading", {}).get("$value"), list):
        heading = ", ".join(f'"{f}"' if " " in str(f) else str(f) for f in font["heading"]["$value"])
    if isinstance(font.get("body", {}).get("$value"), list):
        body = ", ".join(f'"{f}"' if " " in str(f) else str(f) for f in font["body"]["$value"])

    theme_block = f"""@theme {{
  --color-surface-primary: {val(surface, 'primary', '#ffffff')};
  --color-surface-secondary: {val(surface, 'secondary', '#f5f7f6')};
  --color-surface-inverse: {val(surface, 'inverse', '#0f281b')};
  --color-surface-soft: {val(surface, 'soft', '#d7e2dd')};
  --color-surface-media: {val(surface, 'media', '#20211f')};

  --color-text-primary: {val(text, 'primary', '#212d3a')};
  --color-text-muted: {val(text, 'muted', '#5b665d')};
  --color-text-on-inverse: {val(text, 'on-inverse', '#f4f6f3')};
  --color-text-on-inverse-muted: {val(text, 'on-inverse-muted', '#9ab7b2')};
  --color-text-on-media: {val(text, 'on-media', '#ffffff')};
  --color-text-accent-on-inverse: {val(text, 'accent-on-inverse', '#9ab7b2')};

  --color-border-hairline: {val(border, 'hairline', '#e3e2dc')};
  --color-border-on-inverse: {val(border, 'on-inverse', 'rgba(255, 255, 255, 0.16)')};
  --color-border-field: {val(border, 'field', '#d9ddd6')};

  --color-accent: {val(accent, 'primary', '#0f281b')};
  --color-accent-foreground: {val(accent, 'on-accent', '#ffffff')};
  --color-accent-secondary: {val(accent, 'secondary', '#2b4539')};
  --color-accent-highlight: {val(accent, 'highlight-on-dark', '#9ab7b2')};
  --color-graphic-star: {val(graphic, 'star-rating', '#faae7a')};
  --color-graphic-logo: {val(graphic, 'logo-muted', '#959494')};

  --font-heading: {heading};
  --font-body: {body};

  --text-h1: 56px;
  --text-h1--line-height: 1.02;
  --text-h1--letter-spacing: -0.01em;
  --text-h1--font-weight: 700;
  --text-h2: 40px;
  --text-h2--line-height: 1.05;
  --text-h2--letter-spacing: -0.01em;
  --text-h2--font-weight: 700;
  --text-h3: 24px;
  --text-h3--line-height: 1.15;
  --text-h3--letter-spacing: -0.005em;
  --text-h3--font-weight: 700;
  --text-metric: 52px;
  --text-metric--line-height: 1;
  --text-metric--letter-spacing: -0.01em;
  --text-metric--font-weight: 700;
  --text-quote: 22px;
  --text-quote--line-height: 1.25;
  --text-quote--letter-spacing: -0.005em;
  --text-quote--font-weight: 700;
  --text-lead: 16px;
  --text-lead--line-height: 1.5;
  --text-body: 15px;
  --text-body--line-height: 1.55;
  --text-eyebrow: 12px;
  --text-eyebrow--line-height: 1.2;
  --text-eyebrow--letter-spacing: 0.08em;
  --text-eyebrow--font-weight: 500;
  --text-meta: 13px;
  --text-meta--line-height: 1.4;
  --text-control: 15px;
  --text-control--line-height: 1.2;
  --text-control--font-weight: 500;

  --radius-sm: {val(radius, 'sm', '8px')};
  --radius-md: {val(radius, 'md', '12px')};
  --radius-lg: {val(radius, 'lg', '16px')};
  --radius-panel: {val(radius, 'panel', '20px')};
  --radius-pill: {val(radius, 'pill', '999px')};

  --shadow-card: {val(shadow, 'floating-card', '0 8px 24px rgba(20, 30, 24, 0.12)')};

  --spacing-section: {val(space, 'section-y', '96px')};
  --spacing-section-tight: {val(space, 'section-y-tight', '64px')};
}}"""

    css = index_css_path.read_text(encoding="utf-8")
    patched, count = re.subn(r"@theme\s*\{[^}]*\}", theme_block, css, count=1, flags=re.DOTALL)
    if count:
        index_css_path.write_text(patched, encoding="utf-8")


def scaffold_framework_project(
    target_dir: Path,
    *,
    scaffold_dir: Path | None = None,
    brand_assets_manifest: Path | None = None,
) -> Path:
    """Copy the framework template into target_dir (fresh each run)."""
    source = scaffold_dir or DEFAULT_SCAFFOLD_DIR
    if not source.exists():
        raise FileNotFoundError(f"Framework scaffold not found: {source}")

    if target_dir.exists():
        shutil.rmtree(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    for item in source.iterdir():
        if item.name in SCAFFOLD_SKIP:
            continue
        dest = target_dir / item.name
        if item.is_dir():
            shutil.copytree(item, dest, ignore=shutil.ignore_patterns(*SCAFFOLD_SKIP))
        else:
            shutil.copy2(item, dest)

    if brand_assets_manifest and brand_assets_manifest.exists():
        brand_dir = target_dir / "src" / "brand"
        brand_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(brand_assets_manifest, brand_dir / "brand-assets.json")

    return target_dir


def apply_tokens_from_design_system(framework_dir: Path, design_system_markdown: str) -> dict[str, Any]:
    """Write tokens/tokens.json and patch index.css @theme from design-system YAML."""
    front_matter = parse_design_system_front_matter(design_system_markdown)
    dtcg = design_system_to_dtcg_tokens(front_matter)

    tokens_dir = framework_dir / "tokens"
    tokens_dir.mkdir(parents=True, exist_ok=True)
    (tokens_dir / "tokens.json").write_text(json.dumps(dtcg, indent=2) + "\n", encoding="utf-8")

    sync_index_css_theme_from_design_system(framework_dir / "src" / "index.css", design_system_markdown)
    return dtcg


def extract_json_payload(text: str) -> dict[str, Any]:
    """Parse a JSON object from an LLM response."""
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped, flags=re.IGNORECASE)
        stripped = re.sub(r"\s*```$", "", stripped)

    try:
        payload = json.loads(stripped)
        if isinstance(payload, dict):
            return payload
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", stripped, flags=re.DOTALL)
    if match:
        payload = json.loads(match.group(0))
        if isinstance(payload, dict):
            return payload
    raise ValueError("Framework generation response did not contain a JSON object")


def generate_framework_files(
    generation_markdown: str,
    provider_name: str,
    framework_dir: Path,
    *,
    framework_prompt: str | None = None,
    generation_label: str = "design system",
    brand_assets_manifest: Path | None = None,
    chrome_contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Ask the LLM for React source files and write them into the framework package."""
    prompt = framework_prompt or load_framework_prompt()
    front_matter = parse_design_system_front_matter(generation_markdown)
    theme_excerpt = ""
    if _is_design_system_yaml_v1(front_matter):
        theme_excerpt = (
            "Synced @theme (use these exact utilities — do not invent hex):\n```css\n"
            + build_v1_theme_block(front_matter)
            + "\n```\n"
        )
    brand_summary = summarize_brand_assets_manifest(brand_assets_manifest)
    chrome_summary = summarize_chrome_contract(chrome_contract)
    chrome_rules = ""
    if chrome_contract and (chrome_contract.get("nav") or {}).get("found"):
        chrome_rules = (
            "Chrome (required):\n"
            "- `src/components/chrome/SiteNav.tsx` and `SiteFooter.tsx` are ALREADY generated from the live URL.\n"
            "- Import `{ SiteNav, SiteFooter }` from `@/components/chrome` in App.tsx.\n"
            "- Do NOT invent alternate nav/footer links, labels, or hrefs.\n"
            "- Compose ONLY the body (hero → sections → pre-footer CTA). Bookend with <SiteNav /> and <SiteFooter />.\n\n"
        )
    scaffold_summary = (
        "Scaffold layout (already on disk — import these paths):\n"
        "- src/App.tsx (replace entirely)\n"
        "- src/index.css (@theme already synced — do NOT replace the file unless adding 1–2 missing keys)\n"
        "- src/components/ui/{button,badge,card,arrow-link,input,icon-button,section,stat}.tsx\n"
        "- src/components/chrome/{SiteNav,SiteFooter,BrandMark}.tsx when source chrome exists\n"
        "- src/brand/assets.ts + brand-assets.json\n"
        "Button data-variant values: primary | secondary | ghost | onMedia only (no outline/primaryInverse).\n"
        "Buttons have NO trailing arrow by default. Only pass `withArrow` when the source "
        "site's buttons clearly show an arrow/icon — do not invent arrows.\n"
    )
    user_prompt = (
        f"{scaffold_summary}\n"
        f"{chrome_rules}"
        f"{theme_excerpt}"
        f"{chrome_summary + chr(10) if chrome_summary else ''}"
        f"{brand_summary + chr(10) if brand_summary else ''}"
        f"Here is the {generation_label} to implement:\n\n{generation_markdown}"
    )

    if provider_name == "claude":
        provider = AnthropicProvider("claude-opus-4-8")
        result = provider.text_query(
            system_prompt=prompt,
            user_prompt=user_prompt,
            max_tokens=FRAMEWORK_GEN_MAX_TOKENS,
        )
    elif provider_name == "gpt55":
        provider = OpenAIProvider("gpt-5.5")
        result = provider.text_query(
            system_prompt=prompt,
            user_prompt=user_prompt,
            max_tokens=FRAMEWORK_GEN_MAX_TOKENS,
        )
    else:
        raise ValueError(f"Unknown framework provider: {provider_name}")

    payload = extract_json_payload(result)
    files = payload.get("files")
    if not isinstance(files, dict) or not files:
        raise ValueError("Framework generation JSON missing non-empty 'files' object")

    written: list[str] = []
    for rel_path, contents in files.items():
        rel = str(rel_path).strip().lstrip("/")
        if not rel or ".." in Path(rel).parts:
            raise ValueError(f"Unsafe framework file path: {rel_path!r}")
        if not rel.startswith(("src/", "tokens/")):
            raise ValueError(f"Framework generation may only write src/ or tokens/ files: {rel}")
        dest = framework_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(str(contents).strip() + "\n", encoding="utf-8")
        written.append(rel)

    if "src/App.tsx" not in written:
        raise ValueError("Framework generation must include src/App.tsx")

    if "src/index.css" in written:
        merge_scaffold_index_css_layers(framework_dir / "src" / "index.css")
        sync_index_css_theme_from_design_system(
            framework_dir / "src" / "index.css",
            generation_markdown,
        )

    return {"written": written, "notes": payload.get("notes", "")}


def npm_install_if_needed(framework_dir: Path, log=print) -> None:
    if (framework_dir / "node_modules").is_dir():
        return
    log(f"  framework — npm ci in {framework_dir.name}/")
    subprocess.run(
        ["npm", "ci"],
        cwd=str(framework_dir),
        check=True,
        capture_output=True,
        text=True,
    )


def build_framework_project(framework_dir: Path, *, log=print) -> Path:
    """Run npm ci (if needed) + vite singlefile build; return dist/index.html."""
    npm_install_if_needed(framework_dir, log=log)
    # LLM-generated App.tsx often has minor TS issues; skip tsc for the pipeline artifact.
    log(f"  framework — npm run build:nocheck in {framework_dir.name}/")
    proc = subprocess.run(
        ["npm", "run", "build:nocheck"],
        cwd=str(framework_dir),
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            "Framework build failed:\n"
            + (proc.stderr or proc.stdout or "")[-4000:]
        )
    dist_html = framework_dir / "dist" / "index.html"
    if not dist_html.exists():
        raise FileNotFoundError(f"Framework build did not produce {dist_html}")
    return dist_html


def generate_framework_site(
    *,
    generation_markdown: str,
    provider_name: str,
    single_dir: Path,
    output_html_path: Path,
    framework_prompt: str | None = None,
    brand_assets_manifest: Path | None = None,
    chrome_contract_path: Path | None = None,
    generation_label: str = "design system",
    log=print,
) -> dict[str, Any]:
    """Full framework path: scaffold → tokens → LLM → build → copy single-file HTML."""
    framework_dir = single_dir / f"framework-{provider_name}"
    scaffold_framework_project(
        framework_dir,
        brand_assets_manifest=brand_assets_manifest,
    )
    tokens = apply_tokens_from_design_system(framework_dir, generation_markdown)
    # Prefer the richer browser-extracted v2 contract; fall back to static v1.
    chrome_contract = load_chrome_contract_v2(chrome_contract_path) or load_chrome_contract(
        chrome_contract_path
    )
    chrome_written: list[str] = []
    if chrome_contract and (
        (chrome_contract.get("nav") or {}).get("found")
        or (chrome_contract.get("footer") or {}).get("found")
    ):
        chrome_written = write_chrome_components(framework_dir, chrome_contract)
        log(f"  framework — source chrome: {', '.join(chrome_written)}")
    gen_meta = generate_framework_files(
        generation_markdown,
        provider_name,
        framework_dir,
        framework_prompt=framework_prompt,
        generation_label=generation_label,
        brand_assets_manifest=brand_assets_manifest,
        chrome_contract=chrome_contract,
    )
    dist_html = build_framework_project(framework_dir, log=log)
    shutil.copy2(dist_html, output_html_path)

    report = {
        "status": "completed",
        "framework_dir": str(framework_dir),
        "output_html": str(output_html_path),
        "tokens_synced": bool(tokens),
        "files_written": gen_meta.get("written", []),
        "chrome_files": chrome_written,
        "chrome_contract": str(chrome_contract_path) if chrome_contract_path else "",
        "notes": gen_meta.get("notes", ""),
    }
    output_html_path.with_suffix(".framework.json").write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    return report
