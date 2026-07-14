# Style resolution + pass-1 prompt injection (pass 3, 2026-07)

Spec for the two pass-3 stages that make pass-1 facts and the imported
style-library SHAPE generation instead of only policing it. Plan of record:
`contracts/style-library/INTEGRATION-PLAN.md`; execution log:
`contracts/style-library/changes.md`. Pass-2 finding this closes: `build_prompt`
was byte-identical with or without pass-1 artifacts — facts gated output but
never reached the generator.

## 1. The resolver — `brand_pipeline/style_resolver.py`

`resolve(section, style, library, brand)` computes a merged section spec from
the style-library package (`contracts/style-library/`), never stored per pair.

Precedence (strongest → weakest; INTEGRATION-PLAN §4.2):

```
gate battery (physics — a rejection layer, not a merge level; NOT in the resolver)
  brand measured/derived facts        brand_bindings(): style-scale.yaml,
                                      tokens.type families, radius modes,
                                      motion band, voice-facts casing,
                                      signatures — REPLACE directive values,
                                      dissent recorded
  brand.yaml overrides[section]       level 4 (token-schema `brand.overrides`)
  style×section override              level 3 (overrides/overrides.yaml)
  style directive                     level 2 (styles/directives.yaml, projected)
  section default                     level 1 (sections/catalog.yaml)
```

Merge semantics (resolution-model.md, kept verbatim): scalars replace, dicts
deep-merge per key, lists take tagged ops (`$replace`/`$append`/`$remove`,
bare array = replace). Adaptation: unknown `$` tags RAISE
(`StyleResolutionError`), never parse as keys.

Layout resolution (§4.3 adaptations — the authored algorithm's step-5 recompute
made override layout picks dead code):

- an explicit `layout:` at override/brand level WINS if it is in the section's
  `layouts`; if not, the resolver REJECTS LOUDLY — never a silent degrade;
- otherwise the first `layoutBias` entry present in the section's `layouts`
  wins, else `defaultLayout`;
- the two dangling bias ids (`grid-aligned`, `asymmetric` — disciplines, not
  layouts) translate through `DANGLING_BIAS_TRANSLATION` into layout-discipline
  notes so the style's intent survives;
- data repair (prescribed §4.3): `pricing.layouts` and `testimonial.layouts`
  extended with `list-rows` so both brutalist overrides resolve as authored.

Two-class invariants (§4.1): `classify_invariant` splits every catalog
invariant into **physics-class** (delegates to the existing gate id — AS-59,
AS-01/AS-22, AS-32/AS-51, AS-40, AS-50/container-law; names, never
reimplementations) and **genre-class** (soft default, advisory; brand evidence
may override with provenance). The resolver emits the classification; gates
stay the only enforcement.

Zero-signal axes (§5): `motion: subtle` (51/51 directives) and
`scaleRatio: 1.25` (49/51) are filler and project UNSET; newspaper (1.2) and
editorial-magazine (1.333) keep their genuine ratios.

The resolver is pure data-in/data-out (`load_library()` /
`load_brand_bundle()` own the I/O) and consumed by NOTHING in the render or
gate path (test-pinned): its only consumer is the generation prompt.

## 2. Prompt injection — `generate_composition.build_prompt`

Two clearly-delimited, independently-gated blocks:

### 2a. `[[PASS3-FACTS:BEGIN]] … [[PASS3-FACTS:END]]` (automatic, per brand)

Assembled by `pass1_facts_block(doc, brand_dir)` in the system prompt directly
after the brand-facts section:

| injected | source artifact | speaks as |
|---|---|---|
| derived type/space/radius/motion rungs | `style-scale.yaml` (followsScale blocks only) | the ALLOWED geometry vocabulary for novel magnitudes (scale_adherence audits the same ladder) |
| brand signatures (mode/id/kind/claim) | `brand.yaml signatures:` (§4.7) | always/never composition constraints (signature_check verifies) |
| voice budgets (sentence caps, exclamation ban, casing, banned lexicon, tone) | `voice-facts.yaml` (§4.8) | copy constraints (voice gate audits) |

Fact-gated PER ARTIFACT; a brand carrying none keeps the prompt byte-identical
to the pre-pass-3 assembly (test-pinned structurally: with-artifacts prompt
minus the block == without-artifacts prompt).

### 2b. `[[PASS3-STYLE:BEGIN]] … [[PASS3-STYLE:END]]` (caller-resolved)

`style_resolver.render_style_directive_block(style, resolutions, library)`
rendered by the CALLER (e.g. the style-bakeoff lane) and passed through
`generate_composition(..., style_directives=...)` /
`build_prompt(..., style_directives=...)` — the same fact-gated byte-identity
contract as `hero_candidates`. Content: the style's constraint posture,
signature moves, per-section layout guidance (primitive pick + §3.2
composition.v1 archetype hint + soft defaults), and the brand-evidence
dissents (directive value → brand fact WINS, provenance named). The block
STATES its own precedence: it never outranks brand facts, neverDo, or gates.

## 3. What injection is NOT

- NOT physics: renderers and gates are untouched; a resolution that would need
  a renderer change to take effect is logged as a follow-up and shaped via
  prompt only.
- NOT a corrector on extracted brands: genre-mean directive values lose to
  brand facts by construction (§4.2 ordering + the dissent ledger).
- NOT graduation: styles remain `unvalidated seed` until their bakeoff
  (INTEGRATION-PLAN stage C protocol); pass 3 runs the FIRST 3-style bakeoff
  and stops.

## 4. Tests

`brand_pipeline/tests/test_pass3_style_resolver.py` (39) — merge-semantics
table, loading guards (counts, string-typed axes, boolean-axis raise), golden
resolutions (swiss×feature-trio, brutalist×pricing/testimonial repairs,
editorial-magazine×hero 1.333, bias rerank, dangling-bias translation,
default fall-through), invariant classes over the whole catalog, loud
rejection fixtures, §4.2 brand merge with dissents + empty-bundle identity +
poor-fit refusal, 21×51 all-pairs smoke, directive-block rendering.

`brand_pipeline/tests/test_pass3_prompt_injection.py` (16) — facts-block
presence with real fact strings (both brands), byte-stability, graceful
degradation (sentinel absence + purely-additive strip proof + per-artifact
partial gating), style-directives absence/presence/additive proofs, fence
proof (no renderer/gate module imports the resolver; replica never sees the
block).
