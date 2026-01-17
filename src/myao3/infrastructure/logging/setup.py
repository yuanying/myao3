"""Logging setup module using structlog."""

import logging
import sys

import structlog
from structlog.stdlib import BoundLogger

from myao3.config.models import LoggingConfig


def setup_logging(config: LoggingConfig) -> None:
    """Initialize logging configuration.

    Args:
        config: Logging configuration specifying level and format.
    """
    # Map string level to logging constant
    log_level = getattr(logging, config.level)

    # Configure standard logging
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add stdout handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)
    root_logger.addHandler(handler)

    # Common processors
    shared_processors: list[structlog.typing.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.TimeStamper(fmt="iso", utc=True),
    ]

    # Format-specific renderer
    if config.format == "json":
        renderer: structlog.typing.Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=shared_processors
        + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure the formatter for the handler
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )
    handler.setFormatter(formatter)


def get_logger(name: str | None = None) -> BoundLogger:
    """Get a logger instance.

    Args:
        name: Logger name, typically the module name (__name__).

    Returns:
        A bound logger instance that can be used for logging.
    """
    return structlog.stdlib.get_logger(name)
