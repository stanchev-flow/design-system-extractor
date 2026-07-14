#!/usr/bin/env python3
"""Deterministic normalization harness for the Remote composition bakeoff."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw
from jsonschema import Draft202012Validator
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[5]
COMPARE = ROOT / "runs/remote/brand/compose/bakeoff-comparison"
BRAND = ROOT / "runs/remote/brand"
LANES = {
    "Candidate A": ROOT / "runs/remote/brand/compose/bakeoff-opus",
    "Candidate B": ROOT / "runs/remote/brand/compose/bakeoff-sol",
}
STYLE_ARGS = {
    "Candidate A": ["--style", "corporate-saas-clean"],
    "Candidate B": [],
}
SHARED_FILES = [
    "brand_pipeline/render_composition.py",
    "brand_pipeline/compose_from_composition.py",
    "brand_pipeline/compose_page.py",
    "brand_pipeline/compose_section.py",
    "brand_pipeline/component_render.py",
    "brand_pipeline/layout_library.py",
    "brand_pipeline/tokens_css.py",
    "brand_pipeline/styles.py",
    "brand_pipeline/spec/composition.v1.schema.json",
    "runs/remote/brand/brand.yaml",
    "runs/remote/brand/layout-library.yaml",
    "runs/remote/brand/section-copy.yaml",
    "styles/corporate-saas-clean.md",
]
SETTLE_CSS = """
*,*::before,*::after{animation:none!important;transition:none!important}
.cs-motion-ready .cs-reveal,.cs-reveal{opacity:1!important;transform:none!important}
html{scroll-behavior:auto!important}
"""

GEOMETRY_JS = r"""
() => {
  const r = e => {
    const x=e.getBoundingClientRect();
    return {left:+x.left.toFixed(2),top:+(x.top+scrollY).toFixed(2),
      right:+x.right.toFixed(2),bottom:+(x.bottom+scrollY).toFixed(2),
      width:+x.width.toFixed(2),height:+x.height.toFixed(2)};
  };
  const css=e=>getComputedStyle(e);
  const visible=e=>{const x=r(e),s=css(e);return x.width>1&&x.height>1&&s.display!=="none"&&s.visibility!=="hidden"};
  const gapX=(a,b)=>+(r(b).left-r(a).right).toFixed(2);
  const gapY=(a,b)=>+(r(b).top-r(a).bottom).toFixed(2);
  const sections=[...document.querySelectorAll('div.cs-surface[id^="sec-"]')].slice(0,10);
  const out={viewport:{width:innerWidth,height:innerHeight,deviceScaleFactor:devicePixelRatio},
    page:{width:document.documentElement.scrollWidth,height:document.documentElement.scrollHeight},
    sections:[], anomalies:[]};
  for(const wrap of sections){
    const sec=wrap.querySelector(':scope > section.cs-section')||wrap;
    const sr=r(sec), kids=[...sec.children].filter(visible);
    const all=[...sec.querySelectorAll('*')].filter(visible);
    const maxed=all.filter(e=>css(e).maxWidth!=="none"&&r(e).width>=320)
      .sort((a,b)=>r(b).width-r(a).width);
    const container=maxed[0]||kids.sort((a,b)=>r(b).width-r(a).width)[0]||sec;
    const cr=r(container);
    const headings=[...sec.querySelectorAll('h1,h2,h3,.c-heading')].filter(visible);
    const split=sec.querySelector('.cs-split,.cs-acc-split,.cs-hero-panel');
    const splitKids=split?[...split.children].filter(visible):[];
    const grids=[...sec.querySelectorAll('.cs-modules,.cs-signup-grid')].filter(visible).map(g=>{
      const items=[...g.children].filter(visible), rects=items.map(r);
      const rows=[]; rects.forEach(x=>{let row=rows.find(y=>Math.abs(y[0].top-x.top)<=4);row?row.push(x):rows.push([x])});
      const colGaps=[]; for(const row of rows){row.sort((a,b)=>a.left-b.left);for(let i=0;i+1<row.length;i++)colGaps.push(+(row[i+1].left-row[i].right).toFixed(2))}
      const rowGaps=[]; for(let i=0;i+1<rows.length;i++)rowGaps.push(+(Math.min(...rows[i+1].map(x=>x.top))-Math.max(...rows[i].map(x=>x.bottom))).toFixed(2));
      return {className:g.className,rect:r(g),itemRects:rects,columnGaps:colGaps,rowGaps,
        equalHeightSpread:rects.length?+(Math.max(...rects.map(x=>x.height))-Math.min(...rects.map(x=>x.height))).toFixed(2):0};
    });
    const cards=[...sec.querySelectorAll('.cs-module--plate')].filter(visible).map(c=>{
      const s=css(c), action=c.querySelector('.c-button,.c-arrow-link'), body=c.querySelector('.c-paragraph');
      return {rect:r(c),padding:{top:parseFloat(s.paddingTop),right:parseFloat(s.paddingRight),
        bottom:parseFloat(s.paddingBottom),left:parseFloat(s.paddingLeft)},
        ctaSeam:action&&body?gapY(body,action):null};
    });
    const media=[...sec.querySelectorAll('figure,.cs-split-media,.cs-hero-panel-media,.cs-module-media')].filter(visible).map(m=>{
      const mr=r(m),img=m.querySelector('img'),ir=img&&visible(img)?r(img):null;
      return {rect:mr,imageRect:ir,objectFit:img?css(img).objectFit:null,
        emptyWellPx:ir?+Math.max(0,mr.width*mr.height-ir.width*ir.height).toFixed(2):+(mr.width*mr.height).toFixed(2)};
    });
    const tables=[...sec.querySelectorAll('table,.c-rows')].filter(visible).map(t=>{
      const rows=[...t.querySelectorAll('tr,.c-row')].filter(visible);
      return {rect:r(t),rowWidths:rows.map(x=>r(x).width),rowHeights:rows.map(x=>r(x).height),
        columnTemplate:css(t).gridTemplateColumns};
    });
    const form=sec.querySelector('form,.c-form,.cs-signup-panel');
    const fields=form?[...form.querySelectorAll('.cs-field,input,select,textarea')].filter(visible):[];
    const fieldBoxes=fields.filter((e,i,a)=>!a.some((p,j)=>j<i&&p.contains(e))).map(r);
    const fieldGaps=[]; for(let i=0;i+1<fieldBoxes.length;i++){const a=fieldBoxes[i],b=fieldBoxes[i+1];if(Math.abs(a.top-b.top)>4)fieldGaps.push(+(b.top-a.bottom).toFixed(2))}
    const overflow=all.filter(e=>{const x=r(e);return x.left<-1||x.right>innerWidth+1}).slice(0,12).map(e=>({tag:e.tagName,className:e.className,rect:r(e)}));
    const verticalVoids=[]; const flow=[...sec.querySelectorAll(':scope *')].filter(e=>visible(e)&&css(e).position!=="absolute").sort((a,b)=>r(a).top-r(b).top);
    for(let i=0;i+1<flow.length;i++){const g=gapY(flow[i],flow[i+1]);if(g>240)verticalVoids.push(g)}
    out.sections.push({id:wrap.id,layout:wrap.dataset.layout||null,pattern:wrap.dataset.pattern||null,
      sectionRect:sr,computedPadding:{top:parseFloat(css(sec).paddingTop),bottom:parseFloat(css(sec).paddingBottom)},
      contentPadding:{top:kids.length?+(Math.min(...kids.map(x=>r(x).top))-sr.top).toFixed(2):null,
        bottom:kids.length?+(sr.bottom-Math.max(...kids.map(x=>r(x).bottom))).toFixed(2):null},
      container:{rect:cr,leftGutter:+(cr.left-sr.left).toFixed(2),rightGutter:+(sr.right-cr.right).toFixed(2),
        centeringDelta:+Math.abs((cr.left-sr.left)-(sr.right-cr.right)).toFixed(2)},
      headings:headings.map(h=>({text:(h.textContent||'').trim().slice(0,100),rect:r(h),textAlign:css(h).textAlign})),
      split:splitKids.length===2?{rect:r(split),childRects:splitKids.map(r),columnGap:gapX(splitKids[0],splitKids[1])}:null,
      grids,cards,media,tables,form:form?{rect:r(form),fieldRects:fieldBoxes,verticalFieldGaps:fieldGaps}:null,
      anomalies:{overflow,verticalVoids}});
    if(overflow.length)out.anomalies.push({section:wrap.id,type:'horizontal-overflow',count:overflow.length});
    if(verticalVoids.length)out.anomalies.push({section:wrap.id,type:'large-void',values:verticalVoids});
  }
  return out;
}
"""


def file_record(rel: str) -> dict:
    p = ROOT / rel
    st = p.stat()
    return {
        "path": rel,
        "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
        "bytes": st.st_size,
        "mtimeEpoch": st.st_mtime,
        "mtime": datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat(),
    }


def render_lane(label: str, lane: Path) -> dict:
    comp_path = lane / "composition.json"
    original = comp_path.read_bytes()
    original_stat = comp_path.stat()
    cmd = [
        str(ROOT / "venv/bin/python"),
        "brand_pipeline/render_composition.py",
        str(comp_path.relative_to(ROOT)),
        "runs/remote/brand/brand.yaml",
        "-o",
        str(lane.relative_to(ROOT)),
        *STYLE_ARGS[label],
    ]
    started = time.perf_counter()
    proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    elapsed = time.perf_counter() - started
    (lane / "normalized-gates/render-console.txt").write_text(proc.stdout + proc.stderr)
    if comp_path.read_bytes() != original:
        comp_path.write_bytes(original)
    os.utime(comp_path, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns))
    if proc.returncode:
        raise RuntimeError(f"render failed for {label}: {proc.stderr}")
    return {"command": " ".join(cmd), "elapsedSeconds": round(elapsed, 4)}


def validate_lane(label: str, lane: Path, schema: dict) -> dict:
    doc = json.loads((lane / "composition.json").read_text())
    errors = sorted(Draft202012Validator(schema).iter_errors(doc), key=lambda e: list(e.path))
    lines = ["PASS" if not errors else "FAIL"]
    lines += [f"{'/'.join(map(str, e.path))}: {e.message}" for e in errors]
    (lane / "normalized-gates/schema-validation.txt").write_text("\n".join(lines) + "\n")
    return {"pass": not errors, "errorCount": len(errors), "errors": lines[1:]}


def wait_for_images(page) -> None:
    page.evaluate("""async () => {
      await document.fonts.ready;
      await Promise.all([...document.images].map(img => img.complete ? null :
        new Promise(resolve => { img.addEventListener('load',resolve,{once:true});
          img.addEventListener('error',resolve,{once:true}); })));
    }""")


def capture_and_measure(label: str, lane: Path) -> dict:
    out_dir = lane / "normalized-shots"
    for p in out_dir.glob("*.png"):
        p.unlink()
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(
            viewport={"width": 1440, "height": 1000},
            device_scale_factor=1,
            reduced_motion="reduce",
        )
        page.goto((lane / "index.html").resolve().as_uri(), wait_until="networkidle")
        page.add_style_tag(content=SETTLE_CSS)
        wait_for_images(page)
        page.wait_for_timeout(700)
        page.screenshot(path=str(out_dir / "00-full-page-1440.png"), full_page=True)
        sections = page.locator('div.cs-surface[id^="sec-"] > section.cs-section')
        count = min(10, sections.count())
        for i in range(count):
            sec = sections.nth(i)
            sec.scroll_into_view_if_needed()
            page.wait_for_timeout(100)
            sec.screenshot(path=str(out_dir / f"{i+1:02d}-section-1440.png"))
        geometry = page.evaluate(GEOMETRY_JS)
        browser.close()
    return geometry


def side_by_side() -> None:
    out = COMPARE / "shots"
    for p in out.glob("*.png"):
        p.unlink()
    names = ["00-full-page-1440.png"] + [f"{i:02d}-section-1440.png" for i in range(1, 11)]
    for name in names:
        images = [Image.open(LANES[k] / "normalized-shots" / name).convert("RGB") for k in LANES]
        target_w = 680
        resized = []
        for im in images:
            h = round(im.height * target_w / im.width)
            resized.append(im.resize((target_w, h), Image.Resampling.LANCZOS))
        canvas = Image.new("RGB", (target_w * 2 + 24, max(i.height for i in resized) + 44), "white")
        draw = ImageDraw.Draw(canvas)
        draw.text((8, 12), "Candidate A", fill="black")
        draw.text((target_w + 32, 12), "Candidate B", fill="black")
        canvas.paste(resized[0], (0, 44))
        canvas.paste(resized[1], (target_w + 24, 44))
        canvas.save(out / name.replace(".png", "-side-by-side.png"))


def main() -> int:
    state = {
        "schemaVersion": "render-state.v1",
        "capturedAt": datetime.now(timezone.utc).isoformat(),
        "note": "Single shared renderer/composer state used for both normalized candidates.",
        "files": [file_record(p) for p in SHARED_FILES],
    }
    (COMPARE / "RENDER-STATE.json").write_text(json.dumps(state, indent=2) + "\n")
    schema = json.loads((ROOT / "brand_pipeline/spec/composition.v1.schema.json").read_text())
    run = {}
    geometry = {"generatedAt": datetime.now(timezone.utc).isoformat(), "candidates": {}}
    for label, lane in LANES.items():
        run[label] = {"render": render_lane(label, lane)}
        run[label]["schema"] = validate_lane(label, lane, schema)
        geometry["candidates"][label] = capture_and_measure(label, lane)
    side_by_side()
    (COMPARE / "geometry-raw.json").write_text(json.dumps(geometry, indent=2) + "\n")
    (COMPARE / "normalization-run.json").write_text(json.dumps(run, indent=2) + "\n")
    print(json.dumps(run, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
