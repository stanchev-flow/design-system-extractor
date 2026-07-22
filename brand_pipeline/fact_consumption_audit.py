#!/usr/bin/env python3
"""fact_consumption_audit.py — FACT-CONSUMPTION AUDIT (AS-83, 2026-07-22).

The paired GATE for the unified fact-merge path (``responsive_facts.merge_brand_facts``).
It generalizes the knob-consumption lint (AS-63, ``composition_lint.lint_knobs``) and the
declared-copy lint (``compose_from_composition.lint_declared_copy``) from ONE fact family
to ALL measured fact families: for every CAPTURED MEASURED fact in a brand's facts, it
verifies the fact was CONSUMED in the rendered output (its consumer's evidence is present
in the emitted HTML/CSS), and it FAILS LOUD for a captured-but-unconsumed measured fact.

Why it exists — the "captured but not consumed" bug class produced nearly every recent
defect (nav bg, nav collapse, sticky column, hero alignment, per-section surface,
line-height). A fact was measured in Phase 1/2, merged into the doc the replica consumed,
and then SILENTLY dropped on a code path that never read it — invisible to a screenshot
gate and to a CSS-property diff (the missing rule simply isn't there). This audit makes
that class impossible to ship silently: a measured fact with no consumption evidence is an
ERROR; an EXPLICITLY excluded fact (``responsive_facts.GENERATION_UNSAFE_FAMILIES``) is a
documented PASS; a family owned by a sibling gate is a delegated PASS naming that gate.

Provenance-aware. Only facts tagged measured (``provenance.origin ∈ {extracted,
measured}``) are hard errors — an authored/designed value the composer chose not to use is
not a defect. Every finding carries the fact path, its provenance, the named consumer, and
the consumption evidence checked, so the output is a driver list for the next batch.

Brand-agnostic. No brand names, palettes, section names or content examples live here — the
registry names generic fact families + generic consumer evidence signals (the fact-gated
CSS comment markers each consumer already emits, plus structural markers like
``data-surface`` / ``position: sticky``).

Usage (standalone — LOUD gate, non-zero exit on an unconsumed measured fact):
    ./venv/bin/python brand_pipeline/fact_consumption_audit.py <brand.yaml> <render_dir>
Also surfaced as advisory rows by ``onbrand_check`` (``check_fact_consumption``).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import responsive_facts as rf  # noqa: E402  (exclusion table + canonical merge + sidecar)

AS_ID = "AS-83"

# status values (a finding is a PASS unless status == "unconsumed")
CONSUMED = "consumed"        # consumer evidence present in the output (PASS)
UNCONSUMED = "unconsumed"    # measured fact with NO consumer evidence (FAIL — loud)
EXCLUDED = "excluded"        # documented generation-unsafe exclusion (PASS)
DELEGATED = "delegated"      # verified by a named sibling gate (PASS)
NOT_CAPTURED = "not-captured"  # family absent for this brand (fact-gate; not reported)

_MEASURED_ORIGINS = {"extracted", "measured"}


@dataclass
class Finding:
    family: str            # canonical fact family (generic, never brand/section-specific)
    path: str              # the fact's location (dotted path in the facts)
    status: str            # one of the status constants above
    origin: str            # provenance origin (extracted/measured/designed/unknown)
    consumer: str          # the REAL consuming code (test-pinned) or the owning gate
    evidence: str          # the consumption signal checked in the output
    detail: str            # human-readable outcome
    provenance: str        # the fact's own provenance note (why it was captured)

    @property
    def is_error(self) -> bool:
        return self.status == UNCONSUMED

    @property
    def is_measured(self) -> bool:
        return self.origin in _MEASURED_ORIGINS


# ── output-evidence helpers ─────────────────────────────────────────────────────────

def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", str(s or ""))


def _marker_present(html: str, marker: str) -> bool:
    """A fact-gated consumer emits ``/* … (fact-gated: <path>) … */`` in its CSS exactly
    when it consumes the fact — the most reliable consumption signal (byte-for-byte the
    same string the emitter writes, so it can never drift from the consumer)."""
    return marker in (html or "")


def _mega_panel_paints(html: str, value: str) -> bool:
    """The measured mega-panel surface is consumed when the panel container selector
    (``.cs-mega``) carries the resolved background literal — the nav-panel fact's consumer
    (``component_render.render_mega`` surface override)."""
    if not value:
        return False
    return bool(re.search(r"\.cs-mega\b[^{]*\{[^}]*background\s*:\s*"
                          + re.escape(value.strip()), html or "", re.S | re.I))


def _hover_transform_purged(html: str) -> bool:
    """The brand-wide hover-transform purge is consumed when the un-grounded button lift
    (``transform: translateY(-1px)``) is ABSENT from the emitted CSS (an absence fact —
    consumption removes the default the source never had)."""
    return "translateY(-1px)" not in (html or "")


def _origin_of(block) -> str:
    if isinstance(block, dict):
        prov = block.get("provenance")
        if isinstance(prov, dict):
            return str(prov.get("origin") or "unknown")
        if isinstance(prov, list):
            return "extracted" if prov else "unknown"
    return "unknown"


def _prov_note(block, key: str | None = None) -> str:
    if not isinstance(block, dict):
        return ""
    prov = block.get("provenance")
    if isinstance(prov, dict):
        if key and prov.get(key):
            return _norm(prov.get(key))[:220]
        # first descriptive note that is not the origin/source bookkeeping
        for k, v in prov.items():
            if k not in ("origin", "source") and isinstance(v, str) and v.strip():
                return _norm(v)[:220]
        return _norm(f"origin={prov.get('origin')} source={prov.get('source')}")[:220]
    return ""


# ── the RESPONSIVE measured-fact families (the proven bug class) ─────────────────────
#
# Each entry: (family, exclusion_key, consumer, probe(html, sidecar)->bool|None, evidence).
# ``exclusion_key`` maps a family onto ``responsive_facts.GENERATION_UNSAFE_FAMILIES`` so a
# documented generation exclusion reports EXCLUDED (PASS), never a silent drop. ``probe``
# returns True (consumed), False (unconsumed) or None (family not captured for this brand).


def _cap_hero(sc: dict):
    h = sc.get("hero")
    if isinstance(h, dict) and (h.get("heightRule") or h.get("headingSizeLadder")
                                or h.get("navOffset")):
        return h
    return None


def _cap_hero_button(sc: dict):
    h = sc.get("hero")
    b = h.get("primaryButton") if isinstance(h, dict) else None
    return b if isinstance(b, dict) else None


def _cap_footer(sc: dict):
    f = sc.get("footer")
    return f if isinstance(f, dict) and (f.get("grid") or f.get("maxWidth")) else None


def _cap_headings(sc: dict):
    h = sc.get("headings")
    return h if isinstance(h, dict) and h.get("lineHeights") else None


def _cap_nav_collapse(sc: dict):
    n = sc.get("nav")
    c = n.get("collapse") if isinstance(n, dict) else None
    return c if isinstance(c, dict) and c.get("breakpoint") else None


def _cap_nav_panel(sc: dict):
    n = sc.get("nav")
    p = n.get("panelSurface") if isinstance(n, dict) else None
    return p if isinstance(p, dict) and p.get("background") else None


def _cap_buttons_purge(sc: dict):
    b = sc.get("buttons")
    return b if isinstance(b, dict) and b.get("purgeHoverTransform") else None


# family -> spec. The consumer strings name REAL consuming code (test-pinned by literal
# source grep in the tests) — an entry with no consumer is the lie this audit exists to
# catch, so never add one speculatively.
_RESPONSIVE_FAMILIES = [
    {
        "family": "responsive.hero",
        "path": "layouts[hero].responsive (heightRule / headingSizeLadder / navOffset)",
        "exclusion_key": "hero",
        "capture": _cap_hero,
        "consumer": "component_render.hero_responsive_css",
        "evidence": "CSS marker '(fact-gated: layouts[].responsive)'",
        "probe": lambda html, b: _marker_present(html, "fact-gated: layouts[].responsive)"),
    },
    {
        "family": "responsive.hero.primaryButton",
        "path": "layouts[hero].responsive.primaryButton",
        "exclusion_key": "hero",
        "capture": _cap_hero_button,
        "consumer": "component_render.hero_primary_button_css",
        "evidence": "CSS marker '(fact-gated: layouts[].responsive.primaryButton)'",
        "probe": lambda html, b: _marker_present(
            html, "fact-gated: layouts[].responsive.primaryButton)"),
    },
    {
        "family": "responsive.footer",
        "path": "footer.responsive (grid reflow + measured content cap)",
        "exclusion_key": None,
        "capture": _cap_footer,
        "consumer": "component_render.footer_responsive_css",
        "evidence": "CSS marker '(fact-gated: footer.responsive)'",
        "probe": lambda html, b: _marker_present(html, "fact-gated: footer.responsive)"),
    },
    {
        "family": "responsive.headings.lineHeights",
        "path": "responsive.headings.lineHeights",
        "exclusion_key": "headings",
        "capture": _cap_headings,
        "consumer": "component_render.heading_responsive_css",
        "evidence": "CSS marker '(fact-gated: responsive.headings.lineHeights)'",
        "probe": lambda html, b: _marker_present(
            html, "fact-gated: responsive.headings.lineHeights)"),
    },
    {
        "family": "responsive.nav.collapse",
        "path": "responsive.nav.collapse (mobile breakpoint + burger)",
        "exclusion_key": None,
        "capture": _cap_nav_collapse,
        "prov": lambda sc: sc.get("nav"),  # provenance lives on the parent nav block
        "consumer": "component_render.nav_collapse_css + compose_section._navbar_props",
        "evidence": "CSS marker '(fact-gated: responsive.nav.collapse)'",
        "probe": lambda html, b: _marker_present(
            html, "fact-gated: responsive.nav.collapse)"),
    },
    {
        "family": "responsive.nav.panelSurface",
        "path": "responsive.nav.panelSurface.background",
        "exclusion_key": None,
        "capture": _cap_nav_panel,
        "prov": lambda sc: sc.get("nav"),  # provenance lives on the parent nav block
        "consumer": "component_render.render_mega (panel surface override)",
        "evidence": ".cs-mega { background: <resolved panel literal> }",
        "probe": lambda html, b: _mega_panel_paints(
            html, str((b.get("background") or "")).strip()),
    },
    {
        "family": "responsive.buttons.purgeHoverTransform",
        "path": "responsive.buttons.purgeHoverTransform",
        "exclusion_key": None,
        "capture": _cap_buttons_purge,
        "consumer": "component_render._button_variant_css (motion purge)",
        "evidence": "no 'transform: translateY(-1px)' in the emitted button CSS",
        "probe": lambda html, b: _hover_transform_purged(html),
    },
]


# ── INTERACTION measured-fact families (interaction-facts.yaml) ──────────────────────
#
# The capture-prompt upgrades derive structured carousel timing, exhaustive per-component
# states, the mobile hamburger→drawer contract, the sticky/scroll-shrink nav register, and
# shadow/z-index scales + a footer locale selector into ``interaction-facts.yaml``, merged
# into the doc's PRIVATE ``_interactionFacts`` namespace (rf.merge_interaction_facts) so a
# brand that authored a same-named key but has no sidecar stays byte-identical. Each family
# is CONSUMED by a fact-gated ``component_render`` emitter that writes a
# ``/* … (fact-gated: <path>) … */`` marker; the probe checks that marker.


def _ifacts(doc: dict) -> dict:
    f = doc.get("_interactionFacts") if isinstance(doc, dict) else None
    return f if isinstance(f, dict) else {}


_INTERACTION_FAMILIES = [
    {
        "family": "interaction.carousel",
        "path": "blocks.carousel.carousel (structured slider timing recipe)",
        "capture": lambda d: _ifacts(d).get("carousel"),
        "consumer": "component_render.carousel_timing_css",
        "evidence": "CSS marker '(fact-gated: blocks.carousel.carousel)'",
        "probe": lambda html: _marker_present(html, "fact-gated: blocks.carousel.carousel)"),
    },
    {
        "family": "interaction.states",
        "path": "interactionStates (per-component hover/active/focus/disabled)",
        "capture": lambda d: _ifacts(d).get("interactionStates"),
        "consumer": "component_render.interaction_states_css",
        "evidence": "CSS marker '(fact-gated: interactionStates)'",
        "probe": lambda html: _marker_present(html, "fact-gated: interactionStates)"),
    },
    {
        "family": "interaction.navbar.mobile",
        "path": "navbar.mobile (hamburger→drawer contract)",
        "capture": lambda d: (_ifacts(d).get("navbar") or {}).get("mobile"),
        "consumer": "component_render.navbar_mobile_drawer_css",
        "evidence": "CSS marker '(fact-gated: navbar.mobile)'",
        "probe": lambda html: _marker_present(html, "fact-gated: navbar.mobile)"),
    },
    {
        "family": "interaction.navbar.sticky",
        "path": "navbar.sticky (sticky / scroll-shrink register)",
        "capture": lambda d: (_ifacts(d).get("navbar") or {}).get("sticky"),
        "consumer": "component_render.navbar_sticky_css + navbar_sticky_script",
        "evidence": "CSS marker '(fact-gated: navbar.sticky)'",
        "probe": lambda html: _marker_present(html, "fact-gated: navbar.sticky)"),
    },
    {
        "family": "interaction.tokens.shadow",
        "path": "tokens.shadow (measured elevation scale)",
        "capture": lambda d: (_ifacts(d).get("tokens") or {}).get("shadow"),
        "consumer": "component_render.elevation_tokens_css",
        "evidence": "CSS marker '(fact-gated: tokens.shadow)'",
        "probe": lambda html: _marker_present(html, "fact-gated: tokens.shadow)"),
    },
    {
        "family": "interaction.tokens.zIndex",
        "path": "tokens.zIndex (measured stacking scale)",
        "capture": lambda d: (_ifacts(d).get("tokens") or {}).get("zIndex"),
        "consumer": "component_render.elevation_tokens_css",
        "evidence": "CSS marker '(fact-gated: tokens.zIndex)'",
        "probe": lambda html: _marker_present(html, "fact-gated: tokens.zIndex)"),
    },
    {
        "family": "interaction.footer.localeSelector",
        "path": "footer.localeSelector (language/region control)",
        "capture": lambda d: (_ifacts(d).get("footer") or {}).get("localeSelector"),
        "consumer": "component_render.footer_locale_selector_html",
        "evidence": "HTML marker '(fact-gated: footer.localeSelector)'",
        "probe": lambda html: _marker_present(html, "fact-gated: footer.localeSelector)"),
    },
]


# ── LAYOUT interaction-device measured facts (sticky column & siblings) ──────────────
#
# ``specialTreatments`` live in the layout-library sidecar beside brand.yaml; a treatment
# tagged ``origin: extracted`` is a MEASURED interaction device the static composers must
# draw. ``sticky-column`` is the proving unconsumed case: the source pins the copy column
# while the card grid scrolls, but the composer emits no ``position: sticky`` — invisible
# to a CSS-property diff (the rule is simply absent). Generic device-kind → evidence table.

_SPECIAL_TREATMENT_EVIDENCE = {
    "sticky-column": ("position: sticky",
                      "compose_section.stamp_pattern_devices (sticky-column device)"),
    "marquee": ("cs-marquee", "compose_section.stamp_pattern_devices (marquee device)"),
    "edge-cut": ("cs-edgecut", "compose_section.stamp_pattern_devices (edge-cut device)"),
    "inset-emphasis": ("cs-inset", "compose_section.stamp_pattern_devices (inset device)"),
}


def _load_layout_library(brand_dir: Path) -> dict:
    try:
        import yaml
        p = Path(brand_dir) / "layout-library.yaml"
        if not p.is_file():
            return {}
        return yaml.safe_load(p.read_text()) or {}
    except Exception:
        return {}


def _special_treatment_facts(library: dict):
    """[(kind, layout_id, origin)] for every specialTreatment declared in the layout
    library — a measured interaction device the composer is expected to draw. The library
    keys its entries under ``patterns`` (layout-patterns.v1); ``layouts`` is accepted as a
    fallback for older shapes."""
    out = []
    layouts = None
    if isinstance(library, dict):
        layouts = library.get("patterns") or library.get("layouts")
    for lay in (layouts or []):
        if not isinstance(lay, dict):
            continue
        lid = str(lay.get("id") or "layout")
        origin = str(lay.get("origin") or "unknown")
        for t in (lay.get("specialTreatments") or []):
            if isinstance(t, dict) and t.get("kind"):
                out.append((str(t["kind"]), lid, origin))
    return out


# ── per-section surface measured fact (data-surface consumption) ─────────────────────

def _surface_facts(doc: dict):
    """[(surfaceIntent, layout_id, origin)] for layouts that carry a measured section
    surface — the per-section surface fact. Consumed when the rendered section carries the
    matching ``data-surface`` attribute (compose_section.resolve_surface → section paint)."""
    out = []
    for lay in (doc.get("layouts") or []):
        if not isinstance(lay, dict):
            continue
        intent = lay.get("surfaceIntent") or lay.get("surfaceRole")
        if intent:
            out.append((str(intent), str(lay.get("id") or "layout"),
                        str(lay.get("origin") or "unknown")))
    return out


# ── families delegated to a sibling gate (enumerated, documented pass) ───────────────
#
# These enumerated families are verified by an existing gate; the audit reports them as a
# DELEGATED pass naming that gate rather than re-probing (the same discipline as
# onbrand_check._PHYSICS_DELEGATED). This keeps the audit's ENUMERATION complete without
# duplicating — or contradicting — a sibling gate's verdict.
_DELEGATED_FAMILIES = [
    ("tokens.type", "tokens", "type",
     "css_fidelity.heading_tier_divergences (C-checks)"),
    ("tokens.spacing", "tokens", "spacing",
     "css_fidelity.spacing_tier_divergences (C-checks)"),
    ("tokens.radius", "tokens", "radius",
     "css_fidelity.radius_tier_divergences (C-checks)"),
    ("tokens.colors", "tokens", "colors",
     "css_fidelity.color_role_divergences (C-checks)"),
    ("layoutGrammar.actionGroup", "actionGroup", None,
     "composition_lint.lint_knobs (AS-63) + onbrand fidelity"),
    ("mediaComposition", "mediaComposition", None,
     "onbrand_check.check_media_bindings (AS-67/AS-80)"),
]


def _doc_has(doc: dict, top: str, sub: str | None) -> bool:
    node = doc.get(top) if isinstance(doc, dict) else None
    if not node:
        return False
    if sub is None:
        return True
    if isinstance(node, dict):
        return bool(node.get(sub))
    return False


def _recipes_captured(doc: dict) -> bool:
    for lay in (doc.get("layouts") or []):
        if isinstance(lay, dict) and (lay.get("recipeRef") or lay.get("recipe")):
            return True
    return False


# ── the audit ───────────────────────────────────────────────────────────────────────

def audit_facts(*, sidecar: dict, doc: dict, library: dict, html: str,
                target: str) -> list[Finding]:
    """The core audit: enumerate captured measured facts across the fact families and
    verify each is consumed in ``html`` (or is a documented exclusion / delegated to a
    named sibling gate). ``target`` ∈ {"replica", "generation"} selects the documented
    exclusion set. Pure data-in/data-out (no disk, no brand knowledge) so it is directly
    unit-testable with a planted sidecar."""
    sidecar = sidecar or {}
    doc = doc or {}
    html = html or ""
    excluded = rf.excluded_families_for(target)
    findings: list[Finding] = []

    # 1) responsive measured-fact families (marker / structural probes)
    for spec in _RESPONSIVE_FAMILIES:
        block = spec["capture"](sidecar)
        if block is None:
            continue  # fact-gate: family not captured for this brand → not reported
        # provenance may live on the captured block itself or (for a sub-block like
        # nav.collapse / nav.panelSurface) on the family's parent block.
        prov_block = spec.get("prov", lambda _sc: block)(sidecar) or block
        origin = _origin_of(prov_block)
        prov = _prov_note(prov_block)
        ekey = spec["exclusion_key"]
        if ekey and ekey in excluded:
            findings.append(Finding(
                family=spec["family"], path=spec["path"], status=EXCLUDED, origin=origin,
                consumer=spec["consumer"], evidence=spec["evidence"],
                detail=(f"documented generation exclusion ({ekey}): "
                        + _norm(excluded[ekey])[:200]),
                provenance=prov))
            continue
        consumed = bool(spec["probe"](html, block))
        findings.append(Finding(
            family=spec["family"], path=spec["path"],
            status=CONSUMED if consumed else UNCONSUMED, origin=origin,
            consumer=spec["consumer"], evidence=spec["evidence"],
            detail=("consumer evidence present" if consumed else
                    "CAPTURED measured fact with NO consumer evidence in the output"),
            provenance=prov))

    # 1b) INTERACTION measured-fact families (interaction-facts.yaml → _interactionFacts).
    #     Each is captured when the sidecar-merged private namespace carries the family and
    #     consumed when its fact-gated CSS/HTML marker is present. These families are
    #     register-neutral, so they are audited identically for replica and generation.
    for spec in _INTERACTION_FAMILIES:
        block = spec["capture"](doc)
        if not isinstance(block, dict) or not block:
            continue  # fact-gate: family not captured for this brand → not reported
        origin = _origin_of(block) if _origin_of(block) != "unknown" else "extracted"
        prov = _prov_note(block) or "evidence-derived interaction fact"
        consumed = bool(spec["probe"](html))
        findings.append(Finding(
            family=spec["family"], path=spec["path"],
            status=CONSUMED if consumed else UNCONSUMED, origin=origin,
            consumer=spec["consumer"], evidence=spec["evidence"],
            detail=("consumer evidence present" if consumed else
                    "CAPTURED measured interaction fact with NO consumer evidence in the "
                    "output"),
            provenance=prov))

    # 2) layout interaction-device facts (sticky-column & siblings) from the library.
    #    These are SOURCE-section-reproduction facts (a measured device on a source
    #    pattern), so they are audited against the REPLICA (which reproduces the source's
    #    patterns). A GENERATED page composes its own sections, so whether it uses a given
    #    source pattern is a composition decision — delegated there (a device on a pattern
    #    the composition did not seed is not a captured-fact drop for that page).
    hay = _norm(html)
    if target == "replica":
        for kind, lid, origin in _special_treatment_facts(library):
            signal, consumer = _SPECIAL_TREATMENT_EVIDENCE.get(
                kind, (None, "compose_section.stamp_pattern_devices"))
            if signal is None:
                continue  # unknown device kind — no registered evidence signal
            consumed = _norm(signal) in hay
            findings.append(Finding(
                family=f"layout.specialTreatment.{kind}",
                path=f"patterns[{lid}].specialTreatments",
                status=CONSUMED if consumed else UNCONSUMED, origin=origin,
                consumer=consumer, evidence=f"'{signal}' present in the emitted markup",
                detail=("device rendered" if consumed else
                        f"CAPTURED {kind} interaction device with NO render evidence "
                        f"('{signal}' absent) — the composer left it un-drawn"),
                provenance=f"layout-library specialTreatment kind={kind} (origin={origin})"))
    elif _special_treatment_facts(library):
        findings.append(Finding(
            family="layout.specialTreatment", path="composition sections' devices",
            status=DELEGATED, origin="extracted",
            consumer="onbrand_check.check_anatomy_presence (AS-81) + composition invariants",
            evidence="verified by the owning sibling gate",
            detail="delegated for generation: a composed page seeds its own patterns, not "
                   "the source's specialTreatment patterns",
            provenance="enumerated fact family"))

    # 3) per-section surface facts (data-surface consumption). These are the SOURCE's
    #    measured per-section surfaces (brand layouts). They are a REPLICA-faithfulness
    #    fact — the replica reproduces the source's sections, so each must paint. A
    #    GENERATED page composes its OWN sections (doc.layouts is replaced by the
    #    composition), so the source's per-section surfaces do not all apply; the composed
    #    page's own section surfaces are a composition concern (delegated to onbrand
    #    fidelity), not a captured-fact drop — so this family delegates for generation.
    if target == "replica":
        for intent, lid, origin in _surface_facts(doc):
            consumed = f'data-surface="{intent}"' in html
            findings.append(Finding(
                family="layout.surfaceIntent",
                path=f"layouts[{lid}].surfaceIntent={intent}",
                status=CONSUMED if consumed else UNCONSUMED, origin=origin,
                consumer="compose_section.resolve_surface → section paint",
                evidence=f'data-surface="{intent}" on the rendered section',
                detail=("section painted its measured surface" if consumed else
                        f"CAPTURED per-section surface '{intent}' not painted on any "
                        "rendered section (data-surface absent)"),
                provenance=f"layout surfaceIntent (origin={origin})"))
    elif _surface_facts(doc):
        findings.append(Finding(
            family="layout.surfaceIntent", path="composition sections' surfaceIntent",
            status=DELEGATED, origin="extracted",
            consumer="onbrand fidelity (composed sections paint their own surfaces)",
            evidence="verified by the owning sibling gate",
            detail="delegated for generation: a composed page uses its own sections, "
                   "not the source's per-section surface layouts",
            provenance="enumerated fact family"))

    # 4) enumerated families delegated to a sibling gate (documented pass)
    for family, top, sub, gate in _DELEGATED_FAMILIES:
        if _doc_has(doc, top, sub):
            findings.append(Finding(
                family=family, path=f"{top}.{sub}" if sub else top, status=DELEGATED,
                origin="designed" if top in ("actionGroup",) else "extracted",
                consumer=gate, evidence="verified by the owning sibling gate",
                detail=f"delegated to {gate}", provenance="enumerated fact family"))
    if _recipes_captured(doc):
        findings.append(Finding(
            family="recipes", path="layouts[].recipeRef", status=DELEGATED,
            origin="designed", consumer="onbrand fidelity + composition invariants",
            evidence="verified by the owning sibling gate",
            detail="delegated to onbrand fidelity/composition gates",
            provenance="enumerated fact family"))

    return findings


def audit_render(brand_yaml: Path, render_dir: Path,
                 target: str | None = None) -> list[Finding]:
    """Run the audit for an on-disk render: load the sidecar + the MERGED doc (through the
    canonical ``merge_brand_facts``, so what the renderer saw is what we audit) + the
    layout library + the emitted HTML, infer the ``target`` from the render's own
    composition.json (a generated ``composition.v1`` → generation; else replica), and
    return the findings."""
    import yaml
    brand_yaml = Path(brand_yaml)
    render_dir = Path(render_dir)
    brand_dir = brand_yaml.parent
    doc = yaml.safe_load(brand_yaml.read_text()) or {}
    if target is None:
        target = _infer_target(render_dir)
    rf.merge_brand_facts(doc, brand_dir, target=target)
    sidecar = rf.load_sidecar(brand_dir)
    library = _load_layout_library(brand_dir)
    html = (render_dir / "index.html").read_text() if (render_dir / "index.html").is_file() \
        else ""
    return audit_facts(sidecar=sidecar, doc=doc, library=library, html=html, target=target)


def _infer_target(render_dir: Path) -> str:
    """A render whose composition.json is a generated ``composition.v1`` is a GENERATION
    artifact; the replica assembler's ``replica-composition.v1`` (and composition-less
    lanes) are replica artifacts."""
    try:
        comp = json.loads((Path(render_dir) / "composition.json").read_text())
        if isinstance(comp, dict) and comp.get("schemaVersion") == "composition.v1":
            return "generation"
    except (OSError, ValueError, TypeError):
        pass
    return "replica"


# ── report shaping (JSON + markdown + gate rows) ─────────────────────────────────────

def summarize(findings: list[Finding]) -> dict:
    measured_unconsumed = [f for f in findings if f.is_error]
    return {
        "as": AS_ID,
        "ok": not measured_unconsumed,
        "counts": {
            "total": len(findings),
            "consumed": sum(1 for f in findings if f.status == CONSUMED),
            "unconsumed": len(measured_unconsumed),
            "excluded": sum(1 for f in findings if f.status == EXCLUDED),
            "delegated": sum(1 for f in findings if f.status == DELEGATED),
        },
        "unconsumed": [f.family for f in measured_unconsumed],
        "findings": [asdict(f) for f in findings],
    }


def gate_rows(findings: list[Finding]) -> list[tuple[str, str, bool, str]]:
    """onbrand_check-style (rid, label, passed, detail) rows. One row per audited fact so
    an unconsumed measured fact is individually visible; excluded/delegated/consumed pass."""
    rows: list[tuple[str, str, bool, str]] = []
    for f in findings:
        passed = f.status != UNCONSUMED
        label = f"{f.family} consumed ({AS_ID})"
        detail = f"{f.status}: {f.detail}"
        rows.append((f"fact-consumption:{f.family}", label, passed, detail))
    return rows


def render_markdown(findings: list[Finding], target: str) -> str:
    s = summarize(findings)
    L = [f"# Fact-consumption audit ({AS_ID}) — target: {target}", "",
         f"**{'PASS' if s['ok'] else 'FAIL'}** — "
         f"{s['counts']['consumed']} consumed / {s['counts']['unconsumed']} unconsumed / "
         f"{s['counts']['excluded']} excluded / {s['counts']['delegated']} delegated.", ""]
    if s["unconsumed"]:
        L.append("> Captured-but-UNCONSUMED measured facts (driver list for the next "
                 "batch — do NOT fix the renderers here, the audit flags them):")
        for f in findings:
            if f.is_error:
                L.append(f"> - `{f.family}` — {f.detail} (consumer: {f.consumer}; "
                         f"evidence: {f.evidence})")
        L.append("")
    L += ["| family | status | origin | consumer | evidence | provenance |",
          "|---|---|---|---|---|---|"]
    for f in findings:
        L.append(f"| `{f.family}` | {f.status} | {f.origin} | {f.consumer} | "
                 f"{f.evidence} | {f.provenance} |")
    L.append("")
    return "\n".join(L)


def write_reports(render_dir: Path, findings: list[Finding], target: str) -> dict:
    render_dir = Path(render_dir)
    summary = summarize(findings)
    summary["target"] = target
    (render_dir / "fact-consumption-audit.json").write_text(
        json.dumps(summary, indent=2) + "\n")
    (render_dir / "fact-consumption-audit.md").write_text(
        render_markdown(findings, target))
    return summary


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("brand_yaml", type=Path)
    ap.add_argument("render_dir", type=Path)
    ap.add_argument("--target", choices=("replica", "generation"), default=None,
                    help="override the auto-inferred merge target")
    ap.add_argument("--no-write", action="store_true",
                    help="print only; do not write the audit report beside the render")
    args = ap.parse_args(argv)
    target = args.target or _infer_target(args.render_dir)
    findings = audit_render(args.brand_yaml, args.render_dir, target=target)
    summary = summarize(findings)
    if not args.no_write:
        write_reports(args.render_dir, findings, target)
    # LOUD: print the inventory + shout every unconsumed measured fact on stderr.
    print(f"[fact-consumption/{AS_ID}] target={target} "
          f"consumed={summary['counts']['consumed']} "
          f"unconsumed={summary['counts']['unconsumed']} "
          f"excluded={summary['counts']['excluded']} "
          f"delegated={summary['counts']['delegated']}")
    for f in findings:
        tag = {CONSUMED: "PASS", EXCLUDED: "PASS(excluded)", DELEGATED: "PASS(delegated)",
               UNCONSUMED: "FAIL"}.get(f.status, f.status)
        print(f"  [{tag}] {f.family}: {f.detail}")
    if not summary["ok"]:
        sys.stderr.write(
            f"[fact-consumption/{AS_ID}] {summary['counts']['unconsumed']} CAPTURED "
            "measured fact(s) reached the brand doc but were NOT consumed in the output "
            "(silent drop — the 'captured but not consumed' bug class):\n")
        for f in findings:
            if f.is_error:
                sys.stderr.write(f"  - {f.family} [{f.path}]: {f.detail}\n")
    return 0 if summary["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
