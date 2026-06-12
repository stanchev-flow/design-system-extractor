"""Emit token-styled SiteNav / SiteFooter React components from a chrome contract."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def _tsx_str(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _logo_tsx(logo: dict[str, Any] | None, *, use_brand_resolver: bool) -> str:
    if not logo:
        return (
            '<a href="/" className="text-h3 font-serif tracking-tight text-text-primary">'
            "Brand"
            "</a>"
        )
    href = logo.get("href") or "/"
    alt = logo.get("alt") or "Logo"
    if logo.get("inline_svg"):
        svg = json.dumps(logo["inline_svg"])
        return (
            f'<a href={_tsx_str(href)} className="inline-flex h-8 shrink-0 items-center" aria-label={_tsx_str(alt)}>'
            f'<span className="h-8 w-auto [&_svg]:h-full [&_svg]:w-auto" dangerouslySetInnerHTML={{ __html: {svg} }} />'
            "</a>"
        )
    if use_brand_resolver:
        return (
            f'<a href={_tsx_str(href)} className="inline-flex shrink-0 items-center">'
            "<BrandMark fallback={"
            + _tsx_str(alt)
            + "} />"
            "</a>"
        )
    src = logo.get("src") or ""
    return (
        f'<a href={_tsx_str(href)} className="inline-flex shrink-0 items-center">'
        f'<img src={_tsx_str(src)} alt={_tsx_str(alt)} className="h-8 w-auto object-contain" />'
        "</a>"
    )


def render_site_nav_tsx(contract: dict[str, Any]) -> str:
    nav = contract.get("nav") if isinstance(contract.get("nav"), dict) else {}
    layout = nav.get("layout") or "split"
    sticky = bool(nav.get("sticky"))
    links = nav.get("links") if isinstance(nav.get("links"), list) else []
    actions = nav.get("actions") if isinstance(nav.get("actions"), list) else []
    logo = nav.get("logo") if isinstance(nav.get("logo"), dict) else None

    nav_justify = "justify-center" if layout == "centered" else "justify-between"
    sticky_cls = "sticky top-0 z-40" if sticky else ""
    logo_block = _logo_tsx(logo, use_brand_resolver=True)

    link_items = []
    for ln in links:
        label = str(ln.get("label") or "").strip()
        href = str(ln.get("href") or "#")
        if not label:
            continue
        ext = " rel=\"noopener noreferrer\" target=\"_blank\"" if ln.get("external") else ""
        link_items.append(
            f'        <a href={_tsx_str(href)} className="text-control text-text-primary hover:text-text-accent transition-colors"{ext}>'
            f"{label}"
            "</a>"
        )
    links_block = "\n".join(link_items) if link_items else "        <span className=\"text-meta text-text-muted\">Navigation</span>"

    action_items = []
    for act in actions:
        label = str(act.get("label") or "").strip()
        if not label:
            continue
        href = str(act.get("href") or "")
        kind = act.get("kind") or "link"
        if kind in ("button", "cta") and not href:
            action_items.append(
                f'        <Button variant="primary" size="sm">{label}</Button>'
            )
        elif href:
            action_items.append(
                f'        <a href={_tsx_str(href)} className="btn" data-component="button" data-variant="secondary" data-size="sm" data-icon="none">{label}</a>'
            )
        else:
            action_items.append(
                f'        <Button variant="ghost" size="sm">{label}</Button>'
            )
    actions_block = "\n".join(action_items)

    return f"""import {{ Button }} from "@/components/ui/button";
import {{ Container }} from "@/components/ui/section";
import {{ BrandMark }} from "@/components/chrome/BrandMark";

/** Auto-generated from source URL chrome contract — do not invent alternate nav links. */
export function SiteNav() {{
  return (
    <header
      className="{sticky_cls} border-b border-border-divider bg-surface-primary/95 backdrop-blur"
      data-chrome="nav"
    >
      <Container className="flex h-16 items-center {nav_justify} gap-6">
        {logo_block}
        <nav className="hidden items-center gap-6 md:flex" aria-label="Primary">
{links_block}
        </nav>
        <div className="flex items-center gap-3">
{actions_block}
        </div>
      </Container>
    </header>
  );
}}
"""


def render_site_footer_tsx(contract: dict[str, Any]) -> str:
    footer = contract.get("footer") if isinstance(contract.get("footer"), dict) else {}
    columns = footer.get("columns") if isinstance(footer.get("columns"), list) else []
    logo = footer.get("logo") if isinstance(footer.get("logo"), dict) else None
    logo_block = _logo_tsx(logo, use_brand_resolver=True)

    col_blocks = []
    for col in columns:
        heading = str(col.get("heading") or "").strip()
        links = col.get("links") if isinstance(col.get("links"), list) else []
        if not links:
            continue
        title = (
            f'          <p className="text-eyebrow text-text-on-inverse-muted mb-3">{heading}</p>\n'
            if heading
            else ""
        )
        link_lines = []
        for ln in links:
            label = str(ln.get("label") or "").strip()
            href = str(ln.get("href") or "#")
            if not label:
                continue
            ext = ' target="_blank" rel="noopener noreferrer"' if ln.get("external") else ""
            link_lines.append(
                f'            <li><a href={_tsx_str(href)} className="text-body text-text-on-inverse-muted hover:text-text-on-inverse transition-colors"{ext}>{label}</a></li>'
            )
        if not link_lines:
            continue
        col_blocks.append(
            "        <div>\n"
            + title
            + "          <ul className=\"space-y-2\">\n"
            + "\n".join(link_lines)
            + "\n          </ul>\n"
            "        </div>"
        )

    if not col_blocks:
        col_blocks.append(
            '        <p className="text-body text-text-on-inverse-muted">Footer links from source snapshot.</p>'
        )

    cols_joined = "\n".join(col_blocks)

    return f"""import {{ Section }} from "@/components/ui/section";
import {{ BrandMark }} from "@/components/chrome/BrandMark";

/** Auto-generated from source URL chrome contract — preserve column grouping and hrefs. */
export function SiteFooter() {{
  return (
    <Section surface="inverse" contained className="!py-16" data-chrome="footer">
      <div className="grid gap-10 md:grid-cols-[1.2fr_repeat(auto-fit,minmax(140px,1fr))]">
        <div className="space-y-4">
          {logo_block}
        </div>
{cols_joined}
      </div>
    </Section>
  );
}}
"""


def write_chrome_components(framework_dir: Path, contract: dict[str, Any]) -> list[str]:
    """Write SiteNav/SiteFooter + contract copy into the framework package."""
    chrome_dir = framework_dir / "src" / "components" / "chrome"
    chrome_dir.mkdir(parents=True, exist_ok=True)

    v2 = contract.get("schema_version") == "source_chrome.v2"
    nav_path = chrome_dir / "SiteNav.tsx"
    footer_path = chrome_dir / "SiteFooter.tsx"
    if v2:
        nav_path.write_text(render_site_nav_tsx_v2(contract), encoding="utf-8")
        footer_path.write_text(render_site_footer_tsx_v2(contract), encoding="utf-8")
    else:
        nav_path.write_text(render_site_nav_tsx(contract), encoding="utf-8")
        footer_path.write_text(render_site_footer_tsx(contract), encoding="utf-8")

    (chrome_dir / "source-chrome.json").write_text(
        json.dumps(contract, indent=2) + "\n",
        encoding="utf-8",
    )
    index = chrome_dir / "index.ts"
    index.write_text(
        'export { SiteNav } from "./SiteNav";\nexport { SiteFooter } from "./SiteFooter";\n',
        encoding="utf-8",
    )
    return [
        "src/components/chrome/SiteNav.tsx",
        "src/components/chrome/SiteFooter.tsx",
        "src/components/chrome/index.ts",
    ]


# ── v2 codegen (browser-extracted, computed-style aware) ─────────────────────
def _logo_tsx_v2(logo: dict[str, Any] | None, fallback: str = "Brand") -> str:
    """Logo from v2 contract: inline svg / img, else BrandMark (harvested asset)."""
    if logo and logo.get("kind") == "svg" and logo.get("svg"):
        svg = json.dumps(logo["svg"])
        href = logo.get("href") or "/"
        return (
            f'<a href={_tsx_str(href)} className="inline-flex h-8 shrink-0 items-center" aria-label={_tsx_str(logo.get("alt") or fallback)}>'
            f'<span className="h-8 w-auto [&_svg]:h-full [&_svg]:w-auto" dangerouslySetInnerHTML={{ __html: {svg} }} />'
            "</a>"
        )
    if logo and logo.get("kind") == "img" and logo.get("src"):
        href = logo.get("href") or "/"
        return (
            f'<a href={_tsx_str(href)} className="inline-flex shrink-0 items-center">'
            f'<img src={_tsx_str(logo["src"])} alt={_tsx_str(logo.get("alt") or fallback)} className="h-8 w-auto object-contain" />'
            "</a>"
        )
    return f'<a href="/" className="inline-flex shrink-0 items-center"><BrandMark fallback={_tsx_str(fallback)} /></a>'


def _parse_rgb(value: str | None) -> tuple[float, float, float] | None:
    if not value:
        return None
    m = re.match(r"rgba?\(\s*(\d+)[,\s]+(\d+)[,\s]+(\d+)", str(value))
    if not m:
        return None
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)))


def _luminance(rgb: tuple[float, float, float]) -> float:
    r, g, b = (c / 255.0 for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _nav_is_dark(nav: dict[str, Any]) -> bool:
    """True when the source nav sits on a dark surface (light link text)."""
    lums = [
        _luminance(rgb)
        for ln in (nav.get("links") or [])
        if (rgb := _parse_rgb(ln.get("color"))) is not None
    ]
    if not lums:
        bg = _parse_rgb(nav.get("bg"))
        return bool(bg) and _luminance(bg) < 0.35
    lums.sort()
    median = lums[len(lums) // 2]
    return median > 0.55


def _link_is_accent(link: dict[str, Any], majority_lum: float) -> bool:
    """Detect specially-colored links (e.g. a gold 'buy tickets')."""
    rgb = _parse_rgb(link.get("color"))
    if rgb is None:
        return False
    r, g, b = rgb
    saturated = max(r, g, b) - min(r, g, b) > 40
    return saturated and abs(_luminance(rgb) - majority_lum) > 0.08


def _cta_button_tsx_v2(cta: dict[str, Any]) -> str:
    """Render a header CTA as an anchor styled via the .btn contract.

    Uses the extracted fill/outline to pick the variant and only keeps a trailing
    icon when the source button actually had one (no invented arrows).
    """
    label = str(cta.get("label") or "").strip()
    href = str(cta.get("href") or "#") or "#"
    variant = "primary" if bool(cta.get("filled")) else "secondary"
    icon_attr = "trailing" if cta.get("hasIcon") else "none"
    return (
        f'        <a href={_tsx_str(href)} className="btn" data-component="button" '
        f'data-variant="{variant}" data-size="sm" data-icon="{icon_attr}"><span>{label}</span></a>'
    )


def render_site_nav_tsx_v2(contract: dict[str, Any]) -> str:
    nav = contract.get("nav") if isinstance(contract.get("nav"), dict) else {}
    sticky = bool(nav.get("sticky"))
    links = nav.get("links") if isinstance(nav.get("links"), list) else []
    ctas = nav.get("ctas") if isinstance(nav.get("ctas"), list) else []
    logo = nav.get("logo") if isinstance(nav.get("logo"), dict) else None

    dark = _nav_is_dark(nav)
    if dark:
        header_surface = "border-b border-border-on-inverse bg-surface-inverse"
        link_cls = "text-control text-text-on-inverse hover:text-text-accent transition-colors"
        accent_cls = "text-control text-text-accent hover:text-text-on-inverse transition-colors"
    else:
        header_surface = "border-b border-border-divider bg-surface-primary/95 backdrop-blur"
        link_cls = "text-control text-text-primary hover:text-text-accent transition-colors"
        accent_cls = "text-control text-text-accent hover:text-text-primary transition-colors"

    lums = sorted(
        _luminance(rgb)
        for ln in links
        if (rgb := _parse_rgb(ln.get("color"))) is not None
    )
    majority_lum = lums[len(lums) // 2] if lums else (0.9 if dark else 0.1)

    sticky_cls = "sticky top-0 z-40 " if sticky else ""
    logo_block = _logo_tsx_v2(logo)

    link_items = []
    for ln in links:
        label = str(ln.get("label") or "").strip()
        href = str(ln.get("href") or "#")
        if not label:
            continue
        cls = accent_cls if _link_is_accent(ln, majority_lum) else link_cls
        link_items.append(
            f'          <a href={_tsx_str(href)} className="{cls}">{label}</a>'
        )
    links_block = "\n".join(link_items)

    cta_items = [_cta_button_tsx_v2(c) for c in ctas if str(c.get("label") or "").strip()]
    cta_block = "\n".join(cta_items)

    return f"""import {{ Container }} from "@/components/ui/section";
import {{ BrandMark }} from "@/components/chrome/BrandMark";

/** Auto-generated from browser chrome contract (source_chrome.v2). Real top-level
 *  nav, real CTA styling, no invented arrows. Do not add or rename links. */
export function SiteNav() {{
  return (
    <header
      className="{sticky_cls}{header_surface}"
      data-chrome="nav"
    >
      <Container className="flex h-16 items-center justify-between gap-6">
        {logo_block}
        <nav className="hidden items-center gap-7 lg:flex" aria-label="Primary">
{links_block}
        </nav>
        <div className="flex items-center gap-3">
{cta_block}
        </div>
      </Container>
    </header>
  );
}}
"""


def render_site_footer_tsx_v2(contract: dict[str, Any]) -> str:
    footer = contract.get("footer") if isinstance(contract.get("footer"), dict) else {}
    columns = footer.get("columns") if isinstance(footer.get("columns"), list) else []
    logo = footer.get("logo") if isinstance(footer.get("logo"), dict) else None
    logo_block = _logo_tsx_v2(logo)

    col_blocks = []
    for col in columns:
        heading = str(col.get("heading") or "").strip()
        col_links = col.get("links") if isinstance(col.get("links"), list) else []
        if not col_links:
            continue
        title = (
            f'          <p className="text-eyebrow text-text-on-inverse-muted mb-3">{heading}</p>\n'
            if heading
            else ""
        )
        link_lines = []
        for ln in col_links:
            label = str(ln.get("label") or "").strip()
            href = str(ln.get("href") or "#")
            if not label:
                continue
            link_lines.append(
                f'            <li><a href={_tsx_str(href)} className="text-body text-text-on-inverse-muted hover:text-text-on-inverse transition-colors">{label}</a></li>'
            )
        if not link_lines:
            continue
        col_blocks.append(
            "        <div>\n"
            + title
            + '          <ul className="space-y-2">\n'
            + "\n".join(link_lines)
            + "\n          </ul>\n        </div>"
        )

    cols_joined = "\n".join(col_blocks) or '        <p className="text-body text-text-on-inverse-muted">Footer.</p>'

    return f"""import {{ Section }} from "@/components/ui/section";
import {{ BrandMark }} from "@/components/chrome/BrandMark";

/** Auto-generated from browser chrome contract (source_chrome.v2). Preserve column
 *  grouping, headings, and hrefs from the source site. */
export function SiteFooter() {{
  return (
    <Section surface="inverse" contained className="!py-16" data-chrome="footer">
      <div className="grid gap-10 md:grid-cols-2 lg:grid-cols-[1.4fr_repeat(auto-fit,minmax(130px,1fr))]">
        <div className="space-y-4">
          {logo_block}
        </div>
{cols_joined}
      </div>
    </Section>
  );
}}
"""
