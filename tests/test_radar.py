"""Unit tests for agents/radar.py (List-Mode, Feed-Mode, Trim, JSON parsing)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from agents import radar
from agents.config_schema import AgentConfig, RadarConfig
from agents.llm.provider import LLMResponse


def _make_config(
    *,
    mode: str = "list",
    enabled: bool = True,
    trim_days: int = 90,
    queries: list[str] | None = None,
) -> RadarConfig:
    return RadarConfig(
        enabled=enabled,
        mode=mode,  # type: ignore[arg-type]
        schedule="sunday 07:00",
        agent=AgentConfig(provider="anthropic", model="claude-haiku-4-5-20251001"),
        search_queries=queries or [],
        trim_days=trim_days,
    )


def _make_response(content: str) -> LLMResponse:
    return LLMResponse(content=content, model="test-model")


@pytest.mark.unit
class TestParseJsonArray:
    """_parse_json_array handles various LLM response formats."""

    def test_plain_array(self) -> None:
        out = radar._parse_json_array('[{"a": 1}, {"b": 2}]')
        assert out == [{"a": 1}, {"b": 2}]

    def test_markdown_code_block(self) -> None:
        out = radar._parse_json_array('```json\n[{"x": "y"}]\n```')
        assert out == [{"x": "y"}]

    def test_single_object_becomes_list(self) -> None:
        out = radar._parse_json_array('{"a": 1}')
        assert out == [{"a": 1}]

    def test_invalid_json(self) -> None:
        assert radar._parse_json_array("not json at all") == []

    def test_filters_non_dicts(self) -> None:
        out = radar._parse_json_array('[{"a": 1}, "string", 42, null, {"b": 2}]')
        assert out == [{"a": 1}, {"b": 2}]


@pytest.mark.unit
class TestNormalizeKey:
    def test_snake_case_lowercased(self) -> None:
        assert radar._normalize_key("CH-Hosting") == "ch_hosting"
        assert radar._normalize_key("Erst Gesichtet") == "erst_gesichtet"
        assert radar._normalize_key("anbieter") == "anbieter"


@pytest.mark.unit
class TestTrimFeed:
    """_trim_feed removes entries older than trim_days."""

    def test_removes_old_entries(self) -> None:
        old = (datetime.now(tz=timezone.utc) - timedelta(days=120)).strftime("%Y-%m-%d")
        recent = (datetime.now(tz=timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
        content = f"# Feed\n\n### {recent} — Recent\n\nSummary recent\n\n### {old} — Old\n\nSummary old\n\n"
        new_content, removed = radar._trim_feed(content, trim_days=90)
        assert removed == 1
        assert "Recent" in new_content
        assert "Old" not in new_content

    def test_no_entries_no_op(self) -> None:
        content = "# Feed\n\n*Noch keine Einträge.*\n"
        new_content, removed = radar._trim_feed(content, trim_days=90)
        assert removed == 0
        assert new_content == content

    def test_all_recent_kept(self) -> None:
        d1 = (datetime.now(tz=timezone.utc) - timedelta(days=10)).strftime("%Y-%m-%d")
        d2 = (datetime.now(tz=timezone.utc) - timedelta(days=20)).strftime("%Y-%m-%d")
        content = f"# Feed\n\n### {d1} — A\n\nfoo\n\n### {d2} — B\n\nbar\n"
        new_content, removed = radar._trim_feed(content, trim_days=90)
        assert removed == 0
        assert "A" in new_content
        assert "B" in new_content


@pytest.mark.unit
class TestRunListRadar:
    """run_list_radar appends new entries from the LLM to the YAML file."""

    def test_appends_new_entries(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        radar_dir = tmp_path / "radar"
        radar_dir.mkdir()
        yaml_path = radar_dir / "plattformen.yaml"
        yaml_path.write_text(
            yaml.safe_dump(
                {
                    "schema_version": 1,
                    "columns": [{"name": "Anbieter"}, {"name": "Quelle"}],
                    "rows": [{"anbieter": "Existing AG", "quelle": "https://ex.com"}],
                },
                allow_unicode=True,
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        monkeypatch.setattr(radar, "RADAR_DIR", radar_dir)

        provider = MagicMock()
        provider.complete.return_value = _make_response('[{"Anbieter": "New AI", "Quelle": "https://new.com"}]')

        with patch.object(radar, "search", return_value=[]):
            added = radar.run_list_radar("plattformen", _make_config(), provider)

        assert added == 1
        result = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        assert len(result["rows"]) == 2
        assert result["rows"][1]["anbieter"] == "New AI"
        assert result["rows"][1]["quelle"] == "https://new.com"
        assert "last_updated" in result

    def test_no_new_entries_keeps_file_unchanged(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        radar_dir = tmp_path / "radar"
        radar_dir.mkdir()
        yaml_path = radar_dir / "plattformen.yaml"
        original = {"schema_version": 1, "columns": [{"name": "A"}], "rows": [{"a": "x"}]}
        yaml_path.write_text(yaml.safe_dump(original, allow_unicode=True, sort_keys=False), encoding="utf-8")
        monkeypatch.setattr(radar, "RADAR_DIR", radar_dir)

        provider = MagicMock()
        provider.complete.return_value = _make_response("[]")

        with patch.object(radar, "search", return_value=[]):
            added = radar.run_list_radar("plattformen", _make_config(), provider)

        assert added == 0
        result = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        assert result == original

    def test_missing_yaml_returns_zero(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(radar, "RADAR_DIR", tmp_path / "radar")
        provider = MagicMock()
        added = radar.run_list_radar("nonexistent", _make_config(), provider)
        assert added == 0
        provider.complete.assert_not_called()


@pytest.mark.unit
class TestRunFeedRadar:
    """run_feed_radar prepends new entries and trims old ones."""

    def test_prepends_and_replaces_placeholder(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        radar_dir = tmp_path / "radar"
        radar_dir.mkdir()
        md_path = radar_dir / "llm-news.md"
        md_path.write_text("# Radar: LLM News\n\n## Feed\n\n*Noch keine Einträge.*\n", encoding="utf-8")
        monkeypatch.setattr(radar, "RADAR_DIR", radar_dir)

        provider = MagicMock()
        provider.complete.return_value = _make_response(
            '[{"date": "2026-04-15", "title": "GPT-5 released", '
            '"summary": "OpenAI released GPT-5.", "url": "https://openai.com/gpt5"}]'
        )

        with patch.object(radar, "search", return_value=[]):
            added = radar.run_feed_radar("llm_news", _make_config(mode="feed"), provider)

        assert added == 1
        content = md_path.read_text(encoding="utf-8")
        assert "*Noch keine Einträge.*" not in content
        assert "GPT-5 released" in content
        assert "https://openai.com/gpt5" in content

    def test_trim_removes_old_after_prepend(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        radar_dir = tmp_path / "radar"
        radar_dir.mkdir()
        old_date = (datetime.now(tz=timezone.utc) - timedelta(days=120)).strftime("%Y-%m-%d")
        md_path = radar_dir / "llm-news.md"
        md_path.write_text(
            f"# Feed\n\n## Feed\n\n### {old_date} — Very Old\n\nAncient news.\n\n[Quelle](https://old.com)\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(radar, "RADAR_DIR", radar_dir)

        provider = MagicMock()
        provider.complete.return_value = _make_response("[]")

        with patch.object(radar, "search", return_value=[]):
            radar.run_feed_radar("llm_news", _make_config(mode="feed"), provider)

        content = md_path.read_text(encoding="utf-8")
        assert "Very Old" not in content

    def test_missing_md_returns_zero(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(radar, "RADAR_DIR", tmp_path / "radar")
        provider = MagicMock()
        added = radar.run_feed_radar("nothing", _make_config(mode="feed"), provider)
        assert added == 0
        provider.complete.assert_not_called()


@pytest.mark.unit
class TestRunAllEnabled:
    """run_all_enabled filters by schedule and skips disabled radars."""

    def test_schedule_filter_weekly(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from agents.config_schema import AppConfig

        mock_config = MagicMock(spec=AppConfig)
        mock_config.radars = {
            "daily_one": _make_config(mode="feed"),
            "weekly_one": _make_config(mode="list"),
            "disabled": _make_config(enabled=False),
        }
        mock_config.radars["daily_one"].schedule = "daily 07:00"
        mock_config.radars["weekly_one"].schedule = "sunday 07:00"

        calls: list[str] = []

        def fake_run_radar(name: str) -> int:
            calls.append(name)
            return 0

        with (
            patch.object(radar, "load_config", return_value=mock_config),
            patch.object(radar, "run_radar", side_effect=fake_run_radar),
        ):
            radar.run_all_enabled(schedule_filter="sunday")

        assert calls == ["weekly_one"]

    def test_schedule_filter_daily(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from agents.config_schema import AppConfig

        mock_config = MagicMock(spec=AppConfig)
        mock_config.radars = {
            "daily_one": _make_config(mode="feed"),
            "weekly_one": _make_config(mode="list"),
        }
        mock_config.radars["daily_one"].schedule = "daily 07:00"
        mock_config.radars["weekly_one"].schedule = "sunday 07:00"

        calls: list[str] = []

        def fake_run_radar(name: str) -> int:
            calls.append(name)
            return 0

        with (
            patch.object(radar, "load_config", return_value=mock_config),
            patch.object(radar, "run_radar", side_effect=fake_run_radar),
        ):
            radar.run_all_enabled(schedule_filter="daily")

        assert calls == ["daily_one"]


@pytest.mark.unit
class TestRadarConfigDefaults:
    """RadarConfig Pydantic defaults."""

    def test_defaults_disabled(self) -> None:
        cfg = RadarConfig.model_validate({"agent": {"provider": "anthropic", "model": "claude-haiku-4-5-20251001"}})
        assert cfg.enabled is False
        assert cfg.mode == "list"
        assert cfg.trim_days == 90
        assert cfg.search_queries == []

    def test_feed_mode(self) -> None:
        cfg = RadarConfig.model_validate(
            {
                "enabled": True,
                "mode": "feed",
                "agent": {"provider": "anthropic", "model": "claude-haiku-4-5-20251001"},
            }
        )
        assert cfg.mode == "feed"
        assert cfg.enabled is True

    def test_invalid_mode_rejected(self) -> None:
        with pytest.raises(ValueError):
            RadarConfig.model_validate(
                {
                    "mode": "nonsense",
                    "agent": {"provider": "anthropic", "model": "claude-haiku-4-5-20251001"},
                }
            )
