# signal-loop.md — self-education design (SPEC, not yet implemented)

> Status: **design / for review**. This is the **Art Director's** loop (skill
> `brand-art-director`): it specifies how the Brand Extractor pipeline learns over time
> by capturing signals (the **Layout Analyst** emits creation signals; the Art Director
> consolidates), promoting high-confidence design-language rules into the canonical,
> library-agnostic `brand.yaml`, and handling contradictions safely. No runtime changes
> here. Reads/writes only the spec'd files below; never edits `brand.md` (rendered).
> Promotions land in the three rule lists `do[]`/`avoid[]`/`neverDo[]` (or
> `recipePolicy`); `targetMappings` is substrate annotation and is never a promotion target.

## 1. Files

| file | role | format |
|---|---|---|
| `signals.log` | append-only event stream of every signal | JSONL (one JSON object per line) |
| `brand.yaml` | canonical design language (consolidation target) | YAML (see `brand-schema.md`) |
| `pending-questions.yaml` | queue of clarifying questions awaiting the user | YAML |
| `consolidation-report.md` | human-readable summary of the last consolidation pass | Markdown (rendered, not edited) |

All live under `runs/<brand>/brand/` alongside `brand.yaml`.

## 2. `signals.log` — JSONL format

One object per line. Append-only; never rewrite prior lines. Schema:

```jsonc
{
  "id":             "sig-<ts>-<rand>",        // stable unique id
  "type":           "creation|iteration|build-failure",
  "sectionId":      "info-band",              // section/layout this concerns, or null for global
  "text":           "raw observation or user/system message",
  "ruleKey":        "compositionRules.overlap-primary-ornament", // dotted path into brand.yaml, or null if new
  "detectedConflict": true,                   // does this contradict an existing brand.yaml rule?
  "conflictWith":   "neverDo.no-cards-on-cream", // dotted path of the contradicted rule, or null
  "resolution":     "one-off|promote|reject|pending", // action taken (see protocol §5)
  "scope":          "design-language|one-off",
  "confidence":     "high|medium|low",
  "questionId":     "q-<ts>-<rand>",          // pending-question id if one was queued, else null
  "timestamp":      "2026-06-12T17:16:00Z"
}
```

Example lines:

```jsonl
{"id":"sig-20260612T1716-a1","type":"creation","sectionId":"info-band","text":"flush photo + cream panel with ruled action rows","ruleKey":"layouts[].info-band","detectedConflict":false,"conflictWith":null,"resolution":"promote","scope":"design-language","confidence":"high","questionId":null,"timestamp":"2026-06-12T17:16:00Z"}
{"id":"sig-20260613T0902-b7","type":"iteration","sectionId":"about-run","text":"user: put a bordered card around the third about block","ruleKey":null,"detectedConflict":true,"conflictWith":"neverDo.no-cards-on-cream","resolution":"one-off","scope":"one-off","confidence":"low","questionId":"q-20260613T0902-b7","timestamp":"2026-06-13T09:02:00Z"}
{"id":"sig-20260613T1130-c3","type":"build-failure","sectionId":"conversion","text":"Form/Webflow/Lead requires unique Form ID; build rejected duplicate","ruleKey":"recipePolicy.formIdUnique","detectedConflict":false,"conflictWith":null,"resolution":"promote","scope":"design-language","confidence":"high","questionId":null,"timestamp":"2026-06-13T11:30:00Z"}
```

## 3. Three signal sources

1. **creation-time** (`type: creation`) — emitted by the `brand-layout-analyst`
   skill during first-pass extraction. One signal per observed rule/token/layout.
   These seed `brand.yaml` with `source: creation`. Generally non-conflicting
   (they *create* the baseline); high-confidence ones promote directly.
2. **iteration** (`type: iteration`) — emitted when a human edits/redirects a built
   section ("make this panel dark", "add a border here", "use a real button"). The
   signal carries the user's intent text. May or may not conflict with an existing
   rule; conflicts trigger the contradiction protocol (§5).
3. **build-failure** (`type: build-failure`) — emitted when the assembler/Webflow
   build rejects something (e.g. `clamp()` rejected by the size-variable API,
   duplicate Form ID, slot rejecting a raw element). These become high-confidence
   `recipePolicy`/`neverDo` constraints with `source: failure` — the system learns
   what the platform won't accept.

## 4. Consolidation pass

**(SIGN-OFF #2)** Runs **on-demand / manual only** — never on a schedule and never
automatically before publish. A human explicitly invokes it. It promotes eligible
signals into `brand.yaml` and produces `consolidation-report.md`.

Algorithm:

1. Read all `signals.log` lines since the last consolidation watermark.
2. Group by `ruleKey` (or by normalized `text` for new rules without a key yet).
3. For each group, compute an **aggregate confidence**:
   - ≥2 consistent signals across distinct sections → raise toward `high`.
   - single occurrence → cap at `low`/`medium`.
   - any `build-failure` signal → `high` (platform facts are authoritative).
4. **Promotion gate** — two distinct tracks per SIGN-OFF #3 and #4:

   **(SIGN-OFF #3) Design-language promotions REQUIRE explicit user confirmation.**
   Reaching `scope == design-language`, aggregate `confidence == high`, and
   `detectedConflict == false` does **NOT** auto-promote. Instead it raises a
   **candidate** and surfaces it in `consolidation-report.md` (and, optionally, a
   `pending-questions.yaml` entry) for the user to approve. Only after the user
   confirms is the rule upserted into `brand.yaml`. ≥2 consistent signals therefore
   *flag a candidate*, they never auto-write the design language.

   **(SIGN-OFF #4) `build-failure` signals AUTO-PROMOTE without asking.** Platform
   facts (rejected `clamp()`, duplicate Form ID, slot rejecting a raw element) are
   authoritative: promote directly into `neverDo`/`recipePolicy` at `confidence:
   high`, `source: failure`, no user confirmation required.

   Promotion (either track) = upsert the rule envelope in `brand.yaml`, set `source`
   to the signal source (`iteration`/`failure`), and **append a `changelog`** record:
   `{ ts, action: promoted|updated, from, to, by, signalId, note }`.
5. Signals that don't pass the gate:
   - `one-off` → already applied to that single instance; left in the log, NOT in
     `brand.yaml` design language. Recorded in the report under "applied as one-off".
   - `low/medium design-language` → held as "candidate" in the report; re-evaluated
     next pass when more evidence may arrive.
6. After promotion, **re-render `brand.md`** from `brand.yaml` and write
   `consolidation-report.md` (counts: promoted / one-off / candidates / questions
   queued, with the changelog deltas).
7. Advance the watermark.

The append-only `changelog` on every promoted rule (per `brand-schema.md` envelope)
gives full provenance: what changed, when, driven by which signal, and reversibility.

## 5. Contradiction protocol (USER DECISION #3: one-off-and-queue default)

When a signal's `detectedConflict == true` (it contradicts an existing `brand.yaml`
rule) **and the user has not already responded** to a matching question:

1. **Do NOT block** the current work and **do NOT auto-promote** the contradicting
   value into the design language.
2. **Apply as a one-off**: implement the change for *this instance only*; emit the
   signal with `resolution: one-off`, `scope: one-off`. The existing design-language
   rule in `brand.yaml` is left intact.
3. **Queue a clarifying question** in `pending-questions.yaml` (§6) and set the
   signal's `questionId`. Continue working.
4. When the user later answers, apply the chosen branch:
   - **update design language** → promote: update the existing rule's `value`,
     append `changelog` `{action: updated, by: iteration, ...}`, re-render `brand.md`.
   - **one-off for this instance** → confirm the already-applied one-off; mark the
     question resolved; no `brand.yaml` design-language change.
   - **keep existing** → revert the one-off instance back to the design-language
     rule; append `changelog` `{action: reverted, ...}`; mark resolved.

If a contradiction recurs and an *unanswered* question already exists for the same
`conflictWith` rule, do not enqueue a duplicate — link the new signal to the existing
`questionId` and apply one-off again.

### Exact user-facing question template

```
⚠️ Brand-language conflict on section "{sectionId}"

The change you asked for:
  "{signalText}"
contradicts an existing {scope} rule in brand.yaml:
  {conflictWith} → "{existingRuleStatement}"  (confidence: {existingConfidence})

I've applied it as a ONE-OFF for this instance only and kept the rule unchanged.
How should I treat this going forward?

  [1] Update design language — change the rule for ALL future sections
      (updates brand.yaml: {conflictWith} → "{proposedValue}", re-renders brand.md)
  [2] One-off for this instance — keep the change here only, rule stays as-is (DEFAULT, already applied)
  [3] Keep existing — revert this instance back to "{existingRuleStatement}"

Reply 1, 2, or 3.
```

## 6. `pending-questions.yaml` — queue format

```yaml
questions:
  - id:            "q-20260613T0902-b7"
    signalId:      "sig-20260613T0902-b7"
    sectionId:     "about-run"
    status:        open            # open | answered | resolved
    conflictWith:  "neverDo.no-cards-on-cream"
    existingRule:
      statement:   "No cards on the cream canvas — light-canvas content is open collage, never boxed."
      confidence:  high
    proposedChange:
      signalText:  "user: put a bordered card around the third about block"
      proposedValue: "allow bordered card on cream for emphasis blocks"
    appliedAs:     one-off         # what was done in the meantime (per default protocol)
    options:       [ update-design-language, one-off, keep-existing ]
    askedAt:       "2026-06-13T09:02:00Z"
    answer:        null            # one of options once user replies
    answeredAt:    null
    resolution:    null            # promoted | confirmed-one-off | reverted
    changelogRef:  null            # brand.yaml changelog entry id once resolved
```

Lifecycle: `open` → (user replies) `answered` → (protocol branch applied + brand.yaml
updated/re-rendered) `resolved`. The queue is surfaced to the user at natural
checkpoints (end of an iteration batch, before publish, or on request) — never as a
hard mid-build block.
