"""Deterministic input digests for dependent brand projections."""
from __future__ import annotations

import hashlib
from pathlib import Path


RELEVANT_INPUTS = (
    "brand.yaml",
    "section-copy.yaml",
    "layout-library.yaml",
    "brand-chrome.yaml",
    "media-assets.yaml",
    "assets-tagged.json",
)


def projection_input_digest(brand_dir: Path) -> str:
    root = Path(brand_dir)
    digest = hashlib.sha256()
    for name in RELEVANT_INPUTS:
        path = root / name
        digest.update(name.encode())
        digest.update(b"\0")
        digest.update(path.read_bytes() if path.is_file() else b"<missing>")
        digest.update(b"\0")
    return digest.hexdigest()
