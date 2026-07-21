# Test Brief — "AI assistant product launch" (brand-neutral, shared)

Purpose: launch landing page for a new AI-assistant capability inside an existing
product. Run through any brand's `brand.yaml`; the brand supplies the vocabulary.

---

## Brief
- goal: Announce a new AI assistant capability and drive demo requests.
- audience: Existing customers + evaluators who already know the product category.
- tone: Confident, concrete, no hype-words; show, don't shout.
- variations: No — one composed page per brand.

## Copy block (bind into the chosen sections' slots)
- eyebrow: New capability
- headline: Your busywork just met its match
- subhead: An assistant that drafts, files, and follows up inside the tools you already use — so your team ships the work only they can do.
- value_props:
    - title: Drafts in your voice
      body: Learns from what you approve, not from a generic corpus.
    - title: Acts, not just answers
      body: Files the ticket, books the follow-up, updates the record.
    - title: Audited by design
      body: Every action logged, reviewable, and reversible.
- social_proof:
    stat: 4 hours saved per person, per week (median beta team)
    logos: true
    quote: "It cleared a quarter of my calendar in the first month."
    quote_attr: "Team lead, beta program"
- primary_cta: Get a demo
- secondary_cta: Read the docs

## What the composer must do
1. Read the brand's `brand.yaml` (layouts[] with useCase/whenToUse, do[]/avoid[], tokens).
2. SELECT + ORDER the sections that best sell this copy for THIS brand.
3. BIND the copy above into the chosen sections' typed slots (content/media).
4. Respect the brand's do[]/avoid[]/neverDo rules.
5. Map any missing section vocabulary onto the brand's nearest equivalent or flag
   the gap in the rationale — do NOT invent off-brand sections.
6. Output a page plan: ordered section list + per-section slot bindings + a short
   rationale, then render.
