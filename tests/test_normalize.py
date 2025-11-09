"""Tests for :mod:`sanitize_text.utils.normalize`."""

from __future__ import annotations

import importlib.util
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_ROOT / "sanitize_text" / "utils" / "normalize.py"

spec = importlib.util.spec_from_file_location("normalize", MODULE_PATH)
assert spec and spec.loader  # defensive: module must be loadable
normalize = importlib.util.module_from_spec(spec)
spec.loader.exec_module(normalize)

normalize_pdf_text = normalize.normalize_pdf_text


def test_normalize_pdf_text_handles_core_transformations() -> None:
    """Normalize several PDF artefacts in a single pass."""
    raw = (
        "Intro line with spaces   \n"
        "https://example.\n"
        "com/path\n"
        "\n"
        "First paragraph.\n"
        "Bullet intro\n"
        "- bullet item\n"
        "\x0c"
        "Bare url https://foo.bar/baz\n"
    )

    result = normalize_pdf_text(raw, title="Sample Document")

    assert "Intro line with spaces\n" in result
    assert "https://example.\ncom/path" not in result
    assert "https://example.com/path" in result
    assert "Bullet intro\n\n- bullet item" in result
    assert "\x0c" not in result
    assert "Bare url <https://foo.bar/baz>" in result
    assert result.startswith("# Sample Document\n\n")


def test_normalize_pdf_text_keeps_existing_heading() -> None:
    """Do not duplicate headings when one is already present."""
    raw = "# Existing heading\nContent"

    result = normalize_pdf_text(raw, title="Ignored")

    assert result == raw
