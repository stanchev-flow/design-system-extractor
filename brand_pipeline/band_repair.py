#!/usr/bin/env python3
"""band_repair.py — LLM band-repair adapter for the G4 convergence loop
(spec/convergence-loop.md §7.3).

Turns a `replica_repair` candidate (one below-bar band, gap-classified) into
ONE bounded, fact-fenced model call and applies the result through
`staged_author`'s existing patch machinery — the same fence, patch validation,
stage-shape checks, and atomic install the validator-repair loop uses. The
adapter builds the *bundle* (band-scoped fragments + evidence); the fence and
apply are `staged_author`'s, via a synthetic `RepairGroup`.

Doctrine (spec §7.3):
- AUTHORING gaps only in phase 2a. EVIDENCE and ASSET gaps return False (safe
  degradation → the hook marks them noSelfFix; phase 2b routes them to the L1
  targeted re-extract / deterministic asset branch).
- The model receives evidence + the diff note, NEVER the replica score — there
  is no metric-gaming gradient.
- A patch outside the fence raises AuthorBlocked, which the hook's exception
  path converts into snapshot-revert + noSelfFix (test-pinned in phase 1).
- Provider calls ride author_brand's SIGALRM wall-clock guard (the streaming
  hang class cannot stall the loop).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Callable

import yaml

_PKG_DIR = Path(__file__).resolve().parent
if str(_PKG_DIR) not in sys.path:  # staged_author/author_brand import flat
    sys.path.insert(0, str(_PKG_DIR))

import staged_author as sa  # noqa: E402

DEFAULT_MODEL = "claude-opus-4-8"
DEFAULT_TIMEOUT = 180.0          # per-call wall clock (SIGALRM-enforced)
DEFAULT_MAX_TOKENS = 8000   # a full layout-object replace truncated at 4000
GROUNDING_CAP = 8_000            # bytes of grounding YAML attached per band
OWNER = "band-repair"
SCHEMA_PATH = "/layouts"         # fence: brand.yaml /layouts + section-copy /layoutCopy


def _load_yaml(path: Path) -> dict:
    try:
        doc = yaml.safe_load(path.read_text())
        return doc if isinstance(doc, dict) else {}
    except Exception:
        return {}


def resolve_band(brand_dir: Path, section: str) -> dict | None:
    """Join a candidate's section id to its canon fragments: the brand.yaml
    layout (by id), its layout-library pattern (by patternRef), and its
    layoutCopy entry. None when the section matches no layout — the loop must
    not guess."""
    brand = _load_yaml(brand_dir / "brand.yaml")
    layouts = [l for l in (brand.get("layouts") or []) if isinstance(l, dict)]
    idx, layout = next(
        ((i, l) for i, l in enumerate(layouts)
         if str(l.get("id")) == section), (None, None))
    if layout is None:
        return None
    ref = layout.get("patternRef")
    pid = str(ref.get("id")) if isinstance(ref, dict) else (str(ref) if ref else "")
    pattern = None
    if pid:
        lib = _load_yaml(brand_dir / "layout-library.yaml")
        pattern = next(
            (p for p in (lib.get("patterns") or [])
             if isinstance(p, dict) and str(p.get("id")) == pid), None)
    copy_doc = _load_yaml(brand_dir / "section-copy.yaml")
    layout_copy = (copy_doc.get("layoutCopy") or {}).get(section)
    return {"index": idx, "layout": layout, "patternId": pid or None,
            "pattern": pattern, "layoutCopy": layout_copy}


def _parse_no_fix(raw: str) -> str | None:
    """The reason string when the model returned the legal no-authoring-fix
    verdict; None otherwise (normal patch flow)."""
    import re as _re
    text = (raw or "").strip()
    fenced = _re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, _re.S)
    if fenced:
        text = fenced.group(1)
    try:
        doc = json.loads(text)
    except Exception:
        return None
    if isinstance(doc, dict) and doc.get("noAuthoringFix") is True \
            and not doc.get("patches"):
        return str(doc.get("reason") or "no authoring fix")
    return None


def _grounding_excerpt(brand_dir: Path, section: str) -> str:
    """The band's own vision-grounding YAML when a filename matches; capped."""
    gdir = brand_dir / "evidence" / "grounding"
    if not gdir.is_dir():
        return ""
    slug = section.lower()
    for path in sorted(gdir.glob("*.yaml")):
        stem = path.stem.lower()
        if slug in stem or any(tok and tok in stem for tok in slug.split("-")[:2]):
            try:
                return path.read_text()[:GROUNDING_CAP]
            except Exception:
                return ""
    return ""


def build_band_bundle(brand_dir: Path, candidate: dict, resolved: dict) -> dict:
    """Band-scoped repair bundle. Deliberately NO score/bar fields — the model
    sees evidence and the measured diff note only (spec §7.3)."""
    fragments: dict[str, object] = {
        f"brand.yaml:/layouts/{resolved['index']}": resolved["layout"],
    }
    if resolved.get("layoutCopy") is not None:
        fragments[f"section-copy.yaml:/layoutCopy/{candidate['section']}"] = \
            resolved["layoutCopy"]
    bundle = {
        "bandRepair": {
            "section": candidate.get("section"),
            "capability": candidate.get("capability"),
            "measuredDiffNote": candidate.get("note"),
        },
        "failingFragments": fragments,
        # read-only context: the pattern is NOT patchable through this fence,
        # but its contentShape explains the slot vocabulary the layout binds.
        "patternContext": resolved.get("pattern"),
        "sectionGrounding": _grounding_excerpt(
            brand_dir, str(candidate.get("section") or "")),
        "instruction": (
            "The rendered band diverges from the source as described in "
            "measuredDiffNote. Correct ONLY the authored facts (layout slot "
            "widths/measures/geometry, copy bindings) so the deterministic "
            "composer reproduces the measured source. Move facts toward the "
            "attached evidence; never invent values. Patch the SMALLEST "
            "sufficient node to keep output short: op:merge on mapping fields "
            f"(e.g. /layouts/{resolved['index']}/gridRules), op:replace on "
            f"list fields (e.g. /layouts/{resolved['index']}/slots with the "
            "corrected slots array). Only replace the whole layout object at "
            f"/layouts/{resolved['index']} when most of it must change (merge "
            "is not supported on list elements). layoutCopy entries are "
            "mappings and accept op:merge."),
    }
    return bundle


def make_llm_repair_call(
    *,
    model: str = DEFAULT_MODEL,
    timeout: float = DEFAULT_TIMEOUT,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    reasoning_effort: str = "medium",
    caller: Callable[[str, str], str] | None = None,
    telemetry: list | None = None,
) -> Callable[[Path, dict], bool]:
    """Build the ``repair_call`` for ``replica_repair.make_repair_hook``.

    ``caller(system, user) -> str`` is injectable for tests; the default wires
    author_brand's provider + SIGALRM wall-clock guard. ``telemetry`` (a list)
    collects per-call {section, inputBytes, durationS} entries for the ledger.
    """

    def _default_caller(system: str, user: str) -> str:
        from author_brand import (_make_provider, _call_provider,
                                  _provider_available)
        # _provider_available loads .env.local keys into the env (the author
        # flow's own key path) — without it a bare _make_provider has no
        # credentials and every round dies on auth, quarantining bands.
        if not _provider_available():
            raise RuntimeError(
                "ANTHROPIC_API_KEY unavailable (checked env + .env.local) — "
                "converge repair calls cannot run")
        provider = _make_provider(model, reasoning_effort, timeout)
        return _call_provider(provider, system, user,
                              max_tokens=max_tokens, timeout=timeout)

    call = caller or _default_caller

    def repair_call(brand_dir: Path, candidate: dict) -> bool:
        import time as _time
        brand_dir = Path(brand_dir)
        if candidate.get("gap") != "authoring":
            return False  # evidence/asset → phase 2b; renderer never reaches here
        section = str(candidate.get("section") or "")
        resolved = resolve_band(brand_dir, section)
        if resolved is None:
            return False  # unjoinable band — never guess a target
        group = sa.RepairGroup(
            OWNER, SCHEMA_PATH,
            (f"BAND {section}: {candidate.get('capability')} — "
             f"{candidate.get('note')}",))
        bundle = build_band_bundle(brand_dir, candidate, resolved)
        system = (sa._repair_system(group)
                  + " EXCEPTION: if the attached facts already match the "
                    "evidence and NO authoring change can close the described "
                    "divergence (the gap is renderer behavior, not data), "
                    "return {\"patches\":[],\"noAuthoringFix\":true,"
                    "\"reason\":\"<one sentence>\"} instead of inventing a "
                    "no-op patch.")
        user = ("Repair the named band toward the attached measured evidence "
                "while preserving unrelated facts.\n"
                + json.dumps(bundle, ensure_ascii=False, separators=(",", ":")))
        t0 = _time.time()
        raw = call(system, user)
        # legal no-fix verdict (spec §2.1 demotion): the band's gap is not
        # authoring — the hook demotes it to a renderer work order.
        verdict = _parse_no_fix(raw)
        if verdict is not None:
            if telemetry is not None:
                telemetry.append({"section": section, "noAuthoringFix": True,
                                  "reason": verdict,
                                  "durationS": round(_time.time() - t0, 3)})
            return "demote"
        # AuthorBlocked from fence/shape violations propagates: the hook's
        # exception path reverts the round and quarantines the band.
        applied = sa.parse_and_apply_repair(brand_dir, group, raw)
        if telemetry is not None:
            telemetry.append({"section": section,
                              "inputBytes": len(system) + len(user),
                              "durationS": round(_time.time() - t0, 3),
                              "applied": applied})
        return bool(applied)

    return repair_call
