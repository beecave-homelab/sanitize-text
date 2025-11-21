"""Web routes and API endpoints for the text sanitization web interface."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from flask import Flask, Response, jsonify, render_template, request, send_file

from sanitize_text.core.scrubber import (
    collect_filth,
    get_available_detectors,
    setup_scrubber,
)
from sanitize_text.output import get_writer
from sanitize_text.utils import preconvert
from sanitize_text.utils.cleanup import cleanup_output

GENERIC_DETECTORS = {
    "email",
    "phone",
    "url",
    "markdown_url",
    "private_ip",
    "public_ip",
}


def _group_detectors() -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    """Return dictionaries of generic, English, and Dutch detectors."""
    english = get_available_detectors("en_US")
    dutch = get_available_detectors("nl_NL")

    generic = {key: english[key] for key in GENERIC_DETECTORS if key in english}
    english_specific = {
        key: value for key, value in english.items() if key not in GENERIC_DETECTORS
    }
    dutch_specific = {key: value for key, value in dutch.items() if key not in GENERIC_DETECTORS}

    return generic, english_specific, dutch_specific


def _build_locale_selections(
    selected_detectors: list[str] | None,
) -> dict[str, list[str]] | None:
    """Transform raw checkbox values into per-locale detector selections.

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


def _format_results_text(results: list[dict[str, str]]) -> str:
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


def _normalize_detector_tokens(detectors: list[str] | None) -> list[str]:
    """Return normalized detector names without locale prefixes.

    The WebUI represents locale-specific detectors using a ``"<locale>:<name>"``
    prefix (for example ``"en:name"``). The CLI, however, expects bare
    detector names. This helper removes such prefixes and de-duplicates
    detector tokens while preserving a stable order for display.

    Args:
        detectors: Raw detector tokens from the WebUI payload.

    Returns:
        A list of normalized detector names suitable for CLI ``--detectors``.
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


def _build_cli_preview(
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

    The preview is intentionally shell-oriented, mirroring the main CLI
    options without echoing full user content. It is meant purely for
    discoverability so GUI users can learn the equivalent terminal command.
    """
    parts: list[str] = ["sanitize-text"]

    if source == "file":
        parts.extend(["-i", "<input-file>"])
    else:
        # Default to inline text when source is not explicitly "file".
        parts.extend(["-t", "<text>"])

    if locale:
        parts.extend(["-l", locale])

    normalized_detectors = _normalize_detector_tokens(detectors)
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


def _read_uploaded_file_to_text(upload_path: Path, *, pdf_backend: str = "markitdown") -> str:
    """Return text extracted from an uploaded file path.

    Uses the same conversion rules as the CLI: PDF, DOC/DOCX, RTF, images,
    otherwise treats it as UTF-8 text.
    """
    ext = upload_path.suffix.lower()
    if ext == ".pdf":
        backend = (pdf_backend or "markitdown").lower()
        if backend == "pymupdf4llm":
            try:
                import pymupdf4llm  # type: ignore[import]
            except Exception:  # noqa: BLE001
                raw_md = preconvert.to_markdown(str(upload_path))
            else:
                raw_md = pymupdf4llm.to_markdown(str(upload_path))
        else:
            raw_md = preconvert.to_markdown(str(upload_path))
        # Normalize to plain text similar to CLI cleanup path
        from sanitize_text.utils.normalize import normalize_pdf_text

        return normalize_pdf_text(raw_md, title=None)
    if ext in {".doc", ".docx"}:
        return preconvert.docx_to_text(str(upload_path))
    if ext == ".rtf":
        return preconvert.rtf_to_text(str(upload_path))
    if ext in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}:
        return preconvert.image_to_text(str(upload_path))
    return upload_path.read_text(encoding="utf-8", errors="replace")


def init_routes(app: Flask) -> Flask:
    """Initialize Flask routes for the web interface.

    Returns:
        The Flask application with routes registered.
    """
    generic_detectors, english_detectors, dutch_detectors = _group_detectors()
    spacy_available = "spacy_entities" in english_detectors or "spacy_entities" in dutch_detectors

    @app.route("/")
    def index() -> str:
        """Render the main page of the web interface.

        Returns:
            Rendered HTML for the index page.
        """
        return render_template(
            "index.html",
            generic_detectors=generic_detectors,
            english_detectors=english_detectors,
            dutch_detectors=dutch_detectors,
            spacy_available=spacy_available,
        )

    @app.route("/cli-preview", methods=["POST"])
    def cli_preview() -> Response:
        """Return a CLI command preview for the current WebUI configuration.

        The JSON payload mirrors the WebUI options and is translated to a
        human-readable ``sanitize-text`` command string that users can copy.
        """
        data = request.json or {}
        source = (data.get("source") or "text").lower()
        locale = data.get("locale") or None
        detectors = data.get("detectors") or []
        cleanup = bool(data.get("cleanup", True))
        verbose = bool(data.get("verbose", False))
        output_format = (data.get("output_format") or "txt").lower()
        pdf_mode = (data.get("pdf_mode") or "pre").lower()
        pdf_backend = (data.get("pdf_backend") or "pymupdf4llm").lower()

        font_size_raw = data.get("font_size", 11)
        try:
            font_size = int(font_size_raw)
        except (TypeError, ValueError):  # pragma: no cover - defensive
            font_size = 11

        command = _build_cli_preview(
            source=source,
            locale=locale,
            detectors=detectors,
            cleanup=cleanup,
            verbose=verbose,
            output_format=output_format,
            pdf_mode=pdf_mode,
            font_size=font_size,
            pdf_backend=pdf_backend,
        )
        return jsonify({"command": command})

    @app.route("/process", methods=["POST"])
    def process() -> Response:
        """Process text and remove PII based on specified locale and detectors.

        Returns:
            A JSON response with processing results or an error message.
        """
        data = request.json or {}
        input_text = data.get("text", "")
        locale = data.get("locale") or None
        selected_detectors = data.get("detectors") or []
        custom = data.get("custom") or None
        cleanup = bool(data.get("cleanup", True))
        verbose = bool(data.get("verbose", False))

        if not input_text:
            return jsonify({"error": "No text provided"}), 400

        per_locale_selection = _build_locale_selections(selected_detectors)
        locales_to_process = ["en_US", "nl_NL"] if locale is None else [locale]

        results: list[dict[str, object]] = []
        for current_locale in locales_to_process:
            try:
                detectors_for_locale = None
                if per_locale_selection is not None:
                    detectors_for_locale = per_locale_selection.get(current_locale, [])
                scrubber = setup_scrubber(
                    current_locale, detectors_for_locale, custom_text=custom, verbose=verbose
                )
                scrubbed_text = scrubber.clean(input_text)
                if cleanup:
                    scrubbed_text = cleanup_output(scrubbed_text)
                payload: dict[str, object] = {"locale": current_locale, "text": scrubbed_text}
                if verbose:
                    filths = collect_filth(
                        input_text,
                        locale=current_locale,
                        selected_detectors=detectors_for_locale,
                        custom_text=custom,
                    ).get(current_locale, [])
                    payload["filth"] = [
                        {
                            "type": getattr(f, "type", ""),
                            "text": getattr(f, "text", ""),
                            "replacement": getattr(f, "replacement_string", ""),
                        }
                        for f in filths
                    ]
                results.append(payload)
            except Exception as exc:  # pragma: no cover - defensive
                print(f"Warning: Processing failed for locale {current_locale}: {exc}")
                continue

        if not results:
            return jsonify({"error": "All processing attempts failed"}), 500

        return jsonify({"results": results})

    @app.route("/process-file", methods=["POST"])
    def process_file() -> Response:
        """Process an uploaded file and return scrubbed text as JSON.

        The request must be ``multipart/form-data`` with fields:
        - file: the uploaded file
        - locale: optional locale (en_US/nl_NL)
        - detectors: optional repeated field or comma-separated values
        - custom: optional custom text
        - cleanup: optional boolean (default True)
        - verbose: optional boolean (default False)

        Returns:
            Response: JSON body with results per-locale or an error message.
        """
        if "file" not in request.files:
            return jsonify({"error": "No file provided"}), 400

        file = request.files["file"]
        if file.filename == "":
            return jsonify({"error": "Empty filename"}), 400

        pdf_backend = request.form.get("pdf_backend", "pymupdf4llm")

        # Persist upload to a temporary file to reuse existing converters
        suffix = Path(file.filename).suffix or ""
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            file.save(tmp)
            tmp_path = Path(tmp.name)

        try:
            input_text = _read_uploaded_file_to_text(tmp_path, pdf_backend=pdf_backend)
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

        # Parse options
        locale = request.form.get("locale") or None
        custom = request.form.get("custom") or None
        cleanup = request.form.get("cleanup", "true").lower() in {"1", "true", "yes", "on"}
        verbose = request.form.get("verbose", "false").lower() in {"1", "true", "yes", "on"}

        # detectors may come as repeated fields or comma/space separated
        detectors_fields: list[str] = request.form.getlist("detectors") or []
        if not detectors_fields:
            raw = request.form.get("detectors", "")
            if raw:
                detectors_fields = [t for t in raw.replace(",", " ").split() if t]

        per_locale_selection = _build_locale_selections(detectors_fields or None)
        locales_to_process = ["en_US", "nl_NL"] if locale is None else [locale]

        results: list[dict[str, object]] = []
        for current_locale in locales_to_process:
            try:
                detectors_for_locale = None
                if per_locale_selection is not None:
                    detectors_for_locale = per_locale_selection.get(current_locale, [])
                scrubber = setup_scrubber(
                    current_locale, detectors_for_locale, custom_text=custom, verbose=verbose
                )
                scrubbed_text = scrubber.clean(input_text)
                if cleanup:
                    scrubbed_text = cleanup_output(scrubbed_text)
                payload: dict[str, object] = {"locale": current_locale, "text": scrubbed_text}
                if verbose:
                    filths = collect_filth(
                        input_text,
                        locale=current_locale,
                        selected_detectors=detectors_for_locale,
                        custom_text=custom,
                    ).get(current_locale, [])
                    payload["filth"] = [
                        {
                            "type": getattr(f, "type", ""),
                            "text": getattr(f, "text", ""),
                            "replacement": getattr(f, "replacement_string", ""),
                        }
                        for f in filths
                    ]
                results.append(payload)
            except Exception as exc:  # pragma: no cover - defensive
                print(f"Warning: Processing failed for locale {current_locale}: {exc}")
                continue

        if not results:
            return jsonify({"error": "All processing attempts failed"}), 500

        return jsonify({"results": results})

    @app.route("/export", methods=["POST"])
    def export_text() -> Response:
        """Return a downloadable file for scrubbed text from JSON payload.

        Expects JSON with keys: text, locale, detectors, custom, cleanup,
        output_format (txt|docx|pdf), and optional pdf_mode, font_size.
        """
        data = request.json or {}
        input_text = data.get("text", "")
        if not input_text:
            return jsonify({"error": "No text provided"}), 400

        locale = data.get("locale") or None
        selected_detectors = data.get("detectors") or []
        custom = data.get("custom") or None
        cleanup = bool(data.get("cleanup", True))
        output_format = (data.get("output_format") or "txt").lower()
        pdf_mode = data.get("pdf_mode", "pre")
        font_size = int(data.get("font_size", 11))

        # Build results text first (so multi-locale matches CLI semantics)
        per_locale_selection = _build_locale_selections(selected_detectors)
        locales_to_process = ["en_US", "nl_NL"] if locale is None else [locale]

        interim_results: list[dict[str, str]] = []
        for current_locale in locales_to_process:
            try:
                detectors_for_locale = None
                if per_locale_selection is not None:
                    detectors_for_locale = per_locale_selection.get(current_locale, [])
                scrubber = setup_scrubber(current_locale, detectors_for_locale, custom_text=custom)
                scrubbed_text = scrubber.clean(input_text)
                if cleanup:
                    scrubbed_text = cleanup_output(scrubbed_text)
                interim_results.append({"locale": current_locale, "text": scrubbed_text})
            except Exception as exc:  # pragma: no cover - defensive
                print(f"Warning: Processing failed for locale {current_locale}: {exc}")
                continue

        if not interim_results:
            return jsonify({"error": "All processing attempts failed"}), 500

        combined_text = _format_results_text(interim_results)

        # Write to a temporary file using existing writers
        writer = get_writer(output_format)
        suffix = f".{output_format}"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp_path = Path(tmp.name)
        write_kwargs: dict[str, object] = {}
        if output_format == "pdf":
            write_kwargs = {"pdf_mode": pdf_mode, "pdf_font": None, "font_size": font_size}
        writer.write(combined_text, str(tmp_path), **write_kwargs)

        download_name = f"scrubbed{suffix}"
        mimetypes = {
            "txt": "text/plain",
            "md": "text/markdown",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "pdf": "application/pdf",
        }
        return send_file(
            str(tmp_path),
            mimetype=mimetypes.get(output_format, "application/octet-stream"),
            as_attachment=True,
            download_name=download_name,
        )

    @app.route("/download-file", methods=["POST"])
    def download_file() -> Response:
        """Process an uploaded file and return a downloadable artifact.

        multipart/form-data fields:
        - file: input document
        - pdf_font: optional TTF font file (PDF only)
        - locale, detectors, custom, cleanup
        - output_format (txt|docx|pdf), pdf_mode, font_size

        Returns:
            Response: File attachment in the requested format.
        """
        if "file" not in request.files:
            return jsonify({"error": "No file provided"}), 400

        file = request.files["file"]
        if file.filename == "":
            return jsonify({"error": "Empty filename"}), 400

        pdf_backend = request.form.get("pdf_backend", "pymupdf4llm")

        suffix = Path(file.filename).suffix or ""
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_in:
            file.save(tmp_in)
            in_path = Path(tmp_in.name)

        try:
            input_text = _read_uploaded_file_to_text(in_path, pdf_backend=pdf_backend)
        finally:
            try:
                os.unlink(in_path)
            except OSError:
                pass

        # Options
        locale = request.form.get("locale") or None
        custom = request.form.get("custom") or None
        cleanup = request.form.get("cleanup", "true").lower() in {"1", "true", "yes", "on"}
        output_format = (request.form.get("output_format") or "txt").lower()
        pdf_mode = request.form.get("pdf_mode", "pre")
        font_size_raw = request.form.get("font_size", "11")
        try:
            font_size = int(font_size_raw)
        except ValueError:
            font_size = 11

        detectors_fields: list[str] = request.form.getlist("detectors") or []
        if not detectors_fields:
            raw = request.form.get("detectors", "")
            if raw:
                detectors_fields = [t for t in raw.replace(",", " ").split() if t]

        per_locale_selection = _build_locale_selections(detectors_fields or None)
        locales_to_process = ["en_US", "nl_NL"] if locale is None else [locale]

        interim_results: list[dict[str, str]] = []
        for current_locale in locales_to_process:
            try:
                detectors_for_locale = None
                if per_locale_selection is not None:
                    detectors_for_locale = per_locale_selection.get(current_locale, [])
                scrubber = setup_scrubber(current_locale, detectors_for_locale, custom_text=custom)
                scrubbed_text = scrubber.clean(input_text)
                if cleanup:
                    scrubbed_text = cleanup_output(scrubbed_text)
                interim_results.append({"locale": current_locale, "text": scrubbed_text})
            except Exception as exc:  # pragma: no cover - defensive
                print(f"Warning: Processing failed for locale {current_locale}: {exc}")
                continue

        if not interim_results:
            return jsonify({"error": "All processing attempts failed"}), 500

        combined_text = _format_results_text(interim_results)

        # Prepare PDF font if provided
        pdf_font_path: str | None = None
        if output_format == "pdf" and "pdf_font" in request.files:
            font_file = request.files["pdf_font"]
            if font_file and font_file.filename:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".ttf") as tmp_font:
                    font_file.save(tmp_font)
                    pdf_font_path = tmp_font.name

        writer = get_writer(output_format)
        suffix = f".{output_format}"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_out:
            out_path = Path(tmp_out.name)
        write_kwargs: dict[str, object] = {}
        if output_format == "pdf":
            write_kwargs = {"pdf_mode": pdf_mode, "pdf_font": pdf_font_path, "font_size": font_size}
        writer.write(combined_text, str(out_path), **write_kwargs)

        download_name = f"scrubbed{suffix}"
        mimetypes = {
            "txt": "text/plain",
            "md": "text/markdown",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "pdf": "application/pdf",
        }

        response = send_file(
            str(out_path),
            mimetype=mimetypes.get(output_format, "application/octet-stream"),
            as_attachment=True,
            download_name=download_name,
        )
        # Best-effort cleanup of temp font after response is sent handled by OS
        return response

    return app
