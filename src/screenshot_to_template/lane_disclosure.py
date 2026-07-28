"""Site-generation lane disclosure — what a run built, what it skipped, and why.

A run can take more than one site-generation lane, and each lane is gated
independently (a config key, a CLI flag, the per-run provider list, the mode
flags, and — for the framework lane — the fail-closed brand-lane gate). Nothing
used to state which lanes a run actually took: a default CLI invocation builds
zero framework sites because ``framework-generation-enabled`` is false in
``config.default.yaml``, and the only trace of that was the absence of an output
file. The run reported success either way.

This module owns the vocabulary and the derivation:

  * :func:`plan_site_generation_lanes` resolves the gates ONCE, before any model
    work, into a :class:`LanePlan` per lane that names the config key and the flag
    that would enable it.
  * :class:`LaneLedger` records what each lane target (lane × provider × run item)
    actually did, and DERIVES the lane-level outcome from those records. Nothing
    here is hand-authored: a lane can only claim it produced output if a target
    reported a file it wrote.
  * The same records render both the console summary and the manifest payload, so
    the log and ``manifest.json`` can never disagree.

Outcomes are deliberately distinct: a lane that was switched off is a different
fact from a lane a quality gate refused, which is different again from a lane
that tried and failed.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Iterable, Sequence

SCHEMA_VERSION = "site-generation-lanes.v1"

LANE_FRAMEWORK = "framework"
LANE_VANILLA = "vanilla"

# Per-target outcomes. ``skipped_disabled`` (a switch) and ``skipped_gate`` (a
# quality refusal) are never collapsed into one "skipped" — the reader's next
# action is different for each.
OUTCOME_PRODUCED = "produced"
OUTCOME_SKIPPED_DISABLED = "skipped_disabled"
OUTCOME_SKIPPED_NOT_REQUESTED = "skipped_not_requested"
OUTCOME_SKIPPED_NO_INPUT = "skipped_no_input"
OUTCOME_SKIPPED_GATE = "skipped_gate"
OUTCOME_FAILED = "failed"
# Lane-level only: the lane was enabled but the run never got as far as deciding
# anything for it (an earlier stage raised), so claiming "skipped" would be a lie.
OUTCOME_NOT_REACHED = "not_reached"

# Lane-level precedence when a lane's targets disagree. Any real output wins (the
# lane did produce something), then the loudest failure, then the switches.
_OUTCOME_PRECEDENCE = (
    OUTCOME_PRODUCED,
    OUTCOME_FAILED,
    OUTCOME_SKIPPED_GATE,
    OUTCOME_SKIPPED_DISABLED,
    OUTCOME_SKIPPED_NO_INPUT,
    OUTCOME_SKIPPED_NOT_REQUESTED,
)

_OUTCOME_LABELS = {
    OUTCOME_PRODUCED: "PRODUCED",
    OUTCOME_SKIPPED_DISABLED: "SKIPPED — disabled in config",
    OUTCOME_SKIPPED_NOT_REQUESTED: "SKIPPED — not requested for this run",
    OUTCOME_SKIPPED_NO_INPUT: "SKIPPED — no saved input to regenerate from",
    OUTCOME_SKIPPED_GATE: "SKIPPED — blocked by a gate",
    OUTCOME_FAILED: "FAILED",
    OUTCOME_NOT_REACHED: "NOT REACHED — the run stopped before this lane",
}


@dataclass(frozen=True)
class LaneSpec:
    """The static identity of a site-generation lane: what it is called, which
    config key and CLI flag control it, and which providers it can build."""

    lane: str
    label: str
    config_key: str
    enable_flag: str
    providers: tuple[str, ...]
    artifact_template: str

    def artifact(self, provider: str) -> str:
        return self.artifact_template.format(provider=provider)


LANE_SPECS: dict[str, LaneSpec] = {
    LANE_FRAMEWORK: LaneSpec(
        lane=LANE_FRAMEWORK,
        label="framework sites (React + Tailwind v4)",
        config_key="framework-generation-enabled",
        enable_flag="--framework-sites",
        providers=("claude", "gpt55"),
        artifact_template="site-{provider}-framework.html",
    ),
    LANE_VANILLA: LaneSpec(
        lane=LANE_VANILLA,
        label="vanilla one-shot HTML",
        config_key="vanilla-site-generation-enabled",
        enable_flag="--vanilla-sites",
        providers=("claude", "gemini", "gpt55"),
        artifact_template="site-{provider}.html",
    ),
}


@dataclass
class LanePlan:
    """One lane's resolved gate state, decided before any model work runs."""

    lane: str
    label: str
    config_key: str
    enable_flag: str
    config_value: bool
    enabled: bool
    reason: str
    providers: tuple[str, ...] = ()
    skipped_providers: tuple[str, ...] = ()

    @property
    def spec(self) -> LaneSpec:
        return LANE_SPECS[self.lane]

    def artifacts(self) -> tuple[str, ...]:
        return tuple(self.spec.artifact(p) for p in self.providers)

    def to_dict(self) -> dict:
        return {
            "lane": self.lane,
            "label": self.label,
            "configKey": self.config_key,
            "enableFlag": self.enable_flag,
            "configValue": self.config_value,
            "enabled": self.enabled,
            "reason": self.reason,
            "providers": list(self.providers),
            "skippedProviders": list(self.skipped_providers),
        }


@dataclass
class LaneTarget:
    """What one lane × provider × run item actually did."""

    lane: str
    provider: str
    item: str
    outcome: str
    reason: str = ""
    output: str = ""

    def to_dict(self) -> dict:
        row = {
            "lane": self.lane,
            "provider": self.provider,
            "item": self.item,
            "outcome": self.outcome,
        }
        if self.reason:
            row["reason"] = self.reason
        if self.output:
            row["output"] = self.output
        return row


def _disabled_reason(spec: LaneSpec, extra: str = "") -> str:
    base = (
        f"{spec.config_key} is false in the resolved config "
        f"(config.default.yaml is the always-loaded CLI baseline) — set "
        f"{spec.config_key}: true in a --config override or pass {spec.enable_flag}"
    )
    return f"{extra} — {base}" if extra else base


def plan_site_generation_lanes(
    *,
    framework_config_value: bool,
    framework_flag: bool,
    vanilla_config_value: bool,
    vanilla_flag: bool,
    providers: Sequence[str],
    sites_only: bool = False,
    design_only: bool = False,
    surface_map_only: bool = False,
) -> list[LanePlan]:
    """Resolve every site-generation lane's gate state from the run's inputs.

    Mirrors ``run_pipeline``'s own decisions rather than re-deciding them, so the
    disclosure cannot drift from what the run does: the framework lane is on when
    the config key is true OR ``--framework-sites`` was passed, and the vanilla
    lane is skipped exactly when ``skip_vanilla_html`` is true there.

    Each lane's key is authoritative for its own lane. Both keys false is
    therefore a legitimate combination that enables nothing, and the caller is
    expected to refuse such a run rather than let it produce nothing in silence.

    ``design_only`` / ``surface_map_only`` are modes that deliberately stop before
    site HTML, so both lanes come back disabled with the mode as the reason.
    """
    requested = list(providers)
    framework_spec = LANE_SPECS[LANE_FRAMEWORK]
    vanilla_spec = LANE_SPECS[LANE_VANILLA]

    # A flag and its config key are merged the same way run_pipeline merges them:
    # --framework-sites / --vanilla-sites turn the key on for the run.
    framework_enabled = bool(framework_config_value or framework_flag)
    vanilla_requested = bool(vanilla_config_value or vanilla_flag)
    # This is run_pipeline's skip_vanilla_html, kept as one expression so the two
    # can be compared line by line.
    sites_only_framework_refresh = bool(framework_flag and sites_only)
    skip_vanilla = sites_only_framework_refresh or not vanilla_requested

    if framework_flag:
        framework_reason = f"{framework_spec.enable_flag} was passed"
    elif framework_config_value:
        framework_reason = f"{framework_spec.config_key} is true in the resolved config"
    else:
        framework_reason = _disabled_reason(framework_spec)

    if sites_only_framework_refresh:
        vanilla_reason = (
            "--sites-only with --framework-sites refreshes framework output only — "
            "drop --framework-sites to also refresh vanilla HTML"
        )
    elif skip_vanilla:
        vanilla_reason = _disabled_reason(vanilla_spec)
    elif vanilla_flag:
        vanilla_reason = f"{vanilla_spec.enable_flag} was passed"
    else:
        vanilla_reason = f"{vanilla_spec.config_key} is true in the resolved config"

    mode_reason = ""
    if design_only:
        mode_reason = "--design-only stops after the design-system artifacts"
    elif surface_map_only:
        mode_reason = "--surface-map-only stops after the surface-component maps"

    plans: list[LanePlan] = []
    for spec, gate_open, reason, config_value in (
        (framework_spec, framework_enabled, framework_reason, bool(framework_config_value)),
        (vanilla_spec, not skip_vanilla, vanilla_reason, bool(vanilla_config_value)),
    ):
        if mode_reason:
            gate_open, reason = False, mode_reason
        matched = tuple(p for p in spec.providers if p in requested)
        if gate_open and not matched:
            # The gate is open but no provider this lane can build is in the run's
            # provider list, so it would still produce nothing. Name the file that
            # decides that.
            gate_open = False
            reason = (
                f"no provider this lane can build is in the run's provider list "
                f"({', '.join(requested) or 'empty'}); the lane builds "
                f"{', '.join(spec.providers)} — set site-generation-providers.txt"
            )
        built = matched if gate_open else ()
        plans.append(
            LanePlan(
                lane=spec.lane,
                label=spec.label,
                config_key=spec.config_key,
                enable_flag=spec.enable_flag,
                config_value=config_value,
                enabled=gate_open,
                reason=reason,
                providers=built,
                skipped_providers=tuple(p for p in spec.providers if p not in built),
            )
        )
    return plans


class LaneLedger:
    """Records what each lane actually did and derives the disclosure from it.

    Thread-safe: ``run_pipeline`` fans out over run items and providers, so
    targets are recorded from worker threads.
    """

    def __init__(
        self,
        plans: Iterable[LanePlan],
        *,
        expects_site_output: bool = True,
        mode: str = "full",
    ) -> None:
        self.plans: list[LanePlan] = list(plans)
        self.expects_site_output = bool(expects_site_output)
        self.mode = mode
        self._targets: list[LaneTarget] = []
        self._lock = threading.Lock()

    # ── recording ────────────────────────────────────────────────────────────

    def record(
        self,
        lane: str,
        provider: str,
        item: str,
        outcome: str,
        *,
        reason: str = "",
        output: str = "",
    ) -> None:
        if outcome not in _OUTCOME_PRECEDENCE:
            raise ValueError(f"unknown lane outcome: {outcome}")
        with self._lock:
            self._targets.append(
                LaneTarget(lane, provider, item, outcome, reason, output)
            )

    def record_disabled_lane(self, item: str) -> None:
        """Record every disabled lane's providers as skipped for one run item.

        Called from the item's own code path so a disabled lane is disclosed with
        the same provenance as an enabled one, instead of being inferred later
        from the plan alone.
        """
        for plan in self.plans:
            if plan.enabled:
                continue
            for provider in plan.spec.providers:
                self.record(
                    plan.lane,
                    provider,
                    item,
                    OUTCOME_SKIPPED_DISABLED,
                    reason=plan.reason,
                )

    def targets(self) -> list[LaneTarget]:
        with self._lock:
            return list(self._targets)

    def outcome_for(self, lane: str, provider: str, item: str) -> str | None:
        """The outcome one lane target reported, or ``None`` if it reported none.

        Lets a second surface — the per-run step statuses — be derived from the
        same records as the summary and the manifest, instead of assuming a step
        completed because it was submitted.
        """
        with self._lock:
            for target in reversed(self._targets):
                if (target.lane, target.provider, target.item) == (lane, provider, item):
                    return target.outcome
        return None

    # ── derivation ───────────────────────────────────────────────────────────

    def lane_rows(self) -> list[dict]:
        """One derived row per lane: its outcome, why, and the files it produced."""
        targets = self.targets()
        rows: list[dict] = []
        for plan in self.plans:
            mine = [t for t in targets if t.lane == plan.lane]
            present = {t.outcome for t in mine}
            outcome = next(
                (o for o in _OUTCOME_PRECEDENCE if o in present), OUTCOME_NOT_REACHED
            )
            reason = next(
                (t.reason for t in mine if t.outcome == outcome and t.reason), ""
            )
            if not reason and outcome != OUTCOME_PRODUCED:
                reason = plan.reason
            outputs = sorted({t.output for t in mine if t.output})
            built = {t.provider for t in mine if t.outcome == OUTCOME_PRODUCED}
            rows.append(
                {
                    **plan.to_dict(),
                    "outcome": outcome,
                    "outcomeReason": reason,
                    "outputs": outputs,
                    "outputCount": len(outputs),
                    # Every provider this lane can build that has no output, so the
                    # summary names the missing files rather than only the ones the
                    # plan had already ruled out.
                    "unbuiltProviders": sorted(set(plan.spec.providers) - built),
                    "targets": [t.to_dict() for t in mine],
                }
            )
        return rows

    def produced_output_count(self) -> int:
        return sum(1 for t in self.targets() if t.outcome == OUTCOME_PRODUCED)

    def no_output_failure_reason(self) -> str | None:
        """Why this run should fail for having produced no site output at all.

        ``None`` when the run either produced something or never intended to
        (``--design-only`` / ``--surface-map-only`` / ``--assets-only``), so an
        evidence-mining or extract-only invocation is never failed for doing
        exactly what it was asked to do.
        """
        if not self.expects_site_output:
            return None
        if self.produced_output_count():
            return None
        parts = []
        for row in self.lane_rows():
            parts.append(
                f"{row['label']}: {_OUTCOME_LABELS[row['outcome']]}"
                + (f" ({row['outcomeReason']})" if row["outcomeReason"] else "")
            )
        return (
            "no site-generation lane produced any output for this run — "
            + "; ".join(parts)
        )

    # ── rendering ────────────────────────────────────────────────────────────

    def plan_lines(self) -> list[str]:
        """The up-front disclosure: which lanes this run will take, and why not."""
        lines = ["Site generation lanes for this run:"]
        for plan in self.plans:
            if plan.enabled:
                lines.append(
                    f"  {plan.label} — ENABLED; will build "
                    + ", ".join(plan.artifacts())
                )
            else:
                lines.append(f"  {plan.label} — SKIPPED")
                lines.append(
                    "      no output for provider(s): "
                    + ", ".join(plan.spec.providers)
                )
            lines.append(f"      {plan.reason}")
        return lines

    def summary_lines(self) -> list[str]:
        """The end-of-run disclosure, derived from what every target reported."""
        lines = ["Site generation lane summary:"]
        for row in self.lane_rows():
            label = _OUTCOME_LABELS[row["outcome"]]
            head = f"  {row['label']} — {label}"
            if row["outcome"] == OUTCOME_PRODUCED:
                head += f" ({row['outputCount']} file(s))"
            lines.append(head)
            if row["outcomeReason"]:
                lines.append(f"      {row['outcomeReason']}")
            for output in row["outputs"]:
                lines.append(f"      wrote {output}")
            if row["outcome"] != OUTCOME_PRODUCED and row["unbuiltProviders"]:
                lines.append(
                    "      nothing built for provider(s): "
                    + ", ".join(row["unbuiltProviders"])
                )
        return lines

    def manifest_payload(self) -> dict:
        """The structured facts for ``manifest.json``, derived from the same rows
        the console summary renders."""
        rows = self.lane_rows()
        produced = self.produced_output_count()
        return {
            "schemaVersion": SCHEMA_VERSION,
            "mode": self.mode,
            "expectsSiteOutput": self.expects_site_output,
            "producedOutputCount": produced,
            "producedAnyOutput": bool(produced),
            "lanes": rows,
        }
