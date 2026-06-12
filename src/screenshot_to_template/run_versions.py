"""Helpers for allocating permanent section-separator run folders."""

from __future__ import annotations

import os
import re
import time
from datetime import date
from pathlib import Path


SECTION_SEPARATOR_ROOT = Path("runs") / "section-separator"


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "run"


def next_version(root: Path) -> int:
    existing: list[int] = []
    for entry in root.iterdir() if root.exists() else []:
        match = re.match(r"v(\d{3})-", entry.name)
        if entry.is_dir() and match:
            existing.append(int(match.group(1)))
    return (max(existing) + 1) if existing else 1


def acquire_lock(root: Path) -> Path:
    lock_path = root / ".version.lock"
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


def allocate_section_separator_version(
    title: str,
    *,
    slug: str | None = None,
    root: Path | None = None,
    summary: str | None = None,
    screenshot: str | None = None,
) -> Path:
    archive_root = root or SECTION_SEPARATOR_ROOT
    archive_root.mkdir(parents=True, exist_ok=True)
    lock_path = acquire_lock(archive_root)
    try:
        version = next_version(archive_root)
        version_dir = archive_root / f"v{version:03d}-{(slug or slugify(title))}"
        version_dir.mkdir()
        (version_dir / "artifacts").mkdir()
        (version_dir / "temp").mkdir()

        notes_lines = [
            f"# {title}",
            "",
            f"- Created: {date.today().isoformat()}",
            f"- Version: `{version_dir.name}`",
        ]
        if screenshot:
            notes_lines.append(f"- Screenshot: `{screenshot}`")
        notes_lines.extend(
            [
                "",
                "## Summary",
                summary or "Run allocated. Add notes after executing the experiment.",
                "",
            ]
        )
        (version_dir / "notes.md").write_text("\n".join(notes_lines))
        return version_dir
    finally:
        release_lock(lock_path)
