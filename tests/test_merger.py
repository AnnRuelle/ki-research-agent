"""Unit tests for merger and changelog trimmer."""

from __future__ import annotations

from pathlib import Path

import pytest

from agents.changelog_trimmer import trim_changelog, trim_all_changelogs, update_global_changelog
from agents.merger import _extract_last_date, _freshness_indicator
from agents.parser import parse
from datetime import datetime, timezone


@pytest.mark.unit
class TestChangelogTrimmer:
    """Tests for changelog trimming logic."""

    def test_trim_removes_old_entries(self) -> None:
        changelog = (
            "- 2026-04-14: Neu hinzugefuegt\n"
            "- 2026-03-01: Update\n"
            "- 2025-12-01: Sehr alter Eintrag\n"
        )
        trimmed = trim_changelog(changelog, "2026-01-01")
        assert "2026-04-14" in trimmed
        assert "2026-03-01" in trimmed
        assert "2025-12-01" not in trimmed

    def test_trim_keeps_all_recent(self) -> None:
        changelog = "- 2026-04-14: Entry 1\n- 2026-04-07: Entry 2\n"
        trimmed = trim_changelog(changelog, "2026-01-01")
        assert trimmed == changelog

    def test_trim_handles_empty(self) -> None:
        assert trim_changelog("", "2026-01-01") == ""

    def test_trim_preserves_non_date_lines(self) -> None:
        changelog = "Some header text\n- 2026-04-14: Entry\n- 2025-01-01: Old\n"
        trimmed = trim_changelog(changelog, "2026-01-01")
        assert "Some header text" in trimmed
        assert "2026-04-14" in trimmed
        assert "2025-01-01" not in trimmed


@pytest.mark.unit
class TestMergerUtils:
    """Tests for merger utility functions."""

    def test_extract_last_date_found(self) -> None:
        changelog = "- 2026-04-14: Latest\n- 2026-03-01: Older\n"
        assert _extract_last_date(changelog) == "2026-04-14"

    def test_extract_last_date_empty(self) -> None:
        assert _extract_last_date("") is None
        assert _extract_last_date("No dates here") is None

    def test_freshness_green(self) -> None:
        now = datetime(2026, 4, 14, tzinfo=timezone.utc)
        assert _freshness_indicator("2026-04-10", now) == "aktuell"

    def test_freshness_yellow(self) -> None:
        now = datetime(2026, 4, 14, tzinfo=timezone.utc)
        assert _freshness_indicator("2026-03-30", now) == "veraltet"

    def test_freshness_red(self) -> None:
        now = datetime(2026, 4, 14, tzinfo=timezone.utc)
        assert _freshness_indicator("2026-01-01", now) == "stark veraltet"

    def test_freshness_none(self) -> None:
        now = datetime(2026, 4, 14, tzinfo=timezone.utc)
        assert _freshness_indicator(None, now) == "nie aktualisiert"


@pytest.mark.unit
class TestMergerIntegration:
    """Tests for merger with real chapter files."""

    def test_update_dashboard(self) -> None:
        """Dashboard update should not crash on stub chapters."""
        from agents.merger import update_dashboard
        update_dashboard()
        dashboard = Path("index.md").read_text(encoding="utf-8")
        assert "Status Dashboard" in dashboard
        assert "01" in dashboard
        assert "13" in dashboard

    def test_update_chapter_index(self) -> None:
        """Chapter index update should list subpages."""
        from agents.merger import update_chapter_index
        update_chapter_index("01-plattform-architektur")
        index = Path("chapters/01-plattform-architektur/index.md").read_text(encoding="utf-8")
        assert "ai-gateway.md" in index

    def test_global_changelog_update(self) -> None:
        """Global changelog should be writable."""
        update_global_changelog(cutoff_date="2020-01-01")
        cl = Path("CHANGELOG.md").read_text(encoding="utf-8")
        assert "# Changelog" in cl
