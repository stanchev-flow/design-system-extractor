# Test Brief — "Pricing & get started" (brand-neutral, shared)

Purpose: pricing/get-started page converting evaluators into free-tier signups.
Run through any brand's `brand.yaml`; the brand supplies the vocabulary.

---

## Brief
- goal: Convert evaluators to free-tier signups; make paid tiers legible without pressure.
- audience: Buyers late in evaluation; they've seen the product, now they're pricing it.
- tone: Plain, transparent, zero tricks — clarity IS the persuasion.
- variations: No — one composed page per brand.

## Copy block (bind into the chosen sections' slots)
- eyebrow: Pricing
- headline: Start free. Upgrade when it pays for itself.
- subhead: Every core feature is free for small teams — no card, no clock. Paid tiers add scale, controls, and support.
- value_props:
    - title: Free
      body: Full core product for up to 5 seats. Free forever.
    - title: Growth
      body: Unlimited seats, automation, and reporting. Per-seat, monthly.
    - title: Enterprise
      body: SSO, audit logs, dedicated support, custom terms.
- social_proof:
    stat: 78% of paying teams started on the free tier
    logos: true
    quote: "We outgrew the free plan in six months — best sales pitch is no pitch."
    quote_attr: "Co-founder, 40-person team"
- primary_cta: Start free
- secondary_cta: Talk to sales
- footnote: Prices in USD. Cancel anytime; your data exports with one click.

## What the composer must do
1. Read the brand's `brand.yaml` (layouts[] with useCase/whenToUse, do[]/avoid[], tokens).
2. SELECT + ORDER the sections that best sell this copy for THIS brand.
3. BIND the copy above into the chosen sections' typed slots (content/media).
4. Respect the brand's do[]/avoid[]/neverDo rules.
5. Map any missing section vocabulary onto the brand's nearest equivalent or flag
   the gap in the rationale — do NOT invent off-brand sections.
6. Output a page plan: ordered section list + per-section slot bindings + a short
   rationale, then render.
