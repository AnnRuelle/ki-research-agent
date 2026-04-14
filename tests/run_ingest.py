"""Test runner: executes RSS poller and web archive checker with real output."""

from __future__ import annotations

import json
from pathlib import Path

from agents.ingest.rss_poller import poll_all
from agents.ingest.web_archive_checker import check_all
from agents.logging_config import setup_logging

OUTPUT_DIR = Path("tests/output")


def main() -> None:
    """Run ingest agents and save results for PL review."""
    setup_logging(level="INFO")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # RSS
    print("=" * 60)
    print("Running RSS Poller...")
    print("=" * 60)
    rss_items = poll_all()

    rss_out = OUTPUT_DIR / "rss_ingest.json"
    rss_out.write_text(
        json.dumps(
            [
                {
                    "source": item.source_name,
                    "title": item.title,
                    "url": item.url,
                    "published": item.published,
                    "chapters": item.chapters,
                }
                for item in rss_items
            ],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"\nRSS: {len(rss_items)} neue Items")
    for item in rss_items[:5]:
        print(f"  - [{item.source_name}] {item.title}")
    if len(rss_items) > 5:
        print(f"  ... und {len(rss_items) - 5} weitere")

    # Web Archive
    print("\n" + "=" * 60)
    print("Running Web Archive Checker...")
    print("=" * 60)
    changes = check_all()

    web_out = OUTPUT_DIR / "web_changes.json"
    web_out.write_text(
        json.dumps(
            [
                {
                    "source": c.source_name,
                    "url": c.url,
                    "chapters": c.chapters,
                    "status": "NEW" if c.previous_hash is None else "CHANGED",
                    "snippet": c.snippet[:200],
                }
                for c in changes
            ],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"\nWeb: {len(changes)} Änderungen")
    for change in changes:
        status = "NEW" if change.previous_hash is None else "CHANGED"
        print(f"  - [{status}] {change.source_name}")

    # Summary
    print("\n" + "=" * 60)
    print("ZUSAMMENFASSUNG")
    print(f"  RSS Items:    {len(rss_items)}")
    print(f"  Web Changes:  {len(changes)}")
    print(f"  Output:       {rss_out}")
    print(f"                {web_out}")
    print("=" * 60)
    print("\n>> Bitte tests/output/rss_ingest.json und web_changes.json reviewen.")


if __name__ == "__main__":
    main()
