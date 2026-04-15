"""Source verification: fetch URL and LLM-check whether it supports a finding.

Catches hallucinations before they reach the Writer. Findings flagged as
"unsupported" are dropped upstream; "partial"/"unclear" are kept with the
verification status recorded on the Finding.
"""

from __future__ import annotations

import logging
import re
import urllib.error
import urllib.request
from typing import Literal

from agents.llm.provider import LLMError, LLMProvider

logger = logging.getLogger(__name__)

VerificationStatus = Literal["supported", "partial", "unsupported", "unclear", "failed"]

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")
_SCRIPT_RE = re.compile(r"<script[^>]*>.*?</script>", re.DOTALL | re.IGNORECASE)
_STYLE_RE = re.compile(r"<style[^>]*>.*?</style>", re.DOTALL | re.IGNORECASE)

USER_AGENT = "KI-KB-Verifier/1.0 (+https://github.com/AnnRuelle/ki-research-agent)"


def _strip_html(html: str) -> str:
    """Crude HTML-to-text: drop script/style blocks and tags, collapse whitespace."""
    html = _SCRIPT_RE.sub(" ", html)
    html = _STYLE_RE.sub(" ", html)
    text = _HTML_TAG_RE.sub(" ", html)
    return _WHITESPACE_RE.sub(" ", text).strip()


def fetch_text(url: str, timeout: int = 10, max_chars: int = 5000) -> str | None:
    """Fetch a URL and return plain text (up to max_chars). None on failure."""
    if not url:
        return None
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read(500_000)
            encoding = resp.headers.get_content_charset() or "utf-8"
    except (urllib.error.URLError, TimeoutError, ConnectionResetError, OSError) as e:
        logger.warning("source_verifier: fetch failed %s: %s", url[:80], e)
        return None

    try:
        html = raw.decode(encoding, errors="replace")
    except LookupError:
        html = raw.decode("utf-8", errors="replace")

    text = _strip_html(html)
    return text[:max_chars] if text else None


SYSTEM_PROMPT = """\
Du bist ein Fact-Check-Agent. Prüfe, ob ein Quelltext eine Behauptung stützt.

Antworte mit GENAU EINEM Wort, ohne Begründung:
- supported    Quelle belegt die Behauptung eindeutig
- partial      teilweise belegt, Nuance fehlt oder übertrieben
- unsupported  Quelle sagt etwas anderes oder Behauptung nicht enthalten
- unclear      Quelle zu kurz/mehrdeutig für eine Entscheidung
"""


def verify_claim(summary: str, source_text: str, provider: LLMProvider) -> VerificationStatus:
    """Run the LLM fact-check. Assumes source_text is already fetched."""
    if not source_text:
        return "failed"
    user = f"""Behauptung:
{summary}

Quelltext:
{source_text}

Ein Wort:"""
    try:
        response = provider.complete(system=SYSTEM_PROMPT, user=user, temperature=0.0)
    except LLMError:
        logger.exception("source_verifier: LLM call failed")
        return "failed"

    stripped = response.content.strip().lower()
    if not stripped:
        return "unclear"
    first_word = re.sub(r"[^a-z]", "", stripped.split()[0])
    if first_word in {"supported", "partial", "unsupported", "unclear"}:
        return first_word  # type: ignore[return-value]
    return "unclear"


def verify_finding(summary: str, source_url: str, provider: LLMProvider) -> VerificationStatus:
    """Fetch the source URL and verify the summary against it."""
    text = fetch_text(source_url)
    if text is None:
        return "failed"
    return verify_claim(summary, text, provider)
