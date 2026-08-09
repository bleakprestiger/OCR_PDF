"""Core OCR engine module for PDF processing.

Wraps the ``ocrmypdf`` library with pathlib-based path handling,
structured error isolation, and configurable concurrency parameters.
All file I/O uses :class:`pathlib.Path` exclusively — no raw string joins.
"""

from __future__ import annotations

import shutil
import subprocess  # noqa: S404 — controlled ocrmypdf binary invocation only.
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

from .logging_config import get_logger

logger = get_logger("engine")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_PDF_EXTENSION: Final[str] = ".pdf"
_OUTPUT_SUFFIX: Final[str] = "_searchable"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ProcessingResult:
    """Outcome of a single PDF OCR operation."""

    input_path: Path
    output_path: Path | None
    success: bool
    pages_processed: int = 0
    error_message: str | None = None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _is_pdf(file_path: Path) -> bool:
    """Determine whether *file_path* is a PDF by extension and magic bytes.

    Args:
        file_path: The candidate file path.

    Returns:
        True if the file has a ``.pdf`` extension AND starts with the PDF magic header.
    """
    if file_path.suffix.lower() != _PDF_EXTENSION:
        return False

    try:
        with open(file_path, "rb") as fh:
            header = fh.read(5)
            return header == b"%PDF-"
    except (OSError, IOError) as exc:
        logger.warning("Cannot read magic bytes for %s: %s", file_path, exc)
        return False


def _resolve_output_path(input_path: Path) -> Path:
    """Generate the output PDF path by inserting ``_searchable`` before the extension.

    Args:
        input_path: The original scanned PDF path.

    Returns:
        A new :class:`Path` pointing to the OCR output file.
    """
    stem = input_path.stem
    parent = input_path.parent
    return parent / f"{stem}{_OUTPUT_SUFFIX}{_PDF_EXTENSION}"


def _build_command(  # noqa: PLR0913 — explicit parameters for clarity and testability.
    input_path: Path,
    output_path: Path,
    lang: str,
    threads: int,
    skip_text: bool,
    redo_ocr: bool,
    force_ocr: bool,
) -> list[str]:
    """Construct the ocrmypdf CLI command as a list of arguments.

    Args:
        input_path: Source PDF path (must exist).
        output_path: Destination PDF path.
        lang: Plus-separated language codes for Tesseract.
        threads: Number of parallel threads to use.
        skip_text: Skip pages that already contain text.
        redo_ocr: Re-run OCR on pages with an existing text layer.
        force_ocr: Force OCR on all pages regardless of content.

    Returns:
        A list suitable for ``subprocess.run([...])``.
    """
    cmd = [
        sys.executable, "-m", "ocrmypdf",
        "--force-ocr" if force_ocr else "--skip-text" if skip_text else "--redo-ocr" if redo_ocr else None,
        "-l", lang,
        "-j", str(threads),
        str(input_path),
        str(output_path),
    ]
    # Filter out None entries from conditional flags.
    return [arg for arg in cmd if arg is not None]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def process_pdf(  # noqa: PLR0913 — explicit parameters for clarity and testability.
    input_path: Path,
    output_path: Path | None = None,
    lang: str = "eng",
    threads: int = 2,
    skip_text: bool = False,
    redo_ocr: bool = False,
    force_ocr: bool = False,
) -> ProcessingResult:
    """Run OCR on a single PDF file and return the processing result.

    Uses the ``ocrmypdf`` Python module API directly when available; falls back
    to subprocess invocation for robustness against wrapper inconsistencies.

    Args:
        input_path: Path to the source (unsearchable) PDF.
        output_path: Optional destination path. Defaults to ``<stem>_searchable.pdf``.
        lang: Plus-separated Tesseract language codes (e.g. ``eng+deu``).
        threads: Max parallel threads for OCR (capped at 8 internally).
        skip_text: Skip pages that already have text overlay.
        redo_ocr: Re-OCR pages with existing text layers.
        force_ocr: Force OCR on every page unconditionally.

    Returns:
        A :class:`ProcessingResult` describing success, output path, and metrics.
    """
    if not input_path.is_file():
        error_msg = f"Input file does not exist or is not a regular file: {input_path}"
        logger.error(error_msg)
        return ProcessingResult(
            input_path=input_path,
            output_path=None,
            success=False,
            error_message=error_msg,
        )

    if not _is_pdf(input_path):
        error_msg = f"Not a valid PDF file (missing %PDF- header): {input_path}"
        logger.warning(error_msg)
        return ProcessingResult(
            input_path=input_path,
            output_path=None,
            success=False,
            error_message=error_msg,
        )

    resolved_output = output_path or _resolve_output_path(input_path)

    # Cap threads to prevent OOM on large documents.
    capped_threads = min(max(threads, 1), 8)

    try:
        import ocrmypdf  # noqa: PLC0415 — lazy import for optional dependency.

        result = ocrmypdf.ocr(
            str(input_path),
            str(resolved_output),
            language=lang,
            threads=capped_threads,
            skip_text=skip_text,
            redo_ocr=redo_ocr,
            force_ocr=force_ocr,
            optimize=1,  # Minimal optimization to reduce processing time.
        )

        pages = result.pages.in_ if hasattr(result, "pages") and hasattr(result.pages, "in_") else 0

        logger.info(
            "OCR completed: %s → %s (%d pages)",
            input_path.name,
            resolved_output.name,
            pages,
        )

        return ProcessingResult(
            input_path=input_path,
            output_path=resolved_output,
            success=True,
            pages_processed=pages,
        )

    except ImportError:
        # Fallback to subprocess invocation of ocrmypdf CLI.
        logger.warning("ocrmypdf Python module unavailable — falling back to subprocess.")
        return _process_via_subprocess(
            input_path=input_path,
            output_path=resolved_output,
            lang=lang,
            threads=capped_threads,
            skip_text=skip_text,
            redo_ocr=redo_ocr,
            force_ocr=force_ocr,
        )

    except Exception as exc:  # noqa: BLE001 — catch-all for ocrmypdf runtime errors.
        error_msg = f"OCR failed on {input_path}: {exc}"
        logger.error(error_msg)
        return ProcessingResult(
            input_path=input_path,
            output_path=None,
            success=False,
            error_message=error_msg,
        )


def _process_via_subprocess(  # noqa: PLR0913 — mirrors process_pdf signature.
    input_path: Path,
    output_path: Path,
    lang: str,
    threads: int,
    skip_text: bool,
    redo_ocr: bool,
    force_ocr: bool,
) -> ProcessingResult:
    """Execute OCR via ``python -m ocrmypdf`` subprocess invocation.

    Args:
        input_path: Source PDF path.
        output_path: Destination PDF path.
        lang: Language codes string.
        threads: Thread count (capped).
        skip_text: Skip text pages flag.
        redo_ocr: Re-OCR existing text flag.
        force_ocr: Force OCR on all pages flag.

    Returns:
        A :class:`ProcessingResult` describing the outcome.
    """
    cmd = _build_command(
        input_path=input_path,
        output_path=output_path,
        lang=lang,
        threads=threads,
        skip_text=skip_text,
        redo_ocr=redo_ocr,
        force_ocr=force_ocr,
    )

    logger.info("Subprocess OCR command: %s", " ".join(cmd))

    try:
        result = subprocess.run(  # noqa: S603 — controlled binary via sys.executable.
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=600,  # 10-minute per-file timeout to handle large documents.
        )

        if result.returncode == 0:
            logger.info(
                "Subprocess OCR succeeded: %s → %s",
                input_path.name,
                output_path.name,
            )
            return ProcessingResult(
                input_path=input_path,
                output_path=output_path,
                success=True,
                pages_processed=0,  # Subprocess doesn't expose page count easily.
            )

        error_msg = f"ocrmypdf subprocess exited with code {result.returncode}: {result.stderr}"
        logger.error(error_msg)
        return ProcessingResult(
            input_path=input_path,
            output_path=None,
            success=False,
            error_message=error_msg,
        )

    except subprocess.TimeoutExpired as exc:
        error_msg = f"OCR timed out after 600s on {input_path}"
        logger.error(error_msg)
        return ProcessingResult(
            input_path=input_path,
            output_path=None,
            success=False,
            error_message=error_msg,
        )

    except Exception as exc:
        error_msg = f"Subprocess OCR failed on {input_path}: {exc}"
        logger.error(error_msg)
        return ProcessingResult(
            input_path=input_path,
            output_path=None,
            success=False,
            error_message=error_msg,
        )


def discover_pdfs(directory: Path) -> list[Path]:
    """Recursively discover all PDF files in *directory*.

    Filters by ``.pdf`` extension and validates the %PDF- magic header.

    Args:
        directory: Root directory to scan (must exist and be a directory).

    Returns:
        A sorted list of :class:`Path` objects pointing to valid PDFs.
    """
    if not directory.is_dir():
        logger.error("Discovery target is not a directory: %s", directory)
        return []

    pdf_files: list[Path] = []
    for candidate in sorted(directory.rglob("*")):
        if candidate.is_file() and _is_pdf(candidate):
            pdf_files.append(candidate)

    logger.info("Discovered %d valid PDF(s) in %s", len(pdf_files), directory)
    return pdf_files


def batch_process(  # noqa: PLR0913 — explicit parameters for clarity.
    pdf_paths: list[Path],
    lang: str = "eng",
    threads: int = 2,
    skip_text: bool = False,
    redo_ocr: bool = False,
    force_ocr: bool = False,
) -> list[ProcessingResult]:
    """Process a batch of PDF files sequentially with structured error isolation.

    Each file is processed independently — failures in one do not affect others.

    Args:
        pdf_paths: List of PDF paths to process.
        lang: Language codes for OCR.
        threads: Thread count per file.
        skip_text: Skip text pages flag.
        redo_ocr: Re-OCR existing text flag.
        force_ocr: Force OCR on all pages flag.

    Returns:
        A list of :class:`ProcessingResult` objects, one per input PDF.
    """
    results: list[ProcessingResult] = []

    for pdf_path in pdf_paths:
        result = process_pdf(
            input_path=pdf_path,
            lang=lang,
            threads=threads,
            skip_text=skip_text,
            redo_ocr=redo_ocr,
            force_ocr=force_ocr,
        )
        results.append(result)

    return results
