# Phase 1 — Join CSS rules ↔ measured element ↔ vision role (foundation only)

> **Date:** 2026-07-21 · **Scope:** extraction tooling + join output + tests ONLY.
> No harness schema, renderer, authoring, or replica-scoring change (Phases 2–5).

## What landed

- **New module `tools/extract/join_evidence.py`** — a pure JOIN of the three
  previously-separate extraction outputs into a per-element evidence record:
  - binds governing CSS rules to each measured element/section by selector
    matching against the SAVED DOM (Euler-interval subtree index), tagging each
    bound rule `self` / `descendant` / `contextual`, and preserving `@media` and
    pseudo-state (`:hover`/`:focus`/…) rules that target the element or its
    subtree;
  - resolves `var()`/`calc()` chains while keeping the LITERAL expression
    (e.g. `calc(100dvh - var(--global-nav-header-height))` is preserved verbatim;
    the referenced custom property carries its per-`@media` literal values —
    `56px` default, `128px` at `@media(width >= 1080px)`);
  - carries the multi-viewport computed ladder (1920/1440/960/375) joined from
    `computed-styles.json` tier data + `section-rects.json` primary-tier rect;
  - attaches the owning section's `visionRole` from `grounding/*.yaml`
    (matched by `_source.domClasses` token overlap, with a chrome role hint);
  - emits `runs/<brand>/brand/evidence/joined-evidence.json` (schema
    `joined-evidence.v1`) WITHOUT altering any existing evidence file, and reports
    join coverage (elements with ≥1 governing rule vs missing, with reasons).
  - `--acceptance` prints the three responsive-fidelity criteria as PASS/FAIL.
  - HTML is resolved from `--capture`/`--html`, else the authoritative `source`
    field of the evidence (the capture the evidence was measured against).

- **New tests `brand_pipeline/tests/test_join_evidence.py`** (15 tests): selector
  parsing; synthetic-capture join (@media + :hover binding, literal calc/var
  preservation + resolved custom-property chain, 4-tier ladder, vision-role
  attach incl. owning-section inheritance, coverage-report shape, rule scopes,
  provenance/schema); and real hubspot-v3 acceptance fixtures (hero calc / footer
  @media / nav @media+state+background) + coverage ≥ 90%.

## Verification (2026-07-21)

- `join_evidence.py --evidence runs/hubspot-v3/... --acceptance`:
  - hero `.wf-page-header` carries literal
    `calc(100dvh - var(--global-nav-header-height))` — **PASS**
  - footer carries `@media(width >= 900px)` grid/column reflow rules
    (`.global-footer__nav*`) — **PASS**
  - nav/header carries @media (61) + state (118) + background (90) rules,
    incl. `.global-nav-header{background-color:…}` and
    `.global-nav-main[data-cl-fixed-element-is-fixed] @media(>=1080){background…}`
    — **PASS**
  - coverage 62/64 (96.9%); missing: `heading-p` (classless <p>, only tag rules)
    and `action-02` (cookie button with empty class signature).
- hubspot-v2 join: 62/64 (96.9%), no error. remote join: 25/25 (100%), no error
  (resolve HTML from `source` = `screenshots/remote-v2/remote-com.html`).
- Full suite: 1791 passed / 16 failed / 9 skipped / 4 errors — the 16 failures +
  4 errors are the pre-existing baseline (rendering/playwright/glyph); +15 new
  join tests, zero regressions.

## Out of scope (NOT touched)

`render_*`, `compose_*`, `contract_projection`, `author_brand`, `compose_replica`,
harness schema, replica scoring. Existing evidence files unchanged; only new
`joined-evidence.json` artifacts written (under gitignored `runs/`).
