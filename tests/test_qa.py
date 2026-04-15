"""Unit tests for Q&A agent (non-LLM parts)."""

from __future__ import annotations

from pathlib import Path

import pytest

import agents.qa as qa_module
from agents.qa import (
    _extract_keywords,
    _load_chapter_content,
    _score_file,
    _select_relevant_chapters,
)


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


@pytest.mark.unit
class TestExtractKeywords:
    def test_drops_stopwords(self) -> None:
        kws = _extract_keywords("Was kostet eine KI-Plattform fuer den Kanton?")
        assert "kostet" in kws
        assert "plattform" in kws
        assert "kanton" in kws
        assert "was" not in kws
        assert "fuer" not in kws

    def test_drops_short_tokens(self) -> None:
        kws = _extract_keywords("KI ist ok")
        assert all(len(k) >= 3 for k in kws)

    def test_lowercases(self) -> None:
        kws = _extract_keywords("Azure OpenAI Service")
        assert "azure" in kws
        assert "openai" in kws


@pytest.mark.unit
class TestScoreFile:
    def test_scores_filename_hits(self, tmp_path: Path) -> None:
        f = tmp_path / "azure-openai.md"
        f.write_text("content", encoding="utf-8")
        assert _score_file(f, {"azure"}) >= 1

    def test_scores_content_hits(self, tmp_path: Path) -> None:
        f = tmp_path / "foo.md"
        f.write_text("# Bewertungsraster\n\nVergleich der Anbieter.", encoding="utf-8")
        assert _score_file(f, {"bewertungsraster"}) >= 1

    def test_zero_with_no_match(self, tmp_path: Path) -> None:
        f = tmp_path / "foo.md"
        f.write_text("totally unrelated content", encoding="utf-8")
        assert _score_file(f, {"xyzzy"}) == 0

    def test_zero_with_no_keywords(self, tmp_path: Path) -> None:
        f = tmp_path / "foo.md"
        f.write_text("content", encoding="utf-8")
        assert _score_file(f, set()) == 0


@pytest.mark.unit
class TestLoadChapterContent:
    def _setup_chapter(self, tmp_path: Path) -> Path:
        chapter = tmp_path / "99-test"
        chapter.mkdir()
        (chapter / "index.md").write_text("# Index\nOverview", encoding="utf-8")
        (chapter / "azure-openai.md").write_text("# Azure\nDetails", encoding="utf-8")
        (chapter / "aws-bedrock.md").write_text("# AWS\nDetails", encoding="utf-8")
        (chapter / "unrelated.md").write_text("# Something else\nNo match", encoding="utf-8")
        (chapter / "data.data.yaml").write_text("schema_version: 1\nrows: []\n", encoding="utf-8")
        return chapter

    def test_returns_empty_for_missing_chapter(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(qa_module, "CHAPTERS_DIR", tmp_path)
        assert _load_chapter_content("nonexistent") == ""

    def test_always_includes_index_and_data_yaml(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._setup_chapter(tmp_path)
        monkeypatch.setattr(qa_module, "CHAPTERS_DIR", tmp_path)
        out = _load_chapter_content("99-test", keywords={"xyzzy"})
        assert "index.md" in out
        assert "data.data.yaml" in out

    def test_keyword_match_prioritizes_subpage(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._setup_chapter(tmp_path)
        monkeypatch.setattr(qa_module, "CHAPTERS_DIR", tmp_path)
        out = _load_chapter_content("99-test", keywords={"azure"}, max_chars=500)
        azure_idx = out.find("azure-openai.md")
        aws_idx = out.find("aws-bedrock.md")
        assert azure_idx != -1
        assert azure_idx < aws_idx or aws_idx == -1

    def test_respects_char_cap(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        chapter = tmp_path / "99-test"
        chapter.mkdir()
        (chapter / "index.md").write_text("overview", encoding="utf-8")
        for i in range(10):
            (chapter / f"page{i}.md").write_text("x" * 5000, encoding="utf-8")
        monkeypatch.setattr(qa_module, "CHAPTERS_DIR", tmp_path)
        out = _load_chapter_content("99-test", keywords=set(), max_chars=10_000)
        assert len(out) < 15_000  # index + ~2 pages + overhead
