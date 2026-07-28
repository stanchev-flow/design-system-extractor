"""Tests for framework site generation helpers (no LLM calls)."""

import json
import re
from pathlib import Path

from screenshot_to_template.framework_generator import (
    DEFAULT_SCAFFOLD_DIR,
    NEUTRAL_FONT_STACK,
    apply_tokens_from_design_system,
    build_v1_theme_block,
    design_system_to_dtcg_tokens,
    merge_scaffold_index_css_layers,
    parse_design_system_front_matter,
    resolve_scaffold_brand_name,
    resolve_scaffold_typography,
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


def _title(framework_dir: Path) -> str:
    match = re.search(r"<title>(.*?)</title>",
                      (framework_dir / "index.html").read_text(), re.DOTALL)
    return match.group(1) if match else ""


def test_checked_in_scaffold_carries_no_brand_identity():
    """The scaffold's own defaults must not read as a real brand.

    A previous scaffold shipped a past brand's page title and npm package name, so
    every generated app inherited that brand's identity when nothing overwrote it.
    A neutral default is wrong-but-harmless; a stale brand name is a leak."""
    pkg = json.loads((DEFAULT_SCAFFOLD_DIR / "package.json").read_text())
    lock = json.loads((DEFAULT_SCAFFOLD_DIR / "package-lock.json").read_text())
    assert pkg["name"] == "design-system-scaffold"
    # package.json and the committed lock must agree or `npm ci` refuses to run.
    assert lock["name"] == pkg["name"]
    assert lock["packages"][""]["name"] == pkg["name"]
    assert _title(DEFAULT_SCAFFOLD_DIR) == "Design system scaffold"


def test_scaffold_stamps_brand_title_from_asset_manifest(tmp_path: Path):
    manifest = tmp_path / "brand-assets.json"
    manifest.write_text(json.dumps({"brand": {"name": "WoodWave Gallery"}}))
    framework_dir = tmp_path / "fw"
    scaffold_framework_project(framework_dir, brand_assets_manifest=manifest)
    assert _title(framework_dir) == "WoodWave Gallery — design system"


def test_scaffold_stamps_brand_title_from_lane_brand_yaml(tmp_path: Path):
    lane = tmp_path / "lane"
    lane.mkdir()
    (lane / "brand.yaml").write_text('brand:\n  name: "Greenhouse"\n')
    framework_dir = tmp_path / "fw"
    scaffold_framework_project(framework_dir, brand_dir=lane)
    assert _title(framework_dir) == "Greenhouse — design system"


def test_scaffold_without_brand_facts_keeps_neutral_title(tmp_path: Path):
    framework_dir = tmp_path / "fw"
    scaffold_framework_project(framework_dir)
    assert _title(framework_dir) == "Design system scaffold"
    assert resolve_scaffold_brand_name(None, tmp_path / "missing") == ""


# ── typography: the scaffold must not hand a generated app a foreign typeface ──

BRAND_YAML_WITH_TYPE = """
brand:
  name: Fixture Brand
tokens:
  type:
    display-hero:
      family: "'Fixture Serif', Georgia, serif"
      sizeRem: {base: 4}
    body:
      family: "'Fixture Sans', Arial, sans-serif"
      sizeRem: {base: 1}
"""


def _index_css(framework_dir: Path) -> str:
    return (framework_dir / "src" / "index.css").read_text()


def test_checked_in_scaffold_names_no_typeface_and_no_width_axis():
    """The scaffold's own typography defaults must be inert.

    A hardcoded family lets a generated app render — and a hardcoded webfont link
    lets it LOAD — a typeface its brand does not use, and an unconditional
    font-stretch narrows every generated app to one past brand's width axis. Both
    read as correct output, which is what makes them expensive."""
    css = (DEFAULT_SCAFFOLD_DIR / "src" / "index.css").read_text()
    html = (DEFAULT_SCAFFOLD_DIR / "index.html").read_text()
    # Only OS-supplied faces and CSS generics may appear: every member has to be
    # something any machine already has, so nothing here can be a brand's typeface.
    system_only = {"ui-sans-serif", "system-ui", "-apple-system", "segoe ui", "roboto",
                   "helvetica neue", "arial", "sans-serif"}
    heading = re.search(r"--font-heading:([^;]*);", css).group(1)
    body = re.search(r"--font-body:([^;]*);", css).group(1)
    for stack in (heading, body):
        members = [m.strip().strip("\"'").lower() for m in stack.split(",")]
        assert members[0] == "ui-sans-serif", f"scaffold leads with {members[0]!r}"
        assert not set(members) - system_only, f"named typeface in {stack!r}"
    # every width axis is a token reference defaulting to normal, never a constant
    for value in re.findall(r"font-stretch:([^;]*);", css):
        assert "var(--font-stretch-" in value, f"hardcoded width axis: {value!r}"
    assert re.search(r"--font-stretch-(heading|body):\s*normal;", css)
    assert "fonts.googleapis.com/css2" not in html, "scaffold ships a hardcoded webfont"


def test_scaffold_derives_family_and_webfont_link_from_brand_facts(tmp_path: Path):
    lane = tmp_path / "lane"
    lane.mkdir()
    (lane / "brand.yaml").write_text(BRAND_YAML_WITH_TYPE)
    framework_dir = tmp_path / "fw"
    scaffold_framework_project(framework_dir, brand_dir=lane)

    css = _index_css(framework_dir)
    assert "'Fixture Serif'" in re.search(r"--font-heading:([^;]*);", css).group(1)
    assert "'Fixture Sans'" in re.search(r"--font-body:([^;]*);", css).group(1)
    # neither face is self-hosted, so each carries a loadable substitute AND the link
    # that delivers it — a declared family with no delivery is the defect being closed.
    html = (framework_dir / "index.html").read_text()
    assert "fonts.googleapis.com/css2" in html
    assert "Source+Serif+4" in html and "Lexend+Deca" in html


def test_scaffold_typography_survives_token_sync(tmp_path: Path):
    """Token sync rewrites the whole @theme from the run's design-system YAML, which
    need not carry a family at all. The brand-derived stacks must survive it."""
    lane = tmp_path / "lane"
    lane.mkdir()
    (lane / "brand.yaml").write_text(BRAND_YAML_WITH_TYPE)
    framework_dir = tmp_path / "fw"
    scaffold_framework_project(framework_dir, brand_dir=lane)
    apply_tokens_from_design_system(framework_dir, SAMPLE_DS)
    css = _index_css(framework_dir)
    assert "'Fixture Serif'" in css and "'Fixture Sans'" in css
    assert "--font-stretch-heading: normal;" in css


def test_scaffold_with_self_hosted_face_loads_no_substitute(tmp_path: Path):
    lane = tmp_path / "lane"
    (lane / "assets" / "fonts").mkdir(parents=True)
    (lane / "assets" / "fonts" / "FixtureSerif-Regular.woff2").write_bytes(b"x")
    (lane / "brand.yaml").write_text(BRAND_YAML_WITH_TYPE + """
selfHostedFonts:
  - family: Fixture Serif
    faces:
      - weight: 400
        files: [FixtureSerif-Regular.woff2]
""")
    typography = resolve_scaffold_typography(None, lane)
    assert typography["heading"] == "'Fixture Serif', Georgia, serif"
    assert "Source+Serif+4" not in typography["webfontLink"]


def test_scaffold_without_brand_facts_keeps_a_neutral_stack(tmp_path: Path):
    framework_dir = tmp_path / "fw"
    scaffold_framework_project(framework_dir)
    css = _index_css(framework_dir)
    assert NEUTRAL_FONT_STACK.split(",")[0] in css
    assert "fonts.googleapis.com" not in (framework_dir / "index.html").read_text()
    neutral = resolve_scaffold_typography(None, tmp_path / "missing")
    assert neutral["heading"] == NEUTRAL_FONT_STACK
    assert neutral["webfontLink"] == ""


def test_width_axis_is_derived_per_role_not_assumed(tmp_path: Path):
    lane = tmp_path / "lane"
    lane.mkdir()
    (lane / "brand.yaml").write_text(BRAND_YAML_WITH_TYPE.replace(
        '      family: "\'Fixture Sans\', Arial, sans-serif"',
        '      family: "\'Fixture Sans\', Arial, sans-serif"\n      fontStretch: "87.5%"'))
    framework_dir = tmp_path / "fw"
    scaffold_framework_project(framework_dir, brand_dir=lane)
    css = _index_css(framework_dir)
    assert "--font-stretch-body: 87.5%;" in css
    # the role that measured no axis stays at normal rather than inheriting the other's
    assert "--font-stretch-heading: normal;" in css


def test_design_system_font_default_is_not_a_named_typeface():
    dtcg = design_system_to_dtcg_tokens({"tokens": {}})
    for role in ("heading", "body"):
        assert dtcg["font"][role]["$value"] == ["ui-sans-serif", "system-ui", "sans-serif"]
