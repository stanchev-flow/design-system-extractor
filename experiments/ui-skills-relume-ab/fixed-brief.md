---
pageType: customers
genre: heroes-saas
variance: mid
requireArchetype: true
excludeArchetypes: [hero-index-masthead, hero-content-featured-lead]
---
# Customer evidence page

Create one copy-first HubSpot customer-evidence page. Preserve this order and copy shape.

## Hero — orient and prove
- Eyebrow: `Customer stories`
- Heading: `See how teams grow on HubSpot.`
- Body: `Real results from marketing, sales, and service teams that run on one platform.`
- Featured proof: Angel City FC, `300%+`, `fan database growth in two years`
- Supporting line: `Angel City FC grew its fanbase without losing the personal touch.`
- Action: `Read the story`
- Bind `046-angel-fc.png` as the featured proof media.

## Story — explain
- Heading: `Grow the fanbase, keep the connection.`
- Three atomic items:
  1. `A growing club, scattered fan data.` — `Fan sign-ups lived across ticketing, email, and social, with no single view of the supporter.`
  2. `One platform for marketing and service.` — `Marketing Hub and Smart CRM put every fan interaction in one place for the whole team.`
  3. `Personal at scale.` — `Automated journeys stayed on-brand, so every fan still felt spoken to directly.`

## Results — quantify
- Heading: `The results.`
- One repeatable stat slot:
  - `300%+` — `fan database growth`
  - `350+` — `new fans a week`

## Testimonial — human proof
- Quote: `HubSpot gave us the tools we needed to grow without losing the personal connection with our fans. Their support has been vital to our continued marketing success.`
- Attribution: `Whitney Hallock, Director of Marketing & Experience, Angel City FC`

## Pricing — support plan choice
This use case is intentionally absent from the measured HubSpot layout library. Render
one atomic repeatable `card` slot with three complete records; do not use a table.
- `Starter` — `For small teams building a shared customer foundation.` — `Start free`
- `Professional` — `For growing teams coordinating campaigns and service.` — `See Professional`
- `Enterprise` — `For organizations that need governance across teams.` — `Talk to sales`

## Closing — convert
- Heading: `Make your growth story impossibly easy, with HubSpot.`
- Actions: `Get a demo` (filled), `Get started free` (outlined)

Use the extracted brand assets only. Do not invent metrics, copy, visual tokens, or filenames.
Do not invent enumeration or action knobs. In particular, emit no knobs on results,
pricing, testimonial, or closing; arrays carry their own count and action variants.
