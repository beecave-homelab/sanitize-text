"""SharePoint URL detector.

Robustly detects SharePoint links and trims noisy trailing punctuation
commonly produced by exports (e.g., "),[[", ")]", ").", ",").
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterator

from scrubadub.detectors import RegexDetector, register_detector
from scrubadub.filth.url import UrlFilth

logger = logging.getLogger(__name__)


@register_detector
class SharePointUrlDetector(RegexDetector):
    """Detector for SharePoint URLs.

    Runs before the generic URL detector to capture noisy SharePoint links.
    """

    name = "sharepoint_url"
    filth_cls = UrlFilth

    def __init__(self, **kwargs: object) -> None:
        """Initialize the SharePoint URL detector.

        Sets up the regex pattern for detecting SharePoint URLs.
        """
        super().__init__(**kwargs)
        # Match protocol URLs to *.sharepoint.com with generous path
        # Permit a single newline inside the path to accommodate wrapped exports
        self.regex = re.compile(
            r"\bhttps?://[a-z0-9.-]*sharepoint\.com/(?:[^\s<>)\]]|\n)+",
            re.IGNORECASE,
        )

    def iter_filth(
        self,
        text: str,
        document_name: str | None = None,
    ) -> Iterator[UrlFilth]:
        """Iterate over SharePoint URL filth in the given text.

        Cleans and trims detected URLs by removing whitespace and trailing
        punctuation.

        Args:
            text: The text to scan for SharePoint URLs.
            document_name: Optional name of the document for the filth.

        Yields:
            UrlFilth instances for each detected SharePoint URL.
        """
        verbose = getattr(self, "_verbose", False)
        if verbose:
            logger.info("  [%s] Scanning for SharePoint URLs...", self.name)

        match_count = 0
        for m in self.regex.finditer(text):
            url = m.group(0)
            # Remove any whitespace that got inserted in very long URLs
            url = re.sub(r"\s+", "", url)
            # Trim trailing punctuation/junk that may cling to URLs, incl quotes
            url = re.sub(r"[\]\)\.,;:>'\"]+$", "", url)

            match_count += 1
            if verbose:
                # Truncate long URLs for display
                display_url = url[:60] + "..." if len(url) > 60 else url
                logger.info("    ✓ Found: '%s' (%s)", display_url, self.name)

            yield UrlFilth(
                beg=m.start(),
                end=m.end(),
                text=url,
                detector_name=self.name,
                document_name=document_name,
            )

        if verbose:
            logger.info("  [%s] Total matches: %d", self.name, match_count)
