# section-rules.md — the section-scoped deterministic rule library

> **Status: ENFORCED (stage B landed 2026-07-14).** Data:
> `contracts/section-rules.yaml` (section-rules.v1); checker:
> `brand_pipeline/section_rules_audit.py`; tests:
> `tests/test_section_rules_audit.py`; first battery + calibrations:
> `evals/matrix/changes.md`. This doc is the short law text; the YAML is the
> system of record for the rules themselves.

## Why rules belong to sections

The AS registry (`anti-ai-slop.md`) owns UNIVERSAL failure shapes — context-blind
values that break anywhere. But a large class of quality failures is only
falsifiable inside one section family's anatomy: "every stat value carries a real
magnitude" means nothing outside a stat band; "tier cards share slot anatomy" means
nothing outside pricing. Forcing those into global gates yields brittle heuristics;
leaving them unchecked is how generated pages pass every gate and still read as AI
output. So the library scopes each rule to the family whose anatomy makes it
measurable — the same shape as `heroes-saas.yaml` scoping physicsBindings per
archetype and `interaction_audit.py` scoping IC checks per component family.

## Division of law (no duplication)

- **`enforcement: new`** — a genuinely uncovered check; gets checker code in the
  section-rules auditor (stage B: `brand_pipeline/section_rules_audit.py`).
- **`enforcement: delegated`** — the concern is EXISTING law (an AS rule, a gate, an
  IC family). The row names `delegatedTo` and the auditor reports the scoping
  without re-implementing the check — mirror of the archetype-physics delegation
  rows in `onbrand_check.py`. A delegated row exists so a section family's rule
  list reads complete; deleting it changes no enforcement.
- Universal AI-tells stay OUT: `registryCandidates` (bottom of the YAML) records
  the 1–2 generalizations offered to the AS registry owner.

## Scoping + severity doctrine

- **Lane scope**: content-family rules bind in GENERATIVE lanes only
  (`composition.v1` marker or briefed legacy composition — the pass1
  scale_adherence scoping, spacing-conformance §3b). Replica lanes are evidence,
  never audit targets. Chrome families (nav/footer) check fact-parity in generated
  lanes. Specimen/preview lanes skip page-scoped rules.
- **Precedence**: measured brand facts outrank every budget here (brand-schema
  §5.3, AS-44). A brand fact contradicting a rule records **OVERRIDE (blessed,
  fact cited)**, not FAIL — the style-library genre-class posture
  (INTEGRATION-PLAN §4.1).
- **Severity is staged** (pass1 voice-gate posture): `new` rules start advisory
  unless their failure is unambiguous structural dishonesty; `required` gates only
  under `--strict`, and only after the rule is **fixture-proven** — it fails a
  synthetic-bad fixture AND passes all real lanes. A real-lane failure at
  enforcement time is a FINDING: fix it at the right level (copy, composer,
  evidence) or demote the rule with a changelog note. Never tune a budget to make
  a lane pass silently.

## Enforcement shape (stage B contract)

`section_rules_audit.py` follows the interaction-audit pattern:

1. **Detect** each rendered section's families via the `detection:` table
   (composers' stable device classes + the lane composition's `useCase` +
   `data-archetype` stamps). A section may bind multiple families; chrome
   families detect on the page.
2. **Check** matching rules in two layers: STATIC (HTML parse: word counts,
   anatomy-parity sets, shape-class parses, roster diffs) and GEOMETRY
   (Playwright: rendered line counts via box-height/line-height, box uniformity,
   computed register sizes). Absent families emit `skip` findings, never silence.
3. **Report** `report.md` + `report.json` per lane run; findings keyed by rule id
   with locator + budget + measured value. Baseline exits 0; `--strict` exits 1
   on failing `required` rows. OVERRIDE rows cite the winning brand fact.

Generation-time cost: ZERO. The auditor is a post-render check, wired beside the
existing battery (slop / interaction / spacing / signature / voice); nothing runs
inside the generation loop.

## Growing the library

Same doctrine as the AS registry: when a section-scoped quality bug is caught,
add a rule (next `SR-<FAM>-NN`) with a falsifiable assertion, named provenance,
and a fixture — do not just fix the instance. If the failure shape is universal,
it belongs in `anti-ai-slop.md` instead; when unsure, note it under
`registryCandidates` and keep the scoped rule.
