"""Tests for DOCX/PDF writers in :mod:`sanitize_text.output`."""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

from sanitize_text.output import DocxWriter, PdfWriter


def test_docx_writer_raises_when_missing_dependency(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """DocxWriter should raise RuntimeError when python-docx is unavailable."""
    writer = DocxWriter()

    real_import = __import__

    def fake_import(name: str, *args, **kwargs):  # noqa: ANN401 - test shim
        if name == "docx":
            raise ImportError("no docx")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", fake_import)

    with pytest.raises(RuntimeError):
        writer.write("x", tmp_path / "out.docx")


def test_pdf_writer_raises_when_missing_reportlab(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """PdfWriter should raise RuntimeError when reportlab is unavailable."""
    writer = PdfWriter()

    real_import = __import__

    def fake_import(name: str, *args, **kwargs):  # noqa: ANN401 - test shim
        if name.startswith("reportlab"):
            raise ImportError("no reportlab")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", fake_import)

    with pytest.raises(RuntimeError):
        writer.write("x", tmp_path / "out.pdf")


def _install_fake_reportlab(monkeypatch: pytest.MonkeyPatch) -> None:
    """Install minimal stubbed reportlab modules into sys.modules."""
    # reportlab.lib.pagesizes
    lib_pagesizes = types.ModuleType("reportlab.lib.pagesizes")
    lib_pagesizes.A4 = (595.27, 841.89)  # just a tuple placeholder

    # reportlab.lib.styles
    class ParagraphStyle:
        def __init__(self, **kwargs):  # noqa: ANN003 - minimal stub
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
        def __init__(self, *args, **kwargs):  # noqa: ANN003 - minimal stub
            self.args = args
            self.kwargs = kwargs

    class SimpleDocTemplate:
        def __init__(self, filename: str, **kwargs):  # noqa: ANN003 - minimal stub
            self.filename = filename
            self.kwargs = kwargs

        def build(self, story):  # noqa: ANN001 - minimal stub
            # Write something to the target path to simulate PDF output
            Path(self.filename).write_text("PDF", encoding="utf-8")

    platypus = types.ModuleType("reportlab.platypus")
    platypus.Paragraph = _Element
    platypus.Preformatted = _Element
    platypus.SimpleDocTemplate = SimpleDocTemplate
    platypus.Spacer = _Element

    # Register all in sys.modules
    monkeypatch.setitem(sys.modules, "reportlab.lib.pagesizes", lib_pagesizes)
    monkeypatch.setitem(sys.modules, "reportlab.lib.styles", lib_styles)
    monkeypatch.setitem(sys.modules, "reportlab.lib.units", lib_units)
    monkeypatch.setitem(sys.modules, "reportlab.pdfbase.pdfmetrics", pdfbase_pdfmetrics)
    monkeypatch.setitem(sys.modules, "reportlab.pdfbase.ttfonts", pdfbase_ttfonts)
    monkeypatch.setitem(sys.modules, "reportlab.platypus", platypus)


def test_pdf_writer_pre_mode_with_fake_reportlab(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """PDF writer writes a file in pre mode using fake reportlab stubs."""
    _install_fake_reportlab(monkeypatch)
    writer = PdfWriter()
    out = tmp_path / "pre.pdf"
    writer.write("Hello & <world>", out, pdf_mode="pre", font_size=10)
    assert out.exists() and out.read_text(encoding="utf-8") == "PDF"


def test_pdf_writer_para_mode_with_fake_reportlab(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """PDF writer writes a file in paragraph mode using fake reportlab stubs."""
    _install_fake_reportlab(monkeypatch)
    writer = PdfWriter()
    out = tmp_path / "para.pdf"
    writer.write("Para one\n\nPara <two>", out, pdf_mode="para", font_size=12)
    assert out.exists() and out.read_text(encoding="utf-8") == "PDF"
