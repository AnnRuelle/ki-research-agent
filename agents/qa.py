"""Q&A Agent: answers questions based on KB content (on-demand, no scheduled pipeline)."""

from __future__ import annotations

import logging
import re
from pathlib import Path

import yaml

from agents.llm.factory import create_provider
from agents.llm.provider import LLMProvider

logger = logging.getLogger(__name__)

CHAPTERS_DIR = Path("chapters")

MAX_CHARS_PER_CHAPTER = 20_000

STOPWORDS = frozenset(
    {
        "und",
        "oder",
        "aber",
        "ist",
        "sind",
        "war",
        "waren",
        "wird",
        "werden",
        "was",
        "wie",
        "wer",
        "wo",
        "wann",
        "warum",
        "welche",
        "welcher",
        "welches",
        "die",
        "der",
        "das",
        "den",
        "dem",
        "des",
        "ein",
        "eine",
        "einen",
        "einem",
        "einer",
        "eines",
        "von",
        "vom",
        "mit",
        "fuer",
        "für",
        "auf",
        "aus",
        "bei",
        "nach",
        "ueber",
        "über",
        "unter",
        "vor",
        "hinter",
        "zwischen",
        "zu",
        "zum",
        "zur",
        "am",
        "im",
        "ins",
        "ans",
        "kann",
        "koennen",
        "können",
        "soll",
        "sollen",
        "muss",
        "muessen",
        "müssen",
        "hat",
        "haben",
        "hatte",
        "hatten",
        "nicht",
        "kein",
        "keine",
        "mehr",
        "noch",
        "auch",
        "nur",
        "schon",
        "sehr",
        "viel",
        "viele",
        "alle",
        "gibt",
        "gib",
        "the",
        "and",
        "but",
        "for",
        "with",
        "from",
    }
)

TOKEN_RE = re.compile(r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ0-9]{2,}")


def _extract_keywords(text: str) -> set[str]:
    """Extract lowercase keyword tokens from text, dropping stopwords."""
    tokens = TOKEN_RE.findall(text.lower())
    return {t for t in tokens if t not in STOPWORDS}


def _score_file(path: Path, keywords: set[str]) -> int:
    """Score a subpage by keyword hits in filename + first 500 chars."""
    if not keywords:
        return 0
    haystack = path.stem.lower().replace("-", " ").replace("_", " ")
    try:
        haystack += " " + path.read_text(encoding="utf-8")[:500].lower()
    except OSError:
        return 0
    return sum(1 for kw in keywords if kw in haystack)


SYSTEM_PROMPT = """\
Du bist ein Q&A-Agent fuer eine Wissensdatenbank ueber KI-Plattformen fuer kantonale Verwaltungen in der Schweiz.

Deine Aufgabe: Beantworte Fragen AUSSCHLIESSLICH basierend auf den bereitgestellten KB-Inhalten.

Regeln:
- Antworte nur mit Wissen aus der KB — erfinde keine externen Fakten
- Jede Aussage muss mit einem Link zur Quell-Unterseite belegt werden
- Wenn die KB keine Antwort hat: sage das explizit und nenne relevante Kapitel
- Nutze strukturierte Daten (.data.yaml) fuer Vergleiche und Tabellen
- Antwortsprache: Deutsch (Fachbegriffe auf Englisch okay)
- Antwortlaenge: maximal 1000 Woerter

Antwort-Format:
## Antwort

[Deine Antwort mit Quellenlinks im Format -> [chapters/XX/datei.md](chapters/XX/datei.md)]

## Verwendete Quellen
- chapters/XX/datei.md (Letzte Aenderung: YYYY-MM-DD)
- ...
"""


def _select_relevant_chapters(question: str, max_chapters: int = 5) -> list[str]:
    """Select chapters most likely relevant to the question.

    Simple keyword-based selection. In production, this could use embeddings.
    """
    chapter_keywords: dict[str, list[str]] = {
        "01-plattform-architektur": [
            "architektur",
            "gateway",
            "cloud",
            "hybrid",
            "plattform",
            "modell",
            "infrastruktur",
        ],
        "02-use-cases": ["use case", "anwendung", "pilot", "katalog", "prioris"],
        "03-datenschutz-informationssicherheit": ["datenschutz", "sicherheit", "ndsg", "isds", "klassifikation"],
        "04-governance-betriebsmodell": ["governance", "betrieb", "rolle", "freigabe", "organisation"],
        "05-regulatorik": ["regulat", "ai act", "recht", "gesetz", "haftung", "transparenz", "compliance"],
        "06-change-management": ["change", "schulung", "kommunikation", "stakeholder", "training", "prompt"],
        "07-markt-anbieter": ["anbieter", "azure", "aws", "google", "swiss", "markt", "vergleich", "bewertung"],
        "08-integration-it-landschaft": ["integration", "schnittstelle", "iam", "sso", "dms", "fachanwendung"],
        "09-kosten-lizenzmodelle": ["kosten", "kostet", "lizenz", "tco", "preis", "budget", "teuer", "guenstig"],
        "10-referenzprojekte-kantone": ["kanton", "referenz", "zuerich", "bern", "aargau", "projekt", "erfahrung"],
        "11-erfolgsmessung": ["erfolg", "kpi", "messung", "pilot", "auswertung"],
        "12-beschaffung": ["beschaffung", "ivoeb", "ausschreibung", "kriterien", "pflichtenheft"],
        "13-sustainable-it-ki": ["nachhaltig", "sustainable", "energie", "co2", "green"],
    }

    question_lower = question.lower()
    scores: list[tuple[str, int]] = []

    for chapter_id, keywords in chapter_keywords.items():
        score = sum(1 for kw in keywords if kw in question_lower)
        if score > 0:
            scores.append((chapter_id, score))

    scores.sort(key=lambda x: x[1], reverse=True)

    # Always include at least the top matches, or all if few matches
    selected = [chapter_id for chapter_id, _ in scores[:max_chapters]]

    # If no keyword matches, include the most general chapters
    if not selected:
        selected = ["01-plattform-architektur", "07-markt-anbieter", "02-use-cases"]

    return selected


def _load_chapter_content(
    chapter_id: str,
    keywords: set[str] | None = None,
    max_chars: int = MAX_CHARS_PER_CHAPTER,
) -> str:
    """Load scoped chapter content.

    Always includes index.md and all .data.yaml files (structured, compact).
    Other subpages are ranked by keyword hit count and included until max_chars
    is reached. With no keywords, all subpages are included up to the cap.
    """
    chapter_dir = CHAPTERS_DIR / chapter_id
    if not chapter_dir.exists():
        return ""

    parts: list[str] = []
    char_budget = max_chars

    def _append(path: Path, text: str, tag: str = "") -> None:
        nonlocal char_budget
        rel_path = path.relative_to(CHAPTERS_DIR)
        header = f"=== {rel_path}{tag} ===\n"
        block = header + text
        parts.append(block)
        char_budget -= len(block)

    index_md = chapter_dir / "index.md"
    if index_md.exists():
        _append(index_md, index_md.read_text(encoding="utf-8"))

    for yaml_file in sorted(chapter_dir.glob("**/*.data.yaml")):
        try:
            data = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
        except yaml.YAMLError:
            continue
        _append(yaml_file, yaml.dump(data, allow_unicode=True), tag=" (strukturierte Daten)")

    subpages = [p for p in chapter_dir.glob("**/*.md") if p.name != "index.md"]
    if keywords:
        scored = [(_score_file(p, keywords), p) for p in subpages]
        scored.sort(key=lambda sp: (-sp[0], sp[1].name))
        ordered = [p for score, p in scored if score > 0]
        ordered += [p for score, p in scored if score == 0]
    else:
        ordered = sorted(subpages, key=lambda p: p.name)

    included = 0
    for md_file in ordered:
        if char_budget <= 0:
            break
        text = md_file.read_text(encoding="utf-8")
        if len(text) > char_budget:
            text = text[:char_budget] + "\n[...truncated...]"
        _append(md_file, text)
        included += 1

    logger.info(
        "qa: chapter %s loaded — index + %d .data.yaml + %d/%d subpages",
        chapter_id,
        sum(1 for p in parts if ".data.yaml" in p.split("\n", 1)[0]),
        included,
        len(subpages),
    )
    return "\n\n".join(parts)


def ask(
    question: str,
    provider: LLMProvider | None = None,
    max_chapters: int = 5,
    output_dir: Path | None = None,
) -> str:
    """Ask a question against the KB.

    Args:
        question: The question to answer.
        provider: LLM provider (created from config if None).
        max_chapters: Maximum chapters to include as context.
        output_dir: Where to save the answer.

    Returns:
        Answer as Markdown string.
    """
    if output_dir is None:
        output_dir = Path("tests/output")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Select relevant chapters
    selected = _select_relevant_chapters(question, max_chapters)
    logger.info("Q&A: selected chapters %s for question: %s", selected, question[:80])

    # Load scoped content (keyword-filtered, per-chapter char cap)
    keywords = _extract_keywords(question)
    context_parts: list[str] = []
    for chapter_id in selected:
        content = _load_chapter_content(chapter_id, keywords=keywords)
        if content:
            context_parts.append(content)

    context = "\n\n---\n\n".join(context_parts)

    # Create provider
    if provider is None:
        from agents.config_schema import load_config

        config = load_config()
        qa_config = config.agents.get("qa", config.agents["researcher"])
        provider = create_provider(qa_config, agent_name="qa")

    # Build prompt
    user_prompt = f"""\
## Frage:
{question}

## KB-Inhalte (relevante Kapitel):
{context}

Beantworte die Frage basierend auf diesen KB-Inhalten."""

    response = provider.complete(system=SYSTEM_PROMPT, user=user_prompt, temperature=0.2)

    # Save output
    answer_file = output_dir / "qa_answer.md"
    answer_content = f"# Q&A\n\n**Frage:** {question}\n\n{response.content}\n"
    answer_file.write_text(answer_content, encoding="utf-8")
    logger.info("Q&A answer saved: %s", answer_file)

    return response.content


def main() -> None:
    """CLI entry point."""
    import sys

    from agents.logging_config import setup_logging

    setup_logging()

    if len(sys.argv) < 2:
        print('Usage: python -m agents.qa "Deine Frage"')
        sys.exit(1)

    question = " ".join(sys.argv[1:])
    answer = ask(question)
    print(f"\n{'=' * 60}")
    print(answer)
    print(f"{'=' * 60}")
    print("\nGespeichert: tests/output/qa_answer.md")


if __name__ == "__main__":
    main()
