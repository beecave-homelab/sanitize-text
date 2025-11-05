"""Lightweight pre-conversion utilities for binary/rich formats.

This module converts PDFs, DOC/DOCX, RTF, and images to plain UTF-8 text
using CPU-only tools. It prefers lightweight Python libraries when available
and falls back to common system CLIs. OCR for images uses the `tesseract`
binary via its CLI.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path


class ConversionError(Exception):
    """Raised when a pre-conversion tool is missing or fails.

    This module provides lightweight helpers to convert binary/rich formats
    (PDF, DOC/DOCX, RTF, images) into plain UTF-8 text by delegating to
    commonly available CPU-only system tools.
    """


def _run_command(cmd: list[str]) -> str:
    """Run a command and return stdout as UTF-8 text.

    Args:
        cmd: Command and arguments to execute.

    Returns:
        Extracted text from stdout.

    Raises:
        ConversionError: If the command fails.
    """
    try:
        proc = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
        )
    except FileNotFoundError as exc:  # tool missing
        raise ConversionError(f"Required tool not found: {cmd[0]}") from exc
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode("utf-8", errors="replace") if exc.stderr else ""
        raise ConversionError(f"Conversion failed for {cmd[0]}: {stderr}") from exc

    return proc.stdout.decode("utf-8", errors="replace")


def _require(tool: str) -> None:
    """Ensure a required CLI tool is available on PATH.

    Args:
        tool: Executable name to check.

    Raises:
        ConversionError: If the tool cannot be located.
    """
    if shutil.which(tool) is None:
        msg = (
            f"'{tool}' is required but was not found on PATH. "
            "Please install it first."
        )
        raise ConversionError(msg)


def pdf_to_text(path: str | Path) -> str:
    """Extract text from a PDF.

    Args:
        path: Path to a PDF file.

    Returns:
        Extracted plain text.

    Raises:
        ConversionError: If no available method for PDF conversion.
    """
    p = str(Path(path))
    # Prefer external CLI if available (usually quieter & cleaner)
    if shutil.which("pdftotext") is not None:
        return _run_command(["pdftotext", p, "-"])

    # Fallback to pdfminer.six with reduced logging noise
    try:
        from pdfminer.high_level import extract_text  # type: ignore

        logger = logging.getLogger("pdfminer")
        prev = logger.level
        try:
            logger.setLevel(logging.ERROR)
            text = extract_text(p) or ""
        finally:
            logger.setLevel(prev)
        return text
    except Exception as exc:
        raise ConversionError(
            "No available method for PDF conversion (pdftotext CLI or pdfminer.six)."
        ) from exc


def docx_to_text(path: str | Path) -> str:
    """Extract text from a DOC/DOCX file.

    Args:
        path: Path to a DOC/DOCX file.

    Returns:
        Extracted plain text.

    Raises:
        ConversionError: If no suitable tool is available or conversion fails.
    """
    p = str(Path(path))
    # Prefer pure-Python library if available
    try:
        import docx  # type: ignore

        document = docx.Document(p)
        parts: list[str] = []
        for para in document.paragraphs:
            if para.text:
                parts.append(para.text)
        return "\n".join(parts)
    except Exception:
        # Fallback to CLI tools
        if shutil.which("docx2txt") is not None:
            return _run_command(["docx2txt", p, "-"])
        if shutil.which("pandoc") is not None:
            return _run_command(["pandoc", p, "-t", "plain"])
        msg = (
            "No available method for DOC/DOCX conversion "
            "(python-docx, docx2txt, or pandoc)."
        )
        raise ConversionError(msg)


def rtf_to_text(path: str | Path) -> str:
    """Extract text from an RTF file.

    Args:
        path: Path to an RTF file.

    Returns:
        Extracted plain text.

    Raises:
        ConversionError: If no suitable method exists or conversion fails.
    """
    p = str(Path(path))
    # Prefer pure-Python library if available
    try:
        from striprtf.striprtf import rtf_to_text as _rtf_to_text  # type: ignore

        with open(p, encoding="utf-8", errors="ignore") as f:
            data = f.read()
        return _rtf_to_text(data)
    except Exception:
        # Fallback to pandoc
        if shutil.which("pandoc") is not None:
            return _run_command(["pandoc", p, "-t", "plain"])
        msg = "No available method for RTF conversion (striprtf or pandoc)."
        raise ConversionError(msg)


def image_to_text(path: str | Path, *, lang: str | None = None) -> str:
    """Extract text from an image using tesseract OCR.

    Args:
        path: Path to an image file.
        lang: Optional tesseract language code (e.g., 'eng', 'nld').

    Returns:
        Extracted plain text.
    """
    _require("tesseract")
    p = str(Path(path))
    cmd = ["tesseract", p, "stdout"]
    if lang:
        cmd.extend(["-l", lang])
    return _run_command(cmd)


def convert_file(fmt: str, path: str | Path, *, lang: str | None = None) -> str:
    """Convert a file of a given format to plain text.

    Args:
        fmt: Format hint (one of: 'pdf', 'docx', 'doc', 'rtf', 'image').
        path: Path to the source file.
        lang: Optional OCR language for images.

    Returns:
        Extracted plain text.

    Raises:
        ConversionError: If conversion cannot be performed.
    """
    fmt_lc = fmt.lower()
    if fmt_lc == "pdf":
        return pdf_to_text(path)
    if fmt_lc in {"doc", "docx"}:
        return docx_to_text(path)
    if fmt_lc == "rtf":
        return rtf_to_text(path)
    if fmt_lc == "image":
        return image_to_text(path, lang=lang)
    raise ConversionError(f"Unsupported format: {fmt}")
