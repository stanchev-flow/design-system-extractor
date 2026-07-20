#!/usr/bin/env python3
"""Executable, evidence-first authoring stage for brand extraction.

The stage turns a completed extraction bundle into canonical brand artifacts using
the repository's configured text-model provider. Candidate files are parsed as a
transaction before any member of a response group is installed. The C1-C28
validator then drives a bounded repair loop.
"""
from __future__ import annotations

import json
import os
import re
import signal
import sys
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import yaml

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
SPEC_DIR = HERE / "spec"
TOOLS_EXTRACT = REPO_ROOT / "tools" / "extract"
SRC_DIR = REPO_ROOT / "src"
for _path in (str(TOOLS_EXTRACT), str(SRC_DIR), str(HERE)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

DEFAULT_MODEL = "claude-opus-4-8"
DEFAULT_REASONING = "adaptive"
AUTHOR_REPORT = "author-report.json"

MODEL_OUTPUTS = (
    "brand.yaml",
    "layout-library.yaml",
    "section-copy.yaml",
    "assets-tagged.json",
    "media-assets.yaml",
    "voice-facts.yaml",
)
DERIVED_OUTPUTS = ("brand.md", "style-scale.yaml", "voice.md")
EXPECTED_OUTPUTS = MODEL_OUTPUTS + DERIVED_OUTPUTS
VALIDATION_PREREQUISITES = (
    "brand.yaml",
    "layout-library.yaml",
    "section-copy.yaml",
    "assets-tagged.json",
    "media-assets.yaml",
)
AUTHOR_GROUPS = (
    ("brand.yaml", "voice-facts.yaml"),
    ("brand-chrome.yaml", "section-copy.yaml"),
    ("layout-library.yaml",),
    ("media-guidance.yaml",),
)

_FENCE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.S)


class AuthorBlocked(RuntimeError):
    """A clear author-gate failure (provider, response, or validation)."""


@dataclass
class AuthorResult:
    ok: bool
    status: str
    reason: str = ""
    model: str = ""
    calls: int = 0
    repairs: int = 0
    skipped: bool = False
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    usage: dict = field(default_factory=dict)
    outputs: list[str] = field(default_factory=list)
    stages: list[dict] = field(default_factory=list)
    duration_s: float = 0.0

    def to_dict(self) -> dict:
        return {
            "schemaVersion": "brand-author.v1",
            "status": self.status,
            "ok": self.ok,
            "reason": self.reason,
            "model": self.model,
            "calls": self.calls,
            "repairs": self.repairs,
            "skipped": self.skipped,
            "usage": self.usage,
            "outputs": self.outputs,
            "stages": self.stages,
            "validation": {
                "checks": "C1-C28",
                "errors": self.errors,
                "warnings": self.warnings,
            },
            "durationS": round(self.duration_s, 3),
            "completedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }


def _read_capped(path: Path, cap: int) -> str:
    raw = path.read_text(encoding="utf-8", errors="replace")
    if len(raw) <= cap:
        return raw
    return raw[:cap] + f"\n\n[TRUNCATED after {cap} characters; source={path.name}]\n"


def build_input_bundle(brand_dir: Path, *, source_url: str | None = None,
                       per_file_cap: int = 180_000) -> dict:
    """Build the model's factual bundle without reading another lane's artifacts."""
    brand_dir = Path(brand_dir)
    evidence = brand_dir / "evidence"
    required = (
        evidence / "dom-sections.json",
        evidence / "css-facts.json",
        evidence / "computed-styles.json",
        evidence / "section-rects.json",
        evidence / "motion-audit.json",
        evidence / "crops" / "crops-manifest.json",
        brand_dir / "assets-manifest.json",
        brand_dir / "media-assets-draft.yaml",
    )
    missing = [str(p.relative_to(brand_dir)) for p in required if not p.is_file()]
    grounding = sorted((evidence / "grounding").glob("*.yaml"))
    if not grounding:
        missing.append("evidence/grounding/*.yaml")
    if missing:
        raise AuthorBlocked("author inputs incomplete — missing: " + ", ".join(missing))

    manifest = {}
    manifest_path = brand_dir / "manifest.json"
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text())
        except Exception:
            manifest = {}
    source_url = source_url or manifest.get("source_url")
    files = {}
    for path in required:
        files[str(path.relative_to(brand_dir))] = _read_capped(path, per_file_cap)
    for path in grounding:
        files[str(path.relative_to(brand_dir))] = _read_capped(path, per_file_cap)

    specs = {}
    for name in (
        "brand-schema.md",
        "section-copy-schema.md",
        "media-assets-schema.md",
        "layout-analyst-skill.md",
    ):
        path = SPEC_DIR / name
        specs[name] = _read_capped(path, per_file_cap)
    contracts = {}
    for name in ("blocks.yaml", "primitives.yaml"):
        path = HERE / "contracts" / name
        contracts[name] = _read_capped(path, per_file_cap)
    return {
        "lane": brand_dir.parent.name,
        "sourceUrl": source_url,
        "manifestMetadata": {
            k: manifest.get(k) for k in ("project", "brand", "source_url", "capture")
            if manifest.get(k) is not None
        },
        "evidence": files,
        "specs": specs,
        "contracts": contracts,
    }


def _system_prompt() -> str:
    return """You are the executable Layout Analyst in an evidence-first design-system
pipeline. Author canonical files only from the supplied lane's evidence. Never copy or
infer values from another brand. Exact measured facts beat visual estimates. Preserve
measured/extracted provenance; do not invent missing catalog components as measured
patterns (render-time designed-component synthesis owns those gaps).

Return ONLY JSON with this shape:
{"files":{"filename":"complete file contents", ...}}
Every requested filename must be present. YAML/JSON contents must parse. Use generic,
reusable role names, never section-specific token names. Copy must be verbatim from this
lane. Asset filenames must exist in this lane. media-assets.yaml must refine the supplied
draft and preserve measured stats. Attempt every shared block contract with extracted
evidence or explicit notObserved. Author measured recipes/chrome/media arrangements only
when evidenced. Do not emit markdown fences."""


def _user_prompt(bundle: dict, requested: tuple[str, ...], *,
                 validation_errors: list[str] | None = None,
                 current_files: dict[str, str] | None = None) -> str:
    task = {
        "requestedFiles": list(requested),
        "validationErrorsToRepair": validation_errors or [],
        "currentFiles": current_files or {},
        "inputBundle": bundle,
    }
    return (
        "Author the requested complete files. Cross-check all evidence streams and obey "
        "the embedded normative specs. For repairs, change only what the listed C1-C28 "
        "errors require while returning every requested file in full.\n\n"
        + json.dumps(task, ensure_ascii=False)
    )


def parse_model_files(raw: str, requested: tuple[str, ...]) -> dict[str, str]:
    """Parse and syntax-check a complete model response before any write."""
    match = _FENCE.match(raw)
    text = match.group(1) if match else raw.strip()
    try:
        doc = json.loads(text)
    except Exception as exc:
        raise AuthorBlocked(f"author response is not JSON: {exc}") from exc
    files = doc.get("files") if isinstance(doc, dict) else None
    if not isinstance(files, dict):
        raise AuthorBlocked("author response missing object key 'files'")
    missing = [name for name in requested if name not in files]
    if missing:
        raise AuthorBlocked("author response omitted requested files: " + ", ".join(missing))
    parsed: dict[str, str] = {}
    for name in requested:
        value = files[name]
        if not isinstance(value, str):
            if name.endswith(".json"):
                value = json.dumps(value, indent=2, ensure_ascii=False) + "\n"
            else:
                value = yaml.safe_dump(value, sort_keys=False, allow_unicode=True)
        if name.endswith(".json"):
            json.loads(value)
        elif name.endswith((".yaml", ".yml")):
            loaded = yaml.safe_load(value)
            if not isinstance(loaded, dict):
                raise AuthorBlocked(f"{name} must parse to a mapping")
        parsed[name] = value.rstrip() + "\n"
    return parsed


def atomic_write_group(brand_dir: Path, files: dict[str, str]) -> None:
    """Install a fully parsed response group; no partial response is ever written."""
    brand_dir = Path(brand_dir)
    brand_dir.mkdir(parents=True, exist_ok=True)
    staged: list[tuple[Path, Path]] = []
    try:
        for name, content in files.items():
            fd, tmp_name = tempfile.mkstemp(prefix=f".{name}.", suffix=".tmp",
                                            dir=brand_dir)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            staged.append((Path(tmp_name), brand_dir / name))
        for temp, target in staged:
            os.replace(temp, target)
    finally:
        for temp, _ in staged:
            if temp.exists():
                temp.unlink()


def _atomic_json(path: Path, data: dict) -> None:
    atomic_write_group(path.parent, {path.name: json.dumps(data, indent=2) + "\n"})


def _provider_available() -> bool:
    from ground_sections_vision import load_api_keys
    load_api_keys()
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _make_provider(model: str, reasoning_effort: str, timeout: float):
    from screenshot_to_template.models.anthropic import AnthropicProvider
    # The author layer owns a strict wall-clock budget and bounded repair loop;
    # SDK-level retries would multiply that budget and obscure the gate result.
    return AnthropicProvider(model, reasoning_effort=reasoning_effort,
                             timeout=timeout, max_retries=0)


def _usage_add(total: dict, usage: dict) -> None:
    for key, value in (usage or {}).items():
        if isinstance(value, (int, float)):
            total[key] = total.get(key, 0) + value


def _call_provider(provider, system_prompt: str, user_prompt: str, *,
                   max_tokens: int, timeout: float) -> str:
    """Enforce a wall-clock timeout around streaming providers.

    HTTP read timeouts reset whenever a stream emits a chunk, so they do not bound
    a long thinking/output stream. SIGALRM gives the author CLI a real per-call
    wall-clock budget on its supported Unix runtime.
    """
    if timeout <= 0 or not hasattr(signal, "SIGALRM"):
        return provider.text_query(
            system_prompt, user_prompt, max_tokens=max_tokens)

    def expired(_signum, _frame):
        raise TimeoutError(f"author model call exceeded {timeout:g}s wall-clock timeout")

    previous = signal.getsignal(signal.SIGALRM)
    signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, timeout)
    try:
        return provider.text_query(
            system_prompt, user_prompt, max_tokens=max_tokens)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def _derive_outputs(brand_dir: Path) -> None:
    from render_brand_md import render
    import normalize_scales

    doc = yaml.safe_load((brand_dir / "brand.yaml").read_text()) or {}
    brand_md = render(doc, brand_dir=brand_dir)
    scale = normalize_scales.normalize(brand_dir)
    atomic_write_group(brand_dir, {
        "brand.md": brand_md.rstrip() + "\n",
        "style-scale.yaml": yaml.safe_dump(
            scale, sort_keys=False, allow_unicode=True, width=88),
    })


def _default_validator(brand_dir: Path):
    import validate_brand_evidence as validator
    return validator.validate_brand_dir(brand_dir)


def authored_complete(brand_dir: Path) -> tuple[bool, list[str]]:
    missing = [name for name in EXPECTED_OUTPUTS if not (Path(brand_dir) / name).is_file()]
    return not missing, missing


def _write_result(brand_dir: Path, result: AuthorResult) -> None:
    data = result.to_dict()
    _atomic_json(Path(brand_dir) / AUTHOR_REPORT, data)
    manifest_path = Path(brand_dir) / "manifest.json"
    if not manifest_path.is_file():
        return
    try:
        manifest = json.loads(manifest_path.read_text())
    except Exception:
        return
    manifest["authoring"] = data
    manifest.setdefault("stages", {})["author"] = (
        "completed" if result.ok else f"{result.status} — {result.reason}")
    _atomic_json(manifest_path, manifest)


def author_brand(brand_dir: Path, *, model: str = DEFAULT_MODEL,
                 reasoning_effort: str = DEFAULT_REASONING, timeout: float = 300,
                 max_repairs: int = 2, max_tokens: int = 32_000,
                 force: bool = False, source_url: str | None = None,
                 provider=None, validator: Callable | None = None,
                 log=print, force_stage: str | None = None) -> AuthorResult:
    """Run the evidence-scoped author DAG and bounded, owner-routed repairs."""
    from staged_author import author_brand_staged
    return author_brand_staged(
        Path(brand_dir), model=model, reasoning_effort=reasoning_effort,
        timeout=timeout, max_repairs=max_repairs, max_tokens=max_tokens,
        force=force, source_url=source_url, provider=provider,
        validator=validator or _default_validator, log=log,
        force_stage=force_stage, derive_outputs=_derive_outputs)

