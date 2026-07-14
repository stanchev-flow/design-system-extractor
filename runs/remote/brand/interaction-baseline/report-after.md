# Interaction-Contract Baseline Report

Generated: 2026-07-10T17:54:06+00:00 — auditor v1.0.0 — mode: strict
Contracts: `brand_pipeline/spec/interaction-contracts.md` (WAI-ARIA APG primary; Base UI secondary; Radix tertiary)

## Audited lanes

| lane | file | mtime (UTC) | sha256/12 |
|---|---|---|---|
| compose | `/Users/stanchev/Webflow/campaigns-hackathon/design-system-extractor-mine/runs/remote/brand/compose/index.html` | 2026-07-10T17:44:52+00:00 | `a1f2084d2283` |
| compose/replica | `/Users/stanchev/Webflow/campaigns-hackathon/design-system-extractor-mine/runs/remote/brand/compose/replica/index.html` | 2026-07-10T17:45:44+00:00 | `703850c00977` |
| compose/event-genlaunch | `/Users/stanchev/Webflow/campaigns-hackathon/design-system-extractor-mine/runs/remote/brand/compose/event-genlaunch/index.html` | 2026-07-10T17:45:02+00:00 | `7f9edb7a462d` |
| compose/stress-playbook | `/Users/stanchev/Webflow/campaigns-hackathon/design-system-extractor-mine/runs/remote/brand/compose/stress-playbook/index.html` | 2026-07-10T17:45:32+00:00 | `fe3b268db314` |
| components-preview | `/Users/stanchev/Webflow/campaigns-hackathon/design-system-extractor-mine/runs/remote/brand/components-preview/index.html` | 2026-07-10T17:45:34+00:00 | `57b4fe206ee6` |

If a lane is re-rendered by another agent, re-run the audit; the mtime/sha above identify exactly which HTML was measured.

## Summary — 0 failing required cells, 13 advisory, 164 passing, 24 skipped

### Most impactful gaps (required checks failing, by lane count)

- none — all required checks pass

## Lane: compose

| check | family | severity | layer | status | detail |
|---|---|---|---|---|---|
| IC-CAR-03 | carousel | advisory | static | **advisory** | no slide-level group/roledescription semantics (line 2971) |
| IC-NAV-05 | nav | advisory | static | **advisory** | anchor with role=button in nav chrome — promises Space activation anchors don't have (line 2809) |
| IC-ACC-01 | acc | required | static | **pass** | group of 5 details shares name="acc-feature-accordion" (exclusive single-open) (line 2870) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 2870) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 2875) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 2879) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 2883) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 2887) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 2871) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 2876) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 2880) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 2884) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 2888) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 2871) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 2876) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 2880) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 2884) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 2888) |
| IC-ACC-05 | acc | advisory | static | **pass** | 1 item(s) authored open (line 2870) |
| IC-ACC-06 | acc | required | behavioral | **pass** | summary focusable; Enter and Space toggle the panel |
| IC-ACC-07 | acc | required | behavioral | **pass** | group 0 (named, 5 items): opening item 2 closes item 1 (exclusive group holds) |
| IC-ACC-08 | acc | required | behavioral | **pass** | opened panel content is rendered and visible |
| IC-BAN-01 | banner | required | static | **pass** | close control is a native button (line 2806) |
| IC-BAN-02 | banner | required | static | **pass** | close control has an accessible name (line 2806) |
| IC-BAN-03 | banner | advisory | static | **pass** | icon inside close control is aria-hidden (line 2806) |
| IC-BAN-04 | banner | required | behavioral | **pass** | keyboard activation dismisses the banner |
| IC-CAR-01 | carousel | required | static | **pass** | rail is an accessible keyboard-scrollable region (line 2971) |
| IC-CAR-02 | carousel | advisory | static | **pass** | container has aria-roledescription=carousel and a label (line 2971) |
| IC-CAR-05 | carousel | required | behavioral | **pass** | rail focusable; ArrowRight scrolls: 0->142 |
| IC-LANG-01 | lang | required | static | **pass** | toggle is a native <summary> inside <details> (line 2809) |
| IC-LANG-02 | lang | required | static | **pass** | toggle has an accessible name (line 2809) |
| IC-LANG-03 | lang | required | static | **pass** | current selection marked via aria-current/aria-selected (line 2809) |
| IC-LANG-04 | lang | advisory | static | **pass** | locale items are links carrying hreflang (line 2809) |
| IC-LANG-05 | lang | required | behavioral | **pass** | Enter opens (open=True), Space toggles back=True |
| IC-LANG-06 | lang | required | behavioral | **pass** | Escape closes the language dropdown |
| IC-LANG-07 | lang | advisory | behavioral | **pass** | open dropdown items are in the Tab order |
| IC-MARQ-01 | marquee | required | static | **pass** | duplicated seam half is aria-hidden (line 2843) |
| IC-MARQ-02 | marquee | required | static | **pass** | prefers-reduced-motion neutralizes the marquee animation (line 2827) |
| IC-MARQ-03 | marquee | required | behavioral | **pass** | reduced motion: animation=none/running, content visible=True |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Products' is a native button (line 2809) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Solutions' is a native button (line 2809) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Resources' is a native button (line 2809) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Products' carries aria-expanded (line 2809) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Solutions' carries aria-expanded (line 2809) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Resources' carries aria-expanded (line 2809) |
| IC-NAV-03 | nav | required | static | **pass** | no ARIA menu/menubar roles in site nav |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2809) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2809) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2809) |
| IC-NAV-06 | nav | required | behavioral | **pass** | Tab reaches nav triggers, login, and language switcher |
| IC-NAV-07 | nav | required | behavioral | **pass** | hover opens panel=True, keyboard focus opens panel=True |
| IC-NAV-08 | nav | required | behavioral | **pass** | Escape closes the open panel and keeps focus in nav |
| IC-REV-01 | reveal | required | static | **pass** | hidden initial state is gated on a JS-added class (.cs-motion-ready .cs-reveal…) |
| IC-REV-02 | reveal | required | static | **pass** | prefers-reduced-motion forces reveal targets visible |
| IC-REV-03 | reveal | advisory | static | **pass** | timed failsafe present (setTimeout forces all targets visible) |
| IC-REV-04 | reveal | required | behavioral | **pass** | reduced motion: gate applied=False, 0 tagged targets, 0 hidden |
| IC-CAR-04 | carousel | advisory | static | **skip** | no auto-rotation on this rail — pause-control contract not applicable (line 2971) |
| IC-FORM-01 | form | required | static | **skip** | no form controls or labels detected in this lane |
| IC-FORM-07 | form | required | behavioral | **skip** | no form controls detected in this lane |

## Lane: compose/replica

| check | family | severity | layer | status | detail |
|---|---|---|---|---|---|
| IC-CAR-03 | carousel | advisory | static | **advisory** | no slide-level group/roledescription semantics (line 2967) |
| IC-NAV-05 | nav | advisory | static | **advisory** | anchor with role=button in nav chrome — promises Space activation anchors don't have (line 2805) |
| IC-ACC-01 | acc | required | static | **pass** | group of 5 details shares name="acc-feature-accordion" (exclusive single-open) (line 2866) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 2866) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 2871) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 2875) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 2879) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 2883) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 2867) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 2872) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 2876) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 2880) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 2884) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 2867) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 2872) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 2876) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 2880) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 2884) |
| IC-ACC-05 | acc | advisory | static | **pass** | 1 item(s) authored open (line 2866) |
| IC-ACC-06 | acc | required | behavioral | **pass** | summary focusable; Enter and Space toggle the panel |
| IC-ACC-07 | acc | required | behavioral | **pass** | group 0 (named, 5 items): opening item 2 closes item 1 (exclusive group holds) |
| IC-ACC-08 | acc | required | behavioral | **pass** | opened panel content is rendered and visible |
| IC-BAN-01 | banner | required | static | **pass** | close control is a native button (line 2802) |
| IC-BAN-02 | banner | required | static | **pass** | close control has an accessible name (line 2802) |
| IC-BAN-03 | banner | advisory | static | **pass** | icon inside close control is aria-hidden (line 2802) |
| IC-BAN-04 | banner | required | behavioral | **pass** | keyboard activation dismisses the banner |
| IC-CAR-01 | carousel | required | static | **pass** | rail is an accessible keyboard-scrollable region (line 2967) |
| IC-CAR-02 | carousel | advisory | static | **pass** | container has aria-roledescription=carousel and a label (line 2967) |
| IC-CAR-05 | carousel | required | behavioral | **pass** | rail focusable; ArrowRight scrolls: 0->142 |
| IC-LANG-01 | lang | required | static | **pass** | toggle is a native <summary> inside <details> (line 2805) |
| IC-LANG-02 | lang | required | static | **pass** | toggle has an accessible name (line 2805) |
| IC-LANG-03 | lang | required | static | **pass** | current selection marked via aria-current/aria-selected (line 2805) |
| IC-LANG-04 | lang | advisory | static | **pass** | locale items are links carrying hreflang (line 2805) |
| IC-LANG-05 | lang | required | behavioral | **pass** | Enter opens (open=True), Space toggles back=True |
| IC-LANG-06 | lang | required | behavioral | **pass** | Escape closes the language dropdown |
| IC-LANG-07 | lang | advisory | behavioral | **pass** | open dropdown items are in the Tab order |
| IC-MARQ-01 | marquee | required | static | **pass** | duplicated seam half is aria-hidden (line 2839) |
| IC-MARQ-02 | marquee | required | static | **pass** | prefers-reduced-motion neutralizes the marquee animation (line 2823) |
| IC-MARQ-03 | marquee | required | behavioral | **pass** | reduced motion: animation=none/running, content visible=True |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Products' is a native button (line 2805) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Solutions' is a native button (line 2805) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Resources' is a native button (line 2805) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Products' carries aria-expanded (line 2805) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Solutions' carries aria-expanded (line 2805) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Resources' carries aria-expanded (line 2805) |
| IC-NAV-03 | nav | required | static | **pass** | no ARIA menu/menubar roles in site nav |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2805) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2805) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2805) |
| IC-NAV-06 | nav | required | behavioral | **pass** | Tab reaches nav triggers, login, and language switcher |
| IC-NAV-07 | nav | required | behavioral | **pass** | hover opens panel=True, keyboard focus opens panel=True |
| IC-NAV-08 | nav | required | behavioral | **pass** | Escape closes the open panel and keeps focus in nav |
| IC-REV-01 | reveal | required | static | **pass** | hidden initial state is gated on a JS-added class (.cs-motion-ready .cs-reveal…) |
| IC-REV-02 | reveal | required | static | **pass** | prefers-reduced-motion forces reveal targets visible |
| IC-REV-03 | reveal | advisory | static | **pass** | timed failsafe present (setTimeout forces all targets visible) |
| IC-REV-04 | reveal | required | behavioral | **pass** | reduced motion: gate applied=False, 0 tagged targets, 0 hidden |
| IC-CAR-04 | carousel | advisory | static | **skip** | no auto-rotation on this rail — pause-control contract not applicable (line 2967) |
| IC-FORM-01 | form | required | static | **skip** | no form controls or labels detected in this lane |
| IC-FORM-07 | form | required | behavioral | **skip** | no form controls detected in this lane |

## Lane: compose/event-genlaunch

| check | family | severity | layer | status | detail |
|---|---|---|---|---|---|
| IC-FORM-05 | form | advisory | static | **advisory** | field help text not linked to its control via aria-describedby (line 2915) |
| IC-FORM-06 | form | advisory | static | **advisory** | error copy lives only in data-error attributes — invisible to AT (line 2910) |
| IC-NAV-05 | nav | advisory | static | **advisory** | anchor with role=button in nav chrome — promises Space activation anchors don't have (line 2719) |
| IC-ACC-01 | acc | required | static | **pass** | group of 4 details shares name="faq-event-agenda" (exclusive single-open) (line 2824) |
| IC-ACC-01 | acc | required | static | **pass** | group of 6 details shares name="faq-event-faq" (exclusive single-open) (line 2895) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 2824) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 2824) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 2824) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 2824) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 2895) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 2895) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 2895) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 2895) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 2895) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 2895) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 2824) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 2824) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 2824) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 2824) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 2895) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 2895) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 2895) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 2895) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 2895) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 2895) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 2824) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 2824) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 2824) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 2824) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 2895) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 2895) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 2895) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 2895) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 2895) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 2895) |
| IC-ACC-05 | acc | advisory | static | **pass** | 1 item(s) authored open (line 2824) |
| IC-ACC-05 | acc | advisory | static | **pass** | 1 item(s) authored open (line 2895) |
| IC-ACC-06 | acc | required | behavioral | **pass** | summary focusable; Enter and Space toggle the panel |
| IC-ACC-07 | acc | required | behavioral | **pass** | group 0 (named, 4 items): opening item 2 closes item 1 (exclusive group holds) |
| IC-ACC-08 | acc | required | behavioral | **pass** | opened panel content is rendered and visible |
| IC-BAN-01 | banner | required | static | **pass** | close control is a native button (line 2716) |
| IC-BAN-02 | banner | required | static | **pass** | close control has an accessible name (line 2716) |
| IC-BAN-03 | banner | advisory | static | **pass** | icon inside close control is aria-hidden (line 2716) |
| IC-BAN-04 | banner | required | behavioral | **pass** | keyboard activation dismisses the banner |
| IC-FORM-01 | form | required | static | **pass** | control 'event-signup-full-name' is programmatically labelled (line 2910) |
| IC-FORM-01 | form | required | static | **pass** | control 'event-signup-work-email' is programmatically labelled (line 2914) |
| IC-FORM-01 | form | required | static | **pass** | control 'event-signup-company' is programmatically labelled (line 2919) |
| IC-FORM-01 | form | required | static | **pass** | control 'event-signup-company-size' is programmatically labelled (line 2923) |
| IC-FORM-01 | form | required | static | **pass** | control 'event-signup-role' is programmatically labelled (line 2934) |
| IC-FORM-01 | form | required | static | **pass** | control 'pass' is programmatically labelled (line 2946) |
| IC-FORM-01 | form | required | static | **pass** | control 'pass' is programmatically labelled (line 2947) |
| IC-FORM-01 | form | required | static | **pass** | control 'pass' is programmatically labelled (line 2948) |
| IC-FORM-01 | form | required | static | **pass** | control 'product-news' is programmatically labelled (line 2951) |
| IC-FORM-02 | form | required | static | **pass** | form has a real submit button (line 2954) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 2909) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 2913) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 2918) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 2922) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 2933) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 2946) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 2947) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 2948) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 2951) |
| IC-FORM-04 | form | required | static | **pass** | fields with error copy communicate requiredness programmatically (line 2910) |
| IC-FORM-07 | form | required | behavioral | **pass** | all visible form controls have browser-computed labels |
| IC-LANG-01 | lang | required | static | **pass** | toggle is a native <summary> inside <details> (line 2719) |
| IC-LANG-02 | lang | required | static | **pass** | toggle has an accessible name (line 2719) |
| IC-LANG-03 | lang | required | static | **pass** | current selection marked via aria-current/aria-selected (line 2719) |
| IC-LANG-04 | lang | advisory | static | **pass** | locale items are links carrying hreflang (line 2719) |
| IC-LANG-05 | lang | required | behavioral | **pass** | Enter opens (open=True), Space toggles back=True |
| IC-LANG-06 | lang | required | behavioral | **pass** | Escape closes the language dropdown |
| IC-LANG-07 | lang | advisory | behavioral | **pass** | open dropdown items are in the Tab order |
| IC-MARQ-01 | marquee | required | static | **pass** | duplicated seam half is aria-hidden (line 2754) |
| IC-MARQ-02 | marquee | required | static | **pass** | prefers-reduced-motion neutralizes the marquee animation (line 2738) |
| IC-MARQ-03 | marquee | required | behavioral | **pass** | reduced motion: animation=none/running, content visible=True |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Products' is a native button (line 2719) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Solutions' is a native button (line 2719) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Resources' is a native button (line 2719) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Products' carries aria-expanded (line 2719) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Solutions' carries aria-expanded (line 2719) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Resources' carries aria-expanded (line 2719) |
| IC-NAV-03 | nav | required | static | **pass** | no ARIA menu/menubar roles in site nav |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2719) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2719) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2719) |
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
| IC-CAR-03 | carousel | advisory | static | **advisory** | no slide-level group/roledescription semantics (line 3067) |
| IC-FORM-05 | form | advisory | static | **advisory** | field help text not linked to its control via aria-describedby (line 3136) |
| IC-FORM-06 | form | advisory | static | **advisory** | error copy lives only in data-error attributes — invisible to AT (line 3131) |
| IC-NAV-05 | nav | advisory | static | **advisory** | anchor with role=button in nav chrome — promises Space activation anchors don't have (line 2925) |
| IC-ACC-01 | acc | required | static | **pass** | group of 4 details shares name="acc-pb-process" (exclusive single-open) (line 3010) |
| IC-ACC-01 | acc | required | static | **pass** | group of 5 details is a declared multi-open family (data-acc-multi="authored") — single-open grouping waived (line 3116) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 3010) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 3015) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 3019) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 3023) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 3116) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 3116) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 3116) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 3116) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 3116) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 3011) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 3016) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 3020) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 3024) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 3116) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 3116) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 3116) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 3116) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 3116) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 3011) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 3016) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 3020) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 3024) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 3116) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 3116) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 3116) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 3116) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 3116) |
| IC-ACC-05 | acc | advisory | static | **pass** | 1 item(s) authored open (line 3010) |
| IC-ACC-05 | acc | advisory | static | **pass** | 1 item(s) authored open (line 3116) |
| IC-ACC-06 | acc | required | behavioral | **pass** | summary focusable; Enter and Space toggle the panel |
| IC-ACC-07 | acc | required | behavioral | **pass** | group 0 (named, 4 items): opening item 2 closes item 1 (exclusive group holds) |
| IC-ACC-07 | acc | required | behavioral | **pass** | group 1 (declared multi-open, 5 items): items toggle independently (authored multi-open holds) |
| IC-ACC-08 | acc | required | behavioral | **pass** | opened panel content is rendered and visible |
| IC-BAN-01 | banner | required | static | **pass** | close control is a native button (line 2922) |
| IC-BAN-02 | banner | required | static | **pass** | close control has an accessible name (line 2922) |
| IC-BAN-03 | banner | advisory | static | **pass** | icon inside close control is aria-hidden (line 2922) |
| IC-BAN-04 | banner | required | behavioral | **pass** | keyboard activation dismisses the banner |
| IC-CAR-01 | carousel | required | static | **pass** | rail is an accessible keyboard-scrollable region (line 3067) |
| IC-CAR-02 | carousel | advisory | static | **pass** | container has aria-roledescription=carousel and a label (line 3067) |
| IC-CAR-05 | carousel | required | behavioral | **pass** | rail focusable; ArrowRight scrolls: 0->142 |
| IC-FORM-01 | form | required | static | **pass** | control 'pb-form-full-name' is programmatically labelled (line 3131) |
| IC-FORM-01 | form | required | static | **pass** | control 'pb-form-work-email' is programmatically labelled (line 3135) |
| IC-FORM-01 | form | required | static | **pass** | control 'pb-form-company' is programmatically labelled (line 3140) |
| IC-FORM-01 | form | required | static | **pass** | control 'pb-form-phone' is programmatically labelled (line 3144) |
| IC-FORM-01 | form | required | static | **pass** | control 'pb-form-region' is programmatically labelled (line 3149) |
| IC-FORM-01 | form | required | static | **pass** | control 'pb-form-hiring-question' is programmatically labelled (line 3161) |
| IC-FORM-01 | form | required | static | **pass** | control 'quarterly-update' is programmatically labelled (line 3164) |
| IC-FORM-02 | form | required | static | **pass** | form has a real submit button (line 3167) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 3130) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 3134) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 3139) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 3143) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 3148) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 3160) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 3164) |
| IC-FORM-04 | form | required | static | **pass** | fields with error copy communicate requiredness programmatically (line 3131) |
| IC-FORM-07 | form | required | behavioral | **pass** | all visible form controls have browser-computed labels |
| IC-LANG-01 | lang | required | static | **pass** | toggle is a native <summary> inside <details> (line 2925) |
| IC-LANG-02 | lang | required | static | **pass** | toggle has an accessible name (line 2925) |
| IC-LANG-03 | lang | required | static | **pass** | current selection marked via aria-current/aria-selected (line 2925) |
| IC-LANG-04 | lang | advisory | static | **pass** | locale items are links carrying hreflang (line 2925) |
| IC-LANG-05 | lang | required | behavioral | **pass** | Enter opens (open=True), Space toggles back=True |
| IC-LANG-06 | lang | required | behavioral | **pass** | Escape closes the language dropdown |
| IC-LANG-07 | lang | advisory | behavioral | **pass** | open dropdown items are in the Tab order |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Products' is a native button (line 2925) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Solutions' is a native button (line 2925) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Resources' is a native button (line 2925) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Products' carries aria-expanded (line 2925) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Solutions' carries aria-expanded (line 2925) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Resources' carries aria-expanded (line 2925) |
| IC-NAV-03 | nav | required | static | **pass** | no ARIA menu/menubar roles in site nav |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2925) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2925) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2925) |
| IC-NAV-06 | nav | required | behavioral | **pass** | Tab reaches nav triggers, login, and language switcher |
| IC-NAV-07 | nav | required | behavioral | **pass** | hover opens panel=True, keyboard focus opens panel=True |
| IC-NAV-08 | nav | required | behavioral | **pass** | Escape closes the open panel and keeps focus in nav |
| IC-REV-01 | reveal | required | static | **pass** | hidden initial state is gated on a JS-added class (.cs-motion-ready .cs-reveal…) |
| IC-REV-02 | reveal | required | static | **pass** | prefers-reduced-motion forces reveal targets visible |
| IC-REV-03 | reveal | advisory | static | **pass** | timed failsafe present (setTimeout forces all targets visible) |
| IC-REV-04 | reveal | required | behavioral | **pass** | reduced motion: gate applied=False, 0 tagged targets, 0 hidden |
| IC-CAR-04 | carousel | advisory | static | **skip** | no auto-rotation on this rail — pause-control contract not applicable (line 3067) |
| IC-MARQ-01 | marquee | required | static | **skip** | no marquee detected in this lane |
| IC-MARQ-03 | marquee | required | behavioral | **skip** | no marquee detected in this lane |

## Lane: components-preview

| check | family | severity | layer | status | detail |
|---|---|---|---|---|---|
| IC-NAV-05 | nav | advisory | static | **advisory** | anchor with role=button in nav chrome — promises Space activation anchors don't have (line 2087) |
| IC-REV-03 | reveal | advisory | static | **advisory** | no timed failsafe in the reveal script |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 2501) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 2502) |
| IC-FORM-01 | form | required | static | **pass** | control 'text' is programmatically labelled (line 1981) |
| IC-FORM-01 | form | required | static | **pass** | control 'text' is programmatically labelled (line 2045) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 1981) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 2045) |
| IC-FORM-07 | form | required | behavioral | **pass** | all visible form controls have browser-computed labels |
| IC-LANG-01 | lang | required | static | **pass** | toggle is a native <summary> inside <details> (line 2087) |
| IC-LANG-02 | lang | required | static | **pass** | toggle has an accessible name (line 2087) |
| IC-LANG-03 | lang | required | static | **pass** | current selection marked via aria-current/aria-selected (line 2087) |
| IC-LANG-04 | lang | advisory | static | **pass** | locale items are links carrying hreflang (line 2087) |
| IC-LANG-05 | lang | required | behavioral | **pass** | Enter opens (open=True), Space toggles back=True |
| IC-LANG-06 | lang | required | behavioral | **pass** | Escape closes the language dropdown |
| IC-LANG-07 | lang | advisory | behavioral | **pass** | open dropdown items are in the Tab order |
| IC-NAV-03 | nav | required | static | **pass** | no ARIA menu/menubar roles in site nav |
| IC-REV-01 | reveal | required | static | **pass** | hidden initial state is gated on a JS-added class (.cs-motion-ready .cs-reveal…) |
| IC-REV-02 | reveal | required | static | **pass** | prefers-reduced-motion forces reveal targets visible |
| IC-REV-04 | reveal | required | behavioral | **pass** | reduced motion: gate applied=False, 0 tagged targets, 0 hidden |
| IC-ACC-06 | acc | required | behavioral | **skip** | no accordion groups detected in this lane |
| IC-ACC-07 | acc | required | behavioral | **skip** | no accordion groups detected in this lane |
| IC-ACC-08 | acc | required | behavioral | **skip** | no accordion groups detected in this lane |
| IC-BAN-01 | banner | required | static | **skip** | no dismissible banner detected in this lane |
| IC-BAN-04 | banner | required | behavioral | **skip** | no dismissible banner detected in this lane |
| IC-CAR-01 | carousel | required | static | **skip** | no carousel/edge-cut rail detected in this lane |
| IC-CAR-05 | carousel | required | behavioral | **skip** | no carousel/edge-cut rail detected in this lane |
| IC-FORM-04 | form | required | static | **skip** | no required-field signals detected in this lane |
| IC-MARQ-01 | marquee | required | static | **skip** | no marquee detected in this lane |
| IC-MARQ-03 | marquee | required | behavioral | **skip** | no marquee detected in this lane |
| IC-NAV-06 | nav | required | behavioral | **skip** | no disclosure-nav instances detected in this lane |
| IC-NAV-07 | nav | required | behavioral | **skip** | no disclosure-nav instances detected in this lane |
| IC-NAV-08 | nav | required | behavioral | **skip** | no disclosure-nav instances detected in this lane |

