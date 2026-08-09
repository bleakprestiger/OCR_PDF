# PDF OCR CLI

Cross-platform command-line utility that discovers unsearchable/scanned PDFs in a directory and transforms them into standard-compliant, fully text-searchable (OCR) PDF files.

## Features

- **OS-Agnostic**: Works on Windows, macOS, and Linux via `pathlib` and `shutil.which()`
- **Multi-Language**: Supports single and combined Tesseract language packs (`eng`, `eng+deu+fra`, etc.)
- **Batch Processing**: Recursively scan directories with tqdm progress bars
- **Idempotent**: Never modifies input files — outputs `<original>_searchable.pdf`
- **Robust Logging**: Structured console + rotating file logs in `logs/ocr_pdf.log`
- **Health Checks**: Pre-flight verification of system binaries and language packs

## Installation

### System Dependencies

**macOS:**
```bash
brew install tesseract ocrmypdf ghostscript
```

**Ubuntu/Debian:**
```bash
sudo apt-get update && sudo apt-get install -y tesseract-ocr ocrmypdf ghostscript
```

**Windows:**
```powershell
choco install tesseract ghostscript
# Ensure binaries are added to system PATH
```

### Python Environment

```bash
python -m venv .venv
source .venv/bin/activate        # macOS/Linux
.venv\Scripts\activate           # Windows
pip install -e ".[dev]"
```

## Usage

### Pre-flight Health Check

Verify system dependencies before processing:

```bash
ocr-pdf check
ocr-pdf check --lang eng+deu
```

### Single File OCR

```bash
# Basic English OCR
ocr-pdf ocr scanned_document.pdf

# Custom output path
ocr-pdf ocr scanned_document.pdf -o output_searchable.pdf

# Multi-language (English + German)
ocr-pdf ocr scanned_document.pdf -l eng+deu

# Custom thread count
ocr-pdf ocr scanned_document.pdf -j 4
```

### Batch Directory Scan

```bash
# Recursively find and OCR all PDFs in a directory
ocr-pdf scan /path/to/documents

# Multi-language batch processing
ocr-pdf scan ./scans -l eng+jpn+kor -j 2
```

### Advanced Options

| Flag | Description |
|------|-------------|
| `--skip-text` | Skip pages that already contain text |
| `--redo-ocr` | Re-run OCR on pages with existing text layers |
| `--force-ocr` | Force OCR on every page regardless of content |
| `-v, --verbose` | Enable DEBUG-level logging |

## Architecture

```
ocr_pdf/
├── __init__.py          # Package metadata
├── __main__.py          # Entry point (python -m ocr_pdf)
├── cli.py               # Click CLI interface with tqdm progress bars
├── engine.py            # Core OCR engine wrapper (pathlib-based)
├── health.py            # System dependency & language pack probing
└── logging_config.py    # Structured rotating-file + console logging
```

## License

MIT
