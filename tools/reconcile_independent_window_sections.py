#!/usr/bin/env python3
"""Reconcile independently detected overlapping window sections into kept/removed crops."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from PIL import Image

from screenshot_to_template.output import generate_section_map
from screenshot_to_template.run_versions import allocate_section_separator_version


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "section"


def canonical_label(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_version", help="Path to v034-style independent-window experiment folder")
    parser.add_argument(
        "--title",
        default="90156 reconciled independent-window sections",
        help="Title for the allocated vNNN output folder",
    )
    parser.add_argument(
        "--slug",
        default="90156-reconciled-independent-window-sections",
        help="Slug for the allocated vNNN output folder",
    )
    return parser.parse_args()


def window_source_bounds(name: str) -> tuple[int, int]:
    match = re.match(r"window-(\d+)-(\d+)-(\d+)\.png$", name)
    if not match:
        raise ValueError(f"Unexpected window source filename: {name}")
    return int(match.group(2)), int(match.group(3))


def main() -> None:
    args = parse_args()
    input_version = Path(args.input_version)
    window_sources = input_version / "artifacts" / "window-sources" / "windows.json"
    meta = json.loads(window_sources.read_text())
    screenshot_path = Path(meta["screenshot"])
    windows = meta["windows"]
    overlap_start = max(window["y_start"] for window in windows)
    overlap_end = min(window["y_end"] for window in windows)

    output_version = allocate_section_separator_version(
        title=args.title,
        slug=args.slug,
        summary=(
            "Reconciled independently detected window sections into original-page crops. "
            "Removed overlap-truncated sections and exact-name duplicate overlap sections."
        ),
        screenshot=str(screenshot_path),
    )
    artifacts = output_version / "artifacts"
    kept_dir = artifacts / "kept-crops"
    removed_dir = artifacts / "removed-crops"
    kept_dir.mkdir(exist_ok=True)
    removed_dir.mkdir(exist_ok=True)

    candidates: list[dict] = []
    for summary_row in json.loads((input_version / "artifacts" / "summary.json").read_text()):
        window_source = summary_row["window_source"]
        window_start, window_end = window_source_bounds(window_source)
        for index, section in enumerate(summary_row["sections"], start=1):
            global_start = window_start + section["y_start"]
            global_end = window_start + section["y_end"]
            candidates.append(
                {
                    "source_window": window_source,
                    "source_window_start": window_start,
                    "source_window_end": window_end,
                    "label": section["label"],
                    "canonical_label": canonical_label(section["label"]),
                    "local_index": index,
                    "local_y_start": section["y_start"],
                    "local_y_end": section["y_end"],
                    "y_start": global_start,
                    "y_end": global_end,
                    "height": global_end - global_start,
                    "reasons": [],
                    "status": "candidate",
                }
            )

    # Remove sections that are obviously truncated by the overlap edge.
    for candidate in candidates:
        intersects_overlap = candidate["y_start"] < overlap_end and candidate["y_end"] > overlap_start
        if not intersects_overlap:
            continue
        if (
            candidate["local_y_end"] == candidate["source_window_end"] - candidate["source_window_start"]
            and candidate["source_window_end"] == overlap_end
        ):
            candidate["status"] = "removed"
            candidate["reasons"].append("truncated-at-bottom-window-edge-in-overlap")
        elif (
            candidate["local_y_start"] == 0
            and candidate["source_window_start"] == overlap_start
        ):
            candidate["status"] = "removed"
            candidate["reasons"].append("truncated-at-top-window-edge-in-overlap")

    # Remove exact-label duplicates inside the overlap, preferring the larger surviving section.
    kept_candidates = [c for c in candidates if c["status"] == "candidate"]
    for i, current in enumerate(kept_candidates):
        if current["status"] != "candidate":
            continue
        for other in kept_candidates[i + 1:]:
            if other["status"] != "candidate":
                continue
            if current["canonical_label"] != other["canonical_label"]:
                continue
            overlap = min(current["y_end"], other["y_end"]) - max(current["y_start"], other["y_start"])
            if overlap <= 0:
                continue
            loser, winner = (
                (current, other)
                if current["height"] < other["height"]
                else (other, current)
            )
            loser["status"] = "removed"
            loser["reasons"].append(f"duplicate-of-{winner['source_window']}:{winner['label']}")

    kept = [c for c in candidates if c["status"] == "candidate"]
    removed = [c for c in candidates if c["status"] == "removed"]

    kept.sort(key=lambda item: item["y_start"])
    removed.sort(key=lambda item: (item["source_window"], item["y_start"]))

    screenshot = Image.open(screenshot_path).convert("RGB")
    for index, section in enumerate(kept, start=1):
        crop = screenshot.crop((0, section["y_start"], screenshot.size[0], section["y_end"]))
        crop.save(kept_dir / f"{index:02d}-{slugify(section['label'])}.png")

    for index, section in enumerate(removed, start=1):
        crop = screenshot.crop((0, section["y_start"], screenshot.size[0], section["y_end"]))
        crop.save(removed_dir / f"{index:02d}-{slugify(section['label'])}.png")

    generate_section_map(
        screenshot_path=screenshot_path,
        output_path=artifacts / "kept-section-map.html",
        sections=[{"label": s["label"], "y_start": s["y_start"], "y_end": s["y_end"]} for s in kept],
    )

    (artifacts / "candidates.json").write_text(json.dumps(candidates, indent=2) + "\n")
    (artifacts / "kept-sections.json").write_text(json.dumps(kept, indent=2) + "\n")
    (artifacts / "removed-sections.json").write_text(json.dumps(removed, indent=2) + "\n")
    (artifacts / "reconciliation-summary.json").write_text(
        json.dumps(
            {
                "input_version": str(input_version),
                "screenshot": str(screenshot_path),
                "overlap_start": overlap_start,
                "overlap_end": overlap_end,
                "candidate_count": len(candidates),
                "kept_count": len(kept),
                "removed_count": len(removed),
            },
            indent=2,
        )
        + "\n"
    )

    notes = output_version / "notes.md"
    notes.write_text(
        notes.read_text()
        + "\n## Reconciliation Rule\n"
        + "- Remove sections that are truncated by a window edge inside the overlap.\n"
        + "- Remove exact same-name duplicate overlap sections by keeping the larger surviving section.\n"
        + "- Crop the remaining kept sections from the original full-page screenshot.\n"
    )
    print(output_version)


if __name__ == "__main__":
    main()
