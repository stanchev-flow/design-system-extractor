"""Google Gemini provider."""

import base64
import os
from pathlib import Path

from google import genai
from google.genai import types

from .base import LLMProvider
from ..tracking import log_usage_if_context


def _load_shared_google_api_key() -> str | None:
    """Load Gemini/Google API key using the same local env fallback as pipeline scripts."""
    existing = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if existing:
        return existing

    env_file = Path(__file__).resolve().parents[3] / ".env.local"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if "=" not in line or line.startswith("#"):
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            if key == "GOOGLE_API_KEY" and value and not os.environ.get("GOOGLE_API_KEY"):
                os.environ["GOOGLE_API_KEY"] = value
            if key == "GEMINI_API_KEY" and value and not os.environ.get("GEMINI_API_KEY"):
                os.environ["GEMINI_API_KEY"] = value

    if not os.environ.get("GOOGLE_API_KEY") and os.environ.get("GEMINI_API_KEY"):
        os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]
    return os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")


class GoogleProvider(LLMProvider):
    def __init__(self, model: str = "gemini-2.5-pro"):
        super().__init__(model)
        # Support both GOOGLE_API_KEY and GEMINI_API_KEY
        api_key = _load_shared_google_api_key()
        if not api_key:
            raise ValueError(
                "Google API key not found. Set GOOGLE_API_KEY or GEMINI_API_KEY environment variable."
            )
        self.client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                timeout=300_000,
                retry_options=types.HttpRetryOptions(
                    attempts=3,
                    initial_delay=1.0,
                    max_delay=8.0,
                ),
            ),
        )

    def analyze_image(
        self,
        image_b64: str,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096,
        json_mode: bool = False,
        additional_images: list[tuple[str, str]] | None = None,
    ) -> str:
        parts = [types.Part.from_text(text=user_prompt)]
        all_images = [image_b64] + [img_b64 for _, img_b64 in (additional_images or [])]
        for img_b64 in all_images:
            image_bytes = base64.b64decode(img_b64)
            parts.append(types.Part.from_bytes(data=image_bytes, mime_type="image/png"))

        config_kwargs = dict(
            system_instruction=system_prompt,
            max_output_tokens=max_tokens,
        )
        if json_mode:
            config_kwargs["response_mime_type"] = "application/json"
        response = self.client.models.generate_content(
            model=self.model,
            contents=[
                types.Content(
                    parts=parts
                )
            ],
            config=types.GenerateContentConfig(**config_kwargs),
        )
        usage = getattr(response, "usage_metadata", None)
        self.last_usage = {
            "input_tokens": getattr(usage, "prompt_token_count", None),
            "output_tokens": getattr(usage, "candidates_token_count", None),
            "total_tokens": getattr(usage, "total_token_count", None),
        }
        log_usage_if_context("google", self.model, self.last_usage)
        return response.text or ""

    def text_query(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096,
    ) -> str:
        response = self.client.models.generate_content(
            model=self.model,
            contents=[user_prompt],
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                max_output_tokens=max_tokens,
                thinking_config=types.ThinkingConfig(
                    include_thoughts=False,
                ),
            ),
        )
        usage = getattr(response, "usage_metadata", None)
        self.last_usage = {
            "input_tokens": getattr(usage, "prompt_token_count", None),
            "output_tokens": getattr(usage, "candidates_token_count", None),
            "total_tokens": getattr(usage, "total_token_count", None),
        }
        log_usage_if_context("google", self.model, self.last_usage)
        return response.text or ""

    def generate_image(
        self,
        prompt: str,
        *,
        aspect_ratio: str = "1:1",
        image_size: str = "1K",
        output_mime_type: str = "image/png",
        transparent_background: bool = True,
        reference_image_paths: list[Path] | None = None,
    ) -> tuple[bytes, str]:
        """Generate a bitmap image with a Gemini image-capable model."""
        parts = [types.Part.from_text(text=prompt)]
        for path in reference_image_paths or []:
            parts.append(types.Part.from_bytes(data=Path(path).read_bytes(), mime_type="image/png"))
        response = self.client.models.generate_content(
            model=self.model,
            contents=[
                types.Content(
                    parts=parts
                )
            ],
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(
                    aspect_ratio=aspect_ratio,
                    image_size=image_size,
                ),
            ),
        )

        usage = getattr(response, "usage_metadata", None)
        self.last_usage = {
            "input_tokens": getattr(usage, "prompt_token_count", None),
            "output_tokens": getattr(usage, "candidates_token_count", None),
            "total_tokens": getattr(usage, "total_token_count", None),
        }
        log_usage_if_context("google", self.model, self.last_usage)

        parts = list(getattr(response, "parts", []) or [])
        if not parts:
            candidates = getattr(response, "candidates", []) or []
            if candidates:
                content = getattr(candidates[0], "content", None)
                parts = list(getattr(content, "parts", []) or [])

        for part in parts:
            inline_data = getattr(part, "inline_data", None)
            if inline_data and getattr(inline_data, "data", None):
                return inline_data.data, getattr(inline_data, "mime_type", output_mime_type) or output_mime_type

        raise ValueError("Gemini image generation returned no image payload")
