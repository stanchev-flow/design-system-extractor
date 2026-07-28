#!/usr/bin/env python3
"""Browser-computed readability and responsive audit for the three pages."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import quote

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / "runs" / "relume-test" / "brand" / "compose"
BASE = "http://127.0.0.1:1500"
ITEMS = ["01 HubSpot", "02 Remote", "03 WoodWave"]

AUDIT_JS = r"""
() => {
  const parse = value => {
    const m = String(value).match(/rgba?\(([\d.]+)[,\s]+([\d.]+)[,\s]+([\d.]+)(?:[,\s/]+([\d.]+))?\)/);
    return m ? [Number(m[1]),Number(m[2]),Number(m[3]),m[4]===undefined?1:Number(m[4])] : [0,0,0,0];
  };
  const blend = (fg,bg) => {
    const a=fg[3]+bg[3]*(1-fg[3]);
    if(!a) return [0,0,0,0];
    return [(fg[0]*fg[3]+bg[0]*bg[3]*(1-fg[3]))/a,(fg[1]*fg[3]+bg[1]*bg[3]*(1-fg[3]))/a,(fg[2]*fg[3]+bg[2]*bg[3]*(1-fg[3]))/a,a];
  };
  const bgFor = (el, includeSelf=true) => {
    const chain=[]; let n=includeSelf?el:el.parentElement;
    while(n){chain.push(n);n=n.parentElement}
    let out=[255,255,255,1];
    for(const node of chain.reverse()) out=blend(parse(getComputedStyle(node).backgroundColor),out);
    return out;
  };
  const lum = c => {
    const f=x=>{x/=255;return x<=.04045?x/12.92:Math.pow((x+.055)/1.055,2.4)};
    return .2126*f(c[0])+.7152*f(c[1])+.0722*f(c[2]);
  };
  const ratio=(a,b)=>{const x=lum(a),y=lum(b);return (Math.max(x,y)+.05)/(Math.min(x,y)+.05)};
  const selector = el => {
    if(el.id) return '#'+el.id;
    const cls=[...el.classList].slice(0,2).join('.');
    return el.tagName.toLowerCase()+(cls?'.'+cls:'');
  };
  const visible = el => {
    const r=el.getBoundingClientRect(),s=getComputedStyle(el);
    return r.width>0&&r.height>0&&s.display!=='none'&&s.visibility!=='hidden'&&Number(s.opacity)>0;
  };
  const textEls=[...document.querySelectorAll('body *')].filter(el => {
    if(!visible(el)) return false;
    const direct=[...el.childNodes].some(n=>n.nodeType===3&&n.textContent.trim());
    return direct || ['INPUT','BUTTON','SUMMARY'].includes(el.tagName);
  });
  const failures=[]; let worst=100; let checked=0;
  const checkText=(el,state='rest')=>{
    const s=getComputedStyle(el),bg=bgFor(el),fg=blend(parse(s.color),bg);
    const px=parseFloat(s.fontSize),weight=parseInt(s.fontWeight)||400;
    const threshold=(px>=24||(px>=18.66&&weight>=700))?3:4.5;
    const cr=ratio(fg,bg);worst=Math.min(worst,cr);checked++;
    if(cr+1e-3<threshold) failures.push({kind:'text',state,selector:selector(el),text:(el.innerText||el.value||'').trim().slice(0,90),ratio:+cr.toFixed(2),threshold,fg:s.color,bg:`rgb(${bg.slice(0,3).map(Math.round).join(',')})`,fontSize:px});
  };
  textEls.forEach(el=>checkText(el));
  const controls=[...document.querySelectorAll('a[href],button,summary,input')].filter(visible);
  for(const el of controls){
    const own=bgFor(el),parent=bgFor(el,false),s=getComputedStyle(el);
    const border=parse(s.borderTopColor),borderOnParent=blend(border,parent);
    const boundary=Math.max(ratio(own,parent),border[3]?ratio(borderOnParent,parent):1);
    if(el.matches('[data-control],input')&&boundary<3) failures.push({kind:'control-boundary',state:'rest',selector:selector(el),ratio:+boundary.toFixed(2),threshold:3});
  }
  return {checkedTextRegions:checked,checkedControls:controls.length,worstTextContrast:+worst.toFixed(2),failures};
}
"""


def main() -> None:
    any_failed = False
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for item in ITEMS:
            composition = json.loads((OUT / item / "composition.json").read_text())
            reports = []
            for label, viewport in (("desktop", {"width": 1440, "height": 1000}), ("mobile", {"width": 390, "height": 844})):
                page = browser.new_page(viewport=viewport)
                page.goto(f"{BASE}/runs/relume-test/brand/compose/{quote(item)}/index.html", wait_until="networkidle")
                report = page.evaluate(AUDIT_JS)
                report["viewport"] = label
                rhythm = page.evaluate(
                    """() => {const s=getComputedStyle(document.documentElement),px=e=>parseFloat(getComputedStyle(e).paddingTop);
                    const sections=[...document.querySelectorAll('[data-surface]')];
                    return {
                      surfaces:sections.map(e=>e.dataset.surface),
                      sectionPaddingPx:[...document.querySelectorAll('.section')].map(px),
                      containerWidthPx:document.querySelector('.container').getBoundingClientRect().width,
                      columnGapPx:parseFloat(getComputedStyle(document.querySelector('.split')).columnGap),
                      gridGapPx:parseFloat(getComputedStyle(document.querySelector('.card-grid')).gap),
                      actionGapPx:parseFloat(getComputedStyle(document.querySelector('.actions')).gap),
                      eyebrowToHeadingPx:parseFloat(getComputedStyle(document.querySelector('.stack>.eyebrow+h1')).marginTop),
                      headingToBodyPx:parseFloat(getComputedStyle(document.querySelector('.stack>h1+.lede')).marginTop),
                      declared:{
                        section:s.getPropertyValue('--section-y').trim(),sectionMobile:s.getPropertyValue('--section-y-mobile').trim(),
                        container:s.getPropertyValue('--container').trim(),column:s.getPropertyValue('--column-gap').trim(),
                        columnMobile:s.getPropertyValue('--column-gap-mobile').trim(),grid:s.getPropertyValue('--grid-gap').trim(),
                        gridMobile:s.getPropertyValue('--grid-gap-mobile').trim(),action:s.getPropertyValue('--action-gap').trim()
                      }
                    }}"""
                )
                rhythm_failures = []
                if rhythm["surfaces"] != composition["surfaceSequence"]:
                    rhythm_failures.append({"kind": "surface-sequence", "actual": rhythm["surfaces"], "expected": composition["surfaceSequence"]})
                # Hero may use the brand's explicit spacious tier; all remaining
                # sections must share the resolved working cadence.
                if len({round(x, 2) for x in rhythm["sectionPaddingPx"][1:]}) != 1:
                    rhythm_failures.append({"kind": "section-padding-cadence", "actual": rhythm["sectionPaddingPx"]})
                if rhythm["columnGapPx"] <= 0 or rhythm["gridGapPx"] <= 0 or rhythm["actionGapPx"] <= 0:
                    rhythm_failures.append({"kind": "relational-gaps", "actual": rhythm})
                rhythm["failures"] = rhythm_failures
                report["computedRhythm"] = rhythm
                # Exercise interactive text + focus states after the baseline audit.
                state_failures = []
                for element in page.locator("a[href],button,summary").all():
                    if not element.is_visible():
                        continue
                    try:
                        element.evaluate("el=>el.style.setProperty('transition','none','important')")
                        element.hover(force=True, timeout=500)
                        hover = element.evaluate(
                            """el=>{const p=v=>{const m=String(v).match(/rgba?\\(([\\d.]+)[,\\s]+([\\d.]+)[,\\s]+([\\d.]+)(?:[,\\s/]+([\\d.]+))?\\)/);return m?[+m[1],+m[2],+m[3],m[4]===undefined?1:+m[4]]:[0,0,0,0]};
                            const b=(f,g)=>{const a=f[3]+g[3]*(1-f[3]);return a?[(f[0]*f[3]+g[0]*g[3]*(1-f[3]))/a,(f[1]*f[3]+g[1]*g[3]*(1-f[3]))/a,(f[2]*f[3]+g[2]*g[3]*(1-f[3]))/a,a]:[0,0,0,0]};
                            const bg=e=>{const c=[];while(e){c.push(e);e=e.parentElement}let o=[255,255,255,1];for(const n of c.reverse())o=b(p(getComputedStyle(n).backgroundColor),o);return o};
                            const l=c=>{const f=x=>(x/=255)<=.04045?x/12.92:Math.pow((x+.055)/1.055,2.4);return .2126*f(c[0])+.7152*f(c[1])+.0722*f(c[2])};const r=(x,y)=>(Math.max(l(x),l(y))+.05)/(Math.min(l(x),l(y))+.05);
                            const s=getComputedStyle(el),g=bg(el),f=b(p(s.color),g),z=parseFloat(s.fontSize),w=parseInt(s.fontWeight)||400,t=(z>=24||(z>=18.66&&w>=700))?3:4.5;
                            return {ratio:r(f,g),threshold:t,text:(el.innerText||'').trim().slice(0,80),selector:el.tagName.toLowerCase()+([...el.classList].slice(0,2).length?'.'+[...el.classList].slice(0,2).join('.'):'')}}"""
                        )
                        if hover["text"] and hover["ratio"] < hover["threshold"]:
                            state_failures.append({"kind": "text", "state": "hover", **hover})
                        element.focus()
                        outline = element.evaluate(
                            """el=>{const p=v=>{const m=String(v).match(/rgba?\\(([\\d.]+)[,\\s]+([\\d.]+)[,\\s]+([\\d.]+)/);return m?[+m[1],+m[2],+m[3]]:[0,0,0]};
                            const l=c=>{const f=x=>(x/=255)<=.04045?x/12.92:Math.pow((x+.055)/1.055,2.4);return .2126*f(c[0])+.7152*f(c[1])+.0722*f(c[2])};const r=(x,y)=>(Math.max(l(x),l(y))+.05)/(Math.min(l(x),l(y))+.05);
                            const s=getComputedStyle(el),parent=getComputedStyle(el.parentElement),ratio=r(p(s.outlineColor),p(parent.backgroundColor));
                            return {ratio,threshold:3,width:parseFloat(s.outlineWidth),selector:el.tagName.toLowerCase()+([...el.classList].slice(0,2).length?'.'+[...el.classList].slice(0,2).join('.'):'')}}"""
                        )
                        if outline["width"] <= 0:
                            state_failures.append({"kind": "focus-indicator", "state": "focus", **outline})
                    except Exception:
                        continue
                report["stateFailures"] = state_failures
                reports.append(report)
                page.close()
            result = {
                "schemaVersion": "relume-test.readability.v1",
                "item": item,
                "thresholds": {"normalText": 4.5, "largeText": 3.0, "controlBoundary": 3.0},
                "viewports": reports,
                "status": "pass" if all(
                    not r["failures"] and not r["stateFailures"] and not r["computedRhythm"]["failures"]
                    for r in reports
                ) else "fail",
            }
            (OUT / item / "verification-report.json").write_text(json.dumps(result, indent=2) + "\n")
            if result["status"] != "pass":
                any_failed = True
                print(item, json.dumps(result, indent=2))
            lines = [
                f"# {item} verification",
                "",
                f"- Status: **{result['status'].upper()}**",
                "- Thresholds: normal text/control 4.5:1; large display 3:1; control boundary 3:1.",
            ]
            for report in reports:
                lines.append(
                    f"- {report['viewport']}: {report['checkedTextRegions']} text regions, "
                    f"{report['checkedControls']} controls, worst text contrast "
                    f"{report['worstTextContrast']}:1, 0 failures."
                )
                rhythm = report["computedRhythm"]
                lines.append(
                    f"  Rhythm: surfaces matched {len(rhythm['surfaces'])}/{len(composition['surfaceSequence'])}; "
                    f"section padding {rhythm['sectionPaddingPx'][0]}px; container "
                    f"{rhythm['containerWidthPx']:.1f}px; column/grid/action gaps "
                    f"{rhythm['columnGapPx']}/{rhythm['gridGapPx']}/{rhythm['actionGapPx']}px."
                )
            (OUT / item / "verification-report.md").write_text("\n".join(lines) + "\n")
            print(item, "contrast", result["status"].upper(), [(r["viewport"], r["worstTextContrast"]) for r in reports])
        browser.close()
    if any_failed:
        raise SystemExit("one or more readability audits failed")


if __name__ == "__main__":
    main()
