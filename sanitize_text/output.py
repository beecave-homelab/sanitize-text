"""Output writers for different artifact formats.

Each writer converts scrubbed text into a concrete artifact (txt, docx, pdf).
This extracts side-effectful I/O from the CLI so core logic remains clean.
"""

from __future__ import annotations

import abc
from pathlib import Path
from typing import Protocol


class OutputWriter(Protocol):
    """Protocol for objects that persist scrubbed text."""

    def write(self, text: str, output: str | Path, **kwargs: object) -> None:
        """Persist ``text`` to ``output``.

        Args:
            text: Scrubbed text to persist.
            output: Destination path for the artifact.
            **kwargs: Writer-specific options (format dependent).
        """


class _BaseWriter(abc.ABC):
    """Abstract base class providing filesystem helpers."""

    def _prepare_path(self, output: str | Path) -> Path:
        """Ensure parent directories exist and return a ``Path`` instance.

        Args:
            output: Destination path provided by the caller.

        Returns:
            Path: Normalized path pointing to the output file.
        """
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path


class TxtWriter(_BaseWriter):
    """Writer implementation for UTF-8 text files."""

    def write(self, text: str, output: str | Path, **kwargs: object) -> None:
        """Persist ``text`` to ``output`` using UTF-8 encoding.

        Args:
            text: Text to write.
            output: Path that will receive the text file.
            **kwargs: Additional writer-specific options (unused).
        """
        path = self._prepare_path(output)
        path.write_text(text, encoding="utf-8")


class DocxWriter(_BaseWriter):
    """Writer implementation for DOCX artifacts."""

    def write(self, text: str, output: str | Path, **kwargs: object) -> None:
        """Persist ``text`` to ``output`` as a DOCX document.

        Args:
            text: Text to write.
            output: Path that will receive the DOCX document.
            **kwargs: Additional writer-specific options (unused).

        Raises:
            RuntimeError: If ``python-docx`` is not available.
        """
        try:
            import docx  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise RuntimeError("python-docx is required for DOCX output") from exc

        doc = docx.Document()
        for line in text.splitlines():
            doc.add_paragraph(line)
        self._prepare_path(output)
        doc.save(str(output))


class PdfWriter(_BaseWriter):
    """Writer implementation for PDF artifacts using ReportLab."""

    def write(self, text: str, output: str | Path, **kwargs: object) -> None:
        """Persist ``text`` to ``output`` as a PDF document.

        Args:
            text: Text to write.
            output: Path that will receive the PDF document.
            **kwargs: Writer options such as ``pdf_mode``, ``pdf_font`` and
                ``font_size``.

        Raises:
            RuntimeError: If the ReportLab dependency is missing.
        """
        pdf_mode = str(kwargs.get("pdf_mode", "pre"))
        pdf_font_value = kwargs.get("pdf_font")
        pdf_font = str(pdf_font_value) if pdf_font_value is not None else None
        font_size_value = kwargs.get("font_size", 11)
        if isinstance(font_size_value, int):
            font_size = font_size_value
        else:
            try:
                font_size = int(font_size_value)
            except (TypeError, ValueError):  # pragma: no cover - defensive fallback
                font_size = 11

        try:
            from reportlab.lib.pagesizes import A4  # type: ignore
            from reportlab.lib.styles import (  # type: ignore
                ParagraphStyle,
                getSampleStyleSheet,
            )
            from reportlab.lib.units import cm  # type: ignore
            from reportlab.pdfbase import pdfmetrics  # type: ignore
            from reportlab.pdfbase.ttfonts import TTFont  # type: ignore
            from reportlab.platypus import (
                Paragraph,
                Preformatted,
                SimpleDocTemplate,
                Spacer,
            )  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise RuntimeError("reportlab >=4.4.4 is required for PDF output") from exc

        from sanitize_text.utils.pdf import normalize_text_for_pdf  # local import

        output_path = self._prepare_path(output)

        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            leftMargin=2 * cm,
            rightMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
            title="Sanitized Output",
            author="sanitize-text",
        )
        styles = getSampleStyleSheet()
        font_name = "Helvetica"
        if pdf_font:
            try:
                pdfmetrics.registerFont(TTFont("CustomTTF", pdf_font))
                font_name = "CustomTTF"
            except Exception:  # pragma: no cover
                font_name = "Helvetica"

        style = ParagraphStyle(
            name="SanitizeTextBody",
            parent=styles["BodyText"],
            fontName=font_name,
            fontSize=font_size,
            leading=int(font_size * 1.2),
        )

        normalized = normalize_text_for_pdf(text, pdf_mode)
        story: list[str] = []
        if pdf_mode == "pre":
            safe = normalized.replace("&", "&amp;")
            safe = safe.replace("<", "&lt;").replace(">", "&gt;")
            story.append(Preformatted(safe, style))
        else:
            for p in [p for p in normalized.split("\n\n") if p.strip()]:
                safe = p.replace("&", "&amp;")
                safe = safe.replace("<", "&lt;").replace(">", "&gt;")
                story.append(Paragraph(safe, style))
                story.append(Spacer(1, 0.4 * cm))
        if not story:
            from reportlab.platypus import Paragraph  # type: ignore

            story.append(Paragraph("", style))
        doc.build(story)


_WRITERS: dict[str, OutputWriter] = {
    "txt": TxtWriter(),
    "md": TxtWriter(),
    "markdown": TxtWriter(),
    "docx": DocxWriter(),
    "pdf": PdfWriter(),
}


def get_writer(fmt: str) -> OutputWriter:
    """Return a writer for the requested format.

    Args:
        fmt: Desired format string (``"txt"``, ``"md"``, ``"docx"``, or ``"pdf"``).

    Returns:
        OutputWriter: Writer implementation associated with ``fmt``.

    Raises:
        ValueError: If ``fmt`` is unsupported.
    """
    key = fmt.lower()
    if key not in _WRITERS:
        raise ValueError(f"Unsupported output format '{fmt}'")
    return _WRITERS[key]
