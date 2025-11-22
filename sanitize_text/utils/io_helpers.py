"""Shared I/O helpers for converting files to text.

These helpers are intentionally free of CLI and Web framework dependencies so
that both the Web UI and CLI can reuse the same conversion logic.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def read_file_to_text(
    upload_path: Path,
    *,
    pdf_backend: str = "markitdown",
    preconvert_module: Any,
    normalize_pdf_text_func: Any,
) -> str:
    """Return text extracted from a file path.

    Uses the same conversion rules as the CLI and Web UI: PDF, DOC/DOCX, RTF,
    images, otherwise treats it as UTF-8 text.

    Args:
        upload_path: Path to the input file.
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
    ext = upload_path.suffix.lower()
    if ext == ".pdf":
        backend = (pdf_backend or "markitdown").lower()
        if backend == "pymupdf4llm":
            try:
                import pymupdf4llm  # type: ignore[import]
            except Exception:  # noqa: BLE001
                raw_md = preconvert_module.to_markdown(str(upload_path))
            else:
                raw_md = pymupdf4llm.to_markdown(str(upload_path))
        else:
            raw_md = preconvert_module.to_markdown(str(upload_path))
        return normalize_pdf_text_func(raw_md, title=None)
    if ext in {".doc", ".docx"}:
        return preconvert_module.docx_to_text(str(upload_path))
    if ext == ".rtf":
        return preconvert_module.rtf_to_text(str(upload_path))
    if ext in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}:
        return preconvert_module.image_to_text(str(upload_path))
    return upload_path.read_text(encoding="utf-8", errors="replace")
