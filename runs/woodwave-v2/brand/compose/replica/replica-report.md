# Replica gate — rebuild-as-proof report

- brand: **WoodWave Gallery**
- source screenshot: `screenshots/woodwave-v2/woodwave-fullpage.png`
- replica page: `index.html` → `replica-fullpage.png` (doc 4757px vs source 12182px)
- metric: score = 0.5·structure + 0.3·pixel + 0.2·height (Pillow RGB MAE; structure at 64px, pixel at 720px)
- `width` = content-span ratio (diagnostic, not in score): detected content width fraction of each band, min/max ratio — catches centered stacks collapsed to a fraction of the source's content width, which the averaged pixel metric barely registers
- **overall score (height-weighted): 0.750**

| band | source section | score | structure | pixel | height | width | src h | replica h | crops |
|---|---|---|---|---|---|---|---|---|---|
| page-nav | navbar (chrome header) | **0.977** | 0.990 | 0.977 | 0.944 | 1.000 | 102px | 108px | [side-by-side](diff/page-nav.png) |
| sec-0 | hero — woodwavegallery | **0.781** | 0.894 | 0.880 | 0.351 | 0.944 | 1906px | 670px | [side-by-side](diff/sec-0.png) |
| sec-1 | about — about | **0.731** | 0.859 | 0.854 | 0.225 | 0.599 | 3985px | 896px | [side-by-side](diff/sec-1.png) |
| sec-2 | gallery-slider — gallery | **0.691** | 0.732 | 0.726 | 0.538 | 0.466 | 905px | 487px | [side-by-side](diff/sec-2.png) |
| sec-3 | founder-story — WoodWave Gallery is a tribute to decades of creative excellence, fostering the flourishing of art from the late 20th cen | **0.726** | 0.767 | 0.746 | 0.596 | 0.990 | 1620px | 965px | [side-by-side](diff/sec-3.png) |
| sec-4 | visit — visit | **0.681** | 0.760 | 0.755 | 0.375 | 1.000 | 2013px | 754px | [side-by-side](diff/sec-4.png) |
| sec-5 | newsletter — stay updated | **0.924** | 0.964 | 0.954 | 0.781 | 0.939 | 739px | 577px | [side-by-side](diff/sec-5.png) |
| footer | footer (closing bookend) | **0.843** | 0.980 | 0.980 | 0.296 | 0.465 | 1014px | 300px | [side-by-side](diff/footer.png) |

## Multi-viewport replica gate (Phase 5)

Desktop **fidelity** (the `overall` above) is scored against the source full-page screenshot, captured at the primary viewport only. The other viewports have no source shot to diff against, so they record a **responsiveness-health** number instead (1.0 = no horizontal overflow, every band present, reflow intact) — responsiveness is *verified*, not a faked cross-viewport SSIM.

| viewport | role | health | overflow px | bands | hero h | footer cols | doc h | shot |
|---|---|---|---|---|---|---|---|---|
| 1440 | primary (fidelity) | 1.0 | 0 | 8 | 670px | 0 | 4757px | `replica-fullpage-1440.png` |
| 1920 | responsiveness | 1.0 | 0 | 8 | 670px | 0 | 4757px | `replica-fullpage-1920.png` |
| 960 | responsiveness | 1.0 | 0 | 8 | 670px | 0 | 5340px | `replica-fullpage-960.png` |
| 375 | responsiveness | 1.0 | 0 | 8 | 812px | 0 | 6299px | `replica-fullpage-375.png` |

![strip](diff/strip.png)

## Structural gate

Signals the averaged-MAE score cannot carry: whether the rebuild used the same number of bands, the same kind of layout, and the same content span as the source.

| signal | value | floor | ok | detail |
| --- | --- | --- | --- | --- |
| bandCountAgreement | 1.0 | 1.0 | yes | every measured content band is rebuilt by exactly one authored section |
| archetypeFamilyAgreement | 1.0 | 1.0 | yes | composed layout families honor the measured track multiplicity of every band |
| contentSpanFidelity | 0.7708 | 0.8 | **no** | rebuilt content spans a different share of the band than the source — a collapsed or over-wide container leaves most of the band as matching background, so the averaged metric barely registers it |

**Structural gate: FAIL**

## Renderer-gap punch list

1. **hero — fidelity below threshold** (score 0.781): band renders shorter (670px vs 1906px)
2. **about — video static** (score 0.731): video static — the source embeds motion media; the composer renders a still
3. **about — content width diverges** (score 0.731): content span 0.55 of band vs source 0.91 (width fidelity 0.60) — check hug/measure collapse or over-wide container
4. **gallery-slider — carousel statics** (score 0.691): carousel statics — the source is an edge-cut sliding track (cards clipped at the viewport); the composer renders a contained grid
5. **gallery-slider — content width diverges** (score 0.691): content span 0.47 of band vs source 1.00 (width fidelity 0.47) — check hug/measure collapse or over-wide container
6. **founder-story — fidelity below threshold** (score 0.726): band renders shorter (965px vs 1620px); coarse layout structure diverges (module geometry / art direction)
7. **visit — video static** (score 0.681): video static — the source embeds motion media; the composer renders a still
8. **newsletter — video static** (score 0.924): video static — the source embeds motion media; the composer renders a still
9. **page — display font (Melodrama)**: not self-hosted and not Google-loadable — headings render in the declared fallback stack; extract the woff2 files into assets/fonts/
10. **page — structural gate**: contentSpanFidelity: 0.7708 < floor 0.8 (rebuilt content spans a different share of the band than the source — a collapsed or over-wide container leaves most of the band as matching background, so the averaged metric barely registers it)

Diagnostic, not blocking — re-run with `--fail-under <score>` to gate.
