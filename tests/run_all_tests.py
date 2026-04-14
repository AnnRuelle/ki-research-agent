"""Automated quality checks for all pipeline outputs."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from agents.parser import parse, validate_own_notes_unchanged

OUTPUT_DIR = Path("tests/output")
CHAPTERS_DIR = Path("chapters")


class CheckResult:
    """Result of a single check."""

    def __init__(self, name: str, passed: bool, message: str, hard: bool = True) -> None:
        self.name = name
        self.passed = passed
        self.message = message
        self.hard = hard  # hard = must pass, soft = warning


def run_checks() -> list[CheckResult]:
    """Run all automated checks. Returns list of results."""
    results: list[CheckResult] = []

    # === HARD CHECKS ===

    # Researcher output
    researcher_file = OUTPUT_DIR / "researcher_findings.json"
    if researcher_file.exists():
        try:
            findings = json.loads(researcher_file.read_text(encoding="utf-8"))
            valid = isinstance(findings, list) and all(
                "title" in f and "summary" in f and "confidence" in f
                for f in findings
            )
            results.append(CheckResult(
                "Researcher: valides JSON, Pflichtfelder",
                valid,
                f"{len(findings)} findings" if valid else "Missing required fields",
            ))
        except json.JSONDecodeError as e:
            results.append(CheckResult("Researcher: valides JSON", False, str(e)))
    else:
        results.append(CheckResult("Researcher: Output vorhanden", False, "File missing"))

    # Writer draft
    writer_file = OUTPUT_DIR / "writer_draft.md"
    if writer_file.exists():
        try:
            doc = parse(writer_file.read_text(encoding="utf-8"))
            results.append(CheckResult(
                "Writer: alle vier Zonen vorhanden",
                True,
                f"Title: {doc.title}",
            ))
        except Exception as e:
            results.append(CheckResult("Writer: vier Zonen", False, str(e)))

        # Own notes check (needs original)
        sample = Path("tests/fixtures/sample_chapter.md")
        if sample.exists():
            intact = validate_own_notes_unchanged(
                sample.read_text(encoding="utf-8"),
                writer_file.read_text(encoding="utf-8"),
            )
            results.append(CheckResult(
                "Writer: Eigene Notizen unverändert",
                intact,
                "INTACT" if intact else "VIOLATED",
            ))
    else:
        results.append(CheckResult("Writer: Output vorhanden", False, "File missing"))

    # Critic output
    critic_file = OUTPUT_DIR / "critic_review.json"
    if critic_file.exists():
        try:
            review = json.loads(critic_file.read_text(encoding="utf-8"))
            valid = "verdict" in review and "issues" in review
            results.append(CheckResult(
                "Critic: valides JSON mit verdict + issues",
                valid,
                f"Verdict: {review.get('verdict', '?')}",
            ))
        except json.JSONDecodeError as e:
            results.append(CheckResult("Critic: valides JSON", False, str(e)))
    else:
        results.append(CheckResult("Critic: Output vorhanden", False, "File missing"))

    # Resolver output
    resolver_file = OUTPUT_DIR / "resolver_final.md"
    if resolver_file.exists():
        content = resolver_file.read_text(encoding="utf-8")
        has_changelog = "## Changelog" in content
        results.append(CheckResult(
            "Resolver: Changelog-Eintrag vorhanden",
            has_changelog,
            "Changelog section found" if has_changelog else "Missing ## Changelog",
        ))
    else:
        results.append(CheckResult("Resolver: Output vorhanden", False, "File missing"))

    # Newsletter
    newsletter_file = OUTPUT_DIR / "newsletter_preview.html"
    if newsletter_file.exists():
        html = newsletter_file.read_text(encoding="utf-8")
        valid_html = "<html" in html and "</html>" in html
        results.append(CheckResult(
            "Newsletter: valides HTML",
            valid_html,
            f"{len(html)} chars",
        ))
    else:
        results.append(CheckResult("Newsletter: Output vorhanden", False, "File missing"))

    # Dashboard
    dashboard = Path("index.md")
    if dashboard.exists():
        content = dashboard.read_text(encoding="utf-8")
        all_chapters = all(f"{i:02d}" in content for i in range(1, 14))
        results.append(CheckResult(
            "Dashboard: alle 13 Kapitel gelistet",
            all_chapters,
            "All chapters present" if all_chapters else "Missing chapters",
        ))

    # Config
    try:
        from agents.config_schema import load_config, load_sources
        load_config()
        load_sources()
        results.append(CheckResult("Config: yaml fehlerfrei", True, "OK"))
    except Exception as e:
        results.append(CheckResult("Config: yaml fehlerfrei", False, str(e)))

    # === SOFT CHECKS (warnings) ===

    if writer_file.exists() and Path("tests/fixtures/sample_chapter.md").exists():
        try:
            original_doc = parse(Path("tests/fixtures/sample_chapter.md").read_text(encoding="utf-8"))
            draft_doc = parse(writer_file.read_text(encoding="utf-8"))
            orig_words = len(original_doc.overview.split())
            draft_words = len(draft_doc.overview.split())
            if orig_words > 0:
                pct = ((draft_words - orig_words) / orig_words) * 100
                results.append(CheckResult(
                    f"Writer: Längenänderung {pct:+.0f}%",
                    abs(pct) <= 20,
                    f"{orig_words} -> {draft_words} words",
                    hard=False,
                ))
        except Exception:
            pass

    if researcher_file.exists():
        try:
            findings = json.loads(researcher_file.read_text(encoding="utf-8"))
            results.append(CheckResult(
                "Researcher: mindestens 1 Fund",
                len(findings) >= 1,
                f"{len(findings)} findings",
                hard=False,
            ))
        except Exception:
            pass

    return results


def main() -> None:
    """Run all checks and print report."""
    results = run_checks()

    print(f"\n{'='*60}")
    print("AUTOMATED QUALITY CHECKS")
    print(f"{'='*60}\n")

    hard_pass = 0
    hard_fail = 0
    soft_warn = 0

    for r in results:
        if r.hard:
            icon = "PASS" if r.passed else "FAIL"
            if r.passed:
                hard_pass += 1
            else:
                hard_fail += 1
        else:
            icon = "OK  " if r.passed else "WARN"
            if not r.passed:
                soft_warn += 1

        print(f"  [{icon}] {r.name}")
        if not r.passed:
            print(f"         {r.message}")

    print(f"\n{'='*60}")
    print(f"  Hard: {hard_pass} passed, {hard_fail} failed")
    print(f"  Soft: {soft_warn} warnings")
    print(f"{'='*60}")

    if hard_fail > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
