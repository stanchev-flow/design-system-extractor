#!/usr/bin/env python3
"""Archive a section-separator experiment into a numbered permanent run folder."""

import argparse
import os
import re
import shutil
import time
from datetime import date
from pathlib import Path


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "experiment"


def next_version(root: Path) -> int:
    existing = []
    for entry in root.iterdir() if root.exists() else []:
        match = re.match(r"v(\d{3})-", entry.name)
        if entry.is_dir() and match:
            existing.append(int(match.group(1)))
    return (max(existing) + 1) if existing else 1


def acquire_lock(root: Path) -> Path:
    lock_path = root / ".archive.lock"
    while True:
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            return lock_path
        except FileExistsError:
            time.sleep(0.05)


def release_lock(lock_path: Path) -> None:
    if lock_path.exists():
        lock_path.unlink()


def copy_path(source: Path, destination: Path) -> None:
    if source.is_dir():
        shutil.copytree(source, destination)
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", help="Source directory to archive")
    parser.add_argument("title", help="Human-readable experiment title")
    parser.add_argument("summary", help="Short summary of what changed and what we learned")
    parser.add_argument(
        "--root",
        default="runs/section-separator",
        help="Archive root directory (default: runs/section-separator)",
    )
    parser.add_argument(
        "--slug",
        default=None,
        help="Optional slug override for the version directory name",
    )
    parser.add_argument(
        "--extra",
        action="append",
        default=[],
        help="Extra file or directory to copy into the archive under extras/<name>",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source = Path(args.source)
    if not source.exists():
        raise SystemExit(f"Source not found: {source}")

    root = Path(args.root)
    root.mkdir(parents=True, exist_ok=True)
    lock_path = acquire_lock(root)
    try:
        version = next_version(root)
        slug = args.slug or slugify(args.title)
        version_dir = root / f"v{version:03d}-{slug}"
        version_dir.mkdir()
        (version_dir / "temp").mkdir()

        copy_path(source, version_dir / "artifacts")

        if args.extra:
            extras_dir = version_dir / "extras"
            extras_dir.mkdir()
            for extra in args.extra:
                extra_path = Path(extra)
                if not extra_path.exists():
                    raise SystemExit(f"Extra path not found: {extra_path}")
                copy_path(extra_path, extras_dir / extra_path.name)

        notes = "\n".join(
            [
                f"# {args.title}",
                "",
                f"- Archived: {date.today().isoformat()}",
                f"- Source: `{source}`",
                "",
                "## Summary",
                args.summary,
                "",
            ]
        )
        (version_dir / "notes.md").write_text(notes)
        print(version_dir)
    finally:
        release_lock(lock_path)


if __name__ == "__main__":
    main()
