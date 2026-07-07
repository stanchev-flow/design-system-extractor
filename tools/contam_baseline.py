#!/usr/bin/env python3
"""Cross-brand contamination fix (AS-38) — regression lane renderer.

Renders every regression lane into <out_root>/<lane>/ so the SAME script can
snapshot the pre-fix baseline and the post-fix state for byte-diffing:

    ./venv/bin/python tools/contam_baseline.py /tmp/contam-fix/base    # before
    ./venv/bin/python tools/contam_baseline.py /tmp/contam-fix/after   # after
    diff -r /tmp/contam-fix/base /tmp/contam-fix/after

Lanes: WoodWave composed pages (plain / editorial-luxury / radical-editorial /
wildcard), the WoodWave hero single-section render, three composition replays
from persisted composition.json (WoodWave hybrid showcase, hubspot, remote — no
LLM involved), and the three components-preview galleries.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PY = str(REPO / "venv" / "bin" / "python")
BP = REPO / "brand_pipeline"

WW_BRAND = REPO / "runs" / "woodwave" / "brand" / "brand.yaml"
HY_BRAND = REPO / "experiments" / "woodwave-ab" / "inputs" / "brand" / "brand.yaml"
HS_BRAND = REPO / "runs" / "hubspot" / "brand" / "brand.yaml"
RM_BRAND = REPO / "runs" / "remote" / "brand" / "brand.yaml"

SHOWCASE_COMP = REPO / "experiments" / "woodwave-hybrid" / "showcase" / "composition.json"
HS_COMP = REPO / "runs" / "hubspot" / "brand" / "compose" / "signup-launch-fixed-live" / "composition.json"
RM_COMP = REPO / "runs" / "remote" / "brand" / "compose" / "signup-launch-fixed" / "composition.json"


def run(cmd: list[str], label: str) -> bool:
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO)
    ok = r.returncode == 0
    print(f"  [{label}] {'OK' if ok else 'FAIL rc=' + str(r.returncode)}")
    if not ok:
        print((r.stderr or r.stdout)[-1200:])
    return ok


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    out = Path(sys.argv[1]).resolve()
    out.mkdir(parents=True, exist_ok=True)
    ok = True

    # WoodWave composed pages (compose_page CLI, default order)
    ok &= run([PY, str(BP / "compose_page.py"), str(WW_BRAND),
               "-o", str(out / "ww-page-plain")], "ww-page-plain")
    ok &= run([PY, str(BP / "compose_page.py"), str(WW_BRAND),
               "-o", str(out / "ww-page-lux"), "--style", "editorial-luxury"],
              "ww-page-lux")
    ok &= run([PY, str(BP / "compose_page.py"), str(WW_BRAND),
               "-o", str(out / "ww-page-rad"), "--style", "radical-editorial"],
              "ww-page-rad")
    ok &= run([PY, str(BP / "compose_page.py"), str(WW_BRAND),
               "-o", str(out / "ww-page-wild"), "--style", "radical-editorial",
               "--wildcard", "mission-statement=2,curator-quote=2"], "ww-page-wild")

    # WoodWave hero single-section render (compose_section / build_document path)
    ok &= run([PY, str(BP / "compose_section.py"), str(WW_BRAND), "opening-bookend",
               "-o", str(out / "ww-hero-section"), "--style", "editorial-luxury"],
              "ww-hero-section")

    # Composition replays from persisted composition.json (deterministic; no LLM)
    replay = (
        "import json, sys; sys.path.insert(0, {bp!r});"
        "import compose_from_composition as cfc;"
        "comp = json.load(open({comp!r}));"
        "cfc.render_composition(comp, {brand!r}, {out!r}, style_id={style!r})"
    )
    for label, comp, brand, style in (
            ("ww-showcase-replay", SHOWCASE_COMP, HY_BRAND, "editorial-luxury"),
            ("hs-replay", HS_COMP, HS_BRAND, "corporate-saas-clean"),
            ("rm-replay", RM_COMP, RM_BRAND, "corporate-saas-clean")):
        code = replay.format(bp=str(BP), comp=str(comp), brand=str(brand),
                             out=str(out / label), style=style)
        ok &= run([PY, "-c", code], label)

    # Components-preview galleries
    for label, brand in (("ww-preview", WW_BRAND), ("hs-preview", HS_BRAND),
                         ("rm-preview", RM_BRAND)):
        ok &= run([PY, str(BP / "render_components_preview.py"), str(brand),
                   "-o", str(out / label)], label)

    print(f"\nsnapshot -> {out}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
