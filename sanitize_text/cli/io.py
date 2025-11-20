"""I/O helpers for the CLI.

This module centralizes input reading, output format inference, optional
cleanup, and writing artifacts so the CLI command definitions remain lean.
"""

from __future__ import annotations

import os
from pathlib import Path

from sanitize_text.output import get_writer
from sanitize_text.utils import preconvert
from sanitize_text.utils.cleanup import cleanup_output
from sanitize_text.utils.normalize import normalize_pdf_text


def read_input_source(
    *,
    text: str | None,
    input_path: str | None,
    append: bool,
    output_path: str | None,
    pdf_backend: str = "pymupdf4llm",
) -> str:
    """Return input text resolved from CLI sources.

    Args:
        text: Inline text provided via ``--text``/``-t``.
        input_path: Path to a file provided via ``--input``/``-i``.
        append: Whether to treat the output file as input when ``True``.
        output_path: Path used when ``append`` is set.
        pdf_backend: Backend to use for PDF pre-conversion ("pymupdf4llm" or "markitdown").

    Returns:
        str: Materialized input text.

    Raises:
        ValueError: If append is requested without an output path or if no
        usable input source is provided.
    """
    if append and not output_path:
        raise ValueError("--append requires --output to be specified")

    if append and output_path and os.path.exists(output_path):
        return Path(output_path).read_text(encoding="utf-8", errors="replace")

    if input_path:
        ext = Path(input_path).suffix.lower()
        if ext == ".pdf":
            backend = (pdf_backend or "pymupdf4llm").lower()
            if backend == "pymupdf4llm":
                try:
                    import pymupdf4llm  # type: ignore[import]
                except Exception:  # noqa: BLE001
                    raw_md = preconvert.to_markdown(input_path)
                else:
                    raw_md = pymupdf4llm.to_markdown(input_path)
            else:
                raw_md = preconvert.to_markdown(input_path)
            return normalize_pdf_text(raw_md, title=None)
        if ext in {".doc", ".docx"}:
            return preconvert.docx_to_text(input_path)
        if ext == ".rtf":
            return preconvert.rtf_to_text(input_path)
        if ext in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}:
            return preconvert.image_to_text(input_path)
        return Path(input_path).read_text(encoding="utf-8", errors="replace")

    if text is not None:
        return text

    # stdin
    try:
        import sys

        if not sys.stdin.isatty():
            return sys.stdin.read()
    except Exception:  # pragma: no cover
        pass

    raise ValueError("No input provided. Use --text, --input, or pipe input.")


def infer_output_format(output: str | None, explicit_format: str | None) -> str:
    """Return the output format resolved from CLI arguments.

    Args:
        output: Destination path chosen by the user.
        explicit_format: Explicit ``--output-format`` flag.

    Returns:
        str: Resolved output format (``"txt"``, ``"docx"``, or ``"pdf"``).
    """
    if explicit_format:
        return explicit_format
    if output is None:
        return "txt"
    ext = Path(output).suffix.lower()
    if ext in {".doc", ".docx"}:
        return "docx"
    if ext == ".pdf":
        return "pdf"
    if ext in {".md", ".markdown"}:
        return "md"
    return "txt"


def maybe_cleanup(text: str, enabled: bool) -> str:
    """Return text after optional cleanup.

    Args:
        text: Text to post-process.
        enabled: When ``True`` the cleanup pipeline is executed.

    Returns:
        str: Cleaned text (or the original text when cleanup is disabled).
    """
    return cleanup_output(text) if enabled else text


def write_output(
    *,
    text: str,
    output: str | None,
    fmt: str,
    pdf_mode: str,
    pdf_font: str | None,
    font_size: int,
) -> str:
    """Write scrubbed text and return the path used.

    Args:
        text: Scrubbed text to persist.
        output: Optional output path supplied by the user.
        fmt: Output format resolved from CLI flags.
        pdf_mode: Layout mode for PDF output.
        pdf_font: Optional font path for PDF output.
        font_size: Font size used for PDF output.

    Returns:
        str: Final path containing the written artifact.
    """
    if output is None:
        output_dir = Path.cwd() / "output"
        output_dir.mkdir(exist_ok=True)
        output = str(output_dir / "scrubbed.txt")

    writer = get_writer(fmt)
    write_kwargs: dict[str, object] = {}
    if fmt == "pdf":
        write_kwargs = {
            "pdf_mode": pdf_mode,
            "pdf_font": pdf_font,
            "font_size": font_size,
        }
    writer.write(text, output, **write_kwargs)
    return output
