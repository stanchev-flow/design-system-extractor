"""Configuration loading and management."""

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from . import prompts


DEFAULT_MODELS = {
    "google": "gemini-2.5-pro",
    "openai": "gpt-5.5",
    "anthropic": "claude-opus-4-1-20250805",
}

DEFAULT_PROVIDER = "openai"
DEFAULT_MODEL = "gpt-5.5"
DEFAULT_REASONING_EFFORT = "high"
DEFAULT_SECTION_DETECTION_PROVIDER = "openai"
DEFAULT_SECTION_DETECTION_MODEL = "gpt-5.5"
DEFAULT_SECTION_DETECTION_REASONING_EFFORT = "high"


@dataclass
class AppConfig:
    provider: str = DEFAULT_PROVIDER
    model: str = DEFAULT_MODEL
    reasoning_effort: str | None = DEFAULT_REASONING_EFFORT
    site_asset_generation_enabled: bool = True
    site_asset_image_model: str = "gpt-image-2"
    site_asset_generation_workers: int = 3
    # Optional path to a harvested + role-mapped brand-asset manifest. When set,
    # generated pages have their `data-stt-asset-brief` slots filled with the
    # brand's own assets as a post-generation step. Relative paths resolve from
    # the project root.
    brand_assets_manifest: str = ""
    # Framework-first: build React/Tailwind packages; vanilla one-shot HTML off by default.
    framework_generation_enabled: bool = True
    vanilla_site_generation_enabled: bool = False
    # Optional path to source_chrome.json (nav/footer 1:1 contract from live URL).
    source_chrome_contract: str = ""
    surface_map_mode: str = "auto"
    run_reviews: bool = False
    section_detection_provider: str = DEFAULT_SECTION_DETECTION_PROVIDER
    section_detection_model: str = DEFAULT_SECTION_DETECTION_MODEL
    section_detection_reasoning_effort: str | None = DEFAULT_SECTION_DETECTION_REASONING_EFFORT
    structural_analysis_prompt: str = ""
    system_prompt: str = ""
    merge_prompt: str = ""
    section_inventory_prompt: str = ""
    section_window_inventory_prompt: str = ""
    section_detection_prompt: str = ""
    section_window_detection_prompt: str = ""
    section_analysis_prompt: str = ""
    max_image_dimension: int = 2048
    auto_chunk_tall_section_detection: bool = True
    auto_two_chunk_threshold_height: int = 22000
    auto_three_chunk_threshold_height: int = 999999
    auto_chunk_overlap: int = 1600
    use_local_inventory_per_chunk: bool = False
    chunked_section_detection: bool = False
    section_detection_chunk_height: int = 2400
    section_detection_chunk_overlap: int = 400
    section_detection_chunk_trigger_height: int = 3200
    chunk_ruler_major_step: int = 50
    chunk_ruler_minor_step: int = 25
    chunk_boundary_cluster_tolerance: int = 90
    max_tokens: int = 4096
    verbose: bool = False

    def __post_init__(self):
        if not self.model:
            self.model = DEFAULT_MODELS.get(self.provider, DEFAULT_MODEL)
        if not self.section_detection_model:
            self.section_detection_model = DEFAULT_MODELS.get(
                self.section_detection_provider, DEFAULT_SECTION_DETECTION_MODEL
            )
        if not self.structural_analysis_prompt:
            self.structural_analysis_prompt = prompts.DEFAULT_STRUCTURAL_ANALYSIS_PROMPT
        if not self.system_prompt:
            self.system_prompt = prompts.DEFAULT_SYSTEM_PROMPT
        if not self.merge_prompt:
            self.merge_prompt = prompts.DEFAULT_MERGE_PROMPT
        if not self.section_inventory_prompt:
            self.section_inventory_prompt = prompts.SECTION_INVENTORY_PROMPT
        if not self.section_window_inventory_prompt:
            self.section_window_inventory_prompt = prompts.SECTION_WINDOW_INVENTORY_PROMPT
        if not self.section_detection_prompt:
            self.section_detection_prompt = prompts.SECTION_DETECTION_PROMPT
        if not self.section_window_detection_prompt:
            self.section_window_detection_prompt = prompts.SECTION_WINDOW_BOUNDARY_PROMPT
        if not self.section_analysis_prompt:
            self.section_analysis_prompt = prompts.DEFAULT_SECTION_ANALYSIS_PROMPT


def load_config(config_path: str | None = None) -> AppConfig:
    """Load configuration from YAML file, falling back to defaults."""
    config_data = {}

    # Load default config bundled with package
    default_path = Path(__file__).parent.parent.parent / "config.default.yaml"
    if default_path.exists():
        with open(default_path) as f:
            config_data = yaml.safe_load(f) or {}

    # Override with user config
    if config_path and os.path.exists(config_path):
        with open(config_path) as f:
            user_data = yaml.safe_load(f) or {}
            config_data.update(user_data)

    # Map YAML keys to dataclass fields (convert hyphens to underscores)
    normalized = {}
    for key, value in config_data.items():
        normalized[key.replace("-", "_")] = value

    # Only pass known fields
    known_fields = {f.name for f in AppConfig.__dataclass_fields__.values()}
    filtered = {k: v for k, v in normalized.items() if k in known_fields}

    return AppConfig(**filtered)
