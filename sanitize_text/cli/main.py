#!/usr/bin/env python3

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

import sys

import click
from halo import Halo

from sanitize_text.cli.io import (
    infer_output_format,
    maybe_cleanup,
    read_input_source,
    write_output,
)
from sanitize_text.core.scrubber import (
    get_available_detectors,
    get_generic_detector_descriptions,
    scrub_text,
)
from sanitize_text.utils.nlp_resources import download_optional_models

# Define custom context settings
CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


def _print_detectors() -> None:
    """Print available detector descriptions to stdout.

    Outputs both the generic detector catalogue and per-locale detectors for
    human reference.
    """
    generic_detectors = get_generic_detector_descriptions()
    locale_detectors = get_available_detectors()

    click.echo("Available detectors:\n")
    click.echo("Generic detectors (available for all locales):")
    for detector, description in sorted(generic_detectors.items()):
        click.echo(f"  - {detector:<15} {description}")
    click.echo()

    click.echo("Locale-specific detectors:")
    for loc, detector_dict in sorted(locale_detectors.items()):
        click.echo(f"\n{loc}:")
        for detector, description in sorted(detector_dict.items()):
            click.echo(f"  - {detector:<15} {description}")
    click.echo()


def _run_scrub(
    *,
    input_text: str,
    locale: str | None,
    detectors: str | None,
    custom: str | None,
    cleanup: bool,
    verbose: bool,
) -> str:
    """Return scrubbed text for the requested configuration.

    Args:
        input_text: Raw text supplied by the user.
        locale: Optional locale identifier restricting processing.
        detectors: Whitespace-separated detector names from the CLI.
        custom: Optional custom detector text configured by the user.
        cleanup: Whether to normalize the final text with cleanup helpers.
        verbose: Whether to emit detector progress information.

    Returns:
        str: Final scrubbed text (including optional cleanup processing).
    """
    selected_detectors = detectors.split() if detectors else None
    outcome = scrub_text(
        input_text,
        locale,
        selected_detectors,
        custom_text=custom,
        verbose=verbose,
    )
    locales_to_process = [locale] if locale else ["en_US", "nl_NL"]

    formatted_sections = [
        f"Results for {loc}:\n{outcome.texts[loc]}"
        for loc in locales_to_process
        if loc in outcome.texts
    ]
    scrubbed_text = "\n\n".join(formatted_sections)
    scrubbed_text = maybe_cleanup(scrubbed_text, cleanup)

    failed_locales = [loc for loc in locales_to_process if loc not in outcome.texts]
    failure_messages = {
        failed: outcome.errors.get(failed, "Unknown error") for failed in failed_locales
    }
    if not verbose:
        for failed, message in failure_messages.items():
            click.echo(f"Warning: Processing failed for locale {failed}: {message}", err=True)

    if verbose:
        from sanitize_text.core.scrubber import collect_filth

        for loc in locales_to_process:
            detectors_for_locale = outcome.detectors.get(loc)
            if loc in outcome.texts:
                click.echo(f"\n[Processing locale: {loc}]")
                if detectors_for_locale:
                    click.echo(f"[Active detectors: {', '.join(detectors_for_locale)}]")
                click.echo(f"[Scanning text ({len(input_text)} characters)...]")
                click.echo(f"[Completed processing for {loc}]")
            else:
                message = failure_messages.get(loc, "Unknown error")
                click.echo(f"\n[Processing locale: {loc}]")
                click.echo(
                    f"[Failed processing locale {loc}: {message}]",
                    err=True,
                )

        filth_map = collect_filth(
            input_text,
            locale,
            selected_detectors,
            custom_text=custom,
        )
        for loc, filths in filth_map.items():
            click.echo(f"\nFound PII for {loc}:")
            for f in filths:
                mapping = f"  - {f.type}: '{f.text}' -> '{f.replacement_string}'"
                click.echo(mapping)
    return scrubbed_text


@click.group(context_settings=CONTEXT_SETTINGS, invoke_without_command=True)
@click.pass_context
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
    "--output-format",
    type=click.Choice(["txt", "docx", "pdf"]),
    help="Explicit output format. Otherwise inferred from -o extension (txt/docx/pdf).",
)
@click.option(
    "--pdf-mode",
    type=click.Choice(["pre", "para"]),
    default="pre",
    show_default=True,
    help=("PDF layout: 'pre' preserves line breaks, 'para' wraps into paragraphs."),
)
@click.option(
    "--pdf-font",
    type=click.Path(exists=True, dir_okay=False),
    help="Path to a TTF font to embed for Unicode support (PDF only).",
)
@click.option(
    "--font-size",
    type=int,
    default=11,
    show_default=True,
    help="Font size for PDF output.",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show mapping of found PII and their replacements.",
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
@click.option(
    "--list-detectors",
    "-ld",
    is_flag=True,
    help="Show available detectors and exit.",
)
@click.option(
    "--cleanup/--no-cleanup",
    default=True,
    show_default=True,
    help=(
        "Apply a conservative cleanup pass to final output "
        "(dedupe lines, remove UNKNOWN placeholders, ensure trailing newline)."
    ),
)
@click.option(
    "--download-nlp-models",
    is_flag=True,
    help="Download optional NLP resources (NLTK corpora and spaCy small models) before running.",
)
def main(
    ctx: click.Context,
    text: str | None,
    input: str | None,
    output: str | None,
    locale: str | None,
    detectors: str | None,
    custom: str | None,
    list_detectors: bool,
    verbose: bool,
    append: bool,
    output_format: str | None,
    pdf_mode: str,
    pdf_font: str | None,
    font_size: int,
    cleanup: bool,
    download_nlp_models: bool,
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
    # If --list-detectors flag is used, show detectors and exit (back-compat)
    if list_detectors and (ctx.invoked_subcommand is None):
        _print_detectors()
        return

    # If user invoked a subcommand, do not run default flow
    if ctx.invoked_subcommand is not None:
        return

    # Optional: download NLP resources
    if download_nlp_models:
        download_optional_models()

    # Determine input text via helper
    try:
        input_text = read_input_source(
            text=text,
            input_path=input,
            append=append,
            output_path=output,
        )
    except Exception as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    # Set up spinner (only if not verbose)
    spinner = None
    if not verbose:
        spinner = Halo(text="Scrubbing PII", spinner="dots")
        spinner.start()

    try:
        # Process text with selected detectors
        scrubbed_text = _run_scrub(
            input_text=input_text,
            locale=locale,
            detectors=detectors,
            custom=custom,
            cleanup=cleanup,
            verbose=verbose,
        )
    except Exception as e:
        if spinner:
            spinner.fail("Scrubbing failed")
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)
    else:
        if spinner:
            spinner.succeed("Scrubbing completed")

    # Handle output
    if text and output is None and output_format is None:
        click.echo(scrubbed_text)
    else:
        fmt = infer_output_format(output, output_format)
        try:
            out_path = write_output(
                text=scrubbed_text,
                output=output,
                fmt=fmt,
                pdf_mode=pdf_mode,
                pdf_font=pdf_font,
                font_size=font_size,
            )
        except Exception as exc:  # pragma: no cover
            click.echo(f"Error writing output: {exc}", err=True)
            sys.exit(1)

        click.echo(f"Scrubbed text saved to {out_path}")


@main.command("list-detectors")
def list_detectors_cmd() -> None:
    """List available detectors and exit."""
    _print_detectors()


@main.command("scrub")
@click.option("--text", "-t", type=str, help="Inline text input.")
@click.option(
    "--input",
    "-i",
    type=click.Path(exists=True),
    help="Input file path.",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(writable=True),
    help="Output file path.",
)
@click.option(
    "--output-format",
    type=click.Choice(["txt", "docx", "pdf"]),
    help="Explicit output format.",
)
@click.option(
    "--pdf-mode",
    type=click.Choice(["pre", "para"]),
    default="pre",
    show_default=True,
)
@click.option(
    "--pdf-font",
    type=click.Path(exists=True, dir_okay=False),
)
@click.option("--font-size", type=int, default=11, show_default=True)
@click.option("--verbose", "-v", is_flag=True, help="Show mappings for found PII.")
@click.option("--append", "-a", is_flag=True, help="Use output file as input.")
@click.option(
    "--locale",
    "-l",
    type=click.Choice(["nl_NL", "en_US"]),
    metavar="<locale>",
)
@click.option(
    "--detectors",
    "-d",
    metavar="<detectors>",
    help="Space-separated detectors.",
)
@click.option("--custom", "-c", metavar="<text>", help="Custom text to detect.")
@click.option(
    "--cleanup/--no-cleanup",
    default=True,
    show_default=True,
    help="Cleanup output.",
)
@click.option(
    "--download-nlp-models",
    is_flag=True,
    help="Download optional NLP resources (NLTK corpora and spaCy small models) before running.",
)
def scrub_cmd(
    *,
    text: str | None,
    input: str | None,
    output: str | None,
    output_format: str | None,
    pdf_mode: str,
    pdf_font: str | None,
    font_size: int,
    verbose: bool,
    append: bool,
    locale: str | None,
    detectors: str | None,
    custom: str | None,
    cleanup: bool,
    download_nlp_models: bool,
) -> None:
    """Scrub PII from input and write output (subcommand)."""
    if download_nlp_models:
        download_optional_models()
    try:
        input_text = read_input_source(
            text=text, input_path=input, append=append, output_path=output
        )
    except Exception as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    spinner = None
    if not verbose:
        spinner = Halo(text="Scrubbing PII", spinner="dots")
        spinner.start()
    try:
        scrubbed_text = _run_scrub(
            input_text=input_text,
            locale=locale,
            detectors=detectors,
            custom=custom,
            cleanup=cleanup,
            verbose=verbose,
        )
    except Exception as e:  # pragma: no cover
        if spinner:
            spinner.fail("Scrubbing failed")
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)
    else:
        if spinner:
            spinner.succeed("Scrubbing completed")

    if text and output is None and output_format is None:
        click.echo(scrubbed_text)
        return

    fmt = infer_output_format(output, output_format)
    try:
        out_path = write_output(
            text=scrubbed_text,
            output=output,
            fmt=fmt,
            pdf_mode=pdf_mode,
            pdf_font=pdf_font,
            font_size=font_size,
        )
    except Exception as exc:  # pragma: no cover
        click.echo(f"Error writing output: {exc}", err=True)
        sys.exit(1)
    click.echo(f"Scrubbed text saved to {out_path}")


if __name__ == "__main__":
    main()
