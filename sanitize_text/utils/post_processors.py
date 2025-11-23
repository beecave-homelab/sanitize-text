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

    def __init__(self, *, algorithm: str = "md5", modulus: int = 10000) -> None:
        """Initialize internal state for deterministic replacements.

        Args:
            algorithm: Hash algorithm to use ("md5" or "sha256").
            modulus: Bucket size for short IDs (increase to reduce collisions).
        """
        self.seen_values: dict[str, str] = {}
        self.counter = 1
        self.algorithm = algorithm
        self.modulus = max(1, int(modulus))

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
                if self.algorithm == "sha256":
                    hash_obj = hashlib.sha256(key.encode())
                else:
                    hash_obj = hashlib.md5(key.encode())  # noqa: S303 - md5 acceptable here
                # stable shortid
                hash_val = int(hash_obj.hexdigest(), 16) % self.modulus
                # Use a consistent placeholder prefix: treat URL-like text as URL
                text = str(getattr(filth, "text", ""))
                lower_text = text.lower()
                is_urlish = lower_text.startswith(("http://", "https://", "ftp://", "www."))
                # Also catch obvious SharePoint fragments that start with the domain
                is_urlish = is_urlish or ("sharepoint.com/" in lower_text)
                # Markdown-style links such as "[text](<https://example.com>)" should
                # also be treated as URL-like, even when produced by detectors that use
                # the generic "unknown" filth type.
                if not is_urlish:
                    compact = lower_text.replace(" ", "")
                    if compact.startswith("[") and "](" in compact and "://" in compact:
                        is_urlish = True
                placeholder_type = (
                    "URL" if filth.type in {"markdown_url"} or is_urlish else filth.type.upper()
                )
                width = max(3, len(str(self.modulus - 1)))
                placeholder = f"{placeholder_type}-{hash_val:0{width}d}"
                self.seen_values[key] = placeholder

            placeholder = self.seen_values[key]

            if isinstance(filth, MarkdownUrlFilth):
                # Preserve Markdown structure, including single vs double brackets
                brackets = "[" * getattr(filth, "bracket_pairs", 1)
                closing = "]" * getattr(filth, "bracket_pairs", 1)
                filth.replacement_string = f"{brackets}{filth.link_text}{closing}({placeholder})"
            else:
                filth.replacement_string = placeholder

        return filth_list


DEFAULT_POST_PROCESSOR_FACTORY = HashedPIIReplacer
