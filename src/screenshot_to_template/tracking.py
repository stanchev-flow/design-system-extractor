"""Lightweight per-step token usage and step-status tracking."""

from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from threading import Lock
from threading import local
from typing import Any


_state = local()
_status_lock = Lock()


def _ctx_stack() -> list[dict[str, Any]]:
    stack = getattr(_state, "stack", None)
    if stack is None:
        stack = []
        _state.stack = stack
    return stack


@contextmanager
def token_usage_context(output_dir: str | Path | None, step: str, meta: dict[str, Any] | None = None):
    stack = _ctx_stack()
    stack.append(
        {
            "output_dir": str(output_dir) if output_dir else None,
            "step": step,
            "meta": meta or {},
        }
    )
    try:
        yield
    finally:
        stack.pop()


def _current_context() -> dict[str, Any] | None:
    stack = _ctx_stack()
    return stack[-1] if stack else None


def append_token_usage_event(
    output_dir: str | Path,
    step: str,
    provider: str,
    model: str,
    usage: dict[str, Any] | None,
    meta: dict[str, Any] | None = None,
) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    event = {
        "timestamp": datetime.now().isoformat(),
        "step": step,
        "provider": provider,
        "model": model,
        "usage": usage or {},
        "meta": meta or {},
    }
    with open(output_path / "token-usage.jsonl", "a") as f:
        f.write(json.dumps(event) + "\n")


def log_usage_if_context(provider: str, model: str, usage: dict[str, Any] | None) -> None:
    ctx = _current_context()
    if not ctx or not ctx.get("output_dir"):
        return
    append_token_usage_event(
        output_dir=ctx["output_dir"],
        step=ctx["step"],
        provider=provider,
        model=model,
        usage=usage,
        meta=ctx.get("meta") or {},
    )


def update_step_status(
    output_dir: str | Path,
    step: str,
    status: str,
    meta: dict[str, Any] | None = None,
) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    status_path = output_path / "run-steps.json"
    with _status_lock:
        payload: dict[str, Any]
        if status_path.exists():
            try:
                payload = json.loads(status_path.read_text())
            except json.JSONDecodeError:
                payload = {"steps": {}}
        else:
            payload = {"steps": {}}
        payload.setdefault("steps", {})[step] = {
            "status": status,
            "meta": meta or {},
            "updated_at": datetime.now().isoformat(),
        }
        tmp_path = status_path.with_suffix(status_path.suffix + ".tmp")
        tmp_path.write_text(json.dumps(payload, indent=2) + "\n")
        tmp_path.replace(status_path)
