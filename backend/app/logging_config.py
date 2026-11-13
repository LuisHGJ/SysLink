"""Logging estruturado (JSON) com redação de PII."""
import logging
import re
import sys

import structlog

from app.config import settings


class RedactionFilter(logging.Filter):
    """Remove PII e credenciais do log."""

    PATTERNS = {
        "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
        "cpf": r"\d{3}\.\d{3}\.\d{3}-\d{2}",
        "token": r"(Bearer|token)[\s:]+[A-Za-z0-9._-]+",
        "password": r"(password|pwd)[\s:]*[^\s,}]+",
    }

    def filter(self, record: logging.LogRecord) -> bool:
        message = str(record.msg)
        for key, pattern in self.PATTERNS.items():
            message = re.sub(pattern, f"[REDACTED_{key.upper()}]", message)
        record.msg = message
        return True


def setup_logging() -> None:
    """Configura structlog + JSON, com redação de PII."""
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
    )

    # Filtro de redação em todos os handlers
    for handler in logging.getLogger().handlers:
        handler.addFilter(RedactionFilter())

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.log_level.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Retorna um logger estruturado."""
    return structlog.get_logger(name)
