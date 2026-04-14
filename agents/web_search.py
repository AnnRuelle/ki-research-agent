"""Web search integration via Tavily API."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """A single web search result."""

    title: str
    url: str
    content: str
    score: float


def search(
    query: str,
    max_results: int = 5,
    search_depth: str = "advanced",
    include_domains: list[str] | None = None,
    exclude_domains: list[str] | None = None,
) -> list[SearchResult]:
    """Search the web via Tavily API.

    Args:
        query: Search query string.
        max_results: Maximum number of results.
        search_depth: "basic" (fast) or "advanced" (deeper).
        include_domains: Only search these domains.
        exclude_domains: Exclude these domains.

    Returns:
        List of SearchResult objects.
    """
    api_key = os.environ.get("TAVILY_API_KEY", "")
    if not api_key:
        logger.warning("TAVILY_API_KEY not set — web search disabled")
        return []

    try:
        from tavily import TavilyClient

        client = TavilyClient(api_key=api_key)

        kwargs: dict[str, object] = {
            "query": query,
            "search_depth": search_depth,
            "max_results": max_results,
        }
        if include_domains:
            kwargs["include_domains"] = include_domains
        if exclude_domains:
            kwargs["exclude_domains"] = exclude_domains

        response = client.search(**kwargs)

    except ImportError:
        logger.error("tavily-python not installed: pip install tavily-python")
        return []
    except Exception:
        logger.exception("Tavily search failed for query: %s", query[:80])
        return []

    results: list[SearchResult] = []
    for item in response.get("results", []):
        results.append(
            SearchResult(
                title=item.get("title", ""),
                url=item.get("url", ""),
                content=item.get("content", ""),
                score=float(item.get("score", 0.0)),
            )
        )

    logger.info("Web search: %d results for '%s'", len(results), query[:60])
    return results


def search_for_chapter(chapter_id: str, chapter_title: str, scope: str = "ch") -> list[SearchResult]:
    """Search for information relevant to a specific chapter.

    Args:
        chapter_id: Chapter identifier.
        chapter_title: Human-readable chapter title.
        scope: Geographic scope (ch, dach, global).

    Returns:
        List of search results.
    """
    scope_terms = {
        "ch": "Schweiz kantonale Verwaltung",
        "dach": "Deutschland Österreich Schweiz öffentliche Verwaltung",
        "global": "",
    }
    geo = scope_terms.get(scope, "")

    query = f"KI Plattform {chapter_title} {geo} 2025 2026".strip()

    # Search with Swiss/gov focus
    swiss_domains = [
        "admin.ch",
        "digitale-verwaltung-schweiz.ch",
        "ncsc.admin.ch",
        "edoeb.admin.ch",
        "bk.admin.ch",
    ]

    # Do two searches: one focused on Swiss gov, one broader
    results: list[SearchResult] = []

    # Swiss government search
    swiss_results = search(query, max_results=3, include_domains=swiss_domains)
    results.extend(swiss_results)

    # Broader search
    broad_results = search(query, max_results=5)
    # Deduplicate by URL
    seen_urls = {r.url for r in results}
    for r in broad_results:
        if r.url not in seen_urls:
            results.append(r)
            seen_urls.add(r.url)

    logger.info("Chapter search %s: %d total results", chapter_id, len(results))
    return results
