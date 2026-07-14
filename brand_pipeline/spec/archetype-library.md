# Archetype Library — Genre Structure as Data

Status: v1 (heroes-saas). Companion data: `brand_pipeline/contracts/archetypes/*.yaml`.
Related: `brand-schema.md` (§4.4e recipes, §4.4f actionGroup), `composition-rules.md`,
`anti-ai-slop.md`, `layout-analyst-skill.md`, `spacing-conformance.md`, `interaction-contracts.md`.

## 1. The law

Generation must behave like a working designer: the **structure** of a section is chosen
for the page's task; the **style** is the brand's, always; the **physics** of good layout
is never negotiable. Three clauses, in force simultaneously:

1. **STYLE IS INVARIANT.** Tokens, type personality, surface grammar, radius/border
   language, spacing rhythm (including the relational ladder), recipes, shadow policy,
   voice — always from the brand's extracted data (`brand.yaml`, `*-style.md`,
   `layout-library.yaml`). An archetype never carries a palette, a typeface, a copy
   register, or a named surface. If an archetype definition ever needs a color to make
   sense, the archetype is wrong.
2. **STRUCTURE IS VARIABLE.** The structural skeleton of a hero (or any genre section)
   may come from this library, selected by brief + page type. Selection is NOT limited
   to skeletons evidenced on the source site. This is the licensed creative axis: a
   brand extracted from a homepage may still get a form-split demo hero or a terminal
   split developer hero, provided every visible property of the instantiation is drawn
   from brand facts.
3. **PHYSICS IS ALWAYS HARD.** Containment law (content container unless a fact licenses
   breakout), stack measure caps, actionGroup facts (§4.4f) and one-primary-per-group
   (AS-59), heading tier integrity, text-on-media contrast/readability, relational
   spacing ladder, interaction contracts, honest affordances. These bind in creative
   mode exactly as in replica mode. An archetype that "needs" a physics exemption is a
   bug in the archetype.

Shorthand used throughout the pipeline: **style-invariant / structure-variable /
physics-hard**.

## 2. What the library is (and is not)

- The library is **data**: YAML documents under `brand_pipeline/contracts/archetypes/`,
  one file per genre (`heroes-saas.yaml` today; `heroes-editorial.yaml`,
  `heroes-ecommerce.yaml`, or non-hero genres later). Shared pipeline code may LOAD and
  ITERATE these files; it must never enumerate archetype ids in code, branch on a
  specific archetype id, or bake genre taxonomy into a Python/JS enum. If code needs a
  new distinction, add a declared field to the schema and read it generically.
- Each entry is a **structural blueprint**: anatomy (ordered slots with roles and
  contracts), geometry (ranges and characters, not pixels), use-case keys, one annotated
  exemplar, known slop traps, and the physics fact families that must bind.
- Entries deliberately reuse the existing schema vocabulary so no translation layer is
  needed: `structure.archetype` comes from the `composition.v1` enum (`stack`, `split`,
  `stack-fullbleed`, `cards`, `collage`, `interlock`, `overlay`, `banded`);
  `structure.scaffoldRef` points into `contracts/scaffolds.yaml`; slot `contract` values
  come from `contracts/blocks.yaml` for composite roles (`form`, `steps`,
  `pricing-card`, `stat-block`, `logo-bar`, `card`, `media-text`, `content-block`) and
  from the atomic element vocabulary already used by `composition.v1` slots and the kit
  primitives for the rest (`eyebrow`, `heading`, `paragraph`, `button`, `badge`,
  `label`, `link`, `image`, `video`); `textLen`/`sizeClass`/`width`/`mediaAspect`/`z`
  reuse `layout-patterns.v1` slot vocabulary; alignment uses the header-context grammar
  (`headerContext` / `splitColumn` / `overlay` / `bandedSeam`).
- An archetype is NOT a template. It carries no copy, no palette, no type choices, no
  fixed pixel values. Instantiation = archetype skeleton × brand facts × section brief.

## 3. Selection — copy-first (REQUIRED)

**The generation flow is copy-first (doctrine, 2026-07-14).** Structure is chosen FOR
copy, never the reverse; a hero assembled by picking a skeleton and filling its slots
is slop with good bones. The required order:

1. **Copy first.** Write the section's copy brief as a working marketer would: the
   concrete claim/offer/moment, every element with a reason to exist (a meta row
   because logistics answer first; a proof rail because breadth is the story; an
   action pair because two intents exist). No slot-filling — an element without a
   copy reason is omitted even if the skeleton offers it. Voice from the brand's own
   `voice.md`/do-avoid evidence.
2. **Layout for THIS copy.** Only then design the structure the copy needs: what
   leads, what the eye does second, where proof and urgency sit, where actions sit —
   and which of the brand's OWN licensed surfaces carries it (surface choice is part
   of the layout plan; across a gallery/campaign, variety within the licensed roster
   is an explicit consideration). The archetype library is the VOCABULARY for this
   step — an existing archetype, a variant knob, or a newly authored archetype (per
   §6) when the copy demands anatomy the library lacks. That is the library growing
   correctly.
3. **Build** through brand facts, physics hard, exactly as §1.

Selection mechanics happen at composition time (the `generate_composition` prompt),
not at render time:

1. **Inputs**: the copy brief (page type + task intent + the authored copy plan, e.g.
   "pricing page, price-transparency lead"), plus the brand's structural resume
   (which recipes, which scaffolds, which knobs the brand evidences).
2. **Shortlist**: filter the genre library by `useCases.pageTypes` and
   `useCases.taskIntents`; rank by affinity notes; emit **2–3 candidate archetypes**
   into the prompt as structured candidates (id, anatomy summary, geometry character,
   slop traps). Never emit the whole library — candidates only, to keep the prompt
   grounded and the choice legible.
3. **Choice**: the composition model picks the candidate that best serves the copy
   brief (never the reverse — candidates it cannot serve honestly are skipped) and
   records it in the composition output (`archetypeRef`), so downstream audits know
   which skeleton was intended.
4. **Instantiation**: every slot binds through brand facts — recipes fill anatomy where
   the brand has its own recurring pattern for a role; tokens/surfaces/typography come
   from `brand.yaml`; spacing from the relational ladder; actions from actionGroup
   facts. The physicsBindings list on the archetype is the audit contract: each named
   fact family must resolve against the brand or the instantiation fails closed (fall
   back to the brand's evidenced hero recipe).
5. **Variance dial**: at low variance, prefer archetypes matching the brand's own
   evidenced hero recipe; at high variance / wildcard lanes, prefer neighbors the brand
   has NOT evidenced. The dial moves the shortlist, never the physics.

## 4. Archetypes vs brand recipes

- **Recipes** (brand-schema §4.4e) are the brand's OWN recurring anatomy, extracted
  from evidence: "this brand's hero kicker is a bordered pill", "this brand's card
  is title→body→link with a top rule".
- **Archetypes** are the GENRE's structural vocabulary: skeletons any competent SaaS
  designer knows, independent of any one brand.
- **Precedence: brand recipes WIN.** When an archetype slot and a brand recipe describe
  the same role, the recipe's anatomy fills the slot (the archetype contributes only
  placement/geometry). If a brand's hero recipe conflicts with an archetype's skeleton
  wholesale (e.g. brand evidences media-left, archetype defaults media-right), the
  recipe wins in replica-leaning lanes; in creative lanes the archetype may override
  ONLY the axis the brief explicitly varies, and the composition must record it.
- Archetype `variantKnobs` exist so this negotiation is declared, not improvised.

## 5. How a brand's style md references the library

Descriptively, never prescriptively. A brand style md MAY say:

> Hero structure: evidenced hero is a centered statement canvas
> (cf. archetype `hero-centered-statement-canvas`); the brand's kicker recipe replaces
> the archetype kicker slot.

It must NOT say "always use archetype X" or import archetype anatomy wholesale into the
brand file — the brand file records what the brand evidences; the library records what
the genre offers. The composition layer is where the two meet.

## 6. Authoring rules (new archetypes, new genre libraries)

1. **Generic names only.** `hero-form-split`, not `hero-hubspot-demo`. Names describe
   structure (`split`, `banded-seam`, `bento-lead`), role emphasis (`stat-forward`,
   `search-first`), or both. Never a company, palette, or campaign.
2. **Standard facts only.** Every slot must be instantiable from facts the extraction
   already captures (tokens, recipes, actionGroup, relational ladder, surfaces, assets,
   interaction contracts). If an archetype needs a fact family that doesn't exist,
   propose the fact family first (as a schema extension), then the archetype.
3. **Exemplar discipline.** One annotated exemplar per archetype, structured as
   `instance` / `skeleton` / `take` / `ignore`. TAKE = skeleton, rhythm, proof
   placement, geometry character. IGNORE = palette, typeface, copy, mascots. Where one
   of our own run lanes evidences the archetype, cite the run crop path under
   `exemplar.evidence` — those stay verifiable.
4. **Slop traps are mandatory.** 2–3 per archetype, tied to AS rule numbers where the
   registry covers them. If a new archetype has a failure mode the registry lacks,
   propose the AS rule in the same change.
5. **Physics bindings are exhaustive.** The core five bind for every archetype:
   `containment`, `headingTier`, `headerContext`, `relationalRhythm`,
   `surfaceContrast`. Add `actionGroup`, `stackMeasure`, `textOnMedia`,
   `gridEqualize`, `controlMeasure`, `assetFidelity`, `interaction`, `motion` where the
   anatomy implies them. An auditor must be able to run the bindings list as a
   checklist.
6. **Ranges, not pixels.** Geometry uses characters (`compact`/`standard`/`tall`/
   `viewport`) and fractional ranges (`mediaFraction: {min, max}`). Fixed pixels belong
   to instantiation, where brand facts and device geometry decide.
7. **One file per genre; a top-level changelog per file.** Version with
   `schemaVersion: hero-archetypes.v1`. Additive changes append to the file changelog;
   breaking schema changes bump the version and this spec.
8. **New genre libraries** (editorial, ecommerce, docs) copy this schema wholesale.
   Genre-specific slot roles are fine; genre-specific SCHEMA fields require a spec
   update here first.

## 6b. Implemented vocabulary extensions (phase-2 2026-07)

Of the §6-list extensions proposed in PHASE2-PLAN.md, the gallery needed three; they
are implemented as follows (the rest are deferred, noted in the gallery lane's
changes.md):

1. **`knobs.bandHeight`** (`compact|standard|tall`; `viewport` degrades to `tall`) —
   seeded from the archetype's `geometry.bandHeight` at skeleton application, consumed
   by `compose_section.band_height_css`: the section's vertical padding re-registers
   to the NEAREST rung of the brand's OWN `section-*` spacing token family, emitted as
   a `var(--space-…)` reference so token provenance and the spacing audit both see the
   brand's own fact. The knob never invents a length; no rung in the wanted direction
   degrades to standard rhythm.
2. **`requiresOffGrid`** (data-side flag, no schema bump) — set on archetypes whose
   anatomy needs off-grid geometry devices (seam straddle, crest bleed, ghost
   z-depth); `shortlist(off_grid=False)` excludes them, keeping demotion data-driven.
3. **`archetypeRef`** (composition.v1 section key) — the recorded skeleton choice;
   drives skeleton-first normalization, the `data-archetype` wrapper stamp, and the
   HARD `archetype-physics:<section>` gate rows.

## 7. Failure posture

If, at instantiation, a required physics binding cannot resolve (no actionGroup facts,
no scrim/contrast fact for text-on-media, no seam grammar for banded), the pipeline
must not improvise: it falls back to the nearest archetype whose bindings all resolve,
or to the brand's own evidenced hero recipe. Creative mode widens the structural
shortlist; it never widens what counts as resolved physics.
