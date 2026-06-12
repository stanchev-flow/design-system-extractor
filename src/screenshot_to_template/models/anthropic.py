"""Anthropic Claude provider."""

import anthropic

from .base import LLMProvider
from ..tracking import log_usage_if_context


class AnthropicProvider(LLMProvider):
    def __init__(self, model: str = "claude-opus-4-1-20250805", reasoning_effort: str | None = None):
        super().__init__(model)
        # HTML generation can stream for a while; use an explicit, longer timeout.
        self.client = anthropic.Anthropic(timeout=300.0, max_retries=2)
        self.reasoning_effort = reasoning_effort

    def _clamp_max_tokens(self, max_tokens: int) -> int:
        # Claude Opus rejects requests above 32000 output tokens.
        return min(max_tokens, 32000)

    def _thinking_config(self, max_tokens: int) -> dict | None:
        effort = (self.reasoning_effort or "").strip().lower()
        if not effort:
            return None
        if effort in {"none", "off", "disabled", "false"}:
            return {"type": "disabled"}
        if effort in {"adaptive", "thinking", "auto"}:
            return {"type": "adaptive", "display": "omitted"}

        # Newer models (Opus 4.7+, Fable) reject "thinking.type.enabled" with an
        # explicit budget and require adaptive thinking instead.
        model = (self.model or "").lower()
        if any(tag in model for tag in ("opus-4-8", "opus-4-7", "fable")):
            return {"type": "adaptive", "display": "omitted"}

        budget_by_effort = {
            "minimal": 512,
            "low": 1024,
            "medium": 2048,
            "high": 4096,
            "xhigh": 8192,
        }
        budget = budget_by_effort.get(effort, 4096)
        max_budget = max(1, self._clamp_max_tokens(max_tokens) - 1024)
        return {
            "type": "enabled",
            "budget_tokens": min(budget, max_budget),
            "display": "omitted",
        }

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
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": img_b64,
                    },
                }
            )

        result = ""
        kwargs = {
            "model": self.model,
            "max_tokens": self._clamp_max_tokens(max_tokens),
            "system": system_prompt,
            "messages": [{"role": "user", "content": content}],
        }
        thinking = self._thinking_config(max_tokens)
        if thinking:
            kwargs["thinking"] = thinking

        with self.client.messages.stream(**kwargs) as stream:
            for text in stream.text_stream:
                result += text
            final_message = stream.get_final_message()
        usage = getattr(final_message, "usage", None)
        self.last_usage = {
            "input_tokens": getattr(usage, "input_tokens", None),
            "output_tokens": getattr(usage, "output_tokens", None),
            "cache_creation_input_tokens": getattr(usage, "cache_creation_input_tokens", None),
            "cache_read_input_tokens": getattr(usage, "cache_read_input_tokens", None),
        }
        log_usage_if_context("anthropic", self.model, self.last_usage)
        return result

    def text_query(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096,
    ) -> str:
        result = ""
        kwargs = {
            "model": self.model,
            "max_tokens": self._clamp_max_tokens(max_tokens),
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        }
        thinking = self._thinking_config(max_tokens)
        if thinking:
            kwargs["thinking"] = thinking

        with self.client.messages.stream(**kwargs) as stream:
            for text in stream.text_stream:
                result += text
            final_message = stream.get_final_message()
        usage = getattr(final_message, "usage", None)
        self.last_usage = {
            "input_tokens": getattr(usage, "input_tokens", None),
            "output_tokens": getattr(usage, "output_tokens", None),
            "cache_creation_input_tokens": getattr(usage, "cache_creation_input_tokens", None),
            "cache_read_input_tokens": getattr(usage, "cache_read_input_tokens", None),
        }
        log_usage_if_context("anthropic", self.model, self.last_usage)

        if thinking and not result.strip():
            retry_kwargs = dict(kwargs)
            retry_kwargs.pop("thinking", None)
            retry_result = ""
            with self.client.messages.stream(**retry_kwargs) as stream:
                for text in stream.text_stream:
                    retry_result += text
                final_message = stream.get_final_message()
            usage = getattr(final_message, "usage", None)
            self.last_usage = {
                "input_tokens": getattr(usage, "input_tokens", None),
                "output_tokens": getattr(usage, "output_tokens", None),
                "cache_creation_input_tokens": getattr(usage, "cache_creation_input_tokens", None),
                "cache_read_input_tokens": getattr(usage, "cache_read_input_tokens", None),
            }
            log_usage_if_context("anthropic", self.model, self.last_usage)
            result = retry_result

        return result
