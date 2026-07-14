# Interaction-Contract Baseline Report

Generated: 2026-07-14T20:18:14+00:00 — auditor v1.0.0 — mode: strict
Contracts: `brand_pipeline/spec/interaction-contracts.md` (WAI-ARIA APG primary; Base UI secondary; Radix tertiary)

## Audited lanes

| lane | file | mtime (UTC) | sha256/12 |
|---|---|---|---|
| compose/style-bakeoff-swiss/product-launch | `/Users/stanchev/Webflow/campaigns-hackathon/design-system-extractor-mine/runs/hubspot-v2/brand/compose/style-bakeoff-swiss/product-launch/index.html` | 2026-07-14T20:16:32+00:00 | `c46cf4afe5ae` |

If a lane is re-rendered by another agent, re-run the audit; the mtime/sha above identify exactly which HTML was measured.

## Summary — 0 failing required cells, 1 advisory, 16 passing, 16 skipped

### Most impactful gaps (required checks failing, by lane count)

- none — all required checks pass

## Lane: compose/style-bakeoff-swiss/product-launch

| check | family | severity | layer | status | detail |
|---|---|---|---|---|---|
| IC-NAV-05 | nav | advisory | static | **advisory** | anchor with role=button in nav chrome — promises Space activation anchors don't have (line 2785) |
| IC-LANG-01 | lang | required | static | **pass** | toggle is a native <summary> inside <details> (line 2775) |
| IC-LANG-02 | lang | required | static | **pass** | toggle has an accessible name (line 2775) |
| IC-LANG-05 | lang | required | behavioral | **pass** | Enter opens (open=True), Space toggles back=True |
| IC-LANG-06 | lang | required | behavioral | **pass** | Escape closes the language dropdown |
| IC-LANG-07 | lang | advisory | behavioral | **pass** | open dropdown items are in the Tab order |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Products' is a native button (line 2779) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Solutions' is a native button (line 2781) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Resources' is a native button (line 2783) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Products' carries aria-expanded (line 2779) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Solutions' carries aria-expanded (line 2781) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Resources' carries aria-expanded (line 2783) |
| IC-NAV-03 | nav | required | static | **pass** | no ARIA menu/menubar roles in site nav |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2779) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2781) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2783) |
| IC-NAV-06 | nav | required | behavioral | **pass** | Tab reaches nav triggers, login, and language switcher |
| IC-NAV-07 | nav | required | behavioral | **pass** | hover opens panel=True, keyboard focus opens panel=True |
| IC-NAV-08 | nav | required | behavioral | **pass** | Escape closes the open panel and keeps focus in nav |
| IC-REV-01 | reveal | required | static | **pass** | hidden initial state is gated on a JS-added class (.cs-motion-ready .cs-reveal…) |
| IC-REV-02 | reveal | required | static | **pass** | prefers-reduced-motion forces reveal targets visible |
| IC-REV-03 | reveal | advisory | static | **pass** | timed failsafe present (setTimeout forces all targets visible) |
| IC-REV-04 | reveal | required | behavioral | **pass** | reduced motion: gate applied=False, 0 tagged targets, 0 hidden |
| IC-ACC-01 | acc | required | static | **skip** | no accordion/disclosure details detected in this lane |
| IC-ACC-06 | acc | required | behavioral | **skip** | no accordion groups detected in this lane |
| IC-ACC-07 | acc | required | behavioral | **skip** | no accordion groups detected in this lane |
| IC-ACC-08 | acc | required | behavioral | **skip** | no accordion groups detected in this lane |
| IC-BAN-01 | banner | required | static | **skip** | no dismissible banner detected in this lane |
| IC-BAN-04 | banner | required | behavioral | **skip** | no dismissible banner detected in this lane |
| IC-CAR-01 | carousel | required | static | **skip** | no carousel/edge-cut rail detected in this lane |
| IC-CAR-05 | carousel | required | behavioral | **skip** | no carousel/edge-cut rail detected in this lane |
| IC-FORM-01 | form | required | static | **skip** | no form controls or labels detected in this lane |
| IC-FORM-07 | form | required | behavioral | **skip** | no form controls detected in this lane |
| IC-LANG-03 | lang | required | static | **skip** | disclosure-navigation menu (plain nav links, no selection concept) — selection marking not applicable |
| IC-MARQ-01 | marquee | required | static | **skip** | no marquee detected in this lane |
| IC-MARQ-03 | marquee | required | behavioral | **skip** | no marquee detected in this lane |
| IC-TAB-01 | tabs | required | static | **skip** | no tab devices detected in this lane |
| IC-TAB-05 | tabs | required | behavioral | **skip** | no tab devices detected in this lane |
| IC-TAB-06 | tabs | required | behavioral | **skip** | no tab devices detected in this lane |

