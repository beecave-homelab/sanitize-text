"""Output writers implementing the Strategy pattern.

Each writer converts scrubbed text into a concrete artifact (txt, docx, pdf).
This extracts side-effectful I/O from the CLI so core logic remains clean.
"""

from __future__ import annotations

import abc
from pathlib import Path
from typing import Protocol


class OutputWriter(Protocol):
    """Common interface for all writers."""

    def write(self, text: str, output: str | Path, **_: object) -> None:
        """Write *text* to a UTF-8 file."""
        """Write *text* to *output* path."""


class _BaseWriter(abc.ABC):
    """Abstract helper base with path handling."""

    def _prepare_path(self, output: str | Path) -> Path:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path


class TxtWriter(_BaseWriter):
    """Write plain UTF-8 text files.

    Args:
        text: The text to write
        output: The output file path
    """

    def write(self, text: str, output: str | Path, **kwargs: object) -> None:  # noqa: D401
        """Write *text* to a UTF-8 file.

        Args:
            text: The text to write.
            output: The output file path.
            **kwargs: Additional writer-specific options (unused).
        """
        path = self._prepare_path(output)
        path.write_text(text, encoding="utf-8")


class DocxWriter(_BaseWriter):
    """Write a simple DOCX with one paragraph per line."""

    def write(self, text: str, output: str | Path, **kwargs: object) -> None:  # noqa: D401
        """Write *text* to a DOCX file.

        Args:
            text: The text to write
            output: The output file path
            **kwargs: Additional writer-specific options (unused).

        Raises:
            RuntimeError: If python-docx is not installed
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
    """Write a simple PDF using reportlab.

    Args:
        text: The text to write
        output: The output file path
        pdf_mode: The PDF mode (pre/para)
        pdf_font: The PDF font
        font_size: The font size

    Raises:
        RuntimeError: If reportlab >=4.4.4 is not installed
    """

    def write(
        self,
        text: str,
        output: str | Path,
        *,
        pdf_mode: str = "pre",
        pdf_font: str | None = None,
        font_size: int = 11,
    ) -> None:
        """Write *text* to a PDF via ReportLab (supports pre/para modes).

        Args:
            text: The text to write
            output: The output file path
            pdf_mode: The PDF mode (pre/para)
            pdf_font: The PDF font
            font_size: The font size

        Raises:
            RuntimeError: If reportlab >=4.4.4 is not installed
        """
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
    "docx": DocxWriter(),
    "pdf": PdfWriter(),
}


def get_writer(fmt: str) -> OutputWriter:
    """Return an `OutputWriter` for *fmt*.

    Args:
        fmt: Desired format string (txt, docx, pdf).

    Returns:
        An `OutputWriter` instance.

    Raises:
        ValueError: If *fmt* is unsupported.
    """
    key = fmt.lower()
    if key not in _WRITERS:
        raise ValueError(f"Unsupported output format '{fmt}'")
    return _WRITERS[key]
