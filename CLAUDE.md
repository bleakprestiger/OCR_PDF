# CLAUDE.md — Cross-Platform Production-Grade PDF OCR CLI Guidelines

## 🔴 CRITICAL: STATE-TRACKING & TOOL-USE RULES
* **Absolute Path Restriction**: NEVER use absolute system paths (e.g., `C:/...` or `/Users/...`). ALWAYS use exact relative paths (e.g., `src/main.py`) for all tool configurations to avoid breaking Windows/WSL/Linux state tracking.
* **Strict Read-Before-Write Execution**: You MUST explicitly call the `Read` tool on a file using its exact relative path before running any `Edit` or `Write` tool on it. No exceptions.
* **State Error Fatal Fallback**: If any file modification fails with the message `"File has not been read yet"`, immediately abort using the native `Write`/`Edit` tools. Fallback directly to using a standard Bash command with a clean heredoc to overwrite the file content:
  ```bash
  cat << 'EOF' > path/to/file.py
  # Refined file contents go here
  EOF
  ```

---
# Role & Persona
> Act as Elite Software Architect: Think step-by-step; apply these strict constraints only to final file modifications: output ONLY non-destructive, fully implemented, no-TODO, strictly-typed code enforcing strictly localized zero-trust data validation, secure cryptography, error-masking, idempotency, SOLID, robust errors, and optimal Big-O targeting root causes while matching repo patterns and preserving working logic without breaking existing behavior; zero chat text or markdown explanations outside raw code.

## 🎯 Project Vision & Architecture

Build a fast, highly robust, operating-system-agnostic Python CLI utility that discovers unsearchable/scanned PDFs in a directory and transforms them into standard-compliant, fully text-searchable (OCR) PDF files.

### Cross-Platform & OS-Agnostic Strictures
* **Path Resilience**: Use Python's `pathlib.Path` exclusively for all file system, directory scanning, and path manipulations. Never use raw string path concats or hardcoded forward/backward slashes (`/` or `\`).
* **Binary Discovery**: Dynamically look for system dependencies using `shutil.which()` to find external tools like `tesseract` and `ghostscript` gracefully regardless of platform environment setups.

### Technical Stack & Constraints
* **Language/Platform**: Python 3.10+
* **OCR Core Engine**: `ocrmypdf` (Python wrapper utilizing Tesseract OCR engine, Ghostscript, and Leptonica optimization layers).
* **CLI Framework**: `click` (for modular command/argument structures, clear type validations, and cross-platform compatible terminal styling).
* **Progress Visualization**: `tqdm` (thread-safe, cross-platform progress bars indicating batch completion metrics).
* **Code Styling**: Strict PEP 8 compliance, structural type-hinting throughout (`typing` module), and explicit error isolation boundaries.

---

## 🌍 Language-Agnostic & Advanced Enterprise Features
To make this project completely language-independent and safe for real-world deployment, adhere to these implementation rules:

### 1. Robust System & Language Pack Probing
* Prior to processing, the tool must execute a health check via system shell commands to query the underlying Tesseract engine (`tesseract --list-langs`).
* Match the user-supplied `--lang` flag against the host system's installed language packs.
* If a language pack is missing (e.g., user asks for `deu` but only `eng` is installed), block execution safely with a clean, actionable error message detailing how to install the required system assets.

### 2. Multi-Language CLI Parsing
* Accept a flexible `--lang` / `-l` string parameter. Default to `eng`, but natively support combination codes (e.g., `eng+deu+fra`) to facilitate OCR on multi-lingual records.

### 3. Fail-Safe Mutations & Edge-Case Configurations
* **Idempotence & Safety**: Never modify the input file in place by default. Write out to a clear destination pattern (e.g., `<original_name>_searchable.pdf`).
* **Existing Text Handling**: Pass appropriate downstream engine directives (e.g., `--skip-text` or `--redo-ocr`) to handle files that may contain mixed formats or corrupted text layers without failing the application pipeline.
* **Large File & Concurrency Boundaries**: Leverage multi-core pooling where safe. Limit batch concurrency parameters gracefully to prevent memory starvation out-of-bounds (OOM) on large scanned blueprints or multi-hundred-page books.

### 4. Zero-Leak Structured Logging
* Replace raw terminal tracebacks with a dedicated `logging` module configuration. 
* Log standard operation markers to `stdout` / `stderr` via the CLI console, and write detailed trace, performance metrics, and engine warnings to a rotating `.log` file in a dedicated `logs/` directory.

---

## 🛠️ Infrastructure Setup Command Templates
Utilize the following setups during early automation phases:
* **Host System Requirements (macOS)**: `brew install tesseract ocrmypdf`
* **Host System Requirements (Ubuntu/Debian)**: `sudo apt-get update && sudo apt-get install -y tesseract-ocr ocrmypdf ghostscript`
* **Host System Requirements (Windows)**: Install `Tesseract OCR` and `Ghostscript` via `choco install tesseract ghostscript` or official installers, ensuring binaries are added to the system `PATH`.
* **Python Environment Setup**: Initialize a virtual environment (`python -m venv .venv`).
* **Python Dependencies**: `pip install ocrmypdf click tqdm`

---

## 📜 Version Control System (VCS) & Git Workflow
All infrastructure and application code must be tracked atomically with incremental semantic commits. Do not bundle features. 
1. **Bootstrap Repository**: Run `git init` immediately upon reading these rules.
2. **Gitignore Safety**: Immediately create a cross-platform `.gitignore` capturing `.venv/`, `venv/`, `__pycache__/`, `.DS_Store`, `Thumbs.db`, logs, and temporary sandbox PDFs before tracking source files.
3. **Conventional Commits Protocol**: Follow strict structural naming conventions:
   * `feat: initialize repository architecture, cross-platform .gitignore, and virtual environment`
   * `feat: build robust OS-agnostic health-check module for tesseract language verification`
   * `feat: implement core pathlib-based agnostic execution engine wrapper`
   * `feat: craft click CLI interface with batch validation logic and tqdm progress bars`
   * `feat: add robust file logging framework and out-of-bounds safety limits`
   * `docs: add comprehensive README with deployment and multi-language usage examples`
