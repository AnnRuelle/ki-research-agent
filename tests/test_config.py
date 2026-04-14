"""Unit tests for config schema validation."""

from pathlib import Path

import pytest

from agents.config_schema import AppConfig, SourcesConfig, load_config, load_sources

ROOT = Path(__file__).parent.parent


class TestConfigLoading:
    """Tests for config.yaml loading and validation."""

    def test_load_config_yaml(self) -> None:
        """config.yaml should load and validate without errors."""
        config = load_config(str(ROOT / "config.yaml"))
        assert "researcher" in config.agents
        assert "writer" in config.agents
        assert "critic" in config.agents
        assert "resolver" in config.agents
        assert "consistency_checker" in config.agents
        assert config.auto_merge.enabled is False

    def test_load_sources_yaml(self) -> None:
        """sources.yaml should load and validate without errors."""
        sources = load_sources(str(ROOT / "sources.yaml"))
        assert len(sources.rss) > 0
        assert len(sources.websites) > 0
        assert sources.gmail.enabled is False

    def test_config_agent_retries(self) -> None:
        """Agent configs should have retry settings."""
        config = load_config(str(ROOT / "config.yaml"))
        assert config.agents["researcher"].retries == 3
        assert config.agents["researcher"].timeout == 60

    def test_config_schedule(self) -> None:
        """Schedule should be configured."""
        config = load_config(str(ROOT / "config.yaml"))
        assert "daily" in config.schedule.rss_ingest
        assert "sunday" in config.schedule.research_pipeline

    def test_config_missing_agent_raises(self) -> None:
        """Config missing a required agent should fail validation."""
        raw = {
            "agents": {
                "researcher": {"provider": "azure_openai", "model": "gpt-4o-mini"},
                # missing writer, critic, resolver, consistency_checker
            },
            "schedule": {
                "rss_ingest": "daily 06:00",
                "web_archive_check": "sunday 05:00",
                "research_pipeline": "sunday 06:00",
                "consistency_check": "sunday 08:00",
                "newsletter_send": "monday 07:00",
            },
            "newsletter": {
                "sender": "test@test.com",
                "recipients": ["r@test.com"],
            },
        }
        with pytest.raises(ValueError, match="Missing required agent"):
            AppConfig.model_validate(raw)

    def test_sources_rss_chapters(self) -> None:
        """RSS sources should have chapter assignments."""
        sources = load_sources(str(ROOT / "sources.yaml"))
        for rss in sources.rss:
            assert len(rss.chapters) > 0
            assert rss.url.startswith("http")
