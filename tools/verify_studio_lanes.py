#!/usr/bin/env python3
"""Probe a running Studio and assert it serves THIS checkout's projects and lanes.

Written for verifying a fresh clone, where the interesting failure is not a
broken page but a probe that proves nothing. If another Studio already holds the
chosen port, the server started for the check exits and every request goes to the
OTHER checkout — which answers perfectly, because it is a different healthy tree.
The parity assertion is the defence: the project list the API returns must equal
the run directories sitting beside this script, so a misdirected probe fails
loudly instead of reporting success.

The Studio dashboard is client-rendered from `/api/projects` and
`/api/project/<name>`, so the checks read those endpoints rather than scraping
HTML, which only ever contains the JS template.

Usage:
    ./venv/bin/python tools/verify_studio_lanes.py --port 7731
    ./venv/bin/python tools/verify_studio_lanes.py --port 7731 \
        --project woodwave --expect-variants 42 --probe-paths plan.json
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import quote, unquote

REPO_ROOT = Path(__file__).resolve().parent.parent
RUNS_DIR = REPO_ROOT / "runs"


def fetch(base: str, path: str, timeout: int = 120) -> tuple[int, bytes]:
    # Run artifacts carry spaces and em-dashes in their filenames, which a raw
    # request rejects outright. Unquote first so an already-encoded URL from the
    # API is not double-encoded into a 404.
    url = base + quote(unquote(path), safe="/:?=&%")
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return resp.status, resp.read()


def get_json(base: str, path: str, timeout: int = 120) -> dict:
    return json.loads(fetch(base, path, timeout)[1].decode())


def local_projects() -> list[str]:
    """Every run directory the Studio would list — mirrors `list_projects()`."""
    if not RUNS_DIR.is_dir():
        return []
    return sorted(
        d.name for d in RUNS_DIR.iterdir() if d.is_dir() and not d.name.startswith(".")
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--project", default="woodwave", help="project whose lanes are counted")
    ap.add_argument("--expect-variants", type=int, default=None)
    ap.add_argument("--expect-projects", type=int, default=None)
    ap.add_argument("--probe-paths", help="JSON list/dict of repo-relative paths to GET")
    args = ap.parse_args()
    base = f"http://127.0.0.1:{args.port}"
    failures: list[str] = []

    try:
        served = [p["version"] for p in get_json(base, "/api/projects", 60)["projects"]]
    except (urllib.error.URLError, OSError, ValueError) as exc:
        print(f"FAIL: no Studio answered on {base}: {exc}")
        return 1

    mine = local_projects()
    print(f"API projects      : {len(served)}")
    print(f"runs/ directories : {len(mine)}")
    if sorted(served) != mine:
        failures.append(
            "PARITY: API project list != this checkout's runs/ dirs — the probe is "
            f"talking to another tree. only-api={sorted(set(served) - set(mine))} "
            f"only-disk={sorted(set(mine) - set(served))}"
        )
    else:
        print("PARITY OK: the Studio answering is this checkout's own")
    if args.expect_projects is not None and len(served) != args.expect_projects:
        failures.append(f"expected {args.expect_projects} projects, API served {len(served)}")

    print(f"\n{'project':22} {'thumb':6} {'docs':>5} {'lanes':>6} {'variants':>9}")
    for proj in sorted(served):
        try:
            d = get_json(base, f"/api/project/{proj}")
        except (urllib.error.URLError, OSError, ValueError) as exc:
            failures.append(f"{proj}: project API error {exc}")
            continue

        thumb = d.get("thumb") or ""
        thumb_ok = "-"
        if thumb:
            try:
                st, body = fetch(base, thumb, 60)
                thumb_ok = "OK" if st == 200 and body else f"{st}"
                if thumb_ok != "OK":
                    failures.append(f"{proj}: thumbnail {thumb} -> {st}")
            except (urllib.error.URLError, OSError) as exc:
                thumb_ok = "ERR"
                failures.append(f"{proj}: thumbnail {thumb} {exc}")
        else:
            failures.append(f"{proj}: no thumbnail")

        docs, lanes = len(d.get("docs") or {}), len(d.get("lanes") or [])
        variants = len(d.get("variant_pages") or [])
        if not docs:
            failures.append(f"{proj}: Docs tab is empty")
        if not lanes:
            failures.append(f"{proj}: no lanes offered")
        print(f"{proj:22} {thumb_ok:6} {docs:>5} {lanes:>6} {variants:>9}")

    d = get_json(base, f"/api/project/{args.project}")
    variants = d.get("variant_pages") or []
    print(f"\n{args.project}: {len(variants)} variant lanes")
    if args.expect_variants is not None and len(variants) != args.expect_variants:
        failures.append(
            f"{args.project}: expected {args.expect_variants} variant lanes, got {len(variants)}"
        )
    # Every lane the Studio offers must actually serve, or it is a 404 in a clone.
    for v in variants:
        url = v.get("url") if isinstance(v, dict) else v
        if not isinstance(url, str) or not url.startswith("/"):
            continue
        try:
            st, body = fetch(base, url, 60)
            if st != 200 or len(body) < 500:
                failures.append(f"lane {url}: status={st} len={len(body)}")
        except (urllib.error.URLError, OSError) as exc:
            failures.append(f"lane {url}: {exc}")

    if args.probe_paths:
        raw = json.loads(Path(args.probe_paths).read_text())
        paths = sorted(raw)
        print(f"probing {len(paths)} materialized paths over HTTP")
        for rel in paths:
            try:
                st, body = fetch(base, "/" + rel, 60)
                if st != 200 or not body:
                    failures.append(f"{rel}: status={st} len={len(body)}")
            except (urllib.error.URLError, OSError) as exc:
                failures.append(f"{rel}: {exc}")

    print()
    if failures:
        print(f"FAILURES ({len(failures)}):")
        for f in failures[:40]:
            print("  -", f)
        return 1
    print("ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
