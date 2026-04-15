"""Unit tests for URL canonicalization and seen-URL memory."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from agents import url_utils
from agents.url_utils import (
    canonicalize_url,
    filter_unseen,
    load_seen_urls,
    mark_seen,
    save_seen_urls,
    trim_seen_urls,
)


@pytest.mark.unit
class TestCanonicalizeUrl:
    def test_strips_www(self) -> None:
        assert canonicalize_url("https://www.example.com/page") == "https://example.com/page"

    def test_strips_trailing_slash(self) -> None:
        assert canonicalize_url("https://example.com/page/") == "https://example.com/page"

    def test_keeps_root_slash(self) -> None:
        assert canonicalize_url("https://example.com/") == "https://example.com/"

    def test_lowercases_host_and_scheme(self) -> None:
        assert canonicalize_url("HTTPS://Example.COM/Page") == "https://example.com/Page"

    def test_drops_fragment(self) -> None:
        assert canonicalize_url("https://example.com/page#section") == "https://example.com/page"

    def test_drops_utm_params(self) -> None:
        url = "https://example.com/page?utm_source=tw&utm_medium=x&real=keep"
        assert canonicalize_url(url) == "https://example.com/page?real=keep"

    def test_drops_tracking_exact(self) -> None:
        url = "https://example.com/p?fbclid=abc&gclid=def&id=7"
        assert canonicalize_url(url) == "https://example.com/p?id=7"

    def test_dedup_variants_collide(self) -> None:
        variants = [
            "https://www.example.com/page",
            "https://example.com/page/",
            "https://example.com/page#anchor",
            "https://example.com/page?utm_campaign=foo",
        ]
        canonicals = {canonicalize_url(u) for u in variants}
        assert len(canonicals) == 1

    def test_empty_string(self) -> None:
        assert canonicalize_url("") == ""


@pytest.mark.unit
class TestSeenUrlsIO:
    def test_load_missing_returns_empty(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(url_utils, "SEEN_DIR", tmp_path / "seen")
        assert load_seen_urls("01-plattform") == {}

    def test_save_and_load_roundtrip(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(url_utils, "SEEN_DIR", tmp_path / "seen")
        data = {"https://example.com/a": "2026-04-15", "https://example.com/b": "2026-04-10"}
        save_seen_urls("07-markt", data)
        assert load_seen_urls("07-markt") == data

    def test_load_corrupt_file_returns_empty(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        seen_dir = tmp_path / "seen"
        seen_dir.mkdir()
        (seen_dir / "broken.json").write_text("not json", encoding="utf-8")
        monkeypatch.setattr(url_utils, "SEEN_DIR", seen_dir)
        assert load_seen_urls("broken") == {}


@pytest.mark.unit
class TestTrimSeenUrls:
    def test_drops_old(self) -> None:
        today = datetime.now(tz=timezone.utc).date()
        old = (today - timedelta(days=200)).strftime("%Y-%m-%d")
        recent = (today - timedelta(days=30)).strftime("%Y-%m-%d")
        seen = {"https://old.com": old, "https://recent.com": recent}
        trimmed = trim_seen_urls(seen, max_age_days=180)
        assert "https://old.com" not in trimmed
        assert "https://recent.com" in trimmed

    def test_keeps_malformed_dates(self) -> None:
        seen = {"https://a.com": "not-a-date"}
        assert trim_seen_urls(seen) == seen


@pytest.mark.unit
class TestFilterAndMark:
    def test_filter_unseen(self) -> None:
        seen = {canonicalize_url("https://example.com/page"): "2026-04-15"}
        urls = ["https://www.example.com/page/", "https://other.com/new"]
        result = filter_unseen(urls, seen)
        assert result == ["https://other.com/new"]

    def test_mark_seen_adds_canonical(self) -> None:
        seen: dict[str, str] = {}
        result = mark_seen(seen, ["https://www.example.com/a/"], date="2026-04-15")
        assert result == {"https://example.com/a": "2026-04-15"}

    def test_mark_seen_preserves_existing_date(self) -> None:
        seen = {"https://example.com/a": "2026-01-01"}
        result = mark_seen(seen, ["https://www.example.com/a/"], date="2026-04-15")
        assert result["https://example.com/a"] == "2026-01-01"

    def test_mark_seen_empty_url_skipped(self) -> None:
        seen: dict[str, str] = {}
        result = mark_seen(seen, [""], date="2026-04-15")
        assert result == {}
