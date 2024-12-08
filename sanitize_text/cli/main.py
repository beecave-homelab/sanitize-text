#!venv/bin/python3

"""Command-line interface for text scrubbing.

This module provides a command-line interface for the text sanitization
functionality, allowing users to process text files or direct input and
remove personally identifiable information (PII).
"""

import os
import sys
import click
import nltk
from typing import Optional
from halo import Halo
from ..core.scrubber import scrub_text, get_available_detectors

# Download required NLTK data
try:
    nltk.download('punkt', quiet=True)
    nltk.download('averaged_perceptron_tagger', quiet=True)
except Exception as e:
    click.echo(f"Warning: Could not download NLTK data: {str(e)}", err=True)

@click.command()
@click.option(
    "--text", "-t",
    type=str,
    help="Input text to scrub for PII.",
    default=None,
)
@click.option(
    "--input", "-i",
    type=click.Path(exists=True),
    help="Path to input file containing text to scrub.",
    default=None,
)
@click.option(
    "--output", "-o",
    type=click.Path(writable=True),
    help="Path to output file where scrubbed text will be saved. "
         "Defaults to $PWD/output/scrubbed.txt",
    default=None,
)
@click.option(
    "--append", "-a",
    is_flag=True,
    help="If set, use the output file as input when it exists, "
         "ignoring the input file.",
    default=False,
)
@click.option(
    "--locale", "-l",
    type=click.Choice(['nl_NL', 'en_US']),
    help="Locale for text processing (nl_NL or en_US)",
    default=None
)
@click.option(
    "--detectors", "-d",
    help="Space-separated list of specific detectors to use "
         "(e.g., 'url name organisation')",
    default=None
)
@click.option(
    "--list-detectors", "-ld",
    is_flag=True,
    help="List all available detectors",
)
def main(
    text: Optional[str],
    input: Optional[str],
    output: Optional[str],
    locale: Optional[str],
    detectors: Optional[str],
    list_detectors: bool,
    append: bool
) -> None:
    """Remove personally identifiable information (PII) from text.

    This command-line tool processes text from various sources (direct input,
    file, or stdin) and removes PII using configurable detectors. It supports
    multiple locales and can handle various types of PII including emails,
    phone numbers, URLs, names, organizations, and locations.

    Examples:
        # Process text directly
        sanitize-text -t "John lives in Amsterdam"
        
        # Process a file
        sanitize-text -i input.txt -o output.txt
        
        # Use specific detectors
        sanitize-text -i input.txt -d "email url name"
        
        # Process Dutch text
        sanitize-text -i input.txt -l nl_NL
    """
    # If --list-detectors is used, show available detectors and exit
    if list_detectors:
        detectors_by_locale = get_available_detectors()
        generic_detectors = {
            'email': 'Detect email addresses',
            'phone': 'Detect phone numbers',
            'url': 'Detect URLs',
            'private_ip': 'Detect private IP addresses',
            'public_ip': 'Detect public IP addresses'
        }
        
        click.echo("Available detectors:\n")
        click.echo("Generic detectors (available for all locales):")
        for detector, description in generic_detectors.items():
            click.echo(f"  - {detector:<15} {description}")
        click.echo()
        
        click.echo("Locale-specific detectors:")
        for loc, detector_dict in detectors_by_locale.items():
            click.echo(f"\n{loc}:")
            for detector, description in detector_dict.items():
                click.echo(f"  - {detector:<15} {description}")
        click.echo()
        return

    # Validate append mode requirements
    if append and not output:
        click.echo(
            "Error: --append/-a requires --output/-o to be specified.",
            err=True
        )
        sys.exit(1)

    # Determine input text
    if append and output and os.path.exists(output):
        with open(output, "r") as output_file:
            input_text = output_file.read()
    elif input:
        with open(input, "r") as input_file:
            input_text = input_file.read()
    elif text:
        input_text = text
    elif not sys.stdin.isatty():
        input_text = sys.stdin.read()
    else:
        click.echo(
            "Error: No input provided. Use --text, --input, or pipe input.",
            err=True
        )
        sys.exit(1)

    # Set up spinner
    spinner = Halo(text="Scrubbing PII", spinner="dots")
    spinner.start()

    try:
        # Process text with selected detectors
        selected_detectors = detectors.split() if detectors else None
        scrubbed_texts = scrub_text(input_text, locale, selected_detectors)
        scrubbed_text = "\n\n".join(scrubbed_texts)
    except Exception as e:
        spinner.fail("Scrubbing failed")
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)
    else:
        spinner.succeed("Scrubbing completed")

    # Handle output
    if text:
        # Print scrubbed text to terminal when --text is used
        click.echo(scrubbed_text)
    else:
        if output is None:
            # Use default output directory and file
            output_dir = os.path.join(os.getcwd(), "output")
            os.makedirs(output_dir, exist_ok=True)
            output = os.path.join(output_dir, "scrubbed.txt")
        
        with open(output, "w") as output_file:
            output_file.write(scrubbed_text)
        click.echo(f"Scrubbed text saved to {output}")

if __name__ == "__main__":
    main() 