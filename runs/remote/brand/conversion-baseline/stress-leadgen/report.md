# Conversion-structure check (conversion-structure.v1)

2026-07-14T17:58:29Z — advisory-first wiring; hardFloor rows gate from birth

## runs/remote/brand/compose/stress-playbook — PASS with 4 WARN(s) — campaign `leadgen-gated-content` (explicit, ground: rendered)

sequence: pb-hero[hero] -> pb-stats[stat-band] -> pb-statement[-] -> pb-chapters[feature-grid] -> pb-process[feature-grid] -> pb-compare[-] -> pb-banner[cta-band] -> pb-stories[carousel,quote] -> pb-badges[logo-strip] -> pb-faq[faq] -> pb-form[capture-form,cta-band]

| kind | families | sev | verdict | detail |
|---|---|---|---|---|
| opens | hero | req | ok | opens with hero |
| present | capture-form | req | ok | 1 section(s) bind ['capture-form'] (budget 1-2) |
| window | capture-form | req | WARN | first ['capture-form'] match at index 11 (past the first 3) |
| adjacent | capture-form, logo-strip, quote, stat-band | adv | WARN | nearest ['logo-strip', 'quote', 'stat-band'] beat 2 step(s) from ['capture-form'] (maxGap 1) |
| present | feature-grid | adv | ok | 2 section(s) bind ['feature-grid'] (budget 1-2) |
| present | pricing-tiers | req | ok | 0 section(s) bind ['pricing-tiers'] (budget 0-0) |
| closes | cta-band, capture-form | adv | ok | closes on ['capture-form', 'cta-band'] |
| depthBand | — | adv | WARN | 11 content section(s) (band 4-6, funnel consideration) |
| formDepth | capture-form | adv | WARN | 7 visible field(s) (band 2-4) |
| hardFloor:conversion-moment | — | hard | ok | capture-form present |
