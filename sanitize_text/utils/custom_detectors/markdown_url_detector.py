"""Markdown URL detector."""

import re
from collections.abc import Iterator

from scrubadub.detectors import RegexDetector, register_detector
from scrubadub.filth.url import UrlFilth

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
    filth_cls = UrlFilth

    # List of common TLDs to match against
    COMMON_TLDS = BareDomainDetector.COMMON_TLDS

    def __init__(self, **kwargs: object) -> None:
        """Initialize the detector with optional configuration."""
        super().__init__(**kwargs)

        # Build the URL pattern piece by piece (not needed explicitly with DOTALL capture)

        # Pattern for markdown links that handles both empty and non-empty link text.
        # Allow the URL part to span multiple lines/whitespace until the closing ')'.
        self.regex = re.compile(
            r"\["  # Opening bracket
            r"([^\]]*)"  # Link text (can be empty)
            r"\]+"  # One or more closing brackets to handle ']]('
            r"\("  # Opening parenthesis
            r"([^)]+?)"  # URL part (non-greedy), may contain newlines/spaces
            r"\)",  # Closing parenthesis
            re.IGNORECASE | re.DOTALL,
        )

    def iter_filth(self, text: str, document_name: str | None = None) -> Iterator[UrlFilth]:
        """Yield ``UrlFilth`` for each URL found in Markdown links."""
        for match in self.regex.finditer(text):
            link_text = match.group(1)  # The text part [text] (might be empty)
            url_raw = match.group(2)  # The URL part (possibly across lines)

            # Normalize by removing internal whitespace/newlines to reconstruct the URL
            url = re.sub(r"\s+", "", url_raw)

            # Generate a consistent hash for the URL
            url_hash = hash(url) % 10000

            # Create the replacement, preserving empty link text if present
            replacement = f"[{link_text}]({{{{url-{url_hash:04d}}}}})"

            yield UrlFilth(
                beg=match.start(),
                end=match.end(),
                text=match.group(0),
                replacement_string=replacement,
                detector_name="markdown_url",
                document_name=document_name,
            )
