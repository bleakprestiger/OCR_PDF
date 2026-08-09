"""System health-check module for PDF OCR CLI.

Probes the host system for required binaries (Tesseract, Ghostscript),
verifies installed language packs, and validates the ocrmypdf Python package.
All path operations use pathlib; binary discovery uses shutil.which().
"""

from __future__ import annotations

import re
import shutil
import subprocess  # noqa: S404 — external tool version checks only.
import sys
from dataclasses import dataclass, field
from typing import Final

from .logging_config import get_logger

logger = get_logger("health")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_REQUIRED_BINARIES: Final[list[str]] = ["tesseract", "gs"]
_TESSERACT_LANG_RE: Final[re.Pattern[str]] = re.compile(
    r"^\s*(\S+)\s*$"
)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class BinaryStatus:
    """Result of a binary discovery check."""

    name: str
    found: bool
    path: str | None = None


@dataclass(frozen=True)
class LanguagePackStatus:
    """Result of a Tesseract language pack verification."""

    requested: list[str]
    installed: set[str]
    missing: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def check_binary(binary_name: str) -> BinaryStatus:
    """Check whether *binary_name* is discoverable on the system PATH.

    Uses :func:`shutil.which` for cross-platform binary discovery.

    Args:
        binary_name: The executable name to locate (e.g. ``tesseract``).

    Returns:
        A :class:`BinaryStatus` describing presence and resolved path.
    """
    resolved = shutil.which(binary_name)
    status = BinaryStatus(
        name=binary_name,
        found=resolved is not None,
        path=resolved,
    )
    if status.found:
        logger.debug("Binary '%s' found at %s", binary_name, resolved)
    else:
        logger.warning("Binary '%s' NOT found on PATH — required for OCR.", binary_name)
    return status


def check_system_dependencies() -> dict[str, BinaryStatus]:
    """Verify all required system binaries are available.

    Returns:
        Mapping of binary name → :class:`BinaryStatus` for every checked tool.

    Raises:
        SystemExit: If any required binary is missing (with actionable message).
    """
    results: dict[str, BinaryStatus] = {}
    missing: list[str] = []

    for binary in _REQUIRED_BINARIES:
        status = check_binary(binary)
        results[binary] = status
        if not status.found:
            missing.append(binary)

    if missing:
        logger.error(
            "Missing required binaries: %s. Please install them and ensure they are on PATH.",
            ", ".join(missing),
        )
        sys.exit(1)

    logger.info("All system binaries verified: %s", ", ".join(results))
    return results


def get_tesseract_languages() -> set[str]:
    """Query Tesseract for its installed language packs.

    Runs ``tesseract --list-langs`` and parses the output.

    Returns:
        A set of available language code strings (e.g. ``{'eng', 'deu', 'fra'}``).

    Raises:
        RuntimeError: If tesseract is not found or the command fails unexpectedly.
    """
    tesseract_path = shutil.which("tesseract")
    if tesseract_path is None:
        raise RuntimeError("Tesseract binary not found — cannot list language packs.")

    try:
        result = subprocess.run(  # noqa: S603 — controlled binary, already verified.
            [tesseract_path, "--list-langs"],
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("Tesseract executable disappeared between checks.") from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Tesseract --list-langs timed out after 15s.") from exc

    # tesseract writes language names to stderr, not stdout.
    output = result.stderr if result.stderr else result.stdout

    languages: set[str] = set()
    for line in output.strip().splitlines():
        match = _TESSERACT_LANG_RE.match(line)
        if match:
            languages.add(match.group(1).strip())

    logger.debug("Tesseract language packs discovered: %s", sorted(languages))
    return languages


def verify_language_packs(requested_langs: str) -> LanguagePackStatus:
    """Verify that all requested Tesseract language packs are installed.

    Parses the ``--lang`` string (e.g. ``eng+deu+fra``) into individual codes,
    then cross-references against the system's installed packs.

    Args:
        requested_langs: Plus-separated language code string (default ``eng``).

    Returns:
        A :class:`LanguagePackStatus` with missing languages listed.

    Raises:
        SystemExit: If any requested language pack is not installed.
    """
    installed = get_tesseract_languages()
    requested_list = [code.strip().lower() for code in requested_langs.split("+") if code.strip()]
    missing = [lang for lang in requested_list if lang not in installed]

    status = LanguagePackStatus(
        requested=requested_list,
        installed=installed,
        missing=missing,
    )

    if missing:
        logger.error(
            "Missing language pack(s): %s. Requested: %s. Installed: %s.",
            ", ".join(missing),
            ", ".join(requested_list),
            ", ".join(sorted(installed)),
        )
        sys.exit(1)

    logger.info("All requested language packs verified: %s", "+".join(requested_list))
    return status


def run_full_health_check(lang: str = "eng") -> None:
    """Execute the complete pre-flight health check.

    Verifies system binaries, Tesseract language availability, and optionally
    validates that the ocrmypdf Python package is importable.

    Args:
        lang: The ``--lang`` value to verify against installed packs.

    Raises:
        ImportError: If the ``ocrmypdf`` package is not available.
    """
    logger.info("Running full pre-flight health check…")

    # Step 1: Binary discovery.
    check_system_dependencies()

    # Step 2: Language pack verification.
    verify_language_packs(lang)

    # Step 3: Python package availability (soft check).
    try:
        import ocrmypdf  # noqa: F401
    except ImportError as exc:
        logger.error(
            "Python package 'ocrmypdf' is not installed. Run: pip install ocrmypdf",
        )
        raise ImportError("ocrmypdf package required but not found.") from exc

    logger.info("Pre-flight health check passed successfully.")
