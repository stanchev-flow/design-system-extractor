# Section-rules audit (section-rules.v1)

Brand: `/Users/stanchev/Webflow/campaigns-hackathon/design-system-extractor-mine/runs/hubspot-v2/brand` · 57 rules · 2026-07-18T23:44:02Z

## /Users/stanchev/Webflow/campaigns-hackathon/design-system-extractor-mine/experiments/ui-skills-relume-ab/lane-b — PASS (0 required fail(s), 0 advisory warn(s)) — scope: generative

| rule | scope | sev | verdict | detail |
|---|---|---|---|---|
| `SR-HDR-01` | section-header | req | PASS |  4 non-hero section heading(s) within the 2-line budget (half-measure columns license 3) |
| `SR-HDR-02` | section-header | req | PASS |  6 heading(s): 0 duplicates, 0 ellipses, 0 double punctuation |
| `SR-HERO-01` | hero | req | PASS | sec-0 display renders 3 line(s) within the 3-line budget (half-measure columns license 4) |
| `SR-HERO-02` | hero | adv | PASS | sec-0 1 sentence(s), 2 line(s) |
| `SR-HERO-04` | hero | adv | PASS | sec-0 2 eyebrow(s) <= 5 words, no terminal period |
| `SR-STAT-01` | stat-band | req | PASS | sec-2 2 value(s) all carry magnitudes (INT+, PCT) |
| `SR-STAT-02` | stat-band | adv | PASS | sec-2 qualifier grammar parallel across 2 value(s) |
| `SR-STAT-03` | stat-band | adv | PASS | sec-2 2 parallel label(s) |
| `SR-STAT-04` | stat-band | adv | PASS | sec-2 2 stat(s), no duplicates |
| `SR-GRID-01` | feature-grid | req | PASS | sec-1 3 cell(s) share slot anatomy (bento lead exempt) |
| `SR-GRID-01` | feature-grid | req | PASS | sec-4 3 cell(s) share slot anatomy (bento lead exempt) |
| `SR-GRID-03` | feature-grid | adv | PASS | sec-1 3 cell bodies parallel in depth |
| `SR-GRID-03` | feature-grid | adv | PASS | sec-4 3 cell bodies parallel in depth |
| `SR-GRID-04` | feature-grid | adv | PASS | sec-4 3 icon box(es) uniform (median 16px ±10%) |
| `SR-CTA-01` | cta-band | adv | PASS | sec-5 one decision moment (0w support) |
| `SR-CTA-03` | cta-band | adv | PASS | sec-5 primary label 'Get a demo' verb-led, 3 words |
| `SR-NAV-01` | nav | req | PASS |  4 primary-bar label(s) match the harvested roster |
| `SR-NAV-03` | nav | adv | OVERRIDE |  harvested chrome — measured labels are brand evidence (navbar.primary cited) |
| `SR-FOOT-01` | footer | req | PASS |  6 column group(s), 7 social mark(s), legal line — all match the harvested anatomy |
| `SR-FOOT-02` | footer | adv | PASS |  legal register line present |

delegated: SR-CTA-02, SR-FOOT-03, SR-GRID-05, SR-GRID-06, SR-HDR-03, SR-HERO-03, SR-NAV-02, SR-QUOTE-03, SR-STAT-05, SR-TIER-06
skips: 20 (SR-GRID-01, SR-GRID-02, SR-GRID-03, SR-GRID-04, SR-HERO-05, SR-QUOTE-01, SR-QUOTE-02, SR-QUOTE-04, SR-TIER-01, SR-TIER-02, SR-TIER-03, SR-TIER-04)
