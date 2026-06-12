#!/usr/bin/env python3
"""Brand-to-Webflow agent pipeline.

Turns an existing extraction run (design-system.md + screenshot + harvested
assets + chrome contract) into the artifact set the Webflow MCP assembler
consumes:

    runs/{version}/brand/
      webflow-variables.json   deterministic token bridge (no LLM)
      brand.md                 art director — the brand "digital twin"
      voice.md                 copywriter — tone + per-section copy
      assets.md                graphic designer — slot map for real imagery
      build.md                 assembler — per-section Webflow build plan

Each step reads only upstream artifacts, so steps can be re-run independently:

    ./venv/bin/python run_brand_pipeline.py --version woodwave
    ./venv/bin/python run_brand_pipeline.py --version woodwave --steps brand,voice --force
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_DIR / "src"))

from screenshot_to_template.framework_generator import (  # noqa: E402
    parse_design_system_front_matter,
)
from screenshot_to_template.models.anthropic import AnthropicProvider  # noqa: E402
from screenshot_to_template.pipeline.single_shot import (  # noqa: E402
    load_and_encode_image,
)

PROMPTS_DIR = PROJECT_DIR / "brand_pipeline" / "prompts"
INVENTORY_PATH = PROJECT_DIR / "brand_pipeline" / "inventory.md"
RUNS_DIR = PROJECT_DIR / "runs"

ALL_STEPS = ("variables", "brand", "voice", "assets", "build")


def load_api_keys() -> None:
    env_path = PROJECT_DIR / ".env.local"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip("'\"")
        if key and value and not os.environ.get(key):
            os.environ[key] = value


# ── input discovery ───────────────────────────────────────────────────────────
def find_item_dir(version_dir: Path) -> Path:
    """First item dir that carries a design system (runs/{v}/{item}/single/)."""
    for child in sorted(version_dir.iterdir()):
        if child.is_dir() and (child / "single" / "design-system.md").exists():
            return child
    raise FileNotFoundError(f"No item with single/design-system.md under {version_dir}")


def find_screenshot(item_dir: Path) -> Path:
    for ext in (".png", ".webp", ".jpg", ".jpeg"):
        p = item_dir / f"screenshot{ext}"
        if p.exists():
            return p
    raise FileNotFoundError(f"No screenshot.* in {item_dir}")


# ── step 1: deterministic token bridge ────────────────────────────────────────
def _kebab(name: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "-", str(name)).lower()


def _px_to_rem(value: str) -> str | None:
    m = re.match(r"^\s*([\d.]+)\s*px\s*$", str(value))
    if not m:
        return None
    return f"{float(m.group(1)) / 16:g}rem"


def build_webflow_variables(front_matter: dict, host: str) -> dict:
    """Project design-system tokens onto a Webflow variable tree.

    Every variable is marked mode="proposed"; the MCP executor maps onto the
    site's existing variables first and only creates the leftovers.
    """
    tokens = front_matter.get("tokens") or {}
    variables: list[dict] = []

    def add(group: str, name: str, vtype: str, value, source: str) -> None:
        if value in (None, ""):
            return
        variables.append(
            {
                "name": f"{group}/{_kebab(name)}",
                "type": vtype,
                "value": str(value),
                "source": source,
                "mode": "proposed",
            }
        )

    color = tokens.get("color") or {}
    for group_key, group in color.items():
        if not isinstance(group, dict):
            continue
        for name, value in group.items():
            add(_kebab(group_key), name, "color", value, f"tokens.color.{group_key}.{name}")

    for name, value in (tokens.get("spacing") or {}).items():
        rem = _px_to_rem(value)
        add("space", name, "size", rem or value, f"tokens.spacing.{name}")

    typography = front_matter.get("typography") or {}
    for role, node in typography.items():
        if not isinstance(node, dict):
            continue
        size = node.get("fontSize")
        if size:
            rem = _px_to_rem(size)
            add("type", f"{role}-size", "size", rem or size, f"typography.{role}.fontSize")
        if node.get("lineHeight"):
            add("type", f"{role}-leading", "number", node["lineHeight"], f"typography.{role}.lineHeight")
        if node.get("fontFamily"):
            add("type", f"{role}-family", "font-family", node["fontFamily"], f"typography.{role}.fontFamily")

    for name, value in (tokens.get("radius") or {}).items():
        rem = _px_to_rem(value)
        add("radius", name, "size", rem or value, f"tokens.radius.{name}")

    return {
        "schemaVersion": 1,
        "collection": f"Brand/{host}",
        "strategy": "map-then-extend",
        "note": (
            "Executor: for each variable, first try to map onto an existing "
            "site variable by role-name similarity; create it only on miss."
        ),
        "variables": variables,
    }


def variables_markdown_table(bundle: dict) -> str:
    lines = ["| variable | type | value |", "|---|---|---|"]
    for v in bundle["variables"]:
        lines.append(f"| `{v['name']}` | {v['type']} | `{v['value']}` |")
    return "\n".join(lines)


# ── LLM steps ─────────────────────────────────────────────────────────────────
def read_prompt(name: str) -> str:
    return (PROMPTS_DIR / name).read_text(encoding="utf-8").strip()


def compact_asset_manifest(assets_path: Path) -> str:
    """Slim brand-assets.json down to what the asset director needs."""
    data = json.loads(assets_path.read_text())
    out = []
    for role, items in (data.get("byRole") or {}).items():
        for a in items:
            out.append(
                {
                    "id": a.get("id"),
                    "role": role,
                    "type": a.get("type"),
                    "label": a.get("label"),
                    "url": a.get("url") or a.get("displayUrl"),
                }
            )
    return json.dumps(out, indent=1)


def main() -> None:
    ap = argparse.ArgumentParser(description="Brand-to-Webflow agent pipeline")
    ap.add_argument("--version", required=True, help="Existing run version (e.g. woodwave)")
    ap.add_argument("--brief", help="Path to project brief md (default: runs/{v}/brand/brief.md)")
    ap.add_argument("--model", default="claude-fable-5")
    ap.add_argument("--reasoning-effort", default="high")
    ap.add_argument("--steps", default="all", help=f"csv of {','.join(ALL_STEPS)} or 'all'")
    ap.add_argument("--force", action="store_true", help="Re-run steps whose output exists")
    args = ap.parse_args()

    load_api_keys()

    version_dir = RUNS_DIR / args.version
    if not version_dir.exists():
        raise SystemExit(f"Run not found: {version_dir}")
    item_dir = find_item_dir(version_dir)
    single_dir = item_dir / "single"
    out_dir = version_dir / "brand"
    out_dir.mkdir(parents=True, exist_ok=True)

    design_md = (single_dir / "design-system.md").read_text(encoding="utf-8")
    front_matter = parse_design_system_front_matter(design_md)
    if not front_matter:
        raise SystemExit("design-system.md has no parseable front matter")

    meta = {}
    meta_path = version_dir / "studio-project.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text())
    host = re.sub(r"^https?://", "", str(meta.get("url") or args.version)).strip("/")

    brief_path = Path(args.brief) if args.brief else out_dir / "brief.md"
    brief = brief_path.read_text(encoding="utf-8").strip() if brief_path.exists() else ""
    if not brief:
        print(f"[warn] no brief at {brief_path} — copy/build steps fall back to a generic landing brief")
        brief = "Single landing page that represents the brand faithfully: hero, 3-5 editorial sections, contact/visit info, newsletter, footer."

    steps = ALL_STEPS if args.steps == "all" else tuple(s.strip() for s in args.steps.split(","))
    for s in steps:
        if s not in ALL_STEPS:
            raise SystemExit(f"Unknown step: {s} (valid: {ALL_STEPS})")

    def should_run(step: str, output: Path) -> bool:
        if step not in steps:
            return False
        if output.exists() and not args.force:
            print(f"[skip] {step}: {output.name} exists (use --force to redo)")
            return False
        return True

    provider = AnthropicProvider(args.model, reasoning_effort=args.reasoning_effort)
    print(f"Brand pipeline: {args.version} ({host})")
    print(f"Model: {args.model} (reasoning={args.reasoning_effort})")
    print(f"Inputs: {single_dir.relative_to(PROJECT_DIR)}")
    print(f"Output: {out_dir.relative_to(PROJECT_DIR)}")
    print()

    # 1) variables — deterministic
    variables_path = out_dir / "webflow-variables.json"
    if should_run("variables", variables_path):
        bundle = build_webflow_variables(front_matter, host)
        variables_path.write_text(json.dumps(bundle, indent=2) + "\n", encoding="utf-8")
        print(f"[done] variables: {len(bundle['variables'])} proposed → {variables_path.name}")
    variables_table = (
        variables_markdown_table(json.loads(variables_path.read_text()))
        if variables_path.exists()
        else ""
    )

    # 2) brand.md — art director (vision)
    brand_path = out_dir / "brand.md"
    if should_run("brand", brand_path):
        screenshot = find_screenshot(item_dir)
        print(f"[run ] brand: art director on {screenshot.name} ...")
        image_b64 = load_and_encode_image(str(screenshot), max_dimension=7800)
        user = (
            f"Host: {host}\n\n## Webflow variables (reference these names)\n\n"
            f"{variables_table}\n\n## Design-system extraction\n\n{design_md}"
        )
        result = provider.analyze_image(
            image_b64,
            system_prompt=read_prompt("art-director-prompt.md"),
            user_prompt=user,
            max_tokens=16384,
        )
        brand_path.write_text(result.strip() + "\n", encoding="utf-8")
        print(f"[done] brand.md ({len(result)} chars)")
    brand_md = brand_path.read_text(encoding="utf-8") if brand_path.exists() else ""

    # 3) voice.md — copywriter
    voice_path = out_dir / "voice.md"
    if should_run("voice", voice_path):
        print("[run ] voice: copywriter ...")
        user = f"## brand.md\n\n{brand_md}\n\n## Project brief\n\n{brief}"
        result = provider.text_query(
            system_prompt=read_prompt("copywriter-prompt.md"),
            user_prompt=user,
            max_tokens=8192,
        )
        voice_path.write_text(result.strip() + "\n", encoding="utf-8")
        print(f"[done] voice.md ({len(result)} chars)")
    voice_md = voice_path.read_text(encoding="utf-8") if voice_path.exists() else ""

    # 4) assets.md — graphic designer
    assets_out_path = out_dir / "assets.md"
    if should_run("assets", assets_out_path):
        manifest_path = version_dir / "assets" / "brand-assets.json"
        if not manifest_path.exists():
            print(f"[warn] assets: no manifest at {manifest_path}, skipping")
        else:
            print("[run ] assets: asset director ...")
            user = (
                f"## Asset manifest\n\n```json\n{compact_asset_manifest(manifest_path)}\n```\n\n"
                f"## brand.md (imagery direction + layout grammar)\n\n{brand_md}\n\n"
                f"## Project brief\n\n{brief}"
            )
            result = provider.text_query(
                system_prompt=read_prompt("asset-director-prompt.md"),
                user_prompt=user,
                max_tokens=8192,
            )
            assets_out_path.write_text(result.strip() + "\n", encoding="utf-8")
            print(f"[done] assets.md ({len(result)} chars)")
    assets_md = assets_out_path.read_text(encoding="utf-8") if assets_out_path.exists() else ""

    # 5) build.md — assembler plan
    build_path = out_dir / "build.md"
    if should_run("build", build_path):
        chrome = ""
        for name in ("source-chrome.v2.json", "source-chrome.json"):
            p = version_dir / "assets" / name
            if p.exists():
                chrome = p.read_text(encoding="utf-8")
                break
        inventory = INVENTORY_PATH.read_text(encoding="utf-8") if INVENTORY_PATH.exists() else ""
        print("[run ] build: assembler ...")
        user = (
            f"## Available inventory\n\n{inventory}\n\n"
            f"## Webflow variables\n\n{variables_table}\n\n"
            f"## brand.md\n\n{brand_md}\n\n"
            f"## voice.md\n\n{voice_md}\n\n"
            f"## assets.md\n\n{assets_md}\n\n"
            f"## Chrome contract\n\n```json\n{chrome}\n```\n\n"
            f"## Project brief\n\n{brief}"
        )
        result = provider.text_query(
            system_prompt=read_prompt("webflow-build-prompt.md"),
            user_prompt=user,
            max_tokens=30000,
        )
        build_path.write_text(result.strip() + "\n", encoding="utf-8")
        print(f"[done] build.md ({len(result)} chars)")

    print()
    print("Artifacts:")
    for p in sorted(out_dir.iterdir()):
        print(f"  {p.relative_to(PROJECT_DIR)} ({p.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
