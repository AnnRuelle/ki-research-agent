"""URL canonicalization and per-chapter seen-URL memory.

Two responsibilities:
- canonicalize_url: normalize URL variants (www, trailing slash, utm params) to a single key.
- seen-URL store: persist per-chapter which URLs have already produced findings,
  so the Researcher doesn't re-report the same article week after week.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

logger = logging.getLogger(__name__)

SEEN_DIR = Path("updates/seen-urls")

# Tracking params stripped from query string to improve deduplication.
TRACKING_PARAM_PREFIXES = ("utm_", "mc_", "_hs")
TRACKING_PARAM_EXACT = {"fbclid", "gclid", "ref", "ref_src", "trk"}


def canonicalize_url(url: str) -> str:
    """Normalize a URL so equivalent variants collide in a set.

    Rules:
    - lowercase scheme and host
    - strip leading 'www.'
    - drop fragment
    - drop tracking query params (utm_*, fbclid, gclid, ...)
    - strip trailing slash on path (except root '/')
    """
    if not url:
        return ""
    try:
        parsed = urlparse(url.strip())
    except ValueError:
        return url.strip()

    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]

    path = parsed.path
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")

    query_pairs = [
        (k, v)
        for k, v in parse_qsl(parsed.query, keep_blank_values=False)
        if not k.startswith(TRACKING_PARAM_PREFIXES) and k not in TRACKING_PARAM_EXACT
    ]
    query = urlencode(query_pairs)

    return urlunparse((scheme, netloc, path, parsed.params, query, ""))


def _seen_path(chapter_id: str) -> Path:
    return SEEN_DIR / f"{chapter_id}.json"


def load_seen_urls(chapter_id: str) -> dict[str, str]:
    """Load the seen-URL map for a chapter. Returns {canonical_url: first_seen_date}."""
    path = _seen_path(chapter_id)
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        logger.warning("seen-urls: could not read %s, starting fresh", path)
        return {}
    if not isinstance(raw, dict):
        return {}
    return {str(k): str(v) for k, v in raw.items()}


def save_seen_urls(chapter_id: str, seen: dict[str, str]) -> None:
    """Persist the seen-URL map for a chapter."""
    SEEN_DIR.mkdir(parents=True, exist_ok=True)
    path = _seen_path(chapter_id)
    path.write_text(
        json.dumps(seen, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def trim_seen_urls(seen: dict[str, str], max_age_days: int = 180) -> dict[str, str]:
    """Drop entries older than max_age_days. Default: 6 months."""
    cutoff = datetime.now(tz=timezone.utc).date() - timedelta(days=max_age_days)
    kept: dict[str, str] = {}
    for url, date_str in seen.items():
        try:
            seen_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            kept[url] = date_str
            continue
        if seen_date >= cutoff:
            kept[url] = date_str
    return kept


def filter_unseen(urls: list[str], seen: dict[str, str]) -> list[str]:
    """Return only URLs whose canonicalized form is not in `seen`."""
    return [u for u in urls if canonicalize_url(u) not in seen]


def mark_seen(seen: dict[str, str], urls: list[str], date: str | None = None) -> dict[str, str]:
    """Return a new map with urls added under today's date (or the given date)."""
    today = date or datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    updated = dict(seen)
    for url in urls:
        canon = canonicalize_url(url)
        if canon and canon not in updated:
            updated[canon] = today
    return updated
