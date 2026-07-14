# PLAN — "The Global Hiring Playbook" stress-test page (`stress-playbook`)

**Concept.** A content-rich resource landing page: Remote publishes *The Global Hiring
Playbook* — a free, chaptered field guide to hiring in new countries (employ, contract,
pay, stay compliant), distilled from the employment infrastructure Remote owns in 170+
countries. The page's narrative arc: hook → problem (the cost of getting global hiring
wrong) → thesis statement → what's inside (chapters) → how teams use it (process) →
build-vs-buy comparison → conversion beat → proof (customers, third-party validation) →
objections (FAQ) → destination (get-the-playbook form). One action end to end: get the
playbook. All surfaces stay on the brand's continuous light canvas (no dark full bands),
copy follows `voice.md` (sentence case, operational verbs, numbers do the persuading).

**Stress intent.** `event-genlaunch` already exercised: centered art-panel poster hero,
static/marquee logo strip, bento mosaic (+accent cell), FAQ-composer disclosure (accent
active + warm-wash idle), single bento quote cell, pricing tiers (inverse head band),
multi-field signup form on the closing noise band. This page deliberately exercises
**eleven sections, each on a catalog device NOT shown there** (marquee/bento/tiers are
avoided entirely). Known-gap probes are chosen so the page still renders well and the gap
is logged in REPORT.md: no `stat` renderer (big-number register), no comparison-`table`
device, `textarea` form kind coerced to text.

## Section list (order = page order)

| # | id | device exercised (why it's new) |
|---|----|--------------------------------|
| 1 | `pb-hero` | **Split art-panel hero with media counterweight + poster meta/eyebrow slots** — event used the centered solo poster; homepage split uses the globe. This is the split panel variant w/ a product-UI collage counterweight + meta caption line (AS-37 split→panel route). |
| 2 | `pb-stats` | **Stats band through generic-flow module fold** — probes the missing `stat` big-number renderer (numbers land in the caption register). |
| 3 | `pb-statement` | **Editorial interlock** (`interlock` archetype: statement + caption stack + media + support/cta foot cluster) — never exercised on Remote. |
| 4 | `pb-chapters` | **`features-card-grid-navy-media` seeded card grid** — the brand's workflow-card grammar: white cards, navy media wells, card eyebrows, gridEqualize + curated centered header. Event used bento, not this grid. |
| 5 | `pb-process` | **`feature-accordion-deep-accent` seeded split accordion** — deep-accent active inversion + circle-arrow affordance + per-row media swap (fid5 `rowMedia`) + row icons. Event's disclosures ran through the FAQ composer, not this split device. |
| 6 | `pb-compare` | **Split info-band (default split route)** — ruled label/value rows in a panel beside media; probes the missing comparison-`table` contract renderer. |
| 7 | `pb-banner` | **`cta-inline-banner` seeded conversion beat** — rounded inset panel w/ soft glow, question heading, ONE filled pill (`_insetPanel` device). |
| 8 | `pb-stories` | **`testimonial-card-row` seeded edge-cut carousel** — 3-up quote cards w/ company marks + circle avatars + person rows, edge-cut presentation, closing outlined pill. |
| 9 | `pb-badges` | **`badge-award-strip` seeded multi-group strip** — badge shields row + rating chips row as separate measured strip groups + outlined pill (generic-flow group strips). |
| 10 | `pb-faq` | **FAQ accordion, navy-inverse variant** — `knobs.faq.activeSurface: surface/inverse` (the deep-navy well surface as active card; accent stays spent on §5), non-exclusive disclosure (`exclusive: false`) — both knob values unexercised. |
| 11 | `pb-form` | **Compact resource form on the closing noise band** — exercises `tel` field kind (never used) + a deliberate `textarea` kind (coerces to text — logged gap), half/full grid, consent + success microcopy. |

## Process

1. PLAN.md + changes.md (this step — done before any generation).
2. copy-brief.md — hand-authored, on-voice (no LLM call; allowed by the brief).
3. composition.json — hand-authored against `replica-composition.v1` (event-genlaunch schema).
4. Render: `./venv/bin/python brand_pipeline/compose_from_composition.py <comp> runs/remote/brand/brand.yaml -o <lane> --brand-dir runs/remote/brand`.
5. Gates: `onbrand_check.py --composition` + `slop_audit.mjs`; fix composition-level violations, re-render.
6. Screenshots (Playwright, 1440px): full page + 3–4 section closeups into `shots/`.
7. REPORT.md: per-section pattern results, gate output, design-system weaknesses (primary deliverable).
