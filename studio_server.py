#!/usr/bin/env python3
"""Design System Studio — a real end-to-end flow over the extractor pipeline.

A zero-dependency local web app (stdlib http.server only) that lets you:
  • Add a project  → paste a URL + drop a screenshot
  • Run it         → kicks off run_pipeline.py in the background (live log)
  • See everything → generated site outputs, the surface/component CONTRACT,
                     the design-system doc, and the extracted + role-grouped
                     brand ASSETS harvested from the live URL.

It also serves the existing static viewer (viewer.html, runs/**, screenshots/**)
so "Open full comparison viewer" works from the same origin.

Run:
    ./start-studio.sh                               # serves on :1500 (viewer + studio)
    ./venv/bin/python studio_server.py              # same; override with STUDIO_PORT
    STUDIO_PORT=9000 ./venv/bin/python studio_server.py

Nothing here calls an LLM directly; the pipeline subprocess does, using the
keys already in .env.local. Asset harvesting fetches the public URL's HTML.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import ssl
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse
from urllib.request import Request, urlopen

import yaml

PROJECT_DIR = Path(__file__).resolve().parent
RUNS_DIR = PROJECT_DIR / "runs"
SCREENSHOTS_DIR = PROJECT_DIR / "screenshots"
STUDIO_DIR = RUNS_DIR / ".studio"
BASE_CONFIG = PROJECT_DIR / "config-anthropic.yaml"
PY = sys.executable

sys.path.insert(0, str(PROJECT_DIR / "tools"))
sys.path.insert(0, str(PROJECT_DIR / "src"))
sys.path.insert(0, str(PROJECT_DIR / "brand_pipeline"))

# In-memory job registry (also mirrored to disk for resilience across restarts).
JOBS: dict[str, dict] = {}
JOBS_LOCK = threading.Lock()

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


# ── helpers ──────────────────────────────────────────────────────────────────
def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return s or "project"


def unique_version(name: str) -> str:
    base = slugify(name)
    candidate = base
    n = 2
    while (RUNS_DIR / candidate).exists() or (SCREENSHOTS_DIR / candidate).exists():
        candidate = f"{base}-{n}"
        n += 1
    return candidate


def read_text(path: Path, limit: int | None = None) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
        return text[:limit] if limit else text
    except Exception:
        return ""


def run_complete_status(version: str) -> str | None:
    """Status of run_complete from run-steps.json, if present."""
    vdir = RUNS_DIR / version
    if not vdir.exists():
        return None
    for item_dir in sorted(p for p in vdir.iterdir() if p.is_dir() and not p.name.startswith(".")):
        path = item_dir / "single" / "run-steps.json"
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text())
            return (data.get("steps") or {}).get("run_complete", {}).get("status")
        except Exception:
            continue
    return None


def pipeline_status(version: str, *, has_site: bool, created: str) -> str:
    """failed | ready | building | idle — for dashboard badges."""
    if run_complete_status(version) == "failed":
        return "failed"
    if has_site:
        return "ready"
    if created:
        return "building"
    return "idle"


def resolve_shots_dir(version: str) -> Path | None:
    """Screenshots dir for run_pipeline: screenshots/{version} or copy from run item."""
    shots = SCREENSHOTS_DIR / version
    if shots.is_dir():
        if any(p.is_file() and p.suffix.lower() in IMAGE_EXTS for p in shots.iterdir()):
            return shots
    vdir = RUNS_DIR / version
    if not vdir.exists():
        return None
    for item_dir in sorted(p for p in vdir.iterdir() if p.is_dir() and not p.name.startswith(".")):
        shot = next(iter(sorted(item_dir.glob("screenshot.*"))), None)
        if not shot:
            continue
        shots.mkdir(parents=True, exist_ok=True)
        dest = shots / shot.name
        if not dest.exists():
            shutil.copy2(shot, dest)
        return shots
    return None


def project_meta(version: str) -> dict:
    vdir = RUNS_DIR / version
    meta_path = vdir / "studio-project.json"
    meta = {}
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text())
        except Exception:
            meta = {}
    items = []
    thumb = ""
    if vdir.exists():
        for item_dir in sorted(p for p in vdir.iterdir() if p.is_dir() and not p.name.startswith(".")):
            shot = next(iter(sorted(item_dir.glob("screenshot.*"))), None)
            single = item_dir / "single"
            if not shot and not single.exists():
                continue
            if shot and not thumb:
                thumb = "/" + str(shot.relative_to(PROJECT_DIR)).replace("\\", "/")
            items.append({"name": item_dir.name, "has_shot": bool(shot)})
    # Fall back to the local-folder input (screenshots/<version>/) when no run
    # item had a screenshot.* — mirrors the project_detail left-lane fix.
    if not thumb:
        shots = SCREENSHOTS_DIR / version
        if shots.is_dir():
            imgs = [
                p
                for p in sorted(shots.iterdir())
                if p.is_file()
                and p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".avif"}
            ]
            vkey = version.lower().replace("-", "").replace("_", "")
            pick = next(
                (p for p in imgs if vkey in p.stem.lower().replace("-", "").replace("_", "")),
                None,
            ) or (imgs[0] if imgs else None)
            if pick:
                thumb = "/" + str(pick.relative_to(PROJECT_DIR)).replace("\\", "/")
    has_site = any((RUNS_DIR / version).glob("*/single/site-*.html"))
    created = meta.get("created", "")
    return {
        "version": version,
        "url": meta.get("url", ""),
        "title": meta.get("title", version),
        "created": created,
        "job_id": meta.get("job_id", ""),
        "items": items,
        "thumb": thumb,
        "has_site": bool(has_site),
        "pipeline_status": pipeline_status(version, has_site=bool(has_site), created=created),
        "brand_review": brand_review_summary(brand_renders(version)),
        "catalog": catalog_summary(version),
    }


def list_projects() -> list[dict]:
    """Studio-created projects first (by created desc), then any other runs."""
    studio, others = [], []
    if not RUNS_DIR.exists():
        return []
    for vdir in RUNS_DIR.iterdir():
        if not vdir.is_dir() or vdir.name.startswith("."):
            continue
        m = project_meta(vdir.name)
        (studio if m["created"] else others).append(m)
    studio.sort(key=lambda m: m["created"], reverse=True)
    others.sort(key=lambda m: m["version"], reverse=True)
    return studio + others


def first_item_dir(version: str) -> Path | None:
    vdir = RUNS_DIR / version
    if not vdir.exists():
        return None
    return next(
        (p for p in sorted(vdir.iterdir()) if p.is_dir() and (p / "single").exists()),
        None,
    )


def load_studio_config(version: str) -> dict:
    """Merged BASE_CONFIG + per-project runs/.studio/{version}.config.yaml."""
    data: dict = {}
    if BASE_CONFIG.exists():
        data = yaml.safe_load(BASE_CONFIG.read_text()) or {}
    cfg_path = STUDIO_DIR / f"{version}.config.yaml"
    if cfg_path.exists():
        data.update(yaml.safe_load(cfg_path.read_text()) or {})
    return data


def framework_first_mode(version: str) -> bool:
    cfg = load_studio_config(version)
    fw = cfg.get("framework-generation-enabled", True)
    vanilla = cfg.get("vanilla-site-generation-enabled", False)
    return bool(fw) and not bool(vanilla)


def site_rel(version: str, item: str, provider: str, *, framework: bool = False) -> str:
    single = RUNS_DIR / version / item / "single"
    suffix = "-framework" if framework else ""
    applied = single / f"site-{provider}{suffix}.assets-applied.html"
    plain = single / f"site-{provider}{suffix}.html"
    chosen = applied if applied.exists() else (plain if plain.exists() else None)
    if not chosen:
        return ""
    return "/" + str(chosen.relative_to(PROJECT_DIR)).replace("\\", "/")


def compose_pages(version: str) -> list[dict]:
    """Composed campaign pages for the lane dropdown.

    Discovers every `runs/<version>/brand/compose/<brief>/index.html` (the AD-2
    page composer output) and returns selectable lane options pointing at the HTML
    via the existing runs/** static route. Generic over brand + brief: any project
    with a composed page auto-appears; degrades to [] when none exist.
    """
    compose_dir = RUNS_DIR / version / "brand" / "compose"
    if not compose_dir.is_dir():
        return []
    out: list[dict] = []
    for brief_dir in sorted(p for p in compose_dir.iterdir() if p.is_dir()):
        index = brief_dir / "index.html"
        if not index.exists():
            continue
        out.append(
            {
                "label": f"Composed: {brief_dir.name}",
                "url": "/" + str(index.relative_to(PROJECT_DIR)).replace("\\", "/"),
            }
        )
    return out


# Friendly labels for the variance-dial hero variants (render_hero_variants.py).
_VARIANT_LABELS = {
    "a": "Variant A — Safe",
    "b": "Variant B — Bold",
    "c": "Variant C — Wildcard",
}


def variant_pages(version: str) -> list[dict]:
    """Hero variance-dial variants for the lane dropdown.

    Discovers `runs/<version>/brand/variants/<name>/index.html` (e.g. the
    render_hero_variants.py output, or any other variant dir) and returns selectable
    lane options pointing at the HTML via the existing runs/** static route. Mirrors
    compose_pages(): generic over brand, degrades to [] when no variants exist.

    Labels: a `label.txt` file inside a variant dir (first non-empty line) wins, so
    arbitrary-named variant dirs can carry a human name; otherwise the a|b|c friendly
    names are used, falling back to `Variant <NAME>`. Follows symlinked variant dirs.
    """
    variants_dir = RUNS_DIR / version / "brand" / "variants"
    if not variants_dir.is_dir():
        return []
    out: list[dict] = []
    for sub in sorted(p for p in variants_dir.iterdir() if p.is_dir()):
        index = sub / "index.html"
        if not index.exists():
            continue
        label = _VARIANT_LABELS.get(sub.name.lower(), f"Variant {sub.name.upper()}")
        label_file = sub / "label.txt"
        if label_file.is_file():
            custom = next((ln.strip() for ln in read_text(label_file).splitlines() if ln.strip()), "")
            if custom:
                label = custom
        out.append(
            {
                "label": label,
                "url": "/" + str(index.relative_to(PROJECT_DIR)).replace("\\", "/"),
            }
        )
    return out


def hero_gallery_lanes(version: str) -> list[dict]:
    """Experiment lane: the WoodWave ANCHORED hero-variants page — the measured original
    hero first ("Original (measured)"), then 5 single-axis variations of it, each generated
    live via brand_pipeline/generate_composition.py SEEDED with the measured project pattern
    `hero-display-over-staggered-media` (novelty:adapt) and passed through the drift-band +
    onbrand_check --composition gates. SUPERSEDES the earlier free-invention hero gallery
    (experiments/woodwave-hero-gallery/page/), which is deliberately not surfaced.

    Lives in a self-contained experiment dir (experiments/woodwave-hero-gallery/
    page-anchored/) rather than under runs/, and is served by the static handler
    (PROJECT_DIR root). Scoped to the woodwave project; degrades to [] when the page hasn't
    been built yet. The vNN · MM-DD HH:MM version prefix is applied dynamically by
    versioned_lanes() from the output mtime.
    """
    if version != "woodwave":
        return []
    index = PROJECT_DIR / "experiments" / "woodwave-hero-gallery" / "page-anchored" / "index.html"
    if not index.exists():
        return []
    return [{
        "label": "WoodWave — anchored hero variants (live)",
        "url": "/" + str(index.relative_to(PROJECT_DIR)).replace("\\", "/"),
    }]


def static_brand_lanes(version: str) -> list[dict]:
    """Static brand-level preview lanes for the lane dropdown.

    Mirrors compose_pages()/variant_pages() but points at fixed per-brand artifacts
    under runs/<version>/brand/. Generic over brand/version (never hardcodes one):

      - "Components preview" -> brand/components-preview/index.html
        (render_components_preview.py output); listed only when present.
      - "Exact nav/footer" -> brand/chrome/index.html
        (produced by a separate stage). Always listed so the lane exists; if that
        index.html is not present yet the URL 404s cleanly via the static handler
        (graceful, no crash) and the lane simply shows the 404 placeholder.
    """
    brand_dir = RUNS_DIR / version / "brand"

    def rel(p: Path) -> str:
        return "/" + str(p.relative_to(PROJECT_DIR)).replace("\\", "/")

    out: list[dict] = []
    preview = brand_dir / "components-preview" / "index.html"
    if preview.exists():
        out.append({"label": "Components preview", "url": rel(preview)})
    # Always expose the chrome lane; it degrades to a clean 404 when its file is
    # absent (the other worker produces it), rather than disappearing or crashing.
    chrome = brand_dir / "chrome" / "index.html"
    out.append({"label": "Exact nav/footer", "url": rel(chrome)})
    return out


# Matches a previously-applied version prefix so relabeling is idempotent:
# "v07 · 07-01 20:08 · <name>" → strips back to "<name>" before re-prefixing.
_VERSION_PREFIX_RE = re.compile(r"^v\d+\s·\s\d{2}-\d{2}\s\d{2}:\d{2}\s·\s")


def _strip_version_prefix(label: str) -> str:
    """Remove an existing `vNN · MM-DD HH:MM · ` prefix (idempotent relabeling)."""
    return _VERSION_PREFIX_RE.sub("", label or "").strip()


def _lane_mtime(url: str) -> float:
    """Recency signal for a lane: mtime of its rendered output file.

    `url` is a site-relative path (e.g. "/runs/woodwave/brand/.../index.html").
    Returns 0.0 when the file is missing so absent lanes sort as oldest and never
    crash the payload.
    """
    if not url:
        return 0.0
    try:
        return (PROJECT_DIR / url.lstrip("/")).stat().st_mtime
    except OSError:
        return 0.0


def versioned_lanes(raw: list[dict]) -> list[dict]:
    """Attach a recency version prefix to every lane and return them newest-first.

    Each input lane is `{"label", "url"}`. We rank all lanes by the mtime of their
    rendered output (oldest→newest) and assign a zero-padded sequential vNN so the
    HIGHEST vNN is the MOST CURRENT run. Labels become:

        vNN · MM-DD HH:MM · <existing descriptive name>

    Ordering is made newest-first by sorting on mtime descending here (server-side),
    so it does not depend on alphabetical label order. Idempotent: any existing
    `vNN · … · ` prefix on the incoming label is stripped before re-prefixing, so
    re-running never stacks prefixes.
    """
    lanes = [
        {"label": _strip_version_prefix(l["label"]), "url": l["url"], "mtime": _lane_mtime(l["url"])}
        for l in raw
        if l.get("url")
    ]
    total = len(lanes)
    pad = max(2, len(str(total)))
    # Ascending by recency → oldest gets v01, newest gets the highest number. The
    # `url` tiebreaker gives a deterministic total order when two outputs share an
    # mtime (e.g. a batch regeneration writes several files in the same instant).
    ranked = sorted(lanes, key=lambda x: (x["mtime"], x["url"]))
    for i, lane in enumerate(ranked):
        n = i + 1
        if lane["mtime"] > 0:
            ts = time.strftime("%m-%d %H:%M", time.localtime(lane["mtime"]))
        else:
            ts = "--??"
        lane["label"] = f"v{n:0{pad}d} · {ts} · {lane['label']}"
    # Newest-first for the dropdown: reverse the SAME ranked list so display order is
    # the exact inverse of the vNN assignment (highest vNN always at top). A second
    # independent descending sort would NOT reverse tied-mtime groups, so we reverse.
    return [{"label": l["label"], "url": l["url"]} for l in reversed(ranked)]


_HEX_RE = re.compile(r"^#?[0-9a-fA-F]{3,8}$")


def _is_hex(value) -> bool:
    return isinstance(value, str) and bool(_HEX_RE.match(value.strip()))


def parse_design_tokens(design_system_md: str) -> dict:
    """Parse the design-system.md YAML front matter into a clean, structured dict
    that the client renders as a visual gallery (the "Visual" sidebar tab).

    Returns {} when no usable front matter / tokens are present. Parsing the YAML
    server-side keeps the client free of YAML re-parsing and lets data_json carry
    clean JSON.
    """
    text = (design_system_md or "").lstrip()
    if not text.startswith("---"):
        return {}
    # Front matter lives between the first pair of `---` fences.
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    try:
        data = yaml.safe_load(parts[1]) or {}
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}

    tokens = data.get("tokens") if isinstance(data.get("tokens"), dict) else {}
    metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}

    out: dict = {
        "name": metadata.get("name") or "",
        "description": metadata.get("description") or "",
    }

    # ── color swatches grouped by category (surface, text, border, accent, …) ──
    color_groups = []
    color = tokens.get("color") if isinstance(tokens.get("color"), dict) else {}
    for category, entries in color.items():
        if not isinstance(entries, dict):
            continue
        swatches = [
            {"name": name, "path": f"color.{category}.{name}", "hex": value.strip()}
            for name, value in entries.items()
            if _is_hex(value)
        ]
        if swatches:
            color_groups.append({"category": category, "swatches": swatches})
    out["colorGroups"] = color_groups

    # ── surfaces, with their on-surface text colors for legible text samples ──
    surfaces = []
    src_surfaces = data.get("surfaces") if isinstance(data.get("surfaces"), dict) else {}
    for sname, s in src_surfaces.items():
        if not isinstance(s, dict) or not _is_hex(s.get("value")):
            continue
        stext = s.get("text") if isinstance(s.get("text"), dict) else {}
        surfaces.append(
            {
                "name": sname,
                "value": str(s.get("value")).strip(),
                "role": s.get("role") or "",
                "text": {
                    "default": stext.get("default") if _is_hex(stext.get("default")) else "",
                    "muted": stext.get("muted") if _is_hex(stext.get("muted")) else "",
                    "accent": stext.get("accent") if _is_hex(stext.get("accent")) else "",
                },
                "border": s.get("border") if _is_hex(s.get("border")) else "",
            }
        )
    out["surfaces"] = surfaces

    # ── typography roles (skip scalar entries like `note`) ──
    typography = []
    src_typo = data.get("typography") if isinstance(data.get("typography"), dict) else {}
    for tname, t in src_typo.items():
        if not isinstance(t, dict):
            continue
        typography.append(
            {
                "key": tname,
                "fontFamily": t.get("fontFamily") or "",
                "category": t.get("fontFamilyCategory") or "",
                "fontSize": str(t.get("fontSize") or ""),
                "fontWeight": str(t.get("fontWeight") or ""),
                "lineHeight": str(t.get("lineHeight") or ""),
                "letterSpacing": str(t.get("letterSpacing") or ""),
                "role": t.get("role") or "",
            }
        )
    out["typography"] = typography

    # ── spacing: ordered scale + named one-off tokens ──
    spacing = tokens.get("spacing") if isinstance(tokens.get("spacing"), dict) else {}
    scale = spacing.get("scale")
    out["spacingScale"] = [str(x) for x in scale] if isinstance(scale, list) else []
    out["spacingNamed"] = [
        {"name": k, "value": str(v)}
        for k, v in spacing.items()
        if k != "scale" and isinstance(v, (str, int, float))
    ]

    # ── radius + shadow ──
    radius = tokens.get("radius") if isinstance(tokens.get("radius"), dict) else {}
    out["radius"] = [
        {"name": k, "value": str(v)} for k, v in radius.items() if isinstance(v, (str, int, float))
    ]
    shadow = tokens.get("shadow") if isinstance(tokens.get("shadow"), dict) else {}
    out["shadow"] = [
        {"name": k, "value": str(v)} for k, v in shadow.items() if isinstance(v, (str, int, float))
    ]

    return out


def project_detail(version: str) -> dict:
    m = project_meta(version)
    item_dir = first_item_dir(version)
    item = item_dir.name if item_dir else (m["items"][0]["name"] if m["items"] else "")
    single = (item_dir / "single") if item_dir else None
    shot = next(iter(sorted(item_dir.glob("screenshot.*"))), None) if item_dir else None
    # Fall back to the local-folder input (screenshots/<version>/) when the run
    # item has no screenshot.* — this is the case for brands captured via the
    # "Save Page As" folder contract rather than the legacy run pipeline.
    if not shot:
        shots = SCREENSHOTS_DIR / version
        if shots.is_dir():
            imgs = [
                p
                for p in sorted(shots.iterdir())
                if p.is_file()
                and p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".avif"}
            ]
            # Prefer a file whose name matches the brand (e.g. woodwave.webp) over
            # any other captured image (e.g. an unrelated catalog screenshot).
            vkey = version.lower().replace("-", "").replace("_", "")
            shot = next(
                (p for p in imgs if vkey in p.stem.lower().replace("-", "").replace("_", "")),
                None,
            ) or (imgs[0] if imgs else None)

    def doc(name: str) -> str:
        return read_text(single / name) if single else ""

    vdir = RUNS_DIR / version

    def vdoc(name: str) -> str:
        p = vdir / name
        return read_text(p) if p.exists() else ""

    # Combine every prompt the pipeline persisted into one scrollable doc.
    prompt_files = [
        ("System / design-system prompt", "system-prompt.md"),
        ("Structural analysis prompt", "structural-analysis-prompt.md"),
        ("Grounding sync prompt", "grounding-sync-prompt.md"),
        ("Site style sync prompt", "site-style-sync-prompt.md"),
        ("Website generation prompt", "website-gen-framework-prompt.md"),
        ("Website generation prompt (vanilla)", "website-gen-prompt.md"),
        ("Design-system review prompt", "design-system-review-prompt.md"),
        ("Design-system conversion review prompt", "design-system-conversion-review-prompt.md"),
        ("Section inventory prompt", "section-inventory-prompt.md"),
    ]
    prompt_parts = []
    for label, fname in prompt_files:
        body = vdoc(fname)
        if body.strip():
            prompt_parts.append(f"===== {label} ({fname}) =====\n\n{body.strip()}")
    prompts = "\n\n\n".join(prompt_parts)

    # All info artifacts, combining what the pipeline viewer and project view showed.
    # Every doc the old comparison/viewer mode exposed is surfaced here so nothing
    # is lost in the unified sidebar. Empty docs are filtered out client-side.
    docs = {
        "design_system": doc("design-system.md"),
        "structural": doc("structural-analysis.md"),
        "grounding": doc("global-site-grounding.yaml"),
        "generation_input": doc("site-generation-input.md"),
        "ledger": doc("source-style-ledger.yaml"),
        "contract": doc("surface-component-contract.yaml"),
        "contract_audit": doc("surface-component-contract-audit.md"),
        "section_inventory": doc("section-inventory.md"),
        "style_audit": doc("design-system-style-audit.json"),
        "review": doc("design-system-review.md"),
        "conversion_review": doc("design-system-conversion-review.md"),
        "prompts": prompts,
        "learnings": vdoc("learnings.md"),
    }
    # Back-compat: callers/tabs that still expect a single "grounding" doc should
    # get the richest structural source if the dedicated grounding yaml is absent.
    if not docs["grounding"].strip():
        docs["grounding"] = docs["structural"]

    assets = load_assets(version)

    # Unified, recency-sorted lane list for the preview dropdowns. Every lane (the
    # framework/vanilla site outputs, hero variants, composed pages, and the static
    # brand lanes) is gathered here so a single global sort by output mtime can drive
    # both the version prefix (vNN) and the newest-first ordering. Built server-side
    # because compose/static/framework lanes have no label.txt to carry a prefix.
    _raw_site_lanes = [
        ("Claude · Framework", site_rel(version, item, "claude", framework=True) if item else ""),
        ("GPT-5.5 · Framework", site_rel(version, item, "gpt55", framework=True) if item else ""),
        ("Claude · Vanilla HTML", site_rel(version, item, "claude") if item else ""),
        ("GPT-5.5 · Vanilla HTML", site_rel(version, item, "gpt55") if item else ""),
        ("Gemini · Vanilla HTML", site_rel(version, item, "gemini") if item else ""),
    ]
    _raw_lanes = [{"label": lbl, "url": url} for lbl, url in _raw_site_lanes if url]
    _raw_lanes += variant_pages(version)
    _raw_lanes += compose_pages(version)
    _raw_lanes += static_brand_lanes(version)
    _raw_lanes += hero_gallery_lanes(version)
    lanes = versioned_lanes(_raw_lanes)

    # On-brand review: per-section renders + links to the canonical brand docs.
    renders = brand_renders(version)
    brand_dir = vdir / "brand"

    def brand_doc_url(name: str) -> str:
        p = brand_dir / name
        return ("/" + str(p.relative_to(PROJECT_DIR)).replace("\\", "/")) if p.exists() else ""

    return {
        **m,
        "item": item,
        "brand_renders": renders,
        "brand_yaml_url": brand_doc_url("brand.yaml"),
        "brand_md_url": brand_doc_url("brand.md"),
        "catalog": load_catalog(version),
        "screenshot": ("/" + str(shot.relative_to(PROJECT_DIR)).replace("\\", "/")) if shot else "",
        "site_claude": site_rel(version, item, "claude") if item else "",
        "site_gpt55": site_rel(version, item, "gpt55") if item else "",
        "site_claude_framework": site_rel(version, item, "claude", framework=True) if item else "",
        "site_gpt55_framework": site_rel(version, item, "gpt55", framework=True) if item else "",
        "site_gemini": site_rel(version, item, "gemini") if item else "",
        "composed_pages": compose_pages(version),
        "variant_pages": variant_pages(version),
        "static_lanes": static_brand_lanes(version),
        "lanes": lanes,
        # Back-compat keys
        "contract": docs["contract"],
        "contract_audit": docs["contract_audit"],
        "design_system": docs["design_system"],
        "design_tokens": parse_design_tokens(docs["design_system"]),
        "docs": docs,
        "assets": assets,
        "projects": [{"version": p["version"], "title": p.get("title") or p["version"]} for p in list_projects()],
        "framework_first": framework_first_mode(version),
    }


def load_assets(version: str) -> dict:
    path = RUNS_DIR / version / "assets" / "assets-manifest.json"
    if not path.exists():
        return {"total": 0, "by_role": {}, "roles": []}
    try:
        data = json.loads(path.read_text())
    except Exception:
        return {"total": 0, "by_role": {}, "roles": []}
    by_role: dict[str, list[dict]] = {}
    for r in data.get("assets", []):
        by_role.setdefault(r.get("role", "content"), []).append(
            {
                "url": r.get("url", ""),
                "type": r.get("asset_type", ""),
                "name": (r.get("name") or "")[:48],
                "svg": r.get("inline_svg") or "",
                "landmark": (r.get("placement") or {}).get("landmark", ""),
            }
        )
    roles = sorted(by_role, key=lambda k: -len(by_role[k]))
    return {"total": data.get("total_logical_assets", 0), "by_role": by_role, "roles": roles}


# ── on-brand render review (brand thin-spine outputs) ──────────────────────────
def _verdict_in(pattern: str, text: str) -> str:
    """First PASS/FAIL token following `pattern` on the same line (tolerant)."""
    m = re.search(pattern + r"[^\n]*?\b(PASS|FAIL)\b", text, re.IGNORECASE)
    return m.group(1).upper() if m else ""


def parse_onbrand_report(md_path: Path) -> dict:
    """Tolerant parse of an onbrand-report.md → overall verdict + 3 sub-criteria.

    Degrades gracefully: a missing/empty report yields empty verdicts. Sub-criteria
    are matched by their section heading keywords (neverDo / Fidelity / Slop); the
    overall verdict falls back to the worst sub-criterion when no OVERALL line exists.
    """
    text = read_text(md_path)
    if not text.strip():
        return {"verdict": "", "criteria": {"neverDo": "", "fidelity": "", "slop": ""}}
    criteria = {
        "neverDo": _verdict_in(r"neverDo\b", text),
        "fidelity": _verdict_in(r"Fidelity\b", text),
        "slop": _verdict_in(r"Slop\b", text),
    }
    overall = _verdict_in(r"OVERALL\b", text)
    if not overall:
        present = [v for v in criteria.values() if v]
        if present:
            overall = "FAIL" if "FAIL" in present else "PASS"
    return {"verdict": overall, "criteria": criteria}


def brand_renders(version: str) -> list[dict]:
    """Discover per-section brand renders for the on-brand review panel.

    Globs runs/<version>/brand/render/section-*/ generically, so a run shows up
    automatically once its render files exist. Resolves the generated preview and
    the source crop from each section's assets/ dir (by glob), and the verdict from
    onbrand-report.md. Returns [] when no render dir is present.
    """
    render_dir = RUNS_DIR / version / "brand" / "render"
    if not render_dir.is_dir():
        return []

    def rel(p: Path) -> str:
        return "/" + str(p.relative_to(PROJECT_DIR)).replace("\\", "/")

    out: list[dict] = []
    for sect in sorted(render_dir.glob("section-*")):
        if not sect.is_dir():
            continue
        assets = sect / "assets"

        def first_glob(*patterns: str) -> str:
            if not assets.is_dir():
                return ""
            for pat in patterns:
                hits = sorted(p for p in assets.glob(pat) if p.is_file())
                if hits:
                    return rel(hits[0])
            return ""

        index = sect / "index.html"
        preview = first_glob("_preview-render*", "_preview*", "*preview*.png")
        source = first_glob("_source*crop*", "_source*", "*source*crop*")
        report = parse_onbrand_report(sect / "onbrand-report.md")
        out.append(
            {
                "name": sect.name[len("section-"):] or sect.name,
                "html_url": rel(index) if index.exists() else "",
                "preview_png_url": preview,
                "source_crop_url": source,
                "report_summary": report["verdict"] or "no report",
                "verdict": report["verdict"],
                "criteria": report["criteria"],
            }
        )
    return out


def brand_review_summary(renders: list[dict]) -> dict:
    """Roll up discovered renders into a dashboard badge: {count, verdict}."""
    if not renders:
        return {"count": 0, "verdict": ""}
    verdicts = [r["verdict"] for r in renders if r["verdict"]]
    overall = ("FAIL" if "FAIL" in verdicts else "PASS") if verdicts else ""
    return {"count": len(renders), "verdict": overall}


# ── studio catalog (slot-contract catalog from render_catalog.py) ──────────────
def load_origin_catalog(version: str) -> dict:
    """Build the tier-grouped extracted-vs-designed origin catalog LIVE from a
    project's brand.yaml (not the possibly-stale catalog.json), so it works for any
    brand whose brand.yaml carries `origin` fields (WoodWave now, HubSpot later).

    Reuses render_catalog.build_origin_catalog as the single source of truth and
    degrades gracefully ({"hasOrigin": False, "tiers": []}) on any missing file,
    parse error, or brand.yaml without `origin` tagging.
    """
    empty = {"hasOrigin": False, "tiers": []}
    path = RUNS_DIR / version / "brand" / "brand.yaml"
    if not path.is_file():
        return empty
    try:
        doc = yaml.safe_load(path.read_text()) or {}
    except Exception:
        return empty
    if not isinstance(doc, dict):
        return empty
    try:
        import render_catalog  # brand_pipeline/render_catalog.py (on sys.path)

        oc = render_catalog.build_origin_catalog(doc)
        return oc if isinstance(oc, dict) else empty
    except Exception:
        return empty


def load_catalog(version: str) -> dict:
    """Discover + parse a brand's slot-contract catalog for the project detail.

    Globs runs/<version>/brand/catalog/catalog.json generically, so any brand's
    catalog auto-appears once render_catalog.py has emitted it. Returns the parsed
    contract plus server-relative URLs for the self-contained HTML + JSON, and the
    tier-grouped origin catalog (extracted vs designed) read live from brand.yaml.
    Degrades to {} when neither a slot-contract catalog nor origin data exists.
    """
    brand_dir = RUNS_DIR / version / "brand"
    if not brand_dir.is_dir():
        return {}
    origin_catalog = load_origin_catalog(version)
    matches = sorted(brand_dir.glob("catalog/catalog.json"))
    if not matches:
        # No slot-contract catalog yet — still surface the origin catalog if the
        # brand.yaml carries `origin` data, so the badges appear without a rebuild.
        if origin_catalog.get("hasOrigin"):
            return {
                "brand": version,
                "index_url": "",
                "json_url": "",
                "components": [],
                "sections": [],
                "ambiguousSlots": [],
                "typeInference": {},
                "counts": {"components": 0, "sections": 0, "media": 0, "content": 0},
                "originCatalog": origin_catalog,
            }
        return {}
    json_path = matches[0]
    catalog_dir = json_path.parent
    try:
        data = json.loads(json_path.read_text())
    except Exception:
        return {}

    def rel(p: Path) -> str:
        return "/" + str(p.relative_to(PROJECT_DIR)).replace("\\", "/")

    index_html = catalog_dir / "index.html"
    components = data.get("components", []) or []
    sections = data.get("sections", []) or []
    return {
        "brand": data.get("brand", version),
        "index_url": rel(index_html) if index_html.exists() else "",
        "json_url": rel(json_path),
        "components": components,
        "sections": sections,
        "ambiguousSlots": data.get("ambiguousSlots", []) or [],
        "typeInference": data.get("typeInference", {}) or {},
        "counts": {
            "components": len(components),
            "sections": len(sections),
            "media": sum(1 for c in components if c.get("type") == "media"),
            "content": sum(1 for c in components if c.get("type") == "content"),
        },
        # Tier-grouped extracted-vs-designed catalog, read live from brand.yaml.
        "originCatalog": origin_catalog,
    }


def catalog_summary(version: str) -> dict:
    """Lightweight dashboard badge: {sections, components, has}."""
    cat = load_catalog(version)
    if not cat:
        return {"has": False, "sections": 0, "components": 0}
    return {
        "has": True,
        "sections": cat["counts"]["sections"],
        "components": cat["counts"]["components"],
    }


# ── asset harvesting from the live URL (best-effort, no headless browser) ──────
def fetch_html(url: str) -> str:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    with urlopen(req, timeout=25, context=ctx) as resp:
        raw = resp.read(6_000_000)
    return raw.decode("utf-8", errors="ignore")


def harvest_assets(version: str, url: str, log) -> None:
    """Harvest + role-map brand assets from the live URL into the run's assets dir."""
    try:
        import harvest_assets as ha  # tools/harvest_assets.py
    except Exception as exc:  # pragma: no cover
        log(f"[assets] harvester import failed: {exc}")
        return
    try:
        from screenshot_to_template.chrome_extractor import (
            extract_chrome_from_html,
            write_chrome_contract,
        )
    except Exception as exc:  # pragma: no cover
        log(f"[chrome] extractor import failed: {exc}")
        extract_chrome_from_html = None  # type: ignore[assignment,misc]
        write_chrome_contract = None  # type: ignore[assignment,misc]
    try:
        log(f"[assets] fetching {url} ...")
        html = fetch_html(url)
        base = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
        out = RUNS_DIR / version / "assets"
        out.mkdir(parents=True, exist_ok=True)
        (out / "source.html").write_text(html[:2_000_000], encoding="utf-8")
        if extract_chrome_from_html and write_chrome_contract:
            contract = extract_chrome_from_html(html, base, source_url=url)
            chrome_path = write_chrome_contract(out / "source-chrome.json", contract)
            nav_n = len((contract.get("nav") or {}).get("links") or [])
            foot_cols = len((contract.get("footer") or {}).get("columns") or [])
            log(f"[chrome] static nav links={nav_n} footer columns={foot_cols} → {chrome_path.name}")
        # Higher-fidelity browser pass: real computed styles, top-level nav only,
        # real CTA styling, logo. Preferred over the static v1 when it succeeds.
        try:
            from screenshot_to_template.browser_chrome_extractor import (
                extract_chrome_with_browser,
                write_chrome_contract_v2,
            )

            log("[chrome] browser pass (Playwright) ...")
            v2 = extract_chrome_with_browser(url, log=log)
            v2_path = write_chrome_contract_v2(out / "source-chrome.v2.json", v2)
            nav = v2.get("nav") or {}
            log(
                f"[chrome] v2 nav={len(nav.get('links') or [])} ctas={len(nav.get('ctas') or [])} "
                f"footer cols={len((v2.get('footer') or {}).get('columns') or [])} → {v2_path.name}"
            )
        except Exception as exc:  # pragma: no cover - browser optional
            log(f"[chrome] browser pass skipped ({exc}); using static contract")
        records = ha.dedupe(ha.harvest(html, base))
        records.sort(key=lambda r: (r["role"], r["asset_type"], -r.get("count", 1)))
        from collections import Counter

        manifest = {
            "source": base,
            "total_logical_assets": len(records),
            "by_type": dict(Counter(r["asset_type"] for r in records)),
            "by_role": dict(Counter(r["role"] for r in records)),
            "assets": records,
        }
        (out / "assets-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        ha.write_report(records, out / "assets-report.html", base)
        log(f"[assets] harvested {len(records)} logical assets · {manifest['by_role']}")
        write_brand_assets(out, records, log)
    except Exception as exc:
        log(f"[assets] harvest skipped: {exc}")


_BRAND_TYPE_MAP = {
    "photo": "photo",
    "background": "background",
    "texture": "background",
    "illustration": "illustration",
    "vector": "illustration",
}


def write_brand_assets(out: Path, records: list[dict], log) -> Path | None:
    """Transform harvested records into the brand-assets.json shape the
    generation injector (screenshot_to_template.brand_assets) consumes."""
    by_role: dict[str, list[dict]] = {}
    photos = 0
    for r in records:
        url = r.get("url") or ""
        if not url or url.startswith("data:"):
            continue
        dims = r.get("dims") or []
        w = int(dims[0]) if len(dims) >= 2 and dims[0] else None
        h = int(dims[1]) if len(dims) >= 2 and dims[1] else None
        asp = round(w / h, 3) if (w and h) else None
        btype = _BRAND_TYPE_MAP.get(r.get("asset_type", ""))
        entry = {
            "id": f"{slugify(r.get('name', 'asset'))[:40]}-{abs(hash(url)) % 100000}",
            "type": btype or r.get("asset_type", ""),
            "label": r.get("name", ""),
            "alt": r.get("alt", ""),
            "url": url,
            "displayUrl": url,
            "width": w,
            "height": h,
            "aspect": asp,
            "role": r.get("role", "content"),
        }
        if btype == "photo":
            photos += 1
        by_role.setdefault(entry["role"], []).append(entry)
    path = out / "brand-assets.json"
    path.write_text(json.dumps({"byRole": by_role}, indent=2), encoding="utf-8")
    log(f"[assets] brand-assets.json written ({photos} photo candidates)")
    return path if photos else None


def make_run_config(version: str, brand_assets_path: Path | None) -> Path:
    """Per-project config: inherit config-anthropic.yaml, point brand-asset
    injection at THIS project's own harvested assets (or disable it)."""
    data = {}
    if BASE_CONFIG.exists():
        data = yaml.safe_load(BASE_CONFIG.read_text()) or {}
    if brand_assets_path:
        data["brand-assets-manifest"] = str(brand_assets_path.relative_to(PROJECT_DIR))
    else:
        data.pop("brand-assets-manifest", None)
    data["framework-generation-enabled"] = True
    data["vanilla-site-generation-enabled"] = False
    STUDIO_DIR.mkdir(parents=True, exist_ok=True)
    cfg = STUDIO_DIR / f"{version}.config.yaml"
    cfg.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return cfg


# ── background job ─────────────────────────────────────────────────────────────
def set_job(job_id: str, **kw) -> None:
    with JOBS_LOCK:
        JOBS.setdefault(job_id, {})
        JOBS[job_id].update(kw)


def run_job(job_id: str, version: str, url: str, shots_dir: Path, title: str) -> None:
    STUDIO_DIR.mkdir(parents=True, exist_ok=True)
    log_path = STUDIO_DIR / f"{job_id}.log"
    log_fh = open(log_path, "w", encoding="utf-8")

    def log(line: str) -> None:
        log_fh.write(line.rstrip("\n") + "\n")
        log_fh.flush()

    set_job(job_id, status="running", version=version, log=str(log_path), started=time.time())
    log(f"=== Studio job {job_id} ===")
    log(f"project: {title}")
    log(f"version: {version}")
    log(f"url:     {url}")
    log("")

    # 1) Harvest brand assets from the live URL (so generation can re-place them).
    brand_assets_path = None
    if url:
        harvest_assets(version, url, log)
        candidate = RUNS_DIR / version / "assets" / "brand-assets.json"
        # only use for injection if it actually carries photo candidates
        if candidate.exists():
            try:
                blob = json.loads(candidate.read_text())
                has_photo = any(
                    a.get("type") == "photo"
                    for arr in blob.get("byRole", {}).values()
                    for a in arr
                )
                brand_assets_path = candidate if has_photo else None
            except Exception:
                brand_assets_path = None

    # 2) Run the extraction + generation pipeline.
    config_path = make_run_config(version, brand_assets_path)
    cmd = [
        PY,
        "run_pipeline.py",
        "--version",
        version,
        "--screenshots-dir",
        str(shots_dir),
        "--runs-dir",
        str(RUNS_DIR),
        "--config",
        str(config_path),
    ]
    log(f"$ {' '.join(cmd)}")
    log("")
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(PROJECT_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        set_job(job_id, pid=proc.pid)
        for line in proc.stdout:  # type: ignore[union-attr]
            log(line.rstrip("\n"))
        proc.wait()
        rc = proc.returncode
    except Exception as exc:
        log(f"!! pipeline failed to launch: {exc}")
        rc = 1

    log("")
    log(f"=== pipeline exited with code {rc} ===")
    log_fh.close()
    job_status = "done" if rc == 0 else "error"
    if rc == 0 and run_complete_status(version) == "failed":
        job_status = "error"
    set_job(job_id, status=job_status, returncode=rc, finished=time.time())

    # stamp project metadata
    try:
        meta_path = RUNS_DIR / version / "studio-project.json"
        old_created = ""
        if meta_path.exists():
            try:
                old_created = json.loads(meta_path.read_text()).get("created", "")
            except Exception:
                pass
        meta = {
            "url": url,
            "title": title,
            "created": old_created or datetime.now().isoformat(),
            "job_id": job_id,
        }
        meta_path.write_text(json.dumps(meta, indent=2))
    except Exception:
        pass


def tail(path: str, max_bytes: int = 60_000) -> str:
    try:
        p = Path(path)
        data = p.read_bytes()
        return data[-max_bytes:].decode("utf-8", errors="ignore")
    except Exception:
        return ""


# ── HTTP handler ───────────────────────────────────────────────────────────────
class StudioHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PROJECT_DIR), **kwargs)

    def end_headers(self):
        # STATIC runs/** files (composed pages, variants) are regenerated in place many
        # times per session; without this the browser serves STALE copies — twice now a
        # reviewer flagged "slop" that was already fixed on disk (a phantom bug hunt each
        # time). The API/HTML handlers already send no-store; this covers the default
        # SimpleHTTPRequestHandler file-serving path too.
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt, *args):  # quieter console
        pass

    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html: str, status: int = 200) -> None:
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_text(self, text: str, status: int = 200) -> None:
        body = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_brandfile(self, version: str, which: str) -> None:
        """Serve runs/<version>/brand/brand.{yaml,md} as raw text for inline viewing.

        Generic over brand/version: any run with the files works. Resolves under
        RUNS_DIR and refuses paths that escape it; a missing file yields 404 so the
        client shows a graceful "not generated yet" placeholder.
        """
        fname = {"yaml": "brand.yaml", "md": "brand.md"}.get(which, "")
        if not fname:
            return self._send_text("unknown file", status=400)
        runs_root = RUNS_DIR.resolve()
        target = (RUNS_DIR / version / "brand" / fname).resolve()
        if runs_root not in target.parents or not target.is_file():
            return self._send_text("not generated yet", status=404)
        return self._send_text(read_text(target))

    def do_GET(self):  # noqa: N802
        path = urlparse(self.path).path
        if path in ("/", "/studio", "/studio/"):
            return self._send_html(render_dashboard())
        if path == "/api/projects":
            return self._send_json({"projects": list_projects()})
        if path.startswith("/api/jobs/"):
            job_id = unquote(path.rsplit("/", 1)[-1])
            with JOBS_LOCK:
                job = dict(JOBS.get(job_id, {}))
            if not job and (STUDIO_DIR / f"{job_id}.log").exists():
                job = {"status": "unknown"}
            job["output"] = tail(job.get("log", str(STUDIO_DIR / f"{job_id}.log")))
            return self._send_json(job)
        if path == "/api/brandfile":
            qs = parse_qs(urlparse(self.path).query)
            version = unquote((qs.get("version") or [""])[0])
            which = (qs.get("which") or [""])[0]
            return self._send_brandfile(version, which)
        if path.startswith("/api/project/"):
            version = unquote(path.rsplit("/", 1)[-1])
            return self._send_json(project_detail(version))
        if path.startswith("/project/"):
            version = unquote(path.rsplit("/", 1)[-1])
            return self._send_html(render_detail(version))
        # The pipeline viewer and old compare page are now the unified project canvas.
        if path in ("/compare-frameworks.html", "/compare-frameworks", "/viewer.html", "/viewer"):
            qs = parse_qs(urlparse(self.path).query)
            version = (qs.get("version") or qs.get("v") or [""])[0]
            target = f"/project/{quote(version)}" if version else "/studio"
            self.send_response(302)
            self.send_header("Location", target)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            return
        return super().do_GET()

    def _handle_rerun(self, version: str) -> None:
        version = slugify(version) if version else ""
        vdir = RUNS_DIR / version
        if not vdir.exists():
            return self._send_json({"error": f"project not found: {version}"}, 404)
        meta_path = vdir / "studio-project.json"
        meta = {}
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text())
            except Exception:
                meta = {}
        url = (meta.get("url") or "").strip()
        title = (meta.get("title") or version).strip()
        shots_dir = resolve_shots_dir(version)
        if not shots_dir:
            return self._send_json(
                {"error": "no screenshot found (screenshots/{version} or run item screenshot)"},
                400,
            )
        job_id = uuid.uuid4().hex[:12]
        set_job(job_id, status="queued", version=version)
        threading.Thread(
            target=run_job, args=(job_id, version, url, shots_dir, title), daemon=True
        ).start()
        return self._send_json({"version": version, "job_id": job_id})

    def do_POST(self):  # noqa: N802
        path = urlparse(self.path).path
        m = re.match(r"^/api/projects/([^/]+)/rerun$", path)
        if m:
            return self._handle_rerun(unquote(m.group(1)))
        if path != "/api/projects":
            return self._send_json({"error": "not found"}, 404)
        length = int(self.headers.get("Content-Length", 0))
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except Exception:
            return self._send_json({"error": "invalid json"}, 400)

        title = (payload.get("name") or payload.get("url") or "project").strip()
        url = (payload.get("url") or "").strip()
        filename = (payload.get("filename") or "screenshot.png").strip()
        b64 = payload.get("screenshot_b64") or ""
        if "," in b64:  # strip data: prefix
            b64 = b64.split(",", 1)[1]
        if not b64:
            return self._send_json({"error": "screenshot is required"}, 400)

        import base64

        ext = Path(filename).suffix.lower()
        if ext not in IMAGE_EXTS:
            ext = ".png"
        version = unique_version(title)
        shots_dir = SCREENSHOTS_DIR / version
        shots_dir.mkdir(parents=True, exist_ok=True)
        try:
            (shots_dir / f"{slugify(title)}{ext}").write_bytes(base64.b64decode(b64))
        except Exception as exc:
            return self._send_json({"error": f"could not save screenshot: {exc}"}, 400)

        job_id = uuid.uuid4().hex[:12]
        set_job(job_id, status="queued", version=version)
        threading.Thread(
            target=run_job, args=(job_id, version, url, shots_dir, title), daemon=True
        ).start()
        return self._send_json({"version": version, "job_id": job_id})


# ── server-rendered pages (dark theme to match the viewer) ──────────────────────
PAGE_HEAD = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Design System Studio</title>
<script src="https://cdn.tailwindcss.com"></script>
<style>
  :root { color-scheme: dark; }
  body { background: hsl(240 10% 3.9%); color: hsl(0 0% 95%); font-family: ui-sans-serif,-apple-system,Inter,Segoe UI,sans-serif; }
  .card { background: hsl(240 6% 8%); border: 1px solid hsl(240 3.7% 15.9%); border-radius: 14px; }
  .btn { display:inline-flex; align-items:center; gap:8px; height:38px; padding:0 16px; border-radius:10px; font-size:14px; font-weight:600; cursor:pointer; border:1px solid transparent; }
  .btn-primary { background: hsl(152 60% 45%); color:#04150c; }
  .btn-primary:hover { background: hsl(152 64% 52%); }
  .btn-ghost { background: hsl(240 4% 12%); border-color: hsl(240 3.7% 18%); color: hsl(0 0% 90%); }
  .btn-ghost:hover { background: hsl(240 4% 16%); }
  input, textarea { background: hsl(240 6% 11%); border:1px solid hsl(240 3.7% 18%); border-radius:10px; padding:10px 12px; color:#fff; width:100%; font-size:14px; }
  input:focus, textarea:focus { outline:none; border-color: hsl(152 60% 45%); }
  select { background: hsl(240 6% 11%); border:1px solid hsl(240 3.7% 18%); border-radius:8px; padding:6px 26px 6px 9px; color:#fff; font-size:12px; font-weight:600; cursor:pointer; -webkit-appearance:none; appearance:none; background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%2399a' stroke-width='3'%3E%3Cpath d='M6 9l6 6 6-6'/%3E%3C/svg%3E"); background-repeat:no-repeat; background-position:right 8px center; }
  select:focus { outline:none; border-color: hsl(152 60% 45%); }
  /* Lane iframe scaling: render at 1400px desktop width, scale to fit the lane. */
  .lane-body { overflow:auto; }
  .lane-sizer { position:relative; width:100%; }
  .lane-frame { position:absolute; top:0; left:0; width:1400px; transform-origin:0 0; background:#fff; }
  #side-tabs button.on { background:hsl(152 60% 45%) !important; color:#04150c !important; }
  .badge { font-size:11px; padding:2px 9px; border-radius:999px; font-weight:600; }
  .b-done { background: hsl(152 60% 45% / .16); color: hsl(152 70% 72%); }
  .b-run  { background: hsl(38 92% 50% / .16); color: hsl(38 92% 70%); }
  .b-err  { background: hsl(0 72% 51% / .16); color: hsl(0 80% 75%); }
  .b-idle { background: hsl(240 5% 30% / .35); color: hsl(240 5% 70%); }
  .b-fail { background: hsl(0 72% 51% / .16); color: hsl(0 80% 75%); }
  /* origin pills: extracted = solid green ("from page"); designed = dashed outline ("synthesized, overridable") */
  .b-extracted { background: hsl(152 60% 45% / .18); color: hsl(152 70% 72%); border:1px solid hsl(152 60% 45% / .55); }
  .b-designed  { background: transparent; color: hsl(210 90% 74%); border:1px dashed hsl(210 85% 65% / .75); }
  .drop { border:2px dashed hsl(240 3.7% 22%); border-radius:12px; padding:22px; text-align:center; cursor:pointer; transition:.15s; }
  .drop.over { border-color: hsl(152 60% 45%); background: hsl(152 60% 45% / .06); }
  a { color: inherit; }
  pre { white-space:pre-wrap; word-break:break-word; }
</style></head><body class="antialiased">"""


def render_dashboard() -> str:
    return PAGE_HEAD + """
<div class="max-w-6xl mx-auto px-6 py-8">
  <div class="flex items-center justify-between mb-6">
    <div>
      <h1 class="text-2xl font-bold tracking-tight">Design System Studio</h1>
      <p class="text-sm text-zinc-400 mt-1">Add a site, run the full extraction pipeline, and explore the design system, contract, and brand assets.</p>
    </div>
    <div class="flex gap-2">
      <a href="/viewer.html" target="_blank" class="btn btn-ghost">Open comparison viewer ↗</a>
      <button id="new-btn" class="btn btn-primary">+ New project</button>
    </div>
  </div>

  <div id="new-panel" class="card p-5 mb-7" style="display:none">
    <h2 class="font-semibold mb-4">New project</h2>
    <div class="grid md:grid-cols-2 gap-4">
      <div class="space-y-3">
        <div>
          <label class="text-xs text-zinc-400">Project name</label>
          <input id="f-name" placeholder="Acme marketing site">
        </div>
        <div>
          <label class="text-xs text-zinc-400">Site URL</label>
          <input id="f-url" placeholder="https://example.com" type="url">
        </div>
        <p class="text-xs text-zinc-500">The URL is fetched to harvest + role-map the brand's real assets. The screenshot drives design-system extraction.</p>
      </div>
      <div>
        <label class="text-xs text-zinc-400">Screenshot</label>
        <div id="drop" class="drop mt-1">
          <input id="f-file" type="file" accept="image/*" class="hidden" style="display:none">
          <div id="drop-text" class="text-sm text-zinc-400">Drop a full-page screenshot here, or <span class="text-emerald-400 underline">browse</span></div>
          <img id="preview" class="mx-auto mt-3 max-h-40 rounded-lg" style="display:none">
        </div>
      </div>
    </div>
    <div class="flex items-center gap-3 mt-4">
      <button id="run-btn" class="btn btn-primary">Run pipeline</button>
      <button id="cancel-btn" class="btn btn-ghost">Cancel</button>
      <span id="form-msg" class="text-sm text-zinc-400"></span>
    </div>
  </div>

  <div id="job-card" class="card p-5 mb-7" style="display:none">
    <div class="flex items-center justify-between mb-2">
      <h2 class="font-semibold">Run log <span id="job-status" class="badge b-run">running</span></h2>
      <a id="job-open" class="btn btn-ghost" style="display:none">Open project ↗</a>
    </div>
    <pre id="job-log" class="text-xs text-zinc-300 bg-black/40 rounded-lg p-3 max-h-80 overflow-auto"></pre>
  </div>

  <h2 class="text-sm font-semibold text-zinc-400 uppercase tracking-wider mb-3">Projects</h2>
  <div id="projects" class="grid sm:grid-cols-2 lg:grid-cols-3 gap-4"></div>
</div>

<script>
const $ = (id) => document.getElementById(id);
let fileB64 = "", fileName = "";

$("new-btn").onclick = () => { $("new-panel").style.display = "block"; $("new-btn").style.display="none"; };
$("cancel-btn").onclick = () => { $("new-panel").style.display = "none"; $("new-btn").style.display="inline-flex"; };

const drop = $("drop");
$("drop-text").onclick = () => $("f-file").click();
drop.addEventListener("dragover", e => { e.preventDefault(); drop.classList.add("over"); });
drop.addEventListener("dragleave", () => drop.classList.remove("over"));
drop.addEventListener("drop", e => { e.preventDefault(); drop.classList.remove("over"); if (e.dataTransfer.files[0]) readFile(e.dataTransfer.files[0]); });
$("f-file").addEventListener("change", e => { if (e.target.files[0]) readFile(e.target.files[0]); });

function readFile(f) {
  fileName = f.name;
  const r = new FileReader();
  r.onload = () => { fileB64 = r.result; const p = $("preview"); p.src = r.result; p.style.display="block"; $("drop-text").textContent = f.name; };
  r.readAsDataURL(f);
}

$("run-btn").onclick = async () => {
  const name = $("f-name").value.trim(), url = $("f-url").value.trim();
  if (!fileB64) { $("form-msg").textContent = "Please add a screenshot."; return; }
  $("run-btn").disabled = true; $("form-msg").textContent = "Starting…";
  const res = await fetch("/api/projects", { method:"POST", headers:{"Content-Type":"application/json"},
    body: JSON.stringify({ name, url, filename:fileName, screenshot_b64:fileB64 }) });
  const data = await res.json();
  $("run-btn").disabled = false;
  if (data.error) { $("form-msg").textContent = data.error; return; }
  $("new-panel").style.display="none"; $("new-btn").style.display="inline-flex";
  $("form-msg").textContent = "";
  pollJob(data.job_id, data.version);
};

function statusBadge(ps) {
  if (ps === "ready") return '<span class="badge b-done">ready</span>';
  if (ps === "failed") return '<span class="badge b-fail">failed</span>';
  if (ps === "building") return '<span class="badge b-run">building</span>';
  return '<span class="badge b-idle">run</span>';
}

function pollJob(jobId, version) {
  $("job-card").style.display="block";
  $("job-open").href = "/project/" + version;
  const tick = async () => {
    const r = await fetch("/api/jobs/" + jobId); const j = await r.json();
    const log = $("job-log"); log.textContent = j.output || "(waiting for output…)"; log.scrollTop = log.scrollHeight;
    const st = $("job-status");
    st.textContent = j.status || "running";
    st.className = "badge " + (j.status==="done" ? "b-done" : j.status==="error" ? "b-err" : "b-run");
    if (j.status === "done" || j.status === "error") {
      $("job-open").style.display = j.status==="done" ? "inline-flex" : "none";
      loadProjects();
      return;
    }
    setTimeout(tick, 1500);
  };
  tick();
}

async function loadProjects() {
  const r = await fetch("/api/projects"); const { projects } = await r.json();
  $("projects").innerHTML = projects.map(p => {
    const st = statusBadge(p.pipeline_status);
    const shot = p.thumb || "";
    const br = p.brand_review || {};
    const brCls = br.verdict === "PASS" ? "b-done" : br.verdict === "FAIL" ? "b-fail" : "b-idle";
    const brBadge = br.count ? `<span class="badge ${brCls}" title="${br.count} on-brand render(s)">on-brand: ${br.verdict || ("×" + br.count)}</span>` : "";
    return `<a href="/project/${p.version}" class="card p-4 block hover:border-emerald-500/40 transition-colors">
      <div class="flex items-center justify-between gap-2 mb-2">
        <div class="font-semibold truncate">${p.title || p.version}</div>
        <div class="flex items-center gap-2 shrink-0">${brBadge}${st}</div>
      </div>
      <div class="text-xs text-zinc-500 truncate mb-3">${p.url || p.version}</div>
      <div class="rounded-lg overflow-hidden bg-black/30 h-32 flex items-center justify-center">
        ${shot ? `<img src="${shot}" onerror="this.style.display='none'" class="w-full h-full object-cover object-top">` : '<span class="text-zinc-600 text-xs">no preview</span>'}
      </div>
    </a>`;
  }).join("") || '<div class="text-zinc-500 text-sm">No projects yet. Click “New project”.</div>';
}
loadProjects();
</script></body></html>"""


def render_detail(version: str) -> str:
    d = project_detail(version)
    # Safe for embedding in an inline <script>: neutralize </script> breakouts
    # and JS-illegal line separators (U+2028/U+2029) that appear in doc text.
    data_json = (
        json.dumps(d)
        .replace("</", "<\\/")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )
    return PAGE_HEAD + """
<div class="h-screen flex flex-col">
  <div class="flex items-center justify-between gap-3 px-5 py-3 border-b border-zinc-800 shrink-0">
    <div class="min-w-0">
      <a href="/studio" class="text-xs text-zinc-400 hover:text-white">← Studio</a>
      <div class="flex items-baseline gap-3 min-w-0">
        <h1 id="t-title" class="text-lg font-bold tracking-tight truncate"></h1>
        <a id="t-url" class="text-xs text-emerald-400 hover:underline truncate" target="_blank"></a>
      </div>
    </div>
    <div class="flex items-center gap-2 shrink-0">
      <select id="proj-switch" title="Switch project"></select>
      <span id="t-status" class="badge b-idle"></span>
      <button id="info-toggle" type="button" class="btn btn-ghost">Info ◂</button>
    </div>
  </div>

  <div class="flex-1 flex min-h-0">
    <div id="lanes" class="flex-1 flex gap-3 p-3 min-h-0 overflow-x-auto">
      <section class="lane card overflow-hidden flex flex-col min-w-[320px] flex-1">
        <div class="px-3 py-2 border-b border-zinc-800 flex items-center justify-between gap-2 shrink-0" style="height:46px">
          <span class="text-xs font-semibold text-zinc-300">Original site</span>
          <a id="orig-link" target="_blank" class="text-[11px] text-emerald-400 hover:underline" style="display:none">live ↗</a>
        </div>
        <div class="flex-1 overflow-auto bg-white min-h-0">
          <img id="o-shot" class="w-full block" style="display:none">
          <div id="o-shot-empty" class="p-6 text-sm text-zinc-500">No screenshot.</div>
        </div>
      </section>
      <section class="lane card overflow-hidden flex flex-col min-w-[320px] flex-1">
        <div class="px-2 border-b border-zinc-800 flex items-center gap-2 shrink-0" style="height:46px">
          <select data-lane="a" class="min-w-0 flex-1 truncate"></select>
          <a data-lane="a" class="lane-open ml-auto shrink-0 whitespace-nowrap text-[11px] text-emerald-400 hover:underline" target="_blank" style="display:none">open ↗</a>
        </div>
        <div class="lane-body flex-1 min-h-0 bg-white">
          <div class="lane-sizer" data-lane="a"><iframe data-lane="a" class="lane-frame" style="border:0"></iframe></div>
          <div data-lane="a" class="lane-empty p-6 text-sm text-zinc-500" style="display:none"></div>
        </div>
      </section>
      <section class="lane card overflow-hidden flex flex-col min-w-[320px] flex-1">
        <div class="px-2 border-b border-zinc-800 flex items-center gap-2 shrink-0" style="height:46px">
          <select data-lane="b" class="min-w-0 flex-1 truncate"></select>
          <a data-lane="b" class="lane-open ml-auto shrink-0 whitespace-nowrap text-[11px] text-emerald-400 hover:underline" target="_blank" style="display:none">open ↗</a>
        </div>
        <div class="lane-body flex-1 min-h-0 bg-white">
          <div class="lane-sizer" data-lane="b"><iframe data-lane="b" class="lane-frame" style="border:0"></iframe></div>
          <div data-lane="b" class="lane-empty p-6 text-sm text-zinc-500" style="display:none"></div>
        </div>
      </section>
    </div>

    <aside id="sidebar" class="shrink-0 border-l border-zinc-800 flex flex-col min-h-0" style="width:440px">
      <div class="flex flex-wrap gap-1 p-2 border-b border-zinc-800 shrink-0" id="side-tabs"></div>
      <div class="flex-1 overflow-auto p-3 min-h-0" id="side-body"></div>
    </aside>
  </div>
</div>

<script>
const D = __DATA__;
const $ = (id) => document.getElementById(id);
$("t-title").textContent = D.title || D.version;
if (D.url) { $("t-url").textContent = D.url; $("t-url").href = D.url; }

function statusBadgeEl(ps) {
  const el = $("t-status");
  el.textContent = ps || "idle";
  el.className = "badge " + (ps==="ready" ? "b-done" : ps==="failed" ? "b-fail" : ps==="building" ? "b-run" : "b-idle");
}
statusBadgeEl(D.pipeline_status);

// ---- project switcher (this is the single canvas) ----
(function(){
  const sw = $("proj-switch");
  if (!sw) return;
  sw.innerHTML = (D.projects||[]).map(p => `<option value="${p.version}">${p.title}</option>`).join("");
  sw.value = D.version;
  sw.onchange = () => { location.href = "/project/" + encodeURIComponent(sw.value); };
})();

// ---- lane 1: original site ----
if (D.screenshot) { $("o-shot").src = D.screenshot; $("o-shot").style.display="block"; $("o-shot-empty").style.display="none"; }
if (D.url) { const ol=$("orig-link"); ol.href=D.url; ol.style.display="inline"; }

// ---- lanes 2 & 3: any approach via dropdown, rendered at desktop width and scaled ----
// Prefer the server's unified, recency-sorted + version-prefixed lane list
// (newest-first, highest vNN at top). Fall back to the legacy client-side
// assembly only if an older payload without `lanes` is served.
const OUTPUTS = (Array.isArray(D.lanes) && D.lanes.length)
  ? D.lanes.map(c => [c.label, c.url])
  : [
      ["Claude · Framework", D.site_claude_framework],
      ["GPT-5.5 · Framework", D.site_gpt55_framework],
      ["Claude · Vanilla HTML", D.site_claude],
      ["GPT-5.5 · Vanilla HTML", D.site_gpt55],
      ["Gemini · Vanilla HTML", D.site_gemini],
    ].filter(o => o[1])
     .concat((D.variant_pages || []).map(c => [c.label, c.url]))
     .concat((D.composed_pages || []).map(c => [c.label, c.url]))
     .concat((D.static_lanes || []).map(c => [c.label, c.url]));

const bust = (src) => src + (src.includes("?") ? "&" : "?") + "t=" + Date.now();

function fitLane(lane) {
  const sizer = document.querySelector(`.lane-sizer[data-lane="${lane}"]`);
  const frame = document.querySelector(`iframe[data-lane="${lane}"]`);
  if (!sizer || !frame || sizer.style.display === "none") return;
  const body = sizer.parentElement;
  const w = body.clientWidth;
  if (!w) return;
  const s = w / 1400;
  let docH = 1600;
  try {
    const dd = frame.contentDocument;
    if (dd) docH = Math.max(dd.body ? dd.body.scrollHeight : 0, dd.documentElement ? dd.documentElement.scrollHeight : 0, 1600);
  } catch (e) {}
  frame.style.height = docH + "px";
  frame.style.transform = "scale(" + s + ")";
  sizer.style.height = (docH * s) + "px";
}

function setupLane(lane, defaultIndex) {
  const sel = document.querySelector(`select[data-lane="${lane}"]`);
  const frame = document.querySelector(`iframe[data-lane="${lane}"]`);
  const empty = document.querySelector(`.lane-empty[data-lane="${lane}"]`);
  const sizer = document.querySelector(`.lane-sizer[data-lane="${lane}"]`);
  const open = document.querySelector(`.lane-open[data-lane="${lane}"]`);
  if (!OUTPUTS.length) {
    sel.innerHTML = '<option>No outputs</option>'; sel.disabled = true;
    sizer.style.display = "none"; empty.style.display = "block";
    empty.textContent = "No generated outputs yet. Re-run the pipeline.";
    return;
  }
  sel.innerHTML = OUTPUTS.map((o,i) => `<option value="${i}">${o[0]}</option>`).join("");
  sel.value = Math.min(defaultIndex, OUTPUTS.length - 1);
  const load = () => {
    const url = OUTPUTS[sel.value][1];
    if (open) { open.href = url; open.style.display = "inline"; }
    frame.onload = () => fitLane(lane);
    frame.src = bust(url);
  };
  sel.onchange = load; load();
}
setupLane("a", 0);
setupLane("b", OUTPUTS.length > 1 ? 1 : 0);

function fitAll() { fitLane("a"); fitLane("b"); }
window.addEventListener("resize", fitAll);
setTimeout(fitAll, 300);
setTimeout(fitAll, 1200);

// ---- info sidebar: every artifact + assets, combined ----
const esc = (s) => (s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
const DOCS = [
  ["design_system","Design system"],
  ["structural","Structural analysis"],
  ["grounding","Grounding"],
  ["generation_input","Generation input"],
  ["ledger","Ledger"],
  ["contract","Contract"],
  ["contract_audit","Contract audit"],
  ["section_inventory","Sections"],
  ["style_audit","Style audit"],
  ["review","Review"],
  ["conversion_review","Conversion review"],
  ["prompts","Prompts"],
  ["learnings","Learnings"],
];
const docs = D.docs || {};
const DT = D.design_tokens || {};
const hasVisual = !!((DT.colorGroups && DT.colorGroups.length) || (DT.typography && DT.typography.length) || (DT.surfaces && DT.surfaces.length));
const availableDocs = DOCS.filter(t => (docs[t[0]] || "").trim());
// Insert the visual gallery tab right after "Design system" (or up front if that doc is absent).
const sideTabsBase = availableDocs.slice();
if (hasVisual) {
  const dsIdx = sideTabsBase.findIndex(t => t[0] === "design_system");
  sideTabsBase.splice(dsIdx >= 0 ? dsIdx + 1 : 0, 0, ["visual","Visual"]);
}
const onbrandTabs = (D.brand_renders && D.brand_renders.length) ? [["onbrand","On-brand (" + D.brand_renders.length + ")"]] : [];
const C = D.catalog || {};
const OC = C.originCatalog || {};
const hasOrigin = !!(OC.hasOrigin && OC.tiers && OC.tiers.length);
const hasCatalog = !!(C.index_url || (C.sections && C.sections.length) || (C.components && C.components.length) || hasOrigin);
const catalogTabs = hasCatalog ? [["catalog","Catalog (" + ((C.counts && C.counts.sections) || 0) + ")"]] : [];
// brand.yaml / brand.md as inline, scrollable tabs (hidden when the file is absent).
const brandFileTabs = [];
if (D.brand_yaml_url) brandFileTabs.push(["brandyaml","brand.yaml"]);
if (D.brand_md_url) brandFileTabs.push(["brandmd","brand.md"]);
const sideTabs = catalogTabs.concat(onbrandTabs).concat(brandFileTabs).concat(sideTabsBase).concat([["assets","Assets (" + (D.assets.total||0) + ")"]]);

function renderAssets() {
  const A = D.assets;
  if (!A.total) return '<div class="card p-6 text-sm text-zinc-500">No assets harvested. Add a reachable URL when creating the project to populate this.</div>';
  return A.roles.map(role => {
    const items = A.by_role[role];
    const cells = items.map(a => {
      const media = a.svg ? `<div class="h-24 grid place-items-center p-3 text-zinc-200">${a.svg}</div>`
        : a.url ? `<div class="h-24 grid place-items-center bg-black/30 p-2"><img src="${a.url}" loading="lazy" onerror="this.parentElement.innerHTML='<span class=\\'text-zinc-600 text-xs\\'>load failed</span>'" class="max-h-full max-w-full object-contain"></div>`
        : `<div class="h-24 grid place-items-center text-zinc-600">—</div>`;
      return `<figure class="card overflow-hidden m-0">${media}<figcaption class="p-2"><span class="badge b-idle">${a.type}</span><div class="text-[11px] text-zinc-400 truncate mt-1">${a.name}</div></figcaption></figure>`;
    }).join("");
    return `<section class="mb-6"><h3 class="text-xs uppercase tracking-wider text-zinc-400 mb-2">${role} <span class="badge b-done">${items.length}</span></h3><div class="grid grid-cols-2 gap-2">${cells}</div></section>`;
  }).join("");
}

// ---- catalog: origin (extracted vs designed) + components + slot contracts ----
function catTypeBadge(t) {
  const cls = t === "media" ? "b-fail" : "b-done";
  return `<span class="badge ${cls}">${esc(t || "?")}</span>`;
}
function originBadge(o) {
  if (o === "extracted") return '<span class="badge b-extracted" title="observed on the live page">extracted</span>';
  if (o === "designed")  return '<span class="badge b-designed" title="synthesized brand-consistent, overridable">designed</span>';
  return `<span class="badge b-idle">${esc(o || "?")}</span>`;
}
function originDetail(it) {
  if (it.origin === "extracted") {
    const prov = (it.provenance || []).join(", ");
    const conf = it.conflictsWith || [];
    return `<div class="text-[10px] text-zinc-500 truncate" title="${esc(prov)}">from: ${esc(prov || "—")}</div>`
      + (conf.length ? `<div class="text-[10px] text-amber-400/90 truncate" title="${esc(conf.join(", "))}">⚠ conflictsWith: ${esc(conf.join(", "))}</div>` : "");
  }
  if (it.origin === "designed") {
    const note = it.designedFrom || "synthesized from brand rules + tokens";
    return `<div class="text-[10px] text-zinc-500 leading-snug" title="${esc(note)}">${esc(note)}</div>`
      + (it.overridable ? `<div class="text-[10px] uppercase tracking-wider text-sky-400/80 mt-0.5">overridable</div>` : "");
  }
  return "";
}
function renderOriginCatalog(OC) {
  if (!OC || !OC.tiers || !OC.tiers.length) return "";
  const legend = `<div class="flex items-center gap-3 mb-3 flex-wrap text-[10px] text-zinc-500">
    <span class="inline-flex items-center gap-1.5">${originBadge("extracted")} observed on the page</span>
    <span class="inline-flex items-center gap-1.5">${originBadge("designed")} synthesized · overridable</span>
  </div>`;
  const tiers = OC.tiers.map(t => {
    const items = (t.items || []).map(it => {
      const meta = [it.variant ? esc(it.variant) : "", it.use ? "(" + esc(it.use) + ")" : ""].filter(Boolean).join(" · ");
      return `<div class="card p-2 flex items-start justify-between gap-2 mb-1.5">
        <div class="min-w-0">
          <div class="text-xs font-semibold text-zinc-100 truncate" title="${esc(it.name)}">${esc(it.name)}${meta ? ` <span class="text-[10px] text-zinc-600 font-normal">${meta}</span>` : ""}</div>
          ${originDetail(it)}
        </div>
        ${originBadge(it.origin)}
      </div>`;
    }).join("");
    return `<section class="mb-4">
      <h3 class="text-xs uppercase tracking-wider text-zinc-400 mb-2">
        Tier ${t.tier} · ${esc(t.label)}
        <span class="text-zinc-500 normal-case tracking-normal">— ${t.extracted} extracted / ${t.designed} designed</span>
      </h3>
      ${items}
    </section>`;
  }).join("");
  return `<section class="mb-5">
    <h3 class="text-xs uppercase tracking-wider text-zinc-300 mb-2 font-semibold">Catalog by tier — origin</h3>
    ${legend}${tiers}
  </section>`;
}
function renderCatalog() {
  const cat = D.catalog || {};
  if (!hasCatalog) {
    return '<div class="card p-6 text-sm text-zinc-500">No catalog found. It appears automatically once <code>runs/' + esc(D.version) + '/brand/catalog/catalog.json</code> exists (run <code>render_catalog.py</code>), or once the brand.yaml carries <code>origin</code> fields.</div>';
  }
  const cnt = cat.counts || {};
  const head = `<div class="flex items-center gap-1.5 mb-3 flex-wrap">
    ${cat.index_url ? `<a href="${cat.index_url}" target="_blank" class="btn btn-primary" style="height:28px;padding:0 10px;font-size:11px">Open catalog ↗</a>` : ""}
    ${cat.json_url ? `<a href="${cat.json_url}" target="_blank" class="btn btn-ghost" style="height:28px;padding:0 10px;font-size:11px">catalog.json ↗</a>` : ""}
    <span class="badge b-idle">${cnt.components||0} components</span>
    <span class="badge b-idle">${cnt.sections||0} sections</span>
  </div>`;

  // origin catalog (extracted vs designed), grouped by tier — the new headline view
  const originSection = renderOriginCatalog(cat.originCatalog);

  // components
  const comps = (cat.components || []).map(c => {
    const used = (c.usedInSlots || []).join(", ");
    return `<div class="card p-2 flex items-center justify-between gap-2 mb-1.5">
      <div class="min-w-0">
        <div class="text-xs font-semibold text-zinc-100 truncate" title="${esc(c.name)}">${esc(c.name)}</div>
        <div class="text-[10px] text-zinc-500 truncate" title="${esc(used)}">${esc(c.group||"")} · ${esc(used)}</div>
      </div>
      ${catTypeBadge(c.type)}
    </div>`;
  }).join("");
  const compSection = (cat.components||[]).length ? `<section class="mb-5"><h3 class="text-xs uppercase tracking-wider text-zinc-400 mb-2">Components <span class="badge b-done">${(cat.components||[]).length}</span></h3>${comps}</section>` : "";

  // sections as slot contracts
  const sects = (cat.sections || []).map(s => {
    const surf = s.surface || {};
    const slots = (s.slots || []).map(sl => `
      <div class="flex items-start gap-2 mb-1">
        ${catTypeBadge(sl.type)}
        <div class="min-w-0">
          <div class="text-[11px] text-zinc-200 truncate" title="${esc(sl.name)}">${esc(sl.name)}</div>
          <div class="text-[10px] text-zinc-500 truncate" title="${esc(sl.useCase||"")}">→ ${esc(sl.mappedComponent||"")}</div>
        </div>
      </div>`).join("");
    const swatch = surf.bg ? `<span class="inline-block w-3 h-3 rounded-full ring-1 ring-white/20 align-middle" style="background:${esc(surf.bg)}"></span>` : "";
    return `<section class="card p-3 mb-3">
      <div class="flex items-center justify-between gap-2 mb-1.5">
        <div class="text-sm font-semibold text-zinc-100 truncate" title="${esc(s.name)}">${esc(s.name)}</div>
        <span class="text-[10px] text-zinc-500">${(s.slots||[]).length} slots</span>
      </div>
      <div class="flex flex-wrap gap-1 mb-2">
        <span class="badge b-idle">${swatch} mode: ${esc(s.mode||"")}</span>
        <span class="badge b-idle">layout: ${esc(s.layoutArchetype||"n/a")}</span>
        <span class="badge b-idle">${esc(s.scaffold||"")}</span>
      </div>
      ${slots}
    </section>`;
  }).join("");
  const sectSection = (cat.sections||[]).length ? `<section class="mb-4"><h3 class="text-xs uppercase tracking-wider text-zinc-400 mb-2">Sections — slot contracts <span class="badge b-done">${(cat.sections||[]).length}</span></h3>${sects}</section>` : "";

  const amb = cat.ambiguousSlots || [];
  const ambSection = (cat.sections||[]).length
    ? (amb.length
        ? `<div class="card p-3 text-[11px] text-zinc-400"><b>Ambiguous slots (${amb.length}):</b> ${amb.map(a => esc(a.section + " · " + a.slot)).join(", ")}</div>`
        : `<div class="card p-3 text-[11px] text-zinc-500">No ambiguous slots — all resolved via component/role keywords.</div>`)
    : "";

  return head + originSection + compSection + sectSection + ambSection;
}

// ---- on-brand review: source crop vs generated preview, side-by-side ----
function obVerdictBadge(v) {
  const cls = v === "PASS" ? "b-done" : v === "FAIL" ? "b-fail" : "b-idle";
  return `<span class="badge ${cls}">${esc(v || "no report")}</span>`;
}
function obCritBadge(label, v) {
  const cls = v === "PASS" ? "b-done" : v === "FAIL" ? "b-fail" : "b-idle";
  return `<span class="badge ${cls}">${label}: ${esc(v || "n/a")}</span>`;
}
function obFigure(label, url, missing) {
  if (!url) return `<div class="grid place-items-center bg-black/30 rounded-lg h-24 text-zinc-600 text-[11px]">${missing}</div>`;
  return `<figure class="m-0">
    <figcaption class="text-[10px] uppercase tracking-[0.14em] text-zinc-500 mb-1">${label}</figcaption>
    <div class="bg-black/30 rounded-lg overflow-hidden ring-1 ring-white/10"><img src="${url}" loading="lazy" class="w-full block" onerror="this.parentElement.innerHTML='<span class=\\'text-zinc-600 text-[11px] p-2 block\\'>load failed</span>'"></div>
  </figure>`;
}
function renderOnbrand() {
  const R = D.brand_renders || [];
  if (!R.length) return '<div class="card p-6 text-sm text-zinc-500">No brand renders found. They appear automatically once <code>runs/' + esc(D.version) + '/brand/render/section-*/</code> exists.</div>';
  const links = [];
  if (D.brand_yaml_url) links.push(`<a href="${D.brand_yaml_url}" target="_blank" class="btn btn-ghost" style="height:28px;padding:0 10px;font-size:11px">brand.yaml ↗</a>`);
  if (D.brand_md_url) links.push(`<a href="${D.brand_md_url}" target="_blank" class="btn btn-ghost" style="height:28px;padding:0 10px;font-size:11px">brand.md ↗</a>`);
  const head = links.length ? `<div class="flex items-center gap-1.5 mb-3 flex-wrap">${links.join("")}</div>` : "";
  const cards = R.map(r => {
    const c = r.criteria || {};
    const open = r.html_url ? `<a href="${r.html_url}" target="_blank" class="btn btn-primary" style="height:28px;padding:0 10px;font-size:11px">Open render ↗</a>` : "";
    return `<section class="card p-3 mb-4">
      <div class="flex items-center justify-between gap-2 mb-2">
        <div class="text-sm font-semibold text-zinc-100 truncate" title="${esc(r.name)}">${esc(r.name)}</div>
        ${obVerdictBadge(r.verdict)}
      </div>
      <div class="grid grid-cols-2 gap-2 mb-2">
        ${obFigure("Source brand", r.source_crop_url, "no source crop")}
        ${obFigure("Generated", r.preview_png_url, "no preview")}
      </div>
      <div class="flex flex-wrap gap-1 mb-2">${obCritBadge("neverDo", c.neverDo)}${obCritBadge("fidelity", c.fidelity)}${obCritBadge("slop", c.slop)}</div>
      ${open ? `<div class="flex flex-wrap gap-1">${open}</div>` : ""}
    </section>`;
  }).join("");
  return head + cards;
}

// ---- visual design-system gallery (parsed server-side into D.design_tokens) ----
const pxNum = (v) => { const m = String(v).match(/([\\d.]+)\\s*px/); return m ? parseFloat(m[1]) : null; };
// Single-quoted family names so the value is safe inside a double-quoted style="" attribute.
const fontStackFor = (cat) => (/serif/i.test(cat||"") && !/sans/i.test(cat||""))
  ? "Georgia, 'Times New Roman', Times, serif"
  : "system-ui, -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif";
// Resolve a single length to px: handles "16px", "1.5rem" (×16), and bare numbers.
const parsePx = (v) => {
  const s = String(v || "");
  let m = s.match(/([\\d.]+)\\s*px/i); if (m) return parseFloat(m[1]);
  m = s.match(/([\\d.]+)\\s*rem/i); if (m) return parseFloat(m[1]) * 16;
  m = s.match(/^\\s*([\\d.]+)\\s*$/); if (m) return parseFloat(m[1]);
  return null;
};
// Resolve a token font-size to a representative px value; clamp(min,pref,max) → max.
const resolveFontPx = (fs) => {
  const s = String(fs || "");
  const clamp = s.match(/clamp\\(([^)]*)\\)/i);
  if (clamp) {
    const parts = clamp[1].split(",").map(x => x.trim());
    const v = parsePx(parts[parts.length - 1]) || parsePx(parts[0]);
    if (v) return v;
  }
  return parsePx(s) || 16;
};
// On-screen "Aa" specimen size: real type scale clamped to fit the column while staying legible.
const specimenPx = (fs) => Math.round(Math.max(22, Math.min(64, resolveFontPx(fs))));
// Reduce a token fontFamily ("'Inter'", "Editorial serif (note…)", "X, Y") to a clean name.
const cleanFamily = (f) => {
  let s = String(f || "").split("(")[0].trim();
  s = s.replace(/^['"]+|['"]+$/g, "").trim();
  s = s.split(",")[0].trim();
  return s;
};

function vSection(title, inner) {
  if (!inner) return "";
  return `<section class="mb-6"><h3 class="text-xs uppercase tracking-wider text-zinc-400 mb-2">${esc(title)}</h3>${inner}</section>`;
}

function renderVisual() {
  if (!hasVisual) return '<div class="card p-6 text-sm text-zinc-500">No design tokens parsed for this run.</div>';
  const out = [];

  if (DT.name || DT.description) {
    out.push(`<div class="card p-3 mb-5">
      ${DT.name ? `<div class="text-sm font-semibold text-zinc-100">${esc(DT.name)}</div>` : ""}
      ${DT.description ? `<div class="text-[11px] text-zinc-400 mt-1 leading-relaxed">${esc(DT.description)}</div>` : ""}
    </div>`);
  }

  // ── Colors grouped by category ──
  const colorInner = (DT.colorGroups || []).map(g => {
    const cells = g.swatches.map(s => `
      <figure class="m-0">
        <div class="h-12 rounded-lg ring-1 ring-white/10" style="background:${esc(s.hex)}"></div>
        <figcaption class="mt-1">
          <div class="text-[11px] text-zinc-200 truncate" title="${esc(s.path)}">${esc(s.name)}</div>
          <div class="text-[10px] text-zinc-500 font-mono uppercase">${esc(s.hex)}</div>
        </figcaption>
      </figure>`).join("");
    return `<div class="mb-3">
      <div class="text-[11px] text-zinc-400 mb-1.5">${esc(g.category)} <span class="badge b-idle">${g.swatches.length}</span></div>
      <div class="grid grid-cols-3 gap-2">${cells}</div>
    </div>`;
  }).join("");
  out.push(vSection("Colors", colorInner));

  // ── Surfaces with legible on-surface text samples ──
  const surfInner = (DT.surfaces || []).map(s => {
    const t = s.text || {};
    const lines = [];
    if (t.default) lines.push(`<div style="color:${esc(t.default)}" class="text-sm font-medium">${esc(s.name)}</div>`);
    if (t.muted) lines.push(`<div style="color:${esc(t.muted)}" class="text-xs">Muted supporting copy on this surface.</div>`);
    if (t.accent) lines.push(`<div style="color:${esc(t.accent)}" class="text-xs font-semibold underline">Accent link →</div>`);
    if (!lines.length) lines.push(`<div class="text-xs text-zinc-500/70">${esc(s.name)}</div>`);
    const border = s.border ? `border:1px solid ${esc(s.border)}` : "border:1px solid rgba(255,255,255,.08)";
    return `<div class="rounded-lg p-3 mb-2 flex flex-col gap-1" style="background:${esc(s.value)};${border}">
      <div class="flex items-center justify-between gap-2">
        <span class="text-[10px] font-mono uppercase" style="color:${esc(t.default || '#888')};opacity:.7">${esc(s.value)}</span>
        ${s.role ? `<span class="text-[9px] uppercase tracking-wider px-1.5 py-0.5 rounded" style="background:rgba(0,0,0,.18);color:${esc(t.muted || t.default || '#888')}">${esc(s.role)}</span>` : ""}
      </div>
      ${lines.join("")}
    </div>`;
  }).join("");
  out.push(vSection("Surfaces & text", surfInner));

  // ── Typography: one horizontal specimen card per style ──
  const typoInner = (DT.typography || []).map(t => {
    const stack = fontStackFor(t.category);
    const label = String(t.key || "").replace(/[_-]+/g, " ").trim().toUpperCase();
    const family = cleanFamily(t.fontFamily) || (/serif/i.test(t.category || "") && !/sans/i.test(t.category || "") ? "Serif" : "Sans");
    const sub = [
      t.fontSize ? esc(t.fontSize) : "",
      t.fontWeight ? "w" + esc(t.fontWeight) : "",
      t.lineHeight ? "lh " + esc(t.lineHeight) : "",
    ].filter(Boolean).join(" / ");
    // Specimen previews the real type scale: actual size (clamped to fit), weight, family, line-height.
    const spec = specimenPx(t.fontSize);
    const lh = t.lineHeight && parseFloat(t.lineHeight) ? esc(t.lineHeight) : "1";
    return `<div class="card flex items-stretch mb-2 overflow-hidden">
      <div class="shrink-0 grid place-items-center overflow-hidden" style="width:108px;font-family:${stack};font-weight:${esc(t.fontWeight || '400')};font-size:${spec}px;line-height:${lh};color:#f4f4f5">Aa</div>
      <div class="self-stretch w-px bg-zinc-700/70 shrink-0"></div>
      <div class="flex-1 min-w-0 flex flex-col justify-center gap-1 px-4 py-3">
        <div class="text-[10px] uppercase tracking-[0.14em] text-zinc-500">${esc(label)}</div>
        <div class="text-base font-semibold text-zinc-100 leading-tight truncate" title="${esc(t.fontFamily || '')}">${esc(family)}</div>
        ${sub ? `<div class="text-[11px] text-zinc-500">${sub}</div>` : ""}
      </div>
    </div>`;
  }).join("");
  out.push(vSection("Typography", typoInner));

  // ── Spacing scale + named spacing tokens ──
  const allSpace = (DT.spacingScale || []).map(v => ({name: v, value: v}))
    .concat(DT.spacingNamed || []);
  const maxPx = Math.max(1, ...allSpace.map(s => pxNum(s.value) || 0));
  const spaceInner = allSpace.length ? allSpace.map(s => {
    const n = pxNum(s.value);
    const w = n ? Math.max(4, (n / maxPx) * 100) : 4;
    return `<div class="flex items-center gap-2 mb-1.5">
      <div class="h-3 rounded bg-emerald-500/70" style="width:${w}%"></div>
      <span class="text-[10px] text-zinc-400 font-mono whitespace-nowrap">${esc(s.name === s.value ? s.value : s.name + " · " + s.value)}</span>
    </div>`;
  }).join("") : "";
  out.push(vSection("Spacing", spaceInner));

  // ── Radius ──
  const radInner = (DT.radius || []).length ? `<div class="grid grid-cols-3 gap-2">${DT.radius.map(r => {
    const n = pxNum(r.value);
    const rad = n != null ? Math.min(n, 28) : 8;
    return `<figure class="m-0">
      <div class="h-14 bg-zinc-700 ring-1 ring-white/10" style="border-radius:${rad}px"></div>
      <figcaption class="mt-1"><div class="text-[11px] text-zinc-200 truncate">${esc(r.name)}</div><div class="text-[10px] text-zinc-500 font-mono">${esc(r.value)}</div></figcaption>
    </figure>`;
  }).join("")}</div>` : "";
  out.push(vSection("Radius", radInner));

  // ── Shadow ──
  const shadInner = (DT.shadow || []).length ? `<div class="grid grid-cols-2 gap-3">${DT.shadow.map(s => `
    <figure class="m-0">
      <div class="h-16 rounded-lg bg-zinc-100" style="box-shadow:${esc(s.value)}"></div>
      <figcaption class="mt-1"><div class="text-[11px] text-zinc-200 truncate">${esc(s.name)}</div><div class="text-[10px] text-zinc-500 font-mono truncate" title="${esc(s.value)}">${esc(s.value)}</div></figcaption>
    </figure>`).join("")}</div>` : "";
  out.push(vSection("Shadow", shadInner));

  return out.join("") || '<div class="card p-6 text-sm text-zinc-500">No design tokens parsed for this run.</div>';
}

// ---- brand.yaml / brand.md inline viewers (fetched on demand, scrollable) ----
// Tiny dependency-free markdown → HTML renderer (headings, lists, code fences,
// blockquotes, rules, and inline bold/italic/code/links). Everything is escaped
// first so file text can never inject HTML into the page.
// Append a small color swatch right after each hex token in VISIBLE text only.
// Walks the already-built inline HTML, leaving tag markup (attributes) and the
// contents of <code> spans untouched so we never corrupt emitted hex values.
function hexSwatches(html) {
  const hex = /#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})\\b/g;
  const swatch = (m) => m + '<span style="display:inline-block;width:0.85em;height:0.85em;border-radius:3px;border:1px solid rgba(255,255,255,.25);background:' + m + ';vertical-align:middle;margin-left:4px"></span>';
  let inCode = false;
  return html.split(/(<[^>]+>)/).map(part => {
    if (!part) return part;
    if (part[0] === "<") {
      if (/^<code[\\s>]/i.test(part)) inCode = true;
      else if (/^<\\/code>/i.test(part)) inCode = false;
      return part;
    }
    return inCode ? part : part.replace(hex, swatch);
  }).join("");
}
function inlineMd(s) {
  s = esc(s);
  s = s.replace(/`([^`]+)`/g, '<code style="background:rgba(255,255,255,.08);padding:1px 5px;border-radius:4px;font-size:.9em">$1</code>');
  s = s.replace(/\\*\\*([^*]+)\\*\\*/g, '<strong>$1</strong>');
  s = s.replace(/(^|[^*])\\*([^*\\s][^*]*)\\*/g, '$1<em>$2</em>');
  s = s.replace(/\\[([^\\]]+)\\]\\(([^)]+)\\)/g, '<a href="$2" target="_blank" class="text-emerald-400 hover:underline">$1</a>');
  return hexSwatches(s);
}
function mdToHtml(src) {
  const lines = String(src || "").replace(/\\r\\n?/g, "\\n").split("\\n");
  const out = [];
  let para = [], listType = null, listItems = [], i = 0;
  const flushPara = () => { if (para.length) { out.push('<p style="margin:0 0 10px">' + para.map(inlineMd).join("<br>") + '</p>'); para = []; } };
  const flushList = () => {
    if (listItems.length) {
      out.push('<' + listType + ' style="margin:0 0 10px;padding-left:20px">' + listItems.map(li => '<li style="margin:2px 0">' + inlineMd(li) + '</li>').join("") + '</' + listType + '>');
      listItems = []; listType = null;
    }
  };
  while (i < lines.length) {
    const line = lines[i];
    if (/^```/.test(line.trim())) {
      flushPara(); flushList();
      const buf = []; i++;
      while (i < lines.length && !/^```/.test(lines[i].trim())) { buf.push(lines[i]); i++; }
      i++;
      out.push('<pre style="white-space:pre;overflow:auto;background:rgba(0,0,0,.25);border-radius:8px;padding:8px;margin:0 0 10px;font-size:.85em">' + esc(buf.join("\\n")) + '</pre>');
      continue;
    }
    const hm = line.match(/^(#{1,6})\\s+(.*)$/);
    if (hm) {
      flushPara(); flushList();
      const sizes = {1:"1.25rem",2:"1.1rem",3:"1rem",4:".95rem",5:".9rem",6:".85rem"};
      out.push('<div style="font-weight:700;color:#fafafa;margin:14px 0 6px;font-size:' + (sizes[hm[1].length] || "1rem") + '">' + inlineMd(hm[2]) + '</div>');
      i++; continue;
    }
    if (/^(---+|\\*\\*\\*+|___+)\\s*$/.test(line.trim())) {
      flushPara(); flushList();
      out.push('<hr style="border:0;border-top:1px solid rgba(255,255,255,.12);margin:12px 0">');
      i++; continue;
    }
    if (/^>\\s?/.test(line)) {
      flushPara(); flushList();
      const buf = [];
      while (i < lines.length && /^>\\s?/.test(lines[i])) { buf.push(lines[i].replace(/^>\\s?/, "")); i++; }
      out.push('<blockquote style="border-left:3px solid rgba(255,255,255,.18);padding-left:10px;margin:0 0 10px;color:#a1a1aa">' + buf.map(inlineMd).join("<br>") + '</blockquote>');
      continue;
    }
    const um = line.match(/^\\s*[-*+]\\s+(.*)$/);
    if (um) { flushPara(); if (listType && listType !== "ul") flushList(); listType = "ul"; listItems.push(um[1]); i++; continue; }
    const om = line.match(/^\\s*\\d+\\.\\s+(.*)$/);
    if (om) { flushPara(); if (listType && listType !== "ol") flushList(); listType = "ol"; listItems.push(om[1]); i++; continue; }
    if (!line.trim()) { flushPara(); flushList(); i++; continue; }
    flushList(); para.push(line); i++;
  }
  flushPara(); flushList();
  return out.join("");
}

const SCROLL_MAX = "max-height:calc(100vh - 170px);overflow:auto";
const brandFileCache = {};
let currentSideTab = "";
async function renderBrandFile(which) {
  const isYaml = which === "yaml";
  const tabKey = isYaml ? "brandyaml" : "brandmd";
  const label = isYaml ? "brand.yaml" : "brand.md";
  const rawUrl = isYaml ? D.brand_yaml_url : D.brand_md_url;
  const body = $("side-body");
  const rawLink = rawUrl ? `<a href="${rawUrl}" target="_blank" class="btn btn-ghost" style="height:26px;padding:0 9px;font-size:11px">open raw ↗</a>` : "";
  const head = `<div class="flex items-center justify-between gap-2 mb-2"><span class="text-xs font-semibold text-zinc-300">${label}</span>${rawLink}</div>`;
  if (brandFileCache[which] === undefined) {
    body.innerHTML = head + '<div class="text-xs text-zinc-500">Loading…</div>';
    try {
      const r = await fetch("/api/brandfile?version=" + encodeURIComponent(D.version) + "&which=" + which);
      if (!r.ok) throw new Error("status " + r.status);
      brandFileCache[which] = await r.text();
    } catch (e) {
      brandFileCache[which] = null;
    }
  }
  if (currentSideTab !== tabKey) return;  // user switched tabs while we awaited
  const text = brandFileCache[which];
  if (text == null || !text.trim()) {
    body.innerHTML = head + '<div class="card p-6 text-sm text-zinc-500">Not generated yet.</div>';
    return;
  }
  if (isYaml) {
    body.innerHTML = head + `<pre class="text-xs text-zinc-200 font-mono leading-relaxed" style="white-space:pre;margin:0;padding:10px;background:rgba(0,0,0,.25);border-radius:8px;${SCROLL_MAX}">${esc(text)}</pre>`;
  } else {
    body.innerHTML = head + `<div class="text-sm text-zinc-200 leading-relaxed" style="word-break:break-word;${SCROLL_MAX}">${mdToHtml(text)}</div>`;
  }
}

function paintSideTab(active) {
  currentSideTab = active;
  $("side-tabs").querySelectorAll("button").forEach(x => x.classList.toggle("on", x.dataset.s === active));
  const body = $("side-body");
  if (active === "assets") { body.innerHTML = renderAssets(); return; }
  if (active === "catalog") { body.innerHTML = renderCatalog(); return; }
  if (active === "onbrand") { body.innerHTML = renderOnbrand(); return; }
  if (active === "visual") { body.innerHTML = renderVisual(); return; }
  if (active === "brandyaml") { renderBrandFile("yaml"); return; }
  if (active === "brandmd") { renderBrandFile("md"); return; }
  body.innerHTML = `<pre class="text-xs text-zinc-200 whitespace-pre-wrap leading-relaxed">${esc(docs[active] || "Not produced for this run.")}</pre>`;
}
$("side-tabs").innerHTML = sideTabs.map(t => `<button data-s="${t[0]}" class="btn btn-ghost" style="height:28px;padding:0 9px;font-size:11px">${t[1]}</button>`).join("");
$("side-tabs").querySelectorAll("button").forEach(b => b.onclick = () => paintSideTab(b.dataset.s));
paintSideTab((sideTabs[0] || ["assets"])[0]);

let sideOpen = true;
$("info-toggle").onclick = () => {
  sideOpen = !sideOpen;
  $("sidebar").style.display = sideOpen ? "flex" : "none";
  $("info-toggle").textContent = sideOpen ? "Info ◂" : "Info ▸";
  setTimeout(fitAll, 60);
};
</script></body></html>""".replace("__DATA__", data_json)


def main() -> None:
    port = int(os.environ.get("STUDIO_PORT", "1500"))
    STUDIO_DIR.mkdir(parents=True, exist_ok=True)
    try:
        server = ThreadingHTTPServer(("127.0.0.1", port), StudioHandler)
    except OSError as exc:
        if exc.errno in (48, 98):  # macOS EADDRINUSE / Linux EADDRINUSE
            print(
                f"Port {port} is already in use.\n"
                f"  Stop the other server first (often: python3 -m http.server {port}).\n"
                f"  lsof -i :{port}\n"
                f"  Or pick another port: STUDIO_PORT=8800 ./venv/bin/python studio_server.py",
                file=sys.stderr,
            )
        else:
            print(f"Could not bind to 127.0.0.1:{port}: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    print(f"Design System Studio → http://127.0.0.1:{port}/studio")
    print(f"Comparison viewer    → http://127.0.0.1:{port}/viewer.html")
    print(f"  (serving static files + runs from {PROJECT_DIR})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nshutting down")
        server.shutdown()


if __name__ == "__main__":
    main()
