"""Logging configuration."""

import logging
import sys
from typing import Any, cast

import structlog


def setup_logging(
    level: str = "INFO", log_file: str | None = None, format_type: str = "json"
) -> None:
    """Configurar logging estructurado."""

    # Configurar structlog
    processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if format_type == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configurar logging estándar
    log_level = getattr(logging, level.upper(), logging.INFO)

    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]

    if log_file:
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(level=log_level, format="%(message)s", handlers=handlers)

    # Reducir ruido de librerías
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Obtener un logger configurado."""
    return cast(logging.Logger, structlog.get_logger(name))
