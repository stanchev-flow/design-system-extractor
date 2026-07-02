# Test Brief — "New offering launch" (brand-neutral, shared)

Purpose: a single, brand-neutral brief + copy block used to test the page composer.
The SAME brief is run through every brand's `brand.yaml` so we can compare how each
brand selects, sequences, and expresses the same message in its own taste/vocabulary.

Used by: AD-2 page composer (copy-to-section test) for woodwave + hubspot.

---

## Brief
- goal: Drive sign-ups for a new offering (one landing page).
- audience: Prospective customers evaluating options.
- tone: Confident, clear, benefit-led.
- variations: No — one composed page per brand.

## Copy block (bind into the chosen sections' slots)
- eyebrow: Introducing
- headline: Everything in one place
- subhead: A simpler way to get started — built for how you actually work.
- value_props:
    - title: Set up in minutes
      body: No manual wiring — you're live the same day.
    - title: One source of truth
      body: Everyone sees the same thing, always up to date.
    - title: Scales with you
      body: From your first project to your thousandth.
- social_proof:
    stat: Trusted by 10,000+ teams
    logos: true            # logo wall if the brand has one
    quote: "We replaced three tools in a week and never looked back."
    quote_attr: "Operations lead, mid-market team"
- primary_cta: Start free
- secondary_cta: See how it works

## What the composer must do
1. Read the brand's `brand.yaml` (layouts[] with useCase/whenToUse, do[]/avoid[], tokens).
2. SELECT + ORDER the sections that best sell this copy for THIS brand.
3. BIND the copy above into the chosen sections' typed slots (content/media).
4. Respect the brand's do[]/avoid[]/neverDo rules.
5. Where the brand lacks a section type the copy implies (e.g. no logo-wall or
   feature-grid), map the message onto the brand's nearest vocabulary OR flag the gap
   in the rationale — do NOT invent off-brand sections.
6. Output a page plan: ordered section list + per-section slot bindings + a short
   rationale (why these sections, in this order), then render.

## Expected contrast (hypothesis to validate)
- HubSpot (SaaS, rounded): likely hero-cta -> logo-wall -> feature-card-grid -> testimonial -> cta-band.
- WoodWave (editorial gallery): no logo-wall/feature-grid, so social-proof + value-props
  must map onto editorial-collage / info-band / conversion-stack vocabulary (or flag gaps).
