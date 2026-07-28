---
pageType: customers
genre: heroes-saas
variance: mid
requireArchetype: true
excludeArchetypes: [hero-index-masthead, hero-content-featured-lead]
---
# Customer story — Angel City FC on HubSpot (copy-first plan + generator brief)

New page type for the hubspot-v2 lane: a **customers / customer-story page**. No lane
under `compose/` builds this page type — the existing set is homepage, product, pricing,
about, blog, demo, developer, event (hero-archetypes) and a product-launch bakeoff. A
customer-story page is core to HubSpot's identity (proof-by-numbers is a measured voice
trait) and is genuinely new creative output, not a repeat.

Doctrine (spec/archetype-library.md §3): **copy first, then a layout that serves it.**
Everything below is grounded in the run's OWN extracted evidence
(`section-copy.yaml` testimonial panels + `assets-tagged.json`) — nothing invented. The
flagship story is **Angel City FC** (the mid-sized-business testimonial panel), with two
further real stories (Unipart, Youth on Course) and the extracted customer logo wall.

## Voice contract (voice-facts.yaml — the copy budget)

Sentence case headings; product/proper nouns keep their capitals. Mean sentence
≤ 14 words, p90 ≤ 23. No exclamation marks — the strongest punctuation is the orange
period closing a landmark heading. No hype lexicon (leverage, world-class, supercharge,
game-changing, …). Verb-led CTA labels. Numbers carry the sophistication.

## The copy (written first, as the marketer would)

### 1 — Hero (customers-hub opener leading with ONE flagship story)

- kicker / register label: `Customer stories`
- heading (hub claim, closes with the licensed orange period):
  `See how teams grow on HubSpot.`
- subheading (what the reader will find, one line):
  `Real results from the marketing, sales, and service teams that run on one platform.`
- featured case card (the counterweight — Angel City FC):
  - customer mark / photo: `046-angel-fc.png`
  - pulled stat (the card's large numeral): `300%+`
  - stat label: `fan database growth in two years`
  - outcome line: `Angel City FC grew its fanbase without losing the personal touch.`
  - read action (quiet/text register): `Read the story`
- further customers (quiet mark run beneath the split — real extracted logos):
  `019-ebay-logo.svg`, `020-doordash-logo.svg`, `021-reddit-logo.svg`,
  `022-tripadvisor-logo.svg`, `023-eventbrite-logo.svg`

### 2 — The story (challenge → approach → outcome, three parallel beats)

- eyebrow: `The challenge`  (register label; the section heading carries the claim)
- heading: `Grow the fanbase, keep the connection.`
- three benefit/story items (declare list intent so they render as the brand's marked
  list, not look-alike paragraphs):
  1. `A growing club, scattered fan data.` — Fan sign-ups lived across ticketing,
     email, and social, with no single view of the supporter.
  2. `One platform for marketing and service.` — Marketing Hub and Smart CRM put every
     fan interaction in one place for the whole team.
  3. `Personal at scale.` — Automated journeys stayed on-brand, so every fan still felt
     spoken to directly.

### 3 — Results (the real extracted stats — a stat run, one slot, array copy)

- heading: `The results.`
- stats (ONE `stat`/`stat-block` slot whose `copy` is an ARRAY of {value, label}
  objects — do NOT add a `statCount` / `count` knob; the array length IS the count).
  Each VALUE is a clean numeral (no leading `~`); each LABEL is 1–6 words:
  - `300%+` — `fan database growth`
  - `350+` — `new fans a week`

### 4 — Pull quote (the verbatim extracted testimonial)

- quote: `HubSpot gave us the tools we needed to grow without losing the personal
  connection with our fans. Their support has been vital to our continued marketing
  success.`
- attribution: `Whitney Hallock, Director of Marketing & Experience, Angel City FC`

### 5 — More customer stories (two further real stories, as cards)

- heading: `More proof, more industries.`
- card A (Unipart — enterprise): mark/photo `045-unipart-1.png`; stat `Millions → billions`;
  line `Unipart grew its pipeline from millions to billions in twelve months.`;
  attribution `Adam Jones, Unipart`; action `Read the story`
- card B (Youth on Course — small business): mark/photo `047-youth-on-course.png`;
  stat `59%`; line `Youth on Course lifted membership 59% year over year with a Breeze
  Customer Agent.`; attribution `John Mothershead, Youth on Course`; action `Read the story`

### 6 — Customer logo wall (the extracted proof strip)

- heading: `299,000+ customers in over 135 countries grow with HubSpot.`
- marks (real files): `019-ebay-logo.svg`, `020-doordash-logo.svg`, `021-reddit-logo.svg`,
  `022-tripadvisor-logo.svg`, `023-eventbrite-logo.svg`
- Bind the wall as ONE repeatable `logo-bar` slot whose copy is the ARRAY of
  {alt, asset} objects above (the brand's measured logo strip).

### 7 — Closing CTA (the brand's dark conversion bookend)

- heading (a FULL landmark line — long enough to fill the closing stack measure,
  ~55–60 characters — closing with the orange period; heading-only, no body slot):
  `Make your growth story impossibly easy, with HubSpot.`
- actions — ONE `actionGroup`/`button` slot whose `copy` is an ARRAY of two action
  objects (never `primaryCta`/`secondaryCta` knobs):
  - `{ "label": "Get a demo", "styleHint": "filled" }`
  - `{ "label": "Get started free", "styleHint": "outlined" }`

## The layout, designed for THIS copy

- **hero**: `hero-case-lead` (the customers-hub mold) — left hub claim column, right a
  single bounded case card as counterweight (Angel City mark, the 300%+ numeral, the
  outcome line, a quiet read action), a further-marks logo row beneath. `surfaceIntent`
  from the licensed roster: `primary` (warm off-white canvas) — the case card and the
  logos carry the visual weight; the dark band is reserved for the closing bookend.
- **story**: a three-beat marked list (challenge/approach/outcome) — the brand's
  orange-checkmark list device applies here (a benefit run on a light surface).
- **results**: a stat run at the brand's large serif numeral register.
- **quote**: a single testimonial with real attribution.
- **more stories**: two flat white card plates on hairline borders (r8), each with a
  media well, a pulled stat, and a quiet read action.
- **logos**: the measured item-box logo strip.
- **closing**: `surfaceIntent: "inverse"` (deep teal #042729, cream ink) — the brand's
  measured closing rhythm; one filled-orange primary + one outlined-cream secondary.

## Accent & physics discipline (the measured signatures)

- Orange lives ONLY in actions/links, product marks, checkmarks, and the landmark
  heading periods (`action-orange-scope`, ≤ 2% of page paint). Body and headings paint
  ink, never orange (accent TEXT is licensed only on the dark closing band).
- Landmark bands (hero + closing) each CARRY at least one licensed accent device — the
  orange period on their headings (`orange-period` floor 1).
- One filled primary action per group (AS-59): the hero's read action and the story
  cards' read actions stay quiet/text register; the page primary is `Get a demo`.
- Third-party customer marks appear ONLY in factual proof contexts (the case cards, the
  logo wall) — never as decoration (AS-67 / AS-52).
- Buttons are 8px rectangles, never pills; card hover is a wash plus a hairline ring,
  never elevation.

## Knob discipline (HARD — the composition-lint gate enforces it)

Set a section `knobs` entry ONLY when it is a knob a renderer consumes or the chosen
archetype declares: `columns`, `align`, `mediaSide`, `bandHeight`, `supportKind`,
`caseSide`. Never invent count/enumeration knobs (`statCount`, `cardCount`, …) — the
copy array length is the count. Never put ACTIONS in knobs (`primaryCta`,
`secondaryCta`, `cta`) — every action is an object inside ONE `actionGroup`/`button`
slot's copy array ({label, styleHint}). When in doubt, omit `knobs` entirely (an
unconsumable knob is a HARD lint failure that silently drops intent).

## Deliberate omissions (no slot-filling)

No pricing table (this is a proof page, not a plan page), no video (motion honesty —
the stills are the proof), no invented metrics (every number above is a real extracted
stat), no speaker/team strip.

Emit a full multi-section page (hero → story → results → quote → more stories → logos →
closing). The deterministic renderer supplies the brand nav and footer around it.
