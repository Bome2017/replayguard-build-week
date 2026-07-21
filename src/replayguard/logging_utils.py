"""Small structured-logging boundary for local runs and CI diagnostics."""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime


class JsonLogFormatter(logging.Formatter):
    """Render one stable JSON object per log record."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname.lower(),
            "logger": record.name,
            "event": record.getMessage(),
        }
        fields = getattr(record, "replayguard_fields", None)
        if isinstance(fields, dict):
            payload.update(fields)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def configure_logging(*, verbose: bool = False) -> None:
    """Configure package logging without changing unrelated application loggers."""

    requested_level = "INFO" if verbose else os.getenv("REPLAYGUARD_LOG_LEVEL", "WARNING")
    level = getattr(logging, requested_level.upper(), logging.WARNING)
    package_logger = logging.getLogger("replayguard")
    package_logger.handlers.clear()
    handler = logging.StreamHandler()
    if os.getenv("REPLAYGUARD_LOG_FORMAT", "json").casefold() == "json":
        handler.setFormatter(JsonLogFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(levelname)s %(name)s %(message)s"))
    package_logger.addHandler(handler)
    package_logger.setLevel(level)
    package_logger.propagate = False


def log_event(logger: logging.Logger, event: str, **fields: object) -> None:
    """Emit a structured event with non-secret execution metadata."""

    logger.info(event, extra={"replayguard_fields": fields})
