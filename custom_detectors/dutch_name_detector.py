import json
import click
import re
from scrubadub.detectors import Detector, register_detector
from .dutch_filth import NameFilth

@register_detector
class DutchNameDetector(Detector):
    name = 'dutch_name_detector'
    filth_cls = NameFilth

    # Common Dutch words that should never be considered as entities
    COMMON_WORDS = {
        'een', 'het', 'de', 'die', 'dat', 'deze', 'dit', 'die', 'dan', 'toen',
        'als', 'maar', 'want', 'dus', 'nog', 'al', 'naar', 'door', 'om', 'bij',
        'aan', 'van', 'in', 'op', 'te', 'ten', 'ter', 'met', 'tot', 'voor'
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.entities = []
        self._load_json_entities()

    def _load_json_entities(self):
        try:
            with open('nl_entities/names.json', 'r') as f:
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
            click.echo(f"Warning: Could not load JSON entity file names.json: {str(e)}", err=True)

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
                yield NameFilth(
                    beg=found_match.start(),
                    end=found_match.end(),
                    text=matched_text,
                    detector_name=self.name,
                    document_name=document_name
                ) 