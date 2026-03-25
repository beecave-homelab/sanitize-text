# AGENTS.md — sanitize-text Agent Manual

This document is the authoritative working agreement for AI agents and contributors in this
repository. It combines style rules with **sanitize-text-specific architecture and workflow
contracts** so edits remain coherent across CLI, WebUI, core scrubber logic, detectors, and tests.

When in doubt, prefer **correctness → safety → backward compatibility → clarity → brevity**.

## Fast local validation

```bash
# Lint/format
pdm run ruff check --fix .
pdm run ruff format .

# Unit tests
pdm run pytest --maxfail=1 -q

# Coverage
pdm run pytest --cov=. --cov-report=term-missing:skip-covered --cov-report=xml
```

## Operational commands (repo-specific)

```bash
# Install
pdm install

# CLI
pdm run sanitize-text --help

# WebUI (dev)
pdm run sanitize_text.webui --help
pdm run start-dev

# Add Dutch entities
pdm run sanitize_text.add_entity --help

# Docker
docker compose up
docker compose -f docker-compose.dev.yaml up
```

## Table of Contents

- [0) sanitize-text architecture contracts](#0-sanitize-text-architecture-contracts)
- [0.7) Agent task playbooks](#07-agent-task-playbooks)
- [1) Correctness (Ruff F - Pyflakes)](#1-correctness-ruff-f---pyflakes)
- [2) PEP 8 surface rules (Ruff E, W - pycodestyle)](#2-pep-8-surface-rules-ruff-e-w---pycodestyle)
- [3) Naming conventions (Ruff N - pep8-naming)](#3-naming-conventions-ruff-n---pep8-naming)
- [4) Imports: order & style (Ruff I - isort rules)](#4-imports-order--style-ruff-i---isort-rules)
- [5) Docstrings — content & style (Ruff D + DOC)](#5-docstrings--content--style-ruff-d--doc)
- [6) Import hygiene (Ruff TID - flake8-tidy-imports)](#6-import-hygiene-ruff-tid---flake8-tidy-imports)
- [7) Modern Python upgrades (Ruff UP - pyupgrade)](#7-modern-python-upgrades-ruff-up---pyupgrade)
- [8) Future annotations (Ruff FA - flake8-future-annotations)](#8-future-annotations-ruff-fa---flake8-future-annotations)
- [9) Local ignores (only when justified)](#9-local-ignores-only-when-justified)
- [10) Tests & examples (Pytest + Coverage)](#10-tests--examples-pytest--coverage)
- [11) Commit discipline](#11-commit-discipline)
- [12) Quick DO / DON’T](#12-quick-do--dont)
- [13) Pre-commit (recommended)](#13-pre-commit-recommended)
- [14) CI expectations](#14-ci-expectations)
- [15) SOLID design principles — Explanation & Integration](#15-solid-design-principles--explanation--integration)
- [16) Dependency and configuration management](#16-dependency-and-configuration-management)
- [17) Boundaries for safe changes](#17-boundaries-for-safe-changes)
- [Final note](#final-note)

______________________________________________________________________

## 0) sanitize-text architecture contracts

These are **project-level contracts**. Preserve them unless the change is explicitly requested.

### 0.1 Canonical package boundaries

- `sanitize_text/core/scrubber.py`: detector catalogue, scrubber composition, multi-locale orchestration.
- `sanitize_text/cli/main.py` + `sanitize_text/cli/io.py`: Click UX + IO resolution/output writing.
- `sanitize_text/webui/routes.py` + `sanitize_text/webui/helpers.py`: Flask endpoints and request shaping.
- `sanitize_text/output.py`: writer dispatch (`txt`/`md`/`docx`/`pdf`) through `get_writer()`.
- `sanitize_text/utils/custom_detectors/`: custom detector implementations.
- `sanitize_text/data/nl_entities/*.json` + `sanitize_text/data/en_entities/*.json`: detector data.
- `sanitize_text/add_entity/main.py`: JSON entity management CLI for Dutch entity stores.

### 0.2 Runtime behavior that must stay stable

- `locale=None` means process **both** `en_US` and `nl_NL`.
- CLI `_run_scrub()` defaults to **`nl_NL` output priority** when no locale is specified.
- WebUI and CLI must continue sharing the same core scrub logic (`run_multi_locale_scrub` / `scrub_text`).
- `--cleanup` defaults to enabled, and cleanup is the final stage before writing output.
- Output format inference remains centralized in `sanitize_text/cli/io.py::infer_output_format`.
- Writers remain resolved via `sanitize_text/output.py::get_writer`.

### 0.3 Extension points (preferred)

- **Add a detector**:

  1. Implement detector in `sanitize_text/utils/custom_detectors/`.
  2. Add factory + `DetectorSpec` in `sanitize_text/core/scrubber.py`.
  3. Register in `GENERIC_DETECTORS` or `LOCALE_DETECTORS`.
  4. Add/adjust tests in `tests/test_core_scrubber.py` and detector-focused tests.

- **Add an output format**:

  1. Implement writer in `sanitize_text/output.py`.
  2. Register in `_WRITERS` + update `get_writer()` behavior.
  3. Update `infer_output_format()` in `sanitize_text/cli/io.py`.
  4. Update CLI option choices and WebUI export/download MIME mapping if needed.
  5. Add tests in `tests/test_output_*.py`, CLI, and WebUI endpoint tests.

- **Add WebUI request option**:

  1. Parse and validate in `sanitize_text/webui/routes.py`.
  2. Keep helper logic in `sanitize_text/webui/helpers.py` where reusable.
  3. If the option maps to CLI semantics, update `/cli-preview` builder parity.
  4. Add endpoint tests in `tests/test_webui_routes_endpoints.py` and helper tests.

### 0.4 API/UX parity requirements

- WebUI and CLI should expose equivalent core scrubbing capabilities unless explicitly scoped otherwise.
- Avoid adding behavior to only one interface when it belongs in shared core logic.
- Prefer shared helpers over duplicating normalization or detector selection logic.

### 0.5 Two app-factory modules exist

- `sanitize_text/webui/run.py` is the deployment/script target (`gunicorn`, compose, scripts).
- `sanitize_text/webui/__init__.py` also provides `create_app()` and is used in tests/import paths.
- If app creation behavior changes, keep both modules aligned or consolidate carefully with tests updated.

### 0.6 Experimental scripts boundary

- Files under `scripts/` are helper utilities for data extraction/training and are **not** part of the main runtime contract.
- Prefer changes in `sanitize_text/` for production behavior; only touch `scripts/` when the user request is explicitly about tooling/data prep.

### 0.7 Agent task playbooks

Use these short workflows first; they encode the repo’s happy path.

- **Add detector**:

  1. Add detector class in `sanitize_text/utils/custom_detectors/`.
  2. Register `DetectorSpec` in `sanitize_text/core/scrubber.py`.
  3. Add tests in `tests/test_core_scrubber.py` and detector-specific tests.
  4. Run `pdm run pytest tests/test_core_scrubber.py -q`.

- **Change CLI option/behavior**:

  1. Update `sanitize_text/cli/main.py` (option wiring + command UX).
  2. Keep IO/format logic in `sanitize_text/cli/io.py`.
  3. Keep core logic in `sanitize_text/core/scrubber.py` (not in Click handlers).
  4. Run `pdm run pytest tests/test_cli_main.py tests/test_cli_io.py -q`.

- **Change WebUI request/endpoint behavior**:

  1. Parse/validate in `sanitize_text/webui/routes.py`.
  2. Move reusable shaping/normalization to `sanitize_text/webui/helpers.py`.
  3. Keep parity with CLI semantics (`/cli-preview`, detector/locale behavior).
  4. Run `pdm run pytest tests/test_webui_routes_endpoints.py tests/test_webui_routes_helpers.py -q`.

- **Change output format/writer behavior**:

  1. Update writer logic in `sanitize_text/output.py` (`_WRITERS`, `get_writer`).
  2. Keep format inference in `sanitize_text/cli/io.py::infer_output_format`.
  3. Update WebUI MIME/format handling if affected.
  4. Run `pdm run pytest tests/test_output_writers.py tests/test_output_pdf_docx.py tests/test_output_more.py -q`.

- **Update Dutch entity data flow**:

  1. Preserve `{ "match", "filth_type" }` JSON schema and sorted order.
  2. Prefer `sanitize_text/add_entity/main.py` path over ad-hoc writes.
  3. Verify with `pdm run pytest tests/test_add_entity.py tests/test_application_detector.py -q`.

## 1) Correctness (Ruff F - Pyflakes)

### What It Enforces — Correctness

- No undefined names/variables.
- No unused imports/variables/arguments.
- No duplicate arguments in function definitions.
- No `import *`.

### Agent Checklist — Correctness

- Remove dead code and unused symbols.
- Keep imports minimal and explicit.
- Use local scopes (comprehensions, context managers) where appropriate.
- Keep CLI defaults deterministic; do not introduce hidden runtime config for core scrub flows.

______________________________________________________________________

## 2) PEP 8 surface rules (Ruff E, W - pycodestyle)

### What It Enforces — PEP 8 Surface

- Spacing/blank-line/indentation hygiene.
- No trailing whitespace.
- Reasonable line breaks; respect the configured line length (see `pyproject.toml` or `ruff.toml`).

### Agent Checklist — PEP 8 Surface

- Let the formatter handle whitespace.
- Break long expressions cleanly (after operators, around commas).
- End files with exactly one trailing newline.

______________________________________________________________________

## 3) Naming conventions (Ruff N - pep8-naming)

### What It Enforces — Naming

- `snake_case` for functions, methods, and non-constant variables.
- `CapWords` (PascalCase) for classes.
- `UPPER_CASE` for module-level constants.
- Exceptions end with `Error` and subclass `Exception`.

### Agent Checklist — Naming

- Avoid camelCase unless mirroring a third-party API; if unavoidable, use a targeted pragma for that line only.

______________________________________________________________________

## 4) Imports: order & style (Ruff I - isort rules)

### What It Enforces — Imports

- Group imports: 1) Standard library, 2) Third-party, 3) First-party/local.
- Alphabetical within groups; one blank line between groups.
- Prefer one import per line for clarity.

### Agent Checklist — Imports

- Keep imports at module scope (top of file).
- Only alias when it adds clarity (e.g., `import numpy as np`).

### Canonical example — Imports

```python
from __future__ import annotations

from pathlib import Path

from scrubadub.detectors.email import EmailDetector

from sanitize_text.utils.cleanup import cleanup_output
from sanitize_text.utils.io_helpers import read_file_to_text
```

______________________________________________________________________

## 5) Docstrings — content & style (Ruff D + DOC)

Public modules, classes, functions, and methods **must have docstrings**. Ruff enforces **pydocstyle** (`D…`) and **pydoclint** (`DOC…`).

**Single-source style**: **Google-style** docstrings with type hints in signatures.

### Rules of Thumb — Docstrings

- Triple double quotes.
- First line: one-sentence summary, capitalized, ends with a period.
- Blank line after summary, then details.
- Keep `Args/Returns/Raises` in sync with the signature.
- Use imperative mood (“Return…”, “Validate…”). Don’t repeat obvious types (use type hints).

### Function Template — Docstrings

```python
def frobnicate(path: pathlib.Path, *, force: bool = False) -> str:
    """Frobnicate the resource at ``path``.

    Performs an idempotent frobnication. If ``force`` is true, existing
    artifacts will be replaced.

    Args:
        path: Filesystem location of the target resource.
        force: Replace previously generated artifacts if present.

    Returns:
        A stable identifier for the frobnicated resource.

    Raises:
        FileNotFoundError: If ``path`` does not exist.
        PermissionError: If write access is denied.
    """
```

### Class Template — Docstrings

```python
class ResourceManager:
    """Coordinate creation and lifecycle of resources.

    Notes:
        Thread-safe for read operations; writes are serialized.
    """
```

______________________________________________________________________

## 6) Import hygiene (Ruff TID - flake8-tidy-imports)

### What It Enforces — Import Hygiene

- Prefer absolute imports over deep relative imports.
- Avoid circular imports; import inside functions only for performance or to break a cycle.
- Avoid broad implicit re-exports; if you re-export, do it explicitly via `__all__`.

### Agent Checklist — Import Hygiene

```python
try:
    import rich
except ModuleNotFoundError:  # pragma: no cover
    rich = None  # type: ignore[assignment]
```

______________________________________________________________________

## 7) Modern Python upgrades (Ruff UP - pyupgrade)

### What It Prefers — Modernization

- f-strings over `format()` / `%`.
- PEP 585 generics (`list[str]`, `dict[str, int]`) over `typing.List`, `typing.Dict`, etc.
- Context managers where appropriate.
- Remove legacy constructs (`six`, `u''`, redundant `object`).

### Agent Checklist — Modernization

- Use `pathlib.Path` for filesystem paths.
- Use assignment expressions (`:=`) sparingly and only when clearer.
- Prefer `is None`/`is not None`.

______________________________________________________________________

## 8) Future annotations (Ruff FA - flake8-future-annotations)

### Guidance — Future Annotations

- Targeting **Python < 3.11**: place at the top of every module:

  ```python
  from __future__ import annotations
  ```

- Targeting **Python ≥ 3.11**: you may omit it; align the `FA` rule in Ruff config.

______________________________________________________________________

## 9) Local ignores (only when justified)

### Policy — Local Ignores

Prefer fixing the root cause. If a one-off ignore is necessary, keep it **scoped and documented**:

```python
value = compute()  # noqa: F401  # used by plugin loader via reflection
```

For docstring mismatches caused by third-party constraints, use a targeted `# noqa: D…, DOC…` with a brief reason.

______________________________________________________________________

## 10) Tests & examples (Pytest + Coverage)

### Expectations — Tests

- Tests follow the same rules as production code.
- Naming: `test_<unit_under_test>__<expected_behavior>()`.
- Keep tests deterministic; avoid hidden network/filesystem dependencies without fixtures.

### Repo test targeting map

- Core detector orchestration: `tests/test_core_scrubber.py`.
- CLI behavior and option wiring: `tests/test_cli_main.py`, `tests/test_cli_io.py`, `tests/test_cli_verbose.py`.
- WebUI route/helper behavior: `tests/test_webui_routes_endpoints.py`, `tests/test_webui_routes_helpers.py`, `tests/test_webui_run.py`, `tests/test_webui_main.py`.
- Output writers and PDF/DOCX specifics: `tests/test_output_writers.py`, `tests/test_output_pdf_docx.py`, `tests/test_output_more.py`.
- Custom detectors and filth processing: `tests/test_custom_detectors_*.py`, `tests/test_filth.py`, `tests/test_post_processors.py`.

Start with the smallest relevant test file, then broaden to full `pytest` only after targeted tests pass.

### Minimal Example — Tests

```python
def add(a: int, b: int) -> int:
    """Return the sum of two integers.

    Examples:
        >>> add(2, 3)
        5
    """
```

### Running — Tests & Coverage

```bash
# Quick
pdm run pytest -q

# Coverage (adjust --cov target to your package or ".")
pdm run pytest --cov=. --cov-report=term-missing:skip-covered --cov-report=xml
```

### Coverage Policy — Threshold

- Guideline: **≥ 85%** line coverage, with critical paths covered.
- Make CI fail below the threshold (see “CI expectations”).

______________________________________________________________________

## 11) Commit discipline

### Expectations — Commits

Run Ruff and tests **before** committing. Keep commits small and focused.

Use your project’s conventional commit format.

______________________________________________________________________

## 12) Quick DO / DON’T

### DO — Practices

- Google-style docstrings that match signatures.
- Absolute imports and sorted import blocks.
- f-strings and modern type syntax (`list[str]`).
- Remove unused code promptly.
- Use Pytest fixtures for reusable setup; prefer `tmp_path` for temp files.

### DON’T — Anti-patterns

- Introduce camelCase (except when mirroring external APIs).
- Use `import *` or deep relative imports.
- Leave parameters undocumented in public functions.
- Add broad `noqa`—always keep ignores narrow and justified.

______________________________________________________________________

## 13) Pre-commit (recommended)

### Configuration — Pre-commit

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.6.9  # keep in sync with your chosen Ruff version
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
```

______________________________________________________________________

## 14) CI expectations

### Commands — CI

```bash
# Current PR workflow behavior (.github/workflows/pr-ci.yaml)
pdm install -G lint,test,spacy
pdm run lint --fix
pdm run format
pdm run test
pdm run test-cov

# Recommended local pre-push (stricter)
pdm run ruff check .
pdm run ruff format --check .
pdm run pytest --maxfail=1 -q
pdm run pytest --cov=. --cov-report=term-missing:skip-covered --cov-report=xml
```

### Policy — CI Coverage

Keep coverage around or above the current project baseline; add tests for new branches and extension points.

______________________________________________________________________

## 15) SOLID design principles — Explanation & Integration

The **SOLID** principles help you design maintainable, testable, and extensible Python code. This section explains each principle concisely and shows how it maps to our linting, docs, and tests.

### S — Single Responsibility Principle (SRP)

- **Definition**: A module/class should have **one reason to change** (one cohesive responsibility).
- **Pythonic approach**:
  - Keep classes small; factor out I/O, parsing, and domain logic into distinct units.
  - Prefer composition over “god classes”.
- **In practice**:
  - Split functions that both “validate & write to disk” into separate units.
  - Move side-effects (I/O, network) behind narrow interfaces.
- **How we enforce/integrate**:
  - **Docs**: Each public class/function docstring states its single responsibility.
  - **Tests**: Unit tests focus on one behavior per test (narrow fixtures).
  - **Lint**: Large files/functions are a smell (consider refactor even if Ruff passes).

### O — Open/Closed Principle (OCP)

- **Definition**: Software entities should be **open for extension, closed for modification**.
- **Pythonic approach**:
  - Rely on **polymorphism** via abstract base classes or `typing.Protocol`.
  - Inject strategies or policies instead of hard-coding conditionals.
- **In practice**:
  - Define `Storage` protocol with `write()` and implement `FileStorage`, `S3Storage` without changing callers.
- **How we enforce/integrate**:
  - **Docs**: Document stable extension points (interfaces/protocols) in module/class docstrings.
  - **Tests**: Parametrize tests across multiple implementations to validate substitutability.
  - **Lint**: Keep imports clean; avoid “if type == …” switches in hot paths.

### L — Liskov Substitution Principle (LSP)

- **Definition**: Subtypes must be **substitutable** for their base types without breaking expectations.
- **Pythonic approach**:
  - Subclasses must not strengthen preconditions or weaken postconditions.
  - Keep method signatures compatible (types/return values/raised errors).
- **In practice**:
  - If base `Repository.get(id) -> Model | None`, a subtype must not start raising on “not found”.
- **How we enforce/integrate**:
  - **Docs**: State behavioral contracts and possible exceptions in docstrings.
  - **Tests**: Run the same behavior tests against base and derived implementations (parametrized).
  - **Lint**: Ruff won’t prove LSP, but naming and import rules reduce confusion; rely on tests/contracts.

### I — Interface Segregation Principle (ISP)

- **Definition**: Prefer **small, role-specific interfaces** over fat interfaces.
- **Pythonic approach**:
  - Use multiple `Protocol`s (or ABCs) with narrowly scoped methods.
  - Accept only what you need at call sites (e.g., `Readable` protocol, not `FileLikeAndNetworkAndCache`).
- **In practice**:
  - Split `DataStore` into `Readable` and `Writable` where consumers only need one.
- **How we enforce/integrate**:
  - **Docs**: Clarify the minimal interface needed by a function/class (in the Args section).
  - **Tests**: Provide tiny fakes/mocks that implement just the required protocol.
  - **Lint**: Keep imports modular; avoid cyclic dependencies driven by bloated interfaces.

### D — Dependency Inversion Principle (DIP)

- **Definition**: High-level modules **depend on abstractions**, not concrete details.
- **Pythonic approach**:
  - Use constructor or function **dependency injection** of protocols/ABCs.
  - Keep wiring in a thin composition/bootstrap layer.
- **In practice**:
  - Class accepts `Clock` protocol; production uses `SystemClock`, tests pass `FrozenClock`.
- **How we enforce/integrate**:
  - **Docs**: Document injected dependencies and their contracts.
  - **Tests**: Replace dependencies with fakes/stubs; no slow/global state in unit tests.
  - **Lint**: Absolute imports and clean layering reduce unintended tight coupling.

### SOLID — Minimal example (Protocols + DI)

```python
from __future__ import annotations
from typing import Protocol
import pathlib

class Storage(Protocol):
    def write(self, path: pathlib.Path, data: bytes) -> None: ...

class FileStorage:
    def write(self, path: pathlib.Path, data: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

class Uploader:
    """Upload artifacts using an injected Storage (DIP, OCP, ISP).

    Args:
        storage: Minimal interface that supports 'write'.
    """
    def __init__(self, storage: Storage) -> None:
        self._storage = storage  # DIP

    def publish(self, dest: pathlib.Path, payload: bytes) -> None:
        # SRP: only orchestrates publication; no direct filesystem logic here.
        self._storage.write(dest, payload)

# LSP test idea: any Storage conformer can be used transparently (FakeStorage, S3Storage, ...).
```

### SOLID — Agent Checklist

- **SRP**: One responsibility per module/class; split I/O from domain logic.
- **OCP**: Use protocols/ABCs and strategy injection to extend without edits.
- **LSP**: Keep subtype behavior/contract compatible; parametrize tests over implementations.
- **ISP**: Prefer small protocols; accept only what you need.
- **DIP**: Depend on abstractions; inject dependencies (avoid hard-coded singletons/globals).

______________________________________________________________________

## 16) Dependency and configuration management

### 16.1 Dependency source of truth

- `pyproject.toml` is the canonical dependency definition.

- Do **not** hand-edit `requirements.txt`, `requirements.dev.txt`, or `requirements.all.txt` for dependency changes.

- After dependency updates, regenerate requirement exports:

  ```bash
  pdm export --pyproject --no-hashes --prod -o requirements.txt
  pdm export --pyproject --no-hashes --dev -o requirements.dev.txt
  pdm export --pyproject --no-hashes -G :all -o requirements.all.txt
  ```

### 16.2 Runtime configuration in this repo

- CLI/core scrubbing does **not** require project-specific environment variables.
- WebUI container/dev runtime may use Flask environment variables (`FLASK_APP`, `FLASK_ENV`, `FLASK_DEBUG`, `PYTHONUNBUFFERED`) as wired by compose files.
- Keep app behavior primarily controlled by explicit CLI/WebUI options, not hidden env toggles.

### 16.3 Optional model downloads and network sensitivity

- NLP model download is opt-in in CLI (`--download-nlp-models`) and optional in WebUI startup flags.
- Treat model download as a networked side effect; do not make it implicit in core scrubber functions.
- Keep tests isolated from network by monkeypatching `download_optional_models` and related helpers.

### 16.4 Packaging and version alignment

- Entry points must stay aligned with `pyproject.toml` scripts:
  - `sanitize-text = sanitize_text.cli.main:main`
  - `sanitize-text-webui = sanitize_text.webui.main:main`
- If behavior changes in user-facing commands, update `README.md`, tests, and command help text together.

______________________________________________________________________

## 17) Boundaries for safe changes

### ✅ Always

- Keep core logic in reusable modules (`core`, `cli/io`, `webui/helpers`) and keep shell/UI layers thin.
- Add or update tests when behavior changes, especially for locale orchestration and detector selection.
- Preserve backward-compatible CLI/WebUI options unless a breaking change is explicitly requested.
- Reuse existing extension points (`DetectorSpec`, `get_writer`, `read_file_to_text`, route helpers).

### ⚠️ Ask first

- Changing default locale behavior or output precedence in CLI.
- Changing detector default enablement (`enabled_by_default`) or detector ordering.
- Introducing new external services, telemetry, or network dependencies.
- Large rewrites across both app factories (`webui/run.py` and `webui/__init__.py`).

### 🚫 Never

- Bypass `core/scrubber.py` by duplicating scrub logic in CLI or WebUI routes.
- Add a detector only in UI code without registering it in the core catalogue.
- Break output format routing by writing files directly from random modules instead of `get_writer()`.
- Modify locale entity JSON files with ad-hoc structure changes; preserve the `{ "match", "filth_type" }` schema and sorted order expected by `add_entity`.
- Commit changes that skip lint/test validation when the edited area has existing tests.

______________________________________________________________________

## Final note

If you must deviate (e.g., third-party naming or unavoidable import patterns), add a **short comment** explaining why and keep the ignore as narrow as possible.
