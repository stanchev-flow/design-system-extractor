#!/usr/bin/env python3
"""Spacing-conformance auditor — measures rendered gaps on composed lanes and diffs
them against the brand's captured spacing facts (spec/spacing-conformance.md).

Phase 1: measure, classify, rank, report. NO remediation.

Run (repo root):
  env -u PLAYWRIGHT_BROWSERS_PATH ./venv/bin/python -m brand_pipeline.spacing_audit \\
      runs/remote/brand/compose runs/remote/brand/compose/replica \\
      --brand runs/remote/brand

- positional lanes: lane dirs (index.html assumed) or explicit .html files
- --brand:    brand run dir holding brand.yaml + layout-library.yaml (+ evidence/)
- --out:      report dir (default <brand>/spacing-baseline/)
- --annotate: substring choosing the lane that gets annotated offender close-ups
- --strict:   exit 1 on any hard fail or lane error (gate wiring); default exit 0
- --no-shots: skip screenshots (fast re-classify runs)

Severity ladder (see the spec): conform | drift | wrong-step | off-ladder | unmapped.
Hard fails: wrong-step + off-ladder. unmapped = extraction gap, reported separately.
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

ROOT_REM_PX = 16.0          # composed lanes never restyle html font-size
RHYTHM_MAX_PX = 200.0       # gap/inset facts live below this; width facts above
DEFAULT_VIEWPORT = (1440, 900)   # canonical tier (meta.canonicalTier)
LANE_TIMEOUT_MS = 120_000

try:  # derived-scale consumption (pass1) — package + direct-script contexts
    from brand_pipeline import style_scale as _style_scale
except ImportError:  # pragma: no cover - direct sys.path import context
    import style_scale as _style_scale


# ───────────────────────────── fact resolution (pure) ─────────────────────────────

@dataclass(frozen=True)
class Fact:
    name: str
    px: float
    source: str  # token | pattern:<id> | chrome:<node> | scale | derived


@dataclass
class FactBook:
    steps: dict = field(default_factory=dict)          # token name -> Fact
    pattern_facts: dict = field(default_factory=dict)  # pattern id -> {key -> Fact}
    chrome: dict = field(default_factory=dict)         # key -> Fact
    scale: list = field(default_factory=list)          # mined scale rungs (Fact)
    prose: dict = field(default_factory=dict)          # token name -> [Fact] from role prose
    viewport_w: int = DEFAULT_VIEWPORT[0]

    def gap_sanctioned(self) -> list[Fact]:
        """Every rhythm-family fact (gaps/insets/heights) below the rhythm ceiling."""
        out: dict[float, Fact] = {}
        for f in self._all_facts():
            if 0 < f.px <= RHYTHM_MAX_PX:
                out.setdefault(round(f.px, 1), f)
        return sorted(out.values(), key=lambda f: f.px)

    def width_sanctioned(self) -> list[Fact]:
        out: dict[float, Fact] = {}
        for f in self._all_facts():
            if f.px > RHYTHM_MAX_PX:
                out.setdefault(round(f.px, 1), f)
        return sorted(out.values(), key=lambda f: f.px)

    def seam_sums(self) -> list[Fact]:
        """Sanctioned between-section whitespace = pairwise sums of band paddings."""
        pads: dict[float, Fact] = {}
        for name in ("section-padding-light", "section-y-lg", "section-y-xl"):
            f = self.steps.get(name)
            if f:
                pads[f.px] = f
        for pid, facts in self.pattern_facts.items():
            for key in ("bandPadding.top", "bandPadding.bottom"):
                f = facts.get(key)
                if f:
                    pads[f.px] = f
        vals = sorted(pads.values(), key=lambda f: f.px)
        sums: dict[float, Fact] = {}
        for a in vals:
            for b in vals:
                s = round(a.px + b.px, 2)
                sums.setdefault(s, Fact(f"{a.name}+{b.name}", s, "derived"))
        return sorted(sums.values(), key=lambda f: f.px)

    def _all_facts(self):
        yield from self.steps.values()
        for facts in self.pattern_facts.values():
            yield from facts.values()
        yield from self.chrome.values()
        yield from self.scale
        for facts in self.prose.values():
            yield from facts


def parse_length(value, rem_px: float = ROOT_REM_PX, viewport_w: int | None = None):
    """Parse a captured length ('3rem', '48px', 1216, 'min(81.2cqw, 97.5rem)') to px.
    Returns None for non-lengths / multi-value shorthands / ratios."""
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return None
    s = value.strip()
    m = re.fullmatch(r"min\(\s*([\d.]+)cqw\s*,\s*([\d.]+)rem\s*\)", s)
    if m:
        if viewport_w is None:
            return None
        return round(min(float(m.group(1)) / 100.0 * viewport_w,
                         float(m.group(2)) * rem_px), 2)
    m = re.fullmatch(r"(-?[\d.]+)\s*(rem|px|em)", s)
    if m:
        n = float(m.group(1))
        return round(n * rem_px, 2) if m.group(2) in ("rem", "em") else round(n, 2)
    if re.fullmatch(r"-?[\d.]+", s):
        return float(s)
    return None


def mine_scale(css_rules_path: Path, rem_px: float = ROOT_REM_PX) -> list[Fact]:
    """Mine the brand's own authored spacing scale from the evidence CSS corpus:
    custom properties whose name contains space/spacing and resolve to a length."""
    if not css_rules_path or not css_rules_path.exists():
        return []
    try:
        doc = json.loads(css_rules_path.read_text())
    except (json.JSONDecodeError, OSError):
        return []
    rungs: dict[float, str] = {}
    for rule in doc.get("rules", []):
        decls = rule.get("decls") or ""
        if not isinstance(decls, str):
            continue
        for m in re.finditer(
                r"(--[\w-]*(?:spacing|space)[\w-]*)\s*:\s*(-?[.\d]+)(px|rem)", decls):
            px = float(m.group(2)) * (rem_px if m.group(3) == "rem" else 1.0)
            if 0 < px <= RHYTHM_MAX_PX:
                rungs.setdefault(round(px, 2), m.group(1))
    return [Fact(name, px, "scale") for px, name in sorted(rungs.items())]


def load_brand_facts(brand_dir: Path, viewport_w: int = DEFAULT_VIEWPORT[0],
                     rem_px: float = ROOT_REM_PX) -> FactBook:
    import yaml  # lazy: keeps pure-function tests dependency-light

    book = FactBook(viewport_w=viewport_w)
    brand_doc = yaml.safe_load((brand_dir / "brand.yaml").read_text())

    spacing = (brand_doc.get("tokens") or {}).get("spacing") or {}
    for name, tok in spacing.items():
        if not isinstance(tok, dict):
            continue
        px = parse_length(tok.get("value"), rem_px, viewport_w)
        if px is not None:
            book.steps[name] = Fact(name, px, "token")
        # captured role prose often documents a contextual ladder ("cards ~40px,
        # hero panel up to 80px @xl") — keep those as opt-in facts per token
        role = f"{tok.get('role') or ''} {tok.get('note') or ''}"
        prose_vals: dict[float, Fact] = {}
        for m in re.finditer(r"(\d+(?:\.\d+)?)px", role):
            v = float(m.group(1))
            if 0 < v <= RHYTHM_MAX_PX and v != px:
                prose_vals.setdefault(
                    v, Fact(f"{name}~{m.group(1)}px(role)", v, "token-prose"))
        if prose_vals:
            book.prose[name] = sorted(prose_vals.values(), key=lambda f: f.px)

    # brand-level action-group facts (brand-schema §4.4f, fix2 2026-07): the measured
    # inter-action gap joins the fact book as a first-class step for actions.item-gap.
    ag = ((brand_doc.get("layoutGrammar") or {}).get("actionGroup") or {})
    if isinstance(ag, dict):
        agp = parse_length(ag.get("gap"), rem_px, viewport_w)
        if agp is not None:
            book.steps["action-group-gap"] = Fact("action-group-gap", agp, "actionGroup")

    for node in ("navbar", "footer"):
        measured = (brand_doc.get(node) or {}).get("measured") or {}
        cmw = parse_length(measured.get("contentMaxWidth"), rem_px, viewport_w)
        if cmw:
            book.chrome[f"{node}.contentMaxWidth"] = Fact(
                f"{node}.contentMaxWidth", cmw, f"chrome:{node}")
        lg = parse_length(measured.get("linkGap"), rem_px, viewport_w)
        if lg:
            book.chrome[f"{node}.linkGap"] = Fact(
                f"{node}.linkGap", lg, f"chrome:{node}")
        grid = measured.get("grid") or {}
        for k in ("columnGap", "rowGap"):
            v = parse_length(grid.get(k), rem_px, viewport_w)
            if v:
                book.chrome[f"{node}.grid.{k}"] = Fact(
                    f"{node}.grid.{k}", v, f"chrome:{node}")

    lib_path = brand_dir / "layout-library.yaml"
    if lib_path.exists():
        lib = yaml.safe_load(lib_path.read_text()) or {}
        for pat in lib.get("patterns") or []:
            pid = pat.get("id") or "?"
            shape = pat.get("contentShape") or {}
            facts: dict[str, Fact] = {}

            def _add(key, raw):
                px = parse_length(raw, rem_px, viewport_w)
                if px is not None:
                    facts[key] = Fact(f"{pid}.{key}", px, f"pattern:{pid}")

            band = shape.get("bandPadding") or {}
            _add("bandPadding.top", band.get("top"))
            _add("bandPadding.bottom", band.get("bottom"))
            geo = shape.get("deviceGeometry") or {}
            # an edge-cut card track's measured inter-card gap (`cardGap`, fix1)
            # IS the module column gap for that band — same fact, device spelling
            _add("deviceGeometry.columnGap", geo.get("columnGap") or geo.get("cardGap"))
            _add("deviceGeometry.rowGap", geo.get("rowGap"))
            _add("deviceGeometry.contentSpan", geo.get("contentSpan"))
            # measured in-card body→action register (a tight card link row that
            # does not ride the section-scale body-to-cta rung)
            _add("deviceGeometry.cardActionGap", geo.get("cardActionGap"))
            # prose-note fallback: extraction sometimes parks measured geometry
            # in the note ("… copy (gap 101px)") without structured keys
            note = geo.get("note") or ""
            if isinstance(note, str) and note:
                if "deviceGeometry.columnGap" not in facts:
                    m = re.search(r"(?:column-gap|\bgap)\s+([\d.]+)px", note)
                    if m:
                        facts["deviceGeometry.columnGap"] = Fact(
                            f"{pid}.columnGap(note)", float(m.group(1)),
                            f"pattern-note:{pid}")
                if "deviceGeometry.rowGap" not in facts:
                    m = re.search(r"row-gap\s+([\d.]+)px", note)
                    if m:
                        facts["deviceGeometry.rowGap"] = Fact(
                            f"{pid}.rowGap(note)", float(m.group(1)),
                            f"pattern-note:{pid}")
            lst = geo.get("list") or {}
            _add("list.itemGap", lst.get("itemGap"))
            _add("list.triggerMinHeight", lst.get("triggerMinHeight"))
            # per-pattern action-group override (brand-schema §4.4f)
            pag = shape.get("actionGroup") or {}
            if isinstance(pag, dict):
                _add("actionGroup.gap", pag.get("gap"))
                _add("actionGroup.marginAbove", pag.get("marginAbove"))
            _add("stackMeasure", (shape.get("stackMeasure") or {}).get("value")
                 if isinstance(shape.get("stackMeasure"), dict)
                 else shape.get("stackMeasure"))
            gaps = []
            for slot in shape.get("slots") or []:
                ms = slot.get("mediaScale") or {}
                g = parse_length(ms.get("gap"), rem_px, viewport_w)
                if g is not None:
                    gaps.append(g)
                    facts[f"strip.gap.{slot.get('name', '?')}"] = Fact(
                        f"{pid}.strip.gap.{slot.get('name', '?')}", g,
                        f"pattern:{pid}")
            if facts:
                book.pattern_facts[pid] = facts

    book.scale = mine_scale(brand_dir / "evidence" / "css-rules.json", rem_px)
    return book


# ─────────────────────── relationship registry + classification ───────────────────

@dataclass(frozen=True)
class Rel:
    family: str                 # gap | inset | width | height | center
    steps: tuple = ()           # token names and/or '@'-prefixed resolvers
    advisory_only: bool = False
    reason: str = ""


RELATIONSHIPS: dict[str, Rel] = {
    "header.eyebrow-to-heading": Rel("gap", ("eyebrow-to-heading",)),
    "header.heading-to-body": Rel("gap", ("heading-to-body", "stack-md")),
    "header.body-to-actions": Rel("gap", ("body-to-cta", "stack-lg")),
    # body→meta stays an extraction gap (remediation 2026-07): the corpus carries
    # no generic body→caption stack seam (--zora-stats-row-gap is a stats-context
    # rung; the hero meta x4 gap is the meta ROW's internal gap) — the step is
    # pre-wired so authoring `body-to-meta` after a live re-mine lights it up.
    "header.body-to-meta": Rel("gap", ("body-to-meta",)),
    "section.pad-top": Rel("inset", ("@bandPadding.top", "section-padding-light",
                                     "section-y-lg", "section-y-xl")),
    "section.pad-bottom": Rel("inset", ("@bandPadding.bottom", "section-padding-light",
                                        "section-y-lg", "section-y-xl")),
    "section.seam": Rel("gap", ("@seam-sums",)),
    "block.header-to-content": Rel("gap", ("block-to-block",)),
    "block.row-gap": Rel("gap", ("block-to-block",)),
    "block.content-to-actions": Rel("gap", ("block-to-block",)),
    "grid.column-gap": Rel("gap", ("@deviceGeometry.columnGap", "grid-gap")),
    "grid.row-gap": Rel("gap", ("@deviceGeometry.rowGap", "grid-gap")),
    "split.column-gap": Rel("gap", ("@deviceGeometry.columnGap", "column-to-column")),
    "strip.gap": Rel("gap", ("@strip.gaps", "strip-gap")),
    "stat.column-gap": Rel("gap", ("column-to-column",)),
    "card.inset": Rel("inset", ("panel-padding+prose",)),
    "card.media-to-content": Rel("gap", ("panel-padding",)),
    "card.eyebrow-to-heading": Rel("gap", ("eyebrow-to-heading",)),
    "card.heading-to-body": Rel("gap", ("heading-to-body",)),
    "card.body-to-actions": Rel("gap", ("@deviceGeometry.cardActionGap", "body-to-cta")),
    "card.body-to-author": Rel("gap", ("quote-to-attribution",)),
    "card.mark-to-quote": Rel("gap", ("mark-to-quote",)),
    "hero.panel-inset": Rel("inset", ("panel-padding+prose",)),
    "container.width": Rel("width", ("@container",)),
    "container.stack-width": Rel("width", ("@stackMeasure", "header-measure")),
    "container.centering": Rel("center", ()),
    "list.item-gap": Rel("gap", ("@list.itemGap", "list-item-gap")),
    "list.trigger-height": Rel("height", ("@list.triggerMinHeight",)),
    "list.item-inset": Rel("inset", ("list-item-inset",)),
    "footer.link-gap": Rel("gap", ("@chrome.linkGap",)),
    "footer.column-gap": Rel("gap", ("@chrome.footer.columnGap",)),
    "form.field-gap": Rel("gap", ("field-to-field",)),
    "form.label-to-input": Rel("gap", ("field-label-gap",)),
    "form.stack-gap": Rel("gap", ("form-stack",)),
    # action groups (brand-schema §4.4f, fix2 2026-07): the multi-action row's
    # inter-action gap rides the pattern override, then the brand-level fact.
    # Groups only exist where composers emit them, so a fact-less brand simply
    # reports the measurement as unmapped (advisory), same as any other gap.
    "actions.item-gap": Rel("gap", ("@actionGroup.gap", "action-group-gap")),
    # alignment: geometric edge-conformance against the group's OWN stamped
    # declaration (data-ag-align) — same center-family verdict scale as
    # container.centering (conform ≤2px / drift ≤4px / off-ladder).
    "actions.alignment": Rel("center", ()),
    # header-stack COHERENCE (fix5 2026-07 — the mixed-alignment blind spot): a
    # header stack (eyebrow/heading/body/actions sharing one column) must paint
    # ONE stance. The measurement is the largest px displacement any header child
    # would need to match the stack's dominant painted stance — 0 when coherent
    # (all-left, all-center, all-right each conform), hard when a lone centered
    # heading sits over a left kicker/body/action group (the panel-header defect,
    # which every per-child cell passed because each child conformed to its OWN
    # declaration). Same center-family verdict scale as actions.alignment.
    "header.stack-coherence": Rel("center", ()),
}

HARD = ("wrong-step", "off-ladder")


def resolve_steps(rel_id: str, pattern_id: str | None, book: FactBook) -> list[Fact]:
    """Resolve a relationship's declared steps to concrete Facts.
    Pattern-scoped resolvers ('@…') look at the section's stamped pattern first."""
    rel = RELATIONSHIPS[rel_id]
    pfacts = book.pattern_facts.get(pattern_id or "", {})
    out: list[Fact] = []
    for step in rel.steps:
        if step == "@seam-sums":
            out.extend(book.seam_sums())
        elif step == "@container":
            for key in ("container-span", "container-max"):
                f = book.steps.get(key)
                if f:
                    out.append(f)
            f = book.chrome.get("navbar.contentMaxWidth") \
                or book.chrome.get("footer.contentMaxWidth")
            if f:
                out.append(f)
            f = pfacts.get("deviceGeometry.contentSpan")
            if f:
                out.append(f)
        elif step == "@stackMeasure":
            f = pfacts.get("stackMeasure")
            if f:
                out.append(f)
            for facts in book.pattern_facts.values():
                g = facts.get("stackMeasure")
                if g:
                    out.append(g)
        elif step == "@strip.gaps":
            out.extend(v for k, v in pfacts.items() if k.startswith("strip.gap."))
        elif step == "@chrome.linkGap":
            for key in ("footer.linkGap", "navbar.linkGap"):
                f = book.chrome.get(key)
                if f:
                    out.append(f)
        elif step == "@chrome.footer.columnGap":
            f = book.chrome.get("footer.grid.columnGap")
            if f:
                out.append(f)
        elif step.startswith("@"):
            f = pfacts.get(step[1:])
            if f:
                out.append(f)
        elif step.endswith("+prose"):
            tok = step[:-len("+prose")]
            f = book.steps.get(tok)
            if f:
                out.append(f)
            out.extend(book.prose.get(tok, ()))
        else:
            f = book.steps.get(step)
            if f:
                out.append(f)
    # de-dup by px, keep first (declaration order = priority)
    seen, uniq = set(), []
    for f in out:
        key = round(f.px, 1)
        if key not in seen:
            seen.add(key)
            uniq.append(f)
    return uniq


def tolerance(v: float, family: str) -> float:
    if family == "width":
        return max(2.0, 0.01 * abs(v))
    return max(2.0, 0.10 * abs(v))


def classify(measured: float, declared: list[Fact], sanctioned: list[Fact],
             family: str) -> dict:
    """Spec §2/§3: conform / drift on the declared step; wrong-step when another
    sanctioned rung matches; off-ladder otherwise; unmapped when nothing declared."""
    result = {"measured": round(measured, 2), "declared": None, "delta": None,
              "nearest": None, "severity": None}
    if family == "center":
        result["declared"] = {"name": "centered", "px": 0.0}
        result["delta"] = round(measured, 2)
        result["severity"] = ("conform" if measured <= 2.0
                              else "drift" if measured <= 4.0 else "off-ladder")
        return result

    nearest = min(sanctioned, key=lambda f: abs(measured - f.px)) if sanctioned else None
    if nearest:
        result["nearest"] = {"name": nearest.name, "px": nearest.px,
                             "source": nearest.source}
    if not declared:
        result["severity"] = "unmapped"
        return result

    best = min(declared, key=lambda f: abs(measured - f.px))
    tol = tolerance(best.px, family)
    delta = measured - best.px
    result["declared"] = {"name": best.name, "px": best.px, "source": best.source}
    result["delta"] = round(delta, 2)
    if abs(delta) <= tol:
        result["severity"] = "conform"
    elif abs(delta) <= 2 * tol:
        result["severity"] = "drift"
    else:
        hit = None
        for f in sanctioned:
            if abs(measured - f.px) <= tolerance(f.px, family):
                if hit is None or abs(measured - f.px) < abs(measured - hit.px):
                    hit = f
        if hit is not None:
            result["severity"] = "wrong-step"
            result["nearest"] = {"name": hit.name, "px": hit.px, "source": hit.source}
        else:
            result["severity"] = "off-ladder"
    return result


def classify_measurement(meas: dict, book: FactBook) -> dict:
    """Attach classification + gate to one raw measurement dict from the browser."""
    rel_id = meas["rel"]
    rel = RELATIONSHIPS[rel_id]
    declared = resolve_steps(rel_id, meas.get("pattern"), book)
    # bandHeight re-registration (spec/archetype-library.md): a section stamped
    # data-band-rung declared its pad on ANOTHER rung of the brand's own ladder —
    # audit the pads against the STAMPED rung (still hard: a stamped band whose
    # measured pad misses its own declaration fails exactly like any drift).
    if rel_id in ("section.pad-top", "section.pad-bottom") and meas.get("bandRung"):
        stamp = str(meas["bandRung"])
        if stamp.startswith("derived:"):
            # derived-scale re-registration (pass1, style-scale.v1): the knob had
            # no measured rung in its direction and rode the quantized step — the
            # pad audits against that DELIBERATE declaration, same hard gate.
            try:
                declared = [Fact("derived-scale step", float(stamp.split(":", 1)[1]),
                                 "derived")]
            except ValueError:
                pass
        else:
            stamped = book.steps.get(stamp)
            if stamped is not None:
                declared = [stamped]
    sanctioned = (book.width_sanctioned() if rel.family == "width"
                  else book.gap_sanctioned())
    if rel_id == "section.seam":
        sanctioned = sanctioned + book.seam_sums()
    verdict = classify(meas["value"], declared, sanctioned, rel.family)
    out = dict(meas)
    out.update(verdict)
    sev = verdict["severity"]
    if sev == "conform":
        gate = "pass"
    elif sev in HARD:
        gate = "advisory" if rel.advisory_only else "hard"
    else:
        gate = "advisory"
    out["gate"] = gate
    if rel.advisory_only and sev in HARD:
        out["note"] = (out.get("note") or "") + f" [advisory-only: {rel.reason}]"
    return out


# ───────────────────── scale adherence (pass1 2026-07, gate: scale_adherence) ─────
#
# On GENERATIVE lanes only (a composition.json beside the lane's index.html — the
# composed-lane marker; replicas and the component previews carry none, exempt BY
# CONSTRUCTION), novel geometry must lie on the brand's derived scale
# (style-scale.v1): rendered SECTION-CONTENT font sizes and unmapped section-level
# space steps either match a MEASURED fact (which always wins) or sit on a derived
# step. Chrome subtrees are excluded — chrome renders harvested measured facts at
# source-exact sizes the type ladder never declared (nav 12/13/15px etc.).

TYPE_CENSUS_JS = """
() => {
  const CHROME = '.cs-nav, .c-foot, .cs-mega, .cs-utility-banner, nav, footer';
  const out = [];
  const sel = ['.c-heading--display', '.c-heading', 'h1', 'h2', 'h3', '.c-eyebrow',
               'p', '.cs-sub', '.c-button:not(.c-arrow-link)'].join(', ');
  for (const el of document.querySelectorAll(sel)) {
    if (el.closest(CHROME)) continue;
    const wrap = el.closest('[id^="sec-"]');
    if (!wrap) continue;
    const r = el.getBoundingClientRect();
    if (!r.width || !r.height) continue;
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') continue;
    const cls = (typeof el.className === 'string' ? el.className : '') || el.tagName.toLowerCase();
    out.push({ px: parseFloat(cs.fontSize), cls: cls.trim().split(/\\s+/).slice(0, 2).join('.'),
               sec: wrap.id, layout: wrap.dataset.layout || null });
  }
  return out;
}
"""

# space rels that measure CHROME devices — harvested measured facts, not novel
# composed geometry (the footer link column etc. renders on the replica too).
_SCALE_CHROME_REL = re.compile(r"^(footer|nav)\.")


def _is_generative_lane(lane_dir: Path) -> bool:
    """GENERATIVE lanes carry either a composition.v1 (the generated-composition
    contract) or a BRIEFED composition under the older replica-composition.v1
    schema (event-genlaunch predates composition.v1 — a `brief` means someone
    asked for a novel page). The true replica is the assembler's briefless
    replica-composition.v1 (source-order rebuild — measured-fact path, exempt);
    previews write no composition at all (exempt)."""
    comp = lane_dir / "composition.json"
    if not comp.exists():
        return False
    try:
        head = json.loads(comp.read_text())
    except Exception:
        return False
    schema = str(head.get("schemaVersion") or "")
    if schema == "composition.v1":
        return True
    return schema == "replica-composition.v1" and bool(head.get("brief"))


def load_type_facts(brand_dir: Path, rem_px: float = ROOT_REM_PX) -> list[float]:
    """Every MEASURED type-size fact in px: tokens.type sizeRem across tiers, the
    per-tier px table, and button label sizeRem. A rendered size matching any of
    these is measured-fact geometry — never scale-audited."""
    import yaml
    doc = yaml.safe_load((brand_dir / "brand.yaml").read_text()) or {}
    out: set[float] = set()
    for spec in ((doc.get("tokens") or {}).get("type") or {}).values():
        if not isinstance(spec, dict):
            continue
        sr = spec.get("sizeRem")
        if isinstance(sr, dict):
            for v in sr.values():
                if isinstance(v, (int, float)):
                    out.add(round(float(v) * rem_px, 1))
        elif isinstance(sr, (int, float)):
            out.add(round(float(sr) * rem_px, 1))
        for tier in (spec.get("tiers") or {}).values():
            if isinstance(tier, dict) and isinstance(tier.get("px"), (int, float)):
                out.add(round(float(tier["px"]), 1))
    for spec in (doc.get("buttons") or {}).values():
        if isinstance(spec, dict) and isinstance(spec.get("sizeRem"), (int, float)):
            out.add(round(float(spec["sizeRem"]) * rem_px, 1))
    return sorted(out)


def _near(px: float, candidates: list[float], tol: float) -> float | None:
    hit = min(candidates, key=lambda c: abs(c - px), default=None)
    return hit if hit is not None and abs(hit - px) <= tol else None


def classify_scale(type_samples: list[dict], classified_space: list[dict],
                   type_facts: list[float], scale: dict) -> dict:
    """Scale-adherence verdicts for one generative lane. Returns the lane's
    ``scale`` block: type cells (distinct rendered size x section) + space cells
    (unmapped non-chrome measurements), each measured|on-scale|off-scale."""
    type_steps = _style_scale.type_steps_px(scale)
    space_steps = _style_scale.space_steps_px(scale)
    cells: list[dict] = []

    seen: dict[tuple, dict] = {}
    for s in type_samples:
        key = (round(s["px"], 1), s["sec"])
        entry = seen.setdefault(key, {"px": round(s["px"], 1), "sec": s["sec"],
                                      "layout": s.get("layout"),
                                      "examples": set(), "count": 0})
        entry["count"] += 1
        entry["examples"].add(s["cls"])
    for (px, sec), e in sorted(seen.items()):
        tol = max(1.0, 0.02 * px)
        fact = _near(px, type_facts, tol)
        if fact is not None:
            verdict, anchor = "measured", f"type fact {fact:g}px"
        else:
            step = _near(px, type_steps, tol)
            if step is not None:
                verdict, anchor = "on-scale", f"derived step {step:g}px"
            else:
                near_f = min(type_facts, key=lambda c: abs(c - px), default=None)
                near_s = min(type_steps, key=lambda c: abs(c - px), default=None)
                verdict = "off-scale"
                anchor = (f"nearest fact {near_f:g}px / nearest step "
                          f"{near_s:g}px" if near_f is not None and near_s is not None
                          else "no facts/steps")
        cells.append({"kind": "type", "sec": sec, "layout": e["layout"],
                      "px": px, "count": e["count"],
                      "examples": sorted(e["examples"])[:3],
                      "verdict": verdict, "anchor": anchor})

    for m in classified_space:
        if m.get("severity") != "unmapped" or _SCALE_CHROME_REL.match(m["rel"]):
            continue
        px = float(m["measured"])
        tol = max(2.0, 0.02 * px)
        step = _near(px, space_steps, tol)
        cells.append({"kind": "space", "sec": m.get("sec"), "layout": m.get("layout"),
                      "rel": m["rel"], "px": px, "count": 1,
                      "verdict": "on-scale" if step is not None else "off-scale",
                      "anchor": (f"derived step {step:g}px" if step is not None else
                                 f"no derived step within {tol:g}px "
                                 f"(unit {((scale.get('space') or {}).get('baseUnitPx'))})")})

    counts = {"measured": 0, "on-scale": 0, "off-scale": 0}
    for c in cells:
        counts[c["verdict"]] += 1
    return {"cells": cells, "counts": counts,
            "hardFails": counts["off-scale"]}


# ─────────────────────────── ranking + report shaping (pure) ──────────────────────

def rank_offenders(classified: list[dict], top: int = 10) -> list[dict]:
    """Group hard fails by (relationship, expected step, rounded measurement);
    score = frequency x mean |delta-to-expected| (visual magnitude)."""
    groups: dict[tuple, list[dict]] = {}
    for m in classified:
        if m.get("gate") != "hard":
            continue
        expected = (m.get("declared") or m.get("nearest") or {})
        key = (m["rel"], expected.get("name"), round(m["measured"] / 4) * 4)
        groups.setdefault(key, []).append(m)
    ranked = []
    for (rel, expected_name, bucket), items in groups.items():
        deltas = []
        for m in items:
            base = (m.get("declared") or m.get("nearest") or {}).get("px")
            deltas.append(abs(m["measured"] - base) if base is not None
                          else abs(m["measured"]))
        mean_delta = statistics.fmean(deltas) if deltas else 0.0
        first = items[0]
        ranked.append({
            "rel": rel,
            "expected": first.get("declared") or first.get("nearest"),
            "measuredTypical": round(statistics.median(m["measured"] for m in items), 1),
            "count": len(items),
            "meanAbsDelta": round(mean_delta, 1),
            "score": round(len(items) * mean_delta, 1),
            "severity": first["severity"],
            "sections": sorted({f"{m['sec']}({m['layout']})" for m in items}),
            "example": {k: first.get(k) for k in
                        ("sec", "layout", "pattern", "a", "b", "note", "rect")},
        })
    ranked.sort(key=lambda g: -g["score"])
    return ranked[:top]


def severity_counts(classified: list[dict]) -> dict:
    counts = {"conform": 0, "drift": 0, "wrong-step": 0, "off-ladder": 0,
              "unmapped": 0}
    for m in classified:
        counts[m["severity"]] = counts.get(m["severity"], 0) + 1
    counts["hardFails"] = sum(1 for m in classified if m.get("gate") == "hard")
    counts["total"] = len(classified)
    return counts


def shape_report(lanes: list[dict], book: FactBook, meta: dict) -> dict:
    return {
        "generatedAt": meta.get("generatedAt"),
        "brandDir": meta.get("brandDir"),
        "viewport": meta.get("viewport"),
        "toleranceRule": "max(2px, 10%) for rhythm; max(2px, 1%) for widths; "
                         "drift = within 2x tolerance",
        "factbook": {
            "steps": {k: v.px for k, v in sorted(book.steps.items())},
            "scale": [f.px for f in book.scale],
            "patternFacts": {pid: {k: f.px for k, f in facts.items()}
                             for pid, facts in sorted(book.pattern_facts.items())},
            "chrome": {k: f.px for k, f in sorted(book.chrome.items())},
        },
        "lanes": lanes,
    }


def _fmt_fact(d: dict | None) -> str:
    if not d:
        return "—"
    return f"{d['name']} ({d['px']:g}px)"


def render_md(report: dict) -> str:
    L: list[str] = []
    L.append("# Spacing-conformance baseline report")
    L.append("")
    L.append(f"Generated {report['generatedAt']} · viewport "
             f"{report['viewport']} · contract: `brand_pipeline/spec/"
             f"spacing-conformance.md` · tolerance: {report['toleranceRule']}.")
    L.append("")
    L.append("Severity: `conform` pass · `drift` advisory · `wrong-step`/`off-ladder`"
             " **hard fail** · `unmapped` extraction gap (advisory, listed apart).")
    L.append("")
    L.append("## Lane summary")
    L.append("")
    L.append("| lane | audited file (mtime) | total | conform | drift | wrong-step |"
             " off-ladder | unmapped | hard fails |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for lane in report["lanes"]:
        c = lane.get("counts") or {}
        if lane.get("error"):
            L.append(f"| {lane['lane']} | {lane.get('html', '?')} | — | — | — | — | —"
                     f" | — | ERROR: {lane['error']} |")
            continue
        L.append(f"| {lane['lane']} | {lane['mtime']} | {c.get('total', 0)} |"
                 f" {c.get('conform', 0)} | {c.get('drift', 0)} |"
                 f" {c.get('wrong-step', 0)} | {c.get('off-ladder', 0)} |"
                 f" {c.get('unmapped', 0)} | **{c.get('hardFails', 0)}** |")
    L.append("")
    for lane in report["lanes"]:
        if lane.get("error"):
            continue
        L.append(f"## {lane['lane']}")
        L.append("")
        L.append(f"`{lane['html']}` (mtime {lane['mtime']})")
        L.append("")
        offenders = lane.get("offenders") or []
        if offenders:
            L.append("### Top offenders (hard fails, ranked frequency x magnitude)")
            L.append("")
            L.append("| # | relationship | measured | expected | Δ | hits | where |")
            L.append("|---|---|---|---|---|---|---|")
            for i, o in enumerate(offenders, 1):
                where = ", ".join(o["sections"][:4])
                if len(o["sections"]) > 4:
                    where += f" +{len(o['sections']) - 4} more"
                L.append(f"| {i} | `{o['rel']}` | ~{o['measuredTypical']:g}px |"
                         f" {_fmt_fact(o['expected'])} | {o['meanAbsDelta']:g}px |"
                         f" {o['count']} | {where} |")
            L.append("")
        unmapped = [m for m in lane.get("measurements", [])
                    if m["severity"] == "unmapped"]
        if unmapped:
            L.append("### Unmapped relationships (extraction gaps — capture work,"
                     " not render bugs)")
            L.append("")
            L.append("| relationship | measured | nearest sanctioned | where |")
            L.append("|---|---|---|---|")
            seen: dict[tuple, dict] = {}
            for m in unmapped:
                key = (m["rel"], round(m["measured"]))
                entry = seen.setdefault(key, {"m": m, "count": 0, "secs": set()})
                entry["count"] += 1
                entry["secs"].add(f"{m['sec']}({m['layout']})")
            for (rel, val), entry in sorted(seen.items()):
                secs = ", ".join(sorted(entry["secs"])[:3])
                L.append(f"| `{rel}` | {val}px x{entry['count']} |"
                         f" {_fmt_fact(entry['m'].get('nearest'))} | {secs} |")
            L.append("")
        sc = lane.get("scale")
        if sc:
            s = sc["counts"]
            L.append("### Scale adherence (pass1 — generative lane; "
                     "style-scale.v1 derived steps)")
            L.append("")
            L.append(f"{s['measured']} measured-fact · {s['on-scale']} on-scale · "
                     f"**{s['off-scale']} off-scale** — novel geometry must sit on "
                     "a measured fact (always wins) or a derived step; chrome + "
                     "replica lanes exempt by construction.")
            L.append("")
            L.append("| kind | sec | value | verdict | anchor | examples |")
            L.append("|---|---|---|---|---|---|")
            for cell in sc["cells"]:
                ex = ", ".join(cell.get("examples") or ([] if "rel" not in cell
                                                         else [cell["rel"]]))
                sev = (f"**{cell['verdict']}**" if cell["verdict"] == "off-scale"
                       else cell["verdict"])
                L.append(f"| {cell['kind']} | {cell['sec']} ({cell.get('layout')}) |"
                         f" {cell['px']:g}px x{cell['count']} | {sev} |"
                         f" {cell['anchor']} | {ex} |")
            L.append("")
        L.append("### All measurements")
        L.append("")
        L.append("| sec | relationship | measured | declared | Δ | severity | note |")
        L.append("|---|---|---|---|---|---|---|")
        for m in lane.get("measurements", []):
            note = (m.get("note") or "").replace("|", "/")
            sev = m["severity"]
            sev_cell = f"**{sev}**" if m.get("gate") == "hard" else sev
            delta = "—" if m.get("delta") is None else f"{m['delta']:+g}px"
            L.append(f"| {m['sec']} ({m['layout']}) | `{m['rel']}` |"
                     f" {m['measured']:g}px | {_fmt_fact(m.get('declared'))} |"
                     f" {delta} | {sev_cell} | {note} |")
        skips = lane.get("skips") or []
        if skips:
            L.append("")
            L.append("### Skipped (absent/inapplicable anatomy)")
            L.append("")
            for s in skips:
                L.append(f"- {s['sec']} ({s['layout']}): {s['what']} — {s['why']}")
        L.append("")
    shots = report.get("screenshots") or []
    if shots:
        L.append("## Annotated evidence")
        L.append("")
        for s in shots:
            L.append(f"- `{s['file']}` — {s['label']}")
        L.append("")
    return "\n".join(L) + "\n"


# ───────────────────────────── browser measurement (JS) ───────────────────────────

MEASURE_JS = r"""
() => {
  const round2 = (v) => Math.round(v * 100) / 100;
  const rect = (el) => {
    const r = el.getBoundingClientRect();
    const sx = window.scrollX, sy = window.scrollY;
    return { left: round2(r.left + sx), top: round2(r.top + sy),
             right: round2(r.right + sx), bottom: round2(r.bottom + sy),
             width: round2(r.width), height: round2(r.height) };
  };
  const css = (el) => getComputedStyle(el);
  const num = (v) => { const n = parseFloat(v); return isNaN(n) ? null : round2(n); };
  const visible = (el) => {
    if (!el || el.nodeType !== 1) return false;
    const s = css(el);
    if (s.display === 'none' || s.visibility === 'hidden') return false;
    const r = el.getBoundingClientRect();
    return r.width > 0.5 && r.height > 0.5;
  };
  const inFlow = (el) => visible(el) &&
    css(el).position !== 'absolute' && css(el).position !== 'fixed';
  const brief = (el) => {
    const cls = (el.className && typeof el.className === 'string')
      ? '.' + el.className.trim().split(/\s+/).slice(0, 2).join('.') : '';
    return el.tagName.toLowerCase() + cls;
  };
  const vgap = (a, b) => round2(rect(b).top - rect(a).bottom);
  const hgap = (a, b) => round2(rect(b).left - rect(a).right);
  const gapRectV = (a, b) => {
    const ra = rect(a), rb = rect(b);
    const x = Math.min(ra.left, rb.left);
    return { x: round2(x), y: ra.bottom,
             w: round2(Math.max(ra.right, rb.right) - x),
             h: round2(rb.top - ra.bottom) };
  };
  const gapRectH = (a, b) => {
    const ra = rect(a), rb = rect(b);
    const y = Math.min(ra.top, rb.top);
    return { x: ra.right, y: round2(y), w: round2(rb.left - ra.right),
             h: round2(Math.max(ra.bottom, rb.bottom) - y) };
  };
  const median = (arr) => {
    const s = [...arr].sort((a, b) => a - b);
    const mid = Math.floor(s.length / 2);
    return s.length % 2 ? s[mid] : round2((s[mid - 1] + s[mid]) / 2);
  };

  const measurements = [];
  const skips = [];

  // role classifier for header-cluster / block-row children
  const roleOf = (el) => {
    const c = el.classList;
    const row = el.getAttribute && el.getAttribute('data-row');
    if (row === 'eyebrow') return 'eyebrow';
    if (row === 'heading') return 'heading';
    if (row === 'body') return 'body';
    if (row === 'action') return 'actions';
    if (c.contains('c-eyebrow') || c.contains('cs-eyebrow-wrap')) return 'eyebrow';
    if (c.contains('cs-title')) return 'heading';
    if (c.contains('cs-split-intro') || c.contains('cs-modules-intro'))
      return 'header';
    if (c.contains('c-header')) {
      const hasEyebrow = el.querySelector(':scope > .c-eyebrow, :scope > .cs-eyebrow-wrap');
      return hasEyebrow ? 'header' : 'heading';
    }
    if (c.contains('c-heading')) return 'heading';
    if (c.contains('cs-sub') || c.contains('c-paragraph')) return 'body';
    if (c.contains('c-caption') || c.contains('cs-signup-meta')
        || c.contains('cs-hero-panel-meta')) return 'meta';
    if (c.contains('cs-hero-actions') || c.contains('cs-modules-actions')
        || c.contains('cs-signup-actions') || c.contains('cs-conversion-actions')
        || c.contains('c-button') || c.contains('c-arrow-link')) return 'actions';
    if (c.contains('cs-logo-strip')) return 'strip';
    if (c.contains('cs-stat-band')) return 'stats';
    if (c.contains('c-acc') || c.contains('c-faq-list') || c.contains('c-rows'))
      return 'list';
    if (el.tagName === 'FORM' || c.contains('cs-signup-panel')
        || c.contains('c-form')) return 'form';
    if (c.contains('cs-modules') || c.contains('cs-edgecut')) return 'cards';
    if (c.contains('cs-split') || c.contains('cs-interlock')
        || c.contains('cs-collage')) return 'content';
    if (el.tagName === 'FIGURE' || c.contains('c-image')
        || c.contains('c-image-mask') || c.contains('cs-flow-media')
        || c.contains('cs-split-media')) return 'media';
    if (c.contains('cs-flow-item')) {
      const inner = el.firstElementChild;
      return inner ? roleOf(inner) : 'content';
    }
    return 'content';
  };

  const pairRel = (ra, rb) => {
    const a = (ra === 'header') ? 'heading' : ra;
    // a form directly after cluster text is a CTA row, not a content block:
    // the ladder mechanic itself groups `+ .c-form` / `+ .cs-signup-panel`
    // with `+ .c-button` on the body→cta rung
    const b = (rb === 'form' && ['eyebrow', 'heading', 'body', 'meta'].includes(a))
      ? 'actions' : rb;
    const contentish = ['strip', 'stats', 'cards', 'list', 'form', 'media',
                        'content'];
    if (a === 'eyebrow' && b === 'heading') return 'header.eyebrow-to-heading';
    if (a === 'heading' && b === 'body') return 'header.heading-to-body';
    if (a === 'heading' && contentish.includes(b)) return 'block.header-to-content';
    if (a === 'heading' && b === 'actions') return 'header.body-to-actions';
    if (a === 'body' && b === 'meta') return 'header.body-to-meta';
    if (a === 'body' && b === 'actions') return 'header.body-to-actions';
    if (a === 'body' && contentish.includes(b)) return 'block.header-to-content';
    if (a === 'meta' && b === 'actions') return 'header.body-to-actions';
    if (a === 'meta' && contentish.includes(b)) return 'block.header-to-content';
    if (contentish.includes(a) && contentish.includes(b)) return 'block.row-gap';
    if (contentish.includes(a) && b === 'actions')
      return 'block.content-to-actions';
    return null;
  };

  const sections = [...document.querySelectorAll(
    'div.cs-surface[data-layout] > section.cs-section')];

  sections.forEach((sec) => {
    const wrap = sec.parentElement;
    const ctx = {
      sec: wrap.id || '?',
      layout: wrap.getAttribute('data-layout') || '?',
      pattern: wrap.getAttribute('data-pattern') || null,
      // bandHeight declaration stamps (spec/archetype-library.md): the section's
      // deliberate pad re-registration to another rung of the brand's own ladder.
      bandRung: wrap.getAttribute('data-band-rung') || null,
    };
    const push = (rel, value, a, b, gapRect, note, kind) => {
      measurements.push(Object.assign({}, ctx, {
        rel, value: round2(value),
        a: a ? brief(a) : null, b: b ? brief(b) : null,
        rect: gapRect || null, note: note || '', kind: kind || 'gap',
      }));
    };
    const skip = (what, why) => skips.push(Object.assign({}, ctx, { what, why }));

    // ── section band padding (content-edge measurement, the visual truth) ──
    const flowKids = [...sec.children].filter(inFlow);
    const secR = rect(sec);
    if (flowKids.length) {
      const first = flowKids[0], last = flowKids[flowKids.length - 1];
      const padTop = round2(rect(first).top - secR.top);
      const padBottom = round2(secR.bottom - rect(last).bottom);
      const declaredPadTop = num(css(sec).paddingTop);
      const declaredPadBottom = num(css(sec).paddingBottom);
      push('section.pad-top', padTop, sec, first,
           { x: secR.left, y: secR.top, w: secR.width, h: padTop },
           (Math.abs(padTop - declaredPadTop) > 1)
             ? `computed padding-top ${declaredPadTop}px (content stretches)` : '',
           'inset');
      push('section.pad-bottom', padBottom, last, sec,
           { x: secR.left, y: round2(secR.bottom - padBottom),
             w: secR.width, h: padBottom },
           (Math.abs(padBottom - declaredPadBottom) > 1)
             ? `computed padding-bottom ${declaredPadBottom}px` : '',
           'inset');
      wrap.__contentTop = rect(first).top;
      wrap.__contentBottom = rect(last).bottom;
    } else skip('section padding', 'no in-flow content children');

    // ── header clusters / block rows: classify direct children of stack scaffolds ──
    const clusterSelectors = ['.cs-flow', '.cs-hero-panel-content', '.cs-conversion',
                              '.cs-faq', '.cs-split-intro', '.cs-modules-intro',
                              '.cs-split-body', '.cs-acc-col--lead',
                              '.cs-interlock-foot'];
    const seen = new Set();
    clusterSelectors.forEach((sel) => {
      sec.querySelectorAll(sel).forEach((box) => {
        if (seen.has(box)) return;
        seen.add(box);
        const kids = [...box.children].filter(inFlow);
        for (let i = 0; i + 1 < kids.length; i++) {
          const a = kids[i], b = kids[i + 1];
          const rel = pairRel(roleOf(a), roleOf(b));
          if (!rel) continue;
          const g = vgap(a, b);
          if (g < -0.5) continue; // overlapping devices are not rhythm seams
          push(rel, g, a, b, gapRectV(a, b), sel);
        }
      });
    });

    // ── .c-header internal eyebrow→heading (flex-gap header block) ──
    sec.querySelectorAll('.c-header').forEach((h) => {
      const eb = h.querySelector(':scope > .c-eyebrow, :scope > .cs-eyebrow-wrap');
      const hd = h.querySelector(':scope > .c-heading');
      if (eb && hd && visible(eb) && visible(hd))
        push('header.eyebrow-to-heading', vgap(eb, hd), eb, hd, gapRectV(eb, hd),
             '.c-header');
    });

    // ── uniform grids: cards / stats / signup fields ──
    const gridWork = [
      { sel: '.cs-modules', col: 'grid.column-gap', row: 'grid.row-gap',
        colsOnly: true },
      { sel: '.cs-stat-band', col: 'stat.column-gap', row: 'block.row-gap' },
      { sel: '.cs-signup-grid', col: 'form.field-gap', row: 'form.field-gap' },
    ];
    gridWork.forEach((work) => {
      sec.querySelectorAll(work.sel).forEach((grid) => {
        if (work.colsOnly && !grid.classList.contains('cs-modules--cols')) {
          skip(work.sel, 'staggered editorial grid (no uniform row/column gap)');
          return;
        }
        const items = [...grid.children].filter(inFlow);
        if (items.length < 2) return;
        const rows = [];
        items.map((el) => ({ el, r: rect(el) }))
          .sort((p, q) => p.r.top - q.r.top || p.r.left - q.r.left)
          .forEach((it) => {
            const row = rows.find((rw) => Math.abs(rw[0].r.top - it.r.top) <= 4);
            if (row) row.push(it); else rows.push([it]);
          });
        rows.forEach((row) => {
          row.sort((p, q) => p.r.left - q.r.left);
          for (let i = 0; i + 1 < row.length; i++) {
            const g = hgap(row[i].el, row[i + 1].el);
            if (g >= -0.5)
              push(work.col, g, row[i].el, row[i + 1].el,
                   gapRectH(row[i].el, row[i + 1].el),
                   work.sel + ' column', 'gap');
          }
        });
        for (let i = 0; i + 1 < rows.length; i++) {
          const prevBottom = Math.max(...rows[i].map((it) => it.r.bottom));
          const nextTop = Math.min(...rows[i + 1].map((it) => it.r.top));
          const left = Math.min(...rows[i + 1].map((it) => it.r.left));
          const right = Math.max(...rows[i + 1].map((it) => it.r.right));
          push(work.row, round2(nextTop - prevBottom), rows[i][0].el,
               rows[i + 1][0].el,
               { x: round2(left), y: round2(prevBottom),
                 w: round2(right - left), h: round2(nextTop - prevBottom) },
               work.sel + ' row', 'gap');
        }
      });
    });

    // ── card plates: inset + internal rhythm ──
    const plates = [...sec.querySelectorAll('.cs-module--plate')].filter(visible);
    const pinnedSeams = [];
    plates.forEach((card) => {
      const s = css(card);
      push('card.inset', num(s.paddingLeft), card, null, null,
           'computed padding-left', 'inset');
      const kids = [...card.children].filter(inFlow);
      if (!kids.length) return;
      const firstIsBleedMedia = kids[0].classList.contains('cs-module-media')
        && !kids[0].classList.contains('cs-module-media--mark');
      if (!firstIsBleedMedia)
        push('card.inset', num(s.paddingTop), card, null, null,
             'computed padding-top', 'inset');
      for (let i = 0; i + 1 < kids.length; i++) {
        const a = kids[i], b = kids[i + 1];
        const ca = a.classList, cb = b.classList;
        const g = vgap(a, b);
        const gr = gapRectV(a, b);
        const isMediaA = ca.contains('cs-module-media');
        const markA = ca.contains('cs-module-media--mark');
        if (isMediaA && !markA) {
          push('card.media-to-content', g, a, b, gr, 'full-bleed well seam');
        } else if (isMediaA && markA && cb.contains('c-paragraph')) {
          push('card.mark-to-quote', g, a, b, gr, 'quote-card mark seam');
        } else if (ca.contains('c-eyebrow') && cb.contains('c-heading')) {
          push('card.eyebrow-to-heading', g, a, b, gr, '');
        } else if (ca.contains('c-heading') && cb.contains('c-paragraph')) {
          push('card.heading-to-body', g, a, b, gr, '');
        } else if (ca.contains('c-paragraph')
                   && (cb.contains('c-arrow-link') || cb.contains('c-button')
                       || cb.contains('c-person'))) {
          // pinned bottom seam on equalized grids: only the min across the row
          // is the true rung (slack is sanctioned by gridEqualize)
          const rel = cb.contains('c-person')
            ? 'card.body-to-author' : 'card.body-to-actions';
          pinnedSeams.push({ rel, g, a, b, gr });
        }
      }
    });
    ['card.body-to-actions', 'card.body-to-author'].forEach((rel) => {
      const seams = pinnedSeams.filter((s) => s.rel === rel);
      if (!seams.length) return;
      const minSeam = seams.reduce((m, s) => (s.g < m.g ? s : m));
      push(rel, minSeam.g, minSeam.a, minSeam.b, minSeam.gr,
           `min across ${seams.length} equalized cards (pinned slack `
           + 'sanctioned by gridEqualize)');
    });

    // ── split scaffolds: column gap (+ hero panel inset) ──
    const heroPanel = sec.querySelector('.cs-hero-panel');
    if (heroPanel) {
      const content = heroPanel.querySelector(':scope > .cs-hero-panel-content');
      const media = heroPanel.querySelector(':scope > .cs-hero-panel-media');
      if (content && media && visible(media))
        push('split.column-gap', hgap(content, media), content, media,
             gapRectH(content, media), 'hero panel columns');
      if (content) {
        // computed padding = the authored inset (rect deltas would fold in the
        // panel's own flex centering, which is stance, not inset)
        const pr = rect(heroPanel);
        const padL = num(css(heroPanel).paddingLeft);
        const padT = num(css(heroPanel).paddingTop);
        push('hero.panel-inset', padL, heroPanel, content,
             { x: pr.left, y: pr.top + pr.height / 2 - 40, w: padL, h: 80 },
             'panel padding-left (computed)', 'inset');
        push('hero.panel-inset', padT, heroPanel, content,
             { x: pr.left, y: pr.top, w: pr.width, h: padT },
             'panel padding-top (computed)', 'inset');
      }
    }
    sec.querySelectorAll('.cs-split, .cs-acc-split').forEach((split) => {
      const cols = [...split.children].filter(inFlow);
      if (cols.length === 2) {
        const [a, b] = cols.sort((p, q) => rect(p).left - rect(q).left);
        const g = hgap(a, b);
        if (g >= -0.5)
          push('split.column-gap', g, a, b, gapRectH(a, b),
               split.className.includes('cs-acc-split')
                 ? 'accordion split columns' : 'split columns');
      } else if (cols.length > 2) {
        skip('.cs-split', `expected 2 columns, found ${cols.length}`);
      }
    });

    // ── logo/badge/rating strips ──
    sec.querySelectorAll('.cs-logo-strip').forEach((strip) => {
      const items = [...strip.children].filter(inFlow);
      const gaps = [];
      for (let i = 0; i + 1 < items.length; i++) {
        const ra = rect(items[i]), rb = rect(items[i + 1]);
        if (Math.abs(ra.top - rb.top) > ra.height) continue; // wrapped row
        gaps.push(hgap(items[i], items[i + 1]));
      }
      if (gaps.length)
        push('strip.gap', median(gaps), items[0], items[1],
             gapRectH(items[0], items[1]),
             `median of ${gaps.length} inter-mark gaps`);
    });

    // ── action groups: inter-action gap + stamped-alignment conformance ──
    // (brand-schema §4.4f, fix2 2026-07): the multi-action row's gap classifies
    // against the brand's actionGroup facts; alignment conformance measures the
    // group's geometry against its OWN stamped declaration (data-ag-align).
    // Contexts that own their anchor (centered foot/panel/data-align) are the
    // sanctioned exception the schema names — skipped, not misread as drift.
    sec.querySelectorAll(
      '.cs-hero-actions, .cs-modules-actions, .cs-conversion-actions'
    ).forEach((grp) => {
      const items = [...grp.children].filter(inFlow).filter(visible);
      if (items.length >= 2) {
        const gaps = [];
        for (let i = 0; i + 1 < items.length; i++) {
          const ra = rect(items[i]), rb = rect(items[i + 1]);
          if (Math.abs(ra.top - rb.top) > ra.height) continue; // wrapped line
          const g = hgap(items[i], items[i + 1]);
          if (g >= -0.5) gaps.push(g);
        }
        if (gaps.length)
          push('actions.item-gap', median(gaps), items[0], items[1],
               gapRectH(items[0], items[1]),
               `median of ${gaps.length} inter-action gap(s)`);
      }
      const align = grp.getAttribute('data-ag-align');
      const anchored = grp.closest(
        '.cs-foot, [data-align="centered"], .cs-hero-panel--center')
        || css(grp.parentElement).alignItems === 'center';  // centering parent owns the anchor
      if (align && items.length && !anchored) {
        // PAINTED-EDGE conformance (fix3 — the audit blind spot): the old cell
        // measured item edges against the GROUP's own content box, so a group box
        // that was itself displaced (max-width + auto margins hug-centering it
        // inside its column) read 0px while the user saw the whole row floated
        // off the column edge. The reference is now the CONTENT COLUMN the way a
        // reader sees it: the widest in-flow SIBLING sharing the group's parent
        // (the intro/heading stack above the row), else the parent's own content
        // box — and the measurement is the ITEMS' painted edges against it, which
        // catches both box displacement and justify drift in one number.
        const sibs = [...grp.parentElement.children].filter(
          (el) => el !== grp && inFlow(el) && visible(el));
        let colL, colR, ref;
        if (sibs.length) {
          const w = sibs.reduce((a, b) => rect(b).width > rect(a).width ? b : a);
          const wr = rect(w);
          colL = wr.left; colR = wr.right;
          ref = 'column = widest sibling';
        } else {
          const pr = rect(grp.parentElement), pcs = css(grp.parentElement);
          colL = pr.left + num(pcs.paddingLeft);
          colR = pr.right - num(pcs.paddingRight);
          ref = 'column = parent content box';
        }
        const first = rect(items[0]), last = rect(items[items.length - 1]);
        const lg = first.left - colL, rg = colR - last.right;
        const dev = align === 'center' ? Math.abs(lg - rg)
          : align === 'end' ? Math.abs(rg) : Math.abs(lg);
        push('actions.alignment', round2(dev), grp, null,
             { x: Math.min(colL, first.left), y: first.top,
               w: Math.max(4, Math.abs(first.left - colL)),
               h: Math.min(first.height ?? 24, 40) },
             `stamped ${align}; painted edges vs column ${Math.round(lg)}px | `
             + `${Math.round(rg)}px (${ref})`, 'center');
      }
    });

    // ── header-stack coherence (fix5 — the mixed-alignment blind spot) ──
    // Every per-child alignment cell conforms to its OWN declaration, so a
    // heading centered by a leaked section rule over a left kicker/body/actions
    // stack read green. This cell classifies each header child's PAINTED stance
    // (text line boxes + control boxes, never the stretched element box) against
    // the stack's content box and fails when stances mix. Stance-agnostic: an
    // all-centered stack conforms exactly like an all-left one.
    if (wrap.getAttribute('data-align') !== 'mixed') {
      const paintSpan = (el) => {
        let x0 = 1e9, x1 = -1e9, any = false;
        const rng = document.createRange();
        const tw = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
        for (let n = tw.nextNode(); n; n = tw.nextNode()) {
          if (!n.textContent.trim()) continue;
          if (n.parentElement && !visible(n.parentElement)) continue;
          if (n.parentElement && n.parentElement.closest('.c-button, .c-arrow-link'))
            continue;  // controls measure as boxes below (their padding paints)
          rng.selectNodeContents(n);
          for (const r of rng.getClientRects()) {
            if (r.width < 0.5 || r.height < 0.5) continue;
            x0 = Math.min(x0, r.left); x1 = Math.max(x1, r.right); any = true;
          }
        }
        el.querySelectorAll('img, svg, picture, video, input, .c-button, .c-arrow-link')
          .forEach((c) => {
            if (!visible(c)) return;
            const r = c.getBoundingClientRect();
            x0 = Math.min(x0, r.left); x1 = Math.max(x1, r.right); any = true;
          });
        if (el.matches('.c-button, .c-arrow-link')) {
          const r = el.getBoundingClientRect();
          x0 = Math.min(x0, r.left); x1 = Math.max(x1, r.right); any = true;
        }
        if (!any) return null;
        return { left: round2(x0 + window.scrollX), right: round2(x1 + window.scrollX) };
      };
      const headerRole = (el) => {
        const c = el.classList;
        if (c.contains('cs-ov-panel-item') || c.contains('cs-flow-item')) {
          const inner = el.firstElementChild;
          return inner ? headerRole(inner) : null;
        }
        if (c.contains('c-eyebrow') || c.contains('cs-eyebrow-wrap')) return 'eyebrow';
        if (c.contains('c-heading')) return 'heading';
        if (c.contains('cs-sub') || c.contains('c-paragraph')) return 'body';
        if (c.contains('cs-hero-actions') || c.contains('cs-modules-actions')
            || c.contains('cs-conversion-actions') || c.contains('cs-signup-actions'))
          return 'actions';
        return null;
      };
      const stanceOf = (pb, colL, colR) => {
        const L = round2(pb.left - colL), R = round2(colR - pb.right);
        const tol = 6;
        if (L <= tol && R <= tol) return { kind: 'full', L, R };
        if (Math.abs(L - R) <= Math.max(6, 0.06 * Math.max(L, R)))
          return { kind: 'center', L, R };
        if (L <= tol) return { kind: 'left', L, R };
        if (R <= tol) return { kind: 'right', L, R };
        return { kind: 'other', L, R };
      };
      const moveCost = (s, kind) => kind === 'left' ? Math.abs(s.L)
        : kind === 'right' ? Math.abs(s.R) : Math.abs(s.L - s.R) / 2;
      const seen = new Set();
      sec.querySelectorAll('.c-heading').forEach((h) => {
        if (!inFlow(h)) return;
        let stack = h.parentElement;
        while (stack && stack !== sec
               && [...stack.children].filter(inFlow).length === 1)
          stack = stack.parentElement;
        if (!stack || stack === sec || seen.has(stack)) return;
        if (stack.closest('.cs-ov-stepped')) return;   // deliberate stepped indents
        seen.add(stack);
        const sr = rect(stack), scs = css(stack);
        const colL = sr.left + num(scs.paddingLeft);
        const colR = sr.right - num(scs.paddingRight);
        if (colR - colL < 80) return;
        const kids = [...stack.children].filter(inFlow).map((el) => {
          const role = headerRole(el);
          if (!role) return null;
          const pb = paintSpan(el);
          if (!pb) return null;
          return { el, role, box: rect(el), stance: stanceOf(pb, colL, colR) };
        }).filter(Boolean);
        if (kids.length < 2 || !kids.some((k) => k.role === 'heading')) return;
        let worst = 0, wa = kids[0], wb = kids[0], note = 'coherent';
        for (let i = 0; i < kids.length; i++) {
          for (let j = i + 1; j < kids.length; j++) {
            const a = kids[i].stance, b = kids[j].stance;
            // side-by-side children (two-column intros: heading | body rows)
            // are a ROW device, not a stacked header — coherence is a claim
            // about one COLUMN painting one stance.
            const ra = kids[i].box, rb = kids[j].box;
            const overlap = Math.min(ra.bottom, rb.bottom) - Math.max(ra.top, rb.top);
            if (overlap > 0.5 * Math.min(ra.height, rb.height)) continue;
            if (a.kind === 'full' || b.kind === 'full') continue;
            if (a.kind === b.kind) continue;
            const cost = round2(Math.min(moveCost(a, b.kind), moveCost(b, a.kind)));
            if (cost > worst) {
              worst = cost; wa = kids[i]; wb = kids[j];
              note = `${wa.role} paints ${wa.stance.kind} vs ${wb.role} `
                + `${wb.stance.kind} (insets ${Math.round(wa.stance.L)}|`
                + `${Math.round(wa.stance.R)} vs ${Math.round(wb.stance.L)}|`
                + `${Math.round(wb.stance.R)})`;
            }
          }
        }
        const hr = rect(wa.el);
        push('header.stack-coherence', worst, wa.el, wb.el,
             { x: colL, y: hr.top, w: Math.max(4, worst), h: Math.min(hr.height, 40) },
             note, 'center');
      });
    }

    // ── disclosure lists: accordion + FAQ ──
    sec.querySelectorAll('.c-acc').forEach((acc) => {
      const items = [...acc.querySelectorAll(':scope > .c-acc-item')].filter(visible);
      for (let i = 0; i + 1 < items.length; i++)
        push('list.item-gap', vgap(items[i], items[i + 1]), items[i], items[i + 1],
             gapRectV(items[i], items[i + 1]), 'accordion items');
      items.forEach((item) => {
        const trig = item.querySelector(':scope > .c-acc-trigger');
        if (trig)
          push('list.trigger-height', rect(trig).height, trig, null, null,
               item.hasAttribute('open') ? 'open item' : '', 'height');
      });
    });
    sec.querySelectorAll('.c-faq-list').forEach((faq) => {
      const items = [...faq.querySelectorAll(':scope > .c-faq-item')].filter(visible);
      items.forEach((item) => {
        const q = item.querySelector(':scope > .c-faq-q');
        if (q)
          push('list.item-inset', round2(rect(q).top - rect(item).top), item, q,
               null, 'faq item top inset', 'inset');
      });
      // item-box stride (content that overflows a closed disclosure box is the
      // interaction contract's problem, not a spacing seam)
      for (let i = 0; i + 1 < items.length; i++)
        push('list.item-gap', vgap(items[i], items[i + 1]), items[i],
             items[i + 1], gapRectV(items[i], items[i + 1]), 'faq item stride');
    });

    // ── forms: label→input + form-internal stack ──
    sec.querySelectorAll('.cs-field').forEach((fieldBox) => {
      const label = fieldBox.querySelector(':scope > .cs-field-label');
      const input = fieldBox.querySelector(':scope > .cs-input');
      if (label && input)
        push('form.label-to-input', vgap(label, input), label, input,
             gapRectV(label, input), '');
    });
    sec.querySelectorAll('.cs-signup-panel, .c-form').forEach((form) => {
      const kids = [...form.children].filter(inFlow);
      for (let i = 0; i + 1 < kids.length; i++) {
        const g = vgap(kids[i], kids[i + 1]);
        if (g >= -0.5)
          push('form.stack-gap', g, kids[i], kids[i + 1],
               gapRectV(kids[i], kids[i + 1]), 'form internal seam');
      }
    });

    // ── container law ──
    // Discovery is mechanical, not a selector list: the container is a
    // max-width-constrained structural descendant (scaffolds are authored as
    // `max-width: …; margin-inline: auto` across all composers). The widest
    // non-stack candidate is THE section container; deliberately narrow
    // centered stacks are the stack-measure law instead.
    const edgecut = sec.querySelector('.cs-modules--edgecut, .cs-edgecut');
    // deliberately narrow MEASURE-capped stacks (never the section container):
    // .cs-title/.cs-foot joined fix3 — a hero whose pattern authored stackMeasure
    // caps its text boxes at the measured column (--cs-stack-measure), which must
    // audit as container.stack-width against that fact, not as container.width.
    const NARROW_STACKS = '.cs-modules-intro, .cs-conversion, .cs-faq, .cs-title, .cs-foot';
    const TEXT_TAGS = new Set(['P', 'H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'A',
                               'SPAN', 'BUTTON', 'UL', 'OL', 'LI', 'SUMMARY']);
    const candidates = [];
    // a full-bleed MEDIA canvas (an overlay/banded backdrop painting edge-to-edge)
    // is sanctioned geometry, never "the section container" — the container law
    // audits the CONTENT column. Absolutely-positioned bleeds were always excluded
    // (inFlow); this excludes the in-flow canvas the overlay composer draws.
    const isBleedMedia = (el, r) =>
      (el.tagName === 'IMG' || el.tagName === 'FIGURE'
        || el.classList.contains('c-image') || el.classList.contains('cs-ov-canvas'))
      && r.width >= secR.width - 2;
    // the hero media COLLAGE is a media device, not the section container: its
    // width (and its layers' widths) is col-span/scaffold-registered geometry
    // (whole columns + shared gutters of the registration grid — e.g. span 8 ≈
    // 896px at 1440), which the width LADDER can't express by construction. The
    // whole subtree is skipped so the law audits the acting content column
    // (title/foot stacks → the stack-measure fact).
    const isMediaCollage = (el) => el.classList.contains('cs-collage');
    const walkMW = (el, depth) => {
      if (depth > 3) return;
      for (const kid of el.children) {
        if (!visible(kid) || !inFlow(kid) || TEXT_TAGS.has(kid.tagName)
            || isMediaCollage(kid)) continue;
        const kr = rect(kid);
        if (css(kid).maxWidth !== 'none' && kr.width >= 320
            && !isBleedMedia(kid, kr))
          candidates.push({ el: kid, r: kr, narrow: kid.matches(NARROW_STACKS) });
        walkMW(kid, depth + 1);
      }
    };
    walkMW(sec, 1);
    const widest = (arr) => arr.reduce((m, c) => (c.r.width > m.r.width ? c : m));
    const wide = candidates.filter((c) => !c.narrow);
    const stacks = candidates.filter((c) => c.narrow);
    const pushContainer = (relId, c) => {
      push(relId, c.r.width, c.el, null,
           { x: c.r.left, y: c.r.top, w: c.r.width, h: Math.min(c.r.height, 60) },
           '', 'width');
      const lg = round2(c.r.left - secR.left), rg = round2(secR.right - c.r.right);
      push('container.centering', round2(Math.abs(lg - rg)), c.el, null, null,
           `gutters ${lg}px | ${rg}px`, 'center');
    };
    if (wide.length) pushContainer('container.width', widest(wide));
    else if (stacks.length) {
      // SIDE-ANCHORED stacks (fid10 container law): the anchor releases the stack
      // BOX to the shared content spine and the MEASURE cap moves to the text
      // children — audit the acting column (widest capped text child), not the
      // spine box; the centering law still reads the box against the section.
      const c = widest(stacks);
      const cs0 = css(c.el);
      const side = ['flex-start', 'start', 'left', 'flex-end', 'end', 'right']
        .includes(cs0.alignItems);
      let acting = c;
      if (side) {
        const caps = [...c.el.querySelectorAll(':scope > *, :scope > * > *')]
          .filter((k) => visible(k) && css(k).maxWidth !== 'none')
          .map((k) => ({ el: k, r: rect(k), narrow: true }));
        if (caps.length) acting = widest(caps);
      }
      push('container.stack-width', acting.r.width, acting.el, null,
           { x: acting.r.left, y: acting.r.top, w: acting.r.width,
             h: Math.min(acting.r.height, 60) },
           side ? 'side-anchored: acting column = widest capped text child' : '',
           'width');
      const lg = round2(c.r.left - secR.left), rg = round2(secR.right - c.r.right);
      push('container.centering', round2(Math.abs(lg - rg)), c.el, null, null,
           `gutters ${lg}px | ${rg}px`, 'center');
    }
    else if (edgecut) skip('container', 'edge-cut scaffold bleeds by construction');
    else skip('container', 'no max-width-constrained scaffold found');

    // ── footer directory rhythm ──
    sec.querySelectorAll('.c-foot-col').forEach((col) => {
      const links = [...col.querySelectorAll(':scope > .c-foot-col-link')]
        .filter(visible);
      const gaps = [];
      for (let i = 0; i + 1 < links.length; i++)
        gaps.push(vgap(links[i], links[i + 1]));
      if (gaps.length)
        push('footer.link-gap', median(gaps), links[0], links[1],
             gapRectV(links[0], links[1]), `median of ${gaps.length} link gaps`);
    });
    sec.querySelectorAll('.c-foot-cols').forEach((cols) => {
      const cells = [...cols.children].filter(inFlow);
      const sorted = cells.map((el) => ({ el, r: rect(el) }))
        .sort((p, q) => p.r.left - q.r.left);
      for (let i = 0; i + 1 < sorted.length; i++) {
        if (Math.abs(sorted[i].r.top - sorted[i + 1].r.top) > 40) continue;
        push('footer.column-gap', hgap(sorted[i].el, sorted[i + 1].el),
             sorted[i].el, sorted[i + 1].el,
             gapRectH(sorted[i].el, sorted[i + 1].el), 'directory columns');
      }
    });

    if (sec.querySelector('.cs-interlock'))
      skip('.cs-interlock rows', 'float-interlock scaffold (no linear stack seams)');
  });

  // ── between-section seams (visible whitespace between content edges) ──
  const wraps = sections.map((s) => s.parentElement);
  for (let i = 0; i + 1 < wraps.length; i++) {
    const a = wraps[i], b = wraps[i + 1];
    if (a.__contentBottom == null || b.__contentTop == null) continue;
    const seam = round2(b.__contentTop - a.__contentBottom);
    const ra = rect(a), rb = rect(b);
    measurements.push({
      sec: `${a.id}→${b.id}`,
      layout: `${a.getAttribute('data-layout')}→${b.getAttribute('data-layout')}`,
      pattern: null, rel: 'section.seam', value: seam,
      a: a.id, b: b.id,
      rect: { x: ra.left, y: a.__contentBottom, w: ra.width, h: seam },
      note: (Math.abs(rb.top - ra.bottom) > 1)
        ? `section boxes not flush (${round2(rb.top - ra.bottom)}px box gap)` : '',
      kind: 'gap',
    });
  }

  if (!sections.length)
    skips.push({ sec: '—', layout: '—', what: 'whole lane',
                 why: 'no composed sections (div.cs-surface[data-layout] > '
                      + 'section.cs-section) — not a composed lane' });

  return { measurements, skips,
           pageHeight: Math.round(document.documentElement.scrollHeight) };
}
"""

SETTLE_CSS = """
.cs-motion-ready .cs-reveal, .cs-reveal {
  opacity: 1 !important; transform: none !important;
  transition: none !important; animation: none !important;
}
*, *::before, *::after { transition: none !important; animation: none !important; }
html { scroll-behavior: auto !important; }
"""


def _lane_name(html: Path, brand_dir: Path) -> str:
    try:
        rel = html.resolve().relative_to(brand_dir.resolve())
        parts = [p for p in rel.parts if p != "index.html"]
        return "/".join(parts) or html.stem
    except ValueError:
        return html.parent.name


def measure_lane(pw, html: Path, viewport: tuple[int, int]) -> dict:
    browser = pw.chromium.launch()
    try:
        page = browser.new_page(
            viewport={"width": viewport[0], "height": viewport[1]},
            device_scale_factor=1, reduced_motion="reduce")
        page.set_default_timeout(LANE_TIMEOUT_MS)
        page.set_default_navigation_timeout(LANE_TIMEOUT_MS)
        page.goto(html.resolve().as_uri(), wait_until="load",
                  timeout=LANE_TIMEOUT_MS)
        page.add_style_tag(content=SETTLE_CSS)
        page.evaluate("document.fonts && document.fonts.ready")
        page.wait_for_timeout(700)
        raw = page.evaluate(MEASURE_JS)
        # scale-adherence census (pass1): section-content font sizes; consumed only
        # for generative lanes with a derived scale, but measured unconditionally
        # (cheap, and keeps measure_lane single-shot).
        raw["typeSamples"] = page.evaluate(TYPE_CENSUS_JS)
        return raw
    finally:
        browser.close()


def annotate_offenders(pw, html: Path, offenders: list[dict], out_dir: Path,
                       viewport: tuple[int, int], lane: str,
                       top: int = 5) -> list[dict]:
    """Close-up screenshots for the top offenders with the measured gap drawn on."""
    shots: list[dict] = []
    targets = [o for o in offenders if (o.get("example") or {}).get("rect")][:top]
    if not targets:
        return shots
    browser = pw.chromium.launch()
    try:
        page = browser.new_page(
            viewport={"width": viewport[0], "height": viewport[1]},
            device_scale_factor=1, reduced_motion="reduce")
        page.set_default_timeout(LANE_TIMEOUT_MS)
        page.goto(html.resolve().as_uri(), wait_until="load",
                  timeout=LANE_TIMEOUT_MS)
        page.add_style_tag(content=SETTLE_CSS)
        page.evaluate("document.fonts && document.fonts.ready")
        page.wait_for_timeout(500)
        for i, off in enumerate(targets, 1):
            ex = off["example"]
            r = ex["rect"]
            expected = off.get("expected") or {}
            label = (f"{off['rel']}: measured {off['measuredTypical']:g}px — "
                     f"expected {expected.get('name', '?')} "
                     f"{expected.get('px', 0):g}px "
                     f"({off['severity']}, x{off['count']} on this lane)")
            page.evaluate(
                """(args) => {
                  const { r, label, idx } = args;
                  const mark = document.createElement('div');
                  mark.className = 'spacing-audit-overlay';
                  Object.assign(mark.style, {
                    position: 'absolute', left: r.x + 'px', top: r.y + 'px',
                    width: Math.max(r.w, 24) + 'px',
                    height: Math.max(r.h, 2) + 'px',
                    background: 'rgba(211, 47, 60, 0.18)',
                    borderTop: '2px solid #d32f3c',
                    borderBottom: '2px solid #d32f3c',
                    zIndex: 99998, pointerEvents: 'none', boxSizing: 'border-box',
                  });
                  const tag = document.createElement('div');
                  tag.className = 'spacing-audit-overlay';
                  tag.textContent = idx + '. ' + label;
                  Object.assign(tag.style, {
                    position: 'absolute', left: (r.x + 8) + 'px',
                    top: Math.max(2, r.y - 30) + 'px',
                    background: '#d32f3c', color: '#fff',
                    font: '600 13px/1.4 system-ui, sans-serif',
                    padding: '3px 9px', borderRadius: '3px', zIndex: 99999,
                    pointerEvents: 'none', maxWidth: '860px',
                    whiteSpace: 'nowrap', overflow: 'hidden',
                    textOverflow: 'ellipsis',
                  });
                  document.body.appendChild(mark);
                  document.body.appendChild(tag);
                }""",
                {"r": r, "label": label, "idx": i})
            scroll_to = max(0.0, r["y"] - 260)
            page.evaluate(f"window.scrollTo(0, {scroll_to})")
            page.wait_for_timeout(160)
            sy = page.evaluate("window.scrollY")
            clip_y = max(0.0, r["y"] - sy - 200)
            clip_h = min(viewport[1] - clip_y, max(r["h"], 2) + 400)
            clip = {"x": max(0.0, min(r["x"] - 120, viewport[0] - 400.0)),
                    "y": clip_y,
                    "width": min(viewport[0], max(r["w"] + 240, 720)),
                    "height": max(clip_h, 160)}
            clip["width"] = min(clip["width"], viewport[0] - clip["x"])
            slug = re.sub(r"[^a-z0-9]+", "-", off["rel"].lower()).strip("-")
            fname = f"offender-{i:02d}-{slug}.png"
            page.screenshot(path=str(out_dir / fname), clip=clip)
            page.evaluate(
                "document.querySelectorAll('.spacing-audit-overlay')"
                ".forEach(e => e.remove())")
            shots.append({"file": fname, "lane": lane, "label": label})
    finally:
        browser.close()
    return shots


# ──────────────────────────────────── driver ──────────────────────────────────────

def resolve_lane_paths(args_lanes: list[str]) -> list[Path]:
    out = []
    for raw in args_lanes:
        p = Path(raw)
        if p.is_dir():
            p = p / "index.html"
        out.append(p)
    return out


def run_audit(lane_paths: list[Path], brand_dir: Path, out_dir: Path,
              viewport: tuple[int, int] = DEFAULT_VIEWPORT,
              annotate_match: str = "stress", top: int = 10,
              shots: bool = True, annotate_top: int = 5) -> dict:
    from playwright.sync_api import sync_playwright

    book = load_brand_facts(brand_dir, viewport_w=viewport[0])
    out_dir.mkdir(parents=True, exist_ok=True)
    lanes_out: list[dict] = []
    screenshots: list[dict] = []
    # derived-scale gate inputs (pass1): present ⇒ generative lanes get scale cells
    scale = _style_scale.load_style_scale(brand_dir)
    type_facts = load_type_facts(brand_dir) if scale else []

    with sync_playwright() as pw:
        for html in lane_paths:
            lane = _lane_name(html, brand_dir)
            entry: dict = {"lane": lane, "html": str(html)}
            if not html.exists():
                entry["error"] = "file not found"
                lanes_out.append(entry)
                continue
            entry["mtime"] = datetime.fromtimestamp(
                html.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            started = time.time()
            try:
                raw = measure_lane(pw, html, viewport)
            except Exception as exc:  # never let one lane sink the run
                entry["error"] = f"{type(exc).__name__}: {exc}"[:300]
                lanes_out.append(entry)
                continue
            classified = [classify_measurement(m, book)
                          for m in raw["measurements"]]
            entry["elapsedS"] = round(time.time() - started, 1)
            entry["pageHeight"] = raw.get("pageHeight")
            entry["counts"] = severity_counts(classified)
            entry["measurements"] = classified
            entry["skips"] = raw.get("skips", [])
            entry["offenders"] = rank_offenders(classified, top=top)
            # scale_adherence (pass1): GENERATIVE lanes only — the marker is a
            # composition.json with schemaVersion composition.v1 (the generated
            # composition contract). The replica's replica-composition.v1 and the
            # marker-less previews stay exempt by construction.
            if scale and _is_generative_lane(html.parent):
                entry["scale"] = classify_scale(raw.get("typeSamples") or [],
                                                classified, type_facts, scale)
            lanes_out.append(entry)

        if shots:
            target = next((e for e in lanes_out
                           if annotate_match in e["lane"] and not e.get("error")),
                          None)
            if target is None:
                target = next((e for e in lanes_out if not e.get("error")), None)
            if target and target.get("offenders"):
                try:
                    screenshots = annotate_offenders(
                        pw, Path(target["html"]), target["offenders"], out_dir,
                        viewport, target["lane"], top=annotate_top)
                except Exception as exc:
                    screenshots = [{"file": "", "lane": target["lane"],
                                    "label": f"annotation failed: {exc}"[:200]}]

    report = shape_report(lanes_out, book, {
        "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "brandDir": str(brand_dir),
        "viewport": f"{viewport[0]}x{viewport[1]}",
    })
    report["screenshots"] = screenshots
    (out_dir / "report.json").write_text(json.dumps(report, indent=2))
    (out_dir / "report.md").write_text(render_md(report))
    return report


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("lanes", nargs="+",
                    help="lane dirs (index.html assumed) or explicit .html files")
    ap.add_argument("--brand", type=Path, required=True,
                    help="brand run dir (brand.yaml + layout-library.yaml)")
    ap.add_argument("--out", type=Path, default=None,
                    help="report dir (default <brand>/spacing-baseline)")
    ap.add_argument("--viewport", default="1440x900", help="WxH (default 1440x900)")
    ap.add_argument("--annotate", default="stress",
                    help="lane-name substring that gets annotated close-ups")
    ap.add_argument("--top", type=int, default=10, help="offender groups per lane")
    ap.add_argument("--strict", action="store_true",
                    help="exit 1 on hard fails / lane errors (gate mode)")
    ap.add_argument("--no-shots", action="store_true", help="skip screenshots")
    return ap


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        w, h = (int(x) for x in args.viewport.lower().split("x"))
    except ValueError:
        raise SystemExit(f"bad --viewport {args.viewport!r} (expected WxH)")
    out_dir = args.out or (args.brand / "spacing-baseline")
    report = run_audit(resolve_lane_paths(args.lanes), args.brand, out_dir,
                       viewport=(w, h), annotate_match=args.annotate,
                       top=args.top, shots=not args.no_shots)
    hard = 0
    errors = 0
    for lane in report["lanes"]:
        if lane.get("error"):
            errors += 1
            print(f"[spacing-audit] {lane['lane']}: ERROR {lane['error']}",
                  file=sys.stderr)
            continue
        c = lane["counts"]
        hard += c["hardFails"]
        print(f"[spacing-audit] {lane['lane']}: {c['total']} measured — "
              f"{c['conform']} conform / {c['drift']} drift / "
              f"{c['wrong-step']} wrong-step / {c['off-ladder']} off-ladder / "
              f"{c['unmapped']} unmapped")
        sc = lane.get("scale")
        if sc:
            hard += sc["hardFails"]
            s = sc["counts"]
            print(f"[spacing-audit] {lane['lane']}: scale adherence — "
                  f"{s['measured']} measured-fact / {s['on-scale']} on-scale / "
                  f"{s['off-scale']} OFF-SCALE")
    print(f"[spacing-audit] report: {out_dir / 'report.md'}")
    if args.strict and (hard or errors):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
