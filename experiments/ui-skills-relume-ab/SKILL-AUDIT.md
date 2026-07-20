# UI skill audit

Retrieved 2026-07-17. Classifications: **A** generation-taste guidance, **B**
deterministic quality/audit gate, **C** builder-app engineering/tooling, **D**
unsuitable or risky for this generation pipeline. “Applicable” below never means
installing the skill wholesale.

## Source and classification

| Source | Retrieval | Class | Finding |
|---|---|---:|---|
| [Emil design engineering](https://www.ui-skills.com/skills/emilkowalski/emil-design-eng) | Full page/skill text retrieved | A/B | Strong interaction-motion material. Most timing, easing, reduced-motion and compositor advice overlaps current motion/interaction contracts. Keep only frequency/purpose, keyboard-action restraint, pointer gating, and trigger-relative overlay origin as gaps. Framework examples are not portable. |
| [Make interfaces feel better](https://www.ui-skills.com/skills/jakubkrehel/make-interfaces-feel-better) | Full page/skill text retrieved | A/B | Useful narrow craft checks: concentric nested radii, optical alignment, tabular numerals, wrapping, explicit transition properties and touch targets. Fixed prescriptions (“always 0.96”, shadows over borders, forced image outlines) conflict with measured-brand precedence. |
| [12 principles of animation](https://www.ui-skills.com/skills/raphaelsalaja/12-principles-of-animation) | Full page/skill text retrieved | A/B | Mostly duplicates interaction/motion sanity. Its universal “exit=ease-in” conflicts with Emil’s “never ease-in” and proves these are contextual heuristics, not laws. The useful gateable subset is explicit purpose, bounded duration, consistency by interaction family, one focal motion and no linear spatial motion. |
| [Fixing accessibility](https://www.ui-skills.com/skills/ibelick/fixing-accessibility) | Full page/skill text retrieved after one timeout retry | B | Appropriate as deterministic semantic/keyboard/focus/form checks, not as aesthetic prompt material. Native semantics, names, focus return/trap, disclosure state, linked errors and motion alternatives are valuable. |
| [shadcn](https://www.ui-skills.com/skills/shadcn-ui/shadcn) | Full page/skill text retrieved | C/D | This repo generates structured compositions rendered to static HTML/Python; it is not a React/Tailwind/shadcn project. Installing or exposing shadcn components would homogenize anatomy, radii, cards, semantic color roles and interaction defaults around a recognizable SaaS kit. Only framework-neutral ideas—native semantics, complete widget anatomy, semantic token roles—already exist in contracts. Reject for generation. |
| [Vercel React best practices](https://www.ui-skills.com/skills/vercel-labs/react-best-practices) | Full page/skill text retrieved | C | React/Next waterfalls, RSC, hydration, rerenders and bundle rules do not apply to composition generation. A few generic JS performance ideas are builder-app backlog only. |
| [React Doctor](https://www.ui-skills.com/skills/millionco/react-doctor) | Full page/skill text retrieved | C | React-only scanner; irrelevant to Python/static HTML generation. Potentially useful only if the Studio builder becomes a React surface. |
| [Vitest](https://www.ui-skills.com/skills/antfu/vitest) | Full page/skill text retrieved | C | Repo tests are predominantly pytest plus browser/audit scripts. No generation-quality value; do not add a second unit-test framework. |
| [pnpm](https://www.ui-skills.com/skills/antfu/pnpm) | Full page/skill text retrieved | C | Package-manager/workspace guidance only. The experiment adds no dependency and does not alter package management. |
| [Playwright CLI](https://www.ui-skills.com/skills/microsoft/playwright-cli/) | Full page/skill text retrieved | B/C | Useful execution tooling for deterministic screenshots, keyboard checks, snapshots and traces. It should remain an audit harness, never generation taste. Existing Python Playwright paths are sufficient; no CLI install was needed. |
| [Impeccable](https://impeccable.style) | Product page retrieved; underlying command/rule corpus was not exposed by the page | A/B, low evidence | Product claims brand-aware commands and 46 deterministic anti-slop rules. The repo already has a larger brand-specific anti-slop/gate stack. Do not import unseen rules or run source-mutating commands. Evaluate its detector separately against generated HTML before considering individual rules. |
| [ui.sh](https://ui.sh) | Public landing page retrieved; invite-gated skill bodies unavailable | A/C, low evidence | The visible catalog covers design, ideas, brand kit, componentization, dark mode, responsiveness and markup-from-image. No auditable rule text was available, so none entered the experiment. |

## Deduplicated gap matrix

| Candidate law | New value here | Existing coverage | Conflict/risk | Placement |
|---|---|---|---|---|
| Animation must justify frequency and purpose; frequent or keyboard-initiated actions should be instant | **New** explicit frequency/keyboard criterion | Motion tokens, interaction audit, reduced-motion behavior | Over-removal can erase useful state feedback; preserve non-spatial feedback | Interaction contract + deterministic gate |
| Hover motion only on hover-capable fine pointers | **New** device-capability condition | Responsive recipes distinguish mobile interaction, but no repository-wide CSS gate was found | None when used as capability guard | Interaction contract/gate |
| Anchored overlays transform from trigger; viewport modals remain centered | **New** spatial-origin rule | Overlay anatomy/z-order exists | Do not force scaling if brand has no scale motion | Interaction contract |
| Nested rounded surfaces should be concentric unless evidence says otherwise | **New** optical geometry relation | Radius grammar and measured tokens exist | Must never replace measured asymmetry or square brand geometry | Style directive; later measurable gate |
| Tabular numerals for changing/aligned metrics | **New** stability rule | Stat contracts and fit checks exist | Static expressive numerals may intentionally remain proportional | Style directive/component renderer |
| Balance headings and pretty-wrap body text; avoid single-word orphans | **Partly new** browser mechanic | Wireframe AS-75 line caps and measure fitting prevent squeeze, but do not request CSS wrapping behavior | Browser support; do not use it to override measured line breaks | Renderer/style directive |
| Minimum 44px non-overlapping touch target | **New** explicit target floor | Accessibility/interaction audits cover controls but repository search found no explicit 44px law | Dense desktop can use smaller visuals only if invisible hit area remains non-overlapping | Deterministic accessibility gate |
| Explicit transition properties; animate compositor-safe properties | Mostly implemented conceptually | Motion/interaction contracts and slop checks already reject several motion failures | Universal transform-only rule is too strict for intentional color/clip-path transitions | Deterministic motion gate |
| Native semantics, accessible names, focus trap/return, linked errors, disclosure state | Valuable but **gate-only** | Interaction contracts cover behavior; generated-page battery lacks a clearly complete WCAG semantic pass | ARIA overuse can make native controls worse | Deterministic accessibility gate |
| Active press scale | Already covered/contextual | Existing interaction states and motion axis | Fixed 0.96/0.98 values violate brand motion evidence and can feel generic | Do not promote as universal law |
| Staggered entrance animation | Already covered/contextual | Motion contracts and anti-slop restraint | Easily creates AI-demo theater; contradictory 50ms/100ms prescriptions across skills | Reject as default |
| Shadows over borders / mandatory image outline | No general value | Brand border/shadow and media grammar are measured | Directly overwrites brand grammar | Reject |
| shadcn “compose existing components first” | Concept already implemented | Primitive/block contracts, designed components, renderer capability and reuse-before-create | shadcn anatomy creates framework/style monoculture | Keep existing system; reject import |

## Experiment subset

Lane B receives only seven short, palette-agnostic laws: wrapping/orphans, tabular
numerals, purpose/frequency/keyboard motion restraint, explicit interruptible
compositor-safe transitions with reduced motion, subtle non-layout press feedback and
pointer gating, concentric nested geometry, 44px touch targets, and trigger-relative
overlay origin. It does **not** receive external component markup, palettes, Tailwind
classes, prescribed radii/shadows, fixed animation values, or skill review-format prose.
