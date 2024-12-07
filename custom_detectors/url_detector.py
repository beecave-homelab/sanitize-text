import re
from scrubadub.detectors import RegexDetector, register_detector
from scrubadub.filth.url import UrlFilth

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