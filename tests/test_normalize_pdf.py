"""Tests for PDF text normalization utilities.

These tests validate lightweight cleanup applied to text extracted from PDFs.
"""

from __future__ import annotations

import re

from sanitize_text.utils.normalize import normalize_pdf_text


def test_remove_form_feeds_and_trim_trailing_spaces() -> None:
    """Form feeds are converted to blank lines and trailing spaces are trimmed."""
    src = "Line 1  \n\x0cLine 2    \nLine 3\n"
    out = normalize_pdf_text(src, title=None)
    # form feed becomes two newlines between Line 1 and Line 2
    assert out.splitlines()[0] == "Line 1"
    assert out.splitlines()[1] == ""
    assert out.splitlines()[2] == "Line 2"
    # trailing spaces trimmed on Line 1/2
    assert out.startswith("Line 1\n\nLine 2\nLine 3")


def test_insert_h1_if_missing() -> None:
    """If no H1 is present, insert a top-level heading as first content."""
    src = "Body"
    out = normalize_pdf_text(src, title="Results (nl_NL)")
    lines = out.splitlines()
    assert lines[0].startswith("# ")
    assert lines[0] == "# Results (nl_NL)"
    assert lines[1] == ""
    assert lines[2] == "Body"


def test_preserve_existing_h1() -> None:
    """Do not add a new H1 if one already exists at the top."""
    src = "# Existing\nBody"
    out = normalize_pdf_text(src, title="Should not appear")
    assert out.startswith("# Existing\nBody")


def test_wrap_bare_urls() -> None:
    """Bare URLs are wrapped in angle brackets to appease MD034."""
    src = "See https://example.com/path?x=1 and http://sub.domain.tld."
    out = normalize_pdf_text(src, title=None)
    assert "<https://example.com/path?x=1>" in out
    assert "<http://sub.domain.tld>" in out or "<http://sub.domain.tld.>" in out


def test_join_split_urls_across_lines() -> None:
    """URLs broken across newlines are rejoined and wrapped."""
    src = "Visit https://example.\ncom/docs?id=1"
    out = normalize_pdf_text(src, title=None)
    assert "<https://example.com/docs?id=1>" in out


def test_normalize_list_spacing() -> None:
    """Ensure a blank line before list items to satisfy MD032."""
    src = "Paragraph\n- item 1\n- item 2"
    out = normalize_pdf_text(src, title=None)
    # There should be a blank line between paragraph and list
    assert re.search(r"Paragraph\n\n- item 1", out) is not None
