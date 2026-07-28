#!/usr/bin/env python3
"""Compare browser-computed controls to each canonical extracted matrix."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import quote

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / "runs" / "relume-test" / "brand" / "compose"
BASE = "http://127.0.0.1:1500"
ITEMS = ("01 HubSpot", "02 Remote", "03 WoodWave")

SNAPSHOT_JS = """el=>{const s=getComputedStyle(el);return {
background:s.backgroundColor,color:s.color,borderWidth:s.borderTopWidth,
borderStyle:s.borderTopStyle,borderColor:s.borderTopColor,radius:s.borderRadius,
height:s.height,paddingTop:s.paddingTop,paddingRight:s.paddingRight,
fontSize:s.fontSize,fontWeight:s.fontWeight,outlineWidth:s.outlineWidth,
outlineStyle:s.outlineStyle,outlineColor:s.outlineColor,outlineOffset:s.outlineOffset}}"""


def expected_contract(contract: dict, state: str, inverse: bool) -> dict:
    c = dict(contract)
    if inverse and contract.get("onInverse"):
        c.update(contract["onInverse"])
    if state == "hover":
        c["bg"], c["fg"] = c["bgHover"], c["fgHover"]
    elif state == "pressed":
        c["bg"], c["fg"] = c["bgPressed"], c["fgPressed"]
    elif state == "disabled":
        c["bg"], c["fg"] = c["bgDisabled"], c["fgDisabled"]
    return c


def normalize_expected(page, contract: dict) -> dict:
    border = contract.get("border", "none")
    return page.evaluate(
        """c=>{const e=document.createElement('button');Object.assign(e.style,{
        position:'fixed',left:'-10000px',display:'inline-flex',boxSizing:'border-box',
        background:c.bg,color:c.fg,border:c.border,borderRadius:c.radius,
        height:c.height,padding:c.padding,fontSize:String(c.sizeRem||1)+'rem',
        fontWeight:String(c.weight||400),outline:c.outline||'none',
        outlineOffset:c.outlineOffset||'0'});document.body.append(e);
        const s=getComputedStyle(e),o={background:s.backgroundColor,color:s.color,
        borderWidth:s.borderTopWidth,borderStyle:s.borderTopStyle,
        borderColor:s.borderTopColor,radius:s.borderRadius,height:s.height,
        paddingTop:s.paddingTop,paddingRight:s.paddingRight,fontSize:s.fontSize,
        fontWeight:s.fontWeight,outlineWidth:s.outlineWidth,outlineStyle:s.outlineStyle,
        outlineColor:s.outlineColor,outlineOffset:s.outlineOffset};e.remove();return o}""",
        {
            "bg": contract.get("bg", "transparent"),
            "fg": contract.get("fg", "currentColor"),
            "border": border,
            "radius": contract.get("radius", "0"),
            "height": contract.get("height", contract.get("size", "auto")),
            "padding": contract.get("padding", "0"),
            "sizeRem": contract.get("sizeRem", 1),
            "weight": contract.get("weight", 400),
        },
    )


def focus_expected(page, focus: str) -> dict:
    declarations = {}
    for part in focus.split(";"):
        part = part.strip()
        if part.startswith("outline "):
            declarations["outline"] = part.removeprefix("outline ").strip()
        elif part.startswith("outline-offset"):
            declarations["outlineOffset"] = part.removeprefix("outline-offset").replace(":", "", 1).strip()
    return page.evaluate(
        """c=>{const e=document.createElement('button');e.style.outline=c.outline||'none';
        e.style.outlineOffset=c.outlineOffset||'0';document.body.append(e);const s=getComputedStyle(e);
        const o={outlineWidth:s.outlineWidth,outlineStyle:s.outlineStyle,
        outlineColor:s.outlineColor,outlineOffset:s.outlineOffset};e.remove();return o}""",
        declarations,
    )


def compare(actual: dict, expected: dict, keys: tuple[str, ...], context: dict) -> list[dict]:
    return [
        {**context, "property": key, "actual": actual[key], "expected": expected[key]}
        for key in keys
        if actual[key] != expected[key]
    ]


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for item in ITEMS:
            composition = json.loads((OUT / item / "composition.json").read_text())
            contracts = composition["componentContracts"]
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            page.goto(f"{BASE}/runs/relume-test/brand/compose/{quote(item)}/index.html", wait_until="networkidle")
            failures: list[dict] = []
            checked = 0
            for name, contract in contracts.items():
                if name not in ("primary", "secondary", "tertiary", "textCta", "menu", "icon"):
                    continue
                surfaces = (False, True) if contract.get("onInverse") else (False,)
                for inverse in surfaces:
                    probe = page.evaluate_handle(
                        """x=>{const host=document.createElement('div');host.className=x.inverse?'section--inverse':'section--primary';
                        host.style.cssText='position:fixed;left:0;top:0;padding:20px;z-index:99999;opacity:.01';
                        const e=document.createElement('button');e.type='button';e.dataset.control=x.name;
                        e.className='control control--'+x.name+(x.name==='menu'?' menu-control':'')+(x.name==='icon'?' rail-control':'');
                        e.textContent=x.name;e.style.setProperty('display','inline-flex','important');e.style.setProperty('transition','none','important');
                        host.append(e);document.body.append(host);return e}""",
                        {"name": name, "inverse": inverse},
                    ).as_element()
                    assert probe is not None
                    base_context = {"component": name, "surface": "inverse" if inverse else "primary"}
                    for state in ("rest", "hover", "pressed", "disabled"):
                        probe.evaluate("el=>{el.disabled=false;el.blur()}")
                        page.mouse.move(1000, 700)
                        if state == "hover":
                            probe.hover(force=True)
                        elif state == "pressed":
                            box = probe.bounding_box()
                            assert box
                            page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
                            page.mouse.down()
                        elif state == "disabled":
                            probe.evaluate("el=>el.disabled=true")
                        actual = probe.evaluate(SNAPSHOT_JS)
                        resolved = expected_contract(contract, state, inverse)
                        expected = normalize_expected(page, resolved)
                        keys = (
                            "background", "color", "borderWidth", "borderStyle",
                            "borderColor", "radius", "paddingTop", "paddingRight",
                            "fontSize", "fontWeight",
                        )
                        if resolved.get("height", resolved.get("size", "auto")) != "auto":
                            keys += ("height",)
                        failures.extend(compare(actual, expected, keys, {**base_context, "state": state}))
                        checked += len(keys)
                        if state == "pressed":
                            page.mouse.up()
                    probe.evaluate("el=>{el.disabled=false;el.focus()}")
                    actual_focus = probe.evaluate(SNAPSHOT_JS)
                    focus = (contract.get("onInverse") or {}).get("focus", contract["focus"]) if inverse else contract["focus"]
                    expected_focus = focus_expected(page, focus)
                    failures.extend(
                        compare(
                            actual_focus,
                            expected_focus,
                            ("outlineWidth", "outlineStyle", "outlineColor", "outlineOffset"),
                            {**base_context, "state": "focus"},
                        )
                    )
                    checked += 4
                    probe.evaluate("el=>el.parentElement.remove()")

            result = {
                "schemaVersion": "relume-test.component-fidelity.v1",
                "item": item,
                "contractSource": composition["componentContractSource"],
                "checkedProperties": checked,
                "components": ["primary", "secondary", "tertiary", "textCta", "menu", "icon"],
                "degradations": composition["componentDegradations"],
                "failures": failures,
                "status": "pass" if not failures else "fail",
            }
            (OUT / item / "component-fidelity-report.json").write_text(json.dumps(result, indent=2) + "\n")
            (OUT / item / "component-fidelity-report.md").write_text(
                f"# {item} component fidelity\n\n"
                f"- Status: **{result['status'].upper()}**\n"
                f"- Computed properties checked: {checked}\n"
                f"- Declared degradations: {len(result['degradations'])}\n"
                f"- Failures: {len(failures)}\n"
            )
            print(item, result["status"].upper(), checked, "properties", len(failures), "failures")
            if failures:
                print(json.dumps(failures[:20], indent=2))
                raise SystemExit(1)
            page.close()
        browser.close()


if __name__ == "__main__":
    main()
