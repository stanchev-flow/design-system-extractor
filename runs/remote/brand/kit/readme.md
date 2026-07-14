# Remote — atomic brand kit

This folder is a **self-contained, machine-actionable brand system**. Everything an agent
needs to write, design, and build on-brand for Remote is in here — no external pipeline,
no repo, no other context required.

## Consumption order (for agents)

1. **`agent/brand.yaml`** — the CANONICAL source of truth: tokens, surface grammar,
   layout instances, composition rules, and the three rule lists (`do`/`avoid`/`neverDo`).
   Contract references resolve locally to `agent/contracts/`.
2. **`agent/layout-library.yaml`** — the brand's reusable, use-case-keyed layout patterns
   (hero, about, gallery, pricing, faq, …). REUSE these before inventing new section
   structure; sizes are relationships/classes, never px — resolve them against the tokens.
3. **`agent/tokens.css`** — every token as a CSS custom property, plus `@font-face` for the
   self-hosted display face. Build pages directly on these variables.
4. **`agent/motion.json`** — the resolved motion system (duration ladder, easings,
   signature moves when evidenced; scroll-reveal, link hover, image parallax). Respect
   `prefers-reduced-motion`. Where present, **`agent/motion-audit.yaml`** carries the
   full per-selector evidence table the values were derived from.
5. **`agent/quality/rules.yaml`** — `neverDo` is the ONLY hard gate. Check your output
   against it before finishing. `quality/anti-ai-slop.md` lists generation-failure shapes
   (contrast, spacing, context bugs) to self-review against.
6. **`magic-trick.md`** — sanctioned one-off rule relaxations and the human's original
   moves. Only entries marked BLESSED may override a rule, and only as documented there.

## The human layer

`human/` holds the same brand as prose for people: `brand.md` (rendered projection of
brand.yaml — never edit it directly), `voice.md` (tone, vocabulary, casing, length
budgets, real section copy), `assets.md`, and `components-preview/index.html` (open in a
browser to SEE every component).

## Ground rules

- **brand.yaml is canonical.** brand.md is a projection. When they disagree, brand.yaml wins.
- **Reuse before create**: match a layout-library pattern first; adapt via its variantKnobs;
  invent only on a true miss — and keep the invention consistent with `compositionRules`.
- **neverDo is hard.** Everything else bends; those rules don't (except via magic-trick.md).
- Source: https://remote.com — extracted, consolidated, and verified by the
  brand pipeline; provenance and confidence for every fact are recorded in brand.yaml.
