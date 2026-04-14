"""Changelog Trimmer: removes entries older than 3 months from all changelogs."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from agents.parser import parse

logger = logging.getLogger(__name__)

CHAPTERS_DIR = Path("chapters")
MAX_AGE_DAYS = 90  # ~3 months


def trim_changelog(changelog: str, cutoff_date: str) -> str:
    """Remove changelog entries older than cutoff_date.

    Args:
        changelog: Full changelog text.
        cutoff_date: YYYY-MM-DD string. Entries before this are removed.

    Returns:
        Trimmed changelog.
    """
    lines = changelog.split("\n")
    kept: list[str] = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("- ") and len(stripped) > 12:
            date_part = stripped[2:12]
            if len(date_part) == 10 and date_part[4] == "-" and date_part[7] == "-" and date_part < cutoff_date:
                continue  # Skip old entry
        kept.append(line)

    return "\n".join(kept)


def trim_all_changelogs(cutoff_date: str | None = None) -> int:
    """Trim changelogs in all chapter files.

    Args:
        cutoff_date: YYYY-MM-DD cutoff. Defaults to 90 days ago.

    Returns:
        Number of files modified.
    """
    if cutoff_date is None:
        now = datetime.now(tz=timezone.utc)
        from datetime import timedelta

        cutoff = now - timedelta(days=MAX_AGE_DAYS)
        cutoff_date = cutoff.strftime("%Y-%m-%d")

    modified = 0

    for md_file in sorted(CHAPTERS_DIR.glob("**/*.md")):
        try:
            text = md_file.read_text(encoding="utf-8")
            doc = parse(text)

            trimmed = trim_changelog(doc.changelog, cutoff_date)
            if trimmed != doc.changelog:
                doc.changelog = trimmed
                md_file.write_text(doc.to_markdown(), encoding="utf-8")
                modified += 1
                logger.info("Trimmed changelog: %s", md_file)
        except Exception:
            continue

    logger.info("Changelog trimming: %d files modified (cutoff: %s)", modified, cutoff_date)
    return modified


def update_global_changelog(cutoff_date: str | None = None) -> None:
    """Update the global CHANGELOG.md from all chapter changelogs."""
    if cutoff_date is None:
        now = datetime.now(tz=timezone.utc)
        from datetime import timedelta

        cutoff = now - timedelta(days=MAX_AGE_DAYS)
        cutoff_date = cutoff.strftime("%Y-%m-%d")

    entries: list[tuple[str, str, str]] = []  # (date, path, description)

    for md_file in sorted(CHAPTERS_DIR.glob("**/*.md")):
        try:
            doc = parse(md_file.read_text(encoding="utf-8"))
            rel_path = md_file.relative_to(CHAPTERS_DIR)
            for line in doc.changelog.split("\n"):
                stripped = line.strip()
                if stripped.startswith("- ") and len(stripped) > 12:
                    date_part = stripped[2:12]
                    desc = stripped[14:] if len(stripped) > 14 else ""
                    if date_part >= cutoff_date:
                        entries.append((date_part, str(rel_path), desc))
        except Exception:
            continue

    entries.sort(key=lambda x: x[0], reverse=True)

    lines = ["# Changelog\n"]
    if entries:
        for date, path, desc in entries:
            lines.append(f"- **{date}** `{path}`: {desc}")
    else:
        lines.append("*Noch keine Eintraege.*")
    lines.append("")

    Path("CHANGELOG.md").write_text("\n".join(lines), encoding="utf-8")
    logger.info("Global CHANGELOG.md updated: %d entries", len(entries))


def main() -> None:
    """CLI entry point."""
    from agents.logging_config import setup_logging

    setup_logging()
    modified = trim_all_changelogs()
    update_global_changelog()
    print(f"Trimmed {modified} files. CHANGELOG.md updated.")


if __name__ == "__main__":
    main()
