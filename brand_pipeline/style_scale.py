"""Derived-scale consumption (pass1 2026-07; artifact: style-scale.v1).

Loader + step lookup for the quantized scale a brand's raw evidence was
normalized into (`tools/extract/normalize_scales.py` → `<brand>/style-scale.yaml`).

LANE LAW (the byte-identity contract):
- GENERATIVE composers (archetype instantiation, wildcard, composed lanes) may
  prefer a derived step for NEW geometry **only where no measured fact binds** —
  a measured fact always wins by ordering (the derived step is consulted last,
  behind every brand rung/fact resolution).
- The REPLICA lane never loads this artifact: `compose_replica` has no
  ``_styleScale`` and no code path that reads the file, so replica output is
  byte-identical whether or not the artifact exists (test-pinned).
- A scale with ``followsScale: false`` (poor fit) is NOT consumed — the brand
  genuinely doesn't follow a scale and inventing steps from a bad fit would be
  the arbitrary-number failure this layer exists to remove.
"""
from __future__ import annotations

from pathlib import Path

import yaml


def load_style_scale(brand_dir: Path | str | None) -> dict | None:
    """Parsed style-scale.yaml for a brand run dir, or None (absent/invalid)."""
    if not brand_dir:
        return None
    path = Path(brand_dir) / "style-scale.yaml"
    if not path.exists():
        return None
    try:
        art = yaml.safe_load(path.read_text())
    except Exception:
        return None
    if not isinstance(art, dict) or art.get("schema") != "style-scale.v1":
        return None
    return art


def _usable(block: dict | None) -> bool:
    return bool(isinstance(block, dict) and block.get("followsScale")
                and block.get("stepsPx"))


def space_steps_px(scale: dict | None) -> list[float]:
    """Derived space steps (px), [] when absent or the fit is poor."""
    block = (scale or {}).get("space")
    if not _usable(block):
        return []
    return [float(v) for v in block["stepsPx"]]


def type_steps_px(scale: dict | None) -> list[float]:
    """Derived type steps (px), [] when absent or the fit is poor."""
    block = (scale or {}).get("type")
    if not _usable(block):
        return []
    return [float(v) for v in block["stepsPx"]]


def section_rhythm_px(scale: dict | None) -> list[float]:
    block = (scale or {}).get("space")
    if not _usable(block):
        return []
    return [float(v) for v in block.get("sectionRhythmPx") or []]


def nearest_step_px(steps: list[float], px: float,
                    direction: int = 0) -> float | None:
    """Nearest derived step to ``px``; with ``direction`` ±1, nearest step
    STRICTLY beyond ``px`` in that direction (None when none exists)."""
    if not steps:
        return None
    if direction:
        picks = [s for s in steps if (s - px) * direction > 0]
        return min(picks, key=lambda s: abs(s - px)) if picks else None
    return min(steps, key=lambda s: abs(s - px))
