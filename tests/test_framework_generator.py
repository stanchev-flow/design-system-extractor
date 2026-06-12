"""Tests for framework site generation helpers (no LLM calls)."""

from pathlib import Path

from screenshot_to_template.framework_generator import (
    apply_tokens_from_design_system,
    build_v1_theme_block,
    design_system_to_dtcg_tokens,
    merge_scaffold_index_css_layers,
    parse_design_system_front_matter,
    scaffold_framework_project,
    sync_index_css_theme_from_design_system,
)

SAMPLE_DS = """---
schema_version: design_system_yaml.v1
tokens:
  color:
    surface:
      primary: '#ffffff'
      secondary: '#cfe9de'
      inverse: '#19392b'
    text:
      primary: '#1b3a2c'
      muted: '#4a5a50'
      onInverse: '#f2f6f2'
    border:
      divider: '#c9d4cc'
    accent:
      primary: '#1e7a4d'
  radius:
    media: 8px
    pill: 999px
---
# Design System
Body content here.
"""


def test_parse_design_system_front_matter():
    fm = parse_design_system_front_matter(SAMPLE_DS)
    assert fm.get("schema_version") == "design_system_yaml.v1"
    assert fm["tokens"]["color"]["surface"]["primary"] == "#ffffff"


def test_parse_design_system_front_matter_embedded_in_site_generation_input():
    wrapped = "# Site Generation Input\n\n## Source Design System\n\n" + SAMPLE_DS
    fm = parse_design_system_front_matter(wrapped)
    assert fm.get("schema_version") == "design_system_yaml.v1"
    assert fm["tokens"]["color"]["surface"]["secondary"] == "#cfe9de"


def test_design_system_to_dtcg_tokens():
    fm = parse_design_system_front_matter(SAMPLE_DS)
    dtcg = design_system_to_dtcg_tokens(fm)
    assert dtcg["color"]["surface"]["primary"]["$value"] == "#ffffff"
    assert dtcg["color"]["surface"]["secondary"]["$value"] == "#cfe9de"
    assert dtcg["color"]["accent"]["primary"]["$value"] == "#1e7a4d"


def test_scaffold_and_token_sync(tmp_path: Path):
    scaffold_root = Path(__file__).resolve().parents[1] / "handoff" / "scaffold" / "framework-site"
    if not scaffold_root.exists():
        return  # skip when scaffold not checked out

    framework_dir = tmp_path / "framework"
    scaffold_framework_project(framework_dir, scaffold_dir=scaffold_root)
    assert (framework_dir / "package.json").exists()
    assert (framework_dir / "src" / "App.tsx").exists()

    apply_tokens_from_design_system(framework_dir, SAMPLE_DS)
    tokens_path = framework_dir / "tokens" / "tokens.json"
    assert tokens_path.exists()
    css = (framework_dir / "src" / "index.css").read_text()
    assert "--color-surface-primary: #ffffff" in css
    assert "--color-surface-secondary: #cfe9de" in css
    assert "--color-accent-primary: #1e7a4d" in css
    assert "@layer components" in css

    theme = build_v1_theme_block(parse_design_system_front_matter(SAMPLE_DS))
    assert "--color-surface-secondary: #cfe9de" in theme


def test_merge_scaffold_layers_after_llm_strip(tmp_path: Path):
    scaffold_root = Path(__file__).resolve().parents[1] / "handoff" / "scaffold" / "framework-site"
    if not scaffold_root.exists():
        return
    framework_dir = tmp_path / "fw"
    scaffold_framework_project(framework_dir, scaffold_dir=scaffold_root)
    index_css = framework_dir / "src" / "index.css"
    index_css.write_text('@import "tailwindcss";\n\n@theme { --color-surface-primary: #fff; }\n', encoding="utf-8")
    assert merge_scaffold_index_css_layers(index_css, scaffold_dir=scaffold_root)
    merged = index_css.read_text()
    assert "@layer components" in merged
    assert ".btn[data-variant=" in merged
