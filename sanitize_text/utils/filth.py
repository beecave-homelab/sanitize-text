"""Custom filth types for text sanitization.

This module defines custom filth types that represent different kinds of
personally identifiable information (PII) found in text.
"""

from scrubadub.filth import Filth


class LocationFilth(Filth):
    """Filth for location names."""

    type = "location"


class OrganizationFilth(Filth):
    """Filth for organization names."""

    type = "organization"


class NameFilth(Filth):
    """Filth for person names."""

    type = "name"


class PrivateIPFilth(Filth):
    """Filth subclass for private IP addresses.

    This class represents detected private IP addresses in text,
    including addresses in the ranges:
    - 10.0.0.0 to 10.255.255.255
    - 172.16.0.0 to 172.31.255.255
    - 192.168.0.0 to 192.168.255.255
    """

    type = "private_ip"


class PublicIPFilth(Filth):
    """Filth subclass for public IP addresses.

    This class represents detected public IP addresses in text,
    which are any valid IPv4 addresses that are not in private IP ranges.
    These addresses are potentially sensitive as they can identify
    specific internet-connected devices or networks.
    """

    type = "public_ip"


class MarkdownUrlFilth(Filth):
    """Filth for URLs that appear inside Markdown link syntax.

    Stores the original *link text* so a post-processor can recreate a
    well-formed Markdown placeholder (e.g. ``[text](URL-001)``).
    """

    type = "markdown_url"

    def __init__(
        self,
        *args: object,
        link_text: str = "",
        url: str = "",
        **kwargs: object,
    ) -> None:
        """Store extra metadata before delegating to base class."""
        super().__init__(*args, **kwargs)
        self.link_text = link_text
        self.url = url
