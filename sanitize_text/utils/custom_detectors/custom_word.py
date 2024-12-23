from scrubadub.detectors import Detector
from scrubadub.filth import Filth

class CustomWordFilth(Filth):
    type = 'custom'

class CustomWordDetector(Detector):
    """Detector for custom words or phrases."""
    
    name = 'custom'
    filth_cls = CustomWordFilth
    
    def __init__(self, custom_text=None, **kwargs):
        super().__init__(**kwargs)
        self.custom_text = custom_text.strip() if custom_text else None
        
    def iter_filth(self, text, document_name=None):
        if not self.custom_text or not text:
            return
            
        # Find all occurrences of the custom text
        start = 0
        while True:
            start = text.find(self.custom_text, start)
            if start == -1:
                break
                
            yield self.filth_cls(
                beg=start,
                end=start + len(self.custom_text),
                text=self.custom_text,
                detector_name=self.name,
                document_name=document_name
            )
            start += 1 