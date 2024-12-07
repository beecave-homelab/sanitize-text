import re
from scrubadub.detectors import RegexDetector, register_detector
from scrubadub.filth.url import UrlFilth

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
    """
    name = 'markdown_url'
    filth_cls = UrlFilth

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Pattern for markdown links that handles both empty and non-empty link text
        self.regex = re.compile(
            r'\['               # Opening bracket
            r'([^\]]*)'        # Link text (can be empty)
            r'\]'              # Closing bracket
            r'\('              # Opening parenthesis
            r'(https?://[^\s)]+)'  # URL part
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