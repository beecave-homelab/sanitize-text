"""URL detectors."""

from __future__ import annotations

import logging
import re
from collections.abc import Iterator

from scrubadub.detectors import RegexDetector, register_detector
from scrubadub.filth.url import UrlFilth

logger = logging.getLogger(__name__)


@register_detector
class BareDomainDetector(RegexDetector):
    """Detector for URLs in plain text.

    - Bare domain names (e.g., example.com)
    - www prefixed domains (e.g., www.example.com)
    - Protocol prefixed URLs (e.g., http://example.com)
    - Complex URLs with paths and slugs
    - URLs with query parameters and fragments
    - URLs with subdomains
    """

    name = "url"
    filth_cls = UrlFilth

    # List of common TLDs to match against
    COMMON_TLDS = (
        "com|net|org|edu|gov|mil|biz|info|name|museum|coop|aero|"
        "[a-z][a-z]|nl|uk|us|eu|de|fr|es|it|ru|cn|jp|br|pl|in|au|"
        "dev|app|io|ai|cloud|digital|tech|online|site|web|blog|shop|store|"
        "academy|agency|business|center|company|consulting|foundation|institute|"
        "international|management|marketing|solutions|technology|university|"
        "systems|services|support|science|software|studio|training|ventures|"
        "sharepoint|microsoft"
    )

    def __init__(self, **kwargs: object) -> None:
        """Initialize the detector with optional configuration."""
        super().__init__(**kwargs)

        # Build the URL pattern piece by piece
        tld_pattern = f"(?:{self.COMMON_TLDS})"

        # Simple but effective URL pattern
        url_pattern = (
            # Start with word boundary and make sure we're not in an email address
            r"(?<![@\(\[])\b"
            r"(?:"
            # Protocol URLs
            r"(?:https?://(?:www\.)?|ftp://)"
            r"(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)*"  # subdomains
            r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?"  # domain
            r"\."
            + tld_pattern  # TLD
            + r"(?:/[^\s<>]*)?"  # path and query
            r"|"
            # Bare domains with optional www
            r"(?<![@.])"  # Not preceded by @ or .
            r"(?:www\.)?"  # optional www
            r"(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)*"  # subdomains
            r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?"  # domain
            r"\."
            + tld_pattern  # TLD
            + r"(?:/[^\s<>]*)?"  # path and query
            r")"
            r"\b"
        )

        # Compile the pattern
        self.regex = re.compile(url_pattern, re.IGNORECASE)

    def iter_filth(
        self,
        text: str,
        document_name: str | None = None,
    ) -> Iterator[UrlFilth]:  # noqa: D401
        """Yield URL filth and filter split sharepoint.com fragments.

        Heuristic: if the matched host ends with 'point.com' and the preceding
        non-separator characters end with 'share', skip the match. This avoids
        false positives like '... share' + 'epoint.com' from PDF line/word splits.
        """
        verbose = getattr(self, "_verbose", False)
        if verbose:
            logger.info("  [%s] Scanning for URLs...", self.name)

        match_count = 0
        for m in self.regex.finditer(text):
            url = m.group(0)
            # Trim common trailing punctuation/junk that may cling to URLs
            url = re.sub(r"[\]\)\.,;:>]+$", "", url)
            # Extract host part (before first slash) to examine domain fragment
            host = url.split("/", 1)[0].lower()
            # Heuristic: Skip mixed-case bare domains without protocol or www
            url_lower = url.lower()
            has_protocol = url_lower.startswith(("http://", "https://", "ftp://", "www."))
            if not has_protocol and any(c.isupper() for c in url):
                continue
            # Skip sharepoint fragments: '...share' + 'epoint.com' or
            # 'hare' + 'point.com' (check both sides with recomposition checks)
            if host.endswith("point.com"):
                start, end = m.start(), m.end()
                window = 20
                lookback = text[max(0, start - window) : start]
                lookahead = text[end : min(len(text), end + window)]
                prev = re.sub(r"[^a-z0-9]+", "", lookback.lower())
                next_ = re.sub(r"[^a-z0-9]+", "", lookahead.lower())
                if prev.endswith("share") or next_.startswith("share"):
                    continue
                # Recompose candidate full domain to catch wider splits
                target = "sharepoint.com"
                # Use up to 6 chars from prev/next to complete 'share'
                combined_prev = (prev[-6:] + host).startswith(target)
                combined_next = (host + next_[:6]).startswith(target)
                if combined_prev or combined_next:
                    continue
                # Wider window: look for 'sharepointcom' across boundaries
                combined = prev[-30:] + re.sub(r"[^a-z0-9]+", "", host) + next_[:30]
                if "sharepointcom" in combined:
                    continue
                # If the host itself is a known fragment, scan a much larger window
                if host in {"epoint.com", "harepoint.com", "point.com"}:
                    span_start = max(0, start - 1500)
                    span_end = min(len(text), end + 1500)
                    span = re.sub(
                        r"[^a-z0-9]+",
                        "",
                        text[span_start:span_end].lower(),
                    )
                    if "sharepointcom" in span or "sharepoint" in span:
                        continue
                    # Document-level heuristic: if the whole document references
                    # sharepoint, treat these exact fragments as false positives.
                    doc_squeezed = re.sub(r"[^a-z0-9]+", "", text.lower())
                    if "sharepoint" in doc_squeezed:
                        continue
                    # Line-based fallback: check the current line (sanitized)
                    line_start = text.rfind("\n", 0, start) + 1
                    if line_start < 0:
                        line_start = 0
                    line_end = text.find("\n", end)
                    if line_end == -1:
                        line_end = len(text)
                    line = re.sub(
                        r"[^a-z0-9]+",
                        "",
                        text[line_start:line_end].lower(),
                    )
                    if "sharepointcom" in line or "sharepoint" in line:
                        continue

            match_count += 1
            if verbose:
                logger.info("    ✓ Found: '%s' (%s)", url, self.name)
            yield UrlFilth(
                beg=m.start(),
                end=m.end(),
                text=url,
                detector_name=self.name,
                document_name=document_name,
            )

        if verbose:
            logger.info("  [%s] Total matches: %d", self.name, match_count)
