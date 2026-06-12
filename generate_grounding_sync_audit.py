#!/usr/bin/env python3
"""Generate an HTML audit page for grounding pre/post source-style sync."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_DIR / "src"))

from screenshot_to_template.source_colors import (
    HSL_RE,
    HEX_RE,
    RGB_RE,
    collect_allowed_source_color_literals,
)


SECTION_RE = re.compile(
    r"^## Section (\d+): (.+?)\n(.*?)(?=^## Section \d+: |\n## Cross-section Notes|\Z)",
    re.MULTILINE | re.DOTALL,
)
SUBSECTION_RE = re.compile(r"^### (.+)$", re.MULTILINE)
ITEM_RE = re.compile(r"^#### (.+)$", re.MULTILINE)
BULLET_VALUE_RE = re.compile(r"^- \*\*(.+?):\*\* (.+)$")
FONT_FAMILY_RE = re.compile(r"`([^`]*[A-Za-z][^`]*)`")
SIZE_RE = re.compile(r"\b\d+(?:\.\d+)?(?:px|em|rem|%)\b")
WEIGHT_RE = re.compile(r"\b(?:[1-9]00)\b")
LETTER_SPACING_RE = re.compile(r"`?-?\d+(?:\.\d+)?px`?")
APPROX_RE = re.compile(r"\b(?:approximately|around|roughly|family|unclear)\b", re.IGNORECASE)


def extract_color_literals(text: str) -> list[str]:
    values: list[str] = []
    values.extend(HEX_RE.findall(text))
    values.extend(RGB_RE.findall(text))
    values.extend(HSL_RE.findall(text))
    return values


def normalize_hex(value: str) -> str:
    body = value.lstrip("#")
    if len(body) == 3:
        body = "".join(ch * 2 for ch in body)
    if len(body) == 4:
        body = "".join(ch * 2 for ch in body)
    return f"#{body.upper()}"


def color_to_rgba(value: str) -> tuple[float, float, float, float] | None:
    value = value.strip()
    if HEX_RE.fullmatch(value):
        body = value.lstrip("#")
        if len(body) in (3, 4):
            body = "".join(ch * 2 for ch in body)
        if len(body) == 6:
            r, g, b = int(body[0:2], 16), int(body[2:4], 16), int(body[4:6], 16)
            return r / 255, g / 255, b / 255, 1.0
        if len(body) == 8:
            r, g, b, a = (
                int(body[0:2], 16),
                int(body[2:4], 16),
                int(body[4:6], 16),
                int(body[6:8], 16),
            )
            return r / 255, g / 255, b / 255, a / 255
    m = re.match(r"rgba?\(([^)]+)\)", value.strip(), re.IGNORECASE)
    if m:
        parts = [p.strip() for p in m.group(1).split(",")]
        if len(parts) >= 3:
            try:
                r = float(parts[0]) / 255
                g = float(parts[1]) / 255
                b = float(parts[2]) / 255
                a = float(parts[3]) if len(parts) > 3 else 1.0
                return r, g, b, a
            except ValueError:
                return None
    return None


def composite_over(bg: tuple[float, float, float], fg: tuple[float, float, float, float]) -> tuple[float, float, float]:
    fr, fg_g, fb, fa = fg
    br, bg_g, bb = bg
    return (
        fr * fa + br * (1 - fa),
        fg_g * fa + bg_g * (1 - fa),
        fb * fa + bb * (1 - fa),
    )


def relative_luminance(rgb: tuple[float, float, float]) -> float:
    def channel(v: float) -> float:
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4

    r, g, b = rgb
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def contrast_ratio(bg_value: str, fg_value: str) -> float | None:
    bg_rgba = color_to_rgba(bg_value)
    fg_rgba = color_to_rgba(fg_value)
    if not bg_rgba or not fg_rgba:
        return None
    bg_rgb = composite_over((1.0, 1.0, 1.0), bg_rgba) if bg_rgba[3] < 1 else bg_rgba[:3]
    fg_rgb = composite_over(bg_rgb, fg_rgba) if fg_rgba[3] < 1 else fg_rgba[:3]
    l1 = relative_luminance(bg_rgb)
    l2 = relative_luminance(fg_rgb)
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def contrast_grade(ratio: float | None) -> str:
    if ratio is None:
        return "n/a"
    if ratio >= 7:
        return "AAA"
    if ratio >= 4.5:
        return "AA"
    if ratio >= 3:
        return "Large-only"
    return "Fail"


def best_background_for_primary_text(section_fields: dict[str, str], fg_value: str) -> tuple[list[str], float | None]:
    section_bg = extract_color_literals(section_fields.get("Section / Section background", ""))
    large_module_bg = extract_color_literals(section_fields.get("Nested components / Large module / Background", ""))

    def worst_ratio(bg_values: list[str]) -> float | None:
        ratios = [contrast_ratio(bg, fg_value) for bg in bg_values]
        ratios = [r for r in ratios if r is not None]
        return min(ratios) if ratios else None

    section_ratio = worst_ratio(section_bg) if section_bg else None
    module_ratio = worst_ratio(large_module_bg) if large_module_bg else None

    if large_module_bg and module_ratio is not None:
        if section_ratio is None or module_ratio > section_ratio:
            return large_module_bg, module_ratio

    return section_bg, section_ratio


def parse_sections(markdown: str) -> list[dict]:
    sections: list[dict] = []
    for match in SECTION_RE.finditer(markdown):
        num = int(match.group(1))
        title = match.group(2).strip()
        body = match.group(3).strip()
        current_subsection = ""
        current_item = ""
        fields: dict[str, str] = {}
        ordered_entries: list[tuple[str, str, str, str]] = []
        for line in body.splitlines():
            sub = SUBSECTION_RE.match(line)
            if sub:
                current_subsection = sub.group(1).strip()
                current_item = ""
                continue
            item = ITEM_RE.match(line)
            if item:
                current_item = item.group(1).strip()
                continue
            bullet = BULLET_VALUE_RE.match(line)
            if bullet:
                label = bullet.group(1).strip()
                value = bullet.group(2).strip()
                path = " / ".join(part for part in (current_subsection, current_item, label) if part)
                fields[path] = value
                ordered_entries.append((current_subsection, current_item, label, value))
        sections.append(
            {
                "num": num,
                "title": title,
                "body": body,
                "fields": fields,
                "entries": ordered_entries,
            }
        )
    return sections


def extract_typography_literals(text: str) -> list[str]:
    values: list[str] = []
    values.extend(FONT_FAMILY_RE.findall(text))
    values.extend(SIZE_RE.findall(text))
    values.extend(WEIGHT_RE.findall(text))
    values.extend(v.strip("`") for v in LETTER_SPACING_RE.findall(text))
    return sorted({v for v in values if any(ch.isalpha() for ch in v) or any(ch.isdigit() for ch in v)})


def build_source_index(source: dict) -> dict[str, list[str]]:
    index: dict[str, list[str]] = {}

    def add(value: str, label: str):
        index.setdefault(value, []).append(label)

    for key, value in source.get("resolved_custom_properties", {}).items():
        add(value, f"{key}")
    for key, value in source.get("gradient_custom_properties", {}).items():
        add(value, f"{key}")
    for key, value in source.get("typography_custom_properties", {}).items():
        add(value, f"{key}")
    for bucket in (
        "frequent_font_families",
        "frequent_font_sizes",
        "frequent_font_weights",
        "frequent_line_heights",
        "frequent_letter_spacings",
        "frequent_color_literals",
    ):
        for entry in source.get(bucket, []):
            add(entry["value"], f"{bucket}:{entry['count']}")
    return index


def format_section_entries(entries: list[tuple[str, str, str, str]]) -> str:
    groups: list[str] = []
    current_sub = None
    current_item = None
    for subsection, item, label, value in entries:
        if subsection != current_sub:
            groups.append(f"<div class='subheading'>{html.escape(subsection)}</div>")
            current_sub = subsection
            current_item = None
        if item and item != current_item:
            groups.append(f"<div class='itemheading'>{html.escape(item)}</div>")
            current_item = item
        groups.append(
            "<div class='field-row'>"
            f"<div class='field-label'>{html.escape(label)}</div>"
            f"<div class='field-value'>{html.escape(value)}</div>"
            "</div>"
        )
    return "\n".join(groups)


def build_replacements(pre: dict, final: dict, source_index: dict) -> list[dict]:
    replacements: list[dict] = []
    all_paths = sorted(set(pre["fields"]) | set(final["fields"]))
    for path in all_paths:
        before = pre["fields"].get(path, "")
        after = final["fields"].get(path, "")
        if before == after:
            continue
        before_colors = extract_color_literals(before)
        after_colors = extract_color_literals(after)
        before_typos = extract_typography_literals(before)
        after_typos = extract_typography_literals(after)
        source_hits = []
        for value in after_colors + after_typos:
            source_hits.extend(source_index.get(value, []))
            if value.startswith("#"):
                source_hits.extend(source_index.get(normalize_hex(value), []))
        replacements.append(
            {
                "path": path,
                "before": before,
                "after": after,
                "before_colors": before_colors,
                "after_colors": after_colors,
                "before_typos": before_typos,
                "after_typos": after_typos,
                "source_hits": sorted(set(source_hits)),
            }
        )
    return replacements


def build_accessibility_checks(section: dict) -> list[dict]:
    checks: list[dict] = []
    fields = section["fields"]
    for key, value in fields.items():
        if not key.startswith("Primary text / "):
            continue
        if not key.endswith(" / Foreground color"):
            continue
        fg_values = extract_color_literals(value)
        for fg in fg_values:
            bg_values, worst = best_background_for_primary_text(fields, fg)
            if not bg_values:
                continue
            checks.append(
                {
                    "scope": key.replace("Primary text / ", "").replace(" / Foreground color", ""),
                    "background": ", ".join(bg_values),
                    "foreground": fg,
                    "ratio": worst,
                    "grade": contrast_grade(worst),
                }
            )
    component_names = sorted({path.split(" / ")[1] for path in fields if path.startswith("Nested components / ") and len(path.split(" / ")) >= 3})
    for component in component_names:
        bg = extract_color_literals(fields.get(f"Nested components / {component} / Background", ""))
        fg = extract_color_literals(fields.get(f"Nested components / {component} / Foreground colors", ""))
        if not bg or not fg:
            continue
        if len(bg) > 1 and len(fg) > 1:
            checks.append(
                {
                    "scope": component,
                    "background": ", ".join(bg),
                    "foreground": ", ".join(fg),
                    "ratio": None,
                    "grade": "Mixed",
                }
            )
            continue
        for fg_value in fg:
            ratios = [contrast_ratio(bg_value, fg_value) for bg_value in bg]
            ratios = [r for r in ratios if r is not None]
            worst = min(ratios) if ratios else None
            checks.append(
                {
                    "scope": component,
                    "background": ", ".join(bg),
                    "foreground": fg_value,
                    "ratio": worst,
                    "grade": contrast_grade(worst),
                }
            )
    return checks


def source_matches_for_section(section: dict, source_index: dict) -> dict[str, list[str]]:
    matches: dict[str, list[str]] = {}
    values = set(extract_color_literals(section["body"])) | set(extract_typography_literals(section["body"]))
    for value in sorted(values):
        hits = source_index.get(value, [])
        if value.startswith("#"):
            hits = hits + source_index.get(normalize_hex(value), [])
        if hits:
            matches[value] = sorted(set(hits))
    return matches


def render_replacements(replacements: list[dict]) -> str:
    if not replacements:
        return "<div class='muted'>No replacements detected.</div>"
    rows = []
    for rep in replacements:
        source_hits = "<br>".join(html.escape(hit) for hit in rep["source_hits"]) if rep["source_hits"] else "<span class='muted'>No direct source token match</span>"
        rows.append(
            "<div class='replacement'>"
            f"<div class='field-path'>{html.escape(rep['path'])}</div>"
            f"<div class='before'><span class='pill before-pill'>Before</span> {html.escape(rep['before'])}</div>"
            f"<div class='after'><span class='pill after-pill'>After</span> {html.escape(rep['after'])}</div>"
            f"<div class='source-hit'><strong>Source matches:</strong><br>{source_hits}</div>"
            "</div>"
        )
    return "\n".join(rows)


def render_source_matches(matches: dict[str, list[str]]) -> str:
    if not matches:
        return "<div class='muted'>No direct matches found.</div>"
    rows = []
    for value, hits in matches.items():
        rows.append(
            "<div class='source-match'>"
            f"<div class='token-value'>{html.escape(value)}</div>"
            f"<div class='token-hits'>{'<br>'.join(html.escape(hit) for hit in hits)}</div>"
            "</div>"
        )
    return "\n".join(rows)


def render_scorecard(section: dict, replacements: list[dict], checks: list[dict], source_allowed: set[str]) -> str:
    final_colors = extract_color_literals(section["body"])
    source_backed = sum(1 for value in final_colors if value in source_allowed or normalize_hex(value) in source_allowed)
    unresolved_approx = len(APPROX_RE.findall(section["body"]))
    pass_count = sum(1 for check in checks if check["grade"] in {"AA", "AAA"})
    fail_count = sum(1 for check in checks if check["grade"] == "Fail")
    large_only = sum(1 for check in checks if check["grade"] == "Large-only")

    summary = [
        f"<div><strong>Replacement coverage:</strong> {len(replacements)} changed field(s)</div>",
        f"<div><strong>Source-backed final colors:</strong> {source_backed}/{len(final_colors) if final_colors else 0}</div>",
        f"<div><strong>Remaining approximate language:</strong> {unresolved_approx}</div>",
        f"<div><strong>Accessibility:</strong> {pass_count} AA/AAA, {large_only} large-only, {fail_count} fail</div>",
    ]
    if checks:
        summary.append("<div class='rubric-heading'>Foreground / background checks</div>")
        for check in checks:
            ratio = f"{check['ratio']:.2f}" if check["ratio"] is not None else "n/a"
            summary.append(
                "<div class='contrast-row'>"
                f"<div><strong>{html.escape(check['scope'])}</strong></div>"
                f"<div>{html.escape(check['foreground'])} on {html.escape(check['background'])}</div>"
                f"<div>{ratio} · <span class='grade {check['grade'].lower().replace(' ', '-').replace('/', '-')}'>{check['grade']}</span></div>"
                "</div>"
            )
    else:
        summary.append("<div class='muted'>No reliable foreground/background pairs could be scored.</div>")
    return "\n".join(summary)


def generate_html(version: str, screenshot: str, mode: str, base_dir: Path) -> str:
    pre_path = base_dir / "structural-analysis.pre-source-sync.md"
    final_path = base_dir / "structural-analysis.md"
    source_json_path = base_dir / "source-colors.json"
    source_md_path = base_dir / "source-colors.md"

    pre_text = pre_path.read_text()
    final_text = final_path.read_text()
    source = json.loads(source_json_path.read_text())
    source_report = source_md_path.read_text()
    source_index = build_source_index(source)
    source_allowed = collect_allowed_source_color_literals(source)

    pre_sections = {section["num"]: section for section in parse_sections(pre_text)}
    final_sections = parse_sections(final_text)

    section_rows = []
    for final_section in final_sections:
        pre_section = pre_sections.get(final_section["num"], {"entries": [], "fields": {}, "body": ""})
        replacements = build_replacements(pre_section, final_section, source_index)
        source_matches = source_matches_for_section(final_section, source_index)
        checks = build_accessibility_checks(final_section)
        section_rows.append(
            f"""
            <section class="section-row" id="section-{final_section['num']}">
              <div class="row-title">Section {final_section['num']}: {html.escape(final_section['title'])}</div>
              <div class="grid">
                <div class="col">
                  <div class="col-title">Original Grounded Approximation</div>
                  {format_section_entries(pre_section.get("entries", []))}
                </div>
                <div class="col">
                  <div class="col-title">Source CSS Tokens / Styles</div>
                  {render_source_matches(source_matches)}
                </div>
                <div class="col">
                  <div class="col-title">Replacements Applied</div>
                  {render_replacements(replacements)}
                </div>
                <div class="col">
                  <div class="col-title">Final Grounded Output</div>
                  {format_section_entries(final_section['entries'])}
                </div>
                <div class="col">
                  <div class="col-title">Replacement + Accessibility Scorecard</div>
                  {render_scorecard(final_section, replacements, checks, source_allowed)}
                </div>
              </div>
            </section>
            """
        )

    style_preview = html.escape(source_report)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Grounding Sync Audit · {html.escape(version)} · {html.escape(screenshot)}</title>
  <style>
    :root {{
      --bg: #0f1113;
      --panel: #171a1f;
      --panel-2: #1d2128;
      --text: #f2f4f7;
      --muted: #a9b0bb;
      --border: #2c313a;
      --accent: #85f382;
      --danger: #ff7b72;
      --warn: #f6c26b;
      --ok: #72f1b8;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: linear-gradient(180deg, #0f1113, #141922);
      color: var(--text);
    }}
    a {{ color: var(--accent); }}
    .shell {{ padding: 24px; }}
    .hero {{
      background: rgba(255,255,255,0.03);
      border: 1px solid var(--border);
      border-radius: 18px;
      padding: 20px;
      margin-bottom: 20px;
    }}
    .hero h1 {{ margin: 0 0 8px; font-size: 24px; }}
    .hero p {{ margin: 4px 0; color: var(--muted); max-width: 960px; }}
    .summary-grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
      margin-top: 16px;
    }}
    .summary-card {{
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 14px;
    }}
    .summary-card h2 {{ margin: 0 0 8px; font-size: 13px; text-transform: uppercase; letter-spacing: .08em; color: var(--muted); }}
    .summary-card pre {{
      margin: 0;
      white-space: pre-wrap;
      word-break: break-word;
      font-size: 12px;
      line-height: 1.45;
      color: #dce2ea;
    }}
    .section-row {{
      margin-bottom: 22px;
      background: rgba(255,255,255,0.02);
      border: 1px solid var(--border);
      border-radius: 18px;
      overflow: hidden;
    }}
    .row-title {{
      position: sticky;
      top: 0;
      z-index: 2;
      background: #11151c;
      border-bottom: 1px solid var(--border);
      padding: 14px 18px;
      font-weight: 700;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(5, minmax(320px, 1fr));
      overflow-x: auto;
    }}
    .col {{
      min-height: 100%;
      padding: 16px;
      border-right: 1px solid var(--border);
      background: var(--panel);
    }}
    .col:nth-child(odd) {{ background: var(--panel-2); }}
    .col:last-child {{ border-right: none; }}
    .col-title {{
      position: sticky;
      top: 49px;
      z-index: 1;
      background: inherit;
      padding-bottom: 10px;
      margin-bottom: 12px;
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: .08em;
      color: var(--muted);
      border-bottom: 1px solid var(--border);
    }}
    .subheading {{
      margin: 12px 0 8px;
      font-size: 12px;
      font-weight: 700;
      color: #dbe3ee;
      text-transform: uppercase;
      letter-spacing: .08em;
    }}
    .itemheading {{
      margin: 10px 0 6px;
      font-size: 13px;
      font-weight: 700;
      color: var(--accent);
    }}
    .field-row {{
      margin-bottom: 8px;
      padding: 8px 10px;
      border: 1px solid rgba(255,255,255,0.04);
      border-radius: 10px;
      background: rgba(255,255,255,0.02);
    }}
    .field-label {{
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: .08em;
      color: var(--muted);
      margin-bottom: 4px;
    }}
    .field-value {{
      white-space: pre-wrap;
      word-break: break-word;
      font-size: 12px;
      line-height: 1.45;
    }}
    .replacement, .source-match, .contrast-row {{
      border: 1px solid rgba(255,255,255,0.05);
      border-radius: 10px;
      padding: 10px;
      margin-bottom: 10px;
      background: rgba(255,255,255,0.02);
    }}
    .field-path, .token-value {{
      font-size: 12px;
      font-weight: 700;
      margin-bottom: 6px;
      color: #dce2ea;
    }}
    .before, .after, .source-hit, .token-hits {{
      font-size: 12px;
      line-height: 1.45;
      color: #d4dbe5;
      white-space: pre-wrap;
      word-break: break-word;
    }}
    .muted {{ color: var(--muted); font-size: 12px; }}
    .pill {{
      display: inline-block;
      padding: 2px 6px;
      border-radius: 999px;
      font-size: 10px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: .08em;
      margin-right: 6px;
    }}
    .before-pill {{ background: rgba(246,194,107,0.18); color: var(--warn); }}
    .after-pill {{ background: rgba(114,241,184,0.16); color: var(--ok); }}
    .rubric-heading {{
      margin-top: 12px;
      margin-bottom: 8px;
      font-size: 12px;
      font-weight: 700;
      color: #dce2ea;
    }}
    .grade {{
      font-weight: 700;
      padding: 2px 6px;
      border-radius: 999px;
    }}
    .grade.aaa, .grade.aa {{ background: rgba(114,241,184,0.16); color: var(--ok); }}
    .grade.large-only {{ background: rgba(246,194,107,0.18); color: var(--warn); }}
    .grade.mixed {{ background: rgba(169,176,187,0.18); color: var(--muted); }}
    .grade.fail {{ background: rgba(255,123,114,0.16); color: var(--danger); }}
    @media (max-width: 1200px) {{
      .summary-grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <div class="hero">
      <h1>Grounding Sync Audit · {html.escape(version)} · {html.escape(screenshot)} · {html.escape(mode)}</h1>
      <p>This page compares the original grounded approximation, source CSS styles, replacements applied during grounding sync, the final grounded output, and an accessibility/source-fidelity scorecard for each section.</p>
      <p>Artifacts: <a href="{html.escape(str(pre_path.name))}">{html.escape(pre_path.name)}</a>, <a href="{html.escape(str(final_path.name))}">{html.escape(final_path.name)}</a>, <a href="{html.escape(str(source_md_path.name))}">{html.escape(source_md_path.name)}</a></p>
      <div class="summary-grid">
        <div class="summary-card">
          <h2>Source CSS Styles</h2>
          <pre>{style_preview[:7000]}</pre>
        </div>
        <div class="summary-card">
          <h2>What This Audits</h2>
          <pre>1. Original approximated section backgrounds, nested element colors, and fonts
2. Source CSS tokens / style values extracted from HTML
3. Which approximations were replaced with real CSS-backed values
4. Final grounded output after sync
5. Source-fidelity coverage and foreground/background accessibility checks</pre>
        </div>
        <div class="summary-card">
          <h2>Legend</h2>
          <pre>Replacement coverage = changed fields between pre-sync and post-sync
Source-backed final colors = explicit final color literals present in source HTML/CSS
Accessibility grades:
- AAA: 7.0+
- AA: 4.5+
- Large-only: 3.0+
- Fail: below 3.0

For gradients or alpha-heavy surfaces, checks may be partial.</pre>
        </div>
      </div>
    </div>
    {''.join(section_rows)}
  </div>
</body>
</html>"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--screenshot", required=True)
    parser.add_argument("--mode", default="single")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    project_dir = PROJECT_DIR
    base_dir = project_dir / "runs" / args.version / args.screenshot / args.mode
    if not base_dir.exists():
        raise SystemExit(f"Missing run directory: {base_dir}")

    output_path = Path(args.output) if args.output else base_dir / "grounding-sync-audit.html"
    html_text = generate_html(args.version, args.screenshot, args.mode, base_dir)
    output_path.write_text(html_text)
    print(output_path)


if __name__ == "__main__":
    main()
