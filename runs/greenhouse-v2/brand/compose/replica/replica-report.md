# Replica gate — rebuild-as-proof report

- brand: **Greenhouse**
- source screenshot: `screenshots/greenhouse-v2/home/home-fullpage.png`
- replica page: `index.html` → `replica-fullpage.png` (doc 6006px vs source 5031px)
- metric: score = 0.5·structure + 0.3·pixel + 0.2·height (Pillow RGB MAE; structure at 64px, pixel at 720px)
- `width` = content-span ratio (diagnostic, not in score): detected content width fraction of each band, min/max ratio — catches centered stacks collapsed to a fraction of the source's content width, which the averaged pixel metric barely registers
- **overall score (height-weighted): 0.768**

| band | source section | score | structure | pixel | height | width | src h | replica h | crops |
|---|---|---|---|---|---|---|---|---|---|
| page-nav | navbar (chrome header) | **0.000** | 0.000 | 0.000 | 0.000 | — | 0px | 80px | — |
| sec-0 | hero — The only hiring platform you’ll | **0.857** | 0.876 | 0.863 | 0.802 | 0.713 | 900px | 1122px | [side-by-side](diff/sec-0.png) |
| sec-1 | featureGrid — Greenhouse introduces Voice AI following our acquisition of Ezra AI Labs, bringing conversational AI to the hiring proce | **0.205** | 0.223 | 0.218 | 0.142 | 0.772 | 132px | 929px | [side-by-side](diff/sec-1.png) |
| sec-2 | logos — Real Talent | **0.806** | 0.822 | 0.818 | 0.749 | 0.720 | 634px | 475px | [side-by-side](diff/sec-2.png) |
| sec-3 | comparison — Great companies hire with Greenhouse | **0.841** | 0.878 | 0.872 | 0.705 | 0.818 | 786px | 1115px | [side-by-side](diff/sec-3.png) |
| sec-4 | stats — The best teams start with hiring – and the best hiring starts with Greenhouse | **0.783** | 0.874 | 0.854 | 0.446 | 0.887 | 905px | 404px | [side-by-side](diff/sec-4.png) |
| sec-5 | testimonial — Everything you need to get better at hiring | **0.300** | 0.158 | 0.156 | 0.870 | 0.494 | 630px | 548px | [side-by-side](diff/sec-5.png) |
| footer | footer (closing bookend) | **0.954** | 0.972 | 0.965 | 0.895 | 0.948 | 1043px | 934px | [side-by-side](diff/footer.png) |

## Multi-viewport replica gate (Phase 5)

Desktop **fidelity** (the `overall` above) is scored against the source full-page screenshot, captured at the primary viewport only. The other viewports have no source shot to diff against, so they record a **responsiveness-health** number instead (1.0 = no horizontal overflow, every band present, reflow intact) — responsiveness is *verified*, not a faked cross-viewport SSIM.

| viewport | role | health | overflow px | bands | hero h | footer cols | doc h | shot |
|---|---|---|---|---|---|---|---|---|
| 1440 | primary (fidelity) | 1.0 | 0 | 9 | 1122px | 5 | 6006px | `replica-fullpage-1440.png` |
| 1920 | responsiveness | 1.0 | 0 | 9 | 1156px | 5 | 6060px | `replica-fullpage-1920.png` |
| 960 | responsiveness | 0.6167 | 184 (`c-foot-cols`) | 9 | 1562px | 6 | 6608px | `replica-fullpage-960.png` |
| 375 | responsiveness | 0.5 | 669 (`c-foot-cols`) | 9 | 1067px | 6 | 5750px | `replica-fullpage-375.png` |

![strip](diff/strip.png)

## Structural gate

Signals the averaged-MAE score cannot carry: whether the rebuild used the same number of bands, the same kind of layout, and the same content span as the source.

| signal | value | floor | ok | detail |
| --- | --- | --- | --- | --- |
| bandCountAgreement | 1.0 | 1.0 | yes | every measured content band is rebuilt by exactly one authored section |
| archetypeFamilyAgreement | 1.0 | 1.0 | yes | composed layout families honor the measured track multiplicity of every band |
| contentSpanFidelity | 0.7845 | 0.8 | **no** | rebuilt content spans a different share of the band than the source — a collapsed or over-wide container leaves most of the band as matching background, so the averaged metric barely registers it |

**Structural gate: FAIL**

## Renderer-gap punch list

1. **hero — composite hero art** (score 0.857): composite hero art — the source layers an illustration with floating product-UI chips; the composer binds one asset per media slot (no multi-layer collage of tagged crops)
2. **hero — content width diverges** (score 0.857): content span 0.71 of band vs source 1.00 (width fidelity 0.71) — check hug/measure collapse or over-wide container
3. **featureGrid — fidelity below threshold** (score 0.205): band renders taller (929px vs 132px); coarse layout structure diverges (module geometry / art direction); surface color / texture diverges
4. **logos — fidelity below threshold** (score 0.806): band renders shorter (475px vs 634px)
5. **comparison — fidelity below threshold** (score 0.841): band renders taller (1115px vs 786px)
6. **stats — fidelity below threshold** (score 0.783): band renders shorter (404px vs 905px)
7. **testimonial — content width diverges** (score 0.300): content span 0.42 of band vs source 0.85 (width fidelity 0.49) — check hug/measure collapse or over-wide container
8. **testimonial — fidelity below threshold** (score 0.300): coarse layout structure diverges (module geometry / art direction); surface color / texture diverges
9. **page — display font (Untitled Serif, Georgia, sans-serif)**: not self-hosted and not Google-loadable — headings render in the declared fallback stack; extract the woff2 files into assets/fonts/
10. **page — band census**: provenance anchoring unavailable (5/7 pairs resolved, 4 distinct) — falling back to positional band pairing
11. **page — band census**: source chrome census has no measured header band — the page nav is excluded from scoring by declaration (its source pixels sit inside the first content band); fix the measure stage to score it
12. **page — structural gate**: contentSpanFidelity: 0.7845 < floor 0.8 (rebuilt content spans a different share of the band than the source — a collapsed or over-wide container leaves most of the band as matching background, so the averaged metric barely registers it)

Diagnostic, not blocking — re-run with `--fail-under <score>` to gate.
