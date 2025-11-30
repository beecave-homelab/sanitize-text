# VERSIONS.md

## ToC

- [v1.4.2 (Current)](#v142-current---30-11-2025)
- [v1.4.1](#v141---24-11-2025)
- [v1.4.0](#v140---23-11-2025)
- [v1.3.0](#v130---23-11-2025)
- [v1.2.0](#v120---22-11-2025)
- [v1.1.0](#v110---22-11-2025)
- [v1.0.0](#v100---21-11-2025)

## **v1.4.2** (Current) - *30-11-2025*

### 🐛 **Brief Description (v1.4.2)**

Patch release hardening Docker images and CI by fixing multimedia dependencies, correcting OCI metadata, and tightening compose configuration for development and PR workflows.

### 🐛 **Bug Fixes in v1.4.2**

- **Fixed**: Missing `ffmpeg` dependency in Docker images for media-related workloads.
  - **Issue**: Some document conversion and multimedia pipelines required `ffmpeg`, but the base images did not include it, leading to runtime errors inside containers.
  - **Root Cause**: Both `Dockerfile` and `Dockerfile.dev` omitted installation of the `ffmpeg` package.
  - **Solution**: Added explicit `ffmpeg` installation to the production and development Dockerfiles.

- **Fixed**: Incorrect OCI `org.opencontainers.image.source` label syntax in Docker images.
  - **Issue**: Image metadata for the source repository did not fully comply with OCI labelling recommendations.
  - **Root Cause**: The label key/value pair was mis-specified in the Dockerfile.
  - **Solution**: Corrected the label syntax to match the expected OCI format.

- **Fixed**: Inconsistent Docker compose build context for the WebUI service.
  - **Issue**: Earlier tweaks to the compose configuration temporarily regressed the build context, risking unexpected build behaviour.
  - **Root Cause**: The `docker-compose.yaml` build context path was removed and needed to be reintroduced correctly.
  - **Solution**: Restored and simplified the build context definition for the compose service.

### 🔧 **Improvements in v1.4.2**

- **Improved**: Pull request CI workflow configuration now also targets the `dev` branch, ensuring Docker and test workflows are exercised earlier in the development cycle.

### 📝 **Key Commits in v1.4.2**

`b1bd44d`, `e084959`, `d8dca11`, `fc6e424`, `79cb486`

---

## **v1.4.1** - *24-11-2025*

### 🐛 **Brief Description**

Patch release focusing on Docker and CI infrastructure: adds a Docker build workflow for `main` and pull requests, updates the Dockerfile with a clearer dev environment configuration, and tightens repository ignore rules.

### ✨ **New Features in v1.4.1**

- **Added**: GitHub Actions Docker build workflow for the `main` branch and pull requests, ensuring images are built and validated automatically.
- **Enhanced**: Dockerfile and development compose configuration to better support local development and iterative testing.

### 🔧 **Improvements in v1.4.1**

- **Improved**: `.gitignore` and `.githubignore` rules to exclude CI artifacts and workflow-specific files from version control noise.

### 📝 **Key Commits in v1.4.1**

`b2ded6f`, `6f4f538`, `bbf0901`, `870bc2c`

---

## **v1.4.0** - *23-11-2025*

### ✨ **Brief Description**

Feature release improving output formatting by removing locale headers from CLI/WebUI results, adding GitHub Container Registry metadata for Docker images, and tightening temporary file cleanup in the web routes.

### ✨ **New Features in v1.4.0**

- **Added**: GitHub Container Registry (GHCR) metadata to Docker configuration for better image publishing and discovery.

### 🐛 **Bug Fixes in v1.4.0**

- **Fixed**: Ensured temporary export/download files are always scheduled for deletion using `after_this_request` hooks.
  - **Issue**: Some temporary files created during WebUI export/download flows could persist longer than necessary.
  - **Root Cause**: Cleanup logic did not consistently register `after_this_request` callbacks for all code paths.
  - **Solution**: Added dedicated `after_this_request` cleanup hooks in `sanitize_text.webui.routes`.

### 🔧 **Improvements in v1.4.0**

- **Improved**: Removed locale header prefixes from scrubbed output in CLI/WebUI to produce cleaner, copy-paste-friendly results.
- **Refactored**: Simplified helper logic around multi-locale formatting to better separate aggregation from presentation.

### 📝 **Key Commits in v1.4.0**

`da6f413`, `e62db35`, `3fdfb9d`, `174b500`, `3233bb2`

---

## **v1.3.0** - *23-11-2025*

### ✨ **Brief Description (v1.3.0)**

Minor release adding richer verbose logging for CLI/WebUI scrubbing flows, plus performance and quality improvements to JSON-backed entity detectors and Dutch name data.

### ✨ **New Features in v1.3.0**

- **Enhanced**: CLI `sanitize-text` now exposes a single entrypoint with extended `-v/--verbose` logging for input resolution, locale selection, detector configuration, and output writing.
- **Enhanced**: WebUI gains optional verbose logging of scrubbing summaries to aid debugging and observability.

### 🐛 **Bug Fixes in v1.3.0**

- **Fixed**: Reduced false positives in Dutch name detection by removing ambiguous common words from `names.json`.
  - **Issue**: Frequent words like "Elke" and "Eren" were incorrectly flagged as person names.
  - **Root Cause**: These tokens lived in the static Dutch names list despite being common non-PII words.
  - **Solution**: Removed the problematic entries from the names dataset.

### 🔧 **Improvements in v1.3.0**

- **Improved**: JSON-backed entity detectors now collect all match candidates first and only filter overlaps afterward, simplifying the matching logic and paving the way for better performance.
- **Updated**: Markdownlint configuration and docs kept in sync with the evolved CLI/WebUI flows.

### 📝 **Key Commits in v1.3.0**

`bc74868`, `6677897`, `39cdf4d`, `87c6685`, `be3289b`

---

## **v1.2.0** - *22-11-2025*

### ✨ **Brief Description (v1.2.0)**

Patch release delivering configurable WebUI CLI options, matching tests, updated documentation, and lint configuration fixes.

### ✨ **New Features in v1.2.0**

- **Added**: Configurable host, port, debug, and NLP download options to the Click-based WebUI entry point.

### 🐛 **Bug Fixes in v1.2.0**

- **Fixed**: Residual blank line in `sanitize_text.utils.nlp_resources` imports to satisfy linting rules.
  - **Issue**: Markdownlint and Ruff flagged inconsistent spacing after import blocks.
  - **Root Cause**: Previous refactor left an empty spacer contradicting lint expectations.
  - **Solution**: Removed the superfluous newline to keep imports contiguous.

### 🔧 **Improvements in v1.2.0**

- **Improved**: Added markdownlint configuration and `.gitignore` updates so HTML details/summary blocks remain compliant.
- **Updated**: Documentation describing new WebUI CLI options plus matching Click-based integration tests.

### 📝 **Key Commits in v1.2.0**

`fd4a83b`, `5ce358e`, `ff48ffb`

---

## **v1.1.0** - *22-11-2025*

### ✨ **Brief Description (v1.1.0)**

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

### **Brief Description (v1.0.0)**

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
