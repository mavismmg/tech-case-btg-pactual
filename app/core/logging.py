import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any


_STANDARD_LOG_RECORD_ATTRIBUTES = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
    "taskName",
}
_SENSITIVE_KEYS = {"password", "token", "access_token", "refresh_token", "password_hash"}


class JsonFormatter(logging.Formatter):
    def __init__(self, pretty: bool = False) -> None:
        super().__init__()
        self.pretty = pretty

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        for key, value in record.__dict__.items():
            if key in _STANDARD_LOG_RECORD_ATTRIBUTES or key.startswith("_"):
                continue

            payload[key] = "[REDACTED]" if key in _SENSITIVE_KEYS else value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        if record.stack_info:
            payload["stack"] = self.formatStack(record.stack_info)

        indent = 2 if self.pretty else None
        return json.dumps(payload, default=str, ensure_ascii=False, indent=indent)


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default

    return value.lower() in {"1", "true", "yes", "on"}


def configure_logging(level: int = logging.INFO, pretty: bool | None = None) -> None:
    if pretty is None:
        pretty = _env_flag("LOG_PRETTY_JSON")

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter(pretty=pretty))

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(level)
