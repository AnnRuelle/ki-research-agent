"""Resolver Agent: reconciles writer draft with critic feedback."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from agents.llm.factory import create_provider
from agents.llm.provider import LLMProvider
from agents.parser import FourZoneDocument, parse

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_TEMPLATE = """\
Du bist ein Resolver-Agent für eine Wissensdatenbank über KI-Plattformen für kantonale Verwaltungen.

Deine Aufgabe: Überarbeite den Writer-Draft basierend auf dem Critic-Feedback.

Regeln:
- Setze alle "major" Issues des Critics um
- "minor" Issues nach eigenem Ermessen — im Zweifel umsetzen
- "nit" Issues nur wenn sie die Qualität klar verbessern
- Wenn der Critic "approve" sagt: Draft unverändert übernehmen
- Die "Eigene Notizen"-Zone darf NIEMALS verändert werden
- Changelog-Einträge verwenden das RECHERCHE-DATUM (heute: {TODAY}), NICHT das Quell-Datum
  Format: - YYYY-MM-DD: Beschreibung
- Wenn Issues nicht lösbar sind: markiere sie als Flag für die PL

Antwort: Gib das komplette Markdown-Dokument zurück im Vier-Zonen-Format:
# [Titel]
## Überblick
[Finale Version]
## Eigene Notizen
[EXAKT wie im Draft/Original]
## Schlüsselquellen
[Finale Version]
## Changelog
[Finaler Eintrag]
"""


def _build_user_prompt(draft_text: str, critic_json: str) -> str:
    """Build the user prompt for the resolver."""
    return f"""\
## Writer-Draft:
{draft_text}

## Critic-Review:
{critic_json}

Setze das Critic-Feedback um und erstelle die finale Version.
Die "Eigene Notizen"-Zone muss EXAKT unverändert bleiben."""


def _generate_diff(draft_doc: FourZoneDocument, final_doc: FourZoneDocument) -> str:
    """Generate diff between writer draft and resolver final."""
    parts: list[str] = ["## Resolver-Änderungen (Draft -> Final)\n"]

    if draft_doc.overview != final_doc.overview:
        parts.append("### Überblick geändert")
        draft_lines = set(draft_doc.overview.split("\n"))
        final_lines = set(final_doc.overview.split("\n"))
        for line in sorted(final_lines - draft_lines):
            if line.strip():
                parts.append(f"> {line}")
        removed = draft_lines - final_lines
        if removed:
            parts.append("\n**Entfernt:**")
            for line in sorted(removed):
                if line.strip():
                    parts.append(f"~{line}~")
        parts.append("")

    if draft_doc.key_sources != final_doc.key_sources:
        parts.append("### Schlüsselquellen geändert")
        parts.append(f"> {final_doc.key_sources[:200]}...")
        parts.append("")

    if len(parts) == 1:
        parts.append("~Keine Änderungen gegenüber dem Draft.~")

    return "\n".join(parts)


def resolve_draft(
    draft_path: Path,
    critic_path: Path,
    original_path: Path | None = None,
    provider: LLMProvider | None = None,
    output_dir: Path | None = None,
) -> FourZoneDocument:
    """Resolve a writer draft with critic feedback.

    Args:
        draft_path: Path to writer draft markdown.
        critic_path: Path to critic review JSON.
        original_path: Path to original file (for own_notes safety).
        provider: LLM provider.
        output_dir: Output directory.

    Returns:
        Final resolved FourZoneDocument.
    """
    if output_dir is None:
        output_dir = Path("tests/output")
    output_dir.mkdir(parents=True, exist_ok=True)

    draft_text = draft_path.read_text(encoding="utf-8")
    critic_json = critic_path.read_text(encoding="utf-8")
    draft_doc = parse(draft_text)

    # Check if critic approved — no LLM call needed
    try:
        critic_data = json.loads(critic_json)
        if critic_data.get("verdict") == "approve":
            logger.info("Resolver: Critic approved, using draft as-is")
            final_doc = draft_doc

            (output_dir / "resolver_final.md").write_text(final_doc.to_markdown(), encoding="utf-8")
            (output_dir / "resolver_diff.md").write_text("~Keine Änderungen. Critic: approve.~", encoding="utf-8")
            return final_doc
    except json.JSONDecodeError:
        pass

    # Create provider
    if provider is None:
        from agents.config_schema import load_config

        config = load_config()
        provider = create_provider(config.agents["resolver"], agent_name="resolver")

    # Call LLM
    user_prompt = _build_user_prompt(draft_text, critic_json)
    today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    system_prompt = SYSTEM_PROMPT_TEMPLATE.replace("{TODAY}", today)
    logger.info("Resolver: resolving draft with critic feedback")
    response = provider.complete(system=system_prompt, user=user_prompt, temperature=0.2)

    # Parse response
    final_doc = parse(response.content)

    # CRITICAL: Restore original own_notes
    if original_path is not None:
        original_doc = parse(original_path.read_text(encoding="utf-8"))
        final_doc.own_notes = original_doc.own_notes
    else:
        final_doc.own_notes = draft_doc.own_notes

    # Save outputs
    final_file = output_dir / "resolver_final.md"
    final_file.write_text(final_doc.to_markdown(), encoding="utf-8")

    diff_file = output_dir / "resolver_diff.md"
    diff_file.write_text(_generate_diff(draft_doc, final_doc), encoding="utf-8")

    logger.info("Resolver: final saved -> %s", final_file)
    return final_doc


def main() -> None:
    """CLI entry point."""
    from agents.logging_config import setup_logging

    setup_logging()
    resolve_draft(
        draft_path=Path("tests/output/writer_draft.md"),
        critic_path=Path("tests/output/critic_review.json"),
        original_path=Path("tests/fixtures/sample_chapter.md"),
    )
    print("\nFinal: tests/output/resolver_final.md")
    print("Diff:  tests/output/resolver_diff.md")


if __name__ == "__main__":
    main()
