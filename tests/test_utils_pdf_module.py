"""Tests for :mod:`sanitize_text.utils.pdf` module functions."""

from __future__ import annotations

from sanitize_text.utils.pdf import _normalize_text_for_pdf, normalize_text_for_pdf


def test_pre_mode_joins_hyphenated_linebreaks_and_trims() -> None:
    """Pre mode joins hyphenated breaks and trims trailing spaces."""
    # "Hel-\nlo" should become "Hello" and trailing space should be trimmed
    src = "Hel-\nlo world \nNext line"
    out = normalize_text_for_pdf(src, mode="pre")
    assert "Hello world" in out
    assert out.splitlines()[0].rstrip().endswith("world")


def test_para_mode_merges_lines_and_paragraphs() -> None:
    """Para mode merges wrapped lines into sentences and paragraphs."""
    src = "Intro line.\ncontinues on next line\n\nAnother Para:\nmore text\n"
    out = normalize_text_for_pdf(src, mode="para")
    parts = out.split("\n\n")
    assert len(parts) == 2
    assert parts[0].startswith("Intro line.")
    assert "continues on next line" in parts[0]
    assert parts[1].startswith("Another Para:")


def test_unicode_hyphens_handled() -> None:
    """Unicode soft/non-breaking hyphens are normalized."""
    # soft hyphen removed, non-breaking hyphen becomes normal hyphen
    src = "co\u00adop and non\u2011breaking"
    out = normalize_text_for_pdf(src, mode="pre")
    assert "coop" in out
    assert "non-breaking" in out


def test_backward_compat_alias_points_to_function() -> None:
    """Alias points to the same function for backwards compatibility."""
    assert _normalize_text_for_pdf is normalize_text_for_pdf
