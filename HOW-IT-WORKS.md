# How the Design System Extractor Works

Presentation source. Every claim below is backed by a file in this repo, named inline.

## What it does

Point the system at a live website and it extracts that brand's complete design system as structured, evidenced data — colors, type, spacing, components, layout patterns, motion, copy, voice — with every value traceable to a measurement or a screenshot. It then proves the extraction is real by rebuilding the source homepage from that data alone and scoring the rebuild against the actual site (the "replica gate": a band-by-band visual similarity score, 0 to 1). Once a brand passes, the same data drives generation of new on-brand pages, components, and layouts, policed by automated quality gates. Two brands are fully through: remote.com scores 0.950 and hubspot.com scores 0.956 on their replicas.

## The pipeline, step by step

**Capture.** A browser session saves the live page: full-page screenshots at four viewports (1920/1440/960/375), the DOM, every stylesheet, computed styles per section, motion timings, webfonts, and interactive states (open mega-menus, active tabs, carousel frames). For HubSpot: 1,676 CSS rules across 41 sheets and 59 transition rules (`runs/hubspot-v2/brand/manifest.json`).

**Vision grounding.** The page is sliced into section crops and a vision model writes a factual inventory of each one: approximate color values, concrete typography, component anatomy, surface relationships, verbatim copy. Facts, not impressions — the prompt is a versioned contract (`brand_pipeline/spec/extraction-grounding-prompt.md`). HubSpot: 12 of 12 crops grounded.

**Brand authoring.** An agent reconciles the vision facts against the mined measurements and writes the brand's canonical files: `brand.yaml` (tokens and component contracts, each with provenance and a changelog), `layout-library.yaml` (one layout pattern per observed section, plus reusable component recipes), `section-copy.yaml` (verbatim copy), tagged assets (66 for HubSpot), and a voice document.

**Fail-loud validation.** A deterministic validator (`tools/extract/validate_brand_evidence.py`) runs 23 named checks, C1–C23: every color evidenced, every section grounded, every referenced asset on disk, every measured nav affordance declared. Each check encodes a failure the project actually shipped once.

**The replica gate — the honesty test.** The system rebuilds the source homepage using only the extracted data and scores the result against the real site's screenshot, band by band (50% structure, 30% pixel, 20% height). Fidelity becomes a falsifiable number instead of an opinion. Reports live at `runs/<brand>/brand/compose/replica/replica-report.md`.

**Generating new pages.** For a new page, a model emits a structured composition (ordered sections, slots, copy) — never raw HTML. Deterministic composers (`brand_pipeline/compose_section.py`, `compose_page.py`, `compose_from_composition.py`) render it from brand facts. Every rendering device is fact-gated: a brand without a given fact renders without that device, byte-identically. Real examples: Remote's event-launch page and a deliberately hostile "stress playbook" page (`runs/remote/brand/compose/`).

**Gate battery.** Every rendered page must pass four independent audits: the on-brand check (14 hard invariants covering palette, type, contrast, token provenance), the anti-slop audit (60 named rules, AS-1 through AS-60, run at two viewports), the interaction audit (9 component families checked against WAI-ARIA-derived contracts), and the spacing audit (every rendered gap diffed against the brand's own captured spacing facts).

**Review.** One local server (`./start-studio.sh`, port 1500) serves the studio UI, the run viewer, and every artifact, and each brand exports a portable kit (`runs/<brand>/brand/kit/`) with human- and agent-facing halves.

## Why this beats one-shot generation

A raw agent looking at a screenshot guesses; this system measures. The difference shows up five ways:

- **Evidence vs impression.** Every token in `brand.yaml` carries provenance — the CSS rule, computed measurement, or crop it came from — and a changelog. Nothing is "looks about right."
- **A falsifiable score vs vibes.** Earlier attempts at HubSpot — each one agent driving the whole job end to end — produced replicas scoring 0.474 and 0.503 on the same metric (`runs/hubspot-sol/REPORT.md`, `runs/hubspot-sol-clean-v2/REPORT.md`). Their failure list is what unmeasured generation looks like: navbar missing entirely, page ~2,000px shorter than the source, empty logo wall, one hero photo reused everywhere, the brand's serif absent. The first completed run of the canonical pipeline finished at 0.903; two review passes later it stands at 0.956.
- **Brand data is fully separated from engine code.** Shared renderers contain no brand values (a guard test scans for cross-brand leakage), so brands can't contaminate each other and each extracted brand is a portable, reusable data folder.
- **Regeneration is deterministic replay, not re-rolling dice.** The same brand data and composition render the same page, so fixes are diffs, not fresh gambles — and the replica, the spec book, and every new page stay consistent because they draw from the same facts.
- **Failure modes are named and machine-checked.** Sixty anti-slop rules, 23 validator checks, nine interaction families, and a spacing contract catch regressions automatically instead of hoping a reviewer notices.

## How it learns

The core loop: every human-spotted defect is converted into (a) a schema fact, (b) a renderer law, (c) a named gate rule or validator check, and (d) a regression test — so that class of mistake is caught permanently, for every future brand. Real examples from the changelog:

- Buttons and eyebrows were stretching to full width inside flex columns. The mechanic (content-hugging vs stretched) is now a required observation in the grounding prompt and a renderer rule.
- A rebuilt band once showed two identically-styled primary buttons side by side. Now AS-59 fails any action group with more than one filled-primary action.
- Three HubSpot sections shared one unrecognized "headrail" opener. Recipes now record a recurring anatomy once, with variants and use cases, in the brand's own data (validator check C23):

```yaml
recipes:                      # condensed from runs/hubspot-v2/brand/layout-library.yaml
  - id: section-headrail
    anatomy: [kicker, rule, trail]   # identity chip — dotted leader line — quiet action
    variants: [icon-chip, label-pill, badge-with-icon]
    usedBy: [agent-card-carousel, case-study-header-rail, product-grid-split]
```

The growth curve is the learning curve: the anti-slop registry has reached 60 rules, the validator has grown from 15 checks to 23, and the regression suite has grown 192 → 729 → 776 → 805 → 842 tests (root `changes.md`). Learning also happens at the brand level: recipes and facts are written during extraction, so each brand's system gets richer without touching shared code.

## Skills and agents

The division of labor is strict. Deterministic tools measure (`tools/extract/`: capture, DOM/CSS/motion mining, computed measurement, slicing). LLM agents interpret and author, under written skill contracts: the vision grounding prompt, the layout-analyst authoring skill (authoring is "done" only when the validator exits clean), and the brand-designer operating skill (`brand_pipeline/spec/`). Gates verify: no work counts until the validator, the full gate battery, and the whole test suite pass, and both brands' replica scores hold. Fix sessions open by writing down the baselines they must defend ("pytest 776 passed; Remote replica 0.950 ±0.01" — `runs/hubspot-v2/brand/changes.md`). Doctrine binds all agents: evidence-first, fact-gated devices, provenance comments on structural CSS, and fixes at the generation level — never post-processed HTML.

## Proof points for the demo

- Score arc: 0.474 / 0.503 (earlier one-agent attempts) → 0.903 (first canonical run) → **0.956** after review passes; the worst band, the hero, went 0.771 → 0.978.
- Two brands side by side: **Remote 0.950, HubSpot 0.956**, all gates green on both.
- Gate battery green: validator C1–C23 zero errors, on-brand 14/14 invariants, anti-slop pass at both viewports, interaction and spacing audits pass in strict mode.
- **842 tests passing**, with the full suite re-run green after every change batch.
- Slide-worthy images already on disk:
  - `runs/hubspot-v2/brand/shots/fix1-hero-source-vs-replica.png`
  - `runs/hubspot-v2/brand/shots/fix1-testimonial-tabs-source-vs-replica.png`
  - `runs/hubspot-v2/brand/shots/fix2-logo-strip-source-vs-replica.png`
  - `runs/remote/brand/compose/replica/diff/strip.png` (whole homepage, source vs replica)
  - `runs/remote/brand/shots/event-full-1440.png` (a brand-new composed page)
  - `runs/hubspot-v2/brand/shots/fix2-specbook-recipe-chapter.png` (recipes rendered live in the spec book)

## Honest limitations

Extraction is thorough, not instant: the HubSpot run took about five hours end to end, including its five replica iterations. The pixel-scored fidelity proof covers the homepage replica; new pages are gate-checked rather than pixel-scored. Motion-heavy behavior is static-faithful: videos, autoplaying carousels, and mega-menus render correctly at rest with real, keyboard-operable controls, but the replica comparison scores the closed/first-frame state. And so far two brands have been taken through the full current pipeline; each new brand still surfaces new facts to learn — which is, by design, how the system improves.
