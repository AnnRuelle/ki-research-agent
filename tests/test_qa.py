"""Unit tests for Q&A agent (non-LLM parts)."""

from __future__ import annotations

import pytest

from agents.qa import _select_relevant_chapters


@pytest.mark.unit
class TestQAChapterSelection:
    """Tests for chapter selection logic."""

    def test_azure_question_selects_markt(self) -> None:
        """Question about Azure should select market chapter."""
        selected = _select_relevant_chapters("Welche Kantone setzen auf Azure?")
        assert "07-markt-anbieter" in selected

    def test_kosten_question_selects_kosten(self) -> None:
        """Question about costs should select cost chapter."""
        selected = _select_relevant_chapters("Was kostet eine KI-Plattform?")
        assert "09-kosten-lizenzmodelle" in selected

    def test_datenschutz_question(self) -> None:
        """Question about data protection should select relevant chapter."""
        selected = _select_relevant_chapters("Was sagt das NDSG zu KI?")
        assert "03-datenschutz-informationssicherheit" in selected

    def test_kanton_question(self) -> None:
        """Question about cantons should select reference chapter."""
        selected = _select_relevant_chapters("Was macht der Kanton Zuerich?")
        assert "10-referenzprojekte-kantone" in selected

    def test_unknown_question_gets_defaults(self) -> None:
        """Unrelated question should get default chapters."""
        selected = _select_relevant_chapters("xyzzy foobar")
        assert len(selected) >= 1

    def test_max_chapters_respected(self) -> None:
        """Should not return more chapters than max."""
        selected = _select_relevant_chapters("alles ueber alles", max_chapters=3)
        assert len(selected) <= 3

    def test_beschaffung_question(self) -> None:
        """Question about procurement should select procurement chapter."""
        selected = _select_relevant_chapters("Wie schreibe ich ein Pflichtenheft fuer KI?")
        assert "12-beschaffung" in selected
