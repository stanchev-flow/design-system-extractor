#!/usr/bin/env python3
"""Publish a brand run's FINAL results as a small, self-contained, tracked bundle.

`runs/` is gitignored (2.8 GB) and a single run carries node_modules, source
mirrors, per-page crops and full-resolution captures. None of that can be shared.
This script exports only the finished deliverables of one run into a browsable
directory that is committed to the repo and served as-is by the Studio server
(`studio_server.py` serves the repo root, so the bundle needs no new routes).

What lands in the bundle:
  replica/     the composed replica of the source page + its fidelity report
  harness/     the components/harness preview + the per-pattern layout pages
  catalog/     the component catalog page (when the run produced one)
  framework/   the built React/Vite framework app (single-file `dist/index.html`)
  brand/       the authored brand facts (yaml/json) — the extraction deliverable
  logs/        run logs + manifest so a reader can see what passed
  assets/      ONE deduped copy of the media the pages above actually reference
  index.html   landing page explaining and linking every artifact
  README.md    the same, for readers on GitHub
  published.json  machine-readable manifest the Studio dashboard discovers

Relocation is the interesting part: the run's pages reference media three
different ways (`assets/x.png` next to the page, `/runs/<run>/brand/assets/x.png`
absolute from the framework build, and `assets/x.png` from nested layout pages).
Every copied HTML/CSS file is rewritten to point at the single bundle-level
`assets/` dir via a relative path, so the bundle browses identically over the
Studio, over any static host, and from `file://`.

Usage:
    ./venv/bin/python tools/publish_run_bundle.py --run runs/greenhouse-4
    ./venv/bin/python tools/publish_run_bundle.py --run runs/greenhouse-4 \
        --out artifacts/published/greenhouse-4 --base-url http://127.0.0.1:1500

Every page is loaded in headless Chromium afterwards (unless `--no-verify`): that
asserts each one renders content with no broken images or 404s, and produces the
landing page's preview thumbnails. Pass `--base-url` to check it over the running
Studio instead of `file://`.

Re-runnable: managed subdirectories are replaced on each run, so a second
invocation over the same output dir is idempotent and drops stale files.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Subdirectories this script owns end-to-end: wiped and rewritten on every run so
# renames/removals upstream can never leave orphans in a published bundle.
# `previews/` is deliberately absent: it is owned by the verification pass, so a
# --no-verify re-export keeps the previews it cannot regenerate.
MANAGED_DIRS = ("assets", "replica", "harness", "catalog", "framework", "brand", "logs")

# Media referenced by the exported pages. Extensions only — names come from the
# pages themselves, never from a directory listing, so nothing unreferenced ships.
ASSET_EXTS = "png|jpe?g|webp|avif|gif|svg|ico|woff2?|ttf|otf|mp4|webm"

# A reference to `<anything>/assets/<name>.<ext>` that starts at an attribute or
# CSS-value boundary. The lookbehind keeps `https://cdn.example/assets/x.png`
# from matching mid-URL (its match would start after a `/`), and every candidate
# is additionally required to resolve to a real file in the run before rewriting.
ASSET_REF_RE = re.compile(
    r"""(?<=["'(\s=,])(?P<ref>/?(?:[\w.~%+-]+/)*assets/(?P<name>[\w.~%+-]+\.(?:"""
    + ASSET_EXTS
    + r""")))""",
    re.IGNORECASE,
)

# Brand fact files, in the order a reader should meet them. (filename, blurb).
BRAND_FACTS = [
    ("brand.yaml", "Authored brand facts: tokens, surfaces, components, section patterns."),
    ("brand.md", "The same design system as a readable document."),
    ("layout-library.yaml", "Measured layout patterns (one entry per composable section shape)."),
    ("section-copy.yaml", "Verbatim copy captured per section."),
    ("media-assets.yaml", "Media registry: every asset with role, geometry and section binding."),
    ("brand-chrome.yaml", "Measured nav/footer facts (links are captured, never invented)."),
    ("style-scale.yaml", "Normalised type/space scales."),
    ("voice-facts.yaml", "Voice evidence extracted from the source copy."),
    ("voice.md", "Voice guidance derived from those facts."),
    ("assets-manifest.json", "Curated asset manifest (source URL → local file, with tags)."),
    ("media-guidance.yaml", "Art-direction guidance for generated media slots."),
]

# Fact files that live deeper in the run but belong with the rest. dest -> source.
BRAND_FACTS_NESTED = {
    "asset-placements.json": ("evidence/asset-placements.json", "Measured on-page placements for each asset."),
}


def size_of(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file())


def fmt_size(num_bytes: int) -> str:
    for unit, div in (("GB", 1 << 30), ("MB", 1 << 20), ("KB", 1 << 10)):
        if num_bytes >= div:
            return f"{num_bytes / div:.1f} {unit}"
    return f"{num_bytes} B"


class AssetPool:
    """Collects the media the exported pages reference into one deduped dir.

    Names are kept as-is (they are already content-prefixed by the extractor).
    A name that appears in several run-local asset dirs with DIFFERENT bytes gets
    a numeric suffix so nothing is silently overwritten.
    """

    def __init__(self, out_assets: Path, search_dirs: list[Path]):
        self.out_assets = out_assets
        self.search_dirs = [d for d in search_dirs if d.is_dir()]
        self.published: dict[str, str] = {}  # source path -> published filename
        self.missing: set[str] = set()

    def resolve(self, name: str, near: Path | None = None) -> str | None:
        """Copy `name` into the pool (once) and return its published filename."""
        candidates = []
        if near is not None:
            candidates.append(near / "assets" / name)
        candidates += [d / name for d in self.search_dirs]
        src = next((c for c in candidates if c.is_file()), None)
        if src is None:
            self.missing.add(name)
            return None
        key = str(src.resolve())
        if key in self.published:
            return self.published[key]
        dest_name = name
        i = 1
        while (self.out_assets / dest_name).exists():
            # Same name already published from a different source file.
            if (self.out_assets / dest_name).stat().st_size == src.stat().st_size and (
                self.out_assets / dest_name
            ).read_bytes() == src.read_bytes():
                break
            stem, ext = os.path.splitext(name)
            dest_name = f"{stem}~{i}{ext}"
            i += 1
        self.out_assets.mkdir(parents=True, exist_ok=True)
        if not (self.out_assets / dest_name).exists():
            shutil.copy2(src, self.out_assets / dest_name)
        self.published[key] = dest_name
        return dest_name

    @property
    def count(self) -> int:
        return len(set(self.published.values()))


def rewrite_asset_refs(text: str, page: Path, out_dir: Path, pool: AssetPool, near: Path | None) -> tuple[str, int]:
    """Repoint every resolvable `.../assets/<file>` reference at the bundle pool."""
    rel_prefix = os.path.relpath(out_dir / "assets", page.parent).replace(os.sep, "/")
    hits = 0

    def sub(m: re.Match[str]) -> str:
        nonlocal hits
        published = pool.resolve(m.group("name"), near=near)
        if published is None:
            return m.group("ref")
        hits += 1
        return f"{rel_prefix}/{published}"

    return ASSET_REF_RE.sub(sub, text), hits


def normalise_title(text: str, title: str) -> str:
    """Give a relocated page an honest <title> (Vite scaffolds keep a stale one)."""
    return re.sub(r"<title>.*?</title>", f"<title>{html.escape(title)}</title>", text, count=1, flags=re.S)


def copy_page(src: Path, dest: Path, out_dir: Path, pool: AssetPool, *, title: str | None = None) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    text = src.read_text(encoding="utf-8", errors="replace")
    text, _ = rewrite_asset_refs(text, dest, out_dir, pool, near=src.parent)
    if title:
        text = normalise_title(text, title)
    dest.write_text(text, encoding="utf-8")


def copy_plain(src: Path, dest: Path) -> bool:
    if not src.is_file():
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    return True


def load_run_meta(run_dir: Path) -> dict:
    meta: dict = {"name": run_dir.name}
    for fname, keys in (("manifest.json", None), ("studio-project.json", None)):
        path = run_dir / fname
        if not path.is_file():
            continue
        try:
            meta[fname.split(".")[0]] = json.loads(path.read_text())
        except Exception as exc:  # noqa: BLE001
            print(f"  warn: could not parse {fname}: {exc}")
    manifest = meta.get("manifest", {})
    project = meta.get("studio-project", {})
    meta["brand"] = manifest.get("brand") or project.get("title") or run_dir.name
    meta["title"] = project.get("title") or meta["brand"]
    meta["source_url"] = manifest.get("source_url") or project.get("url") or ""
    return meta


def export(run_dir: Path, out_dir: Path) -> dict:
    brand_dir = run_dir / "brand"
    if not brand_dir.is_dir():
        raise SystemExit(f"no brand dir under {run_dir} — is this a brand run?")

    meta = load_run_meta(run_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for name in MANAGED_DIRS:
        shutil.rmtree(out_dir / name, ignore_errors=True)

    pool = AssetPool(
        out_dir / "assets",
        [
            brand_dir / "assets",
            brand_dir / "harness" / "layouts" / "assets",
            brand_dir / "compose" / "replica" / "assets",
        ],
    )
    lanes: list[dict] = []
    replica_overall = None

    # ── replica: the composed rebuild of the source page, plus its fidelity proof
    replica_src = brand_dir / "compose" / "replica"
    if (replica_src / "index.html").is_file():
        copy_page(
            replica_src / "index.html",
            out_dir / "replica" / "index.html",
            out_dir,
            pool,
            title=f"{meta['brand']} — composed replica",
        )
        for name in (
            "replica-report.md",
            "replica-report.json",
            "replica-rects.json",
            "composition.json",
            "tokens.manifest.json",
            "replica-fullpage.png",
        ):
            copy_plain(replica_src / name, out_dir / "replica" / name)
        for diff in sorted((replica_src / "diff").glob("*.png")):
            copy_plain(diff, out_dir / "replica" / "diff" / diff.name)
        report = {}
        try:
            report = json.loads((replica_src / "replica-report.json").read_text())
        except Exception:  # noqa: BLE001
            pass
        # The report next to the page is the truth for the page being published;
        # the run manifest can predate a later replica rebuild.
        replica_overall = report.get("overall")
        lanes.append(
            {
                "kind": "replica",
                "label": "Composed replica of the source page",
                "path": "replica/index.html",
                "note": (
                    f"Rebuilt from the extracted facts alone. Fidelity score "
                    f"{report.get('overall', '—')} against the source capture; per-band "
                    "scores and the punch list are in replica-report.md."
                ),
                "extras": [
                    {"label": "Fidelity report (markdown)", "path": "replica/replica-report.md"},
                    {"label": "Full-page render (PNG)", "path": "replica/replica-fullpage.png"},
                ],
            }
        )

    # ── harness: every composable pattern rendered on its own, plus the index
    harness_src = brand_dir / "harness"
    if (harness_src / "index.html").is_file():
        copy_page(
            harness_src / "index.html",
            out_dir / "harness" / "index.html",
            out_dir,
            pool,
            title=f"{meta['brand']} — components & layout harness",
        )
        for layout in sorted((harness_src / "layouts").glob("*.html")):
            copy_page(layout, out_dir / "harness" / "layouts" / layout.name, out_dir, pool)
        for name in ("harness-quality.json", "tokens.manifest.json"):
            copy_plain(harness_src / name, out_dir / "harness" / name)
        lanes.append(
            {
                "kind": "harness",
                "label": "Components & layout harness",
                "path": "harness/index.html",
                "note": (
                    "Primitives, surfaces, blocks and every measured layout pattern rendered "
                    "from the design system. Each pattern is also a standalone page under "
                    "harness/layouts/."
                ),
            }
        )

    # ── catalog: the component catalog page, when the run built one
    catalog_src = brand_dir / "catalog"
    if (catalog_src / "index.html").is_file():
        copy_page(
            catalog_src / "index.html",
            out_dir / "catalog" / "index.html",
            out_dir,
            pool,
            title=f"{meta['brand']} — component catalog",
        )
        copy_plain(catalog_src / "catalog.json", out_dir / "catalog" / "catalog.json")
        lanes.append(
            {
                "kind": "catalog",
                "label": "Component catalog",
                "path": "catalog/index.html",
                "note": "Machine-readable inventory of the components the extraction declared.",
            }
        )

    # ── framework: the built React app. Prefer the app's own dist/ over any copy.
    fw_src = brand_dir / "framework"
    fw_build = next(
        (
            p
            for p in (
                *sorted(fw_src.glob("single/*/dist/index.html")),
                fw_src / "index.html",
            )
            if p.is_file()
        ),
        None,
    )
    if fw_build is not None:
        copy_page(
            fw_build,
            out_dir / "framework" / "index.html",
            out_dir,
            pool,
            title=f"{meta['brand']} — framework build (React + Vite)",
        )
        copy_plain(fw_src / "framework-report.json", out_dir / "framework" / "framework-report.json")
        copy_plain(fw_src / "brand-assets.json", out_dir / "framework" / "brand-assets.json")
        lanes.append(
            {
                "kind": "framework",
                "label": "Framework build (React + Vite, single file)",
                "path": "framework/index.html",
                "note": (
                    "The opt-in framework lane: a real React + Tailwind app generated from the "
                    "same facts, built to one self-contained HTML file. Source stays in the run "
                    f"dir ({fw_build.parent.parent.relative_to(REPO_ROOT)})."
                ),
            }
        )

    # ── brand facts: the actual output of the extraction
    facts: list[dict] = []
    for name, blurb in BRAND_FACTS:
        if copy_plain(brand_dir / name, out_dir / "brand" / name):
            facts.append({"path": f"brand/{name}", "note": blurb})
    for dest, (rel, blurb) in BRAND_FACTS_NESTED.items():
        if copy_plain(brand_dir / rel, out_dir / "brand" / dest):
            facts.append({"path": f"brand/{dest}", "note": blurb})

    # ── provenance: logs, manifest, and the scripts that produced the run
    logs: list[dict] = []
    for log in sorted(run_dir.glob("*.log")):
        if copy_plain(log, out_dir / "logs" / log.name):
            logs.append({"path": f"logs/{log.name}"})
    for name in ("manifest.json", "changes.md", "extract_pages.sh", "build_framework_lane.py"):
        copy_plain(run_dir / name, out_dir / "logs" / name)

    manifest = {
        "schemaVersion": "published-bundle.v1",
        "name": out_dir.name,
        "run": str(run_dir.relative_to(REPO_ROOT)) if run_dir.is_relative_to(REPO_ROOT) else str(run_dir),
        "brand": meta["brand"],
        "title": meta["title"],
        "source_url": meta["source_url"],
        "published_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "replica_overall": replica_overall,
        "lanes": lanes,
        "facts": facts,
        "logs": logs,
        "assets_published": pool.count,
        "assets_unresolved": sorted(pool.missing),
        "run_manifest": meta.get("manifest", {}),
    }
    finalize(manifest, out_dir)
    return manifest


def finalize(manifest: dict, out_dir: Path) -> None:
    """(Re)write the human + machine entry points once the payload is final."""
    manifest["bytes"] = size_of(out_dir)
    (out_dir / "index.html").write_text(render_landing(manifest, out_dir))
    (out_dir / "README.md").write_text(render_readme(manifest, out_dir))
    (out_dir / "published.json").write_text(json.dumps(manifest, indent=2) + "\n")
    write_published_index(out_dir.parent)


# ── landing page ───────────────────────────────────────────────────────────────

LANDING_CSS = """
:root { color-scheme: dark; --bg:#0b0b0d; --card:#14141a; --line:#26262f; --ink:#f4f4f5;
        --muted:#a1a1aa; --accent:#34d399; }
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--ink); font:15px/1.6 ui-sans-serif,-apple-system,"Segoe UI",Inter,sans-serif; }
.wrap { max-width: 1040px; margin: 0 auto; padding: 48px 24px 72px; }
h1 { font-size: 30px; letter-spacing:-.02em; margin: 0 0 6px; }
h2 { font-size: 13px; text-transform: uppercase; letter-spacing:.12em; color:var(--muted); margin: 40px 0 14px; font-weight:600; }
a { color: var(--accent); }
.sub { color: var(--muted); margin: 0 0 4px; }
.grid { display:grid; gap:16px; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); }
.card { background:var(--card); border:1px solid var(--line); border-radius:14px; overflow:hidden; display:flex; flex-direction:column; }
.card .shot { display:block; background:#000; aspect-ratio: 16/10; object-fit: cover; object-position: top center; width:100%; border-bottom:1px solid var(--line); }
.card .body { padding:16px 18px 18px; }
.card h3 { margin:0 0 6px; font-size:16px; }
.card h3 a { text-decoration:none; }
.card p { margin:0; color:var(--muted); font-size:13px; }
.chip { display:inline-block; font-size:10px; letter-spacing:.1em; text-transform:uppercase; color:#0b0b0d;
        background:var(--accent); border-radius:999px; padding:2px 8px; margin-bottom:10px; font-weight:700; }
.extras { margin:10px 0 0; padding:0; list-style:none; font-size:12px; }
.extras li { margin-top:4px; }
table { width:100%; border-collapse:collapse; font-size:13px; }
th, td { text-align:left; padding:8px 10px; border-bottom:1px solid var(--line); vertical-align:top; }
th { color:var(--muted); font-weight:600; font-size:11px; text-transform:uppercase; letter-spacing:.08em; }
td code { color:var(--ink); }
.meta { display:flex; flex-wrap:wrap; gap:8px 20px; color:var(--muted); font-size:13px; margin:14px 0 0; }
.note { color:var(--muted); font-size:13px; max-width:70ch; }
footer { margin-top:48px; color:#71717a; font-size:12px; }
"""


def _e(text) -> str:
    return html.escape(str(text if text is not None else ""))


def render_landing(manifest: dict, out_dir: Path) -> str:
    rm = manifest.get("run_manifest") or {}
    replica = manifest.get("replica_overall")
    validation = rm.get("validation") or {}
    cards = []
    for lane in manifest["lanes"]:
        shot = out_dir / "previews" / f"{lane['kind']}.png"
        img = (
            f'<img class="shot" src="previews/{lane["kind"]}.png" alt="{_e(lane["label"])} preview" loading="lazy">'
            if shot.is_file()
            else ""
        )
        extras = "".join(
            f'<li><a href="{_e(x["path"])}">{_e(x["label"])}</a></li>' for x in lane.get("extras", [])
        )
        cards.append(
            f'<article class="card">{img}<div class="body">'
            f'<span class="chip">{_e(lane["kind"])}</span>'
            f'<h3><a href="{_e(lane["path"])}">{_e(lane["label"])} →</a></h3>'
            f'<p>{_e(lane.get("note", ""))}</p>'
            + (f'<ul class="extras">{extras}</ul>' if extras else "")
            + "</div></article>"
        )
    fact_rows = "".join(
        f'<tr><td><a href="{_e(f["path"])}"><code>{_e(Path(f["path"]).name)}</code></a></td>'
        f'<td>{_e(f.get("note", ""))}</td>'
        f'<td>{fmt_size(size_of(out_dir / f["path"]))}</td></tr>'
        for f in manifest["facts"]
    )
    log_rows = "".join(
        f'<tr><td><a href="{_e(f["path"])}"><code>{_e(Path(f["path"]).name)}</code></a></td>'
        f'<td>{fmt_size(size_of(out_dir / f["path"]))}</td></tr>'
        for f in manifest["logs"]
    )
    source = manifest.get("source_url") or ""
    source_link = f'<a href="{_e(source)}" rel="noopener">{_e(source)}</a>' if source else "—"
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_e(manifest["brand"])} — published extraction results</title>
<style>{LANDING_CSS}</style></head>
<body><div class="wrap">
<h1>{_e(manifest["brand"])} — published extraction results</h1>
<p class="sub">Everything below was generated from screenshots and DOM/CSS measurements of the
source site. No hand-written page code: the design system is extracted into facts, and the pages
are composed back out of those facts as proof the facts are complete.</p>
<div class="meta">
  <span>source: {source_link}</span>
  <span>run: <code>{_e(manifest["run"])}</code></span>
  <span>published: {_e(manifest["published_at"])}</span>
  {f'<span>replica fidelity: <strong>{_e(replica)}</strong></span>' if replica is not None else ''}
  {f'<span>schema validation: {_e(validation.get("c1_c28_errors", 0))} errors / {_e(validation.get("c1_c28_warnings", 0))} warnings</span>' if validation else ''}
  <span>media: {_e(manifest["assets_published"])} files</span>
</div>

<h2>Rendered results</h2>
<div class="grid">{"".join(cards)}</div>

<h2>Brand facts — the extraction output</h2>
<p class="note">These files are the deliverable; every rendered page above is derived from them.</p>
<table><thead><tr><th>file</th><th>what it is</th><th>size</th></tr></thead><tbody>{fact_rows}</tbody></table>

<h2>What happened — logs &amp; manifest</h2>
<table><thead><tr><th>file</th><th>size</th></tr></thead><tbody>
<tr><td><a href="logs/changes.md"><code>changes.md</code></a></td><td>{fmt_size(size_of(out_dir / "logs" / "changes.md"))}</td></tr>
<tr><td><a href="logs/manifest.json"><code>manifest.json</code></a></td><td>{fmt_size(size_of(out_dir / "logs" / "manifest.json"))}</td></tr>
{log_rows}</tbody></table>

<footer>Exported with <code>tools/publish_run_bundle.py</code> from <code>{_e(manifest["run"])}</code>.
Re-run: <code>./venv/bin/python tools/publish_run_bundle.py --run {_e(manifest["run"])}</code>.
The full run (source captures, crops, evidence, app sources, node_modules) stays local — it is
gitignored and ~300&nbsp;MB.</footer>
</div></body></html>
"""


def render_readme(manifest: dict, out_dir: Path) -> str:
    replica = manifest.get("replica_overall")
    lines = [
        f"# {manifest['brand']} — published extraction results",
        "",
        f"- source site: {manifest.get('source_url') or '—'}",
        f"- run of record: `{manifest['run']}` (gitignored; this directory is the shareable export)",
        f"- published: {manifest['published_at']}",
        f"- bundle size: {fmt_size(size_of(out_dir))} · {manifest['assets_published']} media files",
    ]
    if replica is not None:
        lines.append(f"- replica fidelity score: {replica}")
    lines += [
        "",
        "Browse it through the local Studio server (`./start-studio.sh`, port 1500):",
        "",
        f"    http://127.0.0.1:1500/{out_dir.relative_to(REPO_ROOT).as_posix()}/index.html",
        "",
        "Or open `index.html` directly — every path in the bundle is relative, so it also works",
        "from `file://` or any static host.",
        "",
        "## Contents",
        "",
    ]
    for lane in manifest["lanes"]:
        lines.append(f"- **{lane['label']}** — `{lane['path']}`  \n  {lane.get('note', '')}")
    lines += [
        "- **Brand facts** — `brand/`  \n  The authored extraction output (yaml/json); every page above is derived from it.",
        "- **Logs & manifest** — `logs/`  \n  Run logs, schema validation output, and `changes.md`.",
        "- **Media** — `assets/`  \n  One deduped copy of the media the pages actually reference.",
        "",
        "## Regenerating",
        "",
        "```sh",
        f"./venv/bin/python tools/publish_run_bundle.py --run {manifest['run']} \\",
        f"    --out {out_dir.relative_to(REPO_ROOT).as_posix()}",
        "```",
        "",
        "The script copies only finished artifacts, rewrites every asset reference to this",
        "bundle's `assets/` dir, then loads each page in headless Chromium to assert it renders",
        "content with no broken images (add `--base-url http://127.0.0.1:1500` to check it over the",
        "running Studio, `--no-verify` to skip). Results land in `verify.json`.",
        "",
    ]
    return "\n".join(lines)


def write_published_index(root: Path) -> None:
    """Directory landing page listing every published bundle under `root`."""
    bundles = []
    for manifest_path in sorted(root.glob("*/published.json")):
        try:
            bundles.append(json.loads(manifest_path.read_text()))
        except Exception:  # noqa: BLE001
            continue
    if not bundles:
        return
    rows = "".join(
        f'<article class="card"><div class="body">'
        f'<h3><a href="{_e(b["name"])}/index.html">{_e(b["brand"])} →</a></h3>'
        f'<p>{_e(b.get("source_url") or "")}<br>published {_e(b.get("published_at"))} · '
        f'{fmt_size(b.get("bytes", 0))} · {len(b.get("lanes", []))} rendered lanes</p>'
        "</div></article>"
        for b in bundles
    )
    (root / "index.html").write_text(
        f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Published extraction results</title><style>{LANDING_CSS}</style></head>
<body><div class="wrap">
<h1>Published extraction results</h1>
<p class="sub">Self-contained exports of finished pipeline runs — committed to the repo and served
by the Studio, so they need no local run data.</p>
<h2>Bundles</h2>
<div class="grid">{rows}</div>
</div></body></html>
"""
    )


# ── verification (also produces the landing-page previews) ─────────────────────

PREVIEW_WIDTH = 860


def verify(out_dir: Path, manifest: dict, base_url: str | None) -> dict:
    """Load every exported page in headless Chromium; assert content + assets.

    Writes `verify.json` and, for each rendered lane, a downscaled preview PNG
    used by the landing page. Returns the report. Skips (loudly) when Playwright
    or its browser is unavailable, so the export itself never depends on it.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("  verify: playwright not installed — skipped")
        return {}

    full_pages = ["index.html"] + [lane["path"] for lane in manifest["lanes"]]
    pages = full_pages + sorted(
        str(p.relative_to(out_dir)) for p in (out_dir / "harness" / "layouts").glob("*.html")
    )
    rel_root = out_dir.relative_to(REPO_ROOT).as_posix()
    results: list[dict] = []
    shutil.rmtree(out_dir / "previews", ignore_errors=True)

    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch()
        except Exception as exc:  # noqa: BLE001
            print(f"  verify: chromium unavailable ({exc}) — skipped")
            return {}
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
        for rel in pages:
            page = ctx.new_page()
            failed: list[str] = []
            errors: list[str] = []
            local_prefix = f"{base_url.rstrip('/')}/{rel_root}/" if base_url else out_dir.as_uri()

            def note_failure(url: str, detail: str, sink=failed, prefix=local_prefix) -> None:
                # Only the bundle's own resources are the bundle's problem; webfonts
                # and other third-party requests depend on the reader's network.
                if url.startswith(prefix):
                    sink.append(detail)

            page.on("requestfailed", lambda req: note_failure(req.url, req.url))
            page.on(
                "response",
                lambda res: note_failure(res.url, f"{res.status} {res.url}") if res.status >= 400 else None,
            )
            page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
            url = f"{base_url.rstrip('/')}/{rel_root}/{rel}" if base_url else (out_dir / rel).as_uri()
            entry = {"page": rel, "url": url}
            try:
                page.goto(url, wait_until="load", timeout=45_000)
                page.wait_for_timeout(1200)
                stats = page.evaluate(
                    """() => {
                        const imgs = Array.from(document.images);
                        return {
                          text: (document.body ? document.body.innerText : '').trim().length,
                          nodes: document.querySelectorAll('*').length,
                          images: imgs.length,
                          broken: imgs.filter(i => i.complete && i.naturalWidth === 0)
                                      .map(i => i.getAttribute('src')),
                        };
                    }"""
                )
                entry.update(stats)
                entry["failed_requests"] = sorted(set(failed))
                entry["console_errors"] = errors[:5]
                # Full pages must be substantial (the framework build is a React app:
                # a blank #root would score near zero here). A single composed section
                # can legitimately be one heading and a button, so it only has to have
                # rendered *something* — with every referenced image resolving.
                min_text = 200 if rel in full_pages else 15
                entry["ok"] = (
                    stats["nodes"] > 10
                    and stats["text"] >= min_text
                    and not stats["broken"]
                    and not entry["failed_requests"]
                )
                lane_kind = next(
                    (l["kind"] for l in manifest["lanes"] if l["path"] == rel), "landing" if rel == "index.html" else None
                )
                if lane_kind and lane_kind != "landing":
                    shot = out_dir / "previews" / f"{lane_kind}.png"
                    shot.parent.mkdir(parents=True, exist_ok=True)
                    page.screenshot(path=str(shot))
                    _downscale(shot, PREVIEW_WIDTH)
            except Exception as exc:  # noqa: BLE001
                entry.update({"ok": False, "error": str(exc)})
            results.append(entry)
            page.close()
        browser.close()

    report = {
        "checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "base": base_url or "file://",
        "pages": results,
        "ok": all(r.get("ok") for r in results),
    }
    (out_dir / "verify.json").write_text(json.dumps(report, indent=2) + "\n")
    bad = [r for r in results if not r.get("ok")]
    print(f"  verify: {len(results) - len(bad)}/{len(results)} pages ok ({report['base']})")
    for r in bad:
        detail = r.get("error") or f"text={r.get('text')} broken={r.get('broken')} failed={r.get('failed_requests')}"
        print(f"    FAIL {r['page']}: {detail}")
    return report


def _downscale(path: Path, width: int) -> None:
    try:
        from PIL import Image
    except ImportError:
        return
    with Image.open(path) as im:
        if im.width <= width:
            return
        im = im.convert("RGB").resize((width, round(im.height * width / im.width)), Image.LANCZOS)
        im.save(path, optimize=True)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", required=True, help="run directory, e.g. runs/greenhouse-4")
    ap.add_argument(
        "--out",
        default=None,
        help="output bundle dir (default: artifacts/published/<run name>)",
    )
    ap.add_argument(
        "--no-verify",
        dest="verify",
        action="store_false",
        help="skip the headless-Chromium pass (it is what proves the bundle browses, and it builds the landing-page previews)",
    )
    ap.add_argument("--base-url", default=None, help="verify over HTTP through this origin instead of file://")
    args = ap.parse_args(argv)

    run_dir = Path(args.run).resolve()
    if not run_dir.is_dir():
        raise SystemExit(f"run dir not found: {args.run}")
    out_dir = Path(args.out).resolve() if args.out else REPO_ROOT / "artifacts" / "published" / run_dir.name

    print(f"publishing {run_dir.name} -> {out_dir.relative_to(REPO_ROOT)}")
    manifest = export(run_dir, out_dir)
    for lane in manifest["lanes"]:
        print(f"  lane: {lane['kind']:<10} {lane['path']}")
    print(f"  brand facts: {len(manifest['facts'])} files")
    print(f"  media: {manifest['assets_published']} files, {fmt_size(size_of(out_dir / 'assets'))}")
    if manifest["assets_unresolved"]:
        print(f"  warn: {len(manifest['assets_unresolved'])} references did not resolve to a file:")
        for name in manifest["assets_unresolved"][:10]:
            print(f"    {name}")

    report = verify(out_dir, manifest, args.base_url) if args.verify else {}
    # Verification produces the lane previews, so the entry points are rewritten
    # afterwards to pick them up (and to record the final byte count).
    finalize(manifest, out_dir)

    total = size_of(out_dir)
    print("  size breakdown:")
    for child in sorted(out_dir.iterdir(), key=lambda p: -size_of(p)):
        print(f"    {fmt_size(size_of(child)):>9}  {child.name}")
    print(f"  TOTAL: {fmt_size(total)}")
    print(f"  open: http://127.0.0.1:1500/{out_dir.relative_to(REPO_ROOT).as_posix()}/index.html")
    if report and not report.get("ok"):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
