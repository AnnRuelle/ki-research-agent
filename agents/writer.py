"""Writer Agent: integrates findings into existing chapter content."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from agents.llm.factory import create_provider
from agents.llm.provider import LLMProvider
from agents.parser import FourZoneDocument, parse

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
Du bist ein Writer-Agent für eine Wissensdatenbank über KI-Plattformen für kantonale Verwaltungen in der Schweiz.

Deine Aufgabe: Integriere einen neuen Fund in den bestehenden Überblick-Text einer Seite.

Regeln:
- Schreibe sachlich, präzise und für Entscheidungsträger in der öffentlichen Verwaltung
- Integriere ALLE bereitgestellten Funde nahtlos in den bestehenden Text — kein Anhängen, sondern Einarbeiten
- Verarbeite JEDEN einzelnen Fund. Ignoriere keinen.
- Halte das Soft-Limit von ~2000 Wörtern ein. Kürze wenn nötig ältere Details
- Aktualisiere die Schlüsselquellen-Sektion mit den neuen Quellen
- Ändere NIEMALS die "Eigene Notizen"-Zone — gib sie exakt so zurück wie sie ist
- Bereite einen Changelog-Eintrag vor
- Sprache: Deutsch, Fachbegriffe auf Englisch okay

Antwort-Format: Gib das komplette Markdown-Dokument zurück im Vier-Zonen-Format:
# [Titel]
## Überblick
[Aktualisierter Text]
## Eigene Notizen
[EXAKT wie im Original]
## Schlüsselquellen
[Aktualisiert]
## Changelog
[Neuer Eintrag + bestehende Einträge]
"""


def _build_user_prompt(doc: FourZoneDocument, findings_json: str, finding_count: int) -> str:
    """Build the user prompt for the writer."""
    return f"""\
## Aktuelle Seite:
{doc.to_markdown()}

## Funde ({finding_count} Stück — ALLE verarbeiten!):
{findings_json}

Integriere ALLE {finding_count} Funde in den Überblick-Text. Jeder Fund muss im Text oder in den \
Schlüsselquellen verarbeitet werden. Behalte den bestehenden Inhalt bei und ergänze ihn sinnvoll.
Die "Eigene Notizen"-Zone muss EXAKT unverändert bleiben.
Der Changelog-Eintrag muss ALLE verarbeiteten Funde referenzieren."""


def _generate_diff(original: FourZoneDocument, updated: FourZoneDocument) -> str:
    """Generate a human-readable diff between original and updated document."""
    parts: list[str] = ["## Änderungen\n"]

    # Compare overview
    if original.overview != updated.overview:
        # Simple diff: show what changed
        orig_lines = set(original.overview.split("\n"))
        new_lines = set(updated.overview.split("\n"))
        added = new_lines - orig_lines
        removed = orig_lines - new_lines

        if added:
            parts.append("### Hinzugefügt (Überblick)")
            for line in sorted(added):
                if line.strip():
                    parts.append(f"> {line}")
            parts.append("")

        if removed:
            parts.append("### Entfernt (Überblick)")
            for line in sorted(removed):
                if line.strip():
                    parts.append(f"~{line}~")
            parts.append("")

    # Compare sources
    if original.key_sources != updated.key_sources:
        orig_sources = set(original.key_sources.split("\n"))
        new_sources = set(updated.key_sources.split("\n"))
        added_sources = new_sources - orig_sources

        if added_sources:
            parts.append("### Neue Schlüsselquellen")
            for line in sorted(added_sources):
                if line.strip():
                    parts.append(f"> {line}")
            parts.append("")

    # Changelog
    if original.changelog != updated.changelog:
        parts.append("### Neuer Changelog-Eintrag")
        new_entries = updated.changelog.split("\n")
        for entry in new_entries:
            if entry.strip() and entry not in original.changelog:
                parts.append(f"> {entry}")
        parts.append("")

    if len(parts) == 1:
        parts.append("~Nichts geändert.~")

    return "\n".join(parts)


def write_draft(
    chapter_id: str,
    subpage: str,
    finding_path: Path | None = None,
    finding_data: dict[str, object] | None = None,
    findings_list: list[dict[str, object]] | None = None,
    provider: LLMProvider | None = None,
    output_dir: Path | None = None,
) -> FourZoneDocument:
    """Write a draft integrating findings into a chapter subpage.

    Args:
        chapter_id: Chapter identifier (e.g. "01-plattform-architektur").
        subpage: Subpage filename (e.g. "ai-gateway.md").
        finding_path: Path to findings JSON file (array or single object).
        finding_data: Single finding data dict.
        findings_list: List of finding dicts (preferred for multiple findings).
        provider: LLM provider (created from config if None).
        output_dir: Output directory for draft and diff.

    Returns:
        Updated FourZoneDocument.
    """
    if output_dir is None:
        output_dir = Path("tests/output")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load findings — support single or multiple
    if findings_list is not None:
        all_findings = findings_list
    elif finding_data is not None:
        all_findings = [finding_data]
    elif finding_path is not None:
        raw = json.loads(finding_path.read_text(encoding="utf-8"))
        all_findings = raw if isinstance(raw, list) else [raw]
    else:
        msg = "Either finding_path, finding_data, or findings_list must be provided"
        raise ValueError(msg)

    finding_json = json.dumps(all_findings, ensure_ascii=False, indent=2)
    finding_count = len(all_findings)

    # Load current page
    page_path = Path("chapters") / chapter_id / subpage
    if not page_path.exists():
        msg = f"Page not found: {page_path}"
        raise FileNotFoundError(msg)

    original_text = page_path.read_text(encoding="utf-8")
    original_doc = parse(original_text)

    # Create provider
    if provider is None:
        from agents.config_schema import load_config

        config = load_config()
        provider = create_provider(config.agents["writer"])

    # Call LLM
    user_prompt = _build_user_prompt(original_doc, finding_json, finding_count)
    logger.info("Writer: drafting update for %s/%s", chapter_id, subpage)
    response = provider.complete(system=SYSTEM_PROMPT, user=user_prompt, temperature=0.3)

    # Parse response
    updated_doc = parse(response.content)

    # CRITICAL: Restore original own_notes (safety net)
    updated_doc.own_notes = original_doc.own_notes

    # Calculate word count change
    orig_words = len(original_doc.overview.split())
    new_words = len(updated_doc.overview.split())
    pct_change = ((new_words - orig_words) / max(orig_words, 1)) * 100

    logger.info(
        "Writer: %s/%s — %d -> %d words (%+.0f%%)",
        chapter_id, subpage, orig_words, new_words, pct_change,
    )

    # Save outputs
    draft_file = output_dir / "writer_draft.md"
    draft_file.write_text(updated_doc.to_markdown(), encoding="utf-8")

    diff_file = output_dir / "writer_diff.md"
    diff_file.write_text(_generate_diff(original_doc, updated_doc), encoding="utf-8")

    return updated_doc


def main() -> None:
    """CLI entry point."""
    import sys

    from agents.logging_config import setup_logging

    setup_logging()
    chapter = sys.argv[1] if len(sys.argv) > 1 else "01-plattform-architektur"
    finding = sys.argv[2] if len(sys.argv) > 2 else "tests/output/researcher_findings.json"
    subpage = sys.argv[3] if len(sys.argv) > 3 else "ai-gateway.md"

    write_draft(chapter, subpage, finding_path=Path(finding))
    print(f"\nDraft: tests/output/writer_draft.md")
    print(f"Diff:  tests/output/writer_diff.md")


if __name__ == "__main__":
    main()
