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
        state fact; a single family requires `singleVariantConfirmed: true`
  C4 E  section-copy.yaml present, schema-conformant, wordmark set; every
        content-bearing non-chrome layout has a layoutCopy entry
  C5 E/W layout<->pattern coverage: non-chrome layouts carry patternRef (or
        `noPatternReason`); orphan patterns warn; observed-section breadth warns
  C6 E  logo evidence: a logos use-case requires >= --min-logo-assets on-disk
        logo files (or assets tagged logo-wall-logo)
  C7 E/W chrome: navbar links + surface + presentation/measured facts; footer
        columns/social; `legal.copyright` without `legal.text` is an error
  C8 E/W assets-tagged.json exists; every tagged file exists under assets/
  C9 E  vision evidence: >= 1 evidence/grounding/*.yaml (--allow-no-vision
        downgrades to warning)

Importable API (used by brand_pipeline/tests/test_brand_evidence_contract.py):
    report = validate_brand_dir(brand_dir, contracts_path=..., ...)
    report.errors / report.warnings / report.ok

Usage:
    ./venv/bin/python tools/extract/validate_brand_evidence.py --brand-dir runs/<brand>/brand
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_CONTRACTS = REPO_ROOT / "brand_pipeline" / "contracts" / "blocks.yaml"

ALLOWED_COPY_KEYS = {"sectionCopy", "layoutCopy", "layoutImages", "defaultArt",
                     "wildcardCopy"}
CHROME_LAYOUT_ARCHETYPES = {"nav"}
CHROME_LAYOUT_IDS = {"navbar", "footer"}
IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".svg", ".webp", ".gif")


@dataclass
class Report:
    brand_dir: Path
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def error(self, code: str, msg: str) -> None:
        self.errors.append(f"{code}: {msg}")

    def warn(self, code: str, msg: str) -> None:
        self.warnings.append(f"{code}: {msg}")


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
                       min_logo_assets: int = 3) -> Report:
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

    return rep


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--brand-dir", type=Path, help="runs/<brand>/brand")
    ap.add_argument("--brand", help="brand name (resolves runs/<brand>/brand)")
    ap.add_argument("--contracts", type=Path, default=None,
                    help=f"blocks contract (default {DEFAULT_CONTRACTS})")
    ap.add_argument("--allow-no-vision", action="store_true",
                    help="downgrade the missing-grounding error to a warning")
    ap.add_argument("--min-logo-assets", type=int, default=3)
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
                             min_logo_assets=args.min_logo_assets)
    for w in rep.warnings:
        print(f"WARN  {w}")
    for e in rep.errors:
        print(f"ERROR {e}")
    verdict = "PASS" if rep.ok else "FAIL"
    print(f"[{verdict}] {brand_dir}: {len(rep.errors)} error(s), "
          f"{len(rep.warnings)} warning(s)")
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(
            {"brandDir": str(brand_dir), "ok": rep.ok,
             "errors": rep.errors, "warnings": rep.warnings}, indent=1))
    return 0 if rep.ok else 1


if __name__ == "__main__":
    sys.exit(main())
