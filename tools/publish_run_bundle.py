#!/usr/bin/env python3
"""Publish a brand run's FINAL results as a small, self-contained, tracked bundle.

`runs/` is gitignored (2.8 GB) and a single run carries node_modules, source
mirrors, per-page crops and full-resolution captures. None of that can be shared.
This script exports only the finished deliverables of one run into a browsable
directory that is committed to the repo and served as-is by the Studio server
(`studio_server.py` serves the repo root, so the bundle needs no new routes).

The bundle leads with the DELIVERABLE, not with the process: `index.html` is the
generated site itself, and every pipeline artifact sits one discreet footer link
away on `pipeline.html`. Nothing is dropped — only re-ordered.

What lands in the bundle:
  index.html   the generated site (the framework build), served as a real page
  pipeline.html  every artifact + the run's full gate-status disclosure
  replica/     the composed replica of the source page + its fidelity report
  harness/     the components/harness preview + the per-pattern layout pages
  catalog/     the component catalog page (when the run produced one)
  framework/   the framework build's own reports (the page itself is index.html)
  brand/       the authored brand facts (yaml/json) — the extraction deliverable
  logs/        run logs + manifest so a reader can see what passed
  assets/      ONE deduped copy of the media the pages above actually reference
  README.md    the artifact index, for readers on GitHub
  published.json  machine-readable manifest the Studio dashboard discovers

And beside the bundles, in `artifacts/published/`:
  index.html   the newest bundle's generated site, re-pathed to this depth
  brands.html  every published bundle, when a visitor wants a different one

The bundle is browsed locally: over the Studio, or straight off disk from
`file://`. There is no public deployment — see README.md for why.

Machine-local absolute paths are redacted out of everything textual on the way in
(logs and result JSON quote them freely), so the committed bundle names no one's
home directory. Only the prefix goes; the rest of each path is kept so it is still
a usable debugging reference.

Relocation is the interesting part: the run's pages reference media three
different ways (`assets/x.png` next to the page, `/runs/<run>/brand/assets/x.png`
absolute from the framework build, and `assets/x.png` from nested layout pages).
Every copied HTML/CSS file is rewritten to point at the single bundle-level
`assets/` dir via a relative path COMPUTED FROM WHERE THAT PAGE LANDS, so the
bundle browses identically over the Studio, over any static host, and from
`file://`. The generated site is written at two depths (bundle root and published
root); both are derived, never assumed.

Usage:
    ./venv/bin/python tools/publish_run_bundle.py --run runs/greenhouse-4
    ./venv/bin/python tools/publish_run_bundle.py --run runs/greenhouse-4 \
        --out artifacts/published/greenhouse-4 --base-url http://127.0.0.1:1500

Every page is loaded in headless Chromium afterwards (unless `--no-verify`): that
asserts each one renders content with no broken images or 404s, and produces the
details page's preview thumbnails. Pass `--base-url` to check it over the running
Studio instead of `file://`.

Re-runnable: managed subdirectories are replaced on each run, so a second
invocation over the same output dir is idempotent and drops stale files.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Subdirectories this script owns end-to-end: wiped and rewritten on every run so
# renames/removals upstream can never leave orphans in a published bundle.
# `previews/` is deliberately absent: it is owned by the verification pass, so a
# --no-verify re-export keeps the previews it cannot regenerate.
MANAGED_DIRS = ("assets", "replica", "harness", "catalog", "framework", "brand", "logs")

# Entry points, by role. The generated site owns `index.html` in the bundle AND in
# the published root; everything about how it was made lives on the details page.
SITE_PAGE = "index.html"
DETAILS_PAGE = "pipeline.html"
BRANDS_PAGE = "brands.html"

# Media referenced by the exported pages. Extensions only — names come from the
# pages themselves, never from a directory listing, so nothing unreferenced ships.
ASSET_EXTS = "png|jpe?g|webp|avif|gif|svg|ico|woff2?|ttf|otf|mp4|webm"

# A reference to `<anything>/assets/<name>.<ext>` that starts at an attribute or
# CSS-value boundary. The lookbehind keeps `https://cdn.example/assets/x.png`
# from matching mid-URL (its match would start after a `/`), and every candidate
# is additionally required to resolve to a real file in the run before rewriting.
ASSET_REF_RE = re.compile(
    r"""(?<=["'(\s=,])(?P<ref>/?(?:[\w.~%+-]+/)*assets/(?P<name>[\w.~%+-]+\.(?:"""
    + ASSET_EXTS
    + r""")))""",
    re.IGNORECASE,
)

# ── run status derivation ──────────────────────────────────────────────────────
# The orchestrator (brand_pipeline/pipeline_flow.py) logs one line when a gate
# starts and one when it resolves, and writes brand/flow-report.json when the run
# finishes. A published bundle has to carry that outcome, because artifacts alone
# look identical whether or not the run passed.
FLOW_GATE_START_RE = re.compile(r"^\[flow\]\s+(G\d+)\s+([\w-]+)\s*[.…]", re.M)
FLOW_GATE_RESULT_RE = re.compile(
    r"^\[flow\]\s+(G\d+)\s+(PASS|FAIL|BLOCKED|NEEDS_ITERATION|SKIP)\b[ \t]*(?:—[ \t]*(.*))?$", re.M
)
CRASH_RE = re.compile(r"^Traceback \(most recent call last\):", re.M)
ERROR_MSG_RE = re.compile(r"^\w*(?:Error|Exception):[ \t]*(.+)$", re.M)
RAISED_MSG_RE = re.compile(r"""raise \w*(?:Error|Exception)\([ \t]*["'](.+?)["']?[ \t]*$""", re.M)

# Scaffold defaults that must never survive into a published brand artifact. Kept
# deliberately narrow: broad words like "placeholder" are legitimate design-system
# vocabulary (input placeholder colors), so they would only produce noise.
SCAFFOLD_TOKENS = ("fieldnote", "lorem ipsum", "your brand here", "brand-name-here", "replace-me")

TEXT_SUFFIXES = {".html", ".htm", ".css", ".js", ".json", ".yaml", ".yml", ".md", ".log", ".sh", ".py", ".txt"}
PAGE_SUFFIXES = {".html", ".htm", ".css", ".js"}
DATA_SUFFIXES = {".json", ".yaml", ".yml"}

# Brand fact files, in the order a reader should meet them. (filename, blurb).
BRAND_FACTS = [
    ("brand.yaml", "Authored brand facts: tokens, surfaces, components, section patterns."),
    ("brand.md", "The same design system as a readable document."),
    ("layout-library.yaml", "Measured layout patterns (one entry per composable section shape)."),
    ("section-copy.yaml", "Verbatim copy captured per section."),
    ("media-assets.yaml", "Media registry: every asset with role, geometry and section binding."),
    ("brand-chrome.yaml", "Measured nav/footer facts (links are captured, never invented)."),
    ("style-scale.yaml", "Normalised type/space scales."),
    ("voice-facts.yaml", "Voice evidence extracted from the source copy."),
    ("voice.md", "Voice guidance derived from those facts."),
    ("assets-manifest.json", "Curated asset manifest (source URL → local file, with tags)."),
    ("media-guidance.yaml", "Art-direction guidance for generated media slots."),
]

# Fact files that live deeper in the run but belong with the rest. dest -> source.
BRAND_FACTS_NESTED = {
    "asset-placements.json": ("evidence/asset-placements.json", "Measured on-page placements for each asset."),
}


def size_of(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file())


def fmt_size(num_bytes: int) -> str:
    for unit, div in (("GB", 1 << 30), ("MB", 1 << 20), ("KB", 1 << 10)):
        if num_bytes >= div:
            return f"{num_bytes / div:.1f} {unit}"
    return f"{num_bytes} B"


class AssetPool:
    """Collects the media the exported pages reference into one deduped dir.

    Names are kept as-is (they are already content-prefixed by the extractor).
    A name that appears in several run-local asset dirs with DIFFERENT bytes gets
    a numeric suffix so nothing is silently overwritten.
    """

    def __init__(self, out_assets: Path, search_dirs: list[Path]):
        self.out_assets = out_assets
        self.search_dirs = [d for d in search_dirs if d.is_dir()]
        self.published: dict[str, str] = {}  # source path -> published filename
        self.missing: set[str] = set()

    def resolve(self, name: str, near: Path | None = None) -> str | None:
        """Copy `name` into the pool (once) and return its published filename."""
        candidates = []
        if near is not None:
            candidates.append(near / "assets" / name)
        candidates += [d / name for d in self.search_dirs]
        src = next((c for c in candidates if c.is_file()), None)
        if src is None:
            self.missing.add(name)
            return None
        key = str(src.resolve())
        if key in self.published:
            return self.published[key]
        dest_name = name
        i = 1
        while (self.out_assets / dest_name).exists():
            # Same name already published from a different source file.
            if (self.out_assets / dest_name).stat().st_size == src.stat().st_size and (
                self.out_assets / dest_name
            ).read_bytes() == src.read_bytes():
                break
            stem, ext = os.path.splitext(name)
            dest_name = f"{stem}~{i}{ext}"
            i += 1
        self.out_assets.mkdir(parents=True, exist_ok=True)
        if not (self.out_assets / dest_name).exists():
            shutil.copy2(src, self.out_assets / dest_name)
        self.published[key] = dest_name
        return dest_name

    @property
    def count(self) -> int:
        return len(set(self.published.values()))


def rewrite_asset_refs(text: str, page: Path, out_dir: Path, pool: AssetPool, near: Path | None) -> tuple[str, int]:
    """Repoint every resolvable `.../assets/<file>` reference at the bundle pool."""
    rel_prefix = os.path.relpath(out_dir / "assets", page.parent).replace(os.sep, "/")
    hits = 0

    def sub(m: re.Match[str]) -> str:
        nonlocal hits
        published = pool.resolve(m.group("name"), near=near)
        if published is None:
            return m.group("ref")
        hits += 1
        return f"{rel_prefix}/{published}"

    return ASSET_REF_RE.sub(sub, text), hits


def normalise_title(text: str, title: str) -> str:
    """Give a relocated page an honest <title> (Vite scaffolds keep a stale one).

    Still belt-and-braces after the framework scaffold learned to stamp its own
    brand title: already-generated runs on disk carry the old placeholder, and the
    lane title here ("<Brand> — composed replica") describes the page's role in the
    bundle, which the generators have no reason to know."""
    return re.sub(r"<title>.*?</title>", f"<title>{html.escape(title)}</title>", text, count=1, flags=re.S)


# Published bundles are a working record, not content anyone should find by search.
# There is no public deployment of them any more — they are browsed locally, over
# the Studio or straight off disk — so this tag no longer has a crawler to talk to.
# It is kept because it costs nothing and the repo itself is readable: if a bundle
# is ever served somewhere, it should not want to be indexed.
ROBOTS_META = '<meta name="robots" content="noindex, nofollow">'
HEAD_OPEN_RE = re.compile(r"<head\b[^>]*>", re.IGNORECASE)


def inject_noindex(text: str) -> str:
    """Add the robots meta right after <head>, idempotently."""
    if 'name="robots"' in text:
        return text
    match = HEAD_OPEN_RE.search(text)
    if not match:
        return text
    return f"{text[:match.end()]}\n{ROBOTS_META}{text[match.end():]}"


# ── machine-local paths ────────────────────────────────────────────────────────
# A run's logs and result JSON quote the absolute paths of the machine that
# produced them, and a published bundle is committed to a repo that other people
# read. Only the PREFIX has to go: `<repo>/runs/x/brand/…` still tells whoever is
# debugging exactly which file a line is about, so nothing diagnostic is lost.


def local_path_prefixes() -> list[tuple[str, str]]:
    """Absolute prefixes to redact, longest first so nesting resolves correctly."""
    candidates = [(str(REPO_ROOT), "<repo>"), (str(Path.home()), "<home>")]
    return sorted(
        ((prefix, token) for prefix, token in candidates if len(prefix) > 1),
        key=lambda kv: -len(kv[0]),
    )


def redact_local_paths(text: str) -> str:
    """Swap machine-local absolute path prefixes for stable placeholders.

    Substring replacement on purpose: it reaches paths wherever they appear — bare
    in a log line, inside a `file://` URL, or as a JSON string value — and the
    placeholders contain nothing that needs escaping, so JSON stays valid.
    """
    for prefix, token in local_path_prefixes():
        text = text.replace(prefix, token)
    return text


def copy_page(src: Path, dest: Path, out_dir: Path, pool: AssetPool, *, title: str | None = None) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    text = src.read_text(encoding="utf-8", errors="replace")
    text, _ = rewrite_asset_refs(text, dest, out_dir, pool, near=src.parent)
    if title:
        text = normalise_title(text, title)
    dest.write_text(redact_local_paths(inject_noindex(text)), encoding="utf-8")


def copy_plain(src: Path, dest: Path) -> bool:
    """Copy a file verbatim — unless it is text carrying machine-local paths."""
    if not src.is_file():
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    if src.suffix.lower() in TEXT_SUFFIXES:
        original = src.read_text(encoding="utf-8", errors="replace")
        redacted = redact_local_paths(original)
        # Only rewrite when there was something to redact, so a text file with odd
        # bytes is still copied byte-for-byte in the common case.
        if redacted != original:
            dest.write_text(redacted, encoding="utf-8")
            return True
    shutil.copy2(src, dest)
    return True


def _rel(path: Path, run_dir: Path) -> str:
    try:
        return path.relative_to(run_dir).as_posix()
    except ValueError:
        return path.name


def _read_flow_report(run_dir: Path, brand_dir: Path) -> tuple[dict | None, str | None]:
    """The orchestrator's own report, if it wrote one. Canonical locations only.

    Archived copies (e.g. `_archive/<something>/flow-report.json` carried over from
    another run) are deliberately NOT accepted: a report from a different run would
    turn a crashed flow into a fake pass.
    """
    for candidate in (brand_dir / "flow-report.json", run_dir / "flow-report.json"):
        if candidate.is_file():
            try:
                return json.loads(candidate.read_text()), _rel(candidate, run_dir)
            except Exception as exc:  # noqa: BLE001
                return None, f"{_rel(candidate, run_dir)} (unreadable: {exc})"
    return None, None


def _crash_reason(text: str) -> str:
    """Best short description of a crash, preferring the innermost raised message."""
    outer = ERROR_MSG_RE.search(text)
    raised = RAISED_MSG_RE.findall(text)
    parts = []
    if outer:
        first = outer.group(1).split("Traceback (most recent call last)")[0]
        parts.append(first.strip().rstrip(":").strip()[:200])
    if raised:
        parts.append(raised[-1].strip().rstrip(":").strip()[:200])
    return " — ".join(dict.fromkeys(p for p in parts if p))


def _parse_flow_logs(run_dir: Path) -> dict:
    """Derive the gate outcome from the flow log(s) when there is no flow report.

    Returns `{"determined": bool, "state": ..., "gate", "gate_name", "reason",
    "source"}`. A log that only shows gates PASSING is NOT treated as a completed
    run: the spine length is not knowable from the log, so absence of a failure is
    never read as success.
    """
    logs = sorted(run_dir.glob("*flow*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    for log in logs:
        text = log.read_text(errors="replace")
        started = FLOW_GATE_START_RE.findall(text)
        results = FLOW_GATE_RESULT_RE.findall(text)
        failed = next((r for r in results if r[1] in ("FAIL", "BLOCKED", "NEEDS_ITERATION")), None)
        # Sources are cited at their path INSIDE the bundle (run logs are copied to
        # logs/), so a reader of the landing page can click through to the evidence.
        if CRASH_RE.search(text) or ERROR_MSG_RE.search(text):
            gate, gate_name = started[-1] if started else ("", "")
            return {
                "determined": True,
                "state": "crashed",
                "gate": gate,
                "gate_name": gate_name,
                "reason": _crash_reason(text),
                "source": f"logs/{log.name}",
                "run_path": _rel(log, run_dir),
            }
        if failed:
            return {
                "determined": True,
                "state": "blocked",
                "gate": failed[0],
                "gate_name": "",
                "reason": (failed[2] or "").strip(),
                "source": f"logs/{log.name}",
                "run_path": _rel(log, run_dir),
            }
    return {
        "determined": False,
        "state": "undetermined",
        "gate": "",
        "gate_name": "",
        "reason": "",
        "source": ", ".join(f"logs/{p.name}" for p in logs),
        "run_path": ", ".join(_rel(p, run_dir) for p in logs),
    }


def derive_run_status(run_dir: Path, brand_dir: Path, meta: dict, replica_report: dict) -> dict:
    """Read the run's REAL outcome off disk, for disclosure on the bundle page.

    Sources, in order of authority: `brand/flow-report.json` (the orchestrator's own
    record) → the flow log(s) → the replica report beside the published page. The run
    `manifest.json` is never treated as authoritative for status or score; it is only
    compared, so a stale or over-optimistic manifest surfaces as a disagreement
    instead of silently setting the headline.

    Verdict is one of `passed` / `not-passed` / `undetermined`. `undetermined` is used
    whenever the evidence does not support a conclusion — absence of a recorded
    failure is never read as a pass.
    """
    run_manifest = meta.get("manifest") or {}
    report, report_path = _read_flow_report(run_dir, brand_dir)
    facts: list[dict] = []

    if report:
        gate_state = "completed" if (report.get("ok") and report.get("status") == "completed") else "blocked"
        gate = {
            "determined": True,
            "state": gate_state,
            "gate": report.get("blockedGate") or "",
            "gate_name": "",
            "reason": next(
                (g.get("reason", "") for g in report.get("gates", []) if not g.get("ok")), ""
            ),
            "source": report_path or "flow-report.json",
        }
        cleared = [g.get("gate") for g in report.get("gates", []) if g.get("ok")]
        if gate_state == "completed":
            facts.append(
                {
                    "text": f"The orchestrator completed and cleared every gate ({', '.join(cleared) or 'none recorded'}).",
                    "source": gate["source"],
                }
            )
        else:
            blocked = gate["gate"] or "an unnamed gate"
            facts.append(
                {
                    "text": f"The orchestrator stopped at gate {blocked}"
                    + (f": {gate['reason']}" if gate["reason"] else "."),
                    "source": gate["source"],
                }
            )
    else:
        gate = _parse_flow_logs(run_dir)
        facts.append(
            {
                "text": "The orchestrator writes a flow report when it finishes its gate spine, and this run "
                "has none — so the run never reached the end of that spine.",
                "source": "brand/flow-report.json (missing)",
            }
        )
        if gate["state"] == "crashed":
            where = f"gate {gate['gate']}" + (f" ({gate['gate_name']})" if gate["gate_name"] else "")
            facts.append(
                {
                    "text": f"The last recorded flow run crashed at {where}"
                    + (f": {gate['reason']}." if gate["reason"] else "."),
                    "source": gate["source"],
                }
            )
        elif gate["state"] == "blocked":
            facts.append(
                {
                    "text": f"The last recorded flow run was blocked at gate {gate['gate']}"
                    + (f": {gate['reason']}." if gate["reason"] else "."),
                    "source": gate["source"],
                }
            )
        else:
            facts.append(
                {
                    "text": "Gate status could not be determined from run logs — no flow log records a gate "
                    "outcome, and no conclusion is drawn from that absence.",
                    "source": gate["source"] or "no flow log found",
                }
            )

    # Replica fidelity: the report beside the published page, against whichever bar
    # the run declared. No bar on disk means no pass/fail claim about fidelity.
    overall = replica_report.get("overall")
    bar = (report or {}).get("replicaBar")
    bar_source = report_path if bar is not None else None
    if bar is None:
        bar = (run_manifest.get("replica") or {}).get("bar")
        bar_source = "manifest.json (declared bar)" if bar is not None else None
    fidelity = {"overall": overall, "bar": bar, "bar_source": bar_source, "meets_bar": None, "bands_below_bar": []}
    if overall is not None and bar is not None:
        fidelity["meets_bar"] = overall >= bar
        facts.append(
            {
                "text": f"Replica fidelity is {overall} against this run's {bar:.2f} bar"
                + (" — the bar is met." if fidelity["meets_bar"] else " — below the bar."),
                "source": "replica/replica-report.json",
            }
        )
    elif overall is not None:
        facts.append(
            {
                "text": f"Replica fidelity is {overall}; the run declares no bar to compare it against.",
                "source": "replica/replica-report.json",
            }
        )
    if overall is not None and bar is not None and not fidelity["meets_bar"]:
        scored = [b for b in replica_report.get("bands", []) if isinstance(b.get("score"), (int, float))]
        # A band whose source height is 0 has nothing to diff against, so its score is
        # an artifact of the pairing rather than a fidelity signal. Counted, not ranked.
        unmeasurable = [b for b in scored if not (b.get("srcHeight") or 0) > 0]
        weak = sorted((b for b in scored if b["score"] < bar and b not in unmeasurable), key=lambda b: b["score"])
        fidelity["bands_below_bar"] = [
            {
                "id": b.get("id", ""),
                "label": (b.get("label") or "").split("—")[0].strip() or b.get("id", ""),
                "score": b["score"],
            }
            for b in weak
        ]
        fidelity["bands_unmeasurable"] = [b.get("id", "") for b in unmeasurable]
        worst = ", ".join(f"{b['label'] or b['id']} {b['score']}" for b in fidelity["bands_below_bar"][:3])
        if worst:
            facts.append(
                {
                    "text": f"The gate did flag the weakest sections numerically: {worst}. Low band scores are "
                    "where the composed page diverges most from the source"
                    + (
                        f" ({len(unmeasurable)} band"
                        + (" with" if len(unmeasurable) == 1 else "s with")
                        + " no measurable source height "
                        + ("is" if len(unmeasurable) == 1 else "are")
                        + " left out of this list)."
                        if unmeasurable
                        else "."
                    ),
                    "source": "replica/replica-report.md",
                }
            )

    # The run manifest is compared, never trusted.
    disagreements: list[str] = []
    claims_done = run_manifest.get("status") == "completed" or run_manifest.get("pipeline_run_completed") is True
    if claims_done and gate["state"] != "completed":
        disagreements.append(
            f'the run manifest records status "{run_manifest.get("status")}" / '
            f"pipeline_run_completed {json.dumps(run_manifest.get('pipeline_run_completed'))}, "
            "which the gate evidence above does not support"
        )
    manifest_overall = (run_manifest.get("replica") or {}).get("overall")
    if overall is not None and manifest_overall is not None and abs(manifest_overall - overall) > 1e-4:
        disagreements.append(
            f"the manifest's replica score ({manifest_overall}) predates the replica that is published here "
            f"({overall} in the report beside the page)"
        )
    if disagreements:
        facts.append(
            {
                "text": "Do not trust the run manifest over the report beside the page: "
                + "; and ".join(disagreements)
                + ".",
                "source": "logs/manifest.json",
            }
        )

    # Any gate artifact that carries its own verdict, reported as-is.
    quality = brand_dir / "harness" / "harness-quality.json"
    if quality.is_file():
        try:
            qdata = json.loads(quality.read_text())
        except Exception:  # noqa: BLE001
            qdata = {}
        if "ok" in qdata:
            flow_log = run_dir / (gate.get("run_path") or "")
            newer = flow_log.is_file() and quality.stat().st_mtime > flow_log.stat().st_mtime
            facts.append(
                {
                    "text": f"The harness quality artifact on disk reports ok={json.dumps(qdata['ok'])}"
                    + (
                        " — it was written after the flow log above, so it reflects a later rebuild "
                        "rather than a passing flow run."
                        if newer
                        else "."
                    ),
                    "source": "harness/harness-quality.json",
                }
            )

    failed_fidelity = fidelity["meets_bar"] is False
    if gate["state"] == "completed" and not failed_fidelity:
        verdict = "passed"
        headline = (
            "This run passed its own quality gates. The artifacts below are the output of that "
            "passing run, published for browsing and review."
        )
    elif gate["state"] in ("crashed", "blocked") or failed_fidelity:
        verdict = "not-passed"
        headline = (
            "This run did not pass its own quality gates. The artifacts below are its current best "
            "output, published for browsing and review — not a certified-good build."
        )
    else:
        verdict = "undetermined"
        headline = (
            "Whether this run passed its own quality gates could not be determined from what is on "
            "disk. Treat the artifacts below as unverified output, published for browsing and review."
        )

    return {
        "verdict": verdict,
        "headline": headline,
        "flow_report": {"present": report is not None, "path": report_path},
        "gate_outcome": gate,
        "fidelity": fidelity,
        "manifest_disagreements": disagreements,
        "facts": facts,
    }


def scan_foreign_strings(out_dir: Path, brand: str, run_name: str) -> list[dict]:
    """Report scaffold defaults and other brands' names surviving in the bundle.

    Cross-brand leakage has shipped before (a foreign hero offset, a scaffold page
    title), so a published bundle is scanned for: the scaffold placeholder tokens
    above, and the names of the OTHER runs in this repo. Matches are classified, not
    judged — `page` hits in visible markup matter, hits inside a media filename or a
    changelog usually do not — and nothing is rewritten here: content fixes belong to
    whichever generator emitted the string.
    """
    brand_words = {w for w in re.split(r"[^a-z0-9]+", f"{brand} {run_name}".lower()) if len(w) > 2}
    tokens = set(SCAFFOLD_TOKENS)
    runs_root = REPO_ROOT / "runs"
    if runs_root.is_dir():
        for run in runs_root.iterdir():
            if not run.is_dir() or run.name.startswith(".") or run.name == run_name:
                continue
            token = re.sub(r"[-_]?v?\d+$", "", run.name.lower())
            if token and len(token) > 3 and token not in brand_words:
                tokens.add(token)
    # Media file names carry third-party brands legitimately (a customer logo), and
    # the generated apps refer to the same files by id — the name minus extension and
    # minus the curation index prefix. All three spellings count as "asset name".
    asset_names: set[str] = set()
    for asset in (out_dir / "assets").glob("*"):
        stem = asset.stem.lower()
        asset_names.update({asset.name.lower(), stem, re.sub(r"^\d+-", "", stem)})
    # The bundle's own generated entry points are skipped: their content is derived
    # from the payload (published.json even carries these findings), so including them
    # would just report the report.
    generated = {DETAILS_PAGE, "README.md", "published.json", "verify.json"}
    findings: list[dict] = []
    for path in sorted(out_dir.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if path.parent == out_dir and path.name in generated:
            continue
        text = path.read_text(errors="replace")
        comments = [
            (m.start(), m.end())
            for m in re.finditer(r"/\*.*?\*/|<!--.*?-->", text, re.S)
        ]
        for token in sorted(tokens):
            for m in re.finditer(rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])", text, re.I):
                run_of_path = re.search(r"[\w.~%+-]*$", text[max(0, m.start() - 120) : m.start()]).group(0) + re.match(
                    r"[\w.~%+-]*", text[m.start() :]
                ).group(0)
                near = run_of_path.lower()
                # Only a match embedded in a longer file-name-ish run counts as an asset
                # name; a bare word in prose ("Remote's spacing rung") must not be
                # excused just because some media file happens to contain it.
                kind = (
                    "asset-name"
                    if len(near) > len(token) and any(name in near or near in name for name in asset_names)
                    else "page"
                    if path.suffix.lower() in PAGE_SUFFIXES
                    else "data"
                    if path.suffix.lower() in DATA_SUFFIXES
                    else "provenance"
                )
                findings.append(
                    {
                        "token": token,
                        "file": str(path.relative_to(out_dir)),
                        "kind": kind,
                        "in_comment": any(start <= m.start() < end for start, end in comments),
                        "context": " ".join(text[max(0, m.start() - 60) : m.start() + 60].split())[:140],
                    }
                )
    return findings


def report_foreign_strings(findings: list[dict]) -> None:
    """Print the cross-brand / scaffold scan, loudest category first.

    Nothing here fails the export: a hit in a changelog is expected provenance, and a
    hit in rendered markup needs a generator-side fix that this script must not make.
    """
    if not findings:
        print("  foreign strings: none found (scaffold defaults, other run names)")
        return
    order = {"page": 0, "data": 1, "asset-name": 2, "provenance": 3}
    groups: dict[tuple, list[dict]] = {}
    for f in findings:
        groups.setdefault((f["kind"], f["in_comment"], f["token"]), []).append(f)
    print(f"  foreign strings: {len(findings)} match(es) in {len({f['file'] for f in findings})} file(s) — review only:")
    for (kind, in_comment, token), hits in sorted(
        groups.items(), key=lambda kv: (order.get(kv[0][0], 9), -len(kv[1]))
    ):
        files = sorted({h["file"] for h in hits})
        shown = ", ".join(files[:3]) + (f" +{len(files) - 3} more" if len(files) > 3 else "")
        print(f"    [{kind}{' comment' if in_comment else ''}] '{token}' ×{len(hits)} in {shown}")
        print(f"      {hits[0]['context']}")


def load_run_meta(run_dir: Path) -> dict:
    meta: dict = {"name": run_dir.name}
    for fname, keys in (("manifest.json", None), ("studio-project.json", None)):
        path = run_dir / fname
        if not path.is_file():
            continue
        try:
            meta[fname.split(".")[0]] = json.loads(path.read_text())
        except Exception as exc:  # noqa: BLE001
            print(f"  warn: could not parse {fname}: {exc}")
    manifest = meta.get("manifest", {})
    project = meta.get("studio-project", {})
    meta["brand"] = manifest.get("brand") or project.get("title") or run_dir.name
    meta["title"] = project.get("title") or meta["brand"]
    meta["source_url"] = manifest.get("source_url") or project.get("url") or ""
    return meta


def export(run_dir: Path, out_dir: Path) -> dict:
    brand_dir = run_dir / "brand"
    if not brand_dir.is_dir():
        raise SystemExit(f"no brand dir under {run_dir} — is this a brand run?")

    meta = load_run_meta(run_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for name in MANAGED_DIRS:
        shutil.rmtree(out_dir / name, ignore_errors=True)

    pool = AssetPool(
        out_dir / "assets",
        [
            brand_dir / "assets",
            brand_dir / "harness" / "layouts" / "assets",
            brand_dir / "compose" / "replica" / "assets",
        ],
    )
    lanes: list[dict] = []
    replica_report: dict = {}

    # ── replica: the composed rebuild of the source page, plus its fidelity proof
    replica_src = brand_dir / "compose" / "replica"
    if (replica_src / "index.html").is_file():
        copy_page(
            replica_src / "index.html",
            out_dir / "replica" / "index.html",
            out_dir,
            pool,
            title=f"{meta['brand']} — composed replica",
        )
        for name in (
            "replica-report.md",
            "replica-report.json",
            "replica-rects.json",
            "composition.json",
            "tokens.manifest.json",
            "replica-fullpage.png",
        ):
            copy_plain(replica_src / name, out_dir / "replica" / name)
        for diff in sorted((replica_src / "diff").glob("*.png")):
            copy_plain(diff, out_dir / "replica" / "diff" / diff.name)
        # The report next to the page is the truth for the page being published;
        # the run manifest can predate a later replica rebuild.
        try:
            replica_report = json.loads((replica_src / "replica-report.json").read_text())
        except Exception:  # noqa: BLE001
            replica_report = {}
        report = replica_report
        lanes.append(
            {
                "kind": "replica",
                "label": "Composed replica of the source page",
                "path": "replica/index.html",
                "note": (
                    f"Rebuilt from the extracted facts alone. Fidelity score "
                    f"{report.get('overall', '—')} against the source capture; per-band "
                    "scores and the punch list are in replica-report.md."
                ),
                "extras": [
                    {"label": "Fidelity report (markdown)", "path": "replica/replica-report.md"},
                    {"label": "Full-page render (PNG)", "path": "replica/replica-fullpage.png"},
                ],
            }
        )

    # ── harness: every composable pattern rendered on its own, plus the index
    harness_src = brand_dir / "harness"
    if (harness_src / "index.html").is_file():
        copy_page(
            harness_src / "index.html",
            out_dir / "harness" / "index.html",
            out_dir,
            pool,
            title=f"{meta['brand']} — components & layout harness",
        )
        for layout in sorted((harness_src / "layouts").glob("*.html")):
            copy_page(layout, out_dir / "harness" / "layouts" / layout.name, out_dir, pool)
        for name in ("harness-quality.json", "tokens.manifest.json"):
            copy_plain(harness_src / name, out_dir / "harness" / name)
        lanes.append(
            {
                "kind": "harness",
                "label": "Components & layout harness",
                "path": "harness/index.html",
                "note": (
                    "Primitives, surfaces, blocks and every measured layout pattern rendered "
                    "from the design system. Each pattern is also a standalone page under "
                    "harness/layouts/."
                ),
            }
        )

    # ── catalog: the component catalog page, when the run built one
    catalog_src = brand_dir / "catalog"
    if (catalog_src / "index.html").is_file():
        copy_page(
            catalog_src / "index.html",
            out_dir / "catalog" / "index.html",
            out_dir,
            pool,
            title=f"{meta['brand']} — component catalog",
        )
        copy_plain(catalog_src / "catalog.json", out_dir / "catalog" / "catalog.json")
        lanes.append(
            {
                "kind": "catalog",
                "label": "Component catalog",
                "path": "catalog/index.html",
                "note": "Machine-readable inventory of the components the extraction declared.",
            }
        )

    # ── framework: the built React app — the bundle's front page.
    # It lands at the bundle ROOT (index.html), not under framework/, so a visitor
    # opening the bundle sees the generated site and nothing else. Its own reports
    # still travel under framework/. Prefer the app's own dist/ over any copy.
    fw_src = brand_dir / "framework"
    fw_build = next(
        (
            p
            for p in (
                *sorted(fw_src.glob("single/*/dist/index.html")),
                fw_src / "index.html",
            )
            if p.is_file()
        ),
        None,
    )
    site: dict | None = None
    if fw_build is not None:
        # Depth changed (framework/index.html -> index.html), so the asset prefix is
        # re-derived by copy_page from the destination — never carried over.
        # Title is the brand alone: this page is the site, so it should not announce
        # its own lane the way the review pages under the details page do.
        copy_page(fw_build, out_dir / SITE_PAGE, out_dir, pool, title=meta["brand"])
        copy_plain(fw_src / "framework-report.json", out_dir / "framework" / "framework-report.json")
        copy_plain(fw_src / "brand-assets.json", out_dir / "framework" / "brand-assets.json")
        site = {
            "kind": "framework",
            "path": SITE_PAGE,
            "source": str(fw_build.relative_to(REPO_ROOT)) if fw_build.is_relative_to(REPO_ROOT) else str(fw_build),
        }
        lanes.append(
            {
                "kind": "framework",
                "label": "Generated site (React + Vite)",
                "path": SITE_PAGE,
                "note": (
                    "The framework lane: a real React + Tailwind app generated from the "
                    "same facts, built to one self-contained HTML file. It is this bundle's "
                    f"front page. Source stays in the run dir ({fw_build.parent.parent.relative_to(REPO_ROOT)})."
                ),
            }
        )

    # ── brand facts: the actual output of the extraction
    facts: list[dict] = []
    for name, blurb in BRAND_FACTS:
        if copy_plain(brand_dir / name, out_dir / "brand" / name):
            facts.append({"path": f"brand/{name}", "note": blurb})
    for dest, (rel, blurb) in BRAND_FACTS_NESTED.items():
        if copy_plain(brand_dir / rel, out_dir / "brand" / dest):
            facts.append({"path": f"brand/{dest}", "note": blurb})

    # ── provenance: logs, manifest, and the scripts that produced the run
    logs: list[dict] = []
    for log in sorted(run_dir.glob("*.log")):
        if copy_plain(log, out_dir / "logs" / log.name):
            logs.append({"path": f"logs/{log.name}"})
    for name in ("manifest.json", "changes.md", "extract_pages.sh", "build_framework_lane.py"):
        copy_plain(run_dir / name, out_dir / "logs" / name)

    manifest = {
        "schemaVersion": "published-bundle.v1",
        "name": out_dir.name,
        "run": str(run_dir.relative_to(REPO_ROOT)) if run_dir.is_relative_to(REPO_ROOT) else str(run_dir),
        "brand": meta["brand"],
        "title": meta["title"],
        "source_url": meta["source_url"],
        "published_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "replica_overall": replica_report.get("overall"),
        "status": derive_run_status(run_dir, brand_dir, meta, replica_report),
        # What a visitor lands on, and where the process lives. `site` is null when
        # the run produced no generated site — then the details page IS the front
        # page, so a bundle without a framework lane still opens to something.
        "site": site,
        "details": DETAILS_PAGE,
        "lanes": lanes,
        "facts": facts,
        "logs": logs,
        "assets_published": pool.count,
        "assets_unresolved": sorted(pool.missing),
        "foreign_strings": scan_foreign_strings(out_dir, meta["brand"], run_dir.name),
        "run_manifest": meta.get("manifest", {}),
    }
    finalize(manifest, out_dir)
    return manifest


def finalize(manifest: dict, out_dir: Path) -> None:
    """(Re)write the human + machine entry points once the payload is final.

    `index.html` is the generated site, already copied by export() at this depth —
    finalize only stamps its provenance footer, which is why re-running is safe.
    When the run produced no site, the details page takes the front-page slot so a
    bundle never opens to a 404.
    """
    manifest["bytes"] = size_of(out_dir)
    details = redact_local_paths(render_landing(manifest, out_dir))
    (out_dir / DETAILS_PAGE).write_text(details)
    site_page = out_dir / SITE_PAGE
    if manifest.get("site") and site_page.is_file():
        site_page.write_text(
            stamp_provenance(site_page.read_text(encoding="utf-8"), provenance_footer(manifest, DETAILS_PAGE)),
            encoding="utf-8",
        )
    else:
        site_page.write_text(details)
    (out_dir / "README.md").write_text(redact_local_paths(render_readme(manifest, out_dir)))
    # The manifest embeds the run's own manifest.json, which can quote local paths.
    (out_dir / "published.json").write_text(redact_local_paths(json.dumps(manifest, indent=2) + "\n"))
    write_published_index(out_dir.parent)


# ── landing page ───────────────────────────────────────────────────────────────

LANDING_CSS = """
:root { color-scheme: dark; --bg:#0b0b0d; --card:#14141a; --line:#26262f; --ink:#f4f4f5;
        --muted:#a1a1aa; --accent:#34d399; }
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--ink); font:15px/1.6 ui-sans-serif,-apple-system,"Segoe UI",Inter,sans-serif; }
.wrap { max-width: 1040px; margin: 0 auto; padding: 48px 24px 72px; }
h1 { font-size: 30px; letter-spacing:-.02em; margin: 0 0 6px; }
h2 { font-size: 13px; text-transform: uppercase; letter-spacing:.12em; color:var(--muted); margin: 40px 0 14px; font-weight:600; }
a { color: var(--accent); }
.sub { color: var(--muted); margin: 0 0 4px; }
.grid { display:grid; gap:16px; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); }
.card { background:var(--card); border:1px solid var(--line); border-radius:14px; overflow:hidden; display:flex; flex-direction:column; }
.card .shot { display:block; background:#000; aspect-ratio: 16/10; object-fit: cover; object-position: top center; width:100%; border-bottom:1px solid var(--line); }
.card .body { padding:16px 18px 18px; }
.card h3 { margin:0 0 6px; font-size:16px; }
.card h3 a { text-decoration:none; }
.card p { margin:0; color:var(--muted); font-size:13px; }
.chip { display:inline-block; font-size:10px; letter-spacing:.1em; text-transform:uppercase; color:#0b0b0d;
        background:var(--accent); border-radius:999px; padding:2px 8px; margin-bottom:10px; font-weight:700; }
.extras { margin:10px 0 0; padding:0; list-style:none; font-size:12px; }
.extras li { margin-top:4px; }
table { width:100%; border-collapse:collapse; font-size:13px; }
th, td { text-align:left; padding:8px 10px; border-bottom:1px solid var(--line); vertical-align:top; }
th { color:var(--muted); font-weight:600; font-size:11px; text-transform:uppercase; letter-spacing:.08em; }
td code { color:var(--ink); }
.meta { display:flex; flex-wrap:wrap; gap:8px 20px; color:var(--muted); font-size:13px; margin:14px 0 0; }
.status { margin:26px 0 0; padding:18px 20px; border-radius:14px; background:#16161c;
          border:1px solid var(--line); border-left:4px solid var(--st); }
.status.warn { --st:#d99a34; } .status.ok { --st:#34d399; } .status.unknown { --st:#8b8b96; }
.status .kicker { font-size:11px; text-transform:uppercase; letter-spacing:.12em; color:var(--st); font-weight:700; }
.status .headline { margin:6px 0 0; font-size:15px; font-weight:600; color:var(--ink); }
.status ul { margin:12px 0 0; padding:0 0 0 18px; font-size:13px; color:#d4d4d8; }
.status li { margin-top:7px; }
.status .src { color:#71717a; font-size:11px; font-family:ui-monospace,SFMono-Regular,Menlo,monospace; }
.note { color:var(--muted); font-size:13px; max-width:70ch; }
.backlinks { margin:0 0 20px; font-size:13px; display:flex; gap:18px; flex-wrap:wrap; }
footer { margin-top:48px; color:#71717a; font-size:12px; }
"""


def _e(text) -> str:
    return html.escape(str(text if text is not None else ""))


_STATUS_STYLE = {
    "passed": ("ok", "Run status — gates passed"),
    "not-passed": ("warn", "Run status — gates not passed"),
    "undetermined": ("unknown", "Run status — undetermined"),
}


# ── the generated site's one line of provenance ────────────────────────────────
# The published site leads with the deliverable, so the whole pipeline is
# represented on it by exactly this: one sentence and a link. It states what the
# run's gates said in a single clause and never implies the build is certified;
# the full, unabridged disclosure lives on the details page it links to, where it
# is rendered exactly as it always was.
PROVENANCE_ID = "published-provenance"
PROVENANCE_RE = re.compile(rf'\s*<footer id="{PROVENANCE_ID}".*?</footer>', re.S)
BODY_CLOSE_RE = re.compile(r"</body\s*>", re.IGNORECASE)

PROVENANCE_LEAD = {
    "passed": "Generated automatically from measurements of {source}. The run passed its own quality gates.",
    "not-passed": "Generated automatically from measurements of {source}. The run did not pass its own quality gates.",
    "undetermined": "Generated automatically from measurements of {source}. Whether the run passed its own "
    "quality gates could not be determined.",
}

# Single-quoted font name on purpose: this whole string is an HTML style="…"
# attribute value, so a double quote inside it would terminate the attribute.
_PROV_BOX = (
    "margin:0;padding:16px 20px;background:#0b0b0d;color:#8b8b96;border-top:1px solid #26262f;"
    "font:400 12px/1.7 ui-sans-serif,-apple-system,'Segoe UI',Inter,sans-serif;text-align:center;"
)
_PROV_LINK = "color:#a1a1aa;text-decoration:underline;text-underline-offset:2px;"

# The footer is appended AFTER the app's own markup, which means the app's mount
# node has to size to its content or the footer lands mid-document under it. Vite
# scaffolds routinely pin that node to the viewport height (`#root{height:100%}`)
# and let the app overflow it visibly, which looks fine until something follows it.
# `min-height` keeps the fill-the-viewport intent for a short page. Carried inside
# the footer element so removing the footer removes the rule with it.
_PROV_RESET = f"body>:not(#{PROVENANCE_ID}){{height:auto;min-height:100vh}}"


def provenance_footer(manifest: dict, details_href: str, brands_href: str | None = None) -> str:
    """The single line of process the clean site carries, plus its way in."""
    verdict = (manifest.get("status") or {}).get("verdict", "")
    source = manifest.get("source_url") or ""
    lead = PROVENANCE_LEAD.get(verdict, PROVENANCE_LEAD["undetermined"]).format(source=source or "a source site")
    links = f'<a href="{_e(details_href)}" style="{_PROV_LINK}">Pipeline details</a>'
    if brands_href:
        links += f' · <a href="{_e(brands_href)}" style="{_PROV_LINK}">All published brands</a>'
    return (
        f'\n<footer id="{PROVENANCE_ID}" style="{_PROV_BOX}">'
        f"<style>{_PROV_RESET}</style>{_e(lead)} {links}</footer>\n"
    )


def stamp_provenance(text: str, footer: str) -> str:
    """Put (or replace) the provenance footer just before </body>. Idempotent."""
    text = PROVENANCE_RE.sub("", text)
    closes = list(BODY_CLOSE_RE.finditer(text))
    if not closes:
        return text + footer
    cut = closes[-1].start()
    return text[:cut] + footer + text[cut:]


def repoint_assets(text: str, assets_dir: Path, page: Path) -> tuple[str, int]:
    """Repoint every `.../assets/<file>` reference at `assets_dir`, from `page`.

    Used when an already-exported page is written out again at a DIFFERENT depth
    (the generated site is served both at the bundle root and at the published
    root). The prefix is derived from where the page lands, and a reference only
    moves when the file it names really exists in that pool — so an external URL,
    or a name that is not ours, is left exactly as it was.
    """
    prefix = os.path.relpath(assets_dir, page.parent).replace(os.sep, "/")
    hits = 0

    def sub(m: re.Match[str]) -> str:
        nonlocal hits
        if not (assets_dir / m.group("name")).is_file():
            return m.group("ref")
        hits += 1
        return f"{prefix}/{m.group('name')}"

    return ASSET_REF_RE.sub(sub, text), hits


def render_status_html(status: dict) -> str:
    """The provenance block: what the run's own gates actually said.

    Placed above the artifact links, because the artifacts look the same whether or
    not the run passed. Factual and calm by design — this is a disclosure, not a
    warning banner.
    """
    if not status:
        return ""
    css_class, kicker = _STATUS_STYLE.get(status.get("verdict", ""), _STATUS_STYLE["undetermined"])
    items = "".join(
        f'<li>{_e(f["text"])} <span class="src">{_e(f.get("source", ""))}</span></li>'
        for f in status.get("facts", [])
    )
    return (
        f'<section class="status {css_class}">'
        f'<div class="kicker">{_e(kicker)}</div>'
        f'<p class="headline">{_e(status.get("headline", ""))}</p>'
        + (f"<ul>{items}</ul>" if items else "")
        + "</section>"
    )


def render_status_markdown(status: dict) -> list[str]:
    if not status:
        return []
    _, kicker = _STATUS_STYLE.get(status.get("verdict", ""), _STATUS_STYLE["undetermined"])
    lines = [f"## {kicker}", "", status.get("headline", ""), ""]
    for fact in status.get("facts", []):
        source = fact.get("source", "")
        lines.append(f"- {fact['text']}" + (f" (`{source}`)" if source else ""))
    lines.append("")
    return lines


def render_landing(manifest: dict, out_dir: Path) -> str:
    """The details page: every artifact, and the run's full status disclosure.

    This is what used to be the bundle's front page. Nothing was removed from it —
    it simply moved behind the generated site, which now owns `index.html`.
    """
    rm = manifest.get("run_manifest") or {}
    replica = manifest.get("replica_overall")
    validation = rm.get("validation") or {}
    cards = []
    for lane in manifest["lanes"]:
        shot = out_dir / "previews" / f"{lane['kind']}.png"
        img = (
            f'<img class="shot" src="previews/{lane["kind"]}.png" alt="{_e(lane["label"])} preview" loading="lazy">'
            if shot.is_file()
            else ""
        )
        extras = "".join(
            f'<li><a href="{_e(x["path"])}">{_e(x["label"])}</a></li>' for x in lane.get("extras", [])
        )
        cards.append(
            f'<article class="card">{img}<div class="body">'
            f'<span class="chip">{_e(lane["kind"])}</span>'
            f'<h3><a href="{_e(lane["path"])}">{_e(lane["label"])} →</a></h3>'
            f'<p>{_e(lane.get("note", ""))}</p>'
            + (f'<ul class="extras">{extras}</ul>' if extras else "")
            + "</div></article>"
        )
    fact_rows = "".join(
        f'<tr><td><a href="{_e(f["path"])}"><code>{_e(Path(f["path"]).name)}</code></a></td>'
        f'<td>{_e(f.get("note", ""))}</td>'
        f'<td>{fmt_size(size_of(out_dir / f["path"]))}</td></tr>'
        for f in manifest["facts"]
    )
    log_rows = "".join(
        f'<tr><td><a href="{_e(f["path"])}"><code>{_e(Path(f["path"]).name)}</code></a></td>'
        f'<td>{fmt_size(size_of(out_dir / f["path"]))}</td></tr>'
        for f in manifest["logs"]
    )
    source = manifest.get("source_url") or ""
    source_link = f'<a href="{_e(source)}" rel="noopener">{_e(source)}</a>' if source else "—"
    site_link = (
        f'<a href="{_e(SITE_PAGE)}">← Back to the generated site</a>'
        if manifest.get("site")
        else ""
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
{ROBOTS_META}
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_e(manifest["brand"])} — published extraction results</title>
<style>{LANDING_CSS}</style></head>
<body><div class="wrap">
<p class="backlinks">{site_link}<a href="../{_e(BRANDS_PAGE)}">All published brands</a></p>
<h1>{_e(manifest["brand"])} — published extraction results</h1>
<p class="sub">Everything below was generated from screenshots and DOM/CSS measurements of the
source site. No hand-written page code: the design system is extracted into facts, and the pages
are composed back out of those facts, so the pages double as a check on the facts.</p>
<div class="meta">
  <span>source: {source_link}</span>
  <span>run: <code>{_e(manifest["run"])}</code></span>
  <span>published: {_e(manifest["published_at"])}</span>
  {f'<span>replica fidelity (report): <strong>{_e(replica)}</strong></span>' if replica is not None else ''}
  {f'<span>schema validation (run manifest): {_e(validation.get("c1_c28_errors", 0))} errors / {_e(validation.get("c1_c28_warnings", 0))} warnings</span>' if validation else ''}
  <span>media: {_e(manifest["assets_published"])} files</span>
</div>

{render_status_html(manifest.get("status") or {})}

<h2>Rendered results</h2>
<div class="grid">{"".join(cards)}</div>

<h2>Brand facts — the extraction output</h2>
<p class="note">These files are the deliverable; every rendered page above is derived from them.</p>
<table><thead><tr><th>file</th><th>what it is</th><th>size</th></tr></thead><tbody>{fact_rows}</tbody></table>

<h2>What happened — logs &amp; manifest</h2>
<table><thead><tr><th>file</th><th>size</th></tr></thead><tbody>
<tr><td><a href="logs/changes.md"><code>changes.md</code></a></td><td>{fmt_size(size_of(out_dir / "logs" / "changes.md"))}</td></tr>
<tr><td><a href="logs/manifest.json"><code>manifest.json</code></a></td><td>{fmt_size(size_of(out_dir / "logs" / "manifest.json"))}</td></tr>
{log_rows}</tbody></table>

<footer>Exported with <code>tools/publish_run_bundle.py</code> from <code>{_e(manifest["run"])}</code>.
Re-run: <code>./venv/bin/python tools/publish_run_bundle.py --run {_e(manifest["run"])}</code>.
The full run (source captures, crops, evidence, app sources, node_modules) stays local — it is
gitignored and ~300&nbsp;MB.</footer>
</div></body></html>
"""


def render_readme(manifest: dict, out_dir: Path) -> str:
    replica = manifest.get("replica_overall")
    lines = [
        f"# {manifest['brand']} — published extraction results",
        "",
        f"- source site: {manifest.get('source_url') or '—'}",
        f"- run of record: `{manifest['run']}` (gitignored; this directory is the shareable export)",
        f"- published: {manifest['published_at']}",
        f"- bundle size: {fmt_size(size_of(out_dir))} · {manifest['assets_published']} media files",
    ]
    if replica is not None:
        lines.append(f"- replica fidelity score: {replica} (from the report beside the published page)")
    lines += [""]
    lines += [
        f"`{SITE_PAGE}` is the generated site itself. Everything about how it was made — every",
        f"artifact below, and the run-status disclosure — is on `{DETAILS_PAGE}`, one link away in",
        "the site's footer.",
        "",
    ]
    lines += render_status_markdown(manifest.get("status") or {})
    lines += [
        "Browse it through the local Studio server (`./start-studio.sh`, port 1500):",
        "",
        f"    http://127.0.0.1:1500/{out_dir.relative_to(REPO_ROOT).as_posix()}/{SITE_PAGE}",
        f"    http://127.0.0.1:1500/{out_dir.relative_to(REPO_ROOT).as_posix()}/{DETAILS_PAGE}",
        "",
        f"Or open `{SITE_PAGE}` directly — every path in the bundle is relative, so it also works",
        "from `file://` or any static host.",
        "",
        "## Contents",
        "",
    ]
    for lane in manifest["lanes"]:
        lines.append(f"- **{lane['label']}** — `{lane['path']}`  \n  {lane.get('note', '')}")
    lines += [
        f"- **Pipeline details** — `{DETAILS_PAGE}`  \n  Run status, every rendered lane, the brand "
        "facts and the logs, in one page.",
        "- **Brand facts** — `brand/`  \n  The authored extraction output (yaml/json); every page above is derived from it.",
        "- **Logs & manifest** — `logs/`  \n  Run logs, schema validation output, and `changes.md`.",
        "- **Media** — `assets/`  \n  One deduped copy of the media the pages actually reference.",
        "",
        "## Regenerating",
        "",
        "```sh",
        f"./venv/bin/python tools/publish_run_bundle.py --run {manifest['run']} \\",
        f"    --out {out_dir.relative_to(REPO_ROOT).as_posix()}",
        "```",
        "",
        "The script copies only finished artifacts, rewrites every asset reference to this",
        "bundle's `assets/` dir, then loads each page in headless Chromium to assert it renders",
        "content with no broken images (add `--base-url http://127.0.0.1:1500` to check it over the",
        "running Studio, `--no-verify` to skip). Results land in `verify.json`.",
        "",
    ]
    return "\n".join(lines)


def load_published_bundles(root: Path) -> list[dict]:
    """Every bundle manifest under `root`, newest first (name breaks ties)."""
    bundles = []
    for manifest_path in sorted(root.glob("*/published.json")):
        try:
            bundles.append(json.loads(manifest_path.read_text()))
        except Exception:  # noqa: BLE001
            continue
    return sorted(bundles, key=lambda b: (b.get("published_at", ""), b.get("name", "")), reverse=True)


def render_brands_page(bundles: list[dict]) -> str:
    """The list of every published bundle — a site link and a details link each."""
    rows = "".join(
        f'<article class="card"><div class="body">'
        f'<h3><a href="{_e(b["name"])}/{_e((b.get("site") or {}).get("path") or SITE_PAGE)}">'
        f'{_e(b["brand"])} →</a></h3>'
        f'<p>{_e(b.get("source_url") or "")}<br>published {_e(b.get("published_at"))} · '
        f'{fmt_size(b.get("bytes", 0))} · {len(b.get("lanes", []))} rendered lanes<br>'
        f'gates: <strong>{_e((b.get("status") or {}).get("verdict", "undetermined"))}</strong></p>'
        f'<ul class="extras"><li><a href="{_e(b["name"])}/{_e(b.get("details") or DETAILS_PAGE)}">'
        "Pipeline details</a></li></ul>"
        "</div></article>"
        for b in bundles
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
{ROBOTS_META}
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Published generated sites</title><style>{LANDING_CSS}</style></head>
<body><div class="wrap">
<h1>Published generated sites</h1>
<p class="sub">Each entry opens the site that run generated. The pipeline artifacts behind it — the
replica, the harness, the brand facts, the logs and the run's gate status — are on its details page.</p>
<h2>Brands</h2>
<div class="grid">{rows}</div>
</div></body></html>
"""


def write_published_index(root: Path) -> None:
    """Write the published root: the newest brand's site, plus the brand list.

    A bare URL should open the deliverable, not a chooser, so `index.html` here is
    the newest bundle's generated site re-written for THIS depth — the asset prefix
    is derived from where the page lands, not inherited from the bundle copy. The
    other brands stay one footer link away on `brands.html`, which is also what the
    root falls back to if no bundle has a generated site yet.
    """
    bundles = load_published_bundles(root)
    if not bundles:
        return
    (root / BRANDS_PAGE).write_text(render_brands_page(bundles))

    primary = next(
        (
            b
            for b in bundles
            if b.get("site") and (root / b["name"] / ((b.get("site") or {}).get("path") or SITE_PAGE)).is_file()
        ),
        None,
    )
    if primary is None:
        (root / "index.html").write_text(render_brands_page(bundles))
        return
    bundle_dir = root / primary["name"]
    site_src = bundle_dir / ((primary.get("site") or {}).get("path") or SITE_PAGE)
    root_index = root / "index.html"
    text, _ = repoint_assets(site_src.read_text(encoding="utf-8"), bundle_dir / "assets", root_index)
    root_index.write_text(
        stamp_provenance(
            text,
            provenance_footer(
                primary,
                f"{primary['name']}/{primary.get('details') or DETAILS_PAGE}",
                BRANDS_PAGE if len(bundles) > 1 else None,
            ),
        ),
        encoding="utf-8",
    )


# ── verification (also produces the landing-page previews) ─────────────────────

PREVIEW_WIDTH = 860


def verify(out_dir: Path, manifest: dict, base_url: str | None) -> dict:
    """Load every exported page in headless Chromium; assert content + assets.

    Writes `verify.json` and, for each rendered lane, a downscaled preview PNG
    used by the details page. Returns the report. Skips (loudly) when Playwright
    or its browser is unavailable, so the export itself never depends on it.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("  verify: playwright not installed — skipped")
        return {}

    # Pages outside the bundle that the export also owns: the published root serves
    # the primary bundle's site at a different depth, so it is exactly where a
    # re-derived asset path would silently break, and it gets checked like any other.
    root_pages = [p for p in (out_dir.parent / "index.html", out_dir.parent / BRANDS_PAGE) if p.is_file()]
    # Full pages must be substantial; a single composed section can legitimately be
    # one heading and a button, so only these have to carry real content.
    full_pages = {SITE_PAGE, DETAILS_PAGE, *(lane["path"] for lane in manifest["lanes"])} | {
        os.path.relpath(p, out_dir).replace(os.sep, "/") for p in root_pages
    }
    # The details page is checked LAST, because its thumbnails are the screenshots
    # taken while checking the lanes — verified before they exist, it would always
    # report its own previews as broken images.
    pages = (
        [out_dir / lane["path"] for lane in manifest["lanes"]]
        + sorted((out_dir / "harness" / "layouts").glob("*.html"))
        + root_pages
        + [out_dir / DETAILS_PAGE]
    )
    results: list[dict] = []
    shutil.rmtree(out_dir / "previews", ignore_errors=True)

    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch()
        except Exception as exc:  # noqa: BLE001
            print(f"  verify: chromium unavailable ({exc}) — skipped")
            return {}
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
        # Local == anything under artifacts/published/, so the root pages' requests
        # into a sibling bundle's assets/ are judged too. Third-party (webfonts) is
        # still out of scope: it depends on the reader's network, not the export.
        published_root = out_dir.parent
        local_prefix = (
            f"{base_url.rstrip('/')}/{published_root.relative_to(REPO_ROOT).as_posix()}/"
            if base_url
            else published_root.as_uri()
        )
        for path in pages:
            rel = os.path.relpath(path, out_dir).replace(os.sep, "/")
            if path == out_dir / DETAILS_PAGE:
                # Re-render with the previews now on disk, so what gets checked is what
                # ships (finalize() rewrites it again only to update the size figures).
                path.write_text(render_landing(manifest, out_dir), encoding="utf-8")
            page = ctx.new_page()
            failed: list[str] = []
            errors: list[str] = []

            def note_failure(url: str, detail: str, sink=failed, prefix=local_prefix) -> None:
                # Only our own resources are our problem; webfonts and other
                # third-party requests depend on the reader's network.
                if url.startswith(prefix):
                    sink.append(detail)

            page.on("requestfailed", lambda req: note_failure(req.url, req.url))
            page.on(
                "response",
                lambda res: note_failure(res.url, f"{res.status} {res.url}") if res.status >= 400 else None,
            )
            page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
            url = (
                f"{base_url.rstrip('/')}/{path.relative_to(REPO_ROOT).as_posix()}"
                if base_url
                else path.as_uri()
            )
            entry = {"page": rel, "url": url}
            try:
                page.goto(url, wait_until="load", timeout=45_000)
                page.wait_for_timeout(1200)
                stats = page.evaluate(
                    """() => {
                        const imgs = Array.from(document.images);
                        return {
                          text: (document.body ? document.body.innerText : '').trim().length,
                          nodes: document.querySelectorAll('*').length,
                          images: imgs.length,
                          broken: imgs.filter(i => i.complete && i.naturalWidth === 0)
                                      .map(i => i.getAttribute('src')),
                        };
                    }"""
                )
                entry.update(stats)
                entry["failed_requests"] = sorted(set(failed))
                entry["console_errors"] = errors[:5]
                # Full pages must be substantial (the framework build is a React app:
                # a blank #root would score near zero here). A single composed section
                # can legitimately be one heading and a button, so it only has to have
                # rendered *something* — with every referenced image resolving.
                min_text = 200 if rel in full_pages else 15
                entry["ok"] = (
                    stats["nodes"] > 10
                    and stats["text"] >= min_text
                    and not stats["broken"]
                    and not entry["failed_requests"]
                )
                lane_kind = next((l["kind"] for l in manifest["lanes"] if l["path"] == rel), None)
                if lane_kind:
                    shot = out_dir / "previews" / f"{lane_kind}.png"
                    shot.parent.mkdir(parents=True, exist_ok=True)
                    page.screenshot(path=str(shot))
                    _downscale(shot, PREVIEW_WIDTH)
            except Exception as exc:  # noqa: BLE001
                entry.update({"ok": False, "error": str(exc)})
            results.append(entry)
            page.close()
        browser.close()

    report = {
        "checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "base": base_url or "file://",
        "pages": results,
        "ok": all(r.get("ok") for r in results),
    }
    # Every `file://` URL here is an absolute path on this machine.
    (out_dir / "verify.json").write_text(redact_local_paths(json.dumps(report, indent=2) + "\n"))
    bad = [r for r in results if not r.get("ok")]
    print(f"  verify: {len(results) - len(bad)}/{len(results)} pages ok ({report['base']})")
    for r in bad:
        detail = r.get("error") or f"text={r.get('text')} broken={r.get('broken')} failed={r.get('failed_requests')}"
        print(f"    FAIL {r['page']}: {detail}")
    return report


def _downscale(path: Path, width: int) -> None:
    try:
        from PIL import Image
    except ImportError:
        return
    with Image.open(path) as im:
        if im.width <= width:
            return
        im = im.convert("RGB").resize((width, round(im.height * width / im.width)), Image.LANCZOS)
        im.save(path, optimize=True)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", required=True, help="run directory, e.g. runs/greenhouse-4")
    ap.add_argument(
        "--out",
        default=None,
        help="output bundle dir (default: artifacts/published/<run name>)",
    )
    ap.add_argument(
        "--no-verify",
        dest="verify",
        action="store_false",
        help="skip the headless-Chromium pass (it is what proves the bundle browses, and it builds the details-page previews)",
    )
    ap.add_argument("--base-url", default=None, help="verify over HTTP through this origin instead of file://")
    args = ap.parse_args(argv)

    run_dir = Path(args.run).resolve()
    if not run_dir.is_dir():
        raise SystemExit(f"run dir not found: {args.run}")
    out_dir = Path(args.out).resolve() if args.out else REPO_ROOT / "artifacts" / "published" / run_dir.name

    print(f"publishing {run_dir.name} -> {out_dir.relative_to(REPO_ROOT)}")
    manifest = export(run_dir, out_dir)
    for lane in manifest["lanes"]:
        print(f"  lane: {lane['kind']:<10} {lane['path']}")
    status = manifest.get("status") or {}
    print(f"  run status: {status.get('verdict')} — {status.get('headline', '')[:80]}…")
    for fact in status.get("facts", []):
        print(f"    · {fact['text']} [{fact.get('source', '')}]")
    print(f"  brand facts: {len(manifest['facts'])} files")
    print(f"  media: {manifest['assets_published']} files, {fmt_size(size_of(out_dir / 'assets'))}")
    if manifest["assets_unresolved"]:
        print(f"  warn: {len(manifest['assets_unresolved'])} references did not resolve to a file:")
        for name in manifest["assets_unresolved"][:10]:
            print(f"    {name}")
    report_foreign_strings(manifest.get("foreign_strings") or [])

    report = verify(out_dir, manifest, args.base_url) if args.verify else {}
    # Verification produces the lane previews, so the entry points are rewritten
    # afterwards to pick them up (and to record the final byte count).
    finalize(manifest, out_dir)

    total = size_of(out_dir)
    print("  size breakdown:")
    for child in sorted(out_dir.iterdir(), key=lambda p: -size_of(p)):
        print(f"    {fmt_size(size_of(child)):>9}  {child.name}")
    print(f"  TOTAL: {fmt_size(total)}")
    rel_root = out_dir.relative_to(REPO_ROOT).as_posix()
    print(f"  site:    http://127.0.0.1:1500/{rel_root}/{SITE_PAGE}")
    print(f"  details: http://127.0.0.1:1500/{rel_root}/{DETAILS_PAGE}")
    if report and not report.get("ok"):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
