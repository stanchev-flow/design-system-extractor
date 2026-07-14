# Section-rules audit (section-rules.v1)

Brand: `runs/hubspot-v2/brand` · 57 rules · 2026-07-14T17:58:04Z

## compose/hero-archetypes/homepage — PASS (0 required fail(s), 0 advisory warn(s)) — scope: generative

| rule | scope | sev | verdict | detail |
|---|---|---|---|---|
| `SR-HDR-02` | section-header | req | PASS |  1 heading(s): 0 duplicates, 0 ellipses, 0 double punctuation |
| `SR-HERO-02` | hero | adv | PASS | sec-0 2 sentence(s), 4 line(s) |
| `SR-HERO-04` | hero | adv | PASS | sec-0 1 eyebrow(s) <= 5 words, no terminal period |
| `SR-NAV-01` | nav | req | PASS |  4 primary-bar label(s) match the harvested roster |
| `SR-NAV-03` | nav | adv | OVERRIDE |  harvested chrome — measured labels are brand evidence (navbar.primary cited) |
| `SR-FOOT-01` | footer | req | PASS |  6 column group(s), 7 social mark(s), legal line — all match the harvested anatomy |
| `SR-FOOT-02` | footer | adv | PASS |  legal register line present |

delegated: SR-FOOT-03, SR-HDR-03, SR-HERO-03, SR-NAV-02
skips: 12 (SR-HDR-01, SR-HERO-01, SR-HERO-05, capture-form, carousel, cta-band, faq, feature-grid, logo-strip, pricing-tiers, quote, stat-band)

## compose/hero-archetypes/pricing — PASS (0 required fail(s), 0 advisory warn(s)) — scope: generative

| rule | scope | sev | verdict | detail |
|---|---|---|---|---|
| `SR-HDR-02` | section-header | req | PASS |  1 heading(s): 0 duplicates, 0 ellipses, 0 double punctuation |
| `SR-HERO-01` | hero | req | PASS | sec-0 display renders 2 line(s) within the 3-line budget (half-measure columns license 4) |
| `SR-HERO-02` | hero | adv | PASS | sec-0 2 sentence(s), 2 line(s) |
| `SR-HERO-04` | hero | adv | PASS | sec-0 1 eyebrow(s) <= 5 words, no terminal period |
| `SR-NAV-01` | nav | req | PASS |  4 primary-bar label(s) match the harvested roster |
| `SR-NAV-03` | nav | adv | OVERRIDE |  harvested chrome — measured labels are brand evidence (navbar.primary cited) |
| `SR-FOOT-01` | footer | req | PASS |  6 column group(s), 7 social mark(s), legal line — all match the harvested anatomy |
| `SR-FOOT-02` | footer | adv | PASS |  legal register line present |

delegated: SR-FOOT-03, SR-HDR-03, SR-HERO-03, SR-NAV-02
skips: 11 (SR-HDR-01, SR-HERO-05, capture-form, carousel, cta-band, faq, feature-grid, logo-strip, pricing-tiers, quote, stat-band)

## compose/hero-archetypes/product — PASS (0 required fail(s), 0 advisory warn(s)) — scope: generative

| rule | scope | sev | verdict | detail |
|---|---|---|---|---|
| `SR-HDR-02` | section-header | req | PASS |  1 heading(s): 0 duplicates, 0 ellipses, 0 double punctuation |
| `SR-HERO-01` | hero | req | PASS | sec-0 display renders 2 line(s) within the 3-line budget (half-measure columns license 4) |
| `SR-HERO-02` | hero | adv | PASS | sec-0 1 sentence(s), 3 line(s) |
| `SR-HERO-04` | hero | adv | PASS | sec-0 1 eyebrow(s) <= 5 words, no terminal period |
| `SR-NAV-01` | nav | req | PASS |  4 primary-bar label(s) match the harvested roster |
| `SR-NAV-03` | nav | adv | OVERRIDE |  harvested chrome — measured labels are brand evidence (navbar.primary cited) |
| `SR-FOOT-01` | footer | req | PASS |  6 column group(s), 7 social mark(s), legal line — all match the harvested anatomy |
| `SR-FOOT-02` | footer | adv | PASS |  legal register line present |

delegated: SR-FOOT-03, SR-HDR-03, SR-HERO-03, SR-NAV-02
skips: 11 (SR-HDR-01, SR-HERO-05, capture-form, carousel, cta-band, faq, feature-grid, logo-strip, pricing-tiers, quote, stat-band)

## compose/hero-archetypes/about — PASS (0 required fail(s), 0 advisory warn(s)) — scope: generative

| rule | scope | sev | verdict | detail |
|---|---|---|---|---|
| `SR-HDR-02` | section-header | req | PASS |  1 heading(s): 0 duplicates, 0 ellipses, 0 double punctuation |
| `SR-HERO-01` | hero | req | PASS | sec-0 display renders 3 line(s) within the 3-line budget (half-measure columns license 4) |
| `SR-HERO-02` | hero | adv | PASS | sec-0 1 sentence(s), 2 line(s) |
| `SR-HERO-04` | hero | adv | PASS | sec-0 1 eyebrow(s) <= 5 words, no terminal period |
| `SR-NAV-01` | nav | req | PASS |  4 primary-bar label(s) match the harvested roster |
| `SR-NAV-03` | nav | adv | OVERRIDE |  harvested chrome — measured labels are brand evidence (navbar.primary cited) |
| `SR-FOOT-01` | footer | req | PASS |  6 column group(s), 7 social mark(s), legal line — all match the harvested anatomy |
| `SR-FOOT-02` | footer | adv | PASS |  legal register line present |

delegated: SR-FOOT-03, SR-HDR-03, SR-HERO-03, SR-NAV-02
skips: 11 (SR-HDR-01, SR-HERO-05, capture-form, carousel, cta-band, faq, feature-grid, logo-strip, pricing-tiers, quote, stat-band)

## compose/hero-archetypes/blog — PASS (0 required fail(s), 0 advisory warn(s)) — scope: generative

| rule | scope | sev | verdict | detail |
|---|---|---|---|---|
| `SR-HDR-02` | section-header | req | PASS |  1 heading(s): 0 duplicates, 0 ellipses, 0 double punctuation |
| `SR-HERO-02` | hero | adv | PASS | sec-0 1 sentence(s), 3 line(s) |
| `SR-HERO-04` | hero | adv | PASS | sec-0 1 eyebrow(s) <= 5 words, no terminal period |
| `SR-NAV-01` | nav | req | PASS |  4 primary-bar label(s) match the harvested roster |
| `SR-NAV-03` | nav | adv | OVERRIDE |  harvested chrome — measured labels are brand evidence (navbar.primary cited) |
| `SR-FOOT-01` | footer | req | PASS |  6 column group(s), 7 social mark(s), legal line — all match the harvested anatomy |
| `SR-FOOT-02` | footer | adv | PASS |  legal register line present |

delegated: SR-FOOT-03, SR-HDR-03, SR-HERO-03, SR-NAV-02
skips: 12 (SR-HDR-01, SR-HERO-01, SR-HERO-05, capture-form, carousel, cta-band, faq, feature-grid, logo-strip, pricing-tiers, quote, stat-band)

## compose/hero-archetypes/demo — PASS (0 required fail(s), 0 advisory warn(s)) — scope: generative

| rule | scope | sev | verdict | detail |
|---|---|---|---|---|
| `SR-HDR-02` | section-header | req | PASS |  2 heading(s): 0 duplicates, 0 ellipses, 0 double punctuation |
| `SR-HERO-01` | hero | req | PASS | sec-0 display renders 4 line(s) within the 3-line budget (half-measure columns license 4) |
| `SR-HERO-02` | hero | adv | PASS | sec-0 1 sentence(s), 1 line(s) |
| `SR-HERO-04` | hero | adv | PASS | sec-0 1 eyebrow(s) <= 5 words, no terminal period |
| `SR-FORM-01` | capture-form | adv | PASS | sec-0 3 visible control(s) (max 8), 0 required (max 5) |
| `SR-FORM-04` | capture-form | req | PASS | sec-0 1 filled submit; siblings quiet |
| `SR-FORM-05` | capture-form | adv | PASS | sec-0 consent/privacy line present |
| `SR-FORM-06` | capture-form | adv | PASS | sec-0 3 parallel field label(s) |
| `SR-NAV-01` | nav | req | PASS |  4 primary-bar label(s) match the harvested roster |
| `SR-NAV-03` | nav | adv | OVERRIDE |  harvested chrome — measured labels are brand evidence (navbar.primary cited) |
| `SR-FOOT-01` | footer | req | PASS |  6 column group(s), 7 social mark(s), legal line — all match the harvested anatomy |
| `SR-FOOT-02` | footer | adv | PASS |  legal register line present |

delegated: SR-FOOT-03, SR-FORM-02, SR-FORM-03, SR-HDR-03, SR-HERO-03, SR-NAV-02
skips: 10 (SR-HDR-01, SR-HERO-05, carousel, cta-band, faq, feature-grid, logo-strip, pricing-tiers, quote, stat-band)

## compose/hero-archetypes/developer — PASS (0 required fail(s), 0 advisory warn(s)) — scope: generative

| rule | scope | sev | verdict | detail |
|---|---|---|---|---|
| `SR-HDR-02` | section-header | req | PASS |  1 heading(s): 0 duplicates, 0 ellipses, 0 double punctuation |
| `SR-HERO-01` | hero | req | PASS | sec-0 display renders 2 line(s) within the 3-line budget (half-measure columns license 4) |
| `SR-HERO-02` | hero | adv | PASS | sec-0 1 sentence(s), 2 line(s) |
| `SR-NAV-01` | nav | req | PASS |  4 primary-bar label(s) match the harvested roster |
| `SR-NAV-03` | nav | adv | OVERRIDE |  harvested chrome — measured labels are brand evidence (navbar.primary cited) |
| `SR-FOOT-01` | footer | req | PASS |  6 column group(s), 7 social mark(s), legal line — all match the harvested anatomy |
| `SR-FOOT-02` | footer | adv | PASS |  legal register line present |

delegated: SR-FOOT-03, SR-HDR-03, SR-HERO-03, SR-NAV-02
skips: 12 (SR-HDR-01, SR-HERO-04, SR-HERO-05, capture-form, carousel, cta-band, faq, feature-grid, logo-strip, pricing-tiers, quote, stat-band)

## compose/hero-archetypes/event — PASS (0 required fail(s), 0 advisory warn(s)) — scope: generative

| rule | scope | sev | verdict | detail |
|---|---|---|---|---|
| `SR-HDR-02` | section-header | req | PASS |  1 heading(s): 0 duplicates, 0 ellipses, 0 double punctuation |
| `SR-HERO-01` | hero | req | PASS | sec-0 display renders 1 line(s) within the 3-line budget (half-measure columns license 4) |
| `SR-HERO-02` | hero | adv | PASS | sec-0 1 sentence(s), 2 line(s) |
| `SR-LOGO-01` | logo-strip | req | PASS | sec-0 fact-less strip: max/median height 1.00 (<= 1.5), 6 mark(s) |
| `SR-LOGO-02` | logo-strip | adv | PASS | sec-0 6 distinct mark(s) |
| `SR-LOGO-04` | logo-strip | adv | PASS | sec-0 caption register <= body (18.3px) |
| `SR-NAV-01` | nav | req | PASS |  4 primary-bar label(s) match the harvested roster |
| `SR-NAV-03` | nav | adv | OVERRIDE |  harvested chrome — measured labels are brand evidence (navbar.primary cited) |
| `SR-FOOT-01` | footer | req | PASS |  6 column group(s), 7 social mark(s), legal line — all match the harvested anatomy |
| `SR-FOOT-02` | footer | adv | PASS |  legal register line present |

delegated: SR-FOOT-03, SR-HDR-03, SR-HERO-03, SR-LOGO-03, SR-NAV-02
skips: 11 (SR-HDR-01, SR-HERO-04, SR-HERO-05, capture-form, carousel, cta-band, faq, feature-grid, pricing-tiers, quote, stat-band)

## compose/replica — PASS (0 required fail(s), 0 advisory warn(s)) — scope: replica

skips: 1 (*)
