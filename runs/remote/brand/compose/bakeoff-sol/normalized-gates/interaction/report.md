# Interaction-Contract Baseline Report

Generated: 2026-07-10T19:05:29+00:00 — auditor v1.0.0 — mode: strict
Contracts: `brand_pipeline/spec/interaction-contracts.md` (WAI-ARIA APG primary; Base UI secondary; Radix tertiary)

## Audited lanes

| lane | file | mtime (UTC) | sha256/12 |
|---|---|---|---|
| compose/bakeoff-sol | `/Users/stanchev/Webflow/campaigns-hackathon/design-system-extractor-mine/runs/remote/brand/compose/bakeoff-sol/index.html` | 2026-07-10T19:01:40+00:00 | `47eb2489d73a` |

If a lane is re-rendered by another agent, re-run the audit; the mtime/sha above identify exactly which HTML was measured.

## Summary — 0 failing required cells, 2 advisory, 37 passing, 4 skipped

### Most impactful gaps (required checks failing, by lane count)

- none — all required checks pass

## Lane: compose/bakeoff-sol

| check | family | severity | layer | status | detail |
|---|---|---|---|---|---|
| IC-CAR-03 | carousel | advisory | static | **advisory** | no slide-level group/roledescription semantics (line 3108) |
| IC-NAV-05 | nav | advisory | static | **advisory** | anchor with role=button in nav chrome — promises Space activation anchors don't have (line 2949) |
| IC-ACC-01 | acc | required | static | **pass** | group of 4 details shares name="acc-decision-layer-capabilities" (exclusive single-open) (line 3003) |
| IC-ACC-01 | acc | required | static | **pass** | group of 5 details shares name="faq-workforce-intelligence-faq" (exclusive single-open) (line 3141) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 3003) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 3008) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 3012) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 3016) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 3141) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 3141) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 3141) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 3141) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 3141) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 3004) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 3009) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 3013) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 3017) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 3141) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 3141) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 3141) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 3141) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 3141) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 3004) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 3009) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 3013) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 3017) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 3141) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 3141) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 3141) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 3141) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 3141) |
| IC-ACC-05 | acc | advisory | static | **pass** | 1 item(s) authored open (line 3003) |
| IC-ACC-05 | acc | advisory | static | **pass** | 1 item(s) authored open (line 3141) |
| IC-ACC-06 | acc | required | behavioral | **pass** | summary focusable; Enter and Space toggle the panel |
| IC-ACC-07 | acc | required | behavioral | **pass** | group 0 (named, 4 items): opening item 2 closes item 1 (exclusive group holds) |
| IC-ACC-08 | acc | required | behavioral | **pass** | opened panel content is rendered and visible |
| IC-BAN-01 | banner | required | static | **pass** | close control is a native button (line 2946) |
| IC-BAN-02 | banner | required | static | **pass** | close control has an accessible name (line 2946) |
| IC-BAN-03 | banner | advisory | static | **pass** | icon inside close control is aria-hidden (line 2946) |
| IC-BAN-04 | banner | required | behavioral | **pass** | keyboard activation dismisses the banner |
| IC-CAR-01 | carousel | required | static | **pass** | rail is an accessible keyboard-scrollable region (line 3108) |
| IC-CAR-02 | carousel | advisory | static | **pass** | container has aria-roledescription=carousel and a label (line 3108) |
| IC-FORM-01 | form | required | static | **pass** | control 'qualified-demo-request-first-name' is programmatically labelled (line 3154) |
| IC-FORM-01 | form | required | static | **pass** | control 'qualified-demo-request-last-name' is programmatically labelled (line 3158) |
| IC-FORM-01 | form | required | static | **pass** | control 'qualified-demo-request-email' is programmatically labelled (line 3162) |
| IC-FORM-01 | form | required | static | **pass** | control 'qualified-demo-request-company' is programmatically labelled (line 3166) |
| IC-FORM-01 | form | required | static | **pass** | control 'qualified-demo-request-role' is programmatically labelled (line 3170) |
| IC-FORM-01 | form | required | static | **pass** | control 'qualified-demo-request-company-size' is programmatically labelled (line 3179) |
| IC-FORM-01 | form | required | static | **pass** | control 'qualified-demo-request-operating-footprint' is programmatically labelled (line 3187) |
| IC-FORM-01 | form | required | static | **pass** | control 'qualified-demo-request-workforce-question' is programmatically labelled (line 3191) |
| IC-FORM-02 | form | required | static | **pass** | form has a real submit button (line 3195) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 3153) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 3157) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 3161) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 3165) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 3169) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 3178) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 3186) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 3190) |
| IC-FORM-04 | form | required | static | **pass** | required fields use the required attribute (line 3154) |
| IC-FORM-07 | form | required | behavioral | **pass** | all visible form controls have browser-computed labels |
| IC-LANG-01 | lang | required | static | **pass** | toggle is a native <summary> inside <details> (line 2949) |
| IC-LANG-02 | lang | required | static | **pass** | toggle has an accessible name (line 2949) |
| IC-LANG-03 | lang | required | static | **pass** | current selection marked via aria-current/aria-selected (line 2949) |
| IC-LANG-04 | lang | advisory | static | **pass** | locale items are links carrying hreflang (line 2949) |
| IC-LANG-05 | lang | required | behavioral | **pass** | Enter opens (open=True), Space toggles back=True |
| IC-LANG-06 | lang | required | behavioral | **pass** | Escape closes the language dropdown |
| IC-LANG-07 | lang | advisory | behavioral | **pass** | open dropdown items are in the Tab order |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Products' is a native button (line 2949) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Solutions' is a native button (line 2949) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Resources' is a native button (line 2949) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Products' carries aria-expanded (line 2949) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Solutions' carries aria-expanded (line 2949) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Resources' carries aria-expanded (line 2949) |
| IC-NAV-03 | nav | required | static | **pass** | no ARIA menu/menubar roles in site nav |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2949) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2949) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2949) |
| IC-NAV-06 | nav | required | behavioral | **pass** | Tab reaches nav triggers, login, and language switcher |
| IC-NAV-07 | nav | required | behavioral | **pass** | hover opens panel=True, keyboard focus opens panel=True |
| IC-NAV-08 | nav | required | behavioral | **pass** | Escape closes the open panel and keeps focus in nav |
| IC-REV-01 | reveal | required | static | **pass** | hidden initial state is gated on a JS-added class (.cs-motion-ready .cs-reveal…) |
| IC-REV-02 | reveal | required | static | **pass** | prefers-reduced-motion forces reveal targets visible |
| IC-REV-03 | reveal | advisory | static | **pass** | timed failsafe present (setTimeout forces all targets visible) |
| IC-REV-04 | reveal | required | behavioral | **pass** | reduced motion: gate applied=False, 0 tagged targets, 0 hidden |
| IC-CAR-04 | carousel | advisory | static | **skip** | no auto-rotation on this rail — pause-control contract not applicable (line 3108) |
| IC-CAR-05 | carousel | required | behavioral | **skip** | rail does not overflow at this viewport; keyboard-scroll probe not applicable |
| IC-MARQ-01 | marquee | required | static | **skip** | no marquee detected in this lane |
| IC-MARQ-03 | marquee | required | behavioral | **skip** | no marquee detected in this lane |

