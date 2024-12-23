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
    name = 'hashed_pii_replacer'
    
    def __init__(self):
        self.seen_values = {}
        self.counter = 1
    
    def process_filth(self, filth_list):
        """Process a list of filth and replace with hashed identifiers."""
        for filth in filth_list:
            # Generate a unique identifier based on filth type and text
            key = f"{filth.type}:{filth.text}"
            if key not in self.seen_values:
                # Create a hash of the text for consistent replacement
                hash_obj = hashlib.md5(key.encode())
                hash_val = int(hash_obj.hexdigest(), 16) % 1000
                self.seen_values[key] = f"{filth.type.upper()}-{hash_val:03d}"
            
            # Replace the text with the hashed identifier
            filth.replacement_string = self.seen_values[key]
        
        return filth_list