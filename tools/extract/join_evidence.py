#!/usr/bin/env python3
"""join_evidence.py — Phase 1 responsive-fidelity JOIN of separate extraction outputs.

Today ``mine_css`` (rules incl. @media/:hover), ``measure_computed`` (computed
values across the 1440/1920/960/375 tier ladder) and vision grounding are SEPARATE
documents on disk that are never joined at the element level. The downstream
harness therefore keeps a flattened single-viewport px snapshot and loses the
responsive CSS behavior that governs a real page — e.g. the hero's
``calc(100dvh - var(--global-nav-header-height))`` height, the footer's grid
``@media`` breakpoint reflow, and the mega-nav's stateful/`@media` background.

This module produces the JOINED TRUTH: for each measured element/section it binds
the governing CSS rules (matched against the SAVED DOM, preserving @media and
pseudo-state rules, plus the resolved ``var()``/``calc()`` custom-property chains
as LITERAL expressions), the multi-viewport computed ladder, and the vision role
of the owning section. It is a pure JOIN — it does NOT re-measure, does NOT alter
existing evidence files, and does NOT touch the harness/renderer/authoring.

Read-only over the capture + existing evidence; writes only the joined output
(default ``<evidence>/joined-evidence.json``).

Usage:
    ./venv/bin/python tools/extract/join_evidence.py \
        --evidence runs/<brand>/brand/evidence/ [--capture screenshots/<brand>/] \
        [--out runs/<brand>/brand/evidence/joined-evidence.json]

The saved HTML is auto-discovered from --capture, or from the ``source`` field of
computed-styles.json / section-rects.json resolved against --project-root.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup, Tag

SCHEMA = "joined-evidence.v1"

# the canonical measurement tiers measure_computed emits (desktop-xl/desktop/tablet/mobile)
TIER_ORDER = ("1920", "1440", "960", "375")
PRIMARY_TIER = "1440"  # measure_computed's default primary viewport (section rects live here)


# ── selector parsing (brand-agnostic, tolerant of minified/compound selectors) ──

def split_selector_list(selector: str) -> list[str]:
    """Split a comma selector-list at top level (commas inside ()/[] are kept)."""
    parts, buf, depth = [], [], 0
    for ch in selector:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth = max(0, depth - 1)
        if ch == "," and depth == 0:
            parts.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
    if buf:
        parts.append("".join(buf).strip())
    return [p for p in parts if p]


def _key_compound(selector: str) -> str:
    """Rightmost compound (after the last top-level combinator ` `, `>`, `+`, `~`)."""
    depth, last = 0, 0
    for i, ch in enumerate(selector):
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth = max(0, depth - 1)
        elif depth == 0 and ch in " >+~":
            last = i + 1
    return selector[last:].strip()


_PSEUDO_RE = re.compile(r"::?[a-zA-Z][a-zA-Z-]*(?:\([^)]*\))?")
_ATTR_RE = re.compile(r"\[[^\]]*\]")
_CLASS_RE = re.compile(r"\.(-?[_a-zA-Z][\w-]*)")
_ID_RE = re.compile(r"#(-?[_a-zA-Z][\w-]*)")
_TAG_RE = re.compile(r"^([a-zA-Z][\w-]*|\*)")


def parse_key_compound(selector: str) -> dict:
    """Structured view of a selector's KEY compound (the element the rule paints).

    ``classes``/``id``/``tag`` describe the element the compound targets (pseudo
    and attribute qualifiers are stripped from that match but preserved for the
    record). This is what we test a DOM node against for self/descendant binding.
    """
    compound = _key_compound(selector)
    pseudos = _PSEUDO_RE.findall(compound)
    attrs = _ATTR_RE.findall(compound)
    base = _ATTR_RE.sub("", _PSEUDO_RE.sub("", compound))
    classes = set(_CLASS_RE.findall(base))
    ids = _ID_RE.findall(base)
    tagm = _TAG_RE.match(base.strip())
    tag = tagm.group(1) if tagm else None
    if tag == "*":
        tag = None
    return {
        "classes": frozenset(classes),
        "id": ids[0] if ids else None,
        "tag": tag.lower() if tag else None,
        "pseudos": pseudos,
        "attrs": attrs,
    }


def selector_tokens(selector: str) -> tuple[frozenset, frozenset]:
    """ALL class/id tokens referenced anywhere in a selector (incl. inside
    :has()/:is()/:not()/[attr]) — used for contextual, component-scoped binding."""
    return frozenset(_CLASS_RE.findall(selector)), frozenset(_ID_RE.findall(selector))


# ── DOM index over the saved capture (Euler intervals for O(1) subtree tests) ──

class DomIndex:
    """Preorder index of the saved DOM: subtree membership via [tin, tout]."""

    def __init__(self, html: str):
        self.soup = BeautifulSoup(html, "html.parser")
        self.nodes: list[Tag] = []
        self.tout: list[int] = []
        self.tag: list[str] = []
        self.classes: list[frozenset] = []
        self.node_id: list[str | None] = []
        self.idx_of: dict[int, int] = {}
        self.class_index: dict[str, list[int]] = {}
        self.id_index: dict[str, int] = {}
        self._build()

    def _build(self) -> None:
        work = [(self.soup, False)]
        while work:
            node, exited = work.pop()
            if exited:
                self.tout[self.idx_of[id(node)]] = len(self.nodes) - 1
                continue
            idx = len(self.nodes)
            self.idx_of[id(node)] = idx
            self.nodes.append(node)
            self.tout.append(idx)
            cls = node.get("class") or []
            cls_set = frozenset(cls)
            self.tag.append((node.name or "").lower())
            self.classes.append(cls_set)
            nid = node.get("id") or None
            self.node_id.append(nid)
            for c in cls:
                self.class_index.setdefault(c, []).append(idx)
            if nid:
                self.id_index.setdefault(nid, idx)
            work.append((node, True))
            kids = [c for c in node.children if isinstance(c, Tag)]
            for c in reversed(kids):
                work.append((c, False))

    def index_of(self, tag: Tag) -> int | None:
        return self.idx_of.get(id(tag))

    def candidates(self, key: dict) -> list[int]:
        """Node indices whose own classes/id/tag satisfy a key compound."""
        if key["id"]:
            base = [self.id_index[key["id"]]] if key["id"] in self.id_index else []
        elif key["classes"]:
            posting_lists = [self.class_index.get(c, []) for c in key["classes"]]
            if not all(posting_lists):
                return []
            base = set(posting_lists[0])
            for pl in posting_lists[1:]:
                base &= set(pl)
            base = sorted(base)
        else:
            return []
        out = []
        for i in base:
            if key["classes"] and not key["classes"] <= self.classes[i]:
                continue
            if key["tag"] and key["tag"] != self.tag[i]:
                continue
            out.append(i)
        return out

    def node_matches(self, key: dict, i: int) -> bool:
        if not key["classes"] and not key["id"]:
            return False  # tag-only / universal is not a self/descendant anchor
        if key["classes"] and not key["classes"] <= self.classes[i]:
            return False
        if key["id"] and key["id"] != self.node_id[i]:
            return False
        if key["tag"] and key["tag"] != self.tag[i]:
            return False
        return True

    def subtree_local(self, token: str, tin: int, tout: int, is_id: bool) -> bool:
        """True when every node bearing ``token`` lives inside [tin, tout] — i.e.
        the token is owned by this component (safe contextual anchor)."""
        if is_id:
            p = self.id_index.get(token)
            return p is not None and tin <= p <= tout
        postings = self.class_index.get(token)
        return bool(postings) and all(tin <= p <= tout for p in postings)

    def locate_by_signature(self, classes: str, tag: str | None, node_id: str | None):
        """Best DOM node for a measured element by id, else by class superset."""
        if node_id and node_id in self.id_index:
            return self.id_index[node_id]
        tokens = [t for t in (classes or "").split() if t]
        if not tokens:
            return None
        posting_lists = [self.class_index.get(t, []) for t in tokens]
        if not all(posting_lists):
            # tolerate truncated class strings: drop trailing empty/partial token
            posting_lists = [self.class_index.get(t, []) for t in tokens if self.class_index.get(t)]
            if not posting_lists:
                return None
        cand = set(posting_lists[0])
        for pl in posting_lists[1:]:
            cand &= set(pl)
        if not cand:
            return None
        if tag:
            tagged = [i for i in cand if self.tag[i] == tag.lower()]
            if tagged:
                cand = set(tagged)
        return min(cand)


# ── rule pre-parse + binding ─────────────────────────────────────────────────

def parse_rules(rules: list[dict]) -> list[dict]:
    """Pre-parse each css-rules row into per-selector-part key/token structures."""
    parsed = []
    for r in rules:
        if r.get("kind") == "keyframes":
            continue
        selector = r.get("selector") or ""
        parts = []
        for sp in split_selector_list(selector):
            key = parse_key_compound(sp)
            cls_tokens, id_tokens = selector_tokens(sp)
            parts.append({"selector": sp, "key": key,
                          "classTokens": cls_tokens, "idTokens": id_tokens})
        parsed.append({
            "file": r.get("file"), "media": r.get("media") or "",
            "selector": selector, "decls": r.get("decls") or "",
            "parts": parts,
        })
    return parsed


def bind_rules(dom: DomIndex, tin: int, tout: int, own_classes: frozenset,
               own_tag: str | None, own_id: str | None,
               parsed_rules: list[dict], _cand_cache: dict) -> list[dict]:
    """Return governing rules for the element at [tin, tout], each tagged with a
    scope: ``self`` (rule paints the element), ``descendant`` (rule paints a node
    in its subtree — e.g. footer grid @media on ``.global-footer__nav-column``),
    or ``contextual`` (rule is conditioned on a component-owned token, e.g.
    ``body:has(.global-nav-main)::after`` or a descendant link :hover)."""
    bound: list[dict] = []
    seen: set[tuple] = set()
    self_key = {"classes": own_classes, "id": own_id, "tag": own_tag}
    for rule in parsed_rules:
        best_scope = None
        matched_selector = None
        matched_pseudos: list[str] = []
        for part in rule["parts"]:
            key = part["key"]
            scope = None
            # self: the key compound targets THIS element
            if key["classes"] or key["id"]:
                if (key["classes"] <= own_classes
                        and (not key["id"] or key["id"] == own_id)
                        and (not key["tag"] or key["tag"] == own_tag)):
                    scope = "self"
            if scope is None and (key["classes"] or key["id"]):
                cache_key = (key["id"], key["classes"], key["tag"])
                cand = _cand_cache.get(cache_key)
                if cand is None:
                    cand = dom.candidates(key)
                    _cand_cache[cache_key] = cand
                if any(tin < c <= tout for c in cand):
                    scope = "descendant"
            if scope is None:
                for t in part["classTokens"]:
                    if dom.subtree_local(t, tin, tout, is_id=False):
                        scope = "contextual"
                        break
                if scope is None:
                    for t in part["idTokens"]:
                        if dom.subtree_local(t, tin, tout, is_id=True):
                            scope = "contextual"
                            break
            if scope is None:
                continue
            rank = {"self": 3, "descendant": 2, "contextual": 1}
            if best_scope is None or rank[scope] > rank[best_scope]:
                best_scope = scope
                matched_selector = part["selector"]
                matched_pseudos = key["pseudos"]
        if best_scope is None:
            continue
        dedupe = (rule["file"], rule["media"], rule["selector"], rule["decls"])
        if dedupe in seen:
            continue
        seen.add(dedupe)
        bound.append({
            "scope": best_scope,
            "media": rule["media"],
            "selector": rule["selector"],
            "matchedSelector": matched_selector,
            "pseudo": [p for p in matched_pseudos if p.startswith(":")
                       and p not in (":root",)],
            "decls": rule["decls"],
            "file": rule["file"],
        })
    return bound


# ── custom-property / calc() chain resolution (keep LITERAL expressions) ──────

_VARDEF_RE = re.compile(r"(--[\w-]+)\s*:\s*([^;]+)")
_VARREF_RE = re.compile(r"var\(\s*(--[\w-]+)")


def build_var_defs(rules: list[dict]) -> dict[str, list[dict]]:
    """Map custom-property name -> [{media, value, selector, file}] over ALL rules
    (so ``--global-nav-header-height`` collects its 56px default AND its 128px
    ``@media(width >= 1080px)`` override)."""
    defs: dict[str, list[dict]] = {}
    for r in rules:
        if r.get("kind") == "keyframes":
            continue
        for name, value in _VARDEF_RE.findall(r.get("decls") or ""):
            defs.setdefault(name, []).append({
                "media": r.get("media") or "",
                "value": value.strip(),
                "selector": (r.get("selector") or "")[:160],
                "file": r.get("file"),
            })
    return defs


def resolve_custom_properties(bound_rules: list[dict],
                              var_defs: dict[str, list[dict]]) -> dict[str, list[dict]]:
    """Resolve the var() graph referenced by the element's bound rules, keeping
    literal expressions (e.g. ``calc(100dvh - var(--global-nav-header-height))``
    stays intact; the referenced var carries its per-@media literal values)."""
    referenced: set[str] = set()
    for br in bound_rules:
        referenced.update(_VARREF_RE.findall(br["decls"]))
    resolved: dict[str, list[dict]] = {}
    queue = list(referenced)
    while queue:
        name = queue.pop()
        if name in resolved:
            continue
        entries = var_defs.get(name, [])
        resolved[name] = entries
        for e in entries:
            for ref in _VARREF_RE.findall(e["value"]):
                if ref not in resolved:
                    queue.append(ref)
    return resolved


# ── vision grounding load + match ─────────────────────────────────────────────

def load_grounding(grounding_dir: Path) -> list[dict]:
    try:
        import yaml
    except Exception:  # pragma: no cover
        return []
    out = []
    if not grounding_dir.is_dir():
        return out
    for p in sorted(grounding_dir.glob("*.yaml")):
        try:
            doc = yaml.safe_load(p.read_text(errors="replace")) or {}
        except Exception:
            continue
        src = doc.get("_source") or {}
        dom_classes = (src.get("domClasses") or "").strip()
        m = re.match(r"section-(\d+)-", p.name)
        out.append({
            "file": p.name,
            "sectionRole": doc.get("sectionRole"),
            "domClasses": dom_classes,
            "domTokens": [t for t in dom_classes.split() if t],
            "index": int(m.group(1)) if m else None,
        })
    return out


def match_grounding(element_tokens: list[str], grounding: list[dict],
                    role_hint: str | None = None) -> dict | None:
    """Pick the grounding entry whose ``_source.domClasses`` shares the most
    leading tokens with the element. Falls back to a sectionRole hint for chrome
    (header/navbar, footer) when class overlap is absent."""
    etoks = set(element_tokens)
    best, best_score = None, 0
    for g in grounding:
        if not g["domTokens"]:
            continue
        shared = etoks & set(g["domTokens"])
        # weight leading-token agreement (the section class prefix is distinctive)
        lead = 0
        for a, b in zip(element_tokens, g["domTokens"]):
            if a == b:
                lead += 1
            else:
                break
        score = len(shared) * 10 + lead
        if score > best_score:
            best, best_score = g, score
    if best is not None and best_score > 0:
        return best
    if role_hint:
        roles = {"header": {"navbar", "header", "nav"},
                 "footer": {"footer"}}.get(role_hint, {role_hint})
        for g in grounding:
            if (g["sectionRole"] or "").lower() in roles:
                return g
    return None


# ── computed-ladder assembly (join what measure_computed captured on disk) ─────

def _heading_tag_owner(dom: DomIndex, tag: str) -> int | None:
    """DOM index of the FIRST element of ``tag`` (measure_computed measures the
    first instance per tag, so that instance's owning section gets its ladder)."""
    postings = [i for i, t in enumerate(dom.tag) if t == tag]
    return min(postings) if postings else None


def section_ladder(section_rect: dict, computed: dict, dom: DomIndex,
                   tin: int, tout: int) -> dict:
    """Per-tier record for a section: primary-tier rect+surface, plus any tier
    container/heading facts whose measured DOM node falls inside its subtree."""
    tiers = computed.get("tiers") or {}
    # which heading tags were measured inside THIS section's subtree
    owned_headings = []
    for tg in ("h1", "h2", "h3", "h4", "h5", "h6", "p"):
        owner = _heading_tag_owner(dom, tg)
        if owner is not None and tin <= owner <= tout:
            owned_headings.append(tg)
    # container owner class this section owns (content-owner container = h1's host)
    ladder: dict[str, dict | None] = {}
    for tier in TIER_ORDER:
        rec: dict = {}
        tdata = tiers.get(tier) or {}
        # headings measured at this tier that belong to this section
        h_at_tier = {}
        for tg in owned_headings:
            hv = (tdata.get("headings") or {}).get(tg)
            if hv:
                h_at_tier[tg] = hv
        if h_at_tier:
            rec["headings"] = h_at_tier
        # container facts whose measured node is inside this subtree
        conts = []
        for cf in (tdata.get("containerFacts") or []):
            node = dom.locate_by_signature(cf.get("classes", ""), cf.get("tag"), None)
            if node is not None and tin <= node <= tout:
                conts.append(cf)
        if conts:
            rec["containers"] = conts
        if tier == PRIMARY_TIER:
            rec["rect"] = section_rect.get("rect")
            rec["backgroundColor"] = section_rect.get("backgroundColor")
        ladder[tier] = rec or None
    return ladder


def heading_ladder(tag: str, computed: dict) -> dict:
    tiers = computed.get("tiers") or {}
    ladder = {}
    for tier in TIER_ORDER:
        ladder[tier] = ((tiers.get(tier) or {}).get("headings") or {}).get(tag)
    return ladder


def chrome_ladder(owner: str, chrome_rect: dict, chrome_computed: dict,
                  computed: dict) -> dict:
    tiers = computed.get("tiers") or {}
    ladder: dict[str, dict | None] = {}
    for tier in TIER_ORDER:
        rec: dict = {}
        conts = [cf for cf in ((tiers.get(tier) or {}).get("containerFacts") or [])
                 if (cf.get("owner") or "").startswith(owner)]
        if conts:
            rec["containers"] = conts
        if tier == PRIMARY_TIER:
            if chrome_rect:
                rec["rect"] = chrome_rect.get("rect")
            if chrome_computed:
                rec["surface"] = {k: v for k, v in chrome_computed.items() if k != "_rect"}
        ladder[tier] = rec or None
    return ladder


# ── main join ─────────────────────────────────────────────────────────────────

def _resolve_html(evidence_dir: Path, capture: Path | None, html: Path | None,
                  project_root: Path, computed: dict, section_rects: dict) -> Path:
    if html:
        return html
    if capture:
        pages = sorted(capture.glob("*.htm*"), key=lambda p: p.stat().st_size, reverse=True)
        if pages:
            return pages[0]
    for doc in (computed, section_rects):
        src = doc.get("source")
        if src:
            cand = (project_root / src)
            if cand.is_file():
                return cand
    raise SystemExit("could not resolve saved HTML (pass --capture or --html)")


def join(evidence_dir: Path, capture: Path | None = None, html: Path | None = None,
         project_root: Path | None = None) -> dict:
    project_root = project_root or Path.cwd()
    css_doc = json.loads((evidence_dir / "css-rules.json").read_text())
    computed = json.loads((evidence_dir / "computed-styles.json").read_text())
    section_rects = json.loads((evidence_dir / "section-rects.json").read_text())
    html_path = _resolve_html(evidence_dir, capture, html, project_root, computed, section_rects)

    dom = DomIndex(html_path.read_text(errors="replace"))
    rules = css_doc.get("rules", [])
    parsed_rules = parse_rules(rules)
    var_defs = build_var_defs(rules)
    grounding = load_grounding(evidence_dir / "grounding")
    cand_cache: dict = {}

    records: list[dict] = []

    def make_record(element_id, kind, node_idx, classes, tag, node_id,
                    ladder, vision, extra_prov=None):
        if node_idx is not None:
            tin, tout = node_idx, dom.tout[node_idx]
            own_classes = dom.classes[node_idx]
            own_tag = dom.tag[node_idx]
            own_id = dom.node_id[node_idx]
            bound = bind_rules(dom, tin, tout, own_classes, own_tag, own_id,
                               parsed_rules, cand_cache)
        else:
            bound = []
        custom_props = resolve_custom_properties(bound, var_defs)
        scopes = {"self": 0, "descendant": 0, "contextual": 0}
        for b in bound:
            scopes[b["scope"]] += 1
        dom_selector = None
        if node_idx is not None:
            if own_id:
                dom_selector = f"#{own_id}"
            elif own_classes:
                dom_selector = "".join(f".{c}" for c in sorted(own_classes))
        prov = {
            "cssRules": "css-rules.json",
            "computed": "computed-styles.json",
            "sectionRects": "section-rects.json",
            "domLocated": node_idx is not None,
        }
        if vision:
            prov["grounding"] = vision["file"]
        if extra_prov:
            prov.update(extra_prov)
        return {
            "elementId": element_id,
            "kind": kind,
            "tag": tag,
            "id": node_id or "",
            "classes": classes,
            "domSelector": dom_selector,
            "computedLadder": ladder,
            "cssRules": bound,
            "cssRuleScopes": scopes,
            "customProperties": custom_props,
            "visionRole": (vision or {}).get("sectionRole"),
            "visionGroundingFile": (vision or {}).get("file"),
            "provenance": prov,
        }

    # 1. content sections (section-rects) — the primary joined targets
    for sec in section_rects.get("sections", []):
        classes = sec.get("classes", "")
        tag = sec.get("tag")
        node_id = sec.get("id") or None
        node_idx = dom.locate_by_signature(classes, tag, node_id)
        etoks = classes.split()
        vision = match_grounding(etoks, grounding)
        if node_idx is not None:
            tin, tout = node_idx, dom.tout[node_idx]
            ladder = section_ladder(sec, computed, dom, tin, tout)
        else:
            ladder = {PRIMARY_TIER: {"rect": sec.get("rect"),
                                     "backgroundColor": sec.get("backgroundColor")}}
        records.append(make_record(
            f"section-{sec.get('index'):02d}" if isinstance(sec.get("index"), int)
            else f"section-{classes[:24]}",
            "section", node_idx, classes, tag, node_id, ladder, vision))

    # 2. chrome (header/footer)
    chrome_rects = {c.get("name"): c for c in section_rects.get("chrome", [])}
    chrome_computed = computed.get("chrome", {})
    for owner in ("header", "footer"):
        cr = chrome_rects.get(owner)
        classes = (cr or {}).get("classes", "")
        if owner == "header":
            node_idx = (dom.locate_by_signature(classes, None, None)
                        or (dom.class_index.get("global-nav-header", [None])[0]))
            if node_idx is None:
                h = dom.soup.find("header")
                node_idx = dom.index_of(h) if h else None
        else:
            footers = dom.soup.find_all("footer")
            node_idx = dom.index_of(footers[-1]) if footers else \
                dom.locate_by_signature(classes, None, None)
        tag = dom.tag[node_idx] if node_idx is not None else owner
        node_id = dom.node_id[node_idx] if node_idx is not None else None
        real_classes = " ".join(sorted(dom.classes[node_idx])) if node_idx is not None else classes
        ladder = chrome_ladder(owner, cr, chrome_computed.get(owner) or {}, computed)
        vision = match_grounding((real_classes or classes).split(), grounding,
                                 role_hint=owner)
        records.append(make_record(f"chrome-{owner}", "chrome", node_idx,
                                   real_classes or classes, tag, node_id, ladder, vision))

    # 3. headings (rich multi-viewport ladder from the tier pass)
    headings = computed.get("headings", {})
    for tag in ("h1", "h2", "h3", "h4", "h5", "h6", "p"):
        if not headings.get(tag):
            continue
        node_idx = _heading_tag_owner(dom, tag)
        classes = " ".join(sorted(dom.classes[node_idx])) if node_idx is not None else ""
        node_id = dom.node_id[node_idx] if node_idx is not None else None
        # owning-section vision role
        vision = None
        if node_idx is not None:
            vision = _owning_section_vision(dom, node_idx, section_rects, grounding)
        ladder = heading_ladder(tag, computed)
        records.append(make_record(f"heading-{tag}", "heading", node_idx,
                                   classes, tag, node_id, ladder, vision))

    # 4. action groups (button variant-matrix elements)
    for i, ag in enumerate(computed.get("actionGroups", [])):
        classes = ag.get("classes", "")
        tag = ag.get("tag")
        node_idx = dom.locate_by_signature(classes, tag, None)
        node_id = dom.node_id[node_idx] if node_idx is not None else None
        vision = None
        if node_idx is not None:
            vision = _owning_section_vision(dom, node_idx, section_rects, grounding)
        ladder = {PRIMARY_TIER: {"measured": ag.get("measured"),
                                 "widthBehavior": ag.get("widthBehavior"),
                                 "labelFit": ag.get("labelFit")}}
        records.append(make_record(
            f"action-{i:02d}", "action", node_idx, classes, tag, node_id, ladder,
            vision, extra_prov={"actionSample": ag.get("visibleLabel") or ag.get("sample")}))

    coverage = _coverage(records)
    return {
        "schemaVersion": SCHEMA,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "source": str(html_path),
        "evidenceDir": str(evidence_dir),
        "tierOrder": list(TIER_ORDER),
        "primaryTier": PRIMARY_TIER,
        "coverage": coverage,
        "elements": records,
    }


def _owning_section_vision(dom: DomIndex, node_idx: int, section_rects: dict,
                           grounding: list[dict]) -> dict | None:
    """Vision role of the section (or chrome) whose subtree contains the node."""
    best = None
    best_span = None
    for sec in section_rects.get("sections", []):
        s_idx = dom.locate_by_signature(sec.get("classes", ""), sec.get("tag"),
                                        sec.get("id") or None)
        if s_idx is None:
            continue
        if s_idx <= node_idx <= dom.tout[s_idx]:
            span = dom.tout[s_idx] - s_idx
            if best_span is None or span < best_span:
                best, best_span = sec, span
    if best is not None:
        return match_grounding(best.get("classes", "").split(), grounding)
    # chrome fallback
    for owner in ("header", "footer"):
        el = dom.soup.find(owner) if owner == "header" else (
            dom.soup.find_all("footer")[-1] if dom.soup.find_all("footer") else None)
        idx = dom.index_of(el) if el else None
        if idx is not None and idx <= node_idx <= dom.tout[idx]:
            return match_grounding([], grounding, role_hint=owner)
    return None


def _coverage(records: list[dict]) -> dict:
    total = len(records)
    with_rule = [r for r in records if r["cssRules"]]
    missing = []
    for r in records:
        if r["cssRules"]:
            continue
        if not r["provenance"].get("domLocated"):
            reason = "DOM node not located (empty/truncated class signature or hidden node)"
        else:
            reason = "DOM node located but no CSS rule matched"
        missing.append({"elementId": r["elementId"], "kind": r["kind"],
                        "classes": r["classes"], "reason": reason})
    return {
        "totalElements": total,
        "withGoverningRule": len(with_rule),
        "missingRule": missing,
        "coveragePct": round(len(with_rule) / total * 100, 1) if total else 0.0,
    }


_VIEWPORT_UNIT_RE = re.compile(r"\b\d*\.?\d+(?:dvh|svh|lvh|vh|vw|dvw)\b")


def _find(records: list[dict], **pred):
    for r in records:
        if all(r.get(k) == v for k, v in pred.items()):
            return r
    return None


def acceptance_report(doc: dict) -> dict:
    """Generic PASS/FAIL check of the responsive-fidelity acceptance criteria:

    1. hero record carries a VIEWPORT-RELATIVE height rule (a ``calc()`` with a
       viewport unit such as ``calc(100dvh - var(--global-nav-header-height))``),
       not just a resolved px;
    2. footer record carries its grid/layout ``@media`` breakpoint rules (the
       responsive column reflow);
    3. nav/header record carries @media + pseudo-state + background rules.
    """
    els = doc.get("elements", [])
    checks: dict[str, dict] = {}

    hero = (_find(els, visionRole="hero")
            or next((e for e in els if e["kind"] == "section"
                     and "wf-page-header" in (e.get("classes") or "")), None)
            or next((e for e in els if e["kind"] == "section"
                     and "hero" in (e.get("classes") or "").lower()), None))
    hero_hits = []
    if hero:
        for r in hero["cssRules"]:
            if "calc(" in r["decls"] and _VIEWPORT_UNIT_RE.search(r["decls"]):
                hero_hits.append(r)
    checks["hero_viewport_height_rule"] = {
        "pass": bool(hero_hits),
        "element": hero["elementId"] if hero else None,
        "capturedRules": [{"scope": r["scope"], "selector": r["selector"][:80],
                           "decls": r["decls"][:200]} for r in hero_hits[:3]],
    }

    footer = (_find(els, elementId="chrome-footer")
              or _find(els, visionRole="footer"))
    footer_media = []
    if footer:
        for r in footer["cssRules"]:
            if r["media"] and re.search(r"grid|flex|column|display|width",
                                        r["decls"]) and "footer" in r["selector"].lower():
                footer_media.append(r)
    checks["footer_grid_media_rules"] = {
        "pass": bool(footer_media),
        "element": footer["elementId"] if footer else None,
        "mediaRuleCount": len(footer_media),
        "capturedRules": [{"media": r["media"], "selector": r["selector"][:70],
                           "decls": r["decls"][:100]} for r in footer_media[:4]],
    }

    nav = (_find(els, elementId="chrome-header")
           or _find(els, visionRole="navbar"))
    nav_media = nav_state = nav_bg = []
    if nav:
        nav_media = [r for r in nav["cssRules"] if r["media"]]
        nav_state = [r for r in nav["cssRules"] if r["pseudo"]]
        nav_bg = [r for r in nav["cssRules"] if "background" in r["decls"]]
    checks["nav_media_state_background_rules"] = {
        "pass": bool(nav and nav_media and nav_state and nav_bg),
        "element": nav["elementId"] if nav else None,
        "mediaRuleCount": len(nav_media),
        "stateRuleCount": len(nav_state),
        "backgroundRuleCount": len(nav_bg),
        "sampleBackground": ([{"scope": r["scope"], "media": r["media"],
                               "selector": r["selector"][:60], "decls": r["decls"][:80]}
                              for r in nav_bg
                              if "global-nav" in r["selector"]][:2]),
    }
    return checks


def print_acceptance(checks: dict) -> bool:
    labels = {
        "hero_viewport_height_rule": "hero viewport-relative height rule (calc/dvh)",
        "footer_grid_media_rules": "footer grid @media breakpoint rules",
        "nav_media_state_background_rules": "nav @media + state + background rules",
    }
    all_pass = True
    print("---- acceptance criteria ----")
    for key, label in labels.items():
        c = checks.get(key, {})
        status = "PASS" if c.get("pass") else "FAIL"
        all_pass = all_pass and c.get("pass", False)
        print(f"[{status}] {label} (element={c.get('element')})")
        for r in c.get("capturedRules", []) or []:
            txt = r.get("decls", "")
            print(f"    - {r.get('selector','')}  ::  {txt}")
        if key == "nav_media_state_background_rules":
            print(f"    media={c.get('mediaRuleCount')} state={c.get('stateRuleCount')} "
                  f"background={c.get('backgroundRuleCount')}")
            for r in c.get("sampleBackground", []) or []:
                print(f"    - bg {r.get('selector','')}  ::  {r.get('decls','')}")
    print(f"---- overall: {'ALL PASS' if all_pass else 'SOME FAIL'} ----")
    return all_pass


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--evidence", type=Path, required=True,
                    help="evidence dir (css-rules.json, computed-styles.json, "
                         "section-rects.json, grounding/*.yaml)")
    ap.add_argument("--capture", type=Path, help="capture dir (auto-discovers saved html)")
    ap.add_argument("--html", type=Path, help="explicit saved-page .html")
    ap.add_argument("--project-root", type=Path, default=Path.cwd(),
                    help="root to resolve the html 'source' path against")
    ap.add_argument("--out", type=Path, help="output path (default <evidence>/joined-evidence.json)")
    ap.add_argument("--acceptance", action="store_true",
                    help="print the responsive-fidelity acceptance criteria as PASS/FAIL")
    return ap


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    doc = join(args.evidence, capture=args.capture, html=args.html,
               project_root=args.project_root)
    out = args.out or (args.evidence / "joined-evidence.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=1))
    cov = doc["coverage"]
    print(f"[done] join-evidence: {len(doc['elements'])} elements -> {out.name}; "
          f"coverage {cov['withGoverningRule']}/{cov['totalElements']} "
          f"({cov['coveragePct']}%) with >=1 governing rule; "
          f"{len(cov['missingRule'])} missing")
    if cov["missingRule"]:
        for m in cov["missingRule"]:
            print(f"    missing: {m['elementId']} ({m['kind']}) — {m['reason']}")
    if args.acceptance:
        print_acceptance(acceptance_report(doc))
    return 0


if __name__ == "__main__":
    sys.exit(main())
