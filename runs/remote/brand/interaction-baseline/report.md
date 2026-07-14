# Interaction-Contract Baseline Report

Generated: 2026-07-14T14:54:56+00:00 — auditor v1.0.0 — mode: strict
Contracts: `brand_pipeline/spec/interaction-contracts.md` (WAI-ARIA APG primary; Base UI secondary; Radix tertiary)

## Audited lanes

| lane | file | mtime (UTC) | sha256/12 |
|---|---|---|---|
| compose/hero-archetypes/homepage | `/Users/stanchev/Webflow/campaigns-hackathon/design-system-extractor-mine/runs/hubspot-v2/brand/compose/hero-archetypes/homepage/index.html` | 2026-07-14T14:33:37+00:00 | `ceb928e778c1` |
| compose/hero-archetypes/pricing | `/Users/stanchev/Webflow/campaigns-hackathon/design-system-extractor-mine/runs/hubspot-v2/brand/compose/hero-archetypes/pricing/index.html` | 2026-07-14T14:33:52+00:00 | `55a359d3452a` |
| compose/hero-archetypes/product | `/Users/stanchev/Webflow/campaigns-hackathon/design-system-extractor-mine/runs/hubspot-v2/brand/compose/hero-archetypes/product/index.html` | 2026-07-14T14:34:07+00:00 | `fa274ae72795` |
| compose/hero-archetypes/about | `/Users/stanchev/Webflow/campaigns-hackathon/design-system-extractor-mine/runs/hubspot-v2/brand/compose/hero-archetypes/about/index.html` | 2026-07-14T14:34:23+00:00 | `e6ae9fb95298` |
| compose/hero-archetypes/blog | `/Users/stanchev/Webflow/campaigns-hackathon/design-system-extractor-mine/runs/hubspot-v2/brand/compose/hero-archetypes/blog/index.html` | 2026-07-14T14:51:38+00:00 | `33d47aa1a912` |
| compose/hero-archetypes/demo | `/Users/stanchev/Webflow/campaigns-hackathon/design-system-extractor-mine/runs/hubspot-v2/brand/compose/hero-archetypes/demo/index.html` | 2026-07-14T14:51:54+00:00 | `61dc80aea65d` |
| compose/hero-archetypes/developer | `/Users/stanchev/Webflow/campaigns-hackathon/design-system-extractor-mine/runs/hubspot-v2/brand/compose/hero-archetypes/developer/index.html` | 2026-07-14T14:35:11+00:00 | `33d70b01b12f` |
| compose/hero-archetypes/event | `/Users/stanchev/Webflow/campaigns-hackathon/design-system-extractor-mine/runs/hubspot-v2/brand/compose/hero-archetypes/event/index.html` | 2026-07-14T14:35:28+00:00 | `0dd0905f530b` |
| compose/replica | `/Users/stanchev/Webflow/campaigns-hackathon/design-system-extractor-mine/runs/hubspot-v2/brand/compose/replica/index.html` | 2026-07-14T14:36:56+00:00 | `681b67252956` |
| compose/replica | `/Users/stanchev/Webflow/campaigns-hackathon/design-system-extractor-mine/runs/remote/brand/compose/replica/index.html` | 2026-07-14T14:37:11+00:00 | `59d693dedf42` |
| compose/event-genlaunch | `/Users/stanchev/Webflow/campaigns-hackathon/design-system-extractor-mine/runs/remote/brand/compose/event-genlaunch/index.html` | 2026-07-14T14:36:48+00:00 | `0e68c90d8999` |

If a lane is re-rendered by another agent, re-run the audit; the mtime/sha above identify exactly which HTML was measured.

## Summary — 0 failing required cells, 13 advisory, 215 passing, 134 skipped

### Most impactful gaps (required checks failing, by lane count)

- none — all required checks pass

## Lane: compose/hero-archetypes/homepage

| check | family | severity | layer | status | detail |
|---|---|---|---|---|---|
| IC-NAV-05 | nav | advisory | static | **advisory** | anchor with role=button in nav chrome — promises Space activation anchors don't have (line 2223) |
| IC-LANG-01 | lang | required | static | **pass** | toggle is a native <summary> inside <details> (line 2213) |
| IC-LANG-02 | lang | required | static | **pass** | toggle has an accessible name (line 2213) |
| IC-LANG-05 | lang | required | behavioral | **pass** | Enter opens (open=True), Space toggles back=True |
| IC-LANG-06 | lang | required | behavioral | **pass** | Escape closes the language dropdown |
| IC-LANG-07 | lang | advisory | behavioral | **pass** | open dropdown items are in the Tab order |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Products' is a native button (line 2217) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Solutions' is a native button (line 2219) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Resources' is a native button (line 2221) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Products' carries aria-expanded (line 2217) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Solutions' carries aria-expanded (line 2219) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Resources' carries aria-expanded (line 2221) |
| IC-NAV-03 | nav | required | static | **pass** | no ARIA menu/menubar roles in site nav |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2217) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2219) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2221) |
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
| IC-NAV-05 | nav | advisory | static | **advisory** | anchor with role=button in nav chrome — promises Space activation anchors don't have (line 2230) |
| IC-LANG-01 | lang | required | static | **pass** | toggle is a native <summary> inside <details> (line 2220) |
| IC-LANG-02 | lang | required | static | **pass** | toggle has an accessible name (line 2220) |
| IC-LANG-05 | lang | required | behavioral | **pass** | Enter opens (open=True), Space toggles back=True |
| IC-LANG-06 | lang | required | behavioral | **pass** | Escape closes the language dropdown |
| IC-LANG-07 | lang | advisory | behavioral | **pass** | open dropdown items are in the Tab order |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Products' is a native button (line 2224) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Solutions' is a native button (line 2226) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Resources' is a native button (line 2228) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Products' carries aria-expanded (line 2224) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Solutions' carries aria-expanded (line 2226) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Resources' carries aria-expanded (line 2228) |
| IC-NAV-03 | nav | required | static | **pass** | no ARIA menu/menubar roles in site nav |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2224) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2226) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2228) |
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
| IC-NAV-05 | nav | advisory | static | **advisory** | anchor with role=button in nav chrome — promises Space activation anchors don't have (line 2226) |
| IC-LANG-01 | lang | required | static | **pass** | toggle is a native <summary> inside <details> (line 2216) |
| IC-LANG-02 | lang | required | static | **pass** | toggle has an accessible name (line 2216) |
| IC-LANG-05 | lang | required | behavioral | **pass** | Enter opens (open=True), Space toggles back=True |
| IC-LANG-06 | lang | required | behavioral | **pass** | Escape closes the language dropdown |
| IC-LANG-07 | lang | advisory | behavioral | **pass** | open dropdown items are in the Tab order |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Products' is a native button (line 2220) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Solutions' is a native button (line 2222) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Resources' is a native button (line 2224) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Products' carries aria-expanded (line 2220) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Solutions' carries aria-expanded (line 2222) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Resources' carries aria-expanded (line 2224) |
| IC-NAV-03 | nav | required | static | **pass** | no ARIA menu/menubar roles in site nav |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2220) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2222) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2224) |
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
| IC-NAV-05 | nav | advisory | static | **advisory** | anchor with role=button in nav chrome — promises Space activation anchors don't have (line 2230) |
| IC-LANG-01 | lang | required | static | **pass** | toggle is a native <summary> inside <details> (line 2220) |
| IC-LANG-02 | lang | required | static | **pass** | toggle has an accessible name (line 2220) |
| IC-LANG-05 | lang | required | behavioral | **pass** | Enter opens (open=True), Space toggles back=True |
| IC-LANG-06 | lang | required | behavioral | **pass** | Escape closes the language dropdown |
| IC-LANG-07 | lang | advisory | behavioral | **pass** | open dropdown items are in the Tab order |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Products' is a native button (line 2224) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Solutions' is a native button (line 2226) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Resources' is a native button (line 2228) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Products' carries aria-expanded (line 2224) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Solutions' carries aria-expanded (line 2226) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Resources' carries aria-expanded (line 2228) |
| IC-NAV-03 | nav | required | static | **pass** | no ARIA menu/menubar roles in site nav |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2224) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2226) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2228) |
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
| IC-NAV-05 | nav | advisory | static | **advisory** | anchor with role=button in nav chrome — promises Space activation anchors don't have (line 2223) |
| IC-LANG-01 | lang | required | static | **pass** | toggle is a native <summary> inside <details> (line 2213) |
| IC-LANG-02 | lang | required | static | **pass** | toggle has an accessible name (line 2213) |
| IC-LANG-05 | lang | required | behavioral | **pass** | Enter opens (open=True), Space toggles back=True |
| IC-LANG-06 | lang | required | behavioral | **pass** | Escape closes the language dropdown |
| IC-LANG-07 | lang | advisory | behavioral | **pass** | open dropdown items are in the Tab order |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Products' is a native button (line 2217) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Solutions' is a native button (line 2219) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Resources' is a native button (line 2221) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Products' carries aria-expanded (line 2217) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Solutions' carries aria-expanded (line 2219) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Resources' carries aria-expanded (line 2221) |
| IC-NAV-03 | nav | required | static | **pass** | no ARIA menu/menubar roles in site nav |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2217) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2219) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2221) |
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
| IC-NAV-05 | nav | advisory | static | **advisory** | anchor with role=button in nav chrome — promises Space activation anchors don't have (line 2291) |
| IC-FORM-01 | form | required | static | **pass** | control 'hero-demo-first-name' is programmatically labelled (line 2311) |
| IC-FORM-01 | form | required | static | **pass** | control 'hero-demo-work-email' is programmatically labelled (line 2315) |
| IC-FORM-01 | form | required | static | **pass** | control 'hero-demo-company-size' is programmatically labelled (line 2319) |
| IC-FORM-02 | form | required | static | **pass** | form has a real submit button (line 2322) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 2310) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 2314) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 2318) |
| IC-FORM-07 | form | required | behavioral | **pass** | all visible form controls have browser-computed labels |
| IC-LANG-01 | lang | required | static | **pass** | toggle is a native <summary> inside <details> (line 2281) |
| IC-LANG-02 | lang | required | static | **pass** | toggle has an accessible name (line 2281) |
| IC-LANG-05 | lang | required | behavioral | **pass** | Enter opens (open=True), Space toggles back=True |
| IC-LANG-06 | lang | required | behavioral | **pass** | Escape closes the language dropdown |
| IC-LANG-07 | lang | advisory | behavioral | **pass** | open dropdown items are in the Tab order |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Products' is a native button (line 2285) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Solutions' is a native button (line 2287) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Resources' is a native button (line 2289) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Products' carries aria-expanded (line 2285) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Solutions' carries aria-expanded (line 2287) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Resources' carries aria-expanded (line 2289) |
| IC-NAV-03 | nav | required | static | **pass** | no ARIA menu/menubar roles in site nav |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2285) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2287) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2289) |
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
| IC-NAV-05 | nav | advisory | static | **advisory** | anchor with role=button in nav chrome — promises Space activation anchors don't have (line 2229) |
| IC-FORM-01 | form | required | static | **pass** | control 'text' is programmatically labelled (line 2239) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 2239) |
| IC-FORM-07 | form | required | behavioral | **pass** | all visible form controls have browser-computed labels |
| IC-LANG-01 | lang | required | static | **pass** | toggle is a native <summary> inside <details> (line 2219) |
| IC-LANG-02 | lang | required | static | **pass** | toggle has an accessible name (line 2219) |
| IC-LANG-05 | lang | required | behavioral | **pass** | Enter opens (open=True), Space toggles back=True |
| IC-LANG-06 | lang | required | behavioral | **pass** | Escape closes the language dropdown |
| IC-LANG-07 | lang | advisory | behavioral | **pass** | open dropdown items are in the Tab order |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Products' is a native button (line 2223) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Solutions' is a native button (line 2225) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Resources' is a native button (line 2227) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Products' carries aria-expanded (line 2223) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Solutions' carries aria-expanded (line 2225) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Resources' carries aria-expanded (line 2227) |
| IC-NAV-03 | nav | required | static | **pass** | no ARIA menu/menubar roles in site nav |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2223) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2225) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2227) |
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
| IC-NAV-05 | nav | advisory | static | **advisory** | anchor with role=button in nav chrome — promises Space activation anchors don't have (line 2230) |
| IC-LANG-01 | lang | required | static | **pass** | toggle is a native <summary> inside <details> (line 2220) |
| IC-LANG-02 | lang | required | static | **pass** | toggle has an accessible name (line 2220) |
| IC-LANG-05 | lang | required | behavioral | **pass** | Enter opens (open=True), Space toggles back=True |
| IC-LANG-06 | lang | required | behavioral | **pass** | Escape closes the language dropdown |
| IC-LANG-07 | lang | advisory | behavioral | **pass** | open dropdown items are in the Tab order |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Products' is a native button (line 2224) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Solutions' is a native button (line 2226) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Resources' is a native button (line 2228) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Products' carries aria-expanded (line 2224) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Solutions' carries aria-expanded (line 2226) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Resources' carries aria-expanded (line 2228) |
| IC-NAV-03 | nav | required | static | **pass** | no ARIA menu/menubar roles in site nav |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2224) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2226) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2228) |
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

## Lane: compose/replica

| check | family | severity | layer | status | detail |
|---|---|---|---|---|---|
| IC-CAR-03 | carousel | advisory | static | **advisory** | no slide-level group/roledescription semantics (line 3438) |
| IC-NAV-05 | nav | advisory | static | **advisory** | anchor with role=button in nav chrome — promises Space activation anchors don't have (line 3243) |
| IC-CAR-01 | carousel | required | static | **pass** | prev/next controls are buttons with accessible names (line 3465) |
| IC-CAR-01 | carousel | required | static | **pass** | prev/next controls are buttons with accessible names (line 3304) |
| IC-CAR-02 | carousel | advisory | static | **pass** | container has aria-roledescription=carousel and a label (line 3438) |
| IC-CAR-02 | carousel | advisory | static | **pass** | container has aria-roledescription=carousel and a label (line 3279) |
| IC-CAR-03 | carousel | advisory | static | **pass** | slide containers use role=group + aria-roledescription=slide (line 3279) |
| IC-LANG-01 | lang | required | static | **pass** | toggle is a native <summary> inside <details> (line 3233) |
| IC-LANG-02 | lang | required | static | **pass** | toggle has an accessible name (line 3233) |
| IC-LANG-05 | lang | required | behavioral | **pass** | Enter opens (open=True), Space toggles back=True |
| IC-LANG-06 | lang | required | behavioral | **pass** | Escape closes the language dropdown |
| IC-LANG-07 | lang | advisory | behavioral | **pass** | open dropdown items are in the Tab order |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Products' is a native button (line 3237) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Solutions' is a native button (line 3239) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Resources' is a native button (line 3241) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Products' carries aria-expanded (line 3237) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Solutions' carries aria-expanded (line 3239) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Resources' carries aria-expanded (line 3241) |
| IC-NAV-03 | nav | required | static | **pass** | no ARIA menu/menubar roles in site nav |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 3237) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 3239) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 3241) |
| IC-NAV-06 | nav | required | behavioral | **pass** | Tab reaches nav triggers, login, and language switcher |
| IC-NAV-07 | nav | required | behavioral | **pass** | hover opens panel=True, keyboard focus opens panel=True |
| IC-NAV-08 | nav | required | behavioral | **pass** | Escape closes the open panel and keeps focus in nav |
| IC-REV-01 | reveal | required | static | **pass** | hidden initial state is gated on a JS-added class (.cs-motion-ready .cs-reveal…) |
| IC-REV-02 | reveal | required | static | **pass** | prefers-reduced-motion forces reveal targets visible |
| IC-REV-03 | reveal | advisory | static | **pass** | timed failsafe present (setTimeout forces all targets visible) |
| IC-REV-04 | reveal | required | behavioral | **pass** | reduced motion: gate applied=False, 0 tagged targets, 0 hidden |
| IC-TAB-01 | tabs | required | static | **pass** | tabs are native buttons with exactly one aria-selected (line 3497) |
| IC-TAB-02 | tabs | required | static | **pass** | tab↔panel aria-controls/aria-labelledby wiring is two-way (line 3497) |
| IC-TAB-03 | tabs | required | static | **pass** | roving tabindex + single visible focusable panel (line 3497) |
| IC-TAB-04 | tabs | advisory | static | **pass** | tablist has an accessible name (line 3497) |
| IC-TAB-05 | tabs | required | behavioral | **pass** | ArrowRight/ArrowLeft move focus and selection; the visible panel follows |
| IC-TAB-06 | tabs | required | behavioral | **pass** | Home/End jump selection; click selects (pointer parity) |
| IC-ACC-01 | acc | required | static | **skip** | no accordion/disclosure details detected in this lane |
| IC-ACC-06 | acc | required | behavioral | **skip** | no accordion groups detected in this lane |
| IC-ACC-07 | acc | required | behavioral | **skip** | no accordion groups detected in this lane |
| IC-ACC-08 | acc | required | behavioral | **skip** | no accordion groups detected in this lane |
| IC-BAN-01 | banner | required | static | **skip** | no dismissible banner detected in this lane |
| IC-BAN-04 | banner | required | behavioral | **skip** | no dismissible banner detected in this lane |
| IC-CAR-04 | carousel | advisory | static | **skip** | no auto-rotation on this rail — pause-control contract not applicable (line 3438) |
| IC-CAR-04 | carousel | advisory | static | **skip** | no auto-rotation on this rail — pause-control contract not applicable (line 3279) |
| IC-CAR-05 | carousel | required | behavioral | **skip** | rail does not overflow at this viewport; keyboard-scroll probe not applicable |
| IC-FORM-01 | form | required | static | **skip** | no form controls or labels detected in this lane |
| IC-FORM-07 | form | required | behavioral | **skip** | no form controls detected in this lane |
| IC-LANG-03 | lang | required | static | **skip** | disclosure-navigation menu (plain nav links, no selection concept) — selection marking not applicable |
| IC-MARQ-01 | marquee | required | static | **skip** | no marquee detected in this lane |
| IC-MARQ-03 | marquee | required | behavioral | **skip** | no marquee detected in this lane |

## Lane: compose/replica

| check | family | severity | layer | status | detail |
|---|---|---|---|---|---|
| IC-CAR-03 | carousel | advisory | static | **advisory** | no slide-level group/roledescription semantics (line 3418) |
| IC-NAV-05 | nav | advisory | static | **advisory** | anchor with role=button in nav chrome — promises Space activation anchors don't have (line 3256) |
| IC-ACC-01 | acc | required | static | **pass** | group of 5 details shares name="acc-feature-accordion" (exclusive single-open) (line 3317) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 3317) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 3322) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 3326) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 3330) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 3334) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 3318) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 3323) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 3327) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 3331) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 3335) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 3318) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 3323) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 3327) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 3331) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 3335) |
| IC-ACC-05 | acc | advisory | static | **pass** | 1 item(s) authored open (line 3317) |
| IC-ACC-06 | acc | required | behavioral | **pass** | summary focusable; Enter and Space toggle the panel |
| IC-ACC-07 | acc | required | behavioral | **pass** | group 0 (named, 5 items): opening item 2 closes item 1 (exclusive group holds) |
| IC-ACC-08 | acc | required | behavioral | **pass** | opened panel content is rendered and visible |
| IC-BAN-01 | banner | required | static | **pass** | close control is a native button (line 3253) |
| IC-BAN-02 | banner | required | static | **pass** | close control has an accessible name (line 3253) |
| IC-BAN-03 | banner | advisory | static | **pass** | icon inside close control is aria-hidden (line 3253) |
| IC-BAN-04 | banner | required | behavioral | **pass** | keyboard activation dismisses the banner |
| IC-CAR-01 | carousel | required | static | **pass** | rail is an accessible keyboard-scrollable region (line 3418) |
| IC-CAR-02 | carousel | advisory | static | **pass** | container has aria-roledescription=carousel and a label (line 3418) |
| IC-CAR-05 | carousel | required | behavioral | **pass** | rail focusable; ArrowRight scrolls: 0->142 |
| IC-LANG-01 | lang | required | static | **pass** | toggle is a native <summary> inside <details> (line 3256) |
| IC-LANG-02 | lang | required | static | **pass** | toggle has an accessible name (line 3256) |
| IC-LANG-03 | lang | required | static | **pass** | current selection marked via aria-current/aria-selected (line 3256) |
| IC-LANG-04 | lang | advisory | static | **pass** | locale items are links carrying hreflang (line 3256) |
| IC-LANG-05 | lang | required | behavioral | **pass** | Enter opens (open=True), Space toggles back=True |
| IC-LANG-06 | lang | required | behavioral | **pass** | Escape closes the language dropdown |
| IC-LANG-07 | lang | advisory | behavioral | **pass** | open dropdown items are in the Tab order |
| IC-MARQ-01 | marquee | required | static | **pass** | duplicated seam half is aria-hidden (line 3290) |
| IC-MARQ-02 | marquee | required | static | **pass** | prefers-reduced-motion neutralizes the marquee animation (line 3274) |
| IC-MARQ-03 | marquee | required | behavioral | **pass** | reduced motion: animation=none/running, content visible=True |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Products' is a native button (line 3256) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Solutions' is a native button (line 3256) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Resources' is a native button (line 3256) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Products' carries aria-expanded (line 3256) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Solutions' carries aria-expanded (line 3256) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Resources' carries aria-expanded (line 3256) |
| IC-NAV-03 | nav | required | static | **pass** | no ARIA menu/menubar roles in site nav |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 3256) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 3256) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 3256) |
| IC-NAV-06 | nav | required | behavioral | **pass** | Tab reaches nav triggers, login, and language switcher |
| IC-NAV-07 | nav | required | behavioral | **pass** | hover opens panel=True, keyboard focus opens panel=True |
| IC-NAV-08 | nav | required | behavioral | **pass** | Escape closes the open panel and keeps focus in nav |
| IC-REV-01 | reveal | required | static | **pass** | hidden initial state is gated on a JS-added class (.cs-motion-ready .cs-reveal…) |
| IC-REV-02 | reveal | required | static | **pass** | prefers-reduced-motion forces reveal targets visible |
| IC-REV-03 | reveal | advisory | static | **pass** | timed failsafe present (setTimeout forces all targets visible) |
| IC-REV-04 | reveal | required | behavioral | **pass** | reduced motion: gate applied=False, 0 tagged targets, 0 hidden |
| IC-CAR-04 | carousel | advisory | static | **skip** | no auto-rotation on this rail — pause-control contract not applicable (line 3418) |
| IC-FORM-01 | form | required | static | **skip** | no form controls or labels detected in this lane |
| IC-FORM-07 | form | required | behavioral | **skip** | no form controls detected in this lane |
| IC-TAB-01 | tabs | required | static | **skip** | no tab devices detected in this lane |
| IC-TAB-05 | tabs | required | behavioral | **skip** | no tab devices detected in this lane |
| IC-TAB-06 | tabs | required | behavioral | **skip** | no tab devices detected in this lane |

## Lane: compose/event-genlaunch

| check | family | severity | layer | status | detail |
|---|---|---|---|---|---|
| IC-FORM-05 | form | advisory | static | **advisory** | field help text not linked to its control via aria-describedby (line 3346) |
| IC-FORM-06 | form | advisory | static | **advisory** | error copy lives only in data-error attributes — invisible to AT (line 3341) |
| IC-NAV-05 | nav | advisory | static | **advisory** | anchor with role=button in nav chrome — promises Space activation anchors don't have (line 3150) |
| IC-ACC-01 | acc | required | static | **pass** | group of 4 details shares name="faq-event-agenda" (exclusive single-open) (line 3255) |
| IC-ACC-01 | acc | required | static | **pass** | group of 6 details shares name="faq-event-faq" (exclusive single-open) (line 3326) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 3255) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 3255) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 3255) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 3255) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 3326) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 3326) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 3326) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 3326) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 3326) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 3326) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 3255) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 3255) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 3255) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 3255) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 3326) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 3326) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 3326) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 3326) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 3326) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 3326) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 3255) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 3255) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 3255) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 3255) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 3326) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 3326) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 3326) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 3326) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 3326) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 3326) |
| IC-ACC-05 | acc | advisory | static | **pass** | 1 item(s) authored open (line 3255) |
| IC-ACC-05 | acc | advisory | static | **pass** | 1 item(s) authored open (line 3326) |
| IC-ACC-06 | acc | required | behavioral | **pass** | summary focusable; Enter and Space toggle the panel |
| IC-ACC-07 | acc | required | behavioral | **pass** | group 0 (named, 4 items): opening item 2 closes item 1 (exclusive group holds) |
| IC-ACC-08 | acc | required | behavioral | **pass** | opened panel content is rendered and visible |
| IC-BAN-01 | banner | required | static | **pass** | close control is a native button (line 3147) |
| IC-BAN-02 | banner | required | static | **pass** | close control has an accessible name (line 3147) |
| IC-BAN-03 | banner | advisory | static | **pass** | icon inside close control is aria-hidden (line 3147) |
| IC-BAN-04 | banner | required | behavioral | **pass** | keyboard activation dismisses the banner |
| IC-FORM-01 | form | required | static | **pass** | control 'event-signup-full-name' is programmatically labelled (line 3341) |
| IC-FORM-01 | form | required | static | **pass** | control 'event-signup-work-email' is programmatically labelled (line 3345) |
| IC-FORM-01 | form | required | static | **pass** | control 'event-signup-company' is programmatically labelled (line 3350) |
| IC-FORM-01 | form | required | static | **pass** | control 'event-signup-company-size' is programmatically labelled (line 3354) |
| IC-FORM-01 | form | required | static | **pass** | control 'event-signup-role' is programmatically labelled (line 3365) |
| IC-FORM-01 | form | required | static | **pass** | control 'pass' is programmatically labelled (line 3377) |
| IC-FORM-01 | form | required | static | **pass** | control 'pass' is programmatically labelled (line 3378) |
| IC-FORM-01 | form | required | static | **pass** | control 'pass' is programmatically labelled (line 3379) |
| IC-FORM-01 | form | required | static | **pass** | control 'product-news' is programmatically labelled (line 3382) |
| IC-FORM-02 | form | required | static | **pass** | form has a real submit button (line 3385) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 3340) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 3344) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 3349) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 3353) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 3364) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 3377) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 3378) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 3379) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 3382) |
| IC-FORM-04 | form | required | static | **pass** | fields with error copy communicate requiredness programmatically (line 3341) |
| IC-FORM-07 | form | required | behavioral | **pass** | all visible form controls have browser-computed labels |
| IC-LANG-01 | lang | required | static | **pass** | toggle is a native <summary> inside <details> (line 3150) |
| IC-LANG-02 | lang | required | static | **pass** | toggle has an accessible name (line 3150) |
| IC-LANG-03 | lang | required | static | **pass** | current selection marked via aria-current/aria-selected (line 3150) |
| IC-LANG-04 | lang | advisory | static | **pass** | locale items are links carrying hreflang (line 3150) |
| IC-LANG-05 | lang | required | behavioral | **pass** | Enter opens (open=True), Space toggles back=True |
| IC-LANG-06 | lang | required | behavioral | **pass** | Escape closes the language dropdown |
| IC-LANG-07 | lang | advisory | behavioral | **pass** | open dropdown items are in the Tab order |
| IC-MARQ-01 | marquee | required | static | **pass** | duplicated seam half is aria-hidden (line 3185) |
| IC-MARQ-02 | marquee | required | static | **pass** | prefers-reduced-motion neutralizes the marquee animation (line 3169) |
| IC-MARQ-03 | marquee | required | behavioral | **pass** | reduced motion: animation=none/running, content visible=True |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Products' is a native button (line 3150) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Solutions' is a native button (line 3150) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Resources' is a native button (line 3150) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Products' carries aria-expanded (line 3150) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Solutions' carries aria-expanded (line 3150) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Resources' carries aria-expanded (line 3150) |
| IC-NAV-03 | nav | required | static | **pass** | no ARIA menu/menubar roles in site nav |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 3150) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 3150) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 3150) |
| IC-NAV-06 | nav | required | behavioral | **pass** | Tab reaches nav triggers, login, and language switcher |
| IC-NAV-07 | nav | required | behavioral | **pass** | hover opens panel=True, keyboard focus opens panel=True |
| IC-NAV-08 | nav | required | behavioral | **pass** | Escape closes the open panel and keeps focus in nav |
| IC-REV-01 | reveal | required | static | **pass** | hidden initial state is gated on a JS-added class (.cs-motion-ready .cs-reveal…) |
| IC-REV-02 | reveal | required | static | **pass** | prefers-reduced-motion forces reveal targets visible |
| IC-REV-03 | reveal | advisory | static | **pass** | timed failsafe present (setTimeout forces all targets visible) |
| IC-REV-04 | reveal | required | behavioral | **pass** | reduced motion: gate applied=False, 0 tagged targets, 0 hidden |
| IC-CAR-01 | carousel | required | static | **skip** | no carousel/edge-cut rail detected in this lane |
| IC-CAR-05 | carousel | required | behavioral | **skip** | no carousel/edge-cut rail detected in this lane |
| IC-TAB-01 | tabs | required | static | **skip** | no tab devices detected in this lane |
| IC-TAB-05 | tabs | required | behavioral | **skip** | no tab devices detected in this lane |
| IC-TAB-06 | tabs | required | behavioral | **skip** | no tab devices detected in this lane |

