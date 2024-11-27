import re
import sys
import subprocess
from typing import Dict, Any, Optional

import click
from pii_anonymizer import AnonymizerEngine
from pii_anonymizer.entities import RecognizerResult, OperatorConfig
from collections import Counter
from pathlib import Path

# Define the PII types to be detected
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

# Define the placeholder mappings for each PII type
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

class Sanitizer:
    """A class to sanitize text by replacing PII with placeholders."""

    def __init__(self) -> None:
        """Initialize the Sanitizer with the AnonymizerEngine."""
        self.anonymizer = AnonymizerEngine()

    def sanitize_text(self, text: str) -> str:
        """
        Sanitize the input text by replacing PII with placeholders.

        Args:
            text (str): The input text to sanitize.

        Returns:
            str: The sanitized text.
        """
        # Analyze the text to detect PII entities
        analyzer_results = self.anonymizer.analyze(text=text, language='en')

        # Prepare the operators for anonymization
        operators = {
            entity.entity_type: OperatorConfig(
                operator_name='replace',
                params={'new_value': PLACEHOLDER_MAPPING.get(entity.entity_type, f'<{entity.entity_type}>')}
            )
            for entity in analyzer_results
            if entity.entity_type in SUPPORTED_ENTITY_LABELS
        }

        # Anonymize the text
        result = self.anonymizer.anonymize(
            text=text,
            analyzer_results=analyzer_results,
            operators=operators
        )

        return result.text

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
    # Convert input_file to Path object
    input_path: Path = Path(input_file)

    # Determine output file path
    if output_file:
        output_path: Path = Path(output_file)
    else:
        # Append '-sanitized' before the file extension
        if input_path.suffix:
            output_filename = f"{input_path.stem}-sanitized{input_path.suffix}"
        else:
            # Handle files without an extension
            output_filename = f"{input_path.name}-sanitized"
        output_path = input_path.parent / output_filename

    # Read input text
    try:
        input_text: str = input_path.read_text(encoding='utf-8')
    except Exception as e:
        click.echo(f"Error reading input file: {e}", err=True)
        sys.exit(1)

    # Instantiate Sanitizer and sanitize text
    sanitizer: Sanitizer = Sanitizer()
    sanitized_text: str = sanitizer.sanitize_text(input_text)

    # Write output text
    try:
        output_path.write_text(sanitized_text, encoding='utf-8')
        click.echo(f"Sanitized text has been saved to: {output_path}")
    except Exception as e:
        click.echo(f"Error writing to output file: {e}", err=True)
        sys.exit(1)

if __name__ == '__main__':
    main()