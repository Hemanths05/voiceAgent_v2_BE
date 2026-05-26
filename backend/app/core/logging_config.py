"""
Logging Configuration
Sets up structured logging with JSON format for production
"""
import logging
import sys
from typing import Any, Dict
from datetime import datetime
import json
from app.config import settings


class JSONFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON

        Args:
            record: Log record

        Returns:
            JSON string
        """
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields if present
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)

        # Add request ID if present (for tracing)
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id

        # Add call SID if present (for telephony tracing)
        if hasattr(record, "call_sid"):
            log_data["call_sid"] = record.call_sid

        # Add company ID if present (for multi-tenancy tracing)
        if hasattr(record, "company_id"):
            log_data["company_id"] = record.company_id

        return json.dumps(log_data)


class PlainFormatter(logging.Formatter):
    """
    Plain text formatter for development
    """

    def __init__(self):
        super().__init__(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )


def setup_logging() -> None:
    """
    Configure logging for the application
    Uses JSON format in production, plain text in development
    """
    # Get log level from settings
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)

    # Use JSON formatter in production, plain in development
    if settings.environment == "production":
        formatter = JSONFormatter()
    else:
        formatter = PlainFormatter()

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Set log levels for third-party libraries
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("motor").setLevel(logging.INFO)
    logging.getLogger("pymongo").setLevel(logging.WARNING)
    logging.getLogger("websockets").setLevel(logging.INFO)

    # Log startup message
    root_logger.info(
        f"Logging configured: level={settings.log_level}, "
        f"environment={settings.environment}, "
        f"format={'JSON' if settings.environment == 'production' else 'PLAIN'}"
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance

    Args:
        name: Logger name (usually __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


class LoggerAdapter(logging.LoggerAdapter):
    """
    Custom logger adapter that adds context fields to all log records
    """

    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple:
        """
        Process log message and add context fields

        Args:
            msg: Log message
            kwargs: Keyword arguments

        Returns:
            Tuple of (msg, kwargs)
        """
        # Add extra fields to the log record
        if "extra" not in kwargs:
            kwargs["extra"] = {}

        # Merge context into extra
        kwargs["extra"].update(self.extra)

        return msg, kwargs


def get_context_logger(
    name: str,
    request_id: str = None,
    call_sid: str = None,
    company_id: str = None,
    **extra_context
) -> LoggerAdapter:
    """
    Get a logger with context fields

    Args:
        name: Logger name
        request_id: Request ID for tracing
        call_sid: Call SID for telephony tracing
        company_id: Company ID for multi-tenancy tracing
        **extra_context: Additional context fields

    Returns:
        Logger adapter with context
    """
    logger = get_logger(name)
    context = {}

    if request_id:
        context["request_id"] = request_id
    if call_sid:
        context["call_sid"] = call_sid
    if company_id:
        context["company_id"] = company_id

    context.update(extra_context)

    return LoggerAdapter(logger, context)


# Export functions
__all__ = [
    "setup_logging",
    "get_logger",
    "get_context_logger",
    "LoggerAdapter",
]
