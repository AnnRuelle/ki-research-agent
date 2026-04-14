"""Anthropic Claude provider implementation."""

from __future__ import annotations

import logging
import os

from anthropic import (
    Anthropic,
    APITimeoutError,
)
from anthropic import (
    RateLimitError as AnthropicRateLimitError,
)

from agents.llm.provider import (
    InvalidResponseError,
    LLMError,
    LLMProvider,
    LLMResponse,
    LLMTimeoutError,
    RateLimitError,
)

logger = logging.getLogger(__name__)

# Approximate pricing per 1K tokens (USD)
PRICING: dict[str, tuple[float, float]] = {
    "claude-sonnet-4-6": (0.003, 0.015),
    "claude-haiku-4-5-20251001": (0.0008, 0.004),
    "claude-opus-4-6": (0.015, 0.075),
}


class AnthropicProvider(LLMProvider):
    """Anthropic Claude LLM provider."""

    def __init__(self, model: str, retries: int = 3, timeout: int = 60) -> None:
        super().__init__(model=model, retries=retries, timeout=timeout)

        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            msg = "ANTHROPIC_API_KEY must be set"
            raise LLMError(msg)

        self.client = Anthropic(
            api_key=api_key,
            timeout=float(timeout),
        )

    def _call_api(self, system: str, user: str, temperature: float) -> LLMResponse:
        """Make Anthropic API call."""
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=system,
                messages=[{"role": "user", "content": user}],
                temperature=temperature,
            )
        except AnthropicRateLimitError as e:
            raise RateLimitError(str(e)) from e
        except APITimeoutError as e:
            raise LLMTimeoutError(str(e)) from e
        except Exception as e:
            raise LLMError(f"Anthropic error: {e}") from e

        if not response.content:
            raise InvalidResponseError("Empty response from Anthropic")

        # Extract text from first TextBlock
        content = ""
        for block in response.content:
            if hasattr(block, "text"):
                content = block.text
                break
        if not content:
            raise InvalidResponseError("No text content in Anthropic response")
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens

        input_price, output_price = PRICING.get(self.model, (0.003, 0.015))
        cost = (input_tokens * input_price + output_tokens * output_price) / 1000

        return LLMResponse(
            content=content,
            model=self.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
        )
