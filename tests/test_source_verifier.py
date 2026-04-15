"""Unit tests for agents/source_verifier.py."""

from __future__ import annotations

import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from agents import source_verifier
from agents.llm.provider import LLMError, LLMResponse


def _resp(content: str) -> LLMResponse:
    return LLMResponse(content=content, model="test-model")


@pytest.mark.unit
class TestStripHtml:
    def test_drops_tags(self) -> None:
        html = "<p>Hello <b>world</b></p>"
        assert source_verifier._strip_html(html) == "Hello world"

    def test_drops_script_and_style(self) -> None:
        html = "<html><script>alert(1)</script><style>x{}</style><p>keep</p></html>"
        out = source_verifier._strip_html(html)
        assert "alert" not in out
        assert "keep" in out

    def test_collapses_whitespace(self) -> None:
        html = "<p>a\n\n  b\t\tc</p>"
        assert source_verifier._strip_html(html) == "a b c"


@pytest.mark.unit
class TestFetchText:
    def test_empty_url_returns_none(self) -> None:
        assert source_verifier.fetch_text("") is None

    def test_success(self) -> None:
        fake_resp = MagicMock()
        fake_resp.read.return_value = b"<html><body>Hello</body></html>"
        fake_resp.headers.get_content_charset.return_value = "utf-8"
        fake_resp.__enter__ = MagicMock(return_value=fake_resp)
        fake_resp.__exit__ = MagicMock(return_value=False)

        with patch.object(source_verifier.urllib.request, "urlopen", return_value=fake_resp):
            result = source_verifier.fetch_text("https://example.com")
        assert result == "Hello"

    def test_timeout_returns_none(self) -> None:
        with patch.object(
            source_verifier.urllib.request,
            "urlopen",
            side_effect=urllib.error.URLError("timeout"),
        ):
            assert source_verifier.fetch_text("https://example.com") is None

    def test_truncates_to_max_chars(self) -> None:
        fake_resp = MagicMock()
        fake_resp.read.return_value = ("<p>" + ("x" * 10000) + "</p>").encode()
        fake_resp.headers.get_content_charset.return_value = "utf-8"
        fake_resp.__enter__ = MagicMock(return_value=fake_resp)
        fake_resp.__exit__ = MagicMock(return_value=False)

        with patch.object(source_verifier.urllib.request, "urlopen", return_value=fake_resp):
            result = source_verifier.fetch_text("https://example.com", max_chars=100)
        assert result is not None
        assert len(result) == 100


@pytest.mark.unit
class TestVerifyClaim:
    def test_supported(self) -> None:
        provider = MagicMock()
        provider.complete.return_value = _resp("supported")
        assert source_verifier.verify_claim("claim", "source text", provider) == "supported"

    def test_partial_with_punctuation(self) -> None:
        provider = MagicMock()
        provider.complete.return_value = _resp("partial.")
        assert source_verifier.verify_claim("c", "s", provider) == "partial"

    def test_unsupported_with_leading_space(self) -> None:
        provider = MagicMock()
        provider.complete.return_value = _resp("  Unsupported  \n")
        assert source_verifier.verify_claim("c", "s", provider) == "unsupported"

    def test_garbage_response_becomes_unclear(self) -> None:
        provider = MagicMock()
        provider.complete.return_value = _resp("I think maybe perhaps")
        assert source_verifier.verify_claim("c", "s", provider) == "unclear"

    def test_empty_source_returns_failed(self) -> None:
        provider = MagicMock()
        assert source_verifier.verify_claim("c", "", provider) == "failed"
        provider.complete.assert_not_called()

    def test_llm_error_returns_failed(self) -> None:
        provider = MagicMock()
        provider.complete.side_effect = LLMError("boom")
        assert source_verifier.verify_claim("c", "s", provider) == "failed"


@pytest.mark.unit
class TestVerifyFinding:
    def test_fetch_fail_returns_failed(self) -> None:
        provider = MagicMock()
        with patch.object(source_verifier, "fetch_text", return_value=None):
            assert source_verifier.verify_finding("c", "https://x.com", provider) == "failed"
        provider.complete.assert_not_called()

    def test_fetch_and_verify(self) -> None:
        provider = MagicMock()
        provider.complete.return_value = _resp("supported")
        with patch.object(source_verifier, "fetch_text", return_value="some text"):
            result = source_verifier.verify_finding("claim", "https://x.com", provider)
        assert result == "supported"
