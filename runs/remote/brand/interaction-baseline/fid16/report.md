# Interaction-Contract Baseline Report

Generated: 2026-07-10T18:26:22+00:00 — auditor v1.0.0 — mode: strict
Contracts: `brand_pipeline/spec/interaction-contracts.md` (WAI-ARIA APG primary; Base UI secondary; Radix tertiary)

## Audited lanes

| lane | file | mtime (UTC) | sha256/12 |
|---|---|---|---|
| compose | `/Users/stanchev/Webflow/campaigns-hackathon/design-system-extractor-mine/runs/remote/brand/compose/index.html` | 2026-07-10T18:23:00+00:00 | `839d44d66593` |
| compose/sol-experiment | `/Users/stanchev/Webflow/campaigns-hackathon/design-system-extractor-mine/runs/remote/brand/compose/sol-experiment/index.html` | 2026-07-10T18:23:00+00:00 | `e6fc153cd605` |
| compose/event-genlaunch | `/Users/stanchev/Webflow/campaigns-hackathon/design-system-extractor-mine/runs/remote/brand/compose/event-genlaunch/index.html` | 2026-07-10T18:23:01+00:00 | `346587fc2c31` |
| compose/stress-playbook | `/Users/stanchev/Webflow/campaigns-hackathon/design-system-extractor-mine/runs/remote/brand/compose/stress-playbook/index.html` | 2026-07-10T18:25:15+00:00 | `e65339016b02` |
| compose/replica | `/Users/stanchev/Webflow/campaigns-hackathon/design-system-extractor-mine/runs/remote/brand/compose/replica/index.html` | 2026-07-10T18:26:17+00:00 | `6a3421bb16b2` |

If a lane is re-rendered by another agent, re-run the audit; the mtime/sha above identify exactly which HTML was measured.

## Summary — 0 failing required cells, 14 advisory, 174 passing, 20 skipped

### Most impactful gaps (required checks failing, by lane count)

- none — all required checks pass

## Lane: compose

| check | family | severity | layer | status | detail |
|---|---|---|---|---|---|
| IC-CAR-03 | carousel | advisory | static | **advisory** | no slide-level group/roledescription semantics (line 3083) |
| IC-NAV-05 | nav | advisory | static | **advisory** | anchor with role=button in nav chrome — promises Space activation anchors don't have (line 2967) |
| IC-BAN-01 | banner | required | static | **pass** | close control is a native button (line 2964) |
| IC-BAN-02 | banner | required | static | **pass** | close control has an accessible name (line 2964) |
| IC-BAN-03 | banner | advisory | static | **pass** | icon inside close control is aria-hidden (line 2964) |
| IC-BAN-04 | banner | required | behavioral | **pass** | keyboard activation dismisses the banner |
| IC-CAR-01 | carousel | required | static | **pass** | rail is an accessible keyboard-scrollable region (line 3083) |
| IC-CAR-02 | carousel | advisory | static | **pass** | container has aria-roledescription=carousel and a label (line 3083) |
| IC-LANG-01 | lang | required | static | **pass** | toggle is a native <summary> inside <details> (line 2967) |
| IC-LANG-02 | lang | required | static | **pass** | toggle has an accessible name (line 2967) |
| IC-LANG-03 | lang | required | static | **pass** | current selection marked via aria-current/aria-selected (line 2967) |
| IC-LANG-04 | lang | advisory | static | **pass** | locale items are links carrying hreflang (line 2967) |
| IC-LANG-05 | lang | required | behavioral | **pass** | Enter opens (open=True), Space toggles back=True |
| IC-LANG-06 | lang | required | behavioral | **pass** | Escape closes the language dropdown |
| IC-LANG-07 | lang | advisory | behavioral | **pass** | open dropdown items are in the Tab order |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Products' is a native button (line 2967) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Solutions' is a native button (line 2967) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Resources' is a native button (line 2967) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Products' carries aria-expanded (line 2967) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Solutions' carries aria-expanded (line 2967) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Resources' carries aria-expanded (line 2967) |
| IC-NAV-03 | nav | required | static | **pass** | no ARIA menu/menubar roles in site nav |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2967) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2967) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2967) |
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
| IC-CAR-04 | carousel | advisory | static | **skip** | no auto-rotation on this rail — pause-control contract not applicable (line 3083) |
| IC-CAR-05 | carousel | required | behavioral | **skip** | rail does not overflow at this viewport; keyboard-scroll probe not applicable |
| IC-FORM-01 | form | required | static | **skip** | no form controls or labels detected in this lane |
| IC-FORM-07 | form | required | behavioral | **skip** | no form controls detected in this lane |
| IC-MARQ-01 | marquee | required | static | **skip** | no marquee detected in this lane |
| IC-MARQ-03 | marquee | required | behavioral | **skip** | no marquee detected in this lane |

## Lane: compose/sol-experiment

| check | family | severity | layer | status | detail |
|---|---|---|---|---|---|
| IC-FORM-05 | form | advisory | static | **advisory** | field help text not linked to its control via aria-describedby (line 3096) |
| IC-FORM-06 | form | advisory | static | **advisory** | error copy lives only in data-error attributes — invisible to AT (line 3091) |
| IC-NAV-05 | nav | advisory | static | **advisory** | anchor with role=button in nav chrome — promises Space activation anchors don't have (line 2910) |
| IC-ACC-01 | acc | required | static | **pass** | group of 4 details shares name="acc-sol-process" (exclusive single-open) (line 3021) |
| IC-ACC-01 | acc | required | static | **pass** | group of 5 details shares name="faq-sol-faq" (exclusive single-open) (line 3076) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 3021) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 3026) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 3030) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 3034) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 3076) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 3076) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 3076) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 3076) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 3076) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 3022) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 3027) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 3031) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 3035) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 3076) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 3076) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 3076) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 3076) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 3076) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 3022) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 3027) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 3031) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 3035) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 3076) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 3076) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 3076) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 3076) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 3076) |
| IC-ACC-05 | acc | advisory | static | **pass** | 1 item(s) authored open (line 3021) |
| IC-ACC-05 | acc | advisory | static | **pass** | 1 item(s) authored open (line 3076) |
| IC-ACC-06 | acc | required | behavioral | **pass** | summary focusable; Enter and Space toggle the panel |
| IC-ACC-07 | acc | required | behavioral | **pass** | group 0 (named, 4 items): opening item 2 closes item 1 (exclusive group holds) |
| IC-ACC-08 | acc | required | behavioral | **pass** | opened panel content is rendered and visible |
| IC-BAN-01 | banner | required | static | **pass** | close control is a native button (line 2907) |
| IC-BAN-02 | banner | required | static | **pass** | close control has an accessible name (line 2907) |
| IC-BAN-03 | banner | advisory | static | **pass** | icon inside close control is aria-hidden (line 2907) |
| IC-BAN-04 | banner | required | behavioral | **pass** | keyboard activation dismisses the banner |
| IC-FORM-01 | form | required | static | **pass** | control 'sol-plan-form-full-name' is programmatically labelled (line 3091) |
| IC-FORM-01 | form | required | static | **pass** | control 'sol-plan-form-work-email' is programmatically labelled (line 3095) |
| IC-FORM-01 | form | required | static | **pass** | control 'sol-plan-form-company' is programmatically labelled (line 3100) |
| IC-FORM-01 | form | required | static | **pass** | control 'sol-plan-form-country-count' is programmatically labelled (line 3104) |
| IC-FORM-01 | form | required | static | **pass** | control 'sol-plan-form-current-setup' is programmatically labelled (line 3114) |
| IC-FORM-01 | form | required | static | **pass** | control 'sol-plan-form-improvement' is programmatically labelled (line 3124) |
| IC-FORM-02 | form | required | static | **pass** | form has a real submit button (line 3129) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 3090) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 3094) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 3099) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 3103) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 3113) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 3123) |
| IC-FORM-04 | form | required | static | **pass** | fields with error copy communicate requiredness programmatically (line 3091) |
| IC-FORM-07 | form | required | behavioral | **pass** | all visible form controls have browser-computed labels |
| IC-LANG-01 | lang | required | static | **pass** | toggle is a native <summary> inside <details> (line 2910) |
| IC-LANG-02 | lang | required | static | **pass** | toggle has an accessible name (line 2910) |
| IC-LANG-03 | lang | required | static | **pass** | current selection marked via aria-current/aria-selected (line 2910) |
| IC-LANG-04 | lang | advisory | static | **pass** | locale items are links carrying hreflang (line 2910) |
| IC-LANG-05 | lang | required | behavioral | **pass** | Enter opens (open=True), Space toggles back=True |
| IC-LANG-06 | lang | required | behavioral | **pass** | Escape closes the language dropdown |
| IC-LANG-07 | lang | advisory | behavioral | **pass** | open dropdown items are in the Tab order |
| IC-MARQ-01 | marquee | required | static | **pass** | duplicated seam half is aria-hidden (line 2941) |
| IC-MARQ-02 | marquee | required | static | **pass** | prefers-reduced-motion neutralizes the marquee animation (line 2929) |
| IC-MARQ-03 | marquee | required | behavioral | **pass** | reduced motion: animation=none/running, content visible=True |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Products' is a native button (line 2910) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Solutions' is a native button (line 2910) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Resources' is a native button (line 2910) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Products' carries aria-expanded (line 2910) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Solutions' carries aria-expanded (line 2910) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Resources' carries aria-expanded (line 2910) |
| IC-NAV-03 | nav | required | static | **pass** | no ARIA menu/menubar roles in site nav |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2910) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2910) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2910) |
| IC-NAV-06 | nav | required | behavioral | **pass** | Tab reaches nav triggers, login, and language switcher |
| IC-NAV-07 | nav | required | behavioral | **pass** | hover opens panel=True, keyboard focus opens panel=True |
| IC-NAV-08 | nav | required | behavioral | **pass** | Escape closes the open panel and keeps focus in nav |
| IC-REV-01 | reveal | required | static | **pass** | hidden initial state is gated on a JS-added class (.cs-motion-ready .cs-reveal…) |
| IC-REV-02 | reveal | required | static | **pass** | prefers-reduced-motion forces reveal targets visible |
| IC-REV-03 | reveal | advisory | static | **pass** | timed failsafe present (setTimeout forces all targets visible) |
| IC-REV-04 | reveal | required | behavioral | **pass** | reduced motion: gate applied=False, 0 tagged targets, 0 hidden |
| IC-CAR-01 | carousel | required | static | **skip** | no carousel/edge-cut rail detected in this lane |
| IC-CAR-05 | carousel | required | behavioral | **skip** | no carousel/edge-cut rail detected in this lane |

## Lane: compose/event-genlaunch

| check | family | severity | layer | status | detail |
|---|---|---|---|---|---|
| IC-FORM-05 | form | advisory | static | **advisory** | field help text not linked to its control via aria-describedby (line 2981) |
| IC-FORM-06 | form | advisory | static | **advisory** | error copy lives only in data-error attributes — invisible to AT (line 2976) |
| IC-NAV-05 | nav | advisory | static | **advisory** | anchor with role=button in nav chrome — promises Space activation anchors don't have (line 2785) |
| IC-ACC-01 | acc | required | static | **pass** | group of 4 details shares name="faq-event-agenda" (exclusive single-open) (line 2890) |
| IC-ACC-01 | acc | required | static | **pass** | group of 6 details shares name="faq-event-faq" (exclusive single-open) (line 2961) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 2890) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 2890) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 2890) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 2890) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 2961) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 2961) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 2961) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 2961) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 2961) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 2961) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 2890) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 2890) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 2890) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 2890) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 2961) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 2961) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 2961) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 2961) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 2961) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 2961) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 2890) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 2890) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 2890) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 2890) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 2961) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 2961) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 2961) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 2961) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 2961) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 2961) |
| IC-ACC-05 | acc | advisory | static | **pass** | 1 item(s) authored open (line 2890) |
| IC-ACC-05 | acc | advisory | static | **pass** | 1 item(s) authored open (line 2961) |
| IC-ACC-06 | acc | required | behavioral | **pass** | summary focusable; Enter and Space toggle the panel |
| IC-ACC-07 | acc | required | behavioral | **pass** | group 0 (named, 4 items): opening item 2 closes item 1 (exclusive group holds) |
| IC-ACC-08 | acc | required | behavioral | **pass** | opened panel content is rendered and visible |
| IC-BAN-01 | banner | required | static | **pass** | close control is a native button (line 2782) |
| IC-BAN-02 | banner | required | static | **pass** | close control has an accessible name (line 2782) |
| IC-BAN-03 | banner | advisory | static | **pass** | icon inside close control is aria-hidden (line 2782) |
| IC-BAN-04 | banner | required | behavioral | **pass** | keyboard activation dismisses the banner |
| IC-FORM-01 | form | required | static | **pass** | control 'event-signup-full-name' is programmatically labelled (line 2976) |
| IC-FORM-01 | form | required | static | **pass** | control 'event-signup-work-email' is programmatically labelled (line 2980) |
| IC-FORM-01 | form | required | static | **pass** | control 'event-signup-company' is programmatically labelled (line 2985) |
| IC-FORM-01 | form | required | static | **pass** | control 'event-signup-company-size' is programmatically labelled (line 2989) |
| IC-FORM-01 | form | required | static | **pass** | control 'event-signup-role' is programmatically labelled (line 3000) |
| IC-FORM-01 | form | required | static | **pass** | control 'pass' is programmatically labelled (line 3012) |
| IC-FORM-01 | form | required | static | **pass** | control 'pass' is programmatically labelled (line 3013) |
| IC-FORM-01 | form | required | static | **pass** | control 'pass' is programmatically labelled (line 3014) |
| IC-FORM-01 | form | required | static | **pass** | control 'product-news' is programmatically labelled (line 3017) |
| IC-FORM-02 | form | required | static | **pass** | form has a real submit button (line 3020) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 2975) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 2979) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 2984) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 2988) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 2999) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 3012) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 3013) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 3014) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 3017) |
| IC-FORM-04 | form | required | static | **pass** | fields with error copy communicate requiredness programmatically (line 2976) |
| IC-FORM-07 | form | required | behavioral | **pass** | all visible form controls have browser-computed labels |
| IC-LANG-01 | lang | required | static | **pass** | toggle is a native <summary> inside <details> (line 2785) |
| IC-LANG-02 | lang | required | static | **pass** | toggle has an accessible name (line 2785) |
| IC-LANG-03 | lang | required | static | **pass** | current selection marked via aria-current/aria-selected (line 2785) |
| IC-LANG-04 | lang | advisory | static | **pass** | locale items are links carrying hreflang (line 2785) |
| IC-LANG-05 | lang | required | behavioral | **pass** | Enter opens (open=True), Space toggles back=True |
| IC-LANG-06 | lang | required | behavioral | **pass** | Escape closes the language dropdown |
| IC-LANG-07 | lang | advisory | behavioral | **pass** | open dropdown items are in the Tab order |
| IC-MARQ-01 | marquee | required | static | **pass** | duplicated seam half is aria-hidden (line 2820) |
| IC-MARQ-02 | marquee | required | static | **pass** | prefers-reduced-motion neutralizes the marquee animation (line 2804) |
| IC-MARQ-03 | marquee | required | behavioral | **pass** | reduced motion: animation=none/running, content visible=True |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Products' is a native button (line 2785) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Solutions' is a native button (line 2785) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Resources' is a native button (line 2785) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Products' carries aria-expanded (line 2785) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Solutions' carries aria-expanded (line 2785) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Resources' carries aria-expanded (line 2785) |
| IC-NAV-03 | nav | required | static | **pass** | no ARIA menu/menubar roles in site nav |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2785) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2785) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2785) |
| IC-NAV-06 | nav | required | behavioral | **pass** | Tab reaches nav triggers, login, and language switcher |
| IC-NAV-07 | nav | required | behavioral | **pass** | hover opens panel=True, keyboard focus opens panel=True |
| IC-NAV-08 | nav | required | behavioral | **pass** | Escape closes the open panel and keeps focus in nav |
| IC-REV-01 | reveal | required | static | **pass** | hidden initial state is gated on a JS-added class (.cs-motion-ready .cs-reveal…) |
| IC-REV-02 | reveal | required | static | **pass** | prefers-reduced-motion forces reveal targets visible |
| IC-REV-03 | reveal | advisory | static | **pass** | timed failsafe present (setTimeout forces all targets visible) |
| IC-REV-04 | reveal | required | behavioral | **pass** | reduced motion: gate applied=False, 0 tagged targets, 0 hidden |
| IC-CAR-01 | carousel | required | static | **skip** | no carousel/edge-cut rail detected in this lane |
| IC-CAR-05 | carousel | required | behavioral | **skip** | no carousel/edge-cut rail detected in this lane |

## Lane: compose/stress-playbook

| check | family | severity | layer | status | detail |
|---|---|---|---|---|---|
| IC-CAR-03 | carousel | advisory | static | **advisory** | no slide-level group/roledescription semantics (line 3160) |
| IC-FORM-05 | form | advisory | static | **advisory** | field help text not linked to its control via aria-describedby (line 3229) |
| IC-FORM-06 | form | advisory | static | **advisory** | error copy lives only in data-error attributes — invisible to AT (line 3224) |
| IC-NAV-05 | nav | advisory | static | **advisory** | anchor with role=button in nav chrome — promises Space activation anchors don't have (line 3019) |
| IC-ACC-01 | acc | required | static | **pass** | group of 4 details shares name="acc-pb-process" (exclusive single-open) (line 3103) |
| IC-ACC-01 | acc | required | static | **pass** | group of 5 details is a declared multi-open family (data-acc-multi="authored") — single-open grouping waived (line 3209) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 3103) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 3108) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 3112) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 3116) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 3209) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 3209) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 3209) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 3209) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 3209) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 3104) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 3109) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 3113) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 3117) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 3209) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 3209) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 3209) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 3209) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 3209) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 3104) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 3109) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 3113) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 3117) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 3209) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 3209) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 3209) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 3209) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 3209) |
| IC-ACC-05 | acc | advisory | static | **pass** | 1 item(s) authored open (line 3103) |
| IC-ACC-05 | acc | advisory | static | **pass** | 1 item(s) authored open (line 3209) |
| IC-ACC-06 | acc | required | behavioral | **pass** | summary focusable; Enter and Space toggle the panel |
| IC-ACC-07 | acc | required | behavioral | **pass** | group 0 (named, 4 items): opening item 2 closes item 1 (exclusive group holds) |
| IC-ACC-07 | acc | required | behavioral | **pass** | group 1 (declared multi-open, 5 items): items toggle independently (authored multi-open holds) |
| IC-ACC-08 | acc | required | behavioral | **pass** | opened panel content is rendered and visible |
| IC-BAN-01 | banner | required | static | **pass** | close control is a native button (line 3016) |
| IC-BAN-02 | banner | required | static | **pass** | close control has an accessible name (line 3016) |
| IC-BAN-03 | banner | advisory | static | **pass** | icon inside close control is aria-hidden (line 3016) |
| IC-BAN-04 | banner | required | behavioral | **pass** | keyboard activation dismisses the banner |
| IC-CAR-01 | carousel | required | static | **pass** | rail is an accessible keyboard-scrollable region (line 3160) |
| IC-CAR-02 | carousel | advisory | static | **pass** | container has aria-roledescription=carousel and a label (line 3160) |
| IC-CAR-05 | carousel | required | behavioral | **pass** | rail focusable; ArrowRight scrolls: 0->142 |
| IC-FORM-01 | form | required | static | **pass** | control 'pb-form-full-name' is programmatically labelled (line 3224) |
| IC-FORM-01 | form | required | static | **pass** | control 'pb-form-work-email' is programmatically labelled (line 3228) |
| IC-FORM-01 | form | required | static | **pass** | control 'pb-form-company' is programmatically labelled (line 3233) |
| IC-FORM-01 | form | required | static | **pass** | control 'pb-form-phone' is programmatically labelled (line 3237) |
| IC-FORM-01 | form | required | static | **pass** | control 'pb-form-region' is programmatically labelled (line 3242) |
| IC-FORM-01 | form | required | static | **pass** | control 'pb-form-hiring-question' is programmatically labelled (line 3254) |
| IC-FORM-01 | form | required | static | **pass** | control 'quarterly-update' is programmatically labelled (line 3257) |
| IC-FORM-02 | form | required | static | **pass** | form has a real submit button (line 3260) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 3223) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 3227) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 3232) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 3236) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 3241) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 3253) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 3257) |
| IC-FORM-04 | form | required | static | **pass** | fields with error copy communicate requiredness programmatically (line 3224) |
| IC-FORM-07 | form | required | behavioral | **pass** | all visible form controls have browser-computed labels |
| IC-LANG-01 | lang | required | static | **pass** | toggle is a native <summary> inside <details> (line 3019) |
| IC-LANG-02 | lang | required | static | **pass** | toggle has an accessible name (line 3019) |
| IC-LANG-03 | lang | required | static | **pass** | current selection marked via aria-current/aria-selected (line 3019) |
| IC-LANG-04 | lang | advisory | static | **pass** | locale items are links carrying hreflang (line 3019) |
| IC-LANG-05 | lang | required | behavioral | **pass** | Enter opens (open=True), Space toggles back=True |
| IC-LANG-06 | lang | required | behavioral | **pass** | Escape closes the language dropdown |
| IC-LANG-07 | lang | advisory | behavioral | **pass** | open dropdown items are in the Tab order |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Products' is a native button (line 3019) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Solutions' is a native button (line 3019) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Resources' is a native button (line 3019) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Products' carries aria-expanded (line 3019) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Solutions' carries aria-expanded (line 3019) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Resources' carries aria-expanded (line 3019) |
| IC-NAV-03 | nav | required | static | **pass** | no ARIA menu/menubar roles in site nav |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 3019) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 3019) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 3019) |
| IC-NAV-06 | nav | required | behavioral | **pass** | Tab reaches nav triggers, login, and language switcher |
| IC-NAV-07 | nav | required | behavioral | **pass** | hover opens panel=True, keyboard focus opens panel=True |
| IC-NAV-08 | nav | required | behavioral | **pass** | Escape closes the open panel and keeps focus in nav |
| IC-REV-01 | reveal | required | static | **pass** | hidden initial state is gated on a JS-added class (.cs-motion-ready .cs-reveal…) |
| IC-REV-02 | reveal | required | static | **pass** | prefers-reduced-motion forces reveal targets visible |
| IC-REV-03 | reveal | advisory | static | **pass** | timed failsafe present (setTimeout forces all targets visible) |
| IC-REV-04 | reveal | required | behavioral | **pass** | reduced motion: gate applied=False, 0 tagged targets, 0 hidden |
| IC-CAR-04 | carousel | advisory | static | **skip** | no auto-rotation on this rail — pause-control contract not applicable (line 3160) |
| IC-MARQ-01 | marquee | required | static | **skip** | no marquee detected in this lane |
| IC-MARQ-03 | marquee | required | behavioral | **skip** | no marquee detected in this lane |

## Lane: compose/replica

| check | family | severity | layer | status | detail |
|---|---|---|---|---|---|
| IC-CAR-03 | carousel | advisory | static | **advisory** | no slide-level group/roledescription semantics (line 3038) |
| IC-NAV-05 | nav | advisory | static | **advisory** | anchor with role=button in nav chrome — promises Space activation anchors don't have (line 2876) |
| IC-ACC-01 | acc | required | static | **pass** | group of 5 details shares name="acc-feature-accordion" (exclusive single-open) (line 2937) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 2937) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 2942) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 2946) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 2950) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 2954) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 2938) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 2943) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 2947) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 2951) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 2955) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 2938) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 2943) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 2947) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 2951) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 2955) |
| IC-ACC-05 | acc | advisory | static | **pass** | 1 item(s) authored open (line 2937) |
| IC-ACC-06 | acc | required | behavioral | **pass** | summary focusable; Enter and Space toggle the panel |
| IC-ACC-07 | acc | required | behavioral | **pass** | group 0 (named, 5 items): opening item 2 closes item 1 (exclusive group holds) |
| IC-ACC-08 | acc | required | behavioral | **pass** | opened panel content is rendered and visible |
| IC-BAN-01 | banner | required | static | **pass** | close control is a native button (line 2873) |
| IC-BAN-02 | banner | required | static | **pass** | close control has an accessible name (line 2873) |
| IC-BAN-03 | banner | advisory | static | **pass** | icon inside close control is aria-hidden (line 2873) |
| IC-BAN-04 | banner | required | behavioral | **pass** | keyboard activation dismisses the banner |
| IC-CAR-01 | carousel | required | static | **pass** | rail is an accessible keyboard-scrollable region (line 3038) |
| IC-CAR-02 | carousel | advisory | static | **pass** | container has aria-roledescription=carousel and a label (line 3038) |
| IC-CAR-05 | carousel | required | behavioral | **pass** | rail focusable; ArrowRight scrolls: 0->142 |
| IC-LANG-01 | lang | required | static | **pass** | toggle is a native <summary> inside <details> (line 2876) |
| IC-LANG-02 | lang | required | static | **pass** | toggle has an accessible name (line 2876) |
| IC-LANG-03 | lang | required | static | **pass** | current selection marked via aria-current/aria-selected (line 2876) |
| IC-LANG-04 | lang | advisory | static | **pass** | locale items are links carrying hreflang (line 2876) |
| IC-LANG-05 | lang | required | behavioral | **pass** | Enter opens (open=True), Space toggles back=True |
| IC-LANG-06 | lang | required | behavioral | **pass** | Escape closes the language dropdown |
| IC-LANG-07 | lang | advisory | behavioral | **pass** | open dropdown items are in the Tab order |
| IC-MARQ-01 | marquee | required | static | **pass** | duplicated seam half is aria-hidden (line 2910) |
| IC-MARQ-02 | marquee | required | static | **pass** | prefers-reduced-motion neutralizes the marquee animation (line 2894) |
| IC-MARQ-03 | marquee | required | behavioral | **pass** | reduced motion: animation=none/running, content visible=True |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Products' is a native button (line 2876) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Solutions' is a native button (line 2876) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Resources' is a native button (line 2876) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Products' carries aria-expanded (line 2876) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Solutions' carries aria-expanded (line 2876) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Resources' carries aria-expanded (line 2876) |
| IC-NAV-03 | nav | required | static | **pass** | no ARIA menu/menubar roles in site nav |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2876) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2876) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2876) |
| IC-NAV-06 | nav | required | behavioral | **pass** | Tab reaches nav triggers, login, and language switcher |
| IC-NAV-07 | nav | required | behavioral | **pass** | hover opens panel=True, keyboard focus opens panel=True |
| IC-NAV-08 | nav | required | behavioral | **pass** | Escape closes the open panel and keeps focus in nav |
| IC-REV-01 | reveal | required | static | **pass** | hidden initial state is gated on a JS-added class (.cs-motion-ready .cs-reveal…) |
| IC-REV-02 | reveal | required | static | **pass** | prefers-reduced-motion forces reveal targets visible |
| IC-REV-03 | reveal | advisory | static | **pass** | timed failsafe present (setTimeout forces all targets visible) |
| IC-REV-04 | reveal | required | behavioral | **pass** | reduced motion: gate applied=False, 0 tagged targets, 0 hidden |
| IC-CAR-04 | carousel | advisory | static | **skip** | no auto-rotation on this rail — pause-control contract not applicable (line 3038) |
| IC-FORM-01 | form | required | static | **skip** | no form controls or labels detected in this lane |
| IC-FORM-07 | form | required | behavioral | **skip** | no form controls detected in this lane |

