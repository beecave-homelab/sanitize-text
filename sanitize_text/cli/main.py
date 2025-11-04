#!venv/bin/python3

"""Command-line interface for text sanitization.

This tool removes personally identifiable information (PII) from text using
configurable detectors and locales. It can process text from various sources
including direct input, files, or stdin.

Examples:
    Process text directly:
        $ sanitize-text -t "John lives in Amsterdam"

    Process a file:
        $ sanitize-text -i input.txt -o output.txt

    Use specific detectors:
        $ sanitize-text -i input.txt -d "email url name"

    Process Dutch text:
        $ sanitize-text -i input.txt -l nl_NL
"""

import os
import sys

import click
from halo import Halo

from sanitize_text.core.scrubber import get_available_detectors, scrub_text

# Define custom context settings
CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option(
    "--text",
    "-t",
    type=str,
    help="Text to scrub for PII. Use this for direct text input.",
    metavar="<text>",
)
@click.option(
    "--input",
    "-i",
    type=click.Path(exists=True),
    help="Path to input file containing text to scrub.",
    metavar="<file>",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(writable=True),
    help="Path to output file for scrubbed text. Defaults to ./output/scrubbed.txt",
    metavar="<file>",
)
@click.option(
    "--append",
    "-a",
    is_flag=True,
    help="Use output file as input when it exists, ignoring --input.",
)
@click.option(
    "--locale",
    "-l",
    type=click.Choice(["nl_NL", "en_US"]),
    help="Locale for text processing. Processes both if not specified.",
    metavar="<locale>",
)
@click.option(
    "--detectors",
    "-d",
    help="Space-separated list of detectors to use (e.g., 'url name email').",
    metavar="<detectors>",
)
@click.option(
    "--custom",
    "-c",
    help="Custom text to detect and replace with a unique identifier.",
    metavar="<text>",
)
@click.option("--list-detectors", "-ld", is_flag=True, help="Show available detectors and exit.")
def main(
    text: str | None,
    input: str | None,
    output: str | None,
    locale: str | None,
    detectors: str | None,
    custom: str | None,
    list_detectors: bool,
    append: bool,
) -> None:
    r"""Remove personally identifiable information (PII) from text.

    This tool processes text from various sources (direct input, file, or stdin)
    and removes PII using configurable detectors. It supports multiple locales
    and can handle various types of PII including emails, phone numbers, URLs,
    names, organizations, and locations.

    \b
    Input Sources (in order of precedence):
    1. --text: Direct text input
    2. --input: Text file
    3. --append: Existing output file
    4. stdin: Piped input

    \b
    Detector Types:
    - Generic: email, phone, url, private_ip, public_ip
    - Dutch (nl_NL): location, organization, name
    - English (en_US): location, organization, name, date_of_birth

    \f
    Args:
        text: Direct text input to process
        input: Path to input file
        output: Path to output file
        locale: Locale code for processing
        detectors: Space-separated list of detectors
        list_detectors: Whether to list available detectors
        append: Whether to use output file as input
    """
    # If --list-detectors is used, show available detectors and exit
    if list_detectors:
        detectors_by_locale = get_available_detectors()
        generic_detectors = {
            "email": "Detect email addresses",
            "phone": "Detect phone numbers",
            "url": "Detect URLs",
            "private_ip": "Detect private IP addresses",
            "public_ip": "Detect public IP addresses",
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
        click.echo("Error: --append/-a requires --output/-o to be specified.", err=True)
        sys.exit(1)

    # Determine input text
    if append and output and os.path.exists(output):
        with open(output) as output_file:
            input_text = output_file.read()
    elif input:
        with open(input) as input_file:
            input_text = input_file.read()
    elif text:
        input_text = text
    elif not sys.stdin.isatty():
        input_text = sys.stdin.read()
    else:
        click.echo("Error: No input provided. Use --text, --input, or pipe input.", err=True)
        sys.exit(1)

    # Set up spinner
    spinner = Halo(text="Scrubbing PII", spinner="dots")
    spinner.start()

    try:
        # Process text with selected detectors
        selected_detectors = detectors.split() if detectors else None
        scrubbed_texts = scrub_text(input_text, locale, selected_detectors, custom_text=custom)
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
