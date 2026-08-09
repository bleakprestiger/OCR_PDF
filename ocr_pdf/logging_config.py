"""Structured logging configuration for the PDF OCR CLI.

Provides console + rotating-file logging with ISO-8601 timestamps,
structured log levels, and automatic log rotation to prevent unbounded growth.
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Final

# Absolute path constants for the logs directory (relative to project root).
_LOGS_DIR: Final[Path] = Path("logs")
_LOG_FILE: Final[Path] = _LOGS_DIR / "ocr_pdf.log"

# Maximum log file size before rotation: 10 MB each, keep 5 backups.
_MAX_BYTES: Final[int] = 10 * 1024 * 1024
_BACKUP_COUNT: Final[int] = 5

# Log format with ISO-8601 timestamps and module context.
_LOG_FORMAT: Final[str] = (
    "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
)
_DATE_FORMAT: Final[str] = "%Y-%m-%dT%H:%M:%S%z"


def configure_logging(
    *,
    level: int = logging.INFO,
    enable_file: bool = True,
) -> logging.Logger:
    """Configure and return the root application logger.

    Args:
        level: Minimum log level to capture (default INFO for console).
        enable_file: Whether to add a rotating file handler (default True).

    Returns:
        Configured root logger instance named ``ocr_pdf``.
    """
    # Ensure the logs directory exists before any handler creation.
    if enable_file:
        _LOGS_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("ocr_pdf")
    logger.setLevel(level)

    # Avoid duplicate handlers on repeated calls (idempotent configuration).
    if logger.handlers:
        return logger

    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

    # Console handler — writes to stdout/stderr with color-agnostic output.
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Rotating file handler — captures all levels for audit trails.
    if enable_file:
        file_handler = RotatingFileHandler(
            _LOG_FILE,
            maxBytes=_MAX_BYTES,
            backupCount=_BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """Return a child logger under the ``ocr_pdf`` root namespace.

    Args:
        name: Sub-name for the logger (e.g. ``engine``, ``cli``).

    Returns:
        A named child logger inheriting the configured handlers.
    """
    return logging.getLogger(f"ocr_pdf.{name}")
