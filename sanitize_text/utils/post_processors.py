"""Post-processors for text sanitization.

This module provides post-processors that modify or transform the output
of text sanitization after PII detection.
"""

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
    name = 'hashed_pii_replacer'
    
    def process_filth(self, filth_list):
        """Process a list of filth objects, replacing text with hashed identifiers.
        
        Args:
            filth_list: List of Filth objects to process
            
        Returns:
            The processed list of Filth objects with replacement strings
        """
        for filth in filth_list:
            filth_type = filth.type.upper()
            filth.replacement_string = f"{filth_type}-{hash(filth.text) % 10000:04d}"
        return filth_list 