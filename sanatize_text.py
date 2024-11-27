#!/usr/bin/env python3
"""
sanitize_text.py

A Python script to sanitize text by replacing URLs, email addresses, company names,
and other Personally Identifiable Information (PII) with predefined placeholders.

This script leverages regular expressions and spaCy's Named Entity Recognition (NER)
to identify and replace sensitive information. It automatically checks for the
required spaCy model and installs it if not present.

Author: elvee
Date: 27-11-2024
"""

# [Leveraging the Python Ecosystem: Use the PyPI Instead of Doing It Yourself]
import re
import sys
import subprocess
from typing import Dict, Any, Optional

import click
import spacy
from spacy.language import Language
from spacy.tokens import Doc
from spacy.util import is_package
from collections import Counter
from pathlib import Path


# [Use the Right Data Structures: Store Unique Values with Sets]
SUPPORTED_ENTITY_LABELS = {
    'PERSON',
    'ORG',
    'GPE',
    'LOC',
    'PHONE',
    'DATE',
    'EMAIL',
    'URL'
}

# [Constants]
PLACEHOLDER_MAPPING: Dict[str, str] = {
    'PERSON': '<PERSON>',
    'ORG': '<COMPANY>',
    'GPE': '<LOCATION>',
    'LOC': '<LOCATION>',
    'PHONE': '<PHONE>',
    'DATE': '<DATE>',
    'EMAIL': '<EMAIL>',
    'URL': '<URL>',
}


# [Write Object-Oriented Code]
class Sanitizer:
    """A class to sanitize text by replacing PII with placeholders."""

    def __init__(self, nlp: Language) -> None:
        """
        Initialize the Sanitizer with a spaCy language model.

        Args:
            nlp (Language): The spaCy language model for NER.
        """
        self.nlp = nlp
        # [Precompile regex patterns for performance]
        self.url_pattern = re.compile(r'(https?://\S+|www\.\S+)', re.IGNORECASE)
        self.email_pattern = re.compile(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        )

    def sanitize_text(self, text: str) -> str:
        """
        Sanitize the input text by replacing URLs, email addresses, and PII with placeholders.

        Args:
            text (str): The input text to sanitize.

        Returns:
            str: The sanitized text.
        """
        # [Replace URLs]
        text = self.url_pattern.sub(PLACEHOLDER_MAPPING['URL'], text)

        # [Replace email addresses]
        text = self.email_pattern.sub(PLACEHOLDER_MAPPING['EMAIL'], text)

        # [Use spaCy NER to identify and replace PII]
        doc: Doc = self.nlp(text)
        # [Process entities in reverse order to avoid overlapping replacements]
        entities = sorted(doc.ents, key=lambda ent: ent.start_char, reverse=True)

        # [Collect statistics using Counter]
        entity_counter = Counter(ent.label_ for ent in doc.ents if ent.label_ in SUPPORTED_ENTITY_LABELS)

        for ent in entities:
            placeholder = PLACEHOLDER_MAPPING.get(ent.label_, f'<{ent.label_}>')
            # [Replace the entity with its placeholder]
            start, end = ent.start_char, ent.end_char
            text = f"{text[:start]}{placeholder}{text[end:]}"

        # [Optionally, return statistics if needed]
        # For this script, we'll focus on sanitization only.

        return text


def ensure_spacy_model(model_name: str = 'en_core_web_sm') -> None:
    """
    Ensure that the specified spaCy model is installed. If not, install it automatically.

    Args:
        model_name (str): The name of the spaCy model to check and install. Defaults to 'en_core_web_sm'.
    """
    if not is_package(model_name):
        click.echo(f"The spaCy model '{model_name}' is not installed. Installing now...", err=True)
        try:
            subprocess.run([sys.executable, "-m", "spacy", "download", model_name],
                           check=True)
            click.echo(f"Successfully installed '{model_name}'.", err=True)
        except subprocess.CalledProcessError:
            click.echo(f"Failed to install spaCy model '{model_name}'. Please install it manually.", err=True)
            sys.exit(1)


# [Write Readable and Maintainable Code: Parse Command-Line Arguments]
@click.command()
@click.argument('input_file', type=click.Path(exists=True, file_okay=True, dir_okay=False, readable=True), required=True)
@click.option('-o', '--output', 'output_file', type=click.Path(writable=True, file_okay=True, dir_okay=False), default=None,
              help='Output file to write sanitized text. Defaults to appending "-sanitized" before the file extension in the input file\'s directory.')
def main(input_file: str, output_file: Optional[str]) -> None:
    """
    Sanitize text by replacing URLs, email addresses, company names, and other PII with placeholders.

    INPUT_FILE: Path to the input text file to sanitize.

    If OUTPUT_FILE is not provided, the script saves the sanitized text in the same directory as INPUT_FILE,
    appending '-sanitized' before the file extension.
    """
    # [Ensure spaCy model is installed]
    ensure_spacy_model('en_core_web_sm')

    # [Load spaCy English model]
    try:
        nlp: Language = spacy.load('en_core_web_sm')
    except OSError:
        click.echo("Error: Failed to load the spaCy model after installation.", err=True)
        sys.exit(1)

    # [Convert input_file to Path object]
    input_path: Path = Path(input_file)

    # [Determine output file path]
    if output_file:
        output_path: Path = Path(output_file)
    else:
        # [Append '-sanitized' before the file extension]
        if input_path.suffix:
            output_filename = f"{input_path.stem}-sanitized{input_path.suffix}"
        else:
            # [Handle files without an extension]
            output_filename = f"{input_path.name}-sanitized"
        output_path = input_path.parent / output_filename

    # [Read input text]
    try:
        input_text: str = input_path.read_text(encoding='utf-8')
    except Exception as e:
        click.echo(f"Error reading input file: {e}", err=True)
        sys.exit(1)

    # [Instantiate Sanitizer and sanitize text]
    sanitizer: Sanitizer = Sanitizer(nlp)
    sanitized_text: str = sanitizer.sanitize_text(input_text)

    # [Write output text]
    try:
        output_path.write_text(sanitized_text, encoding='utf-8')
        click.echo(f"Sanitized text has been saved to: {output_path}")
    except Exception as e:
        click.echo(f"Error writing to output file: {e}", err=True)
        sys.exit(1)


# [Main Guard: Ensures script runs only when executed directly]
if __name__ == '__main__':
    main()