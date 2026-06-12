"""OpenAI provider."""

import base64
import os
from contextlib import ExitStack
from pathlib import Path

import requests
from openai import BadRequestError, OpenAI

from .base import LLMProvider
from ..tracking import log_usage_if_context


def _load_shared_openai_api_key() -> str | None:
    """Load OpenAI API key using the same local env fallback as pipeline scripts."""
    existing = os.environ.get("OPENAI_API_KEY")
    if existing:
        return existing

    env_file = Path(__file__).resolve().parents[3] / ".env.local"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if "=" not in line or line.startswith("#"):
                continue
            key, _, value = line.partition("=")
            if key.strip() == "OPENAI_API_KEY" and value.strip():
                os.environ["OPENAI_API_KEY"] = value.strip()
                return os.environ["OPENAI_API_KEY"]
    return None


class OpenAIProvider(LLMProvider):
    def __init__(self, model: str = "gpt-5.5", reasoning_effort: str | None = None):
        super().__init__(model)
        api_key = _load_shared_openai_api_key()
        if not api_key:
            raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY environment variable.")
        timeout_seconds = float(os.environ.get("STT_OPENAI_TIMEOUT_SECONDS", "420"))
        max_retries = int(os.environ.get("STT_OPENAI_MAX_RETRIES", "1"))
        self.client = OpenAI(
            api_key=api_key,
            timeout=timeout_seconds,
            max_retries=max_retries,
        )
        self.image_detail = "high"
        self.reasoning_effort = reasoning_effort

    def _record_usage(self, response) -> None:
        usage = getattr(response, "usage", None)
        self.last_usage = {
            "input_tokens": getattr(usage, "prompt_tokens", None),
            "output_tokens": getattr(usage, "completion_tokens", None),
            "total_tokens": getattr(usage, "total_tokens", None),
        }
        log_usage_if_context("openai", self.model, self.last_usage)

    @staticmethod
    def _extract_message_text(response) -> str:
        content = response.choices[0].message.content
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for part in content:
                if isinstance(part, str):
                    parts.append(part)
                    continue
                text = getattr(part, "text", None)
                if text:
                    parts.append(text)
                    continue
                if isinstance(part, dict) and part.get("type") == "text" and part.get("text"):
                    parts.append(part["text"])
            return "".join(parts)
        return content or ""

    @staticmethod
    def _reasoning_exhausted_without_output(response, text: str, max_tokens: int) -> bool:
        if text.strip():
            return False
        choice = response.choices[0]
        if getattr(choice, "finish_reason", None) != "length":
            return False
        usage = getattr(response, "usage", None)
        details = getattr(usage, "completion_tokens_details", None)
        reasoning_tokens = getattr(details, "reasoning_tokens", None)
        return reasoning_tokens is not None and reasoning_tokens >= max_tokens

    def analyze_image(
        self,
        image_b64: str,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096,
        json_mode: bool = False,
        additional_images: list[tuple[str, str]] | None = None,
    ) -> str:
        content = [{"type": "text", "text": user_prompt}]
        all_images = [image_b64] + [img_b64 for _, img_b64 in (additional_images or [])]
        for img_b64 in all_images:
            content.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{img_b64}",
                        "detail": self.image_detail,
                    },
                }
            )

        kwargs = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content},
            ],
            "max_completion_tokens": max_tokens,
        }
        if self.reasoning_effort:
            kwargs["reasoning_effort"] = self.reasoning_effort
        response = self.client.chat.completions.create(**kwargs)
        self._record_usage(response)
        return self._extract_message_text(response)

    def text_query(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096,
    ) -> str:
        kwargs = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_completion_tokens": max_tokens,
        }
        if self.reasoning_effort:
            kwargs["reasoning_effort"] = self.reasoning_effort
        response = self.client.chat.completions.create(**kwargs)
        text = self._extract_message_text(response)
        self._record_usage(response)

        if self.reasoning_effort and self._reasoning_exhausted_without_output(response, text, max_tokens):
            retry_kwargs = dict(kwargs)
            retry_kwargs.pop("reasoning_effort", None)
            response = self.client.chat.completions.create(**retry_kwargs)
            text = self._extract_message_text(response)
            self._record_usage(response)

        return text

    @staticmethod
    def _image_size_for_openai(aspect_ratio: str, image_size: str) -> str:
        if image_size == "1K":
            return "1024x1024"
        if aspect_ratio in {"16:9", "4:3", "3:2"}:
            return "1536x1024"
        if aspect_ratio in {"9:16", "3:4", "2:3"}:
            return "1024x1536"
        return "1024x1024"

    def supports_transparent_image_background(self) -> bool:
        """Return whether this OpenAI image model accepts background=transparent."""
        return self.model != "gpt-image-2"

    def _generate_gpt_image(
        self,
        prompt: str,
        *,
        aspect_ratio: str,
        image_size: str,
        output_mime_type: str,
        transparent_background: bool,
        reference_image_paths: list[Path] | None = None,
    ) -> tuple[bytes, str]:
        """Generate an image with GPT image models, which always return base64."""
        request = {
            "model": self.model,
            "prompt": prompt,
            "size": self._image_size_for_openai(aspect_ratio, image_size),
            "n": 1,
            "output_format": "png",
            "background": "transparent" if transparent_background else "opaque",
            "quality": "high" if image_size == "2K" else "medium",
        }
        try:
            if reference_image_paths:
                with ExitStack() as stack:
                    request["image"] = [
                        stack.enter_context(open(path, "rb"))
                        for path in reference_image_paths
                    ]
                    response = self.client.images.edit(**request)
            else:
                response = self.client.images.generate(**request)
        except BadRequestError as exc:
            message = str(exc).lower()
            if transparent_background and "transparent background is not supported" in message:
                request["background"] = "opaque"
                request.pop("image", None)
                request.pop("input_fidelity", None)
                if reference_image_paths:
                    with ExitStack() as stack:
                        request["image"] = [
                            stack.enter_context(open(path, "rb"))
                            for path in reference_image_paths
                        ]
                        response = self.client.images.edit(**request)
                else:
                    response = self.client.images.generate(**request)
            else:
                raise
        self.last_usage = None
        log_usage_if_context("openai", self.model, None)

        if not response.data:
            raise ValueError("OpenAI image generation returned no image payload")
        b64_json = getattr(response.data[0], "b64_json", None)
        if not b64_json:
            raise ValueError("OpenAI image generation returned no base64 image payload")
        return base64.b64decode(b64_json), output_mime_type

    def _generate_dalle_image(
        self,
        prompt: str,
        *,
        aspect_ratio: str,
        image_size: str,
        output_mime_type: str,
    ) -> tuple[bytes, str]:
        """Generate an image with DALL-E models, which still support response_format."""
        response = self.client.images.generate(
            model=self.model,
            prompt=prompt,
            size=self._image_size_for_openai(aspect_ratio, image_size),
            n=1,
            response_format="b64_json",
        )
        self.last_usage = None
        log_usage_if_context("openai", self.model, None)

        if not response.data:
            raise ValueError("OpenAI image generation returned no image payload")
        item = response.data[0]
        b64_json = getattr(item, "b64_json", None)
        if b64_json:
            return base64.b64decode(b64_json), output_mime_type

        url = getattr(item, "url", None)
        if not url:
            raise ValueError("OpenAI image generation returned no base64 image payload")
        fetched = requests.get(url, timeout=60)
        fetched.raise_for_status()
        return fetched.content, fetched.headers.get("content-type") or output_mime_type

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
        """Generate a bitmap image with an OpenAI image-capable model."""
        if self.model.startswith("gpt-image"):
            return self._generate_gpt_image(
                prompt,
                aspect_ratio=aspect_ratio,
                image_size=image_size,
                output_mime_type=output_mime_type,
                transparent_background=transparent_background,
                reference_image_paths=reference_image_paths,
            )

        return self._generate_dalle_image(
            prompt,
            aspect_ratio=aspect_ratio,
            image_size=image_size,
            output_mime_type=output_mime_type,
        )
