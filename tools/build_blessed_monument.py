#!/usr/bin/env python3
"""Rebuild the BLESSED centered-monument test page (magic-trick.md ->
runs/woodwave/brand/compose/full-wildcard-centered-monument/) through the real pipeline.

AS-18/AS-19: the blessed inversion is now a DECLARED section-explicit alignment on the
mission-statement layout (in-memory mutation only — brand.yaml untouched), so the
composer's resolution chain supplies the centered anchor + SYMMETRIC statement spans and
stamps data-align-source="section". The injected CSS is only the monument's rhythm and
measure (mirrors wildcard_generator's centered-monument candidate), no longer a grid
collapse fighting the scaffold."""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "brand_pipeline"))

import compose_page as cp        # noqa: E402
import compose_section as cs     # noqa: E402
from styles import load_and_merge  # noqa: E402
from wildcard_generator import _candidates  # noqa: E402

BRAND_YAML = REPO / "runs" / "woodwave" / "brand" / "brand.yaml"
OUT = REPO / "runs" / "woodwave" / "brand" / "compose" / "full-wildcard-centered-monument"
ORDER = ["opening-bookend", "editorial-collage", "mission-statement", "gallery-showcase",
         "heritage-timeline", "curator-quote", "visit-band", "conversion-stack"]
STYLE = "radical-editorial"


def main() -> int:
    doc = cs.load_doc(BRAND_YAML)
    cand = next(c for c in _candidates(doc) if c["id"] == "centered-monument")
    lay = cs.find_layout(doc, cand["base_layout"])
    mutated = cand["mutate"](lay) if cand.get("mutate") else lay
    doc["layouts"] = [mutated if l.get("id") == cand["base_layout"] else l
                      for l in doc.get("layouts", [])]
    style_ctx = load_and_merge(STYLE, doc)
    OUT.mkdir(parents=True, exist_ok=True)
    cs.prepare_nav_logo(doc, BRAND_YAML.parent, OUT / "assets")
    html = cp.build_page(doc, BRAND_YAML, ORDER, style_ctx)
    block = ("\n/* ===== BLESSED MAGIC TRICK (magic-trick.md, 2026-07-02): "
             "centered-monument ===== */" + cand["css"])
    html = html.replace("</style>", block + "\n</style>", 1)
    (OUT / "index.html").write_text(html)
    cs.copy_assets(BRAND_YAML.parent, OUT / "assets")
    cs.copy_fonts(BRAND_YAML.parent, OUT / "assets", doc)
    print(f"blessed monument page -> {OUT / 'index.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
