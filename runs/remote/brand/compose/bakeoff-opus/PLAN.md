# PLAN — Remote Workforce Intelligence launch page (candidate B)

## Concept

**Workforce Intelligence** is positioned as the analytics / insight layer that sits on
top of the employment infrastructure Remote already runs. The wedge is honest and
brand-true: because Remote owns payroll, EOR, contractor, and compliance operations
in-house ("one system of record", per the brand voice + section-copy), the employment
data already lives in one place — so Workforce Intelligence turns it into a single,
current, decision-ready view of **global headcount, total workforce cost, and compliance
risk**, plus benchmarking/planning tools for People and Finance leaders.

This deliberately does NOT reuse the homepage's "hire and pay anyone" narrative — it is a
data/insight product story, so the page reads natively Remote without copying the home
page.

Audience: VP People, CFO, HR Operations at international companies (500+ employees).
Goal: qualified demo requests → the page opens with a demo CTA and closes on a tailored
demo lead form.

## Credibility discipline (per brief: do not invent claims/stats)

- No invented metrics, adoption numbers, or ROI figures anywhere in body copy.
- The only quantified proof is the customer testimonials, which are reused **verbatim**
  from the canonical `section-copy.yaml` (real captured Remote customers). They speak to
  Remote generally (cost, payroll visibility) — I do not reattribute them to this product.
- Security claims (SOC 2 Type 2, ISO 27001) are the ones already asserted in
  `section-copy.yaml` for the owned infrastructure — reused, not invented.
- Award badges / rating chips are intentionally NOT used, to avoid implying third-party
  ratings for a brand-new product.

## Section → pattern → archetype → composer mapping (10 sections)

| # | Section (brief need) | Project pattern (`seededFrom`) | composition archetype | renderer path |
|---|---|---|---|---|
| 1 | Hero (problem hook + product) | `hero-inset-noise-panel` | `split` (art-panel → hero) | `compose_stack_hero` (panel variant) |
| 2 | The problem | `infra-proof-split` | `split` | `compose_info_band` (media \| copy) |
| 3 | Product value | `feature-accordion-deep-accent` | `split` | `compose_info_band` → `_compose_accordion_split` |
| 4 | Key capabilities | `features-card-grid-navy-media` | `cards` | `compose_cards` (navy media wells) |
| 5 | How it works (3 steps) | `features-card-grid-navy-media` (adapt, no media) | `cards` | `compose_cards` (module grid) |
| 6 | Comparison (old way vs product) | `infra-proof-split` (adapt → ruled rows) | `split`, useCase `comparison` | `compose_info_band` (ruled comparison rows) |
| 7 | Customer proof | `testimonial-card-row` | `cards` | `compose_cards` (quote cards + avatars) |
| 8 | Conversion beat | `cta-inline-banner` | `stack`, useCase `cta` | `compose_conversion_stack` (inset panel) |
| 9 | FAQ | (declared `faq`) | `stack`, useCase `faq` | `compose_faq_accordion` |
| 10 | Lead form | (declared `contact` + multi-field form) | `stack`, useCase `contact` | `compose_conversion_stack` → `_compose_signup_form` |

Surface intent is `primary` throughout — the brand is one continuous light canvas
(voice.md: "One continuous light canvas end-to-end; sections separated by breathing
room, never by surface cuts"). The single accent bookend is the hero noise panel; the
one inverted deep-accent emphasis is the accordion's active row (pattern-native).

## Assets (real brand files only)

- Hero art panel: `bg-noise-top-2x.webp`; hero illustration: `hero-globe-illustration.webp`.
- Problem + product-value media well: `panel-infrastructure-ui-snippet.webp` (generic product UI).
- Capability card wells: `card-api-first.webp`, `card-integrations.webp`, `card-mcp-agents.webp`
  (reused as generic Remote product-UI art, not for their homepage labels).
- Testimonials: company marks `logo-fountain.svg`, `logo-reversetech.svg`, `logo-homeproject.svg`;
  avatars `avatar-luke-mckinlay.webp`, `avatar-marisol-jimenez.webp`, `avatar-maria-shkaruppa.webp`.

Hallucinated/mismatched srcs are dropped by the renderer's sanitizer; only real files above are declared.

## Render command

```
venv/bin/python brand_pipeline/render_composition.py \
  runs/remote/brand/compose/bakeoff-opus/composition.json \
  runs/remote/brand/brand.yaml \
  -o runs/remote/brand/compose/bakeoff-opus
```

## Gates

- `brand_pipeline/onbrand_check.py` scoped to the lane index.html.
- `node brand_pipeline/slop_audit.mjs <index.html>` (section completeness).
- Screenshot capture at 1440px full page + per-section closeups; visual inspection pass.
