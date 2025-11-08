"""Markdown URL detector."""

from __future__ import annotations

import re
from collections.abc import Iterator

from scrubadub.detectors import RegexDetector, register_detector

from sanitize_text.utils.filth import MarkdownUrlFilth

from .url_detector import BareDomainDetector


@register_detector
class MarkdownUrlDetector(RegexDetector):
    """Dedicated detector for URLs within Markdown links.

    Handles:
    - Standard Markdown links [text](url)
    - Empty Markdown links [](url)
    - Links with complex URLs
    - Links with query parameters
    - Links with fragments
    - Links with bare domains
    - Links with www prefixes
    """

    name = "markdown_url"
    filth_cls = MarkdownUrlFilth

    # List of common TLDs to match against
    COMMON_TLDS = BareDomainDetector.COMMON_TLDS

    def __init__(self, **kwargs: object) -> None:
        """Initialize the detector with optional configuration."""
        super().__init__(**kwargs)

        # Build the URL pattern piece by piece (not needed explicitly with
        # DOTALL capture)

        # Pattern for Markdown links. We purposefully capture the URL in a *separate
        # group* (``group(2)``) so that ``iter_filth`` can reliably access it. Key
        # considerations:
        #
        # * Link text may be empty.
        # * The URL can contain whitespace (Word-exported Markdown tends to insert
        #   soft-line-breaks), parentheses, query strings, Unicode, etc.
        # * Multiline input is allowed – we therefore compile with the DOTALL flag.
        # * We do **not** attempt full RFC-compliant URL validation here – the goal
        #   is only to capture the complete contents between the parentheses so the
        #   detector can replace it as a whole.
        self.regex = re.compile(
            # group 'open': one or two opening brackets; 'text': link text; 'close': matching closers
            r"(?P<open>\[\[|\[)"
            r"(?P<text>[^\]]*)"
            r"(?P<close>\]\]|\])"
            r"\("  # opening parenthesis
            # group 'url': tolerate internal parens; allow newlines (DOTALL)
            r"(?P<url>[^)]+?|(?:[^)]*\([^)]*\)[^)]*))"
            r"\)",  # closing parenthesis
            re.IGNORECASE | re.DOTALL,
        )

    def iter_filth(
        self,
        text: str,
        document_name: str | None = None,
    ) -> Iterator[MarkdownUrlFilth]:
        """Yield ``UrlFilth`` for each URL found in Markdown links."""
        import click

        verbose = getattr(self, '_verbose', False)
        if verbose:
            click.echo(f"  [{self.name}] Scanning for Markdown URLs...")

        match_count = 0
        for match in self.regex.finditer(text):
            open_br = match.group("open")
            close_br = match.group("close")
            # Enforce matching bracket lengths; skip odd pairs defensively
            if (open_br == "[[" and close_br != "]]") or (
                open_br == "[" and close_br != "]"
            ):
                continue
            bracket_pairs = 2 if open_br == "[[" else 1
            link_text = match.group("text")
            url_raw = match.group("url")
            # Normalize whitespace and common export artifacts
            url = re.sub(r"\s+", "", url_raw)
            url = url.strip()
            # Remove surrounding angle brackets often added by normalizers
            if url.startswith("<") and url.endswith(">"):
                url = url[1:-1]
            # Trim trailing punctuation/junk
            url = re.sub(r"[\]\)\.,;:>'\"]+$", "", url)

            match_count += 1
            if verbose:
                # Truncate long URLs for display
                display_url = url[:60] + "..." if len(url) > 60 else url
                click.echo(f"    ✓ Found: '[{link_text}]({display_url})' ({self.name})")

            yield MarkdownUrlFilth(
                beg=match.start(),
                end=match.end(),
                text=match.group(0),
                link_text=link_text,
                url=url,
                bracket_pairs=bracket_pairs,
                detector_name="markdown_url",
                document_name=document_name,
            )

        if verbose:
            click.echo(f"  [{self.name}] Total matches: {match_count}")
