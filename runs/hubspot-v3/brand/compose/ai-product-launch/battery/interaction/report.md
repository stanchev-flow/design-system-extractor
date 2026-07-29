# Interaction-Contract Baseline Report

Generated: 2026-07-28T23:54:06+00:00 — auditor v1.0.0 — mode: strict
Contracts: `brand_pipeline/spec/interaction-contracts.md` (WAI-ARIA APG primary; Base UI secondary; Radix tertiary)

## Audited lanes

| lane | file | mtime (UTC) | sha256/12 |
|---|---|---|---|
| compose/ai-product-launch | `runs/hubspot-v3/brand/compose/ai-product-launch/index.html` | 2026-07-28T18:39:25+00:00 | `c3f350fbf665` |

If a lane is re-rendered by another agent, re-run the audit; the mtime/sha above identify exactly which HTML was measured.

## Summary — 0 failing required cells, 2 advisory, 27 passing, 11 skipped

### Most impactful gaps (required checks failing, by lane count)

- none — all required checks pass

## Lane: compose/ai-product-launch

| check | family | severity | layer | status | detail |
|---|---|---|---|---|---|
| IC-CAR-03 | carousel | advisory | static | **advisory** | no slide-level group/roledescription semantics (line 3153) |
| IC-NAV-05 | nav | advisory | static | **advisory** | anchor with role=button in nav chrome — promises Space activation anchors don't have (line 3108) |
| IC-CAR-01 | carousel | required | static | **pass** | prev/next controls are buttons with accessible names (line 3175) |
| IC-CAR-02 | carousel | advisory | static | **pass** | container has aria-roledescription=carousel and a label (line 3153) |
| IC-CAR-05 | carousel | required | behavioral | **pass** | rail focusable; ArrowRight scrolls: 0->186 |
| IC-LANG-01 | lang | required | static | **pass** | toggle is a native <summary> inside <details> (line 3108) |
| IC-LANG-01 | lang | required | static | **pass** | toggle is a native <summary> inside <details> (line 3108) |
| IC-LANG-02 | lang | required | static | **pass** | toggle has an accessible name (line 3108) |
| IC-LANG-02 | lang | required | static | **pass** | toggle has an accessible name (line 3108) |
| IC-LANG-03 | lang | required | static | **pass** | current selection marked via aria-current/aria-selected (line 3108) |
| IC-LANG-04 | lang | advisory | static | **pass** | locale items are links carrying hreflang (line 3108) |
| IC-LANG-05 | lang | required | behavioral | **pass** | Enter opens (open=True), Space toggles back=True |
| IC-LANG-06 | lang | required | behavioral | **pass** | Escape closes the language dropdown |
| IC-LANG-07 | lang | advisory | behavioral | **pass** | open dropdown items are in the Tab order |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Products' is a native button (line 3108) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Solutions' is a native button (line 3108) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Resources' is a native button (line 3108) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Products' carries aria-expanded (line 3108) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Solutions' carries aria-expanded (line 3108) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Resources' carries aria-expanded (line 3108) |
| IC-NAV-03 | nav | required | static | **pass** | no ARIA menu/menubar roles in site nav |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 3108) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 3108) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 3108) |
| IC-NAV-06 | nav | required | behavioral | **pass** | Tab reaches nav triggers, login, and language switcher |
| IC-NAV-07 | nav | required | behavioral | **pass** | hover opens panel=True, keyboard focus opens panel=True |
| IC-NAV-08 | nav | required | behavioral | **pass** | Escape closes the open panel and keeps focus in nav |
| IC-REV-01 | reveal | required | static | **pass** | hidden initial state is gated on a JS-added class (.cs-motion-ready .cs-reveal…) |
| IC-REV-02 | reveal | required | static | **pass** | prefers-reduced-motion forces reveal targets visible |
| IC-REV-03 | reveal | advisory | static | **pass** | timed failsafe present (setTimeout forces all targets visible) |
| IC-REV-04 | reveal | required | behavioral | **pass** | reduced motion: gate applied=False, 0 tagged targets, 0 hidden |
| IC-TAB-01 | tabs | required | static | **pass** | tabs are native buttons with exactly one aria-selected (line 3212) |
| IC-TAB-02 | tabs | required | static | **pass** | tab↔panel aria-controls/aria-labelledby wiring is two-way (line 3212) |
| IC-TAB-03 | tabs | required | static | **pass** | roving tabindex + single visible focusable panel (line 3212) |
| IC-TAB-04 | tabs | advisory | static | **pass** | tablist has an accessible name (line 3212) |
| IC-TAB-05 | tabs | required | behavioral | **pass** | ArrowRight/ArrowLeft move focus and selection; the visible panel follows |
| IC-TAB-06 | tabs | required | behavioral | **pass** | Home/End jump selection; click selects (pointer parity) |
| IC-ACC-01 | acc | required | static | **skip** | no accordion/disclosure details detected in this lane |
| IC-ACC-06 | acc | required | behavioral | **skip** | no accordion groups detected in this lane |
| IC-ACC-07 | acc | required | behavioral | **skip** | no accordion groups detected in this lane |
| IC-ACC-08 | acc | required | behavioral | **skip** | no accordion groups detected in this lane |
| IC-BAN-01 | banner | required | static | **skip** | no dismissible banner detected in this lane |
| IC-BAN-04 | banner | required | behavioral | **skip** | no dismissible banner detected in this lane |
| IC-CAR-04 | carousel | advisory | static | **skip** | no auto-rotation on this rail — pause-control contract not applicable (line 3153) |
| IC-FORM-01 | form | required | static | **skip** | no form controls or labels detected in this lane |
| IC-FORM-07 | form | required | behavioral | **skip** | no form controls detected in this lane |
| IC-LANG-03 | lang | required | static | **skip** | disclosure-navigation menu (plain nav links, no selection concept) — selection marking not applicable |
| IC-MARQ-01 | marquee | required | static | **skip** | no marquee detected in this lane |
| IC-MARQ-03 | marquee | required | behavioral | **skip** | no marquee detected in this lane |

