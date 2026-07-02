#!/usr/bin/env python3
"""build_showcase.py — WoodWave FULL VARIATION SHOWCASE.

Renders every variation axis the pipeline can currently express for WoodWave, grouped
into a small set of Studio lanes (deterministic axes exhaustively, generative axes
sampled). NOTHING here edits pipeline code, brand.yaml, layout-library.yaml, or
styles/*.md — the harness only USES the existing composers/generators, exactly like
experiments/woodwave-hybrid/run_hybrid.py and
experiments/woodwave-hero-gallery/build_anchored_variants.py (whose conventions it
follows: deterministic pattern→section derivation, quiet caption-scale divider labels,
shim CSS appended post-render, shoot_reveal_safe screenshots, gate-then-ship).

Sub-commands (run independently so a mid-edit pipeline state only costs one phase):
  patterns   — 4 pages: all 14 PROJECT-tier patterns per style (compose_page, real
               voice.md copy) + all 27 STANDARD-tier patterns per style (sections
               derived deterministically from pattern contentShape — the
               original_hero_section convention — brand-authored copy bound
               mechanically; non-drawable archetypes degrade to generic-flow and are
               labeled as such).
  sampler    — archetype × treatment/lever sampler page (editorial-luxury): the
               section-tunable levers that actually exist today (alignment anchor,
               interlock float side, module count, ghost word vs numerals, split
               sub-composers, gallery counter).
  hybrid     — LIVE generate_composition runs: N seeds with offGridExpansion ON
               (editorial-luxury, by style identity) + M with the flag FORCED off as
               contrast. Real LLM pipeline; never hand-authored compositions.
  anchored   — re-stitch + re-gate the anchored hero-variants page (assemble-only).
  lanes      — publish gate-green pages as versioned Studio lanes (symlink dirs +
               label.txt under runs/woodwave/brand/variants/, the existing wiring).
  shots      — screenshot every published lane + verify the Melodrama font markers.
  report     — write REPORT.md from the accumulated results.json.

Usage: ./venv/bin/python experiments/woodwave-showcase/build_showcase.py <cmd> [...]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
BP = REPO / "brand_pipeline"
sys.path.insert(0, str(BP))
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "experiments" / "woodwave-hero-gallery"))

import layout_library as ll                    # noqa: E402
import generate_composition as gc              # noqa: E402
import compose_from_composition as cfc         # noqa: E402
import compose_section as cs                   # noqa: E402

# ── HARNESS-LEVEL translator completion (in-memory only — the gen_arm_a.py /
# render_composition copy-override mechanism; NO pipeline file is edited).
# compose_split dispatches seeded splits by patternRef to compose_about_statement /
# compose_curator_quote / compose_visit_band, whose copy keys ("body", "quote",
# "mapCaption", …) the adapter's _split_copy translator does not emit → KeyError at
# render for every LLM composition that seeds those patterns. The wrapper surfaces
# the section's OWN LLM-authored slot copy (statement text, quote, attribution) and
# aliases already-translated values for the visit-band keys. No invented copy: every
# string comes from the composition's slots or stays empty.
def _install_split_copy_completion(cfc_mod):
    orig = cfc_mod._COPY_TRANSLATORS["split"]

    def _completed(section: dict) -> dict:
        out = orig(section)
        slots = [s for s in (section.get("slots") or []) if isinstance(s, dict)]

        def first(*keys: str) -> str:
            for s in slots:
                c = s.get("copy")
                if isinstance(c, dict):
                    for k in keys:
                        v = c.get(k)
                        if isinstance(v, str) and v.strip():
                            return v
            return ""

        if not out.get("body"):
            out["body"] = first("text", "body") or first("attribution")
        if not out.get("quote"):
            out["quote"] = first("quote") or out.get("heading", "")
        # visit-band aliases (only read when pid == visit-dual-panel-map)
        out.setdefault("mapCaption", out.get("caption", ""))
        out.setdefault("ticketsTitle", out.get("panelTitle", "Details"))
        out.setdefault("ticketsRows", out.get("rows", []))
        out.setdefault("ticketsCta", out.get("cta", ""))
        out.setdefault("visitTitle", out.get("panelTitle", "Details"))
        out.setdefault("visitRows", out.get("rows", []))
        out.setdefault("visitCta", out.get("cta", ""))
        return out

    cfc_mod._COPY_TRANSLATORS["split"] = _completed


_install_split_copy_completion(cfc)

BRAND_YAML = REPO / "runs" / "woodwave" / "brand" / "brand.yaml"
BRAND_DIR = BRAND_YAML.parent
STYLES = ("radical-editorial", "editorial-luxury")
SHOOT = REPO / "experiments" / "woodwave-ab" / "shoot_reveal_safe.mjs"
VARIANTS_DIR = REPO / "runs" / "woodwave" / "brand" / "variants"
PAGES = HERE / "pages"
HYBRID = HERE / "hybrid"
RESULTS = HERE / "results.json"
PY = sys.executable

# ── the deterministic PROJECT-tier order: every project pattern exactly once ──────
# (layout id in brand.yaml, project pattern id, archetype) — 14 patterns / 14 layouts.
PROJECT_ORDER = [
    ("opening-bookend",      "hero-display-over-staggered-media", "stack"),
    ("editorial-collage",    "editorial-ghostword-collage",       "collage"),
    ("mission-statement",    "about-anchored-statement",          "split"),
    ("gallery-showcase",     "gallery-fullbleed-counter-band",    "stack-fullbleed"),
    ("heritage-timeline",    "heritage-ghost-numerals-timeline",  "collage"),
    ("curator-quote",        "curator-quote-portrait-collage",    "split"),
    ("info-band",            "features-flush-split-panel",        "split"),
    ("visit-band",           "visit-dual-panel-map",              "split"),
    ("demo-staggered-cards", "features-staggered-caption-cards",  "cards"),
    ("demo-interlock-inset", "editorial-interlocking-inset",      "interlock"),
    ("exhibition-schedule",  "schedule-ruled-list-panel",         "stack"),
    ("exhibition-tickets",   "pricing-ruled-list-panel",          "stack"),
    ("exhibition-faq",       "faq-accordion-list",                "stack"),
    ("conversion-stack",     "cta-underline-conversion-stack",    "stack"),
]

DRAWABLE = {"stack", "collage", "split", "stack-fullbleed", "cards", "interlock"}
USE_CASE_ORDER = ["hero", "about", "features", "gallery", "testimonial", "pricing",
                  "cta", "footer"]


# ── results accumulator ───────────────────────────────────────────────────────────

def _load_results() -> dict:
    if RESULTS.exists():
        return json.loads(RESULTS.read_text())
    return {}


def _save_results(key: str, value) -> None:
    data = _load_results()
    data[key] = value
    RESULTS.write_text(json.dumps(data, indent=2) + "\n")


# ── shared helpers (screenshot / gate / font markers) ─────────────────────────────

def screenshot(index_html: Path, out_png: Path) -> bool:
    """Full-page shot via the EXISTING shoot_reveal_safe.mjs (same settings as the
    hybrid + anchored harnesses)."""
    if not SHOOT.exists():
        print(f"  screenshot skipped — {SHOOT} not found")
        return False
    env = {k: v for k, v in os.environ.items() if k != "PLAYWRIGHT_BROWSERS_PATH"}
    try:
        proc = subprocess.run(["node", str(SHOOT), str(index_html), str(out_png),
                               "1440", "900"],
                              cwd=str(SHOOT.parent), capture_output=True, text=True,
                              timeout=240, env=env)
    except Exception as exc:
        print(f"  screenshot failed: {type(exc).__name__}: {exc}")
        return False
    ok = proc.returncode == 0 and out_png.exists()
    print(f"  screenshot {'→ ' + str(out_png) if ok else 'FAILED: ' + (proc.stderr or proc.stdout).strip()[:200]}")
    return ok


def gate_page(render_dir: Path, style_id: str, *, composition: bool,
              report_name: str = "onbrand-report.md") -> tuple[bool, list]:
    """Authoritative gate via onbrand_check.py CLI. Deterministic catalog pages gate
    WITHOUT --composition (the established convention); composition.v1-shaped pages
    gate WITH it (HARD invariants)."""
    cmd = [PY, str(BP / "onbrand_check.py"), str(BRAND_YAML), str(render_dir),
           "--layout", "opening-bookend", "--style", style_id, "--report", report_name]
    if composition:
        cmd.append("--composition")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    scorecard_path = render_dir / re.sub(r"\.md$", ".json", report_name)
    scorecard = json.loads(scorecard_path.read_text()) if scorecard_path.exists() else {}
    overall = bool(scorecard.get("overall", proc.returncode == 0))
    failures = gc._parse_gate_failures(render_dir / report_name)
    if not overall and not failures and proc.returncode != 0:
        failures = [("gate", (proc.stderr or proc.stdout or "").strip()[:400])]
    return overall, failures


def font_markers(index_html: Path) -> dict:
    """Melodrama self-hosted font verification markers (hero display weight 500,
    per-weight @font-face incl. 400 for section headings, files copied to assets/)."""
    html = index_html.read_text()
    assets = index_html.parent / "assets"
    return {
        "melodrama_font_face": "font-family: 'Melodrama'" in html,
        "face_400": bool(re.search(r"Melodrama-Regular[^}]*font-weight: 400", html)),
        "face_500": bool(re.search(r"Melodrama-Medium[^}]*font-weight: 500", html)),
        "display_weight_500": "--c-display-weight: 500" in html,
        "woff2_on_disk": (assets / "Melodrama-Medium.woff2").exists()
                         and (assets / "Melodrama-Regular.woff2").exists(),
    }


# ── quiet divider labels (the hero-gallery divider convention, CSS-shim form) ─────
# Caption-scale, uppercase-tracked, thin hairline rule, minimal padding — NEVER
# display-tier type. Appended post-render exactly like inject_comparison_shim in
# build_anchored_variants.py (brand token values only; no radius/shadow/gradient).

def inject_divider_shim(index_html: Path, labels: list[tuple[str, str]]) -> None:
    """labels = [(data-layout id, label text)]. Idempotent."""
    html = index_html.read_text()
    if 'id="showcase-divider-shim"' in html:
        return
    rules = []
    for lid, text in labels:
        safe = text.replace('"', "'")
        rules.append(f'div[data-layout="{lid}"]::before {{ content: "{safe}"; }}')
    shim = """<style id="showcase-divider-shim">
/* showcase divider labels — appended by build_showcase.py, not a pipeline change.
   Quiet eyebrow-style strips (hero-gallery divider convention): caption scale,
   uppercase tracked, thin hairline rule; can never read as a hero. */
div[data-layout]::before {
  display: block; box-sizing: border-box; width: 100%;
  padding: 0.75rem 2.5rem 0.75rem;
  background: var(--c-panel, #F7EFE6); color: var(--c-panel-ink, #1F1A14);
  font-family: var(--font-body, sans-serif); font-size: 11px;
  letter-spacing: 0.14em; text-transform: uppercase; opacity: 0.92; }
""" + "\n".join(rules) + "\n</style>\n"
    index_html.write_text(html.replace("</head>", shim + "</head>", 1))


# ══════════════════════════════════════════════════════════════════════════════════
# PART A1 — the PROJECT-tier "all patterns" page per style (compose_page, real copy)
# ══════════════════════════════════════════════════════════════════════════════════

def build_project_page(style_id: str) -> dict:
    out = PAGES / f"all-project-{style_id}"
    order = ",".join(lid for lid, _, _ in PROJECT_ORDER)
    cmd = [PY, str(BP / "compose_page.py"), str(BRAND_YAML), "-o", str(out),
           "--style", style_id, "--order", order]
    print(f"\n=== PROJECT tier :: {style_id} ({len(PROJECT_ORDER)} patterns) ===")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        print(proc.stdout[-1500:], proc.stderr[-1500:])
        return {"page": f"all-project-{style_id}", "ok": False,
                "error": (proc.stderr or proc.stdout).strip()[-400:]}
    labels = [(lid, f"{i + 1:02d} / {pid} / project tier / archetype {arch}")
              for i, (lid, pid, arch) in enumerate(PROJECT_ORDER)]
    labels.append(("closing-bookend",
                   f"{len(PROJECT_ORDER) + 1:02d} / closing bookend / brand footer (auto)"))
    inject_divider_shim(out / "index.html", labels)
    overall, failures = gate_page(out, style_id, composition=False)
    print(f"  gate: {'PASS' if overall else 'FAIL ' + str(failures)}")
    return {"page": f"all-project-{style_id}", "style": style_id, "tier": "project",
            "sections": len(PROJECT_ORDER) + 1, "patterns": [p for _, p, _ in PROJECT_ORDER],
            "gate_pass": bool(overall), "failures": failures,
            "index_html": str(out / "index.html"), "fonts": font_markers(out / "index.html")}


# ══════════════════════════════════════════════════════════════════════════════════
# PART A2 — the STANDARD-tier page per style (deterministic pattern→section derivation)
# ══════════════════════════════════════════════════════════════════════════════════
# Derivation follows the blessed original_hero_section convention (anchored harness):
# slots come from the pattern's OWN contentShape, treatments from its specialTreatments
# (minus unsanctioned text-on-media — WoodWave neverDo no-text-on-photos), knobs from
# its variantKnob defaults, and every copy string is BRAND-AUTHORED (voice.md §5 via
# compose_section.LAYOUT_COPY / SECTION_COPY) — never invented here.

def _copy_sources() -> dict:
    CSC, LC = cs.SECTION_COPY, cs.LAYOUT_COPY
    return {
        "hero": {"eyebrow": CSC["eyebrow"], "heading": "WOODWAVE GALLERY",
                 "body": CSC["subhead"], "cta": CSC["cta"],
                 "caption": LC["gallery-showcase"]["caption"], "counter": "1/6",
                 "ghost": CSC["wordmark"].upper()},
        "about": {"eyebrow": LC["mission-statement"]["eyebrow"],
                  "heading": LC["mission-statement"]["heading"],
                  "body": LC["mission-statement"]["body"],
                  "cta": LC["mission-statement"]["cta"],
                  "caption": LC["editorial-collage"]["caption"],
                  "ghost": LC["editorial-collage"]["ghost"]},
        "features": {"eyebrow": LC["info-band"]["eyebrow"],
                     "heading": LC["info-band"]["heading"],
                     "body": LC["mission-statement"]["body"],
                     "cta": LC["info-band"]["cta"],
                     "caption": LC["info-band"]["caption"],
                     "rows": LC["info-band"]["rows"],
                     "panelTitle": LC["info-band"]["panelTitle"],
                     "ghost": LC["editorial-collage"]["ghost"]},
        "gallery": {"eyebrow": LC["gallery-showcase"]["eyebrow"],
                    "heading": LC["mission-statement"]["heading"],
                    "body": LC["mission-statement"]["body"],
                    "cta": LC["mission-statement"]["cta"],
                    "caption": LC["gallery-showcase"]["caption"],
                    "counter": LC["gallery-showcase"]["counter"],
                    "ghost": cs.SECTION_COPY["wordmark"].upper()},
        "testimonial": {"eyebrow": LC["curator-quote"]["eyebrow"],
                        "heading": LC["curator-quote"]["quote"],
                        "body": LC["curator-quote"]["body"],
                        "caption": LC["curator-quote"]["caption"],
                        "cta": LC["mission-statement"]["cta"]},
        "pricing": {"eyebrow": LC["exhibition-tickets"]["eyebrow"],
                    "heading": LC["exhibition-tickets"]["heading"],
                    "body": LC["exhibition-tickets"]["intro"],
                    "rows": LC["exhibition-tickets"]["rows"],
                    "cta": LC["exhibition-tickets"]["cta"],
                    "panelTitle": LC["info-band"]["panelTitle"],
                    "caption": LC["info-band"]["caption"]},
        "cta": {"eyebrow": LC["conversion-stack"]["eyebrow"],
                "heading": LC["conversion-stack"]["heading"],
                "body": LC["conversion-stack"]["body"],
                "placeholder": LC["conversion-stack"]["placeholder"],
                "cta": LC["conversion-stack"]["cta"],
                "caption": LC["info-band"]["caption"]},
        "footer": {"eyebrow": "WoodWave", "heading": CSC["wordmark"].upper(),
                   "body": CSC["subhead"], "cta": CSC["cta"],
                   "caption": LC["gallery-showcase"]["caption"], "counter": "1/1",
                   "ghost": CSC["wordmark"].upper()},
    }


def _slot_contract(s: dict) -> str:
    blob = (str(s.get("name", "")) + " " + str(s.get("role", ""))).lower()
    if s.get("mediaAspect") or any(k in blob for k in ("photo", "media", "image", "map",
                                                       "portrait", "icon")):
        return "image"
    if any(k in blob for k in ("wordmark-nav", "logo")):
        return "logo"
    if any(k in blob for k in ("form", "input", "signup", "field")):
        return "form"
    if any(k in blob for k in ("cta", "action", "link")):
        return "link"
    if any(k in blob for k in ("eyebrow", "overline", "kicker")):
        return "eyebrow"
    if any(k in blob for k in ("caption", "label", "counter", "badge", "utility",
                               "nav-overlay", "attribution", "meta")):
        return "caption"
    if any(k in blob for k in ("ghost", "watermark", "wordmark")):
        return "heading"
    if any(k in blob for k in ("heading", "title", "statement", "quote", "display")):
        return "heading"
    if any(k in blob for k in ("body", "lede", "copy", "para", "text", "answer",
                               "description")):
        return "paragraph"
    return "paragraph"


def _bind_copy(slot: dict, contract: str, p: ll.Pattern, src: dict) -> None:
    """Bind brand-authored copy onto a derived slot in the shape the archetype's copy
    translator (compose_from_composition._COPY_TRANSLATORS) reads."""
    blob = (str(slot.get("name", "")) + " " + str(slot.get("role", ""))).lower()
    arch = p.archetype_ref
    if contract == "image":
        slot["asset"] = None
        return
    if any(k in blob for k in ("ghost", "watermark")) and "wordmark-nav" not in blob:
        slot["copy"] = {"text": str(src.get("ghost", ""))}
        return
    if any(k in blob for k in ("panel", "rows", "list", "prices")):
        slot["copy"] = [{"label": l, "value": v} for l, v in (src.get("rows") or [])]
        return
    if contract == "heading":
        slot["copy"] = {"eyebrow": src.get("eyebrow", ""), "heading": src.get("heading", "")}
        return
    if contract == "eyebrow":
        slot["copy"] = {"text": src.get("eyebrow", "")}
        return
    if contract == "link":
        slot["copy"] = {"label": src.get("cta", "")}
        return
    if contract == "form":
        slot["copy"] = {"placeholder": src.get("placeholder", "Your email"),
                        "submit": src.get("cta", "")}
        return
    if contract == "caption":
        if "counter" in blob or "index" in blob:
            slot["copy"] = {"text": src.get("counter", "1/1")}
        else:
            slot["copy"] = {"text": src.get("caption", src.get("eyebrow", ""))}
        return
    # paragraph-ish body: a split section with brand rows binds them as the repeatable
    # module list (the translator folds list-copy into the ruled panel rows).
    if arch == "split" and src.get("rows"):
        slot["copy"] = [{"label": l, "value": v} for l, v in src["rows"]]
    else:
        slot["copy"] = {"text": src.get("body", "")}


def derive_section(p: ll.Pattern, sid: str, *, knob_overrides: dict | None = None,
                   treatment_side: str | None = None,
                   surface_override: str | None = None,
                   copy_src: dict | None = None) -> dict:
    """ONE pattern → ONE composition.v1-shaped section, derived deterministically from
    the pattern's contentShape/specialTreatments (the original_hero_section convention).
    Unsanctioned text-on-media treatments are dropped (brand neverDo no-text-on-photos);
    for non-drawable archetypes (generic-flow route) z:back decoration slots are skipped
    (a flow cannot draw layered decoration)."""
    src = copy_src or _copy_sources().get(p.use_case, _copy_sources()["about"])
    drawable = p.archetype_ref in DRAWABLE
    slots = []
    for s in p.slots:
        name = str(s.get("name"))
        blob = (name + " " + str(s.get("role") or "")).lower()
        is_ghost = any(k in blob for k in ("ghost", "watermark"))
        if not drawable and str(s.get("z")) == "back" and not s.get("mediaAspect"):
            continue                      # undrawable decoration layer in a flow
        if not drawable and is_ghost:
            continue
        slot = {"name": name, "role": str(s.get("role") or name),
                "textLen": str(s.get("textLen") or "none"),
                "sizeClass": str(s.get("sizeClass") or "body"),
                "width": str(s.get("width") or "hug"),
                "z": str(s.get("z") or "front")}
        contract = _slot_contract(s)
        slot["contract"] = contract
        if s.get("mediaAspect"):
            slot["mediaAspect"] = str(s["mediaAspect"])
        _bind_copy(slot, contract, p, src)
        slots.append(slot)

    treatments = []
    for t in (p.special_treatments or []):
        t = dict(t)
        if str(t.get("kind")) == "text-on-media" and not t.get("sanctioned"):
            continue                      # brand neverDo: no-text-on-photos
        if treatment_side and str(t.get("kind")) in ("float-wrap", "inset"):
            t["side"] = treatment_side
        treatments.append(t)

    knobs = {k: (v or {}).get("default") for k, v in (p.variant_knobs or {}).items()
             if isinstance(v, dict) and v.get("default") is not None}
    if knob_overrides:
        knobs.update(knob_overrides)

    return {
        "id": sid,
        "useCase": p.use_case if p.use_case in ("hero", "features", "pricing",
                                                "testimonial", "gallery", "cta", "about",
                                                "faq", "logos", "footer") else "about",
        "archetype": p.archetype_ref,
        "surfaceIntent": surface_override or (p.surface_intent
                                              if p.surface_intent in cfc.SURFACE_INTENT_MAP
                                              else "any"),
        "novelty": "reuse",
        "seededFrom": {"lib": p.lib or "standard", "id": p.id},
        "slots": slots,
        "treatments": treatments,
        "knobs": knobs,
    }


def _measured_hero_section() -> dict:
    """The measured original hero (opening bookend) — the anchored harness's blessed
    deterministic derivation, imported and reused (never re-invented)."""
    import build_anchored_variants as bav
    _, seed = bav.load_seed()
    return bav.original_hero_section(seed)


def _render_and_gate(comp: dict, out: Path, style_id: str,
                     labels: list[tuple[str, str]]) -> tuple[bool, list]:
    out.mkdir(parents=True, exist_ok=True)
    cfc.render_composition(comp, BRAND_YAML, out, style_id=style_id, brand_dir=BRAND_DIR)
    inject_divider_shim(out / "index.html", labels)
    return gate_page(out, style_id, composition=True)


def build_standard_page(style_id: str) -> dict:
    print(f"\n=== STANDARD tier :: {style_id} ===")
    patterns: list[ll.Pattern] = []
    for uc in USE_CASE_ORDER:
        patterns += ll.load_standard_patterns(uc)
    hero = _measured_hero_section()
    sections = [hero]
    meta = []
    for p in patterns:
        sec = derive_section(p, p.id)
        # SINGLE-ACCENT invariant, enforced deterministically for the stitch (the
        # woodwave-hybrid build_showcase convention): only the opening measured hero
        # keeps the inverse accent bookend; every other section renders primary/panel.
        if sec["surfaceIntent"] in ("inverse", "inverse-strong"):
            sec["surfaceIntent"] = "primary"
        sections.append(sec)
        meta.append({"id": p.id, "useCase": p.use_case, "archetype": p.archetype_ref,
                     "drawable": p.archetype_ref in DRAWABLE})
    comp = {
        "schemaVersion": "composition.v1",
        "brief": {"id": f"woodwave-standard-patterns-{style_id}",
                  "useCasesRequested": USE_CASE_ORDER},
        "brand": {"ref": str(BRAND_YAML)},
        "style": {"id": style_id},
        "sections": sections,
        "rationale": ("Standard-tier layout-pattern showcase: the measured opening "
                      "bookend, then every contracts/layout-patterns/ pattern derived "
                      "deterministically from its contentShape; non-drawable archetypes "
                      "(row/grid/bento/band/overlay) degrade to the generic-flow safety "
                      "net pending the harvest/contract work."),
    }
    labels = [("hero-original", "00 / hero-display-over-staggered-media / project seed / measured opening bookend")]
    for i, m in enumerate(meta):
        note = f"archetype {m['archetype']}" if m["drawable"] \
            else f"archetype {m['archetype']} (not drawable yet - generic-flow fallback)"
        labels.append((m["id"], f"{i + 1:02d} / {m['id']} / standard tier / {note}"))
    labels.append(("closing-bookend", f"{len(meta) + 1:02d} / closing bookend / brand footer (auto)"))

    out = PAGES / f"all-standard-{style_id}"
    excluded: list[dict] = []
    overall, failures = _render_and_gate(comp, out, style_id, labels)
    # exclusion loop: a failing check that names specific sections gets those sections
    # dropped (reported), then re-render + re-gate — failures stay OUT of lanes.
    for _round in range(3):
        if overall:
            break
        drop = set()
        for cid, detail in failures:
            for sid in re.findall(r'data-layout="([^"]+)"', detail):
                drop.add(sid)
            for m in re.finditer(r"#sec-(\d+)", detail):
                idx = int(m.group(1))
                if 0 <= idx < len(comp["sections"]):
                    drop.add(str(comp["sections"][idx].get("id")))
        drop.discard("hero-original")
        if not drop:
            break
        print(f"  gate FAIL — excluding sections implicated: {sorted(drop)}")
        for sid in sorted(drop):
            excluded.append({"id": sid, "reason": "; ".join(
                f"{c}: {d[:160]}" for c, d in failures)})
        comp["sections"] = [s for s in comp["sections"] if s.get("id") not in drop]
        labels = [l for l in labels if l[0] not in drop]
        if (out / "index.html").exists():
            (out / "index.html").unlink()
        overall, failures = _render_and_gate(comp, out, style_id, labels)
    print(f"  gate: {'PASS' if overall else 'FAIL ' + str(failures)}  "
          f"sections={len(comp['sections'])} excluded={len(excluded)}")
    return {"page": f"all-standard-{style_id}", "style": style_id, "tier": "standard",
            "sections": len(comp["sections"]), "patterns": [m["id"] for m in meta],
            "drawable": [m["id"] for m in meta if m["drawable"]],
            "generic_flow": [m["id"] for m in meta if not m["drawable"]],
            "excluded": excluded, "gate_pass": bool(overall), "failures": failures,
            "index_html": str(out / "index.html"),
            "fonts": font_markers(out / "index.html")}


def cmd_patterns(args) -> int:
    results = []
    for style in STYLES:
        results.append(build_project_page(style))
        results.append(build_standard_page(style))
    _save_results("patterns", results)
    ok = all(r.get("gate_pass") for r in results)
    print(f"\npatterns: {sum(1 for r in results if r.get('gate_pass'))}/{len(results)} pages gate-green")
    return 0 if ok else 1


# ══════════════════════════════════════════════════════════════════════════════════
# PART B — archetype × treatment/lever SAMPLER (the levers that exist TODAY)
# ══════════════════════════════════════════════════════════════════════════════════

def _project_pattern(pid: str) -> ll.Pattern:
    p = ll.get({"lib": "project", "id": pid}, BRAND_YAML)
    if p is None:
        raise SystemExit(f"project pattern {pid} not found")
    return p


def build_sampler() -> dict:
    style_id = "editorial-luxury"
    print(f"\n=== ARCHETYPE × LEVER SAMPLER :: {style_id} ===")
    SRC = _copy_sources()
    LC = cs.LAYOUT_COPY

    specs = []
    # 1. stack · hero — the measured baseline (accent bookend).
    specs.append(("smp-hero", "stack / hero / measured baseline (opening bookend)",
                  _measured_hero_section()))
    # id must be unique but keep the hero id convention for the accent bookend
    specs[0][2]["id"] = "smp-hero"

    # 2–3. stack · conversion — alignment anchor center vs left (a real §4.6.5 lever).
    cta = ll.get({"lib": "project", "id": "cta-underline-conversion-stack"}, BRAND_YAML)
    s_center = derive_section(cta, "smp-conversion-center",
                              knob_overrides={"align": "center"}, copy_src=SRC["cta"])
    s_left = derive_section(cta, "smp-conversion-left",
                            knob_overrides={"align": "left"}, copy_src=SRC["cta"])
    specs.append(("smp-conversion-center",
                  "stack / conversion / alignment anchor = center (pattern default)", s_center))
    specs.append(("smp-conversion-left",
                  "stack / conversion / alignment anchor = left", s_left))

    # 4–5. collage — ghost WORD (editorial about-run) vs ghost NUMERALS (heritage).
    col = _project_pattern("editorial-ghostword-collage")
    s_col = derive_section(col, "smp-collage-ghostword", copy_src={
        **SRC["about"], "ghost": LC["editorial-collage"]["ghost"],
        "eyebrow": LC["editorial-collage"]["eyebrow"],
        "heading": LC["editorial-collage"]["heading"],
        "body": LC["editorial-collage"]["body"],
        "caption": LC["editorial-collage"]["caption"],
        "cta": LC["editorial-collage"]["cta"]})
    her = _project_pattern("heritage-ghost-numerals-timeline")
    s_her = derive_section(her, "smp-collage-numerals", copy_src={
        **SRC["about"], "ghost": LC["heritage-timeline"]["ghost"],
        "eyebrow": LC["heritage-timeline"]["eyebrow"],
        "heading": LC["heritage-timeline"]["heading"],
        "body": LC["heritage-timeline"]["body"],
        "caption": LC["heritage-timeline"]["caption"]})
    specs.append(("smp-collage-ghostword", "collage / ghost-word run (About)", s_col))
    specs.append(("smp-collage-numerals",
                  "collage / ghost-numerals timeline (patternRef-routed variant)", s_her))

    # 6. split · info-band (flush photo + cream ruled panel).
    band = _project_pattern("features-flush-split-panel")
    s_band = derive_section(band, "smp-split-infoband", copy_src=SRC["features"])
    specs.append(("smp-split-infoband", "split / dark info-band (photo + ruled panel)", s_band))

    # 7. stack-fullbleed · gallery counter band.
    gal = _project_pattern("gallery-fullbleed-counter-band")
    s_gal = derive_section(gal, "smp-gallery-band", copy_src=SRC["gallery"])
    specs.append(("smp-gallery-band", "stack-fullbleed / full-bleed counter band", s_gal))

    # 8–9. cards — 2 modules (harvest default) vs 3 modules (copy-mediated count).
    cards = _project_pattern("features-staggered-caption-cards")
    two = LC["demo-staggered-cards"]["cards"]
    mod2 = [{"heading": c["caption"], "text": c["body"],
             **({"link": c["link"]} if c.get("link") else {})} for c in two]
    mod3 = mod2 + [{"heading": LC["gallery-showcase"]["caption"],
                    "text": LC["mission-statement"]["body"]}]

    def cards_section(sid, modules):
        sec = derive_section(cards, sid, copy_src=SRC["features"])
        sec["slots"] = [
            {"name": "intro", "role": "section-title", "contract": "heading",
             "textLen": "short", "sizeClass": "title", "width": "hug", "z": "front",
             "copy": {"eyebrow": LC["demo-staggered-cards"]["eyebrow"],
                      "heading": LC["demo-staggered-cards"]["heading"]}},
            {"name": "modules", "role": "module run", "contract": "feature-item",
             "textLen": "long", "sizeClass": "body", "width": "stretch", "z": "front",
             "copy": modules},
        ]
        return sec
    specs.append(("smp-cards-2", "cards / 2 staggered caption modules (default)",
                  cards_section("smp-cards-2", mod2)))
    specs.append(("smp-cards-3", "cards / 3 staggered caption modules (copy-mediated count)",
                  cards_section("smp-cards-3", mod3)))

    # 10–11. interlock — float side right (default) vs left (mirrorable lever).
    inter = _project_pattern("editorial-interlocking-inset")
    def interlock_section(sid, side):
        sec = derive_section(inter, sid, treatment_side=side,
                             knob_overrides={"floatSide": side, "mediaSide": side},
                             copy_src=SRC["about"])
        for slot in sec["slots"]:
            blob = (slot["name"] + " " + slot["role"]).lower()
            if "caption" in blob:
                slot["copy"] = {"text": LC["demo-interlock-inset"]["caption"]}
            elif "statement" in blob or slot["contract"] == "heading":
                slot["copy"] = {"heading": LC["demo-interlock-inset"]["statement"]}
        return sec
    specs.append(("smp-interlock-right", "interlock / float-wrap inset RIGHT (default)",
                  interlock_section("smp-interlock-right", "right")))
    specs.append(("smp-interlock-left", "interlock / float-wrap inset LEFT (mirrored)",
                  interlock_section("smp-interlock-left", "left")))

    sections = [s for _, _, s in specs]
    comp = {
        "schemaVersion": "composition.v1",
        "brief": {"id": "woodwave-archetype-sampler",
                  "useCasesRequested": ["hero", "about", "features", "gallery", "cta"]},
        "brand": {"ref": str(BRAND_YAML)},
        "style": {"id": style_id},
        "sections": sections,
        "rationale": ("Archetype × lever sampler: every registered archetype composer "
                      "with its section-tunable levers exercised (alignment anchor, "
                      "float side, module count, ghost word vs numerals). Levers that "
                      "are library-default-only today (titleOverlap, staggerAmount, "
                      "columnRatio, split mediaSide, panelOrder, insetMeasure) are "
                      "deferred to the in-flight grid/overlap contract work."),
    }
    labels = [(sid, f"{i:02d} / {desc}") for i, (sid, desc, _) in enumerate(specs)]
    labels.append(("closing-bookend", f"{len(specs):02d} / closing bookend / brand footer (auto)"))
    out = PAGES / "archetype-sampler"
    overall, failures = _render_and_gate(comp, out, style_id, labels)
    print(f"  gate: {'PASS' if overall else 'FAIL ' + str(failures)}")
    result = {"page": "archetype-sampler", "style": style_id,
              "sections": [sid for sid, _, _ in specs],
              "gate_pass": bool(overall), "failures": failures,
              "index_html": str(out / "index.html"),
              "fonts": font_markers(out / "index.html")}
    _save_results("sampler", result)
    return result


def cmd_sampler(args) -> int:
    return 0 if build_sampler().get("gate_pass") else 1


# ══════════════════════════════════════════════════════════════════════════════════
# PART C — LIVE hybrid compositions (offGridExpansion ON ×5 / forced OFF ×2)
# ══════════════════════════════════════════════════════════════════════════════════

ON_DIRECTIVES = [
    "Favor LIBRARY SEEDS: reuse the seeded patterns as-is (novelty:reuse) wherever they "
    "fit. A clean, confident, conventional gallery landing page.",
    "ADAPT the seeded patterns: keep their shape but tune variantKnobs and swap a slot "
    "or two (novelty:adapt) to fit the brief tighter. Still library-grounded.",
    "Propose AT LEAST ONE novelty:novel OFF-GRID section (seededFrom:null, stagger / "
    "overlap / bleed) that the library lacks but the brief implies. Keep the rest "
    "reuse/adapt.",
    "REORDER for a different narrative rhythm and alternate surfaces (primary/panel/"
    "inverse) section-to-section; use interlock or collage for the visit info instead "
    "of a plain split.",
    "MAXIMIZE STRUCTURAL CONTRAST: make each section a DIFFERENT archetype (split, "
    "collage, cards, interlock, stack-fullbleed, stack) and include at least one "
    "novelty:novel off-grid section. Push editorial variety while staying gate-legal.",
]
OFF_DIRECTIVES = [
    "Favor LIBRARY SEEDS: reuse the seeded patterns as-is (novelty:reuse) wherever they "
    "fit. A clean, confident, conventional gallery landing page.",
    "Propose AT LEAST ONE novelty:novel OFF-GRID section (seededFrom:null, stagger / "
    "overlap / bleed) that the library lacks but the brief implies. Keep the rest "
    "reuse/adapt.",
]


def cmd_hybrid(args) -> int:
    if not gc.load_api_keys():
        print(f"ERROR: ANTHROPIC_API_KEY not available (looked in {REPO / '.env.local'}).")
        return 3
    from screenshot_to_template.models.anthropic import AnthropicProvider
    provider = AnthropicProvider(args.model or gc.DEFAULT_MODEL,
                                 reasoning_effort=gc.DEFAULT_REASONING)
    print(f"Model: {provider.model}")
    doc = gc.load_brand(BRAND_YAML)
    seeds = gc.seed_patterns(doc, BRAND_YAML)
    print(f"Seed patterns: {', '.join(seeds.pattern_ids()) or '(none)'}")
    brief_text = (BRAND_DIR / "brief.md").read_text()

    runs = [("on", i + 1, d, None) for i, d in enumerate(ON_DIRECTIVES)] \
        + [("off", i + 1, d, False) for i, d in enumerate(OFF_DIRECTIVES)]
    if args.only:
        keep = set(args.only.split(","))
        runs = [r for r in runs if f"{r[0]}-{r[1]}" in keep]

    prior = {r["id"]: r for r in _load_results().get("hybrid", [])}
    rerun_ids = {f"{a}-{n}" for a, n, _, _ in runs}
    # keep prior results for runs NOT being (re)run this invocation.
    results = [v for k, v in prior.items() if k not in rerun_ids]
    for arm, n, directive, force in runs:
        rid = f"{arm}-{n}"
        out_dir = HYBRID / rid
        print(f"\n=== HYBRID {rid} :: offGridExpansion "
              f"{'FORCED OFF' if force is False else 'ON (style identity)'} ===")
        t0 = time.time()
        try:
            res = gc.generate_composition(
                brief_text, BRAND_YAML, "editorial-luxury",
                out_dir=out_dir, brief_id=f"woodwave-showcase-{rid}",
                variety_directive=directive, max_repairs=args.max_repairs,
                provider=provider, seeds=seeds, force_off_grid=force)
        except Exception as exc:
            print(f"  ERRORED: {type(exc).__name__}: {exc}")
            results.append({"id": rid, "ok": False, "error": f"{type(exc).__name__}: {exc}"})
            continue
        wall = round(time.time() - t0, 1)
        comp = res.composition or {}
        secs = comp.get("sections", [])
        shot = False
        if res.render_dir and (Path(res.render_dir) / "index.html").exists():
            shot = screenshot(Path(res.render_dir) / "index.html",
                              Path(res.render_dir) / "screenshot.png")
        results.append({
            "id": rid, "off_grid": (force is not False), "directive": directive,
            "ok": res.ok, "attempts": res.attempts, "wall_s": wall,
            "archetypes": [s.get("archetype") for s in secs],
            "novelties": [s.get("novelty") for s in secs],
            "n_sections": len(secs),
            "has_novel": any(s.get("novelty") == "novel" for s in secs),
            "failures": res.failures, "screenshot": shot,
            "index_html": str(Path(res.render_dir) / "index.html") if res.render_dir else None,
            "fonts": font_markers(Path(res.render_dir) / "index.html")
            if res.render_dir and (Path(res.render_dir) / "index.html").exists() else {},
        })
        print(f"  ok={res.ok} attempts={res.attempts} wall={wall}s "
              f"archetypes={[s.get('archetype') for s in secs]}")
    _save_results("hybrid", results)
    passes = sum(1 for r in results if r.get("ok"))
    print(f"\nhybrid: {passes}/{len(results)} gate-green")
    return 0


def _copy_referenced_brand_assets(page_dir: Path) -> list[str]:
    """copy_assets() only ships compose_section.ASSET_SOURCES; a composition may
    legitimately reference OTHER real files under runs/woodwave/brand/assets/ (the
    sanitizer validates against that dir). Copy any referenced-but-missing REAL brand
    asset into the page's assets/ so the gate's asset-presence rows see the file.
    Real files only — a name with no source file is left for the gate to flag."""
    import shutil
    index = page_dir / "index.html"
    if not index.exists():
        return []
    html = index.read_text()
    out_assets = page_dir / "assets"
    out_assets.mkdir(exist_ok=True)
    copied = []
    for name in set(re.findall(r'assets/([A-Za-z0-9._-]+\.(?:jpg|jpeg|png|svg|webp|gif))', html)):
        dst = out_assets / name
        if dst.exists():
            continue
        for cand in (BRAND_DIR / "assets" / name, BRAND_DIR / name):
            if cand.exists():
                shutil.copy2(cand, dst)
                copied.append(name)
                break
    return copied


def cmd_hybrid_rerender(args) -> int:
    """Re-render + re-gate the PERSISTED LLM compositions (hybrid/<id>/composition.json)
    without new model calls — used after a harness-level render fix. The compositions
    remain 100%% LLM-authored; only the deterministic adapter render is repeated."""
    prior = {r["id"]: r for r in _load_results().get("hybrid", [])}
    results = []
    for rid_dir in sorted(HYBRID.iterdir()):
        rid = rid_dir.name
        cpath = rid_dir / "composition.json"
        if not cpath.exists():
            if rid in prior:
                results.append(prior[rid])
            continue
        comp = json.loads(cpath.read_text())
        print(f"\n=== HYBRID re-render {rid} ===")
        try:
            cfc.render_composition(comp, BRAND_YAML, rid_dir,
                                   style_id="editorial-luxury", brand_dir=BRAND_DIR)
        except Exception as exc:
            print(f"  render failed: {type(exc).__name__}: {exc}")
            old = prior.get(rid, {"id": rid})
            results.append({**old, "ok": False,
                            "failures": [("render", f"{type(exc).__name__}: {exc}")]})
            continue
        extra = _copy_referenced_brand_assets(rid_dir)
        if extra:
            print(f"  copied referenced brand assets: {extra}")
        overall, failures, _ = gc.gate_composition(rid_dir, BRAND_YAML, "editorial-luxury")
        print(f"  gate: {'PASS' if overall else 'FAIL ' + str([c for c, _ in failures])}")
        shot = screenshot(rid_dir / "index.html", rid_dir / "screenshot.png")
        secs = comp.get("sections", [])
        old = prior.get(rid, {})
        results.append({
            "id": rid, "off_grid": old.get("off_grid", rid.startswith("on")),
            "directive": old.get("directive"), "ok": bool(overall),
            "attempts": old.get("attempts"), "wall_s": old.get("wall_s"),
            "rerendered": True,
            "archetypes": [s.get("archetype") for s in secs],
            "novelties": [s.get("novelty") for s in secs],
            "n_sections": len(secs),
            "has_novel": any(s.get("novelty") == "novel" for s in secs),
            "failures": failures, "screenshot": shot,
            "index_html": str(rid_dir / "index.html"),
            "fonts": font_markers(rid_dir / "index.html")
            if (rid_dir / "index.html").exists() else {},
        })
    _save_results("hybrid", results)
    passes = sum(1 for r in results if r.get("ok"))
    print(f"\nhybrid (re-render): {passes}/{len(results)} gate-green")
    return 0


# ══════════════════════════════════════════════════════════════════════════════════
# PART D — anchored hero variants (re-stitch + re-gate the existing page)
# ══════════════════════════════════════════════════════════════════════════════════

def cmd_anchored(args) -> int:
    script = REPO / "experiments" / "woodwave-hero-gallery" / "build_anchored_variants.py"
    proc = subprocess.run([PY, str(script), "--assemble-only"],
                          capture_output=True, text=True)
    tail = "\n".join((proc.stdout or "").splitlines()[-25:])
    print(tail)
    page = REPO / "experiments" / "woodwave-hero-gallery" / "page-anchored"
    summary = {}
    sfile = page / "assemble-summary.json"
    if sfile.exists():
        summary = json.loads(sfile.read_text())
    standalones = []
    stfile = REPO / "experiments" / "woodwave-hero-gallery" / "standalone-gates" / "results.json"
    if stfile.exists():
        standalones = json.loads(stfile.read_text())
    _save_results("anchored", {
        "rc": proc.returncode,
        "assembled_gate_pass": summary.get("gate_pass"),
        "assembled_failures": summary.get("failures"),
        "standalone_pass": sum(1 for r in standalones if r.get("gate_pass")),
        "standalone_total": len(standalones),
        "index_html": str(page / "index.html"),
        "fonts": font_markers(page / "index.html") if (page / "index.html").exists() else {},
    })
    return proc.returncode


# ══════════════════════════════════════════════════════════════════════════════════
# PART E — Studio lanes (symlink dirs + label.txt, the existing variant wiring)
# ══════════════════════════════════════════════════════════════════════════════════

def _publish_lane(name: str, page_dir: Path, label: str) -> None:
    lane = VARIANTS_DIR / name
    lane.mkdir(parents=True, exist_ok=True)
    rel = os.path.relpath(page_dir, lane)
    for target, link in (("index.html", lane / "index.html"), ("assets", lane / "assets")):
        if link.is_symlink() or link.exists():
            link.unlink()
        link.symlink_to(Path(rel) / target)
    (lane / "label.txt").write_text(label + "\n")
    print(f"  lane {name}: {label}")


def cmd_lanes(args) -> int:
    data = _load_results()
    published = []
    skipped = []

    for r in data.get("patterns", []):
        page = Path(r["index_html"]).parent
        tier = r["tier"]
        style = r["style"]
        lane = f"showcase-{tier}-{style}"
        label = (f"WoodWave — all patterns · {tier} tier ({style})")
        if r.get("gate_pass"):
            _publish_lane(lane, page, label)
            published.append({"lane": lane, "label": label, "url":
                              f"/runs/woodwave/brand/variants/{lane}/index.html"})
        else:
            skipped.append({"lane": lane, "failures": r.get("failures")})

    s = data.get("sampler")
    if s:
        if s.get("gate_pass"):
            lane = "showcase-archetype-sampler"
            label = "WoodWave — archetype × treatment sampler (editorial-luxury)"
            _publish_lane(lane, Path(s["index_html"]).parent, label)
            published.append({"lane": lane, "label": label, "url":
                              f"/runs/woodwave/brand/variants/{lane}/index.html"})
        else:
            skipped.append({"lane": "showcase-archetype-sampler", "failures": s.get("failures")})

    for r in data.get("hybrid", []):
        if not r.get("index_html"):
            skipped.append({"lane": f"showcase-hybrid-{r['id']}", "failures": [r.get("error")]})
            continue
        lane = f"showcase-hybrid-{r['id']}"
        onoff = "off-grid ON" if r.get("off_grid") else "off-grid OFF (contrast)"
        label = f"WoodWave — hybrid live seed {r['id']} ({onoff})"
        if r.get("ok"):
            _publish_lane(lane, Path(r["index_html"]).parent, label)
            published.append({"lane": lane, "label": label, "url":
                              f"/runs/woodwave/brand/variants/{lane}/index.html"})
        else:
            skipped.append({"lane": lane, "failures": r.get("failures")})

    # the anchored hero-variants page is already served by studio_server.hero_gallery_lanes
    anch = data.get("anchored") or {}
    published.append({"lane": "(built-in) hero_gallery_lanes", "label":
                      "WoodWave — anchored hero variants (live)", "url":
                      "/experiments/woodwave-hero-gallery/page-anchored/index.html"})

    # verify studio serves every lane 200
    port = os.environ.get("STUDIO_PORT", "1500")
    for p in published:
        url = f"http://localhost:{port}{p['url']}"
        try:
            proc = subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                                   url], capture_output=True, text=True, timeout=15)
            p["http"] = proc.stdout.strip()
        except Exception as exc:
            p["http"] = f"error: {exc}"
        print(f"  {p['http']}  {p['lane']}")
    _save_results("lanes", {"published": published, "skipped": skipped})
    bad = [p for p in published if p.get("http") != "200"]
    return 1 if bad else 0


# ══════════════════════════════════════════════════════════════════════════════════
# PART F — screenshots per lane + font verification
# ══════════════════════════════════════════════════════════════════════════════════

def cmd_shots(args) -> int:
    data = _load_results()
    shots_dir = HERE / "shots"
    shots_dir.mkdir(exist_ok=True)
    out = []
    for p in (data.get("lanes") or {}).get("published", []):
        rel = p["url"].lstrip("/")
        index = REPO / rel
        name = p["lane"].replace("(built-in) ", "").replace("/", "-")
        png = shots_dir / f"{name}.png"
        ok = screenshot(index, png)
        fonts = font_markers(index) if index.exists() else {}
        out.append({"lane": p["lane"], "screenshot": str(png) if ok else None,
                    "fonts": fonts})
    _save_results("shots", out)
    return 0


# ── main ───────────────────────────────────────────────────────────────────────────

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="WoodWave full variation showcase.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("patterns")
    sub.add_parser("sampler")
    hy = sub.add_parser("hybrid")
    hy.add_argument("--only", default="", help="comma list of run ids, e.g. on-1,off-2")
    hy.add_argument("--max-repairs", type=int, default=2)
    hy.add_argument("--model", default=None)
    sub.add_parser("hybrid-rerender")
    sub.add_parser("anchored")
    sub.add_parser("lanes")
    sub.add_parser("shots")
    args = ap.parse_args(argv)
    return {"patterns": cmd_patterns, "sampler": cmd_sampler, "hybrid": cmd_hybrid,
            "hybrid-rerender": cmd_hybrid_rerender,
            "anchored": cmd_anchored, "lanes": cmd_lanes, "shots": cmd_shots}[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
