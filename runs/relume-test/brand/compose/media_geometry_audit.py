#!/usr/bin/env python3
"""Regression gate for intrinsic split-media geometry and relational gaps."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import quote

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / "runs" / "relume-test" / "brand" / "compose"
BASE = "http://127.0.0.1:1500"
ITEMS = ("01 HubSpot", "02 Remote", "03 WoodWave")
TOLERANCE = 1.5

MEASURE_JS = """() => {
const px=v=>parseFloat(v)||0,root=getComputedStyle(document.documentElement);
const tokenPx=name=>{const v=root.getPropertyValue(name).trim(),n=parseFloat(v)||0;
 return v.endsWith('rem')?n*parseFloat(root.fontSize):n};
const sections=[...document.querySelectorAll('[data-feature-split]')];
return sections.map(section=>{
 const split=section.querySelector('.split'),stack=section.querySelector('.stack');
 const frame=section.querySelector('.feature-media'),img=frame.querySelector('img');
 const sr=split.getBoundingClientRect(),tr=stack.getBoundingClientRect();
 const fr=frame.getBoundingClientRect(),ir=img.getBoundingClientRect();
 const eyebrow=stack.querySelector('.eyebrow'),heading=stack.querySelector('h2');
 const body=stack.querySelector('.lede'),actions=stack.querySelector('.actions');
 const tail=section.dataset.featureSplit==='disclosure'?stack.querySelector('.disclosures'):body;
 const er=eyebrow.getBoundingClientRect(),hr=heading.getBoundingClientRect();
 const br=body?.getBoundingClientRect(),ar=actions?.getBoundingClientRect();
 const xr=tail?.getBoundingClientRect();
 const style=getComputedStyle(frame),splitStyle=getComputedStyle(split);
 return {
  id:section.dataset.featureSplit,aspectRatio:style.aspectRatio,minHeight:style.minHeight,
  alignSelf:style.alignSelf,frame:{w:fr.width,h:fr.height,top:fr.top},
  image:{w:ir.width,h:ir.height,naturalWidth:img.naturalWidth,naturalHeight:img.naturalHeight},
  stack:{w:tr.width,h:tr.height,top:tr.top},split:{w:sr.width,h:sr.height,top:sr.top},
  frameCenterDelta:Math.abs((fr.top+fr.height/2)-(sr.top+sr.height/2)),
  stackCenterDelta:Math.abs((tr.top+tr.height/2)-(sr.top+sr.height/2)),
  eyebrowHeadingGap:hr.top-er.bottom,
  headingTailGap:xr?xr.top-hr.bottom:null,
  headingBodyGap:br?br.top-hr.bottom:null,bodyActionsGap:br&&ar?ar.top-br.bottom:null,
  sectionPaddingTop:px(getComputedStyle(section).paddingTop),
  sectionPaddingBottom:px(getComputedStyle(section).paddingBottom),
  gridColumnGap:px(splitStyle.columnGap),gridRowGap:px(splitStyle.rowGap),
  expected:{eyebrowHeading:tokenPx(innerWidth<=720?'--eyebrow-to-heading-mobile':'--eyebrow-to-heading'),
   headingBody:tokenPx(innerWidth<=720?'--heading-to-body-mobile':'--heading-to-body'),
   bodyActions:tokenPx(innerWidth<=720?'--body-to-cta-mobile':'--body-to-cta'),
   block:tokenPx(innerWidth<=720?'--block-gap-mobile':'--block-gap'),
   section:tokenPx(innerWidth<=720?'--section-y-mobile':'--section-y'),
   splitGap:tokenPx(innerWidth<=720?'--column-gap-mobile':'--column-gap')}
 }
})}"""


def close(actual: float, expected: float) -> bool:
    return abs(actual - expected) <= TOLERANCE


def main() -> None:
    failed = False
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for item in ITEMS:
            composition = json.loads((OUT / item / "composition.json").read_text())
            geometry = {entry["slot"]: entry for entry in composition["mediaGeometry"]}
            viewport_reports = []
            failures = []
            for viewport_name, viewport in (
                ("desktop", {"width": 1440, "height": 1000}),
                ("mobile", {"width": 390, "height": 844}),
            ):
                page = browser.new_page(viewport=viewport)
                page.goto(f"{BASE}/runs/relume-test/brand/compose/{quote(item)}/index.html", wait_until="networkidle")
                measures = page.evaluate(MEASURE_JS)
                for measure in measures:
                    slot = "feature-disclosure" if measure["id"] == "disclosure" else "feature-secondary"
                    expected = geometry[slot]
                    context = {"viewport": viewport_name, "slot": slot}
                    if expected["cssAspectRatio"] == "auto" and measure["aspectRatio"] != "auto":
                        failures.append({**context, "check": "aspect-ratio-auto", "actual": measure["aspectRatio"]})
                    if measure["minHeight"] != "0px":
                        failures.append({**context, "check": "min-height-zero", "actual": measure["minHeight"]})
                    if measure["alignSelf"] != "center":
                        failures.append({**context, "check": "align-self-center", "actual": measure["alignSelf"]})
                    natural_ratio = measure["image"]["naturalWidth"] / measure["image"]["naturalHeight"]
                    frame_ratio = measure["frame"]["w"] / measure["frame"]["h"]
                    if abs(frame_ratio - natural_ratio) > 0.02:
                        failures.append({**context, "check": "intrinsic-ratio", "actual": frame_ratio, "expected": natural_ratio})
                    if not close(measure["frame"]["h"], measure["image"]["h"]):
                        failures.append({**context, "check": "frame-hugs-image", "actual": measure["frame"]["h"], "expected": measure["image"]["h"]})
                    if not close(measure["eyebrowHeadingGap"], measure["expected"]["eyebrowHeading"]):
                        failures.append({**context, "check": "eyebrow-heading-gap", "actual": measure["eyebrowHeadingGap"], "expected": measure["expected"]["eyebrowHeading"]})
                    if measure["id"] == "disclosure":
                        if not close(measure["headingTailGap"], measure["expected"]["block"]):
                            failures.append({**context, "check": "heading-disclosure-gap", "actual": measure["headingTailGap"], "expected": measure["expected"]["block"]})
                    else:
                        if not close(measure["headingBodyGap"], measure["expected"]["headingBody"]):
                            failures.append({**context, "check": "heading-body-gap", "actual": measure["headingBodyGap"], "expected": measure["expected"]["headingBody"]})
                        if not close(measure["bodyActionsGap"], measure["expected"]["bodyActions"]):
                            failures.append({**context, "check": "body-actions-gap", "actual": measure["bodyActionsGap"], "expected": measure["expected"]["bodyActions"]})
                    if not close(measure["sectionPaddingTop"], measure["expected"]["section"]) or not close(measure["sectionPaddingBottom"], measure["expected"]["section"]):
                        failures.append({**context, "check": "section-padding", "actual": [measure["sectionPaddingTop"], measure["sectionPaddingBottom"]], "expected": measure["expected"]["section"]})
                    if viewport_name == "desktop":
                        if not close(measure["split"]["h"], max(measure["frame"]["h"], measure["stack"]["h"])):
                            failures.append({**context, "check": "grid-row-max-content", "actual": measure["split"]["h"], "expected": max(measure["frame"]["h"], measure["stack"]["h"])})
                        if measure["frameCenterDelta"] > TOLERANCE or measure["stackCenterDelta"] > TOLERANCE:
                            failures.append({**context, "check": "sibling-center-alignment", "actual": [measure["frameCenterDelta"], measure["stackCenterDelta"]]})
                        if not close(measure["gridColumnGap"], measure["expected"]["splitGap"]):
                            failures.append({**context, "check": "column-gap", "actual": measure["gridColumnGap"], "expected": measure["expected"]["splitGap"]})
                    else:
                        if not close(measure["gridRowGap"], measure["expected"]["splitGap"]):
                            failures.append({**context, "check": "mobile-row-gap", "actual": measure["gridRowGap"], "expected": measure["expected"]["splitGap"]})
                viewport_reports.append({"viewport": viewport_name, "measures": measures})
                page.close()
            result = {
                "schemaVersion": "relume-test.media-geometry.v1",
                "item": item,
                "policy": composition["mediaGeometryPolicy"],
                "viewports": viewport_reports,
                "failures": failures,
                "status": "pass" if not failures else "fail",
            }
            (OUT / item / "media-geometry-report.json").write_text(json.dumps(result, indent=2) + "\n")
            (OUT / item / "media-geometry-report.md").write_text(
                f"# {item} media geometry\n\n- Status: **{result['status'].upper()}**\n"
                f"- Desktop/mobile feature splits checked: 4\n- Failures: {len(failures)}\n"
            )
            print(item, result["status"].upper(), len(failures), "failures")
            if failures:
                print(json.dumps(failures[:20], indent=2))
                failed = True
        browser.close()
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
