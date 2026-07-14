#!/usr/bin/env python3
"""Conversion-structure BRIEF-TIME GUIDANCE (steal 3, prompt side).

Data: contracts/conversion-structure.yaml (campaign section-sequence grammars).
Spec: spec/conversion-structure.md.

This module owns exactly ONE of the contract's two deterministic consumers:
``render_guidance_block`` projects a campaign's grammar into prompt prose for
generate_composition.build_prompt (opt-in ``conversion_guidance=`` parameter /
``inject_conversion_guidance`` flag; default None keeps the assembled prompt
BYTE-IDENTICAL — the hero_candidates fact-gated pattern). Zero extra LLM calls:
same single model call, slightly longer user prompt, riding WITH the brief.

The OTHER consumer — the post-composition/post-render CHECKER — lives in
``conversion_audit.py`` (constraint interpreter, lane campaign resolution,
rendered re-grounding, reports). This module deliberately implements no
constraint interpretation: one checker, one owner (AS-06 discipline).

Doubly fact-gated injection contract:
  1. the caller must opt in (``inject_conversion_guidance=True`` — default False,
     so the pass-3 prompt-injection architecture decision stays unconstrained);
  2. the brief must declare a known ``campaignType:`` in its frontmatter.
Absent either, ``render_guidance_block`` returns None and the prompt is
byte-identical to the un-guided assembly (test-pinned).
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

CONTRACTS_PATH = Path(__file__).resolve().parent / "contracts" / "conversion-structure.yaml"


def load_contracts(path: Path | None = None) -> dict:
    doc = yaml.safe_load((path or CONTRACTS_PATH).read_text()) or {}
    if str(doc.get("schemaVersion")) != "conversion-structure.v1":
        raise ValueError(f"unexpected schemaVersion {doc.get('schemaVersion')!r}")
    return doc


def campaign_by_id(doc: dict, campaign_id: str) -> dict | None:
    for c in doc.get("campaigns") or []:
        if c.get("id") == campaign_id:
            return c
    return None


# ── brief frontmatter ──────────────────────────────────────────────────────────────

_FRONTMATTER_RX = re.compile(r"\A\s*---\s*\n(.*?)\n---\s*\n", re.S)


def parse_brief_frontmatter(brief_text: str) -> dict:
    """YAML frontmatter between the leading ``---`` fences; {} when absent/bad."""
    m = _FRONTMATTER_RX.match(brief_text or "")
    if not m:
        return {}
    try:
        data = yaml.safe_load(m.group(1))
    except yaml.YAMLError:
        return {}
    return data if isinstance(data, dict) else {}


def resolve_campaign_id(brief_text: str, doc: dict) -> str | None:
    """The brief's declared ``campaignType:`` when it names a known campaign."""
    cid = parse_brief_frontmatter(brief_text).get("campaignType")
    return cid if isinstance(cid, str) and campaign_by_id(doc, cid) else None


# ── guidance projection ─────────────────────────────────────────────────────────────

def _spec_label(spec: dict) -> str:
    return spec.get("family") or "|".join(spec.get("anyOf") or []) or "?"


def render_guidance_block(brief_text: str, doc: dict | None = None) -> str | None:
    """The campaign grammar as prompt prose, or None when the brief declares no
    (known) campaignType — None keeps build_prompt byte-identical (fact-gated).

    Constraint rows render as one bullet each, the ``why:`` note verbatim (the
    contract authors those notes AS guidance prose). Severity is deliberately
    not surfaced: at brief time everything is guidance; enforcement staging is
    the checker's concern (conversion_audit.py)."""
    doc = doc or load_contracts()
    cid = resolve_campaign_id(brief_text, doc)
    if cid is None:
        return None
    c = campaign_by_id(doc, cid)
    band = c.get("depthBand") or {}
    form = c.get("formDepth") or {}
    lines = [
        f"# CONVERSION STRUCTURE — {c.get('name')} (campaign: {cid})",
        "Genre grammar for this campaign type (ADVISORY prior — the brief's explicit",
        "asks outrank it; brand evidence outranks both):",
        f"- funnel stage: {c.get('funnelStage')} — aim for {band.get('min')}-{band.get('max')} "
        "content sections (chrome excluded).",
        f"- conversion moment: {c.get('conversionMoment')} — "
        + " ".join(str(c.get("intent") or "").split()),
    ]
    if form:
        note = " ".join(str(form.get("note") or "").split())
        lines.append(f"- form depth: {form.get('minFields')}-{form.get('maxFields')} fields"
                     + (f" — {note}" if note else "") + ".")
    for row in c.get("constraints") or []:
        why = " ".join(str(row.get("why") or "").split())
        kind, label = str(row.get("kind") or ""), _spec_label(row)
        if kind == "opens":
            head = f"open with a {label} section"
        elif kind == "closes":
            head = f"close on {label}"
        elif kind == "present":
            head = f"{label}: {row.get('min', 0)}-{row.get('max', 'any')} section(s)"
        elif kind == "window":
            head = f"{label} lands within the first {row.get('firstN')} sections"
        elif kind == "afterIndex":
            head = f"no {label} before position {row.get('minIndex')}"
        elif kind == "before":
            head = f"{row.get('first')} before {row.get('then')}"
        elif kind == "adjacent":
            head = (f"{row.get('family')} within {row.get('maxGap')} beat(s) of "
                    f"{'|'.join(row.get('toAnyOf') or [])}")
        else:
            continue
        lines.append(f"- {head} — {why}" if why else f"- {head}")
    return "\n".join(lines)
