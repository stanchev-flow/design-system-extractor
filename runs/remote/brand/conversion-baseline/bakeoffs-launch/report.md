# Conversion-structure check (conversion-structure.v1)

2026-07-14T17:58:29Z — advisory-first wiring; hardFloor rows gate from birth

## runs/remote/brand/compose/bakeoff-sol — PASS with 3 WARN(s) — campaign `product-launch` (explicit, ground: rendered)

sequence: workforce-intelligence-hero[hero] -> reporting-gap[feature-grid] -> decision-layer-capabilities[feature-grid] -> how-workforce-intelligence-works[feature-grid] -> leadership-views[feature-grid] -> workflow-comparison[feature-grid] -> remote-customer-perspectives[carousel,quote] -> operational-trust[feature-grid] -> workforce-intelligence-faq[faq] -> qualified-demo-request[capture-form,cta-band]

| kind | families | sev | verdict | detail |
|---|---|---|---|---|
| opens | hero | req | ok | opens with hero |
| present | feature-grid | req | WARN | 6 section(s) bind ['feature-grid'] (budget 1-3) |
| before | feature-grid, cta-band | adv | ok | first feature-grid at 2, first cta-band at 10 |
| present | logo-strip, quote, stat-band | adv | ok | 1 section(s) bind ['logo-strip', 'quote', 'stat-band'] (budget 1-3) |
| afterIndex | capture-form | adv | ok | first capture-form at index 10 (>= minIndex 3) |
| closes | cta-band, capture-form | req | ok | closes on ['capture-form', 'cta-band'] |
| depthBand | — | adv | WARN | 10 content section(s) (band 5-9, funnel awareness) |
| formDepth | capture-form | adv | WARN | 8 visible field(s) (band 0-3) |

## runs/remote/brand/compose/bakeoff-opus — PASS with 3 WARN(s) — campaign `product-launch` (explicit, ground: rendered)

sequence: hero[hero] -> problem[feature-grid] -> product-value[feature-grid] -> capabilities[feature-grid] -> how-it-works[feature-grid] -> comparison[feature-grid] -> proof[carousel,quote] -> conversion-beat[cta-band] -> faq[faq] -> lead-form[capture-form,cta-band]

| kind | families | sev | verdict | detail |
|---|---|---|---|---|
| opens | hero | req | ok | opens with hero |
| present | feature-grid | req | WARN | 5 section(s) bind ['feature-grid'] (budget 1-3) |
| before | feature-grid, cta-band | adv | ok | first feature-grid at 2, first cta-band at 8 |
| present | logo-strip, quote, stat-band | adv | ok | 1 section(s) bind ['logo-strip', 'quote', 'stat-band'] (budget 1-3) |
| afterIndex | capture-form | adv | ok | first capture-form at index 10 (>= minIndex 3) |
| closes | cta-band, capture-form | req | ok | closes on ['capture-form', 'cta-band'] |
| depthBand | — | adv | WARN | 10 content section(s) (band 5-9, funnel awareness) |
| formDepth | capture-form | adv | WARN | 6 visible field(s) (band 0-3) |
