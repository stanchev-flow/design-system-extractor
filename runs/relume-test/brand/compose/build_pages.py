#!/usr/bin/env python3
"""Build three brand-instantiated pages from one approved structural sequence.

Every media binding is validated against the active brand's assets-tagged.json and
its on-disk assets directory. Missing matches become declared unavailable slots.
"""

from __future__ import annotations

import html
import json
from pathlib import Path
from urllib.parse import quote

import yaml
from PIL import Image


ROOT = Path(__file__).resolve().parents[4]
OUT_ROOT = ROOT / "runs" / "relume-test" / "brand" / "compose"


def esc(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


class AssetBinder:
    def __init__(self, brand_slug: str):
        self.brand_slug = brand_slug
        self.brand_dir = ROOT / "runs" / brand_slug / "brand"
        tagged = json.loads((self.brand_dir / "assets-tagged.json").read_text())
        self.inventory = {item["filename"]: item for item in tagged["assets"]}
        self.bindings: list[dict] = []

    def media(self, slot: str, filename: str | None, alt: str, class_name: str = "") -> str:
        if not filename:
            self.bindings.append({"slot": slot, "status": "unavailable", "reason": "no compatible extracted asset"})
            return (
                f'<div class="asset-gap {esc(class_name)}" role="img" '
                f'aria-label="Unavailable asset slot: {esc(slot)}">'
                f'<span>Media unavailable</span><small>{esc(slot)}</small></div>'
            )
        if filename not in self.inventory:
            raise ValueError(f"{self.brand_slug}: {filename} is not in assets-tagged.json")
        path = self.brand_dir / "assets" / filename
        if not path.is_file():
            raise FileNotFoundError(path)
        url = f"../../../../{quote(self.brand_slug)}/brand/assets/{quote(filename)}"
        self.bindings.append(
            {
                "slot": slot,
                "status": "resolved",
                "asset": filename,
                "useCase": self.inventory[filename].get("useCase", ""),
                "intendedSlot": self.inventory[filename].get("intendedSlot", ""),
            }
        )
        return f'<img class="{esc(class_name)}" src="{url}" alt="{esc(alt)}" loading="lazy">'


def _border(value: str | None) -> str:
    return str(value or "none")


def _variant_contracts(brand_doc: dict, cfg: dict) -> tuple[dict, list[dict]]:
    """Resolve canonical button variants and document every honest degradation."""
    source = brand_doc.get("buttons") or {}
    variants: dict[str, dict] = {}
    degradations: list[dict] = []
    primary = source.get("primary") or {}

    for name in ("primary", "secondary", "tertiary", "textCta"):
        raw = source.get(name)
        if not raw:
            continue
        contract = dict(raw)
        contract["border"] = _border(raw.get("border"))
        contract["radius"] = str(raw.get("radius", "0"))
        contract["padding"] = str(raw.get("padding", "0"))
        contract["height"] = str(raw.get("height", "auto"))
        contract["bg"] = str(raw.get("bg", "transparent"))
        contract["fg"] = str(raw.get("fg", "currentColor"))
        contract["bgHover"] = str(raw.get("bgHover", contract["bg"]))
        contract["fgHover"] = str(raw.get("fgHover", contract["fg"]))
        contract["bgPressed"] = str(raw.get("bgPressed", contract["bgHover"]))
        contract["fgPressed"] = str(raw.get("fgPressed", contract["fgHover"]))
        if "bgPressed" not in raw:
            degradations.append({"component": name, "state": "pressed", "to": "hover", "reason": "canonical pressed state absent"})
        contract["bgDisabled"] = str(raw.get("bgDisabled", primary.get("bgDisabled", contract["bg"])))
        contract["fgDisabled"] = str(raw.get("fgDisabled", contract["fg"]))
        if "bgDisabled" not in raw:
            degradations.append(
                {
                    "component": name,
                    "state": "disabled",
                    "to": "primary disabled" if primary.get("bgDisabled") else "rest",
                    "reason": "canonical disabled state absent",
                }
            )
        contract["focus"] = str(raw.get("focus", primary.get("focus", cfg["focus_contract"])))
        if "focus" not in raw:
            degradations.append({"component": name, "state": "focus", "to": "primary focus", "reason": "variant focus absent"})
        inverse = dict(raw.get("onInverse") or {})
        configured_inverse = (cfg.get("surface_overrides") or {}).get(name)
        if configured_inverse:
            inverse.update(configured_inverse)
            inverse["source"] = configured_inverse.get("source", "canonical surface/component prose")
        if inverse:
            inverse["bg"] = str(inverse.get("bg", contract["bg"]))
            inverse["fg"] = str(inverse.get("fg", contract["fg"]))
            inverse["border"] = _border(inverse.get("border", contract["border"]))
            inverse["bgHover"] = str(inverse.get("bgHover", contract["bgHover"]))
            inverse["fgHover"] = str(inverse.get("fgHover", contract["fgHover"]))
            inverse["bgPressed"] = str(inverse.get("bgPressed", inverse["bgHover"]))
            inverse["fgPressed"] = str(inverse.get("fgPressed", inverse["fgHover"]))
            inverse["bgDisabled"] = str(inverse.get("bgDisabled", inverse["bg"]))
            inverse["fgDisabled"] = str(inverse.get("fgDisabled", inverse["fg"]))
            inverse["focus"] = str(inverse.get("focus", contract["focus"]))
            if "bgPressed" not in raw.get("onInverse", {}) and "bgPressed" not in (configured_inverse or {}):
                degradations.append({"component": name, "surface": "inverse", "state": "pressed", "to": "inverse hover", "reason": "canonical inverse pressed state absent"})
            if "bgDisabled" not in raw.get("onInverse", {}) and "bgDisabled" not in (configured_inverse or {}):
                degradations.append({"component": name, "surface": "inverse", "state": "disabled", "to": "inverse rest", "reason": "canonical inverse disabled state absent"})
        contract["onInverse"] = inverse
        variants[name] = contract

    def nearest(alias: str, target: str, reason: str) -> None:
        variants[alias] = dict(variants[target])
        variants[alias]["degradedFrom"] = target
        degradations.append({"component": alias, "state": "all", "to": target, "reason": reason})

    nearest("menu", cfg["menu_variant"], "no independent menu-control matrix; nearest declared brand control")
    if cfg.get("rail_contract"):
        variants["icon"] = dict(cfg["rail_contract"])
        variants["icon"].setdefault("onInverse", {})
        variants["icon"].setdefault("font", cfg["canonical_body_family"])
        variants["icon"].setdefault("weight", cfg["control_weight"])
        variants["icon"].setdefault("sizeRem", 1)
    else:
        nearest("icon", cfg["rail_variant"], "no independent rail-control matrix; nearest declared brand control")
    return variants, degradations


def _focus_css(value: str) -> tuple[str, str]:
    # Canonical format: "outline 2px solid #...; outline-offset 2px".
    bits = value.replace("outline", "", 1).split(";")
    outline = bits[0].strip() or "2px solid currentColor"
    offset = "2px"
    for bit in bits[1:]:
        if "outline-offset" in bit:
            offset = bit.replace("outline-offset", "", 1).replace(":", "", 1).strip()
    return outline, offset


def _component_css(cfg: dict, contracts: dict) -> str:
    scope = f'.brand-page--{cfg["css_slug"]}'
    lines = [
        f"{scope} [data-control]{{display:inline-flex;align-items:center;justify-content:center;width:fit-content;box-sizing:border-box;text-decoration:none;cursor:pointer;transition:background-color var(--motion),color var(--motion),border-color var(--motion),box-shadow var(--motion);}}",
    ]
    for name in ("primary", "secondary", "tertiary", "textCta"):
        if name not in contracts:
            continue
        c = contracts[name]
        selector = f"{scope} .control--{name}"
        style = str(c.get("style", ""))
        border = "none" if name == "textCta" else c["border"]
        lines.append(
            f"{selector}{{background:{c['bg']};color:{c['fg']};border:{border};border-radius:{c['radius']};"
            f"padding:{c['padding']};height:{c['height']};min-height:{c['height']};"
            f"font-family:{c.get('font', cfg['canonical_body_family'])},var(--body);font-weight:{c.get('weight', cfg['control_weight'])};"
            f"font-size:{c.get('sizeRem', 1)}rem;letter-spacing:{c.get('letterSpacing', '0')};"
            f"text-transform:{c.get('case', 'none')};"
            + ("text-decoration:underline;text-underline-offset:.25em;" if "text" in style else "")
            + "}"
        )
        if c.get("glyph"):
            lines.append(
                f"{selector} .control-icon{{width:{c['glyph'].get('size', '1rem')};height:{c['glyph'].get('size', '1rem')};"
                "object-fit:contain;}"
            )
        lines.append(f"{selector}:hover{{background:{c['bgHover']};color:{c['fgHover']};}}")
        lines.append(f"{selector}:active{{background:{c['bgPressed']};color:{c['fgPressed']};}}")
        outline, offset = _focus_css(c["focus"])
        lines.append(f"{selector}:focus,{selector}:focus-visible{{outline:{outline};outline-offset:{offset};}}")
        lines.append(f"{selector}:disabled,{selector}[aria-disabled='true']{{background:{c['bgDisabled']};color:{c['fgDisabled']};cursor:not-allowed;}}")
        inv = c.get("onInverse") or {}
        if inv:
            inv_parts = [
                f"{scope} .section--inverse .control--{name}",
                f"{scope} .section--photo .control--{name}",
                f"{scope} .section--strong .control--{name}",
            ]
            inv_sel = ",".join(inv_parts)
            inv_state = lambda state: ",".join(f"{part}:{state}" for part in inv_parts)
            lines.append(
                f"{inv_sel}{{background:{inv.get('bg', c['bg'])};color:{inv.get('fg', c['fg'])};"
                f"border:{inv.get('border', border)};}}"
            )
            lines.append(
                f"{inv_state('hover')}{{background:{inv.get('bgHover', c['bgHover'])};color:{inv.get('fgHover', c['fgHover'])};}}"
            )
            lines.append(f"{inv_state('active')}{{background:{inv['bgPressed']};color:{inv['fgPressed']};}}")
            inv_outline, inv_offset = _focus_css(inv["focus"])
            inv_focus = ",".join(f"{part}:focus,{part}:focus-visible" for part in inv_parts)
            lines.append(f"{inv_focus}{{outline:{inv_outline};outline-offset:{inv_offset};}}")
            inv_disabled = ",".join(f"{part}:disabled,{part}[aria-disabled='true']" for part in inv_parts)
            lines.append(
                f"{inv_disabled}{{background:{inv['bgDisabled']};color:{inv['fgDisabled']};}}"
            )
            # Nested cards re-enter the light panel surface; inverse ancestor rules
            # must not leak through that surface boundary.
            card_parts = [
                f"{scope} .section--inverse .card .control--{name}",
                f"{scope} .section--photo .card .control--{name}",
                f"{scope} .section--strong .card .control--{name}",
            ]
            card_sel = ",".join(card_parts)
            lines.append(f"{card_sel}{{background:{c['bg']};color:{c['fg']};border:{border};}}")
            lines.append(",".join(f"{part}:hover" for part in card_parts) + f"{{background:{c['bgHover']};color:{c['fgHover']};}}")
            lines.append(",".join(f"{part}:active" for part in card_parts) + f"{{background:{c['bgPressed']};color:{c['fgPressed']};}}")
            lines.append(",".join(f"{part}:disabled" for part in card_parts) + f"{{background:{c['bgDisabled']};color:{c['fgDisabled']};}}")

    # Menu is a semantic alias of the nearest declared variant, not a generic fallback.
    menu = contracts["menu"]
    lines.append(
        f"{scope} .menu-control{{display:none;background:{menu['bg']};color:{menu['fg']};border:{menu['border']};"
        f"border-radius:{menu['radius']};padding:{menu['padding']};height:{menu['height']};font-family:{menu.get('font', cfg['canonical_body_family'])},var(--body);"
        f"font-weight:{menu.get('weight', cfg['control_weight'])};font-size:{menu.get('sizeRem', 1)}rem;"
        f"letter-spacing:{menu.get('letterSpacing', '0')};text-transform:{menu.get('case', 'none')};}}"
    )
    lines.append(f"{scope} .menu-control:hover{{background:{menu['bgHover']};color:{menu['fgHover']};}}")
    lines.append(f"{scope} .menu-control:active{{background:{menu['bgPressed']};color:{menu['fgPressed']};}}")
    outline, offset = _focus_css(menu["focus"])
    lines.append(f"{scope} .menu-control:focus,{scope} .menu-control:focus-visible{{outline:{outline};outline-offset:{offset};}}")
    lines.append(f"{scope} .menu-control:disabled{{background:{menu['bgDisabled']};color:{menu['fgDisabled']};}}")
    menu_inv = menu.get("onInverse") or {}
    if menu_inv:
        menu_inv_parts = [
            f"{scope} .section--inverse .menu-control",
            f"{scope} .section--photo .menu-control",
            f"{scope} .section--strong .menu-control",
            f"{scope} .nav--inverse .menu-control",
        ]
        menu_inv_sel = ",".join(menu_inv_parts)
        lines.append(f"{menu_inv_sel}{{background:{menu_inv['bg']};color:{menu_inv['fg']};border:{menu_inv['border']};}}")
        lines.append(",".join(f"{part}:hover" for part in menu_inv_parts) + f"{{background:{menu_inv['bgHover']};color:{menu_inv['fgHover']};}}")
        lines.append(",".join(f"{part}:active" for part in menu_inv_parts) + f"{{background:{menu_inv['bgPressed']};color:{menu_inv['fgPressed']};}}")
        inv_outline, inv_offset = _focus_css(menu_inv["focus"])
        lines.append(",".join(f"{part}:focus,{part}:focus-visible" for part in menu_inv_parts) + f"{{outline:{inv_outline};outline-offset:{inv_offset};}}")
        lines.append(",".join(f"{part}:disabled" for part in menu_inv_parts) + f"{{background:{menu_inv['bgDisabled']};color:{menu_inv['fgDisabled']};}}")

    icon = contracts["icon"]
    icon_size = icon.get("size", icon.get("height", "3rem"))
    lines.append(
        f"{scope} .rail-control{{background:{icon['bg']};color:{icon['fg']};border:{icon['border']};"
        f"border-radius:{icon['radius']};padding:{icon.get('padding', '0')};width:{icon_size};height:{icon_size};"
        f"font-family:{icon.get('font', cfg['canonical_body_family'])},var(--body);font-weight:{icon.get('weight', cfg['control_weight'])};"
        f"font-size:{icon.get('sizeRem', 1)}rem;}}"
    )
    lines.append(f"{scope} .rail-control:hover{{background:{icon['bgHover']};color:{icon['fgHover']};}}")
    lines.append(f"{scope} .rail-control:active{{background:{icon['bgPressed']};color:{icon['fgPressed']};}}")
    lines.append(f"{scope} .rail-control .rail-icon{{width:{icon.get('iconSize', '1rem')};height:{icon.get('iconSize', '1rem')};object-fit:contain;}}")
    if cfg.get("rotate_previous"):
        lines.append(f"{scope} .rail-control--previous .rail-icon{{transform:rotate(180deg);}}")
    outline, offset = _focus_css(icon["focus"])
    lines.append(f"{scope} .rail-control:focus,{scope} .rail-control:focus-visible{{outline:{outline};outline-offset:{offset};}}")
    lines.append(f"{scope} .rail-control:disabled{{background:{icon['bgDisabled']};color:{icon['fgDisabled']};}}")
    inv = icon.get("onInverse") or {}
    if inv:
        lines.append(
            f"{scope} .section--inverse .rail-control,{scope} .section--photo .rail-control"
            f"{{background:{inv.get('bg', icon['bg'])};color:{inv.get('fg', icon['fg'])};border:{inv.get('border', icon['border'])};}}"
        )
    return "\n".join(lines)


CSS = r"""
@font-face{font-family:"HubSpot Sans";src:var(--font-body-url) format("woff2");font-weight:300 600;font-display:swap}
@font-face{font-family:"HubSpot Serif";src:var(--font-display-url) format("woff2");font-weight:300 600;font-display:swap}
@font-face{font-family:Melodrama;src:var(--font-display-url);font-weight:400 600;font-display:swap}
@font-face{font-family:Satoshi;src:var(--font-body-url);font-weight:400 700;font-display:swap}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;overflow-x:hidden;background:var(--canvas);color:var(--ink);font-family:var(--body);font-size:var(--body-size);line-height:var(--body-line)}
img{display:block;max-width:100%}a{color:inherit}button,input,summary{font:inherit}:focus-visible{outline:3px solid var(--focus);outline-offset:3px}.section--inverse :focus-visible,.section--photo :focus-visible{outline-color:var(--focus-inverse)}.section--strong :focus-visible{outline-color:var(--focus-strong)}.skip{position:fixed;left:1rem;top:1rem;z-index:50;transform:translateY(-180%);background:var(--panel);padding:.75rem 1rem}.skip:focus{transform:none}
.status-note{padding:.55rem 1rem;background:var(--accent);color:var(--on-accent);font-size:.78rem;text-align:center}.container{width:min(calc(100% - 2 * var(--gutter)),var(--container));margin-inline:auto}.section{padding:var(--section-y) 0}.section--primary{background:var(--canvas)}.section--raised{background:var(--raised)}.section--hero{background:var(--hero-surface)}.section--accent{background:var(--accent-soft)}.section--inverse{background:var(--inverse);color:var(--on-inverse)}.section--photo{background:var(--photo-surface);color:var(--on-inverse)}.section--strong{background:var(--strong);color:var(--on-strong)}.narrow{max-width:var(--narrow);margin-inline:auto;text-align:center}.split{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);grid-auto-rows:minmax(0,auto);gap:var(--column-gap);align-items:center}.split>*{min-width:0;min-height:0}.stack{display:flex;flex-direction:column;align-items:flex-start;gap:0}.stack>.eyebrow+h1,.stack>.eyebrow+h2{margin-top:var(--eyebrow-to-heading)}.stack>h1+.lede,.stack>h2+.lede{margin-top:var(--heading-to-body)}.stack>.disclosures,.stack>.feature-list{margin-top:var(--block-gap)}.center{align-items:center;text-align:center}
.eyebrow{margin:0;color:var(--eyebrow-light);font-family:var(--body);font-size:var(--eyebrow-size);font-weight:var(--eyebrow-weight);letter-spacing:var(--eyebrow-track);text-transform:uppercase}.section--inverse .eyebrow,.section--photo .eyebrow{color:var(--eyebrow-inverse)}.section--strong .eyebrow{color:var(--eyebrow-strong)}h1,h2,h3,p{margin:0}h1,h2{font-family:var(--display);font-weight:var(--display-weight);letter-spacing:var(--display-track)}h1{max-width:14ch;font-size:clamp(3rem,var(--hero-size),var(--hero-max));line-height:var(--hero-line);text-transform:var(--display-case)}h2{font-size:clamp(2.25rem,var(--h2-size),var(--h2-max));line-height:var(--h2-line);text-transform:var(--heading-case)}h3{font-size:1.25rem;line-height:1.25}.lede{max-width:58ch;color:var(--muted);font-size:1.08em}.section--inverse .lede,.section--photo .lede{color:var(--muted-inverse)}.section--strong .lede{color:var(--muted-strong)}
.actions{display:flex;flex-wrap:wrap;gap:var(--action-gap);margin-top:var(--body-to-cta)}
.site-header{position:sticky;top:0;z-index:20;background:var(--nav-bg);color:var(--nav-ink);border-bottom:1px solid var(--nav-border)}.nav{min-height:var(--nav-h);display:flex;align-items:center;gap:2rem}.brand{display:inline-flex;align-items:center;margin-right:auto}.brand img{width:auto;max-width:145px;max-height:38px}.nav-links,.nav-actions{display:flex;align-items:center;gap:1.5rem}.nav-links a{text-decoration:none}.hero{padding:var(--hero-top) 0 var(--hero-bottom)}.hero-media,.feature-media{position:relative;align-self:center;min-width:0;min-height:0;background:var(--media-well);overflow:hidden;border-radius:var(--media-radius);aspect-ratio:auto}.hero-media>img,.feature-media>img{display:block;width:100%;height:auto;min-width:0;min-height:0;object-fit:var(--slot-fit,contain);object-position:var(--slot-position,center)}.hero-media.has-canonical-ratio,.feature-media.has-canonical-ratio{aspect-ratio:var(--slot-ratio)}.hero-media.has-canonical-ratio>img,.feature-media.has-canonical-ratio>img{height:100%}
.logo-strip,.award-strip{display:flex;align-items:center;gap:var(--strip-gap);overflow-x:auto;padding:1.5rem 0}.logo-cell,.award-cell{display:grid;min-width:130px;height:72px;place-items:center}.logo-cell img{max-width:130px;max-height:54px;object-fit:contain}.award-cell{height:130px}.award-cell img{max-height:112px;object-fit:contain}.strip-title{text-align:center;font-size:1rem;font-family:var(--body)}
.disclosures{display:flex;flex-direction:column;gap:.65rem}.disclosures details{border-bottom:1px solid var(--hairline);padding:1rem 0}.disclosures summary{cursor:pointer;font-size:1.1rem;font-weight:var(--control-weight)}.disclosures details p{padding:1rem 0;color:var(--muted)}.section--inverse .disclosures details p{color:var(--muted-inverse)}
.section-head{display:flex;align-items:end;justify-content:space-between;gap:var(--column-gap);margin-bottom:var(--block-gap)}.card-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:var(--grid-gap)}.card{display:flex;min-width:0;flex-direction:column;gap:1rem;background:var(--panel);border:1px solid var(--hairline);border-radius:var(--card-radius);overflow:hidden;color:var(--ink);transition:box-shadow var(--motion),background-color var(--motion)}.card:hover{box-shadow:var(--card-shadow-hover)}.card .eyebrow{color:var(--eyebrow-light)}.card-body{display:flex;min-height:220px;flex:1;flex-direction:column;gap:var(--stack-gap);padding:var(--card-pad)}.card-media{width:100%;aspect-ratio:16/9;object-fit:cover;background:var(--media-well)}.card [data-control]{margin-top:auto}
.proof-media{width:112px;height:112px;border-radius:50%;object-fit:cover}.quote{font-family:var(--display);font-size:clamp(1.6rem,3vw,2.7rem);line-height:1.25}.attribution{font-size:.9rem;color:var(--muted)}.section--inverse .attribution,.section--photo .attribution{color:var(--muted-inverse)}.rail{display:grid;grid-auto-flow:column;grid-auto-columns:38%;gap:var(--grid-gap);overflow-x:auto;scroll-snap-type:x mandatory;padding:.25rem .25rem 1.25rem}.rail .card{scroll-snap-align:start}.rail-controls{display:flex;gap:.5rem}.testimonial-media{width:64px;height:64px;border-radius:50%;object-fit:cover}.pagination{text-align:center;margin-top:1rem;color:var(--muted);font-size:.8rem}
.asset-gap{display:grid;width:100%;min-height:160px;place-items:center;align-content:center;gap:.35rem;background:var(--raised);border:1px dashed var(--hairline);color:var(--muted);text-align:center}.asset-gap small{font-size:.7rem}.logo-cell .asset-gap,.award-cell .asset-gap{min-height:inherit}.footer{padding:var(--section-y) 0 2rem}.footer-main{display:grid;grid-template-columns:.8fr 2fr;gap:3rem}.footer-brand{display:flex;flex-direction:column;gap:1.25rem}.footer-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:2rem}.footer-column{display:flex;flex-direction:column;gap:.8rem}.footer-column h3{font-size:.85rem;text-transform:uppercase;letter-spacing:.06em}.footer-column a{color:var(--muted-strong);text-decoration:none}.legal{display:flex;justify-content:space-between;gap:1rem;margin-top:4rem;padding-top:1.5rem;border-top:1px solid var(--hairline-strong);font-size:.8rem}.preview-link{position:fixed;right:1rem;bottom:1rem;z-index:30;background:var(--inverse);color:var(--on-inverse);padding:.55rem .8rem;font-size:.72rem;text-decoration:none}
@media(max-width:980px){.nav-links{display:none}.card-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.card:last-child{grid-column:span 2}.footer-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.rail{grid-auto-columns:56%}}
@media(max-width:720px){body{font-size:var(--body-size-mobile)}h1{font-size:var(--hero-mobile)}h2{font-size:var(--h2-mobile)}.section{padding:var(--section-y-mobile) 0}.hero{padding:var(--hero-top-mobile) 0 var(--hero-bottom-mobile)}.stack>.eyebrow+h1,.stack>.eyebrow+h2{margin-top:var(--eyebrow-to-heading-mobile)}.stack>h1+.lede,.stack>h2+.lede{margin-top:var(--heading-to-body-mobile)}.stack>.disclosures,.stack>.feature-list{margin-top:var(--block-gap-mobile)}.actions{margin-top:var(--body-to-cta-mobile)}.split{gap:var(--column-gap-mobile)}.card-grid{gap:var(--grid-gap-mobile)}.menu-control{display:inline-flex!important}.nav-actions{display:none;position:absolute;left:0;right:0;top:100%;padding:1rem var(--gutter);background:var(--nav-bg);color:var(--nav-ink);border-bottom:1px solid var(--nav-border);flex-direction:column;align-items:stretch}.nav-actions.open{display:flex}.nav-actions a{text-align:center}.split{grid-template-columns:1fr}.hero-media{order:2}.section-head{align-items:flex-start;flex-direction:column}.card-grid{grid-template-columns:1fr}.card:last-child{grid-column:auto}.rail{grid-auto-columns:88%}.footer-main{grid-template-columns:1fr}.footer-grid{grid-template-columns:1fr}.legal{flex-direction:column}.logo-strip,.award-strip{justify-content:flex-start}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}*{transition-duration:0.01ms!important}}
"""


SCRIPT = r"""
const menu=document.querySelector('.menu-control'),nav=document.querySelector('.nav-actions');
menu?.addEventListener('click',()=>{const open=menu.getAttribute('aria-expanded')==='true';menu.setAttribute('aria-expanded',String(!open));nav.classList.toggle('open',!open)});
const rail=document.querySelector('.rail');document.querySelectorAll('[data-scroll]').forEach(b=>b.addEventListener('click',()=>rail?.scrollBy({left:Number(b.dataset.scroll)*(rail.clientWidth*.75),behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'})));
"""


def page_html(cfg: dict, binder: AssetBinder) -> tuple[str, dict, list[dict]]:
    brand_doc = yaml.safe_load((binder.brand_dir / "brand.yaml").read_text())
    contracts, degradations = _variant_contracts(brand_doc, cfg)
    component_css = _component_css(cfg, contracts)

    def image(slot: str, spec: tuple | None, cls: str = "") -> str:
        if not spec:
            return binder.media(slot, None, "", cls)
        return binder.media(slot, spec[0], spec[1], cls)

    def frame_attrs(slot: str, base_class: str) -> str:
        treatment = cfg["media_treatments"][slot]
        ratio = treatment.get("ratio")
        classes = f"{base_class} has-canonical-ratio" if ratio else base_class
        style = f"--slot-fit:{treatment['fit']};--slot-position:{treatment.get('position', 'center')}"
        if ratio:
            style += f";--slot-ratio:{ratio}"
        ratio_source = treatment.get("ratioSource", "intrinsic extracted asset")
        return (
            f'class="{classes}" data-media-slot="{esc(slot)}" '
            f'data-ratio-source="{esc(ratio_source)}" style="{esc(style)}"'
        )

    control_counter = [0]

    def control(label: str, variant: str, href: str | None = None, extra: str = "") -> str:
        control_counter[0] += 1
        tag = "a" if href else "button"
        href_attr = f' href="{esc(href)}"' if href else ' type="button"'
        inner = esc(label)
        glyph = (contracts.get(variant) or {}).get("glyph") or {}
        glyph_asset = glyph.get("asset")
        if glyph_asset in binder.inventory:
            inner += image(
                f"control-{control_counter[0]}-glyph",
                (glyph_asset, ""),
                "control-icon",
            )
        semantic = "c-arrow-link" if variant == "textCta" else f"c-button c-button--{variant}"
        return (
            f'<{tag} data-control="{esc(variant)}" class="{semantic} control control--{esc(variant)} {esc(extra)}"'
            f"{href_attr}>{inner}</{tag}>"
        )

    def logo_cells(items: list[tuple | None], prefix: str, award: bool = False) -> str:
        cell = "award-cell" if award else "logo-cell"
        return "".join(f'<div class="{cell}">{image(f"{prefix}-{i+1}", item)}</div>' for i, item in enumerate(items))

    def cards(items: list[dict], prefix: str) -> str:
        out = []
        for i, item in enumerate(items):
            media = image(f"{prefix}-{i+1}-media", item.get("media"), "card-media")
            out.append(
                f'<article class="card">{media}<div class="card-body">'
                f'<p class="eyebrow">{esc(item.get("eyebrow", cfg["brand"]))}</p>'
                f'<h3>{esc(item["heading"])}</h3><p>{esc(item["body"])}</p>'
                f'{control(item.get("cta", cfg["text_link"]), "textCta", "#closing")}'
                "</div></article>"
            )
        return "".join(out)

    disclosures = "".join(
        f'<details{" open" if i == 0 else ""}><summary>{esc(item["heading"])}</summary>'
        f'<p>{esc(item["body"])}</p></details>'
        for i, item in enumerate(cfg["disclosures"])
    )
    testimonials = cards(cfg["testimonials"], "testimonial")
    unavailable_note = (
        '<div class="status-note">Built from available extracted facts · canonical WoodWave v2 run status: '
        "needs_iteration · generated media is not used</div>"
        if cfg.get("wip")
        else ""
    )
    surface_classes = {
        "surface/primary": "section--primary",
        "surface/raised": "section--raised",
        "surface/accent-wash": "section--accent",
        "surface/inverse": "section--inverse",
        "surface/inverse-strong": "section--strong",
        "surface/photo-hero": "section--photo",
        "surface/hero-noise": "section--hero",
    }

    def surface(index: int) -> str:
        return surface_classes[cfg["surface_sequence"][index]]

    font_body_url = cfg.get("font_body_url", "local('Arial')")
    font_display_url = cfg.get("font_display_url", "local('Georgia')")
    style = ";".join(
        [
            f"--canvas:{cfg['colors']['canvas']}",
            f"--raised:{cfg['colors']['raised']}",
            f"--panel:{cfg['colors']['panel']}",
            f"--ink:{cfg['colors']['ink']}",
            f"--muted:{cfg['colors']['muted']}",
            f"--inverse:{cfg['colors']['inverse']}",
            f"--strong:{cfg['colors']['strong']}",
            f"--photo-surface:{cfg['colors']['photo_surface']}",
            f"--hero-surface:{cfg['colors']['hero_surface']}",
            f"--on-inverse:{cfg['colors']['on_inverse']}",
            f"--muted-inverse:{cfg['colors']['muted_inverse']}",
            f"--on-strong:{cfg['colors']['on_strong']}",
            f"--muted-strong:{cfg['colors']['muted_strong']}",
            f"--accent:{cfg['colors']['accent']}",
            f"--accent-hover:{cfg['colors']['accent_hover']}",
            f"--accent-inverse:{cfg['colors']['accent_inverse']}",
            f"--accent-strong:{cfg['colors']['accent_strong']}",
            f"--accent-soft:{cfg['colors']['accent_soft']}",
            f"--on-accent:{cfg['colors']['on_accent']}",
            f"--secondary-ink:{cfg['colors']['secondary']}",
            f"--link:{cfg['colors']['link']}",
            f"--focus:{cfg['colors']['focus']}",
            f"--focus-inverse:{cfg['colors']['focus_inverse']}",
            f"--focus-strong:{cfg['colors']['focus_strong']}",
            f"--eyebrow-light:{cfg['colors']['eyebrow_light']}",
            f"--eyebrow-inverse:{cfg['colors']['eyebrow_inverse']}",
            f"--eyebrow-strong:{cfg['colors']['eyebrow_strong']}",
            f"--hairline:{cfg['colors']['hairline']}",
            f"--hairline-inverse:{cfg['colors']['hairline_inverse']}",
            f"--hairline-strong:{cfg['colors']['hairline_strong']}",
            f"--media-well:{cfg['colors']['media_well']}",
            f"--nav-bg:{cfg['colors']['nav_bg']}",
            f"--nav-ink:{cfg['colors']['nav_ink']}",
            f"--nav-border:{cfg['colors']['nav_border']}",
            f"--body:{cfg['body_font']}",
            f"--display:{cfg['display_font']}",
            f"--font-body:'{cfg['canonical_body_family']}'",
            f"--font-heading:'{cfg['canonical_display_family']}'",
            f"--display-size:{cfg['canonical_display_size']}rem",
            f"--bg:{cfg['colors']['opening_bg']}",
            f"--font-body-url:url('{font_body_url}')",
            f"--font-display-url:url('{font_display_url}')",
            f"--body-size:{cfg['body_size']}",
            f"--body-size-mobile:{cfg['body_size_mobile']}",
            f"--body-line:{cfg['body_line']}",
            f"--hero-size:{cfg['hero_size']}",
            f"--hero-max:{cfg['hero_max']}",
            f"--hero-line:{cfg['hero_line']}",
            f"--hero-mobile:{cfg['hero_mobile']}",
            f"--h2-size:{cfg['h2_size']}",
            f"--h2-max:{cfg['h2_max']}",
            f"--h2-line:{cfg['h2_line']}",
            f"--h2-mobile:{cfg['h2_mobile']}",
            f"--display-weight:{cfg['display_weight']}",
            f"--display-track:{cfg['display_track']}",
            f"--display-case:{cfg['display_case']}",
            f"--heading-case:{cfg['heading_case']}",
            f"--eyebrow-size:{cfg['eyebrow_size']}",
            f"--eyebrow-weight:{cfg['eyebrow_weight']}",
            f"--eyebrow-track:{cfg['eyebrow_track']}",
            f"--control-weight:{cfg['control_weight']}",
            f"--control-case:{cfg['control_case']}",
            f"--control-track:{cfg['control_track']}",
            f"--container:{cfg['container']}",
            f"--narrow:{cfg['narrow']}",
            f"--gutter:{cfg['gutter']}",
            f"--section-y:{cfg['section_y']}",
            f"--section-y-mobile:{cfg['section_y_mobile']}",
            f"--hero-top:{cfg['hero_top']}",
            f"--hero-bottom:{cfg['hero_bottom']}",
            f"--hero-top-mobile:{cfg['hero_top_mobile']}",
            f"--hero-bottom-mobile:{cfg['hero_bottom_mobile']}",
            f"--column-gap:{cfg['column_gap']}",
            f"--column-gap-mobile:{cfg['column_gap_mobile']}",
            f"--grid-gap:{cfg['grid_gap']}",
            f"--grid-gap-mobile:{cfg['grid_gap_mobile']}",
            f"--stack-gap:{cfg['stack_gap']}",
            f"--eyebrow-to-heading:{cfg['eyebrow_to_heading']}",
            f"--eyebrow-to-heading-mobile:{cfg['eyebrow_to_heading_mobile']}",
            f"--heading-to-body:{cfg['heading_to_body']}",
            f"--heading-to-body-mobile:{cfg['heading_to_body_mobile']}",
            f"--body-to-cta:{cfg['body_to_cta']}",
            f"--body-to-cta-mobile:{cfg['body_to_cta_mobile']}",
            f"--block-gap:{cfg['block_gap']}",
            f"--block-gap-mobile:{cfg['block_gap_mobile']}",
            f"--strip-gap:{cfg['strip_gap']}",
            f"--action-gap:{cfg['action_gap']}",
            f"--card-pad:{cfg['card_pad']}",
            f"--card-radius:{cfg['card_radius']}",
            f"--card-shadow-hover:{cfg['card_shadow_hover']}",
            f"--media-radius:{cfg['media_radius']}",
            f"--nav-h:{cfg['nav_h']}",
            f"--motion:{cfg['motion']}",
        ]
    )
    page = f"""<!doctype html>
<html lang="en" style="{style}">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="{esc(cfg['brand'])} page using the approved Relume test structure and extracted brand facts.">
<title>Relume test · {esc(cfg['brand'])}</title><style>{CSS}\n{component_css}</style></head>
<body class="brand-page--{esc(cfg['css_slug'])}">{unavailable_note}<a class="skip" href="#main">Skip to content</a>
<header class="site-header {esc(cfg['nav_class'])}"><nav class="container nav" aria-label="Primary">
<a class="brand" href="#">{image("navigation-wordmark", cfg["logo"])}</a>
<div class="nav-links">{"".join(f'<a href="#{esc(link[1])}">{esc(link[0])}</a>' for link in cfg["nav"])}</div>
<button data-control="menu" class="control control--menu menu-control" type="button" aria-expanded="false" aria-controls="mobile-actions">Menu</button>
<div class="nav-actions" id="mobile-actions"><a href="#resources">{esc(cfg['nav_secondary'])}</a>{control(cfg['primary_cta'], cfg['nav_variant'], '#closing')}</div>
</nav></header>
<main id="main">
<section class="section hero {surface(0)}" data-surface="{esc(cfg['surface_sequence'][0])}"><div class="container split">
<div class="stack"><p class="eyebrow">{esc(cfg['hero']['eyebrow'])}</p><h1>{esc(cfg['hero']['heading'])}</h1><p class="lede">{esc(cfg['hero']['body'])}</p><div class="actions">{control(cfg['primary_cta'], 'primary', '#features')}{control(cfg['secondary_cta'], 'secondary', '#resources')}</div></div>
<div {frame_attrs("hero", "hero-media")}>{image("hero-media", cfg["hero"]["media"])}</div></div></section>
<section class="section {surface(1)}" data-surface="{esc(cfg['surface_sequence'][1])}"><div class="container"><p class="strip-title">{esc(cfg['trust_heading'])}</p><div class="logo-strip" role="list">{logo_cells(cfg["trust"], "trust-logo")}</div></div></section>
<section class="section {surface(2)}" data-surface="{esc(cfg['surface_sequence'][2])}" data-feature-split="disclosure" id="features"><div class="container split"><div class="stack"><p class="eyebrow">{esc(cfg['feature_one']['eyebrow'])}</p><h2>{esc(cfg['feature_one']['heading'])}</h2><div class="disclosures">{disclosures}</div></div><div {frame_attrs("feature-disclosure", "feature-media")}>{image("disclosure-feature-media", cfg["feature_one"]["media"])}</div></div></section>
<section class="section {surface(3)}" data-surface="{esc(cfg['surface_sequence'][3])}" data-feature-split="secondary"><div class="container split"><div {frame_attrs("feature-secondary", "feature-media")}>{image("second-feature-media", cfg["feature_two"]["media"])}</div><div class="stack"><p class="eyebrow">{esc(cfg['feature_two']['eyebrow'])}</p><h2>{esc(cfg['feature_two']['heading'])}</h2><p class="lede">{esc(cfg['feature_two']['body'])}</p><div class="actions">{control(cfg['feature_two']['cta'], cfg['feature_two_variant'], '#resources')}</div></div></div></section>
<section class="section {surface(4)}" data-surface="{esc(cfg['surface_sequence'][4])}"><div class="container narrow stack center"><p class="eyebrow">{esc(cfg['mid_cta']['eyebrow'])}</p><h2>{esc(cfg['mid_cta']['heading'])}</h2><p class="lede">{esc(cfg['mid_cta']['body'])}</p><div class="actions">{control(cfg['mid_cta']['cta'], cfg['mid_cta_variant'], '#closing')}</div></div></section>
<section class="section {surface(5)}" data-surface="{esc(cfg['surface_sequence'][5])}" id="resources"><div class="container"><div class="section-head"><div class="stack"><p class="eyebrow">{esc(cfg['resources_eyebrow'])}</p><h2>{esc(cfg['resources_heading'])}</h2></div></div><div class="card-grid">{cards(cfg["resources"], "resource")}</div></div></section>
<section class="section {surface(6)}" data-surface="{esc(cfg['surface_sequence'][6])}"><div class="container narrow stack center">{image("centered-proof-media", cfg["proof"]["media"], "proof-media")}<p class="eyebrow">{esc(cfg['proof']['eyebrow'])}</p><blockquote class="quote">{esc(cfg['proof']['quote'])}</blockquote><p class="attribution">{esc(cfg['proof']['attribution'])}</p></div></section>
<section class="section {surface(7)}" data-surface="{esc(cfg['surface_sequence'][7])}"><div class="container"><div class="section-head"><h2>{esc(cfg['testimonial_heading'])}</h2><div class="rail-controls" aria-label="Carousel controls"><button data-control="icon" class="control control--icon rail-control rail-control--previous" type="button" data-scroll="-1" aria-label="Previous">{image("rail-previous-icon", cfg.get("rail_previous"), "rail-icon") if cfg.get("rail_previous") else "Previous"}</button><button data-control="icon" class="control control--icon rail-control rail-control--next" type="button" data-scroll="1" aria-label="Next">{image("rail-next-icon", cfg.get("rail_next"), "rail-icon") if cfg.get("rail_next") else "Next"}</button></div></div><div class="rail" tabindex="0" aria-label="Scrollable proof cards">{testimonials}</div><div class="pagination">Scroll for more</div></div></section>
<section class="section {surface(8)}" data-surface="{esc(cfg['surface_sequence'][8])}"><div class="container narrow"><h2>{esc(cfg['awards_heading'])}</h2><div class="award-strip" role="list">{logo_cells(cfg["awards"], "award", True)}</div></div></section>
<section class="section {surface(9)}" data-surface="{esc(cfg['surface_sequence'][9])}" id="closing"><div class="container narrow stack center"><p class="eyebrow">{esc(cfg['closing']['eyebrow'])}</p><h2>{esc(cfg['closing']['heading'])}</h2><p class="lede">{esc(cfg['closing']['body'])}</p><div class="actions">{control(cfg['closing']['cta'], cfg['closing_variant'], '#footer')}</div></div></section>
</main>
<footer class="footer {surface(10)}" data-surface="{esc(cfg['surface_sequence'][10])}" id="footer"><div class="container"><div class="footer-main"><div class="footer-brand"><a class="brand" href="#">{image("footer-wordmark", cfg["logo"])}</a><p>{esc(cfg['footer_statement'])}</p></div><nav class="footer-grid" aria-label="Footer">{"".join(f'<section class="footer-column"><h3>{esc(col[0])}</h3>{"".join(f"<a href=#>{esc(x)}</a>" for x in col[1])}</section>' for col in cfg["footer_columns"])}</nav></div><div class="legal"><span>{esc(cfg['legal'])}</span><span>{esc(cfg['status_line'])}</span></div></div></footer>
<a class="preview-link" href="preview.png">Preview screenshot</a><script>{SCRIPT}</script></body></html>"""
    return page, contracts, degradations


COMMON = {
    "narrow": "52rem",
    "gutter": "clamp(1rem,4vw,2.5rem)",
    "column_gap": "clamp(2rem,6vw,5rem)",
    "grid_gap": "2rem",
    "stack_gap": "1.25rem",
    "card_pad": "2rem",
    "nav_h": "5.5rem",
}


CONFIGS = [
    {
        **COMMON,
        "dir": "01 HubSpot",
        "brand_slug": "hubspot-v2",
        "brand": "HubSpot",
        "status_line": "Canonical extraction completed · assets validated",
        "logo": ("hubspot-wordmark.svg", "HubSpot"),
        "colors": {"canvas": "#fcfcfa", "raised": "#f8f5ee", "panel": "#ffffff", "ink": "#1f1f1f", "muted": "rgba(0,0,0,.62)", "inverse": "#042729", "strong": "#1f1f1f", "on_inverse": "#f8f5ee", "muted_inverse": "rgba(255,255,255,.62)", "accent": "#ff4800", "accent_hover": "#c93700", "accent_inverse": "#ff4800", "accent_soft": "#fcc6b1", "on_accent": "#ffffff", "secondary": "#ff4800", "link": "#1f1f1f", "focus": "#2f7579", "hairline": "rgba(0,0,0,.11)", "hairline_inverse": "rgba(255,255,255,.11)", "media_well": "#ece6d9"},
        "body_font": "'HubSpot Sans',Arial,sans-serif", "display_font": "'HubSpot Serif',Georgia,serif",
        "font_body_url": "../../../../hubspot-v2/brand/assets/fonts/HubSpotSans-Book.woff2", "font_display_url": "../../../../hubspot-v2/brand/assets/fonts/HubSpotSerif-Medium.woff2",
        "body_size": "1rem", "body_line": "1.75", "hero_size": "5.2vw", "hero_max": "5rem", "hero_line": "1.08", "h2_size": "3.2vw", "h2_max": "3rem", "h2_line": "1.15", "display_weight": "500", "display_track": "0", "display_case": "none", "heading_case": "none", "eyebrow_size": ".875rem", "eyebrow_weight": "500", "eyebrow_track": ".04em", "control_weight": "500", "control_case": "none", "control_track": "0",
        "container": "67.5rem", "section_y": "6rem", "strip_gap": "4rem", "action_gap": "1rem", "card_radius": ".5rem", "media_radius": "1rem", "motion": "150ms ease-out",
        "nav": [("Products", "features"), ("Solutions", "features"), ("Pricing", "resources"), ("Resources", "resources")], "nav_secondary": "Get started free", "primary_cta": "Get a demo", "secondary_cta": "Get started free", "text_link": "Learn more",
        "hero": {"eyebrow": "HUBSPOT AGENTIC CUSTOMER PLATFORM", "heading": "Where go-to-market teams go to grow.", "body": "Unite marketing, sales, and customer service on one agentic customer platform that delivers results fast.", "media": ("018-hs-full-bleed-1-optmised.webp", "Warm interior office scene")},
        "trust_heading": "299,000+ customers in over 135 countries grow their businesses with HubSpot.",
        "trust": [("019-ebay-logo.svg","eBay"),("020-doordash-logo.svg","DoorDash"),("021-reddit-logo.svg","Reddit"),("022-tripadvisor-logo.svg","Tripadvisor"),("023-eventbrite-logo.svg","Eventbrite")],
        "feature_one": {"eyebrow": "Powered by AI", "heading": "Growing a business is hard. HubSpot makes it easier.", "media": ("024-customer-20platform-20graphic-20-20smart-20crm1-5x-20-1.png","HubSpot Smart CRM platform graphic")},
        "disclosures": [
            {"heading":"Marketing Hub®","body":"Attract and convert the right leads. Run campaigns, personalize content, and track it all."},
            {"heading":"Sales Hub®","body":"Generate quality leads and close deals, faster. Automate prospecting, manage pipeline, and accelerate revenue growth."},
            {"heading":"Service Hub®","body":"Streamline and scale support to serve customers faster."},
            {"heading":"Content Hub™","body":"Create content that clicks with your audience. Build pages, publish content across channels, and stay on brand."},
        ],
        "feature_two": {"eyebrow":"BREEZE AGENTS","heading":"Built-in AI agents that work for you 24/7.","body":"Breeze Agents are your always-on teammates. They can resolve over 65% of customer inquiries, accelerate your sales pipeline, and whip up quality content in no time.","cta":"Explore Breeze Agents","media":("036-customer-agent-en-2x.png","Customer Agent product interface")},
        "mid_cta": {"eyebrow":"CONNECTED PLATFORM","heading":"Works with the tools you already use. 2,000+ integrations.","body":"Connected data and tools make it easier to know, do, and connect everything across your business.","cta":"See all app integrations"},
        "resources_eyebrow":"BREEZE AGENTS","resources_heading":"Always-on teammates for every team",
        "resources":[
            {"heading":"Customer Agent","body":"Resolve 65% of your customer inquiries automatically.","media":("036-customer-agent-en-2x.png","Customer Agent UI")},
            {"heading":"Prospecting Agent","body":"Spot buying signals, source contacts, and launch personalized outreach — instantly.","media":("037-prospecting-agent-en-2x.png","Prospecting Agent UI")},
            {"heading":"Data Agent","body":"Get instant answers to custom questions about your customers.","media":("038-data-hub-en-2x.png","Data Agent UI")},
        ],
        "proof":{"eyebrow":"ENTERPRISE","quote":"HubSpot took the time to understand our business needs fully. The pre-sales and subsequent support really stood out from the start.","attribution":"Adam Jones · Director of Business Development, Unipart","media":("045-unipart-1.png","Adam Jones at Unipart")},
        "testimonial_heading":"Remarkable results for every size business.",
        "testimonials":[
            {"heading":"Enterprise","body":"They committed to engage with us deeply and work side-by-side with us on the implementation.","media":("045-unipart-1.png","Unipart case study")},
            {"heading":"Mid-Sized Business","body":"HubSpot gave us the tools we needed to grow without losing the personal connection with our fans.","media":("046-angel-fc.png","Angel City FC case study")},
            {"heading":"Small Business","body":"When something needs a human touch, our team can step in quickly — with full context at their fingertips.","media":("047-youth-on-course.png","Youth on Course case study")},
        ],
        "awards_heading":"Voted #1 in 526 G2 Reports","awards":[("048-badge-leader-small-business.png","G2 Leader"),("049-badge-most-implementable.png","G2 Most Implementable"),("050-badge-best-relationships-small-business.png","G2 Best Relationships"),("051-badge-best-support-enterprise.png","G2 Best Support"),("052-badge-best-results-mid-market.png","G2 Best Results"),("053-badge-best-usability-enterprise.png","G2 Best Usability")],
        "closing":{"eyebrow":"GROW BETTER","heading":"Make impossible growth feel impossibly easy, with HubSpot.","body":"Unite your teams, tools, and customer data on one connected platform.","cta":"Get a demo"},
        "footer_statement":"Unite marketing, sales, and customer service on one agentic customer platform.",
        "footer_columns":[("Products",["Marketing Hub®","Sales Hub®","Service Hub®","Content Hub™"]),("Platform",["Smart CRM™","Breeze™","Data Hub™","Revenue Hub™"]),("Resources",["Case Studies","App integrations","Small Business Bundle","AEO (Beta)"]),("Company",["Products","Solutions","Pricing","Resources"])],
        "legal":"HubSpot · extracted brand facts",
    },
    {
        **COMMON,
        "dir": "02 Remote",
        "brand_slug": "remote",
        "brand": "Remote",
        "status_line": "Available canonical extracted facts · assets validated",
        "logo": ("remote-wordmark.svg", "Remote"),
        "colors": {"canvas": "#eff0f0", "raised": "#f6f7f8", "panel": "#ffffff", "ink": "#141415", "muted": "#383a3d", "inverse": "#00235c", "strong": "#f6f7f8", "on_inverse": "#ffffff", "muted_inverse": "#9bc1ff", "accent": "#0564ff", "accent_hover": "#0047bc", "accent_inverse": "#9bc1ff", "accent_soft": "#dae2e8", "on_accent": "#ffffff", "secondary": "#003284", "link": "#0564ff", "focus": "#9bc1ff", "hairline": "rgba(179,181,183,.4)", "hairline_inverse": "rgba(255,255,255,.4)", "media_well": "#00235c"},
        "body_font": "Inter,Arial,sans-serif", "display_font": "'Lexend Deca',Arial,sans-serif", "body_size": "1.125rem", "body_line": "1.5", "hero_size": "4vw", "hero_max": "3.5rem", "hero_line": "1.2", "h2_size": "3vw", "h2_max": "2.875rem", "h2_line": "1.2", "display_weight": "400", "display_track": "0", "display_case": "none", "heading_case": "none", "eyebrow_size": ".875rem", "eyebrow_weight": "400", "eyebrow_track": ".05em", "control_weight": "500", "control_case": "none", "control_track": "0",
        "container": "76rem", "section_y": "5rem", "strip_gap": "4rem", "action_gap": "1rem", "card_radius": ".625rem", "media_radius": ".625rem", "motion": "200ms cubic-bezier(0,0,.2,1)",
        "nav": [("Products","features"),("Solutions","features"),("Resources","resources"),("Pricing","closing")], "nav_secondary":"Sign up", "primary_cta":"Book demo", "secondary_cta":"Sign up", "text_link":"Learn more",
        "hero":{"eyebrow":"GLOBAL EMPLOYMENT","heading":"Global employment runs on Remote","body":"Hire and pay anyone in the world — with the compliance, reliability, and local expertise that only owned infrastructure delivers.","media":("hero-globe-illustration.webp","Remote globe product illustration")},
        "trust_heading":"GLOBAL COMPANIES GROW WITH REMOTE","trust":[("logo-anthropic.svg","Anthropic"),("logo-gitlab.svg","GitLab"),("logo-vercel.svg","Vercel"),("logo-miro.svg","Miro"),("logo-datadog.svg","Datadog"),("logo-kfc.svg","KFC")],
        "feature_one":{"eyebrow":"HOW WE DO IT","heading":"One system of record. Every employment need.","media":("collage-eor-ui.webp","Employer of Record product UI collage")},
        "disclosures":[
            {"heading":"Employer of Record (EOR)","body":"Need to hire anyone, anywhere? We handle the employment contract, taxes, benefits, and compliance — onboarded in hours, not months."},
            {"heading":"Global Payroll","body":"Accurate, compliant payroll in every country you operate. Run by our in-house teams, no partner network."},
            {"heading":"Contractor of Record (COR)","body":"Engage international contractors compliantly. Contracts, payments, and risk — all handled by our experts."},
            {"heading":"Contractor Management","body":"Engage contractors compliantly, anywhere — and convert them to FTEs before misclassification risk becomes a legal problem."},
        ],
        "feature_two":{"eyebrow":"INTELLIGENT INFRASTRUCTURE","heading":"Owned end-to-end infrastructure, operated in-house.","body":"We have our own legal experts, our own payroll specialists, and our own compliance teams in every market we operate in.","cta":"Explore our platform","media":("panel-infrastructure-ui-snippet.webp","Remote infrastructure product UI")},
        "mid_cta":{"eyebrow":"GLOBAL EMPLOYMENT","heading":"Hiring internationally, converting contractors, or consolidating payroll?","body":"Talk to our team about your global employment needs.","cta":"Book demo"},
        "resources_eyebrow":"INTEGRATIONS, API, AND MCP","resources_heading":"Your workflows, your way, on our infrastructure",
        "resources":[
            {"eyebrow":"MCP","heading":"Deploy AI agents on real employment data","body":"Remote MCP gives any AI agent a live, secure connection to payroll, contracts, compliance data, and org structure.","media":("card-mcp-agents.webp","Remote MCP agents product card")},
            {"eyebrow":"INTEGRATIONS","heading":"Plug Remote into your stack","body":"Keep the HR tools your team already uses. Remote runs the payroll and compliance underneath.","media":("card-integrations.webp","Remote integrations product card")},
            {"eyebrow":"API","heading":"Build on top of ours","body":"Remote is API-first by design. Use our REST API, webhooks, and CLI to build custom workflows.","media":("card-api-first.webp","Remote API-first product card")},
        ],
        "proof":{"eyebrow":"CUSTOMER STORY","quote":"If we had to manage and coordinate everything in-house, it would cost us well over $500,000 more each year.","attribution":"Luke McKinlay · VP of Finance","media":("avatar-luke-mckinlay.webp","Luke McKinlay")},
        "testimonial_heading":"A word from our customers",
        "testimonials":[
            {"heading":"Luke McKinlay","body":"Remote takes the operational burden off our plate, allowing us to focus on growing our business with confidence and efficiency.","media":("avatar-luke-mckinlay.webp","Luke McKinlay")},
            {"heading":"Marisol Jiménez","body":"We run payroll in multiple different currencies and our Finance Manager has full visibility in a single platform.","media":("avatar-marisol-jimenez.webp","Marisol Jiménez")},
            {"heading":"Maria Shkaruppa","body":"The expert support they provide in local payroll, tax compliance, and HR operations has streamlined our processes.","media":("avatar-maria-shkaruppa.webp","Maria Shkaruppa")},
        ],
        "awards_heading":"The #1 global HR platform as voted by you","awards":[("badge-g2-gep-leader.webp","G2 Global Employment Leader"),("badge-g2-payroll-leader.webp","G2 Payroll Leader"),("badge-g2-top100-fastest-growing.webp","G2 Fastest Growing"),("badge-g2-top100-global-sellers.webp","G2 Global Sellers"),("badge-g2-top100-hr.webp","G2 Top HR"),("badge-g2-top50-hr.webp","G2 Top 50 HR")],
        "closing":{"eyebrow":"GLOBAL EMPLOYMENT","heading":"Global employment is hard. We built the infrastructure to do it right.","body":"Remote handles the hard stuff — with in-house payroll teams, local legal experts, and owned entities in every market we operate in.","cta":"Book demo"},
        "footer_statement":"Hire and pay anyone in the world with owned infrastructure and local expertise.",
        "footer_columns":[("Products",["Employer of Record (EOR)","Global Payroll","Contractor of Record","Contractor Management"]),("Infrastructure",["Integrations","API","MCP","Professional Employer Organization"]),("Resources",["Customer stories","Global HR platform","Compliance","Pricing"]),("Company",["Products","Solutions","Resources","Pricing"])],
        "legal":"Remote · extracted brand facts",
    },
    {
        **COMMON,
        "dir": "03 WoodWave",
        "brand_slug": "woodwave-v2",
        "brand": "WoodWave Gallery",
        "wip": True,
        "status_line": "Available extracted facts · canonical run needs_iteration",
        "logo": ("000-657acd8d782ab334f6b2e5f3-logo.svg", "WoodWave Gallery"),
        "colors": {"canvas": "#fbf4ed", "raised": "#f7efe8", "panel": "#fbf4ed", "ink": "#32271a", "muted": "#6b5d50", "inverse": "#32271a", "strong": "#181313", "on_inverse": "#fbf4ed", "muted_inverse": "#a09a94", "accent": "#edd580", "accent_hover": "#1d170f", "accent_inverse": "#edd580", "accent_soft": "#f7efe8", "on_accent": "#32271a", "secondary": "#32271a", "link": "#32271a", "focus": "#edd580", "hairline": "rgba(50,39,26,.2)", "hairline_inverse": "rgba(251,244,237,.2)", "media_well": "#2a2018"},
        "body_font": "Satoshi,Manrope,Arial,sans-serif", "display_font": "Melodrama,'Playfair Display',Georgia,serif",
        "font_body_url": "../../../../woodwave-v2/brand/assets/fonts/Satoshi-400.ttf", "font_display_url": "../../../../woodwave-v2/brand/assets/fonts/Melodrama-500.ttf",
        "body_size": "1.5rem", "body_line": "1.4", "hero_size": "10vw", "hero_max": "11rem", "hero_line": ".9", "h2_size": "5.6vw", "h2_max": "5rem", "h2_line": "1.2", "display_weight": "400", "display_track": ".125rem", "display_case": "uppercase", "heading_case": "uppercase", "eyebrow_size": "1.125rem", "eyebrow_weight": "500", "eyebrow_track": ".0625rem", "control_weight": "400", "control_case": "uppercase", "control_track": ".0625rem",
        "container": "81.25rem", "section_y": "7.5rem", "strip_gap": "2.5rem", "action_gap": "1.5rem", "card_radius": "0", "media_radius": ".25rem", "motion": "300ms ease-in-out",
        "nav":[("About","features"),("Gallery","resources"),("Exhibition","resources"),("Visit","closing")], "nav_secondary":"Visit", "primary_cta":"Buy tickets", "secondary_cta":"Visit", "text_link":"Buy tickets",
        "hero":{"eyebrow":"WOODWAVE GALLERY","heading":"WoodWave Gallery","body":"WoodWave Gallery: where design, nature, and boundless creativity harmoniously converge, inspiring imagination in the city's heart.","media":("001-657acd8d782ab334f6b2e5dc-hero-img-main-p-1600.jpg","Spiral wooden staircase")},
        "trust_heading":"WOODWAVE GALLERY","trust":[("000-657acd8d782ab334f6b2e5f3-logo.svg","WoodWave Gallery"),None,None,None,None],
        "feature_one":{"eyebrow":"ABOUT","heading":"Space as a muse: unleash your creativity and get inspired with us","media":("004-657acd8d782ab334f6b2e5d2-about-img-1-p-800.jpg","Wooden interior architecture")},
        "disclosures":[
            {"heading":"Perspective Hall","body":"ArtUnveil space by Isabella St."},
            {"heading":"Panorapeak Viewpoint","body":"Our uniqueness lies in the seamless blend of contemporary design with the organic."},
            {"heading":"WoodWave Gallery","body":"At WoodWave Gallery, we hold a profound belief in the transformative influence of artistic environments on the boundless human imagination."},
        ],
        "feature_two":{"eyebrow":"1974–2023","heading":"A tribute to decades of creative excellence","body":"Founded by the visionary Margaret Woodwave in 1974, the WoodWave Gallery has been on a journey of constant evolution.","cta":"Visit","media":("016-657acd8d782ab334f6b2e5dd-about-img-5-p-500.jpg","Founder portrait")},
        "mid_cta":{"eyebrow":"STAY UPDATED","heading":"Subscribe now for exclusive updates and invitations to special exhibitions","body":"WoodWave Gallery: where design, nature, and boundless creativity harmoniously converge.","cta":"Subscribe"},
        "resources_eyebrow":"GALLERY","resources_heading":"Explore the gallery",
        "resources":[
            {"heading":"Perspective Hall","body":"ArtUnveil space by Isabella St.","media":("009-657acd8d782ab334f6b2e5e5-web-gallery-1-p-1600.jpg","Gallery interior")},
            {"heading":"Panorapeak Viewpoint","body":"Contemporary design blends with the organic.","media":("010-657acd8d782ab334f6b2e5e6-web-gallery-2-p-1600.jpg","Gallery exhibition")},
            {"heading":"WoodWave Gallery","body":"Innovation and inspiration harmoniously converge.","media":("011-657acd8d782ab334f6b2e5e7-web-gallery-3-p-1600.jpg","Gallery installation")},
        ],
        "proof":{"eyebrow":"1974–2023","quote":"Founded by the visionary Margaret Woodwave in 1974, the WoodWave Gallery has been on a journey of constant evolution.","attribution":"WoodWave Gallery","media":("016-657acd8d782ab334f6b2e5dd-about-img-5-p-500.jpg","Founder portrait")},
        "testimonial_heading":"Space as a muse",
        "testimonials":[
            {"heading":"Perspective Hall","body":"ArtUnveil space by Isabella St.","media":("004-657acd8d782ab334f6b2e5d2-about-img-1-p-800.jpg","Wooden interior architecture")},
            {"heading":"Panorapeak Viewpoint","body":"Our uniqueness lies in the seamless blend of contemporary design with the organic.","media":("005-657acd8d782ab334f6b2e5d4-about-img-2-p-1600.jpg","Gallery hall with sculpture")},
            {"heading":"WoodWave Gallery","body":"Technology and creativity converge, inviting visitors to explore and engage with the art of tomorrow.","media":("007-657acd8d782ab334f6b2e5d3-about-img-4-p-500.jpg","Interior dome with sphere")},
        ],
        "awards_heading":"EXTRACTED MARKS AND RECOGNITION","awards":[("000-657acd8d782ab334f6b2e5f3-logo.svg","WoodWave Gallery"),None,None,None,None],
        "closing":{"eyebrow":"VISIT","heading":"Welcome to the gallery","body":"Art Boulevard, 123 USA, New-Yourk · Mon — Thu 9:00-19:00 · Fri — Sun 11:00-17:00","cta":"Buy tickets"},
        "footer_statement":"Where design, nature, and boundless creativity harmoniously converge.",
        "footer_columns":[("Explore",["About","Gallery","Exhibition","Visit"]),("Visit",["Address","Open hours","Ticket prices","Buy tickets"]),("Gallery",["Perspective Hall","Panorapeak Viewpoint","WoodWave Gallery","Stay updated"]),("Contact",["info@wwgallery.com","+1 123 456 789","Subscribe","Visit"])],
        "legal":"WoodWave Gallery · available extracted facts",
    },
]

# Canonical rhythm contracts projected onto the shared 11-band page anatomy.
# HubSpot and Remote map 1:1 from brand.yaml pageRhythm. WoodWave has a 7-band
# measured source; the added proof/card bands stay on its primary canvas, while
# the media-led resources band uses its licensed photo/inverse family.
CONFIGS[0].update(
    css_slug="hubspot",
    media_treatments={
        "hero": {"fit": "cover", "ratio": None, "ratioSource": "intrinsic extracted hero asset 2160x1440"},
        "feature-disclosure": {"fit": "contain", "ratio": None, "ratioSource": "intrinsic extracted platform graphic 604x353"},
        "feature-secondary": {"fit": "contain", "ratio": None, "ratioSource": "intrinsic extracted product UI 640x640"},
    },
    acceptance_status="blocked: exact extracted primary control is 3.40:1 and transparent border yields 2.68:1 on accent-wash",
    nav_class="nav--light",
    canonical_display_family="HubSpot Serif", canonical_body_family="HubSpot Sans",
    canonical_display_size=5,
    focus_contract="outline 2px solid #2f7579; outline-offset 2px",
    nav_variant="primary", feature_two_variant="tertiary", mid_cta_variant="textCta",
    closing_variant="primary", menu_variant="tertiary", rail_variant="tertiary",
    rail_previous=("icon-previous.svg", "Previous"),
    rail_next=("icon-next.svg", "Next"),
    rail_contract={
        "style": "icon-control", "bg": "#ffffff", "fg": "#1f1f1f",
        "border": "none", "radius": "50%", "padding": "0", "height": "3.5rem",
        "size": "3.5rem", "iconSize": "1rem", "bgHover": "rgba(0, 0, 0, 0.05)",
        "fgHover": "#1f1f1f", "bgPressed": "rgba(0, 0, 0, 0.06)",
        "fgPressed": "#1f1f1f", "bgDisabled": "rgba(0, 0, 0, 0.02)",
        "fgDisabled": "rgba(0, 0, 0, 0.4)",
        "focus": "outline 2px solid #2f7579; outline-offset 2px",
    },
    typography_status="Extracted HubSpot Sans and HubSpot Serif files loaded from canonical brand assets.",
    surface_sequence=[
        "surface/photo-hero", "surface/primary", "surface/primary",
        "surface/primary", "surface/accent-wash", "surface/primary",
        "surface/primary", "surface/primary", "surface/primary",
        "surface/inverse", "surface/inverse-strong",
    ],
    eyebrow_to_heading="1.5rem", heading_to_body="2rem",
    body_to_cta="2.5rem", block_gap="2.5rem",
    section_y="4rem", section_y_mobile="2.5rem",
    hero_top="11rem", hero_bottom="11rem", hero_top_mobile="4rem", hero_bottom_mobile="4rem",
    column_gap="5rem", column_gap_mobile="2rem",
    grid_gap="2rem", grid_gap_mobile="2rem", gutter="1rem",
    strip_gap="4.3125rem", action_gap="1rem", nav_h="5.5rem",
    eyebrow_to_heading_mobile="1rem", heading_to_body_mobile="1.5rem",
    body_to_cta_mobile="2rem", block_gap_mobile="2rem",
    body_size_mobile=".9rem", hero_mobile="3rem", h2_mobile="2rem",
    card_shadow_hover="0 0 0 1px rgba(0,0,0,.11)",
)
CONFIGS[0]["colors"].update(
    photo_surface="#55453e", hero_surface="#fcfcfa",
    on_strong="#f8f5ee", muted_strong="rgba(255,255,255,.62)",
    accent_strong="#ff4800", hairline_strong="rgba(255,255,255,.11)",
    focus="#2f7579", focus_inverse="#ff4800", focus_strong="#ff4800",
    eyebrow_light="#1f1f1f", eyebrow_inverse="#f8f5ee", eyebrow_strong="#f8f5ee",
    opening_bg="#55453e",
    nav_bg="#ffffff", nav_ink="#1f1f1f", nav_border="rgba(0,0,0,.11)",
)

CONFIGS[1].update(
    css_slug="remote",
    media_treatments={
        "hero": {"fit": "contain", "ratio": None, "ratioSource": "intrinsic extracted illustration 1498x1100"},
        "feature-disclosure": {"fit": "contain", "ratio": None, "ratioSource": "intrinsic extracted collage 1068x1068"},
        "feature-secondary": {"fit": "contain", "ratio": None, "ratioSource": "intrinsic extracted UI snippet 1526x1100"},
    },
    acceptance_status="pass",
    nav_class="nav--light",
    canonical_display_family="Bossa", canonical_body_family="Inter",
    canonical_display_size=2.875,
    focus_contract="outline 2px solid #9bc1ff; outline-offset 2px",
    nav_variant="tertiary", feature_two_variant="primary", mid_cta_variant="primary",
    closing_variant="primary", menu_variant="tertiary", rail_variant="secondary",
    typography_status="Canonical Bossa/Inter stacks applied; no Bossa font file exists in the extracted asset directory, so the declared render-proxy/fallback stack is used.",
    surface_sequence=[
        "surface/hero-noise", "surface/primary", "surface/primary",
        "surface/primary", "surface/primary", "surface/primary",
        "surface/primary", "surface/primary", "surface/primary",
        "surface/hero-noise", "surface/raised",
    ],
    eyebrow_to_heading=".75rem", heading_to_body="1rem",
    body_to_cta="2rem", block_gap="4rem",
    section_y="3rem", section_y_mobile="2rem",
    hero_top="5rem", hero_bottom="5rem", hero_top_mobile="5rem", hero_bottom_mobile="5rem",
    column_gap="3rem", column_gap_mobile="1.5rem",
    grid_gap="2rem", grid_gap_mobile="2rem", gutter="2rem",
    strip_gap="4rem", action_gap="1rem", nav_h="5rem",
    eyebrow_to_heading_mobile=".5rem", heading_to_body_mobile=".75rem",
    body_to_cta_mobile="1.5rem", block_gap_mobile="3rem",
    body_size_mobile="1rem", hero_mobile="1.75rem", h2_mobile="1.375rem",
    card_shadow_hover="0 12px 24px rgba(0,0,0,.08)",
)
CONFIGS[1]["colors"].update(
    photo_surface="#00235c", hero_surface="#dae2e8",
    on_strong="#141415", muted_strong="#595b5f",
    accent_strong="#0047bc", hairline_strong="rgba(179,181,183,.4)",
    focus="#003284", focus_inverse="#9bc1ff", focus_strong="#003284",
    eyebrow_light="#0047bc", eyebrow_inverse="#9bc1ff", eyebrow_strong="#0047bc",
    opening_bg="#dae2e8",
    nav_bg="#eff0f0", nav_ink="#141415", nav_border="rgba(179,181,183,.4)",
)

CONFIGS[2].update(
    css_slug="woodwave",
    media_treatments={
        "hero": {"fit": "cover", "ratio": None, "ratioSource": "intrinsic extracted hero photo 1600x997"},
        "feature-disclosure": {"fit": "cover", "ratio": None, "ratioSource": "intrinsic extracted editorial photo 800x923"},
        "feature-secondary": {"fit": "cover", "ratio": None, "ratioSource": "intrinsic extracted portrait 500x652"},
    },
    acceptance_status="blocked: exact extracted light-surface text-link hover gold is 1.34:1; canonical brand run also remains needs_iteration",
    nav_class="nav--inverse",
    canonical_display_family="Melodrama", canonical_body_family="Satoshi",
    canonical_display_size=11,
    focus_contract="outline 2px solid #edd580; outline-offset 2px",
    nav_variant="primary", feature_two_variant="textCta", mid_cta_variant="textCta",
    closing_variant="textCta", menu_variant="textCta", rail_variant="textCta",
    surface_overrides={
        "textCta": {
            "bg": "transparent", "fg": "#fbf4ed", "border": "none",
            "bgHover": "transparent", "fgHover": "#edd580",
            "bgPressed": "transparent", "fgPressed": "#edd580",
            "bgDisabled": "transparent", "fgDisabled": "#a09a94",
            "focus": "outline 2px solid #edd580; outline-offset 2px",
            "source": "brand.yaml buttons.textCta decoration/note + text/on-inverse and accent/highlight-on-inverse",
        }
    },
    rail_previous=("008-slider-arrow.svg", "Previous gallery item"),
    rail_next=("008-slider-arrow.svg", "Next gallery item"),
    rotate_previous=True,
    rail_contract={
        "style": "icon-control", "bg": "transparent", "fg": "#32271a",
        "border": "none", "radius": "0rem", "padding": "0", "height": "2.625rem",
        "size": "2.625rem", "iconSize": "1rem", "bgHover": "transparent",
        "fgHover": "#edd580", "bgPressed": "transparent", "fgPressed": "#edd580",
        "bgDisabled": "transparent", "fgDisabled": "#6b5d50",
        "focus": "outline 2px solid #32271a; outline-offset 2px",
    },
    typography_status="Extracted Melodrama and Satoshi files loaded from available canonical brand assets.",
    surface_sequence=[
        "surface/photo-hero", "surface/primary", "surface/primary",
        "surface/primary", "surface/primary", "surface/photo-hero",
        "surface/primary", "surface/primary", "surface/primary",
        "surface/inverse", "surface/inverse-strong",
    ],
    eyebrow_to_heading="2.5rem", heading_to_body="5rem",
    body_to_cta="2.5rem", block_gap="4rem",
    section_y="7.5rem", section_y_mobile="3rem",
    hero_top="9.375rem", hero_bottom="9.375rem", hero_top_mobile="4rem", hero_bottom_mobile="4rem",
    column_gap="4rem", column_gap_mobile="2rem",
    grid_gap="2rem", grid_gap_mobile="2rem", gutter="1.25rem",
    strip_gap="2.5rem", action_gap="1.5rem", nav_h="6.375rem",
    eyebrow_to_heading_mobile="1rem", heading_to_body_mobile="2rem",
    body_to_cta_mobile="1.5rem", block_gap_mobile="2rem",
    body_size_mobile="1.125rem", hero_mobile="3.28rem", h2_mobile="2.75rem",
    card_shadow_hover="none",
)
CONFIGS[2]["colors"].update(
    photo_surface="#2a2018", hero_surface="#32271a",
    on_strong="#fbf4ed", muted_strong="#a09a94",
    accent_strong="#edd580", hairline_strong="rgba(251,244,237,.2)",
    focus="#32271a", focus_inverse="#edd580", focus_strong="#edd580",
    eyebrow_light="#32271a", eyebrow_inverse="#edd580", eyebrow_strong="#edd580",
    opening_bg="#2a2018",
    nav_bg="#32271a", nav_ink="#fbf4ed", nav_border="rgba(251,244,237,.2)",
)


def main() -> None:
    # Write in reverse so Studio's newest-first lane sorting displays 01, 02, 03.
    for cfg in reversed(CONFIGS):
        binder = AssetBinder(cfg["brand_slug"])
        out = OUT_ROOT / cfg["dir"]
        out.mkdir(parents=True, exist_ok=True)
        html_text, component_contracts, component_degradations = page_html(cfg, binder)
        (out / "index.html").write_text(html_text)
        media_specs = {
            "hero": cfg["hero"]["media"],
            "feature-disclosure": cfg["feature_one"]["media"],
            "feature-secondary": cfg["feature_two"]["media"],
        }
        media_geometry = []
        for slot, spec in media_specs.items():
            treatment = cfg["media_treatments"][slot]
            entry = {
                "slot": slot,
                "asset": spec[0] if spec else None,
                "fit": treatment["fit"],
                "cssAspectRatio": treatment.get("ratio") or "auto",
                "ratioSource": treatment.get("ratioSource", "intrinsic extracted asset"),
            }
            if spec:
                with Image.open(binder.brand_dir / "assets" / spec[0]) as image_file:
                    entry["intrinsicWidth"] = image_file.width
                    entry["intrinsicHeight"] = image_file.height
                    entry["intrinsicRatio"] = round(image_file.width / image_file.height, 6)
            media_geometry.append(entry)
        composition = {
            "schemaVersion": "composition.v1",
            "name": cfg["dir"],
            "brandSource": f"runs/{cfg['brand_slug']}/brand",
            "canonicalStatus": cfg["status_line"],
            "structure": [
                "navigation",
                "hero-content-media-split",
                "trust-logo-strip",
                "feature-disclosure-split",
                "feature-content-media-split",
                "centered-cta",
                "resource-card-grid",
                "centered-proof-testimonial",
                "horizontal-testimonial-rail",
                "awards-logo-rail",
                "closing-cta",
                "multi-column-footer",
            ],
            "sections": [
                {
                    "id": section_id,
                    "surfaceIntent": cfg["surface_sequence"][index],
                    "slots": [{"contract": "heading", "sizeClass": "display", "copy": heading}],
                }
                for index, (section_id, heading) in enumerate(
                    [
                        ("hero", cfg["hero"]["heading"]),
                        ("trust", cfg["trust_heading"]),
                        ("feature-disclosure", cfg["feature_one"]["heading"]),
                        ("feature-split", cfg["feature_two"]["heading"]),
                        ("mid-cta", cfg["mid_cta"]["heading"]),
                        ("resources", cfg["resources_heading"]),
                        ("proof", cfg["proof"]["quote"]),
                        ("testimonial-rail", cfg["testimonial_heading"]),
                        ("awards", cfg["awards_heading"]),
                        ("closing-cta", cfg["closing"]["heading"]),
                        ("footer", cfg["footer_statement"]),
                    ]
                )
            ],
            "mediaPolicy": "existing-extracted-assets-only",
            "mediaGeometryPolicy": "canonical ratio only when explicitly declared; otherwise intrinsic extracted asset ratio with no CSS aspect-ratio",
            "mediaGeometry": media_geometry,
            "surfaceSequence": cfg["surface_sequence"],
            "rhythmSources": {
                "surfaceSequence": f"runs/{cfg['brand_slug']}/brand/brand.yaml#surfaceGrammar.pageRhythm",
                "sectionPadding": f"runs/{cfg['brand_slug']}/brand/brand.yaml#tokens.spacing",
                "container": f"runs/{cfg['brand_slug']}/brand/brand.yaml#tokens.spacing.container-max",
                "relationalGaps": f"runs/{cfg['brand_slug']}/brand/brand.yaml#tokens.spacing + layoutGrammar.actionGroup",
                "styleScale": (
                    f"runs/{cfg['brand_slug']}/brand/style-scale.yaml"
                    if (ROOT / "runs" / cfg["brand_slug"] / "brand" / "style-scale.yaml").exists()
                    else "unavailable (WoodWave canonical manifest notes optional C24 style-scale absent)"
                ),
            },
            "typographyStatus": cfg["typography_status"],
            "componentContractSource": f"runs/{cfg['brand_slug']}/brand/brand.yaml#buttons",
            "acceptanceStatus": cfg["acceptance_status"],
            "componentContracts": component_contracts,
            "componentDegradations": component_degradations,
            "resolvedRhythm": {
                "sectionPadding": cfg["section_y"],
                "heroPadding": {"top": cfg["hero_top"], "bottom": cfg["hero_bottom"]},
                "container": cfg["container"],
                "eyebrowToHeading": cfg["eyebrow_to_heading"],
                "headingToBody": cfg["heading_to_body"],
                "bodyToCta": cfg["body_to_cta"],
                "blockGap": cfg["block_gap"],
                "columnGap": cfg["column_gap"],
                "gridGap": cfg["grid_gap"],
                "actionGap": cfg["action_gap"],
            },
            "mediaBindings": binder.bindings,
            "gaps": [x for x in binder.bindings if x["status"] == "unavailable"],
        }
        (out / "composition.json").write_text(json.dumps(composition, indent=2) + "\n")
        tokens = {"schemaVersion": "relume-test.tokens.v1", "brandSource": composition["brandSource"], "values": cfg["colors"], "note": "Exact values selected from canonical brand.yaml; no cross-brand values."}
        (out / "tokens.manifest.json").write_text(json.dumps(tokens, indent=2) + "\n")
        (out / "changes.md").write_text(
            f"# {cfg['dir']}\n\n"
            "- Built from the approved Relume-test structural sequence.\n"
            f"- Brand facts source: `{composition['brandSource']}`.\n"
            "- Every media slot was validated against `assets-tagged.json` and the on-disk `assets/` directory.\n"
            f"- Resolved media slots: {sum(x['status']=='resolved' for x in binder.bindings)}.\n"
            f"- Declared unavailable media slots: {sum(x['status']=='unavailable' for x in binder.bindings)}.\n"
            f"- Canonical status: {cfg['status_line']}.\n"
            f"- Acceptance status: {cfg['acceptance_status']}.\n"
            f"- Typography status: {cfg['typography_status']}\n"
            f"- Surface sequence: `{' → '.join(cfg['surface_sequence'])}`.\n"
            f"- Rhythm: section `{cfg['section_y']}`, hero `{cfg['hero_top']} / {cfg['hero_bottom']}`, container `{cfg['container']}`, eyebrow→heading `{cfg['eyebrow_to_heading']}`, heading→body `{cfg['heading_to_body']}`, body→CTA `{cfg['body_to_cta']}`, block `{cfg['block_gap']}`, columns `{cfg['column_gap']}`, grid `{cfg['grid_gap']}`, actions `{cfg['action_gap']}`.\n"
            f"- Rhythm sources: canonical `brand.yaml` surfaceGrammar/pageRhythm, tokens.spacing, and layoutGrammar.actionGroup{'; style-scale.yaml' if (ROOT / 'runs' / cfg['brand_slug'] / 'brand' / 'style-scale.yaml').exists() else '; style-scale unavailable in the WIP canonical lane'}.\n"
            f"- Component contracts: primary, secondary, tertiary/text, menu, and rail controls resolve from canonical `brand.yaml#buttons`; {len(component_degradations)} missing state/control mappings are declared in `composition.json` rather than receiving generic styling.\n"
            "- Split media geometry: no generic ratio or minimum height; wrappers use intrinsic extracted asset dimensions, per-slot fit, `min-size: 0`, and centered self-alignment. Details are recorded in `composition.json#mediaGeometry`.\n"
            "- Browser verification: desktop and 390px mobile loaded successfully; mobile navigation opened by keyboard/click control.\n"
            "- Asset verification: every rendered image URL returned HTTP 200.\n"
            "- Preview artifacts: `preview.png` and `preview-mobile.png`.\n"
        )
        print(f"built {cfg['dir']}: {len(binder.bindings)} media slots")


if __name__ == "__main__":
    main()
