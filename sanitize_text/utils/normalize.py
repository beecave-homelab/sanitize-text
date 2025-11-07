"""Text normalization helpers for content extracted from PDFs.

These utilities perform lightweight cleanup to improve Markdown lint
compliance and readability without attempting full semantic reconstruction
of complex layouts (like tables).
"""

from __future__ import annotations

import re
from collections.abc import Iterable

_RE_BARE_URL = re.compile(r"(?<!<)(https?://\S+)(?!>)")


def _trim_trailing_spaces(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.splitlines())


def _join_split_urls(text: str) -> str:
    r"""Join URLs broken by single newlines.

    This conservatively removes a newline if it appears immediately after a URL
    prefix sequence, so that patterns like::

        https://example.\ncom/path

    become::

        https://example.com/path

    Returns:
        The input with URL internal newlines removed.
    """
    # Merge newlines that fall inside a URL token: ...\n<non-space>
    pattern = re.compile(r"(https?://\S*?)\n(\S)")
    while True:
        new = pattern.sub(r"\1\2", text)
        if new == text:
            return new
        text = new


def _wrap_bare_urls(text: str) -> str:
    def _wrap(m: re.Match[str]) -> str:
        url = m.group(1)
        return f"<{url}>"

    return _RE_BARE_URL.sub(_wrap, text)


def _ensure_blank_line_before_lists(lines: Iterable[str]) -> list[str]:
    """Ensure a blank line before list items to satisfy MD032.

    We consider simple bullets starting with ``-``, ``*``, ``•``, or numbered
    lists like ``1.``.

    Returns:
        A new list of lines with blank lines inserted where needed.
    """
    out: list[str] = []
    prev: str | None = None
    for line in lines:
        is_list = bool(re.match(r"\s*(?:[-*•]|\d+\.)\s+", line))
        needs_blank = (
            is_list
            and prev is not None
            and prev.strip() != ""
            and not prev.lstrip().startswith(("-", "*", "•"))
            and not re.match(r"\s*\d+\.\s+", prev)
        )
        if needs_blank:
            out.append("")
        out.append(line)
        prev = line
    return out


def _insert_h1_if_missing(text: str, title: str | None) -> str:
    if not title:
        return text
    lines = text.splitlines()
    # Find first non-empty line
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    if idx < len(lines) and lines[idx].lstrip().startswith("# "):
        return text
    # Prepend H1 and a blank line
    new_lines = [f"# {title}", ""] + lines
    return "\n".join(new_lines)


def normalize_pdf_text(text: str, *, title: str | None) -> str:
    r"""Normalize plain text extracted from PDFs for Markdown output.

    Operations:
    - Convert form-feed (``\x0c``) to double newlines
    - Trim trailing spaces per line
    - Join URLs split across newlines
    - Wrap bare URLs in angle brackets
    - Ensure a blank line before list items
    - Optionally insert a top-level heading when missing

    Returns:
        Normalized text suitable for Markdown output.
    """
    if not text:
        return text

    # 1) Normalize page breaks
    text = text.replace("\x0c", "\n\n")
    # If there was already a newline before a form feed, the replacement may
    # produce 3+ newlines; collapse to exactly one blank line separation.
    text = re.sub(r"\n{3,}", "\n\n", text)

    # 2) Trim trailing spaces
    text = _trim_trailing_spaces(text)

    # 3) Join split URLs across line breaks
    text = _join_split_urls(text)

    # 4) Wrap bare URLs with angle brackets
    text = _wrap_bare_urls(text)

    # 5) Ensure blank line before list items
    lines = _ensure_blank_line_before_lists(text.splitlines())
    text = "\n".join(lines)

    # 6) Insert H1 if requested and missing
    text = _insert_h1_if_missing(text, title)

    return text
