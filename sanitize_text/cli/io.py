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
) -> str:
    """Return input text selected from CLI sources.

    Args:
        text: Inline text from --text/-t.
        input_path: Path to an input file.
        append: Whether to re-use output file as input.
        output_path: Output path used when append is true.

    Returns:
        The resolved input text.

    Raises:
        ValueError: If append is requested without output, or input is missing.
    """
    if append and not output_path:
        raise ValueError("--append requires --output to be specified")

    if append and output_path and os.path.exists(output_path):
        return Path(output_path).read_text(encoding="utf-8", errors="replace")

    if input_path:
        ext = Path(input_path).suffix.lower()
        if ext == ".pdf":
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
    """Infer output format from explicit flag or output file extension.

    Returns:
        The resolved output format string ("txt", "docx", or "pdf").
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
    return "txt"


def maybe_cleanup(text: str, enabled: bool) -> str:
    """Optionally apply cleanup to the final output text.

    Returns:
        The cleaned (or original) output text depending on ``enabled``.
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
    """Write output using the selected writer and return the output path.

    Returns:
        The final output path used for writing the artifact.
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
