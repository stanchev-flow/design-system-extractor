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
Both are idempotent: re-running after a project regenerates its artifacts adds
what appeared and drops what vanished.

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

    kept.sort(key=lambda t: -t[1])
    dropped.sort(key=lambda t: -t[1])
    return {"kept": kept, "dropped": dropped, "redundant": _redundant_bytes(kept)}


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


def stage(plans: list[dict]) -> int:
    """git add every planned path, one explicit path at a time."""
    rels = sorted({p.relative_to(REPO_ROOT).as_posix() for pl in plans for p in tracked_paths(pl)})
    for i in range(0, len(rels), 200):
        subprocess.run(["git", "add", "--", *rels[i : i + 200]], cwd=REPO_ROOT, check=True)
    return len(rels)


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
    ap.add_argument("--json", action="store_true", help="emit the plan as JSON instead of a table")
    args = ap.parse_args()

    projects = [Path(r).name for r in args.run]
    if args.all:
        projects += sorted(
            d.name for d in RUNS_DIR.iterdir() if (d / "studio-project.json").is_file()
        )
    projects = sorted(set(projects))
    if not projects:
        ap.error("pass --run runs/<project> or --all")

    plans = [
        plan(
            v,
            with_screenshots=not args.no_screenshots,
            allow_local_paths=args.allow_local_paths,
        )
        for v in projects
    ]

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

    if args.write_gitignore:
        changed = write_gitignore(plans)
        print(f".gitignore: {'updated' if changed else 'already current'}")
    if args.stage:
        print(f"staged {stage(plans)} paths")


if __name__ == "__main__":
    sys.exit(main())
