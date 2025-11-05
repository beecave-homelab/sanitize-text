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
from pathlib import Path

import click
from halo import Halo

from sanitize_text.core.scrubber import get_available_detectors, scrub_text
from sanitize_text.utils import preconvert

# Define custom context settings
CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


def _normalize_text_for_pdf(text: str, mode: str) -> str:
    """Normalize text for better PDF rendering.

    - Remove soft hyphens and non-breaking hyphens.
    - De-hyphenate line-wrapped words.
    - Optionally merge lines into paragraphs (para mode).
    """
    # Remove soft hyphen and non-breaking hyphen
    text = text.replace("\u00ad", "").replace("\u2011", "-")

    # Work line by line
    lines = text.splitlines()

    # First pass: join hyphenated line breaks (word-\nnext -> wordnext)
    joined: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        if line.endswith("-") and i + 1 < len(lines):
            nxt = lines[i + 1].lstrip()
            # Avoid joining when the hyphen is likely meaningful (e.g., bullets)
            if nxt and nxt[0].islower():
                line = line[:-1] + nxt
                i += 1
            else:
                joined.append(line)
                i += 1
                continue
        joined.append(line)
        i += 1

    if mode == "pre":
        return "\n".join(joined)

    # Paragraph mode: heuristically merge lines into paragraphs
    paras: list[str] = []
    buf: list[str] = []

    def flush() -> None:
        if buf:
            paras.append(" ".join(buf).strip())
            buf.clear()

    for ln in joined:
        if not ln.strip():
            flush()
            continue
        if not buf:
            buf.append(ln.strip())
            continue
        prev = buf[-1]
        # If previous line ends with sentence punctuation, start a new sentence
        if prev.endswith((".", "!", "?", ":")):
            buf.append(ln.strip())
        else:
            # If next line starts lowercase/alphanumeric, consider it a wrapped continuation
            first = ln.lstrip()[:1]
            if first and (first.islower() or first.isdigit()):
                buf[-1] = prev + " " + ln.strip()
            else:
                buf.append(ln.strip())
    flush()

    return "\n\n".join(paras)


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
    "--output-format",
    type=click.Choice(["txt", "docx", "pdf"]),
    help="Explicit output format. Otherwise inferred from -o extension (txt/docx/pdf).",
)
@click.option(
    "--pdf-mode",
    type=click.Choice(["pre", "para"]),
    default="pre",
    show_default=True,
    help=(
        "PDF layout: 'pre' preserves line breaks, 'para' wraps into paragraphs."
    ),
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
    output_format: str | None,
    pdf_mode: str,
    pdf_font: str | None,
    font_size: int,
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
        ext = Path(input).suffix.lower()
        if ext == ".pdf":
            input_text = preconvert.pdf_to_text(input)
        elif ext in {".doc", ".docx"}:
            input_text = preconvert.docx_to_text(input)
        elif ext == ".rtf":
            input_text = preconvert.rtf_to_text(input)
        elif ext in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}:
            input_text = preconvert.image_to_text(input)
        else:
            with open(input, encoding="utf-8", errors="replace") as input_file:
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
    if text and output is None and output_format is None:
        # Print scrubbed text to terminal when --text is used
        click.echo(scrubbed_text)
    else:
        # Determine output path and format
        if output is None:
            output_dir = os.path.join(os.getcwd(), "output")
            os.makedirs(output_dir, exist_ok=True)
            output = os.path.join(output_dir, "scrubbed.txt")
        out_ext = Path(output).suffix.lower()
        fmt = output_format
        if fmt is None:
            if out_ext in {".doc", ".docx"}:
                fmt = "docx"
            elif out_ext == ".pdf":
                fmt = "pdf"
            else:
                fmt = "txt"

        # Write according to format
        if fmt == "txt":
            with open(output, "w", encoding="utf-8") as output_file:
                output_file.write(scrubbed_text)
        elif fmt == "docx":
            try:
                import docx  # type: ignore

                doc = docx.Document()
                for line in scrubbed_text.splitlines():
                    doc.add_paragraph(line)
                # Ensure directory exists
                Path(output).parent.mkdir(parents=True, exist_ok=True)
                doc.save(output)
            except Exception as exc:  # pragma: no cover
                click.echo(f"Error writing DOCX output: {exc}", err=True)
                sys.exit(1)
        elif fmt == "pdf":
            try:
                # Use Platypus for wrapping/pagination; support pre/para modes
                from reportlab.lib.pagesizes import A4  # type: ignore
                from reportlab.lib.styles import (  # type: ignore
                    ParagraphStyle,
                    getSampleStyleSheet,
                )
                from reportlab.lib.units import cm  # type: ignore
                from reportlab.pdfbase import pdfmetrics  # type: ignore
                from reportlab.pdfbase.ttfonts import TTFont  # type: ignore
                from reportlab.platypus import (  # type: ignore
                    Paragraph,
                    Preformatted,
                    SimpleDocTemplate,
                    Spacer,
                )

                Path(output).parent.mkdir(parents=True, exist_ok=True)

                doc = SimpleDocTemplate(
                    output,
                    pagesize=A4,
                    leftMargin=2 * cm,
                    rightMargin=2 * cm,
                    topMargin=2 * cm,
                    bottomMargin=2 * cm,
                    title="Sanitized Output",
                    author="sanitize-text",
                )
                styles = getSampleStyleSheet()
                # Register custom TTF if provided
                font_name = "Helvetica"
                if pdf_font:
                    try:
                        pdfmetrics.registerFont(TTFont("CustomTTF", pdf_font))
                        font_name = "CustomTTF"
                    except Exception:
                        # Fallback silently to default font
                        font_name = "Helvetica"
                # Build style
                style = ParagraphStyle(
                    name="SanitizeTextBody",
                    parent=styles["BodyText"],
                    fontName=font_name,
                    fontSize=font_size,
                    leading=int(font_size * 1.2),
                )
                story = []

                # Normalize extracted text to improve readability
                normalized = _normalize_text_for_pdf(scrubbed_text, pdf_mode)

                if pdf_mode == "pre":
                    # Preserve line breaks; wrap within margins
                    # Escape minimal HTML entities
                    safe = (
                        normalized.replace("&", "&amp;")
                        .replace("<", "&lt;")
                        .replace(">", "&gt;")
                    )
                    story.append(Preformatted(safe, style))
                else:
                    # Paragraph mode: split on blank lines to create paragraphs
                    paragraphs = [
                        p for p in normalized.split("\n\n") if p.strip()
                    ]
                    for p in paragraphs:
                        safe = (
                            p.replace("&", "&amp;")
                            .replace("<", "&lt;")
                            .replace(">", "&gt;")
                        )
                        story.append(Paragraph(safe, style))
                        story.append(Spacer(1, 0.4 * cm))

                if not story:
                    story.append(Paragraph("", style))

                doc.build(story)
            except Exception as exc:  # pragma: no cover
                click.echo(f"Error writing PDF output: {exc}", err=True)
                sys.exit(1)
        else:
            click.echo(f"Error: Unsupported output format '{fmt}'", err=True)
            sys.exit(1)

        click.echo(f"Scrubbed text saved to {output}")


if __name__ == "__main__":
    main()
