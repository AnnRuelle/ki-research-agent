"""Factory to create LLM providers from config."""

from __future__ import annotations

from agents.config_schema import AgentConfig
from agents.llm.provider import LLMProvider


def create_provider(agent_config: AgentConfig) -> LLMProvider:
    """Create an LLM provider instance from agent configuration.

    Args:
        agent_config: Agent configuration with provider, model, retries, timeout.

    Returns:
        Configured LLMProvider instance.

    Raises:
        ValueError: If provider is unknown.
    """
    provider_name = agent_config.provider
    model = agent_config.model
    retries = agent_config.retries
    timeout = agent_config.timeout

    if provider_name == "azure_openai":
        from agents.llm.azure_openai_provider import AzureOpenAIProvider

        return AzureOpenAIProvider(model=model, retries=retries, timeout=timeout)

    if provider_name == "anthropic":
        from agents.llm.anthropic_provider import AnthropicProvider

        return AnthropicProvider(model=model, retries=retries, timeout=timeout)

    msg = f"Unknown provider: {provider_name}. Available: azure_openai, anthropic"
    raise ValueError(msg)
