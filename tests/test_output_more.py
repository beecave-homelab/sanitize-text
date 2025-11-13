"""Additional tests for sanitize_text.output to cover happy paths and branches."""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

from sanitize_text.output import DocxWriter, PdfWriter


def test_docx_writer_happy_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """DocxWriter writes paragraphs and saves via stub docx module."""
    # Build a minimal docx stub
    docx_mod = types.SimpleNamespace()

    class _Doc:
        def __init__(self) -> None:
            self.paragraphs: list[str] = []

        def add_paragraph(self, text: str) -> None:
            self.paragraphs.append(text)

        def save(self, filename: str) -> None:  # noqa: D401 - test stub
            Path(filename).write_text("DOCX" + "\n".join(self.paragraphs), encoding="utf-8")

    docx_mod.Document = _Doc
    monkeypatch.setitem(sys.modules, "docx", docx_mod)

    writer = DocxWriter()
    out = tmp_path / "out.docx"
    writer.write("L1\nL2", out)
    assert out.exists()
    assert "L1" in out.read_text(encoding="utf-8")


def _install_fake_reportlab(monkeypatch: pytest.MonkeyPatch) -> None:
    """Install minimal stubbed reportlab modules into sys.modules (copy)."""
    # reportlab.lib.pagesizes
    lib_pagesizes = types.ModuleType("reportlab.lib.pagesizes")
    lib_pagesizes.A4 = (595.27, 841.89)

    # reportlab.lib.styles
    class ParagraphStyle:
        def __init__(self, **kwargs):  # noqa: ANN003 - stub
            self.kwargs = kwargs

    def getSampleStyleSheet():  # noqa: N802 - mimic external API
        return {"BodyText": object()}

    lib_styles = types.ModuleType("reportlab.lib.styles")
    lib_styles.ParagraphStyle = ParagraphStyle
    lib_styles.getSampleStyleSheet = getSampleStyleSheet

    # reportlab.lib.units
    lib_units = types.ModuleType("reportlab.lib.units")
    lib_units.cm = 28.35

    # reportlab.pdfbase.pdfmetrics and .ttfonts
    pdfbase_pdfmetrics = types.ModuleType("reportlab.pdfbase.pdfmetrics")

    def registerfont(font):  # noqa: ANN001 - test shim
        return None

    pdfbase_pdfmetrics.registerfont = registerfont

    pdfbase_ttfonts = types.ModuleType("reportlab.pdfbase.ttfonts")

    class TTFont:
        def __init__(self, name: str, path: str) -> None:  # noqa: D401
            self.name = name
            self.path = path

    pdfbase_ttfonts.TTFont = TTFont

    # reportlab.platypus classes
    class _Element:
        def __init__(self, *args, **kwargs):  # noqa: ANN003 - stub
            self.args = args
            self.kwargs = kwargs

    class SimpleDocTemplate:
        def __init__(self, filename: str, **kwargs):  # noqa: ANN003 - stub
            self.filename = filename
            self.kwargs = kwargs

        def build(self, story):  # noqa: ANN001 - stub
            Path(self.filename).write_text("PDF", encoding="utf-8")

    platypus = types.ModuleType("reportlab.platypus")
    platypus.Paragraph = _Element
    platypus.Preformatted = _Element
    platypus.SimpleDocTemplate = SimpleDocTemplate
    platypus.Spacer = _Element

    # Register in sys.modules
    monkeypatch.setitem(sys.modules, "reportlab.lib.pagesizes", lib_pagesizes)
    monkeypatch.setitem(sys.modules, "reportlab.lib.styles", lib_styles)
    monkeypatch.setitem(sys.modules, "reportlab.lib.units", lib_units)
    monkeypatch.setitem(sys.modules, "reportlab.pdfbase.pdfmetrics", pdfbase_pdfmetrics)
    monkeypatch.setitem(sys.modules, "reportlab.pdfbase.ttfonts", pdfbase_ttfonts)
    monkeypatch.setitem(sys.modules, "reportlab.platypus", platypus)


@pytest.mark.parametrize(
    "pdf_mode, text",
    [
        ("para", "\n\n"),  # empty story fallback
        ("para", "  \n\n  "),
    ],
)
def test_pdf_writer_para_fallback_and_font(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, pdf_mode: str, text: str
) -> None:
    """PDF para-mode fallback (empty story) and font registration paths.

    Also pass font_size as string to exercise conversion branch.
    """
    _install_fake_reportlab(monkeypatch)
    writer = PdfWriter()
    out = tmp_path / "para_empty.pdf"
    writer.write(text, out, pdf_mode=pdf_mode, pdf_font="/tmp/Font.ttf", font_size="13")
    assert out.exists() and out.read_text(encoding="utf-8") == "PDF"
