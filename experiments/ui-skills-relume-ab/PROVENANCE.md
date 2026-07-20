# Structure provenance

`composition.v1` has no `structureProvenance` field, so these are post-render inferred
stamps mirrored in `lane-b/structure-provenance.json`.

| Section | Source | Evidence |
|---|---|---|
| hero | brand/style archetype | `archetypeRef: hero-case-lead`; no project seed |
| story | shared drawable archetype | cards; no project seed or Relume eligibility |
| results | shared drawable archetype | stack; no project seed or Relume eligibility |
| testimonial | measured brand pattern | `seededFrom: project/testimonial-tab-stats` |
| pricing | Relume structure-only fallback | missing from measured HubSpot layouts; lane B candidates limited to `pricing-content-stack`, `pricing-repeated-grid`, `pricing-table`; emitted as cards |
| closing | measured brand pattern | `seededFrom: project/closing-cta-dark` |

No section was directly stampable as a designed-brand component because the composition
schema has no designed-component reference. Designed components remain a renderer/harness
fallback, not model-visible structural provenance in this run.

Lane A produced no accepted composition after five bounded attempts, so assigning
section provenance to its rejected last draft would be misleading.
