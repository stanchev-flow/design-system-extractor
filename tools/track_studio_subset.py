#!/usr/bin/env python3
"""Track the smallest subset of a run that still makes it a real Studio project.

`runs/` is gitignored (~2.8 GB local) so a clean clone has no projects to look at:
the Studio starts, lists whatever happens to be tracked, and renders empty panes.
This script closes that gap WITHOUT copying anything. The Studio reads `runs/` and
`screenshots/` directly, so the job is to selectively *track* files that are
already there, via `.gitignore` negations.

What counts as "Studio-useful" is not a guess: the include list below mirrors,
path for path, what `studio_server.py` actually opens when it renders the
dashboard card, the project page, and every tab. Anything the server never reads
is excluded — which is where nearly all the weight is (a run's framework build
tree, its extraction evidence, its archived copies).

Usage:
    ./venv/bin/python tools/track_studio_subset.py --run runs/<project>
    ./venv/bin/python tools/track_studio_subset.py --all
    ./venv/bin/python tools/track_studio_subset.py --run runs/<project> --files
    ./venv/bin/python tools/track_studio_subset.py --run runs/<project> \
        --write-gitignore --stage

By default this only measures and prints. `--write-gitignore` rewrites a marked
block in `.gitignore` (never touching the surrounding rules, and never removing
the `runs/` rule itself), and `--stage` runs `git add` over the resolved paths.
Both are idempotent, and additive: re-running after a project regenerates its
artifacts picks up whatever appeared. Taking something back OUT of tracking is
deliberately not automatic — a path that is already committed stays committed
until someone runs `git rm --cached` on it, so a rule change here can never
quietly delete history someone else is relying on.

Every project is handled by the same rules — no brand, lane or page name is
hardcoded anywhere in this file.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote, unquote

REPO_ROOT = Path(__file__).resolve().parent.parent
RUNS_DIR = REPO_ROOT / "runs"
SCREENSHOTS_DIR = REPO_ROOT / "screenshots"
GITIGNORE = REPO_ROOT / ".gitignore"

BEGIN_MARKER = "# BEGIN studio-subset (tools/track_studio_subset.py) — do not hand-edit"
END_MARKER = "# END studio-subset"

# ── what the Studio reads ─────────────────────────────────────────────────────
# Each entry is (glob relative to runs/<project>, why the Studio needs it). The
# globs are matched against POSIX relative paths with fnmatch, where `**` spans
# directory separators. Keep this list in sync with studio_server.py; the second
# element is printed in the report so the inclusion is always justified.
INCLUDE_RULES: tuple[tuple[str, str], ...] = (
    ("studio-project.json", "registers the project (title, url, created)"),
    ("manifest.json", "source url + source_pages, drives the Source pane"),
    ("brand/manifest.json", "fallback project manifest"),
    ("*.md", "run-level docs and prompt texts shown in the Docs tab"),
    ("*.yaml", "run-level docs shown in the Docs tab"),
    ("*.txt", "run-level provider/model notes shown in the Docs tab"),
    ("assets/assets-manifest.json", "Assets tab (roles + counts)"),
    ("assets/brand-assets.json", "Assets tab (harvested brand assets)"),
    ("*/screenshot.*", "dashboard card thumbnail"),
    ("*/single/**", "generated site lanes + every doc in the Docs tab"),
    ("brand/brand.yaml", "brand facts; also powers the origin catalog"),
    ("brand/brand.md", "brand doc linked from the project page"),
    ("brand/catalog/**", "Catalog tab (catalog.json + its standalone page)"),
    ("brand/compose/**", "Replica + generated page lanes and their thumbnails"),
    ("brand/variants/**", "hero variant lanes"),
    ("brand/harness/**", "raw harness spec book lane"),
    ("brand/sections/**", "sections bakeoff gallery lane"),
    ("brand/components-preview/**", "components preview lane"),
    ("brand/chrome/**", "exact nav/footer lane"),
    ("brand/render/**", "on-brand review panel (renders, crops, verdicts)"),
    # The brand-lane document tabs (`BRAND_DOCS` in studio_server.py). Named file
    # by file rather than by subtree: three of them sit inside brand/evidence/,
    # which is otherwise a many-megabyte extraction dump nothing serves, and the
    # tabs read these exact paths. 2.7 MB across every lane in this repo.
    ("brand/evidence/dom-sections.json", "Structural evidence tab"),
    ("brand/evidence/css-facts.json", "Structural evidence tab"),
    ("brand/evidence/computed-styles.json", "Structural evidence tab"),
    ("brand/evidence/motion-audit.json", "Structural evidence tab"),
    ("brand/evidence/grounding/*.yaml", "Grounding tab"),
    ("brand/style-scale.yaml", "Ledger tab"),
    ("brand/layout-library.yaml", "Sections tab"),
    ("brand/section-copy.yaml", "Sections tab"),
    ("brand/voice.md", "Voice tab"),
    ("brand/voice-facts.yaml", "Voice tab"),
    ("brand/author-report.json", "Author report tab"),
    ("brand/author-stage-status.json", "Author report tab"),
    ("brand/contract-projection-audit.json", "Contract audit tab"),
    ("brand/validation-report.md", "Validation tab"),
    ("validate-final.log", "Validation tab (preferred over the brand report)"),
    ("brand/changes.md", "Changelog tab, when the run keeps it under brand/"),
    ("brand/assets-manifest.json", "Assets tab on a brand lane (entries[] shape)"),
    ("brand/media-assets.yaml", "Assets tab badges (authored asset semantics)"),
)

# ── what never ships, and why ─────────────────────────────────────────────────
# Applied INSIDE the include rules above, so an allowed subtree can still shed
# the parts of itself that are build output, mirrors or scratch. Matched against
# the relative path and against every individual path segment.
EXCLUDE_RULES: tuple[tuple[str, str], ...] = (
    ("**/node_modules/**", "installed dependencies — regenerate with npm install"),
    ("**/.vite/**", "bundler cache"),
    ("**/__pycache__/**", "python bytecode"),
    ("**/*_files/**", "'Save Page As' source HTML mirror of the original site"),
    ("**/diff/**", "per-page diff crops — only a last-resort Source fallback"),
    ("**/*.bak", "hand-made backup copy of a file that is already tracked"),
    ("**/.DS_Store", "macOS finder metadata"),
)

# Directory names that mean "this whole subtree is a checked-out JS project", so
# it is dropped wholesale rather than file by file. A `package.json` sitting in a
# run directory always means a build workspace (Vite/shadcn framework lane), and
# those trees are 100x the size of everything else in the run put together.
JS_WORKSPACE_MARKER = "package.json"

# Top-level run directories that are never read by the Studio. Listed explicitly
# only so the report can explain the biggest line items instead of lumping them
# into a generic "not read" bucket.
NOT_READ_REASONS: dict[str, str] = {
    "_archive": "archived copy of an earlier run of the same project",
    "brand/evidence": "extraction evidence (page mirrors, crops, css dumps) — never served",
    "brand/framework": "framework build tree; the Studio links builds by port, not by file",
    "brand/kit": "design-kit export — not read by the Studio",
    "brand/shots": "ad-hoc capture scratch — not read by the Studio",
    "brand/assets": "harvested source-asset pool; served pages carry their own copy",
}

# Source captures: the Studio resolves ONE original-site image per project, but it
# tries several shapes. These are the shapes worth tracking; a capture folder also
# holds the saved HTML page and its `_files` mirror, which is the bulk of it.
SOURCE_IMAGE_EXTS = (".png", ".webp", ".jpg", ".jpeg", ".avif")

# Files worth reading before tracking them. This repo is public and some run
# artifacts record the machine they were produced on, so any text file carrying
# the absolute path of this checkout is held back by default (--allow-local-paths
# overrides, and the report always names the files so a held-back page is never
# a silent omission).
TEXT_EXTS = {
    ".json", ".md", ".yaml", ".yml", ".txt", ".html", ".htm", ".css", ".js",
    ".mjs", ".ts", ".tsx", ".csv", ".svg", ".log", ".sh", ".py",
}
LOCAL_PATH_MARKERS = (str(Path.home()), str(REPO_ROOT))


@lru_cache(maxsize=None)
def _compile(pattern: str) -> re.Pattern[str]:
    """Path-aware glob → regex, with gitignore semantics for `*` vs `**`.

    `*` stops at a separator and `**` spans them, which matters here: a loose
    `*/single/**` that crosses separators would silently pull a framework build
    tree back in through a rule meant for a run item.
    """
    out = ["^"]
    i = 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out.append("(?:[^/]+/)*")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    out.append("$")
    return re.compile("".join(out))


def _match(rel: str, pattern: str) -> bool:
    return _compile(pattern).match(rel) is not None


def _dir_size(path: Path) -> int:
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file() and not p.is_symlink())


def fmt_bytes(num: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if abs(num) < 1024 or unit == "GB":
            return f"{num:.0f} {unit}" if unit == "B" else f"{num:.1f} {unit}"
        num /= 1024
    return f"{num:.1f} GB"


def _in_js_workspace(path: Path, run_dir: Path) -> bool:
    """True when a directory between `path` and the run root is a JS project."""
    for parent in path.parents:
        if parent == run_dir:
            break
        if (parent / JS_WORKSPACE_MARKER).is_file():
            return True
    return False


def leaks_local_path(path: Path) -> bool:
    """True when a text artifact embeds the absolute path of this checkout."""
    if path.suffix.lower() not in TEXT_EXTS:
        return False
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False
    return any(marker in text for marker in LOCAL_PATH_MARKERS)


def classify_run(run_dir: Path, *, allow_local_paths: bool = False) -> dict:
    """Split one run into kept files and excluded files, each with a reason.

    Returns {"kept": [(path, bytes, why)], "dropped": [(path, bytes, why)]}, both
    sorted by size descending so the report leads with what actually matters.
    """
    kept: list[tuple[Path, int, str]] = []
    dropped: list[tuple[Path, int, str]] = []

    for path in sorted(run_dir.rglob("*")):
        if path.is_dir() or path.is_symlink():
            continue
        rel = path.relative_to(run_dir).as_posix()
        size = path.stat().st_size

        why_include = next((why for pat, why in INCLUDE_RULES if _match(rel, pat)), None)
        if why_include is None:
            prefix = next(
                (k for k in NOT_READ_REASONS if rel == k or rel.startswith(k + "/")), None
            )
            reason = NOT_READ_REASONS[prefix] if prefix else "not read by the Studio"
            dropped.append((path, size, reason))
            continue

        why_exclude = next((why for pat, why in EXCLUDE_RULES if _match(rel, pat)), None)
        if why_exclude is None and _in_js_workspace(path, run_dir):
            why_exclude = "inside a JS build workspace (package.json) — rebuild locally"
        if why_exclude is None and not allow_local_paths and leaks_local_path(path):
            why_exclude = "embeds this checkout's absolute path — would leak it publicly"
        if why_exclude is not None:
            dropped.append((path, size, why_exclude))
            continue

        kept.append((path, size, why_include))

    kept = _prune_unshown_images(run_dir, kept, dropped)
    kept.sort(key=lambda t: -t[1])
    dropped.sort(key=lambda t: -t[1])
    return {"kept": kept, "dropped": dropped, "redundant": _redundant_bytes(kept)}


# A lane's own capture dir. `_lane_thumb()` in studio_server.py picks exactly one
# image out of here (or out of the lane root) to illustrate the lane; the rest of
# the dir is contact sheets, per-viewport re-shoots and diff composites that no
# route ever serves.
_SHOTS_DIR = "shots"
# `sections_pages()` prefers this exact file over the generic thumb pick.
_GALLERY_THUMB = "gallery.png"


def _thumb_pick(lane_dir: Path) -> Path | None:
    """The one image `_lane_thumb()` would choose for a lane. Mirrors its scoring."""

    def score(p: Path) -> tuple:
        n = p.name.lower()
        is_page = "diff" not in n and "vs-source" not in n and "contact" not in n
        return (
            is_page,
            "fullpage" in n or "full" in n,
            "1440" in n or "1920" in n or "desktop" in n,
            p.stat().st_mtime,
        )

    candidates: list[Path] = []
    shots = lane_dir / _SHOTS_DIR
    if shots.is_dir():
        candidates += [p for p in shots.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTS]
    candidates += [p for p in lane_dir.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTS]
    return max(candidates, key=score) if candidates else None


IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".avif", ".gif", ".svg"}


def _prune_unshown_images(
    run_dir: Path, kept: list[tuple[Path, int, str]], dropped: list[tuple[Path, int, str]]
) -> list[tuple[Path, int, str]]:
    """Drop images that no tracked page loads and no lane uses as its thumbnail.

    A lane directory accumulates captures: the page at several viewport widths,
    contact sheets, before/after pairs, re-shoots. The Studio shows ONE of them,
    and the pages themselves load their media from an `assets/` dir. Everything
    else is inert — and on image-heavy runs it is most of the weight.

    Kept, in order of precedence: anything under an `assets/` dir (that is what
    the pages reference), anything whose filename appears in a tracked HTML or
    CSS file, and each lane's single thumbnail. Anything else goes, and the
    clean-clone check catches a mistake here as a broken image on a real page.
    """
    text = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path, _, _ in kept
        if path.suffix.lower() in {".html", ".htm", ".css"}
    )
    lanes = {p.parent for p in run_dir.rglob("index.html") if p.is_file()}
    thumbs: set[Path] = set()
    for lane in lanes:
        pick = _thumb_pick(lane)
        if pick:
            thumbs.add(pick)
        gallery = lane / _SHOTS_DIR / _GALLERY_THUMB
        if gallery.is_file():
            thumbs.add(gallery)

    survivors: list[tuple[Path, int, str]] = []
    for path, size, why in kept:
        if path.suffix.lower() not in IMAGE_EXTS:
            survivors.append((path, size, why))
        elif "assets" in path.parts or path.name in text or quote(path.name) in text:
            survivors.append((path, size, why))
        elif path in thumbs:
            survivors.append((path, size, "the lane's thumbnail"))
        else:
            dropped.append((path, size, "image no tracked page loads and no lane shows"))
    return survivors


def _redundant_bytes(kept: list[tuple[Path, int, str]]) -> int:
    """Bytes in the kept set that are a second copy of media kept elsewhere.

    A run carries the same image once per lane that shows it, because each lane's
    page references `assets/<name>` relative to itself. Those copies are NOT
    droppable — dropping one silently breaks that lane's images — so this is
    reported rather than acted on, and it is what a media-aware store (git-lfs,
    or a lane-relative rewrite like tools/publish_run_bundle.py does) would win.
    """
    seen: set[str] = set()
    redundant = 0
    for path, size, _ in sorted(kept, key=lambda t: t[0].as_posix()):
        if not size:
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest in seen:
            redundant += size
        else:
            seen.add(digest)
    return redundant


def resolve_capture(project: str) -> Path | None:
    """The REAL screenshots/ folder for a project, resolving a symlinked alias.

    A project whose capture is an alias of another project's (`screenshots/<a>` →
    `screenshots/<b>`) has to be tracked as the link plus the files it points at:
    git stores the symlink but will not add paths that traverse one. Returns None
    when the capture lives outside the repo, since that cannot be tracked at all.
    """
    cap = SCREENSHOTS_DIR / project
    if not cap.is_dir():
        return None
    real = cap.resolve()
    if REPO_ROOT not in real.parents:
        return None
    return real


def classify_capture(project: str) -> dict:
    """Split a project's source capture into the images the Studio resolves and the rest.

    `resolve_source_image()` walks per-page `<page>/<page>-fullpage.<ext>` first,
    then root-level `*fullpage*` and root-level images. Everything else in a
    capture folder is the saved page and its `_files` mirror, which the Studio
    never opens and which is the overwhelming majority of the bytes.
    """
    cap = resolve_capture(project)
    if cap is None:
        return {"kept": [], "dropped": [], "link": None}

    kept: list[tuple[Path, int, str]] = []
    dropped: list[tuple[Path, int, str]] = []
    for path in sorted(cap.rglob("*")):
        if path.is_dir() or path.is_symlink():
            continue
        rel = path.relative_to(cap).as_posix()
        size = path.stat().st_size
        parts = rel.split("/")
        is_image = path.suffix.lower() in SOURCE_IMAGE_EXTS
        page_fullpage = (
            len(parts) == 2 and is_image and parts[1].startswith(f"{parts[0]}-fullpage")
        )
        root_image = len(parts) == 1 and is_image
        if page_fullpage:
            kept.append((path, size, "per-page full-page capture — the Source pane"))
        elif root_image:
            kept.append((path, size, "root capture image — Source pane fallback"))
        elif any(p.endswith("_files") for p in parts):
            dropped.append((path, size, "'Save Page As' mirror of the original site"))
        else:
            dropped.append((path, size, "not read by the Studio"))

    link = SCREENSHOTS_DIR / project
    return {
        "kept": kept,
        "dropped": dropped,
        "link": link if link.is_symlink() else None,
    }


def studio_config_paths(project: str) -> list[Path]:
    """Per-project Studio config the server merges over config-anthropic.yaml.

    Deliberately narrow: `runs/.studio/` also holds job logs and a registry of
    localhost build ports, neither of which mean anything in someone else's clone.
    """
    cfg = RUNS_DIR / ".studio" / f"{project}.config.yaml"
    return [cfg] if cfg.is_file() else []


def plan(project: str, *, with_screenshots: bool = True, allow_local_paths: bool = False) -> dict:
    run_dir = RUNS_DIR / project
    if not run_dir.is_dir():
        raise SystemExit(f"no such run: {run_dir}")
    run = classify_run(run_dir, allow_local_paths=allow_local_paths)
    cap = (
        classify_capture(project)
        if with_screenshots
        else {"kept": [], "dropped": [], "link": None}
    )
    cfg = studio_config_paths(project)
    return {
        "project": project,
        "run_dir": run_dir,
        "run": run,
        "capture": cap,
        "config": cfg,
        "run_total": _dir_size(run_dir),
        "capture_total": _dir_size(resolve_capture(project)) if resolve_capture(project) else 0,
        "run_kept_bytes": sum(s for _, s, _ in run["kept"]),
        "capture_kept_bytes": sum(s for _, s, _ in cap["kept"]),
        "config_bytes": sum(p.stat().st_size for p in cfg),
    }


def tracked_paths(p: dict) -> list[Path]:
    paths = [f for f, _, _ in p["run"]["kept"]]
    paths += [f for f, _, _ in p["capture"]["kept"]]
    paths += p["config"]
    if p["capture"]["link"] is not None:
        paths.append(p["capture"]["link"])
    return sorted(set(paths), key=lambda x: x.as_posix())


# ── .gitignore negations ──────────────────────────────────────────────────────
def gitignore_block(plans: list[dict]) -> list[str]:
    """The exact negation lines needed to un-ignore the planned paths.

    Git will not descend into an ignored directory, so a deep `!a/b/c` is dead on
    arrival unless every directory above it is re-included first. The block is
    therefore built in three passes:

      1. for every ancestor directory, `!<dir>/` to open it, immediately followed
         by `<dir>/*` to re-ignore everything inside it that we do not name;
      2. `!<file>` for each tracked file (and for a tracked symlink);
      3. nothing else — step 1's `<dir>/*` keeps every sibling ignored, so no
         re-exclusion pass is needed and nothing leaks in by accident.

    The `runs/` and `screenshots/` rules above this block stay exactly as they
    are; `!runs/` re-includes only the directory entry so git can look inside it,
    and the `runs/*` line immediately after restores the same coverage.
    """
    files: set[str] = set()
    for p in plans:
        for path in tracked_paths(p):
            files.add(path.relative_to(REPO_ROOT).as_posix())

    ancestors: set[str] = set()
    for rel in files:
        parts = rel.split("/")[:-1]
        for i in range(1, len(parts) + 1):
            ancestors.add("/".join(parts[:i]))

    lines: list[str] = []
    for anc in sorted(ancestors, key=lambda a: (a.count("/"), a)):
        lines.append(f"!{anc}/")
        lines.append(f"{anc}/*")
    lines += [f"!{rel}" for rel in sorted(files)]
    return lines


def write_gitignore(plans: list[dict]) -> bool:
    """Replace the managed block in .gitignore. Returns True when it changed."""
    body = "\n".join(
        [
            BEGIN_MARKER,
            "# Targeted exceptions to the runs/ and screenshots/ rules above, so a clean",
            "# clone has real Studio projects to open. Regenerate, never hand-edit:",
            "#   ./venv/bin/python tools/track_studio_subset.py --run runs/<project> --write-gitignore",
            *gitignore_block(plans),
            END_MARKER,
        ]
    )
    current = GITIGNORE.read_text()
    if BEGIN_MARKER in current and END_MARKER in current:
        head, rest = current.split(BEGIN_MARKER, 1)
        _, tail = rest.split(END_MARKER, 1)
        updated = head + body + tail
    else:
        updated = current.rstrip("\n") + "\n\n" + body + "\n"
    if updated == current:
        return False
    GITIGNORE.write_text(updated)
    return True


def dirty_paths() -> set[str]:
    """Tracked paths with uncommitted worktree edits."""
    out = subprocess.run(
        ["git", "diff", "--name-only", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True
    )
    return {line for line in out.stdout.split("\n") if line}


def stage(plans: list[dict]) -> tuple[int, list[str]]:
    """git add every planned path, one explicit path at a time.

    Paths that are already tracked AND have uncommitted edits are skipped: this
    tool's job is to bring files under tracking, not to decide that someone's
    half-finished edit is ready to commit. Returns (staged, skipped).
    """
    rels = sorted({p.relative_to(REPO_ROOT).as_posix() for pl in plans for p in tracked_paths(pl)})
    dirty = dirty_paths()
    skipped = [r for r in rels if r in dirty]
    rels = [r for r in rels if r not in dirty]
    for i in range(0, len(rels), 200):
        subprocess.run(["git", "add", "--", *rels[i : i + 200]], cwd=REPO_ROOT, check=True)
    return len(rels), skipped


_VERSION_TOKEN = re.compile(r"^v\d+$")


def _pretty_title(project: str, brand: str) -> str:
    """Human label for a run: the manifest's brand name plus the version token.

    `hubspot-v3` → "HubSpot v3" when the manifest names the brand, "Hubspot v3"
    when it does not. The version token stays lowercase so a project reads as a
    version of a brand rather than as a different brand.
    """
    tokens = project.split("-")
    words = [t if _VERSION_TOKEN.match(t) else t.capitalize() for t in tokens]
    if brand and tokens and tokens[0].lower() == brand.split()[0].lower():
        words[0] = brand.split()[0]
    return " ".join(words)


def ensure_registered(project: str) -> Path | None:
    """Write a minimal `studio-project.json` when a run has none.

    Without it the Studio still lists the run, but with no title and no link back
    to the site it came from. Title and url are derived from the run's own
    manifest, never invented; a run with no discoverable source url still gets a
    title. Idempotent: an existing file is left exactly as it is.
    """
    meta_path = RUNS_DIR / project / "studio-project.json"
    if meta_path.exists():
        return None
    manifest: dict = {}
    for candidate in (RUNS_DIR / project / "manifest.json", RUNS_DIR / project / "brand" / "manifest.json"):
        if candidate.is_file():
            try:
                manifest = json.loads(candidate.read_text()) or {}
            except ValueError:
                manifest = {}
            if manifest.get("source_url"):
                break
    title = _pretty_title(project, str(manifest.get("brand") or "").strip())
    url = str(manifest.get("source_url") or "").strip() or _brand_source_url(project)
    meta_path.write_text(
        json.dumps({"url": url, "title": title, "brand": project}, indent=2) + "\n"
    )
    return meta_path


def _brand_source_url(project: str) -> str:
    """`sourceUrl` from a run's brand.yaml — the fallback when no manifest has one."""
    path = RUNS_DIR / project / "brand" / "brand.yaml"
    if not path.is_file():
        return ""
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines()[:200]:
        match = re.match(r"^\s*sourceUrl:\s*(\S+)\s*$", line)
        if match:
            return match.group(1).strip("'\"")
    return ""


# ── completeness check ────────────────────────────────────────────────────────
# Local references a browser will actually fetch. Deliberately not a parser: the
# point is to be over-inclusive about what might 404, not to model HTML.
_REF_RE = re.compile(
    r"""(?:src|href|poster|data-src)\s*=\s*["']([^"']+)["']|url\(\s*["']?([^"')]+)["']?\s*\)""",
    re.IGNORECASE,
)
_EXTERNAL = ("http://", "https://", "//", "data:", "#", "mailto:", "tel:", "javascript:", "blob:")


def _page_references(plans: list[dict]):
    """Yield (page, reference, resolved path, repo-relative target) per local ref."""
    for pl in plans:
        for path, _, _ in pl["run"]["kept"]:
            if path.suffix.lower() not in {".html", ".htm", ".css"}:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for raw in sorted({m[0] or m[1] for m in _REF_RE.findall(text)}):
                ref = unquote(raw.split("?")[0].split("#")[0]).strip()
                if not ref or ref.startswith(_EXTERNAL):
                    continue
                # Composed pages carry the source site's own navigation (`/de-de`,
                # `/blog/…`). Those are links to pages that never existed in this
                # repo and 404 identically for the author; only extensioned refs
                # are files this subset is responsible for shipping.
                if "." not in ref.rsplit("/", 1)[-1]:
                    continue
                base = REPO_ROOT if ref.startswith("/") else path.parent
                target = (base / ref.lstrip("/")).resolve()
                try:
                    rel = target.relative_to(REPO_ROOT).as_posix()
                except ValueError:
                    continue
                yield path, ref, target, rel


def _available(plans: list[dict]) -> set[str]:
    planned = {p.relative_to(REPO_ROOT).as_posix() for pl in plans for p in tracked_paths(pl)}
    already = set(
        subprocess.run(
            ["git", "ls-files"], cwd=REPO_ROOT, capture_output=True, text=True
        ).stdout.split("\n")
    )
    return planned | already


def rescue_references(plans: list[dict]) -> list[Path]:
    """Pull in files a tracked page loads that the include rules would have skipped.

    Lanes borrow across runs — a composed page can point at another project's
    harvested asset pool — and no static include list predicts that. Rather than
    widen the rules until they cover every case (and drag in the pools nobody
    reads), the references win: whatever a page we ship actually loads gets
    shipped with it, attributed to the plan for the run it lives in.
    """
    added: list[Path] = []
    by_run = {pl["run_dir"]: pl for pl in plans}
    for _ in range(4):  # rescued CSS can itself reference more files
        available = _available(plans)
        round_added = []
        for _page, _ref, target, rel in _page_references(plans):
            if rel in available or not target.is_file():
                continue
            owner = next((d for d in by_run if d in target.parents), None)
            if owner is None:
                continue
            size = target.stat().st_size
            by_run[owner]["run"]["kept"].append((target, size, "loaded by a tracked page"))
            by_run[owner]["run_kept_bytes"] += size
            available.add(rel)
            round_added.append(target)
        added += round_added
        if not round_added:
            break
    return added


def check_references(plans: list[dict]) -> list[tuple[str, str]]:
    """Every local file a tracked page loads must itself be tracked.

    This is the check that separates "the project is in the repo" from "the
    project works in the repo". It resolves each reference the way the Studio
    serves it — root-relative against the repo, otherwise against the page — and
    reports the ones that would 404 in a clone. Returns [(page, reference)].
    """
    available = _available(plans)
    return [
        (page.relative_to(REPO_ROOT).as_posix(), ref)
        for page, ref, target, rel in _page_references(plans)
        if rel not in available and not target.is_dir()
    ]


# ── reporting ─────────────────────────────────────────────────────────────────
def report(p: dict, *, show_files: bool) -> None:
    run, cap = p["run"], p["capture"]
    kept_b, cap_b, cfg_b = p["run_kept_bytes"], p["capture_kept_bytes"], p["config_bytes"]
    print(f"\n=== {p['project']} ===")
    print(f"  run on disk          {fmt_bytes(p['run_total']):>10}")
    print(f"  run subset to track  {fmt_bytes(kept_b + cfg_b):>10}   ({len(run['kept']) + len(p['config'])} files)")
    print(f"  + source capture     {fmt_bytes(cap_b):>10}   ({len(cap['kept'])} files, of {fmt_bytes(p['capture_total'])} on disk)")
    print(f"  TOTAL                {fmt_bytes(kept_b + cfg_b + cap_b):>10}")

    by_reason: dict[str, list[int]] = {}
    for _, size, why in run["dropped"] + cap["dropped"]:
        by_reason.setdefault(why, []).append(size)
    print("  excluded:")
    for why, sizes in sorted(by_reason.items(), key=lambda kv: -sum(kv[1]))[:10]:
        print(f"    {fmt_bytes(sum(sizes)):>10}  {len(sizes):>5} files  {why}")
    if run["redundant"]:
        print(f"  of the subset, {fmt_bytes(run['redundant'])} is media duplicated across lanes")

    leaked = [p for p, _, why in run["dropped"] if "absolute path" in why]
    if leaked:
        print("  held back for embedding this checkout's absolute path:")
        for path in leaked:
            print(f"    {path.relative_to(REPO_ROOT).as_posix()}")

    if show_files:
        print("  tracking:")
        for path in tracked_paths(p):
            rel = path.relative_to(REPO_ROOT).as_posix()
            marker = " (symlink)" if path.is_symlink() else ""
            print(f"    {rel}{marker}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", action="append", default=[], help="run directory, e.g. runs/<project> (repeatable)")
    ap.add_argument("--all", action="store_true", help="every project that has a studio-project.json")
    ap.add_argument("--no-screenshots", action="store_true", help="measure/track without the source capture")
    ap.add_argument(
        "--allow-local-paths",
        action="store_true",
        help="track text artifacts even when they embed this checkout's absolute path",
    )
    ap.add_argument("--files", action="store_true", help="list every file that would be tracked")
    ap.add_argument("--write-gitignore", action="store_true", help="rewrite the managed .gitignore block")
    ap.add_argument("--stage", action="store_true", help="git add the planned paths")
    ap.add_argument(
        "--register",
        action="store_true",
        help="write a minimal studio-project.json for any run that has none",
    )
    ap.add_argument("--json", action="store_true", help="emit the plan as JSON instead of a table")
    ap.add_argument(
        "--check",
        action="store_true",
        help="report local references from tracked pages that would 404 in a clone",
    )
    args = ap.parse_args()

    projects = [Path(r).name for r in args.run]
    if args.all:
        projects += sorted(
            d.name for d in RUNS_DIR.iterdir() if (d / "studio-project.json").is_file()
        )
    projects = sorted(set(projects))
    if not projects:
        ap.error("pass --run runs/<project> or --all")

    if args.register:
        for v in projects:
            written = ensure_registered(v)
            if written:
                print(f"registered {written.relative_to(REPO_ROOT).as_posix()}")

    plans = [
        plan(
            v,
            with_screenshots=not args.no_screenshots,
            allow_local_paths=args.allow_local_paths,
        )
        for v in projects
    ]
    rescued = rescue_references(plans)
    if rescued:
        print(f"pulled in {len(rescued)} file(s) referenced by a tracked page but not matched by the rules")

    if args.json:
        print(
            json.dumps(
                [
                    {
                        "project": p["project"],
                        "run_total": p["run_total"],
                        "subset": p["run_kept_bytes"] + p["config_bytes"],
                        "capture": p["capture_kept_bytes"],
                        "files": [x.relative_to(REPO_ROOT).as_posix() for x in tracked_paths(p)],
                    }
                    for p in plans
                ],
                indent=2,
            )
        )
        return

    for p in plans:
        report(p, show_files=args.files)

    total = sum(p["run_kept_bytes"] + p["config_bytes"] + p["capture_kept_bytes"] for p in plans)
    print(f"\nCOMBINED TOTAL TO TRACK: {fmt_bytes(total)} across {len(plans)} project(s)")

    if args.check:
        broken = check_references(plans)
        if not broken:
            print("reference check: every local reference from a tracked page resolves")
        else:
            by_page: dict[str, list[str]] = {}
            for page, ref in broken:
                by_page.setdefault(page, []).append(ref)
            print(f"reference check: {len(broken)} references would 404, across {len(by_page)} pages")
            for page, refs in sorted(by_page.items(), key=lambda kv: -len(kv[1]))[:15]:
                print(f"  {page}  ({len(refs)})")
                for ref in sorted(refs)[:4]:
                    print(f"      {ref}")

    if args.write_gitignore:
        changed = write_gitignore(plans)
        print(f".gitignore: {'updated' if changed else 'already current'}")
    if args.stage:
        staged, skipped = stage(plans)
        print(f"staged {staged} paths")
        if skipped:
            print(f"skipped {len(skipped)} tracked paths with uncommitted edits (not ours to commit):")
            for rel in skipped[:20]:
                print(f"  {rel}")


if __name__ == "__main__":
    sys.exit(main())
