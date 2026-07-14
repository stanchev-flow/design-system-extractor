# conversion-structure.md — campaign section-sequence contracts

> **Status: stage B wired (2026-07-14).** Data:
> `contracts/conversion-structure.yaml` (conversion-structure.v1). This doc is
> the law text for consumption; the YAML owns the grammars. Two consumer
> modules, one owner each (AS-06 discipline):
> `conversion_structure.py` — the brief-time guidance projection (prompt side);
> `conversion_audit.py` — the deterministic checker (composition + rendered
> lanes, reports, advisory wiring). Tests: `test_conversion_guidance.py`
> (projection + injection byte-identity) / `test_conversion_structure.py`
> (checker interpreter).

## What this layer owns

The ORDER OF ARGUMENT of a campaign page: which section families it needs, how
they sequence, where proof sits, where the form sits, and how deep the page runs
for its funnel stage. It sits above section quality (section-rules.yaml) and
visual law (AS registry): a page can pass every section-scoped check and still be
a broken campaign — a gated-content page with no form, a pricing page that buries
its tiers below four marketing beats, an awareness launch that opens with a
qualification battery. Those are structure-of-argument failures, and they are
checkable from the section family sequence alone.

## Brief-time guidance injection (zero extra LLM calls) — WIRED, default OFF

A brief opts in with ONE frontmatter key: `campaignType: <id>` (beside the
existing `pageType`/`taskIntents`/`variance` keys that `parse_brief_frontmatter`
already reads). `conversion_structure.render_guidance_block(brief_text)`
projects the campaign's grammar into a short guidance block:

- the campaign `intent` prose, verbatim;
- one bullet per constraint, deterministically templated from the constraint
  kind + its `why:` note (e.g. `window/firstN:3` → "capture-form lands within
  the first 3 sections — <why>");
- the depth band and form-depth band as plain sentences.

The block rides the USER prompt (with the brief, before the output contract)
via `build_prompt(..., conversion_guidance=...)`, threaded from
`generate_composition(..., inject_conversion_guidance=True)`. The wiring is
DOUBLY fact-gated, per the pass-2 scope note (pass 3 owns the system-prompt
brand-fact injection; this block must not pre-empt that architecture):

1. the caller must opt in — the flag defaults to **False**, so the default
   pipeline assembles byte-identical prompts (test-pinned:
   `test_conversion_guidance.py::PromptInjection`);
2. the brief must declare a known `campaignType` — absent/unknown projects
   None, byte-identical again.

The projection is a pure function of the YAML (no model call, no network); an
opted-in composition request stays ONE generation call with a slightly longer
prompt (~1.7k chars). Prompt guidance is ADVICE to the generator; the checker
is what verifies the outcome. The eval-matrix BASELINE round runs with the flag
OFF — the baseline measures the un-guided pipeline, and the checker's advisory
findings on it quantify what the guidance is FOR; a later round may A/B the
flag against that baseline.

## Deterministic checker (`conversion_audit.py`; advisory first)

`check_conversion_structure(composition, campaign)` evaluates the ordered
content-section family list (chrome excluded) against the campaign's constraint
rows — a small interpreter over the seven constraint kinds declared in the YAML
(`opens/closes/present/window/afterIndex/before/adjacent`). Families resolve via
`familyMap` at composition level, re-grounded post-render by the section-rules
family detector.

- Wired beside the composition gate for briefed lanes that declare
  `campaignType` (fact-gated: undeclared lanes skip with a note).
- ADVISORY at wiring time: rows report WARN; `required` rows graduate to
  gate-failing only after the eval-matrix baseline proves them against real
  generations (fixture-proven doctrine, mirroring section-rules severity
  staging). The two `hardFloor` rows gate from birth.
- The BRIEF outranks the grammar: an explicit brief instruction contradicting a
  row records OVERRIDE (brief cited), not FAIL. Brand evidence outranks both.

## Offline judge — DESIGNED, NOT BUILT (eval-matrix rounds only)

The deterministic checker verifies sequence mechanics; it cannot judge whether
the argument PERSUADES. That judgment is an LLM-judge rubric that runs only in
offline eval-matrix rounds (`evals/matrix/`) — never in the generation loop,
never in the gate battery, so generation-time cost stays zero.

Rubric (score 1–5 per criterion, every score citing section-level evidence):

1. **Arc coherence** — does the page argue in an order a motivated reader would
   follow (claim → substance → proof → objections → ask), with no beat that
   assumes knowledge a later beat introduces?
2. **Funnel-stage fit** — does depth/friction match the reader's commitment
   (awareness pages story-first, decision pages ask-first)? Penalize
   qualification batteries at awareness stage and story-padding at decision
   stage.
3. **Proof credibility** — is proof specific (named magnitudes, attributed
   voices, real marks) and placed where hesitation peaks, or generic and
   decorative?
4. **Objection coverage** — are this campaign type's predictable objections
   (price/refunds for pricing, time/format for events, switching cost for
   comparison) answered on-page before the conversion moment?
5. **Ask clarity** — is there ONE unmistakable next step, stated in verb-led
   copy, repeated where attention peaks and nowhere else?

Protocol notes for the future implementation: judge prompt receives the brief +
the composition's family/sequence projection + rendered-page screenshots; runs
once per matrix brief per round; scores land in the round's results table beside
gate results; a score is a TREND instrument across rounds, never a gate. Build
condition (stage B ruling): implement only if trivially cheap — otherwise record
as designed-not-built in the round's changelog.
