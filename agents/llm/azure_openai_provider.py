"""Azure OpenAI provider implementation."""

from __future__ import annotations

import logging
import os

from openai import APITimeoutError, AzureOpenAI
from openai import RateLimitError as OpenAIRateLimitError

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
    "gpt-4o": (0.0025, 0.01),
    "gpt-4o-mini": (0.00015, 0.0006),
}


class AzureOpenAIProvider(LLMProvider):
    """Azure OpenAI LLM provider."""

    def __init__(self, model: str, retries: int = 3, timeout: int = 60) -> None:
        super().__init__(model=model, retries=retries, timeout=timeout)

        api_key = os.environ.get("AZURE_OPENAI_API_KEY", "")
        endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT", "")
        api_version = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")

        if not api_key or not endpoint:
            msg = "AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT must be set"
            raise LLMError(msg)

        self.client = AzureOpenAI(
            api_key=api_key,
            azure_endpoint=endpoint,
            api_version=api_version,
            timeout=float(timeout),
        )

    def _call_api(self, system: str, user: str, temperature: float) -> LLMResponse:
        """Make Azure OpenAI API call."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=temperature,
            )
        except OpenAIRateLimitError as e:
            raise RateLimitError(str(e)) from e
        except APITimeoutError as e:
            raise LLMTimeoutError(str(e)) from e
        except Exception as e:
            raise LLMError(f"Azure OpenAI error: {e}") from e

        choice = response.choices[0] if response.choices else None
        if not choice or not choice.message.content:
            raise InvalidResponseError("Empty response from Azure OpenAI")

        usage = response.usage
        input_tokens = usage.prompt_tokens if usage else 0
        output_tokens = usage.completion_tokens if usage else 0

        input_price, output_price = PRICING.get(self.model, (0.0025, 0.01))
        cost = (input_tokens * input_price + output_tokens * output_price) / 1000

        return LLMResponse(
            content=choice.message.content,
            model=self.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
        )
