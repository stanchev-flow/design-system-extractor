#!/usr/bin/env python3
"""ground_sections_vision.py — per-section VISION grounding for brand extraction.

Sends each section crop (slice_sections.py output) to the existing Anthropic
vision provider (src/screenshot_to_template/models/anthropic.py — analyze_image)
with the versioned factual-inventory prompt
(brand_pipeline/spec/extraction-grounding-prompt.md) and writes one
``section-grounding.v1`` YAML evidence file per crop into --out-dir.

This is the scripted vision pass the original Remote extraction lacked: the
grounding YAMLs are the evidence the extraction agent authors brand.yaml /
section-copy.yaml / layout-library.yaml from, and validate_brand_evidence.py
requires them.

Auth: ANTHROPIC_API_KEY from the environment, or repo-local .env.local
(KEY=VALUE lines — same convention as run_brand_pipeline.load_api_keys). The key
is never printed or written to any artifact.

Usage:
    ./venv/bin/python tools/extract/ground_sections_vision.py \
        --crops-dir runs/<brand>/brand/evidence/crops/ \
        --out-dir runs/<brand>/brand/evidence/grounding/ [--limit 2] [--force]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_PROMPT = REPO_ROOT / "brand_pipeline" / "spec" / "extraction-grounding-prompt.md"
DEFAULT_MODEL = "claude-opus-4-8"
SCHEMA = "section-grounding.v1"

_FENCE_RE = re.compile(r"^\s*```(?:yaml|yml)?\s*\n(.*?)\n\s*```\s*$", re.S)


def load_api_keys() -> None:
    """Populate os.environ from repo-local .env.local (KEY=VALUE), never
    overriding already-set vars and never logging names or values."""
    env_path = REPO_ROOT / ".env.local"
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


def strip_fences(text: str) -> str:
    m = _FENCE_RE.match(text.strip())
    return m.group(1) if m else text.strip()


def collect_crops(crops_dir: Path | None, manifest_path: Path | None) -> list[dict]:
    """[{path, index, classes, heading}] from crops-manifest.json when present
    (carries DOM context), else a bare directory listing."""
    if manifest_path is None and crops_dir is not None:
        cand = crops_dir / "crops-manifest.json"
        manifest_path = cand if cand.is_file() else None
    if manifest_path is not None and manifest_path.is_file():
        doc = json.loads(manifest_path.read_text())
        base = manifest_path.parent
        return [{"path": base / c["file"], "index": c.get("index", i),
                 "classes": c.get("classes", ""), "heading": c.get("heading", "")}
                for i, c in enumerate(doc.get("crops") or [])]
    if crops_dir is None:
        raise SystemExit("provide --crops-dir or --crops-manifest")
    return [{"path": p, "index": i, "classes": "", "heading": ""}
            for i, p in enumerate(sorted(crops_dir.glob("*.png")))]


def build_user_prompt(crop: dict, total: int) -> str:
    ctx = [f"Section crop {crop['index'] + 1} of {total} (top-to-bottom page order)."]
    if crop.get("classes"):
        ctx.append(f"DOM wrapper classes for this section: {crop['classes']}")
    if crop.get("heading"):
        ctx.append(f"First DOM heading text in this section: {crop['heading']!r}")
    ctx.append(
        "Analyze the attached crop. Emit ONLY the section-grounding.v1 YAML "
        "document per the system prompt — no prose, no markdown fences.")
    return "\n".join(ctx)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--crops-dir", type=Path, help="dir of section-*.png crops")
    ap.add_argument("--crops-manifest", type=Path,
                    help="crops-manifest.json (preferred: carries DOM context)")
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--prompt-file", type=Path, default=DEFAULT_PROMPT)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--reasoning-effort", default="medium")
    ap.add_argument("--max-tokens", type=int, default=6000)
    ap.add_argument("--max-dimension", type=int, default=2200,
                    help="crop downscale ceiling before base64 (px)")
    ap.add_argument("--limit", type=int, default=0, help="ground only the first N crops")
    ap.add_argument("--force", action="store_true", help="re-ground crops with existing YAML")
    return ap


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    crops = collect_crops(args.crops_dir, args.crops_manifest)
    if args.limit:
        crops = crops[: args.limit]
    if not crops:
        raise SystemExit("no crops found — run slice_sections.py first")
    if not args.prompt_file.is_file():
        raise SystemExit(f"prompt file missing: {args.prompt_file}")
    system_prompt = args.prompt_file.read_text(encoding="utf-8")
    # spec files may carry a design-intent header above a bare `PROMPT` marker
    # line; only the text below the marker is the model-facing prompt.
    marker = re.search(r"^PROMPT\s*$", system_prompt, re.M)
    if marker:
        system_prompt = system_prompt[marker.end():].strip()

    load_api_keys()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY not available (set it in the environment "
                         "or repo-local .env.local) — vision grounding is blocked.")

    sys.path.insert(0, str(REPO_ROOT / "src"))
    import yaml
    from screenshot_to_template.models.anthropic import AnthropicProvider
    from screenshot_to_template.pipeline.single_shot import load_and_encode_image

    provider = AnthropicProvider(args.model, reasoning_effort=args.reasoning_effort)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    telemetry: list[dict] = []
    n_ok = n_err = n_skip = 0
    for crop in crops:
        stem = crop["path"].stem
        out_path = args.out_dir / f"{stem}.yaml"
        if out_path.exists() and not args.force:
            print(f"  [skip] {out_path.name} exists (--force to redo)")
            n_skip += 1
            continue
        print(f"  [run ] {crop['path'].name} ...")
        t0 = time.time()
        try:
            image_b64 = load_and_encode_image(str(crop["path"]), max_dimension=args.max_dimension)
            raw = provider.analyze_image(
                image_b64,
                system_prompt=system_prompt,
                user_prompt=build_user_prompt(crop, len(crops)),
                max_tokens=args.max_tokens)
        except Exception as exc:  # network/auth/API — record and continue
            telemetry.append({"crop": crop["path"].name, "error": type(exc).__name__,
                              "latency_s": round(time.time() - t0, 2)})
            print(f"  [fail] {crop['path'].name}: {type(exc).__name__}: {exc}")
            n_err += 1
            continue
        latency = round(time.time() - t0, 2)
        text = strip_fences(raw)
        try:
            parsed = yaml.safe_load(text)
            if not isinstance(parsed, dict):
                raise ValueError("top level is not a mapping")
        except Exception as exc:
            raw_path = args.out_dir / f"{stem}.raw.txt"
            raw_path.write_text(raw)
            telemetry.append({"crop": crop["path"].name, "latency_s": latency,
                              "error": f"yaml-parse: {exc}", "raw": raw_path.name})
            print(f"  [fail] {crop['path'].name}: response is not YAML "
                  f"(raw saved to {raw_path.name})")
            n_err += 1
            continue
        parsed.setdefault("schemaVersion", SCHEMA)
        parsed.setdefault("_source", {"crop": crop["path"].name,
                                      "domClasses": crop.get("classes", ""),
                                      "model": args.model})
        out_path.write_text(yaml.safe_dump(parsed, sort_keys=False,
                                           allow_unicode=True, width=100))
        usage = getattr(provider, "last_usage", {}) or {}
        telemetry.append({"crop": crop["path"].name, "latency_s": latency,
                          "input_tokens": usage.get("input_tokens"),
                          "output_tokens": usage.get("output_tokens"),
                          "out": out_path.name})
        print(f"  [done] {out_path.name}  ({latency}s)")
        n_ok += 1

    (args.out_dir / "grounding-run.json").write_text(json.dumps(
        {"schemaVersion": SCHEMA, "model": args.model,
         "promptFile": str(args.prompt_file), "runs": telemetry}, indent=1))
    print(f"[done] ground: {n_ok} grounded, {n_skip} skipped, {n_err} failed "
          f"-> {args.out_dir}")
    return 0 if (n_ok or n_skip) and not n_err else (1 if n_err else 0)


if __name__ == "__main__":
    sys.exit(main())
