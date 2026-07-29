# Interaction-Contract Baseline Report

Generated: 2026-07-28T23:58:21+00:00 — auditor v1.0.0 — mode: strict
Contracts: `brand_pipeline/spec/interaction-contracts.md` (WAI-ARIA APG primary; Base UI secondary; Radix tertiary)

## Audited lanes

| lane | file | mtime (UTC) | sha256/12 |
|---|---|---|---|
| compose/hero-archetypes/homepage | `runs/hubspot-v2/brand/compose/hero-archetypes/homepage/index.html` | 2026-07-14T20:03:36+00:00 | `964811d8232f` |
| compose/hero-archetypes/pricing | `runs/hubspot-v2/brand/compose/hero-archetypes/pricing/index.html` | 2026-07-14T20:03:52+00:00 | `adf22ee338af` |
| compose/hero-archetypes/product | `runs/hubspot-v2/brand/compose/hero-archetypes/product/index.html` | 2026-07-14T20:04:08+00:00 | `b4969618ae3e` |
| compose/hero-archetypes/about | `runs/hubspot-v2/brand/compose/hero-archetypes/about/index.html` | 2026-07-14T20:04:24+00:00 | `5ccf31e93fd1` |
| compose/hero-archetypes/blog | `runs/hubspot-v2/brand/compose/hero-archetypes/blog/index.html` | 2026-07-14T20:04:41+00:00 | `bfda09b535c2` |
| compose/hero-archetypes/demo | `runs/hubspot-v2/brand/compose/hero-archetypes/demo/index.html` | 2026-07-14T20:04:58+00:00 | `6be813ca88b5` |
| compose/hero-archetypes/developer | `runs/hubspot-v2/brand/compose/hero-archetypes/developer/index.html` | 2026-07-14T20:05:15+00:00 | `5b0d343f96cb` |
| compose/hero-archetypes/event | `runs/hubspot-v2/brand/compose/hero-archetypes/event/index.html` | 2026-07-14T20:05:33+00:00 | `c95790bf3283` |

If a lane is re-rendered by another agent, re-run the audit; the mtime/sha above identify exactly which HTML was measured.

## Summary — 0 failing required cells, 8 advisory, 135 passing, 126 skipped

### Most impactful gaps (required checks failing, by lane count)

- none — all required checks pass

## Lane: compose/hero-archetypes/homepage

| check | family | severity | layer | status | detail |
|---|---|---|---|---|---|
| IC-NAV-05 | nav | advisory | static | **advisory** | anchor with role=button in nav chrome — promises Space activation anchors don't have (line 2282) |
| IC-LANG-01 | lang | required | static | **pass** | toggle is a native <summary> inside <details> (line 2272) |
| IC-LANG-02 | lang | required | static | **pass** | toggle has an accessible name (line 2272) |
| IC-LANG-05 | lang | required | behavioral | **pass** | Enter opens (open=True), Space toggles back=True |
| IC-LANG-06 | lang | required | behavioral | **pass** | Escape closes the language dropdown |
| IC-LANG-07 | lang | advisory | behavioral | **pass** | open dropdown items are in the Tab order |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Products' is a native button (line 2276) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Solutions' is a native button (line 2278) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Resources' is a native button (line 2280) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Products' carries aria-expanded (line 2276) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Solutions' carries aria-expanded (line 2278) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Resources' carries aria-expanded (line 2280) |
| IC-NAV-03 | nav | required | static | **pass** | no ARIA menu/menubar roles in site nav |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2276) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2278) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2280) |
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

## Lane: compose/hero-archetypes/pricing

| check | family | severity | layer | status | detail |
|---|---|---|---|---|---|
| IC-NAV-05 | nav | advisory | static | **advisory** | anchor with role=button in nav chrome — promises Space activation anchors don't have (line 2288) |
| IC-LANG-01 | lang | required | static | **pass** | toggle is a native <summary> inside <details> (line 2278) |
| IC-LANG-02 | lang | required | static | **pass** | toggle has an accessible name (line 2278) |
| IC-LANG-05 | lang | required | behavioral | **pass** | Enter opens (open=True), Space toggles back=True |
| IC-LANG-06 | lang | required | behavioral | **pass** | Escape closes the language dropdown |
| IC-LANG-07 | lang | advisory | behavioral | **pass** | open dropdown items are in the Tab order |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Products' is a native button (line 2282) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Solutions' is a native button (line 2284) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Resources' is a native button (line 2286) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Products' carries aria-expanded (line 2282) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Solutions' carries aria-expanded (line 2284) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Resources' carries aria-expanded (line 2286) |
| IC-NAV-03 | nav | required | static | **pass** | no ARIA menu/menubar roles in site nav |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2282) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2284) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2286) |
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

## Lane: compose/hero-archetypes/product

| check | family | severity | layer | status | detail |
|---|---|---|---|---|---|
| IC-NAV-05 | nav | advisory | static | **advisory** | anchor with role=button in nav chrome — promises Space activation anchors don't have (line 2284) |
| IC-LANG-01 | lang | required | static | **pass** | toggle is a native <summary> inside <details> (line 2274) |
| IC-LANG-02 | lang | required | static | **pass** | toggle has an accessible name (line 2274) |
| IC-LANG-05 | lang | required | behavioral | **pass** | Enter opens (open=True), Space toggles back=True |
| IC-LANG-06 | lang | required | behavioral | **pass** | Escape closes the language dropdown |
| IC-LANG-07 | lang | advisory | behavioral | **pass** | open dropdown items are in the Tab order |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Products' is a native button (line 2278) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Solutions' is a native button (line 2280) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Resources' is a native button (line 2282) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Products' carries aria-expanded (line 2278) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Solutions' carries aria-expanded (line 2280) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Resources' carries aria-expanded (line 2282) |
| IC-NAV-03 | nav | required | static | **pass** | no ARIA menu/menubar roles in site nav |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2278) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2280) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2282) |
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

## Lane: compose/hero-archetypes/about

| check | family | severity | layer | status | detail |
|---|---|---|---|---|---|
| IC-NAV-05 | nav | advisory | static | **advisory** | anchor with role=button in nav chrome — promises Space activation anchors don't have (line 2289) |
| IC-LANG-01 | lang | required | static | **pass** | toggle is a native <summary> inside <details> (line 2279) |
| IC-LANG-02 | lang | required | static | **pass** | toggle has an accessible name (line 2279) |
| IC-LANG-05 | lang | required | behavioral | **pass** | Enter opens (open=True), Space toggles back=True |
| IC-LANG-06 | lang | required | behavioral | **pass** | Escape closes the language dropdown |
| IC-LANG-07 | lang | advisory | behavioral | **pass** | open dropdown items are in the Tab order |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Products' is a native button (line 2283) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Solutions' is a native button (line 2285) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Resources' is a native button (line 2287) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Products' carries aria-expanded (line 2283) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Solutions' carries aria-expanded (line 2285) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Resources' carries aria-expanded (line 2287) |
| IC-NAV-03 | nav | required | static | **pass** | no ARIA menu/menubar roles in site nav |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2283) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2285) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2287) |
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

## Lane: compose/hero-archetypes/blog

| check | family | severity | layer | status | detail |
|---|---|---|---|---|---|
| IC-NAV-05 | nav | advisory | static | **advisory** | anchor with role=button in nav chrome — promises Space activation anchors don't have (line 2282) |
| IC-LANG-01 | lang | required | static | **pass** | toggle is a native <summary> inside <details> (line 2272) |
| IC-LANG-02 | lang | required | static | **pass** | toggle has an accessible name (line 2272) |
| IC-LANG-05 | lang | required | behavioral | **pass** | Enter opens (open=True), Space toggles back=True |
| IC-LANG-06 | lang | required | behavioral | **pass** | Escape closes the language dropdown |
| IC-LANG-07 | lang | advisory | behavioral | **pass** | open dropdown items are in the Tab order |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Products' is a native button (line 2276) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Solutions' is a native button (line 2278) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Resources' is a native button (line 2280) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Products' carries aria-expanded (line 2276) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Solutions' carries aria-expanded (line 2278) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Resources' carries aria-expanded (line 2280) |
| IC-NAV-03 | nav | required | static | **pass** | no ARIA menu/menubar roles in site nav |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2276) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2278) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2280) |
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

## Lane: compose/hero-archetypes/demo

| check | family | severity | layer | status | detail |
|---|---|---|---|---|---|
| IC-NAV-05 | nav | advisory | static | **advisory** | anchor with role=button in nav chrome — promises Space activation anchors don't have (line 2349) |
| IC-FORM-01 | form | required | static | **pass** | control 'demo-hero-first-name' is programmatically labelled (line 2375) |
| IC-FORM-01 | form | required | static | **pass** | control 'demo-hero-work-email' is programmatically labelled (line 2379) |
| IC-FORM-01 | form | required | static | **pass** | control 'demo-hero-company-size' is programmatically labelled (line 2383) |
| IC-FORM-02 | form | required | static | **pass** | form has a real submit button (line 2386) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 2374) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 2378) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 2382) |
| IC-FORM-07 | form | required | behavioral | **pass** | all visible form controls have browser-computed labels |
| IC-LANG-01 | lang | required | static | **pass** | toggle is a native <summary> inside <details> (line 2339) |
| IC-LANG-02 | lang | required | static | **pass** | toggle has an accessible name (line 2339) |
| IC-LANG-05 | lang | required | behavioral | **pass** | Enter opens (open=True), Space toggles back=True |
| IC-LANG-06 | lang | required | behavioral | **pass** | Escape closes the language dropdown |
| IC-LANG-07 | lang | advisory | behavioral | **pass** | open dropdown items are in the Tab order |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Products' is a native button (line 2343) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Solutions' is a native button (line 2345) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Resources' is a native button (line 2347) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Products' carries aria-expanded (line 2343) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Solutions' carries aria-expanded (line 2345) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Resources' carries aria-expanded (line 2347) |
| IC-NAV-03 | nav | required | static | **pass** | no ARIA menu/menubar roles in site nav |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2343) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2345) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2347) |
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
| IC-FORM-04 | form | required | static | **skip** | no required-field signals detected in this lane |
| IC-LANG-03 | lang | required | static | **skip** | disclosure-navigation menu (plain nav links, no selection concept) — selection marking not applicable |
| IC-MARQ-01 | marquee | required | static | **skip** | no marquee detected in this lane |
| IC-MARQ-03 | marquee | required | behavioral | **skip** | no marquee detected in this lane |
| IC-TAB-01 | tabs | required | static | **skip** | no tab devices detected in this lane |
| IC-TAB-05 | tabs | required | behavioral | **skip** | no tab devices detected in this lane |
| IC-TAB-06 | tabs | required | behavioral | **skip** | no tab devices detected in this lane |

## Lane: compose/hero-archetypes/developer

| check | family | severity | layer | status | detail |
|---|---|---|---|---|---|
| IC-NAV-05 | nav | advisory | static | **advisory** | anchor with role=button in nav chrome — promises Space activation anchors don't have (line 2288) |
| IC-FORM-01 | form | required | static | **pass** | control 'text' is programmatically labelled (line 2298) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 2298) |
| IC-FORM-07 | form | required | behavioral | **pass** | all visible form controls have browser-computed labels |
| IC-LANG-01 | lang | required | static | **pass** | toggle is a native <summary> inside <details> (line 2278) |
| IC-LANG-02 | lang | required | static | **pass** | toggle has an accessible name (line 2278) |
| IC-LANG-05 | lang | required | behavioral | **pass** | Enter opens (open=True), Space toggles back=True |
| IC-LANG-06 | lang | required | behavioral | **pass** | Escape closes the language dropdown |
| IC-LANG-07 | lang | advisory | behavioral | **pass** | open dropdown items are in the Tab order |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Products' is a native button (line 2282) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Solutions' is a native button (line 2284) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Resources' is a native button (line 2286) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Products' carries aria-expanded (line 2282) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Solutions' carries aria-expanded (line 2284) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Resources' carries aria-expanded (line 2286) |
| IC-NAV-03 | nav | required | static | **pass** | no ARIA menu/menubar roles in site nav |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2282) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2284) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2286) |
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
| IC-FORM-04 | form | required | static | **skip** | no required-field signals detected in this lane |
| IC-LANG-03 | lang | required | static | **skip** | disclosure-navigation menu (plain nav links, no selection concept) — selection marking not applicable |
| IC-MARQ-01 | marquee | required | static | **skip** | no marquee detected in this lane |
| IC-MARQ-03 | marquee | required | behavioral | **skip** | no marquee detected in this lane |
| IC-TAB-01 | tabs | required | static | **skip** | no tab devices detected in this lane |
| IC-TAB-05 | tabs | required | behavioral | **skip** | no tab devices detected in this lane |
| IC-TAB-06 | tabs | required | behavioral | **skip** | no tab devices detected in this lane |

## Lane: compose/hero-archetypes/event

| check | family | severity | layer | status | detail |
|---|---|---|---|---|---|
| IC-NAV-05 | nav | advisory | static | **advisory** | anchor with role=button in nav chrome — promises Space activation anchors don't have (line 2288) |
| IC-LANG-01 | lang | required | static | **pass** | toggle is a native <summary> inside <details> (line 2278) |
| IC-LANG-02 | lang | required | static | **pass** | toggle has an accessible name (line 2278) |
| IC-LANG-05 | lang | required | behavioral | **pass** | Enter opens (open=True), Space toggles back=True |
| IC-LANG-06 | lang | required | behavioral | **pass** | Escape closes the language dropdown |
| IC-LANG-07 | lang | advisory | behavioral | **pass** | open dropdown items are in the Tab order |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Products' is a native button (line 2282) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Solutions' is a native button (line 2284) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Resources' is a native button (line 2286) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Products' carries aria-expanded (line 2282) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Solutions' carries aria-expanded (line 2284) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Resources' carries aria-expanded (line 2286) |
| IC-NAV-03 | nav | required | static | **pass** | no ARIA menu/menubar roles in site nav |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2282) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2284) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2286) |
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

