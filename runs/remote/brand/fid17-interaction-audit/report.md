# Interaction-Contract Baseline Report

Generated: 2026-07-10T18:49:07+00:00 — auditor v1.0.0 — mode: strict
Contracts: `brand_pipeline/spec/interaction-contracts.md` (WAI-ARIA APG primary; Base UI secondary; Radix tertiary)

## Audited lanes

| lane | file | mtime (UTC) | sha256/12 |
|---|---|---|---|
| compose | `/Users/stanchev/Webflow/campaigns-hackathon/design-system-extractor-mine/runs/remote/brand/compose/index.html` | 2026-07-10T18:47:39+00:00 | `02f798a8f0df` |
| compose/bakeoff-sol | `/Users/stanchev/Webflow/campaigns-hackathon/design-system-extractor-mine/runs/remote/brand/compose/bakeoff-sol/index.html` | 2026-07-10T18:47:39+00:00 | `47eb2489d73a` |
| compose/bakeoff-opus | `/Users/stanchev/Webflow/campaigns-hackathon/design-system-extractor-mine/runs/remote/brand/compose/bakeoff-opus/index.html` | 2026-07-10T18:47:39+00:00 | `477cbc4dd043` |
| compose/stress-playbook | `/Users/stanchev/Webflow/campaigns-hackathon/design-system-extractor-mine/runs/remote/brand/compose/stress-playbook/index.html` | 2026-07-10T18:47:39+00:00 | `13964a658908` |
| compose/event-genlaunch | `/Users/stanchev/Webflow/campaigns-hackathon/design-system-extractor-mine/runs/remote/brand/compose/event-genlaunch/index.html` | 2026-07-10T18:47:40+00:00 | `067645c1fc6c` |
| compose/replica | `/Users/stanchev/Webflow/campaigns-hackathon/design-system-extractor-mine/runs/remote/brand/compose/replica/index.html` | 2026-07-10T18:47:38+00:00 | `041a392896ca` |

If a lane is re-rendered by another agent, re-run the audit; the mtime/sha above identify exactly which HTML was measured.

## Summary — 0 failing required cells, 15 advisory, 211 passing, 25 skipped

### Most impactful gaps (required checks failing, by lane count)

- none — all required checks pass

## Lane: compose

| check | family | severity | layer | status | detail |
|---|---|---|---|---|---|
| IC-CAR-03 | carousel | advisory | static | **advisory** | no slide-level group/roledescription semantics (line 3088) |
| IC-NAV-05 | nav | advisory | static | **advisory** | anchor with role=button in nav chrome — promises Space activation anchors don't have (line 2972) |
| IC-BAN-01 | banner | required | static | **pass** | close control is a native button (line 2969) |
| IC-BAN-02 | banner | required | static | **pass** | close control has an accessible name (line 2969) |
| IC-BAN-03 | banner | advisory | static | **pass** | icon inside close control is aria-hidden (line 2969) |
| IC-BAN-04 | banner | required | behavioral | **pass** | keyboard activation dismisses the banner |
| IC-CAR-01 | carousel | required | static | **pass** | rail is an accessible keyboard-scrollable region (line 3088) |
| IC-CAR-02 | carousel | advisory | static | **pass** | container has aria-roledescription=carousel and a label (line 3088) |
| IC-LANG-01 | lang | required | static | **pass** | toggle is a native <summary> inside <details> (line 2972) |
| IC-LANG-02 | lang | required | static | **pass** | toggle has an accessible name (line 2972) |
| IC-LANG-03 | lang | required | static | **pass** | current selection marked via aria-current/aria-selected (line 2972) |
| IC-LANG-04 | lang | advisory | static | **pass** | locale items are links carrying hreflang (line 2972) |
| IC-LANG-05 | lang | required | behavioral | **pass** | Enter opens (open=True), Space toggles back=True |
| IC-LANG-06 | lang | required | behavioral | **pass** | Escape closes the language dropdown |
| IC-LANG-07 | lang | advisory | behavioral | **pass** | open dropdown items are in the Tab order |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Products' is a native button (line 2972) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Solutions' is a native button (line 2972) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Resources' is a native button (line 2972) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Products' carries aria-expanded (line 2972) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Solutions' carries aria-expanded (line 2972) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Resources' carries aria-expanded (line 2972) |
| IC-NAV-03 | nav | required | static | **pass** | no ARIA menu/menubar roles in site nav |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2972) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2972) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2972) |
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
| IC-CAR-04 | carousel | advisory | static | **skip** | no auto-rotation on this rail — pause-control contract not applicable (line 3088) |
| IC-CAR-05 | carousel | required | behavioral | **skip** | rail does not overflow at this viewport; keyboard-scroll probe not applicable |
| IC-FORM-01 | form | required | static | **skip** | no form controls or labels detected in this lane |
| IC-FORM-07 | form | required | behavioral | **skip** | no form controls detected in this lane |
| IC-MARQ-01 | marquee | required | static | **skip** | no marquee detected in this lane |
| IC-MARQ-03 | marquee | required | behavioral | **skip** | no marquee detected in this lane |

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

## Lane: compose/bakeoff-opus

| check | family | severity | layer | status | detail |
|---|---|---|---|---|---|
| IC-CAR-03 | carousel | advisory | static | **advisory** | no slide-level group/roledescription semantics (line 3091) |
| IC-NAV-05 | nav | advisory | static | **advisory** | anchor with role=button in nav chrome — promises Space activation anchors don't have (line 2953) |
| IC-ACC-01 | acc | required | static | **pass** | group of 4 details shares name="acc-product-value" (exclusive single-open) (line 2987) |
| IC-ACC-01 | acc | required | static | **pass** | group of 5 details shares name="faq-faq" (exclusive single-open) (line 3132) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 2987) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 2992) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 2996) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 3000) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 3132) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 3132) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 3132) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 3132) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 3132) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 2988) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 2993) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 2997) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 3001) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 3132) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 3132) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 3132) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 3132) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 3132) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 2988) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 2993) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 2997) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 3001) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 3132) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 3132) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 3132) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 3132) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 3132) |
| IC-ACC-05 | acc | advisory | static | **pass** | 1 item(s) authored open (line 2987) |
| IC-ACC-05 | acc | advisory | static | **pass** | 1 item(s) authored open (line 3132) |
| IC-ACC-06 | acc | required | behavioral | **pass** | summary focusable; Enter and Space toggle the panel |
| IC-ACC-07 | acc | required | behavioral | **pass** | group 0 (named, 4 items): opening item 2 closes item 1 (exclusive group holds) |
| IC-ACC-08 | acc | required | behavioral | **pass** | opened panel content is rendered and visible |
| IC-BAN-01 | banner | required | static | **pass** | close control is a native button (line 2950) |
| IC-BAN-02 | banner | required | static | **pass** | close control has an accessible name (line 2950) |
| IC-BAN-03 | banner | advisory | static | **pass** | icon inside close control is aria-hidden (line 2950) |
| IC-BAN-04 | banner | required | behavioral | **pass** | keyboard activation dismisses the banner |
| IC-CAR-01 | carousel | required | static | **pass** | rail is an accessible keyboard-scrollable region (line 3091) |
| IC-CAR-02 | carousel | advisory | static | **pass** | container has aria-roledescription=carousel and a label (line 3091) |
| IC-CAR-05 | carousel | required | behavioral | **pass** | rail focusable; ArrowRight scrolls: 0->142 |
| IC-FORM-01 | form | required | static | **pass** | control 'lead-form-name' is programmatically labelled (line 3145) |
| IC-FORM-01 | form | required | static | **pass** | control 'lead-form-email' is programmatically labelled (line 3149) |
| IC-FORM-01 | form | required | static | **pass** | control 'lead-form-company' is programmatically labelled (line 3153) |
| IC-FORM-01 | form | required | static | **pass** | control 'lead-form-size' is programmatically labelled (line 3157) |
| IC-FORM-01 | form | required | static | **pass** | control 'lead-form-region' is programmatically labelled (line 3165) |
| IC-FORM-01 | form | required | static | **pass** | control 'lead-form-notes' is programmatically labelled (line 3175) |
| IC-FORM-02 | form | required | static | **pass** | form has a real submit button (line 3179) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 3144) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 3148) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 3152) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 3156) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 3164) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 3174) |
| IC-FORM-04 | form | required | static | **pass** | required fields use the required attribute (line 3145) |
| IC-FORM-07 | form | required | behavioral | **pass** | all visible form controls have browser-computed labels |
| IC-LANG-01 | lang | required | static | **pass** | toggle is a native <summary> inside <details> (line 2953) |
| IC-LANG-02 | lang | required | static | **pass** | toggle has an accessible name (line 2953) |
| IC-LANG-03 | lang | required | static | **pass** | current selection marked via aria-current/aria-selected (line 2953) |
| IC-LANG-04 | lang | advisory | static | **pass** | locale items are links carrying hreflang (line 2953) |
| IC-LANG-05 | lang | required | behavioral | **pass** | Enter opens (open=True), Space toggles back=True |
| IC-LANG-06 | lang | required | behavioral | **pass** | Escape closes the language dropdown |
| IC-LANG-07 | lang | advisory | behavioral | **pass** | open dropdown items are in the Tab order |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Products' is a native button (line 2953) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Solutions' is a native button (line 2953) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Resources' is a native button (line 2953) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Products' carries aria-expanded (line 2953) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Solutions' carries aria-expanded (line 2953) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Resources' carries aria-expanded (line 2953) |
| IC-NAV-03 | nav | required | static | **pass** | no ARIA menu/menubar roles in site nav |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2953) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2953) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2953) |
| IC-NAV-06 | nav | required | behavioral | **pass** | Tab reaches nav triggers, login, and language switcher |
| IC-NAV-07 | nav | required | behavioral | **pass** | hover opens panel=True, keyboard focus opens panel=True |
| IC-NAV-08 | nav | required | behavioral | **pass** | Escape closes the open panel and keeps focus in nav |
| IC-REV-01 | reveal | required | static | **pass** | hidden initial state is gated on a JS-added class (.cs-motion-ready .cs-reveal…) |
| IC-REV-02 | reveal | required | static | **pass** | prefers-reduced-motion forces reveal targets visible |
| IC-REV-03 | reveal | advisory | static | **pass** | timed failsafe present (setTimeout forces all targets visible) |
| IC-REV-04 | reveal | required | behavioral | **pass** | reduced motion: gate applied=False, 0 tagged targets, 0 hidden |
| IC-CAR-04 | carousel | advisory | static | **skip** | no auto-rotation on this rail — pause-control contract not applicable (line 3091) |
| IC-MARQ-01 | marquee | required | static | **skip** | no marquee detected in this lane |
| IC-MARQ-03 | marquee | required | behavioral | **skip** | no marquee detected in this lane |

## Lane: compose/stress-playbook

| check | family | severity | layer | status | detail |
|---|---|---|---|---|---|
| IC-CAR-03 | carousel | advisory | static | **advisory** | no slide-level group/roledescription semantics (line 3163) |
| IC-FORM-05 | form | advisory | static | **advisory** | field help text not linked to its control via aria-describedby (line 3232) |
| IC-FORM-06 | form | advisory | static | **advisory** | error copy lives only in data-error attributes — invisible to AT (line 3227) |
| IC-NAV-05 | nav | advisory | static | **advisory** | anchor with role=button in nav chrome — promises Space activation anchors don't have (line 3022) |
| IC-ACC-01 | acc | required | static | **pass** | group of 4 details shares name="acc-pb-process" (exclusive single-open) (line 3106) |
| IC-ACC-01 | acc | required | static | **pass** | group of 5 details is a declared multi-open family (data-acc-multi="authored") — single-open grouping waived (line 3212) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 3106) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 3111) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 3115) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 3119) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 3212) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 3212) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 3212) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 3212) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 3212) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 3107) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 3112) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 3116) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 3120) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 3212) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 3212) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 3212) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 3212) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 3212) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 3107) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 3112) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 3116) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 3120) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 3212) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 3212) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 3212) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 3212) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 3212) |
| IC-ACC-05 | acc | advisory | static | **pass** | 1 item(s) authored open (line 3106) |
| IC-ACC-05 | acc | advisory | static | **pass** | 1 item(s) authored open (line 3212) |
| IC-ACC-06 | acc | required | behavioral | **pass** | summary focusable; Enter and Space toggle the panel |
| IC-ACC-07 | acc | required | behavioral | **pass** | group 0 (named, 4 items): opening item 2 closes item 1 (exclusive group holds) |
| IC-ACC-07 | acc | required | behavioral | **pass** | group 1 (declared multi-open, 5 items): items toggle independently (authored multi-open holds) |
| IC-ACC-08 | acc | required | behavioral | **pass** | opened panel content is rendered and visible |
| IC-BAN-01 | banner | required | static | **pass** | close control is a native button (line 3019) |
| IC-BAN-02 | banner | required | static | **pass** | close control has an accessible name (line 3019) |
| IC-BAN-03 | banner | advisory | static | **pass** | icon inside close control is aria-hidden (line 3019) |
| IC-BAN-04 | banner | required | behavioral | **pass** | keyboard activation dismisses the banner |
| IC-CAR-01 | carousel | required | static | **pass** | rail is an accessible keyboard-scrollable region (line 3163) |
| IC-CAR-02 | carousel | advisory | static | **pass** | container has aria-roledescription=carousel and a label (line 3163) |
| IC-CAR-05 | carousel | required | behavioral | **pass** | rail focusable; ArrowRight scrolls: 0->142 |
| IC-FORM-01 | form | required | static | **pass** | control 'pb-form-full-name' is programmatically labelled (line 3227) |
| IC-FORM-01 | form | required | static | **pass** | control 'pb-form-work-email' is programmatically labelled (line 3231) |
| IC-FORM-01 | form | required | static | **pass** | control 'pb-form-company' is programmatically labelled (line 3236) |
| IC-FORM-01 | form | required | static | **pass** | control 'pb-form-phone' is programmatically labelled (line 3240) |
| IC-FORM-01 | form | required | static | **pass** | control 'pb-form-region' is programmatically labelled (line 3245) |
| IC-FORM-01 | form | required | static | **pass** | control 'pb-form-hiring-question' is programmatically labelled (line 3257) |
| IC-FORM-01 | form | required | static | **pass** | control 'quarterly-update' is programmatically labelled (line 3260) |
| IC-FORM-02 | form | required | static | **pass** | form has a real submit button (line 3263) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 3226) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 3230) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 3235) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 3239) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 3244) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 3256) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 3260) |
| IC-FORM-04 | form | required | static | **pass** | fields with error copy communicate requiredness programmatically (line 3227) |
| IC-FORM-07 | form | required | behavioral | **pass** | all visible form controls have browser-computed labels |
| IC-LANG-01 | lang | required | static | **pass** | toggle is a native <summary> inside <details> (line 3022) |
| IC-LANG-02 | lang | required | static | **pass** | toggle has an accessible name (line 3022) |
| IC-LANG-03 | lang | required | static | **pass** | current selection marked via aria-current/aria-selected (line 3022) |
| IC-LANG-04 | lang | advisory | static | **pass** | locale items are links carrying hreflang (line 3022) |
| IC-LANG-05 | lang | required | behavioral | **pass** | Enter opens (open=True), Space toggles back=True |
| IC-LANG-06 | lang | required | behavioral | **pass** | Escape closes the language dropdown |
| IC-LANG-07 | lang | advisory | behavioral | **pass** | open dropdown items are in the Tab order |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Products' is a native button (line 3022) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Solutions' is a native button (line 3022) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Resources' is a native button (line 3022) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Products' carries aria-expanded (line 3022) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Solutions' carries aria-expanded (line 3022) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Resources' carries aria-expanded (line 3022) |
| IC-NAV-03 | nav | required | static | **pass** | no ARIA menu/menubar roles in site nav |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 3022) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 3022) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 3022) |
| IC-NAV-06 | nav | required | behavioral | **pass** | Tab reaches nav triggers, login, and language switcher |
| IC-NAV-07 | nav | required | behavioral | **pass** | hover opens panel=True, keyboard focus opens panel=True |
| IC-NAV-08 | nav | required | behavioral | **pass** | Escape closes the open panel and keeps focus in nav |
| IC-REV-01 | reveal | required | static | **pass** | hidden initial state is gated on a JS-added class (.cs-motion-ready .cs-reveal…) |
| IC-REV-02 | reveal | required | static | **pass** | prefers-reduced-motion forces reveal targets visible |
| IC-REV-03 | reveal | advisory | static | **pass** | timed failsafe present (setTimeout forces all targets visible) |
| IC-REV-04 | reveal | required | behavioral | **pass** | reduced motion: gate applied=False, 0 tagged targets, 0 hidden |
| IC-CAR-04 | carousel | advisory | static | **skip** | no auto-rotation on this rail — pause-control contract not applicable (line 3163) |
| IC-MARQ-01 | marquee | required | static | **skip** | no marquee detected in this lane |
| IC-MARQ-03 | marquee | required | behavioral | **skip** | no marquee detected in this lane |

## Lane: compose/event-genlaunch

| check | family | severity | layer | status | detail |
|---|---|---|---|---|---|
| IC-FORM-05 | form | advisory | static | **advisory** | field help text not linked to its control via aria-describedby (line 2986) |
| IC-FORM-06 | form | advisory | static | **advisory** | error copy lives only in data-error attributes — invisible to AT (line 2981) |
| IC-NAV-05 | nav | advisory | static | **advisory** | anchor with role=button in nav chrome — promises Space activation anchors don't have (line 2790) |
| IC-ACC-01 | acc | required | static | **pass** | group of 4 details shares name="faq-event-agenda" (exclusive single-open) (line 2895) |
| IC-ACC-01 | acc | required | static | **pass** | group of 6 details shares name="faq-event-faq" (exclusive single-open) (line 2966) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 2895) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 2895) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 2895) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 2895) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 2966) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 2966) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 2966) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 2966) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 2966) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 2966) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 2895) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 2895) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 2895) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 2895) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 2966) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 2966) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 2966) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 2966) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 2966) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 2966) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 2895) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 2895) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 2895) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 2895) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 2966) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 2966) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 2966) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 2966) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 2966) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 2966) |
| IC-ACC-05 | acc | advisory | static | **pass** | 1 item(s) authored open (line 2895) |
| IC-ACC-05 | acc | advisory | static | **pass** | 1 item(s) authored open (line 2966) |
| IC-ACC-06 | acc | required | behavioral | **pass** | summary focusable; Enter and Space toggle the panel |
| IC-ACC-07 | acc | required | behavioral | **pass** | group 0 (named, 4 items): opening item 2 closes item 1 (exclusive group holds) |
| IC-ACC-08 | acc | required | behavioral | **pass** | opened panel content is rendered and visible |
| IC-BAN-01 | banner | required | static | **pass** | close control is a native button (line 2787) |
| IC-BAN-02 | banner | required | static | **pass** | close control has an accessible name (line 2787) |
| IC-BAN-03 | banner | advisory | static | **pass** | icon inside close control is aria-hidden (line 2787) |
| IC-BAN-04 | banner | required | behavioral | **pass** | keyboard activation dismisses the banner |
| IC-FORM-01 | form | required | static | **pass** | control 'event-signup-full-name' is programmatically labelled (line 2981) |
| IC-FORM-01 | form | required | static | **pass** | control 'event-signup-work-email' is programmatically labelled (line 2985) |
| IC-FORM-01 | form | required | static | **pass** | control 'event-signup-company' is programmatically labelled (line 2990) |
| IC-FORM-01 | form | required | static | **pass** | control 'event-signup-company-size' is programmatically labelled (line 2994) |
| IC-FORM-01 | form | required | static | **pass** | control 'event-signup-role' is programmatically labelled (line 3005) |
| IC-FORM-01 | form | required | static | **pass** | control 'pass' is programmatically labelled (line 3017) |
| IC-FORM-01 | form | required | static | **pass** | control 'pass' is programmatically labelled (line 3018) |
| IC-FORM-01 | form | required | static | **pass** | control 'pass' is programmatically labelled (line 3019) |
| IC-FORM-01 | form | required | static | **pass** | control 'product-news' is programmatically labelled (line 3022) |
| IC-FORM-02 | form | required | static | **pass** | form has a real submit button (line 3025) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 2980) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 2984) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 2989) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 2993) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 3004) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 3017) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 3018) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 3019) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 3022) |
| IC-FORM-04 | form | required | static | **pass** | fields with error copy communicate requiredness programmatically (line 2981) |
| IC-FORM-07 | form | required | behavioral | **pass** | all visible form controls have browser-computed labels |
| IC-LANG-01 | lang | required | static | **pass** | toggle is a native <summary> inside <details> (line 2790) |
| IC-LANG-02 | lang | required | static | **pass** | toggle has an accessible name (line 2790) |
| IC-LANG-03 | lang | required | static | **pass** | current selection marked via aria-current/aria-selected (line 2790) |
| IC-LANG-04 | lang | advisory | static | **pass** | locale items are links carrying hreflang (line 2790) |
| IC-LANG-05 | lang | required | behavioral | **pass** | Enter opens (open=True), Space toggles back=True |
| IC-LANG-06 | lang | required | behavioral | **pass** | Escape closes the language dropdown |
| IC-LANG-07 | lang | advisory | behavioral | **pass** | open dropdown items are in the Tab order |
| IC-MARQ-01 | marquee | required | static | **pass** | duplicated seam half is aria-hidden (line 2825) |
| IC-MARQ-02 | marquee | required | static | **pass** | prefers-reduced-motion neutralizes the marquee animation (line 2809) |
| IC-MARQ-03 | marquee | required | behavioral | **pass** | reduced motion: animation=none/running, content visible=True |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Products' is a native button (line 2790) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Solutions' is a native button (line 2790) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Resources' is a native button (line 2790) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Products' carries aria-expanded (line 2790) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Solutions' carries aria-expanded (line 2790) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Resources' carries aria-expanded (line 2790) |
| IC-NAV-03 | nav | required | static | **pass** | no ARIA menu/menubar roles in site nav |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2790) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2790) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2790) |
| IC-NAV-06 | nav | required | behavioral | **pass** | Tab reaches nav triggers, login, and language switcher |
| IC-NAV-07 | nav | required | behavioral | **pass** | hover opens panel=True, keyboard focus opens panel=True |
| IC-NAV-08 | nav | required | behavioral | **pass** | Escape closes the open panel and keeps focus in nav |
| IC-REV-01 | reveal | required | static | **pass** | hidden initial state is gated on a JS-added class (.cs-motion-ready .cs-reveal…) |
| IC-REV-02 | reveal | required | static | **pass** | prefers-reduced-motion forces reveal targets visible |
| IC-REV-03 | reveal | advisory | static | **pass** | timed failsafe present (setTimeout forces all targets visible) |
| IC-REV-04 | reveal | required | behavioral | **pass** | reduced motion: gate applied=False, 0 tagged targets, 0 hidden |
| IC-CAR-01 | carousel | required | static | **skip** | no carousel/edge-cut rail detected in this lane |
| IC-CAR-05 | carousel | required | behavioral | **skip** | no carousel/edge-cut rail detected in this lane |

## Lane: compose/replica

| check | family | severity | layer | status | detail |
|---|---|---|---|---|---|
| IC-CAR-03 | carousel | advisory | static | **advisory** | no slide-level group/roledescription semantics (line 3041) |
| IC-NAV-05 | nav | advisory | static | **advisory** | anchor with role=button in nav chrome — promises Space activation anchors don't have (line 2879) |
| IC-ACC-01 | acc | required | static | **pass** | group of 5 details shares name="acc-feature-accordion" (exclusive single-open) (line 2940) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 2940) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 2945) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 2949) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 2953) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 2957) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 2941) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 2946) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 2950) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 2954) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 2958) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 2941) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 2946) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 2950) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 2954) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 2958) |
| IC-ACC-05 | acc | advisory | static | **pass** | 1 item(s) authored open (line 2940) |
| IC-ACC-06 | acc | required | behavioral | **pass** | summary focusable; Enter and Space toggle the panel |
| IC-ACC-07 | acc | required | behavioral | **pass** | group 0 (named, 5 items): opening item 2 closes item 1 (exclusive group holds) |
| IC-ACC-08 | acc | required | behavioral | **pass** | opened panel content is rendered and visible |
| IC-BAN-01 | banner | required | static | **pass** | close control is a native button (line 2876) |
| IC-BAN-02 | banner | required | static | **pass** | close control has an accessible name (line 2876) |
| IC-BAN-03 | banner | advisory | static | **pass** | icon inside close control is aria-hidden (line 2876) |
| IC-BAN-04 | banner | required | behavioral | **pass** | keyboard activation dismisses the banner |
| IC-CAR-01 | carousel | required | static | **pass** | rail is an accessible keyboard-scrollable region (line 3041) |
| IC-CAR-02 | carousel | advisory | static | **pass** | container has aria-roledescription=carousel and a label (line 3041) |
| IC-CAR-05 | carousel | required | behavioral | **pass** | rail focusable; ArrowRight scrolls: 0->142 |
| IC-LANG-01 | lang | required | static | **pass** | toggle is a native <summary> inside <details> (line 2879) |
| IC-LANG-02 | lang | required | static | **pass** | toggle has an accessible name (line 2879) |
| IC-LANG-03 | lang | required | static | **pass** | current selection marked via aria-current/aria-selected (line 2879) |
| IC-LANG-04 | lang | advisory | static | **pass** | locale items are links carrying hreflang (line 2879) |
| IC-LANG-05 | lang | required | behavioral | **pass** | Enter opens (open=True), Space toggles back=True |
| IC-LANG-06 | lang | required | behavioral | **pass** | Escape closes the language dropdown |
| IC-LANG-07 | lang | advisory | behavioral | **pass** | open dropdown items are in the Tab order |
| IC-MARQ-01 | marquee | required | static | **pass** | duplicated seam half is aria-hidden (line 2913) |
| IC-MARQ-02 | marquee | required | static | **pass** | prefers-reduced-motion neutralizes the marquee animation (line 2897) |
| IC-MARQ-03 | marquee | required | behavioral | **pass** | reduced motion: animation=none/running, content visible=True |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Products' is a native button (line 2879) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Solutions' is a native button (line 2879) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Resources' is a native button (line 2879) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Products' carries aria-expanded (line 2879) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Solutions' carries aria-expanded (line 2879) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Resources' carries aria-expanded (line 2879) |
| IC-NAV-03 | nav | required | static | **pass** | no ARIA menu/menubar roles in site nav |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2879) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2879) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2879) |
| IC-NAV-06 | nav | required | behavioral | **pass** | Tab reaches nav triggers, login, and language switcher |
| IC-NAV-07 | nav | required | behavioral | **pass** | hover opens panel=True, keyboard focus opens panel=True |
| IC-NAV-08 | nav | required | behavioral | **pass** | Escape closes the open panel and keeps focus in nav |
| IC-REV-01 | reveal | required | static | **pass** | hidden initial state is gated on a JS-added class (.cs-motion-ready .cs-reveal…) |
| IC-REV-02 | reveal | required | static | **pass** | prefers-reduced-motion forces reveal targets visible |
| IC-REV-03 | reveal | advisory | static | **pass** | timed failsafe present (setTimeout forces all targets visible) |
| IC-REV-04 | reveal | required | behavioral | **pass** | reduced motion: gate applied=False, 0 tagged targets, 0 hidden |
| IC-CAR-04 | carousel | advisory | static | **skip** | no auto-rotation on this rail — pause-control contract not applicable (line 3041) |
| IC-FORM-01 | form | required | static | **skip** | no form controls or labels detected in this lane |
| IC-FORM-07 | form | required | behavioral | **skip** | no form controls detected in this lane |

