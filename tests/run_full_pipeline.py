"""Full pipeline runner: executes all agents in sequence for a chapter."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from agents.logging_config import setup_logging

OUTPUT_DIR = Path("tests/output")


def run_pipeline(chapter_id: str) -> None:
    """Run the complete agent pipeline for a single chapter."""
    setup_logging(level="INFO")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"{'='*60}")
    print(f"Full Pipeline: {chapter_id}")
    print(f"{'='*60}")

    # Step 1: Researcher
    print("\n[1/6] Researcher...")
    from agents.researcher import research_chapter

    findings = research_chapter(chapter_id, output_dir=OUTPUT_DIR)
    print(f"  -> {len(findings)} findings")

    if not findings:
        print("  No findings, pipeline stops here.")
        return

    # Step 2: Writer (process first finding)
    print("\n[2/6] Writer...")
    from agents.writer import write_draft

    first_finding = findings[0]
    draft = write_draft(
        chapter_id=chapter_id,
        subpage=first_finding.subpage,
        finding_data={
            "title": first_finding.title,
            "summary": first_finding.summary,
            "source_name": first_finding.source_name,
            "source_url": first_finding.source_url,
            "source_date": first_finding.source_date,
        },
        output_dir=OUTPUT_DIR,
    )
    orig_words = len(draft.overview.split())
    print(f"  -> Draft: {orig_words} words")

    # Step 3: Critic
    print("\n[3/6] Critic...")
    from agents.critic import critique_draft

    original_path = Path("chapters") / chapter_id / first_finding.subpage
    review = critique_draft(
        original_path=original_path,
        draft_path=OUTPUT_DIR / "writer_draft.md",
        finding_path=OUTPUT_DIR / "researcher_findings.json",
        output_dir=OUTPUT_DIR,
    )
    print(f"  -> Verdict: {review.verdict}, {len(review.issues)} issues")

    # Step 4: Resolver
    print("\n[4/6] Resolver...")
    from agents.resolver import resolve_draft

    final = resolve_draft(
        draft_path=OUTPUT_DIR / "writer_draft.md",
        critic_path=OUTPUT_DIR / "critic_review.json",
        original_path=original_path,
        output_dir=OUTPUT_DIR,
    )
    print(f"  -> Final: {len(final.overview.split())} words")

    # Step 5: Merger (update dashboard + indexes)
    print("\n[5/6] Merger...")
    from agents.merger import update_chapter_index, update_dashboard

    update_chapter_index(chapter_id)
    update_dashboard()
    print("  -> Dashboard + indexes updated")

    # Step 6: Newsletter preview
    print("\n[6/6] Newsletter...")
    from agents.newsletter import generate_newsletter

    html = generate_newsletter(output_dir=OUTPUT_DIR)
    print(f"  -> Newsletter: {len(html)} chars")

    # Summary
    print(f"\n{'='*60}")
    print("PIPELINE COMPLETE")
    print(f"  Findings:      {len(findings)}")
    print(f"  Critic:        {review.verdict} ({len(review.issues)} issues)")
    print(f"  Own Notes:     {'INTACT' if review.own_notes_intact else 'VIOLATED!'}")
    print(f"  Word Change:   {review.word_count_change_pct:+.0f}%")
    print(f"{'='*60}")
    print(f"\nOutputs in {OUTPUT_DIR}/:")
    for f in sorted(OUTPUT_DIR.glob("*")):
        print(f"  - {f.name}")
    print("\n>> Bitte Outputs reviewen.")


def main() -> None:
    """CLI entry point."""
    chapter = sys.argv[1] if len(sys.argv) > 1 else "01-plattform-architektur"
    run_pipeline(chapter)


if __name__ == "__main__":
    main()
