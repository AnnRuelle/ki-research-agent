"""Radar Agent: continuously monitors narrow topics and appends new findings.

Two modes:
- list: YAML file is source of truth. LLM identifies new entries, we append.
- feed: Markdown file. LLM generates new entries, we prepend them, then trim
  entries older than trim_days.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml

from agents.config_schema import RadarConfig, load_config
from agents.llm.factory import create_provider
from agents.llm.provider import LLMProvider
from agents.web_search import search

logger = logging.getLogger(__name__)

RADAR_DIR = Path("radar")


LIST_SYSTEM_PROMPT = """\
Du bist ein Radar-Agent für eine Wissensdatenbank zu KI-Plattformen in Schweizer Kantonen.

Deine Aufgabe: Identifiziere aus den Web-Search-Ergebnissen NEUE Einträge, die noch nicht
in der bestehenden Liste stehen. Gib NUR neue Einträge zurück.

Regeln:
- Keine Duplikate: prüfe sorgfältig gegen die bestehenden Einträge (nach Name/Titel/URL).
- Quelle muss seriös sein (kein Twitter/Reddit/Hearsay).
- Antwort als JSON-Array. Jedes Objekt hat die folgenden Keys:
  {schema_fields}
- Leeres Array [] wenn nichts Neues.
- Bei Datumsfeldern ('erstgesichtet', 'publiziert') das heutige Datum einsetzen: {today}.
- Bei 'quelle' die URL aus den Search-Ergebnissen.
"""


FEED_SYSTEM_PROMPT = """\
Du bist ein Radar-Agent für einen News-Feed zu LLMs und Foundation Models.

Deine Aufgabe: Identifiziere aus den Web-Search-Ergebnissen NEUE Meldungen, die noch nicht
im bestehenden Feed stehen. Gib NUR neue Einträge zurück.

Regeln:
- Keine Duplikate: prüfe gegen bestehende Einträge.
- Quelle muss seriös sein (offizielle Blogs, etablierte Medien, keine Gerüchte).
- 2-3 Sätze Zusammenfassung pro Eintrag.
- Antwort als JSON-Array. Jedes Objekt:
  {
    "date": "YYYY-MM-DD",
    "title": "Kurztitel",
    "summary": "2-3 Sätze",
    "url": "Quell-URL"
  }
- Leeres Array [] wenn nichts Neues.
- 'date' ist das Release-Datum der Meldung (falls unklar: heute).
"""


def _run_searches(queries: list[str]) -> str:
    """Run all configured queries and format results as context for the LLM."""
    if not queries:
        return "(Keine Queries konfiguriert)"
    seen_urls: set[str] = set()
    lines: list[str] = []
    for query in queries:
        for r in search(query, max_results=3):
            if r.url in seen_urls:
                continue
            seen_urls.add(r.url)
            lines.append(f"- [{r.title}]({r.url})\n  {r.content[:300]}")
    return "\n".join(lines) if lines else "(Keine Web-Search-Ergebnisse)"


def _parse_json_array(content: str) -> list[dict[str, Any]]:
    """Extract a JSON array of dicts from an LLM response."""
    content = content.strip()
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        logger.error("Radar: LLM returned invalid JSON: %s", content[:200])
        return []
    if isinstance(parsed, dict):
        return [parsed]
    if not isinstance(parsed, list):
        return []
    return [item for item in parsed if isinstance(item, dict)]


def _normalize_key(key: str) -> str:
    """Normalize a column name to a YAML-friendly snake_case key."""
    return key.lower().replace("-", "_").replace(" ", "_")


def run_list_radar(
    radar_name: str,
    config: RadarConfig,
    provider: LLMProvider,
) -> int:
    """Run a list-mode radar. Returns number of new entries added."""
    yaml_path = RADAR_DIR / f"{radar_name.replace('_', '-')}.yaml"
    if not yaml_path.exists():
        logger.warning("Radar %s: YAML not found at %s", radar_name, yaml_path)
        return 0

    raw = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
    columns: list[str] = [c["name"] for c in raw.get("columns", [])]
    existing_rows: list[dict[str, Any]] = list(raw.get("rows") or [])

    today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    web_results = _run_searches(config.search_queries)

    existing_summary = yaml.safe_dump(
        existing_rows,
        allow_unicode=True,
        sort_keys=False,
    )
    system = LIST_SYSTEM_PROMPT.format(
        schema_fields=", ".join(columns),
        today=today,
    )
    user = f"""\
## Bestehende Einträge (keine Duplikate hiervon!):
```yaml
{existing_summary}
```

## Neue Web-Search-Ergebnisse:
{web_results}

Finde NUR neue Einträge, die noch nicht oben gelistet sind.
"""
    response = provider.complete(system=system, user=user, temperature=0.3)
    new_entries = _parse_json_array(response.content)

    if not new_entries:
        logger.info("Radar %s: no new entries", radar_name)
        return 0

    for entry in new_entries:
        existing_rows.append({_normalize_key(k): v for k, v in entry.items()})

    raw["rows"] = existing_rows
    raw["last_updated"] = today

    yaml_path.write_text(
        yaml.safe_dump(raw, allow_unicode=True, sort_keys=False, width=120),
        encoding="utf-8",
    )
    logger.info("Radar %s: added %d entries", radar_name, len(new_entries))
    return len(new_entries)


ENTRY_HEADER_RE = re.compile(r"^### (\d{4}-\d{2}-\d{2})\b")


def _trim_feed(content: str, trim_days: int) -> tuple[str, int]:
    """Remove feed entries older than trim_days. Returns (new_content, removed_count)."""
    cutoff = datetime.now(tz=timezone.utc).date() - timedelta(days=trim_days)
    parts = re.split(r"(?=^### \d{4}-\d{2}-\d{2})", content, flags=re.MULTILINE)
    if len(parts) <= 1:
        return content, 0
    header = parts[0]
    kept: list[str] = []
    removed = 0
    for block in parts[1:]:
        m = ENTRY_HEADER_RE.match(block)
        if not m:
            kept.append(block)
            continue
        try:
            entry_date = datetime.strptime(m.group(1), "%Y-%m-%d").date()
        except ValueError:
            kept.append(block)
            continue
        if entry_date < cutoff:
            removed += 1
            continue
        kept.append(block)
    return header + "".join(kept), removed


def _render_feed_entry(entry: dict[str, Any], fallback_date: str) -> str:
    """Render a single feed entry as a markdown block."""
    date = entry.get("date") or fallback_date
    title = entry.get("title") or "(ohne Titel)"
    summary = entry.get("summary") or ""
    url = entry.get("url") or ""
    link = f"\n\n[Quelle]({url})" if url else ""
    return f"### {date} — {title}\n\n{summary}{link}\n"


def run_feed_radar(
    radar_name: str,
    config: RadarConfig,
    provider: LLMProvider,
) -> int:
    """Run a feed-mode radar. Returns number of new entries prepended."""
    md_path = RADAR_DIR / f"{radar_name.replace('_', '-')}.md"
    if not md_path.exists():
        logger.warning("Radar %s: MD file not found at %s", radar_name, md_path)
        return 0

    existing_content = md_path.read_text(encoding="utf-8")
    today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    web_results = _run_searches(config.search_queries)

    user = f"""\
## Bestehender Feed (keine Duplikate hiervon!):
{existing_content}

## Neue Web-Search-Ergebnisse:
{web_results}

Heutiges Datum: {today}. Finde NUR neue Meldungen, die noch nicht oben im Feed stehen.
"""
    response = provider.complete(system=FEED_SYSTEM_PROMPT, user=user, temperature=0.3)
    new_entries = _parse_json_array(response.content)
    new_blocks = [_render_feed_entry(e, today) for e in new_entries]

    if new_blocks:
        joined = "\n".join(new_blocks)
        if "*Noch keine Einträge.*" in existing_content:
            new_content = existing_content.replace("*Noch keine Einträge.*", joined)
        else:
            feed_marker = "## Feed\n"
            if feed_marker in existing_content:
                idx = existing_content.index(feed_marker) + len(feed_marker)
                new_content = existing_content[:idx] + "\n" + joined + "\n" + existing_content[idx:]
            else:
                new_content = existing_content.rstrip() + "\n\n" + joined + "\n"
    else:
        new_content = existing_content

    new_content, removed = _trim_feed(new_content, config.trim_days)
    md_path.write_text(new_content, encoding="utf-8")

    logger.info(
        "Radar %s: prepended %d entries, trimmed %d",
        radar_name,
        len(new_blocks),
        removed,
    )
    return len(new_blocks)


def run_radar(
    radar_name: str,
    provider: LLMProvider | None = None,
) -> int:
    """Run a single radar by name. Returns number of new entries."""
    config = load_config()
    if radar_name not in config.radars:
        msg = f"Unknown radar: {radar_name}"
        raise ValueError(msg)
    radar_config = config.radars[radar_name]
    if not radar_config.enabled:
        logger.info("Radar %s is disabled, skipping", radar_name)
        return 0

    if provider is None:
        provider = create_provider(radar_config.agent)

    if radar_config.mode == "list":
        return run_list_radar(radar_name, radar_config, provider)
    if radar_config.mode == "feed":
        return run_feed_radar(radar_name, radar_config, provider)
    msg = f"Unknown radar mode: {radar_config.mode}"
    raise ValueError(msg)


def run_all_enabled(schedule_filter: str | None = None) -> dict[str, int]:
    """Run all enabled radars. schedule_filter: 'daily', 'sunday', etc. (prefix match)."""
    config = load_config()
    results: dict[str, int] = {}
    for name, radar in config.radars.items():
        if not radar.enabled:
            continue
        if schedule_filter and not radar.schedule.startswith(schedule_filter):
            continue
        try:
            results[name] = run_radar(name)
        except Exception:
            logger.exception("Radar %s failed", name)
            results[name] = -1
    return results


def main() -> None:
    """CLI: python -m agents.radar <name|--all-enabled|--daily|--weekly>."""
    import sys

    from agents.logging_config import setup_logging

    setup_logging()

    if len(sys.argv) < 2:
        print("Usage: python -m agents.radar <name|--all-enabled|--daily|--weekly>")
        sys.exit(1)

    arg = sys.argv[1]
    if arg == "--all-enabled":
        results = run_all_enabled()
    elif arg == "--daily":
        results = run_all_enabled(schedule_filter="daily")
    elif arg == "--weekly":
        results = run_all_enabled(schedule_filter="sunday")
    else:
        results = {arg: run_radar(arg)}

    print(f"\n{'=' * 60}")
    print("Radar-Lauf Zusammenfassung:")
    for name, count in results.items():
        status = "FEHLER" if count < 0 else f"{count} neue Einträge"
        print(f"  - {name}: {status}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
