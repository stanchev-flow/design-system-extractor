# styles/ — changelog

## 2026-07-14 — composition-rules.md split: normative core vs extended edition

**Why**: `generate_composition.build_prompt` injected the ENTIRE file (front-matter
registry + 305 lines of prose, ~27.4KB ≈ ~6.8k tokens) into every generation prompt.
Most of that was rationale and worked detail, which diluted rule salience and paid a
token cost on every call.

**What changed**:

- `styles/composition-rules.md` is now three layers in one file:
  1. **YAML front-matter** — the on-disk registry (documentation; NOT injected, NOT
     machine-parsed at runtime).
  2. **Normative core** (`# Composition rules (normative core)` → the
     `COMPOSITION-CORE:END` sentinel) — the ONLY prompt payload: every law and the
     complete working vocabulary (all 8 archetypes, all 17 treatment kinds, placement/
     registration fields, tiers, anchors, legality machinery) at ~9.7KB ≈ ~2.4k tokens.
  3. **Extended edition** (below the sentinel) — the full original prose with
     rationale, device notes, and the assembly chapter; on-disk reference only.
- `brand_pipeline/generate_composition.py`: new `GRAMMAR_CORE_SENTINEL` +
  `grammar_core()` (strips front-matter via `styles.parse_front_matter`, cuts at the
  sentinel, degrades safely when either marker is absent); `build_prompt` injects the
  core only.
- New golden test `brand_pipeline/tests/test_grammar_core.py` (18 tests): core budget
  (≤13k chars — headroom over the measured 9.7k, far under the old 27.4KB), core
  vocabulary completeness against `layout_library.TREATMENT_KINDS` /
  `ARCHETYPE_COMPOSERS` / the schema archetype enum, front-matter registry consistency
  with `OFF_GRID_TREATMENTS`, end-to-end prompt assembly uses the core and never the
  registry/extended edition, graceful degradation without markers.

**Effect**: generation prompt shrinks ~17.7KB (~4.4k tokens) per call —
hubspot-v2 assembles at ~42.3KB (was ~60KB), remote at ~43.6KB. Prompt content is
unchanged in substance: same laws, same vocabulary, compressed prose.

**Verification**: full suite 1365 passed (`pytest brand_pipeline/tests/` with real
Playwright browser cache; the `staged_test_quality_steals.py` scaffold excluded as
always). No renderer/gate/lane changes — replica scores unaffected by construction
(prompt-shaping only).

**Editing rule going forward**: new laws go in the CORE (short, normative); rationale
and case detail go in the extended edition below the sentinel; keep the front-matter
registry consistent — the golden test enforces budget + completeness.
