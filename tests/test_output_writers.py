"""Tests for :mod:`sanitize_text.output` writer selection and TXT writing."""

from __future__ import annotations

from pathlib import Path

import pytest

from sanitize_text.output import TxtWriter, get_writer


def test_get_writer_supported_and_unsupported() -> None:
    """get_writer returns TxtWriter for 'txt' and raises for unknown formats."""
    txt = get_writer("txt")
    assert isinstance(txt, TxtWriter)

    with pytest.raises(ValueError):
        get_writer("unknown")


def test_txt_writer_writes_and_creates_parent(tmp_path: Path) -> None:
    """TxtWriter writes file contents and creates parent directories as needed."""
    writer = TxtWriter()
    outdir = tmp_path / "nested" / "dir"
    outfile = outdir / "out.txt"

    writer.write("hello", outfile)

    assert outfile.exists()
    assert outfile.read_text(encoding="utf-8") == "hello"
