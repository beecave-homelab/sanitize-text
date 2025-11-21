---
repo: https://github.com/beecave-homelab/sanitize-text
commit: c30ca71ce7ebad61e178de8f7b2c020b83b9bf21
generated: 2025-11-21T12:43:00+01:00
---
<!-- SECTIONS:API,CLI,WEBUI,CI,DOCKER,TESTS -->

# Project Overview | sanitize-text

sanitize-text detects and removes personally identifiable information (PII) from text and common document formats for Dutch (`nl_NL`) and English (`en_US`), via a shared scrubbing core, a Click-based CLI, and a Flask web UI.

[![Language](mdc:https:/img.shields.io/badge/Python-3.10--3.12-blue)](https://www.python.org/)
[![Version](mdc:https:/img.shields.io/badge/Version-1.0.0-brightgreen)](#version-summary)
[![License](mdc:https:/img.shields.io/badge/License-MIT-yellow)](LICENSE)

## Table of Contents

- [Quickstart for Developers](mdc:#quickstart-for-developers)
- [Version Summary](mdc:#version-summary)
- [Project Features](mdc:#project-features)
- [Project Structure](mdc:#project-structure)
- [Architecture Highlights](mdc:#architecture-highlights)
- [API](mdc:#api)
- [CLI](mdc:#cli)
- [WebUI](mdc:#webui)
- [Docker](mdc:#docker)
- [Tests](mdc:#tests)
- [CI/CD](mdc:#cicd)

## Quickstart for Developers

```bash
git clone https://github.com/beecave-homelab/sanitize-text.git
cd sanitize-text
python3.11 -m venv .venv && source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
pdm install  # optional, if you use PDM locally
pdm run ruff check .
pdm run pytest -q
```

## Version Summary

| Version | Date | Type | Key Changes |
|---------|------|------|-------------|
| 1.0.0 | 21-11-2025 | ✨ | WebUI redesign, new CLI/web UI entry points, multi-format document support, and improved PDF/Markdown flows. |
| 0.1.0 | N/A | 🔧 | Initial packaged version before WebUI and CLI enhancements. |

## Project Features

- **Multi-locale PII scrubbing** for Dutch (`nl_NL`) and English (`en_US`) via a shared detector catalogue.
- **Configurable detectors** (email, phone, URL, IPs, names, organizations, locations, `date_of_birth`, optional spaCy entities).
- **CLI workflow** for streaming text, files, stdin, and append mode with rich output formats (txt/md/docx/pdf).
- **Web UI** for interactive scrubbing, detector selection, CLI command preview, and file upload/download.
- **Entity management tool** to extend Dutch city/name/organization lists stored under [`sanitize_text/data/nl_entities`](https://github.com/beecave-homelab/sanitize-text/blob/c30ca71ce7ebad61e178de8f7b2c020b83b9bf21/sanitize_text/data/nl_entities).
- **Binary/rich document support** via pre-conversion utilities for PDF, DOC/DOCX, RTF, and image OCR.
- **Export pipeline** to TXT/DOCX/PDF with layout-aware PDF rendering and cleanup of placeholders/gibberish.
- **Test suite** covering CLI, WebUI, core scrubber, detectors, normalization, and output writers.

## Project Structure

<details><summary>Show tree</summary>

```text
sanitize_text/                # Library and application package
  cli/                        # Click-based CLI entrypoints and IO helpers
  core/                       # Scrubber orchestration and detector catalogue
  webui/                      # Flask app factory, routes, templates, static assets
  utils/                      # Pre-conversion, cleanup, NLP resources, PDF helpers, post-processors
  add_entity/                 # CLI to extend Dutch entity JSON lists
  data/                       # Locale-specific entity data (nl_entities/, en_entities/)
scripts/                      # Helper scripts for conversion and data extraction
tests/                        # Pytest suite for core, CLI, WebUI, utils, outputs
```

</details>

## Architecture Highlights

- **Layered design**: core scrubbing engine in [`sanitize_text/core/scrubber.py`](https://github.com/beecave-homelab/sanitize-text/blob/c30ca71ce7ebad61e178de8f7b2c020b83b9bf21/sanitize_text/core/scrubber.py).
- **Detector catalogue**: detectors declared via `DetectorSpec`/`DetectorContext` dataclasses with locale-aware enabling.
- **UI frontends**: CLI in [`sanitize_text/cli/main.py`](https://github.com/beecave-homelab/sanitize-text/blob/c30ca71ce7ebad61e178de8f7b2c020b83b9bf21/sanitize_text/cli/main.py) and Flask WebUI in [`sanitize_text/webui`](https://github.com/beecave-homelab/sanitize-text/blob/c30ca71ce7ebad61e178de8f7b2c020b83b9bf21/sanitize_text/webui) share the same scrubber and output writers.
- **Conversion + output layer**: [`sanitize_text/utils/preconvert.py`](https://github.com/beecave-homelab/sanitize-text/blob/c30ca71ce7ebad61e178de8f7b2c020b83b9bf21/sanitize_text/utils/preconvert.py) and [`sanitize_text/output.py`](https://github.com/beecave-homelab/sanitize-text/blob/c30ca71ce7ebad61e178de8f7b2c020b83b9bf21/sanitize_text/output.py) isolate binary/rich-document handling and artifact writing.
- **Cleanup + post-processing**: [`sanitize_text/utils/cleanup.py`](https://github.com/beecave-homelab/sanitize-text/blob/c30ca71ce7ebad61e178de8f7b2c020b83b9bf21/sanitize_text/utils/cleanup.py) and post-processors normalize output text and apply hashed PII replacements.
- **Data & detectors**: locale-specific entity JSON under [`sanitize_text/data`](https://github.com/beecave-homelab/sanitize-text/blob/c30ca71ce7ebad61e178de8f7b2c020b83b9bf21/sanitize_text/data) and custom detectors in [`sanitize_text/utils/custom_detectors`](https://github.com/beecave-homelab/sanitize-text/blob/c30ca71ce7ebad61e178de8f7b2c020b83b9bf21/sanitize_text/utils/custom_detectors).
- **Scrubber orchestration** builds `scrubadub.Scrubber` per locale via `setup_scrubber()`, selecting enabled detectors, attaching `HashedPIIReplacer`, and exposing `scrub_text()` / `collect_filth()`.
- **CLI flow** reads input (`--text`/`--input`/stdin/append), routes it through `_run_scrub()`, applies generic cleanup, and uses `output.get_writer()` for TXT/MD/DOCX/PDF artifacts.
- **WebUI flow** mirrors CLI semantics: routes in [`sanitize_text/webui/routes.py`](https://github.com/beecave-homelab/sanitize-text/blob/c30ca71ce7ebad61e178de8f7b2c020b83b9bf21/sanitize_text/webui/routes.py) scrub text or uploaded files, enrich responses with filth metadata, and stream downloadable artifacts.
- **Pre-conversion** uses [`sanitize_text/utils/preconvert.py`](https://github.com/beecave-homelab/sanitize-text/blob/c30ca71ce7ebad61e178de8f7b2c020b83b9bf21/sanitize_text/utils/preconvert.py) and, optionally, `markitdown`/`pymupdf4llm` and `tesseract` to normalize PDFs, Office docs, RTF, and images into text.
- **Locale handling**: both CLI and WebUI can process `en_US`, `nl_NL`, or both; when no locale is specified, both are run, with results combined and failures reported per locale.
- **Deployment**: Docker + Gunicorn run `sanitize_text.webui:create_app()` in production; [`docker-compose.dev.yaml`](https://github.com/beecave-homelab/sanitize-text/blob/c30ca71ce7ebad61e178de8f7b2c020b83b9bf21/docker-compose.dev.yaml) wires live-reload Flask with source mounts for developers.

## Flow Diagrams

```mermaid
flowchart LR
  subgraph CLI
    A[User] --> B[sanitize-text CLI]
    B --> C[read_input_source / preconvert]
    C --> D[core.scrubber.scrub_text]
    D --> E[cleanup_output]
    E --> F[output.get_writer -> file or stdout]
  end

  subgraph WebUI
    A2[Browser] --> B2[Flask routes: /process and /process-file]
    B2 --> C2[_read_uploaded_file_to_text / preconvert]
    C2 --> D2[setup_scrubber + scrubber.clean]
    D2 --> E2[cleanup_output]
    E2 --> F2[JSON response or downloadable file]
  end
```

## API

- **Framework**: Flask app created by [`sanitize_text/webui/run.py`](https://github.com/beecave-homelab/sanitize-text/blob/c30ca71ce7ebad61e178de8f7b2c020b83b9bf21/sanitize_text/webui/run.py) and wired in [`sanitize_text/webui/routes.py`](https://github.com/beecave-homelab/sanitize-text/blob/c30ca71ce7ebad61e178de8f7b2c020b83b9bf21/sanitize_text/webui/routes.py).
- **HTML root**: `GET /` renders `templates/index.html` with detector catalogues and spaCy availability flags.
- **JSON text API**: `POST /process` accepts JSON `{text, locale?, detectors?, custom?, cleanup?, verbose?}` and returns per-locale scrubbed text plus optional filth metadata.
- **JSON file API**: `POST /process-file` (`multipart/form-data`) uploads a document, converts it to text, and returns scrubbed text per locale.
- **Export endpoints**: `POST /export` and `POST /download-file` generate downloadable TXT/DOCX/PDF artifacts via `output.get_writer()`.
- **CLI helper**: `POST /cli-preview` returns a `sanitize-text` command string matching the current WebUI options.
- These endpoints are primarily consumed by the bundled WebUI but can also be scripted against as a lightweight HTTP API.

## CLI

- **Entry point**: [`sanitize_text/cli/main.py`](https://github.com/beecave-homelab/sanitize-text/blob/c30ca71ce7ebad61e178de8f7b2c020b83b9bf21/sanitize_text/cli/main.py) is exposed as the `sanitize-text` console script in [`pyproject.toml`](https://github.com/beecave-homelab/sanitize-text/blob/c30ca71ce7ebad61e178de8f7b2c020b83b9bf21/pyproject.toml).
- **Commands**: a top-level Click group provides the default scrub flow plus `list-detectors` and `scrub` subcommands.
- **Input sources**: `--text`, `--input`, `--append` (reuse output as input), or stdin; PDF pre-conversion backend selectable via `--pdf-backend`.
- **Locale & detectors**: `--locale` (`en_US`/`nl_NL`) and `--detectors` map to the detector catalogue shared with the WebUI.
- **Output handling**: [`sanitize_text/cli/io.py`](https://github.com/beecave-homelab/sanitize-text/blob/c30ca71ce7ebad61e178de8f7b2c020b83b9bf21/sanitize_text/cli/io.py) infers formats and delegates to `output.get_writer()` for TXT/MD/DOCX/PDF artifacts.
- **Optional resources**: `--download-nlp-models` pre-fetches spaCy/NLTK assets via [`sanitize_text/utils/nlp_resources.py`](https://github.com/beecave-homelab/sanitize-text/blob/c30ca71ce7ebad61e178de8f7b2c020b83b9bf21/sanitize_text/utils/nlp_resources.py).
- Core scrubbing logic lives in `_run_scrub()` and `core.scrubber` so tests can exercise behaviour without invoking Click or touching the filesystem.

## WebUI

- **App factory**: [`sanitize_text/webui/run.py`](https://github.com/beecave-homelab/sanitize-text/blob/c30ca71ce7ebad61e178de8f7b2c020b83b9bf21/sanitize_text/webui/run.py) defines `create_app()` and registers routes via `routes.init_routes(app)`.
- **Entry script**: [`sanitize_text/webui/main.py`](https://github.com/beecave-homelab/sanitize-text/blob/c30ca71ce7ebad61e178de8f7b2c020b83b9bf21/sanitize_text/webui/main.py) exposes `main()` for console scripts and `python -m sanitize_text.webui`.
- **Templates & assets**: HTML templates live under [`sanitize_text/webui/templates/`](https://github.com/beecave-homelab/sanitize-text/blob/c30ca71ce7ebad61e178de8f7b2c020b83b9bf21/sanitize_text/webui/templates), with JS/CSS under [`sanitize_text/webui/static/`](https://github.com/beecave-homelab/sanitize-text/blob/c30ca71ce7ebad61e178de8f7b2c020b83b9bf21/sanitize_text/webui/static).
- **Features**: detector selection, locale toggles, custom text, cleanup switch, verbose filth inspection, and CLI command preview.
- **File handling**: `/process-file` and `/download-file` save uploads to temp files, convert via `preconvert`, scrub, then stream JSON or artifacts.
- Development: `python -m sanitize_text.webui` or `docker-compose -f docker-compose.dev.yaml up`.
- Production: Dockerfile + Gunicorn (`sanitize_text.webui:create_app()`) or equivalent WSGI hosting.

## Docker

- [`Dockerfile`](https://github.com/beecave-homelab/sanitize-text/blob/c30ca71ce7ebad61e178de8f7b2c020b83b9bf21/Dockerfile) builds a Python 3.12-slim image, installs the package with `pip install .`, and runs Gunicorn on port 8000.
- [`docker-compose.yaml`](https://github.com/beecave-homelab/sanitize-text/blob/c30ca71ce7ebad61e178de8f7b2c020b83b9bf21/docker-compose.yaml) defines a `webui` service for production-like deployment, mapping `8000:8000`.
- [`docker-compose.dev.yaml`](https://github.com/beecave-homelab/sanitize-text/blob/c30ca71ce7ebad61e178de8f7b2c020b83b9bf21/docker-compose.dev.yaml) wires a development container with source volume mounts and Flask `--reload`.
- Both compose files set `FLASK_APP=sanitize_text.webui:create_app` and `PYTHONUNBUFFERED=1`; dev mode also enables `FLASK_ENV=development` and `FLASK_DEBUG=1`.

## Tests

- **Test runner**: pytest is configured in [`pyproject.toml`](https://github.com/beecave-homelab/sanitize-text/blob/c30ca71ce7ebad61e178de8f7b2c020b83b9bf21/pyproject.toml) with `--maxfail=1 -q --import-mode=append`.
- **Core**: tests cover scrubber orchestration, detector catalogues, NLP resources, normalization, and PDF utilities.
- **CLI**: tests exercise CLI options, IO helpers, verbose mode, and end-to-end scrubbing flows.
- **WebUI**: tests validate app factory, route registration, JSON responses, and export/download endpoints.
- **Output & cleanup**: tests cover writers, cleanup utilities, and edge cases for placeholders and gibberish runs.
- `pdm run pytest -q` for unit tests; `pdm run pytest --cov=. --cov-report=term-missing:skip-covered --cov-report=xml` for coverage.

## CI/CD

> No GitHub Actions or other CI configuration is present in this repo at this commit (no workflow files under `.github/`).

- Add a workflow that runs Ruff (`pdm run ruff check .`) and pytest with coverage on push/PR, mirroring local commands in [AGENTS.md](https://github.com/beecave-homelab/sanitize-text/blob/c30ca71ce7ebad61e178de8f7b2c020b83b9bf21/AGENTS.md) and [pyproject.toml](https://github.com/beecave-homelab/sanitize-text/blob/c30ca71ce7ebad61e178de8f7b2c020b83b9bf21/pyproject.toml).

**Always update this file when code or configuration changes.**
