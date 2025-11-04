"""Base classes for custom detectors."""

from __future__ import annotations

import json
import re
from pathlib import Path

import click
from scrubadub.detectors import Detector


class JSONEntityDetector(Detector):
    """Base class for detectors that load entities from packaged JSON lists."""

    #: Common words that should never be considered entities. Subclasses can
    #: override this with locale-specific stop-word sets.
    COMMON_WORDS: set[str] = set()

    #: Name of the directory inside ``sanitize_text/data`` that contains the
    #: JSON files for this detector family. Subclasses must override it.
    data_subdir: str | None = None

    #: Name of the JSON file to load. Subclasses must override it.
    json_file: str

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.entities: list[str] = []
        self._load_json_entities()

    def _load_json_entities(self) -> None:
        """Populate ``self.entities`` with matches from the JSON resource."""

        if not self.data_subdir:
            raise ValueError("data_subdir must be defined for JSONEntityDetector subclasses")

        try:
            data_dir = Path(__file__).parent.parent.parent / 'data' / self.data_subdir
            filepath = data_dir / self.json_file

            if not filepath.exists():
                click.echo(f"Warning: Could not find entity file {self.json_file}", err=True)
                return

            with open(filepath, 'r', encoding='utf-8') as file_handle:
                entities = json.load(file_handle)
                for entity in entities:
                    match = entity['match'].strip()
                    # Skip empty strings, single characters, and common words
                    if (
                        len(match) <= 1
                        or match.lower() in self.COMMON_WORDS
                        or not any(char.isalpha() for char in match)
                    ):
                        continue
                    self.entities.append(match)
        except Exception as exc:
            click.echo(
                f"Warning: Could not load JSON entity file {self.json_file}: {exc}",
                err=True,
            )

    def iter_filth(self, text, document_name=None):
        for match in self.entities:
            pattern = r'\b' + re.escape(match) + r'\b'

            for found_match in re.finditer(pattern, text, re.IGNORECASE):
                matched_text = found_match.group()
                if matched_text.lower() in self.COMMON_WORDS:
                    continue
                if not any(char.isalpha() for char in matched_text):
                    continue
                yield self.filth_cls(
                    beg=found_match.start(),
                    end=found_match.end(),
                    text=matched_text,
                    detector_name=self.name,
                    document_name=document_name,
                )


class DutchEntityDetector(JSONEntityDetector):
    """Base class for Dutch entity detectors."""

    COMMON_WORDS = {
        'een', 'het', 'de', 'die', 'dat', 'deze', 'dit', 'die', 'dan', 'toen',
        'als', 'maar', 'want', 'dus', 'nog', 'al', 'naar', 'door', 'om', 'bij',
        'aan', 'van', 'in', 'op', 'te', 'ten', 'ter', 'met', 'tot', 'voor', 'ben'
    }
    data_subdir = 'nl_entities'


class EnglishEntityDetector(JSONEntityDetector):
    """Base class for English entity detectors."""

    COMMON_WORDS = {
        'a', 'an', 'and', 'at', 'be', 'for', 'from', 'has', 'have', 'in', 'is',
        'it', 'of', 'on', 'or', 'that', 'the', 'their', 'there', 'this', 'to',
        'was', 'were', 'with'
    }
    data_subdir = 'en_entities'
