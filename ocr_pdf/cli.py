"""Click-based CLI interface for the PDF OCR tool.

Provides modular command/argument structures, cross-platform terminal styling,
and tqdm progress bars for batch operations. All path handling uses pathlib.Path.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Final

import click
from tqdm import tqdm

from . import __version__
from .engine import ProcessingResult, batch_process, discover_pdfs, process_pdf
from .health import run_full_health_check
from .logging_config import configure_logging, get_logger

logger = get_logger("cli")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_DEFAULT_LANG: Final[str] = "eng"
_DEFAULT_THREADS: Final[int] = 2
_MAX_THREADS: Final[int] = 8


# ---------------------------------------------------------------------------
# CLI Group
# ---------------------------------------------------------------------------
@click.group()
@click.version_option(version=__version__, prog_name="ocr-pdf", package_name="ocr_pdf")
@click.option(
    "--verbose", "-v",
    is_flag=True,
    default=False,
    help="Enable DEBUG-level console logging.",
)
@click.pass_context
def cli(ctx: click.Context, verbose: bool) -> None:  # noqa: ARG001 — required by Click.
    """PDF OCR CLI — Transform unsearchable/scanned PDFs into text-searchable files."""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose

    level = "DEBUG" if verbose else "INFO"
    configure_logging(level=getattr(__import__("logging"), level))
    logger.debug("CLI session started (verbose=%s)", verbose)


# ---------------------------------------------------------------------------
# Command: ocr
# ---------------------------------------------------------------------------
@cli.command()
@click.argument(
    "input_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option(
    "--output", "-o",
    type=click.Path(path_type=Path),
    default=None,
    help="Output PDF path. Defaults to <original>_searchable.pdf in the same directory.",
)
@click.option(
    "--lang", "-l",
    type=str,
    default=_DEFAULT_LANG,
    help="Tesseract language code(s), plus-separated (e.g. eng+deu). Default: eng.",
)
@click.option(
    "--threads", "-j",
    type=click.IntRange(1, _MAX_THREADS),
    default=_DEFAULT_THREADS,
    help=f"Parallel threads per file (1-{_MAX_THREADS}). Default: {_DEFAULT_THREADS}.",
)
@click.option(
    "--skip-text",
    is_flag=True,
    default=False,
    help="Skip pages that already contain text.",
)
@click.option(
    "--redo-ocr",
    is_flag=True,
    default=False,
    help="Re-run OCR on pages with an existing text layer.",
)
@click.option(
    "--force-ocr",
    is_flag=True,
    default=False,
    help="Force OCR on every page regardless of content.",
)
@click.pass_context
def ocr(
    ctx: click.Context,
    input_path: Path,
    output: Path | None,
    lang: str,
    threads: int,
    skip_text: bool,
    redo_ocr: bool,
    force_ocr: bool,
) -> None:
    """Run OCR on a single PDF file.

    INPUT_PATH is the path to the unsearchable/scanned PDF to process.
    """
    logger.info("Single-file OCR: %s", input_path)

    # Pre-flight health check for this file's language requirements.
    run_full_health_check(lang=lang)

    result = process_pdf(
        input_path=input_path,
        output_path=output,
        lang=lang,
        threads=threads,
        skip_text=skip_text,
        redo_ocr=redo_ocr,
        force_ocr=force_ocr,
    )

    if result.success:
        click.echo(
            click.style(f"✓ Success: {result.input_path.name} → {result.output_path.name}", fg="green"),
        )
        if result.pages_processed > 0:
            click.echo(click.style(f"  Pages processed: {result.pages_processed}", fg="green"))
    else:
        click.echo(
            click.style(f"✗ Failed: {result.input_path.name} — {result.error_message}", fg="red"),
            err=True,
        )
        ctx.exit(1)


# ---------------------------------------------------------------------------
# Command: scan
# ---------------------------------------------------------------------------
@cli.command(name="scan")
@click.argument(
    "directory",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
)
@click.option(
    "--lang", "-l",
    type=str,
    default=_DEFAULT_LANG,
    help="Tesseract language code(s). Default: eng.",
)
@click.option(
    "--threads", "-j",
    type=click.IntRange(1, _MAX_THREADS),
    default=_DEFAULT_THREADS,
    help=f"Parallel threads per file (1-{_MAX_THREADS}). Default: {_DEFAULT_THREADS}.",
)
@click.option(
    "--skip-text",
    is_flag=True,
    default=False,
    help="Skip pages that already contain text.",
)
@click.option(
    "--redo-ocr",
    is_flag=True,
    default=False,
    help="Re-run OCR on pages with an existing text layer.",
)
@click.option(
    "--force-ocr",
    is_flag=True,
    default=False,
    help="Force OCR on every page regardless of content.",
)
@click.pass_context
def scan(
    ctx: click.Context,
    directory: Path,
    lang: str,
    threads: int,
    skip_text: bool,
    redo_ocr: bool,
    force_ocr: bool,
) -> None:
    """Discover and OCR all PDFs in a directory tree.

    DIRECTORY is the root path to recursively scan for unsearchable PDF files.
    """
    logger.info("Batch scan started on directory: %s", directory)

    # Pre-flight health check.
    run_full_health_check(lang=lang)

    # Discover valid PDFs.
    pdf_files = discover_pdfs(directory)

    if not pdf_files:
        click.echo(click.style(f"No valid PDF files found in {directory}", fg="yellow"))
        return

    total = len(pdf_files)
    click.echo(click.style(f"Found {total} PDF file(s) in {directory}", fg="cyan"))

    # Process with tqdm progress bar.
    results: list[ProcessingResult] = []

    for pdf_path in tqdm(
        pdf_files,
        desc="OCR Progress",
        unit="file",
        total=total,
        ncols=80,
    ):
        result = process_pdf(
            input_path=pdf_path,
            lang=lang,
            threads=threads,
            skip_text=skip_text,
            redo_ocr=redo_ocr,
            force_ocr=force_ocr,
        )
        results.append(result)

    # Summary report.
    _print_summary(results)


# ---------------------------------------------------------------------------
# Command: check
# ---------------------------------------------------------------------------
@cli.command()
@click.option(
    "--lang", "-l",
    type=str,
    default=_DEFAULT_LANG,
    help="Language code(s) to verify against installed packs.",
)
def check(lang: str) -> None:
    """Run a pre-flight health check on system dependencies.

    Verifies Tesseract, Ghostscript binaries and requested language pack availability.
    """
    click.echo(click.style("Running pre-flight health check…", fg="cyan"))

    try:
        run_full_health_check(lang=lang)
        click.echo(click.style("✓ All checks passed.", fg="green"))
    except SystemExit as exc:
        # Health check calls sys.exit on failure — surface the message.
        raise click.exceptions.Exit(exc.code) from exc
    except ImportError as exc:
        click.echo(click.style(f"✗ {exc}", fg="red"), err=True)
        raise click.exceptions.Exit(1) from exc


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _print_summary(results: list[ProcessingResult]) -> None:
    """Print a batch processing summary to the console.

    Args:
        results: List of ProcessingResult objects from batch execution.
    """
    total = len(results)
    success_count = sum(1 for r in results if r.success)
    failure_count = total - success_count

    click.echo()
    click.echo(click.style("─── Batch Summary ───", fg="cyan"))
    click.echo(click.style(f"  Total files:   {total}", fg="white"))
    click.echo(click.style(f"  Succeeded:     {success_count}", fg="green"))
    if failure_count > 0:
        click.echo(click.style(f"  Failed:        {failure_count}", fg="red"))

    # List failed files with reasons.
    failures = [r for r in results if not r.success]
    if failures:
        click.echo()
        for fail in failures:
            reason = fail.error_message or "Unknown error"
            click.echo(click.style(f"  ✗ {fail.input_path.name}: {reason}", fg="red"))

    # Aggregate page count.
    total_pages = sum(r.pages_processed for r in results if r.success)
    if total_pages > 0:
        click.echo(click.style(f"  Total pages:   {total_pages}", fg="white"))

    click.echo()

    if failure_count == total:
        raise SystemExit(1)
