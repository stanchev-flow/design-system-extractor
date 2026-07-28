# Brand-signal composition + retire shadcn defaults (2026-07-28)

## Intent

Stop HubSpot-era / SaaS globals from homogenizing every brand. Drive composition from measured brand signals (layouts → slots → components). Fresh composition only when inventing new sections. Framework/shadcn path off by default.

## Source changes

- `styles/composition-rules.md` — `section_select_and_order: reuse-captured-order-invent-freely`; freedom envelope scoped to invented sections.
- `run_pipeline.py` — Fresh Composition Contract + site-gen layout freshness: preserve measured inventories; invent only net-new sections; no invented proof/stats.
- `brand_pipeline/compose_page.py` — removed unconditional `#sec-0 { min-height: 100cqh }`.
- `brand_pipeline/compose_section.py` — hero scaffold content-sized; removed overlay `90svh` default; banded media height auto.
- `brand_pipeline/generate_composition.py` — wireframe rules no longer force visual anchors/proof; injects `compositionSignals` prompt block.
- `brand_pipeline/section_wireframe.py` + `composition_lint.py` — `proofRequired` brand-gated; text-forward sections legal; consecutive sparse ban only when brand sets `maxConsecutiveTextOnly`.
- `brand_pipeline/compose_from_composition.py` — `_has_brand_anatomy` / `_brand_wants_stat_device`; slot pass-through for measured anatomy; numeric list→stat only when brand licenses.
- `brand_pipeline/composition_signals.py` — **new** extractor + prompt + section stamping.
- `config.default.yaml` — `framework-generation-enabled: false`.
- `website-gen-framework-prompt.md` — token/headless contract; no shadcn-as-shipped.
- `src/screenshot_to_template/chrome_codegen.py` — native token chrome; no `@/components/ui` Button/Section requirement.
- `handoff/scaffold/framework-site/src/components/ui/{card,section}.tsx` — strip default shadow/radius/py-24 SaaS skin.
- Spec/contracts language updated away from “NOW = Tailwind/shadcn”.

## Tests

- `brand_pipeline/tests/test_brand_signal_composition.py` (new)
- Updated `test_section_wireframe.py`, `test_composer_multicolumn.py`

```bash
./venv/bin/python -m unittest brand_pipeline.tests.test_brand_signal_composition \
  brand_pipeline.tests.test_section_wireframe \
  brand_pipeline.tests.test_composer_multicolumn
```

## Follow-ups

- Optional Radix headless wrappers for interactive chrome (opt-in framework only).
- Persist `compositionSignals` onto brand.yaml at extract time (currently derived on the fly from `layouts[]`).

## Verification run — greenhouse-4 (2026-07-28)

- Built `runs/greenhouse-4/` from greenhouse-v2 facts; harness + replica under brand-signal path.
- Fixed `composition_signals._slots_of` to enrich slot contracts from `blockMapping` (Greenhouse stats).
- Harness quality ok; replica overall 0.7496; viewer regenerated.
