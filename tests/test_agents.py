"""Unit tests for agent modules (non-LLM parts)."""

from __future__ import annotations

import json

import pytest

from agents.llm.provider import LLMResponse
from agents.researcher import _parse_findings


@pytest.mark.unit
class TestResearcherParsing:
    """Tests for researcher finding parsing."""

    def test_parse_valid_findings(self) -> None:
        """Valid JSON array should produce Finding objects."""
        response = LLMResponse(
            content=json.dumps(
                [
                    {
                        "title": "Test Finding",
                        "summary": "A test finding.",
                        "source_name": "Test Source",
                        "source_url": "https://example.com",
                        "source_date": "2026-04-14",
                        "source_type": "vendor",
                        "confidence": 0.9,
                        "credibility": "high",
                        "geographic_origin": "ch",
                        "operation": "update_text",
                        "tags": ["test"],
                        "suggested_subpage": "test.md",
                    }
                ]
            ),
            model="test",
        )
        findings = _parse_findings(response, "01-plattform-architektur")
        assert len(findings) == 1
        assert findings[0].title == "Test Finding"
        assert findings[0].confidence == 0.9
        assert findings[0].chapter == "01-plattform-architektur"

    def test_parse_empty_array(self) -> None:
        """Empty array should return empty list."""
        response = LLMResponse(content="[]", model="test")
        findings = _parse_findings(response, "01")
        assert findings == []

    def test_parse_json_in_code_block(self) -> None:
        """JSON wrapped in code block should be extracted."""
        response = LLMResponse(
            content='```json\n[{"title": "Test", "summary": "S", "source_name": "N"}]\n```',
            model="test",
        )
        findings = _parse_findings(response, "01")
        assert len(findings) == 1

    def test_parse_invalid_json(self) -> None:
        """Invalid JSON should return empty list."""
        response = LLMResponse(content="not json at all", model="test")
        findings = _parse_findings(response, "01")
        assert findings == []

    def test_parse_malformed_finding_skipped(self) -> None:
        """Finding missing required fields should be skipped."""
        response = LLMResponse(
            content=json.dumps(
                [
                    {"title": "Good", "summary": "OK", "source_name": "S"},
                    {"bad_field": "no title"},
                ]
            ),
            model="test",
        )
        findings = _parse_findings(response, "01")
        assert len(findings) == 1


@pytest.mark.unit
class TestProviderRetry:
    """Tests for LLM provider retry logic."""

    def test_provider_factory_unknown_raises(self) -> None:
        """Unknown provider should raise ValueError."""
        from agents.config_schema import AgentConfig
        from agents.llm.factory import create_provider

        config = AgentConfig(provider="unknown_provider", model="test")
        with pytest.raises(ValueError, match="Unknown provider"):
            create_provider(config)
