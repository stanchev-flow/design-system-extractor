#!/usr/bin/env python3
"""Generate a horizontal version scoreboard landing page."""

from __future__ import annotations

import html
import json
import re
import statistics
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_DIR = Path(__file__).resolve().parents[1]
RUNS_DIR = PROJECT_DIR / "runs"
OUTPUT_PATH = PROJECT_DIR / "version-scoreboard.html"

SITE_ORDER = ["clean", "elegant", "funky", "futuristic", "minimal"]

REVIEW_LABELS = {
    "surface-component-map-review.json": "Surface Map Fidelity",
    "design-system-conversion-review.json": "Conversion Loss",
    "design-system-review.json": "Design System Review",
    "site-claude-review.json": "Claude Site Review",
    "site-gemini-review.json": "Gemini Site Review",
    "site-gpt54-review.json": "GPT Site Review",
    "full-page-review.json": "Full-Page Grounding",
}

GROUPS = [
    ("Latest Full Runs", "v154", "Best strategy applied to full site generation"),
    ("Strategy Bakeoff", "v146", "Five design-system conversion strategies"),
    ("Conversion Loss", "v123", "Surface map -> design-system preservation"),
    ("Surface Map Fidelity", "v080", "Grounding -> deterministic surface map reviews"),
    ("Design-System Iterations", "v068", "Early prompt fixes and DS scoring"),
    ("Site Review Runs", "v043", "Generated-site review era"),
    ("Early Baselines", "v001", "Initial run history"),
]


def version_number(version: str) -> int:
    match = re.fullmatch(r"v(\d{3})", version)
    return int(match.group(1)) if match else -1


def rel(path: Path) -> str:
    return path.relative_to(PROJECT_DIR).as_posix()


def read_text(path: Path) -> str:
    try:
        return path.read_text()
    except FileNotFoundError:
        return ""


def read_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def display_name(version_dir: Path) -> str:
    explicit = read_text(version_dir / "display-name.txt").strip()
    if explicit:
        return explicit
    changes = read_text(version_dir / "changes.md")
    for line in changes.splitlines():
        stripped = line.strip("# ").strip()
        if stripped and stripped.lower() != "changes":
            return stripped
    return version_dir.name


def score_from_json(data: dict[str, Any]) -> float | None:
    for key in ("weighted_score", "overall_score", "score", "final_score"):
        value = data.get(key)
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                pass
    overall = data.get("overall")
    if isinstance(overall, dict):
        return score_from_json(overall)
    return None


def score_class(score: float, max_score: float = 100.0) -> str:
    normalized = (score / max_score) * 100 if max_score else score
    if normalized >= 85:
        return "score-high"
    if normalized >= 70:
        return "score-good"
    if normalized >= 55:
        return "score-mid"
    return "score-low"


def review_label(path: Path) -> str:
    return REVIEW_LABELS.get(path.name, path.name.replace(".json", "").replace("-", " ").title())


def site_name(version_dir: Path, path: Path) -> str:
    try:
        parts = path.relative_to(version_dir).parts
    except ValueError:
        return "run"
    if parts and parts[0] in SITE_ORDER:
        return parts[0]
    return parts[0] if parts else "run"


def detail_scores(data: dict[str, Any]) -> list[dict[str, Any]]:
    scores = data.get("scores")
    if not isinstance(scores, dict):
        return []
    details: list[dict[str, Any]] = []
    for key, value in scores.items():
        if not isinstance(value, dict):
            continue
        score = value.get("score")
        if not isinstance(score, (int, float)):
            continue
        heading = str(value.get("heading") or key.replace("_", " ").replace("-", " ").title())
        parent = str(value.get("parent_heading") or "").strip()
        label = f"{parent} / {heading}" if parent else heading
        notes = str(value.get("notes") or "")
        details.append({"label": label, "score": float(score), "notes": notes})
    return details


def markdown_to_html(markdown: str) -> str:
    if not markdown.strip():
        return '<p class="empty">No changes.md found.</p>'
    lines = markdown.splitlines()
    out: list[str] = []
    in_list = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if in_list:
                out.append("</ul>")
                in_list = False
            continue
        if stripped.startswith("#"):
            if in_list:
                out.append("</ul>")
                in_list = False
            level = min(len(stripped) - len(stripped.lstrip("#")), 4)
            text = stripped.lstrip("#").strip()
            out.append(f"<h{level}>{inline_md(text)}</h{level}>")
        elif stripped.startswith("- "):
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{inline_md(stripped[2:].strip())}</li>")
        else:
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(f"<p>{inline_md(stripped)}</p>")
    if in_list:
        out.append("</ul>")
    return "\n".join(out)


def inline_md(text: str) -> str:
    escaped = html.escape(text)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    return escaped


def collect_version(version_dir: Path) -> dict[str, Any]:
    version = version_dir.name
    review_rows: list[dict[str, Any]] = []
    scoreless_rows: list[dict[str, Any]] = []
    category_scores: dict[str, list[float]] = {}

    for path in sorted(version_dir.glob("**/*review.json")):
        data = read_json(path)
        if data is None:
            continue
        score = score_from_json(data)
        category = review_label(path)
        row = {
            "site": site_name(version_dir, path),
            "category": category,
            "score": score,
            "path": rel(path),
            "details": detail_scores(data),
            "summary": str(data.get("summary") or data.get("verdict") or ""),
        }
        if score is None:
            scoreless_rows.append(row)
        else:
            review_rows.append(row)
            category_scores.setdefault(category, []).append(score)

    review_rows.sort(key=lambda row: (SITE_ORDER.index(row["site"]) if row["site"] in SITE_ORDER else 99, row["category"]))
    averages = {
        category: statistics.fmean(values)
        for category, values in sorted(category_scores.items())
        if values
    }
    all_scores = [row["score"] for row in review_rows if isinstance(row["score"], float)]
    overall = statistics.fmean(all_scores) if all_scores else None
    return {
        "version": version,
        "number": version_number(version),
        "display_name": display_name(version_dir),
        "path": rel(version_dir),
        "reviews": review_rows,
        "scoreless": scoreless_rows,
        "averages": averages,
        "overall": overall,
        "changes_html": markdown_to_html(read_text(version_dir / "changes.md")),
    }


def render_score(score: float, max_score: float = 100.0) -> str:
    label = f"{score:.1f}/10" if max_score == 10 else f"{score:.2f}"
    return f'<span class="score-pill {score_class(score, max_score)}">{label}</span>'


def render_version_column(version: dict[str, Any]) -> str:
    version_id = html.escape(version["version"])
    name = html.escape(version["display_name"])
    overall = version["overall"]
    averages = version["averages"]
    review_rows = version["reviews"]
    scoreless_rows = version["scoreless"]

    avg_cards = []
    if overall is not None:
        avg_cards.append(
            '<div class="metric-card metric-overall">'
            '<span class="metric-label">All scored artifacts</span>'
            f"{render_score(overall)}"
            "</div>"
        )
    for category, score in averages.items():
        avg_cards.append(
            '<div class="metric-card">'
            f'<span class="metric-label">{html.escape(category)}</span>'
            f"{render_score(score)}"
            "</div>"
        )
    if not avg_cards:
        avg_cards.append('<p class="empty">No scored review artifacts found.</p>')

    rows = []
    for row in review_rows:
        details = ""
        if row["details"]:
            detail_rows = []
            for detail in row["details"]:
                detail_rows.append(
                    "<tr>"
                    f"<td>{html.escape(detail['label'])}</td>"
                    f"<td>{render_score(detail['score'], max_score=10)}</td>"
                    f"<td>{html.escape(detail['notes'])}</td>"
                    "</tr>"
                )
            details = (
                '<details class="detail-scores">'
                "<summary>Section scores</summary>"
                '<table class="detail-table"><tbody>'
                + "".join(detail_rows)
                + "</tbody></table></details>"
            )
        summary = f'<p class="row-summary">{html.escape(row["summary"])}</p>' if row["summary"] else ""
        rows.append(
            '<div class="score-row">'
            '<div class="score-row-top">'
            f'<div><span class="site-label">{html.escape(row["site"])}</span>'
            f'<a href="{html.escape(row["path"])}" target="_blank">{html.escape(row["category"])}</a></div>'
            f"{render_score(row['score'])}"
            "</div>"
            f"{summary}{details}"
            "</div>"
        )

    scoreless = ""
    if scoreless_rows:
        links = "".join(
            f'<li><a href="{html.escape(row["path"])}" target="_blank">{html.escape(row["site"])}: {html.escape(row["category"])}</a></li>'
            for row in scoreless_rows
        )
        scoreless = (
            '<details class="scoreless"><summary>Scoreless artifacts</summary>'
            f"<ul>{links}</ul></details>"
        )

    return (
        f'<article class="version-column" id="{version_id}">'
        '<header class="version-header">'
        f'<a class="version-kicker" href="runs/{version_id}/" target="_blank">{version_id}</a>'
        f"<h2>{name}</h2>"
        "</header>"
        '<section class="column-section">'
        "<h3>Pipeline Scores</h3>"
        f'<div class="metric-grid">{"".join(avg_cards)}</div>'
        f'<div class="score-list">{"".join(rows) if rows else ""}</div>'
        f"{scoreless}"
        "</section>"
        '<section class="column-section changes-section">'
        "<h3>Changes</h3>"
        f'<div class="changes-copy">{version["changes_html"]}</div>'
        "</section>"
        "</article>"
    )


def render_page(versions: list[dict[str, Any]]) -> str:
    generated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    version_count = len(versions)
    scored_count = sum(1 for version in versions if version["reviews"])
    nav_links = []
    available_versions = {version["version"] for version in versions}
    for label, anchor, description in GROUPS:
        if anchor not in available_versions:
            continue
        nav_links.append(
            f'<a href="#{html.escape(anchor)}" title="{html.escape(description)}">{html.escape(label)}</a>'
        )

    columns = "\n".join(render_version_column(version) for version in versions)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Pipeline Version Scoreboard</title>
  <style>
    :root {{
      --bg: #0b0d12;
      --panel: #141821;
      --panel-2: #191f2b;
      --panel-3: #202838;
      --border: #2a3344;
      --text: #eef3fb;
      --muted: #9aa8bd;
      --accent: #8bd3ff;
      --high: #80f2b3;
      --good: #c7f279;
      --mid: #ffd46f;
      --low: #ff8d8d;
    }}
    * {{ box-sizing: border-box; }}
    html {{ scroll-behavior: smooth; }}
    body {{
      margin: 0;
      min-height: 100vh;
      font-family: ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: linear-gradient(180deg, #0a0c11 0%, #111722 100%);
      color: var(--text);
      overflow-x: hidden;
    }}
    a {{ color: var(--accent); text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .topbar {{
      position: sticky;
      top: 0;
      z-index: 20;
      display: grid;
      grid-template-columns: minmax(280px, 1fr) auto;
      gap: 16px;
      align-items: center;
      padding: 14px 18px;
      border-bottom: 1px solid var(--border);
      background: rgba(11, 13, 18, 0.94);
      backdrop-filter: blur(12px);
    }}
    .topbar h1 {{
      margin: 0 0 4px;
      font-size: 18px;
      letter-spacing: 0;
    }}
    .topbar p {{
      margin: 0;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.4;
    }}
    .group-nav {{
      display: flex;
      gap: 8px;
      max-width: min(70vw, 980px);
      overflow-x: auto;
      padding-bottom: 2px;
    }}
    .group-nav a {{
      flex: 0 0 auto;
      padding: 8px 10px;
      border: 1px solid var(--border);
      border-radius: 999px;
      background: rgba(32, 40, 56, 0.72);
      color: var(--text);
      font-size: 12px;
      font-weight: 650;
      white-space: nowrap;
    }}
    .board-wrap {{
      height: calc(100vh - 77px);
      overflow-x: auto;
      overflow-y: auto;
      scroll-padding-left: 18px;
    }}
    .board {{
      display: flex;
      gap: 14px;
      align-items: flex-start;
      width: max-content;
      min-width: 100%;
      padding: 16px 18px 28px;
    }}
    .version-column {{
      flex: 0 0 390px;
      width: 390px;
      min-height: calc(100vh - 125px);
      border: 1px solid var(--border);
      border-radius: 14px;
      background: linear-gradient(180deg, rgba(25, 31, 43, 0.98), rgba(18, 23, 32, 0.98));
      box-shadow: 0 18px 42px rgba(0, 0, 0, 0.24);
      overflow: hidden;
      scroll-margin-left: 18px;
    }}
    .version-header {{
      position: sticky;
      top: 0;
      z-index: 2;
      padding: 14px;
      border-bottom: 1px solid var(--border);
      background: rgba(20, 24, 33, 0.98);
    }}
    .version-kicker {{
      display: inline-flex;
      width: fit-content;
      margin-bottom: 8px;
      padding: 4px 8px;
      border-radius: 999px;
      background: #0d1118;
      color: var(--accent);
      font-size: 12px;
      font-weight: 750;
      letter-spacing: 0;
    }}
    .version-header h2 {{
      margin: 0;
      min-height: 42px;
      font-size: 15px;
      line-height: 1.35;
      letter-spacing: 0;
    }}
    .column-section {{
      padding: 14px;
      border-bottom: 1px solid var(--border);
    }}
    .column-section h3 {{
      margin: 0 0 10px;
      color: #d7e1ef;
      font-size: 12px;
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }}
    .metric-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
      margin-bottom: 12px;
    }}
    .metric-card {{
      min-height: 70px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      gap: 8px;
      padding: 10px;
      border: 1px solid var(--border);
      border-radius: 10px;
      background: rgba(11, 14, 20, 0.45);
    }}
    .metric-overall {{
      grid-column: 1 / -1;
      min-height: 58px;
      flex-direction: row;
      align-items: center;
    }}
    .metric-label {{
      color: var(--muted);
      font-size: 11px;
      line-height: 1.3;
    }}
    .score-pill {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: fit-content;
      min-width: 58px;
      padding: 4px 7px;
      border-radius: 999px;
      color: #071014;
      font-size: 12px;
      font-weight: 800;
      line-height: 1;
    }}
    .score-high {{ background: var(--high); }}
    .score-good {{ background: var(--good); }}
    .score-mid {{ background: var(--mid); }}
    .score-low {{ background: var(--low); }}
    .score-list {{
      display: grid;
      gap: 8px;
    }}
    .score-row {{
      padding: 10px;
      border: 1px solid var(--border);
      border-radius: 10px;
      background: rgba(14, 18, 26, 0.76);
    }}
    .score-row-top {{
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 10px;
    }}
    .site-label {{
      display: block;
      margin-bottom: 3px;
      color: var(--muted);
      font-size: 11px;
      text-transform: capitalize;
    }}
    .row-summary {{
      margin: 8px 0 0;
      color: var(--muted);
      font-size: 11px;
      line-height: 1.45;
    }}
    details {{
      margin-top: 8px;
    }}
    summary {{
      cursor: pointer;
      color: #cbd8e8;
      font-size: 12px;
      font-weight: 650;
    }}
    .detail-table {{
      width: 100%;
      margin-top: 8px;
      border-collapse: collapse;
      font-size: 11px;
      line-height: 1.35;
    }}
    .detail-table td {{
      vertical-align: top;
      padding: 6px;
      border: 1px solid var(--border);
    }}
    .detail-table td:nth-child(2) {{
      width: 66px;
    }}
    .scoreless ul {{
      margin: 8px 0 0;
      padding-left: 18px;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.5;
    }}
    .changes-section {{
      border-bottom: 0;
    }}
    .changes-copy {{
      color: #d4deec;
      font-size: 12px;
      line-height: 1.5;
    }}
    .changes-copy h1, .changes-copy h2, .changes-copy h3, .changes-copy h4 {{
      margin: 10px 0 6px;
      font-size: 13px;
      color: var(--text);
    }}
    .changes-copy h1:first-child, .changes-copy h2:first-child {{
      margin-top: 0;
    }}
    .changes-copy ul {{
      margin: 0;
      padding-left: 18px;
    }}
    .changes-copy li {{
      margin: 6px 0;
    }}
    code {{
      padding: 1px 4px;
      border-radius: 4px;
      background: rgba(139, 211, 255, 0.11);
      color: #bfeaff;
      font-size: 0.94em;
    }}
    .empty {{
      margin: 0;
      color: var(--muted);
      font-size: 12px;
    }}
    @media (max-width: 760px) {{
      .topbar {{
        grid-template-columns: 1fr;
      }}
      .group-nav {{
        max-width: calc(100vw - 36px);
      }}
      .board-wrap {{
        height: calc(100vh - 127px);
      }}
      .version-column {{
        flex-basis: min(360px, calc(100vw - 36px));
        width: min(360px, calc(100vw - 36px));
      }}
    }}
  </style>
</head>
<body>
  <header class="topbar">
    <div>
      <h1>Pipeline Version Scoreboard</h1>
      <p>{version_count} versions scanned, {scored_count} with scored review artifacts. Generated {html.escape(generated)} from local run files.</p>
    </div>
    <nav class="group-nav" aria-label="Version groups">
      {"".join(nav_links)}
    </nav>
  </header>
  <main class="board-wrap" id="board-wrap">
    <div class="board">
      {columns}
    </div>
  </main>
</body>
</html>
"""


def main() -> None:
    version_dirs = sorted(
        (path for path in RUNS_DIR.glob("v[0-9][0-9][0-9]") if path.is_dir()),
        key=lambda path: version_number(path.name),
        reverse=True,
    )
    versions = [collect_version(path) for path in version_dirs]
    OUTPUT_PATH.write_text(render_page(versions))
    print(f"wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
