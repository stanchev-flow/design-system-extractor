#!/usr/bin/env python3
"""render_composition.py — CLI: render a ``composition.v1`` file to a page dir.

Thin wrapper over ``compose_from_composition`` (Phase 2 adapter). Renders a composition
via the EXISTING deterministic composer (compose_page → compose_section →
component_render), with fonts + assets injected exactly like the other composed pages.

Usage:
  python3 brand_pipeline/render_composition.py <composition.json> <brand.yaml> \
      -o <outdir> --style <id>
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from compose_from_composition import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
