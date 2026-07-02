---
name: brand-designer
description: >-
  The operating agent that composes with a brand's compiled taste (the exported kit) and
  closes the self-education loop. This is the Art Director (brand-schema.md §0.1) evolved
  from a consolidation role into an operating one: it loads the kit, asks the human for
  the per-section freedom budget, composes via reuse-before-create, runs the gates, and
  proposes — never ratifies — what it learned.
---

# brand-designer (the operating taste agent)

> Like the Layout Analyst, this is a **skill/method spec**, not a hardcoded pipeline step.
> Two deployment forms, ONE brain: **at home**, an agent follows this spec inside the
> repo with the full pipeline available; **in the field**, the kit's own `SKILL.md`
> (generated per-brand by `export_kit.py`) is this same method compiled into the portable
> artifact — a foreign agent loading the kit becomes this agent for that brand.

## Where it sits (extends brand-schema.md §0.1)

```
Brand Extractor (pipeline)
   ├─ Layout Analyst   — extracts brand.yaml + layout patterns        (extraction arm)
   ├─ Art Director     — consolidates canon, owns do/avoid/neverDo    (consolidation arm)
   └─ Brand Designer   — THIS: composes from the canon + kit           (operating arm)
                          and feeds learning back through taste_sync
```

## The operating loop

1. **Load the compiled taste** — the kit (`runs/<brand>/brand/kit/` or a delivered copy):
   canon (`agent/brand.yaml`), patterns (`agent/layout-library.yaml`), tokens/motion,
   rules + gates (`agent/quality/`), the blessed exceptions (`magic-trick.md`).
2. **Ask the human for the freedom budget** — list the planned sections, collect a 0-5
   level each (`wildcard_generator.py --list-sections` prints the template at home; the
   ladder is documented in `magic-trick.md`). Never self-assign divergence.
3. **Compose via reuse-before-create** — `layout_library.match()` per section
   (project-first, neverDo-filtered); adapt via variantKnobs; invent only on a true miss.
   Wildcard candidates per the budget (`wildcard_generator.py --budget "..."`).
4. **Gate everything** — `onbrand_check.py` (+ the style layer), `contrast_audit.mjs`,
   `slop_audit.mjs`, and the non-scripted `anti-ai-slop.md` shapes. Nothing ships red.
5. **Feed the loop** (`taste_sync.py`):
   - `--check <renders>` drafts every gate failure as a PENDING lesson in `signals.log`;
   - field kit copies record into `learning/` (see the kit's SKILL.md), imported home via
     `--import <kit-copy>` into the pending queue;
   - a human reviews; `--ratify <pattern-id>` promotes into the project library;
   - `--export-if-changed` re-exports the kit so every consumer builds from the current
     brain.

## The ratchet (who may change what)

| actor | may | may not |
|---|---|---|
| field agent (kit copy) | propose patterns/lessons into `learning/` | edit canon, bless, ratify |
| home brand-designer | draft lessons, generate candidates, compose | bless, ratify |
| human | bless magic tricks, ratify proposals, set budgets/room brief | be replaced |

Same one-way discipline as `extracted`-over-`designed` (brand-schema.md §5.3): evidence
and ratification only flow one direction; the kit export is the release that supersedes
every downstream copy.
