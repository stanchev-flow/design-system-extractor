# Section-rules audit (section-rules.v1)

Brand: `runs/remote/brand` · 57 rules · 2026-07-14T17:58:11Z

## compose/event-genlaunch — PASS (0 required fail(s), 2 advisory warn(s)) — scope: generative

| rule | scope | sev | verdict | detail |
|---|---|---|---|---|
| `SR-HDR-01` | section-header | req | PASS |  6 non-hero section heading(s) within the 2-line budget (half-measure columns license 3) |
| `SR-HDR-02` | section-header | req | PASS |  7 heading(s): 0 duplicates, 0 ellipses, 0 double punctuation |
| `SR-HERO-01` | hero | req | PASS | sec-0 display renders 2 line(s) within the 3-line budget (half-measure columns license 4) |
| `SR-HERO-02` | hero | adv | FAIL | sec-0 5 rendered lines (budget 4) |
| `SR-HERO-04` | hero | adv | PASS | sec-0 1 eyebrow(s) <= 5 words, no terminal period |
| `SR-HERO-05` | hero | adv | PASS | sec-0 1 proof row(s) at or below body (20.6px) |
| `SR-LOGO-01` | logo-strip | req | PASS | sec-1 fact-less strip: max/median height 1.00 (<= 1.5), 24 mark(s) |
| `SR-LOGO-02` | logo-strip | adv | PASS | sec-1 12 distinct mark(s) |
| `SR-LOGO-04` | logo-strip | adv | PASS | sec-1 caption register <= body (18.0px) |
| `SR-FORM-01` | capture-form | adv | PASS | sec-7 7 visible control(s) (max 8), 4 required (max 5) |
| `SR-FORM-04` | capture-form | req | PASS | sec-7 1 filled submit; siblings quiet |
| `SR-FORM-05` | capture-form | adv | PASS | sec-7 consent/privacy line present |
| `SR-FORM-06` | capture-form | adv | PASS | sec-7 5 parallel field label(s) |
| `SR-TIER-01` | pricing-tiers | req | PASS | sec-5 3 card(s) share anatomy {cta, list, name, price, tagline} |
| `SR-TIER-02` | pricing-tiers | adv | FAIL | sec-5 filled-primary CTA on non-emphasized card(s) [1] while card 2 carries the emphasis treatment |
| `SR-TIER-03` | pricing-tiers | req | PASS | sec-5 3 price(s) share one grammar |
| `SR-TIER-04` | pricing-tiers | adv | PASS | sec-5 bullets per card [3, 4, 4] |
| `SR-TIER-05` | pricing-tiers | adv | PASS | sec-5 3 tier(s) |
| `SR-QUOTE-01` | quote | req | PASS | sec-4 1 quote unit(s) marked; register below display |
| `SR-QUOTE-02` | quote | req | PASS | sec-4 1 quote(s) all attributed |
| `SR-QUOTE-04` | quote | adv | PASS | sec-4 1 quote(s) within 10-70 words |
| `SR-GRID-01` | feature-grid | req | PASS | sec-2 6 cell(s) share slot anatomy (bento lead exempt) |
| `SR-GRID-02` | feature-grid | adv | PASS | sec-2 7 parallel cell heading(s) |
| `SR-GRID-03` | feature-grid | adv | PASS | sec-2 7 cell bodies parallel in depth |
| `SR-FAQ-01` | faq | req | PASS | sec-6 6 trigger(s) all question-form |
| `SR-FAQ-02` | faq | adv | PASS | sec-6 6 answer(s) within 15-120 words |
| `SR-FAQ-03` | faq | adv | PASS | sec-6 6 item(s) |
| `SR-FAQ-04` | faq | adv | PASS | sec-6 0/6 answers with links (<= 1/3) |
| `SR-CTA-01` | cta-band | adv | PASS | sec-7 one decision moment (22w support) |
| `SR-CTA-03` | cta-band | adv | PASS | sec-7 primary label 'Save my seat' verb-led, 3 words |
| `SR-NAV-01` | nav | req | PASS |  4 primary-bar label(s) match the harvested roster |
| `SR-NAV-03` | nav | adv | OVERRIDE |  harvested chrome — measured labels are brand evidence (navbar.primary cited) |
| `SR-FOOT-01` | footer | req | PASS |  8 column group(s), 4 social mark(s), legal line — all match the harvested anatomy |
| `SR-FOOT-02` | footer | adv | PASS |  legal register line present |
| `SR-CAR-01` | carousel | adv | PASS | sec-1 24 slide(s) share anatomy |
| `SR-CAR-02` | carousel | adv | PASS | sec-1 24 item(s) |

delegated: SR-CAR-03, SR-CAR-04, SR-CTA-02, SR-FAQ-05, SR-FOOT-03, SR-FORM-02, SR-FORM-03, SR-GRID-05, SR-GRID-06, SR-HDR-03, SR-HERO-03, SR-LOGO-03, SR-NAV-02, SR-QUOTE-03, SR-TIER-06
skips: 6 (SR-GRID-01, SR-GRID-02, SR-GRID-03, SR-GRID-04, stat-band)

## compose/stress-playbook — PASS (0 required fail(s), 4 advisory warn(s)) — scope: generative

| rule | scope | sev | verdict | detail |
|---|---|---|---|---|
| `SR-HDR-01` | section-header | req | PASS |  10 non-hero section heading(s) within the 2-line budget (half-measure columns license 3) |
| `SR-HDR-02` | section-header | req | PASS |  11 heading(s): 0 duplicates, 0 ellipses, 0 double punctuation |
| `SR-HERO-01` | hero | req | PASS | sec-0 display renders 4 line(s) within the 3-line budget (half-measure columns license 4) |
| `SR-HERO-02` | hero | adv | FAIL | sec-0 5 rendered lines (budget 4) |
| `SR-HERO-04` | hero | adv | PASS | sec-0 1 eyebrow(s) <= 5 words, no terminal period |
| `SR-HERO-05` | hero | adv | PASS | sec-0 1 proof row(s) at or below body (20.6px) |
| `SR-STAT-01` | stat-band | req | PASS | sec-1 4 value(s) all carry magnitudes (CUR, INT+, INT-UNIT) |
| `SR-STAT-02` | stat-band | adv | PASS | sec-1 qualifier grammar parallel across 4 value(s) |
| `SR-STAT-03` | stat-band | adv | FAIL | sec-1 4 label(s) outside 1-6 words: 'Countries where the playbook's guida…' (12w); 'Typical time to open a local entity …' (15w); 'How often employment law changes som…' (14w) |
| `SR-STAT-04` | stat-band | adv | PASS | sec-1 4 stat(s), no duplicates |
| `SR-LOGO-01` | logo-strip | req | PASS | sec-8 fact-less strip: max/median height 1.00 (<= 1.5), 6 mark(s) |
| `SR-LOGO-01` | logo-strip | req | PASS | sec-8 fact-less strip: max/median height 1.00 (<= 1.5), 3 mark(s) |
| `SR-LOGO-02` | logo-strip | adv | PASS | sec-8 9 distinct mark(s) |
| `SR-FORM-01` | capture-form | adv | PASS | sec-10 7 visible control(s) (max 8), 3 required (max 5) |
| `SR-FORM-04` | capture-form | req | PASS | sec-10 1 filled submit; siblings quiet |
| `SR-FORM-05` | capture-form | adv | PASS | sec-10 consent/privacy line present |
| `SR-FORM-06` | capture-form | adv | FAIL | sec-10 1 label(s) over 4 words: 'Where are you hiring next?' |
| `SR-QUOTE-01` | quote | req | PASS | sec-7 3 quote unit(s) marked; register below display |
| `SR-QUOTE-02` | quote | req | PASS | sec-7 3 quote(s) all attributed |
| `SR-QUOTE-04` | quote | adv | PASS | sec-7 3 quote(s) within 10-70 words |
| `SR-GRID-01` | feature-grid | req | PASS | sec-3 3 cell(s) share slot anatomy (bento lead exempt) |
| `SR-GRID-02` | feature-grid | adv | FAIL | sec-3 1 heading(s) outside 1-8 words: 'Run multi-country payroll people' |
| `SR-GRID-03` | feature-grid | adv | PASS | sec-3 3 cell bodies parallel in depth |
| `SR-FAQ-01` | faq | req | PASS | sec-9 5 trigger(s) all question-form |
| `SR-FAQ-02` | faq | adv | PASS | sec-9 5 answer(s) within 15-120 words |
| `SR-FAQ-03` | faq | adv | PASS | sec-9 5 item(s) |
| `SR-FAQ-04` | faq | adv | PASS | sec-9 0/5 answers with links (<= 1/3) |
| `SR-CTA-01` | cta-band | adv | PASS | sec-6 one decision moment (0w support) |
| `SR-CTA-01` | cta-band | adv | PASS | sec-10 one decision moment (29w support) |
| `SR-CTA-03` | cta-band | adv | PASS | sec-6 primary label 'Get the playbook' verb-led, 3 words |
| `SR-CTA-03` | cta-band | adv | PASS | sec-10 primary label 'Get the playbook' verb-led, 3 words |
| `SR-NAV-01` | nav | req | PASS |  4 primary-bar label(s) match the harvested roster |
| `SR-NAV-03` | nav | adv | OVERRIDE |  harvested chrome — measured labels are brand evidence (navbar.primary cited) |
| `SR-FOOT-01` | footer | req | PASS |  8 column group(s), 4 social mark(s), legal line — all match the harvested anatomy |
| `SR-FOOT-02` | footer | adv | PASS |  legal register line present |
| `SR-CAR-01` | carousel | adv | PASS | sec-7 3 slide(s) share anatomy |
| `SR-CAR-02` | carousel | adv | PASS | sec-7 3 item(s) |

delegated: SR-CAR-03, SR-CAR-04, SR-CTA-02, SR-FAQ-05, SR-FOOT-03, SR-FORM-02, SR-FORM-03, SR-GRID-05, SR-GRID-06, SR-HDR-03, SR-HERO-03, SR-LOGO-03, SR-NAV-02, SR-QUOTE-03, SR-STAT-05
skips: 7 (SR-GRID-01, SR-GRID-02, SR-GRID-03, SR-GRID-04, SR-LOGO-04, pricing-tiers)

## compose/bakeoff-sol — PASS (0 required fail(s), 3 advisory warn(s)) — scope: generative

| rule | scope | sev | verdict | detail |
|---|---|---|---|---|
| `SR-HDR-01` | section-header | req | PASS |  9 non-hero section heading(s) within the 2-line budget (half-measure columns license 3) |
| `SR-HDR-02` | section-header | req | PASS |  10 heading(s): 0 duplicates, 0 ellipses, 0 double punctuation |
| `SR-HERO-01` | hero | req | PASS | sec-0 display renders 2 line(s) within the 3-line budget (half-measure columns license 4) |
| `SR-HERO-02` | hero | adv | PASS | sec-0 2 sentence(s), 4 line(s) |
| `SR-HERO-04` | hero | adv | PASS | sec-0 1 eyebrow(s) <= 5 words, no terminal period |
| `SR-FORM-01` | capture-form | adv | FAIL | sec-9 8 visible control(s) (max 8), 8 required (max 5) |
| `SR-FORM-04` | capture-form | req | PASS | sec-9 1 filled submit; siblings quiet |
| `SR-FORM-05` | capture-form | adv | PASS | sec-9 consent/privacy line present |
| `SR-FORM-06` | capture-form | adv | FAIL | sec-9 2 label(s) over 4 words: 'Where does your company operat'; 'What workforce question are yo' |
| `SR-QUOTE-01` | quote | req | PASS | sec-6 2 quote unit(s) marked; register below display |
| `SR-QUOTE-02` | quote | req | PASS | sec-6 2 quote(s) all attributed |
| `SR-QUOTE-04` | quote | adv | PASS | sec-6 2 quote(s) within 10-70 words |
| `SR-GRID-01` | feature-grid | req | PASS | sec-1 3 cell(s) share slot anatomy (bento lead exempt) |
| `SR-GRID-01` | feature-grid | req | PASS | sec-3 4 cell(s) share slot anatomy (bento lead exempt) |
| `SR-GRID-01` | feature-grid | req | PASS | sec-4 3 cell(s) share slot anatomy (bento lead exempt) |
| `SR-GRID-02` | feature-grid | adv | PASS | sec-1 3 parallel cell heading(s) |
| `SR-GRID-02` | feature-grid | adv | PASS | sec-3 4 parallel cell heading(s) |
| `SR-GRID-02` | feature-grid | adv | PASS | sec-4 3 parallel cell heading(s) |
| `SR-GRID-03` | feature-grid | adv | PASS | sec-1 3 cell bodies parallel in depth |
| `SR-GRID-03` | feature-grid | adv | PASS | sec-3 4 cell bodies parallel in depth |
| `SR-GRID-03` | feature-grid | adv | PASS | sec-4 3 cell bodies parallel in depth |
| `SR-FAQ-01` | faq | req | PASS | sec-8 5 trigger(s) all question-form |
| `SR-FAQ-02` | faq | adv | PASS | sec-8 5 answer(s) within 15-120 words |
| `SR-FAQ-03` | faq | adv | PASS | sec-8 5 item(s) |
| `SR-FAQ-04` | faq | adv | PASS | sec-8 0/5 answers with links (<= 1/3) |
| `SR-CTA-01` | cta-band | adv | PASS | sec-9 one decision moment (20w support) |
| `SR-CTA-03` | cta-band | adv | PASS | sec-9 primary label 'Request a demo' verb-led, 3 words |
| `SR-NAV-01` | nav | req | PASS |  4 primary-bar label(s) match the harvested roster |
| `SR-NAV-03` | nav | adv | OVERRIDE |  harvested chrome — measured labels are brand evidence (navbar.primary cited) |
| `SR-FOOT-01` | footer | req | PASS |  8 column group(s), 4 social mark(s), legal line — all match the harvested anatomy |
| `SR-FOOT-02` | footer | adv | PASS |  legal register line present |
| `SR-CAR-01` | carousel | adv | PASS | sec-6 2 slide(s) share anatomy |
| `SR-CAR-02` | carousel | adv | FAIL | sec-6 2 item(s) — a 2-frame carousel is a split wearing controls |

delegated: SR-CAR-03, SR-CAR-04, SR-CTA-02, SR-FAQ-05, SR-FOOT-03, SR-FORM-02, SR-FORM-03, SR-GRID-05, SR-GRID-06, SR-HDR-03, SR-HERO-03, SR-NAV-02, SR-QUOTE-03
skips: 19 (SR-GRID-01, SR-GRID-02, SR-GRID-03, SR-GRID-04, SR-HERO-05, logo-strip, pricing-tiers, stat-band)

## compose/bakeoff-opus — PASS (0 required fail(s), 2 advisory warn(s)) — scope: generative

| rule | scope | sev | verdict | detail |
|---|---|---|---|---|
| `SR-HDR-01` | section-header | req | PASS |  9 non-hero section heading(s) within the 2-line budget (half-measure columns license 3) |
| `SR-HDR-02` | section-header | req | PASS |  10 heading(s): 0 duplicates, 0 ellipses, 0 double punctuation |
| `SR-HERO-01` | hero | req | PASS | sec-0 display renders 2 line(s) within the 3-line budget (half-measure columns license 4) |
| `SR-HERO-02` | hero | adv | FAIL | sec-0 5 rendered lines (budget 4) |
| `SR-HERO-04` | hero | adv | PASS | sec-0 1 eyebrow(s) <= 5 words, no terminal period |
| `SR-FORM-01` | capture-form | adv | PASS | sec-9 6 visible control(s) (max 8), 4 required (max 5) |
| `SR-FORM-04` | capture-form | req | PASS | sec-9 1 filled submit; siblings quiet |
| `SR-FORM-05` | capture-form | adv | PASS | sec-9 consent/privacy line present |
| `SR-FORM-06` | capture-form | adv | FAIL | sec-9 1 label(s) over 4 words: 'What would you like to see?' |
| `SR-QUOTE-01` | quote | req | PASS | sec-6 3 quote unit(s) marked; register below display |
| `SR-QUOTE-02` | quote | req | PASS | sec-6 3 quote(s) all attributed |
| `SR-QUOTE-04` | quote | adv | PASS | sec-6 3 quote(s) within 10-70 words |
| `SR-GRID-01` | feature-grid | req | PASS | sec-3 3 cell(s) share slot anatomy (bento lead exempt) |
| `SR-GRID-01` | feature-grid | req | PASS | sec-4 3 cell(s) share slot anatomy (bento lead exempt) |
| `SR-GRID-02` | feature-grid | adv | PASS | sec-3 3 parallel cell heading(s) |
| `SR-GRID-02` | feature-grid | adv | PASS | sec-4 3 parallel cell heading(s) |
| `SR-GRID-03` | feature-grid | adv | PASS | sec-3 3 cell bodies parallel in depth |
| `SR-GRID-03` | feature-grid | adv | PASS | sec-4 3 cell bodies parallel in depth |
| `SR-FAQ-01` | faq | req | PASS | sec-8 5 trigger(s) all question-form |
| `SR-FAQ-02` | faq | adv | PASS | sec-8 5 answer(s) within 15-120 words |
| `SR-FAQ-03` | faq | adv | PASS | sec-8 5 item(s) |
| `SR-FAQ-04` | faq | adv | PASS | sec-8 0/5 answers with links (<= 1/3) |
| `SR-CTA-01` | cta-band | adv | PASS | sec-7 one decision moment (0w support) |
| `SR-CTA-01` | cta-band | adv | PASS | sec-9 one decision moment (20w support) |
| `SR-CTA-03` | cta-band | adv | PASS | sec-7 primary label 'Book a demo' verb-led, 3 words |
| `SR-CTA-03` | cta-band | adv | PASS | sec-9 primary label 'Book my demo' verb-led, 3 words |
| `SR-NAV-01` | nav | req | PASS |  4 primary-bar label(s) match the harvested roster |
| `SR-NAV-03` | nav | adv | OVERRIDE |  harvested chrome — measured labels are brand evidence (navbar.primary cited) |
| `SR-FOOT-01` | footer | req | PASS |  8 column group(s), 4 social mark(s), legal line — all match the harvested anatomy |
| `SR-FOOT-02` | footer | adv | PASS |  legal register line present |
| `SR-CAR-01` | carousel | adv | PASS | sec-6 3 slide(s) share anatomy |
| `SR-CAR-02` | carousel | adv | PASS | sec-6 3 item(s) |

delegated: SR-CAR-03, SR-CAR-04, SR-CTA-02, SR-FAQ-05, SR-FOOT-03, SR-FORM-02, SR-FORM-03, SR-GRID-05, SR-GRID-06, SR-HDR-03, SR-HERO-03, SR-NAV-02, SR-QUOTE-03
skips: 18 (SR-GRID-01, SR-GRID-02, SR-GRID-03, SR-GRID-04, SR-HERO-05, logo-strip, pricing-tiers, stat-band)

## compose/replica — PASS (0 required fail(s), 0 advisory warn(s)) — scope: replica

skips: 1 (*)
