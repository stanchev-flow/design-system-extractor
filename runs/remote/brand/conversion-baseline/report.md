# Conversion-structure check (conversion-structure.v1)

2026-07-14T17:53:47Z — advisory-first wiring; hardFloor rows gate from birth

## runs/remote/brand/compose/event-genlaunch — PASS — campaign `webinar-event` (explicit, ground: rendered)

sequence: event-hero[hero] -> event-proof[carousel,logo-strip] -> event-bento[feature-grid] -> event-agenda[-] -> event-quote[feature-grid,quote] -> event-passes[pricing-tiers] -> event-faq[faq] -> event-signup[capture-form,cta-band]

| kind | families | sev | verdict | detail |
|---|---|---|---|---|
| opens | hero | req | ok | opens with hero |
| present | capture-form | req | ok | 1 section(s) bind ['capture-form'] (budget 1-1) |
| closes | capture-form, cta-band | req | ok | closes on ['capture-form', 'cta-band'] |
| window | logo-strip, quote, stat-band | adv | ok | first ['logo-strip', 'quote', 'stat-band'] match at index 2 (within the first 3) |
| before | faq, capture-form | adv | ok | first faq at 7, first capture-form at 8 |
| present | faq | adv | ok | 1 section(s) bind ['faq'] (budget 1-1) |
| present | pricing-tiers | adv | ok | 1 section(s) bind ['pricing-tiers'] (budget 0-1) |
| depthBand | — | adv | ok | 8 content section(s) (band 4-8, funnel consideration) |
| formDepth | capture-form | adv | ok | 7 visible field(s) (band 4-8) |
| hardFloor:conversion-moment | — | hard | ok | capture-form present |
