"""Generic cleanup utilities for final output text.

These cleanups are format-agnostic and safe to apply to any text output
before writing to disk.
"""

from __future__ import annotations

import re

_RE_UNKNOWN_ANGLE = re.compile(r"<UNKNOWN-[^>]*>")
_RE_UNKNOWN_LINK = re.compile(r"\[([^\]]+)\]\(UNKNOWN-\d+\)")
_RE_UNKNOWN_BARE = re.compile(r"\bUNKNOWN-\d+\b")

# Heuristic: long runs of base64/URL-safe-ish gibberish
_RE_GIBBERISH_RUN = re.compile(r"([A-Za-z0-9_%=]{80,})")

# Apply collapsing only inside [] and () to avoid touching normal prose
_RE_BRACKET_BLOCK = re.compile(r"\[[^\]]+\]")
_RE_PAREN_BLOCK = re.compile(r"\([^\)]+\)")


def remove_unknown_placeholders(text: str) -> str:
    """Remove opaque unknown placeholders like ``<UNKNOWN-847>``.

    This keeps other placeholders (e.g., URL-123, LOCATION-045) intact.

    Returns:
        The input with unknown placeholders removed.
    """
    # Remove angle-bracket UNKNOWN tokens
    text = _RE_UNKNOWN_ANGLE.sub("", text)
    # Replace Markdown links targeting UNKNOWN-* with just the link text
    text = _RE_UNKNOWN_LINK.sub(r"\1", text)
    # Remove bare UNKNOWN-* tokens
    text = _RE_UNKNOWN_BARE.sub("", text)
    # Tidy extra spaces introduced
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text


def dedupe_adjacent_identical_lines(text: str) -> str:
    """Remove immediately repeated identical lines to reduce duplication.

    Only collapses consecutive duplicates to avoid altering intended
    repetitions across sections.

    Returns:
        The input with adjacent identical lines collapsed to a single line.
    """
    lines = text.splitlines()
    out: list[str] = []
    prev: str | None = None
    for ln in lines:
        if prev is not None and ln == prev:
            # Skip duplicate
            continue
        out.append(ln)
        prev = ln
    return "\n".join(out)


def ensure_trailing_newline(text: str) -> str:
    """Ensure exactly one trailing newline at EOF.

    Returns:
        The input with a single trailing newline appended if missing.
    """
    if not text.endswith("\n"):
        return text + "\n"
    return text


def cleanup_output(text: str) -> str:
    """Apply a conservative cleanup pipeline to final output text.

    Steps:
    - Remove ``<UNKNOWN-*>`` placeholders
    - Dedupe adjacent identical lines
    - Ensure trailing newline

    Returns:
        The cleaned text after applying the pipeline steps.
    """
    if not text:
        return text
    text = remove_unknown_placeholders(text)
    text = collapse_long_gibberish_in_brackets(text)
    text = dedupe_adjacent_identical_lines(text)
    text = ensure_trailing_newline(text)
    return text


def _collapse_run(match: re.Match[str]) -> str:
    """Collapse a long alphanumeric run keeping the boundaries.

    Example: ABCDEFGH...WXYZ (keep 16 head, 8 tail).
    """
    s = match.group(1)
    if len(s) <= 80:
        return s
    head = s[:16]
    tail = s[-8:]
    return f"{head}…{tail}"


def _collapse_inside_block(block_text: str) -> str:
    # Replace multiple long runs inside the block
    return _RE_GIBBERISH_RUN.sub(_collapse_run, block_text)


def collapse_long_gibberish_in_brackets(text: str) -> str:
    """Collapse very long base64-like or random-looking sequences in [] and ().

    This improves readability for exported artifacts that embed extremely long
    tokens or encoded segments in link text or parenthetical statements.
    """
    def repl_bracket(m: re.Match[str]) -> str:
        inner = m.group(0)
        return _collapse_inside_block(inner)

    def repl_paren(m: re.Match[str]) -> str:
        inner = m.group(0)
        return _collapse_inside_block(inner)

    text = _RE_BRACKET_BLOCK.sub(repl_bracket, text)
    text = _RE_PAREN_BLOCK.sub(repl_paren, text)
    return text
