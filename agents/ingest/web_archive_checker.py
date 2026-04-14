"""Web Archive Checker: detects changes on monitored websites and archives."""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

from agents.config_schema import SourcesConfig, load_sources

logger = logging.getLogger(__name__)

ARCHIVE_DIR = Path("sources/web-archives")
TIMEOUT_SECONDS = 30
MAX_CONTENT_BYTES = 500_000  # 500KB max per page
USER_AGENT = "KI-KB-WebArchiveChecker/1.0"


@dataclass
class WebChange:
    """A detected change on a monitored website."""

    source_name: str
    url: str
    chapters: list[str]
    detected_at: str
    content_hash: str
    previous_hash: str | None
    snippet: str


def _fetch_url(url: str) -> str | None:
    """Fetch URL content as text. Returns None on failure."""
    try:
        req = Request(url, headers={"User-Agent": USER_AGENT})  # noqa: S310
        with urlopen(req, timeout=TIMEOUT_SECONDS) as resp:  # noqa: S310
            content_bytes = resp.read(MAX_CONTENT_BYTES)
            charset = resp.headers.get_content_charset() or "utf-8"
            return content_bytes.decode(charset, errors="replace")
    except (URLError, TimeoutError, OSError):
        logger.exception("Failed to fetch: %s", url)
        return None


def _content_hash(content: str) -> str:
    """Hash page content for change detection."""
    return hashlib.sha256(content.encode()).hexdigest()[:20]


def _extract_snippet(content: str, max_length: int = 500) -> str:
    """Extract a text snippet from HTML content (simple, no parsing)."""
    # Strip tags naively for snippet
    import re

    text = re.sub(r"<[^>]+>", " ", content)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_length]


def _load_hash_index(index_file: Path) -> dict[str, str]:
    """Load the hash index mapping URL -> last known content hash."""
    if index_file.exists():
        try:
            return json.loads(index_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def _save_hash_index(index_file: Path, index: dict[str, str]) -> None:
    """Save the hash index."""
    index_file.write_text(
        json.dumps(index, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def check_all(
    sources: SourcesConfig | None = None, output_dir: Path | None = None
) -> list[WebChange]:
    """Check all websites and archives for changes. Returns list of changes."""
    if sources is None:
        sources = load_sources()
    if output_dir is None:
        output_dir = ARCHIVE_DIR

    output_dir.mkdir(parents=True, exist_ok=True)
    index_file = output_dir / "_hash_index.json"
    hash_index = _load_hash_index(index_file)

    all_sources = [
        (s.name, s.url, s.chapters) for s in sources.websites
    ] + [
        (s.name, s.url, s.chapters) for s in sources.archives
    ]

    changes: list[WebChange] = []

    for name, url, chapters in all_sources:
        logger.info("Checking: %s (%s)", name, url)
        content = _fetch_url(url)
        if content is None:
            continue

        new_hash = _content_hash(content)
        prev_hash = hash_index.get(url)

        if prev_hash == new_hash:
            logger.info("No change: %s", name)
            continue

        change = WebChange(
            source_name=name,
            url=url,
            chapters=chapters,
            detected_at=datetime.now(tz=timezone.utc).isoformat(),
            content_hash=new_hash,
            previous_hash=prev_hash,
            snippet=_extract_snippet(content),
        )
        changes.append(change)
        hash_index[url] = new_hash

        logger.info(
            "Change detected: %s (hash: %s -> %s)",
            name,
            prev_hash or "new",
            new_hash,
        )

    # Save updated index
    _save_hash_index(index_file, hash_index)

    # Save changes
    if changes:
        date_str = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
        out_file = output_dir / f"changes-{date_str}.json"
        out_file.write_text(
            json.dumps([asdict(c) for c in changes], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("Saved %d web changes to %s", len(changes), out_file)
    else:
        logger.info("No web changes detected")

    return changes


def main() -> None:
    """CLI entry point."""
    from agents.logging_config import setup_logging

    setup_logging()
    changes = check_all()
    print(f"\n{'='*60}")
    print(f"Web Archive Check complete: {len(changes)} changes detected")
    for change in changes:
        status = "NEW" if change.previous_hash is None else "CHANGED"
        print(f"  - [{status}] {change.source_name}: {change.url}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
