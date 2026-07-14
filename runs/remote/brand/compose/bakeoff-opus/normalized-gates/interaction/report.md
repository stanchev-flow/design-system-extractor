# Interaction-Contract Baseline Report

Generated: 2026-07-10T19:05:29+00:00 — auditor v1.0.0 — mode: strict
Contracts: `brand_pipeline/spec/interaction-contracts.md` (WAI-ARIA APG primary; Base UI secondary; Radix tertiary)

## Audited lanes

| lane | file | mtime (UTC) | sha256/12 |
|---|---|---|---|
| compose/bakeoff-opus | `/Users/stanchev/Webflow/campaigns-hackathon/design-system-extractor-mine/runs/remote/brand/compose/bakeoff-opus/index.html` | 2026-07-10T19:01:34+00:00 | `e0489d2846c3` |

If a lane is re-rendered by another agent, re-run the audit; the mtime/sha above identify exactly which HTML was measured.

## Summary — 0 failing required cells, 2 advisory, 38 passing, 3 skipped

### Most impactful gaps (required checks failing, by lane count)

- none — all required checks pass

## Lane: compose/bakeoff-opus

| check | family | severity | layer | status | detail |
|---|---|---|---|---|---|
| IC-CAR-03 | carousel | advisory | static | **advisory** | no slide-level group/roledescription semantics (line 3093) |
| IC-NAV-05 | nav | advisory | static | **advisory** | anchor with role=button in nav chrome — promises Space activation anchors don't have (line 2955) |
| IC-ACC-01 | acc | required | static | **pass** | group of 4 details shares name="acc-product-value" (exclusive single-open) (line 2989) |
| IC-ACC-01 | acc | required | static | **pass** | group of 5 details shares name="faq-faq" (exclusive single-open) (line 3134) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 2989) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 2994) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 2998) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 3002) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 3134) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 3134) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 3134) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 3134) |
| IC-ACC-02 | acc | required | static | **pass** | details has a <summary> as first element child (line 3134) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 2990) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 2995) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 2999) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 3003) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 3134) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 3134) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 3134) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 3134) |
| IC-ACC-03 | acc | required | static | **pass** | summary has accessible text (line 3134) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 2990) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 2995) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 2999) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 3003) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 3134) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 3134) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 3134) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 3134) |
| IC-ACC-04 | acc | advisory | static | **pass** | decorative summary icons are aria-hidden (line 3134) |
| IC-ACC-05 | acc | advisory | static | **pass** | 1 item(s) authored open (line 2989) |
| IC-ACC-05 | acc | advisory | static | **pass** | 1 item(s) authored open (line 3134) |
| IC-ACC-06 | acc | required | behavioral | **pass** | summary focusable; Enter and Space toggle the panel |
| IC-ACC-07 | acc | required | behavioral | **pass** | group 0 (named, 4 items): opening item 2 closes item 1 (exclusive group holds) |
| IC-ACC-08 | acc | required | behavioral | **pass** | opened panel content is rendered and visible |
| IC-BAN-01 | banner | required | static | **pass** | close control is a native button (line 2952) |
| IC-BAN-02 | banner | required | static | **pass** | close control has an accessible name (line 2952) |
| IC-BAN-03 | banner | advisory | static | **pass** | icon inside close control is aria-hidden (line 2952) |
| IC-BAN-04 | banner | required | behavioral | **pass** | keyboard activation dismisses the banner |
| IC-CAR-01 | carousel | required | static | **pass** | rail is an accessible keyboard-scrollable region (line 3093) |
| IC-CAR-02 | carousel | advisory | static | **pass** | container has aria-roledescription=carousel and a label (line 3093) |
| IC-CAR-05 | carousel | required | behavioral | **pass** | rail focusable; ArrowRight scrolls: 0->142 |
| IC-FORM-01 | form | required | static | **pass** | control 'lead-form-name' is programmatically labelled (line 3147) |
| IC-FORM-01 | form | required | static | **pass** | control 'lead-form-email' is programmatically labelled (line 3151) |
| IC-FORM-01 | form | required | static | **pass** | control 'lead-form-company' is programmatically labelled (line 3155) |
| IC-FORM-01 | form | required | static | **pass** | control 'lead-form-size' is programmatically labelled (line 3159) |
| IC-FORM-01 | form | required | static | **pass** | control 'lead-form-region' is programmatically labelled (line 3167) |
| IC-FORM-01 | form | required | static | **pass** | control 'lead-form-notes' is programmatically labelled (line 3177) |
| IC-FORM-02 | form | required | static | **pass** | form has a real submit button (line 3181) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 3146) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 3150) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 3154) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 3158) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 3166) |
| IC-FORM-03 | form | required | static | **pass** | label is associated with a real control (line 3176) |
| IC-FORM-04 | form | required | static | **pass** | required fields use the required attribute (line 3147) |
| IC-FORM-07 | form | required | behavioral | **pass** | all visible form controls have browser-computed labels |
| IC-LANG-01 | lang | required | static | **pass** | toggle is a native <summary> inside <details> (line 2955) |
| IC-LANG-02 | lang | required | static | **pass** | toggle has an accessible name (line 2955) |
| IC-LANG-03 | lang | required | static | **pass** | current selection marked via aria-current/aria-selected (line 2955) |
| IC-LANG-04 | lang | advisory | static | **pass** | locale items are links carrying hreflang (line 2955) |
| IC-LANG-05 | lang | required | behavioral | **pass** | Enter opens (open=True), Space toggles back=True |
| IC-LANG-06 | lang | required | behavioral | **pass** | Escape closes the language dropdown |
| IC-LANG-07 | lang | advisory | behavioral | **pass** | open dropdown items are in the Tab order |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Products' is a native button (line 2955) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Solutions' is a native button (line 2955) |
| IC-NAV-01 | nav | required | static | **pass** | trigger 'Resources' is a native button (line 2955) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Products' carries aria-expanded (line 2955) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Solutions' carries aria-expanded (line 2955) |
| IC-NAV-02 | nav | required | static | **pass** | trigger 'Resources' carries aria-expanded (line 2955) |
| IC-NAV-03 | nav | required | static | **pass** | no ARIA menu/menubar roles in site nav |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2955) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2955) |
| IC-NAV-04 | nav | advisory | static | **pass** | trigger references its panel via aria-controls (line 2955) |
| IC-NAV-06 | nav | required | behavioral | **pass** | Tab reaches nav triggers, login, and language switcher |
| IC-NAV-07 | nav | required | behavioral | **pass** | hover opens panel=True, keyboard focus opens panel=True |
| IC-NAV-08 | nav | required | behavioral | **pass** | Escape closes the open panel and keeps focus in nav |
| IC-REV-01 | reveal | required | static | **pass** | hidden initial state is gated on a JS-added class (.cs-motion-ready .cs-reveal…) |
| IC-REV-02 | reveal | required | static | **pass** | prefers-reduced-motion forces reveal targets visible |
| IC-REV-03 | reveal | advisory | static | **pass** | timed failsafe present (setTimeout forces all targets visible) |
| IC-REV-04 | reveal | required | behavioral | **pass** | reduced motion: gate applied=False, 0 tagged targets, 0 hidden |
| IC-CAR-04 | carousel | advisory | static | **skip** | no auto-rotation on this rail — pause-control contract not applicable (line 3093) |
| IC-MARQ-01 | marquee | required | static | **skip** | no marquee detected in this lane |
| IC-MARQ-03 | marquee | required | behavioral | **skip** | no marquee detected in this lane |

