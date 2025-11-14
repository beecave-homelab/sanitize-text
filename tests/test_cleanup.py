"""Tests for sanitize_text.utils.cleanup module."""

from __future__ import annotations

from sanitize_text.utils.cleanup import (
    cleanup_output,
    collapse_long_gibberish_in_brackets,
    dedupe_adjacent_identical_lines,
    ensure_trailing_newline,
    remove_unknown_placeholders,
)


def test_remove_unknown_placeholders() -> None:
    """Test removal of unknown placeholders while keeping other placeholders."""
    # Test angle bracket UNKNOWN tokens
    assert remove_unknown_placeholders("Hello <UNKNOWN-123> world") == "Hello world"

    # Test Markdown links with UNKNOWN targets
    assert remove_unknown_placeholders("[link](UNKNOWN-456)") == "link"

    # Test bare UNKNOWN tokens
    assert remove_unknown_placeholders("Text UNKNOWN-789 more") == "Text more"

    # Test that other placeholders are preserved
    assert (
        remove_unknown_placeholders("Email EMAIL-123 and URL-456") == "Email EMAIL-123 and URL-456"
    )

    # Test multiple spaces are collapsed
    assert remove_unknown_placeholders("Hello <UNKNOWN-1>  world") == "Hello world"


def test_dedupe_adjacent_identical_lines() -> None:
    """Test removal of adjacent duplicate lines."""
    # Test basic deduplication
    input_text = "Line 1\nLine 2\nLine 2\nLine 3"
    expected = "Line 1\nLine 2\nLine 3"
    assert dedupe_adjacent_identical_lines(input_text) == expected

    # Test that non-consecutive duplicates are preserved
    input_text = "Line 1\nLine 2\nLine 1\nLine 2"
    expected = "Line 1\nLine 2\nLine 1\nLine 2"
    assert dedupe_adjacent_identical_lines(input_text) == expected

    # Test triple duplicates
    input_text = "Same\nSame\nSame\nDifferent"
    expected = "Same\nDifferent"
    assert dedupe_adjacent_identical_lines(input_text) == expected


def test_ensure_trailing_newline() -> None:
    """Test that text ends with exactly one trailing newline."""
    # Test adding newline when missing
    assert ensure_trailing_newline("Hello world") == "Hello world\n"

    # Test preserving existing single newline
    assert ensure_trailing_newline("Hello world\n") == "Hello world\n"

    # Test preserving multiple newlines (function only ensures at least one)
    assert ensure_trailing_newline("Hello world\n\n\n") == "Hello world\n\n\n"


def test_cleanup_output_empty_text() -> None:
    """Test cleanup pipeline with empty text."""
    assert cleanup_output("") == ""


def test_cleanup_output_pipeline() -> None:
    """Test the complete cleanup pipeline."""
    input_text = (
        "Hello <UNKNOWN-1> world\n"
        "Line 2\n"
        "Line 2\n"
        "[Very long base64 string: "
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789]"
    )
    result = cleanup_output(input_text)

    # Should remove unknown placeholders
    assert "<UNKNOWN-1>" not in result

    # Should dedupe lines
    assert result.count("Line 2") == 1

    # Should end with newline
    assert result.endswith("\n")


def test_collapse_long_gibberish_in_brackets() -> None:
    """Test collapsing of long alphanumeric sequences in brackets."""
    # Test short sequences (should not be collapsed)
    short_text = "[Short123]"
    assert collapse_long_gibberish_in_brackets(short_text) == short_text

    # Test long sequences in brackets
    long_text = """[
    ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789
    ]"""
    result = collapse_long_gibberish_in_brackets(long_text)
    assert len(result) < len(long_text)
    assert "…" in result

    # Test long sequences in parentheses
    long_paren = """(
    ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789
    )"""
    result_paren = collapse_long_gibberish_in_brackets(long_paren)
    assert len(result_paren) < len(long_paren)
    assert "…" in result_paren

    # Test normal text outside brackets is preserved
    mixed = "Normal text [LongABCDEFGHijklmnopqrstuvwxyz0123456789] more text"
    result_mixed = collapse_long_gibberish_in_brackets(mixed)
    assert "Normal text" in result_mixed
    assert "more text" in result_mixed


def test_collapse_exact_boundary_length() -> None:
    """Test that sequences exactly 80 chars are not collapsed."""
    exact_80 = "A" * 80
    text = f"[{exact_80}]"
    assert collapse_long_gibberish_in_brackets(text) == text


def test_collapse_slightly_over_boundary() -> None:
    """Test that sequences over 80 chars are collapsed."""
    over_80 = "A" * 81
    text = f"[{over_80}]"
    result = collapse_long_gibberish_in_brackets(text)
    assert len(result) < len(text)
    assert "…" in result
