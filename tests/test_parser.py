"""Unit tests for the Vier-Zonen-Parser."""

from pathlib import Path

import pytest

from agents.parser import FourZoneDocument, ParserError, parse, validate_own_notes_unchanged

FIXTURES = Path(__file__).parent / "fixtures"


class TestParse:
    """Tests for parse()."""

    def test_parse_sample_chapter(self) -> None:
        """Parse the sample fixture and verify all zones are extracted."""
        content = (FIXTURES / "sample_chapter.md").read_text(encoding="utf-8")
        doc = parse(content)

        assert doc.title == "AI Gateway"
        assert "zentrale Schnittstelle" in doc.overview
        assert "IT-Leiter GR" in doc.own_notes
        assert "Azure AI Gateway Architecture" in doc.key_sources
        assert "2026-04-07" in doc.changelog

    def test_parse_minimal_document(self) -> None:
        """Parse a minimal valid Vier-Zonen document."""
        md = (
            "# Test\n\n"
            "## Überblick\n\nSome overview.\n\n"
            "## Eigene Notizen\n\n\n"
            "## Schlüsselquellen\n\nNo sources.\n\n"
            "## Changelog\n\nNo entries.\n"
        )
        doc = parse(md)
        assert doc.title == "Test"
        assert doc.overview == "Some overview."
        assert doc.own_notes == ""
        assert doc.key_sources == "No sources."
        assert doc.changelog == "No entries."

    def test_parse_missing_title_raises(self) -> None:
        """Document without h1 title should raise ParserError."""
        md = "## Überblick\n\nText\n## Eigene Notizen\n\n## Schlüsselquellen\n\n## Changelog\n"
        with pytest.raises(ParserError, match="No h1 title"):
            parse(md)

    def test_parse_missing_zone_raises(self) -> None:
        """Document missing a zone header should raise ParserError."""
        md = "# Test\n\n## Überblick\n\nText\n## Eigene Notizen\n\n## Changelog\n"
        with pytest.raises(ParserError, match="Schlüsselquellen"):
            parse(md)

    def test_parse_empty_zones(self) -> None:
        """All zones can be empty."""
        md = "# Empty\n\n## Überblick\n\n## Eigene Notizen\n\n## Schlüsselquellen\n\n## Changelog\n"
        doc = parse(md)
        assert doc.title == "Empty"
        assert doc.overview == ""
        assert doc.own_notes == ""
        assert doc.key_sources == ""
        assert doc.changelog == ""


class TestToMarkdown:
    """Tests for FourZoneDocument.to_markdown()."""

    def test_roundtrip(self) -> None:
        """Parse then reassemble should produce parseable output with same data."""
        content = (FIXTURES / "sample_chapter.md").read_text(encoding="utf-8")
        doc = parse(content)
        reassembled = doc.to_markdown()
        doc2 = parse(reassembled)

        assert doc.title == doc2.title
        assert doc.overview == doc2.overview
        assert doc.own_notes == doc2.own_notes
        assert doc.key_sources == doc2.key_sources
        assert doc.changelog == doc2.changelog

    def test_to_markdown_contains_all_headers(self) -> None:
        """Reassembled Markdown must contain all four zone headers."""
        doc = FourZoneDocument(
            title="Test",
            overview="Overview text",
            own_notes="My notes",
            key_sources="Sources",
            changelog="Log",
        )
        md = doc.to_markdown()
        assert "# Test" in md
        assert "## Überblick" in md
        assert "## Eigene Notizen" in md
        assert "## Schlüsselquellen" in md
        assert "## Changelog" in md


class TestValidateOwnNotes:
    """Tests for validate_own_notes_unchanged()."""

    def test_unchanged_notes_returns_true(self) -> None:
        """Identical own_notes zone should return True."""
        original = (
            "# Test\n\n## Überblick\n\nOld text.\n\n"
            "## Eigene Notizen\n\nMy important notes.\n\n"
            "## Schlüsselquellen\n\nOld sources.\n\n"
            "## Changelog\n\nOld log.\n"
        )
        modified = (
            "# Test\n\n## Überblick\n\nNew text!\n\n"
            "## Eigene Notizen\n\nMy important notes.\n\n"
            "## Schlüsselquellen\n\nNew sources.\n\n"
            "## Changelog\n\nNew log.\n"
        )
        assert validate_own_notes_unchanged(original, modified) is True

    def test_changed_notes_returns_false(self) -> None:
        """Modified own_notes zone should return False."""
        original = (
            "# Test\n\n## Überblick\n\nText.\n\n"
            "## Eigene Notizen\n\nOriginal notes.\n\n"
            "## Schlüsselquellen\n\nSources.\n\n"
            "## Changelog\n\nLog.\n"
        )
        modified = (
            "# Test\n\n## Überblick\n\nText.\n\n"
            "## Eigene Notizen\n\nTAMPERED notes.\n\n"
            "## Schlüsselquellen\n\nSources.\n\n"
            "## Changelog\n\nLog.\n"
        )
        assert validate_own_notes_unchanged(original, modified) is False
