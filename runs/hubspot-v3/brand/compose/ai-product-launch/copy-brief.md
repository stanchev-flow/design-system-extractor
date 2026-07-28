---
pageType: product
genre: heroes-saas
variance: mid
requireArchetype: false
excludeArchetypes: [hero-form-split, hero-form-centered, hero-pricing-value-forward, hero-pricing-plan-peek, hero-index-masthead]
---
# AI product launch — Breeze, HubSpot's AI (copy-first plan + generator brief)

A NEW page for the hubspot-v3 lane: an **AI product-launch page** for **Breeze**, HubSpot's
built-in AI. This is not a replica of the homepage and it is not one of the existing
`compose/` bakeoffs — it is genuinely new creative output composed FROM the faithful v3
harness (its tokens, components, recipes, responsive facts, and captured copy voice).

Doctrine (spec/archetype-library.md §3): **copy first, then a layout that serves it.**
Everything below is grounded in the run's OWN extracted evidence — `voice-facts.yaml`
(voice + proof points), `section-copy.yaml` (real Breeze/agent copy + case panels), and
`media-assets.yaml` / `assets-tagged.json` (measured asset kinds + intrinsic sizes).
Breeze, Breeze Agents (Customer Agent, Prospecting Agent, Data Agent), and every metric
below are REAL captured HubSpot facts. Net-new launch framing (the hero eyebrow
"Introducing Breeze" and the transition line labels) is flagged as **experimental copy**
below; no invented numbers, dates, availability claims, or fabricated capabilities appear.

## Voice contract (voice-facts.yaml — the copy budget)

Sentence-case headings; product/proper nouns keep their capitals. Second person, warm and
plainspoken. Short-to-medium active sentences. No hype lexicon (`synergy`, `disrupt`,
`revolutionary`). Lead with the customer's growth outcome, acknowledge difficulty then
promise it made easier, back claims with concrete proof. No exclamation marks — the
strongest punctuation is the licensed orange period closing a landmark heading. Verb-led,
direct-imperative CTA labels (`Get a demo`, `Get started free`, `Learn more`).

## The copy (written first, as the marketer would)

### 1 — Hero (the launch promise; the brand's measured full-bleed dark hero)

- eyebrow / register label (**experimental copy** — net-new launch label): `Introducing Breeze`
- heading (the promise, grounded in section-copy "AI that works with you, and for you",
  closes with the licensed orange period):
  `Meet Breeze. AI that works for you, and with you.`
- subheading (one line, real value): `Breeze is HubSpot's AI, built into the same customer
  platform your team already runs on — so it works with your data from day one.`
- actions — ONE `actions`/`button` slot whose `copy` is an ARRAY of two action objects
  (never `primaryCta`/`secondaryCta` knobs):
  - `{ "label": "Get a demo", "styleHint": "filled" }`
  - `{ "label": "Get started free", "styleHint": "outlined" }`
- background media (full-bleed photograph): `018-hs-full-bleed-1-optmised.webp`
- floating utility card (the brand's measured floating-card counterweight — a real proof
  line, NOT navigation): pulled proof `Resolve over 65% of customer inquiries automatically`

### 2 — Customer proof row (credibility before the pitch)

- heading: `299,000+ customers in over 135 countries grow their businesses with HubSpot.`
- marks — ONE `logo-row`/`logo-bar` slot whose copy is an ARRAY of {alt, asset} objects
  (the brand's measured customer logo strip; third-party marks in a factual proof context):
  `019-ebay-logo.svg`, `020-doordash-logo.svg`, `021-reddit-logo.svg`,
  `022-tripadvisor-logo.svg`, `023-eventbrite-logo.svg`

### 3 — Product education (what Breeze is — one AI layer across the platform)

A clean copy-left / illustration-right SPLIT — heading + subheading + one body paragraph +
the illustration. Do NOT add a repeatable item/detail array here: in a `split` archetype a
multi-record item collection is not consumable (only the `cards` path consumes item
arrays), so the three points are folded into the body prose below.

- heading: `One AI layer across your whole platform.`
- subheading: `Breeze works from your Smart CRM, so it already knows your customers,
  your content, and your pipeline. No bolt-on, no separate model to feed.`
- body (one paragraph; the three points as prose, not an array): `Because it's grounded in
  the data every hub already shares, Breeze answers reflect your real customers. It shows
  up inside Marketing, Sales, and Service Hub — not in a separate tab you have to remember.
  Turn it on and it works with what you have, with no data project required first.`
- illustration media (a real product graphic — image role, NOT an icon):
  `026-customer-platform-graphic-breeze.png`

### 4 — Feature proof (the three Breeze Agents — the launch's headline capability)

- eyebrow / headrail (**experimental copy** — register label): `Explore Breeze Agents`
- heading (verbatim captured section-04 headline, closes with the orange period):
  `Built-in AI agents that work for you 24/7.`
- body (verbatim captured supporting copy): `Breeze Agents are your always-on teammates.
  They can resolve over 65% of customer inquiries, accelerate your sales pipeline, and whip
  up quality content in no time.`
- cards — ONE repeatable `card-carousel` slot with contract `card` (or `feature-item`),
  NOT contract `carousel` (which flattens the records and fails the semantic-grouping
  lint); its `copy` is an ARRAY of three agent objects, each with a real agent image bound
  as the card's LEAD MEDIA (image role — these are 640×640 photographs, not icons):
  - `{ heading: "Customer Agent", body: "Resolve over 65% of your customer inquiries
    automatically, around the clock.", asset: "036-customer-agent-en-2x.png" }`
  - `{ heading: "Prospecting Agent", body: "Spot buying signals, source contacts, and
    launch personalized outreach — instantly.", asset: "037-prospecting-agent-en-2x.png" }`
  - `{ heading: "Data Agent", body: "Get instant answers to questions about your customer
    data, in plain language.", asset: "038-data-hub-en-2x.png" }`

### 5 — Integrations (Breeze works with the tools you already use)

- heading: `Works with the tools you already use. 2,000+ integrations.`
- read action (quiet/text register): `See all app integrations`
- marks — ONE `logo-collage`/`logo-bar` slot whose copy is an ARRAY of {alt, asset}
  integration marks (spot icons in a mark role — small marks, never blown-up media wells):
  `039-gmail-icon-3.svg`, `040-shopify-icon-3.svg`, `041-mailchimp-icon-3.svg`,
  `042-zapier-icon-2.svg`, `043-google-ads-icon-2.svg`, `044-slack-icon-2.svg`

### 6 — Results (the real AI metrics — a stat run, ONE stat-block slot)

The proof metrics ride in their OWN section as a stat run (the renderer emits real stat
markup — value at the serif numeral register, label on body — only from a dedicated stat
slot; a stat slot buried inside the testimonial card would be silently dropped). This is
the AI-relevant Small Business result (Youth on Course trained a Breeze Customer Agent).

- eyebrow / register label: `Breeze in the field`
- heading: `Real results from a real Breeze Customer Agent.`
- stats — ONE `stats`/`stat-block` slot whose `copy` is an ARRAY of {value, label} objects
  (the array length IS the count; each value a clean numeral, each label 1–4 words). These
  MUST render as stat items (anatomy-presence checks for rendered stat values):
  - `59%` — `increase in members YoY`
  - `17%` — `faster response time`
  - `7%` — `higher customer satisfaction`

### 7 — Proof in the field (a single testimonial — quote + photo + attribution)

A single testimonial SPLIT: a case photo, one verbatim quote, and its attribution. Do NOT
declare a tab rail / tabs device / multi-panel switcher (contract `tabs` has no consumer in
the generative renderer) and do NOT put a stat slot here (the dedicated testimonial
renderer drops it — the numbers live in section 6). One strong, AI-relevant story is the
honest choice: the Small Business case (Youth on Course trained a Breeze Customer Agent).

- portrait / case photo (image role): `047-youth-on-course.png`
- quote (verbatim captured): `Just like you'd train a new hire, we trained Customer
  Agent — and now it's often more accurate than we were. And when something needs a human
  touch, our team can step in quickly — with full context at their fingertips.`
- attribution: `John Mothershead, Director of Member Success, Youth on Course`

### 8 — Closing CTA (the brand's dark conversion bookend)

- heading (a FULL landmark line, ~50–55 characters, closing with the orange period,
  grounded in captured section-09 copy; heading-only, no body slot):
  `Make impossible growth feel impossibly easy, with Breeze.`
- actions — ONE `actions`/`button` slot whose copy is an ARRAY of two action objects:
  - `{ "label": "Get a demo", "styleHint": "filled" }`
  - `{ "label": "Get started free", "styleHint": "outlined" }`

## The layout, designed for THIS copy

- **hero**: reuse the brand's measured `full-bleed-photo-hero` (overlay archetype,
  `surfaceIntent: "inverse"` — the deep teal / cream bookend). Full-bleed photograph
  behind cream ink; left promise column; a single floating utility card as counterweight
  carrying the 65% proof line; the licensed orange period on the display heading. This is
  the only accented text-on-media band besides the closing bookend.
- **customer proof row**: `centered-heading-over-logo-row` (row, `surfaceIntent:
  "primary"`) — a centered claim over the measured customer logo strip.
- **product education**: a clean copy-left / illustration-right `split`
  (`surfaceIntent: "primary"`) — left copy (heading + subheading + one body paragraph),
  right the real Breeze platform graphic as illustration media. No item array.
- **feature proof**: a `cards` collection band (`surfaceIntent: "accent-soft"` — the
  brand's warm breeze band) — headrail eyebrow, the captured 24/7 headline, and ONE
  repeatable card slot (contract `card`) carrying the three agent cards with the agent
  images as lead media. The `cards` path is what consumes a multi-record item array.
- **integrations**: `copy-left-logo-collage-inset` (split, `surfaceIntent: "primary"`) —
  the claim + a quiet read link + the integration-mark collage (small marks).
- **results**: a stat run (`surfaceIntent: "primary"`) — eyebrow + heading + ONE
  stat-block slot; the brand's large serif numeral register. Stat items MUST render.
- **testimonial**: a single testimonial `split` (`surfaceIntent: "primary"`) — case photo,
  one quote + attribution. No stat slot (it lives in the results section), no tab rail /
  tabs device (contract `tabs` is not consumable in the generative renderer).
- **closing**: `dark-band-cta` (band, `surfaceIntent: "inverse"`) — deep teal, cream ink,
  one filled-orange primary + one outlined-cream secondary; the brand's measured closing
  rhythm.

## Accent & physics discipline (the measured signatures)

- Orange (`#ff4800`) lives ONLY in filled actions/links, product marks, and the landmark
  heading periods (`action-orange-scope`, ≤ ~2% of page paint). Body and headings paint
  ink on light; accent TEXT is licensed only on the dark hero + closing bands.
- The two landmark bands (hero + closing) each CARRY the licensed orange-period device on
  their display heading (`orange-period` floor 1).
- Display-class headings are reserved for the hero and the closing CTA (the brand's real
  display bands). Interior sections use the `h2` section-title register, not `display` —
  so every authored display heading actually renders as display.
- One filled primary action per group (AS-59): the integrations read link and the
  testimonial read link stay quiet/text register; the page primary is `Get a demo`.
- Third-party marks (customer logos, integration icons, case photos) appear ONLY in
  factual proof contexts — never as decoration (AS-67 / AS-52).
- Buttons are 8px rectangles, never pills; card hover is a wash plus a hairline ring on the
  8px radius, never elevation.

## Asset binding discipline (AS-80 — kind ↔ slot-role eligibility)

- IMAGE roles (hero background, illustration, card lead media, testimonial portrait) bind
  PHOTOGRAPH-kind assets only: `018-hs-full-bleed-1-optmised.webp`,
  `026-customer-platform-graphic-breeze.png`, the 640×640 agent images
  (`036/037/038-*.png`), and the case photos (`045/046/047-*.png`).
- MARK / ICON roles (logo rows, integration collage) bind logo/spot-icon assets at mark
  fit — NEVER blown up into a media well: customer logos `019–023-*.svg`, integration
  icons `039–044-*.svg`.
- If a needed image is genuinely missing for a role, emit an asset-request manifest entry
  for that slot rather than substituting an icon into an image well.

## Contract & sizeClass discipline (HARD — satisfy BOTH at once, every attempt)

Two independent rules that must hold SIMULTANEOUSLY (do not fix one and regress the other):

1. **sizeClass is a closed enum.** Every slot's `sizeClass`, when present, MUST be one of
   `colossal`, `hero`, `display`, `title`, `body`, `caption`. NEVER invent values like
   `control`, `button`, `label`, or `eyebrow`. For action-group / button slots and small
   labels, OMIT `sizeClass` entirely (or use `caption`). Display headings on the hero and
   the closing CTA use `display`; interior section headings use `title`.
2. **Multi-record content binds a repeatable component contract.** Any slot whose `copy`
   is an ARRAY of multi-field records ({heading, body, …}) MUST use contract
   `feature-item`, `card`, or `content-block` — NEVER `list` or `carousel` (those flatten
   the records and HARD-fail the semantic-grouping lint). Single-string list copy may use
   `list`; multi-field record arrays may not. This applies to the product-education detail
   run AND the feature-proof agent cards.

## Knob discipline (HARD — the composition-lint gate enforces it)

Set a section `knobs` entry ONLY when a renderer consumes it or the chosen archetype
declares it — for THIS page the only safe knobs are `columns`, `align`, and `mediaSide`.
Do NOT set `caseSide`, `supportKind`, `bandHeight`, or any other knob: they have no
consumer here and HARD-fail the knob-consumption lint (declared intent silently drops).
Never invent count/enumeration knobs (`statCount`, `cardCount`, …) — the copy array length
IS the count. Never put actions in knobs (`primaryCta`/`secondaryCta`/`cta`) — every action
is an object inside ONE `actions`/`button` slot's copy array ({label, styleHint}). When in
doubt, omit `knobs` entirely.

## Deliberate omissions (no slot-filling)

No pricing table (this is a launch/education page, not a plan page), no video (motion
honesty — the stills are the proof), no invented metrics (every number above is a real
captured stat), no team strip, no form (the CTA is a demo/get-started pairing, not a
lead-gen form on this page).

Emit a full multi-section page (hero → customer proof → product education → feature proof →
integrations → results → testimonial → closing). The deterministic renderer supplies the
brand nav and footer around it.
