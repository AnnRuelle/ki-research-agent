"""Newsletter Agent: generates weekly update email from pipeline results."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path("templates")
UPDATES_DIR = Path("updates")


@dataclass
class NewsletterData:
    """Data for newsletter rendering."""

    week: int
    year: int
    added: list[dict[str, str]]
    flagged: list[dict[str, str]]
    new_pages: list[dict[str, str]]
    obsolete: list[dict[str, str]]
    contradictions: list[dict[str, str]]
    batch_actions: bool
    batch_approve_text_url: str
    batch_approve_sources_url: str
    stats: dict[str, str | int]


def _load_update_files(updates_dir: Path) -> dict[str, list[dict[str, object]]]:
    """Load merged, flagged, and rejected JSON files from the latest update directory."""
    result: dict[str, list[dict[str, object]]] = {
        "merged": [],
        "flagged": [],
        "rejected": [],
    }

    if not updates_dir.exists():
        return result

    # Find latest week directory
    week_dirs = sorted(updates_dir.iterdir(), reverse=True)
    if not week_dirs:
        return result

    latest = week_dirs[0]
    for key in result:
        f = latest / f"{key}.json"
        if f.exists():
            try:
                result[key] = json.loads(f.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pass

    return result


def _build_approve_url(repo: str, item_id: str, action: str) -> str:
    """Build a GitHub Actions workflow_dispatch URL for approve/reject."""
    return (
        f"https://github.com/{repo}/actions/workflows/approve-reject.yaml"
        f"?inputs[item_id]={item_id}&inputs[action]={action}"
    )


def generate_newsletter(
    repo: str = "AnnRuelle/ki-research-agent",
    updates_dir: Path | None = None,
    output_dir: Path | None = None,
    cost_azure: float = 0.0,
    cost_claude: float = 0.0,
) -> str:
    """Generate newsletter HTML from pipeline results.

    Args:
        repo: GitHub repository (owner/name).
        updates_dir: Directory with update JSON files.
        output_dir: Where to save the preview HTML.
        cost_azure: Azure costs for this run.
        cost_claude: Claude costs for this run.

    Returns:
        Rendered HTML string.
    """
    if updates_dir is None:
        updates_dir = UPDATES_DIR
    if output_dir is None:
        output_dir = Path("tests/output")
    output_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now(tz=timezone.utc)
    updates = _load_update_files(updates_dir)

    # Categorize items
    added: list[dict[str, str]] = []
    flagged: list[dict[str, str]] = []
    new_pages: list[dict[str, str]] = []
    obsolete: list[dict[str, str]] = []
    contradictions: list[dict[str, str]] = []

    for item in updates.get("merged", []):
        added.append({
            "chapter": str(item.get("chapter", "")),
            "subpage": str(item.get("subpage", "")),
            "title": str(item.get("title", "")),
            "source": str(item.get("source_name", "")),
            "critic_verdict": str(item.get("critic_verdict", "approve")),
        })

    for item in updates.get("flagged", []):
        operation = str(item.get("operation", ""))

        if operation == "new_page":
            new_pages.append({
                "chapter": str(item.get("chapter", "")),
                "filename": str(item.get("subpage", "")),
                "reason": str(item.get("reason", "")),
                "approve_url": _build_approve_url(repo, str(item.get("id", "")), "approve"),
                "reject_url": _build_approve_url(repo, str(item.get("id", "")), "reject"),
            })
        elif operation == "obsolescence":
            obsolete.append({
                "chapter": str(item.get("chapter", "")),
                "subpage": str(item.get("subpage", "")),
                "description": str(item.get("description", "")),
                "approve_url": _build_approve_url(repo, str(item.get("id", "")), "approve"),
                "reject_url": _build_approve_url(repo, str(item.get("id", "")), "reject"),
            })
        elif operation == "contradiction":
            contradictions.append({
                "chapter_a": str(item.get("chapter_a", "")),
                "chapter_b": str(item.get("chapter_b", "")),
                "description": str(item.get("description", "")),
                "fix_a_url": _build_approve_url(repo, str(item.get("id", "")), "fix_a"),
                "fix_b_url": _build_approve_url(repo, str(item.get("id", "")), "fix_b"),
                "review_url": _build_approve_url(repo, str(item.get("id", "")), "review"),
            })
        else:
            flagged.append({
                "chapter": str(item.get("chapter", "")),
                "subpage": str(item.get("subpage", "")),
                "title": str(item.get("title", "")),
                "flag_reason": str(item.get("flag_reason", "")),
                "approve_url": _build_approve_url(repo, str(item.get("id", "")), "approve"),
                "reject_url": _build_approve_url(repo, str(item.get("id", "")), "reject"),
            })

    batch_threshold = 10
    batch_actions = (len(flagged) + len(new_pages) + len(obsolete)) > batch_threshold

    stats = {
        "scanned": len(updates.get("merged", [])) + len(updates.get("flagged", [])) + len(updates.get("rejected", [])),
        "auto_merged": len(updates.get("merged", [])),
        "flagged": len(updates.get("flagged", [])),
        "rejected": len(updates.get("rejected", [])),
        "cost_azure": f"{cost_azure:.2f}",
        "cost_claude": f"{cost_claude:.2f}",
    }

    # Render template
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=True,
    )
    template = env.get_template("newsletter.html")

    html = template.render(
        week=now.isocalendar()[1],
        year=now.year,
        added=added if added else None,
        flagged=flagged if flagged else None,
        new_pages=new_pages if new_pages else None,
        obsolete=obsolete if obsolete else None,
        contradictions=contradictions if contradictions else None,
        batch_actions=batch_actions,
        batch_approve_text_url=_build_approve_url(repo, "batch_text", "approve"),
        batch_approve_sources_url=_build_approve_url(repo, "batch_sources", "approve"),
        stats=stats,
    )

    # Save preview
    preview_file = output_dir / "newsletter_preview.html"
    preview_file.write_text(html, encoding="utf-8")
    logger.info("Newsletter preview: %s", preview_file)

    return html


def main() -> None:
    """CLI entry point."""
    from agents.logging_config import setup_logging

    setup_logging()
    html = generate_newsletter()
    print(f"Newsletter preview: tests/output/newsletter_preview.html")
    print(f"HTML length: {len(html)} chars")


if __name__ == "__main__":
    main()
