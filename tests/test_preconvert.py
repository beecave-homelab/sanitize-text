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


@patch("subprocess.run")
def test_run_command_file_not_found(run: MagicMock) -> None:
    """_run_command raises ConversionError when tool is missing."""
    run.side_effect = FileNotFoundError("tool not found")
    with pytest.raises(pc.ConversionError, match="Required tool not found"):
        pc._run_command(["missing_tool"])


@patch("subprocess.run")
def test_run_command_process_error(run: MagicMock) -> None:
    """_run_command raises ConversionError when subprocess fails."""
    # Mock a CalledProcessError with stderr
    from subprocess import CalledProcessError

    error = CalledProcessError(1, ["failing_tool"], stderr=b"error message")
    run.side_effect = error
    with pytest.raises(pc.ConversionError, match="Conversion failed for"):
        pc._run_command(["failing_tool"])


@patch("shutil.which", return_value=None)
def test_require_missing_tool(which: MagicMock) -> None:
    """_require raises ConversionError when tool is not on PATH."""
    with pytest.raises(pc.ConversionError, match="'missing_tool' is required"):
        pc._require("missing_tool")


@patch("shutil.which", return_value="/usr/bin/tool")
def test_require_tool_present(which: MagicMock) -> None:  # noqa: ARG001
    """_require does nothing when tool is present."""
    pc._require("tool")  # Should not raise


@patch("shutil.which", return_value=None)
@patch("builtins.__import__")
def test_pdf_to_text_pdfminer_fallback(mock_import: MagicMock, which: MagicMock) -> None:
    """pdf_to_text falls back to pdfminer when pdftotext is missing."""
    # Mock pdfminer import to raise an exception
    mock_import.side_effect = ImportError("No pdfminer")
    with pytest.raises(pc.ConversionError, match="No available method for PDF conversion"):
        pc.pdf_to_text("file.pdf")


@patch("shutil.which", return_value=None)
@patch("builtins.open", create=True)
@patch("builtins.__import__")
def test_rtf_to_text_striprtf_fallback(
    mock_import: MagicMock, mock_open: MagicMock, which: MagicMock
) -> None:
    """rtf_to_text falls back to striprtf when available."""
    # Mock striprtf import
    mock_striprtf = MagicMock()
    mock_striprtf.rtf_to_text.return_value = "stripped rtf text"
    mock_import.return_value = mock_striprtf

    # Mock file reading
    mock_file = MagicMock()
    mock_file.read.return_value = "{\\rtf test}"
    mock_open.return_value.__enter__.return_value = mock_file

    out = pc.rtf_to_text("file.rtf")
    assert out == "stripped rtf text"


@patch("shutil.which", return_value="/usr/bin/tesseract")
@patch("subprocess.run")
def test_image_to_text_without_lang(run: MagicMock, which: MagicMock) -> None:  # noqa: ARG001
    """image_to_text works without language parameter."""
    run.return_value = _mock_completed("ocr text")
    out = pc.image_to_text("img.png")
    assert out == "ocr text"
    # Check that lang was not added to command
    run.assert_called_once_with(["tesseract", "img.png", "stdout"], check=True, capture_output=True)


@patch("sanitize_text.utils.preconvert.MarkItDown")
@patch("pathlib.Path")
def test_to_markdown_success(mock_path: MagicMock, mock_markitdown: MagicMock) -> None:
    """to_markdown successfully converts file using markitdown."""
    # Setup mocks
    mock_path.return_value.__str__ = lambda: "test.pdf"
    mock_result = MagicMock()
    mock_result.text_content = "# Markdown content"
    mock_markitdown_instance = MagicMock()
    mock_markitdown_instance.convert.return_value = mock_result
    mock_markitdown.return_value = mock_markitdown_instance

    out = pc.to_markdown("test.pdf")
    assert out == "# Markdown content"


@patch("sanitize_text.utils.preconvert.MarkItDown")
@patch("pathlib.Path")
def test_to_markdown_failure(mock_path: MagicMock, mock_markitdown: MagicMock) -> None:
    """to_markdown raises ConversionError when markitdown fails."""
    mock_path.return_value.__str__ = lambda: "test.pdf"
    mock_markitdown.side_effect = Exception("Conversion failed")

    with pytest.raises(pc.ConversionError, match="markitdown failed to convert"):
        pc.to_markdown("test.pdf")


@patch("sanitize_text.utils.preconvert.MarkItDown")
@patch("pathlib.Path")
def test_to_markdown_empty_content(mock_path: MagicMock, mock_markitdown: MagicMock) -> None:
    """to_markdown returns empty string when markitdown returns no content."""
    mock_path.return_value.__str__ = lambda: "test.pdf"
    mock_result = MagicMock()
    mock_result.text_content = None
    mock_markitdown_instance = MagicMock()
    mock_markitdown_instance.convert.return_value = mock_result
    mock_markitdown.return_value = mock_markitdown_instance

    out = pc.to_markdown("test.pdf")
    assert out == ""


def test_suppress_fontbbox_logs_context_manager() -> None:
    """_suppress_fontbbox_logs context manager properly manages logging filters."""
    import logging

    logger_root = logging.getLogger()
    logger_pdf = logging.getLogger("pdfminer")

    # Get initial state
    initial_root_filters = len(logger_root.filters)
    initial_pdf_filters = len(logger_pdf.filters)
    initial_pdf_level = logger_pdf.level

    # Use context manager
    with pc._suppress_fontbbox_logs():
        # Filters should be added
        assert len(logger_root.filters) == initial_root_filters + 1
        assert len(logger_pdf.filters) == initial_pdf_filters + 1

    # Filters should be removed after context
    assert len(logger_root.filters) == initial_root_filters
    assert len(logger_pdf.filters) == initial_pdf_filters
    assert logger_pdf.level == initial_pdf_level


def test_fontbbox_filter() -> None:
    """_FontBBoxFilter correctly filters FontBBox messages."""
    import logging

    # Get the filter class from the context manager function
    with pc._suppress_fontbbox_logs():
        # Get the filter that was added
        filter_obj = logging.getLogger().filters[-1]

        # Test filtering
        record1 = logging.LogRecord(
            name="test",
            level=logging.WARNING,
            pathname="",
            lineno=0,
            msg="FontBBox parsed: 4 floats",
            args=(),
            exc_info=None,
        )
        assert not filter_obj.filter(record1)

        record2 = logging.LogRecord(
            name="test",
            level=logging.WARNING,
            pathname="",
            lineno=0,
            msg="FontBBox 4 floats",
            args=(),
            exc_info=None,
        )
        assert not filter_obj.filter(record2)

        record3 = logging.LogRecord(
            name="test",
            level=logging.WARNING,
            pathname="",
            lineno=0,
            msg="Some other message",
            args=(),
            exc_info=None,
        )
        assert filter_obj.filter(record3)
