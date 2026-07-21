# Test Brief — "Annual conference registration" (brand-neutral, shared)

Purpose: event registration page for the brand's flagship annual conference.
Run through any brand's `brand.yaml`; the brand supplies the vocabulary.

---

## Brief
- goal: Drive registrations for a two-day annual user conference.
- audience: Practitioners and team leads; mix of returning attendees and first-timers.
- tone: Energetic but specific — sell the agenda and the people, not adjectives.
- variations: No — one composed page per brand.

## Copy block (bind into the chosen sections' slots)
- eyebrow: Two days · In person + streamed
- headline: The people building what's next, in one room
- subhead: Two days of working sessions, product deep-dives, and the practitioners behind the playbooks you already use.
- value_props:
    - title: 40+ working sessions
      body: Real builds on stage — bring your laptop, leave with it running.
    - title: The roadmap, unfiltered
      body: Product leads present what ships next and take questions live.
    - title: Your people
      body: Meet the community behind the templates, integrations, and answers.
- social_proof:
    stat: 6,000 attendees last year · 92% would recommend
    logos: true
    quote: "I planned our whole next quarter on the flight home."
    quote_attr: "Marketing operations manager"
- primary_cta: Register now
- secondary_cta: See the agenda
- footnote: Early pricing ends soon. Streaming pass is free.

## What the composer must do
1. Read the brand's `brand.yaml` (layouts[] with useCase/whenToUse, do[]/avoid[], tokens).
2. SELECT + ORDER the sections that best sell this copy for THIS brand.
3. BIND the copy above into the chosen sections' typed slots (content/media).
4. Respect the brand's do[]/avoid[]/neverDo rules.
5. Map any missing section vocabulary onto the brand's nearest equivalent or flag
   the gap in the rationale — do NOT invent off-brand sections.
6. Output a page plan: ordered section list + per-section slot bindings + a short
   rationale, then render.
