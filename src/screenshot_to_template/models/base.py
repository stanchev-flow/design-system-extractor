"""Abstract base class for LLM providers."""

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    def __init__(self, model: str):
        self.model = model
        self.last_usage: dict | None = None

    @abstractmethod
    def analyze_image(
        self,
        image_b64: str,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096,
        json_mode: bool = False,
        additional_images: list[tuple[str, str]] | None = None,
    ) -> str:
        """Send a base64-encoded image with prompts, return text response."""
        ...

    @abstractmethod
    def text_query(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096,
    ) -> str:
        """Send a text-only query, return text response."""
        ...
