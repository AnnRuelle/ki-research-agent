"""Researcher Agent: finds new information relevant to KB chapters."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from agents.config_schema import load_config
from agents.llm.factory import create_provider
from agents.llm.provider import LLMProvider, LLMResponse
from agents.web_search import search_for_chapter

logger = logging.getLogger(__name__)

SOURCES_DIR = Path("sources")


@dataclass
class Finding:
    """A single research finding."""

    finding_id: str
    chapter: str
    subpage: str
    title: str
    summary: str
    source_name: str
    source_url: str
    source_date: str
    source_type: str
    confidence: float
    credibility: str
    geographic_origin: str
    operation: str
    tags: list[str]


SYSTEM_PROMPT = """\
Du bist ein Research-Agent für eine Wissensdatenbank über KI-Plattformen für kantonale Verwaltungen in der Schweiz.

Deine Aufgabe: Finde neue, relevante Informationen zu einem bestimmten Kapitel \
basierend auf den bereitgestellten Quellen.

Regeln:
- Fokus auf Schweiz (CH), DACH-Raum und global relevante Entwicklungen
- Bewerte die Glaubwürdigkeit jeder Quelle (high/medium/low)
- Bewerte dein Confidence-Level (0.0-1.0) für jeden Fund
- Markiere den geographischen Ursprung (ch/dach/global/cn)
- Klassifiziere die Operation: update_text, add_source, obsolescence, new_page
- Gib die Antwort als JSON-Array zurück

Antwort-Format (JSON-Array):
[
  {
    "title": "Kurztitel des Funds",
    "summary": "2-3 Sätze Zusammenfassung mit Relevanz für kantonale Verwaltung",
    "source_name": "Name der Quelle",
    "source_url": "URL",
    "source_date": "YYYY-MM-DD",
    "source_type": "government|vendor|media|academic|newsletter",
    "confidence": 0.85,
    "credibility": "high|medium|low",
    "geographic_origin": "ch|dach|global|cn",
    "operation": "update_text|add_source|obsolescence|new_page",
    "tags": ["tag1", "tag2"],
    "suggested_subpage": "dateiname.md"
  }
]

Wenn du nichts Relevantes findest, gib ein leeres Array zurück: []
"""


def _build_user_prompt(chapter_id: str, chapter_content: str, ingested_sources: str, web_results: str) -> str:
    """Build the user prompt for the researcher."""
    return f"""\
## Kapitel: {chapter_id}

### Aktueller Kapitel-Inhalt:
{chapter_content}

### Neue Quellen seit letztem Scan:
{ingested_sources}

### Web-Search-Ergebnisse:
{web_results}

Finde neue, relevante Informationen für dieses Kapitel. Prüfe die Quellen auf Relevanz, \
Glaubwürdigkeit und Neuheit. Ignoriere Informationen die bereits im Kapitel enthalten sind. \
Nutze sowohl die Ingest-Quellen als auch die Web-Search-Ergebnisse."""


def _load_chapter_content(chapter_id: str) -> str:
    """Load all markdown content from a chapter directory."""
    chapter_dir = Path("chapters") / chapter_id
    if not chapter_dir.exists():
        return "(Kapitel-Verzeichnis nicht gefunden)"

    content_parts: list[str] = []
    for md_file in sorted(chapter_dir.glob("**/*.md")):
        text = md_file.read_text(encoding="utf-8")
        content_parts.append(f"### {md_file.name}\n{text}")

    return "\n\n---\n\n".join(content_parts) if content_parts else "(Keine Inhalte)"


def _load_ingested_sources() -> str:
    """Load recently ingested sources as context."""
    parts: list[str] = []

    # RSS items
    newsletter_dir = SOURCES_DIR / "newsletters"
    if newsletter_dir.exists():
        for f in sorted(newsletter_dir.glob("*.json"), reverse=True)[:3]:
            try:
                items = json.loads(f.read_text(encoding="utf-8"))
                for item in items[:10]:
                    parts.append(f"- [{item.get('source_name', '?')}] {item.get('title', '?')} ({item.get('url', '')})")
            except (json.JSONDecodeError, KeyError):
                continue

    # Web changes
    archive_dir = SOURCES_DIR / "web-archives"
    if archive_dir.exists():
        for f in sorted(archive_dir.glob("changes-*.json"), reverse=True)[:3]:
            try:
                changes = json.loads(f.read_text(encoding="utf-8"))
                for change in changes:
                    parts.append(f"- [WEB] {change.get('source_name', '?')}: {change.get('snippet', '')[:200]}")
            except (json.JSONDecodeError, KeyError):
                continue

    return "\n".join(parts) if parts else "(Keine neuen Quellen)"


def _parse_findings(response: LLMResponse, chapter_id: str) -> list[Finding]:
    """Parse LLM response into Finding objects."""
    content = response.content.strip()

    # Extract JSON from markdown code blocks if present
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()

    try:
        raw_findings = json.loads(content)
    except json.JSONDecodeError:
        logger.error("Failed to parse LLM response as JSON: %s", content[:200])
        return []

    if not isinstance(raw_findings, list):
        raw_findings = [raw_findings]

    findings: list[Finding] = []
    date_str = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")

    for i, raw in enumerate(raw_findings):
        try:
            finding = Finding(
                finding_id=f"{date_str}-{chapter_id[:4]}-{i + 1:03d}",
                chapter=chapter_id,
                subpage=raw.get("suggested_subpage", "index.md"),
                title=raw["title"],
                summary=raw["summary"],
                source_name=raw["source_name"],
                source_url=raw.get("source_url", ""),
                source_date=raw.get("source_date", date_str),
                source_type=raw.get("source_type", "unknown"),
                confidence=float(raw.get("confidence", 0.5)),
                credibility=raw.get("credibility", "medium"),
                geographic_origin=raw.get("geographic_origin", "global"),
                operation=raw.get("operation", "update_text"),
                tags=raw.get("tags", []),
            )
            findings.append(finding)
        except (KeyError, ValueError) as e:
            logger.warning("Skipping malformed finding %d: %s", i, e)

    return findings


def research_chapter(
    chapter_id: str,
    provider: LLMProvider | None = None,
    output_dir: Path | None = None,
) -> list[Finding]:
    """Research a single chapter. Returns list of findings."""
    if output_dir is None:
        output_dir = Path("tests/output")
    output_dir.mkdir(parents=True, exist_ok=True)

    if provider is None:
        config = load_config()
        provider = create_provider(config.agents["researcher"])

    chapter_content = _load_chapter_content(chapter_id)
    ingested_sources = _load_ingested_sources()

    # Web search for fresh results
    chapter_title = chapter_id.split("-", 1)[1].replace("-", " ").title() if "-" in chapter_id else chapter_id
    web_search_results = search_for_chapter(chapter_id, chapter_title)
    web_results_text = (
        "\n".join(f"- [{r.title}]({r.url}) (score: {r.score:.2f})\n  {r.content[:300]}" for r in web_search_results)
        if web_search_results
        else "(Keine Web-Search-Ergebnisse — TAVILY_API_KEY nicht gesetzt?)"
    )

    user_prompt = _build_user_prompt(chapter_id, chapter_content, ingested_sources, web_results_text)

    logger.info("Researching chapter: %s", chapter_id)
    response = provider.complete(system=SYSTEM_PROMPT, user=user_prompt, temperature=0.3)

    findings = _parse_findings(response, chapter_id)

    # Save output
    out_file = output_dir / "researcher_findings.json"
    out_file.write_text(
        json.dumps([asdict(f) for f in findings], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("Researcher: %d findings for %s -> %s", len(findings), chapter_id, out_file)

    return findings


def main() -> None:
    """CLI entry point."""
    import sys

    from agents.logging_config import setup_logging

    setup_logging()
    chapter = sys.argv[1] if len(sys.argv) > 1 else "01-plattform-architektur"
    findings = research_chapter(chapter)

    print(f"\n{'=' * 60}")
    print(f"Researcher: {len(findings)} Funde fuer {chapter}")
    for f in findings:
        print(f"  - [{f.confidence:.2f}] {f.title} ({f.credibility}, {f.geographic_origin})")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
