# Changes — brand_pipeline/contracts/archetypes/

## 2026-07-13 — Phase 1: SaaS hero archetype library (new files only)

- NEW `heroes-saas.yaml` — 29 hero archetypes (`hero-archetypes.v1`), spanning
  homepage, pricing, product, about, blog, careers, demo/lead-gen, developer, event,
  signup, customers, comparison. Anatomy/geometry vocabulary reuses `composition.v1`
  archetypes, `scaffolds.yaml` refs, `blocks.yaml` + atomic element contracts, and
  `layout-patterns.v1` slot fields. Exemplar evidence cites existing crops in
  `runs/hubspot-v2` and `runs/remote` (paths verified).
- NEW `../spec/archetype-library.md` — the style-invariant / structure-variable /
  physics-hard law, selection flow, recipe precedence, authoring rules.
- NEW `PHASE2-PLAN.md` — wiring plan (archetype_library.py loader, generate_composition
  candidate injection, adapt_brand_section instantiation ordering, gate mapping,
  hubspot-v2 hero gallery lane under `runs/hubspot-v2/brand/compose/hero-archetypes/`).
- Verification: YAML parses; ids unique; all 12 declared page types covered; core five
  physicsBindings present on every entry; slot dicts free of flow-mapping junk keys;
  exemplar crop paths exist on disk. No existing file edited (phase-1 fence).
- Follow-up (phase 2): wiring edits per PHASE2-PLAN.md; vocabulary extensions listed in
  its §6 (bandHeight knob, code-panel contract, typeAsGraphic license, reducedMotion
  contract entry, seamOffset fact, requiresOffGrid flag).
