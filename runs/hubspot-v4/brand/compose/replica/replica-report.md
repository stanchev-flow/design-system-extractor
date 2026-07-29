# Replica gate — rebuild-as-proof report

- brand: **HubSpot**
- source screenshot: `screenshots/hubspot-v3/hubspot-fullpage.png`
- replica page: `index.html` → `replica-fullpage.png` (doc 7283px vs source 6986px)
- metric: score = 0.5·structure + 0.3·pixel + 0.2·height (Pillow RGB MAE; structure at 64px, pixel at 720px)
- `width` = content-span ratio (diagnostic, not in score): detected content width fraction of each band, min/max ratio — catches centered stacks collapsed to a fraction of the source's content width, which the averaged pixel metric barely registers
- **overall score (height-weighted): 0.904**

| band | source section | score | structure | pixel | height | width | src h | replica h | crops |
|---|---|---|---|---|---|---|---|---|---|
| page-nav | navbar (chrome header) | **0.983** | 0.983 | 0.973 | 1.000 | 0.979 | 128px | 128px | [side-by-side](diff/page-nav.png) |
| sec-0 | full-bleed-photo-hero — Where go-to-market teams go to 
               grow scale close retain grow | **0.924** | 0.910 | 0.898 | 1.000 | 1.000 | 772px | 772px | [side-by-side](diff/sec-0.png) |
| sec-1 | centered-heading-over-logo-row — 299,000+ customers in over 135 countries grow their businesses with HubSpot. | **0.891** | 0.976 | 0.969 | 0.560 | 0.904 | 261px | 466px | [side-by-side](diff/sec-1.png) |
| sec-2 | copy-left-illustration-right-carousel — HubSpot's Agentic Customer Platform | **0.875** | 0.933 | 0.926 | 0.655 | 0.894 | 742px | 486px | [side-by-side](diff/sec-2.png) |
| sec-3 | sticky-copy-with-card-grid — Growing a business is hard. HubSpot makes it easier. | **0.872** | 0.852 | 0.844 | 0.961 | 0.967 | 1600px | 1665px | [side-by-side](diff/sec-3.png) |
| sec-4 | headrail-split-with-card-carousel — Built-in AI agents that work for you 24/7. | **0.878** | 0.887 | 0.873 | 0.862 | 0.971 | 992px | 855px | [side-by-side](diff/sec-4.png) |
| sec-5 | copy-left-logo-collage-inset — Works with the tools you already use. 2,000+ integrations. | **0.950** | 0.949 | 0.938 | 0.971 | 0.987 | 330px | 340px | [side-by-side](diff/sec-5.png) |
| sec-6 | headrail-two-col-header — Remarkable results for every size business. | **0.924** | 0.969 | 0.957 | 0.764 | 1.000 | 240px | 314px | [side-by-side](diff/sec-6.png) |
| sec-7 | tabbed-testimonial-with-stats — section-7 | **0.941** | 0.936 | 0.922 | 0.982 | 0.974 | 714px | 701px | [side-by-side](diff/sec-7.png) |
| sec-8 | heading-left-award-badges-right — Voted #1 in 526 G2 Reports | **0.899** | 0.958 | 0.948 | 0.679 | 0.710 | 216px | 318px | [side-by-side](diff/sec-8.png) |
| sec-9 | dark-band-cta — Make impossible growth feel impossibly easy, with HubSpot | **0.901** | 0.945 | 0.928 | 0.751 | 0.571 | 335px | 446px | [side-by-side](diff/sec-9.png) |
| footer | footer (closing bookend) | **0.949** | 0.983 | 0.974 | 0.828 | 0.971 | 656px | 792px | [side-by-side](diff/footer.png) |

## Multi-viewport replica gate (Phase 5)

Desktop **fidelity** (the `overall` above) is scored against the source full-page screenshot, captured at the primary viewport only. The other viewports have no source shot to diff against, so they record a **responsiveness-health** number instead (1.0 = no horizontal overflow, every band present, reflow intact) — responsiveness is *verified*, not a faked cross-viewport SSIM.

| viewport | role | health | overflow px | bands | hero h | footer cols | doc h | shot |
|---|---|---|---|---|---|---|---|---|
| 1440 | primary (fidelity) | 1.0 | 0 | 12 | 772px | 5 | 7283px | `replica-fullpage-1440.png` |
| 1920 | responsiveness | 1.0 | 0 | 12 | 952px | 5 | 7475px | `replica-fullpage-1920.png` |
| 960 | responsiveness | 1.0 | 0 | 12 | 664px | 5 | 7465px | `replica-fullpage-960.png` |
| 375 | responsiveness | 0.8933 | 20 (`cs-edgecut`) | 12 | 756px | 1 | 10807px | `replica-fullpage-375.png` |

![strip](diff/strip.png)

## Structural gate

Signals the averaged-MAE score cannot carry: whether the rebuild used the same number of bands, the same kind of layout, and the same content span as the source.

| signal | value | floor | ok | detail |
| --- | --- | --- | --- | --- |
| bandCountAgreement | 1.0 | 1.0 | yes | every measured content band is rebuilt by exactly one authored section |
| archetypeFamilyAgreement | 1.0 | 1.0 | yes | composed layout families honor the measured track multiplicity of every band |
| contentSpanFidelity | 0.9367 | 0.8 | yes | rebuilt content occupies the measured share of each band |

**Structural gate: pass**

## Renderer-gap punch list

1. **full-bleed-photo-hero — composite hero art** (score 0.924): composite hero art — the source layers an illustration with floating product-UI chips; the composer binds one asset per media slot (no multi-layer collage of tagged crops)
2. **heading-left-award-badges-right — content width diverges** (score 0.899): content span 0.47 of band vs source 0.67 (width fidelity 0.71) — check hug/measure collapse or over-wide container
3. **dark-band-cta — content width diverges** (score 0.901): content span 0.40 of band vs source 0.71 (width fidelity 0.57) — check hug/measure collapse or over-wide container
4. **navbar — mega-menu open panels** (score 0.983): the brand declares mega-menu columns; the replica (and the source shot) render the closed bar only — open-panel fidelity is unexercised by this gate

Diagnostic, not blocking — re-run with `--fail-under <score>` to gate.
