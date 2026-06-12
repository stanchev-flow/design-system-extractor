import tempfile
import unittest
from pathlib import Path

from run_pipeline import (
    DEFAULT_SITE_GENERATION_PROVIDERS,
    apply_version_model_overrides,
    parse_provider_list,
)
from screenshot_to_template.config import AppConfig, load_config


class RuntimeDefaultTests(unittest.TestCase):
    def test_app_config_defaults_to_gpt55_for_analysis_and_section_detection(self) -> None:
        config = AppConfig()

        self.assertEqual(config.provider, "openai")
        self.assertEqual(config.model, "gpt-5.5")
        self.assertEqual(config.reasoning_effort, "high")
        self.assertEqual(config.section_detection_provider, "openai")
        self.assertEqual(config.section_detection_model, "gpt-5.5")
        self.assertEqual(config.section_detection_reasoning_effort, "high")

    def test_load_config_defaults_to_gpt55(self) -> None:
        config = load_config()

        self.assertEqual(config.provider, "openai")
        self.assertEqual(config.model, "gpt-5.5")
        self.assertEqual(config.reasoning_effort, "high")
        self.assertEqual(config.section_detection_provider, "openai")
        self.assertEqual(config.section_detection_model, "gpt-5.5")
        self.assertEqual(config.section_detection_reasoning_effort, "high")

    def test_analysis_override_does_not_cascade_to_section_detection(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            version_dir = Path(temp_dir)
            (version_dir / "analysis-provider.txt").write_text("anthropic\n")
            (version_dir / "analysis-model.txt").write_text("claude-opus-4-1-20250805\n")
            config = AppConfig()

            apply_version_model_overrides(config, version_dir)

            self.assertEqual(config.provider, "anthropic")
            self.assertEqual(config.model, "claude-opus-4-1-20250805")
            self.assertEqual(config.section_detection_provider, "openai")
            self.assertEqual(config.section_detection_model, "gpt-5.5")
            self.assertEqual((version_dir / "section-detection-provider.txt").read_text().strip(), "openai")
            self.assertEqual((version_dir / "section-detection-model.txt").read_text().strip(), "gpt-5.5")
            self.assertEqual((version_dir / "section-detection-reasoning-effort.txt").read_text().strip(), "high")

    def test_site_generation_default_keeps_both_final_site_models(self) -> None:
        self.assertEqual(DEFAULT_SITE_GENERATION_PROVIDERS, ("claude", "gpt55"))
        self.assertEqual(parse_provider_list("gemini\n"), ["gpt55"])


if __name__ == "__main__":
    unittest.main()
