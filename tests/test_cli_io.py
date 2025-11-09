"""Tests for CLI I/O helper functions."""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from sanitize_text.cli import io as cli_io


def test_infer_output_format_explicit() -> None:
    """Explicit format should win regardless of output path."""
    assert cli_io.infer_output_format(None, "pdf") == "pdf"


def test_infer_output_format_from_ext(tmp_path: Path) -> None:
    """Infer format from output extension when not explicitly provided."""
    out = tmp_path / "file.docx"
    assert cli_io.infer_output_format(str(out), None) == "docx"
    out = tmp_path / "file.pdf"
    assert cli_io.infer_output_format(str(out), None) == "pdf"
    out = tmp_path / "file.txt"
    assert cli_io.infer_output_format(str(out), None) == "txt"


def test_maybe_cleanup_noop() -> None:
    """When disabled, cleanup should be a no-op."""
    text = "Hello\n"
    assert cli_io.maybe_cleanup(text, enabled=False) == text


def test_read_input_source_text() -> None:
    """Prefer --text when provided."""
    got = cli_io.read_input_source(
        text="abc",
        input_path=None,
        append=False,
        output_path=None,
    )
    assert got == "abc"


def test_read_input_source_file(tmp_path: Path) -> None:
    """Read from file path when provided."""
    p = tmp_path / "in.txt"
    p.write_text("content", encoding="utf-8")
    got = cli_io.read_input_source(
        text=None,
        input_path=str(p),
        append=False,
        output_path=None,
    )
    assert got == "content"


def test_read_input_source_append_requires_output() -> None:
    """Append mode requires output path to be set."""
    with pytest.raises(ValueError):
        cli_io.read_input_source(
            text=None, input_path=None, append=True, output_path=None
        )


def test_read_input_source_append_reads_output(tmp_path: Path) -> None:
    """Append mode reads from the existing output file."""
    out = tmp_path / "out.txt"
    out.write_text("prev", encoding="utf-8")
    got = cli_io.read_input_source(
        text=None,
        input_path=None,
        append=True,
        output_path=str(out),
    )
    assert got == "prev"


def test_read_input_source_pdf(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """PDF input is pre-converted to Markdown then normalized."""
    p = tmp_path / "in.pdf"
    p.write_text("%PDF-1.4", encoding="utf-8")

    class DummyPreconvert:
        @staticmethod
        def to_markdown(path: str) -> str:  # noqa: ARG003 - external API shape
            assert path == str(p)
            return "# Title\nContent"

    def dummy_norm(md: str, *, title: str | None) -> str:  # noqa: ARG001
        return md

    monkeypatch.setattr(cli_io, "preconvert", DummyPreconvert)
    monkeypatch.setattr(cli_io, "normalize_pdf_text", dummy_norm)

    got = cli_io.read_input_source(
        text=None, input_path=str(p), append=False, output_path=None
    )
    assert got.startswith("# Title")


def test_read_input_source_stdin(monkeypatch: pytest.MonkeyPatch) -> None:
    """Read from stdin when not a tty and no other inputs provided."""
    class FakeStdin(io.StringIO):
        def isatty(self) -> bool:  # type: ignore[override]
            return False

    data = "from-stdin"
    fake = FakeStdin(data)
    monkeypatch.setattr("sys.stdin", fake)

    got = cli_io.read_input_source(
        text=None, input_path=None, append=False, output_path=None
    )
    assert got == data


def test_write_output_txt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Default to txt output in ./output when no path is provided."""
    # Ensure cwd for default output path
    monkeypatch.chdir(tmp_path)
    out = cli_io.write_output(
        text="hello",
        output=None,
        fmt="txt",
        pdf_mode="pre",
        pdf_font=None,
        font_size=11,
    )
    p = Path(out)
    assert p.exists()
    assert p.read_text(encoding="utf-8").startswith("hello")
