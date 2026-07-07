#!/usr/bin/env python3
"""Worklist scan: run the token-provenance checker over live WoodWave pages using an
index regenerated from the brand doc (pages predate tokens.manifest.json). Dedupes
violations across pages to produce the hardcode-elimination worklist."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "brand_pipeline"))

import token_provenance  # noqa: E402
import tokens_css  # noqa: E402
import yaml  # noqa: E402

doc = yaml.safe_load((ROOT / "runs/woodwave/brand/brand.yaml").read_text())
_, _, index, _, _ = tokens_css.emit_layer1(doc)

PAGES = [
    "experiments/alignment-fix-shots",  # placeholder; real pages below
]
pages = [
    ROOT / "experiments/woodwave-showcase/pages/all-project-editorial-luxury/index.html",
    ROOT / "experiments/woodwave-showcase/pages/all-standard-editorial-luxury/index.html",
    ROOT / "experiments/woodwave-hybrid/showcase/index.html",
    ROOT / "experiments/woodwave-hybrid/run-1/index.html",
    ROOT / "experiments/woodwave-ab/arm-a-structured/index.html",
    ROOT / "experiments/woodwave-hero-gallery/page-anchored/index.html",
]

seen: dict[tuple, set] = {}
for p in pages:
    if not p.exists():
        continue
    res = token_provenance.check_token_provenance(
        p.read_text(), index, brand="WoodWave", max_items=500)
    for sev, items in (("ERR", res["errors"]), ("WARN", res["warnings"])):
        for item in items:
            seen.setdefault((sev, item), set()).add(p.parent.name)

errs = sorted(k for k in seen if k[0] == "ERR")
warns = sorted(k for k in seen if k[0] == "WARN")
print(f"unique errors: {len(errs)}   unique warnings: {len(warns)}\n")
for sev, item in errs + warns:
    srcs = ",".join(sorted(seen[(sev, item)]))[:70]
    print(f"{sev:4} {item}   [{srcs}]")
