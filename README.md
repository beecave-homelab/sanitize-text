# sanitize-text | PII scrubbing for Dutch and English

sanitize-text detects and removes personally identifiable information (PII) from text and common document formats for Dutch (`nl_NL`) and English (`en_US`). It exposes a Click-based CLI, a Flask web UI, and a shared scrubbing core built on `scrubadub`, with detectors for email, phone numbers, URLs, IP addresses, names, organizations, locations, and optional NLP-backed entities.

## Badges

![Python](https://img.shields.io/badge/Python-3.10--3.12-blue)
![Version](https://img.shields.io/badge/version-1.0.0-brightgreen)
![License](https://img.shields.io/badge/license-MIT-yellow)

## Table of Contents

- [Why This Project?](#why-this-project)
- [Features](#features)
- [What's Included](#whats-included)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
  - [CLI](#cli)
  - [Web UI](#web-ui)
  - [Entity management](#entity-management)
  - [Binary and rich document input](#binary-and-rich-document-input)
- [Output Formats](#output-formats)
- [Development](#development)
- [Contributing](#contributing)
- [License](#license)

## Why This Project?

Handling real-world documents often means handling PII. sanitize-text provides a reproducible, configurable way to scrub PII from free text and common document formats while keeping the rest of the content intact. It is built for Dutch and English use cases, supports both command-line and web-based flows, and offers deterministic replacements so scrubbed output remains useful for analysis, sharing, or storage.

## Features

- **Multi-locale PII scrubbing** for Dutch (`nl_NL`) and English (`en_US`).
- **Configurable detector catalogue** including email, phone, URLs, IP addresses, names, organizations, locations, `date_of_birth`, and optional spaCy-based entities.
- **CLI pipeline** for scrubbing inline text, files, or stdin with append mode and rich output formats (TXT, Markdown, DOCX, PDF).
- **Web UI** for interactive scrubbing, detector selection, locale toggles, verbose inspection, and file upload/download.
- **Entity management tool** for extending Dutch city, name, and organization lists.
- **Binary/rich document support** with pre-conversion for PDF, DOC/DOCX, RTF, and images.
- **Layout-aware PDF export** and cleanup helpers to reduce placeholders and gibberish.

## What's Included

The main modules are:

- `sanitize_text/core/`: Scrubbing orchestration, detector catalogue, and helper APIs.
- `sanitize_text/cli/`: Click-based CLI entrypoint and I/O helpers.
- `sanitize_text/webui/`: Flask application, routes, templates, and static assets.
- `sanitize_text/add_entity/`: Utilities for updating Dutch entity lists on disk.
- `sanitize_text/utils/`: Normalization, cleanup, pre-conversion, and related helpers.
- `scripts/`: Helper scripts for NLP/NER experiments (spaCy training, entity extraction).
- `tests/`: Pytest-based test suite covering CLI, Web UI, scrubber, detectors, and output.

## Installation

### Requirements

- **Python**: 3.10–3.12 (`requires-python = ">=3.10,<3.13"` in `pyproject.toml`).
- **OS**: Developed on macOS, expected to work on Linux. Windows may work but is not explicitly tested.
- **Storage**:
  - Base installation is under ~100 MB and runs entirely on CPU.
  - Optional NLP resources (spaCy models, NLTK corpora) require additional space.

### Install with pipx

From a cloned checkout, you can install sanitize-text into an isolated pipx environment:

```bash
git clone https://github.com/beecave-homelab/sanitize-text.git
cd sanitize-text
pipx install .
```

This makes the `sanitize-text` and `sanitize-text-webui` commands available on your PATH while keeping dependencies isolated.

### Install locally (virtualenv + pip)

1. Clone the repository and create a virtual environment:

   ```bash
   git clone https://github.com/beecave-homelab/sanitize-text.git
   cd sanitize-text
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install runtime dependencies from `requirements.txt`:

   ```bash
   pip install -U pip
   pip install -r requirements.txt
   ```

After installation, the `sanitize-text` and `sanitize-text-webui` console scripts are available inside the virtual environment.

### Install with PDM

If you use [PDM](https://pdm.fming.dev/), you can manage the environment and dependencies via `pyproject.toml`:

```bash
git clone https://github.com/beecave-homelab/sanitize-text.git
cd sanitize-text
pdm install
```

This installs the project and its runtime dependencies into a PDM-managed environment. For development-specific usage (linting, tests, etc.), see `project-overview.md`.

### Run with Docker (Web UI)

To run the Web UI in a container without managing Python environments locally:

```bash
docker compose up
```

This builds the image from the provided `Dockerfile` and starts Gunicorn on `http://localhost:8000`.

For a development Web UI with live reload mounted from your working tree:

```bash
docker compose -f docker-compose.dev.yaml up
```

This runs `flask run --reload` in a container, also exposed on `http://localhost:8000`.

## Configuration

### CLI configuration

Key options that control how scrubbing behaves:

- `--locale / -l`: Locale code (`nl_NL` or `en_US`). When omitted, the core can process both locales.
- `--detectors / -d`: Space-separated detector names (for example `"email url name"`).
- `--custom / -c`: Custom text fragment that should always be treated as PII.
- `--cleanup/--no-cleanup`: Enable or disable final cleanup and normalization.
- `--download-nlp-models`: Download optional NLTK corpora and spaCy small models before running (requires network access).

### Environment variables

The CLI does not require environment variables. The Web UI uses the usual Flask variables, which are already set in the Docker Compose files:

- `FLASK_APP=sanitize_text.webui:create_app`
- `FLASK_ENV=production` (or `development` in `docker-compose.dev.yaml`)
- `FLASK_DEBUG=1` in development mode
- `PYTHONUNBUFFERED=1` for unbuffered logging

When running the Web UI directly via `sanitize-text-webui` or `pdm run sanitize_text.webui`, these values are configured programmatically.

## Usage

### CLI

Once installed (via PDM or pip), the main entry point is the `sanitize-text` console script. From a PDM-managed environment you can prefix commands with `pdm run`:

```bash
# Process inline text
sanitize-text -t "John lives in Amsterdam" -l nl_NL

# Process from a file
sanitize-text -i input.txt -o output.txt

# List available detectors
sanitize-text list-detectors

# Use specific detectors only
sanitize-text -i input.txt -d "email url name"

# Append to existing output
sanitize-text -i input.txt -o output.txt -a
```

Common options:

- `-t, --text`: Inline input text.
- `-i, --input`: Path to an input file to scrub.
- `-o, --output`: Output path (defaults to `$PWD/output/scrubbed.txt`).
- `-l, --locale`: Locale (`nl_NL` or `en_US`).
- `-d, --detectors`: Space-separated detector names.
- `-a, --append`: Append to an existing output file instead of overwriting.
- `--output-format`: Explicit format (`txt`, `md`, `docx`, `pdf`).
- `--pdf-backend`: Backend for PDF pre-conversion (`pymupdf4llm` or `markitdown`).
- `--pdf-mode`, `--pdf-font`, `--font-size`: PDF layout and typography options.
- `--cleanup/--no-cleanup`: Toggle cleanup pipeline.
- `--download-nlp-models`: Download optional NLP resources before running.

Run `sanitize-text --help` for the complete, up-to-date CLI reference.

### Web UI

The Web UI offers an interactive way to scrub text and files.

Development server from the project tree:

```bash
sanitize-text-webui
```

This starts a Flask server (via `sanitize_text.webui.main`) on `http://localhost:5000`.

Containerized Web UI:

```bash
# Production-like Web UI on http://localhost:8000
docker compose up

# Development Web UI with live reload on http://localhost:8000
docker compose -f docker-compose.dev.yaml up
```

The Web UI supports:

- Pasting or typing raw text to scrub.
- Uploading documents (PDF, DOC/DOCX, RTF, images) for conversion and scrubbing.
- Selecting locale and detectors.
- Enabling/disabling cleanup.
- Downloading scrubbed output in various formats.

### Entity management

For Dutch (`nl_NL`) use cases you can extend the built-in entity lists using the `sanitize_text.add_entity` PDM script:

```bash
# Add a new city
pdm run sanitize_text.add_entity -c "Amsterdam"

# Add a new name
pdm run sanitize_text.add_entity -n "John Smith"

# Add a new organization
pdm run sanitize_text.add_entity -o "Example B.V."

# Add multiple entities at once
pdm run sanitize_text.add_entity -c "Amsterdam" -n "John Smith" -o "Example B.V."
```

Options:

- `-c, --city`: Add a new city.
- `-n, --name`: Add a new person name.
- `-o, --organization`: Add a new organization.

### Binary and rich document input

Binary or rich formats (PDF, DOC/DOCX, RTF, images) can be passed directly to the CLI via `-i/--input`. The tool uses its own pre-conversion pipeline to extract text (for example from PDFs and images) before scrubbing.

You can also pre-convert documents yourself and pipe text into the CLI when that gives better results on your system:

```bash
# PDF -> text (requires pdftotext from poppler)
pdftotext input.pdf - | sanitize-text

# DOCX -> text (docx2txt)
docx2txt input.docx - | sanitize-text

# RTF -> text (pandoc)
pandoc input.rtf -t plain | sanitize-text

# Image -> text via OCR (tesseract)
tesseract image.png stdout | sanitize-text
```

## Output Formats

The CLI can write scrubbed output in several formats:

- **TXT** (default): Plain text files.
- **Markdown (MD)**: When `--output-format md` is used or the output path ends in `.md`.
- **DOCX**: When `--output-format docx` is used or the output path ends in `.docx`.
- **PDF**: When `--output-format pdf` is used or the output path ends in `.pdf`.

If `--output` is omitted, the tool writes to `./output/scrubbed.txt` in the current working directory.

PDF-specific options (`--pdf-mode`, `--pdf-font`, `--font-size`) control layout and typography and are forwarded to the internal PDF writer.

## Development

For development setup, linting/formatting, test workflows, and architecture details, see:

- `project-overview.md` – overall structure, CLI/WebUI flows, Docker usage, and test layout.
- `AGENTS.md` – coding standards, Ruff configuration, and testing/coverage expectations.

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss the proposal and how it fits with the existing CLI, Web UI, and scrubbing APIs.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
