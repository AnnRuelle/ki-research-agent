"""Unit tests for ingest agents (RSS poller + web archive checker)."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import pytest

from agents.config_schema import RSSSource, SourcesConfig, WebsiteSource
from agents.ingest.rss_poller import RSSItem, _hash_item, _load_seen_hashes, poll_feed
from agents.ingest.web_archive_checker import (
    WebChange,
    _content_hash,
    _extract_snippet,
    _load_hash_index,
    _save_hash_index,
)


@pytest.mark.unit
class TestRSSPoller:
    """Tests for RSS poller utilities."""

    def test_hash_item_deterministic(self) -> None:
        """Same URL+title always produces the same hash."""
        h1 = _hash_item("https://example.com", "Test")
        h2 = _hash_item("https://example.com", "Test")
        assert h1 == h2

    def test_hash_item_different_inputs(self) -> None:
        """Different inputs produce different hashes."""
        h1 = _hash_item("https://example.com/a", "Title A")
        h2 = _hash_item("https://example.com/b", "Title B")
        assert h1 != h2

    def test_load_seen_hashes_empty_dir(self, tmp_path: Path) -> None:
        """Empty directory returns empty set."""
        assert _load_seen_hashes(tmp_path) == set()

    def test_load_seen_hashes_with_data(self, tmp_path: Path) -> None:
        """Hashes are loaded from existing JSON files."""
        data = [{"item_hash": "abc123", "title": "Test"}]
        (tmp_path / "test.json").write_text(json.dumps(data), encoding="utf-8")
        seen = _load_seen_hashes(tmp_path)
        assert "abc123" in seen

    def test_rss_item_dataclass(self) -> None:
        """RSSItem can be created and serialized."""
        item = RSSItem(
            source_name="Test Feed",
            title="Test Article",
            url="https://example.com/article",
            published="2026-04-14T06:00:00+00:00",
            summary="A test article.",
            chapters=["01-plattform-architektur"],
            item_hash="abc123",
        )
        d = asdict(item)
        assert d["source_name"] == "Test Feed"
        assert d["chapters"] == ["01-plattform-architektur"]


@pytest.mark.unit
class TestWebArchiveChecker:
    """Tests for web archive checker utilities."""

    def test_content_hash_deterministic(self) -> None:
        """Same content always produces the same hash."""
        h1 = _content_hash("Hello World")
        h2 = _content_hash("Hello World")
        assert h1 == h2

    def test_content_hash_different(self) -> None:
        """Different content produces different hashes."""
        h1 = _content_hash("Version 1")
        h2 = _content_hash("Version 2")
        assert h1 != h2

    def test_extract_snippet_truncates(self) -> None:
        """Snippet is truncated to max_length."""
        html = "<p>" + "A" * 1000 + "</p>"
        snippet = _extract_snippet(html, max_length=100)
        assert len(snippet) <= 100

    def test_extract_snippet_strips_tags(self) -> None:
        """HTML tags are removed from snippet."""
        html = "<h1>Title</h1><p>Body text.</p>"
        snippet = _extract_snippet(html)
        assert "<h1>" not in snippet
        assert "Title" in snippet
        assert "Body text." in snippet

    def test_hash_index_roundtrip(self, tmp_path: Path) -> None:
        """Hash index can be saved and reloaded."""
        index_file = tmp_path / "index.json"
        original = {"https://example.com": "abc123", "https://test.ch": "def456"}
        _save_hash_index(index_file, original)
        loaded = _load_hash_index(index_file)
        assert loaded == original

    def test_hash_index_missing_file(self, tmp_path: Path) -> None:
        """Missing index file returns empty dict."""
        index_file = tmp_path / "nonexistent.json"
        assert _load_hash_index(index_file) == {}

    def test_web_change_dataclass(self) -> None:
        """WebChange can be created and serialized."""
        change = WebChange(
            source_name="Test Site",
            url="https://example.com",
            chapters=["05-regulatorik"],
            detected_at="2026-04-14T06:00:00+00:00",
            content_hash="abc123",
            previous_hash=None,
            snippet="Some text",
        )
        d = asdict(change)
        assert d["source_name"] == "Test Site"
        assert d["previous_hash"] is None
