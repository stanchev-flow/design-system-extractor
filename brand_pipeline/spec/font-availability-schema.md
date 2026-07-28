# Typography availability schema (`font-availability.v1`)

A declared font family is a claim. Whether it *renders* is a separate fact, and until
this schema existed nothing recorded it: a brand could declare a family, ship no
`@font-face` and no webfont link, and the page would quietly render a generic with no
artifact saying so. Everything below exists to make that outcome impossible to reach
silently.

Producer: `tools/extract/harvest_font_faces.py` (reads the `@font-face` rows
`tools/extract/mine_css.py` already writes into `evidence/pages/*/css-rules.json`).
Consumer of the same decision at render time: `brand_pipeline/tokens_css.py`
(`deliverable_families`, `substitution_map`, `typography_delivery`), whose output is
embedded in every render's `tokens.manifest.json` under `typographyDelivery`.

## The three delivery outcomes

Every declared family resolves to exactly one of these. There is no fourth, and none of
them is "it probably works":

| `status` | meaning | what makes it render |
| --- | --- | --- |
| `self-hosted` | the brand ships the face itself | `selfHostedFonts` registry + files under `<brand-dir>/assets/fonts/`; composers emit `@font-face` and copy the files next to the render |
| `proxy-substituted` | a loadable stand-in renders in its place | a webfont in the loadable catalog, either an authored `renderProxy` or the generic's default |
| `unavailable` | knowingly not delivered — a named gap | nothing; recorded so the gap is reviewable instead of invisible |

`unavailable` is a legitimate end state, not a failure. Most retail webfonts are
licensed to a single domain, so a public repository frequently *may not* redistribute
the face a capture reveals. Recording the gap is the honest resolution; quietly
rendering a generic is not.

Three rules decide which row a family gets, and each of them is read off what the brand
actually emits rather than recomputed beside it:

1. **A declared family that is itself in the loadable webfont catalog is delivered as
   itself** (`proxySource: declared`). Composers link the declared family in preference
   to any stand-in, so naming a substitute here would describe a font the page never
   uses.
2. **A substitute counts only where it lands ahead of the declaration's own fallbacks.**
   A member sitting behind a locally installed face is never reached, so it is not a
   delivery and the row does not claim one.
3. **A registry entry is a declaration; only files on disk are a delivery.** A family
   registered in `selfHostedFonts` whose files were never captured is reported against
   the disk, not the registry — `proxy-substituted` when the stack still carries a
   stand-in ahead of its fallbacks, `unavailable` when it does not. The registry is
   still what the *emitters* read (a stack that disagreed with the webfont links beside
   it would name a face nothing loads), which is exactly why the discrepancy has to be
   reported rather than silently corrected in one emitter.

Known limit: composers resolve their webfont links from the primary display and body
roles only. A family declared exclusively by some other role can therefore be recorded
as `proxy-substituted` while its stand-in is not among the linked families. Widening
the link set is a composer-side change and is not made here.

## What the harvester writes

Both documents land beside the evidence that produced them.

### `font-faces.json`

Raw observation, one row per `@font-face` seen (deduped across pages that share a
stylesheet):

```json
{ "schemaVersion": "font-availability.v1",
  "faces": [
    { "family": "Example Sans", "weight": "500", "style": "normal",
      "display": "swap", "unicodeRange": null,
      "sources": [ { "kind": "remote", "url": "https://cdn.example/…woff2",
                     "host": "cdn.example", "format": "woff2" } ],
      "seenIn": ["home", "site.css"] } ] }
```

`kind` is one of `remote` (an absolute URL — recorded as provenance, never fetched),
`relative` (a path beside the stylesheet, so the capture may already hold the bytes) or
`data` (the face is inlined in the stylesheet; icon fonts usually are, and `url` is
truncated because the payload is not evidence anyone reads).

### `font-availability.json`

`observed` collapses those rows to one entry per family (weights, styles, source kinds,
hosts, discovered URLs, `licenseHint`, `bytesInline`). `declared` is present only when a
`--brand-dir` is supplied and carries the delivery decision per declared family value,
annotated with the capture evidence:

```json
{ "family": "Example Sans", "declared": "'Example Sans', Fallback, sans-serif",
  "roles": ["body", "control-text"], "generic": "sans-serif",
  "selfHosted": false, "status": "proxy-substituted",
  "proxy": "…", "proxySource": "generic-default",
  "capturedFontFace": true, "capturedUrls": ["https://…"],
  "licenseHint": null }
```

`summary.discoverableButNotVendored` is the interesting list: families whose real files
were located in the capture but which the project does not ship. That is precisely the
set where a licensing decision is owed.

## Licensing evidence, and its limits

`licenseHint` is only ever set from evidence the harvester can actually support: the
serving host. A face served from a host that exclusively distributes openly licensed
webfonts is positive evidence of redistributability. Every other host yields `null`,
which means *unknown* — never "not redistributable". The harvester downloads nothing and
makes no licensing judgement it cannot back up; adopting a face is a human decision.

## Authoring: `fontAvailability:` in brand.yaml

`--emit-brand-snippet` writes a `fontAvailability:` block to paste into `brand.yaml`. It
is a record, not a switch — the render-time decision is derived from `selfHostedFonts`
and `renderProxy`, so the block documents *why* a family is substituted or missing and
survives re-extraction as the reviewed answer.

```yaml
fontAvailability:
  - family: "Example Serif"
    status: proxy-substituted
    substitutedBy: "…"
    capturedFontFace: true
    roles: [display-hero, h1, h2]
    # discovered (not fetched): https://cdn.example/…woff2
    licenseHint: null
```

To promote a family from `proxy-substituted` to `self-hosted`, place the face files
under `<brand-dir>/assets/fonts/` and register them in `selfHostedFonts:` (see
`brand-schema.md`). Do that only for faces the project is licensed to redistribute.

## Where the substitution is inserted, and why it matters

When a declared face is undeliverable, the substitute is inserted **directly after the
primary family**, ahead of the declaration's own fallback members — not appended at the
end. A capture's fallback chain is usually made of locally installed system faces, so a
substitute placed behind them would resolve on no machine and the family would still
render as a foreign face. A family also gets **one** substitute brand-wide
(`substitution_map`), because captures routinely declare the same family with
inconsistent trailing generics and a per-declaration choice would render one brand
family in two genres on the same page.

## Suggested validator row (not yet implemented)

`tools/extract/validate_brand_evidence.py` should fail, or at minimum warn, when a
declared `tokens.type` family is neither self-hosted nor covered by a loadable proxy and
carries no recorded `fontAvailability` entry — i.e. `status: unavailable` with no
authored acknowledgement. The check is a pure function of `typography_delivery(doc,
brand_dir)`: any row whose status is `unavailable` and whose family is absent from
`fontAvailability` is an undisclosed typography gap.
