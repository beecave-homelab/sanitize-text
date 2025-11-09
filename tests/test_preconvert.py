"""Tests for sanitize_text.utils.preconvert.

These tests mock subprocess/which to avoid external tool dependencies.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sanitize_text.utils import preconvert as pc


def _mock_completed(stdout: str = "text", returncode: int = 0) -> MagicMock:
    """Create a mock CompletedProcess-like object with given stdout.

    Returns:
        MagicMock: A mock object with stdout and returncode attributes.
    """
    m = MagicMock()
    m.stdout = stdout.encode("utf-8")
    m.returncode = returncode
    return m


@patch("shutil.which", return_value="/usr/bin/pdftotext")
@patch("subprocess.run")
def test_pdf_to_text_ok(run: MagicMock, which: MagicMock) -> None:  # noqa: ARG001
    """pdf_to_text returns text when tool is present."""
    run.return_value = _mock_completed("pdf text")
    out = pc.pdf_to_text("file.pdf")
    assert out == "pdf text"
    run.assert_called_once()


@patch("shutil.which", return_value=None)
def test_pdf_to_text_missing_tool(which: MagicMock) -> None:
    """pdf_to_text raises when tool is missing."""
    with pytest.raises(pc.ConversionError):
        pc.pdf_to_text("file.pdf")


@patch("subprocess.run")
@patch("shutil.which", side_effect=["/usr/bin/docx2txt", None])
def test_docx_to_text_prefers_docx2txt(which: MagicMock, run: MagicMock) -> None:
    """docx_to_text prefers docx2txt when available."""
    run.return_value = _mock_completed("docx text")
    out = pc.docx_to_text("file.docx")
    assert out == "docx text"
    run.assert_called_once()


@patch("subprocess.run")
@patch("shutil.which", side_effect=[None, "/usr/bin/pandoc"])
def test_docx_to_text_falls_back_to_pandoc(which: MagicMock, run: MagicMock) -> None:
    """docx_to_text falls back to pandoc when docx2txt is absent."""
    run.return_value = _mock_completed("docx text via pandoc")
    out = pc.docx_to_text("file.docx")
    assert out == "docx text via pandoc"


@patch("shutil.which", side_effect=[None, None])
def test_docx_to_text_no_tools(which: MagicMock) -> None:
    """docx_to_text raises when no tool is available."""
    with pytest.raises(pc.ConversionError):
        pc.docx_to_text("file.docx")


@patch("shutil.which", return_value="/usr/bin/pandoc")
@patch("subprocess.run")
def test_rtf_to_text_ok(run: MagicMock, which: MagicMock) -> None:  # noqa: ARG001
    """rtf_to_text returns text via pandoc when present."""
    run.return_value = _mock_completed("rtf text")
    out = pc.rtf_to_text("file.rtf")
    assert out == "rtf text"


@patch("shutil.which", return_value=None)
def test_rtf_to_text_missing_tool(which: MagicMock) -> None:
    """rtf_to_text raises when no method exists."""
    with pytest.raises(pc.ConversionError):
        pc.rtf_to_text("file.rtf")


@patch("shutil.which", return_value="/usr/bin/tesseract")
@patch("subprocess.run")
def test_image_to_text_ok(run: MagicMock, which: MagicMock) -> None:  # noqa: ARG001
    """image_to_text returns OCR text via tesseract."""
    run.return_value = _mock_completed("ocr text")
    out = pc.image_to_text("img.png", lang="eng")
    assert out == "ocr text"
    run.assert_called_once()


@patch("shutil.which", return_value=None)
def test_image_to_text_missing_tool(which: MagicMock) -> None:
    """image_to_text raises when tesseract is missing."""
    with pytest.raises(pc.ConversionError):
        pc.image_to_text("img.png")


@patch("sanitize_text.utils.preconvert.pdf_to_text", return_value="a")
@patch("sanitize_text.utils.preconvert.docx_to_text", return_value="b")
@patch("sanitize_text.utils.preconvert.rtf_to_text", return_value="c")
@patch("sanitize_text.utils.preconvert.image_to_text", return_value="d")
@pytest.mark.parametrize(
    "fmt,expected",
    [("pdf", "a"), ("doc", "b"), ("docx", "b"), ("rtf", "c"), ("image", "d")],
)
def test_convert_file_dispatch(image, rtf, docx, pdf, fmt: str, expected: str) -> None:  # noqa: ANN001
    """convert_file dispatches to the correct converter."""
    assert pc.convert_file(fmt, Path("x")) == expected


def test_convert_file_unsupported() -> None:
    """convert_file raises for unsupported format."""
    with pytest.raises(pc.ConversionError):
        pc.convert_file("unknown", Path("x"))
