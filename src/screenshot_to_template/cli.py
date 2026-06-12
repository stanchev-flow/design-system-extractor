"""CLI entry point for screenshot-to-template."""

import argparse
import sys
from pathlib import Path

from .config import load_config
from .output import write_output


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="screenshot-to-template",
        description="Convert website screenshots into text-based design systems.",
    )
    parser.add_argument(
        "screenshot",
        help="Path to the website screenshot image",
    )
    parser.add_argument(
        "--mode",
        choices=["single"],
        default="single",
        help="Analysis mode. Only 'single' is supported.",
    )
    parser.add_argument(
        "-o", "--output",
        default="design-system.md",
        help="Output markdown file path (default: design-system.md)",
    )
    parser.add_argument(
        "-c", "--config",
        default=None,
        help="Path to custom YAML config file",
    )
    parser.add_argument(
        "--provider",
        choices=["google", "openai", "anthropic"],
        default=None,
        help="LLM provider (default: openai)",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Model name override (e.g., gemini-2.5-pro, gpt-5.5, claude-sonnet-4-20250514)",
    )
    parser.add_argument(
        "--section-detection-provider",
        choices=["google", "openai", "anthropic"],
        default=None,
        help="Provider override just for section boundary detection",
    )
    parser.add_argument(
        "--section-detection-model",
        default=None,
        help="Model override just for section boundary detection",
    )
    parser.add_argument(
        "--system-prompt",
        default=None,
        help="Override the system prompt inline",
    )
    parser.add_argument(
        "--surface-map-mode",
        choices=["auto", "model", "contract", "skip"],
        default=None,
        help="Surface/component intermediate mode for pipelines that support it",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Print progress info to stderr",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    output_path = Path(args.output)

    # Validate screenshot exists
    if not Path(args.screenshot).exists():
        print(f"Error: Screenshot not found: {args.screenshot}", file=sys.stderr)
        sys.exit(1)

    # Load config
    config = load_config(args.config)

    # Apply CLI overrides
    if args.provider:
        config.provider = args.provider
        # Reset model to default for new provider unless explicitly set
        if not args.model:
            from .config import DEFAULT_MODELS
            config.model = DEFAULT_MODELS.get(args.provider, config.model)
    if args.model:
        config.model = args.model
    if args.section_detection_provider:
        config.section_detection_provider = args.section_detection_provider
        if not args.section_detection_model:
            from .config import DEFAULT_MODELS
            config.section_detection_model = DEFAULT_MODELS.get(
                args.section_detection_provider, config.section_detection_model
            )
    if args.section_detection_model:
        config.section_detection_model = args.section_detection_model
    if args.system_prompt:
        config.system_prompt = args.system_prompt
    if args.surface_map_mode:
        config.surface_map_mode = args.surface_map_mode
    config.verbose = args.verbose

    # Run the active single pipeline
    from .pipeline.single_shot import run
    result = run(args.screenshot, config)

    # Write output
    write_output(result, str(output_path))

    if config.verbose:
        print(f"Design system written to: {output_path}", file=sys.stderr)
    else:
        print(f"Output: {output_path}")


if __name__ == "__main__":
    main()
