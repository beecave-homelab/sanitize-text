"""Base classes for custom detectors."""

import re
import json
import click
from pathlib import Path
from scrubadub.detectors import Detector

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
            data_dir = Path(__file__).parent.parent.parent / 'data' / 'nl_entities'
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