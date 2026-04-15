"""LLM Provider abstraction layer (ABC)."""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from agents import cost_tracker

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Response from an LLM provider."""

    content: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    duration_seconds: float = 0.0
    metadata: dict[str, str | int | float] = field(default_factory=dict)


class LLMProvider(ABC):
    """Abstract base class for LLM providers.

    Each provider implements a simple complete() method.
    Agents construct their own prompts and use the provider generically.
    """

    def __init__(self, model: str, retries: int = 3, timeout: int = 60, agent_name: str = "unknown") -> None:
        self.model = model
        self.retries = retries
        self.timeout = timeout
        self.agent_name = agent_name

    def complete(self, system: str, user: str, temperature: float = 0.3) -> LLMResponse:
        """Complete a prompt with retry logic and cost tracking.

        Args:
            system: System prompt / instructions.
            user: User message / content.
            temperature: Sampling temperature (default 0.3 for factual tasks).

        Returns:
            LLMResponse with content and usage metadata.

        Raises:
            LLMError: After all retries exhausted.
        """
        last_error: Exception | None = None

        for attempt in range(1, self.retries + 1):
            try:
                start = time.monotonic()
                response = self._call_api(system, user, temperature)
                response.duration_seconds = time.monotonic() - start

                logger.info(
                    "LLM call success: agent=%s, model=%s, tokens=%d+%d, cost=$%.4f, duration=%.1fs",
                    self.agent_name,
                    response.model,
                    response.input_tokens,
                    response.output_tokens,
                    response.cost_usd,
                    response.duration_seconds,
                )
                cost_tracker.track(self.agent_name, response.cost_usd)
                return response

            except RateLimitError:
                wait = 2**attempt
                logger.warning("Rate limit hit (attempt %d/%d), waiting %ds", attempt, self.retries, wait)
                time.sleep(wait)
                last_error = RateLimitError(f"Rate limit after {attempt} attempts")

            except LLMTimeoutError:
                if attempt < self.retries:
                    logger.warning("Timeout (attempt %d/%d), retrying", attempt, self.retries)
                    last_error = LLMTimeoutError(f"Timeout after {attempt} attempts")
                else:
                    last_error = LLMTimeoutError(f"Timeout after {self.retries} attempts")

            except LLMError as e:
                logger.error("LLM error (attempt %d/%d): %s", attempt, self.retries, e)
                last_error = e
                if attempt < self.retries:
                    time.sleep(1)

        raise LLMError(f"All {self.retries} retries exhausted") from last_error

    @abstractmethod
    def _call_api(self, system: str, user: str, temperature: float) -> LLMResponse:
        """Make the actual API call. Implemented by each provider."""
        ...


class LLMError(Exception):
    """Base error for LLM operations."""


class RateLimitError(LLMError):
    """Rate limit (429) error."""


class LLMTimeoutError(LLMError):
    """Timeout error."""


class InvalidResponseError(LLMError):
    """LLM returned unparseable or empty response."""
