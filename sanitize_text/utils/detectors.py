"""Custom detectors for text scrubbing."""

import re
import json
import click
from pathlib import Path
from scrubadub.detectors import Detector, RegexDetector, register_detector
from scrubadub.filth.url import UrlFilth
from .filth import (
    LocationFilth,
    OrganizationFilth,
    NameFilth,
    PrivateIPFilth,
    PublicIPFilth
)

@register_detector
class BareDomainDetector(RegexDetector):
    """
    Detector for URLs in plain text:
    - Bare domain names (e.g., example.com)
    - www prefixed domains (e.g., www.example.com)
    - Protocol prefixed URLs (e.g., http://example.com)
    - Complex URLs with paths and slugs
    - URLs with query parameters and fragments
    - URLs with subdomains
    """
    name = 'url'
    filth_cls = UrlFilth

    # List of common TLDs to match against
    COMMON_TLDS = (
        'com|net|org|edu|gov|mil|biz|info|name|museum|coop|aero|'
        '[a-z][a-z]|nl|uk|us|eu|de|fr|es|it|ru|cn|jp|br|pl|in|au|'
        'dev|app|io|ai|cloud|digital|tech|online|site|web|blog|shop|store|'
        'academy|agency|business|center|company|consulting|foundation|institute|'
        'international|management|marketing|solutions|technology|university|'
        'systems|services|support|science|software|studio|training|ventures'
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Build the URL pattern piece by piece
        tld_pattern = f"(?:{self.COMMON_TLDS})"
        
        # Simple but effective URL pattern
        url_pattern = (
            # Start with word boundary and make sure we're not in an email address
            r'(?<![@])\b'
            r'(?:'
            # Protocol URLs
            r'(?:https?://(?:www\.)?|ftp://)'
            r'(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)*'  # subdomains
            r'[a-z0-9](?:[a-z0-9-]*[a-z0-9])?'         # domain
            r'\.' + tld_pattern +                       # TLD
            r'(?:/[^\s<>]*)?'                          # path and query
            r'|'
            # Bare domains with optional www
            r'(?<![@.])'                               # Not preceded by @ or .
            r'(?:www\.)?'                              # optional www
            r'(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)*' # subdomains
            r'[a-z0-9](?:[a-z0-9-]*[a-z0-9])?'        # domain
            r'\.' + tld_pattern +                      # TLD
            r'(?:/[^\s<>]*)?'                         # path and query
            r')'
            r'\b'
        )
        
        # Compile the pattern
        self.regex = re.compile(url_pattern, re.IGNORECASE)

@register_detector
class MarkdownUrlDetector(RegexDetector):
    """
    Dedicated detector for URLs within Markdown links.
    Handles:
    - Standard Markdown links [text](url)
    - Empty Markdown links [](url)
    - Links with complex URLs
    - Links with query parameters
    - Links with fragments
    - Links with bare domains
    - Links with www prefixes
    """
    name = 'markdown_url'
    filth_cls = UrlFilth

    # List of common TLDs to match against
    COMMON_TLDS = BareDomainDetector.COMMON_TLDS

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Build the URL pattern piece by piece
        tld_pattern = f"(?:{self.COMMON_TLDS})"
        
        # Comprehensive URL pattern similar to BareDomainDetector
        url_pattern = (
            r'(?:'
            # Protocol URLs
            r'(?:https?://(?:www\.)?|ftp://)'
            r'(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)*'  # subdomains
            r'[a-z0-9](?:[a-z0-9-]*[a-z0-9])?'         # domain
            r'\.' + tld_pattern +                       # TLD
            r'(?:/[^\s<>)]*)?'                         # path and query
            r'|'
            # Bare domains with optional www
            r'(?:www\.)?'                              # optional www
            r'(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)*' # subdomains
            r'[a-z0-9](?:[a-z0-9-]*[a-z0-9])?'        # domain
            r'\.' + tld_pattern +                      # TLD
            r'(?:/[^\s<>)]*)?'                        # path and query
            r')'
        )
        
        # Pattern for markdown links that handles both empty and non-empty link text
        self.regex = re.compile(
            r'\['               # Opening bracket
            r'([^\]]*)'        # Link text (can be empty)
            r'\]'              # Closing bracket
            r'\('              # Opening parenthesis
            f'({url_pattern})'  # URL part using comprehensive pattern
            r'\)',             # Closing parenthesis
            re.IGNORECASE
        )

    def iter_filth(self, text, document_name=None):
        """Yields UrlFilth for each URL found in Markdown links."""
        for match in self.regex.finditer(text):
            link_text = match.group(1)  # The text part [text] (might be empty)
            url = match.group(2)        # The URL part (url)
            
            # Generate a consistent hash for the URL
            url_hash = hash(url) % 10000
            
            # Create the replacement, preserving empty link text if present
            replacement = f"[{link_text}]({{{{url-{url_hash:04d}}}}})"
            
            yield UrlFilth(
                beg=match.start(),
                end=match.end(),
                text=match.group(0),
                replacement_string=replacement,
                detector_name='markdown_url',
                document_name=document_name
            )

@register_detector
class PrivateIPDetector(RegexDetector):
    """
    A custom detector to identify and redact private IP addresses from text.
    The following IP ranges are detected:
    - 192.168.X.X (65,024 IPs)
    - 10.0.X.X (65,024 IPs)
    - 172.X.X.X (1,048,576 IPs)
    """
    name = 'private_ip'
    filth_cls = PrivateIPFilth

    # Compile the regex pattern to match the IP ranges
    regex = re.compile(
        r'\b(?:192\.168\.\d{1,3}\.\d{1,3}|10\.0\.\d{1,3}\.\d{1,3}|172\.\d{1,3}\.\d{1,3}\.\d{1,3})\b'
    )

@register_detector
class PublicIPDetector(RegexDetector):
    """
    A custom detector to identify and redact public IP addresses from text.
    Public IP addresses are identified as any IP that does not fall within the following private IP ranges:
    - 192.168.X.X (65,024 IPs)
    - 10.0.X.X (65,024 IPs)
    - 172.16.0.0 to 172.31.255.255 (1,048,576 IPs)
    """
    name = 'public_ip'
    filth_cls = PublicIPFilth

    # Regex pattern for identifying public IP addresses
    regex = re.compile(
        r'\b(?!(?:192\.168|10\.0|172\.(?:1[6-9]|2[0-9]|3[0-1]))\.\d{1,3}\.\d{1,3})'  # Exclude private ranges
        r'(?:\d{1,3}\.){3}\d{1,3}\b'  # Match valid IPv4 addresses
    )

class DutchEntityDetector(Detector):
    """Base class for Dutch entity detectors."""

    # Common Dutch words that should never be considered as entities
    COMMON_WORDS = {
        'een', 'het', 'de', 'die', 'dat', 'deze', 'dit', 'die', 'dan', 'toen',
        'als', 'maar', 'want', 'dus', 'nog', 'al', 'naar', 'door', 'om', 'bij',
        'aan', 'van', 'in', 'op', 'te', 'ten', 'ter', 'met', 'tot', 'voor', 'ben'
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.entities = []
        self._load_json_entities()

    def _load_json_entities(self):
        try:
            # Get the package's data directory
            data_dir = Path(__file__).parent.parent / 'data' / 'nl_entities'
            filepath = data_dir / self.json_file
            
            if not filepath.exists():
                click.echo(f"Warning: Could not find entity file {self.json_file}", err=True)
                return

            with open(filepath, 'r') as f:
                entities = json.load(f)
                for entity in entities:
                    match = entity['match'].strip()
                    # Skip empty strings, single characters, and common words
                    if (len(match) <= 1 or 
                        match.lower() in self.COMMON_WORDS or 
                        not any(c.isalpha() for c in match)):
                        continue
                    self.entities.append(match)
        except Exception as e:
            click.echo(f"Warning: Could not load JSON entity file {self.json_file}: {str(e)}", err=True)

    def iter_filth(self, text, document_name=None):
        for match in self.entities:
            # Create a pattern that matches the word with word boundaries
            pattern = r'\b' + re.escape(match) + r'\b'
            
            # Find all non-overlapping matches
            for found_match in re.finditer(pattern, text, re.IGNORECASE):
                matched_text = found_match.group()
                # Double-check that the match isn't a common word (case-insensitive)
                if matched_text.lower() in self.COMMON_WORDS:
                    continue
                # Ensure the match contains at least one letter
                if not any(c.isalpha() for c in matched_text):
                    continue
                yield self.filth_cls(
                    beg=found_match.start(),
                    end=found_match.end(),
                    text=matched_text,
                    detector_name=self.name,
                    document_name=document_name
                )

@register_detector
class DutchLocationDetector(DutchEntityDetector):
    """Detector for Dutch locations."""
    name = 'location'
    filth_cls = LocationFilth
    json_file = 'cities.json'

@register_detector
class DutchOrganizationDetector(DutchEntityDetector):
    """Detector for Dutch organizations."""
    name = 'organization'
    filth_cls = OrganizationFilth
    json_file = 'organizations.json'

@register_detector
class DutchNameDetector(DutchEntityDetector):
    """Detector for Dutch names."""
    name = 'name'
    filth_cls = NameFilth
    json_file = 'names.json' 