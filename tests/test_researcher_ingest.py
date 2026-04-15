"""Unit tests for researcher's time-based ingest window (P1-6)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

import agents.researcher as researcher_module
from agents.researcher import _file_date, _files_in_window, _load_ingested_sources

pytestmark = pytest.mark.unit


def _today() -> datetime:
    return datetime.now(tz=timezone.utc)


def _iso(days_ago: int) -> str:
    return (_today() - timedelta(days=days_ago)).strftime("%Y-%m-%d")


class TestFileDate:
    def test_parses_date_from_name(self, tmp_path: Path) -> None:
        f = tmp_path / "rss-2026-04-10.json"
        f.write_text("[]", encoding="utf-8")
        assert _file_date(f).isoformat() == "2026-04-10"

    def test_falls_back_to_mtime(self, tmp_path: Path) -> None:
        f = tmp_path / "no-date-here.json"
        f.write_text("[]", encoding="utf-8")
        # Should return today (or close) from mtime
        result = _file_date(f)
        assert abs((result - _today().date()).days) <= 1


class TestFilesInWindow:
    def test_filters_old_files(self, tmp_path: Path) -> None:
        (tmp_path / f"rss-{_iso(5)}.json").write_text("[]", encoding="utf-8")
        (tmp_path / f"rss-{_iso(20)}.json").write_text("[]", encoding="utf-8")
        (tmp_path / f"rss-{_iso(100)}.json").write_text("[]", encoding="utf-8")
        result = _files_in_window(tmp_path, "*.json", window_days=14)
        assert len(result) == 1
        assert _iso(5) in result[0].name

    def test_sorts_newest_first(self, tmp_path: Path) -> None:
        (tmp_path / f"rss-{_iso(1)}.json").write_text("[]", encoding="utf-8")
        (tmp_path / f"rss-{_iso(7)}.json").write_text("[]", encoding="utf-8")
        (tmp_path / f"rss-{_iso(3)}.json").write_text("[]", encoding="utf-8")
        result = _files_in_window(tmp_path, "*.json", window_days=14)
        names = [p.name for p in result]
        assert _iso(1) in names[0]
        assert _iso(3) in names[1]
        assert _iso(7) in names[2]

    def test_missing_directory(self, tmp_path: Path) -> None:
        assert _files_in_window(tmp_path / "nonexistent", "*.json", 14) == []


class TestLoadIngestedSources:
    def _setup(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(researcher_module, "SOURCES_DIR", tmp_path)
        (tmp_path / "newsletters").mkdir()
        (tmp_path / "web-archives").mkdir()

    def test_includes_fresh_rss(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._setup(tmp_path, monkeypatch)
        items = [{"source_name": "Fresh", "title": "Article X", "url": "https://ex.com/x"}]
        (tmp_path / "newsletters" / f"rss-{_iso(2)}.json").write_text(json.dumps(items), encoding="utf-8")
        out = _load_ingested_sources(window_days=14)
        assert "Fresh" in out
        assert "Article X" in out

    def test_excludes_stale_rss(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._setup(tmp_path, monkeypatch)
        items = [{"source_name": "Old", "title": "Archived", "url": "https://ex.com/old"}]
        (tmp_path / "newsletters" / f"rss-{_iso(60)}.json").write_text(json.dumps(items), encoding="utf-8")
        out = _load_ingested_sources(window_days=14)
        assert "Old" not in out
        assert "Archived" not in out

    def test_respects_max_items(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._setup(tmp_path, monkeypatch)
        items = [{"source_name": "S", "title": f"T{i}", "url": f"https://ex.com/{i}"} for i in range(50)]
        (tmp_path / "newsletters" / f"rss-{_iso(1)}.json").write_text(json.dumps(items), encoding="utf-8")
        out = _load_ingested_sources(window_days=14, max_items=5)
        assert out.count("- [S]") == 5

    def test_includes_web_changes(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._setup(tmp_path, monkeypatch)
        changes = [{"source_name": "FOO", "snippet": "some text"}]
        (tmp_path / "web-archives" / f"changes-{_iso(3)}.json").write_text(json.dumps(changes), encoding="utf-8")
        out = _load_ingested_sources(window_days=14)
        assert "[WEB] FOO" in out

    def test_empty_returns_placeholder(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._setup(tmp_path, monkeypatch)
        out = _load_ingested_sources(window_days=14)
        assert "(Keine neuen Quellen)" in out

    def test_corrupt_json_skipped(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._setup(tmp_path, monkeypatch)
        (tmp_path / "newsletters" / f"rss-{_iso(1)}.json").write_text("not json", encoding="utf-8")
        # Should not raise
        out = _load_ingested_sources(window_days=14)
        assert "(Keine neuen Quellen)" in out
