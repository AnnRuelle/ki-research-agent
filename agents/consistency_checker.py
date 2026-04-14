"""Consistency Checker: finds cross-chapter contradictions."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path

from agents.llm.factory import create_provider
from agents.llm.provider import LLMProvider

logger = logging.getLogger(__name__)


@dataclass
class Contradiction:
    """A contradiction between two chapters."""

    chapter_a: str
    location_a: str
    chapter_b: str
    location_b: str
    description: str
    severity: str  # major, minor
    suggested_resolution: str


@dataclass
class ConsistencyReport:
    """Full consistency check report."""

    chapters_checked: list[str]
    contradictions: list[Contradiction]
    summary: str


SYSTEM_PROMPT = """\
Du bist ein Consistency-Checker für eine Wissensdatenbank über KI-Plattformen für kantonale Verwaltungen.

Deine Aufgabe: Finde kapitelübergreifende Widersprüche.

Beispiele für Widersprüche:
- Kapitel A sagt "On-Premise ist günstiger", Kapitel B sagt "Cloud ist günstiger"
- Kapitel A nennt einen Anbieter "zertifiziert", Kapitel B sagt "Zertifizierung ausstehend"
- Verschiedene Kapitel nennen verschiedene Zahlen für denselben Sachverhalt
- Veraltete Informationen in einem Kapitel, aktualisierte in einem anderen

Antwort als JSON:
{
  "summary": "Kurze Gesamteinschätzung",
  "contradictions": [
    {
      "chapter_a": "01-plattform-architektur/cloud-vs-hybrid.md",
      "location_a": "Absatz über Kosten",
      "chapter_b": "09-kosten-lizenzmodelle/tco-modelle.md",
      "location_b": "TCO-Vergleich Tabelle",
      "description": "Widersprüchliche Kostenangaben für On-Premise vs. Cloud",
      "severity": "major|minor",
      "suggested_resolution": "TCO-Modelle in Kap. 09 als Referenz verwenden"
    }
  ]
}

Wenn keine Widersprüche: {"summary": "Keine Widersprüche gefunden", "contradictions": []}
"""


def _load_chapters_content(chapter_ids: list[str]) -> str:
    """Load content from multiple chapters for comparison."""
    parts: list[str] = []
    for chapter_id in chapter_ids:
        chapter_dir = Path("chapters") / chapter_id
        if not chapter_dir.exists():
            continue
        for md_file in sorted(chapter_dir.glob("**/*.md")):
            text = md_file.read_text(encoding="utf-8")
            rel_path = md_file.relative_to(Path("chapters"))
            parts.append(f"=== {rel_path} ===\n{text}")
    return "\n\n".join(parts)


def check_consistency(
    chapter_ids: list[str] | None = None,
    provider: LLMProvider | None = None,
    output_dir: Path | None = None,
) -> ConsistencyReport:
    """Check for cross-chapter contradictions.

    Args:
        chapter_ids: Chapters to check. All if None.
        provider: LLM provider.
        output_dir: Output directory.

    Returns:
        ConsistencyReport.
    """
    if output_dir is None:
        output_dir = Path("tests/output")
    output_dir.mkdir(parents=True, exist_ok=True)

    if chapter_ids is None:
        chapters_dir = Path("chapters")
        chapter_ids = sorted([d.name for d in chapters_dir.iterdir() if d.is_dir()])

    chapters_content = _load_chapters_content(chapter_ids)

    if provider is None:
        from agents.config_schema import load_config

        config = load_config()
        provider = create_provider(config.agents["consistency_checker"])

    user_prompt = f"""\
Prüfe die folgenden Kapitel auf kapitelübergreifende Widersprüche:

{chapters_content}"""

    logger.info("Consistency Checker: checking %d chapters", len(chapter_ids))
    response = provider.complete(system=SYSTEM_PROMPT, user=user_prompt, temperature=0.2)

    # Parse response
    content = response.content.strip()
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()

    try:
        raw = json.loads(content)
    except json.JSONDecodeError:
        logger.error("Failed to parse consistency response: %s", content[:200])
        raw = {"summary": "Parse error", "contradictions": []}

    contradictions = [
        Contradiction(
            chapter_a=c.get("chapter_a", ""),
            location_a=c.get("location_a", ""),
            chapter_b=c.get("chapter_b", ""),
            location_b=c.get("location_b", ""),
            description=c.get("description", ""),
            severity=c.get("severity", "minor"),
            suggested_resolution=c.get("suggested_resolution", ""),
        )
        for c in raw.get("contradictions", [])
    ]

    report = ConsistencyReport(
        chapters_checked=chapter_ids,
        contradictions=contradictions,
        summary=raw.get("summary", ""),
    )

    out_file = output_dir / "consistency_report.json"
    out_file.write_text(
        json.dumps(asdict(report), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("Consistency: %d contradictions -> %s", len(contradictions), out_file)

    return report


def main() -> None:
    """CLI entry point."""
    from agents.logging_config import setup_logging

    setup_logging()
    report = check_consistency()
    print(f"\nConsistency: {len(report.contradictions)} contradictions")
    for c in report.contradictions:
        print(f"  - [{c.severity}] {c.chapter_a} vs {c.chapter_b}: {c.description}")


if __name__ == "__main__":
    main()
