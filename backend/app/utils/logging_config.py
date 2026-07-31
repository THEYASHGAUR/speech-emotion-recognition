"""
Structured logging configuration for AutoAce AI.
Outputs JSON-formatted logs in production, human-readable in development.
"""

import logging
import sys
from typing import Any

from app.config import get_settings

settings = get_settings()


class _PrettyFormatter(logging.Formatter):
    """Human-readable formatter for local development."""

    LEVEL_COLORS = {
        logging.DEBUG: "\033[36m",     # Cyan
        logging.INFO: "\033[32m",      # Green
        logging.WARNING: "\033[33m",   # Yellow
        logging.ERROR: "\033[31m",     # Red
        logging.CRITICAL: "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.LEVEL_COLORS.get(record.levelno, self.RESET)
        level = f"{color}{record.levelname:<8}{self.RESET}"
        return (
            f"{self.formatTime(record, '%H:%M:%S')} {level} "
            f"[{record.name}] {record.getMessage()}"
        )


class _JSONFormatter(logging.Formatter):
    """JSON formatter for production log aggregation."""

    import json as _json

    def format(self, record: logging.LogRecord) -> str:
        import json
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def configure_logging() -> None:
    """Configure root logger based on environment."""
    import os
    os.environ["TQDM_DISABLE"] = "1"
    os.environ["DISABLE_TQDM"] = "1"

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if settings.debug else logging.INFO)

    # Remove existing handlers
    root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)

    if settings.environment == "production":
        handler.setFormatter(_JSONFormatter())
    else:
        handler.setFormatter(_PrettyFormatter())

    root_logger.addHandler(handler)

    # Quieten noisy third-party loggers
    noisy_loggers = (
        "urllib3", "httpx", "transformers", "torch", "numba",
        "librosa", "soundfile", "asyncio", "uvicorn.access",
        "uvicorn.error", "matplotlib", "PIL", "filelock", "huggingface_hub"
    )
    for noisy in noisy_loggers:
        logging.getLogger(noisy).setLevel(logging.WARNING)
