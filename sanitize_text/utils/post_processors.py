"""Post-processors for text sanitization.

This module provides post-processors that modify or transform the output
of text sanitization after PII detection.
"""

import hashlib

from scrubadub.post_processors import PostProcessor


class HashedPIIReplacer(PostProcessor):
    """Post-processor that replaces PII with hashed identifiers.

    This processor takes detected PII and replaces it with a combination
    of the PII type and a hash of the original text. This makes the
    replacements traceable while maintaining privacy.

    Example:
        Original text: "John lives in Amsterdam"
        Processed text: "NAME-1234 lives in LOCATION-5678"
    """

    name = "hashed_pii_replacer"

    def __init__(self) -> None:
        """Initialize internal state for deterministic replacements."""
        self.seen_values = {}
        self.counter = 1

    def process_filth(self, filth_list: list[object]) -> list[object]:
        """Process a list of filth and replace with hashed identifiers.

        Returns:
            The modified list with ``replacement_string`` set for each filth.
        """
        from sanitize_text.utils.filth import MarkdownUrlFilth  # type: ignore

        for filth in filth_list:
            # Generate a unique identifier based on filth type and text
            key = f"{filth.type}:{filth.text}"
            if key not in self.seen_values:
                # Create a hash of the text for consistent replacement
                hash_obj = hashlib.md5(key.encode())  # noqa: S303 - md5 acceptable here
                hash_val = int(hash_obj.hexdigest(), 16) % 1000  # stable short id
                # Use a consistent placeholder prefix: treat URL-like text as URL
                text = str(getattr(filth, "text", ""))
                is_urlish = text.lower().startswith(("http://", "https://", "ftp://", "www."))
                # Also catch obvious SharePoint fragments that start with the domain
                is_urlish = is_urlish or ("sharepoint.com/" in text.lower())
                placeholder_type = (
                    "URL" if filth.type in {"markdown_url"} or is_urlish else filth.type.upper()
                )
                placeholder = f"{placeholder_type}-{hash_val:03d}"
                self.seen_values[key] = placeholder

            placeholder = self.seen_values[key]

            if isinstance(filth, MarkdownUrlFilth):
                # Preserve Markdown structure
                filth.replacement_string = f"[{filth.link_text}]({placeholder})"
            else:
                filth.replacement_string = placeholder

        return filth_list
