"""Merger Agent: commits resolved content, updates dashboard and chapter indexes.

Pure code — no LLM calls. Reads resolver output and applies changes.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from agents.parser import parse

logger = logging.getLogger(__name__)

CHAPTERS_DIR = Path("chapters")
FRESHNESS_DAYS = {"green": 7, "yellow": 21}


def merge_resolved(
    chapter_id: str,
    subpage: str,
    resolved_path: Path,
    critic_verdict: str = "approve",
    auto_merged: bool = True,
) -> Path:
    """Merge resolved content into the chapter.

    Args:
        chapter_id: Chapter identifier.
        subpage: Subpage filename.
        resolved_path: Path to resolver_final.md.
        critic_verdict: Critic verdict for changelog.
        auto_merged: Whether this was auto-merged or manually approved.

    Returns:
        Path to the updated file.
    """
    target = CHAPTERS_DIR / chapter_id / subpage
    resolved_doc = parse(resolved_path.read_text(encoding="utf-8"))

    # Safety: if target exists, preserve own_notes
    if target.exists():
        original_doc = parse(target.read_text(encoding="utf-8"))
        resolved_doc.own_notes = original_doc.own_notes

    target.write_text(resolved_doc.to_markdown(), encoding="utf-8")
    logger.info("Merged: %s/%s", chapter_id, subpage)

    return target


def update_chapter_index(chapter_id: str) -> None:
    """Update a chapter's index.md with current subpage listing."""
    chapter_dir = CHAPTERS_DIR / chapter_id
    index_path = chapter_dir / "index.md"

    if not index_path.exists():
        return

    index_doc = parse(index_path.read_text(encoding="utf-8"))

    # Build subpage listing
    subpages: list[str] = []
    for md_file in sorted(chapter_dir.glob("*.md")):
        if md_file.name == "index.md":
            continue
        try:
            sub_doc = parse(md_file.read_text(encoding="utf-8"))
            # Extract last changelog date
            last_date = _extract_last_date(sub_doc.changelog)
            date_str = f"Zuletzt: {last_date}" if last_date else "Noch kein Update"
            subpages.append(f"- **[{sub_doc.title}]({md_file.name})** -- {date_str}")
        except Exception:
            subpages.append(f"- **[{md_file.stem}]({md_file.name})** -- Parse-Fehler")

    # Also check subdirectories
    for sub_dir in sorted(chapter_dir.iterdir()):
        if sub_dir.is_dir():
            sub_index = sub_dir / "index.md"
            if sub_index.exists():
                try:
                    sub_doc = parse(sub_index.read_text(encoding="utf-8"))
                    subpages.append(f"- **[{sub_doc.title}]({sub_dir.name}/index.md)**")
                except Exception:
                    subpages.append(f"- **[{sub_dir.name}]({sub_dir.name}/index.md)**")

    index_doc.overview = "\n".join(subpages) if subpages else "*Keine Unterseiten.*"
    index_path.write_text(index_doc.to_markdown(), encoding="utf-8")
    logger.info("Updated chapter index: %s", chapter_id)


def update_dashboard() -> None:
    """Update the root index.md dashboard with current chapter status."""
    dashboard_path = Path("index.md")
    now = datetime.now(tz=timezone.utc)

    rows: list[str] = []
    rows.append("| Kapitel | Aktueller Fokus | Letzte Änderung | Frische |")
    rows.append("|---|---|---|---|")

    chapter_names: dict[str, str] = {
        "01-plattform-architektur": "01 Plattform-Architektur",
        "02-use-cases": "02 Use Cases",
        "03-datenschutz-informationssicherheit": "03 Datenschutz & Informationssicherheit",
        "04-governance-betriebsmodell": "04 Governance & Betriebsmodell",
        "05-regulatorik": "05 Regulatorik",
        "06-change-management": "06 Change Management",
        "07-markt-anbieter": "07 Markt & Anbieter",
        "08-integration-it-landschaft": "08 Integration IT-Landschaft",
        "09-kosten-lizenzmodelle": "09 Kosten & Lizenzmodelle",
        "10-referenzprojekte-kantone": "10 Referenzprojekte Kantone",
        "11-erfolgsmessung": "11 Erfolgsmessung",
        "12-beschaffung": "12 Beschaffung",
        "13-sustainable-it-ki": "13 Sustainable IT & KI",
    }

    for chapter_id, display_name in chapter_names.items():
        chapter_dir = CHAPTERS_DIR / chapter_id
        if not chapter_dir.exists():
            continue

        last_date, focus = _get_chapter_status(chapter_dir)
        freshness = _freshness_indicator(last_date, now)
        date_display = last_date if last_date else "--"
        focus_display = focus if focus else "*Noch kein Inhalt*"

        rows.append(
            f"| [{display_name}](chapters/{chapter_id}/index.md) | {focus_display} | {date_display} | {freshness} |"
        )

    dashboard_content = f"""\
# KI-Plattform fuer kantonale Verwaltung -- Wissensdatenbank

## Status Dashboard

{chr(10).join(rows)}

Legende: aktuell (< 7d) -- veraltet (7-21d) -- stark veraltet (> 21d) -- nie aktualisiert

## Was ist neu (letzte 4 Wochen)

{_get_recent_changes()}
"""
    dashboard_path.write_text(dashboard_content, encoding="utf-8")
    logger.info("Dashboard updated")


def _get_chapter_status(chapter_dir: Path) -> tuple[str | None, str | None]:
    """Get the most recent date and focus (first sentence of overview) of a chapter."""
    latest_date: str | None = None
    latest_page_overview: str | None = None

    for md_file in chapter_dir.glob("**/*.md"):
        if md_file.name == "index.md":
            continue
        try:
            doc = parse(md_file.read_text(encoding="utf-8"))
            date = _extract_last_date(doc.changelog)
            if date and (latest_date is None or date > latest_date):
                latest_date = date
                # Use first sentence of overview as focus
                overview = doc.overview.strip()
                if overview and overview != "*Noch kein Inhalt. Wird durch den Research-Agent befüllt.*":
                    first_sentence = overview.split(".")[0].strip()
                    # Remove markdown formatting for clean display
                    clean = first_sentence.replace("**", "").replace("*", "").replace(">", "").strip()
                    latest_page_overview = f"{clean[:60]}"
        except Exception:
            continue

    return latest_date, latest_page_overview


def _extract_last_date(changelog: str) -> str | None:
    """Extract the most recent date from a changelog.

    Supports formats:
    - 2026-04-14: description
    - **2026-04-14**: description
    - **2026-04-14: description**
    """
    import re

    dates: list[str] = re.findall(r"(\d{4}-\d{2}-\d{2})", changelog)
    # Return the most recent (first found, since changelogs are reverse-chronological)
    return dates[0] if dates else None


def _freshness_indicator(date_str: str | None, now: datetime) -> str:
    """Return a freshness indicator based on age."""
    if date_str is None:
        return "nie aktualisiert"
    try:
        date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        days = (now - date).days
        if days <= FRESHNESS_DAYS["green"]:
            return "aktuell"
        if days <= FRESHNESS_DAYS["yellow"]:
            return "veraltet"
        return "stark veraltet"
    except ValueError:
        return "nie aktualisiert"


def _get_recent_changes() -> str:
    """Collect recent changes from all chapters."""
    # Collect one entry per subpage: (date, chapter_name, page_title, rel_link)
    page_updates: dict[str, tuple[str, str, str, str]] = {}

    for chapter_dir in sorted(CHAPTERS_DIR.iterdir()):
        if not chapter_dir.is_dir():
            continue
        chapter_name = chapter_dir.name.split("-", 1)[1].replace("-", " ").title() if "-" in chapter_dir.name else chapter_dir.name
        for md_file in chapter_dir.glob("**/*.md"):
            if md_file.name == "index.md":
                continue
            try:
                doc = parse(md_file.read_text(encoding="utf-8"))
                date = _extract_last_date(doc.changelog)
                if date:
                    # Use forward slashes for links
                    rel_path = str(md_file.relative_to(CHAPTERS_DIR)).replace("\\", "/")
                    key = rel_path
                    if key not in page_updates or date > page_updates[key][0]:
                        page_updates[key] = (date, chapter_name, doc.title, rel_path)
            except Exception:
                continue

    # Sort by date descending
    sorted_updates = sorted(page_updates.values(), key=lambda x: x[0], reverse=True)
    recent = sorted_updates[:15]

    if not recent:
        return "*Noch keine Updates. Wird automatisch vom Merger befuellt.*"

    lines = []
    for date, chapter_name, title, rel_path in recent:
        lines.append(f"- **{date}** [{chapter_name}: {title}](chapters/{rel_path})")
    return "\n".join(lines)


def main() -> None:
    """CLI entry point: update dashboard and all chapter indexes."""
    from agents.logging_config import setup_logging

    setup_logging()

    for chapter_dir in sorted(CHAPTERS_DIR.iterdir()):
        if chapter_dir.is_dir():
            update_chapter_index(chapter_dir.name)

    update_dashboard()
    print("Dashboard and chapter indexes updated.")


if __name__ == "__main__":
    main()
