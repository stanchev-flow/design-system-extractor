# Event hero — copy-first plan (fix6, 2026-07-14)

Doctrine (user-directed, now spec law in `spec/archetype-library.md` §3): FIRST the
copy, THEN a layout that serves it, THEN the build. The archetype library is
vocabulary for step 2, never a menu for step 1. This file is the plan of record;
`briefs/event.md` carries the generator-facing brief derived from it.

## 1. The copy (written first, as the marketer would)

The event: **HubSpot Spotlight — the fall 2026 product reveal.** A real, believable
HubSpot moment: Spotlight is HubSpot's recurring launch keynote — online, free, one
sitting, product-led. Voice per `voice.md`: plain-spoken growth talk, verb-led,
numbers as proof inline, sentence case, no exclamation marks, no hype adjectives.

| element | copy (verbatim) | why it earns its place |
| --- | --- | --- |
| meta row | `Oct 8, 2026 · 9:00 AM ET · Streamed live · Free` | an event page's first job is when / what format / what it costs — the scan answer before any persuasion |
| event name | `Spotlight` | the identity moment; typeset in the brand's own serif display, never the wordmark raster (type is a brand fact, a pasted image ground is not) |
| promise | `HubSpot's fall reveal — watch Breeze agents and hundreds of Hub updates ship, live.` | the one-sentence reason to attend: what you SEE (things shipping, live), not what the brand wants to say about itself |
| agenda rail | six Hub product marks + caption `90 minutes across Marketing, Sales, Service, Content, Data and Commerce Hub — and Smart CRM.` | agenda-at-a-glance in the brand's real product iconography; proof of breadth without a bullet list |
| actions | `Save my seat` (primary) · `See the fall lineup` (quiet) | register + not-ready-yet pair, per the brand's CTA-pairing pattern |

Deliberate omissions (no slot-filling): no speaker strip (a product reveal, not a
conference — no speaker facts exist in the brand data), no countdown (motion honesty;
the date IS the urgency), no venue art (streamed event; an office photo would be
decoration), no NEW badge (the meta row already carries the news register).

## 2. The layout, designed for THIS copy

1. **What leads:** the meta row — tracked quiet caption above everything (logistics
   answer first); the eye then falls to `Spotlight` at hero scale: the page's one
   identity moment, licensed by the event-title register.
2. **Second read:** the promise line at the stack measure directly under the name;
   short, one line, no competing media — the copy is the hero.
3. **Proof placement:** the agenda rail sits BELOW the actions at mark scale with its
   caption — quiet, factual, real assets (the six orange Hub icons), never louder
   than the name.
4. **Actions:** the pair rides the brand's actionGroup law (gap 1rem, one filled
   primary, quiet sibling) directly under the promise — register impulse peaks right
   after the "why".
5. **Surface (part of the plan, from the licensed roster):** `surface/raised` — the
   warm cream band (#f8f5ee, evidenced: logo-wall). Near-black display type on warm
   cream gives the launch its editorial weight and BREAKS the gallery's teal
   monotony inside the brand's own grammar. Accent discipline: the brand licenses
   accent TEXT only on dark surfaces (textAccent: null on all light roles), so the
   name renders in ink — orange lives in the primary button and the Hub marks, where
   the catalog licenses it. Centered standalone stack (the brand's standaloneStack
   grammar), tall band character.

**Skeleton:** `hero-event-meta-forward` (meta → name → promise → actions), grown with
an optional `agenda` mark-rail slot (library changelog 2026-07-14) — the copy demanded
a proof rail the archetype lacked; that is the library growing correctly, not a new
one-off archetype.

## 3. Build notes (physics, unchanged law)

- Containment: content container; the rail is a contained mark row (no bleed).
- stackMeasure: the promise wraps at the brand's measured hero stack cap; the meta
  row hugs and never wraps mid-fact.
- AS-59: one filled primary ("Save my seat"); the lineup link takes the brand's quiet
  register. AS-33: rail marks are real files (producticons-*-orange.webp).
- bandHeight `tall` re-registers to the brand's own ladder rung (data-band-rung).
- Contrast: ink/primary on #f8f5ee passes text-contrast trivially; interaction
  contrast on cream verified by the standard battery.
