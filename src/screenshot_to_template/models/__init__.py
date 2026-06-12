from .base import LLMProvider


def get_provider(config) -> LLMProvider:
    """Factory function to create the appropriate LLM provider."""
    match config.provider:
        case "google":
            from .google import GoogleProvider
            return GoogleProvider(config.model)
        case "openai":
            from .openai import OpenAIProvider
            return OpenAIProvider(config.model, reasoning_effort=getattr(config, "reasoning_effort", None))
        case "anthropic":
            from .anthropic import AnthropicProvider
            return AnthropicProvider(config.model, reasoning_effort=getattr(config, "reasoning_effort", None))
        case _:
            raise ValueError(f"Unknown provider: {config.provider}")
