#!/usr/bin/env python3
"""Soak/abuse test for studio_server.py hang hardening. Stdlib only.

Boots a fresh studio_server on a scratch port (pipeline subprocess stubbed via
the STUDIO_PIPELINE_CMD hook — no LLM calls), then hammers it for several
minutes with the traffic that used to wedge it, while liveness probes assert it
stays responsive throughout:

  • steady GET load: /healthz, /project/remote, /studio, /api/projects,
    /api/project/remote, /api/jobs/<bogus>, /api/brandfile, real static assets
  • a stall storm: ~140 sockets that connect and never send a request — the
    exact client behavior that used to pin handler threads + fds forever
  • half-request stallers, slow readers, and mid-response aborters
  • two harvest jobs pointed at local tarpits: a SILENT one (accepts, never
    responds → per-op socket timeout must fire) and a DRIP one (valid headers,
    then one byte every 2s forever → the total wall-clock deadline must fire)

PASS requires: zero failed liveness probes, both tarpit jobs terminating with
"harvest skipped", and the handler-thread count returning to baseline after the
stall storm (proves the socket timeout reaps stalled clients).

Usage:
    ./venv/bin/python tools/soak_studio_server.py [--port 7801] [--duration 240]

Cleans up after itself: kills the scratch server's process group and removes
the zz-soak-* screenshots dirs and runs/.studio job logs/configs it created.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import shutil
import signal
import socket
import statistics
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
PY = str(PROJECT_DIR / "venv" / "bin" / "python")

# 1x1 transparent PNG for project-creation POSTs.
TINY_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGNgYGBgAAAABQAB"
    "h6FO1AAAAABJRU5ErkJggg=="
)

STOP = threading.Event()


# ── tiny stats collector ──────────────────────────────────────────────────────
class Track:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.lat: dict[str, list[float]] = {}
        self.err: dict[str, list[str]] = {}

    def ok(self, key: str, dt: float) -> None:
        with self.lock:
            self.lat.setdefault(key, []).append(dt)

    def fail(self, key: str, msg: str) -> None:
        with self.lock:
            self.err.setdefault(key, []).append(msg)

    def report(self) -> tuple[str, int]:
        lines = []
        total_err = 0
        keys = sorted(set(self.lat) | set(self.err))
        for k in keys:
            ls = self.lat.get(k, [])
            es = self.err.get(k, [])
            total_err += len(es)
            if ls:
                p50 = statistics.median(ls)
                p95 = sorted(ls)[max(0, int(len(ls) * 0.95) - 1)]
                lines.append(
                    f"  {k:<28} n={len(ls):<5} err={len(es):<3} "
                    f"p50={p50*1000:6.0f}ms p95={p95*1000:6.0f}ms max={max(ls)*1000:6.0f}ms"
                )
            else:
                lines.append(f"  {k:<28} n=0     err={len(es)}")
            for e in es[:3]:
                lines.append(f"      !! {e}")
        return "\n".join(lines), total_err


T = Track()


# ── tarpits: the "unreachable/slow URL" scenarios, sandbox-proof on localhost ──
def silent_tarpit() -> int:
    """Accepts connections and never sends a byte (never closes either)."""
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", 0))
    srv.listen(16)
    held: list[socket.socket] = []

    def run() -> None:
        while not STOP.is_set():
            try:
                srv.settimeout(1)
                conn, _ = srv.accept()
                held.append(conn)
            except socket.timeout:
                continue
            except OSError:
                return

    threading.Thread(target=run, daemon=True).start()
    return srv.getsockname()[1]


def drip_tarpit() -> int:
    """Sends valid HTTP headers, then drips one body byte every 2s forever —
    each socket op succeeds fast, so only a TOTAL deadline can stop the read."""
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", 0))
    srv.listen(16)

    def feed(conn: socket.socket) -> None:
        try:
            conn.settimeout(5)
            conn.recv(65536)  # swallow the request
            conn.sendall(
                b"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n"
                b"Content-Length: 1000000\r\n\r\n"
            )
            while not STOP.is_set():
                conn.sendall(b"x")
                time.sleep(2)
        except OSError:
            pass
        finally:
            conn.close()

    def run() -> None:
        while not STOP.is_set():
            try:
                srv.settimeout(1)
                conn, _ = srv.accept()
                threading.Thread(target=feed, args=(conn,), daemon=True).start()
            except socket.timeout:
                continue
            except OSError:
                return

    threading.Thread(target=run, daemon=True).start()
    return srv.getsockname()[1]


# ── HTTP helpers ──────────────────────────────────────────────────────────────
def get(port: int, path: str, timeout: float = 10.0, key: str | None = None) -> bytes | None:
    key = key or path.split("?")[0]
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=timeout) as r:
            body = r.read()
            if r.status != 200:
                T.fail(key, f"status {r.status}")
                return None
            T.ok(key, time.monotonic() - t0)
            return body
    except Exception as exc:
        T.fail(key, f"{type(exc).__name__}: {exc} after {time.monotonic()-t0:.1f}s")
        return None


def post_json(port: int, path: str, payload: dict, timeout: float = 20.0) -> dict:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def healthz(port: int) -> dict | None:
    body = get(port, "/healthz", timeout=3.0)
    return json.loads(body) if body else None


def healthz_silent(port: int) -> dict | None:
    """Liveness check that does NOT record into stats (startup wait etc.)."""
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/healthz", timeout=3.0) as r:
            return json.loads(r.read())
    except Exception:
        return None


# ── abusive client behaviors (what used to wedge the server) ──────────────────
def open_stalled(port: int, n: int) -> list[socket.socket]:
    out = []
    for _ in range(n):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(3)
            s.connect(("127.0.0.1", port))
            out.append(s)
        except OSError:
            break
    return out


def half_request_staller(port: int) -> None:
    """Connect, send a *partial* request line, stall until closed by server."""
    while not STOP.is_set():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(60)
            s.connect(("127.0.0.1", port))
            s.sendall(b"GET /project/remote HTTP/1.1\r\nHost: 127.0.0.1")
            # wait for the server to time us out (it must, or this fd leaks)
            s.recv(1024)
        except OSError:
            pass
        finally:
            try:
                s.close()
            except OSError:
                pass
        STOP.wait(5)


def slow_reader(port: int, path: str) -> None:
    """Request a page and read it 1KB per 300ms — steady progress must NOT be
    killed by the socket timeout; then abandon mid-body."""
    while not STOP.is_set():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(30)
            s.connect(("127.0.0.1", port))
            s.sendall(f"GET {path} HTTP/1.0\r\nHost: 127.0.0.1\r\n\r\n".encode())
            for _ in range(40):
                if not s.recv(1024):
                    break
                time.sleep(0.3)
        except OSError:
            pass
        finally:
            try:
                s.close()
            except OSError:
                pass
        STOP.wait(3)


def aborter(port: int, path: str) -> None:
    """Request a file and slam the connection shut mid-response."""
    while not STOP.is_set():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(10)
            s.connect(("127.0.0.1", port))
            s.sendall(f"GET {path} HTTP/1.0\r\nHost: 127.0.0.1\r\n\r\n".encode())
            s.recv(8192)
        except OSError:
            pass
        finally:
            try:
                s.close()
            except OSError:
                pass
        STOP.wait(2)


# ── steady load workers ───────────────────────────────────────────────────────
def prober(port: int, path: str, period: float, timeout: float, key: str) -> None:
    while not STOP.is_set():
        get(port, path, timeout=timeout, key=key)
        STOP.wait(period)


def api_hammer(port: int, statics: list[str]) -> None:
    mix = [
        "/studio",
        "/api/projects",
        "/api/project/remote",
        "/api/jobs/bogus-job-id",
        "/api/brandfile?version=remote&which=yaml",
    ] + statics
    i = 0
    while not STOP.is_set():
        get(port, mix[i % len(mix)], timeout=15.0)
        i += 1
        STOP.wait(0.4)


# ── job runner: harvest against tarpits, stubbed pipeline ─────────────────────
def run_tarpit_job(port: int, name: str, url: str, results: dict, studio_dir: Path) -> None:
    try:
        resp = post_json(
            port,
            "/api/projects",
            {
                "name": name,
                "url": url,
                "filename": "shot.png",
                "screenshot_b64": TINY_PNG_B64,
            },
        )
    except Exception as exc:
        results[name] = f"FAIL: POST /api/projects: {exc}"
        return
    job_id = resp.get("job_id", "")
    if not job_id:
        results[name] = f"FAIL: no job_id in {resp}"
        return
    results.setdefault("_job_ids", []).append(job_id)
    results.setdefault("_versions", []).append(resp.get("version", ""))
    t0 = time.monotonic()
    deadline = t0 + 120
    while time.monotonic() < deadline and not STOP.is_set():
        body = get(port, f"/api/jobs/{job_id}", timeout=10.0, key="/api/jobs/<soak>")
        if body:
            j = json.loads(body)
            if j.get("status") in ("done", "error"):
                out = j.get("output", "")
                took = time.monotonic() - t0
                skipped = "harvest skipped" in out
                stub = "pipeline-stub-done" in out
                verdict = "OK" if (skipped and stub) else "FAIL"
                results[name] = (
                    f"{verdict}: status={j['status']} in {took:.0f}s · "
                    f"harvest-timeout-fired={skipped} · stub-pipeline-ran={stub}"
                )
                return
        STOP.wait(2)
    results[name] = f"FAIL: job {job_id} still not finished after 120s (wedged job thread?)"


# ── main ──────────────────────────────────────────────────────────────────────
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=7801)
    ap.add_argument("--duration", type=int, default=240, help="soak seconds")
    args = ap.parse_args()
    port = args.port

    silent_port = silent_tarpit()
    drip_port = drip_tarpit()
    print(f"tarpits: silent=127.0.0.1:{silent_port} drip=127.0.0.1:{drip_port}")

    env = dict(os.environ)
    env.update(
        {
            "STUDIO_PORT": str(port),
            # stub pipeline: no LLM calls, still exercises Popen/group/watchdog
            "STUDIO_PIPELINE_CMD": "/bin/sh -c 'echo pipeline-stub; sleep 2; echo pipeline-stub-done'",
            "STUDIO_FETCH_TIMEOUT_S": "10",
            "STUDIO_FETCH_DEADLINE_S": "25",
            "PYTHONFAULTHANDLER": "1",
        }
    )
    server = subprocess.Popen(
        [PY, "studio_server.py"],
        cwd=str(PROJECT_DIR),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=True,
    )
    results: dict = {}
    threads: list[threading.Thread] = []
    stalled: list[socket.socket] = []
    verdict_fail: list[str] = []
    studio_dir = PROJECT_DIR / "runs" / ".studio"

    try:
        # wait for liveness (silent probe: startup refusals are not soak errors)
        for _ in range(40):
            if healthz_silent(port):
                break
            time.sleep(0.25)
        else:
            print(server.stdout.read() if server.stdout else "")
            print("FAIL: server never became healthy")
            return 1
        base = healthz_silent(port)
        print(f"server up: pid={base['pid']} threads={base['threads']}")

        statics: list[str] = []
        assets_dir = PROJECT_DIR / "runs" / "remote" / "assets"
        if assets_dir.is_dir():
            for p in sorted(assets_dir.iterdir()):
                if p.is_file() and p.stat().st_size < 8_000_000:
                    statics.append("/" + str(p.relative_to(PROJECT_DIR)))
                if len(statics) >= 3:
                    break

        def spawn(fn, *a) -> None:
            th = threading.Thread(target=fn, args=a, daemon=True)
            th.start()
            threads.append(th)

        # steady load + liveness probes
        spawn(prober, port, "/healthz", 1.0, 3.0, "/healthz (probe)")
        spawn(prober, port, "/project/remote", 2.0, 15.0, "/project/remote (probe)")
        for _ in range(3):
            spawn(api_hammer, port, statics)
        # abusive clients, continuous
        for _ in range(6):
            spawn(half_request_staller, port)
        spawn(slow_reader, port, "/project/remote")
        spawn(slow_reader, port, statics[0] if statics else "/studio")
        spawn(aborter, port, "/project/remote")
        spawn(aborter, port, statics[-1] if statics else "/studio")
        # tarpit harvest jobs (the slow/unreachable-URL scenarios)
        spawn(run_tarpit_job, port, "zz-soak-silent", f"http://127.0.0.1:{silent_port}/", results, studio_dir)
        spawn(run_tarpit_job, port, "zz-soak-drip", f"http://127.0.0.1:{drip_port}/", results, studio_dir)

        t_end = time.monotonic() + args.duration
        storm_done = False
        storm_peak = 0
        post_storm: dict | None = None
        storm_release_at = 0.0

        # stall storm 20s in: 140 connect-and-say-nothing clients, held 60s
        storm_at = time.monotonic() + 20
        while time.monotonic() < t_end:
            now = time.monotonic()
            if not stalled and not storm_done and now >= storm_at:
                stalled = open_stalled(port, 140)
                print(f"[{int(now - (t_end - args.duration))}s] stall storm: {len(stalled)} silent connections opened")
            if stalled and now >= storm_at + 20 and not storm_peak:
                h = healthz(port)
                storm_peak = h["threads"] if h else -1
                print(f"[{int(now - (t_end - args.duration))}s] during storm: healthz threads={storm_peak}")
            if stalled and now >= storm_at + 60:
                for s in stalled:
                    try:
                        s.close()
                    except OSError:
                        pass
                stalled = []
                storm_done = True
                storm_release_at = now
                print(f"[{int(now - (t_end - args.duration))}s] stall storm released")
            if storm_done and post_storm is None and now >= storm_release_at + 45:
                post_storm = healthz(port) or {}
                print(
                    f"[{int(now - (t_end - args.duration))}s] 45s after storm: "
                    f"healthz threads={post_storm.get('threads')}"
                )
            time.sleep(1)

        STOP.set()
        for th in threads:
            th.join(timeout=8)

        # ── verdicts ──
        report, total_err = T.report()
        print("\n=== endpoint stats ===")
        print(report)

        probe_errs = len(T.err.get("/healthz (probe)", [])) + len(T.err.get("/project/remote (probe)", []))
        if probe_errs:
            verdict_fail.append(f"{probe_errs} liveness probe failures")
        if total_err:
            verdict_fail.append(f"{total_err} total request errors")

        print("\n=== tarpit harvest jobs ===")
        for k in ("zz-soak-silent", "zz-soak-drip"):
            print(f"  {k}: {results.get(k, 'NO RESULT')}")
            if not str(results.get(k, "")).startswith("OK"):
                verdict_fail.append(f"tarpit job {k} failed")

        print("\n=== thread reaping (stall storm) ===")
        end_h = healthz(port) or {}
        print(f"  baseline={base['threads']} storm_peak={storm_peak} "
              f"post_storm={post_storm.get('threads') if post_storm else 'n/a'} end={end_h.get('threads')}")
        if storm_peak <= base["threads"] + 60:
            verdict_fail.append(f"storm never registered (peak {storm_peak})")
        if post_storm and post_storm.get("threads", 999) > storm_peak - 80:
            verdict_fail.append(
                f"stalled connections NOT reaped: {post_storm.get('threads')} threads still alive 45s after storm"
            )

        ok = not verdict_fail
        print("\n=== SOAK " + ("PASS" if ok else "FAIL") + " ===")
        for v in verdict_fail:
            print(f"  - {v}")
        return 0 if ok else 1

    finally:
        STOP.set()
        for s in stalled:
            try:
                s.close()
            except OSError:
                pass
        try:
            os.killpg(server.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
        # cleanup soak artifacts (surgical: zz-soak-* only)
        for d in (PROJECT_DIR / "screenshots").glob("zz-soak-*"):
            shutil.rmtree(d, ignore_errors=True)
        for d in (PROJECT_DIR / "runs").glob("zz-soak-*"):
            shutil.rmtree(d, ignore_errors=True)
        for f in studio_dir.glob("zz-soak-*.config.yaml"):
            f.unlink(missing_ok=True)
        for jid in results.get("_job_ids", []):
            (studio_dir / f"{jid}.log").unlink(missing_ok=True)


if __name__ == "__main__":
    sys.exit(main())
