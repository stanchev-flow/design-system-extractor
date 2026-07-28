#!/usr/bin/env python3
"""Opt-in Greenhouse 4 framework lane: token skin from brand.md, no shadcn defaults."""
from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))


def _load_env_local() -> None:
    env_path = ROOT / ".env.local"
    if not env_path.is_file():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip("'\"")
        if key and value and not os.environ.get(key):
            os.environ[key] = value


_load_env_local()

from screenshot_to_template.framework_generator import (  # noqa: E402
    generate_framework_site,
    load_framework_prompt,
)

BRAND = ROOT / "runs" / "greenhouse-4" / "brand"
PAGE = "home"
OUT = BRAND / "framework"
SINGLE = OUT / "single"
REGISTRY = ROOT / "runs" / ".studio" / "framework-builds.json"


def build_measured_asset_bundle() -> Path:
    """media-assets.yaml (+ measured placements) → the app's brand-assets.json."""
    sys.path.insert(0, str(ROOT / "tools"))
    from build_brand_assets import default_assets_prefix, from_brand_registry

    out = BRAND / "framework" / "brand-assets.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    bundle = from_brand_registry(BRAND, default_assets_prefix(BRAND))
    out.write_text(json.dumps(bundle, indent=2) + "\n")
    print(f"measured asset bundle: {len(bundle['assets'])} assets, "
          f"{len(bundle['bySection'])} bound sections -> {out}")
    return out


def main() -> int:
    md_path = BRAND / "brand.md"
    yaml_path = BRAND / "brand.yaml"
    if md_path.exists() and md_path.stat().st_size > 100:
        md = md_path.read_text()
    elif yaml_path.exists():
        md = "# Greenhouse\n\n```yaml\n" + yaml_path.read_text()[:100000] + "\n```\n"
    else:
        raise SystemExit("brand.md/brand.yaml missing — finish author stage first")

    # brand.yaml is the UNION of three captured pages. The framework target is
    # the homepage, so hand the generator that page's lane; the union alone is
    # how the other pages' bands (stats, testimonials) end up on it.
    sys.path.insert(0, str(ROOT / "tools"))
    from page_lane_brief import build_brief

    lane = build_brief(BRAND, PAGE)
    if lane:
        md += "\n\n" + lane
        print(f"page lane: {PAGE} inventory appended to the generation brief")

    # No live-URL chrome contract was captured for this brand, so the measured
    # chrome facts are the only source for the nav and footer. Without them the
    # generator invents links.
    chrome_facts = BRAND / "brand-chrome.yaml"
    if chrome_facts.is_file():
        md += ("\n\n## Measured chrome (verbatim facts — do not invent links)\n\n"
               "```yaml\n" + chrome_facts.read_text() + "\n```\n")

    SINGLE.mkdir(parents=True, exist_ok=True)
    out_html = SINGLE / "site-claude-framework.html"
    prompt = load_framework_prompt(ROOT / "website-gen-framework-prompt.md")
    # The MEASURED bundle (section bindings + geometric roles), not the raw
    # curation manifest — the generator can only bind assets to the bands they
    # came from if the bundle carries that binding.
    manifest = build_measured_asset_bundle()
    chrome = BRAND / "assets" / "source-chrome.v2.json"
    if not chrome.exists():
        chrome = BRAND / "assets" / "source-chrome.json"
    report = generate_framework_site(
        generation_markdown=md,
        provider_name="claude",
        single_dir=SINGLE,
        output_html_path=out_html,
        framework_prompt=prompt,
        brand_assets_manifest=manifest if manifest.exists() else None,
        chrome_contract_path=chrome if chrome.exists() else None,
        generation_label="Greenhouse brand.md tokens",
        log=print,
    )
    # Stable Studio URL
    OUT.mkdir(parents=True, exist_ok=True)
    shutil.copy2(out_html, OUT / "index.html")
    (OUT / "framework-report.json").write_text(json.dumps(report, indent=2) + "\n")
    print("framework page:", OUT / "index.html")

    # Register as external-or-static lane helper note in framework-builds
    # Studio serves runs/** statically, so we also rely on compose/harness discovery;
    # add an entry pointing at the runs-served HTML for convenience.
    try:
        data = json.loads(REGISTRY.read_text()) if REGISTRY.exists() else []
        if not isinstance(data, list):
            data = []
        url = "/runs/greenhouse-4/brand/framework/index.html"
        data = [e for e in data if not (isinstance(e, dict) and e.get("version") == "greenhouse-4"
                                        and "framework" in str(e.get("label", "")).lower())]
        data.append({
            "version": "greenhouse-4",
            "label": "Framework (token skin)",
            "url": f"http://127.0.0.1:1500{url}",
        })
        REGISTRY.parent.mkdir(parents=True, exist_ok=True)
        REGISTRY.write_text(json.dumps(data, indent=2) + "\n")
        print("registered studio framework-builds entry")
    except Exception as exc:
        print("registry update skipped:", exc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
