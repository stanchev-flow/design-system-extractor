# Fact-consumption audit (AS-83) — target: generation

**PASS** — 5 consumed / 0 unconsumed / 2 excluded / 7 delegated.

| family | status | origin | consumer | evidence | provenance |
|---|---|---|---|---|---|
| `responsive.hero` | excluded | extracted | component_render.hero_responsive_css | CSS marker '(fact-gated: layouts[].responsive)' | hero bound height mechanic is viewport-relative (viewport-minus-nav); nav offset from measured --global-nav-header-height |
| `responsive.hero.primaryButton` | excluded | extracted | component_render.hero_primary_button_css | CSS marker '(fact-gated: layouts[].responsive.primaryButton)' | primary action measured @1440 (display/font-size/line-height/border/padding) — the button box the composer left un-grounded |
| `responsive.footer` | consumed | extracted | component_render.footer_responsive_css | CSS marker '(fact-gated: footer.responsive)' | 1 measured @media reflow breakpoint(s); stacked below 900px, 2 column(s) at/above (@media(width >= 900px) column-count:2) |
| `responsive.headings.lineHeights` | consumed | extracted | component_render.heading_responsive_css | CSS marker '(fact-gated: responsive.headings.lineHeights)' | measured heading computedLadder line-heights (stable across the viewport ladder) the composer type scale mis-derived |
| `responsive.nav.collapse` | consumed | extracted | component_render.nav_collapse_css + compose_section._navbar_props | CSS marker '(fact-gated: responsive.nav.collapse)' | mega-nav panel container (.global-nav-main .global-nav-main-inner) paints var(--cl-color-container-01) → resolved #ffffff; our .cs-mega measured transparent |
| `responsive.nav.panelSurface` | consumed | extracted | component_render.render_mega (panel surface override) | .cs-mega { background: <resolved panel literal> } | mega-nav panel container (.global-nav-main .global-nav-main-inner) paints var(--cl-color-container-01) → resolved #ffffff; our .cs-mega measured transparent |
| `responsive.buttons.purgeHoverTransform` | consumed | extracted | component_render._button_variant_css (motion purge) | no 'transform: translateY(-1px)' in the emitted button CSS | source button hover/focus rules declare no transform (bg/border/color swap only); the composer translateY(-1px) lift is un-grounded motion — purged brand-wide (provenance doctrine) |
| `layout.specialTreatment` | delegated | extracted | onbrand_check.check_anatomy_presence (AS-81) + composition invariants | verified by the owning sibling gate | enumerated fact family |
| `layout.surfaceIntent` | delegated | extracted | onbrand fidelity (composed sections paint their own surfaces) | verified by the owning sibling gate | enumerated fact family |
| `tokens.type` | delegated | extracted | css_fidelity.heading_tier_divergences (C-checks) | verified by the owning sibling gate | enumerated fact family |
| `tokens.spacing` | delegated | extracted | css_fidelity.spacing_tier_divergences (C-checks) | verified by the owning sibling gate | enumerated fact family |
| `tokens.radius` | delegated | extracted | css_fidelity.radius_tier_divergences (C-checks) | verified by the owning sibling gate | enumerated fact family |
| `tokens.colors` | delegated | extracted | css_fidelity.color_role_divergences (C-checks) | verified by the owning sibling gate | enumerated fact family |
| `layoutGrammar.actionGroup` | delegated | designed | composition_lint.lint_knobs (AS-63) + onbrand fidelity | verified by the owning sibling gate | enumerated fact family |
