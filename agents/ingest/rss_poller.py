"""RSS Poller: fetches RSS feeds defined in sources.yaml and stores new items."""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from time import struct_time
from typing import Any

import feedparser

from agents.config_schema import SourcesConfig, load_sources

logger = logging.getLogger(__name__)

SOURCES_DIR = Path("sources/newsletters")


@dataclass
class RSSItem:
    """A single RSS feed item."""

    source_name: str
    title: str
    url: str
    published: str
    summary: str
    chapters: list[str]
    item_hash: str


def _parse_date(entry: Any) -> str:
    """Extract and normalize a publication date from a feed entry."""
    published_parsed: struct_time | None = getattr(entry, "published_parsed", None)
    if published_parsed:
        return datetime(*published_parsed[:6], tzinfo=timezone.utc).isoformat()
    published_str: str = getattr(entry, "published", "")
    if published_str:
        return published_str
    return datetime.now(tz=timezone.utc).isoformat()


def _hash_item(url: str, title: str) -> str:
    """Create a stable hash for deduplication."""
    return hashlib.sha256(f"{url}|{title}".encode()).hexdigest()[:16]


def _load_seen_hashes(output_dir: Path) -> set[str]:
    """Load hashes of previously seen items."""
    seen: set[str] = set()
    if not output_dir.exists():
        return seen
    for file in output_dir.glob("*.json"):
        try:
            data = json.loads(file.read_text(encoding="utf-8"))
            items = data if isinstance(data, list) else [data]
            for item in items:
                if "item_hash" in item:
                    seen.add(item["item_hash"])
        except (json.JSONDecodeError, KeyError):
            continue
    return seen


def poll_feed(
    name: str, url: str, chapters: list[str], seen_hashes: set[str]
) -> list[RSSItem]:
    """Poll a single RSS feed and return new items."""
    logger.info("Polling RSS feed: %s", name)
    try:
        feed = feedparser.parse(url)
    except Exception:
        logger.exception("Failed to parse feed: %s", url)
        return []

    if feed.bozo:
        logger.warning("Feed parse warning for %s: %s", name, feed.bozo_exception)
        if not feed.entries:
            return []

    new_items: list[RSSItem] = []
    for entry in feed.entries:
        title: str = getattr(entry, "title", "Untitled")
        link: str = getattr(entry, "link", "")
        item_hash = _hash_item(link, title)

        if item_hash in seen_hashes:
            continue

        summary: str = getattr(entry, "summary", "")
        # Truncate long summaries
        if len(summary) > 1000:
            summary = summary[:1000] + "..."

        item = RSSItem(
            source_name=name,
            title=title,
            url=link,
            published=_parse_date(entry),
            summary=summary,
            chapters=chapters,
            item_hash=item_hash,
        )
        new_items.append(item)
        seen_hashes.add(item_hash)

    logger.info("Feed %s: %d new items (of %d total)", name, len(new_items), len(feed.entries))
    return new_items


def poll_all(sources: SourcesConfig | None = None, output_dir: Path | None = None) -> list[RSSItem]:
    """Poll all RSS feeds from sources.yaml. Returns list of new items."""
    if sources is None:
        sources = load_sources()
    if output_dir is None:
        output_dir = SOURCES_DIR

    output_dir.mkdir(parents=True, exist_ok=True)
    seen_hashes = _load_seen_hashes(output_dir)
    all_new: list[RSSItem] = []

    for rss in sources.rss:
        new_items = poll_feed(rss.name, rss.url, rss.chapters, seen_hashes)
        all_new.extend(new_items)

    if all_new:
        date_str = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
        out_file = output_dir / f"rss-{date_str}.json"
        out_file.write_text(
            json.dumps([asdict(item) for item in all_new], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("Saved %d new RSS items to %s", len(all_new), out_file)
    else:
        logger.info("No new RSS items found")

    return all_new


def main() -> None:
    """CLI entry point."""
    from agents.logging_config import setup_logging

    setup_logging()
    items = poll_all()
    print(f"\n{'='*60}")
    print(f"RSS Ingest complete: {len(items)} new items")
    for item in items:
        print(f"  - [{item.source_name}] {item.title}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
