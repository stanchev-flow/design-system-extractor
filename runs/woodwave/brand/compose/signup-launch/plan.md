# Composed page plan - WoodWave Gallery

- **Brief:** `signup-launch.md` - Drive sign-ups for a new offering (one landing page).
- **Sections selected:** 4 of 4 brand layouts
- **Brand page rhythm:** surface/inverse -> surface/primary -> surface/primary -> surface/inverse -> surface/primary -> surface/inverse-strong

## Order, mapping & rationale

| # | intent | brand section | surface | why this section, here |
|---|---|---|---|---|
| 1 | hero | `opening-bookend` (stack) | Inverse | Opens the page: brand wordmark + slash nav, the brief eyebrow + headline as the sanctioned display-title-over-media overlap, subhead + typographic CTAs below the photo collage. Inverse surface (page rhythm bookend). |
| 2 | value_props | `editorial-collage` (collage) | base (Primary) | Sells the 3 value_props as the brand's editorial-collage modules (micro-caption + serif title + offset paragraph + alternating-anchor media over a ghost watermark) - the open-collage answer to a SaaS feature-card grid the brand forbids. Primary surface. |
| 3 | social_proof | `info-band` (split) | Inverse | Carries social proof: the stat + testimonial quote land in the info-band's cream panel (child of the inverse band), with the CTAs as ruled typographic action rows. Maps the brief's logo-wall onto this panel (see gaps). Inverse surface. |
| 4 | conversion | `conversion-stack` (stack) | base (Primary) | Closes with conversion-stack: centered narrow column, eyebrow -> heading -> underline-only field with an inline typographic submit (no boxed input, no button). Restates the headline as a closing bookend. Primary surface. |

## Slot bindings (brief copy -> section slots)

### 1. `opening-bookend` (hero)
- **eyebrow:** Introducing
- **headline:** Everything in one place
- **subhead:** A simpler way to get started — built for how you actually work.
- **primary_cta:** Start free
- **secondary_cta:** See how it works

### 2. `editorial-collage` (value_props)
- **headline:** Everything in one place
- **ghost:** EVERYTHING
- **value_props (3 modules):**
  - *Set up in minutes* - No manual wiring — you're live the same day.
  - *One source of truth* - Everyone sees the same thing, always up to date.
  - *Scales with you* - From your first project to your thousandth.

### 3. `info-band` (social_proof)
- **band_title:** A simpler way to get started — built for how you actually work.
- **primary_cta:** Start free
- **secondary_cta:** See how it works
- **social_proof.stat:** Trusted by 10,000+ teams
- **social_proof.quote:** “We replaced three tools in a week and never looked back.” - Operations lead, mid-market team

### 4. `conversion-stack` (conversion)
- **eyebrow:** Introducing
- **headline:** Everything in one place
- **conv_title:** Everything in one place
- **primary_cta:** Start free
- **secondary_cta:** See how it works
- **field_placeholder:** you@company.com

## Gaps (brief-implied sections the brand lacks)

- **logo-wall:** brief social_proof.logos=true, but the brand has no logo-wall vocabulary (and a boxed logo grid would violate no-cards-on-cream / the zero-chrome editorial system). Mapped onto: `info-band`.
- **feature-card-grid:** the brief's value_props read as a SaaS feature-card grid, but the brand has no card/grid vocabulary (neverDo:no-cards-on-cream). Mapped onto the nearest brand vocabulary instead. Mapped onto: `editorial-collage`.

## On-brand check

- **OVERALL: PASS** (see `onbrand-report.md`).
- **neverDo violations:** PASS - zero violations.
- **Fidelity vs source:** PASS.
- **Slop checklist:** PASS.

> Note: onbrand_check resolves a single layout from the render-dir name and falls back to the brand's first layout (`opening-bookend`) for a multi-section composed page. Its neverDo + slop scans are global over the whole page HTML/CSS, so the zero-violation result holds for the entire composition; fidelity rows are asserted against that representative layout.
