#!/usr/bin/env python3
"""Walk a Studio and record every request that failed, with the checkout it walked.

Written to be run twice — once against a fresh clone and once against the author's
own tree — so the two reports can be diffed. The comparison is only meaningful if
each run really did talk to its own Studio, and that is the failure this script
exists to prevent.

**The trap.** This is a shared working tree and other agents leave Studios bound to
spare ports. A server that cannot bind exits, the probe connects to whoever already
owns the port, and the "clone" walk quietly measures the author's checkout instead —
which looks like perfect parity because it *is* the author's checkout. So before
believing anything, the walk asserts that the dashboard's project list equals the
run directories of the checkout it was told to verify. A mismatch is fatal, not a
warning.

Usage:
    ./venv/bin/python tools/verify_clone_parity.py --root /path/to/checkout \
        --out /tmp/report.json [--port 0]

`--port 0` (the default) picks a free ephemeral port and starts the Studio itself,
which is the only mode that cannot collide with somebody else's server.
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import quote, urljoin, urlparse


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def run_dirs(root: Path) -> set[str]:
    """The project directories this checkout actually has under `runs/`."""
    runs = root / "runs"
    if not runs.is_dir():
        return set()
    return {
        p.name for p in runs.iterdir()
        if p.is_dir() and not p.name.startswith(".")
    }


def start_studio(root: Path, port: int, log_path: Path) -> subprocess.Popen:
    env = dict(os.environ, STUDIO_PORT=str(port))
    env.pop("PLAYWRIGHT_BROWSERS_PATH", None)
    log = open(log_path, "w")
    proc = subprocess.Popen(
        [str(root / "venv" / "bin" / "python"), str(root / "studio_server.py")],
        cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT,
    )
    for _ in range(120):
        if proc.poll() is not None:
            raise SystemExit(
                f"the Studio exited immediately (code {proc.returncode}) — see "
                f"{log_path}. A silent exit is usually a port already held by "
                "another server."
            )
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.25):
                return proc
        except OSError:
            time.sleep(0.25)
    proc.kill()
    raise SystemExit(f"the Studio never accepted a connection on :{port}")


def get(base: str, path: str) -> tuple[int, bytes]:
    # Lane directory names contain spaces on some projects. A browser encodes
    # those before sending; urllib does not, and the server rejects the raw
    # request — which reads as a broken lane when the lane is fine. Encode
    # everything except the characters that carry meaning in a URL.
    url = urljoin(base, quote(path, safe="/?&=:%#"))
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, b""
    except Exception as exc:                                  # noqa: BLE001
        return 0, str(exc).encode()


def assert_it_is_this_checkout(base: str, root: Path) -> list[str]:
    """Fatal unless the Studio's project list is this checkout's own run dirs.

    This is the whole safety property. Anything downstream is unfalsifiable
    without it.
    """
    status, body = get(base, "/api/projects")
    if status != 200:
        raise SystemExit(f"/api/projects answered {status}; cannot identify the Studio")
    payload = json.loads(body)
    items = payload if isinstance(payload, list) else payload.get("projects") or []
    served = {str(p.get("version") or p.get("id") or p.get("name")) for p in items}
    mine = run_dirs(root)
    if served != mine:
        raise SystemExit(
            "the Studio on this port is NOT serving the checkout under test.\n"
            f"  it lists {len(served)} projects: {sorted(served)[:6]}…\n"
            f"  {root} has {len(mine)} run dirs: {sorted(mine)[:6]}…\n"
            "Refusing to report parity against somebody else's server."
        )
    return sorted(served)


def walk(base: str, root: Path) -> dict:
    projects = assert_it_is_this_checkout(base, root)
    report: dict = {
        "root": str(root), "projects": projects,
        "failures": [], "declared_unavailable": [], "lanes": {},
    }

    status, _ = get(base, "/studio")
    if status != 200:
        report["failures"].append({"where": "/studio", "status": status})

    for version in projects:
        status, body = get(base, f"/api/project/{version}")
        if status != 200:
            report["failures"].append({"where": f"/api/project/{version}", "status": status})
            continue
        payload = json.loads(body)
        # Two separate surfaces a reader can click, and a lane that 404s is just
        # as broken from either. `build_links` is where the framework entries
        # live, so walking only `lanes` would miss the case this exists to check.
        lanes = [
            *(payload.get("lanes") or []),
            *(payload.get("build_links") or []),
            *(payload.get("static_lanes") or []),
        ]
        report["lanes"][version] = [str(lane.get("label") or lane.get("kind")) for lane in lanes]
        for lane in lanes:
            url = str(lane.get("url") or "")
            if lane.get("available") is False:
                # Declared unavailable with a reason. That is the honest state,
                # not a failure — counting it as one would punish the fix.
                report["declared_unavailable"].append(
                    {"project": version, "lane": str(lane.get("label") or ""),
                     "hint": str(lane.get("hint") or "")}
                )
                continue
            if not url or urlparse(url).netloc:
                continue                     # an external link is not ours to serve
            code, _ = get(base, url)
            if code != 200:
                report["failures"].append(
                    {"where": url, "status": code, "project": version,
                     "lane": str(lane.get("label") or lane.get("kind"))}
                )
        for doc in payload.get("availableDocs") or []:
            key = doc if isinstance(doc, str) else str(doc.get("key") or doc.get("id"))
            code, doc_body = get(base, f"/api/rundoc?version={version}&doc={key}")
            if code != 200 or not doc_body.strip():
                report["failures"].append(
                    {"where": f"rundoc {version}/{key}", "status": code,
                     "empty": not doc_body.strip()}
                )
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, required=True, help="checkout to verify")
    ap.add_argument("--out", type=Path, required=True, help="where to write the report")
    ap.add_argument("--port", type=int, default=0, help="0 = pick a free one (default)")
    args = ap.parse_args(argv)

    root = args.root.resolve()
    port = args.port or free_port()
    log_path = args.out.with_suffix(".studio.log")
    proc = start_studio(root, port, log_path)
    try:
        report = walk(f"http://127.0.0.1:{port}", root)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()

    args.out.write_text(json.dumps(report, indent=2) + "\n")
    print(f"{len(report['projects'])} projects, "
          f"{sum(len(v) for v in report['lanes'].values())} lanes, "
          f"{len(report['declared_unavailable'])} declared-unavailable, "
          f"{len(report['failures'])} failures -> {args.out}")
    for f in report["failures"][:20]:
        print("  ", f)
    return 1 if report["failures"] else 0


if __name__ == "__main__":
    sys.exit(main())
