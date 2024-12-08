"""Post-processors for text scrubbing."""

import scrubadub

class HashedPIIReplacer(scrubadub.post_processors.PostProcessor):
    """Post-processor that replaces PII with hashed placeholders."""
    
    name = 'hashed_pii_replacer'
    
    def process_filth(self, filth_list):
        """Process the filth list and replace with hashed placeholders."""
        for filth in filth_list:
            filth.replacement_string = f"{{{{{filth.type}-{hash(filth.text) % 10000:04d}}}}}"
        return filth_list 