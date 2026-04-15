"""Pydantic models for config.yaml and sources.yaml validation."""

from __future__ import annotations

from typing import Literal

import yaml
from pydantic import BaseModel, Field, field_validator

# --- config.yaml ---


class AgentConfig(BaseModel):
    """Configuration for a single agent."""

    provider: str
    model: str
    retries: int = 3
    timeout: int = 60
    max_context_chapters: int | None = None


class ScheduleConfig(BaseModel):
    """Cron schedule configuration."""

    rss_ingest: str
    web_archive_check: str
    research_pipeline: str
    consistency_check: str
    newsletter_send: str


class NewsletterConfig(BaseModel):
    """Newsletter configuration."""

    sender: str
    recipients: list[str]
    batch_approve_threshold: int = 10


class AutoMergeRules(BaseModel):
    """Rules for automatic merging."""

    critic_verdict: str = "approve"
    critic_severity_max: str = "minor"
    operations: list[str] = Field(default_factory=lambda: ["update_text", "add_source"])


class AutoMergeConfig(BaseModel):
    """Auto-merge configuration."""

    enabled: bool = False
    rules: AutoMergeRules = Field(default_factory=AutoMergeRules)
    always_manual_chapters: list[str] = Field(default_factory=list)
    always_manual_tags: list[str] = Field(default_factory=list)
    always_manual_origins: list[str] = Field(default_factory=list)


class ChapterScope(BaseModel):
    """Geographical scope for a chapter."""

    ch: bool = True
    dach: bool = True
    global_: bool = Field(True, alias="global")
    chinese: bool = False
    search_queries: list[str] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    format: Literal["json", "text"] = "json"


class BudgetConfig(BaseModel):
    """Per-run budget cap for LLM costs."""

    max_usd_per_run: float | None = None


class RadarConfig(BaseModel):
    """Configuration for a single radar (continuous monitoring stream)."""

    enabled: bool = False
    mode: Literal["list", "feed"] = "list"
    schedule: str = "sunday 07:00"
    agent: AgentConfig
    search_queries: list[str] = Field(default_factory=list)
    trim_days: int = 90


class AppConfig(BaseModel):
    """Root configuration model for config.yaml."""

    agents: dict[str, AgentConfig]
    schedule: ScheduleConfig
    newsletter: NewsletterConfig
    auto_merge: AutoMergeConfig = Field(default_factory=AutoMergeConfig)
    chapter_scope: dict[str, ChapterScope] = Field(default_factory=dict)
    radars: dict[str, RadarConfig] = Field(default_factory=dict)
    budget: BudgetConfig = Field(default_factory=BudgetConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    @field_validator("agents")
    @classmethod
    def validate_required_agents(cls, v: dict[str, AgentConfig]) -> dict[str, AgentConfig]:
        """Ensure core agents are configured."""
        required = {"researcher", "writer", "critic", "resolver", "consistency_checker"}
        missing = required - set(v.keys())
        if missing:
            msg = f"Missing required agent configs: {missing}"
            raise ValueError(msg)
        return v


# --- sources.yaml ---


class RSSSource(BaseModel):
    """An RSS feed source."""

    name: str
    url: str
    chapters: list[str]


class WebsiteSource(BaseModel):
    """A website source."""

    name: str
    url: str
    chapters: list[str]


class ArchiveSource(BaseModel):
    """A web archive source."""

    name: str
    url: str
    frequency: str = "monthly"
    chapters: list[str]


class GmailConfig(BaseModel):
    """Gmail integration configuration."""

    enabled: bool = False


class SourcesConfig(BaseModel):
    """Root configuration model for sources.yaml."""

    rss: list[RSSSource] = Field(default_factory=list)
    websites: list[WebsiteSource] = Field(default_factory=list)
    archives: list[ArchiveSource] = Field(default_factory=list)
    gmail: GmailConfig = Field(default_factory=GmailConfig)


# --- Loader functions ---


def load_config(path: str = "config.yaml") -> AppConfig:
    """Load and validate config.yaml."""
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return AppConfig.model_validate(raw)


def load_sources(path: str = "sources.yaml") -> SourcesConfig:
    """Load and validate sources.yaml."""
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return SourcesConfig.model_validate(raw)
