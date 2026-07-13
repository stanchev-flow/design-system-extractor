# Interaction Contracts — WAI-ARIA APG-Grade Correctness for Composed Lanes

Status: v1 (baseline-measurement phase). This spec defines per-component-family
interaction contracts for the HTML/CSS lanes the composer emits. It is enforced by
`brand_pipeline/interaction_audit.py` (static + behavioral layers). In this phase the
auditor **measures and reports** — it does not gate builds (`--strict` exists for
future gate wiring).

Doctrine alignment: contracts are **brand-agnostic and palette-agnostic**. They
describe interaction semantics and platform behavior, never colors, section names, or
content. Component families are keyed to *structural signatures* of the renderer's
output (class shapes like `cs-nav-tab`, `details[name]` groups, `cs-marquee-half`),
which are reusable across brands.

Primary source: WAI-ARIA Authoring Practices Guide (APG) patterns.
Secondary: Base UI component behavior (base-ui.com). Tertiary: Radix Primitives docs.
Sources fetched 2026-07-10; per-family citations below.

Severity model:

- **REQUIRED** — hard fail. Violates the platform contract a keyboard or AT user
  depends on. These drive the remediation queue.
- **RECOMMENDED** — advisory. Improves semantics/robustness; absence is reported but
  does not (and will not, under `--strict`) fail the gate.

Layer split:

- **Static** — verifiable by parsing the emitted HTML/CSS (attributes, structure,
  media queries). Runs with no browser; used in unit tests.
- **Behavioral** — requires a real browser (Playwright, headless Chromium, `file://`).
  Verifies focus order, key handling, state changes, reduced-motion computed styles.

Check IDs are stable: `IC-<FAMILY>-<NN>`. The auditor reports
`pass / fail / advisory / skip` per lane x family x check (skip = family absent from
lane, with note).

---

## 1. `nav` — Disclosure navigation (mega-menu)

The sticky navbar's dropdown panels (chevron triggers opening mega-menu panels) are
**disclosures**, per the APG Disclosure pattern and its "Disclosure Navigation Menu"
example. They are NOT ARIA menus: the APG example states explicitly that site
navigation should not use `menu`/`menubar` roles — those roles promise complex
widget keyboard semantics (roving focus, first-letter navigation, interaction-mode
switching in screen readers) that site nav neither needs nor implements. **Applying
`role="menu"`/`menubar`/`menuitem` to site nav is an anti-pattern** and is checked as
a hard failure.

Sources:

- APG Disclosure pattern: https://www.w3.org/WAI/ARIA/apg/patterns/disclosure/
- APG Disclosure Navigation Menu example (incl. the "not a menu" warning and the
  Escape requirement tied to WCAG 2.1 SC 1.4.13):
  https://www.w3.org/WAI/ARIA/apg/patterns/disclosure/examples/disclosure-navigation/
- Base UI Navigation Menu (behavior: closes on `escape-key`, `focus-out`,
  `outside-press`; opens on `trigger-press` and `trigger-hover`):
  https://base-ui.com/react/components/navigation-menu
- Radix Navigation Menu (keyboard table: Space/Enter opens content; Esc closes open
  content and returns focus to the trigger):
  https://www.radix-ui.com/primitives/docs/components/navigation-menu

REQUIRED:

- **IC-NAV-01** (static) — A panel trigger is a `<button>`, or a link with a real
  destination (the "disclosure nav with top-level links" variant). A bare
  `<a href="">` / `<a href="#">` whose only job is opening the panel fails: Enter on
  it navigates/reloads instead of toggling, and it has link semantics with no target.
- **IC-NAV-02** (static) — The trigger carries `aria-expanded` reflecting panel state
  (`false` when closed, `true` when open). Without it, AT users cannot tell the
  collapsed control hides content.
- **IC-NAV-03** (static) — No `role="menu"`, `role="menubar"`, or `role="menuitem"`
  inside site navigation (anti-pattern; see above).
- **IC-NAV-06** (behavioral) — Tab reaches every top-level nav trigger and the nav
  utility controls (login link, language switcher) in document order.
- **IC-NAV-07** (behavioral) — Hover-open must have keyboard-open parity: keyboard
  focus on the trigger (or Enter/Space on it) opens the same panel that hover opens.
  A hover-only panel is invisible to keyboard users.
- **IC-NAV-08** (behavioral) — Escape closes an open panel while focus is inside it,
  and focus stays in the nav (does not fall to `<body>`). Required by WCAG 2.1
  SC 1.4.13 (Content on Hover or Focus) for hover/focus-triggered content.

RECOMMENDED:

- **IC-NAV-04** (static) — Trigger has `aria-controls` referencing the panel element
  id (APG lists this as the standard wiring; optional in the base pattern).
- **IC-NAV-05** (static) — No `role="button"` on `<a>` elements in nav chrome. Per the
  APG Button pattern, role must match behavior: `role="button"` promises Space
  activation, which anchors do not provide natively; prefer a real `<button>` or an
  honest link.

Static-vs-behavioral split: trigger element kind, `aria-expanded` presence, and role
anti-patterns are static; focus order, hover/keyboard parity, and Escape behavior are
behavioral (the current panels open via CSS `:hover`/`:focus-within` — only a browser
can observe that contract).

## 2. `lang` — Select-only dropdown (language switcher)

The language switcher is a **navigation choice among a small fixed set of locale
links**. A native-first implementation (`<details>` + `<summary>` + a list of links)
is acceptable and preferred over a scripted APG combobox/listbox: the APG's own
guidance ("No ARIA is better than Bad ARIA") favors native semantics where they carry
the interaction. The full select-only combobox pattern (role=combobox +
aria-activedescendant listbox) is the reference ceiling, not the minimum bar.

Minimum bar for ANY implementation (native or scripted):

Sources:

- APG Combobox pattern (select-only reference; Escape dismisses the popup):
  https://www.w3.org/WAI/ARIA/apg/patterns/combobox/
- APG Disclosure pattern (the native-first framing for show/hide):
  https://www.w3.org/WAI/ARIA/apg/patterns/disclosure/
- Base UI Select / Radix Select (behavior ceiling: Escape closes, selection
  communicated via `aria-selected`): https://base-ui.com/react/components/select ,
  https://www.radix-ui.com/primitives/docs/components/select

REQUIRED:

- **IC-LANG-01** (static) — The toggle is a native `<summary>` inside `<details>`
  (platform gives focusability + Enter/Space + expand/collapse semantics for free),
  or a `<button>` with `aria-expanded`.
- **IC-LANG-02** (static) — The toggle has an accessible name communicating purpose
  and, ideally, current selection (e.g. aria-label "Select language — current:
  English"; an icon-only summary with no name fails).
- **IC-LANG-03** (static) — The current selection is programmatically communicated:
  `aria-current` (link list) or `aria-selected` (listbox) on the current item, or the
  toggle's name embeds the current value. Scope: applies only when the device IS a
  selector (items carry hreflang, an item is already marked current/selected, or the
  toggle's accessible name declares language/locale/region/country/currency purpose).
  A plain disclosure-navigation menu (About, Company…) rendered with the same device
  has no selection concept — per APG, `aria-current` there means "current page" and
  demanding it would force dishonest markup; the check records as skipped.
- **IC-LANG-05** (behavioral) — The toggle is keyboard reachable and Enter/Space
  toggles the dropdown open/closed.
- **IC-LANG-06** (behavioral) — Escape closes the open dropdown. NOTE: native
  `<details>` does NOT do this by itself; a small script is required. This is the
  known cost of the native-first choice and is still REQUIRED (WCAG 1.4.13 analog,
  and both Base UI and Radix close on Escape).

RECOMMENDED:

- **IC-LANG-04** (static) — Locale items are real links carrying `hreflang`.
- **IC-LANG-07** (behavioral) — With the dropdown open, Tab moves through the locale
  items (list content in tab order).

## 3. `acc` — Accordion (native `<details name=...>` group)

Native `<details>`/`<summary>` with a shared `name` attribute is the blessed
implementation: the platform provides focusable summaries, Enter/Space toggling,
expand/collapse state exposure, and exclusive (single-open) behavior with zero
script. This satisfies the APG Accordion pattern's keyboard contract by construction.
What remains to verify is that the markup actually engages those platform features.

Sources:

- APG Accordion pattern: https://www.w3.org/WAI/ARIA/apg/patterns/accordion/
  (headers are buttons/toggles in the Tab sequence; Enter/Space toggles; single-open
  implementations collapse the previously open panel)
- Base UI Accordion (native-button triggers; notes the 2025 APG guidance update
  removing roving focus — Tab/Shift+Tab is the expected model):
  https://base-ui.com/react/components/accordion
- MDN exclusive accordions (`details` `name` attribute):
  https://developer.mozilla.org/en-US/docs/Web/HTML/Element/details#name

REQUIRED:

- **IC-ACC-01** (static) — Items presented as one accordion group share the same
  `name` attribute value. A visually-grouped accordion whose `<details>` lack `name`
  silently loses single-open behavior.
- **IC-ACC-02** (static) — Every `<details>` has a `<summary>` as its first element
  child (otherwise the browser synthesizes an unlabeled default marker toggle).
- **IC-ACC-03** (static) — Each summary has non-empty accessible text; a summary whose
  visible content is only `aria-hidden` icon spans has no name.
- **IC-ACC-06** (behavioral) — Summary is focusable; Enter and Space toggle the panel.
- **IC-ACC-07** (behavioral) — Single-open behavior holds: opening item 2 closes
  item 1 within a named group.
- **IC-ACC-08** (behavioral) — Revealed panel content is actually visible/reachable
  after opening (not clipped away by CSS).

RECOMMENDED:

- **IC-ACC-04** (static) — Decorative state icons inside the summary (e.g. the "+"
  glyph) are `aria-hidden="true"`.
- **IC-ACC-05** (static) — At most one item per named group is authored `open`
  (multiple `open` in an exclusive group is an authoring bug the browser papers over).

### Resolution notes — authored multi-open groups (remediation 2026-07)

The APG Accordion pattern's single-open behavior is **optional** ("Optionally,
if the accordion allows only one panel to be expanded…"). A composition may
legitimately author a multi-open disclosure family (`knobs.faq.exclusive: false`
in the composition schema). The contract distinguishes a *declared* multi-open
family from an *accidentally ungrouped* single-open group:

- The composer stamps the group's shared parent with `data-acc-multi="authored"`
  **only** for an explicit `exclusive: false` knob; every other FAQ family gets
  the shared `name` attribute by default (single-open is the family default).
- **IC-ACC-01** passes a declared multi-open group with a "grouping waived by
  declaration" note; an unmarked unnamed group still fails.
- **IC-ACC-07** probes a declared multi-open group for the *opposite* invariant:
  items must toggle independently (opening item 2 keeps item 1 open). A named
  group is still probed for exclusive behavior.

This is a recognition amendment, not a weakening: the default path (no
declaration) is exactly as strict as before, and the declared path swaps one
behavioral requirement for its authored counterpart, verified behaviorally.

## 4. `banner` — Dialog/banner dismiss (utility banner close control)

The utility banner is not a modal dialog — no focus trap or `role="dialog"` is
required. Its dismiss control is a plain **button** and must honor the APG Button
pattern: real button semantics, an accessible name, Enter/Space activation, and the
activation must actually do the thing (dismiss).

Sources:

- APG Button pattern: https://www.w3.org/WAI/ARIA/apg/patterns/button/
- APG Dialog (Modal) pattern — cited for the boundary: the banner intentionally is
  not one: https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/

REQUIRED:

- **IC-BAN-01** (static) — The close control is a native `<button>` (`type="button"`),
  or has `role="button"` with `tabindex="0"` and key handling.
- **IC-BAN-02** (static) — The close control has an accessible name (aria-label like
  "Dismiss", or text); an icon-only unlabeled control fails.
- **IC-BAN-04** (behavioral) — Keyboard activation (focus + Enter) dismisses the
  banner. A close button that is rendered but wired to nothing fails.

RECOMMENDED:

- **IC-BAN-03** (static) — The icon inside the control is `aria-hidden="true"`.

## 5. `carousel` + `marquee` — Edge-cut rails, carousels, logo marquee

The APG Carousel pattern targets slide rotators. Our "edge-cut carousels" are
horizontally scrolling rails (overflow-x) — closer to a scrollable region than a
slide rotator, but the user-facing contract is the same: **the content beyond the
edge must be reachable without a pointer, and the widget must announce itself**.

Sources:

- APG Carousel pattern: https://www.w3.org/WAI/ARIA/apg/patterns/carousel/
  (prev/next controls as native buttons with accessible names;
  `aria-roledescription="carousel"` on the container; slides as `role="group"` +
  `aria-roledescription="slide"` with "n of m" names; auto-rotation demands a pause
  control and stops on focus/hover)

REQUIRED:

- **IC-CAR-01** (static) — A scroll rail/carousel exposes previous/next controls as
  native buttons with accessible names, OR is an accessible keyboard-scrollable
  region (`tabindex="0"` + `role="region"`/`role="group"` + accessible name). A rail
  with neither strands its overflow content for keyboard users.
- **IC-CAR-05** (behavioral) — The rail is keyboard operable end-to-end: its controls
  (if any) are reachable and scroll it, or the rail itself takes focus and arrow keys
  scroll it.

RECOMMENDED:

- **IC-CAR-02** (static) — Container has `aria-roledescription="carousel"` and an
  accessible label (label must not contain the word "carousel").
- **IC-CAR-03** (static) — Slide containers use `role="group"` +
  `aria-roledescription="slide"` with per-slide accessible names ("3 of 10" is
  acceptable).
- **IC-CAR-04** (static) — If rotation/advance is automatic, a stop/start control
  exists and rotation stops on focus and hover. Skip-with-note when no auto-advance
  exists.

### Resolution notes — edge-cut rails without visible controls (remediation 2026-07)

FIDELITY TENSION, resolved via IC-CAR-01's second arm (already REQUIRED-compliant,
no bar lowered): the source site's edge-cut rail ships **no visible prev/next
chrome**, and pixel fidelity is doctrine (the replica gate must hold), so the
remediation does not invent visible buttons. The composed rail is instead the
**accessible keyboard-scrollable region** the contract sanctions:

- `tabindex="0"` + `role="region"` + `aria-roledescription="carousel"` +
  `aria-label` derived from the section's own heading ("Gallery" is the
  copy-neutral structural fallback — never invented brand copy).
- ArrowLeft/ArrowRight scroll one card-width per press via the shared structural
  interaction script (`component_render.interaction_script`), giving
  **cross-browser** keyboard parity — Chromium scrolls focused overflow
  containers natively, Firefox/WebKit do not; IC-CAR-05 must not depend on a
  UA quirk.
- Visually-hidden-but-focus-visible prev/next buttons were considered and
  rejected: the region+arrow-keys arm fully satisfies the reachability contract
  (APG's carousel controls exist to expose *slide rotation*, which this rail
  does not have), and hidden-until-focused controls add tab stops that pure
  keyboard users must step through on every rail.

### Marquee sub-family (`marquee`)

The logo marquee has **no APG pattern**. Contract per repo doctrine:

REQUIRED:

- **IC-MARQ-01** (static) — The duplicated half used to hide the animation seam is
  `aria-hidden="true"` (AT must not read the logo list twice).
- **IC-MARQ-02** (static) — `@media (prefers-reduced-motion: reduce)` neutralizes the
  marquee animation (`animation: none` on the track, or equivalent).
- **IC-MARQ-03** (behavioral) — With reduced motion emulated, the computed animation
  on the track is disabled and the content remains visible.

## 5b. `tabs` — Tabbed interface (WAI-ARIA APG tabs)

Added fix1 2026-07 (hubspot-v2 item-9: tabbed testimonial device — tab rail +
quote panel + metric footer). The composed device is `compose_section.py`'s
`_compose_tab_split` + the `_IX_TABS_JS` structural script; the contract is the
APG Tabs pattern with **selection follows focus** (automatic activation — the
panels are pre-rendered static content, so activation is cheap and the APG
prefers it in that case).

Sources:

- APG Tabs pattern: https://www.w3.org/WAI/ARIA/apg/patterns/tabs/
  (`role="tablist"` container with an accessible name; tabs are `role="tab"`
  elements with `aria-selected` + `aria-controls`; panels are `role="tabpanel"`
  with `aria-labelledby`; roving tabindex; ArrowLeft/ArrowRight/Home/End move
  focus within the tablist)

REQUIRED:

- **IC-TAB-01** (static) — Tabs are native `<button>` elements with `role="tab"`
  inside a `role="tablist"`, and EXACTLY ONE tab carries `aria-selected="true"`
  (the static-faithful first-tab-active default).
- **IC-TAB-02** (static) — Every tab's `aria-controls` references an existing
  `role="tabpanel"` id, and every panel's `aria-labelledby` references its tab
  (the two-way wiring AT needs).
- **IC-TAB-03** (static) — Roving tabindex + panel visibility: unselected tabs
  carry `tabindex="-1"` (the selected tab is the tablist's single tab stop);
  exactly the selected panel is visible (`hidden` on all others); the visible
  panel is focusable (`tabindex="0"` — panels hold no interactive first child
  in the composed device).
- **IC-TAB-05** (behavioral) — ArrowRight/ArrowLeft move focus between tabs
  (wrapping) and selection follows focus: the newly focused tab becomes
  `aria-selected="true"` and its panel replaces the visible one.
- **IC-TAB-06** (behavioral) — Home/End jump focus+selection to the first/last
  tab; clicking a tab selects it (pointer parity).

RECOMMENDED:

- **IC-TAB-04** (static) — The tablist carries an accessible name describing the
  content set (not the word "tabs").

## 6. `form` — Forms (text/email/tel/textarea/select/radio/submit)

Baseline scope: only what the renderer emits today — label association, required-field
communication, real submit buttons, help/error text association.

Sources:

- WAI tutorial, Labeling Controls (explicit `for`/`id`, implicit wrapping,
  `aria-label`/`aria-labelledby`): https://www.w3.org/WAI/tutorials/forms/labels/
- WAI tutorial, Form Instructions (`aria-describedby` for help/error text):
  https://www.w3.org/WAI/tutorials/forms/instructions/
- APG Button pattern (submit control): https://www.w3.org/WAI/ARIA/apg/patterns/button/

REQUIRED:

- **IC-FORM-01** (static) — Every visible `input`/`select`/`textarea` (excluding
  `hidden`/`submit`/`button`/`reset` types) has a programmatic label: `label[for]`
  matching its `id`, a wrapping `<label>`, `aria-label`, or `aria-labelledby`.
  Placeholder text is not a label.
- **IC-FORM-02** (static) — The form's submit affordance is a real
  `button[type="submit"]` (or `input[type="submit"]`, or a `<button>` defaulting to
  submit) — not a styled link.
- **IC-FORM-03** (static) — Every `<label>` is associated with an existing control
  (its `for` resolves to a control id, or it wraps a control). Catches display-only
  field mocks that look like inputs but are not.
- **IC-FORM-04** (static) — Required fields communicate requiredness programmatically
  (`required` or `aria-required="true"`), not only visually/via data attributes.
- **IC-FORM-07** (behavioral) — The browser-computed accessible name of every visible
  form control is non-empty (label association verified through the accessibility
  tree, not just markup inspection).

RECOMMENDED:

- **IC-FORM-05** (static) — Help text adjacent to a field (e.g. field-help spans) is
  linked via `aria-describedby`.
- **IC-FORM-06** (static) — Error-message plumbing is AT-visible: if fields carry
  error copy (e.g. `data-error`), the rendered error container is wired with
  `aria-describedby` (and announced via `aria-live` or focus management on submit).
  Baseline flags data-only error copy as advisory.

## 7. `reveal` — Scroll-reveal choreography

No ARIA pattern applies; the contract is a **robustness failsafe** statement: reveal
animation is an enhancement and must never gate content.

REQUIRED:

- **IC-REV-01** (static) — The hidden initial state (`opacity: 0` etc.) applies only
  under a JS-added gate class (e.g. `.cs-motion-ready .cs-reveal`). With JS off or
  IntersectionObserver unavailable, content is fully visible by construction. A bare
  ungated `.cs-reveal { opacity: 0 }` rule fails.
- **IC-REV-02** (static) — `@media (prefers-reduced-motion: reduce)` forces revealed
  targets fully visible and neutralizes reveal transitions.
- **IC-REV-04** (behavioral) — With reduced motion emulated (JS running), reveal
  targets compute to visible (opacity 1) immediately after load — not after a timed
  failsafe.

RECOMMENDED:

- **IC-REV-03** (static) — A timed failsafe exists in the reveal script (deadline
  after which all targets are forced visible), guarding against mis-rooted or
  never-firing observers.

---

## Auditor contract

- `brand_pipeline/interaction_audit.py` implements every static check above and the
  behavioral checks marked behavioral. Component instances are detected by the
  renderer's structural signatures; when a family is absent from a lane the auditor
  emits `skip` with a note rather than silence.
- Findings are keyed `IC-<FAMILY>-<NN>` with severity (required/advisory), element
  locator (source line + snippet), and lane.
- Baseline mode always exits 0. `--strict` exits 1 when any REQUIRED check fails
  (future gate wiring).
- Reports: `runs/remote/brand/interaction-baseline/report.md` (human) and
  `report.json` (machine), including the audited file's mtime/sha so results can be
  correlated if lanes are re-rendered mid-run by other agents.
