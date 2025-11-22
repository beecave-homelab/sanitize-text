# VERSIONS.md

## ToC

- [v1.1.0 (Current)](#v110-current---22-11-2025)
- [v1.0.0](#v100---21-11-2025)

## **v1.1.0** (Current) - *22-11-2025*

### ✨ **Brief Description**

Minor release focusing on SOLID-aligned refactors, a shared multi-locale scrubbing helper, configurable post-processing, and updated documentation.

### ✨ **New Features in v1.1.0**

- **Enhanced**: Shared multi-locale scrubbing helper `run_multi_locale_scrub()` for CLI/WebUI-style flows.
- **Enhanced**: Configurable post-processing via `post_processor_factory` and `DEFAULT_POST_PROCESSOR_FACTORY`.

### 🔧 **Improvements in v1.1.0**

- **Improved**: WebUI routes now use logging-based warnings and delegate multi-locale orchestration to shared helpers.
- **Improved**: Dutch entity deduplication uses an explicit `DutchEntityDetector.reset_loaded_entities()` hook.
- **Updated**: Documentation to describe the new architecture helpers and to use relative links for internal files.

### 📝 **Key Commits in v1.1.0**

`8c8a185`, `189152d`, `cb291d7`, `556119c`, `9586710`

---

## **v1.0.0** - *21-11-2025*

### **Brief Description**

First stable release of `sanitize-text` with a shared scrubbing core, Click-based CLI, Flask WebUI, and support for multiple document formats.

### **New Features in v1.0.0**

- **Added**: Custom detector catalogue for URLs (bare domains, Markdown links, SharePoint), email, phone, and private/public IPs.
- **Added**: Locale-specific detectors and data for Dutch (`nl_NL`) and English (`en_US`), including cities, names, and organizations.
- **Added**: Core scrubbing engine (`sanitize_text.core.scrubber`) with configurable detectors, verbose mode, and `collect_filth()` helpers.
- **Added**: Click-based CLI (`sanitize_text.cli.main`) with rich options for input sources, detectors, locales, PDF backends, and output formats.
- **Added**: Flask-based WebUI (`sanitize_text.webui`) with text and file workflows, detector selection, CLI preview, and downloadable artifacts.
- **Added**: Pre-conversion utilities for PDF, DOC/DOCX, RTF, and images, plus `scripts/pdf2md.py` for multi-backend PDF→Markdown comparison.
- **Added**: Dockerfile and docker-compose configurations for running the WebUI in production and development modes.

### **Bug Fixes in v1.0.0**

- **Fixed**: Corrected Dutch name detection edge cases (COMMON_WORDS tweaks) and cleaned up duplicate or incorrect city entries.
- **Fixed**: Minor data and configuration issues in entity JSON files and Docker-related settings.

### **Improvements in v1.0.0**

- **Refactored**: CLI I/O and output writers into dedicated modules to separate side effects from core logic.
- **Refactored**: WebUI structure and routes to improve user experience and align with the shared scrubbing engine.
- **Improved**: URL and detector handling with additional logging and normalization.
- **Updated**: Requirements and Python version targets to use modern, supported dependency versions.

### **Key Commits in v1.0.0**

Representative commits from `5fcad855264b02ff237bbf00378c502681751e5f` .. `c30ca71ce7ebad61e178de8f7b2c020b83b9bf21`:

`c30ca71`, `80d7436`, `68e7fe3`, `f2ede7d`, `fc70e65`

---
