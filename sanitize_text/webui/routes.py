"""Web routes and API endpoints for the text sanitization web interface."""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path

from flask import Flask, Response, current_app, jsonify, render_template, request, send_file

from sanitize_text.core.scrubber import (
    MultiLocaleResult,
    get_available_detectors,
    run_multi_locale_scrub,
)
from sanitize_text.output import get_writer
from sanitize_text.utils import preconvert
from sanitize_text.utils.cleanup import cleanup_output
from sanitize_text.webui import helpers

logger = logging.getLogger(__name__)


def _log_verbose_summary(
    source: str,
    *,
    raw_text: str,
    result: MultiLocaleResult,
) -> None:
    """Emit CLI-style verbose details for a processed request."""
    active_logger = current_app.logger if current_app else logger
    active_logger.info(
        "[WebUI][VERBOSE] %s request length=%d characters.",
        source,
        len(raw_text),
    )
    for locale_result in result.results:
        locale = locale_result.locale
        active_logger.info(
            "[WebUI][VERBOSE] Locale %s produced %d characters.",
            locale,
            len(locale_result.text),
        )
        filths = locale_result.filth or []
        if filths:
            active_logger.info(
                "[WebUI][VERBOSE] Found %d PII match(es) for %s.",
                len(filths),
                locale,
            )
            for filth in filths:
                replacement = getattr(filth, "replacement_string", "")
                display_type = getattr(filth, "type", "unknown") or "unknown"
                text = getattr(filth, "text", "")
                active_logger.info(
                    "    - %s: '%s' -> '%s'",
                    display_type,
                    text,
                    replacement,
                )
        else:
            active_logger.info("[WebUI][VERBOSE] No PII matches for %s.", locale)

    if result.errors:
        for failed_locale, message in result.errors.items():
            active_logger.warning(
                "[WebUI][VERBOSE] Locale %s failed: %s",
                failed_locale,
                message,
            )


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
    return helpers.group_detectors(
        get_available_detectors=get_available_detectors,
        generic_detector_names=GENERIC_DETECTORS,
    )


def _build_locale_selections(
    selected_detectors: list[str] | None,
) -> dict[str, list[str]] | None:
    """Transform raw checkbox values into per-locale detector selections.

    Returns:
        Mapping from locale code to a sorted list of detector names, or ``None``
        if no selections were provided.
    """
    return helpers.build_locale_selections(selected_detectors)


def _format_results_text(results: list[dict[str, str]]) -> str:
    """Return a human-readable text for multiple locales.

    Args:
        results: List of dicts with keys ``locale`` and ``text``.

    Returns:
        Combined string with sections per-locale.
    """
    return helpers.format_results_text(results)


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
    return helpers.build_cli_preview(
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


def _read_uploaded_file_to_text(upload_path: Path, *, pdf_backend: str = "markitdown") -> str:
    """Return text extracted from an uploaded file path.

    Uses the same conversion rules as the CLI: PDF, DOC/DOCX, RTF, images,
    otherwise treats it as UTF-8 text.
    """
    from sanitize_text.utils.normalize import normalize_pdf_text

    return helpers.read_uploaded_file_to_text(
        upload_path,
        pdf_backend=pdf_backend,
        preconvert_module=preconvert,
        normalize_pdf_text_func=normalize_pdf_text,
    )


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
        request_verbose = bool(data.get("verbose", False))
        app_verbose = bool(current_app.config.get("SANITIZE_VERBOSE", False))
        effective_verbose = app_verbose or request_verbose

        if not input_text:
            return jsonify({"error": "No text provided"}), 400

        per_locale_selection = _build_locale_selections(selected_detectors)
        multi_result = run_multi_locale_scrub(
            text=input_text,
            locale=locale,
            per_locale_detectors=per_locale_selection,
            custom_text=custom,
            cleanup=cleanup,
            cleanup_func=cleanup_output,
            verbose=effective_verbose,
            include_filth=effective_verbose,
        )

        results: list[dict[str, object]] = []
        for item in multi_result.results:
            payload: dict[str, object] = {
                "locale": item.locale,
                "text": item.text,
            }
            if request_verbose and item.filth is not None:
                payload["filth"] = [
                    {
                        "type": getattr(f, "type", ""),
                        "text": getattr(f, "text", ""),
                        "replacement": getattr(f, "replacement_string", ""),
                    }
                    for f in item.filth
                ]
            results.append(payload)

        if not results:
            return jsonify({"error": "All processing attempts failed"}), 500

        if effective_verbose:
            _log_verbose_summary("text", raw_text=input_text, result=multi_result)

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
        request_verbose = request.form.get("verbose", "false").lower() in {"1", "true", "yes", "on"}
        app_verbose = bool(current_app.config.get("SANITIZE_VERBOSE", False))
        effective_verbose = app_verbose or request_verbose

        # detectors may come as repeated fields or comma/space separated
        detectors_fields: list[str] = request.form.getlist("detectors") or []
        if not detectors_fields:
            raw = request.form.get("detectors", "")
            if raw:
                detectors_fields = [t for t in raw.replace(",", " ").split() if t]

        per_locale_selection = _build_locale_selections(detectors_fields or None)
        multi_result = run_multi_locale_scrub(
            text=input_text,
            locale=locale,
            per_locale_detectors=per_locale_selection,
            custom_text=custom,
            cleanup=cleanup,
            cleanup_func=cleanup_output,
            verbose=effective_verbose,
            include_filth=effective_verbose,
        )

        results: list[dict[str, object]] = []
        for item in multi_result.results:
            payload: dict[str, object] = {
                "locale": item.locale,
                "text": item.text,
            }
            if request_verbose and item.filth is not None:
                payload["filth"] = [
                    {
                        "type": getattr(f, "type", ""),
                        "text": getattr(f, "text", ""),
                        "replacement": getattr(f, "replacement_string", ""),
                    }
                    for f in item.filth
                ]
            results.append(payload)

        if not results:
            return jsonify({"error": "All processing attempts failed"}), 500

        if effective_verbose:
            _log_verbose_summary("file", raw_text=input_text, result=multi_result)

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
        multi_result = run_multi_locale_scrub(
            text=input_text,
            locale=locale,
            per_locale_detectors=per_locale_selection,
            custom_text=custom,
            cleanup=cleanup,
            cleanup_func=cleanup_output,
            verbose=False,
            include_filth=False,
        )

        interim_results: list[dict[str, str]] = [
            {"locale": item.locale, "text": item.text} for item in multi_result.results
        ]

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
        multi_result = run_multi_locale_scrub(
            text=input_text,
            locale=locale,
            per_locale_detectors=per_locale_selection,
            custom_text=custom,
            cleanup=cleanup,
            cleanup_func=cleanup_output,
            verbose=False,
            include_filth=False,
        )

        interim_results: list[dict[str, str]] = [
            {"locale": item.locale, "text": item.text} for item in multi_result.results
        ]

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
