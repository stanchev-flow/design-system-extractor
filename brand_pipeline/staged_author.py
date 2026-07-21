#!/usr/bin/env python3
"""Bounded, evidence-scoped brand authoring DAG.

This module is imported lazily by author_brand.py. Each model stage receives a
small deterministic evidence projection, runs behind a hard child-process
boundary, validates its own response, and installs atomically.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import copy
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import yaml

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
SPEC_DIR = HERE / "spec"
CHECKPOINT = "author-stage-status.json"
REPAIR_INPUT_CAP_BYTES = 80_000
for _path in (REPO_ROOT / "tools" / "extract", REPO_ROOT / "src", HERE):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))


@dataclass(frozen=True)
class Stage:
    name: str
    outputs: tuple[str, ...]
    dependencies: tuple[str, ...]
    max_input_bytes: int
    max_output_tokens: int
    timeout_s: float


STAGES = (
    Stage("foundation", ("brand.yaml", "voice-facts.yaml"), (), 180_000, 20_000, 240),
    Stage("copy-chrome", ("brand-chrome.yaml", "section-copy.yaml"), ("foundation",), 150_000, 16_000, 240),
    Stage("patterns-recipes", ("layout-library.yaml",), ("foundation", "copy-chrome"), 180_000, 20_000, 240),
    Stage("media", ("media-guidance.yaml",), ("patterns-recipes",), 45_000, 4_000, 180),
    Stage("projections", (
        "brand.md", "style-scale.yaml", "voice.md", "media-assets.yaml",
        "assets-tagged.json",
    ), ("foundation", "copy-chrome", "patterns-recipes", "media"), 0, 0, 30),
)
MODEL_STAGES = STAGES[:-1]
STAGE_BY_NAME = {stage.name: stage for stage in STAGES}
MODEL_OUTPUTS = tuple(dict.fromkeys(name for stage in MODEL_STAGES for name in stage.outputs))
EXPECTED_OUTPUTS = (
    "brand.yaml", "layout-library.yaml", "section-copy.yaml",
    "assets-tagged.json", "media-assets.yaml", "voice-facts.yaml",
    "brand.md", "style-scale.yaml", "voice.md",
)

CHECK_OWNERS = {
    **{f"C{i}": "foundation" for i in (1, 2, 3, 10, 13, 14, 15, 19, 24, 25)},
    **{f"C{i}": "copy-chrome" for i in (4, 7, 16, 21, 22)},
    **{f"C{i}": "patterns-recipes" for i in (5, 11, 12, 17, 18, 20, 23)},
    **{f"C{i}": "media" for i in (6, 8, 26, 27, 28)},
}

REQUIRED_INPUTS = (
    "evidence/dom-sections.json",
    "evidence/css-facts.json",
    "evidence/computed-styles.json",
    "evidence/section-rects.json",
    "evidence/motion-audit.json",
    "evidence/crops/crops-manifest.json",
    "assets-manifest.json",
    "media-assets-draft.yaml",
)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path):
    text = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix == ".json":
        return json.loads(text)
    return yaml.safe_load(text)


def _jsonable(value, depth: int = 0):
    """Compact arbitrary mined values while preserving factual leaves."""
    if depth > 8:
        return "[depth-capped]"
    if isinstance(value, dict):
        return {str(k): _jsonable(v, depth + 1) for k, v in value.items()}
    if isinstance(value, list):
        return [_jsonable(v, depth + 1) for v in value[:250]]
    if isinstance(value, str) and len(value) > 1500:
        return value[:1500] + " [truncated]"
    return value


def _grounding_index(brand_dir: Path, *, media_only: bool = False) -> list[dict]:
    rows = []
    for path in sorted((brand_dir / "evidence" / "grounding").glob("*.yaml")):
        doc = _load(path) or {}
        if not isinstance(doc, dict):
            continue
        if media_only:
            keys = ("section", "id", "media", "imagery", "photography", "assets",
                    "visualDirection", "surface", "copy")
        else:
            keys = tuple(doc.keys())
        row = {"ref": str(path.relative_to(brand_dir))}
        row.update({k: _jsonable(doc[k]) for k in keys if k in doc})
        rows.append(row)
    return rows


def _manifest_meta(brand_dir: Path, source_url: str | None) -> dict:
    path = brand_dir / "manifest.json"
    doc = _load(path) if path.is_file() else {}
    doc = doc if isinstance(doc, dict) else {}
    return {
        "lane": brand_dir.parent.name,
        "sourceUrl": source_url or doc.get("source_url"),
        "project": doc.get("project"),
        "brand": doc.get("brand"),
    }


def _spec_excerpt(name: str, cap: int) -> str:
    path = SPEC_DIR / name
    text = path.read_text(encoding="utf-8", errors="replace")
    return text[:cap] + (f"\n[excerpt capped at {cap} bytes]" if len(text) > cap else "")


def _existing_summary(brand_dir: Path, names: tuple[str, ...], cap: int = 28_000) -> dict:
    result = {}
    remaining = cap
    for name in names:
        path = brand_dir / name
        if not path.is_file() or remaining <= 0:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        take = min(len(text), remaining)
        result[name] = text[:take]
        remaining -= take
    return result


def _compact_media_evidence(brand_dir: Path) -> dict:
    """Project the measured media corpus to a bounded tag-level author input.

    The complete curator draft remains on disk and is never sent to the provider.
    Representatives expose enough factual variation to refine each small tag family;
    deterministic projection applies the returned rules to every draft asset.
    """
    draft = _load(brand_dir / "media-assets-draft.yaml") or {}
    assets = [row for row in (draft.get("assets") or []) if isinstance(row, dict)]
    counts = Counter(str(row.get("tagGuess") or "untagged") for row in assets)
    extensions: dict[str, Counter] = defaultdict(Counter)
    representatives: dict[str, list[dict]] = defaultdict(list)
    for row in assets:
        tag = str(row.get("tagGuess") or "untagged")
        extensions[tag][Path(str(row.get("file") or "")).suffix.lower() or "(none)"] += 1
        # Two stable examples per family are enough to show measured shape without
        # turning the request back into a per-asset authoring task.
        if len(representatives[tag]) < 2:
            representatives[tag].append({
                "id": row.get("id"),
                "file": row.get("file"),
                "tagGuess": tag,
                "assetSemantics": _jsonable(row.get("assetSemantics") or {}),
                "facts": _jsonable(row.get("facts") or {}),
                "usageRights": row.get("usageRights"),
                "treatmentDefaults": _jsonable(row.get("treatmentDefaults")),
                "compositionRoles": _jsonable(row.get("compositionRoles") or []),
                "provenance": _jsonable(row.get("provenance") or {}),
            })

    grounding = []
    for path in sorted((brand_dir / "evidence" / "grounding").glob("*.yaml")):
        doc = _load(path) or {}
        if not isinstance(doc, dict):
            continue
        row = {"ref": str(path.relative_to(brand_dir))}
        for key in ("sectionRole", "media", "mediaAssets"):
            if key in doc:
                row[key] = _jsonable(doc[key])
        if len(row) > 1:
            grounding.append(row)
    return {
        "draftOnDisk": "media-assets-draft.yaml",
        "totalAssets": len(assets),
        "tagVocabulary": [
            {
                "tagGuess": tag,
                "count": counts[tag],
                "extensions": dict(sorted(extensions[tag].items())),
            }
            for tag in sorted(counts)
        ],
        "representativeAssets": {
            tag: representatives[tag] for tag in sorted(representatives)
        },
        "photographyEvidence": grounding,
    }


def validate_author_inputs(brand_dir: Path) -> None:
    missing = [name for name in REQUIRED_INPUTS if not (brand_dir / name).is_file()]
    if not list((brand_dir / "evidence" / "grounding").glob("*.yaml")):
        missing.append("evidence/grounding/*.yaml")
    if missing:
        from author_brand import AuthorBlocked
        raise AuthorBlocked("author inputs incomplete — missing: " + ", ".join(missing))


def build_stage_bundle(brand_dir: Path, stage_name: str,
                       source_url: str | None = None) -> dict:
    """Build only the evidence projection owned by one author stage."""
    brand_dir = Path(brand_dir)
    validate_author_inputs(brand_dir)
    evidence = brand_dir / "evidence"
    refs: list[str] = []

    def take(rel: str):
        refs.append(rel)
        return _jsonable(_load(brand_dir / rel))

    base = {"metadata": _manifest_meta(brand_dir, source_url)}
    if stage_name == "foundation":
        base["computedStyles"] = take("evidence/computed-styles.json")
        base["cssFacts"] = take("evidence/css-facts.json")
        base["motionAudit"] = take("evidence/motion-audit.json")
        base["grounding"] = _grounding_index(brand_dir)
        refs += [row["ref"] for row in base["grounding"]]
        base["schemaExcerpt"] = _spec_excerpt("brand-schema.md", 26_000)
    elif stage_name == "copy-chrome":
        base["domSections"] = take("evidence/dom-sections.json")
        base["grounding"] = _grounding_index(brand_dir)
        refs += [row["ref"] for row in base["grounding"]]
        base["foundation"] = _existing_summary(
            brand_dir, ("brand.yaml", "voice-facts.yaml"), 28_000)
        base["schemaExcerpt"] = _spec_excerpt("section-copy-schema.md", 22_000)
    elif stage_name == "patterns-recipes":
        base["sectionRects"] = take("evidence/section-rects.json")
        base["cropMetadata"] = take("evidence/crops/crops-manifest.json")
        base["grounding"] = _grounding_index(brand_dir)
        refs += [row["ref"] for row in base["grounding"]]
        base["upstream"] = _existing_summary(
            brand_dir, ("brand.yaml", "section-copy.yaml"), 34_000)
        base["schemaExcerpt"] = _spec_excerpt("layout-analyst-skill.md", 25_000)
    elif stage_name == "media":
        base["mediaEvidence"] = _compact_media_evidence(brand_dir)
        refs += [
            row["ref"] for row in base["mediaEvidence"]["photographyEvidence"]
        ]
    else:
        raise ValueError(f"unknown model author stage: {stage_name}")
    base["evidenceRefs"] = sorted(set(refs))
    return base


def _stage_system(stage: Stage) -> str:
    specifics = {
        "foundation": (
            "Author only evidence-backed brand facts and semantic choices into brand.yaml; "
            "the deterministic contract projector owns only canonical wrapper shapes and "
            "required-key scaffolding; it MUST NOT replace measured facts. Include canonical "
            "`brand` identity with the public source brand name (never the run/lane id), a rich "
            "evidence-grounded `brand.snapshot.value` of at least two factual sentences, plus "
            "generic tokens, typography, spacing, "
            "surfaces, a contract-keyed `blocks` mapping (never a list), button families, "
            "voice, signatures, actionGroup and motion. For every measured control, keep "
            "`visibleLabel` (painted text) separate from `accessibleName`/`ariaLabel`; when "
            "they differ both fields are required, and visibleLabel must fit the measured "
            "host geometry. Never expand painted copy with screen-reader-only text. "
            "Also author structured voice-facts.yaml."),
        "copy-chrome": (
            "Author brand-chrome.yaml as a merge patch containing only evidence-backed "
            "navbar/footer/chrome anatomy (do not repeat foundation tokens or blocks). "
            "Author section-copy.yaml with verbatim source copy and complete layoutCopy "
            "interaction content. Every visible string must come from supplied DOM/grounding; "
            "never emit the run/lane id or generic specimen copy. CTA/nav/button labels use "
            "`visibleLabel` as rendered `label`; preserve a differing `accessibleName` as "
            "`ariaLabel` only. Never render hidden descriptive suffixes as painted copy."),
        "patterns-recipes": (
            "Author factual pattern/recipe deltas in layout-library.yaml with measured reusable patterns, recipes, "
            "responsive behavior, content shape, action groups and geometry. Crops are "
            "references only; never claim unevidenced patterns as measured. Every extracted "
            "pattern must carry distinct canonical contentShape.slots[] with `name`, `role`, "
            "geometry, source-copy binding semantics, and all observed curated asset filenames. "
            "EVERY slot MUST carry `type:` chosen from exactly: content, media, image, video, "
            "logo, action, structural (text-bearing slots are `content`; CTA/button slots are "
            "`action`; a missing or invented type blocks the stage). Every extracted pattern id "
            "must exactly match a layoutCopy key from the copy-chrome stage. "
            "Do not collapse different sections to generic-flow. The deterministic projector "
            "creates layout instances by PRESERVING these slots/assets and validates cross-file ids."),
        "media": (
            "Author compact media-guidance.yaml. It must contain schemaVersion, a "
            "photographyFingerprint, and tagRules keyed by the draft's small tagGuess "
            "vocabulary, with exactly one concise rule per observed tag. A rule may contain "
            "only assetSemantics, usageRights, treatmentDefaults, or compositionRoles, and "
            "must omit fields that are not shared by the whole tag family. Do NOT emit "
            "assets, files, ids, assetAnnotations, facts, provenance, examples, or unchanged "
            "draft content. photographyFingerprint must be either {notObserved, reason} or "
            "{measured:{temperatureCast:warm|neutral|cool,keyExposure:low-key|mid-key|"
            "high-key,saturationBand:muted|moderate|vivid,finish:matte|neutral|glossy,"
            "sampleSize:<integer>,source:measured|vision-estimated},prose}. Set "
            "schemaVersion exactly to media-guidance.v1. Deterministic projection applies "
            "rules to the complete measured draft kept on disk."),
    }[stage.name]
    return (
        "You are one bounded stage in an evidence-first design-system authoring DAG. "
        "Use only supplied facts and upstream summaries. Never copy another lane. "
        "Use generic reusable role names, not section-specific token names. "
        f"{specifics} Return ONLY JSON: {{\"files\":{{\"filename\":\"complete contents\"}}}}. "
        "Every requested file must be complete and parseable; no markdown fences. "
        "YAML SYNTAX LAW: emit BLOCK-STYLE YAML only. Mappings: one key per "
        "line, nested by indentation. Lists: block sequences with `- ` items — "
        "block sequences are REQUIRED wherever the schema says list (e.g. "
        "`patterns:` is a list of `- id: …` entries, never a mapping keyed by "
        "id). ONLY inline/flow syntax is forbidden: no {…} flow mappings, no "
        "[…] flow sequences. Any scalar containing [ ] { } : , # or -> must be "
        "quoted. (Flow-mapping scalars like `border: 1px #ececec` or "
        "`copyBinding: items[].cta` are YAML parse errors that block the stage.)"
    )


def _prompt(stage: Stage, bundle: dict, *, errors: list[str] | None = None,
            current: dict[str, str] | None = None) -> str:
    payload = {
        "stage": stage.name,
        "requestedFiles": list(stage.outputs),
        "validationErrorsOwnedByThisStage": errors or [],
        "currentStageFiles": current or {},
        "input": bundle,
    }
    prefix = (
        "Author the requested factual deltas and choices in parseable requested files. "
        "Do not fabricate required keys: deterministic contract projection supplies canonical "
        "schema scaffolding after this stage. On repair, address only listed checks and preserve "
        "unrelated valid facts.\n"
    )
    return prefix + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _input_size(system_prompt: str, user_prompt: str) -> int:
    return len(system_prompt.encode()) + len(user_prompt.encode())


def _checkpoint_path(brand_dir: Path) -> Path:
    return brand_dir / CHECKPOINT


def _read_checkpoint(brand_dir: Path) -> dict:
    path = _checkpoint_path(brand_dir)
    if not path.is_file():
        return {"schemaVersion": "brand-author-stages.v1", "stages": {}}
    try:
        doc = json.loads(path.read_text())
        return doc if isinstance(doc, dict) else {"stages": {}}
    except Exception:
        return {"schemaVersion": "brand-author-stages.v1", "stages": {}}


def _write_checkpoint(brand_dir: Path, doc: dict) -> None:
    from author_brand import _atomic_json
    doc["updatedAt"] = _now()
    _atomic_json(_checkpoint_path(brand_dir), doc)


def _normalize_brand_identity(doc: dict) -> dict:
    """Normalize the one supported legacy identity shape to the canonical mapping.

    Old staged responses may carry ``brand: <name>``. Preserve canonical mappings
    verbatim, convert only a non-empty string scalar, and reject every other shape
    so malformed required structure still fails before install/projection.
    """
    from author_brand import AuthorBlocked
    identity = doc.get("brand")
    if isinstance(identity, dict):
        if not str(identity.get("name") or "").strip():
            raise AuthorBlocked("brand.yaml brand mapping requires a non-empty name")
        return doc
    if isinstance(identity, str) and identity.strip():
        normalized = dict(doc)
        normalized["brand"] = {"name": identity.strip()}
        return normalized
    raise AuthorBlocked(
        "brand.yaml brand must be a canonical identity mapping with non-empty name "
        "(legacy non-empty string scalar is the only normalized form)")


def _required_shape(name: str, doc: dict) -> None:
    from author_brand import AuthorBlocked
    requirements = {
        "brand.yaml": ("brand", "tokens", "blocks"),
        "brand-chrome.yaml": (),
        "voice-facts.yaml": ("schemaVersion",),
        "section-copy.yaml": ("sectionCopy", "layoutCopy"),
        "layout-library.yaml": ("schemaVersion", "patterns"),
        "assets-tagged.json": ("schemaVersion", "assets"),
        "media-assets.yaml": ("schemaVersion", "assets"),
        "media-guidance.yaml": ("schemaVersion", "photographyFingerprint", "tagRules"),
    }
    missing = [key for key in requirements.get(name, ()) if key not in doc]
    if missing:
        raise AuthorBlocked(f"{name} missing required stage keys: {', '.join(missing)}")
    if name == "brand.yaml":
        canonical = _normalize_brand_identity(doc)
        identity = canonical["brand"]
        public_name = str(identity.get("name") or "").strip()
        if re.search(r"(?:^|[-_\s])v\d+$", public_name, re.I):
            raise AuthorBlocked(
                "brand.yaml brand.name must be the public source brand, not a versioned lane id")
        snapshot = identity.get("snapshot")
        snapshot = snapshot.get("value") if isinstance(snapshot, dict) else snapshot
        if len(str(snapshot or "").strip()) < 120:
            raise AuthorBlocked(
                "brand.yaml brand.snapshot.value must be a rich evidence-grounded narrative "
                "(at least 120 characters)")
        if not isinstance(doc.get("blocks"), dict):
            raise AuthorBlocked(
                "brand.yaml blocks must be a canonical contract-keyed mapping")
        layouts = doc.get("layouts")
        if layouts is not None and (
                not isinstance(layouts, list)
                or not all(isinstance(row, dict) for row in layouts)):
            raise AuthorBlocked(
                "brand.yaml layouts must be a list of layout mappings")
    if name == "layout-library.yaml":
        patterns = doc.get("patterns")
        if not isinstance(patterns, list) or not patterns:
            raise AuthorBlocked("layout-library.yaml patterns must be a non-empty list")
        for pattern in patterns:
            if not isinstance(pattern, dict) or not pattern.get("id"):
                raise AuthorBlocked("layout-library.yaml patterns require stable ids")
            if pattern.get("origin") != "extracted":
                continue
            slots = ((pattern.get("contentShape") or {}).get("slots")
                     if isinstance(pattern.get("contentShape"), dict) else None)
            if not isinstance(slots, list) or not slots:
                raise AuthorBlocked(
                    f"layout-library.yaml extracted pattern {pattern['id']!r} "
                    "requires populated contentShape.slots")
            if any(not isinstance(slot, dict) or not slot.get("name") for slot in slots):
                raise AuthorBlocked(
                    f"layout-library.yaml extracted pattern {pattern['id']!r} "
                    "requires a canonical name on every slot")
            bad_types = [
                slot.get("name") for slot in slots
                if slot.get("type") not in {
                    "content", "media", "image", "video", "logo",
                    "action", "structural",
                }
            ]
            if bad_types:
                raise AuthorBlocked(
                    f"layout-library.yaml extracted pattern {pattern['id']!r} "
                    f"requires canonical slot type on: {', '.join(map(str, bad_types))}")
            if any(slot.get("sourceCopy") is not None for slot in slots):
                raise AuthorBlocked(
                    f"layout-library.yaml extracted pattern {pattern['id']!r} "
                    "uses unsupported sourceCopy indirection")
    if name == "brand-chrome.yaml" and not any(
            key in doc for key in ("navbar", "header", "footer", "chrome")):
        raise AuthorBlocked(
            "brand-chrome.yaml must contain navbar/header/footer/chrome facts")


def validate_stage_files(files: dict[str, str]) -> None:
    for name, text in files.items():
        doc = json.loads(text) if name.endswith(".json") else yaml.safe_load(text)
        if not isinstance(doc, dict):
            from author_brand import AuthorBlocked
            raise AuthorBlocked(f"{name} must parse to a mapping")
        _required_shape(name, doc)
        if name == "brand.yaml":
            files[name] = yaml.safe_dump(
                _normalize_brand_identity(doc), sort_keys=False,
                allow_unicode=True, width=100)


def validate_stage_joins(brand_dir: Path, files: dict[str, str]) -> None:
    """Reject cross-stage namespace drift before atomic installation."""
    if "layout-library.yaml" not in files:
        return
    from author_brand import AuthorBlocked
    library = yaml.safe_load(files["layout-library.yaml"]) or {}
    copy_path = Path(brand_dir) / "section-copy.yaml"
    copy_doc = _load(copy_path) or {}
    layout_copy = copy_doc.get("layoutCopy") \
        if isinstance(copy_doc.get("layoutCopy"), dict) else {}
    allowed_types = {
        "content", "media", "image", "video", "logo",
        "action", "structural",
    }
    errors = []
    for pattern in library.get("patterns") or []:
        if not isinstance(pattern, dict) or pattern.get("origin") != "extracted":
            continue
        pid = str(pattern.get("id") or "")
        slots = ((pattern.get("contentShape") or {}).get("slots") or [])
        if pid not in layout_copy:
            errors.append(f"pattern {pid!r} has no exact layoutCopy join")
        for slot in slots:
            if not isinstance(slot, dict):
                continue
            if slot.get("type") not in allowed_types:
                errors.append(
                    f"pattern {pid!r} slot {slot.get('name')!r} requires canonical type")
            if slot.get("sourceCopy") is not None:
                errors.append(
                    f"pattern {pid!r} slot {slot.get('name')!r} uses unsupported sourceCopy")
    if errors:
        raise AuthorBlocked("cross-stage join validation failed: " + "; ".join(errors))


def _validate_media_guidance(text: str, tag_vocabulary: set[str]) -> None:
    from author_brand import AuthorBlocked
    import media_semantics as ms
    doc = yaml.safe_load(text) or {}
    if doc.get("schemaVersion") != "media-guidance.v1":
        raise AuthorBlocked(
            "media-guidance.yaml schemaVersion must be media-guidance.v1")
    allowed_top = {"schemaVersion", "photographyFingerprint", "tagRules"}
    extra = set(doc) - allowed_top
    if extra:
        raise AuthorBlocked(
            "media-guidance.yaml contains forbidden top-level keys: "
            + ", ".join(sorted(extra)))
    rules = doc.get("tagRules")
    if not isinstance(rules, dict):
        raise AuthorBlocked("media-guidance.yaml tagRules must be a mapping")
    fingerprint = doc.get("photographyFingerprint")
    if not isinstance(fingerprint, dict):
        raise AuthorBlocked("media photographyFingerprint must be a mapping")
    if fingerprint.get("notObserved") is not True:
        measured = fingerprint.get("measured")
        if not isinstance(measured, dict):
            raise AuthorBlocked(
                "media photographyFingerprint requires measured facts")
        enum_fields = {
            "temperatureCast": {"warm", "neutral", "cool"},
            "keyExposure": {"low-key", "mid-key", "high-key"},
            "saturationBand": {"muted", "moderate", "vivid"},
            "finish": {"matte", "neutral", "glossy"},
            "source": {"measured", "vision-estimated"},
        }
        invalid = [
            f"{key}={measured.get(key)!r}"
            for key, allowed in enum_fields.items()
            if measured.get(key) not in allowed
        ]
        if not isinstance(measured.get("sampleSize"), int) \
                or measured["sampleSize"] < 1:
            invalid.append(f"sampleSize={measured.get('sampleSize')!r}")
        if invalid:
            raise AuthorBlocked(
                "media photographyFingerprint has invalid measured fields: "
                + ", ".join(invalid))
    actual = {str(key) for key in rules}
    if actual != tag_vocabulary:
        raise AuthorBlocked(
            "media-guidance.yaml tagRules must exactly match tagGuess vocabulary; "
            f"missing={sorted(tag_vocabulary - actual)}, "
            f"unknown={sorted(actual - tag_vocabulary)}")
    allowed_rule = {
        "assetSemantics", "usageRights", "treatmentDefaults", "compositionRoles",
    }
    for tag, rule in rules.items():
        if not isinstance(rule, dict):
            raise AuthorBlocked(f"media tag rule {tag!r} must be a mapping")
        forbidden = set(rule) - allowed_rule
        if forbidden:
            raise AuthorBlocked(
                f"media tag rule {tag!r} contains forbidden keys: "
                + ", ".join(sorted(forbidden)))
        if "assetSemantics" in rule and not isinstance(
                rule["assetSemantics"], dict):
            raise AuthorBlocked(
                f"media tag rule {tag!r} assetSemantics must be a mapping")
        if "usageRights" in rule and rule["usageRights"] not in ms.USAGE_RIGHTS:
            raise AuthorBlocked(
                f"media tag rule {tag!r} has invalid usageRights")
        if "treatmentDefaults" in rule and not isinstance(
                rule["treatmentDefaults"], dict):
            raise AuthorBlocked(
                f"media tag rule {tag!r} treatmentDefaults must be a mapping")
        if "compositionRoles" in rule and not isinstance(
                rule["compositionRoles"], list):
            raise AuthorBlocked(
                f"media tag rule {tag!r} compositionRoles must be a list")


def stage_valid(brand_dir: Path, stage: Stage) -> bool:
    if stage.name == "projections":
        return all((brand_dir / name).is_file() for name in stage.outputs)
    try:
        files = {name: (brand_dir / name).read_text() for name in stage.outputs}
        validate_stage_files(files)
        if stage.name == "media":
            vocabulary = {
                str(row.get("tagGuess") or "untagged")
                for row in (_load(brand_dir / "media-assets-draft.yaml") or {}).get(
                    "assets", [])
                if isinstance(row, dict)
            }
            _validate_media_guidance(files["media-guidance.yaml"], vocabulary)
        return True
    except Exception:
        return False


def _provider_worker(request_path: Path, response_path: Path) -> int:
    request = json.loads(request_path.read_text())
    from ground_sections_vision import load_api_keys
    load_api_keys()
    from screenshot_to_template.models.anthropic import AnthropicProvider
    provider = AnthropicProvider(
        request["model"], reasoning_effort=request["reasoningEffort"],
        timeout=request["providerTimeout"], max_retries=0)
    raw = provider.text_query(
        request["system"], request["user"], max_tokens=request["maxTokens"])
    response_path.write_text(json.dumps({
        "raw": raw,
        "usage": getattr(provider, "last_usage", {}) or {},
        "model": getattr(provider, "model", request["model"]),
    }))
    return 0


def child_provider_call(*, model: str, reasoning_effort: str, system: str,
                        user: str, max_tokens: int, timeout: float) -> tuple[str, dict, str]:
    """Invoke Anthropic in a disposable process with a hard wall-clock timeout."""
    from author_brand import AuthorBlocked
    with tempfile.TemporaryDirectory(prefix="brand-author-call-") as td:
        root = Path(td)
        request = root / "request.json"
        response = root / "response.json"
        request.write_text(json.dumps({
            "model": model,
            "reasoningEffort": reasoning_effort,
            "system": system,
            "user": user,
            "maxTokens": max_tokens,
            "providerTimeout": min(timeout, 120),
        }))
        cmd = [sys.executable, str(Path(__file__).resolve()), "--provider-worker",
               str(request), str(response)]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True,
                                  timeout=timeout, env=os.environ.copy())
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError(
                f"author stage model call exceeded {timeout:g}s hard timeout") from exc
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout or "").strip()[-1200:]
            raise AuthorBlocked(
                f"author provider child failed (exit {proc.returncode}): {detail}")
        if not response.is_file():
            raise AuthorBlocked("author provider child returned no response file")
        data = json.loads(response.read_text())
        return data["raw"], data.get("usage") or {}, data.get("model") or model


def _call(injected_provider, *, model: str, reasoning_effort: str, system: str,
          user: str, max_tokens: int, timeout: float):
    if injected_provider is None:
        return child_provider_call(
            model=model, reasoning_effort=reasoning_effort, system=system, user=user,
            max_tokens=max_tokens, timeout=timeout)
    raw = injected_provider.text_query(system, user, max_tokens=max_tokens)
    return raw, getattr(injected_provider, "last_usage", {}) or {}, \
        getattr(injected_provider, "model", model)


def _usage_add(total: dict, usage: dict) -> None:
    for key, value in usage.items():
        if isinstance(value, (int, float)):
            total[key] = total.get(key, 0) + value


def _errors_by_owner(errors: list[str]) -> dict[str, list[str]]:
    routed: dict[str, list[str]] = {}
    for error in errors:
        check = str(error).split(":", 1)[0].strip().split()[0]
        owner = CHECK_OWNERS.get(check, "foundation")
        routed.setdefault(owner, []).append(error)
    return routed


@dataclass(frozen=True)
class RepairGroup:
    owner: str
    schema_path: str
    errors: tuple[str, ...]

    @property
    def group_id(self) -> str:
        digest = hashlib.sha256(
            (self.owner + "\0" + self.schema_path + "\0" + "\0".join(self.errors))
            .encode()
        ).hexdigest()[:12]
        return f"{self.owner}:{self.schema_path}:{digest}"


def _error_check(error: str) -> str:
    return str(error).split(":", 1)[0].strip().split()[0]


def _error_schema_path(error: str) -> str:
    """Return the narrowest stable artifact path named by a validator row."""
    check = _error_check(error)
    if check == "C2":
        return "/blocks"
    if check == "C3":
        return "/buttons"
    if check == "C4":
        match = re.search(r"\blayoutCopy\.([^:\s]+)", error)
        return f"/layoutCopy/{match.group(1)}" if match else "/"
    if check == "C7":
        if "footer.social" in error:
            return "/footer/social"
        if "footer.legal" in error:
            return "/footer/legal"
        return "/footer"
    if check == "C10":
        return "/blocks/card"
    if check == "C11":
        return "/layouts"
    if check == "C13":
        match = re.search(r"\bblocks\.([^:\s]+)", error)
        if match:
            return f"/blocks/{match.group(1)}/motion"
        return "/tokens/motion"
    if check == "C15":
        return "/tokens/spacing"
    if check == "C20":
        match = re.search(r"pattern '([^']+)'", error)
        return f"/patterns/{match.group(1)}/contentShape" if match else "/patterns"
    if check == "C21":
        return "/navbar/utility"
    return f"/checks/{check}"


def _path_owner(check: str, schema_path: str) -> str:
    # C11 names a pattern check, but this exact failure is owned by brand.yaml
    # layouts, not by the already-valid layout-library pattern.
    if check == "C11" and (
            schema_path == "/layouts" or schema_path.startswith("/layouts/")):
        return "foundation"
    return CHECK_OWNERS.get(check, "foundation")


def group_repair_errors(errors: list[str]) -> list[RepairGroup]:
    grouped: dict[tuple[str, str], list[str]] = {}
    for error in errors:
        path = _error_schema_path(error)
        owner = _path_owner(_error_check(error), path)
        grouped.setdefault((owner, path), []).append(error)
    return [
        RepairGroup(owner, path, tuple(rows))
        for (owner, path), rows in grouped.items()
    ]


def _markdown_section(name: str, heading_needles: tuple[str, ...]) -> str:
    """Select exact markdown sections, stopping at the next same/higher heading."""
    text = (SPEC_DIR / name).read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    selected: list[str] = []
    for needle in heading_needles:
        start = next(
            (i for i, line in enumerate(lines)
             if line.startswith("#") and needle.lower() in line.lower()),
            None,
        )
        if start is None:
            continue
        level = len(lines[start]) - len(lines[start].lstrip("#"))
        end = len(lines)
        for i in range(start + 1, len(lines)):
            line = lines[i]
            if not line.startswith("#"):
                continue
            next_level = len(line) - len(line.lstrip("#"))
            if next_level <= level:
                end = i
                break
        selected.append("\n".join(lines[start:end]).strip())
    return "\n\n".join(selected)


def _repair_spec_excerpt(checks: set[str]) -> dict[str, str]:
    mapping = {
        "C2": ("brand-schema.md", ("10.1 `blocks.",)),
        "C3": ("brand-schema.md", ("10.2 `buttons:",)),
        "C4": ("section-copy-schema.md", ("2. Top-level keys", "4. `layoutCopy`")),
        "C7": ("brand-schema.md", ("10.3 `footer.legal.text`",)),
        "C10": ("brand-schema.md", ("10.3c `blocks.card.variants`",)),
        "C11": ("brand-schema.md", ("4.2 `layouts[]`", "10.3d Composed-demo")),
        "C13": ("brand-schema.md", ("10.3e Motion",)),
        "C15": ("brand-schema.md", ("10.3e Motion",)),
        "C20": ("brand-schema.md", ("4.4d `contentShape.gridEqualize`",)),
    }
    result: dict[str, str] = {}
    by_file: dict[str, list[str]] = defaultdict(list)
    for check in sorted(checks):
        if check in mapping:
            name, needles = mapping[check]
            by_file[name].extend(needles)
    for name, needles in by_file.items():
        result[name] = _markdown_section(name, tuple(dict.fromkeys(needles)))
    if "C21" in checks:
        text = (SPEC_DIR / "brand-schema.md").read_text(
            encoding="utf-8", errors="replace")
        start = text.find("> - `navbar.utility[]`")
        end = text.find("> - `footer.measured.grid`", start)
        if start >= 0:
            result["brand-schema.md#navbar.utility"] = text[
                start:end if end >= 0 else start + 5000].strip()
    return result


def _at_path(doc, path: str):
    if path == "/":
        return doc
    node = doc
    for token in [p for p in path.split("/") if p]:
        if isinstance(node, dict):
            node = node.get(token)
        elif isinstance(node, list):
            if token.isdigit() and int(token) < len(node):
                node = node[int(token)]
            else:
                return None
        else:
            return None
    return node


def _pattern_fragment(doc: dict, pattern_id: str):
    return next(
        (row for row in (doc.get("patterns") or [])
         if isinstance(row, dict) and str(row.get("id")) == pattern_id),
        None,
    )


def extract_repair_fragments(brand_dir: Path, group: RepairGroup) -> dict:
    """Extract only failing artifact branches plus compact cross-file identities."""
    brand = _load(brand_dir / "brand.yaml") or {}
    chrome = _load(brand_dir / "brand-chrome.yaml") or {}
    layout = _load(brand_dir / "layout-library.yaml") or {}
    copy_doc = _load(brand_dir / "section-copy.yaml") or {}
    path = group.schema_path
    fragments: dict[str, object] = {}
    if path.startswith("/footer") or path.startswith("/navbar"):
        fragments["brand-chrome.yaml"] = {
            path.split("/")[1]: chrome.get(path.split("/")[1])
        }
    elif path.startswith("/patterns/"):
        pid = path.split("/")[2]
        fragments["layout-library.yaml"] = {"pattern": _pattern_fragment(layout, pid)}
    elif path.startswith("/layoutCopy") or (
            path == "/" and any(_error_check(e) == "C4" for e in group.errors)):
        if path == "/":
            fragments["section-copy.yaml"] = {
                "topLevelKeys": list(copy_doc),
                "unknownTopLevel": {
                    key: copy_doc[key] for key in copy_doc
                    if key not in {"sectionCopy", "layoutCopy", "layoutImages",
                                   "defaultArt", "wildcardCopy"}
                },
            }
        else:
            fragments["section-copy.yaml"] = {
                "layoutCopy": {
                    path.split("/")[2]: (copy_doc.get("layoutCopy") or {}).get(
                        path.split("/")[2])
                }
            }
    elif path == "/layouts":
        fragments["brand.yaml"] = {
            "layouts": brand.get("layouts") or [],
        }
        fragments["layout-library.yaml"] = {
            "patterns": [
                {
                    key: row.get(key) for key in (
                        "id", "useCase", "archetypeRef", "surfaceIntent",
                        "contentShape", "gridRules", "responsive", "provenance")
                    if row.get(key) is not None
                }
                for row in (layout.get("patterns") or []) if isinstance(row, dict)
            ]
        }
        fragments["section-copy.yaml"] = {
            "availableLayoutCopyIds": sorted((copy_doc.get("layoutCopy") or {}).keys())
        }
    else:
        fragments["brand.yaml"] = {path: _at_path(brand, path)}
    return fragments


def _compact_repair_evidence(brand_dir: Path, checks: set[str]) -> dict:
    """Return field-level facts only; never inline raw HTML/CSS or unrelated assets."""
    result: dict[str, object] = {}
    if checks & {"C2", "C10"}:
        rows = []
        for path in sorted((brand_dir / "evidence" / "grounding").glob("*.yaml")):
            doc = _load(path) or {}
            components = doc.get("components") if isinstance(doc, dict) else None
            if components:
                rows.append({
                    "ref": str(path.relative_to(brand_dir)),
                    "components": _jsonable(components),
                })
        result["groundedComponents"] = rows
    if checks & {"C3"}:
        facts = _load(brand_dir / "evidence" / "css-facts.json") or {}
        result["actionFacts"] = {
            key: _jsonable(facts.get(key))
            for key in ("buttonCensus", "hoverRules", "actionFamilies")
            if facts.get(key) is not None
        }
    if checks & {"C13"}:
        motion = _load(brand_dir / "evidence" / "motion-audit.json") or {}
        result["motionFacts"] = {
            key: _jsonable(motion.get(key))
            for key in ("durationCensus", "easingCensus", "motionVars",
                        "signatureMoves", "transitions", "animations")
            if motion.get(key) is not None
        }
    if checks & {"C15"}:
        brand = _load(brand_dir / "brand.yaml") or {}
        result["spacingFacts"] = {
            "existingSpacing": _jsonable((brand.get("tokens") or {}).get("spacing")),
            "validatorDerivedRequirement": (
                "Resolve the exact row-rhythm custom properties named in the validator "
                "error through the measured spacing scale; raw CSS is intentionally excluded."
            ),
        }
    if checks & {"C11", "C20"}:
        rects = _load(brand_dir / "evidence" / "section-rects.json") or {}
        result["sectionGeometrySummary"] = {
            key: _jsonable(rects.get(key))
            for key in ("sections", "tiers", "viewport")
            if rects.get(key) is not None
        }
    if checks & {"C21"}:
        chrome = _load(brand_dir / "brand-chrome.yaml") or {}
        result["chromeFacts"] = {
            "navbarUtility": _jsonable((chrome.get("navbar") or {}).get("utility")),
            "evidenceRefs": _jsonable((chrome.get("provenance") or {}).get("navbar")),
            "validatorDerivedRequirement": (
                "The mined stylesheet names an in-bar language/locale switcher; "
                "raw selectors and declarations are intentionally excluded."
            ),
        }
    return result


def _repair_dependency_summary(brand_dir: Path, group: RepairGroup) -> dict:
    brand = _load(brand_dir / "brand.yaml") or {}
    layout = _load(brand_dir / "layout-library.yaml") or {}
    copy_doc = _load(brand_dir / "section-copy.yaml") or {}
    return {
        "brandName": (brand.get("brand") or {}).get("name")
        if isinstance(brand.get("brand"), dict) else brand.get("brand"),
        "patternIds": [
            row.get("id") for row in (layout.get("patterns") or [])
            if isinstance(row, dict) and row.get("id")
        ],
        "layoutRefs": [
            {"id": row.get("id"), "patternRef": row.get("patternRef")}
            for row in (brand.get("layouts") or []) if isinstance(row, dict)
        ],
        "layoutCopyIds": sorted((copy_doc.get("layoutCopy") or {}).keys()),
        "immutable": (
            "Do not alter unrelated branches, evidence artifacts, assets, or completed "
            "stage outputs. Patch only the allowed path(s)."
        ),
    }


def build_repair_bundle(brand_dir: Path, group: RepairGroup) -> dict:
    checks = {_error_check(error) for error in group.errors}
    return {
        "groupId": group.group_id,
        "ownerStage": group.owner,
        "schemaPath": group.schema_path,
        "validatorErrors": list(group.errors),
        "failingFragments": extract_repair_fragments(brand_dir, group),
        "relevantSpecSections": _repair_spec_excerpt(checks),
        "affectedFieldEvidence": _compact_repair_evidence(brand_dir, checks),
        "dependencySummary": _repair_dependency_summary(brand_dir, group),
    }


def _repair_allowed_targets(group: RepairGroup) -> dict[str, tuple[str, ...]]:
    path = group.schema_path
    if path.startswith("/footer") or path.startswith("/navbar"):
        return {"brand-chrome.yaml": (path,)}
    if path.startswith("/patterns/"):
        return {"layout-library.yaml": (path,)}
    if path.startswith("/layoutCopy") or path == "/":
        return {"section-copy.yaml": (path,)}
    if path == "/layouts":
        return {"brand.yaml": ("/layouts",), "section-copy.yaml": ("/layoutCopy",)}
    return {"brand.yaml": (path,)}


def _repair_system(group: RepairGroup) -> str:
    allowed = _repair_allowed_targets(group)
    shape_rule = (
        " For /layouts, emit exactly one replace patch at /layouts whose value is "
        "a JSON ARRAY of layout objects; never encode list markers as mapping keys."
        if group.schema_path == "/layouts" else ""
    )
    if group.schema_path == "/footer/social":
        shape_rule += (
            " Replace /footer/social itself with a JSON ARRAY of {network,href} "
            "entries; do not nest the array under icons or role.")
    if group.schema_path == "/navbar/utility":
        shape_rule += (
            " Replace /navbar/utility itself with a JSON ARRAY of utility controls; "
            "a language switcher is one kind:dropdown entry with dropdown.items and "
            "measured dropdown.panel facts, or use the exact allowed notObserved escape.")
    return (
        "You repair one validator-error group in an evidence-first brand artifact. "
        "Use only supplied fragments, exact spec sections, affected-field evidence, "
        "and immutable dependency summaries. Do not invent design/content facts. "
        "Return ONLY JSON {\"patches\":[...]}. Each patch is "
        "{\"file\":\"name\",\"op\":\"merge|replace|add|remove\","
        "\"path\":\"/json/pointer\",\"value\":...}; remove omits value. "
        "Patch only these file/path prefixes: "
        + json.dumps(allowed, separators=(",", ":"))
        + ". Use merge for bounded mapping fragments and add /.../- for list entries. "
        "Never re-emit a complete artifact, raw HTML/CSS, or unrelated branches. "
        "Keep each field concise. For contract blocks with no direct supplied component "
        "evidence, emit only {notObserved:true, reason:<short evidence-scan reason>}; "
        "do not invent or narrate missing anatomy." + shape_rule
    )


def _repair_prompt(bundle: dict) -> str:
    return (
        "Repair exactly the listed validator rows while preserving unrelated facts.\n"
        + json.dumps(bundle, ensure_ascii=False, separators=(",", ":"))
    )


def split_repair_group_to_cap(brand_dir: Path, group: RepairGroup,
                              cap: int = REPAIR_INPUT_CAP_BYTES) -> list[RepairGroup]:
    """Split multi-error groups until every prompt fits the repair hard cap."""
    pending = [group]
    result: list[RepairGroup] = []
    while pending:
        current = pending.pop(0)
        bundle = build_repair_bundle(brand_dir, current)
        size = _input_size(_repair_system(current), _repair_prompt(bundle))
        if size <= cap:
            result.append(current)
            continue
        if len(current.errors) > 1:
            mid = len(current.errors) // 2
            pending[:0] = [
                RepairGroup(current.owner, current.schema_path, current.errors[:mid]),
                RepairGroup(current.owner, current.schema_path, current.errors[mid:]),
            ]
            continue
        raise RuntimeError(
            f"repair group {current.group_id} input {size} bytes exceeds cap {cap}")
    return result


def _pointer_tokens(path: str) -> list[str]:
    if not path.startswith("/"):
        raise ValueError(f"patch path must be a JSON pointer: {path!r}")
    return [
        token.replace("~1", "/").replace("~0", "~")
        for token in path.split("/")[1:]
    ]


def _path_allowed(path: str, prefixes: tuple[str, ...]) -> bool:
    return any(
        prefix == "/" or path == prefix or path.startswith(prefix.rstrip("/") + "/")
        for prefix in prefixes
    )


def _apply_one_patch(doc, patch: dict):
    op = patch.get("op")
    path = str(patch.get("path") or "")
    tokens = _pointer_tokens(path)
    if not tokens or tokens == [""]:
        if op == "remove":
            return {}
        if op in ("replace", "add", "merge"):
            value = copy.deepcopy(patch.get("value"))
            return _deep_merge(doc, value) if op == "merge" else value
        raise ValueError(f"unsupported patch op {op!r}")
    parent = doc
    for token in tokens[:-1]:
        if isinstance(parent, dict):
            if token not in parent:
                parent[token] = {}
            parent = parent[token]
        elif isinstance(parent, list) and token.isdigit():
            parent = parent[int(token)]
        else:
            raise ValueError(f"patch path does not resolve: {path}")
    leaf = tokens[-1]
    if isinstance(parent, dict):
        if op == "remove":
            parent.pop(leaf, None)
        elif op == "merge":
            value = copy.deepcopy(patch.get("value"))
            parent[leaf] = _deep_merge(parent.get(leaf, {}), value) \
                if isinstance(parent.get(leaf), dict) and isinstance(value, dict) else value
        elif op in ("add", "replace"):
            parent[leaf] = copy.deepcopy(patch.get("value"))
        else:
            raise ValueError(f"unsupported patch op {op!r}")
    elif isinstance(parent, list):
        if leaf == "-" and op == "add":
            parent.append(copy.deepcopy(patch.get("value")))
        elif leaf.isdigit() and op == "remove":
            parent.pop(int(leaf))
        elif leaf.isdigit() and op in ("add", "replace"):
            parent[int(leaf)] = copy.deepcopy(patch.get("value"))
        else:
            raise ValueError(f"invalid list patch {op!r} at {path!r}")
    else:
        raise ValueError(f"patch parent is not a container: {path}")
    return doc


def parse_and_apply_repair(brand_dir: Path, group: RepairGroup, raw: str) -> list[str]:
    """Validate every bounded patch against copies, then install all files atomically."""
    from author_brand import AuthorBlocked, atomic_write_group
    text = raw.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, re.S)
    if fenced:
        text = fenced.group(1)
    try:
        response = json.loads(text)
    except Exception as exc:
        raise AuthorBlocked(f"repair response is not JSON: {exc}") from exc
    patches = response.get("patches") if isinstance(response, dict) else None
    if not isinstance(patches, list) or not patches:
        raise AuthorBlocked("repair response requires a non-empty patches list")
    allowed = _repair_allowed_targets(group)
    candidates: dict[str, dict] = {}
    for patch in patches:
        if not isinstance(patch, dict):
            raise AuthorBlocked("every repair patch must be an object")
        name = str(patch.get("file") or "")
        path = str(patch.get("path") or "")
        if name not in allowed or not _path_allowed(path, allowed[name]):
            raise AuthorBlocked(
                f"repair patch target {name}:{path} is outside group scope")
        if name not in candidates:
            loaded = _load(brand_dir / name)
            if not isinstance(loaded, dict):
                raise AuthorBlocked(f"repair target {name} must be a mapping")
            candidates[name] = copy.deepcopy(loaded)
        apply_patch = dict(patch)
        if name == "layout-library.yaml" and path.startswith("/patterns/"):
            tokens = _pointer_tokens(path)
            pattern_id = tokens[1] if len(tokens) > 1 else ""
            rows = candidates[name].get("patterns")
            index = next(
                (i for i, row in enumerate(rows or [])
                 if isinstance(row, dict) and str(row.get("id")) == pattern_id),
                None,
            )
            if index is None:
                raise AuthorBlocked(
                    f"repair target pattern {pattern_id!r} not found")
            apply_patch["path"] = "/" + "/".join(
                ["patterns", str(index), *tokens[2:]])
        try:
            candidates[name] = _apply_one_patch(candidates[name], apply_patch)
        except Exception as exc:
            raise AuthorBlocked(f"invalid repair patch {name}:{path}: {exc}") from exc
    serialized = {
        name: yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=100)
        for name, doc in candidates.items()
    }
    validate_stage_files(serialized)
    validate_stage_joins(brand_dir, serialized)
    atomic_write_group(brand_dir, serialized)
    return sorted(serialized)


def _deep_merge(base: dict, patch: dict) -> dict:
    result = dict(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _project_media_doc(brand_dir: Path) -> dict:
    draft = yaml.safe_load((brand_dir / "media-assets-draft.yaml").read_text()) or {}
    guidance = yaml.safe_load((brand_dir / "media-guidance.yaml").read_text()) or {}
    brand = yaml.safe_load((brand_dir / "brand.yaml").read_text()) or {}
    tag_rules = guidance.get("tagRules") or {}
    assets = []
    for asset in draft.get("assets") or []:
        if not isinstance(asset, dict):
            continue
        tag_patch = tag_rules.get(str(asset.get("tagGuess")), {}) \
            if isinstance(tag_rules, dict) else {}
        merged = _deep_merge(asset, tag_patch if isinstance(tag_patch, dict) else {})
        assets.append(merged)
    brand_value = brand.get("brand")
    brand_name = brand_value.get("name") if isinstance(brand_value, dict) \
        else brand_value or brand.get("name")
    return {
        "schemaVersion": "media-assets.v1",
        "brand": brand_name,
        "photographyFingerprint": guidance.get("photographyFingerprint") or {
            "notObserved": True,
            "reason": "no photography fingerprint authored from evidence",
        },
        "assets": assets,
    }


def _project_media(brand_dir: Path) -> str:
    return yaml.safe_dump(
        _project_media_doc(brand_dir), sort_keys=False, allow_unicode=True, width=100)


def _project_assets_tagged(brand_dir: Path) -> str:
    media = _project_media_doc(brand_dir)
    assets = []
    for row in media.get("assets") or []:
        if not isinstance(row, dict) or not row.get("file"):
            continue
        entry = {
            "filename": row["file"],
            "useCase": row.get("tagGuess") or "decorative",
            "assetKind": (row.get("assetSemantics") or {}).get("kind"),
        }
        if isinstance(row.get("treatmentDefaults"), dict):
            entry["mediaTreatment"] = row["treatmentDefaults"]
        assets.append(entry)
    return json.dumps({
        "schemaVersion": "assets-tagged.v1",
        "note": (
            "Deterministic renderer-compat projection of media-assets-draft.yaml "
            "plus authored tagRules."
        ),
        "assets": assets,
    }, indent=2, ensure_ascii=False) + "\n"


def _run_projections(brand_dir: Path, derive_outputs: Callable) -> None:
    from author_brand import AuthorBlocked, atomic_write_group
    from contract_projection import (
        project_chrome_labels,
        project_contract_complete,
        project_copy_labels,
    )
    foundation_doc = yaml.safe_load((brand_dir / "brand.yaml").read_text()) or {}
    chrome_doc = yaml.safe_load((brand_dir / "brand-chrome.yaml").read_text()) or {}
    library_path = brand_dir / "layout-library.yaml"
    library_doc = yaml.safe_load(library_path.read_text()) or {} \
        if library_path.is_file() else {}
    if not isinstance(foundation_doc, dict) or not isinstance(chrome_doc, dict):
        raise AuthorBlocked("projection inputs brand.yaml/brand-chrome.yaml must be mappings")
    if not isinstance(library_doc, dict):
        raise AuthorBlocked("projection input layout-library.yaml must be a mapping")
    copy_path = brand_dir / "section-copy.yaml"
    copy_doc = yaml.safe_load(copy_path.read_text()) or {} if copy_path.is_file() else {}
    layout_copy = copy_doc.get("layoutCopy") if isinstance(copy_doc, dict) else None
    if isinstance(layout_copy, dict):
        consumed_roots: set[str] = set()
        for pattern in library_doc.get("patterns") or []:
            if not isinstance(pattern, dict) or not pattern.get("id"):
                continue
            roots: list[str] = []
            for slot in ((pattern.get("contentShape") or {}).get("slots") or []):
                if not isinstance(slot, dict):
                    continue
                refs = slot.pop("sourceCopy", None)
                refs = refs if isinstance(refs, list) else [refs]
                for ref in refs:
                    match = re.match(r"^layoutCopy\.([^.]+)", str(ref or ""))
                    if match and match.group(1) not in roots:
                        roots.append(match.group(1))
            if len(roots) == 1 and isinstance(layout_copy.get(roots[0]), dict):
                layout_copy[str(pattern["id"])] = copy.deepcopy(layout_copy[roots[0]])
                consumed_roots.add(roots[0])
        for root in consumed_roots:
            if root not in {str(row.get("id")) for row in library_doc.get("patterns") or []
                            if isinstance(row, dict)}:
                layout_copy.pop(root, None)
    foundation_doc = _normalize_brand_identity(foundation_doc)
    chrome_doc, chrome_label_audit = project_chrome_labels(brand_dir, chrome_doc)
    copy_doc, copy_label_audit = project_copy_labels(brand_dir, copy_doc)
    merged_doc = _normalize_brand_identity(_deep_merge(foundation_doc, chrome_doc))
    merged_doc, library_doc, contract_audit = project_contract_complete(
        brand_dir, merged_doc, library_doc)
    # MEASURED PER-COMPONENT GEOMETRY (2026-07): fill absent measured band/rhythm/
    # media-aspect facts on every extracted pattern from the lane's OWN grounding +
    # section-rect evidence, so a slot never ships as name/role-only when the evidence
    # carries geometry. Fill-absent-only + provenance-gated (a pattern with no
    # ``section-NN`` provenance or already-authored facts is untouched — the hand-
    # authored v2/remote baselines are byte-identical).
    try:
        from measured_geometry import enrich_layout_library, FIDELITY_FIELDS
        geometry_audit = enrich_layout_library(
            library_doc, brand_dir, fields=FIDELITY_FIELDS)
    except Exception as exc:  # never fail the projection on the enrichment
        geometry_audit = {"_error": f"{type(exc).__name__}: {exc}"}
    contract_audit = chrome_label_audit + copy_label_audit + contract_audit
    atomic_write_group(brand_dir, {
        "brand.yaml": yaml.safe_dump(
            merged_doc, sort_keys=False,
            allow_unicode=True, width=100),
        "layout-library.yaml": yaml.safe_dump(
            library_doc, sort_keys=False,
            allow_unicode=True, width=100),
        "brand-chrome.yaml": yaml.safe_dump(
            chrome_doc, sort_keys=False, allow_unicode=True, width=100),
        "section-copy.yaml": yaml.safe_dump(
            copy_doc, sort_keys=False, allow_unicode=True, width=100),
        "contract-projection-audit.json": json.dumps(
            {
                "schemaVersion": "contract-projection-audit.v1",
                "entries": contract_audit,
                "measuredGeometry": geometry_audit,
            },
            indent=2, ensure_ascii=False) + "\n",
        "media-assets.yaml": _project_media(brand_dir),
        "assets-tagged.json": _project_assets_tagged(brand_dir),
    })
    derive_outputs(brand_dir)
    voice_doc = yaml.safe_load((brand_dir / "voice-facts.yaml").read_text()) or {}
    voice_md = "# Voice facts\n\n```yaml\n" + yaml.safe_dump(
        voice_doc, sort_keys=False, allow_unicode=True).rstrip() + "\n```\n"
    atomic_write_group(brand_dir, {"voice.md": voice_md})


def apply_mechanical_repairs(brand_dir: Path, errors: list[str]) -> list[dict]:
    """Apply only lossless canonical-shape derivations named by current errors."""
    from author_brand import atomic_write_group
    applied: list[dict] = []
    error_checks = {_error_check(error) for error in errors}
    writes: dict[str, str] = {}

    if "C4" in error_checks:
        path = brand_dir / "section-copy.yaml"
        doc = _load(path) or {}
        allowed = {
            "sectionCopy", "layoutCopy", "layoutImages", "defaultArt", "wildcardCopy",
        }
        removed = sorted(set(doc) - allowed)
        if removed:
            doc = {key: value for key, value in doc.items() if key in allowed}
            writes[path.name] = yaml.safe_dump(
                doc, sort_keys=False, allow_unicode=True, width=100)
            applied.append({
                "check": "C4", "path": "/", "file": path.name,
                "kind": "canonical-top-level-projection", "removedKeys": removed,
            })

    if "C17" in error_checks:
        path = brand_dir / "section-copy.yaml"
        doc = _load(path) or {}
        changed = 0
        for payload in (doc.get("layoutCopy") or {}).values():
            if not isinstance(payload, dict):
                continue
            for item in payload.get("items") or []:
                if not isinstance(item, dict) or item.get("bodyNotObserved") is True:
                    continue
                if not str(item.get("body") or item.get("text") or "").strip():
                    item["bodyNotObserved"] = True
                    changed += 1
        if changed:
            writes[path.name] = yaml.safe_dump(
                doc, sort_keys=False, allow_unicode=True, width=100)
            applied.append({
                "check": "C17", "path": "/layoutCopy", "file": path.name,
                "kind": "explicit-empty-body-absence", "entries": changed,
            })

    brand_path = brand_dir / "brand.yaml"
    chrome_path = brand_dir / "brand-chrome.yaml"
    brand = _load(brand_path) or {}
    chrome = _load(chrome_path) or {}
    if "C7" in error_checks:
        social = (chrome.get("footer") or {}).get("social")
        icons = social.get("icons") if isinstance(social, dict) else None
        if isinstance(icons, list) and all(
                isinstance(row, dict) and row.get("href")
                and (row.get("network") or row.get("label")) for row in icons):
            projected = [
                {
                    "network": row.get("network") or row.get("label"),
                    "href": row["href"],
                    **{key: row[key] for key in ("kind", "icon", "box")
                       if row.get(key) is not None},
                }
                for row in icons
            ]
            chrome = copy.deepcopy(chrome)
            chrome.setdefault("footer", {})["social"] = projected
            writes[chrome_path.name] = yaml.safe_dump(
                chrome, sort_keys=False, allow_unicode=True, width=100)
            applied.append({
                "check": "C7", "path": "/footer/social", "file": chrome_path.name,
                "kind": "canonical-list-projection",
                "source": "footer.social.icons",
            })

    if "C13" in error_checks:
        token_motion = (brand.get("tokens") or {}).get("motion")
        legacy_motion = brand.get("motion")
        legacy_value = legacy_motion.get("value") \
            if isinstance(legacy_motion, dict) else None
        if not isinstance(token_motion, dict) and isinstance(legacy_value, dict):
            brand = copy.deepcopy(brand)
            brand.setdefault("tokens", {})["motion"] = {
                **legacy_value,
                "projectionSource": "brand.yaml#motion.value",
            }
            writes[brand_path.name] = yaml.safe_dump(
                brand, sort_keys=False, allow_unicode=True, width=100)
            applied.append({
                "check": "C13", "path": "/tokens/motion", "file": brand_path.name,
                "kind": "canonical-field-projection",
                "source": "motion.value",
            })

    if writes:
        atomic_write_group(brand_dir, writes)
    return applied


def _stage_record(stage: Stage, status: str, **extra) -> dict:
    return {
        "name": stage.name,
        "status": status,
        "dependencies": list(stage.dependencies),
        "outputs": list(stage.outputs),
        "maxInputBytes": stage.max_input_bytes,
        "maxOutputTokens": stage.max_output_tokens,
        "timeoutS": stage.timeout_s,
        "retries": 0,
        **extra,
    }


def author_brand_staged(
    brand_dir: Path, *, model: str, reasoning_effort: str, timeout: float,
    max_repairs: int, max_tokens: int, force: bool, source_url: str | None,
    provider, validator: Callable, log=print, force_stage: str | None = None,
    derive_outputs: Callable,
):
    from author_brand import (
        AuthorBlocked, AuthorResult, _provider_available, _write_result,
        atomic_write_group, parse_model_files,
    )
    started = time.time()
    brand_dir = Path(brand_dir)
    validate_author_inputs(brand_dir)
    if force_stage and force_stage not in STAGE_BY_NAME:
        raise AuthorBlocked(f"unknown author stage {force_stage!r}")
    if not force and not force_stage and all(
            (brand_dir / name).is_file() for name in EXPECTED_OUTPUTS):
        existing_report = validator(brand_dir)
        if getattr(existing_report, "ok", False):
            result = AuthorResult(
                True, "completed", "valid authored artifacts already exist",
                model=model, skipped=True,
                warnings=list(getattr(existing_report, "warnings", [])),
                outputs=list(EXPECTED_OUTPUTS), duration_s=time.time() - started)
            result.stages = [
                _stage_record(stage, "completed", skipped=True, inputBytes=0,
                              durationS=0.0) for stage in STAGES
            ]
            _write_result(brand_dir, result)
            log("[skip] author DAG: complete C1-C28-valid artifacts exist")
            return result
    if provider is None and not _provider_available():
        result = AuthorResult(False, "blocked", "ANTHROPIC_API_KEY not available",
                              model=model, duration_s=time.time() - started)
        _write_result(brand_dir, result)
        raise AuthorBlocked(result.reason)

    checkpoint = _read_checkpoint(brand_dir)
    checkpoint.setdefault("stages", {})
    usage: dict = {}
    stage_reports: list[dict] = []
    calls = 0
    effective_model = model
    force_names = {force_stage} if force_stage else set()
    if force:
        force_names = {stage.name for stage in STAGES}
    if force_stage:
        # A forced node invalidates all descendants.
        seen = False
        for stage in STAGES:
            if stage.name == force_stage:
                seen = True
            if seen:
                force_names.add(stage.name)

    try:
        for stage in MODEL_STAGES:
            dep_failed = [dep for dep in stage.dependencies
                          if checkpoint["stages"].get(dep, {}).get("status") != "completed"]
            if dep_failed:
                raise AuthorBlocked(
                    f"author stage {stage.name} dependencies incomplete: {', '.join(dep_failed)}")
            if stage.name not in force_names and stage_valid(brand_dir, stage) and \
                    checkpoint["stages"].get(stage.name, {}).get("status") == "completed":
                record = _stage_record(stage, "completed", skipped=True,
                                       inputBytes=checkpoint["stages"][stage.name].get("inputBytes"),
                                       durationS=0.0)
                stage_reports.append(record)
                log(f"[skip] author stage {stage.name}: valid checkpoint")
                continue

            bundle = build_stage_bundle(brand_dir, stage.name, source_url)
            system = _stage_system(stage)
            user = _prompt(stage, bundle)
            input_bytes = _input_size(system, user)
            if input_bytes > stage.max_input_bytes:
                raise AuthorBlocked(
                    f"author stage {stage.name} input {input_bytes} bytes exceeds "
                    f"cap {stage.max_input_bytes}")
            stage_timeout = min(timeout, stage.timeout_s)
            stage_tokens = min(max_tokens, stage.max_output_tokens)
            if stage.name == "media":
                tag_count = len(bundle["mediaEvidence"]["tagVocabulary"])
                stage_tokens = min(stage_tokens, max(1_800, 1_000 + 350 * tag_count))
            checkpoint["stages"][stage.name] = _stage_record(
                stage, "running", inputBytes=input_bytes, startedAt=_now())
            checkpoint["stages"][stage.name]["requestedOutputTokens"] = stage_tokens
            _write_checkpoint(brand_dir, checkpoint)
            log(f"[run ] author stage {stage.name}: {input_bytes} bytes, "
                f"timeout={stage_timeout:g}s")
            t0 = time.time()
            calls += 1
            raw, call_usage, effective_model = _call(
                provider, model=model, reasoning_effort=reasoning_effort,
                system=system, user=user, max_tokens=stage_tokens,
                timeout=stage_timeout)
            _usage_add(usage, call_usage)
            checkpoint["stages"][stage.name].update({
                "durationS": round(time.time() - t0, 3),
                "model": effective_model,
                "usage": call_usage,
            })
            _write_checkpoint(brand_dir, checkpoint)
            files = parse_model_files(raw, stage.outputs)
            validate_stage_files(files)
            validate_stage_joins(brand_dir, files)
            if stage.name == "media":
                vocabulary = {
                    row["tagGuess"] for row in bundle["mediaEvidence"]["tagVocabulary"]
                }
                _validate_media_guidance(files["media-guidance.yaml"], vocabulary)
            atomic_write_group(brand_dir, files)
            duration = time.time() - t0
            record = _stage_record(
                stage, "completed", skipped=False, inputBytes=input_bytes,
                durationS=round(duration, 3), model=effective_model, usage=call_usage,
                requestedOutputTokens=stage_tokens,
                completedAt=_now())
            checkpoint["stages"][stage.name] = record
            _write_checkpoint(brand_dir, checkpoint)
            stage_reports.append(record)

        projection = STAGE_BY_NAME["projections"]
        t0 = time.time()
        _run_projections(brand_dir, derive_outputs)
        projection_record = _stage_record(
            projection, "completed", skipped=False, inputBytes=0,
            durationS=round(time.time() - t0, 3), model="deterministic",
            usage={})
        checkpoint["stages"]["projections"] = projection_record
        _write_checkpoint(brand_dir, checkpoint)
        stage_reports.append(projection_record)

        report = validator(brand_dir)
        mechanical = apply_mechanical_repairs(
            brand_dir, list(getattr(report, "errors", [])))
        if mechanical:
            _run_projections(brand_dir, derive_outputs)
            report = validator(brand_dir)
            checkpoint.setdefault("mechanicalRepairs", []).append({
                "completedAt": _now(),
                "repairs": mechanical,
                "postValidationErrors": len(getattr(report, "errors", [])),
                "postValidationWarnings": len(getattr(report, "warnings", [])),
            })
            _write_checkpoint(brand_dir, checkpoint)
        repairs = 0
        while not getattr(report, "ok", False) and repairs < max_repairs:
            repairs += 1
            groups = group_repair_errors(list(getattr(report, "errors", [])))
            bounded_groups: list[RepairGroup] = []
            for group in groups:
                bounded_groups.extend(split_repair_group_to_cap(brand_dir, group))
            for group in bounded_groups:
                owner = group.owner
                stage = STAGE_BY_NAME[owner]
                bundle = build_repair_bundle(brand_dir, group)
                system = _repair_system(group)
                user = _repair_prompt(bundle)
                input_bytes = _input_size(system, user)
                if input_bytes > REPAIR_INPUT_CAP_BYTES:
                    raise AuthorBlocked(
                        f"author repair group {group.group_id} input {input_bytes} "
                        f"bytes exceeds cap {REPAIR_INPUT_CAP_BYTES}")
                t0 = time.time()
                calls += 1
                running_entry = {
                    "round": repairs,
                    "groupId": group.group_id,
                    "schemaPath": group.schema_path,
                    "checks": [_error_check(e) for e in group.errors],
                    "errors": list(group.errors),
                    "status": "running",
                    "inputBytes": input_bytes,
                    "inputCapBytes": REPAIR_INPUT_CAP_BYTES,
                    "startedAt": _now(),
                }
                checkpoint["stages"][owner].setdefault(
                    "pathRepairs", []).append(running_entry)
                _write_checkpoint(brand_dir, checkpoint)
                repair_output_tokens = 16_000 \
                    if group.schema_path == "/blocks" else (
                        10_000 if group.schema_path == "/layouts" else 8_000)
                raw, call_usage, effective_model = _call(
                    provider, model=model, reasoning_effort=reasoning_effort,
                    system=system, user=user,
                    max_tokens=min(
                        max_tokens, stage.max_output_tokens, repair_output_tokens),
                    timeout=min(timeout, stage.timeout_s))
                _usage_add(usage, call_usage)
                running_entry.update({
                    "model": effective_model,
                    "usage": call_usage,
                    "responseBytes": len(raw.encode()),
                })
                _write_checkpoint(brand_dir, checkpoint)
                originals = {
                    name: (brand_dir / name).read_text()
                    for name in _repair_allowed_targets(group)
                    if (brand_dir / name).is_file()
                }
                try:
                    touched = parse_and_apply_repair(brand_dir, group, raw)
                    _run_projections(brand_dir, derive_outputs)
                    report = validator(brand_dir)
                except Exception as exc:
                    if originals:
                        atomic_write_group(brand_dir, originals)
                        try:
                            _run_projections(brand_dir, derive_outputs)
                        except Exception:
                            pass
                    running_entry.update({
                        "status": "blocked",
                        "reason": str(exc),
                        "rolledBack": True,
                        "durationS": round(time.time() - t0, 3),
                        "completedAt": _now(),
                    })
                    _write_checkpoint(brand_dir, checkpoint)
                    raise
                running_entry.update({
                    "status": "completed",
                    "touchedFiles": touched,
                    "durationS": round(time.time() - t0, 3),
                    "model": effective_model,
                    "usage": call_usage,
                    "postValidationErrors": len(getattr(report, "errors", [])),
                    "postValidationWarnings": len(getattr(report, "warnings", [])),
                    "completedAt": _now(),
                })
                _write_checkpoint(brand_dir, checkpoint)

        errors = list(getattr(report, "errors", []))
        warnings = list(getattr(report, "warnings", []))
        result = AuthorResult(
            not errors, "completed" if not errors else "needs_iteration",
            "" if not errors else f"{len(errors)} C1-C28 validation error(s) remain "
            f"after {repairs} repair round(s)",
            model=effective_model, calls=calls, repairs=repairs,
            skipped=all(row.get("skipped") for row in stage_reports if row["name"] != "projections"),
            errors=errors, warnings=warnings, usage=usage,
            outputs=[name for name in EXPECTED_OUTPUTS if (brand_dir / name).is_file()],
            duration_s=time.time() - started)
        result.stages = stage_reports
    except Exception as exc:
        failed_name = next((s.name for s in MODEL_STAGES
                            if checkpoint["stages"].get(s.name, {}).get("status") == "running"), None)
        if failed_name:
            checkpoint["stages"][failed_name]["status"] = "blocked"
            checkpoint["stages"][failed_name]["reason"] = str(exc)
            checkpoint["stages"][failed_name]["completedAt"] = _now()
            _write_checkpoint(brand_dir, checkpoint)
        result = AuthorResult(
            False, "blocked", str(exc), model=effective_model, calls=calls,
            usage=usage, outputs=[name for name in EXPECTED_OUTPUTS
                                  if (brand_dir / name).is_file()],
            duration_s=time.time() - started)
        result.stages = list(checkpoint.get("stages", {}).values())

    _write_result(brand_dir, result)
    if not result.ok:
        raise AuthorBlocked(result.reason)
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider-worker", nargs=2, metavar=("REQUEST", "RESPONSE"))
    args = parser.parse_args(argv)
    if args.provider_worker:
        return _provider_worker(Path(args.provider_worker[0]), Path(args.provider_worker[1]))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
