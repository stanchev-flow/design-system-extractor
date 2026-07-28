# HEARTWOOD — Ten Makers, One Material
## Copy-first creative brief · StoryBrand (Donald Miller) · WoodWave Gallery

A new seasonal exhibition landing page for WoodWave Gallery. This brief is written
**copy-first**: the narrative and the words come BEFORE any layout. Each section is
specified by its JOB in the StoryBrand arc (hook → stakes → guide → plan → proof →
offer → objection → close), and the copy for each job is written here in full. Form
follows copy.

**Voice contract (from voice-facts.yaml — obey it):** curatorial, evocative,
first-person-plural ("we"), unhurried; long flowing editorial sentences; NO
exclamation marks; NO SaaS/corporate jargon (leverage, ROI, funnel, scalable);
verb-led CTAs (Buy tickets, Reserve, Subscribe). Display renders UPPERCASE Melodrama;
copy is authored sentence case.

---

## The StoryBrand spine

- **Character (the hero is the VISITOR):** a curious person, screen-tired, who wants
  to stand in front of something made slowly, by hand, and feel time in it.
- **Problem:**
  - *External:* there is nowhere near them to see contemporary wood art gathered in
    one place.
  - *Internal:* they feel starved of the tactile and the made — of craft they can
    stand inside.
  - *Philosophical:* slow making deserves a room of its own; a material grown over
    decades should be met with attention, not a scroll.
- **Guide (WoodWave):** empathetic ("we know the hunger for something real") and
  authoritative (fifty years championing makers; the founder's 1974 vision).
- **Plan:** three plain steps — reserve a ticket, come and wander (guided or at your
  own pace), leave with the material under your skin.
- **Call to action:** direct = *Buy tickets*; transitional = *Subscribe* for opening-
  night invitations.
- **Failure avoided:** the season ends and you never stood in the grain.
- **Success:** you leave slower, seeing wood — and making — differently.

---

## Sections, by job (copy-first)

### 1 — HOOK  ·  job: stop the visitor and name the doorway
- eyebrow: `Winter exhibition · Nov 14 — Feb 28`
- heading (display): `Heartwood`
- subhead: `Ten makers. One material. A room grown slow.`
- primary CTA: `Buy tickets`
- (surface: espresso photo band — a full-bleed timber-sculpture photograph in the
  gallery's warm-dark register)

### 2 — STAKES  ·  job: make the internal + philosophical problem felt
- eyebrow: `Why now`
- heading (display): `You rarely stand before something made slowly`
- body: `We spend our days in front of glass that forgets us the moment we look away.
  Heartwood is the opposite of a feed — ten makers who let a material take the years
  it needs, and ask only that you give it a little of your attention in return.`

### 3 — GUIDE  ·  job: WoodWave as the empathetic, authoritative guide (heritage)
- heading (display): `We have championed makers since 1974`
- body: `Founded by Margaret Woodwave on a single conviction — that the room around
  the work shapes how deeply we feel it — the gallery has spent fifty years giving
  slow craft the space it deserves. Heartwood gathers a generation of wood artists we
  have followed, argued with, and grown alongside.`
- (surface: cream editorial band with the founder portrait; the founding year 1974
  belongs INSIDE the body sentence — do NOT set a year as a separate display heading)

### 4 — PLAN  ·  job: the simple 3-step plan (remove friction)
- eyebrow: `How to visit`
- heading (display): `Three steps into the grain`
- steps:
  1. `Reserve a ticket` — `Choose an adult, student, or group pass; timed entry keeps
     the rooms quiet.`
  2. `Come and wander` — `Arrive when you like, or join a maker-led tour at noon and
     four.`
  3. `Take it with you` — `Leave with the material under your skin — and a print or a
     small work, if it will not let you go.`

### 5 — PROOF  ·  job: success framing + authority (press + numbers)
- press pull-quote: `"The most quietly moving room in the city this winter — you leave
  slower than you arrived."`  — attribution: `The Evening Review`
- stats: `10 makers` · `60 works` · `52 years of championing craft`

### 6 — OFFER  ·  job: the programme + the tickets (the concrete offer)
- eyebrow: `Programme`
- heading (display): `Come and wander`
- programme rows (date · event · room):
  - `Nov 14 · Opening night — makers in conversation · Main Hall`
  - `Dec 06 · Salvage & grain: a carving demonstration · Workshop`
  - `Jan 17 · Slow-looking, guided in silence · Sphere`
  - `Feb 21 · Closing weekend — last light on the timber · Main Hall`
- ticket rows (price · tier):
  - `$24 · Adult` → `Buy tickets`
  - `$18 · Student` → `Buy tickets`
  - `$16* · Group of 5 (*per person)` → `Buy tickets`

### 7 — OBJECTION  ·  job: answer what holds them back (FAQ)
- eyebrow: `Before you come`
- heading (display): `Questions, answered`
- items:
  - q: `Is Heartwood for me if I know nothing about wood?` — a: `Especially then. The
    work asks for attention, not expertise; the tours are written for first-time
    lookers.`
  - q: `Can I bring children?` — a: `Gladly. Under-12s enter free, and the Workshop
    room keeps a table of offcuts for small hands.`
  - q: `Is the gallery accessible?` — a: `Every room, the tours, and the Sphere are
    step-free; assistance is available at the door.`
  - q: `May I photograph the works?` — a: `Without flash, and never for resale — the
    makers keep the rights to their pieces.`

### 8 — CLOSE  ·  job: the final call, with success + the transitional CTA
- eyebrow: `Stay close`
- heading (display): `Do not let the season end without you`
- body: `Heartwood closes on the twenty-eighth of February, and the timber goes home
  with its makers. Reserve a ticket, or leave us your address and we will write you
  when the doors open.`
- primary CTA: `Buy tickets`
- secondary CTA: `Subscribe`
- (surface: cream band → the near-black footer closes the page)

---

## RENDERING CONTRACT (hard — every band must carry visible content)

No section may render as a bare heading. Use ONLY renderable composer vocabularies —
express every list-like band as a `cards` block (a `cards` slot whose copy is a list
of items, EACH with a `heading` AND a `body`/`text`) or as a `list` / marked-list
(each entry a full line of copy). Specifically:

- **PLAN** → a `cards` block with THREE cards, each card `{heading: step title,
  body: the step description}`. Do NOT use a bespoke `steps` slot.
- **OFFER** → render the programme as a `cards` block (four cards, each
  `{heading: "Nov 14 — Opening night…", body: "Main Hall"}`) AND the tickets as a
  second `cards` block or `list` (three items, each `{heading: "$24 · Adult",
  body: "Buy tickets"}` with the Buy-tickets text-arrow). Do NOT use bespoke
  `programme`/`tickets`/`steps` slots.
- **OBJECTION** → a `cards` block (or accordion) with FOUR items, each
  `{heading: the question, body: the full answer}`. Every item MUST carry its answer
  body. Do NOT emit an empty `items` slot.
- **PROOF** → the quote as a `quote`/statement and the stats as a `stats`/cards run
  with each stat's number AND its caption.

If any band would otherwise be heading-only, add its list/cards/description copy from
this brief. Bind real gallery photography where a band supports media.

## Form notes (copy drives layout — for the generator)

- Open on the gallery's dark photographic hero register (gold Melodrama display).
- Alternate espresso and cream bands (the brand's dark-first rhythm); close near-black.
- The PLAN and OFFER lean on the ruled-arrow-row grammar; the OBJECTION uses the
  synthesized faq-accordion; PROOF uses the synthesized press-pull-quote + gallery-
  stat-band — all `provenance: synthesized-from-brand-signals`.
- CTAs are uppercase text-arrow links; the one filled button is the espresso plate
  with a cream hairline border. Sharp corners throughout.
- Bind real gallery photography by `assetRef` (hero-staircase, about-hall, gallery-*,
  founder-portrait); if a maker portrait or a wood-detail shot is needed and no asset
  exists, EMIT AN ASSET-REQUEST rather than a silent placeholder.
