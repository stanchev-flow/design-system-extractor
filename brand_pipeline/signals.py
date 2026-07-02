#!/usr/bin/env python3
"""signals.py - append a signal to the brand signal loop (see spec/signal-loop.md).

Brand-agnostic, data-driven. Takes a run dir (runs/<brand>) or a brand.yaml path
and appends one JSONL line to runs/<brand>/brand/signals.log.

Three signal sources (signal-loop.md S3): creation | iteration | build-failure.

Contradiction handling (signal-loop.md S5, one-off-and-queue DEFAULT): if a signal
contradicts an existing brand.yaml rule AND it is not a build-failure, this script
- records the signal with resolution=one-off, scope=one-off
- queues a clarifying question in pending-questions.yaml
- NEVER mutates brand.yaml (consolidation, with user confirmation, does that)

Stdlib + pyyaml only.

Examples:
  # creation signal (seeds the baseline; no conflict expected)
  python3 brand_pipeline/signals.py runs/woodwave \
      --type creation --section-id opening-bookend \
      --rule-key "neverDo.no-buttons" \
      --text "all actions typographic with arrows/slashes; no filled buttons" \
      --scope design-language --confidence high

  # iteration signal that contradicts an existing rule -> one-off + queued question
  python3 brand_pipeline/signals.py runs/woodwave \
      --type iteration --section-id about-run \
      --text "user: put a bordered card around the third about block" \
      --conflict-with "neverDo.no-cards-on-cream"

  # build-failure signal (platform fact; consolidation auto-promotes it)
  python3 brand_pipeline/signals.py runs/woodwave \
      --type build-failure --section-id conversion \
      --rule-key "recipePolicy.formIdUnique" \
      --text "Form/Webflow/Lead requires unique Form ID; build rejected duplicate"
"""
from __future__ import annotations

import argparse
import json
import random
import string
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.stderr.write("signals.py requires pyyaml (pip install pyyaml)\n")
    raise

VALID_TYPES = ("creation", "iteration", "build-failure")
VALID_SCOPES = ("design-language", "one-off")
VALID_CONFIDENCE = ("high", "medium", "low")


# --- small shared helpers (also imported by consolidate.py) -------------------

def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rand(n: int = 2) -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))


def gen_id(prefix: str) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    return f"{prefix}-{ts}-{_rand(2)}"


def resolve_brand_dir(run_arg: str) -> Path:
    """Accept runs/<brand>, runs/<brand>/brand, or a brand.yaml path; return brand dir."""
    p = Path(run_arg)
    if p.is_file() and p.name.endswith(".yaml"):
        return p.parent
    if (p / "brand" / "brand.yaml").exists() or (p / "brand").is_dir():
        return p / "brand"
    return p


def load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text())
    return data if isinstance(data, dict) else {}


def resolve_rule(doc: Dict[str, Any], dotted: Optional[str]) -> Tuple[bool, Optional[str], Optional[str]]:
    """Resolve a dotted brand.yaml path like 'neverDo.no-cards-on-cream' or
    'recipePolicy.formIdUnique' or 'compositionRules.z-order'.

    Returns (found, statement, confidence). 'statement' is the human rule text when
    available, else the stringified value.
    """
    if not dotted:
        return False, None, None
    head, _, rest = dotted.partition(".")
    node = doc.get(head)
    if node is None:
        return False, None, None
    # list-of-rule-envelopes keyed by `id` (neverDo, compositionRules, ...)
    if isinstance(node, list):
        for item in node:
            if isinstance(item, dict) and item.get("id") == rest:
                stmt = item.get("statement") or _stringify(item.get("value"))
                return True, stmt, item.get("confidence")
        return False, None, None
    # dict node (recipePolicy, surfaceGrammar, tokens, ...)
    if isinstance(node, dict):
        cur: Any = node
        for part in rest.split("."):
            if not part:
                break
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                return False, None, None
        if isinstance(cur, dict):
            stmt = cur.get("statement") or _stringify(cur.get("value"))
            return True, stmt, cur.get("confidence")
        return True, _stringify(cur), None
    return False, None, None


def _stringify(v: Any) -> Optional[str]:
    if v is None:
        return None
    if isinstance(v, str):
        return v
    return json.dumps(v, ensure_ascii=False)


# --- IO -----------------------------------------------------------------------

def append_signal(brand_dir: Path, signal: Dict[str, Any]) -> Path:
    brand_dir.mkdir(parents=True, exist_ok=True)
    log = brand_dir / "signals.log"
    with log.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(signal, ensure_ascii=False) + "\n")
    return log


def enqueue_question(brand_dir: Path, question: Dict[str, Any]) -> Path:
    """Append a question to pending-questions.yaml (the queue file is read-merge-write;
    signals.log stays strictly append-only). Dedupe by open question on same conflictWith."""
    qpath = brand_dir / "pending-questions.yaml"
    doc = load_yaml(qpath)
    questions: List[Dict[str, Any]] = doc.get("questions") or []
    for q in questions:
        if q.get("status") == "open" and q.get("conflictWith") == question.get("conflictWith"):
            return qpath  # an unanswered question already exists; do not duplicate
    questions.append(question)
    doc["questions"] = questions
    qpath.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True))
    return qpath


def find_open_question(brand_dir: Path, conflict_with: Optional[str]) -> Optional[str]:
    if not conflict_with:
        return None
    doc = load_yaml(brand_dir / "pending-questions.yaml")
    for q in doc.get("questions") or []:
        if q.get("status") == "open" and q.get("conflictWith") == conflict_with:
            return q.get("id")
    return None


# --- main ---------------------------------------------------------------------

def build_signal(args: argparse.Namespace, brand_dir: Path) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
    brand_yaml = brand_dir / "brand.yaml"
    doc = load_yaml(brand_yaml)

    # A contradiction is keyed by --conflict-with (explicit) or detected if the
    # --rule-key already exists and the signal is an iteration redirect.
    conflict_with = args.conflict_with
    existing_stmt = None
    existing_conf = None
    if conflict_with:
        found, existing_stmt, existing_conf = resolve_rule(doc, conflict_with)
        detected = found
    else:
        detected = False

    is_build_failure = args.type == "build-failure"
    is_contradiction = bool(detected) and not is_build_failure

    # Resolution + scope per protocol.
    if is_contradiction:
        resolution = "one-off"
        scope = "one-off"
        confidence = args.confidence or "low"
    elif is_build_failure:
        resolution = "promote"            # consolidation auto-promotes platform facts
        scope = "design-language"
        confidence = "high"
    else:
        resolution = "promote" if args.scope == "design-language" else "one-off"
        scope = args.scope or "design-language"
        confidence = args.confidence or ("high" if args.type == "creation" else "medium")

    sig_id = gen_id("sig")
    question_id = None
    question = None
    if is_contradiction:
        existing_qid = find_open_question(brand_dir, conflict_with)
        if existing_qid:
            question_id = existing_qid  # link to existing unanswered question (no dup)
        else:
            question_id = sig_id.replace("sig-", "q-", 1)
            question = {
                "id": question_id,
                "signalId": sig_id,
                "sectionId": args.section_id,
                "status": "open",
                "conflictWith": conflict_with,
                "existingRule": {
                    "statement": existing_stmt,
                    "confidence": existing_conf,
                },
                "proposedChange": {
                    "signalText": args.text,
                    "proposedValue": args.proposed_value,
                },
                "appliedAs": "one-off",
                "options": ["update-design-language", "one-off", "keep-existing"],
                "askedAt": now_iso(),
                "answer": None,
                "answeredAt": None,
                "resolution": None,
                "changelogRef": None,
            }

    signal = {
        "id": sig_id,
        "type": args.type,
        "sectionId": args.section_id,
        "text": args.text,
        "ruleKey": args.rule_key,
        "detectedConflict": bool(detected),
        "conflictWith": conflict_with,
        "resolution": resolution,
        "scope": scope,
        "confidence": confidence,
        "questionId": question_id,
        "timestamp": now_iso(),
    }
    return signal, question


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Append a signal to runs/<brand>/brand/signals.log")
    ap.add_argument("run_dir", help="runs/<brand>, runs/<brand>/brand, or a brand.yaml path")
    ap.add_argument("--type", required=True, choices=VALID_TYPES)
    ap.add_argument("--text", required=True, help="raw observation or user/system message")
    ap.add_argument("--section-id", default=None, help="section/layout id, or omit for global")
    ap.add_argument("--rule-key", default=None, help="dotted brand.yaml path, or omit if new")
    ap.add_argument("--conflict-with", default=None,
                    help="dotted brand.yaml path this signal contradicts (triggers one-off+queue)")
    ap.add_argument("--proposed-value", default=None,
                    help="what the rule would become if the user promotes the contradiction")
    ap.add_argument("--scope", default=None, choices=VALID_SCOPES)
    ap.add_argument("--confidence", default=None, choices=VALID_CONFIDENCE)
    args = ap.parse_args(argv)

    brand_dir = resolve_brand_dir(args.run_dir)
    signal, question = build_signal(args, brand_dir)
    log = append_signal(brand_dir, signal)

    if question is not None:
        qpath = enqueue_question(brand_dir, question)
        sys.stderr.write(
            f"contradiction with {signal['conflictWith']}: applied as ONE-OFF, "
            f"queued question {question['id']} in {qpath} (brand.yaml NOT mutated)\n")

    print(json.dumps({
        "appended": str(log),
        "id": signal["id"],
        "type": signal["type"],
        "scope": signal["scope"],
        "resolution": signal["resolution"],
        "detectedConflict": signal["detectedConflict"],
        "questionId": signal["questionId"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
