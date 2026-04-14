"""Critic Agent: adversarial review of writer drafts."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path

from agents.llm.factory import create_provider
from agents.llm.provider import LLMProvider
from agents.parser import parse, validate_own_notes_unchanged

logger = logging.getLogger(__name__)


@dataclass
class CriticIssue:
    """A single issue found by the critic."""

    severity: str  # major, minor, nit
    category: str  # hallucination, bias, accuracy, style, completeness, zone_violation
    description: str
    suggested_fix: str
    location: str  # which zone or line


@dataclass
class CriticReview:
    """Complete critic review of a draft."""

    verdict: str  # approve, revise, reject
    issues: list[CriticIssue]
    own_notes_intact: bool
    word_count_change_pct: float
    summary: str


SYSTEM_PROMPT = """\
Du bist ein Critic-Agent für eine Wissensdatenbank über KI-Plattformen für kantonale Verwaltungen.

Deine Aufgabe: Prüfe einen Writer-Draft adversarial auf Fehler, Verzerrungen und Halluzinationen.

Prüfpunkte:
1. HALLUZINATIONEN: Behauptet der Draft etwas, das die Quelle nicht sagt? ("bis zu 40%" vs. "40%")
2. VERZERRUNGEN: Ist die Darstellung ausgewogen? Wird ein Anbieter bevorzugt?
3. GENAUIGKEIT: Stimmen Zahlen, Daten, Namen? Sind Quellen korrekt zitiert?
4. VOLLSTÄNDIGKEIT: Fehlt wichtiger Kontext? Wird die Relevanz für CH-Kantone klar?
5. STIL: Sachlich, präzise, für Verwaltungsentscheidungsträger verständlich?
6. ZONEN-INTEGRITÄT: Wurde die "Eigene Notizen"-Zone verändert? (Das ist ein hartes Fail!)

Verdict:
- "approve": Keine major Issues, direkt mergebar
- "revise": Major Issues vorhanden, Resolver muss nachbessern
- "reject": Grundlegende Probleme, Draft komplett verwerfen

Antwort als JSON:
{
  "verdict": "approve|revise|reject",
  "summary": "1-2 Sätze Gesamteinschätzung",
  "issues": [
    {
      "severity": "major|minor|nit",
      "category": "hallucination|bias|accuracy|style|completeness|zone_violation",
      "description": "Was ist das Problem?",
      "suggested_fix": "Konkreter Verbesserungsvorschlag",
      "location": "Überblick|Schlüsselquellen|Changelog"
    }
  ]
}
"""


def _build_user_prompt(original_text: str, draft_text: str, finding_json: str) -> str:
    """Build the user prompt for the critic."""
    return f"""\
## Original (vor dem Writer):
{original_text}

## Writer-Draft (zu prüfen):
{draft_text}

## Zugrundeliegender Fund:
{finding_json}

Prüfe den Draft kritisch. Vergleiche mit dem Original und der Quelle."""


def critique_draft(
    original_path: Path,
    draft_path: Path,
    finding_path: Path | None = None,
    finding_json: str = "{}",
    provider: LLMProvider | None = None,
    output_dir: Path | None = None,
) -> CriticReview:
    """Review a writer draft against the original and finding.

    Args:
        original_path: Path to the original markdown file.
        draft_path: Path to the writer draft.
        finding_path: Path to the finding JSON (optional).
        finding_json: Finding as JSON string (alternative).
        provider: LLM provider.
        output_dir: Output directory.

    Returns:
        CriticReview with verdict and issues.
    """
    if output_dir is None:
        output_dir = Path("tests/output")
    output_dir.mkdir(parents=True, exist_ok=True)

    original_text = original_path.read_text(encoding="utf-8")
    draft_text = draft_path.read_text(encoding="utf-8")

    if finding_path is not None:
        finding_json = finding_path.read_text(encoding="utf-8")

    # Pre-check: own notes integrity
    own_notes_intact = validate_own_notes_unchanged(original_text, draft_text)
    if not own_notes_intact:
        logger.error("CRITICAL: Eigene Notizen zone was modified!")

    # Word count check
    original_doc = parse(original_text)
    draft_doc = parse(draft_text)
    orig_words = len(original_doc.overview.split())
    draft_words = len(draft_doc.overview.split())
    word_pct = ((draft_words - orig_words) / max(orig_words, 1)) * 100

    # Create provider
    if provider is None:
        from agents.config_schema import load_config

        config = load_config()
        provider = create_provider(config.agents["critic"])

    # Call LLM
    user_prompt = _build_user_prompt(original_text, draft_text, finding_json)
    logger.info("Critic: reviewing draft")
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
        logger.error("Failed to parse critic response: %s", content[:200])
        raw = {"verdict": "revise", "summary": "Critic output parse error", "issues": []}

    # Build issues
    issues: list[CriticIssue] = []

    # Add zone violation if detected
    if not own_notes_intact:
        issues.insert(0, CriticIssue(
            severity="major",
            category="zone_violation",
            description="Die 'Eigene Notizen'-Zone wurde vom Writer verändert",
            suggested_fix="Eigene Notizen aus dem Original wiederherstellen",
            location="Eigene Notizen",
        ))

    for raw_issue in raw.get("issues", []):
        try:
            issues.append(CriticIssue(
                severity=raw_issue.get("severity", "minor"),
                category=raw_issue.get("category", "accuracy"),
                description=raw_issue["description"],
                suggested_fix=raw_issue.get("suggested_fix", ""),
                location=raw_issue.get("location", "Überblick"),
            ))
        except KeyError as e:
            logger.warning("Skipping malformed issue: %s", e)

    verdict = "reject" if not own_notes_intact else raw.get("verdict", "revise")

    review = CriticReview(
        verdict=verdict,
        issues=issues,
        own_notes_intact=own_notes_intact,
        word_count_change_pct=word_pct,
        summary=raw.get("summary", ""),
    )

    # Save output
    out_file = output_dir / "critic_review.json"
    out_file.write_text(
        json.dumps(asdict(review), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("Critic: verdict=%s, %d issues -> %s", review.verdict, len(issues), out_file)

    return review


def main() -> None:
    """CLI entry point."""
    from agents.logging_config import setup_logging

    setup_logging()
    review = critique_draft(
        original_path=Path("tests/fixtures/sample_chapter.md"),
        draft_path=Path("tests/output/writer_draft.md"),
        finding_path=Path("tests/output/researcher_findings.json"),
    )
    print(f"\nVerdict: {review.verdict}")
    print(f"Issues: {len(review.issues)}")
    for issue in review.issues:
        print(f"  - [{issue.severity}] {issue.category}: {issue.description}")


if __name__ == "__main__":
    main()
