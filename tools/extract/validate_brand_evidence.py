#!/usr/bin/env python3
"""validate_brand_evidence.py — fail-loud output contract for a brand extraction.

Checks a `runs/<brand>/brand/` folder against the evidence contract the
extraction redo mandates. Every failure names WHAT is missing, WHERE it lives,
and WHICH stage/author step produces it — the checks encode exactly the gaps
that broke the Remote run (no section copy, no card block, single button
variant, logo wall without logo assets, `legal.copyright` vs `legal.text`,
no vision evidence).

Checks (E = error, W = warning):
  C1 E  brand.yaml exists and parses
  C2 E  every contract block type ATTEMPTED: present in brand.yaml `blocks:`
        with evidence, or explicitly `notObserved: true` (card called out)
  C3 E  button variant matrix: >= 1 family, each with radius + surface + a
        state fact; a single family requires `singleVariantConfirmed: true`.
        STRICT state pairing (sysfix 2026-07): a family measuring `bgHover`
        must also measure `fgHover` (any value, incl. "unchanged"); a FILLED
        family (style filled* or opaque bg) must measure `height` + `padding`
  C4 E  section-copy.yaml present, schema-conformant, wordmark set; every
        content-bearing non-chrome layout has a layoutCopy entry
  C5 E/W layout<->pattern coverage: non-chrome layouts carry patternRef (or
        `noPatternReason`); orphan patterns warn; observed-section breadth warns
  C6 E  logo evidence: a logos use-case requires >= --min-logo-assets on-disk
        logo files (or assets tagged logo-wall-logo)
  C7 E/W chrome: navbar links + surface + presentation/measured facts; footer
        columns/social; `legal.copyright` without `legal.text` is an error.
        RANGE + INTEGRITY (sysfix 2026-07): measured contentMaxWidth must be
        480–2200px when present; a grid-grammar footer needs headed columns;
        a declared nav logo must be renderable (src / svg / wordmark text);
        a footer logo must not be a third-party app/badge/rating asset;
        mega-menu column headings must not be a prefix of their first link
        label (the label-concatenation capture bug)
  C8 E/W assets-tagged.json exists; every tagged file exists under assets/
  C9 E  vision evidence: >= 1 evidence/grounding/*.yaml (--allow-no-vision
        downgrades to warning)
  C10 E card variant coverage: a usable blocks.card must enumerate observed
        `variants:` or carry `singleVariantConfirmed: true`
  C11 E composed-demo smoke (needs the brand_pipeline harness; --no-smoke
        skips): every referenced layout-library pattern composes with no
        srcless `c-image-ph` placeholder markup and no empty module captions
        when authored items exist; a pattern declaring centered alignment
        must stamp an anchor through the composition adapter
  C12 E escape hygiene: generated preview/chrome HTML under the brand dir
        (and the C11 smoke renders) must not contain double-escaped entity
        text such as `&amp;mdash;`
  C13 E motion evidence: `tokens.motion` present with >= 1 evidenced duration
        AND >= 1 easing (or explicit `notObserved: true` + reason). Interactive
        blocks (accordion/tabs/modal/dropdown-menu/carousel) that are evidenced
        must name a timing fact (any `Nms`/`N.Ns` value or a `motion:` note) or
        declare their motion `notObserved`. Authored from
        evidence/motion-audit.json (mine_motion.py stage)
  C14 E canonical-tier discipline: when tokens.type carries sized roles the
        brand declares `meta.canonicalTier` (which measured breakpoint every
        canonical value refers to), and every sized type role carries a
        responsive ladder of >= 2 breakpoints OR an explicit
        `singleTierConfirmed: true` (measured constant across the tier ladder).
        Authored from the measure stage's per-tier samples (computed-styles
        `tiers` — measure_computed.py)
  C15 E relational spacing ladder: tokens.spacing carries >= 2 named RELATIONAL
        rungs (`<role>-to-<role>`: eyebrow-to-heading, heading-to-body,
        body-to-cta, …), each with a value — or an explicit
        `tokens.spacing.relationalLadder: {notObserved: true, reason: …}`
        marker when the source's rhythm genuinely exposes no such ladder.
        COMPLETENESS (fid11): when the mined corpus (cssRuleCorpus) exposes
        relational spacing custom properties — vars pairing two content roles
        with a spacing/gap word, or row-gap/column-gutter rhythm vars — every
        exposed pair rung must be authored under its generic canonical name,
        plus a row rung (block-to-block / grid-gap) and a column rung
        (column-to-column / grid-gap); notObserved alongside exposed pair
        vars is a contradiction
  C16 E/W chrome DEPTH facts (fid4 2026-07), each requirement triggered by the
        brand's OWN evidence: a navbar.primary `menu` needs populated column
        groups (heading+links) and measured.megaPanel motion facts with a time
        literal; megaOpen entries need real panel boxes and a matching menu;
        icon/card/badge `asset:` refs must exist on disk; a footer.social
        entry captured as kind: icon must bind harvested artwork; a measured
        footer grid's wrapperSizes must sum to the extracted group count and
        headed columns need measured.heading style facts; footer.bottomBar
        needs divider presence + {label, href} policy links (social+legal
        without any bottomBar facts warns)
  C17 E disclosure per-item interaction content (fid8 2026-07): a layoutCopy
        entry whose items list shows a disclosure pattern (>= 2 items, any
        item carrying `body`) must carry a `body` on EVERY item — the states
        hidden at static-capture time need the interaction pass — or mark the
        item `bodyNotObserved: true` (entry-level `itemBodiesNotObserved:
        true` accepted). Same all-or-none rule for per-item `media` (the
        active-item media-swap device), and every bound items[].media file
        must exist under the brand's assets (a non-existent name renders
        nothing, silently)
  C18 E contextual header-alignment grammar (fid11): when the observed pattern
        library corroborates a header-alignment rule in BOTH layout contexts
        (>= 2 split patterns agreeing and >= 2 standalone stack/grid patterns
        agreeing, >= 2/3 majority each), layoutGrammar.headerContext must be
        authored with matching splitColumn / standaloneStack anchors — the
        brand-default layer generated sections resolve from (AS-49)
  C21 E/W bar-level AFFORDANCES (fid15, C16's sibling): when the mined corpus
        names a nav trigger chevron/caret, measured.trigger.chevron must carry
        the harvested glyph facts (asset on disk, box; open transform/motion
        warns when absent) or chevronNotObserved; utility-control glyph/chevron
        assets must exist on disk; a dropdown-kind utility control needs its
        live-captured items + panel paint or dropdownNotObserved; a primary
        entry with no href and no menu is a flattened bar control (classify
        under utility or mark utilityNotObserved); a corpus-named in-bar
        language/locale switcher demands a dropdown-kind utility control; an
        observed utilityBanner needs cta anatomy (label+href; ctaNotObserved
        escape) and, when dismissible, close anatomy (kind+box;
        closeNotObserved escape) with all bound assets on disk
  C23 W component-recipe coverage (fix2, brand-schema §4.4e): 2+ patterns
        sharing a rail-like anatomy signature should bind a brand `recipes:`
        entry via recipeRef {recipe, variant}; dangling recipeRefs, empty
        anatomies, id-less variants, and one-way usedBy bindings warn too —
        recipes are brand data written DURING extraction, not post-hoc
  C24 W derived-scale artifact consistency (pass1, style-scale.v1): when
        style-scale.yaml exists it must be INTERNALLY consistent (every space
        step a multiple of the base unit, every type step on base*ratio^k,
        section rhythm a subset of the space steps) and HONEST about fit
        (fitQuality verdicts backed by the recorded errors; a poor fit must
        set followsScale: false — the brand genuinely not following a scale
        is recorded, never forced); staleness vs brand.yaml warns
  C25 W brand signatures (pass1, brand-schema §4.7): the extraction should
        author 3-5 `signatures:` entries (the moves that make THIS brand
        recognizable) — each with a known kind (accent-scope / shape-motif /
        type-treatment / surface-habit / spacing-habit), an always/never
        mode, machine-checkable check params, and evidence provenance;
        missing block, out-of-discipline counts (the "3-5, not 20" rule),
        unknown kinds, and evidence-less entries warn

Importable API (used by brand_pipeline/tests/test_brand_evidence_contract.py):
    report = validate_brand_dir(brand_dir, contracts_path=..., ...)
    report.errors / report.warnings / report.ok

Usage:
    ./venv/bin/python tools/extract/validate_brand_evidence.py --brand-dir runs/<brand>/brand
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_CONTRACTS = REPO_ROOT / "brand_pipeline" / "contracts" / "blocks.yaml"

# a literal double-escaped HTML entity in GENERATED html (e.g. "&amp;mdash;")
# renders as visible "&mdash;" text — always an escaping bug, never content.
DOUBLE_ESCAPED_ENTITY = re.compile(r"&amp;[a-zA-Z]+;")
# third-party store/review badge art masquerading as the brand's footer logo
APP_BADGE_PATTERN = re.compile(r"app.?store|google.?play|play.?store|badge|rating",
                               re.IGNORECASE)
CONTENT_MAX_WIDTH_RANGE = (480, 2200)

ALLOWED_COPY_KEYS = {"sectionCopy", "layoutCopy", "layoutImages", "defaultArt",
                     "wildcardCopy"}
# a CSS time literal ("150ms", ".3s", "0.25s") anywhere in a serialized value
TIME_LITERAL = re.compile(r"\b\d*\.?\d+m?s\b")
# an easing fact: keyword family or a functional timing curve
EASING_LITERAL = re.compile(r"\bease(?:-in|-out|-in-out)?\b|\blinear\b"
                            r"|cubic-bezier\(|steps\(")
# contract block types whose real-world behavior is animated: their evidenced
# entries owe a timing fact (C13)
INTERACTIVE_BLOCK_TYPES = ("accordion", "tabs", "modal", "dropdown-menu",
                           "carousel")
# a RELATIONAL spacing token names the gap between two content roles (C15):
# eyebrow-to-heading, heading-to-body, body-to-cta, label-to-field, …
RELATIONAL_KEY = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*-to-[a-z0-9]+(?:-[a-z0-9]+)*$")
# C15 completeness (fid11): role-synonym classes for detecting the source's OWN
# relational spacing custom properties in the mined CSS corpus. Var names are
# tokenized on hyphens and matched as exact words — a var pairing two DIFFERENT
# role classes with a spacing/gap word (e.g. --*-label-headline-spacing) exposes
# that rung; the brand must then author it under its GENERIC canonical name.
REL_ROLE_WORDS = {
    "eyebrow": ("eyebrow", "label", "kicker", "overline", "tagline"),
    "heading": ("heading", "headline", "title"),
    "body":    ("body", "description", "paragraph", "subtitle", "subhead"),
    "cta":     ("cta", "button", "action"),
}
CANONICAL_RUNGS = {
    ("eyebrow", "heading"): "eyebrow-to-heading",
    ("heading", "body"):    "heading-to-body",
    ("body", "cta"):        "body-to-cta",
}
_REL_ROLE_ORDER = ("eyebrow", "heading", "body", "cta")
CHROME_LAYOUT_ARCHETYPES = {"nav"}
CHROME_LAYOUT_IDS = {"navbar", "footer"}
IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".svg", ".webp", ".gif")


@dataclass
class Report:
    brand_dir: Path
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    # informational notes: resolved/curated states worth seeing but demanding no
    # action (e.g. a C18 dissent a curator already ruled on, brand-schema §4.4c)
    notes: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def error(self, code: str, msg: str) -> None:
        self.errors.append(f"{code}: {msg}")

    def warn(self, code: str, msg: str) -> None:
        self.warnings.append(f"{code}: {msg}")

    def note(self, code: str, msg: str) -> None:
        self.notes.append(f"{code}: {msg}")


def _load_yaml(path: Path):
    return yaml.safe_load(path.read_text()) or {}


def _contract_block_keys(contracts_path: Path) -> list[str]:
    doc = _load_yaml(contracts_path)
    blocks = doc.get("blocks") if isinstance(doc, dict) else None
    if isinstance(blocks, dict):
        return list(blocks.keys())
    # tolerate a bare mapping file (fixtures)
    return [k for k in doc.keys() if isinstance(doc.get(k), dict)] if isinstance(doc, dict) else []


def _is_chrome_layout(layout: dict) -> bool:
    if str(layout.get("archetype") or "") in CHROME_LAYOUT_ARCHETYPES:
        return True
    return str(layout.get("id") or "") in CHROME_LAYOUT_IDS


def _has_content_slot(layout: dict) -> bool:
    return any(str(s.get("type") or "") == "content"
               for s in layout.get("slots") or [] if isinstance(s, dict))


def _sized_type_roles(tokens: dict) -> list[tuple[str, dict]]:
    """(role, node) pairs that carry a size — C14's subjects. Handles BOTH token
    shapes: flat roles (role -> spec) and families+scale (tokens.type.scale)."""
    types = tokens.get("type") if isinstance(tokens.get("type"), dict) else {}
    scale = types.get("scale")
    if isinstance(scale, dict):
        items = scale.items()
    else:
        items = types.items()
    return [(str(k), v) for k, v in items
            if isinstance(v, dict) and v.get("sizeRem") is not None]


def _mentions_logos(doc: dict, patterns: list[dict]) -> bool:
    for layout in doc.get("layouts") or []:
        if str(layout.get("useCase") or "").lower().startswith("customer-proof"):
            return True
        for s in layout.get("slots") or []:
            if isinstance(s, dict) and "logo" in str(s.get("name") or "").lower():
                return True
    return any(str(p.get("useCase") or "").lower() == "logos" for p in patterns)


def validate_brand_dir(brand_dir: Path | str, *, contracts_path: Path | None = None,
                       allow_no_vision: bool = False,
                       min_logo_assets: int = 3,
                       smoke: bool = True) -> Report:
    brand_dir = Path(brand_dir)
    rep = Report(brand_dir)
    contracts_path = contracts_path or DEFAULT_CONTRACTS

    # C1 — brand.yaml
    brand_yaml = brand_dir / "brand.yaml"
    if not brand_yaml.is_file():
        rep.error("C1", f"{brand_yaml} missing — author it from the extraction "
                        "evidence (layout-analyst pass) before validating.")
        return rep
    try:
        doc = _load_yaml(brand_yaml)
    except Exception as exc:
        rep.error("C1", f"{brand_yaml} does not parse as YAML: {exc}")
        return rep
    if not isinstance(doc, dict):
        rep.error("C1", f"{brand_yaml} top level is not a mapping")
        return rep

    # C2 — every contract block type attempted (evidence or explicit notObserved)
    if not contracts_path.is_file():
        rep.warn("C2", f"contracts file not found at {contracts_path} — block "
                       "coverage not checked")
        contract_keys: list[str] = []
    else:
        contract_keys = _contract_block_keys(contracts_path)
    blocks = doc.get("blocks") if isinstance(doc.get("blocks"), dict) else {}
    missing_blocks = []
    for key in contract_keys:
        entry = blocks.get(key)
        if isinstance(entry, dict) and (entry.get("notObserved") is True
                                        or entry.get("origin") or entry.get("use")
                                        or entry.get("slots") or entry.get("provenance")):
            continue
        missing_blocks.append(key)
    if missing_blocks:
        callout = " 'card' is among them — card anatomy (media-well, radius, hover "
        callout += "elevation, link) must be extracted as a component, not left as "
        callout += "layout prose." if "card" in missing_blocks else ""
        rep.error("C2", f"brand.yaml blocks: {len(missing_blocks)} contract block "
                        f"type(s) not attempted: {', '.join(missing_blocks)}. Add "
                        "extracted evidence or an explicit `notObserved: true` per "
                        f"block (source: grounding YAMLs components[]).{callout}")

    # C3 — button variant matrix
    buttons = doc.get("buttons") if isinstance(doc.get("buttons"), dict) else {}
    families = {k: v for k, v in buttons.items() if isinstance(v, dict)
                and k not in ("renderHint",)}
    if not families:
        rep.error("C3", "brand.yaml buttons: no measured button families. Extract "
                        "every observed action style (grounding components kind: "
                        "button; css-facts hoverRules) into buttons:<family> entries.")
    else:
        state_keys = ("bgHover", "fgHover", "decoration", "focus", "hover",
                      "bgPressed")
        for name, fam in families.items():
            missing = []
            if not fam.get("radius"):
                missing.append("radius")
            if not (fam.get("bg") or fam.get("fg") or fam.get("style")):
                missing.append("bg/fg/style")
            if not any(fam.get(k) for k in state_keys):
                missing.append("a state fact (bgHover/fgHover/decoration/focus)")
            # C3-strict (sysfix 2026-07): a measured bg swap without the label's
            # hover fact leaves the renderer guessing label contrast mid-state —
            # measure fgHover too (an explicit "unchanged" marker counts).
            if fam.get("bgHover") and not fam.get("fgHover"):
                missing.append("fgHover (bgHover measured — record the hover label "
                               "color, or an explicit 'unchanged')")
            style = str(fam.get("style") or "").lower()
            bg = str(fam.get("bg") or "").lower()
            filled = style.startswith("filled") or (
                bg and bg not in ("transparent", "none")
                and not bg.startswith("rgba(0, 0, 0, 0"))
            if filled:
                for geom in ("height", "padding"):
                    if not fam.get(geom):
                        missing.append(f"{geom} (filled family — control geometry "
                                       "is measured, not defaulted)")
            if missing:
                rep.error("C3", f"buttons.{name}: missing {', '.join(missing)} — "
                                "each family ships a usable state matrix "
                                "(css-facts hoverRules is the measurement source).")
        if len(families) == 1 and buttons.get("singleVariantConfirmed") is not True:
            only = next(iter(families))
            rep.error("C3", f"buttons: only ONE family ({only}) extracted. Sites "
                            "almost always carry >= 2 action styles (filled/outlined/"
                            "neutral/text). Extract the missing families or set "
                            "`buttons.singleVariantConfirmed: true` after re-checking "
                            "the grounding evidence.")

    # C4 — section-copy.yaml
    copy_path = brand_dir / "section-copy.yaml"
    layouts = [l for l in doc.get("layouts") or [] if isinstance(l, dict)]
    if not copy_path.is_file():
        rep.error("C4", f"{copy_path.name} missing — without it every composed "
                        "section degrades to empty copy (wordmark + arrow renders). "
                        "Author it from the grounding YAMLs' verbatim `copy` blocks "
                        "(see spec/section-copy-schema.md).")
    else:
        try:
            copy_doc = _load_yaml(copy_path)
        except Exception as exc:
            copy_doc = None
            rep.error("C4", f"{copy_path.name} does not parse as YAML: {exc}")
        if isinstance(copy_doc, dict):
            unknown = set(copy_doc.keys()) - ALLOWED_COPY_KEYS
            if unknown:
                rep.error("C4", f"{copy_path.name}: unknown top-level key(s) "
                                f"{sorted(unknown)} — allowed: "
                                f"{sorted(ALLOWED_COPY_KEYS)} (compose_section."
                                "load_brand_copy ignores anything else silently).")
            section_copy = copy_doc.get("sectionCopy")
            if not isinstance(section_copy, dict) or not section_copy:
                rep.error("C4", f"{copy_path.name}: sectionCopy is empty — at "
                                "minimum carry `wordmark:` (nav degrades to "
                                "wordmark-only without it).")
            elif not section_copy.get("wordmark"):
                rep.error("C4", f"{copy_path.name}: sectionCopy.wordmark missing — "
                                "the nav/logo device renders the brand name from it.")
            layout_copy = copy_doc.get("layoutCopy")
            layout_copy = layout_copy if isinstance(layout_copy, dict) else {}
            uncovered = [l.get("id") for l in layouts
                         if not _is_chrome_layout(l) and _has_content_slot(l)
                         and not layout_copy.get(l.get("id"))]
            if uncovered:
                rep.error("C4", "layoutCopy: no copy entry for content-bearing "
                                f"layout(s): {', '.join(map(str, uncovered))} — bind "
                                "each section's REAL verbatim copy (grounding "
                                "`copy` blocks), or the composers render them empty.")

    # C5 — layout<->pattern coverage
    lib_path = brand_dir / "layout-library.yaml"
    patterns: list[dict] = []
    if not lib_path.is_file():
        rep.error("C5", f"{lib_path.name} missing — extracted section patterns are "
                        "the generation seeds (one per observed section family).")
    else:
        try:
            patterns = [p for p in (_load_yaml(lib_path).get("patterns") or [])
                        if isinstance(p, dict)]
        except Exception as exc:
            rep.error("C5", f"{lib_path.name} does not parse as YAML: {exc}")
        if not patterns:
            rep.error("C5", f"{lib_path.name}: zero patterns.")
        pattern_ids = {p.get("id") for p in patterns}
        refless = []
        for l in layouts:
            if _is_chrome_layout(l):
                continue
            ref = l.get("patternRef")
            rid = ref.get("id") if isinstance(ref, dict) else None
            if rid:
                if rid not in pattern_ids:
                    rep.error("C5", f"layout '{l.get('id')}' patternRef.id '{rid}' "
                                    f"not found in {lib_path.name}.")
            elif not l.get("noPatternReason"):
                refless.append(str(l.get("id")))
        if refless:
            rep.error("C5", "layout(s) without patternRef or noPatternReason: "
                            f"{', '.join(refless)} — every observed section becomes "
                            "a library pattern (or documents why not).")
        referenced = {(l.get("patternRef") or {}).get("id")
                      for l in layouts if isinstance(l.get("patternRef"), dict)}
        orphans = [str(p.get("id")) for p in patterns
                   if p.get("id") not in referenced]
        if orphans:
            rep.warn("C5", f"pattern(s) not referenced by any layout: "
                           f"{', '.join(orphans)} — they will not render in the "
                           "components preview.")
        dom_mine = brand_dir / "evidence" / "dom-sections.json"
        if dom_mine.is_file():
            try:
                observed = len((json.loads(dom_mine.read_text()) or {}).get("sections") or [])
                non_chrome = len([l for l in layouts if not _is_chrome_layout(l)])
                if observed > non_chrome * 2:
                    rep.warn("C5", f"dom-mine observed ~{observed} module sections "
                                   f"but only {non_chrome} non-chrome layouts were "
                                   "authored — check extraction breadth.")
            except Exception:
                pass

    # C6 — logo evidence when a logo wall exists
    if _mentions_logos(doc, patterns):
        # recursive: the composer inventories assets/ recursively (AS-34), so
        # logo vectors under assets/logos/ count as evidence too
        assets_dir = brand_dir / "assets"
        logo_files = [p.name for p in assets_dir.rglob("*")
                      if p.suffix.lower() in IMAGE_EXTS
                      and "logo" in p.name.lower()] if assets_dir.is_dir() else []
        tagged = []
        tagged_path = brand_dir / "assets-tagged.json"
        if tagged_path.is_file():
            try:
                tagged = [a.get("filename") for a in
                          (json.loads(tagged_path.read_text()).get("assets") or [])
                          if str(a.get("useCase") or "") == "logo-wall-logo"]
            except Exception:
                pass
        n = max(len(logo_files), len(tagged))
        if n < min_logo_assets:
            rep.error("C6", f"logos use-case declared but only {n} logo asset(s) on "
                            f"disk (need >= {min_logo_assets}). Logo walls render "
                            "from REAL vectors — extract them (curate_assets "
                            "inline-SVG pass) and tag them logo-wall-logo.")

    # C7 — chrome content + presentation evidence
    def _check_content_max(owner: str, measured: dict) -> None:
        raw = measured.get("contentMaxWidth")
        if raw in (None, "", 0):
            return                       # unmeasured (e.g. %-based container) — allowed
        try:
            px = float(raw)
        except (TypeError, ValueError):
            rep.error("C7", f"{owner}.measured.contentMaxWidth is not numeric: {raw!r}")
            return
        lo, hi = CONTENT_MAX_WIDTH_RANGE
        if not (lo <= px <= hi):
            rep.error("C7", f"{owner}.measured.contentMaxWidth={px:g}px outside "
                            f"[{lo}, {hi}] — a value in this range is a % / viewport "
                            "artifact or a mis-measure, not a content column.")

    nav = doc.get("navbar") if isinstance(doc.get("navbar"), dict) else {}
    if not nav:
        rep.error("C7", "brand.yaml navbar: missing — measure_computed chrome facts "
                        "+ the navbar grounding YAML are the evidence sources.")
    else:
        if not (nav.get("primary") or nav.get("links")):
            rep.error("C7", "navbar: no primary/links — nav renders wordmark-only.")
        if not ((nav.get("surface") or {}).get("bg")):
            rep.error("C7", "navbar.surface.bg missing — the chrome bar color must "
                            "be measured, not defaulted.")
        has_presentation = isinstance(nav.get("presentation"), dict)
        measured = nav.get("measured") if isinstance(nav.get("measured"), dict) else {}
        if not has_presentation and not measured.get("link"):
            rep.error("C7", "navbar: no presentation evidence (neither "
                            "`presentation:` nor `measured.link` facts) — casing/"
                            "separators/CTA treatment must come from the source "
                            "(grounding `chrome` block + computed styles), or the "
                            "renderer's habits leak in.")
        _check_content_max("navbar", measured)
        # renderable nav logo (sysfix 2026-07): a declared logo dict must resolve to
        # something the chrome renderer can draw — an image src, inline svg (kind/
        # markup/contract pointer), or the wordmark text device as a last resort.
        logo = nav.get("logo")
        if isinstance(logo, dict):
            renderable = (logo.get("src") or logo.get("svg")
                          or str(logo.get("kind") or "").lower() == "svg"
                          or logo.get("srcContract") or logo.get("text"))
            if not renderable:
                rep.error("C7", "navbar.logo declared but not renderable — carry "
                                "`src` (on-disk asset), `kind: svg` + markup/"
                                "srcContract pointer, or drop the dict so the "
                                "wordmark text device renders.")
        # mega-menu integrity (sysfix 2026-07): a column heading that PREFIXES its
        # first link's label is the label-concatenation capture bug (heading text
        # swallowed into the link), not real information architecture.
        for item in (nav.get("primary") or []):
            if not isinstance(item, dict):
                continue
            menu = item.get("menu") if isinstance(item.get("menu"), dict) else {}
            for col in (menu.get("columns") or []):
                if not isinstance(col, dict):
                    continue
                heading = str(col.get("heading") or "").strip()
                links = [l for l in (col.get("links") or []) if isinstance(l, dict)]
                first = str((links[0].get("label") if links else "") or "").strip()
                if heading and first and len(heading) > 3 \
                        and first.lower().startswith(heading.lower()) \
                        and first.lower() != heading.lower():
                    rep.error("C7", f"navbar mega-menu '{item.get('label')}' column "
                                    f"heading {heading!r} is a prefix of its first "
                                    f"link {first!r} — heading text was concatenated "
                                    "into the link label at capture; re-extract the "
                                    "menu with heading/link separation.")
    foot = doc.get("footer") if isinstance(doc.get("footer"), dict) else {}
    if not foot:
        rep.error("C7", "brand.yaml footer: missing.")
    else:
        if not (foot.get("columns") or foot.get("links") or foot.get("sitemap")):
            rep.error("C7", "footer: no columns/links extracted.")
        legal = foot.get("legal") if isinstance(foot.get("legal"), dict) else {}
        if legal:
            if legal.get("copyright") and not legal.get("text"):
                rep.error("C7", "footer.legal uses `copyright:` but the composers "
                                "read `legal.text` (component_render.footer_content) "
                                "— rename the key or the legal line silently "
                                "disappears.")
        else:
            rep.warn("C7", "footer.legal missing — confirm the source footer truly "
                           "carries no legal line.")
        socials = foot.get("social") or []
        bad_social = [s for s in socials
                      if not (isinstance(s, dict) and s.get("network") and s.get("href"))]
        if bad_social:
            rep.error("C7", "footer.social entries need {network, href} shapes "
                            f"({len(bad_social)} malformed).")
        f_measured = foot.get("measured") if isinstance(foot.get("measured"), dict) else {}
        _check_content_max("footer", f_measured)
        # grid-grammar footers need HEADED columns (sysfix 2026-07): a columns
        # footer whose headings were all lost renders as an anonymous link soup.
        grammar_grid = (
            str(foot.get("archetype") or "").lower() == "grid"
            or str((foot.get("rules") or {}).get("layout") or "").lower() == "grid"
            or bool((foot.get("rules") or {}).get("hasColumnHeadings")))
        columns = [c for c in (foot.get("columns") or []) if isinstance(c, dict)]
        if grammar_grid and columns \
                and not any(str(c.get("heading") or "").strip() for c in columns):
            rep.error("C7", "footer grammar is columns/grid but no column carries a "
                            "heading — headings are part of the measured grammar; "
                            "re-extract them (heading-in-link DOM nesting is the "
                            "usual cause).")
        # footer logo must be the BRAND mark, not a store/review badge asset
        f_logo = foot.get("logo")
        if isinstance(f_logo, dict):
            probe = " ".join(str(f_logo.get(k) or "") for k in ("src", "alt", "href"))
            if APP_BADGE_PATTERN.search(probe):
                rep.error("C7", f"footer.logo looks like a store/review badge asset "
                                f"({probe.strip()!r}) — the footer logo slot carries "
                                "the brand's own mark; badges belong to content "
                                "sections/asset tags.")

    # C8 — assets-tagged manifest matches disk
    tagged_path = brand_dir / "assets-tagged.json"
    if not tagged_path.is_file():
        rep.warn("C8", f"{tagged_path.name} missing — author it from "
                       "assets-manifest.json (curate stage output).")
    else:
        try:
            tagged_doc = json.loads(tagged_path.read_text())
            entries = tagged_doc.get("assets")
            if not isinstance(entries, list):
                rep.warn("C8", f"{tagged_path.name}: no `assets:` list — "
                               "unrecognized manifest shape, files not checked.")
            else:
                assets_dir = brand_dir / "assets"
                on_disk = {p.name for p in assets_dir.rglob("*")
                           if p.is_file()} if assets_dir.is_dir() else set()

                def _exists(name: str) -> bool:
                    return (assets_dir / name).is_file() or Path(name).name in on_disk

                missing = [str(a.get("filename")) for a in entries
                           if isinstance(a, dict) and a.get("filename")
                           and not _exists(str(a["filename"]))]
                if missing:
                    rep.error("C8", f"{len(missing)} tagged asset(s) not on disk "
                                    f"under assets/: {', '.join(missing[:8])}"
                                    f"{' …' if len(missing) > 8 else ''} — a filename "
                                    "in a manifest is not evidence, the file is.")
        except Exception as exc:
            rep.error("C8", f"{tagged_path.name} does not parse as JSON: {exc}")

    # C9 — vision grounding evidence exists
    grounding = sorted((brand_dir / "evidence" / "grounding").glob("*.yaml"))
    if not grounding:
        msg = ("no vision grounding evidence (evidence/grounding/*.yaml) — run "
               "slice_sections + ground_sections_vision; DOM/CSS mining alone "
               "misses creative direction, card anatomy and copy hierarchy.")
        if allow_no_vision:
            rep.warn("C9", msg)
        else:
            rep.error("C9", msg + " (--allow-no-vision downgrades this to a warning)")

    # C10 — card variant coverage (sysfix 2026-07): one measured card is a claim
    # about the WHOLE site's card grammar; enumerate the observed variants or
    # confirm the single variant explicitly after re-checking the grounding.
    card = blocks.get("card")
    if isinstance(card, dict) and not card.get("notObserved") \
            and str(card.get("use") or "").lower() != "never":
        variants = card.get("variants")
        has_variants = isinstance(variants, list) and len(variants) >= 1
        if not has_variants and card.get("singleVariantConfirmed") is not True:
            rep.error("C10", "blocks.card: usable card evidence without variant "
                             "coverage — enumerate the observed `variants:` (e.g. "
                             "media-well vs text-only) or set "
                             "`singleVariantConfirmed: true` after re-checking the "
                             "grounding crops.")

    # C11 — composed-demo smoke (sysfix 2026-07): compose every referenced pattern
    # through the REAL preview harness; structural render bugs (srcless placeholder
    # plates, empty module captions over authored items, dropped alignment) fail
    # here instead of surfacing as visual regressions.
    if smoke:
        _smoke_compose(rep, brand_dir, doc, patterns)

    # C12 — escape hygiene in generated artifacts already living in the brand dir
    for gen in ("components-preview", "chrome"):
        gen_dir = brand_dir / gen
        if not gen_dir.is_dir():
            continue
        for f in sorted(gen_dir.rglob("*.html")):
            hits = DOUBLE_ESCAPED_ENTITY.findall(f.read_text(errors="replace"))
            if hits:
                rep.error("C12", f"{f.relative_to(brand_dir)}: double-escaped "
                                 f"entity text {sorted(set(hits))} — an entity was "
                                 "escaped again (author literal characters, e.g. "
                                 "'—', not '&mdash;', in copy fed to renderers).")

    # C13 — motion evidence: the brand's timing system is part of the extraction
    # contract (the motion-audit gap). tokens.motion must carry at least one
    # evidenced duration AND one easing (envelope shape is free — the check scans
    # the serialized subtree), or declare notObserved with a reason. Evidenced
    # interactive blocks owe their own timing fact.
    motion = (doc.get("tokens") or {}).get("motion") if isinstance(doc.get("tokens"), dict) else None
    if not isinstance(motion, dict) or not motion:
        rep.error("C13", "tokens.motion missing — author the duration ladder / "
                         "easings / signature moves from evidence/motion-audit.json "
                         "(mine_motion.py stage), or record "
                         "`tokens.motion: {notObserved: true, reason: …}` when the "
                         "source genuinely declares no motion.")
    elif motion.get("notObserved"):
        if not str(motion.get("reason") or "").strip():
            rep.error("C13", "tokens.motion.notObserved requires a `reason` naming "
                             "where you looked (motion-audit.json empty? capture "
                             "static-only?).")
    else:
        blob = json.dumps(motion)
        if not TIME_LITERAL.search(blob):
            rep.error("C13", "tokens.motion carries no duration value (e.g. "
                             "'200ms') — derive the ladder from motion-audit.json "
                             "durationCensus.")
        if not EASING_LITERAL.search(blob):
            rep.error("C13", "tokens.motion carries no easing (keyword or "
                             "cubic-bezier) — derive from motion-audit.json "
                             "easingCensus.")
    for btype in INTERACTIVE_BLOCK_TYPES:
        blk = blocks.get(btype)
        if not isinstance(blk, dict) or blk.get("notObserved") \
                or str(blk.get("use") or "").lower() == "never":
            continue
        blob = json.dumps(blk)
        has_timing = bool(TIME_LITERAL.search(blob))
        motion_note = blk.get("motion")
        motion_declared_absent = isinstance(motion_note, dict) and motion_note.get("notObserved")
        if not has_timing and not motion_declared_absent:
            rep.error("C13", f"blocks.{btype}: evidenced interactive block without "
                             "a timing fact — name its observed duration/easing "
                             "(motion-audit.json per-selector table) or record "
                             "`motion: {notObserved: true, reason: …}`.")

    # C14 — canonical-tier discipline (P1.1): a sized type role is a claim about ONE
    # breakpoint unless it carries its measured ladder. The brand must say which
    # measured tier its canonical values refer to (meta.canonicalTier) and every
    # sized role must ship >= 2 ladder stops or confirm single-tier explicitly.
    tokens = doc.get("tokens") if isinstance(doc.get("tokens"), dict) else {}
    sized_roles = _sized_type_roles(tokens)
    if sized_roles:
        meta = doc.get("meta") if isinstance(doc.get("meta"), dict) else {}
        canon = meta.get("canonicalTier")
        if not isinstance(canon, dict) or not canon.get("viewport"):
            rep.error("C14", "meta.canonicalTier missing — the brand must declare "
                             "which measured breakpoint its canonical values refer "
                             "to (e.g. {viewport: 1440, note: …}); the measure "
                             "stage's tier ladder (computed-styles.json `tiers`) "
                             "is the evidence source.")
        undersized = []
        for role, node in sized_roles:
            size = node.get("sizeRem")
            n_stops = len([v for v in size.values() if v is not None]) \
                if isinstance(size, dict) else 1
            if n_stops >= 2:
                continue
            if node.get("singleTierConfirmed") is True:
                continue
            undersized.append(role)
        if undersized:
            rep.error("C14", f"tokens.type role(s) with a single-breakpoint size and "
                             f"no confirmation: {', '.join(undersized)} — author the "
                             "measured per-tier ladder (sizeRem base/tablet/mobileL/"
                             "mobile from the measure stage's tier samples) or set "
                             "`singleTierConfirmed: true` after verifying the size "
                             "holds across the measured tiers.")

    # C15 — relational spacing ladder (P1.1): the gaps BETWEEN content roles are
    # brand rhythm (eyebrow-to-heading, heading-to-body, body-to-cta, …) and must be
    # authored as named relational tokens, or their absence declared with a reason.
    spacing = tokens.get("spacing") if isinstance(tokens.get("spacing"), dict) else {}
    if spacing:
        marker = spacing.get("relationalLadder")
        declared_absent = isinstance(marker, dict) and marker.get("notObserved")
        rungs = [k for k, v in spacing.items()
                 if RELATIONAL_KEY.match(str(k))
                 and isinstance(v, dict) and v.get("value")]
        if declared_absent:
            if not str(marker.get("reason") or "").strip():
                rep.error("C15", "tokens.spacing.relationalLadder.notObserved "
                                 "requires a `reason` naming where you looked "
                                 "(measured margins? spacing custom-property "
                                 "ladders?).")
        elif len(rungs) < 2:
            have = f" (found only: {', '.join(rungs)})" if rungs else ""
            rep.error("C15", "tokens.spacing: no relational spacing ladder — author "
                             "the observed `<role>-to-<role>` rungs (eyebrow-to-"
                             "heading, heading-to-body, body-to-cta, …) as named "
                             f"tokens with measured values{have}, or record "
                             "`relationalLadder: {notObserved: true, reason: …}`.")

    # C16 — chrome DEPTH facts (fid4 2026-07): mega-menu structure + motion, footer
    # column→group hierarchy, bottom-bar structure, and social icon ARTWORK. Every
    # requirement here triggers off the brand's OWN captured evidence (observed but
    # incomplete ⇒ error); a brand whose chrome genuinely lacks the pattern owes
    # nothing. Brand-agnostic: shapes and asset bindings only, never content.
    def _asset_on_disk(ref) -> bool:
        return isinstance(ref, str) and bool(ref.strip()) \
            and (brand_dir / ref.strip()).is_file()

    menus = [(str(item.get("label") or "?"), item["menu"])
             for item in (nav.get("primary") or []) if isinstance(item, dict)
             and isinstance(item.get("menu"), dict)]
    for label, menu in menus:
        cols = [c for c in (menu.get("columns") or []) if isinstance(c, dict)]
        if not cols and not isinstance(menu.get("card"), dict):
            rep.error("C16", f"navbar mega-menu '{label}' carries neither columns "
                             "nor a panel card — an empty menu dict is a capture "
                             "failure; re-extract or drop the key.")
        for col in cols:
            links = [l for l in (col.get("links") or []) if isinstance(l, dict)]
            if not links:
                rep.error("C16", f"navbar mega-menu '{label}' column "
                                 f"{str(col.get('heading') or '?')!r} has no links — "
                                 "column groups are heading+links units.")
            for l in links:
                ic = l.get("icon") if isinstance(l.get("icon"), dict) else None
                if ic and ic.get("asset") and not _asset_on_disk(ic["asset"]):
                    rep.error("C16", f"mega-menu '{label}' link "
                                     f"{str(l.get('label') or '?')!r} icon asset "
                                     f"{ic['asset']!r} not on disk under {brand_dir.name}/ "
                                     "— materialize harvested icons before binding.")
        card = menu.get("card") if isinstance(menu.get("card"), dict) else None
        if card:
            if not str(card.get("title") or "").strip():
                rep.error("C16", f"navbar mega-menu '{label}' panel card has no title "
                                 "— the right-side object is a content card; capture "
                                 "its heading text or drop the fact.")
            img = card.get("image") if isinstance(card.get("image"), dict) else None
            if img and img.get("asset") and not _asset_on_disk(img["asset"]):
                rep.error("C16", f"navbar mega-menu '{label}' card image asset "
                                 f"{img['asset']!r} not on disk — materialize it.")
    if menus:
        mega = (nav.get("measured") or {}).get("megaPanel") \
            if isinstance(nav.get("measured"), dict) else None
        if not isinstance(mega, dict):
            rep.error("C16", "navbar carries mega-menus but no measured.megaPanel "
                             "facts (surface/link/groupTitle/motion) — the open-panel "
                             "presentation must be measured, not defaulted.")
        else:
            motion_blob = json.dumps(mega.get("motion") or {})
            if not TIME_LITERAL.search(motion_blob):
                rep.error("C16", "navbar.measured.megaPanel.motion carries no time "
                                 "literal — panel open/close + link hover timing is "
                                 "part of the captured chrome (mine the transition "
                                 "facts from computed styles).")
        for mo in (nav.get("megaOpen") or []):
            if not isinstance(mo, dict) or not mo.get("open"):
                continue
            panel = mo.get("panel") if isinstance(mo.get("panel"), dict) else {}
            if not (panel.get("w") and panel.get("h")):
                rep.error("C16", f"navbar.megaOpen '{mo.get('label')}' measured no "
                                 "panel box (w/h) — the OPEN-state geometry pass "
                                 "must record the real panel rect.")
    elif isinstance(nav.get("megaOpen"), list) and nav.get("megaOpen"):
        rep.error("C16", "navbar.megaOpen open-state measurements exist but no "
                         "primary link carries a `menu` — structure and measurement "
                         "must describe the same chrome; re-run the bridge.")

    if foot:
        socials = [s for s in (foot.get("social") or []) if isinstance(s, dict)]
        icon_socials = [s for s in socials
                        if str(s.get("kind") or "").lower() == "icon"]
        for s in icon_socials:
            ic = s.get("icon") if isinstance(s.get("icon"), dict) else None
            src = (ic or {}).get("asset") or (ic or {}).get("src") or (ic or {}).get("svg")
            if not src:
                rep.error("C16", f"footer.social '{s.get('network')}' was captured as "
                                 "kind: icon but binds no artwork (icon.asset/src/svg) "
                                 "— harvest the glyph from the DOM (SVG/mask/img) or "
                                 "the renderer degrades to a text link.")
            elif (ic or {}).get("asset") and not _asset_on_disk(ic["asset"]):
                rep.error("C16", f"footer.social '{s.get('network')}' icon asset "
                                 f"{ic['asset']!r} not on disk — materialize it.")
        f_measured = foot.get("measured") if isinstance(foot.get("measured"), dict) else {}
        grid = f_measured.get("grid") if isinstance(f_measured.get("grid"), dict) else None
        f_columns = [c for c in (foot.get("columns") or []) if isinstance(c, dict)]
        headed = any(str(c.get("heading") or "").strip() for c in f_columns)
        if grid and f_columns:
            sizes = [int(s) for s in (grid.get("wrapperSizes") or [])
                     if isinstance(s, (int, float)) and int(s) > 0]
            if sizes and sum(sizes) != len(f_columns):
                rep.error("C16", f"footer.measured.grid.wrapperSizes sums to "
                                 f"{sum(sizes)} but {len(f_columns)} column groups "
                                 "were extracted — the column→group hierarchy and "
                                 "the group list must describe the same footer.")
            if headed and not isinstance(f_measured.get("heading"), dict):
                rep.error("C16", "footer columns carry headings but measured.heading "
                                 "style facts (color/size/weight/casing) are missing "
                                 "— the heading register must be measured, not "
                                 "defaulted to link styling.")
        bb = foot.get("bottomBar")
        if isinstance(bb, dict):
            div = bb.get("divider")
            if not (isinstance(div, dict) and "present" in div):
                rep.error("C16", "footer.bottomBar.divider must record presence "
                                 "({present: bool, color?}) — divider-above-legal is "
                                 "a structural fact renderers consume.")
            bad_pol = [l for l in (bb.get("policyLinks") or [])
                       if not (isinstance(l, dict) and l.get("label") and l.get("href"))]
            if bad_pol:
                rep.error("C16", f"footer.bottomBar.policyLinks: {len(bad_pol)} "
                                 "entr(y/ies) missing {label, href}.")
            for b in (bb.get("storeBadges") or []):
                img = (b.get("img") if isinstance(b, dict) else None) or {}
                if img.get("asset") and not _asset_on_disk(img["asset"]):
                    rep.error("C16", f"footer.bottomBar store badge asset "
                                     f"{img['asset']!r} not on disk — materialize it.")
        elif socials and (foot.get("legal") or {}).get("text"):
            rep.warn("C16", "footer carries social + legal but no bottomBar structure "
                            "facts (divider/rows/policyLinks) — re-extract chrome to "
                            "capture the bottom bar, or the renderer keeps the "
                            "legacy one-row composition.")

    # C17 — disclosure per-item interaction content (fid8 2026-07). A copy entry
    # whose items list carries ANY body is evidence of a disclosure device (an
    # openable item revealing per-item copy) — the states that were closed at
    # static-capture time hide their bodies (and often a per-item media swap), so
    # partial coverage means the interaction pass was skipped, not that the source
    # lacks the content. Brand-agnostic: shapes + asset bindings only.
    if copy_path.is_file():
        try:
            c17_doc = _load_yaml(copy_path)
        except Exception:
            c17_doc = None
        lcopy = (c17_doc or {}).get("layoutCopy")
        for lid, entry in (lcopy.items() if isinstance(lcopy, dict) else []):
            if not isinstance(entry, dict):
                continue
            items = [i for i in (entry.get("items") or []) if isinstance(i, dict)]
            if len(items) < 2:
                continue
            bodied = [i for i in items if str(i.get("body") or "").strip()]
            if bodied and len(bodied) < len(items) \
                    and not entry.get("itemBodiesNotObserved"):
                missing = [str(i.get("heading") or i.get("label") or "?")
                           for i in items
                           if not str(i.get("body") or "").strip()
                           and not i.get("bodyNotObserved")]
                if missing:
                    rep.error("C17", f"layoutCopy.{lid}: disclosure items missing "
                                     f"body copy: {', '.join(missing)} — a body is "
                                     "what makes an item openable; capture the "
                                     "collapsed states (interaction pass / saved-DOM "
                                     "hidden panels) or mark each `bodyNotObserved: "
                                     "true` (entry-level `itemBodiesNotObserved: "
                                     "true` when the source genuinely shows none).")
            with_media = [i for i in items if str(i.get("media") or "").strip()]
            if with_media and bodied:
                if len(with_media) < len(items) and not entry.get("itemMediaNotObserved"):
                    missing = [str(i.get("heading") or i.get("label") or "?")
                               for i in items
                               if not str(i.get("media") or "").strip()
                               and not i.get("mediaNotObserved")]
                    if missing:
                        rep.error("C17", f"layoutCopy.{lid}: per-item media bound on "
                                         f"{len(with_media)}/{len(items)} items "
                                         f"(missing: {', '.join(missing)}) — the "
                                         "media-swap device pairs each ACTIVE item "
                                         "with its own asset; capture every state or "
                                         "mark `mediaNotObserved: true` per item "
                                         "(entry-level `itemMediaNotObserved: true`).")
                for i in with_media:
                    name = Path(str(i.get("media"))).name
                    hits = list(brand_dir.rglob(name)) if name else []
                    if not hits:
                        rep.error("C17", f"layoutCopy.{lid}: items[].media "
                                         f"{name!r} not found under {brand_dir.name}/ "
                                         "— a non-existent filename renders nothing, "
                                         "silently; materialize the captured asset "
                                         "under assets/.")

    # C15 COMPLETENESS (fid11 2026-07): when the source's OWN mined CSS exposes a
    # relational spacing vocabulary — custom properties pairing two content roles
    # (label/headline/description/button "spacing" ladders) or row-gap / column-gap
    # rhythm vars — the authored ladder must be COMPLETE: every exposed pair rung
    # under its generic canonical name, plus a row-rhythm / column-gutter token.
    # A relationalLadder.notObserved marker alongside exposed pair vars is a
    # contradiction. Var/selector names are provenance only (cite them in role:).
    corpus_rel = str((doc.get("indexes") or {}).get("cssRuleCorpus")
                     or "evidence/css-rules.json")
    corpus_path = (brand_dir / corpus_rel).resolve()
    corpus = None       # stays None when the brand ships no mined corpus (C21 reads it too)
    spacing15 = (doc.get("tokens") or {}).get("spacing")
    spacing15 = spacing15 if isinstance(spacing15, dict) else {}

    def _rung_authored(key: str) -> bool:
        node = spacing15.get(key)
        return bool(node.get("value") if isinstance(node, dict) else node)

    if corpus_path.is_file():
        try:
            corpus = json.loads(corpus_path.read_text())
        except Exception:
            corpus = None
        decls_txt = " ".join(str(r.get("decls") or "")
                             for r in ((corpus or {}).get("rules") or [])
                             if isinstance(r, dict))
        prop_names = set(re.findall(r"--[a-z0-9-]+(?=\s*:)", decls_txt))
        role_of = {w: canon for canon, words in REL_ROLE_WORDS.items() for w in words}
        exposed: dict[str, str] = {}          # canonical rung -> exposing var
        row_vars: list[str] = []
        col_vars: list[str] = []
        for name in sorted(prop_names):
            toks = name.strip("-").split("-")
            if not any(t in ("spacing", "gap", "gutter") for t in toks):
                continue
            roles = {role_of[t] for t in toks if t in role_of}
            if len(roles) == 2:
                pair = tuple(sorted(roles, key=_REL_ROLE_ORDER.index))
                rung = CANONICAL_RUNGS.get(pair)
                if rung:
                    exposed.setdefault(rung, name)
            if "row" in toks and "gap" in toks:
                row_vars.append(name)
            if ("column" in toks and "gap" in toks) or "gutter" in toks:
                col_vars.append(name)
        marker15 = spacing15.get("relationalLadder")
        if exposed and isinstance(marker15, dict) and marker15.get("notObserved"):
            rep.error("C15", "tokens.spacing.relationalLadder.notObserved contradicts "
                             "the mined corpus: the source exposes relational spacing "
                             f"custom properties ({', '.join(sorted(exposed.values()))})"
                             " — author the ladder instead of declaring absence.")
        missing_rungs = [f"{rung} (exposed by {var})"
                         for rung, var in sorted(exposed.items())
                         if not _rung_authored(rung)]
        if missing_rungs:
            rep.error("C15", "relational ladder INCOMPLETE against the source's own "
                             "spacing vocabulary: the mined corpus exposes rungs the "
                             f"brand never authored: {'; '.join(missing_rungs)}. "
                             "Resolve each var through the source's spacing scale at "
                             "the canonical tier and author it as the generic "
                             "tokens.spacing rung (source var names are provenance "
                             "for role:, never token names).")
        if row_vars and not any(_rung_authored(k)
                                for k in ("block-to-block", "grid-gap", "row-gap")):
            rep.error("C15", "the mined corpus exposes row-rhythm custom properties "
                             f"({', '.join(sorted(set(row_vars))[:4])}…) but the brand "
                             "authored no row rung — author block-to-block (content-"
                             "block row rhythm) and/or grid-gap with the measured "
                             "value.")
        if col_vars and not any(_rung_authored(k)
                                for k in ("column-to-column", "grid-gap", "column-gap")):
            rep.error("C15", "the mined corpus exposes column-gutter custom properties "
                             f"({', '.join(sorted(set(col_vars))[:4])}…) but the brand "
                             "authored no column rung — author column-to-column "
                             "(split gutter) and/or grid-gap with the measured value.")

    # C18 — contextual header-alignment grammar (fid11, brand-schema §4.4b): when the
    # observed pattern library corroborates a header-alignment rule in BOTH layout
    # contexts (>= 2 split patterns agreeing and >= 2 standalone stack/grid patterns
    # agreeing, at >= 2/3 majority), the brand must author layoutGrammar.headerContext
    # with matching anchors — the brand-default layer generated sections resolve
    # from (AS-49). Dissenting patterns keep their own explicit facts (which outrank
    # the grammar), so exceptions never block authoring.
    lib_rel = str((doc.get("indexes") or {}).get("layoutLibrary")
                  or "layout-library.yaml")
    lib_path = (brand_dir / lib_rel).resolve()
    lib_pats: list[dict] = []
    lib_doc: dict = {}
    if lib_path.is_file():
        try:
            lib_doc = _load_yaml(lib_path) or {}
        except Exception:
            lib_doc = {}
        lib_pats = [p for p in (lib_doc.get("patterns") or []) if isinstance(p, dict)]

    def _norm_anchor18(v) -> str | None:
        v = str(v or "").strip().lower()
        v = {"center": "centered"}.get(v, v)
        return v if v in ("left", "right", "centered") else None

    split_obs: list[tuple[str, str]] = []
    stack_obs: list[tuple[str, str]] = []
    for p in lib_pats:
        arch = str(p.get("archetypeRef") or p.get("archetype") or "").lower()
        a = _norm_anchor18((((p.get("contentShape") or {}).get("alignment")) or {})
                           .get("value"))
        if not a:
            continue
        if arch == "split":
            split_obs.append((str(p.get("id") or "?"), a))
        elif arch in ("stack", "cards", "grid", "stack-fullbleed"):
            stack_obs.append((str(p.get("id") or "?"), a))

    corroborated: dict[str, tuple[str, int, int]] = {}
    for key, obs in (("splitColumn", split_obs), ("standaloneStack", stack_obs)):
        counts: dict[str, int] = {}
        for _, a in obs:
            counts[a] = counts.get(a, 0) + 1
        if not counts:
            continue
        modal = max(counts, key=lambda k: counts[k])
        n = counts[modal]
        if n >= 2 and n * 3 >= len(obs) * 2:
            corroborated[key] = (modal, n, len(obs))
    if len(corroborated) == 2:
        grammar = (doc.get("layoutGrammar") or {}).get("headerContext") \
            if isinstance(doc.get("layoutGrammar"), dict) else None
        for key, (modal, n, total) in sorted(corroborated.items()):
            node = (grammar or {}).get(key) if isinstance(grammar, dict) else None
            authored = _norm_anchor18(node.get("anchor")) \
                if isinstance(node, dict) else None
            if not authored:
                rep.error("C18", f"header-alignment contexts observed but the grammar "
                                 f"is not authored: {n}/{total} {key} patterns agree "
                                 f"on '{modal}' — author layoutGrammar.headerContext."
                                 f"{key}.anchor (brand-schema §4.4b; the brand-default "
                                 "layer generated sections resolve from, AS-49).")
            elif authored != modal:
                rep.error("C18", f"layoutGrammar.headerContext.{key}.anchor "
                                 f"'{authored}' contradicts the observed majority "
                                 f"({n}/{total} patterns agree on '{modal}') — align "
                                 "the grammar with the evidence or re-measure.")
            else:
                # ADVISORY (fid12): a dissenting explicit pattern fact OUTRANKS the
                # grammar by resolution order, so a mis-extracted fact hides behind
                # AS-49 forever — surface each dissent for human review. Verified
                # exceptions are legitimate (cite the re-measurement in the pattern's
                # changelog); unverified ones are exactly where wrong facts live.
                # A dissent the curator already RULED ON (curation.alignment.resolve:
                # follow-grammar, brand-schema §4.4c) downgrades to an informational
                # note: generation lanes resolve through the ruling, review is done.
                obs = split_obs if key == "splitColumn" else stack_obs
                pat_by_id = {str(p.get("id") or "?"): p for p in lib_pats}
                for pid, a in obs:
                    if a == modal:
                        continue
                    cur = ((pat_by_id.get(pid) or {}).get("curation") or {}) \
                        .get("alignment")
                    if isinstance(cur, dict) \
                            and str(cur.get("resolve")) == "follow-grammar":
                        rep.note("C18", f"pattern '{pid}' explicit alignment '{a}' "
                                        f"dissents from the {key} grammar '{modal}' "
                                        f"({n}/{total}) — dissent curated toward "
                                        "grammar (generation lanes center it; the "
                                        "replica keeps the measured fact).")
                        continue
                    rep.warn("C18", f"pattern '{pid}' explicit alignment '{a}' "
                                    f"dissents from the corroborated {key} "
                                    f"grammar '{modal}' ({n}/{total}) — the fact "
                                    "outranks the grammar (AS-49), so verify it "
                                    "against the source (re-measure) and record "
                                    "the confirmation in the pattern changelog.")

    # C19 — RADIUS FIDELITY against the mined census (fid13): tokens.radius values
    # are brand FACTS. When the source publishes its OWN radius custom properties
    # (var()-backed census entries — the design system's actual ladder), every
    # authored magnitude must ride that resolved ladder; raw literal census entries
    # are the fallback vocabulary only (they include third-party embed noise —
    # a 12px chat widget is not the brand's card radius). A vision-estimated radius
    # outside the ladder (12px cards / 20px panels against 2/4/10/40) is an INVENTED
    # fact — fail loud. 0 (square) and percentage circles are always legitimate;
    # brands with no census skip.
    facts_rel = str((doc.get("indexes") or {}).get("cssFacts")
                    or "evidence/css-facts.json")
    facts_path = (brand_dir / facts_rel).resolve()
    if facts_path.is_file():
        try:
            census = (json.loads(facts_path.read_text()) or {}).get("radiusCensus")
        except Exception:
            census = None
        census = census if isinstance(census, dict) else {}
        # resolve var() refs through the mined rule corpus's definitions (--name: <len>)
        var_defs: dict[str, float] = {}
        if corpus_path.is_file():
            try:
                ctxt = " ".join(str(r.get("decls") or "") for r in
                                (json.loads(corpus_path.read_text()).get("rules") or [])
                                if isinstance(r, dict))
            except Exception:
                ctxt = ""
            for name, num, unit in re.findall(
                    r"(--[a-z0-9-]+)\s*:\s*([\d.]+)(px|rem)", ctxt):
                var_defs.setdefault(name, float(num) * (16.0 if unit == "rem" else 1.0))
        ladder_px: set[float] = set()   # the source's OWN radius tokens, resolved
        literal_px: set[float] = set()  # raw literals (embeds included — weak signal)
        for key in census:
            vars_in_key = re.findall(r"--[a-z0-9-]+", key)
            for var in vars_in_key:
                if var in var_defs:
                    ladder_px.add(var_defs[var])
            if not vars_in_key:
                for num, unit in re.findall(r"(?<![\w-])([\d.]+)(px|rem)", key):
                    literal_px.add(float(num) * (16.0 if unit == "rem" else 1.0))
        vocab_px = ladder_px or literal_px
        vocab_kind = "published radius ladder" if ladder_px else "literal radius census"
        if vocab_px:
            radius_tokens = (doc.get("tokens") or {}).get("radius")
            radius_tokens = radius_tokens if isinstance(radius_tokens, dict) else {}
            for tname, node in sorted(radius_tokens.items()):
                raw = node.get("value") if isinstance(node, dict) else node
                m = re.fullmatch(r"([\d.]+)(px|rem)", str(raw or "").strip())
                if not m:
                    continue        # 0, percentages, keywords — always legitimate
                px = float(m.group(1)) * (16.0 if m.group(2) == "rem" else 1.0)
                if px == 0:
                    continue
                if not any(abs(px - v) <= 1.0 for v in vocab_px):
                    near = ", ".join(f"{v:g}px" for v in sorted(vocab_px)[:6])
                    rep.error("C19", f"tokens.radius.{tname} = {raw} ({px:g}px) is "
                                     f"not in the source's {vocab_kind} ({near}) — "
                                     "an authored radius is a FACT; re-measure "
                                     "(JS-off computed) or map it to the source's "
                                     "own ladder instead of a vision estimate.")

    # C20 — GRID EQUALIZATION facts (fid14, brand-schema §4.4d, AS-50): every observed
    # card-grid pattern (grid/cards/mosaic archetypes) must record whether the source
    # equalizes card heights per row — contentShape.gridEqualize with heights
    # stretch|hug plus the companion anatomy (slack slot, actionPinned) — or explicitly
    # mark it unobservable (contentShape.gridEqualizeNotObserved: true). Library
    # patterns ARE observations: while the capture exists the row-height measurement
    # is always available, so a missing stance is an extraction gap — fail loud
    # (same contract weight as the alignment/columns facts these grids already carry).
    for p in lib_pats:
        arch = str(p.get("archetypeRef") or p.get("archetype") or "").lower()
        if arch not in ("grid", "cards", "mosaic"):
            continue
        pid = str(p.get("id") or "?")
        shape = p.get("contentShape") if isinstance(p.get("contentShape"), dict) else {}
        if shape.get("gridEqualizeNotObserved") is True:
            continue
        g = shape.get("gridEqualize")
        heights = str((g or {}).get("heights") if isinstance(g, dict) else "").lower()
        if heights not in ("stretch", "hug"):
            rep.error("C20", f"card-grid pattern '{pid}' records no grid-equalization "
                             "stance — measure the source's card row (JS-off @1440: "
                             "equal heights with differing content = stretch; "
                             "content-sized = hug) and author contentShape."
                             "gridEqualize { heights, slack, actionPinned } "
                             "(brand-schema §4.4d), or mark contentShape."
                             "gridEqualizeNotObserved: true if the capture cannot "
                             "show it (AS-50).")

    # C21 — bar-level AFFORDANCES (fid15 2026-07, C16's sibling): the nav bar's own
    # small devices — dropdown-trigger chevrons, in-bar utility controls (icon
    # links / icon dropdowns), and the utility banner's cta/close anatomy. Each
    # requirement triggers off DOM-DETECTABLE evidence (the mined css corpus names
    # the affordance, or the brand's own captured facts imply it); genuinely absent
    # affordances owe an explicit notObserved marker, never silence. Brand-agnostic:
    # shapes, asset bindings, and web-platform semantics only.
    def _corpus_selector_has(*token_sets: tuple[str, ...]) -> bool:
        """True when any corpus rule's selector carries one token from EVERY set
        (case-insensitive) — the source stylesheet observably names the device."""
        if not isinstance(corpus, dict):
            return False
        for r in corpus.get("rules") or []:
            sel = str((r or {}).get("selector") or "").lower()
            if sel and all(any(t in sel for t in ts) for ts in token_sets):
                return True
        return False

    m_trigger = (nav.get("measured") or {}).get("trigger") \
        if isinstance(nav.get("measured"), dict) else None
    m_chev = (m_trigger or {}).get("chevron") if isinstance(m_trigger, dict) else None
    corpus_nav_chevron = _corpus_selector_has(
        ("nav", "header", "menu"), ("chevron", "caret"))
    if menus and corpus_nav_chevron and not isinstance(m_chev, dict) \
            and not (m_trigger or {}).get("chevronNotObserved"):
        rep.error("C21", "the source's stylesheet names a nav trigger chevron/caret "
                         "but navbar.measured.trigger.chevron carries no facts — "
                         "harvest the glyph (artwork + box + gap + open transform/"
                         "motion) or mark measured.trigger.chevronNotObserved: true.")
    if isinstance(m_chev, dict):
        box = m_chev.get("box") if isinstance(m_chev.get("box"), dict) else {}
        if not (box.get("w") and box.get("h")):
            rep.error("C21", "navbar.measured.trigger.chevron has no measured box "
                             "(w/h) — the glyph's geometry is part of the fact.")
        if m_chev.get("asset") and not _asset_on_disk(m_chev["asset"]):
            rep.error("C21", f"trigger chevron asset {m_chev['asset']!r} not on disk "
                             f"under {brand_dir.name}/ — materialize the harvested "
                             "artwork before binding.")
        if not (m_chev.get("openTransform") or m_chev.get("transition")):
            rep.warn("C21", "trigger chevron carries neither an open-state transform "
                            "nor a transition — the open/close motion is part of the "
                            "affordance; measure it (flip the trigger's expanded "
                            "state) when the source animates it.")

    utility = [u for u in (nav.get("utility") or []) if isinstance(u, dict)]
    for u in utility:
        ulabel = str(u.get("label") or u.get("role") or "?")
        ic = u.get("icon") if isinstance(u.get("icon"), dict) else None
        if ic and ic.get("asset") and not _asset_on_disk(ic["asset"]):
            rep.error("C21", f"utility control {ulabel!r} icon asset "
                             f"{ic['asset']!r} not on disk — materialize harvested "
                             "glyphs; a missing file renders nothing, silently.")
        ch = u.get("chevron") if isinstance(u.get("chevron"), dict) else None
        if ch and ch.get("asset") and not _asset_on_disk(ch["asset"]):
            rep.error("C21", f"utility control {ulabel!r} chevron asset "
                             f"{ch['asset']!r} not on disk — materialize it.")
        if str(u.get("kind") or "") == "dropdown" and not u.get("dropdownNotObserved"):
            dd = u.get("dropdown") if isinstance(u.get("dropdown"), dict) else None
            items = [i for i in ((dd or {}).get("items") or []) if isinstance(i, dict)
                     and str(i.get("label") or "").strip()]
            if not items:
                rep.error("C21", f"utility dropdown {ulabel!r} carries no menu items "
                                 "— the open-state panel must be captured live "
                                 "(panels portal on open; a saved snapshot cannot "
                                 "show them) or marked dropdownNotObserved: true.")
            panel = (dd or {}).get("panel") if isinstance((dd or {}).get("panel"), dict) else {}
            if items and not (panel.get("w") and panel.get("h") and panel.get("bg")):
                rep.error("C21", f"utility dropdown {ulabel!r} items exist but the "
                                 "panel presentation (w/h/bg) was not measured — "
                                 "the open state carries both structure and paint.")

    # a control FLATTENED into the primary tier: a primary entry that is neither a
    # navigation destination (real href) nor a mega-menu tab is a bar control that
    # missed utility classification (the exact regression this contract guards).
    for p in (nav.get("primary") or []):
        if not isinstance(p, dict) or isinstance(p.get("menu"), dict):
            continue
        href = str(p.get("href") or "").strip()
        if href in ("", "#") and not p.get("utilityNotObserved"):
            rep.error("C21", f"navbar.primary entry {str(p.get('label') or '?')!r} "
                             "has no destination href and no menu — an in-bar "
                             "CONTROL flattened into the nav-destination tier; "
                             "classify it under navbar.utility (kind/role/glyph/"
                             "dropdown anatomy) or mark utilityNotObserved: true.")

    # the corpus observably names an in-bar language/locale switcher: the bar owes a
    # dropdown-kind utility control (or the explicit marker on the navbar).
    if _corpus_selector_has(("nav", "header"), ("languageswitcher", "language-switcher",
                                                "localeswitcher", "locale-switcher")) \
            and not any(str(u.get("kind") or "") == "dropdown" for u in utility) \
            and not nav.get("utilityNotObserved"):
        rep.error("C21", "the source's stylesheet names an in-bar language/locale "
                         "switcher but navbar.utility carries no dropdown-kind "
                         "control — capture it (glyph, collapsed presentation, "
                         "locale items, panel) or mark navbar.utilityNotObserved: "
                         "true.")

    ub = nav.get("utilityBanner") if isinstance(nav.get("utilityBanner"), dict) else None
    if ub and ub.get("observed") and str(ub.get("text") or "").strip():
        cta = ub.get("cta") if isinstance(ub.get("cta"), dict) else None
        if cta:
            if not (str(cta.get("label") or "").strip() and str(cta.get("href") or "").strip()):
                rep.error("C21", "utilityBanner.cta needs label + href — a banner "
                                 "action without a destination is a capture gap.")
            arrow = cta.get("arrow") if isinstance(cta.get("arrow"), dict) else None
            if arrow and arrow.get("asset") and not _asset_on_disk(arrow["asset"]):
                rep.error("C21", f"utilityBanner cta arrow asset {arrow['asset']!r} "
                                 "not on disk — materialize it.")
        elif not ub.get("ctaNotObserved"):
            rep.error("C21", "utilityBanner is observed but carries no cta anatomy "
                             "— capture the banner's action link (label/href/"
                             "underline/weight) or mark ctaNotObserved: true when "
                             "the source banner genuinely shows none.")
        close = ub.get("close") if isinstance(ub.get("close"), dict) else None
        if close:
            cbox = close.get("box") if isinstance(close.get("box"), dict) else {}
            if not (cbox.get("w") and cbox.get("h")):
                rep.error("C21", "utilityBanner.close carries no measured box (w/h) "
                                 "— the dismiss affordance's geometry is part of "
                                 "the anatomy.")
            if close.get("asset") and not _asset_on_disk(close["asset"]):
                rep.error("C21", f"utilityBanner close asset {close['asset']!r} not "
                                 "on disk — materialize it.")
        elif ub.get("dismissible") and not ub.get("closeNotObserved"):
            rep.error("C21", "utilityBanner is dismissible but carries no close "
                             "anatomy (glyph kind + box) — capture the close "
                             "affordance or mark closeNotObserved: true.")

    # C22 — TWO-TIER chrome contract (fix1 2026-07, advisory): when the MEASURED
    # chrome shows a real utility tier (utilityBarHeight > 0) the authored contract
    # should declare `navbar.utilityTier` (the renderer's explicit opt-in). Advisory,
    # not error — a brand may legitimately flatten a vestigial tier, but silence
    # usually means the authoring missed the placement facts.
    m_nav = nav.get("measured") if isinstance(nav.get("measured"), dict) else {}
    ut_h = m_nav.get("utilityBarHeight")
    if isinstance(ut_h, (int, float)) and ut_h > 0 \
            and not isinstance(nav.get("utilityTier"), dict):
        rep.warn("C22", f"measured chrome shows a utility tier ({int(ut_h)}px) but "
                        "the authored contract lacks navbar.utilityTier — declare "
                        "the tier (height/bg/fontSize/trailing) so the bar renders "
                        "two-tier, or record why it was flattened.")

    # C23 — COMPONENT-RECIPE coverage (fix2 2026-07, advisory; brand-schema §4.4e):
    # recipes are brand data written DURING extraction. When 2+ project patterns
    # share a rail-like anatomy signature (a *rail treatment kind — the section
    # head-rail device family) they are instantiating ONE recurring component;
    # each should bind a `recipes:` entry via recipeRef {recipe, variant}. Advisory,
    # not error — a brand may carry two genuinely unrelated rails — but silence
    # usually means the recipe layer was skipped. Dangling refs + one-way usedBy
    # bindings are flagged too (both directions of the binding must agree).
    recipes = [r for r in (lib_doc.get("recipes") or []) if isinstance(r, dict)]
    recipe_ids = {str(r.get("id")) for r in recipes if r.get("id")}
    # rail-like = the leader-rule head-rail device family (rule-rail / headrail /
    # leader kinds) — NOT carousel-rail, which is a slide track, not an anatomy.
    _rail_re = re.compile(r"rule-rail|head-?rail|leader")
    railish = [p for p in lib_pats
               if any(_rail_re.search(str(t.get("kind") or "").lower())
                      for t in (p.get("specialTreatments") or [])
                      if isinstance(t, dict))]
    if len(railish) >= 2:
        unbound = [str(p.get("id") or "?") for p in railish
                   if not (isinstance(p.get("recipeRef"), dict)
                           and str(p["recipeRef"].get("recipe") or "") in recipe_ids)]
        if unbound:
            rep.warn("C23", f"{len(railish)} patterns share a rail-like anatomy "
                            f"({', '.join(str(p.get('id')) for p in railish)}) but "
                            f"{', '.join(unbound)} bind(s) no recipes: entry — record "
                            "the shared anatomy as a brand recipe with per-context "
                            "variants (brand-schema §4.4e) and set recipeRef "
                            "{recipe, variant} on each pattern.")
    for p in lib_pats:
        ref = p.get("recipeRef")
        if isinstance(ref, dict) and ref.get("recipe") \
                and str(ref["recipe"]) not in recipe_ids:
            rep.warn("C23", f"pattern '{p.get('id')}' recipeRef names recipe "
                            f"'{ref['recipe']}' which does not exist in "
                            "layout-library.yaml recipes: — dangling binding "
                            "(the composer will degrade to the structural device).")
    pat_ids = {str(p.get("id")) for p in lib_pats if p.get("id")}
    for r in recipes:
        rid = str(r.get("id") or "?")
        if not (r.get("anatomy") or []):
            rep.warn("C23", f"recipe '{rid}' records no anatomy slots — a recipe is "
                            "an ordered anatomy, not just a name.")
        for v in (r.get("variants") or []):
            if isinstance(v, dict) and not v.get("id"):
                rep.warn("C23", f"recipe '{rid}' carries a variant without an id — "
                                "patterns bind variants by id.")
        for uid in (r.get("usedBy") or []):
            if str(uid) not in pat_ids:
                rep.warn("C23", f"recipe '{rid}' usedBy names unknown pattern "
                                f"'{uid}'.")
            else:
                bound = next((p for p in lib_pats if str(p.get("id")) == str(uid)), {})
                ref = bound.get("recipeRef")
                if not (isinstance(ref, dict) and str(ref.get("recipe")) == rid):
                    rep.warn("C23", f"recipe '{rid}' lists pattern '{uid}' in usedBy "
                                    "but that pattern carries no matching recipeRef "
                                    "— bind both directions.")

    _check_style_scale(rep, brand_dir)
    _check_signatures(rep, doc)

    return rep


# C24 — derived-scale artifact (pass1 2026-07, style-scale.v1). The QUANTIZATION
# layer's honesty contract: internal consistency (steps on the base/ratio, section
# rhythm a subset of the steps) and fit honesty (recorded errors back the verdict;
# a poor fit must not claim followsScale). Advisory — the artifact is derived and
# regenerable; a brand without one simply hasn't run the normalizer.
def _check_style_scale(rep: Report, brand_dir: Path) -> None:
    path = brand_dir / "style-scale.yaml"
    if not path.exists():
        rep.note("C24", "style-scale.yaml absent — derived-scale layer not "
                        "generated (tools/extract/normalize_scales.py); generative "
                        "composers keep their fact-only degrades.")
        return
    try:
        art = yaml.safe_load(path.read_text()) or {}
    except Exception as exc:
        rep.warn("C24", f"style-scale.yaml unparsable: {exc}")
        return
    if art.get("schema") != "style-scale.v1":
        rep.warn("C24", f"style-scale.yaml schema '{art.get('schema')}' — expected "
                        "style-scale.v1")
        return

    digest = "sha256:" + hashlib.sha256(
        (brand_dir / "brand.yaml").read_bytes()).hexdigest()[:12]
    if art.get("sourceDigest") and art["sourceDigest"] != digest:
        rep.warn("C24", "style-scale.yaml is STALE — sourceDigest "
                        f"{art.get('sourceDigest')} != current brand.yaml {digest}; "
                        "re-run the normalizer so derived steps track the facts.")

    space = art.get("space") or {}
    unit = space.get("baseUnitPx")
    steps = [float(s) for s in (space.get("stepsPx") or [])]
    if isinstance(unit, (int, float)) and unit > 0:
        off = [s for s in steps if abs(s / unit - round(s / unit)) > 0.02]
        if off:
            rep.warn("C24", f"space steps {off} not multiples of the base unit "
                            f"{unit} — the artifact is internally inconsistent.")
        rhythm = [float(s) for s in (space.get("sectionRhythmPx") or [])]
        stray = [r for r in rhythm if r not in steps]
        if stray:
            rep.warn("C24", f"sectionRhythmPx {stray} not present in stepsPx — "
                            "section rhythm must be a subset of the space steps.")
        cov = ((space.get("fitQuality") or {}).get("coverage"))
        if isinstance(cov, (int, float)) and cov < 0.8 and space.get("followsScale"):
            rep.warn("C24", f"space followsScale claimed at coverage {cov} — a poor "
                            "fit must be recorded honestly (followsScale: false).")

    typ = art.get("type") or {}
    base, ratio = typ.get("basePx"), typ.get("ratio")
    if isinstance(base, (int, float)) and isinstance(ratio, (int, float)) and ratio > 1:
        for s in (typ.get("stepsPx") or []):
            k = round(math.log(float(s) / base, ratio))
            pred = base * ratio ** k
            if abs(pred - float(s)) / float(s) > 0.01:
                rep.warn("C24", f"type step {s}px is not base*ratio^k for base "
                                f"{base} ratio {ratio} — inconsistent step table.")
        fq = typ.get("fitQuality") or {}
        rmse = fq.get("rmse")
        if isinstance(rmse, (int, float)):
            if rmse > 0.05 and typ.get("followsScale"):
                rep.warn("C24", f"type followsScale claimed at rmse {rmse} — a poor "
                                "fit must set followsScale: false, never forced.")
            worst = max((f.get("errPct", 0) for f in (typ.get("fits") or [])),
                        default=0.0)
            claimed = fq.get("worstErrPct")
            if isinstance(claimed, (int, float)) and abs(worst - claimed) > 0.35:
                rep.warn("C24", f"fitQuality.worstErrPct {claimed} does not match "
                                f"the recorded fits (max errPct {worst}) — the "
                                "honesty ledger must agree with itself.")


# C25 — brand signatures (pass1 2026-07, brand-schema §4.7). The extraction
# doctrine (layout-analyst-skill.md) makes authoring REQUIRED; the validator is
# the enforcement backstop, same as C23 for recipes. Advisory.
_SIGNATURE_KINDS = {"accent-scope", "shape-motif", "type-treatment",
                    "surface-habit", "spacing-habit"}


def _check_signatures(rep: Report, doc: dict) -> None:
    sigs = doc.get("signatures")
    if not sigs:
        rep.warn("C25", "no `signatures:` block — the 3-5 moves that make this "
                        "brand recognizable should be authored from the evidence "
                        "during extraction (brand-schema §4.7; skill doctrine).")
        return
    if not isinstance(sigs, list):
        rep.warn("C25", "`signatures:` must be a LIST of signature entries.")
        return
    if not (3 <= len(sigs) <= 5):
        rep.warn("C25", f"{len(sigs)} signature(s) authored — the discipline is "
                        "3-5, not 20 (and not fewer than 3): signatures are the "
                        "brand's recognizable moves, not a rule dump.")
    for s in sigs:
        if not isinstance(s, dict):
            rep.warn("C25", f"non-mapping signature entry: {s!r}")
            continue
        sid = str(s.get("id") or "?")
        kind = str(s.get("kind") or "")
        if kind not in _SIGNATURE_KINDS:
            rep.warn("C25", f"signature '{sid}' kind '{kind}' is not a known rule "
                            f"kind ({', '.join(sorted(_SIGNATURE_KINDS))}) — the "
                            "signature auditor cannot verify it.")
        if str(s.get("mode") or "") not in ("always", "never"):
            rep.warn("C25", f"signature '{sid}' needs mode: always|never — a "
                            "signature is a machine-checkable rule, not prose.")
        if not isinstance(s.get("check"), dict) or not s["check"]:
            rep.warn("C25", f"signature '{sid}' carries no check params — author "
                            "the machine-checkable form (the claim is the prose "
                            "companion, the check is the rule).")
        if not (s.get("evidence") or []):
            rep.warn("C25", f"signature '{sid}' cites no evidence provenance — "
                            "every signature must name the sections/computed facts "
                            "that license it.")


def _smoke_compose(rep: Report, brand_dir: Path, doc: dict,
                   patterns: list[dict]) -> None:
    """C11 body: hydrate + compose every referenced pattern into a temp dir via the
    preview harness (the same path the components preview uses) and check the
    rendered documents. Import failures fail loud — the smoke check is part of the
    evidence contract, not an optional extra."""
    referenced = [p for p in patterns if isinstance(p, dict) and p.get("id")]
    if not referenced or not (brand_dir / "brand.yaml").is_file():
        return
    bp_dir = REPO_ROOT / "brand_pipeline"
    if str(bp_dir) not in sys.path:
        sys.path.insert(0, str(bp_dir))
    try:
        import compose_from_composition as cfc
        import compose_section as cs
        import render_components_preview as rp
    except Exception as exc:                    # pragma: no cover - env specific
        rep.error("C11", f"composed-demo smoke could not import the harness: {exc} "
                         "(run with --no-smoke to skip deliberately)")
        return

    cdoc = yaml.safe_load((brand_dir / "brand.yaml").read_text()) or {}
    cs.attach_brand_copy(cdoc, brand_dir)
    cs.attach_asset_inventory(cdoc, brand_dir)
    authored_copy = cs.brand_layout_copy(cdoc)

    # alignment stamping (structural): a pattern declaring centered alignment must
    # survive the demo-hydration + adapter path with an anchor on the layout. Only
    # probed for patterns the harness would actually hydrate (same gating as
    # compose_pattern_docs) — plain-composer layouts carry their own alignment.
    hydrate_all = rp._demo_hydration_active(cdoc)
    for pat in referenced:
        align = str((((pat.get("contentShape") or {}).get("alignment") or {})
                     .get("value") or "")).lower()
        if align not in ("center", "centered"):
            continue
        layout = rp.layout_for_pattern(cdoc, pat.get("id"))
        if layout is None:
            continue
        if not (hydrate_all or rp._layout_needs_asset_hydration(cdoc, layout)):
            continue
        try:
            sec = rp._demo_section_for_pattern(cdoc, pat, layout)
            comp = cfc._sanitize_assets({"sections": [sec]}, brand_dir)
            adapted = cfc.composition_to_layout(comp["sections"][0])
        except Exception as exc:
            rep.error("C11", f"pattern '{pat.get('id')}' failed to adapt for the "
                             f"alignment smoke: {exc}")
            continue
        anchor = str(((adapted.get("alignment") or {}).get("anchor") or "")).lower()
        if anchor not in ("center", "centered"):
            rep.error("C11", f"pattern '{pat.get('id')}' declares centered "
                             "alignment but the composed layout carries no anchor "
                             "— the declared alignment was dropped on the way to "
                             "the composer.")

    with tempfile.TemporaryDirectory(prefix="evidence-smoke-") as tmp:
        out_dir = Path(tmp)
        try:
            results = rp.compose_pattern_docs(cdoc, referenced,
                                              brand_dir / "brand.yaml", out_dir)
        except Exception as exc:
            rep.error("C11", f"composed-demo smoke crashed: {exc}")
            return
        for pid, res in sorted(results.items()):
            err = (res or {}).get("error")
            if err:
                rep.error("C11", f"pattern '{pid}' did not compose: {err}")
                continue
            html_path = out_dir / "layouts" / f"{pid}.html"
            if not html_path.is_file():
                rep.error("C11", f"pattern '{pid}' composed but wrote no document.")
                continue
            html = html_path.read_text(errors="replace")
            if 'class="c-image-ph' in html:
                rep.error("C11", f"pattern '{pid}' composes a srcless placeholder "
                                 "plate (c-image-ph markup) — bind a real asset to "
                                 "the media slot or drop the slot.")
            layout = rp.layout_for_pattern(cdoc, pid) or {}
            authored = authored_copy.get(layout.get("id")) or {}
            if isinstance(authored.get("items"), list) and authored["items"]:
                if re.search(r'class="cs-module-title"\s*>\s*<', html):
                    rep.error("C11", f"pattern '{pid}' renders empty module "
                                     "caption(s) while the brand authored items — "
                                     "the item copy is not reaching the modules.")
            # action-pair ORDER (sysfix 2026-07): in a multi-button action row the
            # PRIMARY (plain .c-button) leads; a family-variant button rendering
            # before it is the crossed-family/ordering defect class.
            for row in re.findall(
                    r'class="cs-(?:hero|conversion)-actions"\s*>(.*?)</div>', html,
                    flags=re.DOTALL):
                fams = [m or "primary"
                        for m in re.findall(r'class="c-button(?:\s+c-button--([\w-]+))?"', row)]
                if len(fams) >= 2 and "primary" in fams and fams[0] != "primary":
                    rep.error("C11", f"pattern '{pid}' action row orders a "
                                     f"'{fams[0]}' family button before the primary "
                                     "— the primary action leads unless the "
                                     "evidence declares otherwise.")
            # furniture-less panel scan (sysfix 2026-07): a split shipping a cream
            # panel with no title/rows/foot is the invented-content defect class
            # resurfacing as an EMPTY box — the composer must elide it instead.
            if re.search(r'class="cs-panel"\s*>\s*(?:<div class="c-rows">\s*'
                         r'</div>\s*)?</div>', html):
                rep.error("C11", f"pattern '{pid}' renders an EMPTY panel (no "
                                 "title, rows, or foot) — panel-less splits must "
                                 "elide the panel, not ship an empty surface.")
            hits = DOUBLE_ESCAPED_ENTITY.findall(html)
            if hits:
                rep.error("C12", f"pattern '{pid}' demo contains double-escaped "
                                 f"entity text {sorted(set(hits))}.")


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--brand-dir", type=Path, help="runs/<brand>/brand")
    ap.add_argument("--brand", help="brand name (resolves runs/<brand>/brand)")
    ap.add_argument("--contracts", type=Path, default=None,
                    help=f"blocks contract (default {DEFAULT_CONTRACTS})")
    ap.add_argument("--allow-no-vision", action="store_true",
                    help="downgrade the missing-grounding error to a warning")
    ap.add_argument("--min-logo-assets", type=int, default=3)
    ap.add_argument("--no-smoke", action="store_true",
                    help="skip the C11 composed-demo smoke check")
    ap.add_argument("--report", type=Path, help="write a JSON report here")
    return ap


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    brand_dir = args.brand_dir or (
        REPO_ROOT / "runs" / args.brand / "brand" if args.brand else None)
    if brand_dir is None:
        raise SystemExit("provide --brand-dir or --brand")
    rep = validate_brand_dir(brand_dir, contracts_path=args.contracts,
                             allow_no_vision=args.allow_no_vision,
                             min_logo_assets=args.min_logo_assets,
                             smoke=not args.no_smoke)
    for nmsg in rep.notes:
        print(f"NOTE  {nmsg}")
    for w in rep.warnings:
        print(f"WARN  {w}")
    for e in rep.errors:
        print(f"ERROR {e}")
    verdict = "PASS" if rep.ok else "FAIL"
    print(f"[{verdict}] {brand_dir}: {len(rep.errors)} error(s), "
          f"{len(rep.warnings)} warning(s), {len(rep.notes)} note(s)")
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(
            {"brandDir": str(brand_dir), "ok": rep.ok, "errors": rep.errors,
             "warnings": rep.warnings, "notes": rep.notes}, indent=1))
    return 0 if rep.ok else 1


if __name__ == "__main__":
    sys.exit(main())
