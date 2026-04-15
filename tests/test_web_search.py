"""Unit tests for web_search custom_queries path."""

from __future__ import annotations

from collections.abc import Iterator
from unittest.mock import patch

import pytest

from agents import web_search
from agents.config_schema import ChapterScope
from agents.web_search import SearchResult, search_for_chapter


@pytest.mark.unit
class TestChapterScopeSearchQueries:
    """ChapterScope.search_queries field."""

    def test_default_empty(self) -> None:
        scope = ChapterScope.model_validate({})
        assert scope.search_queries == []

    def test_populated(self) -> None:
        scope = ChapterScope.model_validate({"search_queries": ["a", "b", "c"]})
        assert scope.search_queries == ["a", "b", "c"]


def _fake_results(queries: list[str]) -> Iterator[list[SearchResult]]:
    """Yield one SearchResult per query, unique URLs."""
    for q in queries:
        yield [SearchResult(title=f"T-{q}", url=f"https://example.com/{q}", content="c", score=0.5)]


@pytest.mark.unit
class TestSearchForChapterCustomQueries:
    """search_for_chapter with custom_queries."""

    def test_custom_queries_used(self) -> None:
        """When custom_queries is set, search() is called once per query with max_results=3."""
        queries = ["BEGASOFT Brandbot", "Evoya AI Schweiz"]
        calls: list[tuple[str, int]] = []

        def fake_search(query: str, max_results: int = 5, **_: object) -> list[SearchResult]:
            calls.append((query, max_results))
            return [SearchResult(title=f"T-{query}", url=f"https://ex.com/{query}", content="", score=0.5)]

        with patch.object(web_search, "search", side_effect=fake_search):
            results = search_for_chapter("07-markt-anbieter", "Markt", custom_queries=queries)

        assert [c[0] for c in calls] == queries
        assert all(c[1] == 3 for c in calls)
        assert len(results) == 2
        assert {r.url for r in results} == {"https://ex.com/BEGASOFT Brandbot", "https://ex.com/Evoya AI Schweiz"}

    def test_custom_queries_dedup(self) -> None:
        """Duplicate URLs across queries are deduplicated."""
        dupe = SearchResult(title="T", url="https://dupe.com", content="", score=0.5)

        with patch.object(web_search, "search", return_value=[dupe]):
            results = search_for_chapter("07", "Markt", custom_queries=["q1", "q2", "q3"])

        assert len(results) == 1

    def test_fallback_when_no_custom_queries(self) -> None:
        """Without custom_queries, the generic two-search path runs."""
        calls: list[tuple[str, int]] = []

        def fake_search(query: str, max_results: int = 5, **_: object) -> list[SearchResult]:
            calls.append((query, max_results))
            return []

        with patch.object(web_search, "search", side_effect=fake_search):
            search_for_chapter("01-plattform-architektur", "Plattform Architektur", scope="ch")

        assert len(calls) == 2
        assert "2026" in calls[0][0]
        assert "2025" not in calls[0][0]

    def test_empty_custom_queries_list_falls_back(self) -> None:
        """An empty list is treated like None (fallback runs)."""
        calls: list[str] = []

        def fake_search(query: str, max_results: int = 5, **_: object) -> list[SearchResult]:
            calls.append(query)
            return []

        with patch.object(web_search, "search", side_effect=fake_search):
            search_for_chapter("01", "Test", custom_queries=[])

        assert len(calls) == 2
