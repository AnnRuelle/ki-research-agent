"""Structured logging configuration for the KI-KB pipeline."""

from __future__ import annotations

import json
import logging
import sys
import uuid
from datetime import datetime, timezone
from typing import Any


class JSONFormatter(logging.Formatter):
    """Formats log records as JSON lines for GitHub Actions readability."""

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record as a JSON string."""
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "run_id"):
            log_entry["run_id"] = record.run_id
        if hasattr(record, "agent"):
            log_entry["agent"] = record.agent
        if hasattr(record, "chapter"):
            log_entry["chapter"] = record.chapter
        if record.exc_info and record.exc_info[1]:
            log_entry["exception"] = str(record.exc_info[1])
        return json.dumps(log_entry, ensure_ascii=False)


def setup_logging(level: str = "INFO", format_style: str = "json") -> str:
    """Configure logging for the pipeline. Returns the run_id."""
    run_id = uuid.uuid4().hex[:12]

    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove existing handlers
    for handler in root.handlers[:]:
        root.removeHandler(handler)

    handler = logging.StreamHandler(open(sys.stdout.fileno(), mode="w", encoding="utf-8", closefd=False))  # noqa: SIM115
    if format_style == "json":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))

    root.addHandler(handler)

    return run_id


def get_logger(name: str, run_id: str | None = None, agent: str | None = None) -> logging.Logger:
    """Get a logger with optional run_id and agent context."""
    logger = logging.getLogger(name)
    if run_id or agent:
        old_factory = logging.getLogRecordFactory()

        def record_factory(*args: Any, **kwargs: Any) -> logging.LogRecord:
            record = old_factory(*args, **kwargs)
            if run_id:
                record.run_id = run_id
            if agent:
                record.agent = agent
            return record

        logging.setLogRecordFactory(record_factory)
    return logger
