# magic-trick.md — the human-originality slot

Everything else in this kit converges on the brand's MEDIAN — that is what a system is
for. This file is the reserved seat for the one move a system cannot make: the
left-of-center, unpredictable-from-the-inputs idea that makes a launch memorable.

## Rules of the game

- An idea recorded here may relax **exactly one** `neverDo` rule, on **hero sections
  only** (`recipePolicy.magicTrick.wildcardScope`), as a **one-off** — never promoted to
  the design language, always logged.
- An entry only takes effect when marked **BLESSED** by a human. Machine-proposed
  candidates (below, when present) are options, not decisions.
- Yesterday's idea is not today's idea: entries carry the date and the room they were
  made for.

## The room brief (fill this in — it biases everything downstream)

- **The moment**: <what is launching / happening, and when>
- **The audience**: <who is actually looking, what scene are they from>
- **The feeling**: <the one thing they should feel that the median page wouldn't deliver>

## Freedom budget (the per-section 0-5 dial)

Divergence is a PER-SECTION, HUMAN-SET dial, not an all-or-nothing switch. Before
generating, list the page's sections (`wildcard_generator.py --list-sections`), have the
human annotate each 0-5, and run with `--budget "hero 1 mission 3 cta 0"`:

- **0** median only — the section is never touched
- **1** NUDGE — subtle intensification of the section's existing treatments
- **2** CRANK — strong push of an existing treatment
- **3** INVERT — alignment/anchor inversion (bends a SOFT avoid rule; one-off, logged)
- **4** TRANSPLANT — foreign use-case grammar (registered recipes only)
- **5** RELAX — one neverDo relaxation, ONLY where wildcardScope sanctions it (hero) and
  ONLY via a registered recipe; otherwise the level caps down honestly.

Every candidate is gate-checked (brand neverDo) AND contrast-audited (WCAG, every text
element vs its effective background, hover states included) before it may be proposed.

_(budget not set yet)_

## Machine-proposed candidates

<!-- The wildcard generator writes ranked, gate-checked candidates here. Each names the
     rule it bends, its novelty score, and a rendered preview path. None are blessed. -->

_(none generated yet — run `python3 brand_pipeline/wildcard_generator.py <brand.yaml>`)_

## Blessed

_(nothing blessed yet)_
