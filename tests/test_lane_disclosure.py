"""A run has to say which site-generation lanes it took, and which it did not.

The regression these lock down: with ``framework-generation-enabled: false`` in
``config.default.yaml`` (the always-loaded CLI baseline), a flagless run builds
zero framework sites and used to say nothing about it — no console line naming the
key or the flag, and nothing in ``manifest.json``. Every assertion below is about
that disclosure being present, accurate, and derived from what actually happened.
"""

import unittest

from screenshot_to_template.config import load_config
from screenshot_to_template.framework_generator import generation_blocked_error
from screenshot_to_template.lane_disclosure import (
    LANE_FRAMEWORK,
    LANE_VANILLA,
    OUTCOME_FAILED,
    OUTCOME_NOT_REACHED,
    OUTCOME_PRODUCED,
    OUTCOME_SKIPPED_DISABLED,
    OUTCOME_SKIPPED_GATE,
    OUTCOME_SKIPPED_NOT_REQUESTED,
    SCHEMA_VERSION,
    LaneLedger,
    plan_site_generation_lanes,
)

DEFAULT_PROVIDERS = ("claude",)


def baseline_plans(**overrides):
    """The lane plan for a flagless CLI run against the shipped defaults."""
    kwargs = {
        "framework_config_value": False,
        "framework_flag": False,
        "vanilla_config_value": False,
        "vanilla_flag": False,
        "providers": DEFAULT_PROVIDERS,
    }
    kwargs.update(overrides)
    return plan_site_generation_lanes(**kwargs)


def lane(plans, lane_id):
    return next(p for p in plans if p.lane == lane_id)


def row(ledger, lane_id):
    return next(r for r in ledger.lane_rows() if r["lane"] == lane_id)


class LanePlanTests(unittest.TestCase):
    def test_flagless_run_skips_the_framework_lane_and_says_so(self) -> None:
        plans = baseline_plans()
        framework = lane(plans, LANE_FRAMEWORK)

        self.assertFalse(framework.enabled)
        # The whole point: the reader can act without reading source.
        self.assertIn("framework-generation-enabled", framework.reason)
        self.assertIn("--framework-sites", framework.reason)
        self.assertEqual(framework.config_key, "framework-generation-enabled")
        self.assertEqual(framework.enable_flag, "--framework-sites")

    def test_flagless_run_still_takes_the_vanilla_lane(self) -> None:
        # vanilla-site-generation-enabled is false too, but it only suppresses the
        # vanilla lane while framework generation is on. Disclose that, don't
        # pretend the key was honoured.
        vanilla = lane(baseline_plans(), LANE_VANILLA)

        self.assertTrue(vanilla.enabled)
        self.assertEqual(vanilla.artifacts(), ("site-claude.html",))
        self.assertIn("framework generation is off", vanilla.reason)

    def test_framework_sites_flag_turns_the_lane_on_and_skips_vanilla(self) -> None:
        plans = baseline_plans(framework_flag=True)

        self.assertTrue(lane(plans, LANE_FRAMEWORK).enabled)
        self.assertEqual(
            lane(plans, LANE_FRAMEWORK).artifacts(), ("site-claude-framework.html",)
        )
        vanilla = lane(plans, LANE_VANILLA)
        self.assertFalse(vanilla.enabled)
        self.assertIn("vanilla-site-generation-enabled", vanilla.reason)
        self.assertIn("--vanilla-sites", vanilla.reason)

    def test_both_flags_enable_both_lanes(self) -> None:
        plans = baseline_plans(framework_flag=True, vanilla_flag=True)

        self.assertTrue(lane(plans, LANE_FRAMEWORK).enabled)
        self.assertTrue(lane(plans, LANE_VANILLA).enabled)

    def test_studio_style_config_enables_framework_without_a_flag(self) -> None:
        plans = baseline_plans(framework_config_value=True)

        framework = lane(plans, LANE_FRAMEWORK)
        self.assertTrue(framework.enabled)
        self.assertIn("framework-generation-enabled is true", framework.reason)

    def test_design_only_disables_both_lanes_with_the_mode_as_the_reason(self) -> None:
        plans = baseline_plans(framework_flag=True, vanilla_flag=True, design_only=True)

        for plan in plans:
            self.assertFalse(plan.enabled)
            self.assertIn("--design-only", plan.reason)

    def test_a_lane_no_provider_can_build_names_the_provider_file(self) -> None:
        plans = plan_site_generation_lanes(
            framework_config_value=True,
            framework_flag=False,
            vanilla_config_value=True,
            vanilla_flag=False,
            providers=(),
        )

        framework = lane(plans, LANE_FRAMEWORK)
        self.assertFalse(framework.enabled)
        self.assertIn("site-generation-providers.txt", framework.reason)

    def test_sites_only_framework_refresh_explains_the_vanilla_skip(self) -> None:
        plans = baseline_plans(framework_flag=True, vanilla_flag=True, sites_only=True)

        vanilla = lane(plans, LANE_VANILLA)
        self.assertFalse(vanilla.enabled)
        # --vanilla-sites does not win here, and the reason says which flag does.
        self.assertIn("--sites-only", vanilla.reason)
        self.assertIn("--framework-sites", vanilla.reason)

    def test_a_generating_run_always_has_at_least_one_lane(self) -> None:
        # The interlock the up-front refusal relies on: vanilla is only suppressed
        # while framework is on, so no combination of the two keys/flags leaves a
        # generating run with nothing to build. If this ever stops holding, the
        # refusal in run_pipeline is what a reader sees instead of an empty run.
        for framework_key in (False, True):
            for framework_flag in (False, True):
                for vanilla_key in (False, True):
                    for vanilla_flag in (False, True):
                        plans = plan_site_generation_lanes(
                            framework_config_value=framework_key,
                            framework_flag=framework_flag,
                            vanilla_config_value=vanilla_key,
                            vanilla_flag=vanilla_flag,
                            providers=DEFAULT_PROVIDERS,
                        )
                        with self.subTest(
                            framework_key=framework_key,
                            framework_flag=framework_flag,
                            vanilla_key=vanilla_key,
                            vanilla_flag=vanilla_flag,
                        ):
                            self.assertTrue(any(p.enabled for p in plans))

    def test_shipped_cli_default_really_is_framework_off(self) -> None:
        # Ties the disclosure to the real config rather than a fixture: if the
        # baseline default ever flips, this test and the README disagree loudly.
        config = load_config()
        plans = baseline_plans(
            framework_config_value=bool(config.framework_generation_enabled),
            vanilla_config_value=bool(config.vanilla_site_generation_enabled),
        )

        self.assertFalse(config.framework_generation_enabled)
        self.assertFalse(lane(plans, LANE_FRAMEWORK).enabled)


class LaneLedgerTests(unittest.TestCase):
    def test_produced_lane_reports_the_files_it_wrote(self) -> None:
        ledger = LaneLedger(baseline_plans())
        ledger.record(
            LANE_VANILLA,
            "claude",
            "hatch",
            OUTCOME_PRODUCED,
            output="hatch/single/site-claude.html",
        )

        vanilla = row(ledger, LANE_VANILLA)
        self.assertEqual(vanilla["outcome"], OUTCOME_PRODUCED)
        self.assertEqual(vanilla["outputs"], ["hatch/single/site-claude.html"])
        self.assertEqual(ledger.produced_output_count(), 1)

    def test_disabled_lane_is_recorded_per_provider_with_the_plan_reason(self) -> None:
        ledger = LaneLedger(baseline_plans())
        ledger.record_disabled_lane("hatch")

        framework = row(ledger, LANE_FRAMEWORK)
        self.assertEqual(framework["outcome"], OUTCOME_SKIPPED_DISABLED)
        self.assertEqual(
            sorted(t["provider"] for t in framework["targets"]), ["claude", "gpt55"]
        )
        self.assertEqual(framework["outputs"], [])
        # The vanilla lane is enabled, so record_disabled_lane must not touch it.
        self.assertEqual(row(ledger, LANE_VANILLA)["outcome"], OUTCOME_NOT_REACHED)

    def test_gate_refusal_is_not_reported_as_a_failure(self) -> None:
        ledger = LaneLedger(baseline_plans(framework_flag=True))
        ledger.record(
            LANE_FRAMEWORK,
            "claude",
            "hubspot",
            OUTCOME_SKIPPED_GATE,
            reason="framework generation refused for hubspot at G4 (replica)",
        )

        framework = row(ledger, LANE_FRAMEWORK)
        self.assertEqual(framework["outcome"], OUTCOME_SKIPPED_GATE)
        self.assertIn("G4 (replica)", framework["outcomeReason"])

    def test_failure_outranks_a_skip_within_one_lane(self) -> None:
        ledger = LaneLedger(baseline_plans())
        ledger.record(
            LANE_VANILLA, "gpt55", "hatch", OUTCOME_SKIPPED_NOT_REQUESTED, reason="n/a"
        )
        ledger.record(LANE_VANILLA, "claude", "hatch", OUTCOME_FAILED, reason="boom")

        self.assertEqual(row(ledger, LANE_VANILLA)["outcome"], OUTCOME_FAILED)
        self.assertEqual(row(ledger, LANE_VANILLA)["outcomeReason"], "boom")

    def test_real_output_outranks_a_sibling_failure(self) -> None:
        ledger = LaneLedger(baseline_plans())
        ledger.record(LANE_VANILLA, "gpt55", "a", OUTCOME_FAILED, reason="boom")
        ledger.record(
            LANE_VANILLA, "claude", "b", OUTCOME_PRODUCED, output="b/single/site.html"
        )

        self.assertEqual(row(ledger, LANE_VANILLA)["outcome"], OUTCOME_PRODUCED)

    def test_unknown_outcome_is_rejected(self) -> None:
        ledger = LaneLedger(baseline_plans())

        with self.assertRaises(ValueError):
            ledger.record(LANE_VANILLA, "claude", "hatch", "went_fine")


class LaneSummaryTests(unittest.TestCase):
    def summary(self, ledger) -> str:
        return "\n".join(ledger.summary_lines())

    def test_skipped_because_disabled_names_the_key_and_the_flag(self) -> None:
        ledger = LaneLedger(baseline_plans())
        ledger.record_disabled_lane("hatch")
        ledger.record(
            LANE_VANILLA,
            "claude",
            "hatch",
            OUTCOME_PRODUCED,
            output="hatch/single/site-claude.html",
        )
        text = self.summary(ledger)

        self.assertIn("Site generation lane summary:", text)
        self.assertIn("framework sites (React + Tailwind v4)", text)
        self.assertIn("SKIPPED — disabled in config", text)
        self.assertIn("framework-generation-enabled", text)
        self.assertIn("--framework-sites", text)
        self.assertIn("nothing built for provider(s): claude, gpt55", text)
        self.assertIn("wrote hatch/single/site-claude.html", text)
        # The failure verdict belongs to the caller, not to the per-lane rows, so
        # it is not repeated inside the summary.
        self.assertNotIn("no site-generation lane produced", text)

    def test_plan_lines_state_the_lanes_before_any_model_work(self) -> None:
        text = "\n".join(LaneLedger(baseline_plans()).plan_lines())

        self.assertIn("Site generation lanes for this run:", text)
        self.assertIn("vanilla one-shot HTML — ENABLED", text)
        self.assertIn("will build site-claude.html", text)
        self.assertIn("framework sites (React + Tailwind v4) — SKIPPED", text)

    def test_summary_and_manifest_carry_the_same_facts(self) -> None:
        ledger = LaneLedger(baseline_plans())
        ledger.record_disabled_lane("hatch")
        ledger.record(
            LANE_VANILLA,
            "claude",
            "hatch",
            OUTCOME_PRODUCED,
            output="hatch/single/site-claude.html",
        )
        payload = ledger.manifest_payload()
        framework = next(r for r in payload["lanes"] if r["lane"] == LANE_FRAMEWORK)

        self.assertEqual(payload["schemaVersion"], SCHEMA_VERSION)
        self.assertTrue(payload["producedAnyOutput"])
        self.assertEqual(payload["producedOutputCount"], 1)
        self.assertEqual(framework["outcome"], OUTCOME_SKIPPED_DISABLED)
        self.assertEqual(framework["unbuiltProviders"], ["claude", "gpt55"])
        self.assertEqual(framework["configKey"], "framework-generation-enabled")
        self.assertEqual(framework["enableFlag"], "--framework-sites")
        self.assertFalse(framework["configValue"])
        self.assertIn("--framework-sites", framework["outcomeReason"])
        self.assertIn(framework["outcomeReason"], self.summary(ledger))


class NoOutputFailureTests(unittest.TestCase):
    def test_a_run_that_produced_nothing_reports_a_failure_reason(self) -> None:
        ledger = LaneLedger(baseline_plans())
        ledger.record_disabled_lane("hatch")
        ledger.record(
            LANE_VANILLA, "claude", "hatch", OUTCOME_FAILED, reason="provider timeout"
        )
        reason = ledger.no_output_failure_reason()

        self.assertIsNotNone(reason)
        self.assertIn("no site-generation lane produced any output", reason)
        self.assertIn("provider timeout", reason)
        self.assertIn("framework-generation-enabled", reason)

    def test_a_run_with_output_has_no_failure_reason(self) -> None:
        ledger = LaneLedger(baseline_plans())
        ledger.record(
            LANE_VANILLA, "claude", "hatch", OUTCOME_PRODUCED, output="a/site.html"
        )

        self.assertIsNone(ledger.no_output_failure_reason())

    def test_extract_only_modes_are_never_failed_for_producing_no_site(self) -> None:
        # --design-only / --surface-map-only / --assets-only legitimately generate
        # no site. Failing them would break evidence-mining invocations.
        ledger = LaneLedger(
            baseline_plans(design_only=True),
            expects_site_output=False,
            mode="design-only",
        )
        ledger.record_disabled_lane("hatch")

        self.assertIsNone(ledger.no_output_failure_reason())
        self.assertFalse(ledger.manifest_payload()["expectsSiteOutput"])
        self.assertEqual(ledger.manifest_payload()["mode"], "design-only")


class GateErrorTests(unittest.TestCase):
    def test_the_gate_refusal_class_is_reachable_without_importing_the_flow(self) -> None:
        # run_pipeline catches this to tell a gate REFUSAL apart from a FAILURE.
        blocked = generation_blocked_error()

        self.assertTrue(issubclass(blocked, Exception))
        self.assertEqual(blocked.__name__, "GenerationBlocked")


if __name__ == "__main__":
    unittest.main()
