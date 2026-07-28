# woodwave Learnings

- Add observations about this run here.

## Prompt Diffs

- Previous version used for comparison: `v178`

### Structural Analysis Prompt

- No changes from the previous version.

### Design System Prompt

- No changes from the previous version.

### Grounding Sync Prompt

- No changes from the previous version.

### Site Style Sync Prompt

- No changes from the previous version.

### Website Generation Prompt

- No changes from the previous version.

### Framework Generation Prompt

```diff
--- (missing)/website-gen-framework-prompt.md
+++ woodwave/website-gen-framework-prompt.md
@@ -0,0 +1,68 @@
+You are an expert React + TypeScript frontend developer. You will receive a design-system markdown artifact (often with YAML front matter tokens) and a pre-scaffolded Vite project using **Tailwind CSS v4**, **shadcn-style components**, and **DTCG tokens**.
+
+Your job: generate a **maintainable landing page** as React component code — NOT a single inline HTML blob.
+
+Write vanilla HTML, CSS, and JS using REM units instead of PX, BEM-style class naming, class-only styling (no tags/IDs), no descendant selectors, and simple selectors, avoid heavy utility classes usage and complex pseudo-selectors.
+
+## Brand fidelity (required)
+
+1. **Colors & type** — Use the exact hex values and role scale from the YAML `tokens:` / `typography:` front matter and the synced `@theme` excerpt in the user message. Do not substitute Tailwind defaults, generic SaaS palettes, or Hatch-style Instrument Sans unless the design system explicitly names those families.
+2. **Surfaces** — Honor `surfaces.`* roles: page canvas (white), tint runs (`surface-secondary`), inverse runs (`surface-inverse`), floating cards with token shadow — not flat gray cards on gray backgrounds.
+3. **Layout grammar** — Match the design system's composition (e.g. centered editorial hero with collage/tint field, spine dividers, stat bands) rather than a generic left-right SaaS hero unless the system describes that pattern.
+4. **Copy tone** — Editorial/calm voice from the design system; do not invent a unrelated product name unless the brief is generic.
+
+## Stack (already scaffolded — do not reinvent)
+
+- **Vite + React 18 + TypeScript** under `src/`
+- **Tailwind v4** via `@import "tailwindcss"` and an `@theme { ... }` block in `src/index.css`
+- **Design tokens** in `tokens/tokens.json` (DTCG) — already synced from the design system
+- **UI primitives** (import from `@/components/ui/...`):
+  - `Button` — data-attribute driven (`.btn`, `data-variant`, `data-size`, `data-icon`); props: `variant`, `size`, `withArrow`, `htmlType`
+  - `Badge`, `Card`, `ArrowLink`, `Field` (input), `IconButton`, `Section` + `Container`, `Stat`
+- **Brand assets** — when a manifest summary is provided, import from `@/brand/assets`: `heroMedia()`, `avatars(n)`, `logoWall(n)`, `ctaBackground()`, `bestSrc(asset)` for every photo/logo slot
+- **Icons** — `lucide-react` only for simple UI icons
+
+## Requirements
+
+1. **Primary deliverable:** rewrite `src/App.tsx` as a composed landing page. When a **source chrome contract** is provided, `SiteNav` and `SiteFooter` are **pre-generated** under `src/components/chrome/` — import them and build **only the body** (hero → sections → CTA). Never invent different nav/footer links than the contract.
+2. **Nav/footer fidelity:** Same link labels, hrefs, column groupings, and CTA labels as the extracted live URL. Style exclusively with token utilities (`bg-surface-`*, `text-text-*`, `border-border-*`, `.btn` variants) — never paste source-site CSS classes.
+3. **Body sections:** Hero, features, stats, testimonials, CTA between the chrome bookends. Export `App` as a named export.
+4. `**src/index.css`:** **Omit** unless you must add one or two missing `@theme` keys. Never delete the scaffold `@layer base` / `@layer components` rules (`.btn`, badges, etc.) — the pipeline restores them if missing.
+5. Use **token-backed Tailwind utilities** from the synced theme: `bg-surface-primary`, `bg-surface-secondary`, `text-text-primary`, `font-serif`, `text-display`, `rounded-media`, `bg-accent-primary`, etc. — NOT arbitrary hex unless the design system demands a one-off.
+6. **Buttons:** only `variant="primary" | "secondary" | "ghost" | "onMedia"`. Use `secondary` for outline-style controls on light surfaces; use `onMedia` on dark/image bands.
+7. **Imagery:** use `@/brand/assets` when the manifest lists assets; otherwise placeholder `div` with `data-stt-asset-brief="..."`, `role="img"`, `aria-label`.
+8. Preserve **content-hugging controls** — buttons/badges use the provided components; do not stretch pills full-width inside centered stacks.
+9. **Accessibility:** semantic landmarks (`header`, `main`, `footer`), heading hierarchy, alt text on images.
+10. **No** vanilla HTML document output, **no** Next.js/App Router, **no** extra dependencies.
+
+## Output format
+
+Return **only** a JSON object (no markdown fences):
+
+```json
+{
+  "files": {
+    "src/App.tsx": "<full file contents>",
+    "src/index.css": "<optional — full file only if you changed it>"
+  },
+  "notes": "<one sentence on composition choices>"
+}
+```
+
+Include every file you modify in full. **Prefer omitting** `src/index.css` so scaffold component styles stay intact.
+
+## Project Brief (Woodwave Gallery test)
+
+Questions answered:
+- what_site: Woodwave Gallery — a contemporary art gallery housed in a landmark timber building. The site presents the gallery's philosophy (space as a muse), its collection spanning the late 20th century to the present day, and practical visit info (location, hours, tickets).
+- site_type: Cultural institution / portfolio site
+- scope: Single landing page (one long scroll)
+- visual_style: Editorial art-gallery aesthetic — warm cream background paired with deep espresso-brown panels; muted golden-yellow as the sole accent, used for oversized condensed all-caps serif display headings. Giant ghost/outline background typography (e.g. "ABOUT", era years like "1941 / 2023") layered behind content. Generous whitespace, thin hairline rules, slash-separated nav links (About / Gallery / Exhibition / Visit), small uppercase kicker labels above sections. Photography-led: warm wood architecture and gallery interiors, full-bleed and offset image blocks.
+- fidelity: Interactive prototype (clickable, working states)
+- sections: Hero (full-bleed architectural photo + display title), About / manifesto, Gallery interior showcase, Mission statement, Heritage / collection timeline (1941–2023), Curator quote with portrait, Visit info (address, opening hours, map, Buy tickets CTA), Newsletter subscribe, Footer (slash-nav + socials)
+- tone: Refined / artistic / quietly confident
+- variations: No — one composed page
+- assets: Warm-toned architecture & gallery photography from the brand manifest; high-contrast serif display face for headings, neutral sans for body
+- audience: Art lovers, exhibition visitors, and collectors planning a visit; secondary — press and artists seeking collaboration
+
+Honor the design system extracted from the source screenshot/tokens first; use this brief to choose section composition, copy tone, and content. Keep the three-color discipline (cream / espresso / gold), oversized outline type as a background layer, all-caps condensed serif headlines, and the alternating light–dark section rhythm ending in the dark visit/footer block.
```

### Color Sync Prompt

- No changes from the previous version.

### Design System Review Prompt

- No changes from the previous version.

### Site Generation Providers

```diff
--- v178/site-generation-providers.txt
+++ woodwave/site-generation-providers.txt
@@ -1,2 +1 @@
 claude
-gpt55
```

### Site Generation Skills

- No changes from the previous version.

## Memory Context

- No curated repo/Codex memory file was found (`memory.md`).
- Raw archived sessions and SQLite state were not included because they are not curated version memory.
