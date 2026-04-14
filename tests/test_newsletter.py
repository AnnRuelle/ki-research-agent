"""Unit tests for newsletter generation."""

from __future__ import annotations

import pytest

from agents.newsletter import generate_newsletter, _build_approve_url


@pytest.mark.unit
class TestNewsletter:
    """Tests for newsletter generation."""

    def test_generate_empty_newsletter(self) -> None:
        """Newsletter with no updates should still render valid HTML."""
        html = generate_newsletter()
        assert "<html" in html
        assert "</html>" in html
        assert "KI-KB Update" in html
        assert "Stats" in html

    def test_generate_newsletter_contains_stats(self) -> None:
        """Stats section should always be present."""
        html = generate_newsletter()
        assert "Gescannt:" in html
        assert "Auto-merged:" in html

    def test_approve_url_format(self) -> None:
        """Approve URL should contain repo, item_id, and action."""
        url = _build_approve_url("owner/repo", "item-123", "approve")
        assert "owner/repo" in url
        assert "item-123" in url
        assert "approve" in url

    def test_newsletter_html_file_created(self) -> None:
        """Preview file should be created."""
        from pathlib import Path
        output_dir = Path("tests/output")
        generate_newsletter(output_dir=output_dir)
        assert (output_dir / "newsletter_preview.html").exists()
