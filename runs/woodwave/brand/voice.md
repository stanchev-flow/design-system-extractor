# voice.md — Woodwave Gallery

## 1. Voice summary

**Quiet, exacting, sensory, patient, assured.**

Woodwave speaks like the gallery itself: spare and unhurried, with absolute confidence and no salesmanship. Sentences are short and declarative; the longest thoughts are about light, wood, and time. The brand describes rather than persuades — the building and the collection carry the argument. We say "the gallery", "the collection", "the building" more than "we"; when "we" appears it is institutional and modest. Visitors are addressed directly only at the practical moments (visit, tickets, newsletter), always plainly. Reading level: accessible literary (roughly grade 8–9) — simple vocabulary arranged carefully. Person: mostly neutral/third person; "we" sparingly; "you" only in conversion and visit copy.

## 2. Vocabulary

**Use:** the collection · the building · timber · grain · light · quiet · held · housed · since 1941 · room · works · era · craft · curve · presence · standing · visit

**Avoid:** unlock · seamless · supercharge · world-class · immersive experience · explore now · don't miss · curated just for you · iconic · stunning · vibrant · journey (as metaphor) · elevate · discover (as CTA) · cutting-edge

## 3. Casing & punctuation rules

| role | rule |
|---|---|
| Display hero / H1 / H2 / H3 | Written in natural case; **render: uppercase** via type role. No terminal punctuation. No exclamation marks anywhere on the site. |
| Ghost watermark | Single word or year pair, natural case, **render: uppercase**, `aria-hidden`. Year pairs use an en dash or slash exactly as specified per section. |
| Eyebrow / caption | Natural case, **render: uppercase**. Captions ≤ 18 characters, no period. Eyebrows may use a leading index ("01 — About") only if applied consistently; default is plain label. |
| Body | Sentence case. Periods, commas, en dashes only. No semicolons, no ellipses, no bold/italic emphasis. |
| Control text (nav, actions, submit, social) | Natural case, **render: uppercase**. Arrow actions: label + trailing `→`, ~8px gap, never a sentence, never punctuation. Multi-link runs separated by ` / ` with spaces. |
| Counter | Numerals + slash, e.g. `1/6`. Static label only. |
| Footer sitemap | Natural case, **render: uppercase**, ` / ` separated, didone serif — bookend only. |

## 4. Length budgets

| role | max chars/line | max lines | notes |
|---|---|---|---|
| Display hero | 16 | 2 | Hero title; may overlap collage top edge; accent color permitted here only |
| H1 | 28 | 3 | Multi-line by design; break with `\n` as marked |
| H2 | 32 | 2 | Paired with eyebrow above |
| H3 (panel title) | 22 | 1 | Inside cream panels only |
| Ghost watermark | 10 | 1 | One word or year pair per section |
| Eyebrow | 24 | 1 | Metadata register, never a heading |
| Caption | 18 | 1 | Margin-set, beside media, muted |
| Body | 52 | 6 | Narrow measure (~1/3 container); one paragraph per module |
| Arrow action | 16 | 1 | Imperative or noun label + → |
| Counter | 5 | 1 | e.g. 1/6 |
| Footer sitemap link | 12 per link | — | Four links max in run |

## 5. Section copy

### Header (nav)

- action: slash-separated control-text run — `About / Gallery / Exhibition / Visit` (hrefs: #about, #gallery, #exhibition, #visit)
- notes: render uppercase; logo wordmark "Woodwave" left, accent yellow on dark surfaces only.

### Hero (opening bookend, inverse)

- heading: `Woodwave\nGallery`
- body (sub-line, optional, control/eyebrow register): `Contemporary art in a landmark timber hall — since 1941`
- caption(s): `Main hall, east light` · `Timber vault, 1941`
- notes: heading is `type/display-hero`, render uppercase, may take `text/accent`, overlaps collage top edge. Sub-line renders uppercase if set in eyebrow role. Captions sit in margin beside collage tiles, never on the photos.

### About / manifesto (cream collage)

- ghost watermark: `About` (render uppercase, aria-hidden)
- eyebrow: `About the gallery`
- heading (H1): `The building\nis the first\nwork on view` (render uppercase)
- body: `Woodwave occupies a timber hall raised in 1941 and kept close to its original state. The grain of the walls, the curve of the vault, the slow movement of daylight — the architecture sets the terms, and the collection answers them.`
- caption(s): `Vault detail` · `North gallery`
- action: `Our story →` (href: #about)
- notes: heading left-aligned, breaks as marked. Body sits in offset narrow column beside media per collage grammar.

### Gallery interior showcase (counter row + full-bleed band)

- eyebrow: `Inside the hall` (far left)
- counter: `1/6` (far right, same row)
- caption: `Central nave` (below band, margin-set)
- notes: full-bleed photograph, no overlay text, no controls. Counter is a static index label — do not add slider UI.

### Mission statement (cream, left-anchored statement)

- eyebrow: `What we hold`
- heading (H1): `Space as\na muse` (render uppercase)
- body: `We collect work that listens to its room. From the late twentieth century to the present day, the holdings favour pieces shaped by material, scale and place — art that stands differently here than anywhere else.`
- action: `The collection →` (href: #gallery)
- notes: alternate horizontal anchor from the previous module per stagger rule.

### Heritage / collection timeline (cream, ghost numerals)

- ghost watermark: `1941–2023` (render uppercase numerals, aria-hidden)
- eyebrow: `Eight decades`
- heading (H2): `A collection\nbuilt slowly` (render uppercase)
- body: `The first works entered the hall the year it opened. Since then the collection has grown by patience rather than appetite — a few pieces each era, chosen for how they hold the room.`
- caption(s): `Acquisition, 1974` · `New wing, 2023`
- notes: ghost numerals span near-full section width behind heading and media; foreground overlaps deliberately.

### Curator quote with portrait (cream collage module)

- eyebrow: `From the curator`
- heading (H2, used as the quote): `“A room this\nhonest forgives\nnothing”` (render uppercase)
- body: `Elin Marsh, curator since 2011, on hanging work in the timber hall. Every placement is tested against the light at three hours of the day before it stays.`
- caption: `Elin Marsh` (beside portrait)
- notes: quote set in H2 serif with breaks as marked; quotation marks kept. Portrait is a hard-edged rectangle, caption in margin.

### Visit info (inverse band: split + map overlay)

- eyebrow: `Plan your visit`
- heading (H2): `Come stand\nin the hall` (render uppercase, `text/on-inverse`)

**Panel — Ticket Prices (surface/panel):**
- H3: `Ticket prices` (render uppercase)
- ruled rows (label left, value/action right):
  - `Adults` — `12 €`
  - `Reduced` — `8 €`
  - `Under 18` — `Free`
- action: `Buy tickets →` (href: #tickets), right-aligned in final ruled row, dark on panel per rule 4

**Panel — Visit panel on map (surface/panel, overlapping map edges):**
- H3: `Hours & address` (render uppercase)
- body rows:
  - `Tue–Sun, 10–18`
  - `Mondays closed`
  - `14 Harbour Lane, Aldermoor`
- action: `Get directions →` (href hint: external map link)
- caption (beside map rectangle): `Harbour quarter`

- notes: panels keep panel coloring (dark text, dark arrows) regardless of inverse parent. Map is the desaturated static graphic with pin. No accent color anywhere in this band except none — accent is reserved for logo and hero only.

### Newsletter subscribe (cream, centered stack)

- eyebrow: `Stay in touch`
- heading (H1): `Hear when\nthe walls change` (render uppercase)
- body: `One letter a season — new works, new hours, nothing else.`
- form: placeholder `Your email` (render uppercase) · submit `Subscribe →` (inline text submit, shared hairline, baseline-aligned)
- notes: centered narrow column (~50%) — one of only two sanctioned centered stacks.

### Footer (closing bookend, inverse-strong, centered stack)

- logo: `Woodwave` (accent yellow, render uppercase)
- sitemap run (footer-sitemap-link, render uppercase): `About / Gallery / Exhibition / Visit` (hrefs: #about, #gallery, #exhibition, #visit)
- social row (control text, render uppercase): `Instagram / Newsletter / Press` (hrefs: external, #newsletter, mailto hint)
- legal strip (eyebrow register): `© 2024 Woodwave Gallery — 14 Harbour Lane, Aldermoor`
- notes: serif display links exist here only. No arrows in the slash runs. Hard cut from cream above — no divider.
