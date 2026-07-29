# Section-rules audit (section-rules.v1)

Brand: `runs/hubspot-v3/brand` · 57 rules · 2026-07-28T23:54:06Z

## compose/ai-product-launch — PASS (0 required fail(s), 0 advisory warn(s)) — scope: generative

| rule | scope | sev | verdict | detail |
|---|---|---|---|---|
| `SR-HDR-01` | section-header | req | PASS |  6 non-hero section heading(s) within the 2-line budget (half-measure columns license 3) |
| `SR-HDR-02` | section-header | req | PASS |  7 heading(s): 0 duplicates, 0 ellipses, 0 double punctuation |
| `SR-HERO-01` | hero | req | PASS | sec-0 display renders 3 line(s) within the 3-line budget (half-measure columns license 4) |
| `SR-HERO-02` | hero | adv | PASS | sec-0 1 sentence(s), 3 line(s) |
| `SR-HERO-04` | hero | adv | PASS | sec-0 1 eyebrow(s) <= 5 words, no terminal period |
| `SR-STAT-01` | stat-band | req | PASS | sec-5 3 value(s) all carry magnitudes (PCT) |
| `SR-STAT-02` | stat-band | adv | PASS | sec-5 qualifier grammar parallel across 3 value(s) |
| `SR-STAT-03` | stat-band | adv | PASS | sec-5 3 parallel label(s) |
| `SR-STAT-04` | stat-band | adv | PASS | sec-5 3 stat(s), no duplicates |
| `SR-LOGO-01` | logo-strip | req | PASS | sec-1 declared itembox: mark heights within 0.0px |
| `SR-LOGO-01` | logo-strip | req | PASS | sec-4 fact-less strip: max/median height 1.00 (<= 1.5), 6 mark(s) |
| `SR-LOGO-02` | logo-strip | adv | PASS | sec-1 5 distinct mark(s) |
| `SR-LOGO-02` | logo-strip | adv | PASS | sec-4 6 distinct mark(s) |
| `SR-QUOTE-01` | quote | req | PASS | sec-6 3 quote unit(s) marked; register below display |
| `SR-QUOTE-02` | quote | req | PASS | sec-6 3 quote(s) all attributed |
| `SR-QUOTE-04` | quote | adv | PASS | sec-6 3 quote(s) within 10-70 words |
| `SR-GRID-01` | feature-grid | req | PASS | sec-3 3 cell(s) share slot anatomy (bento lead exempt) |
| `SR-GRID-03` | feature-grid | adv | PASS | sec-3 3 cell bodies parallel in depth |
| `SR-CTA-01` | cta-band | adv | PASS | sec-7 one decision moment (0w support) |
| `SR-CTA-03` | cta-band | adv | PASS | sec-7 primary label 'Get a demo' verb-led, 3 words |
| `SR-NAV-01` | nav | req | PASS |  4 primary-bar label(s) match the harvested roster |
| `SR-NAV-03` | nav | adv | OVERRIDE |  harvested chrome — measured labels are brand evidence (navbar.primary cited) |
| `SR-FOOT-01` | footer | req | PASS |  6 column group(s), 7 social mark(s), legal line — all match the harvested anatomy |
| `SR-FOOT-02` | footer | adv | PASS |  legal register line present |
| `SR-CAR-01` | carousel | adv | PASS | sec-3 3 slide(s) share anatomy |
| `SR-CAR-02` | carousel | adv | PASS | sec-3 3 item(s) |

delegated: SR-CAR-03, SR-CAR-04, SR-CTA-02, SR-FOOT-03, SR-GRID-05, SR-GRID-06, SR-HDR-03, SR-HERO-03, SR-LOGO-03, SR-NAV-02, SR-QUOTE-03, SR-STAT-05
skips: 12 (SR-GRID-01, SR-GRID-02, SR-GRID-03, SR-GRID-04, SR-HERO-05, SR-LOGO-04, capture-form, faq, pricing-tiers)
