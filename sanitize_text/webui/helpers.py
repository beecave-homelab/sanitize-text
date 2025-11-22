"""Helper utilities for the sanitize-text web UI.

These functions contain pure logic used by :mod:`sanitize_text.webui.routes`
for detector grouping, CLI preview construction, and file-to-text loading.
They are kept free of Flask and Click dependencies for easier testing and
reuse.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sanitize_text.utils.io_helpers import read_file_to_text


def group_detectors(
    *,
    get_available_detectors: callable,
    generic_detector_names: set[str],
) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    """Return dictionaries of generic, English, and Dutch detectors.

    Args:
        get_available_detectors: Callable returning detector descriptions per
            locale.
        generic_detector_names: Detector names that are considered generic
            across locales.

    Returns:
        Tuple ``(generic, english_specific, dutch_specific)``.
    """
    english = get_available_detectors("en_US")
    dutch = get_available_detectors("nl_NL")

    generic = {key: english[key] for key in generic_detector_names if key in english}
    english_specific = {
        key: value for key, value in english.items() if key not in generic_detector_names
    }
    dutch_specific = {
        key: value for key, value in dutch.items() if key not in generic_detector_names
    }

    return generic, english_specific, dutch_specific


def build_locale_selections(
    selected_detectors: list[str] | None,
) -> dict[str, list[str]] | None:
    """Transform raw checkbox values into per-locale detector selections.

    Args:
        selected_detectors: Raw detector tokens from the WebUI payload.

    Returns:
        Mapping from locale code to a sorted list of detector names, or ``None``
        if no selections were provided.
    """
    if not selected_detectors:
        return None

    generic_selection = {token for token in selected_detectors if ":" not in token}
    locale_map = {
        "en_US": set(generic_selection),
        "nl_NL": set(generic_selection),
    }

    for token in selected_detectors:
        if ":" not in token:
            continue
        prefix, _, detector_name = token.partition(":")
        if prefix == "en":
            locale_map["en_US"].add(detector_name)
        elif prefix == "nl":
            locale_map["nl_NL"].add(detector_name)

    return {locale: sorted(detectors) for locale, detectors in locale_map.items()}


def format_results_text(results: list[dict[str, str]]) -> str:
    """Return a human-readable text for multiple locales.

    Args:
        results: List of dicts with keys ``locale`` and ``text``.

    Returns:
        Combined string with sections per-locale.
    """
    sections: list[str] = []
    for item in results:
        loc = item.get("locale", "?")
        text = item.get("text", "")
        sections.append(f"Results for {loc}:\n{text}")
    return "\n\n".join(sections)


def normalize_detector_tokens(detectors: list[str] | None) -> list[str]:
    """Return normalized detector names without locale prefixes.

    WebUI represents locale-specific detectors using a ``"<locale>:<name>"``
    prefix (for example ``"en:name"``). The CLI expects bare detector names;
    this helper strips prefixes and de-duplicates tokens while preserving a
    stable order for display.
    """
    if not detectors:
        return []

    seen: set[str] = set()
    normalized: list[str] = []
    for token in detectors:
        name = token.split(":", 1)[-1]
        if not name or name in seen:
            continue
        seen.add(name)
        normalized.append(name)
    return normalized


def build_cli_preview(
    *,
    source: str,
    locale: str | None,
    detectors: list[str] | None,
    cleanup: bool,
    verbose: bool,
    output_format: str,
    pdf_mode: str,
    font_size: int,
    pdf_backend: str | None = None,
) -> str:
    """Return a ``sanitize-text`` CLI command preview for the WebUI.

    The preview is shell-oriented and mirrors the main CLI options without
    echoing full user content. It is meant purely for discoverability so GUI
    users can learn the equivalent terminal command.
    """
    parts: list[str] = ["sanitize-text"]

    if source == "file":
        parts.extend(["-i", "<input-file>"])
    else:
        # Default to inline text when source is not explicitly "file".
        parts.extend(["-t", "<text>"])

    if locale:
        parts.extend(["-l", locale])

    normalized_detectors = normalize_detector_tokens(detectors)
    if normalized_detectors:
        detector_str = " ".join(sorted(normalized_detectors))
        parts.extend(["-d", f'"{detector_str}"'])

    if not cleanup:
        parts.append("--no-cleanup")

    if verbose:
        parts.append("-v")

    if output_format and output_format != "txt":
        parts.extend(["--output-format", output_format])

    if output_format == "pdf":
        parts.extend(["--pdf-mode", pdf_mode])
        parts.extend(["--font-size", str(font_size)])

    if source == "file" and pdf_backend:
        parts.extend(["--pdf-backend", pdf_backend])

    return " ".join(parts)


def read_uploaded_file_to_text(
    upload_path: Path,
    *,
    pdf_backend: str = "markitdown",
    preconvert_module: Any,
    normalize_pdf_text_func: Any,
) -> str:
    """Return text extracted from an uploaded file path.

    Uses the same conversion rules as the CLI: PDF, DOC/DOCX, RTF, images,
    otherwise treats it as UTF-8 text.

    Args:
        upload_path: Temporary path to the uploaded file.
        pdf_backend: Backend hint for PDF conversion ("pymupdf4llm" or
            "markitdown").
        preconvert_module: Object providing conversion helpers
            (``to_markdown``, ``docx_to_text``, ``rtf_to_text``,
            ``image_to_text``).
        normalize_pdf_text_func: Callable used to normalize extracted Markdown
            text from PDFs.

    Returns:
        Extracted plain text.
    """
    return read_file_to_text(
        upload_path,
        pdf_backend=pdf_backend,
        preconvert_module=preconvert_module,
        normalize_pdf_text_func=normalize_pdf_text_func,
    )
