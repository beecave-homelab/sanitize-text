import json
import click
import re
from scrubadub.detectors import Detector, register_detector
from .dutch_filth import LocationFilth, OrganizationFilth, NameFilth

@register_detector
class DutchJsonEntityDetector(Detector):
    name = 'dutch_json_entity_detector'
    filth_cls = [LocationFilth, OrganizationFilth, NameFilth]

    # Common Dutch words that should never be considered as entities
    COMMON_WORDS = {
        'een', 'het', 'de', 'die', 'dat', 'deze', 'dit', 'die', 'dan', 'toen',
        'als', 'maar', 'want', 'dus', 'nog', 'al', 'naar', 'door', 'om', 'bij',
        'aan', 'van', 'in', 'op', 'te', 'ten', 'ter', 'met', 'tot', 'voor'
    }

    def __init__(self, filth_types=None, **kwargs):
        super().__init__(**kwargs)
        self.entities = []
        self.filth_types = [ft.lower() for ft in filth_types] if filth_types else None
        self._load_json_entities()

    def _load_json_entities(self):
        json_files = {
            'nl_entities/cities.json': (LocationFilth, 'location'),
            'nl_entities/organizations.json': (OrganizationFilth, 'organization'),
            'nl_entities/names.json': (NameFilth, 'name')
        }
        
        for file_path, (filth_class, filth_type) in json_files.items():
            # Skip if this filth type wasn't requested
            if self.filth_types and filth_type not in self.filth_types:
                continue
                
            try:
                with open(file_path, 'r') as f:
                    entities = json.load(f)
                    for entity in entities:
                        match = entity['match'].strip()
                        # Skip empty strings, single characters, and common words
                        if (len(match) <= 1 or 
                            match.lower() in self.COMMON_WORDS or 
                            not any(c.isalpha() for c in match)):
                            continue
                        self.entities.append((filth_class, match, filth_type))
            except Exception as e:
                click.echo(f"Warning: Could not load JSON entity file {file_path}: {str(e)}", err=True)

    def iter_filth(self, text, document_name=None):
        for filth_class, match, filth_type in self.entities:
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
                yield filth_class(
                    beg=found_match.start(),
                    end=found_match.end(),
                    text=matched_text,
                    detector_name=self.name,
                    document_name=document_name
                )